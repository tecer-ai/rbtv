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
const { readExecutionRecord, CLEAN, PROCESS_OUTCOME_OF } = require('./execution-record');
// The ONE interpreter resolver this repo already has (`python3` is a Microsoft-Store LIE on
// Windows — it is on PATH, is executable, and runs no python).
const { requirePythonCmd } = require('../lib/python-cmd');
const { admitDeclaredOutputs, admitLaneReach } = require('./cage-admission');
// D9 (seed-gates, 2026-08-19): the goal-live check's ONE liveness reading — the same
// `deriveLease` the launch-time gate (`spawn.js` -> `checkGoalExecuting`) reads, at the same
// ROOM threshold, so the pre-spend refusal and the launch refusal can never disagree.
const { deriveLease } = require('../server/lease/lease');
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

function readySeats(goalFolder) {
  const refuse = (reason) => ({ ready: null, rows: [], reason });
  let raw;
  try {
    raw = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder, 'ready-seats', '--json'], {
      encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'],
    });
  } catch (err) {
    return refuse(`\`ready-seats --json\` did not answer (${err.code || err.message})`
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

// ── THE RENEWAL ANSWER, TRANSPORTED (LE-10, 2026-08-19) ───────────────────────────────────────
//
// `coord.renewal_state` (team-kit/coord.py) is THE ONE READER of the successor-pending signal —
// its own header says so, and `jobs/goal-watcher-job.py` § ONE READER states the doctrine: nothing
// else parses `lifecycle-inflight.json`, in any language. This transports that answer through the
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
// ── R3a — A STRUCTURALLY-UNFIXABLE REFUSAL STOPS BEING REISSUED (owner-ruled 2026-08-15) ───────
//
// THE DEFECT: the mint below is asked every 10s per goal, forever, with no bound anywhere. A seat
// whose refusal can NEVER succeed (a garbage outcome word coord's vocabulary refuses; an unspent
// grant already outstanding) was re-offered and refused ~8,600 times a day — one live seat measured
// at ~20 points of a core continuously, 2026-08-13 → 2026-08-15.
//
// ⚠ THE STRUCTURAL/TRANSIENT SPLIT IS COORD'S OWN, NOT A SECOND CLASSIFIER. `coord.py`
// § REFUSAL_LAYERS names the layer in every refusal's first line, and that text ALREADY crosses on
// `err.stderr` — no new surface, no vocabulary duplicated in JS. `input` (the argv can never
// satisfy the verb) and `state` (the run's recorded state forbids it) are unfixable by asking again
// with the SAME argv, so they strike out. `environment` (a busy/contended world), `role gate`,
// `identity`, a coord timeout and any UNLAYERED crash keep retrying forever, unchanged: a strike
// limit that silently gave up on contention would be a worse defect than the loop it replaces, so
// the cap is opt-IN by layer and an unrecognised refusal is treated as transient.
const REFUSAL_STRIKE_LIMIT = 3;
const STRUCTURAL_REFUSAL_LAYERS = new Set(['input', 'state']);
// ⚠ THE KEY IS THE WHOLE INPUT, and that is what keeps this from being a permanent blacklist: a new
// execution row, a different outcome word or a new session is a DIFFERENT key that retries from
// zero. Only the identical unfixable ask is capped.
// ponytail: process-lifetime Map, no eviction. One entry per distinct (goal, seat, outcome,
// session) that was refused structurally, and each stops growing at the limit; if a box ever
// accumulates enough distinct dead executions to matter, evict by insertion order.
const structuralStrikes = new Map();

function refusalLayerOf(stderr) {
  const m = /refused \[coord ([a-z ]+)\]/.exec(String(stderr || ''));
  return m ? m[1] : null;
}

function mintRetryGrants(goalFolder, rows, { view, granted, logger = null }) {
  const last = new Map();
  for (const r of readExecutionRecord(goalFolder).rows) last.set(r.seat, r);
  const minted = new Map();
  for (const row of rows) {
    const rec = last.get(row.seat);
    const rawOutcome = ((rec && rec.outcome) || '').trim();
    // ⚠ THE EMPTY CHECK COMES BEFORE THE TRANSLATION, AND THAT ORDER IS THE POINT. A row that never
    // recorded an outcome at all is not a retry candidate; translating first would hand it to the
    // `crashed` side of the map and mint against it forever.
    if (!rec || !rawOutcome) continue;
    // ⚠ W2 — THE COLUMN IS A PROCESS VOCABULARY (`clean|crashed|killed`, `execution-record.js`
    // § THE SCHEMA) AND OLD ROWS ARE INERT BY MIGRATION: a seat whose last execution predates
    // W2 (`f956f4c4`, 2026-08-14T01:33Z) still carries `done`/`blocked`/`failed` on disk, and
    // those words are refused by coord's `DAEMON_RETRY_FROM_OUTCOMES`. So the legacy word is
    // TRANSLATED ONCE, HERE, through the same map the writer uses — and the translated value is
    // what BOTH the guard below and the mint argv see. Without it, a legacy `failed` row fell
    // through this guard, reached the blocking `execFileSync` below and was refused by coord on
    // every 10s tick, forever (2,621 refusals, 0 mints, measured 2026-08-14).
    // An UNKNOWN word passes through UNCHANGED (`|| rawOutcome`) rather than defaulting to
    // `crashed`: it is then refused once, visibly, instead of being silently retried as a crash.
    const outcome = PROCESS_OUTCOME_OF[rawOutcome] || rawOutcome;
    // THE GUARD IS `CLEAN`, NOT `done`. A clean exit is nothing to retry: whether the WORK finished
    // is the seat's check-out, and that lives on `view.finished` below. `crashed`/`killed` are the
    // whole retry domain and coord's `DAEMON_RETRY_FROM_OUTCOMES` is where that set is enforced —
    // this line only declines to ASK about the rows that plainly are not it. Legacy `blocked` maps
    // to `CLEAN` and is skipped here, which is the same ruling the comment below records.
    if (outcome === CLEAN) continue;
    if (view.finished.has(row.seat) || view.notFinished.has(row.seat)) continue;
    // ⚠ NO AUTO-RETRY AGAINST A WAITING HUMAN — the exclusion TRANSFERRED HERE from coord's
    // `DAEMON_RETRY_FROM_OUTCOMES` (adv, C18). That constant used to carry it by omitting `blocked`
    // from the outcome vocabulary; `blocked` is not an outcome word any more, so the decision moved
    // to the surface that now holds the fact: coord's `HELD` verdict, which `recordView` collects
    // into `view.blocked`. Same ruling, same effect, one hop further up — a seat waiting on an
    // owner-ask is the one terminal state whose remedy is a person, and an unattended retry would
    // spin a wave against a question nobody answered.
    if (view.blocked.has(row.seat)) {
      if (logger) {
        logger({
          level: 'info',
          message: 'seat NOT retried — it is HELD on an unanswered owner-ask, and the remedy for that '
            + 'is a person. An automatic retry would spin the wave against a question nobody answered.',
          seat: row.seat,
          outcome,
          evidence: String(view.blocked.get(row.seat) || '').slice(0, 400),
        });
      }
      continue;
    }
    // ⚠ NEVER AUTO-MINT AGAINST ANOTHER LANE'S SEAT (owner ruling 2026-08-13). `foreign` is "this
    // seat's last execution belongs to a DIFFERENT lane's own store" — the cross-lane
    // never-double-dispatch guarantee. A grant RELEASES a foreign hold (`recordView`'s grant loop),
    // which is correct for a HUMAN-granted relaunch and wrong here: this path is unattended, so a
    // seat that crashed under the console lane, seen by nobody, would be retried by the daemon on
    // its next pass. A cross-lane failure waits for a human instead. Measured red without this
    // line: `probe-daemon-lane-watch.js` L5 (`held-goal`/alpha).
    if (view.foreign.has(row.seat)) {
      if (logger) {
        logger({
          level: 'info',
          message: 'seat NOT retried — its last execution belongs to another lane; an unattended '
            + 'auto-mint would release the cross-lane hold, so this one waits for a human',
          seat: row.seat,
          outcome,
          evidence: String(view.foreign.get(row.seat) || '').slice(0, 400),
        });
      }
      continue;
    }
    if (granted.has(row.seat)) continue;
    const strikeKey = `${goalFolder} ${row.seat} ${outcome} ${rec['session-id'] || ''}`;
    // STRUCK OUT — skipped silently, and the silence is deliberate here where it is a defect
    // everywhere else: the strike-out itself was logged loudly once, naming this exact input, and
    // re-logging it every 10s forever is half of what this fix exists to stop.
    if ((structuralStrikes.get(strikeKey) || 0) >= REFUSAL_STRIKE_LIMIT) continue;
    let out;
    try {
      // D4 — `--as ignite-daemon`, and it is not decoration. The daemon's MAIN process is not a
      // daemon-fired exec, so coord's F16 lane (`daemon_exec_identity`, keyed on an
      // `rbtv-worker-*` cgroup) resolves NOBODY here and `seat-retry`'s role gate refused every
      // one of the 16,865 calls this line ever made. The claim is the documented equivalent of a
      // check-in for a process that has no pane to check in from.
      out = execFileSync(requirePythonCmd(), [COORD_PY, '--package', goalFolder,
        '--as', 'ignite-daemon', 'seat-retry',
        row.seat, '--mint', '--session', rec['session-id'] || '', '--outcome', outcome, '--json'],
      { encoding: 'utf8', timeout: COORD_TIMEOUT_MS, stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (err) {
      // EVERY refusal is reported, and at `info` rather than `warn`: the bound being reached, the
      // outcome being one nobody retries, a grant already outstanding — these are the verb working.
      // What must never happen again is the SILENT arm.
      const layer = refusalLayerOf(err.stderr);
      let struck = 0;
      if (STRUCTURAL_REFUSAL_LAYERS.has(layer)) {
        struck = (structuralStrikes.get(strikeKey) || 0) + 1;
        structuralStrikes.set(strikeKey, struck);
      }
      if (logger) {
        logger({
          level: 'info',
          message: struck >= REFUSAL_STRIKE_LIMIT
            ? 'seat GIVEN UP ON — `coordinate seat-retry --mint` refused this exact input '
              + `${REFUSAL_STRIKE_LIMIT} times at coord's \`${layer}\` layer, which asking again `
              + 'cannot change. It will NOT be reissued or logged again until the seat records a '
              + 'new execution; a human must clear it.'
            : 'seat NOT retried — `coordinate seat-retry --mint` declined',
          seat: row.seat,
          outcome,
          evidence: `${struck ? `structural strike ${struck}/${REFUSAL_STRIKE_LIMIT} · ` : ''}`
            + String(err.stderr || err.message || '').trim().slice(0, 400),
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
    if (!payload || !payload.grant) {
      // W1: NOT a silent `continue`. The mint SUCCEEDED (no throw) and still handed back no grant
      // — the grant-hoist filter above is the known cause, and until this line existed the seat
      // simply vanished from the pass with nothing anywhere saying why.
      if (logger) {
        logger({
          level: 'info',
          message: 'seat NOT retried — `coordinate seat-retry --mint` returned no grant on the wire',
          seat: row.seat,
          outcome,
          evidence: `session ${rec['session-id'] || '(none)'} · payload ${JSON.stringify(payload)}`.slice(0, 400),
        });
      }
      continue;
    }
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
// by a daemon restart — the same conservative direction `goal-stall-alarm.js`'s own dedup Map
// discloses (a duplicate notice after a restart beats a freeze the memo silently remembers past
// the life of the process that decided it).
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
// ── W2 — `done` AND `blocked` NO LONGER COME OUT OF THE RECORD ────────────────────────────────
//
// `readyRows` is coord's `ready-seats --json` answer, handed in by the caller that already paid for
// it (ONE subprocess per goal per pass — see `readySeats`). Two of the four sets below now read it
// instead of the record's `outcome` column:
//
//   done      the seat's CHECK-OUT DISPOSITION is `done` — the seat's own word for its own work,
//             which is the only surface that ever knew it. The record's `outcome` column cannot
//             answer this any more and never honestly could: it said `done` for a seat that
//             fail-blocked, because it was derived from a process exiting 0.
//   blocked   coord's `HELD` verdict — a seat with an unanswered ask to the owner. UNIVERSAL: no
//             `fallback: block-and-queue` gate and no ferry-delivery gate, both of which were the
//             root cause of the original silent stall. The map's VALUE is coord's own reason
//             string, so this file states nothing about why a seat is held.
//
// `foreign` and the OPEN half of `notFinished` still come from the record, because they are facts
// about PROCESSES and lanes, which is exactly what the record now carries.
//
// ⚠ `readyRows` ABSENT DEGRADES TO "NOTHING IS DONE, NOTHING IS HELD", never to the old column
// read. Two callers pass none today — the `--status` verb on a goal whose readiness coord refused,
// and any caller written before this parameter. Both directions of a wrong guess are unsafe, but
// they are not equally unsafe: an empty `done` set makes a finished seat merely look unfinished,
// and the STORE's own no-double-fire guard (`seatHasRun`) plus `foreign` still stop it being
// re-run. Reading the stale column instead would advance a wave off a value the migration
// deliberately left inert (adv, C-migration: old `outcome` values are inert, files are NOT
// rewritten).
function recordView(heartStore, goalFolder, { relaunch = null, readyRows = null } = {}) {
  const rows = readExecutionRecord(goalFolder).rows;
  const done = new Set();
  const foreign = new Map();
  const notFinished = new Map();
  const blocked = new Map();
  // THE ATTESTATION, read first and independently of the record: a seat can carry a disposition
  // with no record row at all (the measured `forg-intake` shape — a daemon execution that wrote no
  // `sessions.csv`, and its mirror, a seat coord knows about that this record never saw).
  for (const r of readyRows || []) {
    if (!r || !r.seat) continue;
    if ((r.disposition || '').trim() === 'done') done.add(r.seat);
    if (r.verdict === 'HELD') {
      blocked.set(r.seat, r.reason || 'coord reports HELD — an unanswered ask to the owner');
      notFinished.set(r.seat, blocked.get(r.seat));
    }
  }
  if (!rows.length) {
    const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));
    for (const seat of withFileGrants(relaunch, goalFolder)) {
      finished.delete(seat); done.delete(seat); notFinished.delete(seat); blocked.delete(seat);
    }
    return { done, finished, foreign, notFinished, blocked };
  }
  // THE GRANT IS SOURCED HERE, not handed in — see `relaunch-grants.js`. A caller-supplied set is
  // still honoured (`--relaunch` argv, and any grant a caller minted for this pass); the goal
  // folder's own file is FOLDED IN rather than used as a fallback, because a pass that already
  // carries one kind of grant must not swallow the operator's.
  const grants = withFileGrants(relaunch, goalFolder);

  // The seat's LAST row, in file order — the record is append-only, so the last row for a seat is
  // its most recent execution. `failed`/`killed` are terminal words that were never `done`; they
  // keep the behaviour they had (the seat is not done and an explicit grant re-runs it), so only
  // the two non-finishes below are collected here.
  // The seat's LAST row, in file order — the record is append-only, so the last row for a seat is
  // its most recent execution. ⚠ ONLY THE **OPEN** CASE IS COLLECTED HERE NOW. The `blocked` arm
  // that stood beside it read the record's outcome column, and W2 deleted that word from this
  // vocabulary: a held seat is coord's `HELD` verdict, folded in above. Every terminal process word
  // (`clean`/`crashed`/`killed`) is silent here, exactly as `failed`/`killed` always were — the
  // seat is not done, and its done-ness is decided by its disposition, not by how its process ended.
  const last = new Map();
  for (const r of rows) last.set(r.seat, r);
  for (const [seat, r] of last) {
    if (!(r.outcome || '').trim()) {
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
    // ⚠ THE `done` BRANCH THAT STOOD HERE IS GONE AND ITS ABSENCE IS THE WHOLE REPOINT. It read
    // `outcome === 'done'` and both ADDED to `done` and skipped the foreign test. Done-ness is the
    // disposition now (folded in at the top), and the foreign test is applied to every row on its
    // own merits — a seat coord attests `done` has its foreign hold cleared below, by the same
    // `finished` deletion that always cleared it.
    if (ours.has(r['session-id'])) continue;            // our own store already governs this one
    foreign.set(r.seat, outcome
      ? `ended '${outcome}' in the ${r.lane || 'other'} lane (session ${r['session-id']})`
      : `still OPEN in the ${r.lane || 'other'} lane (session ${r['session-id']})`);
  }
  // ── `finished` — "IS THIS SEAT DONE **NOW**", AND THE ONE ANSWER EVERY OUTRANKING TEST TAKES ──
  //
  // ⚠ THIS SET EXISTS BECAUSE `done` AND `notFinished` ARE INDEPENDENT, AND EVERY TEST THAT USED TO
  // WRITE `done.has(seat)` MEANT THIS. Since W2 the two come from DIFFERENT SURFACES, which makes
  // the independence structural rather than incidental: `done` is the seat's CHECK-OUT DISPOSITION
  // on coord's answer, `notFinished` is the record's last row (still OPEN) plus coord's `HELD`
  // verdict. A seat can carry both at once and it is the ordinary case — it checked out `done` on
  // an earlier turn and something is running for it now, or it checked out `done` with a question
  // to the owner still unanswered. Review findings F1 and F2 were both that gap, at the two call
  // sites below — the review's own words, a signature change that did not sweep its callers.
  //
  //   F1 (HIGH): the relaunch grant bailed on `done.has(seat)`, so `--relaunch` was a NO-OP for a
  //   seat held on its SECOND ask (`blocked, done, blocked`) — the documented escape did nothing
  //   and hand-editing `executions.csv` was the only way out of a permanently stuck wave.
  //   F2: the `foreign` deletion did the same, so a crashed foreign revival (`done, open`) was
  //   reported by NOTHING while `skippedAsFinished` called it finished and `states` called it live.
  //
  // Computed BEFORE the grant's deletes, so a grant can never make a seat read finished.
  const finished = new Set([...done].filter((seat) => !notFinished.has(seat)));

  // An attested `done` clears a foreign hold — the seat IS finished, and the lane that ran it is
  // nobody's business at that point. But only while nothing outranks the attestation: an OPEN
  // record row, or coord's `HELD`, is the seat's current state and `finished` above already
  // excluded it.
  for (const seat of finished) foreign.delete(seat);
  // The one-shot relaunch grant releases a foreign hold exactly as it releases a local failure —
  // and, exactly as there, it can never release a FINISHED seat. It releases the record's last-word
  // hold too: an operator saying "run this seat again" is the same explicit act, and the answer
  // that would otherwise release it is the one thing he is saying will not come.
  // ⚠ THE `if` IS NOT DEAD FLEXIBILITY. It survives a history worth keeping: sourcing the grant from
  // a file made the old `if (relaunch)` wrapper unnecessary, and dropping it re-indented these lines
  // by two columns — which silently un-anchored the exact-text mutation site that then guarded them
  // (`probe-block-and-queue-hold.js`, mutant `grant`). That mutant reported "0 file(s) carry the
  // mutation site" and its arm went vacuous, which is the failure mode this note exists to name.
  // ⚠ W2 RETIRED THAT PROBE WITH THE HOLD IT MEASURED, so THE INDENTATION IS NO LONGER LOAD-BEARING
  // and nothing pins this line's exact text any more. What guards the BEHAVIOUR instead is
  // `probe-relaunch-grant.js` LEG 5, as a control/treatment pair (ungranted vs granted) rather than
  // as a source mutation — which is the sturdier anchor, because it cannot be un-anchored by
  // reformatting. Do not re-introduce an exact-text pin here without also re-introducing the
  // "0 file(s) carry the mutation site" check that would catch it going vacuous.
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
  suppressedEnqueues = null,
}) {
  // The goal folder's own grant file, folded into whatever the caller supplied (see
  // `withFileGrants`). Every use of the grant below reads `grants`, never `relaunch`, so the
  // predicate answers the same way on both lanes with no caller having to know the file exists.
  const grants = withFileGrants(relaunch, goalFolder);
  const byJob = executionsByJob(heartStore, grants, goal);
  const queued = new Set(heartStore.listQueue().map((q) => q.job_id));
  const { done: finished, foreign, notFinished, blocked } = view || recordView(heartStore, goalFolder, { relaunch: grants, readyRows });
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
      // ⚠ THE WORD IS `HELD`, NOT `BLOCKED` (adv, C82). `ready-seats` already spells `BLOCKED` for
      // "an `after` member is unsatisfied", and the two are different things — a message calling
      // this one BLOCKED sends an operator to the DAG when the answer is a person.
      logger({ level: 'info', message: 'seat HELD — an unanswered ask to the owner, and its dependents wait with it', seat: row.seat, evidence: blocked.get(row.seat) });
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
    if (isHeld && isHeld(row.seat)) {
      if (logger) {
        logger({
          level: 'info',
          message: 'seat NOT enqueued — held for human-interactive detach (dispatched through the foreground carrier or not at all)',
          seat: row.seat,
        });
      }
      continue;
    }

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
      // D2 (2026-08-19): the composition root's ONE workspace-root resolution, threaded via the
      // store (`engine/index.js` assigns it off the spawn manager) — the gate needs it to judge
      // workspace-grammar declared outputs (`.rbtv/mirror/…`) against the same root the spawner
      // resolves rw grants against.
      workspaceRoot: heartStore.config?.workspaceRoot || null,
    });
    if (refusal) {
      if (logger) logger({ level: 'warn', message: 'seat NOT enqueued — a declared output is inadmissible for a caged launch', seat: row.seat, evidence: refusal });
      surfaceCageRefusal(goalFolder, row.seat, refusal, logger);
      continue;
    }
    // ── D5 (seed-gates, 2026-08-19): LANE REACH, the refusal beside the one above ──────────────
    // Could this seat's declared probe lane RUN once caged? The stools DoD judge burned two waves
    // landing in cages where `stools workspaces` exited 127 — the requirement was written in four
    // prose surfaces and read by nothing. It is now machine-readable in the seat's io-spec
    // (`## Requires-reach`) and refused HERE, through the same log + bus surfacing as its sibling.
    // The gate checks REACH (declaration/bind present), never behavior (`exit 0`) — see
    // `cage-admission.js#admitLaneReach` for the honest limit.
    const reachRefusal = admitLaneReach({
      seatBinds: seatBindsFor(row.seat), goalFolder, seat: row.seat,
      workspaceRoot: heartStore.config?.workspaceRoot || null,
    });
    if (reachRefusal) {
      if (logger) logger({ level: 'warn', message: 'seat NOT enqueued — its declared lane reach is not satisfied by the composed cage', seat: row.seat, evidence: reachRefusal });
      surfaceCageRefusal(goalFolder, row.seat, reachRefusal, logger);
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
          '--as', 'ignite-daemon',
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
    // BOTH spend points are needed: this one covers the seedGoal-only paths (lane-watch, the
    // attached engine — no ticker, so spawn's `spendCoordTwin` never fires for them), and
    // spawn-dispatch `spendCoordTwin` covers the ticker path as a dup-safe backstop.
    if (grants.delete(row.seat)) spendGrant(goalFolder, row.seat);

    const after = (row.after || '').trim();
    const seatDir = path.join(goalFolder, 'seats', row.seat);
    const seed = (ready && ready.get(row.seat)) || [];
    const enq = heartStore.enqueue({
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
    if (enq && enq.deduped) {
      if (suppressedEnqueues) {
        suppressedEnqueues[row.seat] = `${enq.because} — queue_id=${enq.queue_id} exec_id=${enq.exec_id} held_status=${enq.held_status}`;
      }
      if (logger) {
        logger({
          level: 'warn',
          message: 'store SUPPRESSED the enqueue — the seat was not queued',
          seat: row.seat,
          because: enq.because,
          queue_id: enq.queue_id,
          exec_id: enq.exec_id,
          held_status: enq.held_status,
        });
      }
      continue;
    }
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
function seedGoal({ heartStore, goalFolder, goal, logger = null, isHeld = null, relaunch = null, readLease = deriveLease }) {
  if (!goal) {
    throw new Error(
      'seedGoal requires the goal NAME: it namespaces the job ids so two goals with a seat of the ' +
      'same name cannot share one job row in a store that holds every goal (the daemon\'s).'
    );
  }
  // ── D9 (seed-gates, 2026-08-19): THE GOAL-LIVE CHECK, BEFORE ANYTHING IS SPENT ──────────────
  // The measured failure (G-leader-0818-1830, meet-transcript-summarizer): two relaunch grants
  // burned with no session row to show for them. The spend lives in this function's ready-row
  // loop (`seat-retry --spend`, then `spendGrant`) while the goal-live refusal (`E_GOAL_NOT_LIVE`)
  // fired LATER and elsewhere — at the ticker's dispatch, in `spawn.js` — so every pass paid the
  // one-shot grant for a launch the spawn door was always going to refuse. The SAME lease, at the
  // SAME threshold, is therefore read HERE FIRST: `deriveLease().live` is the ROOM's existence
  // (never the stricter occupant set — a room mid-relaunch between seat boots must still seed).
  // Not live → one log line, one bus row (the D2 surfacing, keyed by the goal name), and a return
  // with NOTHING enqueued and NOTHING spent; the next cadence retries for free.
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
      return {
        goalFolder, goal, seats: readTaskforce(goalFolder).map((r) => r.seat), enqueued: [], seeds: {},
        skippedAsFinished: [], heldByOtherLane: {}, blockedOnOwner: {}, heldByStore: {}, states: {},
        readinessRefused: null, goalNotLive: notLive, skewed: [], frozen: null,
        suppressedEnqueues: {}, enqueueUnfired: [],
      };
    }
  }
  try {
    const { ensureRoomSelfheal } = require('./ensure-room-selfheal');
    ensureRoomSelfheal({ heartStore, goal, goalFolder, logger });
  } catch (err) {
    if (logger) {
      logger({
        level: 'warn',
        message: 'room selfheal auto-arm failed — seeding continues',
        goal,
        error: err && err.message,
      });
    }
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
      // A refusal computed no rows, so it names no skewed seat. The owner alarm reads
      // `readinessRefused` for this arm — see the `skewed` note on the success return below.
      skewed: [], frozen: null, suppressedEnqueues: {}, enqueueUnfired: [],
    };
  }
  // Q2a — THE SKEW IS STILL LOUD; IT JUST NO LONGER STOPS THE GOAL (owner-ruled 2026-08-18).
  // Before the ruling a skew reached a human (if at all) as the refusal above, which got a `warn`
  // with its evidence. It now arrives as an ordinary row and the goal seeds around it — so without
  // this line the one thing on the pass that a human MUST adjudicate would be the only thing
  // nothing says out loud, and "quieter" was never part of the ruling. Every pass, naming the
  // seats: it is a standing condition that lifts only when someone rules on the row.
  const skewed = (readyRows || []).filter((r) => r && r.verdict === 'SKEW');
  if (skewed.length && logger) {
    logger({
      level: 'warn',
      message: 'seat disposition SKEW — the two records of that seat\'s own ending DISAGREE, so it and its '
        + 'dependents advance on neither until a human rules. The REST of the goal is seeded normally.',
      goal,
      goalFolder,
      evidence: skewed.map((r) => `${r.seat}: ${r.reason}`).join('  ·  '),
    });
  }
  // THE RETRY PASS, between coord's answer and anything this store writes (task 7.776). It mints
  // against the record `recordView` reads, so the two agree by construction about which seats are
  // finished — and a fresh mint FLIPS that seat's coord verdict from `DONE` to `READY`, which is
  // why `ready-seats` is asked a SECOND time when and only when something was minted. Once per
  // pass, never in a loop: a mint that changes no verdict changes none on the second read either.
  let view = recordView(heartStore, goalFolder, { relaunch, readyRows });
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
    view = recordView(heartStore, goalFolder, { relaunch, readyRows });
  }
  seedTaskforce(heartStore, goalFolder, { logger, goal, rows });
  const heldByStore = {};
  const suppressedEnqueues = {};
  const enqueued = enqueueEligible(heartStore, rows, { goalFolder, logger, goal, view, isHeld, relaunch, ready, readyRows, granted, heldByStore, suppressedEnqueues });
  const unfiredCutoff = new Date(Date.now() - ENQUEUE_UNFIRED_GRACE_MS).toISOString().replace(/\.\d{3}Z$/, 'Z');
  const enqueueUnfired = heartStore.listEnqueueUnfired(goal, unfiredCutoff).map((r) => ({
    seat: r.seat, because: r.because, at: r.at,
  }));
  // WITH the grant set, since the loop re-fire (2026-08-12): the `states` report below must agree
  // with the enqueue decision above, and a granted `done` seat is dispatchable again — reporting
  // it `done` off a grant-blind read is the same one-report-contradicting-the-other defect F2
  // fixed for `skippedAsFinished`.
  const byJob = executionsByJob(heartStore, relaunch, goal);
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
  const deadSeats = new Set((readyRows || []).filter((r) => r && r.dead).map((r) => r.seat));
  const moving = seats.some((s) => states[s] === 'live' || states[s] === 'queued');
  const pendingUnseeded = (ready.size || moving) ? []
    : seats.filter((s) => states[s] !== 'done' && !deadSeats.has(s));
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
    // ⚠ THE SAME `skewed` THE WARN ABOVE NAMED, RETURNED RATHER THAN RE-DERIVED (owner alarm,
    // Q3a). The daemon's owner alarm (`server/ticker/goal-stall-alarm.js`) fires on an unresolved
    // SKEW, and it must fire on the set THIS pass acted on. A second filter over `readyRows` in
    // the caller would be free to disagree with the one that decided what to dispatch — the defect
    // class this codebase has closed twice. One computation, one consumer per surface.
    skewed,
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
    suppressedEnqueues,
    enqueueUnfired,
    enqueued,
    // LE-13, computed above: the empty-frontier freeze, shaped for the owner alarm
    // (`goal-stall-alarm.js#conditionOf` reads it first). `null` is the ordinary case.
    frozen: pendingUnseeded.length ? {
      kind: 'seeding-empty',
      seats: pendingUnseeded,
      // D22: THE EXCLUDED-DEAD COUNT IS PART OF THE ALARM, not a debug line — this string is what
      // reaches the owner over Slack (`server/ticker/goal-stall-alarm.js`), and a reader who
      // cannot see how many rows were discounted cannot audit the alarm that discounted them.
      detail: '`ready-seats` ruled NO seat READY (of ' + readyRows.length + ' row(s) answered, '
        + deadSeats.size + ' of them DEAD by design and excluded) while these taskforce seats are pending — coord ruled on nothing dispatchable, so nothing can be seeded',
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
  // Exported for `probes/probe-relaunch-grant.js` LEG 10 ONLY: the mint has to be driven as its own
  // step there, because the grant it writes is SPENT again inside the same `seedGoal` call — the
  // READY-via-grant verdict the leg discriminates on exists only between the two.
  mintRetryGrants,
  enqueueEligible,
  // Exported for `engine/probes/probe-cage-workspace-grammar.js`: the refusal->bus wire, driven
  // against a fixture goal without standing up the whole enqueue path.
  surfaceCageRefusal,
  seedGoal,
};
