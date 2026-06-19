"""Exercises for the 2026-06-18 concurrency + matcher fixes (4 tasks).

Pins:
  A) consult fails CLEANLY (no traceback, no partial JSON) when ``old`` is
     deleted mid-scan by a concurrent move, instead of crashing on a
     NotADirectoryError in the git-toplevel probe.
  B) wikilink basename-collision: a path-qualified ``[[dir/name|alias]]`` to the
     moved file is detected; a basename-collision warning is emitted; a bare
     ``[[name]]`` stays surface (never auto).
  C) inline-code paths written vault-root-relative are surfaced even when the
     scan is scoped to a subtree that does NOT contain ``old``.
  D) a moved folder's OWN ``build/`` files are scanned by the STRUCTURED matchers,
     not only the literal-path sweep; the broad-scope skip is unchanged elsewhere.
"""

from __future__ import annotations

import shutil

import safe_move.scope as scope_mod
from safe_move import classify
from safe_move.cli import main
from safe_move.consult import build_consult_result
from safe_move.move import nested_repos
from safe_move.scope import git_toplevel


# ---------------------------------------------------------------------------
# Task A — concurrent mid-scan deletion of ``old``
# ---------------------------------------------------------------------------


def test_git_toplevel_returns_none_for_missing_cwd(tmp_path):
    # The observed crash: subprocess(cwd=<deleted dir>) raised NotADirectoryError
    # (WinError 267). A vanished cwd must read as "no repository", not crash.
    assert git_toplevel(tmp_path / "vanished") is None


def test_nested_repos_handles_vanished_dir(tmp_path):
    # nested_repos probes git_toplevel(path) too; a vanished folder must not crash.
    assert nested_repos(tmp_path / "vanished") == []


def test_consult_fails_cleanly_when_old_deleted_mid_scan(repo_builder, monkeypatch, capsys):
    files = {
        "proj/old/index.md": "# Project\n",
        "proj/old/a.md": "a\n",
        "proj/old/b.md": "b\n",
        "ref.md": "See [[index]].\n",
    }
    fix = repo_builder("concurrent-delete", files, tracked=list(files))
    old_abs = fix.repo / "proj" / "old"
    new_abs = fix.repo / "proj" / "renamed"

    real_walk = scope_mod.walk_scope

    def deleting_walk(*args, **kwargs):
        # Simulate a parallel session deleting ``old`` mid-scan: AFTER consult's
        # initial existence check, BEFORE it finalizes. The real walk still runs.
        if old_abs.exists():
            shutil.rmtree(old_abs)
        return real_walk(*args, **kwargs)

    monkeypatch.setattr(scope_mod, "walk_scope", deleting_walk)

    code = main(["consult", str(old_abs), str(new_abs), "--scope-root", str(fix.repo)])
    captured = capsys.readouterr()

    assert code == 1
    assert "Traceback" not in captured.err
    assert "no longer exists" in captured.err.lower()
    # No partial / garbage JSON written to stdout.
    assert captured.out.strip() == ""


# ---------------------------------------------------------------------------
# Task D — moved folder's build/ files scanned by the STRUCTURED matchers
# ---------------------------------------------------------------------------


def test_folder_move_scans_moved_build_dir_with_structured_matchers(repo_builder):
    files = {
        "sub/proj/proj.md": "# index\n",
        # A wikilink by basename inside the moved tree's build/ dir: the literal
        # sweep cannot see it (no literal "sub/proj" string), so without the fix
        # it is MISSED entirely.
        "sub/proj/build/log.md": "ref: [[proj]]\n",
        # A config path to the old folder inside the moved tree's build/ dir:
        # without the fix it is caught only as a crude literal-path.
        "sub/proj/build/config.yaml": "parent: sub/proj\n",
        "sub/proj/decisions.md": "d\n",
        # OUTSIDE the moved tree: a build/ file elsewhere must stay skipped.
        "other/build/note.md": "[[proj]] and sub/proj here\n",
    }
    fix = repo_builder("folder-build-structured", files, tracked=list(files))

    consulted = build_consult_result("sub/proj", "sub/proj2", scope_root=fix.repo)
    by_file_syntax = {(r["file"], r["syntax"]) for r in consulted["references"]}

    # The wikilink inside the moved build/ file is now DETECTED (was missed).
    assert ("sub/proj/build/log.md", "wikilink") in by_file_syntax
    # The config path inside the moved build/ file is now a STRUCTURED config-path
    # match, not merely a crude literal-path surface.
    assert ("sub/proj/build/config.yaml", "config-path") in by_file_syntax

    # The broad-scope build/ skip is UNCHANGED for files OUTSIDE the moved tree:
    # other/build/note.md is never scanned, so it contributes no references.
    assert not any(
        r["file"] == "other/build/note.md" for r in consulted["references"]
    )


# ---------------------------------------------------------------------------
# Task C — vault-root-relative inline-code paths with a SUBTREE scope
# ---------------------------------------------------------------------------


def test_inline_code_path_outside_scope_root_is_surfaced(repo_builder):
    files = {
        "4-archives/sub/plan.md": "x\n",
        "1-projects/proj/proj.md": "# proj\n",
        # TRUE ref: a vault-root-relative inline-code path to `old`, in a file
        # that IS inside the (subtree) scan scope. Previously dropped because
        # `old` sits OUTSIDE --scope-root, so `old_rel` was absolute and no
        # scope-relative resolution ever equalled it -> references: 0.
        "1-projects/proj/tasks.md": "see `4-archives/sub/plan.md` here\n",
        # DECOY: an inline-code path to a DIFFERENT, real in-scope file. It must
        # NOT be reported as a reference to `old` (zero false positives).
        "1-projects/proj/sibling.md": "x\n",
        "1-projects/proj/notes.md": "also `proj/sibling.md` (a different file)\n",
    }
    fix = repo_builder("rootrel-inline-code", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "4-archives" / "sub" / "plan.md"),
        str(fix.repo / "1-projects" / "proj" / "plan.md"),
        scope_root=str(fix.repo / "1-projects"),
    )

    # Exactly the vault-root-relative reference to `old` is surfaced — nothing
    # else (the decoy, which resolves to a different real file, is not matched).
    # Files are reported relative to the scan root (1-projects), so `proj/...`.
    assert [
        (r["file"], r["syntax"], r["class"]) for r in consulted["references"]
    ] == [("proj/tasks.md", "inline-code-path", classify.CLASS_SURFACE)]

    # The surfaced cross-root ref now carries a NON-EMPTY, correct proposed: the
    # new path expressed in the SAME vault-root-relative inline-code form the
    # reference was written in (the replace.py half of the 700a0c2 fix). Still a
    # surface-class hint the caller may --apply — inline-code is never auto.
    (ref,) = consulted["references"]
    assert ref["proposed"] == "1-projects/proj/plan.md"


def test_inline_code_path_outside_scope_root_ambiguous_proposed_is_empty(repo_builder):
    """A cross-root inline-code ref whose file-relative reading hits a DIFFERENT
    real file is surfaced but left with an EMPTY proposed (the ambiguity guard).

    The same backtick path resolves two ways: workspace-root-relative it names the
    moved (out-of-scope) `old`; file-relative it names a different, real in-scope
    file. With two valid readings landing on different real files, safe-move must
    NOT guess a rewrite — it surfaces the ref with proposed='' (zero false
    positives).
    """
    files = {
        # `old`: out-of-scope, at workspace-relative path data/x.md.
        "data/x.md": "OLD target\n",
        "projects/proj/proj.md": "# proj\n",
        # A DIFFERENT real file reachable file-relative from the referring file:
        # referring file projects/sub/notes.md -> file_dir projects/sub, so the
        # backtick `data/x.md` read file-relative is projects/sub/data/x.md.
        "projects/sub/data/x.md": "DIFFERENT real file\n",
        "projects/sub/notes.md": "ambiguous ref: `data/x.md` here\n",
    }
    fix = repo_builder("rootrel-inline-ambiguous", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "data" / "x.md"),
        str(fix.repo / "projects" / "proj" / "x.md"),
        scope_root=str(fix.repo / "projects"),
    )

    # The ref is still SURFACED (the matcher resolves it against the workspace
    # root and matches `old`)…
    assert [
        (r["file"], r["syntax"], r["class"]) for r in consulted["references"]
    ] == [("sub/notes.md", "inline-code-path", classify.CLASS_SURFACE)]
    # …but with NO proposed rewrite, because the file-relative reading points at a
    # different real file — the ambiguity guard leaves it empty rather than guess.
    (ref,) = consulted["references"]
    assert ref["proposed"] == ""


# ---------------------------------------------------------------------------
# Task B — wikilink basename collision (over-match bare, miss path-qualified)
# ---------------------------------------------------------------------------


def test_wikilink_basename_collision_detects_pathqualified_and_warns(repo_builder):
    files = {
        "A/x.md": "# x in A\n",
        "B/x.md": "# x in B\n",
        # The path-qualified link is the TRUE reference to A/x.md; the bare link
        # is ambiguous (A/x.md OR B/x.md).
        "D/ref.md": "path-qualified: [[A/x|alias]]\nbare: [[x]]\n",
    }
    fix = repo_builder("wikilink-collision", files, tracked=list(files))

    consulted = build_consult_result("A/x.md", "A/x-renamed.md", scope_root=fix.repo)
    refs = consulted["references"]

    # (i) the path-qualified wikilink to the moved file is now LISTED (was missed),
    # surfaced (not a confident auto), with a correct path-aware proposed rewrite.
    pq = [r for r in refs if r["match"] == "[[A/x|alias]]"]
    assert len(pq) == 1
    assert pq[0]["file"] == "D/ref.md"
    assert pq[0]["syntax"] == "wikilink"
    assert pq[0]["class"] == classify.CLASS_SURFACE
    assert pq[0]["proposed"] == "[[A/x-renamed|alias]]"

    # (ii) a basename-collision warning names the colliding file, and the bare
    # [[x]] is surfaced (never auto) rather than presented as a confident ref.
    collisions = [w for w in consulted["warnings"] if w["kind"] == "basename-collision"]
    assert len(collisions) == 1
    assert "B/x.md" in collisions[0]["message"]

    bare = [r for r in refs if r["match"] == "[[x]]"]
    assert len(bare) == 1
    assert bare[0]["class"] == classify.CLASS_SURFACE
