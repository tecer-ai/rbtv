#!/usr/bin/env python3
"""probe-jobcontain-uncapped.py — `contain()` KILLS node in a child; `uncapped()` lifts it, scoped.

WHAT IT SCORES, and why it exists at all. `jobcontain.contain()` caps this process's `RLIMIT_AS`,
and RLIMIT_AS is INHERITED. A child THIS SCRIPT EXECS is exempted by `child_preexec`, but a helper
called IN-PROCESS spawns its own child, which is not. node is fatal under a 256 MB cap: V8 RESERVES
gigabytes of VIRTUAL address space at startup and aborts with SIGTRAP before running any JS.

That is not hypothetical. `goal-watcher-job.py` calls `coord.derive_lease()` -> `server/lease/
lease.js`; under `contain(mem_mb=256)` node died with signal 5, the lease read as `unreadable
(exit -5)`, and the job REFUSED TO START on every fire from 2026-08-11T04:13Z to 2026-08-15T14:48Z —
200+ consecutive failures reporting IGNORANCE about a lease that reads fine from a shell.

Three arms, and the CONTROL is what makes the green one a measurement:

  U1  CONTROL — under `contain()`, a plain `node -e` child is KILLED BY A SIGNAL (negative
      returncode). If this arm ever goes green the hazard is gone on this host and U2 proves
      nothing; it would then be INOPERATIVE, not a pass.
  U2  INSIDE `uncapped()`, the same node child EXITS 0. This is the arm the fix owns.
  U3  AFTER the block, the cap is BACK — node is killed again. The lift is scoped to the block,
      not a permanent un-containment.

RED-FIRST. `RBTV_PROBE_TREE` re-points TARGET at another tree's `jobcontain.py`. Pointed at a tree
where `uncapped()` is mutated to a no-op context manager, U2 goes red while U1/U3 stay green.

⚠ Run it through the suite — `node ignite/deploy/probe-suite.js --only jobcontain-uncapped` — never
by hand (`G-163`). POSIX + node only; either absent is INOPERATIVE, never a skip.
Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[3])
TARGET = ROOT / "ignite" / "runtime" / "jobs" / "jobcontain.py"
OUT = HERE / "probe-jobcontain-uncapped.out"

lines, failures, inoperative = [], [], []


def check(tag, ok, detail):
    lines.append(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    lines.append(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def run_node():
    """(returncode, note) for a trivial node child. A signal death is a NEGATIVE returncode."""
    r = subprocess.run([NODE, "-e", "process.stdout.write('ok')"],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, (r.stdout or r.stderr or "").strip()[:80]


def main():
    if not TARGET.exists():
        return stop("PROBE", f"{TARGET} does not exist — nothing to measure")
    try:
        import resource  # noqa: F401 — availability check for THIS host
    except ImportError:
        return stop("PROBE", "resource does not import on this host — contain() is a no-op here "
                             "and all three arms would be vacuous (run on the VPS, G-163)")
    if not NODE:
        return stop("PROBE", "node is not on PATH — the hazard this probe measures cannot be shown")

    spec = importlib.util.spec_from_file_location("jobcontain_under_probe", TARGET)
    jc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(jc)

    # The alarm is deliberately short: nothing here should take a minute, and a hung arm must not
    # sit in the suite for contain()'s 600 s default.
    jc.contain(mem_mb=256, seconds=120)

    rc, note = run_node()
    if rc >= 0:
        return stop("U1", f"node SURVIVED the 256 MB cap (rc={rc}, {note!r}) — the hazard is absent "
                          f"on this host, so U2 could not distinguish a fix from a no-op")
    check("U1", True, f"CONTROL: node killed by signal {-rc} under contain(256MB)")

    with jc.uncapped():
        rc, note = run_node()
    check("U2", rc == 0, f"inside uncapped(): node rc={rc} out={note!r}")

    rc, _ = run_node()
    check("U3", rc < 0, f"after the block the cap is back: node rc={rc} "
                        f"({'killed again' if rc < 0 else 'STILL UNCAPPED — the lift leaked'})")


NODE = shutil.which("node")

try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-jobcontain-uncapped  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
