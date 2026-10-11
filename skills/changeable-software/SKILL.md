---
name: changeable-software
description: Design, build and review software so the next change is cheap, safe and local, with tests and feedback fitted to the kind of problem. Use when creating, extending, refactoring or architecting any codebase, module, service, pipeline or script — including when the user only says "build me X", "add a feature", or "fix this". Also use when judging existing code or a design rather than writing it: "is this a good design", "should I split this", "am I over-abstracting", "review this architecture", "where should this live", "is this worth refactoring", reviewing a PR for structure rather than correctness, or reviewing AI-generated code for structural coherence. Has a light path for small changes and a full path for anything that adds a boundary or touches money, auth, external APIs or irreplaceable data. Trigger before writing code, again before declaring the work finished, and whenever asked to review.
---

# Changeable Software

Today's code is the environment tomorrow's changes have to happen in. The question is never just "does this work?" but "what will this make the next change cost?" Everything here follows from that.

The reasoning behind these rules is in `references/laws.md` — read it once, and again whenever a rule here feels wrong for the situation. Testing is in `references/testing-standard.md`. Finishing is in `references/review-checklist.md`.

**Reviewing rather than building?** If the code or design already exists and the job is to judge it — a PR, an architecture, someone else's module, generated code — stop here and use `references/review-mode.md`. It has the procedure, the per-law probes and the report format. The rest of this file is for work you are about to do.

## Pick the path first

**Light path.** The change touches roughly one file, introduces no new boundary, and is revertible in a single commit. Do steps 1 and 5, then the "Always" block of the review checklist. Nothing else.

**Hard disqualifiers — full path regardless of size.** If the change touches a frozen core (one list, defined in step 1) or an external boundary — an external API, or data you cannot regenerate — take the full path even if it is four lines. Size is not the risk; blast radius is. A four-line change inside a live trading loop, a payment path, or an agent's execution path is not a small change.

**Full path.** Everything else that is not light: a new module, a changed interface, a change spanning files, or anything not cleanly revertible. Do all five steps, and record what the next session needs in the project's `CLAUDE.md` — see "Where the answers live".

If genuinely unsure, take the full path. But do not run it on a typo fix. Ceremony on trivial work is how a procedure teaches people to skip it when it matters.

## The five steps

### 1. Classify the problem

The method has to fit the system (Cynefin — see `references/laws.md`, Law 13):

- **Clear**: cause and effect obvious. Use the established pattern in the repo. Do not invent.
- **Complicated**: cause and effect exist but need analysis or expertise. Slow down, read the docs, find the specialist. This is a knowledge problem, not an iteration problem — more attempts do not substitute for understanding.
- **Complex**: cause and effect visible only in hindsight. Small experiments, observe, adapt, keep it reversible. Analysis will not reveal what only experience can.
- **Chaotic**: it is broken now. Stabilise first, understand later.

Most feature work is clear or complicated. "We don't know what users want yet" is complex. Incidents are chaotic. **Getting this wrong is the most common root cause of wasted effort** — usually by treating a knowledge problem as an iteration problem, or the reverse.

If the classification is uncertain, treat the domain as complex: probe, and preserve reversibility. Re-ask as you go. Systems drift from complicated to complex while the playbook stays cached, and the first sign is feedback that starts lying.

One more classification: does this change touch a **frozen core** (`references/laws.md`, Law 1)? Anything whose failure is unacceptable and whose change is rare: money movement, authentication or authorisation, risk limits, kill switches, consensus paths, verified parsers, an agent's execution path. This is the one list; the path rule above points here. Name it now, not at step 3: frozen cores decide where the boundaries go, and inside them correctness outranks changeability. Mark it in the code and record it in `CLAUDE.md` — see "Where the answers live".

And does it change a **sealed measure** — a success criterion, threshold, frozen grid or verdict unit, anything that decides what counts as evidence (`references/laws.md`, Law 1)? That is an amendment: its justification and its consequence are written down before the next result exists, not after.

### 2. Name the concepts

List the domain concepts this change touches, and the single name each will carry everywhere: conversation, code, schema, API, tests, docs. If a thing is `user` in one place and `account` in another, resolve it now.

Concrete check: can you point at two names in this change that mean the same thing? If yes, you are not done. Match existing repo vocabulary unless it is actively wrong.

### 3. Design the boundary, then delegate the interior

For each module the change creates or alters, write the interface before the implementation: responsibilities (including what it explicitly does *not* do), names, contracts and invariants, failure behaviour, dependencies, what it exposes and what it hides.

Prefer deep modules — substantial capability behind a small interface. A module is not good because it is small; it is good because its interface hides real machinery and stops implementation knowledge leaking outward. Organise around the decisions hidden, not the order the program runs in.

Before committing to the shape, two questions (reasoning in `references/laws.md`, Law 3 and the generality note):

- **Where did the complexity go, and who pays?** Every decision moves it somewhere — name which: callers, implementation, or operations. "It got simpler everywhere" is not an available answer; if that is what you wrote, you have not found where it went.
- **Generalise or stay narrow?** Keyed to step 1: if the problem is complicated, consequences are discoverable by analysis and deliberate generality prevents expensive leakage later. If it is complex, the future shape does not yet exist in knowable form and generality is speculation — stay narrow and replaceable. Unsure → whichever mistake is cheaper to reverse.

Your own understanding is not evidence the design is simple. It is simple when it is simple for whoever modifies it next.

### 4. Pick the thinnest end-to-end slice

Find the narrowest path that exercises the real integration: input to output through every layer, not one finished layer in isolation. This first slice is a tracer bullet — its job is to reveal whether the direction is right, not to be the product. Big-bang integration delays the most important feedback until the most assumptions have piled up.

If the change adds no new slice — an interface change, a refactor, a fix inside existing behaviour — the tracer is the existing end-to-end test on that path. If there is none, writing one is the first job of step 5.

### 5. Set the feedback loop

Name what will tell you you are wrong before you go further: compiler, types, tests, linter, assertion, a run against real data, a user, a domain expert, telemetry. Say which one, out loud.

The rate of trustworthy feedback sets the safe rate of change. If you can make ten changes before learning whether the first was right, you are working in the dark — shorten the loop or slow down.

On the full path, read `references/testing-standard.md` and write down which tests this change needs.

## Where the answers live

Nothing carries between sessions unless it is in the repo. Anything the five steps decide that the next session must honour goes in a `## Design` section of the project's `CLAUDE.md` (create it if absent): the vocabulary from step 2, frozen cores and what enforces each (a purity test, a separate process, a fingerprinted config — a frozen core with no mechanism is a declaration, not a core), sealed measures and where their amendment register lives, disposable areas, and named debt with its reason. That section is agent instructions, and Law 6 puts vocabulary there for a reason.

Mark the code too, so review mode can see it without the file:

- `# FROZEN CORE: <why>` at the top of a frozen module.
- `# DISPOSABLE: <why>, <until>` at the top of throwaway code. Unmarked throwaway code is treated as load-bearing.

## While writing code

- Build the tracer-bullet slice first. Make it run end to end before widening it.
- Test at the boundary from step 3. Tests that pin the interior will fight the next refactor.
- Keep the vocabulary from step 2 exact. Do not let a synonym in.
- Implement, run feedback, adjust. Do not batch.
- Treat the requirement as a hypothesis. When the working slice shows it was wrong, say so and stop — surface it and wait for a ruling. Do not proceed on your own revision, and do not quietly build the wrong thing better. Regenerating the same code from the same spec is not progress unless new information entered the loop.
  - *Unattended exception (Amendment, owner's authority, 2026-09-07).* When no ruling can be had in this session — nobody to ask — you may continue only if all three hold: the revision is reversible by configuration or a single revert; nothing has run for real; and the pending ruling is listed at the top of the deliverable. A revision that fails any one of the three stops the work. Drawn from the keel build, which did this before it was written down.
- Comment what the code cannot say: intent, rationale, invariant, contract, why a surprising decision was made. A comment that translates code into English is duplication — delete it.
- Refactor as you go. There is no future cleanup phase; anything left in place becomes something other code depends on.

## When a problem recurs

event → pattern → structure → mental model

Patch the event if you must, then ask what structure keeps generating it. Once deserves a fix. Twice deserves an architectural question. Applies to flaky tests, CI failures, agent misbehaviour and process friction, not just code.

## Before declaring done

Run `references/review-checklist.md` — the "Always" block for light-path changes, all of it for full-path.

Then answer honestly: **what did we improve before leaving?** Never leave the structure strictly worse than found. If the change added debt knowingly, name it and the reason, so the next person is not paying for an unknown unknown.

## When another skill disagrees

Other design skills are installed alongside this one. They are technique; this file is doctrine. Use them
freely for vocabulary and procedure — then let this file settle any conflict, and say which rule you followed.

The `mattpocock/skills` set (installed 2026-09-18) is the current instance, and a friendly one: Matt Pocock is
one of the four sources `references/laws.md` was synthesised from. `codebase-design`, `domain-modeling` and
`prototype` are Laws 4/5, Law 6 and Law 1's discount rate in sharper operational language — prefer their
**deletion test** and their *"one adapter means a hypothetical seam, two means a real one"* over anything
vaguer in step 3. Three places they diverge:

- **Refactor timing.** `tdd` says refactoring belongs to a later review stage. Law 10 says refactor as you go;
  there is no future cleanup phase. Doctrine governs.
- **TDD is not the default.** `implement` says "use /tdd where possible". Strict TDD is on the *deliberately
  not law* list. Law 8 asks for the cheapest trustworthy feedback for the risk at hand — types, assertions,
  linters or a real run may beat a test. And on a new slice the **first** test is the end-to-end tracer, then
  unit and contract tests where risk lives.
- **The gates are absent.** None of them run step 1, the light-vs-full path, the frozen core or the sealed
  measure. A skill that ends at "commit to the current branch" has not finished the work this file describes.
  Run those gates around such a skill, not instead of them.

## Deliberately not required

The canonical list of what is deliberately not law — module size, function length, strict TDD, big-upfront design, comments, plain structure in marked-disposable code, a justified and commented local deviation — lives in `references/laws.md` § "What is deliberately not law". It is not restated here; one list, one place to change it. What binds hardest while building:

- **No proxy as a target.** Coverage is not quality, class count is not modularity, line count is not productivity, passing tests are not good design, volume of generated code is not throughput. The moment any rule here becomes a number to hit, it has become the thing it warned against — including the five steps above.

## Reference files

- `references/laws.md` — the thirteen laws and their reasoning. Read when a rule above needs justification, or when two seem to conflict.
- `references/testing-standard.md` — which tests, at which level, written how. Read at step 5 on the full path.
- `references/review-checklist.md` — before any PR, commit to main, or "it's done".
- `references/review-mode.md` — judging code or a design that already exists. Read instead of this file when reviewing rather than building.
- `references/philosophy-of-changeable-software.md` — the reference edition the laws were distilled from. Open only when a law's provenance or tier is in question, or for the ruling on the declined Law 14 (Conway). Where it and the skill disagree, the skill governs.
