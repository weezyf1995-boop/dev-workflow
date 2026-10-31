#!/usr/bin/env bash
# Run the context guard tests (tests/test_context_guard.py). They feed recorded
# hook payloads to scripts/context_guard.py over stdin with a temp HOME.
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

exec python3 -m unittest -q tests/test_context_guard.py
