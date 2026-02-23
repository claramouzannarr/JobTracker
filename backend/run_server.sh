#!/bin/bash
cd "$(dirname "$0")"
[ -d venv ] && source venv/bin/activate
PORT="${BACKEND_PORT:-8000}"
uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
