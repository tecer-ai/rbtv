# 20260825-c-one-last-progress-at-fact-reco — One last_progress_at fact + recovery config/checkpoint

kind: creation
component: engine
date: 2026-08-25
commit: eec3367f
deployed: no
pin: NONE
components: server,config

## Motivation
The daemon had no single work-product fact per seat. Liveness of WORK was inferred from the
admission fingerprint (which drifted whenever a timestamp or session id inside it changed) and
from transcript growth (which a frozen seat produces by re-reading its own inputs), so a
busy-looking frozen seat survived and a productive seat could be judged idle. The recovery
numbers were literals scattered across `reconcile.js`, `heart-store.js` and `ticker.js`, and
there was no operational contract for what a relaunched seat may resume from.

## Design
Four small modules in `ignite/supervisor/`, the home spec-component-map names for recovery
policy (recovery is not a second folder). `progress.js` holds spec-recovery section 1's table
as code — both columns, because the "does not" column is the half that catches the defect —
and is the ONLY writer of `last_progress_at`. That fact lives on the supervisor registry row
already persisted by the registry seat, reached through a fifth write moment `recordProgress`
that advances the stamp and touches nothing else; it never inserts a row, so a signal for an
unsupervised sitting answers null instead of fabricating a liveness claim. `kill-clock.js`
decides the no-progress kill off that fact alone and pauses on exactly three ruled lane
conditions. `recovery-config.js` is the one read api for the eight tweakable numbers, and
every clause of it is a refusal. `checkpoint.js` is the operational checkpoint contract.
Rejected: a cache in the loader (the boot load and the config-change re-arm are the same
call, and an invalidation path is how a re-arm silently keeps the old numbers), and seeding
from inside the loader (a loader that seeds on a miss can never report a missing file, which
is the contract).

## How it works
A signal is `{goal, seat, kind, signal}`; `recordSignal` advances the fact iff the kind's
advances column carries that signal, and writes nothing otherwise. An unnamed or unknown kind
resolves to file-writing; `orchestrator` is an alias of `planning`, not a fifth kind. The kill
clock's three pauses read lane facts `verified_open_ask`, `provider_backoff_until` (ISO-8601,
produced later by the provider-lanes work — the predicate simply never fires until then) and
`disarmed` + `awaiting_event` (spec-state-store's flag, read never written). `killDecision`
throws `RecoveryConfigError` without a loaded config, which is what makes "refuse to apply
recovery clocks" true by construction rather than by discipline. `loadRecoveryConfig` reads
`{workspace}/.rbtv/config/ignite/recovery.json`: eight keys required, extra keys refused,
integers only, 0 or negative refused, missing/unreadable/invalid = configuration-error and no
fallback. `seedRecoveryConfig` copies `recovery.defaults.json` to the instance path iff absent
(the real guard is the `wx` open flag, not the existence check) and an upgrade never
overwrites. `checkpoint.js` writes `progress-note.md` (all three of done-so-far / next-step /
open-questions or the write is refused) and appends
`ISO-8601<TAB>kind<TAB>target<TAB>idempotency-key` to `side-effect-journal.tsv` BEFORE each
external act; `isJournaled` is the relaunch's skip, and `relaunchPrompt` composes brief + note
+ the spec's verbatim continue-instruction. Non-node callers reach seeding, the read api and
the collector through the existing `cli.js --op` door.

## Consequences
`registry.js` rows carry a new `last_progress_at` field, stamped at spawn so a fresh sitting is
never indistinguishable from one that has never progressed; `recordCheckIn` now preserves an
existing stamp rather than resetting it, because check-in is not a listed signal. No number in
the new modules is a knob literal — grep of 30/3/2/5/15/4 finds only the seed JSON and the
tests. The recognition lists, routing table, backoff production, attempt counters and relaunch
budget are deliberately NOT here: sibling seats own them and consume this loader read-only.

## Verification
`node progress.selftest.js` (every kind, both columns, plus cross-kind leakage and the
unnamed-kind fallback), `node kill-clock.selftest.js` (each of the three pauses, and seven
states that look like pauses and are not), `node recovery-config.selftest.js` (valid file,
absent, unreadable, malformed, each missing key, extra key, non-integer, zero, negative, and
both seeding directions), `node checkpoint.selftest.js` (note fields, journal shape, skip on
key, verbatim prompt) — each prints ALL PASS and exits 0. Siblings re-run green:
`registry.selftest.js`, `doors.selftest.js`, `death-stamp.selftest.js`, and
`probe-suite.js --only probe-verdict-vocabulary` (GREEN). Not deployed: branch
`ignite/core-redesign` in the redesign worktree, pre-cutover.

## ATTENTION
- The "does not" column is binding, not commentary. Advancing `last_progress_at` on transcript
  growth, an unsent draft, inbound mail or sub-agent chatter re-opens the exact defect this
  module closes: a frozen seat that looks busy forever.
- chat-only does NOT list `progress-note`. A note write advances the fact for file-writing,
  planning and judge only — the tempting reading ("a note is progress everywhere") hands a
  chat-only seat a way to look busy without sending anything.
- Never add a fourth pause to the kill clock. The list is closed by ruling, and the accepted
  consequence is a busy-looking runaway that stays unkillable; a fourth pause widens that hole.
- Never give the loader a fallback number, and never call `seedRecoveryConfig` from it. A
  workspace with no instance file is a bootstrap bug, and the daemon must refuse the clocks.
- `recordProgress` never inserts a registry row. A signal for a sitting with no row answers
  null; minting a row would hand the registry a liveness claim it never observed a spawn for.
- the does-not column is binding; advancing on transcript growth re-opens the defect
