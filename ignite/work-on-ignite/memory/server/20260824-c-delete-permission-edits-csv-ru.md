# 20260824-c-delete-permission-edits-csv-ru — Delete permission-edits.csv runtime surface

kind: change
component: server
date: 2026-08-24
commit: de4deb59
deployed: no
pin: NONE
components: engine,team-kit,meta-leader

## Motivation
Owner rulings [T2-R12, T1-R9] (redesign DESIGN-BASELINE.md v2): the grant store is deleted —
owner auth is an answer to a live ask, not a standing widen a leader files and a cage reads back.
`coordination/permission-edits.csv` was its last runtime surface: a leader-writable audit CSV,
read additively by the spawner as a second workspace rw-grant source beside `rw-paths:`
frontmatter, and carved read-only for every seat but the leader. This entry follows
`team-kit/20260824-c-delete-widen-cage-verb.md` (the verb that WROTE the file) — this creation
deletes every READER and the template slot, so the file's runtime role is gone end to end.

## Design
Deletion, not a replacement. `resolvePermissionEditGrants` (seat-grants.js, read additively
beside `rw-paths` at every launch) and `resolvePermissionEditsRoGrant` (spawn.js, the RO carve for
non-leader seats) are both removed rather than left dead — a dead grant resolver that still runs
is a second place a future reader could mistake for a live authority. `PERMISSION_EDITOR_SEAT` is
removed from both the JS side (spawn.js) and its Python mirror (cagespec.py) together, since
probe-permission-edits.js existed specifically to assert the two spellings agreed — with the
symbol gone from both, that whole probe's job is gone, so the probe file is deleted rather than
left asserting nothing.

## How it works
`cagespec.py#compose` no longer special-cases a `{grant:permissionEditsRo}` template field — the
`PERMISSION_EDITS_GRANT`/`PERMISSION_EDITS_REL`/`PERMISSION_EDITOR_SEAT` constants and the whole
branch that read them are gone, so an unknown-field fails closed exactly like any other retired
grant. `config/spawn-profiles.yaml`'s `cage.SeatBinds` no longer carries the
`ro-bind-try:{grant:permissionEditsRo}` line. `engine/cage-admission.js#admitDeclaredOutputs` and
`#admitLaneReach` now compose workspace grants from `resolveRwPathGrants` alone (previously
`[...resolveRwPathGrants(...), ...resolvePermissionEditGrants(...)]`) — refusal prose updated to
name only the one remaining grant class. `spawn.js#composeCageFor` drops both
`resolvePermissionEditsRoGrant(seatPath)` and `resolvePermissionEditGrants(seatPath, log)` from its
grant-list spread.

## Consequences
Deleted whole: `ignite/server/spawn/probes/probe-permission-edits.js` (its only job was asserting
JS/Python agreement on a now-gone symbol). Trimmed dead legs (not whole files) from
`probe-cage-workspace-grammar.js` (arm 2, admitting on a `permission-edits.csv` row) and
`probe-seed-gates.js` (arm 3a/3b's row-present/row-removed pair, collapsed into one no-grant arm).
`probe-master-cage.js` leg M3 no longer names the deleted file (renamed its fixture write target to
`coordination-record.csv` — the leg was always just proving master-cage RW-everywhere on an
ordinary coordination-dir file, D49, never exercising the deleted grant machinery; the file name
was incidental and now misleading, so this entry renamed it, not the leg's assertion).
`cagespec.py`'s inline selftest count dropped from 24 to 21 asserts (the 4 PE-specific asserts
removed, 1 added asserting the retired field now fails closed like any unknown field). Docs updated
in the same change: `ignite/CLAUDE.md`, `spawn-profiles.yaml` comments, `materialize-seats.py`'s
seat-briefing prose (`_cage_write_surface` docstring + `_WRITE_SURFACE_BLOCK` + one more inline
block), and `meta/leader/prompts/leader.md`'s FIX-AND-RELAUNCH disposition (no longer names
`widen-cage`/`permission-edits.csv`; a narrow-cage blocker is now disposition 4, ESCALATE — no
runtime repair exists for it any more).

## Verification
`python3 -B ignite/team-kit/cagespec.py` → `cagespec: 21 asserts hold`. `python3 -B
ignite/team-kit/probes/probe-cagespec-mirror.py` → PASS, 5/5 arms. `node
ignite/engine/probes/probe-cage-workspace-grammar.js` → PASS, all legs. `node
ignite/engine/probes/probe-seed-gates.js` → PASS, all legs (incl. arm 7: "NO grant file was
created by either pass — the stores are deleted (D12)"). `node
ignite/server/spawn/probes/probe-register-door.js` → exit 0. `node
ignite/server/spawn/probes/probe-master-cage.js` → exit 0 (M3 confirmed still passing after the
rename). `py_compile` clean on `coord.py`, `cagespec.py`, `materialize-seats.py`; `node --check`
clean on every touched `.js`. Grep floor after commit: `permission-edits.csv`,
`resolvePermissionEditGrants`, `resolvePermissionEditsRoGrant`, `PERMISSION_EDITOR_SEAT` have zero
live-code hits (only past-tense history comments and this memory tree). Committed
`de4deb59` (worktree `5-workbench/rbtv-redesign`, branch `ignite/core-redesign`) — not yet deployed
to the live daemon (`3-resources/tools/rbtv/`) at filing time.

## ATTENTION
1. **`probe-master-cage.js` M3 is now generic, not special** — it writes to a plain
   `coordination-record.csv` fixture file with no runtime meaning; do not read its presence as
   evidence any permission-edit mechanism still exists. It proves D49 (master cage is
   truly-everything RW), nothing more.
2. **The cage envelope check itself (ruling [T2-R10]) is untouched** — this entry removed one
   grant SOURCE (`permission-edits.csv` rows) that fed the envelope gate, not the gate. `rw-paths:`
   frontmatter is still a live, surviving grant lane through the identical resolver
   (`resolveRwPathGrants`) and identical refusal predicate (`rwPathRefusal`) in `seat-grants.js`.
3. **`stale` comments may remain outside this change's file list** — a concurrent peer agent
   working `private-scope.js` (commit `2c5e20e7`, unrelated ruling [T2-R11]) flagged but did not
   fix stale "D4 pierce is live" comments in `spawn.js` (~939, 1328, 1331) and
   `cage-admission.js` (~284, 370); unrelated to this entry's subject but adjacent in the same
   files, noted here so a future memory reader in this area isn't surprised by them.
4. **This entry's writer (`widen-cage`) is a separate, prior deletion** — see
   `team-kit/20260824-c-delete-widen-cage-verb.md` for the CLI verb and `is_permission_editor`
   deletion. This entry is the reader/template side; together they retire the mechanism end to end.
- cage envelope check itself untouched — one grant source removed, not the gate
- rw-paths frontmatter is the surviving grant lane, unchanged
