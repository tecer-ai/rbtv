"""Bare-name frontmatter guards, in-tree sibling proposals, and term references.

* A frontmatter value that is a BARE shared basename (``CLAUDE.md``) is not a
  reference to a moved folder's file — the uniqueness guard the wikilink and
  prose matchers already apply now gates it too.
* A frontmatter value matched by bare basename (a plain ``x.md``, not a
  ``[[wikilink]]``) is never ``auto``: the rewrite would turn a bare name into a
  full path inside a file that may own its own same-named file.
* A relative reference between two files that move TOGETHER stays valid, so the
  proposal is "no change", never an empty string that would delete the token.
* ``--term`` scans for references to a concept TERM (registry ``to:`` edges and
  prose), which no path matcher can see.
"""

from safe_move.act import run_act
from safe_move.cli import main
from safe_move.consult import build_consult_result


def _refs(result, file_path, syntax=None):
    return [
        r
        for r in result["references"]
        if r["file"] == file_path and (syntax is None or r["syntax"] == syntax)
    ]


# ---------------------------------------------------------------------------
# Bare SHARED basename in frontmatter is not a reference
# ---------------------------------------------------------------------------


def test_shared_basename_frontmatter_value_is_not_a_reference(repo_builder):
    """``CLAUDE.md`` is the least unique basename there is — it must not match."""
    files = {
        "hub/kg-views/CLAUDE.md": "# Hub views\n",
        "hub/kg-views/notes.md": "# Notes\n",
        "hub/CLAUDE.md": "# Hub\n",
        "other/CLAUDE.md": "# Other\n",
        "other/steps/p5.task.md": (
            "---\nread_first: CLAUDE.md\n---\n\n# Step 5\n"
        ),
        "third/steps/p9.task.md": (
            "---\nallowlist:\n  - CLAUDE.md\n---\n\n# Step 9\n"
        ),
    }
    fix = repo_builder("shared-basename", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "hub" / "kg-views"),
        str(fix.repo / "hub" / "prototypes" / "kg-views"),
        scope_root=fix.repo,
    )

    assert _refs(result, "other/steps/p5.task.md", "frontmatter-field") == []
    assert _refs(result, "third/steps/p9.task.md", "frontmatter-field") == []


def test_unique_basename_frontmatter_value_still_matches(repo_builder):
    files = {
        "hub/kg-views/design-notes.md": "# Design\n",
        "other/steps/p5.task.md": (
            "---\nread_first: design-notes.md\n---\n\n# Step 5\n"
        ),
    }
    fix = repo_builder("unique-basename", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "hub" / "kg-views"),
        str(fix.repo / "hub" / "prototypes" / "kg-views"),
        scope_root=fix.repo,
    )

    found = _refs(result, "other/steps/p5.task.md", "frontmatter-field")
    assert found, "a UNIQUE bare basename is still a reference"


# ---------------------------------------------------------------------------
# A bare-basename frontmatter value is never auto-applied
# ---------------------------------------------------------------------------


def test_bare_basename_frontmatter_value_is_never_auto(repo_builder):
    """The rewrite turns a bare name into a full path — always the agent's call."""
    files = {
        "hub/roadmap.md": "# Roadmap\n",
        "other/p5.task.md": "---\nallowlist:\n  - roadmap.md\n---\n\n# Step 5\n",
    }
    fix = repo_builder("bare-fm-auto", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "hub" / "roadmap.md"),
        str(fix.repo / "hub" / "docs" / "roadmap.md"),
        scope_root=fix.repo,
    )

    found = _refs(result, "other/p5.task.md", "frontmatter-field")
    assert found, "the unique bare basename is still surfaced"
    assert all(r["class"] == "surface" for r in found), found


def test_wikilink_form_frontmatter_value_still_auto(repo_builder):
    files = {
        "hub/roadmap.md": "# Roadmap\n",
        "other/note.md": "---\nrelated: '[[roadmap]]'\n---\n\n# Note\n",
    }
    fix = repo_builder("wikilink-fm-auto", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "hub" / "roadmap.md"),
        str(fix.repo / "hub" / "plan.md"),
        scope_root=fix.repo,
    )

    found = _refs(result, "other/note.md", "frontmatter-field")
    assert found
    assert any(r["class"] == "auto" for r in found), found


# ---------------------------------------------------------------------------
# Relative sibling references inside the moved folder
# ---------------------------------------------------------------------------


def test_relative_sibling_ref_inside_moved_folder_proposes_no_change(repo_builder):
    files = {
        "build/run/run-log.md": (
            "# Run log\n\n"
            "- dispatched `dispatches/c1-dispatch.md`\n"
            "- shaped `tasks/s13g-shape.task.md`\n"
        ),
        "build/run/dispatches/c1-dispatch.md": "# c1\n",
        "build/run/tasks/s13g-shape.task.md": "# s13g\n",
    }
    fix = repo_builder("sibling-refs", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "build" / "run"),
        str(fix.repo / "build" / "history" / "run"),
        scope_root=fix.repo,
    )

    inline = _refs(result, "build/run/run-log.md", "inline-code-path")
    assert inline, "the sibling paths inside the moved folder are matched"
    for ref in inline:
        assert ref["proposed"] != "", ref
        assert ref["proposed"] == ref["match"], ref


# ---------------------------------------------------------------------------
# Term references
# ---------------------------------------------------------------------------


def _term_fixture(repo_builder, name):
    files = {
        "sd/goal.md": (
            "---\nterm: goal\n---\n\n"
            "# Goal\n\n"
            "edges:\n"
            "- { verb: composed-of, to: goal contract }\n"
        ),
        "sd/goal-contract.md": (
            "---\nterm: goal contract\n---\n\n"
            "# Goal contract\n\n"
            "The goal contract is the frozen intent.\n"
        ),
        "sd/unrelated.md": "# Unrelated\n\nNo mention here.\n",
    }
    return repo_builder(name, files, tracked=list(files))


def test_term_rename_surfaces_and_auto_fixes_edge_form(repo_builder):
    fix = _term_fixture(repo_builder, "term-rename")

    result = build_consult_result(
        str(fix.repo / "sd" / "goal-contract.md"),
        str(fix.repo / "sd" / "cognitive-unit.md"),
        scope_root=fix.repo,
        terms=["goal contract"],
        new_term="cognitive unit",
    )

    edges = _refs(result, "sd/goal.md", "term-edge")
    assert edges, "the `to: goal contract` edge must be found"
    assert edges[0]["proposed"] == "cognitive unit"
    assert edges[0]["class"] == "auto"

    prose = _refs(result, "sd/goal-contract.md", "term-prose")
    assert prose, "prose uses of the term must be surfaced"
    assert all(r["class"] == "surface" for r in prose)

    assert _refs(result, "sd/unrelated.md") == []


def test_term_retirement_surfaces_every_use_with_no_rewrite(repo_builder):
    fix = _term_fixture(repo_builder, "term-retire")

    result = build_consult_result(
        str(fix.repo / "sd" / "goal-contract.md"),
        str(fix.repo / "sd" / "retired" / "goal-contract.md"),
        scope_root=fix.repo,
        terms=["goal contract"],
    )

    term_refs = [
        r for r in result["references"] if r["syntax"].startswith("term-")
    ]
    assert term_refs
    assert all(r["class"] == "surface" for r in term_refs), term_refs
    assert all(r["proposed"] == "" for r in term_refs), term_refs


def test_term_is_auto_derived_from_the_moved_records_frontmatter(repo_builder):
    fix = _term_fixture(repo_builder, "term-derived")

    result = build_consult_result(
        str(fix.repo / "sd" / "goal-contract.md"),
        str(fix.repo / "sd" / "retired" / "goal-contract.md"),
        scope_root=fix.repo,
    )

    assert _refs(result, "sd/goal.md", "term-edge"), "term: frontmatter drives the scan"


def test_key_colon_value_inside_a_sentence_is_prose_not_an_edge(repo_builder):
    """Found live: a real registry sentence read as an edge and reached auto."""
    files = {
        "sd/harness.md": "---\nterm: harness\n---\n\n# Harness\n",
        "sd/story.md": (
            "# US-10\n\n"
            "- The staffer sets up available models and harnesses for that "
            "seat: `seats.csv` — seat-name; llms: harness, model, params "
            "(other harness params such as effort).\n"
        ),
        "sd/agent.md": (
            "---\nterm: agent\n---\n\nedges:\n- { verb: composed-of, to: harness }\n"
        ),
    }
    fix = repo_builder("term-sentence", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "sd" / "harness.md"),
        str(fix.repo / "sd" / "runtime-harness.md"),
        scope_root=fix.repo,
        terms=["harness"],
        new_term="runtime harness",
    )

    # The genuine inline-mapping edge is still auto.
    edges = _refs(result, "sd/agent.md", "term-edge")
    assert edges and edges[0]["class"] == "auto"

    # Nothing inside the sentence is an edge; every hit there is surfaced prose.
    assert _refs(result, "sd/story.md", "term-edge") == []
    story = _refs(result, "sd/story.md")
    assert story and all(r["class"] == "surface" for r in story), story


def test_act_rewrites_the_edge_form_and_leaves_prose_alone(repo_builder):
    fix = _term_fixture(repo_builder, "term-act")

    result = run_act(
        str(fix.repo / "sd" / "goal-contract.md"),
        str(fix.repo / "sd" / "cognitive-unit.md"),
        scope_root=fix.repo,
        terms=["goal contract"],
        new_term="cognitive unit",
        apply="",
    )

    assert result.exit_code == 0, result.errors
    goal = (fix.repo / "sd" / "goal.md").read_text(encoding="utf-8")
    assert "to: cognitive unit }" in goal
    assert "goal contract" not in goal

    moved = (fix.repo / "sd" / "cognitive-unit.md").read_text(encoding="utf-8")
    assert "term: cognitive unit" in moved
    # Prose was surfaced, not applied — it stays untouched.
    assert "The goal contract is the frozen intent." in moved


def test_act_leaves_in_tree_sibling_paths_byte_identical(repo_builder):
    """The empty-string proposals would have DELETED these path tokens."""
    files = {
        "build/run/run-log.md": (
            "# Run log\n\n- dispatched `dispatches/c1-dispatch.md`\n"
        ),
        "build/run/dispatches/c1-dispatch.md": "# c1\n",
    }
    fix = repo_builder("sibling-act", files, tracked=list(files))
    before = (fix.repo / "build" / "run" / "run-log.md").read_text(encoding="utf-8")

    result = run_act(
        str(fix.repo / "build" / "run"),
        str(fix.repo / "build" / "history" / "run"),
        scope_root=fix.repo,
        apply="",
    )

    assert result.exit_code == 0, result.errors
    after = (
        fix.repo / "build" / "history" / "run" / "run-log.md"
    ).read_text(encoding="utf-8")
    assert after == before


def test_cli_accepts_the_term_options(repo_builder, capsys):
    fix = _term_fixture(repo_builder, "term-cli")

    code = main(
        [
            "consult",
            str(fix.repo / "sd" / "goal-contract.md"),
            str(fix.repo / "sd" / "cognitive-unit.md"),
            "--scope-root",
            str(fix.repo),
            "--term",
            "goal contract",
            "--new-term",
            "cognitive unit",
            "--json",
        ]
    )
    captured = capsys.readouterr()

    assert code == 0, captured.err
    assert "term-edge" in captured.out


def test_no_term_scan_disables_the_auto_derivation(repo_builder):
    fix = _term_fixture(repo_builder, "term-disabled")

    result = build_consult_result(
        str(fix.repo / "sd" / "goal-contract.md"),
        str(fix.repo / "sd" / "retired" / "goal-contract.md"),
        scope_root=fix.repo,
        term_scan=False,
    )

    assert [r for r in result["references"] if r["syntax"].startswith("term-")] == []


def test_term_scan_is_off_without_a_term(repo_builder):
    files = {
        "sd/plain.md": "# Plain\n\nno frontmatter term here\n",
        "sd/other.md": "# Other\n\nplain is mentioned here\n",
    }
    fix = repo_builder("term-off", files, tracked=list(files))

    result = build_consult_result(
        str(fix.repo / "sd" / "plain.md"),
        str(fix.repo / "sd" / "moved.md"),
        scope_root=fix.repo,
    )

    assert [r for r in result["references"] if r["syntax"].startswith("term-")] == []
