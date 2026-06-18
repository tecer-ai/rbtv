"""Tests for consult assembly and the frozen JSON envelope."""

from __future__ import annotations

import json
import subprocess
import sys

import safe_move.consult as consult_module
from safe_move import classify
from safe_move.consult import build_consult_result, compute_git_move_method


TOP_LEVEL_KEYS = {"git_move_method", "references", "warnings", "folder_cascade"}
REFERENCE_KEYS = {
    "id",
    "file",
    "line",
    "match",
    "context",
    "syntax",
    "proposed",
    "class",
    "hash",
    "offset",
}
WARNING_KEYS = {"kind", "message", "file", "ref_id"}


def assert_reference_contract(ref):
    assert set(ref) == REFERENCE_KEYS
    assert isinstance(ref["id"], str)
    assert isinstance(ref["file"], str)
    assert isinstance(ref["line"], int)
    assert isinstance(ref["match"], str)
    assert isinstance(ref["context"], str)
    assert isinstance(ref["syntax"], str)
    assert isinstance(ref["proposed"], str)
    assert isinstance(ref["class"], str)
    assert isinstance(ref["hash"], str)
    assert isinstance(ref["offset"], int)


def assert_warning_contract(warning):
    assert set(warning) == WARNING_KEYS
    assert isinstance(warning["kind"], str)
    assert isinstance(warning["message"], str)
    assert warning["file"] is None or isinstance(warning["file"], str)
    assert warning["ref_id"] is None or isinstance(warning["ref_id"], str)


def test_consult_emits_exact_contract_shape_with_warnings_and_git_method(repo_builder):
    fix = repo_builder(
        "consult-contract",
        {
            "docs/old.md": "old\n",
            "note.md": "See [[old]] and [old](docs/old.md).\n",
            "readonly/page.md": "See [[old]].\n",
            "generated/config.yaml": "target: docs/old.md\n",
            "foreign/page.md": "See [[old]].\n",
        },
        tracked=[
            "docs/old.md",
            "note.md",
            "readonly/page.md",
            "generated/config.yaml",
            "foreign/page.md",
        ],
    )
    subprocess.run(["git", "init"], cwd=fix.repo / "foreign", check=True, capture_output=True)

    result = build_consult_result(
        "docs/old.md",
        "docs/new.md",
        scope_root=fix.repo,
        read_only=["readonly/**"],
        generated=["generated/**"],
    )

    assert set(result) == TOP_LEVEL_KEYS
    assert result["git_move_method"] == "git mv"
    assert result["folder_cascade"] is None
    assert isinstance(result["references"], list)
    assert result["references"]
    for ref in result["references"]:
        assert_reference_contract(ref)
    assert all(ref["id"] == f"ref-{index:04d}" for index, ref in enumerate(result["references"], 1))
    assert all(isinstance(ref["hash"], str) and len(ref["hash"]) == 64 for ref in result["references"])
    for warning in result["warnings"]:
        assert_warning_contract(warning)

    by_file = {ref["file"]: ref for ref in result["references"]}
    assert by_file["note.md"]["class"] == classify.CLASS_AUTO
    assert by_file["readonly/page.md"]["class"] == classify.CLASS_SURFACE
    assert by_file["generated/config.yaml"]["class"] == classify.CLASS_SURFACE
    assert by_file["foreign/page.md"]["class"] == classify.CLASS_SURFACE

    warning_kinds = {warning["kind"] for warning in result["warnings"]}
    assert "regenerate" in warning_kinds
    assert "cross-project" in warning_kinds


def test_consult_cli_prints_parseable_json(repo_builder):
    fix = repo_builder(
        "consult-cli",
        {
            "old.md": "old\n",
            "note.md": "See [[old]].\n",
        },
        tracked=["old.md", "note.md"],
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "safe_move",
            "consult",
            "old.md",
            "new.md",
            "--scope-root",
            str(fix.repo),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == TOP_LEVEL_KEYS
    assert payload["references"][0]["id"] == "ref-0001"
    assert payload["references"][0]["match"] == "[[old]]"
    assert payload["references"][0]["proposed"] == "[[new]]"


def test_empty_or_none_proposed_forces_surface(repo_builder, monkeypatch):
    fix = repo_builder(
        "consult-none-proposed",
        {
            "old.md": "old\n",
            "note.md": "See [[old]].\n",
        },
    )
    monkeypatch.setattr(consult_module.replace, "compute_proposed", lambda *args, **kwargs: None)

    result = build_consult_result("old.md", "new.md", scope_root=fix.repo)

    assert result["references"][0]["class"] == classify.CLASS_SURFACE
    assert result["references"][0]["proposed"] == ""


def test_cross_repo_move_uses_mv_and_warns_history_loss(repo_builder):
    source = repo_builder("consult-source-repo", {"old.md": "old\n"}, tracked=["old.md"])
    dest = repo_builder("consult-dest-repo", {"keep.md": "keep\n"}, tracked=["keep.md"])

    method, warnings = compute_git_move_method(
        source.repo / "old.md",
        dest.repo / "new.md",
        source.repo,
    )

    assert method == "mv"
    assert [warning["kind"] for warning in warnings] == ["history-loss"]


def test_untracked_same_repo_move_uses_plain_mv(repo_builder):
    fix = repo_builder("consult-untracked", {"old.md": "old\n"})

    method, warnings = compute_git_move_method(
        fix.repo / "old.md",
        fix.repo / "new.md",
        fix.repo,
    )

    assert method == "mv"
    assert warnings == []
