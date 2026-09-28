"""The deterministic half of m6, asserted without invoking a summarizer.

run_cases.py runs the six fixture cases end to end, summarizer included, and is
the milestone's evidence. This suite holds the rules those cases rest on — the
reader's two verdicts, the Meet-over-Tactiq rule utterance by utterance, and the
write counter's own discriminating power — so a regression in any of them is
caught in under a second rather than after six model invocations.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import artifact_reader as reader          # noqa: E402
import per_meeting_job                    # noqa: E402
import transcript_merge as merger         # noqa: E402
from harness import FIXTURES, WriteCount   # noqa: E402

SEAMS = HERE.parent.parent / "seams"
CONFIG = json.loads((FIXTURES / "config" / "summarize.json").read_text("utf-8"))
MARKERS = CONFIG["artifact-kinds"]
BINDING = json.loads((FIXTURES / "artifacts" / "binding.json").read_text("utf-8"))["artifacts"]


def bind(ref: str) -> dict:
    entry = dict(BINDING[ref])
    entry["location"] = entry["location"].replace("FIXTURES/artifacts",
                                                  str(FIXTURES / "artifacts"))
    return entry


def read(ref: str) -> dict:
    return reader.read_artifact(ref, bind(ref), MARKERS)


def text_of(name: str) -> str:
    return (FIXTURES / "artifacts" / name).read_text(encoding="utf-8")


# ------------------------------------------------------ the reader's verdicts
@pytest.mark.parametrize("ref,kind", [
    ("drv:file/FIXTURE-a-meet", "transcript"),
    ("drv:file/FIXTURE-a-tactiq", "transcript"),
    ("drv:file/FIXTURE-a-gemini", "meeting-notes"),
    ("drv:file/FIXTURE-b-tactiq", "transcript"),
    ("drv:file/FIXTURE-c-gemini", "meeting-notes"),
    ("drv:file/FIXTURE-f-meet", "transcript"),
])
def test_artifact_kind(ref, kind):
    assert read(ref)["artifact-kind"] == kind


def test_kind_from_the_display_name_when_frontmatter_is_silent():
    """case (c)'s notes file declares no type; only its NAME says what it is."""
    assert "type:" not in text_of("case-c-gemini.md").split("\n", 1)[0]
    assert read("drv:file/FIXTURE-c-gemini")["artifact-kind"] == "meeting-notes"


def test_an_artifact_nothing_marks_is_undetermined_never_a_transcript(tmp_path):
    blank = tmp_path / "mystery.bin"
    blank.write_text("uma linha solta sem marcacao nenhuma\n", encoding="utf-8")
    verdict = reader.read_artifact("drv:file/X", {"location": str(blank), "name": "arquivo"},
                                   MARKERS)
    assert verdict["artifact-kind"] == "undetermined"


def test_bytes_that_are_not_text_read_as_illegible(tmp_path):
    broken = tmp_path / "broken.bin"
    broken.write_bytes(b"\xff\xfe\x00\x01not utf-8")
    verdict = reader.read_artifact("drv:file/Y", {"location": str(broken), "name": "x"}, MARKERS)
    assert verdict["legible"] is False and verdict["illegible-reason"]


def test_every_read_result_validates_against_the_new_seam():
    for ref in BINDING:
        assert reader.validate(read(ref), SEAMS) == []


def test_a_read_result_missing_a_required_property_is_refused_by_the_seam():
    mutant = {k: v for k, v in read("drv:file/FIXTURE-a-meet").items() if k != "sha256"}
    assert reader.validate(mutant, SEAMS) != []


# --------------------------------------------- clause 5, utterance by utterance
MEET_OVER_TACTIQ = [
    ("quarenta e oito", "oitenta e quatro"),
    ("dezenove", "vinte e nove"),
    ("EXAMPLE-Ledgerly", "Legerly"),
    ("reduzir", "ampliar"),
    ("Kappa-7", "Kappa-sete"),
]


def test_merge_counts_case_a():
    result = merger.merge({"meet": text_of("case-a-meet.md"),
                           "tactiq": text_of("case-a-tactiq.md")})
    assert result["compared"] == 16
    assert result["differing"] == 5
    assert result["meet-wins"] == result["differing"]
    assert result["tactiq-only"] == 1      # coverage Meet lacks is carried, never dropped
    assert result["meet-only"] == 0


@pytest.mark.parametrize("meet_wording,tactiq_wording", MEET_OVER_TACTIQ)
def test_meet_wording_wins_each_differing_utterance(meet_wording, tactiq_wording):
    merged = merger.merge({"meet": text_of("case-a-meet.md"),
                           "tactiq": text_of("case-a-tactiq.md")})["text"]
    assert meet_wording in merged
    assert tactiq_wording not in merged


def test_the_rule_is_not_vacuous_the_other_way_round():
    """With the two sources swapped, every assertion above must flip."""
    swapped = merger.merge({"meet": text_of("case-a-tactiq.md"),
                            "tactiq": text_of("case-a-meet.md")})["text"]
    for meet_wording, tactiq_wording in MEET_OVER_TACTIQ:
        assert tactiq_wording in swapped and meet_wording not in swapped


def test_a_single_source_merges_to_itself():
    only = text_of("case-b-tactiq.md")
    result = merger.merge({"tactiq": only})
    assert result["text"] == only and result["compared"] == 0


def test_zero_utterance_transcript_merges_to_zero():
    assert merger.merge({"meet": text_of("case-f-meet.md")})["utterances"] == 0


# ------------------------------------------------- the counter, and the config
def test_the_write_counter_counts_a_real_write(tmp_path):
    counted = tmp_path / "counted"
    counted.mkdir()
    counter = WriteCount({"counted": counted})
    with counter:
        (counted / "a.txt").write_text("x", encoding="utf-8")
    assert counter.counts["counted"] == 1


def test_the_write_counter_does_not_count_a_read(tmp_path):
    counted = tmp_path / "counted"
    counted.mkdir()
    (counted / "a.txt").write_text("x", encoding="utf-8")
    counter = WriteCount({"counted": counted})
    with counter:
        (counted / "a.txt").read_text(encoding="utf-8")
    assert sum(counter.counts.values()) == 0


def test_the_counter_buckets_a_write_outside_every_declared_root(tmp_path):
    counter = WriteCount({"counted": tmp_path / "counted"})
    with counter:
        (tmp_path / "stray.txt").write_text("x", encoding="utf-8")
    assert counter.counts["elsewhere"] == 1


def test_each_entity_is_bound_to_its_own_summarizer():
    bindings = CONFIG["skill-bindings"]
    therapy = per_meeting_job.skill_for("clinic-fix", bindings)
    meeting = per_meeting_job.skill_for("alpha", bindings)
    assert therapy != meeting
    assert therapy.endswith("therapy-summarizer.md")
    assert meeting.endswith("summarization/workflow.md")


def test_an_entity_with_no_binding_refuses_rather_than_picking_one():
    with pytest.raises(SystemExit) as raised:
        per_meeting_job.skill_for("nao-declarado", CONFIG["skill-bindings"])
    assert raised.value.code == per_meeting_job.EXIT_REFUSED


def test_the_skill_report_is_parsed_by_the_skills_own_keys():
    parsed = per_meeting_job.report_block(
        "blah\nGLOSSARY-LOADED: 8\nSUMMARY: /tmp/x-resumo.md\nDOUBTS: 1\nOUTCOME: filed\n")
    assert parsed["OUTCOME"] == "filed" and parsed["GLOSSARY-LOADED"] == "8"
    assert "blah" not in parsed


# ------------------------------------------------- the resolver's placement field
# `placement` is `template` when the route fixes the path and `delegated` when the
# destination repo's own CLAUDE.md decides. Reading `path` on a delegated answer
# would invent a destination, which is the one thing clause 7 forbids — so both
# branches are held here rather than only the one the fixture cases happen to hit.
def _prompt(destination: dict) -> str:
    return per_meeting_job.build_prompt(
        "/skills/x.md", Path("/work/t.md"), [],
        {"entity": "e", "destination": destination}, Path("/checkout"), "0954",
        {"discriminator": {"format": "%H%M", "insert-before": "-resumo"}})


def test_a_template_placement_names_the_folder_and_the_filename():
    text = _prompt({"repo": "r", "path": "a/b/2026-01-01-x-resumo.md", "placement": "template"})
    assert "Destination folder: /checkout/r/a/b" in text
    # The final, discriminated name: the summarizer writes it, publication files it.
    assert "Summary filename: 2026-01-01-x-0954-resumo.md" in text
    assert "own CLAUDE.md" not in text


def test_a_delegated_placement_names_the_repo_and_defers_to_its_CLAUDE_md():
    text = _prompt({"repo": "r", "placement": "delegated"})
    assert "Destination repo: /checkout/r" in text
    assert "own CLAUDE.md" in text
    assert "Summary filename:" not in text
    assert "`-0954`" in text


def test_a_delegated_placement_carrying_a_path_still_does_not_use_it():
    """A future route that leaks a `path` onto a delegated answer must not be obeyed."""
    text = _prompt({"repo": "r", "path": "should/not/appear.md", "placement": "delegated"})
    assert "should/not/appear" not in text


def test_an_already_done_job_does_nothing_and_writes_nothing(tmp_path):
    """The spine owns the disposition; a job it marks done must not be re-summarized."""
    job = json.loads((FIXTURES / "jobs" / "case-a.json").read_text("utf-8"))
    job["disposition"] = "already-done"
    counter = WriteCount({"all": tmp_path})
    with counter:
        result = per_meeting_job.run(
            job, artifacts={"artifacts": {}}, config_root=FIXTURES / "config",
            checkout_root=tmp_path / "checkout", channel_root=tmp_path / "channel",
            state=tmp_path / "state", work=tmp_path / "work", seams=SEAMS,
            store=tmp_path / "channel" / "stores" / "map.jsonl")
    assert result["action"] == "nothing-to-do"
    assert sum(counter.counts.values()) == 0


def test_an_illegible_transcript_posts_a_note_instead_of_vanishing(tmp_path):
    """The dangerous near-miss: not-admitted and unreadable both mean "no transcript"."""
    broken = tmp_path / "broken.md"
    broken.write_bytes(b"---\ntype: transcript\n---\n\xff\xfe not utf-8")
    job = json.loads((FIXTURES / "jobs" / "case-b.json").read_text("utf-8"))
    ref = job["source-set"][0]["drive-ref"]
    counter = WriteCount({"channel": tmp_path / "channel"})
    with counter:
        result = per_meeting_job.run(
            job,
            artifacts={"artifacts": {ref: {"location": str(broken), "name": "x - Transcricao",
                                           "media-type": "text/markdown"}}},
            config_root=FIXTURES / "config", checkout_root=tmp_path / "checkout",
            channel_root=tmp_path / "channel", state=tmp_path / "state",
            work=tmp_path / "work", seams=SEAMS,
            store=tmp_path / "channel" / "stores" / "map.jsonl")
    assert result["action"] == "unreadable" and result["outcome"] == "failed"
    assert result["messages"] == 1
    assert counter.counts["channel"] > 0      # the note was really written


# ------------------------------------------------- the settlement vocabulary
# r-owner-ruling-batch-0926 ruling 6: `skipped` and `unprocessable` joined the
# locked outcome list, and the two endings that had no word of their own stopped
# borrowing `withheld-unroutable`. Each arm below names the OLD value it refuses,
# so removing the change turns the arm red instead of leaving it vacuously green.
OLD_BORROWED_OUTCOME = "withheld-unroutable"


def outcome_enum() -> list[str]:
    """The locked list, read out of the seam — never a remembered six."""
    schema = json.loads((SEAMS / "failure-event-and-outcome.schema.json")
                        .read_text(encoding="utf-8"))
    for branch in schema["oneOf"]:
        enum = branch.get("properties", {}).get("outcome", {}).get("enum")
        if enum:
            return enum
    raise AssertionError("the failure-event-and-outcome seam names no outcome enum")


@pytest.mark.parametrize("word", ["skipped", "unprocessable"])
def test_the_locked_outcome_list_carries_the_two_ruled_words(word):
    assert word in outcome_enum()


def test_the_four_words_that_were_already_locked_are_untouched():
    """A widened enum must not have dropped or reordered what was already ratified."""
    assert outcome_enum()[:3] == ["filed", "amended", "withheld-unroutable"]
    assert outcome_enum()[-1] == "failed"


def test_the_publish_layers_quoted_vocabulary_matches_the_seam():
    """publish_job holds a hand-copied quote of the enum; drift between them is
    how one reader ends up on the old list."""
    sys.path.insert(0, str(HERE.parent.parent / "tools"))
    import publish_job

    assert list(publish_job.OUTCOMES) == outcome_enum()


def settlement_rows(state: Path) -> list[dict]:
    path = state / "outcomes.jsonl"
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def run_case(job_name: str, tmp_path: Path, *, replies=None, cycles: int = 1) -> dict:
    """One fixture case, run for real against its own materialised copy."""
    from harness import materialise

    scaffold = materialise(job_name, tmp_path / "runs")
    job = json.loads((FIXTURES / "jobs" / f"{job_name}.json").read_text("utf-8"))
    results = []
    for cycle in range(cycles):
        if replies and cycle in replies:
            scaffold["channel"].mkdir(parents=True, exist_ok=True)
            with (scaffold["channel"] / "replies.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(replies[cycle], ensure_ascii=False) + "\n")
        results.append(per_meeting_job.run(
            job,
            artifacts=json.loads(
                (scaffold["root"] / "artifacts" / "binding.json").read_text("utf-8")),
            config_root=scaffold["config"], checkout_root=scaffold["checkout"],
            channel_root=scaffold["channel"], state=scaffold["state"],
            work=scaffold["work"], seams=SEAMS,
            store=scaffold["channel"] / "stores" / "thread-meeting-map.jsonl"))
    return {"results": results, "rows": settlement_rows(scaffold["state"])}


def test_a_transcript_with_nothing_said_settles_as_unprocessable(tmp_path):
    """RED arm: before ruling 6 this settled as `withheld-unroutable` — a word
    that says the owner was asked about a meeting nobody was asked about."""
    run = run_case("case-f", tmp_path)
    verdict = run["results"][-1]

    assert verdict["action"] == "zero-utterance"
    assert verdict["outcome"] == "unprocessable"
    assert verdict["outcome"] != OLD_BORROWED_OUTCOME
    assert [row["outcome"] for row in run["rows"]] == ["unprocessable"]
    # nothing was filed, so the row carries no destination
    assert "destination" not in run["rows"][0]


def test_the_owners_skip_answer_settles_as_skipped(tmp_path):
    """RED arm: before ruling 6 the owner's own `skip` was recorded as
    `withheld-unroutable`, indistinguishable from a standing unanswered ask."""
    import channel_protocol

    reply = {"id": "reply-skip", "thread": channel_protocol.thread_id_for("mtg-m6-e"),
             "text": "skip", "at": "2026-04-02T20:00:00-03:00"}
    run = run_case("case-e", tmp_path, replies={1: reply}, cycles=2)
    asked, applied = run["results"]

    assert asked["action"] == "asked" and asked["outcome"] == OLD_BORROWED_OUTCOME
    assert applied["action"] == "skipped"
    assert applied["outcome"] == "skipped"
    assert applied["outcome"] != OLD_BORROWED_OUTCOME
    assert [row["outcome"] for row in run["rows"]] == ["skipped"]


def test_a_standing_unanswered_ask_still_says_withheld_unroutable(tmp_path):
    """The discriminating half: the two new words did NOT displace the old one
    where it is still the true reason — no write, and the owner was asked."""
    run = run_case("case-e", tmp_path)
    verdict = run["results"][-1]

    assert verdict["action"] == "asked"
    assert verdict["outcome"] == OLD_BORROWED_OUTCOME
    assert run["rows"] == []


def test_every_settlement_row_these_writers_emit_validates_against_the_seam(tmp_path):
    """The widened enum is only a contract if the rows still validate against it."""
    import channel_protocol

    seams = channel_protocol.Seams(SEAMS)
    schema, error = seams.schema("failure-event-and-outcome.schema.json")
    assert not error, error
    rows = []
    rows += run_case("case-f", tmp_path / "f")["rows"]
    rows += run_case("case-e", tmp_path / "e",
                     replies={1: {"id": "r", "thread": channel_protocol.thread_id_for("mtg-m6-e"),
                                  "text": "skip", "at": "2026-04-02T20:00:00-03:00"}},
                     cycles=2)["rows"]

    assert [row["outcome"] for row in rows] == ["unprocessable", "skipped"]
    for row in rows:
        assert seams.errors(row, schema) == [], row


# --------------------------------- the clinical fallthrough (owner ruling 3)
# r-owner-ruling-batch-0926 item 3 removed the catch-all route on the owner's
# own account. These arms measure the consequence at the JOB, where the owner
# either gets asked or gets a file: the resolver's own arms live in
# tests/routing/, and a typed `unroutable` that no caller turns into an ask
# would be a ruling applied in name only.


def test_an_own_account_meeting_matching_neither_clinician_asks_and_files_nothing(tmp_path):
    """RED arm: with the catch-all route present this returned `summarized`,
    invoked a summarizer and wrote a file, with no owner involvement at all."""
    from harness import WriteCount, materialise

    scaffold = materialise("own-no-clinician", tmp_path / "runs")
    job = json.loads((FIXTURES / "jobs" / "own-no-clinician.json").read_text("utf-8"))
    counter = WriteCount({"destination": scaffold["checkout"], "channel": scaffold["channel"]})
    with counter:
        result = per_meeting_job.run(
            job,
            artifacts=json.loads(
                (scaffold["root"] / "artifacts" / "binding.json").read_text("utf-8")),
            config_root=scaffold["config"], checkout_root=scaffold["checkout"],
            channel_root=scaffold["channel"], state=scaffold["state"],
            work=scaffold["work"], seams=SEAMS,
            store=scaffold["channel"] / "stores" / "thread-meeting-map.jsonl")

    assert result["action"] == "asked"
    assert result["asked"] is True
    assert result.get("wrote-summary") is not True
    # the counted zero: nothing reached the destination tree on this branch
    assert counter.counts["destination"] == 0
    # and the ask really was written, so the owner can answer it
    assert counter.counts["channel"] > 0
    assert result["messages"] >= 1


def test_the_clinician_route_on_the_same_account_still_files_without_asking(tmp_path):
    """The discriminating half: the ruling removed one route, not the account."""
    from harness import materialise

    scaffold = materialise("clinic-still-routes", tmp_path / "runs")
    job = json.loads((FIXTURES / "jobs" / "own-no-clinician.json").read_text("utf-8"))
    job["source-set"][0]["participants"] = ["Dora Marques"]
    routed = per_meeting_job.destination_resolver.resolve(job, scaffold["config"])

    assert routed["kind"] == "routed"
    assert routed["entity"] == "clinic-fix"


def test_every_model_turn_goes_through_cast_with_the_configured_model(tmp_path, monkeypatch):
    """Owner ruling r-no-vendor-in-code (2026-09-27): no harness is typed into code."""
    seen = {}

    def fake_run(argv, **kwargs):
        seen["argv"] = argv
        return subprocess.CompletedProcess(argv, 0, stdout="OUTCOME: filed\n", stderr="")

    monkeypatch.setattr(per_meeting_job.subprocess, "run", fake_run)
    invocation = {"harness": "EXAMPLE-harness", "model": "EXAMPLE-model", "effort": 2}
    out = per_meeting_job.invoke_agent("do it", tmp_path, tmp_path / "log", 60, invocation)
    assert seen["argv"][:5] == ["cast", "EXAMPLE-harness", "EXAMPLE-model", "2", str(tmp_path)]
    assert out["exit"] == 0 and "OUTCOME: filed" in out["text"]
    with pytest.raises(SystemExit):
        per_meeting_job.invocation_of({"invocation": {"harness": "x"}})
