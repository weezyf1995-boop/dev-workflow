# Handover: build the guardrails and verification plan

**Repo:** `weezyf1995-boop/dev-workflow`. Work on `main`, no pull requests.
**Plan:** `docs/plans/guardrails-and-verification.md`. Read it first; it holds the docs check, the hook audit, the seven gaps, the ten rulings and the order of work. This file doesn't repeat it.

## State

- Step 0 is done: full path, complicated. The docs check stood in for /research.
- The grill is done. Sami took all ten recommendations; they are the "Rulings" section of the plan and are not open for re-litigation.
- The SSH probe is answered: the Mac's remotes are HTTPS, so denying `~/.ssh` costs nothing. Whether the keychain helper works inside the sandbox is checked later, in gap 1's test.
- The cloud environment "dev-workflow" is already on Limited network access.
- Nothing is implemented. No workflow, hook, settings, skill or CI file has changed.

## Next step

1. Run the cloud-hooks probe, as written under gap 2 of the plan ("How it runs"). It was approved and not started. Use the new session's own working branch for the disposable commit, start one second cloud session on that branch, read its transcript, revert the commit without force-pushing, archive the second session.
2. Record the answer in the plan (gap 2's Probe paragraph, and whether workflow lines 123 and 169 change), commit and push to `main`.
3. Stop and name `/to-spec` for Sami. After it: the spec check, `/to-tickets`, the wave plan, then `/implement`, following the plan's "Execution" table.

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
