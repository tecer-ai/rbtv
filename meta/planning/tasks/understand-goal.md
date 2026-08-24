---
id: understand-goal
description: "Produce the facts brief — restated goal, constraints, salvage inventory, credentials/preferences"
---

<task-goal>
Produce a facts brief the later stages can plan from: the seeded goal restated, its constraints, the salvage inventory, and the credentials/preferences inventory.
</task-goal>

<scope>
- **Read:** the goal seed and every artifact it names; any on-disk salvage those paths point at; owner replies on the goal channel.
- **Write:** `planning/facts-brief.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/facts-brief.md` exists and its first line is exactly `FACTS-BRIEF` (existence without the marker is a non-report).
- The body has four named inventories: goal restated; constraints; salvage (path + what it still proves, or an explicit none); credentials/preferences (names only, or an explicit none).
- An `input-gaps` list is present (may be empty) naming every repaired inadequacy and its assumption.
- No credential *value*, owner-specific host, or vault path appears in the file.
- Completeness: every actor the seed names is in the restatement or the constraints; every input the seed consumes has a source or an input-gap; failure-to-understand is logged not rejected; two salvage items for one path are collapsed to one; a thing present in neither seed nor disk is not invented.

Outcome map:

- **Complete** → the facts brief seeds design.
- **Inadequate seed** → repair forward, log the gap, complete. Never reject. Never re-enter.
- **Owner answers pending (interactive)** → fold what arrived; remaining parked asks do not block completion under default-and-disclose. Feedback schema: each parked question paired with the inventory field it would have filled.
</done-contract>
