---
id: research
description: "Answer the dispatcher's seeded question with sourced, grounded findings; label the unverifiable unverified"
---

<task-goal>
Answer the seeded question with findings grounded in named sources, labeling every unverifiable claim unverified.
</task-goal>

<scope>
- **Read:** the seed's named sources and the open web (through the browse capability).
- **Write:** none — the findings return to the dispatcher; nothing lands on disk.
</scope>

<done-contract>
Done criteria — all must hold:

- Every claim in the returned findings carries a source precise enough for the dispatcher to check, or the label unverified.
- The seeded question is answered, or reported unanswerable together with the searches run.
- The findings return to the dispatcher and to nothing else.

Outcome map:

- **Complete** → the dispatcher folds the findings in; the dispatch ends with the return.
- **Nothing found** → return the null result with the searches run — a complete return, not a failure. Feedback schema: the searches run and each one's empty outcome.
- **A source contradicts the seed's premise** → return the contradiction, sourced; never silently adopt the premise. Feedback schema: the premise, the contradicting claim, its source.
</done-contract>
