"""
run_backend.py — Production entrypoint for Render / any platform.

Adds src/ to sys.path so that backend, data, llm packages are importable,
then starts uvicorn programmatically.
"""
import os
import sys
from pathlib import Path

# Ensure the src/ directory is on sys.path so all sibling packages resolve
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        workers=int(os.environ.get("WEB_CONCURRENCY", 1)),
    )
