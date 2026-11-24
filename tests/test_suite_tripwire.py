"""Tests for scripts/suite_tripwire.py, driven through its process boundary.

Each test builds a real temporary git repository with a `main` branch, writes
its own `.claude/checks.json` there, feeds the recorded Stop payload
(tests/payloads/stop.json) to the tripwire over stdin with HOME pointed at a
fresh temp directory, and checks stdout, stderr and the exit code. The
tripwire's functions are never imported, and no test reads this repository's
own `.claude/checks.json`.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRIPWIRE = os.path.join(REPO, "scripts", "suite_tripwire.py")
STOP_PAYLOAD = os.path.join(HERE, "payloads", "stop.json")

GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def git(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class SuiteTripwireTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="suite-tripwire-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.mkdir(self.home)
        self.repo = os.path.join(self.tmp, "repo")
        os.mkdir(self.repo)
        self.ran = os.path.join(self.tmp, "ran.log")  # each run of `full` appends a line here
        git(self.repo, "init", "-q")
        write(os.path.join(self.repo, "app.py"), "x = 1\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "fixture")

    # -- helpers ---------------------------------------------------------

    def checks(self, **commands):
        """Write .claude/checks.json in the temp repo, untracked so main's tree is unchanged."""
        write(os.path.join(self.repo, ".claude", "checks.json"), json.dumps(commands))

    def full(self, script):
        """A `full` command that logs each run, then runs the given shell script."""
        return f"echo run >> '{self.ran}'; {script}"

    def runs(self):
        try:
            with open(self.ran) as f:
                return len(f.readlines())
        except FileNotFoundError:
            return 0

    def land(self, text="x = 2\n"):
        """Commit a change on main, so main's tip has a tree not yet proven."""
        write(os.path.join(self.repo, "app.py"), text)
        git(self.repo, "commit", "-q", "-am", "landing")

    def run_hook(self, payload, project_dir=None):
        """project_dir sets CLAUDE_PROJECT_DIR; by default it is unset, whatever runs the tests."""
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        env.pop("CLAUDE_PROJECT_DIR", None)
        if project_dir:
            env["CLAUDE_PROJECT_DIR"] = project_dir
        p = subprocess.run(
            [sys.executable or "python3", TRIPWIRE], input=stdin, env=env, cwd=self.tmp,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
        )
        return p.returncode, p.stdout, p.stderr

    def stop(self, session="s1", active=False, cwd=None, project_dir=None, **extra):
        with open(STOP_PAYLOAD, encoding="utf-8") as f:
            d = json.load(f)
        d.update(session_id=session, stop_hook_active=active, cwd=cwd or self.repo, **extra)
        return self.run_hook(d, project_dir)

    def assert_silent(self, result):
        self.assertEqual(result, (0, "", ""))

    def assert_blocked(self, result, *needles):
        code, out, err = result
        self.assertEqual(code, 2, (out, err))
        self.assertEqual(out, "")
        self.assertIn("Suite tripwire", err)
        for n in needles:
            self.assertIn(n, err)
        return err

    def state_files(self):
        state = os.path.join(self.home, ".claude", "state")
        return sorted(os.listdir(state)) if os.path.isdir(state) else []


class NoConfigTest(SuiteTripwireTest):
    def test_no_checks_file_is_silent(self):
        self.assert_silent(self.stop())
        self.assertEqual(self.state_files(), [])

    def test_checks_file_without_full_is_silent(self):
        self.checks(lint="false", touched="false")
        self.assert_silent(self.stop())
        self.assertEqual(self.state_files(), [])


class GreenTest(SuiteTripwireTest):
    def test_green_run_passes_and_records_the_tree(self):
        self.checks(full=self.full("echo all good"))
        self.assert_silent(self.stop())
        self.assertEqual(self.runs(), 1)
        self.assertTrue(self.state_files(), "nothing recorded under ~/.claude/state")

    def test_full_runs_from_the_top_level(self):
        sub = os.path.join(self.repo, "pkg")
        os.mkdir(sub)
        self.checks(full=self.full("test -f app.py"))
        self.assert_silent(self.stop(cwd=sub))
        self.assertEqual(self.runs(), 1)


class RedTest(SuiteTripwireTest):
    def test_red_run_blocks_with_the_failure_on_stderr(self):
        self.checks(full=self.full("echo 'FAIL: test_ledger' >&2; exit 1"))
        err = self.assert_blocked(self.stop(), "FAIL: test_ledger", "exit 1")
        self.assertIn(".claude/checks.json", err)
        self.assertEqual([f for f in self.state_files() if f.startswith("suite-green")], [])

    def test_red_tree_is_not_recorded_so_the_next_stop_runs_again(self):
        self.checks(full=self.full("exit 1"))
        self.assert_blocked(self.stop())
        self.checks(full=self.full("true"))
        self.assert_silent(self.stop())
        self.assertEqual(self.runs(), 2)

    def test_failure_is_trimmed_to_its_last_lines(self):
        self.checks(full=self.full("for i in $(seq 1 500); do echo line-$i; done; exit 3"))
        err = self.assert_blocked(self.stop(), "line-500", "exit 3")
        self.assertNotIn("line-1\n", err)
        self.assertLess(len(err.splitlines()), 60)


class GiveUpTest(SuiteTripwireTest):
    """Two blocks for a session and tree, then the stop is let through with a message naming the
    failure, and that session stays given up on that tree."""

    def setUp(self):
        super().setUp()
        self.checks(full=self.full("echo 'FAIL: test_ledger'; exit 1"))

    def assert_let_through(self, result):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        msg = json.loads(out)["systemMessage"]
        self.assertIn("Suite tripwire", msg)
        self.assertIn("FAIL: test_ledger", msg)
        self.assertNotIn("decision", json.loads(out))
        return msg

    def give_up(self, **who):
        self.assert_blocked(self.stop(active=False, **who))
        self.assert_blocked(self.stop(active=True, **who))
        return self.assert_let_through(self.stop(active=True, **who))

    def test_third_stop_passes_with_a_system_message_without_running_full_again(self):
        msg = self.give_up()
        self.assertIn("2 blocks", msg)
        self.assertEqual(self.runs(), 2)

    def test_a_new_turn_after_giving_up_passes_without_running_full(self):
        self.give_up()
        self.assert_silent(self.stop(active=False))
        self.assert_silent(self.stop(active=True))
        self.assertEqual(self.runs(), 2)

    def test_a_new_landing_after_giving_up_runs_and_blocks_again(self):
        self.give_up()
        self.land()
        self.assert_blocked(self.stop())
        self.assertEqual(self.runs(), 3)

    def test_blocks_are_counted_per_session(self):
        self.assert_blocked(self.stop(session="a"))
        self.assert_blocked(self.stop(session="a", active=True))
        self.assert_blocked(self.stop(session="b"))
        self.assert_let_through(self.stop(session="a", active=True))

    def test_blocks_are_counted_per_agent(self):
        self.give_up(agent_id="agent-1")
        self.assert_blocked(self.stop(agent_id="agent-2"))
        self.assert_blocked(self.stop())


class StopHookActiveTest(SuiteTripwireTest):
    """stop_hook_active says this stop continues one a hook blocked. The per-session cap is the
    loop guard: a continuing stop is held to it the same as a fresh one."""

    def setUp(self):
        super().setUp()
        self.checks(full=self.full("echo 'FAIL: test_ledger'; exit 1"))

    def test_a_fresh_stop_between_blocks_does_not_reset_the_count(self):
        self.assert_blocked(self.stop(active=False))
        self.assert_blocked(self.stop(active=False))
        self.assertEqual(self.stop(active=False)[0], 0)
        self.assertEqual(self.runs(), 2)

    def test_active_without_an_earlier_block_still_blocks(self):
        # Another Stop hook blocked first; this hook has not blocked yet, so it has both blocks left.
        self.assert_blocked(self.stop(active=True))
        self.assert_blocked(self.stop(active=True))
        self.assertEqual(self.stop(active=True)[0], 0)

    def test_green_ends_the_chain(self):
        self.assert_blocked(self.stop())
        self.assert_blocked(self.stop(active=True))
        self.checks(full=self.full("true"))
        # Given up is not proven: a fixed suite on the same tree is only found by a new landing.
        self.land()
        self.assert_silent(self.stop(active=True))
        self.land("x = 5\n")
        self.checks(full=self.full("exit 1"))
        self.assert_blocked(self.stop(active=True))


class TrustTest(SuiteTripwireTest):
    """With CLAUDE_PROJECT_DIR set, the hook acts only inside it."""

    def test_cwd_outside_the_project_dir_does_nothing(self):
        self.checks(full=self.full("exit 1"))
        elsewhere = os.path.join(self.tmp, "project")
        os.mkdir(elsewhere)
        self.assert_silent(self.stop(project_dir=elsewhere))
        self.assertEqual(self.runs(), 0)
        self.assertEqual(self.state_files(), [])

    def test_cwd_inside_the_project_dir_acts(self):
        self.checks(full=self.full("exit 1"))
        self.assert_blocked(self.stop(cwd=self.repo, project_dir=self.repo))

    def test_a_worktree_under_the_project_dir_counts_as_inside(self):
        wt = os.path.join(self.repo, ".claude", "worktrees", "t1")
        git(self.repo, "worktree", "add", "-q", wt, "-b", "t1")
        write(os.path.join(wt, ".claude", "checks.json"), json.dumps({"full": self.full("exit 1")}))
        self.assert_blocked(self.stop(cwd=wt, project_dir=self.repo))

    def test_a_sibling_whose_name_extends_the_project_dir_is_outside(self):
        self.checks(full=self.full("exit 1"))
        self.assert_silent(self.stop(project_dir=self.repo[:-1]))  # ".../rep" is not ".../repo"
        self.assertEqual(self.runs(), 0)


class FailureTest(SuiteTripwireTest):
    def assert_warned(self, result):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        d = json.loads(out)
        self.assertNotIn("decision", d)
        msg = d["systemMessage"]
        self.assertIn("suite tripwire failed", msg.lower())
        self.assertIn("not checking", msg)
        return msg

    def test_malformed_input_fails_open_with_a_warning(self):
        self.assertIn("JSONDecodeError", self.assert_warned(self.run_hook("{not json")))

    def test_malformed_checks_file_fails_open(self):
        write(os.path.join(self.repo, ".claude", "checks.json"), "{oops")
        self.assert_warned(self.stop())

    def test_corrupt_state_files_are_treated_as_empty(self):
        self.checks(full=self.full("exit 1"))
        self.assert_blocked(self.stop())
        state = os.path.join(self.home, ".claude", "state")
        for name in self.state_files():
            with open(os.path.join(state, name), "w") as f:
                f.write("{truncated")
        self.assert_blocked(self.stop())   # the count starts again from the corrupt file
        self.checks(full=self.full("true"))
        self.land()
        self.assert_silent(self.stop())
        for name in self.state_files():
            if name.startswith("suite-green"):
                with open(os.path.join(state, name), "w") as f:
                    f.write('["not", "an", "object"]')
        self.assert_silent(self.stop())    # runs again, records again
        self.assert_silent(self.stop())    # and is now skipped
        self.assertEqual(self.runs(), 4)

    def test_unwritable_state_fails_open_even_on_red(self):
        os.makedirs(os.path.join(self.home, ".claude"))
        open(os.path.join(self.home, ".claude", "state"), "w").close()  # state dir cannot be made
        self.checks(full=self.full("exit 1"))
        self.assert_warned(self.stop())

    def test_outside_a_repository_is_silent(self):
        outside = os.path.join(self.tmp, "nowhere")
        write(os.path.join(outside, ".claude", "checks.json"), json.dumps({"full": "exit 1"}))
        self.assert_silent(self.stop(cwd=outside))

    def test_other_events_are_silent(self):
        self.checks(full=self.full("exit 1"))
        for event in ("SubagentStop", "PostToolUse", "UserPromptSubmit"):
            with self.subTest(event=event):
                self.assert_silent(self.run_hook({"hook_event_name": event, "cwd": self.repo,
                                                  "session_id": "s1"}))
        self.assertEqual(self.runs(), 0)


class ProvenTreeTest(SuiteTripwireTest):
    def test_a_tree_recorded_green_is_skipped(self):
        self.checks(full=self.full("true"))
        self.assert_silent(self.stop())
        self.assert_silent(self.stop(session="s2"))
        self.assertEqual(self.runs(), 1, "full ran again on a tree already recorded green")

    def test_a_new_landing_on_main_runs_again(self):
        self.checks(full=self.full("true"))
        self.stop()
        self.land()
        self.assert_silent(self.stop())
        self.assertEqual(self.runs(), 2)

    def test_work_off_main_does_not_run(self):
        self.checks(full=self.full("true"))
        self.stop()
        git(self.repo, "checkout", "-q", "-b", "feature")
        self.land("x = 3\n")
        write(os.path.join(self.repo, "app.py"), "x = 4\n")  # uncommitted too
        self.assert_silent(self.stop())
        self.assertEqual(self.runs(), 1)

    def test_a_green_tree_is_shared_by_every_worktree(self):
        self.checks(full=self.full("true"))
        self.stop()
        wt = os.path.join(self.tmp, "wt")
        git(self.repo, "worktree", "add", "-q", wt, "-b", "t1")
        write(os.path.join(wt, ".claude", "checks.json"), json.dumps({"full": self.full("true")}))
        self.assert_silent(self.stop(cwd=wt))
        self.assertEqual(self.runs(), 1)

    def test_a_checkout_not_at_mains_tree_neither_runs_nor_records(self):
        self.checks(full=self.full("true"))
        wt = os.path.join(self.tmp, "wt")
        git(self.repo, "worktree", "add", "-q", wt, "-b", "builder")
        write(os.path.join(wt, ".claude", "checks.json"), json.dumps({"full": self.full("true")}))
        self.land()                              # main moves on; the builder's checkout does not
        self.assert_silent(self.stop(cwd=wt))
        self.assertEqual(self.runs(), 0)
        self.assert_silent(self.stop())         # main's own checkout still has to prove it
        self.assertEqual(self.runs(), 1)

    def test_no_main_branch_is_silent(self):
        git(self.repo, "branch", "-m", "main", "trunk")
        self.checks(full=self.full("true"))
        self.assert_silent(self.stop())
        self.assertEqual(self.runs(), 0)


if __name__ == "__main__":
    unittest.main()
