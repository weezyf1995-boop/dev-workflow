#!/usr/bin/env bash
# Run the hook dedupe tests (tests/test_hook_dedupe.py). They copy each hook
# to a temp HOME and a temp project, and check the user-level copy stands
# aside when the project carries its own.
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

exec python3 -m unittest -q tests/test_hook_dedupe.py
