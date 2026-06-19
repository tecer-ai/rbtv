#!/usr/bin/env python3
"""RBTV slide-library archive tool — moves superseded fragments out of the
active set and restores them losslessly.

Archiving a fragment moves slides/{id}.html -> archive/{id}.html, removes its
manifest.md row, and appends an entry to archive/archive.md carrying the
verbatim original manifest row (so --unarchive is byte/row lossless). The
engine (assemble.py) is manifest-driven and never scans slides/, so an archived
fragment is invisible to assembly and the GUI with no engine change.

Stdlib-only. Canonical source: rbtv engine/archive.py. Vendored per-library by
install-engine.py alongside assemble.py. Run from the library root (vendored
copy) or with --library <path>.
"""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# ── Constants ──
# Mirror assemble.py's manifest contract (case-sensitive headings). The manifest
# is accepted with the base 10 columns OR with the trailing optional `status`
# column (11 columns) — assemble.py reads both, so archive.py must too.
SLIDES_HEADING = "## Slides"
MANIFEST_COLUMNS = [
    "id", "file", "section", "title", "audience",
    "lang", "kind", "summary", "assets", "provenance",
]
STATUS_COLUMN = "status"

JSON_MODE = False


class ArchiveError(Exception):
    """Raised on any validation or operation failure (loud + atomic)."""


def die(message):
    raise ArchiveError(message)


# ═══════════════════════════════════════════════════════════════════════════
# manifest.md parsing (mirrors assemble.py — case-sensitive, positional)
# ═══════════════════════════════════════════════════════════════════════════

def _split_row(line):
    cells = line.strip().split("|")
    if cells and cells[0].strip() == "":
        cells = cells[1:]
    if cells and cells[-1].strip() == "":
        cells = cells[:-1]
    return [c.strip() for c in cells]


def _slides_section_bounds(lines):
    """Return (header_idx, sep_idx, last_row_idx) for the ## Slides table.

    header_idx/sep_idx are the table header and separator physical line indices;
    last_row_idx is the index of the last |-row in the section. die() if the
    section or its header is absent/malformed.
    """
    in_section = False
    row_indices = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("## "):
            if stripped == SLIDES_HEADING:
                in_section = True
            elif in_section:
                break
            continue
        if in_section and "|" in line:
            row_indices.append(idx)
    if not in_section:
        die("manifest.md has no '## Slides' section")
    if len(row_indices) < 2:
        die("'## Slides' section has no header + separator rows")
    header_idx = row_indices[0]
    header_cells = _split_row(lines[header_idx])
    if header_cells != MANIFEST_COLUMNS and header_cells != MANIFEST_COLUMNS + [STATUS_COLUMN]:
        die(f"manifest.md header mismatch at line {header_idx + 1}")
    return header_idx, row_indices[1], row_indices[-1], row_indices


def _find_live_row(lines, slide_id):
    """Return (line_idx, raw_line) for the data row whose id == slide_id, or None.

    Skips the header and separator rows (the first two |-rows of the section).
    """
    _, _, _, row_indices = _slides_section_bounds(lines)
    for idx in row_indices[2:]:
        cells = _split_row(lines[idx])
        if cells and cells[0] == slide_id:
            return idx, lines[idx]
    return None


# ═══════════════════════════════════════════════════════════════════════════
# archive.md parsing / writing
# ═══════════════════════════════════════════════════════════════════════════

ARCHIVE_HEADING = "## Archived slides"
_ENTRY_RE = re.compile(r"^### ", re.MULTILINE)


def _archive_scaffold(library_name):
    return (
        f"# {library_name} archive log\n\n"
        "Superseded slides moved out of `slides/` by `archive.py`. The engine "
        "never reads this file (same class as `docs/`).\n\n"
        "To restore a slide losslessly: `python archive.py --unarchive <id>`.\n\n"
        f"{ARCHIVE_HEADING}\n\n"
        "<!-- One entry per archive action, appended by archive.py. -->\n"
    )


def _parse_archive_entries(text):
    """Return a list of dicts (in file order): {id, restored, row, start, end}.

    start/end are character offsets spanning the entry block (for in-place
    stamping). row is the verbatim manifest row recovered from the entry's
    fenced ```text block.
    """
    entries = []
    matches = list(_ENTRY_RE.finditer(text))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]
        id_m = re.search(r"^- id: (.+)$", block, re.MULTILINE)
        restored_m = re.search(r"^- restored: (.+)$", block, re.MULTILINE)
        row_m = re.search(r"```text\n(.*?)\n```", block, re.DOTALL)
        if not id_m or not row_m:
            continue
        entries.append({
            "id": id_m.group(1).strip(),
            "restored": restored_m.group(1).strip() if restored_m else "-",
            "row": row_m.group(1),
            "start": start,
            "end": end,
        })
    return entries


def _latest_unrestored(entries, slide_id):
    found = [e for e in entries if e["id"] == slide_id and e["restored"] == "-"]
    return found[-1] if found else None


def _render_entry(slide_id, date, reason, superseded_by, verbatim_row):
    return (
        f"\n---\n\n### {slide_id} — archived {date}\n\n"
        f"- id: {slide_id}\n"
        f"- archived: {date}\n"
        f"- reason: {reason}\n"
        f"- superseded-by: {superseded_by}\n"
        f"- restored: -\n\n"
        "Original manifest row (re-inserted verbatim on unarchive):\n\n"
        f"```text\n{verbatim_row}\n```\n"
    )


# ═══════════════════════════════════════════════════════════════════════════
# Operations
# ═══════════════════════════════════════════════════════════════════════════

def _resolve_paths(library):
    lib = Path(library).resolve()
    return {
        "library": lib,
        "manifest": lib / "manifest.md",
        "slides": lib / "slides",
        "archive": lib / "archive",
        "archive_md": lib / "archive" / "archive.md",
        "library_json": lib / "library.json",
    }


def _library_name(paths):
    try:
        data = json.loads(paths["library_json"].read_text(encoding="utf-8"))
        return data.get("name", paths["library"].name)
    except Exception:
        return paths["library"].name


def do_archive(paths, slide_id, reason, superseded_by, date):
    manifest_path = paths["manifest"]
    if not manifest_path.exists():
        die(f"manifest.md not found in {paths['library']}")

    src_frag = paths["slides"] / f"{slide_id}.html"
    dst_frag = paths["archive"] / f"{slide_id}.html"

    # ── Validate everything first (no mutation on failure) ──
    manifest_text = manifest_path.read_text(encoding="utf-8")
    lines = manifest_text.splitlines()
    hit = _find_live_row(lines, slide_id)
    if hit is None:
        die(f"no live manifest row for id '{slide_id}'")
    if not src_frag.exists():
        die(f"fragment not found: slides/{slide_id}.html")
    if dst_frag.exists():
        die(f"archive/{slide_id}.html already exists — refusing to overwrite")

    row_idx, raw_row = hit
    verbatim_row = raw_row.rstrip("\n")

    # ── Mutate with rollback (manifest -> move -> log) ──
    new_lines = lines[:row_idx] + lines[row_idx + 1:]
    new_manifest = "\n".join(new_lines)
    if manifest_text.endswith("\n"):
        new_manifest += "\n"

    paths["archive"].mkdir(parents=True, exist_ok=True)
    archive_existed = paths["archive_md"].exists()
    old_archive_text = (
        paths["archive_md"].read_text(encoding="utf-8") if archive_existed else None
    )

    manifest_path.write_text(new_manifest, encoding="utf-8")
    try:
        shutil.move(str(src_frag), str(dst_frag))
        try:
            base = old_archive_text if archive_existed else _archive_scaffold(
                _library_name(paths)
            )
            entry = _render_entry(slide_id, date, reason, superseded_by, verbatim_row)
            paths["archive_md"].write_text(base + entry, encoding="utf-8")
        except Exception:
            shutil.move(str(dst_frag), str(src_frag))  # undo move
            raise
    except Exception:
        manifest_path.write_text(manifest_text, encoding="utf-8")  # undo manifest
        raise

    return {
        "fragment": str(dst_frag),
        "manifest_row_removed": verbatim_row,
        "archive_log": str(paths["archive_md"]),
    }


def do_unarchive(paths, slide_id, date):
    manifest_path = paths["manifest"]
    if not manifest_path.exists():
        die(f"manifest.md not found in {paths['library']}")

    archived_frag = paths["archive"] / f"{slide_id}.html"
    restored_frag = paths["slides"] / f"{slide_id}.html"

    # ── Validate everything first ──
    if not archived_frag.exists():
        die(f"no archived fragment: archive/{slide_id}.html")
    if restored_frag.exists():
        die(f"slides/{slide_id}.html already exists — id may already be live")

    manifest_text = manifest_path.read_text(encoding="utf-8")
    lines = manifest_text.splitlines()
    if _find_live_row(lines, slide_id) is not None:
        die(f"id '{slide_id}' already has a live manifest row")

    if not paths["archive_md"].exists():
        die("archive/archive.md not found — cannot recover the original row")
    archive_text = paths["archive_md"].read_text(encoding="utf-8")
    entries = _parse_archive_entries(archive_text)
    entry = _latest_unrestored(entries, slide_id)
    if entry is None:
        die(f"no unrestored archive.md entry holding the original row for '{slide_id}'")

    # ── Build new manifest: re-insert the stored row after the last data row ──
    _, _, last_row_idx, _ = _slides_section_bounds(lines)
    new_lines = lines[:last_row_idx + 1] + [entry["row"]] + lines[last_row_idx + 1:]
    new_manifest = "\n".join(new_lines)
    if manifest_text.endswith("\n"):
        new_manifest += "\n"

    # ── Stamp the entry restored in archive.md (in-place over its block) ──
    stamped_block = re.sub(
        r"^- restored: -$", f"- restored: {date}",
        archive_text[entry["start"]:entry["end"]], count=1, flags=re.MULTILINE,
    )
    new_archive = archive_text[:entry["start"]] + stamped_block + archive_text[entry["end"]:]

    # ── Mutate with rollback (manifest -> move -> log) ──
    manifest_path.write_text(new_manifest, encoding="utf-8")
    try:
        shutil.move(str(archived_frag), str(restored_frag))
        try:
            paths["archive_md"].write_text(new_archive, encoding="utf-8")
        except Exception:
            shutil.move(str(restored_frag), str(archived_frag))
            raise
    except Exception:
        manifest_path.write_text(manifest_text, encoding="utf-8")
        raise

    return {
        "fragment": str(restored_frag),
        "manifest_row_restored": entry["row"],
        "archive_log": str(paths["archive_md"]),
    }


def do_list(paths):
    if not paths["archive_md"].exists():
        return {"archived": []}
    entries = _parse_archive_entries(paths["archive_md"].read_text(encoding="utf-8"))
    return {
        "archived": [
            {"id": e["id"], "restored": e["restored"]}
            for e in entries if e["restored"] == "-"
        ],
        "all_entries": [
            {"id": e["id"], "restored": e["restored"]} for e in entries
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global JSON_MODE
    parser = argparse.ArgumentParser(
        description="RBTV slide-library archive tool (archive / unarchive / list)"
    )
    parser.add_argument("id", nargs="?", help="fragment id to archive")
    parser.add_argument("--unarchive", metavar="ID", help="restore an archived fragment")
    parser.add_argument("--list", action="store_true", help="list archived fragments")
    parser.add_argument("--reason", default="-", help="why the slide is being archived")
    parser.add_argument("--superseded-by", default="-", metavar="ID",
                        help="id of the slide that replaces this one")
    parser.add_argument("--library", default=None,
                        help="path to the library root (default: this script's folder)")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable envelope")
    parser.allow_abbrev = False
    args = parser.parse_args()

    JSON_MODE = args.json

    library = args.library if args.library else str(Path(__file__).resolve().parent)
    paths = _resolve_paths(library)

    # Exactly one mode.
    modes = [bool(args.id), bool(args.unarchive), bool(args.list)]
    if sum(modes) != 1:
        msg = "exactly one of: <id> (archive), --unarchive <id>, --list"
        if JSON_MODE:
            print(json.dumps({"ok": False, "op": None, "error": msg}))
        else:
            print("ERROR: " + msg, file=sys.stderr)
        sys.exit(2)

    if args.list:
        op, slide_id = "list", None
    elif args.unarchive:
        op, slide_id = "unarchive", args.unarchive
    else:
        op, slide_id = "archive", args.id

    date = datetime.now().strftime("%Y-%m-%d")
    envelope = {
        "ok": True, "op": op, "id": slide_id,
        "library": str(paths["library"]), "error": None,
    }

    try:
        if op == "archive":
            result = do_archive(paths, slide_id, args.reason, args.superseded_by, date)
        elif op == "unarchive":
            result = do_unarchive(paths, slide_id, date)
        else:
            result = do_list(paths)
        envelope.update(result)
    except ArchiveError as e:
        envelope["ok"] = False
        envelope["error"] = str(e)
        if JSON_MODE:
            print(json.dumps(envelope))
        else:
            print("ERROR: " + str(e), file=sys.stderr)
        sys.exit(1)

    if JSON_MODE:
        print(json.dumps(envelope))
    else:
        if op == "archive":
            print(f"archived {slide_id} -> archive/{slide_id}.html (row removed, logged)")
        elif op == "unarchive":
            print(f"unarchived {slide_id} -> slides/{slide_id}.html (row restored, logged)")
        else:
            live = envelope.get("archived", [])
            if not live:
                print("no archived slides")
            else:
                for e in live:
                    print(e["id"])
    sys.exit(0)


if __name__ == "__main__":
    main()
