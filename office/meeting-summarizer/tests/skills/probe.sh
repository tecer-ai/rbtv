#!/usr/bin/env bash
# Run one summarizer-skill invocation UNATTENDED and capture its run transcript.
#
#   probe.sh <run-name> <cwd> <prompt-file>
#
# Standard input is closed to EOF (< /dev/null): a path that only works because something was
# there to read is not unattended. Writes, under $RUNS_ROOT/<run-name>/:
#   stream.jsonl   every event the run emitted
#   assistant.txt  every assistant-emitted text block, in order — THE run transcript for the
#                  gate-string grep, because a gate is "reached" only when the agent EMITS it
#                  (the gate strings also appear in the skill file the agent READS, which is why
#                  the grep is over what the run said, not over what it looked at)
#   exit           the process exit code
set -u
name="$1"; cwd="$2"; prompt_file="$3"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/runs_root.sh"
out="${RUNS_ROOT:-$(_default_runs_root "$here")}/$name"
mkdir -p "$out"

start=$(date -u +%s)
( cd "$cwd" && timeout "${PROBE_TIMEOUT:-900}" claude -p "$(cat "$prompt_file")" \
    --output-format stream-json --verbose --permission-mode bypassPermissions \
    < /dev/null ) > "$out/stream.jsonl" 2> "$out/stderr.txt"
code=$?
end=$(date -u +%s)
echo "$code" > "$out/exit"
echo "$((end - start))" > "$out/seconds"

python3 - "$out/stream.jsonl" "$out/assistant.txt" <<'PY'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
parts = []
for line in open(src, encoding="utf-8"):
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        continue
    if ev.get("type") == "assistant":
        for block in ev.get("message", {}).get("content", []):
            if block.get("type") == "text" and block.get("text"):
                parts.append(block["text"])
    elif ev.get("type") == "result" and ev.get("result"):
        parts.append(ev["result"])
open(dst, "w", encoding="utf-8").write("\n".join(parts))
PY

echo "run=$name exit=$code seconds=$(cat "$out/seconds")"
exit "$code"
