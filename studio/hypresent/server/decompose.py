"""Pure decompose engine — deck HTML → library fragments + manifest rows, stdlib only.

Conceptual inverse of recompose.py: given a raw on-disk deck source (data-hyp-* attrs
intact) and a set of selected slide ids, this engine splits the deck into clean
<section>-only library fragments, reads each slide's data-hyp-* export metadata into
manifest rows (suggested id, semantic fields, status=to-review), and discovers referenced
assets.

Export-source invariant: the caller MUST supply the raw on-disk deck source, never
the editor serializer output (serializer.js strips every data-hyp-* except data-hyp-agent
on save, which would empty all auto-fill while still passing structurally).

Section-vocabulary guard: data-hyp-section is mapped to a declared section in the
target library's library.json sections list. If no match, a safe declared default is used
and the slide is flagged.

This module is importable headless — no HTTP, no Flask, no server dependency.
"""

import json
import os
import re
import unicodedata
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass
class ManifestRow:
    """One 11-column manifest row (§ 2.2 + status column)."""

    id: str
    file: str          # slides/{id}.html
    section: str
    title: str
    audience: str
    lang: str
    kind: str
    summary: str
    assets: str        # comma-separated filenames or "-"
    provenance: str
    status: str = "to-review"


@dataclass
class SlideExport:
    """Result for one exported slide."""

    slide_index: int           # 0-based position in the deck
    raw_section_html: str      # the raw <section>…</section> span from the deck
    fragment_html: str         # chrome-stripped, export-metadata attrs preserved
    row: ManifestRow
    asset_paths: list[str]     # resolved on-disk paths to copy (may be empty)
    concerns: list[str] = field(default_factory=list)  # per-slide warnings


@dataclass
class DecomposeResult:
    """Return value of decompose_deck()."""

    exports: list[SlideExport]
    concerns: list[str]        # global concerns (missing assets, section mismatches, etc.)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Attributes considered "editing chrome" — stripped from the fragment output.
# data-hyp-* EXPORT attributes (slide-id, section, title, audience, lang,
# summary, kind, provenance) are NOT in this set; they are preserved.
_CHROME_ATTRS = frozenset(
    {
        "data-hyp-hook",
        "data-hyp-region",
        "data-hyp-text",
        "data-hyp-resize",
        "data-hyp-move",
        "data-hyp-decorative",
        "data-hyp-agent",
        "data-hyp-selected",
        "data-hyp-editing",
        "data-hyp-focus",
        "data-hyp-drag",
    }
)

# CSS classes considered editing chrome (present during editing, not in raw source
# normally, but guarded here for safety).
_CHROME_CLASSES = frozenset(
    {
        "hyp-selected",
        "hyp-focused",
        "hyp-dragging",
        "hyp-editing",
    }
)

# Export metadata attributes on <section> that map to manifest columns.
_EXPORT_ATTRS = {
    "data-hyp-slide-id": "id",
    "data-hyp-section": "section",
    "data-hyp-title": "title",
    "data-hyp-audience": "audience",
    "data-hyp-lang": "lang",
    "data-hyp-summary": "summary",
    "data-hyp-kind": "kind",
    "data-hyp-provenance": "provenance",
}

# Allowed audience values (§ 2.2 convention-spec).
_ALLOWED_AUDIENCE = {"prospect", "client", "investor", "general"}

# Allowed kind values.
_ALLOWED_KIND = {"ready", "template"}


# ---------------------------------------------------------------------------
# Section splitting (mirrors recompose.split_sections)
# ---------------------------------------------------------------------------


class DecomposeError(ValueError):
    """Raised when the deck HTML does not conform to the expected structure."""


def split_sections(html: str) -> list[tuple[int, int]]:
    """Return byte spans (start, end) of each top-level <section>…</section>.

    Depth-counts nested <section> tags; ignores tags inside HTML comments.
    Same algorithm as recompose.split_sections — kept as a local copy so
    decompose.py has zero import dependency on recompose.py.
    """
    spans: list[tuple[int, int]] = []
    depth = 0
    in_comment = False
    i = 0
    n = len(html)
    current_start: int | None = None

    while i < n:
        if not in_comment:
            if html.startswith("<!--", i):
                in_comment = True
                i += 4
                continue
        else:
            if html.startswith("-->", i):
                in_comment = False
                i += 3
                continue
            i += 1
            continue

        if html.startswith("<section", i):
            after = i + 8
            if after < n and html[after] in " \t\n>":
                if depth == 0:
                    current_start = i
                depth += 1
                i += 8
                continue

        if html.startswith("</section>", i):
            depth -= 1
            if depth < 0:
                raise DecomposeError("Unexpected </section> — unbalanced tags")
            if depth == 0 and current_start is not None:
                spans.append((current_start, i + 10))
                current_start = None
            i += 10
            continue

        i += 1

    if depth != 0:
        raise DecomposeError("Unbalanced <section> tags")

    return spans


# ---------------------------------------------------------------------------
# Attribute parsing helpers
# ---------------------------------------------------------------------------


class _AttrExtractor(HTMLParser):
    """Extract attributes from the opening tag of the first element."""

    def __init__(self) -> None:
        super().__init__()
        self.attrs: dict[str, str] = {}
        self._done = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._done:
            self.attrs = {k: (v or "") for k, v in attrs}
            self._done = True


def _parse_opening_attrs(section_html: str) -> dict[str, str]:
    """Return the attribute dict of the <section> opening tag."""
    extractor = _AttrExtractor()
    # Feed only the opening tag to keep parsing fast.
    close = section_html.find(">")
    if close == -1:
        return {}
    extractor.feed(section_html[: close + 1])
    return extractor.attrs


# ---------------------------------------------------------------------------
# Chrome stripping
# ---------------------------------------------------------------------------


def _strip_chrome(section_html: str) -> str:
    """Strip editing-chrome attributes from the section HTML.

    Removes attributes listed in _CHROME_ATTRS from ALL tags inside the section.
    Preserves data-hyp-* export metadata attributes.
    Also removes chrome CSS classes (hyp-*) from class= attributes.

    Operates on the raw string — no external HTML parser dependency.
    """
    # Remove chrome attributes: data-hyp-hook="…", data-hyp-region, etc.
    # Pattern matches name="value", name='value', or bare name (boolean attrs).
    def _strip_attr(m: re.Match) -> str:
        tag_content = m.group(0)
        for attr in _CHROME_ATTRS:
            # Remove attr="…" or attr='…' or bare attr
            tag_content = re.sub(
                r'\s+' + re.escape(attr) + r'(?:=["\'][^"\']*["\']|=[^\s>]*)?',
                "",
                tag_content,
            )
        # Remove chrome classes from class="…"
        def _clean_class(cm: re.Match) -> str:
            quote = cm.group(1)
            classes = cm.group(2).split()
            cleaned = [c for c in classes if c not in _CHROME_CLASSES]
            if cleaned:
                return f'class={quote}{" ".join(cleaned)}{quote}'
            return ""  # remove entire class attr if empty

        tag_content = re.sub(
            r'class=(["\'])([^"\']*)\1', _clean_class, tag_content
        )
        return tag_content

    # Match opening tags (not closing, not comments).
    result = re.sub(r"<[a-zA-Z][^>]*>", _strip_attr, section_html)
    return result


# ---------------------------------------------------------------------------
# Asset discovery
# ---------------------------------------------------------------------------

_ASSET_PATTERNS = [
    # src="assets/foo.png" or src='assets/foo.png'
    re.compile(r"""(?:src|href)=["\']assets/([^"\'>\s]+)["\']"""),
    # url('assets/foo.png') or url("assets/foo.png") or url(assets/foo.png)
    re.compile(r"""url\(["\']?assets/([^"\')\s]+)["\']?\)"""),
]


def _discover_assets(section_html: str, assets_dir: Optional[str]) -> tuple[list[str], list[str]]:
    """Discover asset references in the slide HTML.

    Returns:
        found: list of bare filenames that resolve on disk (or all found if assets_dir is None)
        missing: list of bare filenames that were referenced but not found on disk
    """
    referenced: list[str] = []
    for pattern in _ASSET_PATTERNS:
        for m in pattern.finditer(section_html):
            name = m.group(1)
            if name not in referenced:
                referenced.append(name)

    if assets_dir is None:
        return referenced, []

    found = []
    missing = []
    for name in referenced:
        path = os.path.join(assets_dir, name)
        if os.path.isfile(path):
            found.append(name)
        else:
            missing.append(name)
    return found, missing


# ---------------------------------------------------------------------------
# ID helpers
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert text to a kebab-case slug suitable for a slide id."""
    # Normalise unicode, lowercase, replace non-alnum with hyphens, collapse.
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "slide"


def _dedup_id(suggested: str, used: set[str]) -> str:
    """Return a unique id by appending -2, -3, … until no collision."""
    if suggested not in used:
        return suggested
    counter = 2
    while True:
        candidate = f"{suggested}-{counter}"
        if candidate not in used:
            return candidate
        counter += 1


# ---------------------------------------------------------------------------
# Manifest-cell sanitization (round-trip acceptance by assemble.py)
# ---------------------------------------------------------------------------

# assemble.py validates lang with re.fullmatch(r"[a-z]{2}", lang) — exactly two
# lowercase letters. A row whose lang is not that shape is REJECTED at re-assembly,
# breaking the round-trip. The deck authoring standard declares lang as ISO 639-1.
_LANG_RE = re.compile(r"^[a-z]{2}$")


def _normalize_lang(raw: str, default_lang: str) -> tuple[str, bool]:
    """Normalize a data-hyp-lang value to a 2-letter lowercase code.

    Returns (lang, was_normalized). assemble.py REJECTS any lang not matching
    [a-z]{2}, so the engine must emit a conforming value or the round-trip breaks.
    Strategy: lowercase, take the primary subtag (before '-'/'_'), accept if it is
    two letters; otherwise fall back to the library default (then 'en') and flag.
    """
    candidate = (raw or "").strip().lower()
    # Strip region/script subtags: en-US -> en, pt_BR -> pt.
    primary = re.split(r"[-_]", candidate, 1)[0] if candidate else ""
    if _LANG_RE.match(primary):
        return primary, primary != candidate
    fallback = (default_lang or "").strip().lower()
    if not _LANG_RE.match(fallback):
        fallback = "en"
    return fallback, True


def _sanitize_cell(value: str) -> tuple[str, bool]:
    """Make a value safe for a pipe-delimited manifest cell.

    A literal '|' in any cell over-counts the row and makes assemble.py die()
    (convention-spec § 2.1 RV-2: a pipe in a cell is forbidden; the engine is the
    manifest AUTHOR, so it MUST NOT emit one). Replace '|' with '/' and collapse
    embedded newlines to spaces (cells are single physical lines).
    Returns (clean_value, was_changed).
    """
    cleaned = value.replace("|", "/")
    cleaned = re.sub(r"[\r\n]+", " ", cleaned)
    return cleaned, cleaned != value


# ---------------------------------------------------------------------------
# Section vocabulary guard
# ---------------------------------------------------------------------------


def _resolve_section(
    raw_value: str,
    declared_sections: list[str],
) -> tuple[str, bool]:
    """Map raw_value to a declared section.

    Returns (resolved_section, was_remapped).
    was_remapped=True means the raw value was not declared and a default was used.
    """
    if not declared_sections:
        # No library context — accept the raw value as-is (best-effort).
        return raw_value or "general", False

    # Exact match first (case-sensitive per convention-spec RV-4).
    if raw_value in declared_sections:
        return raw_value, False

    # Case-insensitive fallback (helps with minor casing differences).
    lower_map = {s.lower(): s for s in declared_sections}
    if raw_value.lower() in lower_map:
        return lower_map[raw_value.lower()], True

    # No match — use the first declared section as a safe default.
    default = declared_sections[0]
    return default, True


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------


def decompose_deck(
    deck_html: str,
    selected_ids: list[str],
    library_json: Optional[dict] = None,
    deck_assets_dir: Optional[str] = None,
    existing_library_ids: Optional[set[str]] = None,
) -> DecomposeResult:
    """Decompose a raw deck HTML into library fragments + manifest rows.

    Args:
        deck_html: the raw on-disk deck HTML source (data-hyp-* attrs intact).
            NEVER pass serializer output — it strips export metadata.
        selected_ids: data-hyp-slide-id values of slides to export.
            If a slide has no data-hyp-slide-id, its 0-based index (as string)
            is used as a fallback match key.
        library_json: parsed library.json dict for the target library.
            Used to validate section names (the section-vocabulary guard). If None, section names
            are accepted as-is (best-effort mode).
        deck_assets_dir: absolute path to the deck's assets/ directory.
            If supplied, asset discovery checks existence on disk.
            If None, all referenced assets are reported as found.
        existing_library_ids: set of ids already present in the target library.
            Used for id deduplication (C5). If None, no pre-existing ids assumed.

    Returns:
        DecomposeResult with per-slide SlideExport entries and global concerns.
    """
    declared_sections: list[str] = []
    if library_json:
        declared_sections = library_json.get("sections", [])

    spans = split_sections(deck_html)
    if not spans:
        raise DecomposeError("No <section> slides found — not a conforming deck")

    # Build a map: data-hyp-slide-id → (span_index, attrs)
    # Also map str(index) → (span_index, attrs) as fallback.
    id_to_span: dict[str, tuple[int, dict[str, str]]] = {}
    index_to_span: dict[int, tuple[int, dict[str, str]]] = {}

    for span_idx, (start, end) in enumerate(spans):
        section_html = deck_html[start:end]
        attrs = _parse_opening_attrs(section_html)
        slide_id = attrs.get("data-hyp-slide-id", "").strip()
        index_to_span[span_idx] = (span_idx, attrs)
        if slide_id:
            id_to_span[slide_id] = (span_idx, attrs)

    # Resolve selected_ids to (span_index, attrs) pairs.
    resolved: list[tuple[int, dict[str, str]]] = []
    global_concerns: list[str] = []

    for sel in selected_ids:
        if sel in id_to_span:
            resolved.append(id_to_span[sel])
        else:
            # Try numeric index fallback.
            try:
                idx = int(sel)
                if idx in index_to_span:
                    resolved.append(index_to_span[idx])
                else:
                    global_concerns.append(f"Selected id {sel!r} not found in deck (index out of range); skipped.")
            except ValueError:
                global_concerns.append(f"Selected id {sel!r} not found in deck; skipped.")

    # Track used ids for deduplication.
    used_ids: set[str] = set(existing_library_ids or set())

    exports: list[SlideExport] = []

    for span_idx, attrs in resolved:
        start, end = spans[span_idx]
        raw_html = deck_html[start:end]
        per_slide_concerns: list[str] = []

        # --- 1. Chrome stripping (preserve export metadata attrs) ---
        fragment_html = _strip_chrome(raw_html)

        # --- 2. Read export metadata ---
        slide_id_attr = attrs.get("data-hyp-slide-id", "").strip()
        title_attr = attrs.get("data-hyp-title", "").strip()
        section_attr = attrs.get("data-hyp-section", "").strip()
        audience_attr = attrs.get("data-hyp-audience", "").strip()
        lang_attr = attrs.get("data-hyp-lang", "").strip()
        summary_attr = attrs.get("data-hyp-summary", "").strip()
        kind_attr = attrs.get("data-hyp-kind", "").strip()
        provenance_attr = attrs.get("data-hyp-provenance", "").strip()

        metadata_missing = not slide_id_attr and not title_attr and not section_attr

        # --- 3. Derive id ---
        if slide_id_attr:
            # data-hyp-slide-id may carry characters illegal in a kebab-case id /
            # a filename / a manifest cell (spaces, '|', '/'). Slugify only when it
            # is not already a clean key, so a deliberate kebab id is untouched.
            suggested_id = _slugify(slide_id_attr)
            if suggested_id != slide_id_attr:
                per_slide_concerns.append(
                    f"Slide at index {span_idx}: data-hyp-slide-id={slide_id_attr!r} "
                    f"is not a clean kebab-case id; normalized to {suggested_id!r}."
                )
        elif title_attr:
            suggested_id = _slugify(title_attr)
            per_slide_concerns.append(
                f"Slide at index {span_idx}: missing data-hyp-slide-id; derived id from title: {suggested_id!r}."
            )
        else:
            suggested_id = f"slide-{span_idx}"
            per_slide_concerns.append(
                f"Slide at index {span_idx}: missing data-hyp-slide-id and data-hyp-title; using positional id: {suggested_id!r}."
            )

        unique_id = _dedup_id(suggested_id, used_ids)
        if unique_id != suggested_id:
            per_slide_concerns.append(
                f"Slide id {suggested_id!r} collided with an existing id; deduped to {unique_id!r}."
            )
        used_ids.add(unique_id)

        # --- 4. Section guard ---
        resolved_section, was_remapped = _resolve_section(section_attr, declared_sections)
        # Best-effort mode (no library_json) passes the raw section through; sanitize
        # so a '|' in it cannot corrupt the row. With a library_json the value is
        # already a declared section (pipe-free by construction).
        resolved_section, _ = _sanitize_cell(resolved_section)
        if was_remapped:
            concern = (
                f"Slide {unique_id!r}: data-hyp-section={section_attr!r} is not a declared section "
                f"in the target library; mapped to safe default {resolved_section!r}. Human review required."
            )
            per_slide_concerns.append(concern)
            global_concerns.append(concern)

        # --- 5. Semantic field defaults for missing metadata ---
        if metadata_missing:
            per_slide_concerns.append(
                f"Slide {unique_id!r}: no data-hyp-* export metadata found; "
                "falling back to safe defaults. Deck may not be authoring-standard-compliant."
            )

        title = title_attr or f"Slide {span_idx}"
        audience = audience_attr if audience_attr in _ALLOWED_AUDIENCE else "general"
        default_lang = library_json.get("default_lang", "en") if library_json else "en"
        lang, lang_normalized = _normalize_lang(lang_attr, default_lang)
        if lang_normalized and lang_attr:
            concern = (
                f"Slide {unique_id!r}: data-hyp-lang={lang_attr!r} is not a 2-letter "
                f"ISO 639-1 code; normalized to {lang!r} so the row re-assembles."
            )
            per_slide_concerns.append(concern)
            global_concerns.append(concern)
        kind = kind_attr if kind_attr in _ALLOWED_KIND else "ready"
        summary = summary_attr or f"Exported slide {unique_id}."
        provenance = provenance_attr or "-"

        # --- 5b. Sanitize pipe-bearing / multi-line cells (assemble.py rejects a
        # row whose cell count drifts; convention-spec § 2.1 RV-2 forbids '|'). ---
        title, t_changed = _sanitize_cell(title)
        summary, s_changed = _sanitize_cell(summary)
        provenance, p_changed = _sanitize_cell(provenance)
        if t_changed or s_changed or p_changed:
            concern = (
                f"Slide {unique_id!r}: a manifest cell contained a forbidden '|' or "
                "newline; sanitized to keep the row parseable by the assembler."
            )
            per_slide_concerns.append(concern)
            global_concerns.append(concern)

        # --- 6. Asset discovery ---
        found_assets, missing_assets = _discover_assets(raw_html, deck_assets_dir)
        for ma in missing_assets:
            concern = f"Slide {unique_id!r}: asset {ma!r} referenced but not found on disk; skipped."
            per_slide_concerns.append(concern)
            global_concerns.append(concern)

        assets_cell = ", ".join(found_assets) if found_assets else "-"

        # --- 7. Assemble row ---
        row = ManifestRow(
            id=unique_id,
            file=f"slides/{unique_id}.html",
            section=resolved_section,
            title=title,
            audience=audience,
            lang=lang,
            kind=kind,
            summary=summary,
            assets=assets_cell,
            provenance=provenance,
            status="to-review",
        )

        # --- 8. Resolve on-disk asset paths for copying ---
        asset_paths: list[str] = []
        if deck_assets_dir:
            for name in found_assets:
                asset_paths.append(os.path.join(deck_assets_dir, name))

        exports.append(
            SlideExport(
                slide_index=span_idx,
                raw_section_html=raw_html,
                fragment_html=fragment_html,
                row=row,
                asset_paths=asset_paths,
                concerns=per_slide_concerns,
            )
        )

    return DecomposeResult(exports=exports, concerns=global_concerns)


# ---------------------------------------------------------------------------
# Fragment invariant validation
# ---------------------------------------------------------------------------

_FORBIDDEN_TAGS = re.compile(
    r"<(head|style|script|html|body)[\s>]", re.IGNORECASE
)


def validate_fragment(fragment_html: str) -> list[str]:
    """Check that a fragment satisfies the <section>-only invariant (§ 6.3).

    Returns a list of violation strings (empty = valid).
    """
    violations = []
    for m in _FORBIDDEN_TAGS.finditer(fragment_html):
        violations.append(f"Fragment contains forbidden tag: <{m.group(1)}>")
    return violations


# ---------------------------------------------------------------------------
# Manifest row serialisation
# ---------------------------------------------------------------------------


def row_to_markdown(row: ManifestRow) -> str:
    """Render a ManifestRow as a 11-cell Markdown table row.

    Cells are pipe-delimited; each value is stripped and must not contain
    literal '|' (per convention-spec RV-2).  The engine does not escape pipes
    — a pipe in a value is a manifest authoring error.
    """
    cells = [
        row.id,
        row.file,
        row.section,
        row.title,
        row.audience,
        row.lang,
        row.kind,
        row.summary,
        row.assets,
        row.provenance,
        row.status,
    ]
    return "| " + " | ".join(cells) + " |"


# ---------------------------------------------------------------------------
# Library.json loader (convenience for callers)
# ---------------------------------------------------------------------------


def load_library_json(library_dir: str) -> dict:
    """Load and return the parsed library.json from a library directory."""
    path = os.path.join(library_dir, "library.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
