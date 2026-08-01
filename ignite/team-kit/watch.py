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
             row (the one row nothing else can report on). THIS flag notifies and never acts;
             the loop's ONE actuator arm is the seat-down revival arm — see the charter beside
             the PROP-11 loop in `run_pass`.
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
the pane) telling the recipient exactly what to run — e.g. the seat's OWN
`checkout --renew --handoff "<note>"` at the context threshold. A crossing re-arms only when the
condition clears (activity resumes / the seat's pane changes, i.e. it was renewed).

⚠ A FLAG IS NEVER SENT TO THE SEAT IT IS ABOUT. `--notify-to` (default `leader`) takes the flags;
a flag whose SUBJECT is that seat is diverted to `--notify-fallback` (default `leader`), because a
seat cannot be asked to adjudicate a warning about itself. This is not a special case for one role:
it was found as one — a context warning about the LEADER was delivered to the leader, which holds
its own close/renew/approve with no seat above it and an AFK owner — and the general rule is what
closes it, since pointing the flags at any single seat just moves the hole to that seat.

  python3 watch.py --package <abs-run-package> [--notify] [--loop-forever] [--cadence-s SEC]

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
    # A declared seat cwd may carry a trailing slash (materialize's `cwd-mode: seat-folder`
    # bakes one into the frontmatter); the harness's project-dir name never does. Munging the
    # slash into a trailing `-` names a directory that does not exist, so every transcript
    # lookup from a declared cwd returns None and the CONTEXT flag can never fire.
    return re.sub(r"[/.]", "-", str(cwd).rstrip("/") or "/")


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
    user text references this seat's own `seats/<agent>/` (or legacy `workers/<agent>/`) path
    fragment. mtime alone is never sufficient — the fragment match is required."""
    pdir = projects_dir(proj_override) / munge_cwd(cwd)
    if not pdir.is_dir():
        return None
    fragments = (f"seats/{agent}/", f"workers/{agent}/")
    candidates = []
    for p in sorted(pdir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        head = first_user_text(p)
        if any(f in head for f in fragments):
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


RUN_CLOSED_LINE = "run closed in runs.csv — watch exiting (deterministic close)"


def run_closed(package):
    """True once THIS RUN's own row in the goal's runs.csv reads closed (G-297).

    MATCHED FROM `team_monitor.py:410 run_closed`, DELIBERATELY NOT IMPORTED — the two modules are
    separate custody, the same reason goal_state resolves the goal here instead of reaching into
    coord.base_dir. Until this existed the two sibling loops of ONE watch layer disagreed about a
    closed run: team-monitor exited, this loop did not, and a watch loop outlived run-2 by ~9.5h
    while still WRITING into a folder `.rbtv/goals/CLAUDE.md` rules is append-only HISTORY. A live
    process editing frozen record is a correctness defect, not untidiness.

    FAILS OPEN BY CONSTRUCTION: absent, unreadable or unparseable runs.csv -> False, so a BROKEN
    METER CAN NEVER STOP A HEALTHY LOOP. The reasoning is the sibling's and transfers verbatim —
    this loop is the run's only source of liveness, approval, context and RAM flags, and silencing
    it over an unreadable CSV costs more than letting it run one run too long.

    THE ROW IS FOUND BY RUN-ID, never by position — and the `runs` layer is asserted BEFORE the file
    is opened, which the sibling does not do and this file needs: `run-1` exists in EVERY goal, so a
    package path that resolved the wrong directory would match a FOREIGN goal's `run-1` row and stop
    this loop on a stranger's state. That check can only ever return False, so it cannot weaken the
    fail-open posture. It is R11's discipline, the one goal_state states at :336.
    """
    import csv
    p = Path(package).resolve()
    if p.parent.name != "runs":
        return False
    try:
        with (p.parent.parent / "runs.csv").open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if (row.get("run-id") or "").strip() == p.name:
                    return (row.get("state") or "").strip().lower() == "closed"
    except (OSError, csv.Error, UnicodeDecodeError):
        return False
    return False


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


def _ticks_minutes(ticks, args):
    """`ticks` of the loop rendered as human wall-clock, DERIVED from the cadence actually in force.

    ⚠ IT IS COMPUTED, NOT WRITTEN DOWN, AND THAT IS THE WHOLE REASON IT EXISTS. The line this feeds
    is the one place an operator reads a detection latency, and it used to carry the literal
    "~20 min worst case at the live loop's --loop 10" — arithmetic over a cadence that the owner has
    now superseded, printed every tick, to a human, as if it were an observation. A latency spelled
    out beside a cadence that can change is a stale claim with a schedule.

    The tick constants themselves are UNTOUCHED and stay in TICK units (`r-watch-loop-30s`: they
    re-scale by the cadence alone). This renders them; it never redefines them.

    Returns "n/a (one-shot)" on a non-looping pass, where no cadence is resolved and there is no
    such thing as a next tick.
    """
    cadence = getattr(args, "cadence_s", None)
    if not isinstance(cadence, int) or cadence <= 0:
        return "n/a (one-shot)"
    seconds = ticks * cadence
    if seconds < 120:
        return "%ds" % seconds
    return "%.1f min" % (seconds / 60.0)


def _loop_min_compat(loop_seconds):
    """`loop_seconds` rendered into the heartbeat's LEGACY minute-denominated field, or None.

    ⚠ THIS FUNCTION EXISTS TO KEEP `coord.py` OUT OF TASK 7.112's DIFF, and saying so is the point.
    `loop_min` is a CROSS-MODULE PROTOCOL FIELD with three readers, and two of them are outside this
    change's declared outputs and under separate custody:

      * `coord.py:~884`  `stale_after = (loop_min * 3) if isinstance(loop_min, int) ... else 30`
      * `coord.py:~6841` `f", loop {hb['loop_min']}min" if hb.get("loop_min") else ", one-shot"`
      * `jobs/selfheal-watch.py` — migrated to `loop_seconds` by this same task; it is an output.

    DROPPING THE FIELD WOULD HAVE BEEN THE SILENT DEFECT THIS WHOLE WAVE IS ABOUT. With `loop_min`
    absent or non-int, BOTH coord readers fall through: staleness becomes a flat 30 MINUTES (a dead
    30-second sensor would go unreported ~20x longer than today) and `coordinate workers` prints the
    live sentinel as `one-shot`. That is `G-42`'s weaker-sensor-nobody-notices shape arriving through
    a data field instead of an argv.

    So the field survives, MEANING EXACTLY WHAT ITS NAME SAYS — minutes — rounded UP, never below 1:

      * ceil, not round: it feeds staleness multipliers, and rounding 30 s DOWN to 0 would re-enter
        the `else 30` fallback this exists to avoid — the falsy-zero trap that made `--loop 0`
        meaningless is the same trap one layer down.
      * `max(1, ...)`: coord gates on `loop_min > 0`.

    THE RESIDUAL, NAMED NOT BURIED. At 30 s coord computes staleness of 3 min where the true figure
    is 1.5 — TIGHTER than the 30 it would otherwise use and never looser than today's behaviour, so
    the rounding errs toward reporting a dead sensor early. `coordinate workers` shows `loop 1min`
    for a 30-second loop: visibly coarse, and not the `one-shot` lie. Retiring `loop_min` in favour
    of `loop_seconds` across all three readers is filed as a protocol migration this task must not
    absorb — it requires `coord.py`, which task 7.112 does not hold.
    """
    if not isinstance(loop_seconds, int) or isinstance(loop_seconds, bool) or loop_seconds <= 0:
        return None
    return max(1, -(-loop_seconds // 60))


def save_heartbeat(base, loop_seconds, daemon=None, change=None, daemon_code=None, budget=None):
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
             "loop_seconds": loop_seconds, "loop_min": _loop_min_compat(loop_seconds),
             "pid": os.getpid(), "code": LOADED_CODE,
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


def pressure_remedy(mem_low, load_high):
    """The remedy sentence for the trigger that ACTUALLY fired.

    ⚠ WHY THIS IS NOT ONE STRING ANY MORE. The sent message asserted "An OOM cascade kills seats
    AND this watcher itself. Free the box NOW" on EVERY crossing — including a load-only one,
    where RAM is above the floor and no OOM is coming. A remedy that is wrong most of the times it
    is read costs twice: the reader who follows it acts on the wrong cause, and the reader who
    learns to discount it ignores the message that matters. The condition was already computed a
    few lines up; only the text was unconditional.

    ⚠ EVERY ARM LEADS WITH AN INSPECT MOVE, and that ordering is the rule, not the style. A remedy
    whose FIRST verb is destructive gets a seat closed on a reading nobody looked at. Closing
    comes after the census, never instead of it. No arm names a specific seat-terminating
    invocation: which pane may be closed and which may never be is 7.164's door-exemption
    question, and a second answer here would be a second home for it."""
    if mem_low and load_high:
        return ("Memory AND load both fired; MEMORY is the one that kills — an OOM cascade takes "
                "the seats AND this watcher itself, the one process that would report it. Read "
                "the box first (`free -m`, `uptime`, then the per-seat census) and treat the RAM "
                "as the emergency: close out idle/done seats, tear down leftover dead wave "
                "windows (tmux kill-window), and pause further launches until this clears. The "
                "load may well drain on its own once the memory picture is dealt with.")
    if mem_low:
        return ("An OOM cascade kills seats AND this watcher itself, the one process that would "
                "report it. Read the box first (`free -m`, then the per-seat census) to see what "
                "is holding the RAM, then free it: close out idle/done seats, tear down leftover "
                "dead wave windows (tmux kill-window), and pause further launches until this "
                "clears.")
    return ("This is LOAD, not memory: RAM is ABOVE the floor, nothing here says an OOM is "
            "coming, and no seat needs closing on this flag's account. Read what is actually "
            "running first (`uptime`, `ps` sorted by CPU) — a compile, a selftest sweep or a "
            "transcript scan is load that drains by itself. Hold further launches until it "
            "drains, and escalate only if it does not.")


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
                f"watch: {head} [{' '.join(flags)}] — {sp['avail_mb']}MB RAM available "
                f"(floor {floor}MB), load {sp['load1']}/{sp['cores']} cores. "
                f"{pressure_remedy(mem_low, load_high)}")
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


# ---------- revival detection (stage 4 §1 — the DETECTOR, s4-03) ----------
#
# THE CLASSIFIER CLAIMS NOTHING AND FORKS NOTHING. It decides WHICH seat is down and WHY; the
# marker write lives in the s4-05 block below (`claim_revival`) and the fire is still s4-06's.
# ⚠ AMENDED WHEN s4-05 LANDED: this block was "REPORT-ONLY BY CONSTRUCTION" while it was the only
# one here. It no longer is — the CRASHED branch now calls `claim_revival`, which WRITES the
# shared lifecycle marker under `coord_lock`. Everything above CRASHED is still pure
# classification, and the ordering rationale is unchanged: a mis-classification that only prints
# is cheap, actuation without the interlock double-launches, so the pieces landed in this order
# and must stay separable. NOTHING in this file forks, launches or calls tmux for a revival yet.

REVIVAL_DEBOUNCE_TICKS = 2      # consecutive NON-STALE ticks a candidate must hold before CRASHED
REVIVAL_STALE_NOTE_TICKS = 3    # consecutive stale ticks before the sensor outage is flagged once

# 7.164: consecutive passes a roster-ACTIVE row must show NO harness process before the GHOSTROW
# flag fires. DERIVED FROM `REVIVAL_DEBOUNCE_TICKS`, not written as a second `2`, and that is the
# whole point of the line: the two arms watch the SAME fact — a roster row with nothing behind it —
# from opposite sides (this one from inside the pane's process table, the revival arm from the
# roster's absence). Two independently-tuned numbers for one physical condition is a second
# debounce convention, which the row that added this was told not to introduce. Anyone who wants
# them to differ changes THIS line and says why; the default is that they cannot drift apart.
GHOSTROW_DEBOUNCE_TICKS = REVIVAL_DEBOUNCE_TICKS

# Report-line literals. Kept as constants because the acceptance controls (task s4-03 § Acceptance
# 4, 6, 8, 9) grep for the EXACT strings — a reworded line is a silently-failing control.
REVIVAL_ROOM_DEAD_LINE = "REVIVAL n/a — room dead; recovery is jobs/recover-room.py (task 7.71)"
REVIVAL_STALE_LINE = "REVIVAL paused — snapshot stale"

# ---- s4-04: the COMPLETED-ONE-SHOT gate's literals ----
#
# ⚠⚠ WAY-STATION, NOT A HOME — `decisions.md#d-watch-is-a-way-station` (owner ruling, 2026-07-29),
# and it binds every stage-4 arm in this file, this gate included. THIS FILE IS SCHEDULED FOR
# DELETION BY TASK 7.35. The gate lands here only because `watch.py` is TODAY the sole component
# observing anything at all — team-monitor is not running, the daemon's queue holds zero rows, and
# the live `goal-watcher` job has never executed once — so retiring first was impossible, not
# preferable. WHAT SUPERSEDES IT: the `goal-watcher-job` (CMP-21), consuming the same canonical
# `state.json` snapshot team-monitor (CMP-20) writes. The migration is PRE-PAID by construction:
# this gate reads the SNAPSHOT and the SEAT DESCRIPTORS only — no tmux, no /proc, no pane — so it
# moves to the job unchanged; what 7.35 rewrites is the FIRING logic and its acceptance suite, not
# the mechanism. NOTHING HERE IS PERMANENT. Do not build on it as a home, and do not defend it as
# one: an unlabelled interim mechanism is what the next reader mistakes for architecture.
REVIVAL_ONE_SHOT_LINE = "COMPLETED-ONE-SHOT — never revived"
REVIVAL_ATTEST_CMD = "coordinate attest-exit"
REVIVAL_MODE_LAYER = "revival mode gate"

# ---- s4-14: the OWNER-DOOR gate's literals ----
#
# ⚠⚠ SAME WAY-STATION CAVEAT as the s4-04 block above and it is not repeated here: task 7.35
# deletes this file into the `goal-watcher-job` (CMP-21), and this gate travels with the arm.
# Like s4-04's it reads the SNAPSHOT, the SEAT DESCRIPTORS and one coordination file — no tmux,
# no /proc, no pane — so the migration is pre-paid by construction.
#
# OWNER RULING 2026-07-30 (`decisions.md#r-door-revival-follows-owner-state`): the revival arm
# revives the OWNER DOOR only while the owner's declared state is `present` or `reachable`, and
# NEVER while it is `afk`.
REVIVAL_DOOR_STATES = ("present", "reachable")
REVIVAL_DOOR_LINE = "DOOR HELD SHUT — owner state does not admit a revival"
REVIVAL_DOOR_LAYER = "revival owner-door gate"


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


# ---------- revival CLAIM (stage 4 §2 — THE NO-DOUBLE-LAUNCH INTERLOCK, s4-05) ----------
#
# IT CLAIMS; IT DOES NOT FIRE. The critical section ends with a written claim and a released lock.
# No fork, no launch, no tmux call exists anywhere below — s4-06 owns actuation.
#
# ⚠ THE FLOCK IS THE MUTEX; THE WRITE IS NOT. Stage 3's marker is ONE SHARED FILE keyed by seat
# (`coord.py` § STAGE 3 block, `lifecycle_path` at :3600), so there is no per-seat create-exclusive
# to hold and `O_EXCL` is neither available nor needed. `coord.atomic_write` is `os.replace`
# (:517) — atomic PER WRITE, which `save_state` above already states "is not the same as safe
# under two writers". Two claimers that both read "no entry" and both write produce TWO
# successors. The exclusion comes from `coord.coord_lock` (:534) and from nothing else. Do not
# "simplify" the critical section away.
#
# ⚠⚠ `coord_lock` IS NOT RE-ENTRANT, SO THIS CODE CANNOT CALL STAGE 3'S WRITERS. MEASURED, not
# assumed: `coord_lock` opens a FRESH handle on `{base}/.lock` on every entry (:545), and
# `flock(LOCK_EX)` on a second open file description BLOCKS against the one the same process
# already holds. A nested `with coord.coord_lock(base)` under a 5 s SIGALRM deadlocked on the
# inner `with` against the live coord.py (s4-05 probe, 2026-07-29). Every Stage 3 writer —
# `stamp_lifecycle` (:3648), `append_lifecycle_step` (:3681), `finish_lifecycle` (:3703),
# `clear_lifecycle` (:3729) — takes `coord_lock` ITSELF, so calling one from inside this critical
# section would hang the watch loop forever: a monitor dying of its own bookkeeping, with no
# timeout anywhere to notice. THEREFORE the claim performs the read-modify-write HERE, under the
# ONE outer lock, in `_write_lifecycle`'s exact byte format (:3645) — the identical shape
# `set_awaiting` (:3321) performs one file over. That format coupling is REAL and is asserted in
# the selftest against `coord._write_lifecycle`'s own bytes rather than trusted.
#
# ⚠ WHICH PREDICATE GOVERNS WHICH BRANCH — and why the two never disagree in a way that acts.
# Two liveness readings are in play and they are deliberately not the same call:
#   · `coord.ident_is_live_process((pid, starttime))` (:1629) — PLAIN process identity, the "pair
#     gone" half of the identity table. It has NO "cannot tell" state: any unreadable /proc entry
#     is False. NEVER `ident_is_live_harness` — the executor is a PYTHON process and that
#     predicate matches only claude/codex/opencode basenames, so it reports every live executor
#     DEAD and turns MID-RENEWAL into CRASHED (`_executor_ident_live` above carries the same note).
#   · `coord.lifecycle_stale(entry)` (:3762) — Stage 3's FAILED-RENEWAL predicate, the conjunction
#     `in-flight AND age > LIFECYCLE_STALE_MIN AND NOT ident_is_live_process`. It, and only it,
#     authorises the re-claim.
# They agree because conjunct 3 of `lifecycle_stale` IS the same `ident_is_live_process` call on
# the same `lifecycle_ident`-normalized pair. Where they can diverge is the case Stage 3 documents
# as its fail-safe cost: an `in-flight` entry whose executor ident is MISSING or MALFORMED is
# `lifecycle_stale() == False` FOREVER. That case lands in the stand-down branch here too — the
# claim never fires on it — and is made LOUD instead, because silence is what would let a claim
# nobody will ever execute hold a seat down permanently.
#
# ⚠ NO TTL, NO TIMEOUT, NO "PROBABLY DEAD" HEURISTIC. Age is read ONLY to decide whether to SPEAK
# (the two loud notes below); it never authorises an act on its own. Identity or nothing.

REVIVAL_CLAIM_LAYER = "revival claim gate"


def _claim_note(room, notes, seat, kind, body):
    """Push ONE note per (seat, kind) per episode. Returns True when it actually pushed.

    ⚠ R-8: THE LAYER STRING LEADS THE BODY. Every body passed here begins literally with its own
    gate's layer constant — `REVIVAL_CLAIM_LAYER` for the claim path, `REVIVAL_MODE_LAYER` for
    s4-04's mode gate — so `note.startswith(...)` is a true assertion and a reader cannot
    mistake this TOOL GATE's refusal for the harness permission classifier's — the same bar s4-12
    row 5 asserts. Re-arms where every other revival counter re-arms: when the seat is seen LIVE
    again (`check_revival` step 3 clears both)."""
    seen = room.setdefault("claim_notes", {})
    key = f"{seat}\t{kind}"
    if seen.get(key):
        return False
    seen[key] = True
    notes.append(Flag(seat, body))
    return True


def _claim_record(disposition, pane, attempts):
    """The per-seat record this claim writes. STAGE 3 OWNS THIS SCHEMA (coord.py § STAGE 3 block);
    this consumes it and defines nothing — not the path, not the field set, not the staleness
    constant.

    `caller` goes through `coord.lifecycle_ident` rather than being hand-shaped: Stage 3's block
    records that a `(pid, starttime)` TUPLE written straight through makes every live ident read
    as dead. `disposition` is stored AS GIVEN (`"revive"` for this path) — s3-03's semantics.

    `executor` IS DELIBERATELY ABSENT. No executor process exists at claim time; s4-06 forks it and
    Stage 3's `stamp_lifecycle` writes the real ident. A placeholder here would be a claim about a
    process that does not exist, and every reader of this file treats `executor` as an assertion.

    `attempts` counts the claims THIS one supersedes: 0 on a fresh claim, prior+1 on a re-claim of
    a void entry, and it passes an existing count through unchanged when claiming over a terminal
    entry. ⚠ s4-07/s4-12 drive a retry/abandon ladder ("after 3 attempts → abandoned") over this
    same marker; whether that ladder reuses this field or adds its own is THEIR ruling, not this
    task's. Read this docstring before assuming the counter means fires."""
    return {"disposition": str(disposition),
            "state": "in-flight",
            "caller": coord.lifecycle_ident((os.getpid(), coord.proc_stat(os.getpid())[1])),
            "pane": pane or "",
            "stamped-at": coord.now(),
            "steps-completed": [],
            "failure": "",
            "attempts": int(attempts)}


def claim_revival(base, seat, pane, notes, room, disposition="revive"):
    """THE INTERLOCK. Claim `seat`'s lifecycle-marker entry, or stand down. NEVER raises, NEVER
    fires. Returns `(outcome, why)`:

        "CLAIMED"     the entry is ours — s4-06 may fire on this and ONLY this
        "RE-CLAIMED"  a VOID claim (executor died mid-flight) was superseded; ours, attempts+1
        "STOOD-DOWN"  another path owns this seat's next act. Not an error, not a failure
        "REFUSED"     the interlock could not be honoured. FAIL CLOSED — never fire on this

    Only the first two authorise a launch, and s4-06 MUST branch on the string rather than on
    "did it not refuse": a stand-down and a refusal are different facts with the same consequence
    today and different consequences the moment anyone adds a retry.

    THE CRITICAL SECTION, in order, all of it under ONE `coord.coord_lock(base)`:
      0. the lock itself — `held is False` REFUSES (see below);
      1. re-read the LIVE roster (`coord.load_workers`) — race cover 1;
      2. re-read `closing.json`, `awaiting-close.json` and `lifecycle-inflight.json`;
      3. the identity table over an `in-flight` entry — race cover 2;
      4. read-modify-write our entry;
    then release. The fork happens after the lock is gone, in s4-06.

    ⚠ STEP 0 IS FAIL-CLOSED AND THAT IS THE WHOLE POINT. `coord_lock` yields False and proceeds
    LOCKLESS on a package it cannot lock (its docstring: "a sandboxed seat whose package is
    read-only (codex EROFS) cannot take the lock, so it proceeds WITHOUT it after one note"). For
    every other caller that degradation is correct — a message still gets sent. Here the lock is
    the ONLY mutex, so a lockless claim IS the double-launch risk itself. It refuses, prints, and
    notes once. A relaunch that races is worse than a seat that stays down and says so.

    ⚠ TWO INDEPENDENT RACE COVERS, and the acceptance disables one at a time because two covers
    tested together prove neither:
      · cover 1 — `cmd_close_seat` flips the roster row to `active: no` BEFORE killing the pane, so
        the IN-SECTION roster re-read reads CLEANLY-OUT even if the marker were somehow missed;
      · cover 2 — Stage 3's caller stamps the marker BEFORE forking ("so a marker with no executor
        pid is impossible"), so an in-flight entry with a live executor reads MID-RENEWAL.
      ⚑ COVER 1 IS THE ONE THAT ACTUALLY EXCLUDES A NORMAL RENEWAL, and this is worth stating
      plainly rather than leaving for the next reader to discover: `stamp_lifecycle` writes
      `data[seat] = rec` UNCONDITIONALLY — it does not check for an existing entry — so the marker
      alone gives no mutual exclusion against Stage 3's caller. The marker excludes a second
      REVIVAL claim (both go through this check-then-write under the same lock); the ROSTER
      re-read is what excludes a renewal. Removing either cover leaves a real hole.

    ⚠ THE MARKER IS READ WITH `_strict_ledger`, NOT `coord.load_lifecycle`, and the substitution is
    deliberate: `load_lifecycle` collapses an unreadable file to `{}` — "no entry" — which INSIDE
    this critical section would mean writing a claim over a marker that may hold a live renewal.
    Same inversion, same reason, as the detector's own ledger reads. On any parseable input the two
    return the identical dict, and the selftest asserts BOTH halves of that (agree when parseable,
    disagree when not) so the substitution can never become silent."""
    lifecycle = coord.lifecycle_path(base)
    try:
        with coord.coord_lock(base) as held:
            # ---- 0. FAIL CLOSED on a lock we do not actually hold ----
            if not held:
                _claim_note(room, notes, seat, "lockless",
                            f"{REVIVAL_CLAIM_LAYER}: coordination lock unavailable — '{seat}' is "
                            f"classified CRASHED but the revival claim REFUSES to proceed. "
                            f"coord_lock degraded to lockless under {base} (a read-only or "
                            f"sandboxed package), and with a SHARED marker file that lock is the "
                            f"only mutex there is: a lockless claim would race a concurrent "
                            f"renewal and produce two successors for one seat. Nothing was "
                            f"written and nothing will be launched while this holds. Fix the "
                            f"package's writability. (This is the revival claim gate refusing, "
                            f"not the harness permission classifier.)")
                return "REFUSED", "lock unavailable — fail-closed, no claim written"

            # ---- 1. LIVE roster re-read — race cover 1 ----
            _, _, live_rows = coord.load_workers(base)
            r = {row.get("agent"): row for row in live_rows}.get(seat)
            if r is None or r.get("active") != "yes":
                return "STOOD-DOWN", ("CLEANLY-OUT (cover 1: roster row "
                                      f"{'absent' if r is None else 'not active'} at claim time)")

            # ---- 2. ledgers, re-read INSIDE the section ----
            awaiting, awaiting_st = _strict_ledger(coord.awaiting_path(base))
            closing, closing_st = _strict_ledger(coord.closing_path(base))
            marker, marker_st = _strict_ledger(lifecycle)
            bad = [n for n, s in (("closing.json", closing_st),
                                  ("awaiting-close.json", awaiting_st),
                                  ("lifecycle-inflight.json", marker_st)) if s == "unparseable"]
            if bad:
                # The detector refuses on this before it ever reaches CRASHED, so arriving here
                # means a ledger became unreadable BETWEEN that read and this one. Rare, and
                # exactly the moment to be loudest.
                _claim_note(room, notes, seat, "ledger",
                            f"{REVIVAL_CLAIM_LAYER}: ledger unreadable inside the critical "
                            f"section — {', '.join(bad)} under {base} parsed for the detector and "
                            f"NOT for the claim, so it changed under the lock. '{seat}' is "
                            f"classified CRASHED and the claim REFUSES: a claim written over a "
                            f"marker that cannot be read may overwrite a live renewal. Nothing "
                            f"was written. (This is the revival claim gate refusing, not the "
                            f"harness permission classifier.)")
                return "REFUSED", f"ledger unparseable inside the lock ({', '.join(bad)})"
            if seat in awaiting:
                return "STOOD-DOWN", "CLEANLY-OUT (in awaiting-close.json at claim time)"
            if seat in closing:
                return "STOOD-DOWN", "MID-CLOSE (in closing.json at claim time)"

            # ---- 3. the identity table — race cover 2 ----
            entry = marker.get(seat)
            entry = entry if isinstance(entry, dict) else None
            attempts = int(entry.get("attempts") or 0) if entry else 0
            if entry is not None and entry.get("state") == "in-flight":
                ident = coord.lifecycle_ident(entry.get("executor"))
                alive = bool(ident) and coord.ident_is_live_process(
                    (ident["pid"], ident["starttime"]))
                age = coord.lifecycle_age_min(entry)
                past = age is not None and age > coord.LIFECYCLE_STALE_MIN
                void = coord.lifecycle_stale(entry)          # THE governing predicate for a re-claim
                if alive and not past:
                    # (a) executor pair ALIVE, young — MID-RENEWAL. Stand down, no note: this is
                    # the healthy case and a note every tick would train the room to ignore them.
                    return "STOOD-DOWN", ("MID-RENEWAL (cover 2: executor pid "
                                          f"{ident['pid']} alive, {age} min)")
                if alive:
                    # (b) executor pair ALIVE but past the staleness bound. A SEPARATE loud note,
                    # and it NEVER authorises a re-fire — a slow executor is still an executor,
                    # and identity says it is there.
                    _claim_note(room, notes, seat, "stale-alive",
                                f"{REVIVAL_CLAIM_LAYER}: an in-flight lifecycle claim on '{seat}' "
                                f"is {age} min old, past LIFECYCLE_STALE_MIN "
                                f"({coord.LIFECYCLE_STALE_MIN}), AND ITS EXECUTOR IS ALIVE (pid "
                                f"{ident['pid']}). The seat is roster-absent while a live process "
                                f"holds its renewal, so the renewal is stuck, not dead. NOTHING "
                                f"IS RELAUNCHED ON THIS — identity says the executor is there, "
                                f"and a relaunch would double-launch the seat. Inspect pid "
                                f"{ident['pid']} and its log; kill it deliberately if it is "
                                f"wedged, and the next tick will re-claim. (This is the revival "
                                f"claim gate reporting, not the harness permission classifier.)")
                    return "STOOD-DOWN", (f"STALE-BUT-ALIVE (executor pid {ident['pid']} alive at "
                                          f"{age} min > {coord.LIFECYCLE_STALE_MIN}); no re-fire")
                if void:
                    # (c) pair GONE and past the bound: the executor died mid-flight, so the claim
                    # is VOID and ours supersedes it with attempts+1.
                    attempts = attempts + 1
                    _claim_note(room, notes, seat, "void",
                                f"{REVIVAL_CLAIM_LAYER}: a VOID lifecycle claim on '{seat}' was "
                                f"superseded — its executor (pid {ident['pid']}) is GONE and the "
                                f"entry is {age} min old, past LIFECYCLE_STALE_MIN "
                                f"({coord.LIFECYCLE_STALE_MIN}). That renewal died mid-flight "
                                f"without reporting an ending, so the seat is neither alive nor "
                                f"closed. The revival claim now holds the seat (attempt "
                                f"{attempts}); the previous executor's steps-completed list is "
                                f"the record of how far it got and is being overwritten — read "
                                f"it in the run's transcript if this recurs. (This is the revival "
                                f"claim gate acting, not the harness permission classifier.)")
                    marker[seat] = _claim_record(disposition, pane, attempts)
                    ok, why = _write_claim(lifecycle, marker, room, notes, seat)
                    return ("RE-CLAIMED", f"void claim superseded, attempts={attempts}") if ok \
                        else ("REFUSED", why)
                # (d) pair GONE (or the ident is unresolvable) and NOT void. Stand down.
                if past:
                    # The Stage 3 fail-safe made visible: an in-flight entry with a missing or
                    # malformed executor ident is `lifecycle_stale() == False` FOREVER, so nothing
                    # here or in `sweep_lifecycle` will ever clear it and this seat can never be
                    # revived again. Our OWN fresh claim has exactly this shape (no executor until
                    # s4-06 forks one), so this note is also the alarm for "the claim landed and
                    # nothing ever fired it".
                    _claim_note(room, notes, seat, "unresolvable",
                                f"{REVIVAL_CLAIM_LAYER}: an in-flight lifecycle claim on '{seat}' "
                                f"is {age} min old, past LIFECYCLE_STALE_MIN "
                                f"({coord.LIFECYCLE_STALE_MIN}), and its executor ident is "
                                f"{'MISSING' if not ident else 'UNRESOLVABLE'} — so Stage 3's "
                                f"staleness predicate answers NOT-STALE for it permanently and "
                                f"NOTHING WILL EVER CLEAR OR SUPERSEDE IT, here or at close-run. "
                                f"The seat stays down and cannot be re-claimed. Either a revival "
                                f"claim was written and never fired, or an executor died before "
                                f"stamping its ident. A HUMAN MUST CLEAR THE ENTRY for '{seat}' "
                                f"in {lifecycle}. (This is the revival claim gate reporting, not "
                                f"the harness permission classifier.)")
                    return "STOOD-DOWN", (f"IN-FLIGHT, executor ident unresolvable at {age} min — "
                                          f"not stale by construction, no re-claim possible")
                return "STOOD-DOWN", (f"IN-FLIGHT, executor gone but only {age} min old — under "
                                      f"LIFECYCLE_STALE_MIN ({coord.LIFECYCLE_STALE_MIN}); "
                                      f"identity, not a TTL, decides and it says wait")

            # ---- 4. no entry, or a TERMINAL one (done/FAILED): the claim is ours ----
            # ⚠ s4-05 LEFT THIS EXACT GATE FOR s4-07 AND s4-07 HAS NOW ADDED IT. Its words: "the
            # moment s4-07 introduces a state that means DO NOT RETRY, this line will happily claim
            # over it and restart the ladder forever." `abandoned` IS that state. The check-then-
            # write is inside the SAME critical section as everything else here, so a concurrent
            # ladder write cannot slip an abandonment in between the read and the claim.
            if isinstance(entry, dict) and entry.get("state") == "abandoned":
                return "REFUSED", ("ABANDONED — the RAM-floor ladder exhausted its attempts for "
                                   "this episode; claiming over it would restart the ladder "
                                   "forever (s4-07)")
            marker[seat] = _claim_record(disposition, pane, attempts)
            ok, why = _write_claim(lifecycle, marker, room, notes, seat)
            return ("CLAIMED", f"disposition={disposition}, attempts={attempts}"
                    + ("" if entry is None else f" (over a state={entry.get('state')!r} entry)")) \
                if ok else ("REFUSED", why)
    except (OSError, ValueError, TypeError) as exc:
        # A monitor must never die of its own bookkeeping — but it must never call a failure a
        # stand-down either. REFUSED is the fail-closed word and s4-06 will not fire on it.
        _claim_note(room, notes, seat, "broke",
                    f"{REVIVAL_CLAIM_LAYER}: the revival claim for '{seat}' BROKE ({exc!r}) — no "
                    f"claim was written and nothing will be launched. The seat stays down. (This "
                    f"is the revival claim gate failing, not the harness permission classifier.)")
        return "REFUSED", f"claim raised {exc!r}"


def _write_claim(lifecycle, marker, room, notes, seat):
    """The read-modify-write's WRITE half, in `coord._write_lifecycle`'s exact byte format.

    ⚠ `marker` IS THE WHOLE FILE, mutated in place by the caller — never `{seat: record}`. A
    whole-file write here would silently drop every other seat's entry, which is the acceptance's
    own red arm. Called ONLY from inside the held lock."""
    try:
        coord.atomic_write(lifecycle, json.dumps(marker, indent=2, sort_keys=True) + "\n")
        return True, ""
    except (OSError, ValueError, TypeError) as exc:
        _claim_note(room, notes, seat, "write",
                    f"{REVIVAL_CLAIM_LAYER}: the lifecycle marker write for '{seat}' FAILED "
                    f"({exc!r}) — the claim does NOT hold and nothing will be launched. A claim "
                    f"that cannot be recorded is not a claim. (This is the revival claim gate "
                    f"failing, not the harness permission classifier.)")
        return False, f"marker write failed: {exc!r}"


# ---------- revival ACTUATION (stage 4 §3 — THE FIRE, s4-06) ----------
#
# ⚠⚠ WAY-STATION, NOT A HOME — `decisions.md#d-watch-is-a-way-station` (owner ruling, 2026-07-29).
# THE CODE BELOW IS THE ONE ACT IN THIS ENTIRE FILE THAT CHANGES THE ROOM, and it is a way-station
# all the same. The s4-04 literals block above carries the ruling and the ground in full and is NOT
# restated here; what is SPECIFIC TO THIS ARM is the migration cost, and it is WORSE than the
# detector's, so read this before assuming 7.35 inherits a free move:
#   · the DETECTOR moves to the `goal-watcher-job` (CMP-21) UNCHANGED — it reads the snapshot and
#     the descriptors and nothing else;
#   · THIS ARM DOES NOT. `revival_fork_target` calls tmux directly (`coord.live_panes`,
#     `coord.tmux_pane_window_name`, `coord.tmux_find_window_pane`) and the fire calls
#     `subprocess.Popen`. A daemon-fired job has NEITHER `TMUX` NOR `TMUX_PANE` — which is the
#     precise hazard `jobs/recover-room.py:12-19` measured — so 7.35 rewrites the FIRING logic and
#     its whole acceptance suite, not just its host. NOTHING HERE IS PERMANENT AND NOTHING HERE IS
#     PRE-PAID. Do not build a second caller on it, and do not defend it as architecture.
#
# ⚠ NO AGENT IS IN THIS PATH, AND THAT IS THE RULING, NOT AN IMPLEMENTATION CHOICE.
# `decisions.md#d-cos-may-launch` bars EVERY agent from the terminating acts — close, renew, reap,
# kill, revive — and continues that those acts belong to topic-1's detached executor and stage-4's
# revival arm. So this fires CODE: a `subprocess.Popen` of coord.py's hidden `lifecycle-exec`
# subcommand. It never sends a prompt, never launches a seat, and never asks a seat to act.
#
# ⚠ THE EXIT CONTRACT IS THE EXECUTOR'S AND THIS ARM MUST NOT COLLAPSE IT. 2 = a GUARD refused the
# invocation (all five of `s3-09`'s refuse-to-fork arms exit 2 and all say "YOUR CHECKOUT STANDS");
# 3 = the guards passed and the SEQUENCE broke; 0 = completed. The fork is detached, so this loop
# never sees the code — it is read off the marker (`state` FAILED + `failure`) and off the log,
# which is why the log path is recorded in the marker rather than left to be guessed.
#
# ⚠ WE DO NOT REUSE `coord.fork_lifecycle_renewal`, AND THE REASON IS MEASURED, NOT STYLISTIC.
# That function hard-codes `--disposition renew` and `--handoff-written 1` (coord.py:4744/4752) and
# lives behind a SEAT's own checkout. A revival needs `revive` + `--handoff-written 0`, and
# `coord.py` is under another custody. Widening that function is a Stage 3 change, not a watch one.
#
# ⚠⚠ THE EXECUTOR'S (pid, starttime) IS **NOT** WRITTEN HERE, AND THE TASK TEXT ASKING FOR IT IS
# WRONG ON THE MEASUREMENT. `s4-06` § Detachment says "record the executor's (pid, starttime) into
# the marker entry after the fork". IT CANNOT BE DONE FROM HERE AND IT MUST NOT BE FAKED:
#   (a) MEASURED 2026-07-29 — `subprocess.Popen(["setsid", python, …], start_new_session=True)`
#       returns the pid of the `setsid` BINARY, which double-forks (Python already made the child a
#       session leader, so util-linux `setsid`'s own `setsid()` fails and it forks); the real
#       executor's pid was `Popen.pid + 1` and IS NOT KNOWABLE from the parent. Writing `Popen.pid`
#       would write a DEAD pid into a field every reader treats as an assertion that a process is
#       there — `_executor_ident_live` above and `coord.lifecycle_stale` both key on it.
#   (b) THE CHILD ALREADY WRITES IT, correctly, as its first act: `cmd_lifecycle_exec` guard 5
#       stamps `executor: (os.getpid(), proc_stat(os.getpid())[1])` (coord.py, § STAGE 3). That is
#       WHY `_claim_record` above leaves `executor` deliberately absent.
# So the ident lands in the marker from the CHILD, and `s4-05`'s next-tick MID-RENEWAL check gets
# exactly the ident it needs — one writer, one home (PRIN-11). What this arm records instead is its
# OWN evidence: the log path and the target it computed, on the entry, before the fork.

REVIVAL_FIRE_LAYER = "revival fire gate"


def revival_fork_target(args, snap, seat, pane):
    """(target, why) — the tmux target for a revival fork. `("", why)` means REFUSE, NEVER FIRE.

    ⚠⚠ AN EMPTY TARGET IS THE FAILURE MODE THIS FUNCTION EXISTS FOR, quoted from
    `jobs/recover-room.py:12-19`: *"it would not fail, it would guess"* — `launch` resolves its
    target as `COORD_LAUNCH_TARGET or TMUX_PANE`, a daemon-fired exec has neither, and tmux
    resolves an EMPTY target to the MOST RECENT session, measured to be the LIVE room. *"A recovery
    that opens agents into the live room believing it is repairing a dead one is worse than no
    recovery at all."* So this returns "" and the caller refuses; it never hands "" downward.

    The four steps are stage-4 §3's, in order:
      1. the seat's DESCRIPTOR, through `coord.discover_workers` — the ONE parser of a descriptor's
         frontmatter (a second regex here would be a second opinion, PRIN-11) — then
         `coord.seat_placement`, which reads the `window:` key;
      2. pane LIVE **and** `coord.renew_in_place(...)` true -> the pane ITSELF. In-place respawn,
         window layout intact (G-12);
      3. pane DEAD (or live but in the wrong window) -> RE-PLACE onto an anchor: the first pane of
         the declared window in the room's own session, else any pane the snapshot places in that
         session which tmux still knows. `launch_seat` derives the session from the anchor;
      4. nothing resolves -> "" and the caller refuses LOUDLY (R-8). `args.force` is never set, so
         `launch_seat`'s window-drift check still runs downstream — a drift refusal is a LOUD
         REFUSAL, never a reason to reach for `--force`.

    ⚠ THE SNAPSHOT SUPPLIES THE SESSION, NOT tmux. `state.json` carries ONE `session` for the room
    (team-monitor writes it), so "a pane the snapshot places in that session" is simply a pane on a
    snapshot row: there is exactly one room per snapshot. Re-deriving the session from tmux would
    give one fact a second home AND could name a DIFFERENT room than the one being observed."""
    decl = None
    for w in coord.discover_workers(coord.workers_dir(args)):
        if w.get("agent") == seat:
            decl = w
            break
    if decl is None:
        return "", (f"no descriptor under {coord.workers_dir(args)} carries `agent: {seat}`, so "
                    f"the seat declares no placement and no target can be computed")
    _, wname = coord.seat_placement(decl)
    panes = coord.live_panes()
    pane = (pane or "").strip()
    if pane and pane in panes:
        if coord.renew_in_place(decl, pane, True, coord.tmux_pane_window_name(pane)):
            return pane, (f"pane {pane} is LIVE and already sits in the window its descriptor "
                          f"names, so the successor respawns IN PLACE and the layout survives "
                          f"(G-12)")
        why = (f"pane {pane} is live but is NOT in the window {wname!r} its descriptor declares, so "
               f"this revival is also the act that moves the seat where it belongs")
    else:
        why = (f"pane {pane or '<none recorded>'} is not among the {len(panes)} pane(s) tmux "
               f"currently knows")
    session = str((snap or {}).get("session") or "")
    anchor = coord.tmux_find_window_pane(session, wname) if (session and wname) else ""
    if anchor:
        return anchor, (f"{why}; RE-PLACING onto anchor {anchor} — the first pane of window "
                        f"{wname!r} in session {session!r}")
    for row in ((snap or {}).get("seats") or []):
        p = str(row.get("pane") or "").strip()
        if p and p in panes:
            return p, (f"{why}; window {wname!r} does not exist in session {session!r}, so the "
                       f"anchor is {p} — a live pane the snapshot places in this room's session, "
                       f"from which `launch_seat` derives the session for a new window")
    return "", (f"{why}; `tmux_find_window_pane({session!r}, {wname!r})` MISSED and NO pane the "
                f"snapshot places in that session is live. NO ANCHOR RESOLVES — refusing rather "
                f"than passing an empty target down")


def revival_fork_argv(args, seat, pane, target):
    """The EXACT argv of the detached fire. Pure, so the acceptance can grep it without forking.

    `--handoff-written 0` and it is DELIBERATE, not an omission: a crashed session had no turn
    boundary at which to write a handoff block, so requiring one would make revival impossible in
    exactly the case revival exists for (`stage-3-executor-spec.md` delta 1, and `cmd_lifecycle_exec`
    keys its re-read on `renew` for the same reason). The predecessor's last UNREAD block stays
    exactly where it is and is delivered at the successor's `checkin`, keyed on `(seat, unread)` and
    never on author. NOTHING ON THIS PATH READS OR WRITES `memory.md` — R-14.

    NO `--force` AND NO `--force-memory`. `lifecycle-exec` does not even accept them (verified
    against the built parser in the acceptance), and `--force` carries the ROLE gate ALONE
    (`coord.GATE_FLAGS`) — it would not lift a memory or a window-drift refusal even if it were
    passed. `args.force` is likewise never set, so `launch_seat`'s window-drift check runs."""
    return ["setsid", sys.executable, str(Path(coord.__file__).resolve()), "lifecycle-exec",
            "--package", str(coord.package_dir(args)),
            "--seat", seat,
            "--disposition", "revive",
            "--pane", str(pane or ""),
            "--tmux-target", target,
            "--caller-pid", str(os.getpid()),
            "--caller-starttime", str(coord.proc_stat(os.getpid())[1]),
            "--handoff-written", "0"]


def revival_child_env():
    """The forked child's environment — `coord.LIFECYCLE_SCRUB_ENV` REMOVED, everything else kept.

    ⚠ A DENYLIST, AND IT MUST STAY ONE. `TMUX_TMPDIR` survives into the child and is LOAD-BEARING:
    an acceptance room on a private tmux socket is reachable only through it. Narrowing this to an
    allowlist would make every fire land on the default server.

    ⚠ WHY THE SCRUB AT ALL, in this file's own measured words (`watch.py:943-975`): *"a detached
    loop INHERITS `TMUX_PANE` from whatever shell started it"*, and every send was refused with
    "you claimed 'watcher', but this pane (%145) is registered to 'chief-of-staff'". The executor
    pops the same four names AGAIN at entry (`cmd_lifecycle_exec` guard 1); the redundancy is
    deliberate, so a caller that forgets is still caught by the child."""
    return {k: v for k, v in os.environ.items() if k not in coord.LIFECYCLE_SCRUB_ENV}


def fire_revival(args, base, snap, seat, pane, notes, room):
    """FORK the detached revival executor for `seat`. Returns `(outcome, why)`. NEVER raises.

        "FIRED"      the executor is running detached; its evidence path is in `why`
        "NO-TARGET"  no tmux target resolved — nothing was forked, and a note names the layer
        "REFUSED"    an identity or a log the fork needs could not be obtained; nothing was forked
        "BROKE"      the fork itself failed; nothing is running

    ONLY "FIRED" means a successor is coming. The three others are different facts and the caller
    must not collapse them into "not fired" — that is the same discipline `claim_revival` states for
    STOOD-DOWN vs REFUSED.

    ⚠ stdout/stderr GO TO A FILE, NEVER `DEVNULL`, and the child READS THE PATH BACK off
    `/proc/self/fd/1` (`coord.inherited_log_path`, guard 5) rather than recomputing a name — that is
    what guarantees ONE stamp per run. So the caller MUST open the log; a fork without one is a
    detached process whose output is lost, which this room has already paid for once.

    ⚠ THE MARKER IS NOT RE-WRITTEN HERE. `claim_revival` wrote the entry that authorises this fire;
    the CHILD overwrites it wholesale at guard 5 (`stamp_lifecycle` does `data[seat] = rec`). A
    write from here would race that, and the two would disagree about which process holds the seat.
    What this function records is `log` and `tmux-target` on the entry BEFORE the fork, so a fire
    that never reaches the child still leaves evidence of where it was aimed."""
    target, why_t = revival_fork_target(args, snap, seat, pane)
    if not target:
        _claim_note(room, notes, seat, "no-target",
                    f"{REVIVAL_FIRE_LAYER}: '{seat}' is CRASHED and CLAIMED, but NO tmux target "
                    f"could be computed — {why_t}. NOTHING WAS FORKED. This arm refuses rather "
                    f"than passing an empty target down: with no target tmux resolves to the MOST "
                    f"RECENT session, measured to be the LIVE room, and opening a successor into "
                    f"the wrong room is worse than not opening one. The claim stands on disk and "
                    f"the next tick will retry once a target exists; if the whole room is gone, "
                    f"that is jobs/recover-room.py's (task 7.71), not this arm's. (This is the "
                    f"revival fire gate refusing, not the harness permission classifier.)")
        return "NO-TARGET", why_t
    if not str(coord.proc_stat(os.getpid())[1] or ""):
        _claim_note(room, notes, seat, "no-ident",
                    f"{REVIVAL_FIRE_LAYER}: this loop cannot read its own /proc/{os.getpid()}/stat, "
                    f"so it has no (pid, starttime) pair to hand the executor as `--caller-pid` / "
                    f"`--caller-starttime`. The PAIR is what lets the executor tell 'my caller "
                    f"exited' from 'a recycled pid landed on its number'; a pid alone is not an "
                    f"identity. NOTHING WAS FORKED for '{seat}'. (This is the revival fire gate "
                    f"refusing, not the harness permission classifier.)")
        return "REFUSED", "the loop cannot read its own /proc stat — no caller identity to hand over"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path(base) / f"lifecycle-exec-{seat}-{stamp}.log"
    argv = revival_fork_argv(args, seat, pane, target)
    try:
        handle = open(log_path, "ab")
    except OSError as exc:
        _claim_note(room, notes, seat, "no-log",
                    f"{REVIVAL_FIRE_LAYER}: the executor log {log_path} could not be opened "
                    f"({exc!r}), so '{seat}' was NOT revived. A detached executor whose output goes "
                    f"nowhere is the exact failure this room has already paid for once, so it is "
                    f"not started at all. (This is the revival fire gate refusing, not the harness "
                    f"permission classifier.)")
        return "REFUSED", f"executor log {log_path} could not be opened ({exc!r})"
    # Evidence BEFORE the fork, so a fire that never reaches the child still says where it was
    # aimed. Best-effort by design: a monitor must never die of its own bookkeeping, and the fire
    # is authorised by the claim that is already on disk, not by this annotation.
    _annotate_claim(base, seat, {"tmux-target": target, "log": str(log_path)})
    try:
        subprocess.Popen(argv, stdout=handle, stderr=handle,
                         start_new_session=True, env=revival_child_env())
    except OSError as exc:
        handle.close()
        _claim_note(room, notes, seat, "fork",
                    f"{REVIVAL_FIRE_LAYER}: the detached revival executor for '{seat}' could NOT "
                    f"be spawned ({exc!r}) — nothing is running and the seat stays down. The "
                    f"marker still reads in-flight from the claim; it will go stale and be "
                    f"re-claimed by identity, never by a timeout. (This is the revival fire gate "
                    f"failing, not the harness permission classifier.)")
        return "BROKE", f"the fork failed ({exc!r})"
    handle.close()
    return "FIRED", f"target {target} ({why_t}); evidence {log_path}"


def _annotate_claim(base, seat, fields):
    """Merge `fields` into `seat`'s EXISTING marker entry, under the lock, in coord's byte format.

    ⚠ MERGE, NEVER REPLACE, and never CREATE. An absent entry is answered False rather than written:
    an annotation about a claim this file never saw made would be a claim, and the only thing that
    may make one is `claim_revival` under its own critical section. Returns True/False, never raises
    — this is bookkeeping ABOUT a lifecycle act and must not be able to break the act."""
    try:
        with coord.coord_lock(base) as held:
            if not held:
                return False
            data, status = _strict_ledger(coord.lifecycle_path(base))
            entry = data.get(seat)
            if status != "ok" or not isinstance(entry, dict):
                return False
            entry.update({k: str(v) for k, v in fields.items()})
            data[seat] = entry
            coord.atomic_write(coord.lifecycle_path(base),
                               json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError, TypeError):
        return False


# ---------- the RAM-floor LOUD-REFUSAL PATH (stage 4 §4 — s4-07) ----------
#
# ⚠⚠ WAY-STATION, NOT A HOME — `decisions.md#d-watch-is-a-way-station`. The ladder below is the
# stage-4 arm's RESPONSE half and it is deleted into the `goal-watcher-job` (CMP-21) by task 7.35
# with everything else in this region. Its migration cost sits between the detector's and the
# fire's: it reads the marker and the run's `budget.json` and calls no tmux — but it reads
# `/proc/self/cmdline` for the loop's OWN warn floor, and "the loop" is a different process in the
# job. NOTHING HERE IS PERMANENT.
#
# ⚠⚠ ONE GATE, IN ONE PLACE, AND IT IS **NOT HERE**. The RAM measurement is the EXECUTOR's
# (`coord.lifecycle_memory_gate`), fired before its relaunch step and retried on its own bounded
# schedule. STAGE 4 DOES NOT RE-MEASURE — a second gate is a second home for the bar, which is the
# exact defect `r-bar-home-is-the-run-budget-json` exists to end. What this owns is the LOUD-REFUSAL
# PATH: it reads the marker's `state`/`failure` and drives retry, escalation, abandonment and
# reporting. If you find yourself about to call `coord.memory_gate` or `coord.available_mb` from
# this file, stop: you are building the second gate.
#
# ⚠ NO POLICY NUMBER CROSSES INTO THIS PATH FROM ARGV OR ENV (R-10, `r-floor-single-source`:
# "argv is a copy; a file is a reference"). The floor is READ, per act, from the run's own
# `budget.json`, through `budget.floor_source(run_root, "refuse", None)` — the SAME call the
# executor makes — and it is read ONLY TO REPORT IT, never to decide anything. `read_floor` has no
# `default=` parameter deliberately; a missing declaration raises and this path SAYS SO rather than
# substituting a number. `floor-lint.py` refuses a floor literal anywhere but `budget.json`.
#
# ⚠⚠ THE TWO FLOORS ARE DIFFERENT FACTS AND THIS FILE MUST NEVER CONFLATE THEM (run-2
# `budget.json` `floors._scope`: they were ONE field until task 7.82 split them, and "warn me
# before you start refusing" would be permanently unexpressible collapsed back):
#   · `floors.pressure_warn_mb` — the PRESSURE floor. `--mem-floor-mb` resolves THIS one and only
#     this one (`main`'s `floor_source(run_root, "warn", …)`), and it feeds only the pressure flag
#     (`check_system`). ⚠ THE RUNNING LOOP HOLDS ITS STARTUP COPY IN ITS OWN ARGV until it is next
#     relaunched — `budget.json` `floors._landed_is_not_live` — so the honest reading of "what this
#     loop holds" is `/proc/self/cmdline`, and that is what is reported.
#   · `floors.launch_refuse_mb` — the REFUSE floor. THIS is the revival launch gate's, and the
#     executor reads it FRESH in a per-launch fork that cannot inherit this loop's argv.
# NEVER CLAIM THE WARN FLOOR GATED A LAUNCH. It cannot: it is not the value the gate reads, and it
# is not read in the process that runs the gate.

REVIVAL_LAUNCH_LAYER = "revival launch gate: RAM floor"
REVIVAL_BLOCKED_LINE = "REVIVAL BLOCKED — revival launch gate: RAM floor"
REVIVAL_ABANDONED_LINE = "REVIVAL ABANDONED — revival launch gate: RAM floor"

# MECHANISM, NOT POLICY, and the distinction is `r-floor-single-source`'s own — that ruling binds
# the FLOOR (a policy number with exactly one home). How many times this loop is willing to re-fire,
# and how often, is a property of the loop. `coord.LIFECYCLE_MEM_RETRIES` carries the identical
# argument for the executor's inner retries; these are the OUTER ones and the two are not the same
# ladder: the executor retries for ~60 s inside one fire, this retries across ticks.
REVIVAL_MAX_ATTEMPTS = 3
# ⚠ ONE CADENCE FOR BOTH THE ESCALATION AND THE RETRY, AND IT IS A DECISION, not an accident.
# §3's escalation is `blocked_ticks % 3 == 0` (~1.5 min at the ruled ≤30 s cadence). Re-firing on EVERY
# blocked tick would hammer a floor that has not moved and would exhaust the three attempts in
# three ticks — after which `blocked_ticks` could never reach 6 and the second escalation the
# acceptance names would be UNREACHABLE. Riding the same cadence makes both expressible: escalate
# and retry at 3, again at 6, abandon at 9.
REVIVAL_ESCALATE_EVERY = 3

# The executor's own words for a memory refusal, matched as a substring. The COUPLING IS REAL and
# is asserted in the selftest against `coord.lifecycle_memory_gate`'s source rather than trusted:
# if Stage 3 rewords, this discriminator must go RED rather than silently answering "not a RAM
# refusal" forever and turning every blocked revival into a plain re-claim loop.
REVIVAL_RAM_FAILURE_MARK = "refused on memory"


def _ram_refusal(entry):
    """(is_ram_refusal, failure_text) for a marker entry the EXECUTOR left behind.

    Keyed on `state == "FAILED"` plus the executor's own failure wording. `finish_lifecycle` REFUSES
    any state but `done`/`FAILED`, so `FAILED` is the only shape a broken relaunch can leave."""
    if not isinstance(entry, dict) or entry.get("state") != "FAILED":
        return False, ""
    failure = str(entry.get("failure") or "")
    return (REVIVAL_RAM_FAILURE_MARK in failure), failure


def _loop_warn_floor():
    """The PRESSURE (warn) floor THIS RUNNING LOOP holds, read from its own /proc argv.

    ⚠ NOT the revival gate's floor, and the returned text says so in as many words. `--mem-floor-mb`
    resolves the WARN floor alone; a loop launched with it keeps that copy until it is next
    relaunched, which is why this reads /proc rather than the tree — LANDED IS NOT LIVE."""
    try:
        argv = Path(f"/proc/{os.getpid()}/cmdline").read_bytes().decode("utf-8", "replace")
        parts = [p for p in argv.split("\0") if p]
    except OSError:
        parts = []
    held = ""
    for i, a in enumerate(parts):
        if a == "--mem-floor-mb" and i + 1 < len(parts):
            held = parts[i + 1]
        elif a.startswith("--mem-floor-mb="):
            held = a.split("=", 1)[1]
    return (f"PRESSURE (warn) floor this loop HOLDS, read from /proc/{os.getpid()}/cmdline: "
            + (f"--mem-floor-mb {held} (an explicit operator override, carried in argv since "
               f"startup)" if held else
               "no --mem-floor-mb in argv, so it resolved floors.pressure_warn_mb from the run's "
               "budget.json at startup")
            + " — THIS IS THE PRESSURE FLOOR AND IT DID NOT GATE THE REVIVAL LAUNCH")


def revival_floors(args, base):
    """(warn_text, refuse_text) — the two floors, REPORTED SEPARATELY and never conflated.

    Read ONLY to report. Nothing here gates anything; the gate is the executor's."""
    run_root = coord.package_dir(args) if getattr(args, "package", None) else Path(base).parent
    try:
        value, why = budget_mod.floor_source(run_root, "refuse", None)
        refuse = (f"REFUSE floor (floors.launch_refuse_mb — the one the revival launch gate reads): "
                  f"{value} MB — {why}")
    except budget_mod.FloorUndeclared as exc:
        refuse = (f"REFUSE floor: UNRESOLVED — FloorUndeclared: {exc}. NO NUMBER IS SUBSTITUTED "
                  f"(read_floor has no default= parameter, deliberately). Declare "
                  f"floors.launch_refuse_mb in the run's budget.json; the pre-7.82 name "
                  f"floors.ram_available_mb is RETIRED and is not read")
    except budget_mod.FloorUnreadable as exc:
        refuse = (f"REFUSE floor: UNRESOLVED — FloorUnreadable: {exc}. A budget.json that IS "
                  f"declared and cannot be read is NOT the same fact as no declaration, and is "
                  f"never treated as one")
    return _loop_warn_floor(), refuse


def _publish_ladder(base, seat, marker_state, lad, failure):
    """Publish the ladder's verdict onto the marker entry. Returns True/False, never raises.

    ⚠ ONE AUTHORITY, ONE PROJECTION (PRIN-11). The ladder's counters LIVE in this loop's own
    persisted state (`{base}/watch-state.json`, goal-sectioned), and this writes a PROJECTION of
    them onto the marker so `coordinate status` and any other marker reader can see the seat is
    blocked. THE MARKER CANNOT BE THE AUTHORITY AND THE REASON IS MEASURED: `coord.stamp_lifecycle`
    does `data[seat] = rec` — it REPLACES the whole entry — so the child of the very next retry
    wipes any counter kept there, and `blocked_ticks` could never survive to reach the second
    escalation. Recorded rather than worked around; widening `stamp_lifecycle` is a Stage 3 change.

    ⚠ `blocked` AND `abandoned` ARE STATES `coord.finish_lifecycle` REFUSES TO WRITE (it accepts
    only `done`/`FAILED`), which is exactly why this write is here and not there — `claim_revival`'s
    step-4 comment named this task as the one that would introduce them, and it does."""
    try:
        with coord.coord_lock(base) as held:
            if not held:
                return False
            data, status = _strict_ledger(coord.lifecycle_path(base))
            entry = data.get(seat)
            if status != "ok" or not isinstance(entry, dict):
                return False
            entry["state"] = marker_state
            entry["blocked_ticks"] = int(lad.get("blocked_ticks", 0))
            entry["revival_attempts"] = int(lad.get("attempts", 0))
            entry["failure"] = str(failure)
            data[seat] = entry
            coord.atomic_write(coord.lifecycle_path(base),
                               json.dumps(data, indent=2, sort_keys=True) + "\n")
        return True
    except (OSError, ValueError, TypeError):
        return False


def revival_ladder(args, base, seat, entry, rev, notes, room):
    """THE LOUD-REFUSAL PATH. Returns `(verdict, line_or_None)`; NEVER raises, NEVER fires.

        "PROCEED"    no ladder is running — the caller's normal CRASHED path owns this tick
        "BLOCKED"    blocked on the RAM floor; the caller must NOT fire this tick
        "RETRY"      blocked, but the cadence says re-fire — the caller proceeds to claim + fire
        "ABANDONED"  attempts exhausted; the caller must NEVER fire again for this episode

    ⚠ EVERY FAILURE LANDS AS A VISIBLE ARTIFACT, and the report line prints EVERY TICK on every
    non-PROCEED verdict — including after abandonment, so the hole never goes quiet. THE NOTES DO
    NOT: one at the first block, one per escalation, one at abandonment. That difference is the
    whole distinction between VISIBLE and SPAMMING, and a room trained to ignore this arm's notes
    is a room this arm cannot reach.

    ⚠ THE LADDER RE-ARMS WHERE EVERY OTHER REVIVAL COUNTER RE-ARMS: when the seat is seen LIVE
    again (`check_revival` step 3). A revival that succeeds must not leave an armed ladder behind."""
    lad = dict(rev.get("ladder") or {})
    ram, failure = _ram_refusal(entry)
    # ⚠ THE LADDER'S OWN STATE IS THE AUTHORITY FOR "AM I IN A LADDER", NOT THE MARKER. The FIRST
    # tick enters from the executor's `state: FAILED`; from the second tick on the marker reads
    # `blocked` — this loop's own projection — and `_ram_refusal` correctly answers False for it.
    # Keying continuation on the marker would therefore drop out of the ladder after exactly one
    # tick and hand the seat straight back to the CRASHED branch, re-firing every tick against a
    # floor that has not moved. That was the first draft of this function and it is the reason this
    # line exists.
    in_ladder = bool(lad) and not lad.get("abandoned")
    warn_text, refuse_text = None, None

    if lad.get("abandoned"):
        # Terminal. Reported forever, noted never again, and it authorises nothing.
        return "ABANDONED", (
            f"{seat:<18} {'REFUSED':<7} {REVIVAL_ABANDONED_LINE} — {lad.get('attempts', 0)} "
            f"attempt(s) exhausted after {lad.get('blocked_ticks', 0)} blocked tick(s); NO further "
            f"revival will be attempted for this episode. A human must free memory and relaunch "
            f"the seat by hand")

    if not (ram or in_ladder):
        if isinstance(entry, dict) and entry.get("state") == "FAILED":
            # A NON-RAM executor failure. Stage 3 raised its own alarm; this adds the Stage-4 half
            # so the room learns the revival did not happen, then stands aside — the next tick
            # re-claims over the terminal entry per s4-05, which is the correct behaviour for a
            # failure that is not the one refusal reason that clears on its own.
            _claim_note(room, notes, seat, "exec-failed",
                        f"{REVIVAL_FIRE_LAYER}: the revival executor for '{seat}' ended FAILED and "
                        f"the seat was NOT brought back — "
                        f"{failure or 'no failure text was recorded'}. "
                        f"This is NOT the RAM floor, so there is no retry ladder: the "
                        f"next tick re-claims the seat and fires again. Read the executor's log "
                        f"(the `log` field on the marker entry) before assuming it will succeed "
                        f"the second time. (This is the revival fire gate reporting, not the "
                        f"harness permission classifier.)")
        return "PROCEED", None

    # ---- a RAM refusal, or a ladder already running. Count the tick FIRST, then decide. ----
    # The executor's own words are stored on the ladder at the FIRST refusal and quoted from there
    # afterwards: from tick 2 the marker carries this loop's projection, and a note that stopped
    # quoting the executor would leave the reader with the symptom and none of the evidence.
    failure = failure or str(lad.get("failure") or "(the executor's failure text was not recorded)")
    lad["failure"] = failure
    lad["blocked_ticks"] = int(lad.get("blocked_ticks", 0)) + 1
    # The fire that produced this refusal was attempt 1 — it already happened, and a ladder that
    # started counting at 0 here would grant a fourth.
    lad["attempts"] = max(int(lad.get("attempts", 0)), 1)
    lad.setdefault("since", coord.now())
    ticks, attempts = lad["blocked_ticks"], lad["attempts"]
    cadence = (ticks % REVIVAL_ESCALATE_EVERY == 0)

    if cadence and attempts >= REVIVAL_MAX_ATTEMPTS:
        lad["abandoned"] = True
        rev["ladder"] = lad
        _publish_ladder(base, seat, "abandoned", lad, failure)
        warn_text, refuse_text = revival_floors(args, base)
        notes.append(Flag(seat,
            f"{REVIVAL_LAUNCH_LAYER}: revival of '{seat}' is ABANDONED. {attempts} attempt(s) were "
            f"made and every one was refused by the executor's launch gate; the seat has been down "
            f"and blocked for {ticks} tick(s) since {lad['since']}. NO FURTHER REVIVAL WILL BE "
            f"ATTEMPTED — this loop stops retrying, and the report line keeps printing every tick "
            f"so the hole does not go quiet. Free memory, then bring the seat back by hand. "
            f"Executor's own words: {failure}. {refuse_text}. {warn_text}. (This is the revival "
            f"launch gate reporting, not the harness permission classifier.)"))
        return "ABANDONED", (
            f"{seat:<18} {'REFUSED':<7} {REVIVAL_ABANDONED_LINE} — {attempts} attempt(s) exhausted "
            f"after {ticks} blocked tick(s); NO further revival will be attempted for this episode")

    rev["ladder"] = lad
    _publish_ladder(base, seat, "blocked", lad, failure)
    line = (f"{seat:<18} {'REFUSED':<7} {REVIVAL_BLOCKED_LINE} — blocked_ticks {ticks}, attempt "
            f"{attempts}/{REVIVAL_MAX_ATTEMPTS}, blocked since {lad['since']}")
    if ticks == 1:
        warn_text, refuse_text = revival_floors(args, base)
        _claim_note(room, notes, seat, "ram-blocked",
                    f"{REVIVAL_LAUNCH_LAYER}: revival of '{seat}' is BLOCKED. The detached executor "
                    f"reached its relaunch step and its launch gate REFUSED on available memory, so "
                    f"the seat is roster-absent and is NOT coming back until memory frees. This "
                    f"loop will retry every {REVIVAL_ESCALATE_EVERY} ticks, up to "
                    f"{REVIVAL_MAX_ATTEMPTS} attempts, and will keep saying so every tick. Freeing "
                    f"another seat NOW is what unblocks it. Executor's own words: {failure}. "
                    f"{refuse_text}. {warn_text}. (This is the revival launch gate reporting, not "
                    f"the harness permission classifier.)")
    elif cadence:
        warn_text, refuse_text = revival_floors(args, base)
        notes.append(Flag(seat,
            f"{REVIVAL_LAUNCH_LAYER}: ⚠ ALARM — '{seat}' HAS BEEN DOWN AND BLOCKED FOR {ticks} "
            f"CONSECUTIVE TICKS since {lad['since']}, and every revival attempt so far "
            f"({attempts}/{REVIVAL_MAX_ATTEMPTS}) was refused by the executor's launch gate on "
            f"available memory. Retrying now as attempt {attempts + 1}. Executor's own words: "
            f"{failure}. {refuse_text}. {warn_text}. (This is the revival launch gate reporting, "
            f"not the harness permission classifier.)"))
        lad["attempts"] = attempts + 1
        rev["ladder"] = lad
        _publish_ladder(base, seat, "blocked", lad, failure)
        return "RETRY", line + f" -> RETRYING as attempt {lad['attempts']}"
    return "BLOCKED", line


def check_revival(args, base, snap, snap_err, state, notes):
    """SEAT-DOWN DETECTOR — classify every roster-absent seat, and CLAIM the crashed ones. Lines.

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

    s4-04 adds a FOURTH outcome ahead of CRASHED — COMPLETED-ONE-SHOT, keyed on the descriptor's
    declared `mode:` and never on `harness:`. It is the axis liveness cannot supply: whether
    absence is the seat's EXPECTED terminal state. An undeclared `mode:` is UNDECIDABLE and
    REFUSES; it is not silently read as `interactive`. ⚠ THE WHOLE ARM, THIS GATE INCLUDED, IS A
    WAY-STATION IN THIS FILE — task 7.35 deletes `watch.py` into the `goal-watcher-job` (CMP-21);
    see the s4-04 literals block above for the ruling and the migration cost.

    Debounce is 2 consecutive non-stale ticks, and the number is CHOSEN, NOT MEASURED — no
    crash-to-detection latency data exists in this run. THE CONSTANTS ARE IN TICK UNITS AND THEY
    RE-SCALE BY THE CADENCE ALONE, so at the ruled ≤30 s cadence (`r-watch-loop-30s`) worst-case
    detection is ~1 MIN PLUS ONE SENSOR CADENCE. That is named in the report line rather than hidden.
    Firing on ONE tick would make a single transient sensor error a relaunch.

    ⚠ THE OWNER QUESTION THIS COMMENT USED TO WITHHOLD IS ANSWERED. It read: *"whether ~20 min is
    acceptable for a leader outage is an OWNER QUESTION, UNASKED — do not answer it by editing
    `--loop` here."* The owner ASKED AND ANSWERED it — `r-watch-loop-30s`, 2026-07-30: 30 seconds
    maximum, which discharges 7.32's open question on the side of tighter bounds. The instruction is
    struck because, left standing, it told the next reader NOT to make the change the owner had just
    ruled. The cadence now has a home (`budget.json cadence.watch_loop_max_seconds`), so the way to
    change it is to change that declaration — not to edit a flag here, which is what the retired
    `--loop` refuses to let anyone do silently.

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
            # s4-05: the claim gate's per-seat notes re-arm HERE and nowhere else — same signal,
            # same line. A seat seen live again is a new episode; leaving them armed would make a
            # second, genuinely different outage silent.
            for k in [k for k in room.get("claim_notes", {}) if k.startswith(s["seat"] + "\t")]:
                room["claim_notes"].pop(k, None)

    if not absent:
        lines.append(f"{'revival':<18} {'ok':<7} no roster-absent seat")
        return lines

    # LIVE roster, re-read now: the CLEANLY-OUT predicate must read the roster as it stands at
    # classification time, not as the snapshot saw it up to one sensor cadence ago.
    _, _, live_rows = coord.load_workers(base)
    roster = {r["agent"]: r for r in live_rows}

    # s4-04: the SEAT DESCRIPTORS, re-read now for the same reason the roster is — the gate below
    # keys on a DECLARED property and must read it as it stands, not as a snapshot saw it up to one
    # sensor cadence ago. Through `coord.discover_workers`, which is the ONE parser of a
    # descriptor's frontmatter and already emits `mode` (dag-11's key, `coord.FM_KEY["mode"]`); a
    # second regex here would be a second opinion about what a seat declares (PRIN-11).
    decls = {w["agent"]: w for w in coord.discover_workers(coord.workers_dir(args))}

    # s4-14: the OWNER-DOOR gate's input, and it is DELIBERATELY A SECOND READ rather than a field
    # added to `decls` above. The door is declared by `relays:`, which `discover_workers` does not
    # carry and has no reason to: `inbox_decls` is the ONE derivation of that key, and it is
    # already what BOTH existing door consumers use — the reap exemption (`coord.py`, the
    # `r-owner-afk-liaison-parked` carve-out) and `owner_world`. Adding `relays` to
    # `discover_workers` instead would give one declaration a second parser (PRIN-11), and the two
    # would drift in exactly the way this file has been bitten by twice.
    try:
        door_decls, door_err = coord.inbox_decls(args), ""
    except Exception as exc:  # noqa: BLE001 — a bad descriptor must never take the loop down
        door_decls, door_err = {}, repr(exc)

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

        # ---- (3) s4-04: THE COMPLETED-ONE-SHOT GATE — and it MUST stay BEFORE the CRASHED branch.
        # ⚠ WAY-STATION: this arm's home is `watch.py` only until task 7.35 deletes the file into
        # the `goal-watcher-job` (CMP-21) — see the s4-04 literals block above for the full ruling.
        #
        # D-3C. A NORMALLY-COMPLETED opencode one-shot appears in `roster_absent` BYTE-IDENTICALLY
        # to a crashed claude seat (measured, `opencode-machinery-test.md` §6b). It is not IDLE
        # (nothing is running) and not MID-RENEWAL (no marker), so without this gate it classifies
        # CRASHED and a CORRECT detector resurrects every finished one-shot FOREVER — a relaunch
        # loop firing on a seat whose ABSENCE IS ITS SUCCESS. The missing axis is not liveness; it
        # is whether absence is the seat's EXPECTED TERMINAL STATE, which no liveness observation
        # can supply — which is exactly why the three-way detector above cannot catch it.
        #
        # ⚠ THE KEY IS `mode:`, NEVER `harness:`. Harness is a proxy that is true today and breaks
        # the moment an opencode seat runs in TUI mode, or a future one-shot harness arrives.
        # Gating on the proxy is how a correct rule becomes wrong SILENTLY. `agent_type` is barred
        # too (run-2 `budget.json`: a sensor observation is never an authorization).
        #
        # ⚠ AN UNDECLARED `mode:` IS NOT `interactive`. Defaulting either way ships one of the two
        # failure modes in silence, so an absent — or unrecognised — value is UNDECIDABLE: refuse,
        # print EVERY tick, note ONCE (R-8: the layer string LEADS the body). This is the same
        # reading the attest-exit arm's own term (b) takes on this key (`coord.py`, dag-11), and
        # issue-3's SC-14 makes a missing `mode:` a defect at EMISSION time — never a default here.
        #
        # ⚠ MEASURED CONSEQUENCE, stated so nobody meets it as a surprise: NO run-2 descriptor
        # declares `mode:` (52 `seat.md` files, zero hits, 2026-07-29). On any run whose seats were
        # emitted before dag-04, this gate therefore makes the CRASHED branch UNREACHABLE and every
        # absent seat lands in the refusal below. THAT IS FAIL-CLOSED WORKING AS RULED, not a
        # defect in this gate; the fix is at emission (dag-04 / SC-14), and a silent default here
        # would trade a visible inert arm for an invisible wrong one.
        mode = (decls.get(seat) or {}).get("mode") or ""
        if mode == "one-shot":
            lines.append(f"{seat:<18} {'REVIVAL':<7} {REVIVAL_ONE_SHOT_LINE} — declared mode: "
                         f"one-shot; hand-off, not a drop: {REVIVAL_ATTEST_CMD} --seat {seat}")
            # HAND-OFF, NEVER A SILENT DROP (LG-12): a gate that merely skips the seat has traded a
            # resurrection loop for a PERMANENT STALL — the roster still reads active, the ready
            # arithmetic still reads "working", and the successor never becomes ready. This loop
            # does NOT run the arm (`coordinate attest-exit` is a subcommand, and this arm actuates
            # nothing beyond its one ruled revival fire): it names the seat and the command, and
            # the arm's own cadence plus the chief-of-staff's sweep own the execution.
            _claim_note(room, notes, seat, "one-shot",
                        f"{REVIVAL_MODE_LAYER}: '{seat}' is roster-absent and its descriptor "
                        f"declares mode: one-shot, so its absence is the seat's EXPECTED terminal "
                        f"state — it will NEVER be revived. It still needs an EXIT ATTESTATION, "
                        f"which this loop does not perform: run `{REVIVAL_ATTEST_CMD} --seat "
                        f"{seat}` (bare = report, --go = act). That arm records disposition "
                        f"`exited`, which asserts ONE fact — the harness terminated — and NOTHING "
                        f"about whether the work is done: an `exited` row advances no edge and "
                        f"routes to the LEADER, the only seat that may investigate it and flip it "
                        f"to `done`. (This is the revival mode gate routing a seat, not the "
                        f"harness permission classifier refusing a command.)")
            rev["gone_ticks"] = 0
            st["revival"] = rev
            continue
        if mode != "interactive":
            # UNDECIDABLE. FREEZE the debounce — neither increment nor reset — for the same reason
            # a stale snapshot freezes it: an unreadable declaration is evidence in NEITHER
            # direction. Reported every tick; noted once; re-arms when the seat is seen live.
            lines.append(f"{seat:<18} {'REFUSED':<7} REVIVAL REFUSED — {REVIVAL_MODE_LAYER}: "
                         f"descriptor declares mode: {mode or '<key absent>'} — UNDECIDABLE, so "
                         f"neither revival nor exit-attestation can be ruled correct")
            why_mode = ("absent" if not mode else
                        f"{mode!r}, which is neither one-shot nor interactive")
            _claim_note(room, notes, seat, "mode",
                        f"{REVIVAL_MODE_LAYER}: '{seat}' is roster-absent and its descriptor's "
                        f"`mode:` key is {why_mode} — so whether this absence is a CRASH or a "
                        f"COMPLETED one-shot is UNDECIDABLE from the descriptor, and the two "
                        f"answers are opposite acts (relaunch vs never relaunch). Nothing will be "
                        f"revived for '{seat}' while that holds. Fix it at EMISSION — declare "
                        f"`mode: one-shot | interactive` in the seat's descriptor (issue-3 SC-14 "
                        f"makes a missing key a defect there) — not by a default here. (This is "
                        f"the revival mode gate refusing, not the harness permission classifier.)")
            st["revival"] = rev
            continue

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

        # ---- (4a) s4-14: THE OWNER-DOOR GATE — a DOOR IS NOT A CRASHED SEAT ----
        #
        # ⚠⚠ MEASURED, NOT ARGUED. On 2026-07-30 03:34:51 this arm relaunched run-3's `master`
        # seat ~60s after the OWNER CLOSED THAT CONVERSATION HIMSELF
        # (`coordination/lifecycle-exec-master-20260730-033451.log`). Nothing had crashed. The
        # roster row was still ACTIVE, and a door with no harness behind it is BYTE-IDENTICAL to a
        # crashed seat under every observation this loop makes. The same event also produced a
        # GHOSTROW flag naming `close-seat master --renew` as the remedy — i.e. the loop proposed
        # closing the owner's door on the strength of its own relaunch's startup window.
        #
        # THE MISSING AXIS IS s4-04'S, WITH A DIFFERENT SOURCE. s4-04 asks whether absence is the
        # seat's EXPECTED terminal state and answers from the descriptor. For a door the question
        # is the same and the descriptor CANNOT answer it: the fact that settles it is the OWNER'S
        # OWN DECLARED STATE, which is why this gate reads `owner-status.md` and not another key.
        #
        # ⚠ AND IT CLOSES A RULED CONTRADICTION, not just a nuisance. `reachable` (task 7.85) is
        # defined as *"at the PC, AFK FROM THE RUN — no master session running, a pane standing
        # where one can be"*. An arm that relaunches the door the instant no door session runs
        # makes that ruled state UNREACHABLE BY CONSTRUCTION (goal `issues.md` G-302).
        #
        # ⚠ THE DOOR IS DERIVED FROM `relays:`, NEVER FROM A NAME. `master` is ONE campaign's
        # seat-id; the next human-contact seat is called something else and a name list forgets it
        # identically — the reason `inbox_decls` states at length, and the reason the reap
        # exemption derives the same way. No third vocabulary is minted here.
        #
        # ⚠ FAIL-CLOSED, and the DIRECTION is chosen, not inherited: an owner state that is
        # missing, unparseable or unrecognised does NOT revive. Everywhere else in this arm an
        # unprovable premise HOLDS THE ACT, and it holds it here too — but note what the act IS.
        # Opening a human's door at them is not recoverable by the machine: the owner reopens a
        # door in one keystroke and cannot un-see a session started at him.
        #
        # ⚠ SCOPE IS THE DOOR AND NOTHING ELSE. A seat with no `relays:` never enters this branch,
        # so overnight revival of the `leader`, the planner and every worker is UNCHANGED — the
        # control below asserts exactly that, because "I only touched the door" is a claim, not a
        # proof. AND THIS GATE ONLY REFUSES: it forks nothing, launches nothing, calls no tmux.
        # The file's actuator count stays ONE (`s4-06 LG-16 (c)`), which is why neither the
        # charter in `run_pass` nor `r-watch-revival-arm-amends-notify-only` is amended by it.
        if door_err:
            # The door test itself is unreadable, so we cannot tell a door from a worker — and the
            # arm's whole job is telling absences apart. REFUSE ROOM-WIDE, exactly as an
            # unparseable ledger does below, rather than guessing per seat. FREEZE the debounce: a
            # declaration we cannot read is evidence in NEITHER direction.
            lines.append(f"{seat:<18} {'REFUSED':<7} REVIVAL REFUSED — {REVIVAL_DOOR_LAYER}: seat "
                         f"declarations unreadable ({door_err}); a DOOR cannot be told from a "
                         f"crashed seat")
            _claim_note(room, notes, seat, "door-decls",
                        f"{REVIVAL_DOOR_LAYER}: the seat declarations under "
                        f"{coord.workers_dir(args)} could not be read ({door_err}), so this loop "
                        f"cannot tell which seat carries the owner's door. Nothing will be revived "
                        f"while that holds — reviving blind would relaunch the owner's door at him "
                        f"as readily as a crashed worker. Fix the descriptor that fails to parse. "
                        f"(This is the revival owner-door gate refusing, not the harness "
                        f"permission classifier.)")
            st["revival"] = rev
            continue
        if (door_decls.get(seat) or {}).get("relays"):
            ost = coord.owner_status(base)
            ostate = ost.get("state") or "unknown"
            if ostate not in REVIVAL_DOOR_STATES:
                # An UNRECOGNISED state is called out in both surfaces rather than rendered like a
                # known one — `owner_status` degrades honestly instead of vanishing, and a reader
                # must be able to tell "the owner said afk" from "nobody can parse what he said".
                unk = "" if ost.get("known") else " (UNRECOGNISED by this tool)"
                admitted = " or ".join(REVIVAL_DOOR_STATES)
                lines.append(f"{seat:<18} {'REFUSED':<7} {REVIVAL_DOOR_LINE} — owner state "
                             f"{ostate!r}{unk}; admitted: {admitted}")
                _claim_note(room, notes, seat, "door",
                            f"{REVIVAL_DOOR_LAYER}: '{seat}' is roster-absent and its descriptor "
                            f"declares `relays:` — its pane is the OWNER'S DOOR, not a worker's "
                            f"seat. The owner's declared state is {ostate!r}{unk}, which does not "
                            f"admit a revival ({admitted} do), so the door STAYS SHUT. This is not "
                            f"a stalled seat and needs no rescue: a closed door is the owner's own "
                            f"act, and `coordinate owner <state>` is what changes it. (This is the "
                            f"revival owner-door gate refusing, not the harness permission "
                            f"classifier.)")
                # RESET, not freeze — and the difference is load-bearing. A closed door is a KNOWN
                # state, not an unreadable one, so the counter is not evidence being preserved. If
                # the owner later declares `present`, the door re-serves the full two-tick debounce
                # rather than firing instantly off ticks accumulated while it was legitimately shut.
                rev["gone_ticks"] = 0
                st["revival"] = rev
                continue

        # ---- (4b) s4-07: THE RAM-FLOOR LOUD-REFUSAL PATH, and it MUST sit BEFORE CRASHED.
        # A seat whose last revival was refused on memory is still roster-absent and still looks
        # exactly like a crash — so without this the CRASHED branch below re-claims and re-fires it
        # EVERY TICK against a floor that has not moved, and the abandonment state can never be
        # reached. The ladder decides; the caller obeys the verdict and never second-guesses it.
        verdict, lad_line = revival_ladder(args, base, seat, marker.get(seat), rev, notes, room)
        if verdict in ("BLOCKED", "ABANDONED"):
            lines.append(lad_line)
            st["revival"] = rev
            continue
        if verdict == "RETRY":
            # The cadence says re-fire. Fall through to CRASHED with the debounce SATISFIED — the
            # seat's absence is not in question here, only whether the launch can succeed, so
            # re-serving a two-tick debounce would add a FULL DEBOUNCE (REVIVAL_DEBOUNCE_TICKS ticks)
            # to every retry for no evidence. Stated in TICKS, not minutes, deliberately: this line
            # used to say "~20 min", which was arithmetic over the superseded 10-minute loop and went
            # stale the moment the owner ruled the cadence (`r-watch-loop-30s`). Ticks re-scale; a
            # wall-clock figure written beside a configurable cadence does not.
            lines.append(lad_line)
            rev["gone_ticks"] = REVIVAL_DEBOUNCE_TICKS - 1

        # (5) CRASHED — in roster_absent, none of the above, debounce satisfied.
        rev["gone_ticks"] = int(rev.get("gone_ticks", 0)) + 1
        if rev["gone_ticks"] >= REVIVAL_DEBOUNCE_TICKS:
            # s4-05: THE CLAIM, and only the claim. It re-reads the roster and the ledgers under
            # `coord_lock` — the classification above is up to one sensor cadence old and the
            # section must decide on the room as it stands. The fire is still s4-06's, and it
            # fires on "CLAIMED"/"RE-CLAIMED" ONLY: "STOOD-DOWN" and "REFUSED" are different
            # facts and neither authorises a launch.
            outcome, why = claim_revival(base, seat, row.get("pane"), notes, room)
            # s4-06: THE FIRE, and it fires on "CLAIMED"/"RE-CLAIMED" ONLY. "STOOD-DOWN" and
            # "REFUSED" are different facts with the same consequence today and DIFFERENT
            # consequences the moment anyone adds a retry, so this branches on the STRING and never
            # on "did it not refuse" — `claim_revival`'s own docstring states the requirement.
            if outcome in ("CLAIMED", "RE-CLAIMED"):
                fired, fwhy = fire_revival(args, base, snap, seat, row.get("pane"), notes, room)
                lines.append(f"{seat:<18} {'REVIVAL':<7} CRASHED — claim {outcome}: {why}; fire "
                             f"{fired}: {fwhy}")
            else:
                lines.append(f"{seat:<18} {'REVIVAL':<7} CRASHED — NOT FIRED (pane "
                             f"{row.get('pane')}, {row.get('liveness')}) — claim {outcome}: {why}")
        else:
            lines.append(f"{seat:<18} {'REVIVAL':<7} CRASHED pending — "
                         f"{rev['gone_ticks']}/{REVIVAL_DEBOUNCE_TICKS} consecutive non-stale ticks "
                         f"(~{_ticks_minutes(REVIVAL_DEBOUNCE_TICKS, args)} worst case at this "
                         f"loop's cadence, plus one sensor cadence)")
        st["revival"] = rev

    return lines


# ---------- dag-12: the STALLED-BLOCKING-DEPENDENTS flag (NOTIFY-ONLY, NO ACTUATOR ARM) ----------
#
# ⚠⚠ WAY-STATION, NOT A HOME — `decisions.md#d-watch-is-a-way-station`, the same ruling that binds
# every stage-4 arm above. THIS FILE IS SCHEDULED FOR DELETION BY TASK 7.35; what supersedes this
# flag is the `goal-watcher-job` (CMP-21) reading the same canonical `state.json` snapshot that
# team-monitor (CMP-20) writes. It lands here only because `watch.py` is TODAY the sole component
# observing anything at all. Do not build on it as a home and do not defend it as architecture.
#
# ⚠⚠ THE ACTUATOR COUNT OF THIS FILE STAYS **ONE**, AND THIS SECTION IS NOT IT. This flag NAMES a
# stalled seat and its blocked dependents and stops. It launches nothing, kills nothing, writes no
# lifecycle marker, and is NOT routed into stage-4's revival arm — a SECOND actuator arm here would
# re-open the double-launch question stage 4 closed. The loop's charter (`run_pass`, amended by
# s4-08) says NOTIFY ONLY WITH EXACTLY ONE EXCEPTION, and the exception is `fire_revival`. The
# selftest asserts the count over the whole revival arm's call graph (`s4-06 LG-16 (c)`) AND over
# this section's own call graph (`dag-12 RS-10`), each with a red arm. Anyone who adds a second arm
# amends the charter, the ledger anchor `r-watch-revival-arm-amends-notify-only`, and BOTH
# assertions, in one act.
#
# ⚠ WHY THIS ARM MAY KEY ON SILENCE WHERE THE REVIVAL ARM MAY NOT. `check_revival` is forbidden to
# read `last_activity_age_s` at all: it ACTUATES, and a leader forty minutes into one ruling looks
# exactly like a dead one, so a relaunch fired on silence kills a live seat. This flag actuates
# nothing, and SHAPE A — the interactive stall — is BY DEFINITION a seat that is still alive in its
# pane past a natural end. Silence is the only signal there is. The asymmetry is the design: the
# notifier may guess, the actuator may not.

STALLED_FLAG_NAME = "seat-stalled-blocking-dependents"

# Report-line literals. Constants because the acceptance controls (dag-12 RS-9/RS-15/RS-16) grep
# for the EXACT strings — a reworded line is a silently-failing control.
STALLED_LINE = "STALLED-BLOCKING"
STALLED_OK_LINE = f"{'stalled':<18} {'ok':<7} no stalled seat blocking a dependent"
STALLED_STALE_LINE = "STALLED-BLOCKING paused — snapshot stale"
STALLED_NO_DAG_LINE = (f"{'stalled':<18} {'n/a':<7} STALLED-BLOCKING n/a — the run declares no "
                       f"taskforce.csv, so no row can name a predecessor")
STALLED_LAYER = "stalled-blocking flag"

# ⚠ THE HONEST LIMIT, and it is carried IN THE FLAG TEXT rather than only in a task file — R-6, and
# the reason is that the reader of the flag is the one who has to act on it. For an INTERACTIVE seat
# a DIRTY FINISH (the work is done, the check-out never happened) and a CRASH (the work is not done)
# are NOT MECHANICALLY DISTINGUISHABLE in a run whose tasks carry no machine-checkable done contract
# — telling them apart is CMP-25 step 1, and run-2's tasks carry none. So stage-4's revival arm
# relaunches on the safe assumption (a successor reads `memory.md` and can check out clean in one
# turn) and THIS FLAG surfaces the blocked dependents for a human's adjudication. This is the ONE
# place the emulation is strictly weaker than CMP-25, and it is weaker for a reason not fixable
# here: the absence of done contracts, not the absence of an edge-runner. For a ONE-SHOT the
# ambiguity does not arise — absence is the EXPECTED terminal state, which is exactly what `mode:`
# buys (s4-04) — so this text names the interactive case only.
STALLED_LIMIT = (
    "⚠ THIS FLAG CANNOT TELL A DIRTY FINISH FROM A CRASH, and that is a property of the run, not of "
    "this check: for an interactive seat, 'the work is done and the check-out never happened' and "
    "'the work is not done' produce the IDENTICAL observation, and separating them requires "
    "verifying the seat's own done contract mechanically — which the tasks of this run do not carry. "
    "So nothing is concluded here and nothing is actuated: the two answers are opposite acts and "
    "only a human may pick one. Read the seat's pane and its `memory.md` before deciding.")


def snapshot_age_s(snap):
    """Age in seconds of a team-monitor snapshot, or None when it carries no usable `captured_at`.

    ⚠ DECLARED DUPLICATION, with this as the single home. `check_revival` computes the same age
    INLINE (its staleness block) and is NOT repointed here, because that function is stage 4's and
    out of dag-12's write set. The duplication is therefore declared rather than silent, and it is
    GUARDED: the selftest asserts the two paths agree on BOTH sides of `budget_mod.STALE_AFTER_S`
    for the same snapshot, so a threshold or field change on either side goes red instead of
    letting one arm enforce while the other pauses. Whoever next edits `check_revival` collapses it
    onto this helper — the PRIN-11 sanctioned break is a copy that is declared in one home AND
    checked, and this is both."""
    if not isinstance(snap, dict) or snap.get("captured_at") is None:
        return None
    try:
        return time.time() - float(snap["captured_at"])
    except (TypeError, ValueError):
        return None


def stalled_candidates(snap, inactive_min):
    """{seat: reason} — every seat the SNAPSHOT shows as absent-or-quiet. `state.json` AND NOTHING
    ELSE: this function takes the parsed snapshot as its only argument and opens no file, reads no
    pane, and touches no roster. That is CMP-21 invariant 1 held at its own boundary — a snapshot
    missing `roster_absent`/`seats` yields `{}` and the flag simply does not fire, rather than
    reaching around the sensor to a second observation path.

    Two shapes, and the ORDER matters: a seat already reported roster-absent is never re-reported
    as quiet, so one stalled seat is never two flags."""
    out = {}
    for row in snap.get("roster_absent") or []:
        seat = (row.get("seat") or "").strip()
        if seat:
            out[seat] = (f"roster-absent ({row.get('liveness') or 'absent'}, pane "
                         f"{row.get('pane')})")
    for s in snap.get("seats") or []:
        seat = (s.get("seat") or "").strip()
        if not seat or seat in out or not s.get("roster_active"):
            continue
        try:
            age = float(s.get("last_activity_age_s"))
        except (TypeError, ValueError):
            continue                      # no reading is not a reading of zero, and not a stall
        if age >= inactive_min * 60:
            out[seat] = (f"quiet {int(age // 60)} min (threshold {inactive_min} min), alive in "
                         f"pane {s.get('pane')}")
    return out


def blocking_dependents(after):
    """{predecessor: [dependents]} — the INVERSE of the run's `after` sets, dependents in file
    order. A predecessor with no dependent gets no key, which is the whole discriminator: a stalled
    LEAF blocks nobody and must never be flagged."""
    inv = {}
    for seat, preds in after.items():
        for p in preds:
            if seat not in inv.setdefault(p, []):
                inv[p].append(seat)
    return inv


def check_stalled_blocking(args, base, snap, snap_err, state, notes):
    """`seat-stalled-blocking-dependents` — ONE NOTIFY-ONLY flag. Returns report lines.

    Fires for seat P when ALL THREE hold:
      (1) the SNAPSHOT shows P absent-or-quiet past the loop's inactivity cadence, and
      (2) P has NO terminal disposition — `coord.terminal_disposition`, dag-09's enum
          (`done | renew | revive | exited`); a seat that checked out is not stalled, and
      (3) at least one `taskforce.csv` row names P in its `after` set — P is BLOCKING.

    It names P and every blocked dependent, carries `STALLED_LIMIT` verbatim, routes through
    `flag_recipient` (run-2 sends flags to the chief-of-staff; a flag ABOUT that seat is relayed to
    the leader — this arm adds no routing of its own), and ACTUATES NOTHING.

    ⚠⚠ RS-15 AS THE SPEC WROTE IT DOES NOT HOLD, AND SAYING SO IS PART OF THE WORK. Its literal
    words are "grep the flag's code path for any other file read → zero". THAT IS UNSATISFIABLE
    TOGETHER WITH RS-16: the `after` sets live in the run's `taskforce.csv` and the dispositions in
    `awaiting-close.json` / `sessions.csv`, and team-monitor publishes NEITHER — `state.json`'s
    schema (`team-monitor/1`) has no dependency field at all, so a flag reading only the snapshot
    could never name a dependent. The two controls contradict each other as written.

    What holds instead, and it is the bound CMP-21 invariant 1 actually states ("it never touches a
    tmux pane, a harness session file, /proc or a prompt directly"):
      · EVERY OBSERVATION comes from the snapshot and nothing else — `stalled_candidates` above
        takes the parsed snapshot as its only input and reads no file, no pane and no roster.
      · The other two reads are NOT observations. `taskforce.csv` is the run's REGISTRY (the
        workflow's shape, which no sensor observes) and the ledgers are the CHECK-OUT RECORD. Both
        go through coord's own single-source readers — `taskforce_after` and `terminal_disposition`,
        dag-09/dag-10's — never a second parse here (PRIN-11).
      · That read inventory is CLOSED AND ASSERTED, not asserted-by-prose: the selftest scans this
        section's whole call graph for reader symbols and requires EXACTLY those two plus the
        hoisted `load_awaiting`, with a red arm that inserts a third and goes red.
    The degradation half of RS-15's control DOES hold literally and is run: a `state.json` missing
    `roster_absent`/`seats` degrades to NO FLAG rather than reading around the sensor."""
    # A snapshot that is absent is the SILENT path (this module ships kit-wide and most packages
    # run no team-monitor); a snapshot that is STALE pauses, for CMP-21 invariant 2's reason — stale
    # data is evidence in neither direction. Neither state is a green.
    if snap is None and _snapshot_absent(snap_err):
        return []
    age = snapshot_age_s(snap)
    if snap is None or age is None or age > budget_mod.STALE_AFTER_S:
        why = snap_err or (f"snapshot age {int(age)}s > {budget_mod.STALE_AFTER_S}s"
                           if age is not None else "snapshot carries no captured_at")
        return [f"{'stalled':<18} {'PAUSED':<7} {STALLED_STALE_LINE} — {why}"]
    if snap.get("session_alive") is False:
        # Every seat is absent when the room is gone. Flagging N stalls for ONE incident points the
        # reader at the wrong mechanism entirely — the same reason the revival arm short-circuits.
        return [f"{'stalled':<18} {'n/a':<7} STALLED-BLOCKING n/a — room dead"]

    inactive_min = getattr(args, "inactive_min", None) or 30
    cands = stalled_candidates(snap, inactive_min)
    room = state.setdefault("_stalled_room", {})
    armed = room.setdefault("notified", {})
    if not cands:
        armed.clear()
        return [STALLED_OK_LINE]

    # THE REGISTRY READ — not an observation. `taskforce_after` is dag-10's one parser of the
    # `after` cell, matching `materialize-seats.py`'s writer exactly; a reader that invented its own
    # separator would see one predecessor named "a,b".
    after = coord.taskforce_after(coord.package_dir(args, register=False))
    if not after:
        armed.clear()
        return [STALLED_NO_DAG_LINE]
    inv = blocking_dependents(after)
    # THE LEDGER READ — hoisted ONCE and passed down, exactly as dag-10's `ready_seat_rows` does it,
    # so N candidates cost one read rather than N.
    awaiting = coord.load_awaiting(base)

    lines, seen = [], set()
    for seat, why in cands.items():
        deps = inv.get(seat) or []
        if not deps:
            lines.append(f"{seat:<18} {'ok':<7} stalled but blocks nobody — {why}")
            continue
        value, source, skew = coord.terminal_disposition(
            coord.package_dir(args, register=False), base, seat, awaiting=awaiting)
        if skew:
            # A contradiction is never a tie-break. dag-10 reports SKEW and refuses; so does this.
            lines.append(f"{seat:<18} {'SKEW':<7} STALLED-BLOCKING refused — {STALLED_LAYER}: "
                         f"awaiting-close.json={skew[0]} | sessions.csv={skew[1]} ⚠ ADJUDICATE")
            continue
        if value is not None:
            lines.append(f"{seat:<18} {'ok':<7} stalled but checked out `{value}` ({source}) — "
                         f"not a stall")
            continue
        # ⚠ THE DEPENDENT LIST IS COMPLETE AND DELIBERATELY UNCAPPED, and on a DEGENERATE DAG that
        # is long: measured against run-2's real 52-row taskforce.csv, a stalled `leader` names 50
        # dependents and the note runs past a kilobyte. Truncating it was rejected — RS-16 requires
        # every row that names P, and a "+43 more" would hand the reader back exactly the lookup
        # this flag exists to spare them. The length is a symptom of the DAG (50 of 52 rows say
        # `after: leader`, which is sequencing masquerading as dependency — the spec's RS-7
        # pathology), not of this flag; re-authoring the DAG shortens it at the cause.
        seen.add(seat)
        lines.append(f"{seat:<18} {'FLAG':<7} {STALLED_LINE} — {why}; blocks "
                     f"{len(deps)}: {', '.join(deps)}")
        key = f"{seat}\t{why}"
        if not armed.get(key):
            notes.append(Flag(seat,
                f"watch: {STALLED_FLAG_NAME} — '{seat}' is {why} and has NO check-out on record, "
                f"and {len(deps)} seat(s) name it in their `after` set, so they cannot become "
                f"ready while this holds: {', '.join(deps)}. {STALLED_LIMIT} "
                f"NOTHING WAS ACTUATED BY THIS FLAG — it is a report and no more ({STALLED_LAYER}, "
                f"not the harness permission classifier and not the revival arm). The frontier this "
                f"blocks: {coord.coord_invocation(args)} ready-seats"))
            armed[key] = True
    for key in [k for k in armed if k.split("\t", 1)[0] not in seen]:
        armed.pop(key, None)          # re-arm: a second, genuinely different stall must not be mute
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
    #
    # ---- THE CHARTER OF THIS LOOP (amended by s4-08; goal decisions.md, anchor
    # ---- `r-watch-revival-arm-amends-notify-only`) ----
    # NOTIFY ONLY, WITH EXACTLY ONE EXCEPTION — the seat-down revival arm ruled by
    # `r-leader-revival-is-deterministic` (goal decisions.md, resolve by ANCHOR; ~:3299 today, and
    # that file is append-only and grows, so the number is a HINT and never the citation). That arm
    # relaunches a CRASHED seat's session out-of-pane, from its seat.md, with no agent in the path.
    # Everything else in this loop still closes, kills and relaunches NOTHING: the leader keeps
    # lifecycle, the ctx and inactivity flags stay advisory, and the daemon cutover gate
    # (`r-cutover-gated`) is untouched. The exception is narrow BY CONSTRUCTION: it fires only on a
    # HARD liveness signal (no harness pid behind a roster-ACTIVE row), never on silence.
    #
    # ⚠ THE ACTUATOR COUNT OF THIS FILE IS **ONE**, NOT ZERO AND NOT "SOME" — and it is not a claim
    # made in prose only. The single arm is `fire_revival` (§ revival ACTUATION, s4-06): one
    # `subprocess.Popen` of coord.py's hidden `lifecycle-exec`. The selftest asserts that count over
    # the WHOLE arm's call graph (`s4-06 LG-16 (c)`), with a red arm that inserts `launch_seat` and
    # `tmux_new_window` and reports both — so a SECOND arm added anywhere here turns that row red
    # rather than quietly making this sentence false. Anyone adding one amends THIS charter, the
    # ledger anchor above, and that assertion, in the same act.
    #
    # ⚠ COVERAGE, STATED EXACTLY, because "anywhere here" was too generous the moment a second
    # notify-only arm arrived: LG-16 (c) scans the REVIVAL arm's call graph, and the dag-12
    # stalled-blocking flag below sits OUTSIDE it. That section carries its OWN zero-actuator
    # assertion over its OWN call graph (`dag-12 RS-10`), with its own red arm. So the count is
    # covered by TWO rows, one per arm, and a THIRD arm added in a THIRD place is covered by
    # NEITHER until whoever adds it extends this list. That gap is the honest state of the
    # instrument, not a claim of total coverage.
    #
    # ⚠ AND THE ONE ARM IS A WAY-STATION, NOT A HOME. The ruling, the ground and the migration cost
    # are stated where the arm lives (§ revival ACTUATION) and at `decisions.md#d-watch-is-a-way-
    # station`; they are NOT restated here. Read them before treating this exception as
    # architecture — task 7.35 deletes this file into the goal-watcher-job (CMP-21).
    #
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
                # ---- 7.164 (a) THE DEBOUNCE, and it MIRRORS the revival arm rather than
                # ---- inventing a second convention: a counter in the seat's own state, reset by
                # ---- the healthy observation, threshold DERIVED from REVIVAL_DEBOUNCE_TICKS.
                # One sample was enough to fire this flag while its sibling arm — watching the same
                # physical fact from the roster side — required two. A harness that is mid-restart,
                # a pane read during a relaunch's startup window, and a genuinely dead seat are
                # indistinguishable in ONE sample; on 2026-07-30 03:34 the loop flagged the owner's
                # `master` door off exactly such a window. The counter says nothing new about the
                # seat — it says the observation held.
                gt = int(st.get("ghost_ticks", 0)) + 1
                st["ghost_ticks"] = gt
                if gt < GHOSTROW_DEBOUNCE_TICKS:
                    # Printed EVERY pass, like the revival arm's pending line: a condition being
                    # debounced must never be a condition gone quiet, or the debounce reads as a
                    # mute to anyone watching the report.
                    report.append(f"{agent:<18} GHOSTROW pending — {gt}/{GHOSTROW_DEBOUNCE_TICKS} "
                                  f"consecutive passes with no harness process on pane {pane} "
                                  f"(~{_ticks_minutes(GHOSTROW_DEBOUNCE_TICKS, args)} worst case "
                                  f"at this loop's cadence)")
                else:
                    report.append(f"{agent:<18} GHOSTROW pane {pane} has no harness process "
                                  f"({gt} consecutive passes)")
                    if not st.get("notified_ghostrow"):
                        # ---- 7.164 (b) THE OWNER-DOOR EXEMPTION, scoped to the REMEDY ----
                        #
                        # ⚠ MEASURED. The same 2026-07-30 event produced a GHOSTROW flag naming
                        # `close-seat master --renew` at the owner's door. A PARKED DOOR MATCHES
                        # THIS SHAPE BY DESIGN — `r-owner-afk-liaison-parked` has the door's pane
                        # deliberately SURVIVE its session, so a door between sessions is
                        # byte-identical to a ghost row under the only observation this loop makes.
                        #
                        # ⚠ THE FLAG IS NOT SUPPRESSED — the same reasoning G-176 states at the
                        # inactivity arm: a door in trouble and a door waiting are indistinguishable
                        # from outside, and suppressing here would make the re-mute this fix's own
                        # failure mode. What changes is the REMEDY, and only for the door.
                        #
                        # ⚠ DERIVED FROM `relays:`, NEVER FROM A PANE ID OR A SEAT NAME. `door_seats`
                        # is the ONE resolution the reap exemption and the revival door gate already
                        # use. A rule naming `%40` or `master` protects a dead pane and one
                        # campaign's vocabulary respectively — the standing bar says a live pane id
                        # is resolved at the instant of use and never written into a standing rule.
                        if agent in door_seats:
                            notes.append(Flag(agent,
                                f"watch: '{agent}' is ACTIVE in the roster but pane {pane} has run "
                                f"NO harness process for {gt} consecutive passes — and it declares "
                                f"`relays:`, so its pane is a DOOR to a human role, not a worker's "
                                f"seat. ⚠ A PARKED DOOR MATCHES THIS SHAPE BY DESIGN: the door's "
                                f"pane deliberately outlives its session (r-owner-afk-liaison-parked), "
                                f"so 'no harness behind it' is NOT by itself evidence of a fault — "
                                f"and it is also NOT proof the door is fine. THEY LOOK IDENTICAL "
                                f"FROM OUTSIDE. So LOOK, do not assume either way: "
                                f"tmux capture-pane -p -t {pane}. ⚠ AND DO NOT close, reap or renew "
                                f"this row — that is forbidden on a door, and it is how a run severs "
                                f"the channel its human is reachable through. If the door should be "
                                f"re-opened, that is done by relaunching in THAT SPOT and it is the "
                                f"leader's judgment, never a mechanical response to this flag."))
                        else:
                            notes.append(Flag(agent,
                                f"watch: '{agent}' is ACTIVE in the roster but pane {pane} has run "
                                f"NO harness process for {gt} consecutive passes — the row claims a "
                                f"seat that is not there. Its work is stopped and every wake sent to "
                                f"it is typed into a bare shell. Inspect FIRST "
                                f"(tmux capture-pane -p -t {pane}), then either relaunch or close "
                                f"it: {coord.coord_invocation(args)} close-seat {agent} --renew"))
                        st["notified_ghostrow"] = True
            elif hp:
                # A harness seen behind the row is the healthy observation, so it BOTH re-arms the
                # notification and clears the debounce — an intermittent read must not accumulate
                # across healthy passes into a fire.
                st.pop("notified_ghostrow", None)
                st.pop("ghost_ticks", None)
            # ⚠ THE THIRD CASE IS DELIBERATE AND IS NEITHER BRANCH: an UNVERIFIABLE process table
            # (`verifiable` false) FREEZES the counter — it neither counts nor resets. A reading
            # that could not be taken is evidence in neither direction, the same asymmetry the
            # revival arm applies to a stale snapshot. Resetting here would let a flapping /proc
            # hold a genuinely dead seat below the threshold forever.
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

    # dag-12, NOTIFY-ONLY: the shape-A backstop. A snapshot-level duty like the revival detector, so
    # it sits beside it and not in the per-seat loop — its candidate set is the snapshot's, and the
    # per-seat loop below would reset the arming state it keeps. It runs AFTER the detector on
    # purpose: for a CRASHED seat the reader should meet the classification first and this flag
    # second, as the thing that says who is waiting on it. ⚠ Its lines stay OUT of `report` for the
    # same reason the revival lines do — the pass header counts `report` as "N active seat(s)".
    # ⚠ IT ACTUATES NOTHING; the charter's one exception above is `fire_revival` and stays one.
    stalled_lines = check_stalled_blocking(args, base, snap, snap_err, state, notes)

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
                    # s4-08: the remedy is the SEAT'S OWN act. Renewal stopped being a thing done
                    # TO a seat when stage 2 landed `checkout --renew --handoff`; the closer is the
                    # FAILURE path, for a seat that cannot check itself out (s3-13's sweep of the
                    # seat-facing docs). ⚠ The reader is the LEADER, so both halves are phrased as
                    # something to relay or to do, never as an instruction aimed at a seat that
                    # will not read it.
                    notes.append(Flag(agent, f"watch: '{agent}' has shown no pane activity for {inact_min} min "
                                 f"(threshold {args.inactive_min}). Check on it. If it answers and is "
                                 f"done-but-stuck, renewal is ITS act: tell it to run "
                                 f"`{coord.coord_invocation(args)} checkout --renew` and carry a "
                                 f"`--handoff` on the second call. If it cannot answer at all, that is the "
                                 f"failure path and it is yours: "
                                 f"{coord.coord_invocation(args)} close-seat {agent} --renew"))
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
                # s4-08: same correction as the inactivity flag above. A seat past its ctx
                # threshold is ALIVE — it is exactly the seat that CAN check itself out — so the
                # remedy is the seat's OWN two-step `checkout --renew --handoff`, and the closer is
                # not in that path at all. ⚠ THE READER OF THIS TEXT IS THE LEADER, NOT THE SEAT
                # (`--notify-to`, and a flag is never sent to the seat it is about), so it is
                # written as something to RELAY — an instruction phrased at the seat would be read
                # by whoever cannot perform it.
                notes.append(Flag(agent, f"watch: '{agent}' context is at {pct}% (threshold {threshold}%"
                             f"{source}). Renewal is the SEAT'S OWN act, not yours: tell '{agent}' to run "
                             f"`{coord.coord_invocation(args)} checkout --renew` (that arms it and prints "
                             f"the second call, which carries `--handoff \"<what its next session must "
                             f"do>\"`; nothing is closed until that second call). Reach for "
                             f"`{coord.coord_invocation(args)} close {agent} --renew` — the closer, the "
                             f"FAILURE path — only if '{agent}' cannot check itself out."))
                st["notified_context"] = True

        ctx = f" ctx={pct}%" if pct is not None else ""
        act = f" idle={inact_min}min" if inact_min is not None else ""
        report.append(f"{agent:<18} {'FLAG' if flags else 'ok':<7} {harness:<9}{ctx}{act}"
                      f"  {' '.join(flags)}")
        state[agent] = st

    save_state(base, state)
    save_sys_state(base, sysstate)
    save_heartbeat(base, getattr(args, "cadence_s", None), daemon, daemon_change, daemon_code,
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
    for line in stalled_lines:
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
        # s4-08: the label used to say "with close --renew hint" while the body asserted only
        # "no pane activity" — a label-body mismatch that would have stayed green through the very
        # sweep that changed the hint. The hint is now asserted, in BOTH halves and in the negative.
        check("inactivity: stale pane flagged, and the hint is the SEAT'S OWN `checkout --renew` "
              "with `close-seat` as the failure path — never the superseded `close <seat> --renew`",
              any("alpha" in n and "no pane activity" in n and "checkout --renew" in n
                  and "close-seat alpha --renew" in n and "close alpha --renew" not in n
                  for n in notes))
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
        # s4-08: the ctx flag's REMEDY had no assertion at all — every ctx row above tests WHEN it
        # fires and none tested WHAT it tells the reader to do, so the superseded "have the closer
        # close and RENEW it now" survived every green this suite ever produced. Asserted now, in
        # both directions: the seat's own two-step must be named AND the superseded bare
        # `close <seat> --renew` must be absent as the primary remedy.
        check("⚠ s4-08: the ctx flag names the SEAT'S OWN `checkout --renew` (+ `--handoff`) as the "
              "remedy and the closer only as the failure path — the amended charter's coaching, "
              "which nothing asserted before this row existed",
              any("'eta'" in n and "checkout --renew" in n and "--handoff" in n
                  and "cannot check itself out" in n
                  and "Have the closer close and RENEW it now" not in n for n in notes))

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
        import io as _io
        import contextlib as _cl

        def run_pass_capturing(a):
            """(notes, printed report lines) — the report is PRINTED, not returned, and 7.164's
            pending line lives only there. Same `run_pass`, stdout captured; never a second
            implementation of the loop."""
            buf = _io.StringIO()
            with _cl.redirect_stdout(buf):
                nts = run_pass(a)
            return nts, [ln.strip() for ln in buf.getvalue().splitlines()]

        # THE ARM'S OWN SOURCE, read from disk. F-164c is a claim about what the code CONTAINS
        # (a literal pane id or a seat name), and no behavioural fixture can observe an absent
        # literal — only reading the arm can.
        def _ghostrow_arm_src(code_only=False):
            whole = Path(__file__).read_text()
            i = whole.index("7.164 (a) THE DEBOUNCE")
            j = whole.index("Stage 4 §1 (s4-03), REPORT-ONLY", i)
            arm = whole[i:j]
            if not code_only:
                return arm
            # ⚠ COMMENTS ARE STRIPPED, AND THAT IS THE POINT. The claim below is about what the
            # arm EXECUTES, not what it says: the arm's prose names the 2026-07-30 `master`
            # incident on purpose, and a check that forbade the word would fail on correct code
            # for citing its own evidence — the same false-red G-176 records one line down.
            return "\n".join(ln.split("#", 1)[0] for ln in arm.splitlines())

        def _derived_exemption(src):
            """F-164c as ONE predicate, so its green row and its red row cannot drift apart."""
            return ("%" not in src and "master" not in src and "door_seats" in src)

        check("7.164 fixture guard: the arm slice actually isolates the ghostrow arm, and the "
              "code-only view still carries the arm's logic — a slice that missed, or a strip "
              "that ate the code, would make every absence check below vacuously green",
              "notified_ghostrow" in _ghostrow_arm_src()
              and "notified_ghostrow" in _ghostrow_arm_src(code_only=True)
              and len(_ghostrow_arm_src()) < len(Path(__file__).read_text()) / 10)

        pane_harness["%1"] = []          # alpha's pane: shell only, no harness
        notes, report_lines = run_pass_capturing(ns(context_pct=90))
        # ---- 7.164 (1): THE DEBOUNCE, ASSERTED IN THE SUPPRESSING DIRECTION FIRST ----
        # This row is the one that goes red if the debounce is deleted, and it is written before
        # the firing row on purpose: a debounce is only ever proved by the tick that does NOT fire.
        check("⚠ 7.164 (1) THE SUPPRESSING ARM: ONE sample does NOT fire GHOSTROW. Before this, a "
              "single un-debounced read fired it — and on 2026-07-30 03:34 that read was taken "
              "inside a relaunch's own startup window, at the owner's door",
              not any("NO harness process" in n for n in notes))
        check("7.164 (1b): the pending condition is REPORTED every pass while it debounces — a "
              "condition being debounced must never be a condition gone quiet",
              any(l.startswith("alpha") and "GHOSTROW pending" in l
                  and f"1/{GHOSTROW_DEBOUNCE_TICKS}" in l for l in report_lines))
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: a roster-ACTIVE row whose pane runs NO harness process is flagged "
              "GHOSTROW and the leader is told — the roster is the run's map of what is alive, "
              "and until now nothing ever checked it against the process table. 7.164: it now "
              "takes the SECOND consecutive pass, which is what makes the row above meaningful",
              any("alpha" in n and "NO harness process" in n for n in notes))
        check("PROP-11: the notification says what it costs (work stopped, wakes typed into a "
              "bare shell) and names the exact remedy — THIS FLAG notifies and never acts. Scoped "
              "to the ghostrow flag deliberately (s4-08): the file's charter is no longer "
              "notify-only file-wide, so a label claiming that would be false; what stays true, "
              "and is what this row asserts, is that the GHOSTROW path takes no action itself",
              any("typed into a bare shell" in n and "close-seat alpha --renew" in n
                  for n in notes))
        # Captured from a REAL firing, so the 7.164 door control below compares against an ordinary
        # seat's ACTUAL ghostrow remedy rather than a re-derived expectation of one.
        alpha_ghost = next((n for n in notes if "alpha" in n and "NO harness process" in n), "")
        check("⚠ 7.164 (2) THE DEBOUNCE IS NOT A MUTE: a SUSTAINED condition does fire. F-164b is "
              "the failure this row exists to catch — a debounce that never releases is worse "
              "than none, because the loop then reports a dead seat as healthy",
              bool(alpha_ghost))
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: armed once per seat/pane, like every other flag",
              not any("NO harness process" in n for n in notes))
        pane_harness["%1"] = [4242]      # a harness came back up
        run_pass(ns(context_pct=90))
        check("7.164 (3): a harness seen behind the row CLEARS the debounce counter as well as "
              "re-arming the notification — otherwise intermittent reads accumulate across "
              "HEALTHY passes into a fire, which is a debounce in name only",
              "ghost_ticks" not in (load_state(base).get("alpha") or {}))
        pane_harness["%1"] = []
        notes = run_pass(ns(context_pct=90))
        check("⚠ 7.164 (3b) THE DISCRIMINATING ARM of the reset: the first pass after a healthy "
              "one does NOT fire. Had the reset not happened, the pre-existing count would carry "
              "over and this pass would fire — that is the only observation separating a cleared "
              "counter from an uncleared one",
              not any("NO harness process" in n for n in notes))
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: re-arms once a harness is seen again, so a second death is reported",
              any("NO harness process" in n for n in notes))
        pane_harness["%1"] = None        # unverifiable
        notes = run_pass(ns(context_pct=90))
        check("PROP-11: 'cannot tell' is NOT 'nothing running' — an unreadable process table "
              "raises nothing (fail-safe, same asymmetry as coord's checkin guard)",
              not any("NO harness process" in n for n in notes))
        check("7.164 (4): an UNVERIFIABLE process table FREEZES the debounce counter — it neither "
              "counts nor resets. A reading that could not be taken is evidence in neither "
              "direction; resetting here would let a flapping /proc hold a dead seat below the "
              "threshold forever",
              (load_state(base).get("alpha") or {}).get("ghost_ticks") == GHOSTROW_DEBOUNCE_TICKS)

        # ---- 7.164: THE OWNER-DOOR EXEMPTION — a DOOR IS NOT A GHOST ROW ----
        # ⚠ MEASURED, NOT ARGUED. On 2026-07-30 this arm's flag named `close-seat master --renew`
        # at the owner's door. A parked door matches the ghostrow shape BY DESIGN
        # (r-owner-afk-liaison-parked has its pane outlive its session), so the flag proposed
        # closing the one pane a standing ruling says is never reapable.
        # The `door` seat is IDENTICAL to `alpha` in every respect but its `relays:` declaration —
        # that declaration is the only thing permitted to change the outcome.
        pane_harness["%3"] = []          # door's pane (checked in at %3 by the G-176 block above)
        run_pass(ns(context_pct=90))     # tick 1 — debounce
        notes = run_pass(ns(context_pct=90))
        door_ghost = next((n for n in notes if "door" in n and "NO harness process" in n), "")
        check("⚠ 7.164 (5) THE DOOR STILL FLAGS. Suppressing it would make the re-mute this fix's "
              "own failure mode: a door in trouble and a parked door are indistinguishable from "
              "outside, and the door is the last pane a run can afford to lose unreported",
              bool(door_ghost))
        check("⚠ 7.164 (5b) THE DOOR'S REMEDY HANDS THE READER NO CLOSE/RENEW INVOCATION — this "
              "is F-164a, the exact false positive the row exists to remove. Asserts the ABSENT "
              "COMMAND, not absent words: the text itself says 'DO NOT close, reap or renew', so "
              "forbidding the vocabulary would fail on correct code",
              bool(door_ghost) and "close-seat door" not in door_ghost
              and "--renew" not in door_ghost)
        check("7.164 (5c): the door's remedy says DOOR, tells the reader to LOOK first, and names "
              "the ruling — and it does NOT reassure: it states that a parked door and a failing "
              "door look identical, so the text can never talk a reader out of looking",
              "DOOR" in door_ghost and "capture-pane" in door_ghost
              and "r-owner-afk-liaison-parked" in door_ghost
              and "LOOK IDENTICAL FROM OUTSIDE" in door_ghost.upper())
        check("⚠ 7.164 (5d) THE CONTROL — the ORDINARY seat's ghostrow remedy is UNCHANGED and "
              "still carries the close-seat --renew invocation. THE TWO ARMS MUST DIFFER: "
              "suppressing the invocation on BOTH would pass a one-arm test and break the "
              "detector for every worker in the run",
              "--renew" in alpha_ghost and "DOOR" not in alpha_ghost
              and alpha_ghost != door_ghost)
        check("⚠ 7.164 (5e) THE EXEMPTION IS DERIVED, NOT A LITERAL — F-164c. It keys on the "
              "`relays:` declaration through `door_seats`, the same resolution the reap exemption "
              "and the revival door gate use. No pane id and no seat name appears in the arm: a "
              "rule naming a live id protects a DEAD pane, and a name list encodes one campaign's "
              "vocabulary into a kit every run shares. Asserted over the arm's EXECUTABLE lines "
              "only — the arm's prose cites the `master` incident that produced this row, and "
              "forbidding the word would fail on correct code for naming its own evidence",
              _derived_exemption(_ghostrow_arm_src(code_only=True)))
        check("⚠ 7.164 (5f) RED ARM for the row above — THE SAME PREDICATE over the SAME arm with "
              "a literal pane id and a seat name inserted goes FALSE, so (5e) is a check and not "
              "a decoration: it is the row that catches the next person who hardcodes one",
              not _derived_exemption(_ghostrow_arm_src(code_only=True)
                                     + '\nif agent == "master" or pane == "%40": pass\n'))
        pane_harness.clear()
        coord.cmd_checkin(argparse.Namespace(package=str(pkg), base=None, workers_dir=None,
                                             agent="watcher", summary="w", pane="%3"))
        pane_harness["%3"] = []
        run_pass(ns(context_pct=90))
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
        # ⚠ 7.112 THE CROSS-MODULE SEAM, AND IT IS THE RISKIEST THING IN THIS CHANGE. The cadence is
        # now SECONDS, but `coord.watcher_heartbeat()` still judges staleness off the legacy
        # minute-denominated `loop_min` — and coord.py is NOT this task's to edit. Had the writer
        # simply dropped that field, coord's `isinstance(loop_min, int)` test would fail and staleness
        # would silently become a FLAT 30 MINUTES for a 30-SECOND loop: a dead sensor unreported ~20x
        # longer, with nothing to notice it. This row drives a REAL pass at a 30 s cadence and asserts
        # what coord actually computes from it, because the two modules only meet on disk.
        run_pass(ns(context_pct=90, cadence_s=30))
        _hb30 = json.loads((base / "watch-heartbeat.json").read_text(encoding="utf-8"))
        _rd30 = coord.watcher_heartbeat(base)
        check("⚠ 7.112 the heartbeat a 30 s loop writes is READABLE BY coord.py's UNCHANGED reader: "
              "it carries loop_seconds=30 AND a ceiled loop_min=1, so coord derives a 3-MINUTE "
              "staleness deadline. Dropping loop_min would have silently handed a 30-second loop the "
              "flat 30-MINUTE fallback — the weaker-sensor-nobody-notices defect (G-42) arriving "
              "through a data field instead of an argv",
              _hb30.get("loop_seconds") == 30 and _hb30.get("loop_min") == 1
              and _rd30 is not None and _rd30["stale_after"] == 3)

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
        # `cadence_s=30` is the RULED cadence (`r-watch-loop-30s`), and it is here because the
        # revival report line now DERIVES its latency from the cadence in force instead of carrying a
        # literal. Without it these rows would run as a one-shot pass and the latency assertion in
        # (7) below could only ever see "n/a (one-shot)" — green, and blind to the derivation.
        rargs = argparse.Namespace(package=str(rpkg), base=None, workers_dir=None,
                                   notify_to="leader", notify_fallback="leader", cadence_s=30)

        # ⚠⚠ NO TMUX ANYWHERE IN THIS SUITE — the bar the s4-05 block declared, re-declared by
        # s4-06 and now LOAD-BEARING rather than incidental: s4-06 gave `check_revival` a FIRE, and
        # the fire reads tmux (`live_panes`, `tmux_pane_window_name`, `tmux_find_window_pane`) and
        # forks. Left alone, EVERY pre-existing s4-03/s4-04/s4-05 row that reaches CRASHED would
        # shell out to the real tmux server and fork a real executor at the developer's live room.
        # The three READS are substituted here for the whole revival region; `subprocess.Popen` is
        # substituted ONLY inside the s4-06 rows, and restored immediately.
        #
        # ⚠ THE DEFAULT STATE IS "NO PANES, NO ANCHOR", WHICH IS ITSELF THE NO-TARGET REFUSAL. So
        # every row that predates s4-06 exercises the fire's REFUSAL path and forks nothing — that
        # is deliberate, and it is why those rows still prove what they proved: the fire cannot
        # reach `Popen` without a target, and no row below hands it one by accident.
        _tmux_real = (coord.live_panes, coord.tmux_pane_window_name, coord.tmux_find_window_pane)
        _fx = {"panes": set(), "wname": "", "anchor": ""}
        coord.live_panes = lambda: set(_fx["panes"])
        coord.tmux_pane_window_name = lambda pane: _fx["wname"]
        coord.tmux_find_window_pane = lambda sess, win: _fx["anchor"]

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

        # s4-04 made the descriptor LOAD-BEARING: an undeclared `mode:` is UNDECIDABLE and the
        # detector refuses, so every row below that must REACH the CRASHED branch needs a real
        # descriptor on disk. Written as a real seat file and read back through
        # `coord.discover_workers` — the production path — so these fixtures never assert against
        # a hand-built dict this suite invented.
        rwork = rpkg / "workers"
        rwork.mkdir(parents=True, exist_ok=True)

        def rdecl(seat="dseat", mode="interactive", harness=None, relays=None):
            fm = ["---", f"agent: {seat}"]
            if harness:
                fm.append(f"harness: {harness}")
            if mode:
                fm.append(f"mode: {mode}")
            if relays:
                fm.append(f"relays: {relays}")
            fm += ["---", "", "seat body"]
            (rwork / f"{seat}.md").write_text("\n".join(fm) + "\n", encoding="utf-8")

        def rowner(state):
            """Write the owner-state surface s4-14's gate reads, or REMOVE it when state is None.

            Written through the same shape `coord.owner_status` parses off a live run, never a
            hand-built dict: a fixture that supplies its own parse tests the branch and not the
            integration — the bar the s4-04 block above sets and this one inherits."""
            f = rbase / "owner-status.md"
            if state is None:
                f.unlink(missing_ok=True)
                return
            f.write_text("# owner-status — script-managed\n"
                         f"owner: {state} | since 2026-01-01 00:00 — fixture\n", encoding="utf-8")

        rdecl()
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
              "CRASHED — " in " ".join(l5)
              and "CRASHED — " not in " ".join(l4))
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
              gt() == 1 and "CRASHED — " not in " ".join(l1)
              and "1/2" in " ".join(l1) and "60s" in " ".join(l1))
        l2, _ = rev(rsnap(absent=[gone()]))
        check("s4-03 (7): the second consecutive non-stale tick classifies CRASHED",
              gt() == 2 and "CRASHED — " in " ".join(l2))
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
              gt() == 1 and "CRASHED — " not in " ".join(l3))
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
              "CRASHED — " in " ".join(l3))
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
              "CRASHED — " in " ".join(l4) and "MID-RENEWAL" not in " ".join(l3 + l4))
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

        # ---- Stage 4 D-3C (s4-04): THE COMPLETED-ONE-SHOT GATE ----
        # Every row drives the gate through a REAL descriptor written to disk and read back by
        # `coord.discover_workers`, never a hand-built dict: a fixture that supplies its own parse
        # tests the branch and not the integration. NO TMUX and NO ACTUATION anywhere in this
        # block. ⚠ WAY-STATION: these rows travel with the gate to the goal-watcher-job at 7.35.
        import ast as _ast_mod
        import textwrap as _textwrap

        def twice(**kw):
            """Two consecutive ticks — the debounce — returning (all lines, notes pushed).

            The marker is cleared too: a row that DOES reach CRASHED leaves a real claim on disk,
            and a later row would then stand down against its predecessor's claim rather than
            exercising its own path. Measured while building this block — the resurrection mutant
            below reported STOOD-DOWN and read as a green gate."""
            (rbase / "lifecycle-inflight.json").unlink(missing_ok=True)
            rstate.clear(); rnotes.clear()
            l1, p1 = rev(rsnap(absent=[gone()], **kw))
            l2, p2 = rev(rsnap(absent=[gone()], **kw))
            return l1 + l2, p1 + p2

        # LG-10 — a one-shot seat is NEVER revived, however long it stays absent.
        rdecl(mode="one-shot")
        lo, po = twice()
        check("⚠ s4-04 LG-10: a seat whose descriptor declares `mode: one-shot` is NEVER revived, "
              "however many ticks it is absent — its absence is its SUCCESS. Without this gate a "
              "CORRECT detector resurrects every finished one-shot forever, and the relaunch loop "
              "looks exactly like working machinery",
              all(REVIVAL_ONE_SHOT_LINE in l for l in lo)
              and not any("CRASHED" in l for l in lo) and gt() == 0)
        # THE CONTROL, and it is the same fixture with one key changed.
        rdecl(mode="interactive")
        li, _ = twice()
        check("⚠ s4-04 LG-10 CONTROL: the IDENTICAL fixture with `mode: interactive` DOES reach "
              "CRASHED — one key, opposite verdict. A gate that never lets anything through is "
              "indistinguishable from a detector that is switched off",
              "CRASHED — " in " ".join(li))

        # LG-11 — the gate reads `mode:`, not `harness:`. Both rows are the cases a harness-keyed
        # implementation gets BACKWARDS, so `harness == "opencode"` passes neither.
        rdecl(mode="interactive", harness="opencode")
        lopen, _ = twice()
        check("⚠ s4-04 LG-11 (a): `harness: opencode` + `mode: interactive` → revival FIRES. "
              "Harness is a proxy that is true today and breaks the moment an opencode seat runs "
              "in TUI mode; gating on the proxy is how a correct rule becomes wrong SILENTLY",
              "CRASHED — " in " ".join(lopen))
        rdecl(mode="one-shot", harness="claude")
        lclaude, _ = twice()
        check("⚠ s4-04 LG-11 (b): `harness: claude` + `mode: one-shot` → revival does NOT fire. "
              "With (a) above this is the pair no harness-keyed gate can pass, and the descriptor "
              "the two rows differ in is the DECLARED property, never the proxy",
              all(REVIVAL_ONE_SHOT_LINE in l for l in lclaude)
              and not any("CRASHED" in l for l in lclaude))

        # LG-12 — HANDLED, NOT MERELY SKIPPED. The gate does not RUN the arm (this loop actuates
        # nothing beyond its one ruled revival fire), so what is proven here is that the route it
        # names is REAL: the command exists in coord's own parser with the flag the note prints.
        # ⚠ WHAT IS **NOT** PROVEN HERE: that an `exited` disposition is actually written. That
        # requires executing `coordinate attest-exit --go`, which is actuation this task may not
        # perform — it is the arm's own acceptance (dag-11), and is named as the gap it is.
        rdecl(mode="one-shot")
        lh, ph = twice()
        _sp = next((a for a in coord.build_parser()._subparsers._group_actions
                    if getattr(a, "choices", None)), None)
        check("⚠ s4-04 LG-12: the one-shot seat is HANDED OFF, not dropped — the line and exactly "
              "one note name the attest-exit arm and the seat. A gate that silently skips the seat "
              "has traded a resurrection loop for a PERMANENT STALL: the roster still reads "
              "active, the ready arithmetic still reads 'working', and the successor never becomes "
              "ready (the measured F1 failure, seat `oc2`)",
              len(ph) == 1 and f"{REVIVAL_ATTEST_CMD} --seat dseat" in ph[0]
              and all(f"{REVIVAL_ATTEST_CMD} --seat dseat" in l for l in lh))
        check("⚠ s4-04 LG-12: the command the note prints EXISTS — `attest-exit` is a real "
              "subcommand of coord's own parser and really takes `--seat`. A hand-off to a "
              "command that does not exist is the same permanent stall wearing a report line, and "
              "a string this suite compares to another string in this file would never catch it",
              _sp is not None and "attest-exit" in _sp.choices
              and "--seat" in {o for act in _sp.choices["attest-exit"]._actions
                               for o in act.option_strings}
              # RED ARM for this row: the same membership test on a name that does NOT exist must
              # answer False, or the row would pass for any string at all.
              and REVIVAL_ATTEST_CMD.split()[-1] + "-nope" not in _sp.choices)

        # Row 4 — MISSING `mode:` IS UNDECIDABLE, NOT A DEFAULT. A single-arm test here cannot tell
        # "refused" from "defaulted to one-shot", so both controls run below.
        rdecl(mode=None)
        lu, pu = twice()
        check("⚠ s4-04 (4): a descriptor with NO `mode:` key on a roster-absent seat is "
              "UNDECIDABLE — no revival, a refusal line NAMING THE KEY, printed every tick, and "
              "EXACTLY ONE note. Defaulting either way ships one of the two failure modes in "
              "silence; SC-14 makes the missing key a defect at EMISSION, not a guess here",
              len(pu) == 1 and all("REVIVAL REFUSED" in l and "mode: <key absent>" in l
                                   for l in lu)
              and not any("CRASHED" in l or REVIVAL_ONE_SHOT_LINE in l for l in lu))
        check("⚠ s4-04 (4) R-8: the refusal's LAYER STRING LEADS the note body, so a reader can "
              "never mistake this TOOL GATE for the harness permission classifier",
              pu[0].startswith(REVIVAL_MODE_LAYER))
        _moved = pu[0][len(REVIVAL_MODE_LAYER):].strip() + " " + REVIVAL_MODE_LAYER
        check("⚠ s4-04 (4) RED ARM for the row above: the SAME predicate applied to the SAME body "
              "with the layer string moved to the END returns False — so the assertion "
              "discriminates position, and is not a substring check that any wording would pass",
              REVIVAL_MODE_LAYER in _moved and not _moved.startswith(REVIVAL_MODE_LAYER))
        check("⚠ s4-04 (4) CONTROL (a): adding `mode: interactive` to that same descriptor makes "
              "revival FIRE — the refusal was the missing key, not the fixture",
              (rdecl(mode="interactive") or True)
              and "CRASHED — " in " ".join(twice()[0]))
        check("⚠ s4-04 (4) CONTROL (b): adding `mode: one-shot` instead takes the ATTEST route — "
              "with (a) this is what tells a REFUSAL from a silent default to one-shot, which a "
              "single-arm test cannot",
              (rdecl(mode="one-shot") or True)
              and REVIVAL_ONE_SHOT_LINE in " ".join(twice()[0]))
        check("⚠ s4-04 (4): an UNRECOGNISED value is refused too, not waved through as 'declared "
              "something' — the gate's two known values are the whole vocabulary, and a typo in a "
              "descriptor must not become an authorization",
              (rdecl(mode="one_shot") or True)
              and "REVIVAL REFUSED" in " ".join(twice()[0]))
        # ⚠ A FREEZE AND A RESET ARE INDISTINGUISHABLE FROM A ZERO COUNTER — the first draft of
        # this row asserted `gt() == 0` after two undecidable ticks and would have passed either
        # way. The counter has to be NON-ZERO first, so the two answers differ: 1 (frozen) vs 0.
        rstate.clear(); rnotes.clear()
        (rbase / "lifecycle-inflight.json").unlink(missing_ok=True)
        rdecl(mode="interactive")
        rev(rsnap(absent=[gone()]))
        _before_freeze = gt()
        rdecl(mode=None)
        rev(rsnap(absent=[gone()]))
        check("⚠ s4-04: the UNDECIDABLE branch FREEZES the debounce rather than resetting it — an "
              "undeclared mode is evidence in NEITHER direction, exactly like a stale snapshot, so "
              "the counter neither advances toward a fire nor forgets the absence. Measured from a "
              "NON-ZERO counter: a reset would read 0 here and a zero counter cannot tell the two "
              "apart",
              _before_freeze == 1 and gt() == 1)
        rdecl(mode="interactive")
        rev(rsnap(absent=[gone()]))
        check("⚠ s4-04 CONTROL for the freeze: once the descriptor declares a mode again the "
              "counter RESUMES from the frozen value and fires — proving the freeze preserved "
              "evidence rather than merely stalling the arm forever",
              gt() == 2)

        # Row 5 — ORDERING IS LOAD-BEARING, exercised by MUTATING the function, not by reading it.
        _gate_src = inspect.getsource(check_revival)
        _anchor = '        mode = (decls.get(seat) or {}).get("mode") or ""'
        _gate_block_end = '            st["revival"] = rev\n            continue\n'
        _lines = _gate_src.split(_anchor, 1)
        check("s4-04 (5) PRECONDITION: the ordering mutant below really has an anchor to move — a "
              "mutation that silently fails to apply is a green that proves nothing",
              len(_lines) == 2 and _lines[1].count(_gate_block_end) >= 2)
        _cut = _lines[1].rfind(_gate_block_end, 0, _lines[1].find("# (4) MID-RENEWAL"))
        _gate_body = _anchor + _lines[1][:_cut + len(_gate_block_end)]
        _moved_src = _gate_src.replace(_gate_body, "") + "\n"
        _moved_src = _moved_src.replace("        st[\"revival\"] = rev\n\n    return lines",
                                        "        st[\"revival\"] = rev\n" + _gate_body
                                        + "\n    return lines")
        def _run_mutant(src, tag):
            _ns = dict(globals())
            exec(compile(src, tag, "exec"), _ns)
            rdecl(mode="one-shot")
            (rbase / "lifecycle-inflight.json").unlink(missing_ok=True)
            rstate.clear(); rnotes.clear()
            _ns["check_revival"](rargs, rbase, rsnap(absent=[gone()]), None, rstate, rnotes)
            return _ns["check_revival"](rargs, rbase, rsnap(absent=[gone()]), None,
                                        rstate, rnotes)

        _lm = _run_mutant(_moved_src, "<s4-04 ordering mutant>")
        check("⚠ s4-04 (5) THE ORDERING RED ARM: the same function with the gate MOVED BELOW the "
              "CRASHED branch CLASSIFIES the one-shot seat CRASHED — LG-10 goes RED. A gate placed "
              "after the branch it guards is DEAD CODE THAT READS AS LIVE, and only a mutant that "
              "actually runs can tell the two apart",
              any("CRASHED" in l for l in _lm))
        # ⚠ MEASURED, and disclosed rather than glossed: in THAT mutant the claim does not fire —
        # not because the ordering is harmless, but because the gate's own `gone_ticks = 0` reset
        # runs AFTER the CRASHED branch and starves the debounce. So the mutant above proves the
        # misclassification and NOT the resurrection. This second mutant removes that accidental
        # barrier — gate moved AND its reset dropped — and the resurrection is real: a `mode:
        # one-shot` seat is CLAIMED for revival, marker on disk.
        _no_reset = _gate_body.replace('            rev["gone_ticks"] = 0\n'
                                       '            st["revival"] = rev\n            continue\n',
                                       '            st["revival"] = rev\n            continue\n', 1)
        check("s4-04 (5) PRECONDITION: the second ordering mutant really dropped the reset — a "
              "mutation that silently fails to apply would make the row below vacuous",
              _no_reset != _gate_body)
        _lm2 = _run_mutant(_gate_src.replace(_gate_body, "").replace(
            '        st["revival"] = rev\n\n    return lines',
            '        st["revival"] = rev\n' + _no_reset + "\n    return lines"),
            "<s4-04 ordering mutant, no reset>")
        check("⚠ s4-04 (5) THE RESURRECTION ITSELF: with the gate below CRASHED and its debounce "
              "reset removed, a `mode: one-shot` seat is CLAIMED FOR REVIVAL and the marker lands "
              "on disk — the exact forever-relaunch of a finished one-shot this gate exists to "
              "prevent. This is why the ORDER is load-bearing and not stylistic",
              "claim CLAIMED" in " ".join(_lm2)
              and json.loads((rbase / "lifecycle-inflight.json").read_text()
                             )["dseat"]["disposition"] == "revive")
        (rbase / "lifecycle-inflight.json").unlink()
        rdecl(mode="one-shot")
        rstate.clear(); rnotes.clear()
        check("⚠ s4-04 (5) GREEN: the SHIPPED order — gate BEFORE CRASHED — never reaches the "
              "CRASHED branch for the identical fixture. Paired with the mutant above, this is "
              "the observation that makes the ordering load-bearing rather than incidental",
              "CRASHED" not in " ".join(twice()[0]))

        # ---- Stage 4 (s4-14): THE OWNER-DOOR GATE ----
        # Every row drives a REAL descriptor and a REAL `owner-status.md` through the same parsers
        # the live loop uses (`coord.inbox_decls`, `coord.owner_status`) — never a hand-built dict,
        # for the reason the s4-04 block states. NO TMUX and NO ACTUATION anywhere in this block.
        # ⚠ WAY-STATION: these rows travel with the gate to the goal-watcher-job at 7.35.
        (rbase / "lifecycle-inflight.json").unlink(missing_ok=True)
        rstate.clear(); rnotes.clear()

        def _door_gate_src():
            """The gate's OWN bytes, sliced by its section markers — so row (e) scopes its claim
            to the gate rather than to the whole function, where an unrelated literal elsewhere
            would make it pass or fail for the wrong reason."""
            src = inspect.getsource(check_revival)
            return src.split("(4a) s4-14")[1].split("(4b) s4-07")[0]

        # (a) THE RULING ITSELF — owner `afk` + a door seat ⇒ the door stays shut.
        rdecl(mode="interactive", relays="master")
        rowner("afk")
        lafk, pafk = twice()
        check("⚠ s4-14 (a) THE OWNER RULING: a roster-absent seat declaring `relays:` is NOT "
              "revived while the owner's declared state is `afk`. Measured cause: on 2026-07-30 "
              "this arm relaunched run-3's owner door ~60s after the owner closed it himself — a "
              "door with no harness behind it is byte-identical to a crashed seat, and the axis "
              "that separates them is the owner's own state, not any descriptor key",
              all(REVIVAL_DOOR_LINE in l for l in lafk)
              and not any("CRASHED" in l for l in lafk) and gt() == 0)
        check("⚠ s4-14 (a) R-8: the refusal's LAYER STRING LEADS the note body, so a reader can "
              "never mistake this TOOL GATE for the harness permission classifier",
              len(pafk) == 1 and pafk[0].startswith(REVIVAL_DOOR_LAYER))

        # (a-RED) THE MUTATION. A green that could not have gone red is not evidence: widen the
        # admitted set to include `afk` — the gate still RUNS, still keys on `relays:`, and only
        # stops DISCRIMINATING on owner state — and the row above must flip to CRASHED.
        _door_states_shipped = REVIVAL_DOOR_STATES
        try:
            globals()["REVIVAL_DOOR_STATES"] = ("present", "reachable", "afk")
            lmut, _ = twice()
        finally:
            globals()["REVIVAL_DOOR_STATES"] = _door_states_shipped
        check("⚠ s4-14 (a) RED ARM: with `afk` ADDED to the admitted set — the gate otherwise "
              "untouched — the IDENTICAL fixture reaches CRASHED. So row (a) discriminates on the "
              "owner's state rather than passing for some unrelated reason, and the shipped tuple "
              "is what holds the door shut",
              "CRASHED — " in " ".join(lmut))
        check("⚠ s4-14 (a) RED-ARM RESTORE: the shipped admitted set is back in place, so the "
              "mutation cannot leak into any row below it",
              REVIVAL_DOOR_STATES == ("present", "reachable"))

        # (b) SCOPE — the claim "only the door is affected" made into a control, not left an assertion.
        rdecl(mode="interactive", relays=None)
        lnodoor, _ = twice()
        check("⚠ s4-14 (b) SCOPE CONTROL: the SAME fixture under the SAME `afk` owner state, with "
              "`relays:` REMOVED, IS revived — one key, opposite verdict. This is what proves the "
              "gate touches the owner's door alone and leaves overnight revival of the leader, the "
              "planner and every worker exactly as it was",
              "CRASHED — " in " ".join(lnodoor))

        # (c) FAIL-CLOSED — an owner state nobody can read does NOT open a human's door.
        rdecl(mode="interactive", relays="master")
        rowner(None)
        lmissing, _ = twice()
        check("⚠ s4-14 (c) FAIL-CLOSED, no owner-status.md at all: the door is NOT revived. "
              "Elsewhere in this arm an unprovable premise holds the act; here the act is starting "
              "a session AT A HUMAN, which he cannot un-see — so the unreadable case resolves to "
              "'leave it shut', never to 'assume he wants it'",
              all(REVIVAL_DOOR_LINE in l for l in lmissing)
              and not any("CRASHED" in l for l in lmissing))
        rowner("banana")
        lunk, punk = twice()
        check("⚠ s4-14 (c) FAIL-CLOSED, UNRECOGNISED owner state: a value this tool does not know "
              "is refused too — and is REPORTED as unrecognised rather than rendered like a known "
              "one, so a reader can tell 'the owner said afk' from 'nobody can parse what he said'",
              all(REVIVAL_DOOR_LINE in l for l in lunk)
              and any("UNRECOGNISED" in l for l in lunk)
              and not any("CRASHED" in l for l in lunk))

        # (d) THE OTHER DIRECTION — the gate is not a blanket "never revive the door".
        for _st in REVIVAL_DOOR_STATES:
            rowner(_st)
            _lok, _ = twice()
            check(f"⚠ s4-14 (d) ADMITTED STATE `{_st}`: the door IS revived. Without this pair of "
                  f"rows the gate would be indistinguishable from one that never revives a door at "
                  f"all — which is a different rule than the owner gave, and would strand a "
                  f"genuinely crashed door while he is sitting at it",
                  "CRASHED — " in " ".join(_lok))

        # (e) THE DERIVATION — `relays:` is read through coord's ONE parser of that key, so a
        # future kit-side name list cannot quietly become the door's definition.
        check("⚠ s4-14 (e) DERIVED, NEVER A NAME LIST: the gate's door test reads `relays:` via "
              "`coord.inbox_decls` — the same derivation the reap exemption and `owner_world` use "
              "— and the seat-id `master` appears NOWHERE in the arm. A name list freezes one "
              "campaign's vocabulary into a shared tool and forgets the next such seat identically",
              "inbox_decls" in inspect.getsource(check_revival)
              and not any(lit in _door_gate_src() for lit in ('"master"', "'master'")))
        check("⚠ s4-14 (e) CONTROL for the row above: the same predicate DOES see a seat-name "
              "literal when one is present — proving it is matched rather than never matchable",
              any(lit in (_door_gate_src() + '"master"') for lit in ('"master"', "'master'")))

        rowner(None)
        rdecl(mode="interactive")
        (rbase / "lifecycle-inflight.json").unlink(missing_ok=True)
        rstate.clear(); rnotes.clear()

        # Row 7 — LG-16, AMENDED BY s4-06 AND THE AMENDMENT IS THE POINT. The row as s4-04 wrote it
        # asserted `_actuator_syms(inspect.getsource(check_revival)) == set()` and called that "the
        # actuator-arm count is UNCHANGED (ZERO at this landing point: s4-06 has not landed)".
        #
        # ⚠⚠ s4-06 HAS NOW LANDED AND THAT ASSERTION WOULD STILL HAVE PASSED — VACUOUSLY. The fire
        # lives in `fire_revival`, which `check_revival` reaches by NAME, and `fire_revival` is not
        # in the symbol set. A predicate scoped to one function's own bytes reports ZERO whether the
        # actuator is absent or one call away, so it can no longer discriminate. It is REPLACED
        # rather than left standing as a green: LG-16's real claim was about s4-04's GATE, and that
        # claim is preserved below at its true scope (the gate BLOCK), while the ARM's count is
        # asserted honestly at ONE — the s4-06 fire, named.
        def _actuator_syms(src):
            # DEDENTED before parsing: this predicate is applied to a nested BLOCK (s4-04's gate)
            # as well as to whole functions, and an indented fragment is not a parseable module.
            t = _ast_mod.parse(_textwrap.dedent(src))
            return (({n.id for n in _ast_mod.walk(t) if isinstance(n, _ast_mod.Name)}
                     | {n.attr for n in _ast_mod.walk(t) if isinstance(n, _ast_mod.Attribute)})
                    & {"fork", "Popen", "subprocess", "system", "execv", "execvp", "setsid",
                       "launch_seat", "cmd_launch", "renew_in_place", "seat_placement",
                       "live_panes", "tmux_new_window", "tmux_find_window_pane", "kill"})

        check("⚠ s4-04 LG-16 (a), AT ITS TRUE SCOPE: s4-04's COMPLETED-ONE-SHOT gate BLOCK itself "
              "still references no fork, exec, subprocess, launch or tmux symbol — the gate routes "
              "and refuses, it never acts. This is what LG-16 always meant, asserted over the "
              "gate's own AST rather than over the whole enclosing function",
              _actuator_syms(_gate_body) == set())
        _act_mutant = _gate_body.replace(_anchor, _anchor + "\n        coord.launch_seat(seat)", 1)
        check("⚠ s4-04 LG-16 (a) RED ARM: the SAME predicate over the SAME gate block with one "
              "launch call inserted reports it — the row can go red, and the mutation is asserted "
              "to have applied so a failed replace cannot pass as a green",
              _act_mutant != _gate_body and _actuator_syms(_act_mutant) == {"launch_seat"})
        check("⚠ s4-04 LG-16 (b) — THE VACUITY, MEASURED AND DISCLOSED RATHER THAN INHERITED: the "
              "ORIGINAL predicate (scoped to `check_revival`'s own source) STILL answers 'no "
              "actuator' now that s4-06 has landed, because the fire is one call away by name. A "
              "green that survives the arrival of the very thing it excluded proves nothing, which "
              "is why the row above was re-scoped and the row below was added",
              _actuator_syms(inspect.getsource(check_revival)) == set())
        _arm_src = "\n".join(inspect.getsource(f) for f in
                             (check_revival, fire_revival, revival_fork_target, revival_fork_argv,
                              revival_child_env, claim_revival))
        check("⚠ s4-06 LG-16 (c) — THE ARM'S ACTUATOR COUNT IS NOW **ONE**, AND s4-06 IS IT. Over "
              "the WHOLE revival arm's call graph the actuator symbols are exactly the fire's: "
              "`subprocess.Popen` (the detached exec) plus the three reads the target derivation "
              "needs. ⚠ `setsid` is NOT among them and that is a property of the INSTRUMENT, not "
              "of the code: it rides the argv as a STRING LITERAL, which an AST name/attribute "
              "scan cannot see — stated so nobody reads its absence as evidence. `launch_seat`, "
              "`cmd_launch`, `tmux_new_window` and `kill` ARE absent for real: this arm computes a "
              "target and forks coord.py's `lifecycle-exec`; it never launches a seat itself and "
              "never kills a pane",
              _actuator_syms(_arm_src) == {"subprocess", "Popen", "live_panes",
                                           "tmux_find_window_pane", "renew_in_place",
                                           "seat_placement"}
              and '"setsid"' in _arm_src)
        check("⚠ s4-06 LG-16 (c) RED ARM: the same predicate over the same arm with `launch_seat` "
              "and `tmux_new_window` inserted reports BOTH — so the row can go red, and it is the "
              "row that will catch the next arm somebody adds here",
              _actuator_syms(_arm_src + "\ncoord.launch_seat(x)\ncoord.tmux_new_window(y)\n")
              == {"subprocess", "Popen", "live_panes", "tmux_find_window_pane",
                  "renew_in_place", "seat_placement", "launch_seat", "tmux_new_window"})

        rdecl()
        rstate.clear(); rnotes.clear()

        # ---- Stage 4 §2 (s4-05): THE NO-DOUBLE-LAUNCH INTERLOCK ----
        # ⚠ THE 20x ROW NEEDS REAL CONCURRENCY, so this block FORKS. `os.fork` and not
        # `multiprocessing`: the red arms below are exec'd function objects no start method can
        # pickle, and 3.14's default start method on Linux is no longer fork. Children write a
        # result file and `os._exit` — they never re-enter this suite.
        # ⚠ NO TMUX ANYWHERE. s4-09's throwaway room is not built and this path makes no tmux call
        # to need one, so every row here runs against a throwaway PACKAGE in the temp dir.
        import ast
        cpkg = Path(td) / "claimpkg"
        cbase = cpkg / "coordination"
        cbase.mkdir(parents=True)
        cargs = argparse.Namespace(package=str(cpkg), base=None, workers_dir=None,
                                   notify_to="leader", notify_fallback="leader")
        # s4-04 made the descriptor load-bearing on the way to CRASHED: an undeclared `mode:` is
        # UNDECIDABLE and the detector refuses before it ever reaches the claim. These seats are
        # `interactive` so the rows below still exercise the INTERLOCK, which is what they assert.
        (cpkg / "workers").mkdir(parents=True, exist_ok=True)
        for _cs in ("dseat", "otherseat"):
            (cpkg / "workers" / f"{_cs}.md").write_text(
                f"---\nagent: {_cs}\nmode: interactive\n---\n\nseat body\n", encoding="utf-8")
        cmark = cbase / "lifecycle-inflight.json"
        race_n = [0]

        def croster(*rows):
            body = ["| agent | active | pane | summary | checkin | checkout | lastread |",
                    "|---|---|---|---|---|---|---|"]
            body += [f"| {a} | {act} | {pane} | s | c |  |  |" for a, act, pane in rows]
            (cbase / "workers.md").write_text("\n".join(body) + "\n", encoding="utf-8")

        def cclean():
            for f in ("lifecycle-inflight.json", "awaiting-close.json", "closing.json"):
                if (cbase / f).exists():
                    (cbase / f).unlink()

        def cmarker():
            return json.loads(cmark.read_text(encoding="utf-8")) if cmark.exists() else None

        def put_marker(d):
            cmark.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        def ago(minutes):
            return datetime.fromtimestamp(time.time() - minutes * 60).strftime("%Y-%m-%d %H:%M")

        def claim(seat="dseat", pane="%77", disp="revive", fn=None):
            """One claim, its own notes and room. Returns (outcome, why, notes)."""
            cnotes, croom = [], {}
            out, why = (fn or claim_revival)(cbase, seat, pane, cnotes, croom, disp)
            return out, why, cnotes

        def race(n_revive=10, n_renew=10, fn=None, seat="dseat"):
            """Fork n_revive+n_renew children that ALL enter the claim at once, behind a file
            barrier. Returns [[outcome, disposition, first-note-or-""], ...]."""
            race_n[0] += 1
            resdir = Path(td) / f"claimrace-{race_n[0]}"
            resdir.mkdir()
            gate = resdir / "GO"
            plan = ["revive"] * n_revive + ["renew"] * n_renew
            pids = []
            for i, disp in enumerate(plan):
                pid = os.fork()
                if pid == 0:                                   # ---- child ----
                    rc = 0
                    try:
                        while not gate.exists():
                            time.sleep(0.005)
                        kn, kr = [], {}
                        o, w = (fn or claim_revival)(cbase, seat, "%77", kn, kr, disp)
                        (resdir / f"{i}.json").write_text(
                            json.dumps([o, disp, str(kn[0]) if kn else ""]), encoding="utf-8")
                    except BaseException as exc:               # noqa: BLE001 — reported, not raised
                        rc = 1
                        try:
                            (resdir / f"{i}.json").write_text(
                                json.dumps(["EXC", disp, repr(exc)]), encoding="utf-8")
                        except OSError:
                            pass
                    finally:
                        os._exit(rc)
                pids.append(pid)
            gate.write_text("go", encoding="utf-8")
            for p in pids:
                os.waitpid(p, 0)
            return [json.loads((resdir / f"{i}.json").read_text(encoding="utf-8"))
                    if (resdir / f"{i}.json").exists() else ["MISSING", plan[i], ""]
                    for i in range(len(plan))]

        def tally(res):
            out = {}
            for r in res:
                out[r[0]] = out.get(r[0], 0) + 1
            return out

        me = {"pid": os.getpid(), "starttime": coord.proc_stat(os.getpid())[1]}
        dead = {"pid": 999999, "starttime": "1"}                # starttime never matches: DEAD
        csrc = inspect.getsource(claim_revival)
        wsrc = inspect.getsource(_write_claim)

        # ---- ROW 1: THE MUTEX. 20 concurrent claims, one seat, exactly one winner. ----
        croster(("dseat", "yes", "%77"))
        cclean()
        res1 = race()
        won1 = [r for r in res1 if r[0] in ("CLAIMED", "RE-CLAIMED")]
        print(f"      s4-05 row 1 raw tally (20 concurrent, 10 revive / 10 renew): {tally(res1)}")
        check("⚠ s4-05 (1) THE MUTEX, verbatim from stage-4-revival-spec.md:310-313: a driver "
              "invoking the claim path 20x CONCURRENTLY against ONE seat (10 revive, 10 renew, "
              "released together behind a file barrier) yields EXACTLY 1 success and 19 "
              "stand-downs. With a SHARED marker file `atomic_write` is last-writer-wins, so this "
              "is the flock's result and nothing else's",
              len(res1) == 20 and len(won1) == 1
              and sum(1 for r in res1 if r[0] == "STOOD-DOWN") == 19
              and sorted(r[1] for r in res1) == sorted(["renew"] * 10 + ["revive"] * 10))
        m1 = cmarker()
        check("s4-05 (1): the ONE winner left ONE entry — in-flight, the disposition it was given "
              "(stored as given, s3-03), attempts 0, and NO `executor` key: no executor process "
              "exists at claim time and a placeholder would be a claim about a process that is not "
              "there",
              set(m1) == {"dseat"} and m1["dseat"]["state"] == "in-flight"
              and m1["dseat"]["disposition"] in ("revive", "renew")
              and m1["dseat"]["attempts"] == 0 and "executor" not in m1["dseat"]
              and isinstance(m1["dseat"]["caller"].get("pid"), int)
              and isinstance(m1["dseat"]["caller"].get("starttime"), str)
              and m1["dseat"]["caller"]["starttime"] != ""
              and m1["dseat"]["steps-completed"] == [])

        # ---- ROW 2: lockless REFUSES rather than races. ----
        cclean()
        saved_flock = coord._acquire_flock

        def broken_flock(fh):
            raise OSError("forced by the s4-05 acceptance — the coord.py T5 fallback")

        coord._acquire_flock = broken_flock
        try:
            res2 = race()
        finally:
            coord._acquire_flock = saved_flock
        print(f"      s4-05 row 2 raw tally (20 concurrent, lock forced unavailable): "
              f"{tally(res2)}")
        check("⚠ s4-05 (2) LOCKLESS REFUSES RATHER THAN RACES: with `coord._acquire_flock` forced "
              "to raise — coord.py's own T5 read-only-sandbox fallback — all 20 concurrent claims "
              "REFUSE and ZERO entries are written. `coord_lock` yields False and proceeds "
              "lockless for every other caller by design; here the lock is the only mutex, so a "
              "lockless claim IS the double-launch risk",
              len(res2) == 20 and all(r[0] == "REFUSED" for r in res2) and not cmark.exists())
        check("⚠ s4-05 (2) R-8 — THE LAYER STRING LEADS THE BODY (s4-12 row 5's shape): every "
              "refusal note starts with the layer, so a reader cannot mistake this TOOL GATE's "
              "refusal for the harness permission classifier's",
              all(r[2].startswith(REVIVAL_CLAIM_LAYER + ": coordination lock unavailable")
                  for r in res2))
        mut2_src = csrc.replace("            if not held:", "            if False:  # RED ARM", 1)
        g2 = dict(globals())
        exec(compile(mut2_src, "<s4-05 row 2 red arm>", "exec"), g2)          # noqa: S102
        coord._acquire_flock = broken_flock
        try:
            res2r = race(fn=g2["claim_revival"])
        finally:
            coord._acquire_flock = saved_flock
        won2r = sum(1 for r in res2r if r[0] in ("CLAIMED", "RE-CLAIMED"))
        print(f"      s4-05 row 2 RED ARM raw tally (`held` check removed, lock unavailable): "
              f"{tally(res2r)}")
        check("⚠ s4-05 (2) RED ARM: the SAME 20x driver against a mutant with the `held` check "
              "removed produces claims — so control 2 can go red. An implementation that ignores "
              "`held` passes control 1 (the flock still serialises when it works) and fails ONLY "
              "here, which is why this arm exists",
              csrc.count("            if not held:") == 1 and mut2_src != csrc and won2r > 0)
        cclean()

        # ---- ROW 3: void-claim re-claim, and ONLY when void. ----
        croster(("dseat", "yes", "%77"))
        put_marker({"dseat": {"state": "in-flight", "disposition": "renew",
                              "executor": dead, "stamped-at": ago(60)}})
        o3, w3, n3 = claim()
        m3 = cmarker()
        check("⚠ s4-05 (3) THE POSITIVE ARM: an in-flight marker whose executor pair is GONE and "
              "whose age exceeds LIFECYCLE_STALE_MIN is a VOID claim — the executor died "
              "mid-flight — so it is re-claimed with attempts == 1 and disposition 'revive'",
              o3 == "RE-CLAIMED" and m3["dseat"]["attempts"] == 1
              and m3["dseat"]["disposition"] == "revive" and m3["dseat"]["state"] == "in-flight"
              and len(n3) == 1)
        check("⚠ s4-05 (3) R-8: the loud note's layer string LEADS the body",
              n3[0].startswith(REVIVAL_CLAIM_LAYER + ": a VOID lifecycle claim"))
        put_marker({"dseat": {"state": "in-flight", "disposition": "renew",
                              "executor": me, "stamped-at": ago(1)}})
        o3a, w3a, n3a = claim()
        check("⚠ s4-05 (3) CONTROL (a) — MUST NOT RE-CLAIM: executor pid ALIVE and the entry "
              "young reads MID-RENEWAL. Stand down, no claim, and NO note beyond the report line: "
              "this is the healthy case and a note every tick trains the room to ignore them",
              o3a == "STOOD-DOWN" and "MID-RENEWAL" in w3a and n3a == []
              and cmarker()["dseat"]["disposition"] == "renew")
        put_marker({"dseat": {"state": "in-flight", "disposition": "renew",
                              "executor": me, "stamped-at": ago(60)}})
        o3b, w3b, n3b = claim()
        check("⚠ s4-05 (3) CONTROL (b) — MUST NOT RE-CLAIM: executor pid ALIVE but the entry past "
              "LIFECYCLE_STALE_MIN raises a SEPARATE loud note and NEVER authorises a re-fire. A "
              "slow executor is still an executor and identity says it is there",
              o3b == "STOOD-DOWN" and "STALE-BUT-ALIVE" in w3b and len(n3b) == 1
              and cmarker()["dseat"]["disposition"] == "renew"
              and "attempts" not in cmarker()["dseat"])
        check("⚠ s4-05 (3) CONTROL (b) R-8: that separate note's layer string LEADS its body too, "
              "and its body NAMES the live executor rather than a timeout",
              n3b[0].startswith(REVIVAL_CLAIM_LAYER + ": an in-flight lifecycle claim")
              and "ITS EXECUTOR IS ALIVE" in n3b[0])
        put_marker({"dseat": {"state": "in-flight", "disposition": "renew",
                              "executor": dead, "stamped-at": ago(1)}})
        o3c, w3c, n3c = claim()
        check("⚠ s4-05 (3) CONTROL (c) — MUST NOT RE-CLAIM: executor GONE but the entry younger "
              "than LIFECYCLE_STALE_MIN stands down. With (a) and (b) this separates identity "
              "resolution from a TTL guess: a single positive arm cannot",
              o3c == "STOOD-DOWN" and n3c == []
              and cmarker()["dseat"]["disposition"] == "renew")
        check("s4-05 (3): the RE-CLAIM is governed by `coord.lifecycle_stale` — Stage 3's own "
              "FAILED-RENEWAL conjunction — and the four in-flight branches agree with it on "
              "every one of these fixtures. The store's predicate decides; this file does not "
              "re-derive one",
              coord.lifecycle_stale({"state": "in-flight", "executor": dead,
                                     "stamped-at": ago(60)}) is True
              and coord.lifecycle_stale({"state": "in-flight", "executor": me,
                                         "stamped-at": ago(60)}) is False
              and coord.lifecycle_stale({"state": "in-flight", "executor": dead,
                                         "stamped-at": ago(1)}) is False
              and coord.lifecycle_stale({"state": "in-flight", "stamped-at": ago(60)}) is False)
        put_marker({"dseat": {"state": "in-flight", "disposition": "revive",
                              "stamped-at": ago(60)}})
        o3u, w3u, n3u = claim()
        check("⚠ s4-05 (3) THE FOURTH BRANCH — STAGE 3'S FAIL-SAFE COST, MADE LOUD: an in-flight "
              "entry with NO readable executor ident is `lifecycle_stale() == False` FOREVER, so "
              "nothing here or at close-run will ever clear or supersede it. This is the shape "
              "OUR OWN claim has until s4-06 forks an executor, so the note is also the alarm for "
              "'a claim landed and nothing ever fired it'. It stands down — it never re-claims",
              o3u == "STOOD-DOWN" and len(n3u) == 1
              and n3u[0].startswith(REVIVAL_CLAIM_LAYER + ": an in-flight lifecycle claim")
              and "MISSING" in n3u[0]
              and coord.lifecycle_stale(cmarker()["dseat"]) is False
              and cmarker()["dseat"]["disposition"] == "revive")

        # ---- ROW 4: both race covers, disabled ONE AT A TIME. ----
        cclean()
        croster(("dseat", "no", "%77"))
        o4a, w4a, n4a = claim()
        check("⚠ s4-05 (4a) COVER 1 ALONE — the marker cover DISABLED (no marker file at all): "
              "the IN-SECTION roster re-read reads CLEANLY-OUT and refuses. `cmd_close_seat` "
              "flips the row to active:no BEFORE killing the pane, which is what makes this cover "
              "work at all",
              o4a == "STOOD-DOWN" and "CLEANLY-OUT" in w4a and not cmark.exists())
        croster(("dseat", "yes", "%77"))
        put_marker({"dseat": {"state": "in-flight", "disposition": "renew",
                              "executor": me, "stamped-at": ago(1)}})
        o4b, w4b, n4b = claim()
        check("⚠ s4-05 (4b) COVER 2 ALONE — the roster cover DISABLED (row left ACTIVE): a fresh "
              "in-flight marker reads MID-RENEWAL and refuses. Stage 3's caller stamps the marker "
              "BEFORE forking, so a marker with no executor pid is impossible on that path",
              o4b == "STOOD-DOWN" and "MID-RENEWAL" in w4b
              and cmarker()["dseat"]["disposition"] == "renew")
        cclean()
        o4c, w4c, n4c = claim()
        check("⚠ s4-05 (4) THE DISCRIMINATING CONTROL: with BOTH covers off — roster active AND "
              "no marker — the IDENTICAL call CLAIMS. Two covers tested together prove neither, "
              "and a refusal test whose call could never have claimed proves nothing",
              o4c == "CLAIMED" and cmarker()["dseat"]["disposition"] == "revive")

        # ---- ROW 5: the claim is a REAL read-modify-write. ----
        cclean()
        croster(("dseat", "yes", "%77"), ("otherseat", "yes", "%78"))
        coord.stamp_lifecycle(cbase, "otherseat", {"disposition": "renew", "pane": "%78",
                                                   "executor": me, "caller": me})
        before5 = cmark.read_text(encoding="utf-8")
        frag5 = before5.split('"otherseat":', 1)[1].rsplit("}", 2)[0]
        o5, w5, n5 = claim()
        after5 = cmark.read_text(encoding="utf-8")
        check("⚠ s4-05 (5): the claim is a REAL read-modify-write — a DIFFERENT seat's entry, "
              "written by Stage 3's own `stamp_lifecycle`, survives BYTE-IDENTICAL beside ours",
              o5 == "CLAIMED" and len(frag5) > 80 and frag5 in after5
              and set(json.loads(after5)) == {"dseat", "otherseat"})
        mut5_wsrc = wsrc.replace("json.dumps(marker, indent=2, sort_keys=True)",
                                 "json.dumps({seat: marker[seat]}, indent=2, sort_keys=True)", 1)
        g5 = dict(globals())
        exec(compile(mut5_wsrc, "<s4-05 row 5 red arm>", "exec"), g5)         # noqa: S102
        exec(compile(csrc, "<s4-05 row 5 red arm caller>", "exec"), g5)       # noqa: S102
        cclean()
        coord.stamp_lifecycle(cbase, "otherseat", {"disposition": "renew", "pane": "%78",
                                                   "executor": me, "caller": me})
        o5r, w5r, n5r = claim(fn=g5["claim_revival"])
        check("⚠ s4-05 (5) RED ARM: replacing the read-modify-write with a WHOLE-FILE write of "
              "our entry alone drops the other seat's entry entirely — so control 5 can go red. "
              "`atomic_write` is `os.replace`; the file is shared, and the whole file is the unit",
              wsrc.count("json.dumps(marker, indent=2, sort_keys=True)") == 1
              and mut5_wsrc != wsrc and o5r == "CLAIMED" and set(cmarker()) == {"dseat"})

        # ---- the two consumption couplings, asserted rather than trusted ----
        cclean()
        sample5 = {"z": {"state": "done"}, "a": {"state": "in-flight", "n": 1}}
        coord._write_lifecycle(cbase, sample5)
        store_bytes = cmark.read_text(encoding="utf-8")
        cmark.unlink()
        _write_claim(coord.lifecycle_path(cbase), sample5, {}, [], "z")
        check("s4-05 COUPLING: the claim writes the marker in `coord._write_lifecycle`'s EXACT "
              "byte format. It cannot CALL that writer — `stamp_lifecycle` and friends take "
              "`coord_lock` themselves and flock is not re-entrant on a second handle, so nesting "
              "deadlocks the loop (measured). This asserts the format rather than trusting it, so "
              "a Stage 3 format change goes red here instead of silently reshaping the file",
              cmark.read_text(encoding="utf-8") == store_bytes)
        put_marker({"dseat": {"state": "done"}})
        strict_ok, st_ok = _strict_ledger(coord.lifecycle_path(cbase))
        loader_ok = coord.load_lifecycle(cbase)
        cmark.write_text("{ not json at all", encoding="utf-8")
        strict_bad, st_bad = _strict_ledger(coord.lifecycle_path(cbase))
        check("s4-05 COUPLING: the critical section reads the marker with `_strict_ledger`, NOT "
              "`coord.load_lifecycle`. The two AGREE on parseable input and DISAGREE on an "
              "unreadable file — the loader collapses it to {} ('no entry'), which inside the "
              "lock would mean writing a claim over a marker that may hold a live renewal. The "
              "substitution is asserted here so it can never become silent",
              st_ok == "ok" and strict_ok == loader_ok
              and st_bad == "unparseable" and coord.load_lifecycle(cbase) == {})
        croster(("dseat", "yes", "%77"))
        o6, w6, n6 = claim()
        check("⚠ s4-05: an UNPARSEABLE marker INSIDE the critical section REFUSES and writes "
              "nothing — the file is left exactly as found. The detector refuses on this before "
              "it ever reaches CRASHED, so reaching here means the ledger changed under the lock, "
              "which is the moment to be loudest",
              o6 == "REFUSED" and len(n6) == 1
              and n6[0].startswith(REVIVAL_CLAIM_LAYER + ": ledger unreadable")
              and cmark.read_text(encoding="utf-8") == "{ not json at all")

        # ---- OUT OF SCOPE, STRUCTURALLY: it claims, it does not fire ----
        def _sym(fn):
            t = ast.parse(inspect.getsource(fn))
            return ({n.id for n in ast.walk(t) if isinstance(n, ast.Name)}
                    | {n.attr for n in ast.walk(t) if isinstance(n, ast.Attribute)})

        csyms = _sym(claim_revival) | _sym(_write_claim) | _sym(_claim_record)
        check("⚠ s4-05 OUT OF SCOPE, ASSERTED STRUCTURALLY: the claim path references no fork, "
              "no exec, no subprocess and no tmux/pane symbol. s4-06 owns actuation; the critical "
              "section ends with a written claim and a released lock, and a grep-by-eye is not a "
              "control",
              not (csyms & {"fork", "Popen", "subprocess", "system", "execv", "execvp",
                            "setsid", "live_panes", "window_panes", "tmux_pane_window_name",
                            "cmd_launch", "renew_in_place", "seat_placement"}))

        # ---- WIRED: the detector's CRASHED branch really calls the claim ----
        cclean()
        croster(("dseat", "yes", "%77"))
        cstate, cnotes = {}, []
        check_revival(cargs, cbase, rsnap(absent=[gone()]), None, cstate, cnotes)
        lw = check_revival(cargs, cbase, rsnap(absent=[gone()]), None, cstate, cnotes)
        check("⚠ s4-05 WIRED: the DETECTOR's CRASHED branch calls the claim — proven end to end, "
              "not by reading the call site. ⚠ THE LINE PREFIX WAS `CRASHED — would revive` UNTIL "
              "s4-06 LANDED AND IT WAS A LIE THE MOMENT THE FIRE EXISTED — every control that "
              "grepped it now greps `CRASHED — `, which the `CRASHED pending` line does not carry. "
              "The claim's verdict is on the same line as the classification",
              "CRASHED — " in " ".join(lw) and "claim CLAIMED" in " ".join(lw)
              and cmarker()["dseat"]["disposition"] == "revive"
              and cmarker()["dseat"]["pane"] == "%77")
        lw2 = check_revival(cargs, cbase, rsnap(absent=[gone()]), None, cstate, cnotes)
        check("⚠ s4-05 WIRED — THE LOOP CANNOT CLAIM THE SAME SEAT TWICE: the very next CRASHED "
              "tick stands down against the claim it wrote itself. Without this the interlock "
              "would exclude every OTHER claimer and not the one most likely to fire twice",
              "claim STOOD-DOWN" in " ".join(lw2) and set(cmarker()) == {"dseat"})
        check("s4-05: the claim gate's per-seat notes re-arm when the seat is seen LIVE again — "
              "the same signal that clears the debounce. A second, genuinely different outage "
              "must not be silent",
              (cstate["_revival_room"].setdefault("claim_notes", {"dseat\tx": True})
               or True)
              and (check_revival(cargs, cbase,
                                 rsnap(seats=[{"seat": "dseat", "pane": "%77",
                                               "liveness": "live", "harness_pid": 4242}]),
                                 None, cstate, cnotes) or True)
              and cstate["_revival_room"]["claim_notes"] == {})
        cclean()

        # ---- Stage 4 §3 (s4-06): THE FIRE ----
        # ⚠⚠ WHAT THESE ROWS ARE AND ARE NOT. They are FIXTURE-ONLY. `subprocess.Popen` is
        # SUBSTITUTED (except where a row says otherwise, and that row says so in its own text), the
        # three tmux reads are substituted for the whole region above, and NO `lifecycle-exec` ever
        # runs. The live proof — a real room, a real kill -9, a real successor pane — is s4-10's and
        # s4-12's, and a hand-authored snapshot is explicitly not acceptable as THAT evidence.
        #
        # ⚠⚠ AND THE POSITIVE CANNOT BE DEMONSTRATED ON RUN-2'S OWN DESCRIPTORS AT ALL: ZERO of
        # run-2's 52 `seat.md` files declare `mode:` (console-confirmed on disk), so s4-04's gate
        # routes every roster-absent seat there into the UNDECIDABLE refusal and the CRASHED branch
        # — and therefore this fire — is UNREACHABLE on any pre-dag-04 run. That is the ruled
        # fail-closed behaviour, not a defect. Every fixture below declares `mode: interactive`
        # EXPLICITLY for exactly that reason.
        _popen_real = subprocess.Popen
        _spawned = []

        class _RecPopen:
            """Records the fork instead of performing it. Carries `pid` because the production path
            does not read it — see the way-station block's measured note on why it must not."""

            def __init__(self, argv, stdout=None, stderr=None, start_new_session=None, env=None):
                _spawned.append({"argv": list(argv), "env": dict(env or {}),
                                 "log": getattr(stdout, "name", ""),
                                 "new_session": start_new_session})
                self.pid = -1

        try:
            subprocess.Popen = _RecPopen

            def fire(seat="dseat", pane="%77", seats=()):
                """One fire against a CLAIMED seat. Returns (outcome, why, notes, spawn-or-None).

                `seats` populates the SNAPSHOT's seat rows — the only thing that can supply the
                step-3 fallback anchor, because a pane belongs to this room exactly when the
                snapshot lists it."""
                fnotes, froom = [], {}
                del _spawned[:]
                out, why = fire_revival(cargs, cbase,
                                        rsnap(absent=[gone(seat=seat, pane=pane)], seats=seats),
                                        seat, pane, fnotes, froom)
                return out, why, fnotes, (_spawned[0] if _spawned else None)

            def claimed(seat="dseat", pane="%77"):
                cclean()
                croster((seat, "yes", pane))
                return claim(seat=seat, pane=pane)[0]

            # ---- ROW 1: THE TARGET IS NEVER EMPTY, AND THE REFUSAL IS LOUD ----
            _fx.update(panes=set(), wname="", anchor="")
            (cpkg / "workers" / "dseat.md").write_text(
                "---\nagent: dseat\nmode: interactive\nwindow: control\n---\n\nseat body\n",
                encoding="utf-8")
            o1 = claimed()
            f1, w1, n1, sp1 = fire()
            check("⚠ s4-06 (1) THE TARGET IS NEVER EMPTY: pane DEAD, `tmux_find_window_pane` MISSES "
                  "and NO live pane sits in the snapshot's session -> NO FORK, a refusal, and ONE "
                  "note naming the layer. `recover-room.py:12-19` measured what the alternative "
                  "is: tmux resolves an empty target to the MOST RECENT session, which was the "
                  "LIVE room",
                  o1 == "CLAIMED" and f1 == "NO-TARGET" and sp1 is None and len(_spawned) == 0
                  and len(n1) == 1 and n1[0].startswith(REVIVAL_FIRE_LAYER + ":")
                  and "NO ANCHOR RESOLVES" in w1)
            check("⚠ s4-06 (1) R-8 — THE LAYER STRING LEADS THE BODY, so a reader cannot mistake "
                  "this TOOL GATE's refusal for the harness permission classifier's",
                  n1[0].startswith("revival fire gate: "))
            check("⚠ s4-06 (1) R-8 RED ARM: the SAME predicate against the SAME body with the layer "
                  "string moved to the END goes red — a buried layer string fails R-8's bar and a "
                  "startswith assertion is only worth something if it can",
                  not (str(n1[0])[len(REVIVAL_FIRE_LAYER) + 2:] + " " + REVIVAL_FIRE_LAYER
                       ).startswith(REVIVAL_FIRE_LAYER + ":"))
            # THE RED ARM FOR THE GUARD ITSELF: let an empty target through and the fork happens.
            _empty_ok = inspect.getsource(fire_revival).replace(
                "    if not target:\n", "    if False:\n", 1)
            check("s4-06 (1) PRECONDITION: the empty-target mutant really applied — a replace that "
                  "silently missed would make the red arm below a green that proves nothing",
                  _empty_ok != inspect.getsource(fire_revival))
            _g1 = dict(globals())
            exec(compile(_empty_ok, "<s4-06 row 1 red arm>", "exec"), _g1)     # noqa: S102
            del _spawned[:]
            _g1["fire_revival"](cargs, cbase, rsnap(absent=[gone()]), "dseat", "%77", [], {})
            check("⚠ s4-06 (1) THE RED ARM: with the no-target guard removed the SAME fixture DOES "
                  "fork — and it forks with `--tmux-target ''`. This is what proves the guard is "
                  "the thing that stopped it, rather than something else in the path happening to "
                  "fail first",
                  len(_spawned) == 1
                  and _spawned[0]["argv"][_spawned[0]["argv"].index("--tmux-target") + 1] == "")

            # ---- ROW 2: IN-PLACE vs RE-PLACE, THREE ARMS ----
            # ⚠ THREE ARMS AND NOT TWO, because a two-arm test cannot separate "pane liveness" from
            # "placement": arm (c) holds the pane LIVE and flips only the placement answer.
            _fx.update(panes={"%77", "%9"}, wname="control", anchor="")
            claimed()
            f2a, w2a, _, sp2a = fire()
            check("⚠ s4-06 (2a) IN-PLACE: pane LIVE and already in the window its descriptor names "
                  "-> the argv carries THAT PANE and the successor respawns in place, layout "
                  "intact (G-12)",
                  f2a == "FIRED" and sp2a is not None
                  and sp2a["argv"][sp2a["argv"].index("--tmux-target") + 1] == "%77"
                  and "respawns IN PLACE" in w2a)
            _fx.update(panes={"%9"}, wname="control", anchor="%12")
            claimed()
            f2b, w2b, _, sp2b = fire()
            check("⚠ s4-06 (2b) RE-PLACE: pane DEAD -> the argv carries the ANCHOR, NOT the dead "
                  "pane. Passing the dead pane down would be an empty target by another route",
                  f2b == "FIRED" and sp2b is not None
                  and sp2b["argv"][sp2b["argv"].index("--tmux-target") + 1] == "%12"
                  and "%77" not in sp2b["argv"][sp2b["argv"].index("--tmux-target") + 1])
            _fx.update(panes={"%77", "%9"}, wname="somewhere-else", anchor="%12")
            claimed()
            f2c, w2c, _, sp2c = fire()
            check("⚠ s4-06 (2c) THE DISCRIMINATING ARM: pane LIVE but `renew_in_place` FALSE (its "
                  "window drifted from the descriptor's) -> branch (b) is taken anyway. With only "
                  "(a) and (b) the suite could not tell whether the decision keys on LIVENESS or "
                  "on PLACEMENT; this row separates them",
                  f2c == "FIRED" and sp2c is not None
                  and sp2c["argv"][sp2c["argv"].index("--tmux-target") + 1] == "%12"
                  and "is NOT in the window" in w2c)
            _fx.update(panes={"%9"}, wname="control", anchor="")
            claimed()
            f2d, w2d, _, sp2d = fire(seats=[{"seat": "leader", "pane": "%9"}])
            check("s4-06 (2d) THE SNAPSHOT FALLBACK: the declared window does not exist in the "
                  "session, so the anchor is a LIVE pane the snapshot places in this room — from "
                  "which `launch_seat` derives the session for a new window",
                  f2d == "FIRED" and sp2d is not None
                  and sp2d["argv"][sp2d["argv"].index("--tmux-target") + 1] == "%9")

            # ---- ROW 3: `--force` IS NEVER SET ----
            _fx.update(panes={"%77"}, wname="control", anchor="")
            claimed()
            f3, _, _, sp3 = fire()
            check("⚠ s4-06 (3): NO `--force` AND NO `--force-memory` ANYWHERE in the constructed "
                  "argv, asserted over the real argv rather than by eye. `--force` carries the ROLE "
                  "gate ALONE (coord.GATE_FLAGS) and would not lift a memory or a window-drift "
                  "refusal even if it were passed",
                  f3 == "FIRED" and not ({"--force", "--force-memory"} & set(sp3["argv"]))
                  and "--handoff-written" in sp3["argv"] and "--disposition" in sp3["argv"])
            # ⚠ SUBSTITUTED ARM, AND THE SUBSTITUTION IS DISCLOSED. The task's own red arm — "set
            # args.force = True and assert `launch_seat`'s window-drift refusal stops firing" —
            # CANNOT BE RUN FROM THIS FILE: that refusal lives in `coord.launch_seat`, inside the
            # DETACHED CHILD, and `coord.py` is not this task's write set. What IS measurable here,
            # and is strictly stronger for the argv claim, is that the flag cannot be smuggled at
            # all: the built `lifecycle-exec` parser REJECTS it.
            _lex = coord.build_parser()
            _base_argv = ["lifecycle-exec", "--package", str(cpkg), "--seat", "dseat",
                          "--disposition", "revive", "--tmux-target", "%1",
                          "--caller-pid", "1", "--caller-starttime", "1"]

            def _parses(extra):
                _oe, sys.stderr = sys.stderr, io.StringIO()
                try:
                    _lex.parse_args(_base_argv + extra)
                    return True
                except SystemExit:
                    return False
                finally:
                    sys.stderr = _oe

            check("⚠ s4-06 (3) SUBSTITUTED RED ARM, AND THE SUBSTITUTION IS DISCLOSED RATHER THAN "
                  "GLOSSED: the task's own red arm — set `args.force` and watch `launch_seat`'s "
                  "window-drift refusal stop firing — lives in `coord.launch_seat`, inside the "
                  "DETACHED CHILD, and coord.py is not this task's write set. Substituted with a "
                  "claim that is stronger for THIS argv and measurable here: `--force` and "
                  "`--force-memory` cannot be smuggled onto the fire by any future editor, because "
                  "the built `lifecycle-exec` parser REJECTS them",
                  _parses(["--force"]) is False and _parses(["--force-memory"]) is False)
            check("s4-06 (3) THE INSTRUMENT'S OWN CONTROL: the same probe against a flag the "
                  "parser DOES define returns True — so a `False` above is a rejection and not a "
                  "parser that refuses everything handed to it",
                  _parses(["--handoff-written", "0"]) is True)

            # ---- ROW 4: THE CHILD'S ENVIRONMENT IS SCRUBBED ----
            os.environ["TMUX"] = "/tmp/fake,1,0"
            os.environ["TMUX_PANE"] = "%145"
            os.environ["COORD_AGENT"] = "chief-of-staff"
            os.environ["COORD_LAUNCH_TARGET"] = "%1"
            os.environ["TMUX_TMPDIR"] = "/tmp/s4-06-private-socket"
            os.environ["S4_06_CANARY"] = "kept"
            try:
                _fx.update(panes={"%77"}, wname="control", anchor="")
                claimed()
                f4, _, _, sp4 = fire()
                check("⚠ s4-06 (4) THE SCRUB: the child's env carries NONE of TMUX, TMUX_PANE, "
                      "COORD_AGENT, COORD_LAUNCH_TARGET, while the parent holds all four. "
                      "`watch.py` records why in its own measured words: a detached loop inherits "
                      "TMUX_PANE from whatever shell started it, and every send was refused with "
                      "\"you claimed 'watcher', but this pane (%145) is registered to "
                      "'chief-of-staff'\"",
                      f4 == "FIRED"
                      and not ({"TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET"}
                               & set(sp4["env"]))
                      and all(v in os.environ for v in coord.LIFECYCLE_SCRUB_ENV))
                check("⚠ s4-06 (4) IT IS A DENYLIST AND MUST STAY ONE: TMUX_TMPDIR SURVIVES into "
                      "the child. An acceptance room on a private tmux socket is reachable only "
                      "through it, so narrowing this to an allowlist would silently send every "
                      "fire to the default server. An unrelated variable survives too",
                      sp4["env"].get("TMUX_TMPDIR") == "/tmp/s4-06-private-socket"
                      and sp4["env"].get("S4_06_CANARY") == "kept")
                # THE RED ARM, AND IT IS A REAL /proc MEASUREMENT — "a scrub asserted only in the
                # prompt is not a scrub". A REAL child is started with the REAL `revival_child_env()`
                # and its /proc/<pid>/environ is read back; then the same child is started with the
                # scrub REMOVED and the assertion goes red. No tmux, no lifecycle-exec: the payload
                # is a sleeping python, because what is under test is the ENV COMPUTATION.
                def _environ_of(env):
                    pr = _popen_real([sys.executable, "-c", "import time; time.sleep(5)"],
                                     env=env, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL, start_new_session=True)
                    try:
                        for _ in range(200):
                            try:
                                raw = Path(f"/proc/{pr.pid}/environ").read_bytes()
                            except OSError:
                                raw = b""
                            if raw:
                                break
                            time.sleep(0.01)
                        return {kv.split("=", 1)[0] for kv in
                                raw.decode("utf-8", "replace").split("\0") if "=" in kv}
                    finally:
                        pr.kill()
                        pr.wait()

                _clean = _environ_of(revival_child_env())
                _dirty = _environ_of(dict(os.environ))
                check("⚠ s4-06 (4) MEASURED AT /proc, NOT ASSERTED: a REAL child started with the "
                      "production `revival_child_env()` shows none of the four names in "
                      "/proc/<pid>/environ, and its TMUX_TMPDIR is present",
                      not ({"TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET"} & _clean)
                      and "TMUX_TMPDIR" in _clean)
                check("⚠ s4-06 (4) THE RED ARM AT THE SAME INSTRUMENT: the identical measurement "
                      "with the scrub REMOVED (the parent's env passed straight through) shows all "
                      "four — so the /proc read can go red, and the green above is the scrub's "
                      "doing and not the instrument's",
                      {"TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET"} <= _dirty)
            finally:
                for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET",
                           "TMUX_TMPDIR", "S4_06_CANARY"):
                    os.environ.pop(_v, None)

            # ---- ROW 5: `--handoff-written 0`, AND memory.md IS NOT TOUCHED ----
            _mem = cpkg / "workers" / "dseat" / "memory.md"
            _mem.parent.mkdir(parents=True, exist_ok=True)
            _mem.write_text("# memory\n\n<!-- handoff:start -->\nprior turn\n"
                            "<!-- handoff:end -->\n", encoding="utf-8")
            _before = _mem.read_bytes()
            _fx.update(panes={"%77"}, wname="control", anchor="")
            claimed()
            f5, _, _, sp5 = fire()
            _hw = sp5["argv"][sp5["argv"].index("--handoff-written") + 1]
            check("⚠ s4-06 (5): the argv carries `--handoff-written 0` and `--disposition revive`, "
                  "and `memory.md` is BYTE-IDENTICAL across the fire. A crashed session had no turn "
                  "boundary at which to write a block, so requiring one would make revival "
                  "impossible in exactly the case revival exists for (R-14: this arm neither "
                  "writes, extends, nor reads that block)",
                  f5 == "FIRED" and _hw == "0"
                  and sp5["argv"][sp5["argv"].index("--disposition") + 1] == "revive"
                  and _mem.read_bytes() == _before)
            check("⚠ s4-06 (5) THE DISTINGUISHING CONTROL: the OTHER caller of this executor — "
                  "`coord.fork_lifecycle_renewal`, Stage 2's normal `checkout --renew` path — "
                  "hard-codes `--disposition renew` and `--handoff-written 1`. The two paths are "
                  "therefore distinguishable at the argv, which is the whole reason this arm does "
                  "not reuse that function",
                  '"--handoff-written", "1"' in inspect.getsource(coord.fork_lifecycle_renewal)
                  and '"--disposition", "renew"' in
                  inspect.getsource(coord.fork_lifecycle_renewal))

            # ---- ROW 6: THE EXECUTOR IDENT — THE TASK TEXT IS WRONG AND THIS ROW MEASURES WHY ----
            # `s4-06` § Detachment asks this arm to "record the executor's (pid, starttime) into the
            # marker entry after the fork". IT CANNOT, and writing one anyway would write a DEAD pid
            # into a field every reader treats as "a process is there".
            _sid = _popen_real(
                ["setsid", sys.executable, "-c",
                 f"import os,time; open({str(Path(td) / 'kidpid')!r},'w').write(str(os.getpid())); "
                 f"time.sleep(4)"],
                start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            _kid = ""
            for _ in range(400):
                try:
                    _kid = (Path(td) / "kidpid").read_text().strip()
                except OSError:
                    _kid = ""
                if _kid:
                    break
                time.sleep(0.01)
            check("⚠ s4-06 (6) THE MEASUREMENT THAT OVERTURNS THE TASK TEXT: with `setsid` in the "
                  "argv AND `start_new_session=True`, Popen's pid is NOT the executor's. Python "
                  "already made the child a session leader, so util-linux `setsid`'s own setsid() "
                  "fails and it FORKS — the real executor is a different process. A caller-side "
                  "`executor` write would therefore record a pid that is already gone",
                  _kid != "" and _kid != str(_sid.pid))
            _sid.kill()
            _sid.wait()
            check("⚠ s4-06 (6) SO THE IDENT COMES FROM THE CHILD, WHICH IS WHERE IT ALREADY CAME "
                  "FROM: `cmd_lifecycle_exec` guard 5 stamps `executor: (os.getpid(), "
                  "proc_stat(os.getpid())[1])` as its first act. ONE writer, ONE home (PRIN-11) — "
                  "and it is exactly why `_claim_record` above leaves `executor` deliberately "
                  "absent. Asserted against coord's own source so a Stage 3 change goes red here",
                  '"executor": (os.getpid(), proc_stat(os.getpid())[1])'
                  in inspect.getsource(coord.cmd_lifecycle_exec))
            check("⚠ s4-06 (6) WHAT THIS ARM DOES RECORD INSTEAD — its own evidence, on the entry, "
                  "BEFORE the fork: the target it computed and the log it opened. So a fire that "
                  "never reaches the child still says where it was aimed. `executor` stays ABSENT "
                  "until a real child stamps it",
                  cmarker()["dseat"].get("tmux-target") == "%77"
                  and cmarker()["dseat"].get("log", "").endswith(".log")
                  and "executor" not in cmarker()["dseat"]
                  and Path(cmarker()["dseat"]["log"]).exists())
            _annotate_claim(cbase, "no-such-seat", {"log": "x"})
            check("⚠ s4-06 (6) CONTROL: the annotation MERGES and never CREATES — an entry this "
                  "file never saw claimed is left absent rather than invented, because an "
                  "annotation about a claim nobody made would BE a claim",
                  "no-such-seat" not in cmarker())

            # ---- ROW 7: THE FIRE IS REACHED ONLY THROUGH THE CLAIM ----
            cclean()
            croster(("dseat", "yes", "%77"))
            _fx.update(panes={"%77"}, wname="control", anchor="")
            del _spawned[:]
            wstate, wnotes = {}, []
            check_revival(cargs, cbase, rsnap(absent=[gone()]), None, wstate, wnotes)
            _lf = check_revival(cargs, cbase, rsnap(absent=[gone()]), None, wstate, wnotes)
            check("⚠ s4-06 WIRED: the DETECTOR's CRASHED branch now FIRES, end to end, and the "
                  "line says so — `claim CLAIMED` and `fire FIRED` on one line, one spawn recorded",
                  "claim CLAIMED" in " ".join(_lf) and "fire FIRED" in " ".join(_lf)
                  and len(_spawned) == 1
                  and _spawned[0]["argv"][3] == "lifecycle-exec")
            del _spawned[:]
            _lf2 = check_revival(cargs, cbase, rsnap(absent=[gone()]), None, wstate, wnotes)
            check("⚠ s4-06 WIRED — A STAND-DOWN IS NOT A FIRE: the very next tick stands down "
                  "against the claim this loop wrote itself and NOTHING is forked. The branch is on "
                  "the claim's STRING, not on 'did it not refuse' — a stand-down and a refusal are "
                  "different facts and neither authorises a launch",
                  "claim STOOD-DOWN" in " ".join(_lf2) and "NOT FIRED" in " ".join(_lf2)
                  and len(_spawned) == 0)
            # ---- Stage 4 §4 (s4-07): THE RAM-FLOOR LOUD-REFUSAL PATH ----
            # ⚠ BUILD-LEVEL CONTROLS ONLY, AND FIXTURE-ONLY. Spec §6(c)'s live-fire acceptance —
            # the visible-refusal run and the floor-at-1 control proving the launch COULD have
            # succeeded — is OWNED BY s4-12 and is not duplicated here. No `lifecycle-exec` runs,
            # no memory is actually measured: the executor's RAM gate is the executor's, and this
            # arm is driven by the marker it leaves behind.
            lpkg = Path(td) / "ladderpkg"
            lbase = lpkg / "coordination"
            lbase.mkdir(parents=True)
            (lpkg / "workers").mkdir(parents=True, exist_ok=True)
            (lpkg / "workers" / "dseat.md").write_text(
                "---\nagent: dseat\nmode: interactive\nwindow: control\n---\n\nseat body\n",
                encoding="utf-8")
            (lbase / "workers.md").write_text(
                "| agent | active | pane | summary | checkin | checkout | lastread |\n"
                "|---|---|---|---|---|---|---|\n| dseat | yes | %77 | s | c |  |  |\n",
                encoding="utf-8")
            largs = argparse.Namespace(package=str(lpkg), base=None, workers_dir=None,
                                       notify_to="leader", notify_fallback="leader")
            lmark = lbase / "lifecycle-inflight.json"
            # The floor's ONE home. Declared as the run's own budget.json declares it, with BOTH
            # named thresholds — collapsing them back into one is what `floors._scope` records as
            # permanently unexpressible.
            _FLOOR_FX = 2000

            def lbudget(refuse_field="launch_refuse_mb"):
                (lpkg / "budget.json").write_text(json.dumps(
                    {"floors": {refuse_field: _FLOOR_FX, "pressure_warn_mb": _FLOOR_FX}}),
                    encoding="utf-8")

            # The EXECUTOR's own words, taken from coord's source rather than retyped — see the
            # coupling row below for why that matters.
            _RAM_FAIL = (f"the relaunch was refused on memory after "
                         f"{coord.LIFECYCLE_MEM_RETRIES} retries — the seat is closed and NOT "
                         f"relaunched")

            def lfailed(failure=None):
                lmark.write_text(json.dumps({"dseat": {
                    "state": "FAILED", "disposition": "revive",
                    "failure": failure if failure is not None else _RAM_FAIL,
                    "stamped-at": coord.now(), "steps-completed": [],
                    "caller": {"pid": os.getpid(),
                               "starttime": coord.proc_stat(os.getpid())[1]}}},
                    indent=2, sort_keys=True) + "\n", encoding="utf-8")

            lstate, lnotes = {}, []

            def ltick():
                """One tick. Returns (lines, notes pushed BY THIS TICK, marker entry)."""
                before = len(lnotes)
                out = check_revival(largs, lbase, rsnap(absent=[gone()]), None, lstate, lnotes)
                mk = json.loads(lmark.read_text(encoding="utf-8")) if lmark.exists() else {}
                return out, lnotes[before:], mk.get("dseat", {})

            lbudget()
            _fx.update(panes=set(), wname="control", anchor="")   # no target: nothing can fork
            lfailed()
            del _spawned[:]

            # ---- ROW 1 + ROW 7: transitions ON DISK, and the layer string LEADS the body ----
            l1, n1a, m1a = ltick()
            check("⚠ s4-07 (1): the FIRST tick over an executor entry that FAILED ON MEMORY writes "
                  "`state: blocked` and `blocked_ticks: 1` ON DISK, and the report line carries "
                  "`revival launch gate: RAM floor`. Stage 4 did NOT re-measure anything — the "
                  "measurement is the executor's and this read its verdict",
                  m1a.get("state") == "blocked" and m1a.get("blocked_ticks") == 1
                  and any(REVIVAL_BLOCKED_LINE in l for l in l1) and len(n1a) == 1)
            check("⚠ s4-07 (7): the LAYER STRING LEADS THE BODY — R-8's bar is that a reader cannot "
                  "mistake this TOOL GATE's refusal for the harness permission classifier's, and a "
                  "buried string fails it",
                  str(n1a[0]).startswith(REVIVAL_LAUNCH_LAYER))
            check("⚠ s4-07 (7) RED ARM: the SAME predicate against the SAME body with the layer "
                  "string moved to the END goes red — so the startswith assertion above is worth "
                  "something",
                  not (str(n1a[0])[len(REVIVAL_LAUNCH_LAYER):] + " " + REVIVAL_LAUNCH_LAYER
                       ).startswith(REVIVAL_LAUNCH_LAYER))
            l2, n2a, m2a = ltick()
            check("⚠ s4-07 (1): the SECOND tick increments `blocked_ticks` on disk to 2 and prints "
                  "the line AGAIN — and it pushes NO second note. ⚠ THIS IS ALSO THE ROW THAT "
                  "CATCHES THE MARKER-AS-AUTHORITY BUG: after tick 1 the marker reads `blocked`, "
                  "not `FAILED`, so a ladder keyed on the marker would drop out here and hand the "
                  "seat back to CRASHED. Nothing is forked",
                  m2a.get("blocked_ticks") == 2 and any(REVIVAL_BLOCKED_LINE in l for l in l2)
                  and len(n2a) == 0 and len(_spawned) == 0)
            # RED ARM for row 1: suppress the marker write and the on-disk assertion goes red.
            _mut_pub = inspect.getsource(_publish_ladder).replace(
                "            entry[\"state\"] = marker_state\n", "            return True\n", 1)
            check("s4-07 (1) PRECONDITION: the suppressed-write mutant really applied",
                  _mut_pub != inspect.getsource(_publish_ladder))
            _gp = dict(globals())
            exec(compile(_mut_pub, "<s4-07 row 1 red arm>", "exec"), _gp)       # noqa: S102
            lfailed()
            _rs, _rn = {}, []
            _gp["_publish_ladder"](lbase, "dseat", "blocked",
                                   {"blocked_ticks": 9, "attempts": 1}, "x")
            check("⚠ s4-07 (1) THE RED ARM: with the marker write suppressed, the entry still "
                  "reads `FAILED` with no `blocked_ticks` — the on-disk assertion above goes red, "
                  "proving it observes a real write rather than a state this suite invented",
                  json.loads(lmark.read_text())["dseat"]["state"] == "FAILED"
                  and "blocked_ticks" not in json.loads(lmark.read_text())["dseat"])

            # ---- ROW 2: the `% 3` ESCALATION GATE, not "a note eventually" ----
            lmark.unlink(missing_ok=True)
            lstate.clear()
            del lnotes[:]
            lfailed()
            _esc = []
            for _t in range(1, 13):
                _l, _n, _m = ltick()
                _esc.append((_t, len(_n), _m.get("blocked_ticks"), _m.get("state"),
                             any("ALARM" in str(x) for x in _n)))
                if _m.get("state") == "abandoned":
                    break
            print(f"      s4-07 row 2 ladder trace (tick, notes, blocked_ticks, state, alarm): "
                  f"{_esc}")
            check("⚠ s4-07 (2) THE `% 3` GATE, NOT 'A NOTE EVENTUALLY': an ALARM-worded escalation "
                  "note appears at blocked_ticks 3 AND AGAIN at 6, and at ticks 1, 2, 4 and 5 "
                  "there is NO escalation note. The tick-2, tick-4 and tick-5 ABSENCES are "
                  "asserted, which is what proves the gate is `blocked_ticks % 3 == 0` and not "
                  "'the note fires whenever it feels like it'",
                  [e[4] for e in _esc[:6]] == [False, False, True, False, False, True]
                  and [e[1] for e in _esc[:6]][1] == 0
                  and [e[1] for e in _esc[:6]][3] == 0
                  and [e[1] for e in _esc[:6]][4] == 0)
            _alarm = next(str(x) for x in lnotes if "ALARM" in str(x))
            check("⚠ s4-07 (2): the escalation note NAMES the seat, the REFUSE floor, the measured "
                  "MB from the executor's own failure text, and the elapsed time — a bare 'still "
                  "blocked' teaches the room nothing and gets ignored",
                  all(t in _alarm for t in
                      ("dseat", "REFUSE floor", str(_FLOOR_FX), "CONSECUTIVE TICKS",
                       "refused on memory", "PRESSURE (warn) floor")))

            # ---- ROW 5: ABANDONMENT DOES NOT GO QUIET ----
            _ab = [e for e in _esc if e[3] == "abandoned"]
            check("⚠ s4-07 (5): after 3 attempts the marker reads `state: abandoned` ON DISK and "
                  "the retries STOP. It lands at blocked_tick 9 — attempt 2 fired at 3, attempt 3 "
                  "at 6, and the fourth is refused — which is the arithmetic the shared "
                  "escalate/retry cadence produces and the reason both escalations are reachable "
                  "at all",
                  len(_ab) == 1 and _ab[0][0] == 9 and _esc[-1][3] == "abandoned"
                  and _esc[-1][1] == 1 and _esc[-1][4] is False)
            check("⚠ s4-07 — THE PROJECTION IS WIPED AT EVERY FIRE AND THE LADDER SURVIVES IT, "
                  "WHICH IS THE WHOLE PRIN-11 CLAIM. On the RETRY ticks (3 and 6) the marker's "
                  "`blocked_ticks` reads NOTHING: the claim rewrites the entry, and the child's "
                  "`coord.stamp_lifecycle` would replace it wholesale anyway. The ladder counts "
                  "straight through — 2 -> 4 -> 5 -> 7 — because its counters live in THIS loop's "
                  "own persisted state and the marker carries only a projection of them",
                  [e[2] for e in _esc[:7]] == [1, 2, None, 4, 5, None, 7])
            _post = [ltick() for _ in range(3)]
            check("⚠ s4-07 (5) THE HOLE NEVER GOES QUIET: the report line STILL PRINTS on every "
                  "tick after abandonment",
                  all(any(REVIVAL_ABANDONED_LINE in l for l in p[0]) for p in _post))
            check("⚠ s4-07 (5) THE CONTROL THAT SEPARATES VISIBLE FROM SPAMMING: no note is "
                  "re-pushed on any of those ticks — ONE loud note at abandonment, then "
                  "report-only. A single assertion conflates the two; this one does not",
                  all(len(p[1]) == 0 for p in _post))
            check("⚠ s4-07 (5): and NOTHING is fired on any post-abandonment tick — the "
                  "do-not-retry gate `s4-05` left for this task is in `claim_revival` step 4, so "
                  "even a caller that reached the claim would be REFUSED",
                  len(_spawned) == 0
                  and claim_revival(lbase, "dseat", "%77", [], {})[0] == "REFUSED")
            check("s4-07 (5) RED ARM for that gate: the SAME claim against the SAME entry with "
                  "`abandoned` swapped for a terminal `done` is CLAIMED — so the refusal above is "
                  "the `abandoned` state's doing and not something else refusing first",
                  (lambda: (json.loads(lmark.read_text()),
                            lmark.write_text(json.dumps(
                                {"dseat": dict(json.loads(lmark.read_text())["dseat"],
                                               state="done")}, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8"),
                            claim_revival(lbase, "dseat", "%77", [], {})[0])[-1])() == "CLAIMED")

            # ---- ROW 3: THE FIELD NAME IS READ, NOT GUESSED ----
            lbudget(refuse_field="ram_available_mb")            # the SPEC's stale, RETIRED name
            _w_stale, _r_stale = revival_floors(largs, lbase)
            lbudget()                                          # the name that is actually on disk
            _w_ok, _r_ok = revival_floors(largs, lbase)
            check("⚠ s4-07 (3) THE ROW THAT CATCHES AN IMPLEMENTER WHO BUILT FROM THE SPEC TEXT "
                  "INSTEAD OF DISK: a budget.json declaring the SPEC's stale `floors."
                  "ram_available_mb` with `launch_refuse_mb` ABSENT FAILS LOUD with "
                  "`FloorUndeclared` and substitutes NO number. Task 7.82 split the pre-7.82 field "
                  "into two named thresholds and RETIRED the old name",
                  "FloorUndeclared" in _r_stale and "UNRESOLVED" in _r_stale
                  and str(_FLOOR_FX) not in _r_stale)
            check("⚠ s4-07 (3) CONTROL: renaming it to `launch_refuse_mb` makes the SAME call "
                  "resolve, with the value and the `why` that is task 7.82 criterion 8's "
                  "acceptance — the consumer must SAY which value it used and why",
                  str(_FLOOR_FX) in _r_ok and "budget.json" in _r_ok
                  and "FloorUndeclared" not in _r_ok)

            # ---- ROW 8: THE TWO FLOORS, REPORTED SEPARATELY AND NEVER CONFLATED ----
            check("⚠ s4-07 (8b): the report names the REFUSE floor the executor reads via "
                  "`floor_source(run_root, 'refuse', None)`, WITH its why, and labels it as the "
                  "one the revival launch gate reads",
                  "launch_refuse_mb" in _r_ok and "revival launch gate reads" in _r_ok)
            check("⚠ s4-07 (8a): the report names the WARN floor THIS RUNNING LOOP HOLDS, read "
                  "from /proc, and LABELS it the PRESSURE floor with an explicit statement that it "
                  "did NOT gate the revival launch. `--mem-floor-mb` resolves the WARN floor alone "
                  "and feeds only the pressure flag",
                  "PRESSURE (warn) floor this loop HOLDS" in _w_ok
                  and "/proc/" in _w_ok
                  and "DID NOT GATE THE REVIVAL LAUNCH" in _w_ok)
            # ⚠ SUBSTITUTED CONTROL, DISCLOSED. The task's control launches "the fixture loop with
            # `--mem-floor-mb 1` against a budget.json declaring 2000". This suite IS the loop and
            # cannot rewrite its own /proc argv — so the identical measurement is taken in a REAL
            # CHILD whose argv really carries the flag, against this fixture's budget.json. The
            # function under test is the shipped one, read out of this file.
            _probe = (
                "import sys, importlib.util\n"
                "spec = importlib.util.spec_from_file_location('w', %r)\n"
                "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
                "print(m._loop_warn_floor())\n" % str(Path(__file__).resolve()))
            _pr = _popen_real([sys.executable, "-c", _probe, "--mem-floor-mb", "1"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            _child_warn = (_pr.communicate()[0] or "").strip()
            check("⚠ s4-07 (8) THE DIVERGENCE CONTROL (substituted, and the substitution is "
                  "stated): a REAL child whose argv carries `--mem-floor-mb 1` reports the WARN "
                  "floor as 1 and calls it an explicit operator override, while this fixture's "
                  "budget.json declares %d for BOTH thresholds. The two are reported "
                  "INDEPENDENTLY and correctly labelled, and NOTHING claims the warn floor gated "
                  "the launch — it cannot: the revival gate is the executor's fresh "
                  "read_floor(run_root, 'refuse') in a per-launch fork that cannot inherit this "
                  "loop's argv" % _FLOOR_FX,
                  "--mem-floor-mb 1" in _child_warn
                  and "explicit operator override" in _child_warn
                  and "DID NOT GATE THE REVIVAL LAUNCH" in _child_warn
                  and str(_FLOOR_FX) not in _child_warn)
            check("s4-07 (8) THE INSTRUMENT'S OWN CONTROL: THIS process's argv carries no "
                  "`--mem-floor-mb`, and the same function says so instead of inventing a number "
                  "— so the child's answer above is its argv's doing, not the function's default",
                  "no --mem-floor-mb in argv" in _w_ok)

            # ---- ROW 6: THE UNDELIVERED PATH IS REAL ----
            _undel = lbase / "undelivered-flags.md"
            _send_real = coord.cmd_send
            try:
                coord.cmd_send = lambda ns: (_ for _ in ()).throw(SystemExit(2))
                notify_leader(largs, Flag("dseat", str(lnotes[0])))
                check("⚠ s4-07 (6): with `coord.cmd_send` forced to SystemExit the flag lands in "
                      "the package's `undelivered-flags.md` — a plain append under "
                      "`coordination/` that the messaging layer cannot refuse, which is the whole "
                      "point of not routing this report back through the layer it reports on",
                      _undel.exists() and REVIVAL_LAUNCH_LAYER in _undel.read_text()
                      and "UNDELIVERED" in _undel.read_text())
                _sent = []
                coord.cmd_send = lambda ns: _sent.append(ns.message)
                _bytes_before = _undel.read_bytes()
                notify_leader(largs, Flag("dseat", str(lnotes[0])))
                check("⚠ s4-07 (6) CONTROL: the SAME call with sending WORKING puts the note on "
                      "the bus and appends NOTHING to `undelivered-flags.md` — without this the "
                      "row above could pass against a path that always appends",
                      len(_sent) == 1 and REVIVAL_LAUNCH_LAYER in _sent[0]
                      and _undel.read_bytes() == _bytes_before)
            finally:
                coord.cmd_send = _send_real

            # ---- THE COUPLING TO THE EXECUTOR'S WORDING, ASSERTED RATHER THAN TRUSTED ----
            check("⚠ s4-07 COUPLING: the RAM-refusal discriminator is a SUBSTRING OF THE "
                  "EXECUTOR'S OWN failure text, and that coupling is real. Asserted directly "
                  "against `coord.lifecycle_memory_gate`'s source, so a Stage 3 reword goes RED "
                  "here instead of this predicate silently answering 'not a RAM refusal' forever "
                  "— which would turn every blocked revival back into a re-fire loop",
                  REVIVAL_RAM_FAILURE_MARK in inspect.getsource(coord.lifecycle_memory_gate))
            check("⚠ s4-07 COUPLING CONTROL: a NON-RAM executor failure is NOT swallowed by the "
                  "ladder — it gets its own Stage-4 note and the seat proceeds to be re-claimed, "
                  "because memory pressure is the one refusal reason that clears on its own and "
                  "the others are not",
                  (lambda: (lstate.clear(), lmark.unlink(missing_ok=True),
                            lfailed("the tmux target could not be validated"),
                            revival_ladder(largs, lbase, "dseat",
                                           json.loads(lmark.read_text())["dseat"],
                                           {}, lnotes, {}))[-1])()[0] == "PROCEED")

            # ---- ROW 4: NO LITERAL FLOOR ANYWHERE ----
            # ⚠ THE TASK SAYS "floor-lint exits 0 over the changed tree" AND IT DOES NOT — it
            # exits 1 on a PRE-EXISTING violation in `materialize-seats.py` (a `--mem-floor-mb`
            # argparse default) that is not this task's and is not in its write set. Its line and
            # value are deliberately NOT written here: a floor literal in a comment is a literal,
            # and this file must not add one for the linter to find. So the row asserts
            # the claim that IS this task's: `watch.py` contributes ZERO violations, and the only
            # violation in the tree is that one. Stated rather than passed off as a green.
            _fl = _popen_real([sys.executable, str(Path(__file__).resolve().parent /
                                                   "floor-lint.py")],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            _fl_out = (_fl.communicate()[0] or "")
            _viol = [ln.strip() for ln in _fl_out.splitlines()
                     if ln.startswith("  ") and "value=" in ln and "[" not in ln]
            check("⚠ s4-07 (4) NO LITERAL FLOOR FROM THIS TASK: `floor-lint.py` reports ZERO "
                  "violations in `watch.py`. ⚠ IT EXITS 1, NOT 0 AS THE TASK TEXT SAYS, on a "
                  "PRE-EXISTING violation in `materialize-seats.py` that is neither this task's "
                  "nor in its write set — asserted explicitly so the exit code is not read as this "
                  "arm's",
                  not any("watch.py" in v for v in _viol)
                  and all("materialize-seats.py" in v for v in _viol) and len(_viol) == 1)
            check("⚠ s4-07 (4) THE RED ARM: the SAME linter over a copy of THIS FILE with "
                  "`floor_mb = <a literal>` inserted DOES report it — so the row can go red, and "
                  "the green above is the absence of a literal rather than a linter that cannot "
                  "see this file",
                  (lambda: (
                      (Path(td) / "floorlint" / "ignite" / "team-kit").mkdir(parents=True,
                                                                            exist_ok=True),
                      # ⚠ THE MUTANT USES `mem_floor_mb`, NOT `floor_mb`, AND THE REASON IS A
                      # MEASURED GAP IN THE LINTER: floor-lint's KNOB pattern matches
                      # `--mem-floor-mb`, `mem_floor_mb`, `MEM_FLOOR*`, `LAUNCH_MEM_FLOOR*`,
                      # `ram_available_mb`, `launch_refuse_mb`, `pressure_warn_mb` and
                      # `ram_floor_mb` — and NOT a bare `floor_mb`, which is the exact name
                      # `coord.memory_gate`'s own required parameter carries. A red arm written
                      # with `floor_mb` stays GREEN and proves nothing; measured, not assumed.
                      (Path(td) / "floorlint" / "ignite" / "team-kit" / "watchcopy.py").write_text(
                          "def go(args):\n    mem_floor_mb = %d\n    return mem_floor_mb\n"
                          % _FLOOR_FX, encoding="utf-8"),
                      _popen_real([sys.executable,
                                   str(Path(__file__).resolve().parent / "floor-lint.py"),
                                   "--repo", str(Path(td) / "floorlint")],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True).communicate()[0])[-1])().count("watchcopy.py") >= 1)

        finally:
            subprocess.Popen = _popen_real
            (coord.live_panes, coord.tmux_pane_window_name,
             coord.tmux_find_window_pane) = _tmux_real
        check("s4-06 HYGIENE: the three tmux reads and `subprocess.Popen` are RESTORED to the real "
              "implementations before the suite leaves the revival region — a substitution that "
              "leaks makes every later row's evidence a fixture's",
              coord.live_panes is _tmux_real[0] and subprocess.Popen is _popen_real)
        cclean()

        # ---- dag-12: the STALLED-BLOCKING-DEPENDENTS flag (RS-9, RS-10, RS-15, RS-16) ----
        # ⚠⚠ THE INSTRUMENT DEFECT THIS BLOCK IS BUILT AROUND, MEASURED BEFORE THE CODE EXISTED.
        # Run against the pre-change file, RS-9's two NEGATIVE arms and RS-15's degradation arm all
        # PASSED — because a function that does not exist pushes no flag, so "no flag" is satisfied
        # by absence. Three of the four spec controls were VACUOUS AS WRITTEN. Every negative row
        # below is therefore asserted TOGETHER WITH its positive twin over the SAME fixture with ONE
        # cell changed: the pair is the control, and neither half is evidence alone.
        # ⚠ NO TMUX AND NO ACTUATION ANYWHERE IN THIS BLOCK — nothing here can reach one: the flag's
        # whole call graph is asserted below to contain no actuator symbol at all.
        spkg = Path(td) / "stalledpkg"
        sbase = spkg / "coordination"
        swork = spkg / "workers"
        sbase.mkdir(parents=True); swork.mkdir(parents=True)
        sargs = argparse.Namespace(package=str(spkg), base=None, workers_dir=None, run=None,
                                   notify_to="chief-of-staff", notify_fallback="leader",
                                   inactive_min=30)
        sstate, snotes = {}, []

        def stf(*rows):
            """Write taskforce.csv — `(seat, after)` pairs, the real header, the real separator."""
            out = ["taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id"]
            out += [f"tf-s,{s},{a},claude,opus,low,60,m1" for s, a in rows]
            (spkg / "taskforce.csv").write_text("\n".join(out) + "\n", encoding="utf-8")

        def ssnap(absent=(), seats=(), alive=True, age_s=0):
            return {"captured_at": time.time() - age_s, "session_alive": alive,
                    "session": "ssess", "seats": list(seats), "roster_absent": list(absent)}

        def sgone(seat="P", pane="%77"):
            return {"seat": seat, "pane": pane, "roster_active": True, "liveness": "absent",
                    "reason": "roster row active, pane not in the room"}

        def squiet(seat="P", pane="%9", age=7200.0):
            return {"seat": seat, "pane": pane, "roster_active": True, "liveness": "live",
                    "harness_pid": 4242, "prompt_pending": False, "last_activity_age_s": age}

        def sb(snap, snap_err=None, fresh=True):
            """One tick. Returns (report lines, notes pushed BY THIS TICK)."""
            if fresh:
                sstate.clear()
                del snotes[:]
            before = len(snotes)
            out = check_stalled_blocking(sargs, sbase, snap, snap_err, sstate, snotes)
            return out, snotes[before:]

        (sbase / "awaiting-close.json").write_text("{}")

        # ---- RS-9 — THE PAIR, and the pair is the control. Same snapshot, `after` cells the ONE
        # difference between the two arms.
        stf(("P", ""), ("D1", "P"), ("D2", "P"))
        l_dep, n_dep = sb(ssnap(absent=[sgone()]))
        stf(("P", ""), ("D1", ""), ("D2", ""))
        l_leaf, n_leaf = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12 RS-9: a stalled seat WITH dependents raises the flag and a stalled LEAF "
              "raises NONE — asserted as ONE predicate over the same snapshot with only the `after` "
              "cells changed. ⚠ MEASURED: the leaf arm ALONE passes against a file where the flag "
              "does not exist at all, so it is evidence only paired with the arm above it",
              len(n_dep) == 1 and n_leaf == []
              and any(STALLED_LINE in l for l in l_dep)
              and not any(STALLED_LINE in l for l in l_leaf)
              and any("blocks nobody" in l for l in l_leaf))
        check("dag-12 RS-9: the LEAF arm still PRINTS every tick — a stalled seat that blocks "
              "nobody is reported and not silently dropped, because silence is indistinguishable "
              "from a check that is switched off",
              len(l_leaf) == 1 and l_leaf[0].startswith("P "))

        # ---- RS-9 second arm — a LIVE seat with dependents. The pair differs in ONE FIELD.
        stf(("P", ""), ("D1", "P"))
        l_live, n_live = sb(ssnap(seats=[squiet(age=60.0)]))
        l_stall, n_stall = sb(ssnap(seats=[squiet(age=7200.0)]))
        check("⚠ dag-12 RS-9 (LIVE arm): a LIVE seat with dependents raises NOTHING at 1 min idle "
              "and DOES raise at 120 min — one field of one snapshot row is the whole difference. "
              "Shape A is a seat still ALIVE in its pane past a natural end, so the quiet arm is "
              "the only one that can see it; the pair proves the threshold is read rather than the "
              "arm being dead",
              n_live == [] and len(n_stall) == 1
              and not any(STALLED_LINE in l for l in l_live)
              and any(STALLED_LINE in l and "alive in pane" in l for l in l_stall))
        check("⚠ dag-12: a snapshot row with NO `last_activity_age_s` reading is NOT read as zero "
              "and NOT read as a stall — no reading is not a reading. Control: the same row with "
              "the field present past the cadence DOES fire",
              sb(ssnap(seats=[{"seat": "P", "pane": "%9", "roster_active": True,
                               "liveness": "live"}]))[1] == []
              and len(sb(ssnap(seats=[squiet()]))[1]) == 1)
        check("dag-12: a snapshot row whose seat is NOT roster-active is never a candidate — the "
              "quiet arm reads the sensor's own roster_active and does not re-derive it",
              sb(ssnap(seats=[dict(squiet(), roster_active=False)]))[1] == [])

        # ---- RS-16 — the dependents are NAMED, in the flag text AND the report line.
        stf(("P", ""), ("D1", "P"), ("D2", "P"), ("E", ""))
        l2, n2 = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12 RS-16: the flag text names P and EVERY row that names P in its `after` set "
              "— both dependents, the count, and NOT the unrelated seat. A flag that says 'someone "
              "is blocked' hands the reader the reconstruction work the whole design refuses.\n"
              "      ⚠ INSTRUMENT NOTE: the first draft of this row asserted `\"E\" not in <flag>` "
              "to prove the unrelated seat is excluded. THAT WENT RED FOR THE WRONG REASON — the "
              "flag body is full of capital-E prose (STALLED_LIMIT's own uppercase). A one-letter "
              "seat name is unmatchable in free text, so exclusion is asserted on the DEPENDENT "
              "LIST SEGMENT instead, which is the only place a wrong name could appear",
              len(n2) == 1 and "'P'" in n2[0] and "2 seat(s)" in n2[0]
              and "ready while this holds: D1, D2." in n2[0]
              and "blocks 2: D1, D2" in " ".join(l2))
        check("⚠ dag-12 RS-16 CONTROL: the SAME fixture with P's dependents repointed at E names "
              "NEITHER P nor a dependent — so the row above is reading the `after` cells and not "
              "printing a list it built from the roster",
              (stf(("P", ""), ("D1", "E"), ("D2", "E"), ("E", "")) or True)
              and sb(ssnap(absent=[sgone()]))[1] == [])

        # ---- RS-16 / THE HONEST LIMIT — carried IN THE FLAG, where the reader meets it (R-6).
        stf(("P", ""), ("D1", "P"), ("D2", "P"))
        _, n3 = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12 R-6: the SHAPE-A LIMIT rides in the flag body itself, not only in a task "
              "file — the reader who has to act on this flag is told, in the same sentence, that a "
              "dirty finish and a crash are NOT distinguishable here and that nothing was "
              "actuated. Asserted against the STALLED_LIMIT constant, so a reword of the constant "
              "cannot leave this row passing against stale text",
              len(n3) == 1 and STALLED_LIMIT in n3[0]
              and "NOTHING WAS ACTUATED BY THIS FLAG" in n3[0]
              and "CANNOT TELL A DIRTY FINISH FROM A CRASH" in STALLED_LIMIT
              and "done contract" in STALLED_LIMIT)

        # ---- the TERMINAL-DISPOSITION term: a seat that checked out is not stalled. Both arms.
        (sbase / "awaiting-close.json").write_text(json.dumps({"P": {"since": "x",
                                                                    "disposition": "done"}}))
        l_out, n_out = sb(ssnap(absent=[sgone()]))
        (sbase / "awaiting-close.json").write_text("{}")
        l_in, n_in = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12: a candidate WITH a terminal disposition on record is not a stall (both "
              "arms: `done` on record → no flag; the identical fixture with the record removed → "
              "flag). The term goes through `coord.terminal_disposition` — dag-09/dag-10's own "
              "reader — so this arm and `ready-seats` can never disagree about what a check-out is",
              n_out == [] and len(n_in) == 1
              and any("checked out `done`" in l for l in l_out)
              and any(STALLED_LINE in l for l in l_in))
        (spkg / "sessions.csv").write_text(
            ",".join(coord.SESSIONS_COLS) + "\n"
            "s1,P,claude,,,,2026-01-01,2026-01-02,,,,done\n", encoding="utf-8")
        (sbase / "awaiting-close.json").write_text(json.dumps({"P": {"since": "x",
                                                                    "disposition": "renew"}}))
        l_skew, n_skew = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12: DISPOSITION SKEW is REPORTED AND REFUSED, never tie-broken — the two "
              "records of one seat's own ending disagree, both are named, and no flag is pushed. "
              "Picking a winner would be this loop deciding a question only a human may",
              n_skew == [] and any("SKEW" in l and "awaiting-close.json=renew" in l
                                   and "sessions.csv=done" in l for l in l_skew))
        (spkg / "sessions.csv").unlink()
        (sbase / "awaiting-close.json").write_text("{}")

        # ---- RS-15 (a) THE OBSERVATION BOUND — `stalled_candidates` takes the parsed snapshot and
        # NOTHING ELSE, asserted over its AST rather than promised in prose.
        _READERS = {"open", "read_text", "read_bytes", "load", "loads", "read_csv_table",
                    "load_workers", "discover_workers", "load_awaiting", "load_closing",
                    "taskforce_after", "terminal_disposition", "session_disposition",
                    "pane_tail", "pane_cwd", "live_panes", "window_panes", "Path", "glob",
                    "iterdir", "listdir", "run", "check_output", "Popen"}

        def _reader_syms(src):
            t = _ast_mod.parse(_textwrap.dedent(src))
            return (({n.id for n in _ast_mod.walk(t) if isinstance(n, _ast_mod.Name)}
                     | {n.attr for n in _ast_mod.walk(t) if isinstance(n, _ast_mod.Attribute)})
                    & _READERS)
        _obs_src = inspect.getsource(stalled_candidates)
        check("⚠ dag-12 RS-15 (a) THE OBSERVATION BOUND, AT THE SCOPE THAT CAN HOLD IT: every "
              "OBSERVATION the flag makes comes from the snapshot and nothing else — "
              "`stalled_candidates` references NO file, pane, roster or process reader at all, so "
              "there is no second observation path to reach around the sensor with (CMP-21 "
              "invariant 1's actual words: no tmux pane, no session file, no /proc, no prompt)",
              _reader_syms(_obs_src) == set())
        check("⚠ dag-12 RS-15 (a) RED ARM: the SAME predicate over the SAME function with one "
              "`coord.load_workers(base)` inserted REPORTS it — the row can go red, and the "
              "mutation is asserted to have applied so a failed replace cannot pass as a green",
              (lambda m: m != _obs_src and _reader_syms(m) == {"load_workers"})(
                  _obs_src.replace("    out = {}", "    out = {}\n    coord.load_workers(base)", 1)))

        # ---- RS-15 (b) THE READ INVENTORY OF THE WHOLE ARM IS CLOSED AND ASSERTED.
        # ⚠⚠ RS-15 AS THE SPEC WROTE IT ("grep the flag's code path for any other file read → ZERO")
        # IS UNSATISFIABLE TOGETHER WITH RS-16, and this row is the honest replacement rather than a
        # dropped control. state.json's schema (`team-monitor/1`) carries NO dependency field — the
        # `after` sets live in taskforce.csv and the dispositions in awaiting-close.json /
        # sessions.csv — so a flag reading only the snapshot could never name a dependent, which is
        # exactly what RS-16 demands. What is asserted instead: the non-snapshot reads are EXACTLY
        # the registry read and the ledger read, both delegated to coord's single-source readers,
        # and a THIRD reader added anywhere in the arm turns this row red.
        _arm12 = "\n".join(inspect.getsource(f) for f in
                           (check_stalled_blocking, stalled_candidates, blocking_dependents,
                            snapshot_age_s))
        _expect12 = {"taskforce_after", "terminal_disposition", "load_awaiting"}
        check("⚠ dag-12 RS-15 (b) — RS-15's LITERAL FORM IS UNSATISFIABLE WITH RS-16 AND THIS IS "
              "THE STRONGEST FORM THAT IS NOT: over the WHOLE flag's call graph the reader symbols "
              "are EXACTLY {taskforce_after, terminal_disposition, load_awaiting} — the run's "
              "REGISTRY and its CHECK-OUT RECORD, neither of which any sensor observes or "
              "publishes, each through dag-09/dag-10's own reader and never a second parse. No "
              "tmux, no /proc, no pane, no roster, no direct open()",
              _reader_syms(_arm12) == _expect12)
        check("⚠ dag-12 RS-15 (b) RED ARM: the same predicate over the same arm with a "
              "`coord.load_workers` and a bare `open` inserted reports BOTH — so the inventory is "
              "CLOSED rather than merely listed, and this is the row that catches the next reader "
              "somebody adds here",
              _reader_syms(_arm12 + "\ncoord.load_workers(b)\nopen(p)\n")
              == _expect12 | {"load_workers", "open"})

        # ---- RS-15 (c) THE DEGRADATION ARM — literal, and the one half of RS-15's control that
        # DOES hold as written. Paired, because absence satisfies it vacuously on its own.
        stf(("P", ""), ("D1", "P"))
        _bad = ssnap(absent=[sgone()])
        _bad.pop("roster_absent"); _bad.pop("seats")
        l_bad, n_bad = sb(_bad)
        l_good, n_good = sb(ssnap(absent=[sgone()]))
        check("⚠ dag-12 RS-15 (c): a state.json MISSING `roster_absent`/`seats` degrades to NO "
              "FLAG — it does not read around the sensor to the roster or to tmux to find the "
              "absence it could not see. Paired with the identical-but-complete snapshot that DOES "
              "fire, because 'no flag' is satisfied by a check that is switched off",
              n_bad == [] and len(n_good) == 1
              and l_bad == [STALLED_OK_LINE] and any(STALLED_LINE in l for l in l_good))
        check("dag-12: a run with NO taskforce.csv says so and pushes nothing — dependency is "
              "UNKNOWABLE there, and this module ships kit-wide to packages that have no DAG at "
              "all. Control: the same snapshot with the file present fires",
              ((spkg / "taskforce.csv").unlink() or True)
              and sb(ssnap(absent=[sgone()])) == ([STALLED_NO_DAG_LINE], [])
              and (stf(("P", ""), ("D1", "P")) or True)
              and len(sb(ssnap(absent=[sgone()]))[1]) == 1)

        # ---- STALENESS: enforcement PAUSES, and the two homes of the age are asserted to AGREE.
        l_st, n_st = sb(ssnap(absent=[sgone()], age_s=budget_mod.STALE_AFTER_S + 60))
        check("⚠ dag-12: a STALE snapshot PAUSES this flag (CMP-21 invariant 2 — stale data is "
              "evidence in NEITHER direction) and says so every tick; nothing is pushed. Control: "
              "the same fixture FRESH fires",
              n_st == [] and any(STALLED_STALE_LINE in l for l in l_st)
              and len(sb(ssnap(absent=[sgone()]))[1]) == 1)
        check("⚠ dag-12 THE DECLARED-DUPLICATION GUARD: `snapshot_age_s` and `check_revival`'s "
              "INLINE age computation are asserted to AGREE on the same snapshot on BOTH sides of "
              "budget_mod.STALE_AFTER_S. The duplication is real and declared (check_revival is "
              "stage 4's function and out of dag-12's write set); this is the deterministic check "
              "that makes it PRIN-11's sanctioned break rather than a silent second home — a "
              "threshold or field change on either side goes red here",
              (lambda stale, fresh: (
                  snapshot_age_s(stale) > budget_mod.STALE_AFTER_S
                  and any(REVIVAL_STALE_LINE in l for l in
                          check_revival(rargs, rbase, stale, None, {}, []))
                  and snapshot_age_s(fresh) <= budget_mod.STALE_AFTER_S
                  and not any(REVIVAL_STALE_LINE in l for l in
                              check_revival(rargs, rbase, fresh, None, {}, []))))(
                  ssnap(age_s=budget_mod.STALE_AFTER_S + 60), ssnap()))
        check("dag-12: an ABSENT state.json takes the SILENT path (no line at all), while one that "
              "EXISTS and cannot be read is a sensor outage that PAUSES loudly — the same "
              "absent-vs-unreadable split the revival arm keeps, through the same discriminator",
              check_stalled_blocking(sargs, sbase, None, "state.json is ABSENT at /x", {}, []) == []
              and any(STALLED_STALE_LINE in l for l in check_stalled_blocking(
                  sargs, sbase, None, "state.json is UNREADABLE at /x: Expecting value", {}, [])))
        check("dag-12: a DEAD ROOM short-circuits — every seat is absent when the session is gone, "
              "and N stall flags for ONE incident point the reader at the wrong mechanism",
              sb(ssnap(absent=[sgone()], alive=False))[1] == []
              and "room dead" in " ".join(sb(ssnap(absent=[sgone()], alive=False))[0]))

        # ---- ARMING: the line prints every tick, the flag is pushed ONCE, and it RE-ARMS.
        stf(("P", ""), ("D1", "P"))
        l1, p1 = sb(ssnap(absent=[sgone()]))
        l2, p2 = sb(ssnap(absent=[sgone()]), fresh=False)
        l3, p3 = sb(ssnap(seats=[squiet(age=0.0)]), fresh=False)
        l4, p4 = sb(ssnap(absent=[sgone()]), fresh=False)
        check("⚠ dag-12: the REPORT LINE prints on every tick (a hole must never go quiet) while "
              "the FLAG is pushed ONCE per episode — and it RE-ARMS after the seat is seen healthy, "
              "so a second, genuinely different stall is not mute. Four ticks, one fixture",
              len(p1) == 1 and p2 == [] and p3 == [] and len(p4) == 1
              and all(any(STALLED_LINE in l for l in ls) for ls in (l1, l2, l4))
              and l3 == [STALLED_OK_LINE])

        # ---- RS-10 — THE ACTUATOR COUNT. This section is NOT the file's one arm.
        check("⚠⚠ dag-12 RS-10 — THE ACTUATOR COUNT OF THIS FILE STAYS **ONE**, AND THIS FLAG IS "
              "NOT IT: over the WHOLE stalled-blocking arm's call graph there is not one fork, "
              "exec, subprocess, launch, kill or tmux symbol. Asserted with the SAME predicate "
              "`s4-06 LG-16 (c)` uses on the revival arm, so the two rows together are the file's "
              "arm inventory. A second actuator arm here would re-open the double-launch question "
              "stage 4 closed",
              _actuator_syms(_arm12) == set())
        check("⚠ dag-12 RS-10 RED ARM: the same predicate over the same arm with `launch_seat` and "
              "`subprocess.Popen` inserted reports BOTH — so the row can go red, and it is the row "
              "that catches the next arm somebody adds to THIS section (LG-16 (c) does not: it "
              "scans the revival arm's call graph and this section sits outside it)",
              _actuator_syms(_arm12 + "\ncoord.launch_seat(x)\nsubprocess.Popen(y)\n")
              == {"launch_seat", "subprocess", "Popen"})
        check("⚠ dag-12 RS-10 (the other direction): the flag is NOT ROUTED INTO the revival arm "
              "either — a flag that merely avoided calling Popen itself while handing its seat to "
              "`fire_revival`/`claim_revival` would be a second arm wearing a report's clothes. "
              "Asserted over the arm's own AST",
              not ({"fire_revival", "claim_revival", "revival_ladder", "check_revival"}
                   & ({n.id for n in _ast_mod.walk(_ast_mod.parse(_arm12))
                       if isinstance(n, _ast_mod.Name)}
                      | {n.attr for n in _ast_mod.walk(_ast_mod.parse(_arm12))
                         if isinstance(n, _ast_mod.Attribute)})))
        check("⚠ dag-12 RS-10 CONTROL for the row above: the same predicate DOES see those names "
              "when they are present — proving the set is matched rather than never matchable",
              {"fire_revival", "claim_revival"} <= (
                  {n.attr for n in _ast_mod.walk(_ast_mod.parse(
                      _arm12 + "\nx.fire_revival()\nx.claim_revival()\n"))
                   if isinstance(n, _ast_mod.Attribute)}))

        # ---- WIRED: `run_pass` really calls it, and its lines stay OUT of `report`.
        _rp = inspect.getsource(run_pass)
        check("⚠ dag-12 WIRED: `run_pass` calls `check_stalled_blocking` and PRINTS its lines, and "
              "they are kept OUT of `report` — the pass header counts `report` as 'N active "
              "seat(s)' and folding a stall line in would corrupt a number every reader trusts. A "
              "flag nothing calls is a green suite over dead code (G-78)",
              "check_stalled_blocking(args, base, snap, snap_err, state, notes)" in _rp
              and "for line in stalled_lines:" in _rp
              and "report.append" not in _rp.split("stalled_lines = ")[1].split("for r in rows")[0])
        check("⚠ dag-12 WIRED CONTROL: the charter's one-actuator paragraph in `run_pass` now names "
              "BOTH assertions that cover the count — it claimed 'a second arm added anywhere here' "
              "would turn LG-16 (c) red, and that became FALSE the moment a second arm-shaped "
              "section landed outside the revival call graph. The correction is asserted here so "
              "the charter cannot go stale silently",
              "dag-12 RS-10" in _rp and "covered by TWO rows, one per arm" in _rp)

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

        # ---- G-297: THE RUN-CLOSED LOOP-TURN GUARD ----
        # ⚠ EVERY ROW BELOW DRIVES `watch_loop`, NOT `run_closed`. A suite that only asserted the
        # predicate's verdicts would stay green with the guard DELETED from the loop — and that is
        # this defect's own shape: team_monitor.py:936 asserted its session derivation was
        # self-consistent, never that it agreed with a live room, and stayed green through the whole
        # defect. So the fixture counts the turns the LOOP actually took.
        import io
        import contextlib

        class _RCLoopRanOn(Exception):
            """Raised BY THE FIXTURE to escape a loop that did NOT stop — never by watch_loop."""

        rcgoal = Path(td) / "runclosed-goal"
        rcrun = rcgoal / "runs" / "run-7"
        rcrun.mkdir(parents=True)
        rccsv = rcgoal / "runs.csv"
        # `cadence_s`, not `loop`: task 7.112 retired the minute-denominated flag, and this fixture
        # is a CALLER of `watch_loop`, so it moves with the signature. It carried `loop=1` — the
        # interim 60 s overshoot — which no longer means anything to the loop.
        rcargs = argparse.Namespace(cadence_s=30)

        def _rcturns(payload, root=rcrun, limit=3):
            """(stopped_by_the_guard, turns_taken, printed) for one runs.csv payload.

            `payload` None deletes the file; bytes are written raw (the undecodable case). `limit`
            turns with no stop IS the negative result — an unguarded loop never returns on its own.
            """
            if payload is None:
                if rccsv.exists():
                    rccsv.unlink()
            elif isinstance(payload, bytes):
                rccsv.write_bytes(payload)
            else:
                rccsv.write_text(payload, encoding="utf-8")
            turns = []

            def _pass(_a):
                turns.append(1)
                if len(turns) >= limit:
                    raise _RCLoopRanOn

            stopped, buf = True, io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    watch_loop(rcargs, root, do_pass=_pass, sleep_fn=lambda _s: None)
            except _RCLoopRanOn:
                stopped = False
            return stopped, len(turns), buf.getvalue()

        _CLOSED = "run-id,type,state,taskforce-ids,opened,closed\nrun-7,build,closed,,,2026-07-29\n"
        _OPEN = "run-id,type,state,taskforce-ids,opened,closed\nrun-7,build,open,,,\n"

        _st, _turns, _out = _rcturns(_CLOSED)
        check("⚠ G-297 THE CRITERION ITSELF: with THIS run's row reading closed the LOOP RETURNS — "
              "and it returns BEFORE taking a pass, so a loop started against a closed run never "
              "writes into it. Unguarded, this loop outlived run-2 by ~9.5h still mutating a folder "
              ".rbtv/goals/CLAUDE.md rules is append-only history",
              (_st, _turns) == (True, 0))
        check("G-297: the exit prints ONE distinct deterministic-close line, so a reader of the log "
              "can tell a ruled close from a crash or a reap",
              _out.strip() == RUN_CLOSED_LINE and RUN_CLOSED_LINE.strip() != "")
        check("⚠ G-297 CONTROL, the row that makes the one above mean something: with the SAME "
              "fixture reading open the loop does NOT stop — it keeps taking turns until the "
              "fixture forces it out. Without this pair a guard that returned unconditionally "
              "would pass",
              _rcturns(_OPEN)[:2] == (False, 3))
        check("⚠ G-297 FAILS OPEN — runs.csv ABSENT: the loop keeps running. A broken meter must "
              "never stop a healthy loop; this loop is the run's ONLY source of liveness, approval, "
              "context and RAM flags, and silencing it over a missing file costs more than letting "
              "it run one run too long",
              _rcturns(None)[:2] == (False, 3))
        check("G-297 FAILS OPEN — runs.csv UNDECODABLE (not UTF-8): the loop keeps running",
              _rcturns(b"\xff\xfe\x00run-id,state\n")[:2] == (False, 3))
        check("G-297 FAILS OPEN — runs.csv present but SCHEMA-LESS (no run-id/state columns, the "
              "shape the R10 fixture above happens to write): no row matches, the loop keeps running",
              _rcturns("run,status\nrun-7,closed\n")[:2] == (False, 3))
        check("⚠ G-297 THE ROW IS FOUND BY RUN-ID, NOT BY POSITION: a runs.csv whose FIRST row is a "
              "DIFFERENT run reading closed does not stop this loop. A first-row or last-row read "
              "would stop run-7 on run-1's state — every goal's runs.csv accumulates closed rows",
              _rcturns("run-id,type,state\nrun-1,build,closed\nrun-7,build,open,\n")[:2]
              == (False, 3))
        # UNREADABLE, expressed as a DIRECTORY where the file belongs rather than as chmod 000 —
        # a mode-based fixture is a no-op for root and would pass vacuously in a root container.
        rcdir = Path(td) / "runclosed-unreadable"
        (rcdir / "runs" / "run-7").mkdir(parents=True)
        (rcdir / "runs.csv").mkdir()
        check("G-297 FAILS OPEN — runs.csv UNREADABLE (OSError at open): the loop keeps running",
              _rcturns(None, root=rcdir / "runs" / "run-7")[:2] == (False, 3))

        (rcgoal / "notruns" / "run-7").mkdir(parents=True)
        rccsv.write_text(_CLOSED, encoding="utf-8")
        check("⚠ G-297 REFUSES TO GUESS A GOAL (R11, goal_state's discipline at :336): a package "
              "that is not {goal}/runs/run-N resolves NO goal and the loop keeps running — even "
              "though a closed run-7 row sits one directory away. `run-1` exists in EVERY goal, so "
              "a walk that resolved the wrong directory would stop this loop on a STRANGER's state",
              _rcturns(_CLOSED, root=rcgoal / "notruns" / "run-7")[:2] == (False, 3))

    # ---------- 7.112: the ruled ≤30 s cadence — the flag REFUSES, and the loop SLEEPS SECONDS ----
    #
    # ⚠ WHAT THESE ROWS EXIST TO CATCH is not "is 30 expressible" but the SILENT MIGRATION. The old
    # `--loop` was int MINUTES sleeping `loop * 60`; the two obvious fixes both fail without a sound,
    # in OPPOSITE directions (redefine to seconds → surviving `--loop 10` callers mean 10 s, inside
    # the ceiling so nothing alarms; keep minutes + add a flag → those callers keep the superseded
    # 10-minute cadence). So the assertions below are on the REFUSAL and on the ACTUAL SLEEP ARGUMENT,
    # never on the parser's declared metavar — a metavar is a claim about intent, and intent is
    # exactly what was wrong.
    with tempfile.TemporaryDirectory() as td:
        cpkg = Path(td) / "cadence-pkg"
        cpkg.mkdir()

        class _CadStop(Exception):
            """Raised BY THE FIXTURE to escape the loop after one sleep — never by watch_loop."""

        def _raised(fn, *a):
            """The exception `fn(*a)` raised, or None. Absence of a raise is a real result here."""
            try:
                fn(*a)
            except Exception as exc:
                return exc
            return None

        # (1) THE RETIRED FLAG REFUSES, THROUGH main() — the real wiring, not a re-implementation.
        def _main_with(argv):
            """(exit code or None, stderr) for a real main() invocation."""
            real_argv, err = sys.argv, io.StringIO()
            sys.argv = ["watch.py"] + argv
            try:
                with contextlib.redirect_stderr(err):
                    main()
                return None, err.getvalue()
            except SystemExit as exc:
                return exc.code, err.getvalue()
            finally:
                sys.argv = real_argv

        _code, _err = _main_with(["--loop", "10", "--package", str(cpkg)])
        check("⚠ 7.112 (1) THE CRITERION ITSELF — the minute-denominated --loop is RETIRED and "
              "REFUSES: it exits NON-ZERO and NAMES its replacement. Reinterpreting it would be "
              "silent in both directions — `--loop 10` never said whether it meant 10 minutes (the "
              "superseded cadence) or 10 seconds (inside the ceiling, so no alarm fires)",
              _code not in (None, 0) and "RETIRED" in _err and "--loop-forever" in _err
              and "--cadence-s" in _err)
        # ORDERING, PROVED BY WHICH ERROR WINS. `--loop 10` with NO --package would fail either way,
        # so the exit code proves nothing here and the MESSAGE is the whole assertion: the retirement
        # must beat main()'s own "--package is required", which sits immediately after it. That is
        # what makes this a STARTUP refusal rather than a late one.
        #
        # ⚠ NOT WRITTEN AS `--loop 10 --selftest`, WHICH IS WHERE THIS ROW STARTED: with the guard
        # mutated away that argv re-enters cmd_selftest FROM INSIDE cmd_selftest and the suite HANGS
        # instead of failing. A check that hangs under mutation cannot be proven red — it reports
        # nothing at all — so the fixture had to stop calling the thing it runs inside.
        _ncode, _nerr = _main_with(["--loop", "10"])
        check("7.112 (1) the refusal fires BEFORE any other startup work — with --loop present it "
              "wins over main()'s own --package requirement, so a caller can never get as far as a "
              "pass and learn afterwards that its cadence was ignored",
              _ncode not in (None, 0) and "RETIRED" in _nerr and "--package is required" not in _nerr)

        # (2) ≤30 s IS EXPRESSIBLE AND IS WHAT THE LOOP ACTUALLY SLEEPS.
        _slept = []

        def _record_sleep(seconds):
            _slept.append(seconds)
            raise _CadStop

        try:
            watch_loop(argparse.Namespace(cadence_s=30), Path(td) / "no-such-run",
                       do_pass=lambda _a: None, sleep_fn=_record_sleep)
        except _CadStop:
            pass
        check("⚠ 7.112 (4) THE CRITERION ITSELF — 30 SECONDS IS WHAT THE LOOP SLEEPS, exactly, with "
              "no unit arithmetic on the way: asserted on the ARGUMENT sleep actually received, not "
              "on the flag's metavar. Under the old `args.loop * 60` this value slept 30 MINUTES and "
              "no value of the flag could express 30 s at all",
              _slept == [30])

        # (3) THE DEFAULT COMES FROM budget.json, DRIVEN OFF A REAL FILE ON DISK — not from
        # hand-built inputs, which would test the arithmetic and skip the resolution.
        (cpkg / "budget.json").write_text(json.dumps(
            {"cadence": {"watch_loop_max_seconds": 30}}), encoding="utf-8")
        _v, _why = budget_mod.cadence_source(cpkg, None)
        check("⚠ 7.112 (3) the cadence DEFAULT is READ from the run's budget.json "
              "(r-bar-home-is-the-run-budget-json, p-cadence-home-and-catalog-root ASK 2) and the "
              "loop SAYS which value it used and why — a consumer that resolves correctly and prints "
              "nothing fails budget.py's own acceptance",
              _v == 30 and "budget.json" in _why and "watch_loop_max_seconds" in _why)
        # ⚠ BOTH UNDECLARED BRANCHES, AND THE SECOND ONE IS WHY THIS ROW WAS REWRITTEN. It first
        # asserted only the NO-FILE case, and a mutation that made the missing-FIELD branch return a
        # fallback `30` LEFT IT GREEN — the check could not reach the line it was meant to guard.
        # The missing-field case is also the realistic one: a package can easily carry a budget.json
        # with floors and no cadence section. A control that exercises one of two branches is a
        # control over the branch nobody was worried about.
        _nofield = Path(td) / "budget-without-cadence"
        _nofield.mkdir()
        (_nofield / "budget.json").write_text(json.dumps(
            {"floors": {"pressure_warn_mb": 2000}}), encoding="utf-8")
        _badval = Path(td) / "budget-bad-cadence"
        _badval.mkdir()
        (_badval / "budget.json").write_text(json.dumps(
            {"cadence": {"watch_loop_max_seconds": 0}}), encoding="utf-8")
        check("⚠ 7.112 (3) CONTROL — with NO declaration the resolution RAISES rather than choosing a "
              "number, in BOTH undeclared shapes: no budget.json at all, AND a budget.json that "
              "declares other things but no cadence. A default here would be a literal, a literal is "
              "a home, and a second home for a policy number is the defect r-floor-single-source "
              "exists to prevent",
              isinstance(_raised(budget_mod.cadence_source, Path(td), None),
                         budget_mod.CadenceUndeclared)
              and isinstance(_raised(budget_mod.cadence_source, _nofield, None),
                             budget_mod.CadenceUndeclared))
        check("7.112 (3) CONTROL — a cadence that is declared but NOT a positive integer is UNREADABLE "
              "and loud, never silently treated as absent: failing to read a declaration and having "
              "none are different facts, and collapsing them is how a wrong path once looked exactly "
              "like a package with no budget",
              isinstance(_raised(budget_mod.cadence_source, _badval, None),
                         budget_mod.CadenceUnreadable))
        _vo, _whyo = budget_mod.cadence_source(cpkg, 60)
        check("⚠ 7.112 an override ABOVE the declared ceiling is announced as a BREACH, not as a "
              "disagreement — a cadence is a MAXIMUM, so larger is the one direction that violates "
              "the ruling. This is r-watch-loop-30s's own interim 60 s overshoot: disclosed loudly, "
              "never silently clamped and never silently obeyed",
              _vo == 60 and "BREACH" in _whyo.upper() and "30" in _whyo)

        # (4) THE HEARTBEAT'S LEGACY MINUTE FIELD SURVIVES, ROUNDED UP. This guards coord.py's two
        # readers, which this task does NOT hold: with `loop_min` absent or non-int BOTH fall through
        # to a flat 30-MINUTE staleness and `coordinate workers` prints a live loop as "one-shot".
        check("⚠ 7.112 the heartbeat still carries loop_min for coord.py's two readers, CEILED to "
              "whole minutes and never below 1 — a 30 s cadence must not round to 0 and re-enter the "
              "falsy-zero fallback this exists to avoid",
              _loop_min_compat(30) == 1 and _loop_min_compat(60) == 1
              and _loop_min_compat(90) == 2 and _loop_min_compat(600) == 10)
        check("7.112 loop_min is None exactly when there is no cadence — a one-shot pass reports no "
              "interval rather than a fabricated one",
              _loop_min_compat(None) is None and _loop_min_compat(0) is None
              and _loop_min_compat(True) is None)

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


def watch_loop(args, run_root, do_pass=None, sleep_fn=None):
    """The `--loop-forever` body — and the ONE place this loop decides whether to take another turn.

    EXTRACTED FROM main() SO A CHECK CAN DRIVE IT, and that is the whole reason it is a function:
    the criterion is that THE LOOP exits on a closed run, and a check on run_closed() alone would
    stay green with the guard deleted from the loop. A green that cannot go red is not evidence
    (conduct §9) — and this defect's own history is a builder's green guarding a builder's
    assumption, so the seam is placed where the mutation has to be observable.

    `do_pass` / `sleep_fn` are the fixture's only injection points and default to the real ones.
    """
    do_pass = run_pass if do_pass is None else do_pass
    sleep_fn = time.sleep if sleep_fn is None else sleep_fn
    while True:
        if run_closed(run_root):
            print(RUN_CLOSED_LINE, flush=True)
            return 0
        do_pass(args)
        # SECONDS, AS RESOLVED. No `* 60` and no unit arithmetic anywhere on this path: the flag
        # carries its unit in its name, `budget.json` declares the same unit, and the one conversion
        # that survives (to the heartbeat's minute-denominated field) happens at that field's writer
        # where its lossiness is visible. A cadence multiplied in the sleep call is how 30 s became
        # unreachable in the first place.
        sleep_fn(args.cadence_s)


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
    # ⚠ RETIRED, AND REGISTERED SO IT CAN REFUSE — task 7.112, ruling `r-watch-loop-30s`.
    #
    # NO `type=` AND NO `metavar`, DELIBERATELY: this flag must reach the refusal below whatever was
    # passed to it. With `type=int` a stale `--loop abc` would die on a type error instead of the
    # retirement message, and the caller would never learn what replaced it.
    #
    # WHY A REFUSAL AND NOT A REINTERPRETATION. `--loop` was int MINUTES sleeping `loop * 60`, so the
    # ruled 30 s was unreachable at any value. Both silent migrations fail, in OPPOSITE directions:
    # redefine `--loop` to seconds and the surviving `--loop 10` callers mean 10 s — INSIDE the
    # ceiling, so no policy alarm fires while the sensor's real load triples unrecorded; keep minutes
    # beside a new sub-minute flag and those same callers keep the SUPERSEDED 10-minute cadence
    # exactly where the self-heal path runs. A refusal converts an invisible wrong cadence into a
    # loud startup failure, which is the only one of the three a human finds out about.
    p.add_argument("--loop", default=None,
                   help="RETIRED (r-watch-loop-30s). Use --loop-forever, and --cadence-s to "
                        "override the interval. Passing this REFUSES rather than guessing which "
                        "unit you meant")
    # THE MODE SWITCH CARRIES NO NUMBER, and that is the point: `spawn-profiles.yaml` reproduces the
    # sensor's invocation, and an argv holding a cadence value is a second home that drifts silently
    # because nothing consumes it (that file's own G-42 argument, made for the floor). A recovery
    # path that holds no number cannot resurrect a weaker sensor than the one that died.
    p.add_argument("--loop-forever", action="store_true",
                   help="repeat forever at the run's declared cadence (the watcher seat's mode)")
    p.add_argument("--cadence-s", type=int, metavar="SEC", default=None,
                   help="DELIBERATE OPERATOR OVERRIDE of the loop interval, in SECONDS. Default: "
                        "the run's budget.json cadence.watch_loop_max_seconds "
                        "(r-bar-home-is-the-run-budget-json). The loop reports which value it used "
                        "and why")
    p.add_argument("--claude-projects-dir", help="override ~/.claude/projects (testing only)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    # ⚠ FIRST, BEFORE --selftest AND BEFORE ANY WORK. A retired policy flag must refuse at STARTUP:
    # a caller that gets a pass done and only later learns its cadence was ignored has already been
    # told the room is watched at a rate nobody agreed to.
    if args.loop is not None:
        p.error("--loop is RETIRED (owner ruling r-watch-loop-30s, 2026-07-30): it was integer "
                "MINUTES and the ruled cadence is 30 SECONDS MAXIMUM, which no value of it could "
                "express. It is REFUSED rather than reinterpreted, because `--loop 10` does not say "
                "whether you meant 10 minutes (the superseded cadence) or 10 seconds, and guessing "
                "either way is silent.\n"
                "  Replace it with:  --loop-forever            (loop at the run's declared cadence)\n"
                "                    --loop-forever --cadence-s SEC   (deliberate operator override)\n"
                "  The cadence's one home is the run's budget.json cadence.watch_loop_max_seconds.")
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
    if args.loop_forever:
        # ⚠ RESOLVED ONLY ON THE LOOPING PATH, and the asymmetry with the floor above is deliberate.
        # A ONE-SHOT pass has no interval to be wrong about, so making an absent cadence fatal there
        # would brick every package without a budget.json for a number that pass never uses. A LOOP
        # cannot choose its own interval without becoming that interval's second home, so for the
        # loop an absent declaration IS fatal — same shape as the floor, different trigger.
        try:
            args.cadence_s, cadence_why = budget_mod.cadence_source(run_root, args.cadence_s)
        except (budget_mod.CadenceUndeclared, budget_mod.CadenceUnreadable) as exc:
            print("watch: REFUSING TO LOOP — %s\n"
                  "  The cadence's one home is the run's budget.json "
                  "(r-bar-home-is-the-run-budget-json, p-cadence-home-and-catalog-root ASK 2). This "
                  "loop will not invent an interval: a sensor running at a made-up cadence reports "
                  "staleness and latency against a rate nobody ruled.\n"
                  "  Declare cadence.watch_loop_max_seconds there, or pass --cadence-s to override "
                  "deliberately." % exc, file=sys.stderr)
            sys.exit(2)
        print("watch: cadence %s" % cadence_why, file=sys.stderr)
        # G-297: `run_root` is already resolved above for the floor read, and it IS the run package
        # — so the run-closed guard costs no second derivation of it (PRIN-11).
        watch_loop(args, run_root)
    else:
        run_pass(args)


if __name__ == "__main__":
    main()
