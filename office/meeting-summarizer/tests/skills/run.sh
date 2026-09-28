#!/usr/bin/env bash
# run.sh <run-name> <prompt-name>
# Gives the run its own copy of fixtures/ as its working directory, so every writeback the run
# performs is observable against that copy's own before-state and the owner's live vault is never
# touched. Then invokes probe.sh with standard input closed.
set -eu
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/runs_root.sh"
root="${RUNS_ROOT:-$(_default_runs_root "$here")}"
name="$1"; prompt="$2"
rm -rf "$root/$name"
mkdir -p "$root/$name"
cp -r "$here/fixtures" "$root/$name/ws"
cp -r "$root/$name/ws" "$root/$name/ws-before"   # the before-state, for the writeback diffs
exec "$here/probe.sh" "$name" "$root/$name/ws" "$here/prompts/$prompt.txt"
