# 20260822-i-retarget-catalog-root — retarget-catalog-root

kind: issue
component: meta-leader
date: 2026-08-22
commit: 919e1595
deployed: yes
pin: NONE
components: capabilities,engine,config
seeded: true

## Observed

On 2026-08-22 15:04:34Z commit 49c03d35 (E15 meta-move-build, same author, 16s earlier) homed the leader, master-agent, and planning catalogs at `<rbtv>/meta/`. Every catalog-root consumer still composed `workspace/.rbtv/mirror/meta`: `queue-request.resolveCatalogRoot` / `sheetForSeat` / `buildGoalLocalSeats`, the two `tools:` `--catalog-root` argv values in spawn-profiles, `master_profile.DEFAULT_CATALOG_ROOT`, probe-bindings' `LIVE_MANIFEST` and its `materialize-seats.py` subprocess args, and the execution-mode-birth probe's `catalog_root()`. A planning materialize or master-profile default after that second would read a superseded tree the moment catalog content changed only in the repo. Destination-side move is `20260822-c-home-leader-master-planning-ca.md`. Deployed vs HEAD: `resolveCatalogRoot` and `DEFAULT_CATALOG_ROOT` still match 919e1595; both spawn-profile `--catalog-root` values are still the absolute `<rbtv>/meta` literals this commit wrote.

## Mechanism

`resolveCatalogRoot` already opened `rbtv.json` and refused a missing `rbtv_path`, then threw the field away and joined `workspace/.rbtv/mirror/<PLANNING_MODULE>` — the book was only the F2 workspace-identity gate, not the catalog address. `sheetForSeat` used that same join for every module hit; `buildGoalLocalSeats` hardcoded it. `catalog_root()` walked parents until it found `rbtv.json` and returned `parent/.rbtv/mirror/meta` without parsing the file. `DEFAULT_CATALOG_ROOT` and probe-bindings' `LIVE_MANIFEST` were workspace-relative mirror literals; spawn-profiles carried two absolute `/home/henri/…/.rbtv/mirror/meta` argv values. After 49c03d35 those paths were leftover or empty, so readers silently used the old tree instead of the repo copy E11 had just made canonical.

## Attempts

First attempt held — checked: `git log --before=2026-08-22T15:04:50` over the touched readers for `mirror/meta|catalog-root|catalog_root`. Nearest prior hits (77d2fec7 goal-local seat input, 1de46e07 C5E planning entry, 8aecc0e3 C5 argv templating, aa0b9182 watch cadence) never retargeted the mirror path. The spawn-profiles comment itself records C-2 (2026-08-10): a repoint from `planning-deprecated/` (renamed from `planner-workflow/`, vault `01f60de16`) onto `.rbtv/mirror/meta/planning/` — a component rename, not this mirror→repo move.

## Fix

919e1595 (15:04:50Z) serves E11/E15: meta scaffolding lives only in the repo; the mirror keeps cross-module homes. `resolveCatalogRoot` now resolves `rbtv_path` (relative values against the workspace, same helper as `materialize-seats.py#_rbtv_repo_root`) and joins `<repoRoot>/<PLANNING_MODULE>`. New `repoRootOf` does that read for `sheetForSeat` and `buildGoalLocalSeats`. `sheetForSeat` branches: only `mod === PLANNING_MODULE` leaves the mirror; every other module still joins `workspace/.rbtv/mirror/<mod>`. The execution-mode-birth `catalog_root()` now parses `rbtv.json` the same way. Two readers did not follow the book: `DEFAULT_CATALOG_ROOT` became `_IGNITE.parent / "meta"` and probe-bindings set `REPO = IGNITE.parent` plus `--catalog-root REPO/meta`; spawn-profiles swapped the argv literals to `/home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv/meta`. The materializer binary stayed `__dirname` (this process's build); only the catalog root follows the book. E11/E15 named the destination and the executor; no weighed alternative is in the decision log.

## Consequences

Twenty-four minutes later 933b4ddf (`fix(bindings): accept repo-tree workflow manifests`, D86) had to teach the bindings resolver both trees by shape — 919e1595 never touched that reader, so a workflow-manifest lookup still assumed the mirror layout. That follow-up is `capabilities/20260822-i-exposure-manifest-resolver-fix.md`. Docs in the same commit (`goal-creation-request.md`, starter-set `CLAUDE.md`, `modules/ignite.md`) are prose-only path swaps. No later commit on the 919e1595 path set reverts the retarget (`git log --since=2026-08-22T15:04:50` over those paths).

## Verification

No new probe was added; pin is NONE. Existing probes were rewritten to keep passing against the new location: probe-bindings' two `materialize-seats.py --catalog-root` args, `catalog_root()` in probe-execution-mode-birth, and a fixture-shape comment in `probe-queue-request-pass.js`. Header `deployed: yes`. Python tools and probes re-read live per invocation; `queue-request.js` and `spawn-profiles.yaml` are daemon-boot surfaces and only became live on a later `rbtv ignite daemon deploy` that carried 919e1595 (D6: daemon runs the last commit, never the working tree).

## ATTENTION

- A new catalog-root reader that hardcodes `.rbtv/mirror/meta/...` instead of resolving `rbtv.json`'s `rbtv_path` goes stale the moment `meta/` content changes only in the repo — that is the failure 919e1595 closed.
- This commit left `master_profile.DEFAULT_CATALOG_ROOT` and the two spawn-profiles `--catalog-root` argv values as hardcoded `<rbtv>/meta` literals, not an `rbtv_path` lookup; those two recreate the same class of staleness if the repo's `meta/` location moves again.
- 919e1595 missed `bindings.py`'s `resolve_workflow`; 933b4ddf (24 min later) had to accept both trees. A later catalog-home change has to hunt readers by behavior (`mirror/meta`, workflow/module resolvers), not by the file list one commit message names.
- `sheetForSeat` still joins `workspace/.rbtv/mirror/<mod>` for every module except planning; collapsing that branch "for consistency" would point non-meta catalogs at `<rbtv>/<mod>` where they do not live (E11: the mirror keeps cross-module homes).
