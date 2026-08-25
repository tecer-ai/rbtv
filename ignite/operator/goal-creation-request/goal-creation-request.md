# goal-creation-request — the entry a goal-creation request arrives at

Core-build task **7.211** (design id `E16`) of run-3's `no-row-builds-the-entry` pass.

The tool is `tool/rbtv-goal-request`. It takes a goal-creation request, validates it against the
landed request schema, and discharges it as **two ordered acts — create → launch**. (It was
three; the ARM act is retired — nothing is armed per package any more, readiness is recomputed
from disk every cadence.)

**Why this capability exists.** The wave that consumes this entry was designed on the premise that
the entry already existed. The disk refuted it: every consuming row reached for a thing no row
built, and nothing errored — the rows would simply have waited. This capability is the row that
builds it.

## The three verbs

| Verb | What it does |
|---|---|
| `validate <request.json> [--goals-root R]` | Validates field by field and **names every field it checked**. Performs no act. Exit 0 accepted, 1 refused. |
| `handle <request.json> …` | Validates, then create → launch. A refused request performs **no** act. `--no-launch` withholds the launch act; `--dry-run` writes nothing. |
| `scaffold-and-queue --inbox D --goals-root R --workflow W [--ignite-bin B]` | **The daemon-executed verb** (task C2). Drains a staged inbox: per request, validate → scaffold the goal INTO ITS DECLARED LANE. **Queues nothing, arms nothing, launches nothing** — 7.778 deleted the workflow-start row it used to plant, so the verb's name outlives its second half. Exit 0 when every drained request was accepted (or the inbox was empty), 1 otherwise. |

## `scaffold-and-queue` — the caged requester's path, and the measurements that shaped it

A Slack-caged channel master cannot create a goal directory. The daemon can. This verb is the
daemon's half of that split, and **both halves of its transport were measured before it was
written** (`evidence/c2/probe-c2.js`, 2026-08-08 — captures under the core-build project's
`build/subagent-closeout/evidence/c2/`):

| Measured | Result | What it settled |
|---|---|---|
| A channel-master-shaped **service seat** writing into the goals root, under the SHIPPED cage | `mkdir: Read-only file system`; the target's bytes never reach disk (read from OUTSIDE the cage) | The scaffold MUST happen daemon-side. This is the whole reason the verb exists. |
| The same seat writing inside **its own seat folder** | Writes land | The request PAYLOAD is file-staged there. `fire-tool` argv is static (only `workdir` crosses from a queue row), so no gateway verb can carry a request body to a fired tool. |
| `register-job` at the gateway, per sender kind | owner ✅ · agent ✅ · **bridge ❌** (`authz.canRegisterJob`) | The daemon-side identity the fired tool's door resolves must be owner or agent. A bridge credential refuses **loudly**, naming the enforced predicate and what the sender was seen as. |
| `enqueue-job` at the gateway, per sender kind | owner ✅ · agent ✅ · **bridge ✅** — no authz gate at all | The TRIGGER goes through `enqueue-job`, so the wire holds whichever kind the channel master presents. |

**The inbox is a directory, not a request file**, and that follows from the static argv: one fixed
argument must serve every request, and a drained directory is the only shape that does. Each
request is moved to `<inbox>/done/` or `<inbox>/refused/` as it is handled — without the move, a
re-fire re-processes everything and `V2`/`V3` (goal-name uniqueness) refuses forever, a growing
pile of refusals about work that already succeeded. A refusal is written beside the moved request
as `<name>.refusal.json`, in the folder the requester staged into: **a refusal a caged requester
cannot read is a silent drop.**

**Validation strictly precedes the scaffold.** A malformed or schema-refused payload leaves no goal
directory behind — both arms are exercised in the same fire as an accepted request, so a refusal
that took the accepted request down with it would be visible.

**One partial state is real and is not hidden.** The scaffold is two steps — `rbtv-goal scaffold`
then `scaffold-seats` — so a fire whose second step fails leaves a goal folder with no materialized
seats. The result records it truthfully (`scaffolded: true`, `outcome: REFUSED`, the stated refusal
naming the failed step) rather than rolling the goal back — an unwind here would delete a directory
the daemon cannot prove it alone created.

*(Until 7.778 the partial state was a scaffolded goal with no QUEUED JOB, because the verb ended by
minting and enqueueing a `<goal>-workflow-start` row. That row, its launcher and the whole
`goal-launch-delay` capability that retimed it are deleted; a created goal advances on its LANE.)*

### The orphan that partial state leaves — how an operator finds it and closes it

There is **no unwind, by decision**, so the orphan is an operator's job. This is the procedure; it
is written down because a partial state whose recovery is undocumented is a partial state nobody
closes.

**Find it.** Every orphan is named in the request's own refusal record — `<inbox>/refused/<name>.refusal.json`
— and never only in the goals root. Read these four keys:

| Key | Reads |
|---|---|
| `goal-name` / `goal-dir` | the goal that was scaffolded, and where |
| `goal-exists` | whether the directory is on disk **now** |
| `scaffolded` | `true` the scaffold succeeded · `false` it was never reached · **`null` unknown** — the fire died mid-request and only `goal-exists` is trustworthy |
| `stated-refusal` | which step failed, and its stderr tail |

The whole set of orphans is `refused/*.refusal.json` with `goal-exists: true`. A goal with no
queued job is also visible as a goals-root directory absent from `ignite inspect queue --json`.

**Then close it, one of two ways — the choice is the operator's and neither is automatic:**

1. **Complete it** — the goal is wanted; only part of its content is missing. There is no job to
   re-issue since 7.778: finish the materialization by hand
   (`rbtv-goal materialize <goal>` / `scaffold-seats`, per the failed step named in the refusal
   record), then confirm the goal's LANE is what the requester asked for:

   ```
   rbtv-goal lane <goal>                        # which lane is running this right now
   rbtv-goal lane <goal> --set daemon           # …or console. ONE WORD — no second token
   ```

   The lane marker is written at scaffold time from the request's REQUIRED `execution-lane`, so a
   goal that got past `rbtv-goal scaffold` already has one; check it rather than assume it.

2. **Drop it** — the goal is not wanted. Remove the directory, then rebuild the index, or
   `goals.csv` keeps a row for a goal that is gone:

   ```
   rm -rf <goal-dir> && rbtv-goal reindex --root <goals-root>
   ```

   `rbtv-goal` is `capabilities/goals-tree/tool/rbtv-goal` — name the path unless it is on PATH.

⚠ **Re-staging the same request instead is not recovery.** `V2`/`V3` refuse a goal-name that already
resolves, so a re-stage of an orphaned name is refused forever until one of the two paths above runs.

### The exit code is per-FIRE, and one bad request colours the whole fire

`scaffold-and-queue` exits **1 if ANY drained request was refused**, even when every other one was
accepted and its goal created. That is deliberate — a fire that silently exited 0 while refusing
work would report success for requests that never happened — but it has a consequence an operator
must know before arming, and it is **not softened**:

- The daemon records a fire-tool execution's status from the exit code alone (`ticker.js#recordToolCompletion`:
  `exitCode === 0 ? 'done' : 'failed'`). So **one junk file staged by a channel user marks the whole
  execution `failed`** in `jobs_log`, alongside goals that really were created and queued.
- `failed` here therefore means "not every request succeeded", **never** "nothing happened". The
  per-request truth is only in the JSON on stdout (captured in the execution's tool log) and in
  `<inbox>/done/` vs `<inbox>/refused/`. Read those before treating a `failed` fire as a no-op —
  and never re-stage a whole batch on the strength of the exit code, since the accepted half is
  already scaffolded and would come back as `V2` refusals.
- A monitor that alerts on `failed` fire-tool executions will therefore alert on ordinary requester
  error. Whoever arms this row owns that choice.

### What the inbox defends against, and what it does not

The inbox is a **trust boundary**: it sits inside the requester's own seat folder, so its whole
content — file names, bytes, and directory structure — is chosen by the requester.

| Defended | How |
|---|---|
| A goal outside the goals root | `goal-name` is refused (`V1`) unless it matches `^[a-z0-9]+(?:-[a-z0-9]+)*$`, so no separator, traversal or absolute path survives validation, and validation strictly precedes the scaffold. |
| A goal the requester may not have | `V2`/`V3` refuse a name already taken or declared in the resolved root. |
| **One request wedging the whole surface** | The refusal arm is the **entire per-request body**, not just the JSON read. A directory named `*.json`, an unreadable/dangling entry, and a schema-legal non-string `due-date` each used to raise past the narrow arm and kill the fire with a traceback — and, since the offender never left the inbox, kill every later fire too. Each is now a per-request refusal that settles into `refused/`. |
| **Writes escaping the cage through a symlink** | `<inbox>`, `<inbox>/done` and `<inbox>/refused` are refused if any is a **symlink**: `mkdir(exist_ok=True)` accepts a symlink-to-directory and `Path.replace` follows it, so a pre-created link would have relocated the staged request and its `.refusal.json` to any daemon-writable path. The whole fire refuses and drains nothing. |

| **Not** defended — accepted, and stated | Consequence |
|---|---|
| Volume | No cap on requests per fire. A requester that stages many files makes one fire long; the drain is serial and each accepted request costs two `ignite` calls. |
| A symlink swapped in *during* the fire | The symlink check is a check, so a requester that swaps a real directory for a link between the check and the move still wins that race. Closing it needs directory-fd-relative moves. |
| Disclosure into `refused/` | A refusal record carries the failed step's argv and stderr tail, written where the requester can read it — daemon-side absolute paths and gateway error text included. That is the same property that makes a refusal readable at all. |

### Arming it is two gated acts, in this order

The catalogue entry `tools: goal-creation-request` in `config/spawn-profiles.yaml` is landed **dark**.
Landing it does not arm it:

1. create the inbox directory the entry names (`.rbtv/goals/_channel-master/requests`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read.

*(There was a third — `ignite register-job goal-creation-request --action-type fire-tool …` then
`ignite add-job` — which registers the FIRE-TOOL row that runs this verb. It is unchanged and still
required to make the tool fire; what 7.778 deleted is the SECOND registration this verb performed,
of a per-goal `start-workflow` row. Renumbered here because the two were being read as one gate.)*

Out of order, step 2 logs one `catalogue-paths` error per boot for an `--inbox` that does not exist
yet (that check logs; it never refuses the boot).

⚠ **`--workflow` is RULED — `plan-console`** (owner ruling `d-owner-q10-launcher-0808` (1), 2026-08-08; the workflow was named `planning` until its 2026-08-24 rename, which moved the shipped value and nothing else;
task C5). It names what EVERY master-created goal that does not route to a pre-existing workflow is
materialized with: the meta component `3-resources/tools/rbtv/meta/planning/`, whose chain root is
`plan-interviewer`. ⚠ **`--entry-seat` is GONE** (7.778): it existed only to fill the deleted
workflow-start row's argv, and nothing at this door opens a seat any more.

⚠ **REPOINTED 2026-08-10 (issue C-2) — the ruling held, the component moved.** The pair originally
landed against `3-resources/tools/rbtv/meta/planning-deprecated/` (itself RENAMED from `planner-workflow/` by
the planning-v4 stage-B rename, vault commit `01f60de16`; task 7.598), entry seat `elicitator`. That
component was DELETED and the pair went stale: every daemon-fired creation refused
`workflow-unknown` at `create-package` — `probe-planning-entry.py` recorded it RED, 14 checks. The
live component is the planning REWRITE, a different shape (16 manifest seats, not 9; entry seat
`plan-interviewer`, not `elicitator`), and the shipped values below were repointed at it. The pair shipped here
before was `master-request-launch-entry` / `request-schema-absence-remeasurer` — the run-3 wave that
BUILT this machinery, whose root seat is a build-time measurement seat — so a fresh goal would have
re-run the build wave. Confirming that pair is no longer an owner precondition; it is settled.

✅ **THAT PRECONDITION IS DISCHARGED** (task C5E, owner rulings `d-owner-planning-entry-0808` and
`d-owner-planning-entry-2-0808`). ⚠ **Its `workflows: planning:` half is DELETED by 7.778** — the
`start-workflow` row that entry served is no longer minted, so the entry has no producer and was
removed. The two values below are still ruled and still shipped on the `tools:` entry:

| Was unresolved | Ruled and built |
|---|---|
| how the PACKAGE is resolved | ⚠ 7.607 E2b: IT IS THE GOAL FOLDER (design-lock item 8). `scaffold-and-queue` calls `create()` — the ruled name `scaffold-seats` — which completes the goal folder's WORKING SURFACES. It appends NO register row: `runs.csv` is extinguished, liveness is the derived lease (item 1), and the deadlock that register caused (7.608) dies with it |

**The goal is therefore born with its working surfaces complete**, and — since 7.777 — with its
LANE declared. Nothing rides a queued row: there is no queued row.

⚠ **Four flags on the entry are what make that happen**, and the last two are not defaultable:
`--catalog-root`, `--bindings`, and `--claude-md`/`--budget-json`. `scaffold-seats`
refuses `create-inputs-missing` without the base texts, saying why — it "never invents run
conventions and never defaults a floor". They name the OWNER-AUTHORED, OWNER-APPROVED goal-generic
starter set at `team-kit/starter-set/` (`d-owner-starter-set-approved-0808`). F7 abolished
`conduct.md`; the four procedures live in `coord.py` `boot_prompt`.

⚠ **The per-row argv TEMPLATING mechanism is unchanged and still live** — `{{workflow}}` /
`{{entry-seat}}` / `{{goal}}` / `{{workdir}}` expand from a queue row's own args, so one generic
entry can serve every workflow. Contract, injection argument and value rules:
`server/heart/argv-template.js`. Suite: `server/ticker/probes/probe-argv-template.js`. ⚠ **This
capability is no longer one of its consumers** (7.778): it registers no `start-workflow` job, so
nothing here fills those tokens.

### The launcher this entry used to fire — DELETED (7.778)

`tool/workflow_launcher.py` opened a goal's own detached tmux room and handed the launch to
`coordinate` with an explicit `--tmux-target`, because `coordinate launch` cannot open a room and a
daemon-fired exec has none. It is **deleted with the door**, along with the `workflows: planning:`
entry that fired it, the `<goal>-workflow-start` row that triggered it, and the probes that pinned
it (`probe-planning-entry.py`, `probe-sensor-start.py`, `probe-launcher-attribution.py`).

**What opens the entry seat now: the LANE.** A created goal declares `<goal>/execution-lane` at
birth (task 7.777 — a REQUIRED request field), and the daemon's watch pass reads that marker every
cadence and seeds the goals assigned to `daemon`. A `console` goal opens when a human types
`rbtv run`. One readiness predicate recomputed from disk replaces a one-shot row planted at birth
that had to guess how long to wait — which is why `goal-launch-delay`, the capability that tuned
that guess, is deleted too.

⚠ The `start-workflow` **action type** survives: it is a generic dispatch category with live
consumers (`server/ticker/one-live-run.js`, `server/ticker/goal-channel-start.js`). Only this
capability's use of it is gone.

## The request schema it validates against — THE LIVE CLAUSE

Eight fields — five required, three optional — and the set is **closed**: a name outside it is a
refusal, never a passthrough.

⚠ **This section is the schema's LIVE text and it supersedes the frozen record** (task `7.631`,
2026-08-10). The artifact the code cites as its origin —
`.rbtv/goals/build-core-daemon-mvp/runs/run-3/planning/briefing-master-request-launch-entry/request-schema-goal-creation.md`,
§1 authored by `7.197` (`E2`) and §6 by `7.198` (`E3`) — sits inside a run compartment the owner
ruled **read-only archaeology, never migrate or edit it** (`.rbtv/goals/CLAUDE.md`). It is not
edited and it is not migrated: it stays the historical FIVE-field, THIRTEEN-member record, exactly
as those two rows landed it. The amendment lands HERE instead, in the capability that implements it,
and this file is what `REJECT_SET_SOURCE` now names. **Where the two differ, this clause is what the
tool implements and what a second implementer builds against.**

| Field | Required | Constraint | Member that negates it |
|---|---|---|---|
| `goal-name` | yes | lowercase kebab-case · free in the resolved goals root · not declared by another goal | `P1` · `V1` `V2` `V3` |
| `goal-type` | yes | `one-shot` \| `recurring` | `P2` · `V4` |
| `goal-contract` | yes | non-empty after whitespace strip | `P3` · `V5` |
| `goal-kind` | yes | `interactive` \| `non-interactive` | `P4` · `V6` |
| `due-date` | no | type UNRESOLVED in the schema — **no value of it is rejected** | none — §6.3's empty slice |
| `execution-mode` | no | `interactive` \| `autonomous` | **`V7`** — the fourteenth member, minted by §1.7 |
| `execution-lane` | **yes** | `daemon` \| `console` | **`P5`** · **`V8`** — the fifteenth and sixteenth, minted by §1.8 |
| `launch-profile` | no | a name in the shared config's `profiles:` — enforced at the creation verb, not here | none — §1.9's empty slice |

### §1.7 · `execution-mode` — optional, enum `interactive | autonomous`

The per-goal OWNER-CONTACT policy (registry concept `execution mode`; ABSENT reads `autonomous`).
Optional is the point: a requester who says nothing gets the WORKFLOW's default, resolved from the
workflow's own scaffolding, which is a better answer than any default this layer could invent.

**Resolution ladder, in this order:** (1) the request payload's own `execution-mode` → (2) a
`goal-kind` of `non-interactive` → `autonomous` → (3) the workflow's DECLARED
`default-execution-mode:` → (4) DERIVED from that workflow's manifest Modality column → (5) the
model's own `autonomous` where no workflow is named or none resolves. Each rung's reason, why the
declaration outranks the derivation, and why rung 2 reads the kind in ONE direction only, is
§ *Three properties* item 4 below — that item is the normative statement of the ladder; this line
is only its order.

**Where each half is enforced:**

| Half | Site |
|---|---|
| the NAME is in the closed field set | `validate` — `S2` computes its set difference against `ALL_FIELDS`, which is six |
| the VALUE is in the enum | `validate` — **`V7`**, class `V`, under the `S → P → V` class-stop |
| the RESOLVED value reaches the created goal | `resolve_execution_mode`, called by `scaffold_goal` BEFORE the exists-check and before any write; a payload value outside the enum raises a typed `Refusal` there too, so the act-performing path refuses even when its caller skipped `validate` |

### §1.8 · `execution-lane` — REQUIRED, enum `daemon | console`

Which lane runs the goal (registry concept `lane assignment`,
`system-definition/concepts/lane-assignment.md`). The marker is `<goal>/execution-lane`; `daemon`
means the daemon's watch pass seeds the goal unattended, `console` means nothing runs until a human
types `rbtv run`.

⚠ **REQUIRED, and there is NO resolution ladder** (owner ruling, 2026-08-12, task 7.777). Read
`execution-mode`'s five-rung ladder directly above and then do not generalise from it: every rung
there has a defensible answer, and this field has exactly one. The two lanes differ in WHO runs the
goal, which no layer below the requester knows, so a request that names no lane is REFUSED (`P5`)
and one naming something else is REFUSED (`V8`). Nothing defaults, nothing derives.

⚠ **THE DAEMON WRITES THE MARKER, AND THAT ROUTING IS THE FIX FOR A MEASURED DEFECT.** The channel
master cannot write `<goal>/execution-lane` itself: its `goals-write` cage grant is resolved as a
SPAWN-TIME SNAPSHOT of the goals it may write, so a goal created DURING a sitting can never be in
that snapshot and the write dies on `EROFS` — there is no ordering that works. Carrying the lane as
a request field means `scaffold_goal` forwards it as `goal_cli.py scaffold --lane`, in the very
process that writes `goal.md`, and the master needs no goal-folder access at all.

**Where each half is enforced** — the same two-site shape `execution-mode` has, for the same two
reasons: `P5`/`V8` in `validate` (the requester's pre-flight, which performs no act), and a typed
`Refusal` in `resolve_execution_lane`, called by `scaffold_goal` before the exists-check and before
any write (the acting path, whose callers may skip `validate`). Both read the one constant
`EXECUTION_LANES`.

### §1.9 · `launch-profile` — **DELETED** (`#d-abolish-profile-names`, 2026-08-12)

It named the FALLBACK launch profile for seats declaring no cast of their own. The fallback is
abolished, `rbtv-goal scaffold` has no `--profile` flag left to forward it to, and what a seat runs
is its CAST in the workflow's bindings sheet — not a goal-creation input. The field is REMOVED from
`OPTIONAL_FIELDS` rather than accepted-and-ignored: a value silently dropped would leave the
requester believing it had chosen something.

### The reject-set decision — `V7` is minted, and why

The closed set grew to **fourteen** (and to **sixteen** with §1.8's `P5`/`V8`). That is not an implementer's judgment call; it is what the
schema's own generation rule produces once this clause exists. §6.0 generates the set from §1 by
three finite passes — one member per structural precondition (3), one per REQUIRED field for its
absence (4), **one per constraint CLAUSE for that clause's negation (6)** — and states that *adding
a member requires adding a clause to §1 first*. §1.7 above IS that clause, and it states a closed
two-member enum, so its negation is generated exactly the way `V4` and `V6` are. Declining to mint
it would leave a set no reader can RE-DERIVE from the field table, which is the property §6.0 says
makes the set closed rather than merely enumerated.

**`due-date` is not the precedent it looks like.** It contributes zero value members because §3.1
records its TYPE as UNRESOLVED, and §6.3 rules that a reject named against an unresolved type is
the silent validation §3 exists to prevent. `execution-mode`'s type is resolved — two literals — so
that exemption does not reach it.

**The measurement that settled it, rather than the argument alone.** Before this clause,
enforcement lived only at `resolve_execution_mode`, and the two verbs therefore disagreed about the
same payload:

```
$ goal_creation_request.py validate <payload with execution-mode: "sometimes">
exit 0            # ACCEPTED — no member matched
$ goal_creation_request.py handle  <the same payload>
exit 1            # REFUSED at resolve_execution_mode
```

`validate` is the requester's pre-flight and *"performs no act"* — a pre-flight that clears a
payload the acting verb refuses is worse than no pre-flight, because a caged requester stages on
its verdict. `V7` closes that divergence at the one site that reports members.

**The `resolve_execution_mode` refusal STAYS.** It is not replaced by `V7`: `scaffold_goal` is
reachable as a function (the probes call it directly) and `handle`'s callers may skip `validate`
entirely, so the act-performing path keeps its own typed refusal — the same shape `--kind` has at
`goal_cli.py#cmd_scaffold`. Two enforcement sites for one enum is deliberate here because they
answer two different questions (*may I send this?* and *may I act on this?*), and both read the one
constant `EXECUTION_MODES`.

⚠ **`S2`'s member NAME still reads `field-name-not-in-the-five`** and is left byte-verbatim from the
frozen record. A member id-to-name mapping that two implementers must report identically is not
this clause's to reword; the set it checks is `ALL_FIELDS`, and the check message prints the live
set, so a reader is never told the wrong one.

## The refusal arm — what a refused request is told (task `7.206`, design id `E11`, arm **a**)

**The refusing site and the site that answers the requester are the same file**, so one observable
carries the whole criterion and no propagation question arises.

A refusal names the **member of the schema's closed reject set** that matched — one of sixteen,
`S1`–`S3` (shape), `P1`–`P5` (presence), `V1`–`V8` (value) — its member name, and what held instead.
Never a bare status. The text appears in `stated-refusal`, in `handle`'s requester-facing `outcome`,
and on **stderr** for a human reading a terminal.

**Class-stop is the schema's ruling, not this tool's preference.** The classes are evaluated
`S → P → V` and evaluation **stops at the first class in which any member matched**; within that
class every matching member is reported. The validator *returns* at that stage rather than
evaluating later classes and filtering — `V2`/`V3` reach the filesystem, and "evaluated then
suppressed" is not what §6.2 says. The schema's own worked example is the check: for
`{goal-name: "x", goal-contract: "  ", goal-kind: "interactive", priority: "high"}` the correct
report is **`{S2}` alone** — `P2` and `V5` are real of that request and are deliberately suppressed
until `S2` is fixed.

**The set is CLOSED and this tool mints nothing.** A condition with no member is a condition the
schema **admits**; growing the set requires adding a clause to the schema's §1 first — which is
exactly how the set reached fourteen: §1.7 above landed, and `V7` was generated from it by §6.0's
own rule, not minted at the code. Two readings
were needed to make the members decidable over a JSON payload, and both are stated in the source
rather than buried: `S3` is about **arity** (`null`, or a list/dict — no value, or more than one),
and a wrongly-**typed** scalar fails that field's own value member rather than minting a "wrong
type" member the schema does not carry.

## Three bounds this capability is built to, each with its reason

| Bound | Why |
|---|---|
| **The ruled name.** The create act invokes `scaffold-seats`, resolved on PATH — never the script path `materialize-seats.py` behind it, and never a hand-rolled spawn. | `d-materialize-term` and `p-the-scaffold-seats-fix-is-NOT-a-text-alignment`: invoke the ruled name, do not align text. |
| **Not hosted in `chat-bridge`.** | `chat-bridge.js:11-12` states its own bound: it holds NO spawn/queue capability BY DESIGN. Hosting the entry there changes another component's designed bound. |
| **The chain fails closed.** A failed act stops the chain; a later act never runs on an earlier one's failure, and the outcome never reads `ACCEPTED` when a step returned non-zero. | Measured, not anticipated — see below. |

(The former fourth bound, "one location computer" for the arming marker's path via
`edge-runner-job.arm_path()`, is gone: ARMING IS RETIRED, and both the marker and the edge-runner
are deleted — see below.)

## Three properties of the path, stated because they surprise every reader once

1. **There is no create-only mode.** `scaffold-seats` requires `--seat` or `--workflow` plus an
   explicit `--after|--root`, so the CREATE act **necessarily materializes at least one seat**.
   That is a property of the only creation path in the system, not a choice.
2. **`sessions.csv` is born at LAUNCH, not at create.** The creation path omits it deliberately;
   the file appears only when a seat actually boots. Its absence *before* the launch act is
   expected; its absence *after* one is a defect. (The ordering argument this line once carried
   named a third act, `arm`, which is retired.)
3. **`goal-kind` is validated AND persisted — the carrier is `goal.md` frontmatter.** The carrier
   this schema once declined to invent was owner-ruled on 2026-08-08 (`d-owner-batch1` (2)), so the
   creation verb carries `--kind` and the validated value is forwarded to it instead of being
   dropped. The result reports `kind-carrier: goal.md frontmatter`.
   ⚠ The ruling made the FRONTMATTER KEY optional (a goal scaffolded before the field existed
   stays valid and reads as `interactive`); it did **not** relax this REQUEST schema, where
   `goal-kind` is still one of the four required fields and `P4` still refuses an absent one.
   A requester must say which kind it wants; only stored descriptors may be silent.
4. **A created goal is never born without an `execution-mode` file** (owner ruling 2026-08-10).
   The per-goal owner-contact policy — registry concept `execution mode`, values
   `interactive | autonomous`, absent reading `autonomous` — used to be written by NO creation
   path at all, so every daemon-created goal was born mode-less and the ferry could only read the
   model's default back. The create act now always forwards a resolved word to
   `rbtv-goal scaffold --execution-mode`, and the `create-goal` step reports both
   `execution-mode` and `execution-mode-source`.

   **The resolution ladder, in this order:** the request payload's own `execution-mode` → a
   `goal-kind` of `non-interactive` → the target workflow's DECLARED `default-execution-mode:`
   (frontmatter of `<catalog-root>/<component>/workflows/<W>/workflow.md`) → DERIVED from that
   workflow's manifest (any row whose Modality reads `interactive` → `interactive`, none →
   `autonomous`) → the model's own `autonomous` where no workflow is named (a `--seat` creation)
   or the workflow resolves to no single manifest. Every rung names its source in the step
   record, so a fallback is never mistaken for a resolution.

   ⚠ **The goal-kind rung reads the kind in ONE direction** (owner ruling 2026-08-11, task
   `7.753`). `goal-kind: non-interactive` resolves `autonomous`, OVERRIDING the workflow default:
   a goal nobody will ever sit with was being born `interactive` whenever its workflow declared
   that default, so its seats waited on an owner who was never coming. `goal-kind: interactive`
   derives NOTHING and falls through to the workflow — a goal someone MAY sit with is not thereby
   a goal that must wait, and that call belongs to the manifest, which is what knows whether a
   seat is actually interactive. An explicit request `execution-mode` still outranks both.

   ⚠ **The declaration outranks the derivation on purpose.** Derivation cannot express the one
   case the owner named: a workflow WITH interactive seats that should still default autonomous.
   A malformed declared value is a **refusal**, never a fallback — falling back would create
   goals on a default the workflow's own scaffolding says is not its default.

   ⚠ **`goal-kind`'s `interactive` and this axis's `interactive` are DIFFERENT AXES sharing a
   word** (`concepts/execution-mode.md` § v1 mechanism, vocabulary guard; open issue `F-96`).
   `goal-kind` is `interactive | non-interactive`; execution mode is `interactive | autonomous`.
   Neither enum is ever written in terms of the other.

   ⚠ **The schema clause landed and the set is now FOURTEEN** (task `7.631`, 2026-08-10 — the
   live clause is § *The request schema it validates against* above, §1.7 and its reject-set
   decision). The field shipped on 2026-08-10 with NO member, because growing the closed set
   needs a schema clause FIRST and none had been written; that gap is closed, and `V7`
   (`execution-mode-not-in-enum`) is generated from §1.7 by §6.0's own rule. Its enum is now
   enforced at BOTH sites — `V7` in `validate`, and the typed `Refusal` in
   `resolve_execution_mode` raised **before** the scaffold act, the same shape `--kind` has at
   `goal_cli.py#cmd_scaffold` and, like it, leaving no goal directory behind. The probe drives
   both arms.

## ⚠ Arming does not generalise from this capability — AND ARMING IS RETIRED

This handler was the first production writer of an arming marker for the path it built and for
nothing else (`decisions.md#p-E16-carries-the-durable-arming-writer-itself-and-that-does-NOT-
generalise-arming`). Both the marker and the engine that read it are GONE
(`build/one-readiness-predicate.md`, owner-ruled 2026-08-11): readiness is recomputed from disk
every cadence. What decides whether a goal advances is its LANE (§1.8), which this handler now
writes at birth.

## The probes

**Three**, and they guard different things.

- `probes/probe-goal-creation-request.py` — the entry's own shape and refusal arm (below).
- `probes/probe-goal-type-carrier.py` (task 7.533) — the goal-type carrier's end-to-end witness: a
  request carrying `--type recurring` produces a recurring goal, checked against the created goal's
  own descriptor on disk rather than against the request that asked for it.
- `probes/probe-execution-mode-birth.py` — the execution-mode lifecycle, rung by rung.

⚠ **Three probes were DELETED with the door in 7.778**, named here so a reader looking for them
stops looking: `probe-planning-entry.py` (the `workflows: planning:` argv composition),
`probe-sensor-start.py` (the census sensor starting with the room's first seat) and
`probe-launcher-attribution.py` (the launcher grading a fire by its own reported pane). All three
asserted `workflow_launcher.py`, which no longer exists. The lane-at-birth behaviour that replaced
the door is guarded at the creation verb — `capabilities/goals-tree/probes/probe-lane-at-birth.py`
and `probe-goal-scaffold-standard-files.py`, which asserts `execution-lane` in the ruled file set.

## The other probe, and why it carries mutants

`probes/probe-goal-creation-request.py` runs **nine** checks — six authored by `7.211` (the entry)
and three by `7.206` (the refusal arm: the member is named, the class-stop holds, the refusal is
stated) — and runs each one **twice**: once
against the real file (must be GREEN) and once against a mutated copy carrying the very defect the
check exists to catch (must be RED). A check whose mutant stays green exits **2 (INOPERATIVE)**,
never 0: a control arm that cannot fire is indistinguishable from one that fired and found nothing.
Check 3 additionally carries a positive control reported **per arm**, because a blind arm hides
behind a healthy arm's total.

**Three of the checks exist because the defect was real, found while exercising this capability:**

- a **dry run that wrote** — the contract file's `mkdir(parents=True)` ran before `dry_run` was
  tested, so the inspection command created the goal it was asked only to describe;
- a **chain that did not fail closed** — `scaffold-seats` refused the bindings and returned rc=1,
  and the handler armed the package anyway and reported `ACCEPTED`, leaving an armed package with
  a `coordination/` directory and no run folder;
- a **checker that fired on its own prose** — check 3's first draft matched the docstring sentence
  documenting that the handler never invokes `materialize-seats.py`. It now matches constructs as
  code, never nouns as prose (`code_only`).

**Two more the refusal arm hit, recorded for the same reason:**

- a **mutation that matched nothing** — check 1's substitution text was written against the verdict
  dict `7.206` then moved into `_verdict()`, so the mutant was never applied and the probe reported
  **INOPERATIVE** rather than a pass. That branch existing is the only reason the drift was seen;
  the mutation was repaired, not the report.
- a **mutant that CRASHED instead of going red** — check 7's first mutation removed the `member`
  key where refusals are built, which `_stated()` also reads, so the mutant raised `KeyError` and
  the check never rendered a verdict. A red produced by a traceback is the traceback's, not the
  condition's. The mutation now strips the key at the reported output instead.
