#!/usr/bin/env python3
"""Minimal assemble engine for e2e builder fixtures."""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT_V1 = frozenset({
    "--bg", "--bg-soft", "--fg", "--fg-invert", "--muted", "--brand",
    "--client-accent", "@page", "body", ".slide", ".slide--soft",
    ".slide--dark", ".slide--cover", ".slide--closing", ".dark-bg-overlay",
    ".slide-header", ".kicker", ".slide-title", ".slide-subtitle",
    ".slide-body", ".grid-3", ".card", ".card-icon", ".card-title",
    ".card-body", ".aside-note", ".dark-callout", ".cover-logos",
    ".cover-mark", ".cover-logos-sep", ".cover-client", ".cover-title",
    ".cover-subtitle", ".cover-date", ".divider-statement", ".sources-line",
    ".partner-mark", ".closing-statement", ".closing-contacts",
    ".closing-wordmark", ".slide-number",
})


def parse_css_members(css_text):
    cleaned = re.sub(r"/\*.*?\*/", "", css_text, flags=re.DOTALL)
    members = set()
    for root_block in re.finditer(r":root\s*\{([^}]*)\}", cleaned, re.DOTALL):
        for token_match in re.finditer(r"--([A-Za-z0-9_-]+)\s*:", root_block.group(1)):
            members.add(f"--{token_match.group(1)}")

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


def lint_theme_css(css_text, theme_name):
    missing = sorted(CONTRACT_V1 - parse_css_members(css_text))
    if not missing:
        return []
    return [
        f"Theme '{theme_name}' fails the shared class contract v1 — "
        f"missing: {', '.join(missing)}"
    ]


def load_library():
    with open(os.path.join(HERE, "library.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_theme(lib, theme_name=None):
    name = theme_name if theme_name is not None else lib.get("default_theme", "default")
    if name == "default":
        rel_file = "theme.css"
        contract = lib.get("contract_version", "1.0")
    else:
        entry = next((t for t in lib.get("themes", []) if t.get("name") == name), None)
        rel_file = entry.get("file", f"themes/{name}.css") if entry else f"themes/{name}.css"
        contract = entry.get("contract_version", "1.0") if entry else "1.0"
    path = os.path.join(HERE, rel_file)
    if not os.path.isfile(path):
        return name, path, contract, None, [f"Theme not found: '{name}' (tried {path})"]
    with open(path, "r", encoding="utf-8") as f:
        return name, path, contract, f.read(), []


def stamp_theme(html, theme_name, theme_contract, library_ref):
    html_attrs = (
        f' data-theme="{theme_name}"'
        f' data-theme-contract="{theme_contract}"'
        f' data-theme-library="{library_ref}"'
    )
    style_attrs = (
        f' data-theme="{theme_name}"'
        f' data-theme-contract="{theme_contract}"'
    )
    if "data-theme=" not in html:
        html = re.sub(r"<html\b", f"<html{html_attrs}", html, count=1)
        html = re.sub(r"<style\b", f"<style{style_attrs}", html, count=1)
    return html


def parse_manifest():
    slides = []
    errors = []
    manifest_path = os.path.join(HERE, "manifest.md")
    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    in_slides = False
    header_found = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## Slides"):
            in_slides = True
            continue
        if in_slides and stripped.startswith("## "):
            break
        if in_slides and stripped.startswith("|") and "---" not in stripped:
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if not header_found:
                # Header row
                expected = ["id", "file", "section", "title", "audience", "lang", "kind", "summary", "assets", "provenance"]
                if len(cells) < len(expected) or any(cells[i] != expected[i] for i in range(len(expected))):
                    errors.append(f"Invalid manifest header: expected {expected}, got {cells}")
                    return slides, errors
                header_found = True
                continue
            if len(cells) >= 10:
                slides.append({
                    "id": cells[0],
                    "file": cells[1],
                    "section": cells[2],
                    "title": cells[3],
                    "audience": cells[4],
                    "lang": cells[5],
                    "kind": cells[6],
                    "summary": cells[7],
                    "assets": [a.strip() for a in cells[8].split(",") if a.strip() and a.strip() != "-"],
                    "provenance": cells[9],
                })
    if in_slides and not header_found:
        errors.append("Missing manifest header in Slides section")
    return slides, errors


def parse_presets():
    presets = []
    presets_path = os.path.join(HERE, "presets.md")
    if not os.path.exists(presets_path):
        return presets
    with open(presets_path, "r", encoding="utf-8") as f:
        content = f.read()
    # Find yaml blocks
    for block in re.finditer(r"```yaml\n(.*?)\n```", content, re.DOTALL):
        yaml_text = block.group(1)
        preset = {}
        slides_match = re.search(r"slides:\s*\[(.*?)\]", yaml_text)
        if slides_match:
            preset["slides"] = [s.strip().strip('"').strip("'") for s in slides_match.group(1).split(",")]
        for key in ("preset", "lang", "title", "audience"):
            m = re.search(rf"{key}:\s*(.+)", yaml_text)
            if m:
                preset[key] = m.group(1).strip()
        if preset.get("preset"):
            presets.append(preset)
    return presets


def catalog_data():
    lib = load_library()
    slides, errors = parse_manifest()
    if errors:
        return {"ok": False, "errors": errors}
    if not os.path.isfile(os.path.join(HERE, "theme.css")):
        return {"ok": False, "errors": ["theme.css not found"]}
    presets = parse_presets()
    return {
        "ok": True,
        "catalog_data": {
            "name": lib.get("name", ""),
            "sections": lib.get("sections", []),
            "slides": slides,
            "presets": presets,
            "themes": lib.get("themes", []),
            "default_theme": lib.get("default_theme", "default"),
        },
        "warnings": [],
    }


def check_theme(path):
    if not os.path.isabs(path):
        path = os.path.join(HERE, path)
    if not os.path.isfile(path):
        return {"ok": False, "errors": [f"Check file not found: {path}"], "warnings": []}
    with open(path, "r", encoding="utf-8") as f:
        css = f.read()
    errors = lint_theme_css(css, os.path.splitext(os.path.basename(path))[0])
    return {"ok": not errors, "errors": errors, "warnings": [], "unfilled_tokens": sorted(set(re.findall(r"\{\{[^}]+\}\}", css)))}


def check_themes():
    lib = load_library()
    errors = []
    for theme in lib.get("themes", []):
        name = theme.get("name", "")
        file_name = theme.get("file", f"themes/{name}.css")
        path = os.path.join(HERE, file_name)
        if not os.path.isfile(path):
            errors.append(f"Theme '{name}' file not found: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            errors.extend(lint_theme_css(f.read(), name))
    return {"ok": not errors, "errors": errors, "warnings": []}


def assemble(slide_ids, out_path, lang=None, title=None, accent=None, client_logo=None, theme=None, library_ref=""):
    lib = load_library()
    theme_name, _theme_path, theme_contract, theme_css, theme_errors = resolve_theme(lib, theme)
    if theme_errors:
        return {"ok": False, "errors": theme_errors}
    if theme_name != "default":
        lint_errors = lint_theme_css(theme_css, theme_name)
        if lint_errors:
            return {"ok": False, "errors": lint_errors}

    slides, errors = parse_manifest()
    if errors:
        return {"ok": False, "errors": errors}
    slide_map = {s["id"]: s for s in slides}

    # Read base.html
    base_path = os.path.join(HERE, "base.html")
    with open(base_path, "r", encoding="utf-8") as f:
        base_html = f.read()

    # Concatenate slide HTML
    slide_html_parts = []
    for sid in slide_ids:
        if sid not in slide_map:
            return {"ok": False, "errors": [f"Slide not found: {sid}"]}
        s = slide_map[sid]
        frag_path = os.path.join(HERE, s["file"])
        with open(frag_path, "r", encoding="utf-8") as f:
            slide_html_parts.append(f.read())

    html = base_html
    html = html.replace("{{LANG}}", lang or "en")
    html = html.replace("{{TITLE}}", title or "Deck")
    # Mirror the canonical engine: base.html carries the MARKED comment tokens
    # /* {{ACCENT_CSS}} */ and /* {{THEME_CSS}} */. Replace the whole comment
    # (not the bare token inside it) so injected CSS lands live, not commented
    # out. When no accent is supplied, strip the accent line entirely.
    if accent:
        html = html.replace(
            "/* {{ACCENT_CSS}} */",
            f":root {{ --client-accent: {accent}; }}",
        )
    else:
        html = re.sub(
            r"^[ \t]*/\* \{\{ACCENT_CSS\}\} \*/[ \t]*\n",
            "",
            html,
            count=1,
            flags=re.MULTILINE,
        )
    html = html.replace("/* {{THEME_CSS}} */", theme_css)
    html = html.replace("<!-- {{SLIDES}} -->", "\n".join(slide_html_parts))
    html = html.replace("{{THEME_NAME}}", theme_name)
    html = html.replace("{{THEME_CONTRACT}}", theme_contract)
    html = html.replace("{{THEME_LIBRARY}}", library_ref)
    html = stamp_theme(html, theme_name, theme_contract, library_ref)

    # Ensure output directory exists
    out_dir = os.path.dirname(out_path)
    os.makedirs(out_dir, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Copy assets
    assets_copied = []
    for sid in slide_ids:
        s = slide_map[sid]
        for asset in s.get("assets", []):
            if asset.startswith("{") and asset.endswith("}"):
                continue  # token like {client-logo}
            src = os.path.join(HERE, "assets", asset)
            if os.path.exists(src):
                dst = os.path.join(out_dir, asset)
                shutil.copy2(src, dst)
                assets_copied.append(asset)

    # Update as-built.md — write into the OUTPUT dir, never the (tracked) library
    # dir, so assembling from a git-tracked fixture library never dirties the tree.
    as_built_path = os.path.join(out_dir, "as-built.md")
    entry = f"- {os.path.basename(out_path)} ({', '.join(slide_ids)})\n"
    if os.path.exists(as_built_path):
        with open(as_built_path, "a", encoding="utf-8") as f:
            f.write(entry)
    else:
        with open(as_built_path, "w", encoding="utf-8") as f:
            f.write("# As-built\n\n" + entry)

    return {
        "ok": True,
        "output": out_path,
        "assets_copied": list(set(assets_copied)),
        "unfilled_tokens": [],
        "as_built_entry": entry.strip(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog-data", action="store_true")
    parser.add_argument("--check")
    parser.add_argument("--check-themes", action="store_true")
    parser.add_argument("--slides")
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--title")
    parser.add_argument("--accent")
    parser.add_argument("--client-logo")
    parser.add_argument("--theme")
    parser.add_argument("--library-ref", default="")
    args = parser.parse_args()

    if args.catalog_data:
        result = catalog_data()
    elif args.check:
        result = check_theme(args.check)
    elif args.check_themes:
        result = check_themes()
    elif args.slides and args.out:
        slide_ids = [s.strip() for s in args.slides.split(",")]
        result = assemble(
            slide_ids,
            args.out,
            lang=args.lang,
            title=args.title,
            accent=args.accent,
            client_logo=args.client_logo,
            theme=args.theme,
            library_ref=args.library_ref,
        )
    else:
        result = {"ok": False, "errors": ["Unknown command"]}

    if args.json:
        print(json.dumps(result))
    else:
        print(result)


if __name__ == "__main__":
    main()
