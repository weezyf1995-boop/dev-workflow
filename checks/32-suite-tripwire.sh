#!/usr/bin/env bash
# Run the suite tripwire tests (tests/test_suite_tripwire.py). They build
# real temporary git repositories and feed hook payloads to
# scripts/suite_tripwire.py over stdin with a temp HOME.
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

exec python3 -m unittest -q tests/test_suite_tripwire.py
