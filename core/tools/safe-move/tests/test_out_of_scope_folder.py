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
from safe_move.act import run_act
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
            "--json",
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


def test_out_of_scope_folder_act_proceeds_like_consult(repo_builder):
    """``act`` must AGREE with ``consult`` for an out-of-scope ``old``.

    Regression for the consult/act inconsistency: ``consult`` accepted an
    out-of-scope ``old`` (scanned the subtree, surfaced in-scope refs) but
    ``act`` with the SAME args hard-errored exit 1 with ``'<old>' is not in the
    subpath of '<scope-root>'`` from a ``relative_to`` on ``old``. Both must now
    proceed: ``act`` performs the move and surfaces the same in-scope refs.
    """
    fix = repo_builder("oos-folder-act", _OOS_FILES, tracked=list(_OOS_FILES))

    consulted = build_consult_result(
        str(fix.repo / "4-archives" / "oldfolder"),
        str(fix.repo / "1-projects" / "proj" / "newfolder"),
        scope_root=str(fix.repo / "1-projects"),
    )
    consult_surfaced = {
        (r["file"], r["proposed"]) for r in consulted["references"]
    }

    # Same args that consult accepted — must NOT raise / must NOT exit 1.
    result = run_act(
        str(fix.repo / "4-archives" / "oldfolder"),
        str(fix.repo / "1-projects" / "proj" / "newfolder"),
        scope_root=str(fix.repo / "1-projects"),
        apply="",
    )

    assert result.exit_code == 0
    # The move actually happened.
    assert not (fix.repo / "4-archives" / "oldfolder").exists()
    assert (fix.repo / "1-projects" / "proj" / "newfolder" / "a.md").exists()
    # act surfaces the same in-scope refs consult did (both proceed identically).
    act_surfaced = {(row["file"], row["new"]) for row in result.surfaced}
    assert consult_surfaced <= act_surfaced or act_surfaced <= consult_surfaced
    assert ("proj/tasks.md", "1-projects/proj/newfolder") in act_surfaced
    # The same limitation warning consult emits is carried by act.
    assert any(
        w["kind"] == "moved-folder-out-of-scope" for w in result.warnings
    )


def test_out_of_scope_single_file_act_proceeds_like_consult(repo_builder):
    """Single-file analogue of the real repro (wiki-issues.md at vault root).

    ``old`` sits at the repo root, ``--scope-root`` points at a subtree that does
    NOT contain it. ``consult`` succeeds; ``act`` must succeed too rather than
    erroring ``'<old>' is not in the subpath of '<scope-root>'``.
    """
    files = {
        "wiki-issues.md": "# wiki issues\n",
        "2-areas/sb-os/sb-os.md": "# sb-os\n",
        "2-areas/sb-os/ref.md": "tracked at `wiki-issues.md` here\n",
    }
    fix = repo_builder("oos-single-file-act", files, tracked=list(files))

    # consult accepts the out-of-scope old (no raise).
    build_consult_result(
        str(fix.repo / "wiki-issues.md"),
        str(fix.repo / "2-areas" / "sb-os" / "wiki-issues.md"),
        scope_root=str(fix.repo / "2-areas" / "sb-os"),
    )

    # act with the SAME args must proceed and perform the move.
    result = run_act(
        str(fix.repo / "wiki-issues.md"),
        str(fix.repo / "2-areas" / "sb-os" / "wiki-issues.md"),
        scope_root=str(fix.repo / "2-areas" / "sb-os"),
        apply="",
    )

    assert result.exit_code == 0
    assert not (fix.repo / "wiki-issues.md").exists()
    assert (fix.repo / "2-areas" / "sb-os" / "wiki-issues.md").read_text(
        encoding="utf-8"
    ) == "# wiki issues\n"


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
