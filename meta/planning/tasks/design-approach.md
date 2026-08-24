---
id: design-approach
description: "Produce the design — one approach plus the full milestone list with per-milestone done-criteria"
---

<task-goal>
Produce the design for the seeded goal: one approach and the full milestone list, each milestone carrying falsifiable done-criteria.
</task-goal>

<scope>
- **Read:** `planning/facts-brief.md` and every artifact it names.
- **Write:** `planning/design.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/design.md` exists and its first line is exactly `DESIGN`.
- The body names one approach and a full milestone list; every milestone has an id, an aim, and done-criteria that name an observable, a probe, and a threshold.
- No milestone is omitted for "later"; no `planning-mode` stamp; no per-milestone wall-clock field.
- An `input-gaps` list is present (may be empty).
- Completeness: every actor the brief names is served by at least one milestone or an explicit out-of-scope line; every brief constraint has a home or an input-gap; failure of a milestone is defined in its done-criteria; two milestones with the same id is a fail; a milestone whose input is in neither the brief nor an earlier milestone is a fail.

Outcome map:

- **Complete** → the design seeds draft.
- **Markerless or thin facts brief** → repair forward, log the gap, complete. Never reject. Never re-enter understand.
</done-contract>
