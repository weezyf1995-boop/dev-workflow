Spec review. Read-only: edit nothing in the repo, commit nothing.

Also read /tmp/spec-doctrine.md (the parent spec; only the decisions for this ticket apply) and /tmp/tk/rules.md (rules every ticket must hold).

You read the diff. Do NOT run ./check.sh, lint or builds. You may run one targeted check script, or a probe kept outside the worktree, only to prove a suspected bug.

Report: (a) requirements the ticket asked for that are missing or partial; (b) changes in the diff that were not asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Go through each acceptance criterion and say met / not met. Quote the spec line for each finding. Mark each finding Blocking or Advisory. End with one line: VERDICT: pass or VERDICT: fail. Under 300 words.
