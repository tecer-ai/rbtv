# 20260831-i-rbtv-repo-joins-the-carveable — rbtv-repo joins the carveable ro families

kind: issue
component: envelope
date: 2026-08-31
deployed: no
pin: ignite/supervisor/spawn/probes/probe-envelope-walls.js
components: supervisor,planning
register-id: G-leader-0828-1951

## Observed
`ignite-engine-loop` M1. No caged seat could write the rbtv source repo: `authorizedCarve` had a
carve clause for `vault-wide-read` and (since 2026-08-30) `mirror`, but none for `rbtv-repo`, so a
plan `extraPaths` or a seat `rw-paths:` naming a path inside the repo fell through every clause,
`findConflict` returned the pair and `compile()` refused. Measured live: the seat authoring the fix
(`door-smith`) had no rw bind anywhere under `3-resources/tools/rbtv` in its own bwrap argv, and
could not write the register either.

## Mechanism
`compiler.js#authorizedCarve` spelled the same `wide.family === X && wide.access === 'ro' &&
narrow.access === 'rw'` branch once per family. The shape had already been copied twice; the third
copy was what this milestone was asked to add.

## Attempts
Checked before proceeding, and each is why this shape and not another:
`c962f09f` / `20260830-i-family-6-admitted-no-plan-writ` — split family 6 so a mirror rw path
compiles and explicitly refused to carve `rbtv-repo`, calling it "a different hole"; that refusal is
what this entry supersedes, on the plan's authority, and the supersession is written into
`compiler.js` beside the set rather than left in a record.
`d6b59389` / `20260831-i-declared-rw-paths-never-reache.md` — threaded seat `rw-paths` into
`compile()` as `extraPaths`; that closed the "declaration never reaches the compiler" half and left
the compile-time carve hole this entry closes. Its ATTENTION items 1, 2, 4 and 5 STILL STAND
unchanged; only item 3 is superseded.
Rejected: keying the carve on the family without a declaration requirement — that is the broad
widening the 2026-08-30 sitting refused, and it is not what the plan asked for.
Rejected: a permanent chair-relay architecture (leader applies every build seat's patch by hand) —
the goal contract names the relay a BOOTSTRAP for M1 only, not an architecture.

## Fix
The three branches collapse into ONE keyed set, `CARVEABLE_RO_FAMILIES = {vault-wide-read, mirror,
rbtv-repo}`. Net effect on the tree is a DELETION: the patch is 12 files, +430/-371 with
`spawn.js` alone losing 221 lines (six orphan grant resolvers that composed nothing).

⚠ THIS REVERSES `fix-mirror-family-split` (2026-08-30, `c962f09f`) AND SUPERSEDES ITEM 3 OF THE
ATTENTION IN `20260831-i-declared-rw-paths-never-reache.md`, which says in terms "do not add that
carve to make E20/E25 executable". Read both before touching this again. The reversal is RULED, not
slipped: that split left an open owner question behind it — is the rbtv read-only floor a GAP or a
deliberate policy? — and the `ignite-engine-loop` plan (bound `5dc32b91`, approved 2026-08-31)
settles it as A GAP closed narrowly by M1, with the goal contract built around that premise. Note
honestly that the 2026-08-30 sitting gave a MERITS reason too, not only want of authority: it
called a family-keyed carve "a materially larger, security-shaped widening nobody asked for". What
makes this different is that it is asked for, narrow, and declared-only.

## Consequences
The `mirror` / `rbtv-repo` family split no longer carries the carve distinction it was created for.
It is LEFT STANDING (it still names two roots for a reader and for `wall-report`), but collapsing it
back is now a live simplification and a separate ruling.
Admission still judges via `cage.js#composeSeatCage` while the live cage composes via `compile()`,
so a grant the gate admits can still refuse at compose — filed `G-leader-0831-1859-2`, NOT closed
here.

## Verification
Run UNCAGED by the `leader` chair, because a caged seat cannot create the nested user namespace the
real-bwrap legs need (it fails identically on a pristine control, so a caged run proves nothing):
`probe-envelope-walls.js` ALL LEGS PASS — leg 11 a real caged write lands `onDisk=GRANTED`; leg 12
`declaredRw=true root=ro siblingRw=false`, i.e. the declared subtree composes rw while the repo root
stays ro and an UNDECLARED sibling gets no rw bind. `probe-seat-cage.js` PASS.
`envelope-compiler.selftest.js` PASS incl. `rbtv-repo-declared-carve-admitted` and
`extraPaths-rw-under-rbtv-repo-admitted` (renamed from `-refuses` with the behaviour).
`envelope-launch.selftest.js` PASS incl. `seat-extraPaths-composed`.
Evidence: `.rbtv/goals/ignite-engine-loop/planning/evidence/m1/relay-observable-c-uncaged.log`.

## ATTENTION
1. NOT DEPLOYED AND NOT COMMITTED as of this entry. The daemon boots from
   `/home/henri/.local/state/rbtv-deploy`, whose `spawn.js` is dated 2026-08-27 and which has no
   `plan_envelope.py` at all — so this carve changes NO live cage until a deploy. Do not read a
   green probe here as a live capability.
2. The repo-vs-deploy compiler skew is itself a hazard this patch guards: `path_b.py`
   `compile_check_envelope` gained a `compiler_js` seam because a landing gated on the REPO
   compiler while the DEPLOYED compiler refuses the same grant writes a refusing `envelope.json`,
   which is strictly WORSE than an absent one (absent falls back to `compilePlanning`; present
   refuses the launch outright, making every caged seat of that goal unspawnable). Keep that seam.
3. The fence rests on "nothing declares itself": a path only carves because a plan or a seat NAMED
   it. Never widen the carve to a family-wide rw, and never skip `isCredentialDeny` (which runs
   path-pattern-only, before this, regardless of family) or the private-scope mask appended after.
