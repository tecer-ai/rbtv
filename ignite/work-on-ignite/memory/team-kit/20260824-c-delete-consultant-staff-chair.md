# 20260824-c-delete-consultant-staff-chair — Delete consultant staff chair, keep ask labels

kind: change
component: team-kit
date: 2026-08-24
commit: bbbddaac
deployed: no
pin: NONE
components: engine

## Motivation
Ruling [T2-R17, D-7-ruling] (redesign D19, subsystem 11): the `consultant` ROLE/CHAIR is deleted —
it is not "unstaffed", it is removed. `work-content`/`recovery`-style ask-subject LABELS survive
where they exist; they never named a chair. Before this change `STAFF_SEATS = ("leader",
"consultant")` in `coord.py`, mirrored in `engine/bus-answer.js` and `engine/reconcile.js`
(`STAFF_CHAIRS`), so an `--type ask` sent to `auto` could resolve to a second staff chair no live
goal has ever staffed (measured historically — see `20260820-c-goal-master-mint-door.md`).

## Design
`STAFF_SEATS` narrows to `("leader",)` in `coord.py`; the two JS mirrors drop `'consultant'` the
same way. `routed_recipient`'s `ask` branch, which used to call
`staff_route_target(args, base, "consultant", ...)`, now returns a literal `("leader", why)` —
the ladder that used to weigh "is a consultant staffed?" collapses because there is nothing left
to weigh. `staff_route_target` itself is KEPT as a named function (not inlined): the session
closer's staff-mail arm still calls it with a caller-supplied `--route` flag that can be garbage
or stale, so the "flag is a HINT, never an authority" fallback ladder still earns its keep with
one destination. `--route`'s CLI choices are `list(STAFF_SEATS)`, so removing `consultant` from
the tuple auto-shrank the flag's valid values — no separate edit needed there.

## How it works
`coord.py`: `STAFF_SEATS = ("leader",)` (was `("leader", "consultant")`), `routed_recipient`'s
`ask` branch hardcodes `"leader"`, `staff_route_target` docstring updated, `--route` help text
drops the consultant guidance. Two selftest fixtures that used a `consultant`-named seat to
exercise the STAFF-chair branch of `is_conversational_chair`/`CONVERSATIONAL_CHAIRS` were renamed
to use `leader` instead (the only remaining `STAFF_SEATS` member), keeping the STAFF-chair arm
distinct from the `goal-master` SUMMONED-chair arm. `engine/bus-answer.js`: `STAFF_SEATS = ['leader']`.
`engine/reconcile.js`: `STAFF_CHAIRS = ['leader', 'goal-master']`. `engine/probes/probe-frozen-frontier.js`:
the IDLE-chair fixture (`fixtureIdle`) renamed its `consultant`-named row to `leader`, for the same
reason coord.py's own selftest did — `is_staff_seat('consultant')` is now false, so a seat
literally named `consultant` would read READY, not IDLE, breaking the fixture's premise.
`materialize-seats.py`'s `mint_staff_chairs` needed no functional change — it loops
`_coord_staff_seats()` dynamically, so it now mints only `leader`; only its docstring, which
described the "silent skip for the optional consultant" case, was corrected.
Docs updated: `communication.md` §4's `ask` row now states `leader` unconditionally;
`protocol.md`'s staff-chairs section drops the consultant half entirely, and its `--route`
example and the guidance-shaped-question sentence lose the `consultant` destination;
`roles.md`'s `consultant` bullet is replaced with a DELETED stub, matching the file's own
existing convention for `closer seats` and `watcher seats`; `starter-set/CLAUDE.md`'s scaffold
description drops the "optional sibling" line.

## Consequences
Deleted: the `consultant` value out of `STAFF_SEATS`/`STAFF_CHAIRS` everywhere, the
`ask`-falls-back-to-consultant-else-leader ladder (now a fixed `leader`), the two-package
selftest arm that used to prove the fallback by contrasting a staffed-vs-unstaffed consultant
package (D2 arm 3 in `coord.py`'s selftest — simplified to a single-package "ask always resolves
to leader" arm; the second fixture package and its `_mk_d2_pkg(consultant=...)` parameter were
removed as dead weight once nothing exercised the cast branch).
NOT touched, deliberately out of this subsystem's scope: `meta/leader/component.md`,
`meta/leader/prompts/consultant.md`, `meta/leader/seats.csv`,
`meta/master/references/master-scaffold-flow.md`, `meta/planning/references/workflow-anatomy.md` —
these still fully describe and ship a consultant seat definition/casting door, which is now
orphaned (its `STAFF_SEATS`/`is_staff_seat` special-casing is gone, so casting a
`consultant.json` today would produce a seat that behaves as an ORDINARY root, not a staff
chair — no IDLE exemption, no unconditional-recipient admission). This is a real inconsistency
left for a follow-up (not assigned to this subsystem's explicit file list).

## Verification
`python3 -B -c "import py_compile; py_compile.compile('ignite/team-kit/coord.py', doraise=True)"`
and the same for `materialize-seats.py` — both clean. `node --check` clean on
`bus-answer.js`, `reconcile.js`, `seeding.js` (untouched, checked anyway), `probe-frozen-frontier.js`.
`env -u TMUX python3 -B coord.py selftest`: 1054 ok, PASS (0 failures) — matches the
subsystem-8 baseline exactly. `node ignite/engine/probes/probe-frozen-frontier.js`: 18/18 passed,
PASS, including the renamed IDLE-chair fixture. `node ignite/engine/reconcile.selftest.js`: 32 ok,
exit 0, including the D24 arm ("summoned list read off coord.py: [\"goal-master\"]"). Deployed:
no — not yet deployed to the live daemon tree; `coord.py` is live-tree Python (D6 exception,
effective on save); the JS files need the normal deploy step.

## ATTENTION
1. `staff_route_target`'s CLI-facing `--route` choices are `list(STAFF_SEATS)` — a future staff
   chair addition needs NO edit to the flag's valid-value list, only to `STAFF_SEATS` itself; do
   not hand-list route choices again.
2. A seat literally named `consultant` (or any name that used to sit in `STAFF_SEATS`) is now an
   ORDINARY seat everywhere `is_staff_seat`/`STAFF_SEATS` gates behavior — it will NOT read IDLE
   with no `after`, and `known_recipients`/the JS mirrors will NOT admit it unconditionally. A
   fixture or a real goal casting `consultant.json` today gets silently wrong behavior, not a
   refusal.
3. `meta/leader/` (component.md, prompts/consultant.md, seats.csv) and two `meta/master`/`meta/planning`
   reference docs still describe the consultant chair as staffable — this subsystem's explicit
   file list did not include them, so they are now STALE, not deleted. Follow-up needed.
4. `work-content`/`recovery` — the ASK LABELS the ruling names as surviving — do not exist as
   literal strings anywhere in `ignite/`/`meta/` today (checked by grep before and after this
   change); there was nothing to touch or protect. Do not assume they are wired somewhere unseen.
5. The D2 arm-3 selftest fixture (`_mk_d2_pkg`) lost its `consultant` boolean parameter and its
   second ("cast") package — if a future chair needs a "staffed vs not" contrast test again, that
   two-package pattern is the reusable shape, not a new one.
- meta/leader (component.md, prompts/consultant.md, seats.csv) still ships a consultant seat definition; now orphaned, not this subsystem's scope
