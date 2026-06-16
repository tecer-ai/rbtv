#!/usr/bin/env python3
"""Deterministic git commit for the rbtv-commit workflow.

Runs INSIDE the target repo (uses the current working directory to locate the
repo root). The calling agent supplies the judgment — which files, what message
— and this script owns all the mechanics in one invocation: remote sync, a clean
staging gate, the commit, and an optional push.

It fails loudly (non-zero exit + a clear message) and makes NO commit on:
  - a real merge conflict while syncing the remote,
  - a requested file that has no changes to commit,
  - a staged/requested mismatch (defensive; should not happen after the reset).

Staging is made deterministic by unstaging EVERYTHING first, then staging only
the requested files. A file a parallel session left staged is therefore never
committed — its working-tree changes are preserved, simply left unstaged.

Remote sync is commit-first: the requested files are committed locally, THEN the
remote is pulled. A clean auto-merge is handled silently; a real conflict aborts
the merge and undoes the local commit (`reset --soft`), so no commit survives and
the requested changes are left staged in the working tree — never trapped in a
stash. Other uncommitted work in the tree is untouched throughout.

Paths are repo-root-relative. A rename is two paths (old + new) — pass both.

Usage:
    python commit.py -m "feat: ..." -f path/a -f path/b [--push]
"""
import argparse
import subprocess
import sys


def fail(msg, code=1):
    print(f"commit.py: ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def git(args, root, check=True, capture=True):
    res = subprocess.run(["git", *args], cwd=root, text=True, capture_output=capture)
    if check and res.returncode != 0:
        out = (res.stderr or res.stdout or "").strip()
        fail(f"git {' '.join(args)} failed: {out}")
    return res


def git_ok(args, root):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).returncode == 0


def sync_after_commit(root, before):
    """Pull remote changes on top of the just-made commit. On a real conflict,
    abort the merge and undo the commit so NO commit survives and the requested
    changes are left staged in the working tree. `before` is HEAD prior to the
    commit (the undo target)."""
    pull = git(["pull", "--no-edit"], root, check=False)
    if pull.returncode == 0:
        return
    conflicts = git(["diff", "--name-only", "--diff-filter=U"], root, check=False).stdout.strip()
    git(["merge", "--abort"], root, check=False)
    git(["reset", "--soft", before], root, check=False)  # undo our commit, keep changes staged
    msg = "merge conflict pulling remote changes"
    if conflicts:
        msg += " in: " + ", ".join(conflicts.splitlines())
    fail(msg + ". No commit made; your changes are staged. Resolve the remote divergence, then retry.")


def main():
    p = argparse.ArgumentParser(description="Deterministic git commit (rbtv-commit). Run from inside the repo.")
    p.add_argument("-m", "--message", required=True, help="Commit message for this cluster.")
    p.add_argument("-f", "--file", dest="files", action="append", required=True,
                   help="A repo-root-relative file to include. Repeat for each file.")
    p.add_argument("--push", action="store_true", help="Push after a successful commit.")
    args = p.parse_args()

    res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if res.returncode != 0:
        fail("not inside a git repository (run this from within the target repo).")
    root = res.stdout.strip()

    requested = []
    for f in args.files:
        if f not in requested:
            requested.append(f)
    requested_set = set(requested)

    # --- fetch + learn whether the remote is ahead (sync happens after commit) ---
    no_upstream = True
    behind = False
    if git(["remote"], root).stdout.strip():
        git(["fetch"], root)
        if git_ok(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root):
            no_upstream = False
            count = git(["rev-list", "HEAD..@{u}", "--count"], root).stdout.strip()
            behind = count not in ("", "0")

    # --- clean staging gate: unstage all, then stage ONLY the requested files ---
    git(["reset", "-q"], root)
    for f in requested:
        git(["add", "-A", "--", f], root)

    # --no-renames so a staged rename reads as delete(old) + add(new) — both requested
    # paths then appear, instead of git collapsing them into a single destination name.
    staged = {line for line in git(["diff", "--cached", "--name-only", "--no-renames"], root).stdout.splitlines() if line}
    missing = requested_set - staged
    if missing:
        fail("these requested files have no changes to commit: " + ", ".join(sorted(missing)))
    foreign = staged - requested_set
    if foreign:
        fail("staged index does not match requested files (unexpected): " + ", ".join(sorted(foreign)))

    # --- commit (capturing the undo target first), then sync the remote on top ---
    before = git(["rev-parse", "HEAD"], root, check=False).stdout.strip()
    git(["commit", "-m", args.message], root)
    committed = git(["rev-parse", "--short", "HEAD"], root).stdout.strip()  # MY commit, before any sync merge
    if behind and before:
        sync_after_commit(root, before)
    print(f"committed {committed}: {args.message.splitlines()[0]}")
    print("files: " + ", ".join(requested))
    merged = git(["rev-parse", "--short", "HEAD"], root).stdout.strip()
    if merged != committed:
        print(f"synced remote: merge commit {merged} created on top of {committed}")

    # --- push ---
    if args.push:
        if no_upstream:
            branch = git(["rev-parse", "--abbrev-ref", "HEAD"], root).stdout.strip()
            if branch == "HEAD":
                fail("detached HEAD: cannot push without a branch.")
            git(["push", "-u", "origin", branch], root, capture=False)
        else:
            git(["push"], root, capture=False)
        print("pushed.")


if __name__ == "__main__":
    main()
