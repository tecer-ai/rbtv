# 20260825-c-derived-tree-marker-and-write — Derived-tree marker and write refusal

kind: creation
component: coord
date: 2026-08-25
commit: b9bfd814
deployed: no
pin: NONE
components: planning

## Motivation

A regenerated tree carries no fact of its own — every byte is a copy the next rebuild
overwrites — so a fix applied inside one is erased with no signal. Measured as C10 / IE-13
in the redesign investigation on a goal's `planning/current/seat-lane/`: a seat edited the
derived copy, the next materialize rmtree'd the root and restaged it, and the edit was gone
with nothing printed. `spec-component-map.md` §4 (CP1-amended, FINAL) rules the closure:
a `DERIVED.md` marker at the tree ROOT plus a write refusal at every door, explicitly NOT a
second lock (impl-planning-door owns the `planning/current/` flock).

## Design

Two halves, deliberately split across the two components that own them.

The PREDICATE lives in `coord/records.py`, beside `atomic_write`, as `refuse_if_derived(path)`
plus a typed `DerivedTreeRefusal` carrying `.source`. §4 pins that home so planning imports it
rather than growing a second parent-walk; a second walk is a second place the marker convention
can drift. It is stdlib-only, so `planning/materialize-seats.py` imports it straight from
`records` rather than through the `coord.py` shim, which reads its sixteen split files at import.

Two design points were forced by the lane's shape. First, the path is NOT resolved before the
parent walk: the lane symlinks the sibling module dirs in beside its own module, so a write aimed
THROUGH the lane at a real repo file is a path under the marked root even though it resolves
outside it — resolving first would silently miss exactly the C10 bind-into-lane case. Second, the
refusal message resolves the marker's marker-relative `source:` as well as quoting it: the lane's
marker says `source: ..`, which is correct and useless on its own, and a caller told only
"refused" still does not know where to apply the fix. `DerivedTreeRefusal` was chosen over a bare
`Refuse` because `coord` and `materialize-seats.py` have different refusal vocabularies; the typed
error lets `_refuse_derived_target` re-raise it as `Refuse("target-under-derived-tree", …)` without
re-parsing a message.

The MARKER for the lane is planted by the regenerator, not by a template. The lane root is
goal-instantiated — it exists only once a materialize has run — so there is no template file to
carry it. `build_goal_local_lane` writes it into the STAGING dir, so the marker lands in the same
`staging.replace(root)` as the tree it describes and a torn build never leaves a marked root
without contents.

## How it works

`refuse_if_derived(p)` absolutizes `p` against cwd if needed, then walks `(p, *p.parents)` looking
for a `DERIVED.md`. On the first hit it parses the marker's `source:` and `regenerator:` values
line-by-line (deliberately not a YAML load — the marker is a two-field header followed by free
prose, and a prose line shaped like YAML must not make a write door raise) and raises. No hit
returns None.

Wired at the three §4 call sites: `atomic_write` and `write_csv_table` in `coord/records.py` (the
whole team-kit write surface, plus the one CSV writer that bypasses `atomic_write`); in
`planning/materialize-seats.py`, `_ref_target` at BOTH return arms (the `rbtv:` arm and the
catalog arm), and the five non-lane writers — `create_surfaces` (the declared write-root
realizer, which is the write-root half of C10), `_write_seat_guidance`, `emit_harness_configs`,
`emit_seat_exposure_loaders` and `emit_seat_descriptors`.

The lane REGENERATOR is exempt BY CONSTRUCTION, not by a flag: it builds into
`.seat-lane.tmp` beside the root, whose parent `planning/current/` carries no marker, then
rmtree's the root and renames staging over it. It writes through `write_text`, `copyfile` and
`csv.writer` directly — never through a guarded door — so no exemption branch exists to be got
wrong later.

To mark a further tree: drop a `DERIVED.md` at its root carrying `source:` and `regenerator:`,
or, when the root is instantiated at runtime, have the thing that creates the root emit it.

## Consequences

Nothing was deleted or replaced. A write into a marked tree now raises where it previously
succeeded and was silently lost — that is the whole intended behaviour change, and nothing else
changed: `atomic_write` was not refactored, the atomic-append core was not touched (D23), and no
lock was added.

The `.rbtv/mirror/` row of §4's table was NOT implemented, and that is a deliberate refusal, not
an omission. Ground truth contradicts the row twice: the "team-kit mirror driver" it names by
`BANNER_SENTINEL` (`coord/mirror/driver/state.py`) renders `.agents/` and `.codex/`, never
`.rbtv/mirror/`; and nothing in the product regenerates `.rbtv/mirror/` at all — the installer
only SCANS it (`meta/installer/lib/commands.py`, `discovery.scan_all`) and `meta/installer/
design-decisions.md` D3 calls it workspace-local staging that WINS over the repo on a shared id.
Marking it derived would have been an active break: `meta/planning/seats.csv` gives the
`forg-builder` seat `.rbtv/mirror` as its `rw-paths`, so the marker plus the `create_surfaces`
hook would refuse that seat's every product write. Reported to the seat's owner rather than
improvised.

Known follow-ups, both pre-existing and surfaced by this work: `run_dag05_acceptance` and one
sibling in `materialize-seats.py` still resolve `coord.py` as `Path(__file__).parent / "coord.py"`,
which the 2026-08-25 component-first move (`0e662f82`) invalidated — `--selftest` aborts there
after 239 green rows; and `probe-coord-selftest-notmux` now exceeds its own 165s budget on a
selftest that takes ~3m20s at HEAD, independent of this change.

## Verification

`coord.py selftest` — PASS, 0 failures (3m25s with the change; 3m19s measured on a /tmp copy with
`records.py` reverted to HEAD, so the ~3% cost of the parent walk is not what reddens the probe).
`materialize-seats.py --selftest` — 239 `ok` rows, zero FAIL, including every GL-1 goal-local lane
row; it aborts only at dag-05 on the pre-existing stale `coord.py` path above. The four
`planning/probes/probe-planning-*.py` — all PASS.

Refusal and exemption proven together in a scratch fixture that called `build_goal_local_lane`
twice against a hand-built goal: pass 1 created the lane with `DERIVED.md` at its root carrying
both fields; pass 2 rebuilt over the already-marked root and was NOT refused; `atomic_write` into
that same lane then raised `DerivedTreeRefusal` with the resolved `source:`, exit 1. Commit
`b9bfd814`. Not deployed — worktree `ignite/core-redesign` only, ahead of cutover.

## ATTENTION

- Never call `.resolve()` on the path before the parent walk in `refuse_if_derived`. The lane
  symlinks sibling module dirs in beside its own module, so resolving first turns a write aimed
  through the lane into a real repo path and the C10 bind-into-lane case walks straight past the
  marker.
- The `_ref_target` hook sits at the RETURN arms, after the segment branches. Hoisting it — or
  any other work — above the `len(segs)` branches is the same shape as the 2026-08-23 `own`
  regression that froze two live goals for hours (`20260823-i-goal-local-seats-refused-over`).
- The lane regenerator's exemption is structural: it stages into `.seat-lane.tmp` and renames.
  Anyone who reroutes the lane builder's writes through `atomic_write` for tidiness makes the
  regenerator refuse its own tree on every rebuild after the first.
- `DERIVED.md`'s `source:` is marker-relative by convention, so the lane's reads `..`. Consumers
  must resolve it against the marker's directory; treating it as a workspace path lands nowhere.
- `spec-component-map.md` §4's `.rbtv/mirror/` row is not implementable as written and is
  unimplemented — see Consequences. `.rbtv/mirror/` is a SOURCE staging tree with a seat holding
  write access to it, not a derived one.
- never .resolve() before the parent walk — it defeats the bind-into-lane case
