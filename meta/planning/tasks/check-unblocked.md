---
id: check-unblocked
description: "On the seeded trial verdict, open exactly the right passes: acceptance queues one pass per newly unblocked milestone, a FAIL below the goal's retry threshold queues one gap-filling pass, a FAIL at the threshold queues nothing — the halt"
---

<task-goal>
Act on the seeded trial verdict as the run's pass-opener: queue exactly the passes the verdict warrants — and none at a halted contract.
</task-goal>

<scope>
- **Read:** the run's `milestones.csv`, the run's verdict records — the `verdict` message rows in the run's coordination message log — and the coordination CLI's read-only `fail-status` answer for the seeded milestone.
- **Write:** the planning-pass queue requests and the machine-readable result; nothing else.
</scope>

<done-contract>
Done criteria — all must hold:

- The seeded milestone's consecutive-FAIL count and the threshold it is measured against are READ from the coordination CLI's `fail-status` verb, never re-derived here — verifiable in that the result's numbers equal that verb's answer; no stored counter is read or written, and no threshold is typed.
- On PASS: the computed newly-unblocked set equals exactly the milestones with no pass open or run whose `after` members are all accepted — verifiable by recomputing it from `milestones.csv` and the verdict records alone; one `initial` pass is queued per member, each request carrying the milestone id and its `planning-mode` stamp exactly as read — never re-judged.
- On a FAIL whose `fail-status` reports `halted` false: exactly one `gap-fill` pass is queued for the seeded milestone at the same done contract, its request carrying the verdict message number as seed pointer; a re-run of this seat on the same verdict queues no second one. This holds whether or not `escalated` is true — `escalated` is raw at-most-once history and stays true after a PASS discharges the halt, so `halted` (not `escalated`) is the gate.
- On a FAIL whose `fail-status` reports `halted` true: no pass is queued, and the result records the halted state explicitly.
- A machine-readable result exists listing the queued set (an empty set is a complete result recorded as an empty list, not a failure and not silence) or the halt record.
- `milestones.csv` is byte-identical before and after the pass.

Outcome map:

- **PASS verdict, one or more queued** → the queued passes open in parallel; this seat's work ends with the result.
- **PASS verdict, empty set** → nothing newly unblocked; the result records the empty list and the run proceeds.
- **FAIL, `fail-status` reports `halted` false** (below the bar, or a prior escalation was discharged by a later PASS) → the gap-fill pass opens from the verdict's per-clause gaps; this seat's work ends with the result.
- **FAIL, `fail-status` reports `halted` true** (at the bar, or an escalation stands undischarged) → nothing opens; the halt record stands until an owner answer appears on the channel.
- **`milestones.csv` missing or unparseable** → fail loud with the path and the parse error; never guess the graph. Feedback schema: the path, the error observed.
- **A row missing its `planning-mode` stamp** → fail loud naming the milestone id; never substitute a size judgment. Feedback schema: the milestone id, the missing field.
</done-contract>
