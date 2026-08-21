#!/usr/bin/env python3
"""D49 secret-add — production CLI surface, fixture env file (never the real .env).

    python3 test_secret_add.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
COORD = HERE / "coord.py"
DUMMY_NAME = "TEST_SECRET_DECISION_REVIEW"
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


def python_scan(paths, needle):
    hits = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            continue
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if needle in text:
                hits.append(str(path))
            continue
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
            for fn in files:
                fp = Path(root) / fn
                try:
                    text = fp.read_text(encoding="utf-8", errors="replace")
                except (OSError, UnicodeError):
                    continue
                if needle in text:
                    hits.append(str(fp))
    return hits


def main():
    td = Path(tempfile.mkdtemp(prefix="secret-add-e2e-"))
    try:
        pkg = td / "pkg"
        (pkg / "coordination").mkdir(parents=True)
        envf = td / "scratch.env"
        envf.write_text("# fixture\nKEEP_ME=1\n", encoding="utf-8")
        drop = td / "key.txt"
        drop.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        common = ["--package", str(pkg), "secret-add", DUMMY_NAME,
                  "--from-file", str(drop), "--env-file", str(envf)]

        # 1. happy path — proven master identity, production argv
        code, out, err = run_coord({"COORD_AGENT": "goal-master"}, common)
        combined = out + err
        text = envf.read_text(encoding="utf-8")
        check("E2E happy: exit 0, line appended, drop gone, value not in output",
              code == 0 and f"{DUMMY_NAME}={DUMMY_VAL}" in text
              and not drop.exists()
              and DUMMY_VAL not in combined
              and f"appended {DUMMY_NAME}" in out,
              f"exit={code}\nstdout={out!r}\nstderr={err!r}\nenv_has_name={DUMMY_NAME in text}")

        # 3. log-cleanliness: grep + python scan over output + daemon logs + this pkg bus
        bus = pkg / "coordination" / "messages.md"
        log_roots = [
            Path.home() / ".local/state/rbtv-ignite",
        ]
        # command output files
        out_file = td / "cmd.out"
        err_file = td / "cmd.err"
        out_file.write_text(out, encoding="utf-8")
        err_file.write_text(err, encoding="utf-8")
        scan_paths = [out_file, err_file, pkg / "coordination"] + log_roots
        py_hits = [h for h in python_scan(scan_paths, DUMMY_VAL) if Path(h).resolve() != envf.resolve()]
        grep_hits = []
        for root in scan_paths:
            if not Path(root).exists():
                continue
            g = subprocess.run(
                ["grep", "-R", "-l", "--binary-files=without-match", DUMMY_VAL, str(root)],
                capture_output=True, text=True)
            for line in (g.stdout or "").splitlines():
                if Path(line).resolve() != envf.resolve():
                    grep_hits.append(line)
        check("E2E log-clean: dummy VALUE has zero hits outside the env file (grep + python)",
              not py_hits and not grep_hits,
              f"python={py_hits!r} grep={grep_hits!r} bus_exists={bus.exists()}")

        # 2a. existing NAME
        drop2 = td / "key2.txt"
        drop2.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        common2 = ["--package", str(pkg), "secret-add", DUMMY_NAME,
                   "--from-file", str(drop2), "--env-file", str(envf)]
        code, out, err = run_coord({"COORD_AGENT": "goal-master"}, common2)
        check("E2E refuse existing NAME",
              code == 2 and "already exists" in (out + err) and drop2.exists()
              and DUMMY_VAL not in (out + err),
              f"exit={code}\n{(out + err).strip()}")

        # 2b. worker
        drop3 = td / "key3.txt"
        drop3.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        common3 = ["--package", str(pkg), "secret-add", "TEST_SECRET_WORKER_E2E",
                   "--from-file", str(drop3), "--env-file", str(envf)]
        code, out, err = run_coord({"COORD_AGENT": "crashy"}, common3)
        check("E2E refuse worker",
              code == 2 and "Workers cannot add secrets" in (out + err) and drop3.exists(),
              f"exit={code}\n{(out + err).strip()}")

        # 2c. uncorroborated --as master
        drop4 = td / "key4.txt"
        drop4.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        common4 = ["--package", str(pkg), "--as", "goal-master", "secret-add",
                   "TEST_SECRET_AS_E2E", "--from-file", str(drop4), "--env-file", str(envf)]
        code, out, err = run_coord({"COORD_AGENT": "crashy"}, common4)
        check("E2E refuse uncorroborated --as master",
              code == 2 and "you claimed 'goal-master' (--as)" in (out + err)
              and drop4.exists(),
              f"exit={code}\n{(out + err).strip()}")

        # 2d. drop under .rbtv/goals/
        gdir = td / ".rbtv" / "goals" / "g"
        gdir.mkdir(parents=True)
        drop5 = gdir / "mailbox.txt"
        drop5.write_text(DUMMY_VAL + "\n", encoding="utf-8")
        common5 = ["--package", str(pkg), "secret-add", "TEST_SECRET_GOALS_E2E",
                   "--from-file", str(drop5), "--env-file", str(envf)]
        code, out, err = run_coord({"COORD_AGENT": "goal-master"}, common5)
        check("E2E refuse drop under .rbtv/goals/",
              code == 2 and ".rbtv/goals/" in (out + err) and drop5.exists(),
              f"exit={code}\n{(out + err).strip()}")

        # 4. red-proof: mutate duplicate-check away on a COPY
        mut_dir = td / "mut"
        mut_dir.mkdir()
        mut = mut_dir / "coord.py"
        src = COORD.read_text(encoding="utf-8")
        needle = "if line.split(\"=\", 1)[0].strip() == name:\n            return True"
        repl = "if line.split(\"=\", 1)[0].strip() == name:\n            return False"
        if needle not in src:
            check("E2E red-proof: mutation needle found", False, "needle missing")
        else:
            mut.write_text(src.replace(needle, repl, 1), encoding="utf-8")
            for sib in ("budget.py", "gateway_client.py"):
                shutil.copy2(HERE / sib, mut_dir / sib)
            drop6 = td / "key6.txt"
            drop6.write_text(DUMMY_VAL + "\n", encoding="utf-8")
            env_mut = os.environ.copy()
            env_mut.pop("TMUX_PANE", None)
            env_mut["COORD_AGENT"] = "goal-master"
            r = subprocess.run(
                [sys.executable, str(mut), "--package", str(pkg), "secret-add",
                 DUMMY_NAME, "--from-file", str(drop6), "--env-file", str(envf)],
                cwd=str(mut_dir), env=env_mut, capture_output=True, text=True, timeout=30)
            mut_text = envf.read_text(encoding="utf-8")
            dup_count = mut_text.count(f"{DUMMY_NAME}=")
            check("E2E red-proof: duplicate-check mutated away → refusal arm goes RED (second append)",
                  r.returncode == 0 and dup_count >= 2 and not drop6.exists(),
                  f"exit={r.returncode} dup_count={dup_count}\nstdout={r.stdout!r}\nstderr={r.stderr!r}")
    finally:
        shutil.rmtree(td, ignore_errors=True)

    print(f"\nsecret-add E2E: {'PASS' if not FAIL else 'FAIL'} ({len(FAIL)} failure(s))")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
