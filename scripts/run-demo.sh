#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  echo 'Run bash scripts/setup.sh first.'
  exit 1
fi
echo 'Bus EDS demo: http://127.0.0.1:8000'
echo 'Wait for Models ready. Press Ctrl+C in this terminal to stop the server.'
export TOKENIZERS_PARALLELISM=false
exec .venv/bin/python -m uvicorn demo.app:app --host 127.0.0.1 --port "${BUS_EDS_PORT:-8000}"
