## Observed
The symptom as measured: what, where (component/function), when, by whom/which goal. Deployed-vs-HEAD when they differ. Prose with evidence inline. NEVER a file list. NEVER a one-line restatement of the title.

## Mechanism
What the code actually did, and why that produced the symptom. NOT the symptom again.

## Attempts
Every earlier fix or trial of THIS problem: what it changed, when (commit), and WHY it did not hold. If nothing was tried before: `First attempt held — checked: <commits/docs you looked at>`. The phrase `none recorded` is FORBIDDEN.

## Fix
What was built, and WHY this design rather than the alternatives (ruling served, trade-off taken, what was rejected). NEVER a file list.

## Consequences
What the fix changed elsewhere: what it deleted or replaced, regressions or new bugs, follow-up fixes (cite later commits/entries).

## Verification
How it was proven (probe/selftest by name, inline) and when it was deployed.

## ATTENTION
1–5 bullets. Each names a trap and why it is a trap. Each self-contained. No duplicates of each other or of the header.
