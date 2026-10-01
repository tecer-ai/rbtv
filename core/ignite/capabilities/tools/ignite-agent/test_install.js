#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { main } = require('./cli.js');
const { spawnSync } = require('node:child_process');
const { STANDARD_UNITS, INSTALLER_ENTRY } = require('./install.js');

const failures = [];

async function test(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

function workspace() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-install-'));
}

function agentFile(dir, name = 'probe') {
  const file = path.join(dir, `${name}.md`);
  fs.writeFileSync(file, `---\nname: ${name}\ndescription: A probe agent.\n---\n\n## Role\n\nProbe.\n`);
  return file;
}

function tree(dir) {
  const out = [];
  const walk = (current) => {
    for (const name of fs.readdirSync(current)) {
      const abs = path.join(current, name);
      out.push(path.relative(dir, abs));
      if (fs.statSync(abs).isDirectory()) walk(abs);
    }
  };
  if (fs.existsSync(dir)) walk(dir);
  return out.sort();
}

async function run(argv, extra = {}) {
  const out = [];
  const err = [];
  const code = await main(argv, {
    stdout: (text) => out.push(text),
    stderr: (text) => err.push(text),
    ...extra,
  });
  return { code, out: out.join(''), err: err.join('') };
}

function stubInstall(calls) {
  return (args) => {
    calls.push(args);
    return { status: 0, stdout: '', stderr: '' };
  };
}

(async () => {
  await test('dry-run plan lists standard units and writes nothing', async () => {
    const dir = workspace();
    const file = agentFile(dir);
    const before = tree(dir);
    const calls = [];
    const result = await run([
      'install', file, '--workspace', dir, '--harness', 'claude', '--model', 'm', '--effort', 'high', '--dry-run',
    ], { install: stubInstall(calls) });
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /writes: none/);
    assert.match(result.out, /agent: probe/);
    for (const unit of STANDARD_UNITS) assert.match(result.out, new RegExp(unit.replace(/[/#]/g, '\\$&')));
    assert.equal(calls.length, 2);
    assert.deepEqual(calls[0].slice(0, 2), ['agent', 'add']);
    assert.equal(calls[0].includes('--dry-run'), true);
    assert.equal(calls[1][0], 'add');
    assert.equal(calls[1].includes('--dry-run'), true);
    assert.equal(calls[1][calls[1].indexOf('--guidance') + 1], 'none');
    assert.equal(calls[1][calls[1].indexOf('--harness') + 1], 'claude');
    assert.equal(calls[1].includes('core/ignite#ignite-standing-instructions'), true);
    assert.deepEqual(tree(dir), before);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
  });

  await test('install refuses when the agent exists and points at update', async () => {
    const dir = workspace();
    const file = agentFile(dir);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.md'), 'already\n');
    fs.writeFileSync(path.join(home, 'launch.json'), '{"harness":"claude","model":"m","effort":"high"}\n');
    const calls = [];
    const result = await run([
      'install', file, '--workspace', dir, '--harness', 'claude', '--model', 'm', '--effort', 'high',
    ], { install: stubInstall(calls) }).catch((error) => error);
    assert.match(result.message, /already installed/);
    assert.match(result.message, /ignite-agent update probe/);
    assert.equal(calls.length, 0);
    assert.equal(fs.readFileSync(path.join(home, 'agent.md'), 'utf8'), 'already\n');
  });

  await test('install writes board and sqlite without overwriting a board', async () => {
    const dir = workspace();
    const file = agentFile(dir);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'board.md'), '# Board\n\nkept\n');
    const result = await run([
      'install', file, '--workspace', dir, '--harness', 'claude', '--model', 'm', '--effort', 'high',
    ], { install: stubInstall([]) });
    assert.equal(result.code, 0, result.out + result.err);
    assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), '# Board\n\nkept\n');
    assert.match(result.out, /board: kept/);
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), true);
    assert.equal(fs.existsSync(path.join(home, 'conversations')), true);
  });

  await test('update keeps board launch settings and conversations', async () => {
    const dir = workspace();
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(path.join(home, 'conversations'), { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.md'), '---\nname: probe\ndescription: fixture\n---\n\n## Role\n\nKeep.\n');
    fs.writeFileSync(path.join(home, 'launch.json'), '{"harness":"claude","model":"m","effort":"high"}\n');
    fs.writeFileSync(path.join(home, 'settings.json'), '{"kept":true}\n');
    fs.writeFileSync(path.join(home, 'board.md'), '# Board\n\nkept board\n');
    fs.writeFileSync(path.join(home, 'conversations', 'kept.md'), 'history\n');
    const calls = [];
    const result = await run(['update', 'probe', '--workspace', dir], { install: stubInstall(calls) });
    assert.equal(result.code, 0, result.out + result.err);
    assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), '# Board\n\nkept board\n');
    assert.equal(fs.readFileSync(path.join(home, 'launch.json'), 'utf8'), '{"harness":"claude","model":"m","effort":"high"}\n');
    assert.equal(fs.readFileSync(path.join(home, 'settings.json'), 'utf8'), '{"kept":true}\n');
    assert.equal(fs.readFileSync(path.join(home, 'conversations', 'kept.md'), 'utf8'), 'history\n');
    assert.equal(fs.readFileSync(path.join(home, 'agent.md'), 'utf8').includes('Keep.'), true);
    assert.deepEqual(calls[0].slice(0, 3), ['agent', 'update', 'probe']);
    assert.equal(calls[0].includes('--dry-run'), false);
    assert.equal(calls[1][0], 'add');
    assert.equal(calls[1][calls[1].indexOf('--harness') + 1], 'claude');
    assert.equal(calls[1].includes('--guidance'), true);
    assert.match(result.out, /kept: launch.json, settings.json, board.md/);
  });

  await test('update dry-run writes nothing', async () => {
    const dir = workspace();
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.writeFileSync(path.join(home, 'agent.md'), '---\nname: probe\ndescription: fixture\n---\n');
    fs.writeFileSync(path.join(home, 'launch.json'), '{"harness":"codex","model":"m","effort":"low"}\n');
    fs.writeFileSync(path.join(home, 'board.md'), 'stay\n');
    const before = tree(dir);
    const calls = [];
    const result = await run(['update', 'probe', '--workspace', dir, '--dry-run'], { install: stubInstall(calls) });
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /writes: none/);
    assert.equal(calls[0].includes('--dry-run'), true);
    assert.equal(calls[1].includes('--dry-run'), true);
    assert.equal(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), 'stay\n');
    assert.deepEqual(tree(dir), before);
  });

  await test('real installer agent add dry-run writes nothing', async () => {
    const dir = workspace();
    const file = agentFile(dir);
    const before = tree(dir);
    const result = await run([
      'install', file, '--workspace', dir, '--harness', 'claude', '--model', 'fable-5', '--effort', 'high', '--dry-run',
    ]);
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /writes: none/);
    assert.match(result.out, /core\/ignite#ignite-standing-instructions/);
    assert.match(result.out, /launch: claude fable-5 high/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
    assert.deepEqual(tree(dir), before);
  });

  // A standard unit removed or renamed in rbtv would otherwise fail only at install time on a live
  // machine; the real installer resolves every listed key here (a dry run writes nothing).
  await test('every standard unit exists in the rbtv source', async () => {
    const dir = workspace();
    const python = process.platform === 'win32' ? 'python' : 'python3';
    const result = spawnSync(python, [INSTALLER_ENTRY, 'add', ...STANDARD_UNITS,
      '--harness', 'claude', '--guidance', 'none', '--target', dir, '--dry-run'], { encoding: 'utf8' });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    assert.equal(STANDARD_UNITS.includes('meta/sub-agents#swarm'), false, 'swarm is a capability of sub-agents now');
  });

  await test('create is not a command', async () => {
    const result = await run(['create', '--workspace', workspace()]).catch((error) => error);
    assert.match(result.message, /unknown command: create/);
  });

  if (failures.length) {
    console.log(`FAILED ${failures.length}`);
    process.exit(1);
  }
  console.log('ok');
})().catch((error) => {
  console.log(`FAIL runner: ${error.stack || error.message}`);
  process.exit(1);
});
