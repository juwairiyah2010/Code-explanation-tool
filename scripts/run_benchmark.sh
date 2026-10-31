#!/usr/bin/env bash
# Script to run the automated evaluation benchmark for Code Lore
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

PYTHON_BIN=".venv/bin/python"
if [ ! -f "$PYTHON_BIN" ]; then
    PYTHON_BIN="python3"
fi

echo "=========================================================="
echo "  Running Code Lore Evaluation Benchmark Suite..."
echo "=========================================================="

$PYTHON_BIN -m evaluation.runner "$@"
