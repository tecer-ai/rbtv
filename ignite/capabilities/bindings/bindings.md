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
.rbtv/config/modules/{module}/{component}/bindings/{code}.json
.rbtv/config/modules/meta/planning/bindings/plan.json   ← the planning workflow's sheet
```

The mirror (`.rbtv/mirror/<module>/<component>/`) carries what a component **is**. A casting sheet
is what **this deployment decided to spend** on running it — a different kind of fact with a
different lifetime — so it lives under `.rbtv/config/` beside the other deployment knobs.

This path is ONE INSTANCE of the general configuration convention — owner-specific values live at
`.rbtv/config/modules/<module>/<component>/…`, stated once in
`ignite/team-kit/starter-set/conduct.md` § 11.

⚠ **The pre-D15 spelling `.rbtv/config/bindings/{module}/{component}/{code}.json` still READS.** A
deployment that has not moved its files keeps working: every verb falls back to the old path and
WARNS, naming the new one. The fallback is compatibility, not a second canonical path — move the
files and the warning stops.

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
`apply`. ⚠ **Their reasons are no longer the same, and `master-profile`'s is now the interesting
one:** since its 2026-08-12 retarget it writes a file in THIS tree — which the master's cage grants
it — and it stays split ONLY because the `--repass` that makes the write take effect writes
`<goal>/seat.md`, and a seat cage refuses every grant overlapping `.rbtv/goals/`. So the sheet-write
half of that capability is as unsplit as this one; the re-render is what needs the daemon.

For this capability neither the read-only cage nor a boot-read is true. The bindings tree is in the channel master's
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

## ⚠ `set` has TWO halves, and a STANDING seat calls only the second

`set_seat` = resolve which sheet (from the workflow manifest) + prove the seat is one of the
manifest's + **`cast_seat`**. `cast_seat(path, seat, harness, model, effort_number)` is the half that
validates a cast against the catalog and writes it into one seat of an EXISTING sheet — it was split
out on 2026-08-12 so a caller that already KNOWS its sheet and its seat has nothing to resolve.

That caller is **`capabilities/master-profile`**, the channel master's own knob. A standing seat is
not a workflow, so it has no manifest and no four-letter code, and its sheet is named for the SEAT
(`bindings/channel-master.json`) — which is why `set` cannot serve it (task 7.617) and why that file
was hand-authored until the retarget. ⚠ **The decision recorded in row 7.749 — teach `rbtv-bindings`
a standing-seat MODE, or let `master-profile` write the file itself — was resolved as NEITHER
extreme: `master-profile` owns the transport and the path, and this capability owns the validation
and the write.** No second opinion about what may go in the file exists, and no verb here grew a
standing-seat surface nobody asked for. The imports are pinned by object identity in
`capabilities/master-profile/probes/probe-master-profile.py` check 10d.

## ⚠ The write is `ensure_ascii=False`, and that is a fix

`_write` dumped without it until 2026-08-12, so writing ONE seat's three casting fields also rewrote
every line of prose in the sheet containing a non-ASCII character — `—` became `\u2014` in the
`_what` / `_code` / `description` keys nobody touched. Measured on the channel master's sheet: a
three-field change produced a five-line prose diff. These files are hand-authored and read by
humans; the file is opened as UTF-8 either way, so nothing a parser sees changed. The two planning
sheets on this deployment still carry escaped dashes from earlier writes.

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

…and the **levels** of a dial that exists come from **the profile's own `effort.rungs` list** — per
MODEL, never per harness (owner ruling 2026-08-11: *"effort level is not per harness, is per
model"*). A profile IS one harness+model pair, so `claude-haiku` declares `effort: { inert: true }`
while `claude-fable` declares five rungs: same harness, different ladders. A bindings value is passed
to the harness LITERALLY (`coord.py#harness_command`), and this tool's 1-based `<effort-number>`
indexes that list — the same numbering as the daemon lane's rung.

⚠ **This section used to describe a per-harness `NATIVE_EFFORT` table as a live second copy of that
fact, and a collapse deferred until kimi's two spellings were reconciled. Both are gone.** The table
was deleted with the ruling above — keyed by harness it could not express two ladders for one
harness, and it mis-zeroed opencode — and the kimi blocker went with it, because the sheet stores a
NUMBER and a number has no spelling.

What is there now is ONE ladder, in `spawn-profiles.yaml`, and **two readers — one per language
runtime**:

| Reader | What it is |
|--------|------------|
| `launch-profiles/profiles.js#loadConfig` | The authoritative `js-yaml` parse: the loader the daemon itself boots on, which also VALIDATES the block (an empty `rungs:` list, or `inert: true` beside a translation, is refused at load). |
| `bindings.py#profile_effort` | The one PYTHON reader, a `yaml.safe_load` parse. Three-way answer: `None` = no dial · `[]` = an INERT dial (G-270 — accepts a rung, applies none) · a list = the rungs. **`master_profile.effort_ladder` IS this function object**, imported. |

There were THREE readers until 2026-08-11, and the two Python ones disagreed on identical bytes: a
`rungs:` line sitting above an `effort: { inert: true }` line read as INERT to one and as a five-rung
ladder to the other, and a `rungs:` written as a YAML block sequence was invisible to both while the
authoritative reader read it correctly. Both scrapes were replaced by the one parse. The remaining
two are pinned by **object identity** in `capabilities/master-profile/probes/probe-master-profile.py`
— never by value equality, which is what two copies report right up until they drift.

⚠ **Reading is not writing.** Reads of `spawn-profiles.yaml` are PARSES; writes to it stay
line-precise edits, because the document is hand-authored and its comments are its documentation.
Only a DUMP would destroy them, and nothing here dumps.

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
