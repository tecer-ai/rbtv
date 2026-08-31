# 20260831-i-the-door-admitted-by-label-a-l — the door admitted by label; a leader FYI minted an ask

kind: issue
component: chat
date: 2026-08-31
commit: a3ca7059
deployed: no
pin: ignite/chat/probes/probe-chat-ask-release.js

## Observed
Goal `transcript-summarizer-build`, Slack channel `C0BTFH87E6B`, 2026-08-31 16:19–18:35Z: three
blocking escalations from the `leader` chair were refused at `ask-thread.js#postAsk` (label bypass
did not cover them the way it should have) and delivered only to the owner's DM; he sat in the
goal channel and saw nothing for 2h14m (`d-escalation-surface`, owner interview). Root cause,
found while composing the fix (not at incident time): commit `1ccb943a` (`d-ask14-recovery-thread-
shape`) carved `postAsk`'s [T2-R14] gate open by `label !== 'recovery'`, and `bus-ferry.js` gave
the label `recovery` to an `escalation` row *and* to every other `leader` row. So an ordinary,
non-blocking `leader` message also passed the door and minted a BLOCKING ask record — it never
silently dropped, it silently over-admitted, which is the opposite defect from the one `label`
bypass was built to fix ([the 2026-08-27 entry `20260827-i-a-refused-escalation-retried-2`] had
already warned against exactly this shape of fix: "Do not make `postAsk` admit non-interactive
seats to fix a delivery problem" — the warning fired on the escalation case, and the SAME label
mechanism reused for the leader case is what tripped it).

## Mechanism
`postAsk`'s admission test used `label`, a two-value DIGEST TAXONOMY
(`work-content`/`recovery`) the system-digest sorts asks on, as an AUTHORIZATION FACT. `bus-ferry
.js` computed `askLabel = isEscalation || row.from === 'leader' ? 'recovery' : 'work-content'` —
one formula, two callers with different needs (escalations needing to bypass [T2-R14]; the digest
needing a sort key), and the label carried both. Any `leader` row got the SAME label regardless of
whether it was actually the ONE type [T2-R14] is meant to carve out.

## Attempts
`recovery-poster.js` (also landed in 1ccb943a) uses the SAME `label: 'recovery'` bypass for a
STRUCTURALLY DIFFERENT case: a daemon-decided exhausted-lane ask (`spec-recovery §5`), never a
seat's own traffic. It ALSO passes `kind: 'recovery'` (a field `postAsk` already accepted and
`chat-bridge.js#postOwnerAsk` already forwarded unchanged, just never gated on). That existing,
unrelated `kind` field is what made a clean fix possible without touching `chat-bridge.js`
(out of this seat's row custody, and already dirty with a parallel seat's work).

## Fix
`postAsk`'s gate: `label !== 'recovery'` → `kind !== 'escalation' && kind !== 'recovery'`.
`kind: 'escalation'` is set by `bus-ferry.js` ONLY for `row.type === 'escalation'` (never for an
ordinary `leader` row); `kind: 'recovery'` is untouched, so `recovery-poster.js` needed zero
changes. `label` keeps deciding the digest sort and decides admission for nobody. Separately: a
row refused at the door (now genuinely only non-escalation, non-recovery, non-designated-seat
rows) is no longer silently discarded — the SAME door rescues it as a 💭 notice
(`marker: 'note'` → `postNote`, pre-existing, never checked [T2-R14], mints no record). A failed
notice attempt is treated as an ordinary post failure (falls through to the existing agent-thread/
DM/retry ladder), never a second terminal refusal.

Also built: `openThread` splits a composed ask/note body on a private marker
(`ASK_REPLY_SPLIT`, exported) into a top-level post (decision + TLDR + alternatives) and a first
threaded reply (full reasoning + evidence pointer), same `thread_ts` as the ask id. `bus-ferry.js
#splitAskBody` decides whether to insert the marker — only when the seat's own body has a
discernible "Reasoning:"/"Full reasoning:" heading; absent that, nothing is fabricated and the
body posts whole.

## Consequences
The old `terminalRefusal`/`deliverEscalationInFull` path for a REFUSED escalation is now
defensive-only (an escalation can no longer reach [T2-R14] refusal in normal operation, since
`kind: 'escalation'` bypasses it upstream) — left completely untouched, per the plan's wall, for
`esc-dm-ban` to retire once the dead branch is provably permanent. No schema change, no change to
`open_asks.ask_id` identity or the release door's exact-thread match. `fallbackArm` untouched.

## Verification
`node ignite/deploy/probe-suite.js --only probe-chat-ask-release` — PASS, 40 checks (was 32).
`node ignite/deploy/probe-suite.js --only probe-chat-bus-ferry` — PASS. Full
`--dir chat/probes` run: 26/29 PASS; the 3 failures (`probe-chat-boundary`,
`probe-chat-live-session`, `probe-owner-ask-hold`) reproduce IDENTICALLY against the pre-change
HEAD versions of `ask-thread.js`/`bus-ferry.js` (verified by swapping in `git show HEAD:<path>`
and re-running just those two probes) — pre-existing, unrelated to this change. New probe arm E9
(`probe-chat-ask-release.js`) replays the incident end to end through the real bridge: an
escalation from a non-designated seat is admitted, mints one record, and renders the ruled post
shape. NOT DEPLOYED: `rbtv-chat-bridge` must restart.

## ATTENTION
- `label` is digest taxonomy, not an authorization fact — a future ask-door change must gate on
  `kind`/`type`, never introduce a THIRD meaning for `label`.
- `recovery-poster.js`'s `kind: 'recovery'` bypass and `bus-ferry.js`'s escalation `kind:
  'escalation'` bypass are TWO SEPARATE system-decided cases with the same shape (daemon judgment,
  not a seat's courtesy) — do not merge them into one flag, they have different callers and
  different failure modes if either regresses.
- The terminal-refusal/`deliverEscalationInFull` branch for a refused ESCALATION is now
  unreachable in normal operation (kept intact, walled off for `esc-dm-ban`) — a future change
  that removes it should re-verify no caller still relies on it as a safety net.
- `ASK_REPLY_SPLIT`'s marker convention ("Reasoning:"/"Full reasoning:" heading) is NOT yet taught
  to any seat-authoring prompt — every existing escalation body degrades to "everything above the
  fold" until a seat is told to write that heading. Teaching it is out of this seat's scope.
- label is digest taxonomy, never an authorization fact — gate on kind/type
