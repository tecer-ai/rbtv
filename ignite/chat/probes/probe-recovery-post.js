'use strict';

// probe-recovery-post — `redesign-continue-1` seat `recovery-story`: the recovery ask's
// `composeRecoveryBody` fills the ruled template (subject/body/options/more, R-A4/R-A5) from a
// REAL exhausted lane, not a hand-typed fixture string. STAGE A mints the lane through the REAL
// `supervisor/exhaustion.js#exhaust` (the same function `reconcile.js#countRetry` calls at N,
// proven end-to-end by `reconcile.selftest.js`'s own red-first arm for the seat's-own-diagnostic
// ordering) against a REAL ending store, then reads it back through `recovery-poster.js#checkAndPost`
// via a fake gateway forwarder whose `inspect`/`record-owner-ask` handlers call the REAL
// `listUnpostedLanes`/`recordOwnerAsk`/`markLanePosted` in-process — `probe-disposition-post.js`'s
// own evidence class, adapted to the recovery-lane shape.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const assert = require('node:assert');
const {
  openEndingStoreFor, closeEndingStores, bind: bindStore,
} = require('../../state-store');
const { recordOwnerAsk } = require('../../state-store/heart/ask-record');
const {
  exhaust, listUnpostedLanes, markLanePosted, ASK_OPTIONS,
} = require('../../supervisor/exhaustion');
const counters = require('../../supervisor/attempt-counters');
const { createRecoveryPoster, composeRecoveryBody } = require('../recovery-poster');
const { buildBridge } = require('../index');

const OUT = path.join(__dirname, 'probe-recovery-post.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const OWNER = 'U-OWNER';
const GOAL = 'test-recovery-post-goal';
const SEAT = 'worker-a';

// ── STAGE A: posting, against the REAL store + the REAL exhaustion writer ────────────────────────
function stageA() {
  const workspaceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'recovery-post-a-'));
  fs.mkdirSync(path.join(workspaceRoot, '.rbtv', 'goals', GOAL), { recursive: true });
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    // The seat's own transcript, an ABSOLUTE path under the workspace — the shape
    // `lifecycle_exec.py#ending_transcript` requires of a real export (never the `<kind>:<seat>`
    // fallback token), so `evidence_pointer` on the lane proves the vault-relative rendering.
    const transcriptPath = path.join(workspaceRoot, '.rbtv', 'goals', GOAL, 'seats', SEAT, 'transcript.jsonl');
    // The seat stamps its OWN ending (`who_stamped: 'seat'`) — `reconcile.js`'s call site reads
    // exactly this row before calling `exhaust`; that read is proven in `reconcile.selftest.js`'s
    // DoD-2 red-first arm. This probe starts FROM its output — the real diagnostic + pointer — and
    // proves what the POSTER does with them, not the read again.
    api.stampSeatDeclare({
      goal: GOAL, seat: SEAT, ending: 'incomplete', armed: 1,
      diagnostic: 'the plan file would not parse: unexpected token at line 12',
      evidence_pointer: transcriptPath, replace: true,
    });
    const out = exhaust({
      store: api,
      workspaceRoot,
      goal: GOAL,
      seat: SEAT,
      driver: counters.DRIVERS.RECONCILE_CLASS_A,
      reasonClass: 'incomplete',
      lastWords: 'the plan file would not parse: unexpected token at line 12',
      seatEvidencePointer: transcriptPath,
      firstAt: '2026-09-01T20:00:00Z',
      lastAt: '2026-09-01T20:12:00Z',
      outcome: 'enqueue',
      attempts: 3,
      at: '2026-09-01T20:12:00Z',
    });
    assert.ok(out.ask && out.ask.ask_id, 'setup: exhaust() must mint a grouped ask');

    const posted = [];
    let nextTs = 700;
    const slack = {
      posted,
      async authTest() { return { ok: true, userId: 'U-BOT' }; },
      async openDm(userId) { return { ok: true, channel: 'D_OWNER', userId }; },
      async createChannel({ name }) { return { ok: true, channel: { id: `Ctest-${name}`, name } }; },
      async listChannels() { return { ok: true, channels: [], nextCursor: null }; },
      async archiveChannel() { return { ok: true }; },
      async sendToOwner({ channel, threadTs, text }) {
        const ts = `${nextTs}.${String(nextTs++).padStart(6, '0')}`;
        posted.push({ channel, threadTs: threadTs ?? null, text, ts });
        return { delivered: true, ts };
      },
      async updateMessage(u) { const t = posted.find((q) => q.ts === u.ts); if (t) t.text = u.text; return { updated: true }; },
      async start() { return { connected: true }; },
      stop() {},
    };
    const forwarder = {
      async forward(intent, payload) {
        if (intent === 'inspect' && payload.target === 'recovery-lanes') {
          return { ok: true, result: { target: 'recovery-lanes', rows: listUnpostedLanes(workspaceRoot) } };
        }
        if (intent === 'record-owner-ask') {
          const res = recordOwnerAsk({
            workspaceRoot,
            act: payload.act,
            goal: payload.goal,
            seat: payload.seat,
            thread: payload.thread,
            corpus: payload.corpus,
            label: payload.label || 'work-content',
          });
          if (!res.recorded) return { ok: true, result: { recorded: false, reason: res.reason } };
          // The SAME post-processing `dispatch.js`'s real handler runs (`markLanePosted` beside
          // `record-owner-ask`'s open) — see this seat's edit there, unchanged by this probe.
          if (payload.act === 'open' && payload.label === 'recovery' && res.already !== true) {
            try { markLanePosted(workspaceRoot, { goal: payload.goal, seat: payload.seat }, { askId: res.ask_id }); } catch { /* best-effort, same as production */ }
          }
          return { ok: true, result: res };
        }
        return { ok: true, result: {} };
      },
    };
    const built = buildBridge({
      gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', workspaceRoot, channelPrefix: 'test-',
      stateFile: path.join(workspaceRoot, 'state.json'), allowlist: [OWNER],
      slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
    }, {
      logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder,
      replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 },
    });
    return {
      workspaceRoot, api, out, posted, built, forwarder,
    };
  } catch (err) {
    closeEndingStores();
    throw err;
  }
}

async function runStageA() {
  const {
    workspaceRoot, api, out, posted, built,
  } = stageA();
  try {
    await built.bridge.start();
    await built.bridge.registerGoal(GOAL);
    const poster = createRecoveryPoster({ forwarder: built.forwarder, postOwnerAsk: built.bridge.postOwnerAsk, logger: () => {} });

    const before = listUnpostedLanes(workspaceRoot);
    check('A1: BEFORE posting, the unposted-lane reader finds exactly this one lane',
      before.length === 1 && before[0].goal === GOAL && before[0].seat === SEAT, { before });
    check('A1b: the lane carries the SEAT\'S OWN diagnostic as `last_words`, never a `refusal_text` field',
      before[0].last_words === 'the plan file would not parse: unexpected token at line 12'
        && before[0].refusal_text === undefined,
      { lane: before[0] });
    check('A1c: `evidence_pointer` is rendered VAULT-RELATIVE (Slack cannot link a VPS absolute path)',
      before[0].evidence_pointer === path.join('.rbtv', 'goals', GOAL, 'seats', SEAT, 'transcript.jsonl'),
      { evidence_pointer: before[0].evidence_pointer });

    const first = await poster.checkAndPost();
    check('A2: the poster pass checks one and posts one', first.checked === 1 && first.posted === 1, { first });
    check('A3: exactly ONE Slack message was posted', posted.length === 1, { posted });

    const text = posted[0] && posted[0].text;
    check('A4: the rendered text carries the reserved first-line marker and the plain-words subject — never the raw `driver:`/`reason:`/`attempts:`/`LANE:` tokens',
      typeof text === 'string'
        && /NEEDS YOUR ANSWER/.test(text)
        && /keeps quitting before finishing/.test(text)
        && !/LANE:/.test(text) && !/driver:/.test(text) && !/reason:/.test(text) && !/attempts:/.test(text),
      { text });
    check('A5: the seat\'s own diagnostic is quoted verbatim under "Its last words"',
      typeof text === 'string' && text.includes('the plan file would not parse: unexpected token at line 12'),
      { text });
    check('A6: all three lettered options are present, `c` (pause-goal) recommended at 3 attempts',
      typeof text === 'string' && /^a\)/m.test(text) && /^b\)/m.test(text)
        && /^c\).*recommended/m.test(text),
      { text });
    check('A7: the vault-relative transcript path is the `More:` pointer, not the absolute one',
      typeof text === 'string' && text.includes(path.join('.rbtv', 'goals', GOAL, 'seats', SEAT, 'transcript.jsonl'))
        && !text.includes(workspaceRoot),
      { text });

    const recordFile = path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks', `${out.ask.ask_id}.json`);
    const recordAfter = JSON.parse(fs.readFileSync(recordFile, 'utf8'));
    const laneAfter = recordAfter.lanes.find((l) => l.goal === GOAL && l.seat === SEAT);
    check('A8: the file record\'s lane is stamped `posted_ask_id` after posting',
      laneAfter && typeof laneAfter.posted_ask_id === 'string' && laneAfter.posted_ask_id.length > 0,
      { laneAfter });

    const newRow = api.getAsk(laneAfter.posted_ask_id);
    check('A9: the NEW open_asks row (keyed by the real thread id) is state=open, posted=1',
      newRow && newRow.state === 'open' && newRow.posted === 1, { newRow });

    const second = await poster.checkAndPost();
    check('A10 IDEMPOTENCY: a second pass finds nothing left to post — no duplicate thread',
      second.checked === 0 && second.posted === 0, { second });
    check('A11: still exactly ONE Slack message after the second pass', posted.length === 1, { posted });

    built.bridge.stop();
  } finally {
    closeEndingStores();
  }
}

// ── UNIT: composeRecoveryBody's `unread` framing (no seat text exists to quote at all) ───────────
function runUnitUnread() {
  const composed = composeRecoveryBody({
    goal: GOAL, seat: 'chair-seat', driver: counters.DRIVERS.RECONCILE_RESPAWN, reason_class: 'unread',
    last_words: null, evidence_pointer: null, attempts: 3, first_at: null, last_at: null, outcome: 'enqueue',
  });
  check('U1: `unread` with no seat words renders the DoD-3 exact none-line, never a fabricated quote',
    composed.body.includes('Its last words: (none — it never got far enough to say anything)'),
    { body: composed.body });
  check('U2: the subject reads "keeps failing to start" for `unread`, per DoD 3',
    composed.subject === 'the chair-seat seat keeps failing to start', { subject: composed.subject });
}

// ── UNIT: composeRecoveryBody's `launch-refused` outcome overrides the subject ────────────────────
function runUnitLaunchRefused() {
  const composed = composeRecoveryBody({
    goal: GOAL, seat: 'flaky-seat', driver: counters.DRIVERS.RECONCILE_CLASS_A, reason_class: 'incomplete',
    last_words: null, evidence_pointer: null, attempts: 3, first_at: null, last_at: null, outcome: 'launch-refused',
  });
  check('U3: `outcome: launch-refused` renders the "cannot be started" subject regardless of `reason_class`',
    composed.subject === 'the flaky-seat seat cannot be started', { subject: composed.subject });
}

// ── UNIT: the old hand-duplicated options constant is gone — ASK_OPTIONS is the one source ────────
function runUnitOneSourceOfOptions() {
  const composed = composeRecoveryBody({
    goal: GOAL, seat: SEAT, driver: counters.DRIVERS.RECONCILE_CLASS_A, reason_class: 'incomplete',
    last_words: 'x', evidence_pointer: null, attempts: 3, first_at: null, last_at: null, outcome: 'enqueue',
  });
  const arms = composed.options.map((o) => o.arm).sort();
  check('U4: the composed options\' arms are EXACTLY `exhaustion.js#ASK_OPTIONS` — one source, no second hand-kept ladder',
    JSON.stringify(arms) === JSON.stringify([...ASK_OPTIONS].sort()), { arms, ASK_OPTIONS });
}

(async () => {
  await runStageA();
  runUnitUnread();
  runUnitLaunchRefused();
  runUnitOneSourceOfOptions();

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-recovery-post', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-recovery-post EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-recovery-post EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
