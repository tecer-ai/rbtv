#!/usr/bin/env python3
"""Minimal assemble engine for e2e builder fixtures."""
import argparse
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


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
    with open(os.path.join(HERE, "library.json"), "r", encoding="utf-8") as f:
        lib = json.load(f)
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
        },
        "warnings": [],
    }


def assemble(slide_ids, out_path, lang=None, title=None, accent=None, client_logo=None):
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
    html = html.replace("{{ACCENT_CSS}}", "")
    html = html.replace("{{THEME_CSS}}", "")
    html = html.replace("<!-- {{SLIDES}} -->", "\n".join(slide_html_parts))

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

    # Update as-built.md
    as_built_path = os.path.join(HERE, "as-built.md")
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
    parser.add_argument("--slides")
    parser.add_argument("--out")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--lang")
    parser.add_argument("--title")
    parser.add_argument("--accent")
    parser.add_argument("--client-logo")
    args = parser.parse_args()

    if args.catalog_data:
        result = catalog_data()
    elif args.slides and args.out:
        slide_ids = [s.strip() for s in args.slides.split(",")]
        result = assemble(slide_ids, args.out, lang=args.lang, title=args.title, accent=args.accent, client_logo=args.client_logo)
    else:
        result = {"ok": False, "errors": ["Unknown command"]}

    if args.json:
        print(json.dumps(result))
    else:
        print(result)


if __name__ == "__main__":
    main()
