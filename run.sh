#!/usr/bin/env bash
# run.sh — macOS / Linux shortcut for the Drug Safety app launcher
# Usage:  ./run.sh          (start)
#         ./run.sh --check  (pre-flight check)
#         ./run.sh --stop   (stop running instances)
#
# Make executable once:  chmod +x run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python run.py "$@"
