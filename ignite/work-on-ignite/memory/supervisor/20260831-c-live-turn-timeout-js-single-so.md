# 20260831-c-live-turn-timeout-js-single-so — live-turn-timeout.js: single-sourced daemon turn ceiling

kind: creation
component: supervisor
date: 2026-08-31
commit: 10ad7956
deployed: no
components: chat

## Motivation
The daemon's live-session turn timeout (`supervisor/spawn/live-sessions.js`) and the bridge's live-feed HTTP ceiling (`chat/live-sessions.js`) must satisfy bridge-ceiling > daemon-timeout, or the bridge abandons a turn the daemon still owns. They were two independent literal constants (240000 vs 300000) in two files, in two processes — nothing enforced the relationship, and it inverted in production (`slack-duplicate-replies.md`).

## Design
A tiny, dependency-free leaf module, `ignite/supervisor/spawn/live-turn-timeout.js`, exporting `DEFAULT_TURN_TIMEOUT_MS` as the single source. `supervisor/spawn/live-sessions.js` imports it (cheap — it was already the daemon-side file). `chat/live-sessions.js` (the BRIDGE process, which must hold no spawn capability per `probe-chat-boundary`) also imports it and derives `DEFAULT_FEED_TIMEOUT_MS = DEFAULT_TURN_TIMEOUT_MS + 30000`. Rejected: requiring the whole `supervisor/spawn/live-sessions.js` module from the bridge for the constant — it would pull `child_process`/`harness-config`/`bwrap` into the bridge process, against the architecture's explicit "the manager cannot live here" invariant, even though the static `probe-chat-boundary` grep would not have caught the textual pattern.

## How it works
`require('../supervisor/spawn/live-turn-timeout')` from `chat/live-sessions.js`; `require('./live-turn-timeout')` from `supervisor/spawn/live-sessions.js`. Changing the daemon's turn-timeout now means editing exactly one file — both call sites move together automatically.

## Consequences
Replaced two independent literals with one derivation. No behavior change at the current default (240000 → 330000 for the bridge ceiling is the ONLY numeric change, deliberately widening the margin from -60000 [inverted] to +30000 [correct]).

## Verification
`node -e` sanity check confirming both modules resolve to consistent values; a live edit-only-the-leaf-file test proving both derived values move together (the observation that discriminates "a real derivation" from "two constants that happen to agree today"). Not yet deployed.

## ATTENTION
1. `DEFAULT_TURN_TIMEOUT_MS` is exported from `supervisor/spawn/live-sessions.js` too (re-exported, not redefined) for probes/callers that still import it from there — do not reintroduce a literal at either site.
- re-exported from supervisor/spawn/live-sessions.js too — never reintroduce a literal at either site
