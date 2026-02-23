#!/bin/bash
# Start backend, then frontend. Uses port 8000 for backend, 3000 for frontend.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
sleep 3
cd "$ROOT/frontend"
npm run dev
