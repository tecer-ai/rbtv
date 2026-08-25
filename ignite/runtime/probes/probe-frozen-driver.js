'use strict';

// probe-frozen-driver — THE TICK DRIVER AND THE POST-RESTART SUPPRESSION WINDOW.
//
// `observation/frozen.selftest.js` proves what the INVARIANT decides. This probe proves the two
// things that stood between that module and the owner:
//
//   1. SOMETHING CALLS IT, EVERY CADENCE, WITH REAL FACTS AND THE CONFIGURED WINDOW. Nothing did:
//      `frozen.js` shipped with "wiring itself is not done here — nothing calls either module yet",
//      and `frozen_window_min` had no reader. Here the driver is run on an injected clock over
//      facts shaped exactly as `supervisor/lane-watch.js` collects them, and the alarm that comes out
//      is read back off the persisted registry.
//   2. A DAEMON RESTART SUPPRESSES IT FOR THE CONFIGURED WINDOW (task #113 criterion 2). Incident
//      BIT-7 swung a relaunch grant's pickup latency from 17 s to 10 m 35 s ACROSS a restart; every
//      latency-shaped check read that as a stall. The fact comes off the WATCHDOG's append-only
//      outage ledger, because the daemon's own memory is what the restart erased.
//
// Fixture workspace, injected clock, injected registry and ledger files. No daemon, no Slack, no
// watchdog process: the ledger rows are written in the watchdog's own line format.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-frozen-driver.out');
fs.writeFileSync(outPath, '');

const { runFrozenPass } = require('../frozen-pass');
const { restartSuppression, ledgerPathFor } = require('../../observation/restart-window');
const { frozenFactsFor } = require('../../supervisor/lane-watch');
const { OBSERVATION_FIELDS } = require('../../observation/frozen');
const { seedRecoveryConfig, loadRecoveryConfig } = require('../../supervisor/recovery-config');
const { openEndingStore, bind } = require('../../state-store');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL = 'meet-transcript-summarizer';
const SYS = 'Csystem';
const MINUTE = 60 * 1000;

// The nine facts, minus the channel the driver adds. Shaped exactly as `lane-watch.js` collects
// them, and asserted against `OBSERVATION_FIELDS` below so a rename over there reddens here.
function facts(overrides = {}) {
  return [{
    goal_id: GOAL,
    goal_state: 'running',
    paused: false,
    eligible_launch: false,
    open_ask: false,
    provider_backoff_waiting: false,
    reroute_pending: false,
    evidence_pointer: '/w/.rbtv/goals/meet-transcript-summarizer',
    ...overrides,
  }];
}

function ledgerRow(file, decision, atMs, extra = {}) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.appendFileSync(file, `${JSON.stringify({
    at: new Date(atMs).toISOString().replace(/\.\d{3}Z$/, 'Z'),
    decision,
    reason: 'probe fixture',
    unit: 'ignite-daemon.service',
    ...extra,
  })}\n`);
}

function alarmRows(file) {
  try {
    const doc = JSON.parse(fs.readFileSync(file, 'utf8'));
    return Array.isArray(doc.rows) ? doc.rows : (Array.isArray(doc.alarms) ? doc.alarms : []);
  } catch {
    return [];
  }
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE workspace + injected clock/registry/ledger; no daemon, no watchdog process, no Slack');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'frozen-driver-'));
  const emptyRegistry = path.join(root, 'registry.jsonl');
  fs.writeFileSync(emptyRegistry, '');
  const ledger = path.join(root, '.rbtv', 'runtime', 'watchdog', 'outage-ledger.jsonl');

  // ── 0. THE OBSERVATION SHAPE IS THE INVARIANT'S OWN ─────────────────────────────────────────
  const supplied = Object.keys(facts()[0]).concat(['channel_id']).sort();
  check('0: the driver supplies exactly the nine fields `frozen.js` requires — a renamed field over there reddens here, it does not silently drop an arm',
    supplied.join(',') === [...OBSERVATION_FIELDS].sort().join(','),
    `supplied=${supplied.join(',')} required=${[...OBSERVATION_FIELDS].sort().join(',')}`);

  // ── A. NO RECOVERY CONFIG: NOT ARMED, AND NO FALLBACK WINDOW [spec-recovery §2.1] ───────────
  {
    const said = [];
    const r = await runFrozenPass({
      facts: facts(), workspaceRoot: root, systemChannelId: SYS,
      registryFile: emptyRegistry, now: () => Date.now(), logger: (m) => said.push(m),
    });
    check('A1: with no recovery.json the pass arms NOTHING and names the reason — it never falls back to a window in code',
      r.armed === false && r.reason === 'recovery-config-error', JSON.stringify({ armed: r.armed, reason: r.reason }));
    check('A2: and it said so out loud', said.some((m) => m.level === 'warn' && /recovery config/.test(m.message)), '');
  }

  seedRecoveryConfig(root);
  const config = loadRecoveryConfig({ workspace: root });
  const windowMin = config.frozen_window_min;
  check('SETUP: the seeded recovery config carries frozen_window_min', Number.isInteger(windowMin) && windowMin > 0, `frozen_window_min=${windowMin}`);

  // ── B. NO SYSTEM CHANNEL: NOT ARMED ─────────────────────────────────────────────────────────
  {
    const r = await runFrozenPass({
      facts: facts(), workspaceRoot: root, systemChannelId: null, registryFile: emptyRegistry,
    });
    check('B1: with no system channel the pass arms nothing — a frozen goal observed with nowhere to report it is not an observation',
      r.armed === false && r.reason === 'no-system-channel', JSON.stringify({ armed: r.armed, reason: r.reason }));
  }

  // ── C. THE DRIVER FIRES ON CADENCE, AND ONLY PAST THE WINDOW ────────────────────────────────
  const alarmStore = path.join(root, 'alarms.json');
  const outboxStore = path.join(root, 'outbox.json');
  const holds = path.join(root, 'holds.json');
  const T0 = Date.parse('2026-08-25T12:00:00Z');
  const pass = (atMs, extra = {}) => runFrozenPass({
    facts: extra.facts || facts(extra.overrides || {}),
    workspaceRoot: root,
    systemChannelId: SYS,
    registryFile: emptyRegistry,
    alarmStorePath: alarmStore,
    outboxStore,
    holdsFile: holds,
    ledgerFile: ledger,
    suppressWindowMin: extra.suppressWindowMin === undefined ? null : extra.suppressWindowMin,
    now: () => atMs,
  });

  {
    let r = await pass(T0);
    check('C1: the FIRST cadence starts the hold clock and alarms nothing — the window is what keeps a one-tick gap between two seats off the owner\'s phone',
      r.armed === true && r.emitted.length === 0 && r.results[0].frozen === true,
      JSON.stringify(r.results[0]));

    r = await pass(T0 + (windowMin - 1) * MINUTE);
    check('C2: one minute INSIDE the window still alarms nothing',
      r.emitted.length === 0 && alarmRows(alarmStore).length === 0, JSON.stringify(r.results[0]));

    r = await pass(T0 + (windowMin + 1) * MINUTE);
    check('C3: past the window the driver emits — this is the alarm nothing was calling for',
      r.emitted.length === 1 && r.emitted[0] === GOAL, JSON.stringify(r.results[0]));

    const rows = alarmRows(alarmStore);
    check('C4: ONE registry row, open, keyed on condition-class + subject',
      rows.length === 1 && rows[0].state === 'open' && rows[0].signature === `frozen-goal:goal:${GOAL}`,
      JSON.stringify(rows[0] || {}));
    check('C5: the alarm names the four required fields — an owner-facing page that says what was observed',
      rows.length === 1 && rows[0].condition && rows[0].evidence_pointer && rows[0].what_would_clear_it
        && rows[0].immediate === false,
      JSON.stringify(rows[0] || {}));

    const outbox = JSON.parse(fs.readFileSync(outboxStore, 'utf8')).records;
    check('C6: the post is a DURABLE pending-delivery record with the reason on it — the daemon resolves no Slack credential (r-cutover-gated) and the digest re-surfaces the condition [C-17, §9.2]',
      outbox.length === 1 && outbox[0].kind === 'alarm' && outbox[0].state === 'pending-delivery'
        && /r-cutover-gated/.test(outbox[0].last_error),
      JSON.stringify({ kind: outbox[0].kind, state: outbox[0].state, last_error: outbox[0].last_error }));

    r = await pass(T0 + (windowMin + 2) * MINUTE);
    check('C7: the next cadence is DEDUPED — one emission per open signature, not one per tick',
      r.emitted.length === 0 && alarmRows(alarmStore).length === 1, JSON.stringify(r.results[0]));

    // The [C-5] exclusions still hold through the driver: the facts travel, they are not re-derived.
    r = await pass(T0 + (windowMin + 3) * MINUTE, { overrides: { provider_backoff_waiting: true } });
    check('C8: a provider-backoff-waiting lane is EXCLUDED at the predicate and the standing row is cleared — waiting on purpose is the opposite of frozen [C-5]',
      r.emitted.length === 0 && r.results[0].frozen === false && /provider-backoff/.test(r.results[0].reason),
      JSON.stringify(r.results[0]));
  }

  // ── D. THE POST-RESTART SUPPRESSION WINDOW (task #113 criterion 2) ──────────────────────────
  //
  // RED BEFORE / GREEN AFTER, in one pair: the SAME frozen goal at the SAME instant, with and
  // without a watchdog-recorded restart on the ledger.
  const alarmStore2 = path.join(root, 'alarms-2.json');
  const outbox2 = path.join(root, 'outbox-2.json');
  const holds2 = path.join(root, 'holds-2.json');
  const T1 = Date.parse('2026-08-26T09:00:00Z');
  const pass2 = (atMs, opts = {}) => runFrozenPass({
    facts: facts(),
    workspaceRoot: root,
    systemChannelId: SYS,
    registryFile: emptyRegistry,
    alarmStorePath: alarmStore2,
    outboxStore: outbox2,
    holdsFile: holds2,
    ledgerFile: ledger,
    now: () => atMs,
    ...opts,
  });

  {
    // Hold the goal past the window first, so the ONLY thing standing between it and an alarm is
    // the suppression.
    await pass2(T1);
    let r = await pass2(T1 + (windowMin + 1) * MINUTE, { suppressWindowMin: 15 });
    check('D1: with NO restart on the ledger the alarm fires — suppression is a window after an event, never a mute',
      r.suppressed === false && r.emitted.length === 1, JSON.stringify({ suppressed: r.suppressed, emitted: r.emitted, why: r.suppression && r.suppression.reason }));

    // A second episode: clear the condition, then re-freeze — this time with a restart 5 minutes ago.
    await pass2(T1 + (windowMin + 2) * MINUTE, { facts: facts({ eligible_launch: true }), suppressWindowMin: 15 });
    const T2 = T1 + 60 * MINUTE;
    await pass2(T2);
    ledgerRow(ledger, 'recovered', T2 + (windowMin - 4) * MINUTE, { outage_seconds: 11115, unhealthy_passes: 185 });
    const alarmsBefore = alarmRows(alarmStore2).filter((x) => x.state === 'open').length;
    r = await pass2(T2 + (windowMin + 1) * MINUTE, { suppressWindowMin: 15 });
    check('D2: a watchdog-detected restart 5 minutes ago SUPPRESSES the whole pass — after a restart every goal is late for the same reason, and that reason is not a stall [task #113]',
      r.suppressed === true && r.checked === 0 && r.emitted === undefined,
      JSON.stringify({ suppressed: r.suppressed, checked: r.checked, reason: r.reason }));
    check('D3: and nothing was emitted while suppressed',
      alarmRows(alarmStore2).filter((x) => x.state === 'open').length === alarmsBefore,
      `open rows before=${alarmsBefore} after=${alarmRows(alarmStore2).filter((x) => x.state === 'open').length}`);

    r = await pass2(T2 + 40 * MINUTE, { suppressWindowMin: 15 });
    check('D4: PAST the suppression window the same condition alarms — suppressed is not dropped',
      r.suppressed === false && r.emitted.length === 1,
      JSON.stringify({ suppressed: r.suppressed, emitted: r.emitted }));
  }

  // ── E. THE SUPPRESSION PREDICATE ITSELF ─────────────────────────────────────────────────────
  {
    const at = Date.parse('2026-08-26T12:00:00Z');
    const file = path.join(root, 'ledger-e.jsonl');

    let s = restartSuppression({ ledgerFile: file, windowMin: null, now: () => at });
    check('E1: NO configured window means NO suppression, and it is reported as unarmed — a suppression nobody configured must never silence a real page',
      s.suppressed === false && s.armed === false && s.reason === 'no-window-configured', JSON.stringify(s));

    s = restartSuppression({ ledgerFile: file, windowMin: 15, now: () => at });
    check('E2: an absent ledger suppresses nothing', s.suppressed === false && s.armed === true, JSON.stringify(s));

    ledgerRow(file, 'observed-not-healthy', at - 2 * MINUTE);
    ledgerRow(file, 'restart-withheld-gate', at - MINUTE);
    s = restartSuppression({ ledgerFile: file, windowMin: 15, now: () => at });
    check('E3: a non-healthy observation and a WITHHELD restart are not restarts — the daemon never went away, so nothing about its queue depth changed',
      s.suppressed === false, JSON.stringify(s));

    ledgerRow(file, 'restart-taken', at - 3 * MINUTE);
    s = restartSuppression({ ledgerFile: file, windowMin: 15, now: () => at });
    check('E4: a `restart-taken` row inside the window suppresses', s.suppressed === true && s.decision === 'restart-taken', JSON.stringify(s));

    s = restartSuppression({ ledgerFile: file, windowMin: 2, now: () => at });
    check('E5: the same row with a SHORTER window does not — the number is the owner\'s, read from configuration, never a constant here',
      s.suppressed === false && s.reason === 'outside-the-window', JSON.stringify(s));

    // A ledger big enough to force the bounded tail read: the newest restart must still be found.
    const big = path.join(root, 'ledger-big.jsonl');
    for (let i = 0; i < 4000; i += 1) ledgerRow(big, 'observed-not-healthy', at - (10 * 60 * MINUTE) + i);
    ledgerRow(big, 'recovered', at - MINUTE, { outage_seconds: 5 });
    s = restartSuppression({ ledgerFile: big, windowMin: 15, now: () => at });
    check('E6: the read is BOUNDED to the tail and still finds the newest restart — a ledger that is never rotated must not make this a growing per-cadence cost',
      s.suppressed === true && s.decision === 'recovered',
      `${JSON.stringify(s)} size=${fs.statSync(big).size}`);

    const derived = ledgerPathFor('/w', {});
    check('E7: the default ledger path is DERIVED from the workspace — no hardcoded absolute path (repo law), and `RBTV_WATCHDOG_LEDGER` overrides it exactly as it does for the watchdog',
      derived === path.resolve('/w/.rbtv/runtime/watchdog/outage-ledger.jsonl')
        && ledgerPathFor('/w', { RBTV_WATCHDOG_LEDGER: '/elsewhere/l.jsonl' }) === '/elsewhere/l.jsonl',
      derived);
  }

  // ── F. THE FACTS COME FROM THE PASS THAT ALREADY COMPUTES THEM ──────────────────────────────
  {
    const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'frozen-facts-'));
    const goalFolder = path.join(ws, '.rbtv', 'goals', GOAL);
    fs.mkdirSync(path.join(goalFolder, 'coordination', 'asks'), { recursive: true });
    const db = openEndingStore(path.join(ws, '.rbtv', 'runtime', 'ignite', 'heart.db'));
    const store = bind(db);
    store.writeGoalWord({ goal: GOAL, stored: 'running', who_stamped: 'system', evidence_pointer: 'probe' });

    const engine = { heartStore: { db } };
    let f = frozenFactsFor({ goal: GOAL, goalFolder, engine, pickup: { enqueued: [] }, seats: [] });
    check('F1: the lane watch reads the goal-state row, not a marker file — "running" is the store\'s word',
      f && f.goal_state === 'running' && f.paused === false, JSON.stringify(f));
    check('F2: with nothing enqueued this pass, `eligible_launch` is false — the seed\'s own answer, never a second derivation',
      f && f.eligible_launch === false, `${f && f.eligible_launch}`);

    f = frozenFactsFor({ goal: GOAL, goalFolder, engine, pickup: { enqueued: ['audio-smith'] }, seats: [] });
    check('F3: a seed that enqueued work makes `eligible_launch` true — the scheduler has something to do, so there is nothing to say',
      f && f.eligible_launch === true, `${f && f.eligible_launch}`);

    store.insertAsk({ ask_id: '1724500001.000100', goal: GOAL, seat: 'goal-master', label: 'work-content', evidence_pointer: path.join(goalFolder, 'coordination', 'asks', 'a.txt') });
    store.postAsk({ ask_id: '1724500001.000100', posted_at: '2026-08-25 08:20' });
    f = frozenFactsFor({ goal: GOAL, goalFolder, engine, pickup: { enqueued: [] }, seats: [] });
    check('F4: an open POSTED ask makes `open_ask` true — the owner has been asked, so nobody is stuck without being told',
      f && f.open_ask === true, `${f && f.open_ask}`);

    check('F5: every field the invariant validates is present and non-empty on a collected fact set',
      f && OBSERVATION_FIELDS.filter((k) => k !== 'channel_id')
        .every((k) => f[k] !== undefined && f[k] !== null && f[k] !== ''),
      JSON.stringify(f));

    try { db.close(); } catch { /* done with it */ }
    try { fs.rmSync(ws, { recursive: true, force: true }); } catch { /* tmp */ }
  }

  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`RESULT: ${failed.length ? 'FAIL' : 'PASS'} — ${checks.length - failed.length}/${checks.length} checks`);
  out(`WALL_MS ${Date.now() - start}`);
  out(`EXIT ${failed.length ? 1 : 0}`);
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(failed.length ? 1 : 0);
}

main().catch((err) => {
  out(`PROBE FAULT: ${err && err.stack ? err.stack : err}`);
  out('EXIT 1');
  console.log(fs.readFileSync(outPath, 'utf8'));
  process.exit(1);
});
