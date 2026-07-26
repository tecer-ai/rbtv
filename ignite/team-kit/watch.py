#!/usr/bin/env python3
"""watch — deterministic liveness + context monitor for team-kit runs.

The watcher seat's tool (deterministic-first: the SCRIPT measures, the watcher agent only runs
it and relays judgment). One pass checks every ACTIVE roster seat and reports:

  liveness   registered pane still exists (a DEAD pane means wakes cannot reach the seat)
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
             below --mem-floor-mb (default 500) or 1-min load at/over cores x --load-per-core
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
With --notify each crossing sends ONE coordination `ask` to leader (via coord.py, so it is
logged and wakes the pane) telling it exactly what to run — e.g. `close <agent> --renew` at the
context threshold. A crossing re-arms only when the condition clears (activity resumes / the
seat's pane changes, i.e. it was renewed).

  python3 watch.py --package <abs-run-package> [--notify] [--loop 10]

State: <package>/coordination/watch-state.json (script-managed). Transcript matching: the seat's
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

def load_state(base):
    p = base / "watch-state.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_state(base, state):
    coord.atomic_write(base / "watch-state.json", json.dumps(state, indent=1))


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


def save_heartbeat(base, loop_min):
    """P32 — stamp this pass so something outside the loop can tell a live watcher from a dead one.

    A SEPARATE file from watch-state.json on purpose: that file is keyed by agent name, and a
    reserved key inside it would be one roster name away from a collision. Failure is swallowed —
    a heartbeat that cannot be written must never take the watcher down with it (the same
    read-only-package tolerance coord's cursor persistence has)."""
    try:
        coord.atomic_write(base / "watch-heartbeat.json", json.dumps(
            {"last_pass": now_dt().isoformat(timespec="seconds"),
             "loop_min": loop_min, "pid": os.getpid()}, indent=1))
    except OSError as exc:
        print(f"watch: heartbeat not written ({exc}) — `coordinate workers` will report this "
              f"watcher STALE even while it runs", file=sys.stderr)


# ---------- notification ----------

def notify_leader(args, text):
    """Send one flag to leader through coord (so it is logged AND wakes the pane).

    `agent="watcher"` is coord's internal identity API — the `--as` equivalent (the watcher loop
    runs outside any pane, so no identity contradiction can fire). A refusal inside coord exits
    the process; the loop must survive it, so SystemExit is caught and reported."""
    ns = argparse.Namespace(package=getattr(args, "package", None), base=getattr(args, "base", None),
                            workers_dir=getattr(args, "workers_dir", None),
                            agent="watcher", as_agent=None, to="leader", message=text,
                            type="ask", supersedes=None, re_num=None, file=None, force=False)
    try:
        coord.cmd_send(ns)
    except SystemExit as exc:
        print(f"watch: leader notification refused by coord (exit {exc.code}) — flag not sent: "
              f"{text[:80]}", file=sys.stderr)


# ---------- system + leftover-window checks ----------

def check_system(args, sysstate, notes):
    """PROP-9 — system memory/load as a first-class duty of the loop: the run's stuck-process
    pile-up OOM-killed the WATCHER itself, and nothing had the instrumentation to see the
    pressure building. Flags once per episode; re-arms only when the pressure clears — the same
    discipline as every other crossing. Returns the report line, or None where unmeasurable."""
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
        if not sysstate.get("notified_pressure"):
            notes.append(
                f"watch: SYSTEM PRESSURE — {sp['avail_mb']}MB RAM available (floor {floor}MB), "
                f"load {sp['load1']}/{sp['cores']} cores. An OOM cascade kills seats AND this "
                f"watcher itself. Free the box NOW: accelerate close-out of idle/done seats, "
                f"tear down leftover dead wave windows (tmux kill-window), and pause further "
                f"launches until this clears.")
            sysstate["notified_pressure"] = True
    else:
        sysstate.pop("notified_pressure", None)
    return (f"{'system':<18} {'FLAG' if flags else 'ok':<7} ram={sp['avail_mb']}MB "
            f"load={sp['load1']}/{sp['cores']}  {' '.join(flags)}")


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
    state = load_state(base)
    live = live_panes()
    nnow = now_dt()
    report, notes = [], []

    # PROP-9/PROP-10: box-level duties run FIRST — pressure explains per-seat symptoms, and a
    # leftover dead window is invisible to the per-seat loop (its seats have no active row).
    sysstate = load_sys_state(base)
    sysline = check_system(args, sysstate, notes)
    leftover_lines = check_leftover_windows(rows, seats, sysstate, notes)

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
                notes.append(f"watch: '{agent}' is ACTIVE in the roster but its pane {pane} is gone "
                             f"— wakes cannot reach it. Mark it closed ({coord.coord_invocation(args)} "
                             f"close-seat {agent} --no-export) or relaunch it.")
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
                notes.append(f"watch: '{agent}' ({harness}) is parked on an interactive approval "
                             f"prompt — its pane is frozen until someone answers it, and a wake "
                             f"typed into it would land in the modal. Inspect it "
                             f"(tmux capture-pane -p -t {pane}) and clear it: "
                             f"{coord.coord_invocation(args)} approve {agent}")
                st["notified_approval"] = True
        else:
            st.pop("notified_approval", None)
        if inact_min is not None and inact_min >= args.inactive_min:
            flags.append(f"INACTIVE {inact_min}min")
            if not st.get("notified_inactive"):
                notes.append(f"watch: '{agent}' has shown no pane activity for {inact_min} min "
                             f"(threshold {args.inactive_min}). Check on it; if hung or done-but-"
                             f"stuck, close it — or renew: {coord.coord_invocation(args)} close {agent} --renew")
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
                notes.append(f"watch: '{agent}' context is at {pct}% (threshold {threshold}%"
                             f"{source}). Have the closer close and RENEW it now: "
                             f"{coord.coord_invocation(args)} close {agent} --renew "
                             f"(memory.md gets written, the seat relaunches fresh).")
                st["notified_context"] = True

        ctx = f" ctx={pct}%" if pct is not None else ""
        act = f" idle={inact_min}min" if inact_min is not None else ""
        report.append(f"{agent:<18} {'FLAG' if flags else 'ok':<7} {harness:<9}{ctx}{act}"
                      f"  {' '.join(flags)}")
        state[agent] = st

    save_state(base, state)
    save_sys_state(base, sysstate)
    save_heartbeat(base, getattr(args, "loop", None))
    stamp = nnow.strftime("%Y-%m-%d %H:%M")
    print(f"watch pass {stamp} — {len(report)} active seat(s), {len(notes)} new flag(s)")
    if sysline:
        print("  " + sysline)
    for line in report:
        print("  " + line)
    for line in leftover_lines:
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
        check("notify: flags land in the coordination log as watcher->leader asks",
              "from: watcher | to: leader | type: ask" in raw)

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
    p.add_argument("--mem-floor-mb", type=int, default=500, help="flag SYSTEM PRESSURE when available RAM drops below this many MB (default 500; PROP-9)")
    p.add_argument("--load-per-core", type=float, default=1.0, help="flag SYSTEM PRESSURE when 1-min load reaches cores x this factor (default 1.0; PROP-9)")
    p.add_argument("--notify", action="store_true", help="send each new flag to leader as a coordination ask (default: print only)")
    p.add_argument("--loop", type=int, metavar="MIN", help="repeat forever every MIN minutes (the watcher seat's mode)")
    p.add_argument("--claude-projects-dir", help="override ~/.claude/projects (testing only)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args()
    if args.selftest:
        cmd_selftest()
        return
    if not (args.package or args.base or os.environ.get("COORD_PACKAGE")):
        p.error("--package is required (or COORD_PACKAGE)")
    if args.loop:
        while True:
            run_pass(args)
            time.sleep(args.loop * 60)
    else:
        run_pass(args)


if __name__ == "__main__":
    main()
