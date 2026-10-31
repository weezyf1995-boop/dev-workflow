#!/usr/bin/env python3
"""Assertions about the npx calls the installer made, read from the stub's records.

Usage: calls.py CALL_LOG_DIR INSTALL_SH LOCKFILE [--exact-lock]

CALL_LOG_DIR holds one record per npx call (see bin/npx): every argument
terminated by NUL. INSTALL_SH is read as text, never sourced: the expected
skill lists are its POCOCK=( ... ) style arrays, each array is matched to a
repo through the installer's own `add <repo> "${ARRAY[@]}"` lines, and the
pinned CLI version is its SKILLS_VERSION=... line.

LOCKFILE is an install/skills.lock style file (`skill repo commit` lines).
Each `add` call must name its repo as `<repo>#<commit>` with that repo's
commit from LOCKFILE. With --exact-lock, LOCKFILE must also list exactly the
skills install.sh names, each under its own repo.

Prints one line per failed assertion and exits 1 if any failed. To assert more
about the calls, add a function taking (calls, expected, fail) and append it
to CHECKS; install.sh facts are on `expected`.
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
    source = argv[i + 1] if i + 1 < len(argv) else ""
    repo, _, ref = source.partition("#")
    skills, other = [], []
    j = i + 2
    while j < len(argv):
        if argv[j] == "--skill" and j + 1 < len(argv):
            skills.append(argv[j + 1])
            j += 2
            continue
        other.append(argv[j])
        j += 1
    return {"repo": repo, "ref": ref, "skills": skills, "other": other, "before": argv[:i]}


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


def pinned_version(text):
    """The skills CLI version install.sh pins, from its SKILLS_VERSION= line."""
    m = re.search(r"^SKILLS_VERSION=([^\s#]+)", text, re.M)
    return m.group(1) if m else None


def read_lock(path):
    """Return [(skill, repo, commit)] from a skills.lock file."""
    rows = []
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                rows.append(tuple(line.split()))
    return rows


class Expected(dict):
    """repo -> skill list from install.sh, plus the other facts the checks need."""

    version = None
    lock = ()
    exact_lock = False


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


def check_pinned_version(calls, expected, fail):
    if not expected.version or expected.version == "latest":
        fail("install.sh has no pinned SKILLS_VERSION= line (found %r)" % expected.version)
        return
    want = "skills@" + expected.version
    for argv in calls:
        a = parse_add(argv)
        specs = [x for x in (a["before"] if a else argv) if x.startswith("skills")]
        if specs != [want]:
            fail("package spec %r, expected exactly [%r]: %r" % (specs, want, argv))


def check_commits_from_lock(calls, expected, fail):
    commits = {}
    for row in expected.lock:
        if len(row) != 3 or not re.match(r"^[0-9a-f]{40}$", row[2]):
            fail("lockfile line %r is not `skill repo <40-hex commit>`" % (" ".join(row),))
            continue
        commits.setdefault(row[1], set()).add(row[2])
    for repo, found in sorted(commits.items()):
        if len(found) != 1:
            fail("lockfile has %d commits for %s, expected one" % (len(found), repo))
    for argv in calls:
        a = parse_add(argv)
        if not a or a["repo"] not in expected:
            continue
        want = sorted(commits.get(a["repo"], ()))
        if not want:
            fail("%s: lockfile has no commit for it" % a["repo"])
        elif a["ref"] != want[0]:
            fail("%s: installed at %r, expected the lockfile commit %s as <repo>#<commit>"
                 % (a["repo"], a["ref"], want[0]))


def check_exact_lock(calls, expected, fail):
    if not expected.exact_lock:
        return
    got = sorted((row[0], row[1]) for row in expected.lock if len(row) == 3)
    want = sorted((s, repo) for repo, skills in expected.items() for s in skills)
    if got != want:
        fail("lockfile skills differ from install.sh (missing %r, extra %r)"
             % (sorted(set(want) - set(got)), sorted(set(got) - set(want))))


CHECKS = [check_repos_parsed, check_one_add_per_repo, check_skill_names, check_skill_flag_form,
          check_pinned_version, check_commits_from_lock, check_exact_lock]


def main(argv):
    args = argv[1:]
    exact = "--exact-lock" in args
    args = [a for a in args if a != "--exact-lock"]
    if len(args) != 3:
        sys.stderr.write(__doc__)
        return 2
    log_dir, install_sh, lockfile = args
    with open(install_sh) as f:
        text = f.read()
    expected = Expected(expected_skills(text))
    expected.version = pinned_version(text)
    expected.lock = read_lock(lockfile)
    expected.exact_lock = exact
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
