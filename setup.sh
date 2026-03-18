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

echo ""
echo "Done! Next steps:"
echo "  1. Copy .env.example to .env and fill in your NOTEBOOKLM_URL"
echo "  2. Run ./setup_notebooklm.sh to log in with your Google account"
echo "  3. Open this folder in Claude Code — the MCP server auto-loads via .mcp.json"
