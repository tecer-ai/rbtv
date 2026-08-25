'use strict';

// probe-watchdog-alarm-transport — THE SEAM `tool/watchdog-alarm.js` LEFT OPEN.
//
// The shim shipped with `resolveSend()` returning a refusal by design: "the Slack transport is the
// chat bridge's to wire, so watchdog alarms currently stop at a `pending-delivery` record". That
// record is durable [C-17] and it is not a lost alarm — but it is also not an alarm the owner ever
// SEES. This probe measures the wiring that closes it, and the two walls that keep it honest:
//
//   1. WITH a bot token, the alarm reaches the transport and the outbox flips to `delivered` on
//      Slack's own ack, carrying the ts Slack answered with.
//   2. WITHOUT one, the record is minted `pending-delivery` with the reason ON THE ROW — the
//      behaviour every existing watchdog probe asserts, unchanged.
//   3. WITH `RBTV_WATCHDOG_NOTIFY_FILE` set — this tool's "send nothing" sink — NOTHING is sent
//      even if a token is present. The wall is checked BEFORE the token, exactly as
//      `deadman_ping()` checks it before the URL: a rehearsal that reached real Slack because the
//      shell carried a token would post to the owner's workspace from a test.
//
// Mock Slack: a loopback HTTP server on an EPHEMERAL port, pointed at by `SLACK_API_BASE`. No
// systemd unit is read or touched, no real endpoint is contacted, and the live outbox is never
// opened — every run gets its own scratch workspace.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

const OUT = path.join(__dirname, 'probe-watchdog-alarm-transport.out');
const SHIM = path.join(__dirname, '..', 'tool', 'watchdog-alarm.js');
const SYS = 'Csystem';

const checks = [];
function check(name, pass, evidence = {}) {
  checks.push({ name, pass: !!pass, evidence });
}

function observation() {
  return {
    condition: 'the daemon unit did not read determinately running for 3 consecutive passes',
    subject: { type: 'daemon', id: 'ignite-daemon.service' },
    evidence_pointer: '/w/.rbtv/runtime/watchdog/outage-ledger.jsonl',
    what_would_clear_it: 'the unit reading determinately running again',
    signature_class: 'watchdog-daemon-unhealthy',
    immediate: true,
  };
}

function startMockSlack() {
  const seen = [];
  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => { body += c; });
    req.on('end', () => {
      seen.push({ url: req.url, body: (() => { try { return JSON.parse(body); } catch { return body; } })() });
      res.setHeader('content-type', 'application/json');
      res.end(JSON.stringify({ ok: true, ts: '1724500000.000100' }));
    });
  });
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => resolve({
      seen,
      base: `http://127.0.0.1:${server.address().port}`,
      close: () => new Promise((done) => server.close(done)),
    }));
  });
}

function runShim(input, env) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [SHIM], {
      env: { ...env },
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (c) => { stdout += c; });
    child.stderr.on('data', (c) => { stderr += c; });
    child.on('close', (code) => {
      let doc = null;
      try { doc = JSON.parse(stdout.trim().split('\n').pop()); } catch { /* reported as null */ }
      resolve({ code, stdout, stderr, doc });
    });
    child.stdin.end(JSON.stringify(input));
  });
}

function outboxRecords(workspaceRoot) {
  try {
    return JSON.parse(fs.readFileSync(
      path.join(workspaceRoot, '.rbtv', 'runtime', 'ignite', 'outbox.json'), 'utf8',
    )).records;
  } catch {
    return [];
  }
}

// The shim inherits nothing it was not given: every leg starts from a clean environment so an
// ambient SLACK_* in the operator's shell cannot decide what this probe measures.
function baseEnv(workspaceRoot, extra = {}) {
  return {
    PATH: process.env.PATH,
    HOME: process.env.HOME,
    RBTV_SYSTEM_CHANNEL_ID: SYS,
    RBTV_WATCHDOG_WORKSPACE: workspaceRoot,
    ...extra,
  };
}

(async () => {
  const t0 = Date.now();
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'wd-alarm-transport-'));
  const slack = await startMockSlack();

  // ── 1. WIRED: the alarm reaches Slack and the record flips to delivered ─────────────────────
  {
    const ws = path.join(root, 'wired');
    const r = await runShim({ ...observation(), workspace_root: ws }, baseEnv(ws, {
      SLACK_BOT_TOKEN: 'xoxb-probe',
      SLACK_API_BASE: slack.base,
    }));
    const records = outboxRecords(ws);
    const post = slack.seen.find((s) => /chat\.postMessage$/.test(s.url));
    check('the shim exits 0 and reports the emission', r.code === 0 && r.doc && r.doc.ok === true && r.doc.posted === true,
      { code: r.code, doc: r.doc, stderr: r.stderr.slice(0, 400) });
    check('the alarm REACHED the transport — one chat.postMessage, in the system channel [T5-R1]',
      Boolean(post) && post.body.channel === SYS && /ignite-daemon\.service/.test(post.body.text),
      { post: post && post.body });
    check('the durable record is DELIVERED, carrying the ts Slack answered with [C-17]',
      records.length === 1 && records[0].state === 'delivered' && records[0].slack_ts === '1724500000.000100'
        && r.doc.delivered === true,
      { record: records[0] });
    check('the post is stamped `alarm` by the EMITTER, never by this caller',
      records.length === 1 && records[0].kind === 'alarm', { kind: records[0] && records[0].kind });
  }

  // ── 2. UNWIRED: no token is a durable pending-delivery record with the reason on it ─────────
  {
    const ws = path.join(root, 'no-token');
    const before = slack.seen.length;
    const r = await runShim({ ...observation(), workspace_root: ws }, baseEnv(ws, { SLACK_API_BASE: slack.base }));
    const records = outboxRecords(ws);
    check('with no bot token the shim STILL exits 0 and still mints the record — an unwired transport is not a lost alarm',
      r.code === 0 && r.doc && r.doc.ok === true && records.length === 1, { code: r.code, doc: r.doc });
    check('the record is pending-delivery and names WHY it was not delivered',
      records.length === 1 && records[0].state === 'pending-delivery'
        && /SLACK_BOT_TOKEN/.test(records[0].last_error || ''),
      { record: records[0] });
    check('and nothing was sent', slack.seen.length === before, { calls: slack.seen.length - before });
  }

  // ── 3. THE DRY WALL BEATS THE TOKEN ─────────────────────────────────────────────────────────
  {
    const ws = path.join(root, 'dry');
    const before = slack.seen.length;
    const r = await runShim({ ...observation(), workspace_root: ws }, baseEnv(ws, {
      SLACK_BOT_TOKEN: 'xoxb-probe',
      SLACK_API_BASE: slack.base,
      RBTV_WATCHDOG_NOTIFY_FILE: path.join(ws, 'notify.jsonl'),
    }));
    const records = outboxRecords(ws);
    check('with the "send nothing" sink set, a PRESENT token sends nothing — the wall is checked before the token',
      slack.seen.length === before && records.length === 1 && records[0].state === 'pending-delivery',
      { calls: slack.seen.length - before, record: records[0] });
    check('and the reason names the sink rather than the missing token',
      records.length === 1 && /RBTV_WATCHDOG_NOTIFY_FILE/.test(records[0].last_error || ''),
      { last_error: records[0] && records[0].last_error, doc: r.doc });
  }

  // ── 4. THE REFUSALS THE SHIM ALREADY CARRIED STILL STAND ────────────────────────────────────
  {
    const ws = path.join(root, 'no-channel');
    const env = baseEnv(ws, { SLACK_BOT_TOKEN: 'xoxb-probe', SLACK_API_BASE: slack.base });
    delete env.RBTV_SYSTEM_CHANNEL_ID;
    const before = slack.seen.length;
    const r = await runShim({ ...observation(), workspace_root: ws }, env);
    check('no system channel is still a LOUD refusal, exit 1, nothing posted and nothing minted',
      r.code === 1 && r.doc && r.doc.ok === false && /RBTV_SYSTEM_CHANNEL_ID/.test(r.doc.error)
        && outboxRecords(ws).length === 0 && slack.seen.length === before,
      { code: r.code, doc: r.doc });

    const ws2 = path.join(root, 'bad-alarm');
    const half = observation();
    delete half.what_would_clear_it;
    const r2 = await runShim({ ...half, workspace_root: ws2 }, baseEnv(ws2, {
      SLACK_BOT_TOKEN: 'xoxb-probe', SLACK_API_BASE: slack.base,
    }));
    check('a half-composed alarm is still refused by the emitter — a wired transport did not weaken the schema gate [T4-R10]',
      r2.code === 1 && r2.doc && r2.doc.ok === false && /what_would_clear_it/.test(r2.doc.error)
        && outboxRecords(ws2).length === 0,
      { code: r2.code, doc: r2.doc });
  }

  await slack.close();
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* tmp */ }

  const pass = checks.every((c) => c.pass);
  const wallMs = Date.now() - t0;
  const exit = pass ? 0 : 1;
  fs.writeFileSync(OUT, `${JSON.stringify({
    summary: {
      probe: 'probe-watchdog-alarm-transport',
      pass,
      checks: checks.length,
      failed: checks.filter((c) => !c.pass).map((c) => c.name),
      EXIT: exit,
      WALL_MS: wallMs,
      SKIPPED_COUNT: 0,
    },
    entries: checks,
  }, null, 2)}\n`);
  process.stdout.write(`PROBE probe-watchdog-alarm-transport EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
  if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
  process.exit(exit);
})().catch((err) => {
  process.stdout.write(`PROBE probe-watchdog-alarm-transport EXIT=1 THREW ${err.stack}\n`);
  process.exit(1);
});
