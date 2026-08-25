#!/usr/bin/env python3
"""probe-lifecycle-idents.py — the recycled-pid hazard, and the two predicates that must never
be swapped.

WHAT IS UNDER TEST (task s3-12; spec `stage-3-executor-spec.md` §4.1 + §6(b)):

  PART 1 — THE RECYCLED-PID CASE. Owner directive msg #137's actual shape is NOT "the kernel wrapped
  its pid counter". It is: AN IDENT NAMES A PID THAT IS NOW A LIVE HARNESS BUT IS NOT THE REMEMBERED
  PROCESS. A teardown is exactly when new processes start, so a dead seat's reaper firing on "this
  pid is A harness" SIGKILLs a live successor. The guard is the `(pid, starttime)` PAIR. This part
  constructs the hazard directly — a live stub harness plus a deliberately WRONG starttime — rather
  than trying to recycle an OS pid, which `pid_max` makes impractical without a private pid
  namespace. Both the in-process path (`verify_pids_gone`) and the DETACHED path
  (`arm_pid_reaper` -> `reaper_script`) are fired for real, at a real live process.

  PART 2 — GUARD CONFORMANCE. `ident_is_live_process` and `ident_is_live_harness` are NOT
  interchangeable and this is the only place the difference can be proven against real processes.
  `ident_is_live_harness` rests on `is_harness_argv`, which matches only the claude/codex/opencode
  basenames — so it calls EVERY live python process dead. The lifecycle executor and its forking
  caller ARE python. Wire the caller-settle wait or the staleness test to the harness predicate and
  you get a wait that cannot wait and a MID-RENEWAL misread as CRASHED (a double-launched seat).
  Both failures LOOK like working code, which is why each row here carries a mutation red arm.

  PART 3 — THE SEVEN GUARDED ACTS of spec §4.1 are located in the shipped code, by symbol and by
  today's line, with an ordering check on the teardown and a NEGATIVE conformance check on guards
  4 and 5 (the harness predicate must be ABSENT from `lifecycle_settle` and `lifecycle_stale`). A
  guard with no located call site is a FAILING row, never a note.

WHY A PROBE AND NOT A SELFTEST CASE. `_selftest_checks` (coord.py:6926) stubs `pane_harness_idents`,
`verify_pids_gone`, `arm_pid_reaper`, `process_identity`'s consumers and `available_mb`
(coord.py:6995-7012), and the s3-06 block additionally zeroes `LIFECYCLE_SETTLE_S`. A real-identity
proof cannot live there: every predicate it would assert on has been replaced by a stub.

DISCLOSED SUBSTITUTIONS AND SKIPS (R-6 — an unrun arm reported as absent is the honest form):
  * NO TMUX, AT ALL. The task's acceptance 5 asks for a private socket; this probe is stricter and
    invokes NO tmux binary whatsoever, enforced by a sentinel over coord's `subprocess` that RAISES
    on any tmux argv (control 0c proves the sentinel fires). Nothing here needs a pane: the
    predicates, the reaper, the settle wait and the staleness test all act on plain processes.
    Consequence, stated rather than hidden: the two tmux-reading collaborators of the close path
    (`live_panes` for `--tmux-target` validation, `pane_harness_idents` for a real pane) are
    SUBSTITUTED in part 2's sequence drive — the probe-g188 precedent. Their real behaviour is
    s3-11's subject, not this file's.
  * THE KERNEL-LEVEL RECYCLE IS SKIPPED. The optional `unshare -rp --fork --mount-proc` +
    `/proc/sys/kernel/ns_last_pid` arm is NOT run (it needs a private pid namespace). It is
    reported as SKIPPED in the output, never as passed.
  * Part 2 row 6 drives the REAL `cmd_lifecycle_exec` — all five entry guards, then
    `run_lifecycle_sequence` — on a throwaway package, disposition `close`, no pane.

RUN IT:  cd <repo>/ignite/coord   # this file's parent directory
         python3 probes/probe-lifecycle-idents.py

Exit 0 = every arm passed. Exit 1 = a property is broken. Exit 2 = the probe could not run (never
a pass: a probe that cannot execute has proven nothing, and a red arm that failed to go red makes
its green partner vacuous, so that too is a refusal rather than a pass).

Runtime ~25s: the settle wait is exercised at its REAL budget (LIFECYCLE_SETTLE_S), not zeroed.
"""

import os as _os, sys as _sys, pathlib as _pl  # task 7.630: solo-run tmux isolation, FIRST
_sys.path.insert(0, str(next(p for p in _pl.Path(__file__).resolve().parents if (p / "coord" / "self_isolate.py").is_file()) / "coord"))
from self_isolate import self_isolate_tmux as _self_isolate_tmux; _self_isolate_tmux()

import ast
import hashlib
import os
import re
import shutil
import subprocess as real_subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path

# ---- guard 1, on ourselves: this probe inherits its dispatcher's pane otherwise. ----------------
for _v in ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE"):
    os.environ.pop(_v, None)

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT))

try:
    import coord  # noqa: E402
except Exception as exc:  # noqa: BLE001 — a probe that cannot import proves nothing
    print(f"INOPERATIVE: could not import the kit ({exc})")
    sys.exit(2)

COORD_PY = KIT / "coord.py"
FAILED, PASSED, REDS = [], [], []
PROCS = []


def check(name, ok, detail=""):
    (PASSED if ok else FAILED).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    return ok


def red(name, went_red, detail=""):
    """A RED ARM. `went_red` must be True: it means the deliberately broken variant was REJECTED.
    A red arm that stays green makes its green partner vacuous, so it is recorded as a FAILURE."""
    REDS.append((name, bool(went_red)))
    (PASSED if went_red else FAILED).append("RED ARM: " + name)
    print(f"  {'RED ' if went_red else 'FAIL'}  red arm: {name}" + (f" — {detail}" if detail else ""))
    return went_red


# =================================================================================================
# THE NO-TMUX SENTINEL. Every tmux call in coord.py goes through `subprocess.run` in coord's own
# module namespace, so replacing THAT name blocks the whole surface. It is a shim rather than a
# mutation of the real `subprocess` module: this probe forks its own processes and must keep an
# unshimmed handle (`real_subprocess`).
# =================================================================================================
class _TmuxRefused(RuntimeError):
    pass


class _NoTmux:
    """Delegates everything to the real module EXCEPT an argv whose executable is tmux."""

    @staticmethod
    def _bar(argv):
        if isinstance(argv, (list, tuple)) and argv and os.path.basename(str(argv[0])) == "tmux":
            raise _TmuxRefused(f"the probe refuses to invoke tmux: {' '.join(map(str, argv))}")

    def run(self, argv, *a, **k):
        self._bar(argv)
        return real_subprocess.run(argv, *a, **k)

    def Popen(self, argv, *a, **k):  # noqa: N802 — mirrors the stdlib name it stands in for
        self._bar(argv)
        return real_subprocess.Popen(argv, *a, **k)

    def __getattr__(self, item):
        return getattr(real_subprocess, item)


coord.subprocess = _NoTmux()


# =================================================================================================
# FIXTURE HELPERS
# =================================================================================================
def stub_harness(workdir, tag):
    """Start a REAL live process whose argv makes `is_harness_argv` true — a stand-in for a seat's
    claude. Returns (proc, (pid, starttime)). It is a python sleeper rather than a shell one so the
    process the ident names is the process that dies: a `sh` wrapper leaves an orphan `sleep`."""
    stub = Path(workdir) / f"claude-{tag}" / "claude"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(3600)\n")
    stub.chmod(0o755)
    proc = real_subprocess.Popen([str(stub)], stdout=real_subprocess.DEVNULL,
                                 stderr=real_subprocess.DEVNULL)
    PROCS.append(proc)
    # /proc/<pid>/stat exists from the FORK, /proc/<pid>/cmdline only from the EXEC. Gating on the
    # ident alone therefore never waits at all: it returns a pid whose argv is still EMPTY, and
    # 1.1's `is_harness_argv` read loses that race — measured 0.8-3.3% of spawns on this box, which
    # is the 2-in-24 intermittent of 2026-08-12 (state 'R', ident correct, cmdline zero bytes; the
    # argv settles 40-190us later). Wait for the observable "exec happened" instead — a NON-EMPTY
    # cmdline, not a harness-matching one, so 1.1's own predicate is still free to fail.
    for _ in range(100):
        ident = coord.process_identity(proc.pid)
        if ident and cmdline(proc.pid):
            return proc, ident
        time.sleep(0.05)
    return proc, None


def cmdline(pid):
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(
            "utf-8", errors="replace").strip()
    except OSError:
        return ""


def dead(ident, wait_s=6.0):
    """True once `ident` no longer names a live process (a zombie counts as gone — s3-02)."""
    deadline = time.time() + wait_s
    while time.time() < deadline:
        if not coord.ident_is_live_process(ident):
            return True
        time.sleep(0.1)
    return not coord.ident_is_live_process(ident)


def make_package(root, seat, disposition="done"):
    """The state a real checkout leaves behind, written through the ending store."""
    pkg = Path(root) / f"pkg-{seat}"
    base = pkg / "coordination"
    base.mkdir(parents=True)
    (pkg / "seats" / seat).mkdir(parents=True)
    transcript = base / f"{seat}-transcript.txt"
    transcript.write_text("captured scrollback\n")
    kind = "incomplete" if disposition in ("renew", "incomplete") else "done"
    coord.ending_store.stamp_seat_declare(
        pkg, seat, kind,
        diagnostic="context full" if disposition == "renew" else disposition,
        evidence=str(transcript))
    # Nudge the transcript mtime forward so step 7 cannot fail on clock rounding.
    future = time.time() + 120
    os.utime(transcript, (future, future))

    class A:
        pass
    args = A()
    args.seat = seat
    args.disposition = "close"
    args.pane = ""
    args.tmux_target = "%probe"
    args.caller_pid = 0
    args.caller_starttime = ""
    args.handoff_written = None
    args.base = str(base)
    args.workers_dir = str(pkg / "seats")
    args.package = str(pkg)
    args.run = None
    return pkg, base, args


def drive_close(root, seat, caller_ident):
    """Drive the REAL `cmd_lifecycle_exec` — five guards then the close sequence — with
    `caller_ident` handed in as --caller-pid/--caller-starttime. Returns (elapsed, marker-entry,
    outcome). `live_panes` is the ONE substitution (see the header): guard 2 validates
    --tmux-target through it and this probe invokes no tmux."""
    pkg, base, args = make_package(root, seat)
    args.caller_pid, args.caller_starttime = caller_ident
    saved = coord.live_panes
    coord.live_panes = lambda: {"%probe"}
    t0 = time.monotonic()
    outcome = "returned"
    try:
        coord.cmd_lifecycle_exec(args)
    except SystemExit as exc:                                          # an alarm fired
        outcome = f"SystemExit({exc.code})"
    except Exception as exc:                                           # noqa: BLE001
        outcome = f"{type(exc).__name__}: {exc}"
    finally:
        coord.live_panes = saved
    return time.monotonic() - t0, coord.load_lifecycle(base).get(seat) or {}, outcome


# =================================================================================================
# PART 3'S LOCATOR — pure over a source STRING, so the same function runs against the shipped file
# and against a deliberately broken scratch copy.
# =================================================================================================
def call_map(src):
    """{function-name: {called-symbol: [lines]}} for every top-level and nested def."""
    out = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            calls = {}
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    fn = sub.func
                    nm = (fn.id if isinstance(fn, ast.Name)
                          else fn.attr if isinstance(fn, ast.Attribute) else None)
                    if nm:
                        calls.setdefault(nm, []).append(sub.lineno)
            out[node.name] = calls
    return out


SEQ, EXEC_FN, SETTLE, STALE, LAUNCH = ("run_lifecycle_sequence", "cmd_lifecycle_exec",
                                       "lifecycle_settle", "lifecycle_stale", "launch_seat")

# Spec §4.1's seven acts. `required` = symbols whose call site must EXIST in that function;
# `forbidden` = symbols whose presence there IS the defect.
GUARDS = [
    ("1", "kill the outgoing harness (close, and renew's re-place branch)",
     [(SEQ, "pane_harness_idents"), (SEQ, "tmux_kill_pane"), (SEQ, "verify_pids_gone")], []),
    ("2", "in-place respawn (renew, G-154 true)",
     [(SEQ, "tmux_respawn_pane"), (SEQ, "verify_pids_gone")], []),
    ("3", "straggler reap after either kill",
     [(SEQ, "arm_pid_reaper")], []),
    ("4", "wait on the caller's exit — plain pid+starttime equality, NOT the harness predicate",
     [(SEQ, "lifecycle_settle"), (SETTLE, "ident_is_live_process"), (SETTLE, "proc_stat")],
     [(SETTLE, "ident_is_live_harness")]),
    ("5", "executor liveness in the marker — same plain equality, same reason",
     [(STALE, "ident_is_live_process"), (EXEC_FN, "ident_is_live_process")],
     [(STALE, "ident_is_live_harness"), (EXEC_FN, "ident_is_live_harness")]),
    ("6", "adoption check before acting — a live executor on an in-flight entry stands down",
     [(EXEC_FN, "load_lifecycle"), (EXEC_FN, "lifecycle_ident"), (EXEC_FN, "lifecycle_alarm")], []),
    ("7", "successor liveness after relaunch",
     [(LAUNCH, "wait_harness_up"), (SEQ, "pane_harness_idents"), (SEQ, "launch_seat")], []),
]


def locate(src):
    """{guard-id: (ok, [evidence strings], [problem strings])}. `proc_stat` for guard 4 is resolved
    TRANSITIVELY: the spec words it as 'plain pid+starttime equality via proc_stat', and that
    equality lives one hop down, inside `ident_is_live_process`."""
    cm = call_map(src)
    verdicts = {}
    for gid, act, required, forbidden in GUARDS:
        found, problems = [], []
        for fn, sym in required:
            lines = (cm.get(fn) or {}).get(sym)
            if not lines and sym == "proc_stat" and fn == SETTLE:
                lines = (cm.get("ident_is_live_process") or {}).get(sym)
                if lines:
                    found.append(f"{fn} -> ident_is_live_process:{sym}@{lines[0]}")
                    continue
            if lines:
                shown = ",".join(str(n) for n in sorted(lines)[:3])
                found.append(f"{fn}:{sym}@{shown}" + ("+" if len(lines) > 3 else ""))
            else:
                problems.append(f"MISSING {fn}:{sym}")
        for fn, sym in forbidden:
            lines = (cm.get(fn) or {}).get(sym)
            if lines:
                problems.append(f"FORBIDDEN {fn}:{sym}@{lines[0]}")
        verdicts[gid] = (not problems, found, problems)
    return verdicts, cm


def teardown_order_ok(cm):
    """Guard 1's 're-measured AT ACT TIME': the idents are read BEFORE anything is killed, and the
    verification comes AFTER. A locator that only proved the three symbols exist would pass a
    sequence that measured the survivors after killing them."""
    seq = cm.get(SEQ) or {}
    measure = min(seq.get("pane_harness_idents", [10 ** 9]))
    kill = min(seq.get("tmux_kill_pane", [10 ** 9]) + seq.get("tmux_respawn_pane", [10 ** 9]))
    verify = max(seq.get("verify_pids_gone", [-1]))
    return measure < kill < verify, f"measured@{measure} < killed@{kill} < verified@{verify}"


# =================================================================================================
def main():
    # The split moved these guarded acts out of coord.py into its sibling files [D23,
    # T4-R12]. The product is coord.py PLUS everything it loads, and that is what the
    # locator has always been reading — the scan target moved, its logic did not.
    src = "\n".join([COORD_PY.read_text(encoding="utf-8")]
                   + [(KIT / f"{_n}.py").read_text(encoding="utf-8")
                      for _n in coord.SPLIT_MODULES])
    digest = hashlib.md5(src.encode()).hexdigest()
    print(f"\ncoord.py under test: {COORD_PY}\n  {len(src.splitlines())} lines · md5 {digest}")
    print(f"  LIFECYCLE_SETTLE_S={coord.LIFECYCLE_SETTLE_S}  "
          f"LIFECYCLE_STALE_MIN={coord.LIFECYCLE_STALE_MIN}  HARNESS_PROCS={coord.HARNESS_PROCS}")

    tmp = tempfile.mkdtemp(prefix="probe-lifecycle-idents-")
    try:
        # ---- PART 0 — ISOLATION. The probe must be unable to reach a live surface. -------------
        print("\nPART 0 — isolation: this probe cannot touch the live room.")
        check("0a the working package is a throwaway temp tree, not the vault's goals tree",
              tmp.startswith(tempfile.gettempdir())
              and ".rbtv/goals" not in tmp and str(KIT) not in tmp, tmp)
        check("0b the pane/agent environment is scrubbed, so nothing can inherit a live target",
              not any(os.environ.get(v) for v in
                      ("TMUX", "TMUX_PANE", "COORD_AGENT", "COORD_LAUNCH_TARGET", "COORD_PACKAGE")))
        refused = ""
        try:
            coord.live_panes()                      # the real one — every tmux read goes this way
        except _TmuxRefused as exc:
            refused = str(exc)
        check("0c NO tmux binary can be invoked: the sentinel refuses coord's own tmux argv",
              refused.startswith("the probe refuses to invoke tmux"), refused[:70])
        # The sentinel must not be a blanket ban — the reaper below is a REAL detached fork.
        check("0d ...while a non-tmux fork still runs (the reaper arms for real, not in effigy)",
              coord.subprocess.run([sys.executable, "-c", "print(1)"],
                                   capture_output=True, text=True).stdout.strip() == "1")

        # ---- PART 1 — THE CONSTRUCTED RECYCLED-PID CASE (spec §6(b)). ---------------------------
        print("\nPART 1 — the recycled-pid hazard: a live harness at a pid the ident does not own.")
        print("  SKIPPED, and reported as skipped rather than absent: the optional kernel-level arm")
        print("  (`unshare -rp --fork --mount-proc` + /proc/sys/kernel/ns_last_pid). It needs a")
        print("  private pid namespace; the hazard is constructed directly instead, which is msg")
        print("  #137's actual shape.")

        proc_a, ident_a = stub_harness(tmp, "a")
        if not ident_a:
            print("INOPERATIVE: the stub harness never appeared in /proc")
            return 2
        P, S = ident_a
        S_wrong = str(int(S) + 1)
        argv_a = cmdline(P)
        check("1.1 the stub is a real live process the kit reads as a harness",
              coord.is_harness_argv(argv_a) and coord.process_identity(P) == (P, S),
              f"pid {P} starttime {S} — {argv_a}")
        check("1.2 the predicate accepts the TRUE ident", coord.ident_is_live_harness((P, S)))
        check("1.3 ...and REFUSES the same pid with a wrong starttime — this is the whole guard",
              coord.ident_is_live_harness((P, S_wrong)) is False, f"({P}, {S_wrong})")
        check("1.4 the plain-process predicate refuses it too (the guard is not harness-specific)",
              coord.ident_is_live_process((P, S_wrong)) is False)

        script_wrong = coord.reaper_script([(P, S_wrong)], 1)
        check("1.5 the emitted reaper text names P:S_wrong and NOT P:S — pure, so checkable "
              "without arming anything",
              f"{P}:{S_wrong}" in script_wrong and f"{P}:{S}" not in script_wrong,
              script_wrong[:70] + "…")

        t0 = time.monotonic()
        survivors, note = coord.verify_pids_gone([(P, S_wrong)])
        check("1.6 the close path's in-process verifier reports NO survivors for the stale ident "
              "— it correctly sees nothing matching",
              survivors == [] and note == "", f"{time.monotonic() - t0:.2f}s, note={note!r}")

        coord.arm_pid_reaper([(P, S_wrong)], delay=1)
        time.sleep(3.5)
        check("1.7 ⚠ THE ROW THIS PROBE EXISTS FOR: the DETACHED reaper armed with the stale ident "
              "left the live process ALIVE",
              coord.ident_is_live_harness((P, S)) and coord.process_identity(P) == (P, S),
              f"pid {P} still holds starttime {S}")

        # RED ARM — acceptance 2. Without this, 1.6/1.7 are satisfied by a reaper that never fires.
        proc_b, ident_b = stub_harness(tmp, "b")
        if not ident_b:
            print("INOPERATIVE: the red-arm stub never appeared in /proc")
            return 2
        s_b, note_b = coord.verify_pids_gone([ident_b], timeout=0.0)
        red("the SAME in-process verifier, armed with the CORRECT ident, KILLS the process",
            s_b == [] and "reaped by signal" in note_b and dead(ident_b),
            f"pid {ident_b[0]} — {note_b or 'no escalation note'}")

        proc_c, ident_c = stub_harness(tmp, "c")
        if not ident_c:
            print("INOPERATIVE: the red-arm stub never appeared in /proc")
            return 2
        coord.arm_pid_reaper([ident_c], delay=1)
        red("the SAME detached reaper, armed with the CORRECT ident, KILLS the process",
            dead(ident_c, wait_s=8.0), f"pid {ident_c[0]}")
        check("1.8 and the first stub is STILL alive after both red arms — the reaper hit only "
              "what it owned",
              coord.ident_is_live_harness((P, S)))

        # ---- PART 2 — GUARD CONFORMANCE: the two predicates are not interchangeable. ------------
        print("\nPART 2 — the two predicates: the asymmetry guards 4, 5 and the staleness test rest on.")
        me = coord.process_identity(os.getpid())
        check("2.5a this probe's own python process is LIVE to ident_is_live_process",
              coord.ident_is_live_process(me) is True, f"{me}")
        check("2.5b ...and DEAD to ident_is_live_harness — is_harness_argv matches only "
              f"{'/'.join(coord.HARNESS_PROCS)}",
              coord.ident_is_live_harness(me) is False
              and coord.is_harness_argv(cmdline(os.getpid())) is False,
              cmdline(os.getpid())[:60])

        # 2.6 — the settle wait, at its REAL budget, inside the REAL executor.
        caller, caller_ident = stub_python_child(tmp)
        if not caller_ident:
            print("INOPERATIVE: the settle-wait caller child never appeared in /proc")
            return 2
        elapsed, entry, outcome = drive_close(tmp, "settle-live", caller_ident)
        steps = [str(s) for s in (entry.get("steps-completed") or [])]
        check("2.6a the executor's settle wait ACTUALLY WAITED on a live python caller and "
              "recorded `caller-still-live-after-settle`",
              bool(steps) and steps[0] == "caller-still-live-after-settle",
              f"{elapsed:.1f}s, outcome={outcome}, step0={steps[0] if steps else '(none)'!r}")
        check("2.6b ...for the FULL budget — a wait wired to the harness predicate returns at once",
              elapsed >= coord.LIFECYCLE_SETTLE_S, f"{elapsed:.1f}s >= {coord.LIFECYCLE_SETTLE_S}s")
        check("2.6c ...and the sequence PROCEEDED ANYWAY: it ran to completion and flipped the "
              "marker done",
              entry.get("state") == "done" and any("awaiting-and-closing-cleared" in s
                                                   for s in steps),
              f"{len(steps)} steps, state={entry.get('state')!r}")
        caller.kill()
        caller.wait()

        # The control that keeps 2.6 honest: a DEAD caller must reach the other outcome, fast.
        gone, gone_ident = stub_python_child(tmp)
        gone.kill()
        gone.wait()
        elapsed_d, entry_d, outcome_d = drive_close(tmp, "settle-dead", gone_ident)
        steps_d = [str(s) for s in (entry_d.get("steps-completed") or [])]
        check("2.6d control: a DEAD caller reaches the OTHER outcome immediately — the wait is "
              "not simply always-slow",
              bool(steps_d) and steps_d[0] == "caller-exited" and elapsed_d < 2.0,
              f"{elapsed_d:.1f}s, step0={steps_d[0] if steps_d else '(none)'!r}, {outcome_d}")

        # 2.7 — the staleness side of the same trap.
        stamp = coord.now()
        later = (datetime.now() + timedelta(minutes=coord.LIFECYCLE_STALE_MIN + 5)
                 ).strftime("%Y-%m-%d %H:%M")
        live_entry = {"state": "in-flight", "stamped-at": stamp,
                      "executor": {"pid": me[0], "starttime": me[1]}}
        dead_entry = {"state": "in-flight", "stamped-at": stamp,
                      "executor": {"pid": gone_ident[0], "starttime": gone_ident[1]}}
        check("2.7a an in-flight marker whose executor is a LIVE python process is NOT stale — "
              "that is MID-RENEWAL, and firing on it double-launches the seat",
              coord.lifecycle_stale(live_entry, later) is False)
        check("2.7b ...and the same marker IS stale once its executor is reaped",
              coord.lifecycle_stale(dead_entry, later) is True, f"executor pid {gone_ident[0]}")
        check("2.7c control: conjunct 2 is present — a young entry with a dead executor is not "
              "stale yet",
              coord.lifecycle_stale(dead_entry, stamp) is False)

        # ---- THE THREE MUTATIONS. One swap, three rows, three reds. ----------------------------
        print("\nPART 2 red arms — rewrite the predicate under test to the other one.")
        saved_pred = coord.ident_is_live_process
        try:
            coord.ident_is_live_process = coord.ident_is_live_harness
            red("[row 5] with the predicates swapped, the probe's own live process reads DEAD",
                coord.ident_is_live_process(me) is False)
            caller2, caller2_ident = stub_python_child(tmp)
            e2, entry2, _ = drive_close(tmp, "settle-mutant", caller2_ident)
            steps2 = [str(s) for s in (entry2.get("steps-completed") or [])]
            red("[row 6] ...the settle wait returns INSTANTLY and records `caller-exited` about a "
                "caller that is still running — the false entry this row exists to catch",
                bool(steps2) and steps2[0] == "caller-exited" and e2 < 2.0,
                f"{e2:.1f}s, step0={steps2[0] if steps2 else '(none)'!r}")
            caller2.kill()
            caller2.wait()
            red("[row 7] ...and a MID-RENEWAL marker reads STALE — Stage 4 would revive a seat "
                "whose renewal is in progress",
                coord.lifecycle_stale(live_entry, later) is True)
        finally:
            coord.ident_is_live_process = saved_pred
        check("2.8 the mutation is undone — the live predicate is restored",
              coord.ident_is_live_process is saved_pred
              and coord.ident_is_live_process(me) is True)

        # ---- PART 3 — THE SEVEN GUARDED ACTS, LOCATED IN THE SHIPPED CODE. ---------------------
        print("\nPART 3 — spec §4.1's seven guarded acts, located by symbol and line.")
        verdicts, cm = locate(src)
        for gid, act, _req, _forb in GUARDS:
            ok, found, problems = verdicts[gid]
            check(f"3.{gid} {act}", ok,
                  " · ".join(found) if ok else "; ".join(problems))
        ok_order, order_detail = teardown_order_ok(cm)
        check("3.order guard 1 re-measures BEFORE the kill and verifies AFTER it", ok_order,
              order_detail)

        # RED ARM — acceptance 4. A scratch copy, never the live file, never coord.py.
        scratch = Path(tmp) / "coord-scratch-noreaper.py"
        cut = re.sub(r"\n\s*arm_pid_reaper\(old_idents\)", "\n        pass", src, count=1)
        check("3.red-setup the scratch mutant actually differs from the shipped file",
              cut != src and "arm_pid_reaper(old_idents)" not in cut)
        scratch.write_text(cut)
        v_cut, _ = locate(scratch.read_text())
        red("deleting guard 3's call site in a SCRATCH copy makes the locator report it MISSING",
            v_cut["3"][0] is False and any("MISSING" in p for p in v_cut["3"][2]),
            "; ".join(v_cut["3"][2]))

        scratch2 = Path(tmp) / "coord-scratch-wrongpredicate.py"
        # The MINIMAL mutation — the settle wait's ONE call site, nothing else. A block-wide
        # replace would also rewrite the docstring that warns against this very swap, and the
        # locator reads calls, not prose: the red would then be over-determined.
        needle = "        if not ident_is_live_process(caller):"
        swapped = src.replace(needle, "        if not ident_is_live_harness(caller):", 1)
        diff_lines = [i for i, (a, b) in enumerate(zip(src.splitlines(), swapped.splitlines()))
                      if a != b]
        check("3.red-setup2 the second scratch mutant changes EXACTLY ONE line — the settle "
              "wait's own call site",
              src.count(needle) == 1 and len(diff_lines) == 1
              and len(src.splitlines()) == len(swapped.splitlines()),
              f"line {diff_lines[0] + 1 if diff_lines else '(none)'}")
        scratch2.write_text(swapped)
        v_sw, _ = locate(scratch2.read_text())
        red("wiring the settle wait to the HARNESS predicate in a scratch copy reddens guard 4",
            v_sw["4"][0] is False and any("FORBIDDEN" in p for p in v_sw["4"][2]),
            "; ".join(v_sw["4"][2]))

        # ---- The file itself must be runnable as advertised. -----------------------------------
        print("\nPART 4 — the probe's own contract.")
        own = Path(__file__).resolve()
        check("4a the probe carries a python3 shebang",
              own.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"))
        check("4b ...and is executable", os.access(own, os.X_OK), oct(own.stat().st_mode & 0o777))
        # 4c — what part 3 measured must still hold of the file on disk. It used to assert the
        # digest was UNCHANGED, which encodes a premise this box breaks: autonomous seats edit
        # coord.py live through `save-coord.py`'s atomic `os.replace`, and one landing inside the
        # ~19s window failed the run for a reason that was never a defect. The probe holds no
        # writable handle to coord.py (every write above goes under `tmp`), so it is never the
        # author of such a move. So: same bytes -> nothing to re-prove; different bytes -> RE-RUN
        # the locator against the CURRENT file. That keeps both halves of the old coverage — the
        # freshness of part 3's verdict, and the refusal to accept a damaged coord.py (either
        # scratch mutant reddens guard 3 or guard 4 here) — without the byte-static premise.
        after_src = "\n".join([COORD_PY.read_text(encoding="utf-8")]
                           + [(KIT / f"{_n}.py").read_text(encoding="utf-8")
                              for _n in coord.SPLIT_MODULES])
        after = hashlib.md5(after_src.encode()).hexdigest()
        if after == digest:
            check("4c coord.py is byte-identical to the snapshot part 3 measured", True, digest)
        else:
            print(f"  NOTE  coord.py moved under this run ({digest} -> {after}) — an external "
                  "writer, not this probe. Re-locating the seven guarded acts against it.")
            try:
                v2, cm2 = locate(after_src)
                bad = [gid for gid, *_ in GUARDS if not v2[gid][0]]
                ok2 = not bad and teardown_order_ok(cm2)[0]
                why = f"failing guards {bad}" if bad else "teardown order" if not ok2 else ""
            except SyntaxError as exc:
                ok2, why = False, f"current coord.py does not parse: {exc}"
            check("4c coord.py moved under this run — the seven guarded acts still locate in the "
                  "CURRENT file", ok2, f"{digest} -> {after}" + (f"; {why}" if why else ""))
    finally:
        for p in PROCS:
            try:
                p.kill()
                p.wait(timeout=3)
            except Exception:                                          # noqa: BLE001
                pass
        # The stubs are reaped FIRST, then the tree they ran out of — deleting a running stub's
        # script would leave the process alive with no /proc cmdline to identify it by.
        shutil.rmtree(tmp, ignore_errors=True)

    total = len(PASSED) + len(FAILED)
    print(f"\nCHECKS {len(PASSED)}/{total}   RED ARMS {sum(1 for _, r in REDS if r)}/{len(REDS)}")
    print("SKIPPED (never counted as a pass): the kernel-level ns_last_pid recycle (part 1).")
    if FAILED:
        print("FAILED: " + "; ".join(FAILED))
        return 1
    if len(PASSED) < 34:
        print(f"INOPERATIVE: only {len(PASSED)} checks ran; this probe asserts at least 34")
        return 2
    if len(REDS) < 7 or not all(r for _, r in REDS):
        print("INOPERATIVE: a red arm did not run or did not go red — every green above is vacuous")
        return 2
    return 0


def stub_python_child(workdir):
    """A plain python sleeper — the shape of the executor's forking CALLER. Deliberately NOT a
    harness: that is the asymmetry rows 5-7 turn on. Returns (proc, (pid, starttime))."""
    script = Path(workdir) / "caller.py"
    if not script.exists():
        script.write_text("import time\ntime.sleep(3600)\n")
    proc = real_subprocess.Popen([sys.executable, str(script)],
                                 stdout=real_subprocess.DEVNULL, stderr=real_subprocess.DEVNULL)
    PROCS.append(proc)
    # Same race as `stub_harness`, INVERTED and therefore worse: /proc/<pid>/stat exists from the
    # FORK, /proc/<pid>/cmdline only from the EXEC, so gating on the ident alone hands back a pid
    # whose argv is still ZERO BYTES — and `is_harness_argv("")` is False, which is the answer rows
    # 5-7 want. The negative then PASSES FOR THE WRONG REASON: it cannot tell "this caller is
    # correctly not a harness" from "argv has not materialized yet", and never fails, because the
    # bug makes it pass. Wait for the observable "exec happened" — a NON-EMPTY cmdline, not a
    # python-shaped one, so the consuming predicate is still free to fail.
    for _ in range(100):
        ident = coord.process_identity(proc.pid)
        if ident and cmdline(proc.pid):
            return proc, ident
        time.sleep(0.05)
    return proc, None


if __name__ == "__main__":
    sys.exit(main())
