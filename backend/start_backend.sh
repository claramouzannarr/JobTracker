#!/bin/bash
# Start the backend. Run from project root: ./backend/start_backend.sh
# Uses BACKEND_PORT env (default 8000). For port 8080: BACKEND_PORT=8080 ./backend/start_backend.sh
cd "$(dirname "$0")"
PORT="${BACKEND_PORT:-8000}"
echo "Starting backend on 0.0.0.0:$PORT"
uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
