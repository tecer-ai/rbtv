"""Literal old-path sweep: self-referential bare-prose + command-embedded paths.

Pins the fix for the real folder-move miss found on 2026-06-18 (moving the
self-referential ``rbtv-sb-merge`` project): internal references to the project's
OWN old path — written as bare prose, inside a ``/<cmd> … <path>`` command span,
or in a config header — were left stale because the syntax-specific matchers only
fire on a fully-resolving link/inline-code span. The literal sweep searches for
the EXACT old path and surfaces every occurrence the matchers missed, always
``surface`` (never auto), with strict path-boundary checks for zero false
positives and dedup against the structured matchers.
"""

from __future__ import annotations

from safe_move import classify
from safe_move.act import run_act
from safe_move.consult import build_consult_result


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _literal_refs(consulted: dict) -> list[dict]:
    return [r for r in consulted["references"] if r["syntax"] == "literal-path"]


# ---------------------------------------------------------------------------
# Folder move — self-referential bare prose + command-embedded paths
# ---------------------------------------------------------------------------


def test_folder_move_surfaces_self_referential_bare_prose_and_command_paths(repo_builder):
    files = {
        "proj/old-name/index.md": "# Project\n",
        # bare-prose self-reference (no markdown link, no backticks)
        "proj/old-name/build/state-capsule.md": (
            "- **Decisions file:** proj/old-name/decisions.md\n"
        ),
        # config-header-style bare-prose self-reference inside the moved tree
        "proj/old-name/build/run-log.md": "spine: proj/old-name/state-capsule.md\n",
        # path embedded inside an inline-code COMMAND span (whole span does not
        # resolve as a path, so the inline-code matcher misses it)
        "proj/old-name/tasks.md": (
            "Resume: `/rbtv-orchestrating resume proj/old-name/state-capsule.md`\n"
        ),
        "proj/old-name/decisions.md": "decisions\n",
        "proj/old-name/state-capsule.md": "capsule\n",
    }
    fix = repo_builder("self-ref-folder", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/old-name", "proj/new-name", scope_root=fix.repo
    )
    literal = _literal_refs(consulted)
    by_loc = {(r["file"], r["line"]): r for r in literal}

    # All three self-references are surfaced.
    assert ("proj/old-name/build/state-capsule.md", 1) in by_loc
    assert ("proj/old-name/build/run-log.md", 1) in by_loc
    assert ("proj/old-name/tasks.md", 1) in by_loc

    # Always surfaced (never auto), and the match is exactly the old folder path.
    for r in literal:
        assert r["class"] == classify.CLASS_SURFACE
        assert r["match"] == "proj/old-name"
        assert r["proposed"] == "proj/new-name"


def test_chosen_literal_self_reference_is_applied_preserving_subpath(repo_builder):
    files = {
        "proj/old-name/index.md": "# Project\n",
        "proj/old-name/tasks.md": (
            "Resume: `/rbtv-orchestrating resume proj/old-name/state-capsule.md`\n"
        ),
        "proj/old-name/state-capsule.md": "capsule\n",
    }
    fix = repo_builder("self-ref-apply", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/old-name", "proj/new-name", scope_root=fix.repo
    )
    literal = _literal_refs(consulted)
    assert literal

    result = run_act(
        "proj/old-name",
        "proj/new-name",
        scope_root=fix.repo,
        apply=_apply_string(literal),
    )

    assert result.exit_code == 0
    # The folder-path span is rewritten; the ``/state-capsule.md`` suffix is kept.
    assert (fix.repo / "proj/new-name/tasks.md").read_text(encoding="utf-8") == (
        "Resume: `/rbtv-orchestrating resume proj/new-name/state-capsule.md`\n"
    )


# ---------------------------------------------------------------------------
# Zero false positives + boundary safety
# ---------------------------------------------------------------------------


def test_literal_sweep_has_zero_false_positives_on_unrelated_slash_tokens(repo_builder):
    files = {
        "proj/old-name/index.md": "# Project\n",
        # A URL whose path mirrors the moved path: the left '/' boundary rejects
        # it (it is a sub-path of example.com, not the scope-root path).
        "noise.md": (
            "Visit https://example.com/proj/old-name/page for details.\n"
            "Fractions like 1/2 and a/b are not paths.\n"
        ),
        # A longer sibling folder must NOT be matched (right boundary is '-').
        "sibling.md": "See proj/old-name-other/file.md here.\n",
        # A path nested under a different parent must NOT be matched (left '/').
        "nested.md": "See vendor/proj/old-name/file.md here.\n",
    }
    fix = repo_builder("self-ref-fp", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/old-name", "proj/new-name", scope_root=fix.repo
    )
    literal_files = {r["file"] for r in _literal_refs(consulted)}

    assert "noise.md" not in literal_files
    assert "sibling.md" not in literal_files
    assert "nested.md" not in literal_files


def test_literal_sweep_matches_genuine_bare_prose_at_scope_root(repo_builder):
    files = {
        "proj/old-name/index.md": "# Project\n",
        "ext.md": "The folder proj/old-name holds the spine.\n",
    }
    fix = repo_builder("self-ref-root", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/old-name", "proj/new-name", scope_root=fix.repo
    )
    literal = _literal_refs(consulted)
    by_loc = {(r["file"], r["line"]): r for r in literal}

    # The exact folder path in bare prose is surfaced (the trailing space is a
    # valid right boundary).
    assert ("ext.md", 1) in by_loc
    assert by_loc[("ext.md", 1)]["match"] == "proj/old-name"
    assert by_loc[("ext.md", 1)]["proposed"] == "proj/new-name"


# ---------------------------------------------------------------------------
# Dedup — a structured-matcher hit is never double-counted as literal-path
# ---------------------------------------------------------------------------


def test_literal_sweep_does_not_double_count_markdown_link(repo_builder):
    files = {
        "proj/old-name/decisions.md": "decisions\n",
        "outside.md": "See [decisions](proj/old-name/decisions.md).\n",
    }
    fix = repo_builder("self-ref-dedup", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/old-name", "proj/new-name", scope_root=fix.repo
    )
    refs_in_outside = [r for r in consulted["references"] if r["file"] == "outside.md"]

    # The markdown link is found once, by the markdown matcher — not duplicated
    # by the literal sweep.
    assert len(refs_in_outside) == 1
    assert refs_in_outside[0]["syntax"] == "markdown-link"


# ---------------------------------------------------------------------------
# File move — bare-prose mention of a moved file path is surfaced
# ---------------------------------------------------------------------------


def test_file_move_surfaces_bare_prose_path(repo_builder):
    files = {
        "proj/doc.md": "body\n",
        "ref.md": "The spec lives at proj/doc.md (read it first).\n",
    }
    fix = repo_builder("self-ref-file", files, tracked=list(files))

    consulted = build_consult_result(
        "proj/doc.md", "proj/renamed.md", scope_root=fix.repo
    )
    literal = _literal_refs(consulted)
    by_loc = {(r["file"], r["line"]): r for r in literal}

    assert ("ref.md", 1) in by_loc
    assert by_loc[("ref.md", 1)]["class"] == classify.CLASS_SURFACE
    assert by_loc[("ref.md", 1)]["match"] == "proj/doc.md"
    assert by_loc[("ref.md", 1)]["proposed"] == "proj/renamed.md"
