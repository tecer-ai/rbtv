#!/usr/bin/env python3
"""Age out ~/.cache/agent-tmp — the disk-backed seat tmp location (task 7.404).

Dry run unless --go. Never /tmp, never tmpfs: both the path and its backing
filesystem are checked before anything is removed.
"""
import argparse
import os
import shutil
import sys
import time

# The location coord.py hands kit-launched seats as TMPDIR (its AGENT_TMPDIR, task 7.400),
# resolved per-user so no host path is baked into the repo.
ROOT = os.environ.get("RBTV_AGENT_TMPDIR") or os.path.expanduser("~/.cache/agent-tmp")
MIN_DAYS = 7


def fstype(path):
    """Filesystem type backing `path`, via the longest matching mount point."""
    best, kind = "", ""
    with open("/proc/self/mounts") as fh:
        for line in fh:
            parts = line.split()
            if len(parts) < 3:
                continue
            mnt, typ = parts[1], parts[2]
            if (path == mnt or path.startswith(mnt.rstrip("/") + "/")) and len(mnt) >= len(best):
                best, kind = mnt, typ
    return kind


def size_of(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path, onerror=lambda e: None):
        for name in filenames:
            try:
                total += os.lstat(os.path.join(dirpath, name)).st_size
            except OSError:
                pass
    return total


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=MIN_DAYS,
                    help=f"age floor in days (minimum {MIN_DAYS})")
    ap.add_argument("--go", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("--root", default=ROOT, help="alternate root, for fixture proofs")
    args = ap.parse_args()

    if args.days < MIN_DAYS:
        sys.exit(f"refusing: age floor {args.days}d is below the {MIN_DAYS}d minimum")

    root = os.path.realpath(args.root)
    if root == "/tmp" or root.startswith("/tmp/"):
        sys.exit("refusing: /tmp is never this cleaner's business")
    kind = fstype(root)
    if kind in ("tmpfs", "ramfs", "devtmpfs"):
        sys.exit(f"refusing: {root} is on {kind} — session state on tmpfs is owner-gated")
    if not os.path.isdir(root):
        sys.exit(f"refusing: {root} is not a directory")

    cutoff = time.time() - args.days * 86400
    # ponytail: top-level mtime is the age signal, as in ~/.local/bin/tmpclean. A session
    # dir whose nested files are fresh but whose own mtime is old would age out early;
    # walk for a max-mtime if that ever bites.
    stale = [e for e in os.scandir(root)
             if e.stat(follow_symlinks=False).st_mtime < cutoff]

    freed = 0
    for e in sorted(stale, key=lambda e: e.name):
        isdir = e.is_dir(follow_symlinks=False)
        n = size_of(e.path) if isdir else e.stat(follow_symlinks=False).st_size
        freed += n
        if args.go:
            if isdir:
                shutil.rmtree(e.path, ignore_errors=True)
            else:
                os.unlink(e.path)
        print(f"{'removed' if args.go else 'would remove'} {e.name} ({n / 1e6:.1f} MB)")

    verb = "recovered" if args.go else "would recover"
    print(f"{len(stale)} entries older than {args.days}d — {verb} {freed / 1e6:.1f} MB from {root}")
    if not args.go and stale:
        print("dry run — re-run with --go to delete")


if __name__ == "__main__":
    main()
