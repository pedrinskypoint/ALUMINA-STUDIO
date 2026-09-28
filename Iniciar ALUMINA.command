#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [ -x .venv/bin/python ]; then
  runtime=.venv/bin/python
elif [ -x ../.venv/bin/python ]; then
  runtime=../.venv/bin/python
else
  python3 -m venv .venv
  runtime=.venv/bin/python
  "$runtime" -m pip install -r requirements.txt
fi
echo 'ALUMINA: http://127.0.0.1:7861 — mantené esta ventana abierta.'
exec "$runtime" run.py
