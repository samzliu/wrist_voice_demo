#!/bin/bash
# Start both the web server and LiveKit agent in one process group.
# Web server serves static frontend + API routes on $PORT.
# Agent connects outbound to LiveKit Cloud.

set -e

PORT="${PORT:-8080}"

# Use venv if it exists (uv installs there)
if [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

# Start web server FIRST so Render health check passes
uvicorn src.server:app --host 0.0.0.0 --port "$PORT" &
WEB_PID=$!

# Download turn detector model, then start agent
python -m src.agent download-files 2>/dev/null || true
python -m src.agent start &
AGENT_PID=$!

# If either exits, kill the other
trap "kill $WEB_PID $AGENT_PID 2>/dev/null" EXIT
wait -n
kill $WEB_PID $AGENT_PID 2>/dev/null
