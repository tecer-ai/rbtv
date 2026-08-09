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


_COORD = None


def coord():
    """The coordination CLI, imported by path. Never copied, never edited — same inheritance
    discipline as `sensor()` above.

    ONE importer, CACHED. Three symbols are borrowed from it (`daemon_heart_db`, `ready_seat_rows`,
    `goal_dir`) and `capture()` spends all three on EVERY cadence, so re-executing a
    27k-line module per call is a cost the loop would pay forever (measured: ~49 ms per import).
    The uncached import this replaces was affordable only while `heart_db_path` was its one
    caller."""
    global _COORD
    if _COORD is None:
        p = HERE.parent.parent.parent / "ignite" / "team-kit" / "coord.py"
        spec = importlib.util.spec_from_file_location("_tm_coord", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _COORD = mod
    return _COORD


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


class SessionUnresolved(RuntimeError):
    """The room's session name could not be resolved. There is NO default (`G-296`)."""


def tmux_session_name(target):
    """Session name of a NAMED pane ('' when unresolvable) — the `coord.py:1218` form.

    ⚠ NOT `ctx_monitor.current_session()`: that answers for the CALLER's own `$TMUX_PANE`, which
    a detached daemon does not have at all and which, when set, is the launcher's pane and not
    the room's. This asks about a pane the roster names.
    """
    r = subprocess.run(["tmux", "display-message", "-p", "-t", target, "#{session_name}"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def resolve_session(package, explicit=None):
    """The ONE home of the room's session name (`G-296`) — ASKED OF THE ROOM, never derived.

    Precedence: (i) an explicit `--session` wins; (ii) else the LIVE session of the first roster
    pane that resolves; (iii) else REFUSE, loud and named.

    ⚠⚠ NO PATH DERIVATION, EVER. Its predecessor `default_session` returned the GOAL FOLDER name
    while the room was `core-build`, so four consecutive auto-ensures hit `session_alive` false on
    their first loop turn, printed `room gone — deterministic close` and exited 0 — the room ran
    unobserved behind a log that read healthy (`G-296`). And the derivation was unsound in
    principle, not merely wrong here: nothing in this goal's contract defines a session's NAME, so
    a derived name could only be right by coincidence. A refusal is the correct answer to an
    unanswerable question; a guess is what produced a silent sensor.
    """
    if explicit:
        return explicit
    tried = []
    for seat, rec in roster(package).items():
        pane = (rec.get("pane") or "").strip()
        if not pane:
            continue
        name = tmux_session_name(pane)
        if name:
            return name
        tried.append(f"{seat}={pane}")
    raise SessionUnresolved(
        "cannot resolve the room's tmux session from "
        f"{Path(package) / 'coordination' / 'workers.md'}: "
        + (f"no roster pane resolves to a live session (tried {', '.join(tried)})" if tried
           else "the roster carries no pane at all")
        + " — pass --session explicitly. A session name is NEVER derived from the package"
          " path (`G-296`).")


def session_or_refuse(args):
    """Resolve for a command, or print the refusal and return None (caller exits non-zero)."""
    try:
        return resolve_session(args.package, args.session)
    except SessionUnresolved as e:
        print(f"refusing: {e}", file=sys.stderr, flush=True)
        return None


def session_alive(session):
    return subprocess.run(["tmux", "has-session", "-t", session],
                          capture_output=True).returncode == 0


# ── 7.607 E1 — TERMINATION IS THE FINISH EDGE; THE ROOM GOING AWAY IS A CRASH ──────────────────
#
# `decisions.md#d-extinguishment-design-lock` item 3. The register poll this replaces
# (`run_closed`, reading `<goal>/runs.csv`'s `state` column) is DELETED with the run layer, and so
# is the room-gone exit. Both said "stop watching" for facts that are not completion:
#
#   a closed register row  — a stored status that outlives what it describes (the 7.608 deadlock's
#                            other half; the same row also refused fresh starts forever)
#   an absent room         — which is a CRASH nine times in ten, and this sensor treating it as a
#                            deterministic close is how run-1's room died unwatched (`G-296`)
#
# Now: the FINISH EVENT terminates and nothing else does. An absent room with no finish event is
# recovered — relaunched, bounded — and the sensor keeps running.
#
# ⚠ THE MARKER STRING IS MATCHED FROM `coord.FINISH_MARKER`, DELIBERATELY NOT IMPORTED. Same
# custody argument `run_closed` carried and the same one `ignite/CLAUDE.md` rule 4 makes from the
# other side (ignite must not be reached into at import level, and this file is in `orchestration/`).
# The cost is real and is stated rather than hidden: TWO SPELLINGS OF ONE CONSTANT, kept identical
# by review. A drift between them makes this sensor blind to a finish edge the room already fired.
FINISH_MARKER = "goal-finished: the finish edge fired"
# Bounded by construction — the tuple's LENGTH is the max attempt count, so no second constant can
# disagree with it and no configuration relaunches forever. Seconds, as resolved.
RELAUNCH_BACKOFF_S = (10, 30, 60, 120, 300)


def goal_finished(package):
    """True once this goal's FINISH EVENT is in the append-only coordination log.

    Scans `{package}/coordination/messages.md` for a `type: completion` header whose body OPENS
    with FINISH_MARKER — the first-line convention coord.py's verdict/escalation records already
    use, so no sixth message type is invented (the registry's five are the sole vocabulary, P2).

    ⚠ UNREADABLE -> False, and here that is the SAFE direction rather than the convenient one: a
    sensor that cannot read the log must not conclude the goal is over and walk away from a live
    room. The caller reports the unreadable case; it is never swallowed into "finished".
    """
    p = Path(package).resolve() / "coordination" / "messages.md"
    try:
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    in_completion = False
    for line in text.splitlines():
        m = MSG_HDR_RE.match(line)
        if m:
            in_completion = m.group(4) == "completion"
            continue
        if in_completion and line.strip():
            if line.strip().startswith(FINISH_MARKER):
                return True
            in_completion = False       # the body opened with something else — not a finish event
    return False


def relaunch_room(session, run_fn=None):
    """Restore the lease's PRIMARY evidence — the room. (ok, detail). Idempotent.

    ponytail: restores the ROOM, not the seats inside it — re-seating is the self-heal path's job
    (`ignite/jobs/recover-room.py`), which resolves its target the moment a room exists. Upgrade
    path if that proves insufficient: call that job here instead of tmux.
    """
    run_fn = subprocess.run if run_fn is None else run_fn
    if not session:
        return False, "no room name is known to this sensor — nothing to relaunch"
    r = run_fn(["tmux", "new-session", "-d", "-s", session], capture_output=True, text=True)
    if r.returncode == 0:
        return True, f"room {session} relaunched"
    err = (getattr(r, "stderr", "") or "").strip()
    if "duplicate session" in err:
        return True, f"room {session} already exists (another actor restored it first)"
    return False, f"`tmux new-session -d -s {session}` failed: {err[:200]}"


MSG_HDR_RE = re.compile(
    r"^## (\d+) \| from: (.+?) \| to: (.+?) \| type: (\S+) \| "
    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*$")
MESSAGES_TAIL_N = 10
MESSAGES_TAIL_BYTES = 131072
MSG_TEXT_CAP = 400


def messages_tail(package, limit=MESSAGES_TAIL_N, tail_bytes=MESSAGES_TAIL_BYTES):
    """The last `limit` entries of the run's coordination/messages.md, parsed off the file's
    TAIL (last `tail_bytes` bytes — the log grows into the megabytes and a full read per 2s
    capture would be the sensor's biggest read). Each entry: header fields plus the body's
    first MSG_TEXT_CAP chars flattened to one line. `total` is the highest entry number seen,
    which IS the log's total (the log is append-only with sequential numbers). None when the
    log is absent — a renderer must distinguish 'no log' from 'log empty'. A tail cut that
    lands mid-entry drops only that partial entry's body lines (no header, no entry)."""
    p = Path(package) / "coordination" / "messages.md"
    try:
        size = p.stat().st_size
        with open(p, "rb") as fh:
            if size > tail_bytes:
                fh.seek(size - tail_bytes)
            text = fh.read().decode("utf-8", "replace")
    except OSError:
        return None
    entries, cur = [], None
    for line in text.splitlines():
        m = MSG_HDR_RE.match(line)
        if m:
            cur = {"n": int(m.group(1)), "from": m.group(2), "to": m.group(3),
                   "type": m.group(4), "sent": m.group(5), "text": ""}
            entries.append(cur)
        elif cur is not None and len(cur["text"]) < MSG_TEXT_CAP:
            t = line.strip()
            if t:
                cur["text"] = (cur["text"] + " " + t).strip()[:MSG_TEXT_CAP]
    for e in entries:
        try:  # local wall-clock stamps, same clock coord.py writes them with
            e["sent_epoch"] = time.mktime(time.strptime(e["sent"], "%Y-%m-%d %H:%M"))
        except (ValueError, OverflowError):
            e["sent_epoch"] = None
    return {"total": entries[-1]["n"] if entries else 0, "tail": entries[-limit:]}


# The boot payload every seat reads REGARDLESS of its dispatch prompt or agent type: the run
# CLAUDE.md plus the boot-mandatory coordination docs (protocol.md § seat boot). Absent files
# count 0 — a run without a conduct.md simply has a smaller shared payload.
SHARED_BOOT_FILES = ("CLAUDE.md", "bars.md", "conduct.md", "communication.md")
TOKEN_BYTES = 4  # the standard ~4-bytes-per-token estimate; label stays approximate


def dispatch_tokens(package, seats):
    """Average dispatch payload per LIVE seat, in ~tokens: the shared boot files every seat
    must read plus that seat's own seat.md + memory.md, averaged over the captured seats that
    have a seats/<seat>/seat.md briefing (the door pane and bare shells have none and are
    excluded, not counted as zero). avg_tokens is None when no captured seat has a briefing —
    'not measurable' must stay distinct from 'zero'."""
    root = Path(package)

    def nbytes(p):
        try:
            return p.stat().st_size
        except OSError:
            return 0

    shared = sum(nbytes(root / f) for f in SHARED_BOOT_FILES)
    per_seat = []
    for s in seats:
        name = s.get("seat") or ""
        d = root / "seats" / name
        if name and (d / "seat.md").is_file():
            per_seat.append(nbytes(d / "seat.md") + nbytes(d / "memory.md"))
    out = {"shared_tokens": round(shared / TOKEN_BYTES), "seats": len(per_seat)}
    out["avg_tokens"] = (round((shared + sum(per_seat) / len(per_seat)) / TOKEN_BYTES)
                         if per_seat else None)
    return out


# ---------- the second raw source: the daemon's own job records (task 7.73, design-760) ----------
#
# A headless session occupies a seat but no pane, so every read above is blind to it. design-760
# adds a SECOND RAW SOURCE to this one sensor rather than a second sensor: a READ-ONLY connection
# to the daemon's `heart.db`, whose `jobs_log` is already "one execution = one row = one session
# record" (CMP-2). Nothing new is recorded anywhere; the record the ruling names already exists.
#
# ⚠⚠ TWO BOUNDS, AND THEY ARE THE WHOLE DESIGN:
#
#  1. READ-ONLY, ALWAYS. The connection is opened `mode=ro` on a file: URI, so the kernel refuses
#     a write rather than this module promising not to. CMP-2's E_SECOND_WRITER guards WRITER
#     opens; a reader writes nothing and does not touch the daemon's single-writer guarantee.
#     Reading the STORE (not the daemon) is also why a daemon-DOWN state still reports: a sensor
#     that polled its own subject could not tell "subject down" from "my source down".
#
#  2. THE SEAT COMES FROM THE DISPATCH-TIME RECORD AND NOWHERE ELSE (G-31, design-760 §3). The
#     join key is `session_id`, which `jobs_log` and `sessions.csv` both already carry — no `seat`
#     column on `jobs_log`, no `mode` column on `sessions.csv` (PRIN-11). A row that will not join
#     is an INCIDENT (`headless_unattributed`), never a guess: no pane matching, no workdir
#     heuristic, no post-hoc inference. `workdir` IS read here — for SCOPING ONLY, to decide which
#     run a row belongs to — and never to name a seat, which is the mis-attribution this field
#     exists to make impossible rather than unlikely.

# jobs_log.status values that mean the execution has ENDED (heart schema.sql CHECK). Terminal rows
# are what carry an outcome, and what a daemon-DOWN read must still be able to report.
HEADLESS_TERMINAL = ("done", "blocked", "failed", "stalled", "killed")
# Retention defaults (design-760 §5, disclosed there as a design call): a headless one-shot lives
# seconds, so a live-only view would show it almost never — visibility in principle, invisibility
# in practice. Keep the last K per (job_id, seat) plus everything younger than T. PARAMETERS, not
# inline constants: the caller supplies them and the selftest drives other values. The snapshot is
# a view; the history stays in `jobs_log` itself (PRIN-11).
HEADLESS_KEEP = 5
HEADLESS_WINDOW_S = 3600


def heart_db_path(explicit=None):
    """Where the daemon's per-machine store is, or None when unanswerable.

    Explicit (a probe or a fixture) > this process's own RBTV_IGNITE_DATA_ROOT > the LIVE unit's
    own answer. That last resolution has ONE home — coord.py's `daemon_heart_db`, a protected
    symbol — and is imported by path rather than re-spelled here: two spellings of "which store is
    the daemon's" is how a sensor comes to read a store nobody is writing. Never a hardcoded path:
    reporting rows from the WRONG store is worse than reporting none."""
    if explicit:
        return str(explicit)
    root = os.environ.get("RBTV_IGNITE_DATA_ROOT")
    if root:
        return str(Path(root) / "heart.db")
    try:
        return coord().daemon_heart_db() or None
    except Exception:
        return None


def sessions_seat_index(package):
    """{session-id: [seat, ...]} from the run's `sessions.csv` — the ONE authority for
    session->seat (design-760 §3). A list, not a string, because a session-id claimed by two
    seats is a collision to REPORT (F-R3c/G-31), never a coin to flip."""
    out = {}
    p = Path(package) / "sessions.csv"
    if not p.exists():
        return out
    import csv
    with p.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            sid = (row.get("session-id") or "").strip()
            seat = (row.get("seat") or "").strip()
            if sid and seat not in out.setdefault(sid, []):
                out[sid].append(seat)
    return out


def scoped_execs(db_path, package):
    """Headless `jobs_log` rows belonging to THIS run, read read-only. Raises OSError-shaped
    sqlite3.Error to its caller, which reports the source as unreadable rather than swallowing it.

    Scoping is by `workdir` under the run folder — a row's run membership, NOT its seat."""
    import sqlite3
    root = str(Path(package).resolve())
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    try:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT exec_id, parent_exec_id, job_id, action_type, session_mode, status,"
            "       session_id, pid, exit_code, started_at, ended_at, log_path, workdir,"
            "       completion_msg_id"
            "  FROM jobs_log WHERE session_mode = 'headless' AND workdir IS NOT NULL"
            "  ORDER BY exec_id DESC").fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows
            if r["workdir"] == root or r["workdir"].startswith(root + os.sep)]


def _epoch(stamp):
    """An ISO stamp from the store as epoch seconds, or None. Never guessed."""
    if not stamp:
        return None
    try:
        from datetime import datetime, timezone
        d = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
    except ValueError:
        return None


def headless(package, captured_at, db_path=None, keep=HEADLESS_KEEP, window_s=HEADLESS_WINDOW_S):
    """(rows, unattributed, source) for this run's headless sessions.

    `rows` is design-760 §5's row schema, `seat` REQUIRED — a row cannot be emitted without one.
    `unattributed` is the incident (§4): scoped rows whose session_id joins NO dispatch-time row,
    or joins more than one seat. Both wrong answers are refused: dropping the row (the invisibility
    NEED-3 exists to close) and emitting it seat-less (the owner's rider). `source` states where
    the store was and whether it could be read, so an empty `headless[]` is never ambiguous.

    ⚠ EVERY SCOPED ROW IS ACCOUNTED FOR IN `source`, and that is a bound the leader set on this
    landing (#3980, G-leader-0805-1050): the live launch gate already drops a roster row it cannot
    classify into NOTHING, and this join is the same class of act. So the counts close —
    `scoped == emitted + retention_dropped + unattributed` — and retention, the one place a row
    legitimately leaves the view, says HOW MANY it took. A row may be aged out of a view; it may
    never be silently unclassified."""
    path = heart_db_path(db_path)
    source = {"heart_db": path, "readable": False, "reason": "", "scoped": 0,
              "emitted": 0, "unattributed": 0, "retention_dropped": 0,
              "keep": keep, "window_s": window_s}
    if not path:
        source["reason"] = "no heart.db resolved (no explicit path, no RBTV_IGNITE_DATA_ROOT, no live unit)"
        return [], None, source
    if not Path(path).exists():
        source["reason"] = "heart.db does not exist at the resolved path"
        return [], None, source
    try:
        execs = scoped_execs(path, package)
    except Exception as e:                                    # a broken source is REPORTED
        source["reason"] = f"{type(e).__name__}: {e}"
        return [], None, source
    source["readable"] = True
    source["scoped"] = len(execs)

    seats = sessions_seat_index(package)
    rows, orphans, groups = [], [], {}
    for e in execs:
        cand = seats.get((e["session_id"] or "").strip(), [])
        if len(cand) != 1 or not cand[0]:
            orphans.append({"exec_id": e["exec_id"], "session_id": e["session_id"],
                            "job_id": e["job_id"], "workdir": e["workdir"],
                            "status": e["status"],
                            "candidate_seats": cand,
                            "reason": ("session-id claimed by more than one seat — NOT inferred"
                                       if len(cand) > 1 else
                                       "no dispatch-time sessions.csv row for this session-id")})
            continue
        seat = cand[0]
        started = _epoch(e["started_at"])
        # Retention: young rows always; older ones only while inside their group's K newest.
        key = (e["job_id"], seat)
        n = groups[key] = groups.get(key, 0) + 1
        if started is not None and captured_at - started > window_s and n > keep:
            source["retention_dropped"] += 1        # aged out of the VIEW, and counted saying so
            continue
        rows.append({
            "seat": seat,
            "session_id": e["session_id"],
            "exec_id": e["exec_id"],
            "parent_exec_id": e["parent_exec_id"],
            "job_id": e["job_id"],
            "action_type": e["action_type"],
            "state": e["status"],
            "started_at": e["started_at"],
            "started_age_s": (round(captured_at - started, 1) if started is not None else None),
            "last_activity": _log_mtime(e["log_path"]),
            "outcome": ({"exit_code": e["exit_code"], "status": e["status"],
                         "ended_at": e["ended_at"],
                         "completion_msg_id": e["completion_msg_id"]}
                        if e["status"] in HEADLESS_TERMINAL else None),
            "pid": e["pid"],
            "log_path": e["log_path"] or "",
        })
    source["emitted"] = len(rows)
    source["unattributed"] = len(orphans)
    incident = ({"count": len(orphans), "exec_ids": [o["exec_id"] for o in orphans],
                 "rows": orphans} if orphans else None)
    return rows, incident, source


def _log_mtime(log_path):
    """mtime of the transcript where one exists, else None — NEVER inferred (design-760 §5)."""
    if not log_path:
        return None
    try:
        return round(Path(log_path).stat().st_mtime, 3)
    except OSError:
        return None


# ---------- the run block (CMP-20 Layout) ----------
#
# `ready rows > 0, live executors = 0, nothing queued` is CMP-21's run-stall predicate, and it is
# the whole reason these three numbers are sensed HERE: a consumer computing them for itself would
# be a second toucher of taskforce state and of the queue table — exactly the drift CMP-20's
# single-raw-source-toucher invariant exists to remove.
#
# ⚠ AN UNREADABLE TERM IS `None`, NEVER 0. Two of the three terms can fail to read, and both feed a
# predicate whose stall arm fires on `ready > 0 and live == 0 and queued == 0`. A 0 standing in for
# "unknown" is not a missing fact, it is a FABRICATED one — and it fabricates in the direction that
# raises the alarm. `run.source` says which term could not be read and why, so an absent number is
# never ambiguous (invariant 5: the sensor's own failure is an incident, not silence).


def ready_row_count(package):
    """(count, reason) — taskforce rows whose predecessors are satisfied; `(None, why)` on failure.

    BORROWED from `coord.ready_seat_rows`, the ONE implementation of the readiness predicate: a
    second spelling of its verdict precedence (SKEW > DONE > RUNNING > UNBUILT > UNDECLARED >
    STOPPED > BLOCKED > READY) is how a sensor comes to disagree with the launcher about which
    seats are offerable, and the sensor would be the one that is wrong.

    ⚠ THE CALL WRITES NOTHING, and that is a property of the callee rather than a hope: its whole
    resolver chain (`package_dir` / `base_dir` / `workers_dir`) is invoked `register=False` inside
    it, so no run tag is registered under `~/.config/rbtv/`. The four attributes passed are its
    COMPLETE `args` surface, enumerated from the function body and its transitive resolver calls —
    not assumed. `SystemExit` is caught beside `Exception` because `package_dir` EXITS rather than
    raises on an unresolvable package, and a read must never take the sensor loop down with it."""
    try:
        rows = coord().ready_seat_rows(argparse.Namespace(
            package=str(Path(package).resolve()), base=None, run=None, workers_dir=None))
        return sum(1 for r in rows if r.get("verdict") == "READY"), ""
    except (Exception, SystemExit) as e:
        return None, f"{type(e).__name__}: {e}"


def live_executor_count(seats):
    """Live PANED executor seats — a seat row of this run whose pane holds a harness process.

    Two exclusions, both deliberate. A live pane carrying NO roster seat is not counted: the field
    is "live executor seats" and an unrostered pane is not a seat. A HEADLESS execution has no pane
    at all and is not counted either — the snapshot's own `headless[]` rows carry that half (a row
    whose `state` is outside `HEADLESS_TERMINAL` is an executor occupying work), so a consumer whose
    predicate must not false-positive during a headless window reads them from the SAME snapshot
    rather than from a second observation path."""
    return sum(1 for s in seats if s.get("liveness") == "live" and s.get("seat"))


def _args_carries(node, root):
    """True when any string inside a decoded `args` object IS `root` or sits under it.

    NOT KEYED ON A FIELD NAME. `args` is dry-run-validated at queue time against THAT job_id's own
    `args_schema`, which is per-catalogue-entry — there is no schema-guaranteed `workdir` key to
    read, and hardcoding one would make this sensor a second reader of another component's job
    schema. The ruling's words are "whose args JSON carries this goal's path"; this is those words,
    and it is recursive because a schema is free to nest its paths in a list or a sub-object.

    Containment is the same `== root or startswith(root + sep)` shape `scoped_execs` uses, so a
    sibling goal `/x/goal-2` can never scope into `/x/goal`."""
    if isinstance(node, str):
        return node == root or node.startswith(root + os.sep)
    if isinstance(node, dict):
        return any(_args_carries(v, root) for v in node.values())
    if isinstance(node, list):
        return any(_args_carries(v, root) for v in node)
    return False


def queued_count(package, db_path=None):
    """(count, source) — PENDING queue rows whose args JSON carries this goal's path.

    Owner ruling `d-owner-batch1` (4). The scope key is the GOAL folder, not the run folder — the
    ruling says goal, and live rows spell their path BOTH ways: a seat folder under
    `{goal}/runs/run-n/seats/`, and the goal root itself.

    The scope is read out of `args` because a PENDING row has nothing else to read it from: the
    `workdir` column `scoped_execs` filters `jobs_log` on is acquired when an execution STARTS, and
    a queued row has not started.

    ⚠ A ROW WHOSE `args` WILL NOT DECODE TO AN OBJECT IS EXCLUDED **AND COUNTED** (`unscopable`) —
    never counted in, never dropped silently. Same bound `headless()` carries: a row may leave a
    view, it may never leave it unclassified. The remainder `scanned - count - unscopable` is the
    rows that decoded cleanly and belong to another goal."""
    import sqlite3
    path = heart_db_path(db_path)
    src = {"heart_db": path, "readable": False, "reason": "", "goal": "",
           "scanned": 0, "unscopable": 0}
    if not path:
        src["reason"] = ("no heart.db resolved (no explicit path, no RBTV_IGNITE_DATA_ROOT, "
                         "no live unit)")
        return None, src
    if not Path(path).exists():
        src["reason"] = "heart.db does not exist at the resolved path"
        return None, src
    try:
        root = str(coord().goal_dir(Path(package).resolve()))
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            rows = con.execute("SELECT args FROM queue").fetchall()
        finally:
            con.close()
    except (Exception, SystemExit) as e:                       # a broken source is REPORTED
        src["reason"] = f"{type(e).__name__}: {e}"
        return None, src
    src["readable"] = True
    src["goal"] = root
    src["scanned"] = len(rows)
    count = 0
    for row in rows:
        try:
            decoded = json.loads(row[0] or "")
        except (TypeError, ValueError):
            src["unscopable"] += 1
            continue
        if not isinstance(decoded, (dict, list)):
            src["unscopable"] += 1                             # valid JSON, but not an args object
            continue
        if _args_carries(decoded, root):
            count += 1
    return count, src


# ---------- capture ----------

def capture(package, session=None, sensor_path=None, heart_db=None):
    """One snapshot. captured_at is stamped BEFORE any raw read and never restamped."""
    captured_at = time.time()
    t0 = time.monotonic()

    session = session or resolve_session(package)
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

    # The second raw source. Added to the ONE sensor, never a second writer of state.json.
    head_rows, unattributed, head_source = headless(package, captured_at, heart_db)
    # The run block's two READ terms (the third is an aggregate of `seats`, already in hand).
    ready, ready_reason = ready_row_count(package)
    n_queued, queued_source = queued_count(package, heart_db)

    snap = {
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
        "messages": messages_tail(package),
        "dispatch_tokens": dispatch_tokens(package, seats),
        "headless": head_rows,
        "headless_source": head_source,
        # CMP-20's Layout `run` block. PURELY ADDITIVE: a new top-level key changes no existing
        # one, so every current consumer of this snapshot tolerates it without a change, and a
        # consumer reading an OLDER snapshot must tolerate its absence the same way.
        "run": {
            "ready_rows": ready,
            "live_executors": live_executor_count(seats),
            "queued": n_queued,
            "source": {"ready_rows": ready_reason, "queued": queued_source},
        },
    }
    # NORMALLY ABSENT (design-760 §4): the incident field appears only when there is an incident,
    # so a consumer that renders it as a warning has nothing to render on a healthy run.
    if unattributed:
        snap["headless_unattributed"] = unattributed
    return snap


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
    session = session_or_refuse(args)
    if not session:
        return 4
    print(json.dumps(capture(args.package, session, args.sensor, args.heart_db), indent=1))
    return 0


def cmd_once(args):
    session = session_or_refuse(args)
    if not session:
        return 4
    fh = acquire_writer_lock(args.package)
    if not fh:
        print(f"another writer holds {lock_path(args.package)} (pid {lock_holder(args.package)})",
              file=sys.stderr)
        return 3
    try:
        dest = write_snapshot(capture(args.package, session, args.sensor, args.heart_db), args.package)
        print(dest)
        return 0
    finally:
        fh.close()


# ---------- how `run` ENDS: one home per ending, so the log alone tells them apart ----------
# `G-296`, the severity half. `session_alive` is ONE predicate read at TWO moments, and the two
# readings are OPPOSITE outcomes: false before the loop means nothing was ever observed, false
# inside it means the room ended. Until 2026-07-30 both printed the SAME line at exit 0, so four
# consecutive auto-ensure deaths read as four healthy shutdowns and the room ran unobserved behind
# a log that looked correct. Every ending is spelled ONCE, here, and `cmd_run` emits from these —
# a second copy of a message is how the pairs collapse back together.

EXIT_SESSION_UNRESOLVED = 4
EXIT_SESSION_NEVER_ALIVE = 5
# 7.607 E1: ONE loop ending survives — the finish edge. `RUN_EXIT_ROOM_GONE` is DELETED rather
# than renamed: a room going away is no longer an ending at all, it is a crash to recover, and
# keeping the constant would leave a reader believing the exit still exists somewhere.
RUN_EXIT_FINISHED = ("finish edge fired — team-monitor exiting (the ONE deterministic termination)", 0)
RELAUNCH_EXHAUSTED_LINE = ("team-monitor: RELAUNCH EXHAUSTED — the room did not come back after "
                           f"{len(RELAUNCH_BACKOFF_S)} bounded attempts and NO finish event exists")


def run_exit_never_alive(session, how):
    """The (message, exit-code) pair of a sensor aimed at a session that was NEVER alive.

    It names the session AND how the name was arrived at, because the defect was a name nobody
    could see the provenance of: the log said `session build-core-daemon-mvp` and a reader had no
    way to know that came from the goal-folder path rather than from the room.
    """
    return (f"refusing: session {session!r} was NEVER alive at startup ({how}) — team-monitor "
            "exiting WITHOUT EVER OBSERVING THE ROOM; no snapshot was written. This is NOT a "
            "deterministic close.", EXIT_SESSION_NEVER_ALIVE)


def cmd_run(args):
    """The daemon body: capture on a cadence until the room's session disappears.

    THREE ENDINGS, THREE DISTINGUISHABLE `(message, exit-code)` PAIRS — see the block above:
    unresolvable session (exit 4) · resolved but never alive (exit 5) · the room legitimately
    ended (exit 0). The never-alive test runs BEFORE the lock is taken, so a sensor that never
    observed anything also never occupies the writer slot.
    """
    session = session_or_refuse(args)
    if not session:
        return EXIT_SESSION_UNRESOLVED
    if not session_alive(session):
        how = ("an explicit --session" if args.session else
               "resolved from the roster panes in "
               f"{Path(args.package) / 'coordination' / 'workers.md'}")
        msg, code = run_exit_never_alive(session, how)
        print(msg, file=sys.stderr, flush=True)
        return code
    fh = acquire_writer_lock(args.package)
    if not fh:
        print(f"refusing: another writer holds the lock (pid {lock_holder(args.package)})",
              file=sys.stderr)
        return 3
    print(f"team-monitor up: pid {os.getpid()} session {session} "
          f"interval {args.interval}s -> {state_path(args.package)}", flush=True)
    relaunch_attempts, escalated = 0, False
    try:
        while True:
            # 7.607 E1 — the ONE termination, tested FIRST so a finished goal is never relaunched
            # in the window between its finish event and its room's teardown (`fire_finish_edge`
            # writes the event BEFORE tearing down precisely so this ordering is observable).
            if goal_finished(args.package):
                msg, code = RUN_EXIT_FINISHED
                print(msg, flush=True)
                return code
            if not session_alive(session):
                # NOT an ending any more. No finish event + no room = CRASH, and a sensor that
                # exits here is how `G-296`'s room ran unobserved behind a log that read healthy.
                if relaunch_attempts < len(RELAUNCH_BACKOFF_S):
                    backoff = RELAUNCH_BACKOFF_S[relaunch_attempts]
                    relaunch_attempts += 1
                    ok, detail = relaunch_room(session)
                    print(f"room GONE with no finish event — CRASH, not completion. relaunch "
                          f"attempt {relaunch_attempts}/{len(RELAUNCH_BACKOFF_S)}: {detail}",
                          file=sys.stderr, flush=True)
                    if not ok:
                        time.sleep(backoff)   # the bound that keeps a failing relaunch from storming
                        continue
                elif not escalated:
                    escalated = True
                    print(f"{RELAUNCH_EXHAUSTED_LINE} (room {session}). This sensor does NOT exit: "
                          f"a goal with no finish event is unfinished, and a silent exit here is "
                          f"how a room dies unwatched. Restore the room, or fire the finish edge "
                          f"(`coordinate finish-goal`) if the goal is genuinely over.",
                          file=sys.stderr, flush=True)
            else:
                relaunch_attempts, escalated = 0, False   # the room is back: the budget resets
            try:
                write_snapshot(capture(args.package, session, args.sensor, args.heart_db), args.package)
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
    if args.heart_db:
        argv += ["--heart-db", args.heart_db]
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


def _selftest_run_block(check):
    """The `run` block's checks (CMP-20 Layout + owner ruling `d-owner-batch1` (4)).

    A FUNCTION rather than an inline block so the exact code `selftest` runs is also the code a
    driver can exercise directly — on a box where the surrounding selftest's live-tmux fixture
    cannot be built, a second hand-written copy of these checks would be evidence about the copy."""
    import sqlite3
    import tempfile

    def queue_fixture(td, args_rows):
        """A heart.db carrying ONLY a `queue` table — the columns the DDL declares, so a reader
        that reached for `workdir` (the column a PENDING row does not have) fails here."""
        db = str(Path(td) / "heart.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE queue (queue_id INTEGER PRIMARY KEY AUTOINCREMENT,"
                    " job_id TEXT NOT NULL, args TEXT NOT NULL DEFAULT '{}',"
                    " session_mode TEXT, trigger_kind TEXT, run_at TEXT, repeat_rule TEXT,"
                    " interval_seconds INTEGER, max_fires INTEGER, enqueued_by TEXT,"
                    " enqueued_at TEXT)")
        con.executemany("INSERT INTO queue (job_id, args, session_mode, trigger_kind, run_at,"
                        " enqueued_by, enqueued_at) VALUES ('j', ?, 'headless', 'scheduled',"
                        " '2026-01-01T00:00:00Z', 'owner', '2026-01-01T00:00:00Z')",
                        [(a,) for a in args_rows])
        con.commit()
        con.close()
        return db

    # ---- ready_rows: the READY count, not the row count ----
    # The fixture makes the two DIFFER (2 rows, 1 ready): a count that forgot the verdict filter
    # reads 2 here and cannot pass.
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "goals" / "zz-goal" / "runs" / "run-1"
        (pkg / "coordination").mkdir(parents=True)
        for s in ("alpha", "beta"):
            (pkg / "seats" / s).mkdir(parents=True)
            (pkg / "seats" / s / "seat.md").write_text(
                f"---\nseat: {s}\nharness: claude\n---\nbrief\n", encoding="utf-8")
        (pkg / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,alpha,,claude,opus,high,50,m0\n"
            "tf-2,beta,alpha,claude,opus,high,50,m0\n", encoding="utf-8")
        (pkg / "coordination" / "workers.md").write_text(
            "| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
            "|---|---|---|---|---|---|---|\n", encoding="utf-8")
        n, reason = ready_row_count(str(pkg))
        check(f"B1: ready_rows counts READY verdicts, not taskforce rows (2 rows, 1 ready; "
              f"got {n!r}, reason={reason!r})", n == 1 and reason == "")

    # A package with no taskforce.csv at all answers 0 rather than raising — the sensor runs on
    # rooms that have no DAG, and a raise there would cost the whole snapshot.
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "goals" / "g" / "runs" / "run-1"
        (pkg / "coordination").mkdir(parents=True)
        n, reason = ready_row_count(str(pkg))
        check(f"B1: a package with no taskforce.csv reads 0, never an exception (got {n!r})",
              n == 0 and reason == "")

    # ---- live_executors: live AND seated, paned only ----
    rows = [{"seat": "a", "liveness": "live"},        # counted
            {"seat": "b", "liveness": "no-harness"},  # a seat whose harness died
            {"seat": "c", "liveness": "shell"},       # a seat sitting at a shell
            {"seat": "", "liveness": "live"}]         # a live pane that is NOT a seat
    check("B1: live_executors counts live SEATED panes only (1 of 4)",
          live_executor_count(rows) == 1)

    # ---- queued: the owner ruling's scoping, and the counts that close ----
    with tempfile.TemporaryDirectory() as td:
        goals = Path(td) / "goals"
        pkg = goals / "zz-goal" / "runs" / "run-1"
        pkg.mkdir(parents=True)
        goal = str((goals / "zz-goal").resolve())
        other = str((goals / "zz-goal-2").resolve())   # the sibling-prefix control

        empty_db = queue_fixture(td, [])
        n, src = queued_count(str(pkg), empty_db)
        check(f"B1: baseline — an empty queue is 0 AND readable, never None (got {n!r})",
              n == 0 and src["readable"] is True and src["scanned"] == 0)

        sub = Path(td) / "full"
        sub.mkdir()
        db = queue_fixture(sub, [
            json.dumps({"tool": "selfheal-watch"}),                                    # no path
            json.dumps({"profile": "p", "workdir": f"{goal}/runs/run-1/seats/alpha"}),  # MATCH
            json.dumps({"profile": "p", "workdir": f"{other}/runs/run-1/seats/alpha"}),  # sibling
            json.dumps({"prompt": "c", "workdir": goal}),          # MATCH — the goal root itself
            json.dumps({"profile": "p", "workdir": f"{goal}/runs/run-2/seats/x"}),  # MATCH — run 2
            "{not json at all",                                                   # unscopable
            json.dumps("a bare string"),                          # valid JSON, not an args object
        ])
        n, src = queued_count(str(pkg), db)
        check(f"B1: queued is GOAL-scoped per d-owner-batch1 (4) — the goal root and a SECOND "
              f"run of the same goal both count, so 3 of 7 (got {n!r})", n == 3)
        check(f"B1: a sibling goal sharing the path PREFIX (`zz-goal-2` vs `zz-goal`) is NOT "
              f"scoped in (got {n!r}, would be 4)", n == 3)
        check(f"B1: a row whose args will not decode is EXCLUDED and COUNTED, never silent "
              f"(unscopable={src['unscopable']})", src["unscopable"] == 2)
        check(f"B1: the counts close — scanned {src['scanned']} == matched {n} + unscopable "
              f"{src['unscopable']} + 2 other-goal rows",
              src["scanned"] == n + src["unscopable"] + 2)
        check(f"B1: the source names the goal it scoped on ({src['goal']!r})", src["goal"] == goal)

        # ---- the READ-ONLY bound, checked on THE MODULE's own open (the 7.73 pattern) ----
        # Watching the kernel refuse a write on a connection this check opened proves sqlite works
        # and stays green with `queued_count` switched read-write. The subject is the URI the
        # module itself asked for, captured as it asked.
        opened = []
        real_connect = sqlite3.connect

        def spy(*a, **kw):
            opened.append(a[0] if a else kw.get("database"))
            return real_connect(*a, **kw)

        sqlite3.connect = spy
        try:
            queued_count(str(pkg), db)
        finally:
            sqlite3.connect = real_connect
        uri = str(opened[0] if opened else "")
        check(f"B1: the queue is opened READ-ONLY — the module's own connect asked for mode=ro "
              f"({uri!r})", "mode=ro" in uri)
        ro = real_connect(uri, uri=True)
        try:
            ro.execute("DELETE FROM queue")
            ro.commit()
            refused = False
        except sqlite3.OperationalError:
            refused = True
        finally:
            ro.close()
        rw = real_connect(db)                                    # the control, same statement
        rw.execute("DELETE FROM queue WHERE queue_id = 999")
        rw.commit()
        rw.close()
        check("B1: that connection cannot write — the kernel refuses while the SAME statement "
              "succeeds read-write on the same file (so the refusal is the mode's)", refused)

        # ⚠ THE FIELD THAT COULD NOT BE READ IS None, NEVER 0 — a 0 here would read to CMP-21 as
        # "nothing queued", which is one third of its stall predicate, satisfied by a fabrication.
        n, src = queued_count(str(pkg), str(Path(td) / "nope.db"))
        check(f"B1: an absent heart.db reports WHY and reads None, never 0 (got {n!r}, "
              f"reason={src['reason']!r})",
              n is None and src["readable"] is False and "does not exist" in src["reason"])


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

    # ---- G-296: the room's session name has ONE home, and the ROOM is its source ----
    # ⚠ THE FIXTURE DELIBERATELY DISAGREES WITH ITS OWN PATH: the package sits under a goal folder
    # named `zz-goal-folder` while the live throwaway session is named otherwise — exactly the
    # live room's condition (`build-core-daemon-mvp` on disk, `core-build` in tmux) and exactly the
    # condition no earlier fixture had. The check this REPLACES asserted only that the derivation
    # was self-consistent (`default_session(".../my-goal/runs/run-1") == "my-goal"`), so it stayed
    # green through the entire defect. A fixture that agrees with its path cannot fail; this one
    # can only pass if resolution actually asks the room.
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "goals" / "zz-goal-folder" / "runs" / "run-1"
        (pkg / "coordination").mkdir(parents=True)
        header = ("| agent | active | tmux pane | working on | checked in | checked out |\n"
                  "|---|---|---|---|---|---|\n")
        sess = f"zz-tm-selftest-{os.getpid()}"
        made = subprocess.run(["tmux", "new-session", "-d", "-s", sess],
                              capture_output=True, text=True)
        # a fixture that failed to build is reported, never skipped — a silent skip here would
        # restore the very blind spot this block exists to close
        check(f"G-296 fixture: throwaway room `{sess}` built to resolve against "
              f"(rc={made.returncode}, stderr={made.stderr.strip()!r})", made.returncode == 0)
        try:
            pane = subprocess.run(["tmux", "list-panes", "-t", sess, "-F", "#{pane_id}"],
                                  capture_output=True, text=True).stdout.split()[0]
            (pkg / "coordination" / "workers.md").write_text(
                f"{header}| a-seat | yes | {pane} | w | t1 |  |\n")
            got = resolve_session(str(pkg))
            check(f"G-296: the LIVE room name wins over the goal-folder name "
                  f"(`{sess}` != `zz-goal-folder`; resolved `{got}`)", got == sess)
            check("G-296: an explicit --session outranks the live resolution",
                  resolve_session(str(pkg), "explicit-wins") == "explicit-wins")
        finally:
            subprocess.run(["tmux", "kill-session", "-t", sess], capture_output=True)
    # the refuse branch: no pane resolves, so resolution RAISES — it never falls back to the
    # goal-folder name, which is the whole point of the removal
    for label, rows in (
        ("a roster pane that resolves to nothing", "| a-seat | yes | %999999 | w | t1 |  |\n"),
        ("a roster carrying no pane at all", "| a-seat | yes |  | w | t1 |  |\n"),
    ):
        with tempfile.TemporaryDirectory() as td:
            pkg = Path(td) / "goals" / "zz-goal-folder" / "runs" / "run-1"
            (pkg / "coordination").mkdir(parents=True)
            (pkg / "coordination" / "workers.md").write_text(header + rows)
            try:
                out = repr(resolve_session(str(pkg)))
            except SessionUnresolved:
                out = "SessionUnresolved"
            check(f"G-296: {label} REFUSES loudly and never defaults to the path "
                  f"(got {out})", out == "SessionUnresolved")

    # ---- G-296, the SEVERITY half (task 7.110): three endings a log reader can tell apart ----
    # ⚠ THIS BLOCK DRIVES `cmd_run` ITSELF and reads what it actually PRINTED. It does not compare
    # the constants to each other: a check that hand-types both sides of a message can pass while
    # the daemon prints something else entirely, which is the shape of the green that let this
    # defect through in the first place. Each ending below is produced by the real function, on a
    # throwaway package, and the pair recorded is (what a log reader sees, what the process
    # returned) — the two halves criterion 5 requires to differ.
    import contextlib
    import io

    def drive_run(pkg, session=None):
        """Run `cmd_run` to one of its endings; return (printed-line, exit-code) as observed."""
        a = argparse.Namespace(package=str(pkg), session=session, sensor=None, interval=0.1)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cmd_run(a)
        printed = (out.getvalue() + err.getvalue()).strip().splitlines()
        # the startup endings print one line; the loop endings print the `up:` line first
        return (printed[-1] if printed else "", rc)

    endings = {}
    hdr296 = ("| agent | active | tmux pane | working on | checked in | checked out |\n"
              "|---|---|---|---|---|---|\n")
    with tempfile.TemporaryDirectory() as td:
        # (a) UNRESOLVABLE — a roster whose only pane resolves to nothing
        pkg = Path(td) / "goals" / "zz-goal" / "runs" / "run-1"
        (pkg / "coordination").mkdir(parents=True)
        (pkg / "coordination" / "workers.md").write_text(
            hdr296 + "| a-seat | yes | %999999 | w | t1 |  |\n")
        endings["unresolvable"] = drive_run(pkg)
        # (b) NEVER ALIVE — the name resolves (explicitly) but no such session has ever existed
        endings["never-alive"] = drive_run(pkg, session=f"zz-tm-no-such-session-{os.getpid()}")
        # (c) LEGITIMATE CLOSE — the session IS alive and the run's own row reads closed, so the
        # loop's deterministic close is the ending reached. A live room is required for this one:
        # `session_alive` must be TRUE here or the check would be measuring ending (b) again.
        sess = f"zz-tm-exit-selftest-{os.getpid()}"
        made = subprocess.run(["tmux", "new-session", "-d", "-s", sess],
                              capture_output=True, text=True)
        check(f"7.110 fixture: throwaway room `{sess}` built for the legitimate-close ending "
              f"(rc={made.returncode}, stderr={made.stderr.strip()!r})", made.returncode == 0)
        try:
            # 7.607 E1: the legitimate close is now the FINISH EVENT in the append-only log, not a
            # `state=closed` register row. The fixture writes the event exactly as coord.py's
            # `fire_finish_edge` does — a real header + a body opening with the marker — so this
            # row scores the real reader against the real shape, never a hand-shaped stub.
            (pkg / "coordination").mkdir(parents=True, exist_ok=True)
            (pkg / "coordination" / "messages.md").write_text(
                "\n## 1 | from: leader | to: all | type: completion | 2026-08-09 12:00\n\n"
                f"{FINISH_MARKER}\n\nthe goal's execution is over by the deterministic finish edge\n")
            endings["legitimate-close"] = drive_run(pkg, session=sess)
        finally:
            subprocess.run(["tmux", "kill-session", "-t", sess], capture_output=True)

    for label, (line, rc) in sorted(endings.items()):
        check(f"7.110: the `{label}` ending is reported at all (got rc={rc}, line={line!r})",
              bool(line))
    check("7.110: the never-alive ending exits NON-ZERO — a silent exit 0 is the whole defect "
          f"(got {endings['never-alive'][1]})", endings["never-alive"][1] != 0)
    check("7.110: the never-alive line names the session AND how it was resolved",
          "no-such-session" in endings["never-alive"][0]
          and "explicit --session" in endings["never-alive"][0])
    # criterion 5: all three pairs differ, in BOTH halves, pairwise
    pairs = sorted(endings.items())
    for i, (la, pa) in enumerate(pairs):
        for lb, pb in pairs[i + 1:]:
            check(f"7.110 criterion 5: `{la}` and `{lb}` differ in the MESSAGE "
                  f"({pa[0][:48]!r} vs {pb[0][:48]!r})", pa[0] != pb[0])
            check(f"7.110 criterion 5: `{la}` and `{lb}` differ in the EXIT CODE "
                  f"({pa[1]} vs {pb[1]})", pa[1] != pb[1])
    # criteria 3+4: the legitimate close is UNCHANGED. The expected strings are spelled out as
    # LITERALS rather than read from the constants they guard — a guard that reads the value under
    # test moves with any edit to it and would pass a rewording silently.
    # 7.607 E1 re-founds criteria 3+4. The room-gone EXIT is gone — a room going away is a crash to
    # recover, not an ending — so the check that it is unchanged is replaced by the check that it
    # NO LONGER EXISTS as a module-level name. That is the strongest form available: a renamed-but-
    # surviving exit would pass any check written about the new one.
    check("⚠ 7.607 E1: the room-gone EXIT is DELETED, not renamed — `RUN_EXIT_ROOM_GONE` is not a "
          "name this module carries any more, so no path can still exit on an absent room",
          "RUN_EXIT_ROOM_GONE" not in globals() and "RUN_EXIT_RUN_CLOSED" not in globals())
    # The expected string is spelled out as a LITERAL rather than read from the constant it guards —
    # a guard that reads the value under test moves with any edit to it and passes a rewording.
    check("7.607 E1: the finish-edge line and its exit 0 are what a log reader will see, byte for byte",
          RUN_EXIT_FINISHED
          == ("finish edge fired — team-monitor exiting (the ONE deterministic termination)", 0))
    check("⚠ 7.607 E1 THE CRITERION: the legitimate close observed from `cmd_run` IS the finish-edge "
          "pair — driven by a real finish EVENT in a real messages.md, through the real reader",
          endings["legitimate-close"] == RUN_EXIT_FINISHED)

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

    # ---- messages tail + dispatch tokens (owner-requested teamview feed, 2026-07-28) ----
    with tempfile.TemporaryDirectory() as td:
        coord = Path(td) / "coordination"
        coord.mkdir()
        check("messages_tail: absent log reads None, never an empty tail",
              messages_tail(td) is None)
        body = ["# messages — append-only coordination log\n"]
        for i in range(1, 13):
            body.append(f"## {i} | from: seat-a | to: seat-b | type: note "
                        f"| 2026-07-28 10:{i:02d}\n\nline one of msg {i}.\n"
                        f"line two of msg {i}.\n")
        (coord / "messages.md").write_text("\n".join(body), encoding="utf-8")
        mt = messages_tail(td)
        check("messages_tail: last 10 of 12 entries, in log order, total = highest number",
              mt["total"] == 12 and len(mt["tail"]) == 10
              and [e["n"] for e in mt["tail"]] == list(range(3, 13)))
        e = mt["tail"][-1]
        check("messages_tail: entry carries from/to/type/sent + flattened body text",
              e["from"] == "seat-a" and e["to"] == "seat-b" and e["type"] == "note"
              and e["sent"] == "2026-07-28 10:12"
              and e["text"] == "line one of msg 12. line two of msg 12."
              and isinstance(e["sent_epoch"], float))
        long = ("## 13 | from: a | to: b | type: note | 2026-07-28 11:00\n\n"
                + "x" * 1000 + "\n")
        with (coord / "messages.md").open("a", encoding="utf-8") as fh:
            fh.write("\n" + long)
        check("messages_tail: body text is capped, never the whole essay",
              len(messages_tail(td)["tail"][-1]["text"]) <= MSG_TEXT_CAP + 1)
        # a tail cut landing MID-ENTRY drops the partial entry, never mis-parses it
        cut = messages_tail(td, tail_bytes=600)
        check("messages_tail: a mid-entry tail cut still parses the complete entries after it",
              cut is not None and all(e["n"] for e in cut["tail"]))

        (Path(td) / "CLAUDE.md").write_text("c" * 4000, encoding="utf-8")
        (Path(td) / "bars.md").write_text("b" * 2000, encoding="utf-8")
        sd = Path(td) / "seats"
        (sd / "s1").mkdir(parents=True)
        (sd / "s1" / "seat.md").write_text("s" * 1000, encoding="utf-8")
        (sd / "s1" / "memory.md").write_text("m" * 3000, encoding="utf-8")
        (sd / "s2").mkdir(parents=True)
        (sd / "s2" / "seat.md").write_text("s" * 2000, encoding="utf-8")
        seats_in = [{"seat": "s1"}, {"seat": "s2"}, {"seat": ""}, {"seat": "no-briefing"}]
        dt = dispatch_tokens(td, seats_in)
        # shared 6000B + mean(4000, 2000)=3000B -> 9000B / 4 = 2250 tok, over exactly 2 seats
        check("dispatch_tokens: avg = (shared + mean per-seat payload)/4 over briefed seats "
              "only — the door pane and briefing-less seats are excluded, not zeroed",
              dt == {"shared_tokens": 1500, "seats": 2, "avg_tokens": 2250})
        check("dispatch_tokens: no briefed seat -> avg is None, never a fake zero",
              dispatch_tokens(td, [{"seat": ""}])["avg_tokens"] is None)

    # ---- the non-pane source: jobs_log x sessions.csv -> headless[] (task 7.73, design-760) ----
    # ⚠ THE FIXTURE IS BUILT SO EVERY CHECK CAN FAIL. The seat asserted below appears ONLY in
    # sessions.csv — never in the workdir, never in the job id — so a join that quietly inferred
    # the seat from the path (the G-31 mis-attribution this design exists to make impossible)
    # cannot pass, and neither can one that dropped the unjoinable row.
    import sqlite3
    import tempfile

    def heart_fixture(td, rows):
        db = str(Path(td) / "heart.db")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE jobs_log (exec_id INTEGER PRIMARY KEY, parent_exec_id INTEGER,"
                    " job_id TEXT, action_type TEXT, session_mode TEXT, status TEXT,"
                    " session_id TEXT, pid INTEGER, exit_code INTEGER, started_at TEXT,"
                    " ended_at TEXT, log_path TEXT, workdir TEXT, completion_msg_id INTEGER)")
        con.executemany("INSERT INTO jobs_log (exec_id, job_id, action_type, session_mode, status,"
                        " session_id, pid, exit_code, started_at, ended_at, workdir)"
                        " VALUES (:exec_id,:job_id,'launch-agent','headless',:status,:session_id,"
                        ":pid,:exit_code,:started_at,:ended_at,:workdir)", rows)
        con.commit()
        con.close()
        return db

    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "pkg"
        (pkg / "seats" / "worker-a").mkdir(parents=True)
        iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 30))
        old = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 86400))
        wd = str(pkg / "seats" / "worker-a")
        (pkg / "sessions.csv").write_text(
            "seat,session-id,harness,workdir,pid,pid-starttime,tty,started,ended\n"
            f"worker-a,sid-live,claude,{wd},111,1,,{iso},\n"
            f"worker-a,sid-done,claude,{wd},112,1,,{old},\n"
            "twin,sid-clash,claude,x,113,1,,,\n"
            "other,sid-clash,claude,x,114,1,,,\n", encoding="utf-8")
        base = {"job_id": "hv", "pid": None, "exit_code": None, "ended_at": None, "workdir": wd}
        db = heart_fixture(td, [
            {**base, "exec_id": 1, "status": "running", "session_id": "sid-live",
             "started_at": iso, "pid": 111},
            {**base, "exec_id": 2, "status": "done", "session_id": "sid-done",
             "started_at": old, "ended_at": old, "exit_code": 0},
            {**base, "exec_id": 3, "status": "failed", "session_id": "sid-orphan",
             "started_at": iso},
            {**base, "exec_id": 4, "status": "done", "session_id": "sid-clash",
             "started_at": iso},
            # scoping control: a real headless row of ANOTHER run must not enter this snapshot
            {**base, "exec_id": 5, "status": "running", "session_id": "sid-live",
             "started_at": iso, "workdir": str(Path(td) / "elsewhere" / "seats" / "worker-a")},
        ])
        now_ = time.time()
        rows, inc, src = headless(str(pkg), now_, db)
        by_exec = {r["exec_id"]: r for r in rows}
        check("7.73: the joined row carries the seat from the DISPATCH-TIME sessions.csv row",
              by_exec.get(1, {}).get("seat") == "worker-a")
        check("7.73: every emitted row HAS a seat — the rider holds by construction, not by filter",
              all(r["seat"] for r in rows))
        check("7.73: a terminal row carries exit_code/ended_at/status as its outcome",
              by_exec.get(2, {}).get("outcome", {}).get("exit_code") == 0
              and by_exec[2]["outcome"]["ended_at"] == old
              and by_exec[2]["outcome"]["status"] == "done")
        check("7.73: a live row carries NO outcome (an outcome is a terminal fact)",
              by_exec.get(1, {}).get("outcome") is None)
        check("7.73: a row of ANOTHER run's tree is not scoped into this snapshot",
              5 not in by_exec and src["scoped"] == 4)
        # the two incident shapes — neither dropped, neither guessed at
        orphans = {o["exec_id"]: o for o in (inc or {}).get("rows", [])}
        check("7.73: an unjoinable row surfaces in headless_unattributed, NOT as a session row",
              3 in orphans and 3 not in by_exec)
        check("7.73: a session-id claimed by TWO seats is REPORTED with both, never inferred",
              4 in orphans and sorted(orphans.get(4, {}).get("candidate_seats", [])) == ["other", "twin"]
              and 4 not in by_exec)
        check("7.73: the incident carries count + exec_ids (design-760 §4)",
              inc["count"] == 2 and sorted(inc["exec_ids"]) == [3, 4])
        # ⚠ THE LEADER'S #3980 BAR: no row may vanish silently. The counts must CLOSE.
        check("7.73: every scoped row is accounted for — scoped == emitted + unattributed + "
              f"retention_dropped (got {src['scoped']} == {src['emitted']} + {src['unattributed']}"
              f" + {src['retention_dropped']})",
              src["scoped"] == src["emitted"] + src["unattributed"] + src["retention_dropped"])
        # retention: an old row outside the window AND outside its group's K newest leaves the
        # VIEW — and the count says so. Driven at keep=0 so the same fixture answers both ways.
        rows0, _, src0 = headless(str(pkg), now_, db, keep=0, window_s=60)
        check("7.73: an aged row leaves the view under retention and is COUNTED, never silent",
              src0["retention_dropped"] == 1 and 2 not in {r["exec_id"] for r in rows0}
              and src0["scoped"] == src0["emitted"] + src0["unattributed"] + src0["retention_dropped"])
        check("7.73: the same row is KEPT when the window covers it — retention is the only "
              "reason it left (the discriminating half)", 2 in by_exec)
        # ---- the READ-ONLY bound, checked on THE MODULE and not on sqlite ----
        # ⚠ WHY THIS IS NOT THE OBVIOUS CHECK. Opening a `mode=ro` connection here and watching
        # the kernel refuse a write proves that sqlite works; it stays GREEN with `scoped_execs`
        # switched to read-write, because a reader that never writes is observably identical
        # either way. There is no runtime symptom to catch — so the subject is the module's OWN
        # open, captured as it happens, and the assertion is on the mode it asked for. The second
        # half then shows what that mode BUYS, through the very URI the module built.
        opened = []
        real_connect = sqlite3.connect

        def spy(*a, **kw):
            opened.append(a[0] if a else kw.get("database"))
            return real_connect(*a, **kw)

        sqlite3.connect = spy
        try:
            scoped_execs(db, str(pkg))
        finally:
            sqlite3.connect = real_connect
        uri = opened[0] if opened else ""
        check(f"7.73: the store is opened READ-ONLY — the module's own connect asked for "
              f"mode=ro ({uri!r})", "mode=ro" in str(uri))
        ro = real_connect(str(uri), uri=True)
        try:
            ro.execute("UPDATE jobs_log SET status='tampered' WHERE exec_id=1")
            ro.commit()
            refused = False
        except sqlite3.OperationalError:
            refused = True
        finally:
            ro.close()
        rw = real_connect(db)
        rw.execute("UPDATE jobs_log SET status='running' WHERE exec_id=1")   # the control
        rw.commit()
        rw.close()
        check("7.73: that connection cannot write — the kernel refuses, while the SAME statement "
              "succeeds read-write on the same file (so the refusal is the mode's)", refused)
        # an absent store is REPORTED, never an ambiguous empty list
        _, _, missing = headless(str(pkg), now_, str(Path(td) / "nope.db"))
        check("7.73: an absent heart.db reports WHY rather than an ambiguous empty headless[]",
              missing["readable"] is False and "does not exist" in missing["reason"])

    _selftest_run_block(check)

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
            p.add_argument("--session", help="tmux session; omitted, it is resolved LIVE from a "
                                             "roster pane and NEVER derived from the path")
            p.add_argument("--sensor", help="override the inherited ctx-monitor path")
            # A PATH, never a policy value: which store to read. Omitted, it is resolved from
            # RBTV_IGNITE_DATA_ROOT or from the live daemon unit's own environment.
            p.add_argument("--heart-db", help="override the resolved heart.db (read-only)")
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
