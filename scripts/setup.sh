#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")/.."
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/prepare_models.py
echo 'Setup complete. Run ./start-demo.command and open http://127.0.0.1:8000'
