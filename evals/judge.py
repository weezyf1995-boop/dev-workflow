"""Routing eval judge: a pure function, tested in CI without a model call.

judge(case, reply, comparison) returns a list of problems; an empty list means
the run passed. The matching rules are sealed in cases.json ("matching").

A snapshot is {"files": {relative path: digest}, "commits": count of commits
reachable from any ref}. The runner takes one before and one after each run;
compare() turns the pair into the comparison the judge reads.
"""
import re
from collections import namedtuple

Comparison = namedtuple("Comparison", "changed added deleted new_commits")

# A hyphen-minus, U+2010 HYPHEN or U+2011 NON-BREAKING HYPHEN, or any whitespace.
SEPARATORS = re.compile("[-\u2010\u2011\\s]+")


def compare(before, after):
    """Compare two fixture snapshots. Pure: no file system access."""
    b, a = before["files"], after["files"]
    return Comparison(
        changed=sorted(p for p in b if p in a and a[p] != b[p]),
        added=sorted(p for p in a if p not in b),
        deleted=sorted(p for p in b if p not in a),
        new_commits=max(0, after["commits"] - before["commits"]),
    )


def normalise(text):
    """Lowercase, with hyphens and runs of whitespace turned into one space, so
    "Full-path" and "full  path" read the same. Used for must_contain only."""
    return SEPARATORS.sub(" ", (text or "").lower())


def alternates(item):
    """A must_contain item is one marker or a list of alternates."""
    return [item] if isinstance(item, str) else list(item)


def without_allowed(comparison, prefixes):
    """The comparison minus added files under one of the path prefixes. Changed
    and deleted files and new commits are never discounted."""
    prefixes = tuple(prefixes)
    kept = [p for p in comparison.added if not p.startswith(prefixes)]
    return comparison._replace(added=kept)


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
    command names, and (for no-edit cases) one problem for any edit that the
    case's allowed_new_paths does not cover."""
    literal = (reply or "").lower()
    text = normalise(reply)
    problems = []
    for item in case["must_contain"]:
        options = alternates(item)
        if not any(normalise(option) in text for option in options):
            problems.append("missing marker %s" % " or ".join(repr(o) for o in options))
    for command in case["must_not_contain"]:
        if command.lower() in literal:
            problems.append("forbidden command %r" % command)
    if case["no_edits"]:
        counted = without_allowed(comparison, case.get("allowed_new_paths", ()))
        if edited(counted):
            problems.append("fixture edited: %s" % describe_edit(counted))
    return problems
