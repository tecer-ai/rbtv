"""The summarize -> channel handoff row, at the point it is born.

m8 proved the channel side against a row its own probe staged; m6 proved the
summary. Nothing produced the row in the running product, so the joint was dead.
These are the standing guards over the producer: the m9 joint probe proves the
two halves meet end to end, and this file keeps the parser and the row shape from
drifting afterwards.
"""

import json
import sys
from pathlib import Path

import pytest

PRODUCT = Path(__file__).resolve().parents[2]
SEAMS = PRODUCT / "seams"
if str(PRODUCT / "tools") not in sys.path:
    sys.path.insert(0, str(PRODUCT / "tools"))

import per_meeting_job  # noqa: E402

DEST = {"repo": "EXAMPLE-repo", "path": "notes/2026-03-11-EXAMPLE-resumo.md"}

# The skill's explanation line, byte-exact as ra-1 fixed it (workflows/
# summarization/workflow.md, Unattended Mode § 2): present in every summary that
# carries at least one doubt, and itself carrying the marker grammar's own
# placeholders.
LEGEND_LINE = ("> Termos que o glossario nao resolveu estao marcados como "
               "`{{doubt|term=<term>|guess=<best-guess>}}` e serao corrigidos "
               "no lugar quando o owner responder.")


def test_a_summary_with_the_legend_line_yields_exactly_the_marked_terms():
    """ts-1: the legend explains the notation; it is not a doubt of its own."""
    summary = (LEGEND_LINE + "\n"
               "Presentes: Ana e {{doubt|term=Quenu|guess=Kenu}}.\n"
               "{{doubt|term=Xandi|guess=Xandari}} plenfou.\n")
    doubts = per_meeting_job.parse_doubts(summary)
    assert [d["term"] for d in doubts] == ["Quenu", "Xandi"]
    assert all(d["term"] != "<term>" for d in doubts)


def test_the_legend_exclusion_pair_is_the_seam_grammar_s_own_placeholders():
    """The typed pair is pinned to the seam const, so a grammar change fails
    here instead of silently re-admitting the legend (or excluding a real term)."""
    schema = json.loads((SEAMS / "doubt-flag-marker.schema.json").read_text("utf-8"))
    const = schema["properties"]["marker-syntax"]["const"]
    assert f"term={per_meeting_job.LEGEND_TERM}|guess={per_meeting_job.LEGEND_GUESS}" in const


def test_parses_one_marker_with_its_line_as_excerpt():
    doubts = per_meeting_job.parse_doubts(
        "Presentes: Ana e {{doubt|term=Quenu|guess=Kenu}}.\nOutra linha.\n")
    assert doubts == [{"term": "Quenu", "guess": "Kenu",
                       "excerpt": "Presentes: Ana e {{doubt|term=Quenu|guess=Kenu}}."}]


def test_a_term_marked_twice_is_ONE_doubt():
    """The owner is asked about a TERM, not about a line."""
    doubts = per_meeting_job.parse_doubts(
        "{{doubt|term=Quenu|guess=Kenu}} abriu.\nDepois {{doubt|term=Quenu|guess=Kenu}} fechou.\n")
    assert [d["term"] for d in doubts] == ["Quenu"]


def test_two_distinct_terms_are_two_doubts_in_order():
    doubts = per_meeting_job.parse_doubts(
        "{{doubt|term=Quenu|guess=Kenu}} e {{doubt|term=Xandi|guess=Xandari}}.\n")
    assert [d["term"] for d in doubts] == ["Quenu", "Xandi"]


def test_a_summary_with_no_marker_produces_NO_row(tmp_path):
    """The channel's quiet is the product's payoff; an empty row is a message
    with nothing in it."""
    summary = tmp_path / "s.md"
    summary.write_text("Nada em dúvida aqui.\n", encoding="utf-8")
    state = tmp_path / "state"
    row = per_meeting_job.hand_off_doubts(
        state, SEAMS, meeting_key="mtg-x", entity="EXAMPLE-entity",
        work=tmp_path, transcript=tmp_path / "t.md",
        destination=DEST, summary_path=summary)
    assert row is None
    assert not (state / "doubts.jsonl").exists()


def test_the_row_carries_the_four_fields_and_a_seam_valid_marker(tmp_path):
    summary = tmp_path / "s.md"
    summary.write_text("Falou {{doubt|term=Quenu|guess=Kenu}} hoje.\n", encoding="utf-8")
    state = tmp_path / "state"
    row = per_meeting_job.hand_off_doubts(
        state, SEAMS, meeting_key="mtg-x", entity="EXAMPLE-entity",
        work=tmp_path, transcript=tmp_path / "mtg-x-transcript.md",
        destination=DEST, summary_path=summary)
    assert set(row) == {"meeting-key", "entity", "work", "transcript", "marker"}
    assert row["transcript"] == "./mtg-x-transcript.md"
    assert row["marker"]["summary"] == DEST
    # The grammar is READ from the seam, never typed in the producer.
    schema = json.loads((SEAMS / "doubt-flag-marker.schema.json").read_text("utf-8"))
    assert row["marker"]["marker-syntax"] == schema["properties"]["marker-syntax"]["const"]
    appended = [json.loads(l) for l in (state / "doubts.jsonl").read_text("utf-8").splitlines() if l]
    assert appended == [row]


def test_a_reported_summary_that_cannot_be_read_REFUSES(tmp_path):
    """A skill that reports a SUMMARY path it did not write must not pass silently."""
    with pytest.raises(SystemExit):
        per_meeting_job.hand_off_doubts(
            tmp_path / "state", SEAMS, meeting_key="mtg-x", entity="EXAMPLE-entity",
            work=tmp_path, transcript=tmp_path / "t.md",
            destination=DEST, summary_path=tmp_path / "does-not-exist.md")
