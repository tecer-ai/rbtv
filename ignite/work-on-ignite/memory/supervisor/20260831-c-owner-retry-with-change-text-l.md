# 20260831-c-owner-retry-with-change-text-l — Owner retry-with-change text lands in the next boot prompt

kind: creation
component: supervisor
date: 2026-08-31
commit: bff066ac
deployed: no
pin: ignite/supervisor/retry-correction.selftest.js
components: chat

## Motivation
`d-recovery-correction-lands-in-instructions` (2026-08-31): the owner's free text after a Slack
`retry-with-change` reply on a stuck lane must land in the RESTARTED seat's own starting
instructions, in a section marked as an owner correction, so the seat cannot begin work without
having read it. Posting it as a coordination-log message was the owner's first pick and was
reversed on the race argument — a restarted seat can act before the message lands. Sibling seat
`rr-lane-rearm` built the lane-scoped re-arm act that UNBLOCKS the seat (clears the counter,
arms the ending) but does NOT relaunch it — the actual relaunch is the supervisor's own next
reconcile pass. This creation is the bridge across that gap.

## Design
The composition site is `launch.py#boot_prompt`, NOT `ignite/planning/materialize-seats.py` (this
seat's assigned custody row) — a relaunch never re-runs materialize; `boot_prompt` composes a
fresh prompt on EVERY relaunch of EVERY seat (confirmed via its own docstrings and
`supervisor/seeding.js#seatBootPrompt`'s subprocess call into `coord.py boot-prompt`).
`boot_prompt` already carried a byte-for-byte precedent for this exact shape: a routed-FAIL
payload (`attest.py`'s `write_route_payload`/`read_route_payload`, `ROUTE_PAYLOAD_DIR`) written
to `{goalFolder}/coordination/route-payloads/{seat}.md` and folded into the prompt as an
ADDITION, never a substitution. Extended those two functions with a `kind` parameter
(`"route"` default, unchanged for every existing caller; `"correction"` new) rather than
copy-pasting a second pair, so an owner correction and an unrelated routed FAIL landing for the
same seat before its next boot cannot silently overwrite each other (`write_text` replaces, it
does not merge) — each channel gets its own directory.

Considered and rejected: reusing the ALREADY-WIRED `ask-thread.js#persistReply`/`.reply.txt`
mechanism (`{goalFolder}/coordination/asks/{askId}.reply.txt}`, written unconditionally for every
released ask including the recovery family, before this creation existed). Two reasons it does
not fit: (1) it is keyed by `askId` (the Slack thread), not by `seat` — `boot_prompt` only knows
`w["agent"]`, so using it would need a NEW seat→askId resolution against the ending store's
`open_asks` table, which `dl-abandoned-outcome` was actively editing at build time (state-store is
walled off, not a file to add a read dependency on lightly); (2) it captures the owner's RAW
reply verbatim, including the leading `retry-with-change` token — the already-parsed `comments`
field (`reply-grammar.js`'s output, what `recovery-thread.js#dispatch` already receives) is the
clean text and is what the retryWithChange port already carries in memory. The route-payload
shape was the closer existing means: `boot_prompt` already reads that exact file shape, seat-keyed,
no store coupling needed.

## How it works
New `ignite/supervisor/retry-correction.js` exports `writeRetryCorrection({ goalFolder, seat,
comments })` — the ONE handle `rr-port-wire`'s `retryWithChange` port implementation calls. Empty,
absent, or whitespace-only `comments` is a clean no-op (`{ok:true, written:false}`, nothing
touches disk). Otherwise it writes a marked `## OWNER CORRECTION — retry-with-change (<ISO
timestamp>)` block to `{goalFolder}/coordination/correction-payloads/{seat}.md` (mkdir -p first).
`seat` is checked against a safe-filename pattern (mirrors `runtime/gateway/parse.js`'s
`BUS_NAME_RE`) before it is used as a path segment — defense in depth, the same posture
`coord.py cmd_route_fail` already takes on its own seat-route cells; `comments` is only ever file
CONTENT, never a path segment. `launch.py#boot_prompt` reads it back via
`attest.read_route_payload(base, seat, kind="correction")` and, when present, folds in a
`⚠ OWNER CORRECTION` block right after the existing `⚠ THIS SITTING WAS ROUTED TO YOU` block —
same position, own heading, so the two reasons for a relaunch (a routed FAIL vs an owner
correction) are never conflated.

## Consequences
Nothing deleted or replaced. `write_route_payload`/`read_route_payload`/`route_payload_path` in
`attest.py` gained a `kind` parameter with a default that keeps `cmd_route_fail` and the existing
`boot_prompt` routed-FAIL read byte-identical. Custody note: `attest.py` and `launch.py` are NOT
this seat's assigned custody row (`materialize-seats.py`) — a real mismatch, disclosed to the
orchestrator, since the actual composition site lives elsewhere. Every named holder of the
`launch.py`+`protocol.md` and `attest.py` custody rows in `redesign-continue-1`'s `seats.md` was
already `done` and the working tree was clean on both files before this edit.

## Verification
Red-first at the integration level: a standalone fixture script drove `launch.boot_prompt` with a
correction payload file present, against a `git worktree add <tmp> HEAD` copy of the pre-fix tree
(commit `72f139dc`) — RED, exit 1, "OWNER CORRECTION" absent even with the payload on disk — then
against the live post-fix tree — GREEN, exit 0, marker and text both present. The empty-comments
arm was proven in the SAME script: with no payload file written, the prompt is byte-identical
before and after (no marker, no empty section). `ignite/supervisor/retry-correction.js`'s own
contract (write/no-op/overwrite/two-independent-seats/unsafe-seat-name-refused) is proven by its
sibling `retry-correction.selftest.js`, `node --test` — 7/7 pass. `python3 coord.py selftest` from
inside `ignite/coord/`: 1027 ok, the SAME 24 pre-existing named failures documented by
`selftest-aborts`/`crash-loop-clear` earlier in this plan (7.555/7.278/D35/paused-gate class,
already a known `judge-final` HOLD reason), zero new failures. Not deployed — `ignite/chat/` (the
`retryWithChange` port itself) is pinned to the deploy worktree per R10; this creation lands the
supervisor-side half only, inert until `rr-port-wire` wires the caller and a deploy window runs.

## ATTENTION
1. The JS `CORRECTION_PAYLOAD_DIR = 'correction-payloads'` literal in `retry-correction.js` and
   Python's `attest.CORRECTION_PAYLOAD_DIR` must stay byte-identical by hand — nothing shares
   constants across that language boundary, and a drift here is a silent no-op (the writer would
   write somewhere `boot_prompt` never reads).
2. Like the pre-existing `route-payloads` channel it mirrors, a written correction payload is
   NEVER cleared after `boot_prompt` reads it — it persists until a NEW correction overwrites it,
   so a seat relaunched again later for an unrelated reason will see the same correction again.
   This matches established behaviour (not invented here) and was a deliberate choice not to
   diverge from the route-payload precedent; flagged, not fixed, since fixing it would touch the
   shared `read_route_payload` reader's semantics for BOTH channels.
3. `boot_prompt`'s `⚠ OWNER CORRECTION` block fires on EVERY lane (console and daemon) and on
   EVERY seat — there is no `w["agent"] == "goal-master"`-style narrowing like `unanswered_ask_block`
   carries, because a `retry-with-change` reply is inherently seat-scoped already (the recovery
   ask's `seat` field), so no further scoping is needed or was added.
4. `rr-port-wire` must pass `goalFolder` as the coord PACKAGE directory (what `coord.base_dir`
   resolves as `package_dir(args)/"coordination"`'s parent) — NOT the `coordination/` subfolder
   itself; `writeRetryCorrection` appends `coordination/correction-payloads/` itself.
