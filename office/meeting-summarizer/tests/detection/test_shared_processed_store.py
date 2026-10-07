"""Where the detection tool keeps and finds its records.

Detection reads the SAME processed-transcripts file `publish_job.py` writes: the
agent's live data, `<agent folder>/state/processed-transcripts.jsonl`, found from
`RBTV_AGENT_HOME`. Its own stores are operational data, written under the
installation's `.rbtv/runtime/meeting-summarizer/`, which the first write creates.
These tests use the REAL row shape `publish_job.py` writes, not a hand-typed
schema guess.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import detection_cycle as dc  # noqa: E402
import publish_job as P        # noqa: E402
import source_adapter as sa    # noqa: E402

from conftest import FIRST_TICK, load  # noqa: E402


def _publish_a_processed_record(state: Path, meeting_key: str, source: str = "meet") -> None:
    """The EXACT row shape publish_job.py's run_cycle() appends — not a
    hand-typed guess at the schema."""
    P.append_jsonl(state / P.PROCESSED, {
        "transcript-ref": f"drv:file/{meeting_key}", "account": "tecer", "source": source,
        "meeting-key": meeting_key, "processed-at": "2026-09-28T09:00:00Z",
        "summary": {"repo": "second-brain", "path": f"1-projects/ignite-0.2/meetings/{meeting_key}.md"},
        "coverage": [source],
    })


def test_the_processed_record_is_the_file_publish_writes_in_the_agents_state(config_dir, agent_home):
    env = dc.load_env(config_dir)
    assert env.stores[dc.PROCESSED_ENTRY] == agent_home / "state" / P.PROCESSED


def test_detection_reads_what_publish_wrote(config_dir, agent_home):
    state = agent_home / "state"
    _publish_a_processed_record(state, "mtg-8ab4a27f")
    _publish_a_processed_record(state, "mtg-c650cbeb")

    processed = dc.read_processed(dc.load_env(config_dir))

    assert {row["meeting-key"] for row in processed} == {"mtg-8ab4a27f", "mtg-c650cbeb"}
    for key in ("mtg-8ab4a27f", "mtg-c650cbeb"):
        entry = {"meeting-key": key,
                 "source-set": [{"account": "tecer", "source": "meet",
                                 "drive-ref": f"drv:file/{key}"}]}
        assert dc.job_for(entry, processed)["disposition"] == "already-done", key


def test_without_the_agent_folder_the_cycle_is_refused(config_dir, monkeypatch):
    """No agent folder, no processed record: a tick on an empty one would re-emit
    every filed meeting as `new`."""
    monkeypatch.delenv(dc.AGENT_HOME_ENV)
    with pytest.raises(dc.Refused, match=dc.AGENT_HOME_ENV):
        dc.load_env(config_dir)


def test_the_first_tick_creates_the_runtime_folder_and_keeps_its_stores_there(
        config_dir, agent_home, tmp_path):
    """A first run in an installation with no `.rbtv/runtime/` creates
    `.rbtv/runtime/meeting-summarizer/`; nothing lands in the config folder or
    the agent folder."""
    runtime = tmp_path / ".rbtv" / "runtime" / "meeting-summarizer"
    assert not (tmp_path / ".rbtv" / "runtime").exists()
    before = sorted(p.name for p in config_dir.iterdir())
    _publish_a_processed_record(agent_home / "state", "mtg-8ab4a27f")
    listing = load("drive-listing.json")
    env = dc.load_env(config_dir, source_map=load("source-map.json"),
                      account_emails=listing["account-emails"])

    result = dc.run_tick(env, FIRST_TICK, sa.FixtureDriveDriver(listing))

    assert result.watermark_advanced
    assert (runtime / "stores" / "poll-watermark.json").is_file()
    assert (runtime / "stores" / "detected-meetings.jsonl").is_file()
    for key in (dc.WATERMARK_ENTRY, dc.MEETINGS_KEY, dc.ATTEMPTS_KEY, dc.CLAIMS_KEY):
        assert env.stores[key].is_relative_to(runtime), key
    assert sorted(p.name for p in config_dir.iterdir()) == before
    assert sorted(p.name for p in (agent_home / "state").iterdir()) == [P.PROCESSED]
    assert len(dc.read_processed(env)) == 1


def test_a_config_home_outside_an_installation_names_no_runtime_folder(tmp_path, agent_home):
    """Operational data is never written beside an arbitrary folder."""
    loose = tmp_path / "loose-config"
    loose.mkdir()
    with pytest.raises(SystemExit) as refused:
        dc.resolve_store(dc.MEETINGS_KEY, loose, ".jsonl")
    assert refused.value.code == dc.EXIT_REFUSED
