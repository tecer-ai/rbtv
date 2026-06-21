#!/usr/bin/env python3
"""RBTV slide-library engine — assembles single-file HTML decks."""

import argparse
import html
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Constants ──
ENGINE_VERSION = "1.2"
SUPPORTED_CONVENTION_MAJOR = 1
ENGINE_TARGET_MINOR = 0
MANIFEST_COLUMNS = [
    "id", "file", "section", "title", "audience",
    "lang", "kind", "summary", "assets", "provenance",
]
STATUS_COLUMN = "status"
STATUS_VALUES = ("to-review", "ready")

TOKEN_RE = re.compile(r"\{\{[^}]+\}\}")
SLIDE_NUMBER_RE = re.compile(r'(<div class="slide-number">)\{\{N\}\}(</div>)')

# Shared class contract for multi-theme libraries (library-scoped, v1).
# Every theme in a library that declares themes[] MUST define every selector
# and :root token in this set. Presence-check only.
CONTRACT_V1 = frozenset({
    # Tokens
    "--bg", "--bg-soft", "--fg", "--fg-invert", "--muted", "--brand",
    "--client-accent",
    # Page / base
    "@page", "body",
    # Slide + variants
    ".slide", ".slide--soft", ".slide--dark", ".slide--cover", ".slide--closing",
    ".dark-bg-overlay",
    # Header
    ".slide-header", ".kicker", ".slide-title", ".slide-subtitle",
    # Body / grid / cards
    ".slide-body", ".grid-3", ".card", ".card-icon", ".card-title", ".card-body",
    # Asides
    ".aside-note", ".dark-callout",
    # Cover
    ".cover-logos", ".cover-mark", ".cover-logos-sep", ".cover-client",
    ".cover-title", ".cover-subtitle", ".cover-date",
    # Divider / proof / closing
    ".divider-statement", ".sources-line", ".partner-mark",
    ".closing-statement", ".closing-contacts", ".closing-wordmark",
    # Chrome
    ".slide-number",
})

# Role-token contract for multi-theme libraries (library-scoped, v2).
# v2 themes are PURE SKINS: they define only design-role :root tokens (no
# structural selectors). A theme that declares contract_version "2.0" MUST
# define every token in this set; a v2 theme that also leaks a structural
# selector (a `.class`, an element rule) draws a warning (not an error).
# Presence-check only — token VALUES are free to differ between themes. The
# names below are generic design ROLES (no instance palette): field/stage are
# page surfaces, ink-1..4 are foreground ramps, accent* the brand family,
# surface* the card/panel layers, hairline* the borders, texture/scrim the
# overlays, positive/negative the semantic colors, font-* the type roles, and
# radius*/hairline-w the shape roles.
ROLE_CONTRACT_V2 = frozenset({
    "--field",
    "--field-2",
    "--stage",
    "--ink-1",
    "--ink-2",
    "--ink-3",
    "--ink-4",
    "--accent",
    "--accent-ink",
    "--accent-ink-soft",
    "--accent-soft",
    "--accent-soft-2",
    "--accent-border",
    "--highlight",
    "--surface",
    "--surface-2",
    "--hairline",
    "--hairline-strong",
    "--edge-accent",
    "--shadow-panel",
    "--shadow-card",
    "--texture",
    "--texture-hero",
    "--scrim",
    "--scrim-hero",
    "--positive",
    "--positive-glow",
    "--negative",
    "--font-display",
    "--font-body",
    "--font-mono",
    "--radius",
    "--radius-lg",
    "--hairline-w",
})

# Tokens an assembly injects per-deck (never declared by a theme). They are
# always legitimate in a skin property and MUST never be flagged as undefined.
INJECTED_TOKENS = frozenset({"--client-accent"})

LIBRARY = Path(__file__).resolve().parent


# ═══════════════════════════════════════════════════════════════════════════════
# Theme resolution
# ═══════════════════════════════════════════════════════════════════════════════

def resolve_theme(library_data, requested_theme=None):
    """Resolve a theme name to its file path and contract version."""
    theme_name = (
        requested_theme
        if requested_theme is not None
        else library_data.get("default_theme", "default")
    )

    if theme_name == "default":
        theme_path = LIBRARY / "theme.css"
        if not theme_path.exists():
            die("theme.css not found")
        theme_contract = library_data.get("contract_version", "1.0")
        return theme_name, theme_path, theme_contract

    entry = None
    for t in library_data.get("themes", []):
        if t.get("name") == theme_name:
            entry = t
            break

    if entry is not None:
        theme_file = entry.get("file", f"themes/{theme_name}.css")
        theme_contract = entry.get("contract_version", "1.0")
    else:
        theme_file = f"themes/{theme_name}.css"
        theme_contract = "1.0"

    theme_path = LIBRARY / theme_file
    if not theme_path.exists():
        die(f"Theme not found: '{theme_name}' (tried {theme_path})")

    return theme_name, theme_path, theme_contract

JSON_MODE = False


class EngineDie(Exception):
    pass


def die(message):
    if JSON_MODE:
        raise EngineDie(message)
    print("ERROR: " + message, file=sys.stderr)
    sys.exit(1)


def warn(message):
    print("WARNING: " + message, file=sys.stderr)


def parse_css_members(css_text):
    """Return the set of defined selector heads and :root custom properties."""
    cleaned = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    members = set()

    # :root custom properties
    for root_block in re.finditer(r":root\s*\{([^}]*)\}", cleaned, re.DOTALL):
        for token_match in re.finditer(r"--([A-Za-z0-9_-]+)\s*:", root_block.group(1)):
            members.add(f"--{token_match.group(1)}")

    # Selector heads: extract the text preceding each top-level '{'.
    selector_groups = []
    depth = 0
    last = 0
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                selector_groups.append(cleaned[last:i])
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last = i + 1

    for selector_group in selector_groups:
        selector_group = selector_group.strip()
        if not selector_group:
            continue
        if selector_group.startswith("@"):
            if selector_group.startswith("@page"):
                members.add("@page")
            continue
        for selector in selector_group.split(","):
            selector = selector.strip()
            if not selector or selector == "*":
                continue
            for cls in re.finditer(r"\.([A-Za-z0-9_-]+)", selector):
                members.add(f".{cls.group(1)}")
            type_match = re.match(r"([A-Za-z][A-Za-z0-9]*)", selector)
            if type_match:
                members.add(type_match.group(1))

    return members


def contract_required_members(contract_version):
    """Resolve a contract_version to its required-member set + a human label.

    Returns (members, label). An unknown version returns (None, None) so the
    caller can raise a loud error naming the offending version."""
    if contract_version == "1.0":
        return CONTRACT_V1, "shared class contract v1"
    if contract_version == "2.0":
        return ROLE_CONTRACT_V2, "role-token contract v2"
    return None, None


def lint_themes_contract(library_data):
    """Return (errors, warnings) for theme.css + every themes[].file.

    Each theme is validated against ITS OWN contract_version: the default theme
    (theme.css) uses the library's top-level contract_version (default "1.0");
    each themes[] entry uses its own contract_version (default "1.0"). A v2
    role-only theme that leaks a structural selector draws a warning."""
    errors = []
    warnings = []
    themes = library_data.get("themes", [])
    if not themes:
        return errors, warnings

    theme_entries = [
        ("default", LIBRARY / "theme.css",
         library_data.get("contract_version", "1.0"))
    ]
    for t in themes:
        name = t.get("name")
        file_ = t.get("file", f"themes/{name}.css")
        theme_entries.append((name, LIBRARY / file_, t.get("contract_version", "1.0")))

    for theme_name, theme_path, contract_version in theme_entries:
        if not theme_path.exists():
            errors.append(f"Theme '{theme_name}' file not found: {theme_path}")
            continue
        css = theme_path.read_text(encoding="utf-8")
        members = parse_css_members(css)
        required, contract_label = contract_required_members(contract_version)
        if required is None:
            errors.append(
                f"Theme '{theme_name}' declares unknown contract_version: "
                f"{contract_version}"
            )
            continue
        if contract_version == "2.0":
            leaked = sorted(m for m in members if not m.startswith("--"))
            if leaked:
                warnings.append(
                    f"Theme '{theme_name}' is contract 2.0 (role-only) but "
                    f"includes structural CSS members: {', '.join(leaked)}"
                )
        missing = sorted(required - members)
        if missing:
            errors.append(
                f"Theme '{theme_name}' fails the {contract_label} — "
                f"missing: {', '.join(missing)}"
            )
    return errors, warnings


# ═══════════════════════════════════════════════════════════════════════════════
# No-literal-skin lint
# ═══════════════════════════════════════════════════════════════════════════════

# Skin properties paint the deck's visual identity — a literal value here defeats
# re-skinnability (a theme swap cannot reach a hardcoded color). border-* shorthand
# variants are covered by the `border-` prefix test in _skin_property.
SKIN_PROPERTIES = frozenset({
    "color",
    "background",
    "background-color",
    "background-image",
    "border",
    "border-color",
    "border-top",
    "border-right",
    "border-bottom",
    "border-left",
    "box-shadow",
    "fill",
    "stroke",
    "outline",
    "outline-color",
})
COLOR_FUNCTION_RE = re.compile(r"\b(?:rgb|rgba|hsl|hsla)\s*\(", re.IGNORECASE)
HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
# CSS named colors are literal skin values too (e.g. `color:white`). They defeat
# re-skinnability exactly like a hex does, so a skin property whose value names a
# color verbatim is flagged. The allowed CSS-wide keywords (transparent/inherit/
# currentColor/none/unset/initial/revert) are NOT colors and are exempted in
# _literal_skin_reason; they are deliberately absent from this set. Matched as
# whole words only, AFTER var()/url() spans are blanked, so a custom property or
# asset path that merely contains a color word never false-trips.
NAMED_COLORS = frozenset({
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige",
    "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown",
    "burlywood", "cadetblue", "chartreuse", "chocolate", "coral",
    "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
    "darkgoldenrod", "darkgray", "darkgreen", "darkgrey", "darkkhaki",
    "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred",
    "darksalmon", "darkseagreen", "darkslateblue", "darkslategray",
    "darkslategrey", "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
    "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite",
    "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod",
    "gray", "green", "greenyellow", "grey", "honeydew", "hotpink", "indianred",
    "indigo", "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
    "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
    "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
    "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow",
    "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
    "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen",
    "mediumslateblue", "mediumspringgreen", "mediumturquoise",
    "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin",
    "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange",
    "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise",
    "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum",
    "powderblue", "purple", "rebeccapurple", "red", "rosybrown", "royalblue",
    "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna",
    "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow",
    "springgreen", "steelblue", "tan", "teal", "thistle", "tomato",
    "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow",
    "yellowgreen",
})
VAR_OR_URL_SPAN_RE = re.compile(r"(?:var|url)\s*\([^)]*\)", re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z][A-Za-z-]*")
# var(--token) reference — group(1) is the token name (with leading --).
VAR_TOKEN_RE = re.compile(r"var\(\s*(--[A-Za-z0-9_-]+)")
STYLE_BLOCK_RE = re.compile(r"<style\b[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
INLINE_STYLE_RE = re.compile(
    r"\sstyle\s*=\s*([\"'])(.*?)\1", re.DOTALL | re.IGNORECASE
)


def _preserve_newlines_blank(match):
    text = match.group(0)
    return "".join("\n" if ch == "\n" else " " for ch in text)


def _strip_root_and_comments(css_text):
    """Blank out :root{...} blocks and /* */ comments (newlines preserved) so the
    declaration scan never flags literal token DEFINITIONS inside :root."""
    no_root = re.sub(
        r":root\s*\{([^}]*)\}",
        _preserve_newlines_blank,
        css_text,
        flags=re.DOTALL,
    )
    return re.sub(r"/\*.*?\*/", _preserve_newlines_blank, no_root, flags=re.DOTALL)


def _skin_property(prop):
    prop = prop.strip().lower()
    return prop in SKIN_PROPERTIES or prop.startswith("border-")


def _color_function_has_bare_literal(value):
    """True if any rgb/rgba/hsl/hsla(...) call in value carries no var() — i.e. it
    spells out bare numeric channels rather than referencing a token."""
    for match in COLOR_FUNCTION_RE.finditer(value):
        depth = 0
        end = len(value)
        for i in range(match.end() - 1, len(value)):
            ch = value[i]
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if "var(" not in value[match.start():end]:
            return True
    return False


def _literal_skin_reason(value, inline=False, prop="", allowed_tokens=None):
    """Return a reason string when value is a literal/undefined-token skin value,
    else None. allowed_tokens is the legitimate var() role set; a var(--X) used in
    a skin property whose --X is NOT in that set is flagged 'undefined role token'.
    A None allowed_tokens disables the undefined-token check (any var() passes)."""
    stripped = value.strip()
    lower = stripped.lower()
    if lower in {"transparent", "inherit", "currentcolor", "none", "unset",
                 "initial", "revert"}:
        return None
    if inline and prop == "background-image" and "url(" in lower and "var(" not in lower:
        return "literal inline background image"
    # Undefined / old role token: any var(--X) where --X is not a known role.
    # GENERIC — derived from the active contract, never a hardcoded palette.
    if allowed_tokens is not None:
        for token in VAR_TOKEN_RE.findall(stripped):
            if token not in allowed_tokens:
                return f"undefined role token {token}"
    if HEX_COLOR_RE.search(stripped):
        return "literal hex color"
    if _color_function_has_bare_literal(stripped):
        return "literal color function"
    # Named CSS colors (color:white) are literal skin values; flag them after
    # blanking var()/url() spans so a custom property or asset path containing a
    # color word is never matched.
    outside = VAR_OR_URL_SPAN_RE.sub(" ", stripped)
    for word in WORD_RE.findall(outside):
        if word.lower() in NAMED_COLORS:
            return "literal named color"
    return None


def _lint_css_declarations(css_text, base_line=1, inline=False, allowed_tokens=None):
    errors = []
    scanned = _strip_root_and_comments(css_text) if not inline else css_text
    for match in re.finditer(r"([A-Za-z-]+)\s*:\s*([^;{}]+)", scanned):
        prop = match.group(1).strip().lower()
        value = match.group(2).strip()
        if not _skin_property(prop):
            continue
        reason = _literal_skin_reason(
            value, inline=inline, prop=prop, allowed_tokens=allowed_tokens
        )
        if reason:
            line = base_line + scanned[:match.start()].count("\n")
            errors.append(f"approx-line {line}  {prop}: {value} ({reason})")
    return errors


def lint_no_literal_skin(text, is_html, allowed_tokens=None):
    """Scan text for literal skin values in skin properties.

    is_html → scan every <style>...</style> block and inline style="..." attribute;
    otherwise scan the whole text as a CSS file. allowed_tokens (the active role
    set ∪ injected tokens) enables the GENERIC undefined-role-token check; when
    None, var() references are not checked for definedness."""
    errors = []
    if is_html:
        for block in STYLE_BLOCK_RE.finditer(text):
            base_line = 1 + text[:block.start(1)].count("\n")
            errors.extend(_lint_css_declarations(
                block.group(1), base_line=base_line, allowed_tokens=allowed_tokens
            ))
        for inline in INLINE_STYLE_RE.finditer(text):
            base_line = 1 + text[:inline.start(2)].count("\n")
            errors.extend(
                _lint_css_declarations(
                    inline.group(2),
                    base_line=base_line,
                    inline=True,
                    allowed_tokens=allowed_tokens,
                )
            )
    else:
        errors.extend(_lint_css_declarations(text, allowed_tokens=allowed_tokens))
    return errors


# ═══════════════════════════════════════════════════════════════════════════════
# Parsing
# ═══════════════════════════════════════════════════════════════════════════════

def _split_row(line):
    cells = line.strip().split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def renumber_slides(body):
    counter = {"n": 0}
    def repl(match):
        counter["n"] += 1
        return f"{match.group(1)}{counter['n']}{match.group(2)}"
    return SLIDE_NUMBER_RE.sub(repl, body)


def _find_section_rows(lines, heading):
    """Return list of (line_num, raw_line) for |rows under heading until next ## heading."""
    in_section = False
    rows = []
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped == heading:
                in_section = True
            else:
                if in_section:
                    break
            continue
        if in_section and "|" in line:
            rows.append((line_num, line))
    return rows


def parse_manifest(md_path):
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    slide_rows = _find_section_rows(lines, "## Slides")
    if not slide_rows:
        die("## Slides section has no table rows")
    header_cells = _split_row(slide_rows[0][1])
    if header_cells != MANIFEST_COLUMNS and header_cells != MANIFEST_COLUMNS + [STATUS_COLUMN]:
        die(f"Manifest header mismatch at line {slide_rows[0][0]}")
    data = []
    for line_num, line in slide_rows[2:]:
        cells = _split_row(line)
        data.append({"line_num": line_num, "cells": cells})
    return data


def parse_assets_table(md_path):
    text = md_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    asset_rows = _find_section_rows(lines, "## Assets")
    files = set()
    if len(asset_rows) >= 3:
        for line_num, line in asset_rows[2:]:
            cells = _split_row(line)
            if cells:
                files.add(cells[0].strip('`'))
    return files


def parse_presets(md_path):
    text = md_path.read_text(encoding="utf-8")
    blocks = re.findall(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL)
    presets = []
    for block in blocks:
        p = parse_yaml_subset(block)
        if "preset" in p:
            presets.append(p)
    return presets


# ═══════════════════════════════════════════════════════════════════════════════
# library-YAML subset
# ═══════════════════════════════════════════════════════════════════════════════

def parse_yaml_subset(text):
    """Fresh parser for the library-YAML subset grammar."""
    result = {}
    lines = text.splitlines()
    i = 0
    n = len(lines)
    current_block_key = None

    while i < n:
        raw_line = lines[i]
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m = re.match(r"^(\s*)-\s(.*)$", raw_line)
        if m and current_block_key is not None:
            rest = m.group(2).rstrip()
            result[current_block_key].append(rest)
            i += 1
            continue

        if ":" in stripped:
            colon_idx = stripped.index(":")
            key = stripped[:colon_idx].strip()
            after = stripped[colon_idx + 1:].strip()

            if not after:
                result[key] = []
                current_block_key = key
            elif after.startswith("["):
                flow_text = after
                while i < n and "]" not in flow_text:
                    i += 1
                    if i < n:
                        next_raw = lines[i]
                        if next_raw.strip().startswith("#"):
                            continue
                        flow_text += " " + next_raw.strip()
                if "]" not in flow_text:
                    raise ValueError(f"Unterminated flow list for key {key}")
                inner = flow_text[1:flow_text.index("]")]
                elems = []
                for elem in inner.split(","):
                    elem = elem.strip()
                    if elem:
                        if ":" in elem:
                            raise ValueError(f"Flow list element contains ':': {elem}")
                        elems.append(elem)
                result[key] = elems
                current_block_key = None
            elif after.startswith('"') and after.endswith('"') and len(after) >= 2:
                result[key] = after[1:-1]
                current_block_key = None
            else:
                result[key] = after
                current_block_key = None
            i += 1
            continue

        i += 1

    return result


def write_yaml_subset(entry):
    """Writer for the library-YAML subset."""
    lines = []
    for key, value in entry.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: -")
            else:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            s = str(value)
            # Quote scalars that are not simple unquoted YAML tokens
            if not re.match(r'^[A-Za-z0-9_.\-/]+$', s) or s.startswith("#"):
                lines.append(f'{key}: "{s}"')
            else:
                lines.append(f"{key}: {s}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Validation
# ═══════════════════════════════════════════════════════════════════════════════

def validate_library(library_data, manifest_rows, assets_table_files, base_html,
                     check_assets=False, client_logo=None, requested_slide_ids=None):
    errors = []
    warnings = []

    # Version checks
    conv_ver = library_data.get("convention_version", "")
    try:
        parts = conv_ver.split(".")
        conv_major = int(parts[0])
        conv_minor = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        errors.append(f"Invalid convention_version: {conv_ver}")
        conv_major = None
        conv_minor = None

    if conv_major is not None:
        if conv_major != SUPPORTED_CONVENTION_MAJOR:
            errors.append(
                f"Unsupported convention major version: {conv_major}"
            )
        elif conv_minor != ENGINE_TARGET_MINOR:
            warnings.append(
                f"Convention minor version differs: {conv_minor} "
                f"(target: {ENGINE_TARGET_MINOR})"
            )

    lib_engine_ver = library_data.get("engine_version", "")
    if lib_engine_ver != ENGINE_VERSION:
        warnings.append(
            f"Engine version mismatch: library has {lib_engine_ver}, "
            f"engine is {ENGINE_VERSION}"
        )

    sections = library_data.get("sections", [])
    extra_asset_root = library_data.get("extra_asset_root")

    # Contract lint: only for libraries that declare a non-empty themes[]
    contract_errors, contract_warnings = lint_themes_contract(library_data)
    errors.extend(contract_errors)
    warnings.extend(contract_warnings)

    # base.html markers
    for marker in (
        "{{LANG}}", "{{TITLE}}", "/* {{ACCENT_CSS}} */",
        "/* {{THEME_CSS}} */", "<!-- {{SLIDES}} -->",
    ):
        if marker not in base_html:
            errors.append(f"base.html is missing the marker: {marker}")

    seen_ids = set()
    manifest_asset_names = set()

    for row in manifest_rows:
        line_num = row["line_num"]
        cells = row["cells"]

        if len(cells) not in (10, 11):
            id_hint = cells[0] if cells else f"line {line_num}"
            errors.append(
                f"Row {id_hint}: expected 10 or 11 columns, got {len(cells)}"
            )
            continue

        id_, file_, section, title, audience, lang, kind, summary, assets, provenance = cells[:10]
        status_raw = cells[10].strip() if len(cells) == 11 else ""
        status = status_raw if status_raw else "ready"
        if status not in STATUS_VALUES:
            errors.append(
                f"Row {id_}: invalid status '{status_raw}' — "
                f"must be one of {STATUS_VALUES}"
            )

        # Empty required cells
        required = {
            "id": id_, "file": file_, "section": section,
            "title": title, "lang": lang, "kind": kind, "summary": summary,
        }
        for field, val in required.items():
            if not val:
                errors.append(f"Row {id_}: empty required cell '{field}'")

        # Duplicate id
        if id_:
            if id_ in seen_ids:
                errors.append(f"Duplicate id: {id_}")
            seen_ids.add(id_)

        # Kind enum
        if kind and kind not in ("ready", "template"):
            errors.append(f"Row {id_}: invalid kind '{kind}'")

        # Lang format
        if lang and (not lang.islower() or not re.fullmatch(r"[a-z]{2}", lang)):
            errors.append(f"Row {id_}: invalid lang '{lang}'")

        # Section
        if section and section not in sections:
            errors.append(f"Row {id_}: unknown section '{section}'")

        # Fragment purity
        if file_:
            frag_path = LIBRARY / file_
            if frag_path.exists():
                text = frag_path.read_text(encoding="utf-8")
                for tag in ("<head", "<style", "<script", "<html", "<body"):
                    if tag in text:
                        errors.append(
                            f"Row {id_}: fragment contains forbidden tag '{tag}'"
                        )
            else:
                errors.append(
                    f"Row {id_}: fragment file not found: {file_}"
                )

        # Collect asset names for table completeness
        if assets and assets != "-":
            for a in assets.split(","):
                a = a.strip()
                if a and a != "{client-logo}":
                    if a.startswith("@root/"):
                        manifest_asset_names.add(a[6:].split("/")[-1])
                    else:
                        manifest_asset_names.add(a)

        # Per-composition asset checks
        if check_assets and assets and assets != "-":
            if requested_slide_ids is None or id_ in requested_slide_ids:
                for a in assets.split(","):
                    a = a.strip()
                    if not a or a == "-":
                        continue
                    if a == "{client-logo}":
                        if client_logo is None:
                            errors.append(
                                f"Row {id_}: {{client-logo}} requested but "
                                f"--client-logo not provided"
                            )
                        continue
                    if a.startswith("@root/"):
                        if extra_asset_root is None:
                            errors.append(
                                f"Row {id_}: @root/ asset but extra_asset_root is null"
                            )
                        else:
                            src = LIBRARY / extra_asset_root / a[6:]
                            if not src.exists():
                                errors.append(f"Row {id_}: asset not found: {a}")
                    else:
                        src = LIBRARY / "assets" / a
                        if not src.exists():
                            errors.append(f"Row {id_}: asset not found: {a}")

    # Assets-table completeness
    missing_from_table = manifest_asset_names - assets_table_files
    for m in sorted(missing_from_table):
        warnings.append(
            f"Asset '{m}' listed in manifest but not in Assets table"
        )

    return errors, warnings


# ═══════════════════════════════════════════════════════════════════════════════
# Assembly
# ═══════════════════════════════════════════════════════════════════════════════

def assemble_deck(manifest_rows, slide_ids, lang, title, accent, theme_css,
                  base_html, client_logo=None, extra_asset_root=None,
                  theme_name="default", theme_contract="1.0", library_ref=""):
    by_id = {}
    for row in manifest_rows:
        cells = row["cells"]
        if len(cells) in (10, 11):
            by_id[cells[0]] = cells

    fragments = []
    asset_plan = {}  # leaf_name -> source Path

    for sid in slide_ids:
        if sid not in by_id:
            die(f"Slide id not found in manifest: {sid}")
        row = by_id[sid]
        id_, file_, section, title_, audience, lang_, kind, summary, assets, provenance = row[:10]

        frag_path = LIBRARY / file_
        if not frag_path.exists():
            die(f"Fragment file not found: {file_}")
        text = frag_path.read_text(encoding="utf-8")
        fragments.append(text)

        if assets and assets != "-":
            for a in assets.split(","):
                a = a.strip()
                if not a or a == "-":
                    continue
                src = None
                if a == "{client-logo}":
                    if client_logo is None:
                        die("{client-logo} requested but --client-logo not provided")
                    src = Path(client_logo)
                elif a.startswith("@root/"):
                    if extra_asset_root is None:
                        die("@root/ asset requested but extra_asset_root is null")
                    src = LIBRARY / extra_asset_root / a[6:]
                else:
                    src = LIBRARY / "assets" / a

                if src is not None:
                    if not src.exists():
                        die(f"Asset not found: {a}")
                    asset_plan[src.name] = src

    slides_html = "\n".join(fragments)
    slides_html = renumber_slides(slides_html)

    doc = base_html
    for marker in (
        "{{LANG}}", "{{TITLE}}", "/* {{ACCENT_CSS}} */",
        "/* {{THEME_CSS}} */", "<!-- {{SLIDES}} -->",
    ):
        if marker not in doc:
            die(f"base.html is missing the marker: {marker}")

    doc = doc.replace("{{LANG}}", lang)
    doc = doc.replace("{{TITLE}}", html.escape(title))
    if accent:
        accent_css = f":root {{ --client-accent: {accent}; }}"
        doc = doc.replace("/* {{ACCENT_CSS}} */", accent_css)
    else:
        doc = re.sub(
            r"^[ \t]*/\* \{\{ACCENT_CSS\}\} \*/[ \t]*\n",
            "",
            doc,
            count=1,
            flags=re.MULTILINE,
        )
    doc = doc.replace("/* {{THEME_CSS}} */", theme_css)
    doc = doc.replace("<!-- {{SLIDES}} -->", slides_html)

    doc = doc.replace("{{THEME_NAME}}", theme_name)
    doc = doc.replace("{{THEME_CONTRACT}}", theme_contract)
    doc = doc.replace("{{THEME_LIBRARY}}", library_ref)

    return doc, asset_plan


# ═══════════════════════════════════════════════════════════════════════════════
# As-built writer
# ═══════════════════════════════════════════════════════════════════════════════

def build_as_built_entry(out_path, slide_ids, lang, title, accent,
                         client_logo, preset_name, preset_slide_ids):
    now = datetime.now()
    entry = {
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat(timespec="seconds"),
        "output": os.path.relpath(str(out_path), str(LIBRARY)).replace("\\", "/"),
        "slides": slide_ids,
        "lang": lang,
        "title": title if title else "-",
        "accent": accent if accent else "-",
        "client_logo": Path(client_logo).name if client_logo else "-",
        "engine_version": ENGINE_VERSION,
        "preset": preset_name if preset_name else "-",
    }

    if preset_slide_ids is not None:
        if set(slide_ids) == set(preset_slide_ids) and slide_ids != preset_slide_ids:
            entry["order"] = True

    if preset_slide_ids is not None:
        preset_set = set(preset_slide_ids)
        assembled_set = set(slide_ids)
        deviations = []
        for sid in sorted(preset_set - assembled_set):
            deviations.append(f"removed: {sid}")
        for sid in sorted(assembled_set - preset_set):
            deviations.append(f"added: {sid}")
        entry["deviations"] = deviations
    else:
        entry["deviations"] = []

    return entry


def append_as_built(entry):
    as_built_path = LIBRARY / "as-built.md"
    if not as_built_path.exists():
        die("as-built.md not found")

    text = as_built_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    insert_idx = len(lines)
    for i, line in enumerate(lines):
        if line.strip() == "## As-built log":
            insert_idx = i + 1
            break

    slug = Path(entry["output"]).stem
    heading = f"### {entry['date']}-{slug}"
    yaml_block = write_yaml_subset(entry)

    new_lines = [
        "",
        "---",
        "",
        heading,
        "",
        "```yaml",
        yaml_block,
        "```",
    ]

    lines = lines[:insert_idx] + new_lines + lines[insert_idx:]
    as_built_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# Catalog
# ═══════════════════════════════════════════════════════════════════════════════

def generate_catalog(manifest_rows, library_data, base_html, theme_css,
                     theme_name="default", theme_contract="1.0", library_ref=""):
    sections = library_data.get("sections", [])
    default_lang = library_data.get("default_lang", "en")

    by_id = {}
    for row in manifest_rows:
        cells = row["cells"]
        if len(cells) in (10, 11):
            by_id[cells[0]] = cells

    section_map = {s: [] for s in sections}
    for row in manifest_rows:
        cells = row["cells"]
        if len(cells) in (10, 11):
            sec = cells[2]
            if sec in section_map:
                section_map[sec].append(cells)

    fragments = []
    for sec in sections:
        for cells in section_map[sec]:
            id_, file_, section, title, audience, lang, kind, summary, assets, provenance = cells[:10]
            label = f"{id_} · {kind} · {audience} · {lang} · {summary}"
            frag_path = LIBRARY / file_
            if frag_path.exists():
                text = frag_path.read_text(encoding="utf-8")
                fragments.append(f"<!-- {label} -->")
                fragments.append(text)

    slides_html = "\n".join(fragments)
    slides_html = renumber_slides(slides_html)

    doc = base_html
    for marker in (
        "{{LANG}}", "{{TITLE}}", "/* {{ACCENT_CSS}} */",
        "/* {{THEME_CSS}} */", "<!-- {{SLIDES}} -->",
    ):
        if marker not in doc:
            die(f"base.html is missing the marker: {marker}")

    doc = doc.replace("{{LANG}}", default_lang)
    doc = doc.replace("{{TITLE}}", html.escape(library_data.get("name", "Catalog")))
    doc = re.sub(
        r"^[ \t]*/\* \{\{ACCENT_CSS\}\} \*/[ \t]*\n",
        "",
        doc,
        count=1,
        flags=re.MULTILINE,
    )
    doc = doc.replace("/* {{THEME_CSS}} */", theme_css)
    doc = doc.replace("<!-- {{SLIDES}} -->", slides_html)

    doc = doc.replace("{{THEME_NAME}}", theme_name)
    doc = doc.replace("{{THEME_CONTRACT}}", theme_contract)
    doc = doc.replace("{{THEME_LIBRARY}}", library_ref)

    return doc


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    global JSON_MODE
    parser = argparse.ArgumentParser(description="RBTV slide-library engine")
    parser.add_argument("--preset", type=str)
    parser.add_argument("--slides", type=str)
    parser.add_argument("--check", type=str, metavar="FILE")
    parser.add_argument("--catalog", action="store_true")
    parser.add_argument("--catalog-data", action="store_true")
    parser.add_argument("--out", type=str)
    parser.add_argument("--lang", type=str)
    parser.add_argument("--title", type=str)
    parser.add_argument("--accent", type=str)
    parser.add_argument("--client-logo", type=str)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-log", action="store_true")
    parser.add_argument("--theme", type=str)
    parser.add_argument("--library-ref", type=str)
    parser.add_argument("--check-themes", action="store_true")
    parser.add_argument("--lint-no-literal", type=str, metavar="FILE")
    parser.allow_abbrev = False
    args = parser.parse_args()

    JSON_MODE = args.json

    modes = [
        ("preset", args.preset),
        ("slides", args.slides),
        ("check", args.check),
        ("catalog", args.catalog),
        ("catalog-data", args.catalog_data),
        ("check-themes", args.check_themes),
        ("lint-no-literal", args.lint_no_literal),
    ]
    active_modes = [(n, v) for n, v in modes if v is not None and v is not False]

    if len(active_modes) != 1:
        die(
            "Exactly one mode required: --preset, --slides, "
            "--check, --catalog, --catalog-data, --check-themes, "
            "--lint-no-literal"
        )

    mode_name, mode_val = active_modes[0]

    if mode_name in ("preset", "slides") and not args.out:
        die("--out is required for --preset and --slides")

    envelope_mode = mode_name
    if mode_name in ("preset", "slides"):
        envelope_mode = "assemble"
    envelope = {
        "ok": True,
        "mode": envelope_mode,
        "errors": [],
        "warnings": [],
        "unfilled_tokens": [],
        "output": None,
        "assets_copied": [],
        "as_built_entry": None,
        "catalog_data": None,
    }

    try:
        # Hard-fault loads
        library_json_path = LIBRARY / "library.json"
        if not library_json_path.exists():
            die("library.json not found")
        try:
            with open(library_json_path, "r", encoding="utf-8") as f:
                library_data = json.load(f)
        except json.JSONDecodeError as e:
            die(f"Invalid library.json: {e}")

        manifest_path = LIBRARY / "manifest.md"
        if not manifest_path.exists():
            die("manifest.md not found")

        base_html_path = LIBRARY / "base.html"
        if not base_html_path.exists():
            die("base.html not found")
        base_html = base_html_path.read_text(encoding="utf-8")

        manifest_rows = parse_manifest(manifest_path)
        assets_table_files = parse_assets_table(manifest_path)
        presets = (
            parse_presets(LIBRARY / "presets.md")
            if (LIBRARY / "presets.md").exists()
            else []
        )

        # Back-compat: theme.css (the required default) must exist for every
        # mode, exactly as the original unconditional load enforced. Resolve the
        # literal "default" rather than library_data's configured default_theme,
        # so a library whose default_theme names an alternate still dies loudly
        # when theme.css is absent (theme.css stays REQUIRED).
        _, _default_theme_path, _ = resolve_theme(library_data, "default")

        if mode_name == "lint-no-literal":
            lint_path = Path(mode_val)
            if not lint_path.exists():
                die(f"Lint file not found: {mode_val}")
            text = lint_path.read_text(encoding="utf-8")
            is_html = lint_path.suffix.lower() == ".html" or "<style" in text.lower()
            # Derive the legitimate-token allowlist GENERICALLY from the library's
            # role contracts — the union of every declared theme's contract role
            # set (default theme via top-level contract_version, each themes[]
            # entry via its own) plus the per-deck injected tokens. A var(--X) in a
            # skin property is flagged ONLY when --X is in no contract and is not
            # injected — never against a hardcoded palette blocklist.
            allowed_tokens = set(INJECTED_TOKENS)
            contract_versions = {library_data.get("contract_version", "1.0")}
            for t in library_data.get("themes", []):
                contract_versions.add(t.get("contract_version", "1.0"))
            for cv in contract_versions:
                members, _label = contract_required_members(cv)
                if members:
                    allowed_tokens |= members
            errors = lint_no_literal_skin(text, is_html, allowed_tokens=allowed_tokens)
            if errors:
                envelope["ok"] = False
                envelope["errors"] = errors
                if args.json:
                    print(json.dumps(envelope, ensure_ascii=False))
                else:
                    for err in errors:
                        print(f"ERROR: {err}", file=sys.stderr)
                sys.exit(1)
            if args.json:
                print(json.dumps(envelope, ensure_ascii=False))
            else:
                print("OK: no literal skin values found")
            sys.exit(0)

        if mode_name in ("check", "catalog-data", "check-themes"):
            errors, warnings = validate_library(
                library_data,
                manifest_rows,
                assets_table_files,
                base_html,
                check_assets=False,
            )
            envelope["warnings"] = warnings

            if mode_name == "check":
                check_path = Path(mode_val)
                if not check_path.exists():
                    die(f"Check file not found: {mode_val}")
                text = check_path.read_text(encoding="utf-8")
                tokens = sorted(set(TOKEN_RE.findall(text)))
                envelope["unfilled_tokens"] = tokens
                if tokens:
                    errors.append(
                        f"Found {len(tokens)} unfilled tokens: {', '.join(tokens)}"
                    )

            if errors:
                envelope["ok"] = False
                envelope["errors"] = errors
                if args.json:
                    print(json.dumps(envelope))
                else:
                    for e in errors:
                        print("ERROR: " + e, file=sys.stderr)
                sys.exit(1)

            if mode_name == "catalog-data":
                slides = []
                for row in manifest_rows:
                    cells = row["cells"]
                    if len(cells) in (10, 11):
                        id_, file_, section, title, audience, lang, kind, summary, assets, provenance = cells[:10]
                        status_raw = cells[10].strip() if len(cells) == 11 else ""
                        status = status_raw if status_raw else "ready"
                        asset_list = []
                        if assets and assets != "-":
                            asset_list = [
                                a.strip() for a in assets.split(",")
                                if a.strip()
                            ]
                        slides.append({
                            "id": id_,
                            "file": file_,
                            "section": section,
                            "title": title,
                            "audience": audience if audience else "general",
                            "lang": lang,
                            "kind": kind,
                            "summary": summary,
                            "assets": asset_list,
                            "provenance": provenance,
                            "status": status,
                        })
                catalog_presets = []
                for p in presets:
                    catalog_presets.append({
                        "preset": p.get("preset", ""),
                        "slides": p.get("slides", []),
                        "lang": p.get("lang", ""),
                        "title": p.get("title", ""),
                        "audience": p.get("audience", ""),
                    })
                envelope["catalog_data"] = {
                    "name": library_data.get("name", ""),
                    "default_lang": library_data.get("default_lang", ""),
                    "sections": library_data.get("sections", []),
                    "slides": slides,
                    "presets": catalog_presets,
                    "extra_asset_root": library_data.get("extra_asset_root"),
                    "themes": library_data.get("themes", []),
                    "default_theme": library_data.get("default_theme", "default"),
                }

            if args.json:
                print(json.dumps(envelope))
            sys.exit(0)

        # Resolve theme for catalog / assemble modes
        theme_name, theme_path, theme_contract = resolve_theme(
            library_data, args.theme
        )
        theme_css = theme_path.read_text(encoding="utf-8")
        library_ref = args.library_ref or ""

        # Contract guard for multi-theme libraries — scoped by the chosen theme's
        # own contract_version (resolved in resolve_theme above).
        if library_data.get("themes"):
            members = parse_css_members(theme_css)
            required, contract_label = contract_required_members(theme_contract)
            if required is None:
                die(
                    f"Chosen theme '{theme_name}' declares unknown "
                    f"contract_version: {theme_contract}"
                )
            missing = sorted(required - members)
            if missing:
                die(
                    f"Chosen theme '{theme_name}' fails the {contract_label} — "
                    f"missing: {', '.join(missing)}"
                )

        # Determine requested slide ids for per-composition asset checks
        requested_slide_ids = None
        if mode_name == "preset":
            preset = None
            for p in presets:
                if p.get("preset") == mode_val:
                    preset = p
                    break
            if preset is not None:
                requested_slide_ids = preset.get("slides", [])
        elif mode_name == "slides":
            requested_slide_ids = [s.strip() for s in mode_val.split(",") if s.strip()]

        # Assemble and catalog modes: fail-fast validation
        val_errors, val_warnings = validate_library(
            library_data,
            manifest_rows,
            assets_table_files,
            base_html,
            check_assets=(mode_name in ("preset", "slides")),
            client_logo=args.client_logo,
            requested_slide_ids=requested_slide_ids,
        )
        envelope["warnings"] = val_warnings

        if val_errors:
            die(val_errors[0])

        if mode_name == "catalog":
            doc = generate_catalog(
                manifest_rows, library_data, base_html, theme_css,
                theme_name=theme_name,
                theme_contract=theme_contract,
                library_ref=library_ref,
            )
            out = LIBRARY / "catalog.html"
            out.write_text(doc, encoding="utf-8")
            envelope["output"] = str(out)
            if args.json:
                print(json.dumps(envelope))
            sys.exit(0)

        # Assemble: preset or slides
        if mode_name == "preset":
            preset = None
            for p in presets:
                if p.get("preset") == mode_val:
                    preset = p
                    break
            if preset is None:
                die(f"Preset not found: {mode_val}")
            slide_ids = preset.get("slides", [])
            preset_name = mode_val
            preset_slide_ids = slide_ids[:]
            lang = (
                args.lang
                if args.lang
                else (preset.get("lang") or library_data.get("default_lang", "en"))
            )
            title = args.title if args.title else (preset.get("title") or "-")
        else:  # slides
            slide_ids = [s.strip() for s in mode_val.split(",") if s.strip()]
            preset_name = None
            preset_slide_ids = None
            lang = (
                args.lang
                if args.lang
                else library_data.get("default_lang", "en")
            )
            title = args.title if args.title else "-"

        accent = args.accent if args.accent else ""
        extra_asset_root = library_data.get("extra_asset_root")

        doc, asset_plan = assemble_deck(
            manifest_rows,
            slide_ids,
            lang,
            title,
            accent,
            theme_css,
            base_html,
            client_logo=args.client_logo,
            extra_asset_root=extra_asset_root,
            theme_name=theme_name,
            theme_contract=theme_contract,
            library_ref=library_ref,
        )

        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")

        assets_copied = []
        if asset_plan:
            sibling_assets = out.parent / "assets"
            sibling_assets.mkdir(parents=True, exist_ok=True)
            for name, src in sorted(asset_plan.items()):
                dst = sibling_assets / name
                if src.resolve() == dst.resolve():
                    assets_copied.append(name)
                    continue
                shutil.copy2(src, dst)
                assets_copied.append(name)

        entry = build_as_built_entry(
            out,
            slide_ids,
            lang,
            title,
            accent,
            args.client_logo,
            preset_name,
            preset_slide_ids,
        )

        logged = False
        if not args.no_log:
            append_as_built(entry)
            logged = True

        entry["logged"] = logged

        envelope["ok"] = True
        envelope["output"] = str(out)
        envelope["assets_copied"] = assets_copied
        envelope["as_built_entry"] = entry

        tokens = sorted(set(TOKEN_RE.findall(doc)))
        envelope["unfilled_tokens"] = tokens

        if args.json:
            print(json.dumps(envelope))

        sys.exit(0)

    except EngineDie as e:
        envelope["ok"] = False
        envelope["errors"].append(str(e))
        if JSON_MODE:
            print(json.dumps(envelope))
        else:
            print("ERROR: " + str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
