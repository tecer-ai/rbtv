#!/usr/bin/env python3
"""Capability-cards: render one uniform card per exposed resource."""

import argparse
import csv
import json
import sys
from pathlib import Path

EXPECTED_HEADER = ["part-id", "part-kind", "method", "rbtv-cli", "entry-point",
                   "description", "write-roots"]
CARD_FIELDS = ["part-id", "part-kind", "component", "module", "method", "entry-point", "rbtv-cli", "description"]

# The rbtv repo root — this file's own position is `<repo>/meta/planning/capabilities/
# capability-cards/tool/capability_cards.py`, five levels down. Derived, never hardcoded to a
# user's home: `.rbtv/mirror/` (the old default) is a partial installer copy — a 5-card slice
# of the ~182 cards the real repo carries, and it doesn't exist at all from a seat folder
# (owner ethos rung 2: shop capability cards before inventing a tool; a seat that trusts the
# default must see the real catalog, not a sliver of it).
DEFAULT_ROOT = str(Path(__file__).resolve().parents[5])


def find_components(root: Path):
    """Yield (component_path, module_name, component_name) for every component folder."""
    if not root.exists():
        return
    for path in root.rglob("component.md"):
        comp_dir = path.parent
        # module = the folder holding the component ("" when it sits directly under root)
        yield comp_dir, comp_dir.relative_to(root).parent.name, comp_dir.name


def cell(row, i):
    """One card field from a data row: missing or empty renders '—'."""
    return row[i] if len(row) > i and row[i] else "—"


def load_cards(root: Path):
    cards = []
    warnings = []
    for comp_dir, module, component in find_components(root):
        exposure = comp_dir / "exposure.csv"
        if not exposure.exists():
            prefix = f"{module}/{component}" if module else component
            warnings.append(f"warn: {prefix} has no exposure manifest")
            continue
        with exposure.open(newline="", encoding="utf-8") as f:
            lines = f.readlines()
        # ADX-1/ADX-3: skip '#' comment AND blank lines BEFORE the header only; after it they are data.
        offset = 0
        while offset < len(lines) and (lines[offset].startswith("#") or not lines[offset].strip()):
            offset += 1
        reader = csv.reader(lines[offset:])
        try:
            header = next(reader, None)
        except csv.Error as e:
            warnings.append(f"warn: {exposure}: {e}")
            continue
        if header != EXPECTED_HEADER:
            warnings.append(f"warn: {exposure}: unrecognized header, skipped")
            continue
        for lineno, row in enumerate(reader, start=offset + 2):
            # ADX-3: a blank line among the rows is not a part — never an eight-dash card.
            if not any(field.strip() for field in row):
                warnings.append(f"warn: {exposure}: blank row at line {lineno}, skipped")
                continue
            if len(row) < len(EXPECTED_HEADER):
                warnings.append(f"warn: {exposure}: short row at line {lineno}")
            # ADX-3: ANY empty field renders '—', not just description.
            cards.append({
                "part-id": cell(row, 0),
                "part-kind": cell(row, 1),
                "component": component,
                "module": module,
                "method": cell(row, 2),
                "entry-point": cell(row, 4),
                "rbtv-cli": cell(row, 3),
                "description": cell(row, 5),
            })
    cards.sort(key=lambda c: (c["module"], c["component"], c["part-id"]))
    return cards, warnings


def render_card_text(card):
    return (
        f"part-id: {card['part-id']}\n"
        f"part-kind: {card['part-kind']}\n"
        f"component: {card['component']}\n"
        f"module: {card['module']}\n"
        f"method: {card['method']}\n"
        f"entry-point: {card['entry-point']}\n"
        f"rbtv-cli: {card['rbtv-cli']}\n"
        f"description: {card['description']}"
    )


def cmd_list(args):
    root = Path(args.root)
    if not root.exists():
        print(f"error: root path does not exist: {root}", file=sys.stderr)
        return 2
    cards, warnings = load_cards(root)
    for w in warnings:
        print(w, file=sys.stderr)
    if args.json:
        print(json.dumps(cards))
        return 0
    if not cards:
        print("0 cards")
        return 0
    for i, card in enumerate(cards):
        if i:
            print()
        print(render_card_text(card))
    return 0


def cmd_show(args):
    root = Path(args.root)
    if not root.exists():
        print(f"error: root path does not exist: {root}", file=sys.stderr)
        return 2
    cards, warnings = load_cards(root)
    for w in warnings:
        print(w, file=sys.stderr)
    matches = [c for c in cards if c["part-id"] == args.part_id]
    if not matches:
        print(f"error: no exposed part '{args.part_id}'", file=sys.stderr)
        return 1
    for i, card in enumerate(matches):
        if i:
            print()
        print(render_card_text(card))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="capability_cards")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List all exposed capability cards")
    list_parser.add_argument("--root", default=DEFAULT_ROOT, help="Root mirror path")
    list_parser.add_argument("--json", action="store_true", help="Output JSON array")

    show_parser = sub.add_parser("show", help="Show card(s) for a part-id")
    show_parser.add_argument("--root", default=DEFAULT_ROOT, help="Root mirror path")
    show_parser.add_argument("part_id", help="Part id to look up")

    args = parser.parse_args(argv)
    if args.command == "list":
        return cmd_list(args)
    if args.command == "show":
        return cmd_show(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
