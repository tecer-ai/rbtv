#!/usr/bin/env python3
"""probe-planning-lock.py — .materialize.lock refuses a second concurrent materialize.

  P1  second distinct pass against the same planning/current/ is refused with lock-collision
  P2  first holder finishes; a later take succeeds (no double-splice window)
  P3  same pass-id re-enters (not a collision)
  P4  dead-pid lock is stolen (steal is not a C-16 collision)
"""

import importlib.util
import multiprocessing
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
TARGET = ROOT / "ignite" / "planning" / "lock.py"
OUT = HERE / "probe-planning-lock.out"

lines, failures, inoperative = [], [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load_lock():
    spec = importlib.util.spec_from_file_location("planning_lock_under_probe", TARGET)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hold(goal, pass_id, ready, release, result, target):
    spec = importlib.util.spec_from_file_location("planning_lock_child", target)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        handle = mod.take_lock(goal, pass_id)
        Path(ready).write_text("ready", encoding="utf-8")
        deadline = time.time() + 10
        while not Path(release).exists() and time.time() < deadline:
            time.sleep(0.02)
        handle.release()
        result.value = 0
    except Exception as exc:
        Path(ready).write_text(f"err:{exc}", encoding="utf-8")
        result.value = 1


def main():
    if not TARGET.exists():
        check("P1", False, f"{TARGET} does not exist")
        return
    try:
        import fcntl  # noqa: F401
    except ImportError:
        say("INOP  P1  fcntl does not import on this host")
        inoperative.append("P1")
        return

    lock = load_lock()
    with tempfile.TemporaryDirectory(prefix="planning-lock-") as tmp:
        goal = Path(tmp) / "goal"
        ctx = multiprocessing.get_context("fork")
        ready = Path(tmp) / "ready"
        release = Path(tmp) / "release"
        result = ctx.Value("i", -1)
        first = ctx.Process(
            target=_hold,
            args=(str(goal), "pass-one", str(ready), str(release), result, str(TARGET)),
        )
        first.start()
        deadline = time.time() + 10
        while not ready.exists() and time.time() < deadline:
            time.sleep(0.02)
        first_ready = ready.exists() and ready.read_text(encoding="utf-8") == "ready"
        second_code = None
        second_reason = ""
        if first_ready:
            try:
                lock.take_lock(goal, "pass-two")
            except lock.LockCollision as exc:
                second_code = exc.code
                second_reason = exc.reason
        check(
            "P1",
            first_ready and second_code == lock.CODE_LOCK_COLLISION,
            f"first_ready={first_ready} second_code={second_code!r} {second_reason}",
        )

        release.write_text("go", encoding="utf-8")
        first.join(10)
        third_ok = False
        if first.exitcode == 0:
            try:
                h = lock.take_lock(goal, "pass-three")
                third_ok = True
                h.release()
            except lock.LockCollision:
                third_ok = False
        check(
            "P2",
            first.exitcode == 0 and third_ok,
            f"first.exitcode={first.exitcode} later_take={third_ok}",
        )

        a = lock.take_lock(goal, "same-pass")
        b = lock.take_lock(goal, "same-pass")
        check("P3", a is b and a._depth == 2, f"reentry depth={a._depth} same={a is b}")
        a.release()
        a.release()

        stale = lock.lock_path(goal)
        stale.parent.mkdir(parents=True, exist_ok=True)
        stale.write_text("pid=999999001\npass-id=dead-pass\n", encoding="utf-8")
        check("P4a", not lock.pid_is_live(999999001), "staleness predicate: recorded pid is not live")
        stolen = False
        steal_code = None
        try:
            h = lock.take_lock(goal, "new-pass")
            stolen = True
            rec_pid, rec_pass = lock.read_holder(stale)
            stolen = rec_pass == "new-pass" and rec_pid == os.getpid()
            h.release()
        except lock.LockCollision as exc:
            steal_code = exc.code
        check(
            "P4",
            stolen and steal_code is None,
            f"stolen={stolen} steal_code={steal_code!r}",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    if inoperative and not failures:
        sys.exit(2)
    sys.exit(1 if failures else 0)
