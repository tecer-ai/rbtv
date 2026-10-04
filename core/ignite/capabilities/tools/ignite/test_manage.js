#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { run } = require('./manage.js');
const { INSTALLER_ENTRY } = require('./connect.js');

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
  fs.writeFileSync(path.join(agent, 'agent.json'), JSON.stringify({ name: 'probe', harness: 'codex', model: 'gpt-6-sol', effort: 'high', units: [], packs: [] }), 'utf8');
  fs.writeFileSync(path.join(agent, 'agent.md'), '---\nname: probe\n---\n', 'utf8');
  try {
    const expected = spawnSync('python3', [INSTALLER_ENTRY, 'agent', 'configure', agent, '--effort', '2', '--dry-run'], { cwd: installation, encoding: 'utf8' });
    const actual = await captures(['configure', '--effort', '2', '--dry-run'], {}, { env: { RBTV_AGENT_HOME: agent } });
    assert.equal(actual.code, expected.status);
    assert.equal(actual.stdout, expected.stdout);
    assert.equal(actual.stderr, expected.stderr);
  } finally {
    fs.rmSync(installation, { recursive: true, force: true });
  }
  console.log('PASS manage');
})().catch((error) => { console.error(error.stack || error.message); process.exit(1); });
