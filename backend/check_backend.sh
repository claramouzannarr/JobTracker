#!/bin/bash
# Quick check: is the backend up?
curl -s http://127.0.0.1:8000/api/health && echo "" || echo "Backend not responding on port 8000"
