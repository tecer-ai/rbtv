#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
// The platform helper is swapped in before manage.js loads (it reads the helper once, at load).
// Outside the check that sets helperStandIn, the real helper runs.
const winExecPath = require.resolve('../../../../cast/capabilities/tools/cast/lib/win-exec.js');
const winExec = require(winExecPath);
let helperStandIn = null;
require.cache[winExecPath].exports = {
  ...winExec,
  spawnable: (cmd, args) => (helperStandIn ? helperStandIn(cmd, args) : winExec.spawnable(cmd, args)),
};
const { spawnSync } = require('node:child_process');
const { run } = require('./manage.js');
const { INSTALLER_ENTRY } = require('./connect.js');

const CAST_MODELS = '{"models":[{"harness":"codex","model":"gpt-6.1-sol","mode":"cli","rungs":["low","medium","high"],"effort_numbers":{"low":1,"medium":2,"high":3},"selected":true}]}';

async function captures(argv, flags, deps) {
  let stdout = '';
  let stderr = '';
  const code = await run(argv, flags, { ...deps, stdout: (text) => { stdout += text; }, stderr: (text) => { stderr += text; } });
  return { code, stdout, stderr };
}

(async () => {
  const home = '/tmp/calling-agent';
  const forwarded = await captures(['configure', '--effort', '2', '--dry-run'], {}, {
    env: { RBTV_AGENT_HOME: home },
    install: async (args) => {
      assert.deepEqual(args, ['agent', 'configure', home, '--effort', '2', '--dry-run']);
      return { status: 7, stdout: 'forwarded stdout\n', stderr: 'forwarded stderr\n' };
    },
  });
  assert.deepEqual(forwarded, { code: 7, stdout: 'forwarded stdout\n', stderr: 'forwarded stderr\n' });

  const refused = await captures(['add', 'kiss'], {}, { env: {} });
  assert.equal(refused.code, 1);
  assert.equal(refused.stdout, '');
  assert.match(refused.stderr, /rbtv agent add AGENT kiss/);

  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-manage-'));
  const agent = path.join(installation, '.rbtv', 'agents', 'probe');
  fs.mkdirSync(agent, { recursive: true });
  fs.writeFileSync(path.join(agent, 'agent.json'), JSON.stringify({ name: 'probe', description: 'Probe.', harness: 'codex', model: 'gpt-6.1-sol', effort: 'high', files: [], packs: [] }), 'utf8');
  fs.writeFileSync(path.join(agent, 'agent.md'), '---\nname: probe\n---\n', 'utf8');
  // The installer checks the model and the effort word against `cast models list`, so a stand-in cast
  // answers for this one model, in the shape `cast models list --supported --json` prints. The effort is a word: what a number means the installer asks cast, and this
  // stand-in gives only the list.
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-manage-bin-'));
  const cast = path.join(bin, process.platform === 'win32' ? 'cast.cmd' : 'cast');
  fs.writeFileSync(cast, process.platform === 'win32'
    ? `@echo ${CAST_MODELS}\r\n`
    : `#!/bin/sh\nprintf '%s\\n' '${CAST_MODELS}'\n`);
  if (process.platform !== 'win32') fs.chmodSync(cast, 0o755);
  const oldPath = process.env.PATH;
  process.env.PATH = `${bin}${path.delimiter}${oldPath}`;
  try {
    // Through the installation, by name: the installer's own output for that form (screen 330).
    const expected = spawnSync('python3', [INSTALLER_ENTRY, 'agent', 'configure', 'probe', '--effort', 'medium', '--dry-run'], { cwd: installation, encoding: 'utf8' });
    assert.equal(expected.status, 0, expected.stdout + expected.stderr);
    const actual = await captures(['configure', '--effort', 'medium', '--dry-run'], {}, { env: { RBTV_AGENT_HOME: agent } });
    assert.equal(actual.code, expected.status);
    assert.equal(actual.stdout, expected.stdout);
    assert.equal(actual.stderr, expected.stderr);
  } finally {
    process.env.PATH = oldPath;
    fs.rmSync(bin, { recursive: true, force: true });
    fs.rmSync(installation, { recursive: true, force: true });
  }
  // (a) models starts cast through the platform helper, and passes what the helper returns to the spawn.
  const started = [];
  helperStandIn = (cmd, args) => {
    started.push([cmd, args]);
    return { cmd: process.execPath, args: ['-e', "process.stdout.write('[]\\n')"], opts: {} };
  };
  const viaHelper = await captures(['models'], {}, { env: {} });
  helperStandIn = null;
  assert.deepEqual(started, [['cast', ['models', 'list']]]);
  assert.deepEqual(viaHelper, { code: 0, stdout: '[]\n', stderr: '' });

  // cast runs in --installation when given, so that installation's selection answers; without it,
  // in the current folder. Arguments pass through after `models list`.
  const elsewhere = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-manage-cwd-')));
  const asked = [];
  helperStandIn = (cmd, args) => {
    asked.push(args);
    return { cmd: process.execPath, args: ['-e', 'process.stdout.write(process.cwd())'], opts: {} };
  };
  const inInstallation = await captures(['models', '--supported', '--json'], { installation: elsewhere }, { env: {} });
  const inCurrent = await captures(['models'], {}, { env: {} });
  helperStandIn = null;
  fs.rmSync(elsewhere, { recursive: true, force: true });
  assert.deepEqual(asked, [['models', 'list', '--supported', '--json'], ['models', 'list']]);
  assert.deepEqual(inInstallation, { code: 0, stdout: elsewhere, stderr: '' });
  assert.deepEqual(inCurrent, { code: 0, stdout: process.cwd(), stderr: '' });

  // (b) a start that fails is never silent: the error goes to stderr and the exit code is 1.
  const emptyPath = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-manage-empty-'));
  const oldPathB = process.env.PATH;
  process.env.PATH = emptyPath;
  try {
    const missing = await captures(['models'], {}, { env: {} });
    assert.equal(missing.code, 1);
    assert.equal(missing.stdout, '');
    assert.match(missing.stderr, /spawnSync cast ENOENT/);
  } finally {
    process.env.PATH = oldPathB;
    fs.rmSync(emptyPath, { recursive: true, force: true });
  }

  // (c) Windows only: a stand-in cast.cmd first on PATH is started, and its output is passed through.
  if (process.platform === 'win32') {
    const castBin = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-manage-cmd-'));
    fs.writeFileSync(path.join(castBin, 'cast.cmd'), '@echo off\r\necho ignite-stand-in-cast\r\n', 'utf8');
    const oldPathC = process.env.PATH;
    process.env.PATH = `${castBin}${path.delimiter}${oldPathC}`;
    try {
      const viaCmd = await captures(['models'], {}, { env: {} });
      assert.equal(viaCmd.code, 0);
      assert.match(viaCmd.stdout, /ignite-stand-in-cast/);
    } finally {
      process.env.PATH = oldPathC;
      fs.rmSync(castBin, { recursive: true, force: true });
    }
  }

  const unknown = await run(['settings'], {}, { env: {} }).catch((error) => error);
  assert.equal(unknown.exitCode, 1);
  assert.equal(unknown.message, 'unknown command: settings\nchoose from add, remove, configure, update, models, list, search, show\nNothing changed.\nignite manage -h');

  const help = await captures(['add', '-h'], {}, {
    env: {},
    install: async (args) => {
      assert.deepEqual(args, ['agent', 'add', '-h']);
      return { status: 0, stdout: 'rbtv — agent add help\n', stderr: '' };
    },
  });
  assert.equal(help.stdout, 'ignite manage add — runs rbtv agent add <this agent>.\n'
    + '<this agent> is RBTV_AGENT_HOME, or --agent NAME --installation PATH.\n'
    + 'Outside a turn this is refused. Use: rbtv agent add AGENT\n\nrbtv — agent add help\n');

  const named = await captures(['configure', '--effort', '2', '--dry-run'], {}, {
    env: { RBTV_AGENT_HOME: '/tmp/rbtv-no-such-installation/.rbtv/agents/probe' },
    install: async (args) => {
      // Named, so the installer's "Next:" line names no path (screen 330).
      assert.deepEqual(args, ['agent', 'configure', 'probe', '--effort', '2', '--dry-run']);
      return { status: 0, stdout: '', stderr: '' };
    },
  });
  assert.equal(named.code, 0);

  const outside = '/tmp/rbtv-no-such-installation/plans/probe';
  await captures(['configure', '--dry-run'], {}, {
    env: { RBTV_AGENT_HOME: outside },
    install: async (args) => {
      assert.deepEqual(args, ['agent', 'configure', outside, '--dry-run']);
      return { status: 0, stdout: '', stderr: '' };
    },
  });

  console.log('PASS manage');
})().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
