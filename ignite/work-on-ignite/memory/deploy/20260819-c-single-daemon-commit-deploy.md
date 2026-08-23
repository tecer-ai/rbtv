# 20260819-c-single-daemon-commit-deploy — single-daemon-commit-deploy

kind: creation
component: deploy
date: 2026-08-19
commit: a80c9c58,ce20e757,5a9c8750,44a258c2,8e81a629
deployed: yes
pin: NONE
components: capabilities,server
seeded: true

## What it is
A daemon deploy verb + unit templates making deploy = commit, single instance.

Full: `rbtv ignite daemon deploy` plus the two systemd unit templates and the running server's own log line. It makes "deploying" mean "committing": the deploy tree is a git worktree pinned to `@@DEPLOY_ROOT@@`, the verb refuses to run on a dirty deploy tree, detaches HEAD to `ignite/core-daemon` at the last commit, ensures `node_modules`, then restarts the daemon. There is no staging step and only ONE daemon instance runs at a time.

## Why
D6: deploy identity = last commit hash; live source tree stays separate from what's running.

Fix-inventory row D6, superseding a 2026-08-17 "in-place deploy" ruling (`ignite/CLAUDE.md` history line, commits 44a258c2 / 8e81a629). Before D6, "deploying" was ambiguous — code could be live without being committed, so nobody could tell from `git log` what the running daemon actually was. D6 collapses deploy and commit into one act: the deployed tree's identity IS its last commit hash, and `RBTV_IGNITE_SRC` (the live per-invocation source tree) stays deliberately separate from `RBTV_IGNITE_CONFIG_PATH`/`ExecStart` (the pinned deploy-root worktree) so editing the live tree never touches what's running until an explicit deploy.

## How to use & where wired
`rbtv ignite daemon deploy` (via `daemon-operator`) is the only way to promote code.

- `deploy/rbtv-ignite.service`, `deploy/rbtv-chat-bridge.service` — `ExecStart` and the config path resolve into `@@DEPLOY_ROOT@@` (the pinned worktree), not the live source tree.
- `capabilities/daemon-operator/tool/rbtv-ignite-daemon` — the deploy verb: refuses a dirty tree, `git checkout` to `ignite/core-daemon`'s last commit, `npm ci`/ensure `node_modules`, restart.
- `core/capabilities/rbtv-cli/tool/lib/verbs.js` and `tool/rbtv` (from ce20e757) expose the verb through the `rbtv` CLI.
- `server/index.js` — `resolveIgniteSrc` records the D6 pin split: `RBTV_IGNITE_SRC` names the live per-invocation tree, `RBTV_IGNITE_CONFIG_PATH` resolves into the pinned deploy tree.
- `ignite/CLAUDE.md` documents the ruling and the new "STALE CODE" meaning (code edited in the live tree is stale relative to the daemon until the next deploy).

## commit
a80c9c58,ce20e757,5a9c8750,44a258c2,8e81a629

## deployed
yes

## pin
NONE FOUND — operational discipline, not a checked invariant anywhere in the probe suite (fix-inventory D6).

## ATTENTION
- Nothing in the probe suite asserts "single daemon instance" or "deploy = commit" as an invariant — a regression here fails silently; check `ignite/CLAUDE.md`'s D6 section and `resolveIgniteSrc` by hand if deploy behavior looks off.
- Never confuse `RBTV_IGNITE_SRC` (live per-invocation tree, what you edit) with the deploy-root worktree (what `ExecStart` actually runs) — editing the live tree does not change the running daemon until `daemon deploy` runs.
