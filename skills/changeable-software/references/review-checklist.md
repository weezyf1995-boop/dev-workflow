# Review Checklist

Run before any PR, merge, commit to main, or telling the user the work is done. Answer the questions; do not tick them. Where an answer is bad, fix it or record it in the PR description with the reason.

Scale to the change. The **Always** block is short enough that there is no excuse for skipping it on a one-line fix. The rest applies to full-path changes — new boundaries, anything spanning files, and anything touching money, auth, external APIs or data you cannot regenerate, regardless of size.

## Always (every change, no exceptions)

1. **Does the feedback actually pass, and does it exercise the behaviour this change affects — not merely that the code builds?** Suite green, deterministically, and actually run, not assumed.
2. **What would this break that I haven't looked at?** Name the blast radius, or say why there isn't one.
3. **Is the structure better, equal, or worse than I found it?** If worse anywhere, is the debt named with a reason?
4. **If this fixes a bug, did a test reproduce it and fail before the fix?** If not, write it now. This applies on the light path; most bug fixes are light-path and this is where the rule would otherwise be skipped.

## Full-path changes

### Changeability

- Name one likely next change and trace what it would touch. What does this make that cost?
- Where would a single conceptual change now require edits in more than one place? Is that acceptable, and why?
- How much must the next person understand before they can safely modify this? Could that be less?

### Complexity placement

- Where did the complexity go — callers, implementation, or operations?
- Is there anything the next reader could not discover without reading the interior? Is it stated at the boundary, or in a comment carrying intent?

### Boundaries and vocabulary

- Does every module touched hide real machinery behind a small interface, or has implementation knowledge leaked into callers?
- Do names in code, schema, tests and docs match the vocabulary from step 2, with no synonyms introduced?
- Is failure behaviour defined and tested at each boundary?

### Feedback

- Where was action allowed to outrun trustworthy feedback, and what did that cost?
- Does the change meet `testing-standard.md` § "What professionally tested means"?

### Requirements

- Did building this reveal the original requirement was wrong or incomplete? Was that surfaced to the user, or quietly worked around?
- Is any of this regeneration of the same thing from the same spec, with no new information?

### Structure

- Has this problem occurred before? If so, was the generator addressed or only the event?
- Was any "we'll clean this up later" left in? Do it now, or write down the concrete trigger for doing it.
- Is everything this change classified — new vocabulary, frozen cores, disposable marks, named debt — recorded in the project's `CLAUDE.md` design section, and marked in the code where the skill says to mark it?

### Proxies

- Was anything done to satisfy a number — coverage, function length, file count, test count — rather than a purpose? Remove it.

## Closing question

What did we improve before leaving?
