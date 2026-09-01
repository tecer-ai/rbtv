'use strict';

// probe-ask-fields-carry — `d-owner-ask-shape`'s `kind`/`subject`/`options` fields, carried end to
// end over the REAL LIVE PATH: `ask-thread.js#postAsk` -> `chat/ask-store.js` (the gateway sender)
// -> `runtime/gateway/parse.js#parseRecordOwnerAsk` -> `runtime/internal-api/dispatch.js
// #handleRecordOwnerAsk` -> `state-store/heart/ask-record.js#openAsk` -> a REAL scratch ending
// store. Seat `ask-shape` (9488ebaa) proved the render/letter-resolution/schema halves by DIRECT
// CALL; this probe is what proves the CROSSING between them — the two-file gap its own memory entry
// (`chat/20260901-c-owner-ask-reserved-shape-lette.md`, ATTENTION 2) named and left unbuilt.
//
// NO FAKE FORWARDER. `probe-chat-ask-release.js` (ask-shape's own probe) proves `postAsk`'s
// RENDERING with a hand-rolled fake `askRecord`/forwarder — real by construction for that module's
// own decisions, but it cannot catch a field the wire never carries, because the fake never checks
// the wire shape. This probe's forwarder is the REAL `gateway/parse.js` + a REAL
// `createInternalApi` bound to a REAL scratch `heart.db` — the same in-process pattern
// `probe-inspect-asks.js` uses. No Slack and no daemon process; the store and the validation ladder
// are both real.

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const crypto = require('node:crypto');

const { createAskThreads } = require('../ask-thread');
const { createAskRecord } = require('../ask-store');
const { createInternalApi, ENVELOPE_VERSION } = require('../../runtime/internal-api/dispatch');
const { parseRequest } = require('../../runtime/gateway/parse');
const { bind, openEndingStoreFor } = require('../../state-store');
const askRecordCore = require('../../state-store/heart/ask-record');

const OUT = path.join(__dirname, 'probe-ask-fields-carry.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const GOAL = 'ask-fields-carry-goal';
const SEAT = 'leader';
const CHANNEL = 'C-GOAL-1';
const OWNER = 'U-OWNER';
const BOT = 'U-BOT';

const RECOVERY_OPTIONS = [
  { letter: 'a', arm: 'retry-with-change', text: 'restart it once more' },
  { letter: 'b', arm: 'drop-lane', text: "drop this seat's work" },
  { letter: 'c', arm: 'pause-goal', text: 'pause the whole goal', recommended: true, why: 'reason' },
];

// A real internal API, bound to a real scratch ending store, wired exactly as the daemon wires it
// (`runtime/server.js` builds `createInternalApi` with the daemon's own PRIVATE lane store as
// `heartStore` — `handleRecordOwnerAsk` never reads it for `record-owner-ask`, `ask-record.js`
// resolves `workspaceRoot` itself, per the `state-store/20260830-i-asks-read-from-the-private-sto`
// fix this probe's own memory read surfaced).
function buildLiveForwarder(workspaceRoot) {
  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({
    heartStore: { db: null }, spawnManager: {}, secret, workspaceRoot,
  });
  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };
  return {
    async forward(intent, payload) {
      let parsed;
      try {
        parsed = parseRequest({ intent, payload });
      } catch (err) {
        return { ok: false, error: { code: err.code, message: err.message } };
      }
      return api.dispatch({
        v: ENVELOPE_VERSION,
        id: crypto.randomUUID(),
        ts: new Date().toISOString(),
        auth: secret,
        sender: BRIDGE,
        intent,
        payload: parsed,
      });
    },
    async inspect() { return { ok: true, result: { rows: [] } }; },
  };
}

(async () => {
  const workspaceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-fields-carry-'));
  fs.mkdirSync(path.join(workspaceRoot, '.rbtv', 'goals', GOAL, 'coordination'), { recursive: true });

  const forwarder = buildLiveForwarder(workspaceRoot);
  const askRecord = createAskRecord({ forwarder, logger: null });

  const posts = [];
  const outbox = {
    async post(input) {
      posts.push(input);
      const ts = input.thread_ts == null ? '1724600000.100100' : `${input.thread_ts}-reply`;
      return { delivered: true, ts, error: null };
    },
  };
  const updates = [];
  const threads = createAskThreads({
    outbox,
    askRecord,
    updateMessage: async (u) => { updates.push(u); return { updated: true }; },
    authorizedSenders: [OWNER],
    botUserId: BOT,
    seatIsInteractive: () => true,
    workspaceRoot,
    logger: null,
  });

  // ── THE LIVE POST — kind/subject/options over the REAL crossing ────────────────────────────
  const r = await threads.postAsk({
    goalId: GOAL, channelId: CHANNEL, seatName: SEAT, label: 'recovery', kind: 'recovery',
    subject: 'the leader seat keeps failing to start',
    body: 'What happened: three identical crashes.\nLast words: exit 1.\nQuestion: what should I do with this seat?',
    options: RECOVERY_OPTIONS,
  });
  check('the ask posted and was recorded (the gateway did not refuse, the daemon-side writer did not refuse)',
    r.posted === true && r.recorded && r.recorded.recorded === true,
    { posted: r.posted, recorded: r.recorded });

  const askId = r.askId;
  const store = bind(openEndingStoreFor(workspaceRoot));
  const row = askId ? store.getAsk(askId) : null;

  check('LIVE PATH: the store row\'s `kind` is populated — NOT silently dropped by `ask-store.js`/`gateway/parse.js`/`dispatch.js`',
    !!row && row.kind === 'recovery', { row: row && { kind: row.kind, subject: row.subject } });
  check('LIVE PATH: the store row\'s `subject` is populated',
    !!row && row.subject === 'the leader seat keeps failing to start', { subject: row && row.subject });
  check('LIVE PATH: the store row\'s `options_json` round-trips the exact table posted',
    !!row && (() => {
      let parsed;
      try { parsed = JSON.parse(row.options_json); } catch { return false; }
      return Array.isArray(parsed) && parsed.length === 3 && parsed[0].letter === 'a' && parsed[0].arm === 'retry-with-change';
    })(),
    { options_json: row && row.options_json });

  // ── DIGEST-FACING READ — `ask-record.js#listOpenAsks`, the same function the 2-hourly digest
  // spends, confirms the populated row is visible through THAT read path too, not just `getAsk`.
  const listed = askRecordCore.listOpenAsks(workspaceRoot);
  const listedRow = listed.find((x) => x.id === askId);
  check('the digest\'s own `listOpenAsks(workspaceRoot)` read sees the populated `kind`/`subject`',
    !!listedRow && listedRow.kind === 'recovery' && listedRow.subject === 'the leader seat keeps failing to start',
    { listedRow });

  // ── A LETTER REPLY STILL RESOLVES — `release()`'s letter->arm mapping reads the in-process
  // `options` argument (chat-bridge.js's own askThreads Map, per `d-owner-ask-shape`'s design —
  // never the DB), so this proves no regression: the live crossing this seat built does not change
  // where `release()` gets its table from.
  const released = await threads.release({
    goalId: GOAL, channelId: CHANNEL, seatName: SEAT, askId, threadTs: askId,
    senderId: OWNER, text: 'a please retry with the fixed config', kind: 'recovery', options: RECOVERY_OPTIONS,
  });
  check('a lettered reply (`a`) on the live-posted recovery ask resolves through `release()` to the mapped arm, carrying the owner\'s comment',
    released.released === true && released.outcome === 'retry-with-change' && released.family === 'recovery'
    && released.comments === 'please retry with the fixed config',
    { released });

  // ── THE REAP ALSO CARRIES OVER THE LIVE PATH — confirms the reap leg of the same crossing
  // (act: 'reap') still works with the widened allowlist (kind/subject/options are OPEN-only,
  // never sent on a reap — this call has none of them and must still succeed).
  const rowAfter = store.getAsk(askId);
  check('the reap landed through the SAME live forwarder (act: reap) and the row is closed',
    !!rowAfter && rowAfter.state === 'closed', { state: rowAfter && rowAfter.state });

  // ── RED CONTROL, IN-PROBE — a mutant of `ask-store.js#openAsk` that drops kind/subject/options
  // from the payload (the pre-fix shape) reproduces the live defect against the SAME store: the row
  // lands with empty fields even though the ask itself still posts and records successfully.
  {
    const askStorePath = require.resolve('../ask-store');
    const src = fs.readFileSync(askStorePath, 'utf8');
    const needle = 'if (kind != null) payload.kind = String(kind);\n    if (subject != null) payload.subject = String(subject);\n    if (options != null) payload.options = options;\n';
    if (!src.includes(needle)) {
      check('RED CONTROL: located the exact live fields-forwarding lines to mutate beside the source (never touching the committed file)', false, { askStorePath });
    } else {
      // The mutation drops exactly the three lines this seat's fix ADDS — the payload reverts to
      // its pre-fix shape (`{act, goal, seat, thread, corpus, label}`) with no other change.
      const mutSrc = src.replace(needle, '');
      const mutBeside = path.join(os.tmpdir(), `ask-store-mutant-${process.pid}-${Date.now()}.js`);
      fs.writeFileSync(mutBeside, mutSrc);
      try {
        // eslint-disable-next-line global-require, import/no-dynamic-require -- red control, a scratch copy beside the source
        const mut = require(mutBeside);
        const mutRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'ask-fields-carry-mutant-'));
        fs.mkdirSync(path.join(mutRoot, '.rbtv', 'goals', GOAL, 'coordination'), { recursive: true });
        const mutForwarder = buildLiveForwarder(mutRoot);
        const mutAskRecord = mut.createAskRecord({ forwarder: mutForwarder, logger: null });
        const mutThreads = createAskThreads({
          outbox, askRecord: mutAskRecord, updateMessage: async () => ({ updated: true }),
          authorizedSenders: [OWNER], botUserId: BOT, seatIsInteractive: () => true,
          workspaceRoot: mutRoot, logger: null,
        });
        const mutR = await mutThreads.postAsk({
          goalId: GOAL, channelId: CHANNEL, seatName: SEAT, label: 'recovery', kind: 'recovery',
          subject: 'mutant subject', body: 'mutant body\nline2\nQuestion: x?', options: RECOVERY_OPTIONS,
        });
        const mutStore = bind(openEndingStoreFor(mutRoot));
        const mutRow = mutR.askId ? mutStore.getAsk(mutR.askId) : null;
        check('RED CONTROL: the pre-fix mutant reproduces the live defect — the ask still posts and records, but `kind`/`subject`/`options_json` land EMPTY',
          mutR.posted === true && mutR.recorded && mutR.recorded.recorded === true
          && !!mutRow && mutRow.kind === '' && mutRow.subject === '' && mutRow.options_json === '',
          { posted: mutR.posted, recorded: mutR.recorded && mutR.recorded.recorded, mutRow: mutRow && { kind: mutRow.kind, subject: mutRow.subject, options_json: mutRow.options_json } });
      } finally {
        fs.rmSync(mutBeside, { force: true });
      }
    }
  }

  const pass = checks.every((c) => c.pass);
  const lines = checks.map((c) => `${c.pass ? 'PASS' : 'FAIL'}  ${c.name}${c.pass ? '' : ` — ${JSON.stringify(c.evidence)}`}`);
  fs.writeFileSync(OUT, [
    `probe-ask-fields-carry — ${checks.filter((c) => c.pass).length}/${checks.length} — ${Date.now() - t0}ms`,
    ...lines,
    '',
  ].join('\n'));
  // eslint-disable-next-line no-console
  console.log(`EXIT=${pass ? 0 : 1} PASS=${pass} CHECKS=${checks.length}`);
  process.exit(pass ? 0 : 1);
})().catch((err) => {
  fs.writeFileSync(OUT, `FATAL ${err.stack || err.message}\n`);
  // eslint-disable-next-line no-console
  console.error(err);
  process.exit(1);
});
