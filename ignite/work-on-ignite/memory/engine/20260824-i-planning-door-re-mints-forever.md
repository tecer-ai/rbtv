# 20260824-i-planning-door-re-mints-forever — Planning door re-mints forever on divergent seat ids

kind: issue
component: engine
date: 2026-08-24
commit: 8713ca14
deployed: no
pin: ignite/engine/probes/probe-queue-request-pass.js
components: planning,meta-planning

## Observed

On branch `ignite/core-redesign` in the redesign worktree, every goal carrying `role: planning`
in its `goal.md` frontmatter read as unminted on every daemon cadence. `server/index.js` calls
`runQueueRequestPass` before the lane watch at boot and again inside the ~10s interval; each of
those passes walked the goal, found the pipeline absent, and shelled `path_a.py` to mint it again.
The mint itself succeeds, so nothing errored and no alarm fired — the goal simply accumulated a
supervised materialize invocation roughly every ten seconds for as long as the daemon ran, with
`pipeline-seats.json` and the goal's own `taskforce.csv` both sitting there looking correct in
isolation. Found by the `rename-plan-console` seat while auditing what the `86c9667c` rename had
left behind, not by any probe: `engine/probes/probe-queue-request-pass.js` was green the whole
time and its `already-minted` and `second cadence mints nothing` legs both reported PASS. Nothing
here is deployed — the live repo and running daemon are still pre-cutover and still name the
workflow `planning`, so the symptom was latent on this branch rather than burning a live goal.

## Mechanism

Two vocabularies existed for one thing. `planning/door.js` loads `pipeline-seats.json` into
`PLANNING_SEATS` and `pipelineMinted(rows)` asks whether every one of those strings appears in the
`seat` column of the goal's `taskforce.csv`. That column is written by the mint, which runs
`materialize-seats.py --workflow plan-console` and therefore emits the `Seat/workflow` column of
`meta/planning/workflows/plan-console/plan-console.csv` — `plan-understander`, `plan-designer`,
`plan-drafter`, `plan-reviewer`, `plan-verifier`. `pipeline-seats.json` held
`["understand","design","draft","review-finalize","verify"]`, which are role words, not seat ids,
and match nothing the manifest can produce. The two sets are disjoint, so `every()` returned false
unconditionally: not "sometimes stale", but structurally unsatisfiable. The json was authored at
`88ac3206` when the door landed, and that entry's own Consequences section recorded the dependency
honestly — "impl-pipeline must author the five seats named in `pipeline-seats.json` before a live
mint succeeds" — but the pipeline seat authoring at `67f93286` chose `plan-*` ids under
`references/seat-id-naming.md` and nothing carried that choice back to the json. The `86c9667c`
rename then moved the manifest to `plan-console/plan-console.csv` and repointed four workflow-name
strings, which is why the file looks recently maintained; the rename never touched the seat ids,
because the rename was correct — the ids had already diverged before it.

## Attempts

First attempt held — checked: `88ac3206` (the door and the json's authoring), `67f93286` (the
five-seat pipeline that fixed the real ids), `86c9667c`/`a2607f9b` (the plan-console rename), and
the memory entries `20260824-c-path-a-goal-wide-planning-seat`,
`20260824-c-rename-the-planning-workflow-t`, `20260824-c-d13-replan-mini-pipeline` and
`20260824-c-retire-the-17-rolling-planning`. No earlier commit or entry addresses this divergence;
the door's non-termination work at `88ac3206` fixed the IE-2 per-milestone splice, which is a
different re-fire cause, and its fix left this one intact.

## Fix

The json now carries the manifest's five ids, and the manifest is declared the source of truth in
prose at three surfaces: a block comment above `SEATS_FILE` in `door.js` saying the json is a
cached mirror and that divergence makes `pipelineMinted()` permanently false, the
`ignite/planning/README.md` minted-definition sentence, and a `pipeline-seats.json` row in
`planning/module.md`. A comment-equivalent field inside the json was rejected because the file is a
bare array read by two callers (`door.js` and `argv.py`) that both index it positionally; turning
it into `{source, seats}` would have widened a defect fix into a format change across a Python and
a JS reader for no behavioural gain.

Deleting the json entirely and having the door read the manifest directly was the other candidate,
and it was rejected on coupling: the door runs per goal on every cadence and would then need a
resolved `catalogRoot` before it could answer already-minted, but `resolveCatalogRoot` is allowed
to refuse (five distinct refusal codes), and a workspace with no catalog would stop being a quiet
"nothing to mint" and start being an unanswerable question. Keeping the cheap local mirror and
making divergence LOUD was the better trade.

Loud is where the real fix is. `engine/queue-request.js` — which already owns
`PLANNING_MODULE`/`PLANNING_COMPONENT`/`PLANNING_WORKFLOW` and the catalog resolution — gained
`planningManifestPath()` and `planningManifestSeats(catalogRoot)`, reading the manifest's first
column at `<component>/workflows/<W>/<W>.csv`, the one path shape `materialize-seats.py` resolves.
It parses the id cell as the text before the first comma, because later manifest columns are
RFC-quoted and do contain commas while the id column never is. Its module selftest now asserts
`planningManifestSeats` deep-equals `PLANNING_SEATS`. In the probe, new leg M derives its whole
expectation from the real checked-in manifest rather than a fixture, asserts the json is that
column in order, asserts a manifest-seated taskforce reads MINTED, and — because the original
blindness was hand-typed fixtures agreeing with a wrong json — greps the probe's own source and
fails if any leg types a seat id as a literal at all. The remaining fixtures (`TF_MINTED`, the
casting sheet, the wrote-the-seats assertion) were rewritten to derive from `PLANNING_SEATS`.

## Consequences

`pipelineMinted()` now answers true for a real minted goal, so the door falls to its intended quiet
`already-minted` debug no-op and the ~10s re-mint stops. Anything that had learned the old role
words is wrong: a grep of the worktree for `review-finalize` outside the memory store returns
nothing, so no other caller had. `argv.py` `PLANNING_SEATS` and its `--seats-json` flag change value
with the json and were not otherwise touched; `path_a.py` takes `seats=` from its caller and is
unaffected. The probe is now coupled to the catalog tree in the same repo — it resolves
`REPO_ROOT/meta/...` — so running it against a tree without `meta/` will fail leg M rather than
skip it, which is deliberate. The `plan.json` casting-sheet fixture inside the probe now keys its
seats by `plan-*`; that is fixture-only and does not touch the real workspace bindings sheet, which
is keyed by seat id and already correct because `67f93286` authored it.

Not fixed here and still open from the rename entry: `config/spawn-profiles.yaml` and
`capabilities/goal-creation-request/goal-creation-request.md` both still claim the workflow has
"16 manifest seats" when it has five, and `capabilities/bindings/probes/probe-bindings.py` still
asserts on the retired seat id `plan-binder`.

## Verification

`node --check` clean on `planning/door.js`, `engine/queue-request.js` and the probe.
`node ignite/engine/queue-request.js` selftest OK, now including the manifest deep-equal.
The demonstration that the new leg has teeth: run against the PRE-FIX json, the probe exited 1 with
`FAIL M pipeline-seats.json IS the manifest Seat/workflow column, in order — manifest
[plan-understander plan-designer plan-drafter plan-reviewer plan-verifier] vs json [understand
design draft review-finalize verify]` and `FAIL M a manifest-seated taskforce reads MINTED`, while
all nineteen pre-existing fixture legs stayed green — which is precisely the blindness being
closed. After the json fix the same probe is `RESULT: PASS`, EXIT 0, 23 legs. All four
`ignite/planning/probes/probe-planning-*.py` exit 0 (lock, failure-record, path-b-failure,
path-b-materialize) and `python3 -m py_compile` is clean on all six planning `.py` files.
Committed `8713ca14` by explicit pathspec. NOT deployed: pre-cutover worktree edit on
`ignite/core-redesign`.

## ATTENTION

- `pipeline-seats.json` is a mirror, not a source. Editing it to a name the `plan-console` manifest
  does not carry does not fail loudly at load — it silently makes `pipelineMinted()` unsatisfiable
  and turns the door into a per-cadence mint loop that logs nothing but `info` about minting.
- Do not "fix" the `plan-*` seat ids to match the workflow name `plan-console`. The workflow CODE is
  `plan` and is ruled independent of the workflow name by `references/seat-id-naming.md`; the
  bindings capability's `workflow_code()` refuses any prefix that is not exactly four letters, so
  `plan-console-*` is rejected on deploy.
- Probe leg M must keep reading the checked-in manifest. Replacing it with a fixture restores the
  exact condition that let this ship: nineteen green legs over a door that could never fire
  correctly, because the fixture and the wrong json agreed with each other.
- `planningManifestSeats()` reads the first column as text-before-first-comma. That holds only
  while the id column stays unquoted; a manifest that ever quotes an id needs a real CSV parser here
  and will otherwise return an id with a stray leading quote that compares unequal and, again, only
  shows up as a re-mint loop.
- The door decides already-minted from a LOCAL file on purpose, so a workspace with no resolvable
  catalog stays a quiet no-op. Moving that decision behind `resolveCatalogRoot` makes five refusal
  codes into blockers on a question that should always be answerable.
- pipeline-seats.json is a MIRROR of the plan-console manifest's Seat/workflow column; a name the manifest cannot produce makes pipelineMinted() unsatisfiable and the door mints every ~10s cadence, silently
- Do not rename the plan-* seat ids to match the workflow name plan-console; the workflow code is ruled independent and workflow_code() refuses any prefix that is not exactly four letters
- Probe leg M must keep reading the checked-in manifest; a fixture there restores the blindness that let 19 green legs cover a door that could never fire
- planningManifestSeats() reads the id cell as text-before-first-comma, valid only while that column stays unquoted
