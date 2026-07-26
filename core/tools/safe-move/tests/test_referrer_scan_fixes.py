"""Referrer-scan fixes.

Three defects observed in real campaign runs, all in the *finding* half of the
tool (what the scan can see), plus the summary-clutter observation that rides
with them:

* ``build/`` / ``dist/`` / ``target/`` directories were hardcoded skips for the
  WHOLE scan, so a referrer living under ``build/`` was never found. They are
  now scanned; genuine build OUTPUT is excluded by gitignore, which the walk
  already honors.
* A reference written relative to the WORKSPACE root while the scan is scoped to
  a subtree — so the path begins with the scope root's own directory name
  (``1-projects/...`` while ``--scope-root`` is ``.../1-projects``) — was not
  matched by the literal sweep. Nor was a Windows-backslash absolute path.
* A reference that needs NO rewrite (``proposed == match``) was printed in the
  actionable ``surface`` decision list, cluttering the review set.
"""

from pathlib import Path

import pytest

from safe_move import report
from safe_move.consult import build_consult_result


def _refs_in(result, file_path):
    return [r for r in result["references"] if r["file"] == file_path]


# ---------------------------------------------------------------------------
# build/ (and dist/, target/) are part of the referrer scan
# ---------------------------------------------------------------------------


def test_referrer_under_build_dir_is_found(repo_builder):
    fix = repo_builder(
        "build-referrer",
        {
            "docs/roadmap.md": "# Roadmap\n",
            "build/plan.md": "See [roadmap](../docs/roadmap.md).\n",
        },
        tracked=["docs/roadmap.md", "build/plan.md"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "roadmap.md"),
        str(fix.repo / "roadmap.md"),
        scope_root=fix.repo,
    )

    found = _refs_in(result, "build/plan.md")
    assert found, "a referrer under build/ must be discovered"
    assert found[0]["syntax"] == "markdown-link"


@pytest.mark.parametrize("dirname", ["dist", "target", "build"])
def test_referrer_under_output_named_dirs_is_found(repo_builder, dirname):
    fix = repo_builder(
        f"outdir-{dirname}",
        {
            "docs/roadmap.md": "# Roadmap\n",
            f"{dirname}/plan.md": "See [roadmap](../docs/roadmap.md).\n",
        },
        tracked=["docs/roadmap.md", f"{dirname}/plan.md"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "roadmap.md"),
        str(fix.repo / "roadmap.md"),
        scope_root=fix.repo,
    )

    assert _refs_in(result, f"{dirname}/plan.md")


def test_gitignored_build_dir_is_still_skipped(repo_builder):
    """Real build OUTPUT is gitignored, and the walk already honors gitignore."""
    fix = repo_builder(
        "build-ignored",
        {
            ".gitignore": "build/\n",
            "docs/roadmap.md": "# Roadmap\n",
            "build/plan.md": "See [roadmap](../docs/roadmap.md).\n",
        },
        tracked=[".gitignore", "docs/roadmap.md"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "roadmap.md"),
        str(fix.repo / "roadmap.md"),
        scope_root=fix.repo,
    )

    assert _refs_in(result, "build/plan.md") == []


def test_dependency_dirs_are_still_skipped(repo_builder):
    fix = repo_builder(
        "dep-dirs",
        {
            "docs/roadmap.md": "# Roadmap\n",
            "node_modules/pkg/readme.md": "See [roadmap](../../docs/roadmap.md).\n",
            "__pycache__/notes.md": "See [roadmap](../docs/roadmap.md).\n",
        },
        tracked=["docs/roadmap.md"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "roadmap.md"),
        str(fix.repo / "roadmap.md"),
        scope_root=fix.repo,
    )

    assert _refs_in(result, "node_modules/pkg/readme.md") == []
    assert _refs_in(result, "__pycache__/notes.md") == []


# ---------------------------------------------------------------------------
# Workspace-relative reference prefixed with the scope root's own dir name
# ---------------------------------------------------------------------------


def _scoped_fixture(repo_builder, name, extra_files):
    files = {
        "1-projects/proj/refs/weaver-ui/notes.md": "# Weaver UI\n",
        "1-projects/proj/proj.md": "# Proj\n",
    }
    files.update(extra_files)
    return repo_builder(name, files, tracked=list(files))


def test_workspace_relative_reference_under_scope_root_is_matched(repo_builder):
    """``1-projects/...`` written while ``--scope-root`` IS ``.../1-projects``."""
    fix = _scoped_fixture(
        repo_builder,
        "scope-prefix",
        {
            "1-projects/other/other-tasks.md": (
                "- [ ] Port the UI refs from `1-projects/proj/refs/weaver-ui`\n"
            )
        },
    )

    result = build_consult_result(
        str(fix.repo / "1-projects" / "proj" / "refs"),
        str(fix.repo / "1-projects" / "proj" / "build" / "refs"),
        scope_root=fix.repo / "1-projects",
    )

    found = _refs_in(result, "other/other-tasks.md")
    assert found, "a workspace-relative reference to the moved folder must be matched"
    # The reference points at a SUBDIRECTORY of the moved folder, so the
    # structured inline-code matcher now owns it and rewrites the WHOLE path.
    # (It used to be caught only by the literal sweep, which matched the moved
    # folder's path as a PREFIX span and proposed the folder path alone; the
    # sweep dedups against the structured hit, so that record is gone.)
    assert any(
        r["proposed"] == "1-projects/proj/build/refs/weaver-ui" for r in found
    ), [r["proposed"] for r in found]


def test_windows_absolute_backslash_reference_is_matched(repo_builder):
    fix = _scoped_fixture(
        repo_builder,
        "win-abs",
        {"1-projects/other/other-tasks.md": "- [ ] see PLACEHOLDER\n"},
    )
    old_abs = fix.repo / "1-projects" / "proj" / "refs"
    tasks = fix.repo / "1-projects" / "other" / "other-tasks.md"
    windows_form = str(old_abs).replace("/", "\\")
    tasks.write_text(f'- [ ] see "{windows_form}\\weaver-ui"\n', encoding="utf-8")

    result = build_consult_result(
        str(old_abs),
        str(fix.repo / "1-projects" / "proj" / "build" / "refs"),
        scope_root=fix.repo / "1-projects",
    )

    found = _refs_in(result, "other/other-tasks.md")
    assert found, "a Windows-backslash absolute reference must be matched"
    assert all("\\" in r["proposed"] for r in found), [r["proposed"] for r in found]


def test_absolute_posix_reference_is_matched(repo_builder):
    old_abs = None
    fix = _scoped_fixture(
        repo_builder,
        "posix-abs",
        {"1-projects/other/other-tasks.md": "placeholder\n"},
    )
    old_abs = fix.repo / "1-projects" / "proj" / "refs"
    (fix.repo / "1-projects" / "other" / "other-tasks.md").write_text(
        f"- [ ] see `{old_abs.as_posix()}/weaver-ui`\n", encoding="utf-8"
    )

    result = build_consult_result(
        str(old_abs),
        str(fix.repo / "1-projects" / "proj" / "build" / "refs"),
        scope_root=fix.repo / "1-projects",
    )

    assert _refs_in(result, "other/other-tasks.md")


def test_scope_relative_literal_still_matched_and_not_duplicated(repo_builder):
    """The pre-existing scope-relative literal form keeps working, once."""
    fix = _scoped_fixture(
        repo_builder,
        "scope-rel",
        {"1-projects/other/other-tasks.md": "- [ ] see `proj/refs/weaver-ui`\n"},
    )

    result = build_consult_result(
        str(fix.repo / "1-projects" / "proj" / "refs"),
        str(fix.repo / "1-projects" / "proj" / "build" / "refs"),
        scope_root=fix.repo / "1-projects",
    )

    found = _refs_in(result, "other/other-tasks.md")
    assert len(found) == 1, found


# ---------------------------------------------------------------------------
# .ps1 (and other unsupported-language) warning accuracy
# ---------------------------------------------------------------------------


def test_unsupported_language_warning_does_not_overclaim(repo_builder):
    """A ``.ps1`` referrer's PATH literals ARE swept; only AST matching is skipped."""
    fix = repo_builder(
        "ps1-referrer",
        {
            "docs/roadmap.md": "# Roadmap\n",
            "scripts/run.ps1": '$plan = "docs/roadmap.md"\n',
        },
        tracked=["docs/roadmap.md", "scripts/run.ps1"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "roadmap.md"),
        str(fix.repo / "roadmap.md"),
        scope_root=fix.repo,
    )

    assert _refs_in(result, "scripts/run.ps1"), "the literal sweep must see .ps1 files"
    unsupported = [
        w for w in result["warnings"] if w["kind"] == "code-unsupported-language"
    ]
    assert unsupported
    message = unsupported[0]["message"]
    assert "were not discovered" not in message, message
    assert "literal" in message.lower(), message


# ---------------------------------------------------------------------------
# No-op proposals are not actionable clutter
# ---------------------------------------------------------------------------


def test_no_op_surface_refs_are_not_listed_as_actionable(repo_builder):
    """``story.md -> story.md`` is nothing to decide; it collapses to a count."""
    fix = repo_builder(
        "noop-summary",
        {
            "docs/story.md": "# Story\n",
            "notes/cites.md": "The registry cites `story.md` as the source.\n",
        },
        tracked=["docs/story.md", "notes/cites.md"],
    )

    result = build_consult_result(
        str(fix.repo / "docs" / "story.md"),
        str(fix.repo / "archive" / "story.md"),
        scope_root=fix.repo,
    )

    noop = [
        r
        for r in result["references"]
        if r["file"] == "notes/cites.md" and r["proposed"] == r["match"]
    ]
    assert noop, "the bare-basename citation is a no-op reference"

    summary = report.format_consult_summary(result, "docs/story.md", "archive/story.md", None)
    for ref in noop:
        assert f"{ref['id']}:{ref['hash']}" not in summary, summary
    assert "no-op" in summary, summary
