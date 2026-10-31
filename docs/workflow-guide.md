# Dev workflow guide

Your coding agent builds every task through one workflow with two layers. Matt Pocock's skills set the sequence: what happens next. The changeable-software skill sets the standard: what good looks like at each step. A workflow file ties them together, adds parallel ticket waves, and hands post-commit work to six of Addy Osmani's skills.

It's written for Claude Code. The skills are plain Markdown that Codex, Cursor and other agents can use too, but the workflow file leans on Claude Code features: the `@` import in `CLAUDE.md`, subagents in git worktrees, `/memory` and the Opus and Sonnet model rule. Another agent needs those parts adapted.

Install instructions and credits are in the [README](../README.md).

## Step 0: pick the route

Before any work, Claude sizes the request and classifies it with changeable-software. The answer picks one of seven routes.

| The request is | Route |
| --- | --- |
| Small enough for the light path (the test and its hard disqualifiers are in the workflow's Step 0) | Make the change, run feedback, run the checklist. No flow. |
| Chaotic: broken right now | `/diagnosing-bugs`. Stabilise, then understand. |
| Clear | Main flow, no prototype detour. |
| Complicated: a knowledge gap | `/research` first, then main flow at `/grill-with-docs`. |
| Complex: only trying will tell | Main flow, with the prototype detour mandatory. |
| Too big and foggy for one session | `/wayfinder`, which joins the main flow at `/to-spec`. |
| A bug or request you didn't write | `/triage`, then `/implement`. |

A frozen core or sealed measure forces the full path at any size.

## The main flow

Commands in bold are ones only you can start; Claude stops and names them when they're due.

1. **/setup-matt-pocock-skills**, once per repo. It records your issue tracker and label names.
2. **/grill-with-docs** (no repo yet: **/grill-me**). Claude questions the idea until it's sharp. Every concept gets exactly one name, recorded in `CONTEXT.md`.
3. Prototype detour, when only running code can answer a question: Claude runs /prototype in a subagent in its own git worktree, and only the answer comes back into the grilling. Mandatory for complex problems.
4. Interfaces first. Before the work is split, Claude writes the interfaces, says where the complexity went and who pays for it, and makes the first ticket the thinnest end-to-end slice. An interface with two or more callers, or one in front of a frozen core, gets designed twice by parallel subagents before the shape is settled.
5. **/to-spec**, then **/to-tickets**. Tickets are vertical slices, each listing the tickets that block it.
6. The wave plan, which Claude writes without being asked (next section).
7. **/implement**, once, against the plan. Planning (steps 2 to 6) runs on a cheaper model; the build runs on Opus. Claude hands over by relay: it writes a handoff file and opens a fresh session with `/implement <handoff>` typed in, so you press Enter rather than switching models mid-session. In each ticket Claude names its feedback loop and works test-first with /tdd where that honestly fits.
8. /code-review before every commit, with changeable-software's review checklist and codebase-design as the standards sources. Claude runs this itself; it's an instruction, not an enforced gate.

Keep steps 2 to 5 in one session. Past 200k tokens, compact at the next step boundary; past 400k, Claude relays to a fresh session at the next boundary.

## Waves: tickets in parallel

After /to-tickets, Claude groups the tickets into waves so independent ones build at the same time. With fewer than three tickets, or one straight chain, it skips this and says so.

- **Layering.** Wave 1 is every ticket with no blockers. Wave N is every ticket whose blockers all sit in earlier waves.
- **Clashes.** No blocker doesn't mean safe to run together. Two tickets in one wave that touch the same area (a migration, a shared type, config, a lockfile) can't build at once, so one drops a wave. Unsure counts as a clash.
- **Shared rules.** Under the plan, Claude writes the rules every ticket must hold: the vocabulary, the ADR shape, the frozen cores, and what no ticket touches. Every builder gets that block, and a ticket that would break one stops.
- **Critical path.** The plan names the longest chain of blocking tickets. However many builders run, the build can't finish faster than that chain, so a long one means reworking the breakdown, not adding builders.
- **Builders.** Each ticket builds as a fresh subagent in its own git worktree, at most three at once unless you set another number.
- **Frontier, not waves.** A ticket starts the moment its own blockers have landed and no running builder holds any of its areas, without waiting for the rest of its wave. The waves are the plan you read; the frontier is what runs.
- **Landing.** Finished tickets land one at a time: rebase onto main, run the full suite, merge.

## The build loop for each ticket

These defaults came from building a production app. A repo can tighten them with its own ticket loop, but can't drop them.

- **Model by risk.** Opus for anything touching stored data, parsing, imports, exports, time zones, money or auth; Sonnet for narrow UI and copy. The same rule picks the reviewer.
- **Commands for mechanical checks.** Tests, lint and snapshot diffs are commands; a reviewer agent is spent only on judgement.
- **One full test run.** The builder runs only the touched tests plus a build. The coordinator runs the full suite once, on the commit that will land.
- **One fix round.** Blocking findings go back to the same builder, which still has its context. Speculative polish is deferred to the report.
- **No waiting on you.** Gaps in a ticket are settled by the nearest precedent and recorded as Choices in its report. A ticket that turns out to be wrong is different: the builder stops and reports. It may continue only when all three hold: the revision is reversible by configuration or a single revert, nothing has run for real, and the pending ruling is listed at the top of the report.
- **One commit per ticket**, its message naming each reviewer, its model and its verdict. The report says what changed in plain words, not as a diff.

## Keeping context small

Every request re-sends the whole conversation, so cost grows with context size times the number of calls. The hooks in `scripts/context_guard.py` warn past 200k and 400k tokens and nudge Claude after any shell output over 8,000 characters. `scripts/context_report.py` shows, per session, the peak context, the setup cost before any work, and which tools produced the oversized outputs. Run it weekly and tighten one rule at a time. Claude keeps one task per session, filters shell output at the source, and briefs subagents with the ticket and the diff, never the conversation.

After the commit, Addy Osmani's six skills take over when the work is shipping, instrumenting, hardening, retiring or speeding something up.
