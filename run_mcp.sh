#!/bin/bash
cd "$(dirname "$0")"

# Auto-install dependencies on first run (no manual setup.sh needed)
if [ ! -d venv ]; then
  echo "[video-generator] First run: creating virtual environment..." >&2
  python3 -m venv venv
  source venv/bin/activate
  pip install -q -r requirements.txt
  playwright install chrome >&2
  echo "[video-generator] Dependencies installed." >&2
else
  source venv/bin/activate
fi

exec python mcp_server.py
