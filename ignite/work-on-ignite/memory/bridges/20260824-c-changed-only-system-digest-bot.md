# 20260824-c-changed-only-system-digest-bot — changed-only system digest + bot status line

kind: creation
component: bridges
date: 2026-08-24
commit: eddf1ee3,b26ae2de,a2a93494
deployed: no
pin: ignite/bridges/chat/probes/probe-chat-glance.js
components: observation

## Motivation
The owner had no phone-glance view of what was waiting on them [T5-R13, C-12, D-6-ruling]:
no changed-only system digest, and no standing `N waiting` status line. The two surfaces
that DID exist were the ones the baseline deleted — per-ask re-pings and per-goal digests —
so the owner either got notified about the same ask repeatedly or had to open every goal
channel to reconstruct the state.

## Design
Two modules, split because they answer different questions and update on different clocks.
`bridges/chat/system-digest.js` answers "what changed since the owner last SAW a digest" on
a 2-hourly slot clock; `bridges/chat/status-line.js` answers "how much is waiting right now"
on an event clock. Fusing them would have made the status line inherit the slot timing it
must not have, and made the digest inherit the seven-trigger recompute it must not have.

Every reader is an injected port (open asks, open alarm conditions, blocked count, the Slack
status writer). This is what keeps the boundary `probes/probe-chat-boundary.js` enforces: the
bridge is a separate process from the daemon and may hold no store handle. The alternative —
having the digest open `heart.db` — is exactly the violation `ask-store.js` was rewritten to
avoid on 2026-08-24.

Rejected: putting the alarm-condition read behind a stand-in registry so the digest could be
demoed end-to-end. The registry and its emitter are impl-alarms' (`ignite/observation/`,
spec-owner-io §9); a stand-in here would be a second source of alarm truth and the real one
would have had to delete it.

## How it works
`createSystemDigest({ post, systemChannelId, readOpenAsks, readOpenConditions, statePath })`
exposes `check(at)`. `check` returns `{ran:false}` unless `at` is one of the ten
America/Sao_Paulo slots (00, 06, 08, 10, 12, 14, 16, 18, 20, 22 — the hour is resolved through
`Intl` at that timezone, never through a fixed offset, so a DST rule change cannot silently
shift the slots). On a slot it builds the §5 snapshot — `(open ask ids + one_liners + open
condition signatures)`, sorted — and compares it to the last DELIVERED payload. Equal → it
posts nothing. Different → it renders asks → conditions → links and posts `kind=digest`
through `outbox.js` into the system channel only.

`createStatusLine({ readOpenAsks, readBlockedCount, setStatusText })` exposes `onTrigger(t)`.
`t` must be one of the seven §6 triggers; anything else returns `{updated:false}` and leaves
the status text alone. On a real trigger it renders `N waiting · oldest Xh · M blocked` and
writes it through the status port. It is handed no outbox, no channel and no transport, so
it cannot post even by mistake.

## Consequences
Nothing was replaced or deleted — both surfaces are new. Neither is reachable in production
yet: `index.js#main()` wires no slot driver, no ask/condition readers and no Slack status
port, so both are BUILT AND PROVEN in the same sense the approval and pause/resume doors are.
The digest's condition section renders `• none open` until impl-alarms lands the
alarm-signature registry's READ interface; wiring that port is the one follow-up.

## Verification
`probes/probe-chat-glance.js` — 30 checks, mocked Slack and a mocked clock, no live post.
Every guard was mutation-checked before the commit: making 03:00 a slot, putting age into the
snapshot, advancing the baseline on the attempt instead of the ack, accepting any trigger, and
rounding instead of flooring `oldest Xh` each reddened exactly the rows that claim to cover
them. Full `bridges/chat/probes` dir: 26/26 GREEN. Not deployed — worktree
`ignite/core-redesign` only.

## ATTENTION
1. The digest baseline advances ONLY on `delivered === true`. The outbox mints
   `pending-delivery` and flips on Slack's ack; advancing on the attempt would mean a digest
   Slack never accepted silences the next slot and the owner never learns of the change.
2. Age is rendered in the rows but is deliberately ABSENT from the snapshot. Adding it — which
   looks like a completeness fix — makes every one of the ten slots post and destroys the
   changed-only property the whole module exists for.
3. The baseline is persisted to `statePath` and read at construction. A version of this holding
   the baseline in memory re-posts an unchanged digest after every daemon restart.
4. The status line must never gain a post path. It is the ONE surface allowed to stand because
   it costs no notification; a post here would recreate the per-ask re-ping [T5-R13] deleted.
5. Do not add an eighth status-line trigger without a spec change. The refusal is not defensive
   coding — a status text that redraws on every event is a poll loop against Slack's API.
- the digest baseline advances only on Slack's ack, never on the post attempt
