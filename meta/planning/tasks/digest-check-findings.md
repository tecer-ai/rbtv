---
id: digest-check-findings
description: "Digest the swarm's findings — fix mechanical ones directly, route judgment ones to the authoring seat, loop until the plan passes all checks"
---

<task-goal>
Drive the seeded draft plan to PASS on all check dimensions — six (seven when the goal's use-case ran the mechanization dimension — its findings file joins the set) — by fixing mechanical findings in place and routing judgment findings to their authoring seats.
</task-goal>

<scope>
- Read: the findings files at `planning/current/findings-*.md` — the set is six (`findings-edges.md`, `findings-resources.md`, `findings-permissions.md`, `findings-scope.md`, `findings-clarity.md`, `findings-consistency.md`), plus `findings-mechanization.md` when the goal's `use-case:` reads optimize, port or scaffold — and the draft plan under `planning/current/`; the manifest law in the guides named in this task's Guides bullet (for edge fixes).
- Write: the draft plan's artifacts under `planning/current/` (mechanical fixes only; a ROUTED repair lands only through `delta-anchors apply`, never by hand) and the disposition record at `planning/current/dispositions.md` — never a findings file; route-back files at `planning/current/route-back-<seat-id>.md`; relaunch rows appended to the run's `taskforce.csv` (existing seats only).
- **Guides — read whole before writing:** `references/workflow-anatomy.md`.
</scope>

<done-contract>
Done when, checkable at the edge:
- Every finding from every checker is dispositioned in the record: {finding, fixed-in-place + the edit | routed + the authoring seat (its `planning/current/route-back-<seat-id>.md` written, its relaunch row appended to `taskforce.csv`)}.
- Every counted verdict was read from a findings file's PASS|FAIL line, never from the file's existence — a declared file can exist empty from spawn.
- Every dimension whose subject changed was re-checked; the latest verdict of every checker that ran is PASS.
- Every routed repair was returned as a delta file and applied by `delta-anchors apply` with exit 0; a hand-applied repair is not done.
  probe lane: `delta-anchors check planning/current/deltas-<seat-id>-round-<n>.md --goal .`
- `planning/current/applied-deltas-round-<n>.json` exists for every round that applied a delta, and the re-check of that round names it.
- The disposition record shows no judgment finding fixed in place and no mechanical finding routed.

Outcome map:
- All checkers that ran PASS → completion; the plan seeds binding.
- A finding neither mechanically fixable nor routable, a route-back returned unresolved, or a finding whose re-check returned FAIL twice → FAIL-BLOCKED with the finding attached; feedback schema {finding, dispositions-tried, why-stuck}.
- A third round in which a lane raises findings against text no delta touched → FAIL-BLOCKED to the leader; feedback schema {rounds-run, findings-per-round, lanes-still-failing, why-unconverged}. The count is derived from the disposition records, never stored.
</done-contract>
