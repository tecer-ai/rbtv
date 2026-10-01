# Ignite architecture

What each Ignite file does, the commands and units Ignite exposes, and the configuration and turn contracts.

Exposed commands and units: `ignite-agent` (`capabilities/tools/ignite-agent/cli.js` — `ignite-agent -h` is the command surface), the `create-agent` skill, the `agent-controls` skill for an agent's own settings, schedules, work, wakes, and proactive posts, and the `ignite-standing-instructions` rule every Ignite agent receives.

## capabilities/tools/ignite-agent/

One line from each file's header. A file with no header comment is marked.

| File | Header |
|---|---|
| `audio.js` | `Audio({ command, voice?, spawn? })`, `command` being the audio tool's name on PATH (config `tools.audio`), run directly. `transcribe(file)` runs `<command> transcribe` and throws on empty or failed output. `speak(text, { voice?, out? })` runs `<command> tts`. |
| `cli.js` | Entry `ignite-agent`. Home from `IGNITE_AGENT_HOME`, or `--agent <slug>` plus `--workspace <path>`. `settings set` validates through `cast list --json` and never a copied model list. Install, update, connect, and disconnect: see `ignite-agent -h`. |
| `config.js` | `loadConfig(workspace)` reads and validates `<workspace>/.rbtv/config/ignite/config.json` and returns it plus `workspace`. `envValue` and `slackToken` resolve named environment variables (process environment, then `.rbtv/config/env/.env`). `agentHome(config, slug)` and `storePath(config, slug)`. |
| `connect.js` | `ignite-agent connect|disconnect`: Slack channel or direct messages, the route in `config.json`, an optional timer. Flags: see `ignite-agent -h`. |
| `install.js` | `ignite-agent install|update`: `rbtv install agent add|update`, then Ignite's standard units into the agent folder, `board.md`, the database. Flags: see `ignite-agent -h`. |
| `daemon.js` | No header comment. Exports `start`. Usage line: `daemon.js --workspace <path>`. Startup checks each agent's `launch.json` harness on PATH and resolves the app and bot tokens with `slackToken`. An unset variable refuses startup and names the variable. |
| `deploy.sh` | `deploy.sh <commit>`. Requires `RBTV_DEPLOY` (deploy worktree) and `RBTV_WORKSPACE` (workspace root). |
| `history.js` | `historyPath(home, key)` is `<home>/conversations/<safe>/history.md`. `safe` is the key with Windows-forbidden characters replaced by `-`. A folder still named with the raw key is renamed on first access. `writeHistory` regenerates that file from the store. `DEFAULT_HISTORY_WINDOW` is the recent slice in every turn prompt. |
| `ingress.js` | No header comment. Exports `handleEvent`. |
| `outbox.js` | `deliverPending(store, deps)`. A board conversation (`root_ts` `board`) is posted as a new root and rekeyed. Reply text is posted once; file uploads have no caption. A confirmed post is kept on the pending row so a retry does not post it again. A row is marked delivered only after Slack confirms channel and ts. Transient delivery retries stop at `MAX_ATTEMPTS` (3); a permanent Slack error stops at once. One `hold:` notice. Harness stdout is never read here. |
| `prompt.js` | `composeTurn(...)` builds the turn message. Standing instructions are not copied into it. `readBoard(home)`. |
| `schedule.js` | `parseAt`, `parseDuration`, `cadenceSpec`, `nextOccurrence`. `FIXED_TZ` is the timezone column for `--every`, not an IANA zone. |
| `slack.js` | Slack client: `auth`, `normalize`, Socket Mode `connect`, `postMessage`, `addReaction`, `threadHistory`, `createChannel`, `joinChannel`, `inviteUser`. A mention is `<@botUserId>` outside inline code and fences. |
| `store.js` | One store per agent home. `conversationKey(team, channel, rootTs)` is `<team>:<channel>:<rootTs>`. Dispositions, retry delays, and `MAX_ATTEMPTS` live here. |
| `test_audio.js` | Suite for `audio.js`. No API header. |
| `test_cli.js` | Suite for `cli.js`. No API header. |
| `test_config.js` | Suite for `config.js`. No API header. |
| `test_connect.js` | Suite for `connect.js` via `cli.js`. No API header. |
| `test_install.js` | Suite for `install.js` via `cli.js`. No API header. |
| `test_daemon.js` | Suite for `daemon.js`. No API header. |
| `test_ingress.js` | Suite for `ingress.js`. No API header. |
| `test_slack.js` | Suite for `slack.js`. No API header. |
| `test_store.js` | Suite for `store.js`. No API header. |
| `test_turn_loop.js` | Suite for `turn-loop.js`. No API header. |
| `turn-loop.js` | `runOnce(slug, deps)` is one claimed turn, or a refusal or an empty claim. Refuses when `liveRun()` matches a live pid. `cast turn` cwd is `realpath(home)`. Every request includes `systemPromptFile` `<home>/agent.md`. |

In the tool folder, next to the code: `templates/` and `units/rbtv-ignite-agents.service`. Outside it, in this component: the skills `skills/create-agent.md` and `skills/agent-controls.md`, and the rule `rules/ignite-standing-instructions.md`.

## Contracts

General shape only. Instance ids, token paths, and launch pins are runtime config, never source.

**Workspace config.** `<workspace>/.rbtv/config/ignite/config.json`, loaded by `capabilities/tools/ignite-agent/config.js`. `loadConfig` adds `workspace` (the absolute path it was read for); that field is not stored in the file.

```
{ "slack": { "team": "<team id>", "botUserId": "<bot user id>", "ownerUserId": "<owner user id>",
    "appTokenEnv": "<env var name>", "botTokenEnv": "<env var name>",
    "ownerTokenEnv": "<env var name>", "stoolsWorkspace": "<stools workspace name>" },
  "tools": { "cast": "<cmd>", "stools": "<cmd>", "audio": "<cmd>" },
  "dmAgent": "<slug>",
  "routes": { "<channel id>": "<agent slug>" } }
```

`dmAgent` may be absent. A direct message with none configured is refused (`config.dmAgent required`). Tokens are not in this file. `slackToken` reads the named variable from the process environment, then from `<workspace>/.rbtv/config/env/.env`. An unset variable the daemon needs refuses startup and names the variable; the value is never logged. Each agent's harness, model, and effort live in that agent's `launch.json`, not here. Source MUST NEVER hardcode them.

**Agent home.** `<workspace>/.rbtv/agents/<slug>/`:

| File | Content |
|---|---|
| `agent.md` | The agent's instructions. Every turn passes this absolute path as `systemPromptFile` on the `cast turn` request. Ignite does not write a standing-instructions `CLAUDE.md`. The installer's marked `agent` section and installed units are the instruction files. |
| `launch.json` | `{ "harness", "model", "effort", "voice"? }` — the one agent-wide launch setting. Startup's harness check reads this file, per agent. |
| `settings.json` | This agent's own settings — see "Capabilities vs settings" below. How install seeds it: see `ignite-agent -h`. |
| `board.md` | Human-readable work and the recurring checks the agent attends to |
| `state.sqlite` | The store. Authoritative |
| `conversations/<windows-safe key>/history.md` | Derived full thread history. Folder name is the key with `:` and other Windows-forbidden characters replaced by `-`. Regenerable from the store |
| skill loaders | Written per harness by `rbtv install agent add`, which `ignite-agent install` runs |

## Capabilities vs settings

A CAPABILITY — what an agent can do, reusable by other agents — is an rbtv skill component (skill + its tools) under `<module>/<component>/` in rbtv, installed into agent homes by the installer like any other skill. It carries no agent-specific value: no workspace path, no account name, no owner value. An agent's SPECIFIC settings — the values that make a reusable capability act for THIS agent — live in ONE file in its home, `settings.json`, referenced from the agent's instructions (`agent.md`). How install seeds that file: see `ignite-agent -h`. A capability's own tools take their settings and state paths as an explicit argument or environment variable — never a hardcoded relative path — so the same capability serves any agent that installs it. An agent home is never committed.

**Conversation key.** `<teamId>:<channelId>:<rootTs>`, DM and channel alike. The mapping key → agent is persisted.

### Conversation and work state

A Slack thread is one conversation. A reply uses the thread's root message timestamp as `rootTs`; a new top-level message uses its own timestamp, so it starts a separate conversation even in the same channel. Each agent has its own `state.sqlite`, and work records belong to a conversation key, not to the channel or the agent as a whole.

An owner message in a conversation reuses its latest work record unless that work is `completed` or `stopped`. Those terminal states cause a new work record linked to the old one as its predecessor. A held work record is reused but remains blocked until an explicit retry. A new conversation starts with a new work record. Old records are retained; neither a new thread nor completion deletes their summaries. A new work record starts without a saved summary or next step, although earlier messages in the same thread remain in its history.

For each turn, the runtime puts the current work's `summary`, `nextStep`, `workers`, and `outputs` in the prompt, along with `board.md`, the triggering input, recent messages, and the path to full conversation history. It does not put every open work record in that prompt; `ignite-agent work status` lists them when needed. The agent reports updated work fields and a disposition in RESULT_FILE. The runtime stores those values: `continue` requires a next step and queues another turn; `waiting_owner` and `waiting_workers` pause automatic continuation; `completed` closes that work. Completion does not erase a supplied `nextStep`, but only `continue` queues a turn from it. These fields report the agent's assessment; the runtime validates the result shape and nonce, not whether the underlying task is actually done.

**Turn.** The runtime claims one queue entry per agent (one active turn per agent), composes the prompt (triggering input, board, work state, recent history window, full-history path), and runs it through `cast turn --request <file> --result <file>`. The request includes `systemPromptFile`, the absolute path of `<home>/agent.md`. Each invocation gets a fresh nonce and an output path. The agent MUST write JSON at that path:

```
{ "nonce": "<given>", "disposition": "completed|continue|waiting_owner|waiting_workers|stopped",
  "summary": "…", "nextStep": "…", "workers": [ { "ref": "…", "kind": "…" } ], "outputs": ["<path>"],
  "replies": [ { "text": "…", "audio": false, "files": ["<path>"] } ] }
```

A normal exit without valid output is a technical failure. The runtime delivers `replies` through its outbox. Technical failure: 3 total attempts, retry delays 5 s then 30 s, then a durable hold (agent-wide if the launch itself fails, else work-scoped) plus a Slack blocker notice. Timers and restarts NEVER clear a hold.

**CLI.** `ignite-agent`, entry `capabilities/tools/ignite-agent/cli.js`. Inside a turn the runtime sets `IGNITE_AGENT_HOME` and `IGNITE_CONVERSATION`. Outside a turn `--agent <slug>` selects the home. Subcommands include `settings show|set`, `schedule add|list|change|cancel`, `work status|retry|resume|stop`, `wake`, `post`, and `install|update|connect|disconnect`. Flags are `ignite-agent -h`.

Operator steps — deploy, status, inspect, hold repair — are `runbook.md`.
