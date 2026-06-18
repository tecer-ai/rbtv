"""Tests for the safe-move risk classifier."""

from pathlib import Path

import pytest

from safe_move.classify import (
    CLASS_AUTO,
    CLASS_PROTECTED,
    CLASS_SURFACE,
    OPERATION_BOTH,
    OPERATION_MOVE,
    OPERATION_RENAME,
    classify,
    classify_operation,
)
from safe_move.matchers import Candidate


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
    """Build a ``Candidate`` with sensible defaults for testing."""
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


# ---------------------------------------------------------------------------
# Operation classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ("docs/old.md", "notes/old.md", OPERATION_MOVE),
        ("docs/old.md", "docs/new.md", OPERATION_RENAME),
        ("docs/old.md", "notes/new.md", OPERATION_BOTH),
        ("old.md", "old.md", OPERATION_MOVE),  # no-op
    ],
)
def test_classify_operation(old, new, expected):
    assert classify_operation(old, new) == expected


# ---------------------------------------------------------------------------
# Protected regions — the must-not-touch contract
# ---------------------------------------------------------------------------


class TestProtectedRegions:
    """Every protected signal MUST return ``protected`` and NEVER ``auto``."""

    def test_blockquote_is_protected(self):
        c = cand(
            match="old.md",
            context="> As the source said, see old.md for the original.",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_PROTECTED

    def test_blockquote_is_never_auto(self):
        c = cand(
            match="old.md",
            context="> quote old.md",
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) != CLASS_AUTO

    def test_filename_transcript_is_protected(self):
        c = cand(
            file="meeting-transcript.md",
            match="old.md",
            context="Alice: see old.md for context.",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_PROTECTED

    def test_transcript_filename_is_protected(self):
        # D4: filename containing "transcript" remains a strong signal.
        c = cand(
            file="meeting-transcript.md",
            match="old.md",
            context="see old.md",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_PROTECTED

    def test_transcript_consecutive_speakers_are_protected(self, tmp_path: Path):
        # D4: >=2 consecutive speaker/timestamp lines protect the region.
        file_path = tmp_path / "log.md"
        file_path.write_text(
            "[00:14:22] Alice: welcome\n"
            "[00:14:25] Bob: see old.md for context.\n"
            "[00:14:30] Alice: thanks\n",
            encoding="utf-8",
        )
        c = cand(
            file="log.md",
            line=2,
            match="old.md",
            context="[00:14:25] Bob: see old.md for context.",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME, scope_root=tmp_path) == CLASS_PROTECTED

    def test_lone_speaker_line_is_not_protected(self):
        # D4: a single "Word:" line no longer protects by itself.
        c = cand(
            file="dictation.md",
            match="old.md",
            context="Alice: old.md is the file.",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_lone_source_line_is_not_protected(self):
        # D4: a lone "Source: [[old]]" line in an ordinary file is not protected.
        c = cand(
            file="notes.md",
            match="[[old]]",
            context="Source: [[old]]",
            syntax="wikilink",
            target="old",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_lone_note_line_is_not_protected(self):
        # D4: a lone "Note: see old.md" line in an ordinary file is not protected.
        c = cand(
            file="notes.md",
            match="old.md",
            context="Note: see old.md",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_changelog_md_is_protected(self):
        c = cand(
            file="CHANGELOG.md",
            match="old.md",
            context="- moved old.md to new location",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_PROTECTED

    def test_lone_verb_bullet_is_not_protected(self):
        # D4: a single verb bullet in an ordinary file no longer protects.
        c = cand(
            file="work-log.md",
            match="old.md",
            context="* moved old.md into the archive",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_commit_message_body_line_is_protected(self):
        c = cand(
            file="commit-message.txt",
            match="old.md",
            context="    moved old.md to the new folder",
            syntax="markdown-link",
            target="old.md",
        )
        assert classify(c, OPERATION_RENAME) == CLASS_PROTECTED


# ---------------------------------------------------------------------------
# Off-limits locations — must surface, never auto
# ---------------------------------------------------------------------------


class TestOffLimits:
    """Every off-limits flag MUST return ``surface`` and NEVER ``auto``."""

    def test_read_only_is_surface(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            read_only=True,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_SURFACE

    def test_read_only_is_never_auto(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            read_only=True,
        )
        assert classify(c, OPERATION_RENAME) != CLASS_AUTO

    def test_cross_repo_boundary_is_surface(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            boundary=Path("/other/repo"),
        )
        assert classify(c, OPERATION_RENAME) == CLASS_SURFACE

    def test_cross_repo_boundary_is_never_auto(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            boundary=Path("/other/repo"),
        )
        assert classify(c, OPERATION_RENAME) != CLASS_AUTO

    def test_generated_is_surface(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            generated=True,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_SURFACE

    def test_generated_is_never_auto(self):
        c = cand(
            syntax="wikilink",
            target="old.md",
            resolves_to=1,
            generated=True,
        )
        assert classify(c, OPERATION_RENAME) != CLASS_AUTO

    def test_footnote_citation_is_surface(self):
        c = cand(
            syntax="footnote-citation",
            target="old.md",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_SURFACE


# ---------------------------------------------------------------------------
# Match-safety — ambiguous targets surface
# ---------------------------------------------------------------------------


class TestMatchSafety:
    def test_wikilink_ambiguous_basename_is_surface(self):
        c = cand(
            syntax="wikilink",
            target="old",
            resolves_to=2,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_SURFACE

    def test_wikilink_ambiguous_basename_is_never_auto(self):
        c = cand(
            syntax="wikilink",
            target="old",
            resolves_to=2,
        )
        assert classify(c, OPERATION_RENAME) != CLASS_AUTO


# ---------------------------------------------------------------------------
# Auto eligibility by syntax
# ---------------------------------------------------------------------------


class TestAutoEligibility:
    def test_wikilink_rename_unique_is_auto(self):
        c = cand(
            syntax="wikilink",
            target="old",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_wikilink_move_is_auto(self):
        # Basename does not change on a pure move; no replacement needed.
        c = cand(
            syntax="wikilink",
            target="old",
            resolves_to=1,
        )
        assert classify(c, OPERATION_MOVE) == CLASS_AUTO

    def test_wikilink_both_is_auto(self):
        c = cand(
            syntax="wikilink",
            target="old",
            resolves_to=1,
        )
        assert classify(c, OPERATION_BOTH) == CLASS_AUTO

    def test_markdown_link_unique_is_auto(self):
        c = cand(
            syntax="markdown-link",
            target="old.md",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_frontmatter_field_unique_is_auto(self):
        c = cand(
            syntax="frontmatter-field",
            target="old.md",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO

    def test_config_path_unique_is_auto(self):
        c = cand(
            syntax="config-path",
            target="old.md",
            resolves_to=1,
        )
        assert classify(c, OPERATION_RENAME) == CLASS_AUTO


# ---------------------------------------------------------------------------
# Protected/off-limits cases never auto — the safety contract, per fixture
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label, candidate",
    [
        (
            "blockquote quote",
            cand(
                match="old.md",
                context="> see old.md",
                syntax="markdown-link",
                target="old.md",
            ),
        ),
        (
            "transcript file",
            cand(
                file="transcript.md",
                match="old.md",
                context="see old.md",
                syntax="markdown-link",
                target="old.md",
            ),
        ),
        (
            "changelog file",
            cand(
                file="CHANGELOG.md",
                match="old.md",
                context="- moved old.md",
                syntax="markdown-link",
                target="old.md",
            ),
        ),
        (
            "read-only flag",
            cand(
                syntax="wikilink",
                target="old",
                resolves_to=1,
                read_only=True,
            ),
        ),
        (
            "cross-repo boundary",
            cand(
                syntax="wikilink",
                target="old",
                resolves_to=1,
                boundary=Path("/other"),
            ),
        ),
        (
            "generated flag",
            cand(
                syntax="wikilink",
                target="old",
                resolves_to=1,
                generated=True,
            ),
        ),
        (
            "ambiguous wikilink",
            cand(
                syntax="wikilink",
                target="old",
                resolves_to=2,
            ),
        ),
        (
            "footnote citation",
            cand(
                syntax="footnote-citation",
                target="old",
                resolves_to=1,
            ),
        ),
    ],
)
def test_safety_contract_never_auto(label, candidate):
    """Every protected or off-limits fixture is NEVER classed ``auto``."""
    result = classify(candidate, OPERATION_RENAME)
    assert result != CLASS_AUTO, f"{label} was incorrectly classed auto"


@pytest.mark.parametrize(
    "label, candidate, expected",
    [
        ("blockquote quote", cand(match="old.md", context="> see old.md", syntax="markdown-link", target="old.md"), CLASS_PROTECTED),
        ("transcript file", cand(file="transcript.md", match="old.md", context="see old.md", syntax="markdown-link", target="old.md"), CLASS_PROTECTED),
        ("changelog file", cand(file="CHANGELOG.md", match="old.md", context="- moved old.md", syntax="markdown-link", target="old.md"), CLASS_PROTECTED),
        ("read-only", cand(syntax="wikilink", target="old", resolves_to=1, read_only=True), CLASS_SURFACE),
        ("cross-repo", cand(syntax="wikilink", target="old", resolves_to=1, boundary=Path("/other")), CLASS_SURFACE),
        ("generated", cand(syntax="wikilink", target="old", resolves_to=1, generated=True), CLASS_SURFACE),
        ("ambiguous", cand(syntax="wikilink", target="old", resolves_to=2), CLASS_SURFACE),
    ],
)
def test_safety_contract_expected_class(label, candidate, expected):
    """Every protected/off-limits fixture has the expected class."""
    assert classify(candidate, OPERATION_RENAME) == expected


# ---------------------------------------------------------------------------
# Invalid inputs
# ---------------------------------------------------------------------------


def test_invalid_operation_raises():
    c = cand(syntax="wikilink", target="old", resolves_to=1)
    with pytest.raises(ValueError):
        classify(c, "invalid-op")
