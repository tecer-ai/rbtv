# cast

Launches ONE headless agent turn in any of three harnesses behind one CLI. The caller's
process runs the launch (foreground, blocking). Sessions are
addressable after the fact: `sessions` lists what ran in a folder, `resume` sends one more
turn into an existing session.

## Usage

```
cast <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) [-s TEXT | -S FILE | --rogue AGENT-FILE] [--headed] [--dry-run]
cast --agent NAME (-p TEXT | -f FILE) [--headed] [--dry-run]
cast resume <harness> <session-id|last> [launch-folder] (-p TEXT | -f FILE) [--dry-run]
cast sessions [harness] [launch-folder] [--json] [-n N]
ignite turn --request FILE --result FILE
cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image [--input-image PATH ...]] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
cast route --access open|bounded --type code|text --class planner|broad|bounded|mechanical --optimize price|quality [--caps image] [--explain]
cast route --caps image
cast route --batch <agents.json | -> [--explain]
cast route --catalog [--json]
cast doctor [--json]
cast list [--models | --agents [--full] | --agent NAME] [--json]
cast -h | --help
```

| Arg | Meaning |
|---|---|
| `harness` | `claude` \| `codex` \| `opencode` |
| `model` | that harness's model, SHORT name — the provider prefix and the `claude-` prefix are dropped: `opus-5-5` (not `claude-opus-5-5`), `glm-5.3` (not `zai-coding-plan/glm-5.3`). See `cast -h` or `cast list` for the current inventory; a long id is refused with the short one suggested |
| `effort` | integer 1-5, the universal dial |
| `launch-folder` | working directory for the agent, resolved relative to the caller's CWD; MUST already exist |
| `-p TEXT` | literal prompt text |
| `-f FILE` | read the prompt from a file; `-f -` reads it from stdin |
| `--dry-run` | print the composed argv as JSON and exit 0 without launching |

Run `cast list --models` for the live model/effort table (generated from the tool's own spec; `cast -h`
names that command and prints no model), or `cast list --json` for a machine-readable `{harness: {model: [rungs...]}}` inventory plus two
top-level keys: `effort_numbers` — `{harness: {model: {word: number}}}`, each word mapped to the
smallest number that selects it (`glm-5.3` → `{"high":1,"max":2}`; a model with no dial → `{}`) —
and `usage`, which says to pass the NUMBER as `<effort>` because the launch path accepts only the
integer. The rung words are labels, never values a bare launch takes.
`cast doctor` is the pre-launch view: which harness binaries are on `PATH`, which providers are
enabled behind them, and what is left on each. It runs `acct doctor` + `acct usage`, which own
those answers, so it needs `acct` on `PATH` — and it hits the network for the usage half.
`cast doctor --json` merges both: `{installation, harnesses: {name: {ok, path}},
providers: {name: {enabled, via, slots, active}}, usage: [...]}`.

## Effort mapping (1-5 → the harness's own ladder)

Each (harness, model) has its own rung ladder in `capabilities/tools/cast/catalog.js`. Rule:
`rung = ladder[min(N, ladder.length) - 1]`
— asking for 5 on a 3-rung ladder clamps to that ladder's top rung, never a refusal. An `inert`
ladder (`haiku-4-5`) accepts any N and emits no effort argv at all. `cast list --models` prints the
resolved mapping per model with the clamping folded in (e.g. `glm-5.3  1=high 2-5=max`), so the
number-to-rung answer is never inferred. The positional `<effort>` a bare launch takes is an
integer 1-5 only — a rung word is refused at exit 2 — so `cast list --json` also reports
`effort_numbers` (the same mapping inverted: each word to the smallest number that selects it)
and a `usage` line telling agents to pass the number, because the words in the inventory look
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
| codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` — id + cwd in the first-line `session_meta` (walked newest-first, stops at `-n` matches) | `codex exec resume <id\|--last>` + `-c sandbox_mode=danger-full-access -c approval_policy=never --skip-git-repo-check` |
| opencode | `opencode session list --format json` run with cwd = folder, rows filtered on their `directory` field | `opencode run -s <id>` (`last` → `-c`) |

`resume` runs with cwd = launch-folder (that is also what scopes every harness's `last`), takes the
message via `-p`/`-f` on stdin like a launch, and re-passes the permission/sandbox flags — those
are per-invocation, not per-session. The resumed session keeps its own model/effort; `-s`/`-S` and
`--headed` are refused. `-n` caps `sessions` PER HARNESS (default 10), newest first; `--json` gives
`[{harness, id, started, label}]`. The label is human-readable session identity: opencode's stored
`title`; for claude/codex a ≤60-char excerpt of the first real user message (injected `<...>`
wrapper blocks skipped) — for cast-launched sessions that is the `-p` prompt itself. Known ceiling: two same-harness sessions launched into the same folder
in the same minute are distinguishable only by trying them — no id is captured at birth (codex and
opencode only surface theirs inside their `--json` output streams, which cast passes through
untouched). `ignite turn` is the exception: it returns an exact id for that invocation (see below).


## Agent launches (`--agent`, `--rogue`)

`cast --agent NAME (-p TEXT | -f FILE)` runs an agent folder: a folder holding both `agent.md` and
`agent.json`. AGENT is a name, looked up as `<installation>/.rbtv/agents/AGENT/` from the current
folder upward, or a path to the folder (a value containing `/`, or `.` or `..`, relative to the
current folder). The folder is the working folder. `agent.json` gives the harness, model and effort
(effort as the model's own word, such as `high`); none of them may be given on the command line:
that is refused, and the refusal names `rbtv agent configure AGENT` as the way to change them.
`agent.md` is the system prompt, handed to the model without its frontmatter. The launch sets
`RBTV_AGENT_HOME` to the agent folder for the harness process. A folder holding only one of the two
files is refused by name, so a broken agent is never launched half-read. `--target` is gone.

`--rogue FILE` runs a rogue agent file that is not an agent folder: the file's body, without its
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

  <prompt>
  ```

`-s`/`-S` cannot be combined with `--agent`/`--rogue`. Every Codex launch also passes
`-c project_doc_max_bytes=131072`, because rules reach Codex as full text in `AGENTS.md`.

`ignite turn` takes its standing prompt the same way: the `systemPromptFile` in its request is read
with its frontmatter removed, and the model receives the body only.

### Finding the agents: `cast list --agents`

`cast list --agents` shows the rbtv agents `cast --agent NAME` can launch from the current folder: the
agents in the nearest `.rbtv/agents/` folder above it. For each agent it prints the name, harness,
model, effort, Ignite (`yes` when the agent's `ignite` pack is on, which `ignite connect` does) and
the description from `agent.json`. The description is shortened to fit the line; with `--full`, or on
a terminal too narrow for the table, each agent is a labeled block with its whole description. An agent that cannot
be launched is named with the reason. `--json` prints `{folder, agents}`. `cast list` and
`cast list --models` print the model inventory.

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

`lib/agent-list.js` holds the list, and it is the only list of agents: `cast list --agents` shows it
to an agent, `spark list` shows it to a person, and `rbtv agent list` runs `cast list --agents`. The
three print the same text, so a line that names a command names all three. Each command words
its own refusals.

## spark — open an agent for a person

`spark AGENT` (`capabilities/tools/spark/spark.js`) opens an agent in this terminal, for a person.
It prints the agent's folder, harness, model and effort, then starts `cast --agent NAME --headed` with
a one-line greeting. It passes no harness, model or effort, so cast reads them from `agent.json`.
It needs `cast` on PATH and finds the agent the same way cast does: a name or a path.

- `--dry-run` prints the cast command and launches nothing; `--dry-run --json` prints one JSON value
  with `agent`, `home` and `cast`. A real launch ignores `--json`.
- Refusals, exit 1: no agent by that name or path, `agent.json` unreadable or missing, `agent.md`
  missing, `cast` not on PATH, or an unknown option.

`spark list [AGENT]` shows the agents spark can open by name, or one of them in full: the list of
`cast list --agents`, read in the same process, so it needs nothing on PATH and opens nothing. The
first argument that is not an option decides the form, so `list` is never taken as an agent name:
an agent whose name is `list` is opened by its path.

- Refusals, exit 1: `--dry-run`, more than one agent, an agent that is not found or cannot be
  launched, or an unknown option. A refusal is text on standard error and leaves standard output
  empty, with or without `--json`.

## Execution

The child is spawned with `cwd = <launch-folder>` for every harness (the `--cd`/`--work-dir` flags
are belt-and-braces on the harnesses that have them). The (possibly descriptor-prepended) prompt is
written to the child's stdin and stdin is then closed. Stdout/stderr are inherited. `cast`
exits with the child's exit code.

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

## Exit codes

| Code | Meaning |
|---|---|
| `0` | child ran to completion (its own exit code); also `-h`, `doctor`, `list`, `sessions` |
| `2` | unknown harness/model, launch-folder missing, effort outside 1-5, bad/missing flags |

## Spec source

**codex ladders come from the model manifest embedded in the codex binary** — a JSON blob keyed
`{"models": [{"slug": ..., "supported_reasoning_levels": [...]}]}`, extractable with a brace-matched
read of the binary at `~/.codex/packages/standalone/releases/<ver>/bin/codex`. Read 2026-08-12 from
0.147.0 and spot-checked with live `codex exec` runs. Availability is account-dependent and the
manifest does NOT encode it: `gpt-5.2` is listed with visibility `list` yet a live run returns
`400 … "not supported when using Codex with a ChatGPT account"`, so it is excluded. Also excluded:
`gpt-5.4`, `gpt-5.4-mini`, `codex-auto-review` (manifest visibility `hide`). Note that a bad
`model_reasoning_effort` IS rejected by the API (`invalid_enum_value`, supported: none, minimal,
low, medium, high, xhigh, max) — but `ultra`, which sol/terra list as a 6th level, is accepted
without appearing in that enum, so codex translates it client-side. A 1-5 dial cannot reach a 6th
rung, so `ultra` is left out of the table rather than sitting there unreachable.

**opencode ladders are measured, and there are two disagreeing sources — use the right one.** The
authority for a `--variant` value is the `variants` keys in `opencode models <provider> --verbose`,
which is what the running binary validates against. The models.dev catalog opencode caches at
`~/.cache/opencode/models.json` carries a DIFFERENT field (`reasoning_options[].values`) that
disagrees — it lists `high,xhigh` for `sakana/fugu`, where the binary accepts `low,medium,high`
(both re-measured 2026-08-12). Never source a ladder from the cache file — the `xai/grok-*` ladders
used to be the one exception (the provider was uncredentialed and so invisible to the binary), and
the cache was wrong there too: it claimed `xhigh` for `grok-4.6`, which the binary does not list.
xai is authenticated via opencode oauth as of 2026-08-13 and both grok ladders are now measured
(`low,medium,high`). A model with no variants at all (`zai-coding-plan/glm-4.7`) is inert: any
effort number, no `--variant` argv.

The (harness, model) → argv/effort table lives in `capabilities/tools/cast/catalog.js`; `capabilities/tools/cast/models.csv` holds
the routing catalog. `cast list --models` and `cast list --json` read the current launch table. Update
`capabilities/tools/cast/catalog.js` when a harness model or effort ladder changes, then run `test_cast.js` and
`test_route.js`.

## `cast route`

The deterministic worker selector, REDESIGNED 2026-08-20: you answer four questions about the job
and route names ONE `(harness, model, mode, effort)`. It is a pure function of those flags,
`capabilities/tools/cast/models.csv` and `capabilities/tools/cast/catalog.js` — no network, no clock, no randomness, so the same answers
always give the same verdict. The old JSON-task-profile interface is DELETED with no back-compat
path, and with it the boundedness bands, pinned roles, halt seams, stakes tier-up, the haiku
clause, footprint/window gating and evidence ranking.

```
cast route --access open|bounded --type code|text \
           --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps image] [--explain]
cast route --caps image        # short-circuit — no other flag needed
cast route --batch agents.json  # a whole team in one call; `--batch -` reads stdin
cast route --catalog [--json]  # the roster, asks nothing
```

Three flags are REQUIRED (`--access`, `--type`, `--class`). There are no silent defaults: an
unanswered question is a guess, and a guess is what this command exists to remove. The ONE ruled
default is `--optimize` (owner ruling 2026-08-22): omitted, it is **price**, for every class alike.
`cast route -h` IS the interview in full.

| Flag | The question | Effect |
|---|---|---|
| `--access` | Must the agent navigate and DISCOVER files on disk? | `open` drops every api row — an API worker has no disk. `bounded` (known files only, or no disk at all) keeps them. |
| `--type` | Code, or prose/analysis? | Picks the tie-break axis (`coding` vs `reasoning`). **Planning is TEXT**, even for a coding job. |
| `--class` | How bounded is the work? | Picks BOTH the ONE eligible level and the effort (table below). |
| `--optimize` | Cheapest that qualifies, or best that qualifies? (optional) | The selection rule among survivors. Omitted → price, identical to passing `--optimize price`. |
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
**Default (flag omitted) — owner ruling 2026-08-22: PRICE, for every class alike.** It is the
`price` ranking above in every respect — same order, same blank-cost exclusion, same tie-breaks —
carrying its own `"optimize":"default"` trace label so an `--explain` reader can still tell an
omitted flag from an explicit one. This REPLACED the two-band rule of 2026-08-21 (SOTA/L1 on price,
L2/L3 on quality), which is gone: one rule the owner can hold in their head beat two bands. The
class's level is the ONLY thing standing between a job and the cheapest model on the roster, which
is what makes level curation load-bearing.

**Blank cells** (the owner fills them over time): a blank `cost` sits OUT of every price-ranked
pick — `--optimize price` AND the default — and stays eligible for `quality` — unknown is not cheap; a blank `level` excludes the row entirely; a
blank score reads as 0 in tie-breaks. Every exclusion appears in `--explain`.

Pipeline order: parse flags → load CSV (override-aware) → join `catalog.js` → availability →
image short-circuit → access → caps → class levels → optimize → effort. `--explain` attaches the full
trace with a reason on every dropped row.

**Batch.** `--batch agents.json` (or `--batch -` for stdin) routes a whole team in ONE call — a
planning agent designs every agent at once and needs one deterministic assignment table, not N
shell calls. Input is a JSON array of agent objects (or `{"agents":[...]}`); each agent is the
interview as an object with a unique `name`, the same vocabulary and required-ness as the flags
(`"caps":["image"]` short-circuits the same way), and an unknown key is a refusal. The CSV load
and the catalog join happen ONCE for the batch; every agent still goes through the same selector,
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
interview flags, `--caps` or `--catalog`.

| Verdict | Shape | Exit |
|---|---|---|
| route | `{"verdict":"route","harness":…,"model":…,"mode":"cli"\|"api","effort":1-5,"effort_is_floor":false,"alternates":[{"harness":…,"model":…,"mode":…}]}` | 0 |
| route-batch | `{"verdict":"route-batch","agents":[{"name":…,"verdict":"route",…} \| {"name":…,"error":…,"details":…}]}` — agents in input order | 0 only when EVERY agent routed, else 1 |
| error | `{"error":"malformed_request"\|"zero_candidates"\|"no_models","details":…}` | 1 |

The top-level worker IS the verdict — launch it. `alternates` carries the next two of the same
ranking (fewer if the ranking is shorter) as BACKUPS for when the first cannot be launched; they
share the verdict's effort. `mode: cli` is launchable by `cast <harness> <model> <effort>`; `mode: api` is reached by
`cast api` and refuses a launch at exit 2 rather than pretending the model is unknown. `effort` is
a cast 1-5 integer mapped onto the picked row's own ladder at launch — an inert ladder still takes
the number and emits no argv.

Availability is a PRESENCE test, never a spend: an api-key row resolves from the OS environment
first, then the dotenv at `rbtv.json`'s `env_file`, then a stored CLI login in the harness's own
credential store. An absent key drops the row; it is never an error. ⚠ Consequence worth naming:
with no `GEMINI_API_KEY` on the box, `cast route --caps image` answers `zero_candidates` naming the
key — which is the honest answer, not a bug.

### The catalog: two files, joined

Routing axes live in **`capabilities/tools/cast/models.csv`** — data the owner edits without touching code. It sits beside this tool so `cast route` keeps working when no other tree is present. A per-vault file still replaces it whole (below). Launch
mechanics (harness-native id, effort ladder, auth) stay in **`capabilities/tools/cast/catalog.js`**. Route joins them
on `harness`+`model`, and a CSV row with no `catalog.js` twin is excluded with a loud stderr
warning: route must never name something cast cannot launch.

Columns: `mode` (cli|api) · `harness` · `model` · `efforts` (max N, 0 = inert) · `image` (Y/N) ·
`level` (SOTA|L1|L2|L3|L4) · `reasoning` (1-7) · `coding` (1-7) · `cost` ($ per M
output tokens, **public API list price** — comparable and stable, never the personal
subscription-effective cost) · `use` (route|panel|off) · `quality-override` (Y/N) ·
`price-override` (Y/N).

**The three owner switches** (added 2026-08-22, owner ruling). They are the only columns that
change WHO competes and WHO wins without touching a score:

| Column | Values | What it does |
|---|---|---|
| `use` | `route` (blank reads as this) | the normal state — the row competes for verdicts. |
| | `panel` | no verdict may name it, but it stays in `cast route --catalog`, the roster a panel takes its seats from — every model at the class's level and the level below (the `sub-agents` skill's panel capability at `meta/sub-agents/capabilities/panel.md`). For a model worth a second opinion and never worth being the single answer. |
| | `off` | routing ignores it entirely. Still launchable by hand (`cast <harness> <model> <n>`) and still listed by `--catalog` with its `use` value — taken out of routing, never hidden. |
| `quality-override` | `Y` | inside ITS OWN LEVEL, this row wins a `--optimize quality` ranking whatever the scores say. |
| `price-override` | `Y` | inside ITS OWN LEVEL, this row wins an `--optimize price` ranking whatever the costs say. |

An override **never crosses a level** — an L2 row with `quality-override=Y` still loses to every
eligible L1 row; it only takes the head of its own level's block. It **never bypasses a filter**
either: availability, `--access`, `--caps` and the class's levels all run first, so an override can
only reorder rows that already qualify. The default (no `--optimize`) is a price ranking, so
`price-override` fires there and `quality-override` does not — making a quality-override bite takes
an explicit `--optimize quality`. Several flagged rows in one level keep the normal tie-breaks
among themselves. A `use` value that is none of the three is never guessed — the row drops from
routing with a loud stderr warning.

One `use` column rather than a `route` Y/N plus a `panel-only` Y/N: two flags would allow
`route=Y` + `panel-only=Y`, a state with no meaning that the code would have to invent a winner
for. Three values, three outcomes, no contradiction possible.

**A model MAY sit at more than one level** — one CSV line per level, identical in every other
cell (owner ruling 2026-08-23). `level` is normally the model's single quality tier, and a second
line is the deliberate exception for a model whose list price misrepresents what it actually costs
this vault: `claude/sonnet-5-5` carries a Claude subscription that makes its $10 list cost effectively
~5x lower, so it sits at **L2 and L3** and is reachable by both `bounded` and `mechanical`, winning
each on its `price-override=Y`. The join onto `catalog.js` is on harness+model and every copy
resolves to the same launch spec, so nothing about launching is ambiguous. What remains forbidden
is the ACCIDENTAL duplicate: two lines for one model that disagree on any cell other than `level` —
`test_route.js` fails on it, because route would otherwise rank the same model twice under
different numbers. Adding a level to a model changes every verdict in the classes that reach it, so
it is an owner decision, never a fix applied in passing.

**Per-vault override**, whole-file replace: `{vault}/.rbtv/config/modules/core/cast/models.csv`.
If that file exists it IS the catalog and the shipped CSV is ignored entirely.

The CSV carries **the latest models only, per provider**. Pruning it does NOT remove launch
support — `cast claude haiku-4-5 1` still launches, it just stops being an answer route can give.
`cast route --catalog` shows every CSV row with its axes, whether it is launchable (has a
`catalog.js` twin) and whether its credential resolves right now.

L4 is the image tier and no class admits it, so an L4 row is reachable ONLY through
`--caps image`.

## `cast api`

API workers are catalog rows with `mode: api`, and since 2026-08-20 they are **Google only**: the
Gemini chat worker (`gemini-3.5-flash`) and the Google image-generation worker. The Manus and
DeepSeek api rows and their runner clients were deleted — DeepSeek survives through its opencode
CLI rows. Rows are addressed by short name, never by provider.

```
cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image [--input-image PATH ...]] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
```

`-p TEXT` and `-f FILE` (alias `--prompt-file`) are mutually exclusive; `-p` writes the prompt to
`<output-folder>/prompt.md` so it sits beside the result it produced. Effort 1–5 maps onto the
provider's reasoning knob where one exists (gemini `thinkingBudget`, 1 = off). A caller-supplied
`--extra-params` is merged, not replaced. `--dry-run` prints the composed subprocess argv as JSON
`{argv, cwd, effort_word}` and exits 0 with no spawn, no network, and nothing written to disk.

**`--image`** is the image-generation path: the prompt goes in, image FILES come out into
`--output-folder`. It asks for no JSON envelope and parses none — the model's inline image parts
ARE the return, written as `image-1.png`, `image-2.jpg`, … A run that comes back with no inline
image data is `DONE_WITH_NOTES`, never a clean `DONE`. `--image` and `--grounded` are refused
together: they are two incompatible return surfaces.

**`--input-image PATH`** (repeatable) sends an EXISTING image file IN alongside the prompt —
"edit this picture", "restyle this logo", "use this as reference" — instead of only text-to-image.
Requires `--image`; refused without it. Each path must exist and be readable, and its extension
must be one of `png`/`jpg`/`jpeg`/`webp`/`gif` — anything else is refused rather than guessed at.
The runner (`run.py`) reads each file, base64-encodes it, and builds the user message as a
provider-neutral part list (`clients/base.py Message.content`, already typed to allow it): a text
part carrying the prompt, then one image part per `--input-image`, in the order given. Only
`clients/gemini.py` translates that list onto Google's wire shape (`inlineData` with `mimeType` +
`data`) — `run.py` itself stays provider-agnostic. With no `--input-image`, the message stays a
plain string exactly as before — zero behaviour change on the existing text-to-image and text-only
paths. An unrecognised part type in the neutral list raises rather than being silently dropped.

⚠ **The image row ships with a BLANK model id** — the owner has not picked the model yet. While it
is blank, `cast route --caps image` returns a verdict with an empty `model` and `cast api` refuses
to call it. Filling the id in BOTH `models.csv` and `catalog.js` (identically) is all that is
needed. ⚠ **The image call has never been made live** — `GEMINI_API_KEY` is absent on this box, so
the path is verified by `--dry-run` and by unit tests over the request payload and the
inline-image parsing, not by a real call.

The runner always writes `return.json` `{status: DONE|DONE_WITH_NOTES|BLOCKED, landed, validation,
concerns, open_questions}` under `--output-folder`, prints `"{status} | N file(s)"`, and exits 0
unless `BLOCKED` (then 1). Key resolution is `{PROVIDER}_API_KEY` in the OS env first, then the
dotenv at `rbtv.json`'s `env_file`.

## Layout

| File | What it owns |
|---|---|
| `capabilities/tools/cast/cast.js` | the CLI front door — argv dispatch and the bare launch path, nothing else |
| `capabilities/tools/cast/catalog.js` | LAUNCH mechanics only — harness-native id, effort ladder, auth (see Spec source) |
| `capabilities/tools/cast/models.csv` | the routing table — level, scores, cost, image. Owner-editable; overridable per vault. Lives beside this tool so routing does not depend on any other tree |
| `capabilities/tools/cast/lib/core.js` | shared primitives: argv parsing, model/effort/folder resolution, the model table, `doctor`, `list` |
| `core/ignite/capabilities/tools/ignite/turn.js` | `ignite turn` — exact session id, resume with the requested model/effort, result file |
| `capabilities/tools/cast/lib/handles.js` | the launch-handle registry — the one observable a watcher uses to find a run again |
| `capabilities/tools/cast/lib/launch.js` | spawn, `cast resume` |
| `capabilities/tools/cast/lib/agent.js` | `--agent` / `--rogue`: find the agent folder, read `agent.json` and `agent.md`; the readers spark also uses |
| `capabilities/tools/cast/lib/agent-list.js` | `cast list --agents`: the agents a name can reach, as a table, labeled blocks, or JSON; the one list, which `spark list` and `rbtv agent list` also show |
| `capabilities/tools/spark/spark.js` | `spark AGENT`: the terminal handoff, a thin layer over `cast --agent`; `spark list`: the list of `lib/agent-list.js` (its tests: `test_spark.js`) |
| `capabilities/tools/cast/lib/sessions.js` | the per-harness session-store readers and `cast sessions` |
| `capabilities/tools/cast/lib/monitor.js` | `cast monitor` — the freeze tripwire, its witness channel, roster and watch |
| `capabilities/tools/cast/lib/route.js` | `cast route` — the selector |
| `capabilities/tools/cast/lib/api.js` | `cast api` — the API-worker runner (Google only) |
| `capabilities/tools/cast/lib/help.js` | `-h` output: the top-level page and the per-verb pages |

The require graph is a DAG and `test_cast.js` asserts that it stays one — a CommonJS cycle does
not throw, it silently hands the cycle-closing module a half-built `{}` whose imported bindings
are `undefined`, so the check reads the `require('./x')` edges and walks them for cycles rather
than trusting a clean load.

`handles.js` exists because the handle registry is read by `sessions` and `monitor` as well as
`launch` — leaving it inside `launch.js` was the one genuine cycle the split had to resolve.

Every module exports its whole top-level surface, so the pure functions are directly requirable
(`require('./lib/route').rank(...)`) instead of reachable only through a subprocess.

## Self-check

```
node capabilities/tools/cast/test_cast.js       # -> all cast tests passed
node capabilities/tools/cast/test_route.js      # -> all route tests passed
python3 -m pytest capabilities/tools/cast/api/tests/ -q
```

`test_route.js` asserts EXACT verdicts against the shipped `models.csv`, so editing that file's
levels, scores or costs reddens the suite on purpose: the CSV IS the routing decision, and a silent
edit to it silently changes every answer route gives.
