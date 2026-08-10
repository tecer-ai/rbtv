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
//  2. THE WAVE MATH IS THE ENGINE'S. `seatState` is the ONE predicate; `enqueueEligible` and the
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
const byJob = new Map();
const queued = new Set();
const rows = [{ seat: 'alpha', after: '' }, { seat: 'beta', after: 'alpha' }];
check('the ready set is the ONE eligibility predicate, shared with the enqueue pass',
  rows.filter((r) => attached.seatState(r, byJob, queued) === 'ready').map((r) => r.seat).join() === st.ready.join());
// … and it MOVES when the store says alpha finished: beta becomes ready, alpha done.
byJob.set(attached.jobIdFor('alpha'), [{ status: 'done' }]);
check('a finished predecessor releases its dependent (the wave advances)',
  attached.seatState(rows[0], byJob, queued) === 'done'
  && attached.seatState(rows[1], byJob, queued) === 'ready');

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

// ARM 4 — the two refusals, and they are DIFFERENT refusals.
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
