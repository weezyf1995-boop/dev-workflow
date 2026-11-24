# Wave plan: guardrails and verification (spec #24, tickets #25 to #34)

Base commit for wave 1: `97e47f0`. Written 2026-11-24, before the first builder.

| Wave | Ticket | Blocked by | Areas touched | Builder |
|---|---|---|---|---|
| 1 | #25 Context guard reports its own failures | none | context guard script, its tests, check 30 | low risk: sonnet, medium |
| 1 | #26 README cloud rules, environment check | none | README cloud section | low risk: sonnet, medium |
| 1 | #27 Settings templates, README "Guardrails" | none | `templates/` (settings), README new "Guardrails" section, new check 26 | high risk: opus, medium |
| 1 | #28 Suite tripwire tracer bullet (Stop) | none | new suite tripwire script and tests, `tests/payloads/`, new check 32, `install.sh` and installer test, README "Hooks", `.claude/checks.json` | high risk: opus, medium |
| 1 | #29 Red `main` opens an issue; CI template | none | `.github/workflows/check.yml`, `templates/` (CI), README "Protecting main" | high risk: opus, medium |
| 2 | #30 Suite tripwire: SubagentStop and PostToolUse | #28 | suite tripwire script, tests, payloads, README "Hooks" | high risk: opus, medium |
| 3 | #31 Hooks wired for cloud sessions | #25, #27, #30 | project settings template, check 26, context guard and tests, payloads, README | high risk: opus, medium |
| 4 | #32 (Sami) Merge the user template, hand tests | #27, #31 | Sami's `~/.claude/settings.json`, scratch repo | Sami |
| 5 | #33 Prose batch, cloud skill, routing evals | #26, #29, #32 | workflow file, `skills/changeable-software/`, CONTEXT.md, `cloud/`, `template.sha`, plans, README | low risk: sonnet, medium (owns the eval run) |
| 6 | #34 (Sami) `/doctor prompt-audit` | #33 | Sami's local session | Sami |

**Critical path:** #28 → #30 → #31 → #32 → #33 → #34, six tickets. Two of them are Sami's, so the run itself ends after #31 and parks there: #32 is the pending item.

**Shared area, overridden by Sami.** By the area rule, #26, #27, #28 and #29 all edit the README, so they would take turns. Sami asked for #25 to #28 at once, with #29 starting as soon as one of them lands. Each one edits a different README section, so any overlap is resolved by hand at landing. Builders: up to four at once (Sami's number). Landing is one at a time, in finish order.

## Rules that hold for every ticket

- **Terms (CONTEXT.md):** declaration, tripwire, mechanism, frozen core. "Suite tripwire" is the name of the new hook. #33 defines it in CONTEXT.md; until then, tickets may use it but don't edit CONTEXT.md.
- **ADRs:** none exist, so there is no shape to follow or contradict.
- **Frozen cores:** none in this repo. The sealed measure is the routing evals (`evals/cases.json`, the pass rule, `evals/REGISTER.md`). No ticket touches `evals/`.
- **Untouched until #33:** `workflow/dev-workflow.md`, `skills/`, CONTEXT.md, `cloud/`, `template.sha`, CLAUDE.md.
- **Never touched:** any real settings file. That means no `.claude/settings.json` in this repo and nothing under `~/.claude`. Sami merges settings between sessions.
- **`./check.sh`:** never edited. A new check is a new file in `checks/`.
- **The installer:** never touches settings.
- **Prose:** plain and short, in the README's existing style.
- **No pull requests.** Builders commit in their worktree and don't push. The coordinator lands on `main`.

## Second run: #36 alone

Written 2026-11-24, after #32 closed. #33 is being built in another session that started before this section was written, so it is not part of this run. Base commit: whatever `main` holds once #33 has landed.

| Wave | Ticket | Blocked by | Areas touched | Builder |
|---|---|---|---|---|
| 1 | #36 Context guard recognises a real subagent report | none (start after #33 lands, to keep the README out of two hands) | context guard script, its tests, `tests/payloads/`, README "Hooks" (the context guard paragraph) | high risk: opus, medium (a security control that parses harness text) |

The rules block above holds. Test payloads for #36 are the two logged on #36 and #32, trimmed of nothing but machine paths. #36 doesn't touch `workflow/`, `skills/`, CONTEXT.md, `cloud/` or `template.sha`.

**Not in any ticket.** Three #32 findings change files no open ticket owns and wait for a ruling: `github.com` on the user template's sandbox allowlist, the project template's sandbox block doing nothing in the cloud, and the Alethia entries in Sami's user settings.
