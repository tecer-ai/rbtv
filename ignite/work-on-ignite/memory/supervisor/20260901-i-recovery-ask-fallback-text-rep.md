# 20260901-i-recovery-ask-fallback-text-rep — recovery ask fallback text replaced by the seat's own words

kind: issue
component: supervisor
date: 2026-09-01
commit: 45fa2c44
deployed: no
pin: ignite/supervisor/reconcile.selftest.js
components: chat

## Observed
The daemon's recovery ask, posted verbatim to the owner in `#system-channel`, read:
```
LANE: ignite-engine-planning / leader
driver: reconcile-respawn · reason: unread · attempts: 3
unread retried 3 times with the same refusal class
```
The owner's verdict (interview, 2026-09-01): "it did not ask no clear question, and it did not
give any actual context (what was the refusal, what is being asked me to do)". The text
`unread retried 3 times with the same refusal class` is not the seat's own words at all —
`inv-refusal-source` traced it to a hardcoded fallback string, byte-identical on repo HEAD and
deploy HEAD (`0363d55e`).

## Mechanism
`reconcile.js#countRetry` (line ~633, pre-fix) built the ask's `refusalText` as
`refusalText || \`${reason} retried ${attempts} times with the same refusal class\`` — the fallback
fires whenever the caller passes no real text, which was true for every call site: the main
counting call (class A `incomplete`, class B `unread`, `nonterm`) passed `action.error` (a launch
error, only for the launch-refused sub-case) or `null`; the room-rebuild call passed a system
status string. Neither call site ever read `seat_endings` — the table that DOES hold the seat's own
words (`diagnostic` + `evidence_pointer`, stamped `who_stamped: 'seat'` via `checkout` when the seat
declares itself unfinished) — before `exhaust()` re-stamped that same row with the system's own
`attempt-counter exhaustion` diagnostic and archived the seat's row into `seat_endings_log`. The
words existed on disk the whole time; nothing in this pipeline looked.

## Attempts
First attempt held — checked: `inv-refusal-source`'s report (this plan's own investigation seat,
2026-09-01) traced the exact origin and confirmed no earlier fix touched this fallback; no prior
memory entry (embed-search + grep floor over `component:supervisor`/`component:chat` `_issues.md`/
`_creations.md`) names `countRetry`, `recordGroupedAsk`, `listUnpostedLanes`, or `oneLinerOfLane`.

## Fix
`countRetry`'s TWO callers in `reconcile.js` (the main counting call, and the room-rebuild call) now
read the seat's own state BEFORE calling `countRetry`, per the design in `owner-ask-redesign.md`
§5.2(b): only `t.reason === 'incomplete'` reads `endingStore.getCurrentEnding({goal, seat})` — the
ONE driver whose current ending row is genuinely about THIS retry (a seat's own prior checkout
declaring itself unfinished, which is WHY `deriveOwed` classified it into class A at all); `unread`/
`nonterm` carry no such row structurally (a leader wake for other seats' rows, or unread mail nobody
spoke about) and are not looked up. When the row exists and `who_stamped === 'seat'`, its
`diagnostic`/`evidence_pointer` ride through as new `lastWords`/`evidencePointer` parameters —
replacing `refusalText` end to end (`countRetry` → `exhaust` → `recordGroupedAsk`), never a
synthesized fallback. `exhaust()`'s pre-existing `evidencePointer` param (the SYSTEM stamp's own
pointer, defaulting to the ask file) is untouched — the seat's transcript pointer rides a
differently-named param (`seatEvidencePointer`) to avoid colliding the two concepts.

Two OTHER callers of `recordGroupedAsk` sit outside this seat's custody (`reconcile.js#announceDisarm`,
the "no ending store" degenerate path; `relaunch-budget.js`'s leader-escalation ask) and still pass
their own synthesized/leader-authored `refusalText` — `recordGroupedAsk` keeps accepting it as a
backward-compatible fallback (`last_words: lastWords || refusalText || null`), so neither file needed
editing (`no-duplicate` rule 5: an explicit no-touch boundary is honoured by reusing the interface,
not routing around it).

The room-rebuild call site (line ~1381) is not a seat's own words either (there is no seat to speak
for a room-level failure) — it now passes its system text as `lastWords` directly (mechanical rename
from `refusalText`), so the information is not lost, just correctly labelled as system-authored
rather than seat-authored in the new template's "Its last words" line, which shows it as-is (no
special-casing needed: the template only checks whether ANY text is present, not who wrote it).

RED-FIRST PROOF (the design's own open question, `inv-refusal-source` #1): confirmed by code trace
that `launchSitting` (the relaunch attempt) never touches `seat_endings` — so `getCurrentEnding`
called just before `countRetry` still returns the seat's own row, not a stamp this same pass made.
Proven empirically in `reconcile.selftest.js`'s new red-first block: a fixture stamps the seat's own
`incomplete` ending (`diagnostic: 'context full'`, via the pre-existing `stampEndings` helper), N
passes drive the counter to exhaustion, and the resulting ask's lane carries `last_words: 'context
full'` — never the deleted fallback string.

## Consequences
`exhaustion.js`'s lane shape changed: `refusal_text` → `last_words` + `evidence_pointer` (the seat's
transcript, rendered vault-relative by a new `vaultRelativePointer` helper — Slack cannot link a VPS
absolute path) + `first_at`/`last_at` (from the attempt counter's own row) + `outcome` (this pass's
`action.kind`, `'enqueue'` or `'launch-refused'` — lets the composer distinguish "seat cannot be
started" from "seat keeps quitting"). `oneLinerOfLane` (the digest's one-liner for an UNPOSTED lane)
now reads `last_words` — its own behaviour (first non-blank line, ≤120 chars) is unchanged.

## Verification
`node ignite/supervisor/reconcile.selftest.js` — full suite green, exit 0, including the new
red-first block ("DoD 2 red-first: the exhaustion ask quotes the seat's OWN diagnostic, never the
deleted fallback"). `node ignite/supervisor/last-lane-ask.selftest.js` — green, exit 0 (unaffected
by this half of the change but re-run as a regression check since `exhaustion.js`'s exports are
shared). `node ignite/supervisor/relaunch-budget.selftest.js`, `node ignite/supervisor/owed-from-
endings.selftest.js` — both green, confirming the backward-compatible `refusalText` merge path holds
for the two out-of-custody callers. Committed `45fa2c44`, not deployed — `ignite/supervisor/` and
`ignite/chat/` are deploy-pinned; inert until the orchestrator's deploy window.

## ATTENTION
1. **`countRetry`'s `lastWords` lookup is gated on `t.reason === 'incomplete'` only** — do not widen
   it to `nonterm`/`unread` without re-deriving whether `seat_endings` is actually about THAT retry;
   for those two drivers the current ending row (if any) predates the mail/wake being retried and
   quoting it would misattribute words to the wrong event.
2. **`recordGroupedAsk` accepts both `refusalText` (legacy) and `lastWords` (new) on purpose** — two
   callers outside this fix's custody (`announceDisarm`, `relaunch-budget.js`) still pass the old
   name; do not delete it without sweeping both (neither is this seat's to edit unasked).
3. **`exhaust()`'s `evidencePointer` and `seatEvidencePointer` are DIFFERENT pointers** — the former
   is the system ending stamp's own pointer (defaults to the ask file); the latter is the seat's
   transcript. Collapsing them would make the daemon's own re-stamp point at a seat transcript it
   never produced, or vice versa.
- the lastWords lookup is gated on reason==='incomplete' only — do not widen without re-deriving relevance for nonterm/unread
