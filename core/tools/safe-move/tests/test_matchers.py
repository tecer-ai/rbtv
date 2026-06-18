"""Tests for the non-code reference matchers."""

from __future__ import annotations

from pathlib import Path

import pytest

from safe_move.matchers import (
    Candidate,
    find_candidates,
    match_config_paths,
    match_frontmatter_fields,
    match_markdown_links,
    match_wikilinks,
)
from safe_move.scope import WalkedFile


def _wf(
    tmp_path: Path,
    relpath: str,
    content: str,
    *,
    read_only: bool = False,
    generated: bool = False,
    boundary: Path | None = None,
) -> WalkedFile:
    path = tmp_path / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return WalkedFile(
        path=relpath.replace("\\", "/"),
        abs_path=path,
        read_only=read_only,
        generated=generated,
        boundary=boundary,
    )


def _targets(candidates: list[Candidate]) -> list[str]:
    return [c.target for c in candidates]


def _match(candidates: list[Candidate]) -> list[str]:
    return [c.match for c in candidates]


# ---------------------------------------------------------------------------
# Wikilinks
# ---------------------------------------------------------------------------


def test_wikilink_plain_and_alias_and_embed(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "See [[old-name]] and [[old-name|the alias]] and ![[old-name]].",
    )
    candidates = match_wikilinks(
        "old-name.md",
        wf,
        {"old-name.md", "other.md"},
    )
    assert len(candidates) == 3
    assert all(c.syntax == "wikilink" for c in candidates)
    assert all(c.target == "old-name" for c in candidates)
    assert [c.match for c in candidates] == [
        "[[old-name]]",
        "[[old-name|the alias]]",
        "![[old-name]]",
    ]
    assert candidates[1].alias == "the alias"
    assert candidates[0].alias is None
    assert all(c.fragment is None for c in candidates)
    assert all(c.resolves_to == 1 for c in candidates)


def test_wikilink_with_fragment(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "Jump to [[old-name#heading]] here.")
    candidates = match_wikilinks("old-name.md", wf, {"old-name.md"})
    assert len(candidates) == 1
    assert candidates[0].fragment == "#heading"
    assert candidates[0].target == "old-name"
    assert candidates[0].match == "[[old-name#heading]]"


def test_wikilink_block_id(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "See [[old-name#^block-id]].")
    candidates = match_wikilinks("old-name.md", wf, {"old-name.md"})
    assert len(candidates) == 1
    assert candidates[0].fragment == "#^block-id"


def test_wikilink_respects_basename_with_extension(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[[old-name.md]] works too.")
    candidates = match_wikilinks("old-name.md", wf, {"old-name.md"})
    assert len(candidates) == 1
    assert candidates[0].target == "old-name.md"


def test_wikilink_case_insensitive(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[[OLD-NAME]] link.")
    candidates = match_wikilinks("old-name.md", wf, {"old-name.md"})
    assert len(candidates) == 1
    assert candidates[0].match == "[[OLD-NAME]]"
    assert candidates[0].target == "OLD-NAME"


def test_wikilink_boundary_agent_not_subagent(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "[[agent]] is okay; [[subagent]] is different.",
    )
    candidates = match_wikilinks("agent.md", wf, {"agent.md", "subagent.md"})
    assert len(candidates) == 1
    assert candidates[0].target == "agent"
    assert candidates[0].match == "[[agent]]"


def test_wikilink_ambiguous_basename_surfaces(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[[dup]] is ambiguous.")
    candidates = match_wikilinks(
        "dup.md",
        wf,
        {"dup.md", "dup.txt"},
    )
    assert len(candidates) == 1
    assert candidates[0].resolves_to == 2


def test_wikilink_does_not_match_unrelated_basename(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[[other]] here.")
    candidates = match_wikilinks("old-name.md", wf, {"old-name.md", "other.md"})
    assert len(candidates) == 0


# ---------------------------------------------------------------------------
# Markdown links
# ---------------------------------------------------------------------------


def test_markdown_link_plain(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[text](./old-name.md)")
    candidates = match_markdown_links("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].syntax == "markdown-link"
    assert candidates[0].target == "./old-name.md"
    assert candidates[0].encoding == "plain"


def test_markdown_link_url_encoded(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[text](my%20old-name.md)")
    (tmp_path / "my old-name.md").write_text("x", encoding="utf-8")
    candidates = match_markdown_links("my old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "my old-name.md"
    assert candidates[0].encoding == "url-encoded"
    assert candidates[0].match == "[text](my%20old-name.md)"


def test_markdown_link_angle_bracket(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[text](<my old-name.md>)")
    (tmp_path / "my old-name.md").write_text("x", encoding="utf-8")
    candidates = match_markdown_links("my old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "my old-name.md"
    assert candidates[0].encoding == "angle-bracket"


def test_markdown_link_with_fragment(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[text](./old-name.md#section)")
    candidates = match_markdown_links("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "./old-name.md"
    assert candidates[0].fragment == "#section"


def test_markdown_link_boundary(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "[a](agent.md) and [b](subagent.md)",
    )
    candidates = match_markdown_links("notes/agent.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "agent.md"


def test_markdown_link_case_insensitive(tmp_path: Path) -> None:
    wf = _wf(tmp_path, "notes/a.md", "[text](./OLD-NAME.MD)")
    candidates = match_markdown_links("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------


def test_frontmatter_scalar_value(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "---\narea: notes/old-name.md\n---\n\nbody\n",
    )
    candidates = match_frontmatter_fields("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].syntax == "frontmatter-field"
    assert candidates[0].target == "notes/old-name.md"
    assert candidates[0].match == "notes/old-name.md"


def test_frontmatter_inline_list(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        '---\nrelated: ["notes/old-name.md", "other.md"]\n---\n',
    )
    candidates = match_frontmatter_fields("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "notes/old-name.md"


def test_frontmatter_multiline_list(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "---\nrelated:\n  - notes/old-name.md\n  - other.md\n---\n",
    )
    candidates = match_frontmatter_fields("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "notes/old-name.md"


def test_frontmatter_boundary(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "---\nrelated: [agent.md, subagent.md]\n---\n",
    )
    candidates = match_frontmatter_fields("agent.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "agent.md"


def test_frontmatter_bare_word_without_extension_is_a_label_not_a_reference(tmp_path: Path) -> None:
    # A bare frontmatter value with no extension is a tag/label, not a file
    # reference — even under a key like `area`. The value's FORM decides, not the
    # key (Issue 2 refinement: extension -> file, trailing `/` -> folder, else label).
    wf = _wf(tmp_path, "notes/a.md", "---\narea: old-name\n---\n")
    candidates = match_frontmatter_fields("old-name.md", wf, tmp_path)
    assert candidates == []


def test_frontmatter_value_with_extension_is_a_file_reference(tmp_path: Path) -> None:
    # A value carrying a file extension IS a file reference, matched by basename
    # regardless of key.
    wf = _wf(tmp_path, "notes/a.md", "---\ncover: old-name.md\n---\n")
    candidates = match_frontmatter_fields("docs/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "old-name.md"
    assert candidates[0].syntax == "frontmatter-field"


def test_frontmatter_arbitrary_key_matches_by_value(tmp_path: Path) -> None:
    # D5: any frontmatter key whose value resolves to old is matched.
    wf = _wf(
        tmp_path,
        "notes/a.md",
        '---\ncover: notes/old-name.md\nthumbnail: "[[old-name]]"\n---\n',
    )
    (tmp_path / "notes" / "old-name.md").write_text("x", encoding="utf-8")
    candidates = match_frontmatter_fields("notes/old-name.md", wf, tmp_path)
    targets = _targets(candidates)
    assert "notes/old-name.md" in targets
    assert "old-name" in targets
    assert all(c.syntax == "frontmatter-field" for c in candidates)


def test_frontmatter_non_resolving_value_not_matched(tmp_path: Path) -> None:
    # D5: values that do not resolve to old are ignored, regardless of key.
    wf = _wf(
        tmp_path,
        "notes/a.md",
        '---\ntitle: My Note\ncover: other.md\n---\n',
    )
    candidates = match_frontmatter_fields("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 0


def test_frontmatter_boundary_agent_not_subagent(tmp_path: Path) -> None:
    # D5: boundary-aware basename matching is preserved in arbitrary keys.
    wf = _wf(
        tmp_path,
        "notes/a.md",
        '---\nrelated: [agent.md, subagent.md]\n---\n',
    )
    candidates = match_frontmatter_fields("agent.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "agent.md"


# ---------------------------------------------------------------------------
# Config paths
# ---------------------------------------------------------------------------


def test_config_json_value(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "config.json",
        '{"path": "notes/old-name.md", "other": "x"}',
    )
    candidates = match_config_paths("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].syntax == "config-path"
    assert candidates[0].target == "notes/old-name.md"


def test_config_yaml_value(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "config.yaml",
        "path: notes/old-name.md\nother: x\n",
    )
    candidates = match_config_paths("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "notes/old-name.md"


def test_config_toml_value(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "config.toml",
        'path = "notes/old-name.md"\nother = "x"\n',
    )
    candidates = match_config_paths("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1


def test_config_ini_value(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "config.ini",
        "[section]\npath = notes/old-name.md\n",
    )
    candidates = match_config_paths("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 1


def test_config_boundary(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "config.json",
        '{"a": "agent.md", "b": "subagent.md"}',
    )
    candidates = match_config_paths("agent.md", wf, tmp_path)
    assert len(candidates) == 1
    assert candidates[0].target == "agent.md"


def test_config_ignores_non_config_extension(tmp_path: Path) -> None:
    wf = _wf(
        tmp_path,
        "notes/a.txt",
        'path: "notes/old-name.md"',
    )
    candidates = match_config_paths("notes/old-name.md", wf, tmp_path)
    assert len(candidates) == 0


# ---------------------------------------------------------------------------
# find_candidates orchestrator
# ---------------------------------------------------------------------------


def test_find_candidates_all_syntaxes(tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir()
    (tmp_path / "notes" / "old-name.md").write_text("old", encoding="utf-8")
    (tmp_path / "notes" / "other.md").write_text("other", encoding="utf-8")

    files = [
        _wf(
            tmp_path,
            "notes/a.md",
            "---\narea: notes/old-name.md\n---\n"
            "[[old-name]] and [link](../notes/old-name.md).",
        ),
        _wf(
            tmp_path,
            "config.toml",
            'path = "notes/old-name.md"',
        ),
    ]

    candidates = find_candidates("notes/old-name.md", files, tmp_path)
    syntaxes = sorted(c.syntax for c in candidates)
    assert syntaxes == [
        "config-path",
        "frontmatter-field",
        "markdown-link",
        "wikilink",
    ]


def test_find_candidates_carries_scope_flags(tmp_path: Path) -> None:
    (tmp_path / "notes").mkdir(parents=True, exist_ok=True)
    (tmp_path / "notes" / "old-name.md").write_text("x", encoding="utf-8")

    boundary = tmp_path / "other-repo"
    wf = _wf(
        tmp_path,
        "notes/a.md",
        "[[old-name]]",
        read_only=True,
        generated=True,
        boundary=boundary,
    )
    candidates = find_candidates("notes/old-name.md", [wf], tmp_path)
    assert len(candidates) == 1
    assert candidates[0].read_only is True
    assert candidates[0].generated is True
    assert candidates[0].boundary == boundary
