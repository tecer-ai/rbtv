#!/usr/bin/env python3
"""Bind planning/ artifacts at a git commit that does not contain planning/bound-commit.

The pointer is written AFTER the commit, on disk only — a caged seat reads it; git show of the
named tree must not find it (or must equal the named hash). Staging the whole planning/ folder
puts the previous generation's pointer inside the tree the new hash names.

p-no-rebind-after-the-ask-is-delivered: once planning/approve-package.json records bound_commit,
this tool refuses to move the hash.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

BOUND_COMMIT = Path("planning") / "bound-commit"


def planning_dir(pkg):
    return Path(pkg) / "planning"


def bound_path(pkg):
    return Path(pkg) / BOUND_COMMIT


def frozen(pkg):
    """True when a delivered (or about-to-deliver) approval ask already names a hash."""
    from approve_package import APPROVE_PACKAGE
    p = Path(pkg) / APPROVE_PACKAGE
    if not p.is_file():
        return False
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    return bool(isinstance(obj, dict) and obj.get("bound_commit"))


def _walk_files(folder):
    if not folder.is_dir():
        return
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            yield Path(dirpath) / name


def artifact_mtime(pkg):
    """Newest mtime under planning/ excluding bound-commit. None if no such file."""
    bound = bound_path(pkg).resolve()
    newest = None
    for f in _walk_files(planning_dir(pkg)):
        try:
            if f.resolve() == bound:
                continue
            m = f.stat().st_mtime
        except OSError:
            continue
        if newest is None or m > newest:
            newest = m
    return newest


def freshness(pkg):
    """Bind freshness. applies only once bound-commit exists (a bind has already happened)."""
    bp = bound_path(pkg)
    art = artifact_mtime(pkg)
    out = {
        "applies": False,
        "stale": False,
        "state": "absent",
        "bound_mtime": None,
        "artifact_mtime": art,
        "frozen": frozen(pkg),
    }
    if not bp.is_file():
        return out
    try:
        bm = bp.stat().st_mtime
    except OSError:
        return out
    out["applies"] = True
    out["bound_mtime"] = bm
    stale = art is not None and bm < art
    out["stale"] = stale
    out["state"] = "stale" if stale else "fresh"
    return out


def git_root(pkg, git_dir=None):
    if git_dir:
        root = Path(git_dir)
        return root if (root / ".git").exists() else None
    cur = Path(pkg).resolve()
    for cand in (cur, *cur.parents):
        if (cand / ".git").exists():
            return cand
    return None


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True, text=True, check=False,
    )


def bind(pkg, git_dir=None):
    """Commit planning/ excluding bound-commit, then write the new hash to bound-commit.

    No-op when frozen, already fresh, nothing to bind, or no git. Never writes bound-commit
    into the commit it names.
    """
    pkg = Path(pkg)
    fr = freshness(pkg)
    if fr["frozen"]:
        disk = bound_path(pkg).read_text(encoding="utf-8").strip() if bound_path(pkg).is_file() else ""
        return {"ok": True, "action": "frozen", "commit": disk}
    plan = planning_dir(pkg)
    if not plan.is_dir():
        return {"ok": True, "action": "no-planning"}
    if fr["applies"] and not fr["stale"]:
        disk = bound_path(pkg).read_text(encoding="utf-8").strip()
        return {"ok": True, "action": "fresh", "commit": disk}
    if artifact_mtime(pkg) is None:
        return {"ok": True, "action": "no-artifacts"}
    root = git_root(pkg, git_dir)
    if root is None:
        return {"ok": False, "action": "no-git"}
    try:
        rel = plan.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return {"ok": False, "action": "outside-git", "detail": f"{plan} not under {root}"}
    pointer = bound_path(pkg)
    prev = pointer.read_text(encoding="utf-8") if pointer.is_file() else None
    if pointer.is_file():
        pointer.unlink()
    added = _git(root, "add", "-A", "--", rel)
    if added.returncode != 0:
        if prev is not None:
            pointer.write_text(prev, encoding="utf-8")
        return {"ok": False, "action": "git-error", "detail": (added.stderr or added.stdout)[:400]}
    goal = pkg.name
    committed = _git(root, "commit", "-m", f"{goal}: plan artifacts for approval", "--", rel)
    if committed.returncode != 0:
        err = (committed.stderr or "") + (committed.stdout or "")
        if "nothing to commit" not in err.lower() and "no changes added" not in err.lower():
            if prev is not None:
                pointer.write_text(prev, encoding="utf-8")
            return {"ok": False, "action": "git-error", "detail": err[:400]}
    hashed = _git(root, "rev-parse", "HEAD")
    if hashed.returncode != 0:
        if prev is not None:
            pointer.write_text(prev, encoding="utf-8")
        return {"ok": False, "action": "git-error", "detail": (hashed.stderr or hashed.stdout)[:400]}
    sha = hashed.stdout.strip()
    pointer.write_text(sha + "\n", encoding="utf-8")
    return {"ok": True, "action": "bound", "commit": sha}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="bind-planning",
        description="Commit a goal's planning/ artifacts without putting bound-commit inside "
                    "the named tree. Frozen once approve-package.json records bound_commit.",
    )
    ap.add_argument("--package", required=True, help="the planning goal folder")
    ap.add_argument("--git-dir", default=None, help="vault root (the repo). Default: walk up from --package")
    ap.add_argument("--json", action="store_true", help="print the result object")
    args = ap.parse_args(argv)
    result = bind(args.package, git_dir=args.git_dir)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{result.get('action')} {result.get('commit', '')}".strip())
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    sys.exit(main())
