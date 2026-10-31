"""Tests for scripts/context_guard.py, driven through its process boundary.

Each test feeds a recorded-shape hook payload (tests/payloads/) to the guard
over stdin, with HOME pointed at a fresh temp directory, and checks stdout and
the exit code. The guard's functions are never imported; its thresholds are
read from the source with ast so the tests follow any change to them.
"""
import ast
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GUARD = os.path.join(REPO, "scripts", "context_guard.py")
PAYLOADS = os.path.join(HERE, "payloads")


def read_constants(path, names):
    """Evaluate module-level literal assignments to `names` without running the script."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in names:
                found[target.id] = ast.literal_eval(node.value)
            elif isinstance(target, ast.Tuple) and isinstance(node.value, ast.Tuple):
                for t, v in zip(target.elts, node.value.elts):
                    if isinstance(t, ast.Name) and t.id in names:
                        found[t.id] = ast.literal_eval(v)
    missing = set(names) - set(found)
    if missing:
        raise RuntimeError(f"constants not found in {path}: {sorted(missing)}")
    return found


_C = read_constants(GUARD, ("WARN", "HIGH", "BIG_OUTPUT"))
WARN, HIGH, BIG_OUTPUT = _C["WARN"], _C["HIGH"], _C["BIG_OUTPUT"]


def load_payload(name):
    with open(os.path.join(PAYLOADS, name), encoding="utf-8") as f:
        return json.load(f)


def template_lines():
    with open(os.path.join(PAYLOADS, "transcript.jsonl"), encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ctxguard-")
        self.home = os.path.join(self.tmp, "home")
        os.mkdir(self.home)
        self.addCleanup(shutil.rmtree, self.tmp, True)

    # -- helpers ---------------------------------------------------------

    def run_guard(self, stdin):
        if not isinstance(stdin, str):
            stdin = json.dumps(stdin)
        env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        p = subprocess.run(
            [sys.executable or "python3", GUARD], input=stdin, env=env, cwd=self.tmp,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30,
        )
        return p.returncode, p.stdout, p.stderr

    def run_json(self, payload):
        code, out, err = self.run_guard(payload)
        self.assertEqual(code, 0, err)
        self.assertEqual(err, "")
        self.assertTrue(out.strip(), "guard printed nothing")
        return json.loads(out)

    def transcript(self, tokens, name="transcript.jsonl", extra=()):
        """Write a transcript whose assistant line reports `tokens` of context."""
        lines = template_lines()
        third = tokens // 3
        for r in lines:
            if r["type"] == "assistant":
                r["message"]["usage"].update(
                    input_tokens=tokens - 2 * third,
                    cache_read_input_tokens=third,
                    cache_creation_input_tokens=third,
                )
        lines.extend(extra)
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as f:
            for r in lines:
                f.write(json.dumps(r) + "\n")
        return path

    def prompt(self, tokens, session="sess-1", **override):
        d = load_payload("user_prompt_submit.json")
        d["session_id"] = session
        d["transcript_path"] = self.transcript(tokens, name=f"{session}-{tokens}.jsonl")
        d.update(override)
        return d

    def state_files(self):
        state = os.path.join(self.home, ".claude", "state")
        return sorted(os.listdir(state)) if os.path.isdir(state) else []


class UserPromptSubmitTest(GuardTest):
    def test_thresholds_are_sane(self):
        self.assertLess(0, WARN)
        self.assertLess(WARN, HIGH)

    def test_below_warn_is_silent(self):
        code, out, err = self.run_guard(self.prompt(WARN - 1))
        self.assertEqual((code, out), (0, ""), err)
        self.assertEqual(self.state_files(), [])

    def test_no_usage_line_is_silent(self):
        d = load_payload("user_prompt_submit.json")
        d["transcript_path"] = os.path.join(self.tmp, "missing.jsonl")
        self.assertEqual(self.run_guard(d)[:2], (0, ""))

    def test_warn_tier_briefs_claude_once_per_session(self):
        for tokens in (WARN, (WARN + HIGH) // 2, HIGH - 1):
            with self.subTest(tokens=tokens):
                session = f"warn-{tokens}"
                first = self.run_json(self.prompt(tokens, session))
                self.assertIn("/compact", first["systemMessage"])
                self.assertNotIn("relay", first["systemMessage"])
                ctx = first["hookSpecificOutput"]
                self.assertEqual(ctx["hookEventName"], "UserPromptSubmit")
                self.assertIn("/compact", ctx["additionalContext"])
                self.assertNotIn("relay.sh", ctx["additionalContext"])

                second = self.run_json(self.prompt(tokens, session))
                self.assertEqual(second, {"systemMessage": first["systemMessage"]})

    def test_high_tier_relays_once_per_session(self):
        for tokens in (HIGH, HIGH * 2):
            with self.subTest(tokens=tokens):
                session = f"high-{tokens}"
                first = self.run_json(self.prompt(tokens, session))
                self.assertIn("relays", first["systemMessage"])
                ctx = first["hookSpecificOutput"]
                self.assertEqual(ctx["hookEventName"], "UserPromptSubmit")
                self.assertIn("relay.sh", ctx["additionalContext"])

                second = self.run_json(self.prompt(tokens, session))
                self.assertEqual(second, {"systemMessage": first["systemMessage"]})

    def test_crossing_from_warn_to_high_sends_relay_instruction(self):
        self.assertIn("hookSpecificOutput", self.run_json(self.prompt(WARN, "cross")))
        high = self.run_json(self.prompt(HIGH, "cross"))
        self.assertIn("relay.sh", high["hookSpecificOutput"]["additionalContext"])

    def test_once_per_session_is_per_session(self):
        self.assertIn("hookSpecificOutput", self.run_json(self.prompt(WARN, "a")))
        self.assertIn("hookSpecificOutput", self.run_json(self.prompt(WARN, "b")))

    def test_subagent_prompt_is_silent_at_any_size(self):
        for tokens in (WARN - 1, WARN, HIGH, HIGH * 2):
            with self.subTest(tokens=tokens):
                d = self.prompt(tokens, agent_id="agent-7f3e", agent_type="general-purpose")
                self.assertEqual(self.run_guard(d)[:2], (0, ""))
        self.assertEqual(self.state_files(), [])

    def test_sidechain_usage_is_ignored(self):
        side = template_lines()[1]
        side["isSidechain"] = True
        side["message"]["usage"].update(input_tokens=HIGH * 2)
        d = load_payload("user_prompt_submit.json")
        d["transcript_path"] = self.transcript(WARN - 1, extra=[side])
        self.assertEqual(self.run_guard(d)[:2], (0, ""))

    def test_state_stays_in_temp_home(self):
        self.run_json(self.prompt(WARN, "s"))
        self.assertEqual(self.state_files(), ["ctx-s-warn"])


class PostToolUseTest(GuardTest):
    def payload(self, response):
        d = load_payload("post_tool_use_bash.json")
        d["tool_response"] = response
        return d

    def structured(self, size):
        """A Bash tool_response dict whose json.dumps length is exactly `size`."""
        resp = copy.deepcopy(load_payload("post_tool_use_bash.json")["tool_response"])
        resp["stdout"] = ""
        pad = size - len(json.dumps(resp))
        self.assertGreaterEqual(pad, 0)
        resp["stdout"] = "x" * pad
        self.assertEqual(len(json.dumps(resp)), size)
        return resp

    def assert_note(self, response, size):
        out = self.run_json(self.payload(response))
        ctx = out["hookSpecificOutput"]
        self.assertEqual(ctx["hookEventName"], "PostToolUse")
        self.assertIn(f"{size:,} characters", ctx["additionalContext"])
        self.assertNotIn("systemMessage", out)

    def test_string_response(self):
        self.assertEqual(self.run_guard(self.payload("x" * (BIG_OUTPUT - 1)))[:2], (0, ""))
        self.assert_note("x" * BIG_OUTPUT, BIG_OUTPUT)
        self.assert_note("x" * (BIG_OUTPUT * 3), BIG_OUTPUT * 3)

    def test_structured_response(self):
        self.assertEqual(self.run_guard(self.payload(self.structured(BIG_OUTPUT - 1)))[:2], (0, ""))
        self.assert_note(self.structured(BIG_OUTPUT), BIG_OUTPUT)
        self.assert_note(self.structured(BIG_OUTPUT * 3), BIG_OUTPUT * 3)

    def test_recorded_small_response_is_silent(self):
        self.assertEqual(self.run_guard(load_payload("post_tool_use_bash.json"))[:2], (0, ""))


class SessionStartTest(GuardTest):
    def payload(self, **override):
        d = load_payload("session_start_resume.json")
        d["transcript_path"] = self.transcript(WARN)
        d.update(context_tokens=WARN, prompt_cache_likely_expired=True)
        d.update(override)
        return d

    def test_cold_cache_warning_on_resume_and_fork(self):
        for source in ("resume", "fork"):
            for tokens in (WARN, HIGH):
                with self.subTest(source=source, tokens=tokens):
                    out = self.run_json(self.payload(source=source, context_tokens=tokens))
                    self.assertEqual(set(out), {"systemMessage"})
                    self.assertIn("cold cache", out["systemMessage"])

    def test_each_missing_condition_is_silent(self):
        cases = {
            "startup": dict(source="startup"),
            "clear": dict(source="clear"),
            "compact": dict(source="compact"),
            "below warn": dict(context_tokens=WARN - 1),
            "no context_tokens": dict(context_tokens=None),
            "cache warm": dict(prompt_cache_likely_expired=False),
            "cache flag absent": dict(prompt_cache_likely_expired=None),
        }
        for label, override in cases.items():
            with self.subTest(label):
                d = self.payload(**override)
                for key in [k for k, v in override.items() if v is None]:
                    del d[key]
                self.assertEqual(self.run_guard(d)[:2], (0, ""))


class MalformedInputTest(GuardTest):
    def test_malformed_stdin_is_silent(self):
        for stdin in ("", "not json", "{", "[]", "null", '"text"', "42"):
            with self.subTest(stdin=stdin):
                self.assertEqual(self.run_guard(stdin)[:2], (0, ""))

    def test_unknown_event_is_silent(self):
        d = load_payload("user_prompt_submit.json")
        d["hook_event_name"] = "Stop"
        self.assertEqual(self.run_guard(d)[:2], (0, ""))


if __name__ == "__main__":
    unittest.main()
