"""Tests for scripts/frozen_tripwire.py, driven through its process boundary.

Each test builds a real temporary git repository, feeds a hook payload to the
tripwire over stdin with HOME pointed at a fresh temp directory, and checks
stdout and the exit code. The tripwire's functions are never imported.

The marker line is written into the temporary repositories at run time, so
no file in this repository carries one.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
TRIPWIRE = os.path.join(REPO, "scripts", "frozen_tripwire.py")

MARKER = "FROZEN CORE: money movement"
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
GIT = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
       "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]


def git(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class TripwireTest(unittest.TestCase):
    def setUp(self):
        self.tmp = os.path.realpath(tempfile.mkdtemp(prefix="tripwire-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = os.path.join(self.tmp, "home")
        os.mkdir(self.home)
        self.repo = os.path.join(self.tmp, "repo")
        os.mkdir(self.repo)
        git(self.repo, "init", "-q")
        write(self.path("payments.py"), "# " + MARKER + "\ndef pay():\n    return 1\n")
        write(self.path("plain.py"), "def plain():\n    return 2\n")
        write(self.path("mentions.py"), "x = 1  # " + MARKER + "\n")
        write(self.path("src/ledger.js"), "  // " + MARKER + "\nexport const a = 1;\n")
        write(self.path("other/payments.py"), "def unrelated():\n    return 3\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "fixture")

    # -- helpers ---------------------------------------------------------

    def path(self, rel):
        return os.path.join(self.repo, rel)

    def run_hook(self, payload):
        stdin = payload if isinstance(payload, str) else json.dumps(payload)
        env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run(
            [sys.executable or "python3", TRIPWIRE], input=stdin, env=env, cwd=self.tmp,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30,
        )
        return p.returncode, p.stdout, p.stderr

    def edit(self, target, cwd=None, tool="Edit", **extra):
        key = "notebook_path" if tool == "NotebookEdit" else "file_path"
        d = {"session_id": "s1", "transcript_path": os.path.join(self.tmp, "t.jsonl"),
             "cwd": cwd or self.repo, "permission_mode": "default",
             "hook_event_name": "PreToolUse", "tool_name": tool,
             "tool_input": {key: target, "old_string": "a", "new_string": "b"}}
        d.update(extra)
        return self.run_hook(d)

    def prompt(self, text, cwd=None, **extra):
        d = {"session_id": "s1", "transcript_path": os.path.join(self.tmp, "t.jsonl"),
             "cwd": cwd or self.repo, "permission_mode": "default",
             "hook_event_name": "UserPromptSubmit", "prompt": text}
        d.update(extra)
        return self.run_hook(d)

    def assert_denied(self, result, rel="payments.py"):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertTrue(out.strip(), "tripwire printed nothing: the edit was allowed")
        hso = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        reason = hso["permissionDecisionReason"]
        self.assertIn(rel, reason)
        self.assertIn("full path", reason)
        self.assertIn("ruling", reason)
        self.assertIn(f"frozen override {rel}", reason)

    def assert_allowed(self, result):
        code, out, err = result
        self.assertEqual((code, out, err), (0, "", ""))

    def assert_prompt_blocked(self, result, *needles):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertTrue(out.strip(), "tripwire printed nothing: the prompt reached the model")
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")
        for n in needles:
            self.assertIn(n, d["reason"])
        return d["reason"]

    def state_files(self):
        state = os.path.join(self.home, ".claude", "state")
        return sorted(os.listdir(state)) if os.path.isdir(state) else []

    def add_worktree(self, name="t1"):
        wt = os.path.join(self.repo, ".claude", "worktrees", name)
        git(self.repo, "worktree", "add", "-q", wt, "-b", name)
        return wt


class EditToolTest(TripwireTest):
    def test_each_edit_tool_on_a_marked_file_is_denied(self):
        for tool in EDIT_TOOLS:
            with self.subTest(tool=tool):
                self.assert_denied(self.edit(self.path("payments.py"), tool=tool))

    def test_other_comment_leaders_count(self):
        self.assert_denied(self.edit(self.path("src/ledger.js")), "src/ledger.js")
        for leader in ("--", ";"):
            with self.subTest(leader=leader):
                write(self.path("core.sql"), "select 1;\n" + leader + MARKER + "\n")
                self.assert_denied(self.edit(self.path("core.sql")), "core.sql")

    def test_an_unmarked_file_is_allowed(self):
        self.assert_allowed(self.edit(self.path("plain.py")))

    def test_a_mid_line_mention_of_the_marker_is_allowed(self):
        self.assert_allowed(self.edit(self.path("mentions.py")))

    def test_bash_naming_a_marked_file_is_not_inspected(self):
        d = {"session_id": "s1", "cwd": self.repo, "hook_event_name": "PreToolUse",
             "tool_name": "Bash", "tool_input": {"command": f"sed -i s/1/2/ {self.path('payments.py')}",
                                                 "file_path": self.path("payments.py")}}
        self.assert_allowed(self.run_hook(d))
        for tool in ("Read", "Grep", "Glob"):
            with self.subTest(tool=tool):
                self.assert_allowed(self.edit(self.path("payments.py"), tool=tool))

    def test_subagent_edits_are_covered(self):
        self.assert_denied(self.edit(self.path("payments.py"), agent_id="agent-7f3e"))


class IdentityTest(TripwireTest):
    def test_symlink_to_a_marked_file_is_denied(self):
        os.symlink(self.path("payments.py"), self.path("alias.py"))
        self.assert_denied(self.edit(self.path("alias.py")))
        outside = os.path.join(self.tmp, "outside-link.py")
        os.symlink(self.path("payments.py"), outside)
        self.assert_denied(self.edit(outside))

    def test_hard_link_to_a_marked_file_is_denied(self):
        outside = os.path.join(self.tmp, "hard.py")
        os.link(self.path("payments.py"), outside)
        self.assert_denied(self.edit(outside))

    def test_relative_path_is_resolved_against_the_payload_cwd(self):
        self.assert_denied(self.edit("payments.py"))
        self.assert_denied(self.edit("../payments.py", cwd=self.path("src")))
        self.assert_denied(self.edit("./other/../payments.py"))

    def test_subdirectory_working_directory_still_covers_the_whole_repository(self):
        self.assert_denied(self.edit(self.path("payments.py"), cwd=self.path("other")))
        self.assert_denied(self.edit(self.path("src/ledger.js"), cwd=self.path("other")), "src/ledger.js")

    def test_differently_cased_path_on_a_case_insensitive_filesystem(self):
        probe = os.path.join(self.tmp, "CaseProbe")
        open(probe, "w").close()
        if not os.path.exists(os.path.join(self.tmp, "caseprobe")):
            self.skipTest("filesystem is case-sensitive")
        self.assert_denied(self.edit(self.path("PAYMENTS.PY")))

    def test_unmarked_file_with_the_same_name_as_a_marked_file_is_allowed(self):
        self.assert_allowed(self.edit(self.path("other/payments.py")))

    def test_untracked_marked_file_is_denied(self):
        write(self.path("fresh_core.py"), "  ; " + MARKER + "\n")
        self.assert_denied(self.edit(self.path("fresh_core.py")), "fresh_core.py")

    def test_ignored_marked_file_is_not_discovered(self):
        write(self.path(".gitignore"), "build/\n")
        write(self.path("build/gen.py"), "# " + MARKER + "\n")
        self.assert_allowed(self.edit(self.path("build/gen.py")))

    def test_binary_file_is_skipped(self):
        with open(self.path("blob.bin"), "wb") as f:
            f.write(b"\x00\x01# " + MARKER.encode() + b"\n\x00")
        self.assert_allowed(self.edit(self.path("blob.bin")))

    def test_write_to_a_path_with_no_file_is_allowed(self):
        self.assert_allowed(self.edit(self.path("brand_new.py"), tool="Write",
                                      tool_input={"file_path": self.path("brand_new.py"),
                                                  "content": "# " + MARKER + "\n"}))

    def test_marked_file_inside_a_worktree_is_denied(self):
        wt = self.add_worktree()
        self.assert_denied(self.edit(os.path.join(wt, "payments.py"), cwd=wt))
        self.assert_denied(self.edit("payments.py", cwd=wt))


class PromptTest(TripwireTest):
    def test_other_prompts_are_ignored(self):
        for text in ("Run the tests.", "please frozen override payments.py", "frozen overrides payments.py",
                     "Frozen Override payments.py", "frozen", ""):
            with self.subTest(text=text):
                self.assert_allowed(self.prompt(text))
        self.assertEqual(self.state_files(), [])

    def test_subagent_prompt_is_ignored(self):
        self.assert_allowed(self.prompt("frozen override payments.py", agent_id="agent-7f3e"))
        self.assertEqual(self.state_files(), [])

    def test_bare_override_stores_nothing_and_shows_usage(self):
        for text in ("frozen override", "  frozen   override  ", "frozen override missing.py src"):
            with self.subTest(text=text):
                self.assert_prompt_blocked(self.prompt(text), "frozen override <path>")
                self.assertEqual(self.state_files(), [])
        self.assert_denied(self.edit(self.path("payments.py")))

    def test_named_override_allows_that_path_and_no_other(self):
        self.assert_prompt_blocked(self.prompt("frozen override payments.py"), "payments.py", "8 hours")
        self.assert_allowed(self.edit(self.path("payments.py")))
        self.assert_allowed(self.edit("payments.py", cwd=self.path("other")))
        self.assert_denied(self.edit(self.path("src/ledger.js")), "src/ledger.js")

    def test_override_from_a_subdirectory_names_paths_from_the_top_level(self):
        self.assert_prompt_blocked(self.prompt("frozen override src/ledger.js", cwd=self.path("other")),
                                   "src/ledger.js")
        self.assert_allowed(self.edit(self.path("src/ledger.js")))
        self.assert_denied(self.edit(self.path("payments.py")))

    def test_new_override_replaces_the_previous_one(self):
        self.prompt("frozen override payments.py")
        self.prompt("frozen override src/ledger.js")
        self.assert_denied(self.edit(self.path("payments.py")))
        self.assert_allowed(self.edit(self.path("src/ledger.js")))

    def test_override_typed_in_the_main_checkout_reaches_a_worktree(self):
        wt = self.add_worktree()
        self.assert_prompt_blocked(self.prompt("frozen override payments.py"), "payments.py")
        self.assert_allowed(self.edit(os.path.join(wt, "payments.py"), cwd=wt))
        self.assert_denied(self.edit(os.path.join(wt, "src/ledger.js"), cwd=wt), "src/ledger.js")

    def test_override_typed_in_a_worktree_reaches_the_main_checkout(self):
        wt = self.add_worktree()
        self.prompt("frozen override payments.py", cwd=wt)
        self.assert_allowed(self.edit(self.path("payments.py")))

    def test_clear_restores_the_denial(self):
        self.prompt("frozen override payments.py")
        self.assert_allowed(self.edit(self.path("payments.py")))
        self.assert_prompt_blocked(self.prompt("frozen override clear"), "clear")
        self.assert_denied(self.edit(self.path("payments.py")))

    def test_a_file_named_clear_can_be_named_as_dot_slash(self):
        write(self.path("clear"), "# " + MARKER + "\n")
        self.prompt("frozen override ./clear")
        self.assert_allowed(self.edit(self.path("clear")))
        self.prompt("frozen override clear payments.py")
        self.assert_allowed(self.edit(self.path("clear")))
        self.assert_allowed(self.edit(self.path("payments.py")))

    def test_a_directory_is_dropped(self):
        self.assert_prompt_blocked(self.prompt("frozen override src"), "frozen override <path>")
        self.assertEqual(self.state_files(), [])

    def test_unmarked_file_can_be_named(self):
        self.assert_prompt_blocked(self.prompt("frozen override plain.py"), "plain.py")
        write(self.path("plain.py"), "# " + MARKER + "\n")
        self.assert_allowed(self.edit(self.path("plain.py")))

    def test_expired_override_does_not_allow(self):
        self.prompt("frozen override payments.py")
        self.assert_allowed(self.edit(self.path("payments.py")))
        # The spec stores an expiry time with the paths; move it into the past.
        (name,) = self.state_files()
        f = os.path.join(self.home, ".claude", "state", name)
        with open(f, encoding="utf-8") as fh:
            stored = json.load(fh)
        self.assertGreater(stored["expires"], time.time() + 8 * 3600 - 120)
        self.assertLessEqual(stored["expires"], time.time() + 8 * 3600)
        stored["expires"] = time.time() - 1
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(stored, fh)
        self.assert_denied(self.edit(self.path("payments.py")))


class FailureTest(TripwireTest):
    def assert_warned(self, result):
        code, out, err = result
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        msg = json.loads(out)["systemMessage"]
        self.assertIn("frozen tripwire failed", msg.lower())
        self.assertIn("not protecting", msg)
        self.assertNotIn("permissionDecision", out)
        self.assertNotIn("decision", json.loads(out))
        return msg

    def test_malformed_input_allows_and_warns(self):
        self.assertIn("JSONDecodeError", self.assert_warned(self.run_hook("{not json")))
        bad = {"hook_event_name": "PreToolUse", "tool_name": "Edit", "cwd": self.repo, "tool_input": "oops"}
        self.assertIn("Error", self.assert_warned(self.run_hook(bad)))

    def test_failure_on_an_override_prompt_blocks_it_with_the_warning(self):
        os.makedirs(os.path.join(self.home, ".claude"))
        open(os.path.join(self.home, ".claude", "state"), "w").close()  # state dir cannot be made
        reason = self.assert_prompt_blocked(self.prompt("frozen override payments.py"),
                                            "not protecting")
        self.assertIn("frozen tripwire failed", reason.lower())

    def test_outside_a_repository_is_silent(self):
        outside = os.path.join(self.tmp, "nowhere")
        os.mkdir(outside)
        write(os.path.join(outside, "core.py"), "# " + MARKER + "\n")
        self.assert_allowed(self.edit(os.path.join(outside, "core.py"), cwd=outside))
        self.assert_allowed(self.prompt("frozen override core.py", cwd=outside))
        self.assertEqual(self.state_files(), [])

    def test_unknown_event_is_silent(self):
        self.assert_allowed(self.run_hook({"hook_event_name": "Stop", "cwd": self.repo}))


if __name__ == "__main__":
    unittest.main()
