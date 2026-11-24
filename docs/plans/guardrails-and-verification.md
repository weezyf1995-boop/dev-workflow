# Guardrails and verification plan for dev-workflow

## Context

Lydia Hallie's talk moves steering, approving and checking from the person to the model, the harness and the environment. Her rule: write a hard rule for anything that can't be undone, leave the rest to the model. Compared with `workflow/dev-workflow.md`, the workflow already matches or beats her on coordination, models, context and review. It has seven gaps, almost all in the layer under the prose: permissions, hooks, CI and the cloud environment. Today those are declarations (CONTEXT.md's word for a rule that exists only as prose). This plan turns the ones that guard irreversible actions into tripwires or mechanisms, and leaves the rest alone.

Path check (changeable-software): full path. The change touches security controls and the workflow's own rules. Classification: complicated, and the knowledge gap is closed below, except two points that only a probe can answer (marked **Probe**).

## Rulings (grilled 2026-11-24, Sami took every recommendation)

1. **Scope.** This build changes the dev-workflow repo only: the workflow file, templates, scripts and its own CI. Project repos adopt the templates one at a time afterwards, through a once-per-repo step the workflow names, after one full run here has shown the hooks behave.
2. **Permission mode.** Auto mode is the stated default for an `/implement` run. Deny rules and the sandbox apply in every mode.
3. **Risk review.** Tickets that touch a frozen core, money, auth or the shape of stored data land as normal and are listed in the final report under "Read before deploying". Deploys are hard-denied in auto mode. Nothing parks for review.
4. **Frozen cores and the sandbox.** No `denyWrite` entries for frozen files. The tripwire, the per-core mechanism and CI on `main` stay the controls, and `frozen override` keeps working.
5. **Red `main`.** GitHub-hosted Actions. A job opens a `ready-for-agent` issue when `main` goes red, and the coordinator reads the runs for its own landing commits before the final report. No Claude action with push rights.
6. **Sandbox strictness.** `allowUnsandboxedCommands` starts `true`, with `hard_deny` on unsandboxed reads of `~/.ssh`, `~/.aws` and `.env` files. Tighten to `false` after two weeks of "Where I needed you" reports show which commands need `excludedCommands`.
7. **Full suite on Stop.** The Stop hook runs the full suite only when `main` holds commits not yet recorded green, so it fires around landings and not after every edit.
8. **A builder that can't go green.** Two blocks, then it is let through with a message naming the failure. The coordinator counts that as one failed build under the fallback rule.
9. **Secrets deny list.** Deny `.env`, `.env.local`, `.env.*.local` and `.env.production`. `.env.example` stays readable.
10. **changeable-software.** Amend the skill's "Where the answers live" (owner's amendment, dated); no second local override in the workflow.

Still open, and not yours to decide: the cloud-hooks probe.

## What the docs say (verified 2026-11-23, code.claude.com/docs/en, Claude Code 2.1.331 current)

| Handover claim | Verdict |
|---|---|
| `/doctor prompt-audit`, 2.1.283+ | Exists as stated. Alias `/checkup prompt-audit`. Runs through the bundled claude-api skill. |
| `/auto-mode-setup`; `autoMode.environment` / `allow` / `hard_deny` | Exists. There is a fourth key, `autoMode.soft_deny`. Entries are prose. `"$defaults"` keeps the built-in rules. Read from `~/.claude/settings.json`, managed settings and `--settings` only: **project settings are ignored**. `/auto-mode-setup` is not available in cloud sessions. Inspect with `claude auto-mode config` and `claude auto-mode defaults`. |
| Deny rules checked first in every mode | Correct: deny, then ask, then allow, in every mode including bypassPermissions, and before the auto mode classifier. `Read(.env)` means `Read(**/.env)`. Read/Edit denies also stop `cat`, `head`, `tail`, `sed`, `tee` and redirections, but not `grep -r` or a script that opens the file. |
| `/sandbox`; can a sandboxed command read `~/.ssh`? | Exists, off by default, macOS/Linux/WSL2. **`~/.ssh` and `~/.aws/credentials` are readable by default**; writes are limited to the working directory and temp. Block with `sandbox.credentials.files` (`{"path": "~/.ssh", "mode": "deny"}`) or `sandbox.filesystem.denyRead`. Claude can retry outside the sandbox unless `sandbox.allowUnsandboxedCommands` is `false`. Sandbox arrays merge across scopes, so project settings can add denies. Not confirmed for cloud sessions. |
| Exit 2 blocks, exit 1 doesn't | Correct. Exit 2 blocks PreToolUse, UserPromptSubmit, Stop, SubagentStop, TaskCompleted, TeammateIdle, PreCompact. PostToolUse can't block (the tool ran) but its stderr goes to Claude. SessionStart and SessionEnd can't block. JSON `decision: "block"` on exit 0 is an equal alternative. Settings hooks also fire inside subagents. `TaskCompleted` fires on a TaskUpdate completion, so a builder subagent finishing is `SubagentStop`. |
| Cloud network allowlist, secrets, setup script | Levels are None / Limited / Full. Environment variables are readable inside the VM. Network secrets are added by a proxy after the request leaves the VM, and cannot be used for Anthropic's own hosts. Setup script runs before Claude starts. Cloud sessions read only the repo's `.claude/settings.json`, not the Mac's `~/.claude`. |
| CI auto-fix on pushes to `main` | **Not documented.** Auto-fix (`/autofix-pr`, the toggle, PR Steward) is pull-request only. The GitHub Action can run on any event with a `prompt`, so a custom `workflow_run` job on `main` is possible but unsupported. |

Not found, so dropped: `claude auto-mode critique`, and a "Trusted" or "Custom" network level.

## Hook audit (the handover's exit-1 question)

No hook in the workflow fails with exit 1.

- `scripts/context_guard.py`: every block is exit 0 with JSON (`decision: "block"` line 104, `permissionDecision: "deny"` lines 141-149). On an internal error it exits 0 silently (lines 179-183). That is fail-open by design, but silent.
- `scripts/frozen_tripwire.py`: same JSON pattern (lines 111-119, 139, 142-164). On an internal error it allows the edit and prints a one-line warning (lines 176-191).
- Cloud stop hook (`~/.claude/stop-hook-git-check.sh`, wired in `launcher-settings.json`): exits 2 with the reason on stderr for dirty, untracked and unpushed work. It belongs to the cloud harness, not this repo, and needs no change.

One fix: make the context guard's error path print a `systemMessage` the way the tripwire does, so a broken guard is seen. Lands in `scripts/context_guard.py` with a case in `tests/test_context_guard.py`.

## The gaps

### 1. Permission guardrails

**Now.** `workflow/dev-workflow.md` has no mention of deny rules, auto mode or the sandbox. Line 33 and README line 90 say the frozen tripwire doesn't cover shell commands or cloud sessions. README line 77 says the installer never touches settings.

**Change.** Keep the installer rule. Ship two templates and document them.

- `templates/user-settings.json` (new), merged by hand into `~/.claude/settings.json`:
  - `permissions.deny`: `Read` and `Edit` for `.env`, `.env.local`, `.env.*.local`, `.env.production`, `**/secrets/**`, `~/.ssh/**`, `~/.aws/**`. `.env.example` stays readable (ruling 9).
  - `sandbox`: `enabled: true`, `credentials.files` denying `~/.ssh` and `~/.aws`, `filesystem.denyRead` for the same `.env` files, `allowUnsandboxedCommands: true` to start (ruling 6).
  - `autoMode`: `environment` describing a single owner whose tickets land by fast-forward push to `main`; `allow` with `"$defaults"` plus that push; `hard_deny` with `"$defaults"` plus force-push, deleting a remote branch, deploying to production, `--no-verify`, reading `~/.ssh`, `~/.aws` or a denied `.env` file outside the sandbox, and editing `~/.claude/settings.json` or the hook scripts.
- `templates/project-settings.json` (new), copied to a project's `.claude/settings.json`: the same deny rules, because that file is the only one a cloud session reads. No `autoMode` block, since project scope is ignored.
- `README.md`: a "Guardrails" section after "Hooks" with the three layers in the order they are checked, and what each one doesn't cover.
- `workflow/dev-workflow.md` line 33: one sentence after the tripwire paragraph naming the three layers and pointing to the README. The rule stays "a denial means stop and ask". Line 74: an `/implement` run is expected to run in auto mode (ruling 2).
- `checks/26-settings-templates.sh` (new): both templates parse as JSON and carry the deny entries the README names.

**Probe, answered 2026-11-24.** The ERP repo's remote on the Mac is HTTPS (`https://github.com/...`), so pushes don't read `~/.ssh` and the deny costs nothing there. No `excludedCommands` entry for git is planned. One thing the answer doesn't cover: an HTTPS push takes its token from the macOS keychain, and whether the keychain helper works inside the sandbox is checked by the first item of the test below. If it fails, `git push` and `git fetch` go into `sandbox.excludedCommands`.

**Test.** In a fresh session with the template applied: `cat .env` is denied; a sandboxed `cat ~/.ssh/config` fails; `claude auto-mode config` prints the merged rules; a sandboxed `git fetch` and a normal push to `main` go through (the keychain check); in auto mode a `git push --force` is blocked; one light-path change lands end to end.

### 2. Hooks instead of instructions

**Now.** Lines 101-102 tell the builder to run the touched tests and a build, and the coordinator to run the full suite on the landing commit. Line 76 repeats the full suite at landing. Nothing enforces either. README lines 79-86 list the hooks that exist: all are context or frozen-core hooks.

**Change.** One new script, `scripts/suite_tripwire.py`, driven by a per-repo file `.claude/checks.json` with three optional commands: `lint`, `touched`, `full`. A repo without the file gets no behaviour, so the hook is safe at user level.

| Event | What runs | On failure |
|---|---|---|
| PostToolUse on `Edit\|Write\|MultiEdit` | `lint` on the edited file | exit 2: stderr goes to Claude (the edit already happened) |
| SubagentStop | `touched`, only when the subagent's checkout has changes against its base, so reviewers and Explore agents pass untouched | exit 2: the builder can't finish until it is green |
| Stop | `full`, only when `main` holds commits whose tree is not yet recorded green in `~/.claude/state` (ruling 7) | exit 2: the session can't end with an unproven landing |

Each blocking event gives up after two blocks for the same agent (it respects `stop_hook_active` and keeps a counter in `~/.claude/state`), then lets the stop through with a `systemMessage` naming the failure, so a test that can't pass doesn't loop forever. The coordinator counts that message as one failed build under the fallback rule (workflow line 97, ruling 8). The coordinator still runs the full suite on the landing commit: the hook backs the instruction, it doesn't replace it.

By CONTEXT.md this is a tripwire (local, bypassable). The mechanism is CI on `main` (gap 3). Add "suite tripwire" to CONTEXT.md through /domain-modeling.

Alternative that lost: a git `pre-push` hook running the full suite. It fires at the right moment, but `--no-verify` skips it, it doesn't exist in a fresh cloud clone, and README lines 139-140 already record that a local push hook was dropped in favour of a server-side control.

Files: `scripts/suite_tripwire.py`, `tests/test_suite_tripwire.py`, `tests/payloads/` (SubagentStop and Stop payloads), `checks/32-suite-tripwire.sh`, `install.sh` step 6 (copy the script), README "Hooks" (three new entries), `.claude/checks.json` for this repo (`full` is `./check.sh`), `templates/project-settings.json`, workflow lines 101-102 (one clause: the hooks enforce this where they are on).

**Probe.** Do hooks named in a repo's `.claude/settings.json` fire in a cloud session? If yes, the context guard, the frozen tripwire and the suite tripwire can all run in the cloud from scripts kept in the repo, and workflow lines 123 and 169 ("cloud sessions have no such hooks") change. If no, those lines stay.

How it runs: one commit on `claude/determined-wozniak-5pxpr5` adds `.claude/settings.json` and `.claude/hooks/probe.sh` (marked `# DISPOSABLE: cloud-hooks probe, until the answer is recorded`). The script appends the event name to a log file in the OS temp directory and is wired to SessionStart, UserPromptSubmit, PostToolUse on Bash, SubagentStop and Stop, called through `$CLAUDE_PROJECT_DIR`. A second cloud session starts on that branch with one prompt: run one shell command, start one Explore subagent, print the log file, change nothing. Its transcript shows which events fired. Then the commit is reverted and the second session archived. The answer, not the code, goes into this plan.

**Test.** `tests/test_suite_tripwire.py` drives the script with recorded payloads, the same way `tests/test_frozen_tripwire.py` does, and asserts stdout and exit code for: no config, green, red (exit 2), third block (exit 0 with message), unchanged tree (skipped). Then by hand in a scratch repo: break a test, watch a builder subagent get held at SubagentStop.

### 3. An independent check after landing

**Now.** This repo already has it: `.github/workflows/check.yml` runs `./check.sh` on every push, on Ubuntu and macOS. The workflow file doesn't ask for it anywhere. Line 76 and line 109 end the landing at "merge and push", and nobody reads the run.

**Change** (ruling 5).

- Workflow line 76: after the push, the landing commit's CI run is part of the ticket. Before the final report the coordinator reads the runs for its landing commits (`gh run list --commit <sha>`). A red run is a failed landing: fix forward as a new ticket, or revert, and say which in the report.
- Workflow step 0 of the main flow (line 37): once per repo, a CI workflow on push to `main` that runs the same command as `.claude/checks.json` `full`.
- `.github/workflows/check.yml`: add a job that runs when `check` fails on `main` and opens a `ready-for-agent` issue with the run link, skipping when one is already open. Needs `issues: write` on that job only.
- `templates/ci-check.yml` (new): the same workflow for project repos, Ubuntu only.
- README "Protecting main": one paragraph on the CI workflow, next to the ruleset.

**Test.** Push a deliberately failing check to a scratch branch with the job's branch filter pointed at it; confirm the issue opens once and a second failure doesn't open another. Remove the branch.

### 4. Human review by risk

**Now.** Line 107 says nothing in the loop waits on the user. Line 108 parks tickets that need a ruling. There is no review tier.

**Change** (ruling 3). Workflow lines 108-112: a ticket built by the high-risk builder that touches a frozen core, money, auth or the shape of stored data lands as normal, and the final report lists it under "Read before deploying" with its commit. Deployment sits in `autoMode.hard_deny` (gap 1), so the read happens before anything irreversible. No parking, no new stop.

**Test.** A routing eval case is not needed; the rule only changes the report. Check the next /implement run's final report by reading it.

### 5. CLAUDE.md audit

**Now.** Line 142 puts frozen cores, their mechanisms, sealed measures, disposable areas and named debt in the project CLAUDE.md `## Design` section. Line 143 puts the same cores and disposable areas in code markers. `skills/changeable-software/SKILL.md` "Where the answers live" says the same.

**Change.**

- Line 142: the `## Design` section holds, per frozen core, its enforcing mechanism and its sealed measures, plus named debt. Which files are frozen or disposable is read from the markers. This extends the existing override on vocabulary (line 140).
- `skills/changeable-software/SKILL.md` "Where the answers live" and the last "Structure" question in `references/review-checklist.md`: the same edit, as an owner's amendment with the date (ruling 10).
- Sami, once, in a fresh session: `/doctor prompt-audit` on `~/.claude/CLAUDE.md` and the workflow file, and apply her test to what it flags (keep only what Claude can't learn from the code).

**Test.** `checks/23-frozen-core-list.sh` still passes. The routing evals (below).

### 6. Cloud environment settings

**Now.** This repo's cloud environment ("dev-workflow") had unrestricted network access when the plan was written. It has no setup script, and one network secret, for `api.github.com`. README line 67 mentions only the stop hook.

**Change.**

- Done on 2026-11-23: the environment is on Limited network with package managers and MCP server hosts allowed and no extra hosts. Add a host only when a blocked request shows the need.
- README "Claude Code on the web": start every environment on Limited; put API keys in Network secrets, never in environment variables, which anything in the VM can read; a Claude API key can't be a network secret, so keep it out of cloud environments.
- Your other environments (Default, OVH, NameQ Cloud, Pixel, Hip Hop Architect) are yours to check in their settings against the same two rules.

**Test.** In a new session on the environment: `./check.sh` passes, a push works, and a request to an unlisted host is refused by the proxy.

### 7. "Where I needed you"

**Now.** Line 108 says the final report opens with pending rulings. Line 112 sets the ticket report. Line 147 names the context report as the upkeep measure.

**Change.** Line 108: the final report ends with "Where I needed you": every ruling asked for, every permission prompt or denial, every hook block that a person had to clear, and every stall, one line each. Line 147: read that section alongside the context report and hand off one item.

**Test.** Read the next run's report.

## What forces a regenerated cloud skill and the evals

| Change | `scripts/build_cloud_skill.sh` + commit `cloud/` and `template.sha` | Routing evals vs `evals/results/baseline.txt` | Re-sync account skills |
|---|---|---|---|
| Any edit to `workflow/dev-workflow.md` (gaps 1, 2, 3, 4, 5, 7) | yes | yes | dev-workflow |
| `skills/changeable-software/` (gap 5) | no | yes | changeable-software |
| README, templates, scripts, tests, checks, CI, `.claude/checks.json` | no | no | no |
| Cloud environment settings (gap 6) | no | no | no |

The evals cost model usage, so every workflow and skill edit lands in one batch (step 6 below) and the evals run once. The baseline is 5 green, 3 flaky, 2 red; a case that drops a colour is a regression to explain before pushing.

## Order, smallest safe change first

Scope is this repo only (ruling 1). Each step is its own commit on `main`, with `./check.sh` green before the push. Settings are edited only between sessions (workflow line 130).

1. Context guard error message (hook audit). One script, one test.
2. The README paragraph on cloud environments (gap 6). The environment itself is already on Limited.
3. Settings templates, README "Guardrails", check 26 (gap 1). You merge the user template into `~/.claude/settings.json` and test in a fresh session.
4. Suite tripwire: script, tests, check 32, installer, README, this repo's `.claude/checks.json` (gap 2). Run the cloud-hooks probe here.
5. CI red-`main` job and the project CI template (gap 3).
6. One batch of prose: workflow lines 33, 37, 74, 76, 97, 101-102, 108-112, 142, 147, and 123/169 if the probe says so; the changeable-software amendment; CONTEXT.md term. Then build the cloud skill, run the evals, re-sync both account skills (gaps 1, 2, 3, 4, 5, 7).
7. You run `/doctor prompt-audit` in a fresh session (gap 5).

The SSH probe is answered. Step 6 waits on the cloud-hooks probe. Nothing waits on a decision.

## Execution: through dev-workflow itself

The build runs through `workflow/dev-workflow.md` end to end, with no shortcuts because the repo is its own subject. Running the workflow on a change to the workflow is also the test of this plan: every place the run stalls, asks for you, or relies on a builder obeying its brief is a finding.

| Workflow step | For this change |
|---|---|
| Step 0, path check | Done in this plan: full path, complicated. The docs check above was the /research step. No file in this repo carries a `FROZEN CORE:` marker; the sealed measure is the routing evals (cases and pass rule, `evals/REGISTER.md`), which no ticket changes. |
| 1. /grill-with-docs (you) | Done 2026-11-24: ten rulings, above. The new term "suite tripwire" goes into CONTEXT.md through /domain-modeling, in the prose batch. |
| 2. /prototype detours | The SSH probe is answered (HTTPS remotes). The cloud-hooks probe is next, run as described under gap 2, code marked `# DISPOSABLE`, before /to-spec. |
| 3. Interfaces first | The one new interface is `.claude/checks.json` plus the suite tripwire's three events. Written before any ticket. DESIGN-IT-TWICE is skipped: no frozen core behind it and one caller. The tracer bullet is the Stop event running `./check.sh` in this repo. |
| 4. /to-spec, spec check, /to-tickets (you), wave plan | One ticket per step in "Order" above. README and the workflow file are shared areas, so the tickets that touch them take turns; the prose batch (step 6) is last because it depends on every other ticket. |
| 5. /implement (you, once) | Builders in worktrees, /tdd on the scripts and checks. The suite tripwire, the templates and the CI job get the high-risk builder: they are security controls. Prose and README get the low-risk builder. |
| 6. /code-review | With the changeable-software checklist and codebase-design as standards sources, per ticket, then land on `main` one at a time. |
| Upkeep | Cloud skill rebuilt and the routing evals run once, after the prose batch. Settings merged by you between sessions, never mid-session. |

The run's final report carries the first "Where I needed you" section (gap 7), before the rule is written into the workflow. It also lists every point where a builder skipped a check the suite tripwire would have caught, and anything the workflow had no step for. Those go back into this plan before the prose batch is written, so the workflow edit reflects what the run showed.

## Out of scope

The models table, the waves, the context budget, pull requests, and any edit to settings or CLAUDE.md in the planning session.
