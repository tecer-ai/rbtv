"""Detection reads the SAME processed-transcripts file publish writes — by
construction, with no flag and no call order needed (check-summarizer round 4,
M1; the round-3 attempt made this reachable only via `materialize_config.py
--state`, a flag the model's own turn had to remember to pass, in the right
order, before the tick — correctly judged "a prompt, not a fix").

Live defect: `detection_cycle.py`'s processed-transcript store resolved, by
default, to `<config-dir>/stores/processed-transcripts.jsonl` (`resolve_store`'s
generic fallback) while `publish_job.py` writes to
`<state>/processed-transcripts.jsonl` (`publish_job.py:74,735`) — two different
files, whatever order any tool ran in. `detection_cycle.processed_store_path`
now derives `<state>` directly from `config_dir`'s FIXED position in the agent
home (`config_dir.parent / "state"`) — no `stores.json`, no prior materialize
call, no flag: the very first `tick --config-dir <home>/config` of a turn
already reads the right file. These tests call `tick --config-dir` with
NOTHING run before it in the same test (no materialize call at all) and use
the REAL row shape `publish_job.py` writes, not a hand-typed schema guess.
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

import detection_cycle as dc  # noqa: E402
import publish_job as P        # noqa: E402


@pytest.fixture
def agent_home(tmp_path: Path) -> Path:
    """The live layout: <home>/config/ and <home>/state/, siblings, exactly as
    the agent has them — `config/` is never touched by materialize_config.py
    in these tests, proving the fix needs no prior call of any kind."""
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


def test_no_config_root_or_stores_json_exists_and_the_store_still_resolves(agent_home):
    """Sanity: the fixture's config/ carries no stores.json at all — the exact
    live condition (round 4's evidence: "stores.json did not exist at tick
    time") — and `load_env` must not refuse or need one."""
    assert not (agent_home / "config" / "stores.json").exists()
    env = dc.load_env(agent_home / "config")
    assert env.stores[dc.PROCESSED_ENTRY] == agent_home / "state" / "processed-transcripts.jsonl"


def test_detection_reads_publishs_file_with_zero_prior_setup(agent_home):
    """The exact scenario round 4 demanded: NO materialize call (flagged or
    not) runs before this — `load_env`/`tick` is the very first thing called,
    exactly as a turn's first bash command was live."""
    state = agent_home / "state"
    _publish_a_processed_record(state, "mtg-8ab4a27f")
    _publish_a_processed_record(state, "mtg-c650cbeb")

    env = dc.load_env(agent_home / "config")

    processed = dc.read_processed(env)
    assert {row["meeting-key"] for row in processed} == {"mtg-8ab4a27f", "mtg-c650cbeb"}


def test_job_for_reports_already_done_for_both_live_meetings_with_no_prior_setup(agent_home):
    """The exact live symptom, at the decision point `job_for` makes, for BOTH
    meetings named in every round's evidence — proven with nothing run first."""
    state = agent_home / "state"
    _publish_a_processed_record(state, "mtg-8ab4a27f", source="meet")
    _publish_a_processed_record(state, "mtg-c650cbeb", source="meet")

    env = dc.load_env(agent_home / "config")
    processed = dc.read_processed(env)

    for key in ("mtg-8ab4a27f", "mtg-c650cbeb"):
        entry = {"meeting-key": key,
                "source-set": [{"account": "tecer", "source": "meet",
                                "drive-ref": f"drv:file/{key}"}]}
        job = dc.job_for(entry, processed)
        assert job["disposition"] == "already-done", (key, job)


def test_a_stores_json_override_still_wins_when_one_is_declared(agent_home):
    """The generic config-key redirect stays available for a deployment that
    genuinely needs a different location — it is not removed, only no longer
    the ONLY way to reach the right default."""
    config = agent_home / "config"
    elsewhere = agent_home / "elsewhere-processed.jsonl"
    (config / "stores.json").write_text(
        json.dumps({"processed-transcripts": str(elsewhere)}), encoding="utf-8")

    env = dc.load_env(config)

    assert env.stores[dc.PROCESSED_ENTRY] == elsewhere


def test_the_default_is_a_sibling_of_config_dir_not_nested_under_it(agent_home):
    """The bug's exact shape: a naive fix that reused `resolve_store`'s
    group/leaf nesting would land at `state/stores/processed-transcripts.jsonl`,
    not `state/processed-transcripts.jsonl` — a THIRD file, matching neither
    tool. Pin the literal path `publish_job.PROCESSED` actually uses."""
    env = dc.load_env(agent_home / "config")
    assert env.stores[dc.PROCESSED_ENTRY].name == P.PROCESSED
    assert env.stores[dc.PROCESSED_ENTRY].parent == agent_home / "state"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
