# Testing Standard

Tests exist to keep action from outrunning trustworthy feedback (Law 8). They are one feedback mechanism among several; types, linters, assertions, static analysis and real-world runs are others. Use the cheapest mechanism that gives trustworthy feedback for the risk in question. Reach for a test when nothing cheaper will catch the mistake.

Passing tests are not good design (Law 12). Coverage is not a target. The question for every test is: what mistake would this catch, and would it catch it before the mistake spread?

## Which tests, for what

Match the test to the boundary and the risk. Do not write every kind of test for every change.

| Test | Pins | Write when | Avoid when |
|---|---|---|---|
| Unit | One module's interface contract | The module has real logic, edge cases, or invariants worth stating | It only wires other things together, or the test would just restate the implementation |
| Contract / integration | The agreement between two of your own modules, or between you and an external system | A boundary was designed in the planning step; an external API, DB, queue or file format is involved | The boundary is trivial passthrough |
| End-to-end (tracer) | The whole path from input to output | Every new vertical slice; every bug fixed in production | As the only layer of tests (too slow, too coarse to localise failure) |
| Property / fuzz | Invariants over many inputs | Parsers, serialisers, calculations, anything with an algebraic law (roundtrip, idempotence, ordering) | Behaviour has no stateable invariant |
| Regression | A specific bug never returns | Every bug that reached a user or CI | Never avoid; but ask Law 11 first, and fix the generator too |
| Smoke | The system starts and its main path works | Anything deployed | Never avoid for deployed systems |

## Rules

**Test the boundary, not the interior.** Tests assert on the interface designed in planning: inputs, outputs, side effects, failure behaviour. They do not reach into private state or assert call sequences of internal collaborators. A test that breaks when the interior is refactored without any change to behaviour is a bad test; it turns the interior into interface and raises the cost of the next change.

**The first test is the tracer bullet.** For any new slice, the first thing that runs is one end-to-end test through the real path, however thin. It fails, the slice is built until it passes, then unit and contract tests are added where risk lives. This gives integration feedback before layer feedback.

**Test failure behaviour explicitly.** For each boundary, at least one test for what happens on bad input, missing dependency, timeout, or partial failure. Undefined failure behaviour is the leading source of unknown unknowns.

**Name tests in the shared vocabulary.** Test names use the concepts named in planning and describe behaviour, not implementation: `rejects_booking_outside_venue_hours`, not `test_validate_2`. Reading the test names for a module should read as its specification.

**One reason to fail per test.** A test that checks five things reports one failure and hides four. Split them.

**Deterministic or deleted.** A flaky test is worse than no test: it trains everyone to ignore red. When a test flakes, apply Law 11: find the structure that makes it nondeterministic (shared state, real clock, real network, ordering assumption) and fix that. Do not add retries.

**External systems get a fake at the boundary and a contract test against the real thing.** Unit and most integration tests run against a fake that honours the same interface. One separate contract test (may be slow, may be skipped offline, may run only in CI) confirms the fake still matches reality. When the real system changes behaviour, the contract test is what catches it.

**Fixtures are minimal and named.** A fixture is a named example of a domain concept (`a_paid_invoice`, `an_expired_session`), not a dump of every field. Large anonymous fixtures hide which fields the test actually depends on.

**Every bug gets a test before the fix.** Reproduce it, watch it fail, fix it, watch it pass. Then ask what structure let the bug in and whether that needs a test or a redesign.

**Tests are code and pay Law 2.** Duplicate setup, unclear assertions and clever helpers cost the next reader. Keep test code as readable as production code; do not let it become the place where standards drop.

## Feedback beyond tests

Before writing a test, check whether something cheaper already gives the feedback:

- **Types**: encode invariants in types where the language allows. A state that cannot be represented needs no test for its absence.
- **Assertions**: for invariants inside the interior, an assertion at the point of assumption is cheaper and closer to the fault than a test.
- **Linters and static analysis**: configured once, they catch whole classes of mistakes on every change with no test to maintain.
- **Running the real thing**: for a thin slice or a script, running it against real input is frequently the fastest trustworthy feedback available. Do it before writing tests for it.
- **A domain expert or the user**: for complicated and complex problems, the only feedback that reveals whether the requirement itself was right. Tests cannot provide this.

## What "professionally tested" means for a change

Before calling a change done, the following are true:

1. The main path has at least one end-to-end test.
2. Every boundary designed in planning has its contract tested, including failure behaviour.
3. Every module with real logic has unit tests at its interface, named in the domain vocabulary.
4. Every bug fixed in this change has a regression test that failed before the fix.
5. The full suite passes, deterministically, and runs fast enough that it is actually run before every commit. If it is too slow to run, that is a structural problem to fix, not a reason to skip it.
6. No test asserts on implementation detail that a behaviour-preserving refactor would break.
7. Nothing was written to raise a coverage number. Every test can name the mistake it catches.
