#!/usr/bin/env node
'use strict';

// -- THE WATCHDOG'S ROUTE TO THE ONE ALARM EMITTER [T4-R9, T4-R10, C-17] -----------------------
//
// WHY THIS FILE EXISTS AT ALL. The watchdog is Python (stdlib only, deliberately — it has to run
// when everything else is down) and the ONE alarm emitter is JavaScript
// (`ignite/observation/emitter.js`). Python cannot `require` it. Rather than mint a second emitter
// in Python — which is exactly the "alarms composed at whatever call site noticed the condition"
// defect the emitter exists to end — the watchdog shells out to this shim and is an ORDINARY
// CALLER of the landed module. Nothing about the alarm is decided here: this file marshals one
// finished observation from stdin into `emit()` and prints what the emitter answered.
//
// ⚠ THIS SHIM LIVES IN THE WATCHDOG'S OWN TREE, NOT IN `observation/`. The emitter module is a
// wall: it is consumed, never extended. A caller that needs a different process to reach it owns
// its own bridge to it.
//
// The transport. `send` is the Slack transport and it is NOT WIRED YET (the chat bridge owns it).
// An unwired transport is not a lost alarm: `createOutbox` mints the record FIRST and only flips
// it to `delivered` on Slack's own ack, so an absent transport leaves a queryable
// `pending-delivery` row — which is precisely the C-17 durability the outbox exists for. When the
// bridge lands its sender, `resolveSend()` is the one place that changes.
//
// stdin: one JSON object — the emitter's own input shape (condition, subject, evidence_pointer,
//        what_would_clear_it, signature_class, immediate, …) plus an optional `workspace_root`.
// stdout: one JSON object — { ok, posted, reason, signature, outbox_id, delivered } or { ok:false,
//        error }. Exit 0 when the emitter accepted the observation, 1 when it refused it.

const path = require('node:path');

const emitter = require(path.resolve(__dirname, '..', '..', '..', 'observation', 'emitter.js'));
const outbox = require(path.resolve(__dirname, '..', '..', '..', 'bridges', 'chat', 'outbox.js'));

function readStdin() {
  return new Promise((resolve, reject) => {
    let buf = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (c) => { buf += c; });
    process.stdin.on('end', () => resolve(buf));
    process.stdin.on('error', reject);
  });
}

// No hardcoded channel and no hardcoded workspace (repo law: per-instance inputs resolve at
// runtime). The watchdog passes its own workspace root through; the system channel is the one the
// daemon-level events already go to [T5-R1] and comes from the environment.
function resolveWorkspaceRoot(input) {
  return input.workspace_root || process.env.RBTV_WATCHDOG_WORKSPACE || process.cwd();
}

// The seam the chat bridge closes. Until then every post is minted and left `pending-delivery`,
// with the reason said out loud rather than reported as a delivery.
function resolveSend() {
  return async () => ({ delivered: false, error: 'slack transport not wired into the watchdog shim' });
}

async function main() {
  const raw = await readStdin();
  let input;
  try {
    input = JSON.parse(raw);
  } catch (err) {
    process.stdout.write(`${JSON.stringify({ ok: false, error: `stdin is not JSON: ${err.message}` })}\n`);
    return 1;
  }
  const workspaceRoot = resolveWorkspaceRoot(input);
  const systemChannelId = input.channel_id || process.env.RBTV_SYSTEM_CHANNEL_ID || null;
  if (!systemChannelId) {
    process.stdout.write(`${JSON.stringify({ ok: false, error: 'no system channel: set RBTV_SYSTEM_CHANNEL_ID or pass channel_id' })}\n`);
    return 1;
  }

  const box = outbox.createOutbox({
    storePath: outbox.outboxStorePath(workspaceRoot),
    send: resolveSend(),
  });
  const alarms = emitter.createAlarmEmitter({
    storePath: emitter.alarmRegistryPath(workspaceRoot),
    post: box.post,
    systemChannelId,
  });

  delete input.workspace_root;
  let result;
  try {
    result = await alarms.emit(input);
  } catch (err) {
    // The emitter throws on a missing required field, and that throw IS the contract: the
    // watchdog's own composition is the bug, so it must surface here rather than reach the owner
    // as a fragment.
    process.stdout.write(`${JSON.stringify({ ok: false, error: String(err && err.message ? err.message : err) })}\n`);
    return 1;
  }
  process.stdout.write(`${JSON.stringify({
    ok: true,
    posted: result.posted,
    reason: result.reason,
    signature: result.signature,
    outbox_id: result.outbox_id || null,
    delivered: Boolean(result.delivered),
  })}\n`);
  return 0;
}

main().then((code) => { process.exitCode = code; }, (err) => {
  process.stdout.write(`${JSON.stringify({ ok: false, error: String(err && err.message ? err.message : err) })}\n`);
  process.exitCode = 1;
});
