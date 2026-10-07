#!/usr/bin/env python3
"""Deterministic git commit for the rbtv-commit workflow.

Runs INSIDE the target repo (uses the current working directory to locate the
repo root). The calling agent supplies the judgment — which files, what message
— and this script owns all the mechanics in one invocation: remote sync, staging
the requested paths, the commit, and an optional push.

It fails loudly (non-zero exit + a clear message) and leaves NO commit — unless
the message says, in words, that the commit was made — on:
  - a real merge conflict while syncing the remote,
  - any OTHER remote-sync failure (stale index.lock, network/auth, refused
    fast-forward) — reported as its own class, never as a conflict,
  - a requested file that has no changes to commit.

The repository's index is shared with every parallel session, so this script
stages the requested paths and touches NO other entry: what another session
staged (a changed file, a `git mv`, a new file) stays staged exactly as it was.
The COMMIT is bounded by a temporary index (`GIT_INDEX_FILE`) built from HEAD
plus the requested paths' entries, and is made from that index alone: an entry
another session stages outside the requested paths, before or during the run, is
never committed. Committing from the index, not from the working tree, is also
what carries an executable bit staged with `git update-index --chmod=+x`.

The commit names the commit its tree was built from as its parent, and the
branch moves to it only while its tip is still that parent. A commit another
session makes during the run is therefore never reverted: this run's commit is
rebuilt on top of it, or — when that commit changed a requested path — the run
fails with no commit, rather than overwrite it. `committed <hash>` is printed
only while the branch holds that commit.

Remote sync is commit-first: the requested files are committed locally, THEN the
remote is pulled. A clean auto-merge is handled silently; a real conflict aborts
the merge and undoes the local commit, so no commit survives and the requested
changes are left staged in the working tree — never trapped in a stash. Other
uncommitted work in the tree is untouched throughout. Git refuses a merge while
any entry is staged, so a pull that needs one fails, and is undone the same way,
for as long as another session's entries are staged. The undo removes this run's
commit and nothing else: when another session moved the branch after that commit,
nothing is undone and the error says the commit was made and where it is. The pull
is always a merge (`--no-rebase`), whatever `pull.rebase` says: a rebase would
replace this run's commit with a copy, and the undo and every statement about
the commit hold it by its hash.

A merge, rebase, cherry-pick or revert that is already in progress in the working
tree belongs to whoever started it, and this script leaves it exactly as it is:
it refuses a requested path that operation left in conflict, and it does not
pull (git cannot, and a failed pull would be cleaned up over that operation).
The commit is still made, and the output says that the operation is in progress
and what was not done because of it.

Paths are repo-root-relative. A rename is two paths (old + new) — pass both.

A path may be a FILE or a DIRECTORY. A directory includes every changed file
beneath it (added, modified, deleted) — use it when a cluster touches more files
than fit on a command line. The commit stays exact: only changes UNDER a
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
import tempfile


def fail(msg, code=1):
    print(f"commit.py: ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def warn(msg):
    print(f"commit.py: WARNING: {msg}", file=sys.stderr)


# Git reads and writes BYTES, and the pipes carry them unchanged: the text is
# encoded and decoded here, never by a text-mode pipe. A text-mode pipe also
# rewrites line endings — on Windows it writes every "\n" as "\r\n", which git
# then stores (`commit-tree -F -` keeps a message byte for byte), and on every
# system it reads a "\r" as "\n", so a path holding a carriage return comes back
# as another path. UTF-8, whatever the OS locale: git emits UTF-8 path bytes, and
# under the locale codec (cp1252 on Windows) a non-ASCII path read from git never
# matches the same path from argv. `env` selects the index a command works on
# (GIT_INDEX_FILE); `stdin` feeds it; `root=None` runs in the current directory.
def git(args, root, check=True, capture=True, env=None, stdin=None):
    res = subprocess.run(["git", *args], cwd=root, capture_output=capture, env=env,
                         input=None if stdin is None else stdin.encode("utf-8", "surrogateescape"))
    if capture:
        res.stdout = res.stdout.decode("utf-8", "surrogateescape")
        res.stderr = res.stderr.decode("utf-8", "surrogateescape")
    if check and res.returncode != 0:
        out = (res.stderr or res.stdout or "").strip()
        fail(f"git {' '.join(args)} failed: {out}")
    return res


def git_ok(args, root):
    return git(args, root, check=False).returncode == 0


def staged_mode_changes(root, paths):
    """Executable-bit changes staged under `paths`, as {path: "+x" | "-x"}. A new
    file counts from mode 100644, the mode git gives a new regular file."""
    raw = git(["diff", "--cached", "--raw", "--no-renames", "-z", "--", *paths], root).stdout.split("\0")
    changes = {}
    for meta, path in zip(raw[0::2], raw[1::2]):
        old, new = meta[1:].split(" ")[:2]
        if new == "100755" and old != "100755":
            changes[path] = "+x"
        elif new == "100644" and old == "100755":
            changes[path] = "-x"
    return changes


# What git keeps in its directory for as long as an operation is unfinished.
OPERATION_MARKERS = (("MERGE_HEAD", "merge"), ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert"),
                     ("rebase-merge", "rebase"), ("rebase-apply", "rebase"))


def operation_in_progress(root):
    """The operation left unfinished in this working tree — "merge", "rebase",
    "cherry-pick" or "revert" — or "" when there is none. `--absolute-git-dir`
    (not root/.git) so this holds in a linked worktree, where .git is a file
    pointing elsewhere."""
    git_dir = git(["rev-parse", "--absolute-git-dir"], root).stdout.strip()
    return next((name for marker, name in OPERATION_MARKERS
                 if os.path.exists(os.path.join(git_dir, marker))), "")


def covers(path, file):
    """A requested path covers a file when it IS that file, or is a parent
    directory of it."""
    return file == path or file.startswith(path + "/")


def commit_requested(root, requested, message):
    """Commit the requested paths' entries of the shared index on top of the
    branch, and return (parent, commit) — full hashes, parent "" for a first commit.

    A bare `git commit` commits the whole shared index, so whatever a parallel
    session has staged rides along silently (measured 2026-08-11: commit
    f9cc81fa carried 4 files for 1). The commit is made from a temporary index
    instead: the parent's tree with the requested paths replaced by their entries
    from the shared index, and nothing else can enter it.

    The parent is NAMED (`git commit-tree -p`), never left to whatever the branch
    holds when the commit is written, and the branch advances by one
    compare-and-swap that git refuses unless its tip is still that parent. So the
    commit always carries exactly its parent's tree plus the requested paths. When
    another session committed in between, the commit is rebuilt on that session's
    commit — unless that commit changed a requested path, which stops the run:
    rebuilding would overwrite its change with the staged entry.

    `git commit-tree` runs no hook, so the hooks that `git commit` runs are run
    here, with the outcomes `git commit` gives them: pre-commit and commit-msg
    each refuse the commit by failing, a message that commit-msg leaves empty
    refuses it too, and post-commit runs after the branch moved, so its failure
    is a warning and the commit stands. prepare-commit-msg is not run."""
    subject = message.splitlines()[0]
    before = git(["rev-parse", "--verify", "-q", "HEAD"], root, check=False).stdout.strip()
    with tempfile.TemporaryDirectory(prefix="rbtv-commit-") as tmp:
        own = {**os.environ, "GIT_INDEX_FILE": os.path.join(tmp, "index")}
        msg_file = os.path.join(tmp, "COMMIT_EDITMSG")
        entries = git(["ls-files", "-s", "-z", "--", *requested], root).stdout
        while True:
            git(["read-tree", before or "--empty"], root, env=own)
            # -f: git otherwise refuses to drop an entry that differs from both HEAD
            # and the file on disk, which it does once another session moved HEAD.
            git(["rm", "-r", "-q", "-f", "--cached", "--ignore-unmatch", "--", *requested], root, env=own)
            git(["update-index", "-z", "--index-info"], root, env=own, stdin=entries)

            # --no-renames so a rename reads as delete(old) + add(new) — both requested
            # paths then appear, instead of git collapsing them into a single destination name.
            # -z: NUL-separated, UNQUOTED paths. Without it git quote-escapes any path
            # with non-ASCII bytes (default core.quotepath=true), so a file like
            # "Relatório.pdf" reads back escaped and never matches the raw requested
            # path — a spurious unmatched mismatch. -z sidesteps quoting entirely.
            to_commit = {p for p in git(["diff", "--cached", "--name-only", "--no-renames", "-z"],
                                        root, env=own).stdout.split("\0") if p}
            # A directory path is satisfied when it covers >=1 file to commit; an exact
            # file path when it equals one. Either way: no covered change → nothing to commit.
            unmatched = [p for p in requested if not any(covers(p, s) for s in to_commit)]
            if unmatched:
                fail("these requested paths have no changes to commit: " + ", ".join(sorted(unmatched)))

            git(["hook", "run", "--ignore-missing", "pre-commit"], root, env=own)
            with open(msg_file, "w", encoding="utf-8", newline="") as fh:
                fh.write(message.rstrip("\n") + "\n")  # a whole last line, as `git commit` hands it over
            git(["hook", "run", "--ignore-missing", "commit-msg", "--", msg_file], root, env=own)
            with open(msg_file, encoding="utf-8", newline="") as fh:
                # `git stripspace` is the cleanup `git commit -m` applies to a message.
                text = git(["stripspace"], root, stdin=fh.read()).stdout
            if not text.strip():
                fail("the commit-msg hook left the commit message empty. No commit made; your changes are staged.")
            tree = git(["write-tree"], root, env=own).stdout.strip()
            new = git(["commit-tree", tree, *(["-p", before] if before else []), "-F", "-"],
                      root, stdin=text).stdout.strip()
            swap = git(["update-ref", "-m", f"commit: {subject}", "HEAD", new, before], root, check=False)
            if swap.returncode == 0:
                break
            tip = git(["rev-parse", "--verify", "-q", "HEAD"], root, check=False).stdout.strip()
            if tip == before:
                fail("could not move the branch to the new commit. No commit made; your changes are "
                     "staged. Git reported:\n" + ((swap.stderr or "").strip() or f"git update-ref exited {swap.returncode}"))
            # Another session moved the branch during this run. What it did to the
            # requested paths: the diff from this run's parent, or every such path
            # in its tree when this run started on an empty branch.
            theirs = (["diff", "--name-only", "-z", before, tip] if before
                      else ["ls-tree", "-r", "--name-only", "-z", tip])
            clash = [p for p in git([*theirs, "--", *requested], root).stdout.split("\0") if p] if tip else []
            if clash:
                fail(f"another session committed these requested paths during this run (branch tip is now "
                     f"{tip[:7]}): " + ", ".join(clash) + ". No commit made, so its change is not "
                     "overwritten. Check that those paths hold what you intend to commit, then retry.")
            before = tip
    hook = git(["hook", "run", "--ignore-missing", "post-commit"], root, check=False)
    if hook.returncode != 0:
        warn(f"the post-commit hook failed (exit {hook.returncode}). The commit was made and stands. "
             "The hook reported:\n" + (hook.stderr or hook.stdout or "").strip())
    return before, new


def off_branch(committed, tip, undo_note=""):
    """The sentence for a commit of this run that the branch no longer contains."""
    return (f" Commit {committed} was made, but another session moved the branch to "
            f"{tip[:len(committed)]}, which does not contain it{undo_note}. Recover it "
            f"with `git cherry-pick {committed}` if it is still wanted.")


def undo_commit(root, committed):
    """Take the just-made commit `committed` back off the branch, and return
    (undone, sentence) — the sentence says what the branch holds now.

    The undo is one compare-and-swap: the branch moves to the commit's parent
    ONLY while its tip is still that commit, so it removes this run's commit and
    nothing else. The index is not touched, so the requested changes stay staged.
    When another session moved the branch since the commit, nothing is undone."""
    own, parent = git(["rev-parse", committed, committed + "^"], root).stdout.split()
    undo = git(["update-ref", "-m", "rbtv-commit: undo after a failed pull", "HEAD", parent, own],
               root, check=False)
    if undo.returncode == 0:
        return True, " No commit made; your changes are staged."
    tip = git(["rev-parse", "HEAD"], root, check=False).stdout.strip()
    if tip == own:
        return False, (f" Commit {committed} was made and is still the branch tip: undoing it failed ("
                       + ((undo.stderr or "").strip() or f"git update-ref exited {undo.returncode}") + ").")
    if git_ok(["merge-base", "--is-ancestor", own, "HEAD"], root):
        return False, (f" Commit {committed} was made and STAYS on the branch: another session "
                       f"committed on top of it (branch tip is now {tip[:len(committed)]}), so it was not undone.")
    return False, off_branch(committed, tip, "; nothing was undone")


def sync_after_commit(root, committed):
    """Pull remote changes on top of the just-made commit `committed`. On ANY
    failure, abort the merge and undo that commit (see `undo_commit`), so the
    requested changes are left staged in the working tree. The undo is skipped
    when another session moved the branch since the commit; the message then
    says the commit was made and where it is.

    The caller runs this ONLY while no operation is in progress in the working
    tree (`operation_in_progress`): that is what makes the merge found after a
    failed pull this pull's own, and so this function's to abort.

    A failed pull is CLASSIFIED before it is reported. A non-zero pull is not
    evidence of a conflict: a stale `.git/index.lock`, a network or auth failure,
    or a refused fast-forward all exit non-zero with no conflict anywhere.
    Reporting those as a conflict sends the caller into the conflict-resolution
    workflow hunting for conflicts that do not exist, so the two cases carry
    different messages and the real git error is surfaced verbatim."""
    pull = git(["pull", "--no-edit", "--no-rebase"], root, check=False)
    if pull.returncode == 0:
        return
    # Ground truth for "was this a conflict": unmerged index entries, or a merge
    # left in progress.
    conflicts = git(["diff", "--name-only", "--diff-filter=U"], root, check=False).stdout.strip()
    merging = operation_in_progress(root) == "merge"
    git(["merge", "--abort"], root, check=False)
    mine = set(git(["diff-tree", "--no-commit-id", "--name-only", "-r", "-z", committed], root).stdout.split("\0"))
    undone, left = undo_commit(root, committed)
    # What the index holds beyond HEAD, less this run's own paths, is what other
    # sessions staged — the entries git refuses to merge over.
    foreign = [p for p in git(["diff", "--cached", "--name-only", "-z"], root, check=False).stdout.split("\0")
               if p and p not in mine]
    retry = "then retry" if undone else "then run `git pull --no-edit --no-rebase`; do NOT rerun rbtv-commit for these paths"
    if conflicts or merging:
        msg = "merge conflict pulling remote changes"
        if conflicts:
            msg += " in: " + ", ".join(conflicts.splitlines())
        fail(msg + "." + left + f" Resolve the remote divergence, {retry}.")
    err = (pull.stderr or pull.stdout or "").strip() or f"git pull exited {pull.returncode}"
    if foreign:
        fail("could not pull remote changes — NOT a merge conflict: git refuses a merge while "
             "entries are staged, and other sessions have these staged: " + ", ".join(foreign)
             + "." + left + f" NEVER unstage them; once they are committed, {retry}. Git reported:\n" + err)
    fail("could not pull remote changes — NOT a merge conflict (no unmerged paths, no merge "
         "in progress)." + left + f" Fix the cause reported by git below, {retry}:\n" + err)


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

    res = git(["rev-parse", "--show-toplevel"], None, check=False)
    if res.returncode != 0:
        fail("not inside a git repository (run this from within the target repo).")
    root = res.stdout.strip()

    requested = []
    for f in args.files:
        f = f.rstrip("/")  # a trailing slash names the same path
        if f and f not in requested:
            requested.append(f)

    # --- fetch + learn whether the remote is ahead (sync happens after commit) ---
    no_upstream = True
    behind = False
    if git(["remote"], root).stdout.strip():
        git(["fetch"], root)
        if git_ok(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], root):
            no_upstream = False
            count = git(["rev-list", "HEAD..@{u}", "--count"], root).stdout.strip()
            behind = count not in ("", "0")

    # --- stage ONLY the requested paths; every other index entry is left as it is ---
    # `git add` takes the mode from the file on disk, so an executable bit staged
    # with `git update-index --chmod` (the only way to record one on Windows) is
    # read before the add and put back after it.
    # Staging a path that an operation in progress left in conflict would mark
    # that conflict resolved, in an operation this run did not start.
    held = operation_in_progress(root)
    if held:
        unmerged = sorted({ln.split("\t", 1)[1] for ln in git(
            ["ls-files", "-u", "-z", "--", *requested], root).stdout.split("\0") if ln})
        if unmerged:
            fail(f"a {held} is in progress in this working tree and left these requested paths in "
                 "conflict: " + ", ".join(unmerged) + f". No commit made and nothing was staged: the "
                 f"{held} is exactly as it was. Resolve the paths and finish the {held} with git "
                 "itself; rbtv-commit never finishes an operation it did not start.")
    staged_modes = staged_mode_changes(root, requested)
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
    for path, change in staged_modes.items():
        if os.path.lexists(os.path.join(root, path)):
            git(["update-index", f"--chmod={change}", "--", path], root)

    # --- commit the requested entries on top of the branch, then sync ---
    before, new = commit_requested(root, requested, message)
    committed = git(["rev-parse", "--short", new], root).stdout.strip()
    # Read again, immediately before the pull: a failed pull is cleaned up with
    # `git merge --abort`, which must never reach an operation this run did not start.
    held = operation_in_progress(root)
    pulled = bool(behind and before and not held)
    if pulled:
        sync_after_commit(root, committed)
    # `committed` is printed only while the branch holds that commit: another
    # session may have moved the branch off it since it was made.
    if not git_ok(["merge-base", "--is-ancestor", new, "HEAD"], root):
        tip = git(["rev-parse", "HEAD"], root, check=False).stdout.strip()
        fail(off_branch(committed, tip).strip() + " Nothing was pushed.")
    # Read the files back from the commit OBJECT (not the input list) so the output
    # is ground truth the caller can trust without re-running `git show`.
    in_commit = [ln for ln in git(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "-z", committed], root
    ).stdout.split("\0") if ln]
    print(f"committed {committed}: {message.splitlines()[0]}")
    print(f"files in commit ({len(in_commit)}): " + ", ".join(in_commit))
    merged = git(["rev-parse", "--short", "HEAD"], root).stdout.strip()
    if pulled and merged != committed:
        print(f"synced remote: merge commit {merged} created on top of {committed}")
    if held:
        unpulled = behind and bool(before)
        note = (f"a {held} is in progress in this working tree. This run did not start it and left it "
                f"exactly as it was. Commit {committed} was made.")
        if unpulled:
            note += (f" The remote is ahead and was NOT pulled: git cannot pull while a {held} is in "
                     f"progress. Run `git pull --no-edit --no-rebase` once the {held} is finished.")
        if unpulled and args.push:
            fail(note + " Nothing was pushed; do NOT rerun rbtv-commit for these paths.")
        warn(note)

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
