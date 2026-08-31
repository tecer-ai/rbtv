---
id: build-pieces
description: "Build every piece the seeded forge spec enumerates, land each at its declared target path with exactly the registration acts the spec decided, and account for all of them in the build ledger"
---

<task-goal>
Deliver every artifact the seeded spec orders, built at its declared target path and registered exactly as that spec decided.
</task-goal>

<scope>
- **Read:** the seeded `forge-spec.md`; the authoring and exposure law in the guides named in this task's Guides bullet; every component the spec's target paths touch; the run-time configuration under this component's module configuration folder.
- **Write:** the target paths the spec names — a CLI piece's is its owning component's `capabilities/<name>/tool/` like any other piece's; the registration surfaces its exposure decisions name — `exposure.csv`, `seats.csv`, workflow manifests, prompt frontmatter — in the touched components; `./forge-build.md` in the goal folder.
- **Guides — read whole before writing:** `references/authoring-style.md`; `references/exposure.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `forge-build.md` exists in the goal folder and its first line reads exactly `build: COMPLETE`, `build: PARTIAL`, or `build: ESCALATED`. (The file may exist EMPTY from spawn — existence is not the artifact; the status line is.)
- On `build: ESCALATED`: that line is the whole record, and no component artifact was written.
- Otherwise the ledger carries exactly one row per spec piece, keyed by piece-id: the row count equals the spec's piece count and every spec piece-id appears.
- Every row the ledger marks built names a file that EXISTS at that row's declared target path.
- Every exposure decision the spec recorded appears on its piece's row as an applied registration act, and no registration act appears on any row that the spec did not decide.
- `component-lint` over every touched component returns exactly the pre-build baseline finding set the ledger records — zero new findings — and the ledger carries both that baseline and the final result.
- `build: COMPLETE` holds only where every spec piece is built; one unbuilt piece makes the line `build: PARTIAL` and that piece's row carries the reason it was not built.
- No file outside the spec's target paths, the named registration surfaces, and the goal folder was created, edited, moved, or deleted.

Outcome map:

- **`build: COMPLETE`** → the judging seat tries every piece against the spec.
- **`build: PARTIAL`** → the judging seat tries the run and fails every unbuilt piece as a coverage gap. Feedback schema: per unbuilt piece — {piece-id, what blocked it, what would unblock it}.
- **`build: ESCALATED`** → the run closed at intake; nothing was built and nothing is tried.
- **A CLI piece whose owning component cannot be resolved** → that piece is a coverage gap and the line reads `build: PARTIAL`; nothing is written to a guessed path. Feedback schema: {piece-id, the unresolved destination, the ambiguity}.
- **A new lint finding that cannot be cleared** → the line reads `build: PARTIAL` and the ledger quotes the finding. Feedback schema: {component, check id, the finding text, what was tried}.
</done-contract>
