'use strict';

// Drives spawn.js#resolveSeatGrants over BOTH worktree roots (P3 self-root).
// CMP-17: repoGit / worktreeGitDir come from the worktree's own `.git` file, never caller input.
// A directory whose name does not end `--{goal}--{seat}` is not returned.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { resolveSeatGrants } = require('../spawn');

capture('probe-resolve-seat-grants', async (lines) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'rsg-'));
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  try {
    const goal = 'g1';
    const seat = 'alpha';
    const suffix = `--${goal}--${seat}`;

    function plant(dir, name, gitdir) {
      const wt = path.join(dir, name);
      fs.mkdirSync(wt, { recursive: true });
      fs.writeFileSync(path.join(wt, '.git'), `gitdir: ${gitdir}\n`);
      return wt;
    }

    const ws = path.join(root, 'ws');
    const defaultRoot = path.join(ws, '.rbtv', 'worktrees');
    const selfRoot = path.join(ws, '5-workbench', 'vault-worktrees');
    fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
    fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'worktrees-self-root'),
      '5-workbench/vault-worktrees\n');

    const aGitdir = '/tmp/fake-a/.git/worktrees/a';
    const bGitdir = '/tmp/fake-b/.git/worktrees/b';
    plant(defaultRoot, `repo${suffix}`, aGitdir);
    plant(selfRoot, `vault${suffix}`, bGitdir);
    plant(defaultRoot, 'repo--othergoal--alpha', '/tmp/fake-x/.git/worktrees/x');
    plant(selfRoot, 'not-a-worktree', '/tmp/fake-y/.git/worktrees/y');

    const grants = resolveSeatGrants({ workspaceRoot: ws, goal, seat });
    const names = grants.map((g) => g.worktreeName).sort();
    leg('R-1', 'returns grants from BOTH roots',
      names.length === 2 && names.includes(`repo${suffix}`) && names.includes(`vault${suffix}`),
      `names=${JSON.stringify(names)}`);

    const byName = Object.fromEntries(grants.map((g) => [g.worktreeName, g]));
    const a = byName[`repo${suffix}`] || {};
    const b = byName[`vault${suffix}`] || {};
    leg('R-2', 'CMP-17: repoGit/worktreeGitDir from the worktree .git (default root)',
      a.repoGit === '/tmp/fake-a/.git' && a.worktreeGitDir === aGitdir,
      JSON.stringify(a));
    leg('R-3', 'CMP-17: repoGit/worktreeGitDir from the worktree .git (self root)',
      b.repoGit === '/tmp/fake-b/.git' && b.worktreeGitDir === bGitdir,
      JSON.stringify(b));
    leg('R-4', 'negative control: non-suffix directories are NOT returned',
      !names.includes('repo--othergoal--alpha') && !names.includes('not-a-worktree'),
      `names=${JSON.stringify(names)}`);

    const ws2 = path.join(root, 'ws2');
    fs.mkdirSync(path.join(ws2, '.rbtv', 'config'), { recursive: true });
    fs.mkdirSync(path.join(ws2, '.rbtv', 'worktrees'), { recursive: true });
    fs.writeFileSync(path.join(ws2, '.rbtv', 'config', 'worktrees-self-root'),
      '5-workbench/vault-worktrees\n');
    plant(path.join(ws2, '.rbtv', 'worktrees'), `repo${suffix}`, aGitdir);
    const g2 = resolveSeatGrants({ workspaceRoot: ws2, goal, seat });
    leg('R-5', 'missing self-root directory is not an error',
      g2.length === 1 && g2[0].worktreeName === `repo${suffix}`,
      `len=${g2.length} names=${JSON.stringify(g2.map((g) => g.worktreeName))}`);

    if (fails.length) throw new Error(`legs failed: ${fails.join(', ')}`);
  } finally {
    lines.push('');
    lines.push(`fixture: ${root}`);
    fs.rmSync(root, { recursive: true, force: true });
  }
});
