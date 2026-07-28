'use strict';

// probe-g225-atomic-turn-session — G-225. Does a turn's end and its session's close land TOGETHER
// OR NOT AT ALL?
//
// THE DEFECT: `ticker.js`'s `endTurnAndSession` and `spawn.js`'s kill path each wrote the TURN and
// closed the SESSION as TWO SEPARATE STATEMENTS with no transaction around them. A failure or a
// daemon death between them leaves a TERMINAL TURN UNDER AN `alive` SESSION — precisely the state
// `G-222`'s crash sweep used to destroy. The five unclosed writers (`spawn.js:786/:799/:808`,
// `pty-host.js:289/:327`) only ever write `failed`, which is the NOISE direction; THIS window can
// leave a `done`, which is the direction that destroys a real outcome.
//
// ⚠⚠ WHAT MAKES THIS PROBE EVIDENCE RATHER THAN CEREMONY — read before trusting any green below.
//
// 1 · THE WINDOW OPENS ONLY WHEN THE CLOSE FAILS. A green run under normal conditions is not
//     evidence the branch fired: on the happy path the two-statement shape and the atomic one are
//     INDISTINGUISHABLE. So every arm here runs with the session close FORCED TO FAIL, and the
//     forced failure is itself asserted (`the raiser really fired`) — an arm whose injected fault
//     silently did not fire would grade the two shapes identically and pass either way.
//
// 2 · THE POSITIVE CONTROL IS ARM 0, AND IT IS NOT OPTIONAL. It reproduces the OLD two-statement
//     shape inline, under the SAME forced failure, and asserts it PRODUCES the exposed state. If
//     arm 0 ever stops producing it, the fixture can no longer create the hazard and arm A's green
//     means nothing — "the fix works" and "the fixture cannot make the bug" print the same thing
//     (`bars.md` 11, second half). Arm 0 is expected to pass BEFORE and AFTER the fix: it is a
//     control on the FIXTURE, never on the cure.
//
// 3 · IT DISCRIMINATES THE CORRECT FIX FROM A PLAUSIBLE WRONG ONE (the run's control bound). Two
//     wrong "fixes" would both remove the exposed state and neither is correct:
//       · SWAP THE ORDER (close the session first, then write the turn) -> leaves
//         `turn=running, session=closed`. ⚠⚠ ARM A CANNOT SEE THIS AND THIS HEADER CLAIMED IT
//         COULD. Measured: the swap mutant passed arm A with 0 failures. Arm A injects its fault
//         AT `closeSession()`, so under the swapped order the close throws FIRST, the turn is never
//         written, and both of arm A's assertions hold — THE FAULT'S OWN PLACEMENT MAKES THE
//         ORDERING INVISIBLE. A fault on the SECOND statement cannot discriminate which statement
//         is second. That is what ARM A2 is for: it injects the fault at the TURN WRITE instead and
//         asserts the session was not already closed. Kept as a warning rather than quietly
//         corrected, because the false claim was written INTO the instrument and would have been
//         read as measured.
//       · LET `updateExecutionStatus()` CLOSE THE SESSION ITSELF -> removes the window by
//         destroying the 7.46 structural guarantee that the turn-end write cannot end a session.
//         Arm C asserts that guarantee still holds, so this fails.
//     A probe red only on the exposed state would certify both.
//
// 4 · ARM P HOLDS THE POPULATION CLOSED. The fix is not only the store method — it is that NO
//     production caller pairs the two writes by hand any more. Arm P enumerates every production
//     `closeSession()` call site outside the store and requires it to be the ONE sanctioned site
//     (the `G-222` crash-sweep close, which writes NO turn and is correct). A new hand-rolled
//     pairing turns this red. Without it, a revert of either caller is invisible.
//
// ⚠ SEPARABILITY (`G-232`'s form, leader-bound): this probe and the fix are separate commits. A
// revert of the fix leaves this probe in place and RED — it must never be the case that reverting
// the product also deletes the only thing that can see the defect.
//
// ⚠⚠ WHAT THIS PROBE DOES *NOT* ESTABLISH, and it must never be reported as more: the fix is
// PROVEN IN ISOLATION ON THIS COMMIT, NOT EXERCISED IN PRODUCTION. Nothing short of a real process
// dying under a live session with a reported turn upgrades that claim.
//
// The live store is never opened; every fixture is a throwaway file in tmpdir.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { openHeartStore, closeHeartStore } = require('../heart-store');

const OUT = path.join(__dirname, 'probe-g225-atomic-turn-session.out');
const SERVER_ROOT = path.resolve(__dirname, '..', '..');
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

function openFresh(tag) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `probe-g225-${tag}-`));
  return openHeartStore({ dbPath: path.join(dir, 'heart.db') });
}

// Created through the REAL spawn-recording path: hand-inserting a row would test this probe's SQL,
// and the property under test is what the PRODUCTION path leaves behind.
function newTurn(store) {
  return store.recordExecutionStart({
    jobId: 'probe-job',
    actionType: 'launch-agent',
    args: '{}',
    enqueuedBy: 'probe',
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    parentExecId: null,
  });
}

// The injected fault. It stands in for every way the gap between the two writes can be lost — a
// daemon death, a locked database, a throw. Returns a restore function AND a fired() predicate,
// because an injected fault that silently did not fire is the difference between a measurement and
// a coincidence.
//
// ⚠⚠ WHICH METHOD THE FAULT IS BOUND TO IS NOT A DETAIL — IT DECIDES WHAT THE ARM CAN SEE, and
// getting this wrong cost this probe its headline claim once already. A fault on `closeSession`
// probes the window AFTER the turn write; a fault on `updateExecutionStatus` probes it BEFORE. Only
// the second can tell you which write happened first, because a fault on the second statement is
// reached identically whichever statement is second.
function breakMethod(store, name) {
  const real = store[name];
  let fired = 0;
  store[name] = function broken() {
    fired += 1;
    throw new Error(`injected: ${name} failed`);
  };
  return {
    restore() { store[name] = real; },
    fired: () => fired,
  };
}

const breakCloseSession = (store) => breakMethod(store, 'closeSession');
const breakTurnWrite = (store) => breakMethod(store, 'updateExecutionStatus');

let store = null;
try {
  // ══════════════════════════════════════════════════════════════════ ARM 0 — POSITIVE CONTROL
  // The OLD two-statement shape, reproduced inline, under the injected fault. It MUST produce the
  // exposed state, or nothing below is evidence.
  {
    const s = openFresh('arm0');
    const t = newTurn(s);
    s.updateExecutionStatus(t.exec_id, { status: 'running' });

    const fault = breakCloseSession(s);
    let threw = false;
    try {
      // exactly the shape that was at ticker.js:246/:248 and spawn.js:745/:747
      const exec = s.updateExecutionStatus(t.exec_id, { status: 'done', endedAt: new Date() });
      if (exec && exec.session_pk) {
        s.closeSession(exec.session_pk, { status: 'closed', reason: 'arm0', closedAt: new Date() });
      }
    } catch { threw = true; }
    fault.restore();

    const turn = s.getExecution(t.exec_id);
    const sess = s.getSession(t.session_pk);
    check('ARM 0 · the injected fault really fired (a fault that did not fire grades both shapes the same)',
      fault.fired() === 1 && threw, `close attempts=${fault.fired()} threw=${threw}`);
    check('ARM 0 · POSITIVE CONTROL: the two-statement shape leaves the EXPOSED STATE — a `done` turn under an `alive` session',
      turn.status === 'done' && sess.status === 'alive',
      `turn=${turn.status} session=${sess.status}`);
    closeHeartStore();
  }

  // ══════════════════════════════════════════════════════════════════════ ARM A — THE FIX, FAULT
  // The same fault against the atomic method: BOTH writes must be undone.
  {
    const s = openFresh('armA');
    const t = newTurn(s);
    s.updateExecutionStatus(t.exec_id, { status: 'running' });

    const hasMethod = typeof s.endTurnAndCloseSession === 'function';
    check('ARM A · the store exposes `endTurnAndCloseSession()` — one call owning both writes',
      hasMethod, hasMethod ? 'present' : 'ABSENT: the fix is not in this tree (or was reverted)');

    if (hasMethod) {
      const fault = breakCloseSession(s);
      let threw = false;
      try {
        s.endTurnAndCloseSession(t.exec_id, {
          turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date(), reason: 'armA',
        });
      } catch { threw = true; }
      fault.restore();

      const turn = s.getExecution(t.exec_id);
      const sess = s.getSession(t.session_pk);
      check('ARM A · the injected fault really fired',
        fault.fired() === 1 && threw, `close attempts=${fault.fired()} threw=${threw}`);
      // The two halves of the claim are asserted SEPARATELY and both are load-bearing:
      //   turn rolled back  -> the destructive `done` never reaches disk
      //   session ALIVE     -> rules out the swap-the-order "fix", which removes the exposed state
      //                        by producing a DIFFERENT broken state
      check('ARM A · the turn write ROLLED BACK — no terminal turn reached disk',
        turn.status === 'running', `turn=${turn.status} (expected the pre-call 'running')`);
      check('ARM A · the session is still ALIVE — rules out a fix that merely swapped the order',
        sess.status === 'alive', `session=${sess.status}`);
      check('ARM A · the failure is ANNOUNCED, not swallowed — the caller learns the turn did not end',
        threw, 'the error propagated');
    } else {
      check('ARM A · the turn write ROLLED BACK — no terminal turn reached disk', false, 'skipped: method absent');
      check('ARM A · the session is still ALIVE — rules out a fix that merely swapped the order', false, 'skipped: method absent');
    }
    closeHeartStore();
  }

  // ═══════════════════════════════════════════ ARM A2 — THE FAULT ON THE *OTHER* WRITE (ORDERING)
  // Arm A is blind to a fix that merely swapped the two statements, because its fault sits on the
  // one that would then run FIRST. Here the TURN WRITE is the thing that fails, and the question is
  // whether the session was already closed by the time it did. Under the atomic method nothing was
  // committed, so the session is untouched. Under close-first-then-write it is `closed`, with a
  // `running` turn under it — the same defect wearing the other face.
  //
  // ⚠ This arm ALSO covers a direction arm A does not: a session closed under a turn that never
  // ended. That state is not `G-225`'s original exposed state, and it is just as wrong.
  {
    const s = openFresh('armA2');
    if (typeof s.endTurnAndCloseSession === 'function') {
      const t = newTurn(s);
      s.updateExecutionStatus(t.exec_id, { status: 'running' });

      const fault = breakTurnWrite(s);
      let threw = false;
      try {
        s.endTurnAndCloseSession(t.exec_id, {
          turnStatus: 'done', sessionStatus: 'closed', endedAt: new Date(), reason: 'armA2',
        });
      } catch { threw = true; }
      fault.restore();

      const turn = s.getExecution(t.exec_id);
      const sess = s.getSession(t.session_pk);
      check('ARM A2 · the injected fault really fired (bound to the TURN WRITE, not the close)',
        fault.fired() === 1 && threw, `turn-write attempts=${fault.fired()} threw=${threw}`);
      check('ARM A2 · a failed turn write leaves the session ALIVE — the close did not run first',
        sess.status === 'alive', `session=${sess.status} (a 'closed' here means the session was closed before the turn ended)`);
      check('ARM A2 · and the turn is untouched',
        turn.status === 'running', `turn=${turn.status}`);
    } else {
      check('ARM A2 · a failed turn write leaves the session ALIVE — the close did not run first', false, 'skipped: method absent');
    }
    closeHeartStore();
  }

  // ═════════════════════════════════════════════════════════════════════ ARM B — THE HAPPY PATH
  // A fix that made the failure path safe by breaking the normal one is not a fix.
  {
    const s = openFresh('armB');
    if (typeof s.endTurnAndCloseSession === 'function') {
      const t = newTurn(s);
      s.updateExecutionStatus(t.exec_id, { status: 'running' });
      const endedAt = new Date();
      s.endTurnAndCloseSession(t.exec_id, {
        turnStatus: 'done', sessionStatus: 'closed', endedAt, reason: 'armB normal',
      });
      const turn = s.getExecution(t.exec_id);
      const sess = s.getSession(t.session_pk);
      check('ARM B · the normal path still ends BOTH levels',
        turn.status === 'done' && sess.status === 'closed',
        `turn=${turn.status} session=${sess.status}`);
      check('ARM B · the caller\'s session status and reason are recorded VERBATIM — nothing is inferred',
        sess.close_reason === 'armB normal', `close_reason=${sess.close_reason}`);

      // The kill path's mapping (spawn.js) — a different session status through the same method.
      const t2 = newTurn(s);
      s.updateExecutionStatus(t2.exec_id, { status: 'running' });
      s.endTurnAndCloseSession(t2.exec_id, {
        turnStatus: 'killed', sessionStatus: 'killed', endedAt: new Date(), reason: 'armB kill',
      });
      check('ARM B · the KILL path maps through the same call — turn `killed`, session `killed`',
        s.getExecution(t2.exec_id).status === 'killed' && s.getSession(t2.session_pk).status === 'killed',
        `turn=${s.getExecution(t2.exec_id).status} session=${s.getSession(t2.session_pk).status}`);
    } else {
      check('ARM B · the normal path still ends BOTH levels', false, 'skipped: method absent');
    }
    closeHeartStore();
  }

  // ══════════════════════════════════════════════════ ARM C — THE CURE MUST NOT WEAKEN THE SPLIT
  // G-225's own filing names this: the 7.46 guarantee (`updateExecutionStatus()` structurally
  // cannot end a session) is WHY every caller was forced into the two-statement shape. The obvious
  // "fix" — let the turn-end write close the session — removes the window by removing the
  // guarantee, and a session could then never outlive its turn again.
  {
    const s = openFresh('armC');
    const t = newTurn(s);
    s.updateExecutionStatus(t.exec_id, { status: 'running' });
    s.updateExecutionStatus(t.exec_id, { status: 'done', endedAt: new Date() });
    const sess = s.getSession(t.session_pk);
    check('ARM C · the 7.46 guarantee SURVIVES the cure: a bare turn-end write still leaves the session ALIVE',
      sess.status === 'alive', `session=${sess.status} after a bare 'done' turn write`);
    closeHeartStore();
  }

  // ════════════════════════════════════════════════════════ ARM P — THE POPULATION STAYS CLOSED
  // Enumerated, not remembered. The ONE sanctioned production close outside the store is the
  // `G-222` crash-sweep site, which closes a session and writes NO turn ("writes only what it
  // actually observed"). Every other production pairing is the defect returning.
  {
    const files = [];
    (function walk(dir) {
      for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
        if (e.name === 'node_modules' || e.name === 'probes') continue;
        const p = path.join(dir, e.name);
        if (e.isDirectory()) walk(p);
        else if (e.name.endsWith('.js') && p !== path.join(SERVER_ROOT, 'heart', 'heart-store.js')) files.push(p);
      }
    }(SERVER_ROOT));

    const sites = [];
    for (const f of files) {
      const src = fs.readFileSync(f, 'utf8').split('\n');
      src.forEach((line, i) => {
        if (/\.closeSession\s*\(/.test(line)) sites.push(`${path.relative(SERVER_ROOT, f)}:${i + 1}`);
      });
    }

    // The enumerator's own control: it must be able to SEE a site at all. An enumerator that found
    // nothing anywhere would report a closed population by being blind (`bars.md` 11).
    check('ARM P · the enumerator can see a call site at all (its own positive control)',
      sites.length >= 1, `${sites.length} production closeSession() site(s) found across ${files.length} files`);
    check('ARM P · exactly ONE production caller closes a session outside the store, and it is the G-222 crash-sweep site',
      sites.length === 1 && sites[0].startsWith('ticker/ticker.js:'),
      sites.length ? sites.join(' ') : 'none');
  }
} catch (err) {
  check(`UNCAUGHT: ${err && err.message ? err.message : String(err)}`, false);
} finally {
  try { closeHeartStore(); } catch { /* already closed */ }
  store = null;
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
