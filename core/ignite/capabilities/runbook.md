# Ignite agents — operator runbook

One process per workspace, unit `rbtv-ignite-agents.service`. It runs from the deploy worktree named by `RBTV_DEPLOY`, not from a working tree other sessions edit. The app token is `SLACK_APP_TOKEN` in the file `rbtv.json`'s `env_file` names. The bot token is the file `slack.botTokenFile` names in `.rbtv/agents/ignite.json`. Nothing under `.rbtv/modules/ignite/` is read or created.

## Deploy

```
RBTV_DEPLOY=<worktree> RBTV_WORKSPACE=<workspace> deploy.sh <commit>
```

`deploy.sh` is `core/ignite/capabilities/tools/ignite-agent/deploy.sh` in the repo that owns the worktree. It checks the worktree out detached at `<commit>`, fills the unit template, `systemctl --user daemon-reload`, restarts `rbtv-ignite-agents.service`, and prints the running commit. Running it again at the same commit is safe.

## Status

```
systemctl --user status rbtv-ignite-agents.service
journalctl --user -u rbtv-ignite-agents.service -f
```

Log lines are JSON on stdout. `event` is `ready`, `turn`, `schedules-due`, `turn-left`, or `stop`.

Stop and start:

```
systemctl --user stop rbtv-ignite-agents.service
systemctl --user start rbtv-ignite-agents.service
```

Stop sends SIGTERM. The process stops claiming, logs any in-flight run (`turn-left`), and exits without killing that child. `KillMode=process` leaves the child in place. The next start treats a still-live child as the active run and does not launch a second one. A dead child is recovered as a failed attempt. A second process exits non-zero: `daemon already running`.

## Inspect

```
ignite-agent --agent <slug> --workspace <workspace> work status
```

Entry point, if the PATH link is not installed yet: `node <deploy>/core/ignite/capabilities/tools/ignite-agent/cli.js`.

## Repair a hold

A hold survives ticks and restarts. Set a launch setting that does not use the failed model, then retry. `work retry` with no id clears only an agent hold; with an id it clears only that work hold.

```
ignite-agent --agent <slug> --workspace <workspace> settings set --harness <harness> --model <cast short name> --effort <rung word>
ignite-agent --agent <slug> --workspace <workspace> work retry
ignite-agent --agent <slug> --workspace <workspace> work retry <work-id>
```

The setting applies from the next turn in every conversation of that agent.

## Known behaviour

Queued turns. One primary turn per agent. Agents do not wait on each other. A message saved while that agent is busy stays in its queue and is claimed when the turn ends. Owner input is claimed before an automatic continuation. Saving a message is not the same as starting the turn: the eyes reaction is added when the turn starts.

Steering between turns. There is no mid-turn interruption. An owner message that arrives during a turn is saved and processed on a later turn.

Long threads. The prompt carries a bounded recent window (20 messages) plus the path of the full history file under the agent home. The folder name is the conversation key with colons replaced by hyphens. A folder left under the raw key is renamed on first access. The file is regenerated from the store. The store is authoritative.

The unit starts at boot when user lingering is on. Check with `systemctl --user is-enabled rbtv-ignite-agents.service`.

The installer puts `~/.rbtv/bin` on the user shell PATH. `deploy.sh` also keeps its conditional prepend for the service unit, since a boot-time user service may not source a shell profile; it adds the directory only when absent. The installer links `ignite-agent` there. After installing a harness or a tool in a new location, redeploy. Startup refuses to go ready if `ignite-agent` is not on that PATH.
