#!/usr/bin/env python3
"""goal-watcher-job — the ENFORCEMENT half of R24's observation architecture (task 7.32).

Fired by the ignite daemon as a periodic `fire-tool` job.

**It reads team-monitor's snapshot at `{goal}/runs/run-{n}/state.json` (task 7.33) plus three
DECLARED NON-SENSING inputs, and performs NO RAW SENSING.** No tmux, no /proc, no harness
session files, no pane capture. team-monitor is the run's sole raw sensor and that
single-sensor invariant is the whole architecture; a second raw reader is exactly the "two
sensors, one of them fixed" failure the design exists to prevent. The absence of raw sensing
is grep-provable and a verifier greps it.

The three non-sensing inputs, enumerated so nobody has to grep for them:

  1. `{run}/taskforce.csv` — DECLARED executor bindings (see below).
  2. `{run}/coordination/messages.md` — the room's own message log, read to avoid repeating a
     flag it has already said (see the debounce, below).
  3. its own dedup-state file — what it wrote on its previous pass.

None senses anything; all three are files the run wrote about itself. **This wording is
deliberate and replaces an earlier "and NOTHING else", which was true about the sensing and
false about the file list — one grep falsifies it, and the accurate version cannot be.** Found
by this job's own mechanical verifier; the same shape as the recipient defect below, where a
claim was right about the thing being watched and imprecise about the thing that was not.

WHAT IT DOES: thresholds the snapshot into a DECISION SET, and delivers each decision to a
LIVE recipient. Nothing else.

NOTIFY-ONLY, AND THAT IS A DELIBERATE READING OF A SELF-CONTRADICTING CONTRACT
-----------------------------------------------------------------------------
Task 7.32 says this job "spawns a closer" and "runs the restarter", and in the same
paragraph says it "never performs an agentic action itself", with the chain
    job (deterministic detection) -> chief-of-staff (operational recovery) -> leader
    (judgment) -> master/owner.
Both cannot hold. This job resolves it as DETECT + DELIVER: every flag carries the exact
remedy command, and the agentic half is performed by chief-of-staff. Reasons, not a default:

  1. Lifecycle is the leader's, and `p-no-seat-closed-for-memory` stands — nothing is closed
     to buy headroom, and nothing autonomously at all.
  2. `r-cutover-gated` bars the run's own control loop from adopting an un-shadowed feature.
     Handing a job built tonight autonomous close rights IS that cutover.
  3. It makes the shadow window mean something. `watch.py`, the layer this shadows, is
     explicitly notify-only ("the loop never closes, kills, or relaunches anything"). Two
     layers that both emit decisions are comparable; one that acts and one that advises are
     not, and the comparison object is the DECISION SET, per the window's own definition.

Disclosed to the leader at entry (run-root `m2-lane-e-entry.md`); override is one flag on
one code path.

THE DEAD-ROOM ROW HANDS OFF; IT DOES NOT REBUILD
------------------------------------------------
Task 7.71's `selfheal-room` job is already registered and live against this room, with its
own probe trail. A second recovery path for the same failure is not redundancy — it is two
mechanisms that can disagree about whether a room is dead and both act. So this row DETECTS
(`session_alive: false`) and names the owner of the recovery. Coverage is unchanged; what
changes is only that the condition now appears in this job's decision set, where the shadow
window can score it.

STALENESS IS PAUSE + RECOVER, NOT ALERT-ONLY (R24 + R32)
--------------------------------------------------------
A snapshot older than `--tolerance-mult` x the sensor cadence means THE SENSOR IS THE
INCIDENT. Two behaviours, both required and both implemented here: enforcement PAUSES
entirely (no threshold acts off a frozen snapshot — a watcher enforcing on a stale world
spawns closers against seats that no longer exist), AND chief-of-staff is woken to restart
the sensor. Enforcement resumes on the first fresh snapshot, with no manual re-arm.

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

WHAT IT WRITES
--------------
stdout/stderr (captured by `fire-tool` into `{data_root}/logs/`, bounded by task 7.13's age
sweep) plus ONE small dedup-state file at `{package}/coordination/goal-watcher-state.json`
— `coordination/` is script-owned by the run's surface map. No new unbounded artifact class.
It never writes `state.json`: task 7.33 has exactly one writer and this is a reader.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jobcontain  # noqa: E402

# The chief-of-staff ROLE is what this job escalates to (registry `chief-of-staff`, R32).
# The legacy alias for that role is deliberately ABSENT from this file, its config and its
# prompts: the alias exists for readers of old records, not for new code (grep-provable).
DEFAULT_ROLE_SEAT = "watcher"
DEFAULT_FALLBACK = "leader"
DEFAULT_CADENCE_S = 20.0
DEFAULT_TOLERANCE_MULT = 3.0
DEFAULT_QUIET_MIN = 30
DEFAULT_MEM_FLOOR_MB = 2800
DEFAULT_LOAD_PER_CORE = 1.5
SWAP_RISE_READS = 3


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

def decision(cls, subject, action, detail, remedy=""):
    """One element of the comparison object the shadow window scores (m2 shape §7.1).

    `cls` is the vocabulary class; `action` is what the layer says to DO. Two layers agree
    when they produce the same (class, subject, action), never when they agree on a reading."""
    return {"class": cls, "subject": subject, "action": action,
            "detail": detail, "remedy": remedy}


def evaluate(snap, args, state, now):
    """Snapshot -> (decisions, paused, notes). PURE: reads the snapshot dict and nothing else."""
    decisions = []
    coord_cmd = f"python3 {args.coord} --package {args.package}"

    # ---- ROW 5 (FIRST, and it gates every other row): the staleness tripwire.
    tolerance = args.cadence_s * args.tolerance_mult
    age = snapshot_age_s(snap, now)
    if age is None or age > tolerance:
        shown = "unknown" if age is None else f"{age:.0f}s"
        decisions.append(decision(
            "STALE-SENSOR", "team-monitor", "wake chief-of-staff: restart the sensor",
            f"snapshot age {shown} > tolerance {tolerance:.0f}s "
            f"({args.tolerance_mult:g}x the {args.cadence_s:g}s cadence). ENFORCEMENT IS "
            f"PAUSED — no threshold acts off a frozen snapshot, and box{{}} pressure is "
            f"UNOBSERVED for as long as this lasts.",
            f"python3 {args.team_monitor} ensure --package {args.package}"))
        return decisions, True, []

    # ---- ROW 4: the room itself.
    if snap.get("session_alive") is False:
        decisions.append(decision(
            "ROOM-DEAD", snap.get("session", "?"), "wake chief-of-staff: room recovery",
            "the snapshot reports the room's tmux session absent. Recovery is task 7.71's "
            "registered `selfheal-room` job, which owns this failure and is already armed — "
            "this row detects and hands off rather than running a second recovery path that "
            "could disagree with it.",
            f"{coord_cmd} launch --only <seat> --force --force-memory  (kit fallback)"))

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
            "BOX", "box", "wake chief-of-staff: box pressure",
            "; ".join(box_flags) + ". NEVER an autonomous close — `p-no-seat-closed-for-memory` "
            "stands and no seat is closed to buy headroom.",
            "pause launches; let finishing seats return their own RAM; escalate below 2600MB"))

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
        if r.get("liveness") == "absent":
            decisions.append(decision(
                "DEAD", name, "wake chief-of-staff: pane gone",
                f"roster row ACTIVE but pane {pane} is not in the room — wakes cannot reach "
                f"it. {r.get('reason', '')}".strip(),
                f"{coord_cmd} close-seat {name} --no-export   (or relaunch)"))
        elif harness and harness in one_shot:
            # G-76. `opencode run` executes, prints, exits — for this harness a vanished
            # process is the SUCCESS path, and the remedy is the OPPOSITE of a ghost's.
            decisions.append(decision(
                "COMPLETED", name, "wake chief-of-staff: close the finished one-shot",
                f"pane {pane} holds no process and this seat is bound to `{harness}`, a "
                f"ONE-SHOT harness: it executed, printed and exited. Read the seat's LAST "
                f"MESSAGE before acting — the message says whether work was delivered; the "
                f"process cannot. Close, do not renew.",
                f"{coord_cmd} close-seat {name}"))
        else:
            decisions.append(decision(
                "GHOSTROW", name, "wake chief-of-staff: ghost roster row",
                f"roster row ACTIVE but pane {pane} runs NO harness process"
                + (f" (declared harness `{harness}`)" if harness else
                   " (no declared harness in taskforce.csv — classed conservatively as a "
                   "ghost, which asks for inspection rather than a close)")
                + ". Its work is stopped and every wake sent to it is typed into a bare shell.",
                f"inspect, then relaunch or close: {coord_cmd} close-seat {name} --renew"))

    # ---- ROWS 1/2/3: per-seat, over live rows only.
    for s in snap.get("seats") or []:
        name = s.get("seat") or ""
        pane = s.get("pane") or "?"
        if not name:
            # A launched-but-silent pane: team-monitor reports it as a real state and never
            # guesses a name. Nothing here can be keyed to a seat, so nothing is decided.
            continue
        if not s.get("roster_active") or name in absent:
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
                "APPROVAL", name, "wake chief-of-staff: clear the prompt",
                f"pane {pane} is parked on an interactive approval prompt — it is frozen "
                f"until someone answers, and a wake typed into it lands in the modal.",
                f"{coord_cmd} approve {name}"))

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
                    ""))
            else:
                decisions.append(decision(
                    "QUIET", name, "wake chief-of-staff: re-summon or check",
                    f"no activity for {mins}min (threshold {args.quiet_min}min).",
                    f"check it; if hung or done-but-stuck: {coord_cmd} close {name} --renew"))

        # ROW 3: context past the seat's OWN refresh threshold (its briefing's `ctx-refresh`,
        # with the job's fallback for a seat that declares none).
        #
        # A ONE-SHOT SEAT IS SKIPPED HERE, and this row is where the omission was found. This
        # row's remedy is "spawn a closer, which negotiates handoff AT A TURN BOUNDARY" — that
        # presupposes an interactive, renewable seat. A one-shot has exactly one turn: there is
        # no handoff to negotiate, no later turn to protect, and `close --renew` would relaunch
        # work that is already finishing. Flagging it proposes an action nobody should take.
        # G-76 applied to a THIRD row: I had applied it only to GHOSTROW/COMPLETED, and a shadow
        # pass caught `verify-job-mech` (opencode, 62.6% of a 204800 window) being told to spawn
        # a closer. The old layer never had this bug because it computes context for claude
        # seats only — an accident of its implementation that happened to be right.
        pct = s.get("ctx_pct")
        threshold = args.context_pct_override or s.get("ctx_refresh") or args.context_pct
        if (declared.get(name, harness_of(s)) in one_shot) and pct is not None:
            continue
        if isinstance(pct, (int, float)) and pct >= threshold:
            amb = " (reading is DIRECTIONAL — issue G-31)" if s.get("ctx_ambiguous") else ""
            decisions.append(decision(
                "CONTEXT", name, "wake chief-of-staff: spawn a closer",
                f"context {pct}% >= threshold {threshold}%{amb}. The closer negotiates handoff "
                f"AT A TURN BOUNDARY — nothing is killed mid-turn.",
                f"{coord_cmd} close {name} --renew"))

    return decisions, False, []


# ---------------------------------------------------------------- delivery

def recipient_live(snap, name):
    """Is this recipient a LIVE seat, per the ROOM's snapshot? A flag delivered to a dead seat
    is a log line, and the clause is satisfiable while the claim is false without this check."""
    for s in snap.get("seats") or []:
        if s.get("seat") == name:
            return s.get("liveness") == "live" and bool(s.get("harness_pid"))
    return False


def resolve_recipient(room_snap, args):
    """(recipient, why). The chief-of-staff ROLE, then the declared fallback, then nobody.

    Resolved from the DELIVERY room's snapshot, which is not necessarily the snapshot being
    thresholded. In production they are the same file — the job watches the room it reports
    into. A probe watching a throwaway package is the case that separates them, and it found
    this: resolving the recipient from the thresholded snapshot made every flag about a
    throwaway target undeliverable, because the recipient does not live in that room. The
    subject of a flag and the addressee of a flag are different things."""
    if recipient_live(room_snap, args.to):
        return args.to, f"chief-of-staff seat '{args.to}' is live in the room's snapshot"
    if args.fallback_to and recipient_live(room_snap, args.fallback_to):
        return args.fallback_to, (f"chief-of-staff seat '{args.to}' is NOT live — escalated to "
                                  f"'{args.fallback_to}'")
    return None, (f"NO LIVE RECIPIENT: neither '{args.to}' nor "
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


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--package", required=True, help="the run folder holding state.json")
    p.add_argument("--state-json", default=None, help="override the snapshot path")
    p.add_argument("--coord", required=True, help="path to the kit's coord.py (delivery)")
    p.add_argument("--room-package", default=None,
                   help="the run package flags are DELIVERED into, and whose snapshot decides "
                        "whether the recipient is live. Defaults to --package; in production "
                        "they are the same run. A probe watching a throwaway target is the "
                        "only case that separates them.")
    p.add_argument("--team-monitor", default="", help="path to team_monitor.py (remedy text)")
    p.add_argument("--to", default=DEFAULT_ROLE_SEAT, help="the seat holding chief-of-staff")
    p.add_argument("--fallback-to", default=DEFAULT_FALLBACK)
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
    p.add_argument("--mem-floor-mb", type=int, default=DEFAULT_MEM_FLOOR_MB)
    p.add_argument("--load-per-core", type=float, default=DEFAULT_LOAD_PER_CORE)
    p.add_argument("--standby", action="append", default=[],
                   help="a seat whose correct state is WAITING (G-68); repeatable")
    p.add_argument("--one-shot-harness", action="append", default=["opencode", "codex"],
                   help="a harness whose exit is COMPLETION, not death (G-76)")
    p.add_argument("--notify", action="store_true",
                   help="deliver flags; without it the pass is a dry run")
    p.add_argument("--json", action="store_true", help="print the decision set as JSON")
    p.add_argument("--state-file", default=None)
    p.add_argument("--reflag-min", type=int, default=30,
                   help="refuse to repeat an identical flag to the room inside this many "
                        "minutes, checked against the run's own message log so it survives "
                        "the job's private dedup state being lost or pointed elsewhere")
    p.add_argument("--budget-s", type=int, default=120)
    p.add_argument("--mem-mb", type=int, default=256)
    args = p.parse_args()

    jobcontain.contain(mem_mb=args.mem_mb, seconds=args.budget_s)
    args.room_package = args.room_package or args.package
    pkg = Path(args.package)
    snap_path = args.state_json or str(pkg / "state.json")
    state_path = args.state_file or str(pkg / "coordination" / "goal-watcher-state.json")
    lock = jobcontain.single_instance(str(pkg / "coordination" / "goal-watcher-job.lock"))
    if lock is None:
        print("goal-watcher-job: another instance holds the lock — this pass exits.")
        return 0

    now = time.time()
    snap, err = read_snapshot(snap_path)
    if snap is None:
        # An unreadable snapshot IS the stale-sensor incident: the job cannot see the room,
        # so enforcement is paused for exactly the same reason. It is never a silent no-op.
        print(f"goal-watcher-job: {err} — ENFORCEMENT PAUSED (sensor incident).",
              file=sys.stderr)
        snap = {"seats": [], "captured_at_iso": "?"}
        decisions = [decision("STALE-SENSOR", "team-monitor",
                              "wake chief-of-staff: restart the sensor", err,
                              f"python3 {args.team_monitor} ensure --package {args.package}")]
        paused = True
        state = load_state(state_path)
    else:
        state = load_state(state_path)
        decisions, paused, _ = evaluate(snap, args, state, now)

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
        print(f"  {d['subject']:<20} {d['class']:<13} {d['action']}")

    sent = failed = suppressed = 0
    delivery_note = ""
    if args.notify and fresh:
        room_snap = snap
        if args.room_package != args.package:
            room_snap, _err = read_snapshot(str(Path(args.room_package) / "state.json"))
            room_snap = room_snap or {}
        to, why = resolve_recipient(room_snap, args)
        delivery_note = why
        if to is None:
            # Fail loud. A flag nothing consumes is a log line, not an enforcement action.
            print(f"goal-watcher-job: {why} — {len(fresh)} flag(s) NOT DELIVERED. The "
                  f"detection is sound and the delivery is not; treat this as an incident.",
                  file=sys.stderr)
            failed = len(fresh)
        else:
            print(f"  delivery: {why}")
            for d in fresh:
                head = f"goal-watcher-job [{d['class']}] {d['subject']} —"
                if recently_said(args.room_package, head, args.reflag_min):
                    suppressed += 1
                    print(f"  suppressed: [{d['class']}] {d['subject']} was already said to "
                          f"the room inside {args.reflag_min}min — repeating it trains the "
                          f"room to ignore this job")
                    continue
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
        }, indent=1))

    del lock
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
