#!/usr/bin/env python3
"""team-monitor — the run's ONE raw-source sensor (settle ledger R24).

It is the only component that touches raw sources (tmux panes, harness session files,
/proc RAM + pressure, pending prompts) and its sole output is one canonical timestamped
snapshot at {goal}/runs/run-{n}/state.json. goal-watcher-job and teamview read that file
and never the raw sources — PRIN-2 parity: agents query the same state.json the dashboard
renders.

INHERITANCE, not reimplementation. The per-pane harness/model/context engine is the
existing sensor at ../ctx-monitor/ctx_monitor.py; this module IMPORTS it by path and calls
its module-level API (`pane_records`, `list_panes`, `capture_pane`). It contains no copy of
that source and never edits it (ruling p-m2-sensor-ruling-CORRECTED). What team-monitor
adds on top is what the engine does not expose: seat names from the run roster, per-seat
RAM and liveness, prompt-pending, and box-level pressure.

TIMESTAMP DISCIPLINE. `captured_at` is stamped as the first act of capture(), before any
raw read. Serialization stamps `written_at` separately and NEVER re-stamps captured_at, so
a frozen sensor produces a snapshot that visibly ages — which is the whole basis of task
7.32's staleness tripwire and 7.34's age display.

AGENT TYPE (task 7.80). Each seat row carries `agent_type` + `agent_type_source`, DECLARED in
the seat descriptor and only observed here — the registry record behind it is `agent type`
(values `master | staff | worker | verifier`, settled-by decisions.md#d-agent-taxonomy). This
module holds NO value list and validates nothing.

⚠⚠ THIS FIELD IS A SENSOR OBSERVATION OF A DECLARED CLAIM AND IS NEVER AN AUTHORIZATION; THE
IDENTITY GATE IS THE ONLY AUTHORIZATION. Nothing may ever gate a permission on it. Binding,
and stated here rather than implied BECAUSE THE FIELD'S NAME NO LONGER CARRIES IT: the key was
spelled `class` until 2026-07-28, and its very DIFFERENCE from the registry's term was doing
defensive work — a reader could not mistake it for the permission-bearing concept. The rename
to exact registry parity (owner ruling `r-agent-type-field-name`, PRIN-10) REMOVED that passive
defence, and the registry's own definition of `agent type` says it is a classification "which
DRIVES SOME OF THE AGENT'S PERMISSIONS". IT DOES NOT DO SO HERE. See `declared_agent_types` for
the claim / observation / authorization split the bar rests on.

LIFECYCLE. Run-scoped: `start` is idempotent (safe as a room-creation hook) and the loop
EXITS when the room's tmux session disappears, so the close is deterministic by
construction rather than by remembering. Exactly one writer is enforced mechanically by an
exclusive lock — a second writer refuses to start.
"""

import argparse
import errno
import fcntl
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "team-monitor/1"
DEFAULT_INTERVAL = 20.0
HERE = Path(__file__).resolve().parent
SENSOR_PATH = HERE.parent / "ctx-monitor" / "ctx_monitor.py"


# ---------- inheritance ----------

_SENSOR = None


def sensor(path=None):
    """The existing raw sensor, imported by path. Never copied, never edited."""
    global _SENSOR
    if _SENSOR is None:
        p = Path(path) if path else SENSOR_PATH
        spec = importlib.util.spec_from_file_location("ctx_monitor", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SENSOR = mod
    return _SENSOR


# ---------- raw reads team-monitor owns (the engine exposes none of these) ----------

def read_proc(path):
    try:
        return Path(path).read_text()
    except OSError:
        return ""


def meminfo():
    out = {}
    for ln in read_proc("/proc/meminfo").splitlines():
        k, _, v = ln.partition(":")
        v = v.strip().split(" ")[0]
        if v.isdigit():
            out[k] = int(v)  # kB
    return out


def pressure(resource="memory"):
    """/proc/pressure/<resource> -> {'some_avg10':..,'full_total':..}; {} when absent."""
    out = {}
    for ln in read_proc(f"/proc/pressure/{resource}").splitlines():
        parts = ln.split()
        if not parts:
            continue
        kind = parts[0]
        for kv in parts[1:]:
            k, _, v = kv.partition("=")
            try:
                out[f"{kind}_{k}"] = float(v)
            except ValueError:
                pass
    return out


def box_facts():
    mi = meminfo()
    load = read_proc("/proc/loadavg").split()
    swap_total = mi.get("SwapTotal", 0)
    return {
        "available_mb": mi.get("MemAvailable", 0) // 1024,
        "total_mb": mi.get("MemTotal", 0) // 1024,
        "swap_used_mb": (swap_total - mi.get("SwapFree", 0)) // 1024,
        "swap_total_mb": swap_total // 1024,
        "load1": float(load[0]) if len(load) > 2 else None,
        "load5": float(load[1]) if len(load) > 2 else None,
        "load15": float(load[2]) if len(load) > 2 else None,
        "cores": os.cpu_count(),
        "pressure_memory": pressure("memory"),
    }


def ps_table():
    """{pid: {'ppid':int,'rss_kb':int,'comm':str}} — one ps call for RAM and liveness."""
    r = subprocess.run(["ps", "-eo", "pid=,ppid=,rss=,comm="],
                       capture_output=True, text=True)
    table = {}
    for ln in r.stdout.splitlines():
        parts = ln.split(None, 3)
        if len(parts) < 4:
            continue
        try:
            table[int(parts[0])] = {"ppid": int(parts[1]), "rss_kb": int(parts[2]),
                                    "comm": parts[3].strip()}
        except ValueError:
            continue
    return table


def children_index(table):
    idx = {}
    for pid, rec in table.items():
        idx.setdefault(rec["ppid"], []).append(pid)
    return idx


def tree_pids(root, kids, limit=4000):
    out, stack = [], [root]
    while stack and len(out) < limit:
        pid = stack.pop()
        out.append(pid)
        stack.extend(kids.get(pid, ()))
    return out


# Permission / trust prompts a stuck seat's pane tail shows. Written here rather than
# reused from teamview: teamview is the renderer and, after the R24 cutover, reads
# state.json instead of panes — prompt-pending is the sensor's field to produce.
PROMPT_PATTERNS = tuple(re.compile(p, re.I | re.M) for p in (
    r"do you want to",
    r"do you trust",
    r"esc to cancel",
    r"action required",
    r"^\s*[>❯]?\s*1\.\s*yes\b",
    r"allow this",
))


def prompt_pending(tail):
    return any(p.search(tail) for p in PROMPT_PATTERNS)


# ---------- the run roster ----------

def roster(package):
    """{seat: {'pane','active','checked_in','ctx_refresh'}} from the run package.

    coordination/workers.md is the live roster (script-managed); a renewed seat appends a
    row under the same name, so the LAST row for a name wins.

    ⚠ THE ctx-refresh THRESHOLD COMES FROM THE SEAT'S DESCRIPTOR, NOT FROM taskforce.csv.
    The CSV column is a birth-time copy that is never revisited and drifts LOOSER as seats are
    tightened (`G-255`); it is kept only as a fallback for a seat whose descriptor declares no
    threshold. See declared_ctx_refresh for the measurement and for why the fix lives here
    rather than in either consumer.
    """
    out = {}
    wm = Path(package) / "coordination" / "workers.md"
    if wm.exists():
        for ln in wm.read_text(encoding="utf-8").splitlines():
            if not ln.startswith("|"):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 5 or cells[0] in ("agent", "") or set(cells[0]) <= set("-: "):
                continue
            out[cells[0]] = {"pane": cells[2], "active": cells[1].lower() == "yes",
                             "checked_in": cells[4], "ctx_refresh": None}
    tf = Path(package) / "taskforce.csv"
    if tf.exists():
        import csv
        with tf.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                seat = (row.get("seat") or "").strip()
                if not seat:
                    continue
                raw = (row.get("ctx-refresh") or "").strip()
                rec = out.setdefault(seat, {"pane": "", "active": False,
                                            "checked_in": "", "ctx_refresh": None})
                rec["ctx_refresh"] = int(raw) if raw.isdigit() else None
    for seat, thr in declared_ctx_refresh(package).items():
        rec = out.setdefault(seat, {"pane": "", "active": False,
                                    "checked_in": "", "ctx_refresh": None})
        rec["ctx_refresh"] = thr
    return out


# ---------- the DECLARED agent type (task 7.80) ----------

# The explicit record of an ABSENT declaration. It is not an agent type and never a default:
# the aggregate this field exists for ("live task-executor count == 0 while the free set is
# non-empty") is wrong in whichever direction a default leans, so absence is REPORTED.
# ⚠ THIS IS A VALUE, NOT A KEY — the 2026-07-28 key rename deliberately did not touch it.
UNCLASSIFIED = "unclassified"

_FM_SEAT = re.compile(r"^(?:seat|agent):\s*(\S+)\s*$", re.MULTILINE)
# ⚠ The descriptor key is `agent_type:` as of 2026-07-28 (owner ruling
# `r-agent-type-field-name`). A descriptor still declaring the OLD `class:` spelling reads
# UNCLASSIFIED/undeclared — LOUDLY, which is the intended behaviour: an undeclared seat is a
# finding, never a silent default. Nothing here accepts both spellings, because a compatibility
# shim is exactly the "renderers disagreeing about the field's name" the rename was ruled
# ATOMIC to prevent.
_FM_AGENT_TYPE = re.compile(r"^agent_type:\s*(.+?)\s*$", re.MULTILINE)
# The same pattern coord.py:228 uses for the same key, so every consumer of a seat's
# refresh threshold reads the ONE place a threshold is set. See declared_ctx_refresh.
_FM_CTX_REFRESH = re.compile(r"^ctx-refresh:\s*(\d+)\s*$", re.MULTILINE)


def seats_dir(package):
    """The run's descriptor folder: seats/ (the KG run-folder form) or the legacy workers/.
    Same resolution order coord.py uses, so both tools read the same descriptors."""
    p = Path(package)
    s = p / "seats"
    return s if s.is_dir() else p / "workers"


def declared_agent_types(package):
    """{seat: agent-type-string-or-empty} — each seat's agent type, READ FROM ITS OWN DESCRIPTOR.

    ⚠ THERE IS DELIBERATELY NO VALUE LIST IN THIS FILE, and adding one is forbidden (leader
    ruling `ruling-780-literals-withdrawn-derive-dont-list.md`, RULING 2). Whatever string a
    descriptor declares is published verbatim; this module validates nothing and knows no
    vocabulary. The reason is already ruled in code at `coord.py:338-345`, for `observer:` /
    `auto-wake:` / `senders:`: a name list inside a shared tool encodes ONE campaign's role
    vocabulary into every run, and `SPECIAL_CASE_SEATS` named its members while its own
    comment described a MANDATE — which is exactly how the chief-of-staff came to be omitted
    from the set whose definition described it. A MANDATE CANNOT BE EXPRESSED AS A NAME LIST,
    so the next differently-named seat is forgotten identically.

    A key is absent from this map when the seat has no descriptor at all; it maps to "" when
    the descriptor exists and declares no agent type. Those are DIFFERENT answers —
    `agent_type_of` reports which — because "nobody wrote a descriptor" and "the descriptor is
    silent" need different fixes and only one of them is the staffer's standing duty.

    THE REGISTRY RECORD THIS FIELD PUBLISHES is `agent type` — "the classifier of an agent's
    team function — the four-member TOP set (`master`, `staff`, `worker`, `verifier`)"
    (`sd-graph show "agent type"`, settled-by decisions.md#d-agent-taxonomy). The values live
    THERE, deliberately not here. ⚠ THE KEY IS SPELLED `agent_type:` AS OF 2026-07-28 — exact
    registry parity, owner ruling `r-agent-type-field-name` (PRIN-10, terminology is king). It
    was spelled `class:` before that, which was the owner's word in `r-room-flag-built-portable`;
    the rename made the field name and the record name the same one word for the same one idea.

    ⚠⚠ NOTHING MAY EVER GATE A PERMISSION ON THIS FIELD. BINDING (leader ruling
    `ruling-780-vocabulary-agent-type.md`, item B; promoted to a CONDITION of the rename by
    `r-agent-type-field-name`). THIS FIELD IS A SENSOR OBSERVATION OF A DECLARED CLAIM AND IS
    NEVER AN AUTHORIZATION; THE IDENTITY GATE IS THE ONLY AUTHORIZATION.

        the descriptor's declared type  -> a CLAIM
        this field in state.json        -> a SENSOR OBSERVATION of that claim
        the identity gate               -> the ONLY authorization

    ⚠ THE BAR IS WRITTEN OUT HERE BECAUSE THE NAME NO LONGER CARRIES IT, and that is the whole
    reason the rename needed a condition attached. The registry's own definition of an agent
    type says it is a classification "which DRIVES SOME OF THE AGENT'S PERMISSIONS", so a field
    now named after that record WILL look like a privilege token to a future reader — where the
    old name's mere DIFFERENCE from the registry term used to make the mistake impossible. That
    passive defence is gone; this paragraph is what replaced it, and deleting it re-opens the
    hole. A self-declared value read back by a sensor is not an authorization. The moment
    anything keys a permission on it, EDITING A DESCRIPTOR BECOMES A PRIVILEGE GRANT — exactly
    the `realizes: master` escalation-by-descriptor that `coord.py:205-216` already refused.
    """
    out = {}
    wdir = seats_dir(package)
    if not wdir.is_dir():
        return out
    for p in sorted(list(wdir.glob("*.md")) + list(wdir.glob("*/agent.md"))
                    + list(wdir.glob("*/seat.md"))):
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        fm = text[:end]
        m = _FM_SEAT.search(fm)
        if not m:
            continue
        c = _FM_AGENT_TYPE.search(fm)
        out[m.group(1)] = c.group(1).strip() if c else ""
    return out


def declared_ctx_refresh(package):
    """{seat: int} — each seat's context-refresh threshold, READ FROM ITS OWN DESCRIPTOR.

    ⚠ THE DESCRIPTOR IS THE ONLY PLACE A THRESHOLD IS SET. `taskforce.csv` also carries a
    `ctx-refresh` column, and `roster()` still reads it — but ONLY as a fallback for a seat
    whose descriptor declares none. The roster copy is written once when the row is minted and
    is never revisited, so it records the threshold a seat was BORN with, not the one it has.

    Measured on the live run-2 package, 2026-07-28 (issue `G-255`): the descriptors and the
    roster agreed at birth for all five live seats, then three were deliberately tightened —
    chief-of-staff 55->35, owner-liaison 55->40, engineer 50->45 — while every roster row
    stayed at its birth value across all 10 commits that touched the file. ⚠ EVERY DIVERGENCE
    WAS IN THE LOOSER DIRECTION, so publishing the roster copy raises a seat's flag (by 20
    points for the chief-of-staff) and the CONTEXT check quietly stops firing while every
    surface still reports a clean sweep.

    ⚠⚠ THE TWO CONSUMERS OF THIS FIELD BOTH ALREADY BELIEVE THEY ARE READING THE DESCRIPTOR,
    AND THAT IS WHY THE FIX BELONGS HERE RATHER THAN IN EITHER OF THEM:

        teamview.snapshot_thresholds()  "straight off the snapshot's own seat records" —
                                        G-153's structural cure, which removed a SECOND
                                        drifting path by taking the threshold from the same
                                        snapshot as the ctx% it gates. Sound; it just landed
                                        on a field the sensor was filling from the roster.
        goal-watcher-job.py ROW 3       "its briefing's `ctx-refresh`" — its own comment.

    Feeding this field from the descriptor makes both comments true and needs no change in
    either consumer. Fixing it in the consumers instead would re-create exactly the second
    path G-153 was filed to remove.

    A seat absent from this map declares no threshold; `roster()` then falls back to the CSV
    and, failing that, publishes None — which every consumer already reads as "this seat
    carries no threshold", never as "zero".
    """
    out = {}
    wdir = seats_dir(package)
    if not wdir.is_dir():
        return out
    for p in sorted(list(wdir.glob("*.md")) + list(wdir.glob("*/agent.md"))
                    + list(wdir.glob("*/seat.md"))):
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not text.startswith("---"):
            continue
        end = text.find("\n---", 3)
        if end == -1:
            continue
        fm = text[:end]
        m = _FM_SEAT.search(fm)
        c = _FM_CTX_REFRESH.search(fm)
        if m and c:
            out[m.group(1)] = int(c.group(1))
    return out


def agent_type_of(seat, decls):
    """(agent_type, source) for one row. UNCLASSIFIED is always paired with WHY.

    `no-seat` is the case a descriptor-declared field cannot reach by construction: a pane
    with no roster row has no descriptor to declare anything. The parked owner door is
    exactly that pane, and it reads unclassified for a structural reason rather than a
    missing edit — which is a different finding from an undeclared seat, so it is a
    different source string.
    """
    if not seat:
        return UNCLASSIFIED, "no-seat"
    if seat not in decls:
        return UNCLASSIFIED, "no-descriptor"
    declared = decls[seat]
    if not declared:
        return UNCLASSIFIED, "undeclared"
    return declared, "descriptor"


def default_session(package):
    """The room is the goal's tmux session: .../goals/<goal>/runs/<run> -> <goal>."""
    p = Path(package).resolve()
    return p.parent.parent.name


def session_alive(session):
    return subprocess.run(["tmux", "has-session", "-t", session],
                          capture_output=True).returncode == 0


def run_closed(package):
    """True once THIS RUN's row in the goal's runs.csv reads closed.

    The session is the GOAL's room, shared by every run of that goal, so `tmux has-session`
    cannot tell a closed run from a live one: run-2 was bootstrapped inside run-1's session,
    and run-1's sensor went on writing run-1/state.json for nearly six hours after run-1
    closed at 13:11 — a stale sensor watching a corpse (G-103's shape at the sensor layer,
    found while verifying task 7.33). The run-level close signal is the run-log row, not the
    room.

    FAILS OPEN by construction: an absent, unreadable or unparseable runs.csv returns False,
    so a broken meter can never stop a healthy sensor — the posture coord.py already takes on
    its own memory gate.
    """
    import csv
    p = Path(package).resolve()
    try:
        with (p.parent.parent / "runs.csv").open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("run-id") or "").strip() == p.name:
                    return (row.get("state") or "").strip().lower() == "closed"
    except (OSError, csv.Error, UnicodeDecodeError):
        return False
    return False


# ---------- capture ----------

def capture(package, session=None, sensor_path=None):
    """One snapshot. captured_at is stamped BEFORE any raw read and never restamped."""
    captured_at = time.time()
    t0 = time.monotonic()

    session = session or default_session(package)
    eng = sensor(sensor_path)
    panes = {p["pane_id"]: p for p in eng.list_panes(session)}
    records = eng.pane_records(session)
    procs = ps_table()
    kids = children_index(procs)
    rost = roster(package)
    decls = declared_agent_types(package)
    seat_by_pane = {v["pane"]: k for k, v in rost.items() if v.get("pane")}

    seats = []
    for rec in records:
        pane_id = rec["pane_id"]
        pane = panes.get(pane_id, {})
        try:
            pane_pid = int(pane.get("pid") or 0)
        except ValueError:
            pane_pid = 0
        pids = tree_pids(pane_pid, kids) if pane_pid else []
        rss_kb = sum(procs.get(p, {}).get("rss_kb", 0) for p in pids)
        harness_pid = next((p for p in pids
                            if procs.get(p, {}).get("comm") in eng.HARNESSES), None)
        tail = "\n".join(eng.capture_pane(pane_id).splitlines()[-8:])
        seat = seat_by_pane.get(pane_id, "")
        seat_agent_type, agent_type_source = agent_type_of(seat, decls)
        seats.append({
            "seat": seat,
            "agent_type": seat_agent_type,
            "agent_type_source": agent_type_source,
            "pane": pane_id,
            "window": rec.get("window"),
            "window_name": rec.get("window_name") or "",
            "window_active": bool(rec.get("window_active")),
            "pane_active": bool(rec.get("pane_active")),
            "title": rec.get("title"),
            "cwd": pane.get("cwd", ""),
            "harness": rec.get("harness") or "",
            "harness_pid": harness_pid,
            "pane_pid": pane_pid or None,
            "model": rec.get("model") or "",
            "model_source": rec.get("model_source") or "",
            "ctx_pct": rec.get("ctx_pct"),
            "ctx_tokens": rec.get("ctx_tokens"),
            "window_tokens": rec.get("window_tokens"),
            "ctx_ambiguous": bool(rec.get("ambiguous")),
            "ctx_source": rec.get("source") or "",
            "ctx_refresh": rost.get(seat, {}).get("ctx_refresh"),
            "last_activity": rec.get("as_of"),
            "last_activity_age_s": (round(captured_at - rec["as_of"], 1)
                                    if rec.get("as_of") else None),
            "prompt_pending": prompt_pending(tail),
            "ram_mb": round(rss_kb / 1024, 1),
            "liveness": ("live" if harness_pid else
                         ("shell" if rec.get("shell") else "no-harness")),
            "roster_active": rost.get(seat, {}).get("active"),
        })

    return {
        "schema": SCHEMA,
        "captured_at": round(captured_at, 3),
        "captured_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(captured_at)),
        "capture_ms": round((time.monotonic() - t0) * 1000),
        "session": session,
        "session_alive": session_alive(session),
        "package": str(Path(package).resolve()),
        "sensor": str((Path(sensor_path) if sensor_path else SENSOR_PATH).resolve()),
        "box": box_facts(),
        "seats": seats,
        "roster_absent": absent_rows(rost, panes, seats, decls),
    }


def absent_rows(rost, panes, seats, decls):
    """The GHOSTROW input (task 7.32): a roster row claiming to be active whose pane is
    either gone from the room or holds no harness process. Two distinct failures, reported
    separately — a pane that vanished is a different incident from a harness that died in a
    pane that is still there, and the second is the one that looks healthy from a distance.

    Ghost rows carry `agent_type`/`agent_type_source` for the same reason the live rows do: a
    room aggregate that counted only the live rows would silently exclude exactly the seats whose
    absence it is meant to notice."""
    live_harness = {s["pane"] for s in seats if s["liveness"] == "live"}
    out = []
    for seat, r in sorted(rost.items()):
        if not r.get("active"):
            continue
        pane = r.get("pane") or ""
        seat_agent_type, agent_type_source = agent_type_of(seat, decls)
        if pane not in panes:
            out.append({"seat": seat, "agent_type": seat_agent_type,
                        "agent_type_source": agent_type_source,
                        "pane": pane, "roster_active": True,
                        "liveness": "absent",
                        "reason": "roster row active, pane not in the room"})
        elif pane not in live_harness:
            out.append({"seat": seat, "agent_type": seat_agent_type,
                        "agent_type_source": agent_type_source,
                        "pane": pane, "roster_active": True,
                        "liveness": "no-harness",
                        "reason": "roster row active, pane present but no harness process"})
    return out


# ---------- the single writer ----------

def state_path(package):
    return Path(package) / "state.json"


def lock_path(package):
    return Path(package) / "coordination" / "team-monitor.lock"


def acquire_writer_lock(package):
    """Exclusive, non-blocking. Returns the open file (keep it) or None if another writer
    holds it — 'exactly ONE writer of state.json' enforced by the kernel, not by custom."""
    p = lock_path(package)
    p.parent.mkdir(parents=True, exist_ok=True)
    fh = p.open("a+")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as e:
        if e.errno in (errno.EACCES, errno.EAGAIN):
            fh.close()
            return None
        raise
    fh.seek(0)
    fh.truncate()
    fh.write(f"{os.getpid()}\n")
    fh.flush()
    return fh


def lock_holder(package):
    p = lock_path(package)
    if not p.exists():
        return None
    try:
        pid = int(p.read_text().strip() or 0)
    except ValueError:
        return None
    return pid if pid and Path(f"/proc/{pid}").exists() else None


def write_snapshot(snap, package):
    """Serialize. Adds written_at; NEVER touches captured_at. Atomic via os.replace, so a
    reader never sees a partial snapshot."""
    out = dict(snap)
    now = time.time()
    out["written_at"] = round(now, 3)
    out["written_at_iso"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))
    out["writer_pid"] = os.getpid()
    dest = state_path(package)
    tmp = dest.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, dest)
    return dest


# ---------- commands ----------

def cmd_snapshot(args):
    """Capture and print. Writes nothing and takes no lock — safe for any reader."""
    print(json.dumps(capture(args.package, args.session, args.sensor), indent=1))
    return 0


def cmd_once(args):
    fh = acquire_writer_lock(args.package)
    if not fh:
        print(f"another writer holds {lock_path(args.package)} (pid {lock_holder(args.package)})",
              file=sys.stderr)
        return 3
    try:
        dest = write_snapshot(capture(args.package, args.session, args.sensor), args.package)
        print(dest)
        return 0
    finally:
        fh.close()


def cmd_run(args):
    """The daemon body: capture on a cadence until the room's session disappears."""
    fh = acquire_writer_lock(args.package)
    if not fh:
        print(f"refusing: another writer holds the lock (pid {lock_holder(args.package)})",
              file=sys.stderr)
        return 3
    session = args.session or default_session(args.package)
    print(f"team-monitor up: pid {os.getpid()} session {session} "
          f"interval {args.interval}s -> {state_path(args.package)}", flush=True)
    try:
        while True:
            if not session_alive(session):
                print("room gone — team-monitor exiting (deterministic close)", flush=True)
                return 0
            if run_closed(args.package):
                print("run closed in runs.csv — team-monitor exiting (deterministic close)",
                      flush=True)
                return 0
            try:
                write_snapshot(capture(args.package, session, args.sensor), args.package)
            except Exception as e:  # noqa: BLE001 — a bad pass must never kill the sensor
                print(f"capture failed: {e!r}", file=sys.stderr, flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    finally:
        fh.close()


def cmd_start(args):
    """Idempotent — safe to call from a room-creation hook (`ensure` is the same command)."""
    held = lock_holder(args.package)
    if held:
        print(f"already running (pid {held})")
        return 0
    logp = Path(args.package) / "coordination" / "team-monitor.log"
    logp.parent.mkdir(parents=True, exist_ok=True)
    log = logp.open("a")
    argv = [sys.executable, str(Path(__file__).resolve()), "run",
            "--package", str(Path(args.package).resolve()),
            "--interval", str(args.interval)]
    if args.session:
        argv += ["--session", args.session]
    if args.sensor:
        argv += ["--sensor", args.sensor]
    p = subprocess.Popen(argv, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    for _ in range(50):
        time.sleep(0.1)
        if lock_holder(args.package):
            print(f"started (pid {p.pid}) -> {logp}")
            return 0
    print(f"started (pid {p.pid}) but no lock yet — see {logp}", file=sys.stderr)
    return 1


def cmd_stop(args):
    pid = lock_holder(args.package)
    if not pid:
        print("not running")
        return 0
    os.kill(pid, 15)
    for _ in range(50):
        time.sleep(0.1)
        if not lock_holder(args.package):
            print(f"stopped (pid {pid})")
            return 0
    print(f"pid {pid} did not exit", file=sys.stderr)
    return 1


def cmd_status(args):
    """Read the snapshot the way every consumer must: from state.json, never from panes."""
    pid = lock_holder(args.package)
    dest = state_path(args.package)
    if not dest.exists():
        print(f"writer: {pid or 'none'}   snapshot: absent ({dest})")
        return 1
    snap = json.loads(dest.read_text())
    age = time.time() - snap.get("captured_at", 0)
    if args.json:
        print(json.dumps({"writer_pid": pid, "age_s": round(age, 1), **snap}, indent=1))
        return 0
    box = snap.get("box", {})
    print(f"writer: {pid or 'none'}   captured: {snap.get('captured_at_iso')}   "
          f"age: {age:.0f}s   seats: {len(snap.get('seats', []))}   "
          f"absent-rows: {len(snap.get('roster_absent', []))}")
    print(f"box: {box.get('available_mb')}MB avail  swap {box.get('swap_used_mb')}MB  "
          f"load5 {box.get('load5')}  psi-mem-some60 "
          f"{box.get('pressure_memory', {}).get('some_avg60')}")
    for s in snap.get("seats", []):
        if not s.get("harness"):
            continue
        ctx = f"{s['ctx_pct']:.0f}%" if s.get("ctx_pct") is not None else "-"
        print(f"  {s['pane']:<5} {(s['seat'] or '?'):<22} {s['harness']:<9} "
              f"{s['model'][:18]:<18} {ctx:>5} {s['ram_mb']:>7}MB {s['liveness']:<9}"
              f"{'  PROMPT' if s['prompt_pending'] else ''}")
    return 0


def cmd_selftest(args):
    failures = []

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        if not cond:
            failures.append(name)

    # inheritance is real, and it is the module on disk
    eng = sensor()
    check("sensor imports by path", hasattr(eng, "pane_records") and hasattr(eng, "list_panes"))
    check("sensor is the ctx-monitor engine, not a copy",
          Path(eng.__file__).resolve() == SENSOR_PATH.resolve())
    # No copied sensor code. Checked structurally over EVERY top-level function in both
    # files rather than against a hand-picked name or two: any function the sensor already
    # defines is a re-implementation unless it is CLI boilerplate, and the two boilerplate
    # names allowed through are then required to differ in body from the sensor's.
    import ast
    mine = {n.name: n for n in ast.parse(Path(__file__).read_text()).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    theirs = {n.name: n for n in ast.parse(SENSOR_PATH.read_text()).body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    boilerplate = {"main", "cmd_selftest"}
    shared = set(mine) & set(theirs)
    check(f"no sensor function re-implemented here (shared names: "
          f"{sorted(shared) or 'none'}; allowed boilerplate: {sorted(boilerplate)})",
          shared <= boilerplate)
    check("the shared boilerplate names are not copies either",
          all(ast.dump(mine[n]) != ast.dump(theirs[n]) for n in shared & boilerplate))

    # timestamp discipline: capture stamps, serialize does not restamp
    fake = {"schema": SCHEMA, "captured_at": 1000.0, "captured_at_iso": "x", "seats": []}
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        write_snapshot(fake, td)
        got = json.loads((Path(td) / "state.json").read_text())
        check("write_snapshot preserves captured_at", got["captured_at"] == 1000.0)
        check("write_snapshot stamps written_at separately",
              got["written_at"] != got["captured_at"])
        check("state.json is written atomically (no .tmp left)",
              not (Path(td) / "state.json.tmp").exists())

        # single writer: the second acquirer is refused
        a = acquire_writer_lock(td)
        b = acquire_writer_lock(td)
        check("first writer acquires the lock", a is not None)
        check("second writer is REFUSED (one writer of state.json)", b is None)
        if a:
            a.close()
        c = acquire_writer_lock(td)
        check("lock is released on close", c is not None)
        if c:
            c.close()

    # box facts are real reads, not placeholders
    box = box_facts()
    check("box available_mb is a real read", isinstance(box["available_mb"], int)
          and box["available_mb"] > 0)
    check("box carries swap + load", box["swap_total_mb"] is not None and box["load5"] is not None)
    check("box carries /proc/pressure/memory some+full",
          any(k.startswith("some_") for k in box["pressure_memory"])
          and any(k.startswith("full_") for k in box["pressure_memory"]))

    # prompt detection fires and, more importantly, does NOT fire on ordinary output
    check("prompt_pending fires on a permission dialog",
          prompt_pending("Do you want to proceed?\n> 1. Yes\nEsc to cancel"))
    check("prompt_pending is quiet on ordinary output",
          not prompt_pending("running tests\n12 passed\n"))

    # roster parsing tolerates the renewed-seat case
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "coordination").mkdir()
        (Path(td) / "coordination" / "workers.md").write_text(
            "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
            "|---|---|---|---|---|---|---|\n"
            "| leader | no | %4 | old | t1 | closed | 1 |\n"
            "| leader | yes | %17 | new | t2 |  | 2 |\n")
        (Path(td) / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,leader,,claude,opus,high,50,m0\n")
        r = roster(td)
        check("roster: last row wins for a renewed seat", r["leader"]["pane"] == "%17")
        check("roster: active parsed", r["leader"]["active"] is True)
        check("roster: ctx-refresh falls back to taskforce.csv when no descriptor declares one",
              r["leader"]["ctx_refresh"] == 50)

    # G-255: the descriptor OUTRANKS the CSV, and the fixture makes them DISAGREE so the check
    # cannot pass if the descriptor is ignored. The disagreement runs LOOSER-IN-THE-CSV — the
    # only direction measured live, and the one that silently mutes the flag.
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "coordination").mkdir()
        (Path(td) / "coordination" / "workers.md").write_text(
            "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
            "|---|---|---|---|---|---|---|\n"
            "| tightened | yes | %1 | w | t1 |  | 1 |\n"
            "| csv-only | yes | %2 | w | t1 |  | 1 |\n")
        (Path(td) / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,tightened,,claude,opus,high,55,m0\n"
            "tf-2,csv-only,,claude,opus,high,60,m0\n")
        sd = Path(td) / "seats"
        (sd / "tightened").mkdir(parents=True)
        (sd / "tightened" / "seat.md").write_text(
            "---\nseat: tightened\nharness: claude\nctx-refresh: 35\n---\nbrief\n")
        (sd / "csv-only").mkdir(parents=True)
        (sd / "csv-only" / "seat.md").write_text(
            "---\nseat: csv-only\nharness: claude\n---\nbrief\n")
        r = roster(td)
        check("G-255: a tightened descriptor BEATS the stale CSV copy (35, not 55)",
              r["tightened"]["ctx_refresh"] == 35)
        check("G-255: a descriptor declaring none still falls back to the CSV (60)",
              r["csv-only"]["ctx_refresh"] == 60)
        check("G-255: declared_ctx_refresh reports only descriptor-declared thresholds",
              declared_ctx_refresh(td) == {"tightened": 35})

    # GHOSTROW: both failure shapes, and — the check that matters — no ghost for a healthy
    # seat, because a detector that fires on everything is not a detector.
    rost = {"alive": {"active": True, "pane": "%1"},
            "vanished": {"active": True, "pane": "%9"},
            "hollow": {"active": True, "pane": "%2"},
            "departed": {"active": False, "pane": "%3"}}
    panes = {"%1": {}, "%2": {}, "%3": {}}
    seats_ = [{"pane": "%1", "liveness": "live"}, {"pane": "%2", "liveness": "no-harness"},
              {"pane": "%3", "liveness": "shell"}]
    got = {g["seat"]: g["liveness"] for g in absent_rows(rost, panes, seats_, {})}
    check("GHOSTROW: an active row whose pane left the room", got.get("vanished") == "absent")
    check("GHOSTROW: an active row whose pane lost its harness",
          got.get("hollow") == "no-harness")
    check("GHOSTROW: a healthy seat raises nothing", "alive" not in got)
    check("GHOSTROW: a checked-out seat raises nothing", "departed" not in got)

    check("default_session derives the room from the package path",
          default_session("/x/goals/my-goal/runs/run-1") == "my-goal")

    # ---- the declared agent type (task 7.80) ----
    # Four descriptor states, and the ABSENCES are checked as hard as the presence: an
    # aggregate built on this field is wrong in whichever direction a default leans, so
    # "unclassified" must arrive with the REASON it is unclassified and never as a value.
    with tempfile.TemporaryDirectory() as td:
        sd = Path(td) / "seats"
        for name, fm in (
            # a nonsense value NO vocabulary would admit — this is the check that proves
            # there is no enum and no name list here, which RULING 2 forbids. If someone
            # ever adds validation, this is the check that fails.
            ("declared", "---\nseat: declared\nagent_type: zzz-not-a-real-type\n---\nbody\n"),
            ("silent", "---\nseat: silent\nharness: claude\n---\nbody\n"),
            # ⚠ THE RENAME'S OWN REGRESSION CHECK (2026-07-28, `r-agent-type-field-name`). This
            # descriptor declares the WITHDRAWN `class:` spelling. It must read
            # UNCLASSIFIED/undeclared — the key was renamed, NOT aliased.
            #
            # WHY THIS CHECK IS NOT BLIND, which every other check in this block is vulnerable to
            # being: renaming a key and rewriting the fixtures that assert it passes either way,
            # because the harness supplies both sides. This one asserts the NEW behaviour against
            # the OLD spelling, so it can only pass if the rename actually happened, and it FAILS
            # the moment anyone adds a back-compat shim accepting both names — which is the
            # "renderers disagreeing about the field's name" the owner ruled ATOMIC to prevent.
            ("legacy-key", "---\nseat: legacy-key\nclass: staff\n---\nbody\n"),
        ):
            (sd / name).mkdir(parents=True)
            (sd / name / "seat.md").write_text(fm)
        # a legacy flat workers/-form descriptor must be read too
        (sd / "flat.md").write_text("---\nagent: flat\nagent_type: legacy-form\n---\nbody\n")
        d = declared_agent_types(td)
        check("agent_type: read verbatim from the seat descriptor — NO enum, NO name list",
              agent_type_of("declared", d) == ("zzz-not-a-real-type", "descriptor"))
        check("agent_type: the legacy flat `agent:` descriptor form is read too",
              agent_type_of("flat", d) == ("legacy-form", "descriptor"))
        check("agent_type: a descriptor that declares nothing reads UNCLASSIFIED/undeclared",
              agent_type_of("silent", d) == (UNCLASSIFIED, "undeclared"))
        check("agent_type: a descriptor still on the WITHDRAWN `class:` key reads "
              "UNCLASSIFIED/undeclared — renamed, NEVER aliased (r-agent-type-field-name)",
              agent_type_of("legacy-key", d) == (UNCLASSIFIED, "undeclared"))
        check("agent_type: a seat with no descriptor reads UNCLASSIFIED/no-descriptor",
              agent_type_of("nobody", d) == (UNCLASSIFIED, "no-descriptor"))
        check("agent_type: a pane with no seat reads UNCLASSIFIED/no-seat (parked door's case)",
              agent_type_of("", d) == (UNCLASSIFIED, "no-seat"))
        check("agent_type: UNCLASSIFIED is never silently substituted for a declared value",
              all(agent_type_of(s, d)[0] != UNCLASSIFIED for s in ("declared", "flat")))
        # a ghost row carries the field too, or a room aggregate would exclude exactly the
        # seats whose absence it exists to notice
        ghost = absent_rows({"declared": {"active": True, "pane": "%9"}}, {}, [], d)
        check("agent_type: roster_absent rows carry agent_type + agent_type_source",
              ghost[0]["agent_type"] == "zzz-not-a-real-type"
              and ghost[0]["agent_type_source"] == "descriptor")
        # ⚠ The OLD keys must be GONE from the emitted row, not merely accompanied by the new
        # ones. A rename that leaves both keys present is the disagreement, not the fix.
        check("agent_type: the withdrawn `class`/`class_source` keys are ABSENT from the row",
              "class" not in ghost[0] and "class_source" not in ghost[0])

    print(f"\n{'PASS' if not failures else 'FAIL'} — {len(failures)} failure(s)")
    return 1 if failures else 0


def main():
    ap = argparse.ArgumentParser(prog="team-monitor", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, help_, package=True):
        p = sub.add_parser(name, help=help_)
        p.set_defaults(fn=fn)
        if package:
            p.add_argument("--package", required=True, help="absolute run-folder path")
            p.add_argument("--session", help="tmux session (default: the goal folder name)")
            p.add_argument("--sensor", help="override the inherited ctx-monitor path")
        return p

    add("snapshot", cmd_snapshot, "capture and print JSON; writes nothing, takes no lock")
    add("once", cmd_once, "capture and write state.json once")
    p = add("run", cmd_run, "foreground loop until the room's session disappears")
    p.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    for name, help_ in (("start", "start the loop detached; idempotent"),
                        ("ensure", "alias of start — the room-creation hook form")):
        p = add(name, cmd_start, help_)
        p.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    add("stop", cmd_stop, "stop the running loop")
    p = add("status", cmd_status, "read state.json (never the panes) and report its age")
    p.add_argument("--json", action="store_true")
    add("selftest", cmd_selftest, "self-checks; exit 0 clean", package=False)

    args = ap.parse_args()
    sys.exit(args.fn(args))


if __name__ == "__main__":
    main()
