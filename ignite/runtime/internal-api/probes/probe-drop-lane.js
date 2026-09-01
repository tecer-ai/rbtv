'use strict';

// probe-drop-lane — THE SIXTEENTH INTENT (owner rulings `d-recovery-drop-is-one-lane-permanent`,
// `d-recovery-abandoned-is-an-ending`, `d-recovery-drop-stops-live-work`, 2026-08-31,
// `redesign-continue-1`): the owner's `drop-lane` recovery reply, crossing the daemon boundary and
// stopping a lane's live turn AND marking it abandoned, in that order, in ONE authorized act.
//
// WHY THIS PROBE EXISTS, AND WHAT `probe-chat-recovery-dispatch.js` NO LONGER PROVES. This intent's
// FIRST shape (commit 8c1023af) composed the stop client-side, in the bridge, as two wire calls
// (`inspect` then `kill-session`) — proven by a bridge-level probe over an INJECTED fake forwarder.
// The live daemon (`dl-live-proof`, 2026-09-01) found that shape could never work: `kill-session`'s
// authorization (`authz.js#canKillSession`) admits only `sender.kind === 'owner'` or a
// `creator-seat` match, and the chat bridge always authenticates as `kind: 'bridge'` — which
// satisfies neither, for ANY session, ever. A fake forwarder never enforces `authz.js`, which is
// exactly why that defect shipped past every unit check. This probe closes that gap the only way
// that actually proves anything: in-process parse + dispatch + authz over a REAL `authz.js`, a REAL
// (scratch) ending store, and a stub `heartStore`/`spawnManager` that RECORD call order — so the
// stop-then-mark sequence, the half-completion arms, and the authorization boundary are all
// measured against the genuine policy module, never a stand-in that would wave it through.
//
// In-process only: nothing here spawns, opens a live state directory, or reaches Slack.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-drop-lane.out');
fs.writeFileSync(outPath, '');

const { createInternalApi, ENVELOPE_VERSION } = require('../dispatch');
const { parseRequest } = require('../../gateway/parse');
const { openEndingStore, bind } = require('../../../state-store');

function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL = 'probe-drop-goal';
const SEAT_P = 'worker-p';
const SEAT_Q = 'worker-q';
const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };
const OWNER = { id: 'probe-owner', kind: 'owner' };

function writeRegister(root, names) {
  const goalsRoot = path.join(root, '.rbtv', 'goals');
  fs.mkdirSync(goalsRoot, { recursive: true });
  fs.writeFileSync(path.join(goalsRoot, 'goals.csv'),
    `name,creation date,due date,type,goal-kind,status\n${names.map((n) => `${n},2026-09-01,,one-shot,interactive,briefed`).join('\n')}\n`);
}

function laneWorkdir(root, goal, seat) {
  return path.join(root, '.rbtv', 'goals', goal, 'seats', seat);
}

// A minimal, SCRIPTABLE stand-in for `heartStore` and `spawnManager` — the two handles
// `handleKillSession` already holds and `dropLane()` now consumes directly. Every call is
// RECORDED, in order, which is the entire point: proving the sequence, not just the outcome.
function makeStubs({ liveRows = [] } = {}) {
  const calls = [];
  let killShouldThrow = null;
  const heartStore = {
    listExecutionsByStatus(status) {
      calls.push({ fn: 'listExecutionsByStatus', status });
      return liveRows.filter((r) => r.status === status);
    },
  };
  const spawnManager = {
    async kill(execId) {
      calls.push({ fn: 'kill', execId });
      if (killShouldThrow) throw new Error(killShouldThrow);
      return { execId, killed: true, signal: null };
    },
  };
  return {
    heartStore,
    spawnManager,
    calls,
    setKillThrows(msg) { killShouldThrow = msg; },
  };
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE in-process parse+dispatch+authz over a SCRATCH ending store and a REAL authz.js — heartStore/spawnManager are scriptable stubs that RECORD call order (no live state dir, no spawn, no Slack).');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'drop-lane-probe-'));
  fs.mkdirSync(path.join(root, '.rbtv', 'goals', GOAL), { recursive: true });
  writeRegister(root, [GOAL]);
  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const store = bind(db);
  const secret = crypto.randomBytes(32).toString('hex');

  async function call(sender, payload, api) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'drop-lane', payload });
    } catch (err) {
      return { body: { ok: false, error: { code: err.code, message: err.message } }, gatewayRefused: true };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION, id: crypto.randomUUID(), ts: new Date().toISOString(),
      auth: secret, sender, intent: 'drop-lane', payload: parsed,
    });
    return { body: res, gatewayRefused: false };
  }

  // ── A. LIVE lane: stop then mark, in that exact order ───────────────────────────────────────
  {
    const stubs = makeStubs({
      liveRows: [{ exec_id: 501, status: 'running', args: JSON.stringify({ workdir: laneWorkdir(root, GOAL, SEAT_P) }) }],
    });
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const r = await call(BRIDGE, { goal: GOAL, seat: SEAT_P }, api);
    check('A1: a LIVE lane returns ok:true, stopped:true',
      r.body.ok === true && r.body.result.stopped === true, JSON.stringify(r.body));
    const fns = stubs.calls.map((c) => c.fn);
    check('A2: the ORDER is list-live-sessions, then kill, before anything is marked',
      fns[0] === 'listExecutionsByStatus' && fns.includes('kill') && fns.indexOf('kill') > fns.indexOf('listExecutionsByStatus'),
      JSON.stringify(stubs.calls));
    check('A3: kill targets the exec_id the live-session scan found for this exact (goal, seat)',
      stubs.calls.find((c) => c.fn === 'kill').execId === 501, JSON.stringify(stubs.calls));
    check('A4: the lane is genuinely marked abandoned in the REAL store',
      !!store.getSeatAbandonment({ goal: GOAL, seat: SEAT_P }), JSON.stringify(store.getSeatAbandonment({ goal: GOAL, seat: SEAT_P })));
  }

  // ── B. NOTHING live: clean no-op straight to the mark, no kill call at all ──────────────────
  {
    const stubs = makeStubs({ liveRows: [] });
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const r = await call(BRIDGE, { goal: GOAL, seat: SEAT_Q }, api);
    check('B1: nothing live is ok:true, stopped:false, and NO kill call at all',
      r.body.ok === true && r.body.result.stopped === false && !stubs.calls.some((c) => c.fn === 'kill'),
      JSON.stringify({ result: r.body.result, calls: stubs.calls }));
  }

  // ── C. HALF-COMPLETION (stop fails): kill throws — NOTHING is marked ────────────────────────
  {
    const SEAT_C = 'worker-c';
    const stubs = makeStubs({
      liveRows: [{ exec_id: 777, status: 'launching', args: JSON.stringify({ workdir: laneWorkdir(root, GOAL, SEAT_C) }) }],
    });
    stubs.setKillThrows('carrier refused signal');
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const r = await call(BRIDGE, { goal: GOAL, seat: SEAT_C }, api);
    check('C1: a stop failure returns ok:false, never ok:true',
      r.body.ok === false, JSON.stringify(r.body));
    check('C2: the error says live work was NOT stopped and the lane was NOT dropped',
      /NOT stopped/.test(r.body.error.message) && /NOT dropped/.test(r.body.error.message), r.body.error && r.body.error.message);
    check('C3: the lane is NOT marked abandoned in the REAL store — never both true',
      store.getSeatAbandonment({ goal: GOAL, seat: SEAT_C }) === null, JSON.stringify(store.getSeatAbandonment({ goal: GOAL, seat: SEAT_C })));
  }

  // ── D. RETRY: the SAME lane, stop no longer needed (already gone), completes the mark ───────
  {
    const SEAT_C = 'worker-c'; // same lane as (C) — its stop already "happened" (nothing live now)
    const stubs = makeStubs({ liveRows: [] });
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const r = await call(BRIDGE, { goal: GOAL, seat: SEAT_C }, api);
    check('D1: retrying after a stop failure (now nothing live) completes the mark — ok:true',
      r.body.ok === true, JSON.stringify(r.body));
    check('D2: the lane IS now marked abandoned',
      !!store.getSeatAbandonment({ goal: GOAL, seat: SEAT_C }), JSON.stringify(store.getSeatAbandonment({ goal: GOAL, seat: SEAT_C })));
  }

  // ── E. IDEMPOTENCY: dropping an ALREADY-abandoned lane succeeds as a no-op ──────────────────
  {
    const stubs = makeStubs({ liveRows: [] });
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const r = await call(BRIDGE, { goal: GOAL, seat: SEAT_P }, api); // SEAT_P was already dropped in (A)
    check('E1: dropping an already-abandoned lane is ok:true, idempotent:true, not an error',
      r.body.ok === true && r.body.result.idempotent === true, JSON.stringify(r.body));
  }

  // ── F. THE DISCRIMINATING CONTROL: authorization is BRIDGE-ONLY, same shape as `pause-resume` /
  // `start-execution` — an owner sender and an ordinary agent sender are BOTH refused, proving
  // `canDropLane` is a real gate and not merely reachable by anyone who can reach the gateway.
  {
    const stubs = makeStubs({ liveRows: [] });
    const api = createInternalApi({
      heartStore: stubs.heartStore, spawnManager: stubs.spawnManager, secret, workspaceRoot: root, logger: () => {},
    });
    const asOwner = await call(OWNER, { goal: GOAL, seat: 'worker-owner-drop' }, api);
    check('F1: an OWNER-kind sender is REFUSED — this intent is bridge-only, exactly like pause-resume/start-execution',
      asOwner.body.ok === false && asOwner.body.error.code === 'UNAUTHORIZED_SENDER', JSON.stringify(asOwner.body));
    const asAgent = await call({ id: 'probe-agent', kind: 'agent' }, { goal: GOAL, seat: 'worker-agent-drop' }, api);
    check('F2: an ordinary AGENT sender is also REFUSED — not an open door',
      asAgent.body.ok === false && asAgent.body.error.code === 'UNAUTHORIZED_SENDER', JSON.stringify(asAgent.body));
    const asBridge = await call(BRIDGE, { goal: GOAL, seat: 'worker-bridge-control-drop' }, api);
    check('F3: the BRIDGE sender IS admitted — the control that proves F1/F2 measured the gate, not a fixture fault',
      asBridge.body.ok === true, JSON.stringify(asBridge.body));
  }

  // ── G. THE PROVER'S SPECIFIC MECHANISM, RE-DISPROVEN HERE (not just in the scratch worktree) ──
  {
    let threw = null;
    try {
      parseRequest({ intent: 'kill-session', payload: { id: 1, chat_user: 'U0123ABC' } });
    } catch (err) { threw = err; }
    check('G1: `kill-session` REJECTS a chat_user field outright — it could never have carried the identity the live prover proposed threading through it',
      threw !== null && /chat_user/.test(threw.message), threw && threw.message);
  }

  try { db.close(); } catch {}
  try { fs.rmSync(root, { recursive: true, force: true }); } catch {}

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
