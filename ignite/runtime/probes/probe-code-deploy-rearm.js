'use strict';

// probe-code-deploy-rearm — spec-recovery §5's `code-deploy`, the first of the four named re-arm
// events to have a producer (`runtime/code-deploy-rearm.js`).
//
// WHAT IT IS PROVING, and why each arm exists. Before this wiring, `counters.rearm` had exactly one
// caller and that caller had none: a driver that reached N was disarmed FOREVER, through every
// restart and every deploy (seven lanes on the live instance, 2026-08-27). The three arms that
// matter are therefore (1) a DEPLOY re-arms every row and says so, (2) an ordinary RESTART re-arms
// NOTHING — otherwise the counter is back to the unbounded retry it replaced, since restarting is
// the owner's own remedy for a stuck daemon — and (3) the pass is actually CALLED at boot, before
// the marker that holds the previous digest is overwritten.
//
// NO DAEMON, NO LIVE STATE. Workspace and counter ledger are both throwaway temp dirs; the module
// default counters path (the daemon's own live ledger) is never touched.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const counters = require('../../supervisor/attempt-counters');
const { writeCodeMarker, readCodeMarker } = require('../code-fingerprint');
const { rearmOnCodeDeploy } = require('../code-deploy-rearm');

const OUT = path.join(__dirname, 'probe-code-deploy-rearm.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const fp = (digest, files = 42) => ({ digest, files, captured_at: '2026-08-27T00:00:00Z', entries: { 'x.js': digest } });

function fresh() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'code-deploy-rearm-'));
  const countersFile = path.join(root, 'counters', 'attempt-counters.json');
  const lines = [];
  const log = (level, message, fields) => lines.push({ level, message, fields });
  return { root, countersFile, lines, log };
}

// Two exhausted lanes and one that is only part-way, written through the real driver api.
function seedCounters(countersFile) {
  const rows = [
    { goal: 'goal-a', seat: 'leader', reasonClass: 'nonterm', times: 3 },
    { goal: 'goal-a', seat: 'leader', reasonClass: 'unread', times: 5 },
    { goal: 'goal-b', seat: 'plan-drafter', reasonClass: 'nonterm', times: 3 },
    { goal: 'goal-b', seat: 'leader', reasonClass: 'room', times: 1 },
  ];
  for (const r of rows) {
    for (let i = 0; i < r.times; i += 1) {
      counters.countAttempt({
        driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: r.goal, seat: r.seat, reasonClass: r.reasonClass, n: 3,
      }, { countersFile });
    }
  }
  return counters.listCounters({}, { countersFile });
}

// ── A. A DEPLOY: this boot's code differs from the recorded one ────────────────────────────────
{
  const { root, countersFile, lines, log } = fresh();
  const seeded = seedCounters(countersFile);
  writeCodeMarker(root, fp('old-narrow'), fp('OLD-WIDE'));

  const out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: fp('NEW-WIDE'), log }, { countersFile });
  const after = counters.listCounters({}, { countersFile });

  check('A1: the fixture had four counter rows, two of them at N=3 (a real disarmed pair, not a shape)',
    seeded.length === 4 && seeded.filter((r) => r.attempts >= 3).length === 3,
    { rows: seeded.map((r) => `${r.subject}/${r.reason_class}=${r.attempts}`) });

  check('A2: a changed digest FIRES `code-deploy` and clears every counter row',
    out.fired === true && out.why === 'code-changed' && after.length === 0 && out.cleared.length === 4,
    { fired: out.fired, why: out.why, cleared: out.cleared.length, left: after.length });

  const per = lines.filter((l) => /^re-armed by code-deploy: /.test(l.message));
  check('A3: ONE `info` per cleared row, carrying subject, class and the count it was cleared from',
    per.length === 4 && per.every((l) => l.level === 'info')
      && per.some((l) => l.message === 're-armed by code-deploy: goal-a/leader nonterm (was N=3)')
      && per.some((l) => l.message === 're-armed by code-deploy: goal-a/leader unread (was N=5)'),
    { lines: per.map((l) => l.message) });

  check('A4: and the previous/new digests are journalled, so the decision is auditable after the fact',
    lines.some((l) => l.message === 'code-deploy re-arm fired' && l.fields.previous_digest === 'OLD-WIDE' && l.fields.digest === 'NEW-WIDE'),
    { fields: (lines.find((l) => l.message === 'code-deploy re-arm fired') || {}).fields });

  // The recording of the new digest is the marker's own existing write — no second ledger.
  writeCodeMarker(root, fp('new-narrow'), fp('NEW-WIDE'));
  const marker = readCodeMarker(root);
  check('A5: the new digest is RECORDED on the boot marker, so the next boot compares against it',
    marker.deploy.digest === 'NEW-WIDE' && marker.code.digest === 'new-narrow',
    { deploy: marker.deploy.digest, code: marker.code.digest });
}

// ── B. A RESTART: same bytes, same digest ──────────────────────────────────────────────────────
{
  const { root, countersFile, lines, log } = fresh();
  seedCounters(countersFile);
  writeCodeMarker(root, fp('narrow'), fp('SAME-WIDE'));

  const out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: fp('SAME-WIDE'), log }, { countersFile });
  const after = counters.listCounters({}, { countersFile });

  check('B1: an ordinary restart re-arms NOTHING — the same bytes are not a deploy',
    out.fired === false && out.why === 'unchanged' && after.length === 4,
    { fired: out.fired, why: out.why, left: after.length });

  check('B2: and it is silent about it — a restart that journalled a re-arm would train the reader to ignore the real one',
    lines.length === 0, { lines: lines.map((l) => l.message) });

  const still = counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'goal-a', seat: 'leader', reasonClass: 'nonterm',
  }, { countersFile });
  check('B3: the disarmed row is untouched, count and all',
    still !== null && still.attempts === 3, { attempts: still && still.attempts });
}

// ── C. FIRST BOOT: no marker at all ────────────────────────────────────────────────────────────
{
  const { root, countersFile, lines, log } = fresh();
  seedCounters(countersFile);
  const out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: fp('FIRST'), log }, { countersFile });
  check('C1: no recorded digest FIRES it — a first boot cannot prove the code is unchanged, and something was deployed to get here',
    out.fired === true && out.why === 'first-boot' && out.previous === null
      && counters.listCounters({}, { countersFile }).length === 0,
    { fired: out.fired, why: out.why, previous: out.previous });
  check('C2: and the journal says first_boot, so the wide clear is not read as a mystery',
    lines.some((l) => l.message === 'code-deploy re-arm fired' && l.fields.first_boot === true),
    { fields: (lines.find((l) => l.message === 'code-deploy re-arm fired') || {}).fields });
}

// ── D. UNKNOWN: the capture failed ─────────────────────────────────────────────────────────────
{
  const { root, countersFile, lines, log } = fresh();
  seedCounters(countersFile);
  writeCodeMarker(root, fp('narrow'), fp('WIDE'));
  const out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: null, log }, { countersFile });
  check('D1: a null fingerprint is UNKNOWN, never "changed" — a failed scan must not clear every counter on the instance',
    out.fired === false && out.why === 'unknown-fingerprint'
      && counters.listCounters({}, { countersFile }).length === 4
      && lines.some((l) => l.level === 'warn' && /UNKNOWN at boot/.test(l.message)),
    { fired: out.fired, why: out.why, warned: lines.map((l) => l.message) });
}

// ── E. FAIL-SOFT + THE WIRING ITSELF ───────────────────────────────────────────────────────────
{
  const { root, lines, log } = fresh();
  // A ledger with rows to clear, in a directory that cannot be written: the clear's tmp-then-rename
  // throws. Whatever throws, the boot pass must RETURN — `index.js` exits hard on a boot throw, and
  // a daemon refusing to start because a counter file was unwritable is the worse failure.
  const badDir = fs.mkdtempSync(path.join(os.tmpdir(), 'code-deploy-bad-'));
  const locked = path.join(badDir, 'attempt-counters.json');
  seedCounters(locked);
  fs.chmodSync(badDir, 0o500);
  let threw = null;
  let out = null;
  try { out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: fp('X'), log }, { countersFile: locked }); } catch (err) { threw = err; }
  fs.chmodSync(badDir, 0o700);
  check('E1: FAIL-SOFT — an unusable counter ledger returns, it never throws out of the boot path',
    threw === null && out !== null && out.fired === false && out.why === 'rearm-failed'
      && lines.some((l) => l.level === 'warn' && /re-arm failed/.test(l.message)),
    { threw: threw && threw.message, why: out && out.why });

  // The dead-mechanism check this program keeps having to make: a producer nobody calls is the
  // defect, not the absence of the producer. Order matters — reading the marker AFTER the write
  // would compare this boot against itself and never fire.
  const src = fs.readFileSync(path.join(__dirname, '..', 'index.js'), 'utf8');
  const callAt = src.indexOf('rearmOnCodeDeploy({');
  const writeAt = src.indexOf('writeCodeMarker(workspaceRoot');
  check('E2: the boot path CALLS it, and calls it BEFORE the marker that holds the previous digest is overwritten',
    callAt > 0 && writeAt > 0 && callAt < writeAt, { callAt, writeAt });
}

const pass = checks.every((c) => c.pass);
const wallMs = Date.now() - t0;
const exit = pass ? 0 : 1;
fs.writeFileSync(OUT, `${JSON.stringify({
  summary: {
    probe: 'probe-code-deploy-rearm', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0,
  },
  entries: checks,
}, null, 2)}\n`);
process.stdout.write(`PROBE probe-code-deploy-rearm EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
process.exit(exit);
