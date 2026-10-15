'use strict';

// The waking service's side of the payment gate: it resolves each pending request's recipient through its
// provider and posts it to its agent's thread, sends each approved request through its provider's tool,
// follows the sent operation, reconciles a send whose outcome was lost, and tells the requesting
// conversation the outcome. No model takes part: the service runs the provider's tool with the ledger's
// exact fields.
//
// API
// createPaymentRunner({ gate, slack, store, providers, run?, env?, cwd, log?, kick?, now? }) → { step(), stop() }
//   gate — the Gate. slack() → the Slack client, or null. store(slug) → that agent's open Store, or null.
//   providers — the provider names Ignite may send through: those with a withdrawal validation adapter
//   (payment-webhook.js loadProvider), each also the name of its tool on PATH. kick(slug) asks the service to
//   run that agent's queue and outbox.
//   run(command, args, input) → Promise<{ code, stdout, stderr }>; by default the tool is started with
//   execFile, the request's JSON on stdin, env() as its environment and cwd the installation, for at
//   most 60 s.
//   step() → Promise that never rejects; a pass already running makes the call return at once. A pass:
//   1. resolves each pending request: `<provider> --json pay resolve <id>` with the request (payments.js
//      publicRow) on stdin gives the recipient as the bank names it, recorded with gate.resolved (a key, amount
//      or fee that differs refuses the request); after 3 failed tries 30 s apart, gate.resolveFailed;
//   2. posts each pending request resolved or failed and without a message to its conversation's thread, with
//      Approve and Refuse, or Refuse alone when the resolution failed (payment-panel.js promptBlocks);
//   3. sends each approved request not yet claimed: claims it (once only), runs `<provider> --json pay execute <id>`
//      with the request on stdin, and records sent, with the provider's id, status and receipt; failed only when
//      the tool answers {"created": false} (the bank refused it, or it was never called); otherwise (a timeout,
//      a crash, no operation id) uncertain, which keeps counting toward the limits. A request the owner approved
//      while its recipient was unchecked (payments.js unchecked; a ledger of an earlier release can hold one) is
//      never run: it fails;
//   4. reads each sent operation with `<provider> --json pay status <id>` every 5 s, from 5 s after it was sent for
//      10 minutes, until the tool calls it final; final and not ok fails the request;
//   5. reconciles each uncertain request with an operation id (its own, or the one the withdrawal validation
//      approved) with `pay status` every 60 s: found, it becomes sent, or failed when final and not ok;
//   6. updates each request message whose state changed: the buttons go once it is not pending;
//   7. tells the requesting conversation each outcome once per state (refused by the owner or by Ignite's
//      check, failed, uncertain, sent and final or sent 10 minutes ago): a wake with the outcome as its note,
//      or, when its work does not wait for workers, a system message posted in its thread.
//   A Slack call that fails is retried after 30 s.
//   stop() → Promise settled when the pass in flight ends; no pass starts after it.
// outcomeText(gate, row) → the note an outcome wakes the conversation with.

const { execFile } = require('node:child_process');
const { publicRow, unchecked } = require('./payments.js');
const { promptBlocks, promptText } = require('./payment-panel.js');

const RUN_MS = 60_000;
const RETRY_MS = 30_000;
const RESOLVE_TRIES = 3;

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

function lastJson(stdout) {
  try { return JSON.parse(String(stdout).trim().split('\n').pop()); } catch { return null; }
}

function reasonOf(result) {
  const text = String(result.stderr || result.stdout || '').trim().split('\n').slice(0, 3).join(' ').replace(/\s+/g, ' ');
  return (text || `exit ${result.code}`).slice(0, 300);
}

function keyLabel(method) {
  if (method === 'pix') return 'Pix key';
  if (method === 'bill') return 'bill line';
  if (method === 'qr') return 'QR code';
  if (method === 'recharge') return 'phone';
  return 'recipient';
}

function outcomeText(gate, row) {
  const name = row.resolved_name || row.recipient_name || row.recipient_key;
  const to = `${gate.money(row.amount_cents + row.fee_cents)} to ${name} (${keyLabel(row.method)} ${row.recipient_key})`;
  if (row.state === 'sent') {
    const receipt = row.receipt_url ? `receipt ${row.receipt_url}` : 'no receipt yet';
    return `Payment ${row.id} sent: ${to}. ${row.provider} id ${row.provider_id}, status ${row.provider_status || 'unknown'}, ${receipt}.`;
  }
  if (row.state === 'refused') {
    if (row.decided_by === 'owner') return `Payment ${row.id} was refused by the owner: ${to}. Nothing was sent.`;
    return `Payment ${row.id} was refused: ${to}. ${row.reason}. Nothing was sent.`;
  }
  if (row.state === 'uncertain') {
    return `Payment ${row.id} may have been paid: ${to}. ${row.reason}. It counts toward the limits until Ignite reads it at ${row.provider}; this conversation hears the outcome. Do not ask again before checking the statement.`;
  }
  return `Payment ${row.id} failed: ${to}. ${row.reason}`;
}

function createPaymentRunner({ gate, slack, store, providers, run = null, env = () => process.env, cwd, log = () => {}, kick = () => {}, now = Date.now } = {}) {
  const allowed = new Set(providers || []);
  const launch = run || defaultRun({ env, cwd });
  const nextTry = new Map();
  const resolveTries = new Map();
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

  async function tool(row, verb, input = publicRow(row)) {
    try {
      return await launch(row.provider, ['--json', 'pay', verb, row.id], JSON.stringify(input));
    } catch (error) {
      return { code: 1, stdout: '', stderr: error.message };
    }
  }

  async function resolve(row) {
    if (!due(`resolve:${row.id}`)) return;
    if (!allowed.has(row.provider)) {
      gate.resolveFailed(row.id, `Ignite does not send through ${row.provider}: it has no withdrawal validation for it`);
      return;
    }
    const result = await tool(row, 'resolve');
    const body = result.code === 0 ? lastJson(result.stdout) : null;
    if (body && typeof body === 'object') {
      const { row: after } = gate.resolved(row.id, {
        name: body.name, document: body.document, bank: body.bank, key: body.key, keyType: body.key_type,
        amountCents: body.amount_cents, feeCents: body.fee_cents,
      });
      note({ action: 'resolved', id: row.id, state: after?.state || null });
      return;
    }
    const tries = (resolveTries.get(row.id) || 0) + 1;
    resolveTries.set(row.id, tries);
    const reason = reasonOf(result);
    if (tries >= RESOLVE_TRIES) {
      gate.resolveFailed(row.id, reason);
      note({ action: 'resolve-failed', id: row.id, reason });
    } else {
      later(`resolve:${row.id}`, new Error(reason), { action: 'resolve-retry', id: row.id });
    }
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
          channel: conv.channel, threadTs: conv.root_ts || undefined, text: promptText(gate, row), blocks: promptBlocks(gate, row),
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
    const why = unchecked(row);
    if (why) {
      gate.failed(row.id, `Not sent, because it was approved before Ignite had checked it: ${why}`);
      note({ action: 'send-refused', id: row.id, reason: why });
      return;
    }
    if (!gate.claim(row.id)) return;
    note({ action: 'send', id: row.id, provider: row.provider });
    const result = await tool(row, 'execute', publicRow(gate.get(row.id)));
    const body = lastJson(result.stdout);
    if (result.code === 0 && body?.provider_id) {
      gate.sent(row.id, { providerId: body.provider_id, providerStatus: body.status || null, receiptUrl: body.receipt_url || null });
      note({ action: 'sent', id: row.id, providerId: String(body.provider_id) });
    } else if (body?.created === false) {
      const reason = body.reason ? String(body.reason).slice(0, 300) : reasonOf(result);
      const { row: after } = gate.failed(row.id, reason);
      note({ action: 'send-failed', id: row.id, state: after?.state || null, reason });
    } else {
      const why = result.code === 0 ? `${row.provider} returned no operation id` : reasonOf(result);
      gate.uncertain(row.id, `Ignite does not know whether ${row.provider} made it: ${why}`);
      note({ action: 'send-uncertain', id: row.id, reason: why });
    }
  }

  async function check(row) {
    if (!allowed.has(row.provider)) return;
    const result = await tool(row, 'status');
    const body = result.code === 0 ? lastJson(result.stdout) : null;
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

  async function reconcile(row) {
    if (!allowed.has(row.provider)) return;
    const operation = row.provider_id || row.answered_operation;
    const result = await tool(row, 'status', { ...publicRow(row), provider_id: operation });
    const body = result.code === 0 ? lastJson(result.stdout) : null;
    if (!body?.status) {
      gate.reconciled(row.id, { found: false });
      note({ action: 'reconcile-failed', id: row.id, reason: reasonOf(result) });
      return;
    }
    const { row: after } = gate.reconciled(row.id, {
      found: true, providerId: operation, providerStatus: body.status, receiptUrl: body.receipt_url || null,
      final: Boolean(body.final), ok: body.ok !== false, reason: body.reason || null,
    });
    note({ action: 'reconciled', id: row.id, state: after?.state || null, providerStatus: body.status });
  }

  async function showStates(rows) {
    const client = slack();
    if (!client?.updateMessage) return;
    for (const row of rows) {
      if (halted || !due(`show:${row.id}`) || row.prompt_ts === '-') continue;
      try {
        await client.updateMessage({ channel: row.prompt_channel, ts: row.prompt_ts, text: promptText(gate, row), blocks: promptBlocks(gate, row) });
        gate.promptShown(row.id, row.state);
      } catch (error) {
        later(`show:${row.id}`, error, { action: 'prompt-update-failed', id: row.id });
      }
    }
  }

  function tell(row) {
    const text = outcomeText(gate, row);
    const agentStore = store(row.agent);
    if (!agentStore) {
      gate.notified(row.id, row.state);
      note({ action: 'notify-lost', id: row.id, state: row.state, reason: `agent ${row.agent} has no store` });
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
      gate.notified(row.id, row.state);
      note({ action: 'notify-lost', id: row.id, state: row.state, reason: error.message });
    }
    kick(row.agent);
  }

  async function pass() {
    try {
      const work = gate.due({ now: now() });
      for (const row of work.resolve) {
        if (halted) return;
        await resolve(row);
      }
      await postPrompts(gate.due({ now: now() }).prompts);
      for (const row of work.toSend) {
        if (halted) return;
        await send(row);
      }
      for (const row of work.toCheck) {
        if (halted) return;
        await check(row);
      }
      for (const row of work.toReconcile) {
        if (halted) return;
        await reconcile(row);
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
