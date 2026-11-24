#!/usr/bin/env python3
"""Suite tripwire: a hook that runs a repository's own checks at the moments work is handed over.
A repository opts in with .claude/checks.json at its top level: a JSON object with optional command
strings `lint`, `touched` and `full`, each run by the shell from the top level. With no file, or no
key for the event, the hook does nothing, so it is safe at user level.
This is a tripwire, not a mechanism: it runs locally and can be bypassed. The mechanism is CI on main.
Main below is the default branch: the local branch refs/remotes/origin/HEAD names, else main, else
master.
Events:
  Stop: runs `full` when the tree of main's tip is not yet recorded green for this repository (the
    record is shared by every worktree). Green records the tree, so the same tree never runs twice.
    Red exits 2 with the last lines of the failure on stderr. After two blocks for the same agent
    (session, or subagent within it) on the same tree, the next stop is let through with a
    systemMessage naming the stored failure, without running `full` again, and that agent stays
    given up on that tree: later stops pass at once. A new landing on main starts afresh.
    `full` runs in the checkout the session is in, from its top level, and only when that checkout's
    HEAD has main's tree. With staged or unstaged edits to tracked files it still runs (red still
    blocks) but records nothing, since a pass there doesn't prove the committed tree. Untracked
    files don't count.
  SubagentStop: runs `touched` only when the payload's cwd is in a linked worktree (git-dir differs
    from git-common-dir), since builders always run in one and the main checkout is never a
    builder's; and only when that worktree has changes against its base: the merge-base of HEAD
    with main, plus staged, unstaged and untracked (not ignored) files. Read-only subagents and the
    extra SubagentStop the harness fires after Stop carry the main checkout's cwd, so they pass
    without running anything, whatever work sits there. Red exits 2; the Blocks rule is Stop's, per
    agent and base, so edits between blocks don't reset the count.
  PostToolUse on Edit, Write or MultiEdit: runs `lint` in the checkout holding the edited file, with
    the file's path relative to its top level, prefixed `./` so it can't read as an option, in
    $TRIPWIRE_FILE. The edit has already happened, so
    red only informs: exit 2 with the output on stderr, and nothing is counted.
  Another event slots in as a handler in EVENTS; a stop-like one goes through guarded().
Trust: with CLAUDE_PROJECT_DIR set, it acts only when the payload's cwd (and for lint, the real path
of the edited file) is inside that directory, so a session that has moved into another clone never
runs that clone's commands.
Outside a git repository, or with no default branch, it does nothing. A corrupt state file counts as
empty. On an internal error (a git call over its time budget included) it lets the stop through and
prints a one-line warning naming the error type, so it never fails unseen.
Installed at user level and in the project: the user-level copy exits 0 silently when
$CLAUDE_PROJECT_DIR/.claude/hooks/ holds a file of its name, so each hook acts once."""
import hashlib, json, os, signal, subprocess, sys, tempfile, time

CHECKS_FILE = os.path.join(".claude", "checks.json")
STATE = os.path.expanduser("~/.claude/state")
KEEP_TREES = 50                 # green trees remembered per repository; older ones may run again
MAX_BLOCKS = 2                  # blocks before giving up, so a suite that can't pass doesn't loop
TAIL_LINES = 40                 # lines of a failure shown to Claude
CHECK_TIMEOUT = 540             # seconds for `full` or `touched`,
GIT_BUDGET = 20                 # plus seconds for all git calls, under the 600s Stop hook timeout
LINT_TIMEOUT = 90               # seconds for `lint`, plus GIT_BUDGET, under the 120s PostToolUse timeout
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
    """Blocks for one agent (a session, or a subagent within it) on one key, kept in STATE, with the
    last failure so giving up can name it without running the check again. The key is what a
    block is about: main's tree for Stop, `touched@<base>` for SubagentStop."""

    def __init__(self, d, key):
        who = f"{d.get('session_id') or ''}/{d.get('agent_id') or ''}"
        self.path = os.path.join(STATE, f"suite-blocks-{hashlib.sha256(who.encode()).hexdigest()[:16]}.json")
        self.key = key
        s = read_state(self.path)
        same = s.get("key") == key and isinstance(s.get("blocks"), int)
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
        write_state(self.path, dict(key=self.key, **fields))

    def clear(self):
        try:
            os.remove(self.path)
        except FileNotFoundError:
            pass


def run_check(top, command, env=None, timeout=CHECK_TIMEOUT):
    """(passed, output, how it ended) for one check command, run by the shell from the top level,
    with env added to the environment. Running out of time counts as a failure, so a hung suite
    blocks rather than passing unseen."""
    p = subprocess.Popen(command, shell=True, cwd=top, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, universal_newlines=True, errors="replace",
                         start_new_session=True, env=dict(os.environ, **(env or {})))
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)  # the whole group, so no grandchild holds the pipe open
        out, _ = p.communicate()
        return False, out or "", f"timed out after {timeout}s"
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


def checkout(path):
    """The top level of the trusted checkout holding path, or None (the trust check comes first,
    so no git call runs in an untrusted directory)."""
    if not path or not os.path.isdir(path) or not trusted(path):
        return None
    return top_level(path)


def guarded(d, key, top, name, blocked, fix, gave_up):
    """Run check `name` for one agent under the Blocks rule, shared by every stop-like event: red
    exits 2 naming the failure; after MAX_BLOCKS the stop passes with a systemMessage naming the
    stored failure and no rerun, and the agent stays given up on key. Returns only when green."""
    blocks = Blocks(d, key)
    if blocks.gave_up:
        done()
    if blocks.spent():
        blocks.give_up()
        let_through(f"Suite tripwire gave up after {MAX_BLOCKS} blocks and let the stop through: "
                    f"{gave_up} {blocks.failure}")
    passed, output, ended = run_check(top, check_command(top, name))
    if passed:
        blocks.clear()
        return
    failure = f"`{name}` from {CHECKS_FILE} failed ({ended}).\n{tail(output)}"
    blocks.add(failure)
    block(f"Suite tripwire: {blocked} {failure}\n{fix}")


def default_branch(top):
    """The repository's default branch, called main in this file: the local branch that
    refs/remotes/origin/HEAD names, else `main`, else `master`; None when none exists. One git call."""
    r = git(top, "for-each-ref", "--format=%(refname) %(symref)", "refs/remotes/origin/HEAD", "refs/heads/")
    if r.returncode != 0:
        return None
    heads, origin = set(), None
    for line in r.stdout.splitlines():
        ref, _, target = line.partition(" ")
        if ref == "refs/remotes/origin/HEAD" and target.startswith("refs/remotes/origin/"):
            origin = target[len("refs/remotes/origin/"):]
        elif ref.startswith("refs/heads/"):
            heads.add(ref[len("refs/heads/"):])
    for name in (origin, "main", "master"):
        if name and name in heads:
            return name
    return None


def stop(d):
    top = checkout(d.get("cwd"))
    if not top or not check_command(top, "full"):
        done()
    branch = default_branch(top)
    if not branch:
        done()                                  # no default branch: nothing has landed
    r = git(top, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{tree}}")
    tree = r.stdout.strip()
    if r.returncode != 0 or not tree:
        done()
    if git(top, "rev-parse", "-q", "HEAD^{tree}").stdout.strip() != tree:
        done()                                  # a run here would not prove main's tree
    greens = Greens(top)
    if tree in greens:
        done()
    guarded(d, tree, top, "full",
            blocked=f"{branch} holds commits not yet proven green.",
            fix=f"Fix {branch} and get `full` green before stopping.",
            gave_up=f"{branch} is still not proven green.")
    if git(top, "diff", "--quiet", "HEAD", "--").returncode == 0:
        greens.add(tree)                        # only a clean checkout proves the committed tree
    done()


def has_changes(top, base):
    """True when the checkout differs from base: commits since it, staged, unstaged or untracked
    (not ignored) files."""
    if git(top, "diff", "--quiet", base, "--").returncode != 0:
        return True
    return bool(git(top, "ls-files", "--others", "--exclude-standard").stdout.strip())


def linked_worktree(top):
    """True when top is a linked worktree (git-dir differs from git-common-dir), not the main
    checkout."""
    r = git(top, "rev-parse", "--git-dir", "--git-common-dir")
    dirs = r.stdout.split("\n")[:2]
    if r.returncode != 0 or len(dirs) != 2:
        return False
    git_dir, common = (os.path.realpath(os.path.join(top, p)) for p in dirs)
    return git_dir != common


def subagent_stop(d):
    top = checkout(d.get("cwd"))
    if not top or not check_command(top, "touched"):
        done()
    if not linked_worktree(top):
        done()                                  # reviewers, Explore agents, the post-Stop event
    branch = default_branch(top)
    if not branch:
        done()                                  # no default branch
    r = git(top, "merge-base", "HEAD", f"refs/heads/{branch}")
    base = r.stdout.strip()
    if r.returncode != 0 or not base:
        done()                                  # no history shared with main
    if not has_changes(top, base):
        done()                                  # a worktree with nothing done in it yet
    guarded(d, f"touched@{base}", top, "touched",
            blocked="this checkout's changes are not green.",
            fix="Get `touched` green before finishing.",
            gave_up="the changes are still not green.")
    done()


LINT_FILE_VAR = "TRIPWIRE_FILE"


def post_tool_use(d):
    """`lint` on the file an edit tool just changed, passed as $TRIPWIRE_FILE relative to the top
    level and prefixed `./`, so a file named `-x.py` can't reach a linter as an option. The edit
    has happened, so red only informs: exit 2 with the output, and no counting."""
    if d.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
        done()
    path = (d.get("tool_input") or {}).get("file_path")
    if not isinstance(path, str) or not os.path.isfile(path) or not checkout(d.get("cwd")):
        done()
    path = os.path.realpath(path)               # trust and the checkout follow the real file
    top = checkout(os.path.dirname(path))
    command = top and check_command(top, "lint")
    if not command:
        done()
    rel = "./" + os.path.relpath(path, os.path.realpath(top))
    passed, output, ended = run_check(top, command, {LINT_FILE_VAR: rel}, LINT_TIMEOUT)
    if not passed:
        block(f"Suite tripwire: `lint` from {CHECKS_FILE} failed on {rel} ({ended}). "
              f"The edit stands; fix what lint reports.\n{tail(output)}")
    done()


EVENTS = {"Stop": stop, "SubagentStop": subagent_stop, "PostToolUse": post_tool_use}


def defers_to_project_copy():
    """True when this run is the user-level copy (~/.claude/scripts/) and the project carries its own
    copy, $CLAUDE_PROJECT_DIR/.claude/hooks/<this file name>. Claude Code runs both entries, so the
    user-level one stands aside and the project copy alone acts. A run through the project path
    never stands aside, even when that path resolves into ~/.claude/scripts/."""
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not project:
        return False
    invoked = os.path.dirname(os.path.abspath(__file__))
    hooks = os.path.abspath(os.path.join(project, ".claude", "hooks"))
    if invoked == hooks:
        return False                            # the project copy itself
    if os.path.realpath(invoked) != os.path.realpath(os.path.expanduser("~/.claude/scripts")):
        return False                            # not the user-level copy
    return os.path.isfile(os.path.join(hooks, os.path.basename(__file__)))


def main():
    stdin = sys.stdin.read()
    if defers_to_project_copy():
        done()
    d = json.loads(stdin)
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
