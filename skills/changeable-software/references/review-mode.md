# Review Mode

Read this when judging code or a design that already exists — a PR, an architecture, someone else's module, or a pile of generated code. For finishing your own work, use `review-checklist.md` instead. The difference is the audience: the checklist is questions you answer for yourself, this is a report someone else has to act on.

A reviewer, not a summariser. Every finding is a judgment about the specific thing in front of you, with the law cited and the cheapest correction named.

## Standard of evidence — read before reviewing

`laws.md` was built by agreement across four sources. That filter exists to stop taste being promoted to law, and it binds the review as much as the philosophy:

- **Law** — three or more sources agree. Cite it plainly.
- **Contested** — the sources split. Give the condition that decides it, not a verdict. See "Contested ground" below.
- **Advisory** — one source. Say so when you cite it.
- **Amendment** — the frozen core, the discount rate and the sealed measure in Law 1, and the taxonomy in Law 13. Owner's authority, not the sources'. Cite as such.

Silence is not disagreement, and a dissent is not erased because the majority wins.

Three constraints follow:

- **No finding without a law.** If an observation traces to no numbered law, it is a preference. Drop it, or label it a preference and let the reader weigh it.
- **Do not promote preferences to laws.** An idea is not universal because it sounds wise — including one you arrive at mid-review.
- **Contested stays contested.** Where the sources split, name the deciding condition and stop.

A review that reaches beyond its evidence is doing the thing Law 12 warns about.

## Procedure

Run in order. Skip a step only when it does not apply.

**0 — Classify the system.** Clear, complicated, complex, or chaotic (Law 13). This decides which method is even valid; getting it wrong invalidates the rest of the review. Then ask whether any of this is **frozen core** (Law 1) — risk limit, kill switch, auth or consensus path, verified parser. Inside a frozen core, correctness outranks changeability and the findings change accordingly. Ask too whether the change touches a **sealed measure** — a threshold, criterion or verdict unit; if so the finding is about the amendment record (justification written before the result, consequence pre-committed), not about the value. Also ask whether the code is **marked disposable**. The marks are `# FROZEN CORE: <why>` and `# DISPOSABLE: <why>, <until>` at the top of the module, and the project's `CLAUDE.md` design section lists frozen cores and disposable areas; check both. If marked disposable, structural findings are moot; if unmarked and load-bearing, that is itself the finding.

**1 — Name the concept.** What is the thing called, and is it called that everywhere (Law 6)? Vocabulary drift is the cheapest violation to find and often the first symptom of an unresolved design disagreement.

**2 — Trace the next change.** If the user has stated the next planned change, use it. If not, ask before reviewing; if you cannot ask, state the assumed next change at the top of the report so the reader can reject the premise. Then, for the one or two most likely next changes: For each: how many files, how many concepts must be understood first, how far the decision propagates, what can silently break (Laws 1, 2). This is the core of the review — do it with real file and function names, never in the abstract.

**3 — Locate the complexity.** For each abstraction or boundary, where did the complexity go and who pays — callers, implementation, or operations (Law 3)? "It got simpler" is never an acceptable answer alone. Then ask where it should live.

**4 — Judge the boundary.** Interface against interior (Laws 4, 5). Is the module deep — real machinery behind a small interface — or shallow, a pass-through that costs a reader a hop and hides nothing? Is failure behaviour defined at the boundary?

**5 — Check the feedback loop.** How many changes can be made before anything trustworthy says the first was wrong (Law 8)? If the answer is "many", the safe rate of change is below the actual rate. Tests are one mechanism; so are types, assertions, static analysis, telemetry, domain experts and real users.

**6 — Look for the generator.** If this problem has happened before, descend: event → pattern → structure → mental model (Law 11). Patching a recurring event is not a fix.

**7 — Report.** Format below.

## Per-law probes

Each law, as a question you can answer about the code, the signal that it is being violated, and the correction.

**1 — Changeability is supreme.** Probe: for the likely next change, count files touched and concepts a newcomer must hold. Signal: correct today, resistant to modification. Correction: localise the decision that propagates furthest. Exceptions: frozen core, marked-disposable code, sealed measure.

**2 — Complexity is paid by readers.** Probe: which of the three forms is present — change amplification, cognitive load, unknown unknowns? Flag the last hardest; the author's own understanding is not evidence of simplicity.

**3 — Complexity moves, never disappears.** Probe: name where it went and who pays. Signal: a cache with no invalidation story; an abstraction that simplified callers and made the implementation unownable. Correction: put unavoidable complexity where total cost is lowest, usually behind one boundary rather than spread across callers.

**4 — Information belongs behind deep boundaries.** Probe: ratio of capability provided to interface exposed. Signal: implementation detail leaking through parameter names, return types, or error shapes. Correction: organise around the decisions hidden, not the order the program runs in.

**5 — The interface is the design.** Probe: what must every caller understand — responsibilities, names, contracts, invariants, failure behaviour, dependencies? Signal: a polished interior over an undefined contract. Under AI-assisted work this tightens: the machine may write the interior, it may not silently decide what the abstraction means.

**6 — Name the thing first.** Probe: does one concept appear as `user` here, `account` there? Signal: a thing nobody can name in one phrase has not been understood. Correction: fix vocabulary across code, schema, API, tests, docs and agent instructions, then look again at the structure.

**7 — Requirements are discovered.** Probe: what new information entered the loop? Signal: regeneration from the same spec, which reproduces the same misunderstanding faster. Diff the output before believing a change was made.

**8 — Never outrun feedback.** Probe: changes possible before anything trustworthy answers. Correction: shorten the loop or slow the change rate — one of the two.

**9 — Thin end-to-end slices.** Probe: does the first increment cross the whole system or finish one layer? Signal: big-bang integration, which delays the most important feedback until the most assumptions have accumulated.

**10 — Design continuously.** Signal: a promised future cleanup phase. Correction: name the smallest structural improvement to make before leaving this file.

**11 — Fix the generator.** Probe: has this occurred before? Once deserves a patch, twice deserves an architectural question. Applies to teams, processes and agent workflows as much as code.

**12 — Do not worship proxies.** Coverage is not quality, class count is not modularity, function length is not simplicity, passing tests are not good design, volume of generated code is not throughput. Binds this file too: the moment a law here becomes a numeric quota, it has become what it warns against.

**13 — Method must fit the system.** Probe: is a complicated-system method being used on a complex system, or the reverse? Signal: demanding an upfront answer where only an experiment can produce one; running more attempts at what is actually a knowledge problem.

## Contested ground — do not resolve by taste

**Generality.** "Design good general-purpose abstractions" and "do not build for imaginary futures" are both right, in different conditions. Generalise early when consequences are discoverable by analysis. Stay replaceable when they are visible only through experience. Unsure — prefer the mistake that is cheaper to reverse.

**The expertise exception.** In a complicated domain a specialist can safely make more upfront decisions than a generalist. Two guards, from `laws.md`: expertise is a demonstrated record of correct predictions in this domain, not confidence — if you cannot point at the feedback that calibrated you, the exception does not apply to you. And it amplifies classification error, so where the classification itself is uncertain, it does not apply.

## What is NOT a violation

Do not flag anything in `laws.md` § "What is deliberately not law". Flagging those is the most common way this review goes wrong. By name: module size, function length, not using TDD, deliberate upfront design, comments that carry intent, plain structure in code marked disposable, and a commented, justified local deviation — judge the reason, not the deviation. The reasoning for each lives in `laws.md`; it is not restated here.

If a finding reduces to one of these, drop it or re-derive it from an actual law.

## Output format

Lead with the finding that most raises the cost of the next change. Then, for each:

- **What.** The specific file, module, boundary or name. No abstractions.
- **Law.** Which law, its tier, and the concrete evidence.
- **Cost.** What the next change now costs that it otherwise would not.
- **Correction.** The cheapest fix, and whether it is worth doing now.

Then two closing sections:

- **Not flagged.** Things that look like violations and are not, with the reason. Load-bearing — it is what stops the review reading as a style complaint.
- **Before you leave.** The single structural improvement to make now (Law 10).

Cap findings at what actually matters. Three real ones beat eleven padded ones.

## How this review fails

- A finding that traces to no law. See "Standard of evidence".
- Restating philosophy instead of judging what is in front of you. Every paragraph must point at something specific.
- Flagging style, length or count. See "What is NOT a violation".
- Reviewing a complex system with complicated-system methods — demanding an upfront answer where only an experiment can produce one.
- Treating your own comprehension as proof the design is simple. It is simple when it is simple for the next person who must safely modify it.
- A finding with no correction, or a correction more expensive than the problem.
- Applying changeability findings inside a frozen core, where correctness outranks them.
