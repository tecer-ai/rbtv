# 20260902-i-digest-showed-only-one-lane-of — digest showed only one lane of a multi-lane stuck ask

kind: issue
component: supervisor
date: 2026-09-02
commit: a118929decc72d374290eef9aff0a1164f7beafc
deployed: yes
pin: ignite/internal-api/probes/probe-inspect-asks.js (section G)
components: chat

## Observed
`exhaustion.js#listOpenGroupedAsks` — the read path the owner-facing system digest and `inspect asks`
both consume — collapsed a signature-grouped recovery ask covering N stuck lanes into ONE row: the
first lane's `goal`/`seat`, and a one-liner reading `<first lane's refusal text> (+N more lanes)`. A
live ask (`recovery-8f31b609a83b`) spanning three goals rendered as one row naming only
`ignite-engine-planning`, with the other two goals invisible anywhere in the digest.

## Mechanism
`listOpenGroupedAsks` read `record.lanes[0]` only when building each row — `goal`, `seat`, and the
one-liner (via the old `oneLinerOfRecord`) all came from the first lane in the array, with the count of
remaining lanes folded into a suffix string on that one row. The record on disk always held all N
lanes; the read path simply never emitted more than one row per record.

## Attempts
First attempt held — checked: no prior fix to this function exists; the collapsing was the original
design (`goal`/`seat` documented in-code as "the FIRST lane's — the same lane `recordGroupedAsk`
binds the store row to").

## Fix
Per owner ruling `d-digest-ui` 3a ("N stuck lanes are N rows naming N goals"), `listOpenGroupedAsks`
now iterates every lane in `record.lanes` (falling back to a single empty-lane placeholder `[{}]` when
the array is empty, preserving one row for a record with no lanes) and emits one row per lane, each
carrying that lane's OWN `goal`/`seat`/`one_liner`. The one-liner helper was renamed
`oneLinerOfLane` and reads a single lane's `refusal_text` directly — never an assembled sentence,
preserving the standing rule that the digest only ever quotes the record's own words (cited inline:
`memory/gateway/20260825-c-inspect-asks-the-read-half-of` ATTENTION 3). All rows sharing one record
carry the SAME `ask_id`, because there is one record on disk and no per-lane answering path exists yet
— `digest-recovery-thread` is held pending owner ruling on a separate ask (14).

## Consequences
The row shape stays key-for-key identical to `state-store/heart/ask-record.js#listOpenAsks`'s contract
— every consumer (digest merge, `system-digest` render, `pause-resume`/`reapAsk`, which is a different,
table-keyed function and unaffected) was swept and confirmed unchanged in shape. Intended, disclosed
side effect: the digest's `N waiting` status-line counter now counts a 3-lane stuck ask as 3 waits, not
1.

## Verification
`probe-inspect-asks.js` section G updated and run: 35/35 exit 0, asserting two rows for a two-lane ask,
both goals present, each row's one-liner its own lane's text. Deployed live on deploy tree `e8524c31`
(`ignite/core-daemon`).

## ATTENTION
1. A row's `ask_id` is shared across every lane of the same record — do not use `ask_id` alone as a
   row's unique key in any new consumer; pair it with `goal` (or the row's position) or two lanes of
   the same stuck ask will collide.
2. There is still no per-lane answering path: replying to one lane's row cannot resolve just that
   lane today. A future fix that adds per-lane answering must also decide what happens to the other
   rows sharing the same `ask_id` when one is answered — this was deliberately left open, held on ask
   14.
