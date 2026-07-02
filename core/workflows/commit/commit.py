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

A path may be a FILE or a DIRECTORY. A directory includes every changed file
beneath it (added, modified, deleted) — use it when a cluster touches more files
than fit on a command line. The staging gate stays exact: only changes UNDER a
listed path are committed, but a directory sweeps in whatever currently lives
there, including a parallel session's files — prefer explicit file paths when
precision matters.

The message is supplied EITHER inline (`-m`) for a simple single-line message, OR
from a file (`-F/--message-file`). Prefer `-F` for any multi-line message: write
the message to a file with your editor/Write tool and pass its path, so the shell
never has to quote a multi-line string — this sidesteps the here-string / heredoc
quoting footguns (e.g. PowerShell `@'...'@` syntax pasted into a POSIX shell) that
silently corrupt the message. Exactly one of `-m` / `-F` must be given.

Usage:
    python commit.py -m "feat: ..." -f path/a -f dir/b [--push]
    python commit.py -F msg.txt    -f path/a -f dir/b [--push]
"""
import argparse
import os
import subprocess
import sys


def fail(msg, code=1):
    print(f"commit.py: ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


# Decode git output as UTF-8 (git emits UTF-8 path bytes regardless of the OS
# locale). Without this, text=True uses the locale codec — cp1252 on Windows —
# so a non-ASCII path read from git never matches the same path from argv
# (already proper Unicode), breaking the staging gate's exact comparison.
def git(args, root, check=True, capture=True):
    res = subprocess.run(["git", *args], cwd=root, text=True, capture_output=capture,
                         encoding="utf-8", errors="surrogateescape")
    if check and res.returncode != 0:
        out = (res.stderr or res.stdout or "").strip()
        fail(f"git {' '.join(args)} failed: {out}")
    return res


def git_ok(args, root):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                          encoding="utf-8", errors="surrogateescape").returncode == 0


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
    p.add_argument("-m", "--message", help="Inline commit message (single-line / simple). "
                   "Mutually exclusive with -F.")
    p.add_argument("-F", "--message-file", dest="message_file",
                   help="Path to a UTF-8 file holding the commit message. Preferred for any "
                        "multi-line message: write the file with your Write tool so the shell "
                        "never quotes the message (no here-string / heredoc footguns). "
                        "Mutually exclusive with -m.")
    p.add_argument("-f", "--file", dest="files", action="append", required=True,
                   help="A repo-root-relative file OR directory to include (a directory "
                        "includes every changed file beneath it). Repeat for each path.")
    p.add_argument("--push", action="store_true", help="Push after a successful commit.")
    args = p.parse_args()

    # Exactly one message source. Reading from a file is the shell-quoting-proof path.
    if bool(args.message) == bool(args.message_file):
        fail("provide exactly one of -m/--message or -F/--message-file.")
    if args.message_file:
        try:
            with open(args.message_file, encoding="utf-8") as fh:
                message = fh.read()
        except OSError as e:
            fail(f"cannot read --message-file {args.message_file!r}: {e}")
    else:
        message = args.message
    if not message.strip():
        fail("commit message is empty.")

    res = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                         encoding="utf-8", errors="surrogateescape")
    if res.returncode != 0:
        fail("not inside a git repository (run this from within the target repo).")
    root = res.stdout.strip()

    requested = []
    for f in args.files:
        f = f.rstrip("/")  # a trailing slash names the same path
        if f and f not in requested:
            requested.append(f)

    def covers(path, staged_file):
        """A requested path covers a staged file when it IS that file, or is a
        parent directory of it."""
        return staged_file == path or staged_file.startswith(path + "/")

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
        if os.path.exists(os.path.join(root, f)):
            git(["add", "-A", "--", f], root)
        else:
            # A move/deletion SOURCE: the path is gone from the working tree, so
            # `git add -A -- <gone-path>` errors ("pathspec did not match any
            # files") and never stages the deletion. Stage the index removal
            # instead. --cached: the working-tree copy is already gone; -r:
            # cover a whole directory; --ignore-unmatch: a path neither on disk
            # nor tracked stages nothing (caught by the unmatched gate below)
            # rather than erroring here.
            git(["rm", "-r", "--cached", "--ignore-unmatch", "--", f], root)

    # --no-renames so a staged rename reads as delete(old) + add(new) — both requested
    # paths then appear, instead of git collapsing them into a single destination name.
    # -z: NUL-separated, UNQUOTED paths. Without it git quote-escapes any path
    # with non-ASCII bytes (default core.quotepath=true), so a staged file like
    # "Relatório.pdf" reads back escaped and never matches the raw requested
    # path — a spurious foreign/unmatched mismatch. -z sidesteps quoting entirely.
    staged = {p for p in git(["diff", "--cached", "--name-only", "--no-renames", "-z"], root).stdout.split("\0") if p}
    # A directory path is satisfied when it covers >=1 staged file; an exact file
    # path when it equals one. Either way: no covered change → nothing to commit.
    unmatched = [p for p in requested if not any(covers(p, s) for s in staged)]
    if unmatched:
        fail("these requested paths have no changes to commit: " + ", ".join(sorted(unmatched)))
    # A staged file under NO requested path must never ride along.
    foreign = sorted(s for s in staged if not any(covers(p, s) for p in requested))
    if foreign:
        fail("staged index does not match requested paths (unexpected): " + ", ".join(foreign))

    # --- commit (capturing the undo target first), then sync the remote on top ---
    before = git(["rev-parse", "HEAD"], root, check=False).stdout.strip()
    git(["commit", "-m", message], root)
    committed = git(["rev-parse", "--short", "HEAD"], root).stdout.strip()  # MY commit, before any sync merge
    if behind and before:
        sync_after_commit(root, before)
    # Read the files back from the commit OBJECT (not the input list) so the output
    # is ground truth the caller can trust without re-running `git show`.
    in_commit = [ln for ln in git(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "-z", committed], root
    ).stdout.split("\0") if ln]
    print(f"committed {committed}: {message.splitlines()[0]}")
    print(f"files in commit ({len(in_commit)}): " + ", ".join(in_commit))
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
