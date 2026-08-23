# 20260822-c-component-first-migration — component-first-migration

kind: change
component: team-kit
date: 2026-08-22
commit: da69c086,0563266b
deployed: yes
pin: NONE
components: meta-installer
seeded: true

## What it is
Migrate team-kit to component-first exposure: its own `exposure.csv` instead of a shared root-level one.

Shares the D2 discovery mechanism with the rbtv installer, so both the installer and the materializer resolve `exposes` the same way.

## Why
D86 (owner, 2026-08-22 ~13:45Z, on the `exposes-ref-dangling` live blocker from commit `da69c086`): the materializer's resolver must read `exposure.csv` from the SAME location the installer (`install2.py`) reads it — the installer's location is the source of truth. The resolver follows the installer's rule, sharing the installer's code where possible (the installer can be de-mono-filed), and — like the installer — materialize must recognise BOTH the `.rbtv/mirror` tree and the rbtv repo as sources. Not a "restore the 11 rows" interim fix.

## How to use & where wired
`ignite/team-kit/exposure.csv` (new, team-kit's own manifest — 18 lines added; the old root `ignite/exposure.csv` lost its 11 team-kit rows in the companion commit), `ignite/team-kit/materialize-seats.py`, `meta/installer/discovery.py` (new, 200-line shared discovery module), `meta/installer/install2.py` (206 lines removed — now calls the shared discovery module instead of its own copy). Commits: `da69c086` ("migrate to component-first — its own exposure manifest") moved the manifest; `0563266b` ("share D2 discovery; resolve exposes across both trees (D86)") built the shared resolver.

## commit
da69c086,0563266b

## deployed
yes

## pin
NONE

## ATTENTION
- `da69c086` alone (moving the manifest) left a live blocker (`exposes-ref-dangling`) until `0563266b` landed the shared resolver the same day — if these two commits are ever separated (cherry-pick, revert of one), team-kit's exposure rows go dangling again.
- The resolver now reads BOTH `.rbtv/mirror` and the rbtv repo as valid manifest sources — a future manifest lookup that only checks one tree will silently miss the other.
- da69c086 alone left exposes-ref-dangling until 0563266b landed same day; do not separate these two commits
- Resolver reads both .rbtv/mirror and the rbtv repo; a lookup checking only one tree will miss the other
