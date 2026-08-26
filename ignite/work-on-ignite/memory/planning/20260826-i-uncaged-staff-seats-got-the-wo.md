# 20260826-i-uncaged-staff-seats-got-the-wo — Uncaged staff seats got the worker cage's write surface

kind: issue
component: planning
date: 2026-08-26
commit: 179310e8
deployed: no
pin: NONE
components: supervisor,meta-master

## Observed
Every uncaged staff seat's assembled `seat.md` ended with a derived section that told it the
opposite of what it may do. Measured on the live `.rbtv/goals/ignite-engine/seats/goal-master/seat.md`
(:275-291): under the header *"Your write surface — what the kernel will actually answer"* it listed
the seat's whole write surface as `.` and `seats/goal-master`, declared `seat.md` and
`coordination/permission-edits.csv` read-only, said *"Peer seat folders are absent"*, and described a
`private scope` mask over its reads. Directly above it, the same file's own `<constraints>` carried
the owner-ratified truth (D49, `meta/master/prompts/goal-master-prompt.md:188`): *"the cage no longer
fences you… You may read and write anywhere in the workspace, including the rbtv repo."* The HTML
comment above the section resolved that contradiction the wrong way — *"WHERE ANY PROSE ABOVE
DISAGREES WITH THIS SECTION, THIS SECTION IS RIGHT: the prose is authored, this is measured."* The
same section shipped in `channel-master` and `leader` descriptors. Matrix rows M3 / M22 / M23 of the
2026-08-26 role-action-program inventory grade it `GAP-undocumented`; M23 names the cost — a seat that
declines a fix it could in fact land. Deployed tree and HEAD agreed; no drift.

## Mechanism
`render_descriptors` in `ignite/planning/materialize-seats.py` appended `_WRITE_SURFACE_BLOCK` to
EVERY descriptor, with a comment stating the unconditionality was deliberate ("the trap is a property
of the cage template, not of any one seat's declaration"). That reasoning is sound for the SECTION and
wrong for its CONTENT. The rows came from `_cage_write_surface()`, which evaluates `cagespec` against
`_seat_binds()` — and `_seat_binds()` reads exactly one thing: `cage.SeatBinds` out of
`envelope/spawn-profiles.yaml`, the WORKER cage template. The string `MasterBinds` appears nowhere in
the file, and no branch of it ever asked whether a cage is composed at all. It is not: `spawn.js`
calls `isStaffUncaged(seatPath)` and returns before a single bind exists, answering from the `STAFF`
set in `envelope/launch.js` (`leader`, `goal-master`, `channel-master`). So the three roles that get NO
sandbox were handed the sandbox description of a role that does — and the priority sentence, which
earns its authority by being measured, made the unmeasured half win. The materializer had no reader of
uncaged-ness in any form; `coord.STAFF_SEATS`, which this file already imports for other purposes, is
deliberately `("leader",)` (D24) and answers a different question.

## Attempts
First attempt held on this section — checked: `git log -S'_WRITE_SURFACE_BLOCK' -- ignite/planning/materialize-seats.py`
and the two planning memory entries (`20260825-i-chair-gate-left-half-migrated`,
`20260825-c-the-approve-package-writer`), none of which touch it. The section's own history is a
sequence of fixes to its CAGED half that never questioned its audience: the D3 goal-folder-RW rewrite
after the plan-interviewer's 2026-08-11 EROFS night, and the IPH-2 move of the reading itself into
`cagespec.py`. The SIBLING defect on the same early return was fixed the day before and deliberately
scoped away from this one: `af326d61` (`supervisor/20260826-i-uncaged-staff-seats-never-got`) gave
uncaged staff seats their PATH, and its own Consequences section records leaving this renderer alone —
*"a different component, left to its custodian"* — because folding a Python descriptor renderer into a
JS spawn fix would have let one green test read as two fixes.

## Fix
Commit 179310e8 (2026-08-26). The section stays unconditional; its CONTENT branches, in a new
`_write_surface_section(seat, goal_writes)` that the emission site now calls in one line. An uncaged
staff seat gets `_UNCAGED_WRITE_SURFACE_BLOCK`, which states the real surface — no sandbox is composed,
so it may write anywhere its user account can, this goal folder in full, any other goal's folder, the
rbtv repo, and outside the workspace — and says explicitly that staying out of a peer seat's folder is
a NORM it keeps rather than a wall that keeps it, and that any refusal it does hit is a real error to
fix, never a missing grant. Its read half drops the `private scope` masking claim, which an uncaged
sitting never composes (OQ-26(b): the false promise is struck, not restored).

The alternative shape B15 offered — omit the block for uncaged seats and let the prose above stand —
was rejected. The section's authority is earned by being measured, and for an uncaged seat the
mechanism is still measurable: it is `launch.js`'s roster, not a bind list. Omitting it hands the
answer back to three separately-authored prose blocks with nothing comparing them to code, which is
the drift D13 exists to end, and leaves no gate against a future prose edit re-introducing a false
claim. So the header keeps its priority sentence — it is still the measured half; what changed is what
it measures.

Uncaged-ness is READ, never restated: `_staff_uncaged_seats()` parses the `STAFF` set out of
`envelope/launch.js` — the same directory this file already binds for `cagespec` and reads
`spawn-profiles.yaml` from, on the same principle that what a seat is TOLD and what the kernel will DO
must not be able to drift. It REFUSES (`uncaged-roster-unreadable` / `uncaged-roster-unparseable`) on a
missing or reshaped roster rather than defaulting, because the tempting fallback — assume caged — IS
this defect, re-created in silence. Not moved into the shared `spawn-profiles.yaml`, where one YAML key
would serve both languages: that needs a `launch.js` edit, outside B15's walls, and is surfaced as a
loose end.

## Consequences
Matrix rows M3, M22 and M23 lose their `GAP-undocumented` class at the renderer; the descriptors
themselves only change on the next materialize or `--refresh` of each staff seat — this commit changes
what WOULD be written, not what is on disk in `.rbtv/goals/` today, and the three live descriptors
still carry the false section until they are refreshed. Nothing was deleted: the caged block, its
`{rows}` slot, its pierce paragraph and `_cage_write_surface` are byte-unchanged and still serve every
worker and verifier seat. `materialize-seats.py` now has a second cross-language read of the envelope
component (after `cagespec` and `spawn-profiles.yaml`), and it is the first one that parses JavaScript
rather than data. DELIBERATELY NOT folded in, though it shares this cause: the generated guidance pair
`CLAUDE.md`/`AGENTS.md` (`_SEAT_GUIDANCE_MD` in the same file) repeats both falsehoods to the same
seats — *"the cage makes peer seat folders ABSENT, so an attempt fails rather than lands"* and
*"[the write surface section] is derived from the cage itself, so it beats any prose that disagrees
with it"* — and is auto-loaded by the harness, so it is read at least as often as `seat.md`. It is B15's
sibling, not B15, and is surfaced as a loose end rather than swept in.

## Verification
`python3 ignite/planning/materialize-seats.py --selftest` — PASS, exit 0, 0 failed check(s), 0 failed row(s) of 63. New acceptance row CG-3 in
`ROW_ARMS`, four checks beside the existing CG-2 arms: green — the roster read out of `launch.js`
carries all three staff roles; green — each of their sections says UNCAGED and contains no bind
enumeration, no read-only `seat.md` and no absent-peer-folders claim; green — it still carries the
priority sentence, over prose that now agrees with it; red — a CAGED seat (`exp-seat`) still gets the
enumerated block, so the chooser discriminates rather than always firing; red — a reshaped
(`const STAFF = 1;`) and an empty (`new Set([])`) roster both raise `uncaged-roster-unparseable`, so
the silent fallback is unreachable. CG-2's four arms are unchanged and still green, which is the
caged-path regression control. A direct render of both branches was captured for the seat's report.
NOT DEPLOYED at filing time: `/home/henri/.local/state/rbtv-deploy` is untouched, the daemon was not
restarted, and no live descriptor was rewritten.

## ATTENTION
- THE SECTION'S AUTHORITY IS EARNED, NOT DECLARED. *"WHERE ANY PROSE ABOVE DISAGREES… THIS SECTION IS
  RIGHT"* is only safe while the section is measured from the mechanism that actually governs the
  seat. Adding a third seat class, or a hand-written row, under that header turns a template bug into
  an instruction the occupant is told to trust over the truth.
- THE UNCAGED ROSTER LIVES IN JAVASCRIPT AND IS PARSED FROM PYTHON BY REGEX. Rewriting
  `envelope/launch.js`'s `const STAFF = new Set([...])` into any other form — a variable, an import, a
  config read — makes every materialize REFUSE with `uncaged-roster-unparseable`. That is the designed
  behaviour, not a bug; the repair is to update `_STAFF_SET_RE` in the same change, never to give the
  reader a fallback.
- NEVER SUBSTITUTE `coord.STAFF_SEATS` FOR THIS READER. It is `("leader",)` on purpose (D24, asserted
  by `coord_selftest`) and names which chair joins the first taskforce. Reusing it here silently
  returns `goal-master` and `channel-master` to the caged text, and widening it to fix that breaks the
  taskforce gate instead.
- THE SEAT.MD FIX DOES NOT REACH THE GUIDANCE PAIR. `_SEAT_GUIDANCE_MD` in this same file still tells
  every seat, uncaged ones included, that the cage makes peer folders absent and that the write-surface
  section beats any prose disagreeing with it. A future reader who sees CG-3 green may conclude the
  descriptor family is clean; it is not, and `CLAUDE.md`/`AGENTS.md` are auto-injected.
- A GREEN CG-3 IS NOT A CORRECTED DESCRIPTOR. This changes what materialize WRITES. The three live
  staff descriptors under `.rbtv/goals/` keep the false section until each is re-materialized or
  `--refresh`ed, and the daemon boots from the deploy worktree, not from this repo.
- The section's priority sentence is only safe while measured from the mechanism that governs THAT seat
