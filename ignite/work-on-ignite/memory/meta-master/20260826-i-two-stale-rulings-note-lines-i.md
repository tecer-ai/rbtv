# 20260826-i-two-stale-rulings-note-lines-i — two stale rulings-note lines in goal-master-prompt.md

kind: issue
component: meta-master
date: 2026-08-26
commit: f3aa3f16
deployed: no
pin: NONE
components: meta-leader

## Observed
`meta/master/prompts/goal-master-prompt.md` carried two lines contradicting the owner's own
rulings, in the "2026-08-21"/"2026-08-19" rulings-note sections (dated-rank sections marked NEWER
than the body above them, i.e. live text, not history): (1) line ~223 "Secrets-read stays masked
(D49.2)" — OQ-26(b) ruled nothing masks secrets for an uncaged seat, and that ruling already struck
the sibling "Secrets stay UNREADABLE (…are masked)" sentence in commit 052b0042, but this second,
differently-worded false claim in the same file survived because OQ-26 named only the first
sentence. (2) line ~212 "Future-goal mint (D9, option b). Not automatic." — contradicts D79
(2026-08-22): the goal-master chair is minted AUTOMATICALLY by the materialize staff pass
(`mint_staff_chairs`) since that date, per `master-scaffold-flow.md` §6.

## Mechanism
Both lines are historical-ruling notes appended over time and never revisited when a LATER ruling
superseded them — the file has no mechanism that flags a dated note as stale when a newer decision
lands elsewhere, so a true-when-written sentence silently becomes false-now prose a spawned seat
still reads as current.

## Attempts
First attempt held — checked: commit 052b0042 (which fixed the sibling secrets sentence and six
other stale sites in the same file) and `master-scaffold-flow.md` §6 (which carries the D79 ruling
text this fix aligns to) — neither touched these two specific lines.

## Fix
(1) Replaced "Secrets-read stays masked." with "Secrets are NOT masked for this seat — see the
Secrets bullet below," pointing at the very next bullet (D49.1/D49.3) which already states the true
mechanism (mediated append-only via `secret-add`, no read-back) — avoids restating it a third time
in the same file. (2) Rewrote the mint line to state AUTOMATIC-since-D79 and cite
`master-scaffold-flow.md` §6, keeping the manual `scaffold-seats` mint as the pre-D79 fallback it
still is.

## Consequences
No other line in the rulings-note sections changed. The three PAUSED live goals'
`seats/goal-master/seat.md` (rendered copies of an EARLIER version of this same source file) still
carry the ORIGINAL "Secrets stay UNREADABLE" sentence (already fixed at the source in 052b0042 but
never re-rendered into these three) plus pre-OQ-9 direct-creation prose — both hand-fixed in the
same session under an owner grant, working-tree only in the vault, not part of this repo commit.

## Verification
Read the corrected lines back after editing; cross-checked against the already-fixed sibling text
at lines 166/188/224 of the same file (the honest secrets wording) and against
`master-scaffold-flow.md` §6 (the D79 text) to confirm exact alignment. No selftest covers prompt
prose in this component.

## ATTENTION
1. A "rulings note — DATE" section in this file is a dated-rank LIVE statement, not history, unless
   explicitly marked superseded — treat every one as a claim to re-verify against the current
   decisions ledger, not as an inert log entry.
2. The three paused live goals' rendered `goal-master/seat.md` copies are NOT re-derived from this
   source automatically (the `skill-cli-dangling` refusal blocks `materialize-seats.py --refresh`,
   per this run's captured DEFECT) — a source fix here does not reach them without a separate,
   explicit hand-edit.
- A dated rulings-note section is LIVE, not history, unless marked superseded
