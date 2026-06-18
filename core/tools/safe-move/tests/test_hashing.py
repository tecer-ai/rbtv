"""Tests for per-candidate drift hashes."""

from pathlib import Path

from safe_move.hashing import compute_hash
from safe_move.matchers import Candidate


def cand(
    *,
    match: str = "[[old]]",
    context: str = "See [[old]] today.",
) -> Candidate:
    """Build a minimal ``Candidate`` for hashing tests."""
    return Candidate(
        file="notes.md",
        line=1,
        match=match,
        context=context,
        syntax="wikilink",
        target="old",
        fragment=None,
        alias=None,
        encoding="plain",
        resolves_to=1,
        read_only=False,
        generated=False,
        boundary=Path("notes"),
    )


def test_hash_is_deterministic_for_same_candidate() -> None:
    candidate = cand()

    assert compute_hash(candidate) == compute_hash(candidate)


def test_hash_changes_when_context_changes_by_one_character() -> None:
    original = cand(context="See [[old]] today.")
    changed = cand(context="See [[old]] today!")

    assert compute_hash(original) != compute_hash(changed)


def test_hash_changes_when_match_changes() -> None:
    original = cand(match="[[old]]", context="See [[old]] today.")
    changed = cand(match="[[older]]", context="See [[older]] today.")

    assert compute_hash(original) != compute_hash(changed)


def test_hash_is_recomputable_from_same_match_and_context() -> None:
    consult_candidate = cand(match="[old](old.md)", context="See [old](old.md).")
    act_candidate = cand(match="[old](old.md)", context="See [old](old.md).")

    assert compute_hash(consult_candidate) == compute_hash(act_candidate)
