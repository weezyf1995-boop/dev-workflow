#!/usr/bin/env python3
"""Assertions about the npx calls the installer made, read from the stub's records.

Usage: calls.py CALL_LOG_DIR INSTALL_SH

CALL_LOG_DIR holds one record per npx call (see bin/npx): every argument
terminated by NUL. INSTALL_SH is read as text, never sourced: the expected
skill lists are its POCOCK=( ... ) style arrays, and each array is matched to a
repo through the installer's own `add <repo> "${ARRAY[@]}"` lines.

Prints one line per failed assertion and exits 1 if any failed. To assert more
about the calls (package spec, new flags), add a function taking the parsed
calls and append it to CHECKS.
"""

import os
import re
import sys

EXPECTED_REPOS = ("mattpocock/skills", "addyosmani/agent-skills")


def load_calls(log_dir):
    """Return a list of argv lists, one per recorded call, in call order."""
    calls = []
    for name in sorted(os.listdir(log_dir)):
        with open(os.path.join(log_dir, name), "rb") as f:
            data = f.read()
        args = data.split(b"\0")
        if args and args[-1] == b"":
            args.pop()
        calls.append([a.decode("utf-8") for a in args])
    return calls


def parse_add(argv):
    """Split a `skills add` call into (repo, skill names, other args).

    Returns None if the call is not an `add` call.
    """
    if "add" not in argv:
        return None
    i = argv.index("add")
    repo = argv[i + 1] if i + 1 < len(argv) else None
    skills, other = [], []
    j = i + 2
    while j < len(argv):
        if argv[j] == "--skill" and j + 1 < len(argv):
            skills.append(argv[j + 1])
            j += 2
            continue
        other.append(argv[j])
        j += 1
    return {"repo": repo, "skills": skills, "other": other, "before": argv[:i]}


def installer_arrays(text):
    """Extract NAME=( ... ) bash arrays from install.sh as lists of words."""
    arrays = {}
    for m in re.finditer(r"^([A-Z_]+)=\((.*?)\)", text, re.M | re.S):
        words = []
        for line in m.group(2).splitlines():
            words.extend(line.split("#", 1)[0].split())
        arrays[m.group(1)] = words
    return arrays


def expected_skills(text):
    """Map each repo to the skill list install.sh passes for it."""
    arrays = installer_arrays(text)
    expected = {}
    for m in re.finditer(r'^\s*add\s+(\S+)\s+"\$\{([A-Z_]+)\[@\]\}"', text, re.M):
        expected[m.group(1)] = arrays.get(m.group(2), [])
    return expected


def check_repos_parsed(calls, expected, fail):
    for repo in EXPECTED_REPOS:
        if repo not in expected:
            fail("could not find an `add %s` line with its skill array in install.sh" % repo)
        elif not expected[repo]:
            fail("skill array for %s parsed from install.sh is empty" % repo)


def check_one_add_per_repo(calls, expected, fail):
    adds = [parse_add(c) for c in calls]
    if None in adds:
        fail("npx was called for something other than `add`: %r" % calls[adds.index(None)])
    repos = [a["repo"] for a in adds if a]
    if sorted(repos) != sorted(expected):
        fail("repos added %r, expected one call each for %r" % (repos, sorted(expected)))


def check_skill_names(calls, expected, fail):
    for argv in calls:
        a = parse_add(argv)
        if not a or a["repo"] not in expected:
            continue
        want = expected[a["repo"]]
        if a["skills"] != want:
            missing = [s for s in want if s not in a["skills"]]
            extra = [s for s in a["skills"] if s not in want]
            fail("%s: skills %r differ from install.sh list %r (missing %r, extra %r)"
                 % (a["repo"], a["skills"], want, missing, extra))


def check_skill_flag_form(calls, expected, fail):
    for argv in calls:
        for arg in argv:
            if arg.startswith("--skill="):
                fail("skill passed as %r; expected `--skill NAME` as two arguments" % arg)
            elif arg.startswith("--skill") and arg != "--skill":
                fail("unexpected skill flag %r" % arg)
        a = parse_add(argv)
        if not a:
            continue
        if "*" in a["skills"] or "--all" in a["other"]:
            fail("%s: asked for the whole pack, not named skills" % a["repo"])
        if not a["skills"]:
            fail("%s: no --skill arguments, so the whole pack would install" % a["repo"])


CHECKS = [check_repos_parsed, check_one_add_per_repo, check_skill_names, check_skill_flag_form]


def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    log_dir, install_sh = argv[1], argv[2]
    with open(install_sh) as f:
        expected = expected_skills(f.read())
    calls = load_calls(log_dir)
    failures = []

    def fail(msg):
        failures.append(msg)
        print("FAIL: npx calls in %s: %s" % (os.path.basename(log_dir), msg))

    if not calls:
        fail("npx was never called")
    for check in CHECKS:
        check(calls, expected, fail)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
