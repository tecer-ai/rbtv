# 20260827-c-the-approval-ask-rides-the-bus — the approval ask rides the bus row: send --approve-commit

kind: creation
component: chat
date: 2026-08-27
commit: 8f299bc6
deployed: no
pin: ignite/chat/probes/probe-chat-bus-ferry.js
components: coord,meta-planning

## Motivation
The plan-console workflow's last hop had no poster. `plan-verifier` composed
`planning/approval-digest.md` and `planning/approve-package.json` and stopped — three
texts promised "a later Slack seat posts it" and that seat was never built. Worse, the
obvious repair does not work: no goal-side send could mint an APPROVAL thread. The ferry
called `postAsk` with no `kind`, so `chat-bridge.js` defaulted `kind: 'ordinary'`, and
`approve` starts execution ONLY in a thread whose map entry says `kind === 'approval'`.
The owner would have received the digest and his `approve` would have started nothing —
delivered to the seat as an outcome word. Everything past that door already existed
(dispatch → release → `start-execution.js` → `approve-package.json`, owner ruling
2026-08-24). Ruled option (a), 2026-08-27: carry the approval on the bus row.

## Design
ONE new optional header key on the coordination row, `approve-commit: <sha>`, written by
a new `coordinate send --approve-commit`. The message-type vocabulary stays closed at
eight: a ninth type would have rippled through the enum, `TYPE_COLOR`, argparse, the
gateway skip-list and the store CHECK for a distinction one key already makes, and the
row IS a `note` to `owner` — the same transport the D13 replan notice rides. The
AUTHORITY lands at `coord.py cmd_send`, the one deliberate exception to the choke-point
rule that the escalation identity gate already takes and for its reason: `resolve_agent`
runs there and `_append_message_unlocked` has no identity, so a check at the writer would
test a self-asserted sender against itself. Rejected: a body sigil like `chat-thread`'s
bracketed fallback (text an agent types into a digest would open execution); a new
gateway intent posting on the verifier's ending (option (b) — needs an owner ruling);
composing the approval body in `postOwnerAsk` (the probe already passes a pre-composed
body, so the caller composes, as every existing caller does).

## How it works
`cli_main.py`'s `send` gains `--approve-commit SHA`. `cmd_send` refuses it unless all
three hold, each with its own message and no `--force`: the row is a `--type note` to
`owner`; the sender's `seats/<self>/seat.md` says `human-interactive:`
(`seat_is_human_interactive`, the same descriptor read the ferry's ask door uses); and
`<goal>/planning/approve-package.json` exists with `bound_commit` equal to the flag
(`start-execution.js` reads that package and answers `no-approve-package` in-thread
without it; an approval binds at a commit [T5-R5]). `_append_message_unlocked` emits
`| approve-commit: <sha>` between `deliver:` and `why:`, and `addressing.py#MSG_HEADER`
gains the matching group in the same position. `bus-ferry.js#parseHeader` reads
`hdrApproveCommit`; `rowApproveCommit` validates `^[0-9a-f]{7,64}$` and returns null
otherwise; the `postAsk` call passes `kind: 'approval'` + `commitId` and composes the
body with `approval-thread.js#composeApprovalBody({goalName: goalId, digest: row.body,
commitId})`. `chat-bridge.js#postOwnerAsk` already accepted both arguments and records
them in `askThreads`, which is what the `isApproval` fork reads.

## Consequences
`MSG_HEADER` HAD to change in the same act: with no group of its own the new key is not
refused, it is swallowed by the trailing `ts` group (`.+`), so every reader would have
got a timestamp reading `approve-commit: <sha> | 2026-08-27 18:37`. The `meta/planning`
texts are corrected in the same commit — `tasks/verify-plan.md` gains a Send clause and
loses "do not post"; `prompts/verifier.md`, `seats.csv`, `workflows/plan-console/
plan-console.csv` and `workflow.md` stop promising a later Slack seat. The digest no
longer lists the owner's reply tokens at all: `composeApprovalBody` publishes
`APPROVAL_TOKEN_LINE` from the parser's own vocabulary, and the second source had
already drifted — `verify-plan.md` and `verifier.md` asked for `reject-close` /
`reject-pause` / `reject-retry`, none of which `approval-thread.js` accepts, so every
rejection the owner typed would have come back a NACK. NOT deployed: the bridge
(`rbtv-chat-bridge`) must restart for the ferry change. Already-materialized seat
descriptors do NOT pick up the new task text — `seat.md` has one writer,
`planning/materialize-seats.py`, invoked by the creation route or `--seat <name>
--refresh`, and nothing in the daemon's spawn path re-renders it.

## Verification
Offline, in a scratch workspace under `/tmp` with its own `goals` parent, never the live
goals root. `coordinate send owner --file <digest> --type note --approve-commit <sha>
--as plan-verifier` → `sent message #1 (plan-verifier -> owner, type: note,
approve-commit: 348ebf7e…)`, exit 0, and the row read back through the REAL
`load_messages` gives `approve_commit: 348ebf7e…` with `ts: '2026-08-27 18:37'` intact.
Each refusal exercised live on the same fixture: non-`human-interactive` sender, absent
approve-package, mismatched sha, non-`owner` recipient. Durable arms:
`ignite/coord/coord_selftest.py` W8 arm 3b (all five refusals + the accepted send + the
header key + the ts intact + an ordinary-note control) — `selftest: PASS (0 failure(s))`,
RED-CONFIRMED by deleting the `human-interactive` condition. `ignite/chat/probes/
probe-chat-bus-ferry.js` arm 11 (kind+commit reach `postOwnerAsk`, the §3 body shape, an
ordinary-row control, a malformed-sha fail-closed arm) — `PROBE probe-chat-bus-ferry
EXIT=0 CHECKS=49` (was 45), RED-CONFIRMED by removing the two-line pass-through. The
`approve`→`start-execution` leg is unchanged and already covered: `probe-chat-approval`
`EXIT=0 CHECKS=24`. All 24 other `ignite/chat/probes/probe-*.js` green
(`probe-chat-boundary` is red BEFORE and AFTER — pre-existing `execFile` in
`bus-answer.js:55`, present at HEAD). Deployed: no.

## ATTENTION
- The `kind` on the thread map entry is what makes `approve` irreversible, NOT the word
  the owner types. A row that reaches the owner without it looks identical to him and
  starts nothing — which is exactly the state this fixes.
- An unknown key added to the bus header does not refuse the row: `MSG_HEADER`'s trailing
  `ts` group eats it. A new writer and that regex land in the same change or every reader
  goes quietly wrong.
- Never give this key a body-sigil fallback the way `chat-thread`/`deliver` have one.
  Those predate their header keys; this one does not, and a sigil would let digest text
  open execution.
- The authority check belongs at `cmd_send` and nowhere else. At the ferry it would be a
  second, weaker authority over the same door; at the writer it would test the sender's
  own claim against itself.
- Editing `meta/planning/tasks/*.md` does NOT reach a goal whose seats are already
  materialized. Re-render with `materialize-seats.py --seat <name> --refresh`, or the
  running seat reads yesterday's contract.
- an unknown bus header key is swallowed by the ts group, not refused
