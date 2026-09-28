#!/usr/bin/env bash
# amend.sh <source-run> <amend-run-name> <prompt-name>
# Re-enters an ALREADY COMPLETED run's working directory, so amendment mode is applied to a
# summary that was genuinely filed earlier rather than to a fresh fixture.
set -eu
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/runs_root.sh"
root="${RUNS_ROOT:-$(_default_runs_root "$here")}"
src="$1"; name="$2"; prompt="$3"
rm -rf "$root/$name"
mkdir -p "$root/$name"
cp -r "$root/$src/ws" "$root/$name/ws"
cp -r "$root/$name/ws" "$root/$name/ws-before"
exec "$here/probe.sh" "$name" "$root/$name/ws" "$here/prompts/$prompt.txt"
