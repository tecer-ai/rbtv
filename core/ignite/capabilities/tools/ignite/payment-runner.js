'use strict';

// The waking service's side of the payment gate: it posts each pending request to its agent's thread,
// sends each approved request through its provider's tool, follows the sent operation, and tells the
// requesting conversation the outcome. No model takes part: the service runs the provider's tool with
// the ledger's exact fields.
//
// API
// createPaymentRunner({ gate, slack, store, providers, run?, env?, cwd, log?, kick?, now? }) → { step(), stop() }
//   gate — the Gate. slack() → the Slack client, or null. store(slug) → that agent's open Store, or null.
//   providers — the provider names Ignite may send through: those with a withdrawal validation
//   (payment-webhook.js), each also the name of its tool on PATH. kick(slug) asks the service to run
//   that agent's queue and outbox.
//   run(command, args, input) → Promise<{ code, stdout, stderr }>; by default the tool is started with
//   execFile, the request's JSON on stdin, env() as its environment and cwd the installation, for at
//   most 60 s.
//   step() → Promise that never rejects; a pass already running makes the call return at once. A pass:
//   1. posts each pending request without a message to its conversation's thread, with Approve and Refuse;
//   2. sends each approved request not yet claimed: claims it (once only), runs
//      `<provider> --json pay execute <id>` with the request (payments.js publicRow) as JSON on stdin,
//      and records sent, with the provider's id, status and receipt, or failed with the tool's reason;
//   3. reads each sent operation with `<provider> --json pay status <id>` every 5 s, from 5 s after it
//      was sent for 10 minutes, until the tool calls it final; final and not ok fails the request;
//   4. updates each request message whose state changed: the buttons go once it is not pending;
//   5. tells the requesting conversation each outcome once (refused by the owner, failed, sent and final
//      or sent 10 minutes ago): a wake with the outcome as its note, or, when its work does not wait
//      for workers, a system message posted in its thread.
//   A Slack call that fails is retried after 30 s.
//   stop() → Promise settled when the pass in flight ends; no pass starts after it.

const { execFile } = require('node:child_process');
const { brl, publicRow } = require('./payments.js');
const { promptBlocks, promptText } = require('./payment-panel.js');

const RUN_MS = 60_000;
const RETRY_MS = 30_000;

function defaultRun({ env, cwd }) {
  return (command, args, input) => new Promise((resolve) => {
    const child = execFile(command, args, { env: env(), cwd, timeout: RUN_MS, maxBuffer: 1024 * 1024, windowsHide: true },
      (error, stdout, stderr) => {
        const code = error ? (typeof error.code === 'number' ? error.code : 1) : 0;
        resolve({ code, stdout: String(stdout || ''), stderr: String(stderr || error?.message || '') });
      });
    child.stdin.on('error', () => {});
    child.stdin.end(input);
  });
}

function firstJson(stdout) {
  try { return JSON.parse(String(stdout).trim().split('\n').pop()); } catch { return null; }
}

function reasonOf(result) {
  const text = String(result.stderr || result.stdout || '').trim().split('\n').slice(0, 3).join(' ').replace(/\s+/g, ' ');
  return (text || `exit ${result.code}`).slice(0, 300);
}

function keyLabel(method) {
  if (method === 'pix') return 'Pix key';
  if (method === 'bill') return 'bill line';
  return 'recipient';
}

function outcomeText(row) {
  const to = `${brl(row.amount_cents + row.fee_cents)} to ${row.recipient_name || row.recipient_key} (${keyLabel(row.method)} ${row.recipient_key})`;
  if (row.state === 'sent') {
    const receipt = row.receipt_url ? `receipt ${row.receipt_url}` : 'no receipt yet';
    return `Payment ${row.id} sent: ${to}. ${row.provider} id ${row.provider_id}, status ${row.provider_status || 'unknown'}, ${receipt}.`;
  }
  if (row.state === 'refused') return `Payment ${row.id} was refused by the owner: ${to}. Nothing was sent.`;
  return `Payment ${row.id} failed: ${to}. ${row.reason}`;
}

function createPaymentRunner({ gate, slack, store, providers, run = null, env = () => process.env, cwd, log = () => {}, kick = () => {}, now = Date.now } = {}) {
  const allowed = new Set(providers || []);
  const launch = run || defaultRun({ env, cwd });
  const nextTry = new Map();
  let running = null;
  let halted = false;

  function note(fields) {
    try { log({ event: 'payments', ...fields }); } catch { /* the runner never fails on a log */ }
  }

  function due(key) {
    return (nextTry.get(key) || 0) <= now();
  }

  function later(key, error, fields) {
    nextTry.set(key, now() + RETRY_MS);
    note({ ...fields, message: error.message });
  }

  function conversationOf(row) {
    try { return store(row.agent)?.getConversation(row.conversation_key) || null; } catch { return null; }
  }

  async function postPrompts(rows) {
    const client = slack();
    if (!client?.postBlocks) return;
    for (const row of rows) {
      if (halted || !due(`prompt:${row.id}`)) continue;
      const conv = conversationOf(row);
      if (!conv?.channel) {
        gate.promptPosted(row.id, { channel: null, ts: '-' });
        note({ action: 'prompt-skipped', id: row.id, reason: 'conversation not found; the request is in /payments' });
        continue;
      }
      try {
        const posted = await client.postBlocks({
          channel: conv.channel, threadTs: conv.root_ts || undefined, text: promptText(row), blocks: promptBlocks(row),
        });
        gate.promptPosted(row.id, { channel: posted.channel, ts: posted.ts });
        note({ action: 'prompt', id: row.id });
      } catch (error) {
        later(`prompt:${row.id}`, error, { action: 'prompt-failed', id: row.id });
      }
    }
  }

  async function send(row) {
    if (!allowed.has(row.provider)) {
      gate.failed(row.id, `Ignite does not send through ${row.provider}: it has no withdrawal validation for it`);
      return;
    }
    if (!gate.claim(row.id)) return;
    const input = JSON.stringify(publicRow(gate.get(row.id)));
    note({ action: 'send', id: row.id, provider: row.provider });
    let result;
    try {
      result = await launch(row.provider, ['--json', 'pay', 'execute', row.id], input);
    } catch (error) {
      result = { code: 1, stdout: '', stderr: error.message };
    }
    const body = result.code === 0 ? firstJson(result.stdout) : null;
    if (body?.provider_id) {
      gate.sent(row.id, { providerId: body.provider_id, providerStatus: body.status || null, receiptUrl: body.receipt_url || null });
      note({ action: 'sent', id: row.id, providerId: String(body.provider_id) });
    } else {
      const reason = result.code === 0 ? 'the provider tool returned no operation id' : reasonOf(result);
      gate.failed(row.id, reason);
      note({ action: 'send-failed', id: row.id, reason });
    }
  }

  async function check(row) {
    if (!allowed.has(row.provider)) return;
    let result;
    try {
      result = await launch(row.provider, ['--json', 'pay', 'status', row.id], JSON.stringify(publicRow(row)));
    } catch (error) {
      result = { code: 1, stdout: '', stderr: error.message };
    }
    const body = result.code === 0 ? firstJson(result.stdout) : null;
    if (!body) {
      gate.checked(row.id, {});
      note({ action: 'check-failed', id: row.id, reason: reasonOf(result) });
      return;
    }
    gate.checked(row.id, {
      providerStatus: body.status || null, receiptUrl: body.receipt_url || null,
      final: Boolean(body.final), ok: body.ok !== false, reason: body.reason || null,
    });
  }

  async function showStates(rows) {
    const client = slack();
    if (!client?.updateMessage) return;
    for (const row of rows) {
      if (halted || !due(`show:${row.id}`) || row.prompt_ts === '-') continue;
      try {
        await client.updateMessage({ channel: row.prompt_channel, ts: row.prompt_ts, text: promptText(row), blocks: promptBlocks(row) });
        gate.promptShown(row.id, row.state);
      } catch (error) {
        later(`show:${row.id}`, error, { action: 'prompt-update-failed', id: row.id });
      }
    }
  }

  function tell(row) {
    const text = outcomeText(row);
    const agentStore = store(row.agent);
    if (!agentStore) {
      gate.notified(row.id, `${row.state}:lost`);
      note({ action: 'notify-lost', id: row.id, reason: `agent ${row.agent} has no store` });
      return;
    }
    try {
      const woke = agentStore.wake({ conversationKey: row.conversation_key, note: text });
      if (!woke.inserted) {
        agentStore.enqueueOutbox({
          id: `post:payment:${row.id}:${row.state}`,
          conversationKey: row.conversation_key,
          payload: { text: `System message: ${text}`, audio: false, files: [] },
        });
      }
      gate.notified(row.id, row.state);
      note({ action: 'notify', id: row.id, state: row.state, woke: Boolean(woke.inserted) });
    } catch (error) {
      gate.notified(row.id, `${row.state}:lost`);
      note({ action: 'notify-lost', id: row.id, reason: error.message });
    }
    kick(row.agent);
  }

  async function pass() {
    try {
      const work = gate.due({ now: now() });
      await postPrompts(work.prompts);
      for (const row of work.toSend) {
        if (halted) return;
        await send(row);
      }
      for (const row of work.toCheck) {
        if (halted) return;
        await check(row);
      }
      if (halted) return;
      const after = gate.due({ now: now() });
      await showStates(after.unshown);
      for (const row of after.toNotify) tell(row);
    } catch (error) {
      note({ action: 'pass-failed', message: error.message });
    }
  }

  function step() {
    if (halted || running) return Promise.resolve();
    running = pass().finally(() => { running = null; });
    return running;
  }

  function stop() {
    halted = true;
    return running || Promise.resolve();
  }

  return { step, stop };
}

module.exports = { createPaymentRunner, outcomeText };
