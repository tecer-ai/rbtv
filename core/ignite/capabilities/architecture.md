# Ignite architecture

What each Ignite file does, the commands and units Ignite exposes, and the configuration and turn contracts.

Exposed commands and units: `ignite` (`capabilities/tools/ignite/cli.js` — `ignite -h` is the command surface), the `framework` skill (guide: `core/rbtv/capabilities/glossary/agent.md`), the `agent-controls` skill for an agent's own settings, schedules, work, wakes, proactive posts, board edits, and remembered facts, and the `ignite-standing-instructions` rule every Ignite agent receives.

## capabilities/tools/ignite/

One line from each file's header. A file with no header comment is marked.

| File | Header |
|---|---|
| `audio.js` | `Audio({ command, voice?, spawn? })`, `command` being the audio tool's name on PATH (config `tools.audio`), run directly. `transcribe(file)` runs `<command> transcribe` and throws on empty or failed output. `speak(text, { voice?, out? })` runs `<command> tts`. |
| `board.js` | Checks the four-section board, writes subjects and watch-outs, closes subjects, and refreshes Timers and Flags. |
| `cli.js` | Entry `ignite`. Home from `RBTV_AGENT_HOME`, or `--agent <slug>` plus `--installation <path>`. Connect, disconnect, and `dreamer run|enable|disable`: see `ignite -h`. |
| `config.js` | `loadConfig(workspace)` reads and validates `<installation>/.rbtv/config/ignite/config.json` and returns it plus `workspace`. `envValue` and `slackToken` resolve named environment variables (process environment, then `.rbtv/config/env/.env`). `agentHome(config, slug)` and `storePath(config, slug)`; where an agent's folder is comes from cast's `lib/agent.js`. |
| `connect.js` | `ignite connect|disconnect`: turns the `ignite` pack on or off through `rbtv`, creates working files before connecting Slack, and manages the route in `config.json` and an optional timer. It accepts only agents below the installation's `.rbtv/agents/`. Flags: see `ignite -h`. |
| `daemon.js` | No header comment. Exports `start`, `expiredUntilDate`, and `runInstalledDreamer`. Usage line: `daemon.js --installation <path>`. Startup checks each agent's `agent.json` harness on PATH and resolves the app and bot tokens with `slackToken`. An unset variable refuses startup and names the variable. When `dreamer.enabled` is true, the same daemon calls `runInstalledDreamer` for one slot per process in each 03:00 `America/Sao_Paulo` hour. Busy attempts retry on later ticks. The daemon watches for a success older than 48 hours. |
| `deploy.sh` | `deploy.sh <commit>`. Requires `RBTV_DEPLOY` (deploy worktree) and `RBTV_INSTALLATION` (installation root). |
| `dreamer.js` | `runDreamer({ config, openStore?, model?, now? })` processes agents in sequence, validates memory proposals, applies writes, commits net changes, and returns a digest or alert. It locks snapshot reads and publication separately, releasing the lock before every model call. `getState(store)` reads each agent's cursor, success and reported-conflict state; `saveState(store, state, now)` persists it, including a quiet run's success. |
| `history.js` | `historyPath(home, key)` is `<home>/conversations/<safe>/history.md`. `safe` is the key with Windows-forbidden characters replaced by `-`. A folder still named with the raw key is renamed on first access. `writeHistory` regenerates that file from the store. `DEFAULT_HISTORY_WINDOW` is the recent slice in every turn prompt. |
| `ingress.js` | No header comment. Exports `handleEvent`. |
| `memory.js` | Checks injected memory, saves broken copies and loads checked HEAD fallbacks, matches workspace paths, and appends remembered facts to the shared inbox. |
| `memory-write.js` | Installation publication lock, write containment, and symlink/junction rejection for memory and board writers. `runtimeFolder` names `.rbtv/runtime/ignite/`, the one folder where Ignite keeps its operational files in an installation: `memory.lock` (the publication lock) and `daemon.lock` (held by the running daemon; a second daemon for the same installation refuses to start while its holder is alive). |
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
| `test_dreamer.js` | Fixture SQLite stores and disposable Git workspaces; no live model or Slack calls. |
| `test_ingress.js` | Suite for `ingress.js`. No API header. |
| `test_memory.js` | Suite for memory checking, recovery, workspace selection, append concurrency and path boundaries. |
| `test_memory_write.js` | Suite for shared lock roots, release, timeout, stale recovery and competing processes. |
| `test_outbox.js` | Suite for `outbox.js`. |
| `test_prompt.js` | Suite for checked turn memory and canonical-board recovery. |
| `test_slack.js` | Suite for `slack.js`. No API header. |
| `test_store.js` | Suite for `store.js`. No API header. |
| `test_turn_loop.js` | Suite for `turn-loop.js`. No API header. |
| `turn-loop.js` | `runOnce(slug, deps)` is one claimed turn, or a refusal or an empty claim. Refuses when `liveRun()` matches a live pid. `ignite turn` cwd is `realpath(home)`. Every request includes `systemPromptFile` `<home>/agent.md`. An owner message's attachments that were not downloaded are counted and passed to `composeTurn`, never a failure. |

In the tool folder, next to the code: `templates/` and `units/rbtv-ignite-agents.service`. Outside it, in this component: the skill `skills/agent-controls.md`, and the rule `rules/ignite-standing-instructions.md`.

## Contracts

General shape only. Instance ids, token paths, and launch pins are runtime config, never source.

**Installation config.** `<installation>/.rbtv/config/ignite/config.json`, loaded by `capabilities/tools/ignite/config.js`. `loadConfig` adds `workspace` (the absolute path it was read for); that field is not stored in the file.

```
{ "slack": { "team": "<team id>", "botUserId": "<bot user id>", "ownerUserId": "<owner user id>",
    "appTokenEnv": "<env var name>", "botTokenEnv": "<env var name>",
    "ownerTokenEnv": "<env var name>", "stoolsWorkspace": "<stools workspace name>" },
  "tools": { "cast": "<cmd>", "stools": "<cmd>", "audio": "<cmd>" },
  "dmAgent": "<slug>",
  "dreamer": { "enabled": false,
    "model": { "harness": "codex", "model": "gpt-6.1-sol", "effort": 3 } },
  "routes": { "<channel id>": "<agent slug>" } }
```

`dreamer.enabled` is an optional boolean, default false; unknown Dreamer settings are refused. Both the nightly runner and watchdog remain off until it is true. `dmAgent` may be absent. A direct message with none configured is refused (`config.dmAgent required`). Tokens are not in this file. `slackToken` reads the named variable from the process environment, then from `<installation>/.rbtv/config/env/.env`. An unset variable the daemon needs refuses startup and names the variable; the value is never logged. Each agent's harness, model, and effort live in that agent's `agent.json`, not here. Source MUST NEVER hardcode them.

`dreamer.model` is required when `dreamer.enabled` is true: `loadConfig` refuses the configuration without it, naming the key and an example value. Source holds no model used at run time; `DREAMER_MODEL` in `config.js` is only the value `ignite dreamer enable` records when the key is absent. The object requires exactly three fields: harness `codex`, `opencode` or `claude`, a nonempty model name without whitespace or a leading dash, and integer effort 1–5 (cast's numeric rung). Invalid and unknown fields fail config validation; cast resolves model availability and effort support at invocation. Both manual and nightly consolidation pass these settings to `castProposal`, independently of agent launch settings. `castProposal` starts cast with the installation as its working directory, so the installation's model selection applies, and passes a temporary folder as the launch folder with the task text in `task.md`; it removes that folder afterwards.

**Agent home.** `<installation>/.rbtv/agents/<slug>/`:

| File | Content |
|---|---|
| `agent.md` | The agent's instructions. Every turn passes this absolute path as `systemPromptFile` on the `ignite turn` request. Ignite does not write a standing-instructions `CLAUDE.md`. rbtv's marked `agent` section and installed units are the instruction files. |
| `agent.json` | `{ "name", "description", "harness", "model", "effort", "voice"?, "files", "packs" }` — the one agent-wide configuration record. Ignite reads it only through cast's `lib/agent.js` (`readAgent`): the turn's launch values and voice, the startup harness check, the voice of a spoken reply, and whether the `ignite` pack is on. `harness`, `model` and `effort` are required; a record cast would not launch stops the turn. |
| `settings.json` | This agent's own settings — see "Capabilities vs settings" below. How install seeds it: see `ignite -h`. |
| `_artifacts/board.md` | Tracked short-term memory: subjects, watch-outs, generated Timers and Recently closed |
| `memory/` | Tracked learned rules and topic files, written by the dreamer; `learned.md` is injected every turn |
| `state.sqlite` | The store. Authoritative |
| `conversations/<windows-safe key>/history.md` | Derived full thread history. Folder name is the key with `:` and other Windows-forbidden characters replaced by `-`. Regenerable from the store |
| skill loaders | Written per harness by `rbtv agent add` |

## Capabilities vs settings

Follow [Capability](../../rbtv/capabilities/glossary/capability.md) for reusable instructions and [Choosing where to build](../../rbtv/capabilities/choosing-where-to-build.md) for their component placement. They carry no agent-specific installation path, account or owner value. Agent-specific values belong in [Settings](../../rbtv/capabilities/glossary/settings-json.md), referenced from the prompt. Tools take their settings and state paths as explicit arguments or environment variables, not hardcoded paths. [Agent](../../rbtv/capabilities/glossary/agent.md) owns which agent-folder files are shared through git.

**Conversation key.** `<teamId>:<channelId>:<rootTs>`, DM and channel alike. The mapping key → agent is persisted.

### Dreamer watch-outs and cursors

The dreamer folds watch-outs into `[correction]` rules with a `Why:` clause. A watch-out whose provenance has no link keeps its original date and gains this agent's Slack thread links, each backed by the fold operation's unread owner rows. Existing linked provenance must stay unchanged. A linked watch-out needs matching unread owner thread evidence; an unlinked one needs an unread owner thread to attach. Without that evidence or an existing duplicate rule, it stays on the board and consolidation reports the conflict once. Every foldable watch-out left on the board refuses the run.

Inbox lines are explicit owner remember requests. For filing into profile, knowledge or entities, operation `sources` accepts this agent's exact inbox line as well as unread owner rowids. The destination record retains that line's provenance, even without a thread link, and the inbox removal names the destination and replacement. No unread owner row is needed. This exception does not turn other memory or inbox text into evidence for learned rules.

When an inbox line or watch-out states a fact already recorded at its filing destination, the model can remove it without writing a new record. Use `op: "supersede"`, reason `file` for inbox or `fold` for watch-outs, and a removal `{text, to, replacement, duplicate: true}`: `to` names the existing file and `replacement` is its exact existing bullet, including provenance. Code verifies the bullet exists in the proposal's input snapshot and remains in the result. Inbox duplicates still cite this agent's exact line in `sources`; watch-out duplicates need no unread owner rows. The model judges whether the facts match and explains that judgment. Existing provenance stays unchanged. Duplicate and ordinary removals may share an operation, and the digest lists each duplicate as `already known` with its destination.

Each agent's SQLite `settings.dreamer.cursor` advances to its run-start message-rowid ceiling after a successful Git commit or after applied writes already match HEAD, and only if that agent submitted an operation or had no unread owner rows. An agent with unread owner rows and no operations keeps its cursor even when another agent caused the writes, so those rows return next run. A run with no applied writes advances no cursors.

After writing, the dreamer checks `git diff --quiet HEAD -- <explicit paths>` and whether any of those paths is untracked. If the tracked paths have no net change and no new file needs tracking, it skips the commit, returns the current HEAD as `commit`, and updates cursors and `lastSuccessAt` as for a committed run. `changed` remains true because working files changed, and the digest retains operation explanations and `already known` entries. New untracked destinations still require a commit. A commit failure reports only `git commit failed (nothing to commit)`, `git commit failed (index lock)`, or `git commit failed (other)`, never raw Git stdout or stderr; it rolls back its writes and leaves cursors and success timestamps unchanged.

Dreamer takes `.rbtv/runtime/ignite/memory.lock` to read each snapshot, then releases it before model calls. Publication reacquires it for the final unchanged-since-read comparison through writes, commit, cursor updates and any rollback. A changed snapshot releases the lock and retries once from a fresh snapshot. `remember` and every board write keep the same lock for the whole of their own read/modify/write; `schedules-due` takes it only for its board refresh. Acquisition uses exclusive file creation, retries every 25 ms for up to about 5 seconds, and records the holder pid, hostname and a unique token. A lock is reclaimed only when older than 60 seconds, its hostname matches this host, and `process.kill(pid, 0)` fails with `ESRCH`. A live holder, an unknown or foreign owner, or any other liveness error keeps the lock. `runInstalledDreamer` keeps the lock only for its initial work check and any quiet success update, then releases it before calling `runDreamer` or delivering outbox notices. Manual and nightly runs use these same lock boundaries; overlapping proposals are checked again under the publication lock. Inbox and board writes reject symlink or junction parents and leaves before they open a file, and use no-follow open flags where supported.

Before a commit, rollback compares exact bytes left by each write, including a failed write, truncate, or close. It restores existing files and removes newly created files only while those bytes still match, preserving later concurrent edits. Partial UTF-8 bytes are compared as buffers so a decoding failure cannot prevent restoration.

### Dreamer scheduling and delivery

`runInstalledDreamer` in `daemon.js` is the one Dreamer run. The daemon calls it when `dreamer.enabled` is true; `ignite dreamer run` calls the same function even when that setting is false. `dreamer.enabled` defaults to false and gates the daemon's runner and watchdog, not the command. The daemon reloads config each tick. Each agent's `settings.dreamer_enabled_at` records the current enabled period, survives enabled restarts, and resets when a disabled tick is observed. The watchdog measures from the later of that timestamp and last success, so disabled time never contributes to its 48-hour threshold. When enabled, the daemon checks the 03:00 `America/Sao_Paulo` hour once per slot within the process, then calls `runInstalledDreamer`. A busy result clears the slot reservation so the next tick in that hour can retry after the lock is released. A non-busy result consumes the slot. The command does not read or write that slot. An eligible owner message newer than an agent cursor, any inbox line, or an expired memory record selects a cast proposal call using `dreamer.model` (default `codex gpt-6.1-sol 3`). Agents run in sequence. Expiry takes the greedy body before the last dated provenance tail, then recognizes only a final valid `until YYYY-MM-DD` with an optional period; board state lines without provenance use the same rule. The date must be earlier than the Sao Paulo local date.

A quiet run has no unread owner row, no due expiry, an empty inbox, and no watch-out that can be folded with available owner thread evidence. `runInstalledDreamer` directly updates every configured agent's `settings.dreamer.lastSuccessAt`, bypassing consolidation and the model, without changing cursors, commit references, memory bytes or reported conflicts. It makes no commit or digest. A deferred watch-out alone does not prevent quiet success.

Consolidation returns new conflict strings in `digest.conflicts` without saving them as reported. The shared run enqueues a digest or failure notice on `dmAgent`'s outbox. Required enqueue errors, including a missing `dmAgent` or DM agent store, return `ok: false` with a non-null `error`, retaining the consolidation's `changed` and `alert` fields. Only when that consolidation's own delivery call confirms its digest delivered does it add new conflict strings to each configured agent's `settings.dreamer.reportedConflicts`; absent lists in older state start empty. If delivery is not confirmed, the conflicts remain unreported and are included again on the next consolidation that finds them. `ignite dreamer run` does not call Slack, so it cannot confirm delivery and leaves new conflicts unsaved; the running daemon delivers the queued outbox row but has no conflict metadata to save. Only a later consolidation whose own digest delivery is confirmed saves those conflicts. A quiet run still bypasses consolidation. The model sees that history, and code removes previously reported or duplicate conflicts from the digest. A digest is returned only for changed files or new conflicts. A digest, failure, or 48-hour liveness warning goes through one persisted Slack thread on `dmAgent`; `settings.dreamer_digest` contains the delivered conversation key. All daemon delivery paths, including the regular drain and turn pump, save it on confirmed Dreamer outbox delivery; later notices reuse it. No second systemd unit exists.

`ignite dreamer run [--installation <path>]` is one shot. It prints one JSON line: `{ok, busy, quiet, changed, enabled, digestQueued, noticeQueued, delivered, conflictsSaved, alert, error, note}`. `note` is `dreamer.enabled is false; ran because this command was called` when the setting is false, otherwise null. Installation/config resolution and run-setup failures also emit exactly one JSON line with `ok: false` and a non-null `error`; `enabled` is null when config could not be loaded. When another process has the installation lock, the command returns `busy: true` and does not start a run. Exit 0 when `ok` is true and there is no alert, busy result, or error; otherwise exit 1. The installation is `--installation`, the installation containing `RBTV_AGENT_HOME`, or the walk up to `.rbtv/config/ignite/config.json`.

`ignite dreamer enable|disable [--installation <path>] [--json]` sets `dreamer.enabled` through `updateConfig`, which validates and writes the whole configuration atomically, so every other setting is preserved. `enable` also records `dreamer.model` when it is absent. A call for the state already in force writes nothing. Both report the installation, the resulting state and the model; `disable` keeps `dreamer.model` and does not cancel a consolidation in progress. `ignite dreamer run` is refused with `ok: false` and an `error` naming `dreamer.model` when that key is absent. The setting is installation-wide; the command has no per-agent form and no access check.

`digestQueued` is true only for a queued consolidation digest; `noticeQueued` is true only for a queued failure notice. Both are false on quiet, busy, setup-failure and enqueue-failure results. `delivered` applies to either kind and is false when the manual command only enqueues it. The watchdog's `dreamer-watchdog` JSON log also reports `digestQueued: false`, `noticeQueued` and `delivered` for its liveness notice.

When cast fails, the returned `alert`, owner notice and daemon's `dreamer` log `message` contain only a fixed cause: `model out of credits or spending limit` for stderr matching `spending-limit`, `credits`, `insufficient balance` or `quota`; `model rate limited` for `rate limit` or `429`; `model timed out` for a timeout or terminated call; `model authentication failed` for `401`, `403`, `unauthori` or `invalid api key`; otherwise `model failed (exit <code>)`, with `unknown` when no safe exit code is available. Matching is case-insensitive, in that order. Raw stderr, command errors and model stdout are never copied into those surfaces. Failed consolidation keeps cursors and success timestamps unchanged.

### Conversation and work state

A Slack thread is one conversation. A reply uses the thread's root message timestamp as `rootTs`; a new top-level message uses its own timestamp, so it starts a separate conversation even in the same channel. Each agent has its own `state.sqlite`, and work records belong to a conversation key, not to the channel or the agent as a whole.

An owner message in a conversation reuses its latest work record unless that work is `completed` or `stopped`. Those terminal states cause a new work record linked to the old one as its predecessor. A held work record is reused but remains blocked until an explicit retry. A new conversation starts with a new work record. Old records are retained; neither a new thread nor completion deletes their summaries. A new work record starts without a saved summary or next step, although earlier messages in the same thread remain in its history.

For each turn, the runtime puts the current work's `summary`, `nextStep`, `workers`, and `outputs` in the prompt, along with `.rbtv/memory/profile.md`, `<home>/memory/learned.md`, `<home>/_artifacts/board.md`, `.rbtv/memory/_artifacts/index.md`, and `.rbtv/memory/inbox.md`, the triggering input, recent messages, and the path to full conversation history. Workspace notes under `.rbtv/memory/workspaces/` are injected only when the turn working directory is under one of their installation-relative `paths:`. Missing or rejected files load a checked HEAD fallback and alert; invalid working bytes are saved first, and no valid fallback yields a visible missing note without blocking the turn. Runtime never reads a legacy `<home>/board.md`; `connect` may copy it to an absent canonical path, without reshaping. It does not put every open work record in that prompt; `ignite work status` lists them when needed. The agent reports updated work fields and a disposition in RESULT_FILE. The runtime stores those values: `continue` requires a next step and queues another turn; `waiting_owner` and `waiting_workers` pause automatic continuation; `completed` closes that work. Completion does not erase a supplied `nextStep`, but only `continue` queues a turn from it. These fields report the agent's assessment; the runtime validates the result shape and nonce, not whether the underlying task is actually done.

**Turn.** The runtime claims one queue entry per agent (one active turn per agent), composes the prompt (triggering input, board, work state, recent history window, full-history path), and runs it through `ignite turn --request <file> --result <file>`. The request includes `systemPromptFile`, the absolute path of `<home>/agent.md`. Each invocation gets a fresh nonce and an output path. The agent MUST write JSON at that path:

```
{ "nonce": "<given>", "disposition": "completed|continue|waiting_owner|waiting_workers|stopped",
  "summary": "…", "nextStep": "…", "workers": [ { "ref": "…", "kind": "…" } ], "outputs": ["<path>"],
  "replies": [ { "text": "…", "audio": false, "files": ["<path>"] } ] }
```

A normal exit without valid output is a technical failure. The runtime delivers `replies` through its outbox. Technical failure: 3 total attempts, retry delays 5 s then 30 s, then a durable hold (agent-wide if the launch itself fails, else work-scoped) plus a Slack blocker notice. Timers and restarts NEVER remove a hold.

**CLI.** `ignite`, entry `capabilities/tools/ignite/cli.js`. Inside a turn the runtime sets `RBTV_AGENT_HOME` and `IGNITE_CONVERSATION`. Outside a turn `--agent <slug>` selects the home. Subcommands include `schedule add|list|change|cancel`, `work status|retry|resume|stop`, `wake`, `post [--thread <key-or-root-ts>]`, `board write|close`, `remember <text>`, `dreamer run|enable|disable`, `connect`, and `disconnect`. `dreamer run`, `dreamer enable` and `dreamer disable` do not need an agent; their contract is under Dreamer scheduling. Schedule add/change/cancel and connection timer binding require an existing, valid canonical board and safe write path before they open SQLite; missing or invalid boards refuse with the board path and leave SQLite unchanged. If a committed add/change/cancel or connect/disconnect timer change cannot refresh the board, the command exits 0 with the schedule id(s) and `committed; board refresh pending`; JSON adds a `warning` field to the normal success payload. The next board write/close, schedule tick or turn refreshes from SQLite. Board write/close reads an existing agent store and renders Timers and Flags under the same lock before saving; it never creates a database. `post --thread` joins a known thread's history. `board` writes use the checked canonical path; `remember` appends to the shared inbox. Flags are `ignite -h`.

Operator steps — deploy, status, inspect, hold repair — are `runbook.md`.
