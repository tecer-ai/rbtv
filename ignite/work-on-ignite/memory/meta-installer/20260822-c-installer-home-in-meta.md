# 20260822-c-installer-home-in-meta — installer-home-in-meta

kind: change
component: meta-installer
date: 2026-08-22
commit: eeb1fea6
deployed: yes
pin: NONE
seeded: true

## What it is
The installer moves from `core/capabilities/installer` to `meta/installer/`, and the unbuilt second installer under `admin/install/` is deleted.

`install2.py` → `meta/installer/install2.py`, now a component-first folder with its own `exposure.csv`, discovering itself under the same depth-2 rule it applies to everything else (D2) — no special case. Deleted outright: `admin/install/module-manifest.json`, `core/capabilities/installer/installer.md`, `core/capabilities/installer/tool/lib/adapters.py`, `core/capabilities/installer/tool/lib/catalog.py`, `core/capabilities/installer/tool/rbtv-install` (the unbuilt second installer, ~1300 lines removed net). Four call sites that read `Path(__file__).resolve().parent` as the tree to scan are replaced by one named `REPO_ROOT` constant — from the new home that raw pattern is the component folder, which holds no modules and scans up EMPTY (a wrong-but-silent result, not an error).

NOTE (seeding): this commit lands mostly OUTSIDE `ignite/meta` — it touches `core/capabilities/installer` (deleted), `admin/install/module-manifest.json` (deleted), `core/exposure.csv`, `core/capabilities/rbtv-cli/`, `ignite/server/settings.js`, `modules/core.md`, `modules/ignite.md`, `readme.md` — filed here because the destination `meta/` is the landing component.

## Why
Owner ruling 2026-08-22: the installer belongs to the `meta` module, never `core` — `meta/` hosts what operates on the rbtv SYSTEM itself rather than on a user goal's content, and installing rbtv into a workspace is exactly that. The module's capability-only extension (2026-08-14) admits a component holding no seats and no workflow, so `meta/installer/` is a legal home.

## How to use & where wired
`rbtv install` and `rbtv doctor` follow to the new path automatically.

- `meta/installer/install2.py` — the installer entry point, now with its own `meta/installer/exposure.csv`.
- `core/capabilities/rbtv-cli/tool/lib/verbs.js` and `rbtv-cli.md` — `rbtv install` follows to the new path; `rbtv doctor` resolves the delegate there.
- `ignite/server/settings.js` — updated reference.
- `modules/core.md` (installer section removed), `modules/ignite.md`, `readme.md` — docs updated to point at the new home.
- `REPO_ROOT` (new named constant, replacing four `Path(__file__).resolve().parent` call sites) states the repo-root depth once so no future reader re-derives it from `__file__` at the wrong folder depth.

## commit
eeb1fea6

## deployed
yes — effective on commit (installer is invoked live per run, D6 exception).

## pin
NONE

## ATTENTION
- Any code under `meta/installer/` that re-derives the repo root via `Path(__file__).resolve().parent` (instead of using `REPO_ROOT`) will scan from the WRONG depth (the component folder itself, two levels shallower than repo root) and silently return an empty module list — no error, just nothing found.
- The repo root is now `parents[2]` from `meta/installer/install2.py` — a future move of this file changes that depth and must update `REPO_ROOT` accordingly.
