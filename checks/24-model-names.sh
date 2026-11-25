#!/usr/bin/env bash
# Fail when a model family name (opus, sonnet, haiku, fable; case-insensitive,
# whole word) appears in the workflow outside its "Models" block, or anywhere
# in docs/workflow-guide.md or README.md. Names each hit as file:line. The
# cloud copy is generated from the workflow and is not scanned.
# The "Models" block runs from a heading titled Models to the next heading.
#
# Also fail when the routing evals stop running as the coordinator: the
# DEFAULT_MODEL and DEFAULT_EFFORT of evals/run.py must equal the model and
# effort in the Coordinator row of the table in that block. The model is the
# first word of the row's Model cell. tests/test_eval_run.py runs this check
# on a small root to show both failures.
# -B keeps bytecode out of the repository.

set -u
cd "${REPO_ROOT:-.}" || exit 1

exec python3 -B - <<'PY'
import importlib.util
import re
import sys

NAME = re.compile(r"\b(opus|sonnet|haiku|fable)\b", re.I)
HEADING = re.compile(r"^#{1,6}\s")
MODELS = re.compile(r"^#{1,6}\s+Models\s*$")
COORDINATOR = re.compile(r"^\|\s*Coordinator\s*\|\s*([\w.-]+)[^|]*\|\s*([\w.-]+)\s*\|\s*$")
WORKFLOW = "workflow/dev-workflow.md"
RUNNER = "evals/run.py"

# (path, skip the Models block?)
FILES = [(WORKFLOW, True),
         ("docs/workflow-guide.md", False),
         ("README.md", False)]

hits = []
coordinator = None  # (line number, model, effort)
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
                row = COORDINATOR.match(line)
                if row and coordinator is None:
                    coordinator = (n, row.group(1), row.group(2))
                continue
        for m in NAME.finditer(line):
            hits.append(f"{path}:{n}: '{m.group(0)}' outside the Models block")
    if honour_block and not seen_block:
        hits.append(f"{path}: no Models heading found")

if coordinator is None:
    hits.append(f"{WORKFLOW}: no Coordinator row with a model and an effort in the Models table")
else:
    n, model, effort = coordinator
    try:
        spec = importlib.util.spec_from_file_location("routing_eval_runner", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
    except Exception as err:  # a runner that cannot be loaded has no defaults to compare
        print(f"{RUNNER}: cannot be loaded ({err})")
        sys.exit(1)
    for constant, want, what in (("DEFAULT_MODEL", model, "model"), ("DEFAULT_EFFORT", effort, "effort")):
        have = getattr(runner, constant, None)
        if have != want:
            hits.append(f"{RUNNER}: {constant} is {have!r}, but the Coordinator row's {what} is "
                        f"{want!r} ({WORKFLOW}:{n})")

if hits:
    print("\n".join(hits))
    sys.exit(1)
print("model names appear only in the Models block; the routing evals run as the coordinator.")
PY
