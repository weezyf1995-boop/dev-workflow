#!/usr/bin/env python3
"""Frozen tripwire: a hook that denies edit tools on files marked as frozen core.
Rules live in ~/.claude/dev-workflow.md beside the frozen-core rule. This is a tripwire, not a
mechanism: shell commands and cloud sessions are not covered, and each frozen core still needs its
own mechanism in the project's suite.
Events:
  PreToolUse on Edit/Write/MultiEdit/NotebookEdit (main session and subagents): deny when the target
    is, by file identity, a file in the repository carrying a marker line (a comment leader, then
    FROZEN CORE:), unless an unexpired override names it. Discovery covers the whole repository from
    its top level: tracked files and untracked files that are not ignored, text files only.
  UserPromptSubmit (main session only): `frozen override <path> [...]` opens the named paths, relative
    to the top level, for OVERRIDE_HOURS across every worktree of the repository; `frozen override
    clear` ends it. The prompt is blocked from the model and the confirmation or usage is the reason.
Outside a git repository it does nothing. On an internal error it allows the action and prints a
one-line warning naming the error type, so a broken tripwire never blocks work and never fails unseen.
Installed at user level and in the project: the user-level copy exits 0 silently when
$CLAUDE_PROJECT_DIR/.claude/hooks/ holds a file of its name, so each hook acts once."""
import hashlib, json, os, subprocess, sys, tempfile, time

EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
MARKER = r"^[[:space:]]*(#|//|--|;)[[:space:]]*FROZEN CORE:"
OVERRIDE_HOURS = 8
STATE = os.path.expanduser("~/.claude/state")
BUDGET = 8                      # seconds for all git calls, under the 10s hook timeout in the README,
DEADLINE = time.time() + BUDGET # so a slow git ends in the warning, not in the harness killing the hook
PAYLOAD = {}                    # the parsed payload, for the error path
USAGE = ("Usage: `frozen override <path> [<path>...]`, with paths relative to the repository top level, "
         "or `frozen override clear`.")


def done(obj=None):
    if obj:
        print(json.dumps(obj))
    sys.exit(0)


def remaining():
    return max(0.1, DEADLINE - time.time())


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          universal_newlines=True, timeout=remaining())


def top_level(cwd):
    """The checkout's top level, or None outside a git repository."""
    if not cwd or not os.path.isdir(cwd):
        return None
    r = git(cwd, "rev-parse", "--show-toplevel")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None


def override_file(top):
    """One override per repository: keyed by the git directory every worktree shares."""
    r = git(top, "rev-parse", "--git-common-dir")
    if r.returncode != 0:
        raise RuntimeError("git rev-parse --git-common-dir failed")
    common = os.path.realpath(os.path.join(top, r.stdout.strip()))
    key = hashlib.sha256(common.encode()).hexdigest()[:16]
    return os.path.join(STATE, f"frozen-override-{key}.json")


def frozen_files(top):
    """Repository-relative paths of every marked text file, tracked or untracked-not-ignored."""
    r = subprocess.run(["git", "grep", "-z", "-l", "-I", "-E", "--untracked", MARKER, "--"], cwd=top,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=remaining())
    if r.returncode == 1:
        return []
    if r.returncode != 0:
        raise RuntimeError("git grep failed: " + r.stderr.decode("utf-8", "replace").strip()[:200])
    return [p for p in r.stdout.decode("utf-8", "surrogateescape").split("\0") if p]


def same_file(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def overridden(top, path):
    """True while an unexpired override names a path that is, in this checkout, the same file."""
    try:
        with open(override_file(top), encoding="utf-8") as f:
            stored = json.load(f)
    except FileNotFoundError:
        return False
    if time.time() >= stored["expires"]:
        return False
    return any(same_file(os.path.join(top, p), path) for p in stored["paths"])


def pre_tool_use(d):
    if d.get("tool_name") not in EDIT_TOOLS:
        done()
    ti = d.get("tool_input") or {}
    target = ti.get("file_path") or ti.get("notebook_path")
    if not target:
        done()
    cwd = d.get("cwd") or os.getcwd()
    top = top_level(cwd)
    if not top:
        done()
    target = os.path.join(cwd, target)  # an absolute target stays as it is
    if not os.path.exists(target):
        done()                          # a write where no file exists yet
    for rel in frozen_files(top):
        hit = os.path.join(top, rel)
        if same_file(target, hit) and not overridden(top, hit):
            rel = rel.replace(os.sep, "/")
            done({"hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Frozen tripwire: {rel} is marked as a frozen core, where correctness outranks "
                    "changeability. Changing it needs the full path (changeable-software) and a ruling "
                    f"from the user. Stop and ask; the user can type `frozen override {rel}` to open it "
                    f"for {OVERRIDE_HOURS} hours."),
            }})
    done()


def prompt_submit(d):
    if d.get("agent_id"):
        done()
    words = (d.get("prompt") or "").split()
    if words[:2] != ["frozen", "override"]:
        done()
    top = top_level(d.get("cwd") or os.getcwd())
    if not top:
        done()
    store = override_file(top)
    if words[2:] == ["clear"]:
        try:
            os.remove(store)
        except FileNotFoundError:
            pass
        done({"decision": "block", "reason": "Frozen override cleared: every frozen file is denied again."})

    kept, dropped = [], []
    for p in words[2:]:
        rel = os.path.normpath(p)
        inside = not os.path.isabs(rel) and rel != ".." and not rel.startswith(".." + os.sep)
        (kept if inside and os.path.isfile(os.path.join(top, rel)) else dropped).append(p)
    kept = list(dict.fromkeys(os.path.normpath(p) for p in kept))
    note = f" Not found in this checkout, or not a file, so dropped: {', '.join(dropped)}." if dropped else ""
    if not kept:
        done({"decision": "block", "reason": f"Nothing stored.{note} {USAGE}"})

    expires = time.time() + OVERRIDE_HOURS * 3600
    os.makedirs(STATE, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".frozen-override-", dir=STATE)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"paths": kept, "expires": expires}, f)
        os.replace(tmp, store)
    except BaseException:
        os.unlink(tmp)
        raise
    until = time.strftime("%H:%M", time.localtime(expires))
    done({"decision": "block", "reason": (
        f"Frozen override: {', '.join(kept)} editable in every worktree of this repository for "
        f"{OVERRIDE_HOURS} hours (until {until}). It replaces any earlier override; "
        f"`frozen override clear` ends it.{note}")})


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
    PAYLOAD.update(d)
    ev = d.get("hook_event_name")
    if ev == "PreToolUse":
        pre_tool_use(d)
    if ev == "UserPromptSubmit":
        prompt_submit(d)
    done()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        warning = f"Frozen tripwire failed ({type(e).__name__}) and is not protecting anything."
        words = str(PAYLOAD.get("prompt") or "").split()
        if (PAYLOAD.get("hook_event_name") == "UserPromptSubmit" and not PAYLOAD.get("agent_id")
                and words[:2] == ["frozen", "override"]):
            # The override prompt is the hook's to answer; it never reaches the model, even on failure.
            print(json.dumps({"decision": "block", "reason": warning + " The override was not stored."}))
        else:
            print(json.dumps({"systemMessage": warning}))
        sys.exit(0)
