#!/usr/bin/env python3
"""Check the settings templates against the README's Guardrails deny list.

Usage: check_settings_templates.py [REPO_ROOT]

The README's "Guardrails" section holds the one deny list, as a text block
between the markers below. Both templates must carry every rule in it. The
project template must also wire the README "Hooks" entries (HOOKS below)
through $CLAUDE_PROJECT_DIR, so cloud sessions run the hooks.
Exit 0 when every check passes; exit 1 with one line per problem otherwise.
"""
import json
import os
import re
import sys

START = "<!-- guardrails-deny-list:start -->"
END = "<!-- guardrails-deny-list:end -->"
USER = "templates/user-settings.json"
PROJECT = "templates/project-settings.json"
TEMPLATES = (USER, PROJECT)
# Where a project repo keeps its copies of the hook scripts, so cloud sessions can run them.
PROJECT_HOOKS_DIR = "$CLAUDE_PROJECT_DIR/.claude/hooks/"
# The hook entries of README "Hooks" as (event, matcher or None, script). The project template
# must wire each one through PROJECT_HOOKS_DIR.
HOOKS = (
    ("SessionStart", "resume|fork", "context_guard.py"),
    ("UserPromptSubmit", None, "context_guard.py"),
    ("UserPromptSubmit", None, "frozen_tripwire.py"),
    ("PreToolUse", "Agent|Task", "context_guard.py"),
    ("PreToolUse", "Edit|Write|MultiEdit|NotebookEdit", "frozen_tripwire.py"),
    ("PostToolUse", "Bash", "context_guard.py"),
    ("PostToolUse", "Edit|Write|MultiEdit", "suite_tripwire.py"),
    ("SubagentStop", None, "suite_tripwire.py"),
    ("Stop", None, "suite_tripwire.py"),
)


def readme_rules(root):
    """The deny rules listed in the README block, one per non-blank line."""
    text = open(os.path.join(root, "README.md"), encoding="utf-8").read()
    m = re.search(re.escape(START) + r"\s*```[a-z]*\n(.*?)\n```\s*" + re.escape(END), text, re.S)
    if m is None:
        raise ValueError("README.md: no deny list between " + START + " and " + END)
    rules = [line.strip() for line in m.group(1).splitlines() if line.strip()]
    if not rules:
        raise ValueError("README.md: the deny list is empty")
    return rules


def glob_regex(pattern):
    """Gitignore-style glob to regex: ** spans directories, * and ? stay in one."""
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def denies_env_example(path):
    """True when a deny path would match a .env.example file in a project."""
    if path.startswith("!"):
        return False
    for prefix in ("//", "~/", "./", "/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    rx = glob_regex(path)
    if "/" not in path:
        return bool(rx.match(".env.example"))
    return any(rx.match(c) for c in (".env.example", "app/.env.example", "home/me/app/.env.example"))


def deny_paths(data):
    """Each denied path in a template, as (where it came from, path)."""
    for rule in data.get("permissions", {}).get("deny", []):
        m = re.fullmatch(r"(?:Read|Edit)\((.*)\)", rule)
        if m:
            yield rule, m.group(1)
    sandbox = data.get("sandbox", {})
    for path in sandbox.get("filesystem", {}).get("denyRead", []):
        yield "sandbox.filesystem.denyRead " + path, path
    for entry in sandbox.get("credentials", {}).get("files", []):
        if entry.get("mode") == "deny":
            yield "sandbox.credentials.files " + entry.get("path", ""), entry.get("path", "")


def sandbox_problems(rel, data, rules):
    """The sandbox must back the README list: Read(~/X/**) needs a
    credentials.files deny for ~/X, and Read(<.env name>) a denyRead entry
    ending in /<.env name>."""
    problems = []
    sandbox = data.get("sandbox", {})
    if sandbox.get("enabled") is not True:
        problems.append(rel + ": sandbox.enabled is not true")
    creds = {e.get("path") for e in sandbox.get("credentials", {}).get("files", [])
             if e.get("mode") == "deny"}
    deny_read = sandbox.get("filesystem", {}).get("denyRead", [])
    for rule in rules:
        m = re.fullmatch(r"Read\(~/([^/*]+)/\*\*\)", rule)
        if m and "~/" + m.group(1) not in creds:
            problems.append(rel + ": sandbox.credentials.files has no deny for ~/" + m.group(1)
                            + " (README.md denies " + rule + ")")
        m = re.fullmatch(r"Read\((\.env[^/]*)\)", rule)
        if m and not any(p.endswith("/" + m.group(1)) for p in deny_read):
            problems.append(rel + ": sandbox.filesystem.denyRead has no entry for " + m.group(1)
                            + " (README.md denies " + rule + ")")
    return problems


def hook_problems(rel, data):
    """Each README hook entry must sit in the project template on the same event and matcher,
    calling the script from PROJECT_HOOKS_DIR."""
    problems = []
    hooks = data.get("hooks") if isinstance(data.get("hooks"), dict) else {}
    for event, matcher, script in HOOKS:
        found = any(
            group.get("matcher") == matcher
            and any(PROJECT_HOOKS_DIR + script in (h.get("command") or "")
                    for h in group.get("hooks", []) if isinstance(h, dict))
            for group in hooks.get(event, []) if isinstance(group, dict))
        if not found:
            where = event + (" (matcher " + matcher + ")" if matcher else "")
            problems.append(rel + ": hooks." + where + " does not call " + PROJECT_HOOKS_DIR + script)
    return problems


def check(root):
    problems = []
    try:
        rules = readme_rules(root)
    except (OSError, ValueError) as e:
        return [str(e)]
    for rel in TEMPLATES:
        try:
            data = json.load(open(os.path.join(root, rel), encoding="utf-8"))
        except (OSError, ValueError) as e:
            problems.append(rel + ": does not parse as JSON (" + str(e) + ")")
            continue
        deny = data.get("permissions", {}).get("deny", [])
        for rule in rules:
            if rule not in deny:
                problems.append(rel + ": permissions.deny lacks " + rule + " (named in README.md)")
        problems += sandbox_problems(rel, data, rules)
        for where, path in deny_paths(data):
            if denies_env_example(path):
                problems.append(rel + ": " + where + " denies .env.example, which must stay readable")
        if rel == PROJECT and "autoMode" in data:
            problems.append(rel + ": carries autoMode, which project settings ignore; keep it in the user template")
        if rel == PROJECT:
            problems += hook_problems(rel, data)
    return problems


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    problems = check(root)
    for p in problems:
        print(p)
    if problems:
        return 1
    print("settings templates carry the README deny list and the project template wires the hooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
