"""
run_backend.py — Production entrypoint for Render / any platform.

Resolves the src/ package root regardless of working directory or
how Render nests the repo, then starts uvicorn programmatically.
"""
import os
import sys
from pathlib import Path

# __file__ is always reliable for locating the script itself.
# This file lives at <repo_root>/src/run_backend.py, so its parent IS src/.
THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parent  # the directory that contains backend/, data/, llm/

# Insert src/ at the front of sys.path so all sibling packages resolve
for p in [str(SRC_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Also change cwd to src/ so relative file loads (e.g. sample_faers.json) work
os.chdir(SRC_DIR)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        workers=int(os.environ.get("WEB_CONCURRENCY", 1)),
    )
