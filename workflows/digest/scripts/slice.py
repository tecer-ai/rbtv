#!/usr/bin/env python3
"""Slice a source file into line-numbered chunks for the digest workflow.

Three modes:
- inspect: --inspect      (print density histogram, do not slice)
- naive: --size N         (slice every N lines)
- explicit: --breaks list (use given line numbers as boundaries)

Output (slice modes):
- <out>/chunk-NN.txt    each line prefixed with "<source-line>: "
- <out>/manifest.json   {"source", "total_lines", "chunks": {chunk_id: [start, end]}}

Output (inspect mode):
- stdout markdown table with one row per bucket of --bucket lines
"""

import argparse
import json
from pathlib import Path


def parse_args():
    p = argparse.ArgumentParser(description="Slice a source file into chunks.")
    p.add_argument("--source", required=True, help="Path to source file")
    p.add_argument("--out", help="Output directory for chunks (required unless --inspect)")
    p.add_argument("--encoding", default="utf-8", help="Source file encoding (default utf-8)")
    p.add_argument("--bucket", type=int, default=100, help="Inspect mode: histogram bucket size in lines (default 100)")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--inspect", action="store_true", help="Print density histogram and exit; no slicing")
    g.add_argument("--size", type=int, help="Naive slicing — chunk size in lines")
    g.add_argument("--breaks", help="Explicit line boundaries (comma-separated source line numbers)")
    args = p.parse_args()
    if not args.inspect and not args.out:
        p.error("--out is required unless --inspect is set")
    if args.bucket < 1:
        p.error("--bucket must be >= 1")
    return args


def inspect(src, lines, bucket):
    total_lines = len(lines)
    total_chars = sum(len(ln) for ln in lines)
    print(f"source: {src.name}  total_lines: {total_lines}  total_chars: {total_chars}")
    print("| bucket (lines) | chars | avg chars/line |")
    print("|----------------|-------|----------------|")
    for start in range(0, total_lines, bucket):
        end = min(start + bucket, total_lines)
        seg = lines[start:end]
        seg_chars = sum(len(ln) for ln in seg)
        seg_lines = end - start
        avg = seg_chars / seg_lines if seg_lines else 0
        print(f"| {start}-{end} | {seg_chars} | {avg:.0f} |")


def main():
    args = parse_args()
    src = Path(args.source)
    if not src.is_file():
        raise SystemExit(f"ERROR: source file not found: {src}")

    try:
        with open(src, encoding=args.encoding) as f:
            lines = f.readlines()
    except UnicodeDecodeError as e:
        raise SystemExit(f"ERROR: could not decode {src} as {args.encoding}: {e}")

    total = len(lines)
    if total == 0:
        raise SystemExit(f"ERROR: source file is empty: {src}")

    if args.inspect:
        inspect(src, lines, args.bucket)
        return

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.size is not None:
        if args.size < 1:
            raise SystemExit("ERROR: --size must be >= 1")
        boundaries = list(range(args.size, total, args.size))
    else:
        try:
            boundaries = [int(b.strip()) for b in args.breaks.split(",") if b.strip()]
        except ValueError as e:
            raise SystemExit(f"ERROR: invalid --breaks: {e}")
        boundaries = [b for b in boundaries if 0 < b < total]

    edges = [0] + sorted(set(boundaries)) + [total]
    manifest = {}
    for idx in range(len(edges) - 1):
        s, e = edges[idx], edges[idx + 1]
        chunk_id = f"chunk-{idx:02d}"
        path = out / f"{chunk_id}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# Source: {src.name} | lines {s+1}-{e} of {total}\n")
            for j, ln in enumerate(lines[s:e]):
                f.write(f"{s+j+1}: {ln}")
        manifest[chunk_id] = [s + 1, e]

    with open(out / "manifest.json", "w", encoding="utf-8") as f:
        json.dump({"source": str(src), "total_lines": total, "chunks": manifest}, f, indent=2)

    for chunk_id, (s, e) in manifest.items():
        print(f"{chunk_id}\t{s}-{e}")


if __name__ == "__main__":
    main()
