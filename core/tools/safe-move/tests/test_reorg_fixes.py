"""Regression tests for the four safe-move issues found in real folder-move use.

Each test pins one fix discovered during the 2026-06-17 rbtv-area reorg:

* Issue 1 — ``act`` honors the class contract: ``auto`` applies automatically,
  ``protected`` is never applied even when explicitly requested.
* Issue 2 — a bare frontmatter value with no file extension is a label (tag),
  not a reference, regardless of key; only a value carrying an extension (a file),
  a wikilink, or a path is matched.
* Issue 3 — a path written as inline code (``\\`a/b/c.md\\```) is detected and
  surfaced on a folder move (previously a silent miss).
* Issue 4 — a locked source during a plain (non-git) move completes the
  destination and reports the leftover instead of crashing with a half-deleted
  source and a misleading exit-1.
"""

from __future__ import annotations

from safe_move import classify
from safe_move.act import run_act
from safe_move.consult import build_consult_result


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _raise_oserror(*args, **kwargs):
    raise OSError("simulated cross-device move")


def _raise_permission(*args, **kwargs):
    raise PermissionError("simulated file lock [WinError 32]")


# ---------------------------------------------------------------------------
# Issue 1 — protected refs are never applied, even when requested
# ---------------------------------------------------------------------------


def test_issue1_protected_reference_is_never_applied_even_when_requested(repo_builder):
    fix = repo_builder(
        "issue1-protected",
        {
            "docs/old.md": "old\n",
            "quote.md": "> See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "quote.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    protected = [
        ref
        for ref in consulted["references"]
        if ref["class"] == classify.CLASS_PROTECTED
    ]
    assert protected, "the blockquote markdown link should classify as protected"

    # Explicitly request the protected ref — it must NOT be written.
    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(protected),
    )

    assert result.exit_code == 0
    assert (fix.repo / "quote.md").read_text(encoding="utf-8") == "> See [doc](docs/old.md).\n"
    assert any(w["kind"] == "protected-not-applied" for w in result.warnings)


# ---------------------------------------------------------------------------
# Issue 2 — bare value under a non-link field is not a reference
# ---------------------------------------------------------------------------


def test_issue2_bare_value_under_non_link_field_is_not_a_reference(repo_builder):
    # A bare frontmatter value with no extension is a label, not a reference —
    # regardless of key (the value's FORM decides). A value carrying a file
    # extension IS a file reference. Moving a folder containing ``decisions.md``:
    files = {
        "area/decisions/decisions.md": "body\n",
        "tagged.md": "---\ntags: decisions\n---\nbody\n",       # bare word -> label
        "bareword.md": "---\nrelated: decisions\n---\nbody\n",  # bare, even under a link-ish key -> label
        "filed.md": "---\ncover: decisions.md\n---\nbody\n",    # extension -> file reference
    }
    fix = repo_builder("issue2-bare-tag", files, tracked=list(files))

    consulted = build_consult_result(
        "area/decisions", "area/choices", scope_root=fix.repo
    )
    files_with_refs = {ref["file"] for ref in consulted["references"]}

    assert "tagged.md" not in files_with_refs   # bare tag is not a false positive
    assert "bareword.md" not in files_with_refs  # a bare value never matches, regardless of key
    assert "filed.md" in files_with_refs         # a value with an extension is a file reference


def test_issue2_bare_tag_equal_to_moved_basename_does_not_match_single_file(repo_builder):
    # The same fix at the single-file matcher level: moving ``decisions.md`` does
    # not match a bare ``tags: decisions`` elsewhere.
    files = {
        "area/decisions.md": "body\n",
        "tagged.md": "---\ntags: decisions\n---\nbody\n",
    }
    fix = repo_builder("issue2-single-file", files, tracked=list(files))

    consulted = build_consult_result(
        "area/decisions.md", "area/choices.md", scope_root=fix.repo
    )

    assert not any(ref["file"] == "tagged.md" for ref in consulted["references"])


# ---------------------------------------------------------------------------
# Issue 3 — inline-code path references are detected and surfaced
# ---------------------------------------------------------------------------


def test_issue3_inline_code_path_is_detected_and_surfaced_on_folder_move(repo_builder):
    files = {
        "area/proj/spec.md": "spec body\n",
        "tasks.md": (
            "Ref: `area/proj/spec.md` and the folder `area/proj`.\n"
            "Run `npx something` (not a path, must be ignored).\n"
        ),
    }
    fix = repo_builder("issue3-inline-code", files, tracked=list(files))

    consulted = build_consult_result(
        "area/proj", "area/renamed", scope_root=fix.repo
    )
    inline = [
        ref for ref in consulted["references"] if ref["syntax"] == "inline-code-path"
    ]
    by_match = {ref["match"]: ref for ref in inline}

    # Both the contained-file path and the folder path are detected.
    assert "area/proj/spec.md" in by_match
    assert "area/proj" in by_match
    # Detected inline-code paths are surfaced (never auto) and carry a rewrite.
    assert all(ref["class"] == classify.CLASS_SURFACE for ref in inline)
    assert by_match["area/proj/spec.md"]["proposed"] == "area/renamed/spec.md"
    assert by_match["area/proj"]["proposed"] == "area/renamed"
    # A non-path backtick span (no separator) is not a reference.
    assert "npx something" not in by_match


def test_issue3_chosen_inline_code_path_is_applied(repo_builder):
    # A surfaced inline-code path can be applied by passing its id:hash.
    files = {
        "area/proj/spec.md": "spec body\n",
        "tasks.md": "Ref: `area/proj/spec.md`.\n",
    }
    fix = repo_builder("issue3-apply-inline", files, tracked=list(files))

    consulted = build_consult_result(
        "area/proj", "area/renamed", scope_root=fix.repo
    )
    inline = [
        ref for ref in consulted["references"] if ref["syntax"] == "inline-code-path"
    ]
    assert inline

    result = run_act(
        "area/proj",
        "area/renamed",
        scope_root=fix.repo,
        apply=_apply_string(inline),
    )

    assert result.exit_code == 0
    assert (fix.repo / "tasks.md").read_text(encoding="utf-8") == (
        "Ref: `area/renamed/spec.md`.\n"
    )


# ---------------------------------------------------------------------------
# Issue 4 — a locked source completes the destination and reports the leftover
# ---------------------------------------------------------------------------


def test_issue4_locked_source_completes_destination_and_reports_leftover(
    repo_builder, monkeypatch
):
    files = {"proj/a.txt": "a\n", "proj/sub/b.txt": "b\n"}
    fix = repo_builder("issue4-locked-move", files)  # untracked → plain-mv path

    import safe_move.move as move_mod

    # Force the copy+remove fallback (simulate a cross-device move) and a
    # persistent lock on the source removal; keep retries instant.
    monkeypatch.setattr(move_mod.os, "replace", _raise_oserror)
    monkeypatch.setattr(move_mod.shutil, "rmtree", _raise_permission)
    monkeypatch.setattr(move_mod, "_RMTREE_BACKOFF_SECONDS", 0)

    method, warnings = move_mod.perform_move(
        fix.repo / "proj", fix.repo / "moved" / "proj", fix.repo
    )

    assert method == "mv"
    # Destination is complete.
    assert (fix.repo / "moved" / "proj" / "a.txt").read_text(encoding="utf-8") == "a\n"
    assert (
        fix.repo / "moved" / "proj" / "sub" / "b.txt"
    ).read_text(encoding="utf-8") == "b\n"
    # Source remains (the lock blocked deletion) and is reported — not crashed.
    assert (fix.repo / "proj" / "a.txt").exists()
    leftover = [w for w in warnings if w["kind"] == "partial-source-cleanup"]
    assert len(leftover) == 1
    assert "must be deleted manually" in leftover[0]["message"]
