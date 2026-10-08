#!/usr/bin/env python3
"""digest: the exact steps of mining a source too long to read directly.

Verbs:
  inspect         measure a source and suggest a chunk size
  slice           cut a source into line-numbered chunk files
  adjust          compute chunk boundaries from boundary-review files
  check           verify one extraction file per chunk and count its findings
  merge-answers   append answers to a questions file

Result fields print on standard output as `name value` lines. A run that fails
prints nothing on standard output and prints `error:` and `next:` (the next
invocation) on standard error. Exit status: 0 success, 1 the operation failed,
2 the invocation itself is invalid. `digest VERB -h` describes one verb.
"""

import argparse
import json
import re
import sys
from inspect import cleandoc
from pathlib import Path

TARGET_CHARS = 30000
ONE_CHUNK_BELOW = 45000
TWO_CHUNKS_BELOW = 60000


class Fail(Exception):
    def __init__(self, message, next_invocation):
        super().__init__(message)
        self.next_invocation = next_invocation


def read_lines(path, encoding, retry):
    src = Path(path)
    if not src.is_file():
        raise Fail(f"source file not found: {src}", retry)
    try:
        lines = src.read_text(encoding=encoding).splitlines(keepends=True)
    except (UnicodeDecodeError, LookupError) as exc:
        raise Fail(f"could not decode {src} as {encoding}: {exc}", retry + " --encoding ENCODING")
    if not lines:
        raise Fail(f"source file is empty: {src}", retry)
    return src, lines


def inspect(args):
    """Measure a source and suggest a chunk size. Reads SOURCE; writes nothing.

    Prints: source, total_lines, total_chars, mean_chars_per_line,
    dense_chars_per_line (the densest bucket), chunk_lines and chunks (about
    30,000 characters per chunk; one chunk under 45,000 characters, two under
    60,000), chunk_lines_dense and chunks_dense (the same, sized by the densest
    bucket), then one `bucket FIRST-LAST chars N avg N` line per bucket.

    Example: digest inspect transcript.txt
    """
    retry = "digest inspect SOURCE"
    if args.bucket < 1:
        raise Fail("--bucket must be at least 1", retry + " --bucket 100")
    src, lines = read_lines(args.source, args.encoding, retry)
    total_lines = len(lines)
    total_chars = sum(len(ln) for ln in lines)
    buckets = []
    for start in range(0, total_lines, args.bucket):
        seg = lines[start:start + args.bucket]
        chars = sum(len(ln) for ln in seg)
        buckets.append((start, start + len(seg), chars, chars / len(seg)))
    mean = total_chars / total_lines
    dense = max(b[3] for b in buckets)

    def lines_per_chunk(avg):
        if total_chars < ONE_CHUNK_BELOW:
            return total_lines
        if total_chars < TWO_CHUNKS_BELOW:
            return -(-total_lines // 2)
        return max(1, round(TARGET_CHARS / avg))

    size, size_dense = lines_per_chunk(mean), lines_per_chunk(dense)
    print(f"source {src.name}")
    print(f"total_lines {total_lines}")
    print(f"total_chars {total_chars}")
    print(f"mean_chars_per_line {mean:.0f}")
    print(f"dense_chars_per_line {dense:.0f}")
    print(f"chunk_lines {size}")
    print(f"chunks {-(-total_lines // size)}")
    print(f"chunk_lines_dense {size_dense}")
    print(f"chunks_dense {-(-total_lines // size_dense)}")
    for start, end, chars, avg in buckets:
        print(f"bucket {start + 1}-{end} chars {chars} avg {avg:.0f}")


def slice_source(args):
    """Cut a source into line-numbered chunk files. Reads SOURCE; writes
    chunk-NN.txt (UTF-8, each line prefixed `N: `) and manifest.json into --out,
    creating the folder.

    --size N cuts every N lines. --breaks A,B cuts after source lines A and B;
    each break is a line number from 1 to the last line but one, and an empty
    value gives one chunk.

    Prints: chunks, then one `chunk-NN FIRST-LAST` line per chunk.

    Example: digest slice transcript.txt --out run/chunks --size 400
    """
    retry = "digest slice SOURCE --out DIR"
    src, lines = read_lines(args.source, args.encoding, retry + " --size 400")
    total = len(lines)
    if args.size is not None:
        if args.size < 1:
            raise Fail("--size must be at least 1", retry + " --size 400")
        boundaries = list(range(args.size, total, args.size))
    else:
        retry += " --breaks 690,1300"
        try:
            boundaries = [int(b) for b in args.breaks.split(",") if b.strip()]
        except ValueError as exc:
            raise Fail(f"invalid --breaks: {exc}", retry)
        outside = [b for b in boundaries if not 0 < b < total]
        if outside:
            raise Fail(f"--breaks outside 1-{total - 1} for a source of {total} lines: "
                       + ",".join(str(b) for b in outside), retry)
    edges = [0] + sorted(set(boundaries)) + [total]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for idx in range(len(edges) - 1):
        start, end = edges[idx], edges[idx + 1]
        chunk_id = f"chunk-{idx:02d}"
        with open(out / f"{chunk_id}.txt", "w", encoding="utf-8", newline="\n") as f:
            f.write(f"# Source: {src.name} | lines {start + 1}-{end} of {total}\n")
            for number, ln in enumerate(lines[start:end], start + 1):
                f.write(f"{number}: {ln.rstrip(chr(10)).rstrip(chr(13))}\n")
        manifest[chunk_id] = [start + 1, end]
    (out / "manifest.json").write_text(
        json.dumps({"source": str(src), "total_lines": total, "chunks": manifest}, indent=2) + "\n",
        encoding="utf-8")
    print(f"chunks {len(manifest)}")
    for chunk_id, (start, end) in manifest.items():
        print(f"{chunk_id} {start}-{end}")


def load_chunks(directory, next_invocation):
    path = Path(directory) / "manifest.json"
    if not path.is_file():
        raise Fail(f"no manifest.json in {directory}", next_invocation)
    try:
        chunks = json.loads(path.read_text(encoding="utf-8"))["chunks"]
        return {chunk_id: (int(first), int(last)) for chunk_id, (first, last) in chunks.items()}
    except (ValueError, KeyError, TypeError, AttributeError):
        raise Fail(f"{path} is not a manifest written by digest slice",
                   "digest slice SOURCE --out DIR --size 400, then " + next_invocation)


def yaml_value(text, key):
    m = re.search(rf"^{key}:[ \t]*(\S.*?)[ \t]*$", text, re.MULTILINE)
    if not m or m.group(1) == "null":
        return None
    return m.group(1)


def suggested_line(path, text, key, line_range, retry):
    """The line a boundary review suggests under `key`, or None when it gives none."""
    value = yaml_value(text, key)
    if value is None:
        return None
    first, last = line_range
    if not value.isdigit() or not first <= int(value) <= last:
        raise Fail(f"{path}: {key} is '{value}', not a line number inside {first}-{last}",
                   f"re-run the boundary review that writes {path}, then " + retry)
    return int(value)


def adjust(args):
    """Compute chunk boundaries from boundary reviews. Reads manifest.json in
    --chunks and one chunk-NN.yaml per chunk in --boundaries; writes nothing.

    A chunk whose review says `end_clean: false` ends at its `suggest_end_at`;
    otherwise, when the next chunk says `start_clean: false`, the chunk ends on
    the line before that chunk's `suggest_start_at`. A boundary with no
    suggestion stays where it is.

    Prints: breaks (the value for `slice --breaks`), then one
    `boundary ORIGINAL ADJUSTED REASON` line per boundary.

    Example: digest adjust --chunks run/chunks-naive --boundaries run/boundaries
    """
    retry = "digest adjust --chunks CHUNKS_DIR --boundaries BOUNDARIES_DIR"
    chunks = load_chunks(args.chunks, retry)
    ids = list(chunks)
    reviews = {}
    for chunk_id in ids:
        path = Path(args.boundaries) / f"{chunk_id}.yaml"
        if not path.is_file():
            raise Fail(f"missing boundary review: {path}", retry)
        reviews[chunk_id] = path.read_text(encoding="utf-8")
    rows, breaks = [], []
    review = Path(args.boundaries)
    for before, after in zip(ids, ids[1:]):
        original = chunks[before][1]
        adjusted, reason = original, "unchanged"
        if yaml_value(reviews[before], "end_clean") == "false":
            suggestion = suggested_line(review / f"{before}.yaml", reviews[before], "suggest_end_at",
                                        chunks[before], retry)
            if suggestion:
                adjusted, reason = suggestion, f"{before} end not clean"
            else:
                reason = f"{before} end not clean, no suggestion"
        elif yaml_value(reviews[after], "start_clean") == "false":
            suggestion = suggested_line(review / f"{after}.yaml", reviews[after], "suggest_start_at",
                                        chunks[after], retry)
            if suggestion:
                adjusted, reason = suggestion - 1, f"{after} start not clean"
            else:
                reason = f"{after} start not clean, no suggestion"
        if breaks and adjusted <= breaks[-1]:
            raise Fail(f"the reviews leave {before} empty: it would start after line {breaks[-1]} "
                       f"and end at line {adjusted}",
                       f"re-run the boundary review of {before}, then " + retry)
        breaks.append(adjusted)
        rows.append((original, adjusted, reason))
    print("breaks " + ",".join(str(b) for b in breaks))
    for original, adjusted, reason in rows:
        print(f"boundary {original} {adjusted} {reason}")


def check(args):
    """Verify one extraction file per chunk and count its findings. Reads
    manifest.json in --chunks and chunk-NN.yaml in --extractions; writes nothing.

    Prints: total_findings, then one `chunk-NN findings N` line per chunk.
    Fails when a chunk's file is missing or lacks `source:`, `chunk:` or
    `findings:`, or when no chunk holds a finding; the error lists every chunk
    as `missing`, `malformed` or `findings N`.

    Example: digest check --chunks run/chunks --extractions run/extractions
    """
    retry = "digest check --chunks CHUNKS_DIR --extractions EXTRACTIONS_DIR"
    chunks = load_chunks(args.chunks, retry)
    report, problems, total = [], [], 0
    for chunk_id in chunks:
        path = Path(args.extractions) / f"{chunk_id}.yaml"
        if not path.is_file():
            report.append(f"{chunk_id} missing")
            problems.append(chunk_id)
            continue
        text = path.read_text(encoding="utf-8")
        if not all(re.search(rf"^{key}:", text, re.MULTILINE) for key in ("source", "chunk", "findings")):
            report.append(f"{chunk_id} malformed")
            problems.append(chunk_id)
            continue
        count = len(re.findall(r"^  - (?:decision|kind):", text, re.MULTILINE))
        total += count
        report.append(f"{chunk_id} findings {count}")
    if problems or total == 0:
        why = f"missing or malformed: {', '.join(problems)}" if problems else "no findings in any chunk"
        raise Fail(why + "\n" + "\n".join(report), "re-run the extraction tasks for the listed chunks, then " + retry)
    print(f"total_findings {total}")
    print("\n".join(report))


def merge_answers(args):
    """Append `- Answer:` lines to a questions file. Reads --questions (blocks
    headed `### Q<N>:`) and --answers (a JSON object mapping "Q<N>" to answer
    text); writes --questions itself with --in-place, or the file named by --out.

    Refuses, writing nothing, unless the answers cover exactly the questions
    that have no `- Answer:` line yet.

    Prints: merged (the keys written), already_answered, questions_file.

    Example: digest merge-answers --questions run/synthesis/open-questions.md --answers answers.json --in-place
    """
    retry = ("digest merge-answers --questions QUESTIONS_FILE --answers ANSWERS_JSON "
             "--in-place")
    questions, answers_file = Path(args.questions), Path(args.answers)
    for path in (questions, answers_file):
        if not path.is_file():
            raise Fail(f"file not found: {path}", retry)
    text = questions.read_text(encoding="utf-8")
    try:
        answers = json.loads(answers_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise Fail(f"answers file is not valid JSON: {exc}", retry)
    if not isinstance(answers, dict) or any(not re.fullmatch(r"Q\d+", str(k)) for k in answers):
        raise Fail("answers file must be a JSON object mapping Q<N> to answer text", retry)
    headers = list(re.finditer(r"^### (Q\d+):", text, re.MULTILINE))
    if not headers:
        raise Fail(f"no '### Q<N>:' blocks in {questions}", retry)
    blocks = []
    for i, m in enumerate(headers):
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        blocks.append((m.group(1), m.start(), end))
    found = {qid for qid, _, _ in blocks}
    answered = {qid for qid, s, e in blocks if re.search(r"^- Answer:", text[s:e], re.MULTILINE)}
    unmatched = sorted(set(answers) - found)
    reanswered = sorted(set(answers) & answered)
    missing = sorted(found - set(answers) - answered)
    if unmatched or reanswered or missing:
        raise Fail(f"merge refused, nothing written. unmatched answer keys: {unmatched or 'none'}; "
                   f"already answered: {reanswered or 'none'}; unanswered questions: {missing or 'none'}",
                   "fix the answers file so it holds exactly the unanswered questions, then " + retry)
    merged = text
    for qid, start, end in sorted(blocks, key=lambda b: b[1], reverse=True):
        if qid not in answers:
            continue
        block = merged[start:end]
        line = f"- Answer: {answers[qid]}\n"
        if block.endswith("\n\n"):
            block = block[:-1] + line + "\n"
        else:
            block = block + ("" if block.endswith("\n") else "\n") + line
        merged = merged[:start] + block + merged[end:]
    out = questions if args.in_place else Path(args.out)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(merged)
    print(f"merged {','.join(sorted(answers))}")
    print(f"already_answered {','.join(sorted(answered)) or 'none'}")
    print(f"questions_file {out}")


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, f"error: {message}\nnext: {self.prog} -h\n")


def parser():
    p = Parser(prog="digest", description=__doc__,
               formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="verb", required=True, metavar="VERB")

    def verb(name, run):
        s = sub.add_parser(name, description=cleandoc(run.__doc__),
                           formatter_class=argparse.RawDescriptionHelpFormatter)
        s.set_defaults(run=run)
        return s

    s = verb("inspect", inspect)
    s.add_argument("source", metavar="SOURCE", help="the file to measure")
    s.add_argument("--bucket", type=int, default=100, help="bucket size in lines (default 100)")
    s.add_argument("--encoding", default="utf-8", help="encoding of SOURCE (default utf-8)")

    s = verb("slice", slice_source)
    s.add_argument("source", metavar="SOURCE", help="the file to cut")
    s.add_argument("--out", required=True, metavar="DIR", help="folder for chunk-NN.txt files and manifest.json")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--size", type=int, metavar="N", help="lines per chunk")
    g.add_argument("--breaks", metavar="A,B", help="comma-separated last line of each chunk but the final one")
    s.add_argument("--encoding", default="utf-8", help="encoding of SOURCE (default utf-8)")

    s = verb("adjust", adjust)
    s.add_argument("--chunks", required=True, metavar="DIR", help="folder holding the sliced chunks' manifest.json")
    s.add_argument("--boundaries", required=True, metavar="DIR", help="folder holding one chunk-NN.yaml review per chunk")

    s = verb("check", check)
    s.add_argument("--chunks", required=True, metavar="DIR", help="folder holding the final chunks' manifest.json")
    s.add_argument("--extractions", required=True, metavar="DIR", help="folder holding one chunk-NN.yaml per chunk")

    s = verb("merge-answers", merge_answers)
    s.add_argument("--questions", required=True, metavar="FILE", help="file of '### Q<N>:' blocks")
    s.add_argument("--answers", required=True, metavar="FILE", help="JSON file mapping Q<N> to answer text")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--in-place", action="store_true", help="write the answers into --questions")
    g.add_argument("--out", metavar="FILE", help="write the merged file here instead")
    return p


def main():
    args = parser().parse_args()
    try:
        args.run(args)
    except Fail as exc:
        print(f"error: {exc}\nnext: {exc.next_invocation}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
