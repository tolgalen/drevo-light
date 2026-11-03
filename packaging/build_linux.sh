#!/usr/bin/env bash
# Build a self-contained folder dist/drevo-light/ (run it on Linux).
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt pyinstaller
.venv/bin/pyinstaller packaging/drevo-light.spec --noconfirm
echo "Done: dist/drevo-light/drevo-light"
