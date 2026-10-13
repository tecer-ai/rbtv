# Ignite architecture

What each Ignite file does, the commands and units Ignite exposes, and the configuration and turn contracts.

Exposed commands and units: `ignite` (`capabilities/tools/ignite/cli.js` — `ignite -h` is the command surface), the `framework` skill (guide: `core/rbtv/capabilities/glossary/agent.md`), the `agent-controls` skill for an agent's own settings, schedules, work, wakes, proactive posts, board edits, and remembered facts, and the `ignite-standing-instructions` rule every Ignite agent receives.

## capabilities/tools/ignite/

One line from each file's header. A file with no header comment is marked.

| File | Header |
|---|---|
| `audio.js` | `Audio({ command, voice?, spawn? })`, `command` being the audio tool's name on PATH (config `tools.audio`), run directly. `transcribe(file)` runs `<command> transcribe` and throws on empty or failed output. `speak(text, { voice?, out? })` runs `<command> tts`. |
| `board.js` | Checks the four-section board, writes subjects and watch-outs, closes subjects, and refreshes Timers and Flags. |
| `cli.js` | Entry `ignite`. Home from `RBTV_AGENT_HOME`, or `--agent <slug>` plus `--installation <path>`. Each verb's usage form and flags are in its own `-h` page, for example `ignite connect -h` and `ignite remember -h`. |
| `config.js` | `loadConfig(workspace)` reads and validates `<installation>/.rbtv/config/ignite/config.json` and returns it plus `workspace`. `envValue` and `slackToken` resolve named environment variables (process environment, then `.rbtv/config/env/.env`). `agentHome(config, slug)` and `storePath(config, slug)`; where an agent's folder is comes from cast's `lib/agent.js`. |
| `connect.js` | `ignite connect|disconnect`: turns the `ignite` pack on or off through `rbtv`, creates working files before connecting Slack, and manages the route in `config.json` and an optional timer. It accepts only agents below the installation's `.rbtv/agents/`. Flags: see `ignite -h`. |
| `daemon.js` | No header comment. Exports `start`, `acquireLock` and `releaseLock`. Usage line: `daemon.js --installation <path>`. Startup logs one `error` event, with the agent's name and the reason, for each agent folder cast would not launch, checks each agent's `agent.json` harness on PATH and resolves the app and bot tokens with `slackToken`. An unset variable refuses startup and names the variable. The daemon enqueues due schedules, including Albert's nightly, watchdog and Friday timers. It does not run a separate consolidation. |
| `deploy.js` | `ignite deploy [COMMIT] [--deploy-folder PATH] [--dry-run]`: resolves the commit, the installation and the deploy folder, runs `deploy.sh` once, then confirms the service stays active at that commit. A deploy that ran the script appends one line to `.rbtv/runtime/ignite/deploys.jsonl`; when the deploy folder's commit changed, the output ends with the command that undoes the deploy. Linux only. Flags: see `ignite deploy -h`. |
| `deploy.sh` | `deploy.sh <commit>`, run by `ignite deploy`. Requires `RBTV_DEPLOY` (deploy worktree) and `RBTV_INSTALLATION` (installation root). |
| `fallback.js` | Everything Ignite does about a fallback, by calling cast's rule: `planFor` reads cast's plan for the agent's model, `requestList` builds the `fallbacks` of a turn request, `failureWords` gives the part of a turn's failure a fallback explains, and `report` logs the event and queues the message to the owner (`fallback:<run id>` for a turn that ran on a fallback, `no-model:<queue id>` when no model of the level started). |
| `help.js` | `PAGES` holds the help page of each group and of each verb of `schedule`, `work` and `board`, and of `schedules-due`, `wake`, `post` and `albert`; `helpPage(command, tail)` picks the page of the verb named first after the group, else the group page. A group page lists its verbs and shows no usage form; each verb's page shows its own. |
| `history.js` | `historyPath(home, key)` is `<home>/runtime/ignite/conversations/<safe>/history.md`. `safe` is the key with Windows-forbidden characters replaced by `-`. A folder still named with the raw key is renamed on first access. `writeHistory` regenerates that file from the store. `DEFAULT_HISTORY_WINDOW` is the recent slice in every turn prompt. |
| `ingress.js` | No header comment. Exports `handleEvent`. |
| `memory.js` | Checks injected memory, saves broken copies and loads checked HEAD fallbacks, matches workspace paths, and appends remembered facts to the shared inbox. |
| `memory-write.js` | Installation publication lock, write containment, and symlink/junction rejection for memory and board writers. `runtimeFolder` names `.rbtv/runtime/ignite/`, the one folder where Ignite keeps its operational files in an installation: `memory.lock` (the publication lock), `daemon.lock` (held by the running daemon; a second daemon for the same installation refuses to start while its holder is alive) and `deploys.jsonl` (one line per deploy, appended by `ignite deploy`; no program reads it). |
| `outbox.js` | `deliverPending(store, deps)`. A board conversation (`root_ts` `board`) is posted as a new root and rekeyed. Reply text is posted once; file uploads have no caption. A confirmed post is kept on the pending row so a retry does not post it again. A row is marked delivered only after Slack confirms channel and ts. Transient delivery retries stop at `MAX_ATTEMPTS` (3); a permanent Slack error stops at once. One `hold:` notice. Harness stdout is never read here. |
| `prompt.js` | `composeTurn(...)` builds the turn message. Standing instructions are not copied into it. `readTurnMemory(home, cwd, store?, now?)` loads the five checked files and matching workspace notes. |
| `schedule.js` | `parseAt`, `parseDuration`, `cadenceSpec`, `nextOccurrence`. `FIXED_TZ` is the timezone column for `--every`, not an IANA zone. |
| `slack.js` | Slack client: `auth`, `normalize`, Socket Mode `connect`, `postMessage`, `addReaction`, `threadHistory`, `createChannel`, `joinChannel`, `inviteUser`. A mention is `<@botUserId>` outside inline code and fences. |
| `store.js` | One store per agent home. `conversationKey(team, channel, rootTs)` is `<team>:<channel>:<rootTs>`. Dispositions, retry delays, and `MAX_ATTEMPTS` live here. |
| `test_audio.js` | Suite for `audio.js`. No API header. |
| `test_board.js` | Suite for `board.js`, including checked writes, migration, timers, Flags and path boundaries. |
| `test_cli.js` | Suite for `cli.js`. No API header. |
| `test_config.js` | Suite for `config.js`. No API header. |
| `test_connect.js` | Suite for `connect.js` via `cli.js`. No API header. |
| `test_daemon.js` | Suite for `daemon.js`. No API header. |
| `test_deploy.js` | Suite for `deploy.js` via `cli.js`. The real `deploy.sh` runs against scratch git folders, a scratch HOME and stand-in `systemctl` and `journalctl` programs. |
| `test_ingress.js` | Suite for `ingress.js`. No API header. |
| `test_memory.js` | Suite for memory checking, recovery, workspace selection, append concurrency and path boundaries. |
| `test_memory_write.js` | Suite for shared lock roots, release, timeout, stale recovery and competing processes. |
| `test_outbox.js` | Suite for `outbox.js`. |
| `test_prompt.js` | Suite for checked turn memory and canonical-board recovery. |
| `test_slack.js` | Suite for `slack.js`. No API header. |
| `test_store.js` | Suite for `store.js`. No API header. |
| `test_turn_loop.js` | Suite for `turn-loop.js`. No API header. |
| `turn-loop.js` | `runOnce(slug, deps)` is one claimed turn, or a refusal or an empty claim. Refuses when `liveRun()` matches a live pid. `ignite turn` cwd is `realpath(home)`. Every request includes `systemPromptFile` `<home>/prompt.md` and `agentHome`, that same `realpath(home)`. An owner message's attachments that were not downloaded are counted and passed to `composeTurn`, never a failure. |

In the tool folder, next to the code: `templates/` and `units/rbtv-ignite-agents.service`. Outside it, in this component: the skill `skills/agent-controls.md`, and the rule `rules/ignite-standing-instructions.md`.

## Contracts

General shape only. Instance ids, token paths, and launch pins are runtime config, never source.

**Installation config.** `<installation>/.rbtv/config/ignite/config.json`, loaded by `capabilities/tools/ignite/config.js`. `loadConfig` adds `workspace` (the absolute path it was read for); that field is not stored in the file.

```
{ "slack": { "team": "<team id>", "botUserId": "<bot user id>", "ownerUserId": "<owner user id>",
    "appTokenEnv": "<env var name>", "botTokenEnv": "<env var name>",
    "ownerTokenEnv": "<env var name>", "stoolsWorkspace": "<Slack account name>" },
  "tools": { "cast": "cast", "stools": "slack", "audio": "elevenlabs" },
  "dmAgent": "<slug>",
  "routes": { "<channel id>": "<agent slug>" } }
```

The configuration keys `stools`, `stoolsWorkspace` and `audio` remain compatible with existing installations; their command values use the provider names installed by the connectors module. Reply text is standard Markdown. Slack delivery uses native `markdown_text`, and upload captions use a `markdown` block without `initial_comment`. Both paths reject empty or oversized captions before posting; the limit is 12,000 Unicode characters. Slack controls visual rendering.

A leftover `dreamer` section is not a setting. `loadConfig` ignores it and returns no `dreamer` field. `updateConfig` omits it on the next write. No verb, schedule or model check acts on it. `dmAgent` may be absent. A direct message with none configured is refused (`config.dmAgent required`). Tokens are not in this file. `slackToken` reads the named variable from the process environment, then from `<installation>/.rbtv/config/env/.env`. An unset variable the daemon needs refuses startup and names the variable; the value is never logged. Each agent's harness, model, and effort live in that agent's `agent.json`, not here. Source MUST NEVER hardcode them.

**Agent home.** `<installation>/.rbtv/agents/<slug>/`:

| File | Content |
|---|---|
| `prompt.md` | The agent's instructions. Every turn passes this absolute path as `systemPromptFile` on the `ignite turn` request. Ignite does not write a standing-instructions `CLAUDE.md`. rbtv's marked `agent` section and installed files are the instruction files. |
| `agent.json` | `{ "name", "description", "harness", "model", "effort", "voice"?, "files", "packs" }` — the one agent-wide configuration record. Ignite reads it only through cast's `lib/agent.js` (`readAgent`): the turn's launch values and voice, the startup harness check, the voice of a spoken reply, and whether the `ignite` pack is on. `harness`, `model` and `effort` are required; a record cast would not launch stops the turn. |
| `settings.json` | This agent's own settings — see "Capabilities vs settings" below. How install seeds it: see `ignite -h`. |
| `_artifacts/board.md` | Tracked short-term memory: subjects, watch-outs, generated Timers and Recently closed |
| `memory/` | Tracked learned rules and topic files, written by Albert; `learned.md` is injected every turn |
| `runtime/ignite/state.sqlite` | The store. Authoritative |
| `runtime/ignite/conversations/<windows-safe key>/history.md` | Derived full thread history. Folder name is the key with `:` and other Windows-forbidden characters replaced by `-`. Regenerable from the store |
| skill copies | Written per harness by `rbtv agent add` |

## Capabilities vs settings

Follow [Capability](../../../../../rbtv/capabilities/glossary/capability.md) for reusable instructions and [Choosing where to build](../../../../../rbtv/capabilities/methods/choosing-where-to-build.md) for their component placement. They carry no agent-specific installation path, account or owner value. Agent-specific values belong in [Settings](../../../../../rbtv/capabilities/glossary/settings-json.md), referenced from the prompt. Tools take their settings and state paths as explicit arguments or environment variables, not hardcoded paths. [Agent](../../../../../rbtv/capabilities/glossary/agent.md) owns which agent-folder files are shared through git.

**Conversation key.** `<teamId>:<channelId>:<rootTs>`, DM and channel alike. The mapping key → agent is persisted.

### Memory publication

Albert writes long-term memory. An agent in a turn does not rewrite profile, learned rules, topics, knowledge, entities, workspace notes, workstreams or timelines. `ignite remember` appends one inbox line. Albert files that line and folds watch-outs when the required owner evidence is present. A seventh watch-out is kept. The turn receives a derived board view of at most 6,000 Unicode code points; that view is not written back.

Each source agent's settings key `dreamer` holds `{ cursor, lastSuccessAt, commit, reportedConflicts }` until `ignite albert migrate` copies the cursor. The adapter reads that key. It does not require the retired runner. After migrate, do not treat that key as a live writer.

`remember` and every board write take `.rbtv/runtime/ignite/memory.lock` for their own read, modify and write. Acquisition uses exclusive file creation, retries every 25 ms for up to about 5 seconds, and records the holder pid, hostname and a unique token. A lock is reclaimed only when older than 60 seconds, its hostname matches this host, and `process.kill(pid, 0)` fails with `ESRCH`. Inbox and board writes reject symlink or junction parents and leaves.

### Albert schedules

The daemon does not consolidate. Albert's schedules `albert-nightly`, `albert-watchdog` and `albert-friday` are ordinary timers. `ignite albert recover` disables those three schedules and removes the fence. It does not start a publisher. Redeploy the common candidate to restore the retired runner, and do that before cleanup if the runner must still read the legacy config section.

A leftover `dreamer` section in the Ignite config loads and is omitted on the next write. `ignite albert cleanup` performs that write. `ignite albert probe` prints `dreamer keys absent` only when the section is gone. Cast's model-in-use check ignores the section.

### Conversation and work state

A Slack thread is one conversation. A reply uses the thread's root message timestamp as `rootTs`; a new top-level message uses its own timestamp, so it starts a separate conversation even in the same channel. Each agent has its own `runtime/ignite/state.sqlite`, and work records belong to a conversation key, not to the channel or the agent as a whole.

An owner message in a conversation reuses its latest work record unless that work is `completed` or `stopped`. Those terminal states cause a new work record linked to the old one as its predecessor. A held work record is reused but remains blocked until an explicit retry. A new conversation starts with a new work record. Old records are retained; neither a new thread nor completion deletes their summaries. A new work record starts without a saved summary or next step, although earlier messages in the same thread remain in its history.

For each turn, the runtime puts the current work's `summary`, `nextStep`, `workers`, and `outputs` in the prompt, along with `.rbtv/memory/profile.md`, `<home>/memory/learned.md`, `<home>/_artifacts/board.md`, `.rbtv/memory/_artifacts/index.md`, and `.rbtv/memory/inbox.md`, the triggering input, recent messages, and the path to full conversation history. Workspace notes under `.rbtv/memory/workspaces/` are injected only when the turn working directory is under one of their installation-relative `paths:`. Missing or rejected files load a checked HEAD fallback and alert; invalid working bytes are saved first, and no valid fallback yields a visible missing note without blocking the turn. Runtime never reads a legacy `<home>/board.md`; `connect` may copy it to an absent canonical path, without reshaping. It does not put every open work record in that prompt; `ignite work status` lists them when needed. The agent reports updated work fields and a disposition in RESULT_FILE. The runtime stores those values: `continue` requires a next step and queues another turn; `waiting_owner` and `waiting_workers` pause automatic continuation; `completed` closes that work. Completion does not erase a supplied `nextStep`, but only `continue` queues a turn from it. These fields report the agent's assessment; the runtime validates the result shape and nonce, not whether the underlying task is actually done.

**Turn.** The runtime claims one queue entry per agent (one active turn per agent), composes the prompt (triggering input, board, work state, recent history window, full-history path), and runs it through `ignite turn --request <file> --result <file>`. The request includes `systemPromptFile`, the absolute path of `<home>/prompt.md`, and `agentHome`, the agent's folder. For a request that names `agentHome`, `ignite turn` adds to the harness's command line and environment what cast's `lib/isolation.js` returns for that harness and folder, so the harness loads only what the agent folder holds and keeps no native memory; a new session, a resumed session and a fallback run on another harness all receive it. [Agent isolation](../../../../../cast/capabilities/tools/cast/documentation/agent-isolation.md) owns the values and their effect. Only the request's `agentHome` selects this, never the working folder or `RBTV_AGENT_HOME`: a request without it adds nothing. Every turn removes from the harness's environment the isolation variables the turn itself inherited. When the installation's cast defaults turn the fallback on, the request also carries `fallbacks`: the models cast would try in order when the agent's model fails to start, by [cast's rule](../../../../../cast/capabilities/tools/cast/cast.md#fallback), each with its harness, model and effort, the conversation's own session on that harness (a new one when it has none), and the prompt composed for that session. `ignite turn` runs them in that order, each in place of the run before, while a run fails to start. The result describes the last run and holds `failed`, the harness, model and error of each run before it with `end`, how that run ended (the error of a harness that could not be started, else its exit code, signal and milliseconds), and `exhausted`, true when the last run failed to start too. The runtime saves the session under the harness that ran, logs the event `fallback`, and queues one message of its own in the turn's conversation, delivered before the agent's replies of that turn: `System message: the model <harness model> has failed (exit 1 after 4s), routing to <harness model>`, with one `the model … has failed (…)` part for each run that did not start. When no model of the level starts, the turn's failure names what was tried and the model one level down, which nothing launches, and the runtime queues `System message:` followed by those words. A failed turn is retried, and the owner receives that message once for one queued input, then the one blocker when the retries end. Defaults or a model catalog cast cannot read leave `fallbacks` out of the request and are logged as `fallback-unavailable`. The next turn asks for the agent's own model again. Each invocation gets a fresh nonce and an output path. The agent MUST write JSON at that path:

```
{ "nonce": "<given>", "disposition": "completed|continue|waiting_owner|waiting_workers|stopped",
  "summary": "…", "nextStep": "…", "workers": [ { "ref": "…", "kind": "…" } ], "outputs": ["<path>"],
  "replies": [ { "text": "…", "audio": false, "files": ["<path>"] } ] }
```

A normal exit without valid output is a technical failure. The runtime delivers `replies` through its outbox. Technical failure: 3 total attempts, retry delays 5 s then 30 s, then a durable hold (agent-wide if the launch itself fails, else work-scoped) plus a Slack blocker notice. Timers and restarts NEVER remove a hold.

**CLI.** `ignite`, entry `capabilities/tools/ignite/cli.js`. Inside a turn the runtime sets `RBTV_AGENT_HOME` and `IGNITE_CONVERSATION`. Outside a turn `--agent <slug>` selects the home. Subcommands include `schedule add|list|change|cancel`, `work status|retry|resume|stop`, `wake`, `post [--thread <key-or-root-ts>]`, `board write|close`, `remember <text>`, `albert`, `connect`, and `disconnect`. `dreamer` is an unknown command. Schedule add/change/cancel and connection timer binding require an existing, valid canonical board and safe write path before they open SQLite; missing or invalid boards refuse with the board path and leave SQLite unchanged. If a committed add/change/cancel or connect/disconnect timer change cannot refresh the board, the command exits 0 with the schedule id(s) and `committed; board refresh pending`; JSON adds a `warning` field to the normal success payload. The next board write/close, schedule tick or turn refreshes from SQLite. Board write/close reads an existing agent store and renders Timers and Flags under the same lock before saving; it never creates a database. `post --thread` joins a known thread's history. `board` writes use the checked canonical path; `remember` appends to the shared inbox. Flags are `ignite -h`.

Operator steps — deploy, status, inspect, hold repair — are `runbook.md`.
