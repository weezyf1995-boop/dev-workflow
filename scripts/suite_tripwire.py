#!/usr/bin/env python3
"""Suite tripwire: a hook that runs a repository's own checks at the moments work is handed over.
A repository opts in with .claude/checks.json at its top level: a JSON object with optional command
strings `lint`, `touched` and `full`, each run by the shell from the top level. With no file, or no
key for the event, the hook does nothing, so it is safe at user level.
This is a tripwire, not a mechanism: it runs locally and can be bypassed. The mechanism is CI on main.
Events:
  Stop: runs `full` when the tree of main's tip is not yet recorded green for this repository (the
    record is shared by every worktree). Green records the tree, so the same tree never runs twice.
    Red exits 2 with the last lines of the failure on stderr. After two blocks for the same agent
    (session, or subagent within it) on the same tree, the next stop is let through with a
    systemMessage naming the stored failure, without running `full` again, and that agent stays
    given up on that tree: later stops pass at once. A new landing on main starts afresh.
    `full` runs in the checkout the session is in, from its top level, and only when that checkout's
    HEAD has main's tree, so a green run proves the tree it records (uncommitted changes aside).
  Another event slots in as a handler in EVENTS, with its own check name and the same Blocks rule.
Trust: with CLAUDE_PROJECT_DIR set, it acts only when the payload's cwd is inside that directory, so
a session that has moved into another clone never runs that clone's commands.
Outside a git repository, or with no main branch, it does nothing. A corrupt state file counts as
empty. On an internal error (a git call over its time budget included) it lets the stop through and
prints a one-line warning naming the error type, so it never fails unseen."""
import hashlib, json, os, signal, subprocess, sys, tempfile, time

CHECKS_FILE = os.path.join(".claude", "checks.json")
STATE = os.path.expanduser("~/.claude/state")
KEEP_TREES = 50                 # green trees remembered per repository; older ones may run again
MAX_BLOCKS = 2                  # blocks before giving up, so a suite that can't pass doesn't loop
TAIL_LINES = 40                 # lines of a failure shown to Claude
CHECK_TIMEOUT = 540             # seconds for the check command,
GIT_BUDGET = 20                 # plus seconds for all git calls, under the 600s Stop hook timeout
DEADLINE = time.time() + GIT_BUDGET


def done():
    sys.exit(0)


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          universal_newlines=True, timeout=max(0.1, DEADLINE - time.time()))


def top_level(cwd):
    if not cwd or not os.path.isdir(cwd):
        return None
    r = git(cwd, "rev-parse", "--show-toplevel")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def trusted(cwd):
    """True unless CLAUDE_PROJECT_DIR is set and cwd lies outside it."""
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return True
    project, cwd = os.path.realpath(project), os.path.realpath(cwd)
    return os.path.commonpath([project, cwd]) == project


def check_command(top, name):
    try:
        with open(os.path.join(top, CHECKS_FILE), encoding="utf-8") as f:
            checks = json.load(f)
    except FileNotFoundError:
        return None
    return checks.get(name)


def repo_key(top):
    r = git(top, "rev-parse", "--git-common-dir")
    if r.returncode != 0:
        raise RuntimeError("git rev-parse --git-common-dir failed")
    common = os.path.realpath(os.path.join(top, r.stdout.strip()))
    return hashlib.sha256(common.encode()).hexdigest()[:16]


def read_state(path):
    """A state file's object, or {} when it is missing, unreadable or not a JSON object.
    Treating a corrupt file as empty lets the next write replace it, so it can't disable the hook."""
    try:
        with open(path, encoding="utf-8") as f:
            obj = json.load(f)
    except (OSError, ValueError):
        return {}
    return obj if isinstance(obj, dict) else {}


def write_state(path, obj):
    os.makedirs(STATE, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".suite-", dir=STATE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


class Greens:
    """Trees recorded green for one repository, shared by all its worktrees."""

    def __init__(self, top):
        self.path = os.path.join(STATE, f"suite-green-{repo_key(top)}.json")
        trees = read_state(self.path).get("trees")
        self.trees = [t for t in trees if isinstance(t, str)] if isinstance(trees, list) else []

    def __contains__(self, tree):
        return tree in self.trees

    def add(self, tree):
        write_state(self.path, {"trees": (self.trees + [tree])[-KEEP_TREES:]})


class Blocks:
    """Blocks for one agent (a session, or a subagent within it) on one tree, kept in STATE, with the
    last failure so giving up can name it without running the check again."""

    def __init__(self, d, tree):
        who = f"{d.get('session_id') or ''}/{d.get('agent_id') or ''}"
        self.path = os.path.join(STATE, f"suite-blocks-{hashlib.sha256(who.encode()).hexdigest()[:16]}.json")
        self.tree = tree
        s = read_state(self.path)
        same = s.get("tree") == tree and isinstance(s.get("blocks"), int)
        self.count = s["blocks"] if same else 0
        self.failure = str(s.get("failure") or "") if same else ""
        self.gave_up = bool(s.get("gave_up")) if same else False

    def spent(self):
        return self.count >= MAX_BLOCKS

    def add(self, failure):
        self._write(blocks=self.count + 1, failure=failure, gave_up=False)

    def give_up(self):
        self._write(blocks=self.count, failure=self.failure, gave_up=True)

    def _write(self, **fields):
        write_state(self.path, dict(tree=self.tree, **fields))

    def clear(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


def run_check(top, command):
    """(passed, output, how it ended) for one check command, run by the shell from the top level.
    Running out of time counts as a failure, so a hung suite blocks rather than passing unseen."""
    p = subprocess.Popen(command, shell=True, cwd=top, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True, errors="replace",
                         start_new_session=True)
    try:
        out, _ = p.communicate(timeout=CHECK_TIMEOUT)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)  # the whole group, so no grandchild holds the pipe open
        out, _ = p.communicate()
        return False, out or "", f"timed out after {CHECK_TIMEOUT}s"
    return p.returncode == 0, out, f"exit {p.returncode}"


def tail(output):
    lines = output.rstrip("\n").splitlines()
    cut = lines[-TAIL_LINES:]
    head = f"[last {len(cut)} of {len(lines)} lines]\n" if len(lines) > len(cut) else ""
    return head + "\n".join(cut)


def block(reason):
    """Exit 2: Claude Code keeps the session going and shows stderr to Claude."""
    sys.stderr.write(reason.rstrip("\n") + "\n")
    sys.exit(2)


def let_through(message):
    print(json.dumps({"systemMessage": message}))
    sys.exit(0)


def stop(d):
    cwd = d.get("cwd")
    top = top_level(cwd)
    if not top or not trusted(cwd):
        done()
    command = check_command(top, "full")
    if not command:
        done()
    r = git(top, "rev-parse", "--verify", "-q", "refs/heads/main^{tree}")
    tree = r.stdout.strip()
    if r.returncode != 0 or not tree:
        done()                                  # no main branch: nothing has landed
    if git(top, "rev-parse", "-q", "HEAD^{tree}").stdout.strip() != tree:
        done()                                  # a run here would not prove main's tree
    greens = Greens(top)
    if tree in greens:
        done()
    blocks = Blocks(d, tree)
    if blocks.gave_up:
        done()
    if blocks.spent():
        blocks.give_up()
        let_through(f"Suite tripwire gave up after {MAX_BLOCKS} blocks and let the stop through: "
                    f"main is still not proven green. {blocks.failure}")
    passed, output, ended = run_check(top, command)
    if passed:
        greens.add(tree)
        blocks.clear()
        done()
    failure = f"`full` from {CHECKS_FILE} failed ({ended}).\n{tail(output)}"
    blocks.add(failure)
    block(f"Suite tripwire: main holds commits not yet proven green. {failure}\n"
          "Fix main and get `full` green before stopping.")


EVENTS = {"Stop": stop}


def main():
    d = json.load(sys.stdin)
    handler = EVENTS.get(d.get("hook_event_name"))
    if handler:
        handler(d)
    done()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"systemMessage":
                          f"Suite tripwire failed ({type(e).__name__}) and is not checking anything."}))
        sys.exit(0)
