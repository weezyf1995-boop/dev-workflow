# Wave plan: spec 2 (machinery), issue #16

Written 2026-11-20. Disposable with the rest of `handoff/`.
Base: `spec-2-machinery` at the commit that adds this file. Every ticket lands on `spec-2-machinery` (rebase, `./check.sh`, merge, push that branch); nothing goes to `main`, no pull requests.

| Wave | Ticket | Blocked by | Areas touched | Builder |
|---|---|---|---|---|
| 1 | #17 Bytecode hygiene | none | `.gitignore`, tracked `.pyc` files, new check in `checks/` | sonnet, medium |
| 1 | #18 Worktree base | none | workflow "Building tickets", cloud copy, README | sonnet, medium |
| 2 | #19 Routing evals | #17 | new evals area, new check, workflow Upkeep, cloud copy, README | opus, medium |
| 3 | #20 Frozen tripwire | #17, #19 | new script, context guard + tests, installer + test, new check, workflow, cloud copy, README | opus, medium |
| 4 | #21 Model table and its check | #18, #19, #20 | workflow, guide, README, cloud copy, new check | sonnet, medium |
| 5 | #22 README sections | #19, #20, #21 | README | sonnet, medium |
| 6 | #23 GitHub ruleset | #17 to #22 | repository settings (GitHub API), README | opus, medium |

Critical path: #17 → #19 → #20 → #21 → #22 → #23, six tickets long. Only #18 runs beside it. More builders would not shorten it.

Area note: #18 and #19 share the workflow, the cloud copy and the README. #19's only blocker is #17, so by the frontier rule it waits for #18 to land as well before it starts.

Risk rule applied: #19 parses CLI JSON and judges replies; #20 parses hook payloads, resolves file identity and stores a timed override; #23 changes repository settings through an external API. The rest are prose and simple checks.

## Rules that hold for every ticket

- **Vocabulary (CONTEXT.md):** declaration, tripwire, mechanism, frozen core. The new hook is the frozen tripwire, never a guard or a gate. The context guard keeps its name. "Sealed measure" is the skill's term.
- **The spec governs:** issue #16 holds every decision. Tickets implement its shapes and do not redesign them: the ten sealed eval cases and pass rule, the tripwire's marker, discovery, identity matching, the override's syntax, scope and 8-hour expiry, and its ruled behaviour (handled by the hook without reaching the model; let through the context guard's 400k stop).
- **Frozen cores no ticket moves:** the frozen-core list in `skills/changeable-software/SKILL.md` step 1 and its frontmatter `description`.
- **What no ticket touches:** `main`; anyone's settings file (the installer stays out of settings); the two spec 1 debt items; any repository other than this one.
- **Each workflow edit regenerates the cloud copy** with the existing build script, in the same commit.
- **New checks** take number prefixes from the bands at the top of `check.sh`; Python checks must not write bytecode into the repository.
- **Brief rules:** each builder confirms its worktree contains the base commit named in its brief before doing anything else, and stops and reports if it does not.
- A ticket that finds itself breaking one of these rules has left the spec: it stops and says so.

## Progress

- 2026-11-20, wave 1 landed: #17 as `c29a646`, #18 as `8f2f905`. Both reviews passed on each; advisories applied by the coordinator.
- 2026-11-20, wave 2 landed: #19 as `1a5608e` (cases sealed) … `01dca89` (review fixes); four commits kept so the seal-before-baseline order stays visible. Both reviews (opus) passed. Baseline: 5 green, 3 flaky (migration-four-lines, complicated, spec-check), 2 red (chaotic, recurring-flake). Debt: an amend or reset that leaves files untouched is not seen as an edit.
- 2026-11-20, wave 3 landed: #20 as `3e4a06a`. Both reviews (opus) passed; one fix round for four advisories. Debt: override paths containing spaces cannot be named; the case-insensitive test has only skipped (case-sensitive VPS), never run on macOS.
- 2026-11-20, wave 4 landed: #21 as `169ccee`. Both reviews (sonnet) passed; three wording advisories applied by the coordinator. Choice: the Spec reviewer row names opus for its risky case. Debt: the Spec reviewer's risk list repeats the builder risk rule with small differences.
- 2026-11-20, wave 5 landed: #22 as `1def935`. Both reviews (sonnet) passed; one wording advisory applied by the coordinator. Debt: the push-hook entry in "Deliberately not built" names the GitHub ruleset, which only exists once #23 lands; only the router entry carries a reopen condition (as the spec gives it).
- Next: wave 6, #23 GitHub ruleset (opus, medium). It changes repository settings through the GitHub API: Sami says yes before it runs. Base for its brief: the tip of `spec-2-machinery` after this note.
- Local note: `worktree.baseRef` is not set on this VPS, so the Agent tool's isolation would branch from `main`. Wave 1 used worktrees made by hand at the base commit. Reviewers must be told not to check out branches in the main checkout (one did, in wave 1).
