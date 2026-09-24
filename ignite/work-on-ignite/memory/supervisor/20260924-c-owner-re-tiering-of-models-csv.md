# 20260924-c-owner-re-tiering-of-models-csv — Owner re-tiering of models.csv; one level per route class

kind: change
component: supervisor
date: 2026-09-24
commit: 734866d3
deployed: no
pin: core/sub-agents/tool/test_route.js
components: launch-profiles

## Motivation
Owner re-tiered the shared routing table to their subscriptions; each route class now sees one level.

With two levels per class, the price default handed planning to an L1 row (Grok) and bounded work to L1 rows, which the owner never wanted.

## Design
Per level, one row carries `quality-override` and one carries `price-override`: SOTA astra/fable, L1 opus-5-5/grok-4.7 (gpt-6-sol the price fallback), L2 glm-5.3 on both (terra, sonnet-5 behind), L3 sonnet-5 on both (gpt-6-luna behind). `CLASSES` in `core/sub-agents/tool/lib/route.js` went to planner=SOTA, broad=L1, bounded=L2, mechanical=L3. sonnet-5 is listed at L2 and L3 with overrides set per line, so the shipped-table validation arm in `test_route.js` now lets override columns differ between a model's level twins. Superseded models (opus-5, grok-4.6, gpt-5.6-sol, gpt-5.6-luna) are `use=off` rather than deleted, because ignite pins them by name. Rejected: keeping two-level classes and ranking level-first on price, which needed new ranking code for the same outcome.

## How it works
`promoteOverrides` in `route.js` became a stable partition (flagged rows first), which is exact only because every class admits one level; the comment on `CLASSES` says to rescope it per level if a class ever spans two. The daemon's reroute (`ignite/supervisor/routing-table.js`) reads the same file, keeps only `use=route` cli rows and dedupes by model, so it now offers the new rows as alternates and never the `off` ones. Panels (`core/sub-agents/references/panel.md`) seat every model at the class's level plus the level below.

## Consequences
New catalog rows in `core/sub-agents/tool/catalog.js`: opus-5-5, grok-4.7, gpt-6-sol, gpt-6-luna. The `cast -h` cap in `test_cast.js` rose from 50 to 54 until the superseded rows retire (task "Retire superseded models" in the vault's rbtv-tasks.md). gpt-6-sol and gpt-6-luna need codex-cli >= 0.156.1: 0.154.0 rejects them with "not supported when using Codex with a ChatGPT account", so the VPS codex must be upgraded before the daemon launches them.

## Verification
`node core/sub-agents/tool/test_route.js` and `node core/sub-agents/tool/test_cast.js` pass on the Windows desktop. Running `cast route` for all 4 classes x 2 optimizers returned the owner's table. gpt-6-sol, gpt-6-luna and grok-4.7 were confirmed live with a one-word codex/opencode call on 2026-09-24. Not deployed to the VPS by this sitting.

## ATTENTION
1. Every class admits ONE level. `promoteOverrides` relies on it: widening a class to two levels without rescoping the lift per level lets a lower level's override beat a higher level.
2. A model at two levels may differ ONLY in level and the two override columns. The validation arm still refuses any other difference, because that is how a typo shows up.
3. gpt-6-sol and gpt-6-luna fail on codex-cli 0.154.0. Upgrade codex on any host before routing to them.
- Every route class admits ONE level; promoteOverrides relies on it
