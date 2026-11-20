"""Tests for the routing eval judge (evals/judge.py).

The judge is a pure function: a case, the reply text and the before/after
comparison of the fixture copy in; a list of problems out. These tests use the
sealed cases from evals/cases.json and never call a model.
"""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVALS = os.path.join(REPO, "evals")
sys.path.insert(0, EVALS)

import judge  # noqa: E402


def load_cases():
    with open(os.path.join(EVALS, "cases.json"), encoding="utf-8") as f:
        return {c["name"]: c for c in json.load(f)["cases"]}


CASES = load_cases()
SNAPSHOT = {"files": {"README.md": "a", "payments.py": "b"}, "commits": 1}


def unchanged():
    return judge.compare(SNAPSHOT, SNAPSHOT)


class JudgeTests(unittest.TestCase):
    def test_reply_with_markers_and_no_forbidden_command_passes(self):
        reply = "payments.py is a FROZEN core, so this takes the Full Path even at four lines."
        self.assertEqual(judge.judge(CASES["frozen-four-lines"], reply, unchanged()), [])

    def test_missing_marker_gives_one_problem(self):
        reply = "payments.py is a frozen core; I won't edit it without a ruling."
        problems = judge.judge(CASES["frozen-four-lines"], reply, unchanged())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("full path", problems[0])

    def test_forbidden_command_gives_one_problem(self):
        reply = "Production is down. Use diagnosing-bugs first, then /to-spec the fix."
        problems = judge.judge(CASES["chaotic"], reply, unchanged())
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("/to-spec", problems[0])

    def test_edited_fixture_gives_one_problem(self):
        after = {"files": {"README.md": "a", "payments.py": "changed", "new.py": "c"}, "commits": 1}
        reply = "This is a frozen core, so it takes the full path."
        problems = judge.judge(CASES["frozen-four-lines"], reply, judge.compare(SNAPSHOT, after))
        self.assertEqual(len(problems), 1, problems)

    def test_deleted_file_counts_as_an_edit(self):
        after = {"files": {"README.md": "a"}, "commits": 1}
        reply = "This is a frozen core, so it takes the full path."
        problems = judge.judge(CASES["frozen-four-lines"], reply, judge.compare(SNAPSHOT, after))
        self.assertEqual(len(problems), 1, problems)

    def test_new_commit_counts_as_an_edit(self):
        after = dict(SNAPSHOT, commits=2)
        reply = "This is a frozen core, so it takes the full path."
        problems = judge.judge(CASES["frozen-four-lines"], reply, judge.compare(SNAPSHOT, after))
        self.assertEqual(len(problems), 1, problems)

    def test_not_the_full_path_passes_light_typo(self):
        reply = "Fixed: 'recieve' is now 'receive'. A one-word typo is the light path, not the full path."
        after = {"files": {"README.md": "fixed", "payments.py": "b"}, "commits": 2}
        self.assertEqual(judge.judge(CASES["light-typo"], reply, judge.compare(SNAPSHOT, after)), [])

    def test_matching_ignores_case(self):
        reply = "Run /TO-SPEC yourself; it is a command only you can type."
        self.assertEqual(judge.judge(CASES["user-only-command"], reply, unchanged()), [])


if __name__ == "__main__":
    unittest.main()
