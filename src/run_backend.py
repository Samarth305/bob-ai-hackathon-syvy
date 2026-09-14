"""
run_backend.py — Production entrypoint for Render / any platform.

Must be run from inside the src/ directory:
    cd src && python run_backend.py

Adds the current working directory (src/) to sys.path so that
backend, data, and llm packages are importable as top-level modules.
"""
import os
import sys

# Add cwd (src/) to path — works regardless of how Render resolves __file__
if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        workers=int(os.environ.get("WEB_CONCURRENCY", 1)),
    )
