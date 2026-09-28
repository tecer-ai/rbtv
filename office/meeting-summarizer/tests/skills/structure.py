#!/usr/bin/env python3
"""Emit a markdown document's STRUCTURAL SKELETON, so "the format did not change" is checkable.

The skeleton is everything the owner's ruling protects — frontmatter keys, the heading tree, and
table column headers — with glossary terms masked, so that two runs of the same skill over the
same transcript differ ONLY where a term was corrected. Prose is excluded on purpose: it is the
part an LLM legitimately rewords, and it is not what "no new summary format" is about.

Usage:
    structure.py <doc.md> [--glossary <glossary.md>]     print the skeleton
    structure.py --diff <a.md> <b.md> [--glossary <g>]   exit 0 when skeletons are identical
"""
import argparse
import difflib
import re
import sys
import unicodedata
from pathlib import Path

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
FRONTMATTER_KEY = re.compile(r"^([A-Za-z0-9_-]+):")
DOUBT = re.compile(r"\{\{doubt\|term=[^|]*\|guess=[^}]*\}\}")
DATEISH = re.compile(r"\b\d{1,4}[-/]\d{1,2}[-/]\d{1,4}\b")


def _fold(s):
    """Lowercase, strip accents — the same insensitivity the glossary is matched under."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"
    )


def glossary_terms(path):
    """Every canonical name and transcription variation declared in a glossary file.

    Returns them longest-first so a longer variation is masked before a shorter substring of it.
    """
    terms = set()
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = TABLE_ROW.match(line)
        if not m or TABLE_SEP.match(line):
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) < 2 or cells[0].lower().startswith("nome correto"):
            continue
        terms.add(cells[0])
        for variation in cells[1].split(","):
            variation = variation.strip()
            if variation and variation not in {"-", "—"}:
                terms.add(variation)
    terms.discard("")
    return sorted(terms, key=len, reverse=True)


def mask(text, terms):
    """Replace every glossary term and every date with a placeholder.

    What survives is the structure. A skeleton difference therefore cannot be explained away as
    "only a corrected term" — the corrected terms are already gone.
    """
    out = DOUBT.sub("{DOUBT}", text)
    folded = _fold(out)
    for term in terms:
        ft = _fold(term)
        if not ft:
            continue
        start = 0
        while True:
            i = folded.find(ft, start)
            if i < 0:
                break
            out = out[:i] + "{TERM}" + " " * (len(ft) - len("{TERM}")) + out[i + len(ft):]
            folded = _fold(out)
            start = i + len(ft)
    out = re.sub(r"\s+", " ", out).strip()
    return DATEISH.sub("{DATE}", out)


def skeleton(doc_path, glossary_path=None):
    terms = glossary_terms(glossary_path) if glossary_path else []
    lines = Path(doc_path).read_text(encoding="utf-8").splitlines()
    rows, in_frontmatter, seen_table = [], False, set()
    for n, line in enumerate(lines):
        if n == 0 and line.strip() == "---":
            in_frontmatter = True
            rows.append("frontmatter:open")
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
                rows.append("frontmatter:close")
            else:
                key = FRONTMATTER_KEY.match(line)
                if key:
                    rows.append(f"frontmatter:key {key.group(1)}")
            continue
        h = HEADING.match(line)
        if h:
            rows.append(f"h{len(h.group(1))} {mask(h.group(2), terms)}")
            continue
        t = TABLE_ROW.match(line)
        if t and not TABLE_SEP.match(line):
            header = "|".join(mask(c.strip(), terms) for c in t.group(1).split("|"))
            # only the FIRST row of each table is its column header; later rows are data
            if header not in seen_table and n + 1 < len(lines) and TABLE_SEP.match(lines[n + 1]):
                seen_table.add(header)
                rows.append(f"table-header {header}")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("docs", nargs="+")
    ap.add_argument("--glossary")
    ap.add_argument("--diff", action="store_true")
    args = ap.parse_args()

    if args.diff:
        if len(args.docs) != 2:
            ap.error("--diff takes exactly two documents")
        a, b = (skeleton(d, args.glossary) for d in args.docs)
        delta = list(difflib.unified_diff(a, b, fromfile=args.docs[0], tofile=args.docs[1], lineterm=""))
        if delta:
            print("\n".join(delta))
            print(f"\nSTRUCTURAL-DIFF: {len([d for d in delta if d[:1] in '+-' and d[:3] not in ('+++', '---')])} line(s) differ")
            return 1
        print(f"STRUCTURAL-DIFF: EMPTY ({len(a)} skeleton rows compared)")
        return 0

    for doc in args.docs:
        for row in skeleton(doc, args.glossary):
            print(row)
    return 0


if __name__ == "__main__":
    sys.exit(main())
