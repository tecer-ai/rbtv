#!/usr/bin/env python3
"""probe-lifecycle-exec.py — the DETACHED `lifecycle-exec` fire, at its CURRENT caller.

REPOINTED BY TASK 7.35 (Phase B), not deleted. It used to reach `lifecycle-exec` through
`watch.py`'s `fire_revival`. Owner ruling `decisions.md#d-seat-revival-kept-in-watcher-job` moved
the seat-revival actuator into `ignite/jobs/goal-watcher-job.py`, which fires it through
`jobcontain.detach_argv` -> a real `systemd-run` transient unit (`run_revival`, task 7.662), and
7.35 deletes the old caller. So the exec door has ONE non-probe caller and this probe follows it
there. `coord.py`'s Stage-3 lifecycle machinery is UNCHANGED and is deliberately not touched here:
it serves this live path.

WHY IT HAD TO MOVE. Until the Phase-A dispatch measured it by hand, NO probe on ANY host had ever
driven `run_revival`'s real launch — the only existing arm (`probe-goal-watcher-revival` R3) drives
the REFUSED allowlist branch and never fires. An actuator whose fire path is unexercised is an
actuator nobody can say works.

⚠ WHAT MAKES THE GREEN A MEASUREMENT. P2 is a NEGATIVE CONTROL: the same real `run_revival`, the
same real `systemd-run`, against a target that EXITS 1. The unit must report that failure rather
than swallowing it. Without it, P1's `Result=success` is a default, not a reading.

ISOLATION, and it is a safety property. A throwaway unit prefix that cannot collide with a live
`rbtv-revival-*`; a scratch goal tree under a temp dir; a THROWAWAY program that merely passes the
REAL allowlist by basename (no monkeypatch of the gate, and the live `coord.py` is never invoked).
No live goal, room, daemon or systemd unit is touched, and every unit made here is torn down and
`reset-failed` at the end.

  python3 probes/probe-lifecycle-exec.py
Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE (no `systemd-run`/user manager here).
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "jobs" / "goal-watcher-job.py"
OUT = HERE / "probe-lifecycle-exec.out"
PREFIX = "rbtv-p735lc-revival"          # cannot collide with a live `rbtv-revival-*`

lines, failures, inoperative = [], [], []
made_units = []


def check(tag, ok, detail):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    lines.append(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def show(unit, *props):
    r = subprocess.run(["systemctl", "--user", "show", unit,
                        *[f"--property={p}" for p in props]],
                       capture_output=True, text=True)
    return dict(ln.split("=", 1) for ln in r.stdout.splitlines() if "=" in ln)


def journal(unit, timeout=30, want=None):
    """The unit's OWN journal, waited for. THE READING IS TAKEN HERE, NOT FROM `systemctl show`.

    `jobcontain.detach_argv` passes `--collect`, so a transient unit is REMOVED the moment it
    finishes — including when it FAILS. `systemctl show` on a removed unit answers with defaults
    (`ActiveState=inactive Result=success`), so a failed run and a vanished one are BYTE-IDENTICAL
    there and the negative control read `success` for a target that exited 1. Measured, 2026-08-10.
    The journal persists past the collection, so it is the surface that can tell them apart."""
    deadline = time.time() + timeout
    out = ""
    while time.time() < deadline:
        out = subprocess.run(["journalctl", "--user", "-u", unit, "--no-pager", "-o", "cat"],
                             capture_output=True, text=True).stdout
        if "Deactivated successfully" in out or "Failed with result" in out or                 "Main process exited" in out or (want and want in out):
            return out
        time.sleep(0.3)
    return out


def program(dirpath, name, body):
    """A THROWAWAY program whose BASENAME is what the real allowlist gates on."""
    p = Path(dirpath) / name
    p.write_text(body, encoding="utf-8")
    return p


def main():
    if not TARGET.exists():
        # NOT a skip: the caller's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist — `lifecycle-exec` has no caller at all")
        return
    for tool in ("systemd-run", "systemctl"):
        if not any((Path(d) / tool).exists() for d in os.environ.get("PATH", "").split(os.pathsep)
                   if d):
            stop("C0", f"no `{tool}` on PATH — the detached fire cannot be driven here")
            return
    if subprocess.run(["systemctl", "--user", "is-system-running"],
                      capture_output=True, text=True).returncode not in (0, 1):
        stop("C0", "no reachable systemd --user manager — the detached fire cannot be driven here")
        return

    spec = importlib.util.spec_from_file_location("gwj_lc", TARGET)
    gwj = importlib.util.module_from_spec(spec)
    sys.modules["gwj_lc"] = gwj
    spec.loader.exec_module(gwj)

    for name in ("run_revival", "revival_argv"):
        if not hasattr(gwj, name):
            check("C0", False, f"this tree's watcher job has no `{name}` — the revival actuator "
                               f"is not here, so `lifecycle-exec` has no live caller")
            return

    with tempfile.TemporaryDirectory() as td:
        marker = Path(td) / "TARGET-RAN.txt"
        # The basename is `coord.py` ON PURPOSE: it is what `_inline_fix_program`'s REAL allowlist
        # gates on, so the gate is passed rather than patched. The BODY is a throwaway.
        ok_prog = program(td, "coord.py",
                          "import os, sys, pathlib\n"
                          f"pathlib.Path({str(marker)!r}).write_text("
                          "f'pid={os.getpid()} ppid={os.getppid()} argv={sys.argv[1:]}\\n')\n")
        bad_prog = program(td, "coord.py.bad",
                           "import sys\nsys.stderr.write('deliberate failure\\n')\nsys.exit(1)\n")
        fail_prog = program(td, "team_monitor.py",
                            "import sys\nsys.stderr.write('deliberate failure\\n')\n"
                            "sys.exit(1)\n")

        # ---- C0 / P4: the ARGV tail that reaches the exec door.
        class _A:
            package = str(Path(td) / "goals" / "zz-p735")
        tail = gwj.revival_argv(_A(), "zz-seat", "%99", "zz-room:0.0", (os.getpid(), "0"))
        check("C0", tail[:1] == ["lifecycle-exec"]
              and "revive" in tail and "--handoff-written" in tail
              and not [t for t in tail if t.startswith("--force")],
              f"the tail is the exec door's own verb and carries no `--force` of any kind: "
              f"{tail[:6]}…")

        # ---- P1: THE FIRE. Real run_revival, real systemd-run, real detachment.
        unit1 = f"{PREFIX}-ok-{os.getpid()}"
        made_units.append(unit1)
        outcome, why = gwj.run_revival(str(ok_prog), tail, unit1)
        log1 = journal(unit1, want="Deactivated") if outcome == "FIRED" else ""
        ran = marker.exists()
        body = marker.read_text(encoding="utf-8") if ran else ""
        detached = False
        if ran:
            ppid = body.split("ppid=")[1].split()[0]
            # The child's parent is the systemd USER MANAGER, never this process — the whole
            # property `jobcontain.detach_argv` exists for, and it had never been probed.
            detached = ppid != str(os.getpid())
        clean1 = "Failed with result" not in log1 and "status=1/FAILURE" not in log1
        check("P1", outcome == "FIRED" and ran and detached and "Started" in log1 and clean1,
              f"run_revival -> {outcome} ({why[:60]}…); the target really ran (marker="
              f"{ran}), OUTSIDE this process (detached={detached}), and its unit journal records "
              f"a start with NO failure line (clean={clean1})")

        # ---- P2: THE NEGATIVE CONTROL. Same path, a target that fails.
        unit2 = f"{PREFIX}-fail-{os.getpid()}"
        made_units.append(unit2)
        out2, why2 = gwj.run_revival(str(fail_prog), tail, unit2)
        log2 = journal(unit2, want="Failed with result") if out2 == "FIRED" else ""
        check("P2", out2 == "FIRED" and "status=1/FAILURE" in log2
              and "Failed with result" in log2,
              f"a target that EXITS 1 is REPORTED by its unit, not swallowed: {out2}; journal "
              f"carries {[l for l in log2.splitlines() if 'result' in l or 'FAILURE' in l][-1:]}. "
              f"This is what makes P1's clean journal a reading rather than a default")

        # ---- P3: the allowlist still REFUSES, and refuses BEFORE anything starts.
        unit3 = f"{PREFIX}-refused-{os.getpid()}"
        out3, why3 = gwj.run_revival(str(bad_prog), tail, unit3)
        started = show(unit3, "LoadState").get("LoadState")
        check("P3", out3 == "REFUSED" and started in (None, "not-found"),
              f"a program outside the allowlist -> {out3} ({why3[:60]}…) and NO unit was created "
              f"(LoadState={started!r}) — the refusal is before the launch, never after it")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")
finally:
    for u in made_units:
        subprocess.run(["systemctl", "--user", "stop", u], capture_output=True)
        subprocess.run(["systemctl", "--user", "reset-failed", u], capture_output=True)

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-lifecycle-exec  ({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
