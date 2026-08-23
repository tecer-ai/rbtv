# 20260822-i-exposure-manifest-resolver-fix — exposure-manifest-resolver-fix

kind: issue
component: capabilities
date: 2026-08-22
commit: 933b4ddf
deployed: yes
pin: probe-bindings.py
seeded: true

## Seen
The bindings tool's exposure-manifest resolver only accepted `exposure.csv` from the mirror tree, not from a repo-tree workflow manifest.

D86: this is the `capabilities/bindings` side of the same exposure-manifest-resolution ruling that drove `team-kit`'s `component-first-migration` — the resolver's rule must match wherever the installer reads from.

## Missed
None recorded in sources.

## Held
`bindings.py` now accepts repo-tree workflow manifests, not only the mirror.

Commit `933b4ddf` ("accept repo-tree workflow manifests (D86)") changed `capabilities/bindings/tool/bindings.py` and its probe `capabilities/bindings/probes/probe-bindings.py` (101 lines changed across both).

## commit
933b4ddf

## files
ignite/capabilities/bindings/tool/bindings.py

## deployed
yes

## pin
probe-bindings.py

## ATTENTION
- This is D86's `capabilities/bindings` half; the `team-kit` half (`component-first-migration`, commits `da69c086`/`0563266b`) applies the same "resolve wherever the installer reads from, BOTH `.rbtv/mirror` and the rbtv repo" rule to `materialize-seats.py` and `meta/installer/discovery.py`. Read both together — the ruling is one decision applied twice, not two independent fixes.
- D86's bindings half; team-kit's component-first-migration is the same ruling applied to materialize-seats.py/discovery.py — read together
