#!/usr/bin/env python3
"""probe-jobcontain-degrade.py — jobcontain's POSIX containment is REAL on Linux, LOUDLY OFF when absent (7.715).

WHAT IT SCORES. `jobcontain.py` moved `fcntl`/`resource` from module scope into the three functions
that need them (`contain`, `child_preexec`, `single_instance`), keyed on the import FAILING — so the
four job scripts that import it now LOAD on a non-POSIX host, while their containment ACTIONS stay
POSIX-only. The failure mode this guards against is a jobcontain that loads on Windows and then
silently runs on the Linux SERVER with its double-run lock and memory cap switched off. Both halves
are measured against the REAL module, never a stub of it:

  P1  ON POSIX THE LOCK IS REAL: with `fcntl` importable, `single_instance()` grants the first
      holder and REFUSES the second (returns None). This is the arm a no-op mutation reddens.
  P2  ABSENT, IT DEGRADES LOUD, NOT SILENT: with `fcntl` forced out of `sys.modules`,
      `single_instance()` takes the degraded path — returns a usable handle (the job proceeds) AND
      writes the one-line "fcntl unavailable — NO double-run lock" warning to stderr; a SECOND call
      is ALSO granted, proving the lock is genuinely off rather than merely quiet.
  P3  THE MEMORY CAP DEGRADES THE SAME WAY: with `resource` forced absent, `contain()` returns
      without raising and warns once on stderr.

RED-FIRST. `RBTV_PROBE_TREE` re-points TARGET at another tree's `jobcontain.py`. Pointed at a tree
where `single_instance` was mutated to skip the `flock`, P1 goes red (the second holder is granted)
while P2/P3 stay green — which is what makes the green run a measurement, not a restatement.

⚠ AN ABSENT/UNIMPORTABLE TARGET IS THE FAILURE, NEVER A SKIP. Run it through the suite —
`node ignite/deploy/probe-suite.js --only jobcontain-degrade` — never by hand (`G-163`).
Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import importlib.util
import io
import os
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
# HERE = <root>/ignite/jobs/probes -> parents[2] is the rbtv repo root. `RBTV_PROBE_TREE` is the
# RED-FIRST knob (see the docstring): it re-points TARGET at another tree's source.
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "runtime" / "jobs" / "jobcontain.py"
OUT = HERE / "probe-jobcontain-degrade.out"

lines, failures, inoperative = [], [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def stop(tag, detail):
    say(f"INOP  {tag}  {detail}")
    inoperative.append(tag)


def load_target():
    # Fresh module object each call so a forced-absent fcntl/resource is re-evaluated by the
    # function-scope import, never served from a prior load's cache.
    sys.modules.pop("jobcontain_under_probe", None)
    spec = importlib.util.spec_from_file_location("jobcontain_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def block(name):
    """Force `import <name>` to raise ImportError — the exact condition a non-POSIX host presents."""
    sys.modules[name] = None


def unblock(name):
    sys.modules.pop(name, None)


def call_capturing_stderr(fn, *a, **k):
    buf = io.StringIO()
    saved, sys.stderr = sys.stderr, buf
    try:
        return fn(*a, **k), buf.getvalue()
    finally:
        sys.stderr = saved


def main():
    if not TARGET.exists():
        check("P1", False, f"{TARGET} does not exist — nothing to measure")
        return

    with tempfile.TemporaryDirectory(prefix="jobcontain-probe-") as d:
        # ---- P1: on POSIX, the lock is REAL — first holder granted, second REFUSED.
        try:
            import fcntl  # noqa: F401 — availability check for THIS host
            have_fcntl = True
        except ImportError:
            have_fcntl = False
        if not have_fcntl:
            stop("P1", "fcntl does not import on this host — the real-lock arm cannot run here "
                       "(run the suite on the VPS, G-163)")
        else:
            unblock("fcntl")
            jc = load_target()
            lock = os.path.join(d, "p1.lock")
            first = jc.single_instance(lock)
            second = jc.single_instance(lock)
            check("P1", first is not None and second is None,
                  f"first holder granted ({first is not None}); second holder refused "
                  f"({second is None})")

        # ---- P2: with fcntl absent, degrade LOUD — proceed, warn once, and the lock is really off.
        block("fcntl")
        try:
            jc = load_target()
            lock = os.path.join(d, "p2.lock")
            first, err = call_capturing_stderr(jc.single_instance, lock)
            second, _ = call_capturing_stderr(jc.single_instance, lock)
            check("P2", first is not None and second is not None
                  and "fcntl unavailable" in err and "NO double-run lock" in err,
                  f"granted with no lock (first={first is not None}, second={second is not None}); "
                  f"warning={err.strip()!r}")
        finally:
            unblock("fcntl")

        # ---- P3: with resource absent, contain() degrades without raising and warns once.
        block("resource")
        try:
            jc = load_target()
            ret, err = call_capturing_stderr(jc.contain, 256, 600)
            check("P3", ret is None and "resource unavailable" in err,
                  f"contain() returned {ret!r} without raising; warning={err.strip()!r}")
        except Exception as exc:  # noqa: BLE001
            check("P3", False, f"contain() raised instead of degrading: {type(exc).__name__}: {exc}")
        finally:
            unblock("resource")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-jobcontain-degrade  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
