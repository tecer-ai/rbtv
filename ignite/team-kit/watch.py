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


# ---------- one pass ----------

def run_pass(args):
    base = coord.base_dir(args)
    _, _, rows = coord.load_workers(base)
    seats = {w["agent"]: w for w in coord.discover_workers(coord.workers_dir(args))}
    state = load_state(base)
    live = live_panes()
    nnow = now_dt()
    report, notes = [], []

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
    stamp = nnow.strftime("%Y-%m-%d %H:%M")
    print(f"watch pass {stamp} — {len(report)} active seat(s), {len(notes)} new flag(s)")
    for line in report:
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

    global pane_tail, live_panes, pane_cwd
    coord.wake = lambda pane, text: (False, "stub")
    # coord's identity resolution (T1) reads the calling pane: stub it, or a selftest run from
    # inside a tmux pane would talk to the real server and could inherit a live seat's identity.
    coord.detect_pane = lambda override=None: (override or "")
    coord_env_agent = os.environ.pop("COORD_AGENT", None)
    tails = {}
    pane_tail = lambda pane: tails.get(pane)
    live_panes = lambda: {"%1", "%2", "%3", "%4", "%5", "%6", "%7"}
    pane_cwds = {}
    pane_cwd = lambda pane: pane_cwds.get(pane)
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
                 "inactive_min": 30, "context_pct": 50, "claude_projects_dir": str(Path(td) / "projects")}
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
