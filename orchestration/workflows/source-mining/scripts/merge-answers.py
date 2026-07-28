#!/usr/bin/env python3
"""Merge a caller-supplied answers file into a source-mining questions file (task 7.92, RESUME half).

The RESTRICTIONS half of the RESUME mechanism (machine-enforced) — the counterpart to
`step-05-synthesize.md` § Resuming a Hand-Back (the CONSTRAINTS half, a workflow instruction).
Together they let a caller answer a headless hand-back's recorded questions and re-enter the
workflow at step-06 against the SAME `runtime_root` the hand-back named, in place (task 7.92
criterion 1(c) — no new catalog row, no new entry point, zero bytes of `ignite/`).

Both `open-questions.md` (reconcile) and `reflection-prompts.md` (study) share one block format
(`step-05-synthesize.md` § 2B.2: "same Q-block format as 2A.4"), so this script is mode-agnostic:

    ### Q{N}: <summary>
    - Source: ...
    - ...
    - Rationale: ...

A live interactive run appends the resolution as `- Answer: <user response>` (2A.5 / 2B.3). This
script performs the identical append, driven by a caller-supplied answers file instead of a live
user — the deterministic, verifiable half of the merge (rbtv-deterministic-first's Compute arm:
an exact text transform, never LLM reasoning).

Usage:
    python3 merge-answers.py --questions <path> --answers <path> --in-place
    python3 merge-answers.py --questions <path> --answers <path> --out <path>

Answers file: a JSON object mapping "Q<N>" (string) -> answer text (string), e.g.:
    {"Q1": "B - the enforcement-locus tension", "Q3": "A - pursue the tension only"}

Fail-closed coverage rule, mirroring 2A.5's "do NOT proceed to step-06 until every Q has a
recorded answer": the merge is refused (nothing written) unless every `### Q{N}:` block found in
the questions file ends up answered — by this run or already-answered from a prior one — AND
every key in the answers file matches a real question. A Q block that already carries an
`- Answer:` line is left untouched; supplying an answer for it again is refused as ambiguous
(silently overwriting a recorded answer is the exact failure mode `bars.md` 11 warns about: a
check -- here, a merge -- that can silently do the wrong thing under a plausible input).

Exit codes:
  0  every question in the file is answered (this run's merge, or already-answered); file written
  1  usage/IO error (bad args, file not found, unparseable JSON/questions file)
  2  merge refused — coverage gap, unmatched answer key, or an attempt to re-answer an already-
     answered question; the JSON summary on stdout names exactly which, and nothing is written
"""

import argparse
import json
import re
import sys
from pathlib import Path

Q_HEADER_RE = re.compile(r"^### (Q\d+):", re.MULTILINE)
ANSWER_LINE_RE = re.compile(r"^- Answer:", re.MULTILINE)
ANSWER_KEY_RE = re.compile(r"^Q\d+$")


def parse_args():
    p = argparse.ArgumentParser(description="Merge answers into a source-mining questions file.")
    p.add_argument("--questions", required=True, help="path to open-questions.md or reflection-prompts.md")
    p.add_argument("--answers", required=True, help="path to a JSON file mapping Q<N> -> answer text")
    out = p.add_mutually_exclusive_group(required=True)
    out.add_argument("--in-place", action="store_true", help="overwrite --questions with the merged result")
    out.add_argument("--out", help="write the merged result to this path instead")
    return p.parse_args()


def split_blocks(text):
    """Return [(qid, start, end)] for every ### Q{N}: block; end is exclusive (next header or EOF)."""
    headers = list(Q_HEADER_RE.finditer(text))
    blocks = []
    for i, m in enumerate(headers):
        start = m.start()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        blocks.append((m.group(1), start, end))
    return blocks


def main():
    args = parse_args()
    questions_path = Path(args.questions)
    answers_path = Path(args.answers)

    if not questions_path.is_file():
        print(json.dumps({"ok": False, "error": f"questions file not found: {questions_path}"}))
        return 1
    if not answers_path.is_file():
        print(json.dumps({"ok": False, "error": f"answers file not found: {answers_path}"}))
        return 1

    text = questions_path.read_text(encoding="utf-8")
    try:
        answers = json.loads(answers_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(json.dumps({"ok": False, "error": f"answers file is not valid JSON: {exc}"}))
        return 1
    if not isinstance(answers, dict):
        print(json.dumps({"ok": False, "error": "answers file must be a JSON object of Q<N> -> text"}))
        return 1
    bad_keys = [k for k in answers if not ANSWER_KEY_RE.match(k)]
    if bad_keys:
        print(json.dumps({"ok": False, "error": "answers keys must match Q<N>", "bad_keys": bad_keys}))
        return 1

    blocks = split_blocks(text)
    if not blocks:
        print(json.dumps({"ok": False, "error": f"no '### Q<N>:' blocks found in {questions_path}"}))
        return 1

    found_qids = {qid for qid, _, _ in blocks}
    already_answered = {
        qid for qid, start, end in blocks if ANSWER_LINE_RE.search(text[start:end])
    }
    unmatched_keys = sorted(set(answers) - found_qids)
    reanswer_conflicts = sorted(set(answers) & already_answered)
    missing = sorted(found_qids - set(answers) - already_answered)

    if unmatched_keys or reanswer_conflicts or missing:
        print(json.dumps({
            "ok": False,
            "questions_file": str(questions_path),
            "found_questions": sorted(found_qids),
            "unmatched_answer_keys": unmatched_keys,
            "reanswer_conflicts": reanswer_conflicts,
            "missing_answers": missing,
        }, indent=2))
        return 2

    # Build the merged text back-to-front so earlier offsets stay valid as we splice.
    merged = text
    for qid, start, end in sorted(blocks, key=lambda b: b[1], reverse=True):
        if qid not in answers:
            continue  # already answered in a prior pass; left untouched
        block = merged[start:end]
        insertion = f"- Answer: {answers[qid]}\n"
        if block.endswith("\n\n"):
            block = block[:-1] + insertion + "\n"
        elif block.endswith("\n"):
            block = block + insertion
        else:
            block = block + "\n" + insertion
        merged = merged[:start] + block + merged[end:]

    out_path = questions_path if args.in_place else Path(args.out)
    out_path.write_text(merged, encoding="utf-8")

    print(json.dumps({
        "ok": True,
        "questions_file": str(out_path),
        "merged_this_run": sorted(answers),
        "already_answered_before": sorted(already_answered),
        "total_questions": len(found_qids),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
