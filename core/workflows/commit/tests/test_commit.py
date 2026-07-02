"""Tests for commit.py — the deterministic rbtv-commit staging engine.

Each test builds a throwaway git repo in a tmp dir, performs a real working-tree
change, then runs commit.py inside it and inspects the resulting commit object.
No network: every repo is local with no remote, so the remote-sync paths are
inert and only the staging gate + commit are exercised.
"""
import os
import subprocess
import sys

import pytest

COMMIT_PY = os.path.join(os.path.dirname(os.path.dirname(__file__)), "commit.py")


def git(args, cwd):
    res = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    assert res.returncode == 0, f"git {' '.join(args)} failed: {res.stderr or res.stdout}"
    return res.stdout


def run_commit(repo, files, message="test commit"):
    """Run commit.py inside `repo` requesting `files`. Returns the CompletedProcess."""
    argv = [sys.executable, COMMIT_PY, "-m", message]
    for f in files:
        argv += ["-f", f]
    return subprocess.run(argv, cwd=repo, text=True, capture_output=True)


def commit_message(repo, ref="HEAD"):
    """The full commit message recorded in `ref`."""
    return git(["log", "-1", "--format=%B", ref], repo)


def commit_files(repo, ref="HEAD"):
    """The set of paths recorded in `ref`'s commit object."""
    out = git(["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", ref], repo)
    return {ln for ln in out.splitlines() if ln}


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(["init", "-q"], r)
    git(["config", "user.email", "t@t.test"], r)
    git(["config", "user.name", "test"], r)
    git(["config", "commit.gpgsign", "false"], r)
    return r


def write(repo, rel, content="x\n"):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def test_folder_move_stages_delete_and_add(repo):
    """The regression case: a folder moved on disk (source dir gone) must commit,
    with the old files recorded as deletions and the new files as additions."""
    # Seed a committed folder with two files.
    write(repo, "old/a.md", "alpha\n")
    write(repo, "old/b.md", "beta\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    # Move the whole folder old/ -> new/ (the source dir no longer exists on disk).
    git(["mv", "old", "new"], repo)
    assert not (repo / "old").exists()

    # Commit the move, passing BOTH old and new paths.
    res = run_commit(repo, ["old", "new"], "move old to new")
    assert res.returncode == 0, f"commit.py aborted: {res.stderr}\n{res.stdout}"

    files = commit_files(repo)
    assert files == {"old/a.md", "old/b.md", "new/a.md", "new/b.md"}, files

    # Old side gone, new side present in the tree after the commit.
    assert not (repo / "old").exists()
    assert (repo / "new" / "a.md").exists()


def test_single_file_rename(repo):
    """A single-file move (most common rename) also commits via the gone-source path."""
    write(repo, "doc.md", "hi\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    git(["mv", "doc.md", "renamed.md"], repo)
    res = run_commit(repo, ["doc.md", "renamed.md"], "rename doc")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert commit_files(repo) == {"doc.md", "renamed.md"}


def test_plain_add_still_works(repo):
    """Regression guard: a normal add of an existing path is unaffected by the fix."""
    write(repo, "file.md", "content\n")
    res = run_commit(repo, ["file.md"], "add file")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert commit_files(repo) == {"file.md"}


def test_bogus_path_fails_loud(repo):
    """A requested path that is neither on disk nor tracked stages nothing and is
    caught by the unmatched-paths gate — no silent empty commit."""
    write(repo, "real.md", "content\n")
    res = run_commit(repo, ["real.md", "ghost-dir"], "with ghost")
    assert res.returncode != 0
    assert "no changes to commit" in (res.stderr + res.stdout)


def test_message_file_multiline(repo, tmp_path):
    """A multi-line message supplied via -F/--message-file is committed verbatim —
    the shell-quoting-proof path. Special chars (@, backticks, ->) survive intact."""
    write(repo, "file.md", "content\n")
    msg = (
        "docs: move 4 tasks -> Phase-6 backlog\n"
        "\n"
        "- item with `backticks` and @literal chars\n"
        "- second bullet\n"
    )
    msg_file = tmp_path / "commit-msg.txt"
    msg_file.write_text(msg, encoding="utf-8")

    argv = [sys.executable, COMMIT_PY, "-F", str(msg_file), "-f", "file.md"]
    res = subprocess.run(argv, cwd=repo, text=True, capture_output=True)
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert commit_files(repo) == {"file.md"}
    # Committed message equals the file content (git strips only the trailing newline).
    assert commit_message(repo).strip() == msg.strip()


def test_message_and_message_file_mutually_exclusive(repo, tmp_path):
    """Giving both -m and -F is a loud error and makes no commit."""
    write(repo, "file.md", "content\n")
    msg_file = tmp_path / "m.txt"
    msg_file.write_text("from file\n", encoding="utf-8")
    argv = [sys.executable, COMMIT_PY, "-m", "inline", "-F", str(msg_file), "-f", "file.md"]
    res = subprocess.run(argv, cwd=repo, text=True, capture_output=True)
    assert res.returncode != 0
    assert "exactly one of" in (res.stderr + res.stdout)


def test_no_message_fails_loud(repo):
    """Neither -m nor -F is a loud error."""
    write(repo, "file.md", "content\n")
    argv = [sys.executable, COMMIT_PY, "-f", "file.md"]
    res = subprocess.run(argv, cwd=repo, text=True, capture_output=True)
    assert res.returncode != 0
    assert "exactly one of" in (res.stderr + res.stdout)


def test_move_excludes_parallel_staged_file(repo):
    """A move commit must not carry an unrelated file a parallel session left
    staged. The reset gate unstages it; the commit holds only the move, and the
    unrelated file's working-tree change is preserved (left unstaged)."""
    write(repo, "old/a.md", "alpha\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    git(["mv", "old", "new"], repo)
    # An unrelated change left staged by a "parallel session".
    write(repo, "unrelated.md", "noise\n")
    git(["add", "unrelated.md"], repo)

    res = run_commit(repo, ["old", "new"], "move only")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    # Only the move is committed — the foreign file is not.
    assert commit_files(repo) == {"old/a.md", "new/a.md"}
    # Its working-tree change survives, simply left unstaged.
    assert (repo / "unrelated.md").read_text() == "noise\n"
    status = git(["status", "--porcelain", "unrelated.md"], repo)
    assert status.startswith("??") or status.startswith(" "), status
