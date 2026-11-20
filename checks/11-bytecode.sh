#!/usr/bin/env bash
# Fail when a tracked path is Python bytecode (a __pycache__ directory, a .pyc
# or .pyo file) or a macOS folder-metadata file (.DS_Store). Names each path.

set -u
cd "${REPO_ROOT:-.}" || exit 1

files=$(git ls-files) || { echo "git ls-files failed"; exit 1; }
bad=$(printf '%s\n' "$files" | grep -E '(^|/)__pycache__/|\.py[co]$|(^|/)\.DS_Store$')
if [ -n "$bad" ]; then
  echo "tracked build artefacts or folder metadata:"
  printf '%s\n' "$bad" | sed 's/^/  /'
  exit 1
fi
