# Run report: /implement on spec #24 (tickets #25 to #31)

Run of 2026-11-24, cloud session on the "dev-workflow" environment. Seven tickets landed on `main`. The run stops at #32, which is Sami's. #33 must fold the findings below into the plan before writing the prose batch.

## Pending: yours

1. **#32, hand tests.** Merge the user template between sessions, then run the checks in #32. That now includes logging one real subagent-report UserPromptSubmit payload in a cloud session (added after #31). #33 waits on it.
2. **Delete the remote branch `scratch/red-main-test`.** #29's hand test created it. The session's proxy refused the delete (403), so it was left alone, not worked around.

## Coordinator's rulings (reversible, recorded in the commits)

- **#28:** the suite tripwire acts only when the payload `cwd` is inside `$CLAUDE_PROJECT_DIR`, when that is set. This means a session that has `cd`'d into an untrusted clone doesn't run that clone's `.claude/checks.json`. The reviewers split on whether the trust risk needed this. It was cheap, so it went in.
- **#30:** only a linked worktree counts as a builder's checkout for SubagentStop. Reviewers, Explore agents and the extra post-Stop event run in the main checkout and pass untouched.
  - **Gap.** If a coordinator session itself runs in a linked worktree (as Claude desktop worktree sessions can), the blocking case comes back.

## Read before deploying

All seven landed as normal. These five are security controls built by the high-risk builder:

| Ticket | Commit | What to read |
|---|---|---|
| #27 | 370c78a | Settings templates (deny rules, sandbox, auto mode) and check 26 |
| #28 | cda00dd | Suite tripwire, Stop event |
| #29 | a48d527 | CI job with `issues: write` on red `main`, plus the CI template |
| #30 | c5f8d3e | Suite tripwire, SubagentStop and PostToolUse |
| #31 | 4dde88e | Project template hook wiring; the context guard's subagent-report pass-through past 400k |

No ticket touches money, stored data or a frozen core.

## Tickets

| Ticket | Builder | Reviews | Fix rounds | Landing commit | CI |
|---|---|---|---|---|---|
| #25 Context guard reports its own failures | sonnet | Standards pass, Spec pass (advisories) | 0 | da5f751 | green |
| #26 README cloud rules | sonnet | Standards pass, Spec pass (advisories) | 0 | 13a14e1 | green |
| #27 Settings templates, README Guardrails | opus | both pass (advisories) | 1, prose only | 370c78a | green |
| #28 Suite tripwire: Stop | opus | Spec **fail** (give-up was per turn, not per session) | 1, re-reviewed: pass | cda00dd | green |
| #29 Red `main` issue, CI template | opus | both pass (advisories) | 0 | a48d527 | green |
| #30 Suite tripwire: SubagentStop, PostToolUse | opus | Spec **fail** (read-only agents blocked when the coordinator's checkout was dirty or on a session branch) | 1, re-reviewed: pass | c5f8d3e | green |
| #31 Cloud hook wiring | opus | both pass (advisories) | 1 | 4dde88e | see the commit's run |

- `./check.sh` ran on every landing commit, and all were green: 12 checks to start, 14 by the end.
- No fallback model was used.
- No ticket parked.

## Where I needed you

- **/to-spec:** confirming the four test seams. The skill requires it.
- **/to-tickets:** approving the breakdown. The skill requires it.
- **#29:** deleting `scratch/red-main-test`, refused by the proxy (above).
- **No permission prompts, denials or hook blocks** came up during the run.

## Findings for the plan (fold in before the prose batch)

**Skipped checks:**
- The spec check before `/to-tickets` never ran.
- #30's lint code was written before its tests. The builder then proved the tests by breaking the code.
- The test payloads for #30 and #31 are synthesized from documented shapes, not captured. #32 now checks the one the context guard depends on.

**Doc facts the builders corrected:**
- The layer order is deny rules, then the auto mode classifier, then the sandbox.
- In user scope, a bare `denyRead` path resolves under `~/.claude`, so the templates use `~/**/.env` (user) and `./**/.env` (project).
- `claude auto-mode critique` exists; the plan's "Not found, so dropped" is wrong.
- The hooks docs show no payload field that marks a subagent's report.

**Steps the workflow had no step for:**
- Hand tests that push a scratch branch and open real issues (#29). Deleting the branch afterwards needs rights the cloud proxy doesn't give.
- Landing by cherry-pick from a worktree branch and amending the message to name the reviewers. The workflow says "rebase onto main, merge".
- A small fix round that changes a line or two of logic. The workflow's "no new logic: coordinator re-reads the diff" was stretched to cover #31's one-line rule change.

**Area rule:**
- Four builders edited different README sections at once, at Sami's request, and every landing applied cleanly. Separate sections of one file could count as separate areas in step 2 of the wave plan.

**Spec gaps that reviews caught:**
- #28: "two blocks per session" didn't say what a session is across turns.
- #30: the ticket assumed read-only agents leave no changes, but they run in the coordinator's checkout.

## Debt (advisories not fixed, one line each)

- **#25:** wrong-typed fields in a valid payload now print the failure message, where they used to stay silent. The message repeats the tripwire's wording.
- **#26:** the README doesn't say why a Claude API key can't be a network secret.
- **#27:**
  - the check helper lives in `scripts/`;
  - the credentials walk is duplicated;
  - check 26 sits in the document band but runs tests;
  - the `autoMode.allow` entry for the push may be redundant;
  - "Guardrails" isn't a CONTEXT.md term;
  - nothing pins the seven paths if the README and the templates drop one together;
  - `denyRead` is matched by suffix.
- **#28:**
  - the trust check runs after one git call (fixed in #30);
  - the blocks file holds one key per session;
  - `realpath` doesn't fold case on macOS;
  - the hook skips silently when the checkout isn't at `main`'s tree;
  - a dirty tree gets recorded as green;
  - block files grow;
  - the timeout path is untested.
- **#29:**
  - the issue job is duplicated between `check.yml` and the template, with nothing keeping them in step;
  - `--limit 500`;
  - a macOS-only failure isn't named in the issue;
  - the skip matches by title, not label;
  - a non-object `checks.json` fails with a traceback.
- **#30:**
  - the `guarded()` parameter clump;
  - the redundant `top_level` gate in `post_tool_use`;
  - two tests return at the worktree gate under an old class docstring;
  - the coordinator-in-a-worktree case (above).
- **#31:**
  - check 26's hook list is a second copy of README "Hooks";
  - timeouts are unchecked;
  - each project's copies of the hook scripts can go stale.

## #33, the prose batch (run of 2026-11-24, second cloud session)

One ticket, one builder in a worktree (low-risk builder), two reviewers, one fix round, landed on `main`.

**Choices.**
- The guardrail-layers sentence is its own short paragraph after the frozen tripwire paragraph, and says that a cloud session has the deny rules only.
- "Read before deploying" covers any ticket that touches a frozen core, money, auth or the shape of stored data, whichever builder built it.
- The changeable-software amendment edits the original sentence in place. The skill still puts vocabulary in `CLAUDE.md`; the workflow's override on vocabulary stays the only override (ruling 10).
- Findings about the Waves section are in the plan only ("Findings with no home in this batch").

**Reviews.** Standards: fail, two blocking (the skill's amendment contradicted the sentence above it; the layers sentence was unconditional though a cloud session has no classifier and no sandbox). Spec: fail, two blocking ("the sandbox applies in every mode" was false; two plan lines overstated what #32 and the run report recorded). All fixed in one round, re-read by the coordinator: prose only.

**Routing evals.** Against the baseline (5 green, 3 flaky, 2 red): 6 green, 3 flaky, 1 red, in `evals/results/latest.txt`.
- Up: complicated and spec-check, flaky to green. recurring-flake, red to flaky.
- Same: chaotic red, migration-four-lines flaky (1/3, was 2/3).
- Down: frozen-four-lines, green to flaky (2/3). The failing run made no edit, named the frozen core and asked for a ruling, but never wrote the words "full path". The routing was right and the marker was missed. The new sentences beside the frozen tripwire paragraph end on "stop and ask", which may pull a reply towards "your ruling" and away from "full path". One run can't tell that from noise.
- The cases and the pass rule are unchanged.
- How it ran: in the cloud container, with `CLAUDE_CONFIG_DIR` pointing at a folder holding the edited workflow, the edited skill and the plugin's skills, since `install.sh` can't run here. No hooks were on.

**Read before deploying.** Nothing. The ticket is prose and touches no frozen core, money, auth or stored data.

**Where I needed you.**
- No rulings, permission prompts, denials or hook blocks.
- Stall: the evals ran twice. The first run used the container's default model, not the baseline's, because the runner passes no model unless told to. Its result (7 green, 1 flaky, 2 red) is not the recorded one. The rerun passed `--model` with the coordinator row's value.
- Stall: Claude Code doesn't load a `CLAUDE.md` kept in a session scratchpad, so the eval config folder had to live outside it.
- The session's harness names a session branch and asks for a pull request. This repo's `CLAUDE.md` says push to `main` with no pull request, and that was followed.

**Pending: yours.**
1. Re-sync the two account skills: upload `cloud/dev-workflow` and `skills/changeable-software` to your account's skills again (or run your sync job). A session can't do it. Until then cloud sessions report the cloud skill as behind `template.sha`.
2. #34, `/doctor prompt-audit`, in a fresh local session.
3. Two follow-ups from #32 that this batch recorded but did not make: allow `github.com` in the user template's sandbox network settings, and say in README "Guardrails" that the sandbox block does nothing in a cloud session. Neither has a ticket yet.

**Since then (2026-11-25).** All three are done. The account skills were re-synced and now carry template `a55081d2e19d`. #34 ran and is closed, with each finding ruled on in the issue. The two #32 follow-ups landed in `1fa3d09`.
