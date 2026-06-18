"""Folder reference handling: consult + act for folder targets."""

from __future__ import annotations

from safe_move import classify
from safe_move.act import format_action_log, run_act
from safe_move.consult import build_consult_result


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _auto_refs(result: dict) -> list[dict]:
    return [ref for ref in result["references"] if ref["class"] == classify.CLASS_AUTO]


def test_folder_path_reference_fixed_on_pure_move(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [the folder](docs/old).\n",
    }
    fix = repo_builder("folder-path-ref", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/new",
        scope_root=fix.repo,
    )

    assert consulted["folder_cascade"]["moved_files"] == ["docs/old/file.md"]
    assert len(consulted["references"]) == 1
    ref = consulted["references"][0]
    assert ref["file"] == "links.md"
    assert ref["syntax"] == "markdown-link"
    assert ref["proposed"] == "[the folder](docs/new)"
    assert ref["class"] == classify.CLASS_AUTO
    assert consulted["folder_cascade"]["folder_path_refs"] == [ref["id"]]
    assert consulted["folder_cascade"]["contained_file_refs"] == []

    result = run_act(
        "docs/old",
        "docs/new",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert (fix.repo / "docs" / "new" / "file.md").read_text(encoding="utf-8") == "body\n"
    assert not (fix.repo / "docs" / "old").exists()
    assert (fix.repo / "links.md").read_text(encoding="utf-8") == "See [the folder](docs/new).\n"
    log = format_action_log(result)
    assert "docs/old -> docs/new" in log
    assert "method: git mv" in log


def test_contained_file_reference_fixed_on_folder_rename(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [the file](docs/old/file.md).\n",
    }
    fix = repo_builder("contained-file-ref", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
    )

    assert consulted["folder_cascade"]["moved_files"] == ["docs/old/file.md"]
    assert len(consulted["references"]) == 1
    ref = consulted["references"][0]
    assert ref["file"] == "links.md"
    assert ref["syntax"] == "markdown-link"
    assert ref["proposed"] == "[the file](docs/renamed/file.md)"
    assert ref["class"] == classify.CLASS_AUTO
    assert consulted["folder_cascade"]["contained_file_refs"] == [ref["id"]]
    assert consulted["folder_cascade"]["folder_path_refs"] == []

    result = run_act(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert (
        fix.repo / "docs" / "renamed" / "file.md"
    ).read_text(encoding="utf-8") == "body\n"
    assert not (fix.repo / "docs" / "old").exists()
    assert (
        fix.repo / "links.md"
    ).read_text(encoding="utf-8") == "See [the file](docs/renamed/file.md).\n"


def test_pure_move_leaves_basename_wikilinks_alone(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [[file]].\n",
    }
    fix = repo_builder("folder-move-basename-wikilink", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/new",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    assert len(refs) == 1
    assert refs[0]["syntax"] == "wikilink"
    assert refs[0]["match"] == "[[file]]"
    assert refs[0]["proposed"] == "[[file]]"
    assert refs[0]["class"] == classify.CLASS_AUTO
    assert consulted["folder_cascade"]["contained_file_refs"] == [refs[0]["id"]]

    result = run_act(
        "docs/old",
        "docs/new",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert (fix.repo / "links.md").read_text(encoding="utf-8") == "See [[file]].\n"
    assert (fix.repo / "docs" / "new" / "file.md").exists()


def test_rename_edits_basename_reference_to_folder(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [[old]].\n",
    }
    fix = repo_builder("folder-rename-basename", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    assert len(refs) == 1
    assert refs[0]["syntax"] == "wikilink"
    assert refs[0]["match"] == "[[old]]"
    assert refs[0]["proposed"] == "[[renamed]]"
    assert refs[0]["class"] == classify.CLASS_AUTO
    assert consulted["folder_cascade"]["folder_path_refs"] == [refs[0]["id"]]

    result = run_act(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert (fix.repo / "links.md").read_text(encoding="utf-8") == "See [[renamed]].\n"


def test_folder_move_does_not_rename_index_file_but_warns(repo_builder):
    files = {
        "notes/notes.md": "# Notes\n",
        "notes/other.md": "other\n",
        "links.md": "See [folder](notes).\n",
    }
    fix = repo_builder("folder-index-cascade", files, tracked=list(files))

    consulted = build_consult_result(
        "notes",
        "journal",
        scope_root=fix.repo,
    )

    assert any(
        w["kind"] == "index-cascade" for w in consulted["warnings"]
    ), "consult should warn about the index cascade"

    result = run_act(
        "notes",
        "journal",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert not (fix.repo / "notes").exists()
    # The index file is moved but NOT renamed.
    assert (fix.repo / "journal" / "notes.md").exists()
    assert not (fix.repo / "journal" / "journal.md").exists()
    log = format_action_log(result)
    assert "index-cascade" in log


def test_drift_on_contained_file_reference_is_refused(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [the file](docs/old/file.md).\n",
    }
    fix = repo_builder("folder-drift", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
    )
    chosen = _auto_refs(consulted)
    (fix.repo / "links.md").write_text(
        "See [the changed file](docs/old/file.md).\n", encoding="utf-8"
    )

    result = run_act(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 1
    assert len(result.drifted) == 1
    assert result.drifted[0]["id"] == chosen[0]["id"]
    assert result.drifted[0]["reason"] == "drifted"
    assert (
        fix.repo / "links.md"
    ).read_text(encoding="utf-8") == "See [the changed file](docs/old/file.md).\n"


def test_reference_inside_moved_file_is_edited_at_new_path(repo_builder):
    files = {
        "docs/old/a.md": "---\nrelated: docs/old/b.md\n---\n",
        "docs/old/b.md": "body\n",
        "external.md": "external\n",
    }
    fix = repo_builder("ref-inside-moved-file", files, tracked=list(files))

    consulted = build_consult_result(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
    )

    refs = consulted["references"]
    assert len(refs) == 1
    ref = refs[0]
    assert ref["file"] == "docs/old/a.md"
    assert ref["syntax"] == "frontmatter-field"
    assert ref["proposed"] == "docs/renamed/b.md"
    assert ref["class"] == classify.CLASS_AUTO

    result = run_act(
        "docs/old",
        "docs/renamed",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    # The edit must land on the file at its NEW path, not be lost at the old path.
    assert not (fix.repo / "docs" / "old" / "a.md").exists()
    updated = (fix.repo / "docs" / "renamed" / "a.md").read_text(encoding="utf-8")
    assert "docs/renamed/b.md" in updated
    assert "docs/old/b.md" not in updated
