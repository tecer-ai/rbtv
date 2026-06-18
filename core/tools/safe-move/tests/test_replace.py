"""Tests for operation-aware replacement computation."""

from pathlib import Path

import pytest

from safe_move.classify import OPERATION_BOTH, OPERATION_MOVE, OPERATION_RENAME
from safe_move.matchers import Candidate
from safe_move.replace import compute_proposed


def cand(
    *,
    file: str = "notes.md",
    line: int = 1,
    match: str = "old.md",
    context: str = "see old.md",
    syntax: str = "markdown-link",
    target: str = "old.md",
    fragment: str | None = None,
    alias: str | None = None,
    encoding: str = "plain",
    resolves_to: int = 1,
    read_only: bool = False,
    generated: bool = False,
    boundary: Path | None = None,
) -> Candidate:
    """Build a ``Candidate`` with sensible defaults for replacement tests."""
    return Candidate(
        file=file,
        line=line,
        match=match,
        context=context,
        syntax=syntax,
        target=target,
        fragment=fragment,
        alias=alias,
        encoding=encoding,
        resolves_to=resolves_to,
        read_only=read_only,
        generated=generated,
        boundary=boundary,
    )


@pytest.fixture
def scope_root(tmp_path: Path) -> Path:
    """A tiny scope root with old/new files at predictable paths."""
    (tmp_path / "old.md").write_text("old", encoding="utf-8")
    (tmp_path / "new.md").write_text("new", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "old.md").write_text("old", encoding="utf-8")
    (tmp_path / "docs" / "new.md").write_text("new", encoding="utf-8")
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "new.md").write_text("new", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "old.png").write_text("old", encoding="utf-8")
    (tmp_path / "assets" / "new.png").write_text("new", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Wikilinks
# ---------------------------------------------------------------------------


class TestWikilink:
    def test_move_no_edit(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old]]",
            target="old",
            context="see [[old]]",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_MOVE, scope_root=scope_root) == "[[old]]"

    def test_rename_bare_stem(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old]]",
            target="old",
            context="see [[old]]",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new]]"

    def test_rename_with_extension(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old.md]]",
            target="old.md",
            context="see [[old.md]]",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new.md]]"

    def test_rename_embed(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="![[old.png]]",
            target="old.png",
            context="![[old.png]]",
        )
        assert (
            compute_proposed(c, "assets/old.png", "assets/new.png", OPERATION_RENAME, scope_root=scope_root)
            == "![[new.png]]"
        )

    def test_rename_preserves_alias(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old|Alias Text]]",
            target="old",
            context="see [[old|Alias Text]]",
            alias="Alias Text",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new|Alias Text]]"

    def test_rename_preserves_fragment(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old#Heading]]",
            target="old",
            context="see [[old#Heading]]",
            fragment="#Heading",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new#Heading]]"

    def test_rename_preserves_fragment_and_alias(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old#Heading|alias]]",
            target="old",
            context="see [[old#Heading|alias]]",
            fragment="#Heading",
            alias="alias",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[[new#Heading|alias]]"
        )

    def test_move_embed_no_edit(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="![[old.png]]",
            target="old.png",
            context="![[old.png]]",
        )
        assert (
            compute_proposed(c, "assets/old.png", "moved/old.png", OPERATION_MOVE, scope_root=scope_root)
            == "![[old.png]]"
        )

    def test_both_changes_basename(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old]]",
            target="old",
            context="see [[old]]",
        )
        assert compute_proposed(c, "old.md", "notes/new.md", OPERATION_BOTH, scope_root=scope_root) == "[[new]]"


# ---------------------------------------------------------------------------
# Markdown links
# ---------------------------------------------------------------------------


class TestMarkdownLink:
    def test_move_recomputes_relative_path(self, scope_root: Path):
        c = cand(
            file="docs/page.md",
            syntax="markdown-link",
            match="[text](../old.md)",
            target="../old.md",
            context="see [text](../old.md)",
        )
        assert (
            compute_proposed(c, "old.md", "notes/new.md", OPERATION_MOVE, scope_root=scope_root)
            == "[text](../notes/new.md)"
        )

    def test_rename_recomputes_relative_path(self, scope_root: Path):
        c = cand(
            file="docs/page.md",
            syntax="markdown-link",
            match="[label](./old.md)",
            target="./old.md",
            context="see [label](./old.md)",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[label](./new.md)"
        )

    def test_preserves_fragment(self, scope_root: Path):
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[text](old.md#section)",
            target="old.md",
            fragment="#section",
            context="see [text](old.md#section)",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](new.md#section)"
        )

    def test_preserves_label(self, scope_root: Path):
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[My Label](old.md)",
            target="old.md",
            context="see [My Label](old.md)",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[My Label](new.md)"
        )

    def test_url_encoded_reencodes(self, scope_root: Path):
        # old file has a space; new file has a space
        (scope_root / "my old.md").write_text("old", encoding="utf-8")
        (scope_root / "my new.md").write_text("new", encoding="utf-8")
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[text](my%20old.md)",
            target="my old.md",
            encoding="url-encoded",
            context="see [text](my%20old.md)",
        )
        assert (
            compute_proposed(c, "my old.md", "my new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](my%20new.md)"
        )

    def test_url_encoded_with_fragment(self, scope_root: Path):
        (scope_root / "my old.md").write_text("old", encoding="utf-8")
        (scope_root / "my new.md").write_text("new", encoding="utf-8")
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[text](my%20old.md#sec)",
            target="my old.md",
            fragment="#sec",
            encoding="url-encoded",
            context="see [text](my%20old.md#sec)",
        )
        assert (
            compute_proposed(c, "my old.md", "my new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](my%20new.md#sec)"
        )

    def test_angle_bracket(self, scope_root: Path):
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[text](<old.md>)",
            target="old.md",
            encoding="angle-bracket",
            context="see [text](<old.md>)",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](<new.md>)"
        )

    def test_angle_bracket_with_fragment(self, scope_root: Path):
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[text](<old.md#section>)",
            target="old.md",
            fragment="#section",
            encoding="angle-bracket",
            context="see [text](<old.md#section>)",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](<new.md#section>)"
        )

    def test_relative_to_subdir_file(self, scope_root: Path):
        c = cand(
            file="notes/page.md",
            syntax="markdown-link",
            match="[text](../docs/old.md)",
            target="../docs/old.md",
            context="see [text](../docs/old.md)",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[text](../docs/new.md)"
        )


# ---------------------------------------------------------------------------
# Frontmatter fields
# ---------------------------------------------------------------------------


class TestFrontmatterField:
    def test_rename_bare_basename(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="old",
            target="old",
            context="related: old",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "new"

    def test_move_bare_basename_unchanged(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="old",
            target="old",
            context="related: old",
        )
        assert compute_proposed(c, "old.md", "notes/old.md", OPERATION_MOVE, scope_root=scope_root) == "old"

    def test_rename_basename_with_extension(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="old.md",
            target="old.md",
            context="related: old.md",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "new.md"

    def test_move_scope_root_path(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="old.md",
            target="old.md",
            context="related: old.md",
        )
        assert compute_proposed(c, "old.md", "notes/new.md", OPERATION_MOVE, scope_root=scope_root) == "notes/new.md"

    def test_rename_scope_root_path(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="docs/old.md",
            target="docs/old.md",
            context="related: docs/old.md",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "docs/new.md"
        )

    def test_rename_file_relative_path(self, scope_root: Path):
        c = cand(
            file="notes/page.md",
            syntax="frontmatter-field",
            match="../docs/old.md",
            target="../docs/old.md",
            context="related: ../docs/old.md",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "../docs/new.md"
        )

    def test_wikilink_value_rename(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="[[old]]",
            target="old",
            context="related: [[old]]",
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new]]"

    def test_wikilink_value_move(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="[[old]]",
            target="old",
            context="related: [[old]]",
        )
        assert compute_proposed(c, "old.md", "notes/new.md", OPERATION_MOVE, scope_root=scope_root) == "[[old]]"

    def test_wikilink_value_with_alias(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="[[old|Alias]]",
            target="old",
            alias="Alias",
            context="related: [[old|Alias]]",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[[new|Alias]]"
        )

    def test_wikilink_value_with_fragment(self, scope_root: Path):
        c = cand(
            syntax="frontmatter-field",
            match="[[old#Heading]]",
            target="old",
            fragment="#Heading",
            context="related: [[old#Heading]]",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[[new#Heading]]"
        )


# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------


class TestConfigPath:
    def test_rename_double_quoted_path(self, scope_root: Path):
        c = cand(
            file="config.json",
            syntax="config-path",
            match='"docs/old.md"',
            target="docs/old.md",
            context='  "path": "docs/old.md"',
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == '"docs/new.md"'
        )

    def test_rename_single_quoted_path(self, scope_root: Path):
        c = cand(
            file="config.yaml",
            syntax="config-path",
            match="'docs/old.md'",
            target="docs/old.md",
            context="path: 'docs/old.md'",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "'docs/new.md'"
        )

    def test_rename_unquoted_path(self, scope_root: Path):
        c = cand(
            file="config.ini",
            syntax="config-path",
            match="docs/old.md",
            target="docs/old.md",
            context="path = docs/old.md",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_RENAME, scope_root=scope_root)
            == "docs/new.md"
        )

    def test_rename_bare_basename(self, scope_root: Path):
        c = cand(
            file="config.json",
            syntax="config-path",
            match='"old.md"',
            target="old.md",
            context='  "file": "old.md"',
        )
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == '"new.md"'

    def test_move_file_relative_config(self, scope_root: Path):
        c = cand(
            file="notes/config.yaml",
            syntax="config-path",
            match="../docs/old.md",
            target="../docs/old.md",
            context="path: ../docs/old.md",
        )
        assert (
            compute_proposed(c, "docs/old.md", "docs/new.md", OPERATION_MOVE, scope_root=scope_root)
            == "../docs/new.md"
        )


# ---------------------------------------------------------------------------
# Uncertainty → None
# ---------------------------------------------------------------------------


class TestUncertainReturnsNone:
    def test_unknown_syntax(self, scope_root: Path):
        c = cand(syntax="unknown-syntax", match="old.md", target="old.md")
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) is None

    def test_no_scope_root(self):
        c = cand(syntax="wikilink", match="[[old]]", target="old")
        assert compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=None) is None

    def test_invalid_operation(self, scope_root: Path):
        c = cand(syntax="wikilink", match="[[old]]", target="old")
        with pytest.raises(Exception):
            compute_proposed(c, "old.md", "new.md", "invalid", scope_root=scope_root)


# ---------------------------------------------------------------------------
# Case-insensitive untouched parts (match-safety row 19)
# ---------------------------------------------------------------------------


class TestCasePreservation:
    def test_wikilink_alias_casing_preserved(self, scope_root: Path):
        c = cand(
            syntax="wikilink",
            match="[[old|MixedCase Alias]]",
            target="old",
            alias="MixedCase Alias",
            context="see [[old|MixedCase Alias]]",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[[new|MixedCase Alias]]"
        )

    def test_markdown_label_casing_preserved(self, scope_root: Path):
        c = cand(
            file="page.md",
            syntax="markdown-link",
            match="[Mixed Label](old.md)",
            target="old.md",
            context="see [Mixed Label](old.md)",
        )
        assert (
            compute_proposed(c, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
            == "[Mixed Label](new.md)"
        )


# ---------------------------------------------------------------------------
# End-to-end through matcher/classifier integration
# ---------------------------------------------------------------------------


def test_end_to_end_wikilink_rename(scope_root: Path):
    """A real file + real matcher produces the expected proposed value."""
    from safe_move.matchers import find_candidates
    from safe_move.scope import walk_scope

    note = scope_root / "note.md"
    note.write_text("See [[old]] and [[old|alias]].", encoding="utf-8")

    walked = list(walk_scope(scope_root))
    candidates = find_candidates("old.md", walked, scope_root)
    by_match = {c.match: c for c in candidates}

    plain = by_match["[[old]]"]
    aliased = by_match["[[old|alias]]"]

    assert compute_proposed(plain, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root) == "[[new]]"
    assert (
        compute_proposed(aliased, "old.md", "new.md", OPERATION_RENAME, scope_root=scope_root)
        == "[[new|alias]]"
    )


def test_end_to_end_markdown_link_move(scope_root: Path):
    """A real file + real matcher recomputes a relative markdown path."""
    from safe_move.matchers import find_candidates
    from safe_move.scope import walk_scope

    (scope_root / "docs" / "page.md").write_text("[link](../old.md)", encoding="utf-8")

    walked = list(walk_scope(scope_root))
    candidates = find_candidates("old.md", walked, scope_root)
    assert len(candidates) == 1

    assert (
        compute_proposed(candidates[0], "old.md", "notes/new.md", OPERATION_MOVE, scope_root=scope_root)
        == "[link](../notes/new.md)"
    )
