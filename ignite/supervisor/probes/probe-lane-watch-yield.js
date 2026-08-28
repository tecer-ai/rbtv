#!/usr/bin/env node
'use strict';

// probe-lane-watch-yield — THE LANE WATCH PASS YIELDS BETWEEN GOALS, AND A PASS NEVER STACKS
// (`lane-watch.js#runLaneWatch`, `runtime/index.js`'s cadence callback, 2026-08-28).
//
// THE MEASURED DEFECT this closes (diag `fix-gateway-stall`/`diag-gateway-stall`, 2026-08-28).
// `runLaneWatch` was a plain function: it walked every goal folder spending `execFileSync(python …)`
// per goal — ~2.4 s each — with no `await` anywhere. The daemon's gateway listener
// (`runtime/gateway/gateway.js`) lives on the SAME single event loop, so for the whole sweep the
// daemon could not accept, read or answer anything. Measured on the live daemon with three seeded
// goals: the loop was blocked a median 7.9 s and up to 12.6 s out of every 10 s cadence (~78 %
// duty cycle), `inspect daemon` p90 was 5.44 s against a 10 s watchdog cutoff, and the watchdog
// paged the owner 29 times about a daemon that was never dead — only busy. A status cache was
// refuted at diagnosis: the handler costs 37 ms; there was no THREAD on which to deliver an answer.
//
// THE QUESTION, and it is a latency question, so it is MEASURED and never grepped:
//
//   Y1  during a 4-goal sweep whose per-goal work is a 300 ms synchronous block, does a client
//       hitting a local HTTP server ON THIS SAME EVENT LOOP get answered DURING the sweep, and is
//       its worst wait one goal rather than the whole sweep (< 1 s, against a ~1.2 s sweep)?
//   Y2  RED: with the one `await` deleted from the head of the per-goal loop — the exact pre-fix
//       shape — does that same client's worst wait return to the WHOLE sweep, with zero answers
//       delivered inside it?
//   G1  do two ticks that overlap produce ONE pass (`passInFlight`), with the dropped tick named
//       at `debug` rather than queued behind the running one?
//   G2  RED: with the guard block deleted, do the same two ticks produce TWO passes?
//   G3  does the cadence still run watch -> frozen -> tick, in that order? (`frozenPass` reads the
//       facts the pass just collected and the tick dispatches what it just enqueued; both must
//       observe a FINISHED pass, which before the yield came free and now needs the `await`.)
//
// WHAT IS SUBSTITUTED, disclosed up front (`bars.md` 10):
//   · NO DAEMON PROCESS, no engine, no store, no tmux, no python, no `.rbtv` — nothing outside a
//     `mkdtemp` fixture is touched, and the probe is safe to run beside the live daemon.
//   · The per-goal COST is a stub: `maybeReconcile` is replaced, in an in-memory recompile of
//     `lane-watch.js`, by a 300 ms busy block. The real cost is `execFileSync(python …)`, which a
//     probe must never launch; what Y1/Y2 measure is the SHAPE of the loop around that cost, and a
//     synchronous busy block is the same shape at 1/8th the price. The loop, its `await`, and the
//     goal walk are the REAL ones.
//   · Each fixture goal is left at the `taskforce-unreadable` skip, one line after the block — no
//     seeding, no room, no engine. The taskforce READ is stubbed to throw, and that stub is not
//     cosmetic: the real `readTaskforce` runs `validateTaskforce`, which shells
//     `execFileSync(python goal_cli.py check-acyclic)` — ~750 ms of real subprocess per goal folder,
//     memoised per path, which would both launch python from a probe and make every number here
//     depend on whether that memo was warm. NO SUBPROCESS OF ANY KIND RUNS IN THIS PROBE, and Y0
//     measures that: the sweep must cost goals x 300 ms and nothing more.
//   · G1/G2/G3 drive the REAL SOURCE TEXT of the daemon's cadence callback: the slice between two
//     asserted anchors in `runtime/index.js` is compiled verbatim with `new Function` and the
//     captured callback is invoked. `log`, `laneWatchPass`, `frozenPass` and `engine.tick` are
//     stubs — the guard itself is never re-typed here, because a guard a probe supplies to itself
//     measures nothing.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const Module = require('node:module');

const HERE = __dirname;
const IGNITE_SRC = path.join(HERE, '..', '..');
const OUT_PATH = path.join(HERE, 'probe-lane-watch-yield.out');

const start = Date.now();
const lines = [];
const failures = [];
const say = (s) => { lines.push(s); };
function check(name, ok, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? `  — ${detail}` : ''}`);
  if (!ok) failures.push(name);
  return ok;
}

const GOALS = 4;        // the sized fixture
const GOALS_WIDE = 8;   // the same tree, twice as deep — the scaling arm
const BLOCK_MS = 300;

// ── the fixture ───────────────────────────────────────────────────────────────────────────────
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-lw-yield-'));
function makeRoot(n) {
  const root = path.join(tmp, `ws-${n}`, '.rbtv', 'goals');
  fs.mkdirSync(root, { recursive: true });
  for (let i = 1; i <= n; i += 1) {
    const g = path.join(root, `probe-yield-goal-${i}`);
    fs.mkdirSync(g, { recursive: true });
    fs.writeFileSync(path.join(g, 'execution-lane'), 'daemon\n');
    // Header only: `readTaskforce` refuses it AFTER the per-goal work, so the pass costs its
    // 300 ms and then skips the goal without seeding, opening a room, or touching an engine.
    fs.writeFileSync(path.join(g, 'taskforce.csv'), 'seat,harness,model,effort\n');
  }
  return root;
}
const goalsRoot = makeRoot(GOALS);
const goalsRootWide = makeRoot(GOALS_WIDE);

// ── the harness: `lane-watch.js` recompiled in memory, never written beside the source ────────
const LANE_WATCH_PATH = path.join(IGNITE_SRC, 'supervisor', 'lane-watch.js');
const LANE_WATCH_SRC = fs.readFileSync(LANE_WATCH_PATH, 'utf8');
const RECONCILE_ANCHOR = 'maybeReconcile(';
const YIELD_ANCHOR = '    await new Promise(setImmediate);\n';
const TASKFORCE_ANCHOR = "      unbuiltRows = require('./seeding').readTaskforce(goalFolder);";
const BLOCK_STUB = `(function () { const __t = Date.now() + ${BLOCK_MS}; while (Date.now() < __t); return { skipped: 'probe-block' }; })(`;
const TASKFORCE_STUB = "      unbuiltRows = (function () { throw new Error('probe fixture: no taskforce read, no python'); })();";

// `withYield: false` is the pre-fix shape, reproduced by deleting the one line the fix added.
function buildWatch({ withYield }) {
  if (!LANE_WATCH_SRC.includes(RECONCILE_ANCHOR)) {
    throw new Error('anchor ABSENT in lane-watch.js — the per-goal block would never be installed');
  }
  if (!LANE_WATCH_SRC.includes(YIELD_ANCHOR)) {
    throw new Error('the yield ABSENT in lane-watch.js — Y1/Y2 would measure nothing');
  }
  if (!LANE_WATCH_SRC.includes(TASKFORCE_ANCHOR)) {
    throw new Error('the taskforce-read anchor ABSENT in lane-watch.js — the probe would shell python');
  }
  let src = LANE_WATCH_SRC.split(RECONCILE_ANCHOR).join(BLOCK_STUB);
  src = src.replace(TASKFORCE_ANCHOR, TASKFORCE_STUB);
  if (!withYield) src = src.replace(YIELD_ANCHOR, '');
  const m = new Module(LANE_WATCH_PATH, null);
  m.filename = LANE_WATCH_PATH;
  m.paths = Module._nodeModulePaths(path.dirname(LANE_WATCH_PATH));
  m._compile(src, LANE_WATCH_PATH);
  return m.exports.runLaneWatch;
}

// ── the prober: a real HTTP client and server on THIS event loop, exactly where the gateway is ──
async function measure(runWatch, root = goalsRoot) {
  const server = http.createServer((req, res) => { res.end('ok'); });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const port = server.address().port;

  const answers = [];      // { firedAt, answeredAt }
  let stopped = false;
  const fire = () => {
    if (stopped) return;
    const firedAt = Date.now();
    const req = http.get({ host: '127.0.0.1', port, path: '/', agent: false }, (res) => {
      res.resume();
      res.on('end', () => answers.push({ firedAt, answeredAt: Date.now() }));
    });
    req.on('error', () => {});
  };
  const timer = setInterval(fire, 25);

  // A short warm-up proves the prober itself answers in single-digit ms when nothing blocks —
  // without it a "max wait" number has no control to be read against.
  await new Promise((resolve) => setTimeout(resolve, 150));
  const warmup = answers.splice(0, answers.length).map((a) => a.answeredAt - a.firedAt);

  // ⚠ ONE REQUEST FIRED WITH THE SWEEP, DELIBERATELY. The interval prober alone cannot measure a
  // block it is itself frozen by: a `setInterval` starved for the whole sweep fires ONCE when the
  // loop frees, by which time there is nothing left to wait for. This client is in flight when the
  // first goal starts, exactly like a gateway request that arrives mid-cadence, and its wait is
  // THE number both arms are compared on.
  fire();
  const t0 = Date.now();
  const pass = await runWatch({ goalsRoot: root, engine: {} });
  const t1 = Date.now();

  stopped = true;
  clearInterval(timer);
  await new Promise((resolve) => setTimeout(resolve, 150));
  await new Promise((resolve) => server.close(resolve));

  const waits = answers.map((a) => a.answeredAt - a.firedAt);
  return {
    pass,
    sweepMs: t1 - t0,
    maxWarmupMs: warmup.length ? Math.max(...warmup) : -1,
    maxWaitMs: waits.length ? Math.max(...waits) : -1,
    requests: waits.length,
    answeredDuringSweep: answers.filter((a) => a.answeredAt > t0 && a.answeredAt < t1).length,
  };
}

// The first sweep of the process pays for `require('./seeding')` and its dependency graph, which
// `readTaskforce` pulls in lazily on the first goal. Paid HERE, so neither measured arm carries it
// and the two sweep times can be compared at all.
async function warmModules() {
  await buildWatch({ withYield: true })({ goalsRoot, engine: {} });
}

// ── the cadence callback, compiled from the daemon's own source text ──────────────────────────
const DAEMON_PATH = path.join(IGNITE_SRC, 'runtime', 'index.js');
const DAEMON_SRC = fs.readFileSync(DAEMON_PATH, 'utf8');
const CADENCE_HEAD = '  let passInFlight = false;\n  const timer = setInterval(async () => {';
const CADENCE_TAIL = '  }, intervalMs);';
const GUARD_BLOCK = `    if (passInFlight) {
      log('debug', 'cadence skipped — the previous lane watch pass is still running', { intervalMs });
      return;
    }
`;

function cadenceSlice() {
  const i = DAEMON_SRC.indexOf(CADENCE_HEAD);
  if (i < 0) throw new Error('cadence anchor ABSENT in runtime/index.js — G1/G2/G3 would measure nothing');
  const j = DAEMON_SRC.indexOf(CADENCE_TAIL, i);
  if (j < 0) throw new Error('cadence tail ABSENT in runtime/index.js — G1/G2/G3 would measure nothing');
  return DAEMON_SRC.slice(i, j + CADENCE_TAIL.length);
}

// Compiles the slice VERBATIM and hands back the callback `setInterval` was given. Nothing about
// the guard is re-typed: a stub `setInterval` captures, it does not schedule.
function buildCadence(src, stubs) {
  let captured = null;
  // eslint-disable-next-line no-new-func
  const factory = new Function(
    'log', 'laneWatchPass', 'frozenPass', 'engine', 'intervalMs', 'setInterval',
    `${src}\n  return timer;`,
  );
  factory(stubs.log, stubs.laneWatchPass, stubs.frozenPass, stubs.engine, 10000,
    (fn) => { captured = fn; return { captured: true }; });
  if (typeof captured !== 'function') throw new Error('the cadence callback was not captured');
  return captured;
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 20));

async function driveCadence(src) {
  const order = [];
  const logged = [];
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  const cadence = buildCadence(src, {
    log: (level, message) => logged.push({ level, message }),
    laneWatchPass: async () => { order.push('watch'); await gate; },
    frozenPass: () => order.push('frozen'),
    engine: { tick: async () => { order.push('tick'); } },
  });

  cadence();               // tick 1 — the pass starts and parks
  cadence();               // tick 2 — arrives while tick 1 is still in its pass
  await settle();
  const duringOverlap = order.filter((o) => o === 'watch').length;

  release();
  await settle();
  cadence();               // tick 3 — the pass has finished, so this one must run
  await settle();
  return { order, logged, duringOverlap, total: order.filter((o) => o === 'watch').length };
}

// ── the arms ──────────────────────────────────────────────────────────────────────────────────
async function main() {
  say('# fixture');
  say(`goals: ${GOALS} · per-goal synchronous block: ${BLOCK_MS} ms · expected sweep ≈ ${GOALS * BLOCK_MS} ms`);
  say(`goals root: ${goalsRoot}`);
  say('');

  say('# Y — the sweep, and a client on the same event loop');
  await warmModules();
  const red = await measure(buildWatch({ withYield: false }));
  say(`Y2 (yield DELETED — the pre-fix shape): sweep=${red.sweepMs}ms  max_wait=${red.maxWaitMs}ms  `
    + `answered_during_sweep=${red.answeredDuringSweep}/${red.requests}  warmup_max=${red.maxWarmupMs}ms`);
  const green = await measure(buildWatch({ withYield: true }));
  say(`Y1 (yield PRESENT — at HEAD):            sweep=${green.sweepMs}ms  max_wait=${green.maxWaitMs}ms  `
    + `answered_during_sweep=${green.answeredDuringSweep}/${green.requests}  warmup_max=${green.maxWarmupMs}ms`);
  const redWide = await measure(buildWatch({ withYield: false }), goalsRootWide);
  const greenWide = await measure(buildWatch({ withYield: true }), goalsRootWide);
  say(`Y3 the SAME two arms over ${GOALS_WIDE} goals (the sweep doubles):`);
  say(`   yield DELETED: sweep=${redWide.sweepMs}ms  max_wait=${redWide.maxWaitMs}ms`);
  say(`   yield PRESENT: sweep=${greenWide.sweepMs}ms  max_wait=${greenWide.maxWaitMs}ms`);
  say('');

  check('Y0 the prober is fast when nothing blocks — the control every wait below is read against',
    green.maxWarmupMs >= 0 && green.maxWarmupMs < 100, `warmup max ${green.maxWarmupMs}ms`);
  check('Y0 both arms really swept all four goals, doing the same work',
    red.pass.skipped.length === GOALS && green.pass.skipped.length === GOALS
      && green.pass.skipped.every((s) => s.reason === 'taskforce-unreadable'),
    `red=${red.pass.skipped.length} green=${green.pass.skipped.length} `
    + `reasons=${JSON.stringify([...new Set(green.pass.skipped.map((s) => s.reason))])}`);
  check('Y0 …and both sweeps cost the same wall time — the yield buys availability, not speed',
    Math.abs(green.sweepMs - red.sweepMs) < BLOCK_MS,
    `green=${green.sweepMs}ms red=${red.sweepMs}ms`);
  // The subprocess control. A pass that shelled ANYTHING would blow this by ~750 ms per goal (the
  // `check-acyclic` python `readTaskforce` runs is exactly that size), so a green arm here is the
  // evidence that this probe launched no process at all.
  const perGoal = (m, n) => m.sweepMs / n;
  check('Y0 …and each goal cost the 300 ms stub AND NOTHING ELSE — no subprocess ran in this probe',
    [[red, GOALS], [green, GOALS], [redWide, GOALS_WIDE], [greenWide, GOALS_WIDE]]
      .every(([m, n]) => perGoal(m, n) >= BLOCK_MS && perGoal(m, n) < BLOCK_MS + 60),
    [[red, GOALS], [green, GOALS], [redWide, GOALS_WIDE], [greenWide, GOALS_WIDE]]
      .map(([m, n]) => `${Math.round(perGoal(m, n))}ms`).join(' · '));

  check('Y2 RED · with the `await` deleted the client waits THE WHOLE SWEEP and is answered NOTHING '
    + 'inside it — the measured live defect, reproduced offline',
    red.maxWaitMs >= GOALS * BLOCK_MS * 0.8 && red.answeredDuringSweep === 0,
    `max_wait=${red.maxWaitMs}ms (sweep ${red.sweepMs}ms) answered_during=${red.answeredDuringSweep}`);

  check('Y1 the worst wait during the sweep is under 1 s — one goal, not the whole pass',
    green.maxWaitMs >= 0 && green.maxWaitMs < 1000, `max_wait=${green.maxWaitMs}ms`);
  check('Y1 …and it is a FEW GOAL-BLOCKS, not the sweep — a round trip needs a small fixed number '
    + 'of loop turns and the yield hands out one per goal',
    green.maxWaitMs < BLOCK_MS * 3.5,
    `max_wait=${green.maxWaitMs}ms = ${(green.maxWaitMs / BLOCK_MS).toFixed(1)} goal-blocks `
    + `(sweep ${green.sweepMs}ms = ${GOALS})`);
  check('Y1 …and the client is actually SERVED DURING the sweep, more than once',
    green.answeredDuringSweep >= 2,
    `answered inside the sweep: ${green.answeredDuringSweep} of ${green.requests}`);
  check('Y1 …and it is strictly better than the pre-fix wait on the same tree',
    green.maxWaitMs < red.maxWaitMs,
    `${red.maxWaitMs}ms -> ${green.maxWaitMs}ms `
    + `(${(red.maxWaitMs / Math.max(green.maxWaitMs, 1)).toFixed(1)}x)`);

  // ⚠ THE ARM THAT MATTERS MOST, and it is not the ratio above. A round trip costs a small FIXED
  // number of event-loop turns, and the yield hands out one turn per goal — so with the yield the
  // worst wait is a CONSTANT (a couple of goal-blocks) and without it, it is the SWEEP, which grows
  // with every goal added to the tree. At the acceptance wave's 3 seeded goals × ~2.4 s the pre-fix
  // block was 7.9 s median; at 6 it would have been ~15 s, and the gateway would have been down
  // more often than up. That growth is what this arm proves is gone.
  check('Y3 DOUBLING the tree doubles the pre-fix wait — the defect is LINEAR in goals',
    redWide.maxWaitMs > red.maxWaitMs * 1.6,
    `${GOALS} goals: ${red.maxWaitMs}ms -> ${GOALS_WIDE} goals: ${redWide.maxWaitMs}ms`);
  check('Y3 …and leaves the post-fix wait BOUNDED BY A FEW GOAL-BLOCKS AT BOTH SIZES — the wait no '
    + 'longer grows with the tree, which is the property that makes this fix scale',
    green.maxWaitMs < BLOCK_MS * 3.5 && greenWide.maxWaitMs < BLOCK_MS * 3.5,
    `${GOALS} goals: ${green.maxWaitMs}ms -> ${GOALS_WIDE} goals: ${greenWide.maxWaitMs}ms `
    + `(sweep ${green.sweepMs}ms -> ${greenWide.sweepMs}ms; bound ${BLOCK_MS * 3.5}ms)`);

  say('');
  say('# G — the cadence callback, compiled from `runtime/index.js` verbatim');
  const src = cadenceSlice();
  say(`cadence slice: ${src.split('\n').length} lines, ${src.length} bytes, from the real source`);
  if (!src.includes(GUARD_BLOCK)) {
    throw new Error('the guard block ABSENT in the cadence slice — G2 would measure nothing');
  }
  const g = await driveCadence(src);
  const gRed = await driveCadence(src.replace(GUARD_BLOCK, ''));
  say(`G1 (guard PRESENT): passes after two overlapping ticks = ${g.duringOverlap} · order = ${g.order.join(' -> ')}`);
  say(`G2 (guard DELETED): passes after two overlapping ticks = ${gRed.duringOverlap} · order = ${gRed.order.join(' -> ')}`);
  say('');

  check('G1 two ticks that OVERLAP produce exactly ONE pass — an overrunning pass is never joined '
    + 'by the next one', g.duringOverlap === 1, `passes started: ${g.duringOverlap}`);
  check('G1 …the dropped tick is NAMED at `debug`, once — an operator can see the overrun and is '
    + 'not paged for it',
    g.logged.filter((l) => l.level === 'debug' && /cadence skipped/.test(l.message)).length === 1,
    JSON.stringify(g.logged));
  check('G1 …and the tick is DROPPED, not queued: once the pass finishes, the NEXT tick runs and '
    + 'no third pass appears from the one that was skipped', g.total === 2,
    `passes over three ticks: ${g.total}`);
  check('G2 RED · with the guard block deleted the same two ticks start TWO passes over one tree',
    gRed.duringOverlap === 2, `passes started: ${gRed.duringOverlap}`);
  check('G3 the cadence order is unchanged — watch, then frozen, then tick',
    g.order.join(',') === 'watch,frozen,tick,watch,frozen,tick', g.order.join(' -> '));
}

let exitCode = 0;
main().catch((err) => {
  say(`FAIL  probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}).finally(() => {
  fs.rmSync(tmp, { recursive: true, force: true });
  exitCode = failures.length ? 1 : 0;
  say('');
  say(exitCode
    ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
    : 'RESULT: PASS — the lane watch pass yields between goals, so a client on the daemon\'s own '
      + 'event loop is answered DURING a sweep and waits a couple of goals rather than the whole '
      + 'sweep — a bound that no longer grows with the tree; and the cadence guard means an '
      + 'overrunning pass is never joined by the next tick.');
  say(`WALL_MS ${Date.now() - start}`);
  say(`EXIT ${exitCode}`);
  fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
  console.log(lines.join('\n'));
  process.exit(exitCode);
});
