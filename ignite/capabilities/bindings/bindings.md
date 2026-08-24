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
`.rbtv/config/modules/<module>/<component>/…` (`ignite/team-kit/starter-set/conduct.md`, which
once stated this, was abolished by owner ruling F7, 2026-08-17; `capabilities/bindings/tool/bindings.py`
now carries the canonical path).

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

## ⚠ The GOAL-LOCAL sheet — a second path, for seats no catalog carries (owner ruling 2026-08-14)

```
<goal>/planning/current/bindings.json     ← the seats the goal's own planning pass AUTHORED
```

A planning pass can author a seat inside the goal — `planning/current/seats/<seat>/` holding the
definition itself rather than a `source.md` pointer at a cataloged one. **Those seats belong to no
workflow**, so the canonical path above cannot address them: `bindings/{code}.json` is keyed by a
workflow code they do not have. `ignite/engine/unbuilt-seats.js` (`sheetForSeat`) states exactly this and is
the reason the two paths differ — it is a design, not a bug, and the reader must never be "fixed" to
look under `.rbtv/config/`.

The engine reads the goal-local sheet at `buildGoalLocalSeats` (`unbuilt-seats.js`) and
**refuses `goal-local-sheet-absent` when it is missing** — an uncast goal-authored seat is a named
refusal at every door, never a default (`#d-abolish-profile-names`). Until this mode existed nothing
wrote that file, so every goal whose pass invented a seat stalled at it.

**Every verb takes a GOAL FOLDER in place of `<workflow.csv>`** — dispatched on the argument's own
shape (a directory is a goal; a file is a manifest), so there is no parallel verb set:

```bash
rbtv-bindings scaffold .rbtv/goals/<goal>                                  # sheet, every seat uncast
rbtv-bindings set      .rbtv/goals/<goal> <seat> claude claude-opus-5 3    # same validator
rbtv-bindings inspect  .rbtv/goals/<goal>                                  # casting state
```

The seat set is the goal's `planning/current/manifest.csv` **minus the cataloged reuses** — exactly
the set `materialize-seats.py --goal-local` builds its lane from, which is why casting a `source.md`
seat here is REFUSED: its cast belongs to its own workflow's sheet, and a key outside the
materialized set is `bindings-extra-seat` for the whole batch. Everything else is identical to the
cataloged path — the same `catalog` gate on harness/model/effort, the same atomic write, the same
create-only `scaffold`. `--config-root` is refused in this mode: the sheet is goal product, not
deployment config, so there is no config root to point at.

The only shape difference is `component:`, which is ABSENT per seat: it names the mirrored component
a cataloged seat's definitions come from, and a goal-authored seat has none (the derived lane
`materialize-seats.py` rebuilds on every run is not a component home).

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
| `set-many <workflow.csv> <casts.json>` | Casts **N seats of one workflow in one validated call**, ALL-OR-NOTHING. |

## `set-many` — casting a whole workflow in one call

```bash
rbtv-bindings inspect  <workflow.csv>            # what the seats are, and which are uncast
#   … the owner decides the casting — this CLI never invents one …
rbtv-bindings set-many <workflow.csv> casts.json # one call, refused whole or applied whole
```

```json
{ "plan-binder":  { "harness": "claude", "model": "claude-opus-5",    "effort": 4 },
  "plan-planner": { "harness": "claude", "model": "claude-haiku-4-5" } }
```

One entry per seat, carrying exactly the three things `set` takes — and `effort` is the **1-based
rung NUMBER**, never its word, because the file is what stores the word. The sheet's own
`{"seats": {…}}` wrapper is accepted as input too, so a document copied out of `inspect` or out of
the file itself works unchanged. A pair with no dial omits `effort`.

⚠ **ALL-OR-NOTHING, and the validation is `set` itself.** Every seat is run through
`set_seat(… dry_run=True)` — the same path, the same `catalog` gate, the same manifest-membership
check — and the file is opened only if ALL of them pass. One bad seat and the sheet is left
byte-identical, with **every** offending seat's own reason in the refusal, so the author fixes the
document once instead of discovering the seats one refusal per run. The failure this prevents is a
half-cast taskforce: through the one-seat verb, an agent that gets seat 7 wrong has already written
seats 1–6, and nothing notices until materialize refuses the batch at goal-creation time.

There is no second validator and no second writer here — the destination stays derived from the
workflow path (no path argument), and `set-many` refuses over an absent sheet exactly as `set` does
(`scaffold` first). It exists for the channel master's casting flow: **inspect → discuss with the
owner → one batch `set-many`**. The CLI validates; the owner decides.

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

1. **Which harness+model pairs exist** — `launch-specs:` in `ignite/config/spawn-profiles.yaml` (the block is KEYED by the pair since `#d-abolish-profile-names`, so the pairs are READ, never derived), which
   `r-seats-only-architecture` makes *"ONE PROFILE PER HARNESS+MODEL … nothing else is identity"*.
   That IS the workspace's spawnable set. The harness is the profile's `argv[0]`; the model is the
   literal its `exec` argv PINS.
2. **Whether a pair has an effort dial** — the profile's own `effort:` block. `effort: { inert: true }`
   is a MEASUREMENT under G-270 (*"a harness whose dial does not exist says so"*), so an inert
   profile has no dial — and a rung on it is **accepted and stored as the word `inert`** (owner
   ruling `d-effort-refuses-only-where-a-dial-exists`). See § The effort NUMBER.

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
predicate rejects is listed NOT CASTABLE with its reason rather than dropped: today `test-sleep`
(no harness at all) — the standalone `kimi` harness is retired outright, so `spawn-profiles.yaml`
carries no `kimi` row for this predicate to reject in the first place.

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
because that string is what reaches the binary. Out of range refuses with the ladder printed.

⚠ **An INERT profile (`effort: { inert: true }` — `claude-haiku`) ACCEPTS a rung and stores the word
`inert`, with or without a number.** This REVERSED on 2026-08-12, under owner ruling
`d-effort-refuses-only-where-a-dial-exists` — *refuse only where a dial EXISTS and the level is out
of its range*. The old refusal popped the field, and `materialize-seats.py#open_binding` then
refused the half-declared triple on a standing seat, so the channel master's `claude-haiku` cast was
un-makeable through this CLI and its sheet had to be hand-written. `inert` is not a rung name
because an inert profile has no ladder to name one from; every downstream reader
(`profiles.js#resolveEffort`, `catalog.js#effortRungFor`, `coord.py#validate_seat`) reports inert
before it looks at the word. A profile declaring **no `effort:` block at all** still refuses a rung —
there, nothing downstream could translate one either.

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
touched). Ten checks: the catalog moves when the profiles copy is re-pinned; every offered pair
survives `validate_seat`; the effort number indexes the native ladder while the file stores the
string; six refusal shapes each leave the sheet byte-identical; the code derivation refuses a mixed
manifest and any code that is not exactly four ASCII letters; **four mutants** (each WIDENING one guard — a deletion crashes, and a crash reads like a
refusal) prove those arms discriminate; `materialize-seats.py --dry-run` plans clean over the
artifact this tool writes, with the one-seat-uncast twin refusing; both launch doors spell every
rung of every castable ladder identically; and `set-many` casts three seats in one call while a
batch carrying bad seats leaves the sheet byte-identical — proven discriminating by a mutant that
collapses its validate-then-write two-pass into write-as-you-go (the batch still refuses, so the
scoring observation is that the sheet MOVED). Check 10 covers the GOAL-LOCAL mode on a throwaway
goal with synthetic goal-authored definitions: the sheet lands at the literal path the engine reads,
its keys are the goal-authored seats and not the cataloged reuse beside them, `materialize-seats.py
--goal-local --dry-run` — `goalLocalLint`'s own argv — exits 0 over it and the descriptors it plans
carry that sheet's casting; its mutant widens the cataloged-reuse filter so casting `plan-dod-judge`
into the goal-local sheet becomes ACCEPTED.

Run it through the enumerator: `node deploy/probe-suite.js --only probe-bindings`.
