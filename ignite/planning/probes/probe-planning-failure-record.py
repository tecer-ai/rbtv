#!/usr/bin/env python3
"""probe-planning-failure-record.py — five failure classes + origin routing.

  P1–P5  each class yields a six-field record
  P6     approval-thread origin is not stamped on a lane
  P7     gate-lane origin stamps incomplete: materialize-failed (session-close fallback)
"""

import csv
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
PLANNING = ROOT / "ignite" / "planning"
OUT = HERE / "probe-planning-failure-record.out"

lines, failures = [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load(name):
    path = PLANNING / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"planning_{name}_probe", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if not (PLANNING / "wrapper.py").exists():
        check("P1", False, f"{PLANNING} missing wrapper.py")
        return
    wrapper = load("wrapper")
    failure = sys.modules["failure"]

    fixtures = (
        (
            "P1",
            failure.CLASS_LOCK_COLLISION,
            "lock-collision",
            failure.ORIGIN_APPROVAL_THREAD,
            "thread-d12",
            "collide",
        ),
        (
            "P2",
            failure.CLASS_ROSTER_NAME_COLLISION,
            "name-exists",
            failure.ORIGIN_APPROVAL_THREAD,
            "thread-d12",
            "roster",
        ),
        (
            "P3",
            failure.CLASS_UNRESOLVABLE_REFERENCE,
            "exposes-ref-dangling",
            failure.ORIGIN_GATE_LANE,
            "gate-seat",
            "ref",
        ),
        (
            "P4",
            failure.CLASS_ENVELOPE_REFUSAL,
            "launch-refused",
            failure.ORIGIN_APPROVAL_THREAD,
            "thread-d12",
            "env",
        ),
        (
            "P5",
            failure.CLASS_ATOMIC_CORE_REFUSAL,
            "registry-changed-underfoot",
            failure.ORIGIN_GATE_LANE,
            "gate-seat",
            "atomic",
        ),
    )

    with tempfile.TemporaryDirectory(prefix="planning-fail-") as tmp:
        tmp = Path(tmp)
        sessions = tmp / "sessions.csv"
        sessions.write_text(
            "session-id,seat,ended,disposition\n"
            "s1,gate-seat,,\n",
            encoding="utf-8",
        )

        def raise_mf(class_, code, reason):
            def _fn():
                raise failure.MaterializeFailure(class_, code, reason)

            return _fn

        for tag, class_, code, origin, origin_id, subject in fixtures:
            goal = tmp / subject
            kwargs = dict(
                path=wrapper.PATH_A,
                goal_folder=goal,
                planning_pass_id=f"pass-{subject}",
                origin=origin,
                origin_id=origin_id,
                subject=subject,
                mint=lambda: None,
                sessions_path=sessions,
            )
            if class_ == failure.CLASS_LOCK_COLLISION:
                lock = sys.modules["lock"]
                h = lock.take_lock(goal, "other-pass")
                try:
                    out = wrapper.supervised_materialize(
                        validate=lambda: None, **kwargs
                    )
                finally:
                    h.release()
            elif class_ == failure.CLASS_ENVELOPE_REFUSAL:
                out = wrapper.supervised_materialize(
                    validate=lambda: None,
                    envelope_stamp=failure.ENVELOPE_REFUSED_STAMP,
                    **kwargs,
                )
            else:
                out = wrapper.supervised_materialize(
                    validate=raise_mf(class_, code, f"reason-{subject}"),
                    **kwargs,
                )
            rec = out.get("record") or {}
            missing = [f for f in failure.RECORD_FIELDS if f not in rec]
            routed = rec.get("origin") == origin and rec.get("origin-id") == origin_id
            check(
                tag,
                (not out.get("ok")) and rec.get("class") == class_ and not missing and routed,
                f"ok={out.get('ok')} class={rec.get('class')!r} missing={missing} "
                f"origin={rec.get('origin')!r}/{rec.get('origin-id')!r}",
            )

        d12 = tmp / "collide"
        check(
            "P6",
            not failure.stamp_path(d12).exists(),
            f"approval-thread must not stamp a lane ({failure.stamp_path(d12)})",
        )

        gate_goal = tmp / "ref"
        stamp = failure.stamp_path(gate_goal)
        payload_ok = False
        if stamp.exists():
            payload = json.loads(stamp.read_text(encoding="utf-8"))
            payload_ok = (
                payload.get("diagnostic") == failure.INCOMPLETE_MATERIALIZE_FAILED
                and payload.get("path") == "session-close-fallback"
                and payload.get("armed") == 0
            )
        disp = ""
        with sessions.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        if rows:
            disp = rows[0].get("disposition", "")
        check(
            "P7",
            payload_ok and disp == "incomplete",
            f"stamp={payload_ok} sessions.disposition={disp!r} "
            f"path=session-close-fallback",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    sys.exit(1 if failures else 0)
