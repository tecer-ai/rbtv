# goal-creation-request — the entry a goal-creation request arrives at

Core-build task **7.211** (design id `E16`) of run-3's `no-row-builds-the-entry` pass.

The tool is `tool/rbtv-goal-request`. It takes a goal-creation request, validates it against the
landed request schema, and discharges it as **three ordered acts — create → arm → launch**.

**Why this capability exists.** The wave that consumes this entry was designed on the premise that
the entry already existed. The disk refuted it: every consuming row reached for a thing no row
built, and nothing errored — the rows would simply have waited. This capability is the row that
builds it.

## The three verbs

| Verb | What it does |
|---|---|
| `validate <request.json> [--goals-root R]` | Validates field by field and **names every field it checked**. Performs no act. Exit 0 accepted, 1 refused. |
| `handle <request.json> …` | Validates, then create → arm → launch. A refused request performs **no** act. `--no-launch` withholds the launch act; `--dry-run` writes nothing. |
| `scaffold-and-queue --inbox D --goals-root R --workflow W --entry-seat S [--delay-seconds 600] [--ignite-bin B]` | **The daemon-executed verb** (task C2). Drains a staged inbox: per request, validate → scaffold the goal → register the goal's first workflow job homed at it → queue that job `--delay-seconds` out. **Arms nothing, launches nothing.** Exit 0 when every drained request was accepted (or the inbox was empty), 1 otherwise. |

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

**One partial state is real and is not hidden.** The scaffold runs before `register-job`, so a fire
whose credential cannot register leaves a scaffolded goal with no queued job. The result records it
truthfully (`scaffolded: true`, `outcome: REFUSED`, the stated refusal naming `register-workflow-job`)
rather than rolling the goal back — an unwind here would delete a directory the daemon cannot prove
it alone created.

**`register-job` failure is a refusal of that request, never something to retry around.** The verb
is create-only with no update surface, so re-driving a half-registered id needs a human; sniffing
the failure text for "already exists" would be reading a message as if it were a policy
(project ledger `S-3`).

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

1. **Complete it** — the goal is wanted; only its job is missing. Re-issue exactly what the verb
   would have, with an owner or enrolled-**agent** token (`register-job` refuses a bridge one):

   ```
   ignite register-job <goal>-workflow-start --action-type start-workflow \
     --goal <goal> --seat <entry-seat> \
     --args-schema '{"required": {"workflow": "string", "entry-seat": "string", "goal": "string", "workdir": "string"}}'
   ignite add-job --fn <goal>-workflow-start \
     --args-json '{"workflow": "<workflow>", "entry-seat": "<entry-seat>", "goal": "<goal>", "workdir": "<goal-dir>/runs/run-1"}' \
     --trigger scheduled --at <ISO-8601 Z>
   ```

   `<entry-seat>` and `<workflow>` are the catalogue entry's own `--entry-seat` / `--workflow`
   values; `<goal-dir>` is the refusal record's. If `register-job` reports the id already exists,
   the row was minted before the failure — skip to `add-job`.

   ⚠⚠ **All four schema keys are `required`, exactly as the tool itself registers them**
   (`tool/goal_creation_request.py` `register-workflow-job`) — the launcher's argv templates
   `{{entry-seat}}` / `{{goal}}` / `{{workdir}}` (a row missing one REFUSES AT EVERY FIRE:
   `placeholder {{...}} has no value in the row args`, recorded `failed`), and `workflow` is what
   `launchStartWorkflow` selects the catalogue entry by (a row naming a workflow the boot-read
   config does not carry DEFERS every tick, forever; a row carrying no `workflow` at all cannot
   exist — `add-job` refuses it).
   `register-job` is create-only (`E_JOB_EXISTS`, no update surface), so a schema registered
   without `goal`, `entry-seat`, or `workdir` cannot be repaired in-band — the id is burnt.
   `workflow` is the ONE of the four that CANNOT burn an id: `register-job` refuses a
   `start-workflow` schema that omits it (`args_schema.required declares no "workflow"`), so that
   mistake is a refusal rather than a burn — which is precisely why the other three need this
   warning. `workdir` is the RUN
   PACKAGE (`<goal-dir>/runs/run-1` — the scaffold's `FRESH_RUN_ID`), NOT the bare goal dir
   (task C5E: the package expands `{{workdir}}` in the launcher argv AND becomes the fired
   process's CWD).

   ⚠ **`entry-seat` appears TWICE and both are required** (task C5). `--seat` HOMES the job — the
   ticker resolves the seat FOLDER from it at fire — while the `entry-seat` ARG is what the
   launcher's argv template expands `{{entry-seat}}` from. Omitting the arg is refused at
   `add-job` (the schema declares it required); omitting `--seat` leaves the job unhomed.
   `add-job` also refuses a `workflow`/`entry-seat` that is not lowercase kebab-case, and a
   `workdir` that does not resolve inside `.rbtv/goals/` — those values reach an exec'd command
   line, so they are bounded at the door (`server/heart/argv-template.js`).

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

### Arming it is three gated acts, in this order

The catalogue entry `tools: goal-creation-request` in `config/spawn-profiles.yaml` is landed **dark**.
Landing it does not arm it:

1. create the inbox directory the entry names (`.rbtv/goals/_channel-master/requests`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read;
3. `ignite register-job goal-creation-request --action-type fire-tool …` then `ignite add-job`.

Out of order, step 2 logs one `catalogue-paths` error per boot for an `--inbox` that does not exist
yet (that check logs; it never refuses the boot).

⚠ **`--workflow` / `--entry-seat` are RULED — `planning` / `elicitator`** (owner ruling
`d-owner-q10-launcher-0808` (1), 2026-08-08; task C5). They name what EVERY master-created goal that
does not route to a pre-existing workflow starts with: the existing meta component
`.rbtv/mirror/meta/planner-workflow/`, whose chain root is `elicitator`. The pair shipped here
before was `master-request-launch-entry` / `request-schema-absence-remeasurer` — the run-3 wave that
BUILT this machinery, whose root seat is a build-time measurement seat — so a fresh goal would have
re-run the build wave. Confirming that pair is no longer an owner precondition; it is settled.

✅ **THAT PRECONDITION IS DISCHARGED** (task C5E, owner rulings `d-owner-planning-entry-0808` and
`d-owner-planning-entry-2-0808`). `enqueue-job` refuses a `start-workflow` row whose workflow is
absent from `config.workflows`; `spawn-profiles.yaml` now carries a `workflows:` section whose
`planning` entry is that launcher. The three values named here as unresolved were ruled and landed:

| Was unresolved | Ruled and built |
|---|---|
| which `scaffold-seats` call shape | The WHOLE planning DAG — `--workflow planning --root --run-type fresh`, **9** manifest seats (`workflows/planning/planning.csv`; `seats.csv`'s 10 is a different set), `--catalog-root` the SHARED PARENT `.rbtv/mirror/meta/` because `ledger-groomer` resolves from a sibling component |
| which bindings file | A goal-generic one authored for this path: `.rbtv/mirror/meta/planner-workflow/bindings-fresh-goal-planning.json`. It is STATIC, not a filled template — probing found no per-goal value to fill; `pass-folder` is the documented greenfield CONSTANT `planning/m0-bootstrapping/`, which is why the per-PASS hold that blocked run-3's file does not apply to a fresh goal |
| how the run PACKAGE is resolved | `runs/run-1`, created in this same act. `scaffold-and-queue` now calls `create()` — i.e. the ruled name `scaffold-seats` — which ALSO appends the run's `state=open` row to the goal's `runs.csv`. There is no second writer of that register, and none may be added |

**The goal is therefore born WITH a run**, and the full package path rides the queued row's args as
a whole token — whole-token templating deliberately cannot compose `runs/run-N`, so a row queued at
birth must carry a path that already exists.

⚠ **Five flags on the entry are what make that happen**, and the last three are not defaultable:
`--catalog-root`, `--bindings`, and `--conduct`/`--claude-md`/`--budget-json`. `scaffold-seats`
refuses `create-inputs-missing` without the base texts, saying why — it "never invents run
conventions and never defaults a floor". They name the OWNER-AUTHORED, OWNER-APPROVED goal-generic
starter set at `team-kit/starter-set/` (`d-owner-starter-set-approved-0808`). ⚠ **NOT
`team-kit/conduct-template.md`** — that is an UNFILLED FORM whose own opening lines say a run's
conduct-author instantiates it "filling every `{{slot}}`", while `--conduct` BYTE-COPIES. Pointing
at it would give every auto-created run a rulebook whose law reads `{{INSTANTIATE}}`; that option
was put to the owner and rejected on exactly that ground.

⚠ **The MECHANISM the entry uses is built and proven** (task C5): a registered workflow's argv is
a TEMPLATE whose `{{workflow}}` / `{{entry-seat}}` / `{{goal}}` / `{{workdir}}` tokens expand from
the queue row's own args, so one generic entry serves every workflow. Contract, injection argument
and value rules: `server/heart/argv-template.js`. Suite: `server/ticker/probes/probe-argv-template.js`.

⚠ **`goal` and `workdir` are now REQUIRED args on the registered job**, joining `workflow` and
`entry-seat`. `workdir` moved out of `optional` deliberately: the ticker falls back to the carrier's
DEFAULT workdir when a row carries none, so an absent value does not fail — it composes a command
line pointed somewhere else. `required` turns that into a refusal at the enqueue door.

### The launcher the `workflows: planning:` entry fires

`tool/workflow_launcher.py`. It exists because **`coordinate launch` cannot open a room and a
daemon-fired exec has none**: `launch` contains zero `new-session` calls (it opens a WINDOW in an
EXISTING session) and resolves its target from `COORD_LAUNCH_TARGET or TMUX_PANE`, neither of which
the daemon exports — and with both unset tmux resolves an empty target to the MOST RECENT session,
which is how a stray launch reaches a live room.

So it creates a **per-run DETACHED session named `<goal>-<run-id>`** (owner ruling
`d-owner-planning-entry-2-0808` Q2), proves the resolved pane really belongs to that session, and
hands the launch to `coordinate` with an explicit `--tmux-target`. Properties worth knowing:

- **Nothing short-lived is baked into boot config** — the config carries only placeholders and repo
  paths; the session name is composed at fire time from the goal.
- **Idempotent** — a re-fire joins the room it already opened (`has-session -t =NAME`, EXACT match:
  prefix matching would let goal `foo` resolve goal `foo-bar`'s room). It never kills a session, so
  the room outlives the launch, which is the point — humans attach over SSH.
- **`--force` yes, `--force-memory` no.** `--force` carries the ROLE gate, which a daemon-fired exec
  can never pass any other way (no pane ⇒ no seat identity). The MEMORY gate is left binding: this
  is a NEW launch, exactly what that floor is sized for. `jobs/recover-room.py` does override it,
  correctly, on a premise that is false here — a recovery replaces a seat that already died and is
  load-neutral. Reusing that program as this launcher was considered and REJECTED for that reason.
- ✅ **First fire on a brand-new package OPENS THE ENTRY SEAT — the CAPACITY gate is what
  cold-start clears, and the RAM floor above is still binding.** `coordinate launch` carries a
  COLD-START admission (team-kit task 7.406): a package no sensor has ever run against and no seat
  has ever launched into is recognised on its own markers and admitted on the EMPTY-ROOM BOUND
  (`in_use` 0). ⚠ That is an admission, not a guarantee: the MEMORY gate is left binding on purpose
  (the bullet above — `--force` yes, `--force-memory` no), and every launch prints the floor it is
  measured against (`floors.launch_refuse_mb` vs the per-seat spike). Under memory pressure the
  first fire on a brand-new package opens NOTHING and exits non-zero. Proven end to end against a
  fixture built by the shipped create path —
  `probes/probe-planning-entry.py` **P5**, which fires the real launcher with no `--dry-run` and
  asserts the seat's pane. This **corrects** the earlier claim (carried here, in the launcher and in
  `spawn-profiles.yaml` until task 7.548) that the first fire opens nothing and that whoever arms
  goal-creation must add the team-monitor census sensor to the arming sequence. That claim was read
  off `coordinate launch`'s census-FAILURE branch rather than measured, and the remedy it named is
  impossible anyway: `team_monitor.py` resolves the room's session FROM THE ROSTER and refuses while
  no seat has checked in (exit 4), so it cannot run before the first launch. **Nothing about the
  census belongs in the arming sequence.**
- ✅ **The census sensor starts WITH the room's first seat** (task **7.552**). What no arming
  sequence could carry, the LAUNCH does: `coordinate launch` hands `team_monitor.py ensure` the
  session it just launched into (`--session`, read off the pane it used — asked of the room, never
  derived from a path, `G-296`), so the sensor no longer refuses on an empty roster. This is what
  makes the SECOND fire possible: the cold-start bound above is spent ONCE — it fires only while the
  package is virgin — so before 7.552 every subsequent fire read `CAP UNENFORCEABLE` and deferred
  every counted candidate, and Wave D's advancement launch IS that second fire. Proven end to end by
  `probes/probe-sensor-start.py`: virgin package → first fire opens the entry seat → the sensor is
  RUNNING (live lock holder + a `state.json` naming the room) → the second fire ADMITS and opens
  another seat pane.
- ⚠ **Exit codes: `0` means A SEAT OPENED, and nothing else.** `recordToolCompletion` maps a fired
  tool's `0` to completion `done` and every non-zero to `failed`, so this program's exit code *is*
  the store record. It proves the claim from the pane set THIS fire added (never an absolute count,
  which cannot tell a fresh launch from a re-fire joining a room it already populated):

  | Exit | Means | Store records |
  |---|---|---|
  | `0` | this fire opened ≥ 1 seat pane | `done` |
  | `3` | the delegated launch exited 0 and opened NO seat pane — or the room could not be read, so nothing proves one opened | `failed` |
  | `1` / `2` | refusal — unresolvable target, absent package, bad name, delegated launch failed | `failed` |

  A `3` is a package that is **no longer virgin and has no census**, which is the state
  `coordinate launch` defers on. Since 7.552 that means a sensor that **STOPPED** — the first launch
  starts one, so it is no longer the fresh-package default it was when this table was written (the
  sensor then never lived at all, and every fire ended with `WARNING team-monitor start FAILED …
  the room runs UNOBSERVED`). It is loud and typed, never a silent success. It does **not**
  mint the failure-per-cadence pattern: the row this program runs under is **one-shot** (enqueued
  `--trigger scheduled --at <t>` with no repeat rule; `fireQueueRow` deletes it at fire), so there is
  no cadence for a failure to recur on — one fire, one honest record. Probe **P7** pins that, because
  the day the row becomes periodic this exit code starts writing a `failed` every pass.

## The request schema it validates against

Five fields — four required, one optional — and the set is **closed**: a name outside it is a
refusal, never a passthrough.

| Field | Required | Constraint |
|---|---|---|
| `goal-name` | yes | lowercase kebab-case · free in the resolved goals root · not declared by another goal |
| `goal-type` | yes | `one-shot` \| `recurring` |
| `goal-contract` | yes | non-empty after whitespace strip |
| `goal-kind` | yes | `interactive` \| `non-interactive` |
| `due-date` | no | type UNRESOLVED in the schema — **no value of it is rejected** |

## The refusal arm — what a refused request is told (task `7.206`, design id `E11`, arm **a**)

**The refusing site and the site that answers the requester are the same file**, so one observable
carries the whole criterion and no propagation question arises.

A refusal names the **member of the schema's closed reject set** that matched — one of thirteen,
`S1`–`S3` (shape), `P1`–`P4` (presence), `V1`–`V6` (value) — its member name, and what held instead.
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
schema **admits**; growing the set requires adding a clause to the schema's §1 first. Two readings
were needed to make the members decidable over a JSON payload, and both are stated in the source
rather than buried: `S3` is about **arity** (`null`, or a list/dict — no value, or more than one),
and a wrongly-**typed** scalar fails that field's own value member rather than minting a "wrong
type" member the schema does not carry.

## Four bounds this capability is built to, each with its reason

| Bound | Why |
|---|---|
| **The ruled name.** The create act invokes `scaffold-seats`, resolved on PATH — never the script path `materialize-seats.py` behind it, and never a hand-rolled spawn. | `d-materialize-term` and `p-the-scaffold-seats-fix-is-NOT-a-text-alignment`: invoke the ruled name, do not align text. |
| **One location computer.** The arming marker's location comes from `edge-runner-job.arm_path()`, imported. Computed nowhere else here. | Two computers are two readers free to disagree about which packages are armed — the C4 failure itself. |
| **Not hosted in `chat-bridge`.** | `chat-bridge.js:11-12` states its own bound: it holds NO spawn/queue capability BY DESIGN. Hosting the entry there changes another component's designed bound. |
| **The chain fails closed.** A failed act stops the chain; a later act never runs on an earlier one's failure, and the outcome never reads `ACCEPTED` when a step returned non-zero. | Measured, not anticipated — see below. |

## Three properties of the path, stated because they surprise every reader once

1. **There is no create-only mode.** `scaffold-seats` requires `--seat` or `--workflow` plus an
   explicit `--after|--root`, so the CREATE act **necessarily materializes at least one seat**.
   That is a property of the only creation path in the system, not a choice.
2. **`sessions.csv` is born at LAUNCH, not at create.** The creation path omits it deliberately;
   the file appears only when a seat actually boots. Its absence *before* the launch act is
   expected; its absence *after* one is a defect. This is why the acts are ordered create → arm →
   launch rather than create → launch → arm.
3. **`goal-kind` is validated AND persisted — the carrier is `goal.md` frontmatter.** The carrier
   this schema once declined to invent was owner-ruled on 2026-08-08 (`d-owner-batch1` (2)), so the
   creation verb carries `--kind` and the validated value is forwarded to it instead of being
   dropped. The result reports `kind-carrier: goal.md frontmatter`.
   ⚠ The ruling made the FRONTMATTER KEY optional (a goal scaffolded before the field existed
   stays valid and reads as `interactive`); it did **not** relax this REQUEST schema, where
   `goal-kind` is still one of the four required fields and `P4` still refuses an absent one.
   A requester must say which kind it wants; only stored descriptors may be silent.

## ⚠ Arming does not generalise from this capability

This handler is the first production writer of an arming marker **for the path it builds and for
nothing else** (`decisions.md#p-E16-carries-the-durable-arming-writer-itself-and-that-does-NOT-
generalise-arming`). A goal created by any other path stays BORN INERT. This file's existence
closes no general arming issue.

## The probes

Five, and they guard different things. Three arrived after this section was first written and are
named here so the count stays true: `probes/probe-sensor-start.py` (task 7.552),
`probes/probe-launcher-attribution.py` (task 7.588 — the launcher grades a fire by the pane its
own delegated launch reported, never by a room-wide before/after delta, so two fires racing into
one room cross-attribute neither the exit code nor the pane ids) and
`probes/probe-goal-type-carrier.py` (task 7.533) — the last is the goal-type carrier's
end-to-end witness, standing guard over the fact that a request carrying `--type recurring`
produces a recurring goal, checked against the created goal's own descriptor on disk rather than
against the request that asked for it. `probes/probe-planning-entry.py` (task C5E) is the
**composition** probe: it drains a real request through a fixture goals root with a STUB
`--ignite-bin`, then takes the SHIPPED `workflows: planning:` argv out of `spawn-profiles.yaml`,
expands it with the REAL `argv-template.js` against the args that drain actually produced, and
EXECUTES the composed command line against the real launcher (with `--dry-run` appended and a
private tmux socket). 26 checks, 8 of them red arms.

It exists because that composition was guarded by NOTHING: `probe-argv-template.js` certifies the
mechanism and `probe-goal-creation-request.py` certifies the create act's shape, and **neither reads
`config/spawn-profiles.yaml`** — so the config could drift to a different bindings file or catalog
root and every probe would stay green. For the same reason it TYPES no flag value: every one is
parsed out of the shipped config, and the queue-row args are captured from the drain rather than
composed by hand. Its boundary is stated in its own header: it does not fire the row through a live
ticker (that is `probe-argv-template.js`'s real-fire path); what it proves is that the composed argv
is accepted by the real program.

Nothing in it touches the live daemon, the live store, or a live room — tempdir goals root, stub
`ignite` binary, private `-L` tmux socket.

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
