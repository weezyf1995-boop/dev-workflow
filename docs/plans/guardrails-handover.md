# Handover: build the guardrails and verification plan

**Repo:** `weezyf1995-boop/dev-workflow`. Work on `main`, no pull requests.
**Plan:** `docs/plans/guardrails-and-verification.md`. Read it first; it holds the docs check, the hook audit, the seven gaps, the ten rulings and the order of work. This file doesn't repeat it.

## State

- Step 0 is done: full path, complicated. The docs check stood in for /research.
- The grill is done. Sami took all ten recommendations; they are the "Rulings" section of the plan and are not open for re-litigation.
- The SSH probe is answered: the Mac's remotes are HTTPS, so denying `~/.ssh` costs nothing. Whether the keychain helper works inside the sandbox is checked later, in gap 1's test.
- The cloud environment "dev-workflow" is already on Limited network access.
- The cloud-hooks probe is answered: yes. Repo hooks fire in cloud sessions for all five events tested. The detail and what follows from it are under gap 2 of the plan. The probe commit is reverted and never reached `main`.
- `/to-spec` is done: the spec is issue #24 (`ready-for-agent`), written from the plan. Sami confirmed the four test seams: the hook-script process boundary, `./check.sh` check files, hand tests, and one routing eval run after the prose batch.
- `/to-tickets` is done: ten tickets, #25 to #34, sub-issues of #24 with GitHub's native blocked-by links. #32 (hand tests) and #34 (`/doctor prompt-audit`) are Sami's (`ready-for-human`, a label created for this). The plan's step 4 is split three ways: tracer bullet #28 (Stop), #30 (SubagentStop and PostToolUse), #31 (cloud wiring). Step 3's hand test is #32.
- Skipped: the spec check before `/to-tickets` never ran. It goes into the final report.
- The wave plan is `docs/plans/guardrails-waves.md`.
- `/implement` ran on 2026-11-24. #25 to #31 are landed and closed; the run report is `docs/plans/guardrails-run-report.md`. Nothing in `workflow/`, `skills/`, `CONTEXT.md` or `cloud/` has changed yet.
- #32 (hand tests) is closed. Its three comments hold every result: the cloud checks, the local checks, and the two follow-ups. All pass except one: a real subagent report does not reach the context guard as a `<task-notification>` block. That fix is #36 (`ready-for-agent`, sub-issue of #24, not blocking #33).
- Both scratch branches are deleted and the hand-test scripts are removed from the repo.
- The light-path hand test landed `0109dd0` (README: why a Claude API key can't be a network secret), which clears that debt line from the run report.

## Findings from #32 for #33 to fold into the plan

The detail is on #32. In short:

- **Gap 2, context guard:** the report arrives as `<agent-message from="…">` opening with `[Subagent hand-back]`. A `queued-remote-notifications` `<task-notification>` does fire UserPromptSubmit and passes the guard today. The subagent's own completion notice doesn't fire the hook. Only the cloud shape was tested. Ticketed as #36.
- **Gap 2, pass-through:** the suite tripwire's give-up `systemMessage` for a subagent isn't in a headless `stream-json` transcript. The state file in `~/.claude/state` is the only record, so a headless coordinator can't count it as a failed build.
- **Gap 2, builders:** in `acceptEdits` mode every git command a worktree builder ran needed approval. Not checked in auto mode.
- **Gap 1, sandbox network:** `github.com` isn't on the sandbox allowlist. `git fetch` and `git push` each failed once with a 403 and worked when Claude allowed the host for that command. No keychain problem, so nothing goes into `excludedCommands`. The user template should allow `github.com`.
- **Gap 1, cloud:** a cloud session started with the sandbox off although the project template turns it on. The template's sandbox block does nothing there.
- **Gap 1, user settings:** Sami's user settings carry Alethia-specific `autoMode` entries (`environment` and two `soft_deny` rules) that apply in every repo. They belong in Alethia's project settings.
- **Where I needed you:** the hand tests could not be done as written. The wizard's "Expected / Result" wording read as "type the expected value", the Mac's folders weren't reachable from a cloud session, and the checks ended up run headless by a script with Claude judging the output. Deleting a remote branch was refused twice: by the cloud proxy during the run, and by the auto mode classifier in the session that did #32.

## Next step

#33 is being built in another session (started 2026-11-24). Once it lands, #36 runs alone: its wave plan is the "Second run" section of `docs/plans/guardrails-waves.md`, and the local payload it needed is logged on the ticket. Then Sami's #34.

## Rules that hold

- The build runs through `workflow/dev-workflow.md` itself. Every stall, every time Sami is needed, and every check a builder skipped is a finding for the final report's "Where I needed you" section.
- Scope is this repo only. Project repos adopt the templates later.
- No edits to settings or CLAUDE.md mid-session. Settings templates are merged by Sami between sessions.
- All workflow and skill prose lands in one batch at the end, followed by `scripts/build_cloud_skill.sh` and one run of the routing evals against `evals/results/baseline.txt`.
- `./check.sh` green before every push.
- Out of scope: the models table, the waves, the context budget.

## Not available in a cloud session

- Sami's `ABOUT ME` files and the `OUTPUTS` and `TEMPLATES` folders on his Mac. Deliverables go in the repo.
- `/auto-mode-setup`, and anything that needs his local `~/.claude/settings.json`.
- The plugin has no skill named `grill-with-docs` here; `mattpocock-skills:grilling` is the one that ran.

## Suggested skills

`anthropic-skills:dev-workflow`, `anthropic-skills:changeable-software`, `mattpocock-skills:prototype` (the probe), `mattpocock-skills:tdd`, `anthropic-skills:security-and-hardening` (gap 1), `anthropic-skills:ci-cd-and-automation` (gap 3), `mattpocock-skills:domain-modeling` (the "suite tripwire" term).
