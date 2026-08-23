# 20260819-c-single-daemon-commit-deploy — single-daemon-commit-deploy

kind: creation
component: deploy
date: 2026-08-19
commit: a80c9c58,ce20e757,5a9c8750,44a258c2,8e81a629
deployed: yes
pin: NONE
components: capabilities,server
seeded: true

## Motivation
On 2026-08-17 the owner accepted in-place deploy as designed (`c8123e30`): systemd `ExecStart` pointed at the working copy, with "no build artifact, no staging copy, and no deploy gate." The substitute for a gate was a human ordering rule — a wave's build commits had to land only inside its landing window, ending at the restart that armed them. That convention did not hold: `ignite/CLAUDE.md` at `c8123e30` recorded "~14 min of engine/coord skew when a coordination CLI went live at its build commit while the daemon held the prior engine." Because the long-lived process loaded whatever the working copy contained at the next restart (watchdog or OOM included), `git log` could not name what was running. D6 (`redesign-plan/decisions.md`, owner-ruled 2026-08-19 morning) closed that: single daemon instance, running from the last COMMIT, never the live working tree; deploying = committing; no staging.

## Design
Five commits on 2026-08-19 (14:42–14:43Z) implement D6 as a pin split, not a freeze of the whole repo. `a80c9c58` retargets the two unit templates so `WorkingDirectory`/`ExecStart`/`RBTV_IGNITE_CONFIG_PATH` resolve into `@@DEPLOY_ROOT@@` (a detached worktree) while `RBTV_IGNITE_SRC` still names the live per-invocation tree. `ce20e757` adds the only mover of that worktree: `v_deploy()` in `rbtv-ignite-daemon`, routed as `rbtv ignite daemon deploy` via `DAEMON_VERBS` in `core/capabilities/rbtv-cli/tool/lib/verbs.js`. `5a9c8750` is a comment on `resolveIgniteSrc()` in `server/index.js` — the function still returns `process.env.RBTV_IGNITE_SRC || path.resolve(__dirname, '..')`; the pin lives in the unit env, not in a resolver change. `44a258c2` deletes the 2026-08-17 "Deploy model — in place, gated by ordering" section and publishes the PINNED-vs-LIVE-TREE table: daemon JS require-closure, `spawn-profiles.yaml`, and `bridges/chat/` are PINNED; `team-kit/coord.py`, `jobs/*.py`, attached `rbtv run`, and probes stay LIVE TREE because they are re-read per invocation and were never the identity problem. `8e81a629` changes one history phrase ("ran in place from the source tree" → "ran from the working copy") so the superseded ruling cannot be read as still partly in force.

What was rejected is the 2026-08-17 regime itself: a process convention instead of a checkout gate. No other alternative (image, rsync staging, two-instance flip) is named around D6 in `redesign-plan/decisions.md`. "No staging" is the ruling, not an implementation leftover — `v_deploy` therefore refuses a missing or dirty deploy worktree rather than copying dirty bytes forward.

## How it works
`DEPLOY` defaults to `${XDG_STATE_HOME:-$HOME/.local/state}/rbtv-deploy` (override `RBTV_IGNITE_DEPLOY`). `v_deploy` lists worktrees of the rbtv repo (`git worktree list --porcelain`), refuses if `$DEPLOY` is not among them, refuses if `git status --porcelain` is non-empty there, then `git checkout --detach ignite/core-daemon`, runs `npm ci --omit=dev --prefix $DEPLOY/ignite` only when `ignite/node_modules/js-yaml` is absent (a symlink into the live tree would dirty the worktree), prints `deploy: <old> -> <new>`, restarts the selected systemd user unit, and `assert_running yes`. `RBTV_IGNITE_UNIT=rbtv-chat-bridge.service … deploy` re-pins the bridge onto the same refreshed tree; both units share one worktree and therefore one commit. After boot, `.rbtv/runtime/daemon-code.json` records `root` under the deploy tree and `code.digest` of the loaded bytes; the watchdog's `daemon_code_state` re-hashes under that carried `root`. STALE CODE now means the deploy tree moved and the unit has not restarted — not that someone saved a file. Live-tree edits (`coord.py`, jobs, probes) take effect on the next invocation without `daemon deploy`; daemon JS does not.

## Consequences
The 2026-08-17 in-place / landing-window text is gone; later decisions treat the split as given (D29, `redesign-plan/decisions.md:243`, notes that a `coord.py` checkout is live without a deploy while daemon-side readers wait for the next one). `295bee37` (2026-08-22) later retargeted two dead citations inside `rbtv-ignite-daemon` (archived design-doc path; "see rbtv ignite watch" → `team_monitor.py`) — doc hygiene, not a D6 revert. Subsequent touches of `verbs.js` only register unrelated verbs (installer settings-grammar, embed-search). No later commit retargets `ExecStart` at the live tree or loosens `v_deploy`'s dirty-tree refusal.

## Verification
No probe or selftest asserts the single-instance / commit-pinned invariant. `ce20e757` added a `deploy` row to the daemon-operator capability table and wired the verb into usage strings, but the existing `selftest` verb (throwaway unit lifecycle) gained no assertion over `v_deploy`. Fix-inventory D6 records the pin as absent and the deployed fact as YES at rbtv HEAD `ac1c08d8` (2026-08-21 18:14:37Z), with no ignite JS commits landing after that deploy that would have broken the pin.

## ATTENTION
- The single-daemon / deploy=commit invariant is operational discipline only: nothing in the probe suite fails if `ExecStart` is pointed back at the live tree or if `v_deploy`'s dirty/missing-worktree refusals are dropped. Hand-check `ignite/CLAUDE.md` § Deploy model and the `resolveIgniteSrc` comment in `server/index.js` before changing deploy behavior.
- `RBTV_IGNITE_SRC` (what an editor saves) and the deploy-root worktree (what `ExecStart` boots) are different trees on purpose. A saved daemon JS file is not running until `rbtv ignite daemon deploy`; assuming otherwise is the identity ambiguity D6 removed.
- `v_deploy` refusing a dirty or unregistered deploy worktree is the D6 "no staging" gate. Letting a dirty tree through would put uncommitted bytes under `ExecStart` and restore the 2026-08-17 problem.
