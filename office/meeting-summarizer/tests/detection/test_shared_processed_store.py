"""Detection and publish must read/write the SAME processed-transcripts file
(check-summarizer round 3, M1).

Live defect: `detection_cycle.py`'s processed-transcript store resolves, by
default, to `<config-dir>/stores/processed-transcripts.jsonl` (`resolve_store`'s
fallback, `detection_cycle.py:170-190`) while `publish_job.py` writes to
`<state>/processed-transcripts.jsonl` (`publish_job.py:74,735`) — two different
files. Detection therefore always saw zero processed records for meetings
publish had already filed, and kept re-emitting them as `new` forever.

`materialize_config.py --state <state>` (this resume's fix) writes
`<config-root>/stores.json` naming the SAME file publish already uses — the
config-key redirect `resolve_store` already supported, just never pointed
anywhere. These tests use the REAL two-directory layout (a `config/` and a
`state/` the agent actually has) and the REAL row shape `publish_job.py`
writes, not a hand-typed single path.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]
TOOLS = WORKFLOW / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

FIXTURES = HERE / "fixtures"

import detection_cycle as dc      # noqa: E402
import materialize_config as M    # noqa: E402
import publish_job as P           # noqa: E402


@pytest.fixture
def agent_home(tmp_path: Path) -> Path:
    """The live layout: <home>/config/ (materialized) and <home>/state/ (durable)."""
    home = tmp_path / "agent-home"
    config = home / "config"
    config.mkdir(parents=True)
    for name in ("destination-routing.json", "sources.json", "summarize.json"):
        shutil.copyfile(FIXTURES / "config" / name, config / name)
    (home / "state").mkdir(parents=True)
    return home


def _publish_a_processed_record(state: Path, meeting_key: str, source: str = "meet") -> None:
    """The EXACT row shape publish_job.py's run_cycle() appends — not a
    hand-typed guess at the schema."""
    P.append_jsonl(state / P.PROCESSED, {
        "transcript-ref": f"drv:file/{meeting_key}", "account": "tecer", "source": source,
        "meeting-key": meeting_key, "processed-at": "2026-09-28T09:00:00Z",
        "summary": {"repo": "second-brain", "path": f"1-projects/ignite-0.2/meetings/{meeting_key}.md"},
        "coverage": [source],
    })


def test_detections_default_store_and_publishs_store_are_different_files_by_default(agent_home):
    """Baseline, proving the bug exists absent the redirect (sanity: if this
    ever fails, the two tools' defaults converged on their own and the fix
    below is testing something already true)."""
    env = dc.load_env(agent_home / "config")
    detection_path = env.stores[dc.PROCESSED_ENTRY]
    publish_path = agent_home / "state" / P.PROCESSED
    assert detection_path != publish_path


def test_after_materialize_with_state_detection_reads_publishs_own_file(agent_home):
    config = agent_home / "config"
    state = agent_home / "state"
    _publish_a_processed_record(state, "mtg-8ab4a27f")
    _publish_a_processed_record(state, "mtg-c650cbeb")

    M.write_stores_redirect(config, state)

    env = dc.load_env(config)
    assert env.stores[dc.PROCESSED_ENTRY] == state / "processed-transcripts.jsonl"
    processed = dc.read_processed(env)
    assert {row["meeting-key"] for row in processed} == {"mtg-8ab4a27f", "mtg-c650cbeb"}


def test_job_for_reports_already_done_once_the_redirect_is_in_place(agent_home):
    """The exact live symptom, proven at the decision point `job_for` makes:
    a meeting with a published, matching-coverage row must NOT come back
    `new` — that disposition is what drove the tick to re-emit it forever."""
    config = agent_home / "config"
    state = agent_home / "state"
    _publish_a_processed_record(state, "mtg-8ab4a27f", source="meet")
    M.write_stores_redirect(config, state)

    env = dc.load_env(config)
    processed = dc.read_processed(env)
    entry = {"meeting-key": "mtg-8ab4a27f",
            "source-set": [{"account": "tecer", "source": "meet",
                            "drive-ref": "drv:file/mtg-8ab4a27f"}]}

    job = dc.job_for(entry, processed)

    assert job["disposition"] == "already-done"


def test_the_redirect_survives_a_fresh_materialize_every_cycle(agent_home):
    """`stores.json` is rebuilt, not left stale, on every cycle — same
    unconditional-overwrite rule as every other file under config/."""
    config = agent_home / "config"
    state = agent_home / "state"
    settings = {"sources": {"accounts": ["tecer"]}}
    M.materialize(settings, config)
    M.write_stores_redirect(config, state)

    _publish_a_processed_record(state, "mtg-8ab4a27f")
    # A later cycle re-materializes; the redirect must still be there, unmoved.
    M.materialize(settings, config)
    M.write_stores_redirect(config, state)

    env = dc.load_env(config)
    assert {row["meeting-key"] for row in dc.read_processed(env)} == {"mtg-8ab4a27f"}


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
