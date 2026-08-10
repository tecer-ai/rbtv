# bindings — the casting sheet a workflow is run through

**The knob:** which harness, which model, which effort each seat of a workflow runs on. Owner-ruled
2026-08-10.

A **workflow** is the program — an ordered set of **seats** in
`<component>/workflows/<w>/<w>.csv`. A **taskforce** is its running instance. The **bindings** file
is what casts one into the other, and it is read by exactly one consumer:
`ignite/team-kit/materialize-seats.py --bindings`, once, when a goal's seats are materialized.

```
workflow (the program)  +  bindings (the casting)  ──materialize-seats──▶  taskforce (the run)
```

## Where the file lives, and why not in the mirror

```
.rbtv/config/bindings/{module}/{component}/{code}.json
.rbtv/config/bindings/meta/planning/plan.json          ← the planning workflow's sheet
```

The mirror (`.rbtv/mirror/<module>/<component>/`) carries what a component **is**. A casting sheet
is what **this deployment decided to spend** on running it — a different kind of fact with a
different lifetime — so it lives under `.rbtv/config/` beside the other deployment knobs.

`{code}` is the **workflow's code**: the seat-id prefix every manifest row already carries
(`plan-interviewer`, `plan-splitter`, … → `plan`). It is DERIVED from the manifest and never typed —
the code is the filename, so a typed one would file the sheet under a name the manifest does not
agree with and nothing would notice. A manifest whose rows share no single prefix is REFUSED rather
than guessed at.

⚠ **A workflow code is EXACTLY FOUR ASCII LETTERS** (owner ruling 2026-08-10) — the shape being
minted registry-side as `workflow code`. `workflow_code()` is the one place the code is ever
computed, so it refuses anything else by name and tells the author to fix the manifest's
`Seat/workflow` column: a five-letter prefix that slipped through would name a bindings file, a
seat-id family and a registry record that disagree with the ruling for as long as they exist.

**ONE file per workflow**, created on first use and reused by every later goal until someone edits
it. No per-goal copies and no templates lying around: `check_bindings_cover` demands the sheet's
`seats` key set EQUAL the manifest's, so a stale copy is a refusal at the next materialize, and the
only way to keep N copies honest is to not have them.

## Not a two-part capability — and that is the measured difference

`goal-launch-delay` and `master-profile` each split into a seat-side `request` and a daemon-side
`apply`, because the value they change lives in a file the requesting seat's cage binds read-only
and a service boot-reads. **Neither is true here.** The bindings tree is in the channel master's
`rw-paths`, and nothing boot-reads it — materialization opens the file at goal-creation time and
closes it. So every verb is a plain direct file write, there is no staged inbox, no `enqueue-job`
trigger, and no restart. A seat runs this tool itself.

## The verbs

| Verb | Does |
|---|---|
| `catalog` | Every harness+model this workspace can spawn, each with its effort levels NUMBERED (`claude`: 1=low … 5=max). A model with no effort dial says so. |
| `inspect <workflow.csv>` | Every manifest seat: id, the seat-definition file it resolves to, its staffing hints (advisory), and its current casting — plus which seats remain uncast. |
| `scaffold <workflow.csv>` | Creates the sheet at the canonical path with every manifest seat present and casting values null; lane constants prefilled. **Create-only** — it refuses over an existing sheet rather than silently re-casting a taskforce that may already have run. |
| `set <workflow.csv> <seat> <harness> <model> <effort-number>` | Casts one seat. |

## `catalog` is the validator, not just a display

`catalog` is BOTH the standalone "what can I cast?" surface and the ONE list `set` validates
against — one derivation, two consumers, so the answer an agent reads and the answer that refuses it
can never disagree. It is composed from exactly two measured sources:

1. **Which harness+model pairs exist** — `profiles:` in `ignite/config/spawn-profiles.yaml`, which
   `r-seats-only-architecture` makes *"ONE PROFILE PER HARNESS+MODEL … nothing else is identity"*.
   That IS the workspace's spawnable set. The harness is the profile's `argv[0]`; the model is the
   literal its `exec` argv PINS.
2. **Whether a pair has an effort dial** — the profile's own `effort:` block. `effort: { inert: true }`
   is a MEASUREMENT under G-270 (*"a harness whose dial does not exist says so"*), so an inert
   profile has no dial and refuses any effort number.

…and the **levels** of a dial that exists are the harness's NATIVE ladder, not the profile's
`effort.values` table. Those are different objects: the table maps the daemon lane's four ABSTRACT
levels onto harness strings, while a bindings value is passed to the harness LITERALLY
(`coord.py#harness_command`: `claude --model {model} --effort {effort}`). claude's literal ladder is
five rungs (`claude --help`: *"low, medium, high, xhigh, max"*; same five in
`orchestration/models/claude-code-cli/manifest.yaml`), and binding through the four-rung translation
table would make `xhigh` unspellable on a dial that has it.

Every row is finally passed through **`coord.py#validate_seat`** — the same predicate
`materialize-seats.py`'s F6 gate imports for the whole batch before any write. A profile that
predicate rejects is listed NOT CASTABLE with its reason rather than dropped: today `kimi` (not in
`HARNESSES`) and `test-sleep` (no harness at all).

⚠ **The model vocabulary is the profile's pin, verbatim** — `claude-fable-5` for `claude-fable`,
`claude-opus-5` for `claude-opus`, and so on: every profile now pins a FULL model id (owner ruling
2026-08-10 — the alias/full-id asymmetry the earlier config carried was eliminated at the source,
not papered over here). The claude binary honours both an alias and a full model id, so both
spellings would *run*; but only the pinned literal joins a bindings row back to a profile row, and
minting the other form here would be a second mapping of the same fact — the drift
`DEC-1 § Shared profile source` forbids. A caller passing an alias is REFUSED with the catalog's
models printed, never silently rewritten.

## The effort NUMBER

`set … 4` on a claude pair stores `"effort": "xhigh"`. The number is an input abstraction — a
1-based index into that harness's native ladder — and the FILE stores the harness's own string,
because that string is what reaches the binary. Out of range refuses with the ladder printed; a
number against a dial-less pair refuses rather than storing a knob that turns nothing.

## What the file carries

```json
{ "defaults": { "cwd-mode": "seat-folder" },
  "seats": { "plan-binder": { "agent_type": "staff", "mode": "interactive", "ctx-refresh": 35,
                              "harness": "claude", "model": "claude-opus-5", "effort": "xhigh",
                              "component": "<abs path to the component>/" } } }
```

`mode` is the DESCRIPTOR mode (materialize admits only `one-shot|interactive`) — **not** the
manifest's `Modality` column, which a seat carries through its own `human-interactive:` frontmatter.
`pass-folder` and `window` are deliberately absent: a component whose unit bodies render no pass
placeholder must not declare a folder, and a shared window disables in-place renew (G-154).

A full `json.load`/`json.dump` round trip is correct here and is deliberately unlike this
capability's siblings, which line-edit: those edit hand-authored documents whose comments are their
documentation, while this file is machine-owned end to end.

## Probe

`probes/probe-bindings.py` — hermetic (tempfile copies only; the live bindings tree is never
touched). Seven checks: the catalog moves when the profiles copy is re-pinned; every offered pair
survives `validate_seat`; the effort number indexes the native ladder while the file stores the
string; six refusal shapes each leave the sheet byte-identical; the code derivation refuses a mixed
manifest and any code that is not exactly four ASCII letters; **four mutants** (each WIDENING one guard — a deletion crashes, and a crash reads like a
refusal) prove those arms discriminate; and `materialize-seats.py --dry-run` plans clean over the
artifact this tool writes, with the one-seat-uncast twin refusing.

Run it through the enumerator: `node deploy/probe-suite.js --only probe-bindings`.
