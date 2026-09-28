"""Gemini notes as the third source, at the summarize side.

Owner ruling 2026-09-26: a meeting's inputs are its transcripts AND its Gemini
notes file. The notes are a model-written summary, so they are supplementary input
only — never merged, quoted or glossary-corrected as spoken words (goal.md clause 19).
A meeting holding ONLY notes is summarized from them, labelled (clause 19 as
amended 2026-09-27).

Every arm stands on the one premise that makes the rule matter: a notes file whose
bytes the reader, left alone, WOULD call a transcript. No summarizer is invoked —
the invocation is a stand-in that records the prompt it was handed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "tools"))

import artifact_reader as reader          # noqa: E402
import per_meeting_job                    # noqa: E402
from harness import FIXTURES, WriteCount, materialise   # noqa: E402

SEAMS = HERE.parent.parent / "seams"
MARKERS = json.loads((FIXTURES / "config" / "summarize.json").read_text("utf-8"))["artifact-kinds"]
NOTES_REF = "drv:file/EXAMPLE-gemini-notes"
# Timestamped lines and a name carrying no notes marker: the reader's own three
# signals all say "transcript" here.
NOTES_BYTES = "00:00:05 EXAMPLE-Nara: resumo gerado pelo modelo, nao falado por ninguem\n"


def notes_record(meeting: dict) -> dict:
    first = meeting["source-set"][0]
    return {**first, "source": "gemini-notes", "drive-ref": NOTES_REF}


def scaffold_with_notes(tmp_path: Path) -> tuple[dict, dict, dict]:
    scaffold = materialise("case-a", tmp_path / "runs")
    artifacts = json.loads((scaffold["root"] / "artifacts" / "binding.json").read_text("utf-8"))
    artifacts["auxiliary"] = {}
    notes = scaffold["root"] / "artifacts" / "gemini-notes.md"
    notes.write_text(NOTES_BYTES, encoding="utf-8")
    artifacts["artifacts"][NOTES_REF] = {"location": str(notes), "name": "EXAMPLE-Alpha sync",
                                         "media-type": "text/markdown"}
    job = json.loads((FIXTURES / "jobs" / "case-a.json").read_text("utf-8"))
    return scaffold, artifacts, job


def run(job: dict, scaffold: dict, artifacts: dict, prompts: list) -> dict:
    def invoke(prompt, cwd, log_dir, timeout):
        prompts.append(prompt)
        return {"exit": 1, "text": "", "report": {}}

    return per_meeting_job.run(
        job, artifacts=artifacts, config_root=scaffold["config"],
        checkout_root=scaffold["checkout"], channel_root=scaffold["channel"],
        state=scaffold["state"], work=scaffold["work"], seams=SEAMS,
        store=scaffold["channel"] / "stores" / "thread-meeting-map.jsonl", invoke=invoke)


def test_the_premise_the_reader_alone_would_call_these_notes_a_transcript(tmp_path):
    _, artifacts, _ = scaffold_with_notes(tmp_path)
    verdict = reader.read_artifact(NOTES_REF, artifacts["artifacts"][NOTES_REF], MARKERS)
    assert verdict["artifact-kind"] == "transcript"


def test_notes_ride_beside_the_transcripts_and_are_never_merged_into_them(tmp_path):
    scaffold, artifacts, job = scaffold_with_notes(tmp_path)
    job["source-set"].append(notes_record(job))
    prompts: list = []
    result = run(job, scaffold, artifacts, prompts)

    assert result["merge"]["sources"] == ["meet", "tactiq"]
    (prompt,) = prompts
    notes_lines = [line for line in prompt.splitlines() if line.startswith("Auxiliary meeting notes")]
    assert len(notes_lines) == 1
    assert "not spoken words" in notes_lines[0] and "never glossary-correct" in notes_lines[0]
    transcript = (scaffold["work"] / f"{job['meeting-key']}-transcript.md").read_text("utf-8")
    assert "resumo gerado pelo modelo" not in transcript


def test_a_meeting_holding_only_notes_is_summarized_from_the_notes_and_labelled(tmp_path):
    # Clause 19 as amended 2026-09-27 (owner ruling r-gemini-notes-alone-triggers-summary).
    scaffold, artifacts, job = scaffold_with_notes(tmp_path)
    job["source-set"] = [notes_record(job)]
    prompts: list = []
    result = run(job, scaffold, artifacts, prompts)

    assert result["notes-only"] is True and "merge" not in result
    (prompt,) = prompts
    lines = prompt.splitlines()
    assert not any(line.startswith("Transcript:") for line in lines)
    assert any(line.startswith("Meeting notes (the ONLY source") for line in lines)
    assert per_meeting_job.NOTES_ONLY_LABEL in prompt
    assert not (scaffold["work"] / f"{job['meeting-key']}-transcript.md").exists()


def test_content_routing_accepts_only_a_declared_pick(tmp_path):
    # Pass two of routing (owner ruling r-route-by-content-not-account, 2026-09-27).
    choices = [{"entity": "EXAMPLE-biz", "content": "business"},
               {"entity": "EXAMPLE-rbtv", "content": "the toolkit"}]

    def answering(text, exit_code=0):
        return lambda prompt, cwd, log_dir, timeout: {"exit": exit_code, "text": text,
                                                       "report": {}}

    def pick(invoke):
        return per_meeting_job.classify_content([tmp_path / "t.md"], choices, tmp_path,
                                                tmp_path / "log", 60, invoke)

    assert pick(answering("reasoning...\n**ENTITY:** EXAMPLE-rbtv\n")) == "EXAMPLE-rbtv"
    assert pick(answering("ENTITY: unsure")) is None
    assert pick(answering("ENTITY: EXAMPLE-nobody")) is None
    assert pick(answering("ENTITY: EXAMPLE-biz", exit_code=1)) is None


# ------------------- Google's transcript inside a Gemini notes document
# Owner ruling r-google-transcript-in-notes (2026-09-27): the "📖 Transcrição"
# section is Google Meet's verbatim transcript — speech, the PRIMARY wording — and
# is split off; without it the document is Gemini's summary only, as before.
HEADINGS = ["📖 Transcrição", "📖 Transcript"]
WITH = FIXTURES / "artifacts" / "gemini-notes-with-google-transcript.md"
WITHOUT = FIXTURES / "artifacts" / "gemini-notes-without-google-transcript.md"


def test_the_notes_split_into_geminis_summary_and_googles_transcript():
    summary, spoken = reader.split_notes(WITH.read_text("utf-8"), HEADINGS)
    assert spoken.startswith("📖 Transcrição") and "preciso ativar manualmente" in spoken
    assert "preciso ativar" not in summary and "Unificar especificações" in summary
    text = WITHOUT.read_text("utf-8")
    assert reader.split_notes(text, HEADINGS) == (text, None)
    # no configured heading: nothing is split, whatever the document holds
    assert reader.split_notes(WITH.read_text("utf-8"), [])[1] is None


def _notes_only_run(tmp_path, notes_file: Path) -> tuple:
    scaffold, artifacts, job = scaffold_with_notes(tmp_path)
    config = json.loads((scaffold["config"] / "summarize.json").read_text("utf-8"))
    config["artifact-kinds"]["meeting-notes"]["transcript-headings"] = HEADINGS
    (scaffold["config"] / "summarize.json").write_text(json.dumps(config), "utf-8")
    artifacts["artifacts"][NOTES_REF]["location"] = str(notes_file)
    job["source-set"] = [notes_record(job)]
    prompts: list = []
    result = run(job, scaffold, artifacts, prompts)
    return result, prompts[0], scaffold, job


def test_a_notes_document_with_googles_transcript_is_summarized_from_it(tmp_path):
    result, prompt, scaffold, job = _notes_only_run(tmp_path, WITH)
    assert result["google-transcript"] is True and not result.get("notes-only")
    assert "Google Meet's own verbatim transcript (speech; the PRIMARY wording)" in prompt
    assert "the ONLY source" not in prompt
    assert per_meeting_job.NOTES_ONLY_LABEL not in prompt
    staged = scaffold["work"] / f"{job['meeting-key']}{per_meeting_job.GOOGLE_TRANSCRIPT_SUFFIX}"
    assert "preciso ativar manualmente" in staged.read_text("utf-8")
    notes = (scaffold["work"] / f"{job['meeting-key']}-notes-1.md").read_text("utf-8")
    assert "preciso ativar" not in notes, "the speech stayed inside the 'summary' notes"


def test_a_notes_document_without_googles_transcript_runs_exactly_as_before(tmp_path):
    result, prompt, scaffold, job = _notes_only_run(tmp_path, WITHOUT)
    assert result["google-transcript"] is False and result["notes-only"] is True
    assert "Google Meet" not in prompt, "a Google transcript source was claimed with none present"
    assert per_meeting_job.NOTES_ONLY_LABEL in prompt


def test_google_and_a_second_transcript_carry_the_reconcile_rule(tmp_path):
    text = per_meeting_job.build_prompt(
        "/skills/x.md", Path("/work/t.md"), [], {"entity": "e", "destination":
        {"repo": "r", "placement": "delegated"}}, Path("/checkout"), "0954",
        {"discriminator": {"format": "%H%M", "insert-before": "-resumo"}},
        google=Path("/work/g.md"))
    assert per_meeting_job.RECONCILE_RULE in text
    assert "NEVER combine the two into a quote" in text
