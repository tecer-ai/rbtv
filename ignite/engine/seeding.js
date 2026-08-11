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
const READY_SEATS_TIMEOUT_MS = 60000;

function readySeats(goalFolder) {
  const refuse = (reason) => ({ ready: null, rows: [], reason });
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'ready-seats', '--json'], {
      encoding: 'utf8', timeout: READY_SEATS_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
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
  for (const r of rows) {
    if (!r || r.verdict !== 'READY' || !r.seat) continue;
    ready.set(r.seat, Array.isArray(r.seed) ? r.seed : []);
  }
  return { ready, rows, reason: null };
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
      for (const row of heartStore.listExecutionsByStatus(status)) {
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
  if (relaunch) {
    for (const seat of relaunch) {
      if (finished.has(seat)) continue;
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

// ── Seeding: the taskforce IS the workflow ────────────────────────────────────────────────────
//
// `taskforce.csv` already carries one row per seat with an `after` column naming the seat it
// follows. That column IS the wave structure — nothing new is invented here, and no second
// scheduler is written: seeding only decides WHICH seats are eligible now, and the ticker decides
// what actually launches and how many run at once (`max_live_agent_sessions` — the parallel wave).
//
// The PROFILE is not derived from the row's `harness`/`model` HERE, and it no longer needs to be.
// Mapping a cast (harness, model) onto exactly one profile NAME is task 7.54's catalog, which is
// now BUILT — `launch-profiles/catalog.js#profileForBinding`, the ONE derivation, shared with
// `capabilities/bindings/tool/bindings.py#catalog`. It is applied at the ONE point every launch
// passes through (`server/spawn/spawn.js#profileForSeatCast`, owner ruling D19), so a seat runs
// what its `seat.md` casts it as no matter which lane dispatched it.
//
// So the profile is still passed by NAME by the caller and is still resolved from the ONE shared
// config — it is now the FALLBACK for a seat that declares no cast (the channel master's
// `open_binding` case), not the answer for every seat. Deriving it here as well would be the
// second mapping DEC-1's shared-profile-source ruling exists to prevent.
// `rows` is the taskforce, optionally pre-read by a caller that already needed it (seedGoal reads
// it before deciding whether to register anything at all). Default = read it here, as always.
function seedTaskforce(heartStore, goalFolder, { profile, logger, goal = null, rows = null }) {
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
      argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { workdir: 'string', prompt: 'string' } }),
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
    for (const row of heartStore.listExecutionsByStatus(status)) {
      const list = byJob.get(row.job_id) || [];
      list.push(row);
      byJob.set(row.job_id, list);
    }
  }
  if (relaunch) {
    for (const seat of relaunch) {
      const jobId = jobIdFor(seat, goal);
      if (!seatIsFinished(byJob.get(jobId))) byJob.delete(jobId);
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
  profile, goalFolder, logger, isHeld = null, relaunch = null, goal = null, view = null,
  ready = null, readyRows = [],
}) {
  const byJob = executionsByJob(heartStore, relaunch, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const { done: finished, foreign, notFinished, blocked } = view || recordView(heartStore, goalFolder, { relaunch });
  const enqueued = [];
  // The LIVE cage template this pass's launches compose against — the daemon's own resolved
  // profile, never a re-read of the YAML and never a transcribed snapshot (§ D5). An uncaged
  // profile yields `[]`, and `admitDeclaredOutputs` does not run against one.
  const seatBinds = heartStore.config?.profiles?.[profile]?.sandbox?.SeatBinds || null;

  for (const row of rows) {
    const jobId = jobIdFor(row.seat, goal);
    if (foreign && foreign.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — the execution record shows it elsewhere', seat: row.seat, evidence: foreign.get(row.seat) });
    }
    if (blocked && blocked.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — it is BLOCKED on the owner and its dependents wait with it', seat: row.seat, evidence: blocked.get(row.seat) });
    }
    if (seatState(row, byJob, queued, { done: finished, goal, foreign, notFinished, ready }) !== 'ready') continue;
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
      seatBinds, goalFolder, seat: row.seat, successorReads: successorReads(readyRows, row.seat),
    });
    if (refusal) {
      if (logger) logger({ level: 'warn', message: 'seat NOT enqueued — a declared output is inadmissible for a caged launch', seat: row.seat, evidence: refusal });
      continue;
    }
    if (relaunch) relaunch.delete(row.seat);

    const after = (row.after || '').trim();
    const seatDir = path.join(goalFolder, 'seats', row.seat);
    const seed = (ready && ready.get(row.seat)) || [];
    heartStore.enqueue({
      jobId,
      // ⚠ THE SEED IS NOT IN THIS OBJECT, AND THAT IS THE DOOR'S RULE, NOT A CHOICE. The registered
      // `args_schema` for a seat job is `{profile | workdir, prompt}` and `heart-store.js`
      // validateArgs REFUSES an unregistered key by name (`E_BAD_ARGS: unknown argument: seed`).
      // `edge-runner-job.py#_enqueue_argv` states the rule it was measured into: "THE SEED NO
      // LONGER RIDES IN ARGV AND MUST NOT BE PUT BACK — a seat is driven by its DESCRIPTOR and by
      // the room, never by argv text." So the seed coord resolves is CARRIED (logged per seat and
      // returned on the pass) rather than submitted; the door is where it would have to be widened.
      args: JSON.stringify({ profile, workdir: seatDir }),
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
function seedGoal({ heartStore, goalFolder, profile, goal, logger = null, isHeld = null, relaunch = null }) {
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
  const { ready, rows: readyRows, reason } = readySeats(goalFolder);
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
      heldByOtherLane: {}, blockedOnOwner: {}, states: {}, readinessRefused: reason,
    };
  }
  const view = recordView(heartStore, goalFolder, { relaunch });
  seedTaskforce(heartStore, goalFolder, { profile, logger, goal, rows });
  const enqueued = enqueueEligible(heartStore, rows, { profile, goalFolder, logger, goal, view, isHeld, relaunch, ready, readyRows });
  const byJob = executionsByJob(heartStore, null, goal);
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
  successorReads,
  taskforcePath,
  readTaskforce,
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
