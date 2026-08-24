---
id: gap-understand
description: "Produce the gap brief for a failed milestone — the gate verdict, what execution actually produced, and whether the gap stays inside that milestone"
---

<task-goal>
Produce one combined gap brief for the seeded failed milestone: what the gate verdict said, what
execution actually produced against the milestone's unchanged done contract, the gap between the
two, and the boundary call — does the gap stay inside this milestone, or does it cross into
another. That boundary call is the routing fact the patch stage acts on, so it is stated
explicitly, never left to be inferred.
</task-goal>

<scope>
- **Read:** the gate verdict for the seeded milestone; that milestone's done contract, as written
  and unchanged; that milestone's plan and its seats; every artifact those seats declared, at its
  declared path; the seats' endings, progress notes and side-effect journals; the goal's compiled
  permission envelope; owner replies on the goal channel.
- **Write:** `planning/replan/gap-brief.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/replan/gap-brief.md` exists and its first line is exactly `GAP-BRIEF` (existence
  without the marker is a non-report — a declared path is created empty at spawn).
- The body names the seeded milestone id, and quotes its done contract VERBATIM as the contract
  the patch will be checked against. The contract is transcribed, never restated, never trimmed,
  never improved.
- The body has four named parts: (a) the gate verdict — every failed clause, as the judge wrote
  it; (b) what execution produced — per declared output, the path, whether it exists, whether it
  carries its marker, and what it proves; (c) the gap — each failed clause paired with the
  evidence that it is unmet, or with an explicit "verdict unsupported by the artifacts" where the
  artifacts contradict the verdict; (d) the salvage inventory — every produced artifact a patch
  may reuse rather than re-derive.
- The body carries an explicit boundary call in one of exactly two words: `contained` (every
  failed clause is closable by changing only this milestone's plan or seats) or `cross-milestone`
  (closing any failed clause requires a change to another milestone's plan, seats, done contract,
  or to the permission envelope). Where the call is `cross-milestone`, the crossing is named:
  which other milestone or which envelope grant, and which clause forces it.
- The body proposes no patch, no seat, no edge and no grant. This task diagnoses; it does not plan.
- An `input-gaps` list is present (may be empty) naming every inadequacy repaired here and the
  assumption taken.
- No credential *value*, owner-specific channel, host, account, or vault path appears in the file.
- Completeness: every clause of the done contract appears in the gap section with a verdict of met
  or unmet; every declared output of every seat in the milestone is accounted for as present,
  absent, or markerless; a clause the verdict never judged is reported as unjudged rather than
  assumed met; two seats producing the same declared path are reported as one collision, not two
  artifacts; an artifact present in neither the verdict nor on disk is not invented.

Outcome map:

- **Complete, `contained`** → the gap brief seeds the patch stage, which may patch.
- **Complete, `cross-milestone`** → the gap brief still seeds the patch stage, which then escalates
  on it rather than patching. The boundary call is this task's product either way; the decision to
  escalate is not.
- **Thin or missing verdict, absent artifacts** → repair forward from what is on disk and the seed,
  log the gap in `input-gaps`, complete. Never reject. Never re-run the milestone's seats. Never
  re-enter the gate.
- **Owner answers pending (interactive)** → fold what arrived; remaining parked asks do not block
  completion under `default-and-disclose`. Feedback schema: each parked question paired with the
  gap-brief part it would have filled.
</done-contract>
