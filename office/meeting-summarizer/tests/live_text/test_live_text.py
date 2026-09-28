"""The live text download and the binding handoff, with a fake Google CLI."""

import sys
import json
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))

import artifact_bindings  # noqa: E402
import artifact_reader  # noqa: E402
import source_adapter  # noqa: E402


FAKE_GTOOLS = '''import json, pathlib, sys
args = sys.argv[1:]
assert "--format" in args and args[args.index("--format") + 1] == "txt"
assert "--json" in args
ref = args[args.index("--file-id") + 1]
path = pathlib.Path(args[args.index("--output") + 1])
path.write_text("title: EXAMPLE sync\\nstart: 2026-08-20T10:00:00-03:00\\n", encoding="utf-8")
print(json.dumps({"path": str(path), "name": "EXAMPLE sync - Transcript",
                  "mimeType": "text/plain"}))
'''


def test_live_driver_reads_the_downloaded_text(tmp_path):
    cli = tmp_path / "gtools.py"
    cli.write_text(FAKE_GTOOLS, encoding="utf-8")
    driver = source_adapter.GtoolsDriveDriver(cli)

    head = driver.read_record("EXAMPLE", {"id": "drv:file/EXAMPLE-a"})

    assert head["title"] == "EXAMPLE sync"
    assert head["start-time"] == "2026-08-20T10:00:00-03:00"


def test_binding_producer_downloads_once_per_ref_and_reader_gets_text(tmp_path):
    cli = tmp_path / "gtools.py"
    cli.write_text(FAKE_GTOOLS, encoding="utf-8")
    ref = "drv:file/EXAMPLE-a"
    record = {"drive-ref": ref, "account": "owner@EXAMPLE.test", "source": "meet"}
    jobs = [{"source-set": [record]}, {"source-set": [record]}]

    table = artifact_bindings.build(
        jobs, source_adapter.GtoolsDriveDriver(cli),
        {"owner@EXAMPLE.test": "EXAMPLE"}, tmp_path / "downloads")

    assert list(table["artifacts"]) == [ref]
    binding = table["artifacts"][ref]
    assert binding["name"] == "EXAMPLE sync - Transcript"
    assert binding["media-type"] == "text/plain"
    read = artifact_reader.read_artifact(ref, binding, {"transcript": {"name-contains": ["Transcript"]}})
    assert read["legible"] and read["artifact-kind"] == "transcript"
    assert "EXAMPLE sync" in read["text"]


def test_unknown_account_cannot_produce_a_partial_binding_table(tmp_path):
    jobs = [{"source-set": [{"drive-ref": "drv:file/EXAMPLE-a",
                             "account": "missing@EXAMPLE.test"}]}]
    with pytest.raises(ValueError, match="no watched account key"):
        artifact_bindings.build(jobs, None, {}, tmp_path / "downloads")
    assert not (tmp_path / "downloads" / "bindings.json").exists()


def test_cli_binds_detection_jobs_from_the_declared_account_map(tmp_path, capsys):
    cli = tmp_path / "gtools.py"
    cli.write_text(FAKE_GTOOLS, encoding="utf-8")
    (tmp_path / "config.yaml").write_text(
        "accounts:\n  EXAMPLE:\n    email: owner@EXAMPLE.test\n", encoding="utf-8")
    config = tmp_path / "config"
    config.mkdir()
    (config / "sources.json").write_text(json.dumps(
        {"gtools-path": str(cli), "accounts": ["EXAMPLE"]}), encoding="utf-8")
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps({"jobs": [{"source-set": [
        {"drive-ref": "drv:file/EXAMPLE-a", "account": "owner@EXAMPLE.test"}]}]}),
        encoding="utf-8")
    out = tmp_path / "artifacts"

    assert artifact_bindings.main(["--jobs", str(jobs), "--out-dir", str(out),
                                   "--config-dir", str(config)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["artifacts"] == 1
    assert (out / "bindings.json").is_file()
