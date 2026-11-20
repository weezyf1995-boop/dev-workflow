#!/usr/bin/env python3
"""Run the routing evals against the installed workflow.

Usage: python3 -B evals/run.py [--model M] [--case NAME] [--out FILE]
                               [--jobs N] [--timeout SECONDS] [--replies DIR]

Each case in cases.json runs three times. Every run gets a fresh temporary
copy of evals/fixture, with "# FROZEN CORE: money movement" added to the top
of the copied payments.py, made a git repository with one commit. The prompt
goes to the Claude Code CLI in headless print mode with JSON output and the
acceptEdits permission mode. judge.py decides each run.

Prints one line per case (green, flaky or red, pass count, reasons for failed
runs) and a summary. Exits 1 only when a case is red (2 on a usage error).
With no --model, no model is passed to the CLI, so the session default from
the user's settings is used. Assumes install.sh has been run on this machine.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import judge  # noqa: E402

FIXTURE = os.path.join(HERE, "fixture")
MARKER = "# FROZEN CORE: money movement\n"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "evals", "GIT_AUTHOR_EMAIL": "evals@example.invalid",
    "GIT_COMMITTER_NAME": "evals", "GIT_COMMITTER_EMAIL": "evals@example.invalid",
}


def load_cases():
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as f:
        return json.load(f)


def git(repo, *args):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run(["git", "-C", repo, *args], check=True, env=env,
                          capture_output=True, text=True).stdout


def make_copy():
    root = tempfile.mkdtemp(prefix="routing-eval-")
    repo = os.path.join(root, "fixture")
    shutil.copytree(FIXTURE, repo)
    path = os.path.join(repo, "payments.py")
    with open(path, encoding="utf-8") as f:
        body = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(MARKER + body)
    git(repo, "init", "-q", "-b", "main")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "fixture")
    return root, repo


def snapshot(repo):
    files = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if not (dirpath == repo and d == ".git")]
        for name in filenames:
            full = os.path.join(dirpath, name)
            with open(full, "rb") as f:
                files[os.path.relpath(full, repo)] = hashlib.sha256(f.read()).hexdigest()
    try:
        commits = int(git(repo, "rev-list", "--all", "--count").strip() or 0)
    except subprocess.CalledProcessError:
        commits = 0
    return {"files": files, "commits": commits}


KEEP_ENV = ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_")


def cli_env():
    """The environment minus the variables a running Claude Code session sets
    for its children (session id, effort, bridge, entrypoint), so a run started
    from inside a session behaves like one started from a plain terminal.
    Credentials and the config directory are kept."""
    env = {}
    for key, value in os.environ.items():
        if key.startswith("CLAUDE") and not key.startswith(KEEP_ENV):
            continue
        env[key] = value
    return env


def ask(prompt, cwd, model, timeout):
    """Return (reply text, error or None) from one headless CLI run."""
    cmd = ["claude", "-p", prompt, "--output-format", "json",
           "--permission-mode", "acceptEdits"]
    if model:
        cmd += ["--model", model]
    try:
        out = subprocess.run(cmd, cwd=cwd, env=cli_env(), capture_output=True, text=True,
                             timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return "", "timed out after %ss" % timeout
    except FileNotFoundError:
        return "", "claude CLI not found on PATH"
    try:
        data = json.loads(out.stdout)
    except ValueError:
        tail = (out.stderr or out.stdout).strip().splitlines()[-1:] or [""]
        return "", "CLI exit %s, no JSON: %s" % (out.returncode, tail[0][:160])
    reply = data.get("result") or ""
    if data.get("is_error"):
        return reply, "CLI error: %s" % (data.get("subtype") or reply[:160])
    return reply, None


def run_once(case, model, timeout):
    root, repo = make_copy()
    try:
        before = snapshot(repo)
        reply, error = ask(case["prompt"], repo, model, timeout)
        problems = judge.judge(case, reply, judge.compare(before, snapshot(repo)))
        if error:
            problems.insert(0, error)
        return reply, problems
    finally:
        shutil.rmtree(root, ignore_errors=True)


def verdict(passes, runs):
    if passes == runs:
        return "green"
    return "red" if passes == 0 else "flaky"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", help="model for the CLI (default: none passed)")
    parser.add_argument("--case", help="run only the case with this name")
    parser.add_argument("--out", help="also write the results to this file")
    parser.add_argument("--jobs", type=int, default=1, help="runs at once (default 1)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per run (default 900)")
    parser.add_argument("--replies", help="directory to save each run's reply in")
    args = parser.parse_args(argv)

    spec = load_cases()
    runs = spec["pass_rule"]["runs_per_case"]
    cases = spec["cases"]
    if args.case:
        cases = [c for c in cases if c["name"] == args.case]
        if not cases:
            print("no case named %r" % args.case, file=sys.stderr)
            return 2

    jobs = [(c, i) for c in cases for i in range(runs)]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(run_once, c, args.model, args.timeout): (c["name"], i) for c, i in jobs}
        for fut in concurrent.futures.as_completed(futures):
            results[futures[fut]] = fut.result()

    if args.replies:
        os.makedirs(args.replies, exist_ok=True)
        for (name, i), (reply, _) in results.items():
            with open(os.path.join(args.replies, "%s-%d.txt" % (name, i + 1)), "w", encoding="utf-8") as f:
                f.write(reply)

    lines = ["# Routing evals, %s, model: %s" % (
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        args.model or "session default")]
    counts = {"green": 0, "flaky": 0, "red": 0}
    for c in cases:
        failed = [(i + 1, results[(c["name"], i)][1]) for i in range(runs) if results[(c["name"], i)][1]]
        passes = runs - len(failed)
        v = verdict(passes, runs)
        counts[v] += 1
        line = "%-6s %-21s %d/%d" % (v, c["name"], passes, runs)
        if failed:
            line += "  " + " | ".join("run %d: %s" % (n, "; ".join(p)) for n, p in failed)
        lines.append(line)
    lines.append("summary: %d green, %d flaky, %d red of %d cases" % (
        counts["green"], counts["flaky"], counts["red"], len(cases)))

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 1 if counts["red"] else 0


if __name__ == "__main__":
    sys.exit(main())
