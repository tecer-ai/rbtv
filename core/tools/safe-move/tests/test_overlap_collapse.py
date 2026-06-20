"""Tests for overlapping edit span handling in act."""

from __future__ import annotations

import pytest

from safe_move.act import _ApplySiteError, _replace_context_matches


def _ref(ref_id: str, match: str, proposed: str, offset: int = 0) -> dict[str, object]:
    return {
        "id": ref_id,
        "match": match,
        "proposed": proposed,
        "offset": offset,
        "context": "unused",
    }


def test_identical_span_with_identical_proposed_applies_once():
    context = '  - "[[long-context-scaffolds-comparison.md]]"\n'
    match = "[[long-context-scaffolds-comparison.md]]"
    proposed = "[[long-context-scaffolds-renamed.md]]"
    refs = [
        _ref("ref-0001", match, proposed, 0),
        _ref("ref-0002", match, proposed, 0),
    ]

    assert _replace_context_matches(context, refs, "wiki.md") == (
        '  - "[[long-context-scaffolds-renamed.md]]"\n'
    )


def test_identical_span_with_different_proposed_escalates():
    context = '  - "[[old.md]]"\n'
    refs = [
        _ref("ref-0001", "[[old.md]]", "[[new-a.md]]", 0),
        _ref("ref-0002", "[[old.md]]", "[[new-b.md]]", 0),
    ]

    with pytest.raises(_ApplySiteError, match="DOUBT_ESCALATED overlapping matches"):
        _replace_context_matches(context, refs, "wiki.md")


def test_partially_overlapping_distinct_spans_escalate():
    context = "abcdef"
    refs = [
        _ref("ref-0001", "abc", "ABC", 0),
        _ref("ref-0002", "bcd", "BCD", 1),
    ]

    with pytest.raises(_ApplySiteError, match="DOUBT_ESCALATED overlapping matches"):
        _replace_context_matches(context, refs, "wiki.md")


def test_non_overlapping_distinct_spans_both_apply():
    context = "alpha beta gamma"
    refs = [
        _ref("ref-0001", "alpha", "ALPHA", 0),
        _ref("ref-0002", "gamma", "GAMMA", 0),
    ]

    assert _replace_context_matches(context, refs, "wiki.md") == "ALPHA beta GAMMA"
