# 20260822-c-installer-home-in-meta — installer-home-in-meta

kind: change
component: meta-installer
date: 2026-08-22
commit: eeb1fea6
deployed: yes
pin: NONE
seeded: true

## Motivation

Three installers coexisted. The live one, `install2.py`, sat at the repo root because its own D1 (the file's DESIGN DECISIONS block, not redesign-plan D1) justified that placement only as "the later supersession is then a single `git mv install2.py install.py`". A second installer — `core/capabilities/installer/tool/rbtv-install` (task 7.64) plus `installer.md` / `adapters.py` / `catalog.py` — had never run: it required `<module>/module.md` and `prompts/cognitive-units/` pools that never materialized on the live trees. The older `install.py` kept serving flat module components. Owner ruling 2026-08-22, quoted in eeb1fea6: the installer belongs to the `meta` module, never `core` — `meta/` hosts what operates on the rbtv SYSTEM itself rather than on a user goal's content, and installing rbtv into a workspace is exactly that. The module's capability-only extension (2026-08-14) admits a component holding no seats and no workflow, so `meta/installer/` is a legal home.

## Design

eeb1fea6 (2026-08-22 13:18:54Z) is a near-pure move of `install2.py` → `meta/installer/install2.py` (99% similarity) plus a deletion, not a rewrite. The new folder is component-first: `meta/installer/exposure.csv` sits beside the tool so a depth-2 directory holding that file IS the component (install2.py's own D2). The installer therefore discovers itself on the same rule it applies to every other component, with no special case. D1 was rewritten in the same commit to record the placement and the `parents[2]` repo-root fact.

The second installer was deleted outright rather than left dormant. `readme.md` had called it a "third installer" and told readers to ignore it unless they were working on that layout; the commit turns that paragraph into a tombstone ("nothing ever ran it"; content stays in git history) instead of keeping an unbuilt tree that other docs still described as live.

Rejected: leaving `install2.py` at repo root (old D1's `git mv` story, and the `verbs.js` / `rbtv-cli.md` claim that the installer must be a repo-root file because a workspace runs it before anything is installed). Rejected: homing it under `core/` (the subject test is the rbtv system, not a user goal). Rejected: keeping `core/capabilities/installer/` as a future KG-shape path.

First attempt held — checked: `git log --before=2026-08-22T13:18:54 -- install2.py` is only feature/fix work at the root location (D16 settings verbs, harness pruning, ls/li, D2 `component.md` retirement in 7201891b, mutation-audit, PATH linking, verb/selector surface, target discovery); no earlier commit proposes a `core`/`meta` relocation. No commit touches `core/capabilities/installer/` before eeb1fea6.

## How it works

`rbtv install` and `rbtv doctor` reach the file through `core/capabilities/rbtv-cli/tool/lib/verbs.js`: the `INSTALLER` constant is now `path.join(RBTV_ROOT, 'meta', 'installer', 'install2.py')`. The argparse prog name was already `rbtv install`; the route makes that string true at a shell. The new exposure row is `install,tool,path,rbtv install,install2.py`.

Tree scans cannot use `Path(__file__).parent` any more: from `meta/installer/` that is the component folder, which holds no modules and would return an empty catalog with no error. A named `REPO_ROOT = Path(__file__).resolve().parents[2]` (added after `STATE_REL`) is the single source; `interactive()`, `selftest()`, `cmd_doctor()`, and `main()` were the four call sites switched in this commit.

## Consequences

Deleted with the second installer: `core/capabilities/installer/` (`installer.md`, `tool/lib/adapters.py`, `tool/lib/catalog.py`, `tool/rbtv-install` — 750 lines), the `rbtv-install` row in `core/exposure.csv` (comment rewritten to explain the departure), the `installer` entry in `admin/install/module-manifest.json` (the file itself still parses), and the `### installer` section of `modules/core.md`. Two prose claims that treated the deleted tool as live were corrected in the same commit: `modules/ignite.md` no longer says it realizes `ignite/module.md` as a discovery skill (`meta/installer/install2.py` has no module-level discovery-skill method; nothing does today); `ignite/server/settings.js` now says the history-line writer it adopted is gone, while the lines it already wrote remain on disk so the shared six-key format still stands.

`da69c086` (2026-08-22 11:36:05Z, two hours earlier) had already moved `ignite/team-kit` onto the same depth-2 + `exposure.csv` rule — the precedent this commit reuses, not a consequence. Direct follow-up: `0563266b` (14:56:54Z, ~1.5h later) extracts `meta/installer/discovery.py` and makes `ignite/team-kit/materialize-seats.py` share it, serving redesign-plan D86 (owner ~13:45Z): the materializer must read `exposure.csv` from the same location `install2.py` reads it. The installer's new home is what made the materializer's independent path-derivation diverge into the live `exposes-ref-dangling` blocker. `c8e9909c` (23:01:02Z) continues feature work (multi-select selectors, settings grammar) at the new path — the move held. `919e1595` same-day retargets ignite catalog-root from the mirror to repo `meta/`; no commit message or D-id cites this move as the cause, so it is not treated as a follow-up here.

This commit lands mostly outside `ignite/meta` (core/, admin/, modules/, readme, one settings.js comment). It is filed under `meta-installer` because the destination folder is the landing component.

## Verification

eeb1fea6's message: "Both selftests green" — `install2.py`'s existing `selftest()` and `rbtv-cli`'s existing selftest. No new selftest arm and no pin (header `pin: NONE`) were added; this is a re-pass after the move and the four `REPO_ROOT` substitutions. Deployed yes on commit: `install2.py` is live-tree Python invoked per `rbtv install` / `rbtv doctor` run, not daemon JS waiting on `rbtv ignite daemon deploy`.

## ATTENTION

- Any code under `meta/installer/` that re-derives the repo root via `Path(__file__).resolve().parent` instead of `REPO_ROOT` scans the component folder (two levels too shallow) and returns an empty module list with no error — the failure mode eeb1fea6 named "a wrong-but-silent result, not an error".
- `REPO_ROOT = Path(__file__).resolve().parents[2]` is coupled to `meta/installer/install2.py`'s exact depth. A future move of that file that does not update `parents[N]` reproduces the same silent empty scan.
- `meta/installer/discovery.py` (extracted 0563266b for redesign-plan D86) is shared by `install2.py` and `ignite/team-kit/materialize-seats.py`. Editing the discovery rule in only one consumer re-opens the `exposes-ref-dangling` split D86 closed.
- Deleting a tool is not done when its registration row is gone: `modules/ignite.md` and `ignite/server/settings.js` still described `core/capabilities/installer/tool/rbtv-install` as live until this commit grepped the claims, not just the inventory.
