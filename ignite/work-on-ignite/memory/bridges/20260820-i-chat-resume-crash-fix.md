# 20260820-i-chat-resume-crash-fix — chat-resume-crash-fix

kind: issue
component: bridges
date: 2026-08-20
commit: d491c8f0,91e287ca
deployed: yes
pin: bridges/chat/probes/probe-chat-summon-halted.js;server/ticker/probes/probe-chain-resume.js arm F
components: server
seeded: true

## Observed
Two defects blocked CP4 check 2 on the already-mapped stools conversation (goal `stools-canvas-audio-elevenlabs`, Slack C0BQE62C3AB) after D26/D27 (02:00Z / 02:30Z) re-cast consultant, goal-master, and the leader chairs from `opencode · grok` to `claude · opus` when the grok subscription hit `personal-team-blocked: spending-limit` (~01:33Z, 2026-08-20).

Defect 1 — resume crash, measured exec 30110 at 02:34:44Z: the follow-up live-answer (queue 995, parent exec 30033) ran `claude -p --resume …/seats/goal-master` and died in 11s (`Error: --resume requires a valid session ID or session title… Provided value "…/seats/goal-master" is not a UUID`). The crash sweep marked the chain `failed`; the reply leg delivered the 43-char `FALLBACK_TEXT` stub. Every later mapped follow-up that took the resume path crashed the same way.

Defect 2 — silent notes, measured msgs 33266/33306 ("how is the goal doing?"): `forwardFollowUp` filed each as a NOTE on thread exec-30028 with `routed_at_tick` NULL and returned `forwarded: true`. A `failed` tail is the one verdict the ticker's wake-redispatch never wakes, so the notes sat unread. Owner ruled D28 at 03:15Z (option (a) of the stools-silence ask): fix both before CP4, then re-post in stools. HEAD still carries the three predicates this commit added (`sessionRefIsForeign`, `chainHalted`, `summonHaltedChain`); no revert through 2026-08-23.

## Mechanism
`session_ref` is harness-vocabulary, not a portable UUID. OpenCode's `cwd-implicit` ref *is* the seat folder; Claude's `assigned` ref is a session UUID. After D26/D27 re-cast the same seat between turns, the ticker's chain-decision `why` ternary in `createTicker` still saw a parent row with a `session_ref` and a resume template, so it fed the folder to Claude.

Independently, `forwardFollowUp` on a mapped conversation only persisted a note. Delivery of that note is the daemon's job: a `done` tail wakes on the new sender row; a `blocked` tail has its own redispatch. A `failed` tail is owner-halted — nothing ever reads the note. After exec 30110's crash the two defects stacked: the mapped stools path could neither resume nor summon.

## Attempts
First attempt held — checked: `91e287ca` (01:17:41Z, same day, same `forwardFollowUp`) drops a stale mapping and mints a session-create when `resolved.reason === 'exec-id-unknown'` — a no-spawn disarm that had wedged both live goal channels. That is a different trigger (unresolvable exec-id, not a known-chain foreign resume or a failed tail); redesign-plan/loose-ends.md marks D28 distinct from it. `63413504` (same day) is the live-holder branch that owns "a sitting already holds the seat"; D28's comments cite it as the other door, not a prior try. `git log --before=2026-08-20T03:36:28` on `forward-path.js` and `ticker.js`, plus `--grep` for resume / foreign-harness / halted, found no earlier trial of these two triggers. `missed_trials_source: NONE`.

## Fix
`d491c8f0` (03:36:28Z) implements D28. The written fix-1 asked to "resolve the chain's exec-id to the real session UUID before resuming." What landed is a negative harness gate instead: `sessionRefIsForeign(parentProfile, spec)` inside the chain-decision closure compares `bindingOf(spec).harness` — the same reader `profiles.js#validateSpecKey` trusts, not `injection-ladder#harnessOf`, which returns null on a pathed argv0 — against the first `/` segment of `parentRow.profile`. A mismatch that is not a `harness-` prefix variant inserts `session-ref-foreign-harness` between `no-resume-template` and `parent-compaction`, forcing the transcript-embed fresh session. An OpenCode folder path cannot become a Claude session UUID, so falling through beats resolving. A NULL/legacy profile is deliberately not foreign (pre-D28 posture; old rows are not retroactively blocked).

Fix 2 adds `chainHalted` and `summonHaltedChain` inside `createForwardPath`. `chainHalted` reads the last 50 messages, takes the last `completion`, and reports halted only when `status === 'failed'`; `inspect-failed` / `no-messages` / `no-completion-in-tail` all return `halted: false` ("a blind reader must not mint one"). `summonHaltedChain` then no-ops unless halted, a seat home exists, `findLiveHolder` is empty (`63413504`'s case), and no queued `chat-thread: <id>` marker; otherwise it `threadMap.drop`s the dead mapping and `forwardSessionCreate`s. Invoked from the follow-up return only when `!corrective && route.kind !== 'agent' && !deduped`. The note write is unchanged (persistence); only delivery is added. Agent-route semantics stay ratified. `91e287ca` is in this entry's header because `fix-inventory.csv` bundled it with D28; it is not the D28 design.

## Consequences
Nothing was deleted. The note path, agent-route follow-up, live-holder branch, and wake-redispatch for `done`/`blocked` tails are unchanged. Same-day D29 (`eda7e4c7`, ruled 03:30Z) exempts summoned chairs from `verified-done`'s outputs-undeclarable check via `is_summoned_seat()` — the question D28 queued, because a summoned chair's product is conversation. That is why `fix-inventory.csv` lists `team-kit/coord.py` on D28: bleed from D29; neither listed commit touches coord.py.

Orchestrator residual at 04:00Z: the warm-leg still attempted a doomed foreign-ref resume and failed soft (~1–3s); the ticker gate is on the chain-decision path only. `chainHalted`'s last-50-row window is speculative. Later touches of these files (`e5a8e0de` D12 grant deletion, `01f61350` D81 comment cleanup, `0a3a14d2`/`607014d4` ferry, `a554197b` E22 boot-prompt) do not change the three predicates. No revert through 2026-08-23.

## Verification
RED-first against pre-fix code, green after. `probe-chain-resume` arm F seeds an OpenCode `cwd-implicit` parent (`session_ref === workdir`, profile `opencode/test-cwd`), re-casts the seat.md to claude, and asserts the chained spawn takes `chain=transcript` / `chainReason=session-ref-foreign-harness` and never puts the workdir in the resume argv. `probe-chat-summon-halted` (new, arms A–F): A halted + no sitting → note and chat-launch reminted; B `done` tail → note only (wake-redispatch owns it); C live sitting → note only; D agent route → note only; E already-queued create → no second; F mutation (summon call cut from a copy) turns A red. Commit reports chat probes 19/20 (`probe-chat-live-session` arm1 `E_UNMAPPED_BINDING` pre-existing) and ticker 29/29.

Deployed with a manual bridge restart at 03:37:16Z (deploy tree == `d491c8f0`). Live proof ~03:43–03:46Z: owner posted in stools; exec 30186 (non-conformant) revived as exec 30193; reply leg delivered 3731 chars at 03:46:54Z (`conformant:true`) — the mapped path through the halted-chain summon. Meet (fresh conversation) delivered 3522 chars at 03:47:04Z. Rode the later tree deploy `ac1c08d8` at 2026-08-21 18:14:37Z.

## ATTENTION
- `session_ref` is harness-vocabulary (Claude UUID vs OpenCode seat folder). Skipping `sessionRefIsForeign` on a cross-harness re-cast feeds the folder to `--resume`; the reply-leg fallback stub then masks the crash as a normal 43-char answer.
- A NULL/legacy `jobs_log.profile` is treated as not-foreign on purpose so pre-D28 rows keep resuming. Widening what counts as unkeyed silently exempts more resumes from the gate.
- `summonHaltedChain` refuses three cases: the agent route, a live holder (`63413504`), and a queued `chat-thread:` create. Widening any of them double-spawns; narrowing them re-rots notes. Re-run `probe-chat-summon-halted` A–F after any `forwardFollowUp` edit.
- `chainHalted` treats every read failure as `halted: false` ("a blind reader must not mint one"). Flipping that default toward more aggressive summoning double-spawns sittings on inspect flakes.
