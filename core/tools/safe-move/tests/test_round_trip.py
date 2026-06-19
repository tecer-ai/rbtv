"""End-to-end consult-to-act fixture matrix."""

from __future__ import annotations

import subprocess
from pathlib import Path

from safe_move.act import format_action_log, run_act
from safe_move.consult import build_consult_result


ACTION_LOG_SECTIONS = ("moved", "auto-fixed", "surfaced", "drifted", "warnings")


def _apply_string(refs: list[dict]) -> str:
    return ",".join(f"{ref['id']}:{ref['hash']}" for ref in refs)


def _auto_refs(result: dict) -> list[dict]:
    return [ref for ref in result["references"] if ref["class"] == "auto"]


def _refs_for_file(result: dict, file: str) -> list[dict]:
    return [ref for ref in result["references"] if ref["file"] == file]


def _text_tree(root: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")
    return files


def _commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", message], cwd=repo, check=True, capture_output=True)


def _git_log_follow(repo: Path, path: str) -> str:
    result = subprocess.run(
        ["git", "log", "--follow", "--format=%s", "--", path],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def test_round_trip_feeds_real_consult_auto_pairs_to_real_act(repo_builder):
    fix = repo_builder(
        "round-trip-all-auto",
        {
            "docs/old.md": "canonical body\n",
            "notes/wiki.md": "See [[old]] and ![[old#section|embed]].\n",
            "links/ref.md": "Read [doc](../docs/old.md).\n",
            "meta.md": "---\nrelated: docs/old.md\n---\nbody\n",
            "settings.yaml": "target: docs/old.md\n",
            "manual/review.md": "Manual [doc](../docs/old.md).\n",
        },
        tracked=[
            "docs/old.md",
            "notes/wiki.md",
            "links/ref.md",
            "meta.md",
            "settings.yaml",
            "manual/review.md",
        ],
    )
    consulted = build_consult_result(
        "docs/old.md",
        "moved/new.md",
        scope_root=fix.repo,
        read_only=["manual/**"],
    )
    chosen = _auto_refs(consulted)

    assert {ref["id"] for ref in chosen} == {
        ref["id"] for ref in consulted["references"] if ref["class"] == "auto"
    }
    assert chosen

    result = run_act(
        "docs/old.md",
        "moved/new.md",
        scope_root=fix.repo,
        read_only=["manual/**"],
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 0
    assert {row["id"] for row in result.auto_fixed} == {ref["id"] for ref in chosen}
    assert _text_tree(fix.repo) == {
        "links/ref.md": "Read [doc](../moved/new.md).\n",
        "manual/review.md": "Manual [doc](../docs/old.md).\n",
        "meta.md": "---\nrelated: moved/new.md\n---\nbody\n",
        "moved/new.md": "canonical body\n",
        "notes/wiki.md": "See [[new]] and ![[new#section|embed]].\n",
        "settings.yaml": "target: moved/new.md\n",
    }


def test_tracked_round_trip_uses_git_mv_and_preserves_follow_history(repo_builder):
    fix = repo_builder(
        "round-trip-git-mv",
        {
            "docs/old.md": "tracked body\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "renamed/new.md", scope_root=fix.repo)

    result = run_act(
        "docs/old.md",
        "renamed/new.md",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )
    _commit(fix.repo, "move tracked file")

    assert result.exit_code == 0
    assert result.moved == {"old": "docs/old.md", "new": "renamed/new.md", "method": "git mv"}
    assert "method: git mv" in format_action_log(result)
    assert "tracked body\n" == (fix.repo / "renamed/new.md").read_text(encoding="utf-8")
    log = _git_log_follow(fix.repo, "renamed/new.md")
    assert "move tracked file" in log
    assert "seed fixture" in log


def test_untracked_round_trip_uses_plain_mv(repo_builder):
    fix = repo_builder(
        "round-trip-plain-mv",
        {
            "docs/old.md": "untracked body\n",
            "note.md": "See [doc](docs/old.md).\n",
        },
        tracked=["note.md"],
    )
    consulted = build_consult_result("docs/old.md", "renamed/old.md", scope_root=fix.repo)

    result = run_act(
        "docs/old.md",
        "renamed/old.md",
        scope_root=fix.repo,
        apply=_apply_string(_auto_refs(consulted)),
    )

    assert result.exit_code == 0
    assert result.moved == {"old": "docs/old.md", "new": "renamed/old.md", "method": "mv"}
    assert "method: mv" in format_action_log(result)
    assert not (fix.repo / "docs" / "old.md").exists()
    assert (fix.repo / "renamed" / "old.md").read_text(encoding="utf-8") == "untracked body\n"


def test_cross_repo_round_trip_uses_mv_warns_and_surfaces_boundary_refs(repo_builder):
    source = repo_builder(
        "round-trip-cross-source",
        {
            "docs/old.md": "cross repo body\n",
            "local.md": "Local [doc](docs/old.md).\n",
            "foreign/ref.md": "Foreign [doc](../docs/old.md).\n",
        },
        tracked=["docs/old.md", "local.md", "foreign/ref.md"],
    )
    destination = repo_builder(
        "round-trip-cross-dest",
        {"keep.md": "destination repo\n"},
        tracked=["keep.md"],
    )
    subprocess.run(["git", "init"], cwd=source.repo / "foreign", check=True, capture_output=True)
    new_path = destination.repo / "incoming" / "old.md"

    # Opt into the nested 'foreign' repo so the cross-repo reference is found
    # (nested repos are skipped by default).
    consulted = build_consult_result(
        "docs/old.md", str(new_path), scope_root=source.repo, descend_nested_repos=True
    )
    boundary_refs = _refs_for_file(consulted, "foreign/ref.md")

    result = run_act(
        "docs/old.md",
        str(new_path),
        scope_root=source.repo,
        descend_nested_repos=True,
        apply=_apply_string(_auto_refs(consulted)),
    )
    log = format_action_log(result)

    assert result.exit_code == 0
    assert result.moved == {
        "old": "docs/old.md",
        "new": new_path.as_posix(),
        "method": "mv",
    }
    assert [ref["class"] for ref in boundary_refs] == ["surface"]
    assert boundary_refs[0]["id"] in {row["id"] for row in result.surfaced}
    assert "history-loss" in log
    assert "cross-project" in log
    assert (new_path).read_text(encoding="utf-8") == "cross repo body\n"
    assert (source.repo / "foreign" / "ref.md").read_text(encoding="utf-8") == (
        "Foreign [doc](../docs/old.md).\n"
    )


def test_consult_to_mutate_to_act_refuses_drifted_site(repo_builder):
    fix = repo_builder(
        "round-trip-drift",
        {
            "docs/old.md": "body\n",
            "note.md": "Before [doc](docs/old.md) after.\n",
        },
        tracked=["docs/old.md", "note.md"],
    )
    consulted = build_consult_result("docs/old.md", "docs/new.md", scope_root=fix.repo)
    chosen = _auto_refs(consulted)
    (fix.repo / "note.md").write_text("Before CHANGED [doc](docs/old.md) after.\n", encoding="utf-8")

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        apply=_apply_string(chosen),
    )

    assert result.exit_code == 1
    assert result.drifted == [{"id": chosen[0]["id"], "file": "note.md", "reason": "drifted"}]
    assert (fix.repo / "note.md").read_text(encoding="utf-8") == (
        "Before CHANGED [doc](docs/old.md) after.\n"
    )
    assert "reason: drifted" in format_action_log(result)


def test_action_log_contains_all_five_sections_in_one_round_trip(repo_builder):
    fix = repo_builder(
        "round-trip-action-log",
        {
            "docs/old.md": "body\n",
            "auto.md": "Auto [doc](docs/old.md).\n",
            "stale.md": "Stale [doc](docs/old.md).\n",
            "manual/review.md": "Manual [doc](../docs/old.md).\n",
            "generated/config.yaml": "target: docs/old.md\n",
        },
        tracked=[
            "docs/old.md",
            "auto.md",
            "stale.md",
            "manual/review.md",
            "generated/config.yaml",
        ],
    )
    consulted = build_consult_result(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        read_only=["manual/**"],
        generated=["generated/**"],
    )
    chosen = [ref for ref in _auto_refs(consulted) if ref["file"] == "auto.md"]
    drift = [ref for ref in _auto_refs(consulted) if ref["file"] == "stale.md"]
    (fix.repo / "stale.md").write_text(
        "Stale changed [doc](docs/old.md).\n",
        encoding="utf-8",
    )

    result = run_act(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        read_only=["manual/**"],
        generated=["generated/**"],
        apply=_apply_string(chosen + drift),
    )
    log = format_action_log(result)

    assert result.exit_code == 1
    for section in ACTION_LOG_SECTIONS:
        assert section in log
    assert "method: git mv" in log
    assert "auto.md [doc](docs/old.md) -> [doc](docs/new.md)" in log
    assert "manual/review.md [doc](../docs/old.md) -> [doc](../docs/new.md)" in log
    assert "generated/config.yaml docs/old.md -> docs/new.md" in log
    assert "reason: drifted" in log
    assert "regenerate" in log
