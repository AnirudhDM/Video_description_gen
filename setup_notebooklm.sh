#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "Error: .env file not found. Copy .env.example to .env and set NOTEBOOKLM_URL."
  exit 1
fi

source .env

if [ -z "$NOTEBOOKLM_URL" ]; then
  echo "Error: NOTEBOOKLM_URL is not set in .env"
  exit 1
fi

source venv/bin/activate

echo "Opening Chrome for Google login..."
echo "Log in to your Google account in the browser that opens, then press Enter here."
echo ""

python notebooklm_playwright.py \
  --setup \
  --notebook-url "$NOTEBOOKLM_URL" \
  --session-dir "$(pwd)/notebooklm_session"

# Write notebooklm_config.json so the MCP tool knows the URL
python -c "
import json
from pathlib import Path
Path('notebooklm_config.json').write_text(json.dumps({'notebook_url': '$NOTEBOOKLM_URL'}))
print('Config saved.')
"

echo ""
echo "Setup complete. You can now use upload_to_notebooklm in Claude Code."
