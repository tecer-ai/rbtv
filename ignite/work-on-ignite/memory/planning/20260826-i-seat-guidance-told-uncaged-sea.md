# 20260826-i-seat-guidance-told-uncaged-sea — seat guidance told uncaged seats a false cage story

kind: issue
component: planning
date: 2026-08-26
commit: f3aa3f16
deployed: no
pin: NONE

## Observed
`ignite/planning/materialize-seats.py`'s `_SEAT_GUIDANCE_MD` — the body written into every seat
folder's `CLAUDE.md`/`AGENTS.md` pair — told EVERY seat, uncaged staff included, two false things:
"the cage makes peer seat folders ABSENT, so an attempt fails rather than lands" and `seat.md`'s
write-surface section "is derived from the cage itself, so it beats any prose that disagrees with
it." Both are false for `goal-master`/`channel-master`/`leader` (`_staff_uncaged_seats()`): no
sandbox is built for them at all (`spawn.js` returns at `isStaffUncaged` before composing any
bind), so there is no cage to make anything absent, and the derived section they actually get
(`_UNCAGED_WRITE_SURFACE_BLOCK`) is measured off `launch.js`'s STAFF roster, not a cage.

## Mechanism
`_write_seat_guidance` rendered `_SEAT_GUIDANCE_MD` with a single fixed template for every seat —
the same false-cage framing this run's B15/CG-3 fix (`planning/_issues.md`, 2026-08-26) already
corrected on the DERIVED `_write_surface_section`, but `_SEAT_GUIDANCE_MD` is a SEPARATE static
template nobody had touched, so the same lie survived in the seat-folder guidance file even after
the derived section told the truth right below it.

## Attempts
First attempt held — checked: `planning/_issues.md`'s 2026-08-26 "Uncaged staff seats got the
worker cage's write surface" entry (the B15/CG-3 fix on `_write_surface_section` — a different
function, same false-cage cause, left this template untouched).

## Fix
Parameterized the two divergent paragraphs of `_SEAT_GUIDANCE_MD` as `{peer_folder_note}` /
`{write_surface_note}`, added caged/uncaged constant pairs, and a `_seat_guidance_notes(seat)`
helper that picks between them via `_staff_uncaged_seats()` — the SAME predicate
`_write_surface_section` already uses, so the two derived texts cannot drift onto different rosters
again. Rejected duplicating the whole template for an uncaged variant: only two paragraphs differ,
and a full second template is two things to keep in sync instead of one predicate and four short
constants.

## Consequences
No other paragraph of `_SEAT_GUIDANCE_MD` changed. `_write_seat_guidance`'s `.format()` call gained
two new keyword args sourced from the new helper; no caller outside this file constructs the
template directly.

## Verification
`python3 ignite/planning/materialize-seats.py --selftest` — 0 failed, 63/63 rows PASS. Added CG-4
(two new checks, run alongside CG-3 in the same `--selftest` invocation): green proves every
uncaged staff seat's guidance text says UNCAGED and never blames a cage; red proves a caged seat
still gets the cage-attributed wording (the chooser discriminates, not a blanket always-uncaged
text).

## ATTENTION
1. `_SEAT_GUIDANCE_MD` (seat-folder CLAUDE.md/AGENTS.md) and `_WRITE_SURFACE_BLOCK` /
   `_UNCAGED_WRITE_SURFACE_BLOCK` (the derived section appended to `seat.md`) are TWO SEPARATE
   templates that both describe the same cage/no-cage fact — a future fix to one's wording must
   check the other, since nothing ties them together beyond both reading
   `_staff_uncaged_seats()`.
2. The rendered fix reaches NEW seat folders only. Already-materialized seat folders (e.g. the
   three paused live goals' `goal-master`) keep whatever guidance text they were written with, and
   `--refresh` currently REFUSES on an unrelated `skill-cli-dangling` defect (this run's captured
   DEFECT), so there is no live path to re-render them until that is fixed.
- Two separate templates (guidance file + derived write-surface) both encode cage/no-cage; keep both in sync
