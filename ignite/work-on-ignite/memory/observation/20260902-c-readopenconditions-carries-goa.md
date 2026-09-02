# 20260902-c-readopenconditions-carries-goa — readOpenConditions carries goal_id/channel_id

kind: creation
component: observation
date: 2026-09-02
commit: 829a7b43227e7ad1c247ae01681b8c24308763f7
deployed: yes
pin: ignite/chat/probes/probe-chat-glance.js
components: chat,runtime

## Motivation
Owner ruling `d-digest-ui` 5(b): the digest's "open conditions" section should lead a goal-scoped
condition (today, only the frozen-goal alarm) with the goal itself, linked to that goal's Slack
channel, so the owner can tell WHERE without opening it — the same treatment `d-digest-ui` gave
open-ask rows in the sibling commit `f96d14e6`. `frozen.js` already emitted `goal_id`/`channel_id`
on the frozen-goal alarm and `emitter.js` already persisted both on the registry row, but
`observation/emitter.js#readOpenConditions` — the alarm registry's one published READ interface —
was the single place that dropped both fields before the digest could ever see them.

## Design
Widen `readOpenConditions`'s returned row shape to include `goal_id`/`channel_id`, reading `null`
whenever the emitting caller never supplied `goal_id` — never fabricated for a row that has none.
The row's own `channel_id` is always stored on disk (required to post at all), so passing it
through unconditionally would fabricate a "goal channel" for a machine-level row (the watchdog
family); gating `channel_id`'s pass-through on `goal_id` keeps the read honest to what the emitting
caller actually supplied. `system-digest.js` gains `renderConditionRow`: a goal-scoped condition
(`goal_id` set, `channel_id` present) leads with `<https://slack.com/archives/<channel_id>|*<goal_id>*>`
— deliberately a CHANNEL link, never a thread permalink, since a condition carries no thread
timestamp (`forward-path.js#slackThreadPermalink` was rejected as reuse here for that reason). A
machine-level condition (no goal) keeps leading with its own `subject` and carries
`evidence_pointer` inline, unchanged — there is no tap target to reach it through.
`signatureOf`/`emit`/registry format are untouched by design: verified byte-identical condition
signatures rendered from the live alarm registry (`.rbtv/runtime/ignite/alarm-registry.json`)
under the pre-edit and post-edit `emitter.js`.

## How it works
`readOpenConditions` filters open rows and maps each to
`{ signature, condition, subject, first_emitted_at, evidence_pointer, goal_id, channel_id }`, with
`goal_id`/`channel_id` both `null` when the row's `goal_id` is `null`. `system-digest.js#renderDigest`
calls `renderConditionRow` per row instead of the old fixed 4-field `joinRow`. A grep of every
`readOpenConditions` consumer confirmed the widened shape's blast radius:
`glance.js#createConditionReader` and `dispatch.js` (internal-api `inspect daemon`) are both
pass-throughs, unaffected; `probe-inspect-open-conditions.js` hardcoded the exact key set and broke
(fixed by adding `goal_id`/`channel_id` to its expected set plus a null-fields assertion on a
machine-level fixture row); `emitter.selftest.js`'s documented-shape loop didn't break but didn't
cover the new keys either (extended to assert both are `null` on its `GOOD` fixture, which supplies
no `goal_id`); `probe-chat-glance.js` had a fixture on the retired `cond.link` field (dead — no
longer read since the old `link ? ... : evidence_pointer` branch was replaced), updated to
`goal_id`/`channel_id` with the expected rendered string updated to the new
`<channel-link|*goal*> · condition · age` lead shape.

## Consequences
The dead `cond.link` field this commit removed the last reader of was itself created by an earlier
landing (`digest-row-shape`) — not a separate pre-existing defect, just the seam this change
widened. Landed alongside sibling commit `f96d14e6` (ask rows get a Slack link via a disjoint code
path, `glance.js#linkForAsk`) under the same `d-digest-ui` ruling — built concurrently by a
different seat (`digest-ask-link`), no shared file. At commit time, `probe-chat-glance-wiring.js`
was failing 5 checks unrelated to this change (all about ask-link resolution, mid-edit by the
concurrent `digest-ask-link` seat) — flagged for the orchestrator to confirm it lands clean, not
fixed here.

## Verification
`node ignite/chat/probes/probe-chat-glance.js` → `EXIT=0 CHECKS=30`.
`node ignite/observation/emitter.selftest.js` → `ALL PASS EXIT=0`.
`node ignite/observation/frozen.selftest.js` → `ALL PASS EXIT=0`.
`node ignite/runtime/internal-api/probes/probe-inspect-open-conditions.js` → `EXIT=0`.
`python3 ignite/observation/daemon-watchdog/probes/probe-watchdog-alarm-registry.py` → 31 checks, 0
failed; the sibling watchdog probes (`probe-watchdog-alarm-exit-zero.py`,
`probe-watchdog-bit7-silence.py`, `probe-watchdog-dry-run-no-dm.py`,
`probe-watchdog-timeout-strikes.py`) all `EXIT=0`. Committed `829a7b43`, deployed on branch
`ignite/core-daemon` (live tree `e8524c31` carries this commit); no daemon restart is required for
correctness beyond the digest process's own next natural restart/deploy cycle picking up the new
render.

## ATTENTION
1. `channel_id` on a condition row is gated on `goal_id` being non-null — never widen this to pass
   `channel_id` through unconditionally; a machine-level row (the watchdog family) always carries
   a stored `channel_id` (needed to post) that is NOT a goal channel, and passing it through would
   fabricate a goal link on a row with no goal.
2. A goal-scoped condition links its CHANNEL, never a thread — a condition has no `thread_ts` to
   permalink to. Do not reuse `forward-path.js#slackThreadPermalink` here; that was explicitly
   considered and rejected.
3. `readOpenConditions`'s row shape changed (two new keys) — any new consumer that asserts an
   exact key set (as `probe-inspect-open-conditions.js` did) will break on the next such widening;
   prefer asserting presence of the keys you actually read.
- channel_id gated on goal_id non-null
- conditions link the CHANNEL not a thread
- row shape widened
