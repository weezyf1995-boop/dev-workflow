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
- Nothing is implemented. No workflow, hook, settings, skill or CI file has changed.

## Next step

The wave plan, then `/implement`. The frontier is #25, #26, #27, #28 and #29. #26, #27, #28 and #29 all edit the README, so they take turns, and #25 can run beside any of them.

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
