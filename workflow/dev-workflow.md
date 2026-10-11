> Use when: any coding work in Claude Code. Load it into every session with an `@` import in `~/.claude/CLAUDE.md` (see the repo README).

# Dev workflow: Pocock skills + changeable-software

Two systems, one job each. The Pocock skills decide what happens next (the sequence). changeable-software decides what good looks like at each step (the standard). Neither replaces the other.

## Who can fire what

Only the user can run these; you cannot invoke them. When a step needs one, stop and name the exact command to type: /grill-with-docs, /grill-me, /handoff, /to-spec, /to-tickets, /implement, /triage, /wayfinder, /improve-codebase-architecture.

You may invoke these yourself when the step calls for them: changeable-software, /tdd, /code-review, /diagnosing-bugs, /codebase-design, /domain-modeling, /prototype, /research.

## Step 0: size and classify before anything else

On any coding request, run changeable-software's path check and Cynefin classification first. The answer picks the route:

- Light path (about one file, no new boundary, one-commit revert, no frozen core): skip the flow entirely. Make the change, run feedback, run the checklist's "Always" block. Nobody grills a typo.
- Chaotic (broken right now): /diagnosing-bugs. Stabilise, then understand.
- Clear: main flow, no prototype detour.
- Complicated (a knowledge gap): /research first, then main flow at /grill-with-docs.
- Complex (answer only visible by trying): main flow, and the prototype detour is mandatory before /to-spec.
- Too big and foggy to hold in one session: /wayfinder, which merges at /to-spec. Never for a well-scoped feature.
- Incoming bugs or requests the user didn't write: /triage, then /implement. Never triage tickets /to-tickets made.

Name any frozen core or sealed measure here. Either one forces the full path regardless of size.

## Main flow: idea to ship

0. Once per repo: /setup-matt-pocock-skills.
1. /grill-with-docs (no repo: /grill-me). changeable-software step 2 lands here: every concept gets exactly one name, recorded in CONTEXT.md through /domain-modeling.
2. Detour when a question needs running code: /handoff out, /prototype in a fresh session (mark it `# DISPOSABLE: <why>, <until>`), /handoff back.
3. Before splitting the work, changeable-software steps 3 and 4: write the interfaces first using /codebase-design vocabulary, say where the complexity went and who pays, and make the first ticket the thinnest end-to-end tracer bullet.
4. Multi-session build: /to-spec, /to-tickets, then the wave plan (see Waves), then /implement on that plan. Single session: /implement right here.
5. Inside /implement: name the feedback loop out loud (changeable-software step 5), then /tdd drives the slices. TDD is the tool, not a law. If a slice can't honestly be test-first, say so instead of faking it.
6. Before committing: /code-review, passing changeable-software's `references/review-checklist.md` to the Standards sub-agent as a standards source (local install: `~/.claude/skills/changeable-software/`; anywhere else: `find ~/.claude -path "*changeable-software/references/review-checklist.md"`). It lives outside the repo, so /code-review will not find it unprompted. Then answer: what did we improve before leaving?

Context hygiene: keep steps 1 to 4 in one window until /to-tickets is done. Nearing ~150k tokens before then, /compact at the nearest phase boundary.

A repo may carry its own ticket loop (for example `docs/agents/ticket-workflow.md`). It can reshape steps 4 to 6 for that repo (who builds, which models, extra checks such as screenshots). It never removes step 0, the ticket as the spec, /code-review with the changeable-software checklist, or the cloud rules. Where it contradicts those, this file wins and the conflict is noted in the ticket's report.

## Waves: tickets in parallel

Right after /to-tickets publishes and before /implement, write the wave plan without being asked. Skip it when there are fewer than three tickets or the edges form one straight chain, and say so in a line.

1. Layer by blocking edges. Wave 1 is every ticket with no blockers. Wave N is every ticket whose blockers all sit in earlier waves. A cycle means /to-tickets got an edge wrong: stop and show it to the user.
2. No edge doesn't mean safe in parallel. For each ticket, estimate the areas it will touch: modules, schema and migrations, shared types, config, route tables, lockfiles, CONTEXT.md. Two tickets in one wave that share an area can't build at once, so the later-numbered one drops to the next wave. Unsure counts as shared. Expand–contract migrate batches split by directory are built to run together and stay in one wave.
3. Show the plan as one table: wave, ticket, blocked by, areas touched, builder model (risk rule under "Building tickets"). Under it, name the critical path: the longest chain of blocking edges. That chain is the floor on build time however many builders run, so a long one is a reason to revisit the breakdown, not to add builders.
4. The user types /implement once against the plan. Before the first builder, check `.claude/worktrees/` is in `.gitignore`; if not, add it and commit that alone. Each ticket gets a fresh worktree subagent (Agent tool, `isolation: "worktree"`) running the loop in "Building tickets". That replaces /clear between tickets on every machine, not only in the cloud. At most three builders at once unless the user sets another number.
5. Dispatch by frontier, not by wave. A ticket starts the moment its own blockers have landed, without waiting for the rest of its wave. The waves are the plan the user reads; the frontier is what runs.
6. Builds run in parallel; landing doesn't. Land one ticket at a time in finish order: rebase onto main, full suite on the integrated result, merge. A conflict while landing means step 2 missed a shared area: fix it with /resolving-merge-conflicts and name the miss in that ticket's report.

## Building tickets: defaults for any repo

Learned building a production app. A repo's own loop can tighten these, not drop them.

- Models by risk: opus when the ticket touches stored data, parsing, imports, exports, time zones, money or auth; sonnet for narrow UI and copy. The same rule picks the reviewer's model.
- Mechanical checks are commands, not agents: the full test run, lint, screenshot or snapshot diffs. Spend a reviewer only on judgement.
- The builder runs only the touched tests plus a compile or build, so reviewers never see broken code. Review runs on the diff. The coordinator runs the full suite once, after review and the fix round, on the frozen commit that will land. Nobody runs it twice.
- Record the base commit before building. Before landing, fetch: if `main` moved, rebase and rerun the full suite on the integrated result. Never force-push over another session.
- If the repo has screenshot or snapshot tests, any visual change the ticket didn't ask for is a fail. Add a screens review (both themes, every language the app ships, right-to-left if it ships one) only when screens changed.
- Blocking findings and cheap, clearly worthwhile advisories go back to the same builder, which still has its context, in one round. Speculative polish is deferred in the report. Only what the fix touched is reviewed again. If a sonnet reviewer fails the same item twice, opus does the next fix and review.
- Heavy test runs that the machine can't run two of at once go through a lock, not discipline. The next ticket's builder may start while the current one is in review when the two share no files; it queues on the lock for tests.
- Nothing inside the loop waits on the user. Thresholds are set by rule or script, judgement calls are the coordinator's and are recorded. The user is needed only for grilling and for decisions that are genuinely his.
- One commit per ticket, its message naming each reviewer, its model and its verdict.
- Where the ticket leaves something open, follow the nearest precedent and record it as a Choice. Every Choice goes in the report; that is what makes building without check-ins allowed under changeable-software's unattended exception.
- Report each ticket in plain words: what it does on screen or in behaviour, not the diff. Close the ticket with the tests run, each reviewer's verdict, and the Choices.

## One home for each thing

- Vocabulary: CONTEXT.md. Do not copy it into CLAUDE.md. This overrides changeable-software's "Where the answers live" on vocabulary only.
- Hard-to-reverse decisions: docs/adr/.
- Frozen cores with their enforcing mechanism, sealed measures, disposable areas, named debt: the project CLAUDE.md `## Design` section, which points to CONTEXT.md for terms.
- Code markers: `# FROZEN CORE: <why>` and `# DISPOSABLE: <why>, <until>`.

## Upkeep

/improve-codebase-architecture, pick one candidate, take it into /grill-with-docs, design it on /codebase-design. A bug that comes back twice is an architecture question, not another patch; /diagnosing-bugs post-mortems feed the same route.

## Any time

/research, /prototype, /tdd, /code-review, /resolving-merge-conflicts, /wizard (steps only a human can do), /to-questionnaire, /wait-what, /teach, /writing-for-agents, /domain-modeling.

Past the commit, where the Pocock flow stops: shipping-and-launch, observability-and-instrumentation, security-and-hardening, deprecation-and-migration, ci-cd-and-automation, performance-optimization. Model-invoked; reach for them when the work is deploying, instrumenting, hardening or retiring something, not while building it.

## Cloud sessions

Applies when the session runs in a disposable cloud container (Claude Code on the web), where your local ~/.claude/CLAUDE.md is not loaded. Everything above still holds; this adds the rules the container forces.

- The container is deleted after inactivity, and anything not pushed goes with it. Run a stop hook that checks the main checkout after every reply and re-prompts while it holds uncommitted, untracked or unpushed work. Work so it stays quiet.
- Builders never work in the main checkout. Every /implement ticket, and any subagent that writes code, runs as a subagent with worktree isolation (Agent tool, `isolation: "worktree"`). One fresh subagent per ticket is the cloud form of "/clear between tickets".
- Before the first builder, check `.claude/worktrees/` is in the repo's `.gitignore`. If it isn't, add it and commit that alone, or the worktrees show up as untracked and trip the hook.
- The main checkout only ever receives a reviewed commit: builder finishes, /code-review passes, merge to main, push, all in the same reply. Never end a reply with the main checkout dirty.
- Stopping mid-ticket: commit the work to the ticket's branch and push it, or write a /handoff file, commit and push it. Nothing important lives only in the container.
- When the stop hook fires while a builder is still running in a worktree, something is wrong: the main checkout got touched. Find out what, don't just wait it out.
