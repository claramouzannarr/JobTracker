#!/bin/bash
# Run the FastAPI server with proper reload exclusions
# This script excludes venv and other unnecessary directories from file watching
cd "$(dirname "$0")"
source venv/bin/activate

# Only watch Python files in the app directory
# This explicitly excludes venv and other directories
uvicorn app.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --reload-include "app/*.py" \
    --reload-include "app/**/*.py"
