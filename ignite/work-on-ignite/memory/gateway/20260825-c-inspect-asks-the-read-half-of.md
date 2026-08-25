# 20260825-c-inspect-asks-the-read-half-of — inspect asks: the READ half of the owner-ask record

kind: creation
component: gateway
date: 2026-08-25
commit: 537ecb87
deployed: no
pin: ignite/server/internal-api/probes/probe-inspect-asks.js
components: server,cli,state-store,bridges

## Motivation
`spec-owner-io` §5's system digest is SYSTEM-WIDE, and the process that renders it — the chat
bridge — is walled off from `heart.db` by `bridges/chat/probes/probe-chat-boundary.js`. The
thirteenth intent gave that process a WRITE path to the owner-ask record (`record-owner-ask`,
open | reap) and no read path at all, so `system-digest.js`'s `readOpenAsks` port had nothing
legal to wire to: the digest was BUILT AND PROVEN with an injected reader nobody could inject.
The store had no fleet-wide reader either — `listOpenAsks` is §2.1's per-goal wait predicate and
requires a goal.

## Design
A read-only TARGET of the existing `inspect` intent, never a fifteenth intent. That is this
daemon's own standing rule (ce-5/D3, stated twice in `gateway/parse.js` and again in
`server/internal-api/dispatch.js`): read-only store queries extend `inspect`, and a separate
intent would duplicate its plumbing and widen the authenticated surface, which is an owner act.
`asks` is a FIXED view like `jobs`/`queue` — no id, no status, no paging — because §5 renders
the whole waiting set or it is not that digest, and both refusals are enforced at the gateway.

A SEPARATE store predicate, `state-store/predicates.js#listAllOpenAsks`, rather than making
`listOpenAsks`'s `goal` optional. §2.1's predicate is per-goal and its caller must NAME the goal
it asks about; a default-null goal there would turn a forgotten argument into a silent fleet-wide
read. The WHERE clause is `listOpenAsks`'s with the goal clause dropped and nothing else changed,
so the digest and the per-goal wait predicate can never disagree about what an open ask is.

Rejected: a third act (`list`) on `record-owner-ask` — a "record" intent that reads is a name that
lies, and the two-act field-set refusal in its parse is written per-act on purpose. Rejected: a
new column for the ask's one-liner — §3 keeps the ask BODY out of the store and names
`evidence_pointer` as the on-disk copy, so the one-liner is read back from that copy.

## How it works
`server/heart/ask-record.js#listOpenAsks(heartStore)` binds the store, asks `listAllOpenAsks`
(open + posted, ordered by `posted_at`), and maps each row into the digest's documented port
shape: `id` (the ask id, which IS the Slack thread [T5-R7]), `goal`, `seat`, `label`,
`one_liner`, `opened_at` (= `posted_at`, when the ask reached the OWNER, which is what §5 renders
an age from) and `evidence_pointer`. `oneLinerOf` reads the first non-empty line of the ask copy
and truncates at 120 chars; an unreadable copy yields `null` — the row survives with no words
rather than invented ones. `dispatch.js` answers the target with those rows; `gateway/parse.js`
and `cli/commands/inspect.js` gained the member so the three copies of the target set stay
identical, and the CLI reaches it through `runJobsOrQueue` (same fixed-view shape).

## Consequences
Nothing was replaced or deleted. `listOpenAsks` (per-goal) is untouched and every existing caller
— `team-kit/ready.py`'s HELD row, `owed-answers.py`, `seatWaitingOnOwner` — is byte-identical in
behaviour. The bridge's `ask-store.js` gained a `listOpenAsks()` sender for the new target whose
refusal answers `null`, NEVER `[]`, so a gateway outage cannot be rendered as "nothing is
waiting". `inspect asks` is documented in `cli/README.md`. The three-copy lockstep that
`probe-inspect-executions.js` guards is re-asserted by the new probe as well.

## Verification
`server/internal-api/probes/probe-inspect-asks.js` — 19 checks, exit 0: in-process parse +
dispatch over a scratch store, asks written through the daemon's OWN writer. It proves the
listing crosses goals, that a REAPED ask and a NEVER-POSTED ask are both absent (two different
reasons, both §2.1), the row shape key by key, the one-liner against a two-line body, that an id
/ a status / an unknown key are refused at the gateway, and that a deleted ask copy costs the
sentence and not the row. `probe-inspect-executions.js` (the target-set lockstep) and the whole
`gateway/probes`, `cli/probes`, `server/internal-api/probes`, `server/heart/probes` and
`state-store` selftests re-run green. Not deployed: worktree `5-workbench/rbtv-redesign`, branch
`ignite/core-redesign`.

## ATTENTION
1. `listAllOpenAsks` and `listOpenAsks` must keep the SAME WHERE clause. They are one predicate
   asked two ways, and a fix applied to one of them alone is how a seat comes to be HELD by the
   engine and absent from the owner's digest at the same instant.
2. `posted` defaults to 1 on both and that default IS §2.1. An ask the owner was never told about
   is not a wait — no answer to it can ever arrive — so widening the digest's read to unposted
   rows would report the system as waiting on a human who was never asked.
3. The one-liner comes off disk, so it can be missing. `null` is the honest answer and the
   renderer drops the field; filling it with the seat name or the label would put a sentence on
   the owner's phone that nobody wrote.
4. Do not give this target an id, a status or paging "for symmetry". The digest reads the whole
   waiting set; a paged digest would report a partial set as the complete one, which is the
   silence §5 exists to end.
- listAllOpenAsks and listOpenAsks are one predicate asked two ways — never fix one alone
- the inspect TARGET set has FOUR copies: gateway, core, CLI Set, CLI HELP
