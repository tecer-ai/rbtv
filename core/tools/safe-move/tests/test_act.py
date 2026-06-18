"""Tests for act re-derivation, hash guarding, edits, move, and action log."""

from __future__ import annotations

from safe_move.act import format_action_log, parse_apply, run_act
from safe_move.consult import build_consult_result


SECTIONS = ["moved", "auto-fixed", "surfaced", "drifted", "warnings"]


def _apply_string(refs) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _refs(result, *, cls: str | None = None):
    refs = result["references"]
    if cls is None:
        return refs
    return [ref for ref in refs if ref["class"] == cls]


def test_auto_applies_chosen_surface_applies_unchosen_surface_untouched(repo_builder):
    # The class contract at act time: auto-class refs are applied automatically
    # (even absent from --apply); a surface ref is applied ONLY when its id:hash
    # is passed; an unchosen surface ref is left untouched.
    fix = repo_builder(
        "act-auto-surface-mix",
        {
            "docs/old.md": "old\n",
            "auto.md": "See [doc](docs/old.md).\n",
            "readonly/chosen.md": "Pick [doc](../docs/old.md).\n",
            "readonly/skip.md": "Skip [doc](../docs/old.md).\n",
        },
        tracked=["docs/old.md", "auto.md", "readonly/chosen.md", "readonly/skip.md"],
    )
    consulted = build_consult_result(
        "docs/old.md", "docs/new.md", scope_root=fix.repo, read_only=["readonly/**"]
    )
    assert {ref["file"] for ref in _refs(consulted, cls="auto")} == {"auto.md"}
    chosen = [
        ref
        for ref in _refs(consulted, cls="surface")
        if ref["file"] == "readonly/chosen.md"
    ]

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        read_only=["readonly/**"],
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 0
    assert not (fix.repo / "docs" / "old.md").exists()
    assert (fix.repo / "docs" / "new.md").read_text(encoding="utf-8") == "old\n"
    # Auto applied without being passed in --apply.
    assert (fix.repo / "auto.md").read_text(encoding="utf-8") == "See [doc](docs/new.md).\n"
    # Chosen surface applied.
    assert (fix.repo / "readonly" / "chosen.md").read_text(encoding="utf-8") == (
        "Pick [doc](../docs/new.md).\n"
    )
    # Unchosen surface untouched.
    assert (fix.repo / "readonly" / "skip.md").read_text(encoding="utf-8") == (
        fix.before["readonly/skip.md"]
    )

    log = format_action_log(result)
    for section in SECTIONS:
        assert section in log
    assert "method: git mv" in log
    assert "auto.md [doc](docs/old.md) -> [doc](docs/new.md)" in log


def test_apply_rewrites_multiple_refs_sharing_one_context_line(repo_builder):
    fix = repo_builder(
        "act-shared-context",
        {
            "docs/old.md": "old\n",
            "note.md": "See [[old]] and ![[old#section|embed]].\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    chosen = [
        ref
        for ref in _refs(consulted, cls="auto")
        if ref["file"] == "note.md"
    ]

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 0
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == (
        "See [[new]] and ![[new#section|embed]].\n"
    )
    assert {row["id"] for row in result.auto_fixed} == {ref["id"] for ref in chosen}


def test_drifted_id_is_refused_and_exits_nonzero(repo_builder):
    fix = repo_builder(
        "act-drift",
        {
            "docs/old.md": "old\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    chosen = _refs(consulted, cls="auto")
    (fix.repo / "note.md").write_text("Changed [doc](docs/old.md).\n", encoding="utf-8")

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 1
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == "Changed [doc](docs/old.md).\n"
    assert result.drifted == [{"id": chosen[0]["id"], "file": "note.md", "reason": "drifted"}]
    assert "drifted" in format_action_log(result)
    assert "reason: drifted" in format_action_log(result)


def test_drifted_requested_id_is_not_also_surfaced(repo_builder):
    fix = repo_builder(
        "act-drift-bucket",
        {
            "docs/old.md": "old\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    chosen = _refs(consulted, cls="auto")
    (fix.repo / "note.md").write_text("Changed [doc](docs/old.md).\n", encoding="utf-8")

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    drifted_ids = {row["id"] for row in result.drifted}
    surfaced_ids = {row["id"] for row in result.surfaced}
    assert drifted_ids == {chosen[0]["id"]}
    assert chosen[0]["id"] not in surfaced_ids


def test_duplicate_source_warning_is_listed_once(repo_builder):
    source = repo_builder(
        "act-warning-source",
        {
            "docs/old.md": "old\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    destination = repo_builder(
        "act-warning-destination",
        {"anchor.md": "destination\n"},
        tracked=["anchor.md"],
    )
    new_path = destination.repo / "incoming" / "old.md"

    result = run_act(
        "docs/old.md",
        str(new_path),
        scope_root=source.repo,
        apply="",
    )
    log = format_action_log(result)

    assert [warning["kind"] for warning in result.warnings].count("history-loss") == 1
    assert log.count("history-loss: cross-repo move uses mv; git history does not follow") == 1


def test_pure_move_noop_reference_is_not_auto_fixed(repo_builder):
    fix = repo_builder(
        "act-noop-auto-fixed",
        {
            "docs/old.md": "old\n",
            "note.md": "See [[old]].\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "renamed/old.md", scope_root=fix.repo)
    chosen = _refs(consulted, cls="auto")

    result = run_act(
        "docs/old.md",
        "renamed/old.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert chosen[0]["match"] == chosen[0]["proposed"]
    assert chosen[0]["id"] not in {row["id"] for row in result.auto_fixed}
    assert result.auto_fixed == []
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == "See [[old]].\n"


def test_empty_apply_applies_auto_class_fixes_and_moves(repo_builder):
    # Issue 1 regression: with an empty --apply the move is performed AND every
    # auto-class fix is applied (previously auto refs were surfaced and nothing
    # was written — the documented "auto-applies the auto fixes" was not honored).
    fix = repo_builder(
        "act-empty-apply",
        {
            "docs/old.md": "old\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )

    result = run_act("docs/old.md", "docs/new.md", scope_root=fix.repo, apply="")

    assert result.exit_code == 0
    assert not (fix.repo / "docs" / "old.md").exists()
    assert (fix.repo / "docs" / "new.md").read_text(encoding="utf-8") == "old\n"
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == "See [doc](docs/new.md).\n"
    assert [row["old"] for row in result.auto_fixed] == ["[doc](docs/old.md)"]
    assert result.surfaced == []


def test_self_reference_in_moved_file_is_rewritten_at_new_path(repo_builder):
    fix = repo_builder(
        "act-self-reference",
        {
            "old.md": "Self [[old]].\n",
        },
        tracked=["old.md"],
    )
    consulted = build_consult_result("old.md", "new.md", scope_root=fix.repo)
    chosen = _refs(consulted, cls="auto")

    result = run_act("old.md", "new.md", scope_root=fix.repo, apply=_apply_string(chosen))

    assert result.exit_code == 0
    assert not (fix.repo / "old.md").exists()
    assert (fix.repo / "new.md").read_text(encoding="utf-8") == "Self [[new]].\n"
    assert result.auto_fixed == [
        {
            "id": chosen[0]["id"],
            "file": "new.md",
            "old": "[[old]]",
            "new": "[[new]]",
        }
    ]


def test_destination_exists_refuses_move_and_rewrites_nothing(repo_builder):
    fix = repo_builder(
        "act-destination-exists",
        {
            "docs/old.md": "old\n",
            "docs/new.md": "already here\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "docs/new.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    chosen = _refs(consulted, cls="auto")

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 1
    assert (fix.repo / "docs" / "old.md").read_text(encoding="utf-8") == (
        fix.before["docs/old.md"]
    )
    assert (fix.repo / "docs" / "new.md").read_text(encoding="utf-8") == (
        fix.before["docs/new.md"]
    )
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == fix.before["note.md"]
    assert result.moved is None
    assert result.auto_fixed == []
    assert any("destination already exists" in error for error in result.errors)


def test_action_log_has_all_five_sections_for_partial_failure(repo_builder):
    fix = repo_builder(
        "act-partial-log",
        {
            "docs/old.md": "old\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply="ref-9999:deadbeef",
    )
    log = format_action_log(result)

    assert result.exit_code == 1
    for section in SECTIONS:
        assert section in log
    assert "ref-9999 reason: vanished" in log
    assert "moved\n- docs/old.md -> docs/new.md" in log


def test_apply_pairs_are_order_independent():
    parsed = parse_apply("ref-0002:bbbb,ref-0001:aaaa")

    assert parsed == {"ref-0002": "bbbb", "ref-0001": "aaaa"}
