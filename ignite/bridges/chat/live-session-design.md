# Live sessions + event-driven bridge — design

Owner goal (ruled 2026-08-10, this session): under-3-second Slack replies on warm paths, thread
continuity as a feature, covering (1) owner↔channel-master, (2) ferry to/from goal seats,
(3) async job follow-ups. Resolves `_channel-master/issues.md` `i-cold-contact-latency` and
`i-no-completion-nudge`, and closes the feedback half of `i-profile-switch-no-feedback` /
`i-switch-thread-scope-unclear`.

## Measured baseline (2026-08-10, live daemon, 39 sittings + journal)

| Leg | Today (avg) | Evidence |
|---|---|---|
| Slack → spawn decision | ~1s (0.3–1.9) | nudged ticks, 7 samples |
| Process creation (systemd-run + bwrap + CLI cold start) | 2.75s (1.8–3.6) | sessions.csv vs exit-file mtime minus duration_ms, 14 samples |
| First token (CLI boot + ~27.5k-token system prompt: seat.md 51KB + CLAUDE.mds 24KB + rules 26KB) | 5.5s (2.2–15.1) | ttft_ms, 39 samples |
| Reply-leg poll (turn-end detection) | 1.5s (0–3) | reply-leg.js:104, 3s interval |
| **Direct-thread total (simple message)** | **~12s (8–20)** | matches owner-observed 10–20s |
| Ferry: goal bus → Slack | +7.5s (0–15) | bus-ferry.js 15s blind setInterval, no event hook |
| Ferry DM-fallback compounding | + full sitting pipeline | chat-bridge.js:118–150 mints a new sitting |

## Ruled decisions (owner, 2026-08-10)

1. **Mechanism:** live process + resume fallback. Warm claude process per active thread fed over
   stdin; after 10 idle minutes it dies; next message cold-spawns with `--resume` (existing,
   shipped resume machinery) so thread memory survives the reaper.
2. **Scope:** ALL human-interactive seats (`human-interactive: yes` frontmatter) the owner is
   actively messaging — channel-master and e.g. a planning interviewer alike. Non-interactive
   seats keep one-shot semantics. Warm window: 10 min after last owner message, unless the seat
   closes naturally first.
3. **Ferry:** file-watch (inotify) on coordination buses + existing 15s poll retained as safety
   net. No coord.py change.
4. **Async jobs:** both — daemon posts the settled outcome into the originating thread itself
   (no agent turn), AND wakes the seat's session with the outcome when the job carries a
   follow-up/action flag.

## Components

### 1. Live session manager — **BUILT 2026-08-10** (`ignite/server/spawn/live-sessions.js`)

Registry: chatThreadId → { pid/unit, sessionId, seat, profile, lastOwnerMsgAt, state: idle|in-turn }.

- **Warm spawn:** existing profile argv (spawn-profiles.yaml exec template) with
  `--input-format stream-json --output-format stream-json` instead of one-shot text input;
  `--session-id` minted as today; `--append-system-prompt-file seat.md` unchanged; same bwrap
  cage/systemd-run carrier.
- **Feed:** new owner message while warm → write a stream-json user message to stdin. Mid-turn
  arrival: write immediately if the CLI queues it (spike-verify at implementation start);
  otherwise manager-side FIFO released on the turn's `result` event.
- **Reply:** manager parses stream-json stdout; on each `result` event → `toMrkdwn` → post to the
  thread directly. Event-driven; replaces the 3s reply-leg poll on warm paths. Reply-leg stays
  untouched as the cold/one-shot path and safety net.
- **Reaper:** `live_session_idle_ms` (default 600 000) after last owner message → close stdin,
  let the process exit, record end. Also reaped: on natural exit, on master-profile apply
  (guarantees a switch takes effect at the very next message — closes the switch-scope
  ambiguity), and beyond `live_session_max` (default 4) by LRU.
- **Fallback:** any death (crash, reap, restart) → next message takes today's cold path with the
  resume template. Continuity survives; only latency degrades.
- **Accounting:** one sessions.csv sitting row per live process (spawn→exit), per-turn events in
  the session log (already stream-json). Heart/acct told of each fed turn (see hook choice).

### 2. Ferry file-watch (`bus-ferry.js`)

`fs.watch` on each goal's `coordination/` dir (+ goals root for new goals), 200ms debounce →
run the existing `_runOnce` pass. The 15s `setInterval` poll stays as the safety net (inotify
overflow, unwatched new dirs). Watcher only *triggers* the pass; the pass still reads at rest
(size-check + parse) — never sources content from the raw event.

### 3. Async job completion (dispatch/settle path)

At enqueue, jobs already correlate to the originating chat thread. On settle the daemon:
(a) always posts a short outcome line into that thread via the bridge (no agent, no inference);
(b) when the job carries `wake: true` (or an action follow-up), also feeds/spawns the seat's
session with the outcome as prompt so the agent can act on it.

### 4. Dispatch hook for warm feeds — RULED (owner, 2026-08-10) · **BUILT 2026-08-10**

**Direct feed + fire-and-forget accounting event.** The bridge hands a warm-session message
straight to the live process (~0.1s); the manager reports each fed turn to the gateway so
acct/session records stay whole. Admission checks (allowlist, caps) run bridge-side as today.
Cold spawns keep the queue path unchanged. (Queue-path alternative rejected for its 0.3–1.9s
nudge+tick cost — warm total would sometimes exceed the 3s target.)

## §1/§4 as built (2026-08-10) — the spike, the code, and the four deltas

### The spike that unblocked it (claude 2.1.226, this box, 2026-08-10)

The design's first risk was "stream-json stdin mid-turn semantics unverified". All four questions
are now **measured**, and the manager-side FIFO fallback is **not needed**:

| Question | Measured answer |
|---|---|
| The user-turn shape on stdin | `{"type":"user","message":{"role":"user","content":[{"type":"text","text":"…"}]}}` + `\n`, one JSON object per line |
| A second message written MID-TURN | **The CLI QUEUES it.** Written 3.0s into a 15.8s turn: no error, no interleave; answered 3.3s after turn 1 ended, strictly in order. **So: write immediately.** The manager keeps a RESPONDER queue only (match `result` events to waiters in arrival order), never a send queue |
| Closing stdin | Clean exit, code 0, ~300ms |
| `--session-id` + a later `--resume` | Context preserved, in-process AND across a fresh process. ⚠ `--resume` of an id that does NOT exist ends the turn `is_error` with `No conversation found with session ID: …` — which is why an errored turn is reported as NOT answered (below) |
| Per-turn events | A fresh `system/init` is re-emitted before EVERY turn; exactly one `result` per fed turn |

### Where the code is

| Piece | File |
|---|---|
| The manager — registry, eligibility, launch, feed, reaper, LRU, shutdown | `server/spawn/live-sessions.js` (new) |
| Live-pipe carriage (`--pipe --quiet`, no `StandardOutput/Input` properties) | `server/spawn/carrier.js` — `buildSystemdRunArgs({ …, live: true })` |
| The wire: `live-feed` intent | `gateway/parse.js` (`INTENTS`, `parseLiveFeed`), `server/internal-api/dispatch.js` (`INTENTS`, `LIVE_FEED_KEYS`, `handleLiveFeed`) |
| Construction + shutdown | `server/index.js` (`createLiveSessions`, `liveSessions.stop()` in `shutdown`) |
| The bridge's caller | `bridges/chat/live-sessions.js` (new), hooked in `chat-bridge.js#onChatMessage` before the forward path |
| Config | `bridges/chat/config.js` — `live_sessions` (default **true**) |
| Proof — the harness half | `bridges/chat/probes/probe-chat-live-session.js` — 29 checks, 7 arms, 1 mutation arm |
| Proof — the POSTING half | `bridges/chat/probes/probe-chat-warm-post.js` — the fence extraction, the ⏳ receipt, and the posted-once claim (§ the two defects below) |

### The four deltas from the sketch — each forced, each measured

1. **The manager is DAEMON-SIDE, not bridge-side.** `probe-chat-boundary` scans every runtime `.js`
   under `bridges/chat/` for `child_process|\bspawn\s*\(` and fails the suite on a hit —
   chat-bridge-spec.md Behavior #5's "no spawn path" is a STRUCTURAL invariant of that subtree. A
   bridge-side manager would also have had to re-implement the seat cage, the carrier, profile
   resolution and the at-dispatch record. §4's ruling is intact: the feed is DIRECT (one loopback
   call, no queue row, no tick), which is the thing the ruling chose. Only the process's holder moved.
   This is also what §1's own path (`ignite/server/spawn/live-sessions.js`) said all along.
2. **§4's fire-and-forget accounting event collapsed to ZERO code.** It existed because a
   bridge-held process would have to TELL the daemon what it did. Daemon-side, the manager writes
   the `sessions.csv` sitting row itself (same writer as the dispatch door) and tees the
   stream-json transcript to the same `logs/<session-id>.log`. No `jobs_log` execution row is
   minted: a live session bypasses the queue BY RULING, so an execution row would be inventing a
   queue row that never existed — a false record, not a whole one.
3. **Every live session is a `--resume`, never a fresh `exec`.** The FIRST message of a
   conversation takes today's cold path unchanged; the SECOND launches the warm process by
   resuming that chain's `session_ref` (read from the store via the `exec_id` the bridge already
   holds — never taken from the wire). Because `session_ref: {source: assigned}` and a resumed
   claude session keeps its id, the chain's ref is ONE value for its whole life, so the reaper's
   fallback is correct BY CONSTRUCTION: the cold `--resume` spawn that replaces a reaped live
   session is the same conversation. Cost, stated: message #1 cold, #2 pays the live launch,
   #3 onward warm.
4. **`live_session_idle_ms` / `live_session_max` are DAEMON knobs, not bridge config**
   (`RBTV_IGNITE_LIVE_IDLE_MS` / `RBTV_IGNITE_LIVE_MAX` on the daemon unit; defaults 600000 / 4).
   They govern processes the daemon holds and the memory they occupy; a bridge that could set them
   over the wire would be dictating another process's resource policy. Only the enable flag
   (`live_sessions`, default true) is the bridge's, because "try the warm path first" is genuinely
   the bridge's decision.

Two smaller ones, both measured: **an errored or empty turn is reported as NOT answered** so the
caller falls back rather than posting a blank fast reply (the `No conversation found` case); and
**the master-profile reap needs no hook into the python** — the caller resolves the profile from
its own freshly-read config on every message, so a warm session whose conversation now names a
different profile is reaped at the next message, which is exactly the guarantee §1 asked for.

### The two defects the posting path shipped with (owner-reported 2026-08-10, fixed the same hour)

Both were in ONE block — `chat-bridge.js#onChatMessage`'s `warm.answered` arm — and both are the
same mistake: **the warm arm posts, and posting was already a solved problem it did not reuse.**
The cold path had been correct on both counts since 30fba1e.

1. **THE ANSWER ARRIVED TWICE.** A live session's `result` event carries the WHOLE final turn text,
   and the reply contract asks the agent to end its turn with the message between
   `<<<SLACK-REPLY>>>` and `<<<END-SLACK-REPLY>>>`. So a *conformant* warm reply is the prose, the
   sentinels, and the message again — and the arm posted it raw. The owner read his answer twice
   with the markers between the halves, minutes after df65147 went live. Fixed by extracting
   through `reply-leg.js#extractFenced` — the COLD PATH'S OWN extractor, imported, never a second
   regex: last complete pair wins, sentinels matched as whole trimmed lines. An unfenced reply is
   posted unchanged, so the fix can only ever remove a duplication that is there.
   ⚑ The bridge is the right layer and the daemon is not: `extractFenced` lives in the bridge
   subtree, the manager is daemon-side, and `ignite/CLAUDE.md`'s relocatable-subtree rule runs in
   both directions. A conformance verdict is the reply contract's business — which is a CHAT
   contract — so it belongs where the contract lives.
2. **NO READ RECEIPT ON A FOLLOW-UP.** The ⏳ marker was stamped only on the cold-forward branch,
   which a warm turn returns before reaching. Message #1 of a thread was marked and every message
   after it — precisely the warm ones — showed nothing, which the owner read as the bridge ignoring
   him. The original reasoning ("a marker added and removed inside two seconds is noise") rested on
   the §1 budget below; the journal for this box on 2026-08-10 measured the warm turns that
   provoked the report at **13.4s, 18.5s and 25.8s**, so the premise was simply false in practice.
   The mark now happens BEFORE the feed, where the gap actually is; `deliverToOwner` already takes
   it off on both legs. `markPending` became idempotent on the same message so the warm→cold
   fall-through cannot flicker it, and a message the forward path then REFUSES has its marker
   cleared — a ⏳ with nothing behind it is dead air wearing the costume of work in progress.

**No double-post race exists, and the reason is structural** (checked before looking for one): a
warm turn writes no queue row and no `jobs_log` row (delta 2 above), so `recent_ticks` carries no
`spawn` action for the reply leg to capture, and the warm arm returns before `replyLeg.arm`. The
live journal for the first warm conversation (`D0BJ…053339`) shows it directly — one
`reply leg delivered worker reply to owner` for the cold turn at 14:47:53Z, then three
`chat message handled on the warm path` with no further capture or delivery. The property is now
asserted rather than argued: the probe requires exactly one post and zero enqueues per warm turn.

### ⚠ ON THIS DEPLOYMENT, NOTHING IS ELIGIBLE YET — two owner decisions

The gates are implemented as ruled (`human-interactive: yes` seat + a claude profile). Measured
against the live config on 2026-08-10, **zero conversations pass them**:

| Blocker | Fact | The decision |
|---|---|---|
| The master profile is not claude | `.rbtv/config/chat-bridge-config.json` has `master_profile: "kimi"`, and `--input-format stream-json` is claude's flag — no other harness's equivalent has been MEASURED, so a non-claude profile is ineligible rather than guessed at | Switch the master profile to a claude one (`master-profile` capability), or commission the measurement for kimi |
| The channel-master seat does not declare the gate | `.rbtv/goals/_channel-master/seat.md` frontmatter carries `mode: one-shot` and **no `human-interactive:` key** | Declare `human-interactive: yes` (+ the required `fallback:` arm) on that seat, or rule that the master path is exempt from gate 1 |

The only `human-interactive:` seats on the box today are the four planning seats of
`meeting-transcript-digest` — goal/agent traffic, not the owner's DM path, which is the surface
`i-cold-contact-latency` is about. **Until one of the two rows above is decided, the warm path is
armed and inert, and every conversation takes exactly the cold path it takes now.**

## Expected budgets after

| Path | Today | After |
|---|---|---|
| Warm direct thread | ~12s | **~1.5–2.5s** (feed ~0.1 + inference 1–2 + post 0.3) |
| Cold (first contact / after idle) | ~12s | ~8–12s unchanged (resume spawn); receipt emoji already exists, no ack work needed |
| Ferried bus row → Slack | 0–15s poll | **~0.3s** (watch debounce + pass) |
| Async job outcome → owner | never (manual ask) | ~0.5s after settle |

## Per-harness eligibility verdicts — measured 2026-08-10

Task 7.641 answered "why is warm claude-only?" (owner asked 2026-08-10) for the two other installed
harnesses plus opencode. Live spikes ran on this box (Windows 11, codex-cli 0.130.0/npm →
0.137.0-shaped CLI confirmed at dispatch time, kimi 1.41.0; opencode NOT installed). Evidence files:
`1-projects/rbtv-sb-merge-refactor-core-build/build/warm-session-batch-0810/evidence/7641-*`
(prefix `7641-`, one file per harness per capability).

The three capabilities, restated from § *The spike that unblocked it* above: (1) `--input-format
stream-json` multi-turn stdin feeding with in-order mid-turn queueing, (2) exactly one `result`
event per fed turn, (3) `--session-id`/`--resume` continuity for the cold fallback.

### codex (codex-cli, this box)

| Capability | Verdict | Evidence |
|---|---|---|
| (1) stream-json stdin, mid-turn queueing | **FAIL — no mechanism** | `codex exec --help` (`7641-codex-exec-help.txt`) has NO `--input-format` flag at all; the only prompt paths are the positional `PROMPT` arg or an opaque stdin block appended verbatim to it — not a structured per-turn feed. `codex exec-server` (`codex exec-server --help`, `7641-codex-exec-server-help.txt`) is marked **[EXPERIMENTAL]**, a ws/stdio transport with no documented per-turn JSON schema — using it would be brute-forcing an undocumented wire protocol, which the spike's own instruction rules out. No live turn-feed test was run because there is nothing to feed. |
| (2) one `result` event per fed turn | **NOT-APPLICABLE** | Depends on capability (1)'s prerequisite — a persistent multi-turn process — which does not exist for codex; each `codex exec` invocation is a fresh one-shot process by construction, so "events per fed turn" has no substrate to measure against this harness. |
| (3) session-id / resume continuity | **Mechanism exists, NOT LIVE-VERIFIED (auth-blocked)** | `codex exec resume <SESSION_ID>` is documented (`codex --help` → `7641-codex-toplevel-help.txt`; `codex exec resume --help` → `7641-codex-exec-resume-help.txt`). A live two-turn resume probe (`codex exec --json … "Reply with exactly: OK"`) could not run: `codex login status` reports "Logged in using ChatGPT," yet every live call 401s with `Your access token could not be refreshed because your refresh token was already used` (`7641-codex-turn1-stdout.jsonl`, `7641-codex-turn1-stderr.txt`, exit 1, reproduced twice). Re-login is interactive/owner-only (manual: "USER-EXECUTED-ONLY; never automate the browser sign-in") — outside this dispatch's authority. |

**codex conclusion: stays cold-path.** Capability (1) is a measured FAIL by absence — sufficient on
its own per the eligibility gate — independent of the auth blocker on (3).

### kimi (kimi-code-cli, this box)

| Capability | Verdict | Evidence |
|---|---|---|
| (1) stream-json stdin, mid-turn queueing | **FAIL — live-verified 2026-08-10 on the ignite VPS (authenticated): mechanism-NAME match, wire-shape mismatch** | The Windows spike below stalled on a 401; the re-spike ran on the VPS where kimi IS authenticated (baseline `kimi --quiet --prompt` replies correctly). A claude-shaped `{"type":"user","message":{"role":"user","content":[...]}}` JSONL line over `--input-format stream-json` is **silently rejected by kimi's parser** — `kimi.log`: `WARNING _read_next_command:474 - Ignoring invalid user message`. Zero stdout, exit 0: the flag names mirror claude's byte-for-byte, but the wire envelope is incompatible, and the rejection is invisible from the outside. Evidence: `7641-vps-kimi-single-turn-stdout.jsonl` (empty), `7641-vps-kimi-log-rejection-evidence.txt`, synthesis `7641-vps-kimi-respike-summary.md`. (Earlier Windows measurement, kept for the record: the same probe shape produced zero stdout/exit 0 under a 401 — `7641-kimi-cap1-2-stdout.jsonl`, `7641-kimi-cap1-2-meta.txt` — an ambiguity the authenticated re-run has now settled as a genuine shape rejection.) |
| (2) one `result` event per fed turn | **MOOT** | No turn was ever accepted by kimi's stream-json parser (capability (1) FAIL), so there is no event cardinality to count. |
| (3) session-id / resume continuity | **PASS — live-verified 2026-08-10 on the ignite VPS** | `kimi --quiet --prompt` prints a resumable session id; `kimi --resume <id> --prompt` correctly recalls prior-turn content (start → store a secret → resume by printed id → recall). Evidence: `7641-vps-kimi-resume-continuity.txt`. |

**kimi conclusion: does NOT qualify — measured, not inferred.** The eligibility gate needs all
three capabilities; capability (1) is a live-verified FAIL on an authenticated box, and it fails in
the worst possible shape — a silent parse rejection (zero stdout, exit 0) behind flag names
identical to claude's, so nothing distinguishes "fed and thinking" from "fed and discarded" at the
transport level. No adapter is warranted on kimi's current wire protocol; a future kimi release
accepting a documented stream-json input envelope would reopen the question (re-measure — never
assume from flag names, which is exactly the trap this measurement closed).

### opencode

| Capability | Verdict | Evidence |
|---|---|---|
| (1) stream-json stdin, mid-turn queueing | **FAIL — no mechanism** | `where opencode` finds no binary on this box (`7641-opencode-absence.txt`) — no `--help` to check directly. Falling back to the opencode model package's own manual (`orchestration/models/opencode/manual.md`, `7641-opencode-manual-excerpt.txt`): "`opencode run` executes one headless turn (or resumes a session)... There is no separate print/quiet flag — `run` IS the headless mode" (line 153). The only structured-JSON option documented is `--format json` for OUTPUT events (line 179) — no `--input-format`/stream-json INPUT mechanism appears anywhere in the 44 KB manual. |
| (2) one `result` event per fed turn | **NOT-APPLICABLE** | Same reasoning as codex — no persistent multi-turn process in the documented invocation shape. |
| (3) session-id / resume continuity | **Mechanism documented, NOT-MEASURABLE-ON-THIS-BOX** | `opencode run -s <SESSION_ID>` (resume by id) and `opencode run -c` (resume cwd's last session, "POC-proven two-turn memory, 2026-07-06") are both documented (manual lines 205–213) — but cannot be live-exercised: the CLI is not installed here. |

Per the run's scope ruling, the `i-opencode-profile-broken` issue named in the dispatch was checked
at `.rbtv/goals/_channel-master/issues.md`: it is **absent** from that ledger as of this read — only
`i-cold-contact-latency` remains open there. Cross-referencing `decisions.md#d-async-jobs-self-report-and-reply-contract`
and `build/chat-bridge-feedback-and-reply-contract.md` (both in the core-build project root) shows
the row was **resolved and deleted the same day** (2026-08-10, WP-A/B/C): it was a reply-contract /
fence-conformance defect ("opencode: first bare turn ignores the fence... rides the revive path"),
unrelated to stdin/stream-json/session mechanics — it does not change either verdict above. Full
citation trail: `7641-opencode-issue-resolved.txt`.

**opencode conclusion: stays cold-path, ineligible** — documented rather than guessed, per the run's
scope ruling. Capability (1) fails by absence in its own model-package docs regardless of
installation state; installing opencode on this box would not change that verdict without a
harness-level stdin-feeding mechanism appearing in a future opencode release.

### Net effect on eligibility (§ *On this deployment, nothing is eligible yet*, above)

No new adapter work is warranted by this measurement: codex and opencode both fail capability (1)
by documented absence, and kimi fails it by a live-verified wire-shape rejection (re-spiked
authenticated on the VPS, 2026-08-10 — see the settled table above). All three non-claude
harnesses are now MEASURED ineligible, not merely unmeasured. The `master profile is not claude`
blocker in the table above is therefore not resolvable by switching harness today — a claude
profile remains the only path to an eligible master until a harness ships a compatible (or
adaptable) stream-json input mechanism.

## Deploy policy (owner-ruled 2026-08-10)

Implementation agents restart the ignite daemon and verify end-to-end (real Slack round-trip)
after each phase. VPS runbook: `1-projects/rbtv-sb-merge-refactor/build/ignite-vps.md`.
Defaults confirmed: doc home `ignite/bridges/chat/live-session-design.md`, idle window 10 min
(`live_session_idle_ms: 600000`), warm-session cap 4 LRU (`live_session_max: 4`).

## Risks & mitigations

- ~~**Stream-json stdin mid-turn semantics unverified**~~ → **RESOLVED by measurement 2026-08-10**
  (§ *The spike that unblocked it*): the CLI queues a mid-turn message. The manager-side send
  queue was not built; only a responder queue exists.
- **Stale in-session state** (files/rulings changed under a warm session) → reaper on profile
  apply; seats' own read-before-write discipline unchanged; 10-min ceiling bounds staleness.
- **Memory** (240–600MB per warm process, 8GB box) → `live_session_max` LRU cap + reaper.
- **Live daemon** — code changes activate only on daemon restart; deploy/restart policy is an
  owner ruling (open question at review).

## Implementation phases (Opus subagents)

1. Ferry file-watch (bus-ferry.js — small, independent, ships alone).
2. Async outcome post + wake flag (dispatch/settle path).
3. ~~Live session manager + bridge/ticker hook + streamed replies (the core).~~ **DONE 2026-08-10.**
4. ~~Config surface, probes/self-checks, docs.~~ **DONE 2026-08-10** — with the two open owner
   decisions in § *On this deployment, nothing is eligible yet*, and the warm-latency figure still
   awaiting a real owner round-trip (probe-measured warm turn on `claude-haiku`: **3.8s**, against
   4.6s for the same turn including the live launch).
