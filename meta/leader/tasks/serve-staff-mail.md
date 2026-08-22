---
id: serve-staff-mail
description: "Drain the goal's staff mail to a disposition — every item triaged on evidence and resolved, routed, answered or escalated, so no seat's stall is left silent"
---

<task-goal>
Every item of staff mail this sitting was woken for leaves the sitting with a DISPOSITION that moves it — resolved, routed, answered, or escalated. The failure this task exists to prevent is a correct signal arriving at an occupied chair and still going nowhere.
</task-goal>

<scope>
- **IN:** the mail addressed to this seat on the goal's coordination log — staff mail minted on a seat's terminal non-done outcome, a seat's mid-run question, a routed FAIL verdict, an executor-failure lifecycle alarm; the EVIDENCE each item points at (the reporting seat's session log, its durable marker, the artifacts it claims to have produced); the goal's own artifacts (`goal.md`, `milestones.csv`, `taskforce.csv`) as the context that makes an item legible.
- **OUT:** the goal's deliverables — this seat never writes the work it judges. Operational sequencing (choosing which ready row runs next, launching a wave, materializing a seat) is the engine's and is never taken back out of helpfulness; a duty taken back is DUPLICATED, which is worse than either home. Planning, decomposition, and workflow or seat design are the planning workflow's. Anything the seat's own `<permissions>` do not grant is ROUTED, never performed.
- **Read surfaces:** the workspace, read-only, as evidence demands.
- **Write surfaces:** appended rows on the goal's coordination log; APPENDS to the five goal ledgers (`issues.md`, `decisions.md`, `doubts.md`, `gotchas.md`, `ideas.md`); this seat's own folder. Nothing else.
</scope>

<done-contract>
Done criteria — all must hold:

- EVERY item this sitting read carries exactly one disposition below, and the disposition left the seat as a MESSAGE. An item resolved only in the sitting's reasoning is not resolved.
- Each disposition rests on EVIDENCE OBSERVED THIS SITTING — the session log, the durable marker, the artifacts on disk — never on the reporting seat's own account of itself. An unclean exit says how a SESSION ended; it says nothing about whether the WORK finished.
- No unfinished row was relabelled by hand or without an investigation. The ONE sanctioned act is `rule-disposition <seat> done --anchor <anchor quoting the on-disk evidence> --go` (or destination `""` to clear the row, which re-arms an ordinary relaunch), on a row carrying `exited`, an empty cell, `unverified` or `incomplete` — recorded as a ruling line (D33(b), 2026-08-20). A `done` row is never rewritten. (Distinct from, and not to be confused with, the acceptance that gates a done-close, which is a seat's own authority where its `<permissions>` grant it.)
- Nothing was escalated to the owner that this seat or another seat could have fixed, and nothing unfixable was left un-escalated.
- The sitting ended with the mail DRAINED and with a CHECK-OUT: `done` when every item left with a disposition, `--incomplete "<why>"` otherwise, never `--force`. (Changed 2026-08-20 with D29's extension to conversational chairs: a chair's prose `done` no longer downgrades, and a checked-out chair is still re-woken by its next unread mail — while a non-terminal last row is owed a relaunch every 300 s forever.)

Disposition map — one per item, and the seat's own `<permissions>` bound which of them it may take:

- **FIX AND RELAUNCH** — the blocker is an environment or permission defect the seat can repair. Repair it, then relaunch the blocked seat on a fresh grant. Evidence for the repair goes in the message.
- **ROUTE** — the defect is in what a seat was TOLD to do, not in how it ran. Route it to the seat that authored the instruction, naming what must change.
- **ANSWER** — a substantive question with an answer this seat holds or can establish. Answer it, and where the answer is a ruling that outlives the message, append it to the goal's `decisions.md` in the SAME act — a ruling recorded only in a message is not recorded.
- **ESCALATE** — the blocker is beyond this seat and beyond any seat. Escalation is the LAST disposition, permitted only where `<permissions>` grant it; a seat without that grant ROUTES the item to the one that has it.

Outcome map:

- **An item whose disposition needs an authority this seat lacks** → route it to the staff seat that holds the authority, naming the item, the evidence, and what is asked. Never self-authorize, and never drop it.
- **An item whose evidence cannot be reached at all** → say so on the item, name the surface that is missing, and take the next disposition the missing evidence still permits. "Evidence unavailable" is a finding, never a reason to leave the item unmoved.
</done-contract>
