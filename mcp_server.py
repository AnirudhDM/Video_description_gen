"""
mcp_server.py
MCP server for automated coding task video generation.
No API key needed — Claude Code generates Manim scripts directly.
"""

import os
import json
import time
import glob
import asyncio
import subprocess
from pathlib import Path

import pyttsx3
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

BASE_DIR   = Path(os.environ.get("POC_DIR", Path.home() / "Desktop/poc")).expanduser()
AUDIO_DIR  = BASE_DIR / "audio"
TMP_DIR    = BASE_DIR / "tmp"
VOICE_NAME = "com.apple.voice.compact.en-US.Samantha"
VOICE_RATE = 140
QUALITY    = "qm"

server = Server("video-generator")

# ── Helpers ────────────────────────────────────────────────────────────────

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    return result.returncode, result.stdout, result.stderr

def get_duration(filepath):
    _, out, _ = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ])
    val = out.strip()
    if not val or val == "N/A":
        return round(os.path.getsize(filepath) / 22050 / 2, 3)
    return round(float(val), 3)

def speak_to_file(text, output_wav):
    aiff = output_wav.replace(".wav", ".aiff")
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    selected = None
    for v in voices:
        if VOICE_NAME in v.id:
            selected = v.id
            break
    if not selected:
        for v in voices:
            if "en" in v.id.lower():
                selected = v.id
                break
    if selected:
        engine.setProperty("voice", selected)
    engine.setProperty("rate", VOICE_RATE)
    engine.setProperty("volume", 1.0)
    engine.save_to_file(text, aiff)
    engine.runAndWait()
    engine.stop()
    del engine
    time.sleep(0.8)
    if not os.path.exists(aiff) or os.path.getsize(aiff) < 1000:
        raise Exception(f"aiff empty: {aiff}")
    run(["ffmpeg", "-y", "-i", aiff, "-ar", "22050", "-ac", "1", output_wav])
    if os.path.exists(aiff):
        os.remove(aiff)

# ── Tool registry ──────────────────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="generate_audio",
            description="Generates TTS wav files for narration lines using pyttsx3",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_name": {"type": "string"},
                    "lines": {"type": "array", "items": {"type": "string"}}
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
                    "examples": {"type": "array"},
                    "constraints": {"type": "array"},
                    "narration_lines": {"type": "array"}
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
                    "clips": {"type": "array"},
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
                    "examples": {"type": "array"},
                    "constraints": {"type": "array"},
                    "output_path": {"type": "string"}
                },
                "required": ["task_title", "task_description", "difficulty", "topic", "time_estimate", "examples", "constraints"]
            }
        ),
        Tool(
            name="generate_whiteboard_video",
            description=(
                "New whiteboard pipeline: single scene, no intro/outro, no subtitles. "
                "Generates per-step TTS audio, then returns a precise Manim prompt for "
                "Claude to write a WhiteboardScene with audio baked in via add_sound(). "
                "One render pass produces the final synced mp4."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "task_title":        {"type": "string"},
                    "short_description": {"type": "string", "description": "2-3 sentences max"},
                    "difficulty":        {"type": "string"},
                    "time_estimate":     {"type": "string"},
                    "examples": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "input":  {"type": "string"},
                                "output": {"type": "string"},
                                "steps": {
                                    "type": "array",
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

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
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
    New whiteboard pipeline (single scene, audio baked in):
    1. Flatten all example steps into one narration sequence.
    2. Generate TTS audio for each step.
    3. Return a precise Manim prompt for Claude to write WhiteboardScene.py.
    """
    snake      = task_title.lower().replace(" ", "_").replace("-", "_")
    script_path = BASE_DIR / f"{snake}_whiteboard.py"
    out        = output_path or str(BASE_DIR / f"{snake}_whiteboard.mp4")
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

    # Generate audio for every step
    narration_lines = [s["narration"] for s in all_steps]
    audio_result = await _generate_audio(scene_name=timing_key, lines=narration_lines)
    timings = audio_result["timings"]   # [{index, text, file, duration}, ...]

    # Attach timing data back onto each step
    for i, step in enumerate(all_steps):
        step["wav"]      = timings[i]["file"]
        step["duration"] = timings[i]["duration"]

    # Build the Manim prompt
    prompt_result = _prepare_whiteboard_prompt(
        task_title, short_description, difficulty, time_estimate,
        examples, all_steps, script_path
    )

    return {
        "status": "audio_ready_script_needed",
        "script_path": str(script_path),
        "class_name": "WhiteboardScene",
        "audio_total": audio_result["total_duration"],
        "next_step": prompt_result["prompt"],
        "render_instruction": (
            f"manim -qm {script_path} WhiteboardScene  "
            f"# output will be in media/videos/.../WhiteboardScene.mp4"
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
    examples, all_steps, script_path
) -> dict:
    title_wrapped = _wrap(task_title, max_chars=20)
    desc_wrapped  = _wrap(short_description, max_chars=32)

    steps_spec = "\n".join(
        f"  Step {s['index'] if 'index' in s else i}:\n"
        f"    narration:      \"{s['narration']}\"\n"
        f"    animation_hint: \"{s['animation_hint']}\"\n"
        f"    wav:            \"{s['wav']}\"\n"
        f"    duration:       {s['duration']}s"
        for i, s in enumerate(all_steps)
    )

    examples_spec = "\n".join(
        f"  Example {i+1}: input={ex['input']}  output={ex['output']}"
        for i, ex in enumerate(examples)
    )

    prompt = f"""Write a Manim Python scene and save it to: {script_path}

CLASS NAME: WhiteboardScene

═══ OPENING — BOARD STARTS COMPLETELY EMPTY ══════════════════════════
The scene must open on a blank dark screen. No left panel, no divider,
no labels. Build up content gradually so the viewer is never overwhelmed.

Phase 1 — INTRO (full-screen, centered, no split layout yet):
  Play Step 0 audio while these elements appear one by one:
    1. Title: Text("{title_wrapped}", font_size=34, color=YELLOW, weight=BOLD)
              move_to([0, 2.5, 0])
    2. Function signature chip centered at [0, 1.5, 0]
              RoundedRectangle(w=5.4, h=0.58) + Text("solution(...) → ...", font_size=20, color=BLUE)
    3. Description lines, each appearing separately, centered around y=0.4
    4. "e.g." label + example calls, each fading in one at a time, y=-0.6 downward

Phase 2 — LAYOUT TRANSITION (silent, ~1s):
  Fade out all intro elements, then fade in:
    - Vertical divider at x=-1.3
    - Left panel (see LEFT PANEL spec below)
  After this transition the split layout is used for the rest of the scene.

═══ LEFT PANEL (static after transition) ═════════════════════════════
Build as a single VGroup, arranged DOWN buff=0.42, aligned_edge=LEFT,
then move_to([-4.1, 0.3, 0]).  Fade in with run_time=0.7.

Elements (top to bottom) — NO "CODING TASK" tag, NO difficulty/time pills:
1. Title
     Text("{title_wrapped}", font_size=26, color=YELLOW, weight=BOLD, line_spacing=1.25)

2. Description
     Text("{desc_wrapped}", font_size=16, color=WHITE, line_spacing=1.3)

3. Function signature chip
     RoundedRectangle(w=4.8, h=0.48, color=BLUE, fill_color="#16213e", fill_opacity=0.95, stroke_width=1.2)
     Text("solution(...) → ...", font_size=16, color=BLUE) centered on rect

4. Example calls (small, muted)
     One Text() per example call, font_size=13, color=MUTED ("#666688")
     Arranged DOWN buff=0.15, aligned_edge=LEFT

═══ RIGHT PANEL (walkthrough) ════════════════════════════════════════
Show the examples being walked through step by step.

Examples reference:
{examples_spec}

Suggested Y positions (right panel, adjust if content overflows):
  Section header : y =  3.2
  Input row      : y =  2.1   (label + letter boxes)
  Second row     : y =  1.3
  Table / chips  : y =  0.4 downward
  Notes          : y = -2.85
  Result chip    : y = -3.1

═══ SYNC PATTERN — FOLLOW THIS EXACTLY FOR EVERY STEP ═══════════════
For each step call self.add_sound(wav) BEFORE running any animation.
Animate + wait so total time equals the audio duration.
After EVERY step's audio finishes, add a 1.5s silent pause before the next step.

Template:
    # Step N — <narration summary>
    if os.path.exists("<wav>"):
        self.add_sound("<wav>")          # ALWAYS before self.play / self.wait
    self.play(YourAnimation(), run_time=X)
    self.wait(max(<duration> - X, 0.05))  # fill remaining audio time
    self.wait(1.5)                        # 1.5s silent pause — EVERY step, no exceptions

═══ STEPS ════════════════════════════════════════════════════════════
{steps_spec}

═══ STRICT RULES ════════════════════════════════════════════════════
- NEVER use Tex() — always Text()
- NO subtitles, captions, or voiced text overlaid on screen
- NO "CODING TASK" tag and NO difficulty/time pill badges anywhere
- All right-panel Text() objects: call .set_max_width(6.2)
- Use RoundedRectangle for all chip/card/box shapes
- Subtle grid (stroke_width=0.3, color="#ffffff05") added at the very start and kept throughout
- Colors:
    YELLOW = "#CCFF00"   BG     = "#1a1a2e"   CARD   = "#16213e"
    BLUE   = "#4FC3F7"   GREEN  = "#69F0AE"   RED    = "#FF5252"
    ORANGE = "#FFB74D"   MUTED  = "#666688"   WHITE  = "#FFFFFF"
- digit_box(char, color, scale=0.72):
    RoundedRectangle + Text(char) centered, fill_color=CARD, fill_opacity=0.95
- count_chip(label, value, note, color):
    RoundedRectangle(w=3.1, h=0.58) + Text(f"{{label}}:  {{value}}  ({{note}})")
    .set_max_width(2.9) centered
- import os at the top (needed for os.path.exists wav check)
- Write ONLY the Python file content, no markdown fences
"""
    return {"prompt": prompt}


# ── Run ────────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())