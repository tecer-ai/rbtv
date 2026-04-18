#!/usr/bin/env python3
"""
Generic config-driven markdown-to-DOCX converter.

Usage:
    python md-to-docx.py input.md output.docx --style document-style.yaml [--workspace-root /path/to/root]

Requires: python-docx, PyYAML
    pip install python-docx pyyaml
"""

import sys
import re
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Run: pip install pyyaml")
    sys.exit(1)

from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor, Emu
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


# ---------------------------------------------------------------------------
# Defaults (equivalent to the original Tecer constants)
# ---------------------------------------------------------------------------

DEFAULTS = {
    "font": {
        "family": "Outfit",
        "monospace": "Space Mono",
        "sizes": {"body": 10, "h1": 16, "h2": 13, "h3": 11, "small": 8},
        "line_spacing": 1.15,
    },
    "colors": {
        "primary": "#1B2B4B",
        "heading": "#1B2B4B",
        "table": {
            "header_bg": "E8EDF5",
            "border": "8DA0C0",
            "alt_row": "F5F7FA",
        },
    },
    "logo": {
        "path": "",
        "width_cm": 3,
        "position": "header-right",
        "fallback_text": "",
    },
    "page": {
        "size": "letter",
        "margins": {"top": 2.5, "bottom": 2.5, "left": 2.5, "right": 2.5},
    },
    "signature": {
        "enabled": True,
        "header_keywords": ["assinatura", "signature"],
        "date_label": "Data",
    },
}


def deep_merge(base, override):
    """Recursively merge override into a copy of base."""
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_style(style_path, workspace_root=None):
    """Load style config from YAML, merged over defaults."""
    with open(style_path, "r", encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}
    config = deep_merge(DEFAULTS, user_config)

    # Resolve logo path relative to workspace root (or YAML file's directory as fallback)
    logo_rel = config["logo"].get("path", "")
    if logo_rel:
        base = Path(workspace_root) if workspace_root else Path(style_path).parent
        config["logo"]["_resolved_path"] = str(base / logo_rel)
    else:
        config["logo"]["_resolved_path"] = ""

    return config


def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' or 'RRGGBB' to RGBColor."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    return RGBColor(r, g, b)


# ---------------------------------------------------------------------------
# Run-time style accessors
# ---------------------------------------------------------------------------

def font_name(cfg):
    return cfg["font"]["family"]


def mono_font(cfg):
    return cfg["font"]["monospace"]


def font_size(cfg, key):
    return cfg["font"]["sizes"][key]


def line_spacing(cfg):
    return cfg["font"]["line_spacing"]


def color_primary(cfg):
    return hex_to_rgb(cfg["colors"]["primary"])


def color_heading(cfg):
    return hex_to_rgb(cfg["colors"]["heading"])


def color_table_header_bg(cfg):
    return cfg["colors"]["table"]["header_bg"].lstrip("#")


def color_table_border(cfg):
    return cfg["colors"]["table"]["border"].lstrip("#")


def color_table_alt_row(cfg):
    return cfg["colors"]["table"]["alt_row"].lstrip("#")


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def add_run(paragraph, text, bold=False, italic=False, size=None, color=None, font_name_override=None, cfg=None):
    run = paragraph.add_run(text)
    fname = font_name_override or (font_name(cfg) if cfg else "Calibri")
    fsize = size or (font_size(cfg, "body") if cfg else 11)
    run.font.name = fname
    run.font.size = Pt(fsize)
    if bold:
        run.font.bold = True
    if italic:
        run.font.italic = True
    if color:
        run.font.color.rgb = color

    rPr = run._r.get_or_add_rPr()
    rFonts = OxmlElement("w:rFonts")
    rFonts.set(qn("w:ascii"), fname)
    rFonts.set(qn("w:hAnsi"), fname)
    rFonts.set(qn("w:cs"), fname)
    rPr.insert(0, rFonts)
    return run


def format_inline(paragraph, text, size=None, color=None, cfg=None):
    """Handle inline formatting: **bold**, *italic*, `code`."""
    if not text:
        return

    pattern = r"(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)"
    parts = re.split(pattern, text)

    for part in parts:
        if not part:
            continue
        if part.startswith("**") and part.endswith("**"):
            add_run(paragraph, part[2:-2], bold=True, size=size, color=color, cfg=cfg)
        elif part.startswith("*") and part.endswith("*") and not part.startswith("**"):
            add_run(paragraph, part[1:-1], italic=True, size=size, color=color, cfg=cfg)
        elif part.startswith("`") and part.endswith("`"):
            add_run(paragraph, part[1:-1], size=size, font_name_override=mono_font(cfg) if cfg else "Courier New", cfg=cfg)
        else:
            add_run(paragraph, part, size=size, color=color, cfg=cfg)


# ---------------------------------------------------------------------------
# Table helpers
# ---------------------------------------------------------------------------

def set_table_border(table, color):
    tbl = table._tbl
    tblPr = tbl.tblPr
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl.insert(0, tblPr)
    existing = tblPr.find(qn("w:tblBorders"))
    if existing is not None:
        tblPr.remove(existing)
    tblBorders = OxmlElement("w:tblBorders")
    for name in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        border = OxmlElement(f"w:{name}")
        border.set(qn("w:val"), "single")
        border.set(qn("w:sz"), "4")
        border.set(qn("w:color"), color)
        border.set(qn("w:space"), "0")
        tblBorders.append(border)
    tblPr.append(tblBorders)


def set_cell_shading(cell, color_hex):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), color_hex.lstrip("#"))
    shading.set(qn("w:val"), "clear")
    tcPr.append(shading)


def set_cell_width(cell, width_emu):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcW = tcPr.find(qn("w:tcW"))
    if tcW is None:
        tcW = OxmlElement("w:tcW")
        tcPr.append(tcW)
    tcW.set(qn("w:w"), str(int(width_emu)))
    tcW.set(qn("w:type"), "dxa")


def set_cell_margins(cell, top=20, bottom=20, left=60, right=60):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    margins = OxmlElement("w:tcMar")
    for side, val in [("top", top), ("bottom", bottom), ("start", left), ("end", right)]:
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(val))
        el.set(qn("w:type"), "dxa")
        margins.append(el)
    tcPr.append(margins)


def set_table_width_100pct(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    tblW = tblPr.find(qn("w:tblW"))
    if tblW is None:
        tblW = OxmlElement("w:tblW")
        tblPr.append(tblW)
    tblW.set(qn("w:w"), "5000")
    tblW.set(qn("w:type"), "pct")


def set_no_table_autofit(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")


def estimate_column_widths(headers, rows, num_cols, available_width):
    max_lengths = []
    for col_idx in range(num_cols):
        header_len = len(headers[col_idx]) if col_idx < len(headers) else 0
        max_len = header_len
        for row in rows:
            if col_idx < len(row):
                cell_len = len(row[col_idx].replace("**", ""))
                max_len = max(max_len, cell_len)
        max_lengths.append(max(max_len, 3))

    total = sum(max_lengths)
    avail_twips = int(available_width / Emu(1) * 20 / 914400)
    widths_emu = []
    for length in max_lengths:
        proportion = max(0.08, min(0.60, length / total))
        widths_emu.append(int(avail_twips * proportion))

    total_assigned = sum(widths_emu)
    if total_assigned > 0:
        factor = avail_twips / total_assigned
        widths_emu = [int(w * factor) for w in widths_emu]

    return widths_emu


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------

def parse_markdown_table(lines, start_idx):
    headers = []
    rows = []
    alignments = []
    idx = start_idx

    header_line = lines[idx].strip()
    headers = [cell.strip() for cell in header_line.strip("|").split("|")]
    idx += 1

    if idx < len(lines) and re.match(r"^\|[\s\-:]+\|", lines[idx].strip()):
        sep_line = lines[idx].strip()
        sep_cells = [cell.strip() for cell in sep_line.strip("|").split("|")]
        for cell in sep_cells:
            if cell.startswith(":") and cell.endswith(":"):
                alignments.append("center")
            elif cell.endswith(":"):
                alignments.append("right")
            else:
                alignments.append("left")
        idx += 1

    while idx < len(lines):
        line = lines[idx].strip()
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        rows.append(cells)
        idx += 1

    return headers, rows, alignments, idx


# ---------------------------------------------------------------------------
# Signature block
# ---------------------------------------------------------------------------

def is_signature_table(headers, cfg):
    if not cfg["signature"]["enabled"]:
        return False
    keywords = [k.lower() for k in cfg["signature"]["header_keywords"]]
    h_lower = [h.lower().strip() for h in headers]
    return any(k in h_lower for k in keywords)


def render_signature_block(doc, headers, rows, cfg):
    date_label = cfg["signature"]["date_label"]
    for row in rows:
        if not row or not row[0].strip():
            continue
        name = row[0].strip().replace("**", "")
        if not name:
            continue

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(30)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.line_spacing = Pt(14)
        add_run(p, "\u2500" * 50, cfg=cfg)

        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        add_run(p, name, bold=True, cfg=cfg)

        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        add_run(p, f"{date_label}: ____/____/________", cfg=cfg)


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def add_table_to_doc(doc, headers, rows, alignments, cfg):
    if is_signature_table(headers, cfg):
        render_signature_block(doc, headers, rows, cfg)
        return

    num_cols = len(headers)
    num_rows = len(rows) + 1

    table = doc.add_table(rows=num_rows, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_border(table, color_table_border(cfg))
    set_table_width_100pct(table)
    set_no_table_autofit(table)

    available_width = Inches(6.5)
    col_widths = estimate_column_widths(headers, rows, num_cols, available_width)

    # Header row
    for col_idx, header_text in enumerate(headers):
        cell = table.rows[0].cells[col_idx]
        set_cell_shading(cell, color_table_header_bg(cfg))
        set_cell_margins(cell)
        if col_idx < len(col_widths):
            set_cell_width(cell, col_widths[col_idx])

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(1)
        p.paragraph_format.line_spacing = Pt(12)

        align = alignments[col_idx] if col_idx < len(alignments) else "left"
        if align == "center":
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        elif align == "right":
            p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

        format_inline(p, header_text, size=9, color=color_heading(cfg), cfg=cfg)
        for run in p.runs:
            run.font.bold = True

    # Data rows
    for row_idx, row_data in enumerate(rows):
        for col_idx in range(num_cols):
            cell_text = row_data[col_idx] if col_idx < len(row_data) else ""
            cell = table.rows[row_idx + 1].cells[col_idx]
            set_cell_margins(cell)
            if col_idx < len(col_widths):
                set_cell_width(cell, col_widths[col_idx])

            if row_idx % 2 == 1:
                set_cell_shading(cell, color_table_alt_row(cfg))

            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = Pt(12)

            align = alignments[col_idx] if col_idx < len(alignments) else "left"
            if align == "center":
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            elif align == "right":
                p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT

            format_inline(p, cell_text, size=9, cfg=cfg)

    # Keep small tables together on one page
    if len(rows) <= 15:
        for row in table.rows:
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            cantSplit = OxmlElement("w:cantSplit")
            cantSplit.set(qn("w:val"), "1")
            trPr.append(cantSplit)
            if row != table.rows[-1]:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        pPr = p._p.get_or_add_pPr()
                        keepNext = OxmlElement("w:keepNext")
                        keepNext.set(qn("w:val"), "1")
                        pPr.append(keepNext)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)


# ---------------------------------------------------------------------------
# Header / footer
# ---------------------------------------------------------------------------

def add_header_logo(section, cfg):
    logo_path = cfg["logo"].get("_resolved_path", "")
    width_cm = cfg["logo"].get("width_cm", 3)
    fallback_text = cfg["logo"].get("fallback_text", "")

    header = section.header
    header.is_linked_to_previous = False
    for p in header.paragraphs:
        p.clear()

    p = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.right_indent = Cm(0)

    if logo_path and Path(logo_path).exists():
        run = p.add_run()
        run.add_picture(str(logo_path), width=Cm(width_cm))
    else:
        if logo_path:
            print(f"Warning: Logo not found at {logo_path}, using text fallback")
        label = fallback_text or ""
        if label:
            run = p.add_run(label)
            run.font.name = font_name(cfg)
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = color_primary(cfg)
            rPr = run._r.get_or_add_rPr()
            rFonts = OxmlElement("w:rFonts")
            rFonts.set(qn("w:ascii"), font_name(cfg))
            rFonts.set(qn("w:hAnsi"), font_name(cfg))
            rPr.insert(0, rFonts)


def add_footer_page_number(section, cfg):
    footer = section.footer
    footer.is_linked_to_previous = False
    for p in footer.paragraphs:
        p.clear()

    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(0)

    run = p.add_run()
    run.font.name = font_name(cfg)
    run.font.size = Pt(font_size(cfg, "body"))
    run.font.color.rgb = color_primary(cfg)

    fldChar_begin = OxmlElement("w:fldChar")
    fldChar_begin.set(qn("w:fldCharType"), "begin")
    run._r.append(fldChar_begin)

    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = " PAGE "
    run._r.append(instrText)

    fldChar_end = OxmlElement("w:fldChar")
    fldChar_end.set(qn("w:fldCharType"), "end")
    run._r.append(fldChar_end)


# ---------------------------------------------------------------------------
# Page helpers
# ---------------------------------------------------------------------------

def add_page_break(doc):
    from docx.enum.text import WD_BREAK
    p = doc.add_paragraph()
    run = p.add_run()
    run.add_break(WD_BREAK.PAGE)


def set_paragraph_shading(paragraph, color_hex):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color_hex.lstrip("#"))
    shd.set(qn("w:val"), "clear")
    pPr.append(shd)


# ---------------------------------------------------------------------------
# Main conversion
# ---------------------------------------------------------------------------

def convert_md_to_docx(input_path, output_path, cfg):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.split("\n")
    doc = Document()

    # Page setup
    margins = cfg["page"]["margins"]
    page_size = cfg["page"].get("size", "letter")
    for section in doc.sections:
        section.top_margin = Cm(margins["top"])
        section.bottom_margin = Cm(margins["bottom"])
        section.left_margin = Cm(margins["left"])
        section.right_margin = Cm(margins["right"])
        if page_size == "a4":
            section.page_width = Cm(21.0)
            section.page_height = Cm(29.7)
        else:  # letter
            section.page_width = Inches(8.5)
            section.page_height = Inches(11)

    # Header and footer
    for section in doc.sections:
        add_header_logo(section, cfg)
        add_footer_page_number(section, cfg)

    logo_path = cfg["logo"].get("_resolved_path", "")
    if logo_path and Path(logo_path).exists():
        print(f"Logo: {logo_path}")
    elif not logo_path and not cfg["logo"].get("fallback_text"):
        print("Info: No logo path or fallback text configured — header will be empty")

    # Default style
    style = doc.styles["Normal"]
    style.font.name = font_name(cfg)
    style.font.size = Pt(font_size(cfg, "body"))
    style.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
    style.paragraph_format.line_spacing = line_spacing(cfg)

    idx = 0
    in_code_block = False
    code_lines = []

    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        # Page break
        if stripped == "\\newpage":
            add_page_break(doc)
            idx += 1
            continue

        # Code block toggle
        if stripped.startswith("```"):
            if in_code_block:
                p = doc.add_paragraph()
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.left_indent = Cm(1)
                set_paragraph_shading(p, "F0F0F0")
                for i, cl in enumerate(code_lines):
                    if i > 0:
                        run = p.add_run()
                        run.add_break()
                    add_run(p, cl, font_name_override=mono_font(cfg), size=9, cfg=cfg)
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            idx += 1
            continue

        if in_code_block:
            code_lines.append(line)
            idx += 1
            continue

        # Horizontal rule
        if stripped == "---":
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            pPr = p._p.get_or_add_pPr()
            pBdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "4")
            bottom.set(qn("w:color"), "CCCCCC")
            bottom.set(qn("w:space"), "1")
            pBdr.append(bottom)
            pPr.append(pBdr)
            idx += 1
            continue

        # Empty line
        if not stripped:
            idx += 1
            continue

        # Headings
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            text = stripped.lstrip("#").strip()
            p = doc.add_paragraph()

            if level == 1:
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(12)
                p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
                format_inline(p, text, size=font_size(cfg, "h1"), color=color_heading(cfg), cfg=cfg)
                for run in p.runs:
                    run.font.bold = True
            elif level == 2:
                p.paragraph_format.space_before = Pt(16)
                p.paragraph_format.space_after = Pt(8)
                p.paragraph_format.keep_with_next = True
                format_inline(p, text, size=font_size(cfg, "h2"), color=color_heading(cfg), cfg=cfg)
                for run in p.runs:
                    run.font.bold = True
                pPr = p._p.get_or_add_pPr()
                pBdr = OxmlElement("w:pBdr")
                bottom = OxmlElement("w:bottom")
                bottom.set(qn("w:val"), "single")
                bottom.set(qn("w:sz"), "4")
                bottom.set(qn("w:color"), color_table_border(cfg))
                bottom.set(qn("w:space"), "2")
                pBdr.append(bottom)
                pPr.append(pBdr)
            elif level == 3:
                p.paragraph_format.space_before = Pt(12)
                p.paragraph_format.space_after = Pt(6)
                p.paragraph_format.keep_with_next = True
                format_inline(p, text, size=font_size(cfg, "h3"), color=color_heading(cfg), cfg=cfg)
                for run in p.runs:
                    run.font.bold = True
            else:
                p.paragraph_format.space_before = Pt(8)
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.keep_with_next = True
                format_inline(p, text, size=font_size(cfg, "body"), color=color_heading(cfg), cfg=cfg)
                for run in p.runs:
                    run.font.bold = True

            idx += 1
            continue

        # Markdown table
        if stripped.startswith("|") and "|" in stripped[1:]:
            next_idx = idx + 1
            if next_idx < len(lines) and re.match(r"^\|[\s\-:]+\|", lines[next_idx].strip()):
                headers, rows, alignments, end_idx = parse_markdown_table(lines, idx)
                add_table_to_doc(doc, headers, rows, alignments, cfg)
                idx = end_idx
                continue

        # Bullet list
        if stripped.startswith("- "):
            text = stripped[2:]
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            add_run(p, "\u2022  ", size=font_size(cfg, "body"), cfg=cfg)
            format_inline(p, text, cfg=cfg)
            idx += 1
            continue

        # Numbered list
        num_match = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if num_match:
            num = num_match.group(1)
            text = num_match.group(2)
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.left_indent = Cm(1)
            p.paragraph_format.first_line_indent = Cm(-0.5)
            add_run(p, f"{num}.  ", bold=True, size=font_size(cfg, "body"), cfg=cfg)
            format_inline(p, text, cfg=cfg)
            idx += 1
            continue

        # Bold-only line
        if stripped.startswith("**"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            format_inline(p, stripped, cfg=cfg)
            idx += 1
            continue

        # Italic-only line (e.g., *confidential notice*)
        if stripped.startswith("*") and stripped.endswith("*") and not stripped.startswith("**"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(4)
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            add_run(p, stripped.strip("*"), italic=True, size=font_size(cfg, "small"), cfg=cfg)
            idx += 1
            continue

        # Regular paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        format_inline(p, stripped, cfg=cfg)
        idx += 1

    doc.save(output_path)
    print(f"Created: {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert a markdown file to a branded DOCX."
    )
    parser.add_argument("input", help="Input markdown file path")
    parser.add_argument("output", help="Output DOCX file path")
    parser.add_argument(
        "--style",
        metavar="YAML",
        help="Path to document-style.yaml. If omitted, built-in defaults are used.",
    )
    parser.add_argument(
        "--workspace-root",
        metavar="PATH",
        help="Workspace root for resolving relative logo paths in the style config.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    output_path = Path(args.output)

    if args.style:
        style_path = Path(args.style)
        if not style_path.exists():
            print(f"Error: Style config not found: {style_path}")
            sys.exit(1)
        cfg = load_style(style_path, workspace_root=args.workspace_root)
        print(f"Style: {style_path}")
    else:
        cfg = DEFAULTS.copy()
        cfg["logo"]["_resolved_path"] = ""
        print("Style: using built-in defaults")

    convert_md_to_docx(str(input_path), str(output_path), cfg)


if __name__ == "__main__":
    main()
