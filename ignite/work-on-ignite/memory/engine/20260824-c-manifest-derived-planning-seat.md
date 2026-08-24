# 20260824-c-manifest-derived-planning-seat — Manifest-derived planning seat divergence alarm

kind: creation
component: engine
date: 2026-08-24
commit: 8713ca14
deployed: no
pin: ignite/engine/probes/probe-queue-request-pass.js
components: planning,meta-planning

## Motivation

`engine/probes/probe-queue-request-pass.js` was green across all nineteen of its legs while the Path
A planning door could not fire correctly at all: `pipeline-seats.json` named role words the
`plan-console` manifest can never emit, so `pipelineMinted()` was unsatisfiable and the door
re-minted every ~10s cadence (filed as `20260824-i-planning-door-re-mints-forever`). The probe
missed it because it supplied its own fixture seat names, hand-typed to agree with the json. A probe
whose expectation comes from the same wrong place as the code under test proves nothing. What was
owed was a check anchored to the one artifact that is authoritative — the workflow manifest on disk.

## Design

The manifest is the source of truth for the planning seat ids, because
`materialize-seats.py --workflow W` resolves exactly `<component>/workflows/<W>/<W>.csv` and writes
that file's `Seat/workflow` column onto the goal's `taskforce.csv`. Everything else is a mirror. So
the reader lives in `engine/queue-request.js`, not the probe: that module already owns
`PLANNING_MODULE`/`PLANNING_COMPONENT`/`PLANNING_WORKFLOW` and the catalog resolution, so putting it
there keeps the path shape stated once and makes it available to the module selftest as well as the
probe. Putting it in `planning/door.js` was rejected — the door has no workflow-name constant and
would have had to duplicate one, and the door is deliberately allowed to answer already-minted from
a purely local file so that a workspace with no resolvable catalog stays a quiet no-op rather than
an error.

## How it works

`planningManifestPath(catalogRoot)` joins `PLANNING_MANIFEST_REL`
(`planning/workflows/plan-console/plan-console.csv`, built from the existing constants).
`planningManifestSeats(catalogRoot)` reads it, drops the header, and takes each row's text before
the first comma — valid because later manifest columns are RFC-quoted and contain commas while the
id column never is. Unreadable or empty manifests raise the module's own `Refusal` with codes
`queue-request-planning-manifest-unreadable` / `-empty`, matching the five refusal codes
`resolveCatalogRoot` already speaks. Both are exported alongside `PLANNING_MANIFEST_REL`.

Two callers consume it. The `queue-request.js` module selftest (`node ignite/engine/queue-request.js`)
deep-equals the manifest column against `PLANNING_SEATS`. Probe leg M, which runs first, resolves
`REPO_ROOT/meta` from the probe's own location and makes four checks: the manifest exists; the json
IS that column in order; a taskforce seated from the manifest reads MINTED through `pipelineMinted`;
and — the reflexive one — the probe's own source is grepped for each manifest seat id as a literal,
failing if any leg hand-types one. The remaining fixtures (`TF_MINTED`, the casting sheet, the
wrote-the-seats assertion) were rewritten to derive from `PLANNING_SEATS` so that guard holds.

## Consequences

The probe is now coupled to the catalog tree in the same repo: run it against a checkout without
`meta/`, and leg M fails rather than skipping. That is deliberate — a silently skipped divergence
alarm is the thing being fixed. Leg M's own failure at the pre-fix json is what forced
`pipeline-seats.json` to the real ids in the same commit. Nothing was deleted; the nineteen existing
legs kept their assertions and only changed where their seat names come from. No follow-up is
outstanding for this piece, though the seat-count staleness in `config/spawn-profiles.yaml` and
`capabilities/goal-creation-request/goal-creation-request.md` noted at `86c9667c` remains open and
is a different kind of drift on the same workflow.

## Verification

Proven by its own red: against the pre-fix `pipeline-seats.json` the probe exited 1 with
`FAIL M pipeline-seats.json IS the manifest Seat/workflow column, in order` and
`FAIL M a manifest-seated taskforce reads MINTED`, while all nineteen fixture legs reported ok — a
check that only ever passes proves nothing, so this red is the evidence. After the json was
corrected the probe is `RESULT: PASS`, EXIT 0, 23 legs, WALL_MS ~112. `node --check` clean on the
probe and on `queue-request.js`; the module selftest prints `queue-request selftest OK`. Committed
`8713ca14`. NOT deployed: pre-cutover worktree edit on `ignite/core-redesign`.

## ATTENTION

- Leg M's expectation must come from the checked-in manifest. A fixture there re-creates the exact
  hole it was built to close: agreement between two copies of the same mistake, reported as green.
- The "no leg hand-types a seat id" check greps the probe's own source. Adding a legitimate literal
  mention of a seat id anywhere in that file — even in a comment — turns it red; derive from
  `PLANNING_SEATS` instead of loosening the check.
- `planningManifestSeats()` is a first-comma split, not a CSV parser. It is correct only while the
  id column is unquoted; a quoted id returns a value with a stray quote that compares unequal and
  surfaces only as a mint loop.
- Manifest folder name and file name are ONE identity (`--workflow W` → `<component>/workflows/<W>/<W>.csv`).
  `PLANNING_MANIFEST_REL` encodes that; building the path any other way can find a file the mint
  itself would never resolve.
- Leg M must read the checked-in plan-console manifest, never a fixture — a fixture re-creates the blindness it closes
- planningManifestSeats() is a first-comma split, not a CSV parser; only valid while the id column stays unquoted
- The no-hand-typed-seat-id check greps the probe's own source, so even a comment mentioning a seat id turns it red
