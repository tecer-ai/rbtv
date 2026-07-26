"""Two folder-move reference-rewrite fixes.

1. A reference to a SUBDIRECTORY of a moved folder is matched by the STRUCTURED
   matchers (markdown-link, wikilink, inline-code path), not only by the crude
   literal sweep — including a ``../``-relative one, which the literal sweep
   cannot see at all.
2. A trailing ``/`` in the matched path (the author's folder notation) survives
   into the proposed rewrite, for every syntax that rewrites a path value.
"""

from __future__ import annotations

from safe_move import classify
from safe_move.consult import build_consult_result


def _by_syntax(result: dict, syntax: str) -> list[dict]:
    return [ref for ref in result["references"] if ref["syntax"] == syntax]


def _ref_at(result: dict, file: str, syntax: str) -> dict:
    matches = [
        ref
        for ref in result["references"]
        if ref["file"] == file and ref["syntax"] == syntax
    ]
    assert len(matches) == 1, f"expected one {syntax} in {file}, got {matches}"
    return matches[0]


# ---------------------------------------------------------------------------
# 1. Subdirectory references via the structured matchers
# ---------------------------------------------------------------------------


def test_markdown_link_to_subdirectory_of_moved_folder_is_matched(repo_builder):
    files = {
        "refs/weaver-ui/note.md": "body\n",
        "links.md": "See [the subdir](refs/weaver-ui).\n",
    }
    fix = repo_builder("subdir-markdown-link", files, tracked=list(files))

    consulted = build_consult_result("refs", "build/refs", scope_root=fix.repo)

    ref = _ref_at(consulted, "links.md", "markdown-link")
    assert ref["match"] == "[the subdir](refs/weaver-ui)"
    assert ref["proposed"] == "[the subdir](build/refs/weaver-ui)"
    # A structured match, not the crude literal fallback.
    assert not _by_syntax(consulted, "literal-path")
    assert ref["id"] in consulted["folder_cascade"]["contained_file_refs"]
    # moved_files stays files-only — the subdirectory is not listed there.
    assert consulted["folder_cascade"]["moved_files"] == ["refs/weaver-ui/note.md"]


def test_inline_code_path_to_subdirectory_is_matched(repo_builder):
    files = {
        "refs/weaver-ui/note.md": "body\n",
        "docs/guide.md": "Look in `refs/weaver-ui` for the UI notes.\n",
    }
    fix = repo_builder("subdir-inline-code", files, tracked=list(files))

    consulted = build_consult_result("refs", "build/refs", scope_root=fix.repo)

    ref = _ref_at(consulted, "docs/guide.md", "inline-code-path")
    assert ref["match"] == "refs/weaver-ui"
    assert ref["proposed"] == "build/refs/weaver-ui"
    # inline-code paths are never auto-applied.
    assert ref["class"] == classify.CLASS_SURFACE


def test_relative_reference_to_subdirectory_is_matched(repo_builder):
    """A ``../``-relative subdirectory reference — invisible to the literal sweep."""
    files = {
        "refs/weaver-ui/note.md": "body\n",
        "docs/guide.md": "See [the subdir](../refs/weaver-ui).\n",
    }
    fix = repo_builder("subdir-relative", files, tracked=list(files))

    consulted = build_consult_result("refs", "build/refs", scope_root=fix.repo)

    ref = _ref_at(consulted, "docs/guide.md", "markdown-link")
    assert ref["match"] == "[the subdir](../refs/weaver-ui)"
    assert ref["proposed"] == "[the subdir](../build/refs/weaver-ui)"


def test_bare_wikilink_to_subdirectory_name_surfaces_never_auto(repo_builder):
    """The false-positive guard: a bare ``[[dirname]]`` must not reach ``auto``.

    The basename index counts FILES only, so a directory name resolves to zero
    files — the certainty gate must therefore surface it.
    """
    files = {
        "refs/weaver-ui/note.md": "body\n",
        "links.md": "See [[weaver-ui]].\n",
    }
    fix = repo_builder("subdir-bare-wikilink", files, tracked=list(files))

    consulted = build_consult_result("refs", "build/refs", scope_root=fix.repo)

    ref = _ref_at(consulted, "links.md", "wikilink")
    assert ref["class"] == classify.CLASS_SURFACE
    # A pure move leaves the basename alone: no edit to make.
    assert ref["proposed"] == ref["match"] == "[[weaver-ui]]"


# ---------------------------------------------------------------------------
# 2. Trailing-slash preservation
# ---------------------------------------------------------------------------


def test_inline_code_folder_reference_keeps_its_trailing_slash(repo_builder):
    files = {
        "proto/kg-viz/note.md": "body\n",
        "proto/CLAUDE.md": "Runs live in `kg-viz/` next door.\n",
    }
    fix = repo_builder("trailing-slash-inline-code", files, tracked=list(files))

    consulted = build_consult_result(
        "proto/kg-viz", "history/kg-viz", scope_root=fix.repo
    )

    ref = _ref_at(consulted, "proto/CLAUDE.md", "inline-code-path")
    assert ref["match"] == "kg-viz/"
    assert ref["proposed"] == "../history/kg-viz/"


def test_markdown_link_folder_reference_keeps_its_trailing_slash(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "links.md": "See [the folder](docs/old/) and [the file](docs/old/file.md).\n",
    }
    fix = repo_builder("trailing-slash-markdown", files, tracked=list(files))

    consulted = build_consult_result("docs/old", "docs/new", scope_root=fix.repo)

    folder_ref = next(
        ref for ref in consulted["references"] if ref["match"].endswith("docs/old/)")
    )
    assert folder_ref["proposed"] == "[the folder](docs/new/)"
    # A match WITHOUT a trailing slash is unchanged by the fix.
    file_ref = next(
        ref for ref in consulted["references"] if "file.md" in ref["match"]
    )
    assert file_ref["proposed"] == "[the file](docs/new/file.md)"


def test_frontmatter_folder_value_keeps_its_trailing_slash(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "note.md": "---\nsource: docs/old/\n---\nbody\n",
    }
    fix = repo_builder("trailing-slash-frontmatter", files, tracked=list(files))

    consulted = build_consult_result("docs/old", "docs/new", scope_root=fix.repo)

    ref = _ref_at(consulted, "note.md", "frontmatter-field")
    assert ref["match"] == "docs/old/"
    assert ref["proposed"] == "docs/new/"


def test_config_folder_value_keeps_its_trailing_slash(repo_builder):
    files = {
        "docs/old/file.md": "body\n",
        "settings.json": '{\n  "docsDir": "docs/old/"\n}\n',
    }
    fix = repo_builder("trailing-slash-config", files, tracked=list(files))

    consulted = build_consult_result("docs/old", "docs/new", scope_root=fix.repo)

    ref = _ref_at(consulted, "settings.json", "config-path")
    assert ref["match"] == '"docs/old/"'
    assert ref["proposed"] == '"docs/new/"'
