'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture, fixtureRoot } = require('./lib');
const { admitLaunch } = require('../../../envelope/launch');
const { writeWallReport } = require('../../../envelope/wall-report');
const { writeConfigShims, realStoreOnBinds } = require('../../../envelope/shims');
const { parseSeatPath } = require('../../../runtime/seat-identity/seat-folder');
const { buildBwrapArgv } = require('../bwrap');
// Leg 10 drives the REAL exposed-CLI cover check out of the spawn door, not a copy of it: the
// defect it pins lived in that branch, so a probe re-spelling the predicate would prove nothing.
// Legs 11–13 drive composeCageFor itself: seat.md `rw-paths:` must become a bind (or refuse
// loudly), and rw+exposedCli on the same directory must still refuse.
const { composeCageFor, exposedCliConflict } = require('../spawn');

capture('probe-envelope-walls', async (lines) => {
  const root = fixtureRoot('env-walls-');
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  try {
    const workspace = path.join(root, 'ws');
    const home = path.join(root, 'home');
    const rbtvRepo = path.join(root, 'rbtv');
    const goalId = 'g1';
    const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
    const register = path.join(goalDir, 'register');
    fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
    fs.mkdirSync(path.join(workspace, '.rbtv', 'mirror', 'x'), { recursive: true });
    fs.mkdirSync(path.join(home, '.cache'), { recursive: true });
    fs.mkdirSync(path.join(home, '.config', 'tool'), { recursive: true });
    fs.mkdirSync(path.join(rbtvRepo, 'ignite', 'envelope'), { recursive: true });
    fs.mkdirSync(register, { recursive: true });
    fs.writeFileSync(path.join(home, '.claude.json'), '{"ok":true}\n');
    fs.mkdirSync(path.join(workspace, '3-resources', 'tools', 'stools'), { recursive: true });
    fs.writeFileSync(path.join(workspace, '3-resources', 'tools', 'stools', 'config.yaml'), 'token: x\n');
    fs.writeFileSync(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'), '');
    fs.writeFileSync(path.join(goalDir, 'envelope.json'), JSON.stringify({
      extraPaths: [{ path: register, access: 'rw' }],
    }));

    const base = { workspaceRoot: workspace, goalId, goalDir, home, tmpdir: os.tmpdir(), rbtvRepo };
    const admitted = admitLaunch(base);
    leg('1', 'admitLaunch returns a bind list',
      admitted.spawn === true && Array.isArray(admitted.binds) && admitted.binds.length > 0,
      `spawn=${admitted.spawn} binds=${(admitted.binds || []).length}`);
    const regBind = (admitted.binds || []).find((b) => path.resolve(b.path) === path.resolve(register));
    leg('2', 'plan-named register extraPath is on the bind list rw',
      !!regBind && regBind.access === 'rw',
      `regBind=${JSON.stringify(regBind)}`);

    const shims = writeConfigShims(base);
    const leaked = realStoreOnBinds(admitted.binds, shims.sources);
    leg('3', 'real harness/tool store paths are not on the bind list; shims land in scratch',
      leaked.length === 0 && shims.files.some((f) => f.harness === 'claude') && shims.files.some((f) => f.tool === 'stools'),
      `leaked=${leaked.join(',')} files=${shims.files.map((f) => f.dest).join(',')}`);

    // The goal scratch folder is NOT a case of this leg any more: `admitLaunch` materializes it
    // before compiling (it is where the §8 shims land), so leg 6 below holds that instead. The
    // unresolved arm needs a baked family path nothing on the launch path creates — family 6's
    // `{workspace}/.rbtv/mirror`, absent from this second workspace.
    const ws2 = path.join(root, 'ws-no-mirror');
    const goalDir2 = path.join(ws2, '.rbtv', 'goals', goalId);
    fs.mkdirSync(goalDir2, { recursive: true });
    const refused = admitLaunch({ ...base, workspaceRoot: ws2, goalDir: goalDir2 });
    leg('4', 'unresolved baked template path is refused at launch',
      refused.spawn === false && refused.refuse && refused.refuse.kind === 'unresolved'
        && refused.refuse.path === path.join(ws2, '.rbtv', 'mirror'),
      `refuse=${JSON.stringify(refused.refuse)}`);

    const rec = writeWallReport({
      path: path.join(home, '.cache', 'missed'),
      seat: 'worker',
      goal: goalId,
      goalDir,
      home,
      tmpdir: os.tmpdir(),
    });
    leg('5', 'benign-shaped wall writes family-match=cache with path/seat/goal',
      rec.record['family-match'] === 'cache' && rec.record.seat === 'worker' && rec.record.goal === goalId,
      JSON.stringify(rec.record));

    // Regression guard for the compile-order defect: family 4 bakes `{goal}/scratch`, nothing else
    // on the launch path creates it, so a compile-first order refused EVERY first launch with
    // `unresolved …/scratch`. `admitLaunch` must leave the folder on disk and bind it rw.
    const scratch = path.join(goalDir, 'scratch');
    const scratchBind = (admitted.binds || []).find((b) => path.resolve(b.path) === path.resolve(scratch));
    leg('6', 'launch materializes {goal}/scratch and binds it rw',
      fs.existsSync(scratch) && !!scratchBind && scratchBind.access === 'rw',
      `exists=${fs.existsSync(scratch)} bind=${JSON.stringify(scratchBind)}`);

    // ── leg 7 — THE OWN-SEAT RW PUNCH (spec-envelope §5), and its three boundaries ───────────
    // `{goal}/seats` is daemon-owned ro; §5's directory row excepts "a worker's need to write its
    // own seat folder" and `daemon-owned-records.yaml` records it as `own-seat-folder-rw`. The
    // compiler is per-goal and cannot spell `{self}`, so launch punches it — and until it did, a
    // seat spawned, passed caps-at-kernel, and could not write its own folder
    // (`probe-tmux-seat-live`, red on its own `a4-report.txt`).
    // Four assertions, because three of them are what keeps the punch from being a widening:
    // own folder rw; the seats TREE still ro; the PEER folder not rw; and `{self}/seat.md` still
    // ro AND still ordered after the punch — bwrap applies mounts in argv order, so a punch
    // appended last would remount the seat folder over that carve and hand the worker a writable
    // `seat.md`.
    const seats = path.join(goalDir, 'seats');
    const selfSeat = path.join(seats, 'w1');
    const peerSeat = path.join(seats, 'w2');
    fs.mkdirSync(selfSeat, { recursive: true });
    fs.mkdirSync(peerSeat, { recursive: true });
    fs.writeFileSync(path.join(selfSeat, 'seat.md'), '---\nseat: w1\n---\n');
    const punched = admitLaunch({ ...base, seatDir: selfSeat });
    const at = (p) => (punched.binds || []).find((b) => path.resolve(b.path) === path.resolve(p));
    const idx = (p) => (punched.binds || []).findIndex((b) => path.resolve(b.path) === path.resolve(p));
    const selfBind = at(selfSeat);
    const seatsBind = at(seats);
    const peerBind = at(peerSeat);
    const seatMd = at(path.join(selfSeat, 'seat.md'));
    leg('7', 'launch punches the OWN seat folder rw and nothing wider (seats tree ro, peer absent, own seat.md still ro and still after the punch)',
      !!selfBind && selfBind.access === 'rw' && selfBind.origin === 'own-seat'
        && !!seatsBind && seatsBind.access === 'ro'
        && !peerBind
        && !!seatMd && seatMd.access === 'ro' && idx(path.join(selfSeat, 'seat.md')) > idx(selfSeat)
        && idx(selfSeat) > idx(seats),
      `self=${JSON.stringify(selfBind)} seats=${seatsBind && seatsBind.access} peer=${JSON.stringify(peerBind)} seat.md=${seatMd && seatMd.access} order=${idx(seats)}<${idx(selfSeat)}<${idx(path.join(selfSeat, 'seat.md'))}`);

    // Leg 8 — the punch is `{self}` or nothing. A seatDir that is not a DIRECT child of the
    // launching goal's own `seats/` (a peer goal's seat, a nested path, a service seat whose home
    // IS the goal dir) must add no bind at all: the field is caller-supplied, and "punch whatever
    // I am handed" is how a one-folder exception becomes a grant source.
    const foreignGoalDir = path.join(workspace, '.rbtv', 'goals', 'g2');
    const foreignSeat = path.join(foreignGoalDir, 'seats', 'w9');
    fs.mkdirSync(foreignSeat, { recursive: true });
    const nested = path.join(selfSeat, 'deeper');
    fs.mkdirSync(nested, { recursive: true });
    const foreign = admitLaunch({ ...base, seatDir: foreignSeat });
    const deep = admitLaunch({ ...base, seatDir: nested });
    const service = admitLaunch({ ...base, seatDir: goalDir });
    const rwAt = (adm, p) => {
      const b = (adm.binds || []).find((x) => path.resolve(x.path) === path.resolve(p));
      return !!b && b.access === 'rw' && b.origin === 'own-seat';
    };
    leg('8', 'a seatDir outside the launching goal\'s own seats/ punches nothing',
      !rwAt(foreign, foreignSeat) && !rwAt(deep, nested) && !rwAt(service, goalDir),
      `foreign=${!rwAt(foreign, foreignSeat)} nested=${!rwAt(deep, nested)} service-home=${!rwAt(service, goalDir)}`);

    // Leg 9 — an unresolvable own seat folder is a REFUSE, not a silent read-only launch. The
    // compiler refuses every baked path that does not resolve; the punch holds the same line one
    // layer out, because the quiet alternative is the exact defect this leg set exists for.
    const ghost = admitLaunch({ ...base, seatDir: path.join(seats, 'not-materialized') });
    leg('9', 'an unresolvable own seat folder refuses the launch',
      ghost.spawn === false && ghost.refuse && ghost.refuse.kind === 'unresolved'
        && ghost.refuse.source === 'own-seat',
      `refuse=${JSON.stringify(ghost.refuse)}`);

    // ── leg 10 — AN EXPOSED CLI LAUNCHES OVER THE STANDARD GOAL BINDS ────────────────────────
    // `spawn.js#composeCageFor` re-asks "does anything cover anything else at a different
    // access?" over the COMPILED bind list once a seat declares `exposed-clis:`. Asked without
    // the compiler's carve rules, the answer is yes for a list the compiler itself admitted —
    // `{goal}` rw covers the daemon-owned `{goal}/seats` ro, and the own-seat punch adds
    // `{self}` rw inside that — so every such seat refused at spawn before any process existed.
    // Two arms, because the fix is only correct if it kept the refusal it was hiding: an ordinary
    // exposed CLI (code tree overlapping nothing at a different access) admits, and a CLI whose
    // code tree lands ro inside an opening the envelope holds rw still refuses. The second arm is
    // what says this is a carve, not a disabled check.
    const cliCode = path.join(rbtvRepo, 'ignite', 'coord');
    fs.mkdirSync(cliCode, { recursive: true });
    const sourcesFor = (codeDir) => [
      ...(punched.binds || []).map((b) => ({
        path: b.path, access: b.access, family: b.family, origin: b.origin, source: b.source || 'envelope',
      })),
      { path: codeDir, access: 'ro', source: 'exposedCli' },
    ];
    const admits = exposedCliConflict(sourcesFor(cliCode));
    // `{goal}/scratch` is bound rw by family 4 (leg 6); an exposed CLI rooted there is the real
    // shape of the refusal — an ro tree at a different access inside an rw opening, and carried by
    // no family or origin, so there is nothing for `authorizedCarve` to authorize.
    const overRw = exposedCliConflict(sourcesFor(scratch));
    leg('10', 'a seat with an exposed CLI launches over the standard goal binds, and an exposed CLI landing ro inside an rw bind still refuses',
      admits === null && !!overRw && overRw.kind === 'conflict',
      `admits=${JSON.stringify(admits)} over-rw=${JSON.stringify(overRw && overRw.pair && overRw.pair.map((x) => `${x.access}:${x.source}:${x.path}`))}`);

    const grantRel = path.join('.rbtv', 'mirror', 'x');
    const grantAbs = path.join(workspace, grantRel);
    const writerDir = path.join(goalDir, 'seats', 'writer');
    fs.mkdirSync(writerDir, { recursive: true });
    fs.writeFileSync(path.join(writerDir, 'seat.md'), [
      '---',
      'seat: writer',
      'harness: bash',
      'model: test-sleep',
      'rw-paths:',
      `  - ${grantRel}`,
      '---',
      '',
    ].join('\n'));
    const writerPath = parseSeatPath(writerDir);
    let composed;
    let composeErr = null;
    try {
      composed = composeCageFor({}, writerPath, writerDir, null, () => {});
    } catch (err) {
      composeErr = err;
    }
    const grantReal = fs.realpathSync(grantAbs);
    const hasRwBind = Array.isArray(composed) && composed.some((a, i) => a === '--bind' && composed[i + 1] === grantReal);
    const marker = path.join(grantAbs, 'WRITE-TEST');
    let writeExit = null;
    let writeStderr = '';
    let onDisk = 'ABSENT';
    if (Array.isArray(composed)) {
      const argv = buildBwrapArgv({
        argv: ['bash', '-c', `echo GRANTED > "${marker}" && echo WROTE`],
        workdir: writerDir,
        harness: null,
        seatBinds: composed,
      });
      try {
        execFileSync(argv[0], argv.slice(1), {
          stdio: ['ignore', 'pipe', 'pipe'], timeout: 15000, encoding: 'utf8',
        });
        writeExit = 0;
      } catch (err) {
        writeExit = err.status === undefined ? -1 : err.status;
        writeStderr = String(err.stderr || '').trim().slice(0, 240);
      }
      onDisk = fs.existsSync(marker) ? fs.readFileSync(marker, 'utf8').trim() : 'ABSENT';
    }
    leg('11', 'composeCageFor grants seat.md rw-paths under the mirror family; a caged write lands',
      !composeErr && hasRwBind && writeExit === 0 && onDisk === 'GRANTED',
      `err=${composeErr && (composeErr.message || composeErr.code)} hasBind=${hasRwBind} exit=${writeExit} stderr=${writeStderr} onDisk=${onDisk}`);

    // Leg 12 asserted the OPPOSITE until 2026-08-31 (`ignite-engine-loop` M1, register filing
    // `G-leader-0828-1951`): a declared rw path inside the rbtv SOURCE repo refused at compose
    // because `authorizedCarve` carried no `rbtv-repo` clause. The plan bound at 5dc32b91 settles
    // that floor as a GAP, so the leg now asserts the grant AND the fence in one breath — the
    // DECLARED subtree composes rw, an UNDECLARED sibling inside the same repo does not, and the
    // repo root keeps its own ro bind.
    const repoGrantAbs = path.join(rbtvRepo, 'ignite', 'envelope');
    const repoSibling = path.join(rbtvRepo, 'core');
    fs.mkdirSync(repoSibling, { recursive: true });
    const repoWrite = admitLaunch({
      ...base,
      extraPaths: [{ path: repoGrantAbs, access: 'rw' }],
    });
    const repoBinds = repoWrite.binds || [];
    const repoDeclaredRw = repoBinds.some((b) => b.access === 'rw' && fs.realpathSync(b.path) === fs.realpathSync(repoGrantAbs));
    const repoRootBind = repoBinds.find((b) => fs.realpathSync(b.path) === fs.realpathSync(rbtvRepo));
    const repoSiblingRw = repoBinds.some((b) => b.access === 'rw' && fs.realpathSync(b.path) === fs.realpathSync(repoSibling));
    leg('12', 'a DECLARED rw extraPath inside the rbtv source repo composes rw; the repo root stays ro and an UNDECLARED sibling gets no rw bind',
      repoWrite.spawn === true && repoDeclaredRw && repoRootBind && repoRootBind.access === 'ro' && !repoSiblingRw,
      `spawn=${repoWrite.spawn} declaredRw=${repoDeclaredRw} root=${repoRootBind && repoRootBind.access} siblingRw=${repoSiblingRw} refuse=${JSON.stringify(repoWrite.refuse)}`);

    fs.writeFileSync(path.join(grantAbs, 'cli.sh'), '#!/bin/sh\necho ok\n', { mode: 0o755 });
    fs.writeFileSync(path.join(writerDir, 'seat.md'), [
      '---',
      'seat: writer',
      'harness: bash',
      'model: test-sleep',
      'rw-paths:',
      `  - ${grantRel}`,
      'exposed-clis:',
      `  - demo-cli ${path.join(grantAbs, 'cli.sh')}`,
      '---',
      '',
    ].join('\n'));
    let clashErr = null;
    try {
      composeCageFor({}, writerPath, writerDir, null, () => {});
    } catch (err) {
      clashErr = err.refuse || { message: err.message, code: err.code };
    }
    leg('13', 'rw-paths and exposedCliCode on the SAME directory still refuse at compose (task 122)',
      !!clashErr && clashErr.kind === 'conflict',
      `refuse=${JSON.stringify(clashErr)}`);
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  lines.push('ALL LEGS PASS');
});
