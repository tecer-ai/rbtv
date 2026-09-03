'use strict';

// probe-disposition-post — the JOIN `d-hold4-wire-disposition-post` builds: posting the
// close-or-keep ask `supervisor/last-lane-ask.js#mintLastLaneAsk` mints (`posted:0`, nothing
// posts or parses a reply today) and both reply arms, proven against REAL server-side code, not a
// stand-in for it:
//
//   STAGE A (posting) — a REAL disposition record + REAL `open_asks` row (minted directly via the
//   proven `mintLastLaneAsk`, same call `last-lane-ask.selftest.js` case 4 makes — the minting half
//   is NOT rebuilt here) is read back by `chat/disposition-poster.js#checkAndPost` through a fake
//   gateway forwarder whose `inspect`/`record-owner-ask` handlers call the REAL
//   `listUnpostedDispositions` / `recordOwnerAsk` / `markDispositionPosted` in-process, against the
//   SAME real ending store the mint used — no Slack, no gateway socket, no daemon process, exactly
//   `probe-inspect-asks.js`'s own evidence class ("three asks were recorded through the daemon
//   writer"). This proves the row that ends up `posted:1` is the real store's row, not a fake ack.
//
//   STAGE B (reply arms) — a full `buildBridge` harness (`probe-chat-recovery-dispatch.js`'s own
//   shape: mock Socket-Mode transport, scriptable fake forwarder) proves `close`, `keep`, and a
//   discriminating control against the REAL `ask-thread.js#release` + `reply-grammar.js` +
//   `disposition-thread.js#createDispositionDispatch`, wired exactly as `chat-bridge.js` wires them
//   in production (`closeGoal: null` — see `disposition-thread.js`'s header for why).

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const assert = require('node:assert');
const {
  openEndingStoreFor, closeEndingStores, bind: bindStore,
} = require('../../state-store');
const { recordOwnerAsk } = require('../../state-store/heart/ask-record');
const { mintLastLaneAsk, listUnpostedDispositions, markDispositionPosted } = require('../../supervisor/last-lane-ask');
const { createDispositionPoster } = require('../disposition-poster');
const { buildBridge } = require('../index');
const { closeGoal } = require('../../state-store/heart/close-goal');
const { openHeartStore, closeHeartStore } = require('../../state-store/heart/heart-store');
const { reconcileGoal } = require('../../supervisor/reconcile');
const { seedRecoveryConfig, loadRecoveryConfig } = require('../../supervisor/recovery-config');

const OUT = path.join(__dirname, 'probe-disposition-post.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence: evidence || {} }); };

const OWNER = 'U-OWNER';
const GOAL = 'test-disposition-goal';
const SEAT = 'worker-dropped';

// ── STAGE A: posting, against the REAL store ──────────────────────────────────────────────────
function stageA() {
  const workspaceRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'disposition-post-a-'));
  fs.mkdirSync(path.join(workspaceRoot, '.rbtv', 'goals', GOAL), { recursive: true });
  const db = openEndingStoreFor(workspaceRoot);
  const api = bindStore(db);
  try {
    // The minting half, REUSED not rebuilt — the exact call `last-lane-ask.selftest.js` case 4
    // makes, proven idempotent and correct there. This probe starts FROM a real minted, unposted
    // record + row (posted:0), which is the premise this seat re-verified against the tree.
    const minted = mintLastLaneAsk({
      store: api, workspaceRoot, goal: GOAL, abandonedSeats: [{ seat: SEAT }], at: '2026-09-01T00:00:00Z',
    });
    assert.ok(minted.minted, 'setup: the disposition ask must mint');
    const preRow = api.getAsk(minted.askId);
    check('A0 SETUP: the minted row is open, posted=0 — the exact premise re-verified before this change',
      preRow && preRow.state === 'open' && preRow.posted === 0, { preRow });

    // The fake gateway forwarder: `inspect disposition-asks` and `record-owner-ask` call the REAL
    // server-side functions in-process, against the SAME real ending store the mint used — the
    // network hop is faked, the daemon's own code is not.
    const posted = [];
    let nextTs = 800;
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
        if (intent === 'inspect' && payload.target === 'disposition-asks') {
          return { ok: true, result: { target: 'disposition-asks', rows: listUnpostedDispositions(workspaceRoot) } };
        }
        if (intent === 'record-owner-ask') {
          const out = recordOwnerAsk({
            workspaceRoot,
            act: payload.act,
            goal: payload.goal,
            seat: payload.seat,
            thread: payload.thread,
            corpus: payload.corpus,
            label: payload.label || 'work-content',
          });
          if (!out.recorded) return { ok: true, result: { recorded: false, reason: out.reason } };
          // The SAME post-processing `dispatch.js`'s real handler runs — see this seat's edit there.
          if (payload.act === 'open' && payload.label === 'recovery' && out.already !== true) {
            try { markDispositionPosted(workspaceRoot, { goal: payload.goal }, { askId: out.ask_id }); } catch { /* best-effort, same as production */ }
          }
          return { ok: true, result: out };
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

    return { workspaceRoot, api, minted, posted, built, forwarder };
  } catch (err) {
    closeEndingStores();
    throw err;
  }
}

async function runStageA() {
  const { workspaceRoot, api, minted, posted, built } = stageA();
  try {
    await built.bridge.start();
    // The goal↔channel map (`goal-channel-map.js`, task 7.58) must know this goal BEFORE
    // `postOwnerAsk` can resolve a channel for it — the same precondition `openDispositionAsk`
    // meets for STAGE B below via `registerGoal`.
    await built.bridge.registerGoal(GOAL);
    const poster = createDispositionPoster({ forwarder: built.forwarder, postOwnerAsk: built.bridge.postOwnerAsk, logger: () => {} });

    const before = listUnpostedDispositions(workspaceRoot);
    check('A1: BEFORE posting, the unposted-disposition reader finds exactly this one record',
      before.length === 1 && before[0].goal === GOAL, { before });

    const first = await poster.checkAndPost();
    check('A2: the poster pass checks one and posts one', first.checked === 1 && first.posted === 1, { first });

    check('A3: exactly ONE Slack message was posted', posted.length === 1, { posted });
    const text = posted[0] && posted[0].text;
    check('A4: the posted text carries the goal id and both options in plain owner words',
      typeof text === 'string' && text.includes(GOAL) && /\bclose\b/.test(text) && /\bkeep\b/.test(text),
      { text });
    check('A5: the post landed in a NEW thread of its own (thread_ts minted by this post, not the mint-time hash id)',
      posted[0].threadTs === null, { posted: posted[0] });

    // The file record now carries `posted_ask_id` — RED-FIRST comparison: `before` (pre-post) had
    // no such field on the same record; this is the field this seat's `markDispositionPosted` adds.
    const recordFile = path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'asks', `${minted.askId}.json`);
    const recordAfter = JSON.parse(fs.readFileSync(recordFile, 'utf8'));
    check('A6: the file record is stamped `posted_ask_id` after posting (it carried none before)',
      typeof recordAfter.posted_ask_id === 'string' && recordAfter.posted_ask_id.length > 0,
      { recordAfter });

    // The REAL open_asks row for the NEW thread-ts-keyed ask — the one `countOpenAsks` (the
    // suspension chain `dl-last-lane-ask` already proved) actually reads.
    const newRow = api.getAsk(recordAfter.posted_ask_id);
    check('A7 (DoD clause 2): the NEW open_asks row is state=open AND posted=1',
      newRow && newRow.state === 'open' && newRow.posted === 1, { newRow });
    check('A7b: the ORIGINAL mint-time row (hash id) stays posted=0 forever — the same accepted shape `exhaustion.js`\'s recovery-lane rows use, not a new defect',
      api.getAsk(minted.askId) && api.getAsk(minted.askId).posted === 0, { originalRow: api.getAsk(minted.askId) });
    check('A8: the goal now has an OPEN, POSTED ask — the suspension chain (`dl-last-lane-ask`\'s proven work) is live for this goal',
      api.countOpenAsks(GOAL) === 1, { count: api.countOpenAsks(GOAL) });

    // IDEMPOTENCY — a second pass must post nothing more (the whole point of stamping posted_ask_id).
    const second = await poster.checkAndPost();
    check('A9: a second poster pass finds nothing left to post — no duplicate thread',
      second.checked === 0 && second.posted === 0, { second });
    check('A10: still exactly ONE Slack message after the second pass', posted.length === 1, { posted });

    built.bridge.stop();
  } finally {
    closeEndingStores();
  }
}

// ── STAGE B: the two reply arms + a discriminating control, against a full bridge harness ───────
function harnessB() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'disposition-post-b-'));
  const posted = [];
  let nextTs = 900;
  const chans = [];
  let nextChan = 1;
  const slack = {
    posted,
    async authTest() { return { ok: true, userId: 'U-BOT' }; },
    async openDm(userId) { return { ok: true, channel: 'D_OWNER', userId }; },
    async createChannel({ name }) { const ch = { id: `C${String(nextChan++).padStart(4, '0')}`, name }; chans.push(ch); return { ok: true, channel: ch }; },
    async listChannels() { return { ok: true, channels: chans, nextCursor: null }; },
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
  const calls = [];
  const forwarder = {
    async forward(intent, payload) {
      calls.push({ intent, payload });
      // `record-owner-ask` (open + reap) — the ask-store's own ledger, same fake ack shape
      // `probe-chat-recovery-dispatch.js` uses: this probe is not re-testing the mint/post
      // pipeline (STAGE A already proved that against the real store) — only what a `close`/`keep`
      // reply does AFTER the ask releases.
      return { ok: true, result: { recorded: true, ask_id: payload.thread || null, state: payload.act === 'reap' ? 'closed' : 'open', relaunch: { queued: true } } };
    },
  };
  const built = buildBridge({
    gatewayAddr: '127.0.0.1:0', bridgeToken: 'stub', workspaceRoot: root, channelPrefix: 'test-',
    stateFile: path.join(root, 'state.json'), allowlist: [OWNER],
    slack: { apiBase: 'http://127.0.0.1:0', appToken: null, botToken: null },
  }, {
    logger: () => {}, makeTransport: () => slack, forwarderImpl: forwarder,
    replyLegOptions: { pollMs: 3600000 }, busFerryOptions: { pollMs: 3600000 },
  });
  return {
    root, posted, calls, bridge: built.bridge,
    reply(channel, threadTs, text, user = OWNER) {
      return built.bridge.onChatMessage({
        chatUserId: user, chatThreadId: `${channel}:${threadTs}`, text,
        _channel: channel, _threadTs: threadTs, _msgTs: `${Date.now()}.1`, _inThread: true, _channelType: 'channel',
      });
    },
  };
}

async function openDispositionAsk(h) {
  const reg = await h.bridge.registerGoal(GOAL);
  const ask = await h.bridge.postOwnerAsk({
    goalId: GOAL, seatName: SEAT, kind: 'goal-disposition', label: 'recovery',
    body: `*GOAL*: ${GOAL}\n\nReply with one word: close · keep`,
  });
  return { channelId: reg.channelId, askId: ask.askId };
}

async function runStageB() {
  // ── KEEP: settles the ask, posts confirmation, no goal-state act attempted ───────────────────
  {
    const h = harnessB();
    await h.bridge.start();
    const { channelId, askId } = await openDispositionAsk(h);
    const out = await h.reply(channelId, askId, 'keep');
    check('B1 keep: the ask RELEASES', out.released === true, { out: { released: out.released, outcome: out.outcome } });
    check('B2 keep: dispatch reports ok:true, action:keep', out.dispatched && out.dispatched.ok === true && out.dispatched.action === 'keep', { dispatched: out.dispatched });
    const posted = h.posted[h.posted.length - 1];
    check('B3 keep: the thread is told the goal stays open and nothing launches on its own',
      posted && /kept open/.test(posted.text) && /nothing launches on its own/.test(posted.text), { text: posted && posted.text });
    h.bridge.stop();
  }

  // ── CLOSE: the ask still releases (owner-visible half done), and `closeGoal` is now WIRED
  //           (`d-goal-closed-word`) — this harness's forwarder is a GENERIC fake ack (same one
  //           `record-owner-ask` uses), so what it proves is the DISPATCH plumbing: `close`
  //           reaches `chat-bridge.js`'s port, which calls the `close-goal` gateway intent with the
  //           right shape, and a success is reported honestly. It does NOT exercise the real
  //           store write — that is STAGE C, against a real ending store + real `reconcileGoal`. ──
  {
    const h = harnessB();
    await h.bridge.start();
    const { channelId, askId } = await openDispositionAsk(h);
    const out = await h.reply(channelId, askId, 'close');
    check('C1 close: the ask still RELEASES — the owner-visible half is done regardless of the daemon-side act',
      out.released === true, { out: { released: out.released, outcome: out.outcome } });
    check('C2 close (CHANGED — was ok:false before `d-goal-closed-word` wired the port): dispatch reports ok:true, action:close',
      out.dispatched && out.dispatched.ok === true && out.dispatched.action === 'close', { dispatched: out.dispatched });
    const posted = h.posted[h.posted.length - 1];
    check('C3 close (CHANGED, same reason): the thread is told the goal closed — given up on, not a success',
      posted && /closed — given up on, not a success/.test(posted.text), { text: posted && posted.text });
    check('C4 close (CHANGED, same reason): exactly ONE `close-goal` intent call, naming this goal and the ask',
      h.calls.filter((c) => c.intent === 'close-goal').length === 1
        && h.calls.find((c) => c.intent === 'close-goal').payload.goal === GOAL,
      { intents: h.calls.map((c) => c.intent), closeGoalCall: h.calls.find((c) => c.intent === 'close-goal') });
    check('C5 close: no `pause-resume` or `drop-lane` intent was ever called for this outcome — only `record-owner-ask` (the release) and `close-goal`',
      !h.calls.some((c) => c.intent !== 'record-owner-ask' && c.intent !== 'close-goal'), { intents: h.calls.map((c) => c.intent) });
    h.bridge.stop();
  }

  // ── DISCRIMINATING CONTROL: an unrelated token does NOT settle the ask ────────────────────────
  {
    const h = harnessB();
    await h.bridge.start();
    const { channelId, askId } = await openDispositionAsk(h);
    const out = await h.reply(channelId, askId, 'banana');
    check('D1 CONTROL: an unrelated first word does NOT release the ask', out.released === false, { out: { released: out.released, reason: out.reason } });
    check('D2 CONTROL: it is refused as UNPARSED, never silently accepted as an outcome', out.reason === 'unparsed', { reason: out.reason });
    const posted = h.posted[h.posted.length - 1];
    check('D3 CONTROL: the NACK names the disposition thread\'s own two-word vocabulary, not the approval/recovery ones',
      posted && /close, keep/.test(posted.text), { text: posted && posted.text });
    check('D4 CONTROL: no dispatch action of any kind was returned for the unparsed reply', !out.dispatched, { dispatched: out.dispatched });
    h.bridge.stop();
  }
}

// ── STAGE C (`d-goal-closed-word`): the REAL store write + the REAL reconcile skip ──────────────
//
// STAGE A proved posting against the real store; STAGE B proved the dispatch plumbing against a
// fake ack. Neither exercises `state-store/heart/close-goal.js#closeGoal` (the daemon-side
// executor `chat-bridge.js`'s port calls via the `close-goal` intent) or `reconcile.js`'s new
// `closed` skip — this stage does, against a REAL ending store, following the EXACT fixture shape
// `finish-gate.selftest.js` proves the `finished` skip with (`openHeartStore` + a minimal
// leader-only taskforce), so the two terminal words are proven the same way.
function writeSeatC(goalFolder, seat) {
  const dir = path.join(goalFolder, 'seats', seat);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'seat.md'), `---\nseat: ${seat}\nharness: bash\nmodel: probe-disposition-post\n---\n\nbody\n`);
}
function writeTaskforceC(goalFolder, seats) {
  const rows = seats.map((s) => `tf,${s},,bash,probe-disposition-post,high,35,`);
  fs.writeFileSync(path.join(goalFolder, 'taskforce.csv'), `taskforce-id,seat,after,harness,model,effort,ctx-refresh,milestone-id\n${rows.join('\n')}\n`);
}
function writeSessionsC(goalFolder, rows) {
  const cols = ['session-id', 'seat', 'harness', 'native-session-id', 'workdir',
    'recorded', 'started', 'ended', 'pid', 'pid-starttime', 'tty', 'disposition',
    'disposition-writer', 'execution', 'checkin', 'model', 'hold-anchor'];
  const linesOut = [cols.join(',')];
  for (const r of rows) linesOut.push(cols.map((c) => (r[c] == null ? '' : String(r[c]).replace(/,/g, ' '))).join(','));
  fs.writeFileSync(path.join(goalFolder, 'sessions.csv'), `${linesOut.join('\n')}\n`);
}
function writeMessagesC(goalFolder, blocks) {
  const dir = path.join(goalFolder, 'coordination');
  fs.mkdirSync(dir, { recursive: true });
  const parts = ['# messages\n'];
  for (const b of blocks) {
    parts.push(`## ${b.num} | from: ${b.sender} | to: ${b.to} | type: ${b.type} | ${b.ts || '2026-08-19 12:00'}`);
    parts.push('');
    parts.push(b.body || 'body');
    parts.push('');
  }
  fs.writeFileSync(path.join(dir, 'messages.md'), parts.join('\n'));
}
function fixtureRunningOwed(goalFolder) {
  writeSeatC(goalFolder, 'leader');
  writeTaskforceC(goalFolder, ['leader']);
  writeSessionsC(goalFolder, [
    { 'session-id': 'ld1', seat: 'leader', started: '2026-08-19 10:00', ended: '2026-08-19 10:05', disposition: 'done', checkin: '2026-08-19 10:04' },
  ]);
  writeMessagesC(goalFolder, [
    { num: 1, sender: 'worker', to: 'leader', type: 'note', ts: '2026-08-19 11:00', body: 'please sit' },
  ]);
}
const readyEmptyC = {
  ready: new Map(), granted: new Map(), rows: [], reason: null,
};

async function runStageC() {
  const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'disposition-post-c-'));
  const CGOAL = 'test-close-real';
  const RGOAL = 'test-close-control-running';

  // C0 — the REAL executor: closeGoal() against a real workspace + a real goals.csv roster.
  {
    const workspaceRoot = fs.mkdtempSync(path.join(tmpRoot, 'exec-ws-'));
    const goalsRoot = path.join(workspaceRoot, '.rbtv', 'goals');
    fs.mkdirSync(path.join(goalsRoot, CGOAL), { recursive: true });
    fs.writeFileSync(path.join(goalsRoot, 'goals.csv'), `name,created\n${CGOAL},2026-09-01\n`);
    try {
      const out = await closeGoal({ workspaceRoot, goal: CGOAL, askId: 'T-ASK-1' });
      check('C0a: closeGoal() finds the live goal and writes the row',
        out.found === true && out.idempotent === false && out.state && out.state.stored === 'closed', { out });
      check('C0b (DoD): the stored word is `closed`, NEVER `finished`',
        out.state && out.state.stored === 'closed' && out.state.stored !== 'finished', { state: out.state });
      check('C0c: who_stamped is `owner` — an owner act, not a system one', out.state && out.state.who_stamped === 'owner', { state: out.state });

      const again = await closeGoal({ workspaceRoot, goal: CGOAL, askId: 'T-ASK-1' });
      check('C0d IDEMPOTENT: a repeated close on an already-closed goal is a no-op, not a second ruling',
        again.found === true && again.idempotent === true, { again });

      // The highest-value success/finished reader, direct: `isGoalFinished` must NEVER read a
      // closed goal as done. Proven against BOTH words on the SAME store, so the negative is not
      // just "nothing writes finished" — a genuinely finished CONTROL row returns true.
      const { bind: bindApi, openEndingStoreFor: openFor } = require('../../state-store');
      const api = bindApi(openFor(workspaceRoot));
      check('C0e (DoD — highest-value reader): isGoalFinished(closed goal) is false',
        api.isGoalFinished(CGOAL) === false, { isGoalFinished: api.isGoalFinished(CGOAL) });
      check('C0f: isGoalPaused/isGoalRunning also both false for a closed goal — none of the three success/running predicates fire',
        api.isGoalPaused(CGOAL) === false && api.isGoalRunning(CGOAL) === false,
        { paused: api.isGoalPaused(CGOAL), running: api.isGoalRunning(CGOAL) });

      const FGOAL = 'test-close-control-finished';
      fs.mkdirSync(path.join(goalsRoot, FGOAL), { recursive: true });
      api.writeGoalWord({
        goal: FGOAL, stored: 'finished', who_stamped: 'system', evidence_pointer: 'control row',
      });
      check('C0g CONTROL: a genuinely `finished` row DOES read isGoalFinished === true — the predicate itself discriminates',
        api.isGoalFinished(FGOAL) === true, { isGoalFinished: api.isGoalFinished(FGOAL) });
    } finally {
      require('../../state-store').closeEndingStores();
    }
  }

  // C1 — the REAL reconcile skip, same fixture shape `finish-gate.selftest.js` proves `finished`
  // with. `closed` fixture: skipped, no rebuild, no launch. `running` CONTROL: proceeds past the
  // check (rebuilds or launches) — the discriminating pass the DoD asks for.
  {
    const store = openHeartStore({ dbPath: path.join(fs.mkdtempSync(path.join(tmpRoot, 'hs-')), 'heart.db') });
    const recWs = fs.mkdtempSync(path.join(tmpRoot, 'rec-ws-'));
    seedRecoveryConfig(recWs);
    const fx = {
      workspaceRoot: recWs,
      recovery: loadRecoveryConfig({ workspace: recWs }),
      countersFile: path.join(recWs, 'counters.json'),
      lanesFile: path.join(recWs, 'provider-lanes.json'),
    };
    try {
      // `laneIsClosed`/`laneIsPaused` resolve the goal NAME from the folder's basename
      // (`ending-reads.js#goalNameOf`, no override arg) — the same contract production has (a
      // goal IS named by its `.rbtv/goals/<goal>` folder), so the fixture folder must be named
      // EXACTLY the goal it represents, not an mkdtemp-random sibling.
      const closedFolder = path.join(tmpRoot, CGOAL);
      fs.mkdirSync(closedFolder, { recursive: true });
      fixtureRunningOwed(closedFolder);
      require('../../state-store').bind(store.db).writeGoalWord({
        goal: CGOAL, stored: 'closed', who_stamped: 'owner', evidence_pointer: 'reconcile-skip fixture',
      });
      const rebuiltClosed = [];
      const rClosed = reconcileGoal({
        goal: CGOAL, goalFolder: closedFolder, engine: { heartStore: store }, say: () => {}, force: true,
        readyAnswer: readyEmptyC, live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuiltClosed.push(a); return { ok: true }; },
        ...fx,
      });
      check('C1a (DoD): reconcile SKIPS a closed goal, `skipped: "closed"` — never `"finished"`',
        rClosed.skipped === 'closed', { rClosed });
      check('C1b: no room-rebuilt, no launch, on the closed goal',
        rebuiltClosed.length === 0 && (rClosed.actions || []).filter((a) => a.kind === 'enqueue').length === 0,
        { rebuiltClosed, actions: rClosed.actions });

      const runningFolder = path.join(tmpRoot, RGOAL);
      fs.mkdirSync(runningFolder, { recursive: true });
      fixtureRunningOwed(runningFolder);
      const rebuiltRunning = [];
      const rRunning = reconcileGoal({
        goal: RGOAL, goalFolder: runningFolder, engine: { heartStore: store }, say: () => {}, force: true,
        readyAnswer: readyEmptyC, live: new Set(), promptFn: () => 'BOOT',
        recoverFn: (a) => { rebuiltRunning.push(a); return { ok: true }; },
        ...fx,
      });
      check('C1c CONTROL (discriminating pass): the SAME fixture shape, un-closed, is NOT skipped — reconcile proceeds (rebuilds or launches)',
        rRunning.skipped !== 'closed' && rRunning.skipped !== 'finished'
          && (rebuiltRunning.length > 0 || (rRunning.actions || []).filter((a) => a.kind === 'enqueue').length > 0),
        { rRunning, rebuiltRunning });
    } finally {
      store.close();
      closeHeartStore();
    }
  }

  fs.rmSync(tmpRoot, { recursive: true, force: true });
}

(async () => {
  await runStageA();
  await runStageB();
  await runStageC();

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: { probe: 'probe-disposition-post', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-disposition-post EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-disposition-post EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
