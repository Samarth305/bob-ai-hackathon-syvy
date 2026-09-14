"""
run_backend.py — Production entrypoint for Render.

Sets PYTHONPATH and app_dir so uvicorn worker processes can also
resolve backend/, data/, llm/ as top-level packages.
"""
import os
import sys
from pathlib import Path

# The directory that contains backend/, data/, llm/
SRC_DIR = str(Path(__file__).resolve().parent)

# Set PYTHONPATH so subprocess workers inherit the correct path
os.environ["PYTHONPATH"] = SRC_DIR

# Also add to current process sys.path
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

os.chdir(SRC_DIR)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=port,
        app_dir=SRC_DIR,
        workers=1,
    )
