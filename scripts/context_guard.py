#!/usr/bin/env python3
"""Context-budget hooks for the dev workflow.
Rules live in ~/.claude/dev-workflow.md under "Context budget".
Events: UserPromptSubmit (warn the user, brief Claude once per tier; past HIGH Claude relays via relay.sh), PostToolUse on Bash
(nudge after oversized output), SessionStart on resume/fork (cold-cache warning).
Never blocks anything. Any error exits 0 silently."""
import json, os, sys

WARN, HIGH = 200_000, 400_000   # tokens in context (1M window; baseline is 30-100k)
BIG_OUTPUT = 8_000              # characters of tool output
STATE = os.path.expanduser("~/.claude/state")


def k(n):
    return f"{round(n / 1000)}k"


def done(obj=None):
    if obj:
        print(json.dumps(obj))
    sys.exit(0)


def last_context(path):
    """Tokens sent with the latest main-session request, read from the transcript tail."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 2_000_000))
            lines = f.read().decode("utf-8", "ignore").splitlines()
    except (OSError, TypeError):
        return 0
    for line in reversed(lines):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") != "assistant" or r.get("isSidechain"):
            continue
        u = (r.get("message") or {}).get("usage")
        if u:
            return sum(u.get(x) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    return 0


def main():
    d = json.load(sys.stdin)
    ev = d.get("hook_event_name")

    if ev == "UserPromptSubmit":
        if d.get("agent_id"):
            done()
        ctx = last_context(d.get("transcript_path"))
        if ctx < WARN:
            done()
        tier = "high" if ctx >= HIGH else "warn"
        if tier == "high":
            msg = f"Context {k(ctx)}, past the {k(HIGH)} line. Claude relays to a fresh session at the next boundary."
        else:
            msg = f"Context {k(ctx)}. Finish this unit, then /compact at the next phase boundary, or /clear if the task is done."
        res = {"systemMessage": msg}
        os.makedirs(STATE, exist_ok=True)
        flag = os.path.join(STATE, f"ctx-{d.get('session_id')}-{tier}")
        if not os.path.exists(flag):
            open(flag, "w").close()
            if tier == "high":
                todo = ("At that boundary, relay: write a handoff file (the /handoff skill's format) to the OS temp "
                        "directory, run ~/.claude/scripts/relay.sh <cwd> \"Continue from <handoff path>\", "
                        "say so in one line, and stop.")
            else:
                todo = "When you reach it, tell the user to /compact, or /clear if the task is done."
            res["hookSpecificOutput"] = {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"Context budget (dev workflow): this conversation is at about {k(ctx)} tokens. "
                    "Steer toward the next phase or ticket boundary and keep tool output short. " + todo
                ),
            }
        done(res)

    if ev == "PostToolUse":
        resp = d.get("tool_response")
        n = len(resp if isinstance(resp, str) else json.dumps(resp or ""))
        if n < BIG_OUTPUT:
            done()
        done({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": (
                f"Context budget: that command returned about {n:,} characters, which stay in context "
                "for the rest of the session. Filter at the source next time: tail, grep, quiet flags, "
                "a summary test reporter."
            ),
        }})

    if ev == "SessionStart":
        ctx = d.get("context_tokens") or 0
        if d.get("source") in ("resume", "fork") and ctx >= WARN and d.get("prompt_cache_likely_expired"):
            done({"systemMessage": (
                f"Resuming re-sends {k(ctx)} tokens with a cold cache. If the last task is done, "
                "/clear and start from the ticket or a /handoff file instead."
            )})
    done()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
