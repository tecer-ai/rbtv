'use strict';

// engine/queue-request.js — THE `queue-request` CONSUMER PASS (W7 of the silent-stall rulings
// programme; the type's own record is `system-definition/concepts/queue-request.md`, settled by
// `decisions.md#d-message-types-seven`).
//
// THE DEFECT IT CLOSES (D7): a milestone judge records a PASS, the unblock-checker derives which
// milestones just became ready — and NOTHING reads that derivation. Every multi-milestone daemon
// goal parks at every wave boundary, looking healthy. `coord.py` now WRITES the request row; this
// file is the reader that gives it a mechanical consequence.
//
// WHAT IT IS NOT:
//   · NOT a second bus parser. `coordinate ... queue-requests --json` is the ONE reader of
//     `coordination/messages.md` (adv, C66/fidelity-2) — exactly as `engine/seeding.js` shells
//     `ready-seats` rather than re-deriving readiness in JS. There is no JS `messages.md` reader
//     anywhere in this file and there must never be one: a header key coord adds is a key a JS
//     reader silently drops.
//   · NOT a second seat-name composer. Every composed name of a nested instance comes from
//     `materialize-seats.py#compose_seat_name`. Nothing here spells `<prefix>-<n>-<seat>`.
//   · NOT a second splicer. The nested materializer's own append IS the splice (see § REUSE THE
//     PURE CORE below), and this pass never re-parents an existing row — so `goal_cli.py`'s
//     `--before` machinery has no analogue here at all.
//
// ── THE SEVEN CLI GATES, AND THIS PASS'S VERDICT ON EACH ─────────────────────────────────────
//
// `rbtv-goal add-seat` (`capabilities/goals-tree/tool/goal_cli.py#cmd_add_seat`, ~:3255) is the
// HUMAN door that grows a live goal's roster. It carries seven gates. This pass is the MACHINE
// door for the same act, and the gates are ruled one at a time — a gate copied without its
// reason is a gate that will be wrong here.
//
// | gate | what it refuses (goal_cli.py)               | verdict | why                                |
// |------|---------------------------------------------|---------|------------------------------------|
// | (a)  | the goal is not PAUSED (`goal-not-paused`)  | STRIP   | the pass IS mid-run. Pausing exists so a HUMAN's splice cannot race the seeder; this pass runs INSIDE the daemon's own loop, before `engine.tick`, so there is no concurrent seeder to race — demanding a pause here would mean the daemon must pause itself to serve itself. |
// | (b)  | an open execution row (`goal-not-quiescent`)| STRIP   | same: a wave re-entry happens precisely while other seats of the goal are running. Quiescence is a property this act can never have. |
// | (c)  | a `--before` seat has already run           | N/A     | the pass NEVER re-parents. It appends rows and rewrites no `after` cell of any existing row, so there is no successor whose resolved edge could be falsified. |
// | (d)  | `ATTACHED_RUN_LOCK` (`attached-run-live`)   | **KEEP**| a console `rbtv run` is advancing THE SAME GRAPH this pass appends to. Two writers to one `taskforce.csv` is the defect; the daemon is not the attached runner and must stay off the goal. Implemented via `consoleRunIsLive` (`./lane-watch`) — the lock's own LIVENESS test, so a crashed runner's stale lock cannot park the goal forever. |
// | (e)  | `--bindings` sheet carries the seat         | STRIP   | as a CLI ARGUMENT. The operator names a sheet at that door; here the sheet is the goal's own component sheet, resolved at splice time (§ THE BINDINGS SHEET). The CHECK it performs is not stripped — it is strengthened into the uncast refusal below, which reads the same sheet and refuses on the same fact. |
// | (f)  | `daemon-complex-cell`                       | STRIP   | VERIFIED LIVE, see § GATE (f) below. |
// | (g)  | splice preflight (`_preflight_splice`)      | KEEP    | "is this write possible at all, computed before anything is minted". Kept in the only form this pass can have one: the pre-write refusals below (malformed key, unresolvable catalog root, unreadable milestone mode, UNCAST bindings) all fire before the materializer is spawned, so a refusable pass never leaves a half-grown goal. |
//
// ── GATE (f), AND THE EVIDENCE THAT LIFTS IT ─────────────────────────────────────────────────
//
// The gate refuses a splice that writes a multi-member or guarded `after` cell onto a goal whose
// stashed lane is `daemon`, and its own text names the lift: "The parallel seeder fix
// (engine/seeding.js) lifts this concern once deployed." The precondition was verified LIVE on
// this workspace rather than reasoned about, because the full-mode planning chain is made almost
// entirely of the cells it refuses:
//
//   `3-resources/tools/rbtv/meta/planning/workflows/planning/planning.csv` carries
//     · a SIX-member cell        — plan-check-assembler after plan-check-{edges,resources,
//                                  permissions,scope,clarity,consistency}
//     · GUARDED members          — plan-task-definer after plan-dag-structurer[planning-mode=full]
//                                  plan-planner     after plan-dag-structurer[planning-mode=collapsed]
//     · a guarded ALTERNATE cell — plan-check-mechanization after plan-assembler,
//                                  plan-interviewer[use-case=optimize]|…[port]|…[scaffold]
//
//   and `coordinate --package .rbtv/goals/meet-transcript-summarizer ready-seats --json` — THE
//   reader the daemon seeder consumes (`seeding.js#readySeats`), which is the whole of the
//   seeder's readiness arithmetic — resolves every one of them per member:
//     plan-task-definer        met:false  state "<guard planning-mode=collapsed>"
//     plan-planner             met:true   state "done+guard-ruled"
//     plan-check-mechanization        state "<any-of unmet: …[optimize]=exited …[port]=exited …>"
//     plan-check-assembler            six members, each rendered with its own met/state
//
// So the cell class is not merely handled — it is decomposed member by member by coord's
// `taskforce_after`/`parse_after_member` (the ONE grammar reading, 7.383/7.424), and the JS side
// holds no after-cell reader at all. The gate's stated lift condition is met; it is STRIPPED.
//
// ── REUSE THE PURE CORE (adv, C67): THE NON-GATE MECHANICS ARE **NOT** RE-IMPLEMENTED ────────
//
// The gate-stripping ruling does NOT cover the atomicity mechanics, and this pass writes none of
// them, because the nested materializer ALREADY performs all three, with evidence:
//   · single-write splice ........... `team-kit/materialize-seats.py:4411` `_rewrite_in_place`
//                                     (one `os.pwrite` under an exclusive `flock`, SAME INODE;
//                                     never an open-append, and — since task 08 — never
//                                     `tmp + os.replace`, which orphaned the dentry a seat's
//                                     single-file cage bind was attached to), called at `:4484`.
//   · changed-underfoot re-read ..... `:3840` `registry-changed-underfoot` — the file is re-read
//                                     immediately before the write and compared to the text the
//                                     validations ran against.
//   · acyclicity over the MUTATED
//     rowset ........................ `:3713` `check_acyclic(combined, …)` where `combined` is
//                                     existing rows PLUS the rows this run would append — through
//                                     `goal_cli.check_acyclic` itself (imported at `:192-198`),
//                                     never a hand-rolled walk.
// ⚠ RESIDUAL, disclosed rather than papered over: `cmd_add_seat` also runs `check_after_grammar`
// over the mutated rowset and the materializer does NOT (no call site exists in that file). It is
// not re-implemented here either: every `after` cell this pass causes is written by the
// materializer itself — internal cells copied verbatim from the workflow manifest and mechanically
// re-keyed, and the attach cell, which is a plain comma-joined list of existing seat names with no
// guard and no alternate. The grammar has no way to be violated by a cell of that shape. If a
// future caller passes an authored `--after` cell, this residual becomes real.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { requirePythonCmd } = require('../lib/python-cmd');
// The lane gate is READ from lane-watch, never re-implemented: `readLane`/`laneIsPaused` already
// have a python twin they must stay in step with (DEC-1), and a third reading of the marker is a
// third answer. `consoleRunIsLive` is gate (d).
const { readLane, laneIsPaused, consoleRunIsLive, DAEMON } = require('./lane-watch');
const { readCsv, readTaskforce } = require('./seeding');
// The SAME predicate `uncastSeats` refuses on (`seeding.js#uncastSeats`), reached directly because
// the seats this pass is about do not exist on disk yet — see § THE UNCAST REFUSAL.
const { declaresBinding } = require('../launch-profiles/catalog');

const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
const MATERIALIZE_PY = path.join(__dirname, '..', 'team-kit', 'materialize-seats.py');
const SUBPROCESS_TIMEOUT_MS = 120000;

// THE ROUTE IS OWNER-RULED (D-6): a queue-request's pass is a NESTED INSTANCE of the `planning`
// workflow of the `meta/planning` component. These four constants are that ruling, spelled out in
// one greppable place rather than derived — there is exactly one planning workflow and deriving
// "which workflow plans" from the request would be inventing a payload the type deliberately does
// not carry (`concepts/queue-request.md` § What it deliberately does NOT carry).
const PLANNING_MODULE = 'meta';
const PLANNING_COMPONENT = 'planning';
const PLANNING_WORKFLOW = 'planning';
const PLANNING_CODE = 'plan';          // the bindings sheet's filename == the workflow's CODE
const COLLAPSED_SEAT = 'plan-planner'; // the one seat a `collapsed` milestone's pass runs

// A nested instance's taskforce-id, as `materialize-seats.py` mints it: `tf-<n>-<prefix><m>`.
// MIRROR of `NESTED_TF_RE` (`materialize-seats.py:822`) and used for ONE thing only — counting how
// many nested passes a milestone has already had (§ CONSUMPTION DETECTION). It composes no name.
const NESTED_TF_RE = /^tf-\d+-[a-z]{4}\d+$/;

class Refusal extends Error {
  constructor(code, message) { super(message); this.code = code; }
}

// ── THE WORKSPACE, THE BOOK, AND THE CATALOG ROOT (the F2 fix, in JS) ────────────────────────
//
// `goalsRoot` IS `<workspace>/.rbtv/goals` — that is the daemon's own construction
// (`server/index.js`: `path.join(workspaceRoot, '.rbtv', 'goals')`), so the workspace is two
// levels up and is derived from the ARGUMENT. Never from `process.cwd()` (a daemon's cwd is
// whatever systemd gave it) and never from an env var (an unset one reads as a plausible wrong
// answer). This is the JS copy of `materialize-seats.py#_rbtv_repo_root` (:3070-3115): the book is
// read, its field is required, and EVERY missing step refuses with its own NAMED code rather than
// falling through to a default that would materialize into the wrong tree.
function resolveCatalogRoot(goalsRoot) {
  const workspace = path.resolve(goalsRoot, '..', '..');
  const book = path.join(workspace, 'rbtv.json');
  if (!fs.existsSync(book)) {
    throw new Refusal('queue-request-workspace-book-absent',
      `${book} — the book that records \`rbtv_path\` — does not exist, so this is not a workspace `
      + 'and there is no component catalog to materialize a planning pass from');
  }
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(book, 'utf8'));
  } catch (err) {
    throw new Refusal('queue-request-workspace-book-unreadable',
      `${book} is not readable JSON — ${err.message}`);
  }
  if (!String((parsed && parsed.rbtv_path) || '').trim()) {
    throw new Refusal('queue-request-workspace-book-no-rbtv-path',
      `${book} carries no \`rbtv_path\` — the one field that proves this tree is an rbtv workspace`);
  }
  // The catalog now lives IN the repo (`<rbtv>/meta/`, owner E11/E15). `rbtv_path` is the same
  // helper `materialize-seats.py#_rbtv_repo_root` uses — relative values resolve against the
  // workspace. The materializer BINARY is still the build this process IS (`__dirname`); only
  // the catalog root follows the book.
  let repoRoot = String(parsed.rbtv_path).trim();
  if (!path.isAbsolute(repoRoot)) repoRoot = path.resolve(workspace, repoRoot);
  const catalogRoot = path.join(repoRoot, PLANNING_MODULE);
  if (!fs.existsSync(catalogRoot)) {
    throw new Refusal('queue-request-catalog-root-absent',
      `${catalogRoot}: the component catalog root is absent — the '${PLANNING_WORKFLOW}' workflow `
      + 'is read from there and nothing can be materialized without it');
  }
  const sheet = path.join(workspace, '.rbtv', 'config', 'modules', PLANNING_MODULE,
    PLANNING_COMPONENT, 'bindings', `${PLANNING_CODE}.json`);
  if (!fs.existsSync(sheet)) {
    throw new Refusal('queue-request-bindings-sheet-absent',
      `${sheet}: the planning workflow's casting sheet is absent — which harness, model and effort `
      + 'each seat runs on has no honest guess (`#d-abolish-profile-names`)');
  }
  return { workspace, catalogRoot, sheet };
}

// ── THE REQUESTS, THROUGH COORD, PARSED NOWHERE ELSE ─────────────────────────────────────────
//
// Without `--all`, coord has ALREADY dropped the superseded rows and the rows whose VERDICT was
// superseded (`coord.py#cmd_queue_requests` :10466) — the supersedes-skip is coord's, consumed
// here, computed nowhere. A non-zero exit or unparseable output returns `null`, which is a
// REFUSAL and never an empty request list: "no requests" and "I could not ask" are different
// claims (`seeding.js#readySeats` takes the same shape for the same reason).
function queueRequests(goalFolder) {
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(),
      [COORD_PY, '--package', goalFolder, 'queue-requests', '--json'],
      { encoding: 'utf8', timeout: SUBPROCESS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    return { rows: null, reason: `\`queue-requests --json\` did not answer (${err.code || err.message})`
      + `${err.stderr ? `: ${String(err.stderr).trim().slice(0, 400)}` : ''}` };
  }
  let rows;
  try { rows = JSON.parse(raw); } catch {
    return { rows: null, reason: `\`queue-requests --json\` returned no JSON: ${String(raw).slice(0, 200)}` };
  }
  if (!Array.isArray(rows)) return { rows: null, reason: '`queue-requests --json` returned no row array' };
  return { rows, reason: null };
}

// ── CONSUMPTION DETECTION — THE LOG IS THE STORE (no separate consumption file) ──────────────
//
// A pass's rows all carry the milestone in `taskforce.csv`'s `milestone-id` column and the nested
// instance's OWN minted `taskforce-id` (`tf-<n>-<prefix><m>`, ruling `d-r2-tfid-structured-counter`
// — the identity the materializer publishes for exactly this purpose). So "how many passes has
// this milestone already had" is a COUNT OF DISTINCT NESTED TASKFORCE-IDS on that milestone's
// rows, read off the registry the pass writes to.
//
// ⚠ WHY NOT COMPOSED NAMES. The obvious detection — "do this pass's composed seat names exist" —
// cannot be computed without composing them, and composing them in JS is the second naming
// implementation this file exists not to have. Worse, the ordinal a composition would use is
// MAX+1 over the rows already present, so it MOVES the moment the first pass lands: a re-fire
// would compute the NEXT instance's names, find them absent, and mint again — the exact
// double-fire the no-double-fire arm proves cannot happen. The taskforce-id count does not move.
//
// The i-th live request for a milestone (log order, oldest first — coord's own ordering) is
// CONSUMED when that milestone already carries i+1 nested passes. That is what makes a re-check
// safe with no store: the splice is create-only, so re-reading the registry re-derives the same
// answer every cadence.
function passesMinted(rows, milestone) {
  const ids = new Set();
  for (const r of rows) {
    if ((r['milestone-id'] || '').trim() !== milestone) continue;
    const tf = (r['taskforce-id'] || '').trim();
    if (NESTED_TF_RE.test(tf)) ids.add(tf);
  }
  return ids.size;
}

// `full` | `collapsed` for one milestone, off the goal's own `milestones.csv`. Absent file, absent
// row or absent value REFUSES: a pass shape guessed wrong mints the wrong team, and "which of the
// two shapes" has no safe default.
function planningMode(goalFolder, milestone) {
  const file = path.join(goalFolder, 'milestones.csv');
  let rows;
  try { rows = readCsv(file); } catch (err) {
    throw new Refusal('queue-request-milestones-unreadable', `${file}: ${err.message}`);
  }
  const row = rows.find((r) => (r['milestone-id'] || '').trim() === milestone);
  if (!row) {
    throw new Refusal('queue-request-milestone-unknown',
      `${file} carries no row for milestone '${milestone}' — the request names a milestone this `
      + 'goal does not have');
  }
  const mode = (row['planning-mode'] || '').trim();
  if (mode !== 'full' && mode !== 'collapsed') {
    throw new Refusal('queue-request-planning-mode-unstamped',
      `${file}: milestone '${milestone}' carries planning-mode ${mode ? `'${mode}'` : '(empty)'} — `
      + 'the pass shape is `full` (the whole chain) or `collapsed` (`' + COLLAPSED_SEAT + '` alone), '
      + 'and there is no third answer to fall back to');
  }
  return mode;
}

// ── THE UNCAST REFUSAL — REFUSE BEFORE WRITING (adv, C69) ────────────────────────────────────
//
// ⚠ WHY THIS IS A REFUSAL AND NOT A WARNING. `runLaneWatch` skips a goal **WHOLESALE** on ONE
// uncast seat — `if (uncast.length) { … continue; }` — and after the first cadence that line is
// logged at `debug` (the `shouldShout` memo is keyed on the lane marker's text, which does not
// change). So splicing a SINGLE uncast row does not degrade the new pass: it FREEZES THE ENTIRE
// GOAL, silently, from the next cadence onward. That is precisely the silent-stall shape this
// whole programme exists to kill, and it would be caused BY the mechanism built to end it. A pass
// that would land any uncast row therefore writes NOTHING AT ALL.
//
// WHICH CHECK IS IMPLEMENTED, precisely. `uncastSeats` (`seeding.js`) answers the question off
// `seats/<seat>/seat.md` — the descriptor — so it CANNOT answer for seats that do not exist yet,
// which is every seat of an unminted pass. The cast is knowable pre-mint from exactly one place:
// the BINDINGS SHEET the materialize invocation will read (`--bindings`), which is where the
// descriptor's `harness`/`model` come from in the first place. So this pre-checks the sheet
// through `declaresBinding` — THE SAME PREDICATE `uncastSeats` filters on
// (`launch-profiles/catalog#declaresBinding`), so the pre-mint refusal and the post-mint one can
// never disagree about what "cast" means.
//
// COVERAGE, and its bound: for a `collapsed` pass exactly one seat is checked (the one that will
// be minted). For a `full` pass EVERY seat in the sheet is checked rather than every seat of the
// manifest — reading the manifest here would be a second reader of `planning.csv`. That is
// complete in the direction that matters and the materializer closes the other: a manifest seat
// MISSING from the sheet is its own refusal (`bindings-missing-seat`), and a sheet seat NOT in the
// manifest is `bindings-extra-seat`. Sheet ⊆ cast and manifest ⊆ sheet gives manifest ⊆ cast.
function uncastInSheet(sheetPath, onlySeat = null) {
  let sheet;
  try { sheet = JSON.parse(fs.readFileSync(sheetPath, 'utf8')); } catch (err) {
    throw new Refusal('queue-request-bindings-unreadable', `${sheetPath}: ${err.message}`);
  }
  const seats = sheet && sheet.seats;
  if (!seats || typeof seats !== 'object') {
    throw new Refusal('queue-request-bindings-schema',
      `${sheetPath}: must be a JSON object carrying a 'seats' mapping`);
  }
  if (onlySeat && !(onlySeat in seats)) {
    throw new Refusal('queue-request-bindings-missing-seat',
      `${sheetPath}: carries no entry for seat '${onlySeat}' — a missing binding is a refusal, `
      + 'never a default');
  }
  const names = onlySeat ? [onlySeat] : Object.keys(seats);
  return names.filter((s) => !declaresBinding({
    harness: (seats[s] || {}).harness, model: (seats[s] || {}).model,
  }));
}

// ── THE ONE INVOCATION ───────────────────────────────────────────────────────────────────────
//
// ⚠ EXACTLY ONE MATERIALIZE PER PASS, AND THAT IS THE WHOLE-CHAIN ATOMICITY ARGUMENT. The
// materializer renders every row in memory and appends them in ONE write
// (`materialize-seats.py:4453 append_taskforce_rows` → `:4484 _rewrite_in_place`), so a refusal on
// the last seat of seventeen leaves ZERO rows. N single-seat mints would have no such property and
// NO ROLLBACK VERB EXISTS to repair a half-minted chain — there is nothing to call. So the loop
// that would be natural here is forbidden.
//
// `--force-partial` IS PASSED DELIBERATELY, and it is the crash-between-mint-and-splice recovery
// (adv, C68). The materializer writes seat DESCRIPTORS first and the registry rows second (its own
// documented order, `:3800`), so an interrupted pass leaves folders with no rows. Re-firing plain
// would take the pinned `seat-exists` refusal FOREVER. `--force-partial` computes the DELTA inside
// the materializer — the rows this pass needs minus the rows already present — and appends only
// those, asserting every already-present row BYTE-MATCHES what this run would write
// (`partial-row-mismatch` otherwise). The delta arithmetic therefore lives with the naming, where
// it belongs; this file never subtracts one set of seat names from another.
function materializeArgv({ goalFolder, catalogRoot, sheet, milestone, mode, after }) {
  const argv = [MATERIALIZE_PY, '--package', goalFolder];
  // ⚠ THE COLLAPSED SHAPE IS THE ONE THE MATERIALIZER'S OWN REFUSAL NAMES, and it is being built
  // on the python side as this lands. Measured 2026-08-14 against the live script: a single-seat
  // `--nested` refuses `nested-without-workflow` with the message "Pass the workflow: --seat <seat>
  // --nested <workflow>" — so `--nested` takes a VALUE on this path while remaining a bare flag on
  // the `--workflow` path. If that lands as a bare flag instead, delete the `PLANNING_WORKFLOW`
  // token on the next line; nothing else changes.
  if (mode === 'collapsed') argv.push('--seat', COLLAPSED_SEAT, '--nested', PLANNING_WORKFLOW);
  else argv.push('--workflow', PLANNING_WORKFLOW, '--nested');
  argv.push('--catalog-root', catalogRoot);
  if (after.length) argv.push('--after', after.join(','));
  else argv.push('--root');
  argv.push('--bindings', sheet, '--milestone-id', milestone, '--force-partial', '--json');
  return argv;
}

// ── THE UNBUILT SEAT: A REGISTERED ROW WITH NO `seats/<seat>/` FOLDER (adv, C71 / D5 defect 1) ─
//
// Called from `runLaneWatch` — see the branch there for WHY it lives in that loop. These two
// helpers live HERE because they are the same act as the pass above (materialize into a LIVE
// goal), and a second copy of the invocation is a second set of flags to keep in step.
//
// WHICH SHEET CASTS AN ARBITRARY SEAT. `.rbtv/config/modules/<module>/<component>/bindings/
// <code>.json`, where the CODE is the workflow's seat-id prefix and IS the file's name — the
// convention the sheets themselves state (`plan.json` § `_code`: "the seat-id prefix every
// manifest row carries — and it is this file's name. Derived from the manifest, never typed").
// So the sheet is found by the seat's own first segment, and the module it sits under gives the
// catalog root. Anything but EXACTLY ONE hit refuses: two components sharing a code, or none, is
// a question with no honest guess.
function readdirSafe(dir) {
  try { return fs.readdirSync(dir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name); } catch { return []; }
}

// ⚠ THE WORKFLOW SHEET IS NOT THE ONLY SPELLING, AND TWO SEAT CLASSES LIVE OUTSIDE IT.
//   · A seat belonging to NO workflow — meta/planning's eval pool (`plan-dod-judge`,
//     `plan-unblock-checker`), a staff chair — is DELIBERATELY absent from its component's
//     workflow sheet (`check_bindings_cover` refuses it there as `bindings-extra-seat`) and
//     carries its OWN sheet at `bindings/<seat>.json`: the standing-seat spelling
//     (`materialize-seats.py#staff_sheet_path`), owner-ruled 2026-08-15 in the sheets themselves.
//   · An INSTANCE-NAMED seat (`plan-6-plan-dod-judge`) is a composed DISK name whose sheet entry
//     is keyed by its BASE seat — a composed name is never a catalog or bindings key
//     (`materialize-seats.py` § the two-name model).
// So the candidates are tried MOST SPECIFIC FIRST — the seat's own sheet, then its base seat's,
// then the workflow code's — and the "exactly one hit or refuse" discipline holds WITHIN each
// candidate: a class that resolves 2 sheets is still a question with no honest guess. Trying them
// in one flat set instead would make `plan-dod-judge.json` + `plan.json` read as ambiguity when
// one of them is simply more specific than the other.
const INSTANCE_SEAT_RE = /^[a-z]{4}-[2-9][0-9]*-([a-z0-9][a-z0-9-]*)$/;

// The BASE seat of a composed instance name, or '' — the JS twin of
// `materialize-seats.py#parse_instance_seat_name`, narrowed to the shape that carries an EXPLICIT
// ordinal. The bare first-instance shape (`plan-researcher`) is indistinguishable from an ordinary
// seat id, so reading a base out of it would invent one for every seat in the tree.
function instanceBaseSeat(seat) {
  const m = INSTANCE_SEAT_RE.exec(String(seat || ''));
  return m ? m[1] : '';
}

function repoRootOf(workspace) {
  const book = path.join(workspace, 'rbtv.json');
  const parsed = JSON.parse(fs.readFileSync(book, 'utf8'));
  let root = String((parsed && parsed.rbtv_path) || '').trim();
  if (!path.isAbsolute(root)) root = path.resolve(workspace, root);
  return root;
}

function sheetForSeat(workspace, seat) {
  const code = String(seat || '').split('-')[0];
  const base = instanceBaseSeat(seat);
  const modulesRoot = path.join(workspace, '.rbtv', 'config', 'modules');
  const tried = [];
  let repoRoot = null;
  for (const name of [...new Set([seat, base, code].filter(Boolean))]) {
    const hits = [];
    for (const mod of readdirSafe(modulesRoot)) {
      for (const comp of readdirSafe(path.join(modulesRoot, mod))) {
        const sheet = path.join(modulesRoot, mod, comp, 'bindings', `${name}.json`);
        if (fs.existsSync(sheet)) {
          if (mod === PLANNING_MODULE && repoRoot === null) repoRoot = repoRootOf(workspace);
          const catalogRoot = (mod === PLANNING_MODULE)
            ? path.join(repoRoot, PLANNING_MODULE)
            : path.join(workspace, '.rbtv', 'mirror', mod);
          hits.push({ sheet, catalogRoot });
        }
      }
    }
    if (hits.length === 1) return hits[0];
    if (hits.length > 1) {
      throw new Refusal('unbuilt-seat-sheet-unresolvable',
        `seat '${seat}' resolves ${hits.length} casting sheets named ${name}.json under `
        + `${modulesRoot} — a seat is built from exactly one sheet and there is no honest guess: `
        + hits.map((h) => h.sheet).join(', '));
    }
    tried.push(`${name}.json`);
  }
  throw new Refusal('unbuilt-seat-sheet-unresolvable',
    `seat '${seat}' resolves NO casting sheet under ${modulesRoot} — tried ${tried.join(', ')}`);
}

// ⚠ `--force-partial` IS WHAT MAKES THIS LEGAL AT ALL. The row already exists, so a plain
// materialize takes the pinned `seat-exists` refusal. `--force-partial` completes the MISSING half
// of a partial materialize — here the descriptor — and asserts the row already on disk BYTE-MATCHES
// the row this run would write (`partial-row-mismatch` otherwise), so it can only ever ADD the
// folder that is missing. It never rewrites the registry row and never touches an edge.
function materializeUnbuiltSeatArgv({ goalFolder, seat, after, milestone, catalogRoot, sheet }) {
  const argv = [MATERIALIZE_PY, '--package', goalFolder, '--seat', seat,
    '--catalog-root', catalogRoot];
  if (after) argv.push('--after', after);
  else argv.push('--root');
  argv.push('--bindings', sheet);
  if (milestone) argv.push('--milestone-id', milestone);
  argv.push('--force-partial', '--json');
  return argv;
}

// ── THE GOAL-LOCAL LANE, FROM THE ENGINE SIDE (W7 R7, adv C75) ───────────────────────────────
//
// `sheetForSeat` above resolves a CATALOGED seat: the first segment of the name is a workflow code
// and the sheet is `bindings/<code>.json`. A GOAL-AUTHORED seat has no such code and no such sheet
// — `seam-toolsmith` yields code `seam`, nothing is named `seam.json`, and the honest refusal is
// `unbuilt-seat-sheet-unresolvable`. That refusal was CORRECT and it was also the whole D5 stall:
// the planning pass authored the seat inside the goal (`planning/current/seats/<seat>/`), the
// binder registered its row, and no lane could read the definition back.
//
// A seat is GOAL-LOCAL when the goal's own planning product holds its definition folder AND that
// folder is not a `source.md` pointer — a pointer means "this seat is CATALOGED, reuse it", which
// is the cataloged lane's job and must not be served here.
const GOAL_LOCAL_SOURCE = ['planning', 'current'];
const GOAL_LOCAL_REUSE = 'source.md';

function goalLocalSeatDir(goalFolder, seat) {
  const dir = path.join(goalFolder, ...GOAL_LOCAL_SOURCE, 'seats', seat);
  if (!fs.existsSync(dir)) return null;
  if (fs.existsSync(path.join(dir, GOAL_LOCAL_REUSE))) return null;   // cataloged reuse
  return dir;
}

// ⚠ THE LINT IS A REAL INVOCATION, NOT A SECOND IMPLEMENTATION (R7). The lane's dangling-ref and
// collision checks live in `materialize-seats.py --goal-local`, where the reading happens; running
// them from JS would be a second opinion about the goal's own product. `--dry-run` performs every
// one of them and appends nothing, so the lint IS the materializer, asked not to write. It is run
// BEFORE the build so a goal whose pass authored a broken seat set is reported ONCE, by code, with
// nothing half-built behind it — rather than N times, one per seat, as an opaque build failure.
// ⚠ THE CAST OF A GOAL-AUTHORED SEAT IS AN OPEN QUESTION, AND IT IS REFUSED RATHER THAN GUESSED.
// A cataloged seat's harness/model/effort come from its workflow's casting sheet. A goal-authored
// seat belongs to no workflow, so nothing casts it — and `#d-abolish-profile-names` ruled that an
// uncast seat is a NAMED REFUSAL at every door, never a default. The goal's `taskforce.csv` row
// does carry harness/model/effort (the binder wrote them), but a row is not a casting sheet: it
// carries no `agent_type`, no `mode`, no `cwd-mode`, and inventing those three here would be this
// engine deciding what kind of agent a planning pass authored. So: the pass must leave a sheet at
// `planning/current/bindings.json`, and until it does this refuses BY NAME. Surfaced to the owner
// rather than papered over — a wrong default here casts a live seat.
const GOAL_LOCAL_SHEET = 'bindings.json';

function buildGoalLocalSeats({ goalFolder, workspace, seats, rows = [], say }) {
  const catalogRoot = path.join(repoRootOf(workspace), PLANNING_MODULE);
  const sheet = path.join(goalFolder, ...GOAL_LOCAL_SOURCE, GOAL_LOCAL_SHEET);
  // ⚠ THE MILESTONE COMES OFF THE SEATS' OWN ROWS, exactly as the cataloged lane below reads it
  // (`:532`). It is not decoration: `--force-partial` byte-compares the row it WOULD write against
  // the one on disk, and the milestone is a column of that row — omit it and a goal-authored seat
  // registered under a milestone (every one of them: the pass that authors them runs FOR a
  // milestone) refuses `partial-row-mismatch` on a cell nobody meant to change. One run carries
  // one `--milestone-id`, so a set spanning two milestones is split by the caller, not guessed.
  const mByRow = new Map(rows.map((r) => [(r.seat || '').trim(), (r['milestone-id'] || '').trim()]));
  const milestones = [...new Set(seats.map((s) => mByRow.get(s) || ''))];
  if (milestones.length > 1) {
    say('warn', 'lane watch: this goal\'s authored seats span more than one milestone — one '
      + 'materialize carries one milestone-id, so the set is refused rather than split blind',
    { code: 'goal-local-milestone-split', milestones, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, code: 'goal-local-milestone-split' })) };
  }
  const milestone = milestones[0] || '';
  if (!fs.existsSync(sheet)) {
    say('warn', 'lane watch: this goal authored its own seats and left no casting sheet — they '
      + 'cannot be built, and their harness/model/effort is not the engine\'s to invent',
    { code: 'goal-local-sheet-absent', sheet, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, code: 'goal-local-sheet-absent' })) };
  }
  const lint = goalLocalLint({ goalFolder, catalogRoot, sheet, milestone });
  if (lint) {
    say('warn', 'lane watch: the goal\'s own authored seat set does not LINT — nothing was built, '
      + 'and it is one refusal for the whole set rather than one opaque failure per seat',
    { code: lint.code, evidence: lint.evidence, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, code: lint.code })) };
  }
  const argv = goalLocalArgv({ goalFolder, catalogRoot, sheet, milestone });
  try {
    execFileSync(requirePythonCmd(), argv,
      { encoding: 'utf8', timeout: SUBPROCESS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    say('info', 'lane watch: built the goal\'s OWN authored seats — definitions no component '
      + 'catalog carries, which is why nothing could build them before W7', { seats });
    return { built: seats, failed: [] };
  } catch (err) {
    const evidence = (String(err.stdout || '') + String(err.stderr || '')).trim().slice(0, 400);
    say('warn', 'lane watch: materializing the goal\'s own authored seats REFUSED — the goal '
      + 'stalls at them until it is cleared', { evidence, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, error: evidence })) };
  }
}

// ⚠ ONE ARGV, TWO CALLERS — and that is the whole point of the lint (R7). The lint is the BUILD
// asked not to write, so it must differ from it in `--dry-run` AND NOTHING ELSE. It did differ:
// the lint omitted `--force-partial`, so on a goal whose seats already carry registry rows (the
// flagship's `seam-author`/`seam-toolsmith`, hand-built 2026-08-13) the lint took the pinned
// `seat-exists` refusal that `--force-partial` exists to lift, and reported the whole set unbuilt
// on a refusal the build would never have hit. Two argv literals is how that happened; one is how
// it stops happening.
function goalLocalArgv({ goalFolder, catalogRoot, sheet, milestone, dryRun = false }) {
  const argv = [MATERIALIZE_PY, '--package', goalFolder, '--workflow', 'goal-local',
    '--goal-local', '--catalog-root', catalogRoot, '--root', '--bindings', sheet];
  if (milestone) argv.push('--milestone-id', milestone);
  argv.push('--force-partial', '--json');
  if (dryRun) argv.push('--dry-run');
  return argv;
}

function goalLocalLint({ goalFolder, catalogRoot, sheet, milestone }) {
  const argv = goalLocalArgv({ goalFolder, catalogRoot, sheet, milestone, dryRun: true });
  try {
    execFileSync(requirePythonCmd(), argv,
      { encoding: 'utf8', timeout: SUBPROCESS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    return null;
  } catch (err) {
    const out = String(err.stdout || '') + String(err.stderr || '');
    let code = '';
    try { code = ((JSON.parse(out.slice(out.indexOf('{'))).refusal) || {}).code || ''; } catch { /* prose only */ }
    return { code: code || 'goal-local-lint-failed', evidence: out.trim().slice(0, 400) };
  }
}

// ── CIRCUIT NOTE (D16, dag-hardening) — a refusal that repeats every ~10s cadence for the SAME
// set of seats, for the SAME reason, is said once at `warn` and thereafter at `debug`. The
// measured shape (LE-13, `unbuilt-seats`): N seats refusing every cadence for a day is N × 8,640
// identical lines, and the refusal itself is unchanged either way — only the LOG LEVEL moves. Keyed
// on the goal folder, deliberately its OWN Map and never `lane-watch.js`'s `failedOn` (keyed on the
// lane MARKER, not this refusal set — sharing it would let one silence the other). A goal that
// starts failing on a DIFFERENT seat set, a different code, or that stops failing entirely is loud
// again the very next pass. ponytail: process-lifetime, re-armed by a daemon restart.
const unbuiltRefusalMemo = new Map();  // goalFolder -> last-shouted signature

// Build every registered-but-unbuilt seat of one goal. Returns `{built, failed}`; NEVER throws —
// the caller is a watch pass over the whole tree.
function buildUnbuiltSeats({ goalFolder, goalsRoot, rows, unbuilt, say = () => {} }) {
  const built = [];
  const failed = [];
  const toLog = [];   // buffered per-seat refusals — the level is decided once the full SET is known
  const workspace = path.resolve(goalsRoot, '..', '..');
  // The goal-local half runs ONCE for the whole goal, not once per seat: the lane is the goal's
  // manifest, and one materialize of it builds every goal-authored seat in one atomic append.
  const local = unbuilt.filter((s) => goalLocalSeatDir(goalFolder, s));
  if (local.length) {
    const outcome = buildGoalLocalSeats({ goalFolder, workspace, seats: local, rows, say });
    built.push(...outcome.built);
    failed.push(...outcome.failed);
  }
  unbuilt = unbuilt.filter((s) => !local.includes(s));   // the cataloged remainder
  const bySeat = new Map(rows.map((r) => [(r.seat || '').trim(), r]));
  for (const seat of unbuilt) {
    const row = bySeat.get(seat) || {};
    let where;
    try { where = sheetForSeat(workspace, seat); } catch (err) {
      failed.push({ seat, code: err.code, error: err.message });
      toLog.push(['lane watch: a taskforce row has NO seat folder and its casting sheet could not '
        + 'be resolved — the seat cannot be built and this goal cannot advance past it',
      { seat, code: err.code, error: err.message }]);
      continue;
    }
    // ⚠ A SCOPED, ONE-SEAT SHEET, written OUTSIDE the goal folder — the same act
    // `goal_cli.py#cmd_add_seat` performs for the same reason: the materializer refuses
    // `bindings-extra-seat` for any sheet naming a seat outside the set being materialized, and
    // the component's shared sheet names every seat of the workflow. Outside the goal on purpose:
    // a temp file inside it would be a stray artifact under the tree this is repairing, and a
    // crash would leave it there.
    let scoped = null;
    try {
      const full = JSON.parse(fs.readFileSync(where.sheet, 'utf8'));
      // Keyed by the seat, else by its BASE seat when the name is a composed instance name — a
      // sheet is keyed by CATALOG ids and a composed name is never one, so the base is where a
      // nested instance's cast actually lives. The key that FOUND it is the key the scoped sheet
      // is written under: the materializer accepts either and re-keys the base itself, so the one
      // it is handed is the one it was found under, never a translated third spelling.
      const key = ((full && full.seats) || {})[seat] ? seat : instanceBaseSeat(seat);
      const entry = ((full && full.seats) || {})[key];
      if (!entry) {
        throw new Refusal('unbuilt-seat-not-in-sheet',
          `${where.sheet}: carries no entry for seat '${seat}' — a missing binding is a refusal, `
          + 'never a default');
      }
      scoped = path.join(require('node:os').tmpdir(),
        `rbtv-unbuilt-${seat}-${process.pid}-${Date.now()}.json`);
      fs.writeFileSync(scoped, JSON.stringify({ defaults: full.defaults || {}, seats: { [key]: entry } }));
      execFileSync(requirePythonCmd(), materializeUnbuiltSeatArgv({
        goalFolder, seat, after: (row.after || '').trim(), milestone: (row['milestone-id'] || '').trim(),
        catalogRoot: where.catalogRoot, sheet: scoped,
      }), { encoding: 'utf8', timeout: SUBPROCESS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
      built.push(seat);
    } catch (err) {
      const evidence = (String(err.stdout || '') + String(err.stderr || '')).trim().slice(0, 400);
      failed.push({ seat, code: err.code, error: evidence || err.message });
      toLog.push(['lane watch: a taskforce row has NO seat folder and MATERIALIZING it refused — '
        + 'the goal stalls at this seat until it is built', { seat, evidence: evidence || err.message }]);
    } finally {
      if (scoped) fs.rmSync(scoped, { force: true });
    }
  }
  // The refusal set's SIGNATURE — seat + code/evidence, sorted so seat ORDER is not a state change.
  // Unchanged from the last pass ⇒ every buffered line above drops to `debug`; changed (a different
  // seat, a different reason, or empty because everything built) ⇒ loud, and the memo re-arms.
  const sig = failed.map((f) => `${f.seat}:${f.code || f.error || ''}`).sort().join('|');
  const alreadyShouted = sig !== '' && unbuiltRefusalMemo.get(goalFolder) === sig;
  if (sig) unbuiltRefusalMemo.set(goalFolder, sig); else unbuiltRefusalMemo.delete(goalFolder);
  for (const [message, extra] of toLog) say(alreadyShouted ? 'debug' : 'warn', message, extra);
  if (built.length) {
    say('info', 'lane watch: built registered-but-unbuilt seat(s) — the rows existed and their '
      + 'folders did not, which is the state nothing else in this system repairs', { seats: built });
  }
  return { built, failed };
}

// ── ONE PASS OVER THE GOALS TREE ─────────────────────────────────────────────────────────────
//
// Runs as a SIBLING of `laneWatchPass` in the daemon's loop, immediately BEFORE it, so a row this
// pass mints is seeded by the lane watch of the same cadence and dispatched by the tick that
// follows — rather than a cadence later. It does not seed anything itself: `engine.seedGoal` has
// ONE caller and it is the lane watch (PRIN-11). `engine` is accepted for call-shape parity with
// `runLaneWatch` and is deliberately unused.
//
// NOTHING HERE IS FATAL — the same rule the lane watch runs under. One goal's unreadable registry,
// refusing materializer or malformed request is logged and skipped; every other goal is served
// from the same pass, and the next cadence retries.
//
// ⚠ AT MOST ONE MINT PER GOAL PER PASS. After a mint the registry has changed, and every
// consumption count computed from the pre-mint snapshot is stale; re-reading and re-deriving
// inside the loop would be a second arithmetic that can disagree with the first. The next cadence
// (10 s) takes the next request. A wave boundary is not a latency-sensitive event.
function runQueueRequestPass({ goalsRoot, engine = null, logger = null }) {   // eslint-disable-line no-unused-vars
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  const seeded = [];
  const skipped = [];

  let catalog;
  let entries;
  try {
    entries = fs.readdirSync(goalsRoot, { withFileTypes: true });
  } catch {
    return { seeded, skipped };            // no goals tree on this workspace — not an error
  }
  try {
    catalog = resolveCatalogRoot(goalsRoot);
  } catch (err) {
    // Workspace-wide and unchanging: said once per pass, at debug, because a workspace with no
    // mirror is the ordinary state of every workspace that has never planned anything.
    skipped.push({ reason: err.code || 'catalog-unresolvable', error: err.message });
    say('debug', 'queue-request pass: no component catalog on this workspace — nothing consumed',
      { code: err.code, error: err.message });
    return { seeded, skipped };
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const goal = entry.name;
    const goalFolder = path.join(goalsRoot, goal);

    // GATE: the lane. Read through `lane-watch`'s own readers so this pass and the seeder can
    // never disagree about who owns a goal. `laneIsPaused` is asked SEPARATELY because `readLane`
    // deliberately flattens `paused …` into `console` — an operator's explicit pause is a state
    // this pass must honour as a pause, not merely as "not mine".
    if (laneIsPaused(goalFolder)) { skipped.push({ goal, reason: 'goal-paused' }); continue; }
    if (readLane(goalFolder).lane !== DAEMON) {
      skipped.push({ goal, reason: 'not-assigned-to-the-daemon' });
      continue;
    }
    // GATE (d) — KEPT. See the table above.
    if (consoleRunIsLive(goalFolder)) {
      skipped.push({ goal, reason: 'console-run-live' });
      say('info', 'queue-request pass: a console run is LIVE on this goal — not splicing against it',
        { goal });
      continue;
    }

    let rows;
    try { rows = readTaskforce(goalFolder); } catch {
      skipped.push({ goal, reason: 'no-taskforce-yet' });     // not materialized: normal, quiet
      continue;
    }

    const { rows: requests, reason } = queueRequests(goalFolder);
    if (requests === null) {
      skipped.push({ goal, reason: 'queue-requests-refused', evidence: reason });
      say('warn', 'queue-request pass: could not read this goal\'s queue-requests — NOTHING was '
        + 'spliced, and a wave that is waiting on one is still waiting', { goal, evidence: reason });
      continue;
    }
    if (!requests.length) { skipped.push({ goal, reason: 'no-queue-requests' }); continue; }

    // Per-milestone log-order index, so request i of milestone M can be compared against how many
    // passes M already carries.
    const seen = new Map();
    let minted = false;
    for (const req of requests) {
      if (minted) break;
      if (!req || req.key === null || req.key === undefined) {
        // ⚠ NEVER SILENTLY DROPPED. coord LISTS a row whose first body line is not
        // `queue-request: <milestone>/<verdict>/<pass-kind>` precisely so the consumer can refuse
        // it loudly; a request that vanishes from the listing AND from the log is a wave that
        // stalls with nothing anywhere saying why.
        skipped.push({ goal, reason: 'queue-request-malformed-key', num: req && req.num });
        say('warn', 'queue-request pass: a `queue-request` row carries NO parseable key line '
          + '(`queue-request: <milestone-id>/<verdict-id>/<pass-kind>` must be its first body '
          + 'line) — it is REFUSED, not consumed, and whatever wave it was asking for has NOT '
          + 'been queued', { goal, num: req && req.num, sender: req && req.sender });
        continue;
      }
      // THE MILESTONE. coord's `milestone:` HEADER KEY is authoritative (`concepts/body-sigil.md`
      // § Why a header key beats a body convention) and is taken whenever it is there. The key
      // line's FIRST FIELD is the documented round-trip copy of the same value ("the body's first
      // field is the same value and is kept only so the key string round-trips",
      // `coord.py#queue_request_rows`), and is the fallback — because `coordinate send` carries no
      // `--milestone` flag today, so every request written through it lands with a null header key
      // and refusing on that would make the consumer inert against its only writer. The fallback is
      // said out loud at debug so a divergence is never silent.
      let milestone = String(req.milestone || '').trim();
      if (!milestone && req.key) {
        milestone = String(req.key).split('/')[0].trim();
        if (milestone) {
          say('debug', 'queue-request pass: no `milestone:` header key on this row — using the key '
            + 'line\'s own first field, which coord documents as the same value', { goal, num: req.num, milestone });
        }
      }
      if (!milestone) {
        skipped.push({ goal, reason: 'queue-request-no-milestone', num: req.num });
        say('warn', 'queue-request pass: a `queue-request` row carries no `milestone:` header key '
          + '— REFUSED; there is no milestone to plan', { goal, num: req.num, sender: req.sender });
        continue;
      }
      const idx = seen.get(milestone) || 0;
      seen.set(milestone, idx + 1);
      if (idx < passesMinted(rows, milestone)) {
        // CONSUMED. Quiet by construction: this is the steady state of every request ever drained,
        // re-derived every cadence forever.
        skipped.push({ goal, reason: 'queue-request-consumed', num: req.num, milestone });
        say('debug', 'queue-request pass: request already consumed', { goal, num: req.num, milestone, key: req.key });
        continue;
      }

      // ── EVERY REFUSAL COMPUTABLE BEFORE THE WRITE, FIRED BEFORE THE WRITE (gate (g)) ──────
      let mode;
      let uncast;
      try {
        mode = planningMode(goalFolder, milestone);
        uncast = uncastInSheet(catalog.sheet, mode === 'collapsed' ? COLLAPSED_SEAT : null);
      } catch (err) {
        skipped.push({ goal, reason: err.code || 'queue-request-refused', num: req.num, milestone, error: err.message });
        say('warn', 'queue-request pass: REFUSED before writing anything', {
          goal, num: req.num, milestone, code: err.code, error: err.message,
        });
        continue;
      }
      if (uncast.length) {
        skipped.push({ goal, reason: 'queue-request-would-land-uncast', num: req.num, milestone, seats: uncast });
        say('warn', 'queue-request pass: this pass would splice seat(s) with NO cast — NOTHING was '
          + 'written. An uncast row does not merely fail to launch: `runLaneWatch` skips the goal '
          + 'WHOLESALE on one uncast seat, and quietly after the first cadence, so splicing it '
          + 'would freeze the ENTIRE goal.', {
            goal, num: req.num, milestone, seats: uncast, sheet: catalog.sheet,
            fix: `rbtv-bindings set ${catalog.sheet} <seat> <harness> <model> [effort]`,
          });
        continue;
      }

      // The attach point: the SENDER's row, when the sender is a seat of this goal. That keeps the
      // causal edge — "this pass exists because that checker judged the milestone" — in the one
      // place readiness is computed from, the DAG. A sender with no row (the request came from
      // outside this taskforce) attaches at the root, which is honest: the request IS the
      // readiness statement, so an empty `after` is ready now.
      const sender = String(req.sender || '').trim();
      const after = rows.some((r) => (r.seat || '').trim() === sender) ? [sender] : [];

      const argv = materializeArgv({
        goalFolder, catalogRoot: catalog.catalogRoot, sheet: catalog.sheet, milestone, mode, after,
      });
      let out;
      try {
        out = execFileSync(requirePythonCmd(), argv,
          { encoding: 'utf8', timeout: SUBPROCESS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
      } catch (err) {
        // A refusing materializer is a per-goal fact, never a pass-wide one: log the code and
        // CONTINUE to the next goal. Nothing was written — every refusal in that script fires
        // before the atomic replace or leaves it untouched.
        const evidence = String(err.stdout || '') + String(err.stderr || '');
        let code = null;
        try { code = (JSON.parse(String(err.stdout || '')).refusal || {}).code || null; } catch { /* text refusal */ }
        skipped.push({ goal, reason: 'materialize-refused', num: req.num, milestone, code, evidence: evidence.trim().slice(0, 400) });
        say('warn', 'queue-request pass: the planning pass MINT refused — nothing was spliced and '
          + 'the wave is still waiting', {
            goal, num: req.num, milestone, mode, code, evidence: evidence.trim().slice(0, 600),
          });
        break;                       // this goal is done for this cadence
      }
      let result = null;
      try { result = JSON.parse(out); } catch { /* --json should always parse; absence is reported below */ }
      minted = true;
      seeded.push({
        goal, num: req.num, key: req.key, milestone, mode,
        seats: (result && result.added_seats) || [],
        // The materializer's own count of rows it appended — the one number that says the whole
        // chain landed rather than a fraction of it. (It publishes no `taskforce_id` on the result;
        // the instance's id is read off the appended rows, which is where consumption reads it.)
        rows: (result && result.taskforce_rows_appended) || 0,
      });
      say('info', 'queue-request pass: a planning pass was spliced for a newly unblocked milestone', {
        goal, num: req.num, key: req.key, milestone, mode, after,
        seats: (result && result.added_seats) || [],
      });
    }
  }

  return { seeded, skipped };
}

module.exports = {
  PLANNING_MODULE, PLANNING_COMPONENT, PLANNING_WORKFLOW, PLANNING_CODE, COLLAPSED_SEAT,
  MATERIALIZE_PY, SUBPROCESS_TIMEOUT_MS, NESTED_TF_RE,
  Refusal, resolveCatalogRoot, queueRequests, passesMinted, planningMode, uncastInSheet,
  materializeArgv, runQueueRequestPass,
  sheetForSeat, materializeUnbuiltSeatArgv, buildUnbuiltSeats,
  goalLocalSeatDir, goalLocalLint, goalLocalArgv, buildGoalLocalSeats,
  GOAL_LOCAL_SOURCE, GOAL_LOCAL_REUSE, GOAL_LOCAL_SHEET,
};

// Self-check: the two pure derivations this file OWNS — the consumption count and the argv shape.
// Everything else in here is a subprocess or a borrowed reader and is proven by
// `probes/probe-queue-request-pass.js`.
if (require.main === module) {
  const assert = require('node:assert');
  const rows = [
    { 'taskforce-id': 'tf-1', seat: 'plan-binder', 'milestone-id': '' },
    { 'taskforce-id': 'tf-2-plan1', seat: 'plan-2-plan-planner', 'milestone-id': 'm2' },
    { 'taskforce-id': 'tf-2-plan1', seat: 'plan-2-plan-binder', 'milestone-id': 'm2' },
    { 'taskforce-id': 'tf-3-plan2', seat: 'plan-3-plan-planner', 'milestone-id': 'm2' },
    { 'taskforce-id': 'tf-4-plan3', seat: 'plan-4-plan-planner', 'milestone-id': 'm3' },
  ];
  assert.strictEqual(passesMinted(rows, 'm2'), 2, 'two distinct nested taskforce-ids on m2');
  assert.strictEqual(passesMinted(rows, 'm3'), 1);
  assert.strictEqual(passesMinted(rows, 'm9'), 0);
  assert.strictEqual(passesMinted([{ 'taskforce-id': 'tf-1', 'milestone-id': 'm2' }], 'm2'), 0,
    'a BARE taskforce-id is the goal-level pass, never a nested one');
  const full = materializeArgv({
    goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json', milestone: 'm2', mode: 'full', after: ['x'],
  });
  assert(full.includes('--workflow') && full.includes('planning') && full.includes('--nested'));
  assert.deepStrictEqual(full.slice(full.indexOf('--after'), full.indexOf('--after') + 2), ['--after', 'x']);
  assert(full.includes('--force-partial') && full.includes('--json'));
  const collapsed = materializeArgv({
    goalFolder: '/g', catalogRoot: '/c', sheet: '/s.json', milestone: 'm2', mode: 'collapsed', after: [],
  });
  assert(collapsed.includes('--seat') && collapsed.includes(COLLAPSED_SEAT));
  assert(!collapsed.includes('--workflow') && collapsed.includes('--root'));
  // The goal-local DISCRIMINATOR — the one pure derivation the engine half owns. A definition
  // folder makes a seat goal-local; a `source.md` pointer inside it makes it CATALOGED again, and
  // getting that backwards would have the lane shadow every reused cataloged seat with a copy.
  const os = require('node:os');
  const gl = fs.mkdtempSync(path.join(os.tmpdir(), 'qr-gl-'));
  const mk = (seat, reuse) => {
    const d = path.join(gl, ...GOAL_LOCAL_SOURCE, 'seats', seat);
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, reuse ? GOAL_LOCAL_REUSE : 'prompt.md'), 'x');
  };
  mk('authored', false);
  mk('reused', true);
  assert(goalLocalSeatDir(gl, 'authored'), 'an authored definition folder IS the goal-local lane');
  assert.strictEqual(goalLocalSeatDir(gl, 'reused'), null,
    'a source.md pointer is a CATALOGED seat — the goal-local lane must not shadow it with a copy');
  assert.strictEqual(goalLocalSeatDir(gl, 'absent'), null, 'no folder, no lane');
  fs.rmSync(gl, { recursive: true, force: true });
  console.log('queue-request selftest OK');
}
