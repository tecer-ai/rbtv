"""Out-of-scope FOLDER move: consult must not crash and must surface cross-root refs.

The folder analogue of the single-file out-of-scope fix (see
``test_concurrency_and_matcher_fixes.py`` Task C). A FOLDER ``consult`` whose
moved folder sits OUTSIDE the scan ``--scope-root`` previously crashed with an
uncaught ``ValueError`` from ``relative_to(scope_root)`` — at the moved-tree
self-reference sweep AND at the ``moved_files`` cascade. It now completes:
in-scope references TO the moved folder (and to files inside it) are surfaced
cross-root with a correct workspace-root-relative ``proposed``; the moved tree's
OWN files are not scanned for self-references (consistent with a single-file
out-of-scope move) and that limitation is reported via a
``moved-folder-out-of-scope`` warning rather than silently dropped.
"""

from __future__ import annotations

import json

from safe_move import classify
from safe_move.cli import main
from safe_move.consult import build_consult_result


_OOS_FILES = {
    "4-archives/oldfolder/oldfolder.md": "# index\n",
    "4-archives/oldfolder/a.md": "a\n",
    "1-projects/proj/proj.md": "# proj\n",
    # In-scope ref to the moved FOLDER, written workspace-root-relative.
    "1-projects/proj/tasks.md": "see `4-archives/oldfolder` here\n",
    # In-scope ref to a FILE inside the moved folder, workspace-root-relative.
    "1-projects/proj/notes.md": "and `4-archives/oldfolder/a.md` too\n",
}


def test_out_of_scope_folder_consult_surfaces_cross_root_refs(repo_builder):
    fix = repo_builder("oos-folder", _OOS_FILES, tracked=list(_OOS_FILES))

    # Must not raise (previously: ValueError / raw traceback aborted the run).
    consulted = build_consult_result(
        str(fix.repo / "4-archives" / "oldfolder"),
        str(fix.repo / "1-projects" / "proj" / "newfolder"),
        scope_root=str(fix.repo / "1-projects"),
    )

    surfaced = {
        (r["file"], r["syntax"], r["class"], r["proposed"])
        for r in consulted["references"]
    }
    # The reference to the moved FOLDER -> new folder path (workspace-root-relative).
    assert (
        "proj/tasks.md",
        "inline-code-path",
        classify.CLASS_SURFACE,
        "1-projects/proj/newfolder",
    ) in surfaced
    # The reference to a FILE inside the moved folder -> new contained-file path.
    assert (
        "proj/notes.md",
        "inline-code-path",
        classify.CLASS_SURFACE,
        "1-projects/proj/newfolder/a.md",
    ) in surfaced

    # The unscanned-self-refs limitation is reported (never a silent miss).
    oos = [
        w for w in consulted["warnings"] if w["kind"] == "moved-folder-out-of-scope"
    ]
    assert len(oos) == 1


def test_out_of_scope_folder_consult_cli_no_traceback(repo_builder, capsys):
    fix = repo_builder("oos-folder-cli", _OOS_FILES, tracked=list(_OOS_FILES))

    code = main(
        [
            "consult",
            str(fix.repo / "4-archives" / "oldfolder"),
            str(fix.repo / "1-projects" / "proj" / "newfolder"),
            "--scope-root",
            str(fix.repo / "1-projects"),
        ]
    )
    captured = capsys.readouterr()

    # Clean completion: exit 0, valid JSON on stdout, NO raw traceback on stderr.
    assert code == 0
    assert "Traceback" not in captured.err
    payload = json.loads(captured.out)
    assert any(r["syntax"] == "inline-code-path" for r in payload["references"])
    assert any(
        w["kind"] == "moved-folder-out-of-scope" for w in payload["warnings"]
    )


def test_in_scope_folder_move_has_no_out_of_scope_warning(repo_builder):
    """The new out-of-scope branch must NOT misfire for an in-scope folder move."""
    files = {
        "1-projects/proj/sub/sub.md": "# index\n",
        "1-projects/proj/sub/a.md": "a\n",
        "1-projects/other/ref.md": "see `1-projects/proj/sub/a.md`\n",
    }
    fix = repo_builder("inscope-folder", files, tracked=list(files))

    consulted = build_consult_result(
        str(fix.repo / "1-projects" / "proj" / "sub"),
        str(fix.repo / "1-projects" / "proj" / "sub-renamed"),
        scope_root=str(fix.repo / "1-projects"),
    )

    assert not any(
        w["kind"] == "moved-folder-out-of-scope" for w in consulted["warnings"]
    )
    moved_files = consulted["folder_cascade"]["moved_files"]
    assert moved_files
    # In-scope moved files stay scope-relative (no absolute fallback).
    assert all(mf.startswith("proj/sub") for mf in moved_files)
