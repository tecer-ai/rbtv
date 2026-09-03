'use strict';

// Red-first proof for `d-broker-midrun-alert` (ruled §10b of `cred-account-shape-design.md`): a
// mid-run credential-mint failure ALSO escalates into the daemon's existing alarm/report
// vocabulary — `bus-ferry.js#scanCredentialBrokerLog`, reusing the SAME `postOwner({kind:'alarm'})`
// surface `postUnreachableChannelAlarm` already posts to the system channel, never a new one. A
// DISCRIMINATING CONTROL: a forced failure raises the alarm; a successful mint, in the SAME log,
// raises none. Fixture workspace only — no real goal, no real broker, no real Slack.

const fs = require('node:fs');
const path = require('node:path');
const { createBusFerry } = require('../bus-ferry');

const outPath = path.join(__dirname, 'probe-chat-credential-broker-alarm.out');
fs.writeFileSync(outPath, '');
function out(line) { fs.appendFileSync(outPath, `${line}\n`); }
const checks = [];
function check(name, pass, detail) {
  checks.push(pass);
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`);
}

function mkdirp(p) { fs.mkdirSync(p, { recursive: true }); }

function mkroot() {
  return fs.mkdtempSync(path.join('/var/tmp', 'chat-cba-'));
}

function seedGoal(root, goalId) {
  const goalDir = path.join(root, '.rbtv', 'goals', goalId);
  mkdirp(path.join(goalDir, 'coordination')); // goalBuses() requires this to discover the goal
  mkdirp(path.join(goalDir, 'scratch'));
  return { goalDir, logFile: path.join(goalDir, 'scratch', 'credential-broker.log') };
}

function appendAuditLine(logFile, fields) {
  fs.appendFileSync(logFile, `${JSON.stringify({ ts: new Date().toISOString(), ...fields })}\n`);
}

async function main() {
  out('COMMAND: node ignite/chat/probes/probe-chat-credential-broker-alarm.js');
  out('evidence-class: FIXTURE /var/tmp workspace + fixture transport; REAL createBusFerry/scanCredentialBrokerLog');

  const root = mkroot();
  const { goalDir, logFile } = seedGoal(root, 'test-cba-goal');
  const systemPosted = [];
  const transport = {
    async openDm() { return { ok: true, channel: 'D_OWNER' }; },
    async sendToOwner({ channel, threadTs, text }) {
      if (channel === 'C_SYSTEM') systemPosted.push({ channel, threadTs, text });
      return { delivered: true, ts: String(systemPosted.length) };
    },
  };
  const ferry = createBusFerry({
    workspaceRoot: root, transport, dmUserId: 'U_OWNER', pollMs: 3600000, systemChannelId: 'C_SYSTEM',
  });
  const started = await ferry.start();
  check('SETUP the fixture ferry starts (dmUserId + transport.openDm wired)', started && started.enabled === true, JSON.stringify(started));

  // ── CONTROL — a SUCCESSFUL mint, alone, raises no alarm ───────────────────────────────────
  appendAuditLine(logFile, { op: 'mint', account: 'fixture-acct', ok: true });
  await ferry.tick();
  check(
    'CONTROL a successful mint raises no alarm',
    systemPosted.length === 0,
    `posted=${JSON.stringify(systemPosted)}`,
  );

  // ── RED-then-GREEN — a FAILED mint DOES raise the alarm, on the system channel, once ──────
  appendAuditLine(logFile, { op: 'mint', account: 'fixture-acct', ok: false, reason: 'forced failure for this probe' });
  await ferry.tick();
  check(
    'GREEN a forced mint failure raises exactly one alarm on the system channel, naming the goal and the account',
    systemPosted.length === 1 && systemPosted[0].channel === 'C_SYSTEM'
      && systemPosted[0].text.includes('test-cba-goal') && systemPosted[0].text.includes('fixture-acct')
      && systemPosted[0].text.includes('forced failure for this probe'),
    `posted=${JSON.stringify(systemPosted)}`,
  );

  // ── NO DOUBLE-FIRE — a later pass with no new log line does not re-alarm ─────────────────
  await ferry.tick();
  check('NO-REFIRE a later pass with no new log line does not alarm again', systemPosted.length === 1, `posted=${systemPosted.length}`);

  // ── AUDIT — the durable per-goal record survives independently of the alarm ──────────────
  const auditLines = fs.readFileSync(logFile, 'utf8').split('\n').filter(Boolean);
  check('AUDIT the durable record carries both attempts regardless of alarm delivery', auditLines.length === 2, `lines=${auditLines.length}`);

  // ── A SECOND FAILURE on a DIFFERENT account fires a SECOND, distinct alarm ────────────────
  appendAuditLine(logFile, { op: 'mint', account: 'other-acct', ok: false, reason: 'second forced failure' });
  await ferry.tick();
  check(
    'SECOND FAILURE a later, distinct failure raises a second alarm naming the new account',
    systemPosted.length === 2 && systemPosted[1].text.includes('other-acct'),
    `posted=${JSON.stringify(systemPosted)}`,
  );

  ferry.stop();
  try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  const failed = checks.filter((p) => !p).length;
  out(failed === 0 ? 'ALL LEGS PASS' : `FAILED ${failed}/${checks.length}`);
  process.exit(failed === 0 ? 0 : 1);
}

main().catch((err) => {
  out(`FATAL ${err && err.stack}`);
  process.exit(1);
});
