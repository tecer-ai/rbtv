'use strict';

// engine/seeding.js — SEEDING A GOAL'S TASKFORCE, for whichever lane is doing it.
//
// This is the code that used to live inside `attached-execution.js`, unchanged in behaviour and
// moved for ONE reason: it was never attached-lane machinery. It reads `taskforce.csv`, registers
// one job per seat, and enqueues the seats whose turn it is — none of which is a property of the
// terminal the run is attached to. It lived there because the attached lane was its only caller,
// and that accident is exactly what the B3 probe measured as "the daemon lane has no path that
// seeds a goal's taskforce into its own store" (owner ruling
// decisions.md#d-s23-single-execution-record-now, criterion 2).
//
// ⚠⚠ THIS FILE NO LONGER COMPUTES READINESS (owner-ruled 2026-08-11,
// `build/one-readiness-predicate.md` § D1). There were THREE implementations of "is this seat ready
// to launch" — coord.py's, the edge-runner's and this one — they drifted, and the drift is what
// stalled the live goal. The split is now TOTAL and there is no third term:
//
//   coord answers the DAG      has this seat checked out, with what disposition; are its `after`
//                              members satisfied; do its guards discharge. ONE home, ONE grammar.
//                              Reached ONCE PER GOAL PER PASS through `readySeats` below.
//   seeding answers the store  has THIS store already registered, queued or fired this seat. It is
//                              purely a no-double-fire guard: it can only ever DECLINE to enqueue,
//                              never promote a seat to ready on its own.
//
// THE CONSEQUENCES ARE DELIBERATE AND ARE NOT TO BE WORKED AROUND. A seat whose session ended with
// no check-out is `UNDECLARED` to coord — not READY and not DONE — so the goal STALLS there, loudly,
// with the seat named. An exit code is not a check-out: "`done` is the seat reporting its own work
// finished, which no exit code can assert" (coord.py's own words, and the defect this closes — the
// ticker's clean-exit sweep advanced a seat that did nothing).
//
// TWO THINGS ARE NEW HERE, and both exist because a SECOND store may now do this:
//
//  1. THE COMPLETION AUTHORITY IS THE GOAL'S EXECUTION RECORD (`execution-record.js`), not the
//     store. `seatState` answers `done` from `<goal>/executions.csv` FIRST, and only then from the
//     rows the caller's own store carries. The store half stays because it is the local
//     no-double-fire guard create-only seeding has always been — it can only ADD done-ness, so the
//     union can never cause a double run, only decline to re-run something a lane already ran.
//
//  2. THE JOB-ID NAMESPACE. `seat-<name>` is unique inside a per-goal store and is NOT unique
//     inside the daemon's single store, which holds every goal it serves — two goals with a seat
//     named `alpha` would collide there and silently share one job row. So a caller whose store is
//     shared passes `goal`, and the id becomes `seat-<goal>-<name>`. The attached lane passes
//     nothing and its ids are byte-identical to what it has always written, so every goal already
//     on disk resumes exactly as before. Cross-lane identity does NOT ride on this id — it rides on
//     the seat name in the shared record, which is the whole reason that record exists.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { readExecutionRecord, finishedSeats, DONE, BLOCKED } = require('./execution-record');
// The ONE interpreter resolver this repo already has (`python3` is a Microsoft-Store LIE on
// Windows — it is on PATH, is executable, and runs no python).
const { requirePythonCmd } = require('../lib/python-cmd');
const { admitDeclaredOutputs } = require('./cage-admission');
// THE RELAUNCH GRANT'S ONE HOME — a file in the goal folder, read HERE rather than threaded in by
// each caller. See `relaunch-grants.js`'s header for why the parameter was the defect: the daemon
// lane's only call (`lane-watch.js#runLaneWatch` -> `seedGoal`) passes no relaunch key and never
// will, so a grant sourced at the caller is a grant one lane can never receive.
const { readGrants, spendGrant } = require('./relaunch-grants');
// The ONE quote-aware row splitter this module already has (`execution-record.js` reads the goal's
// record with it). Reusing it is the whole CSV fix — see below.
const { splitRow } = require('../server/seat-identity/csv');

const TASKFORCE = 'taskforce.csv';

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// Header-driven CSV read. The cell split is `splitRow` — RFC-4180 quoting (a double-quoted field
// with embedded commas, `""` for a literal quote) — and NOT the plain `line.split(',')` this
// replaces.
//
// ⚠ THE DEFECT THE PLAIN SPLIT WAS. `taskforce.csv` is NOT written by hand: the writer is
// `team-kit/materialize-seats.py#_render_csv_line`, which is `csv.writer` (QUOTE_MINIMAL) — so a
// MULTI-PREDECESSOR `after` cell is written QUOTED, because it carries commas. Split naively, that
// one cell became several and EVERY COLUMN TO ITS RIGHT SHIFTED: `harness`, `model`, `effort` and
// `milestone-id` were read off the wrong fields, and the `after` the wave math saw was the first
// predecessor only. A six-predecessor row (the planning workflow's check-assembler) shifted five
// columns. No dependency is bought for this: the splitter already existed one folder over.
//
// ponytail: line-oriented, so a field containing an EMBEDDED NEWLINE would still break. The writer
// cannot produce one (a seat name, a guard and a milestone id have no newlines) and the previous
// reader had the same ceiling; upgrade to a full streaming parse the day a cell can carry one.
function readCsv(file) {
  const text = fs.readFileSync(file, 'utf8');
  const lines = text.split('\n').filter((l) => l.trim().length);
  if (!lines.length) return [];
  const cols = splitRow(lines[0]).map((c) => c.trim());
  return lines.slice(1).map((line) => {
    const cells = splitRow(line);
    const row = {};
    cols.forEach((c, i) => { row[c] = (cells[i] === undefined ? '' : cells[i]).trim(); });
    return row;
  });
}

// ── THE READINESS ANSWER — coord's, consumed here, computed nowhere (§ D1) ────────────────────
//
// ONE subprocess per goal per pass:
//
//   python3 <ignite>/team-kit/coord.py --package <goal-folder> ready-seats --json
//
// ⚠ THE INTERPRETER AND THE SCRIPT ARE BOTH NAMED, NEVER RESOLVED ON PATH. A daemon-fired exec
// inherits the systemd --user manager's PATH, which does NOT carry `~/.local/bin`, so `coordinate`
// as a bare name resolves interactively and NOT here — the same fact every daemon-fired entry in
// `config/spawn-profiles.yaml` and `workflow_launcher.py#launch_argv` states. The repo file is the
// address; `requirePythonCmd` is the one interpreter resolver (task 7.700).
//
// ⚠ A NON-ZERO EXIT SEEDS NOTHING FOR THIS GOAL THIS PASS. `ready-seats` exits 1 on SKEW (the
// durable and live surfaces disagree about one seat) and that is the one outcome a consumer must
// not be able to sweep past. Every other failure — no python, an unreadable package, a timeout,
// output that is not the documented array — lands in the same place, for the same reason: a
// refused computation may never be PARTIALLY seeded off. `null` is the refusal; it is never an
// empty ready set, because "nothing is ready" and "I could not ask" are different claims.
//
// ponytail: one python invocation per daemon-assigned goal per cadence. At the current scale that
// is noise; if it stops being noise, batch the VERB (`ready-seats` over N packages) — never
// reintroduce a JS reader.
const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
const COORD_TIMEOUT_MS = 60000;

function readySeats(goalFolder) {
  const refuse = (reason) => ({ ready: null, rows: [], reason });
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'ready-seats', '--json'], {
      encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err) {
    return refuse(`\`ready-seats --json\` did not answer (${err.code || err.message})`
      + `${err.status === 1 ? ' — exit 1 is SKEW: the durable and live surfaces disagree about a seat, and coord refuses to pick a winner' : ''}`
      + `${err.stderr ? `: ${String(err.stderr).trim().slice(0, 400)}` : ''}`);
  }
  let rows;
  try { rows = JSON.parse(raw); } catch { return refuse(`\`ready-seats --json\` returned no JSON: ${String(raw).slice(0, 200)}`); }
  if (!Array.isArray(rows)) return refuse('`ready-seats --json` returned no row array');
  // seat -> its predecessors' declared outputs, resolved absolute (§ D4, coord's own resolution).
  // ⚠ AN ABSENT `seed` FIELD IS `[]` AND IS NEVER GUESSED AT HERE: resolving a predecessor's
  // declared outputs in JS would be the second reader this whole design deletes.
  const ready = new Map();
  // seat -> its UNSPENT relaunch grant, as coord's own `relaunch-grant` field carries it. NO new
  // computation and NO second subprocess: the field is already on every row of the wire, on the
  // rows it fires on and the ones it does not. Built here rather than at each call site so the two
  // maps come off ONE parse of one answer.
  const granted = new Map();
  for (const r of rows) {
    if (!r || !r.seat) continue;
    if (r['relaunch-grant']) granted.set(r.seat, r['relaunch-grant']);
    if (r.verdict !== 'READY') continue;
    ready.set(r.seat, Array.isArray(r.seed) ? r.seed : []);
  }
  return { ready, granted, rows, reason: null };
}

// ── THE DAEMON'S OWN RETRY GRANT — minted by coord, spent by coord, decided here (task 7.776) ──
//
// THE DEFECT THIS CLOSES, measured live 2026-08-11 on goal `forge-reference-seat-id-naming`. Seat
// `forg-intake` ran, its execution ended `failed` (exec 26274), and nothing ever ran it again: coord
// says READY (the seat has no `sessions.csv` row at all, so it carries no disposition), while
// `seatState` says `live` because `seatHasRun` sees the failed row in the store. `enqueueEligible`
// then `continue`d with NO log line, so the goal sat still and every surface looked healthy. A
// failed seat had exactly one escape — a HUMAN minting a ruled grant — and nobody was watching.
//
// ⚠ THE ENGINE AND COORD DO NOT READ EACH OTHER'S FILES, AND THIS PRESERVES THAT. `coord.py` never
// opens `executions.csv` and this file never opens `relaunch-grants.csv`; the session-id and the
// outcome cross as COMMAND-LINE ARGUMENTS. That is what makes the measured case solvable at all —
// `forg-intake` has no session log, so there is no session-id coord could resolve on its own.
//
// ⚠ IT MINTS ONLY ON THE SEAT'S **LAST** EXECUTION ROW, and only on a terminal non-`done` outcome
// the retry set admits. `blocked` is excluded at coord's end BY DECISION (a blocked seat is waiting
// on the owner); an OPEN row is excluded here, because a seat still running is not a seat to retry.
function mintRetryGrants(goalFolder, rows, { view, granted, logger = null }) {
  const last = new Map();
  for (const r of readExecutionRecord(goalFolder).rows) last.set(r.seat, r);
  const minted = new Map();
  for (const row of rows) {
    const rec = last.get(row.seat);
    const outcome = ((rec && rec.outcome) || '').trim();
    if (!rec || !outcome || outcome === DONE) continue;
    if (view.finished.has(row.seat) || view.notFinished.has(row.seat)) continue;
    if (granted.has(row.seat)) continue;
    let out;
    try {
      out = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'seat-retry',
        row.seat, '--mint', '--session', rec['session-id'] || '', '--outcome', outcome, '--json'],
      { encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (err) {
      // EVERY refusal is reported, and at `info` rather than `warn`: the bound being reached, the
      // outcome being one nobody retries, a grant already outstanding — these are the verb working.
      // What must never happen again is the SILENT arm.
      if (logger) {
        logger({
          level: 'info',
          message: 'seat NOT retried — `coordinate seat-retry --mint` declined',
          seat: row.seat,
          outcome,
          evidence: String(err.stderr || err.message || '').trim().slice(0, 400),
        });
      }
      continue;
    }
    let payload;
    try { payload = JSON.parse(out); } catch { payload = null; }
    // ⚠ THE ROW COMES BACK FROM THE MINT AND IS NOT RE-READ OFF `ready-seats`, and that is not an
    // optimisation. coord's grant hoist filters a grant against `sessions_last_ended`, so a seat
    // with NO session row NEVER carries its grant on the wire however many were minted for it —
    // the exact `forg-intake` shape. Re-reading would return null and the seat would stay stuck
    // with an unspendable grant. coord's own self-test states this limit as a row.
    if (!payload || !payload.grant) continue;
    minted.set(row.seat, payload.grant);
    if (logger) {
      logger({
        level: 'info',
        message: 'seat RETRIED — the daemon minted its own single-use relaunch grant against the '
          + 'execution record\'s failed outcome',
        seat: row.seat,
        outcome,
        evidence: `session ${rec['session-id']} · attempt ${payload['minted-so-far']} of ${payload.bound}`,
      });
    }
  }
  return minted;
}

// ── THE BOOT PROMPT — coord's, consumed here, composed nowhere ────────────────────────────────
//
//   python3 <ignite>/team-kit/coord.py --package <goal-folder> boot-prompt <seat>
//
// A queued seat that carries no `prompt` reaches `spawn.js#ensurePromptFile`, which writes a
// 0-BYTE file, and the harness exits 1 on "Input must be provided either through stdin or as a
// prompt argument when using --print" — measured on two goals, 2026-08-11 (execs 26274, 26358).
// The prompt exists; nothing asked for it. `coord.py#boot_prompt` is the ONE composer — it is what
// `launch` boots every seat on, and it alone knows the ephemeral/persistent split, the memory-file
// instruction and the leader's resume-first form. Composing a second one in JavaScript is exactly
// the drift § D1 deletes, so the seeding pass ASKS instead.
//
// ⚠ ONE SUBPROCESS PER LAUNCH, NOT PER PASS — deliberately not carried on `ready-seats --json`.
// That verb runs every cadence for every daemon-assigned goal; a launch happens once per seat, for
// the whole life of the seat. Measured on this box: `ready-seats --json` is ~0.43 s, and this verb
// costs the same interpreter start — so the readiness surface stays a status read of a few hundred
// bytes rather than a multi-KB prompt payload recomputed every ten seconds for nobody.
//
// ⚠ NULL IS A REFUSAL AND NEVER AN EMPTY PROMPT. Empty output is treated as failure for the same
// reason the whole defect exists: an empty prompt enqueued in a new place is the same bug moved.
function seatBootPrompt(goalFolder, seat) {
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'boot-prompt', seat], {
      encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err) {
    return { prompt: null, reason: `\`boot-prompt ${seat}\` did not answer (${err.code || err.message})`
      + `${err.stderr ? `: ${String(err.stderr).trim().slice(0, 400)}` : ''}` };
  }
  if (!raw || !raw.trim()) return { prompt: null, reason: `\`boot-prompt ${seat}\` printed nothing` };
  return { prompt: raw, reason: null };
}

// Does any OTHER row of this taskforce read `seat`'s declared output? Answered off coord's own
// parsed `after` member list, so no `after` grammar is read in JavaScript — the whole point of D1.
//
// ⚠ THE TEST IS CONTAINMENT OF THE SEAT NAME IN THE RAW MEMBER TEXT, and its error direction is
// the safe one. A member that truly names the seat must contain the seat's characters, whatever
// the grammar turns out to be, so a false NEGATIVE is impossible; a false POSITIVE (`x-terminal-2`
// for `terminal`) answers `yes`, which only ever makes the cage admission STRICTER. This is
// `edge-runner-job.py#successor_reads`' own bound, arrived at without a second decomposition of
// the member grammar.
function successorReads(rows, seat) {
  return rows.some((r) => r && r.seat !== seat
    && (Array.isArray(r.after) ? r.after : []).some((m) => String(m).includes(seat)))
    ? 'yes' : 'no';
}

function taskforcePath(goalFolder) {
  return path.join(goalFolder, TASKFORCE);
}

function readTaskforce(goalFolder) {
  const tfPath = taskforcePath(goalFolder);
  if (!fs.existsSync(tfPath)) {
    throw new Error(
      `${tfPath}: no taskforce — a run executes the run's seats, and the taskforce is ` +
      `where they are declared (CMP-4 goals tree). Nothing to run.`
    );
  }
  const rows = readCsv(tfPath).filter((r) => r.seat);
  if (!rows.length) throw new Error(`${tfPath}: no seat rows`);
  return rows;
}

// ── WHICH SEATS ARE NOT CAST — the ONE predicate every door refuses on (7.787) ────────────────
//
// Ruling D19 made a caller-named profile the FALLBACK for a seat that declares no cast; the
// 2026-08-12 narrowing stopped the two doors demanding it when nothing would read it; and
// `#d-abolish-profile-names` sub-ruling 3 finishes the line by deleting the fallback outright.
// "Any workflow reaching a taskforce MUST be cast first; an uncast seat is a NAMED REFUSAL at
// materialize/lane time — never a fallback, never a 03:00 journal line."
//
// So this function's job changed from "does the operator need to type a profile name?" to "may
// this goal be assigned to the daemon at all?". `rbtv-goal lane --set daemon`, `rbtv run` and the
// daemon's own watch pass all ask THIS, so what one accepts the others accept.
//
// ⚠ THE SURFACE IS `seat.md`, AND THAT IS MEASURED, NOT ASSUMED. `taskforce.csv` carries
// `harness,model,effort` columns too, and `rbtv run --help` says "seat.md" — they can disagree
// (`goal_cli.py#lint`'s "binding matches taskforce.csv" finding exists because they do). The
// LAUNCH reads the DESCRIPTOR: `spawn.js#launchSpecForSeat` builds its binding from
// `seatDeclaresValue(seatDir, 'harness'|'model')`, and every lane — daemon seeding, the attached
// tick, the foreground carrier, the warm-session leg — reaches the catalog through it. A gate
// reading the other surface is a gate that can disagree with the thing it gates. `taskforce.csv`
// supplies the seat NAMES here and nothing else.
//
// ⚠ THE PREDICATE IS THE CATALOG'S OWN. `declaresBinding` answers "is this seat cast at all", and
// nothing here re-implements it — a second interpreter of the one mapping is the drift
// DEC-1 § Shared launch-spec source forbids, and it is the drift `catalog.js` was built to end.
//
// Both are LAZY-required for the reason `attached-execution.js` lazy-requires the same reader:
// `seeding.js` is loaded by probes and by the engine index that have no business pulling in the
// spawn manager, and a new module-level import is a sibling dependency every one of them inherits.
function seatCast(goalFolder, seat) {
  const { seatDeclaresValue } = require('../server/spawn/spawn');
  const seatDir = path.join(goalFolder, 'seats', seat);
  return {
    harness: seatDeclaresValue(seatDir, 'harness'),
    model: seatDeclaresValue(seatDir, 'model'),
  };
}

// The seats that declare no cast. NON-EMPTY IS A REFUSAL at every door: there is nothing left for
// such a seat to run as, so seeding it would queue a row whose only possible outcome is
// `E_UNCAST_SEAT` at spawn, hours later, against a wasted execution row.
//
// Throws `readTaskforce`'s refusal when the goal is not materialized: "which seats need a
// fallback" has no answer before the seats exist, and inventing one either way is a guess. Each
// caller rules what to do with that — see their own comments.
function uncastSeats(goalFolder) {
  const { declaresBinding } = require('../launch-profiles/catalog');
  return readTaskforce(goalFolder)
    .filter((row) => !declaresBinding(seatCast(goalFolder, row.seat)))
    .map((row) => row.seat);
}

// ── WHAT THE RECORD SAYS ABOUT EACH SEAT, from the perspective of THIS store ──────────────────
//
// Two answers, not one, and the second is the review finding F3/F6 this exists to close.
//
//   done      the record carries a `done` outcome for the seat. Nobody re-runs it.
//   foreign   the record carries a row for the seat that THIS STORE HAS NO EXECUTION FOR, and that
//             row is not `done` — either still OPEN (a seat live in the other lane RIGHT NOW) or
//             ended non-`done` (failed / blocked / killed elsewhere).
//
// WHY `foreign` HAS TO EXIST AT ALL. Without it the record only ever stopped a re-run when the
// other lane had already FINISHED — so a seat the other lane was in the middle of running read
// `ready` here and was dispatched a second time, concurrently. The at-dispatch row was being
// written and read by nothing; the whole point of writing it at dispatch is that the other lane can
// see the seat is taken. And on the terminal-non-`done` side the two lanes were ASYMMETRIC: a
// locally failed seat needs an explicit `--relaunch` grant, while the same failure in the other
// lane was invisible and re-ran silently — conferring the grant nobody gave. `foreign` makes both
// cases behave like the local one: the seat is not `ready`, and an explicit grant is what releases
// it.
//
// ⚠ THE MEMBERSHIP TEST IS THE SESSION-ID JOIN, NOT THE `lane` COLUMN. `lane` says which KIND of
// store wrote the row (CMP-2), and two attached runs on two machines share that value — so a lane
// comparison would call another machine's live seat "ours" and dispatch it again. What actually
// answers "is this row mine" is whether an execution in THIS store owns that session id, which is
// the same join the retired v1 guard used and the one honest thing it had.
//
// ⚠ THE DISCLOSED BOUND: a foreign writer that CRASHED leaves its row open, and this holds the seat
// until that lane republishes. That is not a dead end — the other lane's next boot runs the
// adoption pass, which stamps the row from its own store (a crashed foreground row reconciles to
// `failed`, a killed detached one to `failed`/`killed`) and the seat becomes grantable. The operator
// path when that lane will never run again: `--relaunch <seat>`, which is the same explicit act a
// local failure already requires. Holding is the safe direction — the unsafe one is running a seat
// somebody else may still be running.
//
// ── AND A THIRD: `notFinished` — THE RECORD'S LAST WORD (owner ruling
// decisions.md#d-block-and-queue-mechanical-hold, which also closes the 7.626 review's F6) ─────
//
//   notFinished   the seat's LAST row in the record is not a finish — it is either still OPEN (a
//                 session is running for this seat RIGHT NOW) or it ended `blocked`. Either way the
//                 seat is NOT done, and — this is the part that needed code — an EARLIER `done`
//                 row, or the store's own `done` turn, does not make it done either.
//
// TWO FACTS RIDE ONE SET, because they are the same fact: `done` has always been "any row says
// done", which is right for the cross-lane no-double-run guarantee and WRONG as an answer to "is
// this seat finished now". F6 measured the difference: the chat revival opens a SECOND row for a
// seat whose first row is `done`, and the `done` row outranked it — so `--status` reported the seat
// done while a live session ran in its home, and the dependents that `done` released ran CONCURRENT
// with it. The last word settles both that and the hold, with one rule instead of two.
//
// And the HOLD is the `blocked` half of it: a `block-and-queue` seat that asked the owner and
// exited 0 has a store turn of `done` (the process really did exit) and a record row of `blocked`
// (`execution-record.js` § THE BLOCK-AND-QUEUE HOLD, where the word is decided). The record is THE
// completion authority, so its word wins over the store's — the sentence this file already opens
// with, now true in the direction that REMOVES done-ness as well.
//
// Derived, not stored: the last row per seat, out of the same file `done` and `foreign` come from.
// A LATER row clears it — which is exactly what the owner's answer mints (a revival session at the
// seat's home), so the hold releases through machinery that already existed. A `--relaunch` grant
// clears it for the same reason it clears `foreign`: an explicit human act.
function recordView(heartStore, goalFolder, { relaunch = null } = {}) {
  const rows = readExecutionRecord(goalFolder).rows;
  const done = new Set();
  const foreign = new Map();
  const notFinished = new Map();
  const blocked = new Map();
  if (!rows.length) return { done, finished: done, foreign, notFinished, blocked };
  // THE GRANT IS SOURCED HERE, not handed in — see `relaunch-grants.js`. A caller-supplied set is
  // still honoured (`--relaunch` argv, and any grant a caller minted for this pass); the goal
  // folder's own file is FOLDED IN rather than used as a fallback, because a pass that already
  // carries one kind of grant must not swallow the operator's.
  const grants = withFileGrants(relaunch, goalFolder);

  // The seat's LAST row, in file order — the record is append-only, so the last row for a seat is
  // its most recent execution. `failed`/`killed` are terminal words that were never `done`; they
  // keep the behaviour they had (the seat is not done and an explicit grant re-runs it), so only
  // the two non-finishes below are collected here.
  const last = new Map();
  for (const r of rows) last.set(r.seat, r);
  for (const [seat, r] of last) {
    const outcome = (r.outcome || '').trim();
    if (outcome === BLOCKED) {
      blocked.set(seat, `its last execution ended '${BLOCKED}' — the seat is waiting on an answer, so its dependents wait with it`);
      notFinished.set(seat, blocked.get(seat));
    } else if (!outcome) {
      notFinished.set(seat, `its last execution is still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
    }
  }

  // A NULL store is the `--status` case on a goal this lane has never run: nothing is ours, so
  // every non-done row is somebody else's — which is exactly what is true there.
  const ours = new Set();
  if (heartStore) {
    for (const status of ALL_TURN_STATUSES) {
      // `withThread: false` — only `session_id` is read here, and the attach is a recursive CTE
      // PER ROW. This runs once per goal per cadence over the store's WHOLE history.
      for (const row of heartStore.listExecutionsByStatus(status, { withThread: false })) {
        if (row.session_id) ours.add(row.session_id);
      }
    }
  }
  for (const r of rows) {
    const outcome = (r.outcome || '').trim();
    if (outcome === DONE) { done.add(r.seat); continue; }
    if (ours.has(r['session-id'])) continue;            // our own store already governs this one
    foreign.set(r.seat, outcome
      ? `ended '${outcome}' in the ${r.lane || 'other'} lane (session ${r['session-id']})`
      : `still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
  }
  // ── `finished` — "IS THIS SEAT DONE **NOW**", AND THE ONE ANSWER EVERY OUTRANKING TEST TAKES ──
  //
  // ⚠ THIS SET EXISTS BECAUSE `done` AND `notFinished` ARE INDEPENDENT, AND EVERY TEST THAT USED TO
  // WRITE `done.has(seat)` MEANT THIS. `done` is "ANY row says done" — the cross-lane no-double-run
  // guarantee, which must stay any-row. `notFinished` is the LAST row. Between them sits the seat
  // this build created: rows `done, blocked` or `done, open`, which `done` calls finished and the
  // last word calls not. Review findings F1 and F2 were both that gap, at the two call sites below
  // — the review's own words, a signature change that did not sweep its callers.
  //
  //   F1 (HIGH): the relaunch grant bailed on `done.has(seat)`, so `--relaunch` was a NO-OP for a
  //   seat held on its SECOND ask (`blocked, done, blocked`) — the documented escape did nothing
  //   and hand-editing `executions.csv` was the only way out of a permanently stuck wave.
  //   F2: the `foreign` deletion did the same, so a crashed foreign revival (`done, open`) was
  //   reported by NOTHING while `skippedAsFinished` called it finished and `states` called it live.
  //
  // Computed BEFORE the grant's deletes, so a grant can never make a seat read finished.
  const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));

  // A later `done` outranks an earlier non-done row for the same seat: the seat IS finished — but
  // only when `done` IS the last word (see above). An OPEN or `blocked` row after it is the seat's
  // current state and outranks the older `done`.
  for (const seat of finished) foreign.delete(seat);
  // The one-shot relaunch grant releases a foreign hold exactly as it releases a local failure —
  // and, exactly as there, it can never release a FINISHED seat. It releases the record's last-word
  // hold too: an operator saying "run this seat again" is the same explicit act, and the answer
  // that would otherwise release it is the one thing he is saying will not come.
  // ⚠ THE `if` IS NOT DEAD FLEXIBILITY AND THE INDENTATION IS LOAD-BEARING. This loop's guard line
  // is a MUTATION SITE, matched by exact text (`probe-block-and-queue-hold.js`, mutant `grant` —
  // review F1's red-first proof that a grant bails on the LAST WORD and not on any `done` row).
  // Sourcing the grant from a file made the old `if (relaunch)` wrapper unnecessary, and dropping
  // it re-indented these lines by two columns — which silently un-anchored that mutant: it reported
  // "0 file(s) carry the mutation site" and its arm went vacuous. The wrapper stays, now testing
  // the set instead of the parameter.
  if (grants.size) {
    for (const seat of grants) {
      // Since the 2026-08-12 loop-re-fire ruling the grant releases a FINISHED seat too — the
      // finished-guard that stood here (review F1's fix kept it on the last word) is gone,
      // because "a grant must not re-run completed work" now holds at the MINT, not here: the
      // file is written only by deliberate acts (the relaunch CLI, the leader, the verdict
      // verb's route-back), and the loop's whole point is re-dispatching a done-but-FAILed seat
      // on its slot (`concepts/loop.md`). Do not spell the old guard in this comment — the hold
      // probe's mutation site is matched by exact text.
      finished.delete(seat);
      done.delete(seat);
      foreign.delete(seat);
      notFinished.delete(seat);
      blocked.delete(seat);
    }
  }
  return { done, finished, foreign, notFinished, blocked };
}

function jobIdFor(seat, goal = null) {
  return goal ? `seat-${goal}-${seat}` : `seat-${seat}`;
}

// THE ONE PLACE THE GRANT IS SOURCED, and the reason it is here rather than at each caller.
//
// The eligibility engine already honoured a grant; what it had no way to RECEIVE one from was the
// daemon lane, because the grant's only source was an in-memory Set built from `rbtv-execution
// --relaunch` argv and `lane-watch.js` calls `seedGoal({goalFolder, goal})` with no
// relaunch key, ever. Threading a parameter down from `lane-watch.js` would have created a SECOND
// place that decides whether a grant applies — so the third caller of `seedGoal`, whenever it is
// written, would silently get none. That is exactly how this gap was born. Sourcing it inside the
// shared functions means `lane-watch.js` needs NO edit at all, which is the proof the fix sits at
// the right level.
//
// ⚠ FOLD, NOT FALLBACK. `relaunch ?? readGrants(...)` would be enough if the caller-supplied set
// were only ever `--relaunch` argv — but `seedGoal` can now also arrive carrying grants minted for
// this pass, and under `??` the presence of one of those would silently discard the operator's
// file grant for the same pass. The union is the only merge where neither authorization can
// swallow the other. The caller's own Set is mutated in place when there is one, deliberately: the
// attached loop's spend (`grants.delete(seat)`) is what stops a spent grant surviving to the next
// pass, and returning a fresh copy would leave that delete writing to an object nobody reads.
function withFileGrants(relaunch, goalFolder) {
  const grants = relaunch || new Set();
  for (const seat of readGrants(goalFolder)) grants.add(seat);
  return grants;
}

// ── Seeding: the taskforce IS the workflow ────────────────────────────────────────────────────
//
// `taskforce.csv` already carries one row per seat with an `after` column naming the seat it
// follows. That column IS the wave structure — nothing new is invented here, and no second
// scheduler is written: seeding only decides WHICH seats are eligible now, and the ticker decides
// what actually launches and how many run at once (`max_live_agent_sessions` — the parallel wave).
//
// NOTHING PROFILE-SHAPED IS SEEDED HERE, and that is the pivot of `#d-abolish-profile-names`
// (sub-ruling 2). A seat's launch spec is its own — resolved at spawn from its descriptor by
// `launch-profiles/catalog.js#specForSeatCast`, keyed by the (harness, model) its bindings sheet
// cast it as. A value carried on the queue row could only ever drift from that, which is exactly
// what it did: `rbtv run --profile`, the lane marker's second token and the chat bridge's
// `session_profile` all existed to fill ONE required argument, and every one of them was capable
// of naming something the seat was not cast as.
//
// `rows` is the taskforce, optionally pre-read by a caller that already needed it (seedGoal reads
// it before deciding whether to register anything at all). Default = read it here, as always.
function seedTaskforce(heartStore, goalFolder, { logger, goal = null, rows = null }) {
  rows = rows || readTaskforce(goalFolder);

  // CREATE-ONLY, and that is what makes a re-run a RESUME rather than a replay. registerJob is
  // create-only in the store (it throws E_JOB_EXISTS); a second boot finds every job already
  // registered and registers nothing.
  for (const row of rows) {
    const jobId = jobIdFor(row.seat, goal);
    if (heartStore.getJob(jobId)) continue;
    heartStore.registerJob({
      jobId,
      actionType: 'launch-agent',
      function: `attached-execution seat ${row.seat}`,
      // `required`/`optional` are OBJECTS of name -> type, not arrays — the store parses them
      // that way (parseArgsSchema) and REFUSES an array. Registration is strict on purpose: a
      // schema a future enqueue could never satisfy is what campaign issue S-2(a) was.
      argsSchema: JSON.stringify({ required: {}, optional: { workdir: 'string', prompt: 'string' } }),
      description: `seat ${row.seat} of ${row.taskforce_id || row['taskforce-id'] || 'this run'}`,
      createdAt: isoNow(),
      updatedAt: isoNow(),
    });
    if (logger) logger({ level: 'info', message: 'registered seat job', jobId, seat: row.seat });
  }
  return rows;
}

// The execution picture, read ONCE per pass from the store's own partition of jobs_log.
//
// `relaunch` is the ONE-SHOT RELAUNCH GRANT (console-run B1): a seat named in it is presented to
// the predicate WITHOUT its execution history, so a seat whose last attempt died reads `ready`
// again. The grant hides the rows from THIS VIEW only — nothing in the store is rewritten, so the
// failed attempt stays on the record it was written to. A FINISHED seat is never hidden: a grant
// must not be able to re-run completed work, and that is enforced here rather than trusted to the
// caller who typed the seat name. (Nor can a grant re-open a seat the RECORD calls done — that
// check is in `seatState`, ahead of everything the grant can touch.)
const ALL_TURN_STATUSES = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];

function executionsByJob(heartStore, relaunch = null, goal = null) {
  const byJob = new Map();
  for (const status of ALL_TURN_STATUSES) {
    // `withThread: false` — see `recordView` above. No consumer of this map reads `thread`
    // (the wave math keys on `job_id`, `status` and `session_id`); the attach is a recursive CTE
    // per row, paid once per goal per cadence over every execution ever recorded.
    for (const row of heartStore.listExecutionsByStatus(status, { withThread: false })) {
      const list = byJob.get(row.job_id) || [];
      list.push(row);
      byJob.set(row.job_id, list);
    }
  }
  if (relaunch) {
    for (const seat of relaunch) {
      // A granted seat's history is hidden WHOLE — finished rows included (owner ruling
      // 2026-08-12, the loop re-fire: a judge's FAIL verdict relaunches a builder whose row says
      // `done`, per `concepts/loop.md` — "a fresh worker re-dispatched on the slot"). The guard
      // that kept finished rows visible ("a grant must not re-run completed work") moved to the
      // MINT: every writer of the grant file is a deliberate act (the relaunch CLI, the leader,
      // the verdict verb's route-back), so admission rests on the act, not on this reader.
      byJob.delete(jobIdFor(seat, goal));
    }
  }
  return byJob;
}

function seatIsFinished(rows) {
  return Boolean(rows) && rows.some((r) => r.status === 'done');
}

function seatHasRun(rows) {
  return Boolean(rows) && rows.length > 0;
}

// THE ELIGIBILITY PREDICATE, in ONE place. Both the enqueue pass and the read-only status verb
// answer "what is this seat's state right now" from here — a second copy of the wave math is a
// status surface that can disagree with the engine it reports on, which is worse than no surface.
//
//   done     the goal's execution record says so, or a finished execution exists in this store
//   live     an execution exists that has not finished (running / stalled / failed / …)
//   queued   a pending queue row exists
//   ready    never fired, and COORD says READY — the next thing the engine enqueues
//   waiting  never fired, and coord does not say READY (or was never asked)
//
// `done` is a Set of seat names from `<goal>/executions.csv` — THE completion authority, and the
// one arm that makes a seat finished in one lane invisible-to-re-running in the other. It is
// optional so a caller with no goal folder in hand (a probe exercising the wave math on a
// hand-built map) still gets the store-only answer it always got.
const SEAT_STATES = ['done', 'live', 'queued', 'ready', 'waiting'];

// `notFinished` is the MECHANICAL HOLD (and the F6 fix), applied INSIDE `isDone` rather than as a
// state of its own — deliberately, and it is the whole ruling in one line. A held seat is not done,
// and neither is it done FOR ITS DEPENDENTS: `isDone(after)` is the same call, so the wave stops
// with no second rule to keep in step. No sixth seat state is minted: such a seat reads `live` for
// the same reason a foreign one does — it is neither dispatchable nor finished, and every reader of
// SEAT_STATES already understands that pair. WHY it is not moving is reported alongside the state
// (`seedGoal().blockedOnOwner`, `statusAttached()`'s `blockedOnOwner` flag), never as a state word.
// ⚠ `ready` IS COORD'S ANSWER, HANDED IN — never derived here (§ D1). Absent (a caller that could
// not ask, or did not) means NO seat is ready: the store may decline, never promote. That is the
// whole asymmetry, in one default.
function seatState(row, byJob, queued, { done = null, goal = null, foreign = null, notFinished = null, ready = null } = {}) {
  const isDone = (seat) => !(notFinished && notFinished.has(seat))
    && ((done && done.has(seat)) || seatIsFinished(byJob.get(jobIdFor(seat, goal))));
  if (isDone(row.seat)) return 'done';
  if (notFinished && notFinished.has(row.seat)) return 'live';
  const jobId = jobIdFor(row.seat, goal);
  // A seat the record shows running-or-ended-badly ELSEWHERE is `live` here — the same word the
  // local answer uses for exactly the same situation, so no reader learns a sixth state and no
  // caller can treat "live over there" as dispatchable.
  if (foreign && foreign.has(row.seat)) return 'live';
  if (seatHasRun(byJob.get(jobId))) return 'live';
  if (queued.has(jobId)) return 'queued';
  return ready && ready.has(row.seat) ? 'ready' : 'waiting';
}

// Enqueue every seat whose `after` dependency has finished and which has never been fired. Returns
// the seats enqueued this pass.
//
// `isHeld` is the ONE place the engine can DETACH a human-interactive seat, and it is where it is
// stopped (console-run ruling 1: such a seat is dispatched through the foreground carrier or not at
// all). Skipping it here rather than filtering the rows earlier keeps the wave math on the WHOLE
// taskforce — a held seat still blocks its dependents exactly as it would if it had been queued.
function enqueueEligible(heartStore, rows, {
  goalFolder, logger, isHeld = null, relaunch = null, goal = null, view = null,
  ready = null, readyRows = [], granted = null, heldByStore = null,
}) {
  // The goal folder's own grant file, folded into whatever the caller supplied (see
  // `withFileGrants`). Every use of the grant below reads `grants`, never `relaunch`, so the
  // predicate answers the same way on both lanes with no caller having to know the file exists.
  const grants = withFileGrants(relaunch, goalFolder);
  const byJob = executionsByJob(heartStore, grants, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const { done: finished, foreign, notFinished, blocked } = view || recordView(heartStore, goalFolder, { relaunch: grants });
  const enqueued = [];
  // The LIVE cage template each launch composes against — never a re-read of the YAML and never a
  // transcribed snapshot (§ D5). ⚠ IT IS PER SEAT SINCE 7.787, and it always should have been: it
  // used to read the CALLER'S profile, so on a mixed-cast goal (a claude seat and a codex seat)
  // the admission test ran against a template belonging to neither. It now reads the seat's OWN
  // launch spec, resolved through `specKey` from the same descriptor `spawn()` will read.
  // `heartStore.config.launchSpecs` is assigned by the composition root (`engine/index.js`) off
  // the spawn manager's loaded config. An uncaged spec yields `[]`, and `admitDeclaredOutputs`
  // does not run against one.
  const { specKey } = require('../launch-profiles/catalog');
  const launchSpecs = heartStore.config?.launchSpecs || {};
  const seatBindsFor = (seat) => {
    const cast = seatCast(goalFolder, seat);
    const spec = launchSpecs[specKey(cast.harness, cast.model)];
    return (spec && spec.sandbox && spec.sandbox.SeatBinds) || null;
  };

  for (const row of rows) {
    const jobId = jobIdFor(row.seat, goal);
    if (foreign && foreign.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — the execution record shows it elsewhere', seat: row.seat, evidence: foreign.get(row.seat) });
    }
    if (blocked && blocked.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — it is BLOCKED on the owner and its dependents wait with it', seat: row.seat, evidence: blocked.get(row.seat) });
    }
    // ⚠ THE SILENT DROP THIS LINE USED TO BE (task 7.776). It was a bare `continue` with no logger
    // call, and it is where the measured 18-hour stall lived: coord answered READY, this store's
    // own `seatHasRun` answered `live` off a `failed` execution row, and the seat vanished from
    // the pass with nothing said anywhere. A disagreement between coord's verdict and this store's
    // computed state is the ONE skip an operator cannot reconstruct from any other surface, so it
    // is the one that must be reported — with the computed state, which is the half he does not
    // have. Every other state word (`done`, `queued`, `waiting`) is ordinary and stays quiet:
    // logging those would bury this line under one message per seat per cadence forever.
    const state = seatState(row, byJob, queued, { done: finished, goal, foreign, notFinished, ready });
    if (state !== 'ready') {
      if (ready && ready.has(row.seat) && state === 'live') {
        if (heldByStore) heldByStore[row.seat] = `coord says READY, this store says \`${state}\` — an execution row exists here that has not finished`;
        if (logger) {
          logger({
            level: 'info',
            message: 'seat NOT enqueued — coord says READY and THIS store disagrees; the store never promotes, so the seat waits',
            seat: row.seat,
            state,
            evidence: heldByStore ? heldByStore[row.seat] : `computed state \`${state}\``,
          });
        }
      }
      continue;
    }
    if (isHeld && isHeld(row.seat)) continue;

    // ── § D5 · CAGE ADMISSIBILITY, THE LAST PRE-QUEUE REFUSAL ────────────────────────────────
    //
    // Could this seat actually WRITE its declared outputs once sandboxed, and could a successor
    // READING them read them? A row that declares a token the cage refuses fails at the FAR end,
    // after a launch, as a missing artifact marked against the seat's WORK — when the truth is
    // that its DECLARATION named a place it was never able to write. Refused here, at the door,
    // it costs one refusal instead of one wasted seat and one misattributed mark.
    //
    // Ordered LAST of the pre-queue tests, exactly as the Python it replaces was: no seat that
    // would have been declined for another reason is now declined for this one.
    const refusal = admitDeclaredOutputs({
      seatBinds: seatBindsFor(row.seat), goalFolder, seat: row.seat, successorReads: successorReads(readyRows, row.seat),
    });
    if (refusal) {
      if (logger) logger({ level: 'warn', message: 'seat NOT enqueued — a declared output is inadmissible for a caged launch', seat: row.seat, evidence: refusal });
      continue;
    }
    // ── THE BOOT PROMPT, THE LAST PRE-QUEUE REFUSAL ──────────────────────────────────────────
    // Composed by coord, for THIS seat, from THIS goal's package — never here. Ordered after the
    // cage test and BEFORE the relaunch grant is spent: a seat that cannot be composed for is not
    // launched, so its one-shot grant must survive to be spent on the pass that can.
    const { prompt, reason: promptReason } = seatBootPrompt(goalFolder, row.seat);
    if (prompt === null) {
      if (logger) {
        logger({
          level: 'warn',
          message: 'seat NOT enqueued — coord could not compose its boot prompt, and a seat queued '
            + 'without one boots a harness that exits immediately on empty input',
          seat: row.seat,
          evidence: promptReason,
        });
      }
      continue;
    }
    // ── THE GRANT IS SPENT HERE, AND NOWHERE EARLIER ─────────────────────────────────────────
    // Ordered AFTER the cage test and AFTER the boot-prompt test on purpose, and the comment above
    // states the rule it obeys: a seat that cannot be composed for is not launched, so its one-shot
    // grant must survive to be spent on the pass that can. Fail-closed in the other direction too —
    // an empty stamp means somebody else took the row, and this pass must NOT enqueue on an
    // authorization it did not burn, or two lanes launch one seat off one grant.
    const grant = granted && granted.get(row.seat);
    if (grant) {
      let stamp = '';
      let why = `session ${grant['session-id']} · anchor ${grant.anchor} — no unspent row matched`;
      try {
        const out = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder,
          'seat-retry', row.seat, '--spend', '--session', grant['session-id'] || '', '--json'],
        { encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
        stamp = (JSON.parse(out).stamp || '');
      } catch (err) {
        why = `\`coordinate seat-retry --spend\` failed: ${String(err.stderr || err.message || '').trim().slice(0, 400)}`;
      }
      if (!stamp) {
        if (logger) logger({ level: 'warn', message: 'seat NOT enqueued — its relaunch grant was NOT spent, and a launch off an unburnt grant is a replay window', seat: row.seat, evidence: why });
        continue;
      }
    }
    // THE SPEND, in the SAME instant the in-memory delete already happened — still after the cage
    // test and the boot-prompt compose, still with no `continue` between here and the enqueue, so
    // "grant spent" and "seat enqueued" remain ONE event. `Set.delete` answers whether this seat
    // held a grant at all, so a seat that never had one costs no file write.
    if (grants.delete(row.seat)) spendGrant(goalFolder, row.seat);

    const after = (row.after || '').trim();
    const seatDir = path.join(goalFolder, 'seats', row.seat);
    const seed = (ready && ready.get(row.seat)) || [];
    heartStore.enqueue({
      jobId,
      // ⚠ THE SEED IS NOT IN THIS OBJECT, AND THAT IS THE DOOR'S RULE, NOT A CHOICE. The registered
      // `args_schema` for a seat job is `{workdir, prompt}` (7.787 emptied its `required` half) and `heart-store.js`
      // validateArgs REFUSES an unregistered key by name (`E_BAD_ARGS: unknown argument: seed`).
      // `edge-runner-job.py#_enqueue_argv` states the rule it was measured into: "THE SEED NO
      // LONGER RIDES IN ARGV AND MUST NOT BE PUT BACK — a seat is driven by its DESCRIPTOR and by
      // the room, never by argv text." So the seed coord resolves is CARRIED (logged per seat and
      // returned on the pass) rather than submitted; the door is where it would have to be widened.
      //
      // ⚠ `prompt` IS A REGISTERED KEY (`seedTaskforce`'s `optional: {workdir, prompt}`) and it is
      // what the harness is actually booted on: `ticker.js#launchAgent` reads `args.prompt ?? null`
      // and `spawn.js#ensurePromptFile` writes those bytes as the session's stdin. Passed VERBATIM
      // — coord printed it with no trailing newline exactly so nothing here has to strip anything,
      // and a consumer that strips is a consumer that has begun re-assembling the prompt.
      args: JSON.stringify({ workdir: seatDir, prompt }),
      sessionMode: 'headless',
      triggerKind: 'scheduled',
      runAt: isoNow(),
      enqueuedBy: 'attached-execution',
    });
    enqueued.push(row.seat);
    if (logger) logger({ level: 'info', message: 'enqueued seat', seat: row.seat, after: after || null, seed });
  }
  return enqueued;
}

// ── THE DAEMON LANE'S PICKUP (criterion 2 of #d-s23-single-execution-record-now) ──────────────
//
// One call: read the goal's execution record, seed the taskforce into THIS store, enqueue the seats
// whose turn it is — skipping every seat the record says is finished, whichever lane finished it.
// The attached lane reaches the same two functions directly (it also owns a foreground carriage
// this does not); a shared store reaches them through here, with the namespace argument set.
//
// It is deliberately a FUNCTION AND NOT A TRIGGER. What tells the daemon to pick a goal up is a
// separate, owner-facing question — arming is per-package today (edge-fastpath) and deliberately
// unreachable from a flag — and answering it by, say, seeding every goal folder the daemon can see
// would be a policy this build was not asked to invent. `engine.seedGoal()` is the seam; the caller
// that fires it is named in the contract as the follow-on.
function seedGoal({ heartStore, goalFolder, goal, logger = null, isHeld = null, relaunch = null }) {
  if (!goal) {
    throw new Error(
      'seedGoal requires the goal NAME: it namespaces the job ids so two goals with a seat of the ' +
      'same name cannot share one job row in a store that holds every goal (the daemon\'s).'
    );
  }
  const rows = readTaskforce(goalFolder);
  const seats = rows.map((r) => r.seat);
  // ⚠ COORD FIRST, AND BEFORE ANYTHING IS WRITTEN. A refused computation seeds NOTHING for this
  // goal this pass — not a partial enqueue, and not even the create-only job registration, which
  // would be store rows written off an answer nobody has. The next pass retries; missing any
  // number of passes costs latency and nothing else (§ Why the re-seed stays the driver).
  let { ready, granted, rows: readyRows, reason } = readySeats(goalFolder);
  if (!ready) {
    if (logger) {
      logger({
        level: 'warn',
        message: 'goal NOT seeded this pass — `coordinate ready-seats` refused to compute readiness, and a partial '
          + 'seed off a refused computation is worse than none. Retried next cadence.',
        goal,
        goalFolder,
        evidence: reason,
      });
    }
    return {
      goalFolder, goal, seats, enqueued: [], seeds: {}, skippedAsFinished: [],
      heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, states: {}, readinessRefused: reason,
    };
  }
  // THE RETRY PASS, between coord's answer and anything this store writes (task 7.776). It mints
  // against the record `recordView` reads, so the two agree by construction about which seats are
  // finished — and a fresh mint FLIPS that seat's coord verdict from `DONE` to `READY`, which is
  // why `ready-seats` is asked a SECOND time when and only when something was minted. Once per
  // pass, never in a loop: a mint that changes no verdict changes none on the second read either.
  let view = recordView(heartStore, goalFolder, { relaunch });
  const minted = mintRetryGrants(goalFolder, rows, { view, granted, logger });
  if (minted.size) {
    const again = readySeats(goalFolder);
    if (again.ready) ({ ready, granted, rows: readyRows } = again);
    for (const [seat, grant] of minted) if (!granted.has(seat)) granted.set(seat, grant);
  }
  // ⚠ AN EXPLICIT CALLER-SUPPLIED SET STILL WINS. `--relaunch <seats>` is an operator saying "run
  // these again", and folding grants into it would silently widen what he named. Nothing in the
  // daemon lane passes one (`lane-watch.js` calls `seedGoal({ goalFolder, goal })`), so
  // this is the branch that runs unattended; the other is the one a human is standing over.
  // The view is recomputed WITH the set, because the grant's release of a record-level hold is
  // `recordView`'s own act and re-deriving it here would be its second home.
  if (!relaunch && granted.size) {
    relaunch = new Set(granted.keys());
    view = recordView(heartStore, goalFolder, { relaunch });
  }
  seedTaskforce(heartStore, goalFolder, { logger, goal, rows });
  const heldByStore = {};
  const enqueued = enqueueEligible(heartStore, rows, { goalFolder, logger, goal, view, isHeld, relaunch, ready, readyRows, granted, heldByStore });
  // WITH the grant set, since the loop re-fire (2026-08-12): the `states` report below must agree
  // with the enqueue decision above, and a granted `done` seat is dispatchable again — reporting
  // it `done` off a grant-blind read is the same one-report-contradicting-the-other defect F2
  // fixed for `skippedAsFinished`.
  const byJob = executionsByJob(heartStore, relaunch, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  return {
    goalFolder,
    goal,
    seats,
    readinessRefused: null,
    // The predecessors' declared outputs coord resolved for each seat this pass launched (§ D4).
    // Reported rather than submitted — see the enqueue call's note on the door's registered keys.
    seeds: Object.fromEntries(enqueued.map((s) => [s, ready.get(s) || []])),
    // ⚠ `finished`, NOT `done` (review F2): a seat with a `done` row and a LATER open or `blocked`
    // one was reported here as FINISHED while `states` said `live` — one report contradicting the
    // other, about the seat this build exists to hold.
    skippedAsFinished: seats.filter((s) => view.finished.has(s)),
    // Named separately from `skippedAsFinished` because the two are different facts and an operator
    // must be able to tell them apart: one seat is DONE, the other is somebody else's right now.
    // Since F2 this also carries the seat whose LAST row is somebody else's OPEN one — a crashed
    // foreign revival used to be deleted from this map by an older `done` row and reported nowhere.
    heldByOtherLane: Object.fromEntries(seats.filter((s) => view.foreign.has(s)).map((s) => [s, view.foreign.get(s)])),
    // The THIRD held-for-a-reason set, named separately for the same reason the second is: an
    // operator must be able to tell "somebody else is running it" from "it is waiting on YOU".
    blockedOnOwner: Object.fromEntries(seats.filter((s) => view.blocked.has(s)).map((s) => [s, view.blocked.get(s)])),
    // THE FOURTH HELD-FOR-A-REASON SET, and the one that cost a live investigation (task 7.776).
    // coord said READY and THIS store said otherwise, so `enqueueEligible` skipped the seat — with
    // no log line, nothing in the return, and every other surface reading healthy. The goal sat
    // still for 18 hours. It is named separately from the three above for their own reason: "the
    // record says somebody else has it" and "MY OWN store has already fired it" are different
    // facts with different remedies, and the second is the one an operator cannot see anywhere
    // else. ⚠ NOT COSMETIC: this reproduces the identical invisible hold the moment the retry
    // budget runs out, which is a state this design GUARANTEES will be reached.
    heldByStore,
    enqueued,
    states: Object.fromEntries(rows.map((r) => [r.seat, seatState(r, byJob, queued, { done: view.done, goal, foreign: view.foreign, notFinished: view.notFinished, ready })])),
  };
}

module.exports = {
  TASKFORCE,
  ALL_TURN_STATUSES,
  SEAT_STATES,
  readCsv,
  readySeats,
  seatBootPrompt,
  successorReads,
  taskforcePath,
  readTaskforce,
  seatCast,
  uncastSeats,
  jobIdFor,
  seedTaskforce,
  executionsByJob,
  seatIsFinished,
  seatHasRun,
  seatState,
  recordView,
  enqueueEligible,
  seedGoal,
};
