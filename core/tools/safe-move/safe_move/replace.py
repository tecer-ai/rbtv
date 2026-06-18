"""Operation-aware replacement computation for safe-move.

Given a discovered reference (``Candidate``), the old path, the new path, and
the classified operation (move / rename / both), compute the single correct
replacement string for ``candidate.match``.  If a single correct replacement
cannot be determined, return ``None`` so the reference stays ``surface``.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from pathlib import Path

from safe_move.classify import (
    OPERATION_MOVE,
    VALID_OPERATIONS,
)
from safe_move.matchers import Candidate, _case_equal, _normalize_old, _rel


# Markdown-link text/path extractor (a stricter view of the matcher regex).
_MARKDOWN_LINK_RE = re.compile(
    r"\[(?P<text>[^\]\r\n]*)\]"
    r"\("
    r"(?P<path><[^>\r\n]+>|[^)\s\r\n]+)"
    r"(?:\s+[\"'][^\"'\r\n]*[\"'])?"
    r"\)"
)


class ReplacementError(Exception):
    """Raised when replacement computation encounters an unrecoverable problem."""


def compute_proposed(
    candidate: Candidate,
    old: str,
    new: str,
    operation: str,
    *,
    scope_root: Path | str | None = None,
) -> str | None:
    """Return the operation-aware replacement for ``candidate.match``.

    Returns the same string as ``match`` when no edit is needed (pure-move
    wikilinks).  Returns ``None`` when a single correct replacement cannot be
    computed deterministically.
    """
    if operation not in VALID_OPERATIONS:
        raise ReplacementError(f"invalid operation: {operation!r}")

    if scope_root is None:
        return None

    scope_root_path = Path(scope_root).expanduser().resolve()
    old_rel = _normalize_old(old, scope_root_path)
    new_rel = _normalize_old(new, scope_root_path)

    if candidate.syntax == "wikilink":
        return _propose_wikilink(candidate, new_rel, operation)
    if candidate.syntax == "markdown-link":
        return _propose_markdown_link(candidate, new_rel, scope_root_path)
    if candidate.syntax == "frontmatter-field":
        return _propose_frontmatter_field(candidate, old_rel, new_rel, operation, scope_root_path)
    if candidate.syntax == "config-path":
        return _propose_config_path(candidate, old_rel, new_rel, operation, scope_root_path)
    if candidate.syntax == "inline-code-path":
        return _propose_inline_code_path(candidate, old_rel, new_rel, scope_root_path)

    # Unknown syntax — cannot compute a deterministic replacement.
    return None


# ---------------------------------------------------------------------------
# Wikilink replacement
# ---------------------------------------------------------------------------


def _propose_wikilink(candidate: Candidate, new_rel: str, operation: str) -> str:
    """Compute the replacement for a wikilink reference.

    Pure move leaves the basename unchanged, so ``proposed == match``.
    Rename/both swap in the new basename, preserving extension form, leading
    embed ``!``, fragment, and alias.
    """
    if operation == OPERATION_MOVE:
        return candidate.match

    new_name = _new_basename_or_stem(candidate.target, new_rel)

    prefix = "!" if candidate.match.startswith("!") else ""
    inner = new_name
    if candidate.fragment:
        inner += candidate.fragment
    if candidate.alias is not None:
        inner += f"|{candidate.alias}"

    return f"{prefix}[[{inner}]]"


# ---------------------------------------------------------------------------
# Markdown-link replacement
# ---------------------------------------------------------------------------


def _propose_markdown_link(candidate: Candidate, new_rel: str, scope_root: Path) -> str | None:
    """Compute the replacement for a markdown link ``[text](path)``.

    The path is always recomputed relative to the referring file's directory.
    The link label, fragment, original encoding form, and a leading ``./``
    style are preserved.
    """
    parsed = _MARKDOWN_LINK_RE.fullmatch(candidate.match)
    if not parsed:
        return None

    text = parsed.group("text")
    original_path = parsed.group("path")

    file_dir = str(Path(candidate.file).parent)
    new_path = _compute_relative_path(file_dir, new_rel, scope_root)
    if new_path is None:
        return None

    if candidate.fragment:
        new_path = f"{new_path}{candidate.fragment}"

    # Preserve a leading "./" or ".\" marker when the original used one.
    if original_path.startswith("./") or original_path.startswith(".\\"):
        if not new_path.startswith("./"):
            new_path = f"./{new_path}"

    raw_path = _reencode_path(new_path, candidate.encoding)
    return f"[{text}]({raw_path})"


def _reencode_path(path: str, encoding: str) -> str:
    """Re-encode ``path`` to the original markdown-link encoding form."""
    if encoding == "url-encoded":
        if "#" in path:
            path_part, fragment = path.split("#", 1)
            return f"{urllib.parse.quote(path_part, safe='/')}#{fragment}"
        return urllib.parse.quote(path, safe="/")
    if encoding == "angle-bracket":
        return f"<{path}>"
    return path


# ---------------------------------------------------------------------------
# Frontmatter-field replacement
# ---------------------------------------------------------------------------


def _propose_frontmatter_field(
    candidate: Candidate,
    old_rel: str,
    new_rel: str,
    operation: str,
    scope_root: Path,
) -> str | None:
    """Compute the replacement for a frontmatter field value.

    Wikilink-shaped values are replaced like wikilinks.  Values that look
    like paths (contain ``/`` or a file extension) are treated as
    scope-root-relative paths, preserving their resolution form when they
    contain ``/``.  Bare names without an extension are treated as
    wikilink-style basenames and keep their extension form.
    """
    match = candidate.match

    if match.startswith("[[") and match.endswith("]]"):
        return _propose_wikilink_value(match, candidate.target, candidate.fragment, candidate.alias, new_rel, operation)

    if "/" in match or Path(match).suffix:
        if "/" in match:
            file_dir = str(Path(candidate.file).parent)
            form = _resolve_form(match, file_dir, scope_root, old_rel)
            if form is None:
                return None
            return _compute_path_value(form, file_dir, new_rel, scope_root)
        # Bare filename with extension = scope-root-relative path.
        return _compute_path_value("scope-root", "", new_rel, scope_root)

    # Bare name without extension = wikilink-style basename.  Pure move keeps it.
    if operation == OPERATION_MOVE:
        return match
    return _new_basename_or_stem(match, new_rel)


def _propose_wikilink_value(
    match: str,
    target: str,
    fragment: str | None,
    alias: str | None,
    new_rel: str,
    operation: str,
) -> str:
    """Compute the replacement for a wikilink-shaped frontmatter value."""
    if operation == OPERATION_MOVE:
        return match

    new_name = _new_basename_or_stem(target, new_rel)

    inner = new_name
    if fragment:
        inner += fragment
    if alias is not None:
        inner += f"|{alias}"

    return f"[[{inner}]]"


# ---------------------------------------------------------------------------
# Config-path replacement
# ---------------------------------------------------------------------------


def _propose_config_path(
    candidate: Candidate,
    old_rel: str,
    new_rel: str,
    operation: str,
    scope_root: Path,
) -> str | None:
    """Compute the replacement for a config file path literal.

    The surrounding quote style is preserved exactly.  Path-shaped values keep
    their resolution form; bare values are treated as scope-root-relative
    paths.
    """
    match = candidate.match
    quote, inner = _split_quotes(match)

    if inner.startswith("[[") and inner.endswith("]]"):
        new_inner = _propose_wikilink_value(
            inner,
            candidate.target,
            candidate.fragment,
            candidate.alias,
            new_rel,
            operation,
        )
        return f"{quote}{new_inner}{quote}"

    if "/" in inner:
        file_dir = str(Path(candidate.file).parent)
        form = _resolve_form(inner, file_dir, scope_root, old_rel)
        if form is None:
            return None
        new_inner = _compute_path_value(form, file_dir, new_rel, scope_root)
    else:
        # Bare config value = scope-root-relative path.
        new_inner = _compute_path_value("scope-root", "", new_rel, scope_root)

    if new_inner is None:
        return None
    return f"{quote}{new_inner}{quote}"


def _split_quotes(raw: str) -> tuple[str, str]:
    """Return ``(quote_char, unquoted_value)`` for a config literal."""
    stripped = raw.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in ('"', "'"):
        return stripped[0], stripped[1:-1]
    return "", raw


# ---------------------------------------------------------------------------
# Inline-code-path replacement
# ---------------------------------------------------------------------------


def _propose_inline_code_path(
    candidate: Candidate,
    old_rel: str,
    new_rel: str,
    scope_root: Path,
) -> str | None:
    """Compute the replacement for an inline-code path reference.

    ``candidate.match`` is the bare path inside the backticks (the backticks
    themselves are preserved by the act layer, which rewrites only the path).
    The path keeps its resolution form — scope-root-relative or relative to the
    referring file's directory — so the rewrite matches how the reference was
    originally written. Returns ``None`` when the form is genuinely ambiguous,
    leaving the reference surfaced with no proposed rewrite.
    """
    target = candidate.match.strip()
    if "/" not in target:
        return None
    file_dir = str(Path(candidate.file).parent)
    form = _resolve_form(target, file_dir, scope_root, old_rel)
    if form is None:
        return None
    return _compute_path_value(form, file_dir, new_rel, scope_root)


# ---------------------------------------------------------------------------
# Shared path helpers
# ---------------------------------------------------------------------------


def _new_basename_or_stem(original_value: str, new_rel: str) -> str:
    """Return the new basename or stem matching the original value's form."""
    new_path = Path(new_rel)
    if Path(original_value).suffix:
        return new_path.name
    return new_path.stem


def _resolve_form(
    target: str,
    file_dir: str,
    scope_root: Path,
    old_rel: str,
) -> str | None:
    """Determine whether ``target`` matched ``old_rel`` as scope-root-relative or file-relative.

    Returns ``"scope-root"``, ``"file-dir"``, or ``None`` when genuinely
    ambiguous or neither resolution matches.  When the referring file sits at
    the scope root the two forms coincide, so scope-root-relative is preferred.
    """
    root = scope_root.expanduser().resolve()

    scope_resolved = _resolve_path(target, root, root)
    file_resolved = _resolve_path(target, root / file_dir, root)

    scope_matches = scope_resolved is not None and _case_equal(scope_resolved, old_rel)
    file_matches = file_resolved is not None and _case_equal(file_resolved, old_rel)

    same_resolution = scope_resolved is not None and scope_resolved == file_resolved

    if scope_matches and file_matches and not same_resolution:
        return None
    if scope_matches:
        return "scope-root"
    if file_matches:
        return "file-dir"
    return None


def _resolve_path(target: str, base: Path, scope_root: Path) -> str | None:
    """Return the scope-relative path that ``target`` names under ``base``, or None."""
    try:
        resolved = (base / target).resolve()
        root = scope_root.expanduser().resolve()
        if resolved == root or root in resolved.parents:
            return _rel(resolved, root)
    except (OSError, ValueError, RuntimeError):
        pass
    return None


def _compute_path_value(
    form: str,
    file_dir: str,
    new_rel: str,
    scope_root: Path,
) -> str | None:
    """Compute the new path string in the requested resolution form."""
    root = scope_root.expanduser().resolve()
    new_abs = (root / new_rel).resolve()

    if form == "scope-root":
        return _rel(new_abs, root)

    if form == "file-dir":
        return _compute_relative_path(file_dir, new_rel, scope_root)

    return None


def _compute_relative_path(
    file_dir: str,
    new_rel: str,
    scope_root: Path,
) -> str | None:
    """Return ``new_rel`` relative to ``file_dir`` (POSIX, with ``../`` if needed)."""
    root = scope_root.expanduser().resolve()
    ref_dir = (root / file_dir).resolve()
    new_abs = (root / new_rel).resolve()

    try:
        rel = os.path.relpath(new_abs, ref_dir)
    except ValueError:
        return None

    return rel.replace(os.sep, "/")
