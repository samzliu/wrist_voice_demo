#!/bin/bash
set -e

PORT="${PORT:-8080}"

# Use venv if it exists (uv installs there)
if [ -d ".venv/bin" ]; then
    export PATH=".venv/bin:$PATH"
fi

# Ensure src is importable
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

# Start Next.js on the public port (serves frontend + API routes)
cd web && PORT="$PORT" npx next start -p "$PORT" &
WEB_PID=$!
cd ..

# Download turn detector model, then start LiveKit agent
python -m src.agent download-files 2>/dev/null || true
python -m src.agent start &
AGENT_PID=$!

# If either exits, kill the other
trap "kill $WEB_PID $AGENT_PID 2>/dev/null" EXIT
wait -n
kill $WEB_PID $AGENT_PID 2>/dev/null
