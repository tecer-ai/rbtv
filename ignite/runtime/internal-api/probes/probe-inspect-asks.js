'use strict';

// probe-inspect-asks — THE READ HALF OF THE OWNER-ASK RECORD: `inspect asks`.
//
// WHAT THIS PROBE IS FOR. `spec-owner-io` §5's system digest is SYSTEM-WIDE, and the process that
// renders it — the chat bridge — is walled off from `heart.db` (`probe-chat-boundary.js`). Before
// this target the bridge had a WRITE path to the ask record (the thirteenth intent) and no read
// path at all, so the digest's `readOpenAsks` port had nothing legal to wire to and rendered an
// empty set forever. This probe measures the daemon half of that wiring.
//
// The load-bearing legs:
//   · the listing crosses GOALS (a per-goal answer cannot serve a system-wide digest);
//   · a NEVER-POSTED ask is absent (§2.1: an ask the owner was never told about is not a wait);
//   · a REAPED ask is absent (the digest must stop carrying an answered question);
//   · the row shape is the digest's own documented port, key by key;
//   · the three copies of the target set (gateway, core, CLI) still agree — the drift
//     `probe-inspect-executions` guards, re-asserted here because this change adds a member.
//
// ⚑ SECTION G — THE SECOND RECORD. `spec-recovery` §5's exit at N opens ONE signature-grouped ask
// per failure signature, and that ask is a FILE under `<workspace>/.rbtv/runtime/ignite/asks/`,
// written by `supervisor/exhaustion.js#recordGroupedAsk` — a different record from the `open_asks`
// table sections A-F measure. Nothing carried it to the owner: two lanes disarmed on 2026-08-28
// and the digest, whose only port is this target, rendered neither. G measures the merge.
//
// In-process parse + dispatch over a real (scratch) store. No daemon, no gateway socket, no Slack.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-inspect-asks.out');
fs.writeFileSync(outPath, '');

const { createInternalApi, ENVELOPE_VERSION, INSPECT_TARGETS: CORE_TARGETS } = require('../dispatch');
const { parseRequest, INSPECT_TARGETS: GW_TARGETS } = require('../../gateway/parse');
const { TARGETS: CLI_TARGETS, HELP: CLI_HELP } = require('../../../ignite-cli/commands/inspect');
const { openEndingStore, bind, openEndingStoreFor } = require('../../../state-store');
const askRecord = require('../../../state-store/heart/ask-record');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

const GOAL_A = 'meet-transcript-summarizer';
const GOAL_B = 'audio-component';

function seedGoal(root, goal) {
  const dir = path.join(root, '.rbtv', 'goals', goal);
  fs.mkdirSync(path.join(dir, 'coordination', 'asks'), { recursive: true });
  return dir;
}

async function main() {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('evidence-class: FIXTURE in-process parse+dispatch over a scratch ending store; no gateway socket, no Slack, no daemon');

  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'inspect-asks-probe-'));
  seedGoal(root, GOAL_A);
  seedGoal(root, GOAL_B);

  const db = openEndingStore(path.join(root, '.rbtv', 'runtime', 'ignite', 'heart.db'));
  const heartStore = { db };
  const store = bind(db);

  // Two goals, three asks, written through the DAEMON'S OWN writer so the rows and their on-disk
  // copies are exactly what the thirteenth intent produces.
  const openA = askRecord.openAsk({
    workspaceRoot: root, goal: GOAL_A, seat: 'goal-master', thread: '1724500001.000100',
    corpus: 'Should the summarizer keep the 90-minute cap?\n\n(second line, deliberately not the one-liner)',
  });
  const openB = askRecord.openAsk({
    workspaceRoot: root, goal: GOAL_B, seat: 'audio-smith', thread: '1724500002.000200',
    corpus: 'Which mic profile is the reference?',
  });
  const reaped = askRecord.openAsk({
    workspaceRoot: root, goal: GOAL_A, seat: 'verify-seat', thread: '1724500003.000300',
    corpus: 'Is this verdict good enough to close?',
  });
  check('SETUP: three asks were recorded through the daemon writer',
    openA.recorded && openB.recorded && reaped.recorded,
    `A=${openA.recorded} B=${openB.recorded} reaped=${reaped.recorded}`);

  const secret = crypto.randomBytes(32).toString('hex');
  const api = createInternalApi({ heartStore, spawnManager: {}, secret, workspaceRoot: root });
  const BRIDGE = { id: 'probe-bridge', kind: 'bridge' };

  async function inspect(payload, sender = BRIDGE) {
    let parsed;
    try {
      parsed = parseRequest({ intent: 'inspect', payload });
    } catch (err) {
      return { gatewayRefused: true, body: { ok: false, error: { code: err.code, message: err.message } } };
    }
    const res = await api.dispatch({
      v: ENVELOPE_VERSION,
      id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      auth: secret,
      sender,
      intent: 'inspect',
      payload: parsed,
    });
    return { gatewayRefused: false, body: res };
  }

  // ── A. THE TARGET EXISTS AT ALL THREE DOORS ─────────────────────────────────────────────────
  check('A1: the gateway allowlist admits `asks`', GW_TARGETS.has('asks'));
  check('A2: the server core admits `asks`', CORE_TARGETS.has('asks'));
  check('A3: the CLI surface admits `asks`', CLI_TARGETS.has('asks'));
  // The FOURTH copy: the usage lines an operator reads. A target in every Set and absent from the
  // help is a surface nobody can discover — `probe-inspect-executions.js` guards the same four,
  // and it is re-asserted here because this change adds a member to all of them.
  const helpTargets = new Set();
  for (const line of CLI_HELP.split('\n')) {
    const m = /^ignite inspect ([a-z][a-z0-9-]*)/.exec(line);
    if (m) helpTargets.add(m[1]);
  }
  check('A3b: the CLI HELP names `asks` as a usage line — a target nobody can discover is not shipped',
    helpTargets.has('asks'), `help=${[...helpTargets].sort().join(',')}`);

  const gw = [...GW_TARGETS].sort().join(',');
  const core = [...CORE_TARGETS].sort().join(',');
  const cli = [...CLI_TARGETS].sort().join(',');
  check('A4: the three copies of the target set are IDENTICAL — a member added to one and not the others is the drift this set has three homes for',
    gw === core && core === cli, `gw=${gw} core=${core} cli=${cli}`);

  // ── B. THE LISTING CROSSES GOALS ────────────────────────────────────────────────────────────
  let r = await inspect({ target: 'asks' });
  const rows = (r.body.result && r.body.result.rows) || [];
  check('B1: `inspect asks` answers ok', r.body.ok === true, JSON.stringify(r.body.error || {}));
  const goals = [...new Set(rows.map((x) => x.goal))].sort();
  check('B2: the listing spans EVERY goal — a per-goal answer cannot serve a SYSTEM-wide digest [§5]',
    goals.length === 2 && goals[0] === GOAL_B && goals[1] === GOAL_A,
    `goals=${goals.join('|')} rows=${rows.length}`);

  // ── C. THE ROW SHAPE IS THE DIGEST'S DOCUMENTED PORT ────────────────────────────────────────
  const rowA = rows.find((x) => x.id === '1724500001.000100');
  check('C1: the ask id is the SLACK THREAD [T5-R7]', Boolean(rowA), `ids=${rows.map((x) => x.id).join(',')}`);
  check('C2: every key the digest renders is present — id, seat, one_liner, opened_at, evidence_pointer',
    Boolean(rowA) && ['id', 'seat', 'one_liner', 'opened_at', 'evidence_pointer'].every((k) => rowA[k] !== undefined),
    JSON.stringify(rowA || {}));
  check('C3: the one-liner is the FIRST line of the ask copy, never the whole body — the digest is a phone glance',
    Boolean(rowA) && rowA.one_liner === 'Should the summarizer keep the 90-minute cap?',
    rowA && JSON.stringify(rowA.one_liner));
  check('C4: `opened_at` is when the ask reached the OWNER (`posted_at`), which is what §5 renders an age from',
    Boolean(rowA) && typeof rowA.opened_at === 'string' && rowA.opened_at.length > 0,
    rowA && rowA.opened_at);
  check('C5: `evidence_pointer` names a file that EXISTS — the Links section must open something',
    Boolean(rowA) && fs.existsSync(rowA.evidence_pointer), rowA && rowA.evidence_pointer);

  // ── D. WHAT MUST NOT BE IN IT ───────────────────────────────────────────────────────────────
  //
  // A reaped ask, and an ask that was never posted. Both are rows in the table; neither is a wait.
  store.reapAndRelaunch({ ask_id: '1724500003.000300', authorized_reply_at: '2026-08-25 09:30' });
  store.insertAsk({
    ask_id: '1724500004.000400', goal: GOAL_B, seat: 'audio-smith', label: 'work-content',
    evidence_pointer: path.join(root, 'never-posted.txt'),
  });
  r = await inspect({ target: 'asks' });
  const after = (r.body.result && r.body.result.rows) || [];
  const ids = after.map((x) => x.id);
  check('D1: a REAPED ask is gone from the listing — the digest must stop carrying a question the owner answered',
    !ids.includes('1724500003.000300'), `ids=${ids.join(',')}`);
  check('D2: an ask that was never POSTED is absent [§2.1] — an ask the owner was never told about is a wait nobody can end',
    !ids.includes('1724500004.000400'), `ids=${ids.join(',')}`);
  check('D3: the two live asks remain', ids.includes('1724500001.000100') && ids.includes('1724500002.000200'), `ids=${ids.join(',')}`);

  // ── E. IT IS A FIXED VIEW, AND THE SHAPE IS REFUSED AT THE DOOR ─────────────────────────────
  r = await inspect({ target: 'asks', id: 12 });
  check('E1: `inspect asks` takes no id — refused at the GATEWAY, never silently ignored',
    r.gatewayRefused === true && /id/.test(r.body.error.message), r.body.error && r.body.error.message);
  r = await inspect({ target: 'asks', status: 'failed' });
  check('E2: `inspect asks` takes no status — refused at the gateway',
    r.gatewayRefused === true, r.body.error && r.body.error.message);
  r = await inspect({ target: 'asks', goal: GOAL_A });
  check('E3: an unknown payload key is refused — the digest asks for the WHOLE waiting set or it is not that digest',
    r.gatewayRefused === true && /goal/.test(r.body.error.message), r.body.error && r.body.error.message);

  // ── F. AN UNREADABLE ASK COPY DOES NOT LOSE THE ROW ─────────────────────────────────────────
  //
  // The words live on disk and the STATE lives in the store, so a deleted copy costs the sentence,
  // never the fact that somebody is waiting.
  fs.rmSync(rowA.evidence_pointer, { force: true });
  r = await inspect({ target: 'asks' });
  const rowAgain = ((r.body.result && r.body.result.rows) || []).find((x) => x.id === '1724500001.000100');
  check('F1: the row survives a deleted ask copy, with no words rather than invented ones',
    Boolean(rowAgain) && rowAgain.one_liner === null, JSON.stringify(rowAgain || {}));

  // ── G. THE RECOVERY EXIT'S SIGNATURE-GROUPED ASK IS IN THE SAME LISTING ─────────────────────
  //
  // Written through `exhaustion.js`'s OWN writer, never hand-rolled JSON: a fixture that invents
  // the record shape proves the reader agrees with the fixture, not with the producer.
  const exhaustion = require('../../../supervisor/exhaustion');
  const grouped = exhaustion.recordGroupedAsk({
    store, workspaceRoot: root, goal: GOAL_B, seat: 'audio-smith',
    driver: 'reconcile-respawn', reasonClass: 'nonterm',
    refusalText: 'nonterm reached the attempt bound on this lane; the lane is stamped disarmed\nsecond line, deliberately not the one-liner',
    attempts: 3, at: '2026-08-20T04:00:00Z',
  });
  // A SECOND lane on the SAME signature — one ask, two lanes. The listing must still be ONE row,
  // because rendering a grouped ask once per lane is the per-lane ask the grouping rule forbids.
  exhaustion.recordGroupedAsk({
    store, workspaceRoot: root, goal: GOAL_A, seat: 'goal-master',
    driver: 'reconcile-respawn', reasonClass: 'nonterm',
    refusalText: 'nonterm reached the attempt bound on this lane; the lane is stamped disarmed',
    attempts: 3, at: '2026-08-20T05:00:00Z',
  });
  r = await inspect({ target: 'asks' });
  const merged = (r.body.result && r.body.result.rows) || [];
  const gRows = merged.filter((x) => x.id === grouped.ask_id);
  const gRow = gRows[0];
  check('G1: the signature-grouped ask record is IN the listing — spec-recovery §5\'s exit at N is owner-VISIBLE or it is not that exit',
    Boolean(gRow), `ids=${merged.map((x) => x.id).join(',')}`);
  // ONE ROW PER LANE [owner ruling 2026-08-31, `d-digest-ui` 3a]: a two-lane ask is two rows naming
  // two goals — collapsing them into one row hid every goal but the first (the defect this fix
  // closes). Both rows share the ONE record's `ask_id`; there is only one record on disk and no
  // per-lane answering path exists yet (`digest-recovery-thread` is held pending ask 14) — the
  // `goal` field is what tells the rows apart.
  check('G2: TWO rows for a TWO-lane ask, naming BOTH goals — "one ask per signature" grouped the FILE, never the render',
    gRows.length === 2 && gRows.some((x) => x.goal === GOAL_B) && gRows.some((x) => x.goal === GOAL_A),
    `rows=${gRows.map((x) => `${x.goal}:${x.seat}`).join(' | ')}`);
  check('G3: the row shape is the heart-store row\'s, key for key — the digest reads ONE list and cannot tell which record a row came from',
    Boolean(gRow) && ['id', 'goal', 'seat', 'label', 'one_liner', 'opened_at', 'evidence_pointer'].every((k) => gRow[k] !== undefined),
    JSON.stringify(gRow || {}));
  check('G4: each row\'s one-liner is THAT LANE\'S own first line — never a sentence assembled from the goal and seat names, never another lane\'s words',
    gRows.find((x) => x.goal === GOAL_B)?.one_liner === 'nonterm reached the attempt bound on this lane; the lane is stamped disarmed'
      && gRows.find((x) => x.goal === GOAL_A)?.one_liner === 'nonterm reached the attempt bound on this lane; the lane is stamped disarmed',
    JSON.stringify(gRows.map((x) => [x.goal, x.one_liner])));
  check('G5: `evidence_pointer` is the record file for EVERY lane row, and it EXISTS',
    gRows.length > 0 && gRows.every((x) => x.evidence_pointer === grouped.file) && fs.existsSync(grouped.file),
    gRow && gRow.evidence_pointer);
  check('G6: the thread-recorded owner asks are STILL there beside it — this is a merge, not a replacement',
    merged.some((x) => x.id === '1724500001.000100') && merged.some((x) => x.id === '1724500002.000200'),
    `ids=${merged.map((x) => x.id).join(',')}`);
  check('G7: OLDEST FIRST across BOTH records — §5 renders an age, and a listing sorted per-record would interleave two clocks',
    merged.map((x) => String(x.opened_at || '')).every((v, i, a) => i === 0 || a[i - 1] <= v),
    merged.map((x) => `${x.id}@${x.opened_at}`).join(' | '));

  // G-RED: the same listing with the directory read gone. Kept in-probe rather than as an external
  // mutation because the green above is indistinguishable from "there happened to be no file".
  const asksHome = exhaustion.asksDir(root);
  const parked = `${asksHome}-parked`;
  fs.renameSync(asksHome, parked);
  r = await inspect({ target: 'asks' });
  const withoutDir = (r.body.result && r.body.result.rows) || [];
  check('G8 RED CONTROL: with the asks directory gone the grouped row DISAPPEARS and the owner asks remain — the arm above discriminates',
    !withoutDir.some((x) => x.id === grouped.ask_id)
      && withoutDir.some((x) => x.id === '1724500001.000100'),
    `ids=${withoutDir.map((x) => x.id).join(',')}`);
  fs.renameSync(parked, asksHome);

  try { db.close(); } catch { /* the probe is done with it */ }
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }

  // ── H. THE THREE-STORE SPLIT — `openAsk`/`listOpenAsks` must resolve the ENDING store from
  // `workspaceRoot`, never from a caller's `heartStore` ────────────────────────────────────────
  //
  // Sections A-G above hand the dispatcher `heartStore: { db }` where `db` IS the ending store, so
  // a writer bound to the caller's handle looks identical to one bound to the home — exactly how
  // `919be192` found the sibling defect in `pause-resume.js` unmeasured by every existing fixture.
  // This section runs a SECOND scratch workspace whose `heartStore` is a genuinely DIFFERENT file
  // from the workspace's ending store (the daemon's real shape: `{data_root}/heart.db` vs
  // `<workspace>/.rbtv/runtime/ignite/heart.db`), and proves the fixed writer/reader never touch it.
  const root2 = fs.mkdtempSync(path.join(os.tmpdir(), 'inspect-asks-split-probe-'));
  seedGoal(root2, GOAL_A);
  const privateDb = openEndingStore(path.join(root2, 'private-lane-store', 'heart.db')); // NEVER the ending store
  const THREAD_H1 = '1724509001.100100';

  const openH1 = askRecord.openAsk({
    workspaceRoot: root2, goal: GOAL_A, seat: 'goal-master', thread: THREAD_H1, corpus: 'split-probe H1',
  });
  check('H1: SETUP — the ask recorded through the FIXED writer', openH1.recorded, JSON.stringify(openH1));
  check('H2: the row landed in the ENDING store (resolved from workspaceRoot), never the private lane store',
    Boolean(bind(openEndingStoreFor(root2)).getAsk(THREAD_H1)) && !bind(privateDb).getAsk(THREAD_H1));
  const listedH = askRecord.listOpenAsks(root2);
  check('H3: `listOpenAsks(workspaceRoot)` finds it — the reader and the writer resolve the SAME file',
    listedH.some((x) => x.id === THREAD_H1), `ids=${listedH.map((x) => x.id).join(',')}`);

  // RED CONTROL — a mutant restoring the pre-919be192-sibling shape: `openAsk`/`listOpenAsks` take
  // a caller `heartStore` and `bind(heartStore.db)` instead of resolving `openEndingStoreFor`. Run
  // against the SAME private store the daemon would hold, on a fresh thread, to reproduce the live
  // defect this fix closes: the write lands in the caller's store and the real reader sees nothing.
  const srcPath = path.join(__dirname, '..', '..', '..', 'state-store', 'heart', 'ask-record.js');
  const src = fs.readFileSync(srcPath, 'utf8');
  const openNeedle = "function openAsk({ workspaceRoot, goal, seat, thread, corpus, label = 'work-content' }) {";
  const bindNeedle = '    const api = bind(openEndingStoreFor(workspaceRoot));\n    const existing = api.getAsk(String(thread));';
  const listNeedle = 'function listOpenAsks(workspaceRoot) {\n  const api = bind(openEndingStoreFor(workspaceRoot));';
  check('M1: red-proof — both mutation needles are found in the fixed source',
    src.includes(openNeedle) && src.includes(bindNeedle) && src.includes(listNeedle));
  if (src.includes(openNeedle) && src.includes(bindNeedle) && src.includes(listNeedle)) {
    const mutBeside = path.join(path.dirname(srcPath), 'ask-record.MUTANT.js');
    const mutated = src
      .replace(openNeedle, "function openAsk(heartStore, { workspaceRoot, goal, seat, thread, corpus, label = 'work-content' }) {")
      .replace(bindNeedle, '    const api = bind(heartStore.db);\n    const existing = api.getAsk(String(thread));')
      .replace(listNeedle, 'function listOpenAsks(heartStore) {\n  const api = bind(heartStore.db);');
    fs.writeFileSync(mutBeside, mutated);
    try {
      const mut = require(mutBeside);
      const THREAD_M1 = '1724509002.200200';
      const mutOpen = mut.openAsk({ db: privateDb }, {
        workspaceRoot: root2, goal: GOAL_A, seat: 'goal-master', thread: THREAD_M1, corpus: 'split-probe mutant',
      });
      check('M2: red-proof SETUP — the mutant\'s write reports recorded',
        mutOpen.recorded, JSON.stringify(mutOpen));
      check('M3 RED — with the caller-store binding restored, the ask lands in the PRIVATE store and NOT the ending store (the live 2026-08-28 defect, reproduced)',
        Boolean(bind(privateDb).getAsk(THREAD_M1)) && !bind(openEndingStoreFor(root2)).getAsk(THREAD_M1));
      const mutListed = mut.listOpenAsks({ db: privateDb });
      const fixedListed = askRecord.listOpenAsks(root2);
      check('M4 RED — the FIXED reader (`listOpenAsks(workspaceRoot)`) answers NOTHING for the mutant\'s ask — the split, measured',
        !fixedListed.some((x) => x.id === THREAD_M1) && mutListed.some((x) => x.id === THREAD_M1),
        `fixed=${fixedListed.map((x) => x.id).join(',')} mutant-private=${mutListed.map((x) => x.id).join(',')}`);
    } finally {
      try { fs.rmSync(mutBeside, { force: true }); } catch {}
    }
  }

  try { privateDb.close(); } catch {}
  try { fs.rmSync(root2, { recursive: true, force: true }); } catch {}

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
