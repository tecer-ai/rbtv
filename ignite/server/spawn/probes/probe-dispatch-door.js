'use strict';

// Task 7.75 — THE DISPATCH DOOR (design-760 §3, the owner rider of `r-headless-visibility`).
//
// The clause under test is the REFUSAL, not the happy path: "a goal-scoped headless dispatch that
// names no seat is REFUSED with a typed error naming the missing field; a seat-named dispatch
// produces the sessions.csv row AT DISPATCH; a sub-agent dispatch is NOT refused."
//
// So every leg here is written to DISCRIMINATE — each pair differs in exactly one property of the
// dispatch and must come out with DIFFERENT verdicts. A probe whose legs all pass a door that
// refuses everything (or nothing) proves nothing about the door, and D2/D3 exist precisely to
// deny that:
//
//   D1  goal-scoped, no seat   -> REFUSED  E_SEATLESS_GOAL_DISPATCH, and NOTHING was created
//   D2  goal-scoped, IS a seat -> ADMITTED, and the sessions.csv row is written AT DISPATCH
//   D3  NOT goal-scoped        -> REFUSED too (r-seats-only-architecture (3): the 7.75 sub-agent /
//                                 machine-lane exemption retired with the flat launch branch)
//
// The refusal legs are ABSENCE-PROVEN, not message-proven (the §4a evidence rule): the filesystem
// and the store are re-read after each refusal and asserted unchanged. A gate that throws loudly
// after already having mkdir'd a session dir satisfies an error check and fails the actual bar.

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const { capture, fixtureRoot } = require('./lib');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

// A goal tree with a LIVE run and one real, rostered seat — plus the two dispatch targets the door
// must tell apart from it: the RUN folder itself (goal-scoped, seatless) and the flat interim
// `.rbtv/sessions/` path (not goal-scoped at all).
//
// `workdir_root` is the WORKSPACE root here, not the goals dir, deliberately: it must admit both
// `.rbtv/goals/…` and `.rbtv/sessions/…` so that the containment gate (E_WORKDIR_ESCAPE) cannot be
// what refuses D1. If the older boundary answered first, this probe would be green while the 7.75
// door did not exist — the classic confounded check.
function fixture() {
  const root = fixtureRoot('p775-door-');
  const ws = path.join(root, 'ws');
  const goalsDir = path.join(ws, '.rbtv', 'goals');
  const goalDir = path.join(goalsDir, 'testgoal');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', 'mine');
  const seatlessDir = path.join(runDir, 'seats');
  const interimDir = path.join(ws, '.rbtv', 'sessions', 'subagent-1');
  for (const d of [seatDir, interimDir]) fs.mkdirSync(d, { recursive: true });
  fs.mkdirSync(path.join(ws, '.rbtv', 'mirror', 'x'), { recursive: true });  // envelope family 6 ro-binds {workspace}/.rbtv/mirror; a real workspace always has one

  fs.writeFileSync(path.join(goalsDir, 'goals.csv'), 'name,created,due,type,status\ntestgoal,2026-08-05,,one-shot,active\n');
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,mine\n');
  // The header task 7.37 settled — written BY COLUMN NAME by the writer under test, so a schema
  // this probe invented from the writer's side would prove nothing. This is the real one.
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: mine\nharness: bash\nmodel: door-probe\n---\n');

  const dataRoot = path.join(root, 'data');
  fs.mkdirSync(dataRoot, { recursive: true });

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(root, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'auto', kill_grace_seconds: 2 },
    default_workdir_root: ws,
    'launch-specs': {
      bash: {
      // A REAL process (`sleep`), not a dry run: the at-dispatch row carries the launched pid, and
      // a composition-only check could not see whether the row was written at all.
      'door-probe': {
        exec: { argv: ['bash', '-c', 'exec sleep 3600', '--model', 'door-probe'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        workdir_root: ws,
        caps: { memory_max: '64M', runtime_max: '1h' },
      },
      },
    },
  };
  const cfgPath = path.join(root, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const dbPath = path.join(root, '.rbtv', 'heart', 'heart.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const store = openHeartStore({ dbPath });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });
  return { root, ws, goalDir, runDir, seatDir, seatlessDir, interimDir, sessionsCsv: path.join(runDir, 'sessions.csv'), store, mgr, dataRoot };
}

let tick = 1;
function fire(f, workdir) {
  return f.store.recordExecutionStart({
    jobId: 'launch-agent', actionType: 'launch-agent', args: JSON.stringify({ workdir }),
    enqueuedBy: 'probe', sessionMode: 'headless', firedTick: tick++, firedAt: new Date(), profile: 'door-probe', workdir,
  });
}

function sessionRows(f) {
  const raw = fs.readFileSync(f.sessionsCsv, 'utf8').trim().split('\n');
  const header = raw[0].split(',');
  return raw.slice(1).filter(Boolean).map((line) => {
    const cells = line.split(',');
    return Object.fromEntries(header.map((h, i) => [h, cells[i]]));
  });
}

// The absence half — everything a launch would have left behind.
function world(f) {
  const ls = (p) => { try { return fs.readdirSync(p).length; } catch { return 0; } };
  return {
    csvRows: sessionRows(f).length,
    logs: ls(path.join(f.dataRoot, 'logs')),
    prompts: ls(path.join(f.dataRoot, 'prompts')),
    interimDirs: ls(path.join(f.ws, '.rbtv', 'sessions')),
  };
}

capture('probe-dispatch-door', async (lines) => {
  const f = fixture();
  const fails = [];
  const spawned = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  const dispatch = async (workdir) => {
    const row = fire(f, workdir);
    try {
      const fresh = await f.mgr.spawn(row.exec_id, 'headless', null, workdir, 'probe');
      spawned.push(row.exec_id);
      return { threw: false, execId: row.exec_id, row: fresh };
    } catch (err) {
      const after = f.store.getExecution(row.exec_id);
      return { threw: true, execId: row.exec_id, code: err.code, message: err.message, status: after && after.status };
    }
  };

  try {
    // ── D1 — GOAL-SCOPED, NAMES NO SEAT. Two shapes, because "not a seat folder" has more than
    // one way to be true: the run folder itself, and the `seats/` parent (one segment short of a
    // seat). Both are inside the goal tree; neither names a seat.
    for (const [label, dir] of [['<run>/', f.runDir], ['<run>/seats/', f.seatlessDir], ['<goal>/', f.goalDir]]) {
      const before = world(f);
      const r = await dispatch(dir);
      const after = world(f);
      const nothing = JSON.stringify(before) === JSON.stringify(after);
      const namesField = /MISSING FIELD: seat/.test(r.message || '');
      leg(`D1[${label}]`, 'REFUSED with a typed error NAMING the missing field, and nothing was created',
        r.threw && r.code === 'E_SEATLESS_GOAL_DISPATCH' && namesField && nothing && r.status !== 'running',
        `code=${r.code} names-missing-field=${namesField} store-status=${r.status} world-unchanged=${nothing} `
        + `(csv rows ${after.csvRows}, logs ${after.logs}, prompts ${after.prompts})`);
    }

    // ── D2 — GOAL-SCOPED AND NAMES A SEAT: admitted, and THE ROW IS WRITTEN AT DISPATCH.
    //
    // This is the leg that makes D1 mean something: same door, same goal tree, one property
    // changed (the workdir IS a seat folder), OPPOSITE verdict. Without it, a `spawn` that threw
    // unconditionally would read green above.
    //
    // "AT DISPATCH" is asserted as an IDENTITY, not as a coincidence: the row's `session-id` must
    // equal the `session_id` on this dispatch's OWN jobs_log row. That is the join key task 7.73
    // reads, so a row written by anything other than this dispatch — later, by hand, by a
    // reconciliation pass — cannot satisfy it.
    const beforeD2 = sessionRows(f).length;
    const d2 = await dispatch(f.seatDir);
    const rows = sessionRows(f);
    const added = rows.slice(beforeD2);
    const execRow = f.store.getExecution(d2.execId);
    const one = added.length === 1 ? added[0] : null;
    leg('D2', 'a seat-named goal-scoped dispatch is ADMITTED and writes its sessions.csv row AT DISPATCH',
      !d2.threw && added.length === 1 && one.seat === 'mine'
      && one['session-id'] === execRow.session_id && one['session-id'] !== ''
      // `ended` is EMPTY, not absent: this is the row's OPEN half. The trailing cell of a
      // 10-column line splits to '' — asserting `undefined` would be asserting a parse artifact.
      && one.workdir === f.seatDir && one.started !== '' && !one.ended,
      `refused=${d2.threw} rows-added=${added.length} seat=${one && one.seat} `
      + `row.session-id=${one && one['session-id']} jobs_log.session_id=${execRow && execRow.session_id} `
      + `identical=${Boolean(one) && one['session-id'] === execRow.session_id} pid=${one && one.pid}`);

    // ── D3 — THE RETIRED FLAT PATH IS REFUSED (r-seats-only-architecture (3)/(4)). The 7.75
    // door carried an exemption here: a dispatch outside `.rbtv/goals/` (the sub-agent lane's
    // `<ws>/.rbtv/sessions/<exec-id>/` shape, machine-lane jobs) was ADMITTED. The lane retired
    // with the daemon's delegation broker and the flat launch branch retired with it — a dispatch
    // with no home is a refusal, not a flat dir. Absence-proven like D1: nothing created.
    const beforeD3 = world(f);
    const d3 = await dispatch(f.interimDir);
    const afterD3 = world(f);
    const d3nothing = JSON.stringify(beforeD3) === JSON.stringify(afterD3);
    leg('D3', 'a dispatch into the RETIRED flat .rbtv/sessions/ path is REFUSED (REFUSING SEATLESS DISPATCH), and nothing was created',
      d3.threw && d3.code === 'E_SEATLESS_GOAL_DISPATCH' && /REFUSING SEATLESS DISPATCH/.test(d3.message || '')
      && d3nothing && d3.status !== 'running',
      `refused=${d3.threw} code=${d3.code || 'none'} store-status=${d3.status} world-unchanged=${d3nothing}`);

    // ── D4 — a seat-SHAPED path outside any `.rbtv/goals/` tree is NOT a seat folder and is
    // REFUSED too. Under 7.75 this leg proved the goal tree was what armed the gate; under
    // r-seats-only-architecture the gate is armed everywhere — parseSeatPath requires the full
    // canonical shape (`.rbtv/goals/<goal>/seats/<seat>`), so a decoy `seats/` segment outside the
    // goal tree cannot buy admission. Inside the workspace, deliberately, so the containment gate
    // is not what answers (the confounding D1's fixture note warns about). ⚠ The decoy keeps a
    // `.rbtv/goals`-SHAPED tail depth so what refuses it is the missing `.rbtv`/`goals` anchor and
    // not merely a path too short to parse.
    const decoy = path.join(f.ws, 'decoy', 'goals', 'testgoal', 'seats', 'mine');
    fs.mkdirSync(decoy, { recursive: true });
    const beforeD4 = world(f);
    const d4 = await dispatch(decoy);
    const afterD4 = world(f);
    const d4nothing = JSON.stringify(beforeD4) === JSON.stringify(afterD4);
    leg('D4', 'a seat-SHAPED path outside .rbtv/goals/ is not a seat folder — REFUSED, and nothing was created',
      d4.threw && d4.code === 'E_SEATLESS_GOAL_DISPATCH' && d4nothing && d4.status !== 'running',
      `refused=${d4.threw} code=${d4.code || 'none'} store-status=${d4.status} world-unchanged=${d4nothing}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`dispatch door probes failed: ${fails.join(', ')}`);
  } finally {
    for (const execId of spawned) {
      try { await f.mgr.kill(execId); } catch {}
    }
    try { closeHeartStore(); } catch {}
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
