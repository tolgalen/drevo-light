#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
if [ ! -f .venv/.deps_v11_ok ]; then
  .venv/bin/pip install -r requirements.txt && touch .venv/.deps_v11_ok
fi
exec .venv/bin/python drevo_light.py
