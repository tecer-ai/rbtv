# 20260831-i-granted-cli-shim-minted-with-n — granted CLI shim minted with no +x died Permission denied

kind: issue
component: supervisor
date: 2026-08-31
commit: f55dc3a3
deployed: no
pin: ignite/supervisor/spawn/probes/probe-exposed-cli-exec-bit.js
register-id: G-plan-verifier-0830-1850

## Observed
A granted CLI whose target `.py` lacks the execute bit died `Permission denied` on the granted bare
name. Measured 2026-08-31 on today's tree: `capability_cards.py` and `gtools.py` and
`approve_package.py` are all `-rw-rw-r--`. Sighted repeatedly (task 161 seed evidence):
`G-plan-drafter-0828-2120` (`capability-cards`, `plan-drafter` on `meet-transcript-summarizer-planning`,
`$ capability-cards --help` -> `Permission denied`, `which capability-cards` -> exit 1 no output) and
`G-plan-verifier-0830-1850` (`approve-package`, approval-critical — the seat's only route to its own
product). Both entries' own suggested fix: "emit a `#!`-wrapper shim instead of a bare symlink for a
non-executable target."

## Mechanism
`resolveExposedCliGrants` (`ignite/supervisor/spawn/spawn.js`) validated that a granted CLI's target
existed (`fs.existsSync`) but never checked its execute bit. `composeCageFor` then emitted a bare
bwrap `--symlink <target> <rbtvBin>/<name>` for every grant. bwrap's `--symlink` only creates a
symlink NODE — exec resolution still enforces the OS execute bit on whatever the symlink resolves
to, which is the target's REAL mode (preserved through the ro-bind of its code tree). A `-rw-rw-r--`
target therefore refused `Permission denied` regardless of the grant being correctly declared and
correctly minted.

## Attempts
First attempt held — checked commit `98186c76` (`20260831-i-caged-planning-seat-could-not`), which
fixed a DIFFERENT half of the same grant surface (binding `cli-write-roots` into the cage) and does
not touch `resolveExposedCliGrants` or the symlink mint at all. No prior attempt at THIS defect
found in `ignite/work-on-ignite/memory/supervisor/`.

## Fix
`resolveExposedCliGrants` now `fs.accessSync(target, X_OK)`-checks the target; when it lacks +x, a
new `execWrapperFor` reads the target's own shebang line and mints a `#!/bin/sh\nexec <interpreter>
"<target>" "$@"\n` wrapper at a content-keyed path in host tmp (idempotent across spawns, same shape
as the existing `refusalShimSource`), chmod 0o755. The grant's `exposedCliEntry` (the `--symlink`
destination) becomes the wrapper instead of the raw target; `exposedCliCode` (the ro-bound code-tree
directory) stays the target's real dirname unchanged, since the wrapper `exec`s into the target's
real path and its siblings must resolve there. `composeCageFor` additionally `--ro-bind`s the
wrapper file itself (it lives outside the code-tree ro-bind). Rejected: chmod'ing the target file —
it lives in the shared repo tree and a per-seat spawn must not mutate a file every other seat and
session reads; the fix belongs at the mint, not on the shared source.

## Consequences
No deletions. A target that IS already executable is completely unaffected (no wrapper, same bare
symlink as before) — verified as an explicit control leg.

## Verification
New probe `ignite/supervisor/spawn/probes/probe-exposed-cli-exec-bit.js` drives the REAL
`resolveExposedCliGrants` against a 644 shebang fixture (same shape as the measured targets): grant
still resolves (not dropped), carries an `execWrapper`, the wrapper is `755` on disk, and invoking
`exposedCliEntry` (as the granted bare-name symlink target would) actually runs and prints, no
`Permission denied`. Control leg: an already-`+x` fixture gets `execWrapper: null` and
`exposedCliEntry` equal to the raw target. Revert-in-place control: stashing just this file's diff
reproduced the pre-fix `TypeError: resolveExposedCliGrants is not a function` (the export itself is
part of the fix) — restoring the diff turned the suite green again.
`node ignite/deploy/probe-suite.js --only probe-exposed-cli-exec-bit` — PASS.
`node ignite/deploy/probe-suite.js --only probe-seat-exposed-clis` (pre-existing sibling probe,
regression check) — PASS. Not deployed — the sandbox mint (`~/.rbtv-bin`) is daemon JS, inert until
`rbtv ignite daemon deploy`.

## ATTENTION
- The wrapper routes through the target's OWN shebang line, not a hardcoded `python3` — a target
  with no shebang (or a binary with no shebang) gets no wrapper and is left exactly as before
  (still refuses `Permission denied`, now ALSO with a `log('warn', …)` naming which grant and why).
- `execWrapper` is keyed by an md5 of the absolute target path, so two different targets never
  collide and repeated spawns of the same seat reuse the same wrapper file rather than growing tmp.
- Distinct from "CLI not registered" (missing from PATH/`~/.rbtv-bin` entirely, a different class,
  intentionally not folded in here) and from task 158 (capability-cards' wrong `--root` catalog,
  fixed separately in `meta-planning`).
