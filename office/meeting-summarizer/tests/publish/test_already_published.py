"""A meeting whose destination bytes already match the fetched remote must
close as PUBLISHED, not FAILED — the M1/M2 defect (check-summarizer round 2).

`_push_via_worktree` (regime "vault") returns `{"pushed": False, "cause":
"nothing of this cycle's own is unpushed"}` when there is nothing to push —
correct information, wrongly read as a failure by `run_cycle()`'s "vault"
publish step whenever this cycle's own `commit()` also made no new commit. It
happened live: the owner had already committed the identical summary bytes
(the meeting was re-summarized, deterministically, to the same text), so the
cycle's own commit was a no-op, and the meeting was parked at `committed` /
`head: null` forever — the tick kept re-emitting it as `new`, and
`processed-transcripts.jsonl` was never written.

These tests fail against the code before the fix (the committed one at
7982f643/fc991b0e) — checked against an isolated scratch copy of the prior
commit's `publish_job.py`, evidence pasted in the seat report — and pass after.
"""

from __future__ import annotations

import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import harness as H     # noqa: E402
import publish_job as P  # noqa: E402

ROUTING = {
    "config-key": "destination-routing",
    "timezone": "America/Sao_Paulo",
    "tzinfo": ZoneInfo("America/Sao_Paulo"),
    "routes": [
        {"entity": "clinic-a", "match": {"participants-any": ["Dora Marques"]},
         "destination": {"repo": "wellbeing-vault",
                         "path-template": "areas/wellbeing/{year}/{date}-already-resumo.md"}},
    ],
}

JOB = {
    "meeting-key": "mtg-already-published",
    "source-set": [
        {"account": "work-a@fixture.invalid", "source": "meet",
         "drive-ref": "drv:file/FIXTURE-already", "title": "sessao",
         "start-time": "2026-03-11T10:02:00-03:00", "participants": ["Dora Marques"]},
    ],
}

SUMMARY_TEXT = "# resumo\n\nmeeting-key: mtg-already-published\n\nsame content every time\n"


@pytest.fixture
def world():
    scratch = H.Scratch()
    scratch.repo("wellbeing-vault")
    scratch.checkout = scratch.checkouts / "wellbeing-vault"
    yield scratch
    scratch.clean()


def _target_paths(world):
    """The exact repo-relative summary AND transcript paths this job renders
    to. Both must already be on the remote for `commit()` to find NOTHING new
    — the cycle writes both every time (`transcript_paths`), so seeding only
    the summary leaves the transcript as a genuinely new, uncommitted file."""
    targets = {"targets": {"wellbeing-vault": {"regime": "vault", "remote": "origin",
                                                "branch": "main"}},
               "discriminator": {"format": "%H%M"}}
    routed = P.resolve_job(JOB, None, world.state, routing=ROUTING)
    token = P.discriminator(JOB, targets, ROUTING)
    summary_path = P.discriminate(routed["destination"]["path"], token, targets)
    transcript_path = P.transcript_paths(summary_path, ["meet"])["meet"]
    return summary_path, transcript_path


def _seed_remote_with_identical_bytes(world):
    """The owner (or a prior cycle) already committed and pushed the EXACT
    summary and transcript text this cycle's fixture summarizer will produce."""
    summary_path, transcript_path = _target_paths(world)
    world.owner_commits("wellbeing-vault", summary_path, SUMMARY_TEXT)
    world.owner_commits("wellbeing-vault", transcript_path, H.transcripts("meet")["meet"])
    return summary_path


def cycle(world):
    return P.run_cycle(JOB, config_root=H.CONFIG_ROOT, checkout_root=world.checkouts,
                       state=world.state, transcripts=H.transcripts("meet"),
                       summarize=H.Summarizer(SUMMARY_TEXT), bus=H.Bus(), routing=ROUTING)


def test_a_meeting_already_matching_the_remote_closes_as_published(world):
    _seed_remote_with_identical_bytes(world)

    result = cycle(world)

    assert result["outcome"] in ("filed", "amended"), result
    assert "already-published" in result["trace"]
    assert result["published"] == {"pushed": True, "via": "already-current"}


def test_it_writes_the_processed_record_so_the_next_tick_sees_already_done(world):
    _seed_remote_with_identical_bytes(world)

    cycle(world)

    processed = P.read_jsonl(world.state / P.PROCESSED)
    assert any(row["meeting-key"] == "mtg-already-published" for row in processed), processed


def test_it_still_reaches_published_stage_in_the_journal(world):
    _seed_remote_with_identical_bytes(world)

    cycle(world)

    stages = [row["stage"] for row in P.journal_rows(world.state, "mtg-already-published")]
    assert "published" in stages
    assert "processed" in stages


def test_a_genuine_push_failure_still_refuses(world):
    """The fix must not swallow a REAL failure: the remote is unreachable and
    this cycle DOES make a fresh commit (nothing pre-seeded on the remote)."""
    world.unreachable("wellbeing-vault")

    result = cycle(world)

    assert result["outcome"] == "failed"
    assert result.get("retryable") is True
    processed = P.read_jsonl(world.state / P.PROCESSED)
    assert not any(row["meeting-key"] == "mtg-already-published" for row in processed)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
