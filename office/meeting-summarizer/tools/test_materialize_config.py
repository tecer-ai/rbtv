"""An edit to settings.json must reach the tools on the very next cycle.

The bug this guards: materialization gated to "first cycle only" left
`config/destination-routing.json` stale after the owner edited `settings.json` —
two copies existed and the second, unwritten one is what the tools kept reading.
`materialize_config.py` has no such gate; every call overwrites. These tests prove
that property directly, independent of which turn calls it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import materialize_config as M  # noqa: E402


def test_materialize_writes_one_file_per_top_level_key(tmp_path):
    settings = {
        "sources": {"accounts": ["a"]},
        "destination-routing": {"timezone": "America/Sao_Paulo"},
    }
    config_root = tmp_path / "config"

    written = M.materialize(settings, config_root)

    assert sorted(Path(p).name for p in written) == ["destination-routing.json", "sources.json"]
    assert json.loads((config_root / "sources.json").read_text(encoding="utf-8")) == {"accounts": ["a"]}
    assert json.loads((config_root / "destination-routing.json").read_text(encoding="utf-8")) == {
        "timezone": "America/Sao_Paulo"}


def test_a_comment_key_is_never_materialized(tmp_path):
    written = M.materialize({"_this-file": ["prose"], "runtime": {"checkout-root": "/x"}},
                            tmp_path / "config")
    assert len(written) == 1
    assert not (tmp_path / "config" / "_this-file.json").exists()


def test_an_edit_to_settings_json_overwrites_the_stale_config_file(tmp_path):
    """The exact bug: settings.json changes, config/ must NOT keep the old value."""
    config_root = tmp_path / "config"
    M.materialize({"destination-routing": {"timezone": "America/Sao_Paulo", "routes": []}},
                  config_root)
    before = json.loads((config_root / "destination-routing.json").read_text(encoding="utf-8"))
    assert before["routes"] == []

    # The owner edits settings.json — a route is added. A later cycle's
    # materialize() call, run unconditionally, must replace the stale file.
    M.materialize({"destination-routing": {"timezone": "America/Sao_Paulo",
                                            "routes": [{"entity": "new-route"}]}},
                  config_root)
    after = json.loads((config_root / "destination-routing.json").read_text(encoding="utf-8"))
    assert after["routes"] == [{"entity": "new-route"}]


def test_a_file_belonging_to_a_removed_key_is_left_alone(tmp_path):
    """materialize() mirrors what settings.json currently declares; it never
    guesses what to delete."""
    config_root = tmp_path / "config"
    M.materialize({"runtime": {"checkout-root": "/old"}, "summarize": {"a": 1}}, config_root)
    assert (config_root / "summarize.json").is_file()
    M.materialize({"runtime": {"checkout-root": "/new"}}, config_root)  # summarize dropped
    assert (config_root / "summarize.json").is_file()  # not deleted
    assert json.loads((config_root / "runtime.json").read_text(encoding="utf-8")) == {"checkout-root": "/new"}


def test_cli_refuses_a_missing_settings_file(tmp_path):
    with pytest.raises(SystemExit) as excinfo:
        M.main(["--settings", str(tmp_path / "missing.json"), "--config-root", str(tmp_path)])
    assert excinfo.value.code == M.EXIT_REFUSED


def test_cli_end_to_end(tmp_path, capsys):
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"sources": {"accounts": ["tecer"]}}), encoding="utf-8")
    config_root = tmp_path / "config"

    exit_code = M.main(["--settings", str(settings), "--config-root", str(config_root)])

    assert exit_code == M.EXIT_OK
    assert json.loads((config_root / "sources.json").read_text(encoding="utf-8")) == {"accounts": ["tecer"]}
    printed = json.loads(capsys.readouterr().out)
    assert printed["written"] == [str(config_root / "sources.json")]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
