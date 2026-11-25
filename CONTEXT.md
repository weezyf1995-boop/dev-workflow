# Dev workflow

The coding workflow and the `changeable-software` doctrine it runs on: which skill fires when, how tickets are built and landed, and how the rules are enforced.

## Language

### Enforcement

**Declaration**:
A rule that exists only as prose an agent is asked to follow.
_Avoid_: Policy, guideline

**Tripwire**:
A local check that stops an honest mistake at the moment of action but can be bypassed.
_Avoid_: Guard, gate, sandbox

**Suite tripwire**:
The tripwire that runs a repository's own checks, named in `.claude/checks.json`, at three moments: after an edit, when a builder subagent stops, and when the session stops after a landing.
_Avoid_: Test hook, suite gate, CI

**Mechanism**:
A check that fails the suite or the server whoever acts and on whichever machine.
_Avoid_: Gate, guard, enforcement hook

**Frozen core**:
A component whose failure is unacceptable and whose change is rare, where correctness outranks changeability.
_Avoid_: Critical path, protected file

### Routing evals

**Floor**:
Per routing eval case, the worst pass count across three full runs, held in `evals/results/baseline.txt`.
_Avoid_: Threshold, pass mark, target

**Regression**:
A red case (no run passes), or a case two or more runs below its floor.
_Avoid_: Failure, flake, drop
