# 20260831-c-digest-asks-sort-blocking-firs — digest asks sort blocking-first (d-ask15)

kind: creation
component: chat
date: 2026-08-31
commit: 6c97194f
deployed: no
pin: ignite/chat/probes/probe-chat-glance.js

## Motivation
Owner ruling `d-ask15-blocking-asks-first`: the 2-hourly system digest's `❓ open asks` list mixed
asks a seat is genuinely WAITING on (blocking) with asks a seat already answered with its own
declared default and disclosed (informational) — in arrival order, indistinguishable, 9 of 12
lines informational in the 2026-08-28 20:00 digest. Owner picked option (a): sort blocking to the
top of the ONE list, no new sections.

## Design
Checked the `open_asks` schema (`state-store/tables.sql`) and `ask-record.js#listOpenAsks`'s row
shape before writing anything: NO structural field distinguishes blocking from informational. The
only column in that space, `label`, is `work-content|recovery` (D-7-ruling) — orthogonal.
`bus-ferry.js` computes the real arm (`block-and-queue`/`default-and-disclose`/`park`) per
delivery pass via `fallbackArm`, but never writes it back to `open_asks`; it survives only baked
into the posted message's header text via `FALLBACK_MARK`, which becomes the ask's `one_liner`
(first line of its corpus). Rejected inventing a producer-side column (out of this seat's custody,
`system-digest.js` only) in favour of keying on that rendered text mark, explicitly as the
WEAKEST-available fallback, not a primary key pretending to be structural.

## How it works
`system-digest.js#sortAsksBlockingFirst` does a stable two-pass partition (not `Array#sort`) so
arrival order is preserved by construction within each group — asks with no
`FALLBACK_MARK['default-and-disclose']` substring in `one_liner` (imported from `bus-ferry.js`
rather than re-typed) lead; asks carrying it follow. `renderDigest` calls it immediately before
the `❓ open asks` render loop only — `snapshotOf` (the change-gate hash) is untouched, since it
already sorts asks by id independently for hashing, so display order never affects change
detection.

## Consequences
Nothing deleted or replaced. `digest-row-shape`'s row shape (goal-lead, id-tail, inline
`evidence_pointer`) is unchanged — the sort only reorders which row renders first. `Open
conditions` was evaluated for the same treatment (`d-digest-ui` 5b) and deliberately NOT changed:
alarm/condition records (`observation/emitter.js`) carry no `arm`/label-equivalent field and no
analogous "proceeded on a default" text mark — conditions are alarms, not asks a seat can carry on
past.

## Verification
`node ignite/chat/probes/probe-chat-glance.js` — 33 checks (30 prior + 3 new), EXIT=0. New checks:
an interleaved fixture (informational, blocking, blocking, informational) renders blocking-first
with arrival order kept in each group; a stability fixture (ids that would swap under any
id-keyed comparator) proves arrival order, not id, decides sub-order; a link-carrying row proves
`digest-row-shape` survives the sort untouched. `probe-chat-glance-wiring.js` — 27 checks, EXIT=0,
unchanged (wiring only, no sort-order assertions). Not deployed — committed to
`ignite/core-daemon` only, per this plan's no-mid-plan-deploy rule.

## ATTENTION
1. The sort key is TEXT, not a column — a future rewording of `bus-ferry.js`'s `FALLBACK_MARK`
   constant (imported here, not re-typed) silently breaks the sort with no test failure unless the
   marker string changes; grep both files together before editing either.
2. A header line long enough to push the mark past `oneLinerOf`'s 120-char truncation loses the
   marker and that ask silently reads as blocking (fails safe toward the more-visible bucket, but
   worth knowing if a goal/seat-name combination ever gets that long).
3. `snapshotOf` still sorts asks by id for the change-gate hash — display order and hash order are
   two independent sorts on purpose; do not "simplify" by reusing one for the other.
- text-marker sort key breaks silently if FALLBACK_MARK's wording changes without updating both files
