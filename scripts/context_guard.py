#!/usr/bin/env python3
"""Context-budget hooks for the dev workflow.
Rules live in ~/.claude/dev-workflow.md under "Context budget".
Events:
  UserPromptSubmit: past WARN, tell the user and brief Claude once to relay at the next phase boundary
    (or the next task boundary when no workflow step is under way). Past HIGH, the stop: a prompt is
    refused unless it is `relay`, a housekeeping slash command, a `frozen override` (the frozen
    tripwire's, which starts no new work), or starts with `override`, which lets the session run on
    for OVERRIDE_SPAN more tokens before the stop returns.
  PreToolUse on Agent/Task: past HIGH (and not overridden), deny new subagents so a long run relays
    at its next ticket boundary.
  PostToolUse on Bash: nudge after oversized output.
  SessionStart on resume/fork: cold-cache warning.
Any error exits 0 silently, so a broken guard never blocks work."""
import json, os, sys

WARN, HIGH = 200_000, 400_000   # tokens in context (1M window; baseline is 30-100k)
OVERRIDE_SPAN = 100_000         # how much further an `override` lets a session run past the stop
BIG_OUTPUT = 8_000              # characters of tool output
STATE = os.path.expanduser("~/.claude/state")
# Slash commands that tidy up or hand off rather than start new work; they pass the stop.
HOUSEKEEPING = {"clear", "compact", "handoff", "rewind", "recap", "usage", "context", "cost", "status",
                "exit", "quit", "resume", "model", "effort", "config", "help", "mcp", "memory", "fork",
                "permissions", "hooks", "doctor", "login", "logout"}
RELAY_STEPS = ("write a handoff file (the /handoff skill's format: state, next step, and for a build the "
               "wave plan, the rules block, the base commit and anything still in flight) to the OS temp "
               "directory, run ~/.claude/scripts/relay.sh <cwd> \"Continue from <handoff path>\", say so "
               "in one line, and stop.")


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


def flag_path(session, name):
    return os.path.join(STATE, f"ctx-{session}-{name}")


def overridden(session, ctx):
    """True while an earlier `override` still covers this context size."""
    try:
        with open(flag_path(session, "override")) as f:
            return ctx < int(f.read().strip()) + OVERRIDE_SPAN
    except (OSError, ValueError):
        return False


def prompt_submit(d, ctx):
    session = d.get("session_id")
    os.makedirs(STATE, exist_ok=True)

    if ctx >= HIGH and not overridden(session, ctx):
        prompt = (d.get("prompt") or "").strip()
        word = prompt.split(None, 1)[0].lower().rstrip(".,:;!") if prompt else ""
        if word.startswith("/") and word[1:].split(":")[-1] in HOUSEKEEPING:
            done()
        if prompt.split()[:2] == ["frozen", "override"]:
            done()  # the frozen tripwire's override starts no new work; that hook answers it
        if word == "relay":
            done({"systemMessage": f"Context {k(ctx)}. Claude is relaying to a fresh session.",
                  "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": (
                      f"Context budget (dev workflow): the user asked for the relay at {k(ctx)} tokens. "
                      "Do no other work first: " + RELAY_STEPS)}})
        if word == "override":
            with open(flag_path(session, "override"), "w") as f:
                f.write(str(ctx))
            done({"systemMessage": (f"Override: this session runs on until about {k(ctx + OVERRIDE_SPAN)}, "
                                    "then the stop returns."),
                  "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": (
                      "Context budget (dev workflow): the user overrode the context stop. Treat the rest of "
                      "their message, after the word override, as the request.")}})
        done({"decision": "block", "reason": (
            f"Context {k(ctx)}, past the {k(HIGH)} stop. Send `relay` to have Claude hand off to a fresh "
            f"session, or start your message with `override` to carry on for another {k(OVERRIDE_SPAN)}.")})

    # Housekeeping is Claude's: the tiers end in a relay, never in asking the user to /compact.
    if ctx >= HIGH:
        tier, where = "high", "the next boundary of any kind (a step, a ticket landing)"
        msg = f"Context {k(ctx)}, past the stop under an override. Claude relays at the next boundary."
    else:
        tier = "warn"
        where = ("the next phase boundary (spec published, tickets and wave plan written, an /implement "
                 "run landed), never mid-grill or mid-ticket; when no workflow step is under way, the next "
                 "task boundary (a request answered, a fix landed)")
        msg = (f"Context {k(ctx)}. Claude relays to a fresh session at the next phase boundary, "
               "or the next task boundary outside the workflow.")
    res = {"systemMessage": msg}
    flag = flag_path(session, tier)
    if not os.path.exists(flag):
        open(flag, "w").close()
        res["hookSpecificOutput"] = {"hookEventName": "UserPromptSubmit", "additionalContext": (
            f"Context budget (dev workflow): this conversation is at about {k(ctx)} tokens; at {k(HIGH)} "
            "the session stops taking new work. Steer toward the boundary and keep tool output short. "
            f"At {where}, relay: " + RELAY_STEPS)}
    done(res)


def main():
    d = json.load(sys.stdin)
    ev = d.get("hook_event_name")

    if ev == "UserPromptSubmit":
        if d.get("agent_id"):
            done()
        ctx = last_context(d.get("transcript_path"))
        if ctx < WARN:
            done()
        prompt_submit(d, ctx)

    if ev == "PreToolUse":
        if d.get("agent_id") or d.get("tool_name") not in ("Agent", "Task"):
            done()
        ctx = last_context(d.get("transcript_path"))
        if ctx < HIGH or overridden(d.get("session_id"), ctx):
            done()
        done({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"Context budget (dev workflow): this session is at {k(ctx)} tokens, past the {k(HIGH)} "
                "stop, so it starts no new subagents. Let anything already running finish or park it, "
                "then relay: " + RELAY_STEPS),
        }})

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
