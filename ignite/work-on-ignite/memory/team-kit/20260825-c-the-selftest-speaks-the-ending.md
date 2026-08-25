# 20260825-c-the-selftest-speaks-the-ending — the selftest speaks the ending store

kind: change
component: team-kit
date: 2026-08-25
commit: 489fa4ec,df716f29,c41ab9c0
deployed: no
pin: team-kit/probes/probe-coord-selftest-notmux.py

## Motivation
`coord_selftest.py` graded four surfaces spec-state-store §4.1 deleted — the six-value record enum
and its kit-side writer bound, `awaiting-close.json` as the live ending surface, `sessions.csv`'s
`disposition` column as the durable one, and the SKEW that two ending records made possible. The
suite could not reach a verdict at all (it aborted mid-run, twice in two sittings, each time on a
row reading a retired surface), and the rows that did run were grading a vocabulary no writer could
produce. A green suite over a dead vocabulary is worse than a red one: it reports coverage of a
design that no longer exists.

## Design
Rows were RETARGETED where the claim survived the vocabulary change, and DELETED where the claim's
subject was removed — never softened to pass. Which of the two applies is stated at every site,
because the difference is the whole record: a retarget says "this property still holds, on the new
surface", a deletion says "this property has no subject, and here is what was lost with it".

The retargets put each claim on the surviving surface rather than on a rename of the old one.
dag-08's record enum plus its writer bound became the ending store's OWN write boundary — the
killed-word screen, the two voices (`who_stamped`, read off `vocabulary.js` so a third door reds the
row at its source), and the mandatory reason class — which is the same R-6 claim ("no party attests
to a fact it did not witness") enforced by CHECK constraints instead of by a keyword a call site
could decline to pass. dag-09's LG-7 INVERTED: it existed because the debt file was cleared on
success and a durable copy was needed, and §4.1 removed the erasing writer instead, so the row now
asserts the `disposition` cell is EMPTY. The W1 closer rows inverted the same way: the closer used
to originate `exited` OVER a seat's own `incomplete`, and now the seat's word stands.

The deletions each name their loss. RS-5, 7.481's skew row and RS-20's arm 3 needed two ending
records to disagree; one record cannot. 7.274's arm 1C, its three 1M meta-rows, arm 2 and row S
grade `ready.py` tables §1.7 emptied. `reap_blockers`' rows went with the function.

Rejected: keeping `seed_ending`'s legacy-word translation. It was the ONE mapping and looked like
the right place for it, but it kept `renew` and `exited` alive in the file the rest of the suite
copies its spellings from — a killed vocabulary surviving a migration inside its own translator.
Callers now say what the store stores, and `seed_ending` RAISES on anything else rather than falling
through to `done`, because a fall-through is how a fixture asks for one state and grades another.

## How it works
`seed_ending(base, seat, ending=…, armed=…, reason_class=…)` is the one seeder; `clear_ending` and
`read_ending_direct` are the two documented back doors past the store's API, each for one caller
with its reason at the site (a fixture needs "no declared ending", which no writer can produce; and
a `subprocess.Popen` stub cannot ask a store whose client is a subprocess without recursing).
`SEED_ENDINGS` is §1.2's ending→voices table, `ENDING_REASON_CLASSES` is §1.4, `KILLED_ENDING_WORDS`
is §1.7's kit-written subset. `_rs_make`'s `sessions=` takes `done|incomplete|failed:<class>`; its
`awaiting=` parameter is gone.

## Consequences
The suite reaches a verdict again, which is the point: an aborted run reads greener than a complete
one in the exit code, and that is G-121 inside the suite written to catch it.

Three LIVE gates were found by doing this and are filed as the sibling issue — the retarget is what
exposed them, because a row cannot be honestly re-pointed at a surface until someone checks that the
product reads that surface too. Two `ready.py` defects were found the same way and are SURFACED
rather than fixed, that file being out of this sitting's custody: its renew gate is unreachable
(`terminal_disposition` can no longer return `renew`), and `_DEFERRAL_BY_DISPOSITION` has no key for
`failed`, so a crashed seat classes `terminal-unenumerated` — "a value nobody established", for the
most established ending there is. Both are pinned by rows that redden when fixed.

## Verification
`python3 -B coord.py selftest`, `TMUX` unset, from `ignite/team-kit/`: before, ABORTED after 758
checks with 70 failures; after, the suite COMPLETES over 1014 discovered checks. The dag-08 boundary
rows were driven against the real store rather than a stub — the predecessor `_d8_val` had been
hollowed out to return `None` for every input while its rows went on asserting a deleted mapping, so
each refusal string was re-measured directly (`killed vocabulary refused: exited`,
`system may not stamp seat-voice done`, `seat may not stamp failed`, `unknown reason_class`) before
being asserted. Not deployed: worktree branch `ignite/core-redesign`.

## ATTENTION
- A row deleted for a vocabulary change must say what was LOST, not merely that it went. Two claims
  in this sweep were owner-level rulings with no successor — `r-owner-afk-liaison-parked`'s
  human-door exemption and Q2a's per-seat containment — and a silent deletion turns each into a
  protection everyone believes is still tested.
- `_d8_val` was a stub returning `None` unconditionally while five rows asserted on it. A grader
  that cannot fail is worse than an absent one: the suite reports it as coverage. When a row's
  helper is stubbed during a migration, the row is not red, and nothing will tell you.
- Do not re-add a legacy-word translation to `seed_ending`. It is the single most tempting place to
  put one — it is the ONE seeder, so the mapping looks canonical there — and it is exactly how
  `renew` and `exited` outlive the change that deleted them.
- `read_ending_direct` and `clear_ending` reach past the store's validation boundary. They exist for
  two named fixture needs; a row that grades the boundary and seeds through them is grading nothing.
- a row deleted for a vocabulary change must say what was LOST — two owner rulings here have no successor
- _d8_val was a stub returning None while five rows asserted on it: a grader that cannot fail reads as coverage
- never re-add a legacy-word translation to seed_ending — it is how killed words outlive their deletion
