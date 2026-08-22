---
id: review-goal-completeness
description: "Try to fail the ratified definition of done on completeness — missing actors, unstated inputs, undefined failure behaviour, implicit assumptions, uncovered edges — and close every gap the owner ratifies"
---

<task-goal>
Drive the ratified `goal.md` from falsifiable to COMPLETE: every gap of the five completeness lenses either closed by a new criterion in the definition of done, or shown empty in a per-lens account.
</task-goal>

<scope>
- **Read:** `goal.md` in the goal folder and every artifact it names; the owner's answers on the goal's owner-channel thread; the returns of the cataloged `researcher` and `diagnoser` sub-agents.
- **Write:** `goal.md` in the goal folder (additions only) and appends to the goal's five write-if-something ledgers.
</scope>

<done-contract>
Kill criteria — the completeness lenses; any hit is a gap that must be closed or disclosed:
- An actor who acts, is acted on, or must be notified, and whom no criterion names or scores.
- A datum the work consumes whose source, shape, or absence-behaviour the definition of done does not state.
- A criterion with no defined behaviour for the case where it is NOT met.
- A noun or verb the goal takes on faith — an assumption stated nowhere and tested nowhere.
- An edge the happy path hides: two of a thing inside one window, an item present in neither source, a duplicate, an empty set, a boundary value, a repeat run over the same input.

Done when, checkable at the edge:
- `goal.md` carries every ratified addition inside its definition of done, each naming an observable, the probe that checks it, and its threshold; and its ratification record carries the owner's ratifying answer for each.
- Every criterion present before this task ran is present, unweakened and unreworded; the goal statement and the `use-case:` field are byte-unchanged.
- The closing account names all five lenses, each either with the criteria it produced or with what was checked and found empty.
- Any criterion added without an owner ratification is marked in `goal.md` as derived-and-unratified with its derivation, and the derivation is recorded in the goal's `decisions.md`.

Outcome map:
- Every lens closed or shown empty → completion; the extended `goal.md` seeds the split step.
- **Owner answers pending** → the task WAITS LOUDLY: the asks and drafted criteria parked on the coordination bus addressed to the reserved `owner` token — a disclosed waiting state, never a silent stall. Feedback schema: each queued ask paired with the lens and the gap it closes.
- **Goal runs autonomously, or the parked ask cannot be answered** → derive each open criterion from the goal's own artifacts, write it into `goal.md` marked derived-and-unratified, record the derivation in `decisions.md` and each unclosable gap in `doubts.md`, and complete. Feedback schema: {lens, gap, derivation, provenance}.
- `goal.md` missing, unratified, or unreadable → FAIL-BLOCKED naming the missing artifact; feedback schema {expected-path, expected-producer}.
</done-contract>
