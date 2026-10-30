#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  echo 'Run bash scripts/setup.sh first.'
  exit 1
fi
echo "EDS Reader: http://127.0.0.1:${BUS_EDS_PORT:-8000}/detect"
echo 'Press Ctrl+C to stop the server.'
export TOKENIZERS_PARALLELISM=false
exec .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port "${BUS_EDS_PORT:-8000}"
