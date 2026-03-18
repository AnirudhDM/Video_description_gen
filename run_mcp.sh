#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
exec python mcp_server.py
