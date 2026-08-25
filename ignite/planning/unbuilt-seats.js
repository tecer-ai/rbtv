'use strict';

// Unbuilt-seat repair + goal-local lane (D5). Not the planning-door mint.
// Extracted from queue-request.js so that file is no longer a splice-door monolith.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { requirePythonCmd } = require('../runtime/python-cmd');

const MATERIALIZE_PY = path.join(__dirname, '..', 'team-kit', 'materialize-seats.py');
const SUBPROCESS_TIMEOUT_MS = 120000;
const PLANNING_MODULE = 'meta';

class Refusal extends Error {
  constructor(code, message) { super(message); this.code = code; }
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
    return { built: [], failed: seats.map((seat) => ({ seat, code: 'goal-local-milestone-split',
      error: `the authored set spans milestones ${milestones.map((x) => x || '(none)').join(', ')} and one materialize carries one milestone-id` })) };
  }
  const milestone = milestones[0] || '';
  if (!fs.existsSync(sheet)) {
    say('warn', 'lane watch: this goal authored its own seats and left no casting sheet — they '
      + 'cannot be built, and their harness/model/effort is not the engine\'s to invent',
    { code: 'goal-local-sheet-absent', sheet, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, code: 'goal-local-sheet-absent',
      error: `no casting sheet at ${sheet} — harness/model/effort is not the engine's to invent` })) };
  }
  const lint = goalLocalLint({ goalFolder, catalogRoot, sheet, milestone });
  if (lint) {
    say('warn', 'lane watch: the goal\'s own authored seat set does not LINT — nothing was built, '
      + 'and it is one refusal for the whole set rather than one opaque failure per seat',
    { code: lint.code, evidence: lint.evidence, seats });
    return { built: [], failed: seats.map((seat) => ({ seat, code: lint.code, error: lint.reason })) };
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
    return { built: [], failed: seats.map((seat) => ({ seat, code: 'goal-local-materialize-refused', error: evidence })) };
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
    // ⚠ PARSE STDOUT ALONE. `goalLocalArgv` passes `--json`, and that flag's whole purpose is a
    // machine-readable payload on STDOUT; the tool's prose refusal goes to STDERR. This block used
    // to parse `stdout + stderr`, which is JSON followed by prose and therefore NEVER valid JSON —
    // so the parse always threw, `code` was always the `goal-local-lint-failed` fallback, and the
    // refusal's own `message` was never recovered at all. Combined with `lane-watch.js` rendering
    // the alarm from a field this arm did not set, a frozen goal told its owner only the word
    // "undefined": meet-transcript-summarizer sat frozen ~13h behind an alarm that named no cause.
    const payload = String(err.stdout || '');
    const evidence = (payload + String(err.stderr || '')).trim().slice(0, 400);
    let code = '';
    let reason = '';
    try {
      const refusal = (JSON.parse(payload.slice(payload.indexOf('{'))).refusal) || {};
      code = refusal.code || '';
      reason = refusal.message || '';
    } catch { /* prose only — `evidence` still carries whatever the tool said */ }
    return { code: code || 'goal-local-lint-failed', reason: reason || evidence, evidence };
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
// ⚠ EVERY `failed` ENTRY IS `{ seat, code, error }` AND ALL THREE ARE ALWAYS SET. `code` is the
// machine-readable refusal id (it keys `unbuiltRefusalMemo`'s signature); `error` is the
// human-readable reason, and it is what `lane-watch.js` renders into the OWNER'S FROZEN ALARM. This
// shape is declared here because it was previously undeclared: six producers emitted three
// different shapes, the goal-local lint arm set `code` only, and the alarm — which reads `error` —
// posted the literal word "undefined" as the reason a goal was frozen. meet-transcript-summarizer
// sat frozen for ~13 hours behind an alarm that named no cause. A producer that cannot name a real
// reason has not finished diagnosing its own refusal; do not paper over it at the consumer.
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

module.exports = {
  Refusal,
  sheetForSeat, materializeUnbuiltSeatArgv, buildUnbuiltSeats,
  goalLocalSeatDir, goalLocalLint, goalLocalArgv, buildGoalLocalSeats,
  GOAL_LOCAL_SOURCE, GOAL_LOCAL_REUSE, GOAL_LOCAL_SHEET,
  instanceBaseSeat, repoRootOf,
};
