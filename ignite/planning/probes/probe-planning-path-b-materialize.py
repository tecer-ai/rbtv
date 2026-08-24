#!/usr/bin/env python3
"""probe-planning-path-b-materialize.py — approve-package births a NEW execution goal.

  P1  plan fixture at a recorded commit → execution goal folder created
  P2  planning goal taskforce.csv is byte-identical after
  P3  planning goal planning/current/ is byte-identical after
  P4  mint argv aims --package at the NEW folder; never --goal-local/--milestone-id/--nested
"""

import hashlib
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
OUT = HERE / "probe-planning-path-b-materialize.out"

lines, failures = [], []


def say(msg):
    lines.append(msg)


def check(tag, ok, detail):
    say(f"{'PASS' if ok else 'FAIL'}  {tag}  {detail}")
    if not ok:
        failures.append(tag)


def load(name):
    path = PLANNING / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"planning_{name}_pbm", path)
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


def digest_tree(folder):
    folder = Path(folder)
    acc = []
    if not folder.exists():
        return ""
    for p in sorted(folder.rglob("*")):
        if p.is_file():
            rel = p.relative_to(folder).as_posix()
            acc.append(rel + ":" + hashlib.sha256(p.read_bytes()).hexdigest())
    return "\n".join(acc)


def main():
    if not (PLANNING / "path_b.py").exists():
        check("P1", False, f"{PLANNING} missing path_b.py")
        return
    path_b = load("path_b")

    with tempfile.TemporaryDirectory(prefix="path-b-mat-") as tmp:
        tmp = Path(tmp)
        goals = tmp / "goals"
        goals.mkdir()
        plan_goal = goals / "plan-alpha"
        current = plan_goal / "planning" / "current"
        current.mkdir(parents=True)
        tf = plan_goal / "taskforce.csv"
        tf.write_text(
            "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
            "tf-1,understand,,claude,opus,1,,m0\n",
            encoding="utf-8",
        )
        (current / "marker.txt").write_text("planning-pass-body\n", encoding="utf-8")
        tf_before = tf.read_bytes()
        current_before = digest_tree(current)

        artifacts = tmp / "artifacts"
        artifacts.mkdir()
        (artifacts / "contract.md").write_text("build the thing\n", encoding="utf-8")
        (artifacts / "roster.json").write_text(
            json.dumps(["build", "verify"]) + "\n", encoding="utf-8"
        )
        git(artifacts, "init")
        git(artifacts, "config", "user.email", "probe@example")
        git(artifacts, "config", "user.name", "probe")
        git(artifacts, "add", ".")
        git(artifacts, "commit", "-m", "plan")
        sha = git(artifacts, "rev-parse", "HEAD").stdout.strip()

        sheet = tmp / "sheet.json"
        sheet.write_text(
            json.dumps(
                {
                    "seats": {
                        "build": {"harness": "claude", "model": "opus"},
                        "verify": {"harness": "claude", "model": "opus"},
                    }
                }
            ),
            encoding="utf-8",
        )

        seen = {}

        def _mint(argv):
            seen["argv"] = list(argv)

        pkg = {
            "execution_goal": "exec-alpha",
            "planning_goal": str(plan_goal),
            "goals_root": str(goals),
            "lane": "daemon",
            "contract": "build the thing",
            "bound_commit": sha,
            "plan_artifacts": str(artifacts),
            "git_dir": str(artifacts),
            "roster": ["build", "verify"],
            "workflow": "execute",
            "catalog_root": str(tmp / "catalog"),
            "sheet": str(sheet),
            "origin_id": "thread-approve-1",
        }
        out, argv = path_b.run_path_b(pkg=pkg, mint=_mint)
        exec_dir = goals / "exec-alpha"
        check(
            "P1",
            bool(out.get("ok")) and exec_dir.is_dir() and (exec_dir / "goal.md").is_file(),
            f"ok={out.get('ok')} exists={exec_dir.is_dir()} record={out.get('record')}",
        )
        check(
            "P2",
            tf.read_bytes() == tf_before,
            "planning goal taskforce.csv changed" if tf.read_bytes() != tf_before else "unchanged",
        )
        check(
            "P3",
            digest_tree(current) == current_before,
            "planning/current/ changed" if digest_tree(current) != current_before else "unchanged",
        )
        used = seen.get("argv") or argv
        joined = " ".join(used)
        aimed = False
        if "--package" in used:
            aimed = used[used.index("--package") + 1] == str(exec_dir)
        check(
            "P4",
            aimed
            and "--goal-local" not in used
            and "--milestone-id" not in used
            and "--nested" not in used,
            f"aimed={aimed} argv={joined}",
        )


if __name__ == "__main__":
    try:
        main()
    finally:
        text = "\n".join(lines) + "\n"
        OUT.write_text(text, encoding="utf-8")
        sys.stdout.write(text)
    sys.exit(1 if failures else 0)
