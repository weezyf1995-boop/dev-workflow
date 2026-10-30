#!/usr/bin/env python3
"""Context report for the dev workflow's Upkeep step.
Usage: python3 ~/.claude/scripts/context_report.py [days=7]
Reads ~/.claude/projects logs. Per session: requests, subagent requests, peak and average
context, first-request baseline (what loads before any work), and oversized tool outputs."""
import glob, json, os, statistics, sys, datetime as dt
from collections import defaultdict

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 7
WARN, BIG = 200_000, 8_000
since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS)
S = defaultdict(lambda: {"folder": "?", "start": None, "ctx": [], "sub": 0, "big": [], "seen": set()})
TOOL_OF, BIG_BY_TOOL = {}, defaultdict(lambda: [0, 0])   # tool_use id -> name; name -> [count, chars]

for f in glob.glob(os.path.expanduser("~/.claude/projects/**/*.jsonl"), recursive=True):
    if os.path.getmtime(f) < since.timestamp():
        continue
    sub = "/subagents/" in f
    for line in open(f, errors="ignore"):
        try:
            r = json.loads(line)
            t = dt.datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            continue
        if t < since:
            continue
        s = S[r.get("sessionId") or f]
        if not sub and r.get("cwd"):
            s["folder"] = os.path.basename(r["cwd"].rstrip("/")) or r["cwd"]
        s["start"] = min(s["start"] or t, t)
        m = r.get("message") or {}
        if r.get("type") == "assistant" and not sub and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    TOOL_OF[c.get("id")] = c.get("name", "?")
        if r.get("type") == "assistant" and m.get("usage"):
            key = (m.get("id"), r.get("requestId"))
            if key in s["seen"]:
                continue
            s["seen"].add(key)
            if sub:
                s["sub"] += 1
            else:
                u = m["usage"]
                s["ctx"].append(sum(u.get(x) or 0 for x in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")))
        if r.get("type") == "user" and not sub and isinstance(m.get("content"), list):
            for c in m["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    n = len(json.dumps(c.get("content")))
                    if n >= BIG:
                        s["big"].append(n)
                        b = BIG_BY_TOOL[TOOL_OF.get(c.get("tool_use_id"), "?")]
                        b[0] += 1
                        b[1] += n

rows = [s for s in S.values() if s["ctx"]]
rows.sort(key=lambda s: -max(s["ctx"]))
k = lambda n: f"{round(n / 1000)}k"
print(f"Context report, last {DAYS} days: {len(rows)} sessions\n")
print(f"{'started':<13}{'folder':<20}{'reqs':>6}{'sub':>6}{'peak':>7}{'avg':>7}{'first':>7}{'big outs':>10}")
for s in rows[:20]:
    flag = " <" if max(s["ctx"]) >= WARN else ""
    print(f"{s['start']:%b %d %H:%M} {s['folder'][:19]:<20}{len(s['ctx']):>6}{s['sub']:>6}{k(max(s['ctx'])):>7}"
          f"{k(statistics.mean(s['ctx'])):>7}{k(s['ctx'][0]):>7}{len(s['big']):>10}{flag}")
if rows:
    over = [s for s in rows if max(s["ctx"]) >= WARN]
    base = statistics.median(s["ctx"][0] for s in rows)
    reqs = sum(len(s["ctx"]) for s in rows)
    subs = sum(s["sub"] for s in rows)
    bigs = sum(len(s["big"]) for s in rows)
    print(f"\n{len(over)} of {len(rows)} sessions passed {k(WARN)} (marked <).")
    print(f"Median first request: {k(base)} (setup plus whatever the opening prompt pulls in)..")
    print(f"Subagents made {subs:,} of {reqs + subs:,} requests ({subs / max(1, reqs + subs):.0%}).")
    print(f"Tool outputs over {BIG:,} characters in main sessions: {bigs}.")
    if BIG_BY_TOOL:
        top = sorted(BIG_BY_TOOL.items(), key=lambda kv: -kv[1][1])[:5]
        print("  by tool: " + ", ".join(f"{n.split('__')[-1]} {c} ({ch // 4000}k tokens)" for n, (c, ch) in top)
              + ". Bash output is capped at 30k characters, so 30k entries hit the cap.")
