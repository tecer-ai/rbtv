"""Risk classifier for safe-move.

Assigns each discovered reference one of three classes:

* ``auto``      — precise, low blast-radius, safe to fix automatically.
* ``surface``   — ambiguous, cross-boundary, read-only, generated, or
                  machine-read in a way that an agent should decide.
* ``protected`` — recorded content (transcript, log/history, quote) that
                  nobody edits.

The classifier is deliberately generic: it uses only the candidate record,
the operation type, and universal content signals.  No vault, sb-os, or
RBTV-specific convention is hardcoded.
"""

from __future__ import annotations

import re
from pathlib import Path

from safe_move.matchers import Candidate

#: Recognized operation types.
OPERATION_MOVE = "move"
OPERATION_RENAME = "rename"
OPERATION_BOTH = "both"
VALID_OPERATIONS = frozenset({OPERATION_MOVE, OPERATION_RENAME, OPERATION_BOTH})

#: Classes returned by ``classify``.
CLASS_AUTO = "auto"
CLASS_SURFACE = "surface"
CLASS_PROTECTED = "protected"

#: Syntaxes that the non-code classifier handles.
#: ``code-import`` is intentionally out of scope for this phase.
NON_CODE_SYNTAXES = frozenset(
    {
        "wikilink",
        "markdown-link",
        "frontmatter-field",
        "config-path",
    }
)

#: Syntaxes whose auto-eligibility is limited to the careful case.
CAREFUL_SYNTAXES = frozenset({"config-path"})

#: Syntaxes handled by the structural code-matcher.
CODE_SYNTAXES = frozenset({"code-import"})


# ---------------------------------------------------------------------------
# Protected-region detection — generic signals only
# ---------------------------------------------------------------------------

# Speaker / timestamp patterns used to detect transcripts and dictation.
# Examples that match: "[12:34] Alice:" , "[00:00:00] Bob:"
_TIMESTAMP_SPEAKER_RE = re.compile(
    r"(?:"
    r"^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*(?:\w+\s*:)"  # [HH:MM] Speaker:
    r"|"
    r"^\s*\[\d{1,2}:\d{2}(?::\d{2})?\]\s*\w+"          # [HH:MM] Speaker
    r")",
    re.MULTILINE,
)

_BARE_SPEAKER_RE = re.compile(
    r"^\s*(?P<speaker>[A-Z][\w'-]*|[A-Z])\s*:\s+(?P<text>\S.*)$"
)

_METADATA_VALUE_RE = re.compile(
    r"(?:"
    r"\[\[.*\]\]"
    r"|"
    r"\[[^\]]+\]\([^)]+\)"
    r"|"
    r"[./~]?[\w.-]+(?:[/\\][\w .-]+)+"
    r"|"
    r"[\w .-]+\.[A-Za-z0-9]{1,8}(?:[#?].*)?$"
    r")"
)


def _is_bare_speaker_line(line: str) -> bool:
    """Return True when a bare ``Name:`` line looks like dialogue."""
    match = _BARE_SPEAKER_RE.match(line)
    if not match:
        return False
    text = match.group("text").strip()
    return not _METADATA_VALUE_RE.fullmatch(text)


def _is_speaker_or_timestamp_line(line: str) -> bool:
    """Return True for transcript/dictation speaker or timestamp lines."""
    return bool(_TIMESTAMP_SPEAKER_RE.search(line) or _is_bare_speaker_line(line))


def _is_transcript_signal(
    candidate: Candidate, scope_root: Path | str | None = None
) -> bool:
    """Return True when the candidate lives in a transcript/dictation region."""
    basename = Path(candidate.file).name.lower()
    if "transcript" in basename:
        return True

    if scope_root is None:
        # Without a scope root we cannot read neighbouring lines for
        # corroboration, so we fall back to the filename signal only.
        return False

    # Require >=2 consecutive speaker/timestamp-shaped lines in a small window
    # around the match.  A lone ``Word:`` line no longer protects by itself.
    file_path = Path(scope_root) / candidate.file
    try:
        lines = file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, ValueError):
        return False

    idx = candidate.line - 1  # 0-based
    window = lines[max(0, idx - 3) : min(len(lines), idx + 4)]
    consecutive = 0
    for line in window:
        if _is_speaker_or_timestamp_line(line):
            consecutive += 1
            if consecutive >= 2:
                return True
        else:
            consecutive = 0
    return False


def _is_log_or_history_signal(candidate: Candidate) -> bool:
    """Return True when the candidate lives in a log/history/record region."""
    basename = Path(candidate.file).name.lower()
    # Recognized record files only.
    if basename == "changelog.md" or "changelog" in basename:
        return True
    # Commit-message body: indented line inside a commit-message-looking file.
    if "commit" in basename or "message" in basename:
        stripped = candidate.context.lstrip(" ")
        indent = len(candidate.context) - len(stripped)
        if indent >= 4:
            return True
    return False


def _is_quote_signal(candidate: Candidate) -> bool:
    """Return True when the match sits inside a markdown blockquote."""
    return candidate.context.lstrip().startswith(">")


def is_protected_region(
    candidate: Candidate, scope_root: Path | str | None = None
) -> bool:
    """Detect protected recorded content using generic signals.

    The detection is intentionally conservative: any generic transcript,
    log/history, or blockquote signal tips the candidate to ``protected``.
    Transcript protection now requires corroboration (filename or >=2
    consecutive speaker/timestamp lines) rather than a lone line shape.
    """
    return (
        _is_quote_signal(candidate)
        or _is_transcript_signal(candidate, scope_root)
        or _is_log_or_history_signal(candidate)
    )


# ---------------------------------------------------------------------------
# Operation classification
# ---------------------------------------------------------------------------


def classify_operation(old: str, new: str) -> str:
    """Classify the move operation as ``move``, ``rename``, or ``both``."""
    old_path = Path(old)
    new_path = Path(new)

    old_dir = old_path.parent
    new_dir = new_path.parent
    old_name = old_path.name
    new_name = new_path.name

    dir_changes = old_dir != new_dir
    name_changes = old_name != new_name

    if dir_changes and name_changes:
        return OPERATION_BOTH
    if dir_changes:
        return OPERATION_MOVE
    if name_changes:
        return OPERATION_RENAME
    # No change — still a valid input; treat as move (no replacement needed).
    return OPERATION_MOVE


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


def _off_limits(candidate: Candidate) -> bool:
    """Return True when the candidate is in an off-limits location."""
    return bool(
        candidate.read_only
        or candidate.boundary is not None
        or candidate.generated
    )


def _match_is_ambiguous(candidate: Candidate) -> bool:
    """Return True when the match is too ambiguous for auto-fixing."""
    if candidate.resolves_to > 1:
        return True
    return False


def _replacement_is_certain(candidate: Candidate, operation: str) -> bool:
    """Return True when the operation-aware new value is uniquely known.

    * Wikilinks are resolved by basename.  A pure move keeps the basename, so
      no replacement is needed (still certain).  A rename/both changes the
      basename; certainty requires a unique target.
    * Markdown links, frontmatter fields, and config paths encode a relative
      path.  Any operation that changes the directory or basename changes the
      correct relative path, but for a single resolved target the new path is
      deterministic.  Certainty therefore requires a unique target.
    """
    if candidate.resolves_to != 1:
        return False

    if candidate.syntax == "wikilink":
        if operation == OPERATION_MOVE:
            return True
        # rename / both: the new basename is known because the target is unique.
        return True

    # markdown-link / frontmatter-field / config-path
    return True


def _code_replacement_is_certain(candidate: Candidate) -> bool:
    """Return True for a precise, single-target structural code reference.

    The structural matcher only emits AST-confirmed static import/require/export
    nodes, so ``code-import`` candidates are already past the dynamic/aliased/
    string-built filter.  The remaining certainty test is a single resolvable
    target and a non-ambiguous match.
    """
    return candidate.syntax == "code-import" and candidate.resolves_to == 1


def _auto_eligible_syntax(syntax: str) -> bool:
    """Return True for syntaxes that may ever be ``auto`` in the non-code phase."""
    return syntax in NON_CODE_SYNTAXES


def classify(candidate: Candidate, operation: str, *, scope_root: Path | str | None = None) -> str:
    """Assign ``auto`` / ``surface`` / ``protected`` to a candidate reference.

    Parameters
    ----------
    candidate:
        The discovered reference from the matcher layer.
    operation:
        One of ``move``, ``rename``, ``both`` (see ``classify_operation``).
    scope_root:
        Optional scope root for reading richer file context.  Reserved for
        future multi-line protected-region detection; the current heuristics
        operate on the candidate's own ``context`` line.
    """
    if operation not in VALID_OPERATIONS:
        raise ValueError(f"invalid operation: {operation!r}")

    # 1. Protected recorded content — nobody edits.
    if is_protected_region(candidate, scope_root):
        return CLASS_PROTECTED

    # 2. Off-limits locations — agent decides; never auto.
    if _off_limits(candidate):
        return CLASS_SURFACE

    # 3. Path-qualified wikilinks ([[dir/name|alias]]) carry an explicit path; the
    # correct rewrite form (vault-root vs file-relative, .md handling) is surfaced
    # for the agent rather than auto-applied. A bare [[name]] is unaffected.
    if candidate.syntax == "wikilink" and "/" in candidate.target:
        return CLASS_SURFACE

    # 4. Match-safety gate.
    if _match_is_ambiguous(candidate):
        return CLASS_SURFACE

    # 5. Code precision gate: structural static single-target → auto; else surface.
    if candidate.syntax in CODE_SYNTAXES:
        if _code_replacement_is_certain(candidate):
            return CLASS_AUTO
        return CLASS_SURFACE

    # 6. Syntax gate: only recognized non-code syntaxes reach auto.
    if not _auto_eligible_syntax(candidate.syntax):
        return CLASS_SURFACE

    # 7. Operation-aware certainty gate.
    if not _replacement_is_certain(candidate, operation):
        return CLASS_SURFACE

    # 8. Risk gate — blast radius.
    #    Wikilink / markdown-link / frontmatter-field: plain prose/notes.
    #    Config-path: precise path literal in a settings file — careful, but auto.
    return CLASS_AUTO
