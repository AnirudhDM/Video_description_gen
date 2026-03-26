"""
mcp_server.py
MCP server for NotebookLM Video Overview generation.

Tools:
  prepare_notebooklm_doc   — generate source doc + chat prompt from task markdown
  setup_notebooklm         — one-time Google login via headed Chrome
  upload_to_notebooklm     — headless Playwright: add source + trigger Video Overview
"""

import os
import json
import shutil
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_DIR = Path(__file__).parent

# SESSION_TTL_SECONDS defaults to 1 hour. Set to a lower value in .env for testing.
# e.g. SESSION_TTL_SECONDS=30 to expire in 30 seconds.
SESSION_TTL_SECONDS = int(os.environ.get("SESSION_TTL_SECONDS", 3600))

server = Server("video-generator")


# ── Helpers ─────────────────────────────────────────────────────────────────

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    return result.returncode, result.stdout, result.stderr


# ── Tool registry ────────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="check_setup",
            description=(
                "CALL THIS FIRST before using any other tool. "
                "Checks whether the NotebookLM automation is ready to use. "
                "On first run it returns step-by-step setup instructions. "
                "On subsequent runs it returns status=ready and you can proceed directly to video generation."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="prepare_notebooklm_doc",
            description=(
                "Generates a NotebookLM-optimized source document from raw coding problem markdown. "
                "Covers ONLY: problem description, examples walkthrough, constraints, and a brief "
                "implementation callout — no solution hints. "
                "Returns a prompt for Claude to write the document AND a notebooklm_prompt to type "
                "into the NotebookLM Chat to trigger Video Overview generation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_markdown": {"type": "string", "description": "Raw markdown of the coding problem"},
                    "tone": {
                        "type": "string",
                        "enum": ["interview", "explainer", "neutral"],
                        "description": "interview=professional/direct, explainer=narrative/podcast, neutral=balanced"
                    },
                    "target_duration": {
                        "type": "string",
                        "enum": ["1min", "2min", "3min"],
                        "description": "Target video length. 1min=~250 words, 2min=~500 words, 3min=~750 words"
                    }
                },
                "required": ["task_markdown"]
            }
        ),
        Tool(
            name="setup_notebooklm",
            description=(
                "One-time setup: opens a headed Chrome browser so the user can log in to Google, "
                "then saves the session and notebook URL for future headless use."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "notebook_url": {
                        "type": "string",
                        "description": "URL of the NotebookLM notebook to use permanently"
                    }
                },
                "required": ["notebook_url"]
            }
        ),
        Tool(
            name="upload_to_notebooklm",
            description=(
                "Uploads a document to NotebookLM via headless Playwright, adds it as a source, "
                "types the prompt into the Chat to trigger Video Overview generation, "
                "and returns once generation has started. Run setup_notebooklm first."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "document_text": {
                        "type": "string",
                        "description": "The generated NotebookLM source document text"
                    },
                    "notebooklm_prompt": {
                        "type": "string",
                        "description": "The chat prompt that triggers Video Overview generation"
                    }
                },
                "required": ["document_text", "notebooklm_prompt"]
            }
        ),
    ]


def _parse_args(arguments: dict) -> dict:
    """JSON-parse any string values that should be lists/dicts/numbers (MCP sends them as strings)."""
    out = {}
    for k, v in arguments.items():
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith(("[", "{")):
                try:
                    v = json.loads(stripped)
                except json.JSONDecodeError:
                    pass
        out[k] = v
    return out


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    arguments = _parse_args(arguments)
    if name == "check_setup":
        result = await _check_setup()
    elif name == "prepare_notebooklm_doc":
        result = await _prepare_notebooklm_doc(**arguments)
    elif name == "setup_notebooklm":
        result = await _setup_notebooklm(**arguments)
    elif name == "upload_to_notebooklm":
        result = await _upload_to_notebooklm(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Tool implementations ─────────────────────────────────────────────────────

async def _check_setup() -> dict:
    config_path = BASE_DIR / "notebooklm_config.json"
    session_dir = BASE_DIR / "notebooklm_session"
    has_config = config_path.exists()
    has_session = session_dir.exists() and any(session_dir.iterdir())

    if has_config and has_session:
        config = json.loads(config_path.read_text())

        # Check session TTL
        created_at = config.get("session_created_at")
        if created_at:
            age_seconds = (datetime.now(timezone.utc) - datetime.fromisoformat(created_at)).total_seconds()
            if age_seconds > SESSION_TTL_SECONDS:
                # Wipe session files — they are now obsolete
                shutil.rmtree(session_dir, ignore_errors=True)
                config_path.unlink(missing_ok=True)
                return {
                    "status": "session_expired",
                    "message": (
                        f"Session expired after {int(age_seconds / 60)} minutes. "
                        "All session files have been deleted. "
                        "Call setup_notebooklm(notebook_url=...) to log in again."
                    ),
                }

        return {
            "status": "ready",
            "notebook_url": config.get("notebook_url"),
            "message": "Setup complete. You can call prepare_notebooklm_doc then upload_to_notebooklm.",
        }

    steps = [
        "1. Ask the user for their NotebookLM notebook URL "
        "(format: https://notebooklm.google.com/notebook/<id>).",
        "2. Call setup_notebooklm(notebook_url=<url>). "
        "This opens a Chrome window — tell the user to log in to Google "
        "and press Enter in the terminal when done.",
        "3. Call check_setup again to confirm status=ready, "
        "then proceed with video generation.",
    ]

    return {
        "status": "first_run",
        "message": "NotebookLM is not configured yet. Follow the steps below.",
        "steps": steps,
    }


async def _prepare_notebooklm_doc(
    task_markdown: str,
    tone: str = "neutral",
    target_duration: str = "2min",
) -> dict:
    tone_styles = {
        "interview": (
            "Professional and direct. Address the reader in second person "
            "('You are given...', 'Your task is to...', 'Consider what happens when...'). "
            "Tone is like a technical interviewer reading the problem aloud: precise, no fluff."
        ),
        "explainer": (
            "Warm and narrative. Use first-person plural "
            "('Let's explore...', 'Imagine we have...', 'What would happen if...'). "
            "Tone is like a curious podcast host discovering the problem with the listener."
        ),
        "neutral": (
            "Clear and balanced. Neither interview-formal nor overly casual. "
            "State facts, walk through examples methodically, let the problem speak for itself."
        ),
    }
    style = tone_styles.get(tone, tone_styles["neutral"])

    duration_configs = {
        "1min": {
            "word_target": 250,
            "problem_budget": "2 sentences",
            "example_budget": "1 short paragraph per example",
            "constraint_budget": "bullets only — one line each",
        },
        "2min": {
            "word_target": 500,
            "problem_budget": "1 paragraph",
            "example_budget": "1 paragraph per example",
            "constraint_budget": "1 sentence each",
        },
        "3min": {
            "word_target": 750,
            "problem_budget": "2 paragraphs",
            "example_budget": "2 paragraphs per example",
            "constraint_budget": "1 sentence each",
        },
    }
    cfg = duration_configs.get(target_duration, duration_configs["2min"])

    # Shared strict rules injected into every prompt tier
    _slide_rules = (
        "STRICT SLIDE RULES — follow these exactly: "
        "1. Every single slide MUST contain readable text with substantive information. "
        "2. NO decorative slides, NO graphical-only slides, NO transition slides, NO empty title cards. "
        "3. If a slide would only show a title or an image with no informative text, DELETE it. "
        "4. Viewers must have enough time to read every word on each slide — keep text concise but present. "
        "5. Never repeat the same information across two slides. "
        "6. No solution hints, no algorithm discussion, no complexity analysis. "
    )

    notebooklm_prompts = {
        "1min": (
            "Generate a Video Overview for this problem. Strictly under 1 minute. "
            f"{_slide_rules} "
            "Use EXACTLY 3 slides, no more, no less: "
            "Slide 1 — Problem: what the task asks + what 'balanced' means (with 1 valid and 1 invalid example). "
            "Slide 2 — Example: show S = input, trace balanced substrings, state the answer. "
            "Slide 3 — Task: function signature, constraints, correctness reminder. "
            "Each slide stays on screen ~15-20 seconds. That's it — three dense, readable slides."
        ),
        "2min": (
            "Generate a Video Overview for this problem. Strictly under 2 minutes. "
            f"{_slide_rules} "
            "Use EXACTLY 4 slides, no more, no less: "
            "Slide 1 — Problem: one-sentence summary of what the task asks. "
            "Slide 2 — Definition: what 'balanced' means, 2-3 tiny valid examples, 1 counter-example. "
            "Slide 3 — Example: show the main input, trace through it, highlight the longest balanced substrings, state the answer. "
            "Slide 4 — Task: function signature, constraints, correctness reminder. "
            "Each slide stays on screen ~25-30 seconds. Four dense, readable slides — nothing else."
        ),
        "3min": (
            "Generate a Video Overview for this problem. Strictly under 3 minutes. "
            f"{_slide_rules} "
            "Use EXACTLY 5 slides, no more, no less: "
            "Slide 1 — Problem: one-sentence summary of what the task asks. "
            "Slide 2 — Definition: what the key concept means, with valid examples and a counter-example. "
            "Slide 3 — Example 1: show input, trace through, state output and why. "
            "Slide 4 — Example 2 (if available, otherwise deeper trace of Example 1): show input, trace, state output. "
            "Slide 5 — Task: function signature, all constraints, correctness reminder. "
            "Each slide stays on screen ~30-35 seconds. Five dense, readable slides — nothing else."
        ),
    }
    notebooklm_prompt = notebooklm_prompts.get(target_duration, notebooklm_prompts["2min"])

    prompt = f"""Generate a NotebookLM source document for the coding problem below.
This document will be uploaded to NotebookLM to generate a ~{target_duration} Video Overview.

TONE: {style}

STRICT CONSTRAINTS:
- Target ~{cfg["word_target"]} words total
- Cover ONLY: problem + definition, example walkthrough, function signature + constraints
- DO NOT include: solution approaches, algorithm hints, time/space complexity, patterns to use
- Problem statement + definition: {cfg["problem_budget"]} + 2-3 sentences defining the key concept
- Each example: {cfg["example_budget"]}
- Each constraint: {cfg["constraint_budget"]}

SLIDE ECONOMY — CRITICAL:
- This document drives a video. Each section = one video slide.
- Every section must be dense with information. No padding, no filler.
- Every sentence must teach the viewer something new.
- Do NOT write anything that would produce a decorative or graphical-only slide.
- Do NOT create sections that merely restate a title or contain only a heading.

SOURCE MARKDOWN:
---
{task_markdown}
---

Write the document with EXACTLY these sections (each section = one video slide):

## [Problem Title]: What It Asks
[{cfg["problem_budget"]} stating what the problem asks: input, output, what makes an answer valid.
Then define the key concept (e.g., what "balanced" means). Include 2-3 tiny valid examples
and 1 counter-example inline. All in one dense block — no sub-headings.]

## Example
[For the primary example: {cfg["example_budget"]} — show the input string, trace which substrings
are balanced and why, identify the longest one(s), state the answer. Keep it concrete.]

## Implement: solution(S)
[State the function signature. State constraints inline ({cfg["constraint_budget"]}).
Remind to focus on correctness. 2-3 sentences max. No hints about approach.]

Write the full document now. No markdown fences. Clean prose only."""

    return {
        "status": "prompt_ready",
        "tone": tone,
        "target_duration": target_duration,
        "prompt": prompt,
        "notebooklm_prompt": notebooklm_prompt,
        "instructions": (
            "Execute the prompt above to generate the NotebookLM document. "
            "Then call upload_to_notebooklm(document_text=..., notebooklm_prompt=...) — "
            "Playwright will add the document as a source and type the notebooklm_prompt "
            "into the Chat, which triggers Video Overview generation automatically."
        ),
    }


async def _setup_notebooklm(notebook_url: str) -> dict:
    session_dir = str(BASE_DIR / "notebooklm_session")
    config_path = BASE_DIR / "notebooklm_config.json"
    script = str(BASE_DIR / "notebooklm_playwright.py")

    rc, out, err = run([
        "python", script,
        "--setup",
        "--notebook-url", notebook_url,
        "--session-dir", session_dir,
    ])
    if rc != 0:
        return {"status": "error", "message": err or out}

    config_path.write_text(json.dumps({
        "notebook_url": notebook_url,
        "session_created_at": datetime.now(timezone.utc).isoformat(),
    }))
    return {
        "status": "session_saved",
        "notebook_url": notebook_url,
        "session_dir": session_dir,
        "expires_in_minutes": SESSION_TTL_SECONDS // 60,
    }


async def _upload_to_notebooklm(document_text: str, notebooklm_prompt: str) -> dict:
    setup = await _check_setup()
    if setup["status"] != "ready":
        return setup

    notebook_url = setup["notebook_url"]
    session_dir = str(BASE_DIR / "notebooklm_session")
    script = str(BASE_DIR / "notebooklm_playwright.py")

    rc, out, err = run([
        "python", script,
        "--notebook-url", notebook_url,
        "--session-dir", session_dir,
        "--document-text", document_text,
        "--notebooklm-prompt", notebooklm_prompt,
    ])
    if rc != 0:
        return {"status": "error", "message": err or out}

    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"status": "error", "message": f"Unexpected output: {out}", "stderr": err}


# ── Run ──────────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
