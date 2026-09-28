#!/usr/bin/env python3
"""visual-check — deterministic HTML style checker against brand-pack tokens and a library page-type profile."""

from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

CHECK_IDS = (
    "palette",
    "fonts",
    "sizing",
    "banned-css",
    "token-literals",
    "grid-ceilings",
    "cover-closing",
)

GENERIC_FAMILIES = frozenset(
    {
        "serif",
        "sans-serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-sans-serif",
        "ui-serif",
        "ui-monospace",
        "ui-rounded",
        "emoji",
        "math",
        "fangsong",
        "inherit",
        "initial",
        "unset",
        "revert",
        "revert-layer",
    }
)

COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{3,8})\b|rgba?\(\s*[^)]+\)|hsla?\(\s*[^)]+\)",
    re.I,
)
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]"
)
IDENTITY_PROPS = (
    "background",
    "background-color",
    "color",
    "font-family",
    "font-size",
    "display",
    "justify-content",
    "align-items",
    "text-align",
    "grid-template-columns",
)
SKIN_PROPS = frozenset(
    {
        "color",
        "background",
        "background-color",
        "border-color",
        "outline-color",
        "fill",
        "stroke",
        "stop-color",
        "text-decoration-color",
        "column-rule-color",
    }
)
PRINT_HINTS = ("slide", "page", "cover", "closing", "canvas", "body", "html")
CAPTION_HINTS = (".caption", "figcaption", "small", ".secondary", ".hint", ".node")
ICON_HINTS = ("icon",)
POSITIONED = frozenset({"absolute", "fixed", "relative", "sticky"})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministic HTML style checker. Inputs: HTML artifact, brand-pack "
            "token file, library page-type profile. Floors and ceilings are read "
            "from the profile at run time."
        ),
        epilog="Check ids: " + ", ".join(CHECK_IDS),
    )
    parser.add_argument("--html", required=True, help="HTML artifact path")
    parser.add_argument("--tokens", required=True, help="brand-pack token file")
    parser.add_argument("--profile", required=True, help="library page-type profile")
    args = parser.parse_args(argv)
    try:
        html = Path(args.html).read_text(encoding="utf-8")
        tokens = _load_tokens(Path(args.tokens))
        profile = _load_profile(Path(args.profile))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    doc = _parse_html(html)
    violations = _run_checks(html, doc, tokens, profile)
    json.dump({"violations": violations}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if violations else 0


def _load_tokens(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    colors: dict[str, str] = {}
    for name, spec in (data.get("colors") or {}).items():
        if isinstance(spec, dict) and spec.get("value"):
            colors[name] = str(spec["value"])
    families: list[str] = []
    for spec in (data.get("type") or {}).values():
        if isinstance(spec, dict) and spec.get("value"):
            families.append(str(spec["value"]).strip().strip("'\""))
    allowed = {_norm_color(v) for v in colors.values() if _norm_color(v)}
    return {"families": families, "allowed_colors": allowed}


def _load_profile(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    floors: dict[str, int] = {}
    for match in re.finditer(
        r"^\|\s*([a-z][a-z0-9-]*)\s*\|\s*([0-9]+)\s*\|", text, re.M
    ):
        floors[match.group(1)] = int(match.group(2))
    return {
        "floors": floors,
        "text": text,
        "require_page": "@page" in text,
        "require_print": "@media print" in text,
        "require_tokens": bool(
            re.search(r"token", text, re.I)
            and re.search(r"second token|var\(--token\)|token contract", text, re.I)
        ),
    }


def _norm_color(value: str) -> str | None:
    raw = value.strip()
    hex_match = re.fullmatch(r"#([0-9a-fA-F]{3,8})", raw)
    if hex_match:
        h = hex_match.group(1).lower()
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h[:3])
        else:
            h = h[:6]
        return f"#{h}"
    rgb = re.fullmatch(
        r"rgba?\(\s*([0-9]+)\s*,\s*([0-9]+)\s*,\s*([0-9]+)", raw, re.I
    )
    if rgb:
        return "#{:02x}{:02x}{:02x}".format(
            int(rgb.group(1)), int(rgb.group(2)), int(rgb.group(3))
        )
    return None


def _match_brace(src: str, open_idx: int) -> tuple[str, int]:
    depth = 0
    for idx in range(open_idx, len(src)):
        if src[idx] == "{":
            depth += 1
        elif src[idx] == "}":
            depth -= 1
            if depth == 0:
                return src[open_idx + 1 : idx], idx
    return src[open_idx + 1 :], len(src) - 1


def _split_rules(css: str) -> list[tuple[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[str, str]] = []
    idx = 0
    while idx < len(css):
        if css[idx].isspace():
            idx += 1
            continue
        if css.startswith("@media", idx):
            brace = css.find("{", idx)
            if brace < 0:
                break
            inner, end = _match_brace(css, brace)
            rules.extend(_split_rules(inner))
            idx = end + 1
            continue
        brace = css.find("{", idx)
        if brace < 0:
            break
        sel = css[idx:brace].strip()
        inner, end = _match_brace(css, brace)
        rules.append((sel, inner))
        idx = end + 1
    return rules


def _decls(body: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for part in body.split(";"):
        if ":" not in part:
            continue
        key, val = part.split(":", 1)
        out.append((key.strip().lower(), val.strip()))
    return out


class _Tree(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.roots: list[dict] = []
        self.stack: list[dict] = []
        self.css_chunks: list[str] = []
        self._in_style = False
        self._style: list[str] = []
        self._skip_text = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {k: (v or "") for k, v in attrs}
        node = {"tag": tag, "attrs": ad, "text": "", "children": []}
        if self.stack:
            self.stack[-1]["children"].append(node)
        else:
            self.roots.append(node)
        self.stack.append(node)
        if tag == "style":
            self._in_style = True
            self._style = []
        if tag in {"script", "title"}:
            self._skip_text = True
        if ad.get("style"):
            self.css_chunks.append(f"{tag}[style] {{{ad['style']}}}")
        for key in ("fill", "stroke", "color", "stop-color"):
            if ad.get(key):
                self.css_chunks.append(f"{tag}[{key}] {{{key}:{ad[key]}}}")

    def handle_endtag(self, tag: str) -> None:
        if tag == "style" and self._in_style:
            self.css_chunks.append("".join(self._style))
            self._in_style = False
        if tag in {"script", "title"}:
            self._skip_text = False
        if self.stack:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._style.append(data)
            return
        if self._skip_text:
            return
        if self.stack:
            self.stack[-1]["text"] += data


def _parse_html(html: str) -> dict:
    tree = _Tree()
    tree.feed(html)
    css = "\n".join(tree.css_chunks)
    return {
        "roots": tree.roots,
        "css": css,
        "rules": _split_rules(css),
        "raw": html,
    }


def _walk(nodes: list[dict], fn) -> None:
    for node in nodes:
        fn(node)
        _walk(node["children"], fn)


def _classes(node: dict) -> list[str]:
    return (node["attrs"].get("class") or "").split()


def _sel_has(sel: str, name: str) -> bool:
    return re.search(
        rf"(^|[#.\s,>+~]){re.escape(name)}([^a-zA-Z0-9_-]|$)", sel, re.I
    ) is not None


def _is_generic_family(name: str) -> bool:
    lowered = name.lower().strip()
    if lowered in GENERIC_FAMILIES:
        return True
    if "system" in lowered:
        return True
    return lowered.startswith("-apple-") or lowered.startswith("-webkit-")


def _families(value: str) -> list[str]:
    parts = [p.strip().strip("'\"") for p in value.split(",")]
    return [p for p in parts if p]


def _px(value: str) -> float | None:
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)px", value.strip(), re.I)
    return float(match.group(1)) if match else None


def _column_count(value: str) -> int:
    match = re.match(r"repeat\(\s*(\d+)\s*,", value.strip(), re.I)
    if match:
        return int(match.group(1))
    tracks = [
        tok
        for tok in re.split(r"\s+", value.strip())
        if tok and tok.lower() not in {"none", "auto", "subgrid", "masonry"}
    ]
    return len(tracks)


def _v(check_id: str, location: str, observed: str, expected: str) -> dict:
    return {
        "check_id": check_id,
        "location": location,
        "observed": observed,
        "expected": expected,
    }


def _run_checks(html: str, doc: dict, tokens: dict, profile: dict) -> list[dict]:
    out: list[dict] = []
    out.extend(_check_palette(doc, tokens))
    out.extend(_check_fonts(doc, tokens))
    out.extend(_check_sizing(doc, profile))
    out.extend(_check_banned(html, doc, profile))
    out.extend(_check_token_literals(doc, profile))
    out.extend(_check_grid(doc, profile))
    out.extend(_check_cover_closing(doc))
    return out


def _check_palette(doc: dict, tokens: dict) -> list[dict]:
    found: list[dict] = []
    allowed = tokens["allowed_colors"]
    for sel, body in doc["rules"]:
        if _sel_has(sel, ":root") and re.search(r"gradient\s*\(", body, re.I):
            found.append(
                _v(
                    "palette",
                    sel,
                    "gradient in :root",
                    "no training-mean placeholder gradient in :root",
                )
            )
        for prop, val in _decls(body):
            for raw in COLOR_RE.findall(val):
                norm = _norm_color(raw)
                if not norm:
                    continue
                if norm not in allowed:
                    found.append(
                        _v(
                            "palette",
                            f"{sel} {prop}",
                            raw,
                            "a brand-pack token colour",
                        )
                    )
    return found


def _check_fonts(doc: dict, tokens: dict) -> list[dict]:
    found: list[dict] = []
    pairing = {f.lower() for f in tokens["families"] if f}
    for sel, body in doc["rules"]:
        for prop, val in _decls(body):
            if prop != "font-family":
                continue
            faces = _families(val)
            branded = [f for f in faces if not _is_generic_family(f)]
            if not branded:
                found.append(
                    _v(
                        "fonts",
                        sel,
                        val,
                        "a brand-pack pairing face, not a system-default stack as the only face",
                    )
                )
                continue
            extra = [f for f in branded if f.lower() not in pairing]
            if extra:
                found.append(
                    _v(
                        "fonts",
                        sel,
                        ", ".join(extra),
                        "declared families ⊆ brand-pack pairing",
                    )
                )
    return found


def _check_sizing(doc: dict, profile: dict) -> list[dict]:
    found: list[dict] = []
    floors = profile["floors"]
    min_body = floors.get("min-body-text")
    min_caption = floors.get("min-caption-text")
    min_node = floors.get("min-node-text")
    min_cell = floors.get("min-cell-text")
    min_icon = floors.get("min-icon-size")
    canvas_w = floors.get("canvas-width")
    canvas_h = floors.get("canvas-height")

    def floor_for(sel: str) -> tuple[int | None, str]:
        lowered = sel.lower()
        if min_icon is not None and any(h in lowered for h in ICON_HINTS):
            return min_icon, "min-icon-size"
        if min_cell is not None and re.search(r"\b(td|th|table)\b", lowered):
            return min_cell, "min-cell-text"
        if min_node is not None and any(h in lowered for h in (".node", "node")):
            return min_node, "min-node-text"
        if min_caption is not None and any(h in lowered for h in CAPTION_HINTS):
            return min_caption, "min-caption-text"
        return min_body, "min-body-text"

    for sel, body in doc["rules"]:
        dmap = dict(_decls(body))
        size = dmap.get("font-size")
        if size:
            px = _px(size)
            floor, name = floor_for(sel)
            if px is not None and floor is not None and px < floor:
                found.append(
                    _v(
                        "sizing",
                        f"{sel} font-size",
                        size,
                        f"{name} {floor}px from profile",
                    )
                )
        if canvas_w is not None and "width" in dmap:
            px = _px(dmap["width"])
            if px is not None and any(h in sel.lower() for h in PRINT_HINTS) and px != canvas_w:
                found.append(
                    _v(
                        "sizing",
                        f"{sel} width",
                        dmap["width"],
                        f"canvas-width {canvas_w}px from profile",
                    )
                )
        if canvas_h is not None and "height" in dmap:
            px = _px(dmap["height"])
            if px is not None and any(h in sel.lower() for h in PRINT_HINTS) and px != canvas_h:
                found.append(
                    _v(
                        "sizing",
                        f"{sel} height",
                        dmap["height"],
                        f"canvas-height {canvas_h}px from profile",
                    )
                )
        if min_icon is not None:
            for dim in ("width", "height"):
                if dim in dmap and any(h in sel.lower() for h in ICON_HINTS):
                    px = _px(dmap[dim])
                    if px is not None and px < min_icon:
                        found.append(
                            _v(
                                "sizing",
                                f"{sel} {dim}",
                                dmap[dim],
                                f"min-icon-size {min_icon}px from profile",
                            )
                        )
    return found


def _check_banned(html: str, doc: dict, profile: dict) -> list[dict]:
    found: list[dict] = []

    def on_node(node: dict) -> None:
        cls = " ".join(_classes(node)).lower()
        iconish = "icon" in cls or node["tag"] in {"i"} or node["attrs"].get("role") == "img"
        if iconish and EMOJI_RE.search(node["text"]):
            found.append(
                _v(
                    "banned-css",
                    _locate(node),
                    node["text"].strip(),
                    "no emoji-as-icon characters",
                )
            )

    _walk(doc["roots"], on_node)
    for sel, body in doc["rules"]:
        dmap = dict(_decls(body))
        if "aspect-ratio" in dmap and any(h in sel.lower() for h in PRINT_HINTS):
            found.append(
                _v(
                    "banned-css",
                    sel,
                    f"aspect-ratio: {dmap['aspect-ratio']}",
                    "no aspect-ratio on print-critical nodes",
                )
            )
        pos = dmap.get("position", "").split()[0] if dmap.get("position") else ""
        if pos in POSITIONED and "transform" in dmap:
            found.append(
                _v(
                    "banned-css",
                    sel,
                    f"position:{pos}; transform:{dmap['transform']}",
                    "no transforms on positioned elements",
                )
            )
        if re.search(r"::?before|::?after", sel, re.I):
            content = dmap.get("content", "")
            empty = content in {"", '""', "''", "none"}
            structural = any(
                k in dmap
                for k in (
                    "border",
                    "border-top",
                    "border-bottom",
                    "border-left",
                    "border-right",
                    "height",
                    "width",
                    "background",
                    "background-color",
                )
            )
            if empty and structural:
                found.append(
                    _v(
                        "banned-css",
                        sel,
                        "pseudo-element structural divider",
                        "no pseudo-element structural dividers",
                    )
                )
    if profile["require_page"] and not re.search(r"@page\b", html):
        found.append(
            _v(
                "banned-css",
                "document",
                "missing @page",
                "profile requires an @page block",
            )
        )
    if profile["require_print"] and not re.search(r"@media\s+print\b", html, re.I):
        found.append(
            _v(
                "banned-css",
                "document",
                "missing @media print",
                "profile requires an @media print block",
            )
        )
    return found


def _locate(node: dict) -> str:
    ident = node["attrs"].get("id")
    cls = ".".join(_classes(node))
    if ident:
        return f"{node['tag']}#{ident}"
    if cls:
        return f"{node['tag']}.{cls}"
    return node["tag"]


def _check_token_literals(doc: dict, profile: dict) -> list[dict]:
    if not profile["require_tokens"]:
        return []
    found: list[dict] = []
    for sel, body in doc["rules"]:
        for prop, val in _decls(body):
            if prop.startswith("--"):
                continue
            if prop not in SKIN_PROPS and "shadow" not in prop:
                continue
            for raw in COLOR_RE.findall(val):
                found.append(
                    _v(
                        "token-literals",
                        f"{sel} {prop}",
                        raw,
                        "skin values via var(--token)",
                    )
                )
    return found


def _check_grid(doc: dict, profile: dict) -> list[dict]:
    found: list[dict] = []
    floors = profile["floors"]
    max_cols = floors.get("max-grid-columns")
    max_cards = floors.get("max-cards")
    max_zones = floors.get("max-zones")
    if max_cols is not None:
        for sel, body in doc["rules"]:
            for prop, val in _decls(body):
                if prop != "grid-template-columns":
                    continue
                count = _column_count(val)
                if count > max_cols:
                    found.append(
                        _v(
                            "grid-ceilings",
                            f"{sel} {prop}",
                            str(count),
                            f"max-grid-columns {max_cols} from profile",
                        )
                    )
    cards = []
    zones = []

    def on_node(node: dict) -> None:
        cls = {c.lower() for c in _classes(node)}
        if "card" in cls:
            cards.append(node)
        if "zone" in cls or node["tag"] == "section" and "slide" in cls:
            zones.append(node)

    _walk(doc["roots"], on_node)
    if max_cards is not None and len(cards) > max_cards:
        found.append(
            _v(
                "grid-ceilings",
                ".card",
                str(len(cards)),
                f"max-cards {max_cards} from profile",
            )
        )
    if max_zones is not None and len(zones) > max_zones:
        found.append(
            _v(
                "grid-ceilings",
                "zones",
                str(len(zones)),
                f"max-zones {max_zones} from profile",
            )
        )
    return found


def _rule_props(doc: dict, name: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for sel, body in doc["rules"]:
        if _sel_has(sel, name) and "::" not in sel and ":before" not in sel.lower() and ":after" not in sel.lower():
            for prop, val in _decls(body):
                if prop in IDENTITY_PROPS:
                    props[prop] = val
    return props


def _find_named(doc: dict, names: tuple[str, ...]) -> dict | None:
    hit: dict | None = None

    def on_node(node: dict) -> None:
        nonlocal hit
        if hit is not None:
            return
        cls = {c.lower() for c in _classes(node)}
        ident = (node["attrs"].get("id") or "").lower()
        if cls.intersection(names) or ident in names:
            hit = node

    _walk(doc["roots"], on_node)
    return hit


def _check_cover_closing(doc: dict) -> list[dict]:
    cover = _find_named(doc, ("cover",))
    closing = _find_named(doc, ("closing", "close"))
    if cover is None or closing is None:
        return []
    cover_props = _rule_props(doc, "cover")
    closing_props = _rule_props(doc, "closing")
    if not closing_props:
        closing_props = _rule_props(doc, "close")
    keys = set(cover_props) | set(closing_props)
    found: list[dict] = []
    for key in sorted(keys):
        left = cover_props.get(key)
        right = closing_props.get(key)
        if left != right:
            found.append(
                _v(
                    "cover-closing",
                    key,
                    f"cover={left!s}; closing={right!s}",
                    "cover and closing match on background, type, and layout",
                )
            )
    return found


if __name__ == "__main__":
    sys.exit(main())
