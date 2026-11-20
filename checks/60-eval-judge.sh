#!/usr/bin/env bash
# Run the routing eval judge tests (tests/test_eval_judge.py). No model call:
# the judge is a pure function over a case, a reply and a fixture comparison.
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

exec python3 -B -m unittest -q tests/test_eval_judge.py
