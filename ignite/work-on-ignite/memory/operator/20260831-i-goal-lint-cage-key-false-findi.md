# 20260831-i-goal-lint-cage-key-false-findi — goal lint: cage-key false findings + spawn-masked dir test

kind: issue
component: operator
date: 2026-08-31
commit: 6da3e3b0c03957dd41a2523672b7de7220feeb7c
deployed: no
pin: operator/goals-tree/probes/probe-goal-lint-cage.py
register-id: redesign-continue-1#125

## Observed

`rbtv-goal lint` could never return exit 0 for a goal carrying a materialized goal-master
seat. Two register filings (`.rbtv/goals/_archive/ignite-engine/register/open/
G-plan-planner-0822-1711-3`, `G-leader-0822-2351`), grouped by owner-ruled triage
2026-08-23. On `ignite-engine`'s `seats/goal-master/seat.md`, lint reported three false
"no assembled block in the body" findings for `master`, `1-projects`, `2-areas` — the
`relays:`/`rw-paths:` VALUES of a materialized master seat, not cognitive-unit references.
Separately, the "taskforce row resolves to a real seat" criterion is a
`Path.is_dir()` test against `seats/<seat>`; at spawn time `seats/` is masked (tmpfs +
one bind, `envelope/cagespec.py`) to hold only the occupant's own folder, so a
caged seat evaluating this criterion sees every OTHER row's folder as "absent" and can
never pass. `plan-3-plan-binder`, whose done-contract requires a clean lint, ended
`incomplete` at 23:42 and was relaunched at 23:43 on the ~300s reconcile loop —
measured in `G-leader-0822-2351` before a hand-made leader ruling broke the cycle.

## Mechanism

HALF ONE: `LINT_NON_REF_KEYS` (`goal_cli.py`, the frontmatter-reference walker's exclusion
list) omitted `relays`, `rw-paths`, `cage-grants`, `goal-writes`, `exposes`,
`exposed-clis`, `cli-write-roots` — every cage-grant/exposure key a materialized master or
staff seat carries. The walker treats any string/list frontmatter value matching the
bare-unit-id grammar as a reference to resolve against the assembled body; `relays:
master` and `rw-paths: [1-projects, 2-areas]` matched that grammar and had no
`id="…"` block to resolve against, since they were never references.

HALF TWO: the per-row loop in `lint_goal` did `seat_dir = seats_dir / seat; if not
seat_dir.is_dir(): f.add("taskforce row resolves to a real seat", …); continue`. From
inside a cage, `seats_dir.is_dir()` is true but its `iterdir()`/subpath resolution for any
seat other than the occupant is empty by construction — the sandbox, not a materialize
defect, is what makes the folder look absent. The check could not distinguish "genuinely
missing" from "masked by the cage it is running in".

## Attempts

First attempt held — checked: both register filings' own stated remedies (which this fix
implements verbatim for HALF ONE, and the "drop or resolve" fork for HALF TWO), and
`materialize-seats.py`'s SC-8 selftest control (the write-order proof HALF TWO's removal
relies on) — no prior commit had acted on either filing.

## Fix

HALF ONE: added the seven cage-grant keys to `LINT_NON_REF_KEYS`, per the filing's own
named remedy ("skip the cage keys entirely").

HALF TWO: removed the `f.add("taskforce row resolves to a real seat", …)` finding (kept
the `continue`, so a row whose folder isn't visible still skips deeper — also
cage-blocked — validation silently rather than reporting a spurious defect). Chose REMOVAL
over "resolve through the engine's resolver": traced both candidate resolvers
(`supervisor/launch.py#registered_seats` — docstring states "Folder presence is not
consulted" — and `coord/messages.py#known_recipients`'s `registered_seats` call) and found
neither one ever checks the seat FOLDER either; they are built FROM `taskforce.csv` rows,
so routing through them would be a checked-looking no-op, not a stronger guarantee.
What actually backs "a row names a real seat" now: `materialize-seats.py` writes the seat
descriptor FOLDER (step 1) strictly BEFORE it appends the registry ROW (step 2) — proven
by its own SC-8 selftest control (abort before step 1 leaves nothing on disk; abort
between step 1 and the append leaves an ORPHAN FOLDER with no row, never the reverse).
The forward direction (row → folder) is therefore a write-time invariant, not something a
caged reader can or needs to re-verify. The mirror direction (folder → row, an actual
half-materialize) stays covered by lint's existing § 5 orphan-folder walk, which degrades
safely when caged: it only visits folders `seats_dir.iterdir()` actually yields.

## Consequences

HALF TWO removes lint's only defense against a hand-corrupted `taskforce.csv` naming a
seat whose folder was deleted after a normal materialize (not a materialize-time defect,
an out-of-band corruption). No known live case has ever hit this; the write-order
guarantee covers every state materialize itself can produce. Nothing else read the removed
finding's check-name (`"taskforce row resolves to a real seat"`) — grepped clean.

## Verification

New probe `operator/goals-tree/probes/probe-goal-lint-cage.py`: a real `bwrap` cage
(`--tmpfs seats/ --bind seats/<occupant> seats/<occupant>`, the exact shape
`cagespec.py` documents) around a two-seat fixture goal (goal-master + a worker whose
folder the cage hides). 4 checks: uncaged lint exits 0 with no findings, uncaged lint
carries no "taskforce row resolves to a real seat" finding, a control proving `ls seats/`
inside the cage sees only the occupant, and caged lint STILL exits 0. Run through
`node ignite/deploy/probe-suite.js --only goal-lint-cage` — PASS. Red-first: reverting
each fix hunk separately (LINT_NON_REF_KEYS additions; the finding removal) in the live
tree reproduced, respectively, the exact three false findings named in the filing and the
exact caged-only "taskforce row resolves to a real seat" failure — both restored to green
after re-applying. Not yet deployed — `READY-TO-DEPLOY` in the closing report.

## ATTENTION

- `LINT_NON_REF_KEYS` is the ONE place cage-grant keys are excluded — a future
  cage-grant/exposure key added to the seat schema (a materialize change) must be added
  here in the SAME act, or it silently reopens HALF ONE for every seat that carries it.
- The removed "taskforce row resolves to a real seat" check must NOT be reintroduced as a
  bare `Path.is_dir()` test — that is exactly the defect. If a stronger guarantee is ever
  wanted, it has to come from something that does not require `seats/` visibility (a
  manifest file, a registry row, an engine resolver that is verified to skip the folder
  check — not assumed to).
- § 5 (orphan-folder-without-row) is NOT touched by this fix and still runs uncaged-only
  in practice — it degrades safely (never false-positives) when caged, but it also
  verifies nothing extra in that case. That asymmetry is intentional, not an oversight.
