#!/usr/bin/env bash
# Fail when workflow/dev-workflow.md names a /command that a fresh install
# would not provide. Provided means: a skill install.sh asks the skills CLI
# for (read from its arrays with tests/installer/calls.py, never sourced), a
# skill folder under skills/, or a Claude Code built-in listed below.
#
# A token counts only when the slash starts a word (start of line, whitespace
# or opening punctuation before it) and the name is [a-z0-9-]+ with no further
# path segment after it. So docs/adr/, ~/.claude/..., /home/... and URLs are
# not commands. Prints one FAIL line per unprovided command.

set -u
cd "${REPO_ROOT:-.}" || exit 1

python3 - <<'PY'
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join("tests", "installer"))
import calls  # noqa: E402  (shared install.sh parser)

BUILT_IN = {"clear", "compact", "context", "mcp", "memory"}
WORKFLOW = "workflow/dev-workflow.md"

# Slash at a word start; the name must end there, not run on into a path.
TOKEN = re.compile(r"(?:^|(?<=[\s(\[`\"']))/([a-z0-9-]+)(?![A-Za-z0-9_/-]|\.[A-Za-z0-9_])", re.M)

with open("install.sh") as f:
    expected = calls.expected_skills(f.read())
installed = {s for skills in expected.values() for s in skills}
if not installed:
    sys.exit("FAIL: no skill lists parsed from install.sh")
local = {d for d in os.listdir("skills") if os.path.isfile(os.path.join("skills", d, "SKILL.md"))}
provided = installed | local | BUILT_IN

with open(WORKFLOW) as f:
    text = f.read()
named = set(TOKEN.findall(text))
missing = sorted(named - provided)
for name in missing:
    print("FAIL: %s names /%s, which install.sh does not install and is not built in" % (WORKFLOW, name))
if missing:
    sys.exit(1)
print("ok: all %d /commands in %s are installed or built in" % (len(named), WORKFLOW))
PY
