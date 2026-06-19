"""Tier-1 synthetic fixtures for the non-code reference matrix."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from safe_move.classify import (
    CLASS_AUTO,
    CLASS_PROTECTED,
    CLASS_SURFACE,
    classify,
    classify_operation,
)
from safe_move.matchers import Candidate, find_candidates
from safe_move.replace import compute_proposed
from safe_move.scope import walk_scope
from tests.harness import RepoFixture

AnalyzedRow = tuple[Candidate, str, str | None]


def analyze(
    fix: RepoFixture,
    old: str,
    new: str,
    *,
    exclude: tuple[str, ...] = (),
    read_only: tuple[str, ...] = (),
    generated: tuple[str, ...] = (),
    include_archive: bool = False,
    descend_nested_repos: bool = False,
) -> list[AnalyzedRow]:
    """Run the read-side safe-move pipeline for one synthetic fixture."""
    root = fix.repo
    walked = list(
        walk_scope(
            root,
            exclude=exclude,
            read_only=read_only,
            generated=generated,
            include_archive=include_archive,
            descend_nested_repos=descend_nested_repos,
        )
    )
    candidates = find_candidates(old, walked, root)
    operation = classify_operation(old, new)
    return [
        (
            candidate,
            classify(candidate, operation, scope_root=root),
            compute_proposed(candidate, old, new, operation, scope_root=root),
        )
        for candidate in candidates
    ]


def by_match(rows: list[AnalyzedRow]) -> dict[str, AnalyzedRow]:
    return {candidate.match: (candidate, cls, proposed) for candidate, cls, proposed in rows}


@pytest.mark.parametrize(
    "label,files,old,new,expected_match,expected_proposed",
    [
        (
            "wikilink plain",
            {"old.md": "", "note.md": "See [[old]]."},
            "old.md",
            "new.md",
            "[[old]]",
            "[[new]]",
        ),
        (
            "wikilink alias",
            {"old.md": "", "note.md": "See [[old|Alias]]."},
            "old.md",
            "new.md",
            "[[old|Alias]]",
            "[[new|Alias]]",
        ),
        (
            "wikilink embed",
            {"img/old.png": "", "note.md": "See ![[old.png]]."},
            "img/old.png",
            "img/new.png",
            "![[old.png]]",
            "![[new.png]]",
        ),
        (
            "wikilink fragment",
            {"old.md": "", "note.md": "See [[old#heading]]."},
            "old.md",
            "new.md",
            "[[old#heading]]",
            "[[new#heading]]",
        ),
        (
            "markdown plain",
            {"old.md": "", "note.md": "See [target](old.md)."},
            "old.md",
            "new.md",
            "[target](old.md)",
            "[target](new.md)",
        ),
        (
            "markdown url encoded",
            {"my old.md": "", "note.md": "See [target](my%20old.md)."},
            "my old.md",
            "my new.md",
            "[target](my%20old.md)",
            "[target](my%20new.md)",
        ),
        (
            "markdown angle bracket",
            {"old.md": "", "note.md": "See [target](<old.md>)."},
            "old.md",
            "new.md",
            "[target](<old.md>)",
            "[target](<new.md>)",
        ),
        (
            "frontmatter arbitrary path key",
            {"old-note.md": "", "note.md": "---\ncover: old-note.md\n---\n"},
            "old-note.md",
            "new-note.md",
            "old-note.md",
            "new-note.md",
        ),
        (
            "frontmatter arbitrary wikilink key",
            {"old-note.md": "", "note.md": '---\nthumbnail: "[[old-note]]"\n---\n'},
            "old-note.md",
            "new-note.md",
            "[[old-note]]",
            "[[new-note]]",
        ),
        (
            "config path",
            {"docs/old.md": "", "config.yaml": "input: docs/old.md\n"},
            "docs/old.md",
            "docs/new.md",
            "docs/old.md",
            "docs/new.md",
        ),
    ],
)
def test_live_pointer_forms_are_found_and_auto(
    repo_builder, label, files, old, new, expected_match, expected_proposed
):
    fix = repo_builder(f"live-{label.replace(' ', '-')}", files)

    rows = by_match(analyze(fix, old, new))

    assert expected_match in rows
    _, cls, proposed = rows[expected_match]
    assert cls == CLASS_AUTO
    assert proposed == expected_proposed


def test_frontmatter_non_resolving_value_is_not_matched(repo_builder):
    fix = repo_builder(
        "frontmatter-non-resolving",
        {
            "old-note.md": "",
            "other-note.md": "",
            "note.md": "---\ncover: other-note.md\nthumbnail: \"[[other-note]]\"\n---\n",
        },
    )

    assert analyze(fix, "old-note.md", "new-note.md") == []


def test_substring_collision_matches_only_target_basename(repo_builder):
    fix = repo_builder(
        "substring-collision",
        {
            "agent.md": "",
            "subagent.md": "",
            "note.md": "See [[agent]] and [[subagent]].",
        },
    )

    rows = analyze(fix, "agent.md", "renamed-agent.md")

    assert [candidate.match for candidate, _, _ in rows] == ["[[agent]]"]
    assert rows[0][1] == CLASS_AUTO
    assert rows[0][2] == "[[renamed-agent]]"


def test_ambiguous_bare_basename_surfaces_and_is_never_auto(repo_builder):
    fix = repo_builder(
        "ambiguous-basename",
        {
            "left/old.md": "",
            "right/old.md": "",
            "note.md": "See [[old]].",
        },
    )

    rows = analyze(fix, "left/old.md", "left/new.md")

    assert len(rows) == 1
    assert rows[0][1] == CLASS_SURFACE
    assert rows[0][1] != CLASS_AUTO


def test_ambiguous_bare_basename_frontmatter_value_surfaces_and_is_never_auto(
    repo_builder,
):
    # A frontmatter value carrying a file extension is a file reference; when two
    # files share that basename it is ambiguous and MUST surface — never auto-edit.
    # (A bare value with no extension — e.g. `tags: old` — is a label and no
    # longer matches at all, regardless of key; see test_reorg_fixes.)
    fix = repo_builder(
        "ambiguous-basename-frontmatter",
        {
            "left/old.md": "",
            "right/old.md": "",
            "note.md": "---\ncover: old.md\n---\n",
        },
    )

    rows = analyze(fix, "left/old.md", "left/new.md")

    assert len(rows) == 1
    assert rows[0][0].syntax == "frontmatter-field"
    assert rows[0][1] == CLASS_SURFACE
    assert rows[0][1] != CLASS_AUTO


@pytest.mark.parametrize(
    "label,files,old,new,expected_match",
    [
        (
            "transcript filename",
            {"old.md": "", "meeting-transcript.md": "See [old](old.md).\n"},
            "old.md",
            "new.md",
            "[old](old.md)",
        ),
        (
            "speaker region",
            {
                "old.md": "",
                "notes.md": "Alice: opening\nBob: See [old](old.md).\nAlice: closing\n",
            },
            "old.md",
            "new.md",
            "[old](old.md)",
        ),
        (
            "changelog",
            {"old.md": "", "CHANGELOG.md": "- Moved [old](old.md).\n"},
            "old.md",
            "new.md",
            "[old](old.md)",
        ),
        (
            "blockquote",
            {"old.md": "", "quote.md": "> See [old](old.md).\n"},
            "old.md",
            "new.md",
            "[old](old.md)",
        ),
    ],
)
def test_d4_corroborated_recorded_content_is_protected(
    repo_builder, label, files, old, new, expected_match
):
    fix = repo_builder(f"protected-{label.replace(' ', '-')}", files)

    rows = by_match(analyze(fix, old, new))

    assert expected_match in rows
    _, cls, _ = rows[expected_match]
    assert cls == CLASS_PROTECTED
    assert cls != CLASS_AUTO


@pytest.mark.parametrize(
    "label,content,expected_match,expected_proposed",
    [
        ("lone source line", "Source: [[old]]\n", "[[old]]", "[[new]]"),
        ("lone note line", "Note: see [old](old.md)\n", "[old](old.md)", "[old](new.md)"),
        ("lone word line", "Word: see [old](old.md)\n", "[old](old.md)", "[old](new.md)"),
        ("lone verb bullet", "- moved [old](old.md)\n", "[old](old.md)", "[old](new.md)"),
    ],
)
def test_d4_lone_line_shapes_are_not_protected(repo_builder, label, content, expected_match, expected_proposed):
    fix = repo_builder(
        f"d4-negative-{label.replace(' ', '-')}",
        {"old.md": "", "notes.md": content},
    )

    rows = by_match(analyze(fix, "old.md", "new.md"))

    assert expected_match in rows
    _, cls, proposed = rows[expected_match]
    assert cls == CLASS_AUTO
    assert proposed == expected_proposed


@pytest.mark.parametrize(
    "label,content",
    [
        ("lowercase", "related: [[old]]\nsource: [doc](old.md)\n"),
        ("capitalized", "Related: [[old]]\nSource: [doc](old.md)\n"),
    ],
)
def test_consecutive_key_value_prose_lines_are_not_transcript_protected(
    repo_builder, label, content
):
    fix = repo_builder(
        f"key-value-prose-lines-{label}",
        {
            "old.md": "",
            "notes.md": content,
        },
    )

    rows = by_match(analyze(fix, "old.md", "new.md"))

    assert rows["[[old]]"][1] == CLASS_AUTO
    assert rows["[[old]]"][2] == "[[new]]"
    assert rows["[doc](old.md)"][1] == CLASS_AUTO
    assert rows["[doc](old.md)"][2] == "[doc](new.md)"


def test_excluded_path_is_absent_unless_archive_is_included(repo_builder):
    fix = repo_builder(
        "excluded-path",
        {
            "old.md": "",
            "archive/page.md": "See [[old]].",
        },
    )

    assert analyze(fix, "old.md", "new.md", exclude=("archive",)) == []

    rows = analyze(fix, "old.md", "new.md", exclude=("archive",), include_archive=True)
    assert len(rows) == 1
    assert rows[0][0].file == "archive/page.md"
    assert rows[0][1] == CLASS_AUTO
    assert rows[0][2] == "[[new]]"


def test_read_only_area_surfaces_and_is_never_auto(repo_builder):
    fix = repo_builder(
        "read-only-area",
        {
            "old.md": "",
            "readonly/page.md": "See [[old]].",
        },
    )

    rows = analyze(fix, "old.md", "new.md", read_only=("readonly/**",))

    assert len(rows) == 1
    assert rows[0][1] == CLASS_SURFACE
    assert rows[0][1] != CLASS_AUTO


def test_nested_git_repo_reference_surfaces_and_is_never_auto(repo_builder):
    fix = repo_builder(
        "nested-repo",
        {
            "old.md": "",
            "foreign/page.md": "See [[old]].",
        },
    )
    subprocess.run(["git", "init"], cwd=fix.repo / "foreign", check=True, capture_output=True)

    # Nested repos are skipped by default, so the cross-repo reference must be
    # opted into via descend_nested_repos; it is then surfaced, never auto.
    rows = analyze(fix, "old.md", "new.md", descend_nested_repos=True)

    assert len(rows) == 1
    assert rows[0][0].file == "foreign/page.md"
    assert rows[0][0].boundary == (fix.repo / "foreign").resolve()
    assert rows[0][1] == CLASS_SURFACE
    assert rows[0][1] != CLASS_AUTO

    # Default scope (no opt-in) does NOT read the nested repo at all.
    assert analyze(fix, "old.md", "new.md") == []


def test_case_only_difference_matches_without_overmatching_neighbors(repo_builder):
    fix = repo_builder(
        "case-only",
        {
            "old.md": "",
            "gold.md": "",
            "note.md": "See [[OLD]] and [[gold]].",
        },
    )

    rows = analyze(fix, "old.md", "new.md")

    assert [candidate.match for candidate, _, _ in rows] == ["[[OLD]]"]
    assert rows[0][1] == CLASS_AUTO
    assert rows[0][2] == "[[new]]"


def test_wikilink_anchor_fragment_is_preserved(repo_builder):
    fix = repo_builder(
        "anchor-fragment",
        {
            "old.md": "",
            "note.md": "See [[old#heading]].",
        },
    )

    rows = by_match(analyze(fix, "old.md", "new.md"))

    assert rows["[[old#heading]]"][1] == CLASS_AUTO
    assert rows["[[old#heading]]"][2] == "[[new#heading]]"


def test_relative_markdown_link_in_subdir_recomputes_from_referring_file(repo_builder):
    fix = repo_builder(
        "relative-markdown",
        {
            "docs/old.md": "",
            "notes/page.md": "See [old](../docs/old.md).",
        },
    )

    rows = by_match(analyze(fix, "docs/old.md", "archive/new.md"))

    assert rows["[old](../docs/old.md)"][1] == CLASS_AUTO
    assert rows["[old](../docs/old.md)"][2] == "[old](../archive/new.md)"


def test_generated_file_surfaces_and_is_never_auto(repo_builder):
    fix = repo_builder(
        "generated-file",
        {
            "old.md": "",
            "generated/page.md": "See [[old]].",
        },
    )

    rows = analyze(fix, "old.md", "new.md", generated=("generated/**",))

    assert len(rows) == 1
    assert rows[0][1] == CLASS_SURFACE
    assert rows[0][1] != CLASS_AUTO
