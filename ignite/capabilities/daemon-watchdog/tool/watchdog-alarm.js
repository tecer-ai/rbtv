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
// The transport. `send` is the chat bridge's OWN Slack sender, reached through the module that
// owns it (`bridges/chat/slack-socket-mode.js#sendToOwner`) — never a second `chat.postMessage`
// composed here. Without a bot token in the environment it stays unwired, and an unwired transport
// is not a lost alarm: `createOutbox` mints the record FIRST and only flips it to `delivered` on
// Slack's own ack, so an absent token leaves a queryable `pending-delivery` row — precisely the
// C-17 durability the outbox exists for.
//
// stdin: one JSON object — the emitter's own input shape (condition, subject, evidence_pointer,
//        what_would_clear_it, signature_class, immediate, …) plus an optional `workspace_root`.
// stdout: one JSON object — { ok, posted, reason, signature, outbox_id, delivered } or { ok:false,
//        error }. Exit 0 when the emitter accepted the observation, 1 when it refused it.

const path = require('node:path');

const emitter = require(path.resolve(__dirname, '..', '..', '..', 'observation', 'emitter.js'));
const outbox = require(path.resolve(__dirname, '..', '..', '..', 'bridges', 'chat', 'outbox.js'));
const { createSlackSocketMode } = require(path.resolve(__dirname, '..', '..', '..', 'bridges', 'chat', 'slack-socket-mode.js'));

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

// ONE LINE, BY THIS FILE'S OWN DESIGN: the transport is the bridge's, and this shim is a caller of
// it. `createSlackSocketMode` opens NOTHING until `start()` is called — `sendToOwner` is a single
// outbound `chat.postMessage` on the bot token — so this process never joins a Socket-Mode session
// it has no business holding, and the outbound-only property `probe-chat-outbound` proves is
// untouched.
//
// ⚠ NO TOKEN IS A REFUSAL, NEVER A SILENT DROP. The watchdog runs when everything else is down, so
// the branch where Slack cannot be reached at all is the ordinary one: the record is minted and
// left `pending-delivery` with the reason on the row, and the dead-man (whose signal is a MISSED
// ping) is the channel that still works when this one does not [spec-owner-io §8].
//
// ⚠ `onMessage` IS A NO-OP AND MUST STAY ONE. This shim is outbound-only; a callback here would be
// a second consumer of owner messages living outside the bridge that owns that path.
function resolveSend() {
  // ⚠ THE DRY WALL IS CHECKED BEFORE THE TOKEN, exactly as `deadman_ping()` checks it before the
  // URL and for the same reason. `RBTV_WATCHDOG_NOTIFY_FILE` is this tool's "send nothing, write
  // what you would have sent" sink; a probe or a rehearsal that reached real Slack because the
  // shell happened to carry a bot token would post to the owner's workspace from a test.
  if (process.env.RBTV_WATCHDOG_NOTIFY_FILE) {
    return async () => ({ delivered: false, error: 'RBTV_WATCHDOG_NOTIFY_FILE is set — this pass sends nothing; the alarm is minted pending-delivery' });
  }
  const botToken = process.env.SLACK_BOT_TOKEN || null;
  if (!botToken) {
    return async () => ({ delivered: false, error: 'SLACK_BOT_TOKEN unset — the alarm is minted pending-delivery, not delivered' });
  }
  const slack = createSlackSocketMode({
    botToken,
    apiBase: process.env.SLACK_API_BASE || undefined,
    onMessage: () => {},
    // The constructor REFUSES to build without a WebSocket implementation, because the bridge it
    // was written for opens one. This process never does — `start()` is never called — so it is
    // handed a stand-in that throws if anything ever tries. A watchdog that could not raise an
    // alarm because the runtime lacked a global `WebSocket` would be blind for a reason that has
    // nothing to do with the alarm path.
    WebSocketImpl: globalThis.WebSocket || function WebSocketNeverOpened() {
      throw new Error('the watchdog alarm shim never opens a Socket-Mode connection');
    },
  });
  return (args) => slack.sendToOwner(args);
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
