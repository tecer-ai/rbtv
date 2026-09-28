"""A content-routed meeting must not come back unroutable on its second pass.

`destination_resolver.resolve()` only matches a content route when the JOB carries
a `content-entity` — the pick a model made once, at summarize time, and
`per_meeting_job.py`'s `settle()` call recorded in `outcomes.jsonl`. Nothing about
the meeting's title or participants lets a fresh resolve rediscover that pick, so
`publish_job.py` must carry it forward itself. These tests fail against the code
before that fix (`resolve_job`/`settled_content_entity` did not exist; `run_cycle`
and the `precheck` CLI path called `destination_resolver.resolve()` directly) and
pass after it — evidence pasted in the seat report.
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H           # noqa: E402
import per_meeting_job as PMJ  # noqa: E402
import publish_job as P        # noqa: E402

CONTENT_ROUTING = {
    "config-key": "destination-routing",
    "timezone": "America/Sao_Paulo",
    "tzinfo": ZoneInfo("America/Sao_Paulo"),
    "routes": [
        {"entity": "content-fixture", "match": {}, "content": "a content-routed fixture meeting",
         "destination": {"repo": "alpha-works"}},
    ],
}

JOB = {
    "meeting-key": "mtg-content-fixture",
    "source-set": [
        {"account": "work-a@fixture.invalid", "source": "meet",
         "drive-ref": "drv:file/FIXTURE-content", "title": "teste 2",
         "start-time": "2026-03-11T10:02:00-03:00", "participants": ["Henrique"]},
    ],
}


@pytest.fixture
def world():
    scratch = H.Scratch()
    scratch.repo("alpha-works")
    scratch.checkout = scratch.checkouts / "alpha-works"
    yield scratch
    scratch.clean()


def cycle(world, job=JOB):
    return P.run_cycle(job, config_root=H.CONFIG_ROOT, checkout_root=world.checkouts,
                       state=world.state, transcripts=H.transcripts("meet"),
                       summarize=H.Summarizer("# resumo\n\nfixture body\n",
                                              path="notes/content-fixture-resumo.md"),
                       bus=H.Bus(), routing=CONTENT_ROUTING)


def settle_content_entity(world, meeting_key="mtg-content-fixture", entity="content-fixture"):
    PMJ.append_jsonl(world.state / PMJ.OUTCOMES,
                     {"meeting-key": meeting_key, "outcome": "filed",
                      "content-entity": entity, "at": "2026-09-28T00:00:00Z"})


def test_settled_content_entity_reads_the_latest_matching_row(tmp_path):
    state = tmp_path / "state"
    PMJ.append_jsonl(state / PMJ.OUTCOMES, {"meeting-key": "other", "content-entity": "x"})
    assert P.settled_content_entity(state, "mtg-content-fixture") is None
    PMJ.append_jsonl(state / PMJ.OUTCOMES,
                     {"meeting-key": "mtg-content-fixture", "content-entity": "content-fixture"})
    assert P.settled_content_entity(state, "mtg-content-fixture") == "content-fixture"
    # A later row for the same meeting wins.
    PMJ.append_jsonl(state / PMJ.OUTCOMES,
                     {"meeting-key": "mtg-content-fixture", "content-entity": "resettled"})
    assert P.settled_content_entity(state, "mtg-content-fixture") == "resettled"


def test_resolve_job_uses_the_jobs_own_content_entity_when_present(tmp_path):
    job = {**JOB, "content-entity": "content-fixture"}
    routed = P.resolve_job(job, None, tmp_path / "state", routing=CONTENT_ROUTING)
    assert routed["kind"] == "routed"
    assert routed["destination"]["repo"] == "alpha-works"


def test_resolve_job_is_unroutable_without_a_settled_content_entity(tmp_path):
    routed = P.resolve_job(JOB, None, tmp_path / "state", routing=CONTENT_ROUTING)
    assert routed["kind"] == "unroutable"


def test_resolve_job_carries_forward_a_settled_content_entity(tmp_path):
    state = tmp_path / "state"
    PMJ.append_jsonl(state / PMJ.OUTCOMES,
                     {"meeting-key": "mtg-content-fixture", "content-entity": "content-fixture"})
    routed = P.resolve_job(JOB, None, state, routing=CONTENT_ROUTING)
    assert routed["kind"] == "routed"
    assert routed["destination"]["repo"] == "alpha-works"


def test_a_content_routed_meeting_without_settlement_is_withheld(world):
    result = cycle(world)
    assert result["outcome"] == "withheld-unroutable"


def test_a_content_routed_meeting_files_and_writes_processed_transcripts(world):
    settle_content_entity(world)
    result = cycle(world)
    assert result["outcome"] == "filed"
    assert result["destination"]["repo"] == "alpha-works"
    filed = world.checkout / result["destination"]["path"]
    assert filed.is_file()

    processed = P.read_jsonl(world.state / P.PROCESSED)
    assert any(row["meeting-key"] == "mtg-content-fixture" for row in processed)


def test_a_second_tick_after_publish_would_see_already_done(world):
    """The M1 symptom, proven at its root: once publish has run, precheck alone
    (no fresh summarize) reports `already-done` — the shape a later detection
    tick's `already-done` disposition depends on."""
    settle_content_entity(world)
    cycle(world)

    routed = P.resolve_job(JOB, H.CONFIG_ROOT, world.state, routing=CONTENT_ROUTING)
    assert routed["kind"] == "routed"
    target = {"repo": "alpha-works", "regime": "git", "remote": "origin", "branch": "main"}
    decision = P.precheck(JOB, routed, target, world.checkout, world.state, "")
    assert decision["disposition"] == "already-done"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
