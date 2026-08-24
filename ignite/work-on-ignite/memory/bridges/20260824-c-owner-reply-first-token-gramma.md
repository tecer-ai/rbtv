# 20260824-c-owner-reply-first-token-gramma — owner-reply first-token grammar

kind: creation
component: bridges
date: 2026-08-24
commit: d17d63c13771e728c1c1c5a313703b69b6d38f61
deployed: no
pin: bridges/chat/probes/probe-chat-reply-grammar.js

## Motivation
Owner replies had no first-token grammar: unrecognized text stayed silent until the next digest [F-owner-ux-2], there was no outcome vocabulary [F-owner-ux-3], and approval vs ordinary threads would otherwise grow two parsers. `spec-owner-io` §4 pins one parser for both.

## Design
A pure function `parseReply(text, opts)` in the existing chat-bridge folder (`ignite/bridges/chat/`, not a new `ignite/chat/` — that home is not on disk yet and inventing it would collide with impl-structure). Success returns canonical `outcome`, `comments`, `family`, plus dispatch metadata (`findings` for `retry with:` / `reject-and-retry` [T3-R21], `goal` for pause/resume). Failure returns which verbatim §4.5 NACK applies (`ask` vs `mechanical`). Rejected: wiring into `chat-bridge.js` / `reply-leg.js` / `ask-store.js` (other seats' custody); posting the NACK from this module; guessing `ok`/`lgtm`/`yes`/`reject`/`retry` as approve.

## How it works
Callers pass raw reply text. Optional `opts.channelGoal` makes a bare `pause`/`resume` target that goal; optional `opts.liveGoals` NACKs a slug that hits zero or several live names. Tokenizer: skip empty leading lines, longest-match first, case-insensitive, hyphen/space equivalent on multi-word tokens, trailing `.` `)` `:` only on letter tokens a–g. The module does not post, open Slack, or touch a store.

## Consequences
Nothing replaced. No caller is wired. New `module.md` and `exposure.csv` under `bridges/chat/` were created from empty with only this module's rows — impl-structure may need to merge them when it conforms the folder.

## Verification
`node --check ignite/bridges/chat/reply-grammar.js` exit 0. `node ignite/bridges/chat/probes/probe-chat-reply-grammar.js` PASS, 153 checks. `node ignite/deploy/probe-suite.js --dir bridges/chat/probes` GREEN 21/21 (20 baseline chat probes + this one). Not deployed (`deployed: no`).

## ATTENTION
- Owner-reply `pause {goal}` is not `lane-watch.laneIsPaused` (the `execution-lane` first token). A third pause grammar here would split the lane reader.
- The module never posts the NACK. A caller that parses and then stays silent reopens [F-owner-ux-2].
- Bare `pause`/`resume` is mechanical NACK unless the caller passes `channelGoal`. Forgetting that in a goal channel looks like a parser bug; it is a missing opt.
- Do not edit `chat-bridge.js`, `bus-ferry.js`, `reply-leg.js`, or `ask-store.js` to wire this — those files are other seats' custody.
- Owner-reply pause {goal} is not lane-watch.laneIsPaused
- Module never posts the NACK; silence reopens F-owner-ux-2
- Bare pause/resume NACKs unless caller passes channelGoal
- Do not wire via chat-bridge.js / reply-leg.js / ask-store.js
