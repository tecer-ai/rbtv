"""Tests for commit.py — the deterministic rbtv-commit staging engine.

Each test builds a throwaway git repo in a tmp dir, performs a real working-tree
change, then runs commit.py inside it and inspects the resulting commit object.
No network: a repo has no remote, so the remote-sync paths are inert and only
the staging + commit are exercised — except the tests that build a local bare
remote to drive a refused pull.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

COMMIT_PY = os.path.join(os.path.dirname(__file__), "commit.py")

# Imported as a module (not just run as a subprocess) so the race tests below can
# wrap commit.py's own git helper and land a parallel session's `git add` or
# commit at an exact point inside the run.
_spec = importlib.util.spec_from_file_location("commit_mod", COMMIT_PY)
commit_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(commit_mod)


def git(args, cwd, stdin=None):
    res = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, input=stdin)
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
    p.write_text(content, encoding="utf-8")


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


def staged_entries(repo, *paths):
    """The staged changes (mode, blob and status per path), whole index or under `paths`."""
    return git(["diff", "--cached", "--raw", "--no-abbrev", "--no-renames", "--", *paths], repo)


def test_parallel_staged_entries_stay_staged(repo):
    """What a parallel session staged — a changed file, a `git mv` pair, a new
    file — is neither committed nor unstaged by a commit of other paths: after
    the commit the index holds exactly those entries, unchanged."""
    write(repo, "old/a.md", "alpha\n")
    write(repo, "theirs/changed.md", "v1\n")
    write(repo, "theirs/from.md", "moved\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    # The "parallel session": one changed file, one move, one new file, all staged.
    write(repo, "theirs/changed.md", "v2\n")
    git(["add", "theirs/changed.md"], repo)
    git(["mv", "theirs/from.md", "theirs/to.md"], repo)
    write(repo, "theirs/new.md", "new\n")
    git(["add", "theirs/new.md"], repo)
    theirs = staged_entries(repo, "theirs")
    assert len(theirs.splitlines()) == 4, theirs  # changed + move (delete, add) + new

    # This session: its own move, staged in the same index.
    git(["mv", "old", "new"], repo)
    res = run_commit(repo, ["old", "new"], "move only")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"

    assert commit_files(repo) == {"old/a.md", "new/a.md"}
    assert staged_entries(repo) == theirs


def test_deleted_file_commits(repo):
    """A file removed from disk is committed as a deletion from its path alone."""
    write(repo, "keep.md")
    write(repo, "gone.md")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    os.remove(repo / "gone.md")
    res = run_commit(repo, ["gone.md"], "delete")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert commit_files(repo) == {"gone.md"}
    assert git(["ls-tree", "-r", "--name-only", "HEAD"], repo).split() == ["keep.md"]


def test_staged_executable_bit_lands(repo):
    """An executable bit that exists only in the index (`git update-index
    --chmod=+x`, the one way to record it on Windows) is committed, on a tracked
    file whose content also changed and on a new file. The files on disk are
    never made executable."""
    write(repo, "tool.py", "#!/usr/bin/env python3\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    git(["update-index", "--chmod=+x", "tool.py"], repo)
    write(repo, "tool.py", "#!/usr/bin/env python3\nprint('v2')\n")
    write(repo, "new-tool.py", "#!/usr/bin/env python3\n")
    git(["add", "new-tool.py"], repo)
    git(["update-index", "--chmod=+x", "new-tool.py"], repo)

    res = run_commit(repo, ["tool.py", "new-tool.py"], "executable tools")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    modes = {ln.split("\t")[1]: ln.split()[0] for ln in git(["ls-tree", "HEAD"], repo).splitlines()}
    assert modes == {"tool.py": "100755", "new-tool.py": "100755"}, modes
    assert "v2" in git(["show", "HEAD:tool.py"], repo)


def remote_ahead(repo, tmp_path):
    """Seed `repo` (base.md, theirs.md), give it a local bare remote as upstream,
    and move that remote one commit ahead, so the next commit.py run must pull."""
    write(repo, "base.md")
    write(repo, "theirs.md", "v1\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    origin = tmp_path / "origin.git"
    git(["clone", "-q", "--bare", str(repo), str(origin)], tmp_path)
    git(["remote", "add", "origin", str(origin)], repo)
    git(["fetch", "-q", "origin"], repo)
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()
    git(["branch", "-q", f"--set-upstream-to=origin/{branch}"], repo)
    git(["config", "pull.rebase", "false"], repo)

    # The remote moves ahead (a commit pushed from a second clone).
    other = tmp_path / "other"
    git(["clone", "-q", str(origin), str(other)], tmp_path)
    git(["config", "user.email", "t@t.test"], other)
    git(["config", "user.name", "test"], other)
    git(["config", "commit.gpgsign", "false"], other)
    write(other, "remote.md")
    git(["add", "-A"], other)
    git(["commit", "-q", "-m", "remote"], other)
    git(["push", "-q"], other)


def test_pull_refused_over_parallel_staged_entries(repo, tmp_path):
    """The remote is ahead and a parallel session has an entry staged: git refuses
    the merge. The run fails naming that entry, makes no commit, and leaves both
    the parallel session's entry and the requested change staged."""
    remote_ahead(repo, tmp_path)

    write(repo, "theirs.md", "v2\n")
    git(["add", "theirs.md"], repo)
    theirs = staged_entries(repo, "theirs.md")
    head = git(["rev-parse", "HEAD"], repo)
    write(repo, "mine.md")

    res = run_commit(repo, ["mine.md"], "mine")
    assert res.returncode != 0
    assert "other sessions have these staged: theirs.md." in res.stderr, res.stderr
    assert git(["rev-parse", "HEAD"], repo) == head
    assert staged_entries(repo, "theirs.md") == theirs
    assert git(["diff", "--cached", "--name-only", "--", "mine.md"], repo).strip() == "mine.md"


def run_racing(repo, monkeypatch, at, race):
    """Run commit.py in-process for mine.md, calling `race()` once, the instant
    commit.py issues its first `git <at>`. Returns the exit code."""
    real_git = commit_mod.git
    fired = []

    def racing_git(args, root, **kw):
        if args and args[0] == at and not fired:
            fired.append(at)
            race()
        return real_git(args, root, **kw)

    monkeypatch.setattr(commit_mod, "git", racing_git)
    monkeypatch.setattr(sys, "argv", ["commit.py", "-m", "mine", "-f", "mine.md"])
    monkeypatch.chdir(repo)
    try:
        commit_mod.main()
        code = 0
    except SystemExit as exit_info:
        code = exit_info.code
    assert fired == [at]
    return code


def test_foreign_staged_in_race_window_excluded(repo, monkeypatch):
    """A parallel session's `git add` landing AFTER the staging and BEFORE the
    commit must not ride along (measured leak: f9cc81fa carried 4 files for 1).
    The race is made deterministic by wrapping commit.py's own git helper: the
    foreign file is staged the instant commit.py reads its own entries back from
    the shared index (`ls-files`), which it does once, after its staging."""
    write(repo, "mine.md", "v1\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)

    write(repo, "mine.md", "v2\n")
    write(repo, "foreign.md", "parallel session\n")

    assert run_racing(repo, monkeypatch, "ls-files", lambda: git(["add", "foreign.md"], repo)) == 0

    assert commit_files(repo) == {"mine.md"}
    assert git(["diff", "--cached", "--name-only"], repo).strip() == "foreign.md"


def refused_pull_setup(repo, tmp_path):
    """The remote is ahead and a parallel session has theirs.md staged, so the
    pull is refused; mine.md is the requested change and foreign.md is what a
    parallel session will commit during the run."""
    remote_ahead(repo, tmp_path)
    write(repo, "theirs.md", "v2\n")
    git(["add", "theirs.md"], repo)
    write(repo, "mine.md")
    write(repo, "foreign.md", "parallel session\n")


def foreign_commit(repo):
    git(["add", "foreign.md"], repo)
    git(["commit", "-q", "-m", "foreign", "--", "foreign.md"], repo)


def subjects(repo):
    """The subject of every commit reachable from the branch."""
    return git(["log", "--format=%s"], repo).splitlines()


def test_foreign_commit_before_own_commit_survives_failed_pull(repo, tmp_path, monkeypatch, capsys):
    """A parallel session commits AFTER the tool read HEAD and BEFORE the tool's
    own commit, then the pull is refused. The undo removes the tool's commit
    alone: the branch ends on the parallel session's commit, the requested change
    stays staged, and a retry commits once."""
    refused_pull_setup(repo, tmp_path)
    assert run_racing(repo, monkeypatch, "read-tree", lambda: foreign_commit(repo)) != 0
    err = capsys.readouterr().err

    assert subjects(repo)[0] == "foreign", subjects(repo)
    assert "mine" not in subjects(repo)
    assert "other sessions have these staged: theirs.md. No commit made; your changes are staged." in err, err
    assert git(["diff", "--cached", "--name-only", "--", "mine.md"], repo).strip() == "mine.md"

    # The retry the message asks for: once the staged entry is committed.
    git(["commit", "-q", "-m", "theirs", "--", "theirs.md"], repo)
    res = run_commit(repo, ["mine.md"], "mine")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert subjects(repo).count("mine") == 1 and "foreign" in subjects(repo), subjects(repo)


def test_foreign_commit_after_own_commit_survives_failed_pull(repo, tmp_path, monkeypatch, capsys):
    """A parallel session commits on top of the tool's commit, then the pull is
    refused. Nothing is undone: both commits stay on the branch, the error says
    the commit was made, and rerunning the tool does not commit a second time."""
    refused_pull_setup(repo, tmp_path)
    assert run_racing(repo, monkeypatch, "pull", lambda: foreign_commit(repo)) != 0
    err = capsys.readouterr().err

    assert subjects(repo)[:2] == ["foreign", "mine"], subjects(repo)
    assert "was made and STAYS on the branch" in err, err
    assert "No commit made" not in err, err
    assert "do NOT rerun rbtv-commit" in err, err
    assert "other sessions have these staged: theirs.md." in err, err

    res = run_commit(repo, ["mine.md"], "mine")
    assert res.returncode != 0
    assert "no changes to commit" in res.stderr, res.stderr
    assert subjects(repo).count("mine") == 1, subjects(repo)


def test_branch_moved_off_own_commit_is_left_as_found(repo, tmp_path, monkeypatch, capsys):
    """A parallel session moves the branch off the tool's commit, then the pull
    is refused. The tool undoes nothing, leaves the branch where that session
    put it, and names the commit so it can be recovered."""
    refused_pull_setup(repo, tmp_path)
    seed = git(["rev-parse", "HEAD"], repo).strip()

    def replace_tip():
        git(["update-ref", "HEAD", seed], repo)
        foreign_commit(repo)

    assert run_racing(repo, monkeypatch, "pull", replace_tip) != 0
    err = capsys.readouterr().err

    assert subjects(repo)[0] == "foreign" and "mine" not in subjects(repo), subjects(repo)
    assert "which does not contain it; nothing was undone" in err, err
    assert "No commit made" not in err, err
    lost = err.split("git cherry-pick ")[1].split("`")[0]
    assert git(["log", "-1", "--format=%s", lost], repo).strip() == "mine"


# `read-tree` is the first thing commit.py does after it reads HEAD, and it does
# it nowhere else: a race fired there lands between that read and the commit.
def test_foreign_commit_in_window_keeps_its_content(repo, monkeypatch, capsys):
    """A parallel session commits — one file added, one changed — AFTER the tool
    read HEAD and BEFORE the tool's own commit. The tool's commit lands on top of
    that commit and carries the requested path alone: both of the parallel
    session's changes are in the branch tip."""
    write(repo, "base.md", "v1\n")
    write(repo, "mine.md", "v1\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    write(repo, "mine.md", "v2\n")

    def foreign_add_and_change():
        write(repo, "foreign.md", "parallel session\n")
        write(repo, "base.md", "v2\n")
        git(["add", "foreign.md", "base.md"], repo)
        git(["commit", "-q", "-m", "foreign", "--", "foreign.md", "base.md"], repo)

    assert run_racing(repo, monkeypatch, "read-tree", foreign_add_and_change) == 0

    assert git(["show", "HEAD:foreign.md"], repo) == "parallel session\n"
    assert git(["show", "HEAD:base.md"], repo) == "v2\n"
    assert git(["show", "HEAD:mine.md"], repo) == "v2\n"
    assert commit_files(repo) == {"mine.md"}
    assert subjects(repo) == ["mine", "foreign", "seed"], subjects(repo)
    foreign = git(["rev-parse", "HEAD~1"], repo).strip()
    git(["merge-base", "--is-ancestor", foreign, "HEAD"], repo)  # asserts exit 0
    assert git(["status", "--porcelain"], repo) == ""
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert f"committed {tip}: mine" in capsys.readouterr().out


def test_foreign_commit_to_requested_path_in_window_stops_the_run(repo, monkeypatch, capsys):
    """A parallel session commits a change to a REQUESTED path after the tool read
    HEAD. The tool makes no commit and says which path, rather than overwrite that
    change; the branch stays on the parallel session's commit and the requested
    change stays staged."""
    write(repo, "mine.md", "v1\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    write(repo, "mine.md", "mine v2\n")

    def foreign_commit_to_mine():
        # Built from objects alone, so the shared index and the file on disk keep
        # what this session has in them.
        blob = git(["hash-object", "-w", "--stdin"], repo, stdin="theirs v2\n").strip()
        tree = git(["mktree"], repo, stdin=f"100644 blob {blob}\tmine.md\n").strip()
        commit = git(["commit-tree", tree, "-p", "HEAD", "-m", "foreign"], repo).strip()
        git(["update-ref", "HEAD", commit], repo)

    assert run_racing(repo, monkeypatch, "read-tree", foreign_commit_to_mine) != 0
    out = capsys.readouterr()

    assert "another session committed these requested paths during this run" in out.err, out.err
    assert "): mine.md. No commit made" in out.err, out.err
    assert "committed" not in out.out
    assert subjects(repo) == ["foreign", "seed"], subjects(repo)
    assert git(["show", "HEAD:mine.md"], repo) == "theirs v2\n"
    assert git(["show", ":mine.md"], repo) == "mine v2\n"


def test_branch_moved_off_own_commit_before_successful_pull(repo, tmp_path, monkeypatch, capsys):
    """A parallel session moves the branch back off the tool's commit, then the
    pull SUCCEEDS (a fast-forward). The tool does not print `committed`: it
    fails, naming the commit so it can be recovered."""
    remote_ahead(repo, tmp_path)
    seed = git(["rev-parse", "HEAD"], repo).strip()
    write(repo, "mine.md")

    assert run_racing(repo, monkeypatch, "pull", lambda: git(["update-ref", "HEAD", seed], repo)) != 0
    out = capsys.readouterr()

    assert "committed" not in out.out and "synced remote" not in out.out, out.out
    assert subjects(repo) == ["remote", "seed"], subjects(repo)  # the pull succeeded
    assert "which does not contain it. Recover it" in out.err, out.err
    lost = out.err.split("git cherry-pick ")[1].split("`")[0]
    assert git(["log", "-1", "--format=%s", lost], repo).strip() == "mine"


def hook(repo, name, body):
    path = repo / ".git" / "hooks" / name
    path.parent.mkdir(exist_ok=True)
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    path.chmod(0o755)
    return path


def test_commit_hooks_run(repo):
    """The repository's pre-commit and commit-msg hooks run, as under `git
    commit`: a failing pre-commit hook stops the run with no commit, and what the
    commit-msg hook writes into the message is committed."""
    write(repo, "seed.md")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    write(repo, "file.md")

    pre_commit = hook(repo, "pre-commit", "echo refused by hook >&2; exit 1")
    res = run_commit(repo, ["file.md"], "add file")
    assert res.returncode != 0
    assert "refused by hook" in res.stderr, res.stderr
    assert subjects(repo) == ["seed"]

    os.remove(pre_commit)
    hook(repo, "commit-msg", 'echo "added by hook" >> "$1"')
    res = run_commit(repo, ["file.md"], "add file")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert commit_message(repo).split() == ["add", "file", "added", "by", "hook"]


def test_failing_post_commit_hook_is_a_warning(repo):
    """A post-commit hook that fails changes nothing, as under `git commit`: the
    commit stands, the result is reported, and the failure is shown as a warning."""
    write(repo, "seed.md")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    write(repo, "file.md")

    hook(repo, "post-commit", "echo post failed >&2; exit 3")
    res = run_commit(repo, ["file.md"], "add file")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert f"committed {tip}: add file" in res.stdout, res.stdout
    assert "files in commit (1): file.md" in res.stdout, res.stdout
    assert "WARNING: the post-commit hook failed (exit 3). The commit was made and stands." in res.stderr, res.stderr
    assert "post failed" in res.stderr, res.stderr
    assert subjects(repo) == ["add file", "seed"]


def test_commit_msg_hook_emptying_the_message_refuses_the_commit(repo):
    """A commit-msg hook that leaves the message empty refuses the commit, as
    under `git commit`: no commit, and the requested change stays staged."""
    write(repo, "seed.md")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    write(repo, "file.md")

    hook(repo, "commit-msg", ': > "$1"')
    res = run_commit(repo, ["file.md"], "add file")
    assert res.returncode != 0
    assert "the commit-msg hook left the commit message empty. No commit made" in res.stderr, res.stderr
    assert "committed" not in res.stdout
    assert subjects(repo) == ["seed"]
    assert git(["diff", "--cached", "--name-only"], repo).strip() == "file.md"


def test_own_commit_reported_under_pull_rebase(repo, tmp_path):
    """The repository sets pull.rebase=true and the remote is ahead. The commit
    the tool reports is the commit the branch holds: the pull is a merge, so the
    commit is not replaced by a rebased copy."""
    remote_ahead(repo, tmp_path)
    git(["config", "pull.rebase", "true"], repo)
    write(repo, "mine.md")

    res = run_commit(repo, ["mine.md"], "mine")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    reported = res.stdout.split("committed ")[1].split(":")[0]
    assert git(["log", "-1", "--format=%s", reported], repo).strip() == "mine"
    git(["merge-base", "--is-ancestor", reported, "HEAD"], repo)  # asserts exit 0
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert f"synced remote: merge commit {tip} created on top of {reported}" in res.stdout, res.stdout
    assert git(["rev-list", "--parents", "-1", "HEAD"], repo).split()[1] == git(["rev-parse", reported], repo).strip()
    assert sorted(subjects(repo)[1:]) == ["mine", "remote", "seed"], subjects(repo)


def conflicting_branches(repo):
    """On top of the current commit: the branch gains `one` then `two` in c.md,
    and a branch `side` gains s.md and its own c.md. Merging, cherry-picking or
    rebasing onto `side` conflicts in c.md, and so does reverting `one`."""
    branch = git(["rev-parse", "--abbrev-ref", "HEAD"], repo).strip()
    git(["checkout", "-q", "-b", "side"], repo)
    write(repo, "s.md", "side\n")
    write(repo, "c.md", "side\n")
    git(["add", "s.md", "c.md"], repo)
    git(["commit", "-q", "-m", "side"], repo)
    git(["checkout", "-q", branch], repo)
    for content in ("one", "two"):
        write(repo, "c.md", content + "\n")
        git(["add", "c.md"], repo)
        git(["commit", "-q", "-m", content], repo)


def stop(repo, *command):
    """Run a git operation that stops unfinished."""
    res = subprocess.run(["git", *command], cwd=repo, text=True, capture_output=True)
    return res.returncode


def operation_state(repo):
    """Everything an unfinished operation consists of: git's markers for it, the
    staged entries, the unmerged entries, and the files it wrote on disk."""
    git_dir = repo / ".git"
    markers = {name: (git_dir / name).read_text() if (git_dir / name).is_file() else (git_dir / name).is_dir()
               for name in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")}
    on_disk = {name: (repo / name).read_text() if (repo / name).exists() else None for name in ("c.md", "s.md")}
    return markers, staged_entries(repo), git(["ls-files", "-u"], repo), on_disk


@pytest.mark.parametrize("conflict", [True, False], ids=["conflict resolved on disk", "clean merge"])
def test_merge_in_progress_with_remote_ahead_is_left_as_found(repo, tmp_path, conflict):
    """Another session has a merge open — stopped on a conflict it resolved by
    hand on disk, or clean and not yet committed — and the remote is ahead. The
    tool commits its own path, does not pull, says so, and leaves the merge
    exactly as it was: MERGE_HEAD, the staged entries, the resolved file."""
    remote_ahead(repo, tmp_path)
    conflicting_branches(repo)
    if conflict:
        assert stop(repo, "merge", "--no-commit", "--no-ff", "side") != 0
        write(repo, "c.md", "RESOLVED-BY-HAND\n")
    else:
        git(["merge", "-q", "--no-commit", "--no-ff", "side", "-X", "ours"], repo)
    state = operation_state(repo)
    assert state[0]["MERGE_HEAD"] and "s.md" in state[1], state
    assert bool(state[2]) == conflict, state
    write(repo, "base.md", "v2\n")

    res = run_commit(repo, ["base.md"], "mine")

    assert operation_state(repo) == state, res.stderr
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert subjects(repo)[0] == "mine" and "remote" not in subjects(repo), subjects(repo)
    assert commit_files(repo) == {"base.md"}
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert f"committed {tip}: mine" in res.stdout, res.stdout
    assert "merge conflict" not in res.stderr, res.stderr
    assert (f"WARNING: a merge is in progress in this working tree. This run did not start it and left it "
            f"exactly as it was. Commit {tip} was made. The remote is ahead and was NOT pulled") in res.stderr, res.stderr


def test_merge_in_progress_with_remote_ahead_refuses_the_push(repo, tmp_path):
    """Same state, with --push: the commit is made, nothing is pushed, and the
    run fails saying both; the merge is exactly as it was."""
    remote_ahead(repo, tmp_path)
    conflicting_branches(repo)
    assert stop(repo, "merge", "--no-commit", "--no-ff", "side") != 0
    state = operation_state(repo)
    remote_tip = git(["rev-parse", "HEAD"], tmp_path / "origin.git")
    write(repo, "base.md", "v2\n")

    res = subprocess.run([sys.executable, COMMIT_PY, "-m", "mine", "-f", "base.md", "--push"],
                         cwd=repo, text=True, capture_output=True)
    assert res.returncode != 0
    assert operation_state(repo) == state
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert subjects(repo)[0] == "mine"
    assert f"Commit {tip} was made." in res.stderr and "Nothing was pushed" in res.stderr, res.stderr
    assert "pushed." not in res.stdout
    assert git(["rev-parse", "HEAD"], tmp_path / "origin.git") == remote_tip


@pytest.mark.parametrize("operation, command", [
    ("merge", ["merge", "side"]),
    ("cherry-pick", ["cherry-pick", "side"]),
    ("revert", ["revert", "--no-edit", "HEAD~1"]),
    ("rebase", ["rebase", "side"]),
])
def test_operation_in_progress_is_named_and_left_as_found(repo, operation, command):
    """A merge, cherry-pick, revert or rebase stopped on a conflict, no remote.
    The tool commits another path, names the operation, and leaves it exactly as
    it was. A requested path the operation left in conflict is refused instead:
    no commit, and nothing staged."""
    write(repo, "base.md", "v1\n")
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "seed"], repo)
    conflicting_branches(repo)
    assert stop(repo, *command) != 0
    state = operation_state(repo)
    assert state[2] and any(state[0].values()), state
    head = git(["rev-parse", "HEAD"], repo)

    res = run_commit(repo, ["c.md"], "theirs to finish")
    assert res.returncode != 0
    assert (f"a {operation} is in progress in this working tree and left these requested paths in "
            "conflict: c.md. No commit made and nothing was staged") in res.stderr, res.stderr
    assert operation_state(repo) == state and git(["rev-parse", "HEAD"], repo) == head

    write(repo, "base.md", "v2\n")
    res = run_commit(repo, ["base.md"], "mine")
    assert res.returncode == 0, f"{res.stderr}\n{res.stdout}"
    assert operation_state(repo) == state
    tip = git(["rev-parse", "--short", "HEAD"], repo).strip()
    assert subjects(repo)[0] == "mine" and f"committed {tip}: mine" in res.stdout
    assert (f"WARNING: a {operation} is in progress in this working tree. This run did not start it and "
            f"left it exactly as it was. Commit {tip} was made.") in res.stderr, res.stderr
    assert "NOT pulled" not in res.stderr
