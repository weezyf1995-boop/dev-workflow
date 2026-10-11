# The Philosophy of Changeable Software

## A Unified Design Philosophy Derived from Four Sources

*(Second revision: evidence rule made honest, taxonomy extracted, reversibility promoted, expertise guarded, structure bounded. Edits by Hermes; all unmarked text is the original author's.)*

*(Third revision: the Amendment tier named, disposable structure removed from the violation list, review mode recorded. Edits by Hermes.)*

*(Fourth revision, 2026-09-07: the Conway line removed from the Final Constitution, since Section V declined Law 14 and the one-page summary cannot carry a rule the document ruled out. Law 13 recorded as Amendment tier in the operating edition. Edits by Claude.)*

*(Fifth revision, 2026-09-07: installed as `references/philosophy-of-changeable-software.md` inside the operating skill — still the reference edition, still non-governing. Pointers updated for the third bounded exception, the sealed measure, ratified 2026-09-05 in the operating edition; the body deliberately does not carry it. Edits by Claude Code on the VPS.)*

***Edition note (2026-09-03, updated 2026-09-06):** this is the reference edition. The operating edition is the installed `changeable-software` skill (`/root/.claude/skills/changeable-software/`) — `SKILL.md` with `references/laws.md`, `testing-standard.md`, `review-checklist.md` and, since 2026-09-06, `review-mode.md`; since 2026-09-07 this file ships beside them as a non-governing reference. It now governs reviewing as well as building. Where this text and the installed skill disagree, the skill governs.*

---

## The governing principle

Software exists in time.

The code you write today is not the final object. It is the environment within which tomorrow's changes will have to occur. Therefore the fundamental question of software design is not:

"Does this work?"

It is:

"What will this make the next change cost?"

Everything else follows from this.

---

## I. The Rule of Evidence

Four sources inform this philosophy:

- John Ousterhout — software structure and complexity
- Andrew Hunt & David Thomas — pragmatic software practice
- Matt Pocock — software design in the age of AI-assisted development
- Sandeep Swadia — systems thinking and decision-making in complex systems

A proposition becomes Law when at least three sources support it.

A 2–2 disagreement is Contested.

A proposition supported by only one source is Advisory.

A proposition ratified by the owner against or beyond the sources is an **Amendment**. It carries the owner's authority, not the sources', and must be cited that way wherever it is used. In the operating edition these are the three exceptions in Law 1 — the frozen core, the discount rate and, since 2026-09-05, the sealed measure — and the taxonomy in Law 13. This reference edition's body carries the first two; the third lives in the operating edition, which governs.

*(Third revision: the fourth tier is named here because the second revision adopted Law 1's exceptions with no tier to hold them, which left owner's authority indistinguishable from witnessed agreement. The operating edition states all four tiers, and its review mode requires the tier to be cited with every finding.)*

Silence is not disagreement.

A dissent is not to be erased merely because the majority wins.

The purpose of this rule is not democracy. It is protection against synthesis by taste. A useful idea is not made universal merely because it sounds wise.

Two properties of this rule must be stated honestly.

**The sources are correlated.** Ousterhout, Hunt & Thomas, and Pocock descend from one school (Parnas, Brooks, information hiding); Swadia from another (systems thinking). A 3-of-4 majority can be a single school plus one follower. Treat the count as a signal of breadth, not a proof of independence.

**This rule is an axiom, not a theorem.** No source voted for the Rule of Evidence itself. It is taste with a procedure around it. The procedure does not eliminate taste; it makes taste visible, contestable, and reversible. This is Law 12 applied to this document: the moment "3 of 4" becomes the target rather than the signal, the rule has become the thing it guards against.

Adjacent thinkers may corroborate a law, explain it, or supply vocabulary for it, but they do not acquire a vote merely by being interesting.

---

## II. The Taxonomy of Problems

Before any law can be applied, the problem must be classified. There is no universally correct development method, because there is no single kind of problem.

**Clear.** Cause and effect are obvious. Use established procedures, checklists, and repeatable execution. Do not invent unnecessarily.

**Complicated.** Cause and effect exists but requires analysis or expertise. Slow down. Investigate. Find the right specialist. Do not mistake a knowledge problem for an iteration problem.

**Complex.** Cause and effect becomes visible only in hindsight. Prediction is limited. Use small experiments. Observe. Adapt. Preserve reversibility. Do not pretend that analysis can discover an answer that only experience can reveal.

**Chaotic.** The relationship between cause and effect has broken down. Stabilize first. Understand later. In chaos, analysis paralysis is itself a failure mode.

Classification is itself a judgment, and it can be wrong. When the classification is uncertain, behave as if the domain were more complex than it appears: probe, and preserve reversibility. Re-ask the question periodically, because systems drift between categories while playbooks stay cached.

---

## III. The AI Corollary

The laws in this document predate AI-assisted development. AI does not repeal them. It changes their economics.

When producing code was expensive, poor structure primarily constrained human productivity.

When producing code becomes cheap, poor structure becomes the constraint on how much code humans and machines can safely produce.

Therefore AI increases the value of:

- good boundaries
- clear abstractions
- shared vocabulary
- fast feedback
- external verification
- strategic engineering judgment
- architectural coherence

The scarce resource is no longer merely the ability to write code.

It is the ability to know what code should exist, where it should live, what must remain hidden, and whether the resulting structure is still changeable.

The tactical layer may be automated.

The strategic layer cannot be casually surrendered.

---

## IV. The Most Important Reconciliation

The sources appear to disagree about several things. Often they are not actually disagreeing about the underlying principle. They are operating in different conditions.

The classic example is generality.

One philosophy says: make abstractions somewhat general because a well-designed general-purpose abstraction can hide complexity. Another says: do not design for imaginary futures.

Both can be correct.

If a problem is complicated, the relevant structure may be discoverable now. Designing the abstraction deliberately can prevent expensive leakage later. If a problem is complex, the future shape of the problem does not yet exist in a knowable form. Premature generalization becomes speculation.

Therefore the governing rule is:

**Generalize early when the consequences are discoverable by analysis. Remain replaceable when the consequences are visible only through experience.**

**When uncertain, prefer the option whose mistake is cheaper to reverse.**

That is not compromise. It is applying the correct method to the correct kind of system.

This rule is load-bearing. Every law in Section V reduces to it. It appears again in the Final Constitution, because that is where it belongs.

### The Expertise Exception

This framework has a crucial corollary. In complicated domains, a domain specialist can safely make more upfront design decisions than a generalist. The expert's mental model is calibrated to the domain's structure; they can see the shape of the solution before the rest of us can.

Two guards keep this exception from swallowing the rule:

**Expertise is evidence, not confidence.** It means a demonstrated record of correct predictions in this domain. If you cannot point to the feedback that calibrated you, the exception does not apply to you. This is Law 8 applied to people.

**The exception amplifies classification error.** An expert who mistakes a complex domain for a complicated one now commits early, with license. When the classification itself is uncertain, the exception does not apply.

In AI-assisted development this exception describes the human's role precisely: the machine generates, and the calibrated mental model judges. As generated code becomes abundant, calibrated judgment becomes the scarce input. The exception is no longer exceptional. It is the job.

---

## V. The Laws

### Law 1 — Changeability Is the Default Criterion

*(Operating edition: "Changeability is the supreme criterion, with three bounded exceptions" — frozen core and discount rate ratified 2026-09-03, the sealed measure ratified 2026-09-05. Where the wording differs, the skill governs.)*

A high-quality design makes future change cheaper, safer, and more local.

Correctness matters, but correctness is not the end of the story. A system that is correct today but resistant to modification is accumulating failure against the future.

Judge a design by its behavior under change:

- How many things must change?
- How much must a developer understand before changing them?
- How much can go wrong without being noticed?
- How far does one decision propagate?

This criterion has two boundaries.

**The frozen core.** Some components must be correct rather than changeable: risk limits, consensus paths, verified parsers, anything whose failure is unacceptable and whose change is rare. For these, correctness under adversarial input outranks changeability. Keep such cores small, isolated behind deep boundaries, and deliberately frozen, so the rest of the system remains changeable around them.

**The discount rate.** Changeability is an option, and options have carrying costs. For deliberately disposable code (spikes, prototypes, end-of-life systems) the option expires worthless. Write such code plainly and invest nothing in its structure. But mark it disposable: unmarked throwaway code becomes load-bearing, and then its structure is everyone's problem.

*(Third revision: these two exceptions are Amendment tier — ratified, not witnessed. They carry the owner's authority, not the four sources'. See Section I.)*

The quality of today's implementation is subordinate to the quality of tomorrow's modification, except where tomorrow's modification is not supposed to happen.

### Law 2 — Complexity Is a Liability Paid by Readers

Complexity is anything in the structure of a system that makes it harder to understand or modify.

Its most dangerous forms are:

- **change amplification** — one conceptual change requires changes in many places;
- **cognitive load** — too much must be held in the mind simultaneously;
- **unknown unknowns** — the developer cannot even determine what a change might affect.

Complexity therefore belongs to the person who must understand the system next, not to the person who happens to have written it.

Your own understanding is not evidence that the design is simple.

A design is simple only when it is simple for the next person who must safely modify it.

### Law 3 — Complexity Cannot Be Destroyed; It Can Only Be Managed

Every design decision places complexity somewhere.

An abstraction may simplify its callers while making its implementation harder.

A cache may remove runtime cost while adding invalidation complexity.

A boundary may simplify the public API while concentrating difficult machinery behind it.

Therefore never ask merely:

"Did we simplify this?"

Ask:

"Where did the complexity go, and who now pays for it?"

The objective is not to make complexity disappear. The objective is to place unavoidable complexity where it has the smallest total cost.

### Law 4 — Information Belongs Behind Deep Boundaries

The primary unit of design is the module.

A good module provides substantial capability through a relatively small interface while hiding the decisions required to implement that capability.

The boundary should communicate what callers need to know.

The implementation should contain what callers do not need to know.

Prefer depth over arbitrary smallness.

A module is not good because it contains five functions rather than twenty.

A module is good when its interface hides substantial machinery and prevents implementation knowledge from leaking outward.

The strongest form of this law is information hiding: modules should be organized around the decisions they can hide, not merely around the sequence in which the program happens to execute.

### Law 5 — The Interface Is the Design

The interface is the part of a module that everyone must understand.

The interior is the part that can change without teaching everyone else about the change.

Therefore strategic design effort belongs disproportionately at the boundary:

- responsibilities
- names
- contracts
- invariants
- failure behavior
- dependencies
- information exposed

The interior remains important, but it is less expensive to replace when the boundary remains stable.

This is particularly important in AI-assisted development.

Design the boundary deliberately. Delegate the interior only after the boundary is understood and verifiable.

The machine may write the implementation.

It may not silently decide what the abstraction means.

### Law 6 — Name the Thing Before You Build the Thing

A thing that cannot be named clearly has probably not yet been understood clearly.

The system's vocabulary is architectural infrastructure.

The same concept should not casually become "user" in one place, "account" in another, and "member" somewhere else.

Use a shared vocabulary across:

- conversations
- requirements
- design documents
- code
- schemas
- APIs
- tests
- agent instructions

Naming is not cosmetic.

Naming exposes whether the people building the system have actually agreed on what the system contains.

A naming problem is often a design problem wearing linguistic clothing.

### Law 7 — Requirements Are Discovered, Not Received

No requirement should be treated as sacred merely because it appeared in the initial specification.

People frequently do not know exactly what they want before interacting with a working system.

The initial requirement is therefore a hypothesis.

Development is a learning process in which implementation, feedback, and conversation progressively reveal what the system should actually become.

This has a direct consequence for AI-assisted development:

regenerating the same system from the same specification is not inherently progress.

Without new information entering the loop, repeated generation can simply reproduce the same misunderstanding at greater speed.

### Law 8 — Never Outrun Your Feedback

The rate at which reliable feedback can be obtained sets the safe rate of change.

If an engineer can make ten changes before discovering whether the first one was correct, the engineer is effectively working in the dark.

Therefore:

shorten the feedback loop, or reduce the speed of change.

Tests are one mechanism.

Types are another.

Assertions, static analysis, linters, review, production telemetry, domain experts, prototypes, and real users are others.

The law is not:

"Always use TDD."

The law is:

"Never allow action to outrun trustworthy feedback."

TDD is one possible implementation of the law, not the law itself.

### Law 9 — Build in Thin, End-to-End Slices

When the system is uncertain, learn by building a narrow path through the real system.

A thin vertical slice provides feedback about the actual integration of the system rather than proving that isolated layers work independently.

The first useful slice is a tracer bullet.

It is not intended to be the final product.

It is intended to reveal whether the direction is correct.

A working vertical slice is therefore both implementation and experiment.

Big-bang integration is the opposite strategy: it delays the most important feedback until the largest number of assumptions have accumulated.

### Law 10 — Design Continuously

Design is not a phase preceding implementation.

Design is the continuous maintenance of the structure through which future work must pass.

Small structural investments compound.

Small defects compound too.

The longer a structural problem remains in the system, the more other decisions become dependent upon it, and the more expensive correction becomes.

Therefore:

refactor early, improve continuously, and never create a mythical future cleanup phase.

A system that is repeatedly told "we will fix this later" is being actively designed toward decay.

### Law 11 — Fix the Generator, Not the Symptom

A recurring failure is evidence of a recurring cause.

When the same problem appears repeatedly, descend one level:

event → pattern → structure → mental model

Fixing an individual event may be necessary.

It is not sufficient when the structure continues to generate the event.

A bug that occurs once may deserve a patch.

A bug that occurs repeatedly deserves an architectural question.

The same principle applies to teams, processes, incentives, AI workflows, and organizational systems.

### Law 12 — Do Not Worship Proxies

A measurement is not the thing being measured.

Once a proxy becomes a target, people and systems begin optimizing the proxy itself.

Therefore:

- code coverage is not quality;
- number of classes is not modularity;
- function length is not simplicity;
- story points are not progress;
- lines of code are not productivity;
- passing tests are not automatically good design;
- number of AI-generated changes is not engineering throughput.

Every measurable engineering practice is vulnerable to becoming a target that corrupts its original purpose.

Never confuse the scoreboard with the game.

This law applies to the other laws as well.

The moment "good design" becomes a rigid numerical quota, the philosophy has turned into the thing it warned you about.

### Law 13 — The Method Must Fit the System

There is no universally correct development method.

Before choosing how to solve a problem, determine what kind of problem it is, using the taxonomy in Section II.

Match method to kind: procedure for the clear, analysis for the complicated, experiment for the complex, stabilization for the chaotic.

Then keep watching. A system can drift from complicated to complex while the playbook stays cached, and the first sign is feedback that starts lying.

### Law 14 — Structure Follows Communication

*(Proposed as an Amendment — Section I — and declined. See editor's note below.)*

A system's structure will come to mirror the communication structure of the people and agents building it, whether or not anyone designs it that way.

Therefore design the communication structure deliberately:

- module boundaries follow ownership boundaries;
- every module has an owner who can say no to changes;
- a module without an owner decays, and shared ownership is usually no ownership.

This applies with extra force in AI-assisted development, where the team includes machines: the instructions, context, and feedback channels given to agents are communication structure, and the codebase will reflect their quality.

> **Editor's note:** this is Conway's law (1968). All four sources corroborate it in spirit; none of the four voted on it. Under this document's own Rule of Evidence it enters as Advisory. **Maintainer's ruling (2026-09-03): buried, not ratified.** It remains in this reference edition only as the record of a proposal that failed the document's own evidence bar. The operating edition (the installed `changeable-software` skill) never carried it. *(Third revision: now that Section I names the Amendment tier, this ruling reads exactly — the proposal asked for owner's ratification and did not get it, so it holds no tier above Advisory. The absent fourteenth law is the record of that refusal, not a gap between the two editions.)*

---

## VI. What Is Not Law

Several powerful ideas should deliberately remain outside the constitution.

**Module size.** There is no universal law that smaller modules are better. The relevant criterion is depth, cohesion, information hiding, and the cost imposed on readers.

**Function length.** No numerical line-count threshold defines good design. Shortness can improve readability, but blindly optimizing for short functions can produce fragmented, shallow abstractions.

**Strict TDD.** Tests and fast feedback are foundational. Test-first development is a valuable technique, but not a universal law. It becomes dangerous when passing tests becomes the design objective rather than a source of evidence.

**Big-Upfront Design.** There is no contradiction between continuous design and deliberate design of important abstractions. Design enough of the boundary to avoid expensive structural mistakes. Do not attempt to predict an unknowable future in its entirety.

**Comments.** Comments are neither inherently good nor inherently bad. A useful comment communicates something the code cannot adequately express: intent, rationale, invariant, contract, non-obvious constraint, reason for a surprising decision. A comment that merely translates the code into English is usually a symptom of duplication.

**Plain structure in code marked disposable.** *(Third revision.)* Code that is deliberately disposable and written plainly is Law 1's discount rate working, not a design failure. The judgment moves to whether it is marked. Unmarked throwaway code that has become load-bearing is the finding; its plainness is not.

**Consistency with this document.** These laws are default settings, not commandments. A justified local violation, explained in a comment (see above), beats blind obedience. This is Law 12's final application.

---

## VII. The Operating Doctrine

The philosophy can be reduced to a sequence.

Before changing the system, ask:

1. **What kind of system/problem is this?** Clear, complicated, complex, or chaotic? (Section II.) Is this a frozen core?
2. **What is the real concept?** Can everyone name it the same way?
3. **What will the next change cost?** Where will change amplify?
4. **Where did the complexity go, and who now pays for it?** And then: where should it live? What must be visible, and what can be hidden?
5. **What belongs at the boundary?** What must the caller know?
6. **Who pays for the complexity here, and who can say no to changes?**
7. **What alternative design exists?** Have we actually considered a genuinely different structure?
8. **What is the smallest useful step?** Can we learn something before committing to more?
9. **What independent feedback will tell us whether we are wrong?** Compile, test, inspect, measure, prototype, ask a user, consult an expert, observe production.
10. **What structural problem is generating today's problem?** Do not merely patch a recurring symptom.
11. **What will we improve before we leave?** Never leave the structure strictly worse than you found it.

**Building and reviewing are the same doctrine addressed to different audiences.** *(Third revision.)* The operating edition splits them accordingly. `review-checklist.md` holds the questions you answer for yourself before declaring your own work done. `review-mode.md` holds the procedure for judging something that already exists — a pull request, an architecture, someone else's module, a pile of generated code — and it produces a report another person has to act on.

Four constraints keep that report honest. No finding without a law: an observation that traces to no numbered law is a preference, and must be dropped or labelled one. Every finding cites its tier, Amendment included. Contested ground is reported as the condition that decides it, never as a verdict. And the procedure opens by asking whether the code is frozen core or marked disposable, because a changeability finding inside a frozen core is a category error and a structural finding against marked-disposable code is Law 1 misread. Section VI is the list the review may not flag.

---

## VIII. The Final Constitution

If the entire philosophy had to fit on one page, it would read:

Build for the next change, not merely the present state.

Freeze the rare core that must be correct rather than changeable.

Treat complexity as a liability paid by future readers.

Hide complexity behind deep, deliberate boundaries.

Design the boundary; keep the interior replaceable.

Name concepts collectively before encoding them individually.

Treat requirements as hypotheses and development as learning.

Never outrun trustworthy feedback.

Build thin end-to-end slices before making large commitments.

Invest continuously in structure.

Fix the structures that generate recurring failures.

Never let a metric become a substitute for the thing it measures.

Choose methods according to the kind of system you are actually operating in.

When uncertain, prefer the change whose mistake is cheaper to undo.

And above all:

**A good design is one that makes the next correct change cheaper, safer, and easier to understand.**
