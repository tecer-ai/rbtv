#!/usr/bin/env python3
"""probe-nudge-degrade.py — nudge.py LOADS anywhere; its single-loop lock is REAL on POSIX and
LOUDLY off where `fcntl` is absent.

WHAT IT SCORES. `nudge.py` had `import fcntl` at module scope, so on a non-POSIX host `import
nudge` died before a line of its own code ran — the same defect class 7.715 fixed in
`runtime/jobs/jobcontain.py`. The import now lives inside `main()`'s lock block, keyed on the import
FAILING (never on a platform name). The failure mode guarded against is the opposite of the first
one: a nudge that loads on Windows and then runs on the Linux box with its single-loop lock quietly
switched off, two loops sharing a heartbeat and destroying the gap signal. Both halves are measured
against the REAL module, never a stub:

  P1  IT LOADS WITH fcntl ABSENT: with `fcntl` forced out of `sys.modules`, the module executes.
      This is the arm the pre-fix source reddens (ModuleNotFoundError at exec time).
  P2  ON POSIX THE LOCK IS REAL: with `fcntl` importable and a SECOND process-level holder already
      flocking `<heartbeat>.lock`, `main()` REFUSES with exit code 3. INOPERATIVE where `fcntl`
      does not import (run the suite on the VPS, G-163).
  P3  ABSENT, IT DEGRADES LOUD, NOT SILENT: with `fcntl` forced absent, `main()` proceeds (exit 0)
      even against that same held lock — proving the lock is genuinely OFF rather than merely
      quiet — AND writes the one-line "fcntl unavailable — NO single-loop lock" warning to stderr.

RED-FIRST. `RBTV_PROBE_TREE` re-points TARGET at another tree's `ignite/coord/nudge.py`.
Pointed at the pre-fix source, P1 goes red.

⚠ AN ABSENT/UNIMPORTABLE TARGET IS THE FAILURE, NEVER A SKIP. Run it through the suite —
`node ignite/deploy/probe-suite.js --only nudge-degrade` — never by hand (`G-163`).
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
# HERE = <root>/ignite/coord/probes -> parents[2] is the rbtv repo root. `RBTV_PROBE_TREE` is
# the RED-FIRST knob (see the docstring): it re-points TARGET at another tree's source.
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "coord" / "nudge.py"
OUT = HERE / "probe-nudge-degrade.out"

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
    # Fresh module object each call so a forced-absent fcntl is re-evaluated by the function-scope
    # import, never served from a prior load's cache.
    sys.modules.pop("nudge_under_probe", None)
    spec = importlib.util.spec_from_file_location("nudge_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def block(name):
    """Force `import <name>` to raise ImportError — the exact condition a non-POSIX host presents."""
    sys.modules[name] = None


def unblock(name):
    sys.modules.pop(name, None)


def call_capturing(fn, *a, **k):
    """Run fn with BOTH streams captured — a nudge tick prints its message to stdout."""
    err, out = io.StringIO(), io.StringIO()
    saved_e, saved_o = sys.stderr, sys.stdout
    sys.stderr, sys.stdout = err, out
    try:
        return fn(*a, **k), err.getvalue()
    finally:
        sys.stderr, sys.stdout = saved_e, saved_o


def run_argv(mod, pkg, hb):
    return mod.main(["run", "--package", str(pkg), "--to", "probe-seat",
                     "--transport", "stdout", "--once", "--heartbeat", str(hb)])


def hold_lock(hb):
    """Take the exclusive flock a rival nudge loop would hold. None where fcntl is absent."""
    import fcntl
    fh = open(str(hb) + ".lock", "w", encoding="utf-8")
    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return fh


def main():
    if not TARGET.exists():
        check("P1", False, f"{TARGET} does not exist — nothing to measure")
        return

    with tempfile.TemporaryDirectory(prefix="nudge-probe-") as d:
        pkg = Path(d) / "pkg"
        (pkg / "coordination").mkdir(parents=True)

        # ---- P1: with fcntl absent the module still LOADS. The pre-fix source dies here.
        block("fcntl")
        try:
            nudge = load_target()
            check("P1", True, f"module executed with fcntl absent ({nudge.__name__})")
        except Exception as exc:  # noqa: BLE001
            check("P1", False, f"module failed to load with fcntl absent: "
                               f"{type(exc).__name__}: {exc}")
            unblock("fcntl")
            return
        finally:
            unblock("fcntl")

        try:
            import fcntl  # noqa: F401 — availability check for THIS host
            have_fcntl = True
        except ImportError:
            have_fcntl = False

        # ---- P2: on POSIX the lock is REAL — a second loop against a held lock is REFUSED.
        hb = pkg / "coordination" / "hb.jsonl"
        if not have_fcntl:
            stop("P2", "fcntl does not import on this host — the real-lock arm cannot run here "
                       "(run the suite on the VPS, G-163)")
            holder = None
        else:
            holder = hold_lock(hb)
            nudge = load_target()
            rc, err = call_capturing(run_argv, nudge, pkg, hb)
            check("P2", rc == 3 and "refused" in err,
                  f"second loop refused (rc={rc}); stderr={err.strip()!r}")

        # ---- P3: with fcntl absent, degrade LOUD — proceed against the SAME held lock, warn once.
        hb3 = pkg / "coordination" / "hb3.jsonl"
        holder3 = hold_lock(hb3) if have_fcntl else None
        block("fcntl")
        try:
            nudge = load_target()
            rc, err = call_capturing(run_argv, nudge, pkg, hb3)
            check("P3", rc == 0 and "fcntl unavailable" in err
                  and "NO single-loop lock" in err,
                  f"granted with no lock (rc={rc}, rival holder="
                  f"{'held' if holder3 else 'n/a — no fcntl on this host'}); "
                  f"warning={err.strip()!r}")
        finally:
            unblock("fcntl")
            for fh in (holder, holder3):
                if fh is not None:
                    fh.close()


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-nudge-degrade  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
