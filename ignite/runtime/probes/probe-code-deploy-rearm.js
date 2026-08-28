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

  // ⚠ NOT "every row" ANY MORE, and the exception is the event's own premise. `code-deploy` fires
  // because the CODE changed, so it clears the counters whose failure the code could have caused.
  // A `reconcile-respawn` / `nonterm` row counts leader wakes over another seat's `failed` ENDING —
  // a row new daemon bytes do not touch — and it SURVIVES (owner ruling 2026-08-28, decision 4(c);
  // `attempt-counters.js#DEPLOY_IMMUNE`). Two of the four seeded rows are that shape.
  check('A2: a changed digest FIRES `code-deploy` and clears the CODE-CAUSED rows',
    out.fired === true && out.why === 'code-changed' && out.cleared.length === 2
      && out.cleared.every((r) => r.reason_class !== 'nonterm'),
    { fired: out.fired, why: out.why, cleared: out.cleared.map((r) => `${r.subject}/${r.reason_class}`) });

  check('A2b: and the two `reconcile-respawn`/`nonterm` rows survive it WITH their attempts — the '
    + 'failure they count is a seat\'s ending, which new daemon bytes do not change',
    after.length === 2 && after.every((r) => r.reason_class === 'nonterm' && Number(r.attempts) === 3)
      && out.kept.length === 2,
    { left: after.map((r) => `${r.subject}/${r.reason_class}=${r.attempts}`), kept: out.kept.length });

  const per = lines.filter((l) => /^re-armed by code-deploy: /.test(l.message));
  check('A3: ONE `info` per cleared row, carrying subject, class and the count it was cleared from',
    per.length === 2 && per.every((l) => l.level === 'info')
      && per.some((l) => l.message === 're-armed by code-deploy: goal-a/leader unread (was N=5)')
      && per.some((l) => l.message === 're-armed by code-deploy: goal-b/leader room (was N=1)'),
    { lines: per.map((l) => l.message) });

  // A lane that stays disarmed THROUGH a deploy is a lane whose next wake is not coming. That must
  // be as audible as a re-arm, or the operator reads the silence as "it was cleared".
  const notPer = lines.filter((l) => /^NOT re-armed by code-deploy/.test(l.message));
  check('A3b: and ONE `info` per row the deploy did NOT clear, saying why',
    notPer.length === 2 && notPer.every((l) => l.level === 'info' && /nonterm \(N=3\)/.test(l.message)),
    { lines: notPer.map((l) => l.message) });

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
      // The cause filter is the event's, not the reason's: a first boot clears the code-caused
      // rows and keeps the ending-caused ones, exactly as an ordinary deploy does.
      && counters.listCounters({}, { countersFile }).every((r) => r.reason_class === 'nonterm')
      && out.cleared.length === 2,
    { fired: out.fired, why: out.why, previous: out.previous, cleared: out.cleared.length });
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

// ── F. THE CAUSE FILTER, STATED AS ITS OWN FACT [owner ruling 2026-08-28, decision 4(c)] ────────
//
// WHAT WAS BROKEN. This event cleared EVERY row. `reconcile-respawn`/`nonterm` counts how many
// times the LEADER was woken to rule another seat's `failed` ENDING — a row in the ending store
// written before this daemon booted. New daemon bytes do not change it and do not make a fourth
// wake likelier to succeed than the third, so wiping the count re-bought three paid opus-5 leader
// sittings on every deploy: nine of them on `goal-memory-management` across three deploys on
// 2026-08-28, all nine producing the same verdict. Crash- and launch-class rows keep the wide
// behaviour, because those failures are exactly what a code change can fix.
{
  const { root, countersFile, log } = fresh();
  const seed = [
    { goal: 'g', seat: 'leader', reasonClass: 'nonterm', times: 2 },
    { goal: 'g', seat: 'w', reasonClass: 'crash', times: 2 },
    { goal: 'g', seat: 'w', reasonClass: 'launch-refused', times: 1 },
    { goal: 'g', seat: 'j', subject: 'job:7', reasonClass: 'unknown-tool', driver: counters.DRIVERS.TICKER_DEFERRED, times: 3 },
  ];
  for (const r of seed) {
    for (let i = 0; i < r.times; i += 1) {
      counters.countAttempt({
        driver: r.driver || counters.DRIVERS.RECONCILE_RESPAWN,
        goal: r.goal, seat: r.subject ? null : r.seat, subject: r.subject, reasonClass: r.reasonClass, n: 3,
      }, { countersFile });
    }
  }
  writeCodeMarker(root, fp('n1'), fp('W1'));
  const out = rearmOnCodeDeploy({ workspaceRoot: root, fingerprint: fp('W2'), log }, { countersFile });
  const left = counters.listCounters({}, { countersFile });
  const kept = counters.peekCounter({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g', seat: 'leader', reasonClass: 'nonterm',
  }, { countersFile });

  check('F1: after `code-deploy`, the `reconcile-respawn`/`nonterm` row PERSISTS with its attempts intact',
    kept !== null && Number(kept.attempts) === 2 && kept.driver === 'reconcile-respawn',
    { row: kept && `${kept.subject}/${kept.reason_class}=${kept.attempts}` });

  check('F2: and the `crash` row is CLEARED — a crash is a code-caused failure and new bytes are a real reason to retry it',
    counters.peekCounter({
      driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g', seat: 'w', reasonClass: 'crash',
    }, { countersFile }) === null,
    { cleared: out.cleared.map((r) => `${r.subject}/${r.reason_class}`) });

  check('F3: every other class and every other driver keeps the WIDE behaviour — only the one (driver, class) pair is immune',
    left.length === 1 && left[0].reason_class === 'nonterm' && out.cleared.length === 3,
    { left: left.map((r) => `${r.driver}:${r.subject}/${r.reason_class}`), cleared: out.cleared.length });

  check('F4: the immune pair is DECLARED, not spelled at the call site — one list, readable by a reviewer',
    Array.isArray(counters.DEPLOY_IMMUNE) && counters.DEPLOY_IMMUNE.length === 1
      && counters.deployImmune({ driver: 'reconcile-respawn', reason_class: 'nonterm' }) === true
      && counters.deployImmune({ driver: 'reconcile-respawn', reason_class: 'crash' }) === false
      && counters.deployImmune({ driver: 'ticker-deferred', reason_class: 'nonterm' }) === false,
    { immune: counters.DEPLOY_IMMUNE });

  // A LANE-SCOPED EVENT IS UNCHANGED, and that is the boundary of this ruling: a person asking for
  // a lane back (`resume`, an owner/leader act) is a fact about the LANE, never about the code.
  const { countersFile: cf2 } = fresh();
  counters.countAttempt({
    driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g', seat: 'leader', reasonClass: 'nonterm', n: 3,
  }, { countersFile: cf2 });
  const laneReset = counters.rearm({
    event: counters.RE_ARM.OWNER_LEADER_ACT, goal: 'g', seat: 'leader',
  }, { countersFile: cf2 });
  check('F5: an owner/leader act still clears the SAME row — the narrowing is `code-deploy`\'s alone',
    laneReset.reset.length === 1 && counters.listCounters({}, { countersFile: cf2 }).length === 0,
    { reset: laneReset.reset.length });

  // RED. The filter removed from a COPY of the live source: if F1/F3 do not discriminate, the
  // mutant passes them too.
  const Module = require('node:module');
  const cFile = require.resolve('../../supervisor/attempt-counters');
  const csrc = fs.readFileSync(cFile, 'utf8');
  const ANCHOR = `    if (event === RE_ARM.CODE_DEPLOY && deployImmune(row)) {
      kept.push(key);
      continue;
    }
`;
  const mutSrc = csrc.includes(ANCHOR) ? csrc.replace(ANCHOR, '') : null;
  let redLeft = null;
  if (mutSrc) {
    const mut = new Module(cFile, null);
    mut.filename = cFile;
    mut.paths = Module._nodeModulePaths(path.dirname(cFile));
    mut._compile(mutSrc, cFile);
    const { countersFile: cf3 } = fresh();
    for (let i = 0; i < 2; i += 1) {
      counters.countAttempt({
        driver: counters.DRIVERS.RECONCILE_RESPAWN, goal: 'g', seat: 'leader', reasonClass: 'nonterm', n: 3,
      }, { countersFile: cf3 });
    }
    mut.exports.rearm({ event: 'code-deploy' }, { countersFile: cf3 });
    redLeft = counters.listCounters({}, { countersFile: cf3 }).length;
  }
  check('F6: RED — with the filter removed, `code-deploy` wipes the `nonterm` row again, so F1/F3 discriminate',
    mutSrc !== null && redLeft === 0, { anchorFound: mutSrc !== null, rowsLeft: redLeft });
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
