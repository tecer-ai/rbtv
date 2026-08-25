#!/usr/bin/env python3
"""supervise — the supervision CLI: the daemon's and a leader's remedial surface over a run.

The owner split the single `coordinate` front door in two by AUDIENCE (2026-08-25): "one for the
daemon or for leaders (if smth broken), the other for all agents working on ignite (checkin,
checkout, message, etc)". This is the first of those. It accepts the launch composer
(`launch`, `session-open`, `descriptors`, `boot-prompt`), the readiness arithmetic (`ready-seats`,
and the engine-only `renewal-state` / `surface-refusal`), the mechanical remedies (`close-seat`,
`reap`, `kill-pane`, `relaunch-pane`, `terminate-pid`, `approve`, and the daemon-forked
`lifecycle-exec`) and the death stamp (`attest-exit`, `route-fail`) — the concerns
`spec-component-map` §3 homes in this component.

Seat-facing coordination — check in, check out, message, read, records, groups — is the OTHER
door, `coordinate`. No verb sits on both, and no verb's behaviour, flags or output changed when
they were separated: this file selects a door, and the parser and every command body are the
kit's, unchanged.

A THIN FRONT DOOR AND NOTHING ELSE. The kit is ONE namespace, always named `coord`; a second copy
of it under another name would leave the CLI reading one and every supervision module the other.
So this door imports the kit rather than re-executing it, and dispatches into the same `main()`
`coordinate` uses, telling it which door it is.

Run `supervise -h` for the grouped command list, `supervise <command> -h` for one command's
arguments, one example, and the step that usually follows.
"""
import sys
from pathlib import Path

# The kit lives in the sibling component `coord/`. Resolve the symlink first: this file is reached
# through a `~/.local/bin` symlink like `coordinate` is, and a bare `Path(__file__).parent` would
# point there instead of at the repo.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "coord"))
import coord  # noqa: E402 — the path insert above is what makes this importable

if __name__ == "__main__":
    sys.exit(coord.main(coord.SUPERVISION_DOOR))
