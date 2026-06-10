#!/usr/bin/env python3
"""Deterministic component measurement for the component-review workflow.

Usage:
    python measure-component.py PATH [PATH ...]

PATH may be a file or a directory (directories are walked recursively).
Emits markdown tables to stdout:
  1. Per-file metrics: lines, words, imperative count, conditional lines,
     cross-file references.
  2. Duplicated blocks: contiguous runs of 12-word shingles shared between
     file pairs, with approximate duplicated word mass.

Exit codes: 0 = ok, 1 = unreadable input path, 2 = no measurable files found.
Stdlib only. No network. Read-only.
"""

import os
import re
import sys
from collections import defaultdict

TEXT_EXTS = {".md", ".py", ".yaml", ".yml", ".xml", ".json", ".csv", ".txt"}
SHINGLE = 12  # words per shingle for duplication detection
MIN_SHARED_RUNS = 1  # report a pair if it shares at least one run

IMPERATIVE_RE = re.compile(r"\b(MUST|NEVER|ALWAYS|STOP)\b")  # case-sensitive
CONDITIONAL_RE = re.compile(r"(^|\s)(if|when)\s", re.IGNORECASE)
CROSSREF_RE = re.compile(r"[\w\-./{}]+\.(?:md|py|yaml|yml|xml|csv|json)\b")


def collect_files(paths):
    files, errors = [], []
    for p in paths:
        if os.path.isfile(p):
            files.append(p)
        elif os.path.isdir(p):
            for root, _dirs, names in os.walk(p):
                for n in sorted(names):
                    if os.path.splitext(n)[1].lower() in TEXT_EXTS:
                        files.append(os.path.join(root, n))
        else:
            errors.append(p)
    return sorted(set(files)), errors


def normalize_words(text):
    return re.sub(r"\s+", " ", text.lower()).split(" ")


def file_metrics(path, text):
    lines = text.splitlines()
    words = [w for w in re.split(r"\s+", text) if w]
    imperatives = len(IMPERATIVE_RE.findall(text))
    conditionals = sum(1 for ln in lines if CONDITIONAL_RE.search(ln))
    self_name = os.path.basename(path)
    refs = [m for m in CROSSREF_RE.findall(text)]
    crossrefs = sum(1 for m in CROSSREF_RE.finditer(text)
                    if os.path.basename(m.group(0)) != self_name)
    return {
        "lines": len(lines),
        "words": len(words),
        "imperatives": imperatives,
        "conditionals": conditionals,
        "crossrefs": crossrefs,
    }


def shingles_of(words):
    return [tuple(words[i:i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)]


def duplicated_runs(words_a, shingle_set_b):
    """Maximal contiguous runs in A whose shingles all appear in B.

    Returns a list of run lengths in shingles; approximate duplicated words
    per run = run_length + SHINGLE - 1.
    """
    runs, current = [], 0
    for sh in shingles_of(words_a):
        if sh in shingle_set_b:
            current += 1
        else:
            if current:
                runs.append(current)
            current = 0
    if current:
        runs.append(current)
    return runs


def main(argv):
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 1
    files, errors = collect_files(argv[1:])
    for e in errors:
        print(f"ERROR: path not found: {e}", file=sys.stderr)
    if errors:
        return 1
    if not files:
        print("ERROR: no measurable files found", file=sys.stderr)
        return 2

    texts, metrics = {}, {}
    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                texts[f] = fh.read()
        except OSError as exc:
            print(f"ERROR: cannot read {f}: {exc}", file=sys.stderr)
            return 1
        metrics[f] = file_metrics(f, texts[f])

    base = os.path.commonpath(files) if len(files) > 1 else os.path.dirname(files[0])

    print("## Per-File Metrics\n")
    print("| File | Lines | Words | Imperatives | Conditional lines | Cross-file refs |")
    print("|------|------:|------:|------------:|------------------:|----------------:|")
    totals = defaultdict(int)
    for f in files:
        m = metrics[f]
        rel = os.path.relpath(f, base)
        print(f"| {rel} | {m['lines']} | {m['words']} | {m['imperatives']} "
              f"| {m['conditionals']} | {m['crossrefs']} |")
        for k, v in m.items():
            totals[k] += v
    print(f"| **TOTAL ({len(files)} files)** | **{totals['lines']}** | **{totals['words']}** "
          f"| **{totals['imperatives']}** | **{totals['conditionals']}** | **{totals['crossrefs']}** |")

    words_by_file = {f: normalize_words(texts[f]) for f in files}
    shingle_sets = {f: set(shingles_of(words_by_file[f])) for f in files}

    print("\n## Duplicated Blocks (12-word shingle runs shared between files)\n")
    rows = []
    for i, fa in enumerate(files):
        for fb in files[i + 1:]:
            if not shingle_sets[fb]:
                continue
            runs = duplicated_runs(words_by_file[fa], shingle_sets[fb])
            if len(runs) >= MIN_SHARED_RUNS and runs:
                approx = sum(r + SHINGLE - 1 for r in runs)
                rows.append((approx, os.path.relpath(fa, base),
                             os.path.relpath(fb, base), len(runs)))
    if not rows:
        print("No duplicated blocks detected at the 12-word threshold.")
    else:
        print("| File A | File B | Shared runs | Approx duplicated words |")
        print("|--------|--------|------------:|------------------------:|")
        for approx, fa, fb, n in sorted(rows, reverse=True):
            print(f"| {fa} | {fb} | {n} | {approx} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
