# 20260824-c-cmd-status-no-longer-claims-pa — cmd_status no longer claims pane liveness [T4-R8]

kind: change
component: team-kit
date: 2026-08-24
commit: 7b425e77
deployed: no
pin: NONE

## Motivation
Design-baseline v2 [T4-R8, C-15, C6] settles that a terminal pane is a viewport, never a
heartbeat — "is it alive" is answered only by the supervisor registry (not built by any seat
yet). `cmd_status`'s pane line rendered ACTIVE/DEAD-shaped verdicts straight off pane presence.
This is the fourth and last of this seat's (del-observers) D19 deletions.

## Design
Removed the `pane_tone`/verdict-word half of `cmd_status`'s pane report entirely (`"ok"`/`"DEAD?"`
+ `C_ALIVE`/`C_DEAD` colouring). Replaced with a plain mechanical-fact report: whether the row's
registered pane is currently present in tmux's pane list — i.e. can a wake reach it — with no
colour and no ALIVE/DEAD/ok wording. Investigated and deliberately left untouched (not this
deletion's subject, distinct concern):
- `cmd_workers`'s ACTIVE/DEAD? roster column (same pane-presence-as-liveness pattern, a sibling of
  the fixed defect, but not named in this seat's brief — see ATTENTION 1).
- `pane_harness_pids`/`seat_radius_pids`/`ident_is_live_harness`/`ident_is_live_process`/
  `wait_harness_up`: these answer "which processes are under this pane, to scope a kill/close
  safely" or "did my just-issued spawn actually start a process" — process-management mechanics,
  pid+starttime-keyed where it matters (not pane-ancestry), a different question from a standing
  "is this seat alive" status surface.
- `carrier_self_session()`: a check-in IDENTITY corroborator (D43/F-6 — "which seat is THIS
  session registered as", read off `/proc/self/cgroup`'s daemon-minted carrier unit), never a
  liveness claim. Confirmed by reading every call site before leaving it alone.

## How it works
`cmd_status`'s pane branch now reports one of four plain strings with no colour: "no pane
registered", "paneless — bound to your session id, not a tmux pane", "not in tmux's current pane
list — a wake sent to it will not be delivered", or "registered". All four are facts about
wake-deliverability through tmux, not inferences about the seat's own aliveness.

## Consequences
None outside `cmd_status` itself — no other reader of this function's output was found (it prints
directly to stdout and returns nothing, so no caller anywhere in the tree can have depended on the
removed colour codes or the removed "ok"/"DEAD?" verdict words; grepped to confirm before editing).

## Verification
`python3 -c "compile(...)"` on coord.py. `python3 coord.py selftest` from `ignite/team-kit/` —
PASS (0 failures); no existing selftest arm asserted the removed literal strings ("DEAD?"/"ok") or
colours for `cmd_status` specifically. Deployed: no (worktree only, `5-workbench/rbtv-redesign`,
branch ignite/core-redesign; live repo untouched).

## ATTENTION
1. `cmd_workers` (the `workers` command's roster listing) still classifies rows `ACTIVE`/`DEAD?`
   off `live_panes()` presence — the exact same pattern this entry fixes in `cmd_status`, left
   untouched because it was not named in this seat's brief and carries heavier downstream logic
   (a `dead` counter, an `awaiting_debts(..., live)` RAM-accounting reader, a close-seat hint).
   A future seat closing the observer-deletion program should treat this as the natural next
   sibling fix, not a new defect.
2. `carrier_self_session()` and the whole pid/pane-radius cluster
   (`pane_harness_pids`/`seat_radius_pids`/`ident_is_live_harness`) were investigated and are
   correctly OUT of scope — do not re-flag them as liveness-predicate remnants without re-reading
   this entry's Design section first.
