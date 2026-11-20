# DISPOSABLE: reference for the frozen tripwire ticket of issue #16 (a reviewer-proposed hook, rebuilt and probed; it fails two probes: override does not reach worktrees, untracked marked files are missed), until that ticket lands.
"""PreToolUse: deny Edit/Write/NotebookEdit/MultiEdit to files marked FROZEN CORE.
Whole-repo scope from any cwd; identity by inode (symlinks, hardlinks, case-insensitive
FS). No Bash layer: Bash mutations and cloud sessions are known holes — a frozen core
still needs its own enforcing mechanism (purity test, fingerprinted config) per doctrine.
Override: `frozen override <path>...` allows those paths in this repo for 8 hours;
`frozen override clear` revokes. Any error exits 0 silently."""
import hashlib, json, os, subprocess, sys, time

GREP = r"^[[:space:]]*(#|//|--|;)[[:space:]]*FROZEN CORE:"
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
TTL = 8 * 3600

def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=10)

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
        "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    sys.exit(0)

def repo_root(cwd):
    r = sh(["git", "rev-parse", "--show-toplevel"], cwd)
    return r.stdout.strip() if r.returncode == 0 else None

def flag(root):
    h = hashlib.sha1(root.encode()).hexdigest()[:12]
    return os.path.expanduser(f"~/.claude/state/frozen-override-{h}")

def same(a, b):
    try:
        if os.path.exists(a) and os.path.exists(b):
            return os.path.samefile(a, b)
    except OSError:
        pass
    return os.path.realpath(a) == os.path.realpath(b)

def override_allows(root, target):
    try:
        with open(flag(root)) as f:
            d = json.load(f)
        return time.time() < d["until"] and any(same(target, p) for p in d["paths"])
    except (OSError, ValueError, KeyError):
        return False

def main():
    d = json.load(sys.stdin)
    ev = d.get("hook_event_name")
    cwd = d.get("cwd") or os.getcwd()
    if ev == "UserPromptSubmit":
        words = (d.get("prompt") or "").split()
        if words[:2] != ["frozen", "override"]:
            sys.exit(0)
        root = repo_root(cwd)
        if not root:
            sys.exit(0)
        if words[2:] == ["clear"]:
            try: os.remove(flag(root))
            except OSError: pass
            print(json.dumps({"systemMessage": "Frozen-core override cleared."}))
            sys.exit(0)
        paths = [os.path.realpath(os.path.join(root, p)) for p in words[2:]]
        paths = [p for p in paths if os.path.exists(p)]
        if not paths:
            print(json.dumps({"systemMessage":
                "Name the ruled paths: `frozen override <path>...` (repo-relative), "
                "or `frozen override clear`."}))
            sys.exit(0)
        os.makedirs(os.path.expanduser("~/.claude/state"), exist_ok=True)
        with open(flag(root), "w") as f:
            json.dump({"until": time.time() + TTL, "paths": paths}, f)
        rel = ", ".join(os.path.relpath(p, root) for p in paths)
        print(json.dumps({"systemMessage":
            f"Frozen-core override: {rel} editable in this repo for 8 hours."}))
        sys.exit(0)
    if ev != "PreToolUse" or d.get("tool_name") not in EDIT_TOOLS:
        sys.exit(0)
    ti = d.get("tool_input") or {}
    target = ti.get("file_path") or ti.get("notebook_path") or ""
    if not target:
        sys.exit(0)
    root = repo_root(cwd)
    if not root:
        sys.exit(0)
    if not os.path.isabs(target):
        target = os.path.join(cwd, target)
    frozen = [os.path.join(root, p) for p in
              sh(["git", "grep", "-lE", GREP, "--"], root).stdout.splitlines() if p]
    hit = next((p for p in frozen if same(target, p)), None)
    if hit is None or override_allows(root, target):
        sys.exit(0)
    deny(f"{os.path.relpath(hit, root)} is marked FROZEN CORE: correctness outranks "
         "changeability here. This needs the full path and a user ruling. The user can "
         "type `frozen override <path>` to allow ruled edits to named paths for 8 hours.")
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
