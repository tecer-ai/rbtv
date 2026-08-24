'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { admitLaunch } = require('../../../envelope/launch');
const { writeWallReport } = require('../../../envelope/wall-report');
const { writeConfigShims, realStoreOnBinds } = require('../../../envelope/shims');

capture('probe-envelope-walls', async (lines) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'env-walls-'));
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
    fs.mkdirSync(path.join(goalDir, 'scratch'), { recursive: true });
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

    const missingScratch = path.join(workspace, '.rbtv', 'goals', 'gone', 'scratch');
    const refused = admitLaunch({ ...base, goalId: 'gone', goalDir: path.join(workspace, '.rbtv', 'goals', 'gone') });
    leg('4', 'unresolved template path is refused at launch',
      refused.spawn === false && refused.refuse && refused.refuse.kind === 'unresolved',
      `refuse=${JSON.stringify(refused.refuse)} missing=${missingScratch}`);

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
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  lines.push('ALL LEGS PASS');
});
