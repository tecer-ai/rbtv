# 20260901-c-digest-becomes-a-plain-waiting — digest becomes a plain waiting-on-you list (R-A2)

kind: change
component: chat
date: 2026-09-01
commit: 4802a888
deployed: no
pin: ignite/chat/probes/probe-chat-glance.js
components: bridges,state-store

## Motivation
Owner ruling R-A2 (`owner-ask-redesign.md` §2): the system-channel digest's ask row was machine
text (`• goal · seat · LANE: goal / seat · 4h · 084259`) — ids the owner does not use, a seat token
he does not need, and a `LANE:` label that is system vocabulary. The row's root cause: it was built
entirely from `one_liner` (the machine-composed first line of the ask's on-disk body) and
`displaySuffix` (the thread-ts tail) — fields born for the daemon's own bookkeeping, never for a
reader. §5.2 rules the replacement: one plain sentence per ask, the goal name as the tap target,
no ids/LANE/seat token in the visible line.

## Design
`renderAskRow` (`ignite/chat/system-digest.js`) now renders `• <link|goal name> — <subject or,
when empty, one_liner> · waiting Xh`, dropping the seat token and the trailing id suffix (kept only
as the lead's fallback text when an ask genuinely carries no goal — the one case a lead cannot be
left blank). `subject` is the new field `ask-shape` (a sibling seat building the same owner-ask
redesign in parallel) adds to the `listOpenAsks` row contract; a pre-existing row carries
`subject: ''` per that contract, so `subject || one_liner` degrades cleanly with no plumbing this
seat owns. Rejected: waiting for `ask-shape` to land before coding against `subject` — the
interface contract (`digest-sentence` seat.md) fixes the field name and its empty-string fallback
in advance specifically so the three sibling seats can build in parallel; coding against the name
now and tolerating its absence is the point of a fixed contract.

`snapshotOf`'s text input moved from `one_liner` alone to `subject || one_liner`, matching what the
row now renders — the alternative (leaving the snapshot on `one_liner` while the row renders
`subject`) would mean the digest could render a NEW sentence without ever re-posting to announce it,
which defeats "changed-only" from the reader's side. Link, age and goal name stay OUT of the
snapshot, unchanged — the standing trap this module's own header comment states.

`glance.js#linkForAsk` gained a `systemChannelId` fallback: R-A1 has a goal with no Slack channel
get its recovery/keep-or-close ask posted straight into `#system-channel` instead of nowhere. Before
this change, `linkForAsk` gave such an ask NO link (the goal→channel resolver answers `null`
cleanly). That is now indistinguishable from "this ask genuinely has no thread" and denies the
owner a working tap target for an ask that DOES have a real thread — just not on a goal channel.
The fallback triggers ONLY when the resolver answers cleanly with no channel (or `ask.goal` is
absent); a resolver that THROWS (an operational failure, not evidence of the R-A1 case) still
degrades to no link, unchanged from before — a throw is not proof the ask lives in the system
channel.

## How it works
`renderDigest`'s ask section header also went plain: `Waiting on you (N):` with rows beneath it, or
a single line `Nothing is waiting on you.` when the list is empty — replacing `❓ open asks` /
`• none open`. The `Open conditions` section (`digest-condition-goal`'s territory) is untouched.
`sortAsksBlockingFirst`/`isInformationalAsk` are untouched — both still key on `one_liner`
specifically (the `bus-ferry.js#FALLBACK_MARK` text mark bakes into `one_liner`, never `subject`),
per this seat's DoD ("the structural field is out of scope, disclosed").

`ask-record.js#listOpenAsks` was checked, not touched (out of `digest-sentence` custody):
`listAllOpenAsks(db, { posted = 1 } = {})` (`state-store/predicates.js:48`) already defaults to
`posted = 1`, and `ask-record.js#listOpenAsks` calls it with `{}` — so a never-posted
`recovery-*`/`disposition-*` row (`posted = 0`) is excluded before the digest or the bridge ever see
it. `inv-digest-render`'s "recovery asks get no link" claim (superseded already by the orchestrator's
own check of `ask-record.js:31` per `owner-ask-redesign.md` §5.1) is not repeated anywhere in
`system-digest.js`/`glance.js`'s comments — nothing needed correcting there.

## Consequences
Nothing deleted. The row shape `digest-row-shape` built (`d76eecd0`) and the plain `• none open`
empty state (`bridges/20260824-c-changed-only-system-digest-bot`) are both superseded by this
change — expected, since THIS mission (`owner-ask-redesign`) supersedes the prior `d-digest-ui`
mission's row shape by owner ruling. `linkForAsk`'s signature changed from
`(ask, resolveGoalChannel, log)` to `(ask, resolveGoalChannel, systemChannelId, log)` — its one call
site (`glance.js#checkSlot`) was updated in the same change; it has no other caller in the repo
(grepped: only `exhaustion.js`/`dispatch.js` reference it in COMMENTS, never call it).

## Verification
`node ignite/chat/probes/probe-chat-glance.js` — 33 → 40 checks, EXIT 0. New checks: the new row
format (goal-as-link-text, subject-or-one_liner sentence, `waiting Xh`, no seat/LANE/ref anywhere in
the text), the plain-language empty state, and four snapshot-signature checks — a goal-name-only
change does NOT re-post, a link-only change does NOT re-post, an ask acquiring a real subject for
the first time (simulating `asks-repost`'s in-thread DB update to an already-open ask) posts EXACTLY
ONE re-post, and the next slot with the same subject posts NONE after.
`node ignite/chat/probes/probe-chat-glance-wiring.js` — 27 → 29 checks, EXIT 0. Rewrote the four
existing id-shape rows to the new format and added a fifth: a thread-ts id whose goal resolves to no
channel now links its own thread in the system channel (`https://slack.com/archives/Csystem/p...`);
confirmed a THROWING resolver still degrades to no link (never guesses the system-channel fallback
on an operational failure, only on a clean "no channel" answer).
Regression: `probe-chat-boundary.js` and `probe-owner-ask-hold.js` are RED, but pre-existing and
unrelated — neither references `system-digest.js` or `glance.js` (grepped), and a scratch worktree
at pristine HEAD (`0363d55e`, before this change) hits the same `MODULE_NOT_FOUND` /
`TypeError: Cannot read properties of null (reading 'find')` failures untouched by node_modules
availability in the worktree, confirming they are not caused by this change.
Committed `4802a888` on `ignite/core-daemon`, pathspec `ignite/chat/system-digest.js
ignite/chat/glance.js ignite/chat/probes/probe-chat-glance.js
ignite/chat/probes/probe-chat-glance-wiring.js`. NOT DEPLOYED — the daemon runs
`~/.local/state/rbtv-deploy` (`0363d55e`), a separate deploy window this seat does not open.

## ATTENTION
1. `subject || one_liner` is BOTH the row's text AND the snapshot's text, on purpose — the two must
   stay the same expression. Rendering one and hashing the other reopens the exact defect a
   changed-only digest exists to prevent (a sentence the owner never got notified about).
2. `linkForAsk`'s `systemChannelId` fallback fires ONLY when the goal resolver returns cleanly with
   no channel (or `ask.goal` is absent) — a THROWING resolver must keep degrading to no link. Do not
   collapse the two cases: a throw is an operational failure, not evidence the ask's thread lives in
   the system channel.
3. `sortAsksBlockingFirst`/`isInformationalAsk` still key on `one_liner`, never `subject` — a future
   edit that "simplifies" by switching the sort key to `subject` breaks silently, since
   `bus-ferry.js#FALLBACK_MARK`'s text mark is only ever baked into `one_liner`.
4. Do not re-add the seat name or a `ref <id>` fragment to `renderAskRow`'s output "for
   completeness" — R-A2's whole point is that the visible line carries none of that; the id is
   still available to the owner as the link's destination, never as visible text.
- subject and the snapshot text must stay the SAME expression (`subject || one_liner`) or changed-only breaks silently
- linkForAsk's systemChannelId fallback is for a clean "no channel" answer only, never for a thrown resolver
- subject and the snapshot text must stay the SAME expression (subject || one_liner) or changed-only breaks silently
- linkForAsk's systemChannelId fallback is for a clean no-channel answer only, never for a thrown resolver
