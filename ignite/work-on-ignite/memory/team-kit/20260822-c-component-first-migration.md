# 20260822-c-component-first-migration — component-first-migration

kind: change
component: team-kit
date: 2026-08-22
commit: da69c086,0563266b
deployed: yes
pin: NONE
components: meta-installer
seeded: true

## Motivation
Eleven team-kit tools (`coordinate` through `statusline-usage`) lived as rows in the module-root `ignite/exposure.csv`. `install2.py` cannot see that file: its D2 rule (owner, 2026-08-22, documented in the installer header) is that a directory at exactly depth 2 holding `exposure.csv` *is* the component, identity `<module>/<component>`, and a depth-1 module-root manifest is the old installer's shape. So nothing could create their PATH shortcuts, and `ignite/deploy/link-tools.py` could not retire. The module-root file's own comment already named the move: "when the component tree materializes and these rows split into `<component>/exposure.csv`, the prefixes drop with the move and nothing else changes."

`da69c086` (2026-08-22 11:36:05Z) did that data move and made `ignite/team-kit` the repo tree's first new-standard component. It immediately produced the live `exposes-ref-dangling` blocker D86 opened on: `materialize-seats.py#_ref_target` still resolved `exposes:` by path arithmetic (`comp_dir`, `comp_dir.parent`, `comp_dir.parent.parent`) that assumed the referencing seat and the target component sat in one tree. After the rows left the module-root file, a repo-resident seat referencing a mirror component (or the reverse) had no parent walk that landed on a real `exposure.csv`.

## Design
Two commits, same day, one ruling. `da69c086` created `ignite/team-kit/exposure.csv` with the eleven rows plus a twelfth ALIAS (`scaffold-seats` → `materialize-seats.py`). Entry-points dropped the `team-kit/` prefix and became component-relative. Nothing moved on disk — `ignite/team-kit` was already at depth 2. The team-kit SKILL stayed in the module-root manifest because it points at `ignite/skills/team-kit/SKILL.md`, outside the component. The alias is a same-day owner ruling: the declared name is `materialize-seats`, but 24 files and a probe (including the daemon's launch path) hardcode `scaffold-seats`; both names stay linked until the rename filed in `redesign-plan/loose-ends.md` retargets them.

`0563266b` (14:56:54Z) is the D86 mechanism. D86 (owner, 2026-08-22 ~13:45Z, executor the blocked engine-goal session `second-brain-70` already in `materialize-seats.py`): the materializer must read `exposure.csv` from the same place `install2.py` reads it, follow the installer's rule, ideally share the installer's code ("the installer can be de-mono-filed"), and — like the installer — recognise both `.rbtv/mirror` and the rbtv repo (mirror/meta stays in the mirror only while under development). The commit extracts a 200-line `meta/installer/discovery.py` (D2 component scan + D3 two-tree merge, mirror wins, shadowing reported) and deletes 206 lines of the same logic from `install2.py`. `materialize-seats.py` live-imports that module instead of growing a second copy.

Rejected by D86 by name: restoring the eleven rows into the module-root manifest as a stopgap. The D2/D3 labels here are `install2.py`'s own 2026-08-22 rulings (what a component is; which trees and who wins), not redesign-plan D2 (typed-message routing).

## How it works
`_discovery()` live-imports `meta/installer/discovery.py` from `Path(__file__).resolve().parents[2] / "meta" / "installer"` through `_live_import`, the sys.path helper refactored out of `_coord_import`. `_exposure_rows` stopped hand-parsing with `csv.DictReader` and calls `disc.exposure_rows({"path": str(comp_dir)})`, re-raising `disc.Refuse` as the materializer's `Refuse`. `_scan_all(comp_dir)` caches one `discovery.scan_all(mirror, repo)` per `(mirror, repo)` pair for the run (`mirror` = workspace `.rbtv/mirror`, `repo` = `_rbtv_repo_root`); `_clear_discovery_cache` runs at `main` and `run_selftest` so fixtures do not leak.

`_ref_target` now looks the referencing component up via `_own_component_id` (catalog path match, else relative-path depth against the two roots; else `Refuse("exposes-ref-dangling", …)`) and resolves `part` / `component/part` / `module/component/part` against that catalog, not against `comp_dir.parent`. `resolve_seat_exposes` appends `; scanned scan_all(mirror=… · repo=…)` onto a dangling-row refusal so the message names which trees were actually searched. A future editor declaring a team-kit tool adds a row to `ignite/team-kit/exposure.csv`; `install2.py` and `materialize-seats.py` then see the same `ignite/team-kit` component through the same `scan_all`.

## Consequences
Between 11:36Z and 14:56Z the live materializer could not resolve the newly component-local rows. Same-day sibling `933b4ddf` (15:28:55Z) applied D86 a second time inside `bindings.py#resolve_workflow` — shape-derives a catalog and admits `<ws>/.rbtv/mirror` or the workspace `rbtv.json` `rbtv_path` — without importing `discovery.py`. Read `20260822-i-exposure-manifest-resolver-fix` with this entry: one ruling, two independent copies.

`build_fixture` had to move every catalog fixture from `tmp/catalog/<comp>` onto installer depth 2 (`tmp/.rbtv/mirror/<module>/<comp>` plus repo-tree twins under `tmp/repo/…`); the old one-level layout is invisible to `scan_all`. Later same-file commits do not revert this pair: `2524e4c9` (15:18Z, D78 file-issue CLI), `d487c072` (15:45Z, lane-symlink loop from `919e1595`, not a D86 regression), `c8e9909c` (23:01Z, installer multi-select), `c80602d8` (2026-08-23, memory verb). No later D/E ruling revisits `da69c086`/`0563266b` beyond D86 itself.

## Verification
`da69c086` recorded its own check (no new probe file): both manifests parse (11 module-root rows remain, 12 in the new file), every path entry-point resolves, the module-root diff is 11 deletions and zero additions, the existing selftest passes, `~/.local/bin` still holds 27 entries, `~/.rbtv/bin` still does not exist, and the real book is untouched — nothing installed, only planned. `0563266b` extends `run_selftest` / `build_fixture` in place: EXP-1 green both directions (repo seat → mirror `web/capture/capture`, mirror seat → repo `web/browse/browse`), a same-id-in-both-trees case that must take the mirror copy, and EXP-1 red (`exposes-ref-dangling`) whose stderr names `.rbtv/mirror` and `repo`. `pin: NONE` — the pin lives inside `materialize-seats.py --selftest`. `deployed: yes` on commit: `ignite/team-kit/*.py` is live-tree Python, re-read on every invocation.

## ATTENTION
- `da69c086` alone (manifest move, no resolver change) left `exposes-ref-dangling` live until `0563266b` landed the shared scanner the same day. Cherry-picking or reverting one of the pair without the other makes team-kit's exposure rows dangling again.
- `discovery.scan_all` reads both `.rbtv/mirror` and the rbtv repo and lets the mirror win on a shared id (installer D3). A later lookup or refactor that checks only one tree silently misses the other; the `0563266b` selftest exists specifically to catch both directions and the precedence case.
- `scaffold-seats` is a deliberate temporary alias onto `materialize-seats.py` (owner, 2026-08-22) because 24 files, the daemon launch path, and a probe still hardcode that string. Deleting the row as "duplicate" breaks those callers until the rename in `redesign-plan/loose-ends.md` retargets them.
- D86 rejected restoring the eleven rows to the module-root manifest as a fix. A later dangling-reference on another component is a resolver-alignment problem, not a reason to put rows back where `install2.py` cannot see them.
- `bindings.py#resolve_workflow` (`20260822-i-exposure-manifest-resolver-fix`, `933b4ddf`) is a second D86 implementation that does not import `discovery.py`. Editing one copy does not update the other.
