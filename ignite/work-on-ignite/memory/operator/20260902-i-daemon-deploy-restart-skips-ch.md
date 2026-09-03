# 20260902-i-daemon-deploy-restart-skips-ch — daemon deploy restart skips chat-bridge + stale tools

kind: issue
component: operator
date: 2026-09-02
commit: 338f1a87eb61b3a7de28d5f1723c0525b43501b6
deployed: not-applicable
pin: NONE

## Observed
Task 42: `rbtv ignite daemon deploy` (the operator command that checks out the deploy worktree and
restarts the live daemon) restarted only the daemon unit, so `rbtv-chat-bridge.service` (the Slack-
connected bridge process) ran stale in-memory code across every deploy. Measured 2026-08-20: the
bridge stayed active from 18:38:45 through five subsequent deploys (`79ede919`..`005c3c0c`) with no
restart. Task 167: a plain restart (used for crash recovery) reboots the daemon process, but its
`ExecStart`/`RBTV_IGNITE_CONFIG_PATH` both resolve into the deploy tree, never the live repo — so a
fire-tool (a registered command a goal can invoke) added only to the live repo's tool catalogue
stayed `E_UNKNOWN_TOOL` after a restart, measured on `goal-memory-management`'s `memory-commit`
tool.

## Mechanism
`v_deploy` in `rbtv-ignite-daemon` (the operator script wrapping `systemctl --user`) ran `sc restart
"$UNIT"` against only the daemon unit — `rbtv-chat-bridge.service`, which boots from the same
deploy-tree bytes, had no restart call anywhere in the deploy verb. Separately, `restart` had no
code path comparing the deploy tree's commit against the live repo's `ignite/core-daemon` branch, so
a restart during active development silently left a config/tool gap invisible until something failed
at runtime.

## Attempts
First attempt held — a search for the "roles sitting 4" 2026-08-20 report the task's seed text named
as a possible prior fix found no such report anywhere in the vault; the only trace is a one-time
bump in the bridge's start timestamp on that date, consistent with a hand restart, never a code fix
— confirmed by `grep -n 'v_deploy\|sc restart'` on `rbtv-ignite-daemon` showing the deploy verb's
code was still unchanged going into this fix.

## Fix
Task 42: `v_deploy` now restarts `rbtv-chat-bridge.service` immediately after restarting the daemon
unit, skipped only if the bridge unit isn't installed or is already the unit being deployed;
`daemon-operator.md`'s verb table documents this. Task 167: `restart`, when acting on the `ignite`
or `chat-bridge` unit, was deliberately NOT changed to read the live repo directly — that would
break the deploy model (deploying = committing; undeployed edits must never ship silently). Instead
it now prints a loud warning naming how many commits the deploy tree is behind the live repo's
`ignite/core-daemon` branch when they disagree. It does not hard-refuse the restart, because restart
is also the crash-recovery verb and the deploy tree lags the live repo almost constantly during
active development — a hard refusal would make ordinary crash-recovery restarts unusable.

## Consequences
No change to `heart-store.js`, `ticker.js`, or `spawn-profiles.yaml` — confirmed via empty `git
diff`, including a check that the `memory-commit` argv block (a separate, unrelated task) was
untouched. The unregistered-tool refusal path (`E_UNKNOWN_TOOL`) is unchanged and still correct for
a genuinely unregistered tool.

## Verification
Task 42: verified the fix is present in the committed script (quoted in the build seat's own
report); live verification requires a deploy plus `systemctl --user show rbtv-chat-bridge.service -p
ActiveEnterTimestamp` compared against the deploy tree's HEAD commit time. Task 167: verified the
staleness-warning logic directly against real repo state (read-only, no restart run) — correctly
reported "5 commit(s) behind." Existing fixture probe `ignite/state-store/heart/probes/probe-
reject.js`: `REJECT_OK: true`, `ERROR_CODE: E_UNKNOWN_TOOL`, `QUEUE_ROWS_AFTER: 0` — a genuinely
unregistered tool still refuses correctly. `bash -n` syntax check on the modified script: OK. Not
deployed — READY-TO-DEPLOY: `rbtv ignite daemon deploy`, then compare `rbtv-chat-bridge.service`'s
`ActiveEnterTimestamp` against the deploy tree's HEAD commit time (task 42); register a throwaway
fixture tool in the live repo without deploying, run `rbtv ignite daemon restart`, expect a
staleness warning naming the commit gap, then deploy and confirm the tool resolves (task 167).

## ATTENTION
1. `restart` deliberately does NOT hard-refuse on a stale deploy tree — it only warns — because
   restart doubles as the crash-recovery verb and the deploy tree lags constantly during active
   development. Do not "fix" this into a hard refusal without accounting for crash recovery. 2.
   Any future unit added alongside the daemon that also boots from deploy-tree bytes needs its
   own restart call added to `v_deploy`, the same way `rbtv-chat-bridge.service` was added here —
   it does not happen automatically. 3. `ExecStart`/`RBTV_IGNITE_CONFIG_PATH` resolve into the
   DEPLOY tree, never the live repo, by design (deploying = committing). A fire-tool added only
   to the live repo will not be visible to the running daemon until a deploy, no matter how many
   restarts happen.
