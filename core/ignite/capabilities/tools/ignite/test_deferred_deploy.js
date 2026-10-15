#!/usr/bin/env node
'use strict';

// Suite for deferred-deploy.js: the request ignite deploy --after-turn records, and the daemon's
// step that starts it once no turn runs and reports the deploy log line back.

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const deferred = require('./deferred-deploy.js');

const COMMIT = 'c1e5b34574d62d9173a37ae5bbf266ba32932be3';

function scratch(t) {
  const installation = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-deferred-'));
  t.after(() => fs.rmSync(installation, { recursive: true, force: true }));
  const log = path.join(installation, '.rbtv', 'runtime', 'ignite', 'deploys.jsonl');
  const calls = { start: [], report: [] };
  const deps = (over = {}) => ({
    installation,
    busy: () => false,
    start(req) { calls.start.push(req); return { ok: true }; },
    report(req, text) { calls.report.push({ req, text }); },
    ...over,
  });
  const appendLog = (row) => {
    fs.mkdirSync(path.dirname(log), { recursive: true });
    fs.appendFileSync(log, `${JSON.stringify(row)}\n`);
  };
  const ask = (now = 1000) => deferred.request({ installation, commit: COMMIT, deployFolder: '/deploy', agent: 'master', conversation: 'T1:D1:1.1', now });
  return { installation, calls, deps, appendLog, ask, file: deferred.requestFile(installation) };
}

test('no request: nothing to do', (t) => {
  const s = scratch(t);
  assert.equal(deferred.step(s.deps()), 'none');
  assert.equal(s.calls.start.length, 0);
});

test('a running turn holds the deploy; it starts once, when no turn runs', (t) => {
  const s = scratch(t);
  s.ask();
  assert.equal(deferred.step(s.deps({ busy: () => true, now: 2000 })), 'waiting');
  assert.equal(s.calls.start.length, 0);
  assert.equal(deferred.step(s.deps({ now: 3000 })), 'started');
  assert.equal(deferred.step(s.deps({ now: 4000 })), 'started');
  assert.equal(s.calls.start.length, 1, 'started once: the start is recorded before the launch');
  assert.equal(s.calls.start[0].startedAt, 3000);
  assert.equal(JSON.parse(fs.readFileSync(s.file, 'utf8')).startedAt, 3000);
});

test('the log line of this deploy is reported and the request closed; an older line for the commit is not', (t) => {
  const s = scratch(t);
  s.ask();
  const started = Date.parse('2026-10-15T14:00:00Z');
  deferred.step(s.deps({ now: started }));
  s.appendLog({ time: '2026-10-15T13:00:00.000Z', commitAsked: COMMIT, outcome: 'ok' });
  assert.equal(deferred.step(s.deps({ now: started + 1000 })), 'started');
  assert.equal(s.calls.report.length, 0);
  const row = { time: '2026-10-15T14:00:40.000Z', commitAsked: COMMIT, outcome: 'failed', reason: 'deploy.sh exited 1.' };
  s.appendLog(row);
  assert.equal(deferred.step(s.deps({ now: started + 60_000 })), 'reported');
  assert.equal(s.calls.report.length, 1);
  assert.equal(s.calls.report[0].req.conversation, 'T1:D1:1.1');
  assert.match(s.calls.report[0].text, new RegExp(`^Deploy of ${COMMIT} .* FAILED: deploy\\.sh exited 1\\.`));
  assert.ok(s.calls.report[0].text.includes(JSON.stringify(row)));
  assert.equal(fs.existsSync(s.file), false);
  assert.equal(deferred.step(s.deps()), 'none');
});

test('a launch that fails is reported at once and deploys nothing', (t) => {
  const s = scratch(t);
  s.ask();
  assert.equal(deferred.step(s.deps({ start: () => ({ ok: false, error: 'systemd-run exited 1' }) })), 'reported');
  assert.match(s.calls.report[0].text, /did not start: systemd-run exited 1\. Nothing was deployed\./);
  assert.equal(fs.existsSync(s.file), false);
});

test('a started deploy with no log line is reported after the limit', (t) => {
  const s = scratch(t);
  s.ask();
  deferred.step(s.deps({ now: 0 }));
  assert.equal(deferred.step(s.deps({ now: deferred.REPORT_LIMIT_MS })), 'started');
  assert.equal(deferred.step(s.deps({ now: deferred.REPORT_LIMIT_MS + 1 })), 'reported');
  assert.match(s.calls.report[0].text, /wrote no deploy log line in 10 minutes/);
});

test('a report that throws still closes the request, so it is not retried forever', (t) => {
  const s = scratch(t);
  s.ask();
  const logged = [];
  deferred.step(s.deps({ start: () => ({ ok: false, error: 'x' }), report() { throw new Error('store gone'); }, log: (row) => logged.push(row) }));
  assert.equal(fs.existsSync(s.file), false);
  assert.ok(logged.some((row) => /report failed: store gone/.test(row.message || '')));
});

test('the job runs ignite by absolute path with the service PATH and HOME, outside the service', () => {
  const [program, args] = deferred.startCommand(
    { commit: COMMIT, startedAt: 7, deployFolder: '/deploy' }, '/inst', { PATH: '/a:/b', HOME: '/home/h' }, '/home/h/.rbtv/bin/ignite');
  assert.equal(program, 'systemd-run');
  assert.deepEqual(args, ['--user', '--collect', `--unit=ignite-deploy-${COMMIT.slice(0, 12)}-7`, '--setenv=PATH=/a:/b', '--setenv=HOME=/home/h',
    '/home/h/.rbtv/bin/ignite', 'deploy', COMMIT, '--installation', '/inst', '--deploy-folder', '/deploy']);
});
