"""Stable drift hashes for safe-move candidates."""

from __future__ import annotations

import hashlib

from safe_move.matchers import Candidate


def compute_hash(candidate: Candidate) -> str:
    """Return a SHA-256 hex digest of a candidate's matched text and context."""
    payload = f"{candidate.match}\x00{candidate.context}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
