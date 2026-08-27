---
description: "The staff-agent component — the ON-DEMAND seat every goal's taskforce staffs: the `leader` (the unblocker holding the goal's authority, which fixes, relaunches, routes, answers or escalates what reaches it)."
---

# leader

This component homes the staff agent of a goal's taskforce. It exists for ONE reason: a seat that cannot finish must reach a chair that is occupied. Every silent stall this system has suffered was a correct signal delivered to an empty chair.

- **`leader`** — MANDATORY. Every workflow's taskforce staffs one. It holds the goal's authority: it triages what reaches it on evidence, and it either FIXES the blocker and relaunches, ROUTES the defect to the seat that authored it, ANSWERS the question, or ESCALATES to the owner when the blocker is beyond its reach. KG: `leader` (`concepts/leader.md`, settled-by `decisions.md#d-agent-taxonomy`).

## Lifecycle — ON-DEMAND, and it is what makes the chair occupied

The seat is not a standing session. It is EXCLUDED from checkin and checkout: a sitting is spawned when the seat has unread mail, it drains that mail, and it ends. Messages addressed to `leader` are ALWAYS accepted and queued — a send to a staff chair never fails for want of a live session, which is the whole point.

Consequence for the occupant, carried in the prompt: **there is no `checkout` at the end of a sitting.** A staff seat that checks out is a seat whose next mail wakes nothing.

## Seats

| Seat | Reached when | Launch home |
|------|--------------|-------------|
| `leader` | A seat's work terminated non-done, a seat asks mid-run, a FAIL is routed back, or an executor-failure alarm fires — the coordination CLI resolves `leader` from the goal's own roster (`lifecycle_alarm_recipient`) | Its seat folder in the goal's run; a real `taskforce.csv` row minted at goal-materialize, spawned on unread mail |

## Parts

- `prompts/leader.md` — the role.
- `tasks/serve-staff-mail.md` — the ONE act the seat performs. The task states the WORK; the prompt carries the authority.
- `seats.csv` — the one row, full nine columns: `goal-writes` (empty — its product is messages and ledger appends, already granted), `cage-grants`, `rw-paths` (empty — the staff cage stays narrow), `on-fail-relaunch` (empty — a staff seat holds no DAG loop route).
- **No `exposure.csv`.** The prompt is not exposed at install time; it reaches its occupant through the seat's assembled `seat.md` at goal-materialize. A part with no manifest row is not exposed, and that is the correct state — no row is invented to fill a file.
- **No `workflows/`.** The seat holds no workflow node; it is a taskforce member reached by mail, not a DAG row.

## Owner contact — barred, with exactly one carve-out

A goal's taskforce never talks to the owner; owner contact routes through the `master`. The `leader` holds ONE narrow exception: an **`escalation`** message, for a blocker it cannot fix and no seat can. It is a message TYPE, gated at the coordination CLI's door by identity — not a chat channel, and not a licence to open a conversation.

The seat is not flagged `human-interactive`, deliberately: that flag gates contact on the goal running in interactive mode, and escalation exists precisely for the autonomous goals nobody is watching.

## The binding act — why an uncaged chair holds it

An approval binds at a git commit and never at a canvas [T5-R5], and the seats that WRITE a plan cannot make one: they run caged, and `.git` is a default mask (`ignite/supervisor/spawn/private-scope.js`). `leader` is uncaged and holds git, so when it ACCEPTS a seat whose declared `goal-writes` lands under `planning/`, it commits those artifacts to the vault by pathspec and writes the hash to `<goal>/planning/bound-commit` — the one source a caged verify seat can read the binding from. The commands and the discipline are in `prompts/leader.md` §4. This is the only write this component makes outside the coordination log, the five ledgers and its own seat folder.

## Authoring provenance

Re-authored on the current component anatomy (whole-file prompts and tasks, kind-named XML sections, `seats.csv`) from the ruled design in `hand-notes/fixes/rulings-state.md` § 3. The 2026-08-10 `meta/leader-agent/` files (deleted in vault commit `d2268e6f8`) were PROSE INPUT ONLY — they use the retired split-cognitive-unit anatomy, are structured around the retired `chief-of-staff` role, and teach the `exited`→`done` flip this design BANS. None of that is carried here, and no decision anchor from them is cited: every anchor those files named is absent from the KG.

The `consultant` seat this component once also homed was deleted [T2-R17, D-7-ruling]: no term for it was ever minted, so nothing is owed to the registry.
