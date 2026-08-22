---
description: "The staff-agent component — the two ON-DEMAND seats every goal's taskforce may staff: the `leader` (the unblocker holding the goal's authority, which fixes, relaunches, routes, answers or escalates what reaches it) and the OPTIONAL `consultant` (the same judgment surface without the close-gate and acceptance authorities)."
---

# leader

This component homes BOTH staff agents of a goal's taskforce. They exist for ONE reason: a seat that cannot finish must reach a chair that is occupied. Every silent stall this system has suffered was a correct signal delivered to an empty chair.

- **`leader`** — MANDATORY. Every workflow's taskforce staffs one. It holds the goal's authority: it triages what reaches it on evidence, and it either FIXES the blocker and relaunches, ROUTES the defect to the seat that authored it, ANSWERS the question, or ESCALATES to the owner when the blocker is beyond its reach. KG: `leader` (`concepts/leader.md`, settled-by `decisions.md#d-agent-taxonomy`).
- **`consultant`** — OPTIONAL, per workflow; planning decides whether to staff one. Same judgment surface, MINUS two authorities: it never gates a close and never accepts work done. It answers guidance-shaped questions, and it routes anything needing authority to the `leader`. Its KG record is OWED — no `consultant` term resolves yet, and the mint is a registry act, not this component's.

## Lifecycle — ON-DEMAND, and it is what makes the chair occupied

Neither seat is a standing session. Both are EXCLUDED from checkin and checkout: a sitting is spawned when the seat has unread mail, it drains that mail, and it ends. Messages addressed to `leader` or `consultant` are ALWAYS accepted and queued — a send to a staff chair never fails for want of a live session, which is the whole point.

Consequence for the occupant, carried in both prompts: **there is no `checkout` at the end of a sitting.** A staff seat that checks out is a seat whose next mail wakes nothing.

## Seats

| Seat | Reached when | Launch home |
|------|--------------|-------------|
| `leader` | A seat's work terminated non-done, a seat asks mid-run, a FAIL is routed back, or an executor-failure alarm fires — the coordination CLI resolves `leader` from the goal's own roster (`lifecycle_alarm_recipient`) | Its seat folder in the goal's run; a real `taskforce.csv` row minted at goal-materialize, spawned on unread mail |
| `consultant` | A seat has a guidance-shaped question and the workflow staffed one | Same, where the workflow staffs it |

## Parts

- `prompts/leader.md` · `prompts/consultant.md` — the two roles.
- `tasks/serve-staff-mail.md` — the ONE act both seats perform. The task states the WORK; the two prompts carry the authority difference, so the difference has one home instead of two drifting copies.
- `seats.csv` — the two rows, full nine columns: `goal-writes` (empty on both — their product is messages and ledger appends, both already granted), `cage-grants`, `rw-paths` (empty on both — the staff cage stays narrow), `on-fail-relaunch` (empty on both — a staff seat holds no DAG loop route).
- **No `exposure.csv`.** Neither prompt is exposed at install time; each reaches its occupant through the seat's assembled `seat.md` at goal-materialize. A part with no manifest row is not exposed, and that is the correct state — no row is invented to fill a file.
- **No `workflows/`.** Neither seat holds a workflow node; they are taskforce members reached by mail, not DAG rows.

## Owner contact — barred, with exactly one carve-out

A goal's taskforce never talks to the owner; owner contact routes through the `master`. The `leader` holds ONE narrow exception: an **`escalation`** message, for a blocker it cannot fix and no seat can. It is a message TYPE, gated at the coordination CLI's door by identity — not a chat channel, and not a licence to open a conversation. The `consultant` holds no exception at all.

Neither seat is flagged `human-interactive`, deliberately: that flag gates contact on the goal running in interactive mode, and escalation exists precisely for the autonomous goals nobody is watching.

## Authoring provenance

Re-authored on the current component anatomy (whole-file prompts and tasks, kind-named XML sections, `seats.csv`) from the ruled design in `hand-notes/fixes/rulings-state.md` § 3. The 2026-08-10 `meta/leader-agent/` files (deleted in vault commit `d2268e6f8`) were PROSE INPUT ONLY — they use the retired split-cognitive-unit anatomy, are structured around the retired `chief-of-staff` role, and teach the `exited`→`done` flip this design BANS. None of that is carried here, and no decision anchor from them is cited: every anchor those files named is absent from the KG.

Owed to the registry, and never coined here: the `consultant` mint.
