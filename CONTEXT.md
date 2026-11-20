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

**Mechanism**:
A check that fails the suite or the server whoever acts and on whichever machine.
_Avoid_: Gate, guard, enforcement hook

**Frozen core**:
A component whose failure is unacceptable and whose change is rare, where correctness outranks changeability.
_Avoid_: Critical path, protected file
