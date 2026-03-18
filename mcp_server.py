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
import subprocess
import asyncio
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_DIR = Path(__file__).parent

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
    if name == "prepare_notebooklm_doc":
        result = await _prepare_notebooklm_doc(**arguments)
    elif name == "setup_notebooklm":
        result = await _setup_notebooklm(**arguments)
    elif name == "upload_to_notebooklm":
        result = await _upload_to_notebooklm(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ── Tool implementations ─────────────────────────────────────────────────────

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

    notebooklm_prompts = {
        "1min": (
            "Generate a Video Overview for this problem. Keep it strictly under 1 minute. "
            "Cover only: one sentence on what the problem asks, then walk through example 1 only — "
            "state the input, state the output, confirm it matches the definition. "
            "End with 1 sentence reminding the candidate to implement the solution function in the "
            "provided file. No solution hints, no algorithm discussion."
        ),
        "2min": (
            "Generate a Video Overview for this problem. Keep it strictly under 2 minutes. "
            "Cover only: a brief introduction to what the problem asks (2-3 sentences), "
            "then walk through each example — state the input, state the output, explain why "
            "it's correct per the problem definition only (not any algorithm). "
            "End with 1-2 sentences directed at the candidate: remind them to implement the "
            "solution function in the provided file and focus on correctness across all constraint "
            "ranges. Do not explain any solution approach."
        ),
        "3min": (
            "Generate a Video Overview for this problem. Keep it under 3 minutes. "
            "Cover: what the problem asks, all examples with input/output walkthroughs, "
            "the constraints as plain facts, and a closing reminder to implement the solution "
            "function in the provided file. No solution hints, no algorithm discussion."
        ),
    }
    notebooklm_prompt = notebooklm_prompts.get(target_duration, notebooklm_prompts["2min"])

    prompt = f"""Generate a NotebookLM source document for the coding problem below.
This document will be uploaded to NotebookLM to generate a ~{target_duration} Video Overview.

TONE: {style}

STRICT CONSTRAINTS:
- Target ~{cfg["word_target"]} words total
- Cover ONLY: problem description, examples walkthrough, constraints, implementation callout
- DO NOT include: solution approaches, algorithm hints, time/space complexity, patterns to use
- Problem statement: {cfg["problem_budget"]}
- Each example: {cfg["example_budget"]}
- Each constraint: {cfg["constraint_budget"]}

SOURCE MARKDOWN:
---
{task_markdown}
---

Write the document with exactly these sections:

## [Problem Title]: Understanding the Challenge

### What You're Being Asked
[{cfg["problem_budget"]} in the chosen tone. What does the problem ask for? What is the input?
What is the output? What makes a valid answer? Be concrete — no solution hints.]

### Walking Through the Examples
[For EACH example in the markdown: {cfg["example_budget"]} tracing the input,
stating the expected output, and explaining WHY that output is correct per the problem
definition — NOT in terms of any algorithm.]

### The Rules of the Game
[For each constraint: {cfg["constraint_budget"]} about what it means in practice.
Do NOT say what algorithm that suggests.]

### Your Task
[1-2 sentences in the chosen tone: name the exact function signature the candidate must implement,
tell them to write it in the provided solution file, and remind them to handle all constraint
ranges correctly. No hints about how to solve it.]

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

    config_path.write_text(json.dumps({"notebook_url": notebook_url}))
    return {
        "status": "session_saved",
        "notebook_url": notebook_url,
        "session_dir": session_dir,
    }


async def _upload_to_notebooklm(document_text: str, notebooklm_prompt: str) -> dict:
    config_path = BASE_DIR / "notebooklm_config.json"
    if not config_path.exists():
        return {
            "status": "error",
            "message": "Run setup_notebooklm first to configure notebook URL and session.",
        }

    config = json.loads(config_path.read_text())
    notebook_url = config["notebook_url"]
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
