#!/usr/bin/env python3
"""probe-team-monitor-homings.py — the two behaviours task 7.35 moved INTO the surviving sensor.

WHAT IT SCORES. `watch.py` is deleted by 7.35 and two of its behaviours were ruled HOME here
(owner ratification of the Phase-A dossier, run decision D7):

  B2   the /tmp uid-QUOTA CANARY — `watch.py:282-385`. It exists because `df`/`statvfs` read
       775 MB free on `/tmp` at the SAME instant a 1 KB uid-1000 write failed EDQUOT: the per-uid
       quota sits BELOW the tmpfs size, so a free-space threshold — however configured — is
       STRUCTURALLY blind to this edge. Only a real write can see it. Deleting it without a home
       would leave `budget.json`'s `floors.tmp_free_warn_mb` naming a binding probe that no longer
       exists, and the box's only detector of a failure that has already fired here once.
  B22  the IGNORANCE ESCALATION'S BUS HALF — `watch.py:_escalate_unreadable`. Its twin
       (`escalate_relaunch_exhausted`) was restored in Phase A; this one was left behind by 7.664
       and the asymmetry was an accident of that change, not a decision. A sensor that runs
       DETACHED escalating only to a stderr nobody tails has not escalated.

RED-FIRST. `RBTV_PROBE_TREE` re-points every arm at another rbtv repo root. Pointed at a tree from
before this change, every arm below goes red while C0 stays green — which is what makes the green
run a measurement rather than a restatement.

FIXTURE-DRIVEN (run decision D4). The canary arms drive the REAL function with `open` replaced in
the module's own namespace, so all three of its outcomes are reachable on a healthy box: a probe
that could only observe "the write succeeded" would pass identically over a canary that cannot
report a refusal at all — which is the detector-that-dies-with-its-condition shape this behaviour
was written against.

ARMS
  C0   THE TARGET IS REAL: the module loads and still publishes a box section.
  B2-FIELD    `box_facts()` carries a `tmp_quota` field with the canary's three keys.
  B2-REFUSED  an EDQUOT and an ENOSPC from the write are reported as REFUSED (the quota signal),
              and are NEVER raised out of the function.
  B2-OTHER    any OTHER OSError is `refused=None` — a DIFFERENT failure, never collapsed into the
              quota edge, which is what keeps a permissions problem from reading as exhaustion.
  B22-BUS     `escalate_unreadable` puts the escalation on the coordination BUS as an `ask`, and a
              bus that cannot be written is REPORTED rather than raised — the loop may never die
              of its own complaint.

Run it through the suite — `node ignite/deploy/probe-suite.js --only team-monitor-homings`.
Exit 0 = green · 1 = a property is broken · 2 = INOPERATIVE.
"""

import errno
import importlib.util
import os
import sys
import tempfile
import time
from pathlib import Path

for _v in ("TMUX", "TMUX_PANE"):
    os.environ.pop(_v, None)

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "orchestration" / "team-monitor" / "tool" / "team_monitor.py"
OUT = HERE / "probe-team-monitor-homings.out"

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
    spec = importlib.util.spec_from_file_location("tm_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["tm_under_probe"] = mod
    spec.loader.exec_module(mod)
    return mod


class _Raiser:
    """`open` replaced in the module's OWN namespace — the laziest way to reach the two branches
    a healthy box cannot produce, and it exercises the REAL function rather than a copy of it."""

    def __init__(self, eno):
        self.eno = eno

    def __call__(self, *a, **kw):
        raise OSError(self.eno, os.strerror(self.eno))


def main():
    if not TARGET.exists():
        # NOT a skip: the target's absence IS a failure of the property under test.
        check("C0", False, f"{TARGET} does not exist")
        return
    tm = load_target()

    box = tm.box_facts()
    check("C0", isinstance(box, dict) and "available_mb" in box,
          f"the module loads and still publishes a box section "
          f"({len(box)} field(s), available_mb={box.get('available_mb')})")

    # ---- B2-FIELD: the canary reaches the published snapshot, not just the module.
    q = box.get("tmp_quota")
    check("B2-FIELD", isinstance(q, dict) and set(q) == {"refused", "errno", "trend_mb"}
          and q["refused"] is False,
          f"box.tmp_quota={q!r} — the canary is a PUBLISHED box fact, and a real write on this "
          f"box was not refused")

    gauge = getattr(tm, "tmp_quota_gauge", None)
    writer = getattr(tm, "tmp_canary_write", None)
    if gauge is None or writer is None:
        check("B2-REFUSED", False, "this tree carries no `tmp_canary_write`/`tmp_quota_gauge` — "
                                   "the uid-quota edge has NO detector on this box")
        check("B2-OTHER", False, "no canary to classify")
    else:
        real_open = getattr(tm, "open", None)
        got = {}
        try:
            for label, eno in (("EDQUOT", errno.EDQUOT), ("ENOSPC", errno.ENOSPC),
                               ("EACCES", errno.EACCES)):
                tm.open = _Raiser(eno)
                got[label] = gauge()
        finally:
            if real_open is None:
                tm.__dict__.pop("open", None)
            else:
                tm.open = real_open

        check("B2-REFUSED",
              got["EDQUOT"]["refused"] is True and got["EDQUOT"]["errno"] == errno.EDQUOT
              and got["ENOSPC"]["refused"] is True,
              f"a write refused with EDQUOT -> {got['EDQUOT']!r}; with ENOSPC -> refused="
              f"{got['ENOSPC']['refused']}. Neither RAISED: the detector reports its own "
              f"condition instead of dying of it")
        check("B2-OTHER", got["EACCES"]["refused"] is None
              and got["EACCES"]["errno"] == errno.EACCES,
              f"a DIFFERENT OSError -> {got['EACCES']!r} — reported as its own errno and never "
              f"as the quota edge, so a permissions fault cannot read as exhaustion")

    # ---- B22: the ignorance escalation lands on the BUS.
    esc = getattr(tm, "escalate_unreadable", None)
    if esc is None:
        check("B22-BUS", False, "this tree carries no `escalate_unreadable` — the ignorance "
                                "bound escalates to a detached stderr and nowhere else, while "
                                "its designed twin escalates to the bus")
        return
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "goals" / "zz-b22"
        (pkg / "coordination").mkdir(parents=True)
        msgs = pkg / "coordination" / "messages.md"
        esc(str(pkg), "zz-room", 5)
        body = msgs.read_text(encoding="utf-8") if msgs.exists() else ""
        # A bus that cannot be written must be REPORTED, never raised: the loop may not die of
        # its own complaint. Driven, not reasoned about — the package below has no `coordination`.
        raised = ""
        try:
            esc(str(Path(td) / "no" / "such" / "package"), "zz-room", 5)
        except Exception as exc:                                   # noqa: BLE001
            raised = f"{type(exc).__name__}: {exc}"
        check("B22-BUS", len(body) > 0 and "UNREADABLE" in body.upper() and not raised,
              f"the escalation wrote {len(body)} bytes to the room's messages.md naming the "
              f"unreadable window; an unwritable bus raised {raised or 'NOTHING'} — it is "
              f"reported and the loop survives it")


try:
    main()
except Exception as exc:  # noqa: BLE001 — a crashed probe is INOPERATIVE, never a silent pass
    stop("PROBE", f"{type(exc).__name__}: {exc}")

verdict = ("INOPERATIVE" if inoperative else "FAILED" if failures else "GREEN")
body = "\n".join([f"{verdict}  probe-team-monitor-homings  "
                  f"({time.strftime('%Y-%m-%dT%H:%M:%S%z')})",
                  f"target={TARGET}", *lines,
                  f"failures={failures} inoperative={inoperative}"]) + "\n"
OUT.write_text(body)
sys.stdout.write(body)
sys.exit(2 if inoperative else 1 if failures else 0)
