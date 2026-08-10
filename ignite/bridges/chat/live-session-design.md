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

### 1. Live session manager (`ignite/server/spawn/live-sessions.js`, new)

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

### 4. Dispatch hook for warm feeds — RULED (owner, 2026-08-10)

**Direct feed + fire-and-forget accounting event.** The bridge hands a warm-session message
straight to the live process (~0.1s); the manager reports each fed turn to the gateway so
acct/session records stay whole. Admission checks (allowlist, caps) run bridge-side as today.
Cold spawns keep the queue path unchanged. (Queue-path alternative rejected for its 0.3–1.9s
nudge+tick cost — warm total would sometimes exceed the 3s target.)

## Expected budgets after

| Path | Today | After |
|---|---|---|
| Warm direct thread | ~12s | **~1.5–2.5s** (feed ~0.1 + inference 1–2 + post 0.3) |
| Cold (first contact / after idle) | ~12s | ~8–12s unchanged (resume spawn); receipt emoji already exists, no ack work needed |
| Ferried bus row → Slack | 0–15s poll | **~0.3s** (watch debounce + pass) |
| Async job outcome → owner | never (manual ask) | ~0.5s after settle |

## Deploy policy (owner-ruled 2026-08-10)

Implementation agents restart the ignite daemon and verify end-to-end (real Slack round-trip)
after each phase. VPS runbook: `1-projects/rbtv-sb-merge-refactor/build/ignite-vps.md`.
Defaults confirmed: doc home `ignite/bridges/chat/live-session-design.md`, idle window 10 min
(`live_session_idle_ms: 600000`), warm-session cap 4 LRU (`live_session_max: 4`).

## Risks & mitigations

- **Stream-json stdin mid-turn semantics unverified** → first implementation task is a 10-minute
  spike against claude v2.1.226; manager-side queue is the fallback design.
- **Stale in-session state** (files/rulings changed under a warm session) → reaper on profile
  apply; seats' own read-before-write discipline unchanged; 10-min ceiling bounds staleness.
- **Memory** (240–600MB per warm process, 8GB box) → `live_session_max` LRU cap + reaper.
- **Live daemon** — code changes activate only on daemon restart; deploy/restart policy is an
  owner ruling (open question at review).

## Implementation phases (Opus subagents)

1. Ferry file-watch (bus-ferry.js — small, independent, ships alone).
2. Async outcome post + wake flag (dispatch/settle path).
3. Live session manager + bridge/ticker hook + streamed replies (the core).
4. Config surface, probes/self-checks, docs (README + this design doc finalized in-repo).
