"""Non-code reference matchers for safe-move.

Each matcher scans a ``WalkedFile`` for live-pointer references to ``old`` and
emits a ``Candidate`` record carrying enough information for the classifier
(phase p2-3), replacement computer (p2-4), and hasher (p2-5).

The matchers are syntax-specific and generic — no vault, sb-os, or RBTV
literal is hardcoded.  They operate on the content of scoped text files only.
"""

from __future__ import annotations

import bisect
import os
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from safe_move.scope import ContentProvider, WalkedFile, read_text_safe


class MatchError(Exception):
    """Raised when a matcher encounters an unrecoverable problem."""


@dataclass(frozen=True, slots=True)
class Candidate:
    """One discovered live-pointer reference.

    Fields beyond the contract's per-reference set are structural pieces the
    later phases need.  All file paths are relative to the scope root (POSIX
    separators), matching ``WalkedFile.path`` and the contract ``file`` field.
    """

    # Per-contract fields filled by the matcher.
    file: str  # relative to scope root, POSIX
    line: int  # 1-based
    match: str  # exact matched text as it appears in the file
    context: str  # immediate surrounding text (the line containing the match)
    syntax: str  # one of: wikilink, markdown-link, frontmatter-field, config-path

    # Structural pieces for later phases.
    target: str  # decoded path/basename the reference points at (path-part only)
    fragment: str | None  # anchor/heading/block fragment, e.g. "#h" or "#^id"
    alias: str | None  # wikilink alias, preserved for replacement
    encoding: str  # original link encoding form: plain / url-encoded / angle-bracket
    resolves_to: int  # how many scope files a bare-basename target resolves to

    # Carried scope flags from WalkedFile (no re-walk needed by classifier).
    read_only: bool
    generated: bool
    boundary: Path | None

    # Position of the match within its context line (0-based).  Used to
    # disambiguate multiple identical references on the same line.
    offset: int = 0


# ---------------------------------------------------------------------------
# Note-field keys treated as frontmatter live-pointers.  The design names
# ``area:``, ``related:``, ``up:`` explicitly; a small conservative extension
# covers other path-holding fields seen in the wild without over-declaring.
# ---------------------------------------------------------------------------
FRONTMATTER_NOTE_FIELDS = frozenset(
    {
        "area",
        "related",
        "up",
        "parent",
        "project",
        "source",
        "target",
    }
)

CONFIG_EXTENSIONS = frozenset(
    {
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
    }
)

# Files whose prose may carry inline-code path references (the inline-code-path
# matcher scans only these). Markdown is where this vault writes the majority of
# its cross-references as backtick-wrapped paths.
MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown"})

# Wikilink: optional leading "!" (embed), target, optional #fragment, optional |alias.
_WIKILINK_RE = re.compile(
    r"!?(?P<open>\[\[)"
    r"(?P<target>[^|\]#\r\n]+?)"
    r"(?:#(?P<fragment>[^|\]\r\n]+?))?"
    r"(?:\|(?P<alias>[^\]\r\n]+?))?"
    r"(?P<close>\]\])"
)

# Markdown link: [text](path).  Path may be angle-bracketed or plain/url-encoded.
# A title after the path is ignored.
_MARKDOWN_LINK_RE = re.compile(
    r"\[(?P<text>[^\]\r\n]*)\]"
    r"\("
    r"(?P<path><[^>\r\n]+>|[^)\s\r\n]+)"
    r"(?:\s+[\"'][^\"'\r\n]*[\"'])?"
    r"\)"
)

# Frontmatter key: value or key: [list, ...] on one line.
# Keys may contain hyphens (Obsidian/YAML metadata keys).
_FRONTMATTER_SCALAR_RE = re.compile(r"^([\w-]+):\s*(.*)$")

# JSON string value after a key or inside an array.
_JSON_VALUE_RE = re.compile(r'(?:":\s*|\[\s*)("(?:[^"\\]|\\.)*")')

# YAML / generic key: value
_GENERIC_KV_RE = re.compile(r"^\s*[^#\s][^:#]*:\s*(.+)$")

# TOML / INI key = value
_GENERIC_EQ_RE = re.compile(r"^\s*[^#;\s][^=]*=\s*(.+)$")

# Inline code span on a single line: a backtick run wrapping non-backtick text.
# Used to find path references written as inline code (e.g. `2-areas/x/y.md`).
# Restricted to single-line spans; fenced code blocks use their own delimiters
# and are not matched here.
_INLINE_CODE_RE = re.compile(r"`(?P<code>[^`\r\n]+)`")


def _rel(path: Path, root: Path) -> str:
    """Return ``path`` relative to ``root`` as a POSIX path string."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_old(old: str | Path, scope_root: Path) -> str:
    """Return ``old`` normalized as a POSIX path relative to ``scope_root``.

    Relative ``old`` values are interpreted against ``scope_root`` so that
    callers (including tests) can reason consistently in scope-relative paths.
    """
    resolved_root = scope_root.expanduser().resolve()
    old_path = Path(old).expanduser()
    if not old_path.is_absolute():
        old_path = resolved_root / old_path
    resolved_old = old_path.resolve()
    return _rel(resolved_old, resolved_root)


def _decode_markdown_path(raw: str) -> tuple[str, str, str | None]:
    """Decode a markdown-link path.

    Returns ``(encoding, decoded_path, fragment)``.  ``fragment`` includes the
    leading ``#`` when present.
    """
    raw = raw.strip()
    if raw.startswith("<") and raw.endswith(">"):
        encoding = "angle-bracket"
        decoded = raw[1:-1].strip()
    elif "%" in raw:
        encoding = "url-encoded"
        decoded = urllib.parse.unquote(raw)
    else:
        encoding = "plain"
        decoded = raw

    if "#" in decoded:
        path_part, _, frag = decoded.partition("#")
        fragment = f"#{frag}"
        return encoding, path_part, fragment
    return encoding, decoded, None


def _resolve_target(
    target: str, file_dir: str, scope_root: Path
) -> list[str]:
    """Return normalized POSIX paths (relative to scope root) that ``target`` could name.

    Both scope-root-relative and file-directory-relative resolutions are tried.
    Paths that escape ``scope_root`` are discarded.

    ``scope_root`` MUST already be resolved (callers resolve it once per run).
    Resolution is LEXICAL and PURE-STRING (``os.path`` only, no ``pathlib``):
    the walk skips symlinks and a reference names a logical path, so a per-site
    filesystem ``resolve()`` is unnecessary AND ``Path`` object construction is
    far too costly here — this helper runs millions of times across a real
    scope (every markdown-link, frontmatter value, and config value), so it must
    stay allocation-free. ``_case_equal`` makes the downstream match
    case-insensitive, so the returned strings need only be lexically correct.
    """
    target = target.strip().strip("'\"'")
    if not target:
        return []

    # Fast path — a separator-free, navigation-free value (the overwhelming
    # majority of config and frontmatter values: tags, names, flags) resolves
    # trivially to ``target`` under the root and ``file_dir/target`` under the
    # referring directory, with no os.path.join/normpath (the profiled hotspot
    # at millions of calls across a real scope).
    if "/" not in target and "\\" not in target and target not in (".", ".."):
        if file_dir in ("", "."):
            return [target]
        return sorted({target, f"{file_dir.replace(os.sep, '/')}/{target}"})

    root_str = str(scope_root)
    prefix = root_str + os.sep
    candidates: set[str] = set()

    # Scope-root-relative and referring-file-directory-relative.
    for base in (root_str, os.path.join(root_str, file_dir)):
        try:
            joined = os.path.normpath(os.path.join(base, target))
        except (ValueError, OSError):
            continue
        if joined == root_str:
            candidates.add(".")
        elif joined.startswith(prefix):
            candidates.add(joined[len(prefix):].replace(os.sep, "/"))

    return sorted(candidates)


def _case_equal(a: str, b: str) -> bool:
    return a.lower() == b.lower()


def _basename_set(walked_files: Iterable[WalkedFile]) -> list[str]:
    return [Path(wf.path).name for wf in walked_files]


def _wikilink_target_matches_old(target: str, old_rel: str) -> bool:
    """Return True when a wikilink-style basename/stem target points at old."""
    old_basename = Path(old_rel).name
    old_stem = Path(old_rel).stem if old_basename.lower().endswith(".md") else None
    return _case_equal(target, old_basename) or (
        old_stem is not None and _case_equal(target, old_stem)
    )


def _build_candidate(
    wf: WalkedFile,
    line_no: int,
    context: str,
    syntax: str,
    match: str,
    target: str,
    fragment: str | None,
    alias: str | None,
    encoding: str,
    resolves_to: int,
    offset: int = 0,
) -> Candidate:
    return Candidate(
        file=wf.path,
        line=line_no,
        match=match,
        context=context,
        syntax=syntax,
        target=target,
        fragment=fragment,
        alias=alias,
        encoding=encoding,
        resolves_to=resolves_to,
        offset=offset,
        read_only=wf.read_only,
        generated=wf.generated,
        boundary=wf.boundary,
    )


def _resolve_frontmatter_value(value: str) -> str:
    """Return the path/basename target a frontmatter value names.

    Wikilink-style values such as ``[[old-note]]`` or ``[[old-note#h|a]]``
    are unwrapped to their target so they resolve with the same basename/
    path logic used by the wikilink matcher.
    """
    m = _WIKILINK_RE.fullmatch(value)
    if m:
        return m.group("target").strip()
    return value


# ---------------------------------------------------------------------------
# Target-independent reference-site extraction.
#
# Each extractor scans a file's content ONCE and returns every reference site of
# its syntax, decoupled from any particular ``old`` target. A single pass over
# the haystack then matches all targets against these sites in memory, so a
# folder move (many sub-targets) reads and regex-scans each file once instead of
# once per sub-target. The single-target ``match_*`` functions below are thin
# wrappers that extract then filter, preserving their original behaviour.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _WikilinkSite:
    line_no: int
    context: str
    match: str
    target: str
    fragment: str | None
    alias: str | None
    offset: int
    resolves_to: int


@dataclass(frozen=True, slots=True)
class _MarkdownSite:
    line_no: int
    context: str
    match: str
    decoded_path: str
    fragment: str | None
    encoding: str
    offset: int
    resolved: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _FrontmatterSite:
    line_no: int
    context: str
    raw_value: str
    value: str
    is_wikilink: bool
    offset: int
    resolved: tuple[str, ...]
    basename_resolves_to: int


@dataclass(frozen=True, slots=True)
class _InlineCodeSite:
    line_no: int
    context: str
    match: str
    target: str
    offset: int
    resolved: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ConfigSite:
    line_no: int
    context: str
    raw: str
    value: str
    offset: int
    resolved: tuple[str, ...]


def _line_offset(content: str, start: int) -> int:
    """Return the 0-based column of ``start`` within its line."""
    return start - content.rfind("\n", 0, start) - 1


def _build_line_starts(content: str) -> list[int]:
    """Return the offset where each line begins (line 1 at offset 0).

    Built ONCE per file so a site's line number is an O(log lines) binary
    search instead of ``content.count("\\n", 0, pos)`` (O(pos)) per site —
    which is quadratic on a large link-heavy file scanned for every reference.
    """
    starts = [0]
    idx = content.find("\n")
    while idx != -1:
        starts.append(idx + 1)
        idx = content.find("\n", idx + 1)
    return starts


def _locate(
    content: str, line_starts: list[int], start: int, end: int
) -> tuple[int, int, str]:
    """Return ``(1-based line_no, line_start_offset, line_text)`` for ``[start, end)``.

    Uses the prebuilt ``line_starts`` index (an O(log lines) binary search for the
    line number) instead of rescanning ``content`` from the top per site.
    """
    line_no = bisect.bisect_right(line_starts, start)
    line_start = line_starts[line_no - 1]
    line_end = content.find("\n", end)
    if line_end == -1:
        line_end = len(content)
    return line_no, line_start, content[line_start:line_end]


def _build_resolves_index(basenames: Iterable[str]) -> dict[str, int]:
    """Map lowercased basename/stem -> count of scope files matching it.

    Built ONCE per run so wikilink/frontmatter multiplicity (``resolves_to``)
    is an O(1) lookup instead of an O(basenames) scan per reference site. A
    file contributes to its basename key and its stem key, deduped so a file
    whose stem equals its basename (no extension) counts once — a wikilink
    target matches a file by exact basename or by stem.
    """
    index: dict[str, int] = {}
    for b in basenames:
        for key in {b.lower(), Path(b).stem.lower()}:
            index[key] = index.get(key, 0) + 1
    return index


def _resolves_to(target: str, resolves_index: dict[str, int]) -> int:
    """O(1) ``resolves_to`` lookup for ``target`` against a prebuilt index."""
    return resolves_index.get(target.lower(), 0)


def _extract_wikilink_sites(
    content: str, resolves_index: dict[str, int]
) -> list[_WikilinkSite]:
    """Return every wikilink occurrence in ``content`` (target-independent)."""
    sites: list[_WikilinkSite] = []
    line_starts: list[int] | None = None
    for m in _WIKILINK_RE.finditer(content):
        target = m.group("target").strip()
        if not target:
            continue
        if line_starts is None:
            line_starts = _build_line_starts(content)
        fragment_raw = m.group("fragment")
        line_no, line_start, context = _locate(content, line_starts, m.start(), m.end())
        sites.append(
            _WikilinkSite(
                line_no=line_no,
                context=context,
                match=m.group(0),
                target=target,
                fragment=f"#{fragment_raw}" if fragment_raw else None,
                alias=m.group("alias"),
                offset=m.start() - line_start,
                resolves_to=_resolves_to(target, resolves_index),
            )
        )
    return sites


def _extract_markdown_sites(
    content: str, file_dir: str, scope_root: Path
) -> list[_MarkdownSite]:
    """Return every markdown-link occurrence in ``content`` (target-independent)."""
    sites: list[_MarkdownSite] = []
    line_starts: list[int] | None = None
    for m in _MARKDOWN_LINK_RE.finditer(content):
        encoding, decoded_path, fragment = _decode_markdown_path(m.group("path"))
        if not decoded_path:
            continue
        if line_starts is None:
            line_starts = _build_line_starts(content)
        line_no, line_start, context = _locate(content, line_starts, m.start(), m.end())
        sites.append(
            _MarkdownSite(
                line_no=line_no,
                context=context,
                match=m.group(0),
                decoded_path=decoded_path,
                fragment=fragment,
                encoding=encoding,
                offset=m.start() - line_start,
                resolved=tuple(_resolve_target(decoded_path, file_dir, scope_root)),
            )
        )
    return sites


def _extract_frontmatter_sites(
    content: str, file_dir: str, scope_root: Path, resolves_index: dict[str, int] | None
) -> list[_FrontmatterSite]:
    """Return every frontmatter note-field value in ``content`` (target-independent)."""
    extracted = _extract_frontmatter_values(content)
    if not extracted:
        return []
    lines = content.splitlines()
    sites: list[_FrontmatterSite] = []
    for line_no, key, raw_value in extracted:
        value = _resolve_frontmatter_value(raw_value)
        context = lines[line_no - 1]
        key_pos = context.find(key)
        search_from = key_pos + len(key) if key_pos != -1 else 0
        value_offset = context.find(raw_value, search_from)
        if value_offset == -1:
            value_offset = 0
        sites.append(
            _FrontmatterSite(
                line_no=line_no,
                context=context,
                raw_value=raw_value,
                value=value,
                is_wikilink=bool(_WIKILINK_RE.fullmatch(raw_value)),
                offset=value_offset,
                resolved=tuple(_resolve_target(value, file_dir, scope_root)),
                basename_resolves_to=(
                    _resolves_to(value, resolves_index)
                    if resolves_index is not None
                    else 1
                ),
            )
        )
    return sites


def _extract_inline_code_sites(
    content: str, file_dir: str, scope_root: Path
) -> list[_InlineCodeSite]:
    """Return every inline-code span in ``content`` that holds a path-like value.

    Detects backtick-delimited inline code whose content contains a ``/``
    separator and records its scope/file resolutions so the single-pass matcher
    can tell whether it points at a moved target. Separator-free spans (a bare
    command like ``npx`` or a bare basename) are skipped — only path-shaped
    content is a candidate reference. The ``/`` gate keeps this allocation-light
    on backtick-heavy markdown.
    """
    sites: list[_InlineCodeSite] = []
    line_starts: list[int] | None = None
    for m in _INLINE_CODE_RE.finditer(content):
        inner = m.group("code")
        path = inner.strip()
        if "/" not in path:
            continue
        if line_starts is None:
            line_starts = _build_line_starts(content)
        lead = len(inner) - len(inner.lstrip())
        line_no, line_start, context = _locate(
            content, line_starts, m.start("code"), m.end("code")
        )
        sites.append(
            _InlineCodeSite(
                line_no=line_no,
                context=context,
                match=path,
                target=path,
                offset=m.start("code") + lead - line_start,
                resolved=tuple(_resolve_target(path, file_dir, scope_root)),
            )
        )
    return sites


def _extract_config_sites(
    path: Path, content: str, file_dir: str, scope_root: Path
) -> list[_ConfigSite]:
    """Return every config key/value path in ``content`` (target-independent)."""
    lines = content.splitlines()
    sites: list[_ConfigSite] = []
    for line_no, raw, value, value_col in _extract_config_values(path, content):
        if not value:
            continue
        sites.append(
            _ConfigSite(
                line_no=line_no,
                context=lines[line_no - 1],
                raw=raw,
                value=value,
                offset=value_col,
                resolved=tuple(_resolve_target(value, file_dir, scope_root)),
            )
        )
    return sites


def _wikilink_candidate(wf: WalkedFile, s: _WikilinkSite) -> Candidate:
    return _build_candidate(
        wf, s.line_no, s.context, "wikilink", s.match, s.target,
        s.fragment, s.alias, "plain", s.resolves_to, s.offset,
    )


def _markdown_candidate(wf: WalkedFile, s: _MarkdownSite) -> Candidate:
    return _build_candidate(
        wf, s.line_no, s.context, "markdown-link", s.match, s.decoded_path,
        s.fragment, None, s.encoding, 1, s.offset,
    )


def _frontmatter_candidate(
    wf: WalkedFile, s: _FrontmatterSite, resolves_to: int
) -> Candidate:
    return _build_candidate(
        wf, s.line_no, s.context, "frontmatter-field", s.raw_value, s.value,
        None, None, "plain", resolves_to, s.offset,
    )


def _config_candidate(wf: WalkedFile, s: _ConfigSite) -> Candidate:
    return _build_candidate(
        wf, s.line_no, s.context, "config-path", s.raw, s.value,
        None, None, "plain", 1, s.offset,
    )


def _inline_code_candidate(wf: WalkedFile, s: _InlineCodeSite) -> Candidate:
    return _build_candidate(
        wf, s.line_no, s.context, "inline-code-path", s.match, s.target,
        None, None, "plain", 1, s.offset,
    )


# ---------------------------------------------------------------------------
# Individual matchers
# ---------------------------------------------------------------------------

def match_wikilinks(
    old_rel: str,
    wf: WalkedFile,
    basenames: list[str],
) -> list[Candidate]:
    """Find wikilink references to ``old_rel``.

    Supported forms: ``[[x]]``, ``[[x|alias]]``, ``![[x]]``, ``[[x#h]]``,
    ``[[x#^id]]``.  Resolution is by basename across the scope.
    """
    content = read_text_safe(wf.abs_path)
    if content is None:
        return []
    resolves_index = _build_resolves_index(basenames)
    return [
        _wikilink_candidate(wf, s)
        for s in _extract_wikilink_sites(content, resolves_index)
        if _wikilink_target_matches_old(s.target, old_rel)
    ]


def match_markdown_links(
    old_rel: str,
    wf: WalkedFile,
    scope_root: Path,
) -> list[Candidate]:
    """Find markdown-link references to ``old_rel``.

    Supports plain, URL-encoded, and angle-bracket paths.  The path is decoded
    before matching; the original encoding form is preserved on the candidate.
    """
    content = read_text_safe(wf.abs_path)
    if content is None:
        return []
    root = Path(scope_root).expanduser().resolve()
    file_dir = str(Path(wf.path).parent)
    return [
        _markdown_candidate(wf, s)
        for s in _extract_markdown_sites(content, file_dir, root)
        if any(_case_equal(r, old_rel) for r in s.resolved)
    ]


def _extract_frontmatter_values(content: str) -> list[tuple[int, str, str]]:
    """Return ``(line_no, key, value)`` for frontmatter note-field values.

    Handles one-line scalar values and inline ``[a, b]`` lists.  Multi-line
    YAML lists are parsed as consecutive ``- item`` lines under the current key.
    """
    if not content.startswith("---"):
        return []

    lines = content.splitlines()
    if len(lines) < 2 or lines[0].strip() != "---":
        return []

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return []

    values: list[tuple[int, str, str]] = []
    current_key: str | None = None

    for idx in range(1, end):
        line = lines[idx]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        scalar = _FRONTMATTER_SCALAR_RE.match(stripped)
        if scalar:
            key, raw_value = scalar.group(1), scalar.group(2).strip()
            current_key = key
            if not raw_value:
                continue
            if raw_value.startswith("[") and raw_value.endswith("]"):
                for item in raw_value[1:-1].split(","):
                    item = item.strip().strip("'\"")
                    if item:
                        values.append((idx + 1, key, item))
            else:
                values.append((idx + 1, key, raw_value.strip("'\"")))
        elif current_key and stripped.startswith("-"):
            item = stripped[1:].strip().strip("'\"")
            if item:
                values.append((idx + 1, current_key, item))

    return values


def match_frontmatter_fields(
    old_rel: str,
    wf: WalkedFile,
    scope_root: Path,
    note_fields: Iterable[str] | None = None,
    basenames: list[str] | None = None,
) -> list[Candidate]:
    """Find frontmatter references to ``old_rel``.

    Every frontmatter field is checked — the old key-allowlist is no longer a
    gate.  A candidate is emitted whenever the field's value resolves to
    ``old_rel`` using the same path/basename resolution the other matchers use.
    The ``note_fields`` argument is kept for API compatibility but ignored.
    """
    # note_fields intentionally ignored per D5: every frontmatter field is a
    # potential live pointer; value-resolution (below) gates false positives.
    _ = note_fields

    content = read_text_safe(wf.abs_path)
    if content is None:
        return []
    root = Path(scope_root).expanduser().resolve()
    file_dir = str(Path(wf.path).parent)
    resolves_index = _build_resolves_index(basenames) if basenames is not None else None

    candidates: list[Candidate] = []
    for s in _extract_frontmatter_sites(content, file_dir, root, resolves_index):
        # Values may be paths or bare basenames (treated like wikilinks).
        path_matches = any(_case_equal(r, old_rel) for r in s.resolved)
        # A bare frontmatter value is a reference ONLY by its FORM: a wikilink
        # (``[[x]]``) or a name carrying a file extension (``x.md`` = a file). A
        # plain word with no extension (``tags: decisions``) is a label, not a
        # reference. Values with a path separator — including a trailing ``/``
        # folder — are matched by path above and never need this basename branch.
        basename_allowed = s.is_wikilink or bool(Path(s.value).suffix)
        basename_matches = basename_allowed and _wikilink_target_matches_old(
            s.value, old_rel
        )
        if not (path_matches or basename_matches):
            continue

        # A full-path resolution names exactly one file (resolves_to == 1).  A
        # bare-basename value carries the same basename multiplicity a wikilink
        # does — count it so an ambiguous basename surfaces instead of auto.
        resolves_to = 1 if path_matches else s.basename_resolves_to
        candidates.append(_frontmatter_candidate(wf, s, resolves_to))
    return candidates


def _unquote_value(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        return raw[1:-1]
    return raw


def _extract_config_values(
    path: Path, content: str
) -> list[tuple[int, str, str, int]]:
    """Return ``(line_no, raw_value, decoded_value, value_col)`` for config file values.

    ``value_col`` is the 0-based column where ``raw_value`` starts within the
    line; it lets act replace the value without colliding with the same text
    elsewhere on the line (e.g. a bare basename that is also a substring of the
    key).
    """
    ext = path.suffix.lower()
    values: list[tuple[int, str, str, int]] = []
    lines = content.splitlines()

    if ext == ".json":
        for i, line in enumerate(lines, 1):
            for m in _JSON_VALUE_RE.finditer(line):
                raw = m.group(1)
                values.append((i, raw, _unquote_value(raw), m.start(1)))
        return values

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue

        # key: value (YAML / generic)
        kv = _GENERIC_KV_RE.match(line)
        if kv:
            raw = kv.group(1).strip()
            # Strip inline comment
            comment_pos = raw.find(" #")
            if comment_pos != -1:
                raw = raw[:comment_pos].strip()
            # Group 1 begins after the colon and any whitespace; skip leading
            # whitespace inside the group to reach the actual value text.
            value_col = kv.start(1) + len(kv.group(1)) - len(kv.group(1).lstrip())
            values.append((i, raw, _unquote_value(raw), value_col))
            continue

        # key = value (TOML / INI)
        eq = _GENERIC_EQ_RE.match(line)
        if eq:
            raw = eq.group(1).strip()
            comment_pos = raw.find(" #")
            if comment_pos != -1:
                raw = raw[:comment_pos].strip()
            value_col = eq.start(1) + len(eq.group(1)) - len(eq.group(1).lstrip())
            values.append((i, raw, _unquote_value(raw), value_col))

    return values


def match_config_paths(
    old_rel: str,
    wf: WalkedFile,
    scope_root: Path,
) -> list[Candidate]:
    """Find config-file path values that reference ``old_rel``."""
    if Path(wf.path).suffix.lower() not in CONFIG_EXTENSIONS:
        return []

    content = read_text_safe(wf.abs_path)
    if content is None:
        return []
    root = Path(scope_root).expanduser().resolve()
    file_dir = str(Path(wf.path).parent)
    return [
        _config_candidate(wf, s)
        for s in _extract_config_sites(wf.abs_path, content, file_dir, root)
        if any(_case_equal(r, old_rel) for r in s.resolved)
    ]


def match_inline_code_paths(
    old_rel: str,
    wf: WalkedFile,
    scope_root: Path,
) -> list[Candidate]:
    """Find inline-code path references (``\\`some/dir/file.md\\```) to ``old_rel``.

    Only markdown files are scanned, and only backtick spans whose content
    contains a path separator and resolves to ``old_rel`` are reported. The
    ``inline-code-path`` syntax is not auto-eligible, so the classifier always
    surfaces these — an inline-code path is a hint to the agent, never an
    automatic rewrite.
    """
    if Path(wf.path).suffix.lower() not in MARKDOWN_EXTENSIONS:
        return []
    content = read_text_safe(wf.abs_path)
    if content is None:
        return []
    root = Path(scope_root).expanduser().resolve()
    file_dir = str(Path(wf.path).parent)
    return [
        _inline_code_candidate(wf, s)
        for s in _extract_inline_code_sites(content, file_dir, root)
        if any(_case_equal(r, old_rel) for r in s.resolved)
    ]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def find_candidates(
    old: str | Path,
    walked_files: Iterable[WalkedFile],
    scope_root: str | Path,
    note_fields: Iterable[str] | None = None,
    *,
    provider: ContentProvider | None = None,
) -> list[Candidate]:
    """Return every non-code reference to ``old`` across ``walked_files``."""
    return find_candidates_multi(
        [old], walked_files, scope_root, note_fields, provider=provider
    )[0]


def find_candidates_multi(
    olds: list[str | Path],
    walked_files: Iterable[WalkedFile],
    scope_root: str | Path,
    note_fields: Iterable[str] | None = None,
    *,
    provider: ContentProvider | None = None,
) -> list[list[Candidate]]:
    """Return non-code references for EACH target in ``olds`` (results aligned to it).

    The haystack is read and regex-scanned ONCE; every target is then matched
    against the extracted sites in memory. Equivalent to calling
    ``find_candidates`` once per target, but without re-reading or re-scanning
    the haystack for each — this is what makes a folder move (one sub-target per
    contained file) scan the scope a single time instead of once per file.
    """
    _ = note_fields  # frontmatter ignores the key allowlist (D5); kept for API.
    scope_root_path = Path(scope_root).expanduser().resolve()
    old_rels = [_normalize_old(old, scope_root_path) for old in olds]
    files = list(walked_files)
    basenames = _basename_set(files)
    # Built ONCE (O(basenames)); makes per-site resolves_to an O(1) lookup
    # instead of an O(basenames) scan per reference site across the whole scope.
    resolves_index = _build_resolves_index(basenames)
    if provider is None:
        provider = ContentProvider()

    results: list[list[Candidate]] = [[] for _ in old_rels]

    # Invert the match: build O(1) target lookups ONCE, so each site is matched
    # against the targets in O(1) rather than scanning all targets per site
    # (which made matching O(sites x targets) — the folder-move bottleneck).
    # by_path mirrors _case_equal(resolved, old_rel); by_basename mirrors
    # _wikilink_target_matches_old (basename, or stem when old is a .md file).
    by_path: dict[str, list[int]] = {}
    by_basename: dict[str, list[int]] = {}
    for index, old_rel in enumerate(old_rels):
        by_path.setdefault(old_rel.lower(), []).append(index)
        ob_lower = Path(old_rel).name.lower()
        by_basename.setdefault(ob_lower, []).append(index)
        if ob_lower.endswith(".md"):
            stem_lower = Path(old_rel).stem.lower()
            if stem_lower != ob_lower:
                by_basename.setdefault(stem_lower, []).append(index)

    for wf in files:
        content = provider.get(wf)
        if content is None:
            continue
        file_dir = str(Path(wf.path).parent)
        wl_sites = _extract_wikilink_sites(content, resolves_index)
        md_sites = _extract_markdown_sites(content, file_dir, scope_root_path)
        fm_sites = _extract_frontmatter_sites(
            content, file_dir, scope_root_path, resolves_index
        )
        cfg_sites = (
            _extract_config_sites(wf.abs_path, content, file_dir, scope_root_path)
            if Path(wf.path).suffix.lower() in CONFIG_EXTENSIONS
            else []
        )
        ic_sites = (
            _extract_inline_code_sites(content, file_dir, scope_root_path)
            if Path(wf.path).suffix.lower() in MARKDOWN_EXTENSIONS
            else []
        )
        # Process sites in (wikilink, markdown, frontmatter, config) order so the
        # per-target list order — and thus the post-sort order — is identical to
        # the single-target find_candidates path.
        for s in wl_sites:
            for index in by_basename.get(s.target.lower(), ()):
                results[index].append(_wikilink_candidate(wf, s))
        for s in md_sites:
            matched: set[int] = set()
            for r in s.resolved:
                matched.update(by_path.get(r.lower(), ()))
            for index in matched:
                results[index].append(_markdown_candidate(wf, s))
        for s in fm_sites:
            path_indices: set[int] = set()
            for r in s.resolved:
                path_indices.update(by_path.get(r.lower(), ()))
            for index in path_indices:
                results[index].append(_frontmatter_candidate(wf, s, 1))
            # A bare frontmatter value is a reference ONLY by its FORM: a wikilink
            # (``[[x]]``) or a name carrying a file extension (``x.md``). A plain
            # word with no extension (``tags: decisions``) is a label, not a
            # reference. (Separator / trailing-``/`` values are matched by path
            # above.) This is the folder-move false-positive fix.
            if s.is_wikilink or bool(Path(s.value).suffix):
                for index in by_basename.get(s.value.lower(), ()):
                    if index not in path_indices:
                        results[index].append(
                            _frontmatter_candidate(wf, s, s.basename_resolves_to)
                        )
        for s in cfg_sites:
            matched = set()
            for r in s.resolved:
                matched.update(by_path.get(r.lower(), ()))
            for index in matched:
                results[index].append(_config_candidate(wf, s))
        for s in ic_sites:
            matched = set()
            for r in s.resolved:
                matched.update(by_path.get(r.lower(), ()))
            for index in matched:
                results[index].append(_inline_code_candidate(wf, s))

    # Stable ordering: file, line, match text (matches find_candidates).
    for out in results:
        out.sort(key=lambda c: (c.file, c.line, c.match))
    return results
