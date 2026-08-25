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
// ⚠ `finishedSeats` IS GONE AND IT WAS ALREADY DEAD HERE (W2). It was imported on this line and
// called from NOWHERE — repointing it would have been a no-op on a live goal, which is why the
// consumer sweep was ordered by grep rather than by memory. What replaced its QUESTION is
// `recordView`'s `done` set, and that set no longer comes from this file at all: it comes from the
// seats' own check-out dispositions on coord's `ready-seats --json` answer.
const {
  recordView, readyFromEndings, isPendingWork, bindEnding, goalNameOf,
} = require('./ending-reads');
// The ONE interpreter resolver this repo already has (`python3` is a Microsoft-Store LIE on
// Windows — it is on PATH, is executable, and runs no python).
const { requirePythonCmd } = require('../lib/python-cmd');
const { admitDeclaredOutputs, admitLaneReach } = require('./cage-admission');
// D9 (seed-gates, 2026-08-19): the goal-live check's ONE liveness reading — the same
// `deriveLease` the launch-time gate (`spawn.js` -> `checkGoalExecuting`) reads, at the same
// ROOM threshold, so the pre-spend refusal and the launch refusal can never disagree.
const { deriveLease } = require('../server/lease/lease');
// The ONE quote-aware row splitter this module already has (`execution-record.js` reads the goal's
// record with it). Reusing it is the whole CSV fix — see below.
const { splitRow } = require('../server/seat-identity/csv');
const { DOORS, refuseLaunch } = require('../supervisor/doors');
// ── THE ONE OWED-WORK COMPUTER AND THE ONE ENQUEUE [spec-supervisor §5, T4-R7, C-15] ──────────
// This module used to own a SECOND owed-work computer (`enqueueEligible`) and a second call to
// `heartStore.enqueue`. Both are gone: `deriveOwed` is the single "this seat is owed a launch"
// function and `launchThroughDoor` is the single enqueue on the owed path. Nothing in this file
// may re-derive either — see `supervisor/owed.js`'s header for the disagreement that cost.
const { deriveOwed, seatState: owedSeatState } = require('../supervisor/owed');
const { admitLaunch, launchThroughDoor, storeDisagreeRefusal } = require('../supervisor/launch-door');

// One message per launch-door refusal kind, so the journal names WHICH gate refused rather than
// leaving an operator to infer it from the evidence string.
const REFUSAL_MESSAGES = Object.freeze({
  hold: 'seat NOT enqueued — held for human-interactive detach (dispatched through the foreground carrier or not at all)',
  'cage-admit': 'seat NOT enqueued — a declared output is inadmissible for a caged launch',
  'lane-reach': 'seat NOT enqueued — its declared lane reach is not satisfied by the composed cage',
  'boot-prompt': 'seat NOT enqueued — coord could not compose its boot prompt, and a seat queued '
    + 'without one boots a harness that exits immediately on empty input',
});

const TASKFORCE = 'taskforce.csv';

// D25 — the frozen-at-seeding classifier. Waitable work is ONLY what coord positively
// names: READY, or BLOCKED and not dead. An unknown verdict is NOT waitable (falls OUT).
// `probe-verdict-vocabulary.js` extracts coord's live vocabulary and asserts every value
// is a key here — a new coord verdict becomes a commit-time failure, never a silent alarm.
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
// ⚠ A NON-ZERO EXIT SEEDS NOTHING FOR THIS GOAL THIS PASS. No python, an unreadable package, a
// timeout, output that is not the documented array — all land in the same place, for the same
// reason: a refused computation may never be PARTIALLY seeded off. `null` is the refusal; it is
// never an empty ready set, because "nothing is ready" and "I could not ask" are different claims.
//
// ⚠ A DISPOSITION SKEW IS NOT ONE OF THEM ANY MORE (Q2a, owner-ruled 2026-08-18). It used to be:
// `ready-seats` exited 1 on any SKEW row, that exit landed in the catch below, and the COMPLETE
// answer was discarded — so ONE disputed seat on `meet-transcript-summarizer` froze 65 healthy
// siblings for 4.5 hours across 1,704 refusals, one every ~10s, with no owner-facing signal. coord
// now exits 0 and carries the dispute ON THE ROWS: the disputed seat reads `SKEW`, everything with
// an `after` path to it reads `BLOCKED`, and every other seat is offered as usual. Nothing here
// filters for it — a `SKEW` row is simply not `READY`, which the loop below already handles — and
// `seedGoal` says it out loud every pass so shrinking the blast radius does not silence the alarm.
// The old whole-goal fail-close is still available to a caller that asks by name
// (`ready-seats --fail-on-skew`); this consumer deliberately does not.
//
// ponytail: one python invocation per daemon-assigned goal per cadence. At the current scale that
// is noise; if it stops being noise, batch the VERB (`ready-seats` over N packages) — never
// reintroduce a JS reader.
const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
const COORD_TIMEOUT_MS = 60000;
// Lane-watch cadence is ~10 s and a fire follows its queue row within one tick, so 60 s is
// comfortably past "one full cadence" while the real thresholding is left to the alarm's
// existing STALL_MS 5-minute persistence. Do not add a second timer.
const ENQUEUE_UNFIRED_GRACE_MS = 60 * 1000;

function readySeats(goalFolder, { heartStore = null, goal = null, rows: taskRows = null } = {}) {
  const refuse = (reason) => ({ ready: null, rows: [], reason });
  let rows = taskRows;
  if (!rows) {
    let raw;
    try {
      raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'ready-seats', '--json'], {
        encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
      });
    } catch (err) {
      return refuse(`\`ready-seats --json\` did not answer (${err.code || err.message})`
        + `${err.stderr ? `: ${String(err.stderr).trim().slice(0, 400)}` : ''}`);
    }
    try { rows = JSON.parse(raw); } catch { return refuse(`\`ready-seats --json\` returned no JSON: ${String(raw).slice(0, 200)}`); }
    if (!Array.isArray(rows)) return refuse('`ready-seats --json` returned no row array');
  }
  const ready = readyFromEndings(heartStore, goalFolder, { rows, goal });
  return { ready, rows, reason: null };
}

// ── THE RENEWAL ANSWER, TRANSPORTED (LE-10, 2026-08-19) ───────────────────────────────────────
//
// `coord.renewal_state` (team-kit/coord.py) is THE ONE READER of the successor-pending signal —
// its own header says so: nothing else parses `lifecycle-inflight.json`, in any language. The
// one JS-side consumer (`engine/attached-execution.js`) TRANSPORTS that answer through the
// read-only `renewal-state` verb exactly as `readySeats` above transports the frontier: JS carries
// the value, never the computation.
//
// Returns coord's `state` word (`successor-pending` | `no-successor`) or `null` when there is no
// answer at all (no python, a refused verb, junk output). ⚠ EVERY CALLER MUST TREAT `null` AS
// no-successor — the conservative direction, because the ONLY thing a caller does with
// `successor-pending` is KEEP WAITING, and waiting forever on a question nobody answered is the
// absorbing state this signal exists to prevent.
function renewalState(goalFolder, seat) {
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'renewal-state', seat, '--json'], {
      encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch { return null; }
  try {
    const answer = JSON.parse(raw);
    return (answer && typeof answer.state === 'string') ? answer.state : null;
  } catch { return null; }
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

// ── THE BOOT PROMPT — coord's, consumed here, composed nowhere ────────────────────────────────
//
//   python3 <ignite>/team-kit/coord.py --package <goal-folder> boot-prompt <seat> --lane <lane>
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
// ⚠ W1 (adv, C4) — THE LANE RIDES ALONG, because the prompt differs by it: a daemon-lane seat is
// NOT told to check in (a caged `systemd-run` unit has no pane to check in from, so that
// instruction could only ever be failed as the first act of every session), while check-OUT — the
// sole producer of `incomplete` and of the leader route flag — is instructed on both lanes.
// This pass serves BOTH lanes (`attached-execution.js` calls it too), so the marker is read rather
// than assumed, through the ONE JS speller of its grammar. The require is lazy because
// `lane-watch` requires THIS module.
function seatBootPrompt(goalFolder, seat) {
  let lane = 'console';
  try { lane = require('./lane-watch').readLane(goalFolder).lane; } catch { /* console, fail-closed */ }
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'boot-prompt', seat, '--lane', lane], {
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

// ── VALIDATE AT LOAD (D16, dag-hardening) ──────────────────────────────────────────────────────
//
// THE MEASURED INCIDENT: `readCsv` above is header-driven and forgiving BY DESIGN (a short row
// reads `''` for its missing tail, a long row drops the overflow) — the 08-14/15 stall was a
// malformed `taskforce.csv` row the reader absorbed silently, refusing every seat, every 10 s, for
// a day, with no owner signal, until an owner-ruled hand edit ended it (root-cause-archaeology
// §2). D16's whole scope: a malformed row becomes a REFUSAL here, naming the file, the row, and
// the defect — not a change to what a well-formed row MEANS.
//
// Two checks are local (no subprocess, no second grammar): a data row whose CELL COUNT disagrees
// with the header's, and two rows naming the SAME seat. The graph — cycles, dangling `after`,
// guard/alternate grammar — is NOT re-walked here: `goal_cli.py#check_acyclic` is "the room's ONLY
// sanctioned acyclicity check" (its own docstring, Rule 9) and is INVOKED, never re-implemented.
const GOAL_CLI_PY = path.join(__dirname, '..', 'capabilities', 'goals-tree', 'tool', 'goal_cli.py');
const CHECK_ACYCLIC_TIMEOUT_MS = 60000;

// The two local checks. Line numbers are 1-based FILE lines (blank lines skipped, same filter
// `readCsv` applies), so a defect message points at the exact row an editor would open. Cells are
// split with `splitRow` — the same RFC-4180 splitter `readCsv` uses — so a legitimately quoted
// multi-predecessor `after` cell is never miscounted as extra columns.
function validateTaskforceRows(tfPath) {
  const text = fs.readFileSync(tfPath, 'utf8');
  const numbered = [];
  text.split('\n').forEach((line, idx) => { if (line.trim().length) numbered.push({ n: idx + 1, line }); });
  if (!numbered.length) return null;
  const header = splitRow(numbered[0].line).map((c) => c.trim());
  const seatIdx = header.indexOf('seat');
  const seenAt = new Map();
  for (const { n, line } of numbered.slice(1)) {
    const cells = splitRow(line);
    if (cells.length !== header.length) {
      const shown = line.length > 200 ? `${line.slice(0, 200)}…` : line;
      return `${tfPath}:${n}: row has ${cells.length} cell(s), header has ${header.length} — ${shown}`;
    }
    if (seatIdx < 0) continue;
    const seat = (cells[seatIdx] || '').trim();
    if (!seat) continue;
    if (seenAt.has(seat)) {
      return `${tfPath}: seat '${seat}' is named on lines ${seenAt.get(seat)} and ${n} — duplicate seat row`;
    }
    seenAt.set(seat, n);
  }
  return null;
}

// The graph check, PERFORMED by invoking `check-acyclic`, exactly as `queue-request.js#goalLocalLint`
// invokes the materializer's own lint rather than re-deciding its verdict (R7). Returns one of:
//   'clean'              the after-graph is acyclic, every edge resolves, every guard/alternate parses
//   { defect }           a genuine FINDING — the load refuses
//   'no-after-column'    this taskforce carries no `after` column at all — nothing to check (NOT a
//                        defect: some fixtures/manifests legitimately carry none)
//   { checkFailed }      the check itself could not run — no python, a timeout, undocumented output
function checkAcyclicViaCli(tfPath) {
  try {
    execFileSync(requirePythonCmd(), [GOAL_CLI_PY, 'check-acyclic', tfPath],
      { encoding: 'utf8', timeout: CHECK_ACYCLIC_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    return 'clean';
  } catch (err) {
    const stdout = String(err.stdout || '');
    const stderr = String(err.stderr || '');
    const findingLines = stdout.split('\n').map((l) => l.trim()).filter((l) => l.startsWith('FINDING'));
    if (findingLines.length) return { defect: findingLines.join('  ·  ').slice(0, 400) };
    // A `Refusal` naming the missing `after` column (`goal_cli.py#check_acyclic`'s own docstring:
    // "column absent -> Refusal ... cell empty -> a finding") is not a malformed file — it is a file
    // this check was never meant to walk. Anything ELSE non-zero (no python, a timeout, junk output)
    // is the check failing to answer, which is not evidence about the file either way.
    if (/no '.*' column/.test(stderr)) return 'no-after-column';
    return { checkFailed: (stderr || stdout || (err && err.message) || 'unknown error').trim().slice(0, 400) };
  }
}

// ── THE MEMO — serves both the subprocess cost and the "quiet must never mean forgotten" property
// (`lane-watch.js#shouldShout`'s own doctrine, keyed here on the FILE rather than the lane marker:
// a taskforce fix does not touch the marker, so a marker-keyed memo would never re-arm). Keyed on
// the file's mtime+size — cheap, no hashing — so the SAME bytes never re-spawn the subprocess or
// re-print the trap-1/trap-2 notices, and a CHANGED file always revalidates and is loud again.
//
// ponytail: process-lifetime Maps, one small entry per goal, cleared by nothing and re-armed only
// by a daemon restart — the same conservative direction the deleted `goal-stall-alarm.js`'s own
// dedup Map disclosed (a duplicate notice after a restart beats a freeze the memo silently
// remembers past the life of the process that decided it). ⚠ That Map is exactly what
// `observation/emitter.js` replaced with a PERSISTED signature registry — do not read this note
// as a precedent for a new in-memory alarm memo.
const taskforceValidationMemo = new Map();  // tfPath -> { key, error: string|null }
const graphCheckNoticed = new Map();        // tfPath -> key already reported (trap 1 / trap 2)

function taskforceFileKey(tfPath) {
  const st = fs.statSync(tfPath);
  return `${st.mtimeMs}:${st.size}`;
}

// `readTaskforce`'s validation gate. Throws a row-precise `Error` for a genuine defect; otherwise
// returns having spawned nothing (memo hit) or having run the two local checks plus (at most once
// per file version) the graph check. NEVER refuses on a check that could not run — see
// `checkAcyclicViaCli` above; `console.error` is used for those two trap notices because
// `readTaskforce` has no logger threaded to it (many callers, no shared umbrella) and this still
// lands in the daemon's journal, which is what "logged loudly" requires here.
function validateTaskforce(tfPath) {
  const key = taskforceFileKey(tfPath);
  const cached = taskforceValidationMemo.get(tfPath);
  if (cached && cached.key === key) {
    if (cached.error) throw new Error(cached.error);
    return;
  }
  let error = validateTaskforceRows(tfPath);
  if (!error) {
    const graph = checkAcyclicViaCli(tfPath);
    if (graph && graph.defect) {
      error = `${tfPath}: after-graph malformed — ${graph.defect}`;
    } else if (graph === 'no-after-column' || (graph && graph.checkFailed)) {
      if (graphCheckNoticed.get(tfPath) !== key) {
        graphCheckNoticed.set(tfPath, key);
        console.error(graph === 'no-after-column'
          ? `readTaskforce: ${tfPath} carries no 'after' column — the acyclicity check is SKIPPED, not refused`
          : `readTaskforce: the acyclicity check could not run for ${tfPath} — proceeding WITHOUT it (${graph.checkFailed})`);
      }
    }
  }
  taskforceValidationMemo.set(tfPath, { key, error: error || null });
  if (error) throw new Error(error);
}

function readTaskforce(goalFolder) {
  const tfPath = taskforcePath(goalFolder);
  if (!fs.existsSync(tfPath)) {
    throw new Error(
      `${tfPath}: no taskforce — a run executes the run's seats, and the taskforce is ` +
      `where they are declared (CMP-4 goals tree). Nothing to run.`
    );
  }
  validateTaskforce(tfPath);
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
// locally failed seat was HELD here, while the same failure in the other lane was invisible and
// re-ran silently. `foreign` makes both cases behave like the local one: the seat is not `ready`.
// (What used to release either was the operator's `--relaunch` grant; D12 deleted it, and the
// releasing act is now the goal watcher's owed-work launch off the ledgers.)
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
// `failed`, a killed detached one to `failed`/`killed`) and the seat is offerable again. When that
// lane will never run again, the goal watcher is what picks the work up — D12 (2026-08-20) deleted
// the `--relaunch` grant that used to be the operator's act here. Holding is the safe direction —
// the unsafe one is running a seat somebody else may still be running.
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
// seat's home), so the hold releases through machinery that already existed.
// recordView lives in ending-reads.js — done-set = ending=done; hold-set = §2.1.

function jobIdFor(seat, goal = null) {
  return goal ? `seat-${goal}-${seat}` : `seat-${seat}`;
}

// The execution picture, read ONCE per pass from the store's own partition of jobs_log.
//
// D12 (2026-08-20): IT READS PLAIN LEDGER STATE. The `relaunch` parameter used to hide a granted
// seat's execution history WHOLE so the predicate would re-offer it; that masking is deleted with
// the grant stores. A seat comes back because the goal watcher derives it as owed work from the
// ledgers (`engine/reconcile.js`), never because a reader was told to look away.
const ALL_TURN_STATUSES = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];

function executionsByJob(heartStore, goal = null) {
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
// `seatState` IS `supervisor/owed.js`'S NOW [spec-supervisor §5, T1-R3]. The wave arithmetic IS
// the owed question for the graph half, so leaving it here would have left half the one owed-work
// computer behind. Re-exported under its own name and with its own signature: the injected record
// readers are this module's, and no caller of `seatState` learns a new name for a predicate whose
// behaviour did not change.
function seatState(row, byJob, queued, opts = {}) {
  return owedSeatState(row, byJob, queued, { ...opts, jobIdFor, seatIsFinished, seatHasRun });
}

// D2 (2026-08-19): a cage-admission refusal lands ONCE on the goal's own bus, not only in this
// daemon's journal — the measured failure was a seat refused every 10s for hours with nothing an
// operator-read surface saying so (G-owner-console-0818-2030). The engine reaches coord-side
// surfaces through coord.py verbs only (the boundary stated above: neither runtime reads the
// other's files); `surface-refusal` is idempotent per (seat, reason) under coord's own lock, so
// calling it on every seed pass costs one read, never a duplicate row. Never fatal, and never a
// verdict: a surfacing failure must not change whether the seat is enqueued.
function surfaceCageRefusal(goalFolder, seat, refusal, logger) {
  try {
    const out = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder,
      '--as', 'ignite-daemon', 'surface-refusal', seat, '--reason', refusal, '--json'],
    { encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    const res = JSON.parse(out);
    if (res.status === 'surfaced' && logger) {
      logger({ level: 'info', message: 'cage-admission refusal surfaced on the goal bus', seat, num: res.num });
    }
  } catch (err) {
    if (logger) {
      logger({ level: 'warn', message: 'cage-admission refusal NOT surfaced on the goal bus', seat,
        error: String(err.stderr || err.message || '').trim().slice(0, 400) });
    }
  }
}

// -- LAUNCH WHAT THE ONE COMPUTER SAYS IS OWED [spec-supervisor §5, T4-R7, C-15] ---------------
//
// ⚠ THIS FUNCTION USED TO BE `enqueueEligible`, AND IT USED TO BE A COMPUTER. It worked out its
// own owed set (whose `after` is satisfied and who has never fired) on a ~10 s cadence while
// `reconcile.js` worked out a different one on a ~300 s cadence, and BOTH called
// `heartStore.enqueue` (CODE-GROUND-TRUTH §4). Two computers that can disagree, with no third
// surface able to say which is right, is the defect spec-supervisor §5 retires.
//
// It computes nothing now. `deriveOwed` (`supervisor/owed.js`) is the single "this seat is owed a
// launch" function and class R is the graph-derived launchability [T1-R3] that used to live in
// this loop's head. It enqueues nothing either: `launchThroughDoor` (`supervisor/launch-door.js`)
// is the ONE enqueue on the owed path, and this function's five old pre-queue gates are that
// door's refusals. What is left here is the seeding CADENCE and its reporting — which is all this
// lane ever needed to own.
//
// `isHeld` is still the ONE place the engine can DETACH a human-interactive seat, and it is still
// applied at the door rather than by filtering the rows earlier: a held seat must keep blocking its
// dependents exactly as it would if it had been queued, so the wave math stays on the WHOLE
// taskforce (console-run ruling 1).
function launchOwed(heartStore, rows, {
  goalFolder, logger, isHeld = null, goal = null, view = null,
  ready = null, readyRows = [], heldByStore = null,
  suppressedEnqueues = null,
}) {
  const byJob = executionsByJob(heartStore, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const resolvedView = view || recordView(heartStore, goalFolder, { readyRows });
  const { foreign, blocked } = resolvedView;

  // THE ONE OWED COMPUTER. Class R is asked for, never re-derived — the injected readers are this
  // module's own record readers, which is the seam that keeps `supervisor/` from requiring `engine/`
  // at load time.
  const { classR, disagreements } = deriveOwed(goalFolder, {
    goal,
    ready,
    graph: {
      rows, byJob, queued, view: resolvedView,
      jobIdFor, seatIsFinished, seatHasRun,
    },
  });

  for (const row of rows) {
    if (foreign && foreign.has(row.seat) && logger) {
      logger({ level: 'info', message: 'seat held — the execution record shows it elsewhere', seat: row.seat, evidence: foreign.get(row.seat) });
    }
    if (blocked && blocked.has(row.seat) && logger) {
      // ⚠ THE WORD IS `HELD`, NOT `BLOCKED` (adv, C82). `ready-seats` already spells `BLOCKED` for
      // "an `after` member is unsatisfied", and the two are different things — a message calling
      // this one BLOCKED sends an operator to the DAG when the answer is a person.
      logger({ level: 'info', message: 'seat waiting — an unanswered ask to the owner, and its dependents wait with it', seat: row.seat, evidence: blocked.get(row.seat) });
    }
  }

  // THE DISAGREEMENT, NOW A NAMED DOOR REFUSAL rather than the silent `continue` it once was
  // (task 7.776 — coord answered READY, this store's own `seatHasRun` answered `live` off a
  // `failed` execution row, and the seat vanished from the pass with nothing said anywhere: an
  // 18-hour stall). It is the ONE skip an operator cannot reconstruct from any other surface.
  for (const [seat, why] of Object.entries(disagreements)) {
    const refused = storeDisagreeRefusal({ seat, goal, evidence: why });
    if (heldByStore) heldByStore[seat] = refused.evidence;
    if (logger) {
      logger({
        level: 'info',
        message: 'seat NOT enqueued — coord says READY and THIS store disagrees; the store never promotes, so the seat waits',
        seat,
        state: 'live',
        evidence: refused.evidence,
      });
    }
  }

  // The LIVE cage template each launch composes against — never a re-read of the YAML and never a
  // transcribed snapshot (§ D5). ⚠ IT IS PER SEAT SINCE 7.787, and it always should have been: it
  // used to read the CALLER'S profile, so on a mixed-cast goal (a claude seat and a codex seat)
  // the admission test ran against a template belonging to neither. It now reads the seat's OWN
  // launch spec, resolved through `specKey` from the same descriptor `spawn()` will read.
  const { specKey } = require('../launch-profiles/catalog');
  const launchSpecs = heartStore.config?.launchSpecs || {};
  const seatBindsFor = (seat) => {
    const cast = seatCast(goalFolder, seat);
    const spec = launchSpecs[specKey(cast.harness, cast.model)];
    return (spec && spec.sandbox && spec.sandbox.SeatBinds) || null;
  };

  const enqueued = [];
  for (const item of classR) {
    const seat = item.seat;
    const admit = admitLaunch({
      seat,
      goal,
      goalFolder,
      isHeld,
      seatBinds: seatBindsFor(seat),
      successorReads: successorReads(readyRows, seat),
      // D2 (2026-08-19): the composition root's ONE workspace-root resolution, threaded via the
      // store (`engine/index.js` assigns it off the spawn manager) — the gate needs it to judge
      // workspace-grammar declared outputs (`.rbtv/mirror/…`) against the same root the spawner
      // resolves rw grants against.
      workspaceRoot: heartStore.config?.workspaceRoot || null,
      promptFn: seatBootPrompt,
    });
    if (admit.refused) {
      if (logger) {
        logger({
          level: admit.kind === 'hold' ? 'info' : 'warn',
          message: REFUSAL_MESSAGES[admit.kind] || 'seat NOT enqueued — the launch door refused it',
          seat,
          evidence: admit.evidence,
        });
      }
      // D2 (2026-08-19): a cage-admission refusal lands ONCE on the goal's own bus, not only in
      // this daemon's journal — the measured failure was a seat refused every 10s for hours with
      // nothing an operator-read surface saying so (G-owner-console-0818-2030).
      if (admit.surface) surfaceCageRefusal(goalFolder, seat, admit.evidence, logger);
      continue;
    }

    const seatDir = path.join(goalFolder, 'seats', seat);
    const launched = launchThroughDoor({
      heartStore,
      seat,
      goal,
      jobId: jobIdFor(seat, goal),
      // ⚠ THE SEED IS NOT IN THIS OBJECT, AND THAT IS THE DOOR'S RULE, NOT A CHOICE. The registered
      // `args_schema` for a seat job is `{workdir, prompt}` and `heart-store.js` validateArgs
      // REFUSES an unregistered key by name (`E_BAD_ARGS: unknown argument: seed`).
      // `edge-runner-job.py#_enqueue_argv` states the rule it was measured into: "THE SEED NO
      // LONGER RIDES IN ARGV AND MUST NOT BE PUT BACK — a seat is driven by its DESCRIPTOR and by
      // the room, never by argv text." So the seed coord resolves is CARRIED (logged per seat and
      // returned on the pass) rather than submitted; the door is where it would have to be widened.
      //
      // ⚠ `prompt` IS A REGISTERED KEY and it is what the harness is actually booted on:
      // `ticker.js#launchAgent` reads `args.prompt ?? null` and `spawn.js#ensurePromptFile` writes
      // those bytes as the session's stdin. Passed VERBATIM — coord printed it with no trailing
      // newline exactly so nothing here has to strip anything.
      args: JSON.stringify({ workdir: seatDir, prompt: admit.prompt }),
      runAt: isoNow(),
      // ── THE SEEDING DOOR'S NAME [spec-supervisor §3, T4-R7] ────────────────────────────────
      // Read off the supervisor's door list rather than spelled here, because this string is what
      // travels: the queue row carries it as `enqueued_by`, `ticker.js#launchAgent` threads it
      // into `spawn()`, and `doors.js#doorForLauncher` turns it back into the door name at the pid
      // moment. Two spellings of it — one here, one in the door list — is a launch that silently
      // becomes UNSUPERVISED the day either side is edited.
      enqueuedBy: DOORS.seeding.launcher,
    });
    if (launched.refused) {
      if (suppressedEnqueues) suppressedEnqueues[seat] = launched.evidence;
      if (logger) {
        // ⚠ THE FIELDS ARE THE MESSAGE. `probe-enqueue-record.js` Arm A reads `because` off this
        // record by name — the suppression's own word for why (`live-turn`, …) is the half an
        // operator cannot reconstruct, so it is carried as a field rather than folded into prose.
        const enq = launched.enq || {};
        logger({
          level: 'warn',
          message: launched.kind === 'braked'
            ? 'the admission brake REFUSED this launch — the seat was not queued'
            : 'store SUPPRESSED the enqueue — the seat was not queued',
          seat,
          because: enq.because,
          queue_id: enq.queue_id,
          exec_id: enq.exec_id,
          held_status: enq.held_status,
          evidence: launched.evidence,
        });
      }
      continue;
    }
    enqueued.push(seat);
    if (logger) {
      logger({
        level: 'info',
        message: 'enqueued seat',
        seat,
        after: item.after || null,
        seed: (ready && ready.get(seat)) || [],
      });
    }
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
function seedGoal({ heartStore, goalFolder, goal, logger = null, isHeld = null, readLease = deriveLease }) {
  if (!goal) {
    throw new Error(
      'seedGoal requires the goal NAME: it namespaces the job ids so two goals with a seat of the ' +
      'same name cannot share one job row in a store that holds every goal (the daemon\'s).'
    );
  }
  // ── D9 (seed-gates, 2026-08-19): THE GOAL-LIVE CHECK, BEFORE ANYTHING IS SPENT ──────────────
  // The measured failure (G-leader-0818-1830, meet-transcript-summarizer): two relaunch grants
  // burned with no session row to show for them, because the spend ran in this function's ready-row
  // loop while the goal-live refusal (`E_GOAL_NOT_LIVE`) fired LATER and elsewhere — at the
  // ticker's dispatch, in `spawn.js`. THERE IS NOTHING LEFT TO SPEND (D12, 2026-08-20), and the
  // gate STAYS: seeding a dead room still costs a pass of work the spawn door was always going to
  // refuse, and the bus row is how an operator learns the room is gone. The SAME lease, at the
  // SAME threshold, is read HERE FIRST: `deriveLease().live` is the ROOM's existence
  // (never the stricter occupant set — a room mid-relaunch between seat boots must still seed).
  // Not live → one log line, one bus row (the D2 surfacing, keyed by the goal name), and a return
  // with NOTHING enqueued; the next cadence retries for free.
  //
  // `readLease` is the probes' injection point, `checkGoalExecuting`'s own pattern. The workspace
  // root is the composition root's ONE resolution threaded via the store (D2); absent (a bare
  // test store with no spawn manager behind it), the check cannot be derived and seeding proceeds
  // as before — the daemon and the attached lane always thread one.
  const wsRoot = heartStore.config?.workspaceRoot || null;
  if (wsRoot) {
    const lease = readLease({ workspaceRoot: wsRoot, goal });
    const notLive = !lease.ok
      ? `the lease of goal ${goal} is UNREADABLE (${lease.reason}) — refused on ignorance rather than spent on a fact it could not measure`
      : (lease.live ? null : `goal ${goal} has NO live room (tmux session named \`${goal}\`) — the spawn door would refuse every launch E_GOAL_NOT_LIVE, so nothing is enqueued and no relaunch grant is spent. Start the room (\`rbtv run\`) and the next seed pass proceeds`);
    if (notLive) {
      if (logger) {
        logger({
          level: 'warn',
          message: 'goal NOT seeded this pass — the goal is not LIVE, and seeding it would spend grants on launches the spawn door refuses',
          goal, goalFolder, evidence: notLive,
        });
      }
      surfaceCageRefusal(goalFolder, goal, notLive, logger);
      // ── E_GOAL_NOT_LIVE IS A SUPERVISOR-OWNED REFUSAL [spec-supervisor §3, T4-R7] ───────────
      //
      // The room is down, so no process can be born — and the refusal is the SUPERVISOR's word,
      // not seeding's own, because the three absences it asserts are the supervisor's subject:
      // nothing spawned (no registry row), nothing stamped (a refused launch is not a dead seat,
      // and stamping one would put a `failed` on a seat that never ran), nothing enqueued
      // (G-leader-0818-1830 burned two relaunch grants on launches the spawn door was always
      // going to refuse). It is NOT a seat `failed` — that class is envelope's `launch-refused`.
      const refusal = refuseLaunch({ door: 'goal-not-live', goal, evidence: notLive });
      return {
        launchRefused: refusal,
        goalFolder, goal, seats: readTaskforce(goalFolder).map((r) => r.seat), enqueued: [], seeds: {},
        skippedAsFinished: [], heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, states: {},
        readinessRefused: null, goalNotLive: notLive, skewed: [], frozen: null,
        suppressedEnqueues: {}, enqueueUnfired: [],
      };
    }
  }
  const rows = readTaskforce(goalFolder);
  const seats = rows.map((r) => r.seat);
  // ⚠ COORD FIRST, AND BEFORE ANYTHING IS WRITTEN. A refused computation seeds NOTHING for this
  // goal this pass — not a partial enqueue, and not even the create-only job registration, which
  // would be store rows written off an answer nobody has. The next pass retries; missing any
  // number of passes costs latency and nothing else (§ Why the re-seed stays the driver).
  const { ready, rows: readyRows, reason } = readySeats(goalFolder, { heartStore, goal });
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
      // A refusal computed no rows, so it names no skewed seat. The owner alarm reads
      // `readinessRefused` for this arm — see the `skewed` note on the success return below.
      skewed: [], frozen: null, suppressedEnqueues: {}, enqueueUnfired: [],
    };
  }
  const view = recordView(heartStore, goalFolder, { readyRows, goal });
  seedTaskforce(heartStore, goalFolder, { logger, goal, rows });
  const heldByStore = {};
  const suppressedEnqueues = {};
  const enqueued = launchOwed(heartStore, rows, { goalFolder, logger, goal, view, isHeld, ready, readyRows, heldByStore, suppressedEnqueues });
  const unfiredCutoff = new Date(Date.now() - ENQUEUE_UNFIRED_GRACE_MS).toISOString().replace(/\.\d{3}Z$/, 'Z');
  const enqueueUnfired = heartStore.listEnqueueUnfired(goal, unfiredCutoff).map((r) => ({
    seat: r.seat, because: r.because, at: r.at,
  }));
  const byJob = executionsByJob(heartStore, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  // Hoisted off the return (LE-13 below reads it): the per-seat state map, unchanged.
  const states = Object.fromEntries(rows.map((r) => [r.seat, seatState(r, byJob, queued, { done: view.done, goal, foreign: view.foreign, notFinished: view.notFinished, ready })]));
  // ── LE-13 (2026-08-19): AN EMPTY FRONTIER OVER PENDING SEATS IS A FREEZE, NOT HEALTH ────────
  // `readySeats`' three refusal arms all land in the `!ready` return above — but a ZERO-EXIT `[]`
  // is a valid array, so it walks past them as an empty ready map with no refusal. On a goal
  // whose taskforce still registers PENDING seats that is a goal nothing will ever seed: coord
  // ruled on none of its rows, so no pass, ever, has anything to dispatch. "Pending" is read off
  // `states` — the ONE classifier this return already reports — not a second predicate: a seat
  // neither `done` (its disposition, or this store's own finished turn) nor moving is pending,
  // and a goal with anything `live`/`queued` is a goal in motion, never frozen. `[]` over a goal
  // whose every seat is finished is an honest empty answer and stays silent. `ready-seats`' own
  // exit behavior is deliberately untouched (backlog task 3's producer side).
  // ── D22 (2026-08-19): A DEAD MODE-VARIANT BRANCH IS NOT PENDING WORK ───────────────────────
  // A goal's taskforce registers ONE SEAT PER `planning-mode` variant and the lane runs exactly
  // one, so the other — and everything downstream of it — is BLOCKED FOREVER BY DESIGN. LE-13's
  // filter above counted those rows and fired `goal frozen AT seeding` on two HEALTHY production
  // goals on the day it shipped (14 of stools' 16 non-done rows; the same shape on meet). An
  // alarm that fires on healthy goals is an alarm the owner learns to ignore, which reinstates
  // the failure mode this whole guard exists to catch.
  //
  // ⚠ THE ANSWER IS COORD'S OWN `dead` FIELD, NEVER A JS RE-DERIVATION. Reachability is decided
  // by one predicate in one language (`coord.py#mark_dead_rows`, D22 / PRIN-11); a second reader
  // here would need the `after` grammar, the guard-ruling file and the alternate/conjunct
  // arithmetic — which is exactly the duplication `readySeats`' own `seed` note refuses. An
  // ABSENT field reads FALSE, which is the pre-D22 behaviour: an older coord.py degrades to the
  // false positive, never to a silent hole in the alarm.
  //
  // ⚠ `ready.size` IS UNTOUCHED — it is `freeze-alarm`'s landed fix (it replaced
  // `readyRows.length`, which counted rows coord ANSWERED rather than rows coord ruled READY, so
  // the guard could never fire on the real freeze). Nothing here weakens it.
  //
  // ── D25 (2026-08-20): INVERT THE ARITHMETIC. Subtract-the-known-harmless (done, then dead)
  // is what produced the THIRD false positive — minted IDLE chairs (`goal-master`, `consultant`)
  // counted as pending-forever work and re-lit `goal frozen AT seeding` every 10s. Count as
  // pending ONLY what coord POSITIVELY classifies as waitable work: verdict READY, or BLOCKED
  // with `dead` false. Every other verdict (IDLE, DONE, HELD, RUNNING, SKEW, RENEWING,
  // RENEW-BLOCKED, UNBUILT, UNDECLARED, STOPPED) and any future unknown class falls OUT of the
  // alarm, never into it. `isWaitableWork` is the one classifier; the vocabulary probe fails
  // if coord grows a verdict this table does not name.
  const deadSeats = new Set((readyRows || []).filter((r) => r && r.dead).map((r) => r.seat));
  const moving = seats.some((s) => states[s] === 'live' || states[s] === 'queued');
  const api = bindEnding(heartStore, goalFolder);
  const gid = goalNameOf(goalFolder, goal);
  const waitableSeats = (readyRows || [])
    .filter((r) => r && r.seat && !r.dead && isPendingWork(api, gid, r.seat))
    .map((r) => r.seat);
  const pendingUnseeded = (ready.size || moving) ? []
    : waitableSeats;
  if (pendingUnseeded.length && logger) {
    logger({
      level: 'warn',
      message: 'goal frozen AT seeding — `ready-seats` ruled NO seat READY for a goal whose '
        + 'taskforce registers pending seats, so nothing was seeded and nothing ever will be until '
        + 'the goal state is repaired',
      goal, goalFolder, seats: pendingUnseeded, deadExcluded: deadSeats.size,
    });
  }
  return {
    goalFolder,
    goal,
    seats,
    readinessRefused: null,
    skewed: [],
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
    // coord said READY and THIS store said otherwise, so the seeding pass skipped the seat — with
    // no log line, nothing in the return, and every other surface reading healthy. The goal sat
    // still for 18 hours. It is named separately from the three above for their own reason: "the
    // record says somebody else has it" and "MY OWN store has already fired it" are different
    // facts with different remedies, and the second is the one an operator cannot see anywhere
    // else. ⚠ NOT COSMETIC: this reproduces the identical invisible hold the moment the retry
    // budget runs out, which is a state this design GUARANTEES will be reached.
    heldByStore,
    suppressedEnqueues,
    enqueueUnfired,
    enqueued,
    // LE-13, computed above: the empty-frontier freeze, shaped for the owner alarm
    // (read first by the deleted `goal-stall-alarm.js#conditionOf`; its successor is
    // `observation/`'s emitter, an ordinary caller). `null` is the ordinary case.
    frozen: pendingUnseeded.length ? {
      kind: 'seeding-empty',
      seats: pendingUnseeded,
      // D22: THE EXCLUDED-DEAD COUNT IS PART OF THE ALARM, not a debug line — this string is what
      // reaches the owner over Slack (now via `observation/emitter.js`), and a reader who
      // cannot see how many rows were discounted cannot audit the alarm that discounted them.
      detail: 'no launchable seat (of ' + readyRows.length + ' row(s) answered, '
        + deadSeats.size + ' of them DEAD by design and excluded) while these taskforce seats are pending',
    } : null,
    states,
  };
}

module.exports = {
  TASKFORCE,
  ALL_TURN_STATUSES,
  SEAT_STATES,
  readCsv,
  readySeats,
  renewalState,
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
  launchOwed,
  // Exported for `engine/probes/probe-cage-workspace-grammar.js`: the refusal->bus wire, driven
  // against a fixture goal without standing up the whole enqueue path.
  surfaceCageRefusal,
  seedGoal,
};
