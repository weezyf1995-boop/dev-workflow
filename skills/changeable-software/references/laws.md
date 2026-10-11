# The Laws of Changeable Software

Synthesised from four sources: John Ousterhout on structure and complexity, Andrew Hunt and David Thomas on pragmatic practice, Matt Pocock on design in AI-assisted development, and Sandeep Swadia on systems thinking and decision-making in complex systems. A proposition became Law only where the sources agreed. That filter exists for one reason: to stop personal taste being promoted to universal law. It is not a proof — these are not independent authorities of equal weight, and their agreement is evidence rather than validation. Where a rule stops paying, drop it — and say why. Four tiers follow from the filter: **Law** where three or more sources agree; **Contested** where they split, in which case the deciding condition is stated rather than a verdict; **Advisory** where one source speaks; and **Amendment**, a rule ratified by the owner against or beyond the sources and cited as owner's authority — currently the three exceptions in Law 1 and the taxonomy in Law 13. Per-law source tallies are not recorded here; the tiers are asserted, not shown, and a reviewer should treat an untagged law's tier as claimed rather than proven.

## Governing principle

Software exists in time. Today's code is the environment in which tomorrow's changes must happen. The fundamental design question is therefore not "does this work?" but "what will this make the next change cost?"

## The AI corollary

AI does not repeal these laws; it changes the economics. When writing code was expensive, poor structure limited human productivity. When writing code is cheap, poor structure limits how much code humans and machines can safely produce at all. AI therefore raises the value of good boundaries, clear abstractions, shared vocabulary, fast feedback, external verification, strategic judgement and architectural coherence. The scarce resource is knowing what code should exist, where it should live, what must stay hidden, and whether the structure is still changeable. The tactical layer may be automated. The strategic layer must not be casually surrendered.

## Law 1: Changeability is the supreme criterion, with three bounded exceptions

A high-quality design makes future change cheaper, safer and more local. Correctness matters but is not the end of the story; a system correct today but resistant to modification is accumulating failure against the future. Judge a design by its behaviour under change: how many things must change, how much must be understood first, how much can go wrong unnoticed, how far one decision propagates.

This criterion is supreme, not merely default: it outranks every other design consideration except in the three bounded cases below. These are exceptions to be named and justified, not a general licence to trade changeability away.

**The frozen core.** Some components must be correct rather than changeable: money movement, authentication and authorisation, risk limits, kill switches, consensus paths, verified parsers, anything whose failure is unacceptable and whose change is rare. For these, correctness under adversarial input outranks changeability. Keep such cores small, isolated behind deep boundaries, and deliberately frozen, so the rest of the system stays changeable around them. Identify the frozen core before designing boundaries, not after: it determines where the boundaries go.

**The discount rate.** Changeability is an option and options carry cost. For deliberately disposable code — spikes, prototypes, end-of-life systems — the option expires worthless. Write it plainly and invest nothing in its structure. But mark it disposable: unmarked throwaway code becomes load-bearing, and then its structure is everyone's problem.

**The sealed measure.** Some rules exist to decide what counts as evidence: success criteria and thresholds, the unit a verdict is read in, a frozen parameter grid, the estimator behind an interval. These must resist change, and not for the frozen core's reason — the threat here is not an attacker or a rare catastrophic failure but the ordinary, well-meaning revision that happens to help. A measuring rule you may revise after seeing the number it produced has stopped measuring anything and started reporting your preference; changeability is precisely the property that lets you fool yourself, so here the cost of change is the point rather than a defect. This seals the declaration, not the code: the implementation that computes a metric stays as changeable as any module, while what the metric means and what it must clear does not. Nor does it forbid correction, because a measure can simply be wrong — change one by numbered amendment, recorded before results exist wherever possible; when it must land after them, it carries a justification that stands without reference to any observed number, and a consequence pre-committed before the re-run.

*These three exceptions are ratified amendments, not witnessed law. They carry the owner's authority, not the four sources'.*

## Law 2: Complexity is a liability paid by readers

Complexity is anything in the structure that makes it harder to understand or modify. Its worst forms: change amplification (one conceptual change touches many places), cognitive load (too much held in mind at once), unknown unknowns (cannot tell what a change might affect). Complexity belongs to whoever must understand the system next, not to whoever wrote it. Your own understanding is not evidence of simplicity.

## Law 3: Complexity cannot be destroyed, only managed

Every design decision places complexity somewhere. An abstraction simplifies callers and hardens its implementation; a cache removes runtime cost and adds invalidation; a boundary simplifies the API and concentrates machinery behind it. Never ask only "did we simplify this?" Ask "where did the complexity go, and who pays?" The goal is to place unavoidable complexity where its total cost is smallest.

## Law 4: Information belongs behind deep boundaries

The module is the primary unit of design. A good module provides substantial capability through a small interface and hides the decisions needed to implement it. Prefer depth over arbitrary smallness: five functions is not better than twenty. The strongest form is information hiding: organise modules around the decisions they can hide, not the sequence in which the program executes.

## Law 5: The interface is the design

The interface is what everyone must understand; the interior can change without teaching everyone. Strategic effort belongs disproportionately at the boundary: responsibilities, names, contracts, invariants, failure behaviour, dependencies, exposed information. In AI-assisted development, design the boundary deliberately and delegate the interior only once the boundary is understood and verifiable. The machine may write the implementation; it may not silently decide what the abstraction means.

## Law 6: Name the thing before you build the thing

A thing that cannot be named clearly has not been understood clearly. Vocabulary is architectural infrastructure. The same concept must not drift between "user", "account" and "member". Use one shared vocabulary across conversations, requirements, design docs, code, schemas, APIs, tests and agent instructions. A naming problem is often a design problem wearing linguistic clothing.

## Law 7: Requirements are discovered, not received

No requirement is sacred because it appeared in the spec. People rarely know exactly what they want before using a working system. The initial requirement is a hypothesis; development is learning. Consequence for AI-assisted work: regenerating the same system from the same spec is not progress. Without new information entering the loop, repeated generation reproduces the same misunderstanding faster.

## Law 8: Never outrun your feedback

The rate of reliable feedback sets the safe rate of change. Ten changes before learning whether the first was right is working in the dark. Shorten the loop or slow down. Tests, types, assertions, static analysis, linters, review, telemetry, domain experts, prototypes and real users are all mechanisms. The law is not "always use TDD". The law is "never let action outrun trustworthy feedback". TDD is one implementation, not the law.

## Law 9: Build in thin, end-to-end slices

When the system is uncertain, learn by building a narrow path through the real thing. A vertical slice gives feedback about actual integration rather than proving isolated layers work alone. The first slice is a tracer bullet: not the final product, but the test of direction. Big-bang integration delays the most important feedback until the most assumptions have accumulated.

## Law 10: Design continuously

Design is not a phase before implementation; it is continuous maintenance of the structure future work passes through. Small structural investments compound; so do small defects. The longer a structural problem stays, the more depends on it and the dearer correction becomes. Refactor early, improve continuously, and never invent a future cleanup phase. A system repeatedly told "we'll fix it later" is being designed toward decay.

## Law 11: Fix the generator, not the symptom

A recurring failure is evidence of a recurring cause. Descend: event → pattern → structure → mental model. Fixing the event may be necessary; it is not sufficient while the structure keeps producing it. Once deserves a patch; repeatedly deserves an architectural question. Applies equally to teams, processes, incentives and AI workflows.

*Tier: Law. The principle is witnessed by Ousterhout (strategic against tactical programming) and Hunt & Thomas (root-cause debugging, broken windows); the event → pattern → structure → mental model ladder is Swadia's vocabulary for it. Vocabulary does not carry a vote, and does not need one.*

## Law 12: Do not worship proxies

A measurement is not the thing measured. Once a proxy becomes a target, it gets optimised for its own sake. Coverage is not quality; class count is not modularity; function length is not simplicity; story points are not progress; lines of code are not productivity; passing tests are not good design; volume of AI-generated change is not throughput. This law applies to the other laws too: the moment "good design" becomes a quota, the philosophy has become what it warned against.

## Law 13: The method must fit the system

No universally correct method exists. First determine the kind of problem you are in. The four domains below are Cynefin, after Dave Snowden:

- **Clear**: cause and effect obvious. Use established procedures and checklists. Do not invent.
- **Complicated**: cause and effect exist but need analysis or expertise. Slow down, investigate, find the specialist. Do not mistake a knowledge problem for an iteration problem.
- **Complex**: cause and effect visible only in hindsight. Small experiments, observe, adapt, preserve reversibility. Do not pretend analysis can reveal what only experience can.
- **Chaotic**: cause and effect broken down. Stabilise first, understand later. Analysis paralysis is itself a failure here.

When the classification is uncertain, treat the domain as complex: probe, and preserve reversibility. Then keep watching. A system can drift from complicated to complex while the playbook stays cached, and the first sign is feedback that starts lying.

*Tier: Amendment. The taxonomy is Cynefin, Dave Snowden's, and it enters this document through one source. Under the rule that buried Law 14 — corroborated in spirit, voted on by none — that is Advisory, not Law. It is ratified as the gating step of the operating procedure on the owner's authority, and is cited as such.*

## The reconciliation on generality

One witness says make abstractions somewhat general because a good general abstraction hides complexity. Another says never design for imaginary futures. Both are right in different conditions. If the problem is complicated, the structure is discoverable now and deliberate generalisation prevents expensive leakage later. If the problem is complex, the future shape does not yet exist in knowable form and generalisation is speculation.

Rule: generalise early when consequences are discoverable by analysis; stay replaceable when consequences are visible only through experience. When uncertain, choose the option whose mistake is cheaper to reverse.

Expertise exception: in complicated domains a specialist can safely make more upfront decisions than a generalist, because their mental model is calibrated to the domain. Outside your expertise, prefer the reversible mistake.

Two guards stop this exception swallowing the rule. **Expertise is evidence, not confidence**: it means a demonstrated record of correct predictions in this domain. If you cannot point to the feedback that calibrated you, the exception does not apply to you — Law 8 applied to people. **The exception amplifies classification error**: an expert who mistakes a complex domain for a complicated one now commits early, with licence. When the classification itself is uncertain, the exception does not apply.

## What is deliberately not law

- **Module size**: no universal "smaller is better". Depth, cohesion, information hiding and reader cost are the criteria.
- **Function length**: no line count defines good design. Chasing short functions produces fragmented, shallow abstractions.
- **Strict TDD**: valuable technique, not universal law. Dangerous when passing tests become the objective rather than evidence.
- **Big-upfront design**: not in conflict with continuous design. Design enough boundary to avoid expensive mistakes; do not predict the unknowable.
- **Comments**: neither good nor bad in themselves. Useful when they carry intent, rationale, invariant, contract, non-obvious constraint or reason for a surprise. A comment that translates code into English is duplication.
- **Plain structure in code marked disposable**: Law 1's discount rate working, not failing. The judgement moves to whether it is marked. Unmarked throwaway code that has become load-bearing is the finding; its plainness is not.
- **A justified local deviation**: these laws are defaults, not commandments. A deviation explained in a comment carrying the reason beats blind obedience. Judge the reason, not the deviation. This is Law 12's final application.

This is the canonical list. `SKILL.md` and `review-mode.md` point here rather than restating it; change it in one place.

## The one-page constitution

Build for the next change, not merely the present state.
Treat complexity as a liability paid by future readers.
Hide complexity behind deep, deliberate boundaries.
Design the boundary; keep the interior replaceable.
Name concepts collectively before encoding them individually.
Treat requirements as hypotheses and development as learning.
Never outrun trustworthy feedback.
Build thin end-to-end slices before making large commitments.
Invest continuously in structure.
Fix the structures that generate recurring failures.
Never let a metric substitute for the thing it measures.
Choose methods according to the kind of system you are in.

A good design is one that makes the next correct change cheaper, safer and easier to understand.
