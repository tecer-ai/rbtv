#!/usr/bin/env python3
"""goal-watcher-job — the ENFORCEMENT half of R24's observation architecture (task 7.32).

Fired by the ignite daemon as a periodic `fire-tool` job.

**It reads team-monitor's snapshot at `{goal}/state.json` (goal-direct since 7.607; task 7.33) plus three
DECLARED NON-SENSING inputs, and performs NO RAW SENSING.** No tmux, no /proc, no harness
session files, no pane capture. team-monitor is the run's sole raw sensor and that
single-sensor invariant is the whole architecture; a second raw reader is exactly the "two
sensors, one of them fixed" failure the design exists to prevent. The absence of raw sensing
is grep-provable and a verifier greps it.

The five non-sensing inputs, enumerated so nobody has to grep for them:

  1. `{run}/taskforce.csv` — DECLARED executor bindings (see below).
  2. `{run}/coordination/messages.md` — the room's own message log, read to avoid repeating a
     flag it has already said (see the debounce, below).
  3. its own dedup-state file — what it wrote on its previous pass.
  4. `{run}/sessions.csv` — the run's own session trace, read through `coord.session_disposition`
     for ONE thing: whether a seat that is no longer in the room checked out CLEANLY. It is the
     SHADOW BACKSTOP's only added input (see THE SHADOW BACKSTOP, below). It was THREE inputs
     before that arm landed, and this count is part of the claim rather than decoration.
  5. the seat DESCRIPTORS under `{run}/seats/`, read through `coord.inbox_decls` for ONE thing:
     which seats declare `relays:` and are therefore DOORS to a human role. It is the DOOR
     EXEMPTION's only added input (see THE DOOR EXEMPTION, below), and it took the count from
     FOUR to FIVE — the count moves with the list or the list is decoration.

None senses anything; all five are files the run wrote about itself. **This wording is
deliberate and replaces an earlier "and NOTHING else", which was true about the sensing and
false about the file list — one grep falsifies it, and the accurate version cannot be.** Found
by this job's own mechanical verifier; the same shape as the recipient defect below, where a
claim was right about the thing being watched and imprecise about the thing that was not.

WHAT IT DOES: thresholds the snapshot into a DECISION SET, and delivers each decision to a
LIVE recipient. Nothing else.

THE CHAIN IS DETERMINISTIC AND HAS NO OPERATIONAL-RECOVERY AGENT IN IT (CMP-21)
-------------------------------------------------------------------------------
Owner ruling `decisions.md#d-watcher-deterministic-chain` (2026-08-08) settles CMP-21 and
RETIRES the `chief-of-staff` role and the `closer` outright. The chain this file implements
is exactly:

    deterministic detect -> fix INLINE where the fix is mechanical -> nudge the SEAT where
    the seat can act -> nudge the LEADER where judgment is needed -> the leader to the
    `master` or the owner.

No agent is ever spawned to close another agent, and NO AGENT IS EVER SPAWNED TO RECYCLE A
SEAT. No decision, remedy, flag or help string here names a retired role: that ABSENCE is the
grep-provable property, and it replaces task 7.32's older self-contradicting wording
(`job -> chief-of-staff -> leader`), which the ruling supersedes.

⚠ THAT CLAUSE READ "nothing mechanical recycles a seat" UNTIL TASK 7.662, AND IT WAS WRONG BY
ONE WORD. Owner ruling `decisions.md#d-seat-revival-kept-in-watcher-job` NARROWS it to the
sentence above: what `d-watcher-deterministic-chain` bars is an AGENT in the recycling path, not
a DETERMINISTIC SCRIPT RESTART with no agent in the loop — which is an INLINE MECHANICAL FIX and
is permitted, exactly as the sensor restart and the reap confirmation are. Everything else in
that ruling stands in full, including its retirement of the two roles. `r-leader-revival-is-
deterministic` (2026-07-30) SURVIVES unchanged and is what the revival row implements. The
amendment lands in the SAME change as the behaviour: a file whose header denies what it does is
the defect class this campaign keeps paying for, and it is why the wording is fixed here rather
than filed as a follow-up.

WHICH ROWS ACT AND WHICH ONLY NUDGE — enumerated, because "deterministic" is not a mood:

  INLINE MECHANICAL FIX (performed here, and ONLY with `--notify`; see `run_inline`)
    STALE-SENSOR  runs team-monitor's OWN idempotent `ensure` (invariant 2). Idempotent is
                  what makes it a fix rather than a judgment. A sensor that does not come
                  back is nudged to the LEADER, with the failing exit in the flag.
    REAP          runs the kit's OWN `reap` observation pass over the awaiting-close debt
                  (invariant 6). The pane KILL is `reap --go`, which coord role-gates to a
                  LEADER-CLASS seat — a gate this job holds no role to pass, in a file this
                  change does not own (⚠ coord's gate predicate still spells the retired second
                  half of that role in its own identifier; flagged for coord's owner, never
                  extended here). So the CONFIRMATION is what is performed (coord's own
                  two-pass rule needs it and its docstring names a watcher as the sweeper),
                  and the confirmed set is what is nudged to the LEADER.
    REVIVAL       fires the system's ONE deterministic seat-revival ACTUATOR — a DETACHED exec
                  of coord.py's `lifecycle-exec --disposition revive` — at a debounced GHOSTROW
                  whose seat is NOT a door and for which the snapshot yields a tmux target. It
                  moved here from `watch.py`'s `fire_revival` by owner ruling
                  `decisions.md#d-seat-revival-kept-in-watcher-job` (task 7.662). It is the ONE
                  row here that is NOT idempotent, so it is the ONE row gated on the flag being
                  FRESH — see THE REVIVAL ROW below, and `run_revival`.
  NUDGE THE SEAT  QUIET (the seat is the one that can answer) and CONTEXT (invariant 3: the
                  seat renews ITSELF — writes memory, runs `checkout --renew`, relaunches).
                  Unresolved `--escalate-after` consecutive passes later -> nudge the LEADER.
  NUDGE THE LEADER  every row needing judgment: ROOM-DEAD, BOX, RUN-STALL, APPROVAL,
                  DEAD/COMPLETED/GHOSTROW, WORKTREE-SWEEP, and every escalated seat row.

Two Layout rows are DELIBERATELY not actuated here, and each names its owner rather than
being silently absent:

  - the dirty-finish FAILURE-MODE ENQUEUE stays SHADOW — barred as autonomous actuation by
    rider 1 of `p-756-edge-consumption-true` (OWNER-CLASS, not this change's to reverse) and
    by `r-cutover-gated`. See THE SHADOW BACKSTOP below.
  - LAUNCH GATING under a breached RAM floor ALREADY belongs to the launch door:
    `coord.launch_gates` refuses a launch against the SAME `budget.json` floor this row
    thresholds. A second gate here would be a second implementation of one rule (`PRIN-11`),
    free to disagree with the door that actually stops launches. So this row detects the
    RISING TREND the at-launch gate structurally cannot see (it fires AT LAUNCH and cannot
    evaluate a trend) and nudges the LEADER with the facts. It never kills a working seat.

THE DEAD-ROOM ROW HANDS OFF; IT DOES NOT REBUILD
------------------------------------------------
Task 7.71's `selfheal-room` job is already registered and live against this room, with its
own probe trail. A second recovery path for the same failure is not redundancy — it is two
mechanisms that can disagree about whether a room is dead and both act. So this row DETECTS
(`session_alive: false`) and names the owner of the recovery. Coverage is unchanged; what
changes is only that the condition now appears in this job's decision set, where the shadow
window can score it.

STALENESS IS PAUSE + RECOVER, NOT ALERT-ONLY (R24, CMP-21 invariant 2)
----------------------------------------------------------------------
A snapshot older than `--tolerance-mult` x the sensor cadence means THE SENSOR IS THE
INCIDENT. Two behaviours, both required and both implemented here: enforcement PAUSES
entirely (no threshold acts off a frozen snapshot — a watcher enforcing on a stale world
acts against seats that no longer exist), AND the sensor's own idempotent `ensure` is run
INLINE, here, as a mechanical fix with no agent in the path. Enforcement resumes on the
first fresh snapshot, with no manual re-arm. A sensor the `ensure` does not bring back is
the one case that leaves this row for the leader.

This is a PREREQUISITE of the box-pressure row, not a sibling of it. `box{}` lives inside
the snapshot, so a dead sensor takes the box signal with it silently — the gravestone shape
(`p-heartbeat-is-two-facts`) one level up. Only the tripwire makes that failure announce
itself, which is why E3 must be green before E5 is trusted.

A SEAT WHOSE CORRECT STATE IS NOT-RUNNING (run issues G-68 + G-76)
------------------------------------------------------------------
Two defects inherited from the `watcher` rather than rediscovered, because this job is the
detector that would otherwise repeat them, and they are the same class: CORRECT BEHAVIOUR
SCORED AS FAILURE.

  G-68 — a standby seat's correct state is WAITING. An inactivity check with no concept of
  it cries wolf forever, and the fourth time a leader waves the alarm off is the time a
  genuinely hung seat is waved off with it. `--standby SEAT` suppresses QUIET for that seat
  and reports it as `STANDBY` — visible, never silent, never a flag.

  G-76 — `opencode run` is ONE-SHOT: it executes, prints, exits. "Roster ACTIVE + no harness
  process" is its SUCCESS path. For an interactive harness the same reading is a ghost. The
  two remedies are OPPOSITE (close vs relaunch), so conflating them is not cosmetic.
  `--one-shot-harness` splits them: COMPLETED (remedy: close) vs GHOSTROW (remedy: inspect,
  then relaunch or close).

THE DOOR EXEMPTION, AND THE GHOSTROW DEBOUNCE (G-176; kit map rows B9 + B13)
----------------------------------------------------------------------------
Two defects the kit had already paid for and written down, which this layer re-opened when it
was built and which are closed here. Both were measured on ONE event: 2026-07-30 03:34, the
owner's own `master` door.

  THE DEBOUNCE. A roster-ACTIVE row whose pane holds no harness process is, in ONE reading,
  indistinguishable from a harness mid-restart and from a pane read inside a relaunch's startup
  window. GHOSTROW therefore requires `GHOSTROW_DEBOUNCE_PASSES` CONSECUTIVE readings; a single
  reading emits `GHOSTROW-PENDING`, which is REPORTED and never delivered. The counter rides the
  same `_repeat` map the QUIET/CONTEXT ladders use, so a healthy reading CLEARS it and a stale
  snapshot FREEZES it (`evaluate` returns before `_repeat` is rewritten) — a reading that could
  not be taken is evidence in neither direction. ⚠ THE ONCE-PER-EPISODE `armed` DEDUP IS NOT A
  DEBOUNCE and never was: it suppresses REPEATS, never the FIRST reading, which is precisely the
  one that fired on the door.

  THE DOOR EXEMPTION, SCOPED TO THE REMEDY. A seat declaring `relays:` has a pane that is a DOOR
  to a human role, and `r-owner-afk-liaison-parked` has that pane deliberately OUTLIVE its
  session — so a parked door is byte-identical to a ghost, and to a quiet seat, under the only
  observations this job has. GHOSTROW's remedy was unconditionally `close-seat <name> --renew`
  and QUIET-ESCALATED's was `close <name> --renew`: the exact act that ruling forbids, coached at
  the owner's channel. ⚠ THE FLAG IS NOT SUPPRESSED — a door in trouble and a door waiting look
  identical from outside, so muting would make this fix its own next failure. What changes is the
  REMEDY, and only for the door.

  ⚠ DERIVED FROM `relays:`, NEVER FROM A PANE ID OR A SEAT NAME, and read through
  `coord.inbox_decls` — the ONE home of that derivation, which the kit's reap exemption and
  revival door gate already read. A second parse here would give one fact a second home to drift
  in (G-159); a rule naming `%40` or `master` would protect a dead pane and one campaign's
  vocabulary respectively.

NOTE FOR THE SHADOW WINDOW: `COMPLETED` and `STANDBY` are classes the OLD layer cannot
emit. That is a declared DIVERGENCE, filed before the window opens — not a disagreement
discovered inside it, which would invalidate the window. `GHOSTROW-PENDING` is a THIRD such
class, declared here for the same reason and on the same terms; the door-scoped GHOSTROW and
QUIET rows are the same class as before with a different ACTION, which the comparison object
scores as a divergence in the action term and not as a missing row. `REVIVAL` is a FOURTH,
declared on the same terms — and it is ADDITIVE: the GHOSTROW row it accompanies is still
emitted, unchanged in class, action and remedy, so the comparison sees one extra row rather
than a row that moved.

THE REVIVAL ROW — THE ACTUATOR'S NEW HOME (task 7.662)
-------------------------------------------------------
`watch.py`'s `fire_revival` was the system's ONLY deterministic seat-recovery actuator, and
`decisions.md#d-seat-revival-kept-in-watcher-job` moved it HERE rather than letting task 7.35
delete it with its host. Three things about the move are worth stating because each is a place
a literal port would have gone wrong:

  THE DETECTOR DID NOT MOVE — IT WAS ALREADY HERE. `check_revival`'s candidate set is
  `snap["roster_absent"]` and its discriminator is harness-pid liveness and nothing else
  (`r-leader-revival-is-deterministic`'s BINDING CONDITION: a hard pane/pid death signal, never
  a silence threshold). That is precisely the GHOSTROW row above. So the revival row hangs off
  that row rather than re-deriving the condition: one detector, and the debounce and the DOOR
  EXEMPTION come with it for free. A DOOR IS NEVER REVIVED — its pane deliberately outlives its
  session, so a revival there would sever the channel its human is reachable through.

  THE TARGET IS DERIVED FROM THE SNAPSHOT AND NOTHING ELSE, which is what keeps the no-raw-
  sensing invariant true. `revival_fork_target` in `watch.py` called tmux DIRECTLY
  (`coord.live_panes`, `tmux_pane_window_name`, `tmux_find_window_pane`) — three raw reads that
  MUST NOT follow the actuator into this file. `revival_target` below replaces them with the
  snapshot's own `liveness` and pane fields. The one check that is genuinely lost is watch.py's
  pre-flight window-drift test, and it is lost SAFELY: `--force` is never passed, so
  `launch_seat`'s OWN window-drift check still runs downstream and a drifted pane produces a
  LOUD REFUSAL from the executor rather than a misplaced seat.

  THE DETACHMENT IS NOT `Popen(start_new_session=True)` — see the block above `run_revival`.

WHAT DID **NOT** MOVE, AND IS NOT SILENTLY ABSENT. `watch.py`'s revival CLAIM MUTEX
(`claim_revival`), its attempt LADDER (`revival_ladder`) and its RAM-floor refusal
(`revival_floors`) stay in `watch.py` and are 7.35's to home or retire. What stands in for them
here is stated rather than assumed: the once-per-episode `armed` gate below, `jobcontain`'s
stable transient-unit name (systemd refuses a second unit of that name while the first is
active), and coord's OWN entry guard 3, which stands down when a live executor already holds
the seat. The residual ceiling is that a flag whose DELIVERY fails re-arms and may re-fire the
revival up to `DELIVER_RETRIES` times inside one episode; the two guards above make each of
those a refusal rather than a second launch, and the ladder is 7.35's decision, not this row's.

ONE INPUT THAT IS NOT THE SNAPSHOT, AND WHY IT IS NOT A SECOND SENSOR
---------------------------------------------------------------------
`{run}/taskforce.csv` — the run's own DECLARATION of each seat's executor binding. It is
read for exactly one thing: which harness a seat was bound to, so a vanished process can be
classed COMPLETED or GHOSTROW. The snapshot cannot answer it, and the bound is worth stating
rather than discovering: when a harness process is gone, team-monitor reports `harness: ""`
— there is no process left to identify. A runtime fact is gone; a DECLARED one is not.

The invariant is untouched. The snapshot remains the sole source of RUNTIME FACTS; the
roster is the source of DECLARED SEAT PROPERTIES and senses nothing. No tmux, no /proc, no
harness session file is read here — which is the criterion, and it is grep-provable.

THE ACCEPTED TRADE, STATED IN THE DESIGN BECAUSE THE CONTRACT ASKS FOR IT
-------------------------------------------------------------------------
A tmux-server death loses every in-flight turn. Nothing here changes that, and nothing here
is built to. This layer is RECOVERY, NOT SURVIVAL: it notices that the room, a seat, or the
sensor has stopped, and it names who repairs it. It cannot preserve the work that was in
flight at the moment of death, and a design that tried would be a different system.

That re-scopes CON-1 rather than satisfying it, and the re-scope is deliberate. Do not build
for survival on top of this: the honest boundary is that a restarted seat resumes from its
recorded session ref and its written memory, never from the turn it was mid-way through.

WHAT IS NOT IN THIS FILE, AND MUST NOT BE READ AS COVERED
---------------------------------------------------------
The R4 RESTART PATH — recreating the room from launch profiles on crash/reboot and resuming
each seat by harness-native session ref, with a restarter AGENT as the fallback for a
non-resumable harness or a corrupt transcript. This job DETECTS a dead room and names its
owner; it does not perform the restart, and no line here should be read as evidence that a
live crash+restart has been exercised. Task 7.32's criterion on that is a SEPARATE build and
is reported UNMET rather than folded into this one's green.

THE SHADOW BACKSTOP — IT COMPUTES THE ENQUEUE AND DOES NOT PERFORM IT (task 7.430 / W7)
---------------------------------------------------------------------------------------
CMP-21's layout carries one row this job does NOT have: *seat finished/dead, no clean check-out
→ enqueue its `workflow-edge` job in FAILURE MODE (CMP-25) — the backstop to the check-out fast
path.* That enqueue is an ACTUATION, and rider 1 of `p-756-edge-consumption-true` bars it: the
rider is OWNER-CLASS and is not the run's to reverse, and `r-cutover-gated` stands beside it.
So the row is built SHADOW, which is the sanctioned design that rider names:

  DETECT  a seat in the snapshot's `roster_absent` — finished or dead, out of the room
  DECIDE  read its DURABLE disposition off `sessions.csv` (`coord.session_disposition`) and
          COMPUTE the would-be decision: `done` → WOULD-NOT-ENQUEUE, anything else including
          UNKNOWN → WOULD-ENQUEUE (failure mode)
  EMIT    one probe-trail record per detected seat at
          `{package}/coordination/goal-watcher-shadow-trail.jsonl`, carrying the three fields
          the design orders — the INPUTS READ, the DECISION REACHED, and the ACT NOT TAKEN

**THE ACT IS NOT PERFORMED, AND THAT IS AN ACT-IDENTITY CLAIM, NOT A LABEL.** The barred act's
side-effect set, read at `edge-runner-job.py:enqueue` → `default_submitter`, is: spawn
`ignite add-job` through `subprocess.run`, which reaches the daemon's gateway `enqueue-job`
intent, which writes a durable queue row, which later launches a seat. This arm's side-effect
set is: append lines to the trail file above, and print. THE INTERSECTION IS EMPTY, and it is
still grep-provable — but the proof is NARROWER than it was, and the narrowing is stated here
rather than left for a reader to discover. This file now DOES import `subprocess`: CMP-21's
invariants 2 and 6 make the sensor restart and the reap confirmation INLINE MECHANICAL FIXES,
and a fix that spawns nothing is not a fix. So the claim is no longer "imports no
`subprocess`" but the exact one that matters: `INLINE_FIX_SCRIPTS` is the COMPLETE set of
programs `run_inline` may exec and it is enforced there by refusal, `ignite` is not in it and
neither is any queue door, this file imports `edge-runner-job` not at all, and it contains no
enqueue verb and no queue call. A shadow that
enqueued to a side queue would still be the barred act (D-3's act-identity test); the bar
attaches to the side-effect set, never to the word on the branch.

**TRAIL GREENS NEVER RIPEN INTO AUTHORITY.** No accumulation of records here — none, at any
count, however long they agree with the predicted decisions — authorizes performing the act.
The REAL enqueue arrives one way only: a FRESH authorization from the bar's owner, which is
OWNER-CLASS and travels through the `master`. It is not queued by this wave and no line here
asks for it.

NOTE FOR THE SHADOW WINDOW: `SHADOW-BACKSTOP` is a decision class the OLD layer cannot emit,
declared here as a DIVERGENCE the same way `COMPLETED` and `STANDBY` are above — filed before
the window rather than discovered inside it. It is REPORTED and never DELIVERED: its action
begins `none`, which is the existing suppression the STANDBY row already relies on. Nobody is
woken about a decision nobody may act on.

WHAT IT WRITES
--------------
stdout/stderr (captured by `fire-tool` into `{data_root}/logs/`, bounded by task 7.13's age
sweep), ONE small dedup-state file at `{package}/coordination/goal-watcher-state.json`, and the
shadow trail at `{package}/coordination/goal-watcher-shadow-trail.jsonl` — capped at
`SHADOW_TRAIL_KEEP` records, so it is bounded rather than a new unbounded artifact class.
`coordination/` is script-owned by the run's surface map.
It never writes `state.json`: task 7.33 has exactly one writer and this is a reader.
"""

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobcontain  # noqa: E402
sys.path.insert(0, str(HERE.parent / "team-kit"))
import budget as budget_mod  # noqa: E402 — the ONE reader of the run's declared floor (task 7.82)

# The LEADER is the one role this job escalates to (CMP-21's chain). The two roles that ruling
# retired name nothing here, and `--selftest` asserts it rather than this comment claiming it.
DEFAULT_LEADER_SEAT = "leader"
DEFAULT_FALLBACK = ""
DEFAULT_CADENCE_S = 20.0
DEFAULT_TOLERANCE_MULT = 3.0
DEFAULT_QUIET_MIN = 30
# How many CONSECUTIVE passes a seat-addressed row may go unresolved before the same condition
# is escalated to the leader (CMP-21 Layout rows 3 and ctx-refresh: "still quiet N cadences
# later -> nudge the LEADER"). Consecutive, not cumulative: the counter resets the pass the
# condition clears, so a seat that answers and later goes quiet again starts its own episode.
DEFAULT_ESCALATE_AFTER = 3
# ⚠ `DEFAULT_MEM_FLOOR_MB = 2000` STOOD HERE, and its own comment said the quiet part out loud:
# "it MUST be re-synchronised whenever that ruling moves — it is a copy, and a copy drifts." A
# default that documents its own drift is still a home. Task 7.82 / `r-floor-single-source` deletes
# it: the floor is READ from the run's budget.json (this job already requires `--package`), and
# `--mem-floor-mb` survives ONLY as a deliberate operator override. No fallback number lives here.

# How many passes may ATTEMPT to deliver one flag before the episode is armed anyway (task
# 7.536). The dedup state records DELIVERY, not INTENT: a `deliver()` that failed leaves the
# episode RETRYABLE, so the next pass re-nudges. BOUNDED, because an unreachable coord would
# otherwise re-nudge forever — at the bound the flag is armed and the failure stands on the
# record. The counter resets the pass the condition clears.
DELIVER_RETRIES = 3
DEFAULT_LOAD_PER_CORE = 1.5
SWAP_RISE_READS = 3

# ---- THE GHOSTROW DEBOUNCE (see THE DOOR EXEMPTION, AND THE GHOSTROW DEBOUNCE above).
# CONSECUTIVE snapshot readings a ghost row must hold before GHOSTROW is DELIVERED. Two, which
# is the kit's own `GHOSTROW_DEBOUNCE_TICKS` — the value it landed on after one reading flagged
# the owner's door off a mid-restart window. Below 2 there is no debounce at all.
GHOSTROW_DEBOUNCE_PASSES = 2

# The remedy every DOOR-scoped row carries, in place of the close/renew command a worker's seat
# gets. ⚠ IT IS PROSE AND CARRIES NO COMMAND, deliberately: the remedy is a line a leader — or an
# agent acting on a leader-addressed flag — PASTES, and the only operands a door row could
# interpolate are a seat name and a pane id off the snapshot, which nothing validates the
# characters of (task 7.601). A remedy with nothing to quote cannot be quoted wrong.
DOOR_REMEDY = (
    "LOOK at the pane before assuming anything — and do NOT close, reap or renew this row. Its "
    "pane is a DOOR to a human role and deliberately outlives its session "
    "(r-owner-afk-liaison-parked), so what this flag reports is NOT by itself evidence of a "
    "fault — and it is NOT proof the door is fine either. THEY LOOK IDENTICAL FROM OUTSIDE. "
    "Closing or renewing it severs the channel its human is reachable through; re-opening a door "
    "is done by relaunching in THAT SPOT and is the leader's judgment, never a mechanical "
    "response to this flag.")

# ---- the SHADOW BACKSTOP's constants (task 7.430 / W7). See the docstring section.
SHADOW_TRAIL_FILENAME = "goal-watcher-shadow-trail.jsonl"
SHADOW_TRAIL_KEEP = 500
# The ONE value that is a clean check-out. Equality against one value — never a truthiness test,
# never "not renew" — the same gate `edge-runner-job.py`'s ADVANCES_EDGE holds, for the same
# reason: `renew`, `revive` and `exited` each name a seat that has NOT finished.
CLEAN_CHECKOUT = "done"
# The act this arm COMPUTES and DOES NOT PERFORM, written out in full because the record's
# `act_not_taken` field is this constant and nothing else — there is deliberately no code path
# by which a trail record can carry an act that WAS performed.
BARRED_ACT = ("enqueue this seat's `workflow-edge` job in FAILURE MODE (CMP-25) "
              "through the daemon's enqueue door — barred as autonomous actuation by rider 1 of "
              "`p-756-edge-consumption-true` (OWNER-CLASS, not the run's to reverse) and by "
              "`r-cutover-gated`. NOT PERFORMED. No accumulation of these records authorizes "
              "performing it; the real act needs a FRESH owner-class authorization through the "
              "`master`.")

# ---- the INLINE MECHANICAL FIX door (CMP-21 invariants 2 and 6).
# THE COMPLETE SET OF PROGRAMS THIS FILE MAY EXEC, by basename. It is the successor to the
# old "imports no subprocess" proof: the barred act's door is `ignite add-job`, `ignite` is not
# on this list, and `run_inline` REFUSES anything that is not — so the act-identity claim in
# THE SHADOW BACKSTOP is enforced by a branch rather than by a promise.
INLINE_FIX_SCRIPTS = ("team_monitor.py", "coord.py")
INLINE_FIX_TIMEOUT_S = 45

# ---- THE SECOND EXEC DOOR, AND IT IS THE SAME DOOR (task 7.662).
# The revival actuator reaches `coord.py`, which is ALREADY on `INLINE_FIX_SCRIPTS` — a revival
# IS an exec of `coord.py lifecycle-exec`. So this change needs NO new program, NO new exec path
# and, above all, NO WIDENING OF THE ALLOWLIST: the allowlist's narrowness is what makes the exec
# surface auditable and what enforces THE SHADOW BACKSTOP's act-identity claim, and both doors go
# through the ONE gate `_inline_fix_program` with the ONE refusal (PRIN-11).
REVIVAL_CLASS = "REVIVAL"
# THE ATTEMPT LADDER (task 7.35 Phase B, ported from `watch.py:2436 revival_ladder`, which dies
# with that file). The once-per-episode `armed` gate below suppresses REPEATS of a steady
# condition; it does NOT bound an episode that keeps re-arming. A flag whose DELIVERY fails is
# left UNARMED on purpose (see `DELIVER_RETRIES`), so one episode can legitimately reach this
# fire more than once — and NOTHING capped it. Double-launch is covered three ways already
# (`armed`, systemd's refusal of a second unit of the same name, coord's entry guard 3); RUNAWAY
# was covered by nothing, and runaway is the storm case.
#
# Bounded BY CONSTRUCTION — the tuple's LENGTH is the cap, the `RELAUNCH_BACKOFF_S` idiom, so no
# second constant can disagree with it and no configuration revives forever. Each element is what
# that attempt is CALLED in the line a human reads, so the ladder's position is legible in the log.
REVIVAL_ATTEMPTS = ("first", "second", "final")
REVIVAL_UNIT_PREFIX = "rbtv-revival"


def _inline_fix_program(script):
    """(name, refusal) — THE allowlist gate. ONE implementation, BOTH exec doors. `refusal` is
    "" when the program is allowed.

    ⚠ THE EMPTINESS CHECK RUNS FIRST, and the order is the whole point. `--team-monitor`
    DEFAULTS TO `""`, so an entry that omits it reaches here with an empty path — and
    `basename("")` is `""`, which the allowlist branch below rejects with "`` is not an
    inline-fix program … no queue door is reachable from here". That text lands in the flag the
    LEADER reads (the caller folds this detail into it), pointing at the act-identity bar when
    the actual cause is an unset operator flag. Behind the allowlist branch this check was
    unreachable, which is why it never fired.

    ⚠ SPLIT OUT OF `run_inline` BY TASK 7.662 rather than copied into the revival door. A second
    copy of the check that makes this file's exec surface auditable is a second copy free to
    drift, and the whole act-identity claim rests on there being exactly one branch to read."""
    if not str(script).strip():
        return "", ("REFUSED: no program path was given for this inline fix — the operator "
                    "flag naming it (`--team-monitor` for the staleness row, `--coord` for "
                    "the reap row) is unset or empty, so the row degrades to a nudge. This is "
                    "a MISSING PATH, not a refused program.")
    name = os.path.basename(str(script))
    if name not in INLINE_FIX_SCRIPTS:
        return name, (f"REFUSED: `{name}` is not an inline-fix program. This job may exec only "
                      f"{INLINE_FIX_SCRIPTS} — no queue door is reachable from here.")
    return name, ""


def run_inline(script, tail, timeout=INLINE_FIX_TIMEOUT_S):
    """Run ONE inline mechanical fix as a child process. (ok, detail). THE ONLY exec door here.

    Both fixes it carries are IDEMPOTENT by the callee's own contract — team-monitor's `ensure`
    and coord's observe-only `reap` — which is precisely what makes them fixes rather than
    judgments, and what makes running one on every stale pass safe.

    The child is exempted from this job's own address-space and CPU caps (`child_preexec`): a
    sensor restart killed by the WATCHER's budget would leave the sensor half-started, which is
    a worse state than the one being repaired.

    ⚠ SYNCHRONOUS AND TIMEOUT-BOUNDED, AND THAT IS WHY THE REVIVAL DOES NOT COME THROUGH HERE:
    see the block above `run_revival`."""
    name, refusal = _inline_fix_program(script)
    if refusal:
        return False, refusal
    try:
        r = subprocess.run([sys.executable, str(script), *tail], capture_output=True,
                           text=True, timeout=timeout, preexec_fn=jobcontain.child_preexec)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return False, f"`{name}` did not run: {type(exc).__name__}: {exc}"
    lines = [ln for ln in (r.stdout or r.stderr or "").splitlines() if ln.strip()]
    return r.returncode == 0, (f"exit {r.returncode}"
                               + (f"; {lines[-1].strip()[:160]}" if lines else ""))


# ---- THE SEAT-REVIVAL ACTUATOR (task 7.662). See THE REVIVAL ROW in the module docstring for
# WHY it lives here; this block is the ONE adaptation the move forced, and it is recorded at the
# code because a reader of the fire needs it before the fire, not in a run log.
#
# ⚠⚠ THE SYNC-VS-DETACHED MISMATCH, AND THE ARM CHOSEN. `run_inline` is `subprocess.run` under
# `INLINE_FIX_TIMEOUT_S`; `watch.py`'s `fire_revival` was fire-and-forget. They do not compose.
# THE CHOICE IS ARM (a) — A DETACHED VARIANT OF THE SAME DOOR — and it is forced by measurement,
# not preference:
#   · ADAPTING REVIVAL TO THE TIMEOUT BOUND (arm b) IS UNSAFE. `cmd_lifecycle_exec` runs a
#     bounded SETTLE WAIT, then checks out the predecessor and RELAUNCHES the seat.
#     `subprocess.run` KILLS its child at the timeout, so a revival one second over the bound
#     would be killed MID-SEQUENCE, leaving a seat half-renewed — strictly worse than the outage
#     it repairs. Raising the bound instead would block the whole watcher pass behind one seat.
#   · WAITING BUYS NOTHING. The exit contract is the EXECUTOR's (2 = a guard refused, 3 = the
#     guards passed and the sequence broke, 0 = completed) and is read off the seat's lifecycle
#     marker and the unit's journal by design. The caller exiting is a NORMAL, cheaper outcome
#     for the child: `lifecycle_settle` records `caller-exited` immediately instead of burning
#     its full settle budget waiting on a watch loop that never exits (coord.py § s3-07).
#   · THE ALLOWLIST IS NOT TOUCHED. Both doors call `_inline_fix_program`; `coord.py` was
#     already on it. Widening `INLINE_FIX_SCRIPTS` to dodge this would have destroyed the exact
#     property the door exists for.
#
# ⚠⚠ AND `Popen(..., start_new_session=True)` — what `watch.py:2320` did — IS NOT DETACHMENT IN A
# FIRED JOB. THIS IS THE ONE PLACE A VERBATIM PORT WOULD HAVE SHIPPED A SILENT DEFECT: a
# `fire-tool` exec runs inside its own transient systemd unit, so a plain detached child stays in
# THIS pass's cgroup and is reaped with it. MEASURED 2026-07-27 05:15 (evidence
# C2-daemon-staged-failure.txt; `jobcontain.detach_argv`'s own docstring) — a detector that
# relaunched `watch.py` that way reported a real pid and the process was gone moments later, and
# it only shows up when the job is run END TO END. So the revival goes out through
# `jobcontain.detach_argv` + `launch_detached`, which is what every other outliving act in this
# folder already uses (`selfheal-room.py`, `selfheal-watch.py`, `restart-daemon.py`) — ONE
# implementation of "outlive this job" (PRIN-11), not a fourth. Two things come free: the child
# is outside this pass's cgroup by construction, and `--unit=` REFUSES when a unit of that name
# is already active, which is a systemd-enforced double-fire guard under this file's own.


def caller_ident(args):
    """`(pid, starttime)` for THIS pass, or `None` when it cannot be read. Resolved ONCE in
    `main` and passed on `args` — the same discipline `door_seats` follows, so `evaluate` stays
    PURE and a fixture can drive the revival row with no `/proc` and no package on disk.

    `lifecycle-exec` REQUIRES `--caller-pid` and `--caller-starttime`, and the PAIR is the point:
    it lets the executor tell "my caller exited" from "a recycled pid landed on its number". A
    pid alone is not an identity, so an unreadable stat REFUSES the revival rather than inventing
    one — the same refusal `watch.py`'s `fire_revival` made under the name `no-ident`.

    ⚠ THIS IS NOT RAW SENSING, AND THE INVARIANT'S OWN WORDS ARE WHAT DRAW THE LINE. What this
    job may not do is SENSE THE ROOM — tmux, a seat's `/proc`, a harness session file, a pane
    capture — because team-monitor is the sole raw sensor of the ROOM and a second reader of it
    is the failure the design exists to prevent. This reads THIS PROCESS'S OWN identity, about
    which the room says nothing and with which no sensor can disagree. `coord.proc_stat` is the
    ONE reader of that file's format (the same single-reader rule `declared_door_seats` states).
    """
    try:
        sys.path.insert(0, str(Path(args.coord).resolve().parent))
        import coord  # noqa: E402 — the /proc/<pid>/stat format's single reader
        starttime = coord.proc_stat(os.getpid())[1]
        return (os.getpid(), starttime) if str(starttime or "").strip() else None
    except Exception:                                             # noqa: BLE001
        return None


def revival_target(row, snap):
    """PURE. `(target, why)` — the tmux target for a revival, FROM THE SNAPSHOT ALONE.
    `("", why)` means REFUSE, NEVER FIRE.

    ⚠⚠ AN EMPTY TARGET IS THE FAILURE MODE THIS FUNCTION EXISTS FOR, quoted from
    `jobs/recover-room.py:12-19`: *"it would not fail, it would guess"* — `launch` resolves its
    target as `COORD_LAUNCH_TARGET or TMUX_PANE`, a daemon-fired exec has NEITHER, and tmux
    resolves an EMPTY target to the MOST RECENT session, measured to be the LIVE room. *"A
    recovery that opens agents into the live room believing it is repairing a dead one is worse
    than no recovery at all."* So this returns "" and the caller refuses; it never hands ""
    downward.

    TWO STEPS, and they are `watch.py`'s four with the three tmux reads REMOVED — which is the
    whole no-raw-sensing half of the move:
      1. the row is `no-harness` — team-monitor's own class for a pane that is STILL IN THE ROOM
         holding no harness process. The pane's presence is the sensor's reading, not a fresh
         tmux query, so the successor respawns IN PLACE and the window layout survives (G-12).
      2. the row is `absent` — the pane LEFT the room. RE-PLACE onto an anchor: any pane THIS
         SAME SNAPSHOT reports live. There is exactly ONE room per snapshot (team-monitor writes
         one `session`), so a live pane on it is a pane of this room and `launch_seat` derives
         the session from it. This is `watch.py`'s own last-resort anchor, and it was ALREADY
         snapshot-derived there.
      3. nothing resolves -> "" and the caller refuses LOUDLY (R-8).

    ⚠ WHAT IS LOST, AND WHY IT IS LOST SAFELY. `watch.py` step 2 also asked tmux whether the live
    pane still sits in the window its descriptor declares, and re-placed when it did not. That is
    `tmux_pane_window_name` — a raw read, and it does not follow the actuator here. The check is
    NOT gone from the system: `args.force` is never set on this path either, so `launch_seat`'s
    OWN window-drift check runs downstream and a drifted pane is a LOUD REFUSAL by the executor
    rather than a seat opened in the wrong place. The cost is one extra round trip on a drifted
    seat; the invariant is worth more than the round trip."""
    pane = str((row or {}).get("pane") or "").strip()
    if pane and (row or {}).get("liveness") == "no-harness":
        return pane, (f"pane {pane} is STILL IN THE ROOM and it is the HARNESS that is gone — "
                      f"team-monitor classes the row `no-harness` — so the successor respawns IN "
                      f"PLACE and the window layout survives (G-12)")
    for s in ((snap or {}).get("seats") or []):
        p = str(s.get("pane") or "").strip()
        if p and s.get("liveness") == "live":
            return p, (f"pane {pane or '<none recorded>'} is NOT in the room any more, so the "
                       f"successor is RE-PLACED onto anchor {p} — a pane THIS SAME SNAPSHOT "
                       f"reports live, and there is exactly one room per snapshot, so it is this "
                       f"room's. `launch_seat` derives the session from the anchor")
    return "", (f"pane {pane or '<none recorded>'} is not in the room and this snapshot reports "
                f"NO live pane to re-place onto. NO ANCHOR RESOLVES — refusing rather than "
                f"passing an empty target down: with an empty target tmux resolves to the MOST "
                f"RECENT session, measured to be the LIVE room. If the WHOLE room is gone that "
                f"is `jobs/recover-room.py`'s (task 7.71), not this row's")


def revival_argv(args, seat, pane, target, caller):
    """PURE. The EXACT argv tail of the detached fire, so the selftest greps it without forking.

    `--handoff-written 0` and it is DELIBERATE, not an omission: a crashed session had no turn
    boundary at which to write a handoff block, so requiring one would make revival impossible in
    exactly the case revival exists for. The predecessor's last UNREAD block stays where it is
    and is delivered at the successor's `checkin`. NOTHING ON THIS PATH READS OR WRITES
    `memory.md` — R-14.

    NO `--force` AND NO `--force-memory`. `lifecycle-exec` does not accept them, and `--force`
    carries the ROLE gate ALONE — it would not lift a memory or a window-drift refusal even if it
    were passed. That is also what leaves `launch_seat`'s window-drift check standing (see
    `revival_target`).

    ⚠ LIST-ARGV, NEVER A SHELL LINE. The seat name is an operand off the snapshot and reaches the
    exec as one array element, so task 7.601's quoting hazard — which is about a remedy string a
    leader PASTES — does not arise on this path and MUST NOT be "fixed" by quoting here, which
    would hand coord a literal quote character. No revival operand ever reaches a remedy TEXT."""
    return ["lifecycle-exec",
            "--package", str(args.package),
            "--seat", str(seat),
            "--disposition", "revive",
            "--pane", str(pane or ""),
            "--tmux-target", str(target),
            "--caller-pid", str(caller[0]),
            "--caller-starttime", str(caller[1]),
            "--handoff-written", "0"]


def run_revival(script, tail, unit):
    """FIRE one DETACHED seat revival. `(outcome, why)`. NEVER raises. See the block above.

        "FIRED"    the executor is running in its own transient unit; `why` names it
        "REFUSED"  the allowlist or the detach pre-flight said no — NOTHING was started
        "BROKE"    the launch itself failed — nothing is running

    ⚠ THE THREE ARE DIFFERENT FACTS and the caller must not collapse them into "not fired" — the
    same discipline `watch.py`'s `fire_revival` states, carried over with the actuator."""
    name, refusal = _inline_fix_program(script)
    if refusal:
        return "REFUSED", refusal
    argv = [sys.executable, str(script), *tail]
    try:
        launch, launched_unit = jobcontain.detach_argv(argv, unit)
        out, code = jobcontain.launch_detached(launch, launched_unit,
                                               preexec_fn=jobcontain.child_preexec)
    except jobcontain.CarrierEnvMissing as exc:
        # REFUSED, not BROKE: the pre-flight declined to launch and nothing ran. Degrading to a
        # launch without the forwarded PATH is the defect `detach_argv` refuses for (task 7.564).
        return "REFUSED", f"the detach pre-flight refused: {exc}"
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return "BROKE", f"`{name}` did not launch: {type(exc).__name__}: {exc}"
    if code != 0:
        return "BROKE", (f"the launcher exited {code}" + (f"; {out.splitlines()[-1][:160]}"
                                                          if out.strip() else ""))
    return "FIRED", (f"unit {launched_unit}" if launched_unit else
                     "no `systemd-run` on this PATH — started as a bare detached child, which "
                     "does NOT outlive a fired job and is the shell-run fallback only") \
        + (f"; {out.splitlines()[-1][:160]}" if out.strip() else "")


# ---- THE ROOM'S SESSION, for the sensor's own `ensure` (task 7.561).

def remember_session(state, snap):
    """Bank the room's session name from the SENSOR'S OWN snapshot. Called on EVERY pass.

    ⚠ EVERY pass, not only the flagging ones, and that is the whole point: the arm that NEEDS
    the name is the one with NO readable snapshot to take it from. Banking it inside the fix
    builder would bank it only on passes that already flagged — i.e. never before the outage.
    `_`-prefixed keys survive the end-of-pass state sweep, so ONE good snapshot ever is enough.
    """
    name = ((snap or {}).get("session") or "").strip()
    if name:
        state["_session"] = name


def sensor_ensure(args, state):
    """The ONE argv tail for the sensor's idempotent `ensure` — WITH the room's session.

    ⚠ WHY A SESSION IS PASSED AT ALL — this is the whole of task 7.561. team-monitor's
    `resolve_session` takes an explicit `--session` first and otherwise asks the ROSTER for a
    pane that still resolves to a live tmux session; with none it REFUSES (`SessionUnresolved`,
    `G-296`). A room whose sensor has died and whose roster panes are all gone IS that state, so
    the sessionless `ensure` this row used to build could not start a sensor in precisely the
    state the row exists to recover from. Measured on the live run-3 package: 432 roster seats,
    408 carrying a pane cell, 0 resolving.

    ⚠ REMEMBERED, NEVER DERIVED. The name comes from `state.json`'s own `session` field — the
    room has exactly one and team-monitor writes it — which is the SAME source `watch.py`'s
    revival anchor already reads ("THE SNAPSHOT SUPPLIES THE SESSION, NOT tmux"). Deriving a
    name from the goal-folder path is what `G-296` outlawed after four auto-ensures ran a room
    unobserved behind a log that read healthy. With no name banked the tail is UNCHANGED — the
    row degrades to exactly today's behaviour rather than inventing one.

    Both call sites render the remedy TEXT from this same list, so what the leader is told to
    run and what the job actually runs cannot drift apart."""
    name = (state.get("_session") or "").strip()
    return ["ensure", "--package", str(args.package)] + (["--session", name] if name else [])


def sensor_ensure_text(team_monitor, tail):
    """The leader-facing REMEDY TEXT for the argv `sensor_ensure` just returned (task 7.578).

    ⚠ THE TEXT PATH ONLY. The exec path hands `tail` to `run_inline` as LIST-ARGV with no shell,
    so it is already correct and quoting it there would corrupt a literal argv value. What is
    unsafe is this string: a leader — or, foreseeably, an AGENT acting on a leader-addressed flag
    — PASTES it into a shell, so a session name of `room; touch /tmp/PWNED` renders as TWO
    commands and a name carrying a newline splits across lines.

    ⚠ RENDERED FROM THE SAME LIST, and that property is why this is a FUNCTION rather than a
    quote added at each call site: both remedy strings pass the very `tail` object they hand to
    `fix=`, so the coached text and the executed argv cannot drift apart (task 7.561), and a
    second copy of the string cannot go unquoted while this one is fixed.

    `shlex.join` quotes each element only when it needs quoting, so a legitimate session name
    renders byte-identically to the pre-fix text."""
    return "python3 " + shlex.join([str(team_monitor)] + list(tail))


def coord_text(coord, package, *tail):
    """The leader-facing REMEDY TEXT for a `coord.py` invocation — the ONE renderer every
    `coord.py` remedy in `evaluate` is built on (task 7.590; `*tail` added by task 7.601).

    ⚠ THE TEXT PATH ONLY, exactly as `sensor_ensure_text` above, and for the same reason. The
    package reaches the EXEC path as list-argv (`sensor_ensure` -> `fix=` -> `run_inline`, no
    shell), where a quote would be handed to the program as a literal character. What is unsafe
    is this string: a leader — or an agent acting on a leader-addressed flag — PASTES it, so a
    package path or a `--coord` path carrying a space renders as extra operands and one carrying
    `;` renders as a second command.

    ONE renderer, and that is why this is a function rather than a quote at each site: NINE remedy
    strings in `evaluate` are built from its return value (counted off this file's own AST, task
    7.601 — the 7.590 docstring said TEN), so a second copy cannot go unquoted while this one is
    fixed (the 7.561 property). `shlex.join` quotes only what needs quoting, so an ordinary path
    renders byte-identically to the pre-fix text.

    ⚠ `*tail` IS THE 7.601 FIX, and it exists because the prefix alone was only half the defect:
    SEVEN of those nine remedy strings appended a SEAT NAME — taken off the snapshot, which no
    code anywhere validates the characters of (swept by symbol, task 7.601) — by f-string
    interpolation, so a seat called `a; touch /tmp/PWNED` rendered as two commands in a line a
    leader PASTES. Passing the subcommand and its operands THROUGH here quotes them by the same
    one mechanism instead of adding a `shlex.quote` at seven call sites, any one of which could
    later be forgotten. A remedy that is prose + command concatenates the prose to this call's
    return value; the prose never goes through `shlex.join`, which would quote its punctuation."""
    return "python3 " + shlex.join([str(coord), "--package", str(package)]
                                   + [str(t) for t in tail])


def worktree_flow_text(flow, goal_name):
    """The leader-facing REMEDY TEXT for the worktree sweep (task 7.590). Text path only —
    nothing execs this line; `worktree_leftovers` runs its own list-argv git calls, and the goal
    name reaching this string comes off a path the operator supplied."""
    return "python3 " + shlex.join([str(flow), "list", "--goal", str(goal_name)])


# ---------------------------------------------------------------- snapshot

def read_snapshot(path):
    """The job's ONLY input. Any failure to read it is treated as a sensor incident."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except FileNotFoundError:
        return None, f"snapshot ABSENT at {path}"
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"snapshot UNREADABLE at {path}: {exc}"


def harness_of(seat_row):
    """The harness the SNAPSHOT reports, which is empty once the process is gone."""
    return seat_row.get("harness") or ""


def declared_harnesses(package):
    """seat -> declared harness, from the run's `taskforce.csv`. Declaration, not sensing.

    Last row for a seat wins, matching how the run's own roster resolution reads it."""
    path = Path(package) / "taskforce.csv"
    out = {}
    try:
        import csv
        with open(path, "r", encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                seat = (row.get("seat") or "").strip()
                if seat:
                    out[seat] = (row.get("harness") or "").strip()
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        pass
    return out


def snapshot_age_s(snap, now):
    ts = snap.get("captured_at")
    if not isinstance(ts, (int, float)):
        return None
    return now - float(ts)


# ---------------------------------------------------------------- dedup state

def load_state(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            d = json.load(fh)
            return d if isinstance(d, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_state(path, state):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, sort_keys=True)
    os.replace(tmp, path)


# ---------------------------------------------------------------- decisions

def revival_ladder(state, seat):
    """SPEND one rung of the revival attempt ladder for `seat`. `(allowed, attempt, cap)`.

    PURE over `state` (it mutates the dict it is handed and reads nothing else), so the bound is
    measurable without firing anything — a probe that had to drive the real fire to score a
    counter would start a real transient unit. `allowed` is False once the cap is reached, and the
    counter is NOT advanced past it: an abandoned seat reports the same numbers every pass instead
    of climbing forever.

    The counter lives under a `_`-prefixed key, which is what survives the end-of-pass sweep."""
    spent = dict(state.get("_revival_attempts") or {})
    attempt = spent.get(seat, 0)
    cap = len(REVIVAL_ATTEMPTS)
    if attempt >= cap:
        return False, attempt, cap
    spent[seat] = attempt + 1
    state["_revival_attempts"] = spent
    return True, attempt, cap


def prune_revival_attempts(state, subjects):
    """Drop the spent attempts of every seat no longer asking to be revived — the ladder bounds
    ONE episode, never the seat's whole life. Same pruning idiom as `_undelivered` below."""
    state["_revival_attempts"] = {k: v for k, v in (state.get("_revival_attempts") or {}).items()
                                  if k in subjects}


def decision(cls, subject, action, detail, remedy="", nudge="leader", fix=None):
    """One element of the comparison object the shadow window scores (m2 shape §7.1).

    `cls` is the vocabulary class; `action` is what the layer says to DO. Two layers agree
    when they produce the same (class, subject, action), never when they agree on a reading.

    `nudge` is CMP-21's RECIPIENT CLASS and it is per-decision, never per-pass — `"seat"`
    addresses the subject seat itself, `"leader"` the leader, `""` nobody (a reported row).
    One recipient for a whole pass was the old shape and it cannot express the seat half of
    the chain at all: a quiet seat's flag went to a third party who could only relay it.

    `fix` is `(script, [argv-tail])` for a row whose repair is MECHANICAL — run by the caller
    through `run_inline`, and only under `--notify`. It is built here and executed nowhere in
    this function, which is what keeps `evaluate` pure and a dry pass genuinely dry."""
    return {"class": cls, "subject": subject, "action": action,
            "detail": detail, "remedy": remedy, "nudge": nudge, "fix": fix}


# ---------------------------------------------------------------- shadow backstop

def declared_dispositions(args, seats):
    """seat -> DURABLE check-out disposition, from the run's own `sessions.csv`. Declaration,
    not sensing — the run's record of what a seat said on the way out.

    ONE READER, and it is `coord.session_disposition`, imported from the `--coord` path this job
    already requires. A second implementation here would be free to disagree with coord's own
    asymmetry — `None` means UNKNOWN and NEVER means `done` — and a disagreement about whether a
    seat checked out cleanly is the whole decision this arm makes.

    An unreadable trace yields UNKNOWN for every seat, which decides WOULD-ENQUEUE. That is the
    conservative direction and it is deliberate: the backstop exists for the seat that did NOT
    check out, so an absent record must never read as a clean one."""
    try:
        sys.path.insert(0, str(Path(args.coord).resolve().parent))
        import coord  # noqa: E402 — the trace's single reader; see this docstring
        pkg = Path(args.package)
        return {s: coord.session_disposition(pkg, s) for s in seats}
    except Exception:                                             # noqa: BLE001
        return {s: None for s in seats}


def declared_door_seats(args):
    """The seats whose pane is a DOOR to a human role — those declaring `relays:` in their OWN
    seat descriptor. Declaration, not sensing: a descriptor is a file the run wrote about itself.

    ONE READER, and it is `coord.inbox_decls`, imported from the `--coord` path this job already
    requires — the same single-reader discipline `declared_dispositions` above states, and for a
    sharper reason: `relays:` already has exactly one derivation, which the kit's reap exemption
    and its revival door gate both read. A second parse here would be free to disagree with them
    about which panes are doors, and a disagreement about that is a run severing its own owner
    channel (G-159, and G-176 for what the disagreement costs).

    An unreadable descriptor set yields an EMPTY door set, which is today's behaviour: every seat
    is treated as a worker's seat. That is the LOUD direction rather than the safe one, and it is
    chosen deliberately — the alternative (treat everything as a door on a read failure) would
    silently mute every GHOSTROW and QUIET remedy in the run off one unreadable file."""
    try:
        sys.path.insert(0, str(Path(args.coord).resolve().parent))
        import coord  # noqa: E402 — the `relays:` derivation's single reader; see this docstring
        ns = argparse.Namespace(package=str(args.package), base=None, workers_dir=None)
        return {a for a, d in (coord.inbox_decls(ns) or {}).items() if d.get("relays")}
    except Exception:                                             # noqa: BLE001
        return set()


def shadow_decide(disposition):
    """PURE. (decision, why) — the would-be FAILURE-MODE enqueue, COMPUTED, never performed.

    This function is the detection predicate's decision half and it is the thing a C-3 red arm
    mutates: with it neutered the trail goes silent, which is what proves the trail is driven by
    the reading rather than by the pass happening at all."""
    if disposition == CLEAN_CHECKOUT:
        return "WOULD-NOT-ENQUEUE", (
            f"durable disposition is `{CLEAN_CHECKOUT}` — this seat checked out CLEANLY, so the "
            f"check-out fast path already advanced its edges. The backstop is the backstop TO "
            f"that path and has nothing to do here.")
    shown = "UNKNOWN (no ended row, no disposition column, or an empty cell)" \
        if disposition is None else f"`{disposition}`"
    return "WOULD-ENQUEUE", (
        f"the seat is out of the room and its durable disposition is {shown} — NOT "
        f"`{CLEAN_CHECKOUT}`. UNKNOWN is never read as clean (coord's own asymmetry), and "
        f"`renew`/`revive`/`exited` each name a seat that has NOT finished. This is the "
        f"finished-or-dead-WITHOUT-clean-check-out condition CMP-21's backstop row keys on.")


def shadow_record(seat, cls, pane, disposition, decision, why, snap):
    """One probe-trail record. THREE FIELDS by contract — the inputs read, the decision reached,
    and the act NOT taken — plus enough identity to compare it against a predicted decision.

    `act_not_taken` is the module constant and is written by no other expression: there is no
    code path here that can put a PERFORMED act in a record, because nothing here performs one."""
    return {
        "layer": "goal-watcher-job/shadow-backstop",
        "subject": seat,
        "captured_at_iso": snap.get("captured_at_iso"),
        "inputs_read": {
            "snapshot.roster_absent": {"seat": seat, "pane": pane, "class": cls},
            "sessions.csv:session_disposition": disposition,
        },
        "decision": decision,
        "decision_why": why,
        "act_not_taken": BARRED_ACT,
    }


def append_trail(path, records):
    """Append this pass's records, then trim to the last SHADOW_TRAIL_KEEP. Returns the count."""
    if not records:
        return 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, sort_keys=True) + "\n")
    # ponytail: trim by read-and-rewrite, which is fine against a 500-line cap. Real rotation
    # belongs here only if the trail ever outgrows one file.
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return len(records)
    if len(lines) > SHADOW_TRAIL_KEEP:
        tmp = f"{path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines[-SHADOW_TRAIL_KEEP:]) + "\n")
        os.replace(tmp, path)
    return len(records)


# ---------------------------------------------------------------- run stall

def headless_live(snap):
    """(count, why) — executors occupying work with NO PANE, from this same snapshot.

    `run.live_executors` counts live PANED seats only, and says so; a HEADLESS execution has no
    pane and is invisible to it. A stall predicate reading only that term therefore fires DURING
    A HEALTHY HEADLESS WINDOW, which is a false alarm on the one row whose whole value is that
    it is believed.

    NON-TERMINALITY IS READ OFF THE ROW'S OWN `outcome`, NOT off a copy of the sensor's status
    enum: team-monitor sets `outcome` to a dict exactly when the row's status is terminal and to
    `null` otherwise, so `outcome is None` IS "this executor is still occupying work" in the
    sensor's own words. A second spelling of that enum here would be free to drift from it.

    An UNREADABLE source is `None`, never 0 — the same discipline CMP-20 applies to the run
    block's own terms, and for the same reason: a 0 standing in for "unknown" satisfies a third
    of the stall predicate with a fabrication.

    THE VIEW ITSELF IS BOUNDED (task 7.556). `snap['headless']` is not every headless row this
    run ever had — team-monitor's `headless()` ages a row out of it once it is older than
    `HEADLESS_WINDOW_S` AND beyond its `(job_id, seat)` group's `HEADLESS_KEEP` newest, and
    counts every one it drops into `source['retention_dropped']` (the closure guarantee:
    `scoped == emitted + retention_dropped + unattributed`). A row aged out this way is
    UNOBSERVED, not absent — counting only what remains in view would silently undercount a
    long-lived seat on a repeatedly-fired periodic job with total confidence. So `retention_dropped`
    is READ here (never recomputed — `headless()` already counted it) and, exactly like an
    unreadable source, turns the count `None` rather than trusting a view known to be short a row.

    A source with NO `retention_dropped` key is read as 0, not as unknown — deliberately, unlike
    every other term this file guards with the null-never-0 rule. `headless()` ITSELF always
    carries the key (it is set at the top of its `source` dict before any row is scored), so a
    missing key can only mean a fixture built before this field existed, never a live run; five
    such fixtures already ship in this repo's own probe suite (`headless_source` sans
    `retention_dropped`), each asserting an UNRELATED contract via a `run_stall` decision this
    field must not silently swallow. Reading the true absent-VALUE case as 0 keeps those probes'
    coverage intact; reading a REAL, POSITIVE `retention_dropped` as unknown — the case that can
    actually happen against live data — is the whole of what task 7.556 asked for."""
    src = snap.get("headless_source")
    if not isinstance(src, dict):
        return None, "snapshot carries no headless_source (older sensor)"
    if not src.get("readable"):
        return None, (src.get("reason") or "headless[] source not readable")
    dropped = src.get("retention_dropped") or 0
    if dropped > 0:
        return None, (f"{dropped} headless row(s) aged out of the view for this run "
                       f"(retention_dropped={dropped}) — the live count would undercount")
    return sum(1 for r in (snap.get("headless") or []) if r.get("outcome") is None), ""


def run_stall(snap, args):
    """CMP-21 invariant 5 — [decision] or []. DETECTION ONLY: launching is the edge-runner's.

    Ready DAG rows with zero live executors and nothing queued is a stalled RUN even though
    every individual seat row looks clean — the contradiction no per-seat threshold can see.
    All four terms come from the SNAPSHOT (invariant 1); none is computed here.

    ⚠ THE PREDICATE IS EVALUATED ONLY WHEN EVERY TERM IS KNOWN. `ready_rows`, `queued` and the
    headless count are each `null` when the sensor could not read their source, and every null
    biases the predicate TOWARD firing — so an unreadable term would turn a sensor failure into
    a stall alarm. Undecidable is reported as its own row and never delivered: it is a fact for
    the decision set, and the sensor's own failure already has a row (STALE-SENSOR)."""
    run = snap.get("run")
    if not isinstance(run, dict):
        return [decision("RUN-STALL", "run", "none — UNDECIDABLE: no run block in the snapshot",
                         "this snapshot predates CMP-20's `run` block, so the stall predicate "
                         "has no terms to read. Reported, never delivered.", "", nudge="")]
    ready, live, queued = run.get("ready_rows"), run.get("live_executors"), run.get("queued")
    hl, hl_why = headless_live(snap)
    src = run.get("source") or {}
    unknown = [n for n, v in (("ready_rows", ready), ("live_executors", live),
                              ("queued", queued), ("headless-live", hl)) if v is None]
    if unknown:
        qsrc = src.get("queued") if isinstance(src.get("queued"), dict) else {}
        why = "; ".join(x for x in (src.get("ready_rows") or "", qsrc.get("reason") or "",
                                    hl_why) if x) or "no reason given by the sensor"
        return [decision(
            "RUN-STALL", "run", "none — UNDECIDABLE: " + ", ".join(unknown) + " unreadable",
            f"the stall predicate needs all four terms and {len(unknown)} could not be read "
            f"({why}). A null is NEVER read as 0 here: every null biases this predicate toward "
            f"firing, so an unreadable term would turn a sensor failure into a stall alarm.",
            "", nudge="")]
    if not (ready > 0 and live == 0 and hl == 0 and queued == 0):
        return []
    return [decision(
        "RUN-STALL", "run", "nudge leader: the run is stalled",
        f"{ready} DAG row(s) are READY to be offered, and NOTHING is executing them: "
        f"{live} live paned executor(s), {hl} live headless execution(s), {queued} queued "
        f"row(s) for this goal. Every seat row can look clean while this holds — that is the "
        f"contradiction this row exists to catch. DETECTION ONLY: launching a ready seat is the "
        f"edge-runner's monopoly (CMP-25) and nothing here launches anything.",
        "offer the ready rows, or say why they are not offerable", nudge="leader")]


# ---------------------------------------------------------------- run-close sweep

def worktree_leftovers(room_goal):
    """CMP-21 invariant 8 — the goal's leftover worktrees under `{workspace}/.rbtv/worktrees/`.

    A DIRECTORY READ filtered by `worktree-flow.py`'s own `{repo}--{goal}--{seat}` naming, run
    both when the goal has NO live run (the refusal branch, where "the run closed" is otherwise
    unobservable from where this job stands) and, since task 7.557, once at the start of a
    healthy watch (`report_worktree_leftovers`'s two call sites in `main`) — closing the blind
    spot where leftovers from a run that never hits refusal went unreported. REMOVAL IS NOT
    PERFORMED and is not this file's: `worktree-flow.py` owns it and REFUSES on a dirty tree, and
    a backstop that force-removed a dirty worktree would destroy unmerged work — the opposite of
    a backstop."""
    goal = Path(room_goal).resolve()
    root = goal.parent.parent.parent / ".rbtv" / "worktrees"     # {ws}/.rbtv/goals/<goal>
    try:
        return sorted(p.name for p in root.iterdir()
                      if p.is_dir() and f"--{goal.name}--" in p.name)
    except OSError:
        return []


def report_worktree_leftovers(args):
    """Task 7.557 — the un-cleaned-worktree report BODY, shared by the two call sites so neither
    duplicates it: the refusal branch (below, in `main` — fires every refusal pass, its own
    event) and the healthy-watch-start call site (also in `main`, gated there on a once-per-watch
    state key so this body runs exactly once per watch instead of every cycle). A no-op when
    `--room-goal` was never given — the refusal branch's prior guard, preserved unchanged."""
    if not args.room_goal:
        return
    goal_name = Path(args.room_goal).name
    left = worktree_leftovers(args.room_goal)
    flow = Path(args.coord).resolve().parent / "worktree-flow.py"
    print(f"goal-watcher-job [WORKTREE-SWEEP] {goal_name} — "
          f"{len(left)} leftover worktree(s): {', '.join(left) or '(none)'}")
    if left:
        print(f"  remedy: {worktree_flow_text(flow, goal_name)}   (then merge-seat / "
              f"close-goal — removal REFUSES on a dirty tree and is never forced here)")


# ---------------------------------------------------------------- decisions

def evaluate(snap, args, state, dispositions, now):
    """Snapshot -> (decisions, paused, trail). PURE: reads its arguments and nothing else.

    `dispositions` is the seat -> durable-check-out map the caller read off `sessions.csv`; it is
    a REQUIRED parameter rather than something this function fetches, so the purity above stays
    true and so a caller cannot silently skip the shadow arm by leaving a default in place.

    The third return value is the SHADOW BACKSTOP's probe trail — the records this pass computed
    and did not act on. It was an always-empty `notes` slot before."""
    decisions = []
    trail = []
    coord_cmd = coord_text(args.coord, args.package)

    def coord_seat(*tail):
        """A `coord.py` remedy carrying OPERANDS — every one of which is shell-quoted, because
        the operand is a SEAT NAME off the snapshot (task 7.601). `coord_cmd` above stays for the
        two remedy lines whose operands are literal text: routing those through `shlex.join` too
        would quote the `<seat>` placeholder into `'<seat>'` and rewrite a line that is correct."""
        return coord_text(args.coord, args.package, *tail)

    repeats = state.get("_repeat") or {}
    held = {}          # condition-key -> consecutive passes it has held, THIS pass

    # ---- ROW 5 (FIRST, and it gates every other row): the staleness tripwire.
    tolerance = args.cadence_s * args.tolerance_mult
    age = snapshot_age_s(snap, now)
    if age is None or age > tolerance:
        shown = "unknown" if age is None else f"{age:.0f}s"
        tail = sensor_ensure(args, state)
        decisions.append(decision(
            "STALE-SENSOR", "team-monitor", "inline fix: restart the sensor (idempotent ensure)",
            f"snapshot age {shown} > tolerance {tolerance:.0f}s "
            f"({args.tolerance_mult:g}x the {args.cadence_s:g}s cadence). ENFORCEMENT IS "
            f"PAUSED — no threshold acts off a frozen snapshot, and box{{}} pressure is "
            f"UNOBSERVED for as long as this lasts. The sensor's own `ensure` is idempotent, so "
            f"restarting it is a mechanical fix and not a judgment (CMP-21 invariant 2); only a "
            f"sensor that does NOT come back is the leader's.",
            sensor_ensure_text(args.team_monitor, tail),
            nudge="leader",
            fix=(args.team_monitor, tail)))
        # The shadow arm is gated by the SAME tripwire as every threshold: a would-be decision
        # computed off a frozen snapshot is a would-be decision about a room that no longer
        # exists, and a trail of those is worse than an empty trail.
        return decisions, True, trail

    # ---- ROW 4: the room itself.
    if snap.get("session_alive") is False:
        decisions.append(decision(
            "ROOM-DEAD", snap.get("session", "?"), "nudge leader: the room is gone",
            "the snapshot reports the room's tmux session absent. CMP-21 invariant 7 puts the "
            "recreate-from-launch-profiles + harness-native-resume + ONE re-orient nudge behind "
            "this row, and task 7.71's registered `selfheal-room` job ALREADY OWNS that recovery "
            "and is armed against this room. Running a second recreate here would be two "
            "mechanisms that can disagree about whether a room is dead and both act, so this row "
            "detects and hands off. ⚠ The resume-by-birth-`session_ref` half of invariant 7 is "
            "UNBUILT in that job as of this writing — it recreates rather than resurrects; the "
            "gap is the leader's to route, and is why this row is a nudge and not a `none`.",
            f"{coord_cmd} launch --only <seat> --force --force-memory  (kit fallback)",
            nudge="leader"))

    # ---- ROW 7: box pressure. Continuous, which is the whole reason it exists — the launch
    # gate fires AT LAUNCH and cannot evaluate a rising trend at all.
    box = snap.get("box") or {}
    swap_hist = list(state.get("_swap_history", []))
    swap_now = box.get("swap_used_mb")
    if isinstance(swap_now, (int, float)):
        swap_hist.append(float(swap_now))
        swap_hist = swap_hist[-SWAP_RISE_READS:]
    state["_swap_history"] = swap_hist

    avail = box.get("available_mb")
    cores = box.get("cores") or 4
    load5 = box.get("load5")
    box_flags = []
    if isinstance(avail, (int, float)) and avail < args.mem_floor_mb:
        box_flags.append(f"available {avail:.0f}MB < floor {args.mem_floor_mb}MB")
    if (len(swap_hist) == SWAP_RISE_READS
            and all(b > a for a, b in zip(swap_hist, swap_hist[1:]))):
        box_flags.append(f"swap RISING across {SWAP_RISE_READS} consecutive reads "
                         f"({' -> '.join(f'{v:.0f}' for v in swap_hist)} MB)")
    if isinstance(load5, (int, float)) and load5 >= cores * args.load_per_core:
        box_flags.append(f"load5 {load5} on {cores} cores "
                         f"(>= {cores * args.load_per_core:g})")
    if box_flags:
        decisions.append(decision(
            "BOX", "box", "nudge leader: box pressure, launches already gated at the door",
            "; ".join(box_flags) + ". NEVER an autonomous close — `p-no-seat-closed-for-memory` "
            "stands and no seat is closed to buy headroom, and no working seat is ever killed "
            "(CMP-21 invariant 6). The launch GATE is not re-implemented here: "
            "`coord.launch_gates` already refuses a launch against this same budget.json floor, "
            "so a second gate would be free to disagree with the door that actually stops "
            "launches (PRIN-11). What this row adds is the RISING TREND an at-launch gate "
            "structurally cannot see, handed to the leader with the numbers.",
            "let finishing seats return their own RAM; the launch door refuses new ones "
            "below the run's declared floor",
            nudge="leader"))

    # ---- ROW 8: DECLARED CAPACITY vs the LIVE CENSUS (gap B3, ported from
    # `watch.py:1486 check_budget`, which dies with that file). Thresholding a declared cap
    # against a census is exactly this file's half of R24, and the census input — `state.json`,
    # already this pass's `snap` — is a sensor input it already holds, so NO new sensing arrives
    # with it and the single-sensor invariant is untouched.
    #
    # THREE STATES, CARRIED VERBATIM, and collapsing the third into the first is the exact defect
    # the LOUD branch exists to prevent:
    #   SILENT           no budget.json here — the normal case for every other package;
    #   current          declared and readable and within cap — no row, and the once-per-episode
    #                    arm keeps a steady breach from repeating;
    #   LOUD-unreadable  declared but UNREADABLE — the room has NO capacity signal at all, which
    #                    is NOT the same fact as having declared none. A fail-soft that made a
    #                    wrong path observationally identical to a run with no budget is what hid
    #                    this defect for a whole run.
    # A STALE snapshot never reaches here: ROW 5 returns first, so `census`'s own UNKNOWN-on-stale
    # verdict can never be mistaken for a capacity claim.
    bpath = Path(args.package) / "budget.json"
    if bpath.exists():
        _b, _err = budget_mod._load(str(bpath), "budget.json")
        if _err:
            decisions.append(decision(
                "BUDGET", "room", "nudge leader: the capacity check is DOWN",
                f"a budget.json IS declared at {bpath} but the capacity check cannot run: "
                f"{_err}. THE ROOM HAS NO CAPACITY SIGNAL UNTIL THIS IS FIXED — treat it as the "
                f"check being down, never as the room being within budget. Silence from this "
                f"check is not a green.",
                f"repair or remove {bpath}", nudge="leader"))
        else:
            _c = budget_mod.census(_b, snap, now)
            if _c["verdict"] == "BREACH":
                decisions.append(decision(
                    "BUDGET", "room", "nudge leader: ROOM OVER CAPACITY",
                    f"{_c['in_use']} agent panes live against a declared cap of {_c['cap']} "
                    f"({-_c['headroom']} over)"
                    + ("" if _c["complete"] else "; INCOMPLETE — unclassified seats") +
                    ". The cap is in budget.json with its ruling; if the cap is what is wrong, "
                    "change it THERE rather than working around it, or the number goes back to "
                    "being folklore. NO SEAT IS CLOSED FOR THIS: report and judge "
                    "(`p-no-seat-closed-for-memory`, CMP-21 invariant 6).",
                    "raise the cap in budget.json with its reason, or let finishing seats leave",
                    nudge="leader"))

    # ---- ROW 6: GHOSTROW / COMPLETED / DEAD, driven from `roster_absent` — team-monitor's
    # own designated GHOSTROW input, which already separates the two failures that look alike
    # from a distance: a pane that LEFT the room, and a pane still there holding no harness.
    standby = set(args.standby or [])
    one_shot = set(args.one_shot_harness or [])
    # Read ONCE in `main` off the seat descriptors and passed in on `args`, exactly as `--standby`
    # and `--one-shot-harness` are — so `evaluate` stays PURE and a fixture can declare a door
    # without a package on disk.
    doors = set(getattr(args, "door_seats", None) or ())
    declared = declared_harnesses(args.package)
    absent = {}
    for r in snap.get("roster_absent") or []:
        name = r.get("seat") or "?"
        pane = r.get("pane") or "?"
        absent[name] = True
        harness = declared.get(name, "")

        # ---- THE SHADOW BACKSTOP (CMP-21's enqueue row, task 7.430). A `roster_absent` row IS
        # the finished-or-dead half of the detection condition; the durable disposition is the
        # WITHOUT-CLEAN-CHECK-OUT half. The would-be act is COMPUTED here and performed nowhere.
        #
        # The NEGATIVE is recorded too, and deliberately: a trail carrying only WOULD-ENQUEUE
        # rows cannot be told apart from a trail that is blind, and telling those apart is the
        # entire point of the comparison the window runs against the predicted decisions.
        s_cls = "DEAD" if r.get("liveness") == "absent" else (
            "COMPLETED" if harness and harness in one_shot else "GHOSTROW")
        s_disp = dispositions.get(name)
        s_decision, s_why = shadow_decide(s_disp)
        trail.append(shadow_record(name, s_cls, pane, s_disp, s_decision, s_why, snap))
        decisions.append(decision(
            "SHADOW-BACKSTOP", name, f"none — SHADOW: {s_decision}, the act is NOT taken",
            f"{s_why} Trail record emitted; no enqueue, to any queue, under any name. Trail "
            f"greens never ripen into authority — the real act needs a fresh OWNER-CLASS "
            f"authorization through the `master` (rider 1 of `p-756-edge-consumption-true`).",
            ""))

        if r.get("liveness") == "absent":
            decisions.append(decision(
                "DEAD", name, "nudge leader: pane gone",
                f"roster row ACTIVE but pane {pane} is not in the room — wakes cannot reach "
                f"it, so the SEAT is not a reachable recipient for its own flag. "
                f"{r.get('reason', '')}".strip(),
                coord_seat("close-seat", name, "--no-export") + "   (or relaunch)",
                nudge="leader"))
        elif harness and harness in one_shot:
            # G-76. `opencode run` executes, prints, exits — for this harness a vanished
            # process is the SUCCESS path, and the remedy is the OPPOSITE of a ghost's.
            decisions.append(decision(
                "COMPLETED", name, "nudge leader: close the finished one-shot",
                f"pane {pane} holds no process and this seat is bound to `{harness}`, a "
                f"ONE-SHOT harness: it executed, printed and exited. Read the seat's LAST "
                f"MESSAGE before acting — the message says whether work was delivered; the "
                f"process cannot. Close, do not renew. The close is LIFECYCLE and stays the "
                f"leader's; nothing here closes a seat.",
                coord_seat("close-seat", name),
                nudge="leader"))
        else:
            # ---- THE DEBOUNCE. One reading cannot tell a ghost from a harness mid-restart, and
            # the once-per-episode `armed` dedup suppresses REPEATS rather than the FIRST reading
            # — which is the one that fired on the owner's door. See the docstring section.
            n = repeats.get(f"ghost:{name}", 0) + 1
            held[f"ghost:{name}"] = n
            ghost_why = (
                f"roster row ACTIVE but pane {pane} runs NO harness process"
                + (f" (declared harness `{harness}`)" if harness else
                   " (no declared harness in taskforce.csv — classed conservatively as a "
                   "ghost, which asks for inspection rather than a close)"))
            if n < GHOSTROW_DEBOUNCE_PASSES:
                # ⚠ EMITTED EVERY PASS, not swallowed: a condition being debounced must never
                # look like a condition gone quiet, or the debounce reads as a mute to anyone
                # watching the decision set. REPORTED, never delivered (`nudge=""`, action
                # `none`) — the same suppression STANDBY already relies on.
                decisions.append(decision(
                    "GHOSTROW-PENDING", name,
                    f"none — DEBOUNCED: reading {n} of {GHOSTROW_DEBOUNCE_PASSES}",
                    ghost_why + f". ONE reading is indistinguishable from a harness mid-restart "
                    f"or a pane read inside a relaunch's startup window, so this is held for "
                    f"{GHOSTROW_DEBOUNCE_PASSES} consecutive readings before anyone is woken. A "
                    f"healthy reading clears the count; a STALE snapshot freezes it.",
                    "", nudge=""))
            elif name in doors:
                decisions.append(decision(
                    "GHOSTROW", name,
                    "nudge leader: quiet DOOR — LOOK, do not close, reap or renew",
                    ghost_why + f", held for {n} consecutive readings — AND this seat declares "
                    f"`relays:`, so its pane is a DOOR to a human role and not a worker's seat. "
                    f"A PARKED DOOR MATCHES THIS SHAPE BY DESIGN.",
                    DOOR_REMEDY, nudge="leader"))
            else:
                # ---- THE REVIVAL ROW (task 7.662). ADDITIVE: the GHOSTROW flag is emitted
                # UNCHANGED and the leader still gets it. What the second row adds is the ACT —
                # the deterministic actuator this job inherited from `watch.py`. It hangs off
                # this same branch rather than re-deriving the condition, so the debounce and
                # the DOOR exemption gate it for free (a door never reaches here at all).
                target, why_t = revival_target(r, snap)
                caller = getattr(args, "caller_ident", None)
                # ⚠ A REVIVAL NOT FIRED IS SAID OUT LOUD, on the flag the leader already gets.
                # A silent non-fire is indistinguishable from a fire that worked, and the whole
                # reason `fire_revival` had four outcomes rather than a boolean is that the
                # difference decides whether a human has to do something.
                no_fire = ("" if (target and caller) else
                           " NO REVIVAL WAS FIRED: " + (
                               why_t if not target else
                               "this pass cannot read its own /proc stat, so it has no "
                               "(pid, starttime) pair to hand the executor as "
                               "`--caller-pid`/`--caller-starttime`; a pid alone is not an "
                               "identity, so the revival refuses rather than inventing one."))
                decisions.append(decision(
                    "GHOSTROW", name, "nudge leader: ghost roster row",
                    ghost_why + f", held for {n} consecutive readings. Its work is stopped and "
                    f"every wake sent to it is typed into a bare shell." + no_fire,
                    "inspect, then relaunch or close: "
                    + coord_seat("close-seat", name, "--renew"),
                    nudge="leader"))
                if target and caller:
                    decisions.append(decision(
                        REVIVAL_CLASS, name,
                        "inline mechanical fix: revive the seat (DETACHED lifecycle-exec)",
                        f"{ghost_why}, held for {n} consecutive readings — and this seat is NOT "
                        f"a door, so the deterministic revival applies. A DETACHED exec of "
                        f"coord.py's `lifecycle-exec --disposition revive` is fired from here "
                        f"and NO AGENT IS IN THE PATH: it never sends a prompt, never asks a "
                        f"seat to act, and it is an INLINE MECHANICAL FIX in exactly the sense "
                        f"the sensor restart and the reap confirmation are "
                        f"(`decisions.md#d-seat-revival-kept-in-watcher-job`, narrowing "
                        f"`d-watcher-deterministic-chain`; `r-leader-revival-is-deterministic` "
                        f"survives and is the binding condition this row keys on). TARGET: "
                        f"{why_t}.",
                        "WATCH the pane — a successor is being launched into it. Its evidence is "
                        "the transient unit's journal and the seat's own lifecycle marker, which "
                        "the executor stamps as its first act. Act by hand only if the fix line "
                        "below this one reports it did not fire.",
                        nudge="leader",
                        fix=(args.coord, revival_argv(
                            args, name, str(r.get("pane") or "").strip(), target, caller))))

    # ---- ROWS 1/2/3 + REAP: per-seat.
    reapable = []
    for s in snap.get("seats") or []:
        name = s.get("seat") or ""
        pane = s.get("pane") or "?"
        if not name:
            # A launched-but-silent pane: team-monitor reports it as a real state and never
            # guesses a name. Nothing here can be keyed to a seat, so nothing is decided.
            continue
        if name in absent:
            continue

        # ---- THE REAP ROW (CMP-21 invariant 6), and it lives BEFORE the roster_active skip
        # because it is the only row about a seat whose roster row is DONE. Three conditions,
        # and the third is what keeps it deterministic: a roster row that is no longer active,
        # a pane still LIVE (still holding the memory), and a DURABLE `done` disposition off
        # sessions.csv. Without the third, a seat that was launched and never checked in reads
        # identically to one that finished — both carry `roster_active: false` — and reaping
        # the first would kill a starting seat. The disposition is read through the SAME single
        # reader the shadow arm uses, so the two arms cannot disagree about what `done` means.
        if s.get("roster_active") is False:
            if s.get("liveness") == "live" and dispositions.get(name) == CLEAN_CHECKOUT:
                reapable.append(f"{name} ({pane})")
            continue
        if not s.get("roster_active"):
            continue

        # ROWS 1/2/3 are evaluated INDEPENDENTLY — no early exit between them. A seat can be
        # gated AND quiet AND past its context threshold at once, and the kit layer emits all
        # three. An early `continue` here would suppress the later classes and the shadow
        # window would score the suppression as agreement, which is the exact silence-reads-
        # as-agreement failure the comparison method exists to prevent.
        #
        # ROW 1: the approval gate is reported FIRST because it EXPLAINS quiet — a gated pane
        # is frozen, so it trips the quiet threshold with a remedy that is wrong for a seat
        # waiting on one keypress.
        if s.get("prompt_pending"):
            decisions.append(decision(
                "APPROVAL", name, "nudge leader: non-allowlisted prompt residue",
                f"pane {pane} is parked on an interactive approval prompt — it is frozen "
                f"until someone answers, and a wake typed into it lands in the modal. "
                f"⚠ CMP-21 invariant 4 splits this row: allowlisted residue is answered "
                f"DETERMINISTICALLY here and only the rest is the leader's. THE ALLOWLIST HALF "
                f"IS NOT BUILT, and the reason is a snapshot bound rather than an omission: "
                f"CMP-20 carries `prompt_pending` as a BOOLEAN and no prompt identity, so from "
                f"`state.json` alone — invariant 1, the only input this job has — no prompt can "
                f"be matched against any allowlist. Every prompt is therefore non-allowlisted "
                f"residue by construction, which is the SAFE arm of the split. Answering one "
                f"needs CMP-20 to carry the prompt's identity first.",
                "inspect the pane, then: " + coord_seat("approve", name),
                nudge="leader"))

        # ROW 2: quiet. G-68 — a standby seat's correct state is WAITING.
        age_s = s.get("last_activity_age_s")
        if isinstance(age_s, (int, float)) and age_s >= args.quiet_min * 60:
            mins = int(age_s // 60)
            if name in standby:
                decisions.append(decision(
                    "STANDBY", name, "none — correct state is WAITING",
                    f"quiet {mins}min, and this seat is declared STANDBY: waiting IS its "
                    f"correct state. Reported so it is visible, never flagged — an alarm that "
                    f"fires on correct behaviour trains the reader to wave off the real one.",
                    "", nudge=""))
            elif name in doors:
                # THE DOOR EXEMPTION at the inactivity row (kit map B13 — the same gap as B9).
                # ⚠ NOT SUPPRESSED and NOT LADDERED: the escalation ladder exists to nudge the
                # SEAT and then escalate when the seat does not act, and a door has no agent
                # behind it to act — its every rung would end at `close <name> --renew`, which is
                # the forbidden act. So this row goes straight to the leader, once per episode,
                # with the door remedy and no command in it.
                decisions.append(decision(
                    "QUIET", name, "nudge leader: quiet DOOR — LOOK, do not close",
                    f"no activity for {mins}min (threshold {args.quiet_min}min), and this seat "
                    f"declares `relays:` — its pane is a DOOR to a human role. A door between "
                    f"sessions is byte-identical to a quiet worker under this observation, so "
                    f"quiet here is NOT evidence of a fault.",
                    DOOR_REMEDY, nudge="leader"))
            else:
                # CMP-21 Layout row 3, both halves: the SEAT first (it is the one that can
                # answer), the LEADER only once the seat has been given N consecutive cadences
                # and is still quiet. Two recipients, staged — never one recipient re-notified.
                n = repeats.get(f"quiet:{name}", 0) + 1
                held[f"quiet:{name}"] = n
                if n >= args.escalate_after:
                    decisions.append(decision(
                        "QUIET-ESCALATED", name, "nudge leader: seat still quiet after nudges",
                        f"no activity for {mins}min (threshold {args.quiet_min}min), and this "
                        f"is pass {n} with the condition unbroken — the seat has been nudged "
                        f"and has not moved, so the row is now judgment.",
                        "check it; if hung or done-but-stuck: "
                        + coord_seat("close", name, "--renew"),
                        nudge="leader"))
                else:
                    decisions.append(decision(
                        "QUIET", name, "nudge seat: still there?",
                        f"no activity for {mins}min (threshold {args.quiet_min}min). Pass {n} "
                        f"of {args.escalate_after} before this escalates to the leader.",
                        "if you are working, say so on the log; if you are done, check out",
                        nudge="seat"))

        # ROW 3: context past the seat's OWN refresh threshold (its briefing's `ctx-refresh`,
        # with the job's fallback for a seat that declares none).
        #
        # A ONE-SHOT SEAT IS SKIPPED HERE, and this row is where the omission was found. Renewal
        # presupposes an interactive, renewable seat. A one-shot has exactly one turn: there is
        # no handoff to negotiate, no later turn to protect, and a renew would relaunch work that
        # is already finishing. Flagging it proposes an action nobody should take. G-76 applied
        # to a THIRD row: I had applied it only to GHOSTROW/COMPLETED, and a shadow pass caught
        # `verify-job-mech` (opencode, 62.6% of a 204800 window) being flagged here. The old
        # layer never had this bug because it computes context for claude seats only — an
        # accident of its implementation that happened to be right.
        pct = s.get("ctx_pct")
        threshold = args.context_pct_override or s.get("ctx_refresh") or args.context_pct
        if (declared.get(name, harness_of(s)) in one_shot) and pct is not None:
            continue
        if isinstance(pct, (int, float)) and pct >= threshold:
            amb = " (reading is DIRECTIONAL — issue G-31)" if s.get("ctx_ambiguous") else ""
            # CMP-21 invariant 3. RENEWAL IS THE SEAT'S OWN ACT: it writes its memory, runs the
            # renew command and relaunches itself. The remedy is therefore `checkout --renew`,
            # which coord's own help calls "the SEAT's own act now" — NOT `close <seat> --renew`,
            # which is a THIRD PARTY closing and relaunching someone else. Those are different
            # commands with different actors and the old row handed out the wrong one.
            n = repeats.get(f"ctx:{name}", 0) + 1
            held[f"ctx:{name}"] = n
            if n >= args.escalate_after:
                decisions.append(decision(
                    "CONTEXT-ESCALATED", name, "nudge leader: seat has not renewed",
                    f"context {pct}% >= threshold {threshold}%{amb}, unbroken for {n} passes — "
                    f"the seat has been nudged to renew itself and has not.",
                    "the seat's own act: " + coord_seat("checkout", name, "--renew"),
                    nudge="leader"))
            else:
                decisions.append(decision(
                    "CONTEXT", name, "nudge seat: renew yourself",
                    f"context {pct}% >= threshold {threshold}%{amb}. Renewal is YOUR act and "
                    f"nothing will be spawned to do it for you: write your memory, then run the "
                    f"renew command, then relaunch fresh. Pass {n} of {args.escalate_after} "
                    f"before this escalates to the leader.",
                    coord_seat("checkout", name, "--renew"),
                    nudge="seat"))

    # ---- THE REAP ROW's decision (CMP-21 invariant 6), ONE per pass rather than one per seat:
    # the fix is a single sweep over the run's whole awaiting-close debt, so N identical child
    # processes would be N spellings of one act.
    if reapable:
        decisions.append(decision(
            "REAP", "awaiting-close debt",
            "inline fix: confirm the reap set; nudge leader to free it",
            f"{len(reapable)} cleanly-checked-out seat(s) still hold a LIVE pane and its memory: "
            + ", ".join(sorted(reapable)) +
            ". The kit's own `reap` owns this act and requires TWO confirming passes before it "
            "frees anything — its docstring names a watcher sweeping on its own cadence as how "
            "that is satisfied honestly, and this is that sweep. The pane KILL (`reap --go`) is "
            "role-gated by coord to a leader-class seat, which this job is not, so the "
            "confirmation is performed here and the freeing is the leader's.",
            f"{coord_cmd} reap --go", nudge="leader",
            fix=(args.coord, ["--package", str(args.package), "reap"])))

    # ---- CMP-21 Layout ROW 5 / invariant 5: the RUN stalls even when every seat row is clean.
    decisions.extend(run_stall(snap, args))

    state["_repeat"] = held
    return decisions, False, trail


# ---------------------------------------------------------------- delivery

def recipient_live(snap, name):
    """Is this recipient a LIVE seat, per the ROOM's snapshot? A flag delivered to a dead seat
    is a log line, and the clause is satisfiable while the claim is false without this check."""
    for s in snap.get("seats") or []:
        if s.get("seat") == name:
            return s.get("liveness") == "live" and bool(s.get("harness_pid"))
    return False


def resolve_recipient(room_snap, args, d=None):
    """(recipient, why) for ONE decision — CMP-21's chain, resolved PER ROW, never per pass.

    A `nudge == "seat"` row addresses THE SUBJECT SEAT ITSELF. That is the entire seat half of
    the chain: invariant 3's renewal is the seat's own act, and a quiet seat is the one that can
    answer. The old shape resolved ONE recipient for a whole pass, which cannot express this at
    all — every seat's flag went to a third party who could at best relay it.

    A subject that is not live cannot be nudged, so the row falls through to the leader AND SAYS
    it fell through: a flag that silently becomes someone else's is how a recipient defect hides.

    Resolved from the DELIVERY room's snapshot, which is not necessarily the snapshot being
    thresholded. In production they are the same file — the job watches the room it reports
    into. A probe watching a throwaway package is the case that separates them, and it found
    this: resolving the recipient from the thresholded snapshot made every flag about a
    throwaway target undeliverable, because the recipient does not live in that room. The
    subject of a flag and the addressee of a flag are different things."""
    if d and d.get("nudge") == "seat":
        subject = d.get("subject") or ""
        if recipient_live(room_snap, subject):
            return subject, f"seat '{subject}' is live — nudged DIRECTLY (CMP-21 seat half)"
        fell = f"seat '{subject}' is NOT live — this seat nudge falls through to the leader; "
    else:
        fell = ""
    # A FLAG ABOUT A SEAT IS NEVER SENT TO THAT SEAT FOR JUDGMENT (gap B17, ported from
    # `watch.py:flag_recipient`). The rule is GENERAL rather than a special case for one role: it
    # was FOUND as one — a context warning about the LEADER was delivered to the leader, which
    # holds its own close/renew/approve with no seat above it and an AFK owner — and pointing the
    # flags at any single named seat just moves the hole to that seat. So a judgment row whose
    # SUBJECT is the primary recipient is diverted to the fallback, whichever seat it is about.
    #
    # THE ONE CARVE-OUT, and it is not an exception to the rule: a `nudge == "seat"` row above is
    # an INSTRUCTION TO the seat (invariant 3's renewal is the seat's own act), not a warning ABOUT
    # it handed over for adjudication. It already returned. Everything reaching here is addressed
    # to the leader, which is exactly where the rule bites.
    subject = (d or {}).get("subject") or ""
    divert = bool(subject) and subject == args.to
    if divert and args.fallback_to and args.fallback_to != subject \
            and recipient_live(room_snap, args.fallback_to):
        return args.fallback_to, (f"{fell}this flag is ABOUT '{subject}', which IS the primary "
                                  f"recipient — diverted to '{args.fallback_to}': no seat "
                                  f"adjudicates a warning about itself")
    if recipient_live(room_snap, args.to):
        # ORPHANED is the honest third state: subject, primary and fallback are the same seat, so
        # there is no independent recipient at all. The flag is delivered anyway AND says so — a
        # monitor with nowhere impartial to report must say that, not quietly report to the
        # subject.
        orphan = (" ORPHANED: this flag is ABOUT that seat and no independent recipient exists "
                  "(the fallback is the same seat, or is not live), so it is delivered to its own "
                  "subject and this line is the record of that") if divert else ""
        return args.to, f"{fell}leader seat '{args.to}' is live in the room's snapshot{orphan}"
    if args.fallback_to and recipient_live(room_snap, args.fallback_to):
        return args.fallback_to, (f"{fell}leader seat '{args.to}' is NOT live — escalated to "
                                  f"'{args.fallback_to}'")
    return None, (f"{fell}NO LIVE RECIPIENT: neither '{args.to}' nor "
                  f"'{args.fallback_to or '(none)'}' is live in the room's snapshot")


def deliver(args, to, text):
    """Send through coord so the flag is LOGGED and WAKES the recipient's pane.

    `agent=` is coord's internal identity API (the `--as` equivalent). This job runs outside
    any pane, so no identity contradiction can fire — and it sends under its OWN name rather
    than borrowing a seat's, so the log attributes the flag to the detector that raised it."""
    sys.path.insert(0, str(Path(args.coord).resolve().parent))
    import coord  # noqa: E402
    ns = argparse.Namespace(package=args.room_package, base=None, workers_dir=None,
                            agent=args.send_as, as_agent=None, to=to, message=text,
                            # `note`, NOT `ask`, and the reason is structural rather than
                            # stylistic. An `ask` opens a thread that stays OPEN until someone
                            # answers it with `--re`, and an answer must be addressed to the
                            # SENDER. This job's sender (`goal-watcher-job`) has no roster row,
                            # so coord refuses it as a recipient — the thread has NO POSSIBLE
                            # TERMINUS and accumulates forever in `pending`. Found while trying
                            # to close this job's own probe flags: 13 open asks that nobody,
                            # including their recipient, could ever close.
                            #
                            # `watch.py` does send `ask`, and correctly — it sends AS `watcher`,
                            # a real seat that can be answered. Copying its type without its
                            # identity would have inherited half a design.
                            #
                            # A note still logs the flag and still WAKES the recipient's pane,
                            # which is everything a notify-only job needs.
                            type="note", supersedes=None, re_num=None, file=None,
                            force=False, why=None, pane=None)
    try:
        coord.cmd_send(ns)
        return True, ""
    except SystemExit as exc:
        return False, f"coord refused the send (exit {exc.code})"
    except Exception as exc:                                  # noqa: BLE001
        return False, f"coord send failed: {exc}"


def recently_said(room_package, headline, minutes):
    """Has this exact flag already been said to the room within `minutes`?

    A SECOND dedup, and it exists because the first one is not enough. The per-episode re-arm
    state lives in one file, so any invocation with a different or missing state file re-emits
    everything — which is exactly how two identical GHOSTROW flags reached one recipient from
    one snapshot timestamp during this build's own probes (leader #617; the cause was two
    probes with two state files, deterministic, not a race).

    A notify-only job's entire value is that a human reads its flags, so a job that repeats
    itself trains the room to ignore it — G-68's failure arriving by a different road. This
    check therefore keys on the LOG THE HUMAN ACTUALLY READS rather than on the job's private
    state, and so it survives the private state being lost, reset, or pointed elsewhere.

    Best-effort by design: an unreadable log must never stop a flag from going out. Silence is
    the worse failure of the two."""
    path = Path(room_package) / "coordination" / "messages.md"
    try:
        txt = path.read_text(encoding="utf-8", errors="replace")
    except (FileNotFoundError, OSError):
        return False
    cutoff = time.time() - minutes * 60
    for block in reversed(txt.split("\n## ")[-400:]):
        if headline not in block or "from: goal-watcher-job" not in block:
            continue
        stamp = block.split("| ")[-1].splitlines()[0].strip() if "| " in block else ""
        try:
            when = time.mktime(time.strptime(stamp, "%Y-%m-%d %H:%M"))
        except ValueError:
            continue
        if when >= cutoff:
            return True
    return False


def flag_text(d, snap):
    return (f"goal-watcher-job [{d['class']}] {d['subject']} — {d['action']}\n"
            f"{d['detail']}\n"
            + (f"remedy: {d['remedy']}\n" if d["remedy"] else "")
            + f"(from state.json captured {snap.get('captured_at_iso', '?')}; "
              f"this job reads that snapshot and no raw source)")


# ---------------------------------------------------------------- room target

def resolve_room_package(args):
    """(str, provenance) or (None, refusal) — the run package flags are DELIVERED into.

    THE ROOM IS RESOLVED, NEVER PINNED. The `goal-watcher-throwaway` entry used to carry
    `--room-package .../runs/run-1` for a run closed 2026-07-27, so a fire would have delivered its
    flags into a CLOSED run's package while the job's own status kept reading healthy. Swapping in a
    different run number reproduces that defect at the next run close; the fix is that the entry
    names NO run at all and asks the register instead (task 7.168 / design T9). This is the same
    remedy `recover-room.py:resolve_package()` and `selfheal-watch.py:resolve_package()` already
    carry, deliberately in the same shape — three jobs answering "which run is live" three different
    ways is the defect one level up.

    `--room-package` SURVIVES AS THE EXPLICIT OVERRIDE and wins whenever it is present. That is not
    a compatibility shim: a probe whose flags must NOT reach the live room needs a way to say so,
    and an override that resolves live on being dropped would promote such a probe onto the live run
    silently.

    ⚠ THERE IS NO REGISTER ANY MORE, AND THE ROOM IS THE LEASE (7.607 E3, design-lock item 1).
    Which package is live is DERIVED at fire time from the goal's tmux room and its ancestry-
    verified seats, never from a stored status. `coord.derive_lease()` is the ONE accessor over the
    one home (`server/lease/lease.js`); a second room predicate here would be the same two-readers
    defect a second `runs.csv` parse was. What this replaces was already BROKEN, not merely dated:
    it composed `<goal>/runs/<name>` from `resolve_live_run`'s compat return, and E2b moved the
    layout out from under that path — the flags would have been delivered into a directory that is
    gone, and a flag that reads as delivered and was not is the worst ending this function has.

    `coord` is imported INSIDE this function from the `--coord` path this job already requires, so
    a copy-and-test of this file carries no sibling dependency it does not otherwise need.

    With NEITHER flag the room is the watched package, which is the production case: in production
    the run being watched and the room being told about it are the same run.

    Refusal is FAIL-CLOSED and returns no package: delivering a flag into a room picked by a guess
    on an ambiguous register is worse than not delivering it, because the flag reads as having been
    delivered to whoever can act on it."""
    if args.room_package:
        return args.room_package, "--room-package (explicit override; the lease is not consulted)"
    if not args.room_goal:
        return args.package, "--package (neither --room-package nor --room-goal; room == watched run)"
    sys.path.insert(0, str(Path(args.coord).resolve().parent))
    import coord  # noqa: E402  — the lease's single accessor; see this docstring
    goal = Path(args.room_goal).resolve()
    lease, why = coord.derive_lease(goal)
    if why:
        return None, (f"the lease for {goal.name} is UNREADABLE ({why}). That is IGNORANCE, not an "
                      f"idle goal — refusing rather than reading it as 'nothing is running'.")
    rooms = lease.get("rooms") or []
    if len(rooms) != 1:
        return None, (f"the live lease for {goal.name} names {len(rooms)} rooms and the design "
                      f"rules exactly one (lock item 2): "
                      + ("the goal is NOT EXECUTING, so there is no room to deliver into"
                         if not rooms else
                         "two rooms of one goal is a box state nothing here should resolve"))
    pkg = Path(rooms[0].get("packageDir") or "").resolve()
    return str(pkg), (f"DERIVED from the live lease of {goal.name}: room "
                      f"{rooms[0].get('room')!r} -> {pkg} (no stored status read; lock item 1)")


# ---------------------------------------------------------------- selftest

# The retired role names, spelled ONCE so the grep-proof is an assertion rather than a claim.
#
# ⚠ THE SCAN'S TARGET IS THE BINDING VALUE, NOT THE WORD. A checker that grepped this whole
# file would fire on the docstring that DOCUMENTS the retirement and on this very line — it
# would report the statement of the rule and stay silent about a breach that used a synonym.
# What `d-run-context` actually forbids is code, config or a prompt that WAKES, SPAWNS or FALLS
# BACK TO one of these — so the scan runs over the strings that reach a recipient (every literal
# inside a `decision(...)` call, plus `BARRED_ACT`, which reaches one by name) and over the two
# recipient defaults. Prose explaining the retirement is the record, never the residue.
RETIRED_ROLE_TOKENS = ("chief-of-staff", "closer")


def _ns(**kw):
    base = dict(coord="/nonexistent/coord.py", package="/nonexistent/pkg", cadence_s=20.0,
                tolerance_mult=3.0, team_monitor="/nonexistent/team_monitor.py",
                mem_floor_mb=2000, load_per_core=1.5, standby=[], one_shot_harness=["opencode"],
                quiet_min=30, escalate_after=3, context_pct_override=0, context_pct=50,
                to="leader", fallback_to="", door_seats=set())
    base.update(kw)
    return argparse.Namespace(**base)


def selftest():
    """Assertions over the PURE predicates this file decides with. No package, no room, no I/O.

    It covers the four things a reader cannot verify by reading: the stall predicate's null
    discipline, the headless half of that predicate, the per-decision recipient chain, and the
    seat->leader escalation. Plus the two guards whose failure is silent — `run_inline`'s exec
    allowlist and the retired-role absence."""
    fails = []

    def check(label, cond):
        print(f"  [{'ok ' if cond else 'FAIL'}] {label}")
        if not cond:
            fails.append(label)

    fresh = time.time()
    # `retention_dropped: 0` is part of the emitter's real contract (team_monitor.headless()
    # always sets it — task 7.556): a fixture that omits it would be testing a shape the sensor
    # never actually produces.
    ok_src = {"readable": True, "reason": "", "retention_dropped": 0}

    def snap(ready=1, live=0, queued=0, headless=(), src=None, run=True):
        s = {"captured_at": fresh, "captured_at_iso": "iso", "seats": [], "roster_absent": [],
             "headless": list(headless), "headless_source": dict(src or ok_src)}
        if run:
            s["run"] = {"ready_rows": ready, "live_executors": live, "queued": queued,
                        "source": {"ready_rows": "", "queued": {"reason": ""}}}
        return s

    print("goal-watcher-job --selftest")
    a = _ns()

    # ---- the stall predicate
    d = run_stall(snap(), a)
    check("STALL: ready>0, no paned/headless executor, nothing queued -> nudge leader",
          len(d) == 1 and d[0]["class"] == "RUN-STALL" and d[0]["nudge"] == "leader")
    check("STALL: queued>0 is not a stall", run_stall(snap(queued=1), a) == [])
    check("STALL: a live paned executor is not a stall", run_stall(snap(live=1), a) == [])
    check("STALL: no ready rows is not a stall", run_stall(snap(ready=0), a) == [])
    # THE HEADLESS HALF — the false positive B1's README names, and the reason this row may not
    # read `live_executors` alone: a healthy headless window has zero live PANES.
    check("STALL: a NON-TERMINAL headless row suppresses the stall (no pane, still executing)",
          run_stall(snap(headless=[{"outcome": None}]), a) == [])
    check("STALL: a TERMINAL headless row does NOT suppress it (that executor is finished)",
          len(run_stall(snap(headless=[{"outcome": {"status": "done"}}]), a)) == 1)
    # THE NULL DISCIPLINE — every null biases the predicate toward firing, so none may read as 0.
    for term in ("ready", "queued"):
        d = run_stall(snap(**{term: None}), a)
        check(f"STALL: a null `{term}` is UNDECIDABLE and undelivered, never read as 0",
              len(d) == 1 and d[0]["nudge"] == "" and "UNDECIDABLE" in d[0]["action"])
    d = run_stall(snap(src={"readable": False, "reason": "store unreadable"}), a)
    check("STALL: an unreadable headless source is UNDECIDABLE, never counted as 0",
          len(d) == 1 and d[0]["nudge"] == "" and "UNDECIDABLE" in d[0]["action"])
    d = run_stall(snap(run=False), a)
    check("STALL: a snapshot with no `run` block is UNDECIDABLE, not a stall",
          len(d) == 1 and d[0]["nudge"] == "")
    check("HEADLESS-LIVE: counts non-terminal rows only",
          headless_live(snap(headless=[{"outcome": None}, {"outcome": {}},
                                       {"outcome": None}]))[0] == 2)
    # 7.556 — a row aged out of the view makes the count UNKNOWN, never a number, never 0.
    dropped_src = {"readable": True, "reason": "", "retention_dropped": 1}
    hl_dropped = headless_live(snap(headless=[{"outcome": None}], src=dropped_src))
    check("HEADLESS-LIVE (7.556): retention_dropped > 0 makes the count UNKNOWN, not a number",
          hl_dropped[0] is None and "retention_dropped" in hl_dropped[1])
    missing_src = {"readable": True, "reason": ""}
    check("HEADLESS-LIVE (7.556): a source with no retention_dropped KEY reads as 0, not unknown "
          "(headless() itself always sets the key; a missing key is a pre-7.556 test fixture, "
          "never live data — five of those fixtures ship in this suite and must keep working)",
          headless_live(snap(headless=[{"outcome": None}], src=missing_src))[0] == 1)
    check("HEADLESS-LIVE (7.556): retention_dropped == 0 still returns a real number "
          "(the fix does not degrade every pass to unknown)",
          headless_live(snap(headless=[{"outcome": None}]))[0] == 1)
    # THE FLOW-THROUGH: an aged-out row must not let the stall predicate silently read the
    # unknown headless count as if it were 0 (the "same action as zero" the task criteria name).
    # ready>0, live=0, queued=0 with hl==0 fires RUN-STALL; the SAME shape with a dropped row
    # must instead report UNDECIDABLE — a different action, not a quieter version of the same one.
    d = run_stall(snap(headless=[{"outcome": None}], src=dropped_src), a)
    check("STALL (7.556): a dropped headless row is UNDECIDABLE, never treated as hl==0",
          len(d) == 1 and d[0]["nudge"] == "" and "UNDECIDABLE" in d[0]["action"]
          and "headless-live" in d[0]["action"])

    # ---- the recipient chain
    room = {"seats": [{"seat": "alpha", "liveness": "live", "harness_pid": 7},
                      {"seat": "leader", "liveness": "live", "harness_pid": 9}]}
    seat_row = decision("QUIET", "alpha", "nudge seat", "", nudge="seat")
    check("CHAIN: a seat row is nudged to ITS OWN SEAT",
          resolve_recipient(room, a, seat_row)[0] == "alpha")
    check("CHAIN: a leader row is nudged to the leader",
          resolve_recipient(room, a, decision("BOX", "box", "", ""))[0] == "leader")
    dead = decision("QUIET", "ghost", "nudge seat", "", nudge="seat")
    to, why = resolve_recipient(room, a, dead)
    check("CHAIN: a seat row whose seat is NOT live falls through to the leader AND says so",
          to == "leader" and "falls through" in why)
    check("CHAIN: no live recipient at all is a refusal, not a guess",
          resolve_recipient({"seats": []}, a, seat_row)[0] is None)

    # ---- the seat -> leader escalation
    quiet = {"captured_at": fresh, "captured_at_iso": "iso", "roster_absent": [], "headless": [],
             "headless_source": dict(ok_src),
             "seats": [{"seat": "alpha", "pane": "%1", "roster_active": True, "liveness": "live",
                        "last_activity_age_s": 99999, "ctx_pct": None}]}
    st = {}
    classes = []
    for _ in range(a.escalate_after):
        ds, _p, _t = evaluate(quiet, a, st, {}, fresh)
        classes.append(next(x["class"] for x in ds if x["class"].startswith("QUIET")))
    check(f"ESCALATION: seat first, leader on pass {a.escalate_after} "
          f"({' -> '.join(classes)})",
          classes[0] == "QUIET" and classes[-1] == "QUIET-ESCALATED")
    ds, _p, _t = evaluate(quiet, a, {}, {}, fresh)
    check("ESCALATION: the counter is CONSECUTIVE — a cleared condition starts a new episode",
          next(x["class"] for x in ds if x["class"].startswith("QUIET")) == "QUIET")
    check("CONTEXT: the seat's remedy is its OWN `checkout --renew`, never a third-party close",
          all("checkout" in x["remedy"] for x in evaluate(
              {"captured_at": fresh, "captured_at_iso": "i", "roster_absent": [], "headless": [],
               "headless_source": dict(ok_src),
               "seats": [{"seat": "a", "pane": "%1", "roster_active": True, "liveness": "live",
                          "ctx_pct": 90, "ctx_refresh": 60}]},
              a, {}, {}, fresh)[0] if x["class"].startswith("CONTEXT")))

    # ---- the two guards whose failure is silent
    ok, why = run_inline("/usr/bin/ignite", ["add-job"])
    check("EXEC ALLOWLIST: a program outside INLINE_FIX_SCRIPTS is REFUSED (act identity)",
          ok is False and "REFUSED" in why)
    check("EXEC ALLOWLIST: `ignite` is not on the list", "ignite" not in INLINE_FIX_SCRIPTS)
    # An allowlisted BASENAME is not an allowlisted FILE. The interpreter starts and the missing
    # script is its non-zero exit, so this fails LOUD rather than reading as a fix that ran.
    ok, why = run_inline("/nonexistent/team_monitor.py", ["ensure"])
    check("EXEC ALLOWLIST: an allowlisted basename with no file behind it is NOT a green fix",
          ok is False and "exit 0" not in why)
    # An UNSET operator flag and a REFUSED program are different failures reaching the same
    # leader, and `--team-monitor` defaults to `""` — so the empty path must diagnose ITSELF
    # rather than borrow the act-identity refusal's text.
    ok, why = run_inline("", ["ensure"])
    check(f"EXEC ALLOWLIST: an EMPTY program path says MISSING PATH, not 'not an inline-fix "
          f"program' ({why[:60]}…)",
          ok is False and "MISSING PATH" in why and "not an inline-fix program" not in why)

    # ---- task 7.578: the leader-facing REMEDY TEXT is shell-safe; the ARGV stays raw.
    # ⚠ DRIVEN OFF `evaluate`'s REAL STALE-SENSOR DECISION, never a hand-composed string — the
    # defect is that the remedy a leader PASTES is built by interpolation, so the arm has to
    # measure what that call site actually emits, not what a local re-render would.
    hostile = "room; touch /tmp/PWNED\nsecond --session --help"
    stale = snap()
    stale["captured_at"] = fresh - 10_000
    sd = evaluate(stale, a, {"_session": hostile}, {}, fresh)[0][0]
    argv = list(sd["fix"][1])
    naive = f"python3 {a.team_monitor} {' '.join(argv)}"   # the pre-7.578 rendering, for control
    check("7.578 TEXT PATH: a session name carrying `;` and a newline renders as ONE command — "
          f"the remedy shell-parses back to EXACTLY the argv the fix runs, so the `touch` is a "
          f"quoted WORD and not a second command a paste would execute ({sd['remedy'][-48:]!r})",
          sd["class"] == "STALE-SENSOR"
          and shlex.split(sd["remedy"]) == ["python3", str(a.team_monitor)] + argv)
    # THE CONTROL, and it is what makes the arm above a measurement rather than a restatement:
    # the UNQUOTED rendering this row replaces splits that one word into four and loses the flag
    # boundary entirely. Without this line the arm would pass against the code it exists to fix.
    check("7.578 CONTROL: the pre-fix `' '.join(...)` rendering does NOT survive a shell parse — "
          "it splits the session name into separate words, which is the defect",
          shlex.split(naive) != ["python3", str(a.team_monitor)] + argv)
    check("7.578 EXEC PATH UNCHANGED: the argv element is the RAW name, unquoted — the fix runs "
          "through list-argv with no shell, so a quote added there would be passed to "
          "team-monitor as a literal character",
          argv[-2:] == ["--session", hostile] and sd["fix"][0] == a.team_monitor)
    # A LEGITIMATE NAME STILL RESOLVES, and renders byte-identically to the pre-fix text: quoting
    # that fired on ordinary names would change every remedy line in the run's logs.
    ok_d = evaluate(stale, a, {"_session": "run-3"}, {}, fresh)[0][0]
    check("7.578 (2) a legitimate session name is UNCHANGED in both paths — raw in the argv and "
          "unquoted in the text",
          ok_d["fix"][1][-1] == "run-3"
          and ok_d["remedy"] == f"python3 {a.team_monitor} {' '.join(ok_d['fix'][1])}")
    # ---- task 7.590: the SAME text/exec split, at the TWO sites 7.578's criterion did not word.
    # ⚠ THE PACKAGE ARM IS DRIVEN OFF `evaluate`'s REAL ROOM-DEAD DECISION, never a local
    # re-render — `coord_text` feeds ten remedy strings, and what has to hold is what those call
    # sites emit.
    hostile_pkg = "/tmp/pk g; touch /tmp/PWNED"
    hostile_coord = "/tmp/co ord.py; touch /tmp/PWNED2"
    b = _ns(coord=hostile_coord, package=hostile_pkg)
    dead = snap()
    dead["session_alive"] = False
    rd = next(x for x in evaluate(dead, b, {}, {}, fresh)[0] if x["class"] == "ROOM-DEAD")
    check("7.590 TEXT PATH (package): a `--coord` path and a package path carrying a space and "
          "`;` render as ONE command — the remedy shell-parses back to EXACTLY those operands, so "
          f"both `touch`es are quoted WORDS and not two more commands a paste would execute "
          f"({rd['remedy'][:46]!r}…)",
          shlex.split(rd["remedy"])[:4] == ["python3", hostile_coord, "--package", hostile_pkg])
    # THE CONTROL, and it is what makes the arm above a measurement rather than a restatement:
    # the pre-7.590 interpolation splits those two paths into six words and smuggles in two `;`.
    check("7.590 CONTROL (package): the pre-fix f-string rendering does NOT survive a shell parse",
          shlex.split(f"python3 {hostile_coord} --package {hostile_pkg}")[:4]
          != ["python3", hostile_coord, "--package", hostile_pkg])
    # A LEGITIMATE path still renders byte-identically to the pre-fix text — quoting that fired on
    # ordinary values would rewrite every remedy line in the run's logs.
    check("7.590 (2) an ordinary path is UNCHANGED by the renderer",
          coord_text("/a/coord.py", "/b/pkg") == "python3 /a/coord.py --package /b/pkg")
    check("7.590 EXEC PATH UNCHANGED: the hostile package reaches the fix ARGV raw and unquoted — "
          "`sensor_ensure` hands it to `run_inline` as list-argv with no shell, where a quote "
          "would be passed to team-monitor as a literal character",
          evaluate(dict(snap(), captured_at=fresh - 10_000), b, {"_session": "run-3"}, {},
                   fresh)[0][0]["fix"][1][:3] == ["ensure", "--package", hostile_pkg])
    hostile_goal = "goal; touch /tmp/PWNED"
    hostile_flow = "/tmp/wf low.py"
    check("7.590 TEXT PATH (goal name): the worktree-sweep remedy shell-parses as ONE command "
          "even when the goal directory's name carries a space and `;`",
          shlex.split(worktree_flow_text(hostile_flow, hostile_goal))
          == ["python3", hostile_flow, "list", "--goal", hostile_goal])
    # ⚠ THE ARM ABOVE WOULD PASS AGAINST AN UNUSED RENDERER — an absent call site is the failure,
    # so the call site is asserted too. The forbidden literal is spelled in two halves on purpose:
    # written whole, this very line would be the match and the check would fire on its own
    # statement of the rule.
    src_text = Path(__file__).read_text(encoding="utf-8")
    check("7.590 CALL SITE (goal name): the worktree-sweep line renders THROUGH "
          "`worktree_flow_text`, and no unquoted interpolation of it survives",
          "worktree_flow_text(flow, goal_name)" in src_text
          and ("list --goal {" + "goal_name}") not in src_text)

    # ---- task 7.601: the SAME text/exec split at the SEVEN remedy strings that append a SEAT
    # NAME to the coord prefix. The name comes off the SNAPSHOT and NOTHING validates its
    # characters anywhere on the path (swept by symbol before this was written: no seat-name
    # regex exists in the tree; `coord.validate_seat` validates harness and model, not the name),
    # so `trusted by construction` would rest on nothing.
    # ⚠ EVERY ARM IS DRIVEN OFF `evaluate`'s REAL DECISION, never a local re-render — the defect
    # is what those call sites emit, not what the renderer can do when called correctly.
    hs = "al pha; touch /tmp/PWNED"            # a seat name carrying a space AND a `;`

    def cmd601(*tail):
        return ["python3", hostile_coord, "--package", hostile_pkg] + list(tail)

    def has_run(remedy, exp):
        """Shell-parse the COMMAND HALF of a remedy — from its `python3 ` onward — and assert it
        opens with EXACTLY the operand list `exp`.

        The command half, not the whole line, because four of these seven remedies are prose +
        command and one is command + prose: prose is prose and is not shell input, and one of the
        prefixes ("the seat's own act: ") carries an apostrophe that no shell parse of the whole
        line survives. It remains a ONE-TOKEN-STREAM assertion of everything a paste would run —
        under the pre-fix interpolation the hostile name is FOUR tokens and the prefix mismatches
        at the seat operand."""
        i = remedy.find("python3 ")
        toks = shlex.split(remedy[i:]) if i >= 0 else []
        return toks[:len(exp)] == exp

    def site601(ds, cls, *tail):
        d = next((x for x in ds if x["class"] == cls), None)
        return d is not None and has_run(d["remedy"], cmd601(*tail))

    absent_snap = snap()
    absent_snap["roster_absent"] = [{"seat": hs, "pane": "%1", "liveness": "absent"},
                                    {"seat": hs + "-2", "pane": "%2", "liveness": "live"}]
    # ⚠ TWO PASSES OVER ONE STATE, because GHOSTROW is DEBOUNCED: reading 1 emits
    # GHOSTROW-PENDING and only reading 2 emits the deliverable row whose remedy this arm reads.
    # (DEAD is not debounced and is present on either pass.)
    st_absent = {}
    evaluate(absent_snap, b, st_absent, {}, fresh)
    ads = evaluate(absent_snap, b, st_absent, {}, fresh)[0]
    live_snap = snap()
    live_snap["seats"] = [{"seat": hs, "pane": "%3", "roster_active": True, "liveness": "live",
                           "prompt_pending": True, "last_activity_age_s": 99999,
                           "ctx_pct": 90, "ctx_refresh": 60}]
    st601 = {}
    lds1 = evaluate(live_snap, b, st601, {}, fresh)[0]          # pass 1: seat-addressed rows
    for _ in range(b.escalate_after - 1):
        ldsN = evaluate(live_snap, b, st601, {}, fresh)[0]      # pass N: the escalated rows

    check("7.601 TEXT PATH (DEAD): a seat name carrying a space and `;` renders as ONE shell "
          "token — the remedy parses back to exactly the coord operands, so the `touch` is a "
          "quoted WORD and not a second command a paste would execute",
          site601(ads, "DEAD", "close-seat", hs, "--no-export"))
    check("7.601 TEXT PATH (GHOSTROW): the prose-prefixed remedy still carries ONE shell command",
          site601(ads, "GHOSTROW", "close-seat", hs + "-2", "--renew"))
    check("7.601 TEXT PATH (APPROVAL): the approve remedy carries the seat name as one token",
          site601(lds1, "APPROVAL", "approve", hs))
    check("7.601 TEXT PATH (CONTEXT): the seat's own `checkout --renew` carries it as one token",
          site601(lds1, "CONTEXT", "checkout", hs, "--renew"))
    check("7.601 TEXT PATH (QUIET-ESCALATED): the leader-addressed close carries it as one token",
          site601(ldsN, "QUIET-ESCALATED", "close", hs, "--renew"))
    check("7.601 TEXT PATH (CONTEXT-ESCALATED): the escalated renew carries it as one token",
          site601(ldsN, "CONTEXT-ESCALATED", "checkout", hs, "--renew"))
    # THE CONTROL, and it is what makes the six arms above measurements rather than restatements:
    # the pre-7.601 rendering — the coord PREFIX with the name interpolated after it — splits that
    # one name into FOUR words and smuggles in a `;`. Without this line every arm above would pass
    # against the code they exist to fix.
    check("7.601 CONTROL: the pre-fix `{coord_cmd} <verb> {name}` rendering does NOT survive a "
          "shell parse as one command",
          not has_run(f"{coord_text(hostile_coord, hostile_pkg)} close-seat {hs} --no-export",
                      cmd601("close-seat", hs, "--no-export")))
    # A LEGITIMATE seat name renders byte-identically to the pre-fix text — quoting that fired on
    # ordinary names would rewrite every remedy line in the run's logs.
    check("7.601 (2) an ordinary seat name is UNCHANGED by the renderer",
          coord_text("/a/coord.py", "/b/pkg", "close-seat", "alpha", "--renew")
          == "python3 /a/coord.py --package /b/pkg close-seat alpha --renew")
    # ⚠ THE SIX ARMS ABOVE REACH SIX OF THE SEVEN SITES. `COMPLETED` needs a declared one-shot
    # harness, which only a real `taskforce.csv` under the package supplies, and this selftest has
    # no package — so that site is closed HERE, off the file's own AST, together with any site a
    # future fixture also cannot reach: a remedy f-string that interpolates `coord_cmd` may
    # interpolate NOTHING ELSE. The two survivors are the literal-operand lines (`launch --only
    # <seat>`, `reap --go`). The `>= 2` half is the vacuity guard — a renamed variable would
    # otherwise find zero sites and pass.
    import ast as _ast601
    _t601 = _ast601.parse(src_text)
    coord_fstrings = [n for n in _ast601.walk(_t601) if isinstance(n, _ast601.JoinedStr)
                      and any(isinstance(v, _ast601.FormattedValue)
                              and getattr(v.value, "id", "") == "coord_cmd" for v in n.values)]
    smuggled = [n.lineno for n in coord_fstrings
                if sum(isinstance(v, _ast601.FormattedValue) for v in n.values) > 1]
    check(f"7.601 CENSUS: every remedy f-string built on `coord_cmd` interpolates nothing else "
          f"({len(coord_fstrings)} such f-string(s), smuggled={smuggled})",
          len(coord_fstrings) >= 2 and not smuggled)
    # THE PATH THAT MUST NOT MOVE: the REAP `fix=` this loop emits carries the package RAW and
    # names no seat at all — a quote added there would be handed to coord as a literal character.
    # ⚠ THIS COMMENT READ "no seat name reaches an exec argv at all" UNTIL TASK 7.662, and that
    # was a claim about the two rows that existed rather than about the hazard. The REVIVAL row
    # DOES put a seat name in an exec argv (`--seat`), and it is safe for the reason 7.601 is
    # about in the first place: the hazard is a remedy STRING a leader pastes into a shell, and
    # `revival_argv` is LIST-ARGV with no shell — its own arms below assert both halves. What
    # still holds unchanged, and is what this arm measures, is the REAP row.
    reap_snap = snap()
    reap_snap["seats"] = [{"seat": hs, "pane": "%4", "roster_active": False, "liveness": "live"}]
    rp = next(x for x in evaluate(reap_snap, b, {}, {hs: CLEAN_CHECKOUT}, fresh)[0]
              if x["class"] == "REAP")
    check("7.601 EXEC PATH UNCHANGED: the reap fix argv is raw and unquoted, and no seat name is "
          "smuggled into its remedy",
          rp["fix"] == (b.coord, ["--package", hostile_pkg, "reap"]) and hs not in rp["remedy"])

    # ---- task 7.662: THE REVIVAL ACTUATOR'S NEW HOME. The arms below are the ones a reader
    # cannot verify by reading: that the SECOND exec door is the SAME door, that the target is
    # snapshot-derived and refuses rather than guessing, and that a DOOR is never revived.
    #
    # ⚠ ONE GATE, BOTH DOORS — read off this file's OWN AST, so a future door that grows its own
    # copy of the allowlist check is caught even if every behavioural arm below still passes.
    # The `== 2` half is the vacuity guard: a renamed gate would otherwise find zero callers.
    import ast as _ast662
    _t662 = _ast662.parse(src_text)
    _gate_callers = sorted({fn.name for fn in _ast662.walk(_t662)
                            if isinstance(fn, _ast662.FunctionDef)
                            and any(isinstance(c, _ast662.Call)
                                    and getattr(c.func, "id", "") == "_inline_fix_program"
                                    for c in _ast662.walk(fn))})
    check(f"7.662 ONE GATE: every exec door goes through `_inline_fix_program` and there are "
          f"exactly two of them ({_gate_callers})",
          _gate_callers == ["run_inline", "run_revival"])
    _out, _why = run_revival("/usr/bin/ignite", ["lifecycle-exec"], "unit-never-created")
    check(f"7.662 SAME REFUSAL: the DETACHED door refuses a non-allowlisted program with the "
          f"SAME text the inline door gives, and starts nothing ({_why[:52]}…)",
          _out == "REFUSED" and _why == run_inline("/usr/bin/ignite", ["add-job"])[1])
    check("7.662 ALLOWLIST UNWIDENED: the revival needs no new entry — `coord.py` was already "
          "on it, and the set is still exactly the two programs",
          INLINE_FIX_SCRIPTS == ("team_monitor.py", "coord.py"))

    # ---- the target derivation: snapshot only, and it REFUSES rather than guessing.
    _rev_snap = snap()
    _rev_snap["seats"] = [{"seat": "other", "pane": "%9", "roster_active": True,
                           "liveness": "live"}]
    _tg, _ = revival_target({"seat": hs, "pane": "%1", "liveness": "no-harness"}, _rev_snap)
    check("7.662 TARGET (in place): a `no-harness` row respawns onto its OWN pane, so the "
          "window layout survives (G-12)", _tg == "%1")
    _tg2, _w2 = revival_target({"seat": hs, "pane": "%1", "liveness": "absent"}, _rev_snap)
    check("7.662 TARGET (re-place): a pane that LEFT the room re-places onto a live pane THIS "
          "SNAPSHOT reports — never onto the dead pane, never onto a tmux query",
          _tg2 == "%9" and "%1" != _tg2)
    _tg3, _w3 = revival_target({"seat": hs, "pane": "", "liveness": "absent"}, snap())
    check(f"7.662 TARGET REFUSES: no pane and no live anchor -> EMPTY target and a reason, "
          f"never an empty string handed downward (tmux would resolve it to the LIVE room) "
          f"({_w3[:40]}…)",
          _tg3 == "" and "NO ANCHOR RESOLVES" in _w3)

    # ---- the argv: the executor's contract, and no shell anywhere on this path.
    _argv = revival_argv(b, hs, "%1", "%1", (4242, "99"))
    check(f"7.662 ARGV: `lifecycle-exec --disposition revive --handoff-written 0`, the caller "
          f"PAIR is present, and NO `--force` of any kind reaches the executor",
          _argv[0] == "lifecycle-exec"
          and _argv[_argv.index("--disposition") + 1] == "revive"
          and _argv[_argv.index("--handoff-written") + 1] == "0"
          and _argv[_argv.index("--caller-pid") + 1] == "4242"
          and _argv[_argv.index("--caller-starttime") + 1] == "99"
          and not [t for t in _argv if t.startswith("--force")])
    check("7.662 ARGV IS LIST-ARGV: the hostile package is ONE element, raw and unquoted — the "
          "exec takes no shell, so 7.601's quoting would corrupt a literal operand here",
          hostile_pkg in _argv and _argv[_argv.index("--seat") + 1] == hs)

    # ---- the ROW, driven off `evaluate` and never hand-composed.
    _rev_args = _ns(coord=hostile_coord, package=hostile_pkg, caller_ident=(4242, "99"))
    _ghost_snap = snap()
    _ghost_snap["seats"] = [{"seat": "other", "pane": "%9", "roster_active": True,
                             "liveness": "live"}]
    _ghost_snap["roster_absent"] = [{"seat": hs, "pane": "%1", "liveness": "no-harness"}]

    def _drive662(a_, passes=GHOSTROW_DEBOUNCE_PASSES):
        st, ds = {}, []
        for _ in range(passes):
            ds = evaluate(_ghost_snap, a_, st, {}, fresh)[0]
        return ds

    _ds = _drive662(_rev_args)
    _rev = [x for x in _ds if x["class"] == REVIVAL_CLASS]
    check(f"7.662 ROW: a DEBOUNCED non-door ghost emits a REVIVAL row carrying a `fix` on the "
          f"`--coord` path, and the GHOSTROW flag beside it is still emitted "
          f"({[x['class'] for x in _ds if x['subject'] == hs]})",
          len(_rev) == 1 and _rev[0]["fix"][0] == hostile_coord
          and _rev[0]["fix"][1][:2] == ["lifecycle-exec", "--package"]
          and any(x["class"] == "GHOSTROW" and x["subject"] == hs for x in _ds))
    check("7.662 NOT DEBOUNCED AWAY: one reading fires NOTHING — the revival is gated by the "
          "same debounce as the flag, so a harness mid-restart is never revived on top of",
          not [x for x in _drive662(_rev_args, 1) if x["class"] == REVIVAL_CLASS])
    check("7.662 A DOOR IS NEVER REVIVED: the same ghost declaring `relays:` yields NO revival "
          "row at all — its pane deliberately outlives its session",
          not [x for x in _drive662(_ns(coord=hostile_coord, package=hostile_pkg,
                                        caller_ident=(4242, "99"), door_seats={hs}))
               if x["class"] == REVIVAL_CLASS])
    _no_id = _drive662(_ns(coord=hostile_coord, package=hostile_pkg))
    check("7.662 NO IDENT -> NO FIRE, SAID OUT LOUD: without a caller (pid, starttime) pair no "
          "REVIVAL row exists and the GHOSTROW flag carries the refusal",
          not [x for x in _no_id if x["class"] == REVIVAL_CLASS]
          and any(x["class"] == "GHOSTROW" and "NO REVIVAL WAS FIRED" in x["detail"]
                  for x in _no_id))

    # ⚠ EVERY `decision(...)` CALL SITE, not only the rows this selftest happens to reach: parsed
    # off this file's own AST, so an unreachable row carrying a retired name is caught too.
    import ast
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    residue = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "decision"):
            continue
        for lit in ast.walk(node):
            if isinstance(lit, ast.Constant) and isinstance(lit.value, str):
                residue += [(node.lineno, t) for t in RETIRED_ROLE_TOKENS if t in lit.value]
    check(f"RETIRED ROLE: no decision this file can emit names one ({len(residue)} hit(s): "
          f"{residue})", not residue)
    check("RETIRED ROLE: BARRED_ACT — the one delivered string reached by name — is clean",
          not any(t in BARRED_ACT for t in RETIRED_ROLE_TOKENS))
    check("RETIRED ROLE: neither recipient default is a retired role",
          not any(t in (DEFAULT_LEADER_SEAT + "|" + DEFAULT_FALLBACK)
                  for t in RETIRED_ROLE_TOKENS))

    print(f"selftest: {len(fails)} failure(s)" if fails else "selftest: all green")
    return 1 if fails else 0


# ---------------------------------------------------------------- main

def main():
    # ⚠ BEFORE parse_args, deliberately: `--package` and `--coord` are REQUIRED for a real pass
    # and a selftest has neither a package nor a room. Relaxing them instead would weaken the
    # fail-closed start for every production fire to buy one test entry point.
    if "--selftest" in sys.argv[1:]:
        return selftest()
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--package", required=True, help="the goal folder holding state.json")
    p.add_argument("--state-json", default=None, help="override the snapshot path")
    p.add_argument("--coord", required=True, help="path to the kit's coord.py (delivery)")
    p.add_argument("--room-package", default=None,
                   help="the package flags are DELIVERED into, and whose snapshot decides "
                        "whether the recipient is live — the EXPLICIT OVERRIDE. Absent: DERIVED "
                        "from the goal's live lease (needs --room-goal), else --package. "
                        "In production the watched goal and the room are the same goal; a probe "
                        "watching a throwaway target is the only case that separates them.")
    p.add_argument("--room-goal", default=None,
                   help="goal folder whose LIVE LEASE resolves the room at FIRE TIME when "
                        "--room-package is absent. Naming a package here instead would be a home "
                        "in waiting: it goes stale the moment that execution ends. Resolution "
                        "goes through coord.derive_lease(), which REFUSES on an unreadable lease "
                        "or on anything but exactly one room, rather than guessing (R10 / "
                        "design-lock items 1-2).")
    p.add_argument("--team-monitor", default="",
                   help="path to team_monitor.py — the remedy TEXT and, under --notify, the "
                        "program the staleness row's inline `ensure` fix actually runs")
    p.add_argument("--to", default=DEFAULT_LEADER_SEAT,
                   help="the LEADER seat — the recipient of every judgment row and of every "
                        "escalated seat row (CMP-21's chain ends at the leader, who carries it "
                        "to the master or the owner)")
    p.add_argument("--fallback-to", default=DEFAULT_FALLBACK,
                   help="a second recipient when the leader seat is not live. EMPTY BY DEFAULT: "
                        "no undeliverable name is invented, and a pass with no live recipient "
                        "fails loud rather than sending flags into a dead seat")
    p.add_argument("--escalate-after", type=int, default=DEFAULT_ESCALATE_AFTER,
                   help="consecutive passes a seat-addressed condition may hold before the same "
                        "condition escalates to the leader (CMP-21 Layout rows 3/ctx-refresh)")
    p.add_argument("--send-as", default="goal-watcher-job")
    p.add_argument("--cadence-s", type=float, default=DEFAULT_CADENCE_S)
    p.add_argument("--tolerance-mult", type=float, default=DEFAULT_TOLERANCE_MULT)
    p.add_argument("--quiet-min", type=int, default=DEFAULT_QUIET_MIN)
    p.add_argument("--context-pct", type=int, default=50,
                   help="fallback ctx threshold for a seat declaring no ctx-refresh")
    p.add_argument("--context-pct-override", type=int, default=0,
                   help="PROBES ONLY — override every seat's OWN ctx-refresh. The live "
                        "catalogue entry never sets it: a seat's declared threshold winning "
                        "over the fallback is the production behaviour, so inducing a real "
                        "CONTEXT crossing needs an override rather than a lower fallback. "
                        "Discovered by a probe that failed for exactly this reason.")
    # ⚠ DEFAULT None, NOT A NUMBER (task 7.82 criterion 3). ABSENT means READ the run's
    # budget.json; a value means an operator deliberately overrode the ruling, and the job says so.
    p.add_argument("--mem-floor-mb", type=int, default=None,
                   help="DELIBERATE OVERRIDE ONLY. Absent, the floor is read from "
                        "{--package}/budget.json (floors.pressure_warn_mb), which is its one "
                        "normative home (r-floor-single-source). Passing a number here overrules "
                        "an owner ruling, so the job reports which value it used and why.")
    p.add_argument("--load-per-core", type=float, default=DEFAULT_LOAD_PER_CORE)
    p.add_argument("--standby", action="append", default=[],
                   help="a seat whose correct state is WAITING (G-68); repeatable")
    p.add_argument("--one-shot-harness", action="append", default=["opencode", "codex"],
                   help="a harness whose exit is COMPLETION, not death (G-76)")
    p.add_argument("--notify", action="store_true",
                   help="deliver nudges AND perform the inline mechanical fixes; without it the "
                        "pass is a full dry run — every row is decided and printed, nothing is "
                        "sent and no child process is spawned. This is the SHADOW mode a fixture "
                        "run is thresholded in")
    p.add_argument("--selftest", action="store_true",
                   help="run this file's own assertions over the pure predicates and exit")
    p.add_argument("--json", action="store_true", help="print the decision set as JSON")
    p.add_argument("--state-file", default=None)
    p.add_argument("--shadow-trail", default=None,
                   help="override the SHADOW BACKSTOP's probe-trail path (default: "
                        "{--package}/coordination/" + SHADOW_TRAIL_FILENAME + "). The trail is "
                        "the record of enqueues COMPUTED AND NOT PERFORMED — nothing here "
                        "reaches a queue, and no flag can make it.")
    p.add_argument("--reflag-min", type=int, default=30,
                   help="refuse to repeat an identical flag to the room inside this many "
                        "minutes, checked against the run's own message log so it survives "
                        "the job's private dedup state being lost or pointed elsewhere")
    p.add_argument("--budget-s", type=int, default=120)
    p.add_argument("--mem-mb", type=int, default=256)
    args = p.parse_args()

    jobcontain.contain(mem_mb=args.mem_mb, seconds=args.budget_s)
    # ⚠ RESOLVED ONCE, HERE, AND REPORTED — same discipline as the memory floor below. A refusal is
    # a HARD START FAILURE, never a fallback onto some run the job picked: see resolve_room_package.
    room, room_why = resolve_room_package(args)
    if room is None:
        # ---- CMP-21 invariant 8, and this is the ONLY place the run-close state is observable
        # from: the job thresholds a LIVE run, so "the run closed" reaches it as the register no
        # longer resolving one. The sweep is REPORTED here rather than performed — see
        # `worktree_leftovers` for why removal stays with the tool that owns it.
        report_worktree_leftovers(args)
        print("goal-watcher-job: REFUSING TO START — %s\n"
              "  The room flags are DELIVERED into must be the LIVE run, and this job will not "
              "guess which one that is: a flag delivered into the wrong room reads as having "
              "reached someone who can act on it.\n"
              "  Fix the run register, or pass --room-package to override deliberately."
              % room_why, file=sys.stderr)
        return 2
    args.room_package = room
    print("goal-watcher-job: room %s" % room_why, file=sys.stderr)
    pkg = Path(args.package)

    # ⚠ RESOLVED ONCE, HERE, AND REPORTED. Criterion 5: a missing or unreadable declaration is a
    # HARD START FAILURE, never a silent fallback -- the ONLY thing that may stand in for a
    # declaration is an EXPLICIT operator override, which is what `--mem-floor-mb` now means.
    # Criterion 8: the job says WHICH VALUE IT USED AND WHY, on the way up, not only when it flags.
    try:
        args.mem_floor_mb, floor_why = budget_mod.floor_source(pkg, "warn", args.mem_floor_mb)
    except (budget_mod.FloorUndeclared, budget_mod.FloorUnreadable) as exc:
        print("goal-watcher-job: REFUSING TO START — %s\n"
              "  The floor's one home is the run's budget.json (r-floor-single-source, G-42). This "
              "job will not invent a number to watch against: a pressure flag raised against a "
              "made-up floor is worse than no flag, because it reads as a measurement.\n"
              "  Declare floors.pressure_warn_mb there, or pass --mem-floor-mb to override "
              "deliberately." % exc, file=sys.stderr)
        return 2
    print("goal-watcher-job: floor %s" % floor_why, file=sys.stderr)
    # ⚠ RESOLVED ONCE, HERE, AND REPORTED — same discipline as the room and the floor above. The
    # count is printed on EVERY pass, including the zero case: a door exemption that silently
    # stopped resolving would otherwise look exactly like a run with no doors in it, and the
    # difference is whether `close-seat --renew` is about to be coached at the owner's channel.
    args.door_seats = declared_door_seats(args)
    print("goal-watcher-job: doors %d seat(s) declaring `relays:`%s"
          % (len(args.door_seats),
             (": " + ", ".join(sorted(args.door_seats))) if args.door_seats else ""),
          file=sys.stderr)
    # ⚠ RESOLVED ONCE, HERE, AND REPORTED — the same discipline as the doors above, and for the
    # same reason: `evaluate` stays PURE, and a revival that stopped being possible must not look
    # like a run with no ghosts in it (task 7.662).
    args.caller_ident = caller_ident(args)
    print("goal-watcher-job: revival caller ident %s"
          % (f"pid {args.caller_ident[0]} starttime {args.caller_ident[1]}"
             if args.caller_ident else
             "UNREADABLE — the revival row will REFUSE this pass (see `caller_ident`)"),
          file=sys.stderr)
    snap_path = args.state_json or str(pkg / "state.json")
    state_path = args.state_file or str(pkg / "coordination" / "goal-watcher-state.json")
    trail_path = args.shadow_trail or str(pkg / "coordination" / SHADOW_TRAIL_FILENAME)
    lock = jobcontain.single_instance(str(pkg / "coordination" / "goal-watcher-job.lock"))
    if lock is None:
        print("goal-watcher-job: another instance holds the lock — this pass exits.")
        return 0

    now = time.time()
    snap, err = read_snapshot(snap_path)
    # ⚠ LOADED AND BANKED BEFORE THE BRANCH, deliberately (task 7.561): both arms below build the
    # sensor's `ensure`, and the one that needs the room's session most is the arm that has no
    # snapshot to read it from. `remember_session` runs on every pass — including the healthy
    # ones, which are the only passes that HAVE a session to bank.
    state = load_state(state_path)
    # ---- Task 7.557: the un-cleaned-worktree report ALSO runs ONCE when a healthy watch starts —
    # `room` has already resolved above (a refusal returned at line ~2113 before reaching here), so
    # every pass that gets this far IS a healthy watch. Without this call site the report only ever
    # fires from the refusal branch, so leftovers from a run that never hits refusal are never
    # surfaced until something else checks later — the coverage gap the owner ruled on 2026-08-08.
    # Gated on a `_`-prefixed state key: non-underscore keys are wiped every pass (below, for the
    # per-episode dedup), but underscore keys persist across passes in the SAME watch's state file
    # — and a NEW watch starts with a state file that does not have this key yet (a fresh run gets
    # a fresh `coordination/` folder), which is exactly what makes "once per watch" fall out of
    # "once per state file" with no extra bookkeeping.
    # ponytail: the ceiling of that equivalence is a watch loop RESTARTED against the same package
    # — it inherits the key and stays quiet. Deliberate: re-reporting on every unit restart is the
    # per-cycle cost the ruling excluded. Upgrade path if a restart must re-report: key the gate on
    # the watch unit's boot id rather than on the key's mere presence.
    if not state.get("_worktree_swept_reported"):
        report_worktree_leftovers(args)
        state["_worktree_swept_reported"] = True
    remember_session(state, snap)
    if snap is None:
        # An unreadable snapshot IS the stale-sensor incident: the job cannot see the room,
        # so enforcement is paused for exactly the same reason. It is never a silent no-op.
        print(f"goal-watcher-job: {err} — ENFORCEMENT PAUSED (sensor incident).",
              file=sys.stderr)
        snap = {"seats": [], "captured_at_iso": "?"}
        tail = sensor_ensure(args, state)
        decisions = [decision("STALE-SENSOR", "team-monitor",
                              "inline fix: restart the sensor (idempotent ensure)", err,
                              sensor_ensure_text(args.team_monitor, tail),
                              nudge="leader",
                              fix=(args.team_monitor, tail))]
        paused = True
        trail = []
    else:
        # The seats the DURABLE check-out record is asked about, and only these. Two rows need
        # it and they need it for the SAME question — did this seat check out cleanly:
        #   roster_absent  -> the SHADOW BACKSTOP's without-clean-check-out half
        #   live pane, roster row no longer active -> the REAP row's cleanly-DONE half
        # One reader, one meaning of `done`; two rows deriving it separately is how they come
        # to disagree about the same seat in the same pass.
        absent_seats = [r.get("seat") for r in (snap.get("roster_absent") or []) if r.get("seat")]
        done_paned = [s.get("seat") for s in (snap.get("seats") or [])
                      if s.get("seat") and s.get("roster_active") is False
                      and s.get("liveness") == "live"]
        decisions, paused, trail = evaluate(
            snap, args, state,
            declared_dispositions(args, sorted(set(absent_seats) | set(done_paned))), now)

    # Flag once per episode; re-arm when the condition clears — the same discipline the kit
    # layer uses, so a per-pass comparison is not swamped by repeats of one crossing.
    armed = {k: v for k, v in state.items() if not k.startswith("_")}
    fresh, seen, emitted = [], {}, set()
    for d in decisions:
        key = f"{d['class']}:{d['subject']}"
        seen[key] = True
        # A decision whose action is "none" is REPORTED and never DELIVERED — STANDBY is a
        # seat behaving correctly, and waking anyone about it is the defect (G-68) rather
        # than the detection. It still appears in the decision set the window scores.
        #
        # `key in emitted` is the WITHIN-PASS half, and it was missing until a probe proved it
        # (G-81, Case C). The armed check only consults the PREVIOUS pass's state, so a
        # snapshot carrying one seat twice — a renewed seat whose old pane is still reported,
        # for instance — emitted the same flag twice from a SINGLE pass. The leader suspected
        # exactly this mechanism from the log alone and I was about to argue it could not
        # happen, because the observed duplicates had a different cause. Both were true: the
        # duplicates came from separate invocations, AND this hole was real and separate.
        if key in emitted or armed.get(key) or d["action"].startswith("none"):
            continue
        emitted.add(key)
        fresh.append(d)
    state = {k: v for k, v in state.items() if k.startswith("_")}
    # ⚠ THE ARMING MOVED BELOW THE DELIVERY LOOP (task 7.536). It stood here, so an episode was
    # armed on INTENT — a `deliver()` that failed was indistinguishable from a nudge that was
    # ignored, and the row was never retried inside the episode.

    stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
    print(f"goal-watcher-job pass {stamp} — {len(decisions)} decision(s), {len(fresh)} new"
          + ("  [ENFORCEMENT PAUSED: stale sensor]" if paused else ""))
    for d in decisions:
        print(f"  {d['subject']:<20} {d['class']:<17} [{d['nudge'] or '-':<6}] {d['action']}")

    # ---- THE INLINE MECHANICAL FIXES, before delivery and gated on --notify. Each row that
    # carries one built its argv in `evaluate`; NOTHING is spawned in a dry pass. Deduped by
    # argv because two rows may name one sweep, and the outcome is folded into the flag the
    # leader receives — a fix that ran and failed must never reach anyone as a bare detection.
    ran = {}
    # ⚠ THE REVIVAL IS THE ONE FIX THAT IS NOT IDEMPOTENT, so it is the ONE fix gated on the row
    # being FRESH — once per episode, re-armed only when the seat is seen healthy again. The
    # other two run on every pass because running them twice is running them once (task 7.662).
    fresh_keys = {f"{d['class']}:{d['subject']}" for d in fresh}
    if args.notify:
        for d in decisions:
            if not d.get("fix"):
                continue
            script, tail = d["fix"]
            if d["class"] == REVIVAL_CLASS:
                if f"{d['class']}:{d['subject']}" not in fresh_keys:
                    continue
                # THE ATTEMPT LADDER (see REVIVAL_ATTEMPTS). Spent BEFORE the fire, and ABANDONED
                # at the cap: the hole is then reported on every pass rather than going quiet,
                # because a bound that silently stops trying cannot be told from a seat that
                # recovered.
                allowed, attempt, cap = revival_ladder(state, d["subject"])
                if not allowed:
                    print(f"  revival [{d['subject']}]: ABANDONED — {attempt}/{cap} "
                          f"attempts spent")
                    d["detail"] += (
                        f" REVIVAL ABANDONED: the attempt ladder is EXHAUSTED ({attempt}/{cap} "
                        f"attempts). NOTHING further will be launched for this seat "
                        f"automatically — the bound exists so a seat that cannot be revived does "
                        f"not re-launch forever. This row keeps reporting on every pass; it is "
                        f"the leader's now.")
                    continue
                # The unit name is STABLE per (package, seat): systemd refuses a second unit of
                # that name while the first is active, which is the double-fire guard under this
                # file's own — see WHAT DID NOT MOVE in the module docstring.
                outcome, why = run_revival(script, tail, jobcontain.unit_name(
                    REVIVAL_UNIT_PREFIX, f"{args.package}\t{d['subject']}"))
                print(f"  revival [{d['subject']}]: {outcome} "
                      f"({REVIVAL_ATTEMPTS[attempt]} of {cap} attempts); {why}")
                d["detail"] += (f" REVIVAL {outcome}: {why}."
                                + ("" if outcome == "FIRED" else
                                   " NOTHING IS RUNNING for this seat — which is exactly the "
                                   "case CMP-21 leaves to the leader."))
                continue
            key = (str(script), tuple(tail))
            if key not in ran:
                ran[key] = run_inline(script, tail)
                print(f"  inline fix [{d['class']}]: {os.path.basename(str(script))} "
                      f"{' '.join(tail)} -> {'OK' if ran[key][0] else 'FAILED'}; {ran[key][1]}")
            ok, detail = ran[key]
            d["detail"] += (f" INLINE FIX {'RAN' if ok else 'FAILED'}: {detail}."
                            + ("" if ok else " The mechanical arm did not repair this — which is"
                                             " exactly the case CMP-21 leaves to the leader."))
    elif any(d.get("fix") for d in decisions):
        print("  (dry: --notify not set — inline mechanical fixes NOT run)")

    sent = failed = suppressed = 0
    undelivered = set()
    delivery_note = ""
    if args.notify and fresh:
        room_snap = snap
        if args.room_package != args.package:
            room_snap, _err = read_snapshot(str(Path(args.room_package) / "state.json"))
            room_snap = room_snap or {}
        for d in fresh:
            # ⚠ RESOLVED PER DECISION. A seat row goes to its own seat and a judgment row to the
            # leader, so one recipient for the pass cannot express this chain (CMP-21).
            key = f"{d['class']}:{d['subject']}"
            to, why = resolve_recipient(room_snap, args, d)
            delivery_note = why
            if to is None:
                # Fail loud. A flag nothing consumes is a log line, not an enforcement action.
                print(f"goal-watcher-job: {why} — flag [{d['class']}] {d['subject']} NOT "
                      f"DELIVERED. The detection is sound and the delivery is not; treat this "
                      f"as an incident.", file=sys.stderr)
                undelivered.add(key)
                failed += 1
                continue
            head = f"goal-watcher-job [{d['class']}] {d['subject']} —"
            if recently_said(args.room_package, head, args.reflag_min):
                suppressed += 1
                print(f"  suppressed: [{d['class']}] {d['subject']} was already said to "
                      f"the room inside {args.reflag_min}min — repeating it trains the "
                      f"room to ignore this job")
                continue
            print(f"  delivery [{d['class']}] -> {to}: {why}")
            ok, msg = deliver(args, to, flag_text(d, snap))
            if ok:
                sent += 1
            else:
                undelivered.add(key)
                failed += 1
                print(f"goal-watcher-job: {msg} — flag [{d['class']}] "
                      f"{d['subject']} NOT DELIVERED", file=sys.stderr)
    elif fresh:
        print("  (dry: --notify not set — flags NOT delivered)")

    # ---- ARMED BY DELIVERY (task 7.536). A key that was NOT delivered this pass is left
    # UNARMED so the next pass re-nudges it, up to DELIVER_RETRIES attempts; `_undelivered`
    # counts them and is pruned to conditions still seen, so the budget resets with the episode.
    # A dry pass (no --notify) attempts no delivery and arms as it always did.
    tries = {k: v for k, v in (state.get("_undelivered") or {}).items() if k in seen}
    for key in seen:
        if key not in undelivered:
            tries.pop(key, None)
            state[key] = True
            continue
        tries[key] = attempt = tries.get(key, 0) + 1
        if attempt >= DELIVER_RETRIES:
            state[key] = True
            print(f"  UNDELIVERED {key} — retry bound reached "
                  f"({attempt}/{DELIVER_RETRIES}); armed anyway, the failure stands here")
        else:
            print(f"  UNDELIVERED {key} — left RETRYABLE for the next pass "
                  f"(attempt {attempt}/{DELIVER_RETRIES})")
    state["_undelivered"] = tries
    # The ladder RE-ARMS when the condition clears: a seat with no revival row this pass has its
    # spent attempts dropped, so the cap bounds ONE episode and never the seat's whole life.
    prune_revival_attempts(state, {d["subject"] for d in decisions
                                   if d["class"] == REVIVAL_CLASS})
    save_state(state_path, state)
    trailed = append_trail(trail_path, trail)
    if trailed:
        print(f"  shadow: {trailed} probe-trail record(s) -> {trail_path} "
              f"(COMPUTED, NOT ENQUEUED — no queue was reached)")

    if args.json:
        print(json.dumps({
            "layer": "goal-watcher-job",
            "captured_at": snap.get("captured_at"),
            "captured_at_iso": snap.get("captured_at_iso"),
            "enforcement_paused": paused,
            "decisions": decisions,
            "new": [f"{d['class']}:{d['subject']}" for d in fresh],
            "delivered": sent, "delivery_failed": failed,
            "suppressed_as_repeat": suppressed,
            "undelivered": sorted(undelivered),
            "retry_bound": DELIVER_RETRIES,
            "delivery": delivery_note,
            "shadow_trail": trail,
            "shadow_trail_path": trail_path,
        }, indent=1))

    del lock
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
