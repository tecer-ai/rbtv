# cast

Launches ONE headless agent turn in any of three harnesses through one CLI. The caller's
process runs the launch (foreground, blocking). Sessions are
addressable after the fact: `sessions` lists what ran in a folder, `resume` sends one more
turn into an existing session.

## Usage

```
cast --agent AGENT [-p TEXT | -f FILE] [--headed] [--dry-run]
cast <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) [-s TEXT | -S FILE | --rogue PROMPT-FILE] [--headed] [--dry-run]
cast resume <harness> <session-id|last> [launch-folder] (-p TEXT | -f FILE) [--dry-run]
cast sessions [harness] [launch-folder] [--json] [-n N]
ignite turn --request FILE --result FILE
cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image [--input-image PATH ...]] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
cast route --access open|bounded --type code|text --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps image] [--explain]
cast route --caps image
cast route --batch <agents.json | -> [--explain]
cast doctor [--json]
cast list [--agents [--full] | --agent NAME] [--target FOLDER] [--json]
cast models list [--selected | --supported | --catalog] [--json]
cast models add HARNESS MODEL [--dry-run] [--json]
cast models remove HARNESS MODEL [--force] [--dry-run] [--json]
cast models set HARNESS MODEL [--use route|panel|off] [--quality-override Y|N] [--price-override Y|N] [--level LEVEL] [--dry-run] [--json]
cast models update [HARNESS MODEL] [--dry-run] [--json]
cast models defaults [--route price|quality] [--fallback off|price|quality] [--dry-run] [--json]
cast -h | --help
```

| Arg | Meaning |
|---|---|
| `harness` | `claude` \| `codex` \| `opencode` |
| `model` | that harness's model, SHORT name — the provider prefix and the `claude-` prefix are dropped: `opus-5-5` (not `claude-opus-5-5`), `glm-5.3` (not `zai-coding-plan/glm-5.3`). See `cast models list` for the selected models; a long id is refused with the short one suggested |
| `effort` | integer 1-5, the universal dial |
| `launch-folder` | working directory for the agent, resolved relative to the caller's CWD; MUST already exist |
| `-p TEXT` | the task of this launch, as literal text |
| `-f FILE` | read the task from a file; `-f -` reads it from stdin |
| neither, with `--agent` | the task is `task.md` in the agent folder; every other form requires `-p` or `-f` |
| a task with no text | refused with exit 2, by a launch, a `cast resume` and a `--dry-run` alike: text that is empty or only whitespace is no task. The refusal names where the text came from: `the -p text`, `the -f file FILE`, `standard input (-f -)` or `task.md in <agent folder>` |
| `--dry-run` | print the composed argv as JSON and exit 0 without launching |

The first form launches an rbtv agent and is the form to use for any agent launched more than
once: its folder holds the prompt and the harness, model and effort. The second form is for a
worker chosen by `cast route`, or a throwaway. To write an agent, make an rbtv agent in any
folder as [Agent](../../../../rbtv/capabilities/glossary/agent.md) says, then `rbtv agent add FOLDER
--harness H --model M --effort E` and `cast --agent FOLDER -p "..."`; `cast -h` prints the same
route with the absolute path of the `framework` skill.

Run `cast models list` for the live model/effort table (generated from the tool's own spec; `cast -h`
names that command and prints no model). Pass the NUMBER as `<effort>`: the launch path accepts
only the integer, and the rung words are labels, never values a bare launch takes.

A launch names a model that is **supported** (a row of `supported-models.js`) and **selected** in
the installation that holds the launch (a row of its [model catalog](../../glossary/model-catalog.md);
the refusals are under [the launch check](#the-model-catalog-and-the-launch-check)). The installation is
found from the agent's folder for `--agent`, and from the current folder for every other launch,
`cast api` included. A model that is not selected is refused at exit 2, and the refusal names the
command that selects it: `cast models add HARNESS MODEL`.
`cast doctor` is the pre-launch view of cast's own data: which harness programs are on `PATH`, and,
for each selected model (the models `cast models list` shows for the installation of the current
folder, cli and api), whether the login of its provider is present. For claude and codex that is the login files the harness keeps in the home folder; for
every other provider it is the key variable in the OS environment or in the installation's
environment file, or the provider's entry in opencode's store, as `providers.json` says. It reads
local files and the environment only: no network call, no other program started, and no key, token
or account name printed. A present login is not proof that the account has credit left: the report
ends with `rbtv providers list` and `rbtv providers usage`, which answer for accounts, saved logins
and usage limits. Each model line says where its login was found, or what was looked for. A model
catalog that cannot be read is reported in place of the models, still at exit 0. When cells of the
installation's own model catalog differ from the shipped one in the columns rbtv proposes, one line
gives their number and `cast models update --dry-run`, which lists them.
`cast doctor --json` prints `{installation, selection, catalog_problem, catalog_drift, harnesses: {name: path},
models: [{harness, model, provider, login, via, reason}], next: [command, ...]}`; `selection` is
the installation's model catalog, `null` while the shipped one is in force. It takes `--json` and
nothing else: any other word is refused at exit 2.

## Effort mapping (1-5 → the harness's own ladder)

Each (harness, model) has its own rung ladder in `capabilities/tools/cast/supported-models.js`. Rule:
`rung = ladder[min(N, ladder.length) - 1]`
— asking for 5 on a 3-rung ladder clamps to that ladder's top rung, never a refusal. An `inert`
ladder (`haiku-4-5`) accepts any N and emits no effort argv at all. `cast models list` prints the
resolved mapping per model with the clamping folded in (e.g. `glm-5.3  1=high 2-5=max`), so the
number-to-rung answer is never inferred. The positional `<effort>` a bare launch takes is an
integer 1-5 only — a rung word is refused at exit 2 — because the words `cast models list` prints look
like passable values but are labels.

## Messaging a session — `sessions` and `resume`

Discovery is pull-based: `sessions` prints nothing at launch and reads no registry of its own —
the harnesses' own session stores ARE the registry, keyed by launch folder. `resume` is a launch in
its own right, though, so it DOES emit a `cast: handle` line and register with `cast monitor`'s
handle registry, exactly like a bare launch — the model/effort a resumed session runs
with is not cast's to name, so the handle's `model` field reads `resume` instead of a model name:

| Harness | Store read by `cast sessions` | `resume` argv |
|---|---|---|
| claude | `~/.claude/projects/<encoded-folder>/<id>.jsonl` — filename is the id | `claude -p --resume <id>` (`last` → `--continue`) + `--permission-mode bypassPermissions` |
| codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` — id + cwd in the first-line `session_meta` (walked newest-first, stops at `-n` matches) | `codex exec resume <id\|--last>` + `-c sandbox_mode=danger-full-access -c approval_policy=never --skip-git-repo-check --dangerously-bypass-hook-trust` |
| opencode | `opencode session list --format json` run with cwd = folder, rows filtered on their `directory` field | `opencode run -s <id>` (`last` → `-c`) |

`resume` runs with cwd = launch-folder (that is also what scopes every harness's `last`), takes the
message via `-p`/`-f` on stdin like a launch (an empty message is refused as an empty task is), and re-passes the permission/sandbox flags — those
are per-invocation, not per-session. The resumed session keeps its own model/effort; `-s`/`-S` and
`--headed` are refused. `-n` caps `sessions` PER HARNESS (default 10), newest first; `--json` gives
`[{harness, id, started, label}]`. The label is human-readable session identity: opencode's stored
`title`; for claude/codex a ≤60-char excerpt of the first real user message (injected `<...>`
wrapper blocks skipped) — for cast-launched sessions that is the `-p` task itself. Known ceiling: two same-harness sessions launched into the same folder
in the same minute are distinguishable only by trying them — no id is captured at birth (codex and
opencode only surface theirs inside their `--json` output streams, which cast passes through
untouched). `ignite turn` is the exception: it returns an exact id for that invocation (see below).


## Agent launches (`--agent`, `--rogue`)

`cast --agent AGENT [-p TEXT | -f FILE]` runs an agent folder: a folder that contains both `prompt.md` and
`agent.json`. AGENT is a name, looked up as `<installation>/.rbtv/agents/AGENT/` from the current
folder upward, or a path to the folder (a value containing `/` or `\`, or `.` or `..`, relative to
the current folder). The folder is the working folder. `agent.json` gives the harness, model and
effort, all three required (effort as the model's own word, such as `high`, never a number; a
record without one is refused); none of them may be given on the command line:
that is refused, and the refusal names `rbtv agent configure AGENT` as the way to change them.
`prompt.md` is the system prompt. It has no frontmatter: the body starts at the first line, and the
agent's name lives in `agent.json` only. A frontmatter block that still opens the file is ignored at
the launch and reported by `rbtv doctor`; remove it. The launch sets
`RBTV_AGENT_HOME` to the agent folder for the harness process. A folder that contains only one of the two
files is refused by name, so a broken agent is never launched half-read; a folder that holds
`agent.md` in place of `prompt.md` is refused with the `git mv` command that renames it. A launch takes no
`--target`: that option belongs to `cast list`, and an agent outside `.rbtv/agents/` is launched by
its path.

The task of an `--agent` launch comes from one of three places. `-p TEXT` or `-f FILE` gives it, and
either one wins whether or not the folder holds a `task.md`. With neither, cast sends `task.md` in
the agent folder, read exactly as `-f <agent folder>/task.md` reads it. With neither and no
`task.md`, the launch is refused with exit 2 and names the absent file:
`refused: no task: pass -p TEXT or -f FILE, or write task.md in <agent folder>`. A task that is empty
or only whitespace is refused with exit 2 from each of the three places, and the refusal names the
one it came from: `refused: the task is empty: task.md in <agent folder> holds no text`, or
`the -p text`, `the -f file FILE` or `standard input (-f -)` in place of the `task.md` clause. An agent launched
once keeps its task in that file, so the folder holds everything the launch needs; an agent launched
with different tasks is given each one with `-p` or `-f`. `--rogue`, `cast resume` and the
`<harness> <model> <effort>` form have no agent folder and always require `-p` or `-f`.

`--rogue PROMPT-FILE` runs a rogue agent file that is not an agent folder: the file's body, without its
frontmatter, is the system prompt, and the launch folder is the usual one. It sets no
`RBTV_AGENT_HOME`. Harness, model and effort are always given on the command line for `--rogue`.

The system prompt rides each harness's strongest channel, the same as `-s TEXT`/`-S FILE`:

- **claude** — `--append-system-prompt <text>`.
- **codex** — `-c developer_instructions=<text>`.
- **opencode** — no system-prompt channel, so the text is prepended to the first message with
  this wrapper:

  ```
  <system prompt>

  ---

  The text above is your system-prompt directive for this run — it rides this first message
  because your harness carries no system prompt. The user's message follows:

  <task>
  ```

`-s`/`-S` cannot be combined with `--agent`/`--rogue`. Every Codex launch also passes
`-c project_doc_max_bytes=131072`, because Codex joins every `AGENTS.md` from the project root down to
the working folder and cuts the text past its 32 KiB default.

Every Codex launch and every Codex `resume` passes `--dangerously-bypass-hook-trust`, and so does
every Codex turn the Ignite waking service runs through `ignite turn`. Codex runs a
hook only when it holds a stored approval of that hook ("persisted hook trust" in Codex's help); a
headless run cannot give that approval and skips every hook without a message. With the option,
the hooks in the launch folder's `.codex/hooks.json` run. The cost: cast and `ignite turn` skip
Codex's approval for every hook file Codex reads in that launch, so any hook file in the launch
folder runs unreviewed. Read a folder's `.codex/hooks.json` before launching Codex, or running an
Ignite agent on Codex, in a folder whose content you did not write.

`ignite turn` takes its standing prompt the same way: the `systemPromptFile` in its request is read
with its frontmatter removed, and the model receives the body only.

### Finding the agents: `cast list`

`cast list`, or `cast list --agents`, shows the rbtv agents `cast --agent NAME` can launch from the current folder: the
agents in the nearest `.rbtv/agents/` folder above it. For each agent it prints the name, harness,
model, effort, Ignite (`yes` when the agent's `ignite` pack is on, which `ignite connect` does) and
the description from `agent.json`. The description is shortened to fit the line; with `--full`, or on
a terminal too narrow for the table, each agent is a labeled block with its whole description. An agent that cannot
be launched is named with the reason, and is never a row of the table: an unreadable record, or a
model the launch check refuses, as in `tiny: cannot be launched: model not selected: cast models add claude haiku-4-5`.
`--json` prints `{folder, agents}`, where such an agent is `{name, home, problem}`. The models are
`cast models list`: `cast list --models` is refused and names that command.

`--target FOLDER` lists the agents of FOLDER instead of those above the current folder. FOLDER is
read as the first of three things it is: an installation (it holds `.rbtv/`), whose agents are those
in its `.rbtv/agents/`; an agent folder, which is that one agent; or a folder that holds agent
folders, such as the `agents/` folder of a plan, whose agents are those folders. A FOLDER that is
none of the three is refused, exit 2. `folder` in the result is where the agents were read from.
With `--agent NAME`, NAME is a name among those agents, and a path is refused. One function reads
the option, `targetAgents` in `lib/agent.js`: `spark list --target FOLDER`, `spark AGENT --target
FOLDER` and `rbtv agent list --target FOLDER` take the same three folders through it.

`cast list --agent NAME` shows one agent in full; AGENT is a name or a path. Besides its folder and
whole description it lists what is installed in the agent, each under the name `rbtv show` takes:
every pack that is on, one per row, with the skills, rules, commands, MCP servers and hooks that
pack installs on a row each under it; then, by kind, what is installed outside a pack. A unit a
pack installs is shown with its pack only. The list is followed by the two commands that tell
more about a name (`rbtv show --pack NAME` for a pack, `rbtv show NAME` for the rest), each with
`--target` and the agent's folder: without it `rbtv show` answers for the installation, where the
same unit may not be installed. Only the
installer knows what a pack brings in and what kind each unit is, so cast asks it:
`rbtv list --installed --target <agent folder>`. This is the one place where cast receives from
`rbtv`. Without `rbtv` on PATH, or when it refuses, the view says so and shows the rest. `--json`
prints the agent's object with `installed`: `pack` is a list of `{name, skill, rule, command,
mcp-server, hook}`, and `skill`, `rule`, `command`, `mcp-server` and `hook` list what is outside a pack; or
`installed: null` and the reason in `installed_problem`. Every form only reads.

`lib/agent-list.js` builds the list, and it is the only list of agents: `cast list --agents` shows it
to an agent, `spark list` shows it to a person, and `rbtv agent list` runs `cast list --agents`. The
three print the same text, so a line that names a command names all three. Each command words
its own refusals.

## Execution

The child is spawned with `cwd = <launch-folder>` for every harness (the `--cd`/`--work-dir` flags
are belt-and-braces on the harnesses that have them). The (possibly descriptor-prepended) task is
written to the child's stdin and stdin is then closed. Stdout/stderr are inherited. `cast`
exits with the child's exit code; where a [fallback](#fallback) ran, that is the last run's.
A child that exits without reading the task still ends the launch with its own exit code.

**Output format is deliberately the harness default — no `--output-format`/`--json` flag on a bare
launch (owner-ruled 1a, 2026-08-18, closing a measured divergence with ignite).** `ignite turn` is the exception: it captures stdout to a file and passes those flags so it can read an exact session id. The contract for every other verb is
"child stdout IS the plain-text completion report", and callers rely on it. Consequences and
rationale, per harness: codex and opencode stream their output natively, so their logs grow live;
**claude's `-p` buffers stdout until exit — a claude launch's log is 0 bytes for the entire run
and that is normal**, never a liveness signal (use `cast monitor`, which reads the transcript, and
the `cast: handle` line's minted `--session-id`). ignite launches the same harnesses with
structured-output flags (`stream-json` for claude, `--json` for codex) — that is not a
contradiction: ignite needs to EXTRACT the session id from the child's stdout, while cast obtains
session identity without stdout (claude: minted id; codex: rollout store; opencode: directory).
Adopting ignite's flags here would multiply stdout ~380x (measured) and break the report contract
for no remaining gain.

## Fallback

A headless launch whose model fails to start can run another model in its place. The installation turns this on and says how to rank, with `fallback` in its defaults: `off` (cast's own value), `price` or `quality`, set by `cast models defaults --fallback VALUE`.

A launch fails to start in two cases: the harness program cannot be started, or the harness exits with a failure, and without a signal, less than 15 seconds after cast started it. A harness that cannot reach its model ends in 2.4 to 3.2 seconds on `claude`, `codex` and `opencode` (measured 2026-10-07 with a model name no provider has). A provider that refuses a launch for a spending limit ended `opencode` with exit 1 in about 4 seconds (measured 2026-10-08 in an Ignite turn on `grok-4.7`, which then ran its first fallback); the same refusal on `claude` and `codex` is not measured. A failure after 15 seconds can follow work the agent already did, and a second run would repeat that work, so the launch ends with that failure and exit code. A job that stays alive without progress is not a failure to start: `cast monitor` reports it and nothing relaunches it.

The candidates are the other models of the failed model's level in the [model catalog](../../glossary/model-catalog.md): `cli` rows with `use` `route` whose login is present, models of the provider that just failed included. A model listed at two levels falls back inside the higher one. They are ranked as `cast route` ranks a level, overrides included: by `price`, cheapest first, a row with a blank cost left out; by `quality`, on the reasoning and coding scores added, because a launch does not say which kind of task it runs. The order does not depend on the failed model, so with three models at three prices a failure of the middle one tries the cheapest first and the dearest second.

The launch tries the candidates in that order, each in the same launch folder with the same task and the same system prompt, while each one fails to start. The first one that starts is the launch: cast exits with its exit code, whatever that is. A fallback launches at the effort the launch asked for. A dial number is passed as given. An agent's own rung word becomes its place on its model's ladder, and the top rung becomes 5, so the highest effort stays the highest; a model with no dial gives 3.

A fallback never leaves the level. When no candidate starts, or the level holds none, the launch ends with the last failure and exit code, and standard error names what was tried and the best model of the next level down that holds one, which is not launched:

```
cast: claude sonnet-5-5 did not start (exit 1 after 2s); launching fallback 1 of 2 at level L2 by price: codex gpt-5.6-terra
cast: codex gpt-5.6-terra did not start (exit 1 after 3s); launching fallback 2 of 2 at level L2 by price: opencode glm-5.3
cast: opencode glm-5.3 did not start (exit 1 after 2s)
cast: no model of level L2 started: tried claude sonnet-5-5, codex gpt-5.6-terra, opencode glm-5.3
cast: the next model by price is one level down (L3) and was not launched: codex gpt-6-luna
```

Each run writes its own `cast: handle` line; all carry cast's one process id, and `cast monitor` reads the latest. Standard output holds the report of the run that started, alone: a closing note of a failed run (`cast: no-report`, a provider limit) goes to standard error when another run follows it. When the defaults or the model catalog cannot be read at that moment, one line says so and the launch ends with its own failure.

An rbtv agent's folder holds the installed files of every harness, so an agent that falls back to a model of another harness receives its prompt, its task and the skills, rules, hooks and folder instructions installed in its folder. A harness-native sub-agent is the exception: it exists only for the harnesses it was given a model and an effort for. A folder installed before this was so holds one harness's files until `rbtv agent update AGENT scaffolding` runs.

A launch with `--headed`, a `--dry-run`, `cast resume` and `cast api` never run a fallback. An Ignite turn applies the same rule through `ignite turn`: [Ignite architecture](../../../../ignite/capabilities/tools/ignite/documentation/architecture.md).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | child ran to completion (its own exit code); also `-h`, `doctor`, `list`, `sessions`, and `models` for a result, a change or no change |
| `2` | unknown harness/model, launch-folder missing, effort outside 1-5, bad/missing flags, a task file that cannot be read, a task with no text, any refusal of `models` |

## Spec source

**codex ladders come from the model manifest embedded in the codex binary** — a JSON blob keyed
`{"models": [{"slug": ..., "supported_reasoning_levels": [...]}]}`, extractable with a brace-matched
read of the binary at `~/.codex/packages/standalone/releases/<ver>/bin/codex`. Read 2026-08-12 from
0.147.0 and spot-checked with live `codex exec` runs. Availability is account-dependent and the
manifest does NOT encode it: `gpt-5.2` is listed with visibility `list` yet a live run returns
`400 … "not supported when using Codex with a ChatGPT account"`, so it is excluded. Also excluded:
`gpt-5.4`, `gpt-5.4-mini`, `codex-auto-review` (manifest visibility `hide`). A bad
`model_reasoning_effort` IS rejected by the API (`invalid_enum_value`, supported: none, minimal,
low, medium, high, xhigh, max) — but `ultra`, which sol/terra list as a 6th level, is accepted
without appearing in that enum, so codex translates it client-side. A 1-5 dial cannot reach a 6th
rung, so `ultra` is left out of the table rather than sitting there unreachable.

**opencode ladders are measured, and there are two disagreeing sources — use the right one.** The
authority for a `--variant` value is the `variants` keys in `opencode models <provider> --verbose`,
which is what the running binary validates against. The models.dev model list opencode caches at
`~/.cache/opencode/models.json` carries a DIFFERENT field (`reasoning_options[].values`) that
disagrees — it lists `high,xhigh` for `sakana/fugu`, where the binary accepts `low,medium,high`
(both re-measured 2026-08-12). Never source a ladder from the cache file — the `xai/grok-*` ladders
used to be the one exception (the provider was uncredentialed and so invisible to the binary), and
the cache was wrong there too: it claimed `xhigh` for `grok-4.6`, which the binary does not list.
xai is authenticated via opencode oauth as of 2026-08-13 and both grok ladders are now measured
(`low,medium,high`). A model with no variants at all (`zai-coding-plan/glm-4.7`) is inert: any
effort number, no `--variant` argv.

The (harness, model) → argv/effort table lives in `capabilities/tools/cast/supported-models.js`; the model catalog
(`capabilities/tools/cast/models.csv`, or the installation's own) holds the routing columns. `cast models list` reads the current launch table. Update
`capabilities/tools/cast/supported-models.js` when a harness model or effort ladder changes, then run `test_cast.js` and
`test_route.js`.

## `cast route`

The deterministic worker selector, REDESIGNED 2026-08-20: you answer four questions about the job
and route names ONE `(harness, model, mode, effort)`. It is a pure function of those flags,
the model catalog in force and `capabilities/tools/cast/supported-models.js` — no network, no clock, no randomness, so the same answers
always give the same verdict. The old JSON-task-profile interface is DELETED with no back-compat
path, and with it the boundedness bands, pinned roles, halt seams, stakes tier-up, the haiku
clause, footprint/window gating and evidence ranking.

```
cast route --access open|bounded --type code|text \
           --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps image] [--explain]
cast route --caps image        # short-circuit — no other flag needed
cast route --batch agents.json  # a whole team in one call; `--batch -` reads stdin
```

Three flags are REQUIRED (`--access`, `--type`, `--class`). There are no silent defaults: an
unanswered question is a guess, and a guess is what this command exists to remove. The ONE ruled
default is `--optimize`: omitted, a call ranks as the installation's defaults say (`cast models
defaults --route price|quality`), and where the installation sets none, by **price**, for every
class alike (owner ruling 2026-08-22). Every verdict states the ranking it used in `optimize` and
where it came from in `optimize_from`: `--optimize`, the installation's defaults file, or `cast's
default`.
`cast route -h` IS the interview in full.

A verdict is launched as it stands for one job. For an agent launched more than once, put the
verdict in the agent's record instead: `rbtv agent add FOLDER --harness H --model M --effort E` for
a new agent, `rbtv agent configure AGENT --harness H --model M --effort E` for an existing one.
Route ranks the rows of the model catalog in force; what its columns mean is in [Model
catalog](../../glossary/model-catalog.md), and changing them is [Personalizing the model
catalog](documentation/personalizing-the-model-catalog.md).

| Flag | The question | Effect |
|---|---|---|
| `--access` | Must the agent navigate and DISCOVER files on disk? | `open` drops every api row — an API worker has no disk. `bounded` (known files only, or no disk at all) keeps them. |
| `--type` | Code, or prose/analysis? | Picks the tie-break axis (`coding` vs `reasoning`). **Planning is TEXT**, even for a coding job. |
| `--class` | How bounded is the work? | Picks BOTH the ONE eligible level and the effort (table below). |
| `--optimize` | Cheapest that qualifies, or best that qualifies? (optional) | The selection rule among survivors. Omitted → the installation's default, and price where it sets none, identical to passing that value. |
| `--caps` | A specific capability? (optional) | `image` SHORT-CIRCUITS to the L4 image row and skips every other question. |

| `--class` | Eligible levels | Effort (code / text) |
|---|---|---|
| `planner` | SOTA | 3 / 3 — a **FLOOR** (`effort_is_floor: true`); the CALLING AGENT raises it for criticality, complexity or blast radius. Route does not decide that. |
| `broad` | L1 | 2 / 3 |
| `bounded` | L2 | 2 / 2 |
| `mechanical` | L3 | 1 / 1 |

**One level per class (owner ruling 2026-09-24).** Each class sees exactly one level, so
`--optimize` only reorders rows of that level: a bounded job never reaches an L1 model and only
`planner` reaches SOTA. While `planner` and `bounded` spanned two levels, the price default handed
them the cheaper level's row (planning went to an L1 model). A model the owner wants in two classes
gets one line per level, and its override columns are set per line. haiku is normally routable as L3.

**Price, a total order.** `price`: lowest `cost` → higher score → alphabetical harness, then model.
`quality`: highest level within the class's own levels → higher score → lower cost → alphabetical.
**Default (flag omitted, no installation default) — owner ruling 2026-08-22: PRICE, for every class alike.** It is the
`price` ranking above in every respect — same order, same blank-cost exclusion, same tie-breaks —
carrying its own `"optimize":"default"` trace label so an `--explain` reader can still tell an
omitted flag from an explicit one. An installation default ranks under its own name, after a trace
entry `{"stage":"optimize","action":"default","optimize":…,"source":<the defaults file>}`. This REPLACED the two-band rule of 2026-08-21 (SOTA/L1 on price,
L2/L3 on quality), which is gone: one rule the owner can remember beat two bands. The
class's level is the ONLY thing standing between a job and the cheapest model in the model catalog, which
is what makes level curation load-bearing.

**Blank cells** (the owner fills them over time): a blank `cost` sits OUT of every price-ranked
pick — `--optimize price` AND the default — and stays eligible for `quality` — unknown is not cheap; a blank `level` excludes the row entirely; a
blank score reads as 0 in tie-breaks. Every exclusion appears in `--explain`.

Pipeline order: parse flags → load the model catalog in force → join `supported-models.js` → availability →
image short-circuit → access → caps → class levels → optimize → effort. `--explain` attaches the full
trace with a reason on every dropped row.

**Batch.** `--batch agents.json` (or `--batch -` for stdin) routes a whole team in ONE call — a
planning agent designs every agent at once and needs one deterministic assignment table, not N
shell calls. Input is a JSON array of agent objects (or `{"agents":[...]}`); each agent is the
interview as an object with a unique `name`, the same vocabulary and required-ness as the flags
(`"caps":["image"]` short-circuits the same way), and an unknown key is a refusal. The load of the
model catalog and its join with the supported models happen ONCE for the batch; every agent still goes through the same selector,
so a batch of one produces exactly the flag form's verdict. Output is one object with the agents in
INPUT order, the name mapping each verdict back:

```
{"verdict":"route-batch","agents":[
  {"name":"planner","verdict":"route","harness":…,"model":…,"mode":…,"effort":…,"effort_is_floor":…,"alternates":[…]},
  {"name":"fixer","error":"zero_candidates","details":"…"}]}
```

Exit 0 only when EVERY agent routed; 1 when any agent errored. A per-agent error never aborts the
batch — every agent's problem lands in its own entry so the whole plan is fixed in one pass. A bad
envelope (unreadable/unparseable input, empty stdin, empty or duplicate-named agent list) refuses
the whole call with one `{"error":"malformed_request","details":[…]}` and routes nothing.
`--explain` attaches each agent's own trace to its entry. `--batch` combines with none of the
interview flags, nor with `--caps`.

| Verdict | Shape | Exit |
|---|---|---|
| route | `{"verdict":"route","harness":…,"model":…,"mode":"cli"\|"api","effort":1-5,"effort_is_floor":false,"optimize":"price"\|"quality","optimize_from":…,"alternates":[{"harness":…,"model":…,"mode":…}]}` | 0 |
| route-batch | `{"verdict":"route-batch","agents":[{"name":…,"verdict":"route",…} \| {"name":…,"error":…,"details":…}]}` — agents in input order | 0 only when EVERY agent routed, else 1 |
| error | `{"error":"malformed_request"\|"zero_candidates"\|"no_models"\|"bad_defaults","details":…}`; `bad_defaults` is an installation defaults file that cannot be used | 1 |

The top-level worker IS the verdict — launch it. `alternates` carries the next two of the same
ranking (fewer if the ranking is shorter) as BACKUPS for when the first cannot be launched; they
share the verdict's effort. `mode: cli` is launchable by `cast <harness> <model> <effort>`; `mode: api` is reached by
`cast api` and refuses a launch at exit 2 rather than pretending the model is unknown. `effort` is
a cast 1-5 integer mapped onto the picked row's own ladder at launch — an inert ladder still takes
the number and emits no argv.

Availability is a PRESENCE test, never a spend. Each row names its provider, and
`capabilities/tools/cast/providers.json` says what that provider's login is: its key variable, and
its entry in the harness's own credential store. A claude or codex harness row is always
available (the harness holds its own account login). An opencode row is available when the key
variable is set in the OS environment, else in the installation's environment file
(`.rbtv/config/env/.env`), else when opencode's store holds the provider's entry. An `api` row
needs the key variable, in the OS environment or the environment file. A variable set to an empty
value is not a key. The installation is the first folder, from the folder cast runs in upward,
that holds `.rbtv/config/install.json`; outside any installation there is no environment file. An
absent login drops the row; it is never an error. ⚠ Consequence worth naming:
with no `GEMINI_API_KEY` on the box, `cast route --caps image` answers `zero_candidates` naming the
key — which is the honest answer, not a bug.

### The model catalog and the launch check

The [model catalog](../../glossary/model-catalog.md) is the table of the models an installation selects:
its entry defines the files (the shipped one beside `cast.js`, the installation's
`.rbtv/config/cast/models.csv`, and which is in force), what a row selects, every column, the three
`use` values, the two overrides and a model listed at two levels. A [supported
model](../../glossary/supported-model.md) is a row of `capabilities/tools/cast/supported-models.js`; a
[selected model](../../glossary/selected-model.md) is a supported model with a row in the model catalog
in force. `cast route` joins the two on harness+model, and a row with no supported model is excluded
with a loud stderr warning, because route must never name something cast cannot launch. To choose
the models of an installation, or to make cast support a new model, follow [Personalizing the model
catalog](documentation/personalizing-the-model-catalog.md).

The launch check (`lib/model-catalog.js` `gate`, called from the one lookup every launch goes
through, `lookupModel` in `lib/core.js`) refuses at exit 2 with the reason, `Nothing changed.` and
one next command:

| Case | Refusal · next command |
|---|---|
| not supported, not in the file | `'H M' is not a model cast supports`, with the closest supported name · `cast models list --supported` |
| supported, file present, no row | `'H M' is not selected in <installation>`, naming the file · `cast models add H M` |
| row in the file, not supported by this copy of cast | `'H M' is selected in <file> but this copy of cast does not support it` (the daemon runs its own deployed copy of rbtv) · `cast models remove H M` |
| the file cannot be read as a table | `cannot read the model catalog <file> line N: <why>` · `correct <file>, then run the same command again` |

The installation's file is read strictly, because it gates every launch in the installation, the
daemon's included. Cells are read by header name; a column the header does not carry reads blank
(a blank `use` is `route`, a blank `level` is not routed). An unknown column, a missing `mode`,
`harness` or `model` column, a row whose cell count is not the header's (what a decimal comma
makes), or a blank `mode`, `harness` or `model` cell refuses with the file and the line: a skipped
row would silently unselect a model. `cast route` answers the same failure as
`{"error":"no_models"}`. cast replaces the file in one step (a temporary file, then a rename) and
keeps the file's own line ending.

Each supported model names its provider, a key of **`capabilities/tools/cast/providers.json`**. That file
holds one entry per provider: the lab, the login method (`account` or `api-key`), the key variable
(`env_var`), the harnesses that reach it with the provider's entry in each harness's credential
store (`harnesses.<harness>.store_key`; `harnesses.api` marks a provider `cast api` calls), the
files a [saved login](../../../../rbtv/capabilities/glossary/provider.md#login-and-saved-login) is made of (`saved_login`, only where logins can be saved and switched) and
where its usage figure comes from (`usage`). `stores` says where a harness keeps its credentials.
Add a provider there before a supported model names it; `test_route.js` fails on a row whose
provider or harness the file does not list.

Removing a row from the model catalog in force unselects that model: `cast claude haiku-4-5 1` is
then refused with `cast models add claude haiku-4-5`. A model that should stay launchable and never
be routed keeps its row with `use=off`. `cast models list --catalog` shows every row with its
columns, whether it is launchable (cast supports it) and whether its login is present right now.

### `cast models`: list, add, remove

`cast models` is the one home of every list of models, and the only command that changes which
models an installation selects, the cells of its model catalog and its defaults. It acts on the installation that holds the current folder; it takes
no `--target`, so a caller sets the working folder. Every result starts with that installation and
the model catalog it read or changed.

| Form | What it does |
|---|---|
| `cast models list` (`--selected`, the default) | the models that can be launched here, cli and api, each with what every effort number means on it, then `N of M supported models are selected.` |
| `cast models list --supported` | every model this copy of cast can launch, with `selected` yes or no |
| `cast models list --catalog` | every row of the model catalog in force with its routing columns, `launchable` and `available`; a row cast does not support is shown |
| `cast models add HARNESS MODEL` | selects a supported model: appends its row from the shipped model catalog (every level it is listed at) under the installation file's own header, and prints each row with what its `use` value means. No login is checked |
| `cast models remove HARNESS MODEL` | deletes the model's rows from the installation's file; a row cast does not support can be removed |
| `cast models set HARNESS MODEL [--use route\|panel\|off] [--quality-override Y\|N] [--price-override Y\|N] [--level LEVEL]` | writes the cells an installation owns. `--use` holds for every level of the model. An override belongs to one level: a model listed at two levels takes `--level`. A column the file's header lacks is added |
| `cast models update [HARNESS MODEL]` | copies the cells rbtv proposes (`efforts`, `image`, `level`, `reasoning`, `coding`, `cost`) from the shipped model catalog, for every selected model or for one, and lists each changed cell. It writes only columns the file's header carries, adds and removes no row, and never changes `use` or an override |
| `cast models defaults [--route price\|quality] [--fallback off\|price\|quality]` | shows the installation's defaults, or sets the ones named: how `cast route` ranks when a call gives no `--optimize`, and how a launch ranks the [fallback](#fallback) of a model that fails to start (`off`: it runs none). They are kept in `.rbtv/config/cast/defaults.json`; a key the file lacks reads cast's own value, `price` and `off` |

HARNESS and MODEL are the words of a launch; an api model takes harness `api`. `--dry-run` on every
form but `list` prints what would change and writes nothing. Both lists of `cast models list` and
`--catalog` show the defaults in force on a line under the model catalog.

- **No file yet.** `add` changes nothing and saves no file, because every supported model is
  already selected. `remove` and `set` first copy the shipped model catalog into the installation,
  then change it, so every other model stays selected. `update` has nothing to do: the shipped
  model catalog is the one in force.
- **How update pairs rows.** A row is compared with the shipped row of the same model and level. A
  model with one row here and one shipped is compared whatever the levels, so a level rbtv changed
  is updated. A model whose levels cannot be paired, or that has no shipped row, is named under
  `not compared` and left as it is. `up to date` is said of the rows that were compared: when a
  model is named under `not compared` the line reads `the rows compared are up to date`, and when
  no row was compared it is left out.
- **No-ops exit 0.** `add` of a selected model and `remove` of a model that is not selected say so
  and write nothing.
- **Who still uses a model.** `remove` is refused while an agent under `<installation>/.rbtv/agents/`
  names the model in its `agent.json`, or the Dreamer is on and
  `.rbtv/config/ignite/config.json` names it as `dreamer.model`. The refusal lists them;
  `--force` removes it anyway and lists who will now be refused at launch. The result always says
  what was not checked: a record that could not be read, agents kept outside `.rbtv/agents/`, and
  settings of a component that name a model.
- **Writes.** The file is replaced in one step (a temporary file beside it, then a rename) and
  keeps its own line ending; a file the installation did not have is written with the machine's.
- **Refusals** exit 2 and change nothing: outside an installation (`add`, `remove`), a model cast
  does not support (`add`), a model still in use (`remove`), a model that is not selected or an
  override with no level named for a model listed at two (`set`), a model catalog or a defaults
  file that cannot be read, and a word or a value the verb does not take.

`--json` prints one value. Lists: `{installation, selection, view, models: [{harness, model, mode,
rungs, effort_numbers, selected}], usage}`, where `selection` is the installation's file, `null`
while the shipped one is in force; `--catalog`: `{installation, source, rows}`. `add`:
`{installation, selection, harness, model, changed, added, dry_run}`. `remove`: `{installation,
selection, harness, model, changed, removed, copied_shipped, users, not_checked, dry_run}`. `set`:
`{installation, selection, harness, model, changed, set: [{level, column, from, to}],
copied_shipped, dry_run}`. `update`: `{installation, selection, changed, updated: [{harness, model,
level, column, from, to}], not_updated: [text], dry_run}`. `defaults`: `{installation, file, route,
fallback, changed, dry_run}`. The lists also carry `defaults: {route, fallback, file}`, `file`
being `null` while the installation sets none. A
refusal under `--json` is `{error, message, next}` on standard output, with nothing on standard
error.

L4 is the image tier and no class admits it, so an L4 row is reachable ONLY through
`--caps image`.

## `cast api`

API workers are model catalog rows with `mode: api`, and since 2026-08-20 they are **Google only**: the
Gemini chat worker (`gemini-3.5-flash`) and the Google image-generation worker. The Manus and
DeepSeek api rows and their runner clients were deleted — DeepSeek survives through its opencode
CLI rows. Rows are addressed by short name, never by provider.

```
cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image [--input-image PATH ...]] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
```

`-p TEXT` and `-f FILE` (alias `--prompt-file`) are mutually exclusive; `-p` writes the task to
`<output-folder>/task.md` so it sits beside the result it produced. A `-f` file that is not there or
cannot be read, and a task that is empty or only whitespace, are refused with exit 2 in the words
of a launch, with and without `--dry-run`, before the output folder is written and before the
Python program starts. Effort 1–5 maps onto the
provider's reasoning knob where one exists (gemini `thinkingBudget`, 1 = off). A caller-supplied
`--extra-params` is merged, not replaced. `--dry-run` prints the composed subprocess argv as JSON
`{argv, cwd, effort_word}` and exits 0 with no spawn, no network, and nothing written to disk.

**`--image`** is the image-generation path: the task goes in, image FILES come out into
`--output-folder`. It asks for no JSON envelope and parses none — the model's inline image parts
ARE the return, written as `image-1.png`, `image-2.jpg`, … A run that comes back with no inline
image data is `DONE_WITH_NOTES`, never a clean `DONE`. `--image` and `--grounded` are refused
together: they are two incompatible return surfaces.

**`--input-image PATH`** (repeatable) sends an EXISTING image file IN alongside the task —
"edit this picture", "restyle this logo", "use this as reference" — instead of only text-to-image.
Requires `--image`; refused without it. Each path must exist and be readable, and its extension
must be one of `png`/`jpg`/`jpeg`/`webp`/`gif` — anything else is refused rather than guessed at.
The runner (`run.py`) reads each file, base64-encodes it, and builds the user message as a
provider-neutral part list (`clients/base.py Message.content`, already typed to allow it): a text
part carrying the task, then one image part per `--input-image`, in the order given. Only
`clients/gemini.py` translates that list onto Google's wire shape (`inlineData` with `mimeType` +
`data`) — `run.py` itself stays provider-agnostic. With no `--input-image`, the message stays a
plain string exactly as before — zero behaviour change on the existing text-to-image and text-only
paths. An unrecognised part type in the neutral list raises rather than being silently dropped.

⚠ **The image row ships with a BLANK model id** — the owner has not picked the model yet. While it
is blank, `cast route --caps image` returns a verdict with an empty `model` and `cast api` refuses
to call it. Filling the id in BOTH `models.csv` and `supported-models.js` (identically) is all that is
needed. ⚠ **The image call has never been made live** — `GEMINI_API_KEY` is absent on this box, so
the path is verified by `--dry-run` and by unit tests over the request payload and the
inline-image parsing, not by a real call.

The runner always writes `return.json` `{status: DONE|DONE_WITH_NOTES|BLOCKED, landed, validation,
concerns, open_questions}` under `--output-folder`, prints `"{status} | N file(s)"`, and exits 0
unless `BLOCKED` (then 1). Key resolution is `{PROVIDER}_API_KEY` in the OS env first, then the
environment file (`.rbtv/config/env/.env`) of the installation that holds the folder `cast api`
runs in.

## Layout

| File | What it owns |
|---|---|
| `capabilities/tools/cast/cast.js` | the CLI front door — argv dispatch and the bare launch path, nothing else |
| `capabilities/tools/cast/cast.json` | the tool record: the name `cast`, its listing description and the executable `cast.js` |
| `capabilities/tools/cast/supported-models.js` | the supported models: LAUNCH mechanics only — harness-native id, effort ladder, provider (see Spec source) |
| `capabilities/tools/cast/providers.json` | the providers: login method, key variable, credential-store entry per harness, saved-login files, usage source |
| `capabilities/tools/cast/models.csv` | the shipped model catalog — level, scores, cost, image, `use` for every supported model. In force wherever an installation has no model catalog of its own. Lives beside this tool so routing does not depend on any other tree |
| `capabilities/tools/cast/api/` | the Python program `cast api` runs (`run.py`), its provider clients (`clients/`) and their tests (`tests/`) |
| `capabilities/tools/cast/test_cast.js` | the suite for the CLI and its `lib/` modules, `route.js` excepted (see Self-check) |
| `capabilities/tools/cast/test_route.js` | the suite for `cast route` (see Self-check) |
| `capabilities/tools/cast/lib/installation.js` | the installation a launch belongs to (first folder upward holding `.rbtv/config/install.json`) and its environment file |
| `capabilities/tools/cast/lib/model-catalog.js` | the model catalog in force for an installation: reading it strictly, changing cells, replacing it in one step, who owns each column, the join with the supported models, and the launch check |
| `capabilities/tools/cast/lib/models.js` | `cast models`: the three lists, `add`, `remove`, `set`, `update` and `defaults`, who in the installation still uses a model, and where its model catalog differs from the shipped one |
| `capabilities/tools/cast/lib/core.js` | shared primitives: argv parsing, model/effort/folder resolution (`lookupModel`, which runs the launch check), the words of `cast list` |
| `capabilities/tools/cast/lib/doctor.js` | `cast doctor`: harness programs on `PATH`, the login of each model the installation selects and the count of cells that differ from the shipped model catalog, from local files only |
| `capabilities/tools/cast/lib/handles.js` | the launch-handle registry — the one observable a watcher uses to find a run again |
| `capabilities/tools/cast/lib/launch.js` | spawn, the fallback runs of a launch, `cast resume` |
| `capabilities/tools/cast/lib/fallback.js` | the fallback of a launch: what counts as a failure to start, the candidates of a model in the order to try them, the effort they launch at, the words for how an attempt ended, and the words that close a level with none left. `launch.js` and Ignite's turn both use it |
| `capabilities/tools/cast/lib/defaults.js` | the installation's defaults, `.rbtv/config/cast/defaults.json`: the default ranking of `cast route` and the ranking of a fallback, read and replaced in one step |
| `capabilities/tools/cast/lib/win-exec.js` | how a harness name becomes a process on Windows: finds the program on `PATH` and wraps an npm `.cmd` shortcut so that it can be started |
| `capabilities/tools/cast/lib/agent.js` | `--agent` / `--rogue`: find the agent folder, read `agent.json` and `prompt.md`. The one place that knows where an agent's folder is (`<installation>/.rbtv/agents/<name>`), which agents a `--target FOLDER` names, what counts as a path, and how the record is read: spark, the agent list and Ignite load it |
| `capabilities/tools/cast/lib/agent-list.js` | `cast list --agents`: the agents a name can reach, as a table, labeled blocks, or JSON; the one list, which [`spark list`](../spark/spark.md) and `rbtv agent list` also show |
| `capabilities/tools/cast/lib/sessions.js` | the per-harness session-store readers and `cast sessions` |
| `capabilities/tools/cast/lib/monitor.js` | `cast monitor` — the freeze tripwire, its witness channel, roster and watch |
| `capabilities/tools/cast/lib/win-proc.js` | the Windows process table `cast monitor` samples, where Linux reads `/proc` |
| `capabilities/tools/cast/lib/provider-limit.js` | recognizing a provider usage limit in a harness log, and the reason and reset time reported for it |
| `capabilities/tools/cast/lib/optional.js` | loading `monitor.js` and `provider-limit.js` so that a failure in either leaves every other verb working |
| `capabilities/tools/cast/lib/route.js` | `cast route` — the selector |
| `capabilities/tools/cast/lib/api.js` | `cast api` — the API-worker runner (Google only) |
| `capabilities/tools/cast/lib/help.js` | `-h` output: the top-level page, the per-verb pages, and one page for each verb of `cast models` |

`ignite turn` (exact session id, resume with the requested model/effort, result file) is not in this folder: it is `core/ignite/capabilities/tools/ignite/turn.js`, in the Ignite tool. `spark` has its own folder and page: [spark](../spark/spark.md).

The require graph is a DAG and `test_cast.js` asserts that it stays one — a CommonJS cycle does
not throw, it silently hands the cycle-closing module a half-built `{}` whose imported bindings
are `undefined`, so the check reads the `require('./x')` edges and walks them for cycles rather
than trusting a clean load.

`handles.js` exists because the handle registry is read by `sessions` and `monitor` as well as
`launch` — leaving it inside `launch.js` was the one genuine cycle the split had to resolve.

Every module exports its whole top-level surface, so the pure functions are directly requirable
(`require('./lib/route').selectRoute(...)`) instead of reachable only through a subprocess.

## Self-check

```
node capabilities/tools/cast/test_cast.js       # -> all cast tests passed
node capabilities/tools/cast/test_route.js      # -> all route tests passed
python3 -m pytest capabilities/tools/cast/api/tests/ -q
```

`test_route.js` asserts EXACT verdicts against the shipped `models.csv`, so editing that file's
levels, scores or costs reddens the suite on purpose: the CSV IS the routing decision, and a silent
edit to it silently changes every answer route gives.
