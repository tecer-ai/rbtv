#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { configPath, loadConfig, updateConfig, agentHome, storePath, envValue, slackToken, paymentsConfig } = require('./config.js');

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
    slack: {
      team: 'T1',
      botUserId: 'U1',
      ownerUserId: 'U2',
      appTokenEnv: 'IGNITE_APP_TOKEN',
      botTokenEnv: 'IGNITE_BOT_TOKEN',
      ownerTokenEnv: 'IGNITE_OWNER_TOKEN',
      stoolsWorkspace: 'ignite',
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    dmAgent: 'master',
    routes: { C1: 'sample' },
  };
  const body = { ...base, ...patch, slack: { ...base.slack, ...patch.slack } };
  const folder = path.dirname(configPath(dir));
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(configPath(dir), JSON.stringify(body), 'utf8');
  return body;
}

function without(name, fn) {
  const prev = process.env[name];
  delete process.env[name];
  try {
    return fn();
  } finally {
    if (prev === undefined) delete process.env[name];
    else process.env[name] = prev;
  }
}

test('loads a valid config from the runtime path', (dir) => {
  writeConfig(dir);
  const config = loadConfig(dir);
  assert.equal(configPath(dir), path.join(dir, '.rbtv', 'config', 'ignite', 'config.json'));
  assert.equal(config.workspace, path.resolve(dir));
  assert.equal(config.dmAgent, 'master');
  assert.equal(config.routes.C1, 'sample');
  assert.equal(config.slack.appTokenEnv, 'IGNITE_APP_TOKEN');
  assert.equal(config.slack.botTokenEnv, 'IGNITE_BOT_TOKEN');
  assert.equal(Object.hasOwn(config, 'defaultLaunch'), false);
});

test('a legacy dreamer section loads and the next write drops enabled and model', (dir) => {
  writeConfig(dir, { dreamer: { enabled: true, model: { harness: 'codex', model: 'example-model', effort: 3 } } });
  const loaded = loadConfig(dir);
  assert.equal(Object.hasOwn(loaded, 'dreamer'), false);
  assert.equal(JSON.parse(fs.readFileSync(configPath(dir), 'utf8')).dreamer.enabled, true);
  const written = updateConfig(dir, (config) => { config.routes.C2 = 'sample'; });
  assert.equal(Object.hasOwn(written, 'dreamer'), false);
  const file = JSON.parse(fs.readFileSync(configPath(dir), 'utf8'));
  assert.equal(Object.hasOwn(file, 'dreamer'), false);
  assert.equal(file.routes.C2, 'sample');
  assert.equal(file.routes.C1, 'sample');
});

test('a config without a legacy dreamer section is unchanged by the next write', (dir) => {
  writeConfig(dir);
  const before = JSON.parse(fs.readFileSync(configPath(dir), 'utf8'));
  updateConfig(dir, (config) => config);
  const after = JSON.parse(fs.readFileSync(configPath(dir), 'utf8'));
  assert.deepEqual(after, before);
  assert.equal(Object.hasOwn(loadConfig(dir), 'dreamer'), false);
});

test('cast model-in-use check ignores a legacy dreamer section', (dir) => {
  writeConfig(dir, { dreamer: { enabled: true, model: { harness: 'claude', model: 'example-model', effort: 3 } } });
  const { usersOf } = require('../../../../cast/capabilities/tools/cast/lib/models.js');
  const found = usersOf(dir, 'claude', 'example-model');
  assert.deepEqual(found.users, []);
  assert.ok(!found.unread.some((line) => /dreamer/i.test(line)));
});

test('agentHome resolves under the given workspace', (dir) => {
  writeConfig(dir);
  const loaded = loadConfig(dir);
  assert.equal(agentHome(loaded, 'master'), path.join(dir, '.rbtv', 'agents', 'master'));
  assert.equal(storePath(loaded, 'sample'), path.join(dir, '.rbtv', 'agents', 'sample', 'runtime', 'ignite', 'state.sqlite'));
});

test('missing file throws', (dir) => {
  assert.throws(() => loadConfig(dir), /cannot load Ignite config/);
});

test('missing field throws', (dir) => {
  const body = writeConfig(dir);
  delete body.slack.botUserId;
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /botUserId/);
});

test('bad slug throws', (dir) => {
  writeConfig(dir);
  assert.throws(() => agentHome(loadConfig(dir), '../escape'), /slug/);
  assert.throws(() => agentHome(loadConfig(dir), 'HasCaps'), /slug/);
});

test('token env name is a name, not a path', (dir) => {
  const body = writeConfig(dir);
  body.slack.appTokenEnv = path.join(dir, 'app.token');
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /environment variable name/);
  body.slack.appTokenEnv = 'relative/app.token';
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /environment variable name/);
});

test('unknown field and bad route slug throw', (dir) => {
  const body = writeConfig(dir);
  body.defaultLaunch = { harness: 'claude' };
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /unknown config field/);
  const again = writeConfig(dir);
  again.slack.botTokenFile = path.join(dir, 'bot.json');
  fs.writeFileSync(configPath(dir), JSON.stringify(again));
  assert.throws(() => loadConfig(dir), /unknown slack field/);
  again.slack = writeConfig(dir).slack;
  again.routes = { C1: 'Not A Slug' };
  fs.writeFileSync(configPath(dir), JSON.stringify(again));
  assert.throws(() => loadConfig(dir), /slug/);
});

test('stoolsWorkspace required and not a path', (dir) => {
  const body = writeConfig(dir);
  delete body.slack.stoolsWorkspace;
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /stoolsWorkspace required/);
  body.slack.stoolsWorkspace = path.join(dir, 'vault');
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /not a path/);
});

test('empty routes object is valid and dmAgent is optional', (dir) => {
  const body = writeConfig(dir, { routes: {} });
  delete body.dmAgent;
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  const config = loadConfig(dir);
  assert.deepEqual(config.routes, {});
  assert.equal(config.dmAgent, undefined);
  body.dmAgent = 'Not-A-Slug';
  fs.writeFileSync(configPath(dir), JSON.stringify(body));
  assert.throws(() => loadConfig(dir), /dmAgent/);
});

test('envValue prefers the OS environment, then .env', (dir) => {
  const name = `IGNITE_W5A_ENV_${process.pid}`;
  const envDir = path.join(dir, '.rbtv', 'config', 'env');
  fs.mkdirSync(envDir, { recursive: true });
  fs.writeFileSync(path.join(envDir, '.env'), `${name}="from-file"\r\nOTHER=xoxb-other\n# ${name}=comment\n`);
  without(name, () => {
    assert.equal(envValue(dir, name), 'from-file');
    assert.equal(envValue(dir, 'OTHER'), 'xoxb-other');
    assert.equal(envValue(dir, 'MISSING_IGNITE_W5A'), null);
    process.env[name] = 'from-env';
    assert.equal(envValue(dir, name), 'from-env');
  });
});

test('unset token names the variable and not a value', (dir) => {
  const appName = `IGNITE_W5A_APP_${process.pid}`;
  const botName = `IGNITE_W5A_BOT_${process.pid}`;
  const secret = 'xoxb-do-not-print-w5a';
  writeConfig(dir, { slack: { appTokenEnv: appName, botTokenEnv: botName } });
  const envDir = path.join(dir, '.rbtv', 'config', 'env');
  fs.mkdirSync(envDir, { recursive: true });
  fs.writeFileSync(path.join(envDir, '.env'), `${botName}=${secret}\n`);
  without(appName, () => without(botName, () => {
    const config = loadConfig(dir);
    assert.throws(() => slackToken(config, 'app'), (error) => {
      assert.match(error.message, new RegExp(appName));
      assert.equal(error.message.includes(secret), false);
      assert.equal(error.message.includes('xoxb'), false);
      return true;
    });
    assert.equal(slackToken(config, 'bot'), secret);
  }));
});

test('a payments section turns the gate on, with its defaults; no section leaves it off', (dir) => {
  writeConfig(dir);
  assert.equal(paymentsConfig(loadConfig(dir)), null);
  writeConfig(dir, { payments: {} });
  assert.deepEqual(paymentsConfig(loadConfig(dir)), { webhookPort: 8787, providers: ['asaas'], timeZone: 'America/Sao_Paulo', currency: 'BRL' });
  writeConfig(dir, { payments: { webhookPort: 9000, providers: ['otherbank'], timeZone: 'Europe/Lisbon', currency: 'EUR' } });
  assert.deepEqual(paymentsConfig(loadConfig(dir)), { webhookPort: 9000, providers: ['otherbank'], timeZone: 'Europe/Lisbon', currency: 'EUR' });
});

test('a payments section refuses an unknown field, a bad port, provider, time zone or currency', (dir) => {
  for (const [payments, message] of [
    [{ mode: 'automatic' }, /^Error: unknown payments field: mode/],
    [{ webhookTokenEnv: 'PAY_HOOK' }, /^Error: unknown payments field: webhookTokenEnv/],
    [{ webhookPort: 0 }, /^Error: payments.webhookPort must be a port number from 1 to 65535$/],
    [{ webhookPort: '8787' }, /^Error: payments.webhookPort must be a port number from 1 to 65535$/],
    [{ providers: 'asaas' }, /^Error: payments.providers must be a list of provider names, such as \["asaas"\]$/],
    [{ providers: ['../asaas'] }, /^Error: payments.providers must be a list of provider names, such as \["asaas"\]$/],
    [{ timeZone: 'Mars/Base' }, /^Error: payments.timeZone must be an IANA time zone, such as America\/Sao_Paulo$/],
    [{ currency: 'real' }, /^Error: payments.currency must be an ISO 4217 currency code, such as BRL$/],
    [{ currency: 'JPY' }, /^Error: payments.currency must be a currency with two decimals: amounts are kept in hundredths$/],
    ['on', /payments must be an object/],
  ]) {
    writeConfig(dir, { payments });
    assert.throws(() => loadConfig(dir), message);
  }
});

if (failures.length) {
  console.log(`FAIL ${failures.length}`);
  process.exit(1);
}
console.log('PASS config');
