#!/usr/bin/env python3
"""Check "the format did not change" against each skill's OWN declared output format.

The owner's ruling is that the summary FORMAT must not change. A skill's format is the set of
sections its own text declares — the therapy skill's `### Output Format` block, the meeting
workflow's selected summary prompt. Everything else in a produced summary is CONTENT the
transcript supplied: the per-topic sub-sections the therapy skill orders it to emit one per topic,
the document title, and (for the meeting path) frontmatter, which no meeting prompt declares at
all.

So the comparison here is: the ORDERED SEQUENCE OF DECLARED SECTIONS each summary actually
carries. A section added, removed, reordered or reworded shows up. A differently-worded topic
title or a differently-named frontmatter key does not, because neither is format — and the
measured proof of that is the criterion-10 control, where two runs of the BYTE-IDENTICAL
unedited skill differ in exactly those two places and in no declared section.

Usage:
  format_contract.py declared  <contract.md>...            list the declared sections
  format_contract.py sections  <summary.md> --contract C   the declared sequence a summary carries
  format_contract.py diff <a.md> <b.md> --contract C       exit 0 when the sequences are identical
"""
import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):")


def norm(s):
    s = re.sub(r"[*_`]", "", s)
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s).strip()
    return s.rstrip(":").strip()


def headings(path):
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = HEADING.match(line)
        if m:
            yield len(m.group(1)), m.group(2)


def declared(contracts):
    """Every section heading the skill's own format declaration names."""
    out = {}
    for c in contracts:
        for level, text in headings(c):
            n = norm(text)
            if n and n not in out:
                out[n] = text.strip()
    return out


def sections(summary, decl):
    """The ordered sequence of DECLARED sections this summary carries.

    An undeclared heading becomes {SLOT}; runs of identical slots at one level collapse, because
    how many topics a transcript produced is content, not format.
    """
    rows, last = [], None
    for level, text in headings(summary):
        n = norm(text)
        row = f"h{level} {decl[n]}" if n in decl else f"h{level} {{SLOT}}"
        if row.endswith("{SLOT}") and row == last:
            continue
        rows.append(row)
        last = row
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["declared", "sections", "diff"])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--contract", action="append", default=[])
    ap.add_argument("--conditional", action="append", default=[],
                    help="a section the SKILL ITSELF declares as conditional; a difference in it is\nreported as allowed rather than structural, and must be named here to be allowed")
    args = ap.parse_args()

    if args.mode == "declared":
        for n, t in declared(args.files).items():
            print(t)
        return 0

    decl = declared(args.contract)
    if args.mode == "sections":
        for r in sections(args.files[0], decl):
            print(r)
        return 0

    a, b = (sections(f, decl) for f in args.files[:2])
    delta = [d for d in difflib.unified_diff(a, b, fromfile=args.files[0], tofile=args.files[1], lineterm="")]
    changed = [d for d in delta if d[:1] in "+-" and d[:3] not in ("+++", "---")]
    conditional = {norm(c) for c in args.conditional}
    structural = [d for d in changed if norm(d[1:].split(" ", 1)[-1]) not in conditional]
    if delta:
        print("\n".join(delta))
    for d in changed:
        kind = "STRUCTURAL" if d in structural else "declared-conditional (allowed, named on the command line)"
        print(f"  {d}  <- {kind}")
    print(f"\nFORMAT-DIFF: {len(structural)} structural line(s), "
          f"{len(changed) - len(structural)} declared-conditional line(s), "
          f"{len(a)} declared sections compared")
    return 1 if structural else 0


if __name__ == "__main__":
    sys.exit(main())
