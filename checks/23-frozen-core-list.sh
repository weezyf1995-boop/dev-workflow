#!/usr/bin/env bash
# Fail when a frozen-core list is written back into a governing file other than
# SKILL.md. SKILL.md step 1 is the one list; laws.md, review-mode.md,
# review-checklist.md and testing-standard.md must point to it, not repeat it.
# The reference edition and the SKILL.md frontmatter are not checked.

set -u
cd "${REPO_ROOT:-.}" || exit 1

python3 - <<'PY'
import re
import sys

base = "skills/changeable-software/references/"
files = [base + n for n in ("laws.md", "review-mode.md", "review-checklist.md", "testing-standard.md")]

# Distinctive items of the list in SKILL.md step 1, case-insensitive, plurals included.
# These items must follow SKILL.md step 1: update them when that list changes.
items = [
    r"money movements?",
    r"kill[ -]switch(?:es)?",
    r"consensus paths?",
    r"verified parsers?",
    r"risk limits?",
    r"execution paths?",
    r"authentication (?:or|and) authori[sz]ation",
]
pattern = re.compile(r"\b(?:" + "|".join(items) + r")\b", re.I)

# Staleness guard: every item must still occur in SKILL.md, or the list has changed.
skill = open("skills/changeable-software/SKILL.md", encoding="utf-8").read()
stale = [i for i in items if not re.search(r"\b" + i + r"\b", skill, re.I)]
if stale:
    sys.exit("skills/changeable-software/SKILL.md: list changed; update the items in checks/23-frozen-core-list.sh (no longer found: " + ", ".join(stale) + ")")

bad = False
for path in files:
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as e:
        sys.exit(path + ": " + str(e))
    hits = sorted({m.group(0).lower() for m in pattern.finditer(text)})
    if hits:
        print(path + ": frozen-core list item(s) repeated (" + ", ".join(hits) + "); point to SKILL.md step 1 instead")
        bad = True
if bad:
    sys.exit(1)
print("frozen-core list lives only in SKILL.md step 1.")
PY
