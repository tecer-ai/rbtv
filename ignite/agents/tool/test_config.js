#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { loadConfig, agentHome, storePath } = require('./config.js');

const failures = [];

function test(name, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-config-'));
  try {
    fn(dir);
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function writeConfig(dir, patch = {}) {
  const base = {
    workspace: dir,
    slack: {
      team: 'T1',
      botUserId: 'U1',
      ownerUserId: 'U2',
      botTokenFile: path.join(dir, 'bot.json'),
      appTokenSource: 'SLACK_APP_TOKEN',
      ownerTokenFile: path.join(dir, 'owner.json'),
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    defaultLaunch: { harness: 'claude', model: 'm', effort: 'high' },
    dmAgent: 'master',
    routes: { C1: 'gaming' },
  };
  const body = { ...base, ...patch };
  const folder = path.join(dir, '.rbtv', 'agents');
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(folder, 'ignite.json'), JSON.stringify(body));
  return body;
}

test('loads a valid workspace config from the runtime path', (dir) => {
  writeConfig(dir);
  const config = loadConfig(dir);
  assert.equal(config.dmAgent, 'master');
  assert.equal(config.routes.C1, 'gaming');
  assert.equal(config.slack.appTokenSource, 'SLACK_APP_TOKEN');
});

test('agentHome resolves under the given workspace', (dir) => {
  const config = writeConfig(dir);
  const loaded = loadConfig(dir);
  assert.equal(agentHome(loaded, 'master'), path.join(config.workspace, '.rbtv', 'agents', 'master'));
  assert.equal(storePath(loaded, 'gaming'), path.join(dir, '.rbtv', 'agents', 'gaming', 'state.sqlite'));
});

test('missing file throws', (dir) => {
  assert.throws(() => loadConfig(dir), /cannot load workspace config/);
});

test('workspace mismatch throws', (dir) => {
  writeConfig(dir, { workspace: path.join(dir, 'elsewhere') });
  assert.throws(() => loadConfig(dir), /does not match/);
});

test('missing field throws', (dir) => {
  const body = writeConfig(dir);
  delete body.slack.botUserId;
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /botUserId/);
});

test('relative token path and bad slug throw', (dir) => {
  const body = writeConfig(dir);
  body.slack.botTokenFile = 'credentials/token.json';
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /absolute path/);
  writeConfig(dir);
  assert.throws(() => agentHome(loadConfig(dir), '../escape'), /slug/);
  assert.throws(() => agentHome(loadConfig(dir), 'HasCaps'), /slug/);
});

test('appTokenSource accepts env name or absolute path only', (dir) => {
  const body = writeConfig(dir);
  body.slack.appTokenSource = path.join(dir, 'app.token');
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(body));
  assert.equal(loadConfig(dir).slack.appTokenSource, path.join(dir, 'app.token'));
  body.slack.appTokenSource = 'relative/app.token';
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /absolute/);
});

test('unknown field and bad route slug throw', (dir) => {
  const body = writeConfig(dir);
  body.extra = true;
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /unknown config field/);
  writeConfig(dir);
  const again = writeConfig(dir);
  again.routes = { C1: 'Not A Slug' };
  fs.writeFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), JSON.stringify(again));
  assert.throws(() => loadConfig(dir), /slug/);
});

test('empty routes object is valid', (dir) => {
  writeConfig(dir, { routes: {} });
  assert.deepEqual(loadConfig(dir).routes, {});
});

if (failures.length) {
  console.log(`FAIL ${failures.length}`);
  process.exit(1);
}
console.log('PASS config');
