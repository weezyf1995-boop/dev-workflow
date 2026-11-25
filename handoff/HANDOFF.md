# Handoff: dev-workflow, spec 2 (machinery)

Written 2026-11-20 from a cloud session, for a local Claude Code session to continue.
This folder is disposable. Delete `handoff/` in the last commit before `spec-2-machinery` is merged.

## Where things stand

- **Spec 1 (doctrine) is finished and on `main`.** Issue #10 and its tickets #11 to #15 are closed. `main` is at `593b714`. Eight checks pass and CI is green.
- **Spec 2 (machinery) is published and checked, not yet ticketed.** It is issue #16. Read it in full before anything else: `gh issue view 16`. It holds every decision; this file does not repeat them.
- **Branch.** All spec 2 work goes on `spec-2-machinery` (branched from `593b714`). Sami's instruction: commit and push to this branch, nothing to `main`, until spec 2 is ticketed and built; he decides about merging afterwards. This overrides the workflow's "merge to main" rule and his standing "push to the default branch" preference for this build.

## Next step

1. **Get one ruling from Sami** (asked, not yet answered). How a `frozen override` prompt behaves:
   - the hook handles it completely and it never reaches the model; and
   - the context guard lets it through the 400k stop (a new branch beside `relay` and `override`, plus one test).
   Both are written into issue #16 as "pending the owner's ruling" with yes as the recommendation. If he says yes, remove the "pending" wording from the issue. If he rules otherwise, edit those two bullets, the matching test bullets and the Further Notes line.
2. **He runs `/to-tickets`** against issue #16. Proposed breakdown, in the spec's landing order:
   1. Bytecode hygiene
   2. Worktree base
   3. Routing evals
   4. Frozen tripwire (includes the context guard branch and the installer changes)
   5. Model table and its check
   6. README sections (ownership, prerequisites, "Deliberately not built")
   7. GitHub ruleset (last; tell Sami and wait for a yes before running it)
3. **Write the wave plan unasked.** Expect it to be close to serial: tickets 2, 3 (its Upkeep line), 4 and 5 all edit `workflow/dev-workflow.md` and regenerate the cloud copy, and 3, 4, 5 and 6 all edit `README.md`. Ticket 1 is free of both.
4. **He runs `/implement`.** Each ticket lands by rebasing onto `spec-2-machinery`, running `./check.sh` on the integrated result, merging into that branch and pushing that branch. Issues stay open until the branch reaches `main`, so comment on each ticket when it lands.

## Decisions made in the grill (already in issue #16; listed so nothing is re-litigated)

- No router split, no review-trailer gate, no Bash layer on the tripwire, no local push hook. Each goes in the README's "Deliberately not built" list with its reason; the router entry carries a reopen condition.
- The frozen tripwire covers the edit tools only. The override names its paths, works across worktrees, lasts 8 hours and ends on `clear`. It warns visibly when it fails.
- Evals: ten sealed cases, three runs each, run by hand, baseline measured before the tripwire hook lines are added to settings.
- Worktree base: a documented setting plus a base-commit check in every builder brief.
- GitHub ruleset on this repo only; other repos are a separate one-off when Sami asks.
- Vocabulary is in `CONTEXT.md`: declaration, tripwire, mechanism, frozen core. Do not call the new hook a guard or a gate.

## Things learned in the cloud session that may not hold locally

- **Worktree isolation was refused** by the cloud harness (`Agent` with `isolation`). Builders ran in git worktrees created by hand under `.claude/worktrees/`, each confined to its own. Locally the Agent tool's isolation should work; still put the base commit in every brief and have the builder verify it first.
- **Isolated worktrees branch from the default branch**, not the current commit, unless `worktree.baseRef` is `head` (Claude Code docs, "Run parallel sessions with worktrees"). On this build the base must be the tip of `spec-2-machinery`, not `main`, so this matters from the first ticket.
- **`gh` GraphQL was unavailable** in the cloud; issues were created and edited through `gh api repos/weezyf1995-boop/dev-workflow/...`. Locally the plain `gh issue` commands should work.
- **A push to `main` was refused** by the session's safety classifier until Sami said to push. Not relevant while work stays on the branch.
- **The `claude` CLI exists in the cloud container.** Whether it runs headless there was not tested. Locally it will, so the evals baseline can be run on Sami's machine as part of the evals ticket. Run it before adding the tripwire's hook lines to settings.

## Reference material in this folder

- `reference_frozen_guard_v2.py`: a reviewer-proposed tripwire, rebuilt and run. It passes every probe except two: its override does not reach worktrees (it keys on the checkout's top level and compares real paths), and it misses untracked marked files. The spec fixes both. Use it as a starting point, not as the answer; write the tests first.
- `reference_probes.py`: the adversarial probes that were run. The frozen-tripwire section is the prior art for the ticket's tests. The push-hook section is for a hook that was dropped.
- `brief-standards-review.md`, `brief-spec-review.md`, `smell-baseline.md`: the reviewer briefs used on spec 1. Their paths point at the cloud container (`/tmp/tk/...` and the synced skill folders); swap in local paths (`~/.claude/skills/changeable-software/references/review-checklist.md`, and the `codebase-design` skill).

## How builders were briefed on spec 1 (worked well; reuse)

1. First run `git rev-parse HEAD` and `git log --oneline -3`. The base must contain the commit named in the brief. If not, stop and report.
2. Make the change. Run the checks the change touches, then `./check.sh` once.
3. Commit everything as one commit on the worktree's branch. Do not push, merge or open a pull request; the coordinator lands it.
4. Report only what the coordinator acts on: Choices and any pending ruling first, then the tests run with pass or fail, the branch and the commit. A reviewer's report is its verdict and findings.

Reviews: one Standards and one Spec reviewer per ticket, reading the diff only, verdict on the last line. One fix round back to the same builder for a blocking finding. Each commit message names each reviewer, model and verdict.

## Debt and follow-ups outside spec 2

- **Debt from spec 1** (recorded in the commits, out of scope for spec 2):
  - the staleness guard in `checks/23-frozen-core-list.sh` searches all of `SKILL.md`, so removing "an agent's execution path" from step 1 alone would not trip it;
  - in the checklist's Changeability item, the new sentence sits before "What does this make that cost?" and blurs what "that" refers to.
- **Installed copies are stale.** The skill and the workflow on the Mac, the VPS and the account-level copies do not have spec 1 yet. Re-run the installer and the sync.
- **Undecided:** a written rule for sessions that refuse worktree isolation.
- **Not done in the cloud session:** the files in `/Users/sami/Claude/ABOUT ME/` could not be read because the Mac was not connected. Read them at the start of the local session, as Sami's preferences ask.
