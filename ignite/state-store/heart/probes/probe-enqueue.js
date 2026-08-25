'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-enqueue.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-enqueue-${Date.now()}-${process.pid}.db`);

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

function dump(label, store) {
  out(label);
  const data = store.dump();
  out('jobs:', JSON.stringify(data.jobs));
  out('queue:', JSON.stringify(data.queue));
  out('jobs_log:', JSON.stringify(data.jobs_log));
}

try {
  fs.writeFileSync(outPath, '');

  const store = openHeartStore({
    dbPath: tmpDb,
    profiles: { default: { headed: false } },
  });
  store.registerJob({
    jobId: 'launch-worker',
    actionType: 'launch-agent',
    function: 'spawnLaunchAgent',
    argsSchema: JSON.stringify({ required: {}, optional: {} }),
    enabled: 1,
  });

  const now = new Date();
  const runAt = now.toISOString().replace(/\.\d{3}Z$/, 'Z');
  const row = store.enqueue({
    jobId: 'launch-worker',
    args: JSON.stringify({}),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt,
    enqueuedBy: 'owner',
  });

  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  dump('=== BEFORE CLOSE ===', store);

  const queueIdBefore = row.queue_id;
  closeHeartStore();

  const store2 = openHeartStore({ dbPath: tmpDb });
  const after = store2.getQueueRow(queueIdBefore);
  dump('=== AFTER REOPEN ===', store2);
  closeHeartStore();

  const ok = after !== null && after.job_id === 'launch-worker';
  out(`PERSISTENCE_OK: ${ok}`);

  // ══ Task 7.574 · THE FIRE-TOOL ENQUEUE DOOR of 7.559's `args_allowlist` gate ═══════════════
  //
  // Fixture stores ONLY — the live `heart.db` carries a periodic `goal-creation-request` row that
  // fires against the real box every 300 s and is never touched from here.
  //
  // The catalogue below mirrors the SHAPES `envelope/spawn-profiles.yaml` admits, not its roster.
  // ⚠ `allowlisted-tool` IS A FIXTURE AND HAS NO LIVE COUNTERPART: since `one-readiness-predicate.md`
  // deleted `edge-runner` — the only entry that ever declared an `args_allowlist` — no shipped entry
  // declares one. The 7.559 gate itself is untouched, so the door still has to be measured, and a
  // fixture is now the only way to reach it. The self-heal and goal-creation rows below ARE the args
  // shapes actually stored live (read read-only from `heart.db`: `{"tool":"selfheal-watch"}` /
  // `{"tool":"goal-creation-request"}`), so arm 3 still exercises real rows.
  // Derived from this script's own location — never a baked-in vault path (task 7.799).
  const WORKSPACE = path.resolve(__dirname, '..', '..', '..', '..', '..', '..', '..');
  const LIVE_GOAL = path.join(WORKSPACE, '.rbtv', 'goals', 'build-core-daemon-mvp');
  const doorTools = {
    'allowlisted-tool': {
      argv: ['/usr/bin/python3', '/…/some-job.py', '--goal', '{{goal}}'],
      args_allowlist: { goal: [LIVE_GOAL] },
    },
    'selfheal-watch': { argv: ['/usr/bin/python3', '/…/selfheal-watch.py'] },
    'goal-creation-request': { argv: ['/usr/bin/python3', '/…/goal_creation_request.py'] },
    // The operator typo of task 7.577 — a SCALAR where a mapping of key → list is meant. Its arm
    // below is the local twin of `probe-argv-template.js` S2b, which needs this row to EXIST.
    'malformed-allowlist': { argv: ['/bin/true'], args_allowlist: 'goal' },
  };
  const doorDb = path.join(os.tmpdir(), `heart-probe-enqueue-door-${Date.now()}-${process.pid}.db`);
  const door = openHeartStore({ dbPath: doorDb, tools: doorTools });
  const register = (jobId, schema) => door.registerJob({
    jobId,
    actionType: 'fire-tool',
    function: 'spawnFireTool',
    argsSchema: JSON.stringify(schema),
    enabled: 1,
  });
  const WITH_GOAL = { required: { tool: 'string' }, optional: { goal: 'string', workdir: 'string' } };
  register('allowlisted-tool', WITH_GOAL);
  register('selfheal-watch', { required: { tool: 'string' }, optional: { workdir: 'string' } });
  register('goal-creation-request', { required: { tool: 'string' } });
  register('malformed-allowlist', WITH_GOAL);

  const doorEnqueue = (jobId, rowArgs) => door.enqueue({
    jobId,
    args: JSON.stringify(rowArgs),
    sessionMode: 'headless',
    triggerKind: 'scheduled',
    runAt,
    enqueuedBy: 'owner',
  });

  const arms = [];
  // ⚠ ASSERTS THE ENFORCED PROPERTY DIRECTLY — the typed code AND the refusal reason — never
  // "it threw" and never "it did not throw". A no-throw assertion would pass against a door that
  // was deleted, and a bare-throw assertion would pass on an unrelated schema failure.
  function refused(name, jobId, rowArgs, wantIn) {
    let got = null;
    try {
      doorEnqueue(jobId, rowArgs);
    } catch (e) {
      got = `${e.code}: ${e.message}`;
    }
    const pass = got !== null && got.startsWith('E_BAD_ARGS:') && got.includes(wantIn);
    arms.push([pass, name, got === null ? 'ENQUEUED (no refusal)' : got]);
  }
  function accepted(name, jobId, rowArgs) {
    let got;
    try {
      const r = doorEnqueue(jobId, rowArgs);
      got = r && r.queue_id ? `queue_id=${r.queue_id}` : `no row: ${JSON.stringify(r)}`;
      arms.push([Boolean(r && r.queue_id), name, got]);
    } catch (e) {
      arms.push([false, name, `REFUSED ${e.code}: ${e.message}`]);
    }
  }

  // (1) HOSTILE ROW, REFUSED AT THE DOOR. `goal` is not the value the config author wrote down.
  refused('7.574(1) hostile goal on an allowlisted entry is refused at ENQUEUE',
    'allowlisted-tool', { tool: 'allowlisted-tool', goal: '/etc/passwd' }, "not on this entry's allowlist");
  refused('7.574(1b) a near-miss (case) is a miss, refused at ENQUEUE',
    'allowlisted-tool', { tool: 'allowlisted-tool', goal: LIVE_GOAL.toUpperCase() }, "not on this entry's allowlist");
  refused('7.574(1c) a control character in an allowlisted key is refused at ENQUEUE',
    'allowlisted-tool', { tool: 'allowlisted-tool', goal: `${LIVE_GOAL}\n--x` }, 'must carry no control character');

  // (2) THE LEGAL ROW STILL ENQUEUES — fail-closed must not swallow valid traffic.
  accepted('7.574(2) the allowlisted goal still enqueues',
    'allowlisted-tool', { tool: 'allowlisted-tool', goal: LIVE_GOAL });

  // (3) THE LIVE ROWS, BY THEIR ACTUAL STORED ARGS, STILL ENQUEUE UNCHANGED.
  accepted('7.574(3) live goal-creation-request row shape (periodic, queue_id 281) still enqueues',
    'goal-creation-request', { tool: 'goal-creation-request' });
  accepted('7.574(3) live selfheal-watch row shape still enqueues',
    'selfheal-watch', { tool: 'selfheal-watch' });
  // ⚠⚠ THE REGRESSION THIS ROW EXISTS TO CATCH. A `workdir` OUTSIDE `.rbtv/goals/` is legal on a
  // fire-tool row (a repo, a state root) and illegal on a start-workflow one. If this door is ever
  // widened to the bare grammar call, THIS is the arm that goes red — and the live self-heal rows
  // are what would have been refused in production.
  accepted('7.574(3) a fire-tool workdir outside `.rbtv/goals/` is still legal (no workflow containment)',
    'selfheal-watch', { tool: 'selfheal-watch', workdir: WORKSPACE });
  accepted('7.574(3) an entry declaring NO args_allowlist admits its untemplated row unchanged',
    'goal-creation-request', { tool: 'goal-creation-request' });
  // ⚠⚠ THE DOOR REFUSES TO JUDGE AN OPERATOR TYPO. A malformed `args_allowlist` is a SHAPE error,
  // owned by the fire path since task 7.577 (refused there and RECORDED on the execution). If this
  // door raised it, the row could never be stored — and `probe-argv-template.js` S2b, whose
  // fire-path arms need exactly this row, could no longer build its fixture. Caught by running that
  // probe against the first build of this change, not by inspection.
  accepted('7.574(3) a row against a MALFORMED args_allowlist still enqueues — the shape error stays the FIRE path\'s (7.577)',
    'malformed-allowlist', { tool: 'malformed-allowlist', goal: '/etc/passwd' });
  closeHeartStore();
  try { fs.unlinkSync(doorDb); } catch {}
  try { fs.unlinkSync(doorDb + '-wal'); } catch {}
  try { fs.unlinkSync(doorDb + '-shm'); } catch {}

  // (4) THE FIRE PATH IS UNCHANGED AND STILL REFUSES. `expandArgv` is the function `ticker.js`
  // launchFireTool calls with the entry's allowlist; exercised here on the SAME hostile value arm 1
  // refuses at the door, so adding the door is visibly not a reason the boundary weakened.
  const { expandArgv } = require('../argv-template');
  const fireArgv = doorTools['allowlisted-tool'].argv;
  const fireAllow = doorTools['allowlisted-tool'].args_allowlist;
  const fireBad = expandArgv(fireArgv, { tool: 'allowlisted-tool', goal: '/etc/passwd' }, fireAllow);
  arms.push([
    typeof fireBad.refused === 'string' && fireBad.refused.includes("not on this entry's allowlist")
      && fireBad.argv === undefined,
    '7.574(4) the 7.559 FIRE-path refusal still fires on the same hostile value',
    JSON.stringify(fireBad),
  ]);
  const fireOk = expandArgv(fireArgv, { tool: 'allowlisted-tool', goal: LIVE_GOAL }, fireAllow);
  arms.push([
    Array.isArray(fireOk.argv) && fireOk.argv[3] === LIVE_GOAL && fireOk.refused === undefined,
    '7.574(4) the 7.559 FIRE path still composes the legal value into argv',
    JSON.stringify(fireOk),
  ]);

  out('=== 7.574 · fire-tool enqueue door (fixture stores only) ===');
  for (const [pass, name, detail] of arms) out(`  ${pass ? 'PASS' : 'FAIL'}  ${name} → ${detail}`);
  const armsFailed = arms.filter(([p]) => !p).length;
  out(`ARMS: ${arms.length}  FAILED: ${armsFailed}`);
  if (!ok || armsFailed) throw new Error(`probe-enqueue: ${armsFailed} arm(s) failed, persistence_ok=${ok}`);

  out(`EXIT: 0`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 0;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  try { fs.unlinkSync(tmpDb); } catch {}
  try { fs.unlinkSync(tmpDb + '-wal'); } catch {}
  try { fs.unlinkSync(tmpDb + '-shm'); } catch {}
}
