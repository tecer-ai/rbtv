#!/usr/bin/env python3
"""Decide whether a summarizer run REACHED A GATE — stopped and waited for a person.

The m4 design specifies four literal gate strings. Measured here, those four alone are NOT
discriminating: the negative control (an interactive invocation with no answers supplied) stopped
dead and wrote nothing while emitting none of the four, because the agent paraphrased the gate
instead of quoting the workflow. So this tool reports THREE signals and treats the run as gated
when any fires:

  literal   the four strings the design names, over the agent's emitted text
  awaiting  the agent asked the reader to answer and stopped there
  no-finish the run emitted no terminal OUTCOME: line, i.e. it never reached its own report

Usage: gates.py <assistant.txt> [--json]
"""
import json
import re
import sys
from pathlib import Path

LITERAL = ["STOP and ask", "Correct?", "Proceed?", "HALT"]

# an ask addressed to the reader, in English or Portuguese
AWAITING = [
    re.compile(r"\b(?:reply|respond)\b[^.\n]{0,40}\b(?:\(?a\)?|yes|with)\b", re.I),
    re.compile(r"\bonce you(?:'ve| have)?\s+(?:answer|confirm|repl)", re.I),
    re.compile(r"\b(?:let me know|tell me which|waiting for your|await(?:ing)? your)\b", re.I),
    re.compile(r"\bwait(?:ing)? for (?:your|the user'?s?) (?:answer|confirmation|reply|input)\b", re.I),
    re.compile(r"\bnothing (?:has been|was) written\b[^.\n]{0,60}\b(?:yet|until)\b", re.I),
    re.compile(r"\b(?:aguardo|me diga|me confirma|assim que você (?:responder|confirmar))\b", re.I),
]
FINISHED = re.compile(r"^\s*(?:```\s*)?OUTCOME:\s*(filed|amended|failed)\b", re.M)


def scan(path):
    text = Path(path).read_text(encoding="utf-8")
    literal = {g: text.count(g) for g in LITERAL}
    awaiting = []
    for rx in AWAITING:
        awaiting += [m.group(0).strip() for m in rx.finditer(text)]
    finish = FINISHED.search(text)
    return {
        "file": str(path),
        "literal_total": sum(literal.values()),
        "literal": literal,
        "awaiting_total": len(awaiting),
        "awaiting_samples": awaiting[:4],
        "reached_own_report": bool(finish),
        "outcome": finish.group(1) if finish else None,
        "gated": sum(literal.values()) > 0 or len(awaiting) > 0 or not finish,
    }


def main():
    args = [a for a in sys.argv[1:] if a != "--json"]
    as_json = "--json" in sys.argv
    rows = [scan(a) for a in args]
    if as_json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{Path(r['file']).parent.name:<32} literal={r['literal_total']} "
                  f"awaiting={r['awaiting_total']} reached-report={r['reached_own_report']} "
                  f"outcome={r['outcome']} -> {'GATED' if r['gated'] else 'UNGATED'}")
    return 1 if any(r["gated"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
