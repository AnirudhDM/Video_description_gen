"""
mcp_server.py
MCP server for automated coding task video generation.
No API key needed — Claude Code generates Motion Canvas scenes directly.
"""

import os
import json
import glob
import asyncio
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_DIR   = Path(os.environ.get("POC_DIR", Path.home() / "Desktop/poc")).expanduser()
AUDIO_DIR  = BASE_DIR / "audio"
TMP_DIR    = BASE_DIR / "tmp"
KOKORO_VOICE = "af_nova"
QUALITY    = "qm"

_kokoro_pipeline: "KPipeline | None" = None

server = Server("video-generator")

# ── Helpers ────────────────────────────────────────────────────────────────

def _get_kokoro_pipeline() -> "KPipeline":
    global _kokoro_pipeline
    if _kokoro_pipeline is None:
        _kokoro_pipeline = KPipeline(lang_code="a")  # "a" = American English
    return _kokoro_pipeline

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    return result.returncode, result.stdout, result.stderr

def run_node(cmd, cwd=None):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd or BASE_DIR))
    return result.returncode, result.stdout, result.stderr

PROJECT_TS_TEMPLATE = """\
import {makeProject} from '@motion-canvas/core';
import scene from './scenes/SCENE_NAME?scene';

export default makeProject({
  scenes: [scene],
  audio: AUDIO_PATH,
});
"""

def get_duration(filepath):
    _, out, _ = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ])
    val = out.strip()
    if not val or val == "N/A":
        return round(os.path.getsize(filepath) / 24000 / 2, 3)
    return round(float(val), 3)

def speak_to_file(text, output_wav):
    pipeline = _get_kokoro_pipeline()
    segments = []
    for _, _, audio in pipeline(text, voice=KOKORO_VOICE):
        if audio is not None and len(audio) > 0:
            segments.append(audio)
    if not segments:
        raise Exception(f"Kokoro produced no audio for: {text!r}")
    combined = np.concatenate(segments, axis=0)
    sf.write(output_wav, combined, samplerate=24000, subtype="PCM_16")

# ── Tool registry ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_audio",
            description="Generates TTS wav files for narration lines using Kokoro",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string"},
                    "lines": {"type": ["array", "string"]}
                },
                "required": ["scene_name", "lines"]
            }
        ),
        Tool(
            name="prepare_manim_prompt",
            description="Prepares a detailed prompt for Claude Code to write a Manim scene. Returns the prompt and target file path.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_title": {"type": "string"},
                    "task_description": {"type": "string"},
                    "examples": {"type": ["array", "string"]},
                    "constraints": {"type": ["array", "string"]},
                    "narration_lines": {"type": ["array", "string"]}
                },
                "required": ["task_title", "task_description", "examples", "constraints", "narration_lines"]
            }
        ),
        Tool(
            name="render_scene",
            description="Renders a Manim scene and returns path to output mp4",
            inputSchema={
                "type": "object",
                "properties": {
                    "script_path": {"type": "string"},
                    "scene_name": {"type": "string"}
                },
                "required": ["script_path", "scene_name"]
            }
        ),
        Tool(
            name="stitch_video",
            description="Mixes audio onto each clip then stitches into final mp4",
            inputSchema={
                "type": "object",
                "properties": {
                    "clips": {"type": ["array", "string"]},
                    "output_path": {"type": "string"}
                },
                "required": ["clips", "output_path"]
            }
        ),
        Tool(
            name="generate_task_video",
            description="Full pipeline: generates audio, prompts Claude Code to write Manim script, renders and stitches final mp4",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_title": {"type": "string"},
                    "task_description": {"type": "string"},
                    "difficulty": {"type": "string"},
                    "topic": {"type": "string"},
                    "time_estimate": {"type": "string"},
                    "examples": {"type": ["array", "string"]},
                    "constraints": {"type": ["array", "string"]},
                    "output_path": {"type": "string"}
                },
                "required": ["task_title", "task_description", "difficulty", "topic", "time_estimate", "examples", "constraints"]
            }
        ),
        Tool(
            name="render_motion_canvas",
            description="Renders a Motion Canvas TypeScript scene to mp4",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_tsx_path": {"type": "string"},
                    "audio_path":     {"type": "string"},
                    "output_path":    {"type": "string"}
                },
                "required": ["scene_tsx_path", "audio_path"]
            }
        ),
        Tool(
            name="generate_whiteboard_video",
            description=(
                "Whiteboard pipeline: single scene, no intro/outro, no subtitles. "
                "Generates per-step TTS audio, concatenates to a full WAV, then returns "
                "a Motion Canvas TypeScript prompt for Claude to write a .tsx scene. "
                "Use render_motion_canvas afterwards to render to mp4."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_title":        {"type": "string"},
                    "short_description": {"type": "string", "description": "2-3 sentences max"},
                    "difficulty":        {"type": "string"},
                    "time_estimate":     {"type": "string"},
                    "examples": {
                        "type": ["array", "string"],
                        "items": {
                            "type": "object",
                            "properties": {
                                "input":  {"type": "string"},
                                "output": {"type": "string"},
                                "steps": {
                                    "type": ["array", "string"],
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "narration":       {"type": "string"},
                                            "animation_hint":  {"type": "string"}
                                        },
                                        "required": ["narration", "animation_hint"]
                                    }
                                }
                            },
                            "required": ["input", "output", "steps"]
                        }
                    },
                    "output_path": {"type": "string"}
                },
                "required": ["task_title", "short_description", "difficulty", "time_estimate", "examples"]
            }
        ),
    ]

def _parse_args(arguments: dict) -> dict:
    """JSON-parse any string values that should be lists/dicts (MCP sends arrays as strings)."""
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
    if name == "generate_audio":
        result = await _generate_audio(arguments["scene_name"], arguments["lines"])
    elif name == "prepare_manim_prompt":
        result = await _prepare_manim_prompt(**arguments)
    elif name == "render_scene":
        result = await _render_scene(arguments["script_path"], arguments["scene_name"])
    elif name == "stitch_video":
        result = await _stitch_video(arguments["clips"], arguments["output_path"])
    elif name == "generate_task_video":
        result = await _generate_task_video(**arguments)
    elif name == "generate_whiteboard_video":
        result = await _generate_whiteboard_video(**arguments)
    elif name == "render_motion_canvas":
        result = await _render_motion_canvas(**arguments)
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]

# ── Tool implementations ───────────────────────────────────────────────────

async def _generate_audio(scene_name: str, lines: list) -> dict:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for f in glob.glob(str(AUDIO_DIR / f"{scene_name}_*.wav")):
        if os.path.getsize(f) < 1000:
            os.remove(f)

    timings = []
    for i, line in enumerate(lines):
        wav = str(AUDIO_DIR / f"{scene_name}_{i:02d}.wav")
        if not os.path.exists(wav) or os.path.getsize(wav) < 1000:
            speak_to_file(line, wav)
        duration = get_duration(wav)
        timings.append({"index": i, "text": line, "file": wav, "duration": duration})

    timing_path = AUDIO_DIR / "timing.json"
    existing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
    existing[scene_name] = timings
    timing_path.write_text(json.dumps(existing, indent=2))

    list_file = AUDIO_DIR / f"{scene_name}_list.txt"
    list_file.write_text("\n".join([f"file '{t['file']}'" for t in timings]))

    merged = str(AUDIO_DIR / f"{scene_name}_full.wav")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", merged])

    return {
        "timings": timings,
        "merged_path": merged,
        "total_duration": round(sum(t["duration"] for t in timings), 3)
    }


async def _prepare_manim_prompt(task_title, task_description, examples,
                                 constraints, narration_lines) -> dict:
    class_name  = task_title.replace(" ", "").replace("-", "")
    script_path = BASE_DIR / f"{class_name.lower()}_scene.py"

    prompt = f"""Write a Manim Python scene and save it to: {script_path}

TASK: {task_title}
DESCRIPTION: {task_description}
EXAMPLES: {json.dumps(examples, indent=2)}
CONSTRAINTS: {json.dumps(constraints, indent=2)}
NARRATION LINES: {json.dumps(narration_lines, indent=2)}

STRICT RULES:
- Class name must be exactly: {class_name}
- NEVER use Tex() — always use Text()
- Colors: YELLOW_H="#CCFF00" BG_COLOR="#1a1a2e" BLUE_H="#4FC3F7" GREEN_H="#69F0AE" RED_H="#FF5252" WHITE="#FFFFFF"
- Always start with dark grid background
- Use RoundedRectangle for boxes
- Use VGroup().arrange() for layouts
- LaggedStartMap(FadeIn, group, lag_ratio=0.2) — NO shift argument ever
- Add make_subtitle(self, text) method and show each narration line as subtitle
- Structure: definition then examples then walkthrough then solution spec
- Write ONLY the Python code to the file, no markdown fences
"""

    return {
        "script_path": str(script_path),
        "class_name": class_name,
        "prompt": prompt
    }


async def _render_scene(script_path: str, scene_name: str) -> dict:
    import shutil

    script = Path(script_path)
    if not script.exists():
        return {"error": f"Script not found: {script_path}"}

    rc, out, err = run(["manim", f"-{QUALITY}", str(script), scene_name])
    if rc != 0:
        return {"error": err}

    matches = list(BASE_DIR.glob(f"media/videos/**/{scene_name}.mp4"))
    if not matches:
        return {"error": f"Rendered file not found for: {scene_name}"}

    raw_video = sorted(matches)[-1]
    duration  = get_duration(str(raw_video))

    # Copy rendered video to BASE_DIR root before cleanup
    final_video = BASE_DIR / f"{scene_name}.mp4"
    shutil.copy2(str(raw_video), str(final_video))

    # Cleanup: audio, media cache, and the generated scene script
    for cleanup_dir in [AUDIO_DIR, BASE_DIR / "media", TMP_DIR]:
        if cleanup_dir.exists():
            shutil.rmtree(str(cleanup_dir))
    if script.exists():
        script.unlink()

    return {"video_path": str(final_video), "duration": duration}


async def _stitch_video(clips: list, output_path: str) -> dict:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    mixed = []

    for clip in clips:
        out = str(TMP_DIR / f"{clip['label']}_mixed.mp4")
        rc, _, err = run([
            "ffmpeg", "-y",
            "-i", clip["video_path"],
            "-i", clip["audio_path"],
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            out
        ])
        if rc != 0:
            return {"error": f"Mix failed for {clip['label']}: {err}"}
        mixed.append(out)

    list_file = TMP_DIR / "stitch_list.txt"
    list_file.write_text("\n".join([f"file '{os.path.abspath(c)}'" for c in mixed]))

    rc, _, err = run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path
    ])
    if rc != 0:
        return {"error": f"Stitch failed: {err}"}

    return {"final_path": output_path, "duration": get_duration(output_path)}


async def _render_motion_canvas(scene_tsx_path: str, audio_path: str, output_path: str = None) -> dict:
    import shutil
    mc_dir = BASE_DIR / "motion-canvas"

    if not mc_dir.exists():
        return {"error": f"motion-canvas scaffold not found at {mc_dir}"}

    # Install node_modules on first run
    if not (mc_dir / "node_modules").exists():
        rc, out, err = run_node(["npm", "install"], cwd=mc_dir)
        if rc != 0:
            return {"error": f"npm install failed: {err}"}

    scene_name = Path(scene_tsx_path).stem
    final = Path(output_path) if output_path else BASE_DIR / f"{scene_name}.mp4"

    # Write project.ts with correct scene + audio references
    project_ts = mc_dir / "src" / "project.ts"
    audio_literal = json.dumps(str(Path(audio_path).expanduser().resolve()))
    project_ts.write_text(
        PROJECT_TS_TEMPLATE
        .replace("SCENE_NAME", scene_name)
        .replace("AUDIO_PATH", audio_literal)
    )

    # Copy scene file into motion-canvas/src/scenes/
    scenes_dir = mc_dir / "src" / "scenes"
    scenes_dir.mkdir(parents=True, exist_ok=True)
    source = Path(scene_tsx_path).expanduser().resolve()
    dest = (scenes_dir / f"{scene_name}.tsx").resolve()
    if source != dest:
        shutil.copy2(str(source), str(dest))

    # Render via Puppeteer (drives the Vite dev server headlessly)
    # argv: scene_name, audio_path (or "" if none), output_mp4_path
    rc, out, err = run_node(
        ["node", str(mc_dir / "headless-render.mjs"),
         scene_name,
         audio_path,
         str(final)],
        cwd=mc_dir
    )
    if rc != 0:
        return {"error": err or out}

    if not final.exists():
        return {"error": f"Output mp4 not found at {final}. stderr: {err}"}

    return {"video_path": str(final), "duration": get_duration(str(final))}


async def _generate_task_video(task_title, task_description, difficulty, topic,
                                time_estimate, examples, constraints,
                                output_path=None) -> dict:
    snake      = task_title.lower().replace(" ", "_").replace("-", "_")
    out        = output_path or str(BASE_DIR / f"{snake}.mp4")
    class_name = task_title.replace(" ", "").replace("-", "")
    log        = []

    narration = {
        "intro": [
            f"Hello and welcome! Today we are solving {task_title}.",
            f"This is a {difficulty} difficulty problem on {topic}. Estimated time is {time_estimate}.",
            "Let us get started!",
        ],
        "explanation": (
            [task_description] +
            [f"For example, {e['input']} gives us {e['output']}." for e in examples] +
            [f"Constraint: {c}." for c in constraints]
        ),
        "outro": [
            f"Let us recap {task_title}.",
            f"This was a {difficulty} problem on {topic}.",
            "Remember to consider edge cases and efficiency.",
            "Good luck!",
        ]
    }

    # Step 1 — Audio first
    log.append("Generating audio...")
    for scene, lines in narration.items():
        result = await _generate_audio(scene_name=scene, lines=lines)
        log.append(f"  {scene}: {result['total_duration']}s")

    # Step 2 — Ask Claude Code to write the Manim script
    log.append("Preparing Manim script prompt for Claude Code...")
    prompt_result = await _prepare_manim_prompt(
        task_title=task_title,
        task_description=task_description,
        examples=examples,
        constraints=constraints,
        narration_lines=narration["explanation"]
    )
    log.append(f"  Script path: {prompt_result['script_path']}")
    log.append("  ACTION NEEDED: Claude Code must write the Manim script using the prompt above before rendering.")

    return {
        "status": "audio_ready_script_needed",
        "log": log,
        "next_step": prompt_result["prompt"],
        "script_path": prompt_result["script_path"],
        "class_name": class_name,
        "render_instructions": {
            "intro":  f"render_scene(script_path='{BASE_DIR}/intro_outro_synced.py', scene_name='IntroScene')",
            "explanation": f"render_scene(script_path='{prompt_result['script_path']}', scene_name='{class_name}')",
            "outro":  f"render_scene(script_path='{BASE_DIR}/intro_outro_synced.py', scene_name='OutroScene')",
            "stitch": f"stitch_video(clips=[...], output_path='{out}')"
        }
    }

async def _generate_whiteboard_video(
    task_title, short_description, difficulty, time_estimate,
    examples, output_path=None
) -> dict:
    """
    Whiteboard pipeline (single scene, Motion Canvas):
    1. Flatten all example steps into one narration sequence.
    2. Generate TTS audio for each step + concat to full WAV.
    3. Compute cumulative audio offsets for each step.
    4. Return a Motion Canvas TypeScript prompt for Claude to write the scene.
    """
    snake      = task_title.lower().replace(" ", "_").replace("-", "_")
    scene_path = BASE_DIR / "motion-canvas" / "src" / "scenes" / f"{snake}.tsx"
    out        = output_path or str(BASE_DIR / f"{snake}.mp4")
    timing_key = snake

    # Flatten steps across all examples into a single ordered list
    all_steps = []
    for ex in examples:
        for step in ex.get("steps", []):
            all_steps.append({
                "narration":      step["narration"],
                "animation_hint": step.get("animation_hint", ""),
                "example_input":  ex["input"],
                "example_output": ex["output"],
            })

    if not all_steps:
        return {"error": "examples must contain at least one step"}

    # Generate audio for every step (also produces {timing_key}_full.wav)
    narration_lines = [s["narration"] for s in all_steps]
    audio_result = await _generate_audio(scene_name=timing_key, lines=narration_lines)
    timings = audio_result["timings"]   # [{index, text, file, duration}, ...]
    full_audio = audio_result["merged_path"]

    # Attach timing + cumulative audio offset onto each step
    offset = 0.0
    for i, step in enumerate(all_steps):
        step["duration"]     = timings[i]["duration"]
        step["audio_offset"] = round(offset, 3)
        offset += step["duration"] + 1.5  # 1.5s silent pause per step

    # Build the Motion Canvas prompt
    prompt_result = _prepare_whiteboard_prompt(
        task_title, short_description, difficulty, time_estimate,
        examples, all_steps, scene_path
    )

    return {
        "status": "audio_ready_scene_needed",
        "scene_path": str(scene_path),
        "full_audio_path": full_audio,
        "audio_total": audio_result["total_duration"],
        "next_step": prompt_result["prompt"],
        "render_instruction": (
            f"Call render_motion_canvas with:\n"
            f"  scene_tsx_path: \"{scene_path}\"\n"
            f"  audio_path: \"{full_audio}\"\n"
            f"  output_path: \"{out}\""
        ),
        "final_path": out,
    }


def _wrap(text: str, max_chars: int = 32) -> str:
    """Word-wrap a string so no line exceeds max_chars (for Manim Text)."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _prepare_whiteboard_prompt(
    task_title, short_description, difficulty, time_estimate,
    examples, all_steps, scene_path
) -> dict:
    title_safe = title_wrapped = _wrap(task_title, max_chars=20)
    desc_wrapped = _wrap(short_description, max_chars=36)

    steps_spec = "\n".join(
        f"  Step {i}:\n"
        f"    narration:       \"{s['narration']}\"\n"
        f"    animation_hint:  \"{s['animation_hint']}\"\n"
        f"    audio_offset:    {s['audio_offset']}s  // cumulative offset into full audio track\n"
        f"    duration:        {s['duration']}s"
        for i, s in enumerate(all_steps)
    )

    examples_spec = "\n".join(
        f"  Example {i+1}: input={ex['input']}  output={ex['output']}"
        for i, ex in enumerate(examples)
    )

    prompt = f"""Write a Motion Canvas TypeScript scene and save it to: {scene_path}

This is a Motion Canvas 2D scene (.tsx). Use @motion-canvas/2d and @motion-canvas/core.

═══ SCENE STRUCTURE ══════════════════════════════════════════════════
The audio is a single full-track WAV baked into project.ts — do NOT
import or reference audio files inside the scene. All audio sync is
done via waitFor() matching cumulative offsets.

Import pattern:
  import {{makeScene2D, Layout, Rect, Txt, Line, Circle}} from '@motion-canvas/2d';
  import {{all, sequence, waitFor, chain, createRef, createSignal, easeInOutCubic}} from '@motion-canvas/core';

Scene export:
  export default makeScene2D(function* (view) {{
    // set background
    view.fill('#1a1a2e');
    // scene content...
  }});

═══ LAYOUT & VISUAL DESIGN ════════════════════════════════════════════
Colors:
  YELLOW = '#CCFF00'   BG     = '#1a1a2e'   CARD   = '#16213e'
  BLUE   = '#4FC3F7'   GREEN  = '#69F0AE'   RED    = '#FF5252'
  ORANGE = '#FFB74D'   MUTED  = '#666688'   WHITE  = '#FFFFFF'

Layout system: Motion Canvas uses flexbox-style props on Layout nodes.
  <Layout direction="column" gap={{16}} padding={{24}} layout>

Text uses Txt component (NOT Text — this is TypeScript/JSX):
  <Txt text="{title_safe}" fontSize={{32}} fill="{{'#CCFF00'}}" fontWeight={{700}} />

Cards/boxes use Rect:
  <Rect width={{320}} height={{48}} radius={{8}} fill="{{'#16213e'}}" stroke="{{'#4FC3F7'}}" lineWidth={{1.5}}>

Subtle grid: add a large Rect with dashed stroke at opacity 0.04 as background decoration.

═══ TWO-PHASE LAYOUT ══════════════════════════════════════════════════
Phase 1 — INTRO (full-screen, centered):
  While Step 0 audio plays, fade in one by one:
    1. Title Txt — fontSize 36, fill YELLOW, fontWeight 700, y=-120
    2. Signature Rect chip — centered at y=-30 (Txt inside: "solution(...) → ...")
    3. Description Txt lines — centered, fontSize 18, y=60 area
    4. "e.g." label + example snippets fading in below

Phase 2 — LAYOUT TRANSITION (use waitFor(1) between phases):
  yield* all(...refs.map(r => r().opacity(0, 0.5)));  // fade out intro
  // fade in: vertical divider Line at x=-160, left panel, right panel header

═══ LEFT PANEL (static after transition) ══════════════════════════════
A Layout node anchored left, direction="column", gap=16, x=-520, y=30.
Elements (top to bottom):
  1. Title Txt — fontSize 24, fill YELLOW, fontWeight 700
     text: "{title_wrapped}"
  2. Description Txt — fontSize 14, fill WHITE
     text: "{desc_wrapped}"
  3. Signature chip Rect — fill CARD, stroke BLUE, lineWidth 1.2
     Txt inside: fontSize 14, fill BLUE
  4. Example calls Txt — fontSize 12, fill MUTED, one per example

═══ RIGHT PANEL (walkthrough) ══════════════════════════════════════════
Examples reference:
{examples_spec}

Use createRef() for every animated element. Build elements for each step,
starting hidden (opacity 0 or scale 0), then animate them in per step.

Suggested y positions (right panel x≈200):
  Section header : y = -260
  Input row      : y = -160
  Working area   : y = -60 to 120
  Result chip    : y =  220

═══ AUDIO SYNC PATTERN — FOLLOW EXACTLY ════════════════════════════════
The full audio track plays automatically from project.ts.
Use waitFor(offset) to jump to the correct timestamp before each step's
animations, so visuals stay locked to narration.

Template for each step:
  // Step N — <narration summary>
  // audio_offset: Xs — animations must START at this point in time
  // We arrive here at cumulative time = Xs, so no extra waitFor needed
  // if prior steps consumed exactly their allocated time.
  // Use: yield* all(animation1, animation2) → takes animDuration seconds
  // Then: yield* waitFor(stepDuration - animDuration) to fill remaining
  // Then: yield* waitFor(1.5) for the silent pause between steps

  yield* all(
    yourRef().opacity(1, 0.5),
    yourRef().scale(1, 0.4),
  );
  yield* waitFor(Math.max(stepDuration - animDuration, 0.1));
  yield* waitFor(1.5);  // silent pause — EVERY step, no exceptions

═══ STEPS ═════════════════════════════════════════════════════════════
{steps_spec}

═══ STRICT RULES ══════════════════════════════════════════════════════
- File extension is .tsx — use JSX/TSX syntax, NOT Python
- Use Txt (not Text) — Txt is the Motion Canvas 2D text primitive
- Use Rect (not RoundedRectangle) with radius={{8}} for cards
- NO subtitles, captions, or voiced text overlaid on screen
- NO "CODING TASK" tag, NO difficulty/time pill badges
- All animated refs use createRef<NodeType>()
- Wrap multi-line text in Txt with maxWidth prop
- Import only from '@motion-canvas/2d' and '@motion-canvas/core'
- Write ONLY the TypeScript/TSX file content — no markdown fences
- The scene must export default makeScene2D(...)
"""
    return {"prompt": prompt}


# ── Run ────────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())