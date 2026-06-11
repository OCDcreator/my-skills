#!/bin/bash
# Thin wrapper: delegates to Python core logic.
# The canonical implementation lives in scripts/update_external.py.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

if command -v python3 >/dev/null 2>&1; then
    python3 scripts/update_external.py "$@"
elif command -v python >/dev/null 2>&1; then
    python scripts/update_external.py "$@"
else
    echo "ERROR: Python is required but not found."
    echo "Please install Python 3 and try again."
    exit 1
fi
