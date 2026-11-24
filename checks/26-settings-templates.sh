#!/usr/bin/env bash
# Fail when the settings templates drift from the README "Guardrails" deny list.
# The list between the guardrails-deny-list markers in README.md is the one
# source: both templates must deny every rule in it and back it in the sandbox,
# neither may deny .env.example, and the project template may not carry
# autoMode. Then run the checker's own tests (tests/test_settings_templates.py).
# PYTHONDONTWRITEBYTECODE keeps __pycache__ out of the repo.

set -u
cd "${REPO_ROOT:-.}" || exit 1

PYTHONDONTWRITEBYTECODE=1
export PYTHONDONTWRITEBYTECODE

python3 scripts/check_settings_templates.py . || exit 1
exec python3 -m unittest -q tests/test_settings_templates.py
