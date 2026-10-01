# Ignite agents — operator runbook

One process per workspace, unit `rbtv-ignite-agents.service`. It runs from the deploy worktree named by `RBTV_DEPLOY`, not from a working tree other sessions edit. Config is `<workspace>/.rbtv/config/ignite/config.json`. It names the environment variables that hold Slack's tokens (`appTokenEnv`, `botTokenEnv`, `ownerTokenEnv`); the values live in the process environment or `<workspace>/.rbtv/config/env/.env`, never in the config file. An unset variable the daemon needs refuses startup and names the variable; the value is never printed. Nothing under `.rbtv/modules/ignite/` is read or created.

## Deploy

```
RBTV_DEPLOY=<worktree> RBTV_WORKSPACE=<workspace> deploy.sh <commit>
```

`deploy.sh` is `core/ignite/capabilities/tools/ignite-agent/deploy.sh` in the repo that owns the worktree. It checks the worktree out detached at `<commit>`, fills the unit template (`EnvironmentFile` is `<workspace>/.rbtv/config/env/.env`), `systemctl --user daemon-reload`, restarts `rbtv-ignite-agents.service`, and prints the running commit. Running it again at the same commit is safe. The env file must exist or deploy refuses.

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

## Agents

Installing, updating, connecting, and disconnecting an agent: `ignite-agent install|update|connect|disconnect`. Flags: see `ignite-agent -h`.

## Inspect

```
ignite-agent --agent <slug> --workspace <workspace> work status
```

Entry point, if the PATH link is not installed yet: `node <deploy>/core/ignite/capabilities/tools/ignite-agent/cli.js`.

## Post into an existing thread

Use a full conversation key from the agent's stored history, or its root timestamp when unique:

```
ignite-agent --agent <slug> --workspace <workspace> post --thread <team>:<channel>:<root-ts> --text "Check complete"
```

The command prints `<conversation key> activated` and queues delivery; `--json` returns `conversationKey`, `outboxId`, `clientMsgId`, `activated` and `channel`. Exit 0 means queued, not delivered. The confirmed post joins that thread's history. Unknown or ambiguous targets fail with exit 1 and an error on stderr; use the exact key in this agent's history to resolve ambiguity. Omitting `--thread` starts a new conversation. `--text-file`, `--file` and `--audio` also work with a thread target.

Each timer wake starts with a new conversation key and harness session, with no thread or earlier conversation history. Its input is only the schedule id. A later wake stays fresh even after an earlier result opens a Slack thread; schedules are never moved during that binding.

## Write or close a board subject

Use `ignite-agent board --help` for the checked form. Copy `<home>/board.md` to a candidate file, edit its subjects or watch-outs, then submit it:

```
ignite-agent --agent <slug> --workspace <workspace> board write --file "board candidate.md"
ignite-agent --agent <slug> --workspace <workspace> board close "Subject title" "One-line outcome" "[discussion](https://example.com/thread)"
```

The close thread is optional. All four sections must be present, even when empty. Keep Timers, Recently closed and existing Flags unchanged in a candidate. New subjects use Flags `none`. `write` reports the board path and whether bytes changed; `close` reports the title and path. `--json` returns `{path, changed, subject?}` on success or `{path, error}` with exit 1 on failure (`path` is null before a home is resolved). Validation refuses malformed or over-cap input without changing the board. Close records a dated outcome; when six closed entries already exist, archive old entries before trying again. No entry is truncated or automatically pruned. Legacy boards require reshaping before using the checked commands; these commands do not migrate them.

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
