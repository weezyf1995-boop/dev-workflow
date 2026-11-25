#!/usr/bin/env bash
# Run the routing eval runner's tests (tests/test_eval_run.py). No model call:
# they cover the result-file parser, the three-run floor, the regression rule,
# main() with the CLI call replaced, and check 24's comparison of the runner's
# default model and effort with the Coordinator row of the Models table.
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

exec python3 -B -m unittest -q tests/test_eval_run.py
