#!/usr/bin/env bash
# Fail when a model family name (opus, sonnet, haiku, fable; case-insensitive,
# whole word) appears in the workflow outside its "Models" block, or anywhere
# in docs/workflow-guide.md or README.md. Names each hit as file:line. The
# cloud copy is generated from the workflow and is not scanned.
# The "Models" block runs from a heading titled Models to the next heading.
# -B keeps bytecode out of the repository.

set -u
cd "${REPO_ROOT:-.}" || exit 1

exec python3 -B - <<'PY'
import re
import sys

NAME = re.compile(r"\b(opus|sonnet|haiku|fable)\b", re.I)
HEADING = re.compile(r"^#{1,6}\s")
MODELS = re.compile(r"^#{1,6}\s+Models\s*$")

# (path, skip the Models block?)
FILES = [("workflow/dev-workflow.md", True),
         ("docs/workflow-guide.md", False),
         ("README.md", False)]

hits = []
for path, honour_block in FILES:
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
    except OSError as err:
        print(f"{path}: {err}")
        sys.exit(1)
    in_block = False
    seen_block = False
    for n, line in enumerate(lines, 1):
        if honour_block:
            if MODELS.match(line):
                in_block = seen_block = True
                continue
            if in_block and HEADING.match(line):
                in_block = False
            if in_block:
                continue
        for m in NAME.finditer(line):
            hits.append(f"{path}:{n}: '{m.group(0)}' outside the Models block")
    if honour_block and not seen_block:
        hits.append(f"{path}: no Models heading found")

if hits:
    print("\n".join(hits))
    sys.exit(1)
print("model names appear only in the Models block.")
PY
