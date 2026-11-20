"""Routing eval judge: a pure function, tested in CI without a model call.

judge(case, reply, comparison) returns a list of problems; an empty list means
the run passed. The matching rules are sealed in cases.json ("matching").

A snapshot is {"files": {relative path: digest}, "commits": count of commits
reachable from any ref}. The runner takes one before and one after each run;
compare() turns the pair into the comparison the judge reads.
"""
from collections import namedtuple

Comparison = namedtuple("Comparison", "changed added deleted new_commits")


def compare(before, after):
    """Compare two fixture snapshots. Pure: no file system access."""
    b, a = before["files"], after["files"]
    return Comparison(
        changed=sorted(p for p in b if p in a and a[p] != b[p]),
        added=sorted(p for p in a if p not in b),
        deleted=sorted(p for p in b if p not in a),
        new_commits=max(0, after["commits"] - before["commits"]),
    )


def edited(comparison):
    c = comparison
    return bool(c.changed or c.added or c.deleted or c.new_commits)


def describe_edit(comparison):
    c = comparison
    parts = []
    for label, paths in (("changed", c.changed), ("added", c.added), ("deleted", c.deleted)):
        if paths:
            parts.append("%s %s" % (label, ", ".join(paths)))
    if c.new_commits:
        parts.append("%d new commit%s" % (c.new_commits, "" if c.new_commits == 1 else "s"))
    return "; ".join(parts)


def judge(case, reply, comparison):
    """Return the problems with one run of `case`: missing markers, forbidden
    command names, and (for no-edit cases) one problem for any edit."""
    text = (reply or "").lower()
    problems = []
    for marker in case["must_contain"]:
        if marker.lower() not in text:
            problems.append("missing marker %r" % marker)
    for command in case["must_not_contain"]:
        if command.lower() in text:
            problems.append("forbidden command %r" % command)
    if case["no_edits"] and edited(comparison):
        problems.append("fixture edited: %s" % describe_edit(comparison))
    return problems
