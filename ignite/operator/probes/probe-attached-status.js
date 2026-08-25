'use strict';

// probe-attached-status — the ORIENTATION verb (`rbtv run <goal> --status`), console-run wave A
// item A3.
//
// WHAT IT GUARDS, and why each arm exists rather than being obvious:
//
//  1. THE VERB IS READ-ONLY, INCLUDING THE STORE. Opening a heart store CREATES and migrates it.
//     A status call before the first run would therefore leave a `heart.db` behind, and after that
//     "has this goal ever run?" is unanswerable from disk forever. The arm compares a full
//     directory listing before and after.
//  2. THE WAVE MATH IS THE ENGINE'S. `seatState` is the ONE predicate; `launchOwed` and the
//     status verb both go through it. A second copy is a status surface that can disagree with the
//     engine it reports on — the arm asserts the ready set the status verb prints is exactly the
//     set the enqueue pass fires.
//  3. HELD-FOR-USER IS TWO GATES, NOT ONE (console-run design ruling 5 / D14). The seat declares
//     `human-interactive:` AND the goal's execution mode is `interactive`. Each gate is measured
//     WITH THE OTHER HELD OPEN, so an arm that passes because the other gate happened to close is
//     impossible: flipping execution-mode alone must empty the held set while the seat flag stays.
//  4. A NON-GOAL FOLDER AND A SEATLESS GOAL REFUSE, and they refuse DIFFERENTLY.
//
// Self-contained: builds a throwaway goal tree under the OS temp dir, no daemon, no ports, no
// network. Exit code is the truth; the .out footer is a hint.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-attached-status.out');
const lines = [];
const emit = (s) => { lines.push(s); };

const attached = require('../attached-execution');
const failures = [];
function check(name, ok, detail) {
  emit(`${ok ? 'ok  ' : 'FAIL'} ${name}${ok || detail === undefined ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(name);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-attached-status-'));
const goalFolder = path.join(tmp, '.rbtv', 'goals', 'demo-goal');
fs.mkdirSync(path.join(goalFolder, 'seats', 'alpha'), { recursive: true });
fs.mkdirSync(path.join(goalFolder, 'seats', 'beta'), { recursive: true });
fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'),
  'taskforce-id,seat,after\ntf-1,alpha,\ntf-1,beta,alpha\n');
// alpha declares itself human-interactive; beta does not. The two seats differ in exactly that
// one field, so an arm that fires on both is measuring something else.
fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'),
  '---\nseat: alpha\nhuman-interactive: yes\nfallback: block-and-queue\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'beta', 'seat.md'),
  '---\nseat: beta\n---\n\nbody\n');
fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');

function listing(dir) {
  const out = [];
  const walk = (d, rel) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const p = path.join(d, e.name);
      out.push(path.join(rel, e.name));
      if (e.isDirectory()) walk(p, path.join(rel, e.name));
    }
  };
  walk(dir, '');
  return out.join('\n');
}

emit('— A3: the status verb —');

const before = listing(goalFolder);
const st = attached.statusAttached({ goalFolder });
const after = listing(goalFolder);

check('a goal that has never run still reports, and says so', st.everRun === false && st.storePath === null,
  JSON.stringify({ everRun: st.everRun, storePath: st.storePath }));
check('READ-ONLY: no heart.db, no file at all, created by a status call', before === after,
  `before=${before.split('\n').length} after=${after.split('\n').length}`);
check('done / ready / next / waiting are computed from the after column',
  st.done.length === 0 && st.ready.join() === 'alpha' && st.next.join() === 'alpha'
  && st.waiting.join() === 'beta', JSON.stringify(st));

// ARM 2 — the status verb's ready set IS the enqueue pass's, measured through the shared
// predicate rather than by re-deriving it here (which would only prove this file agrees with
// itself). A fake store stands in: the enqueue pass needs a store, the predicate does not.
//
// ⚠ THE FRONTIER IS COORD'S SINCE § D1 (`one-readiness-predicate.md`), so it is HANDED to the
// predicate here exactly as the status verb and the enqueue pass hand it: `readySeats` is the ONE
// reader, and what this arm measures is that all three consumers get the same answer out of it.
const { readySeats } = require('../../supervisor/seeding');
const byJob = new Map();
const queued = new Set();
const rows = [{ seat: 'alpha', after: '' }, { seat: 'beta', after: 'alpha' }];
const frontier = () => {
  const dbPath = path.join(goalFolder, 'heart.db');
  if (!fs.existsSync(dbPath)) return readySeats(goalFolder).ready;
  const { openHeartStore, closeHeartStore } = require('../../state-store/heart/heart-store');
  const hs = openHeartStore({ dbPath });
  try { return readySeats(goalFolder, { heartStore: hs, goal: path.basename(goalFolder) }).ready; }
  finally { hs.close(); closeHeartStore(); }
};
check('the ready set is the ONE eligibility predicate, shared with the enqueue pass',
  rows.filter((r) => attached.seatState(r, byJob, queued, { ready: frontier() }) === 'ready')
    .map((r) => r.seat).join() === st.ready.join());
// … and it MOVES when alpha CHECKS OUT `done` — the seat's own declaration, which is the only
// thing that advances an edge now. A store turn is a fact about a process and advances nothing:
// the `byJob` row below says alpha's execution finished, and beta moves because of the CHECK-OUT
// beside it, not because of that.
fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
  'session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,pid-starttime,tty,'
  + 'disposition,disposition-writer,execution,checkin,model\n'
  + 'sid-alpha,alpha,claude,,,,2026-08-11T10:00Z,2026-08-11T10:05Z,,,,done,seat,,,\n');
// ⚠ THE STAMP GOES TO THE STORE'S OWN HOME, NOT TO THE LANE STORE THIS FIXTURE HOLDS OPEN.
// spec-state-store §1.1 puts the ONE ending store at `<workspace>/.rbtv/runtime/ignite/heart.db`
// (never per-goal, never `{state_root}` after cutover), and `supervisor/ending-reads.js#bindEnding`
// derives exactly that path from the goal folder. A fixture stamping `heartStore.db` is writing a
// file no reader consults.
{
  const store = require('../../state-store');
  store.bind(store.openEndingStoreFor(path.resolve(goalFolder, '..', '..', '..'))).stampSeatDeclare({
    goal: path.basename(goalFolder), seat: 'alpha', ending: 'done',
    evidence_pointer: 'probe-attached-status', declared_outputs: [], replace: true,
  });
}
byJob.set(attached.jobIdFor('alpha'), [{ status: 'done' }]);
const advanced = frontier();
check('a CHECKED-OUT predecessor releases its dependent (the wave advances)',
  attached.seatState(rows[0], byJob, queued, { ready: advanced }) === 'done'
  && attached.seatState(rows[1], byJob, queued, { ready: advanced }) === 'ready');
// The DISCRIMINATOR, and it is the whole design: the same store turn with the check-out taken
// away leaves the dependent WAITING. Without this the arm above would pass on a predicate that
// simply read the store's `done` row, which is what it did before § D1.
fs.writeFileSync(path.join(goalFolder, 'sessions.csv'),
  'session-id,seat,harness,native-session-id,workdir,recorded,started,ended,pid,pid-starttime,tty,'
  + 'disposition,disposition-writer,execution,checkin,model\n'
  + 'sid-alpha,alpha,claude,,,,2026-08-11T10:00Z,2026-08-11T10:05Z,,,,,,,,\n');
// ⚠ TAKING THE CHECK-OUT AWAY IS NOW TWO ACTS, and the second one is raw SQL on purpose. It used
// to be `unlink(<goal>/heart.db)` — the per-goal store the ending was stamped into. Since §1.1 the
// ending lives at the workspace home, which this fixture must NOT delete (the handle is open, and
// unlinking under sqlite leaves the reader on the old inode reading the row it was meant to lose).
// There is no API for this because PRODUCTION NEVER UN-DECLARES an ending: a new sitting REPLACES
// the row, it does not blank it. The state being modelled — no current row at all — is the absence
// §1.1 calls "no declared ending", so the fixture removes the row directly and says why.
{
  const store = require('../../state-store');
  store.openEndingStoreFor(path.resolve(goalFolder, '..', '..', '..'))
    .prepare('DELETE FROM seat_endings WHERE goal = ? AND seat = ?')
    .run(path.basename(goalFolder), 'alpha');
}
check('…and with the SAME store turn but NO check-out, the dependent stays WAITING (UNDECLARED)',
  attached.seatState(rows[1], byJob, queued, { ready: frontier() }) === 'waiting');
fs.unlinkSync(path.join(goalFolder, 'sessions.csv'));

// ARM 3 — the two gates, each measured with the other held OPEN.
check('gate A+B open: a human-interactive seat in an interactive goal is HELD FOR USER',
  st.heldForUser.join() === 'alpha', JSON.stringify(st.heldForUser));
fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'autonomous\n');
const stAuto = attached.statusAttached({ goalFolder });
check('gate B closed ALONE (seat flag untouched): held set empties',
  stAuto.heldForUser.length === 0
  && stAuto.seats.find((s) => s.seat === 'alpha').humanInteractive === true,
  JSON.stringify(stAuto.heldForUser));
fs.unlinkSync(path.join(goalFolder, 'execution-mode'));
check('an ABSENT execution-mode reads as autonomous (the ratified default), so nothing is held',
  attached.statusAttached({ goalFolder }).heldForUser.length === 0);
fs.writeFileSync(path.join(goalFolder, 'execution-mode'), 'interactive\n');
fs.writeFileSync(path.join(goalFolder, 'seats', 'alpha', 'seat.md'), '---\nseat: alpha\n---\n\nbody\n');
check('gate A closed ALONE (goal still interactive): held set empties',
  attached.statusAttached({ goalFolder }).heldForUser.length === 0);

// ARM 4 — ANSWERED asks stop being listed; unanswered ones do not.
//
// Asks and answers correlate only by `thread` — nothing marks the ask row itself — so an
// answered question printed under UNANSWERED QUESTIONS forever, which trains the reader to
// ignore the one section written to be read. Driven through the real `messages` shape
// (server/heart/schema.sql), ordered by msg_id as the store's own dump returns them.
const msgs = [
  { msg_id: 1, type: 'ask', sender: 'alpha', thread: 'exec-1', corpus: 'answered question' },
  { msg_id: 2, type: 'answer', sender: 'owner', thread: 'exec-1', corpus: 'here you go' },
  { msg_id: 3, type: 'ask', sender: 'beta', thread: 'exec-2', corpus: 'still waiting' },
  { msg_id: 4, type: 'note', sender: 'beta', thread: 'exec-2', corpus: 'unrelated chatter' },
];
const open1 = attached.unansweredAsks(msgs);
check('an ANSWERED ask is not listed, and the unanswered one still is',
  open1.map((a) => a.msgId).join() === '3', JSON.stringify(open1));
check('a `note` on the thread does NOT count as an answer',
  open1.length === 1 && open1[0].corpus === 'still waiting', JSON.stringify(open1));
// TWO asks, ONE answer, same thread. The cheap test ("an answer exists on this thread")
// would call both answered — erring toward HIDING an unanswered question, the one direction
// this surface must never err in.
const open2 = attached.unansweredAsks([
  { msg_id: 1, type: 'ask', sender: 'a', thread: 't', corpus: 'first' },
  { msg_id: 2, type: 'ask', sender: 'a', thread: 't', corpus: 'second' },
  { msg_id: 3, type: 'answer', sender: 'owner', thread: 't', corpus: 'answers the first' },
]);
check('two asks and one answer on one thread leaves the SECOND ask open',
  open2.map((a) => a.corpus).join() === 'second', JSON.stringify(open2));
check('an answer on a DIFFERENT thread answers nothing',
  attached.unansweredAsks([
    { msg_id: 1, type: 'ask', sender: 'a', thread: 't1', corpus: 'q' },
    { msg_id: 2, type: 'answer', sender: 'owner', thread: 't2', corpus: 'a' },
  ]).length === 1);

// ARM 5 — the two refusals, and they are DIFFERENT refusals.
function refusal(fn) {
  try { fn(); return null; } catch (err) { return err.message; }
}
const notGoal = refusal(() => attached.statusAttached({ goalFolder: tmp }));
check('a NON-goal folder refuses, naming the goal-folder shape',
  Boolean(notGoal) && notGoal.includes('is not a goal folder'), String(notGoal));
const seatless = path.join(tmp, '.rbtv', 'goals', 'seatless');
fs.mkdirSync(seatless, { recursive: true });
const noTf = refusal(() => attached.statusAttached({ goalFolder: seatless }));
check('a goal with NO taskforce refuses differently, naming the missing file',
  Boolean(noTf) && noTf.includes('no taskforce') && !noTf.includes('is not a goal folder'), String(noTf));

fs.rmSync(tmp, { recursive: true, force: true });

const exitCode = failures.length ? 1 : 0;
emit('');
emit(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the status verb orients read-only, shares the engine\'s one eligibility predicate, and holds a seat only when BOTH ruling-5 gates are open.');
emit(`WALL_MS ${Date.now() - start}`);
emit(`EXIT ${exitCode}`);
fs.writeFileSync(outPath, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);
