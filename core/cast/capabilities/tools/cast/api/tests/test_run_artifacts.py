"""Unit tests for the runner's artifact/structured-output writing helper.

NO network. NO subprocess, NO provider call. Drives the extracted helper
`run.write_artifacts(...)` directly with a fake Response. Covers spec
test-plan items 7-9.
"""
import json

import pytest

import run
from clients.base import Artifact, Response


def make_response(artifacts=None, structured_result=None, content="narration"):
    return Response(
        content=content,
        artifacts=artifacts,
        structured_result=structured_result,
        raw_response={"task_id": "t", "artifact_errors": []},
    )


# --------------------------------------------------------------------------
# Test 7 — runner writes artifacts + structured output
# --------------------------------------------------------------------------
def test_runner_writes_artifacts_and_structured(tmp_path):
    artifacts = [
        Artifact(filename="report.pdf", content=b"PDF-BYTES",
                 content_type="application/pdf", source_url="u1"),
        Artifact(filename="chart.png", content=b"PNG-BYTES",
                 content_type="image/png", source_url="u2"),
    ]
    structured = {"success": True, "value": {"answer": "42"}, "error": None}
    resp = make_response(artifacts=artifacts, structured_result=structured)

    landed = []
    validation = {}
    concerns = []
    run.write_artifacts(resp, str(tmp_path), landed, validation, concerns)

    # both artifact files written with bytes intact
    assert (tmp_path / "report.pdf").read_bytes() == b"PDF-BYTES"
    assert (tmp_path / "chart.png").read_bytes() == b"PNG-BYTES"
    # structured output written
    written = json.loads((tmp_path / "structured-output.json").read_text(encoding="utf-8"))
    assert written == structured
    # all appended to landed
    assert "report.pdf" in landed
    assert "chart.png" in landed
    assert "structured-output.json" in landed
    # artifact_count surfaced
    assert validation["artifact_count"] == 2


# --------------------------------------------------------------------------
# Test 8 — runner name-collision dedup
# --------------------------------------------------------------------------
def test_runner_name_collision_dedup(tmp_path):
    # return.json already reserved (runner writes it last); two artifacts share
    # a name, and one collides with return.json.
    (tmp_path / "return.json").write_text("{}", encoding="utf-8")
    artifacts = [
        Artifact(filename="data.bin", content=b"AAA", content_type=None, source_url="u1"),
        Artifact(filename="data.bin", content=b"BBB", content_type=None, source_url="u2"),
        Artifact(filename="return.json", content=b"CCC", content_type=None, source_url="u3"),
    ]
    resp = make_response(artifacts=artifacts, structured_result=None)

    landed = ["return.json"]
    validation = {}
    concerns = []
    run.write_artifacts(resp, str(tmp_path), landed, validation, concerns)

    # return.json must NOT be clobbered by the artifact
    assert (tmp_path / "return.json").read_text(encoding="utf-8") == "{}"
    # all three artifact byte-blobs landed under unique on-disk names
    written_blobs = []
    for name in landed:
        p = tmp_path / name
        if name == "return.json":
            continue
        written_blobs.append(p.read_bytes())
    assert b"AAA" in written_blobs
    assert b"BBB" in written_blobs
    assert b"CCC" in written_blobs
    # no two artifacts share an on-disk name; none equals return.json
    artifact_names = [n for n in landed if n != "return.json"]
    assert len(artifact_names) == len(set(artifact_names))
    assert "return.json" not in artifact_names
    assert validation["artifact_count"] == 3


# --------------------------------------------------------------------------
# Test 9 — runner regression: raw-dump path untouched (no artifacts)
# --------------------------------------------------------------------------
def test_runner_raw_dump_unchanged_when_no_artifacts(tmp_path):
    # Simulate the state AFTER the existing raw-dump branch ran:
    # raw-output.md written, landed=["raw-output.md"], status DONE_WITH_NOTES.
    (tmp_path / "raw-output.md").write_text("the model narration", encoding="utf-8")
    resp = make_response(artifacts=None, structured_result=None)

    landed = ["raw-output.md"]
    validation = {"file_count": 1}
    concerns = ["model did not return the {files:...} envelope"]
    run.write_artifacts(resp, str(tmp_path), landed, validation, concerns)

    # raw-output.md untouched, landed unchanged, no structured file created
    assert (tmp_path / "raw-output.md").read_text(encoding="utf-8") == "the model narration"
    assert landed == ["raw-output.md"]
    assert not (tmp_path / "structured-output.json").exists()
    # artifact_count is 0 (helper sets it even when nothing to write)
    assert validation.get("artifact_count", 0) == 0
