'use strict';

// probe-session-turn-split — task 7.46. Does the store hold SESSION and TURN as two levels?
//
// WHAT WOULD MAKE THIS PROBE WORTHLESS, stated first because it is the trap this task's criteria
// name explicitly: writing a turn-level status into a column and reading it back exercises THE
// COLUMN, NOT THE SPLIT. A probe like that passes on the pre-7.46 store too. The check that
// discriminates is the MULTI-TURN SESSION — turn ends → session stays alive → a NEXT TURN starts
// on the same session — because the flat enum could not express it at all: there was exactly one
// status, so a session whose turn had reported `done` was indistinguishable from a session that
// had ended.
//
// So this probe carries a CONTROL first: it asserts, against the pre-split shape, that the thing
// it is about to prove was impossible. A bar its predecessor could pass is not a bar.
//
// The live store is never opened. Every fixture here is a throwaway file in tmpdir
// (`r-746-schema-pregrant`: throwaway store only; the live migration is parked for the owner's
// morning ratification). The MIGRATION half is proven separately, against a COPY of the real live
// store, because fresh fixtures are exactly where a migration bug is invisible (G-135).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { openHeartStore, closeHeartStore, HeartStoreError } = require('../heart-store');
const { migrate, userVersion, MIGRATION_SESSION_SPLIT, MIGRATIONS } = require('../migrations');

const OUT = path.join(__dirname, 'probe-session-turn-split.out');
const started = new Date();
const lines = [];
const checks = [];

function say(s) {
  lines.push(s);
  console.log(s);
}

function check(name, ok, detail) {
  checks.push({ name, ok: Boolean(ok) });
  say(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function tmpStore(tag) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `probe-746-${tag}-`));
  return path.join(dir, 'heart.db');
}

function openFresh(tag) {
  return openHeartStore({ dbPath: tmpStore(tag) });
}

// A turn to work with, created through the REAL spawn-recording path rather than by hand-inserting
// a row: hand-inserting would test this probe's SQL, and the property under test is that the
// PRODUCTION path opens a session.
function newTurn(store, { sessionMode = 'headless', parentExecId = null } = {}) {
  return store.recordExecutionStart({
    jobId: 'probe-job',
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'probe',
    sessionMode,
    firedTick: 1,
    firedAt: new Date(),
    parentExecId,
  });
}

let store;
try {
  // ───────────────────────────────────────────────────────────── CONTROL: the pre-split shape
  // Prove the OLD schema could not express what the checks below assert. Without this, "a session
  // is alive while its turn is done" is a sentence about two columns and says nothing about
  // whether the split was needed — the control is what makes the rest evidence.
  {
    const { DatabaseSync } = require('node:sqlite');
    const p = tmpStore('control');
    const db = new DatabaseSync(p);
    db.exec(`
      CREATE TABLE jobs_log (
        exec_id INTEGER PRIMARY KEY AUTOINCREMENT,
        status  TEXT NOT NULL DEFAULT 'launching'
                CHECK (status IN ('launching','running','done','blocked','failed','stalled','killed'))
      );
    `);
    db.prepare("INSERT INTO jobs_log (status) VALUES ('done')").run();
    let refused = false;
    try {
      // The pre-split store has ONE status column, so representing "the session is still alive"
      // means writing a session word into it. The legacy CHECK refuses it.
      db.prepare("UPDATE jobs_log SET status='alive' WHERE exec_id=1").run();
    } catch { refused = true; }
    const tables = db.prepare(
      "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
    ).all();
    db.close();
    check('CONTROL: the pre-split shape has NO sessions table', tables.length === 0);
    check('CONTROL: the pre-split shape CANNOT record a live session beside a done turn',
      refused, 'the flat enum refuses a session-level value — there was nowhere else to put it');
  }

  // ───────────────────────────────────────────────────────────── the two levels exist and are wired
  store = openFresh('split');
  const t1 = newTurn(store);
  check('a spawned turn OPENS a session (production path, not the probe)',
    Number.isInteger(t1.session_pk) && t1.session_pk > 0, `session_pk=${t1.session_pk}`);

  const s1 = store.getSession(t1.session_pk);
  check('the session starts ALIVE with its own status column',
    s1 && s1.status === 'alive', `sessions.status=${s1 && s1.status}`);
  check('turn status and session status are SEPARATE columns in separate tables',
    s1.status === 'alive' && t1.status === 'launching',
    `session=${s1.status} turn=${t1.status}`);

  // ───────────────────────────────────── THE DISCRIMINATING CHECK: a session survives its turn-end
  store.updateExecutionStatus(t1.exec_id, { status: 'running' });
  const ended = store.updateExecutionStatus(t1.exec_id, { status: 'done', endedAt: new Date() });
  const afterTurnEnd = store.getSession(t1.session_pk);
  check('THE SPLIT: a turn reports done and its SESSION STAYS ALIVE',
    ended.status === 'done' && afterTurnEnd.status === 'alive',
    `turn=${ended.status} session=${afterTurnEnd.status}`);

  // Structural, not incidental: the turn-end write has no way to end a session. This is the
  // property the design rests on — "a session survives its report" is true because no code path
  // exists that would end it, not because callers remember not to.
  const t2 = newTurn(store, { parentExecId: t1.exec_id });
  check('a NEXT TURN can start while the session is still alive (multi-turn session)',
    t2.parent_exec_id === t1.exec_id, `turn ${t2.exec_id} chains to ${t1.exec_id}`);

  // The same session must be able to hold both turns — the store's representation of "the process
  // stayed up". Today's spawn path opens a session per turn (1:1 degeneracy), so the second turn
  // is re-homed onto the first session the way the tmux path (7.30/7.32) will.
  store._prepare('UPDATE jobs_log SET session_pk = ? WHERE exec_id = ?').run(t1.session_pk, t2.exec_id);
  const turns = store.listTurnsOfSession(t1.session_pk);
  check('ONE session holds MORE THAN ONE turn — inexpressible before this task',
    turns.length === 2 && store.getSession(t1.session_pk).status === 'alive',
    `${turns.length} turns under a session still alive`);

  // The chain works within a session AND across sessions — one column, both jobs, which is what
  // the criteria ask for.
  const t3 = newTurn(store, { parentExecId: t2.exec_id });
  check('parent_exec_id chains ACROSS sessions too',
    t3.parent_exec_id === t2.exec_id && t3.session_pk !== t2.session_pk,
    `turn ${t3.exec_id} (session ${t3.session_pk}) chains to turn ${t2.exec_id} (session ${t1.session_pk})`);
  check('the chain thread is unchanged by the split',
    t3.thread === `exec-${t1.exec_id}`, `thread=${t3.thread}`);

  // ───────────────────────────────────────────────── no path infers one level from the other
  let sessionValueRefused = null;
  try {
    store.updateExecutionStatus(t1.exec_id, { status: 'alive' });
  } catch (e) { sessionValueRefused = e; }
  check('a SESSION status is REFUSED on a turn row, with a named error',
    sessionValueRefused instanceof HeartStoreError
      && /SESSION status/.test(sessionValueRefused.message),
    sessionValueRefused ? sessionValueRefused.message.slice(0, 80) : 'not refused');

  let turnValueRefused = null;
  try {
    store.closeSession(t1.session_pk, { status: 'done' });
  } catch (e) { turnValueRefused = e; }
  check('a TURN status is REFUSED on a session, with a named error',
    turnValueRefused instanceof HeartStoreError,
    turnValueRefused ? turnValueRefused.message.slice(0, 80) : 'not refused');

  // closeSession is the ONLY exit from alive, and it must actually work.
  const closed = store.closeSession(t1.session_pk, { status: 'closed', reason: 'probe' });
  check('closeSession() is the one exit from alive',
    closed.status === 'closed' && closed.closed_at && closed.close_reason === 'probe',
    `status=${closed.status}`);
  check('closing a session does NOT rewrite its turns',
    store.getExecution(t1.exec_id).status === 'done', 'turn kept its own outcome');

  // A re-close must not overwrite the first honest close — a crash sweep and a late exit
  // observation can both fire on one session, and the first one saw the truth.
  const reclosed = store.closeSession(t1.session_pk, { status: 'crashed', reason: 'second' });
  check('a second close does NOT rewrite the first',
    reclosed.status === 'closed' && reclosed.close_reason === 'probe',
    `still ${reclosed.status}/${reclosed.close_reason}`);

  // ─────────────────────────────────── the live-set readers answer from their own level
  const liveTurnRows = store.listExecutionsByStatus('launching')
    .concat(store.listExecutionsByStatus('running'));
  const liveSessionRows = store.listTurnsOfLiveSessions();
  check('the SESSION-level live set is computed from sessions.status',
    liveSessionRows.every((r) => store.getSession(r.session_pk).status === 'alive'),
    `${liveSessionRows.length} rows, every one under an alive session`);
  check('the two live sets are genuinely DIFFERENT questions',
    // t1 is a done turn under a CLOSED session; t2 is a launching turn under that same closed
    // session. So the turn-level set contains a row the session-level set does not — the exact
    // divergence the old single reader could never show.
    liveTurnRows.some((r) => r.exec_id === t2.exec_id)
      && !liveSessionRows.some((r) => r.exec_id === t2.exec_id),
    `turn-level=${liveTurnRows.length} session-level=${liveSessionRows.length}`);

  closeHeartStore();
  store = null;

  // ─────────────────────────────────────────── the completion path ends the session DELIBERATELY
  // Today's one-shot process really does exit at its report, so the completion path closes the
  // session explicitly. That is what keeps behaviour byte-identical (the degenerate case, R16) —
  // and it is an EXPLICIT close, not an inference: the turn-end write itself still cannot do it.
  {
    const s = openFresh('degenerate');
    const t = newTurn(s);
    s.updateExecutionStatus(t.exec_id, { status: 'running' });
    s.recordMessage({
      type: 'completion', sender: 'worker', thread: t.thread,
      corpus: 'done', status: 'done', createdAt: new Date(), execId: t.exec_id,
    });
    const sess = s.getSession(t.session_pk);
    const turn = s.getExecution(t.exec_id);
    check('DEGENERATE CASE: a one-shot completion closes both levels together',
      turn.status === 'done' && sess.status === 'closed',
      `turn=${turn.status} session=${sess.status}`);
    check('a one-shot session is a session with EXACTLY ONE turn (R16)',
      s.listTurnsOfSession(t.session_pk).length === 1);
    check('the live sets are EQUAL while sessions and turns are 1:1 — behaviour unchanged',
      s.listTurnsOfLiveSessions().length === 0
        && s.listExecutionsByStatus('running').length === 0,
      'both empty after the one-shot ended');
    closeHeartStore();
  }

  // ───────────────────────────────────────────────────────── the park is real, not a promise
  check('the split migration is NOT registered — landing it must not ARM it',
    !MIGRATIONS.some((m) => m.version === MIGRATION_SESSION_SPLIT.version),
    `MIGRATIONS holds versions [${MIGRATIONS.map((m) => m.version).join(',')}]; `
    + 'the live migration executes only when the owner ratifies, by appending it');

  // …and it must nonetheless WORK, or the park is hiding a broken migration. Proven by injection
  // on a store built in the PRE-SPLIT shape, so the migration has real work to do.
  {
    const { DatabaseSync } = require('node:sqlite');
    const p = tmpStore('migrate');
    const db = new DatabaseSync(p);
    db.exec(`
      CREATE TABLE jobs_log (
        exec_id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_exec_id INTEGER REFERENCES jobs_log(exec_id),
        session_mode TEXT NOT NULL DEFAULT 'headless',
        fired_at TEXT NOT NULL,
        ended_at TEXT,
        session_id TEXT,
        status TEXT NOT NULL DEFAULT 'launching'
      );
    `);
    for (const st of ['done', 'failed', 'killed', 'running', 'stalled', 'blocked', 'launching']) {
      db.prepare("INSERT INTO jobs_log (status, fired_at) VALUES (?, '2026-07-27T00:00:00Z')").run(st);
    }
    const before = db.prepare('SELECT count(*) n FROM jobs_log').get().n;
    const res = migrate(db, { fresh: false, migrations: [MIGRATIONS[0], MIGRATION_SESSION_SPLIT] });
    check('the parked migration APPLIES when injected', res.applied.includes(2)
      && userVersion(db) === 2, `applied=${JSON.stringify(res.applied)}`);
    const orphans = db.prepare('SELECT count(*) n FROM jobs_log WHERE session_pk IS NULL').get().n;
    check('the migration STRANDS NO ROW', orphans === 0 && before === 7, `${orphans} orphans`);
    const killed = db.prepare("SELECT j.status turn, s.status sess FROM jobs_log j "
      + 'JOIN sessions s ON s.session_pk=j.session_pk WHERE j.exec_id=3').get();
    check("the lossy case is mapped as designed: flat 'killed' -> session killed, turn failed",
      killed.sess === 'killed' && killed.turn === 'failed',
      `session=${killed.sess} turn=${killed.turn}`);
    const stalled = db.prepare("SELECT j.status turn, s.status sess FROM jobs_log j "
      + 'JOIN sessions s ON s.session_pk=j.session_pk WHERE j.exec_id=5').get();
    check("'stalled' stays a TURN state under an ALIVE session (owner ruling 2026-07-20)",
      stalled.sess === 'alive' && stalled.turn === 'stalled',
      `session=${stalled.sess} turn=${stalled.turn}`);
    MIGRATION_SESSION_SPLIT.up(db);
    const after2 = db.prepare('SELECT count(*) n FROM sessions').get().n;
    check('the migration is IDEMPOTENT — registering it later is a no-op on migrated stores',
      after2 === before, `${after2} sessions after a second run of ${before}`);
    db.close();
  }
} catch (err) {
  check(`UNCAUGHT: ${err && err.message ? err.message : String(err)}`, false);
} finally {
  if (store) { try { closeHeartStore(); } catch { /* already closed */ } }
}

const failed = checks.filter((c) => !c.ok).length;
say('');
say(`${checks.length} checks, ${failed} failure(s)`);
say(`started ${started.toISOString()} ended ${new Date().toISOString()}`);
// Completeness trailer (G-121): a truncated run reads greener than a complete one, so the run
// asserts its own end. A reader who sees no PROBE-COMPLETE has an INCOMPLETE run, whatever the
// PASS lines above say.
say('PROBE-COMPLETE');
fs.writeFileSync(OUT, `${lines.join('\n')}\n`, 'utf8');
process.exit(failed ? 1 : 0);
