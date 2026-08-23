# 20260822-c-home-leader-master-planning-ca — home-leader-master-planning-catalogs

kind: creation
component: meta-leader
date: 2026-08-22
commit: 49c03d35
deployed: yes
pin: NONE
components: meta-master-agent,meta-planning
seeded: true

## What it is
The leader, master-agent, and planning catalogs move from the vault mirror into the rbtv repo's `meta/` tree.

Full: `meta/leader/` (component.md, prompts/), `meta/master-agent/` (component.md, exposure.csv, prompts/), and `meta/planning/` (tasks/, workflows/forge/, workflows/planning/ — 111 files, 10423 insertions) are rewritten in-tree from `.rbtv/mirror/meta/...` literals into `3-resources/tools/rbtv/meta/...`, so they are now versioned with the code instead of living only in the mirror.

## Why
E11 (build-memory program ruling) + E15: meta scaffolding — "every harness/scaffolding layer that rbtv and ignite need to survive" — lives ONLY in the rbtv repo, never the mirror. The mirror keeps cross-module homes (things impacting all modules, like materialize/install); anything meta-only moves out.

## How to use & where wired
Any reader of leader/master-agent/planning catalogs now resolves them under `3-resources/tools/rbtv/meta/`, not `.rbtv/mirror/meta/`.

This is the destination-side move; the source-side retarget of every catalog-root reader (spawn-profiles.yaml, queue-request.js, bindings probes, master-profile tool) is a separate commit — see `20260822-i-retarget-catalog-root.md` in this same component.

## commit
49c03d35

## deployed
yes — effective on commit (meta files are read live per invocation, D6 exception).

## pin
NONE

## ATTENTION
- This commit only ADDS the files at their new repo home — it does not by itself retarget every reader; a reader still pointed at `.rbtv/mirror/meta/...` after this commit is stale until the companion retarget lands (see the linked issue entry).
