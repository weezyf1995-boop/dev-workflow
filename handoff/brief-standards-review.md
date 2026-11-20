Standards review. Read-only: edit nothing in the repo, commit nothing.

Standards sources (read them):
1. /root/.claude/skills/synced/13c631e7-98a2-4935-b13f-44302eec917a_83b0702a-6e1d-4577-b53e-15699e0ee127/changeable-software/references/review-checklist.md
2. The surrounding text of each edited file in the worktree: additions should match the form, density, vocabulary, spelling (British) and notation of the text beside them, including the skill's Amendment notes.
3. /tmp/tk/smells.md (the smell baseline; judgement calls only; most will not apply to prose).
4. /tmp/tk/rules.md (rules every ticket must hold).
5. CONTEXT.md at the worktree root (vocabulary).

You read the diff. Do NOT run ./check.sh, lint or builds: the builder ran them and the coordinator runs them on the landing commit. You may run one targeted check script, or a probe kept outside the worktree, only to prove a suspected bug.

Report: (a) every place the diff violates a documented standard or a rule in /tmp/tk/rules.md, citing it; (b) any baseline smell or inconsistency with the surrounding text (a claim the rest of the file contradicts, vocabulary drift, broken notation). Separate hard violations from judgement calls. Mark each finding Blocking or Advisory. End with one line: VERDICT: pass or VERDICT: fail. Under 300 words.
