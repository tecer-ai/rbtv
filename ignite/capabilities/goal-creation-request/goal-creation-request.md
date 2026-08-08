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

### Arming it is three gated acts, in this order

The catalogue entry `tools: goal-creation-request` in `config/spawn-profiles.yaml` is landed **dark**.
Landing it does not arm it:

1. create the inbox directory the entry names (`.rbtv/goals/_channel-master/requests`);
2. restart the daemon — `spawn-profiles.yaml` is boot-read;
3. `ignite register-job goal-creation-request --action-type fire-tool …` then `ignite add-job`.

Out of order, step 2 logs one `catalogue-paths` error per boot for an `--inbox` that does not exist
yet (that check logs; it never refuses the boot).

⚠ **`--workflow` / `--entry-seat` are the one pair an owner must confirm before arming.** They name
what EVERY master-created goal starts with. A second precondition sits behind them: `enqueue-job`
refuses a `start-workflow` row whose workflow is absent from `config.workflows`, and
`spawn-profiles.yaml` **has no `workflows:` section at all**. The launcher argv for
`master-request-launch-entry` is a deployment/design value, so the C2 proof stubs it in a throwaway
config and names the substitution rather than inventing one into the shipped file.

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

## The probe, and why it carries mutants

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
