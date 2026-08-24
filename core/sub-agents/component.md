---
description: "The sub-agents component — one headless sub-agent launch behind a single interface (CLI: `cast`): claude, codex, or opencode"
---
# sub-agents

The component is `sub-agents`; the CLI it ships is `cast`.

Launches ONE headless agent turn in any of three harnesses behind one CLI. Detached — no
cage/systemd; the caller's process IS the launch (foreground, blocking). Sessions are
addressable after the fact: `sessions` lists what ran in a folder, `resume` sends one more
turn into an existing session.

## Usage

```
tool/cast.js <harness> <model> <effort 1-5> [launch-folder] (-p TEXT | -f FILE) [-s TEXT | -S FILE] [--headed] [--dry-run]
tool/cast.js seat [launch-folder] [-p TEXT | -f FILE] [--headed] [--dry-run]
tool/cast.js resume <harness> <session-id|last> [launch-folder] (-p TEXT | -f FILE) [--dry-run]
tool/cast.js sessions [harness] [launch-folder] [--json] [-n N]
tool/cast.js api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
tool/cast.js route --access open|bounded --type code|text --class planner|broad|bounded|mechanical --optimize price|quality [--caps web[,image]] [--explain]
tool/cast.js route --caps image
tool/cast.js route --batch <seats.json | -> [--explain]
tool/cast.js route --catalog [--json]
tool/cast.js doctor [--json]
tool/cast.js list [--json]
tool/cast.js -h | --help
```

| Arg | Meaning |
|---|---|
| `harness` | `claude` \| `codex` \| `opencode` |
| `model` | that harness's model, SHORT name — the provider prefix and the `claude-` prefix are dropped: `opus-5` (not `claude-opus-5`), `glm-5.2` (not `zai-coding-plan/glm-5.2`). The two K2.7 kimi models are the exception: their ids (`kimi-for-coding`, `kimi-for-coding-highspeed`) name no generation, so they carry the display short names `k2.7`, `k2.7-highspeed` (`k3` and `k3-256k` derive normally). See `cast -h` or `cast list` for the current inventory; a long id is refused with the short one suggested |
| `effort` | integer 1-5, the universal dial |
| `launch-folder` | working directory for the agent, resolved relative to the caller's CWD; MUST already exist |
| `-p TEXT` | literal prompt text |
| `-f FILE` | read the prompt from a file; `-f -` reads it from stdin |
| `--dry-run` | print the composed argv as JSON and exit 0 without launching |

Run `cast -h` for the live model/effort table (generated from the tool's own spec), or
`cast list --json` for a machine-readable `{harness: {model: [rungs...]}}` inventory.
`cast doctor` is the pre-launch view: which harness binaries are on `PATH`, which providers are
enabled behind them, and what is left on each. It runs `acct doctor` + `acct usage`, which own
those answers, so it needs `acct` on `PATH` — and it hits the network for the usage half.
`cast doctor --json` merges both: `{workspace, harnesses: {name: {ok, path}},
providers: {name: {enabled, via, slots, active}}, usage: [...]}`.

## Effort mapping (1-5 → the harness's own ladder)

Each (harness, model) has its own rung ladder (mirrored from
`ignite/config/spawn-profiles.yaml`, `launch-specs:`). Rule: `rung = ladder[min(N, ladder.length) - 1]`
— asking for 5 on a 3-rung ladder clamps to that ladder's top rung, never a refusal. An `inert`
ladder (`haiku-4-5`) accepts any N and emits no effort argv at all. `cast -h` prints the
resolved mapping per model with the clamping folded in (e.g. `glm-5.2  1=high 2-5=max`), so the
number-to-rung answer is never inferred.

## Messaging a session — `sessions` and `resume`

Discovery is pull-based: `sessions` prints nothing at launch and reads no registry of its own —
the harnesses' own session stores ARE the registry, keyed by launch folder. `resume` is a launch in
its own right, though, so it DOES emit a `cast: handle` line and register with `cast monitor`'s
handle registry, exactly like a bare or `seat` launch — the model/effort a resumed session runs
with is not cast's to name, so the handle's `model` field reads `resume` instead of a model name:

| Harness | Store read by `cast sessions` | `resume` argv |
|---|---|---|
| claude | `~/.claude/projects/<encoded-folder>/<id>.jsonl` — filename is the id | `claude -p --resume <id>` (`last` → `--continue`) + `--permission-mode bypassPermissions` |
| codex | `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` — id + cwd in the first-line `session_meta` (walked newest-first, stops at `-n` matches) | `codex exec resume <id\|--last>` + `-c sandbox_mode=danger-full-access -c approval_policy=never` |
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
untouched).

## seat.md descriptor behavior (`cast seat`)

`cast seat` reads `harness`/`model`/`effort` from `<launch-folder>/seat.md` frontmatter and treats
the file's content as the seat's binding instruction set for the sitting (plain launches ignore a
seat.md sitting in the folder):

- **claude** — has a real system-prompt flag: `--append-system-prompt-file <launch-folder>/seat.md` is appended to argv.
- **codex / opencode** — no system-prompt flag exists, so the descriptor rides the first
  stdin message instead, prepended ahead of the wake prompt with the same wrapper text ignite's
  daemon uses (`d-uniform-descriptor-carriage`):

  ```
  <seat.md content>

  ---

  The descriptor above is this seat's binding instruction set for this whole sitting — it rides
  this first message because your harness carries no system prompt. Do not re-read seat.md; you
  have just read it. The message that fired this sitting follows:

  <prompt>
  ```

No `seat.md` in the folder → `cast seat` refuses (exit 2). For plain launches, `-s TEXT`/`-S FILE`
set a system prompt with the same carriage (real flag for claude, first-message prepend elsewhere).

## Execution

The child is spawned with `cwd = <launch-folder>` for every harness (the `--cd`/`--work-dir` flags
are belt-and-braces on the harnesses that have them). The (possibly descriptor-prepended) prompt is
written to the child's stdin and stdin is then closed. Stdout/stderr are inherited. `cast`
exits with the child's exit code.

**Output format is deliberately the harness default — no `--output-format`/`--json` flag on any
harness (owner-ruled 1a, 2026-08-18, closing a measured divergence with ignite).** The contract is
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

The (harness, model) → argv/effort table lives in `tool/catalog.js` (extracted from `cast.js`
2026-08-18), copied from
`ignite/config/spawn-profiles.yaml`'s `launch-specs:` block — see that file's comment
`// source of truth: ...`. Three model lists go BEYOND that block, all read live on 2026-08-12,
because `spawn-profiles.yaml` had gone stale on each:

| Harness | What it adds over `spawn-profiles.yaml` |
|---|---|
| opencode (kimi) | the four `kimi-for-coding` models, which moved here when the standalone `kimi` CLI went away (2026-08-14); the yaml still lists them under a `kimi` harness |
| codex | the whole GPT-5.6 family (`sol`, `terra`, `luna`); and `gpt-5.5` gains `xhigh` — the yaml's 3-rung ladder could not reach the model's top |
| opencode | `glm-5.2-highspeed`, `glm-4.7`, `gemini-3.7-flash` (which replaced `gemini-3.6-flash` on 2026-08-22), `grok-4.6`, `grok-4.6-fast` |

The seven opencode ladders `spawn-profiles.yaml` does carry were re-measured and all match — no
drift there. **`spawn-profiles.yaml` itself is NOT updated by this capability** — the daemon's own
launch path still carries the stale codex list and the retired `kimi` harness. `ignite/launch-profiles/catalog.js` and `profiles.js` were tried first
(`loadConfig()` require()s cleanly) but `profiles.js#loadConfig` refuses to parse the real config
without a daemon-supplied `seatBindValidator` for the `cage`/`sandbox` blocks — not a plain
require() away — so this tool does not depend on the daemon's resolver. Update `tool/catalog.js`
by hand when `spawn-profiles.yaml`'s ladders or argv shapes drift.

## `cast route`

The deterministic worker selector, REDESIGNED 2026-08-20: you answer four questions about the job
and route names ONE `(harness, model, mode, effort)`. It is a pure function of those flags,
`tool/models.csv` and `tool/catalog.js` — no network, no clock, no randomness, so the same answers
always give the same verdict. The old JSON-task-profile interface is DELETED with no back-compat
path, and with it the boundedness bands, pinned roles, halt seams, stakes tier-up, the haiku
clause, footprint/window gating and evidence ranking.

```
cast route --access open|bounded --type code|text \
           --class planner|broad|bounded|mechanical [--optimize price|quality] [--caps web[,image]] [--explain]
cast route --caps image        # short-circuit — no other flag needed
cast route --batch seats.json  # a whole team in one call; `--batch -` reads stdin
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
| `--class` | How bounded is the work? | Picks BOTH the eligible levels and the effort (table below). |
| `--optimize` | Cheapest that qualifies, or best that qualifies? (optional) | The selection rule among survivors. Omitted → price, identical to passing `--optimize price`. |
| `--caps` | A specific capability? (comma-separated, optional) | `web` drops every `web=N` row. `image` SHORT-CIRCUITS to the L4 image row and skips every other question. |

| `--class` | Eligible levels | Effort (code / text) |
|---|---|---|
| `planner` | SOTA + L1 | 3 / 3 — a **FLOOR** (`effort_is_floor: true`); the CALLING AGENT raises it for criticality, complexity or blast radius. Route does not decide that. |
| `broad` | L1 | 2 / 3 |
| `bounded` | L1 + L2 | 2 / 2 |
| `mechanical` | L2 + L3 | 1 / 1 |

A class never unlocks a level it blocks: `--class bounded --optimize quality` picks the best L1, never
SOTA. Only `planner` reaches SOTA. L1 membership IS the trust bar — planning is no longer
Claude-scoped, so curate the L1 rows accordingly. haiku is normally routable as L3.

**Price, a total order.** `price`: lowest `cost` → higher score → alphabetical harness, then model.
`quality`: highest level within the class's own levels → higher score → lower cost → alphabetical.
**Default (flag omitted) — owner ruling 2026-08-22: PRICE, for every class alike.** It is the
`price` ranking above in every respect — same order, same blank-cost exclusion, same tie-breaks —
carrying its own `"optimize":"default"` trace label so an `--explain` reader can still tell an
omitted flag from an explicit one. This REPLACED the two-band rule of 2026-08-21 (SOTA/L1 on price,
L2/L3 on quality), which is gone: one rule the owner can hold in their head beat two bands. What
changed in practice: a class spanning two levels now takes the cheaper row wherever it sits, so
`bounded` (L1+L2) can answer with an L2 — under the retired rule the whole SOTA/L1 band ranked
first and it never could. The class's levels are now the ONLY thing standing between a job and the
cheapest model on the roster, which is what makes level curation load-bearing.

**Blank cells** (the owner fills them over time): a blank `cost` sits OUT of every price-ranked
pick — `--optimize price` AND the default — and stays eligible for `quality` — unknown is not cheap; a blank `level` excludes the row entirely; a
blank score reads as 0 in tie-breaks. Every exclusion appears in `--explain`.

Pipeline order: parse flags → load CSV (override-aware) → join `catalog.js` → availability →
image short-circuit → access → caps → class levels → optimize → effort. `--explain` attaches the full
trace with a reason on every dropped row.

**Batch.** `--batch seats.json` (or `--batch -` for stdin) routes a whole team in ONE call — a
planning agent designs every seat at once and needs one deterministic assignment table, not N
shell calls. Input is a JSON array of seat objects (or `{"seats":[...]}`); each seat is the
interview as an object with a unique `name`, the same vocabulary and required-ness as the flags
(`"caps":["image"]` short-circuits the same way), and an unknown key is a refusal. The CSV load
and the catalog join happen ONCE for the batch; every seat still goes through the same selector,
so a batch of one produces exactly the flag form's verdict. Output is one object with the seats in
INPUT order, the name mapping each verdict back:

```
{"verdict":"route-batch","seats":[
  {"name":"planner","verdict":"route","harness":…,"model":…,"mode":…,"effort":…,"effort_is_floor":…,"alternates":[…]},
  {"name":"fixer","error":"zero_candidates","details":"…"}]}
```

Exit 0 only when EVERY seat routed; 1 when any seat errored. A per-seat error never aborts the
batch — every seat's problem lands in its own entry so the whole plan is fixed in one pass. A bad
envelope (unreadable/unparseable input, empty stdin, empty or duplicate-named seat list) refuses
the whole call with one `{"error":"malformed_request","details":[…]}` and routes nothing.
`--explain` attaches each seat's own trace to its entry. `--batch` combines with none of the
interview flags, `--caps` or `--catalog`.

| Verdict | Shape | Exit |
|---|---|---|
| route | `{"verdict":"route","harness":…,"model":…,"mode":"cli"\|"api","effort":1-5,"effort_is_floor":false,"alternates":[{"harness":…,"model":…,"mode":…}]}` | 0 |
| route-batch | `{"verdict":"route-batch","seats":[{"name":…,"verdict":"route",…} \| {"name":…,"error":…,"details":…}]}` — seats in input order | 0 only when EVERY seat routed, else 1 |
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

Routing axes live in **`tool/models.csv`** — data the owner edits without touching code. Launch
mechanics (harness-native id, effort ladder, auth) stay in **`tool/catalog.js`**. Route joins them
on `harness`+`model`, and a CSV row with no `catalog.js` twin is excluded with a loud stderr
warning: route must never name something cast cannot launch.

Columns: `mode` (cli|api) · `harness` · `model` · `efforts` (max N, 0 = inert) · `image` (Y/N) ·
`web` (Y/N) · `level` (SOTA|L1|L2|L3|L4) · `reasoning` (1-7) · `coding` (1-7) · `cost` ($ per M
output tokens, **public API list price** — comparable and stable, never the personal
subscription-effective cost) · `use` (route|panel|off) · `quality-override` (Y/N) ·
`price-override` (Y/N).

**The three owner switches** (added 2026-08-22, owner ruling). They are the only columns that
change WHO competes and WHO wins without touching a score:

| Column | Values | What it does |
|---|---|---|
| `use` | `route` (blank reads as this) | the normal state — the row competes for verdicts. |
| | `panel` | no verdict may name it, but it stays in `cast route --catalog`, the roster a panel spreads its seats across (`references/panel.md`). For a model worth a second opinion and never worth being the single answer. |
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
this vault: `claude/sonnet-5` carries a Claude subscription that makes its $10 list cost effectively
~5x lower, so it sits at **L2 and L3** and is reachable by both `bounded` and `mechanical`, winning
each on its `price-override=Y`. The join onto `catalog.js` is on harness+model and every copy
resolves to the same launch spec, so nothing about launching is ambiguous. What remains forbidden
is the ACCIDENTAL duplicate: two lines for one model that disagree on any cell other than `level` —
`test_route.js` fails on it, because route would otherwise rank the same model twice under
different numbers. Adding a level to a model changes every verdict in the classes that reach it, so
it is an owner decision, never a fix applied in passing.

**Per-vault override**, whole-file replace: `{vault}/.rbtv/config/modules/core/sub-agents/models.csv`.
If that file exists it IS the catalog and the shipped CSV is ignored entirely.

The CSV carries **the latest models only, per provider**. Pruning it does NOT remove launch
support — `cast codex gpt-5.5 3` still launches, it just stops being an answer route can give.
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
cast api <model> <effort 1-5> (-p TEXT | -f FILE) --output-folder DIR [--image] [--target-file PATH] [--timeout N] [--grounded] [--extra-params JSON] [--dry-run]
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

Split 2026-08-20 from one 2052-line `cast.js` into a front door plus one module per verb, cut on
the section banners that file already carried. Nothing was rewritten: every composed argv and
every stdout surface is byte-identical across the split (163-invocation corpus, both suites).

| File | What it owns |
|---|---|
| `tool/cast.js` | the CLI front door — argv dispatch and the bare launch path, nothing else |
| `tool/catalog.js` | LAUNCH mechanics only — harness-native id, effort ladder, auth (see Spec source) |
| `tool/models.csv` | the ROUTING axes — level, scores, cost, web, image. Owner-editable; overridable per vault |
| `tool/lib/core.js` | shared primitives: argv parsing, model/effort/folder resolution, the model table, `doctor`, `list` |
| `tool/lib/handles.js` | the launch-handle registry — the one observable a watcher uses to find a run again |
| `tool/lib/launch.js` | spawn, `cast seat`, `cast resume` |
| `tool/lib/sessions.js` | the per-harness session-store readers and `cast sessions` |
| `tool/lib/monitor.js` | `cast monitor` — the freeze tripwire, its witness channel, roster and watch |
| `tool/lib/route.js` | `cast route` — the selector |
| `tool/lib/api.js` | `cast api` — the API-worker runner (Google only) |
| `tool/lib/help.js` | `-h` output: the top-level page and the per-verb pages |

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
node tool/test_cast.js       # -> all cast tests passed
node tool/test_route.js      # -> all route tests passed
python3 -m pytest tool/api/tests/ -q
```

`test_route.js` asserts EXACT verdicts against the shipped `models.csv`, so editing that file's
levels, scores or costs reddens the suite on purpose: the CSV IS the routing decision, and a silent
edit to it silently changes every answer route gives.
