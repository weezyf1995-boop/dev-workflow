"""Tests for the routing eval runner (evals/run.py). No model call anywhere.

Three groups: the pure functions that parse result files, build the floor and
find regressions; main() with run_once replaced by a fake, so the wiring from
flags to output and exit status is exercised; and checks/24-model-names.sh run
on a small repository root, to show it fails when the runner's default model
or effort leaves the Coordinator row of the Models table.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EVALS = os.path.join(REPO, "evals")
sys.path.insert(0, EVALS)

import run as runner  # noqa: E402

CASE_NAMES = [c["name"] for c in runner.load_cases()["cases"]]
# The pin itself is checked against the Models table by check 24; these tests only follow it.
MODEL, EFFORT = runner.DEFAULT_MODEL, runner.DEFAULT_EFFORT
# A level the CLI accepts that is not the pinned one, for the override tests.
OTHER_EFFORT = next(level for level in runner.EFFORT_LEVELS if level != EFFORT)

# The baseline as it stood before floors: one run's result file.
OLD_BASELINE = """# Routing evals, 2026-11-24 22:47 UTC, model: session default
green  light-typo            3/3
flaky  spec-check            2/3  run 1: missing marker 'spec check'
summary: 9 green, 1 flaky, 0 red of 10 cases
"""


def result_text(when="2026-11-25 10:00 UTC", model=MODEL, effort=EFFORT, names=CASE_NAMES, **passes):
    """A result file as a run writes it: every named case 3/3 unless given."""
    lines = [runner.run_header(when, model, effort)]
    for name in names:
        got = passes.get(name.replace("-", "_"), 3)
        line = runner.case_line(name, got, 3)
        if got < 3:
            line += "  run 1: missing marker 'full path' | run 2: fixture edited: added x.py"
        lines.append(line)
    lines.append("summary: made up")
    return "\n".join(lines) + "\n"


def floor_of(*texts):
    named = [("run%d.txt" % i, runner.parse_run(t)) for i, t in enumerate(texts, 1)]
    return runner.build_floor(named, CASE_NAMES, 3)


class ParseRunTests(unittest.TestCase):
    def test_reads_the_header_and_every_case_line(self):
        parsed = runner.parse_run(result_text(spec_check=1, complicated=0))
        self.assertEqual((parsed.when, parsed.model, parsed.effort), ("2026-11-25 10:00 UTC", MODEL, EFFORT))
        self.assertEqual(list(parsed.passes), CASE_NAMES)
        self.assertEqual(parsed.passes["spec-check"], (1, 3))
        self.assertEqual(parsed.passes["complicated"], (0, 3))
        self.assertEqual(parsed.passes["light-typo"], (3, 3))

    def test_header_from_before_the_pin_has_no_effort(self):
        parsed = runner.parse_run(OLD_BASELINE)
        self.assertEqual((parsed.model, parsed.effort), ("session default", None))
        self.assertEqual(parsed.passes, {"light-typo": (3, 3), "spec-check": (2, 3)})

    def test_text_without_a_run_header_is_not_a_run(self):
        for text in ("", "green  light-typo  3/3\n", runner.floor_text(floor_of(*[result_text()] * 3))):
            with self.subTest(text=text[:30]):
                self.assertIsNone(runner.parse_run(text))


class FloorTests(unittest.TestCase):
    def test_floor_is_the_worst_pass_count_per_case(self):
        floor = floor_of(result_text(when="A", spec_check=2),
                         result_text(when="B", spec_check=1, complicated=2),
                         result_text(when="C", frozen_four_lines=0))
        self.assertEqual(floor.passes["spec-check"], (1, 3))
        self.assertEqual(floor.passes["complicated"], (2, 3))
        self.assertEqual(floor.passes["frozen-four-lines"], (0, 3))
        self.assertEqual(floor.passes["light-typo"], (3, 3))
        self.assertEqual((floor.sources, floor.model, floor.effort), (["A", "B", "C"], MODEL, EFFORT))

    def test_floor_file_names_its_runs_and_settings_and_reads_back(self):
        floor = floor_of(result_text(when="2026-11-25 10:00 UTC", spec_check=2),
                         result_text(when="2026-11-25 11:00 UTC"),
                         result_text(when="2026-11-25 12:00 UTC"))
        text = runner.floor_text(floor)
        head = text.splitlines()[:3]
        self.assertTrue(head[0].startswith("# Routing evals floor"))
        self.assertEqual(head[1], "# runs: 2026-11-25 10:00 UTC | 2026-11-25 11:00 UTC | 2026-11-25 12:00 UTC")
        self.assertEqual(head[2], "# model: %s, effort: %s" % (MODEL, EFFORT))
        self.assertIn("flaky  spec-check            2/3", text.splitlines())
        self.assertEqual(runner.parse_floor(text), floor)

    def test_inputs_that_cannot_make_a_floor_are_refused_by_name(self):
        good = runner.parse_run(result_text())
        for bad, needle in (
                (None, "not a result file"),
                (runner.parse_run(OLD_BASELINE), "no effort"),
                (runner.parse_run(result_text(names=CASE_NAMES[:-1])), CASE_NAMES[-1]),
                (runner.parse_run(result_text(names=CASE_NAMES + ["made-up"])), "made-up"),
                (runner.parse_run(result_text().replace("light-typo            3/3", "light-typo            2/2")),
                 "light-typo"),
                (runner.parse_run(result_text(model="another-model")), "another-model"),
                (runner.parse_run(result_text(effort="another-effort")), "another-effort")):
            with self.subTest(needle=needle):
                with self.assertRaises(ValueError) as caught:
                    runner.build_floor([("a.txt", good), ("b.txt", bad), ("c.txt", good)], CASE_NAMES, 3)
                self.assertIn("b.txt", str(caught.exception))
                self.assertIn(needle, str(caught.exception))

    def test_a_floor_needs_three_runs(self):
        good = runner.parse_run(result_text())
        with self.assertRaises(ValueError):
            runner.build_floor([("a.txt", good), ("b.txt", good)], CASE_NAMES, 3)

    def test_a_single_run_file_is_not_a_floor(self):
        for text in ("", OLD_BASELINE, result_text(),
                     "# Routing evals floor: cut short\n# runs: A | B | C\n# model: m, effort: e\n"):
            with self.subTest(text=text[:40]):
                self.assertIsNone(runner.parse_floor(text))


class RegressionTests(unittest.TestCase):
    def test_red_is_a_regression_with_or_without_a_floor(self):
        for floor in ({}, {"a": (0, 3)}, {"a": (3, 3)}):
            with self.subTest(floor=floor):
                self.assertEqual(runner.regressions({"a": (0, 3)}, floor), ["regression: a is red (0/3)"])

    def test_two_runs_below_the_floor_is_a_regression(self):
        self.assertEqual(runner.regressions({"a": (1, 3)}, {"a": (3, 3)}),
                         ["regression: a is 1/3, 2 runs below its floor of 3/3"])

    def test_one_run_below_the_floor_is_not(self):
        for got, floor in ((2, 3), (1, 2), (3, 3), (3, 1), (2, 2)):
            with self.subTest(got=got, floor=floor):
                self.assertEqual(runner.regressions({"a": (got, 3)}, {"a": (floor, 3)}), [])

    def test_a_case_with_no_floor_regresses_only_by_going_red(self):
        self.assertEqual(runner.regressions({"new": (1, 3)}, {"a": (3, 3)}), [])

    def test_one_line_per_regression_in_case_order(self):
        lines = runner.regressions({"a": (1, 3), "b": (3, 3), "c": (0, 3)}, {"a": (3, 3), "b": (3, 3), "c": (3, 3)})
        self.assertEqual([line.split()[1] for line in lines], ["a", "c"])


class FloorForTests(unittest.TestCase):
    FLOOR = None

    @classmethod
    def setUpClass(cls):
        cls.FLOOR = runner.floor_text(floor_of(result_text(when="A"), result_text(when="B", spec_check=2),
                                               result_text(when="C")))

    def test_a_floor_for_the_same_model_and_effort_is_compared(self):
        passes, note = runner.floor_for(self.FLOOR, MODEL, EFFORT)
        self.assertEqual(passes["spec-check"], (2, 3))
        self.assertEqual(note, "baseline: compared with the floor of runs A | B | C")

    def test_nothing_to_compare_gives_one_warning_and_no_floor(self):
        for text, model, effort, needle in ((None, MODEL, EFFORT, "not found"),
                                            (OLD_BASELINE, MODEL, EFFORT, "not a three-run floor"),
                                            (self.FLOOR, "another-model", EFFORT, "model another-model"),
                                            (self.FLOOR, MODEL, "another-effort", "effort another-effort")):
            with self.subTest(needle=needle):
                passes, note = runner.floor_for(text, model, effort)
                self.assertEqual(passes, {})
                self.assertTrue(note.startswith("baseline: "))
                self.assertIn(needle, note)
                self.assertIn("not compared", note)
                self.assertNotIn("\n", note)


class NoFloorNoteTests(unittest.TestCase):
    def test_cases_with_no_line_in_the_floor_are_named_in_one_line(self):
        note = runner.no_floor_note({"a": (3, 3), "new": (2, 3), "newer": (0, 3)}, {"a": (3, 3)})
        self.assertEqual(note, "baseline: no floor for new, newer; compared for red only")

    def test_no_line_when_every_case_has_a_floor_or_nothing_was_compared(self):
        self.assertIsNone(runner.no_floor_note({"a": (3, 3)}, {"a": (3, 3), "b": (3, 3)}))
        self.assertIsNone(runner.no_floor_note({"a": (3, 3)}, {}))


class MainTests(unittest.TestCase):
    """main() end to end, with run_once replaced so no CLI or model is called."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.baseline = os.path.join(self.dir, "baseline.txt")
        patcher = mock.patch.object(runner, "BASELINE", self.baseline)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.calls = []

    def path(self, name):
        return os.path.join(self.dir, name)

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8") as f:
            f.write(text)
        return self.path(name)

    def write_floor(self, **passes):
        self.write("baseline.txt", runner.floor_text(floor_of(result_text(when="A", **passes),
                                                              result_text(when="B"), result_text(when="C"))))

    def main(self, *argv, failing=None):
        """Run main(argv) with a fake run_once: the first failing[name] runs of
        a case fail. Returns (exit status, stdout lines, stderr text)."""
        failing = failing or {}
        seen = {}

        def fake_run_once(case, model, effort, timeout):
            self.calls.append((case["name"], model, effort))
            seen[case["name"]] = seen.get(case["name"], 0) + 1
            if seen[case["name"]] <= failing.get(case["name"], 0):
                return "a reply", ["missing marker 'made up'"]
            return "a reply", []

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(runner, "run_once", fake_run_once), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                status = runner.main(list(argv))
            except SystemExit as exc:  # argparse reports a usage error this way
                status = exc.code
        return status, out.getvalue().splitlines(), err.getvalue()

    def test_defaults_are_the_pinned_model_and_effort_and_the_header_prints_both(self):
        status, lines, _ = self.main("--no-baseline")
        self.assertEqual(status, 0)
        self.assertEqual({(m, e) for _, m, e in self.calls}, {(MODEL, EFFORT)})
        self.assertEqual(len(self.calls), 3 * len(CASE_NAMES))
        self.assertRegex(lines[0], r"^# Routing evals, \d{4}-\d\d-\d\d \d\d:\d\d UTC, model: %s, effort: %s$"
                         % (MODEL, EFFORT))

    def test_the_cli_is_given_the_model_and_the_effort(self):
        cmd = runner.command("a prompt", "some-model", "some-effort")
        self.assertEqual(cmd[:3], ["claude", "-p", "a prompt"])
        self.assertEqual(cmd[cmd.index("--model") + 1], "some-model")
        self.assertEqual(cmd[cmd.index("--effort") + 1], "some-effort")

    def test_flags_override_the_model_and_effort(self):
        status, lines, _ = self.main("--model", "another-model", "--effort", OTHER_EFFORT, "--case", "chaotic",
                                     "--no-baseline")
        self.assertEqual(status, 0)
        self.assertEqual(self.calls, [("chaotic", "another-model", OTHER_EFFORT)] * 3)
        self.assertTrue(lines[0].endswith("model: another-model, effort: %s" % OTHER_EFFORT))

    def test_effort_takes_only_the_levels_the_cli_documents(self):
        self.assertEqual(runner.EFFORT_LEVELS, ("low", "medium", "high", "xhigh", "max"))
        self.assertIn(EFFORT, runner.EFFORT_LEVELS)
        status, lines, err = self.main("--effort", "another-effort", "--case", "chaotic", "--no-baseline")
        self.assertEqual(status, 2)
        self.assertIn("invalid choice: 'another-effort'", err)
        self.assertEqual((lines, self.calls), ([], []))

    def test_result_lines_keep_their_shape_and_the_out_file_reads_back(self):
        self.write_floor()
        out = self.path("latest.txt")
        status, lines, _ = self.main("--out", out, failing={"spec-check": 1})
        self.assertEqual(status, 0)
        self.assertIn("green  light-typo            3/3", lines)
        self.assertIn("flaky  spec-check            2/3  run 1: missing marker 'made up'", lines)
        self.assertIn("summary: 9 green, 1 flaky, 0 red of 10 cases", lines)
        with open(out, encoding="utf-8") as f:
            text = f.read()
        self.assertEqual(text.splitlines(), lines)
        parsed = runner.parse_run(text)
        self.assertEqual((parsed.model, parsed.effort), (MODEL, EFFORT))
        self.assertEqual(parsed.passes, dict({n: (3, 3) for n in CASE_NAMES}, **{"spec-check": (2, 3)}))

    def test_no_regression_against_the_floor_exits_zero(self):
        self.write_floor(spec_check=2)
        status, lines, _ = self.main(failing={"spec-check": 2, "complicated": 1})
        self.assertEqual(status, 0)
        self.assertEqual(lines[-1], "baseline: compared with the floor of runs A | B | C")
        self.assertTrue(lines[-2].startswith("summary: "))

    def test_a_case_two_runs_below_its_floor_exits_one_with_one_line(self):
        self.write_floor()
        status, lines, _ = self.main(failing={"spec-check": 2, "complicated": 1})
        self.assertEqual(status, 1)
        self.assertEqual([line for line in lines if line.startswith("regression: ")],
                         ["regression: spec-check is 1/3, 2 runs below its floor of 3/3"])
        self.assertEqual(lines[-1], "regression: spec-check is 1/3, 2 runs below its floor of 3/3")

    def write_floor_without(self, name):
        """A floor of 3/3 for every case but the named one, which has no line."""
        self.write_floor()
        with open(self.baseline, encoding="utf-8") as f:
            kept = [line for line in f.read().splitlines() if line.split()[1:2] != [name]]
        self.write("baseline.txt", "\n".join(kept) + "\n")

    def test_a_case_with_no_floor_is_named_in_one_warning_line_and_the_exit_is_unchanged(self):
        self.write_floor_without("chaotic")
        status, lines, _ = self.main(failing={"chaotic": 2})
        self.assertEqual(status, 0)
        self.assertEqual([line for line in lines if line.startswith("baseline: ")],
                         ["baseline: compared with the floor of runs A | B | C",
                          "baseline: no floor for chaotic; compared for red only"])
        self.assertEqual([line for line in lines if line.startswith("regression: ")], [])

    def test_a_case_with_no_floor_still_fails_the_run_by_going_red(self):
        self.write_floor_without("chaotic")
        status, lines, _ = self.main(failing={"chaotic": 3, "spec-check": 2})
        self.assertEqual(status, 1)
        self.assertIn("baseline: no floor for chaotic; compared for red only", lines)
        self.assertEqual([line for line in lines if line.startswith("regression: ")],
                         ["regression: chaotic is red (0/3)",
                          "regression: spec-check is 1/3, 2 runs below its floor of 3/3"])

    def test_no_baseline_skips_the_comparison(self):
        self.write_floor()
        status, lines, _ = self.main("--no-baseline", failing={"spec-check": 2})
        self.assertEqual(status, 0)
        self.assertTrue(lines[-1].startswith("summary: "))

    def test_a_red_case_exits_one_whatever_the_baseline(self):
        for argv in ((), ("--no-baseline",)):
            with self.subTest(argv=argv):
                status, lines, _ = self.main(*argv, failing={"wayfinder": 3})
                self.assertEqual(status, 1)
                self.assertIn("red    wayfinder             0/3  run 1: missing marker 'made up' | "
                              "run 2: missing marker 'made up' | run 3: missing marker 'made up'", lines)
                self.assertEqual(lines[-1], "regression: wayfinder is red (0/3)")

    def test_a_missing_or_old_baseline_is_one_warning_line_and_no_error(self):
        for text, needle in ((None, "not found"), (OLD_BASELINE, "not a three-run floor")):
            with self.subTest(needle=needle):
                if text is not None:
                    self.write("baseline.txt", text)
                status, lines, _ = self.main(failing={"spec-check": 2})
                self.assertEqual(status, 0)
                self.assertEqual(len([line for line in lines if line.startswith("baseline: ")]), 1)
                self.assertIn(needle, lines[-1])

    def test_a_floor_taken_with_another_model_is_not_compared(self):
        self.write_floor()
        status, lines, _ = self.main("--model", "another-model", failing={"spec-check": 2})
        self.assertEqual(status, 0)
        self.assertIn("not compared", lines[-1])

    def test_replies_are_saved_one_file_per_run(self):
        replies = self.path("replies")
        status, _, _ = self.main("--case", "chaotic", "--replies", replies, "--no-baseline")
        self.assertEqual(status, 0)
        self.assertEqual(sorted(os.listdir(replies)), ["chaotic-1.txt", "chaotic-2.txt", "chaotic-3.txt"])
        with open(os.path.join(replies, "chaotic-1.txt"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "a reply")

    def test_an_unknown_case_is_a_usage_error(self):
        status, _, err = self.main("--case", "no-such-case")
        self.assertEqual(status, 2)
        self.assertIn("no-such-case", err)
        self.assertEqual(self.calls, [])

    def test_write_baseline_writes_the_floor_of_three_result_files_and_runs_nothing(self):
        paths = [self.write("a.txt", result_text(when="A", spec_check=2)),
                 self.write("b.txt", result_text(when="B", spec_check=1)),
                 self.write("c.txt", result_text(when="C", complicated=2))]
        status, lines, _ = self.main("--write-baseline", *paths)
        self.assertEqual(status, 0)
        self.assertEqual(self.calls, [])
        with open(self.baseline, encoding="utf-8") as f:
            floor = runner.parse_floor(f.read())
        self.assertEqual(floor.sources, ["A", "B", "C"])
        self.assertEqual((floor.model, floor.effort), (MODEL, EFFORT))
        self.assertEqual(floor.passes, dict({n: (3, 3) for n in CASE_NAMES},
                                            **{"spec-check": (1, 3), "complicated": (2, 3)}))
        self.assertEqual(lines[-1], "wrote evals/results/baseline.txt")

    def test_a_run_then_compares_with_the_baseline_it_wrote(self):
        paths = [self.write(n, result_text(when=n)) for n in ("a.txt", "b.txt", "c.txt")]
        self.assertEqual(self.main("--write-baseline", *paths)[0], 0)
        status, lines, _ = self.main(failing={"chaotic": 2})
        self.assertEqual(status, 1)
        self.assertEqual(lines[-1], "regression: chaotic is 1/3, 2 runs below its floor of 3/3")

    def test_write_baseline_refuses_bad_input_and_leaves_the_baseline_alone(self):
        self.write("baseline.txt", OLD_BASELINE)
        good = [self.write(n, result_text(when=n)) for n in ("a.txt", "b.txt", "c.txt")]
        partial = self.write("partial.txt", result_text(names=CASE_NAMES[:3]))
        for argv, needle in (((good[0], good[1], partial), "partial.txt"),
                             ((good[0], good[1], good[0]), "three different"),
                             ((good[0], good[1], self.path("absent.txt")), "absent.txt"),
                             ((good[0], good[1]), "expected 3 arguments")):
            with self.subTest(needle=needle):
                status, _, err = self.main("--write-baseline", *argv)
                self.assertEqual(status, 2)
                self.assertIn(needle, err)
                with open(self.baseline, encoding="utf-8") as f:
                    self.assertEqual(f.read(), OLD_BASELINE)
        self.assertEqual(self.calls, [])

    def test_write_baseline_refuses_two_files_with_the_same_header_timestamp(self):
        self.write("baseline.txt", OLD_BASELINE)
        paths = [self.write("a.txt", result_text(when="2026-11-25 10:00 UTC")),
                 self.write("b.txt", result_text(when="2026-11-25 11:00 UTC", spec_check=2)),
                 self.write("c.txt", result_text(when="2026-11-25 10:00 UTC", complicated=2))]
        status, lines, err = self.main("--write-baseline", *paths)
        self.assertEqual((status, lines), (2, []))
        for needle in ("same header timestamp", "2026-11-25 10:00 UTC", "a.txt", "c.txt"):
            self.assertIn(needle, err)
        self.assertNotIn("b.txt", err)
        with open(self.baseline, encoding="utf-8") as f:
            self.assertEqual(f.read(), OLD_BASELINE)

    def test_write_baseline_refuses_runs_off_the_pinned_model_or_effort(self):
        self.write("baseline.txt", OLD_BASELINE)
        for settings, needle in (({"model": "another-model"}, "model another-model, effort %s" % EFFORT),
                                 ({"effort": OTHER_EFFORT}, "model %s, effort %s" % (MODEL, OTHER_EFFORT))):
            with self.subTest(settings=settings):
                paths = [self.write(n, result_text(when=n, **settings)) for n in ("a.txt", "b.txt", "c.txt")]
                status, lines, err = self.main("--write-baseline", *paths)
                self.assertEqual((status, lines), (2, []))
                self.assertIn("pinned model and effort (model %s, effort %s)" % (MODEL, EFFORT), err)
                self.assertIn(needle, err)
                self.assertNotIn("timestamp", err)
                with open(self.baseline, encoding="utf-8") as f:
                    self.assertEqual(f.read(), OLD_BASELINE)
        self.assertEqual(self.calls, [])


WORKFLOW = """# Workflow

Some prose that names only roles.

### Models

| Role | Model | Effort |
|---|---|---|
%s| High-risk builder | opus | medium |
| Low-risk builder | sonnet | high |

### The ticket loop

More prose.
"""
COORDINATOR = '| Coordinator | opus (settings value `"model": "opus"`) | high |\n'


class ModelTableCheckTests(unittest.TestCase):
    """checks/24-model-names.sh, run on a small root through its process boundary."""

    def run_check(self, model="opus", effort="high", row=COORDINATOR, runner_text=None):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        files = {
            "workflow/dev-workflow.md": WORKFLOW % row,
            "docs/workflow-guide.md": "# Guide\n\nRoles only.\n",
            "README.md": "# Readme\n\nRoles only.\n",
            "evals/run.py": runner_text if runner_text is not None
            else 'DEFAULT_MODEL = "%s"\nDEFAULT_EFFORT = "%s"\n' % (model, effort),
        }
        for rel, text in files.items():
            full = os.path.join(root, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(text)
        env = dict(os.environ, REPO_ROOT=root, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(["bash", os.path.join(REPO, "checks", "24-model-names.sh")],
                              env=env, capture_output=True, text=True)

    def assertFails(self, result, *needles):
        out = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, out)
        for needle in needles:
            self.assertIn(needle, out)

    def test_defaults_that_match_the_coordinator_row_pass(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_default_model_off_the_coordinator_row_fails(self):
        self.assertFails(self.run_check(model="sonnet"), "evals/run.py", "DEFAULT_MODEL", "sonnet", "opus")

    def test_a_default_effort_off_the_coordinator_row_fails(self):
        self.assertFails(self.run_check(effort="medium"), "evals/run.py", "DEFAULT_EFFORT", "medium", "high")

    def test_a_changed_coordinator_row_fails_until_the_runner_follows(self):
        row = "| Coordinator | sonnet | xhigh |\n"
        self.assertFails(self.run_check(row=row), "DEFAULT_MODEL", "DEFAULT_EFFORT")
        result = self.run_check(model="sonnet", effort="xhigh", row=row)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_table_without_a_coordinator_row_fails(self):
        self.assertFails(self.run_check(row=""), "Coordinator")

    def test_a_runner_without_the_defaults_fails(self):
        self.assertFails(self.run_check(runner_text="MODEL = 'opus'\n"), "evals/run.py", "DEFAULT_MODEL")

    def test_a_model_name_outside_the_models_block_still_fails(self):
        # The check's first duty, unchanged: a heading ends the block, so the prose under it is a leak.
        leaked = COORDINATOR + "\n### After\n\nUse opus here.\n\n"
        self.assertFails(self.run_check(row=leaked), "workflow/dev-workflow.md:13: 'opus' outside the Models block")


if __name__ == "__main__":
    unittest.main()
