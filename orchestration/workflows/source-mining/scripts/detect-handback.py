#!/usr/bin/env python3
"""Detect a source-mining headless hand-back (task 7.90) and report it.

The DETECT half of the EMIT/DETECT split: step-05-synthesize.md's § Headless Hand-Back Procedure
(the EMIT side, a workflow instruction) prints one documented marker line as its final output:

    ##RBTV-SOURCE-MINING-HANDBACK## <absolute path to handback.json>

HISTORY (`r-seats-only-architecture`, 2026-08-06): the `rbtv-subagent` dispatcher and its flat
`.rbtv/sessions/<exec-id>/` workdirs are RETIRED; a headless worker's `workdir` is now whatever
launch dir the orchestration skill's CLI-worker lane gives it — this script only needs that dir's
`stdout.log`. The retired dispatcher's supervisor persisted the session's full stdout to `<workdir>/stdout.log`
(stream-json events, one per line; the final text is the `type":"result"` event's `result` field,
also echoed inside the last `type":"assistant"` message). This script bridges the gap: given only
`workdir`, it finds the marker in the persisted log and follows it to the hand-back record.

Usage:
    python3 detect-handback.py --workdir <path>

Exit codes:
  0  hand-back found; JSON summary on stdout (record contents included)
  1  no hand-back marker in the log (run is mid-flight, halted interactively, or finished normally)
  2  marker found but its record could not be read (path missing / unreadable / bad JSON) -- a
     real defect, not "no hand-back"
"""

import argparse
import json
import re
import sys
from pathlib import Path

MARKER = "##RBTV-SOURCE-MINING-HANDBACK##"
# The marker is read out of a persisted stream-json log, where it sits inside a JSON string with
# no whitespace before the closing quote (`...handback.json"}`). A plain \S+ capture is GREEDY and
# swallows that trailing `"}` into the path, which then fails to exist -- a false negative on every
# real dispatch. No legitimate filesystem path contains a literal double-quote, so excluding it (in
# addition to whitespace) stops the match exactly at the JSON string boundary.
MARKER_RE = re.compile(re.escape(MARKER) + r'\s+([^\s"]+)')


def parse_args():
    p = argparse.ArgumentParser(description="Detect a source-mining headless hand-back.")
    p.add_argument("--workdir", required=True, help="the headless worker's launch dir (holds stdout.log)")
    return p.parse_args()


def find_marker_text(raw):
    """Return the text to search for the marker in, preferring the harness's own final answer.

    MEASURED DEFECT (fixed here), caught only against a real dispatch, never against a synthetic
    fixture: step-05-synthesize.md's own instructions quote the marker format as a literal example
    ("print exactly: ##RBTV-SOURCE-MINING-HANDBACK## <path>"). When the agent reads that file, the
    tool-result echo containing that example lands in stdout.log BEFORE the agent's real, later
    emission -- so a naive "first match in the whole log" grab returns the instructions' own
    example text, not the real hand-back path. The stream-json format gives an unambiguous fix: the
    agent's actual final answer is the LAST `type":"result"` event's `result` field (mirrored in
    the last `type":"assistant"` message) -- nothing legitimately follows it. Restricting the
    search to that field means an earlier echo of the instructions can never be mistaken for it.
    """
    last_result = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            last_result = event["result"]
    if last_result is not None:
        return last_result
    # Fallback (non-stream-json log, or no parseable result event): take the LAST match in the
    # raw text rather than the first, for the same reason -- an earlier echo of the instructions
    # must never outrank the agent's actual final output.
    return raw


def main():
    args = parse_args()
    workdir = Path(args.workdir)
    stdout_log = workdir / "stdout.log"

    if not stdout_log.exists():
        print(json.dumps({"handback": False, "reason": f"no stdout.log at {stdout_log}"}))
        return 1

    raw = stdout_log.read_text(encoding="utf-8", errors="replace")
    searchable = find_marker_text(raw)
    matches = list(MARKER_RE.finditer(searchable))
    if not matches:
        print(json.dumps({"handback": False, "reason": "no marker line in stdout.log", "log": str(stdout_log)}))
        return 1
    m = matches[-1]

    record_path = Path(m.group(1))
    if not record_path.is_absolute():
        print(json.dumps({"handback": True, "record_error": f"marker path is not absolute: {record_path}"}))
        return 2
    if not record_path.exists():
        print(json.dumps({"handback": True, "record_error": f"record file does not exist: {record_path}"}))
        return 2

    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"handback": True, "record_error": f"could not read/parse {record_path}: {exc}"}))
        return 2

    print(json.dumps({"handback": True, "record_path": str(record_path), "record": record}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
