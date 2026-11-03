#!/usr/bin/env bash
# Remove everything that should not be committed (venv, caches, build output).
# Usage: ./clean.sh [-n]   (-n = dry run, only list what would be removed)
cd "$(dirname "$0")" || exit 1
DRY=0; [ "$1" = "-n" ] && DRY=1

targets=(.venv venv env build dist .pytest_cache .mypy_cache .ruff_cache .tox .cache
         htmlcov .coverage '*.egg-info')
# Name patterns searched recursively (skipping the venv, which is removed anyway)
patterns=(__pycache__ '*.pyc' '*.pyo' '*.spec.bak' '*.log' '*~' '*.swp' .DS_Store Thumbs.db)

rm_path() {
  if [ "$DRY" = 1 ]; then echo "would remove: $1"; else rm -rf -- "$1" && echo "removed: $1"; fi
}

for t in "${targets[@]}"; do
  for p in $t; do [ -e "$p" ] && rm_path "$p"; done
done
for pat in "${patterns[@]}"; do
  while IFS= read -r -d '' f; do rm_path "$f"; done \
    < <(find . -path ./.venv -prune -o -name "$pat" -print0 2>/dev/null)
done
echo "Done."
