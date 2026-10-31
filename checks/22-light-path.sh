#!/usr/bin/env bash
# Fail when the light-path quotation in workflow/dev-workflow.md and the Hard
# disqualifiers sentences in skills/changeable-software/SKILL.md differ.
# Both directions are checked, byte for byte, so editing either copy alone fails.

set -u
cd "${REPO_ROOT:-.}" || exit 1

python3 - <<'PY'
import re
import sys

wf_path = "workflow/dev-workflow.md"
sk_path = "skills/changeable-software/SKILL.md"
wf = open(wf_path, "rb").read()
sk = open(sk_path, "rb").read()

# Skill side: first two sentences after the bold label on the Hard disqualifiers line.
line = next((l for l in sk.split(b"\n") if l.startswith(b"**Hard disqualifiers")), None)
if line is None:
    sys.exit(sk_path + ": no '**Hard disqualifiers' line")
rest = line.split(b"**", 2)[2].strip()
sentences = re.split(rb"(?<=\.)\s+(?=[A-Z])", rest)
if len(sentences) < 2:
    sys.exit(sk_path + ": fewer than two sentences after the label")
want = b" ".join(sentences[:2])

# Workflow side: the quoted text in the light-path bullet.
m = re.search(rb"^- Light path .*?says: \"(.*?)\" Otherwise", wf, re.M)
if m is None:
    sys.exit(wf_path + ": light-path bullet has no quotation")
quoted = m.group(1)

bad = False
if quoted not in sk:
    print(wf_path + ": quoted text is not verbatim in " + sk_path)
    bad = True
if want not in wf:
    print(wf_path + ": does not contain the Hard disqualifiers sentences of " + sk_path)
    bad = True
if bad:
    sys.exit(1)
print("light-path quotation matches changeable-software.")
PY
