> Use when: any coding work in Claude Code. Load it into every session with an `@` import in `~/.claude/CLAUDE.md` (see the repo README).

# Dev workflow: Pocock skills + changeable-software

Two systems, one job each. The Pocock skills decide what happens next (the sequence). changeable-software decides what good looks like at each step (the standard). Neither replaces the other.

## Who can fire what

Only the user can run these; you cannot invoke them. When a step needs one, stop and name the exact command to type: /grill-with-docs, /grill-me, /handoff, /to-spec, /to-tickets, /implement, /triage, /wayfinder, /improve-codebase-architecture.

You may invoke these yourself when the step calls for them: changeable-software, /tdd, /code-review, /diagnosing-bugs, /codebase-design, /domain-modeling, /prototype, /research.

The relay: where a step below says relay, Claude writes the handoff file itself, in the /handoff skill's format (state, next step, suggested skills, references by path, never copies of specs or diffs), to the OS temp directory, then runs `~/.claude/scripts/relay.sh <absolute folder> "<prompt>"` and stops. On macOS that opens a new Code session in the Claude desktop app with the prompt typed in; you confirm the folder and press Enter, because a deep link never sends on its own. Anywhere else relay.sh prints the prompt to paste. Relaying is never a way into a step that is yours to decide: grilling and architecture review still wait for you.

In a cloud session relay.sh can't open anything, so the relay is a one-off scheduled task instead: create it (the create_trigger tool, run_once_at about two minutes ahead, push notification on) with the handoff text itself as its prompt, in the same format, naming the plan, the rules block and the base commit by path. The task starts a fresh session with this session's repos already attached and the prompt already sent, so nobody presses anything. Say so in one line and stop. Never delete that scheduled task afterwards: deleting it deletes the session it started.

Between your commands the housekeeping is Claude's: fresh sessions by relay, a fresh subagent per ticket, keeping the window small. Claude never asks you to /compact or /clear; both stay yours to type whenever you like. Your part of a build is the commands above and the pending rulings in the final report.

## Step 0: size and classify before anything else

On any coding request, run changeable-software's path check and Cynefin classification first. The answer picks the route:

- Light path (about one file, no new boundary, one-commit revert), unless a hard disqualifier applies. changeable-software says: "If the change touches a frozen core (one list, defined in step 1) or an external boundary — an external API, or data you cannot regenerate — take the full path even if it is four lines. Size is not the risk; blast radius is." Otherwise skip the flow entirely. Make the change, run feedback, run the checklist's "Always" block. Nobody grills a typo. The step 1 in that quote is changeable-software's, and its frozen-core list includes money movement and authentication. A change to the shape of persisted state (a migration, a stored file format, a queue payload, a wire schema) also forces the full path, because reverting the commit does not revert the data already written; a cache that can be rebuilt from source does not count.
- Chaotic (broken right now): /diagnosing-bugs. Stabilise, then understand.
- A bug or flake that has come back twice or more: an architecture question, not another patch. Diagnose it with /diagnosing-bugs, then take the structure that keeps producing it to /improve-codebase-architecture.
- Clear: main flow, no prototype detour.
- Complicated (a knowledge gap): /research first, then main flow at /grill-with-docs.
- Complex (answer only visible by trying): main flow, and the prototype detour is mandatory before /to-spec.
- Too big and foggy to hold in one session: /wayfinder, which merges at /to-spec. Never for a well-scoped feature.
- Incoming bugs or requests the user didn't write: /triage, then /implement. Never triage tickets /to-tickets made.

Name the route in the reply's first sentence (the skill, or light or full path), even when you stop before starting it because something is missing, and even when you have already invoked the skill and are replying in its terms. The user should see which rule fired.

Name any frozen core or sealed measure here. Either one forces the full path regardless of size.

The frozen tripwire backs that rule where its hook is on (README, Hooks): it denies Edit, Write, MultiEdit and NotebookEdit, for the main session and subagents, on any file in the repository carrying a `FROZEN CORE:` marker line, whether reached by symlink, hard link or relative path, or by other casing where the filesystem is case-insensitive. A denial means stop and ask for the user's ruling; Claude never works round it. Once the user has ruled, they type `frozen override <path> [<path>...]` (repository-relative) to open those files for 8 hours across every worktree, and `frozen override clear` ends it. It is a tripwire, not a mechanism: shell commands are not covered, and cloud sessions are covered only when the repo's `.claude/settings.json` names the hook and the script is in the repo, so each frozen core still needs its own mechanism (a purity test, a fingerprinted config, a separate process) running in the project's suite.

An action meets three guardrail layers, in this order: deny rules, the auto mode classifier, then the sandbox (README, Guardrails). In a cloud session only the deny rules apply. A denial from any of them still means stop and ask; Claude never works round it.

## Main flow: idea to ship

0. Once per repo: /setup-matt-pocock-skills, and a CI workflow on push to `main` that runs the same command as `.claude/checks.json` `full` (the template is `templates/ci-check.yml`).
1. /grill-with-docs (no repo: /grill-me). changeable-software step 2 lands here: every concept gets exactly one name, recorded in CONTEXT.md through /domain-modeling.
2. Detour when a question needs running code: Claude runs /prototype in a worktree subagent (Agent tool, `isolation: "worktree"`), briefed with the question and the files it needs, never the conversation. The code is marked `# DISPOSABLE: <why>, <until>`. The subagent reports only the answer, briefly, and the answer, not the code, comes back into the grilling. Keep the branch only if the answer points at it.
3. Before splitting the work, changeable-software steps 3 and 4: write the interfaces first using /codebase-design vocabulary, say where the complexity went and who pays, and make the first ticket the thinnest end-to-end tracer bullet. On the full path, when a new or changed interface sits in front of a frozen core or will have two or more callers, run codebase-design's DESIGN-IT-TWICE (parallel sub-agents, radically different interfaces, compared on depth, locality and seam placement) before settling the shape. Skip it otherwise: it costs several agents.
4. Multi-session build: /to-spec, the spec check (see Spec check) and Show-me (see Show-me), /to-tickets, then the wave plan (see Waves), then /implement on that plan. Single session: /implement right here.
   Model by phase: the session runs as the coordinator (see "Models" under "Building tickets") from step 1 to the end of the build; new Code sessions start there when ~/.claude/settings.json sets the coordinator row's settings value as the default model, with its effort. Planning, the wave plan, the coordinating session, /tdd and /code-review all run in it, so there is no model switch and no relay between planning and building. /implement follows in the same window unless it is past ~200k; then Claude relays first (see Context budget), with a handoff naming the wave plan, the rules block and the base commit, and the prompt `/implement <handoff path>`. Builder, reviewer and helper subagents take their model and effort from the same table. The fallback model never starts a session or a ticket: it enters only through the fallback rule beside the table.
5. Inside /implement: name the feedback loop out loud (changeable-software step 5), then /tdd drives the slices. TDD is the tool, not a law. If a slice can't honestly be test-first, say so instead of faking it.
6. Before committing: /code-review, passing changeable-software's `references/review-checklist.md` to the Standards sub-agent as a standards source (local: `~/.claude/skills/changeable-software/`; cloud: `find ~/.claude/skills/synced -path "*changeable-software/references/review-checklist.md"`). Pass codebase-design's `SKILL.md` as a second standards source (`find ~/.claude ~/.agents -path "*codebase-design/SKILL.md" | head -1`), so the Standards sub-agent runs the deletion test and the adapter rule on every seam in the diff. Both live outside the repo, so /code-review will not find them unprompted. Then answer: what did we improve before leaving?

Context hygiene: keep steps 1 to 4 in one window where it fits. Past ~200k tokens, Claude relays at the nearest phase boundary, never mid-grill: the earliest is once /to-spec has published, because the spec carries what the grill decided. The context guard says when (see Context budget).

A repo may carry its own ticket loop (for example `docs/agents/ticket-workflow.md`). It can reshape steps 4 to 6 for that repo (who builds, which models, extra checks such as screenshots). It never removes step 0, the ticket as the spec, /code-review with the changeable-software checklist, or the cloud rules. Where it contradicts those, this file wins and the conflict is noted in the ticket's report.

## Spec check: fresh eyes before tickets

Right after /to-spec publishes and before /to-tickets, Claude runs the spec check without being asked. The session that wrote the spec can't review it, because it fills every gap from memory. A reader who has only the spec finds the gaps on paper, where a fix costs one edit, not in a builder halfway through a ticket. If a relay happens at this boundary, the handoff names the spec check and Show-me as next steps, and any built-but-unapproved artefact by its repo path with "awaiting approval".

1. Save the spec text to a file in the OS temp directory. Start two fresh subagents at once, as `subagent_type: "Explore"` (read-only, and it starts without any CLAUDE.md, so no workflow rule fills a gap the spec left), run as helper subagents (see "Models" under "Building tickets"). Each brief holds only the spec file's path, the repo path and its task: never the conversation, the grill, or a summary of either.
   - Comprehension: restate in a short paragraph what will be built, for whom, and what is out of scope. Then list every sentence that could honestly be read two ways.
   - Readiness: check every file path, module, type, signature and CONTEXT.md term the spec names against the repo and docs/adr/. List what is missing, misnamed, or contradicts an ADR.
2. Claude compares the restatement with what the grill decided. Every mismatch and every readiness gap is a finding, ranked Blocker (a builder would build the wrong thing or can't start), Major (a builder would have to guess) or Nit.
3. A Blocker or Major that is only wording: Claude fixes the spec issue and says what changed. One that needs a decision the grill didn't make goes to the user, one question per finding, before /to-tickets. Nits are listed, not fixed.
4. At most one re-check: if the spec changed, a fresh subagent reruns only the task whose findings changed it. Whatever it still finds goes to the user. No third round.
5. Report briefly: findings by rank, what changed, what waits on the user. Then name /to-tickets once Show-me is approved or skipped.

Skip it on the light path and whenever /to-spec didn't run.

## Show-me: the user's eyes before tickets

Right after /to-spec publishes, beside the spec check, Claude runs Show-me without being asked. A spec can pass the spec check and still produce the wrong screen or data shape, because every reader so far has read it as text. Show-me puts one compact artefact of the settled shape in front of the user while a fix costs one spec edit.

1. Timing: it starts when /to-spec has published, in parallel with the spec check's two subagents. The artefact goes to the user as soon as it is built, while spec check findings may still be open. /to-tickets waits for both the resolved spec check and the user's approval.
2. Kinds: Claude decides which kinds the spec touches and states in one line which fired. A user-visible screen gives one self-contained HTML file in the project's own palette and type, never browser defaults. A lifecycle or status flow gives a state diagram. Stored data gives a schema diagram. An interface with two or more callers gives a contract table (operation, input, output, errors, callers). One artefact per kind that fires, each about one screen in size: several kinds give several small artefacts, not one busy page.
3. Formats: the screen is its own HTML file. The three other kinds are sections of one Markdown model file (diagrams as Mermaid blocks, the contract table as a Markdown table, one section per kind). The model file is one file for the three non-screen kinds, so a spec yields at most two files: `<spec issue>-screen.html` and `<spec issue>-model.md`.
4. Producer: a helper subagent (see "Models" under "Building tickets"), started as `subagent_type: "general-purpose"` because it writes files. Claude saves the spec text once to the OS temp directory, and the spec check and the helper both read that file; after any spec edit Claude re-saves it before a fresh helper rebuilds. The brief holds the spec file's path, the repo path, the kinds that fired with an output path in the OS temp directory for each, where the project's palette and type live, and three rules: one screen each, no variants, nothing the spec does not say. Never the conversation. Claude finds the palette and type source beforehand: CSS tokens, a theme file or a design reference; with none, the project's existing screens; with no screens yet, Claude asks the user for a visual reference before the helper starts. The helper reports the paths and a list of every guess it had to make to finish.
5. Guesses are findings: each goes into the spec check report as a Major, since a builder would have guessed the same thing, and follows the spec check's rules (a wording fix is Claude's; a decision goes to the user, one question per finding).
6. Home: as soon as the helper reports, Claude copies the files into `docs/show-me/`, commits and pushes them on main at once, and links them from the spec issue. Each rebuild is a new commit. The helper never writes inside the main checkout.
7. Delivery: the user gets each artefact as a published page when the session can publish a page; otherwise the files are attached in chat. The model file also renders at its GitHub link.
8. Approval loop: the user replies "approved" or asks for changes. Every change goes into the spec first; a fresh helper subagent then rebuilds from the edited spec. No cap on rounds (the spec check's one re-check cap is separate). Claude records the approval as a comment on the spec issue naming the commit that holds the approved version.
9. Staleness: from the moment the helper starts, Claude judges every spec edit, from any source, for whether it changes something the artefact shows. If so, rebuild, say so in a line, and re-ask any approval already given. An edit made while the helper is still building means a rebuild once it reports. Wording-only edits change nothing and leave the approval alone.

Show-me confirms one settled shape and never offers variants. Comparing directions is a grill question, answered by /prototype; Show-me runs again after it. When the user asks in words to see the spec's screen or shape ("show me the screen", not "show me the diff"), run the step early from the saved spec file; with no spec file and no screen in play, say there is nothing to show yet.

Skip it on the light path, and on the full path whenever no kind fires, saying so in a line as the wave plan does.

## Waves: tickets in parallel

Right after /to-tickets publishes and before /implement, write the wave plan without being asked. Skip it when there are fewer than three tickets or the edges form one straight chain, and say so in a line.

Several specs can share one plan. When the user has run /to-tickets on more than one spec before /implement, write one wave plan across all their tickets, with a spec column in the table. Edges stay as /to-tickets wrote them; where a ticket in one spec needs another spec's work, add that edge and say so under the table. The area check in step 2 runs across specs, so two specs that touch the same area take turns there. If no single plan can hold them without a cycle, stop and show which specs clash; the user runs those one after the other.

1. Layer by blocking edges. Wave 1 is every ticket with no blockers. Wave N is every ticket whose blockers all sit in earlier waves. A cycle means /to-tickets got an edge wrong: stop and show it to the user.
2. No edge doesn't mean safe in parallel. For each ticket, estimate the areas it will touch: modules, schema and migrations, shared types, config, route tables, lockfiles, CONTEXT.md. Two tickets in one wave that share an area can't build at once, so the later-numbered one drops to the next wave. Unsure counts as shared. Expand–contract migrate batches split by directory are built to run together and stay in one wave.
3. Show the plan as one table: wave, ticket, blocked by, areas touched, builder model (risk rule under "Building tickets"). Under it, name the critical path: the longest chain of blocking edges. That chain is the floor on build time however many builders run, so a long one is a reason to revisit the breakdown, not to add builders. When a ticket drops a wave for a shared area, say which area in a line under the table.
   Under that, write "Rules that hold for every ticket": the CONTEXT.md terms the build uses, the ADR shape tickets implement but don't redesign, the frozen cores no ticket moves, and what no ticket touches. Every builder brief carries this block. A ticket that finds itself breaking one of these rules has left the spec: it stops and says so.
4. The user types /implement once against the plan, and it runs the whole plan, every wave, to the end: no stop between tickets or waves to report or ask, and a parked ticket (see "Building tickets") doesn't stop it. An /implement run is expected to run in auto mode; deny rules apply in every mode. Before the first builder, check `.claude/worktrees/` is in `.gitignore`; if not, add it and commit that alone. Each ticket gets a fresh worktree subagent (Agent tool, `isolation: "worktree"`) running the loop in "Building tickets". That replaces /clear between tickets on every machine, not only in the cloud. At most three builders at once unless the user sets another number.
5. Dispatch by frontier, not by wave. A ticket starts the moment its own blockers have landed and no running builder holds any of its areas, without waiting for the rest of its wave. Without the area check, a ticket dropped a wave in step 2 can still start beside the ticket it conflicts with. The waves are the plan the user reads; the frontier is what runs.
6. Builds run in parallel; landing doesn't. Land one ticket at a time in finish order: rebase onto main, full suite on the integrated result, merge. Fix a conflict while landing by hand: read the commit or ticket behind each side, keep both intents where they fit, and run the full suite again. If both sides came from this plan's tickets, step 2 missed a shared area: name the miss in that ticket's report. If main moved for other reasons, just say so. After the push, the landing commit's CI run is part of the ticket. Before the final report the coordinator reads the runs for its landing commits (`gh run list --commit <sha>`, or the GitHub tools in a cloud session). A red run is a failed landing: fix forward as a new ticket, or revert, and say which in the report.

## Building tickets: defaults for any repo

A repo's own loop can tighten these, not drop them.

### Models

One table holds every model and effort; every other passage in the workflow, the guide and the README names the role or links here (`#models`). A model change is one edit to this table plus regenerating the cloud copy. Pass `model` and `effort` from the table on every Agent call.

| Role | Model | Effort |
|---|---|---|
| Coordinator | opus (settings value `"model": "opus"`) | high |
| High-risk builder | opus | medium |
| Low-risk builder | sonnet | high |
| Standards reviewer | the model of the builder's risk row | the effort of the builder's risk row |
| Spec reviewer | sonnet; opus when the ticket touches core domain logic, stored data, parsing, time, money or auth | high on sonnet, medium on opus |
| Helper subagent (exploration, /research, /prototype, DESIGN-IT-TWICE drafts, the spec check, the Show-me artefact, the spec-drift pass) | sonnet | high |
| Fallback | fable | high |

- Risk rule: a ticket that touches stored data, parsing, imports, exports, time zones, money or auth gets the high-risk builder; narrow UI and copy get the low-risk builder. The same rule picks the Standards reviewer's model.
- Fallback rule: the fallback is never a first choice. When the high-risk builder has failed the same ticket twice in a row (two builds or fix rounds that each still leave a red suite or a blocking finding), a fresh fallback subagent takes the next fix and its review, briefed with the ticket, the current diff, both failure reports and the rules block. A suite tripwire pass-through (it let a builder through after two blocks) counts as one failed build. Where the message isn't shown, as in a headless run, the builder's state file under `~/.claude/state` records it (`"gave_up": true`). If the fallback fails too, the ticket parks (see below). The fallback only ever runs as a subagent, never as the coordinator.

### The ticket loop

- Mechanical checks are commands, not agents: the full test run, lint, screenshot or snapshot diffs. Spend a reviewer only on judgement. Reviewers read the diff; they never run the full suite, lint, typecheck, build or the whole e2e suite, because the builder already ran them and the coordinator runs the full suite on the landing commit. A reviewer may run one targeted test, or a probe test kept outside the worktree, only to prove a suspected bug. Say this in every reviewer brief.
- The builder runs only the touched tests plus a compile or build, so reviewers never see broken code. Review runs on the diff. The coordinator runs the full suite once, after review and the fix round, on the frozen commit that will land. Run it once per landing candidate: a rebase or any content change makes a new candidate, which gets its own run. The suite tripwire backs both duties where its hooks are on.
- A ticket that changes behaviour a user can observe also needs runtime proof from its builder: the change shown running, not only passing tests. Use a curl probe against the running service, a headless browser flow, or the app's CLI output, and put the command and what it showed in the ticket report next to the tests run. This is a builder duty; reviewers read the diff and judge the proof as written.
- Record the base commit before building, and name it in every builder brief. The builder's first act, before anything else, is to confirm its worktree contains that commit (`git merge-base --is-ancestor <commit> HEAD`). If it doesn't, the builder stops and reports, and the coordinator recreates the worktree from the right commit. Before landing, fetch: if `main` moved, rebase and rerun the full suite on the integrated result. Never force-push over another session.
- If the repo has screenshot or snapshot tests, any visual change the ticket didn't ask for is a fail. Add a screens review (both themes, every language the app ships, right-to-left if it ships one) only when screens changed.
- Blocking findings and cheap, clearly worthwhile advisories go back to the same builder, which still has its context, in one round. A review with only advisories gets a fix round only when one of them is about type safety, a dependency cycle or a frozen-core boundary; renames, helper moves and other polish are listed as debt in the report instead, since every round reloads the builder's whole context. Only what the fix touched is reviewed again: a fix that adds no new logic is re-reviewed by the coordinator reading its diff, not by a fresh reviewer. If a reviewer on the low-risk builder's model fails the same item twice, the high-risk builder's model does the next fix and review.
- Heavy test runs that the machine can't run two of at once go through a lock, not discipline. The next ticket's builder may start while the current one is in review when the two share no files; it queues on the lock for tests.
- Nothing inside the loop waits on the user. Thresholds are set by rule or script, judgement calls are the coordinator's and are recorded. The user is needed only for grilling and for decisions that are genuinely theirs.
- A ticket that needs the user's ruling, and isn't covered by the unattended exception below, parks instead of stopping the run: push its work to the ticket's branch, put the ruling at the top of its report, release its areas, and keep dispatching every ticket that doesn't depend on it. Tickets blocked by a parked ticket wait for it. The run ends when nothing else can start, and its final report opens with every pending ruling, so the user comes back once, at the end. Tickets that touch a frozen core, money, auth or the shape of stored data land as normal and are listed in the final report under "Read before deploying" with their commit. The final report ends with "Where I needed you": one line per ruling asked for, permission prompt or denial, hook block the user had to clear, and stall.
- A ticket lands by merging to main and pushing, on every machine. Never open a pull request or wait on one unless the user asked for it; a harness or tool default that suggests one doesn't apply.
- One commit per ticket, its message naming each reviewer, its model and its verdict.
- A Choice is a decision on something the ticket left open, resolved by the nearest precedent and made inside the spec. A ticket that turns out to be wrong stops and reports; it may continue only under changeable-software's unattended exception, which needs all three conditions: the revision is reversible by configuration or a single revert, nothing has run for real, and the pending ruling is listed at the top of the report. Choices and any pending ruling go at the top of the ticket report.
- Report each ticket in plain words: what it does on screen or in behaviour, not the diff. Open the report with the Choices and any pending ruling, then the tests run, any runtime proof and each reviewer's verdict.

## Context budget

Every request re-reads the whole conversation, so usage scales with context size times the number of calls. Measured on the author's machine, Jul to Oct 2026: about 228k tokens per request, 97% of them cache reads, and subagents making half the calls. These rules keep the window small without breaking the cache. They sit on top of everything above and change no step.

Runs on its own (local installs; hooks in `~/.claude/settings.json` call `~/.claude/scripts/context_guard.py`, alongside the hooks already there. The sync job keeps the scripts in step; the hook entries are set per machine):
- Each prompt past 200k shows the user the size and the next move. Claude gets one note telling it to relay at the next phase boundary, or at the next task boundary (a request answered, a fix landed) when no workflow step is under way. It never asks the user to /compact or /clear.
- Past 400k the session stops taking new work. A prompt is refused unless it is `relay` (Claude hands off at once), a housekeeping command such as /clear, /compact or /handoff, or starts with `override`, which lets the session run on for another 100k before the stop returns. Claude also can't start new subagents past 400k, so an /implement run relays at its next ticket boundary; anything already running finishes or parks first.
- After any Bash output over 8,000 characters, Claude gets a note to filter at the source.
- Resuming a session over 200k with a cold cache warns before the first request.
- Cloud sessions get the same hooks when the repo's `.claude/settings.json` names them and the scripts are in the repo (`templates/project-settings.json` wires them). Without that, the rules below still apply there, and Claude keeps the 400k stop itself.

Claude does without being told:
- One task per session. When a light-path change or an /implement run lands and the next request is unrelated, relay it into a fresh session instead of taking it on in this window. Don't ask the user to /clear.
- Loops: /loop re-runs its prompt inside the same conversation, so its context only grows. A loop expected to run more than a few passes goes into a scheduled task that starts a fresh session each pass, with the state it needs in a file the task reads. A /loop already running relays at the 200k note like any other session.
- Filter shell output at the source: `| tail -40`, `| grep`, quiet flags, test reporters that print failures and a summary. Never print a whole log, lockfile or build output.
- Grep first, then read files by range once the location is known.
- Never break the cache mid-session: no model switch in the main session (the fallback only ever runs as a subagent), and no CLAUDE.md, template or settings edits in the middle of working sessions. Such edits land and get tested in a fresh session.
- Subagent briefs carry the ticket, the files or diff, and the checklist, never the conversation. A reviewer works to a budget of about 40 tool calls; at the budget it stops and reports what it has. Builders and reviewers report only what the coordinator acts on: verdict, Choices, pending rulings, tests run. The diff stays in the worktree.

You do:
- Weekly (schedule it with cron or launchd if you like): `python3 ~/.claude/scripts/context_report.py`. The report lists sessions by peak context, flags any past 200k, and shows the baseline before any work, the subagent share and the oversized outputs. It covers 7 days by default, or pass a number. Bring the output into a session and pick one rule to tighten; run it again after a heavy build.
- If the baseline (the "first" column) grows, run /context in a fresh session of that repo and cut what loads on every request: CLAUDE.md length, imports, MCP servers the repo doesn't use (/mcp), and unused skills or plugins.
- /context costs about 50k tokens: its full output is saved into the conversation and re-sent with every later request. Read it, then /clear. Never run it mid-task in a session you mean to keep.

## One home for each thing

- Vocabulary: CONTEXT.md. Do not copy it into CLAUDE.md. This overrides changeable-software's "Where the answers live" on vocabulary only. Where an installed skill says GLOSSARY.md, or calls CONTEXT.md legacy, read that as CONTEXT.md and don't rename the file.
- Hard-to-reverse decisions: docs/adr/.
- The project CLAUDE.md `## Design` section holds, per frozen core, its enforcing mechanism and its sealed measures, plus named debt, and points to CONTEXT.md for terms. Which files are frozen or disposable is read from the code markers.
- Code markers: `# FROZEN CORE: <why>` and `# DISPOSABLE: <why>, <until>`.

## Upkeep

/improve-codebase-architecture, pick one candidate, take it into /grill-with-docs, design it on /codebase-design. Alongside it, run the context report (see Context budget) and read "Where I needed you" next to it, then tighten one rule or hand off one item if either flags something. A bug that comes back twice is an architecture question, not another patch; /diagnosing-bugs post-mortems feed the same route.

A lesson (from a correction, an escaped bug or a post-mortem) lands on the highest rung that can hold it: a deterministic check or lint rule, then a regression eval case or test, then a changeable-software invariant, and only last a CLAUDE.md or skill note, since every note is re-read on every request (see Context budget). When a lesson lands as a note, say in the commit which higher rung couldn't hold it and why.

After any edit to this workflow or the changeable-software skill, run the routing evals from the dev-workflow repo (`python3 -B evals/run.py`) and compare with the baseline in `evals/results/baseline.txt`.

Spec drift, in the same pass when the repo has specs: a fresh Explore subagent (a helper subagent) gets the spec issues closed since the last pass and the current code, and lists each place where they now disagree, with the file and the spec line. Claude doesn't pick a side. Each disagreement goes to the user as a choice: the code is wrong (a bug, via /triage) or the spec went stale (a comment on the spec issue saying what changed and why).

## Any time

/research, /prototype, /tdd, /code-review, /wizard (steps only a human can do), /to-questionnaire, /wait-what, /teach, /writing-for-agents, /domain-modeling.

Library docs: use the `ctx7` CLI through the find-docs skill (`npx ctx7@latest library <name> "<query>"`, then `npx ctx7@latest docs <id> "<query>"`) before web search or training data, and whenever the user mentions ctx7 or Context7. This holds outside coding work too. CLI and skill only: never install the Context7 MCP server or plugin. find-docs is a trimmed copy, kept in step with the other skills by the sync job and installed as an account skill for cloud sessions. Don't rerun `npx ctx7 setup`: it overwrites the trimmed copy with the long original.

Past the commit, where the Pocock flow stops: shipping-and-launch, observability-and-instrumentation, security-and-hardening, deprecation-and-migration, ci-cd-and-automation, performance-optimization. Model-invoked; reach for them when the work is deploying, instrumenting, hardening or retiring something, not while building it. Install them locally and as account skills for cloud sessions.

## Cloud sessions

Applies when the session runs in a disposable cloud container (Claude Code on the web), where your local ~/.claude isn't loaded and account skills appear under ~/.claude/skills/synced. Everything above still holds; this adds the rules the container forces.

- The container is deleted after inactivity, and anything not pushed goes with it. A stop hook checks the main checkout after every reply and re-prompts while it holds uncommitted, untracked or unpushed work. Keep the hook. Work so it stays quiet.
- Builders never work in the main checkout. Every /implement ticket, and any subagent that writes code, runs as a subagent with worktree isolation (Agent tool, `isolation: "worktree"`). One fresh subagent per ticket is the cloud form of "/clear between tickets".
- Before the first builder, check `.claude/worktrees/` is in the repo's `.gitignore`. If it isn't, add it and commit that alone, or the worktrees show up as untracked and trip the hook.
- The main checkout only ever receives a reviewed commit (the Show-me artefact and CONTEXT.md are reference documents, not code, and land by direct commit): builder finishes, /code-review passes, merge to main, push, all in the same reply. Never end a reply with the main checkout dirty. No pull requests here either, whatever the cloud harness's git defaults say (see "Building tickets").
- Context hooks run only when the repo's `.claude/settings.json` names them and the scripts are in the repo, and relaying is by scheduled task (see "The relay"). Without the hooks Claude keeps the 400k stop itself: past 400k it starts no new subagents and relays at the next boundary. The fresh subagent per ticket keeps the coordinator small, and the harness's own auto-compact is the backstop; don't ask the user to /compact.
- The user-only commands come from the Pocock plugin here. If one isn't found by its plain name, it takes the plugin's prefix (`mattpocock-skills:` before the name).
- Stopping mid-ticket: commit the work to the ticket's branch and push it, or write a /handoff file, commit and push it. Nothing important lives only in the container.
- When the stop hook fires while a builder is still running in a worktree, something is wrong: the main checkout got touched. Find out what, don't just wait it out.
- On the first coding reply, compare this skill's `Template sha256` line with `template.sha` at the dev-workflow repo root (https://raw.githubusercontent.com/weezyf1995-boop/dev-workflow/main/template.sha). If they differ, tell the user the cloud skill is behind the workflow file and carry on.
