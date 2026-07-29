#!/usr/bin/env python3
"""watch — deterministic liveness + context monitor for team-kit runs.

The watcher seat's tool (deterministic-first: the SCRIPT measures, the watcher agent only runs
it and relays judgment). One pass checks every ACTIVE roster seat and reports:

  liveness   registered pane still exists (a DEAD pane means wakes cannot reach the seat)
  ghostrow   a roster-ACTIVE row whose pane runs NO harness process (PROP-11, leader ruling
             2026-07-27): the row claims a seat that is not there, so its work is stopped and
             every wake sent to it is typed into a bare shell. It is the gap common to five
             defects in one night — a closer that checked itself in from a shell, and a watcher
             agent that died twice with its row still reading ACTIVE. Checked HERE and in no
             agent, because this detached loop outlives every agent, INCLUDING the watcher's own
             row (the one row nothing else can report on). Notify only, never act.
  activity   minutes since the pane's visible content last changed (content-hash based, so it
             works for panes sharing a window, where tmux window_activity cannot distinguish)
  context    for claude-harness seats: % of the context window used, computed from the seat's
             session transcript JSONL exactly like the rbtv context-monitor hook (last
             non-sidechain assistant turn: input + cache_read + cache_creation tokens over the
             window; window from $RBTV_CONTEXT_WINDOW, default 1,000,000). codex/opencode seats
             have no externally readable transcript — activity watching only.
  approval   the seat's pane TITLE says its harness is parked on an interactive approval prompt
             (P38 — a codex seat at "Action Required" stalls silently: its pane content is frozen,
             so it reads as a healthy idle seat until the inactivity threshold finally fires
             ~30 min later). Flagged immediately, with the `approve <agent>` command to run.
  system     RAM/load pressure on the BOX (PROP-9, tv-ux-review — a stuck-process pile-up
             OOM-killed the watcher itself, the one seat meant to notice it): available memory
             below the run's DECLARED floor (budget.json floors.pressure_warn_mb; --mem-floor-mb
             overrides it deliberately) or 1-min load at/over cores x --load-per-core
             flags SYSTEM PRESSURE. Read from /proc/meminfo + /proc/loadavg; on a box without
             /proc the check skips honestly (never a fake reading).
  leftover   a briefing-declared wave window whose panes are ALL agent-dead — no active roster
             seat left in it (PROP-10, tv-ux-review): either its wave closed leaving bash-only
             shells, or its seats died at model-init before ever checking in. Flagged once with
             the sanctioned teardown (`tmux kill-window` — bash ignores SIGTERM, kill-pane is
             classifier-blocked).

Every pass stamps `<package>/coordination/watch-heartbeat.json` (P32 — nothing watched the
watcher: this loop runs detached, so a dead loop is indistinguishable from a quiet run). `coordinate
workers` reads the stamp and reports the watcher STALE past three missed passes.

Thresholds (watcher defaults, owner-ruled 2026-07-24): --inactive-min 30, --context-pct 50.
With --notify each crossing sends ONE coordination `note` (via coord.py, so it is logged and wakes
the pane) telling the recipient exactly what to run — e.g. `close <agent> --renew` at the context
threshold. A crossing re-arms only when the condition clears (activity resumes / the seat's pane
changes, i.e. it was renewed).

⚠ A FLAG IS NEVER SENT TO THE SEAT IT IS ABOUT. `--notify-to` (default `leader`) takes the flags;
a flag whose SUBJECT is that seat is diverted to `--notify-fallback` (default `leader`), because a
seat cannot be asked to adjudicate a warning about itself. This is not a special case for one role:
it was found as one — a context warning about the LEADER was delivered to the leader, which holds
its own close/renew/approve with no seat above it and an AFK owner — and the general rule is what
closes it, since pointing the flags at any single seat just moves the hole to that seat.

  python3 watch.py --package <abs-run-package> [--notify] [--loop 10]

State (7.37 criterion 3 / R10): the agent-keyed re-arm state lives at the GOAL folder —
<goal>/watch-state.json, SECTIONED BY RUN (`{"runs": {"run-1": {...}, "run-2": {...}}}`) — so it
survives a run boundary while a run reads only its OWN section. Every key it holds (`pane`, `hash`,
`stable_since`, `notified_*`) describes a seat in the run-scoped tmux room R15 tears down at run
close, so NO field is correct to inherit across runs and none is. A package with no goal folder
above it (a bare `--base`, a test tree) keeps the per-run `<package>/coordination/watch-state.json`
unchanged. The other two state files stay PER-RUN on purpose: `watch-system.json` is run-scoped
(windows) and box-scoped (pressure), never goal-scoped; `watch-heartbeat.json` is this loop's own
liveness stamp plus the daemon reading (see `save_heartbeat`). Transcript matching: the seat's
launch cwd maps to ~/.claude/projects/<munged-cwd>/*.jsonl; the boot prompt names the agent
("You are agent '<name>'" / "You are **<name>**"), newest matching file wins. Fallback (a
hand-started seat's boot prompt never carries that phrasing): the seat's REGISTERED pane's live
`#{pane_current_path}` is munged instead, and the newest transcript there whose first user text
references the seat's own `workers/<agent>/` path fragment wins — generic, no run/path/agent
special-casing; a seat with no match on either path stays unmeasured, never a crash.

  python3 watch.py --selftest    # temp dir, no tmux needed — exit 0 must gate any edit here
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import coord  # noqa: E402  — roster/messaging/discovery live there; state stays in the package
import budget as budget_mod  # noqa: E402  — declared capacity vs the live census; reads state.json only


def _loaded_code_fingerprint():
    """sha256 per kit source file, over THE BYTES THIS PROCESS LOADED (run issue G-158).

    WHY THIS EXISTS. This loop is `while True: pass; sleep` in ONE process (see cmd_watch), and
    python binds module source at import: there is no reload path here (`execv`/`importlib.reload`
    appear zero times, measured). So an edit to watch.py or coord.py NEVER reaches a running loop
    — and the loop keeps heartbeating, keeps printing its pass line, and keeps reporting healthy.
    Its output is indistinguishable from a correct run. Three long-lived processes ran stale code
    within one hour on 2026-07-27 and every one was caught by hand, by comparing a start time
    against a commit time. This stamps the answer into the artifact the loop already writes.

    TWO THINGS IT DELIBERATELY DOES NOT DO, each a way the check would certify what it exists to
    detect:

      * NOT git metadata. A sha from `git log` describes the REPO; this process runs a FILE. On a
        dirty tree git reports CURRENT while the loop runs bytes that were never committed. The
        fingerprint is taken from the file contents, so it answers the question actually asked.
      * NOT watch.py alone. The loop's live code is its whole import surface — watch.py:78 is
        `import coord`, and on 2026-07-27 coord.py drifted FOUR commits under a running loop whose
        own watch.py was current. A watch.py-only marker would have read CURRENT throughout, which
        is precisely the state it is for. So the set is DERIVED from sys.modules rather than
        enumerated: every loaded module whose file sits in the kit directory is covered, and a kit
        module added later is covered without anyone remembering to add it here.

    HONEST LIMIT, stated rather than left to be discovered: the bytes are re-read from disk
    immediately after import, not intercepted during it. A file rewritten inside that microsecond
    window would be fingerprinted as its new bytes. That is not the failure mode this addresses —
    the real one lasts minutes to hours — but the marker means "the file as it stood at this
    process's import", never "the bytes the interpreter compiled".
    """
    kit = Path(__file__).resolve().parent
    out = {}
    for mod in list(sys.modules.values()):
        path = getattr(mod, "__file__", None)
        if not path:
            continue
        try:
            resolved = Path(path).resolve()
            if resolved.parent != kit or resolved.suffix != ".py":
                continue
            out[str(resolved)] = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except OSError:
            continue  # unreadable at import: absent from the map, reported UNKNOWN, never a crash
    return out


# Computed ONCE, at import, on purpose. Recomputing per pass would hash the file on disk and
# compare it against itself — a detector that can never fire, and the exact green-harness shape
# this run has paid for repeatedly (the harness supplying the value under test).
LOADED_CODE = _loaded_code_fingerprint()

WINDOW_DEFAULT = 1_000_000
TAIL_LINES = 60  # pane-content hash window: enough to see any output change, cheap to capture


def now_dt():
    return datetime.now()


def window_size():
    try:
        v = int(os.environ.get("RBTV_CONTEXT_WINDOW", ""))
        if v > 0:
            return v
    except ValueError:
        pass
    return WINDOW_DEFAULT


# ---------- tmux (stubbable) ----------

def pane_tail(pane):
    r = subprocess.run(["tmux", "capture-pane", "-p", "-t", pane],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return "\n".join(r.stdout.splitlines()[-TAIL_LINES:])


def live_panes():
    return coord.live_panes()


def pane_cwd(pane):
    """Live cwd of a tmux pane, or None if the pane is unknown / tmux is unavailable."""
    r = subprocess.run(["tmux", "display-message", "-p", "-t", pane, "-F", "#{pane_current_path}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    out = r.stdout.strip()
    return out or None


def at_approval_gate(pane):
    """P38 detection half. The marker set and the title read both live in coord (`coordinate send`
    needs the same predicate to skip a blind gate seat, 8(b)) — one definition, two consumers."""
    return coord.at_approval_gate(pane)


def window_panes():
    """Live panes grouped by 'session:window' — one tmux call (PROP-10). {} when tmux is
    unavailable or unreadable; callers treat {} as unmeasurable, never as 'all windows gone'."""
    try:
        r = subprocess.run(["tmux", "list-panes", "-a", "-F",
                            "#{session_name}:#{window_name}\t#{pane_id}"],
                           capture_output=True, text=True)
    except OSError:
        return {}
    if r.returncode != 0:
        return {}
    out = {}
    for ln in r.stdout.splitlines():
        if "\t" not in ln:
            continue
        win, pane = ln.split("\t", 1)
        out.setdefault(win, []).append(pane.strip())
    return out


# ---------- system pressure (stubbable) ----------

def system_pressure():
    """RAM/load reading for PROP-9. Returns {"avail_mb", "load1", "cores"}, or None where
    /proc is unavailable (a non-Linux box) — the check skips honestly, never fakes a reading."""
    try:
        avail_kb = None
        with open("/proc/meminfo", encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("MemAvailable:"):
                    avail_kb = int(ln.split()[1])
                    break
        if avail_kb is None:
            return None
        with open("/proc/loadavg", encoding="utf-8") as f:
            load1 = float(f.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None
    return {"avail_mb": avail_kb // 1024, "load1": load1, "cores": os.cpu_count() or 1}


# ---------- claude transcript matching ----------

def munge_cwd(cwd):
    return re.sub(r"[/.]", "-", str(cwd))


def projects_dir(override=None):
    if override:
        return Path(override)
    return Path.home() / ".claude" / "projects"


def first_user_text(path, max_lines=40):
    """Text of the first user entry in a transcript JSONL ('' on any failure)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(e, dict) or e.get("type") != "user":
                    continue
                msg = e.get("message") or {}
                content = msg.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    except OSError:
        pass
    return ""


def find_transcript(agent, cwd, proj_override=None):
    """Newest transcript JSONL in cwd's project dir whose boot prompt names this agent."""
    pdir = projects_dir(proj_override) / munge_cwd(cwd)
    if not pdir.is_dir():
        return None
    marks = (f"You are agent '{agent}'", f"You are **{agent}**")
    candidates = []
    for p in sorted(pdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        head = first_user_text(p)
        if any(m in head for m in marks):
            candidates.append(p)
    return candidates[0] if candidates else None


def find_transcript_by_path_fragment(agent, cwd, proj_override=None):
    """Fallback for a seat whose boot prompt never carries the standard launch phrasing (a
    hand-started seat, e.g. leader). Newest transcript JSONL in cwd's project dir whose first
    user text references this seat's own `workers/<agent>/` path fragment. mtime alone is never
    sufficient — the fragment match is required."""
    pdir = projects_dir(proj_override) / munge_cwd(cwd)
    if not pdir.is_dir():
        return None
    fragment = f"workers/{agent}/"
    candidates = []
    for p in sorted(pdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        head = first_user_text(p)
        if fragment in head:
            candidates.append(p)
    return candidates[0] if candidates else None


def transcript_usage(path):
    """(tokens, pct) from the LAST non-sidechain assistant turn — context-monitor hook math."""
    last = 0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(e, dict) or e.get("type") != "assistant" or e.get("isSidechain"):
                    continue
                usage = (e.get("message") or {}).get("usage") or {}
                total = (usage.get("input_tokens", 0)
                         + usage.get("cache_read_input_tokens", 0)
                         + usage.get("cache_creation_input_tokens", 0))
                if total:
                    last = total
    except OSError:
        return 0, 0.0
    return last, round(100.0 * last / window_size(), 1)


# ---------- state ----------

def goal_state(base):
    """(goal-level watch-state.json, this run's tag) — or (None, None) if `base` is not inside a
    goal folder (task 7.37 criterion 3 / settle-ledger R10).

    RESOLVED HERE, NOT IN coord.base_dir: base_dir is coord's, and coord.py is a separate custody.
    watch.py:78 is `import coord`; a watcher relocation has no business reaching into the file the
    whole room's messaging shares.

    THE GOAL FOLDER IS IDENTIFIED BY ITS `runs.csv` — the run INDEX (R11), not by counting path
    segments. A parent-walk of fixed depth would silently pick the wrong directory for any package
    that is not exactly `{goal}/runs/run-{n}/coordination`, and would resolve SOMETHING rather than
    nothing — the failure mode where a watcher writes a goal file outside the goal.

    Returns (None, None) rather than raising or guessing when there is no goal above: a package
    with no goal folder (the selftest's temp tree, a bare `--base`) keeps the pre-7.37 per-run
    behaviour untouched. Absence of a goal is a legitimate shape, not an error."""
    try:
        run_dir = base.parent                      # {goal}/runs/run-{n}
        goal = run_dir.parent.parent               # {goal}
        if run_dir.parent.name != "runs" or not (goal / "runs.csv").is_file():
            return None, None
        return goal / "watch-state.json", run_dir.name
    except (OSError, IndexError):
        return None, None


def _migrate_runs(goal):
    """Every run's legacy per-run state, as {run-tag: {...}} — the one-time lift into the goal file.

    MIGRATED, NOT DISCARDED, and the reason is not sentiment: the live loop already holds this
    run's flags, so a goal file that started EMPTY would re-arm every seat on the first pass and
    re-fire notifications already sent. The migration is what makes the cutover SILENT. Discarding
    would also satisfy a naive reading of "survives across runs" while destroying every flag on
    disk — the trap ruling-737-watchpy-bars.md §7 names."""
    out = {}
    for p in sorted((goal / "runs").glob("run-*/coordination/watch-state.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(d, dict) and d:
            out[p.parent.parent.name] = d
    return out


def _read_goal_file(p):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    runs = d.get("runs") if isinstance(d, dict) else None
    return runs if isinstance(runs, dict) else {}


def load_state(base):
    """This run's watcher state — from the GOAL-level file when there is a goal, else per-run.

    ⚠ THIS RUN'S SECTION ONLY. Prior runs are PRESERVED in the file and never merged into the
    evaluation, and that is the whole of criterion 3's "read correctly". Measured across both runs
    on disk, EVERY key this file holds is per-run by construction — `pane`, `hash`, `stable_since`
    and the `notified_*` re-arm flags all describe a seat in a tmux room that R15 tears down at run
    close. There is no field for which cross-run inheritance is correct, so a flat name-keyed merge
    is not merely risky: it has nothing to get right.

    Proven by A/B on an identical fixture (seats/S9-737-watchstate/probe_737_c3.py): a flat merge
    SUPPRESSES a real ghostrow flag and SPURIOUSLY fires an inactivity flag; per-run sections do
    neither. ⚠ The suppression is gated on PANE-ID EQUALITY — `:813`/`:836` re-arm when the pane
    differs — so it is narrower than ruling-737-watchpy-bars.md §3 states, and that guard is
    coincidental rather than designed (nothing keeps tmux pane ids unique across runs; a tmux
    server restart resets the counter). A protection nobody knows they have is one nobody maintains.
    """
    p, tag = goal_state(base)
    if p is None:
        legacy = base / "watch-state.json"          # no goal above: pre-7.37 behaviour, untouched
        if legacy.exists():
            try:
                return json.loads(legacy.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}
    runs = _read_goal_file(p) if p.exists() else _migrate_runs(p.parent)
    got = runs.get(tag)
    return got if isinstance(got, dict) else {}


def save_state(base, state):
    """Write back THIS RUN'S SECTION, leaving every other run's byte-for-byte.

    Read-modify-write, because the file is shared with any other run's loop. ⚠ THIS NARROWS THE
    UNLOCKED-WRITER HAZARD, IT DOES NOT CLOSE IT, and saying so is the point: two coexisting loops
    touch DIFFERENT sections so neither clobbers the other's flags in the ordinary case, but a
    read-modify-write race can still drop a section. `coord.atomic_write` is atomic PER WRITE,
    which is not the same as safe under two writers. The real fix is R9's one-live-run enforcement
    (task 7.77, unbuilt) — until it lands this rests on the hand-held convention 7.37's own task
    body names. NO `coord_lock` is added here: that lives in coord.py, which is a separate custody."""
    p, tag = goal_state(base)
    if p is None:
        coord.atomic_write(base / "watch-state.json", json.dumps(state, indent=1))
        return
    runs = _read_goal_file(p) if p.exists() else _migrate_runs(p.parent)
    runs[tag] = state
    coord.atomic_write(p, json.dumps({"runs": runs}, indent=1))


def load_sys_state(base):
    """PROP-9/PROP-10 re-arm state. A SEPARATE file from watch-state.json for the P32 reason:
    that file is keyed by agent name, and a reserved key inside it would be one roster name away
    from a collision."""
    p = base / "watch-system.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_sys_state(base, st):
    coord.atomic_write(base / "watch-system.json", json.dumps(st, indent=1))


def load_heartbeat(base):
    """The heartbeat this loop last wrote, or None. Read back rather than held in memory ON
    PURPOSE: a one-shot pass has no memory of a previous one, and the restart comparison must work
    across separate invocations exactly as it does across loop iterations."""
    p = base / "watch-heartbeat.json"
    if not p.exists():
        return None
    try:
        hb = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return hb if isinstance(hb, dict) else None


IGNITE_UNIT = "rbtv-ignite.service"


def _int_or_none(kv, key):
    """systemd's counter as an int, or None when it is absent/unparseable — never 0 on failure.

    0 is a MEANINGFUL value here (a unit that has never restarted), so defaulting a failed read to
    0 would report the healthiest possible answer at the moment the read broke. None is the only
    honest absence, and the caller treats it as "no comparison possible" rather than "no climb"."""
    raw = kv.get(key)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def daemon_identity():
    """The ignite daemon's systemd identity THIS PASS — or UNKNOWN, said out loud (run issue G-188).

    WHY THE LOOP SAMPLES A DAEMON AT ALL. Twice on 2026-07-27 the daemon was restarted by an
    owner-side act and the run did not know: a 15:27 restart nobody noticed, and a full deploy at
    03:45 that the run spent ~50 minutes reasoning around with a false picture, including an owner
    brief that had to be withdrawn. `ignite inspect daemon` does publish pid and uptime — but only
    to whoever thinks to ask, and nobody asks a question they do not know to have. This loop is the
    run's only thing that observes continuously, so the observation belongs here.

    ⚠⚠ `--user` IS LOAD-BEARING AND IS NOT A STYLE CHOICE. The unit is user-scoped. Asking the
    SYSTEM bus for it returns, MEASURED on this box against the live daemon:
        LoadState=not-found  ActiveState=inactive  SubState=dead  MainPID=0  exit 0
    which is BYTE-IDENTICAL to what the user bus returns for a unit that genuinely does not exist.
    Exit status is 0 in both cases. So "the daemon is gone" and "I asked the wrong bus" are THE SAME
    ANSWER, and no amount of care at the call site can tell them apart afterwards.

    ⇒ THEREFORE `not-found` IS REPORTED AS UNKNOWN, NEVER AS ABSENT. That is not caution; it is the
    measurement above. This run's signature failure is absence being indistinguishable from health,
    and a checker that answers "absent" here would be asserting a fact it provably cannot hold.
    A determinate `loaded` + `inactive` IS reportable as stopped — there the unit answered for
    itself. Only the ambiguous case degrades to UNKNOWN.

    Returns one of:
        {"state": "running", "unit": str, "pid": int, "since": str, "invocation": str}
        {"state": "stopped", "unit": str, "why": str}     — the unit answered; it is down
        {"state": "unknown", "unit": str, "why": str}     — the question could not be answered
    `invocation` is systemd's InvocationID, minted fresh on every start, and it is the identity the
    restart comparison keys on rather than MainPID: a pid is recycled by the kernel and carries no
    promise of uniqueness across time, while the InvocationID exists precisely to say "this is a
    different run of the same unit".

    Every reading CARRIES the unit it asked about. The reader in `coord.workers` renders that value
    instead of holding a literal of its own — coord cannot import watch (watch imports coord), so a
    second copy of the name would be a copy nobody keeps in step, and it would go stale in the one
    line whose job is telling an operator which unit to go and ask about (run issue G-107's shape:
    carry the subject, never re-derive it)."""
    props = ["LoadState", "ActiveState", "SubState", "MainPID", "ActiveEnterTimestamp",
             "InvocationID", "NRestarts"]
    try:
        out = subprocess.run(["systemctl", "--user", "show", IGNITE_UNIT,
                              "--property=" + ",".join(props)],
                             capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"state": "unknown", "unit": IGNITE_UNIT,
                "why": f"systemctl --user did not answer ({exc})"}
    if out.returncode != 0:
        return {"state": "unknown", "unit": IGNITE_UNIT,
                "why": f"systemctl --user exited {out.returncode}: "
                       f"{(out.stderr or '').strip()[:120] or 'no stderr'}"}
    kv = {}
    for line in (out.stdout or "").splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip()
    load = kv.get("LoadState")
    if not load:
        return {"state": "unknown", "unit": IGNITE_UNIT,
                "why": "systemctl --user printed no LoadState"}
    if load != "loaded":
        return {"state": "unknown", "unit": IGNITE_UNIT,
                "why": f"LoadState={load} — indistinguishable from asking the wrong bus, so this "
                       f"is NOT reported as absent"}
    active = kv.get("ActiveState", "")
    if active != "active":
        return {"state": "stopped", "unit": IGNITE_UNIT, "restarts": _int_or_none(kv, "NRestarts"),
                "why": f"the unit answered for itself: ActiveState={active or '?'} "
                       f"SubState={kv.get('SubState') or '?'}"}
    invocation = kv.get("InvocationID") or ""
    pid = kv.get("MainPID") or ""
    if not invocation or not pid.isdigit() or int(pid) <= 0:
        return {"state": "unknown", "unit": IGNITE_UNIT,
                "why": f"unit is active but its identity is unreadable "
                       f"(MainPID={pid or '?'}, InvocationID={'set' if invocation else 'empty'})"}
    return {"state": "running", "unit": IGNITE_UNIT, "pid": int(pid),
            "restarts": _int_or_none(kv, "NRestarts"),
            "since": kv.get("ActiveEnterTimestamp") or "", "invocation": invocation}


def _daemon_change(prev, now):
    """The restart record to persist, or None — given the PREVIOUS pass's reading and this one's.

    A change is only claimed when BOTH readings are determinate. A transition into or out of
    `unknown` is a MEASUREMENT failing, not an event observed, and reporting it as a restart would
    manufacture exactly the false certainty this feature exists to remove."""
    if not isinstance(prev, dict) or not isinstance(now, dict):
        return None
    if prev.get("state") == "unknown" or now.get("state") == "unknown":
        return None
    same = (prev.get("state") == now.get("state")
            and prev.get("invocation", "") == now.get("invocation", ""))
    if same:
        return None
    return {"at": now_dt().isoformat(timespec="seconds"), "from": prev, "to": now}


def daemon_reading(base):
    """(this pass's daemon identity, the sticky change record) — sampled ONCE per pass.

    ⚠ WHY THIS IS ITS OWN FUNCTION RATHER THAN LEFT INSIDE save_heartbeat, and it is a correctness
    point rather than tidiness: the box-level FLAG runs at the top of a pass and the heartbeat is
    written at the BOTTOM. Sampling in both places would issue two `systemctl` calls per pass whose
    answers can differ — the daemon can restart between them — and the room would then get a flag
    announcing a restart while the heartbeat on disk recorded the identity from BEFORE it, or the
    reverse. Two readings of one moment that disagree is the defect class this whole feature exists
    to close, so the pass takes ONE reading and both consumers use it."""
    prev = load_heartbeat(base)
    daemon = daemon_identity()
    change = _daemon_change((prev or {}).get("daemon"), daemon)
    if change is None:
        change = (prev or {}).get("daemon_change")
    return daemon, change


def daemon_code_state(workspace_root, daemon):
    """Is the DAEMON running current code? — G-188 stage 3. Returns (verdict, detail).

    The watcher already gets this question asked of itself (`G-158`); the daemon never did, and its
    answer was an INFERENCE from start-time against commit-time. The daemon now writes a
    credential-free marker at boot; this correlates it and hashes the same files from disk NOW.

    ⚠⚠ THE MARKER OUTLIVES THE PROCESS THAT WROTE IT, and that is the whole reason this function is
    careful (leader ruling `#840`, binding). It is a file: if the daemon dies, the marker SURVIVES
    carrying the last boot's fingerprint. A reader trusting it standalone would report "code is
    current" about a daemon that is not running — absence-reading-as-health, arriving through the
    artifact built to prevent it.

    ⇒ THE THREE OUTCOMES ARE KEPT DISTINCT AND COLLAPSING ANY TWO IS THE DEFECT:
        "stale"    the marker MATCHES the live unit's boot AND named files have changed on disk.
        "current"  the marker matches the live unit's boot and every named file still agrees.
        "unknown"  anything else — no marker, corrupt marker, a marker from a DIFFERENT boot, or a
                   daemon that is not determinately running. NEVER stale, NEVER current.
    A marker whose identity does not match the live unit says nothing about the running process, so
    the only honest verdict is UNKNOWN — and it is said out loud rather than left as silence."""
    if not isinstance(daemon, dict) or daemon.get("state") != "running":
        # No determinate live identity to correlate against. Any verdict about "the running code"
        # would be a claim about a process we cannot even confirm is running.
        return "unknown", "the daemon is not determinately running, so nothing can be correlated"
    p = Path(workspace_root) / ".rbtv" / "runtime" / "daemon-code.json"
    try:
        marker = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return "unknown", ("no boot marker at .rbtv/runtime/daemon-code.json — this daemon booted "
                           "before the marker existed, or its write failed")
    except (json.JSONDecodeError, OSError) as exc:
        return "unknown", f"the boot marker is unreadable ({exc.__class__.__name__})"
    if not isinstance(marker, dict):
        return "unknown", "the boot marker is not an object"
    live_inv, mark_inv = daemon.get("invocation"), marker.get("invocation")
    # ⚠ THE CORRELATION, and it is the bar. Identity first, bytes second — a byte comparison against
    # a marker from a previous boot is arithmetic about a process that no longer exists.
    if not mark_inv or not live_inv or mark_inv != live_inv:
        return "unknown", (f"the marker is from a DIFFERENT boot than the running unit "
                           f"(marker {str(mark_inv)[:12] or 'none'}, live {str(live_inv)[:12]}), so "
                           f"it describes a process that is gone")
    entries = (marker.get("code") or {}).get("entries")
    if not isinstance(entries, dict) or not entries:
        # Empty-but-present is the state that lies; the writer never emits it, and a reader that
        # accepted it would report "nothing drifted" forever.
        return "unknown", "the marker carries no file fingerprints"
    # ⚠ THE ROOT IS TAKEN FROM THE MARKER, NEVER RE-DERIVED HERE. This kit is shared by every
    # workspace, and a literal like `3-resources/tools/rbtv/ignite/server` would freeze one vault's
    # layout into a tool other installs run — the same objection that keeps campaign role names out
    # of this file. The writer knows its own root; it says so, and this trusts what it said.
    root = marker.get("code_root") or marker.get("root")
    if not root:
        return "unknown", ("the marker does not say which root its paths are relative to, so they "
                           "cannot be resolved without guessing this install's layout")
    root = Path(root)
    drifted = []
    for rel, want in sorted(entries.items()):
        try:
            got = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        except OSError:
            drifted.append(f"{rel} (unreadable now)")
            continue
        if got != want:
            drifted.append(rel)
    if drifted:
        return "stale", ", ".join(drifted[:6]) + (f" (+{len(drifted) - 6} more)"
                                                 if len(drifted) > 6 else "")
    return "current", f"{len(entries)} files match the bytes this daemon booted on"


def check_daemon(sysstate, daemon, change, notes, code=None):
    """PROP-9's box-level sibling for the ignite daemon — the PUSH half of G-188.

    What landed first was PULL-ONLY: it renders on `coordinate workers`, so somebody must type it.
    A daemon that dies at 04:00 stays invisible until somebody does — and *nobody thought to ask*
    IS the original defect. `ignite inspect daemon` answered for anyone who asked the whole time.

    HOME, ruled (leader `#811`): the daemon is NOT a seat, so 7.32/7.33's per-seat flag set is the
    wrong population; this belongs beside `check_system`, which is already the BOX-level path.

    ⚠ THE CALIBRATION THIS IS BUILT AGAINST. Of run-1's 12 attributable PER-SEAT flags, ELEVEN WERE
    FALSE POSITIVES, and the one class that actually cost the run anything raised no flag at all.
    A flag earns its interruption by naming a HARD, MEASURABLE transition — never a judgment, never
    the watcher's own difficulty. That is why:

      DOWN       flags ONCE PER EPISODE, re-arming when the unit returns.
      RESTARTED  flags ONCE PER EVENT, keyed on the new InvocationID.
      UNKNOWN    NEVER pushes. It means THE MEASUREMENT FAILED, not that something happened; it is
                 unactionable at 04:00, and a flag that fires on the watcher's own blindness is
                 exactly what trains a room to discount the next one. It stays LOUD on `workers`.
                 ⚠ THE PRICE, named rather than buried: a daemon dying while `systemctl` is
                 unreadable is un-pushed. Never invisible — un-pushed. Judged the right trade at
                 11-of-12; one branch to reverse if the leader ever overrules it.

    ⚠ ONCE-PER-EPISODE IS CORRECT HERE FOR THE REASON THAT MAKES IT WRONG IN check_system, and the
    difference must be argued rather than copied across. PROP-9 carries a leader ruling that a flag
    must re-fire while its condition WORSENS — because RAM slid 2,904 -> 2,695 MB and the room heard
    once. That ruling turns on MONOTONIC vs FLAPPING. RAM slides toward an OOM, so each new reading
    is a new actionable fact. DOWN IS BINARY: a daemon down three hours is not more down than at
    three minutes and the remedy does not change, so a duration ladder would emit alerts carrying no
    new decision — the 11-of-12 failure mode with a timer bolted on. The standing state is never
    lost either way: `coordinate workers` shows DOWN on every pull; only the INTERRUPTION is bounded.

    ⚠ THE RESTART KEY IS THE INVOCATION, NOT THE PRESENCE OF A CHANGE RECORD. `daemon_change` is
    STICKY by design, so flagging on its mere presence would re-announce the same restart on every
    pass forever. Keying on the new InvocationID also means a restart that happened while the LOOP
    was down is still announced exactly once when the loop returns — which is the case the run
    actually suffered. If `watch-system.json` is ever lost, the notified key goes with it and one
    duplicate announcement follows; a single duplicate, not a storm, and stated here so it is not
    mistaken for a second restart.

    At most ONE note per pass (the bound this seat proposed and the leader held it to). Returns the
    report line."""
    state = (daemon or {}).get("state")
    restarts = (daemon or {}).get("restarts")
    seen = sysstate.get("daemon_restarts_flagged")
    # ⚠ THE CRASH-LOOP CASE, and my own design argument was INCOMPLETE until the run's history
    # corrected it. I argued DOWN is BINARY — three hours down is not more down than three minutes,
    # so once per episode. That is true of a STEADY outage and FALSE of a crash loop, which is the
    # shape the real incident took: 2026-07-27 16:15, `NRestarts=32 and climbing every 5 seconds`,
    # learned by a seat noticing BY HAND. A crash loop is MONOTONIC — the count climbs — so it is
    # PROP-9's deterioration case exactly, and PROP-9's ruling (a flag must re-fire while its
    # condition worsens) governs rather than my binary argument.
    # It is read from systemd's OWN NRestarts rather than counted from my sampling: a 10-minute
    # loop watching a 5-second loop would undercount by two orders of magnitude and call a storm
    # a single restart.
    climbing = isinstance(restarts, int) and isinstance(seen, int) and restarts > seen
    lines = []
    if state == "stopped":
        if not sysstate.get("notified_daemon_down") or climbing:
            loop = (f" ⚠ AND IT IS CRASH-LOOPING: systemd's own restart count has risen "
                    f"{seen} -> {restarts} since the last warning, so it is failing repeatedly "
                    f"rather than sitting still." if climbing else
                    " Announced ONCE for this outage: it stays on `coordinate workers` until it "
                    "clears.")
            lines.append(f"watch: IGNITE DAEMON IS DOWN — {daemon.get('why') or 'unit inactive'}. "
                         f"Nothing is running jobs, ticks or spawns.{loop}")
            sysstate["notified_daemon_down"] = True
            if isinstance(restarts, int):
                sysstate["daemon_restarts_flagged"] = restarts
    elif state == "running":
        # Re-arm on recovery, so a SECOND outage is announced. Only a determinate `running` clears
        # it — see the `unknown` branch below, which deliberately clears nothing.
        sysstate.pop("notified_daemon_down", None)
        to = (change or {}).get("to") or {}
        inv = to.get("invocation")
        if inv and sysstate.get("notified_daemon_invocation") != inv:
            frm = (change or {}).get("from") or {}
            lines.append(
                f"watch: IGNITE DAEMON RESTARTED — pid {frm.get('pid') or '?'} -> "
                f"{to.get('pid') or '?'}, observed {(change or {}).get('at') or '?'}. An "
                f"owner-side deploy or bounce is otherwise INVISIBLE to this run; that happened "
                f"twice on 2026-07-27 and was noticed hours late both times. This says THAT it "
                f"restarted, never WHICH CODE it loaded.")
            sysstate["notified_daemon_invocation"] = inv
        # SEEDED QUIETLY on the running path, never flagged from here (PROP-9's migration lesson,
        # the G-135/G-152 shape): a unit that crash-looped BEFORE this code landed carries a high
        # NRestarts, and announcing it now would report an outage the room already lived through.
        # A fix whose first act is a false alarm teaches the room to discount the next one.
        if isinstance(restarts, int):
            sysstate["daemon_restarts_flagged"] = restarts
    # G-188 stage 3: the daemon running STALE CODE is a hard, measurable transition and belongs in
    # the same single note. Keyed on the digest so one deploy is announced ONCE, not every pass —
    # the same reason the restart flag keys on the InvocationID rather than on a record existing.
    # UNKNOWN never pushes here either: it is the marker failing to correlate, not an event.
    if code and code[0] == "stale":
        seen_stale = sysstate.get("notified_daemon_stale")
        key = f"{(daemon or {}).get('invocation')}:{code[1]}"
        if seen_stale != key:
            lines.append(f"watch: IGNITE DAEMON IS RUNNING STALE CODE — {code[1]} changed on disk "
                         f"since this daemon booted, and node binds a module's source at require, "
                         f"so the running daemon can never pick it up. It will keep serving the OLD "
                         f"behaviour while every surface reports healthy. A restart deploys it "
                         f"(owner-only, task 7.68).")
            sysstate["notified_daemon_stale"] = key
    elif code and code[0] == "current":
        sysstate.pop("notified_daemon_stale", None)
    # `unknown` falls through: no note, and NOTHING IS CLEARED. Popping the down-flag on an
    # unreadable pass would silently re-arm a duplicate announcement for an outage the room has
    # already been told about — a measurement failing must never be able to manufacture a flag.
    if lines:
        notes.append(" ".join(lines))
    label = {"running": "ok", "stopped": "DOWN", "unknown": "UNKNOWN"}.get(state, "UNKNOWN")
    detail = (f"pid {daemon.get('pid')}" if state == "running"
              else (daemon or {}).get("why") or "unreadable")
    if isinstance(restarts, int) and restarts:
        detail += f" (systemd restarts: {restarts})"
    if code:
        # Printed in EVERY state, including current: G-158's second pass proved that a healthy case
        # printing nothing leaves "checked and current" to be inferred from an absence, in the one
        # feature whose whole subject is that absence and health look identical.
        detail += {"current": ", running current code",
                   "stale": ", RUNNING STALE CODE",
                   "unknown": f", code UNKNOWN ({code[1]})"}.get(code[0], "")
    return f"{'daemon':<18} {label:<7} {detail}"


def save_heartbeat(base, loop_min, daemon=None, change=None, daemon_code=None, budget=None):
    """P32 — stamp this pass so something outside the loop can tell a live watcher from a dead one.

    A SEPARATE file from watch-state.json on purpose: that file is keyed by agent name, and a
    reserved key inside it would be one roster name away from a collision. Failure is swallowed —
    a heartbeat that cannot be written must never take the watcher down with it (the same
    read-only-package tolerance coord's cursor persistence has).

    `code` carries LOADED_CODE — the fingerprint of the source THIS PROCESS loaded, so a reader
    outside can tell a live loop running current code from a live loop running stale code (G-158).
    P32 answered "is it running"; this extends the same artifact to "is it running WHAT WE THINK".

    `daemon` / `daemon_change` carry the ignite daemon's identity this pass and the last observed
    restart (G-188). THIS FILE, deliberately, and NOT watch-state.json — stated here because task
    7.37 relocates watch-state.json to goal level and whoever takes it inherits this field. Two
    reasons: watch-state.json is keyed by AGENT NAME and the daemon is not an agent (a reserved key
    there is one roster name away from a collision — the same reason this heartbeat file was split
    out for P32); and it is merged across runs, which is how a stale `notified_*` from run-1 can
    pre-suppress a run-2 flag. A restart record must never inherit another run's history.

    `daemon_change` is STICKY — it survives later passes until the next change replaces it, and it
    is stamped with `at`. A restart signal that expires after one pass would reproduce the exact
    miss this exists for: both restarts on 2026-07-27 were noticed hours late, by hand.

    ⚠ `daemon_code` carries the (verdict, detail) of "is the DAEMON running current code" — and it
    is here because LEAVING IT OUT WAS A REAL DEFECT, found by the chief-of-staff reading the source
    rather than trusting a prediction. The comparison ran every pass and reached ONLY the push
    surface: `coordinate workers` composes its line from THIS FILE, so a verdict absent here can
    never be printed there. **THE PULL SURFACE IS THE ONE THIS WHOLE FEATURE EXISTS TO SERVE** — the
    arc's own premise is that `inspect daemon` already answered whoever asked, and that *nobody
    thought to ask* WAS the defect. A value correctly computed with no consumer is `G-184`'s shape
    ("the sum was the signal and there is no consumer of the sum"), and no probe asserting this
    function's ARGUMENTS or `check_daemon`'s RETURN can see it: the break is between computation and
    surface, so the assertion has to live at the surface.

    `daemon`/`change` are PASSED IN by a pass that already took the reading, so one pass issues one
    `systemctl` call and the flag and the heartbeat can never describe different moments (see
    `daemon_reading`). They default to None for standalone callers — a direct call still samples,
    so the function keeps working on its own."""
    if daemon is None and change is None:
        daemon, change = daemon_reading(base)
    try:
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(
            {"last_pass": now_dt().isoformat(timespec="seconds"),
             "loop_min": loop_min, "pid": os.getpid(), "code": LOADED_CODE,
             "daemon": daemon, "daemon_change": change,
             # A tuple would round-trip through JSON as a list; named keys instead, so the reader
             # never indexes into a shape it has to remember.
             "daemon_code": ({"verdict": daemon_code[0], "detail": daemon_code[1]}
                             if daemon_code else None),
             # Room-capacity re-arm state. HERE and not in watch-state.json for the same measured
             # reason as the daemon fields above: that file is agent-keyed and merged across runs,
             # so a stale run-1 flag would silently pre-suppress a run-2 one.
             "budget": budget}, indent=1))
    except OSError as exc:
        print(f"watch: heartbeat not written ({exc}) — `coordinate workers` will report this "
              f"watcher STALE even while it runs", file=sys.stderr)


# ---------- notification ----------

class Flag(str):
    """A flag line that REMEMBERS WHICH SEAT IT IS ABOUT.

    A plain string was enough while every flag went to one hardcoded recipient. Routing needs the
    SUBJECT, and the subject is deliberately CARRIED rather than parsed back out of the rendered
    sentence: re-deriving `'leader'` from "watch: 'leader' context is at 52.6%" would be a check
    that INFERS a property instead of asserting it — the shape this run filed as `G-107` and paid
    for repeatedly. A `str` subclass keeps every existing reader (`'x' in note`, the report lines,
    the whole selftest) working untouched while the routing layer reads `.subject`.

    `subject is None` means the flag is about the ROOM, not a seat (system pressure, a leftover
    window) — those have no subject to divert away from and always go to the primary recipient."""

    subject = None

    def __new__(cls, subject, text):
        obj = super().__new__(cls, text)
        obj.subject = subject
        return obj


def flag_recipient(args, subject):
    """(recipient, diverted, orphaned) for a flag about `subject`.

    ⚠ THE RULE, and it is general rather than a special case for one seat: A FLAG ABOUT A SEAT MUST
    NEVER BE ROUTED TO THAT SEAT. `notify` used to hardcode `leader`, so a warning that the LEADER
    was out of context arrived in the leader's own inbox — a seat holding its own close/renew/approve
    with no seat above it and an AFK owner. That is the structural hole; the owner ruled the flags
    at the chief-of-staff. Pointing them there and stopping would move the hole rather than close
    it: a flag about the CoS would then land on the CoS. So the subject is diverted to a SECOND
    recipient whichever seat it is about, and the leader-subject case is one instance of it.

    Both recipients are ARGUMENTS defaulting to `leader`, never a name baked into this file. This
    kit is shared by every run; hardcoding `chief-of-staff` would freeze one campaign's roles into a
    tool other runs use — the exact objection that got `SPECIAL_CASE_SEATS` demoted to a default
    table. run-2 passes `--notify-to chief-of-staff`; the default keeps every other run's behaviour.

    `orphaned` is the honest third state: when subject, primary AND fallback are all the same seat
    there is no independent recipient at all, so the flag is delivered anyway AND recorded — a
    monitor with nowhere impartial to report must say so, not quietly report to the subject."""
    primary = getattr(args, "notify_to", None) or "leader"
    fallback = getattr(args, "notify_fallback", None) or "leader"
    if subject and subject == primary:
        if subject == fallback:
            return primary, False, True
        return fallback, True, False
    return primary, False, False


def record_undelivered(args, text, reason):
    """Append an UNDELIVERED flag to the run package, so a refused warning survives where the run
    looks instead of dying in a detached stderr.

    Deliberately NOT a coord message: this reports that the messaging layer refused something, so
    routing it back through that layer is the one path guaranteed to be able to fail the same way.
    A plain append under `coordination/` cannot be refused by a sender bound, a type enum, or a
    roster row — the three things that swallowed tonight's warnings.

    Best-effort like every other side-effect in this loop: a monitor must never die of its own
    bookkeeping. But it prints on failure, because the alternative is the silence being fixed."""
    try:
        base = coord.base_dir(argparse.Namespace(
            package=getattr(args, "package", None), base=getattr(args, "base", None)))
        base.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        line = f"- {stamp} | UNDELIVERED ({reason}): {' '.join(str(text).split())}\n"
        with open(base / "undelivered-flags.md", "a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except Exception as exc:                                   # noqa: BLE001
        print(f"watch: CANNOT RECORD an undelivered flag either ({exc}) — this warning is being "
              f"lost entirely: {str(text)[:120]}", file=sys.stderr)
        return False


def notify_leader(args, text):
    """Send one flag to its RECIPIENT through coord (so it is logged AND wakes the pane).

    Name kept for its callers; the recipient is now `flag_recipient`'s, not `leader` by fiat — see
    that function for why a flag never goes to the seat it is about.

    `agent="watcher"` is coord's internal identity API — the `--as` equivalent (the watcher loop
    runs outside any pane, so no identity contradiction can fire).

    ⚠ THIS SENDS A `note`, NOT AN `ask`, AND THAT ONE WORD IS THE WHOLE DELIVERY FIX. It sent an
    `ask`; the `watcher` ROLE WAS DISSOLVED mid-run and its roster row DELETED, so coord correctly
    refused every flag — an ask whose sender cannot be addressed can never be closed (S-7). The
    refusals went to stderr, into a detached log nobody reads, while the loop went on reporting
    healthy. Two individually-correct mechanisms composing into a silent failure: the dissolution
    audited the role's DUTIES and not the mechanisms that SEND AS it.
    A flag is a FACT, not a question — nothing is owed in reply, so a note is also the honest type,
    and coord accepts a note from an unaddressable sender by design. coord's own refusal text said
    so ("Send this as --type note"); the fix was written on the failure the whole time.

    NO SENDER IDENTITY IS MINTED HERE, deliberately: the loop is not a seat and must not become one
    (`r-watcher-attributions-distributed` — detection is the loop's, never a seat's). Reusing the
    relay machinery was considered and is UNNECESSARY, because a note needs no reply route at all."""
    subject = getattr(text, "subject", None)
    to, diverted, orphaned = flag_recipient(args, subject)
    if diverted:
        # The reader must know WHY this arrived here rather than with the usual recipient, and that
        # it is about a seat that cannot be told to act on itself. Prepended to the body because
        # coord carries no routing metadata a human reads.
        text = Flag(subject, f"[routed to you: this flag is ABOUT '{subject}', the seat it would "
                             f"normally go to] {text}")
    if orphaned:
        record_undelivered(args, text, f"no impartial recipient — '{subject}' is both the subject "
                                       f"and the only configured recipient; sent to it anyway")
    ns = argparse.Namespace(package=getattr(args, "package", None), base=getattr(args, "base", None),
                            workers_dir=getattr(args, "workers_dir", None),
                            agent="watcher", as_agent=None, to=to, message=str(text),
                            type="note", supersedes=None, re_num=None, file=None, force=False)
    try:
        # ⚠ THE SECOND REFUSAL, and the ruled fix did not reach it. `resolve_agent` refuses a
        # claimed identity that CONTRADICTS the calling pane's roster row — and its docstring
        # assumes this loop "runs outside any pane, so no contradiction can fire". FALSE: a
        # detached loop INHERITS `TMUX_PANE` from whatever shell started it, so when it was started
        # from the chief-of-staff's pane every flag was refused with "you claimed 'watcher', but
        # this pane (%145) is registered to 'chief-of-staff'" — exit 2, a different refusal from
        # the ask/S-7 one and immune to changing the message type. Both are in
        # /tmp/watch-run2.log; fixing only the documented one would have left the flag ABOUT the
        # chief-of-staff still refused, which is the crossing the owner noticed by eye.
        #
        # The loop is genuinely not in a pane; the inherited variable is noise, not identity. So it
        # is cleared for the send rather than overridden with --force, which would have suppressed
        # every OTHER refusal too — including ones that should stop a bad send.
        _prior = os.environ.pop("TMUX_PANE", None)
        try:
            coord.cmd_send(ns)
        finally:
            if _prior is not None:
                os.environ["TMUX_PANE"] = _prior
        return True
    except SystemExit as exc:
        # ⚠ A MONITOR THAT CANNOT DELIVER MUST SHOUT THAT IT CANNOT DELIVER. This used to print to
        # stderr and return, which is a fail-loud violation (conduct §9) at the exact point where
        # silence and health are indistinguishable — the loop kept printing "N new flag(s)" while
        # every flag was refused. stderr is not a channel: this one ran detached into /tmp for
        # hours. So the failure is written where the run actually looks, through a path that cannot
        # itself be refused by the messaging layer it is reporting on.
        print(f"watch: leader notification refused by coord (exit {exc.code}) — flag not sent: "
              f"{text[:80]}", file=sys.stderr)
        record_undelivered(args, text, f"coord refused the send (exit {exc.code})")
        return False


# ---------- system + leftover-window checks ----------

# A flag re-fires when its condition has got MATERIALLY WORSE since the reading that last flagged.
#
# ⚠ WHY THESE NUMBERS, since a threshold nobody can justify is the next agent's cargo cult:
# 250 MB is roughly HALF A SEAT — four seats closing returned ~2.4 GB on this box, ~600 MB each — so
# a 250 MB slide is a materially different staffing picture, not noise. It also bounds the noise:
# between the 2,800 MB launch floor and the 85%-used distress line (~1,162 MB available) there is
# ~1,640 MB, so 250 MB yields at most ~6 further warnings across an entire slide to distress. And it
# is calibrated against a REAL slide rather than imagined: 2,904 -> 2,773 -> 2,722 -> 2,695 MB over
# ten minutes, measured tonight, which re-flags about once per 10-minute pass while a slide is
# actually happening and goes quiet the moment RAM is merely low and stable.
# 1.0 is one core's worth of load — the same "one unit of the resource" logic.
PRESSURE_REFLAG_MEM_MB = 250
PRESSURE_REFLAG_LOAD = 1.0


def check_system(args, sysstate, notes):
    """PROP-9 — system memory/load as a first-class duty of the loop: the run's stuck-process
    pile-up OOM-killed the WATCHER itself, and nothing had the instrumentation to see the
    pressure building. Returns the report line, or None where unmeasurable.

    ⚠ A FLAG MUST BE ABLE TO FIRE AGAIN WHILE ITS CONDITION IS GETTING WORSE (leader ruling,
    2026-07-27). This flagged ONCE PER EPISODE and re-armed only when the pressure CLEARED, which is
    correct for a FLAPPING condition and wrong for a MONOTONIC one. Measured live the night it was
    found: available RAM fell 2,904 -> 2,695 MB in ten minutes, the room heard about it exactly
    once, and nothing further would have been said however far it fell — the next signal after that
    single warning is the OOM that kills the seats AND this watcher, the one process that would have
    reported it. Silence while the thing you warned about worsens is the same failure as silence
    while it starts, arriving later.

    So the flag ALSO re-arms on DETERIORATION, measured against the reading that last flagged rather
    than against the threshold. Deliberately NOT a second gate: no threshold moves, nothing new is
    refused, and the 2,800 floor and the 85%-used distress line are untouched and still serve their
    separate purposes (conduct §8 — they must never be reconciled). The only thing that changes is
    that the loop stops going quiet during a slide."""
    sp = system_pressure()
    if sp is None:
        return None
    floor = args.mem_floor_mb
    mem_low = sp["avail_mb"] < floor
    load_high = sp["load1"] >= sp["cores"] * args.load_per_core
    flags = []
    if mem_low:
        flags.append(f"MEM {sp['avail_mb']}MB<{floor}MB")
    if load_high:
        flags.append(f"LOAD {sp['load1']}/{sp['cores']}")
    if flags:
        prev = sysstate.get("pressure_reading")
        first = not sysstate.get("notified_pressure")
        worse = ""
        if not first and prev:
            if mem_low and sp["avail_mb"] <= prev.get("avail_mb", 0) - PRESSURE_REFLAG_MEM_MB:
                worse = (f"RAM has fallen a further {prev['avail_mb'] - sp['avail_mb']}MB since the "
                         f"last warning ({prev['avail_mb']}MB -> {sp['avail_mb']}MB)")
            elif load_high and sp["load1"] >= prev.get("load1", 0) + PRESSURE_REFLAG_LOAD:
                worse = (f"load has risen a further {round(sp['load1'] - prev['load1'], 2)} since "
                         f"the last warning ({prev['load1']} -> {sp['load1']})")
        if first or worse:
            # The trend is IN the message, because the trend is the actionable part: one reading
            # says the box is low, two say whether it is heading for an OOM.
            head = ("SYSTEM PRESSURE" if first
                    else f"SYSTEM PRESSURE WORSENING — {worse}.")
            notes.append(
                f"watch: {head} — {sp['avail_mb']}MB RAM available (floor {floor}MB), "
                f"load {sp['load1']}/{sp['cores']} cores. An OOM cascade kills seats AND this "
                f"watcher itself. Free the box NOW: accelerate close-out of idle/done seats, "
                f"tear down leftover dead wave windows (tmux kill-window), and pause further "
                f"launches until this clears.")
            sysstate["notified_pressure"] = True
            sysstate["pressure_reading"] = {"avail_mb": sp["avail_mb"], "load1": sp["load1"]}
        elif prev is None:
            # ⚠ MIGRATION, and it is the G-135/G-152 shape: this key is NEW, so an episode already
            # in progress when the code lands carries `notified_pressure` and NO reading to compare
            # against. Seed it from the current reading and stay QUIET — flagging here would fire a
            # spurious duplicate on upgrade, and a fix whose first act is a false alarm teaches the
            # room to discount the next one. Deterioration from this point re-flags normally.
            sysstate["pressure_reading"] = {"avail_mb": sp["avail_mb"], "load1": sp["load1"]}
    else:
        sysstate.pop("notified_pressure", None)
        sysstate.pop("pressure_reading", None)
    return (f"{'system':<18} {'FLAG' if flags else 'ok':<7} ram={sp['avail_mb']}MB "
            f"load={sp['load1']}/{sp['cores']}  {' '.join(flags)}")


def check_budget(base, notes, prev_hb, snap, snap_err):
    """ROOM CAPACITY — declared cap vs the live census. Returns (report_line, state).

    `snap`/`snap_err` are the ONE state.json snapshot `run_pass` hoists (s4-02) — the same pair
    `check_revival` (s4-03) consumes — never loaded privately here anymore. `snap_err` MUST stay
    distinguishable from `snap is None` with no error: a budget declared-but-unreadable and no
    budget declared are DIFFERENT FACTS (see the LOUD/SILENT split below).

    Box-level, so it sits beside `check_system` rather than in the per-seat loop: capacity is not
    a property of any seat, the same call `check_daemon` made for the daemon.

    ⚠ WHY THIS EXISTS AT ALL: run-2 spent a night at one executor against an "executor budget of
    2" that was written in NO ruling surface. It was a past census, saved into a seat's memory.md,
    carried across a renewal, and read by the successor as live policy — while RAM, the pane cap
    and the DAG all had room. A capacity number that lives only in prose decays into folklore, and
    nothing in the room could contradict it. This recomputes it every pass from two declared
    inputs, so the number can never again be something a seat merely remembers.

    ⚠⚠ IT PUSHES **BREACH ONLY**, and the omission is the design, not a gap. The obvious second
    flag — "a live agent pane nobody declared" — CANNOT BE STATED CORRECTLY over this data and was
    deliberately NOT shipped. Three legitimate descriptor-less agent panes exist (the staffer, the
    owner door, and the OWNER'S OWN claude session), and an owner session is observationally
    IDENTICAL to a leaked pane in state.json: live harness, no roster row, no descriptor. A flag
    on that predicate would have coached the chief-of-staff to close the owner's own session,
    which is G-176 — already fixed once here. Of run-1's 12 per-seat flags ELEVEN were false
    positives, and a usually-wrong flag trains its reader to ignore the real one (G-194). The
    unaccounted set is REPORTED by `budget.py` for whoever asks and wakes nobody.
    Full finding: seats/owner-liaison/finding-undeclared-pane-predicate.md.

    ⚠ RE-ARM STATE LIVES IN watch-heartbeat.json, NEVER watch-state.json — the engineer's catch,
    and the hazard is measured: watch-state.json is keyed by AGENT NAME and MERGED ACROSS RUNS, so
    a stale run-1 `notified_*` would pre-suppress a run-2 flag and the silence would be
    unexplainable from inside the room. Same reasoning that put the daemon fields here (G-188).

    HARD TRANSITIONS ONLY — flags on entering breach, once, and re-arms when it clears. UNKNOWN
    NEVER PUSHES: a stale snapshot means the SENSOR is the incident, and check_system already owns
    that alarm. Flagging capacity off a frozen room would describe a room that no longer exists.
    """
    # ⚠ THE RUN ROOT, NOT `base`. `base` is coord.base_dir() = {run}/coordination/, and both inputs
    # live one level up at the run root. The first version of this read them from `base`, found
    # neither, and took the fail-soft branch below EVERY PASS — a flag that could never fire, in
    # either direction, forever. `state.json` is no longer read HERE (s4-02 hoisted it into
    # `run_pass`, same root, same hazard note) — `bpath` is the one load this function still owns.
    root = base.parent
    bpath = root / "budget.json"

    # SILENT: no budget is declared here. The normal case for every other package, and it must stay
    # silent or this module cannot be shipped kit-wide.
    if not bpath.exists():
        return None, None

    # ⚠ LOUD: a budget WAS declared and could not be read. This half is the load-bearing one and its
    # absence is what hid the path defect — the fail-soft that makes the module safe everywhere else
    # made a WRONG PATH observationally identical to a run with no budget. Absence of a declaration
    # and failure to read a declaration are DIFFERENT FACTS; collapsing them is how this recurs
    # invisibly the next time a path moves, and tasks 7.32/7.33 WILL move this code.
    b, err_b = budget_mod._load(str(bpath), "budget.json")
    s, err_s = snap, snap_err
    prev = (prev_hb or {}).get("budget") or {}
    if err_b or err_s:
        if not prev.get("broken"):  # once per episode, like every other flag here
            notes.append(
                f"watch: BUDGET CHECK BROKEN — a budget.json IS declared at {bpath} but the "
                f"capacity check cannot run: {err_b or err_s}. THE ROOM HAS NO CAPACITY SIGNAL "
                f"UNTIL THIS IS FIXED — treat it as the check being down, never as the room being "
                f"within budget. Silence from this check is not a green.")
        return (f"{'budget':<18} {'BROKEN':<7} {err_b or err_s}",
                {"broken": True, "breaching": False})

    c = budget_mod.census(b, s)
    was = bool(prev.get("breaching"))
    now_breach = c["verdict"] == "BREACH"

    if now_breach and not was:
        notes.append(
            f"watch: ROOM OVER CAPACITY — {c['in_use']} agent panes live against a declared cap of "
            f"{c['cap']} ({-c['headroom']} over). The cap is in budget.json with its ruling; if the "
            f"cap is what is wrong, change it THERE rather than working around it, or the number "
            f"goes back to being folklore. No seat is closed for this: report and judge.")

    state = {"breaching": now_breach, "in_use": c["in_use"], "cap": c["cap"],
             "verdict": c["verdict"], "broken": False}
    # ⚠ The status word is the VERDICT, never a breach/no-breach binary. A stale snapshot renders
    # UNKNOWN, not `ok` — printing `ok` beside "SNAPSHOT STALE" would be absence reading as health,
    # which is this run's signature failure and was in the first draft of this very line.
    status = "FLAG" if now_breach else ("UNKNOWN" if c["verdict"] == "UNKNOWN" else "ok")
    line = (f"{'budget':<18} {status:<7} "
            f"{c['in_use']}/{c['cap'] if c['cap'] is not None else '?'} panes"
            f"{'' if c['complete'] else '  (INCOMPLETE — unclassified seats)'}"
            f"{'  SNAPSHOT STALE — no capacity claim is made' if c['stale'] else ''}")
    return line, state


# ---------- revival detection (stage 4 §1 — DETECTOR ONLY, s4-03) ----------
#
# REPORT-ONLY BY CONSTRUCTION. This block classifies and PRINTS; it claims nothing, writes no
# lifecycle marker, forks nothing. Actuation is s4-05 (the coord_lock interlock) + s4-06 (the
# fire). Landing the detector alone is safe: a mis-classification prints a wrong word. Landing
# actuation first would double-launch. Do not merge the two here.

REVIVAL_DEBOUNCE_TICKS = 2      # consecutive NON-STALE ticks a candidate must hold before CRASHED
REVIVAL_STALE_NOTE_TICKS = 3    # consecutive stale ticks before the sensor outage is flagged once

# Report-line literals. Kept as constants because the acceptance controls (task s4-03 § Acceptance
# 4, 6, 8, 9) grep for the EXACT strings — a reworded line is a silently-failing control.
REVIVAL_ROOM_DEAD_LINE = "REVIVAL n/a — room dead; recovery is jobs/recover-room.py (task 7.71)"
REVIVAL_STALE_LINE = "REVIVAL paused — snapshot stale"


def _snapshot_absent(snap_err):
    """True when `snap_err` means state.json is NOT THERE, as opposed to unreadable.

    ⚠ THE TWO ARE DIFFERENT FACTS AND THE DIRECTIONS ARE OPPOSITE — the same distinction
    `check_budget` preserves for budget.json (its SILENT/LOUD split): NO SNAPSHOT AT ALL is the
    normal case for every package that does not run team-monitor, and this module ships kit-wide,
    so it must stay silent there. A snapshot that EXISTS and cannot be read is a SENSOR OUTAGE and
    is treated as STALE — never as "no seat is absent", which would read absence as health.

    The discriminator is `budget._load`'s own message wording, because s4-02 hoisted the ONE
    state.json reading into `run_pass` and a second stat/read here would be a second observation of
    the same fact (and a race between them). The coupling to that wording is REAL, so the selftest
    asserts it directly against `budget_mod._load` on a missing path: if budget.py rewords, the
    control goes red rather than this predicate silently answering False forever."""
    return bool(snap_err) and " is ABSENT at " in snap_err


def _strict_ledger(path):
    """(data, status) with status in {"absent", "ok", "unparseable"} — the INVERTED reader.

    ⚠ WHY THIS IS NOT `coord.load_closing` / `coord.load_awaiting`. Both of those collapse an
    unreadable file to `{}` — "nobody is closing" / "no debt". That fail-SAFE direction is correct
    for THEIR callers (a parse error must not take `checkout` down) and DANGEROUS for this one: it
    would present a mid-close seat as having no ledger entry, i.e. as a crash, and a revival arm
    reading it would relaunch a seat that is closing cleanly. So this caller needs three states
    where they need two, and it gets them LOCALLY. Do NOT "fix" the shared loaders — their
    direction is right for them, and changing it would break the callers it protects.

    An EMPTY file reads as `absent`: both mean "no entry", both are safe to proceed on. Anything
    that is not a JSON object is `unparseable` — a list where a dict belongs cannot be looked up by
    seat, and guessing is the failure this reader exists to refuse."""
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, "absent"
    except OSError:                                            # present but unreadable != absent
        return {}, "unparseable"
    if not raw.strip():
        return {}, "absent"
    try:
        data = json.loads(raw)
    except ValueError:
        return {}, "unparseable"
    if not isinstance(data, dict):
        return {}, "unparseable"
    return data, "ok"


def _executor_ident_live(entry):
    """True when the marker entry's executor process is STILL THE SAME PROCESS.

    ⚠ PLAIN pid+starttime EQUALITY, NEVER `coord.ident_is_live_harness`. That predicate rests on
    `is_harness_argv` (`coord.py:1492`), which matches only claude/codex/opencode basenames — and
    the lifecycle executor is a PYTHON process. Asked about a live executor it answers DEAD, which
    turns MID-RENEWAL into CRASHED and produces the exact double-launch stage 4 exists to prevent
    (stage-3 §4.1 guards 4/5). A pid alone is not an identity either: the kernel recycles pids and
    a teardown is precisely when new processes start, so the starttime is the identity half."""
    ex = entry.get("executor") if isinstance(entry, dict) else None
    if not isinstance(ex, dict):
        return False
    pid, starttime = ex.get("pid"), ex.get("starttime")
    if not pid or starttime in (None, ""):
        return False
    try:
        return coord.proc_stat(int(pid))[1] == str(starttime)
    except (TypeError, ValueError):
        return False


def check_revival(args, base, snap, snap_err, state, notes):
    """SEAT-DOWN DETECTOR — classify every roster-absent seat. REPORT-ONLY (s4-03). Returns lines.

    ⚠⚠ A SLOW OR THINKING SEAT IS NEVER CLASSIFIED CRASHED, AND THAT IS STRUCTURAL, NOT TUNED.
    The discriminator is `harness_pid` liveness and NOTHING ELSE: `last_activity_age_s` and
    `prompt_pending` are NOT READ BY THIS ARM AT ALL — not as a tiebreak, not as a hint. A seat
    forty minutes into one ruling has `liveness: live` and a real `harness_pid`, so it cannot enter
    `roster_absent` in the first place. This is the ruling's BINDING CONDITION
    (`r-leader-revival-is-deterministic`): the trigger is a HARD liveness signal — pane/pid death —
    NEVER a silence timeout, because a leader thinking through a long ruling and a leader that is
    gone produce the SAME signal under every detector this run owns (measured: neither watch.py nor
    state.json samples CPU), and a relaunch fired on silence would kill a live leader mid-judgement
    and lose the turn. THE NEXT READER WILL WANT TO "IMPROVE" THIS WITH AN ACTIVITY AGE. Do not.

    Candidate set is `snap["roster_absent"]` — `team_monitor.absent_rows` already computes exactly
    this conjunction (roster row ACTIVE and (pane gone → `absent` | pane present, no harness →
    `no-harness`)). Re-deriving it from `snap["seats"]` would give one fact a second home. It is
    strictly broader than either loop in `run_pass`: the ghostrow loop visits only panes present in
    `live`, and the per-seat flag loop skips `watcher`. Scope is EVERY roster-active seat, not
    `leader` alone — the ruling's own rejection (c) is that a per-role responder just moves the
    hole, the lesson `flag_recipient` already generalised for flags.

    ⚠ `agent_type` / `agent_type_source` ride on these rows (task 7.80) and NO DECISION HERE MAY
    KEY ON THEM — run-2's `budget.json` bar `no_permission_may_key_on_agent_type` is binding: the
    field is a SENSOR OBSERVATION of a descriptor's claim, never an authorization.

    ⚠ MEASURED CAVEAT: `snap["roster_absent"]` has NEVER been observed non-empty in run-2 (live
    snapshot 2026-07-28 22:50 → `[]`). This candidate set is verified by CODE READING, not by a
    live positive; task s4-10's acceptance (a) is the first thing that produces one.

    Debounce is 2 consecutive non-stale ticks, and the number is CHOSEN, NOT MEASURED — no
    crash-to-detection latency data exists in this run. At the LIVE loop's `--loop 10` (the flag is
    declared with NO `default=`; the 10 is the running invocation's, recorded in the heartbeat as
    `loop_min: 10` — never call it "the default") worst-case detection is ~20 MIN PLUS ONE SENSOR
    CADENCE. That is named in the report line rather than hidden. Firing on ONE tick would make a
    single transient sensor error a relaunch. Whether ~20 min is acceptable for a leader outage is
    an OWNER QUESTION, UNASKED — do not answer it by editing `--loop` here.

    Every disposition prints a line EVERY tick: a hole must never go quiet."""
    # ---- 0. No snapshot at all → SILENT. Every package without team-monitor lands here. ----
    if snap is None and _snapshot_absent(snap_err):
        return []

    room = state.setdefault("_revival_room", {})   # room-level, not a seat: nothing in this module
    lines = []                                     # iterates `state` as a seat map (verified).

    # ---- 1. SENSOR STALENESS PAUSES ENFORCEMENT (CMP-21 invariant 2) ----
    # A stale snapshot is evidence in NEITHER direction, so the debounce counters are FROZEN —
    # neither incremented nor reset. `snap_err` with the file PRESENT (unreadable) is stale too,
    # never absence: the distinction check_budget's LOUD/SILENT split exists to preserve.
    age = None
    if isinstance(snap, dict) and snap.get("captured_at") is not None:
        try:
            age = time.time() - float(snap["captured_at"])
        except (TypeError, ValueError):
            age = None
    if snap is None or age is None or age > budget_mod.STALE_AFTER_S:
        room["stale_ticks"] = int(room.get("stale_ticks", 0)) + 1
        why = snap_err or (f"snapshot age {int(age)}s > {budget_mod.STALE_AFTER_S}s"
                           if age is not None else "snapshot carries no captured_at")
        lines.append(f"{'revival':<18} {'PAUSED':<7} {REVIVAL_STALE_LINE} — {why}")
        if room["stale_ticks"] >= REVIVAL_STALE_NOTE_TICKS and not room.get("notified_stale"):
            notes.append(Flag(None,
                f"watch: REVIVAL PAUSED — the seat-down detector has had no usable state.json "
                f"snapshot for {room['stale_ticks']} consecutive passes ({why}). The SENSOR is the "
                f"incident: while it is stale nothing can tell a crashed seat from a thinking one, "
                f"so the detector takes no action in either direction and its debounce counters "
                f"are frozen. Silence from this check is not a green."))
            room["notified_stale"] = True
        return lines
    room["stale_ticks"] = 0
    room.pop("notified_stale", None)

    # ---- 2. ROOM-DEAD short-circuits: no per-seat classification at all ----
    # Every seat is absent when the tmux session is gone; classifying them one by one would report
    # N crashes for ONE incident, and the recovery owner is a different mechanism entirely. Two
    # mechanisms that can disagree about whether a room is dead and both act is not redundancy.
    if snap.get("session_alive") is False:
        lines.append(REVIVAL_ROOM_DEAD_LINE)
        return lines

    absent = snap.get("roster_absent")
    absent = absent if isinstance(absent, list) else []

    # ---- 3. Clear the debounce EXPLICITLY on liveness == "live" ----
    # ⚠ THE EXISTING `if st.get("pane") != pane` RESET IS NOT ENOUGH, and relying on it is the bug:
    # an IN-PLACE RESPAWN (`tmux respawn-pane -k`, coord.renew_in_place) keeps the SAME pane id, so
    # a pane-keyed reset never fires and a stale gone_ticks would survive into a healthy seat.
    for s in snap.get("seats") or []:
        if s.get("liveness") == "live" and s.get("seat"):
            st = state.get(s["seat"])
            if isinstance(st, dict) and st.get("revival"):
                st.pop("revival", None)

    if not absent:
        lines.append(f"{'revival':<18} {'ok':<7} no roster-absent seat")
        return lines

    # LIVE roster, re-read now: the CLEANLY-OUT predicate must read the roster as it stands at
    # classification time, not as the snapshot saw it up to one sensor cadence ago.
    _, _, live_rows = coord.load_workers(base)
    roster = {r["agent"]: r for r in live_rows}

    closing, closing_st = _strict_ledger(coord.closing_path(base))
    awaiting, awaiting_st = _strict_ledger(coord.awaiting_path(base))
    # Stage 3's marker. Its READER is Stage 3's to ship (cross-prefix dep s3-03); until it lands an
    # ABSENT marker file is "no entry", which is the correct reading, not a workaround.
    marker, marker_st = _strict_ledger(base / "lifecycle-inflight.json")

    bad = [n for n, s in (("closing.json", closing_st), ("awaiting-close.json", awaiting_st),
                          ("lifecycle-inflight.json", marker_st)) if s == "unparseable"]

    for row in absent:
        seat = (row.get("seat") or "").strip()
        if not seat:
            continue
        st = state.setdefault(seat, {"pane": row.get("pane")})
        rev = st.get("revival") or {"gone_ticks": 0, "pane": row.get("pane")}
        if rev.get("pane") != row.get("pane"):
            rev = {"gone_ticks": 0, "pane": row.get("pane")}

        # IDLE — unreachable BY CONSTRUCTION: a live harness never enters roster_absent. Asserted
        # loudly rather than branched on, and NOT via `assert` (stripped under -O, and a monitor
        # must never die of its own bookkeeping). If this ever prints, the sensor's conjunction and
        # this reader disagree, and every classification below is untrustworthy.
        if row.get("liveness") == "live":
            lines.append(f"{seat:<18} {'BROKEN':<7} REVIVAL INVARIANT BROKEN — a `live` row in "
                         f"roster_absent; classification refused")
            if not room.get("notified_invariant"):
                notes.append(Flag(seat,
                    f"watch: REVIVAL DETECTOR INVARIANT BROKEN — '{seat}' appears in state.json's "
                    f"roster_absent with liveness 'live', which team_monitor.absent_rows cannot "
                    f"produce. The detector refuses to classify it. Treat the SENSOR as the "
                    f"incident, not the seat."))
                room["notified_invariant"] = True
            st["revival"] = rev
            continue

        # (1) ROOM-DEAD handled above, before the candidate walk.

        # (2) CLEANLY-OUT — never a candidate. `cmd_checkout` records the pane as a debt that never
        # expires BY DESIGN; a checked-out seat is not a crash.
        r = roster.get(seat)
        if seat in awaiting or (r is not None and r.get("active") != "yes"):
            lines.append(f"{seat:<18} {'REVIVAL':<7} CLEANLY-OUT — "
                         f"{'in awaiting-close.json' if seat in awaiting else 'roster row not active'}")
            rev["gone_ticks"] = 0
            st["revival"] = rev
            continue

        # (3) s4-04: COMPLETED-ONE-SHOT gate goes here, BEFORE CRASHED.
        #     D-3C (stage-4-revival-spec.md § Deltas accepted from topic 3). A normally-completed
        #     opencode one-shot appears in roster_absent BYTE-IDENTICALLY to a crashed claude seat,
        #     so without this gate a correct detector resurrects every finished one-shot forever.
        #     The gate keys on the descriptor's `mode:`, NEVER on `harness:`. NOT IMPLEMENTED HERE.

        # (4) MID-RENEWAL — the marker's executor is a LIVE PYTHON process (plain pid+starttime),
        # or the seat is mid-close. Never fires today: Stage 3's executor is unbuilt.
        entry = marker.get(seat) if isinstance(marker.get(seat), dict) else None
        if (entry is not None and entry.get("state") == "in-flight"
                and _executor_ident_live(entry)) or seat in closing:
            lines.append(f"{seat:<18} {'REVIVAL':<7} MID-RENEWAL — "
                         f"{'lifecycle executor in-flight and alive' if entry else 'in closing.json'}")
            rev["gone_ticks"] = 0
            st["revival"] = rev
            continue

        # Ledger unreadable → REFUSE TO FIRE, and FREEZE (a ledger we cannot read is evidence in
        # neither direction, exactly like a stale snapshot). Reported EVERY tick; noted ONCE.
        # ⚠ R-8: the refusal names its LAYER. This is the DETECTOR's own refusal — a tool gate —
        # not a harness permission classifier refusing a command.
        if bad:
            lines.append(f"{seat:<18} {'REFUSED':<7} REVIVAL REFUSED — revival detector gate: "
                         f"ledger unparseable ({', '.join(bad)}); cannot rule out a clean exit")
            if not room.get("notified_ledger"):
                notes.append(Flag(seat,
                    f"watch: REVIVAL DETECTOR REFUSED — revival detector gate: {', '.join(bad)} "
                    f"under {base} is present but unparseable, so a seat that checked out cleanly "
                    f"is indistinguishable from a crashed one. '{seat}' is roster-absent and will "
                    f"NOT be classified while that is true. Fix or remove the file. (This is the "
                    f"detector refusing, not the harness permission classifier.)"))
                room["notified_ledger"] = True
            st["revival"] = rev
            continue

        # (5) CRASHED — in roster_absent, none of the above, debounce satisfied.
        rev["gone_ticks"] = int(rev.get("gone_ticks", 0)) + 1
        if rev["gone_ticks"] >= REVIVAL_DEBOUNCE_TICKS:
            lines.append(f"{seat:<18} {'REVIVAL':<7} CRASHED — would revive "
                         f"(pane {row.get('pane')}, {row.get('liveness')}; report-only, s4-05/s4-06 "
                         f"own the claim and the fire)")
        else:
            lines.append(f"{seat:<18} {'REVIVAL':<7} CRASHED pending — "
                         f"{rev['gone_ticks']}/{REVIVAL_DEBOUNCE_TICKS} consecutive non-stale ticks "
                         f"(~20 min worst case at the live loop's --loop 10, plus one sensor cadence)")
        st["revival"] = rev

    return lines


def check_leftover_windows(rows, seats, sysstate, notes):
    """PROP-10 — a briefing-declared window whose panes are ALL agent-dead: no ACTIVE roster
    seat's pane is in it. Covers both halves of the incident: a closed wave leaving bash-only
    shells, AND a wave whose seats died at model-init before ever checking in (which is also
    the runtime residue PROP-8's pre-flight cannot catch locally). Keyed to windows the
    briefings declare (`window: NAME`, or the agent's own name for `window: yes`), so the
    control panel and unrelated tmux windows never false-fire. Flags once per window; re-arms
    when the window disappears or an active seat (re)appears in it. Returns report lines."""
    declared = set()
    for s in seats.values():
        w = s.get("window")
        if w == "yes":
            declared.add(s["agent"])
        elif w:
            declared.add(w)
    if not declared:
        sysstate.pop("windows", None)
        return []
    wins = window_panes()
    if not wins:  # tmux unavailable/unreadable — unmeasurable, leave the armed state untouched
        return []
    active_panes = {r["pane"] for r in rows if r["active"] == "yes" and r["pane"]}
    prior = sysstate.get("windows", {})
    leftover, lines = {}, []
    for full, panes in sorted(wins.items()):
        name = full.split(":", 1)[1] if ":" in full else full
        if name not in declared or not panes:
            continue
        if any(p in active_panes for p in panes):
            continue
        lines.append(f"{name:<18} LEFTOVER window '{full}': {len(panes)} pane(s), no active seat")
        leftover[full] = True
        if not prior.get(full):
            notes.append(
                f"watch: window '{full}' still holds {len(panes)} pane(s) but NO active seat — "
                f"either its wave closed leaving dead shells, or its seats died before checkin "
                f"(a config error kills a seat at model-init, before it ever registers). Inspect "
                f"it, then tear the whole window down: tmux kill-window -t '{full}' — the "
                f"sanctioned teardown: an interactive bash ignores SIGTERM, and kill-pane is "
                f"blocked by the harness automation classifier.")
    if leftover:
        sysstate["windows"] = leftover
    else:
        sysstate.pop("windows", None)
    return lines


# ---------- one pass ----------

def run_pass(args):
    base = coord.base_dir(args)
    _, _, rows = coord.load_workers(base)
    seats = {w["agent"]: w for w in coord.discover_workers(coord.workers_dir(args))}
    # G-176: seats whose pane is a DOOR to a human role. Read from coord.inbox_decls, which is the
    # ONE home of the `relays:` derivation and already backs the reap exemption (rbtv 6b25104) —
    # NOT re-parsed here and NOT added to discover_workers, either of which would give one fact a
    # second home to drift in (that is G-159, which this seat fixed an hour before writing this).
    door_seats = {a for a, d in (coord.inbox_decls(args) or {}).items() if d.get("relays")}
    state = load_state(base)
    live = live_panes()
    nnow = now_dt()
    report, notes = [], []

    # PROP-9/PROP-10: box-level duties run FIRST — pressure explains per-seat symptoms, and a
    # leftover dead window is invisible to the per-seat loop (its seats have no active row).
    sysstate = load_sys_state(base)
    sysline = check_system(args, sysstate, notes)
    # ONE state.json snapshot, taken now and reused by both check_budget below and check_revival
    # (s4-03) — the single reading s4-02 hoists so a second consumer never gets a second load of
    # the same fact. THE RUN ROOT, NOT `base` — see the hazard note inside check_budget.
    snap, snap_err = budget_mod._load(str(base.parent / "state.json"), "state.json")
    # Room capacity is box-level too. Read the PREVIOUS heartbeat before this pass overwrites it —
    # the re-arm comparison needs the prior breach state, and save_heartbeat rewrites the file whole.
    budgetline, budget_state = check_budget(base, notes, load_heartbeat(base), snap, snap_err)
    # G-188 push half: the daemon is box-level, not a seat, so it runs here with the other
    # box duties. ONE reading, taken now and reused by save_heartbeat at the end of the pass.
    daemon, daemon_change = daemon_reading(base)
    # G-188 stage 3: the workspace root is RESOLVED by coord's own rbtv.json walk-up, never a
    # literal — this kit is shared, and the daemon's root is carried in the marker itself. A
    # workspace with no rbtv.json yields None, and the verdict is then UNKNOWN, said out loud.
    ws_root, _ = coord.find_workspace_root(base)
    daemon_code = daemon_code_state(ws_root, daemon) if ws_root else (
        "unknown", "no rbtv.json above the run package, so the daemon marker cannot be located")
    daemonline = check_daemon(sysstate, daemon, daemon_change, notes, daemon_code)
    leftover_lines = check_leftover_windows(rows, seats, sysstate, notes)

    # PROP-11 (leader ruling 2026-07-27, msg #125): reconcile every roster-ACTIVE row against the
    # PROCESS TABLE. Nothing did, and it is the common half of five defects in one night — a row
    # said ACTIVE while its pane held only a shell, twice on the same seat. It belongs HERE, in the
    # detached loop, and in no agent: this loop was the only thing that survived tonight, still
    # stamping heartbeats while the agent whose job was to watch had died of the very gap it had
    # named. An agent that must remember to look IS vigilance; prevention has to be structural.
    # NOTIFY ONLY — the loop never closes, kills, or relaunches anything (leader keeps lifecycle).
    # The WATCHER'S OWN ROW is checked too, and it is the only check applied to it: watch.py
    # outlives the watcher agent, so it is the one thing positioned to report that death.
    for r in rows:
        if r["active"] != "yes":
            continue
        agent, pane = r["agent"], r["pane"]
        if pane and pane in live:
            hp, verifiable = coord.pane_harness_pids(pane)
            st = state.get(agent, {})
            if st.get("pane") != pane:
                st = {"pane": pane}
            if verifiable and not hp:
                report.append(f"{agent:<18} GHOSTROW pane {pane} has no harness process")
                if not st.get("notified_ghostrow"):
                    notes.append(Flag(agent,
                        f"watch: '{agent}' is ACTIVE in the roster but pane {pane} runs NO "
                        f"harness process — the row claims a seat that is not there. Its work is "
                        f"stopped and every wake sent to it is typed into a bare shell. Inspect "
                        f"(tmux capture-pane -p -t {pane}), then either relaunch or close it: "
                        f"{coord.coord_invocation(args)} close-seat {agent} --renew"))
                    st["notified_ghostrow"] = True
            elif hp:
                st.pop("notified_ghostrow", None)
            state[agent] = st

    # Stage 4 §1 (s4-03), REPORT-ONLY: classify every roster-absent seat. A SNAPSHOT-LEVEL duty, so
    # it sits here with the other snapshot consumers and NOT inside the per-seat loop — its
    # candidate set (`snap["roster_absent"]`) is strictly broader than either loop around it: the
    # ghostrow loop above visits only panes present in `live`, and the flag loop below skips
    # `watcher`. It consumes the ONE hoisted state.json reading (s4-02), never a second load.
    # ⚠ its lines are kept OUT of `report`, like `leftover_lines`: the pass header counts `report`
    # as "N active seat(s)", and a revival line is not a seat row — folding them in would corrupt
    # a number every reader trusts.
    revival_lines = check_revival(args, base, snap, snap_err, state, notes)

    for r in rows:
        if r["active"] != "yes" or r["agent"] == "watcher":
            continue
        agent, pane = r["agent"], r["pane"]
        st = state.get(agent, {})
        if st.get("pane") != pane:
            st = {"pane": pane}  # new/renewed seat: re-arm every notification
        seat = seats.get(agent, {})
        harness = seat.get("harness", "claude")

        # liveness
        if pane and live and pane not in live:
            report.append(f"{agent:<18} DEAD    pane {pane} gone")
            if not st.get("notified_dead"):
                notes.append(Flag(agent, f"watch: '{agent}' is ACTIVE in the roster but its pane {pane} is gone "
                             f"— wakes cannot reach it. Mark it closed ({coord.coord_invocation(args)} "
                             f"close-seat {agent} --no-export) or relaunch it."))
                st["notified_dead"] = True
            state[agent] = st
            continue

        # activity (content hash of the visible tail)
        tail = pane_tail(pane) if pane else None
        inact_min = None
        if tail is not None:
            h = hashlib.sha1(tail.encode("utf-8", "replace")).hexdigest()
            if st.get("hash") != h:
                st["hash"] = h
                st["stable_since"] = nnow.isoformat(timespec="seconds")
                st.pop("notified_inactive", None)  # activity resumed -> re-arm
            since = st.get("stable_since")
            if since:
                inact_min = int((nnow - datetime.fromisoformat(since)).total_seconds() // 60)

        # context (claude seats only)
        pct = None
        if harness == "claude":
            t = find_transcript(agent, seat.get("cwd", coord.VAULT_ROOT),
                                getattr(args, "claude_projects_dir", None))
            if t is None and pane:
                fb_cwd = pane_cwd(pane)
                if fb_cwd:
                    t = find_transcript_by_path_fragment(agent, fb_cwd,
                                                         getattr(args, "claude_projects_dir", None))
            if t:
                _, pct = transcript_usage(t)

        flags = []
        # P38: an approval gate is checked BEFORE inactivity, because it explains inactivity. A
        # gated pane is frozen, so its content hash never changes and it would eventually trip
        # INACTIVE — 30 minutes after the seat actually stopped, with a hint ("check on it, close
        # it, or renew it") that is wrong for a seat waiting on one keypress. Re-arms when the
        # title clears, like every other flag.
        if at_approval_gate(pane):
            flags.append("APPROVAL")
            if not st.get("notified_approval"):
                notes.append(Flag(agent, f"watch: '{agent}' ({harness}) is parked on an interactive approval "
                             f"prompt — its pane is frozen until someone answers it, and a wake "
                             f"typed into it would land in the modal. Inspect it "
                             f"(tmux capture-pane -p -t {pane}) and clear it: "
                             f"{coord.coord_invocation(args)} approve {agent}"))
                st["notified_approval"] = True
        else:
            st.pop("notified_approval", None)
        if inact_min is not None and inact_min >= args.inactive_min:
            flags.append(f"INACTIVE {inact_min}min")
            if not st.get("notified_inactive"):
                # G-176: the remedy above coaches `close`, and on ONE class of seat that is an act a
                # standing owner ruling FORBIDS. A seat declaring `relays:` carries the relay path to
                # a human role, so its pane is a DOOR — the spot a human watches while away — and it
                # is never closed or reaped mechanically (r-owner-afk-liaison-parked). At 23:58 this
                # flag fired on the live owner door and recommended exactly that; the chief-of-staff
                # refused and routed it up, which is the only reason it cost nothing.
                #
                # ⚠ THE FLAG IS NOT SUPPRESSED, AND THE EVENING PROVED WHY RATHER THAN THE PRINCIPLE
                # ALONE. The first draft of this text reassured the reader — "idle is expected while
                # the human is away, so this is not evidence of a fault". THAT REASSURANCE WOULD HAVE
                # BEEN WRONG THE NIGHT IT WAS WRITTEN: the door flagged here had been silent since
                # 23:01 (verified by PARSING the transcript — its mtime lied, showing a write with no
                # new content) and its pane was GONE by ~23:58. A door waiting quietly for its human
                # and a door in trouble are INDISTINGUISHABLE FROM OUTSIDE, so this text must not
                # talk anyone out of looking. Suppressing the flag would have muted the last warning
                # before the door died.
                #
                # So: the flag stays, the REMEDY becomes true, and the text asserts the ambiguity
                # instead of resolving it. What is NOT solved is a general notion of
                # legitimately-idle (7.32/7.33's flag set); this closes the one class where the
                # generic advice is actively DESTRUCTIVE.
                if agent in door_seats:
                    notes.append(Flag(agent, f"watch: '{agent}' has shown no pane activity for {inact_min} min "
                                 f"(threshold {args.inactive_min}) — and it declares `relays:`, so its pane is a "
                                 f"DOOR to a human role, not a worker that has stalled. ⚠ THIS FLAG CANNOT TELL A "
                                 f"DOOR WAITING QUIETLY FOR ITS HUMAN FROM A DOOR IN TROUBLE — they look identical "
                                 f"from outside, and on 2026-07-27 a door flagged after 37 min of silence was GONE "
                                 f"twenty minutes later. So LOOK, do not assume either way: "
                                 f"`tmux capture-pane -p -t {pane}`. ⚠ AND DO NOT close, renew or reap it — that is "
                                 f"forbidden on a door (r-owner-afk-liaison-parked) and it is how a run severs the "
                                 f"channel it is reachable through. If it needs action, that is the leader's "
                                 f"judgment, never a mechanical response to this flag."))
                else:
                    notes.append(Flag(agent, f"watch: '{agent}' has shown no pane activity for {inact_min} min "
                                 f"(threshold {args.inactive_min}). Check on it; if hung or done-but-"
                                 f"stuck, close it — or renew: {coord.coord_invocation(args)} close {agent} --renew"))
                st["notified_inactive"] = True
        # A seat may declare its OWN refresh threshold in its briefing (`ctx-refresh: 60`) — a
        # cheap ephemeral seat and a long-lived builder do not want the same one. The watcher's
        # --context-pct is the fallback for every seat that declares none.
        seat_pct = seat.get("ctx_refresh")
        threshold = seat_pct if seat_pct else args.context_pct
        if pct is not None and pct >= threshold:
            flags.append(f"CONTEXT {pct}%")
            if not st.get("notified_context"):
                source = " from its briefing ctx-refresh" if seat_pct else ""
                notes.append(Flag(agent, f"watch: '{agent}' context is at {pct}% (threshold {threshold}%"
                             f"{source}). Have the closer close and RENEW it now: "
                             f"{coord.coord_invocation(args)} close {agent} --renew "
                             f"(memory.md gets written, the seat relaunches fresh)."))
                st["notified_context"] = True

        ctx = f" ctx={pct}%" if pct is not None else ""
        act = f" idle={inact_min}min" if inact_min is not None else ""
        report.append(f"{agent:<18} {'FLAG' if flags else 'ok':<7} {harness:<9}{ctx}{act}"
                      f"  {' '.join(flags)}")
        state[agent] = st

    save_state(base, state)
    save_sys_state(base, sysstate)
    save_heartbeat(base, getattr(args, "loop", None), daemon, daemon_change, daemon_code,
                   budget_state)
    stamp = nnow.strftime("%Y-%m-%d %H:%M")
    print(f"watch pass {stamp} — {len(report)} active seat(s), {len(notes)} new flag(s)")
    if sysline:
        print("  " + sysline)
    if daemonline:
        print("  " + daemonline)
    if budgetline:
        print("  " + budgetline)
    for line in report:
        print("  " + line)
    for line in leftover_lines:
        print("  " + line)
    for line in revival_lines:
        print("  " + line)
    if args.notify:
        for text in notes:
            notify_leader(args, text)
    elif notes:
        print("(dry: --notify not set — flags NOT sent to leader)")
        for text in notes:
            print("  would send: " + text[:120])
    return notes


def cmd_selftest():
    import tempfile
    failures = []

    def check(name, cond):
        print(("ok  " if cond else "FAIL") + f"  {name}")
        if not cond:
            failures.append(name)

    global pane_tail, live_panes, pane_cwd, system_pressure, window_panes
    coord.wake = lambda pane, text: (False, "stub")
    # coord's identity resolution (T1) reads the calling pane: stub it, or a selftest run from
    # inside a tmux pane would talk to the real server and could inherit a live seat's identity.
    coord.detect_pane = lambda override=None: (override or "")
    # coord functions cmd_checkin/cmd_checkout shell out to on this suite's behalf — unstubbed,
    # the selftest CRASHED on a box without tmux on PATH (FileNotFoundError from set_pane_title,
    # observed 2026-07-26 on Windows), despite the kit's promise that selftests need no tmux.
    coord.set_pane_title = lambda pane, title: None
    coord.live_panes = lambda: set()
    coord_env_agent = os.environ.pop("COORD_AGENT", None)

    # PROP-9/PROP-10: the real readers must be GRACEFUL wherever they run — a box without /proc
    # or tmux gets None/{} back, never a raise. Exercised for real BEFORE the stubs go in.
    real_sp = system_pressure()
    check("PROP-9: real system_pressure() returns a reading or None, never raises "
          "(graceful on a box without /proc)",
          real_sp is None or {"avail_mb", "load1", "cores"} <= set(real_sp))
    check("PROP-10: real window_panes() returns a dict, never raises (graceful without tmux)",
          isinstance(window_panes(), dict))

    tails = {}
    pane_tail = lambda pane: tails.get(pane)
    live_panes = lambda: {"%1", "%2", "%3", "%4", "%5", "%6", "%7", "%40", "%41"}
    sys_reading = {"v": {"avail_mb": 4000, "load1": 0.4, "cores": 4}}
    system_pressure = lambda: sys_reading["v"]
    win_map = {}
    window_panes = lambda: dict(win_map)
    pane_cwds = {}
    pane_cwd = lambda pane: pane_cwds.get(pane)
    # P38: the approval predicate reads the pane TITLE through coord — stub it there, so this
    # selftest exercises the SAME function `coordinate send` calls (8(b)), not a local copy.
    pane_titles = {}
    coord.pane_title = lambda pane: pane_titles.get(pane, "")
    # PROP-11 reads the PROCESS TABLE through coord. Unstubbed, this suite would judge fixture pane
    # ids against whatever runs on the tester's box — and pane "%1" exists on the box this was
    # written on. None = unverifiable (the fail-safe default), {} entries set per check.
    pane_harness = {}
    coord.pane_harness_pids = lambda pane: (([], False) if pane_harness.get(pane) is None
                                            else (list(pane_harness[pane]), True))
    # Every coord call below resolves a package, and resolving a package REGISTERS its folder
    # name as a run tag. Unredirected, this selftest wrote a `pkg` tag pointing at its own temp
    # directory into the owner's real ~/.config/rbtv/coordinate-runs.json — a test that mutates
    # the machine it runs on. coord's own selftest already redirects the registry; do the same
    # here, and prove it by comparing the real file byte-for-byte before and after.
    real_runs_index = coord.RUNS_INDEX
    try:
        real_runs_before = real_runs_index.read_bytes()
    except OSError:
        real_runs_before = None

    with tempfile.TemporaryDirectory() as td:
        coord.RUNS_INDEX = Path(td) / "coordinate-runs.json"
        pkg = Path(td) / "pkg"
        (pkg / "coordination").mkdir(parents=True)
        wdir = pkg / "workers"
        (wdir / "alpha").mkdir(parents=True)
        (wdir / "alpha" / "agent.md").write_text("---\nagent: alpha\nharness: claude\ncwd: /w/one\n---\nb\n")
        (wdir / "gamma").mkdir(parents=True)
        (wdir / "gamma" / "agent.md").write_text("---\nagent: gamma\nharness: opencode\nmodel: m/x\n---\nb\n")
        # leader exists as a briefing so the watcher's `send leader` passes coord's recipient
        # validation before leader has checked in (a watcher can flag a seat that early).
        (wdir / "leader").mkdir(parents=True)
        (wdir / "leader" / "agent.md").write_text("---\nagent: leader\nharness: claude\n---\nb\n")
        # per-seat ctx-refresh: epsilon tolerates more context than the watcher default,
        # zeta less. Both sit at the same measured 57%.
        (wdir / "epsilon").mkdir(parents=True)
        (wdir / "epsilon" / "agent.md").write_text(
            "---\nagent: epsilon\nharness: claude\ncwd: /w/one\nctx-refresh: 90\n---\nb\n")
        (wdir / "zeta").mkdir(parents=True)
        (wdir / "zeta" / "agent.md").write_text(
            "---\nagent: zeta\nharness: claude\ncwd: /w/one\nctx-refresh: 40\n---\nb\n")
        # G-176: a DOOR — a seat declaring `relays:`, so its pane carries the relay path to a human
        # role. Identical to the others in every other respect, which is the point: only the
        # declaration may change the remedy.
        (wdir / "door").mkdir(parents=True)
        (wdir / "door" / "agent.md").write_text(
            "---\nagent: door\nharness: claude\nrelays: master\n---\nb\n")

        # fake claude projects dir with a matching transcript at 57% of a 1M window
        proj = Path(td) / "projects" / munge_cwd("/w/one")
        proj.mkdir(parents=True)
        tr = proj / "s1.jsonl"
        tr.write_text(
            json.dumps({"type": "user", "message": {"content": "You are agent 'alpha' of the run"}}) + "\n"
            + json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 100}}}) + "\n"
            + json.dumps({"type": "assistant", "isSidechain": True,
                          "message": {"usage": {"input_tokens": 999999}}}) + "\n"
            + json.dumps({"type": "assistant", "message": {"usage": {
                "input_tokens": 200000, "cache_read_input_tokens": 350000,
                "cache_creation_input_tokens": 20000}}}) + "\n")

        def ns(**kw):
            d = {"package": str(pkg), "base": None, "workers_dir": None, "notify": True,
                 "inactive_min": 30, "context_pct": 50, "mem_floor_mb": 500,
                 "load_per_core": 1.0, "claude_projects_dir": str(Path(td) / "projects")}
            d.update(kw)
            return argparse.Namespace(**d)

        check("transcript: boot-prompt match finds the file",
              find_transcript("alpha", "/w/one", str(Path(td) / "projects")) == tr)
        check("transcript: no match for unknown agent",
              find_transcript("zeta", "/w/one", str(Path(td) / "projects")) is None)
        toks, pct = transcript_usage(tr)
        check("context: last main-chain assistant wins, sidechain ignored",
              toks == 570000 and pct == 57.0)

        # fallback: a hand-started seat (e.g. leader) never carries the standard boot-prompt
        # phrasing. Its recorded frontmatter cwd is deliberately WRONG here — only the seat's
        # LIVE pane cwd (tmux #{pane_current_path}, stubbed via pane_cwd below) carries a
        # transcript whose first user text references its own workers/<agent>/ fragment.
        (wdir / "beta").mkdir(parents=True)
        (wdir / "beta" / "agent.md").write_text("---\nagent: beta\nharness: claude\ncwd: /w/wrong\n---\nb\n")
        (wdir / "delta").mkdir(parents=True)
        (wdir / "delta" / "agent.md").write_text("---\nagent: delta\nharness: claude\ncwd: /w/wrong\n---\nb\n")

        beta_proj = Path(td) / "projects" / munge_cwd("/w/real-beta")
        beta_proj.mkdir(parents=True)
        beta_tr = beta_proj / "s1.jsonl"
        beta_tr.write_text(
            json.dumps({"type": "user", "message": {"content": "execute workers/beta/agent.md"}}) + "\n"
            + json.dumps({"type": "assistant", "message": {"usage": {
                "input_tokens": 100000, "cache_read_input_tokens": 250000,
                "cache_creation_input_tokens": 30000}}}) + "\n")

        check("fallback: boot-prompt match fails for a hand-started seat (recorded cwd)",
              find_transcript("beta", "/w/wrong", str(Path(td) / "projects")) is None)
        check("fallback: path-fragment match finds the transcript via the pane's live cwd",
              find_transcript_by_path_fragment("beta", "/w/real-beta", str(Path(td) / "projects")) == beta_tr)
        check("fallback: no match for an unrelated agent even in the right directory",
              find_transcript_by_path_fragment("zeta", "/w/real-beta", str(Path(td) / "projects")) is None)

        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="alpha", summary="w", pane="%1"))
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="gamma", summary="w", pane="%2"))
        tails["%1"] = "one"
        tails["%2"] = "two"

        notes = run_pass(ns())
        check("pass 1: context flag fires for the claude seat (57% >= 50%)",
              any("alpha" in n and "57" in n for n in notes))
        check("pass 1: opencode seat gets no context flag", not any("gamma" in n and "%" in n for n in notes))
        notes = run_pass(ns())
        check("pass 2: context flag does NOT re-fire (armed once per seat/pane)",
              not any("context is at" in n for n in notes))

        # age alpha's stability timestamp -> inactivity fires; gamma changes -> no flag
        base = pkg / "coordination"
        st = load_state(base)
        st["alpha"]["stable_since"] = "2000-01-01T00:00:00"
        save_state(base, st)
        tails["%2"] = "two CHANGED"
        notes = run_pass(ns())
        check("inactivity: stale pane flagged with close --renew hint",
              any("alpha" in n and "no pane activity" in n for n in notes))
        check("inactivity: changed pane not flagged", not any("gamma" in n for n in notes))
        notes = run_pass(ns())
        check("inactivity: does not re-fire while still stale",
              not any("no pane activity" in n for n in notes))
        tails["%1"] = "one CHANGED"
        run_pass(ns())  # activity resumes -> re-arms
        st = load_state(base)
        st["alpha"]["stable_since"] = "2000-01-01T00:00:00"
        save_state(base, st)
        notes = run_pass(ns())
        check("inactivity: re-fires after activity resumed and went stale again",
              any("alpha" in n and "no pane activity" in n for n in notes))
        # Captured from a REAL firing above, so the G-176 control below compares against an
        # ordinary seat's actual remedy rather than a re-derived expectation.
        alpha_note = next((n for n in notes if "alpha" in n and "no pane activity" in n), "")

        # ---- G-176: the remedy on a DOOR must not coach the act a ruling forbids ----
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="door", summary="w", pane="%3"))
        tails["%3"] = "door idle"
        run_pass(ns())
        st = load_state(base)
        st["door"]["stable_since"] = "2000-01-01T00:00:00"
        save_state(base, st)
        notes = run_pass(ns())
        door_note = next((n for n in notes if "door" in n and "no pane activity" in n), "")
        check("G-176: a DOOR still FLAGS when idle — the fix makes the remedy true, it does not "
              "silence the loop. A door that genuinely hangs is the last seat a run can afford to "
              "go unreported, so suppressing it here would make the re-mute the fix's own failure mode",
              bool(door_note))
        # ⚠ ASSERTS THE ABSENT COMMAND, NOT ABSENT WORDS. The first draft of this check forbade the
        # substrings "close"/"reap" and FAILED ON CORRECT CODE, because the door remedy says "DO NOT
        # close, renew or reap it" — a false RED produced by testing vocabulary instead of the
        # property. What is forbidden is the runnable coaching: an invocation the reader can paste.
        check("G-176: the door's remedy NEVER hands the reader a close/renew INVOCATION — at 23:58 "
              "this flag fired on the live owner door and did exactly that "
              "(r-owner-afk-liaison-parked forbids it); a flag advising the severing of the channel "
              "the run is reachable through is worse than no flag",
              bool(door_note) and "close door" not in door_note and "--renew" not in door_note)
        check("G-176: the door's remedy says DOOR and tells the reader to LOOK, not act",
              "DOOR" in door_note and "capture-pane" in door_note)
        # The first draft reassured — "idle is expected, not evidence of a fault". It would have
        # been WRONG the night it was written: that door had been silent since 23:01 and its pane
        # was gone by ~23:58. A remedy that talks a reader out of looking at a dying door is a
        # second way to lose it, so the text must assert the ambiguity, never resolve it.
        check("G-176: the door's remedy does NOT reassure — it states that a quiet door and a "
              "failing door are indistinguishable from outside, because on the night this was "
              "written the door flagged here was gone twenty minutes later",
              "CANNOT TELL" in door_note and "not evidence of a fault" not in door_note)
        check("G-176 CONTROL: an ORDINARY seat's remedy is UNCHANGED and still carries the close "
              "--renew invocation — the door text is scoped by the `relays:` declaration, so this "
              "check is what separates a scoped fix from a blanket rewrite of the remedy",
              "--renew" in alpha_note and "DOOR" not in alpha_note)

        # dead pane
        live_panes_backup = live_panes
        globals()["live_panes"] = lambda: {"%2"}
        notes = run_pass(ns())
        check("dead pane: flagged once with close-seat hint",
              any("alpha" in n and "pane %1 is gone" in n for n in notes))
        notes = run_pass(ns())
        check("dead pane: does not re-fire", not any("pane %1 is gone" in n for n in notes))
        globals()["live_panes"] = live_panes_backup

        # fallback, end to end: beta (pane-cwd fallback resolves) vs delta (neither path
        # resolves, no transcript anywhere) — run through run_pass exactly like a live pass.
        pane_cwds["%3"] = "/w/real-beta"
        pane_cwds["%4"] = "/w/nowhere-real"
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="beta", summary="w", pane="%3"))
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="delta", summary="w", pane="%4"))
        tails["%3"] = "beta-tail"
        tails["%4"] = "delta-tail"

        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            run_pass(ns())
        printed_lines = buf.getvalue().splitlines()
        check("fallback (live pass): hand-started seat gets ctx= via the pane-cwd fallback",
              any(ln.strip().startswith("beta") and "ctx=" in ln for ln in printed_lines))
        check("fallback (live pass): seat with no match on either path stays unmeasured, no crash",
              any(ln.strip().startswith("delta") for ln in printed_lines)
              and not any(ln.strip().startswith("delta") and "ctx=" in ln for ln in printed_lines))

        raw = (base / "messages.md").read_text()
        # ⚠ THIS CHECK ASSERTED `type: ask` AND HAD BEEN FAILING SINCE THE ask->note FIX LANDED
        # (e5e55e5), whose message reports "0 failures". Measured on that commit, in this tree, on
        # two different invocations: FAIL (1 failure). The one check standing guard over delivery
        # was red while the delivery fix it belonged to shipped — the type moved and its assertion
        # did not follow. Corrected to the behaviour that is actually right, rather than deleted.
        check("notify: flags land in the coordination log as watcher->leader NOTES (never asks — "
              "an ask from an unaddressable sender can never be closed, S-7)",
              "from: watcher | to: leader | type: note" in raw
              and "from: watcher | to: leader | type: ask" not in raw)

        # ---- B: a flag is NEVER routed to the seat it is ABOUT ----
        # Pure-function first: exhaustive over the four cases, and DISCRIMINATING BY CONSTRUCTION —
        # on the pre-fix code the recipient was the literal string "leader" in every case, so every
        # non-leader expectation below fails without the routing layer.
        rec = lambda subj, to="chief-of-staff", fb="leader": flag_recipient(
            ns(notify_to=to, notify_fallback=fb), subj)
        check("B: a flag about an ORDINARY seat goes to the configured recipient",
              rec("beta") == ("chief-of-staff", False, False))
        check("B: a flag about the RECIPIENT ITSELF is diverted to the fallback — the structural "
              "hole: a warning about the leader was delivered to the leader, which holds its own "
              "close/renew/approve with no seat above it",
              rec("chief-of-staff") == ("leader", True, False))
        check("B: the rule is GENERAL, not a carve-out for one role — it diverts whichever seat "
              "is configured, so pointing flags at a new seat cannot move the hole to that seat",
              rec("leader", to="leader", fb="chief-of-staff") == ("chief-of-staff", True, False))
        check("B: a room-level flag (system pressure / leftover window) has no subject to divert "
              "and goes to the primary recipient",
              rec(None) == ("chief-of-staff", False, False))
        check("B: subject == primary == fallback is ORPHANED — no impartial recipient exists, so "
              "it is delivered anyway AND recorded, never quietly reported to its own subject",
              rec("leader", to="leader", fb="leader") == ("leader", False, True))
        check("B: defaults are unchanged for every run that configures nothing (leader, leader)",
              flag_recipient(ns(), "beta") == ("leader", False, False)
              and flag_recipient(ns(), "leader") == ("leader", False, True))
        check("B: a Flag CARRIES its subject rather than having it parsed back out of the "
              "rendered sentence (G-107: assert, never infer), and is still a plain str",
              Flag("beta", "watch: 'beta' x").subject == "beta"
              and Flag("beta", "watch: 'beta' x") == "watch: 'beta' x"
              and getattr("plain string", "subject", None) is None)

        # End-to-end through the REAL send path — the same function the loop calls, writing the
        # real coordination log. A pass count is not a result (G-121): this asserts the ADDRESS on
        # the delivered message, which is the whole of what B changes.
        notify_leader(ns(notify_to="alpha"), Flag("beta", "watch: 'beta' end-to-end routing probe"))
        notify_leader(ns(notify_to="alpha"), Flag("alpha", "watch: 'alpha' end-to-end divert probe"))
        raw2 = (base / "messages.md").read_text()
        check("B (end-to-end): a flag about 'beta' is ADDRESSED to the configured recipient "
              "'alpha' in the real log — pre-fix every flag was addressed to leader",
              "from: watcher | to: alpha | type: note" in raw2
              and "end-to-end routing probe" in raw2)
        check("B (end-to-end): a flag ABOUT 'alpha' is addressed to the FALLBACK instead, and the "
              "body says why it arrived there — the reader must not have to infer the divert",
              "routed to you: this flag is ABOUT 'alpha'" in raw2
              and raw2.index("divert probe") > raw2.index("to: leader | type: note"))

        # ---- per-seat ctx-refresh threshold (coord exposes it, watch.py enforces it) ----
        for seat, marker in (("epsilon", "s_eps.jsonl"), ("zeta", "s_zet.jsonl"),
                             ("eta", "s_eta.jsonl")):
            (proj / marker).write_text(
                json.dumps({"type": "user",
                            "message": {"content": f"You are agent '{seat}' of the run"}}) + "\n"
                + json.dumps({"type": "assistant", "message": {"usage": {
                    "input_tokens": 200000, "cache_read_input_tokens": 350000,
                    "cache_creation_input_tokens": 20000}}}) + "\n")
        (wdir / "eta").mkdir(parents=True)
        (wdir / "eta" / "agent.md").write_text(
            "---\nagent: eta\nharness: claude\ncwd: /w/one\n---\nb\n")
        seats = {w["agent"]: w for w in coord.discover_workers(wdir)}
        check("ctx-refresh: coord exposes the briefing key per seat (int|None)",
              seats["epsilon"]["ctx_refresh"] == 90 and seats["zeta"]["ctx_refresh"] == 40
              and seats["eta"]["ctx_refresh"] is None)
        for seat, seat_pane in (("epsilon", "%5"), ("zeta", "%6"), ("eta", "%7")):
            coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                                 agent=seat, summary="w", pane=seat_pane))
            tails[seat_pane] = seat
        # All three sit at the SAME measured 57%. With the watcher's global at 60: zeta's own 40
        # must fire anyway, epsilon's own 90 must suppress, and eta (no per-seat value) must
        # follow the global and stay quiet.
        notes = run_pass(ns(context_pct=60))
        check("ctx-refresh: a seat's own threshold fires BELOW the watcher's global one",
              any("zeta" in n and "57" in n and "threshold 40" in n
                  and "briefing ctx-refresh" in n for n in notes))
        check("ctx-refresh: a seat's own HIGHER threshold suppresses the flag at 57%",
              not any("epsilon" in n for n in notes))
        check("ctx-refresh: a seat declaring none follows the global (57 < 60, quiet)",
              not any("'eta'" in n and "context is at" in n for n in notes))
        notes = run_pass(ns(context_pct=50))
        check("ctx-refresh: the global governs seats that declare none (eta at 57 >= 50)",
              any("'eta'" in n and "context is at" in n and "threshold 50" in n for n in notes))
        check("ctx-refresh: epsilon (own threshold 90) stays quiet even under the lower global",
              not any("epsilon" in n for n in notes))

        # ---- P38: an approval-gated seat is seen from its pane title, not 30 minutes later ----
        pane_titles["%7"] = "eta — Action Required"
        notes = run_pass(ns(context_pct=90))
        check("P38: a seat parked on its harness's approval prompt is flagged AT ONCE with the "
              "exact approve command — its pane is frozen, so the content-hash inactivity check "
              "only notices ~30 min after the seat stopped, and offers the wrong remedy",
              any("'eta'" in n and "approval prompt" in n and "approve eta" in n for n in notes))
        notes = run_pass(ns(context_pct=90))
        check("P38: the approval flag does not re-fire while the same gate is still up",
              not any("approval prompt" in n for n in notes))
        pane_titles.pop("%7")
        run_pass(ns(context_pct=90))
        check("P38: clearing the gate re-arms it — same discipline as every other crossing",
              not load_state(base).get("eta", {}).get("notified_approval"))
        pane_titles["%7"] = "eta — Action Required"
        notes = run_pass(ns(context_pct=90))
        check("P38: and it fires again on the next gate",
              any("'eta'" in n and "approve eta" in n for n in notes))
        pane_titles.pop("%7")

        # ---- PROP-9: system RAM/load pressure is a first-class duty of the loop ----
        sys_reading["v"] = {"avail_mb": 358, "load1": 1.6, "cores": 4}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            notes = run_pass(ns(context_pct=90))
        check("PROP-9: RAM below the floor flags SYSTEM PRESSURE once, with the remedy — the "
              "run's stuck-process pile-up OOM-killed the watcher ITSELF, unwarned",
              any("SYSTEM PRESSURE" in n and "358MB" in n and "floor 500MB" in n for n in notes))
        check("PROP-9: the pass report carries a system line, not counted as a seat",
              any(ln.strip().startswith("system") and "FLAG" in ln
                  for ln in buf.getvalue().splitlines()))
        notes = run_pass(ns(context_pct=90))
        check("PROP-9: does not re-fire while the pressure persists",
              not any("SYSTEM PRESSURE" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 4000, "load1": 0.4, "cores": 4}
        run_pass(ns(context_pct=90))  # pressure clears -> re-arms
        sys_reading["v"] = {"avail_mb": 4000, "load1": 9.2, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9: load at/over cores x factor fires a fresh episode after the clear",
              any("SYSTEM PRESSURE" in n and "9.2/4" in n for n in notes))
        # ---- PROP-9b: a flag must be able to FIRE AGAIN while its condition is getting worse ----
        # ⚠ EVERY CHECK BELOW FAILS ON THE PRE-FIX CODE BY CONSTRUCTION: it flagged once per episode
        # and re-armed only on a CLEAR, so a worsening reading produced exactly nothing. Measured
        # live the night this was found — RAM fell 2,904 -> 2,695 MB in ten minutes and the room
        # heard about it once. The re-fire cannot be shown by a first flag, so each case below runs
        # a first flag and then asserts about the SECOND.
        sys_reading["v"] = {"avail_mb": 4000, "load1": 0.4, "cores": 4}
        run_pass(ns(context_pct=90))                      # clear -> re-arm, known-good baseline
        sys_reading["v"] = {"avail_mb": 400, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: baseline — the FIRST flag of an episode still fires exactly as before",
              any("SYSTEM PRESSURE" in n and "400MB" in n for n in notes)
              and not any("WORSENING" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 351, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: a SMALL further drop (49MB, under the 250MB delta) stays QUIET — the "
              "re-arm must not turn every pass into a warning",
              not any("SYSTEM PRESSURE" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 150, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: a MATERIALLY worse reading RE-FIRES, and carries the trend (both readings) "
              "— one reading says the box is low, two say whether it is heading for an OOM",
              any("WORSENING" in n and "400MB -> 150MB" in n and "150MB RAM available" in n
                  for n in notes))
        sys_reading["v"] = {"avail_mb": 200, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: an IMPROVING reading that is still under the floor does NOT re-fire — "
              "deterioration is measured against the last FLAGGED reading, not the threshold",
              not any("SYSTEM PRESSURE" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 4000, "load1": 0.4, "cores": 4}
        run_pass(ns(context_pct=90))                      # clear
        sys_reading["v"] = {"avail_mb": 4000, "load1": 4.1, "cores": 4}
        run_pass(ns(context_pct=90))                      # first LOAD flag
        sys_reading["v"] = {"avail_mb": 4000, "load1": 5.2, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: the same rule applies to LOAD — a rise of one core's worth re-fires",
              any("WORSENING" in n and "4.1 -> 5.2" in n for n in notes))
        # ⚠ MIGRATION, the G-135/G-152 shape: `pressure_reading` is a NEW key, so an episode already
        # in progress when this code lands has `notified_pressure` set and nothing to compare with.
        # It must seed and stay QUIET — a fix whose first act is a spurious duplicate warning
        # teaches the room to discount the next one.
        st = load_sys_state(base)
        st.pop("pressure_reading", None)
        st["notified_pressure"] = True
        save_sys_state(base, st)
        sys_reading["v"] = {"avail_mb": 300, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: an episode already in flight when the key lands SEEDS silently — no "
              "spurious duplicate on upgrade — and re-fires normally on the next deterioration",
              not any("SYSTEM PRESSURE" in n for n in notes)
              and load_sys_state(base).get("pressure_reading", {}).get("avail_mb") == 300)
        sys_reading["v"] = {"avail_mb": 40, "load1": 0.4, "cores": 4}
        notes = run_pass(ns(context_pct=90))
        check("PROP-9b: ...and the seeded episode then re-fires on a materially worse reading",
              any("WORSENING" in n and "300MB -> 40MB" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 4000, "load1": 0.4, "cores": 4}
        run_pass(ns(context_pct=90))
        check("PROP-9b: clearing still wipes BOTH keys, so the next episode starts clean",
              "notified_pressure" not in load_sys_state(base)
              and "pressure_reading" not in load_sys_state(base))

        sys_reading["v"] = None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            notes = run_pass(ns(context_pct=90))
        check("PROP-9: an unmeasurable box (no /proc) -> no system line, no flag, no crash",
              not any(ln.strip().startswith("system") for ln in buf.getvalue().splitlines())
              and not any("SYSTEM PRESSURE" in n for n in notes))
        sys_reading["v"] = {"avail_mb": 4000, "load1": 0.4, "cores": 4}

        # ---- PROP-10: a briefing-declared wave window left with NO active seat ----
        (wdir / "wv1").mkdir()
        (wdir / "wv1" / "agent.md").write_text(
            "---\nagent: wv1\nharness: claude\nwindow: wave-x\nephemeral: yes\n---\nb\n")
        win_map["testsess:wave-x"] = ["%40", "%41"]
        notes = run_pass(ns(context_pct=90))
        check("PROP-10: a wave window with panes but no active seat is flagged once with the "
              "kill-window remedy — covers seats that died at model-init before ever checking "
              "in, AND a closed wave's leftover bash shells",
              any("wave-x" in n and "kill-window" in n for n in notes))
        notes = run_pass(ns(context_pct=90))
        check("PROP-10: does not re-fire while the leftover window persists",
              not any("kill-window" in n for n in notes))
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="wv1", summary="w", pane="%40"))
        tails["%40"] = "wv1-tail"
        notes = run_pass(ns(context_pct=90))
        check("PROP-10: an active seat in the window clears the flag (re-arm) — a live wave is "
              "never reported as leftover",
              not any("kill-window" in n for n in notes))
        coord.cmd_checkout(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                              agent="wv1", no_export=True))
        notes = run_pass(ns(context_pct=90))
        check("PROP-10: fires again once the wave has closed and its window still holds panes",
              any("wave-x" in n and "kill-window" in n for n in notes))
        win_map.clear()

        # ---- PROP-11: roster-ACTIVE rows reconciled against the process table (leader #125) ----
        # The gap common to five defects in one night: nothing checked that a row claiming ACTIVE
        # still had a harness behind it. A closer checked itself in from a bare shell and was
        # believed; the watcher agent died twice with its row still reading ACTIVE.
        pane_harness["%1"] = []          # alpha's pane: shell only, no harness
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: a roster-ACTIVE row whose pane runs NO harness process is flagged "
              "GHOSTROW and the leader is told — the roster is the run's map of what is alive, "
              "and until now nothing ever checked it against the process table",
              any("alpha" in n and "NO harness process" in n for n in notes))
        check("PROP-11: the notification says what it costs (work stopped, wakes typed into a "
              "bare shell) and names the exact remedy — never acts itself",
              any("typed into a bare shell" in n and "close-seat alpha --renew" in n
                  for n in notes))
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: armed once per seat/pane, like every other flag",
              not any("NO harness process" in n for n in notes))
        pane_harness["%1"] = [4242]      # a harness came back up
        run_pass(ns(context_pct=90))
        pane_harness["%1"] = []
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: re-arms once a harness is seen again, so a second death is reported",
              any("NO harness process" in n for n in notes))
        pane_harness["%1"] = None        # unverifiable
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: 'cannot tell' is NOT 'nothing running' — an unreadable process table "
              "raises nothing (fail-safe, same asymmetry as coord's checkin guard)",
              not any("NO harness process" in n for n in notes))
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="watcher", summary="w", pane="%3"))
        pane_harness["%3"] = []
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: the WATCHER'S OWN row is reconciled too — this loop outlives the watcher "
              "agent, so it is the only thing positioned to report that death (the watcher named "
              "this exact gap to the owner and then died of it)",
              any("watcher" in n and "NO harness process" in n for n in notes))
        coord.cmd_checkout(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                              agent="watcher", no_export=True))
        pane_harness.clear()

        # ---- P32: every pass stamps a heartbeat, so a dead loop is visible from outside ----
        run_pass(ns(context_pct=90))
        hb = coord.watcher_heartbeat(base)
        check("P32: each pass writes watch-heartbeat.json and coord reads it back as a LIVE "
              "watcher — this loop is detached (nohup), so its death used to leave the run with "
              "no liveness/context/approval cover and no signal that anything had stopped",
              hb is not None and hb["stale"] is False and hb["age_min"] == 0
              and hb["pid"] == os.getpid())
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(
            {"last_pass": "2000-01-01T00:00:00", "loop_min": 10, "pid": 1}))
        hb = coord.watcher_heartbeat(base)
        check("P32: a stamp older than three missed passes reads STALE, and the deadline is "
              "derived from the loop's own cadence — a 10-min loop and a 60-min loop are not "
              "late at the same age",
              hb["stale"] is True and hb["stale_after"] == 30)
        (base / "watch-heartbeat.json").write_text("{ not json", encoding="utf-8")
        check("P32: an unreadable or half-written heartbeat reads as 'no watcher', never a crash "
              "inside the roster view every seat runs",
              coord.watcher_heartbeat(base) is None)

        # ---- G-158: is it running, vs is it running WHAT WE THINK ----
        check("G-158: the fingerprint covers the WHOLE import surface, not just watch.py — a "
              "marker over this file alone would have read CURRENT for two hours while coord.py "
              "drifted four commits under a live loop, certifying the exact state it exists to "
              "detect",
              set(Path(p).name for p in LOADED_CODE) >= {"watch.py", "coord.py"})
        check("G-158: the fingerprint is taken from FILE BYTES, not git metadata — a repo sha "
              "reports CURRENT while a dirty tree runs bytes that were never committed",
              all(v == hashlib.sha256(Path(k).read_bytes()).hexdigest()
                  for k, v in LOADED_CODE.items()))
        run_pass(ns(context_pct=90))
        hb = coord.watcher_heartbeat(base)
        check("G-158 CONTROL: a loop whose files are untouched reports NO drift — without this "
              "the next check cannot tell a working detector from one that always cries stale",
              hb["code_known"] is True and hb["code_drifted"] == [])
        # The defect itself, reproduced: stamp a real pass, then change a file underneath it. This
        # is what the live loop has been doing all evening — heartbeating over code that moved.
        stamped = json.loads((base / "watch-heartbeat.json").read_text(encoding="utf-8"))
        drifted_file = next(p for p in stamped["code"] if Path(p).name == "coord.py")
        stamped["code"][drifted_file] = "0" * 64
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(stamped))
        hb = coord.watcher_heartbeat(base)
        check("G-158: a file that CHANGED since the loop imported it is named in the drift list — "
              "and coord.py specifically, because the loop's stale code is its import surface and "
              "not merely its own script",
              hb["code_known"] is True and hb["code_drifted"] == ["coord.py"])
        stamped["code"] = {str(base / "vanished.py"): "0" * 64}
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(stamped))
        hb = coord.watcher_heartbeat(base)
        check("G-158: a stamped file that no longer exists reads as DRIFTED, never as agreement — "
              "an unreadable file answers 'I cannot tell', which is not 'fine'",
              hb["code_drifted"] == ["vanished.py (unreadable now)"])
        del stamped["code"]
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(stamped))
        hb = coord.watcher_heartbeat(base)
        check("G-158: a loop predating the marker reports code_known FALSE — UNKNOWN, never OK. "
              "Defaulting absence to healthy would rebuild the absence-reads-as-health defect "
              "inside the detector built to close it",
              hb["code_known"] is False and hb["code_drifted"] == [])

        # ---- Stage 4 §1 (s4-03): the seat-down DETECTOR, report-only ----
        # FIXTURE-ONLY BY DESIGN. The live-substrate proof (a real tmux room, a real team_monitor
        # state.json, a real kill -9) is task s4-10's and is NOT attempted here — a hand-authored
        # snapshot is explicitly not acceptable as THAT evidence. These are the detector's own
        # controls: they prove the classifier, not the room.
        rpkg = Path(td) / "revpkg"
        rbase = rpkg / "coordination"
        rbase.mkdir(parents=True)
        rstate, rnotes = {}, []
        rargs = argparse.Namespace(package=str(rpkg), base=None, workers_dir=None,
                                   notify_to="leader", notify_fallback="leader")

        def rroster(*rows):
            body = ["| agent | active | pane | summary | checkin | checkout | lastread |",
                    "|---|---|---|---|---|---|---|"]
            body += [f"| {a} | {act} | {pane} | s | c |  |  |" for a, act, pane in rows]
            (rbase / "workers.md").write_text("\n".join(body) + "\n", encoding="utf-8")

        def rsnap(absent=(), seats=(), alive=True, age_s=0):
            return {"captured_at": time.time() - age_s, "session_alive": alive,
                    "session": "revsess", "seats": list(seats), "roster_absent": list(absent)}

        def gone(seat="dseat", pane="%77", liveness="absent"):
            return {"seat": seat, "pane": pane, "roster_active": True, "liveness": liveness,
                    "agent_type": "claude-code", "agent_type_source": "descriptor",
                    "reason": "roster row active, pane not in the room"}

        def rev(snap, snap_err=None):
            """One tick. Returns (report lines, notes pushed BY THIS TICK)."""
            before = len(rnotes)
            out = check_revival(rargs, rbase, snap, snap_err, rstate, rnotes)
            return out, rnotes[before:]

        def gt(seat="dseat"):
            return ((rstate.get(seat) or {}).get("revival") or {}).get("gone_ticks")

        rroster(("dseat", "yes", "%77"), ("leader", "yes", "%1"))

        # (9) `snap_err` — UNREADABLE reads as STALE, ABSENT is the different, silent path.
        lines, pushed = rev(None, "state.json is UNREADABLE at /x/state.json: Expecting value")
        check("s4-03 (9): a state.json that EXISTS and cannot be read is a SENSOR OUTAGE — it "
              "pauses the detector, and is never read as 'no seat is absent'. Absence reading as "
              "health is this run's signature failure",
              any(REVIVAL_STALE_LINE in l for l in lines))
        check("s4-03 (9) CONTROL: an ABSENT state.json takes the different, SILENT path — this "
              "module ships kit-wide and every package without team-monitor lands there, so a "
              "pause line every tick would be noise in every other run",
              rev(None, "state.json is ABSENT at /x/state.json")[0] == [])
        check("s4-03 (9) COUPLING GUARD: the absent-vs-unreadable discriminator is budget._load's "
              "OWN wording, so it is asserted against that function rather than assumed — if "
              "budget.py rewords, this goes red instead of the predicate silently answering False",
              _snapshot_absent(budget_mod._load(str(rpkg / "nope.json"), "state.json")[1])
              and not _snapshot_absent(None))
        rstate.clear(); rnotes.clear()

        # (2) THE CONTROL THAT MUST NOT FIRE — a detector, not a relauncher.
        thinking = {"seat": "thinker", "pane": "%1", "liveness": "live", "harness_pid": 4242,
                    "prompt_pending": False, "last_activity_age_s": 7200.0}
        lines, pushed = rev(rsnap(seats=[thinking]))
        lines2, pushed2 = rev(rsnap(seats=[thinking]))
        check("⚠ s4-03 (2) THE CONTROL THAT MUST NOT FIRE: a LIVE seat with prompt_pending false "
              "and last_activity_age_s > 3600 — a leader forty minutes into one ruling — is NEVER "
              "classified crashed, changes no state and pushes no note. Without this control the "
              "test cannot distinguish a detector from a relauncher",
              not any("CRASHED" in l for l in lines + lines2)
              and "thinker" not in rstate and pushed == [] and pushed2 == [])
        rstate.clear(); rnotes.clear()

        # (3) The discriminator is harness_pid liveness AND NOTHING ELSE — asserted over the
        # function's OWN source, so a future "tiebreak on activity age" cannot land quietly.
        import inspect
        rsrc = inspect.getsource(check_revival)
        check("⚠ s4-03 (3): `last_activity_age_s` and `prompt_pending` are NOT READ by this arm at "
              "all — the ruling's binding condition (a HARD liveness signal, never a silence "
              "timeout) is satisfied STRUCTURALLY rather than by a tuned threshold. Grep-shaped and "
              "weak alone; it is paired with the behavioural control above",
              "last_activity_age_s" not in rsrc.split('"""')[2]
              and "prompt_pending" not in rsrc.split('"""')[2])

        # (4) ROOM-DEAD short-circuits the whole candidate walk.
        lines, pushed = rev(rsnap(absent=[gone()], alive=False))
        check("s4-03 (4): a DEAD ROOM prints its one line and performs NO per-seat "
              "classification — every seat is absent when the session is gone, and reporting N "
              "crashes for ONE incident would point the room at the wrong mechanism entirely",
              lines == [REVIVAL_ROOM_DEAD_LINE])
        check("s4-03 (4) CONTROL: with session_alive TRUE the same fixture DOES classify per "
              "seat — proving the short-circuit is the room's state and not a dead branch",
              any("dseat" in l for l in rev(rsnap(absent=[gone()], alive=True))[0]))
        rstate.clear(); rnotes.clear()

        # (5) CLEANLY-OUT is never a candidate, and its control proves the fixture COULD crash.
        (rbase / "awaiting-close.json").write_text(json.dumps({"dseat": {"since": "x"}}))
        l1, _ = rev(rsnap(absent=[gone()]))
        l2, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (5): a seat in awaiting-close.json is CLEANLY-OUT, never CRASHED, however "
              "many ticks it stays absent — cmd_checkout records the pane as a debt that never "
              "expires BY DESIGN, and a checked-out seat is not a crash",
              all("CLEANLY-OUT" in l for l in l1 + l2) and not any("CRASHED" in l for l in l1 + l2)
              and gt() == 0)
        (rbase / "awaiting-close.json").write_text(json.dumps({}))
        rroster(("dseat", "no", "%77"), ("leader", "yes", "%1"))
        l3, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (5b): the LIVE roster row reading active != yes is the second CLEANLY-OUT "
              "arm, read at classification time rather than from the snapshot",
              "CLEANLY-OUT" in " ".join(l3))
        rroster(("dseat", "yes", "%77"), ("leader", "yes", "%1"))
        l4, _ = rev(rsnap(absent=[gone()]))
        l5, _ = rev(rsnap(absent=[gone()]))
        check("⚠ s4-03 (5) CONTROL: with the awaiting entry removed and the roster row active, "
              "the IDENTICAL fixture reaches CRASHED — a never-fires test proves nothing",
              "CRASHED — would revive" in " ".join(l5)
              and "CRASHED — would revive" not in " ".join(l4))
        rstate.clear(); rnotes.clear()

        # (6) An unparseable ledger REFUSES. BOTH ARMS, or the inversion was never tested —
        # load_awaiting's own fail-safe would silently pass the first arm on its own.
        (rbase / "awaiting-close.json").write_text("{ not json at all")
        l1, p1 = rev(rsnap(absent=[gone()]))
        l2, p2 = rev(rsnap(absent=[gone()]))
        check("⚠ s4-03 (6): a ledger that is PRESENT but UNPARSEABLE makes the detector REFUSE — "
              "the shared loaders collapse it to 'no debt', which here would let a mid-close seat "
              "read as a crash. Three states locally where they have two",
              not any("CRASHED" in l for l in l1 + l2)
              and all("REVIVAL REFUSED" in l for l in l1 + l2))
        check("s4-03 (6): the refusal NAMES ITS LAYER (R-8) and is pushed exactly ONCE, while the "
              "report line prints every tick so the hole never goes quiet",
              len(p1) == 1 and p2 == [] and "revival detector gate" in p1[0])
        check("s4-03 (6) CONTROL: the same fixture with VALID json and no entry reaches CRASHED — "
              "without it the refusal arm could be passing for the wrong reason",
              ((rbase / "awaiting-close.json").write_text("{}") or True)
              and "CRASHED" in " ".join(rev(rsnap(absent=[gone()]))[0] +
                                        rev(rsnap(absent=[gone()]))[0]))
        rstate.clear(); rnotes.clear()

        # (7) Debounce needs two ticks, and the reset must survive an IN-PLACE respawn.
        l1, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (7): one tick on a fresh candidate counts, and does NOT classify CRASHED — "
              "firing on a single tick would make one transient sensor error a relaunch",
              gt() == 1 and "CRASHED — would revive" not in " ".join(l1)
              and "1/2" in " ".join(l1) and "20 min" in " ".join(l1))
        l2, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (7): the second consecutive non-stale tick classifies CRASHED",
              gt() == 2 and "CRASHED — would revive" in " ".join(l2))
        rstate.clear()
        rev(rsnap(absent=[gone()]))
        rev(rsnap(seats=[{"seat": "dseat", "pane": "%77", "liveness": "live",
                          "harness_pid": 31337}]))
        check("⚠ s4-03 (7) CONTROL — THE BUG THE EXISTING RESET CANNOT CATCH: an IN-PLACE respawn "
              "keeps the SAME pane id, so the `pane != pane` reset never fires. The counter is "
              "cleared EXPLICITLY on liveness == live, and this proves it",
              gt() is None or gt() == 0)
        l3, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (7) CONTROL: after that reset the seat must start over at 1, not resume at 2 "
              "— otherwise the reset is cosmetic",
              gt() == 1 and "CRASHED — would revive" not in " ".join(l3))
        rstate.clear(); rnotes.clear()

        # (8) STALE FREEZES the counter. A freeze and a reset are indistinguishable without the pair.
        rev(rsnap(absent=[gone()]))
        l2, _ = rev(rsnap(absent=[gone()], age_s=budget_mod.STALE_AFTER_S + 60))
        check("s4-03 (8): a stale snapshot PAUSES enforcement and FREEZES the debounce counter — "
              "neither increments nor resets, because a stale snapshot is evidence in NEITHER "
              "direction (CMP-21 invariant 2)",
              any(REVIVAL_STALE_LINE in l for l in l2) and gt() == 1)
        l3, _ = rev(rsnap(absent=[gone()]))
        check("⚠ s4-03 (8) THE DISCRIMINATING ARM: the next fresh tick reaches CRASHED. Had the "
              "stale tick RESET instead of frozen, this tick would read 1/2 — that is the only "
              "observation that tells a freeze from a reset",
              "CRASHED — would revive" in " ".join(l3))
        _, p1 = rev(rsnap(absent=[gone()], age_s=9999))
        _, p2 = rev(rsnap(absent=[gone()], age_s=9999))
        _, p3 = rev(rsnap(absent=[gone()], age_s=9999))
        _, p4 = rev(rsnap(absent=[gone()], age_s=9999))
        check("s4-03 (8): a sustained sensor outage is flagged ONCE, after 3 consecutive stale "
              "ticks — the SENSOR is the incident, and it says so",
              p1 == [] and p2 == [] and len(p3) == 1 and p4 == []
              and "REVIVAL PAUSED" in p3[0])
        rstate.clear(); rnotes.clear()

        # (10) MID-RENEWAL uses PLAIN pid+starttime equality, never the harness predicate.
        me = (os.getpid(), coord.proc_stat(os.getpid())[1])
        (rbase / "lifecycle-inflight.json").write_text(json.dumps(
            {"dseat": {"state": "in-flight", "disposition": "renew",
                       "executor": {"pid": me[0], "starttime": me[1]}}}))
        l1, _ = rev(rsnap(absent=[gone()]))
        l2, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (10): a marker entry in-flight whose executor is a LIVE PYTHON process is "
              "MID-RENEWAL — and stays so however long it is absent",
              all("MID-RENEWAL" in l for l in l1 + l2)
              and not any("CRASHED" in l for l in l1 + l2))
        check("⚠ s4-03 (10) THE RED ARM, IN-SUITE: `coord.ident_is_live_harness` answers DEAD for "
              "this very same live ident, because is_harness_argv matches only "
              "claude/codex/opencode and the lifecycle executor is PYTHON. Using it here would "
              "turn MID-RENEWAL into CRASHED and produce the exact double-launch stage 4 exists "
              "to prevent — so the two predicates are asserted to DISAGREE on this ident",
              _executor_ident_live({"executor": {"pid": me[0], "starttime": me[1]}}) is True
              and coord.ident_is_live_harness(me) is False)
        (rbase / "lifecycle-inflight.json").write_text(json.dumps(
            {"dseat": {"state": "in-flight", "executor": {"pid": 999999, "starttime": "1"}}}))
        l3, _ = rev(rsnap(absent=[gone()]))
        l4, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (10) CONTROL: a marker whose executor ident is GONE does not hold the seat in "
              "MID-RENEWAL forever — the same fixture with a dead ident reaches CRASHED",
              "CRASHED — would revive" in " ".join(l4) and "MID-RENEWAL" not in " ".join(l3 + l4))
        (rbase / "lifecycle-inflight.json").unlink()
        rstate.clear(); rnotes.clear()

        # Marker ABSENT reads as "no entry", the correct reading until Stage 3 ships its reader.
        check("s4-03: an ABSENT lifecycle-inflight.json is 'no entry', not a refusal — Stage 3 "
              "has not shipped the marker yet and treating its absence as unreadable would make "
              "the detector permanently inert",
              "CRASHED" in " ".join(rev(rsnap(absent=[gone()]))[0]
                                    + rev(rsnap(absent=[gone()]))[0]))
        rstate.clear(); rnotes.clear()

        # IDLE is unreachable BY CONSTRUCTION, and the code says so out loud rather than branching.
        l1, p1 = rev(rsnap(absent=[gone(liveness="live")]))
        check("s4-03 (IDLE): a `live` row inside roster_absent is a SENSOR CONTRADICTION "
              "team_monitor.absent_rows cannot produce — the detector refuses to classify it and "
              "says so, instead of silently picking a branch",
              "INVARIANT BROKEN" in " ".join(l1) and len(p1) == 1)
        rstate.clear(); rnotes.clear()

        check("s4-03: a room with NO roster-absent seat still prints a line every tick — a hole "
              "must never go quiet, and silence is indistinguishable from a detector that is off",
              rev(rsnap())[0] == [f"{'revival':<18} {'ok':<7} no roster-absent seat"])
        rstate.clear(); rnotes.clear()

        # ---- 7.37 criterion 3 / R10: goal-level state, per-run sections ----
        # ⚠ THIS BLOCK EXISTS BECAUSE THE SUITE ABOVE PASSED WITHOUT EXERCISING ONE LINE OF IT.
        # The temp package has no goal folder, so every case above takes the no-goal fallback —
        # a green suite over code that never ran (G-78). The goal shape has to be built on purpose.
        goal = Path(td) / "goalfolder"
        for tag in ("run-1", "run-2"):
            (goal / "runs" / tag / "coordination").mkdir(parents=True)
        gbase1 = goal / "runs" / "run-1" / "coordination"
        gbase2 = goal / "runs" / "run-2" / "coordination"

        check("R10 CONTROL: with no runs.csv the goal does NOT resolve — the resolver refuses to "
              "GUESS a goal folder. Without this, the checks below could pass against a directory "
              "picked by counting path segments, which is how a watcher writes outside its goal",
              goal_state(gbase2) == (None, None))

        (goal / "runs.csv").write_text("run,status\nrun-1,closed\nrun-2,open\n")
        gp, gtag = goal_state(gbase2)
        check("R10: the goal folder resolves by its runs.csv (the R11 run INDEX), and the state "
              "file sits at GOAL level — not inside the run",
              gp == goal / "watch-state.json" and gtag == "run-2")
        check("R10: a bare --base outside any goal keeps the pre-7.37 per-run behaviour",
              goal_state(Path(td) / "coordination") == (None, None))

        # legacy per-run files, as they exist on disk before the cutover
        (gbase1 / "watch-state.json").write_text(json.dumps(
            {"ghost": {"pane": "%40", "notified_ghostrow": True}}))
        (gbase2 / "watch-state.json").write_text(json.dumps({"live": {"pane": "%292"}}))

        check("R10 MIGRATE, not discard: the first load lifts EVERY run's legacy file into "
              "sections and returns THIS run's — a goal file starting empty would re-arm every "
              "seat and re-fire notifications already sent",
              load_state(gbase2) == {"live": {"pane": "%292"}})
        check("R10 MIGRATE: the prior run's entries are lifted too, not dropped on the floor",
              load_state(gbase1) == {"ghost": {"pane": "%40", "notified_ghostrow": True}})

        save_state(gbase2, {"live": {"pane": "%292", "notified_dead": True}})
        on_disk = json.loads((goal / "watch-state.json").read_text())
        check("R10: the goal-level file is written, sectioned by run tag",
              set(on_disk["runs"]) == {"run-1", "run-2"})
        check("R10: writing run-2 leaves run-1's section INTACT — a whole-file write that dropped "
              "the other run would be the silent-flag-loss this shape exists to prevent",
              on_disk["runs"]["run-1"] == {"ghost": {"pane": "%40", "notified_ghostrow": True}})
        check("⚠ R10 THE CRITERION ITSELF — read correctly ACROSS a run boundary: run-2's loop "
              "opens a file that CONTAINS run-1's stale notified_ghostrow and does NOT inherit it. "
              "A flat name-keyed merge returns that flag and pre-suppresses the warning; this "
              "returns only run-2's section (A/B measured in seats/S9-737-watchstate/)",
              "ghost" not in load_state(gbase2))
        check("R10: run-1's section is still readable after run-2 wrote — SURVIVES across runs, "
              "which is R10's actual words",
              load_state(gbase1) == {"ghost": {"pane": "%40", "notified_ghostrow": True}})

        (goal / "watch-state.json").write_text("{ this is not json")
        check("R10: a corrupt goal file degrades to EMPTY, never raises — a watcher that dies on "
              "its own state file takes the run's only sensor down with it",
              load_state(gbase2) == {})

    coord.RUNS_INDEX = real_runs_index
    try:
        real_runs_after = real_runs_index.read_bytes()
    except OSError:
        real_runs_after = None
    check("isolation: the real runs registry is byte-identical before and after — this selftest "
          "used to leak its temp package into ~/.config/rbtv/coordinate-runs.json",
          real_runs_after == real_runs_before)

    if coord_env_agent is not None:
        os.environ["COORD_AGENT"] = coord_env_agent
    print(f"\nselftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failure(s))")
    sys.exit(1 if failures else 0)


def main():
    p = argparse.ArgumentParser(prog="watch.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--package", help="abs path of the run package folder")
    p.add_argument("--base", help="override state-file directory (testing only)")
    p.add_argument("--workers-dir", help="override worker-briefings directory (testing only)")
    p.add_argument("--inactive-min", type=int, default=30, help="flag a seat after this many minutes without pane activity (default 30)")
    p.add_argument("--context-pct", type=float, default=50, help="flag a claude seat at this context percentage (default 50)")
    # ⚠ DEFAULT None, NOT 500 (task 7.82 criterion 3, leader ruling #1409). The old default was
    # the exact defect criterion 5 names: it let the loop START WITHOUT READING the declaration,
    # so a relaunch that dropped the flag watched against a floor 4x under the ruled one and said
    # nothing. ABSENT now means READ the run's budget.json; a value means a deliberate override.
    #
    # ⚠ THE G-29 BOUNDARY, so nobody reads this as that defect's fix: G-29 is where the NUMBER 500
    # gets judged against the owner's "supersedes 2800 and 2400 alike" test. 7.82 is where the
    # COPYING stops. This change removes the fallback; it does not rule on 500 as a value.
    p.add_argument("--mem-floor-mb", type=int, default=None,
                   help="DELIBERATE OVERRIDE ONLY (PROP-9). Absent, the pressure floor is read "
                        "from {--package}/budget.json floors.pressure_warn_mb, its one normative "
                        "home (r-floor-single-source). A value here overrules an owner ruling, so "
                        "the loop reports which value it used and why.")
    p.add_argument("--load-per-core", type=float, default=1.0, help="flag SYSTEM PRESSURE when 1-min load reaches cores x this factor (default 1.0; PROP-9)")
    p.add_argument("--notify", action="store_true", help="send each new flag to its recipient as a coordination note (default: print only)")
    p.add_argument("--notify-to", metavar="SEAT", default="leader",
                   help="seat that receives flags (default leader). A flag ABOUT this seat is "
                        "diverted to --notify-fallback: a seat cannot be told to act on itself")
    p.add_argument("--notify-fallback", metavar="SEAT", default="leader",
                   help="seat that receives flags ABOUT --notify-to (default leader)")
    p.add_argument("--loop", type=int, metavar="MIN", help="repeat forever every MIN minutes (the watcher seat's mode)")
    p.add_argument("--claude-projects-dir", help="override ~/.claude/projects (testing only)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        cmd_selftest()
        return
    if not (args.package or args.base or os.environ.get("COORD_PACKAGE")):
        p.error("--package is required (or COORD_PACKAGE)")

    # ⚠ RESOLVED ONCE, AT STARTUP, AND REPORTED — criterion 5 is a HARD START FAILURE, so it must
    # fire HERE and not on the first pass: a loop that starts and only later discovers it has no
    # floor has already told the room it is watching.
    #
    # ⚠⚠ AND THIS IS A DIFFERENT CALL SITE FROM THE CAPACITY CHECK, DELIBERATELY. `check_budget`
    # stays SILENT when a package declares no budget.json -- that is the normal case for every
    # other package and it must stay silent so this module ships kit-wide. THE FLOOR IS NOT THE
    # CAP: this loop cannot flag pressure without a threshold, so absence here is fatal where
    # absence there is routine. Collapsing the two would either brick the module everywhere or
    # restore the silent fallback. Both halves are load-bearing; neither is the other's default.
    run_root = Path(args.package or os.environ.get("COORD_PACKAGE")
                    or Path(args.base).resolve().parent)
    try:
        args.mem_floor_mb, floor_why = budget_mod.floor_source(run_root, "warn", args.mem_floor_mb)
    except (budget_mod.FloorUndeclared, budget_mod.FloorUnreadable) as exc:
        print("watch: REFUSING TO START — %s\n"
              "  The pressure floor's one home is the run's budget.json (r-floor-single-source, "
              "G-42). This loop will not invent a threshold: a SYSTEM PRESSURE flag raised "
              "against a made-up floor reads as a measurement and is worse than no flag.\n"
              "  Declare floors.pressure_warn_mb there, or pass --mem-floor-mb to override "
              "deliberately." % exc, file=sys.stderr)
        sys.exit(2)
    print("watch: floor %s" % floor_why, file=sys.stderr)
    if args.loop:
        while True:
            run_pass(args)
            time.sleep(args.loop * 60)
    else:
        run_pass(args)


if __name__ == "__main__":
    main()
