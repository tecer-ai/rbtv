# 20260824-c-delete-credential-pierce-role — Delete credential-pierce role (T2-R11)

kind: change
component: server
date: 2026-08-24
commit: 2c5e20e7
deployed: no
pin: server/spawn/probes/probe-exposed-cli-secrets.js,server/spawn/probes/probe-master-cage.js,server/spawn/probes/probe-private-scope.js

## Motivation
Owner ruling [T2-R11] (redesign D19, `1-projects/build-ignite/redesign/DESIGN-BASELINE.md` v2):
credentials are env-injected, never caged — the private-scope compiler must never re-open
`credentials/` / `*.env` / `*.key` / `*token*` for any caller/role. `composePrivateScope`'s TIER 2b
carried the D4 (2026-08-18, `bddca338`) `exposedCliCode` grant-class pierce: an opening tagged
`grantClass: 'exposedCliCode'` (only ever produced for an `exposed-clis:`-declared CLI's own code
directory) that CONTAINED an enumerated deny entry — in every observed and tested use, a declared
CLI's own `config.yaml` / `credentials/` — skipped the mask and re-opened it whole for the seat that
declared the tool. That mechanism is exactly, and only, the "credential-pierce role" the ruling names.

## Design
Deleted the D4 branch in TIER 2b of `composePrivateScope` (`ignite/server/spawn/private-scope.js`)
rather than the file's other pierce mechanism (TIER 3, the generic "a grant that NAMES a path inside
a private entry" authored exception whose motivating and only cited case is the therapy-summarizer's
health path, not a credential). Kept TIER 3 intact: it already refuses the two HARDCODES (`.env`,
`private.json`) unconditionally and serves an unrelated need (an owner-authored per-seat exception to
an arbitrary private entry) the ruling does not touch. Kept the mask entirely — every private entry
(hardcoded, enumerated `deny`, or pattern-floor match) now masks unconditionally regardless of any
`exposedCliCode` tag or declaration. Rejected: pattern-matching the entry's basename against
`credentials/`/`*.env`/`*.key`/`*token*` and only refusing those (would leave a real gap — the
stools fixture's `config.yaml` deny entry, which the D4 mechanism actually pierced in every probe,
does not itself match any of those four patterns by filename; the whole grant-class mechanism was
credential-only in every tested/documented use, so deleting it wholesale is both simpler and more
complete than a pattern filter).

## How it works
`composePrivateScope`'s TIER 2b mask loop no longer special-cases `seeded.has(e) &&
!scope.hardcoded.has(e)` against a `spec` opening tagged `grantClass === 'exposedCliCode'`; every
masked entry is `--ro-bind`-covered with an empty (or TIER-3-pierce-skeletal) source, full stop. The
`grantClass: 'exposedCliCode'` tag itself is untouched in `spawn.js#resolveExposedCliGrants` — it
still serves its OTHER, unrelated job (per `cage-compose.md` Q1): a read-only exposed-CLI code tree
appended last in `SeatBinds`' TEMPLATE so it shadows any writable `rw-paths` opening under the same
path. `needsDeclaration`/the D56/D74 undeclared-tool PATH shim in the same file is also untouched —
it still exists to give a NAMED refusal instead of a raw `PermissionError` traceback for an
undeclared tool reaching a private-shaped directory, but now (declared or not) the mask never lifts,
so declaring a tool changes only which error a seat gets, never whether the CLI's own secrets are
readable.

## Consequences
A previously-working path is now closed by design: a seat with `exposed-clis: stools` (or any
similarly credential-bearing declared CLI) can no longer read that CLI's own `config.yaml` /
`credentials/` through the cage — it hits the same masked-empty read every undeclared seat already
got. Building the replacement (env-var credential injection) is explicitly out of scope for this
change per the ruling ("Do not build injection, impl-envelope, out of scope"); until that lands,
any declared CLI whose own process-time config-load path needs its `config.yaml`/`credentials/` on
disk (stools' `load_config` shape, per `20260821-i-stools-undeclared-tool-refusal.md`) is unable to
read it in-cage. Updated stale doc comments in the same file that described the D4 mechanism as
live (the TIER-3 header's "EXCEPTION (D4…)" clause, and the `needsDeclaration` header's D56
narrative). Left `spawn.js` (lines ~939, ~1328, ~1331), `engine/cage-admission.js` (lines ~284,
~370) comments referencing "the D4 pierce" as-is — those are prose-only references in files outside
this component's explicit edit scope for this task; they are now slightly stale (describing a
mechanism that no longer exists) but do not affect behavior, since neither file's actual logic
depends on the pierce firing.

## Verification
`node --check` clean on all three edited files. `git grep -n -iE 'pierce' -- ignite/server` after the
edit shows only TIER-3 (generic named-grant pierce) mentions — no `exposedCliCode`/D4 credential
pierce remains. Ran all three touched/adjacent probes directly (`node
server/spawn/probes/<name>.js`, output in the sibling `.out` file): `probe-exposed-cli-secrets.js`
(rewrote leg 1 to assert the exposedCliCode-tagged opening now leaves `config.yaml`/`credentials/`
masked with `pierced.length === 0`; rewrote leg 2 similarly for the untagged case; kept leg 3
(`.git` floor still masks) and leg 4 (renumbered from 5, `grantClass` tagging still threaded) and
legs 6–12 (`needsDeclaration`/PATH-shim, unaffected) as-is; deleted the old leg 4 that asserted the
spawn disclosure named two pierced entries) — ALL LEGS PASS. `probe-master-cage.js` (deleted legs
S1/S2/S2-control and their dedicated stools-shaped fixture (`toolDir`, `masterStoolsDir`,
`undeclaredMasterDir`); kept M1–M6/W1/W2/C1 unchanged) — ALL PASS, including M6 (master cage still
read-masks `.env`/`private.json`). `probe-private-scope.js` (untouched, run as a regression check
that TIER 3's health-path named-grant pierce still fires) — ALL LEGS PASS, confirming the surgical
scope of the deletion.

## ATTENTION
- The `exposedCliCode` grant-class TAG (`spawn.js#resolveExposedCliGrants`) is still emitted and
  still load-bearing for the unrelated read-only-shadows-writable-grant ordering effect
  (`cage-compose.md` Q1 point 1). Do not delete that tagging as "dead code from the pierce removal"
  — it is not dead, it serves a different mechanism entirely.
- `needsDeclaration`/the PATH shim (D56/D74) still exist and still matter: without them, ANY seat
  (declared or not) reaching a private-shaped tool directory by PATH now hits the same raw
  `PermissionError` a masked `config.yaml` throws — the shim is what turns that into a named refusal
  for the undeclared case. It does not, and no longer can, grant reach.
- `spawn.js` (~939, ~1328, ~1331) and `engine/cage-admission.js` (~284, ~370) still carry prose
  referencing "the D4 pierce" as a live mechanism that fixes masked-but-declared secrets reach — that
  prose is now stale. Left un-updated (out of this task's explicit file scope); a future edit to
  either file's neighboring logic should not infer the pierce still exists from those comments.
- Credential env-injection (the actual replacement for what this mechanism used to provide) is
  explicitly NOT built here — a declared CLI needing its own on-disk secrets to run (e.g. stools'
  `load_config`) is broken in-cage until that lands. This is the ruling's accepted, deliberate gap,
  not a defect of this change.
