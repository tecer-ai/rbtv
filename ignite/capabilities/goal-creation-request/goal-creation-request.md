# goal-creation-request — the entry a goal-creation request arrives at

Core-build task **7.211** (design id `E16`) of run-3's `no-row-builds-the-entry` pass.

The tool is `tool/rbtv-goal-request`. It takes a goal-creation request, validates it against the
landed request schema, and discharges it as **three ordered acts — create → arm → launch**.

**Why this capability exists.** The wave that consumes this entry was designed on the premise that
the entry already existed. The disk refuted it: every consuming row reached for a thing no row
built, and nothing errored — the rows would simply have waited. This capability is the row that
builds it.

## The two verbs

| Verb | What it does |
|---|---|
| `validate <request.json> [--goals-root R]` | Validates field by field and **names every field it checked**. Performs no act. Exit 0 accepted, 1 refused. |
| `handle <request.json> …` | Validates, then create → arm → launch. A refused request performs **no** act. `--no-launch` withholds the launch act; `--dry-run` writes nothing. |

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
3. **`goal-kind` is validated and deliberately NOT persisted.** The schema declares the field and
   states explicitly that it does not say where the kind is stored, because choosing a carrier is a
   structural convention and owner-gated. `goal.md` frontmatter carries no such field. The result
   reports `kind-carrier: NONE` rather than inventing one.

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
