# 20260902-i-refuse-an-overlapping-live-fee — refuse an overlapping live-feed request

kind: issue
component: supervisor
date: 2026-09-02
commit: 1e01b6c6dfe1b0089ac6d5c218e146d5c04a8545
deployed: yes
pin: ignite/chat/probes/probe-chat-live-session.js
components: chat

## Observed
Owner saw two different-worded answers to one Slack question on goal `transcript-summarizer-build`
(`slack-duplicate-replies.md`). Investigating the 18:53:50Z pair specifically (§4/§9-5 of that
handoff, deployed code at commit `fa99f199`, the commit live on the daemon at that exact time —
confirmed via `git -C ~/.local/state/rbtv-deploy reflog` and the daemon's own boot marker
`.rbtv/runtime/daemon-code.json`, both timestamped 13:48:03Z): production `journalctl` logs show
message B's own `feed()` call landing at 18:49:54, 14 seconds into a 90-second turn already running
from message A. The CLI produced exactly ONE `result` event (`queued_turn_count:0`, matching the
session's `"turns":4` in its ended-log — one fewer than the 5 that would exist had A and B each got
a discrete completion), which resolved the FIRST waiter. The SECOND waiter sat unresolved until its
own 300-second turn-timeout fired at 18:54:54 — exactly 300000ms after its own `feed()` call,
reproducible only by an in-process `setTimeout`, not any network event — 64 seconds AFTER the
bridge's shorter 240-second feed ceiling had already given up and manufactured a cold-path retry
that duplicated the already-answered reply.

## Mechanism
`ignite/supervisor/spawn/live-sessions.js#feed()` (at the deployed commit, lines 502-542) had no
busy check: finding a session already mid-turn, it pushed a second waiter onto `s.waiting` and
wrote the second message into the child process's stdin anyway, betting that the CLI would produce
a SECOND, separately-matchable `result` event for it. The module's own comment documented this as
an established fact from a 2026-08-10 spike (a short message fed 3.0s into a 15.8s turn WAS
answered separately, in order) — but that spike measured one narrow case, not a guaranteed CLI
contract, and production fell through the assumption on a longer, 90-second turn: the CLI merged
both owner messages into one completion, and `onStdout`'s FIFO `shift()` had only one `result` to
resolve one waiter, orphaning the second.

## Attempts
First attempt held — checked `slack-duplicate-replies.md` (the investigation handoff this fix
executes against) and this component's `_issues.md`/`_creations.md` for a prior fix of this
specific pair; none found. A related but DIFFERENT contributor to the same owner-visible duplicate
defect (a mismatched feed-timeout-vs-turn-timeout constant, plus a missing idempotency key on
`chat-bridge.js#deliverToOwner`) was fixed separately in commit `10ad7956`
(`chat/20260831-i-duplicate-replies-timeout-inve.md`) — that fix addresses the EARLIER 18:39 pair
under "Reading B" (a genuine connection reset); this fix addresses the 18:53:50Z pair under
"Reading A" (no connection reset — a mid-turn overlap with no busy gate). Both readings are real,
in different pairs, for different mechanisms; neither fix supersedes the other.

## Fix
Root cause is born at `ignite/supervisor/spawn/live-sessions.js`, inside `feed()`, immediately
before the `if (!s) {...}` launch branch — the point where an ALREADY-EXISTING session is handed a
second concurrent write with no gate. `feed()` now checks `s && s.waiting.length > 0` and refuses
the overlapping write with `{ok:false, reason:'busy-mid-turn'}` instead of racing a second waiter
against the CLI. This was chosen over widening the waiter queue or trying to detect which `result`
belongs to which fed message, because EVERY feed refusal already falls through to the cold path by
design (`chat/live-sessions.js`'s own header) — a `busy` refusal takes that same path immediately
instead of after minutes of silence, costing the caller nothing it cannot already handle.
`probe-chat-live-session.js` arm 2 was updated to assert the new contract: an overlapping feed must
be refused busy, and a sequential follow-up after resolution still works, same warm process, in
order.

## Consequences
`s.waiting` is no longer trusted as a multi-entry FIFO in practice (the busy check caps it at one
un-answered waiter before a second write is even attempted) — the field itself and its FIFO
`shift()` logic in `onStdout` are unchanged, only newly unreachable beyond length 1. No `lane-watch.js`
change was needed (Reading B, the earlier pair's connection-reset cause, is not implicated in this
pair). A real, PRE-EXISTING crash was found but not fixed: `feed()`'s
`s.child.stdin.write(line)` has no `'error'` listener on the child's stdin stream, so an EPIPE
(write to an already-dead child) is an unhandled `'error'` event that crashes the daemon process —
reproduces on pristine, un-fixed HEAD in this sandbox on the very first real live-session launch,
root cause not diagnosed (suspected sandbox/bwrap-cage specific, since `systemd-run --user` works
standalone); this blocked `probe-chat-live-session.js` from completing live in-sandbox, so the fix
was verified against a mocked-child harness instead (see Verification).

## Verification
Verified with `child_process.spawn` stubbed and everything else real (config load, cast resolution,
cage composition) since the sandbox's real launch path throws the pre-existing EPIPE on first feed:
fixed code — turn A settles in 344ms via the emitted result, turn B settles in 52ms with
`{"ok":false,"reason":"busy-mid-turn"}`; the same scenario against the reverted code — turn A
settles in 345ms (unaffected), turn B settles in 1502ms (== `turnTimeoutMs`) with
`{"ok":false,"reason":"turn-timeout","unanswered":true}` — reproducing the exact incident shape
(an orphaned waiter resolved only by its own timeout, long after the genuine answer). Suite run:
`node ignite/deploy/probe-suite.js --dir chat/probes` → `discovered:29 attempted:29 passed:25
failed:4`; of the 4 reds, `probe-chat-live-session.js` fails on the pre-existing sandbox EPIPE
(confirmed reproducing on pristine, un-edited HEAD), and the other 3
(`probe-chat-boundary.js`, `probe-chat-bus-ferry.js`, `probe-owner-ask-hold.js`) do not reference
`live-sessions.js` at all — explained by an unrelated parallel session's concurrent uncommitted
edit to `bus-ferry.js`, correctly excluded from this commit. Committed
`1e01b6c6dfe1b0089ac6d5c218e146d5c04a8545`, deployed on branch `ignite/core-daemon` (live tree
`e8524c31` carries this commit); a live-verify (two owner Slack messages seconds apart, confirming
exactly one reply and a `"live session busy — refusing the overlapping feed…"` journal line instead
of a 300s-later duplicate) is still owed as of this filing.

## ATTENTION
1. `s.waiting.length > 0` is the ENTIRE busy gate — a session is considered "mid-turn" purely by
   having one unresolved waiter. Do not reintroduce a code path that pushes a second waiter without
   going through `feed()`'s busy check first; that reopens exactly this race.
2. The pre-existing EPIPE crash on `s.child.stdin.write(line)` (no `'error'` listener on the
   child's stdin) is UNFIXED — it blocks `probe-chat-live-session.js` from completing in this
   sandbox and will crash the real daemon process on any write to an already-dead child. Whoever
   picks this up should add the listener and re-run the probe live, not just against the mocked
   harness this fix used.
3. This fix addresses ONLY the mid-turn-overlap mechanism (Reading A). The earlier-pair
   connection-reset mechanism (Reading B) is a SEPARATE, already-shipped fix
   (`10ad7956`, `chat/20260831-i-duplicate-replies-timeout-inve.md`) — do not treat either fix as
   redundant with, or a superset of, the other; both readings are real for different pairs.
- `s.waiting.length > 0` is the busy gate
- EPIPE crash on stdin.write UNFIXED
- fixes Reading A only (10ad7956 = Reading B)
