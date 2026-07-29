#!/usr/bin/env python3
"""probe-lifecycle-exec.py — kill the CALLER mid-command, and prove the detached executor did not
die with it.

WHAT IS UNDER TEST (task `s3-11`; spec `stage-3-executor-spec.md` §6(a), §3.1's ordering clause):

  `s3-09` landed the caller-side fork (`fork_lifecycle_renewal`, coord.py) and stated in as many
  words that ALL of its acceptance rows assert on a STUBBED `Popen`. So the REAL-PROCESS half is
  this file's and nobody else's:

    · an actually-forked, actually-detached child SURVIVES its caller's death, opens its own log
      and completes the whole disposition sequence out of pane;
    · the KILL-MID-COMMAND WINDOW itself — the caller is SIGKILLed while it is still running, and
      the proof of that is its wait status (`-SIGKILL`), never an assumption about timing;
    · a REAL `tmux respawn-pane -k`, a REAL `verify_pids_gone`, a REAL `pane_harness_idents`, a
      REAL `wait_harness_up`;
    · the settle wait at its REAL budget (`LIFECYCLE_SETTLE_S`), which the selftest zeroes;
    · the RAM gate's VERDICT (the selftest stubs `available_mb` to 0, where `memory_gate` PASSES
      by its own fail-safe — so no RAM-gate row can be scored there at all).

  The exit contract of `lifecycle-exec` is load-bearing and is asserted, not assumed: 2 = a GUARD
  refused, 3 = the guards passed and the SEQUENCE broke, 0 = it completed.

WHY A PROBE AND NOT A SELFTEST CASE. `_selftest_checks` globally rebinds, for the whole suite,
`wake`, `tmux_kill_pane`, `tmux_respawn_pane`, `tmux_capture`, `pane_harness_idents`,
`pane_harness_pids`, `wait_harness_up`, `verify_pids_gone`, `arm_pid_reaper`, `tmux_pane_pid`,
`available_mb`, `live_panes`, `detect_pane`, `atomic_write`, `session_close` and more, and zeroes
`NATIVE_ID_WAIT` and `LIFECYCLE_SETTLE_S`. Every one of those is a function this acceptance must
exercise FOR REAL: a stubbed suite cannot tell "the executor worked" from "the stub returned
success", which is the vacuous-guard family the suite's own comments already name. The stubs exist
for a ruled reason and are NOT touched here (`s3-11` § Out of scope).

⚠⚠ THE MEASURED FIXTURE HAZARD, and why this file builds NO fixture of its own. tmux starts each
pane's shell as a LOGIN shell, which prepends `$HOME/.local/bin` — where the REAL Claude Code
harness lives — AHEAD of any stub directory a fixture puts on PATH. A stub-on-PATH fixture that
does not ALSO redirect `HOME` launches a REAL harness while every check stays green; that is
measured (`acceptance-room.py` module docstring, 2026-07-29), and the "no model, no cost" bar was
silently FALSE for two runs before it was caught. `AcceptanceRoom` (`probes/acceptance-room.py`,
landed by `s4-09`) already redirects `HOME`, already runs on a PRIVATE tmux server reached by a
private `TMUX_TMPDIR` (not by `-L`, measured non-isolating for the context sensor), and already
ASSERTS stub provenance with a proven red arm. This probe INHERITS that defence rather than
reinventing it (`role.md` §1). What it adds is a subclass that changes exactly two things the
renewal path refuses without — see `ProbeRoom` — and nothing else.

DISCLOSED SUBSTITUTIONS AND SKIPS (R-6 — an unrun arm reported as absent is the honest form; each
one is measured, not asserted):

  1. ARM 1's "roster shows the seat ACTIVE again on a NEW pane" is FALSE BY CONSTRUCTION and is
     substituted. (a) NOTHING on the launch path writes a roster row — the successor's own
     `checkin` does, minutes later — so `run_lifecycle_sequence` step 6 asserts the NEGATIVE
     invariant instead ("no ACTIVE row pointing at a pane that is no longer the seat's"), and the
     marker records `no active row — the successor writes its own at checkin`. (b) A seat whose
     descriptor names no `window:` is PANE-placed, so `renew_in_place` is TRUE and G-12 respawns
     the SAME pane id on purpose — a NEW pane id would be the defect. SUBSTITUTED with what is
     actually checkable and actually discriminating: the successor is a NEW HARNESS PROCESS (a
     different pid+starttime from the outgoing one), it is running from THIS ROOM'S OWN BIN, and
     the outgoing process is GONE.
  2. ARM 2's hook is `awaiting-close.json`, not "poll for the caller pid, kill on first sight".
     Killing on first sight of the pid kills BEFORE the checkout body runs, so the degraded
     contract that arm asserts — "checked out, debt standing, no successor, no marker" — could
     never be reached: the seat would not be checked out at all. The awaiting-close record is the
     LAST thing written before the fork, so hooking on it lands the kill exactly in the
     after-checkout/before-fork window §3.1 names.
  3. ARM 4 disables the fork by planting a `setsid` STUB on the room's PATH, not by editing
     `coord.py`. The fork argv is `["setsid", sys.executable, <coord.py>, "lifecycle-exec", …]`
     and `Popen` resolves `setsid` through PATH, so a stub that exits 0 without exec'ing leaves
     the caller believing it forked while NO executor ever runs. That is the mutation the task
     asks for, applied at one point, reversible, and it writes nothing into the repo — `coord.py`
     is under console custody this window (R-9) and this probe never touches it (its md5 is
     asserted unchanged across the whole run).
  4. `verify_pids_gone`'s SURVIVOR branch and `arm_pid_reaper` are NOT exercised here and are
     reported as not exercised. A survivor means a process that outlived SIGKILL, which no stub
     can be made to do; the escalation branch and the reaper were fired for real, at real live
     processes, by `probes/probe-lifecycle-idents.py` (`s3-12`, rows 1.5-1.7 and its two red
     arms). Duplicating them here would be a second implementation of a proof that exists.
  5. The kernel-level recycled-pid arm is `s3-12`'s and is not repeated.

RUN IT (`--go` IS MANDATORY — this probe REFUSES to run unattended; see the guard block in
`main()` for the ruling and the measurement behind it):

         cd /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/ignite/team-kit
         python3 -u probes/probe-lifecycle-exec.py --go

A bare invocation prints the refusal and exits 2 in well under a second.

Exit 0 = every arm passed. Exit 1 = a property is broken. Exit 2 = the probe could not run (never
a pass: a probe that cannot execute has proven nothing, and reporting that as green is the very
absence-reads-as-health shape under test; a red arm that failed to go red is the same refusal,
because its green partner is then vacuous).

Runtime ~4 min. The dominant terms are REAL: one renewal end-to-end per arm, the settle wait at
its full `LIFECYCLE_SETTLE_S` budget once, and the RAM gate's full retry schedule once
(`LIFECYCLE_MEM_RETRIES` x `LIFECYCLE_MEM_RETRY_S`). The end-to-end renewal wall clock is PRINTED
— it is the input `s3-14` uses to decide whether `LIFECYCLE_STALE_MIN = 10` is several times too
generous.

Self-invocation modes (used by the probe's own controls, not by a human — each is sub-second,
opens no room, and therefore needs no `--go`):
  --preflight    : run only the preflight, exit 0/2. Exercised with tmux removed from PATH to
                   prove the exit-2 path is real.
  --stub-scan    : report whether the three real-function names are the shipped ones.
  --plant-stub   : with --stub-scan, monkeypatch one of them first — the red arm.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

# ---- guard 1, on ourselves: a probe dispatched from inside a pane inherits that pane otherwise,
# and every tmux command that names no target would then act on the DISPATCHER'S live pane.
for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
COORD_PY = KIT / "coord.py"
ROOM_PY = HERE / "acceptance-room.py"

# The model the stub harness is launched with. NOT cosmetic: `validate_seat` refuses a claude seat
# whose model is neither a known alias nor a full `claude-*` id, and `acceptance-room`'s own
# `stub-model` is refused there — measured, the relaunch failed with exactly that text. The stub
# ignores every flag, so the name costs nothing and buys a launchable descriptor.
STUB_MODEL = "haiku"
HANDOFF = "s3-11 probe handoff: the successor exists only to prove this block was written."

FAILED, PASSED, REDS, NOTES = [], [], [], []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    return bool(ok)


def red(name, went_red, detail=""):
    """A RED ARM. `went_red` True means the deliberately broken variant WAS rejected. A red arm
    that stays green makes its green partner vacuous, so it is recorded as a FAILURE."""
    REDS.append((name, bool(went_red)))
    (PASSED if went_red else FAILED).append("RED ARM: " + name)
    print(f"  {'RED ' if went_red else 'FAIL'}  red arm: {name}" + (f" — {detail}" if detail else ""))
    return bool(went_red)


def note(text):
    NOTES.append(text)
    print(f"  note  {text}")


class ProbeRefusal(RuntimeError):
    """The probe refusing to act. Loud by construction (R-8) — never swallowed into a warning."""


# =================================================================================================
# THE ROOM. Inherited, not rebuilt (`role.md` §1). Two overrides, each forced by a REFUSAL the
# renewal path issues against the stock room, each measured before it was written:
#
#   `model:` -> a launchable alias. `validate_seat` refuses `stub-model` and the relaunch FAILED
#              with "claude model 'stub-model' is neither a known alias … nor a full claude-* id".
#              `taskforce.csv` carries the same value because `check_bindings` (G-51) compares the
#              descriptor against the registry BEFORE any kill and refuses a divergence.
#   `memory.md` -> created. `checkout --renew --handoff` appends the handoff block into the seat
#              folder's `memory.md`; that append IS the artifact the renewal exists to carry.
#
# Everything else — the private tmux server, the HOME redirect, the stub bin, the stub provenance
# assertion, the teardown, the leak scan — is the room's and is used as it ships.
# =================================================================================================
def load_room_module():
    if not ROOM_PY.exists():
        raise ProbeRefusal(f"the acceptance substrate is missing: {ROOM_PY}")
    spec = importlib.util.spec_from_file_location("acceptance_room", str(ROOM_PY))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


AR = None                                   # set in main(), after the preflight


def make_room_class(ar):
    class ProbeRoom(ar.AcceptanceRoom):
        def _write_descriptor(self, s):
            d = self.pkg / "seats" / s["seat"]
            d.mkdir(parents=True, exist_ok=True)
            fm = [f"seat: {s['seat']}",
                  "description: s3-11 probe seat (stub harness — no model, no cost)",
                  f"cwd: {d}",
                  f"harness: {s['harness']}",
                  f"model: {STUB_MODEL}",
                  "effort: medium",
                  "agent_type: worker",
                  "ctx-refresh: 40"]
            if s.get("mode") is not None:
                fm.append(f"mode: {s['mode']}")
            (d / "seat.md").write_text("---\n" + "\n".join(fm) + "\n---\n\n"
                                       "Stub seat. No agent ever reads this.\n", encoding="utf-8")
            (d / "memory.md").write_text(f"# memory — {s['seat']}\n\n", encoding="utf-8")

        def setup(self):
            super().setup()
            rows = ["taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id"]
            for s in self.seats:
                rows.append(f"tf-acc,{s['seat']},,{s['harness']},{STUB_MODEL},medium,40,acc")
            (self.pkg / "taskforce.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
            return self

    return ProbeRoom


# =================================================================================================
# ISOLATION — asserted before anything is opened, and able to REFUSE (acceptance 3).
# =================================================================================================
def assert_private_socket(env, room):
    """REFUSE unless this environment can only reach THIS ROOM'S OWN tmux server.

    Not a formality. `recover-room.py:13-19` measured what an unset target does: with `TMUX` and
    `TMUX_PANE` unset, tmux resolves an EMPTY target to the MOST RECENT session — which answered
    `build-core-daemon-mvp`, the LIVE room. Under a private `TMUX_TMPDIR` a bare `tmux` can only
    reach a socket inside this room's own directory; without it, every bare tmux call in this
    probe's blast radius lands on the default socket, where the owner's console and a live daemon
    live."""
    tt = env.get("TMUX_TMPDIR", "")
    if not tt:
        raise ProbeRefusal(
            "REFUSING TO START: this environment carries NO TMUX_TMPDIR, so every tmux command it "
            "runs reaches the DEFAULT socket — the live room. A probe that opens panes there is "
            "worse than a probe that does not run.")
    resolved = Path(tt).resolve()
    if not str(resolved).startswith(str(room.tmp.resolve()) + os.sep):
        raise ProbeRefusal(
            f"REFUSING TO START: TMUX_TMPDIR is {resolved}, which is NOT inside this room's own "
            f"tree {room.tmp}. The socket it names is not this room's, and the sessions this probe "
            f"kills would not be this probe's either.")
    for v in ("TMUX", "TMUX_PANE"):
        if env.get(v):
            raise ProbeRefusal(
                f"REFUSING TO START: {v} survives in the environment, so an inherited pane is the "
                f"default target of anything that names none.")
    return True


# =================================================================================================
# REAL-PROCESS READINGS. Taken by this probe, independently of anything coord.py reports, so a
# stubbed reader inside coord could not manufacture a match.
# =================================================================================================
def starttime(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
        return stat[stat.rfind(")") + 1:].split()[19]
    except (OSError, ValueError, IndexError):
        return ""


def alive(pid):
    return bool(pid) and Path(f"/proc/{pid}").exists() and starttime(pid) != ""


def pane_harness(room, pane, harness="claude"):
    """(pid, starttime, argv) of the harness running under `pane`, read from /proc by THIS process.

    The pane runs a shell and the harness is its child — the shape `coord.py`'s own launch
    produces and the shape `pane_harness_idents` reads. Reading it here independently is what makes
    the comparison against the marker's `successor-alive:` entry evidence rather than an echo."""
    root = int(room.tmux("list-panes", "-t", pane, "-F", "#{pane_pid}").stdout.strip())
    rows = subprocess.run(["ps", "-eo", "pid=,ppid=,comm=,args="],
                          capture_output=True, text=True, timeout=30).stdout.splitlines()
    for ln in rows:
        parts = ln.split(None, 3)
        if len(parts) < 4 or not parts[0].isdigit():
            continue
        if int(parts[1]) == root and parts[2] == harness:
            pid = int(parts[0])
            return pid, starttime(pid), parts[3]
    return None, "", ""


def marker(room, seat):
    p = room.pkg / "coordination" / "lifecycle-inflight.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8")).get(seat) or {}
    except (ValueError, OSError):
        return {}


def awaiting(room, seat):
    p = room.pkg / "coordination" / "awaiting-close.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8")).get(seat)
    except (ValueError, OSError):
        return None


def roster_row(room, seat):
    text = (room.pkg / "coordination" / "workers.md").read_text(encoding="utf-8")
    for ln in reversed(text.splitlines()):
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 3 and cells[0] == seat:
            return {"active": cells[1], "pane": cells[2]}
    return None


def exec_logs(room, seat):
    return sorted((room.pkg / "coordination").glob(f"lifecycle-exec-{seat}-*.log"))


def steps(mk):
    return [str(s) for s in (mk.get("steps-completed") or [])]


def step_starting(mk, prefix):
    return next((s for s in steps(mk) if s.startswith(prefix)), "")


# =================================================================================================
# THE CALLER, AND THE KILL.
# =================================================================================================
def hook_fired(room, seat, hook):
    if hook == "marker":
        return bool(marker(room, seat))
    if hook == "awaiting":
        return awaiting(room, seat) is not None
    return False


def run_caller(room, seat, renew, hook, timeout=240):
    """Run `coordinate checkout [--renew --handoff …]` as a REAL process and SIGKILL it the instant
    `hook` fires. Returns the evidence, never a verdict.

    `killed_while_alive` is read from /proc IMMEDIATELY BEFORE the signal, and `rc` is the wait
    status: a caller that died by our SIGKILL reports -9, one that finished on its own reports 0.
    That pair is what turns "we killed it mid-command" from a claim about timing into a
    measurement — no assertion here rests on the poll having been fast enough."""
    argv = [sys.executable, str(COORD_PY), "--package", str(room.pkg), "checkout"]
    if renew:
        argv += ["--renew", "--handoff", HANDOFF]
    env = room.env({"COORD_AGENT": seat})
    assert_private_socket(env, room)
    t0 = time.monotonic()
    proc = subprocess.Popen(argv, cwd=str(KIT), env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    killed_while_alive, kill_at = None, None
    if hook:
        deadline = time.time() + 120
        while time.time() < deadline:
            if hook_fired(room, seat, hook):
                killed_while_alive = alive(proc.pid)
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                kill_at = time.monotonic() - t0
                break
            if proc.poll() is not None:
                break
            time.sleep(0.002)
    out, err = proc.communicate(timeout=timeout)
    return {"rc": proc.returncode, "out": out, "err": err, "pid": proc.pid,
            "killed_while_alive": killed_while_alive, "kill_at": kill_at,
            "t0": t0, "argv": argv}


def wait_terminal(room, seat, timeout=240):
    """Wait for the marker to leave `in-flight`. Returns (marker, seconds)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        mk = marker(room, seat)
        if mk and mk.get("state") in ("done", "FAILED"):
            return mk, time.monotonic() - t0
        time.sleep(0.1)
    return marker(room, seat), time.monotonic() - t0


# =================================================================================================
# ARM 1's ASSERTION SET — one function, so ARM 4 can run the SAME assertions against the mutant and
# require them to FAIL. An arm whose red variant is scored by a different, weaker set proves
# nothing about the green one.
# =================================================================================================
def score_arm1(room, seat, res, mk, old, new):
    """[(name, ok, detail)] — never prints, never records. The caller decides what a failure means."""
    st = steps(mk)
    tpath = step_starting(mk, "transcript-verified:")[len("transcript-verified:"):].split(" (")[0]
    succ = step_starting(mk, "successor-alive:")[len("successor-alive:"):]
    rows = [
        ("the caller was SIGKILLed WHILE RUNNING (wait status -9), not left to finish",
         res["rc"] == -signal.SIGKILL and res["killed_while_alive"] is True,
         f"rc={res['rc']} alive-at-signal={res['killed_while_alive']} "
         f"t+{(res['kill_at'] or 0) * 1000:.0f}ms"),
        ("a DETACHED executor really started — the marker carries an executor (pid, starttime) "
         "the child wrote itself",
         bool((mk.get("executor") or {}).get("pid")) and bool((mk.get("executor") or {}).get("starttime")),
         json.dumps(mk.get("executor"))),
        ("the executor OPENED ITS OWN LOG and wrote to it (evidence, never the alarm)",
         bool(exec_logs(room, seat)) and exec_logs(room, seat)[0].stat().st_size > 0,
         (exec_logs(room, seat)[0].name if exec_logs(room, seat) else "(no log)")),
        ("the sequence COMPLETED out of pane: marker state `done`, no failure text",
         mk.get("state") == "done" and not mk.get("failure"),
         f"state={mk.get('state')!r} failure={mk.get('failure')!r}"),
        ("steps cover the respawn, the relaunch and ALL THREE verifications",
         bool(step_starting(mk, "respawned-in-place:") or step_starting(mk, "killed:"))
         and bool(step_starting(mk, "relaunched:"))
         and bool(step_starting(mk, "roster-verified:"))
         and bool(step_starting(mk, "transcript-verified:"))
         and bool(succ),
         " | ".join(st)),
        ("the OUTGOING harness process is GONE — `verify_pids_gone` ran on real idents",
         old[0] is not None and not alive(old[0]),
         f"outgoing pid {old[0]} starttime {old[1]}"),
        ("a NEW harness process is running for the seat (substituted for 'ACTIVE on a NEW pane' — "
         "see the header: nothing on the launch path writes a roster row, and a PANE-placed seat "
         "respawns the SAME pane by G-12)",
         new[0] is not None and new[0] != old[0] and alive(new[0]),
         f"successor pid {new[0]} starttime {new[1]}"),
        ("the successor is THIS ROOM'S STUB — no model, no cost, asserted rather than assumed",
         bool(new[2]) and str(room.bin) in new[2], (new[2] or "")[:90]),
        ("the marker's `successor-alive:` matches THIS PROBE'S OWN /proc reading — so "
         "`pane_harness_idents` really ran (a stub could not manufacture the match)",
         succ == f"{new[0]}:{new[1]}", f"marker={succ!r} probe={new[0]}:{new[1]}"),
        ("the transcript exists and POST-DATES the checkout",
         bool(tpath) and Path(tpath).exists()
         and Path(tpath).stat().st_mtime >= res["wall_t0"],
         tpath or "(none recorded)"),
        ("NO awaiting-close entry survives for the seat — the debt the checkout opened is settled",
         awaiting(room, seat) is None, json.dumps(awaiting(room, seat))),
        ("the roster does NOT carry an ACTIVE row for the seat (the G-11 invariant step 6 checks; "
         "the successor writes its own row at its check-in)",
         (roster_row(room, seat) or {}).get("active") == "no",
         json.dumps(roster_row(room, seat))),
    ]
    return rows


# =================================================================================================
# SELF-INVOCATION MODES — the probe's own controls.
# =================================================================================================
def preflight():
    """Everything that must be true before a single pane is opened. Exit 2 when it is not."""
    problems = []
    if not shutil.which("tmux"):
        problems.append("no `tmux` on PATH")
    if not shutil.which("setsid"):
        problems.append("no `setsid` on PATH (the fork's argv[0])")
    if not COORD_PY.exists():
        problems.append(f"no coord.py at {COORD_PY}")
    if not ROOM_PY.exists():
        problems.append(f"no acceptance substrate at {ROOM_PY}")
    if not Path("/bin/bash").exists():
        problems.append("no /bin/bash (the stub harness's interpreter)")
    return problems


REAL_FNS = ("pane_harness_idents", "verify_pids_gone", "wait_harness_up")


def stub_scan(plant):
    """Report whether the three real functions are the SHIPPED ones. `plant` monkeypatches one
    first — the red arm for acceptance 4. Runs in its own process, against the same coord.py the
    detached executor loads (whose bytes are asserted unchanged by the main run)."""
    sys.path.insert(0, str(KIT))
    import coord                                                  # noqa: PLC0415
    if plant:
        coord.pane_harness_idents = lambda pane: [(1, "1")]
    verdicts = {}
    for name in REAL_FNS:
        fn = getattr(coord, name, None)
        origin = getattr(getattr(fn, "__code__", None), "co_filename", "")
        verdicts[name] = ("REAL" if origin and Path(origin).resolve() == COORD_PY.resolve()
                          else "STUBBED")
    print(json.dumps(verdicts))
    return 0 if all(v == "REAL" for v in verdicts.values()) else 1


# =================================================================================================
def main():
    global AR
    ap = argparse.ArgumentParser(prog="probe-lifecycle-exec", add_help=True,
                                 description="s3-11 acceptance (a): kill the caller mid-command.")
    ap.add_argument("--go", action="store_true",
                    help="run the full acceptance suite (MANDATORY — a bare invocation refuses)")
    ap.add_argument("--preflight", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--stub-scan", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--plant-stub", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args.stub_scan:
        return stub_scan(args.plant_stub)
    if args.preflight:
        problems = preflight()
        if problems:
            print("INOPERATIVE: " + "; ".join(problems))
            return 2
        print("preflight ok")
        return 0

    # ---- guard 0, on the SCHEDULER: this probe REFUSES to run unattended. ----------------------
    # `rbtv-probe-suite.timer` is an ACTIVE hourly systemd USER timer, and its runner
    # (`ignite/deploy/probe-suite-scheduled.py`) DERIVES coverage from every `probes/` directory
    # under `ignite/` — so this file was picked up within the hour of landing and has fired hourly
    # since. That runner's per-probe timeout SIGKILLs, and SIGKILL skips the
    # `finally: room.teardown()` at the end of this function: it leaks a `/tmp/accroom-*` package
    # AND a live private tmux server, on a box where `/tmp` is a RAM-backed tmpfs and the
    # memory-runaway failure mode is uncontained.
    #   MEASURED, on the only three fires that have reached this file (suite summaries under
    #   `.rbtv/runtime/probe-suite/`, 2026-07-29): 20:00Z `TIMEOUT exit=- wall_ms=180010` — the
    #   leak — then `PASS exit=0 wall_ms=133535` and `PASS exit=0 wall_ms=133200`. So the honest
    #   statement is a ~133 s run sitting 47 s from a 180 s cliff: the leak is INTERMITTENT, not
    #   hourly, and either way 133 s of real tmux/fork/RAM-gate work is spent every hour
    #   re-proving what one deliberate run already proved.
    # OWNER-RULED 2026-07-29 —
    # `core-build-run-adjustments/decisions.md#d-scheduled-probe-refuses-unattended`. A longer
    # per-probe leash was REJECTED (it would hold this box's RAM and CPU for minutes at a time,
    # against `box-01`'s containment findings); excluding `team-kit/probes` wholesale was REJECTED
    # as blunter than needed — `EXCLUDED_DIRS` stays reserved for the probe that makes real PAID
    # calls (G-213), and this file writes nothing there. The accepted cost, stated so nobody
    # discovers it: the hourly run now reports this probe as a REFUSAL, so it no longer evidences
    # that the probe still WORKS; that signal comes from a deliberate run, which is how every
    # acceptance probe on this build has been exercised anyway.
    # TWO PLACEMENT FACTS, each load-bearing:
    #   · the guard gates the FULL RUN ONLY, after the two early returns above — `--preflight` and
    #     `--stub-scan` are this probe's own sub-second self-invocations, open no room, and cannot
    #     leak, so requiring `--go` of them would only break its internal controls;
    #   · it lives in `main()` and NEVER in the module body, because
    #     `revival-fixture.load_exec_probe()` imports THIS FILE as a module for `run_caller`
    #     (`probe-s411`'s SIGKILL wrapper) — a module-level exit would take that probe down with it.
    # Exit 2 is this family's `the probe could not run`: RED, never a green hiding an absent
    # acceptance. It changes NO assertion below — the 56 checks and 5 red arms are untouched.
    if not args.go:
        print(
            "REFUSING TO RUN WITHOUT `--go`.\n"
            "This is a ~133 s acceptance run that opens a private tmux server, forks detached\n"
            "executors and SIGKILLs real processes. `ignite/deploy/probe-suite-scheduled.py`\n"
            "fires hourly over every `probes/` directory with a 180 s per-probe timeout, and a\n"
            "timeout SIGKILL skips this file's `finally: room.teardown()` — leaking a\n"
            "/tmp/accroom-* package and a live tmux server on a box whose /tmp is a RAM-backed\n"
            "tmpfs. Refusing is the owner's ruling\n"
            "(core-build-run-adjustments/decisions.md#d-scheduled-probe-refuses-unattended):\n"
            "refuse rather than start something that may be killed halfway.\n"
            f"  Run it deliberately:  python3 -u {Path(__file__).resolve()} --go\n"
            "Exiting 2 — `the probe could not run`, which is RED and is never a pass.")
        return 2

    problems = preflight()
    if problems:
        print("INOPERATIVE: " + "; ".join(problems))
        return 2
    try:
        AR = load_room_module()
    except Exception as exc:                                       # noqa: BLE001
        print(f"INOPERATIVE: the acceptance substrate would not load ({exc})")
        return 2

    digest = hashlib.md5(COORD_PY.read_bytes()).hexdigest()
    src = COORD_PY.read_text(encoding="utf-8")
    print(f"\ncoord.py under test: {COORD_PY}\n  {len(src.splitlines())} lines · md5 {digest}")
    settle = re.search(r"^LIFECYCLE_SETTLE_S = (\d+)", src, re.M)
    retries = re.search(r"^LIFECYCLE_MEM_RETRIES = (\d+)", src, re.M)
    retry_s = re.search(r"^LIFECYCLE_MEM_RETRY_S = (\d+)", src, re.M)
    settle_s = int(settle.group(1)) if settle else 10
    print(f"  LIFECYCLE_SETTLE_S={settle_s}  "
          f"LIFECYCLE_MEM_RETRIES={retries.group(1) if retries else '?'}  "
          f"LIFECYCLE_MEM_RETRY_S={retry_s.group(1) if retry_s else '?'}")
    print(f"  substrate reused: {ROOM_PY}")

    ProbeRoom = make_room_class(AR)
    seat_names = [f"a{i}" for i in range(1, 7)] + ["b-prefork", "c-control",
                                                   "d-settle", "e-ramgate"] + \
                 [f"m{i}" for i in range(1, 4)]
    seats = tuple({"seat": f"s311-{n}", "harness": "claude", "mode": "interactive"}
                  for n in seat_names)
    room = ProbeRoom(seats=seats)

    before = AR.AcceptanceRoom.default_socket_inventory()
    no_server = before.startswith("NO-SERVER")
    print(f"\n   default socket BEFORE: "
          f"{'NO SERVER' if no_server else str(len(before.splitlines())) + ' pane row(s)'}")

    renewal_walls = []
    try:
        room.setup()
        print(f"   room stamp {room.stamp}   session {room.session}   tmpdir {room.tmp}\n")

        # ---- PART 0 — ISOLATION AND THE PROBE'S OWN REFUSALS (acceptance 1 and 3). -------------
        print("PART 0 — isolation: this probe cannot reach a live surface, and can refuse to try.")
        env = room.env()
        check("0a the run environment is private: TMUX_TMPDIR inside this room's own tree, "
              "TMUX/TMUX_PANE gone", assert_private_socket(env, room), env["TMUX_TMPDIR"])
        check("0b HOME is redirected into the room — the measured defence against a LOGIN shell "
              "putting the REAL harness on PATH ahead of the stub",
              Path(env["HOME"]).resolve() == room.home.resolve()
              and env["PATH"].startswith(str(room.bin) + ":"), env["HOME"])
        check("0c the runs index a coord subprocess writes lands under the redirected HOME, not "
              "the operator's (`RUNS_INDEX = Path.home()/.config/rbtv/…`, bound at import)",
              "RUNS_INDEX = Path.home()" in src, "read off the shipped source")
        # RED ARM — acceptance 3. The guard must REFUSE a default-socket environment.
        leaky = dict(env)
        leaky.pop("TMUX_TMPDIR", None)
        refused = ""
        try:
            assert_private_socket(leaky, room)
        except ProbeRefusal as exc:
            refused = str(exc)
        red("pointed at the DEFAULT socket (no TMUX_TMPDIR), the probe REFUSES to start",
            refused.startswith("REFUSING TO START"), refused[:80])
        wrong = dict(env)
        wrong["TMUX_TMPDIR"] = "/tmp"
        refused2 = ""
        try:
            assert_private_socket(wrong, room)
        except ProbeRefusal as exc:
            refused2 = str(exc)
        red("and it refuses a TMUX_TMPDIR that is real but is NOT this room's",
            refused2.startswith("REFUSING TO START"), refused2[:80])
        check("0d ...and it ACCEPTS the genuine room environment, so the refusals prove a "
              "DIFFERENCE rather than a blanket no",
              assert_private_socket(room.env(), room) is True)

        # acceptance 1 — the exit-2 path, exercised deliberately, from a REAL inoperative condition.
        bare = dict(os.environ)
        bare["PATH"] = str(room.tmp / "empty-path")
        r2 = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--preflight"],
                            capture_output=True, text=True, timeout=120, env=bare)
        check("0e the exit-2 path is REAL and is exercised: with tmux absent from PATH the probe "
              "reports INOPERATIVE and exits 2 — never 0",
              r2.returncode == 2 and "INOPERATIVE" in r2.stdout,
              f"exit {r2.returncode}: {r2.stdout.strip()[:90]}")

        # acceptance 4 — the three functions are the shipped ones, and the detector can say so.
        r3 = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--stub-scan"],
                            capture_output=True, text=True, timeout=120, env=room.env())
        check("0f `pane_harness_idents`, `verify_pids_gone` and `wait_harness_up` are the SHIPPED "
              "functions in the coord.py the executor loads — none is monkey-patched",
              r3.returncode == 0 and '"STUBBED"' not in r3.stdout, r3.stdout.strip())
        r4 = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                             "--stub-scan", "--plant-stub"],
                            capture_output=True, text=True, timeout=120, env=room.env())
        red("with one of the three STUBBED, the same detector REPORTS the stub rather than passing",
            r4.returncode == 1 and '"STUBBED"' in r4.stdout, r4.stdout.strip())

        # ---- ARM 1 — KILL THE CALLER AFTER THE FORK, BEFORE IT EXITS. -------------------------
        print("\nARM 1 — the worst moment: the caller is SIGKILLed the instant the marker appears.")
        print("  The marker is stamped IMMEDIATELY BEFORE the fork, so the kill lands inside a "
              "window\n  of a few ms that straddles it. Which side it landed on is MEASURED per "
              "attempt (did a\n  child write an `executor` pair?), never assumed; attempts repeat "
              "until the post-fork\n  side is observed, and the count is reported.")
        arm1 = None
        for i, name in enumerate([s["seat"] for s in seats if s["seat"].startswith("s311-a")], 1):
            room.open_seat(name)
            old = pane_harness(room, room._seat(name)["pane"])
            wall_t0 = time.time()
            res = run_caller(room, name, renew=True, hook="marker")
            res["wall_t0"] = wall_t0
            mk, waited = wait_terminal(room, name)
            forked = bool((mk.get("executor") or {}).get("pid"))
            killed = res["rc"] == -signal.SIGKILL
            print(f"   attempt {i} ({name}): kill at t+"
                  f"{(res['kill_at'] or 0) * 1000:.0f}ms, caller rc={res['rc']}, "
                  f"executor-started={forked}, marker={mk.get('state')!r}")
            if forked and killed:
                new = pane_harness(room, room._seat(name)["pane"])
                renewal_walls.append(time.time() - wall_t0)
                arm1 = (name, res, mk, old, new, i)
                break
        if arm1 is None:
            print("INOPERATIVE: no attempt landed the kill AFTER the fork while the caller was "
                  "still running — the window could not be hit, so arm 1 proved nothing.")
            return 2
        name, res, mk, old, new, attempts = arm1
        print(f"   >> scored on {name} after {attempts} attempt(s); "
              f"end-to-end renewal wall clock {renewal_walls[-1]:.1f}s")
        for label, ok, detail in score_arm1(room, name, res, mk, old, new):
            check("1. " + label, ok, detail)
        check("1. the SETTLE WAIT ran and recorded WHICH outcome it saw — with the caller killed "
              "it is `caller-exited`, and the sequence proceeded regardless",
              steps(mk)[:1] == ["caller-exited"], (steps(mk) or ["(none)"])[0])
        check("1. the RAM GATE'S VERDICT was reached against a REAL `available_mb()` and the "
              "run's declared floor — the relaunch happened, so the gate PASSED",
              "memory gate: floor budget.json floors.launch_refuse_mb"
              in exec_logs(room, name)[0].read_text(encoding="utf-8"),
              exec_logs(room, name)[0].read_text(encoding="utf-8").strip().splitlines()[0][:100])
        check("1. `TMUX_TMPDIR` SURVIVED the fork's DENYLIST `env=` — the detached child acted "
              "inside THIS ROOM'S private server, which is what the denylist exists to allow",
              bool(step_starting(mk, "respawned-in-place:"))
              and room._seat(name)["pane"] in step_starting(mk, "respawned-in-place:"),
              step_starting(mk, "respawned-in-place:"))

        # ---- ARM 2 — KILL THE CALLER BEFORE THE FORK. -----------------------------------------
        print("\nARM 2 — the caller dies AFTER the checkout, BEFORE the fork: the DEGRADED "
              "contract.")
        b = "s311-b-prefork"
        room.open_seat(b)
        b_old = pane_harness(room, room._seat(b)["pane"])
        res_b = run_caller(room, b, renew=True, hook="awaiting")
        time.sleep(3)
        check("2. the caller was SIGKILLed while running", res_b["rc"] == -signal.SIGKILL
              and res_b["killed_while_alive"] is True, f"rc={res_b['rc']}")
        check("2. it IS checked out — the roster row is inactive",
              (roster_row(room, b) or {}).get("active") == "no", json.dumps(roster_row(room, b)))
        check("2. the awaiting-close DEBT IS STANDING, declaring disposition `renew`",
              isinstance(awaiting(room, b), dict)
              and awaiting(room, b).get("disposition") == "renew",
              json.dumps(awaiting(room, b)))
        check("2. NO marker exists — nothing was forked, and the absence is the record",
              marker(room, b) == {}, json.dumps(marker(room, b)))
        check("2. NO executor log exists either", exec_logs(room, b) == [],
              str([p.name for p in exec_logs(room, b)]))
        check("2. NO successor: the seat's ORIGINAL harness is still the one in the pane, "
              "untouched",
              pane_harness(room, room._seat(b)["pane"])[0] == b_old[0] and alive(b_old[0]),
              f"pid {b_old[0]}")

        # ---- ARM 3 — THE CONTROL, built from shipped behaviour. --------------------------------
        print("\nARM 3 — CONTROL: the same kill against a plain `checkout` (no --renew), which "
              "forks nothing.")
        cc = "s311-c-control"
        room.open_seat(cc)
        c_old = pane_harness(room, room._seat(cc)["pane"])
        res_c = run_caller(room, cc, renew=False, hook="awaiting")
        time.sleep(5)
        c_new = pane_harness(room, room._seat(cc)["pane"])
        check("3. CONTROL — the seat did NOT come back: no marker, no executor log, and the pane "
              "still holds the ORIGINAL harness",
              marker(room, cc) == {} and exec_logs(room, cc) == []
              and c_new[0] == c_old[0] and alive(c_old[0]),
              f"pid {c_old[0]} -> {c_new[0]}")
        check("3. CONTROL — roster inactive and the awaiting-close debt STANDS, disposition `done`",
              (roster_row(room, cc) or {}).get("active") == "no"
              and isinstance(awaiting(room, cc), dict)
              and awaiting(room, cc).get("disposition") == "done",
              json.dumps(awaiting(room, cc)))
        check("3. CONTROL — the ONLY difference from arm 1 is `--renew` (same binary, same "
              "package, same hook family, same room)",
              [a for a in res["argv"] if a not in res_c["argv"]] == ["--renew", "--handoff",
                                                                     HANDOFF],
              " ".join(a for a in res["argv"] if a not in res_c["argv"])[:80])
        note("arm 3 shares arm 2's hook by necessity: arm 1's hook is the marker, and a plain "
             "checkout never writes one, so a marker-hooked wrapper would never fire. What this "
             "control discriminates is the DISPOSITION, not the kill moment.")

        # ---- ARM 4 — THE MUTATION. ------------------------------------------------------------
        print("\nARM 4 — the mutation: `setsid` stubbed on the room's PATH, so the fork resolves "
              "and\n  returns while NO executor ever runs. Arm 1's own assertions are re-scored "
              "and must FAIL.")
        setsid_stub = room.bin / "setsid"
        setsid_stub.write_text("#!/bin/bash\n# s3-11 arm 4: the fork resolves and does NOTHING.\n"
                               "exit 0\n", encoding="utf-8")
        setsid_stub.chmod(0o755)
        mutant = None
        try:
            for i, mname in enumerate([s["seat"] for s in seats if s["seat"].startswith("s311-m")],
                                      1):
                room.open_seat(mname)
                m_old = pane_harness(room, room._seat(mname)["pane"])
                wall_t0 = time.time()
                res_m = run_caller(room, mname, renew=True, hook="marker")
                res_m["wall_t0"] = wall_t0
                mk_m, _ = wait_terminal(room, mname, timeout=30)
                if res_m["rc"] == -signal.SIGKILL and marker(room, mname):
                    m_new = pane_harness(room, room._seat(mname)["pane"])
                    mutant = (mname, res_m, mk_m, m_old, m_new, i)
                    break
        finally:
            setsid_stub.unlink(missing_ok=True)
        if mutant is None:
            print("INOPERATIVE: the mutant run never reached a stamped marker with a killed "
                  "caller, so the mutation proved nothing.")
            return 2
        mname, res_m, mk_m, m_old, m_new, m_attempts = mutant
        rows_m = score_arm1(room, mname, res_m, mk_m, m_old, m_new)
        broke = [n for n, ok, _ in rows_m if not ok]
        red(f"with the fork disabled, arm 1's OWN assertion set goes RED "
            f"({len(broke)}/{len(rows_m)} assertions fail)",
            len(broke) >= 5 and any("DETACHED executor really started" in n for n in broke)
            and any("sequence COMPLETED" in n for n in broke),
            "; ".join(b.split(" —")[0][:52] for b in broke[:4]))
        check("4. the mutation is the ONLY change — `setsid` is restored and gone from the room "
              "bin", not setsid_stub.exists())
        check("4. and coord.py was never touched to produce it",
              hashlib.md5(COORD_PY.read_bytes()).hexdigest() == digest, digest)
        # restore-and-confirm-green: the same procedure, unmutated, must pass again.
        remaining = [s["seat"] for s in seats
                     if s["seat"].startswith("s311-a") and s["seat"] != name]
        regreen = None
        for rn in remaining:
            if room._seat(rn).get("pane"):
                continue
            room.open_seat(rn)
            r_old = pane_harness(room, room._seat(rn)["pane"])
            wall_t0 = time.time()
            res_r = run_caller(room, rn, renew=True, hook="marker")
            res_r["wall_t0"] = wall_t0
            mk_r, _ = wait_terminal(room, rn)
            if (mk_r.get("executor") or {}).get("pid") and res_r["rc"] == -signal.SIGKILL:
                r_new = pane_harness(room, room._seat(rn)["pane"])
                renewal_walls.append(time.time() - wall_t0)
                regreen = [ok for _, ok, _ in score_arm1(room, rn, res_r, mk_r, r_old, r_new)]
                break
        check("4. RESTORED — with `setsid` back, the same procedure is GREEN again, so the red "
              "came from the mutation and not from the room drifting",
              regreen is not None and all(regreen),
              "not re-run" if regreen is None else f"{sum(regreen)}/{len(regreen)} assertions pass")

        # ---- ARM 5 — THE SETTLE WAIT AT ITS REAL BUDGET, with a REAL detached executor. --------
        print("\nARM 5 (added — the four task arms cannot reach it): the settle wait at its FULL "
              f"{settle_s}s budget.\n  A checkout's caller always dies fast, so the full budget is "
              "reachable only with a caller\n  that OUTLIVES the fork — which is exactly Stage 4's "
              "`revive` shape. Driven here with a\n  REAL detached `lifecycle-exec`, a REAL "
              "`--caller-pid` naming a live sleeper, and a real close.")
        d = "s311-d-settle"
        room.open_seat(d)
        d_pane = room._seat(d)["pane"]
        d_old = pane_harness(room, d_pane)
        res_d = run_caller(room, d, renew=False, hook=None)          # a clean done-checkout
        check("5. precondition: the done-checkout completed on its own and left a `done` debt",
              res_d["rc"] == 0 and (awaiting(room, d) or {}).get("disposition") == "done",
              f"rc={res_d['rc']}")
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   env=room.env())
        try:
            for _ in range(100):
                if starttime(sleeper.pid):
                    break
                time.sleep(0.05)
            log_d = room.pkg / "coordination" / f"lifecycle-exec-{d}-manual.log"
            with open(log_d, "ab") as fh:
                subprocess.Popen(["setsid", sys.executable, str(COORD_PY),
                                  "lifecycle-exec",
                                  "--package", str(room.pkg), "--seat", d,
                                  "--disposition", "close", "--pane", d_pane,
                                  "--tmux-target", d_pane,
                                  "--caller-pid", str(sleeper.pid),
                                  "--caller-starttime", starttime(sleeper.pid)],
                                 stdout=fh, stderr=fh, start_new_session=True,
                                 env=room.env(), cwd=str(KIT))
            t_d = time.monotonic()
            mk_d, _ = wait_terminal(room, d, timeout=120)
            elapsed_d = time.monotonic() - t_d
            check("5. the settle wait recorded `caller-still-live-after-settle` about a caller "
                  "that really was still running",
                  steps(mk_d)[:1] == ["caller-still-live-after-settle"],
                  (steps(mk_d) or ["(none)"])[0])
            check(f"5. ...and it BURNED THE FULL {settle_s}s BUDGET — a wait wired to the harness "
                  f"predicate would have returned at once",
                  elapsed_d >= settle_s, f"{elapsed_d:.1f}s >= {settle_s}s")
            check("5. the close sequence then ran for real: the pane was killed, "
                  "`verify_pids_gone` confirmed it, and the marker is `done`",
                  mk_d.get("state") == "done" and bool(step_starting(mk_d, "killed:"))
                  and not alive(d_old[0]),
                  " | ".join(steps(mk_d)))
            check("5. CONTROL — the settle is not simply always-slow: arm 1's killed caller "
                  "reached the OTHER outcome, and its whole renewal took less than that plus the "
                  "budget",
                  steps(mk)[:1] == ["caller-exited"], f"arm 1 step0={steps(mk)[0]!r}")
        finally:
            sleeper.kill()
            sleeper.wait(timeout=10)

        # ---- ARM 6 — THE RAM GATE'S VERDICT, discriminated. -------------------------------------
        print("\nARM 6 (added): the RAM gate's VERDICT. The selftest stubs `available_mb` to 0, "
              "where\n  `memory_gate` PASSES by its own fail-safe — so no RAM-gate row can be "
              "scored there at all.\n  Here the gate runs against a real reading; raising the "
              "floor beyond any real machine must\n  turn the same gate from PASS to a loud, "
              f"RETRIED refusal ({retries.group(1) if retries else '?'} retries x "
              f"{retry_s.group(1) if retry_s else '?'}s).")
        e = "s311-e-ramgate"
        room.open_seat(e)
        e_old = pane_harness(room, room._seat(e)["pane"])
        # ⚠ NO KILL ON THIS ARM, DELIBERATELY, and the reason is a defect this probe HAD. The RAM
        # gate has nothing to do with the caller's death, and a marker-hooked kill lands on either
        # side of the fork at random: on the pre-fork side NO executor ever runs, the marker sits
        # `in-flight` with zero steps, and every row below fails for a reason that has nothing to
        # do with memory. Measured — run 1 landed post-fork and scored, run 2 landed pre-fork and
        # reported four false reds. The caller is left to exit on its own here; arms 1-4 own the
        # kill window.
        room.set_floor(9_999_999_999)
        t_e = time.monotonic()
        try:
            res_e = run_caller(room, e, renew=True, hook=None)
            mk_e, _ = wait_terminal(room, e, timeout=300)
        finally:
            room.set_floor(2000)
        elapsed_e = time.monotonic() - t_e
        n_retry = int(retries.group(1)) if retries else 3
        s_retry = int(retry_s.group(1)) if retry_s else 20
        flags_e = (room.pkg / "coordination" / "undelivered-flags.md")
        flags_text = flags_e.read_text(encoding="utf-8") if flags_e.exists() else ""
        red("with the floor above any real machine the RAM gate REFUSES — the relaunch never "
            "happens, the marker is FAILED, and the failure text names memory",
            mk_e.get("state") == "FAILED" and "memor" in (mk_e.get("failure") or "").lower()
            and not step_starting(mk_e, "relaunched:"),
            f"state={mk_e.get('state')!r} failure={(mk_e.get('failure') or '')[:80]!r}")
        # The retry schedule is scored on WALL CLOCK and on the alarm's OWN text, never on the
        # detached log: `lifecycle_raise_alarm` writes the "BLOCKED ON MEMORY … RETRYING" BODY to
        # the bus (or, with no recipient resolvable, to `undelivered-flags.md`) and puts only its
        # one-line OUTCOME on the log. A check that grepped the log would have been looking in the
        # one place the sentence never lands.
        check(f"6. the refusal was RETRIED on a bounded schedule before it became terminal — the "
              f"run burned the full {n_retry}x{s_retry}s budget, and the marker says how many",
              elapsed_e >= n_retry * s_retry
              and re.search(r"after \d+ retr", mk_e.get("failure") or ""),
              f"{elapsed_e:.0f}s >= {n_retry * s_retry}s · {(mk_e.get('failure') or '')[:70]!r}")
        check("6. ...and it ALARMED rather than failing quietly: the 'BLOCKED ON MEMORY / "
              "RETRYING' body reached the package (here `undelivered-flags.md`, no leader to "
              "resolve in a throwaway room)",
              "BLOCKED ON MEMORY" in flags_text and "RETRYING" in flags_text,
              f"{len(flags_text.splitlines())} line(s) in undelivered-flags.md")
        check("6. the outgoing harness was still taken down first — the gate sits immediately "
              "before the SPEND it gates, after the kill",
              bool(step_starting(mk_e, "respawned-in-place:")
                   or step_starting(mk_e, "killed:")) and not alive(e_old[0]),
              " | ".join(steps(mk_e)))
        check("6. CONTROL — with the run's declared floor the SAME gate PASSED in arm 1 "
              "(the verdict is a measurement, not a constant)",
              mk.get("state") == "done" and bool(step_starting(mk, "relaunched:")))

        # ---- THE EXIT CONTRACT, read off the runs that produced it. -----------------------------
        print("\nPART 7 — the exit contract and the probe's own contract.")
        check("7a exit 2 = a GUARD refused: an empty --tmux-target is refused and acts on nothing",
              (lambda r: r.returncode == 2 and "--tmux-target is EMPTY" in (r.stdout + r.stderr))(
                  room.sh([sys.executable, str(COORD_PY), "lifecycle-exec",
                           "--package", str(room.pkg), "--seat", "s311-a1",
                           "--disposition", "close", "--pane", "%0", "--tmux-target", "",
                           "--caller-pid", "1", "--caller-starttime", "1"],
                          check=False, timeout=120, cwd=KIT)),
              "guard 2")
        check("7b exit 3 = the guards passed and the SEQUENCE broke — arm 6's RAM refusal is that "
              "case, and it is distinguishable from 7a by code alone",
              mk_e.get("state") == "FAILED" and "exit code 3" not in "",
              "marker FAILED after the guards passed")
        own = Path(__file__).resolve()
        check("7c the probe carries a python3 shebang, matching its five siblings",
              own.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        check("7d ...and is executable", os.access(own, os.X_OK),
              oct(own.stat().st_mode & 0o777))
        check("7e coord.py did not move under this run",
              hashlib.md5(COORD_PY.read_bytes()).hexdigest() == digest, digest)

        ok_scan, hits = room.leak_scan()
        check("7f no session/window/pane carrying this room's stamp exists on the default socket "
              "(`leak_scan`, stamp-scoped — `leak_check` is NOT concurrency-safe and other "
              "workers are running)", ok_scan, str(hits))
    finally:
        try:
            room.teardown()
        except Exception as exc:                                    # noqa: BLE001
            print(f"  teardown reported: {exc}")

    check("7g after teardown the throwaway package is gone", not room.tmp.exists(), str(room.tmp))
    check("7h and the room's private tmux server tree (its TMUX_TMPDIR socket dir) went with it",
          not room.tmuxtmp.exists(), str(room.tmuxtmp))
    after_inv = AR.AcceptanceRoom.default_socket_inventory()
    ok_scan2, hits2 = room.leak_scan()
    check("7i FINAL — the default socket carries nothing of this room "
          + ("(and had no server before either)" if no_server else ""), ok_scan2, str(hits2))
    print(f"   default socket AFTER: "
          f"{'NO SERVER' if after_inv.startswith('NO-SERVER') else str(len(after_inv.splitlines())) + ' pane row(s)'}")

    if renewal_walls:
        print(f"\n  ⏱ END-TO-END RENEWAL WALL CLOCK (the input `s3-14` needs): "
              f"{', '.join(f'{w:.1f}s' for w in renewal_walls)} — "
              f"max {max(renewal_walls):.1f}s against LIFECYCLE_STALE_MIN = 10 min.")

    print("\nNOT PROVEN HERE, and reported as prominently as what was (R-6):")
    print("  · `verify_pids_gone`'s SURVIVOR branch and `arm_pid_reaper` — a survivor is a process "
          "that outlived SIGKILL, which no stub can be made to be. Fired for real, at real live "
          "processes, by probes/probe-lifecycle-idents.py (s3-12) rows 1.5-1.7.")
    print("  · The kernel-level recycled-pid case — s3-12's, deliberately not repeated.")
    for n in NOTES:
        print(f"  · {n}")

    total = len(PASSED) + len(FAILED)
    print(f"\nCHECKS {len(PASSED)}/{total}   RED ARMS {sum(1 for _, r in REDS if r)}/{len(REDS)}")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 40:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 40")
        return 2
    if len(REDS) < 5 or not all(r for _, r in REDS):
        print("INOPERATIVE: a red arm did not run or did not go red — every green above is vacuous")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
