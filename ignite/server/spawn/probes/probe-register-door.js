'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { admitLaunch } = require('../../../envelope/launch');

capture('probe-register-door', async (lines) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'register-door-'));
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
    const goalId = 'ignite-engine';
    const goalDir = path.join(workspace, '.rbtv', 'goals', goalId);
    const register = path.join(goalDir, 'register');
    fs.mkdirSync(path.join(goalDir, 'scratch'), { recursive: true });
    fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
    fs.mkdirSync(path.join(workspace, '.rbtv', 'mirror', 'x'), { recursive: true });
    fs.mkdirSync(path.join(home, '.cache'), { recursive: true });
    fs.mkdirSync(path.join(home, '.config', 'tool'), { recursive: true });
    fs.mkdirSync(path.join(rbtvRepo, 'ignite', 'envelope'), { recursive: true });
    fs.mkdirSync(register, { recursive: true });
    fs.writeFileSync(path.join(rbtvRepo, 'ignite', 'envelope', 'spawn-profiles.yaml'), '');
    fs.writeFileSync(path.join(goalDir, 'envelope.json'), JSON.stringify({
      extraPaths: [{ path: register, access: 'rw' }],
    }));
    const admitted = admitLaunch({
      workspaceRoot: workspace,
      goalId,
      goalDir,
      home,
      tmpdir: os.tmpdir(),
      rbtvRepo,
    });
    const bind = (admitted.binds || []).find((b) => path.resolve(b.path) === path.resolve(register));
    leg('L1', 'plan-named register extraPath is an rw bind',
      admitted.spawn === true && bind && bind.access === 'rw',
      `spawn=${admitted.spawn} bind=${JSON.stringify(bind)}`);
    const sessions = path.join(goalDir, 'sessions.csv');
    fs.writeFileSync(sessions, 'seat\n');
    const sessionBind = (admitted.binds || []).find((b) => path.resolve(b.path) === path.resolve(sessions));
    leg('L2', 'daemon-owned sessions.csv is not an rw extraPath punch',
      !sessionBind || sessionBind.access === 'ro',
      `sessionBind=${JSON.stringify(sessionBind)}`);
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  lines.push('ALL LEGS PASS');
});
