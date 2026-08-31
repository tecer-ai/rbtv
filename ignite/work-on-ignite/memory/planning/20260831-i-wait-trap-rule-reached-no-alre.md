# 20260831-i-wait-trap-rule-reached-no-alre — Wait-trap rule reached no already-authored seat

kind: issue
component: planning
date: 2026-08-31
commit: c48d2fa1
deployed: no
pin: NONE
components: meta-planning

## Observed

Seven agent sittings in the `redesign-continue-1` plan were lost to the headless-wait trap
(a headless sitting ends when its turn does; a seat that ends a turn expecting to be woken
loses everything uncommitted). The seventh happened AFTER `meta/planning/references/
headless-seat-cannot-wait.md` (commit `91c2a160`) was already committed, by a seat launched
after that commit — it still ended its turn saying "it will notify me automatically".

## Mechanism

The reference document was correct and linked from `build.md`, both plan workflows, and
`ignite/planning/component.md` — but nothing in a MATERIALISED SEAT's own body pointed at
it. A seat only reads what its own `seat.md`/guidance pair puts in front of it; a reference
that requires an unprompted, self-directed read is read by nobody under load. The originally
recorded justification for not landing it in the generator ("`meta/planning/references/` is
not bound into any cage, so a caged seat cannot open it") was independently checked in this
pass and found FALSE: `spawn.js#composeCageFor` → `envelope/launch.js#admitLaunch` →
`compiler.js#compile()` unconditionally ro-binds family 5 (`vault-wide-read`, the whole
workspace) and family 6 (`rbtv-repo`, the whole rbtv repo) into every compiled cage, ungated
by any seat.md declaration — confirmed by running `compile()` live against repo HEAD
(`05f0ee81`) and the deployed copy (`fa99f199`), and no deny-list/private-scope entry masks
`meta/planning/references/`. The true gap was discoverability, not access.

## Attempts

First attempt held partially: the reference file itself (commit `91c2a160`, 2026-08-31) was
correct on its subject and reached plan-authoring surfaces (drafters, `build.md`), but did
not reach a seat already authored or one whose body simply omitted the link — which is
exactly the seventh sitting's shape. That gap was surfaced but deliberately not closed in
that pass (recorded in that entry's own Consequences/ATTENTION as future work).

## Fix

Landed the rule directly in `_SEAT_GUIDANCE_MD` in `ignite/planning/materialize-seats.py` —
the constant `_write_seat_guidance()` renders into every materialised seat's `CLAUDE.md` AND
`AGENTS.md`, unconditionally, regenerated on every run. One line plus a pointer, added right
after the banner blockquote (before the first `##` section, so it is the first thing read):
"Your sitting ends when your turn does — never end a turn expecting to be woken; run every
check now, or stop and report state." plus the reference path. Chosen over expanding the
reference's own reach (rejected: no seat-body surface reaches an already-authored seat) and
over reorganising the guidance block (out of scope by owner ruling — the block is prime
context-cost real estate, so the fix is the minimum that closes the discoverability gap).

## Consequences

Regenerates the guidance pair of every materialised seat in every goal — no other file
duplicates or golden-copies this text (checked: `grep` for the unique section strings
returned no hits outside `materialize-seats.py`), and the nine other repo hits on
`d-uniform-descriptor-carriage` all discuss content DELIVERY (system-prompt vs stdin), never
the guidance text's content, so none needed a change. Nothing deleted or replaced.

## Verification

Red-first: materialised a fixture seat (`build_fixture()` + `main()` against `demo-flow`) on
the pre-change tree — guidance pair carried no wait-trap text. Green: re-materialised the
same fixture post-change — both `CLAUDE.md` and `AGENTS.md` carry the identical new line
(diff confirmed byte-identical between the two files). `python3 ignite/planning/
materialize-seats.py --selftest`: PASS — 0 failed check(s), 0 failed row(s) of 63. Not yet
deployed as of this filing — commit `c48d2fa1` on `ignite/core-daemon`, repo only.

## ATTENTION

- The stated justification for a change can be independently false while the change itself
  remains correct for a different reason — verify the STATED premise before building, but
  don't assume a false premise voids the ask; check whether a narrower true reason survives.
- `meta/planning/references/` (and `meta/` generally) IS reachable read-only from every
  caged seat via the unconditional `rbtv-repo` (family 6) and `vault-wide-read` (family 5)
  cage families — this was previously and wrongly assumed unreachable in at least one other
  memory entry (`meta-planning/20260831-c-reference-a-headless-seat-cann.md`) and one plan
  ruling (superseded by `d-ask16-wait-rule-reaffirmed`); do not re-inherit the old claim.
- A reference file reaching PLAN-AUTHORING surfaces (drafters, `build.md`) is not the same
  as reaching a MATERIALISED SEAT — the seat only reads what its own generated body carries.
- meta/ IS cage-reachable read-only (family 5+6, ungated) — a prior belief it wasn't is false, do not re-inherit it
- a reference reaching plan-authoring surfaces does not reach an already-materialised seat's own body
