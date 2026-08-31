#!/usr/bin/env python3
"""probe-bound-commit — after-edge refuses a stale bind; bind-commit is not inside the named tree.

157: successor READY while bound-commit is older than review-package.md (red, freshness
skipped); BLOCKED bind=stale after the fix; bind() then READY on a fresh hash without a
leader sitting.

156: today's whole-folder add commits a superseded pointer; bind() leaves the in-tree
copy absent.

Freeze: approve-package.json names H → a later planning write does not move bound-commit.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANNING = HERE.parent
COORD = PLANNING.parent / "coord"
SUPERVISE = PLANNING.parent / "supervisor" / "supervise.py"
OUT = HERE / "probe-bound-commit.out"
FIX_ANCHOR = '_fr = planning_bind.freshness(pkg)'

sys.path.insert(0, str(COORD))
sys.path.insert(0, str(PLANNING.parent / "supervisor"))
sys.path.insert(0, str(PLANNING))
import ending_store  # noqa: E402
import planning_bind  # noqa: E402
import ready  # noqa: E402

CHECKS = []
T0 = time.time()


def check(name, ok, evidence=None):
    CHECKS.append({"name": name, "pass": bool(ok), "evidence": evidence or {}})


def git(root, *args, check_ok=True):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check_ok and r.returncode != 0:
        raise RuntimeError(f"git {args}: {r.stderr or r.stdout}")
    return r


def init_git(root):
    git(root, "init", "-q")
    git(root, "config", "user.email", "probe@example.com")
    git(root, "config", "user.name", "probe")


def fixture_goal(root, name="test-bound-commit"):
    rec = root / ".rbtv" / "modules" / "ignite" / "server.json"
    rec.parent.mkdir(parents=True, exist_ok=True)
    rec.write_text('{"machines": {}}\n', encoding="utf-8")
    pkg = root / ".rbtv" / "goals" / name
    for seat in ("reviewer", "verifier"):
        (pkg / "seats" / seat).mkdir(parents=True, exist_ok=True)
        (pkg / "seats" / seat / "seat.md").write_text(
            f"---\nagent: {seat}\nmodel: opus\n---\nbrief\n", encoding="utf-8")
    (pkg / "coordination").mkdir(parents=True, exist_ok=True)
    (pkg / "coordination" / "workers.md").write_text(
        "# workers\n\n| agent | active | tmux pane | working on | checked in | checked out | last-read |\n"
        "|-------|--------|-----------|------------|------------|-------------|-----------|\n",
        encoding="utf-8")
    (pkg / "planning").mkdir(parents=True, exist_ok=True)
    (pkg / "taskforce.csv").write_text(
        "taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n"
        "tf,reviewer,,bash,probe,high,35,\n"
        "tf,verifier,reviewer,bash,probe,high,35,\n",
        encoding="utf-8")
    ending_store.stamp_seat_declare(pkg, "reviewer", "done", evidence="probe-bound-commit")
    return pkg


def rows_of(pkg):
    ns = type("A", (), {"package": str(pkg), "base": None, "workers_dir": None,
                        "as_agent": None, "force": False, "json": True,
                        "explain": None, "fail_on_skew": False})()
    return {r["seat"]: r for r in ready.ready_seat_rows(ns)}


def supervise_json(pkg):
    r = subprocess.run(
        ["python3", str(SUPERVISE), "--package", str(pkg), "ready-seats", "--json"],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr or r.stdout)
    return {row["seat"]: row for row in json.loads(r.stdout)}


root = Path(tempfile.mkdtemp(prefix="probe-bound-commit-"))
try:
    src = (PLANNING.parent / "supervisor" / "ready.py").read_text(encoding="utf-8")
    check("FIX_ANCHOR present in ready.py", FIX_ANCHOR in src)

    pkg = fixture_goal(root)
    (pkg / "planning" / "bound-commit").write_text("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n")
    os.utime(pkg / "planning" / "bound-commit", (time.time() - 120, time.time() - 120))
    time.sleep(0.05)
    (pkg / "planning" / "review-package.md").write_text("REVIEW-PACKAGE\nlanded after bind\n")
    green = supervise_json(pkg)
    check("157 green: stale bind → verifier not READY",
          green["verifier"]["verdict"] == "BLOCKED" and "bind=stale" in green["verifier"]["reason"],
          {"verdict": green["verifier"]["verdict"], "reason": green["verifier"]["reason"]})

    orig = planning_bind.freshness
    planning_bind.freshness = lambda _pkg: {
        "applies": False, "stale": False, "state": "absent",
        "bound_mtime": None, "artifact_mtime": None, "frozen": False}
    try:
        red = rows_of(pkg)
    finally:
        planning_bind.freshness = orig
    check("157 red: skipping freshness launches verifier on stale bind",
          red["verifier"]["verdict"] == "READY" and red["reviewer"]["verdict"] == "DONE",
          {"verdict": red["verifier"]["verdict"]})

    init_git(root)
    git(root, "add", "--", ".rbtv/goals/test-bound-commit/planning")
    git(root, "commit", "-q", "-m", "test-bound-commit: prior bind",
        "--", ".rbtv/goals/test-bound-commit/planning")
    (pkg / "planning" / "review-package.md").write_text("REVIEW-PACKAGE\nv2\n")
    git(root, "add", "--", ".rbtv/goals/test-bound-commit/planning")
    git(root, "commit", "-q", "-m", "test-bound-commit: plan artifacts for approval",
        "--", ".rbtv/goals/test-bound-commit/planning")
    old_bound = git(root, "rev-parse", "HEAD").stdout.strip()
    (pkg / "planning" / "bound-commit").write_text(old_bound + "\n")
    rel = ".rbtv/goals/test-bound-commit/planning/bound-commit"
    shown = git(root, "show", f"{old_bound}:{rel}", check_ok=False)
    check("156 red: git show of named tree prints a superseded pointer",
          shown.returncode == 0 and shown.stdout.strip() != old_bound
          and (pkg / "planning" / "bound-commit").read_text().strip() == old_bound,
          {"show": shown.stdout.strip()[:80], "disk": old_bound[:12]})

    (pkg / "planning" / "review-package.md").write_text("REVIEW-PACKAGE\nv3 for bind()\n")
    os.utime(pkg / "planning" / "bound-commit", (time.time() - 5, time.time() - 5))
    result = planning_bind.bind(pkg, git_dir=root)
    new_sha = result.get("commit", "")
    show2 = git(root, "show", f"{new_sha}:{rel}", check_ok=False)
    disk2 = (pkg / "planning" / "bound-commit").read_text().strip()
    check("156 green: in-tree copy absent or equal to the named hash",
          result.get("ok") and result.get("action") == "bound"
          and disk2 == new_sha
          and (show2.returncode != 0 or show2.stdout.strip() == new_sha),
          {"action": result.get("action"), "show_code": show2.returncode,
           "show": (show2.stdout or show2.stderr)[:80], "disk": disk2[:12]})

    after = supervise_json(pkg)
    check("157 green: after bind() verifier READY on the fresh hash (no leader sitting)",
          after["verifier"]["verdict"] == "READY" and disk2 == new_sha,
          {"verdict": after["verifier"]["verdict"], "commit": new_sha[:12]})

    (pkg / "planning" / "approve-package.json").write_text(
        json.dumps({"bound_commit": new_sha, "execution_goal": "x", "lane": "daemon",
                    "plan_artifacts": "planning"}) + "\n",
        encoding="utf-8")
    frozen_hash = new_sha
    time.sleep(0.05)
    (pkg / "planning" / "review-package.md").write_text("REVIEW-PACKAGE\nv4 after ask delivered\n")
    froze = planning_bind.bind(pkg, git_dir=root)
    still = (pkg / "planning" / "bound-commit").read_text().strip()
    check("freeze: delivered ask hash is not moved",
          froze.get("action") == "frozen" and still == frozen_hash,
          {"action": froze.get("action"), "still": still[:12], "named": frozen_hash[:12]})
    held = supervise_json(pkg)
    check("freeze: later write leaves successor blocked, does not compose stale",
          held["verifier"]["verdict"] == "BLOCKED" and "bind=stale" in held["verifier"]["reason"],
          {"verdict": held["verifier"]["verdict"]})

    claim = (PLANNING.parent.parent / "meta" / "leader" / "prompts" / "leader.md").read_text(
        encoding="utf-8")
    check("leader.md names the freeze and does not stage whole planning/ as the bind",
          "p-no-rebind-after-the-ask-is-delivered" in claim
          and "planning_bind.py" in claim
          and "deliberately not inside the commit it names" in claim,
          {})
finally:
    shutil.rmtree(root, ignore_errors=True)

failed = [c for c in CHECKS if not c["pass"]]
exit_code = 1 if failed else 0
lines = [f"{'ok  ' if c['pass'] else 'FAIL'}  {c['name']}"
         + ("" if c["pass"] else f" — {c['evidence']}") for c in CHECKS]
lines.append("")
lines.append("RESULT: PASS — stale after-edge refused; bind pointer absent-or-equal; freeze holds"
             if exit_code == 0
             else f"RESULT: FAIL — {len(failed)} check(s): "
             + " · ".join(c["name"] for c in failed))
lines.append(f"WALL_MS {int((time.time() - T0) * 1000)}")
lines.append(f"EXIT {exit_code}")
text = "\n".join(lines) + "\n"
OUT.write_text(text, encoding="utf-8")
sys.stdout.write(text)
sys.exit(exit_code)
