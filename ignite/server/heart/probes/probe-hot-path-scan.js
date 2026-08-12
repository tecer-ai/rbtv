'use strict';

// THE GATEWAY WEDGE OF 2026-08-12, AS A CHECK (defect: the ingress stopped accepting minutes after
// every boot and never recovered, while the ticker's timers kept firing punctually).
//
// The mechanism was not in the gateway at all. Two hot paths materialised the store's ENTIRE
// history into JS on every pass:
//
//   1. `inspect ticker` (chat bridge reply leg, every 3 s) called `getMessages()` with no filter and
//      picked the last 10 `owner-feed` rows in JS — 27,490 rows and ~27 MB of corpus text per call.
//   2. `engine/execution-record.js#publishToRecord` (every tick) called `listExecutionsByStatus` for
//      all seven statuses, and that call attached a chain `thread` to every row with a RECURSIVE CTE
//      PER ROW — 874 ms to act on 18 rows.
//
// Neither is bounded and neither shrinks: retention never touches `heart.db` by construction. The
// main thread ended up ~84 % busy and allocating ~30 MB/s, and libuv can only `accept()` between JS
// turns — so the LISTEN backlog stopped draining (Recv-Q > 0 with the sockets still LISTEN and the
// process healthy) while `setInterval` timers still ran, which is exactly what made it look like a
// socket bug instead of a starvation one.
//
// ⚠ THE TIMING ARMS ARE RATIOS AGAINST A CONTROL RUN IN THE SAME PROCESS, never wall-clock budgets:
// a budget tuned on one box is a probe that fails on a slower one and passes on a faster one after
// the fix is reverted. The control IS the old code path, executed here.
//
// ⚠ AND THE SOURCE ARMS ARE THE POINT. Both store APIs keep their old behaviour by default, so a
// green store arm proves only that the bounded call EXISTS — the defect was the production call
// site not using it. That is `gateway.js`'s own 7.10 lesson (producer green, consumer green,
// never connected), so the consumers are asserted directly.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { openHeartStore, closeHeartStore } = require('../heart-store');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-hot-path-scan.out');
const tmpDb = path.join(os.tmpdir(), `heart-probe-hot-path-${Date.now()}-${process.pid}.db`);
const IGNITE = path.resolve(__dirname, '..', '..', '..');

const failures = [];
function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}
function check(name, ok, detail) {
  out(`${name}: ${ok ? 'PASS' : 'FAIL'}${detail ? ` (${detail})` : ''}`);
  if (!ok) failures.push(name);
}

try {
  fs.writeFileSync(outPath, '');
  out('COMMAND: node probe-hot-path-scan.js');

  const store = openHeartStore({ dbPath: tmpDb });

  // Enough history that a full materialisation is measurably worse than a filtered read, and a
  // corpus big enough to carry the cost that actually mattered (the text, not the row count).
  const MESSAGES = 6000;
  const THREADS = 30;
  const corpus = 'x'.repeat(1024);
  for (let i = 0; i < MESSAGES; i++) {
    store.recordMessage({
      type: 'note',
      sender: 'probe',
      thread: i % THREADS === 0 ? 'owner-feed' : `thread-${i % THREADS}`,
      corpus,
      createdAt: new Date(),
    });
  }
  // A chain deep enough that the per-row `_chainThread` CTE has something to walk.
  const EXECS = 3000;
  let parent = null;
  for (let i = 0; i < EXECS; i++) {
    const row = store.recordExecutionStart({
      jobId: 'launch-worker',
      actionType: 'launch-agent',
      args: '{}',
      enqueuedBy: 'owner',
      sessionMode: 'headless',
      firedTick: i + 1,
      firedAt: new Date(),
      parentExecId: i % 50 === 0 ? null : parent,
    });
    parent = row.exec_id;
  }
  out(`SEEDED_MESSAGES: ${MESSAGES}`, `SEEDED_EXECUTIONS: ${EXECS}`);

  // ── 1. The owner-feed read: same answer, and the filter is in SQL ──────────────────────────
  let t = Date.now();
  const control = store.getMessages().filter((m) => m.thread === 'owner-feed');
  const controlMs = Date.now() - t;
  t = Date.now();
  const filtered = store.getMessages({ thread: 'owner-feed' });
  const filteredMs = Date.now() - t;
  out(`FETCH_ALL_THEN_FILTER_MS: ${controlMs}`, `SQL_THREAD_FILTER_MS: ${filteredMs}`);

  check('OWNER_FEED_SAME_ANSWER',
    JSON.stringify(control.map((m) => m.msg_id)) === JSON.stringify(filtered.map((m) => m.msg_id)),
    `${control.length} rows`);
  check('THREAD_FILTER_IS_IN_SQL', filteredMs * 5 <= controlMs,
    `${controlMs}ms unfiltered vs ${filteredMs}ms filtered — must be at least 5x`);

  // ── 2. The per-tick execution scan: no per-row chain walk ──────────────────────────────────
  const ALL = ['launching', 'running', 'done', 'blocked', 'failed', 'stalled', 'killed'];
  t = Date.now();
  let withThreadRows = 0;
  for (const s of ALL) withThreadRows += store.listExecutionsByStatus(s).length;
  const withThreadMs = Date.now() - t;
  t = Date.now();
  let plainRows = 0;
  let sawThreadKey = false;
  for (const s of ALL) {
    const rows = store.listExecutionsByStatus(s, { withThread: false });
    plainRows += rows.length;
    if (rows.some((r) => 'thread' in r)) sawThreadKey = true;
  }
  const plainMs = Date.now() - t;
  out(`SCAN_WITH_THREAD_MS: ${withThreadMs}`, `SCAN_WITHOUT_THREAD_MS: ${plainMs}`);

  check('SCAN_SAME_ROW_COUNT', withThreadRows === plainRows, `${withThreadRows} rows`);
  check('NO_THREAD_ATTACHED_WHEN_OPTED_OUT', !sawThreadKey);
  check('THREAD_ATTACH_STILL_DEFAULT',
    store.listExecutionsByStatus('done').every((r) => typeof r.thread === 'string'),
    'existing callers must keep the derived thread');
  check('CHAIN_WALK_SKIPPED', plainMs * 3 <= withThreadMs,
    `${withThreadMs}ms with vs ${plainMs}ms without — must be at least 3x`);

  // ── 3. The CONSUMERS. A bounded API nothing calls is the 7.10 defect. ──────────────────────
  const dispatchSrc = fs.readFileSync(path.join(IGNITE, 'server', 'internal-api', 'dispatch.js'), 'utf8');
  const recordSrc = fs.readFileSync(path.join(IGNITE, 'engine', 'execution-record.js'), 'utf8');
  const seedingSrc = fs.readFileSync(path.join(IGNITE, 'engine', 'seeding.js'), 'utf8');

  check('DISPATCH_NEVER_FILTERS_THREAD_IN_JS',
    // `[^)]*` does NOT work here: the arrow param `(m)` closes a paren before `thread` ever
    // appears, so the pattern can never match the very line it exists to catch — measured against
    // the reverted call site on 2026-08-12, which it passed.
    !/getMessages\(\)[\s\S]{0,80}?\.filter\([\s\S]{0,60}?thread/.test(dispatchSrc),
    'inspect must pass { thread } to getMessages, not fetch-all-then-filter');
  check('DISPATCH_USES_THREAD_FILTER',
    (dispatchSrc.match(/getMessages\(\{[^}]*thread/g) || []).length >= 3,
    'the three thread-scoped inspect reads (owner-feed, messages-by-thread, messages-by-exec)');
  check('PUBLISH_SKIPS_CHAIN_WALK',
    /listExecutionsByStatus\(status,\s*\{\s*withThread:\s*false\s*\}\)/.test(recordSrc),
    'publishToRecord runs once per execution ever recorded');
  // The COSTLIEST pair, and the reason a fix to `publishToRecord` alone did not lift the wedge:
  // `recordView` and `executionsByJob` each scan all seven statuses ONCE PER DAEMON-LANE GOAL, per
  // cadence. At 3 goals on the live store that was 5.9 s of blocking JS per 12 s tick, arriving as
  // ONE synchronous block — which is what the gateway's accept path was actually losing to.
  check('SEEDING_SCANS_SKIP_CHAIN_WALK',
    (seedingSrc.match(/listExecutionsByStatus\(status,\s*\{\s*withThread:\s*false\s*\}\)/g) || []).length >= 2,
    'both recordView and executionsByJob — each runs per goal per cadence');
  check('NO_UNBOUNDED_ALL_STATUS_SCAN_LEFT',
    !/for \(const status of ALL_TURN_STATUSES\)[\s\S]{0,300}?listExecutionsByStatus\(status\)\s*\)/.test(seedingSrc),
    'an all-status scan that still attaches the chain thread');

  closeHeartStore();
} catch (err) {
  out(`THREW: ${err && err.message}`);
  failures.push('THREW');
} finally {
  for (const suffix of ['', '-wal', '-shm']) {
    try { fs.unlinkSync(tmpDb + suffix); } catch { /* not there */ }
  }
  out(`FAILURES: ${failures.length ? failures.join(',') : 'none'}`);
  out(`EXIT: ${failures.length ? 1 : 0}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exit(failures.length ? 1 : 0);
}
