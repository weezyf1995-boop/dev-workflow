# Register of changes to the routing evals

The case list and pass rule in `cases.json` are a sealed measure. They were committed before the first run. Any later change to a case, a prompt, a marker, a forbidden command, a no-edit flag, the matching rules or the pass rule gets an entry here, with its date and reason, before the next run. A red case is a finding about the workflow, not a reason to change a case.

| Date | Change | Reason |
| --- | --- | --- |
| 2026-11-20 | Case list and pass rule sealed as written in issue #16, "Routing evals". | First version, committed before the baseline run. |
| 2026-11-25 | Baseline reset to the 2026-11-24 22:47 UTC run (9 green, 1 flaky, 0 red). Cases and pass rule unchanged. | Workflow commit 2e9b5e9 fixed the two red cases, and the session default moved to opus at high effort; later runs compare against this. |
