#!/usr/bin/env python3
"""posh — render a structured vault document as a polished static HTML page.

Document types are subcommands; each pairs a parser with a template in
../templates/. `plan` renders a /plan seat-plan folder (seats.md + seat
bodies + companion files) as a dashboard page. Standard library only.
"""

import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
STATUSES = ("pending", "wip", "done", "blocked")


# ---------- minimal markdown -> HTML (headings, tables, lists, fences, inline) ----------

def _inline(text):
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', out)
    return out


def _table_html(rows):
    head, body = rows[0], rows[2:]
    cells = "".join(f"<th>{_inline(c)}</th>" for c in head)
    parts = [f"<div class='table-wrap'><table><tr>{cells}</tr>"]
    for r in body:
        parts.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    parts.append("</table></div>")
    return "".join(parts)


def _split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_html(text):
    """Render a useful subset of markdown; unrecognized lines become paragraphs."""
    out, lines, i = [], text.splitlines(), 0
    para, ul = [], []

    def flush_para():
        if para:
            out.append("<p>" + _inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_ul():
        if ul:
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in ul) + "</ul>")
            ul.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_para(); flush_ul()
            fence = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                fence.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(fence)) + "</code></pre>")
        elif stripped.startswith("|"):
            flush_para(); flush_ul()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(_split_row(lines[i])); i += 1
            i -= 1
            if len(rows) >= 2 and set("".join(rows[1])) <= set("-: "):
                out.append(_table_html(rows))
            else:
                out.append("<pre><code>" + html.escape("\n".join("|".join(r) for r in rows)) + "</code></pre>")
        elif m := re.match(r"(#{1,6})\s+(.*)", stripped):
            flush_para(); flush_ul()
            lvl = min(len(m.group(1)) + 2, 6)  # demote: page owns h1/h2
            out.append(f"<h{lvl}>{_inline(m.group(2))}</h{lvl}>")
        elif re.match(r"[-*]\s+", stripped) or re.match(r"\d+\.\s+", stripped):
            flush_para()
            ul.append(re.sub(r"^([-*]|\d+\.)\s+", "", stripped))
        elif stripped in ("---", "***"):
            flush_para(); flush_ul()
            out.append("<hr>")
        elif stripped.startswith(">"):
            flush_para(); flush_ul()
            out.append(f"<blockquote><p>{_inline(stripped.lstrip('> '))}</p></blockquote>")
        elif not stripped:
            flush_para(); flush_ul()
        else:
            flush_ul()
            para.append(stripped)
        i += 1
    flush_para(); flush_ul()
    return "\n".join(out)


# ---------- plan-folder parsing ----------

def parse_frontmatter(text):
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            text = text[end + 4:]
    return meta, text


def extract_tables(text):
    """Return (seat_rows, checkpoint_rows, remainder_text)."""
    lines = text.splitlines()
    keep, seat_rows, cp_rows = [], [], []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(_split_row(lines[i])); i += 1
            header = [h.lower() for h in block[0]]
            if header[:1] == ["seat"] and "status" in header:
                seat_rows = block
            elif header and header[0].startswith("checkpoint"):
                cp_rows = block
            else:
                keep.extend("|".join(r) for r in block)
            continue
        keep.append(lines[i]); i += 1
    # drop the mermaid restatement of the dependency edges — waves render them
    remainder = re.sub(r"```mermaid.*?```", "", "\n".join(keep), flags=re.S)
    return seat_rows, cp_rows, remainder


def parse_status(cell, warnings, seat):
    plain = cell.replace("**", "").strip()
    word = plain.split(None, 1)[0].lower() if plain else ""
    rest = plain[len(word):].strip(" —–-:") if plain else ""
    if word not in STATUSES:
        warnings.append(f"seat '{seat}': unrecognized status '{word or '(empty)'}', shown as pending")
        return "pending", "", plain
    return word, rest, ""


def parse_plan(folder, warnings):
    seats_md = folder / "seats.md"
    if not seats_md.is_file():
        sys.exit(f"posh: refused: {seats_md} not found — a plan folder must carry seats.md")
    _, text = parse_frontmatter(seats_md.read_text(encoding="utf-8"))
    seat_rows, cp_rows, remainder = extract_tables(text)
    if not seat_rows:
        sys.exit("posh: refused: no seat table (| seat | after | status | description |) found in seats.md")

    seats = []
    for row in seat_rows[2:]:
        row += [""] * (4 - len(row))
        name, after, status_cell, desc = row[0], row[1], row[2], row[3]
        if not name or set(name) <= set("-: ") or name == "read-first":
            continue
        status, evidence, _ = parse_status(status_cell, warnings, name)
        touch = "⚠ owner touchpoint" in desc
        desc = desc.replace("⚠ owner touchpoint", "").strip(" —–-:")
        deps = [] if after.strip() in ("", "—", "-") else [d.strip() for d in after.split(",") if d.strip()]
        body_file = folder / "seats" / name / "seat.md"
        meta, body = ({}, "")
        if body_file.is_file():
            meta, body = parse_frontmatter(body_file.read_text(encoding="utf-8"))
        else:
            warnings.append(f"seat '{name}': no seats/{name}/seat.md found")
        seats.append({"name": name, "deps": deps, "status": status, "evidence": evidence,
                      "desc": desc, "touch": touch, "meta": meta, "body": body})
    return seats, cp_rows, remainder


def compute_waves(seats, warnings):
    depth, by_name = {}, {s["name"]: s for s in seats}

    def resolve(name, trail):
        if name in depth:
            return depth[name]
        if name in trail:
            warnings.append(f"dependency cycle at '{name}' — its seats placed in the last wave")
            return len(seats)
        seat = by_name.get(name)
        if seat is None:
            return -1  # unknown deps (e.g. read-first) count as satisfied
        depth[name] = 1 + max((resolve(d, trail | {name}) for d in seat["deps"]), default=-1)
        return depth[name]

    for s in seats:
        for d in s["deps"]:
            if d not in by_name and d != "read-first":
                warnings.append(f"seat '{s['name']}' waits on unknown seat '{d}'")
        resolve(s["name"], frozenset())
    waves = {}
    for s in seats:
        waves.setdefault(min(depth[s["name"]], len(seats)), []).append(s)
    return [waves[k] for k in sorted(waves)]


# ---------- rendering ----------

def load_template(name):
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    blocks = dict(re.findall(r"<!-- posh:([\w-]+) -->\n(.*?)<!-- /posh:\1 -->\n?", text, flags=re.S))
    skeleton = re.sub(r"\n?<!-- posh:[\w-]+ -->\n.*?<!-- /posh:[\w-]+ -->\n?", "", text, flags=re.S)
    return skeleton, blocks


def fill(block, values):
    for key, val in values.items():
        block = block.replace("{{%s}}" % key, val)
    return block


def render_seat(block, seat):
    chips = [f"<span class='chip'>after: {html.escape(', '.join(seat['deps']))}</span>"] if seat["deps"] else []
    exec_bits = [seat["meta"].get(k, "") for k in ("harness", "model", "effort")]
    if any(exec_bits):
        chips.append("<span class='chip'>runs on: %s</span>"
                     % html.escape(" · ".join(b for b in exec_bits if b)))
    label = seat["status"]
    evidence = ""
    if seat["evidence"]:
        prefix = "why blocked: " if seat["status"] == "blocked" else ""
        evidence = f"<div class='evidence'>{prefix}{_inline(seat['evidence'])}</div>"
    body = ""
    if seat["body"].strip():
        body = ("<details><summary>Full seat instructions</summary>"
                f"<div class='body'>{md_html(seat['body'])}</div></details>")
    touch = ("<p><span class='badge b-touch'>⚠ owner touchpoint — needs a human decision</span></p>"
             if seat["touch"] else "")
    return fill(block, {
        "NAME": html.escape(seat["name"]), "STATUS": seat["status"], "STATUS_LABEL": label,
        "TOUCH_BADGE": touch, "DESC": _inline(seat["desc"]), "CHIPS": "".join(chips),
        "EVIDENCE": evidence, "BODY_DETAILS": body,
    })


def doc_section(block, title, sub, body_md, open_=False):
    return fill(block, {"DOC_TITLE": html.escape(title), "DOC_SUB": html.escape(sub),
                        "DOC_BODY": md_html(body_md), "OPEN": " open" if open_ else ""})


def render_plan(folder, out_path):
    warnings = []
    seats, cp_rows, remainder = parse_plan(folder, warnings)
    waves = compute_waves(seats, warnings)
    skeleton, blocks = load_template("plan.html")

    counts = {s: 0 for s in STATUSES}
    for s in seats:
        counts[s["status"]] += 1
    total = len(seats) or 1
    pct = round(100 * counts["done"] / total)
    segments = "".join(
        f"<span class='p-{k}' style='width:{100 * counts[k] / total:.1f}%'></span>"
        for k in ("done", "wip", "blocked") if counts[k])

    waves_html = []
    for n, wave in enumerate(waves, 1):
        cards = "\n".join(render_seat(blocks["seat-card"], s) for s in wave)
        label = f"Wave {n} · {len(wave)} seat{'s' if len(wave) > 1 else ''}"
        waves_html.append(fill(blocks["wave"], {"WAVE_LABEL": label, "CARDS": cards}))

    checkpoints = ""
    if cp_rows:
        checkpoints = fill(blocks["checkpoints"], {"CHECKPOINT_TABLE": _table_html(cp_rows)})

    extras = []
    if remainder.strip():
        extras.append(doc_section(blocks["doc-section"], "Rules & contract",
                                  "everything else stated in seats.md", remainder))
    named = [("read-first.md", "shared context every seat's worker reads first"),
             ("status.md", "current state"), ("decisions.md", "rulings, append-only"),
             ("issues.md", "open questions needing a ruling"),
             ("loose-ends.md", "captured deferred work"),
             ("doubts.md", "self-resolved doubts"), ("ideas.md", "framed ideas")]
    for fname, sub in named:
        f = folder / fname
        if f.is_file():
            _, body = parse_frontmatter(f.read_text(encoding="utf-8"))
            extras.append(doc_section(blocks["doc-section"], fname, sub, body))
    for sub_dir, sub in (("checkpoints", "owner checkpoint file"), ("judgements", "machine-judge verdicts")):
        for f in sorted((folder / sub_dir).glob("*.md")) if (folder / sub_dir).is_dir() else []:
            extras.append(doc_section(blocks["doc-section"], f"{sub_dir}/{f.name}", sub, f.read_text(encoding="utf-8")))

    warn_html = ""
    if warnings:
        warn_html = fill(blocks["warnings"], {"WARNING_ITEMS": " · ".join(html.escape(w) for w in warnings)})

    page = fill(skeleton, {
        "TITLE": html.escape(folder.name), "SOURCE": html.escape(str(folder)),
        "GENERATED_AT": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "PCT_DONE": str(pct), "TOTAL": str(len(seats)),
        "N_DONE": str(counts["done"]), "N_WIP": str(counts["wip"]),
        "N_PENDING": str(counts["pending"]), "N_BLOCKED": str(counts["blocked"]),
        "PROGRESS_SEGMENTS": segments, "WAVES": "\n".join(waves_html),
        "CHECKPOINTS": checkpoints, "EXTRA_SECTIONS": "\n".join(extras),
        "WARNINGS": warn_html,
    })
    out_path.write_text(page, encoding="utf-8")
    return {"type": "plan", "source": str(folder), "output": str(out_path),
            "seats": len(seats), "waves": len(waves), "pct_done": pct, "warnings": warnings}


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        prog="posh", description="Render a structured vault document as a polished static HTML page.")
    sub = parser.add_subparsers(dest="type", required=True, metavar="<type>")
    p_plan = sub.add_parser("plan", help="render a /plan seat-plan folder as a dashboard page")
    p_plan.add_argument("folder", type=Path, help="the plan folder (holds seats.md)")
    p_plan.add_argument("--out", type=Path, help="output file (default: <folder>/plan.html)")
    p_plan.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args()

    folder = args.folder.resolve()
    if not folder.is_dir():
        sys.exit(f"posh: refused: {folder} is not a directory")
    out_path = (args.out or folder / "plan.html").resolve()
    result = render_plan(folder, out_path)
    for w in result["warnings"]:
        print(f"posh: note: {w}", file=sys.stderr)
    if args.json:
        print(json.dumps(result))
    else:
        print(f"posh: wrote {result['output']} — {result['seats']} seats in "
              f"{result['waves']} waves, {result['pct_done']}% done")


if __name__ == "__main__":
    main()
