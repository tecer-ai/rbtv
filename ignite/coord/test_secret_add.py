#!/usr/bin/env python3
"""D49 secret-add client gates — production CLI, no env write (the write is daemon-side).

    python3 test_secret_add.py
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD = HERE / "coord.py"
DUMMY_VAL = "dummy-secret-add-e2e-7f3a9c"

FAIL = []


def check(label, cond, evidence=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    if evidence:
        print("        " + evidence.strip().replace("\n", "\n        "))
    if not cond:
        FAIL.append(label)


def run_coord(env_extra, argv, cwd=None):
    env = os.environ.copy()
    env.pop("TMUX_PANE", None)
    env.pop("TMUX", None)
    env.update(env_extra)
    r = subprocess.run(
        [sys.executable, str(COORD), *argv],
        cwd=str(cwd or HERE),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return r.returncode, r.stdout, r.stderr


def main():
    td = Path(tempfile.mkdtemp(prefix="secret-add-e2e-"))
    try:
        pkg = td / "pkg"
        (pkg / "coordination").mkdir(parents=True)

        code, out, err = run_coord(
            {"COORD_AGENT": "goal-master"},
            ["--package", str(pkg), "secret-add", "X", "--from-file", "/tmp/x",
             "--env-file", "/tmp/y"])
        check("E2E --env-file hatch closed (parser refuses the flag)",
              code != 0 and "unrecognized arguments" in (out + err),
              f"exit={code}\n{(out + err).strip()}")

        drop3 = td / "key3.txt"
        drop3.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        code, out, err = run_coord(
            {"COORD_AGENT": "crashy"},
            ["--package", str(pkg), "secret-add", "TEST_SECRET_WORKER_E2E",
             "--from-file", str(drop3)])
        check("E2E refuse worker",
              code == 2 and "Workers cannot add secrets" in (out + err) and drop3.exists()
              and DUMMY_VAL not in (out + err),
              f"exit={code}\n{(out + err).strip()}")

        drop4 = td / "key4.txt"
        drop4.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        code, out, err = run_coord(
            {"COORD_AGENT": "crashy"},
            ["--package", str(pkg), "--as", "goal-master", "secret-add",
             "TEST_SECRET_AS_E2E", "--from-file", str(drop4)])
        check("E2E refuse uncorroborated --as master",
              code == 2 and "you claimed 'goal-master' (--as)" in (out + err)
              and drop4.exists() and DUMMY_VAL not in (out + err),
              f"exit={code}\n{(out + err).strip()}")

        gdir = td / ".rbtv" / "goals" / "g"
        gdir.mkdir(parents=True)
        drop5 = gdir / "mailbox.txt"
        drop5.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        code, out, err = run_coord(
            {"COORD_AGENT": "goal-master"},
            ["--package", str(pkg), "secret-add", "TEST_SECRET_GOALS_E2E",
             "--from-file", str(drop5)])
        check("E2E refuse drop under .rbtv/goals/",
              code == 2 and ".rbtv/goals/" in (out + err) and drop5.exists()
              and DUMMY_VAL not in (out + err),
              f"exit={code}\n{(out + err).strip()}")
    finally:
        import shutil
        shutil.rmtree(td, ignore_errors=True)

    print(f"\nsecret-add E2E: {'PASS' if not FAIL else 'FAIL'} ({len(FAIL)} failure(s))")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
