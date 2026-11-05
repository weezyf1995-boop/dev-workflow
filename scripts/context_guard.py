#!/usr/bin/env python3
"""Context-budget hooks for the dev workflow.
Rules live in ~/.claude/dev-workflow.md under "Context budget".
Events: UserPromptSubmit (tell the user, brief Claude once per tier; Claude relays via relay.sh at a phase boundary past
WARN, at any boundary past HIGH), PostToolUse on Bash
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
        # Housekeeping is Claude's: both tiers end in a relay, never in asking the user to /compact.
        # The tiers differ only in which boundary Claude waits for.
        tier = "high" if ctx >= HIGH else "warn"
        if tier == "high":
            where = "the next boundary of any kind (a step, a ticket landing)"
            msg = f"Context {k(ctx)}, past the {k(HIGH)} line. Claude relays to a fresh session at the next boundary."
        else:
            where = ("the next phase boundary (spec published, tickets and wave plan written, "
                     "an /implement run landed), never mid-grill or mid-ticket")
            msg = f"Context {k(ctx)}. Claude relays to a fresh session at the next phase boundary."
        res = {"systemMessage": msg}
        os.makedirs(STATE, exist_ok=True)
        flag = os.path.join(STATE, f"ctx-{d.get('session_id')}-{tier}")
        if not os.path.exists(flag):
            open(flag, "w").close()
            todo = (f"At {where}, relay: write a handoff file (the /handoff skill's format) to the OS temp "
                    "directory, run ~/.claude/scripts/relay.sh <cwd> \"Continue from <handoff path>\", "
                    "say so in one line, and stop.")
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
