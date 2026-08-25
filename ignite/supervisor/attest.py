# ---- this module is IMPORTED, never `exec`d into `coord.py`'s namespace ----------------------
# It left `coord/` for the home `spec-component-map` §3 names, under the owner's 2026-08-25 ruling
# ("SPLIT_MODULES / coordinate split"). The move-only split loaded it by `exec` into ONE shared
# namespace; it is a real module now, so everything it did not define itself is named through the
# module that owns it.
#
# ⚠ QUALIFY — NEVER `from coord import NAME`. The selftest rebinds ~60 kit names at runtime
# (`global wake, atomic_write, ...` plus the `globals()[...]` sites), and a name copied into this
# module at import time is a SNAPSHOT: every later stub would be inert. Measured 2026-08-24 on the
# same bytes — 913 ok under a copying bind vs 1039 ok / PASS through the shared namespace. Reading
# `coord.NAME` at CALL time is what keeps a rebinding visible here.
#
# ⚠ The peer imports below are CIRCULAR by construction (`launch` <-> `attest`, `ready` <-> ...)
# and that is sound ONLY because every cross-module name is read inside a function body. A
# module-level read of a peer's attribute would break the import cycle — measure before adding one.

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import coord
import launch
import lifecycle_exec
import process
import ready

# ---------- dag-11: the attest-exit arm (`coordinate attest-exit`) ----------
#
# THE MEASURED FAILURE THIS CLOSES (F1, 2026-07-28, seat `oc2`). The seat DID THE WORK — `done.txt`
# read `OK` — and its one-shot harness exited without checking out. Afterwards: the roster still
# said `oc2 ACTIVE pane=%466`; the pane held a bare `bash`; the `sessions.csv` row was open with no
# `ended`; and `awaiting-close.json` had NO `oc2` entry at all. Only the sensor saw it, as
# `roster_absent`. So every surface the ready arithmetic reads says "still working, forever", the
# successor never becomes READY, and the work is complete on disk the whole time.
#
# NOT OPENCODE-SPECIFIC IN PRINCIPLE: any harness whose terminal state is ABSENCE has this shape.
#
# ⚠⚠ WHAT THIS ARM ATTESTS IS ONE FACT AND ONLY ONE: THE HARNESS TERMINATED. It does NOT decide
# whether the work succeeded, and it MUST NOT — an attestation by a third party to a fact it did
# not witness is exactly the misgrading R-6 bars.
#
# ⚠⚠ AND IT NO LONGER STAMPS ANYTHING ITSELF [spec-supervisor §3, T4-R7]. This door BECAME the
# supervisor death stamp: it hands the supervisor the facts it witnessed — which sitting, that the
# process is gone, the exit code, the transcript tail — and the supervisor's ONE evidence-to-ending
# table (`supervisor/death-stamp.js`) decides the ending and performs the reap. Two independent
# stampers was the defect: this arm and the daemon-lane closer below each wrote the reason-less
# word `exited` onto an open row, and a terminal carrying no reason left the recovery ladder with
# nothing to classify. `exited` is dead vocabulary now — the ending store refuses it at the write
# boundary, so it cannot come back by anyone's convention.
#
# WHY THE KIT AND NOT THE CHIEF-OF-STAFF: the CoS is barred from lifecycle actuation, and its pane
# is the measured-unreliable surface. This is pure code; the CoS may READ its report.

# One full sensor cadence. team-monitor's own default interval is 20s, and this is deliberately a
# WHOLE multiple of it rather than equal to it: the debounce must span a complete sensor pass plus
# the slack of one more, or a seat observed absent in the snapshot written the instant its harness
# began exiting would be attested while its check-out was still in flight.
# ⚠ THE CADENCE IS NOT READABLE FROM THE SNAPSHOT — team-monitor does not record the interval it
# is running at, so this constant cannot be derived from the run and is a documented second home
# for that number. Filed as a loose end; the fix is on the monitor's side (record `interval` in
# `state.json`), not here.
ATTEST_MIN_ABSENCE_S = 60


def attest_exit_blockers(args, seat, snap=None, now_ts=None):
    """Every reason `seat` must NOT be exit-attested, as a list. EMPTY means every term holds.

    A LIST, not a bool, and for `reap_blockers`' reason: this arm writes to four surfaces, so a
    caller — and a human reading a dry pass — must see WHICH term held it, never merely that
    something did. A gate that answers only yes/no teaches nobody why the run is stuck.

    THE PREDICATE, and every term is required:

      (a) the seat is in `state.json`'s `roster_absent`      — sensor-detected, never self-derived
      (b) its descriptor declares `mode: one-shot`           — the terminal state is EXPECTED
      (c) it has NO terminal disposition                     — it never checked out
      (d) no LIVE `lifecycle-inflight.json` entry            — it is not mid-renewal
      (e) the condition has HELD longer than one full sensor cadence — not a race with a slow exit

    ⚠ HOW (e) IS MEASURED, because it is the term with no field behind it. Nothing on disk records
    HOW LONG a seat has been absent: `roster_absent` rows carry no duration, and this is a
    stateless CLI with no tick counter of its own (watch.py keeps `gone_ticks` in its private
    state; reading that would couple this arm to a component being retired). So (e) is taken as
    TWO INDEPENDENT OBSERVATIONS SEPARATED BY REAL TIME rather than as an inferred duration:

      (e1) the SNAPSHOT saw the seat absent, and that snapshot is at least one cadence old;
      (e2) a LIVE re-read of the room, taken now, still finds no harness on the seat's pane;
      (e3) the seat's OPEN session row started BEFORE the snapshot was written — so the absence
           the snapshot recorded belongs to THIS session and not to an earlier one that has
           since been relaunched into the same seat.

    Two observations a cadence apart, both absent, provably about the same session. That is
    stronger than a tick count, because (e2) is taken AT ACT TIME: a classification carried from a
    snapshot is up to one cadence stale, and this arm must decide on the room as it stands."""
    base = coord.base_dir(args, register=False)
    pkg = coord.package_dir(args, register=False)
    now_ts = time.time() if now_ts is None else now_ts
    snap = coord.load_state_snapshot(base) if snap is None else snap
    why = []
    if snap is None:
        return ["no readable `state.json` snapshot — the sensor's observation is this arm's ONLY "
                "evidence that the harness is gone, and an unreadable one is evidence in neither "
                "direction (refuse, never assume)"]
    absent = {(r.get("seat") or ""): r for r in (snap.get("roster_absent") or [])
              if isinstance(r, dict)}
    row = absent.get(seat)
    if row is None:
        why.append("(a) not in `state.json`'s roster_absent — the sensor does not report this "
                   "seat as an active roster row whose harness is gone")
    decl = next((w for w in launch.discover_workers(coord.workers_dir(args)) if w["agent"] == seat), None)
    mode = (decl or {}).get("mode") or ""
    if mode != "one-shot":
        why.append(f"(b) descriptor declares mode: {mode or '<undeclared>'} — attestation is only "
                   f"for a harness whose terminal state is EXPECTED to be absence. An undeclared "
                   f"mode is NOT one-shot: this refuses rather than assumes, so no existing seat "
                   f"becomes attestable by having said nothing")
    value, source, skew = ready.terminal_disposition(pkg, base, seat)
    if skew:
        why.append(f"(c) its two disposition records DISAGREE (awaiting-close.json={skew[0]} | "
                   f"sessions.csv={skew[1]}) — a skew is a human's to adjudicate, and attesting "
                   f"on top of one would bury the contradiction")
    elif value is not None:
        why.append(f"(c) it already has a check-out: disposition `{value}` ({source}) — there is "
                   f"nothing left to attest")
    entry = lifecycle_exec.load_lifecycle(base).get(seat)
    # PLAIN pid+starttime liveness, NEVER `ident_is_live_harness`: the lifecycle executor is a
    # PYTHON process, and the harness predicate answers DEAD for every live one of them — which
    # would turn MID-RENEWAL into "exited" and attest a seat that is actively being renewed.
    _ex = lifecycle_exec.lifecycle_ident(entry.get("executor")) if isinstance(entry, dict) else None
    if (isinstance(entry, dict) and entry.get("state") == "in-flight" and _ex
            and process.ident_is_live_process((_ex["pid"], _ex["starttime"]))):
        why.append("(d) a LIVE lifecycle executor holds this seat — it is mid-renewal, not exited")
    written = snap.get("written_at")
    age = (now_ts - written) if isinstance(written, (int, float)) else None
    if age is None:
        why.append("(e1) the snapshot carries no `written_at`, so its age — and with it whether "
                   "the absence has held for a full sensor cadence — cannot be established")
    elif age < ATTEST_MIN_ABSENCE_S:
        why.append(f"(e1) the snapshot is only {int(age)}s old and the absence must have held "
                   f"longer than one full sensor cadence ({ATTEST_MIN_ABSENCE_S}s) — this would "
                   f"be a race with a slow exit, attesting a harness still shutting down")
    pane = (row or {}).get("pane") or ""
    if pane and pane in coord.live_panes() and process.pane_harness_idents(pane):
        why.append(f"(e2) pane {pane} holds a LIVE harness right now — the snapshot's observation "
                   f"is up to one cadence stale and the room as it stands contradicts it")
    if isinstance(written, (int, float)):
        started = session_open_started(pkg, seat)
        if started is not None and started > written:
            why.append("(e3) this seat's open session row STARTED AFTER the snapshot was written, "
                       "so the absence the snapshot recorded belongs to an earlier session — "
                       "attesting it would close the wrong one")
    return why


def session_open_started(pkg, seat):
    """The epoch seconds at which `seat`'s LAST OPEN session row started, or None.

    `None` covers every unreadable case — no file, no columns, no open row, an unparseable stamp —
    and the caller treats it as "cannot establish", never as "old enough"."""
    path = coord.sessions_csv(pkg)
    if not path.exists():
        return None
    header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if not {"seat", "ended", "started"} <= set(idx):
        return None
    found = None
    for r in rows:
        coord.pad_row(r, header)
        if r[idx["seat"]].strip() == seat and not r[idx["ended"]].strip():
            found = r[idx["started"]].strip()
    if not found:
        return None
    try:
        return datetime.strptime(found, "%Y-%m-%d %H:%M").timestamp()
    except ValueError:
        return None


def attest_exit_seat(args, seat):
    """Perform the attestation for ONE seat. Returns the list of step strings performed.

    THE ORDER IS `cmd_checkout`'S OWN, deliberately, so the surfaces this leaves behind can never
    diverge from the ones a normal check-out leaves: export, flip the roster row, record the debt,
    close the session row. A different order here would be a second definition of what a finished
    seat looks like."""
    base = coord.base_dir(args, register=False)
    _, _, rows = coord.load_workers(base)
    row = coord.current_row(rows, seat) or {}
    steps = []
    out, err = coord.export_transcript(args, seat, "attest-exit")
    steps.append(f"transcript: {out}" if not err else f"transcript SKIPPED — {err}")

    def flip(r):
        r["active"] = "no"
        r["checkout"] = coord.now()

    ok, note = coord.update_row(base, seat, flip)
    steps.append(f"roster: flipped to inactive" if ok else f"roster: NOT flipped — {note}")
    # THE SUPERVISOR DEATH STAMP, and this arm decides NOTHING about the ending [spec-supervisor
    # §4]. It reports the evidence it holds; the supervisor reads the checkout (a `done` or
    # `incomplete` the seat declared for itself STANDS and is merely reaped) and otherwise stamps
    # `failed` with a mandatory reason class. The killed word `exited` is unreachable from here —
    # not by this arm's restraint, but because the ending store refuses it at the boundary.
    #
    # ⚠ THE CALLER'S EVIDENCE WINS. `--evidence` carries the exit code and transcript-tail path the
    # witness read (`spawn.js#crashEvidence`); §1.4 requires the pointer to name the observed
    # death, and this process can see neither fact. The exported transcript is the fallback, and
    # the seat name the last resort — the store refuses an empty pointer outright.
    pkg = coord.package_dir(args, register=False)
    _res, _step = supervisor_stamp(args, pkg, seat,
                                   checked_in=bool(row.get("checkin")),
                                   fallback_evidence=out or f"attest-exit:{seat}")
    steps.append(_step)
    sid, cerr = coord.session_trace_safe(coord.session_close, args, seat)
    steps.append(f"sessions.csv: {sid} ended" if not cerr
                 else f"sessions.csv: row NOT completed — {cerr}")
    return steps


# ---------- W1: THE SESSION-CLOSER — attest-exit's DAEMON-LANE candidate source ----------------
#
# ⚠ IT IS THE SAME VERB, DELIBERATELY (adv, C1). `attest-exit` is already the specced kit-side
# writer for "a harness terminated and nobody closed the row": it flips the roster, writes both
# disposition surfaces, closes the session row, and advances no edge. What it LACKED was a
# candidate source that works where there is no tmux (the daemon lane) and a caller inside the
# engine. Minting a second closing verb would have given one act two instruments and two places
# for the writer bound to drift apart.
#
# ⚠⚠ THE ROW KEY IS THE SESSION-ID AND NEVER THE SEAT NAME (adv, C6). The daemon HOLDS the id — it
# wrote the open row itself at spawn (`spawn.js` § THE AT-DISPATCH RECORD, keyed by the same
# `session_id` the `jobs_log` row carries). Matching by seat name would stamp whichever row is open
# for that name RIGHT NOW, which under concurrent sittings is a LIVE one: F4's race, performed by
# the mechanism built to close F3.
#
# ⚠⚠ THE ENDING IS THE SUPERVISOR'S, NEVER THIS CLOSER'S. Checkout writes `sessions.csv` itself.
# This closer runs only when the process died without checking out (or died mid-checkout before the
# ledger write), and all it does with that fact is HAND IT TO `supervisor_door.death_stamp`. It used
# to originate the reason-less word `exited` under `kit`; that word is dead [T1-R3, T4-R7] and the
# supervisor's evidence table answers in its place — a dead process with no declared ending is a
# `failed: crash`, and a mid-checkout death that DID leave a declaration has that declaration stand.
# `daemon_close_blockers` (a) still refuses to re-stamp a row checkout already closed.


def session_row_by_id(pkg, sid):
    """`(seat, ended, pid, pid_starttime)` for the session row named `sid`, or None.

    Read-only and by SESSION-ID: this is the daemon lane's row key and the whole reason the closer
    cannot misattribute under concurrent sittings."""
    path = coord.sessions_csv(pkg)
    if not path.exists():
        return None
    header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
    idx = {c: i for i, c in enumerate(header)}
    if "session-id" not in idx or "seat" not in idx:
        return None
    for r in rows:
        coord.pad_row(r, header)
        if r[idx["session-id"]].strip() == sid:
            return (r[idx["seat"]].strip(),
                    r[idx["ended"]].strip() if "ended" in idx else "",
                    r[idx["pid"]].strip() if "pid" in idx else "",
                    r[idx["pid-starttime"]].strip() if "pid-starttime" in idx else "")
    return None


def close_session_row_by_id(pkg, base, sid, disposition, writer):
    """Stamp `ended` + the disposition pair on the OPEN row named `sid`. `(seat, why)`.

    RAISES nothing the caller must handle except `validate_disposition`'s ValueError, which is a
    caller-contract breach and stays loud (R-8). Every environmental failure is reported as `why`.

    It is `session_close`'s twin, keyed differently and NOT a rewrite of it: `session_close` targets
    a SEAT's last open row (right for a check-out, which is the occupant speaking) and this targets
    ONE session-id (right for a closer, which is a third party speaking about a specific ending)."""
    # Work endings are not written here.
    with coord.coord_lock(base):
        path = coord.sessions_csv(pkg)
        if not path.exists():
            return "", f"no sessions.csv under {pkg}"
        header, rows = coord.read_csv_table(path, coord.SESSIONS_COLS)
        header, widened = coord.widen_header(header, coord.SESSIONS_COLS)
        if widened:
            rows = [coord.pad_row(r, header) for r in rows]
        idx = {c: i for i, c in enumerate(header)}
        if "session-id" not in idx or "ended" not in idx:
            return "", "sessions.csv carries no `session-id`/`ended` columns"
        target = None
        for r in rows:
            coord.pad_row(r, header)
            if r[idx["session-id"]].strip() == sid and not r[idx["ended"]].strip():
                target = r
        if target is None:
            return "", f"no OPEN row carries session-id `{sid}`"
        target[idx["ended"]] = coord.now()
        if disposition and "disposition" in idx:
            target[idx["disposition"]] = disposition
            if "disposition-writer" in idx:
                target[idx["disposition-writer"]] = writer
        coord.write_csv_table(path, header, rows)
        return target[idx["seat"]].strip(), ""


def daemon_close_blockers(args, sid, seat, ended, pid, pid_starttime):
    """Every reason the session-closer must NOT close `sid`, as a list. EMPTY means act.

    A LIST for `attest_exit_blockers`' reason — a caller and a human reading a dry pass must see
    WHICH term held. The tmux-lane predicate's terms do not transfer: there is no roster row, no
    `state.json` sensor pass and no pane to re-read, so the evidence is the ROW plus /proc.

      (a) the row is still OPEN                      — a closed row is nobody's to close again
      (b) its recorded process is DEAD               — pid+starttime, the identity pair the row
                                                       already carries; a live one is not an exit
      (c) the two disposition records do not SKEW    — a skew is a human's to adjudicate
      (d) no LIVE lifecycle executor holds the seat  — mid-renewal is not an exit
    """
    base = coord.base_dir(args, register=False)
    pkg = coord.package_dir(args, register=False)
    why = []
    if ended:
        why.append(f"(a) the row for session `{sid}` is ALREADY CLOSED (ended {ended}) — there is "
                   f"nothing left to close, and re-stamping it would rewrite a settled ending")
    # ⚠ `ident_is_live_process`, NOT the harness predicate: a daemon-lane exec is whatever the
    # launch spec named, and the harness predicate answers DEAD for processes that are plainly
    # alive — which would close a RUNNING seat's row. An UNREADABLE pair is not evidence of death
    # either, so it refuses (fail-closed) rather than assuming the exit it exists to record.
    if getattr(args, "force_dead", False):
        # The caller witnessed the death directly; the flag IS the evidence, whether or not the
        # row happens to carry a pid pair to corroborate it. The warm chat-bridge door writes
        # rows with NO pair at all — requiring one here made the engine's own `--force-dead`
        # closer the one verb that could never close the rows only it creates (2026-08-18).
        pass
    elif not pid or not pid_starttime:
        why.append("(b) the row carries no pid/pid-starttime pair, so this arm cannot establish "
                   "that the process is gone — and an absence of evidence is not evidence of an "
                   "exit. The engine caller passes `--force-dead` when IT witnessed the death")
    elif process.ident_is_live_process((pid, pid_starttime)):
        why.append(f"(b) pid {pid} (starttime {pid_starttime}) is STILL ALIVE — the process this "
                   f"row names has not exited, and closing its row would end a live session on "
                   f"paper while it keeps working")
    _value, _source, skew = ready.terminal_disposition(pkg, base, seat)
    if skew:
        why.append(f"(c) its two disposition records DISAGREE (awaiting-close.json={skew[0]} | "
                   f"sessions.csv={skew[1]}) — a skew is a human's to adjudicate, and closing on "
                   f"top of one would bury the contradiction")
    entry = lifecycle_exec.load_lifecycle(base).get(seat)
    _ex = lifecycle_exec.lifecycle_ident(entry.get("executor")) if isinstance(entry, dict) else None
    if (isinstance(entry, dict) and entry.get("state") == "in-flight" and _ex
            and process.ident_is_live_process((_ex["pid"], _ex["starttime"]))):
        why.append("(d) a LIVE lifecycle executor holds this seat — it is mid-renewal, not exited")
    return why


def supervisor_stamp(args, pkg, seat, *, session="", checked_in=False, fallback_evidence=""):
    """Call the ONE death-stamp path. `(result_or_None, step_string)`.

    Both closers share it deliberately: a second spelling of "hand the supervisor the evidence" is
    how two doors start disagreeing again, which is the whole defect spec-supervisor §3 closes.
    NEVER RAISES — a closer that dies on an unreachable stamper leaves the world worse than the
    silent arm it replaced, so every failure is REPORTED as its step and the caller's remaining
    steps still run."""
    try:
        res = coord.supervisor_door.death_stamp(
            pkg, seat, session=session,
            checked_in=checked_in,
            evidence=(getattr(args, "evidence", "") or "").strip() or fallback_evidence)
    except (coord.supervisor_door.SupervisorError, OSError, ValueError) as exc:
        return None, f"supervisor death stamp: NOT stamped — {exc}"
    act = (res or {}).get("act", "")
    ending = (res or {}).get("ending", "")
    reason = (res or {}).get("reason_class") or ""
    reaped = "reaped" if (res or {}).get("reaped") else ((res or {}).get("reason") or "not reaped")
    if (res or {}).get("stamped"):
        return res, f"supervisor death stamp: {ending}/{reason} stamped · {reaped}"
    return res, f"supervisor death stamp: {act} — the seat's own `{ending}` stands · {reaped}"


def close_session_seat(args, sid, seat):
    """Perform the daemon-lane close for ONE session-id. Returns the list of step strings.

    Originates NOTHING. Checkout already wrote any seat-declared value; for a process that died
    without a complete checkout the supervisor's evidence table stamps the ending and reaps."""
    base = coord.base_dir(args, register=False)
    pkg = coord.package_dir(args, register=False)
    steps = []
    steps.append("closer hands the supervisor its evidence — it stamps no ending of its own")
    closed_seat, cerr = close_session_row_by_id(pkg, base, sid, "", "")
    steps.append(f"sessions.csv: {sid} ended" if not cerr
                 else f"sessions.csv: row NOT completed — {cerr}")
    row = coord.current_row(coord.load_workers(base)[2], seat) or {}
    res, step = supervisor_stamp(args, pkg, seat, session=sid,
                                 checked_in=bool(row.get("checkin")),
                                 fallback_evidence=f"session:{sid}")
    steps.append(step)
    # The ENDING IS WHATEVER THE SUPERVISOR SAYS IT IS — never a constant this closer chose. It used
    # to return the literal `"exited"` (then, briefly, the literal `"failed"`), which reported a
    # crash even for the row the evidence table's FIRST line covers: a seat that checked out `done`
    # and whose process simply had to be reaped.
    ending = (res or {}).get("ending") or "failed"
    if row.get("active") == "yes":
        def flip(r):
            r["active"] = "no"
            r["checkout"] = f"closed {coord.now()}"

        ok, note = coord.update_row(base, seat, flip)
        steps.append("roster: flipped to inactive" if ok else f"roster: NOT flipped — {note}")
    # A `done` seat's work IS done: mailing a staff chair "its work is NOT done" about a completed
    # sitting is exactly the misgrading this arm's own header bars.
    if ending == "done":
        steps.append("staff mail: NOT minted — the seat declared `done`; the reap is not a failure")
    else:
        entry = {"reason": (res or {}).get("row", {}).get("diagnostic") or ""}
        steps.extend(close_staff_mail_arm(args, base, pkg, seat, ending, entry, sid))
    return steps, closed_seat, ending


# ═══ W3 · THE STAFF WIRING — a signal that reaches an OCCUPIED chair ══════════════════════════
#
# Everything in this section exists for one sentence: a seat that cannot finish must reach a chair
# that is occupied. The three surfaces, in the order a wake travels them:
#
#   1. THE CLOSER'S STAFF-MAIL ARM  — every terminal non-`done` ending mints one message to a staff
#      chair, carrying the seat's own check-out reason. Mechanical: no agent decides whether to
#      mail, so no agent can decide not to.
#   2. THE WAKE                     — D12 (2026-08-20): THE MAIL *IS* THE WAKE. There is no grant,
#      no store and no latch. The goal watcher (`supervisor/reconcile.js`, cadence 300 s) derives a
#      chair with UNREAD MAIL as owed work and launches the sitting itself. The three grant stores
#      that used to carry this — `relaunch-grants.csv`, the bare `relaunch-grants`, and
#      `disposition-grants.csv` — are deleted from the code; the files that exist in older goal
#      folders are inert history no runtime path opens.
#   3. `route-fail`                 — a FAIL verdict with a declared route goes to the AUTHOR of the
#      instruction; an undeclared one goes to the leader. Never a void.
#
# `widen-cage` — the leader's audited permission-edit verb that used to be a fourth surface here —
# is DELETED (ruling [T2-R6, C-6], 2026-08-24): runtime auto-widen is dead, the seat's cage
# envelope is fixed at plan time now. No repair actuator replaces it in this file; a seat blocked
# on a narrow cage escalates to the leader as a message, same as any other blocker.
#
ROUTE_PAYLOAD_DIR = "route-payloads"


def staff_route_target(args, base, flag, who="the check-out"):
    """`(chair, why)` — WHICH staff chair an ending's mail goes to.

    The `consultant` chair is DELETED [T2-R17, D-7-ruling]: `STAFF_SEATS` now names only
    `leader`, so this always resolves there unless the caller's own `--route` flag names it
    explicitly. Kept as a named function (not inlined) because the session-closer's staff-mail
    arm calls it with a caller-supplied flag that can still be garbage or a stale value — the
    "flag is a HINT, never an authority" fallback ladder still earns its keep even with one
    destination."""
    try:
        known = coord.known_recipients(args, base)
    except Exception:                                          # noqa: BLE001
        known = set()
    want = (flag or "").strip()
    if want and coord.is_staff_seat(want) and want in known:
        return want, f"{who} named `{want}` and this goal staffs it"
    if want and coord.is_staff_seat(want):
        return "leader", (f"{who} named `{want}`, which this goal does NOT staff — falling "
                          f"back to the unblocker rather than mailing a chair that does not exist")
    if want:
        return "leader", (f"{who}'s route flag `{want}` names no staff chair — the flag is "
                          f"a HINT, never an authority, so this falls back to the unblocker")
    return "leader", "no route flag — the default is the unblocker"


def routed_recipient(args, base, mtype, sender):
    """`(to, why)` — WHO a ROUTED type reaches, when the sender did not choose (owner ruling D2).

    THE TABLE IS HERE AND NOWHERE ELSE IN CODE. It is stated for humans in the `ROUTED TYPES`
    comment beside `AUTO_TOKEN` and in `coord/communication.md` §4 — and in NO agent prompt,
    which is the point of the ruling: an agent emits a TYPE and never has to discover who to
    contact.

    Callers must only reach this for a type in `ROUTED_TYPES`; anything else is a caller bug and
    raises rather than inventing a default."""
    if mtype == "stuck":
        # ALWAYS the leader — no branch, no goal-shape question, nothing for a sender to get wrong.
        # The leader escalates to the owner what it cannot solve, which is one filter more than the
        # seat crossing that door itself (the same reasoning the owner-ask gate carries).
        return "leader", "`stuck` always reaches the `leader` — the chair that unblocks"
    if mtype == "ask":
        # THE ONE EXCEPTION the ruling names: a seat the descriptor declares may talk to a human
        # asks the human. Read by PATH, the ferry's own read, so this answers the same question the
        # ferry will answer about delivery (see `seat_is_human_interactive`).
        if coord.seat_is_human_interactive(coord.package_dir(args), sender):
            return coord.OWNER_TOKEN, (f"`{sender}` declares `human-interactive:` in its seat.md, so its "
                                 f"questions go STRAIGHT to the owner")
        return "leader", ("the `consultant` chair is deleted [T2-R17, D-7-ruling] — `ask` always "
                          "reaches the `leader`")
    raise ValueError(f"routed_recipient called for non-routed type {mtype!r}")


def staff_mail_body(args, seat, value, entry, sid):
    """The mail's TEXT: enough that the chair ACTS without opening the closer's own reasoning."""
    reason = ""
    if isinstance(entry, dict):
        reason = str(entry.get("reason") or entry.get("incomplete-reason") or "").strip()
    pkg = coord.package_dir(args, register=False)
    reason = reason or ("(none recorded — the ending was stamped from evidence by the supervisor, "
                        "not declared by the seat)")
    return "\n".join([
        f"STAFF MAIL — seat '{seat}' ended `{value}` and its work is NOT done.",
        f"reason given at check-out: {reason}",
        f"session: {sid or '(unresolved)'}",
        f"evidence: {pkg}/sessions.csv (this seat's row), {pkg}/seats/{seat}/ (its own folder and "
        f"session scratchpad), and whatever artifacts its briefing declares.",
        "",
        "This is the failure path. Triage it on evidence YOU observe — an unclean exit says how a "
        "SESSION ended and nothing about whether the WORK finished — then take exactly one "
        "disposition: FIX AND RELAUNCH, ROUTE to the seat that authored the instruction, ANSWER, "
        "or ESCALATE. Never relabel this row by hand or without an investigation. `rule-disposition` "
        "— the verb that recorded a leader's ruling on this row — was deleted [T2-R12, T1-R9]; no "
        "replacement ruling instrument is wired here yet. Where the harness simply DIED and the "
        "work must RUN AGAIN: "
        "`launch --only " + seat + " --rerun <anchor>` — ONE act, an ordinary working session, "
        "and the `failed` row stays on the record (D42).",
    ])


def close_staff_mail_arm(args, base, pkg, seat, value, entry, sid):
    """The closer's staff-mail arm: mint the mail AND the wake for ONE ended seat. Steps, as a list.

    ⚠ STAFF SEATS ARE EXCLUDED BY AN EXPLICIT PREDICATE (adv, C30). A chair MAY check out — since
    the 2026-08-20 extension of D29 it may even record `done` — and it is excluded here regardless:
    mailing a chair about its own row would mail the chair about itself, and each such mail would
    mint the wake for the sitting that writes the next one. Its row is closed silently. WHAT CLOSES
    A STAFF SITTING'S SESSION ROW is this same closer, silently: the row is ended and its ending
    stamped from evidence exactly as any other, the roster is flipped, and NO mail is minted.

    ⚠ IT MAILS ON EVERY TERMINAL NON-`done` ENDING and reads no further into the value.
    `incomplete` is the seat's own honest declaration and reaches the chair IMMEDIATELY; `failed`
    is the supervisor's evidence stamp for a process that died without declaring anything. Both are
    endings nobody has ruled on, which is the only property this arm needs — the value is passed
    through to the mail body and never branched on here."""
    steps = []
    if value == "done":
        return steps
    if coord.is_staff_seat(seat) or coord.is_summoned_seat(seat):
        steps.append(f"staff mail: NOT minted — '{seat}' is closed silently. A staff chair ends "
                     f"`{value}` by construction (it never checks out), so mailing here would mail "
                     f"the chair about itself forever; a SUMMONED chair ends one row PER OWNER "
                     f"TURN of a single resumed conversation, and D24 rules that mail is not a "
                     f"wake term for it. Its row is closed silently, which is the whole of what "
                     f"this ending means.")
        return steps
    to, why = staff_route_target(args, base, (entry or {}).get("route") if isinstance(entry, dict)
                                 else "")
    try:
        n = coord.append_message(base, coord.DISPOSITION_WRITER_KIT, to, "note",
                           staff_mail_body(args, seat, value, entry, sid))
        steps.append(f"staff mail: #{n} -> `{to}` ({why}) — carrying '{seat}'s check-out reason")
    except Exception as exc:                                   # noqa: BLE001
        steps.append(f"staff mail: NOT minted — {type(exc).__name__}: {exc}. The ending is "
                     f"recorded and NOBODY WAS TOLD; say so.")
        return steps
    # D12 · THE MAIL *IS* THE WAKE. No grant is minted here and none exists to mint: the goal
    # watcher (`supervisor/reconcile.js`) derives a chair with unread mail as owed work on every
    # 5-minute pass and launches the sitting itself. The chair's own ENDED row no longer has to be
    # superseded by anything — reconcile reads the mail, not a disposition.
    steps.append(f"staff wake: none needed — `{to}` has unread mail, which the goal watcher "
                 f"reconciles into a sitting on its next pass")
    return steps


# ── `route-fail` — a FAIL verdict always reaches a receiver (adv, C31/C32) ─────────────────────
#
# D6's root cause was a builder seat's FAIL verdict with no mechanical receiver: its ask went to a
# known-but-UNSTAFFED `leader` chair and was silently swallowed. This is the verb that makes the
# receiver mandatory.
#
# ⚠ D12 (2026-08-20) — IT GRANTS NOTHING. The verb used to mint a relaunch grant per route target
# in both stores; those stores are deleted. What it writes now is the MAIL and the PAYLOAD, and
# what makes the routed seat sit again is `supervisor/reconcile.js`: a chair is owed work while its
# mail is unread, and an ordinary seat is owed work while its last ended row is non-terminal.
# ⚠ A ROUTED SEAT WHOSE OWN ROW READS `done` IS NOT OWED WORK and will not come back on its own.
# That is a REAL narrowing of this verb and it is stated rather than papered over — the `--go`
# epilogue says it to the caller too.
#
# ⚠ THE PAYLOAD RIDES A FILE, NOT A GRANT (D6's false-complete is the proof a bare grant re-runs
# the STALE SEED). Every in-cage write path to a target's boot seed is closed — `seat.md` is
# ro-bound, the goal root is read-only — and the ONE shared writable surface is
# `{goalDir}/coordination`. So the payload is written there and `boot_prompt` folds it into the
# relaunched sitting's opening.


def route_payload_path(base, seat):
    return Path(base) / ROUTE_PAYLOAD_DIR / f"{seat}.md"


def write_route_payload(base, seat, text):
    """Write the relaunched seat's payload. `(ok, why)` — never raises."""
    p = route_payload_path(base, seat)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    except OSError as exc:
        return False, f"{p}: {exc}"
    return True, ""


def read_route_payload(base, seat):
    """The payload text for a seat's next sitting, or `''`. Never raises — a boot prompt that
    raises is a seat that never boots, and the payload is an ADDITION to the prompt, not the
    prompt."""
    try:
        return route_payload_path(base, seat).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def cmd_route_fail(args):
    """Route a FAIL back to a receiver that exists. BARE = report; `--go` = act.

    The route is the CALLER'S OWN declaration — `on-fail-relaunch:` in its `seat.md` frontmatter,
    read by `on_fail_relaunch_route`, the same function the verdict verb's loop re-fire reads.
    An UNDECLARED fail goes to the `leader`: a verdict with no declared receiver is exactly the
    case D6 lost, so the fallback is a chair rather than a silence."""
    base = coord.base_dir(args)
    pkg = coord.package_dir(args)
    sender = coord.resolve_agent(args)
    body = coord.message_body(args)
    go = bool(getattr(args, "go", False))
    route = [r for r in coord.on_fail_relaunch_route(base, sender)]
    if not route:
        to, why = staff_route_target(args, base, "")
        print(f"{coord.c(sender, coord.C_LABEL)}  UNDECLARED FAIL -> `{to}` ({why})")
        if not go:
            print("    (report only — nothing was written. Re-run with --go to route it.)")
            return
        n = coord.append_message(base, sender, to, "note",
                           f"ROUTED FAIL — '{sender}' failed and declares no "
                           f"`{coord.ON_FAIL_RELAUNCH_KEY}` route.\n\n{body}")
        print(f"    routed: message #{n} -> `{to}`")
        print(f"    staff wake: none needed — the goal watcher reconciles a chair's unread mail "
              f"into a sitting on its next pass")
        return
    # A DECLARED route. Each target is checked for EXISTENCE and for a bindable session BEFORE
    # anything is written: `_ferry_safe_name` is SYNTAX ONLY, and D6's root cause was a TASK ID in
    # that cell — a perfectly well-formed name that names no seat.
    plans = []
    for seat in route:
        if not coord._ferry_safe_name(seat):
            coord.refuse("input",
                   f"`{coord.ON_FAIL_RELAUNCH_KEY}` entry {seat!r} on '{sender}'s seat.md is not a valid "
                   f"seat name. Fix the descriptor; this verb routes to seats, not to text.", 1)
        if seat not in launch.registered_seats(pkg) and seat not in coord.briefing_frontmatters(coord.workers_dir(args)):
            coord.refuse("state",
                   f"`{coord.ON_FAIL_RELAUNCH_KEY}` names `{seat}`, and this run has NO SEAT of that "
                   f"name (not in taskforce.csv or sessions.csv).\n"
                   f"That cell is checked for SYNTAX at every other door and for EXISTENCE at "
                   f"none, and a task id sitting in it is exactly how a routed FAIL reached "
                   f"nobody. Fix '{sender}'s `{coord.ON_FAIL_RELAUNCH_KEY}` cell in its seat.md and in "
                   f"the workflow's seats.csv, or route this by hand to a seat that exists.", 1)
        sid = (coord.sessions_last_ended(pkg).get(seat) or ("", ""))[0]
        plans.append((seat, sid))
    print(f"{coord.c(sender, coord.C_LABEL)}  DECLARED ROUTE -> {', '.join(s for s, _ in plans)}")
    if not go:
        for seat, sid in plans:
            print(f"    would write `{seat}`'s payload to {route_payload_path(base, seat)} "
                  f"and message it (last ended session {sid or '(none)'})")
        print("    (report only — nothing was written. Re-run with --go to route it.)")
        return
    for seat, sid in plans:
        n = coord.append_message(base, sender, seat, "note",
                           f"ROUTED FAIL from '{sender}' — you are being relaunched to address "
                           f"it.\n\n{body}")
        ok, why = write_route_payload(
            base, seat,
            f"## Routed FAIL from `{sender}` ({coord.now()})\n\nYou are being relaunched because of "
            f"this, and it is NOT the seed you ran on last time — address it before anything "
            f"else.\n\n{body}\n")
        print(f"    `{seat}`: message #{n}")
        told = f"written to {route_payload_path(base, seat)}" if ok else f"NOT written — {why}"
        print(f"    `{seat}`: payload {told}")
    print(coord.c("\nD12 · THIS VERB GRANTS NOTHING. The payload and the message are RECORDS: the boot "
            "prompt of the routed seat's NEXT sitting carries the payload, so it is never re-run "
            "on the stale seed. WHAT MAKES THAT SITTING HAPPEN is the goal watcher "
            "(`supervisor/reconcile.js`), which relaunches a seat whose last ended row is NON-TERMINAL "
            "and a chair that has unread mail. A routed seat whose own row reads `done` is NOT "
            "owed work to it and will NOT come back on its own — say so to the leader rather than "
            "assuming this routed it.", coord.C_HINT))


# ── `send`'s recipient wrapper (adv, C33) ─────────────────────────────────────────────────────
#
# ⚠ WRAPPED AT THE CALL SITE, NEVER INSIDE `known_recipients`. That function's RETURN SET is
# selftest-keyed and has a SECOND caller — `lifecycle_alarm_recipient`, which resolves the
# `leader` chair for executor-failure alarms — so widening the function itself would change what
# that caller reports as resolvable. The wrapper covers both concerns by sitting where the
# recipient DECISION is made, and by leaving the set the two readers share untouched.


def send_recipients(args, base):
    """`(admitted, departed)` for `send`'s gate ONLY.

    `admitted` is `known_recipients` plus the STAFF CHAIRS, which are always addressable whether or
    not this goal has minted their roster rows yet: a send to a staff chair must never fail for
    want of a live session, because "the chair was empty" is the failure this whole program exists
    to close. `departed` is the roster names whose rows are no longer active — accepted, and LOUDLY,
    because a message to a seat that has gone is not refused (its successor may read the log) but
    is never silent either."""
    admitted = set(coord.known_recipients(args, base))
    admitted |= set(coord.STAFF_SEATS)
    departed = set()
    try:
        _, _, rows = coord.load_workers(base)
        for r in rows:
            if r.get("active") != "yes":
                departed.add(r["agent"])
    except Exception:                                          # noqa: BLE001
        departed = set()
    return admitted, departed - set(coord.STAFF_SEATS)


def cmd_attest_exit(args):
    """Attest that a one-shot harness terminated. BARE = report; `--go` = act."""
    base = coord.base_dir(args, register=False)
    # ── W1: THE DAEMON-LANE ARM. Keyed on the session-id the caller HOLDS, so it never touches
    # `state.json` (there is no sensor on this lane) and never matches by seat name (adv, C6).
    sid = (getattr(args, "session", None) or "").strip()
    if sid:
        pkg = coord.package_dir(args, register=False)
        found = session_row_by_id(pkg, sid)
        if found is None:
            print(f"no candidate: no row in {coord.sessions_csv(pkg)} carries session-id `{sid}`. "
                  f"This arm closes a row the daemon itself opened; it invents none.")
            return
        seat, ended, pid, pid_st = found
        why = daemon_close_blockers(args, sid, seat, ended, pid, pid_st)
        if why:
            print(f"{coord.c(seat, coord.C_LABEL)}  NOT CLOSABLE (session `{sid}`)")
            for w in why:
                print(f"    {w}")
            sys.exit(1)
        print(f"{coord.c(seat, coord.C_LABEL)}  CLOSABLE — session `{sid}` is open and its process is gone")
        if not getattr(args, "go", False):
            print("    (report only — nothing was written. Re-run with --go to act.)")
            return
        steps, _closed, _value = close_session_seat(args, sid, seat)
        for step in steps:
            print(f"    {step}")
        return
    snap = coord.load_state_snapshot(base)
    candidates = ([args.seat] if getattr(args, "seat", None)
                  else sorted({(r.get("seat") or "") for r in ((snap or {}).get("roster_absent")
                                                               or []) if isinstance(r, dict)}))
    if not candidates:
        print("no candidate: nothing is in `state.json`'s roster_absent, so no harness is "
              "sensor-reported as gone from a seat the roster still calls active.")
        return
    acted = 0
    for seat in candidates:
        why = attest_exit_blockers(args, seat, snap=snap)
        if why:
            print(f"{coord.c(seat, coord.C_LABEL)}  NOT ATTESTABLE")
            for w in why:
                print(f"    {w}")
            continue
        print(f"{coord.c(seat, coord.C_LABEL)}  EXIT-ATTESTABLE — every term of the predicate holds")
        if not getattr(args, "go", False):
            print("    (report only — nothing was written. Re-run with --go to act.)")
            continue
        for step in attest_exit_seat(args, seat):
            print(f"    {step}")
        acted += 1
    if acted:
        print(coord.c(f"\n{acted} seat(s) handed to the supervisor death stamp. THE ONLY CLAIM THIS ARM "
                f"MAKES IS THAT THE HARNESS TERMINATED; the ending is stamped from evidence. "
                f"Whether the work is done is NOT established here — each row routes "
                f"to the LEADER, which investigates and either relaunches the seat or, where the "
                f"work had in fact concluded, records that ruling — `rule-disposition` was deleted "
                f"[T2-R12, T1-R9]; no replacement ruling instrument is wired here yet. Until then "
                f"it advances NO edge ({coord.coord_invocation(args)} ready-seats).", coord.C_HINT))


def cmd_rule_guard(args):
    """(the seat named in the pair) Record the value for a guarded `after` member's guard. BARE =
    report; `--go` = write.

    `r-gate-ships-with-its-own-key`: the guard term is a GATE — it refuses READY — and this is its
    KEY. They ship in one change, because a gate whose key does not exist is not a gate, it is a
    wall: without this verb, a party who had measured a guard's value had NO mechanism to say so,
    and the only path left was hand-editing the `after` cell to delete the precondition. That edit
    destroys the record of a real precondition to silence a display, which is how folklore is
    manufactured.

    ⚠⚠ WHO MAY WRITE, AND WHY IT CHANGED (`one-readiness-predicate` D2, owner-ruled 2026-08-11).
    THE SEAT NAMED IN THE `(seat, key)` PAIR WRITES ITS OWN VALUE, AND NO OTHER SEAT MAY. The
    leader gate is REMOVED, not widened: the leader is not a participant in advancement, and a
    guard value is a FACT ABOUT THE PRODUCING SEAT'S OWN WORK — which use-case it took, whether
    its retirement was safe — witnessed by that seat and by nothing else. Routing it through a
    leader made the one party who knows the answer ask a party who does not to record it. This is
    the same test every disposition writer answers to (`RECORD_DISPOSITION_WRITER`): WHO SAW IT.

    THE COMMAND RECORDS A MEASUREMENT; IT NEVER MAKES ONE. It opens nothing and grades nothing:
    the work happened BEFORE this call, and this is where its result is written down.

    ⚠ IT IS ONE HALF OF A DOUBLE VALIDATION. This verb bounds WHAT may be written (a pair a live
    edge references, by the seat it is about). `cmd_checkout`'s D3 gate enforces THAT it was
    written: a seat that owes a value cannot check out `done` without it.

    ⚠ `--source` IS MANDATORY. A guard ruling with no citation of where the value was measured is
    indistinguishable from a guess, and it is read months later by somebody who was not there.
    ⚠ THE PAIR MUST BE REFERENCED BY A LIVE EDGE. A ruling on a `(seat, key)` no `after` member
    consumes is a typo until proven otherwise, and a typo that writes is worse than a refusal."""
    # No role check here anymore [T2-R10, D24, F-simplicity-7] — `seat` is read only because
    # `ruled_by` below wants the resolved caller's identity for the record it writes, not to
    # gate on it.
    seat = (args.seat or "").strip()
    ruler = coord.gate(args, "rule-guard")
    pkg = coord.package_dir(args)
    base = coord.base_dir(args)
    go = bool(getattr(args, "go", False))

    # LAYER 1, `input`: the SHAPE of what was typed. Checked before anything on disk is consulted,
    # so a malformed invocation never reports on a package it was never going to write to.
    raw_kv = (args.guard or "").strip()
    if raw_kv.count("=") != 1 or raw_kv.startswith("=") or raw_kv.endswith("="):
        coord.refuse("input",
               f"'{raw_kv}' is not a `<key>=<value>` pair. The guard is TWO halves and both are "
               f"required — a bare key rules nothing and a bare value rules nothing about what.\n"
               f"  {coord.coord_invocation(args)} rule-guard {seat or '<seat>'} "
               f"retirement-safe=yes --source \"<where it was measured>\"", 2)
    key, value = (x.strip() for x in raw_kv.split("=", 1))
    source = (getattr(args, "source", None) or "").strip()
    if not source:
        coord.refuse("input",
               "--source is MANDATORY and was not given. It cites WHERE this value was measured "
               "or ruled — a ledger anchor, a record path, or a message id. A guard ruling with "
               "no source is folklore: by VALUE it is indistinguishable from a guess, and the "
               "party that reads it months from now cannot tell which it was.\n"
               f"  {coord.coord_invocation(args)} rule-guard {seat} {key}={value} "
               f"--source \"planning/<pass>/<record>.md §N (derived verdict)\"", 2)

    # LAYER 2, `state`: the WORLD. Both terms read the package the ruling would be written beside.
    rows = ready.taskforce_after(pkg)
    if seat not in rows:
        coord.refuse("state",
               f"'{seat}' has no row in this run's taskforce.csv, so no edge can ever consume a "
               f"ruling about it. Seats in this run: {', '.join(sorted(rows)) or '(none)'}", 1)
    pairs = ready.guarded_pairs(pkg)
    if (seat, key) not in pairs:
        _have = ", ".join(f"`{s}[{k}=…]`" for s, k in sorted(pairs)) or "(none — this run has no " \
                                                                        "guarded `after` member)"
        coord.refuse("state",
               f"no `after` member of this run references the guard `{seat}[{key}=…]`, so this "
               f"ruling would be consumed by nothing. A dead ruling is a typo until a live edge "
               f"reads it.\n  guarded pairs this run actually has: {_have}", 1)

    current = ready.load_guard_values(base).get((seat, key))
    consumers = ", ".join(f"`{t}`" for t in pairs[(seat, key)])
    # D2: the row names the CALLER, which the gate above has already proven is the seat the pair is
    # about — never a constant. `DISPOSITION_WRITER_LEADER` was right while the leader was the only
    # admitted writer and is a lie now. The `--force` lane can still carry an unresolvable identity
    # past the gate; that writes `unresolved` rather than an empty cell, because an empty `ruled-by`
    # renders as `(unrecorded)` and is indistinguishable from a row written before the column
    # existed — which is exactly the folklore `--source` is mandatory to prevent.
    ruled_by = ruler or "unresolved"
    if not go:
        # The CURRENT row is read off disk and printed, never assumed absent: a leader about to
        # supersede its own earlier ruling must see the value it is superseding, and the file is
        # append-only precisely so that value still exists to be shown.
        if current is None:
            print(f"{coord.c(seat, coord.C_LABEL)}  `{key}` is UNRULED — nothing is recorded for this pair "
                  f"yet.")
        else:
            print(f"{coord.c(seat, coord.C_LABEL)}  `{key}` currently rules `{current['value']}` "
                  f"(source: {current['source'] or '(none recorded)'}, "
                  f"by {current['ruled-by'] or '(unrecorded)'}, {current['stamp'] or '(unstamped)'})"
                  + ("" if current["value"] != value else " — the SAME value you are about to "
                                                          "record; the append would be a no-op in "
                                                          "effect, and a second row on disk"))
        print(f"    would append: {key}={value}, source `{source}`, ruled-by "
              f"`{ruled_by}`")
        print(f"    consumed by: {consumers}")
        print("    (report only — nothing was written. Re-run with --go to record the ruling.)")
        return
    written = ready.append_guard_value(base, seat, key, value, source, ruled_by)
    print(f"{coord.c(seat, coord.C_LABEL)}  RULED `{key}={value}` by {ruled_by}")
    print(f"    {ready.GUARD_VALUES_FILE}: appended — source `{written['source']}`, "
          f"stamp {written['stamp']}")
    if current is not None and current["value"] != value:
        print(f"    SUPERSEDES the earlier `{current['value']}` — that row stays on disk; the "
              f"LAST row per (seat, key) wins, so the record of what was ruled first survives")
    print(coord.c(f"\nThe ruling is recorded, and the row names the party that made it and the source it "
            f"was measured at. It also DISCHARGES this seat's check-out debt for `{key}` — a "
            f"`done` check-out is refused while a guard the seat owes is unwritten (D3). "
            f"Advancement follows the ordinary arithmetic ({coord.coord_invocation(args)} ready-seats) "
            f"— the guarded edge now reads this value, and still requires this seat's own `done`.",
            coord.C_HINT))


