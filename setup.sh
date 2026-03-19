#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

echo "Installing Playwright Chrome..."
playwright install chrome

# ── Generate IDE config files ─────────────────────────────────────────────────

echo "Generating IDE config files..."

# VS Code / GitHub Copilot / Cursor / Windsurf
mkdir -p .vscode
cat > .vscode/mcp.json << 'EOF'
{
  "servers": {
    "video-generator": {
      "type": "stdio",
      "command": "${workspaceFolder}/run_mcp.sh"
    }
  }
}
EOF

# Claude Code bonus — auto-calls check_setup at session start
cat > CLAUDE.md << 'EOF'
# NotebookLM Video Generator

At the start of every session, call `check_setup` before anything else.
- If it returns `status=ready`, proceed directly to video generation.
- If it returns `status=first_run`, follow the steps it provides to complete one-time setup.

## Video generation workflow
1. `check_setup` — confirm ready
2. `prepare_notebooklm_doc(task_markdown=..., tone=..., target_duration=...)` — generate source doc
3. Execute the returned `prompt` to write the NotebookLM document
4. `upload_to_notebooklm(document_text=..., notebooklm_prompt=...)` — upload and trigger Video Overview
5. Open the returned `notebook_url` to watch or download the video
EOF

echo ""
echo "Done! Next steps:"
echo "  1. Copy .env.example to .env and set NOTEBOOKLM_URL=<your-notebook-url>"
echo "  2. Run ./setup_notebooklm.sh to log in with your Google account (one-time)"
echo "  3. Open this folder in your agentic IDE — MCP server loads automatically"
echo "     Claude Code  → .mcp.json"
echo "     VS Code/Cursor/Windsurf → .vscode/mcp.json"
