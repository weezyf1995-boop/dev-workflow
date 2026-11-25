#!/usr/bin/env python3
"""Run the routing evals against the installed workflow.

Usage: python3 -B evals/run.py [--case NAME] [--out FILE] [--replies DIR]
                               [--jobs N] [--timeout SECONDS]
                               [--model M] [--effort E] [--no-baseline]
       python3 -B evals/run.py --write-baseline RUN1 RUN2 RUN3

Each case in cases.json runs three times. Every run gets a fresh temporary
copy of evals/fixture, with "# FROZEN CORE: money movement" added to the top
of the copied payments.py, made a git repository with one commit. The prompt
goes to the Claude Code CLI in headless print mode with JSON output and the
acceptEdits permission mode. judge.py decides each run.

The model and effort are pinned: DEFAULT_MODEL and DEFAULT_EFFORT repeat the
Coordinator row of the Models table in workflow/dev-workflow.md, and
checks/24-model-names.sh fails when they differ. --model and --effort override
them for a one-off run. Assumes install.sh has been run on this machine.

Prints one line per case (green, flaky or red, pass count, reasons for failed
runs) and a summary, then compares the run with the floor in
results/baseline.txt and prints one line per regression: a red case, or a case
two or more runs below its floor. Exits 1 on any regression (2 on a usage
error). --no-baseline skips the comparison, leaving red cases as the only
regressions. A baseline that is missing, is not a floor or was taken with
another model or effort gets one warning line and is treated the same way. A
case with no line in the floor is named in one warning line and can regress
only by going red.

--write-baseline runs nothing. It reads three result files written with --out,
each a full run with the pinned model and effort and its own header timestamp,
and writes results/baseline.txt: per case, the worst pass count of the three.
An input that breaks a rule is refused (exit 2) and the baseline is left alone.
"""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import judge  # noqa: E402

# The Coordinator row of the Models table in workflow/dev-workflow.md.
# checks/24-model-names.sh fails when these stop matching it.
DEFAULT_MODEL = "opus"
DEFAULT_EFFORT = "high"
# The levels `claude --help` documents for --effort.
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")

FIXTURE = os.path.join(HERE, "fixture")
BASELINE = os.path.join(HERE, "results", "baseline.txt")
BASELINE_NAME = "evals/results/baseline.txt"  # what messages call it
MARKER = "# FROZEN CORE: money movement\n"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "evals", "GIT_AUTHOR_EMAIL": "evals@example.invalid",
    "GIT_COMMITTER_NAME": "evals", "GIT_COMMITTER_EMAIL": "evals@example.invalid",
}

# Result files and the floor file share one case line: "green  name  3/3  reasons".
CASE_LINE = re.compile(r"^(green|flaky|red)\s+(\S+)\s+(\d+)/(\d+)(?:\s|$)")
RUN_HEADER = re.compile(r"^# Routing evals, (?P<when>[^,]+), model: (?P<model>[^,]+?)"
                        r"(?:, effort: (?P<effort>\S+))?\s*$")
FLOOR_PREFIX = "# Routing evals floor"
FLOOR_TITLE = FLOOR_PREFIX + ": the worst result per case across three full runs"
FLOOR_RUNS = re.compile(r"^# runs: (.+)$")
FLOOR_SETTINGS = re.compile(r"^# model: (\S+), effort: (\S+)\s*$")

# passes maps a case name to (runs passed, runs made).
Run = namedtuple("Run", "when model effort passes")
Floor = namedtuple("Floor", "sources model effort passes")


def load_cases():
    with open(os.path.join(HERE, "cases.json"), encoding="utf-8") as f:
        return json.load(f)


# Results, the floor and the comparison: pure functions, tested without a model call.

def verdict(passes, runs):
    if passes == runs:
        return "green"
    return "red" if passes == 0 else "flaky"


def case_line(name, passes, runs):
    return "%-6s %-21s %d/%d" % (verdict(passes, runs), name, passes, runs)


def run_header(when, model, effort):
    return "# Routing evals, %s, model: %s, effort: %s" % (when, model, effort)


def parse_case_lines(text):
    passes = {}
    for line in text.splitlines():
        m = CASE_LINE.match(line)
        if m:
            passes[m.group(2)] = (int(m.group(3)), int(m.group(4)))
    return passes


def parse_run(text):
    """A result file as a Run, or None when it does not open with a run header.
    A header from before the model and effort were pinned gives effort None."""
    m = RUN_HEADER.match(text.split("\n", 1)[0])
    if not m:
        return None
    return Run(m.group("when").strip(), m.group("model").strip(), m.group("effort"),
               parse_case_lines(text))


def build_floor(named_runs, case_names, runs_per_case):
    """The floor of three full runs: per case, the worst pass count.
    named_runs is [(label, Run or None)]. Raises ValueError, naming the input,
    when a run is not a full run of case_names or the runs differ in model or
    effort."""
    if len(named_runs) != 3:
        raise ValueError("a floor needs three runs, got %d" % len(named_runs))
    for label, run in named_runs:
        if run is None:
            raise ValueError("%s: not a result file (no '# Routing evals, ...' header)" % label)
        if not run.effort:
            raise ValueError("%s: its header names no effort, so it predates the pinned model "
                             "and effort" % label)
        missing = [n for n in case_names if n not in run.passes]
        if missing:
            raise ValueError("%s: not a full run, no result for %s" % (label, ", ".join(missing)))
        extra = [n for n in run.passes if n not in case_names]
        if extra:
            raise ValueError("%s: has results for cases that are not in cases.json: %s"
                             % (label, ", ".join(extra)))
        short = [n for n in case_names if run.passes[n][1] != runs_per_case]
        if short:
            raise ValueError("%s: not %d runs per case for %s"
                             % (label, runs_per_case, ", ".join(short)))
    first = named_runs[0][1]
    for label, run in named_runs[1:]:
        if (run.model, run.effort) != (first.model, first.effort):
            raise ValueError("%s: model %s, effort %s, but %s has model %s, effort %s"
                             % (label, run.model, run.effort, named_runs[0][0],
                                first.model, first.effort))
    passes = {n: (min(run.passes[n][0] for _, run in named_runs), runs_per_case)
              for n in case_names}
    return Floor([run.when for _, run in named_runs], first.model, first.effort, passes)


def floor_text(floor):
    lines = [FLOOR_TITLE,
             "# runs: %s" % " | ".join(floor.sources),
             "# model: %s, effort: %s" % (floor.model, floor.effort)]
    lines += [case_line(name, passes, runs) for name, (passes, runs) in floor.passes.items()]
    return "\n".join(lines) + "\n"


def parse_floor(text):
    """A baseline file as a Floor, or None when it is not one (for example a
    single run's result file, which is what the baseline held before floors)."""
    lines = text.splitlines()
    if len(lines) < 3 or not lines[0].startswith(FLOOR_PREFIX):
        return None
    sources, settings = FLOOR_RUNS.match(lines[1]), FLOOR_SETTINGS.match(lines[2])
    passes = parse_case_lines(text)
    if not (sources and settings and passes):
        return None
    return Floor([s.strip() for s in sources.group(1).split("|")],
                 settings.group(1), settings.group(2), passes)


def floor_for(baseline_text, model, effort):
    """Return (floor passes to compare a run with, one line saying what was
    compared or why nothing was). baseline_text is None when there is no
    baseline file. With nothing to compare, the passes are empty and only red
    cases are regressions."""
    if baseline_text is None:
        return {}, "baseline: %s not found; not compared, red cases only" % BASELINE_NAME
    floor = parse_floor(baseline_text)
    if floor is None:
        return {}, ("baseline: %s is not a three-run floor (build one with --write-baseline); "
                    "not compared, red cases only" % BASELINE_NAME)
    if (floor.model, floor.effort) != (model, effort):
        return {}, ("baseline: the floor is for model %s, effort %s and this run used model %s, "
                    "effort %s; not compared, red cases only"
                    % (floor.model, floor.effort, model, effort))
    return floor.passes, "baseline: compared with the floor of runs %s" % " | ".join(floor.sources)


def no_floor_note(passes, floor_passes):
    """One warning line naming the cases of a run that have no line in the
    floor it was compared with, or None when every case has one or there was
    no floor to compare with."""
    missing = [name for name in passes if name not in floor_passes]
    if not floor_passes or not missing:
        return None
    return "baseline: no floor for %s; compared for red only" % ", ".join(missing)


def regressions(passes, floor_passes):
    """One line per regression under the sealed pass rule: a red case, or a
    case two or more runs below its floor. floor_passes is empty when there is
    no floor to compare with; a case with no floor regresses only by going red."""
    lines = []
    for name, (got, runs) in passes.items():
        floor = floor_passes.get(name)
        if got == 0:
            lines.append("regression: %s is red (0/%d)" % (name, runs))
        elif floor is not None and floor[0] - got >= 2:
            lines.append("regression: %s is %d/%d, %d runs below its floor of %d/%d"
                         % (name, got, runs, floor[0] - got, floor[0], floor[1]))
    return lines


def command(prompt, model, effort):
    return ["claude", "-p", prompt, "--output-format", "json",
            "--permission-mode", "acceptEdits", "--model", model, "--effort", effort]


# Running the cases: the fixture copy, the CLI and the files.

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


def ask(prompt, cwd, model, effort, timeout):
    """Return (reply text, error or None) from one headless CLI run."""
    try:
        out = subprocess.run(command(prompt, model, effort), cwd=cwd, env=cli_env(),
                             capture_output=True, text=True, timeout=timeout,
                             stdin=subprocess.DEVNULL)
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


def run_once(case, model, effort, timeout):
    root, repo = make_copy()
    try:
        before = snapshot(repo)
        reply, error = ask(case["prompt"], repo, model, effort, timeout)
        problems = judge.judge(case, reply, judge.compare(before, snapshot(repo)))
        if error:
            problems.insert(0, error)
        return reply, problems
    finally:
        shutil.rmtree(root, ignore_errors=True)


def read_baseline():
    try:
        with open(BASELINE, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return None


def write_baseline(paths, case_names, runs_per_case):
    """Build the floor from three result files and write the baseline.
    Returns the exit status: 2, with the baseline untouched, when an input
    cannot be used, two files carry the same header timestamp, or the runs
    were not made with the pinned model and effort."""
    if len({os.path.realpath(p) for p in paths}) != len(paths):
        print("--write-baseline needs three different result files", file=sys.stderr)
        return 2
    named_runs = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                named_runs.append((path, parse_run(f.read())))
        except OSError as exc:
            print("%s: %s" % (path, exc.strerror or exc), file=sys.stderr)
            return 2
    try:
        floor = build_floor(named_runs, case_names, runs_per_case)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    seen = {}
    for path, run in named_runs:
        if run.when in seen:
            print("--write-baseline needs three separate runs: %s and %s carry the same header "
                  "timestamp (%s)" % (seen[run.when], path, run.when), file=sys.stderr)
            return 2
        seen[run.when] = path
    if (floor.model, floor.effort) != (DEFAULT_MODEL, DEFAULT_EFFORT):
        print("--write-baseline needs runs with the pinned model and effort (model %s, effort %s): "
              "these have model %s, effort %s"
              % (DEFAULT_MODEL, DEFAULT_EFFORT, floor.model, floor.effort), file=sys.stderr)
        return 2
    text = floor_text(floor)
    with open(BASELINE, "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.write(text)
    print("wrote %s" % BASELINE_NAME)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help="model for the CLI (default: %(default)s, the coordinator's)")
    parser.add_argument("--effort", default=DEFAULT_EFFORT, choices=EFFORT_LEVELS,
                        help="effort for the CLI (default: %(default)s, the coordinator's)")
    parser.add_argument("--case", help="run only the case with this name")
    parser.add_argument("--out", help="also write the results to this file")
    parser.add_argument("--jobs", type=int, default=1, help="runs at once (default 1)")
    parser.add_argument("--timeout", type=int, default=900, help="seconds per run (default 900)")
    parser.add_argument("--replies", help="directory to save each run's reply in")
    parser.add_argument("--no-baseline", action="store_true",
                        help="do not compare the run with the floor in " + BASELINE_NAME)
    parser.add_argument("--write-baseline", nargs=3, metavar=("RUN1", "RUN2", "RUN3"),
                        help="run nothing: write " + BASELINE_NAME + " as the floor of three "
                             "full-run result files")
    args = parser.parse_args(argv)

    spec = load_cases()
    runs = spec["pass_rule"]["runs_per_case"]
    cases = spec["cases"]
    if args.write_baseline:
        return write_baseline(args.write_baseline, [c["name"] for c in cases], runs)
    if args.case:
        cases = [c for c in cases if c["name"] == args.case]
        if not cases:
            print("no case named %r" % args.case, file=sys.stderr)
            return 2

    jobs = [(c, i) for c in cases for i in range(runs)]
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = {pool.submit(run_once, c, args.model, args.effort, args.timeout): (c["name"], i)
                   for c, i in jobs}
        for fut in concurrent.futures.as_completed(futures):
            try:
                results[futures[fut]] = fut.result()
            except Exception as exc:  # one broken run must not lose the others
                results[futures[fut]] = ("", ["runner error: %s" % exc])

    if args.replies:
        os.makedirs(args.replies, exist_ok=True)
        for (name, i), (reply, _) in results.items():
            with open(os.path.join(args.replies, "%s-%d.txt" % (name, i + 1)), "w", encoding="utf-8") as f:
                f.write(reply)

    when = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [run_header(when, args.model, args.effort)]
    counts = {"green": 0, "flaky": 0, "red": 0}
    passed = {}
    for c in cases:
        failed = [(i + 1, results[(c["name"], i)][1]) for i in range(runs) if results[(c["name"], i)][1]]
        passes = runs - len(failed)
        passed[c["name"]] = (passes, runs)
        counts[verdict(passes, runs)] += 1
        line = case_line(c["name"], passes, runs)
        if failed:
            line += "  " + " | ".join("run %d: %s" % (n, "; ".join(p)) for n, p in failed)
        lines.append(line)
    lines.append("summary: %d green, %d flaky, %d red of %d cases" % (
        counts["green"], counts["flaky"], counts["red"], len(cases)))

    floor_passes = {}
    if not args.no_baseline:
        floor_passes, note = floor_for(read_baseline(), args.model, args.effort)
        lines.append(note)
        partial = no_floor_note(passed, floor_passes)
        if partial:
            lines.append(partial)
    regressed = regressions(passed, floor_passes)
    lines += regressed

    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
    return 1 if regressed else 0


if __name__ == "__main__":
    sys.exit(main())
