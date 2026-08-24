#!/usr/bin/env python3
"""probe-planning-path-b-failure.py — collision + reclaim leave no half-goal.

  P1  existing execution-goal name → failure record (origin-id present); no new write
  P2  roster seat-id clash → failure record; directory absent
  P3  scaffold succeeded + mint failed → reclaim: directory absent; record on planning goal
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("RBTV_PROBE_TREE") or HERE.parents[2])
PLANNING = ROOT / "ignite" / "planning"
OUT = HERE / "probe-planning-path-b-failure.out"

lines, failures = [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load(name):
    path = PLANNING / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"planning_{name}_pbf", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def make_commit(artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "contract.md").write_text("contract\n", encoding="utf-8")
    git(artifacts, "init")
    git(artifacts, "config", "user.email", "probe@example")
    git(artifacts, "config", "user.name", "probe")
    git(artifacts, "add", ".")
    git(artifacts, "commit", "-m", "plan")
    return git(artifacts, "rev-parse", "HEAD").stdout.strip()


def base_pkg(tmp, goals, plan_goal, sha, artifacts, name, roster):
    sheet = tmp / f"{name}-sheet.json"
    sheet.write_text(
        json.dumps(
            {
                "seats": {
                    s: {"harness": "claude", "model": "opus"} for s in dict.fromkeys(roster)
                }
            }
        ),
        encoding="utf-8",
    )
    return {
        "execution_goal": name,
        "planning_goal": str(plan_goal),
        "goals_root": str(goals),
        "lane": "daemon",
        "contract": "contract",
        "bound_commit": sha,
        "plan_artifacts": str(artifacts),
        "git_dir": str(artifacts),
        "roster": roster,
        "workflow": "execute",
        "catalog_root": str(tmp / "catalog"),
        "sheet": str(sheet),
        "origin_id": "thread-d12",
    }


def record_ok(out, subject):
    rec = out.get("record") or {}
    return (
        not out.get("ok")
        and rec.get("origin") == "approval-thread"
        and rec.get("origin-id") == "thread-d12"
        and rec.get("subject") == subject
        and rec.get("class")
    )


def main():
    if not (PLANNING / "path_b.py").exists():
        check("P1", False, f"{PLANNING} missing path_b.py")
        return
    path_b = load("path_b")
    failure = sys.modules["failure"]

    with tempfile.TemporaryDirectory(prefix="path-b-fail-") as tmp:
        tmp = Path(tmp)
        goals = tmp / "goals"
        goals.mkdir()
        plan_goal = goals / "plan-beta"
        (plan_goal / "planning" / "current").mkdir(parents=True)
        (plan_goal / "taskforce.csv").write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n",
            encoding="utf-8",
        )
        artifacts = tmp / "artifacts"
        sha = make_commit(artifacts)

        taken = goals / "exec-taken"
        taken.mkdir()
        (taken / "goal.md").write_text(
            "---\nname: exec-taken\nstatus: briefed\n---\n\ntaken\n",
            encoding="utf-8",
        )
        pkg1 = base_pkg(tmp, goals, plan_goal, sha, artifacts, "exec-taken", ["build"])
        out1, _ = path_b.run_path_b(pkg=pkg1, mint=lambda argv: None)
        rec1 = out1.get("record") or {}
        rec_path = failure.record_path(plan_goal)
        check(
            "P1",
            record_ok(out1, "exec-taken")
            and rec1.get("class") == failure.CLASS_ROSTER_NAME_COLLISION
            and rec_path.is_file()
            and taken.is_dir(),
            f"ok={out1.get('ok')} class={rec1.get('class')!r} "
            f"origin-id={rec1.get('origin-id')!r} record={rec_path.is_file()}",
        )

        pkg2 = base_pkg(
            tmp, goals, plan_goal, sha, artifacts, "exec-clash", ["build", "build"]
        )
        out2, _ = path_b.run_path_b(pkg=pkg2, mint=lambda argv: None)
        rec2 = out2.get("record") or {}
        clash_dir = goals / "exec-clash"
        check(
            "P2",
            record_ok(out2, "exec-clash")
            and rec2.get("class") == failure.CLASS_ROSTER_NAME_COLLISION
            and not clash_dir.exists(),
            f"ok={out2.get('ok')} class={rec2.get('class')!r} exists={clash_dir.exists()}",
        )

        def _boom(argv):
            raise failure.MaterializeFailure(
                failure.CLASS_ATOMIC_CORE_REFUSAL,
                "materialize-refused",
                "injected mint fail",
                "exec-half",
            )

        pkg3 = base_pkg(tmp, goals, plan_goal, sha, artifacts, "exec-half", ["build"])
        out3, _ = path_b.run_path_b(pkg=pkg3, mint=_boom)
        rec3 = out3.get("record") or {}
        half = goals / "exec-half"
        check(
            "P3",
            record_ok(out3, "exec-half")
            and rec3.get("class") == failure.CLASS_ATOMIC_CORE_REFUSAL
            and rec3.get("origin-id") == "thread-d12"
            and not half.exists()
            and rec_path.is_file(),
            f"ok={out3.get('ok')} class={rec3.get('class')!r} "
            f"exists={half.exists()} origin-id={rec3.get('origin-id')!r}",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    sys.exit(1 if failures else 0)
