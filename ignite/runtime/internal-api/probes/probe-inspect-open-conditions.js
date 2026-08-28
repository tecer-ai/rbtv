'use strict';

// probe-inspect-open-conditions — `inspect daemon` publishes the ALARM REGISTRY alongside its own
// warning table (wave test 2, 2026-08-26).
//
// WHAT WAS BROKEN. `standing_warnings` is the daemon's OWN warning table. `inspect daemon` — which
// `ignite status` is the alias for — published it and nothing else, and the master material told
// every role that field IS the alarm surface. spec-owner-io §5 puts open conditions in the
// alarm-signature REGISTRY, written from OUTSIDE this process by the watchdog and the frozen
// invariant. A master seat asked "is anything standing", read this answer, and told the owner
// "No standing warnings" while the watchdog had held a probe-suite alarm for hours. One true
// source, presented as the answer from both.
//
// WHAT IS PROVEN, in-process over the REAL dispatcher and a THROWAWAY store and registry:
//   1. a registry carrying one OPEN row surfaces on `open_conditions`, key by key;
//   2. a CLEARED row does not;
//   3. no registry file at all → `[]` (nothing is open), not an error;
//   4. no workspace root → `null` (this daemon CANNOT READ the registry) — a different fact,
//      never collapsed into the empty list;
//   5. `standing_warnings` is untouched by any of it;
//   6. the reader RELOADS: a row written AFTER the daemon booted is still seen (the writers are
//      other processes, so a constructor-time snapshot would read as "nothing is wrong" forever);
//   7. RED CONTROL — a dispatcher built with the field removed answers `undefined`, which is the
//      state the wave-test-2 answer was given from.
//
// The capture is truncated at module load, BEFORE any work. The process exit code is the truth.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-inspect-open-conditions.out');
fs.writeFileSync(outPath, '');

const { openHeartStore, closeHeartStore } = require('../../../state-store/heart/heart-store');
const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { createAlarmEmitter, alarmRegistryPath } = require('../../../observation/emitter');

const stamp = `${Date.now()}-${process.pid}`;
const tmpDb = path.join(os.tmpdir(), `ignite-probe-open-conditions-${stamp}.db`);
const workspace = fs.mkdtempSync(path.join(os.tmpdir(), `ignite-probe-open-conditions-ws-${stamp}-`));
const emptyWorkspace = fs.mkdtempSync(path.join(os.tmpdir(), `ignite-probe-open-conditions-empty-${stamp}-`));

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// A writer that is NOT the daemon — the whole point of this surface is that the rows arrive from
// another process. `post` is a no-op sink here: the emission path is the watchdog probe's subject,
// not this one's.
function writeAlarm(root, over) {
  const emitter = createAlarmEmitter({
    storePath: alarmRegistryPath(root),
    post: async () => ({ outbox_id: 'ob-probe', delivered: false }),
    systemChannelId: 'C-PROBE-SYSTEM',
  });
  return emitter.emit(Object.assign({
    condition: 'probe-suite: suite is LIVE but the correctness verdict is RED: 16 genuine probe failure(s).',
    subject: { type: 'probe-suite', id: 'rbtv-probe-suite.timer' },
    evidence_pointer: path.join(root, '.rbtv', 'runtime', 'probe-suite', 'latest.json'),
    what_would_clear_it: 'the watchdog reads the probe-suite row `up` again on any pass',
    signature_class: 'watchdog-probe-suite-alarm',
    immediate: true,
  }, over || {}));
}

// ONE store for the whole probe: `openHeartStore` refuses a second writer in one process, and the
// store is not this probe's subject — the three apis below differ ONLY in `workspaceRoot`, which is
// the variable under test.
const SECRET = crypto.randomBytes(32).toString('hex');
let heartStore = null;

function apiFor(root, factory = createInternalApi) {
  return factory({
    heartStore,
    spawnManager: { config: {} },
    secret: SECRET,
    workspaceRoot: root,
  });
}

async function inspectDaemon(api) {
  const res = await api.dispatch({
    v: ENVELOPE_VERSION,
    id: crypto.randomUUID(),
    ts: new Date().toISOString(),
    auth: SECRET,
    sender: { id: 'probe-agent', kind: 'agent' },
    intent: 'inspect',
    payload: { target: 'daemon' },
  });
  if (!res.ok) throw new Error(`inspect daemon refused: ${JSON.stringify(res.error)}`);
  return res.result;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  heartStore = openHeartStore({ dbPath: tmpDb, tools: {}, workflows: {} });

  // --- 1/2/5/6. one OPEN row, over the real dispatcher -------------------------------------
  await writeAlarm(workspace);
  const api = apiFor(workspace);
  let res = await inspectDaemon(api);

  check('1a open_conditions is a list', Array.isArray(res.open_conditions), JSON.stringify(res.open_conditions));
  check('1b exactly one open condition', (res.open_conditions || []).length === 1,
    `n=${(res.open_conditions || []).length}`);
  const row = (res.open_conditions || [])[0] || {};
  check('1c signature is condition-class + subject',
    row.signature === 'watchdog-probe-suite-alarm:probe-suite:rbtv-probe-suite.timer', String(row.signature));
  check('1d the condition text crosses verbatim',
    typeof row.condition === 'string' && row.condition.includes('correctness verdict is RED'), String(row.condition).slice(0, 70));
  check('1e subject flattens to the bare id', row.subject === 'rbtv-probe-suite.timer', String(row.subject));
  check('1f first_emitted_at crosses', typeof row.first_emitted_at === 'string' && row.first_emitted_at.length > 0);
  check('1g evidence_pointer crosses', typeof row.evidence_pointer === 'string' && row.evidence_pointer.endsWith('latest.json'),
    String(row.evidence_pointer));
  check('1h the published key set is exactly the digest contract',
    JSON.stringify(Object.keys(row).sort()) === JSON.stringify(['condition', 'evidence_pointer', 'first_emitted_at', 'signature', 'subject']),
    Object.keys(row).sort().join(','));

  // 5. the daemon's OWN table is untouched by any of this.
  check('5a standing_warnings still answers, independently', Array.isArray(res.standing_warnings),
    JSON.stringify(res.standing_warnings));
  check('5b the two fields are separate answers, not one', res.standing_warnings !== res.open_conditions);

  // 6. RELOAD. A SECOND writer process writes AFTER this api was built.
  await writeAlarm(workspace, {
    condition: 'the meet-transcript-summarizer goal has been frozen for 15 minutes.',
    subject: { type: 'goal', id: 'meet-transcript-summarizer' },
    signature_class: 'frozen-goal',
    what_would_clear_it: 'a seat executing a row for this goal',
  });
  res = await inspectDaemon(api);
  check('6a a row written after boot is seen (reload before every read)',
    (res.open_conditions || []).length === 2, `n=${(res.open_conditions || []).length}`);

  // 2. a CLEARED row leaves the list.
  const reader = createAlarmEmitter({ storePath: alarmRegistryPath(workspace), post: async () => ({}) });
  reader.clear('frozen-goal:goal:meet-transcript-summarizer');
  res = await inspectDaemon(api);
  check('2a a cleared row stops being an open condition',
    (res.open_conditions || []).length === 1
    && res.open_conditions[0].signature === 'watchdog-probe-suite-alarm:probe-suite:rbtv-probe-suite.timer',
    JSON.stringify((res.open_conditions || []).map((r) => r.signature)));

  // --- 3. NO registry file → `[]` (nothing is open), never an error ------------------------
  const emptyApi = apiFor(emptyWorkspace);
  const emptyRes = await inspectDaemon(emptyApi);
  check('3a no registry file → an empty list', Array.isArray(emptyRes.open_conditions) && emptyRes.open_conditions.length === 0,
    JSON.stringify(emptyRes.open_conditions));
  check('3b and the registry file was NOT created by the read',
    !fs.existsSync(alarmRegistryPath(emptyWorkspace)), alarmRegistryPath(emptyWorkspace));

  // --- 4. NO workspace root → `null`, a DIFFERENT fact from `[]` ---------------------------
  const rootlessApi = apiFor(null);
  const rootlessRes = await inspectDaemon(rootlessApi);
  check('4a no workspace root → null, not []', rootlessRes.open_conditions === null,
    JSON.stringify(rootlessRes.open_conditions));
  check('4b null and [] are distinguishable to a reader',
    rootlessRes.open_conditions === null && Array.isArray(emptyRes.open_conditions));

  // --- 7. RED CONTROL: the pre-fix dispatcher answers `undefined` --------------------------
  const dispatchPath = require.resolve('../dispatch');
  const src = fs.readFileSync(dispatchPath, 'utf8');
  const marker = '      open_conditions: readOpenConditions ? readOpenConditions() : null,';
  if (!src.includes(marker)) {
    check('7a the mutation target is present in dispatch.js', false,
      're-point the mutation: the open_conditions line no longer reads as this probe expects');
  } else {
    const redPath = path.join(os.tmpdir(), `ignite-probe-open-conditions-red-${stamp}.js`);
    fs.writeFileSync(redPath, src.replace(marker, ''));
    // Same folder-relative requires would break from /tmp, so the copy is loaded from the real
    // directory under a throwaway name instead.
    const sibling = path.join(path.dirname(dispatchPath), `.probe-red-${stamp}.js`);
    fs.copyFileSync(redPath, sibling);
    try {
      /* eslint-disable-next-line global-require, import/no-dynamic-require */
      const redRes = await inspectDaemon(apiFor(workspace, require(sibling).createInternalApi));
      check('7a pre-fix: open_conditions is absent from the answer', redRes.open_conditions === undefined,
        JSON.stringify(redRes.open_conditions));
      check('7b pre-fix: standing_warnings still answers — which is why the wrong answer looked right',
        Array.isArray(redRes.standing_warnings) && redRes.standing_warnings.length === 0);
    } finally {
      try { fs.unlinkSync(sibling); } catch {}
      try { fs.unlinkSync(redPath); } catch {}
    }
  }
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { closeHeartStore(); } catch {}
  for (const suffix of ['', '-wal', '-shm']) {
    try { fs.unlinkSync(tmpDb + suffix); } catch {}
  }
  fs.rmSync(workspace, { recursive: true, force: true });
  fs.rmSync(emptyWorkspace, { recursive: true, force: true });
});
