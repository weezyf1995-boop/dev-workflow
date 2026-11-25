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


class MarkerMatchingTests(unittest.TestCase):
    """The matching rules recorded in evals/REGISTER.md on 2026-11-25."""

    def test_hyphen_or_whitespace_run_in_the_reply_matches_a_spaced_marker(self):
        for wording in ("full-path", "Full-Path", "full  path", "full\npath", "full \u2011 path",
                        "full\u2010path", "full -\tpath"):
            with self.subTest(wording=wording):
                reply = "payments.py is a frozen core, so this is a %s change." % wording
                self.assertEqual(judge.judge(CASES["frozen-four-lines"], reply, unchanged()), [])

    def test_hyphenated_marker_matches_a_spaced_reply(self):
        reply = "Production is down, so this goes to diagnosing bugs first."
        self.assertEqual(judge.judge(CASES["chaotic"], reply, unchanged()), [])

    def test_words_run_together_do_not_match(self):
        reply = "payments.py is a frozen core, so this is a fullpath change."
        self.assertEqual(len(judge.judge(CASES["frozen-four-lines"], reply, unchanged())), 1)

    def test_any_one_alternate_satisfies_the_item(self):
        for reply in ("I ran the spec check first; it found nothing.",
                      "Spec-check done.",
                      "Two readers reviewed the spec. One Blocker: the export format is not named."):
            with self.subTest(reply=reply):
                self.assertEqual(judge.judge(CASES["spec-check"], reply, unchanged()), [])

    def test_missing_item_names_every_alternate(self):
        problems = judge.judge(CASES["spec-check"], "Here are the tickets.", unchanged())
        self.assertEqual(problems, ["missing marker 'spec check' or 'blocker'"])

    def test_every_item_is_still_required(self):
        case = dict(CASES["spec-check"], must_contain=[["spec check", "blocker"], "tickets"])
        problems = judge.judge(case, "One blocker found.", unchanged())
        self.assertEqual(problems, ["missing marker 'tickets'"])

    def test_forbidden_command_is_matched_literally_slash_and_hyphen_included(self):
        for reply in ("Then /TO-SPEC the fix.", "then /to-spec."):
            with self.subTest(reply=reply):
                problems = judge.judge(CASES["chaotic"], "diagnosing-bugs. " + reply, unchanged())
                self.assertEqual(problems, ["forbidden command '/to-spec'"])
        for reply in ("Then /to spec the fix.", "Then to-spec the fix.", "Then /to\u2011spec the fix.",
                      "Then /to--spec it."):
            with self.subTest(reply=reply):
                self.assertEqual(judge.judge(CASES["chaotic"], "diagnosing-bugs. " + reply, unchanged()), [])


class AllowedNewPathsTests(unittest.TestCase):
    REPLY = "I don't know which library fits, so this starts with research."

    def run_case(self, after, name="complicated"):
        return judge.judge(CASES[name], self.REPLY, judge.compare(SNAPSHOT, after))

    def after(self, **changes):
        files = dict(SNAPSHOT["files"])
        commits = changes.pop("commits", SNAPSHOT["commits"])
        for path, digest in changes.pop("files", {}).items():
            if digest is None:
                del files[path]
            else:
                files[path] = digest
        return {"files": files, "commits": commits}

    def test_new_file_under_an_allowed_prefix_is_not_an_edit(self):
        after = self.after(files={"docs/research/locale-formatting.md": "n",
                                  "docs/research/deeper/notes.md": "n"})
        self.assertEqual(self.run_case(after), [])

    def test_new_file_elsewhere_still_fails(self):
        for path in ("export.py", "docs/notes.md", "docs/research.md", "docs/research-old/x.md",
                     "src/docs/research/x.md"):
            with self.subTest(path=path):
                problems = self.run_case(self.after(files={path: "n"}))
                self.assertEqual(problems, ["fixture edited: added " + path])

    def test_other_edits_beside_an_allowed_file_still_fail_and_only_they_are_named(self):
        allowed = {"docs/research/x.md": "n"}
        for change, expected in (
                ({"files": dict(allowed, **{"README.md": "changed"})}, "fixture edited: changed README.md"),
                ({"files": dict(allowed, **{"README.md": None})}, "fixture edited: deleted README.md"),
                ({"files": dict(allowed, **{"export.py": "n"})}, "fixture edited: added export.py"),
                ({"files": allowed, "commits": 2}, "fixture edited: 1 new commit")):
            with self.subTest(expected=expected):
                self.assertEqual(self.run_case(self.after(**change)), [expected])

    def test_changing_a_file_that_was_already_under_the_prefix_fails(self):
        before = {"files": dict(SNAPSHOT["files"], **{"docs/research/old.md": "a"}), "commits": 1}
        after = {"files": dict(SNAPSHOT["files"], **{"docs/research/old.md": "b"}), "commits": 1}
        problems = judge.judge(CASES["complicated"], self.REPLY, judge.compare(before, after))
        self.assertEqual(problems, ["fixture edited: changed docs/research/old.md"])

    def test_a_case_without_the_field_allows_no_new_file(self):
        reply = "payments.py is a frozen core, so it takes the full path."
        after = self.after(files={"docs/research/x.md": "n"})
        problems = judge.judge(CASES["frozen-four-lines"], reply, judge.compare(SNAPSHOT, after))
        self.assertEqual(problems, ["fixture edited: added docs/research/x.md"])


class SealedCasesShapeTests(unittest.TestCase):
    """A malformed case must fail here, not pass or fail every run silently."""

    def test_markers_and_allowed_paths_are_well_formed(self):
        for name, case in CASES.items():
            with self.subTest(case=name):
                for item in case["must_contain"]:
                    options = judge.alternates(item)
                    self.assertTrue(options, "an item needs at least one marker")
                    for option in options:
                        self.assertIsInstance(option, str)
                        self.assertTrue(judge.normalise(option).strip(), "a marker cannot be blank")
                for command in case["must_not_contain"]:
                    self.assertRegex(command, r"^/[a-z0-9-]+$")
                self.assertIsInstance(case["no_edits"], bool)
                if "allowed_new_paths" in case:
                    self.assertTrue(case["no_edits"], "allowed_new_paths only means something with no_edits")
                    for prefix in case["allowed_new_paths"]:
                        self.assertRegex(prefix, r"^[^/].*/$", "a prefix is a relative directory ending in /")


if __name__ == "__main__":
    unittest.main()
