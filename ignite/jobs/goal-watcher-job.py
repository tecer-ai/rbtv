#!/usr/bin/env python3
"""goal-watcher-job — the ENFORCEMENT half of R24's observation architecture (task 7.32).

Fired by the ignite daemon as a periodic `fire-tool` job.

**It reads team-monitor's snapshot at `{goal}/runs/run-{n}/state.json` (task 7.33) plus three
DECLARED NON-SENSING inputs, and performs NO RAW SENSING.** No tmux, no /proc, no harness
session files, no pane capture. team-monitor is the run's sole raw sensor and that
single-sensor invariant is the whole architecture; a second raw reader is exactly the "two
sensors, one of them fixed" failure the design exists to prevent. The absence of raw sensing
is grep-provable and a verifier greps it.

The four non-sensing inputs, enumerated so nobody has to grep for them:

  1. `{run}/taskforce.csv` — DECLARED executor bindings (see below).
  2. `{run}/coordination/messages.md` — the room's own message log, read to avoid repeating a
     flag it has already said (see the debounce, below).
  3. its own dedup-state file — what it wrote on its previous pass.
  4. `{run}/sessions.csv` — the run's own session trace, read through `coord.session_disposition`
     for ONE thing: whether a seat that is no longer in the room checked out CLEANLY. It is the
     SHADOW BACKSTOP's only added input (see THE SHADOW BACKSTOP, below). It was THREE inputs
     before that arm landed, and this count is part of the claim rather than decoration.

None senses anything; all four are files the run wrote about itself. **This wording is
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

No agent is ever spawned to close another agent and nothing mechanical recycles a seat. No
decision, remedy, flag or help string here names a retired role: that ABSENCE is the
grep-provable property, and it replaces task 7.32's older self-contradicting wording
(`job -> chief-of-staff -> leader`), which the ruling supersedes.

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

NOTE FOR THE SHADOW WINDOW: `COMPLETED` and `STANDBY` are classes the OLD layer cannot
emit. That is a declared DIVERGENCE, filed before the window opens — not a disagreement
discovered inside it, which would invalidate the window.

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
DEFAULT_LOAD_PER_CORE = 1.5
SWAP_RISE_READS = 3

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


def run_inline(script, tail, timeout=INLINE_FIX_TIMEOUT_S):
    """Run ONE inline mechanical fix as a child process. (ok, detail). THE ONLY exec door here.

    Both fixes it carries are IDEMPOTENT by the callee's own contract — team-monitor's `ensure`
    and coord's observe-only `reap` — which is precisely what makes them fixes rather than
    judgments, and what makes running one on every stale pass safe.

    The child is exempted from this job's own address-space and CPU caps (`child_preexec`): a
    sensor restart killed by the WATCHER's budget would leave the sensor half-started, which is
    a worse state than the one being repaired."""
    # ⚠ THE EMPTINESS CHECK RUNS FIRST, and the order is the whole point. `--team-monitor`
    # DEFAULTS TO `""`, so an entry that omits it reaches here with an empty path — and
    # `basename("")` is `""`, which the allowlist branch below rejects with "`` is not an
    # inline-fix program … no queue door is reachable from here". That text lands in the flag the
    # LEADER reads (the caller folds this detail into it), pointing at the act-identity bar when
    # the actual cause is an unset operator flag. Behind the allowlist branch this check was
    # unreachable, which is why it never fired.
    if not str(script).strip():
        return False, ("REFUSED: no program path was given for this inline fix — the operator "
                       "flag naming it (`--team-monitor` for the staleness row, `--coord` for "
                       "the reap row) is unset or empty, so the row degrades to a nudge. This is "
                       "a MISSING PATH, not a refused program.")
    name = os.path.basename(str(script))
    if name not in INLINE_FIX_SCRIPTS:
        return False, (f"REFUSED: `{name}` is not an inline-fix program. This job may exec only "
                       f"{INLINE_FIX_SCRIPTS} — no queue door is reachable from here.")
    try:
        r = subprocess.run([sys.executable, str(script), *tail], capture_output=True,
                           text=True, timeout=timeout, preexec_fn=jobcontain.child_preexec)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return False, f"`{name}` did not run: {type(exc).__name__}: {exc}"
    lines = [ln for ln in (r.stdout or r.stderr or "").splitlines() if ln.strip()]
    return r.returncode == 0, (f"exit {r.returncode}"
                               + (f"; {lines[-1].strip()[:160]}" if lines else ""))


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
    of the stall predicate with a fabrication."""
    src = snap.get("headless_source")
    if not isinstance(src, dict):
        return None, "snapshot carries no headless_source (older sensor)"
    if not src.get("readable"):
        return None, (src.get("reason") or "headless[] source not readable")
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
    when the goal has NO live run: that is the only moment "the run closed" is observable from
    where this job stands. REMOVAL IS NOT PERFORMED and is not this file's: `worktree-flow.py`
    owns it and REFUSES on a dirty tree, and a backstop that force-removed a dirty worktree
    would destroy unmerged work — the opposite of a backstop."""
    goal = Path(room_goal).resolve()
    root = goal.parent.parent.parent / ".rbtv" / "worktrees"     # {ws}/.rbtv/goals/<goal>
    try:
        return sorted(p.name for p in root.iterdir()
                      if p.is_dir() and f"--{goal.name}--" in p.name)
    except OSError:
        return []


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

    # ---- ROW 6: GHOSTROW / COMPLETED / DEAD, driven from `roster_absent` — team-monitor's
    # own designated GHOSTROW input, which already separates the two failures that look alike
    # from a distance: a pane that LEFT the room, and a pane still there holding no harness.
    standby = set(args.standby or [])
    one_shot = set(args.one_shot_harness or [])
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
            decisions.append(decision(
                "GHOSTROW", name, "nudge leader: ghost roster row",
                f"roster row ACTIVE but pane {pane} runs NO harness process"
                + (f" (declared harness `{harness}`)" if harness else
                   " (no declared harness in taskforce.csv — classed conservatively as a "
                   "ghost, which asks for inspection rather than a close)")
                + ". Its work is stopped and every wake sent to it is typed into a bare shell.",
                "inspect, then relaunch or close: "
                + coord_seat("close-seat", name, "--renew"),
                nudge="leader"))

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
    if recipient_live(room_snap, args.to):
        return args.to, f"{fell}leader seat '{args.to}' is live in the room's snapshot"
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

    THE REGISTER IS READ BY EXACTLY ONE READER, AND IT IS NOT THIS FILE. `coord.resolve_live_run()`
    already does this and already REFUSES rather than guesses when zero or two rows read `open`
    (R9's one-live-run guarantee, whose enforcement — task 7.77 — is NOT BUILT). A second CSV reader
    here would be a second answer to the same question. `coord` is imported INSIDE this function
    from the `--coord` path this job already requires, so a copy-and-test of this file carries no
    sibling dependency it does not otherwise need.

    With NEITHER flag the room is the watched package, which is the production case: in production
    the run being watched and the room being told about it are the same run.

    Refusal is FAIL-CLOSED and returns no package: delivering a flag into a room picked by a guess
    on an ambiguous register is worse than not delivering it, because the flag reads as having been
    delivered to whoever can act on it."""
    if args.room_package:
        return args.room_package, "--room-package (explicit override; register not consulted)"
    if not args.room_goal:
        return args.package, "--package (neither --room-package nor --room-goal; room == watched run)"
    sys.path.insert(0, str(Path(args.coord).resolve().parent))
    import coord  # noqa: E402  — the register's single reader; see this docstring
    goal = Path(args.room_goal).resolve()
    run_id, detail = coord.resolve_live_run(goal)
    if not run_id:
        return None, (f"register at {goal / 'runs.csv'} did not resolve ONE live run: {detail}")
    return str((goal / "runs" / run_id).resolve()), (
        f"{goal / 'runs.csv'} state=open -> {run_id} (resolved live via coord.resolve_live_run, R10)")


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
                to="leader", fallback_to="")
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
    ok_src = {"readable": True, "reason": ""}

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
    ads = evaluate(absent_snap, b, {}, {}, fresh)[0]
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
    # THE PATH THAT MUST NOT MOVE: no seat name reaches an exec argv at all, and the one `fix=`
    # this loop can emit still carries the package RAW — a quote added there would be handed to
    # coord as a literal character.
    reap_snap = snap()
    reap_snap["seats"] = [{"seat": hs, "pane": "%4", "roster_active": False, "liveness": "live"}]
    rp = next(x for x in evaluate(reap_snap, b, {}, {hs: CLEAN_CHECKOUT}, fresh)[0]
              if x["class"] == "REAP")
    check("7.601 EXEC PATH UNCHANGED: the reap fix argv is raw and unquoted, and no seat name is "
          "smuggled into its remedy",
          rp["fix"] == (b.coord, ["--package", hostile_pkg, "reap"]) and hs not in rp["remedy"])

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
    p.add_argument("--package", required=True, help="the run folder holding state.json")
    p.add_argument("--state-json", default=None, help="override the snapshot path")
    p.add_argument("--coord", required=True, help="path to the kit's coord.py (delivery)")
    p.add_argument("--room-package", default=None,
                   help="the run package flags are DELIVERED into, and whose snapshot decides "
                        "whether the recipient is live — the EXPLICIT OVERRIDE. Absent: resolved "
                        "live from the goal's run register (needs --room-goal), else --package. "
                        "In production the watched run and the room are the same run; a probe "
                        "watching a throwaway target is the only case that separates them.")
    p.add_argument("--room-goal", default=None,
                   help="goal folder whose runs.csv resolves the LIVE room at FIRE TIME when "
                        "--room-package is absent. Naming a run here instead would be a home in "
                        "waiting: it goes stale the moment that run closes. Resolution goes "
                        "through coord.resolve_live_run(), which REFUSES on zero or two open "
                        "rows rather than guessing (R9/R10).")
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
        if args.room_goal:
            goal_name = Path(args.room_goal).name
            left = worktree_leftovers(args.room_goal)
            flow = Path(args.coord).resolve().parent / "worktree-flow.py"
            print(f"goal-watcher-job [WORKTREE-SWEEP] {goal_name} — "
                  f"{len(left)} leftover worktree(s): {', '.join(left) or '(none)'}")
            if left:
                print(f"  remedy: {worktree_flow_text(flow, goal_name)}   (then merge-seat / "
                      f"close-goal — removal REFUSES on a dirty tree and is never forced here)")
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
    state.update({k: True for k in seen})

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
    if args.notify:
        for d in decisions:
            if not d.get("fix"):
                continue
            script, tail = d["fix"]
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
    delivery_note = ""
    if args.notify and fresh:
        room_snap = snap
        if args.room_package != args.package:
            room_snap, _err = read_snapshot(str(Path(args.room_package) / "state.json"))
            room_snap = room_snap or {}
        for d in fresh:
            # ⚠ RESOLVED PER DECISION. A seat row goes to its own seat and a judgment row to the
            # leader, so one recipient for the pass cannot express this chain (CMP-21).
            to, why = resolve_recipient(room_snap, args, d)
            delivery_note = why
            if to is None:
                # Fail loud. A flag nothing consumes is a log line, not an enforcement action.
                print(f"goal-watcher-job: {why} — flag [{d['class']}] {d['subject']} NOT "
                      f"DELIVERED. The detection is sound and the delivery is not; treat this "
                      f"as an incident.", file=sys.stderr)
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
                failed += 1
                print(f"goal-watcher-job: {msg} — flag [{d['class']}] "
                      f"{d['subject']} NOT DELIVERED", file=sys.stderr)
    elif fresh:
        print("  (dry: --notify not set — flags NOT delivered)")

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
            "delivery": delivery_note,
            "shadow_trail": trail,
            "shadow_trail_path": trail_path,
        }, indent=1))

    del lock
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
