#!/usr/bin/env python3
"""research-check: check a research report against the fixed report form.

The form is stated in ../../methods/researching-with-sources.md. This program
checks form and arithmetic only: it cannot tell whether a score or a link
status is true.
"""
from __future__ import annotations

import argparse
import re
import sys

LEGEND = ("> **Legend:** TS = Total Score (average of AT, TR, TM) | AT = Authority | "
          "TR = Trustability | TM = Topic Match | Scale: 1-10 | Threshold: TS ≥ 6")
NONE_DISCARDED = "No sources discarded — all sources met TS ≥ 6 threshold."
DISCARDED_HEADER = re.compile(r"^\|\s*Source\s*\|\s*TS\s*\|\s*Reason\s*\|$")
THRESHOLD = 6
PROHIBITED = ("sophisticated", "revolutionary", "cutting-edge", "best-in-class",
              "industry-leading", "game-changing", "transformative")
PROHIBITED_RE = re.compile(r"(?<![\w-])(" + "|".join(PROHIBITED) + r")(?![\w-])", re.IGNORECASE)

_NUM = r"\d+(?:\.\d+)?"
SOURCE_RE = re.compile(
    r"^\[(?P<id>\d+[a-z]?)\] (?P<title>.+?) — (?P<url>https?://\S+) — "
    r"(?P<researched>\d{4}-\d{2}-\d{2}) — (?P<dated>.+?) — "
    rf"TS:(?P<ts>{_NUM}) \(AT:(?P<at>{_NUM}) TR:(?P<tr>{_NUM}) TM:(?P<tm>{_NUM})\) — "
    r"(?P<status>✓ Verified|⚠ Redirect → \S.*|✗ Broken)$"
)
SOURCE_FORM = ("[n] Title — URL — YYYY-MM-DD — Source Date — TS:x (AT:x TR:x TM:x) — "
               "✓ Verified | ⚠ Redirect → <destination> | ✗ Broken")
CITATION_RE = re.compile(r"\[(\d+[a-z]?)\](?!\()")
HEADING_RE = re.compile(r"^#{1,6}\s+(.*?)\s*$")


def _section(lines: list[str], title: str) -> tuple[int, int] | None:
    """Return (first, end) line indexes of the body under the heading `title`."""
    for i, line in enumerate(lines):
        m = HEADING_RE.match(line)
        if m and m.group(1).lower() == title.lower():
            end = next((j for j in range(i + 1, len(lines)) if HEADING_RE.match(lines[j])),
                       len(lines))
            return i + 1, end
    return None


def check(text: str) -> list[tuple[int, str]]:
    """Return findings as (line number, message); line 0 means the whole report."""
    lines = text.splitlines()
    findings: list[tuple[int, str]] = []

    if LEGEND not in (line.strip() for line in lines):
        findings.append((0, f"the legend line is missing or altered; write it exactly: {LEGEND}"))

    sources = _section(lines, "Sources")
    discarded = _section(lines, "Sources Discarded")
    listed: dict[str, int] = {}

    if sources is None:
        findings.append((0, f"no '## Sources' section; add it with one line per source: {SOURCE_FORM}"))
    else:
        for i in range(*sources):
            line = lines[i].strip()
            if line.startswith("- "):
                line = line[2:]
            if not line:
                continue
            m = SOURCE_RE.match(line)
            if not m:
                findings.append((i + 1, f"source line is not in the form: {SOURCE_FORM}"))
                continue
            if m["id"] in listed:
                findings.append((i + 1, f"source [{m['id']}] is already listed on line "
                                        f"{listed[m['id']]}; give each source its own number"))
            listed[m["id"]] = i + 1
            scores = [float(m[k]) for k in ("at", "tr", "tm")]
            if any(not 1 <= s <= 10 for s in scores):
                findings.append((i + 1, "AT, TR and TM are each between 1 and 10"))
                continue
            mean = sum(scores) / 3
            ts = float(m["ts"])
            if abs(ts - mean) > 0.05 + 1e-9 and ts != round(mean):
                findings.append((i + 1, f"TS:{m['ts']} is not the average of AT, TR and TM; "
                                        f"the average is {mean:.1f}"))
            if mean < THRESHOLD:
                findings.append((i + 1, f"a source with TS below {THRESHOLD} supports no claim; move "
                                        "it to Sources Discarded and remove its citations"))
        if not listed:
            findings.append((sources[0], "the Sources section lists no source"))

    if discarded is None:
        findings.append((0, "no '## Sources Discarded' section; add it with the table "
                            "| Source | TS | Reason |, or the sentence: " + NONE_DISCARDED))
    else:
        body = [lines[i].strip() for i in range(*discarded) if lines[i].strip()]
        rows = [b for b in body if b.startswith("|")]
        has_table = (len(rows) >= 3 and DISCARDED_HEADER.match(rows[0])
                     and set(rows[1]) <= set("|-: "))
        if not has_table and NONE_DISCARDED not in body:
            findings.append((discarded[0], "Sources Discarded holds neither the table "
                                           "| Source | TS | Reason | with a row per source, "
                                           "nor the sentence: " + NONE_DISCARDED))

    skip = set()
    for span in (sources, discarded):
        if span:
            skip.update(range(*span))
    cited: set[str] = set()
    for i, line in enumerate(lines):
        if i in skip:
            continue
        for m in PROHIBITED_RE.finditer(line):
            findings.append((i + 1, f"prohibited term '{m.group(1)}'; use a neutral verb such as "
                                    "supports, enables, provides or implements"))
        for m in CITATION_RE.finditer(line):
            cited.add(m.group(1))
            if sources is not None and m.group(1) not in listed:
                findings.append((i + 1, f"citation [{m.group(1)}] has no line in Sources"))
    if not cited:
        findings.append((0, "no claim carries a citation; follow every number and claim with [n]"))
    for sid, line_no in listed.items():
        if sid not in cited:
            findings.append((line_no, f"source [{sid}] is cited nowhere in the report; cite it or remove it"))

    return sorted(findings)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="research-check",
        description="Check a research report against the fixed report form: the legend line, "
                    "the Sources lines with their scores and link status, the citations, the "
                    "Sources Discarded section and the prohibited terms. Checks form and "
                    "arithmetic only; it reads no web page.",
        epilog="Prints 'pass' and exits 0 when the report has the form. Otherwise prints one "
               "line per finding (line number, what is wrong, the correction) and exits 1. "
               "Exits 2 when the report cannot be read. Example: research-check report.md",
    )
    parser.add_argument("report", metavar="REPORT",
                        help="the report file, UTF-8 Markdown; '-' reads standard input")
    args = parser.parse_args(argv)

    try:
        if args.report == "-":
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(args.report, encoding="utf-8") as handle:
                text = handle.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"research-check: cannot read {args.report}: {exc}. "
              "Run: research-check <path of the report file>", file=sys.stderr)
        return 2

    findings = check(text)
    out = sys.stdout
    if hasattr(out, "reconfigure"):
        out.reconfigure(encoding="utf-8")
    if not findings:
        print("pass")
        return 0
    print(f"{len(findings)} finding(s) in {args.report}. Correct each and run again.")
    for line_no, message in findings:
        where = f"line {line_no}" if line_no else "report"
        print(f"{where}: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
