# rbtv-goal — the goals-tree machinery

The deterministic surfaces over the CMP-4 goals tree. Built for task 7.63; the command
grammar is owner-ruled (`r-763-grammar-ruled` — all four decision items at their recommended
defaults) and is **implemented here, not re-derived**.

```
rbtv-goal scaffold <goal-name> --contract FILE|-  --lane daemon|console
                                                  [--type T] [--kind K] [--due DATE]
                                                  [--execution-mode interactive|autonomous] [--dry-run]
rbtv-goal reindex
rbtv-goal lint <goal-name>
rbtv-goal materialize <goal-name> --catalog-root DIR [--force] [--dry-run]
rbtv-goal lane <goal-name> [--set daemon | --set console]
rbtv-goal pause <goal-name>
rbtv-goal resume <goal-name>
rbtv-goal dag <goal-name>
rbtv-goal add-seat <goal-name> --seat X --after a[,b] [--before x[,y]]
                               --bindings SHEET.json --catalog-root DIR
                               [--splice-only] [--allow-daemon-complex-cell]
                               [--allow-open-execution] [--dry-run]
rbtv-goal teardown <goal-name> [--yes] [--dry-run] [--ignite-bin PATH]   # ⚠ NEEDS THE DAEMON UP
rbtv-goal selftest
```

`--root` (the `.rbtv/goals` root) and `--json` are accepted on either side of the verb. Without
`--root` the root is found by walking up from the working directory.

**⚠ `teardown` is the ONE verb here that requires the daemon to be running**, and it is the one
exception to the local-file-operations property every other verb has. What it reclaims is the job
CATALOGUE, which lives in the machine's `heart.db` and is served only by the gateway (`ignite/CLAUDE.md`
§ State layout — "the jobs catalogue is not readable without the daemon"). It refuses typed
(`daemon-unreachable`) rather than half-working, and it reads auth from the environment the `ignite`
client already reads (`IGNITE_SENDER_TOKEN`, `IGNITE_GATEWAY_ADDR` / `server.json`).

**`--kind interactive|non-interactive`** (default `interactive`) stamps `goal-kind` into `goal.md`
frontmatter. Owner ruling `d-owner-batch1` (2), 2026-08-08: the frontmatter IS the carrier — a
consumer looks the kind up on the descriptor and it is never carried on a queue row.

**`--execution-mode interactive|autonomous`** (default `autonomous`) writes the goal's
`execution-mode` file — the per-goal OWNER-CONTACT policy (registry concept `execution mode`),
gate 2 of all agent-initiated owner contact. Owner ruling 2026-08-10: **no creation path wrote
this file until then**, so every created goal was born mode-less and the question "was this goal
meant to be autonomous?" had no answer on disk. `scaffold` now always writes it, one word plus a
newline — a comment or header line in that file would read as "not interactive" and silently make
the goal autonomous.

The default is `autonomous` because that is exactly what an ABSENT file already reads as: writing
it changes no behaviour, it makes the value ATTRIBUTABLE. **This verb derives nothing** — the
workflow-level default (a workflow's declared `default-execution-mode:`, else derived from its
manifest's Modality column) is resolved by the request layer, which is the layer that knows which
workflow a goal is being created for (`goal_creation_request.py#resolve_execution_mode`), and the
resolved word arrives here on the flag. A hand-scaffolded goal names no workflow, so there is
nothing here to derive from; the console entry writes the file explicitly in its own step.

⚠ **`--kind interactive` and `--execution-mode interactive` are DIFFERENT AXES sharing a word**
(open issue `F-96`). `--kind` is the goal-kind stamped in frontmatter (`interactive |
non-interactive`); `--execution-mode` is the owner-contact policy in its own file (`interactive |
autonomous`). Neither is derived from the other.

The `--kind` field is **OPTIONAL on the descriptor**, and that has one consequence worth stating outright:
a goal scaffolded before the field existed carries no `goal-kind` key, **lints clean**, and reads
as `interactive`. So `goal-kind` is deliberately NOT in lint's identity-fields check (the same
treatment `due-date` gets); only its ENUM is checked, and only when a value is present. `reindex`
projects the declared value and leaves the cell EMPTY when the descriptor declares none — the
index reports what each descriptor says, and the default is applied by the reader, in one place
(`seat-folder.js#goalKind`), so the ruled default cannot fork across two files.

**Exit codes** (the `sd-graph` convention): `0` success/clean · `1` refusal, gate-fail, or
not-found · `2` usage error.

**`<goal-name>` is a single folder name directly under `--root`, never a path.** `lint` and
`materialize` resolve it and REFUSE (exit 1) anything landing outside the root — an absolute path
or a `..` traversal. Before the guard, `root / name` discarded the root whenever the name was
absolute: `materialize` wrote a `seat.md` outside the declared root and reported `"ok": true`,
which defeats the only sandbox this tool has (`--root` is how a write verb is aimed at a test tree
instead of a live package). Guarded by `../probes/probe-goal-root-escape.py`, whose red control
runs the pre-fix expression and requires it to escape.

Every verb is a LOCAL file operation — they work with the daemon down, which is why they live
on the `rbtv` side and never on `ignite` (the detached gateway client). v1 ships standalone and
folds into `rbtv goal <verb>` verbatim when the `rbtv` CLI lands (task 7.65) — the operator-surface
stand-in pattern, no contract change at fold-in.

## The verbs

| Verb | Does | Never |
|---|---|---|
| `scaffold` | Creates the goal root — `goal.md` (identity frontmatter + the contract body), `threads.sql` (empty schema), `execution-mode` (one word — the owner-contact policy, `--execution-mode`), `execution-lane` (one word — WHICH LANE runs it, from the REQUIRED `--lane`; task 7.777 — ONE WORD, no second token since `#d-abolish-profile-names`), plus the standard goal-folder artifacts of § below — then reindexes. **No `runs.csv`:** the run register was extinguished in 7.607 (design-lock item 1) and liveness is DERIVED from the goal's tmux room, never stored. Create-only: refuses an existing goal, never overwrites. `--contract` is REQUIRED, so a goal is born lint-green rather than sitting red until a second manual step. | Writes seat folders — seat birth is `materialize`'s step |
| `reindex` | Rebuilds `goals.csv` whole from every `goal.md` frontmatter. Always the full projection; a partial one would leave silent staleness. Fails loud on an unparseable descriptor, naming the file, and leaves `goals.csv` **untouched** — a projection that silently drops a goal is corruption. | Touches any goal folder |
| `lint` | READ-ONLY validate + dry-run emulate (CMP-14). Exit 0 = gate open, 1 = gate blocks, every finding named with file + reason. | **Writes anything, ever** — conflating lint and materialize breaks the read-only contract |
| `materialize` | Creates `seats/<seat>/` per `taskforce.csv` row and assembles each `seat.md`; writes permissions. Assembles everything in memory FIRST, so a mid-assembly failure never leaves a half-materialized run. **Refuses (exit 1, nothing written) a manifest whose after-graph does not validate** — the same acyclicity + guard-grammar arm `lint` runs, now unskippable at the registration act (7.456/MC14). | Touches cognitive-unit sources, catalogs, or `taskforce.csv` |
| `lane` | Shows or sets WHICH LANE runs the goal — the daemon's pickup button (§ below). With no `--set` it is read-only orientation. Works **daemon-down**: it is a file read and a file write, which is most of why the trigger is a file. | Runs anything, or creates a goal — it assigns an EXISTING one |
| `pause` / `resume` | Stashes the lane assignment behind a `paused ` prefix and hands it back byte-for-byte (§ below). Bounds **SEEDING only** — see the warning there. | Stops a running session, or invents a lane |
| `dag` | READ-ONLY one-shot graph view: every `taskforce.csv` row with its predecessors (through the after grammar, never a comma split) and its execution state derived from `executions.csv`, in dependency order, plus `seats/` folders with no row. | Writes anything, or stores a state — every field is derived |
| `add-seat` | Grows a **paused** goal's roster: gates, mints the seat through `materialize-seats.py`, then splices it into the after-graph in ONE atomic registry write (§ below). | Runs without a pause, splices before minting, or rewrites a row it did not re-parent |
| `retry-threshold` | Shows or sets the consecutive-FAIL bar the dod-judge escalates to the owner at (§ below). Bare, it is READ-ONLY orientation. | Enforces the bar, or resolves it for the gate — `coord.py#resolve_retry_threshold` is the authority; this verb writes the two files it reads |
| `teardown` | Reclaims the goal's JOB-CATALOGUE rows so its NAME is free again (`IPH-27`, § below): removes their pending queue rows, then `deregister-job --purge`es each one, in the one order the purge guards admit. Ids come from the goal's OWN `taskforce.csv`, so another goal's row can never enter the set. **⚠ The only verb here that needs the daemon UP.** | **Deletes the goal FOLDER** (owner-ruled 2026-08-12 — it cannot prove it created that directory), kills a live session, or cascades a queue row it did not name |

### `lane` — the daemon's pickup button (owner ruling `d-daemon-lane-button`, 2026-08-10)

```
rbtv-goal lane <goal>                                   # which lane runs this right now?
rbtv-goal lane <goal> --set daemon                      # every seat declares its own cast
rbtv-goal lane <goal> --set daemon                           # …REFUSED if any seat is uncast
rbtv-goal lane <goal> --set console
```

One word in `<goal>/execution-lane`, on the `execution-mode` file's precedent. The ignite daemon's
watch pass (`ignite/engine/lane-watch.js`, fired by the daemon loop before every tick) reads it and
seeds the goals assigned to it through `engine.seedGoal`; the console lane is `rbtv run`.

- **ABSENT MEANS `console`.** An unreadable file, a junk word and a missing file are ONE answer —
  the daemon adopts ONLY goals explicitly assigned to it. Fail-closed on purpose: the opposite
  default would have adopted every goal folder already on disk the first time the daemon ticked.
  ⚠ **A goal scaffolded since 7.777 is never absent**: `scaffold --lane` is REQUIRED, so the
  marker is written at birth and this reader's absence arm covers only goals older than that (or
  a `pause`, which stashes the assignment behind a prefix both readers resolve to `console`).
- **`--set daemon` REFUSES A GOAL WITH ANY UNCAST SEAT, AND NAMES THEM** (`#d-abolish-profile-names`
  sub-ruling 3, 2026-08-12). This door once demanded `--profile <name>` as the fallback such a seat
  would launch on; the flag and the fallback are both gone, so an uncast seat has nothing to run as
  and handing the goal to the daemon would queue rows whose only possible outcome is
  `E_UNCAST_SEAT` at spawn, hours later. The predicate is `engine/seeding.js#uncastSeats` — the
  same one `rbtv run` and the daemon's own lane watch ask — so no two doors can disagree.
  An UNMATERIALIZED goal is its own refusal (`lane-cast-unknown`): "unknown" is not "none".
- **The marker is written temp + rename**, like the execution record beside it: a truncate-then-write
  leaves a window where the file reads EMPTY, which the daemon's reader resolves as `console`.
- **FLIPPING IT MID-GOAL IS THE POINT.** The daemon lets go on its very next pass and the other lane
  resumes from the goal's execution record with nothing re-run — start in the daemon, finish in the
  console, or the reverse. A goal a console runner is attached to right now is never seeded against
  (the run lock is READ, never taken). Measured end to end:
  `ignite/engine/probes/probe-daemon-lane-watch.js`.
- The marker's TERM is **lane assignment**, values `daemon | console` — minted registry-side
  2026-08-10 (`system-definition/decisions.md#d-lane-assignment`, `concepts/lane-assignment.md`);
  this build coined no noun and the filename stays descriptive. `console` (who SHOULD run the goal)
  and `attached` (how an execution-record row RAN) are the same lane's two readings — ruled, and
  stated in that concept file alone.

### `pause` / `resume` — the lane stash (issue `S-33`)

```
rbtv-goal pause  <goal>      # execution-lane: `daemon claude-sonnet` -> `paused daemon claude-sonnet`
rbtv-goal resume <goal>      # …and back, byte for byte
```

**The marker grammar is one token wider, and NEITHER READER CHANGED.** `pause` rewrites
`<goal>/execution-lane` to `paused ` + whatever it said before, verbatim; `resume` strips exactly
that prefix and writes the remainder back. Both lane readers — `goal_cli.read_lane` and
`engine/lane-watch.js#readLane` — already resolve any first token that is not `daemon` to
`console`, so a paused marker reads as "not assigned to the daemon" on both sides with zero reader
change. The daemon lets go on its next watch pass; the stashed assignment is still on disk, and
`lane --json` reports `paused` / `paused_from` so nothing has to be inferred.

- **Pausing bounds SEEDING, not EXECUTION.** It stops the daemon starting anything NEW for this
  goal. It does **not** stop a session that is already running, and it does not touch an attached
  `rbtv run` (which never reads the marker). "Nothing new starts" is the guarantee; "nothing is
  running" is `add-seat`'s quiescence gate, which is a different check against `executions.csv`.
- **`pause` is idempotent** — a second pause does not double the prefix, and reports the stash it
  already holds.
- **`resume` refuses `not-paused`** rather than stripping a prefix that is not there: doing so
  would rewrite an assignment nobody paused.
- **`lane --set` refuses `lane-paused` while the stash is held.** `--set` writes the marker WHOLE,
  so setting a lane during a pause would discard the stashed assignment silently — and leave the
  operator believing the goal is paused while the daemon reads it as assigned.
- Absent file → the stashed text is `console`, which is what an absent file already reads as.

### `retry-threshold` — the milestone retry bar (issue `IPH-11`, owner ruling 2026-08-11)

```
rbtv-goal retry-threshold <goal>                      # show: the resolved bar and which rung answered
rbtv-goal retry-threshold <goal> --set 3              # the per-goal default -> <goal>/retry-threshold
rbtv-goal retry-threshold <goal> --milestone m4 --set 5   # the override -> milestones.csv's column
rbtv-goal retry-threshold <goal> --milestone m4 --unset   # clear it; the next rung answers
```

The bar the produced taskforce's dod-judge escalates to the owner at. Three rungs, first hit wins:
the milestone's own `retry-threshold` cell in `milestones.csv` · `<goal>/retry-threshold` · **2**.

- **This verb is not the authority — `coord.py#resolve_retry_threshold` is**, because that is the
  function the escalation gate calls. This verb writes the two files that resolver reads, and
  `goal_cli`'s selftest cross-checks the three literals against `coord.py`'s own source rather than
  bridging them. A seat READS the resolved bar from `coordinate fail-status <milestone-id>`, which
  answers off the same resolver — so no prompt ever states a number.
- **The floor is 1, not 0.** The gate reads `count < bar`, so `bar = 0` is never true and the goal
  would escalate on ZERO FAILs — the safety switched off by a value that looks like it tightened it.
  A non-integer, `0`, `-1` or an empty `--set` refuses `retry-threshold-invalid` and writes nothing.
- **Write refuses vs. read falls back, deliberately.** `--set` refuses loudly; the READER warns on
  stderr and falls back to the next rung, because refusing there would append no escalation row and
  fail OPEN — silently disabling the halt.
- **`--milestone` edits `milestones.csv` LINE-PRECISELY, never through a csv round trip.** The file
  carries quoted multi-clause `done-when` prose that a round trip re-renders to satisfy one cell.
  A missing column is APPENDED to every line — the one structural edit that adds bytes and rewrites
  none. Refuses `milestone-unknown` for an id with no row.
- **`--set` refuses `pass-open` while an execution row carries an empty outcome.** `check-unblocked`
  asserts `milestones.csv` is byte-identical across its own pass, so a write landing mid-pass fails
  a criterion the writer never sees. A HALTED goal's rows are all closed, so the case the owner
  actually raises the bar in is never barred.

### `add-seat` — growing a LIVE goal's roster (issue `S-33`)

```
rbtv-goal pause my-goal
rbtv-goal add-seat my-goal --seat reviewer --after builder --before shipper \
                   --bindings .rbtv/config/.../bindings.json --catalog-root <dir> --dry-run
rbtv-goal add-seat my-goal --seat reviewer --after builder --before shipper \
                   --bindings … --catalog-root …
rbtv-goal resume my-goal
```

A goal that is already running turns out to need a seat nobody planned. `add-seat` inserts it
BETWEEN existing seats: the new seat waits on `--after`, and each `--before` successor is
re-parented onto the new seat — but only for the members it shares with `--after`. An insertion
re-parents the edges it sits on and nothing else.

**Write order is MINT-then-SPLICE, never the reverse.** `materialize-seats.py` writes the seat's
descriptors before its registry row (its own discipline). Splicing first would point live `after`
cells at a seat that does not exist yet — a window the daemon could seed against. Minting first
leaves the opposite window, which is harmless: a seat nothing waits on. `--splice-only` is the
**crash resume** for a run that died in that gap; it skips the mint and finishes the rewiring.

**Which checks fire under `--dry-run`, exactly.** Everything computable from the PRE-MINT registry
fires under a dry run — a dry run that skipped them would rehearse a different act — and, since
the same checks now run before the mint on a real run, a refusable splice never mints. Only three
checks are post-mint-only, because each needs the file the mint just wrote:

| When it fires | Checks |
|---|---|
| **Every run, including `--dry-run`** (pre-mint) | `goal-not-paused` · `goal-not-quiescent` · `splice-target-has-run` · `attached-run-live` · `bindings-missing-seat` / `bindings-unreadable` / `bindings-schema` · `daemon-complex-cell` (warns under `--dry-run`) · and the **preflight splice** checks: `splice-before-unknown` · `splice-not-an-insertion` · `taskforce-noncanonical` / `taskforce-tail-unterminated` / `taskforce-empty` / `taskforce-header-drift` |
| **Post-mint only** | `splice-no-row` (pre-mint the new seat has no row by construction) · `spliced-graph-invalid` (the acyclic + grammar validation of the ACTUALLY-MINTED rowset) · `taskforce-changed-underfoot` |

Each refuses with a CODE (machine-readable on `--json`, so an agent never matches prose):

| Code | Refuses |
|---|---|
| `goal-not-paused` | the goal is not paused — the seeder reads `taskforce.csv` every cadence and this act rewrites it |
| `goal-not-quiescent` | a seat's LAST `executions.csv` row carries an EMPTY outcome: it is still going, and re-parenting the graph under it changes what its successors wait on mid-turn. The refusal NAMES each offending row (seat, session-id, started). ⚠ **`--allow-open-execution` is the escape** — a KILLED run's row is never closed by anything, so without the flag this gate is permanent. Pass it only when the session is genuinely gone; passing it while a session is alive re-parents the graph under a running seat, which is the exact damage the gate exists to prevent |
| `splice-target-has-run` | a `--before` seat already has execution-record rows, so its `after` cell was resolved once — re-parenting now makes the registry describe a graph that never ran |
| `attached-run-live` | the goal carries `.attached-run.lock`: an `rbtv run` engine is advancing the same graph |
| `bindings-missing-seat` | the shared sheet has no entry for the seat (which harness/model/effort it runs on has no honest default) |
| `daemon-complex-cell` | the run would write a multi-member or guarded `after` cell AND the stashed lane is `daemon`. WARNS under `--dry-run`; `--allow-daemon-complex-cell` accepts it deliberately. The parallel seeder fix (`engine/seeding.js`) lifts this concern once deployed |
| `splice-before-unknown` · `splice-not-an-insertion` · `splice-no-row` | a `--before` seat with no row · a `--before` cell sharing no member with `--after` (so the new seat would not be BETWEEN anything) · a new seat with no registry row (`--splice-only` before the mint) |
| `taskforce-noncanonical` | a registry row that does not re-render byte-identically through the append's own csv writer — see below. **CRLF line endings refuse under this code with a message naming them**: the registry's canonical form is LF-only and nothing is normalized for you |
| `spliced-graph-invalid` · `taskforce-changed-underfoot` | the MUTATED graph fails the same `check_acyclic` + `check_after_grammar` pair `materialize` runs, in the same order · another writer touched the registry between the read and the write |

**The canonical-form guard is what makes the promise checkable.** Before mutating anything, every
row is re-rendered through the **same** writer the registry append uses (`render_csv_line`, which
`materialize-seats.py#_render_csv_line` now delegates to) and must come back byte-identical. Without
it a hand-edited registry — one unnecessarily quoted cell — would be silently REFORMATTED on the way
through, every line changed and the diff unreviewable. With it, `add-seat`'s actual promise holds:
**every line but the re-parented ones is byte-unchanged**, and the registry is replaced in ONE
atomic write.

Guards and alternates survive: the substitution runs through the one after-grammar substitution
(`substitute_after_ids`), so a `[key=value]` span passes untouched even when its value spells a seat
id, and members replaced more than once collapse order-preservingly (`a,b` → `new`, never
`new,new`). `--bindings` takes the goal's SHARED sheet; a one-seat scoped copy is written to a temp
file **outside** the goal folder for the mint and removed in a `finally`.

Measured end to end by `../probes/probe-goal-splice.py`
(`node deploy/probe-suite.js --only goal-splice`), which runs the real command as a subprocess.

### `teardown` — reclaiming a goal's NAME (issue `IPH-27`, owner ruling 2026-08-12)

```
rbtv-goal teardown my-goal --dry-run     # the plan: every row that would go, nothing changed
rbtv-goal teardown my-goal               # …then delete the folder yourself
rbtv-goal teardown my-goal --yes         # the ORPHAN path, when the folder is already gone
```

Scaffolding a goal WRITES job-catalogue rows — one `seat-<goal>-<seat>` per seat from
`engine/seeding.js#seedTaskforce` on the goal's first seed. *(A `<goal>-workflow-start` row from
`capabilities/goal-creation-request` was the other producer until task 7.778 deleted that door;
rows minted before then are still on disk and are still this verb's to reclaim.)* Deleting the goal folder removed none
of them, and `register-job` is create-only, so **the goal's NAME was burnt**: 18 stranded rows for
one goal on the live box, and a same-name re-scaffold refused `E_JOB_EXISTS`. `ignite
deregister-job --purge` made the rows reclaimable; this verb is what calls it.

**Run it BEFORE deleting the folder.** With `taskforce.csv` present the ids are COMPOSED from the
goal's own seat registry — reconstructed, never guessed — so no other goal's row can be in the set.

| It does | It never |
|---|---|
| removes the goal's pending queue rows, then deregisters + purges each catalogue row — in that order, because a pending row refuses the purge | forces past a guard, or cascades a queue row it did not name |
| refuses UP FRONT, atomically, if ANY of the goal's jobs has a non-terminal execution, naming each | kills a live session — `ignite kill <session-id>` is a separate, deliberate act |
| leaves the goal FOLDER completely untouched and says so | delete a directory it cannot prove it created (the same reasoning `goal_creation_request.py` records for building no unwind on a failed scaffold) |
| treats an id that was never registered as normal, not an error | report success over a catalogue it could not read — a transport failure is its own typed refusal |

**The orphan path, and the collision it has to survive.** With the folder already gone there is no
registry to read, so ids are matched by NAME (`seat-<goal>-`) — and **a goal name can be a prefix of
another goal's name**; this workspace carried a live pair (`throwaway-0811-settle` /
`throwaway-0811-settle-kill`). Rows belonging to a still-present shadowing goal are therefore
**EXCLUDED** from the sweep and listed as excluded, and the remaining name-matched list is PRINTED
and requires `--yes`.

⚠ The exclusion cannot see a shadowing goal whose folder is ALSO gone: nothing in
`seat-<goal>-<seat>` says where the goal name ends (seat names carry `-` too —
`seat-meeting-digest-plan-check-edges`), so that case is undecidable from the data and the printed
list is the only guard. **Read it.** The first cut of this made the shadow check a *refusal* gated
on `not --yes`, so the flag confirming the orphan list also switched off the shadow protection —
`../probes/probe-goal-teardown.js` caught that on its first run, and excluding replaced refusing.

Measured end to end by `../probes/probe-goal-teardown.js`
(`node deploy/probe-suite.js --only goal-teardown`), which boots its own throwaway daemon and runs
the real command as a subprocess — never the live daemon, never the live catalogue.

### What `lint` checks

Folder name ≡ `goal.md` name · cross-goal name uniqueness · identity fields present · thin goal
state and type in their enums · the goal-radius contract body is non-empty · CMP-4 goal-level
layout · `milestones.csv` / `taskforce.csv` parse · every
taskforce row resolves to a REAL seat with a parseable `seat.md` · the `after` graph is acyclic
(guards `ref[field=value]` stripped, alternates `a|b` split) and every predecessor names a real
seat row · **every guard and alternate is well-formed** (below) · each seat's binding matches the
`taskforce.csv` row it was copied from · every
frontmatter cognitive-unit reference has its assembled block in the body · permissions well-formed
· dry-run dispatch emulation (would this seat launch under its resolved harness+model+effort — no
launch, no LLM call).

### The standard goal-folder artifacts `scaffold` writes (7.582 / owner ruling R21; set extended by 7.595 / Q16)

Seven of the ten files are written from **deterministic templates in `goal_cli.py`** — module-level
strings, the `THREADS_SCHEMA` precedent. **No agent is in the path**, and two scaffolds of the same
goal name produce byte-identical files.

| Written | What it is |
|---|---|
| `CLAUDE.md`, `AGENTS.md` | the ROUTER, one per supported harness. It names the sibling artifacts and where to write, and carries no content of its own. `AGENTS.md` is `CLAUDE.md`'s body behind a header saying so |
| `issues.md`, `decisions.md`, `doubts.md`, `gotchas.md`, `ideas.md` | the five **write-if-something** files. Nothing obliges an entry; an agent with nothing to note writes nothing |

`decisions.md` is the one write-if-something file with its OWN template body (`DECISIONS_TEMPLATE`),
per owner ruling **Q19** (2026-08-09, `d-owner-batch-q12-q19-0809` item 8): a created goal carries
the **durability split** from birth — goal-durable rulings in the goal's `decisions.md`, and
PROVISIONAL (`p-*`) rulings alongside them, ALL DURABLE and pruned by hand (7.607 design-lock item
6: no automatic mortality boundary, because there is no run to die with) — and adopts the entry shape **by
citation** of `orchestration/workflows/_shared/authoring/decisions-discipline.md`, restating none of
its rules. This is the same convention the vault's `.rbtv/goals/CLAUDE.md` § decision-ledger states
(`r-decision-ledger-contract`); the template agrees with it rather than re-legislating it.

`ROUTER_FILENAMES` is **measured, not assumed**: it is the distinct set of `guidance_file.convention`
values across every model package manifest (`orchestration/models/*/manifest.yaml`) — `CLAUDE.md`
(claude-code-cli) and `AGENTS.md` (codex-cli, kimi-code-cli, opencode). The API packages and
claude-code-native omit `guidance_file` deliberately: those workers load no workspace guidance file,
so no router of any name reaches them. A package adopting a third convention adds its filename to
that tuple and nothing else changes.

The router also carries the **tooling-gap filing rule** (owner ruling 2026-08-10, issue
`i-wrote-outside-own-seat-first`): a defect found in a TOOL goes to the `issues.md` of the goal that
OWNS that tooling, with this goal's own `issues.md` as the fallback when that ledger is unreachable.
It is materialized rather than remembered, and it reaches every seat under the goal because
`server/spawn/cage.js` masks path-up instruction files EXCEPT inside `.rbtv/goals`. The same text —
from the ONE `TOOLING_FINDING_BLOCK` constant here — is rendered into each seat's own `AGENTS.md` by
`team-kit/materialize-seats.py`, which imports it rather than restating it (the carriage a
hand-authored goal `CLAUDE.md`, e.g. a standing seat's, does not get from this template).

`write_standard_artifacts` is **skip-if-exists per file**. `scaffold` refuses an existing goal
outright so it never meets one — the guard lives in the writer because these are the files agents
write INTO, and an overwrite there is data loss. Scored by
`probes/probe-goal-scaffold-standard-files.py` (`--only goal-scaffold-standard-files`), whose two
mutants prove the presence arm and the no-clobber arm can each go red.

**Registry note:** `ideas.md` was deliberately EXCLUDED under R21 alone (scaffolding it would have
been this tool minting a convention no ruling named). That exclusion is **superseded by owner ruling
Q16** (2026-08-09) — the ruling now names it, so `ideas.md` is scaffolded and a created goal matches
the live `build-core-daemon-mvp` goal's three-ledger shape (`issues.md` / `decisions.md` /
`ideas.md`).

### The guard-grammar arm (7.426) and its carve-out

`lint <goal>`, `check-acyclic <file>` and — since **7.456 / MC14** — the `materialize` ACT validate
the `after` member grammar **on top of** acyclicity. Two rules, and a refusal names the one it broke:

| Rule (the finding's `check` string) | Refuses |
|---|---|
| ``guard grammar `ref[field=value]` `` | a member carrying brackets that is not a guard — `a[nokey]`, `a[k=v]x`, an unclosed `a[k=v`. `parse_after_member` hands such a token back WHOLE, so the evaluator looks up a seat literally named `a[nokey]`, finds nothing, and the edge is permanently unmet with no reason given. Refused at registration instead. |
| ``alternate grammar `a|b` `` | an empty alternate limb — `a|`, `|b`, `a||b`. An alternate joins two NAMED predecessors. |

**Grammar only.** The arm rules on ADMISSIBILITY, never on whether a guard is satisfied — that
evaluation is `coord.ready_seat_rows`', against the ruling recorded in
`coordination/guard-values.csv`. A clean
verdict here says the manifest is well-formed, nothing about how it will route.

**One decomposition, imported.** The member grammar is decomposed in exactly one place in this
system — `coord.py`'s `parse_after_member` and `after_member_limbs` (7.424/W1 collapsed the two
readings that used to exist; `one-readiness-predicate.md` collapsed the second copy of the limb
split). `after_member_grammar()` / `after_member_limbs()` import them; there is no copy of the grammar in this file, and if
the import fails the check REFUSES rather than reading clean. The same import backs
`check_acyclic`'s edge extraction, which previously truncated a member at its first `[` — under
that reading `a[g=y]|b` lost limb `b`, and a cycle through it was reported clean (the
strip-then-split defect #3386, closed here; the selftest keeps the control).

> **⚠ CARVE-OUT — the proof surface of this arm is the TEST GOAL, and nothing here is wired into
> the live room.** The arm activates only where a verb invokes it (`lint`, `check-acyclic`, and
> since 7.456/MC14 `materialize`, where it REFUSES the act rather than reporting on it); no
> daemon lane, job or watcher calls it, and 7.426 performed **no live-room wiring**. Live-room
> adoption is a separate, later act behind `r-cutover-gated`
> (`.rbtv/goals/build-core-daemon-mvp/decisions.md`). What was measured, not assumed: the live
> `build-core-daemon-mvp` run-3 `taskforce.csv` (356 rows, 331 members, 6 guarded, 0 alternates)
> yields the SAME two lint findings before and after this change — the arm adds none there. That
> is a measurement of one package, not a licence to adopt.

### How `materialize` assembles a seat

The settled **catalog indirection** (`d-seat-assembled-projection`): a `seats.csv` row joins an
executor (`prompt-id`) and a `task-id`; the unit references live on the `prompts.csv` / `tasks.csv`
rows, never on the seat row. Units resolve to files under `--catalog-root` by frontmatter `id`.

- **Frontmatter** = the seat id + description, the executor binding copied from `taskforce.csv`
  (`harness` · `model` · `effort` · `ctx-refresh`), and the RESOLVED unit references — the
  assembly-lockfile realization. Plural kinds take list values (YAML forbids duplicate keys).
- **Body** = one kind-named XML block per unit, stamped by the assembler with `id` and `version`
  attributes. ASSEMBLED kinds carry their full content; INVOKED kinds (`capability`, `reference`)
  enter as loader stubs — description + entry-point pointer — and stay `@latest`.

Source unit files use the settled form: a **kind-named tag with no attributes** (`<persona>…`),
with the `id` in frontmatter only. The office-scaffold prototype's `<cognitive-unit id kind>`
wrapper is superseded and is not read.

## Stand-ins and divergences

`--catalog-root` is **required and explicit**. The live rbtv repo carries no CMP-5
component-database — no `cognitive-units-index.csv`, no `seats.csv` / `prompts.csv` / `tasks.csv`,
no `cognitive-units/` pools; CMP-5 is status `draft`, designed-unbuilt. Rather than guess a path
into a tree that has no such shape, `materialize` refuses with that reason named.

**Version strings are a STAND-IN, not the settled schema.** CMP-5 resolves versions through a
repo-root `cognitive-units-index.csv` mapping version-id → (commit, filepath). Until it exists, a
frozen `@latest` records `latest+standin-sha256:<12>` over the unit file's bytes — the lockfile
stays pinned and re-checkable without inventing an index schema. The marker is greppable and every
assembled `seat.md` carries the warning in its header. **When the index lands this format is
REPLACED by real version-ids, never grandfathered.** (Registry divergence 5.)

Registry divergences flagged for transcription — **never applied to `system-definition/`**:

1. **Seat-folder naming.** CMP-4 § Layout writes `seats/seat-{name}/`; 7.63's canonical path form
   and both live run packages use bare `seats/{seat}/`. Built BARE.
2. **Command spelling.** CMP-14 § Layout writes standalone `goal-lint` / `goal-materialize`; D1a
   ruled the one `rbtv goal <verb>` family.
3. **`threads.sql` at scaffold.** Created per the KG shape; the live run's kit `coordination/`
   stand-in stays noted under `r-kg-shape`.
4. **Goal-level watcher state.** CMP-4 and the `goal-folder` record place it at goal level but name
   no file; not invented here.
5. **`cognitive-units-index.csv` absent** — above.

## Safety

`scaffold`, `reindex` and `materialize` MUTATE. `materialize --force` regenerates seat folders,
which on a live run would rewrite the frozen lockfiles of seats that are currently executing —
including, if aimed at the executing package, the run's own. Aim write verbs at a test root with an
explicit `--root`. `lint` is read-only by contract and safe against any package (verified
empirically: a path+size+mtime fingerprint of a live goal folder is identical before and after).

## Verify

```
rbtv-goal selftest        # end-to-end on a throwaway tree; exit 0 / 1
```

`selftest` exercises scaffold (+ its four refusals), `goal-kind` (the default stamped when
`--kind` is omitted, an explicit `--kind` round-tripping to frontmatter, the projected column, and
the lint PAIR — a key-less descriptor raising no finding *beside* an out-of-enum value raising
one, because the clean arm alone would also pass if the check never fired), the read-only property
of lint, name/layout
violation rejection, cycle rejection, the full assembly (frozen assembled refs, `@latest` invoked
refs, stamped XML blocks, loader stubs not inlined), refuse-without-`--force`, `--force`,
refuse-without-`--catalog-root`, reindex's fail-loud-and-leave-untouched behaviour, and the
guard-grammar arm (clean guarded manifest, malformed guard, empty alternate limb, a cycle through
an alternate limb, and the control that the arm stays silent on a clean file), and the S-33 roster
arm (the pause/resume byte-exact round trip, pause idempotence, `lane --set`'s `lane-paused`
refusal, the splice's happy path with every other line byte-unchanged, guard preservation,
alternate dedupe, every `add-seat` gate asserted BY REFUSAL CODE, and `dag`'s ordering and derived
state). Run it after ANY edit to `goal_cli.py` — it must exit 0.

The selftest calls those verbs IN PROCESS. `probes/probe-goal-splice.py` runs the same acts as
real subprocesses, which is what covers verb registration, flag `dest`s, exit codes, and the
MINT half `--splice-only` skips — a read-ordering defect there (splicing a pre-mint snapshot, so a
perfect mint refused `splice-no-row`) was invisible to every in-process arm.

The one row the selftest CANNOT carry is that the grammar is imported rather than copied: it would
have to mutate `coord.py`. That control runs on a mirrored scratch tree — mutate
`GUARDED_MEMBER_RE` there and a manifest that validated clean must go red. Recorded for 7.426 in
`planning/briefing-m6-remainder-drain/mrd-w3-lint-arm-record.md` under the
`build-core-daemon-mvp` goal (written under its then-current `runs/run-3/` compartment — a
historical citation, not a live path).

A selftest sits inside its own blast radius, so it is not sufficient evidence on its own: vary the
invocation (bare, under `timeout`, via `sh -c`, from another cwd, absolute path, piped/no-tty) and
prove the assembly against real captured content, not only its own fixtures.
