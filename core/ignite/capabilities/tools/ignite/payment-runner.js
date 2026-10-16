'use strict';

// The waking service's side of the payment gate: it resolves each pending request's recipient through its
// connector and posts it to its agent's thread, sends each approved request through its connector's command,
// follows the sent operation, reconciles a send whose outcome was lost, and tells the requesting
// conversation the outcome. No model takes part: the service runs the connector's command directly
// (`<connector> --json pay resolve|execute|status <id>`, the request on stdin) with the ledger's exact fields.
//
// API
// createPaymentRunner({ gate, slack, store, connectors, run?, env?, cwd, log?, kick?, now? }) → { step(), stop() }
//   gate — the Gate. slack() → the Slack client, or null. store(slug) → that agent's open Store, or null.
//   connectors — the connector names Ignite may send through: those with a withdrawal validation adapter
//   (payment-webhook.js loadConnector), each also the name of its command on PATH. kick(slug) asks the service to
//   run that agent's queue and outbox.
//   run(command, args, input) → Promise<{ code, stdout, stderr }>; by default the command is started with
//   execFile, the request's JSON on stdin, env() as its environment and cwd the installation, for at
//   most 60 s.
//   step() → Promise that never rejects; a pass already running makes the call return at once. A pass:
//   1. resolves each pending request: `<connector> --json pay resolve <id>` with the request (payments.js
//      publicRow) on stdin gives the recipient as the bank names it, recorded with gate.resolved (a key, amount
//      or fee that differs refuses the request); after 3 failed tries 30 s apart, gate.resolveFailed;
//   2. posts each pending request resolved or failed and without a message to its conversation's thread, with
//      Approve and Refuse, or Refuse alone when the resolution failed (payment-panel.js promptBlocks); a message
//      Slack took that the ledger could not record (it was busy) is recorded on a later pass, every 30 s, and never
//      posted again;
//   3. sends each approved request not yet claimed: claims it (once only), runs `<connector> --json pay execute <id>`
//      with the request on stdin, and records sent, with the connector's id (connector_id, or provider_id, its older spelling),
//      status and receipt; failed only when the command answers {"created": false} (the bank refused it, or it was never called) or the program could not be
//      started (Node refused the launch, at once or in its callback); otherwise (a timeout, a crash, no operation id)
//      uncertain, which keeps counting toward the limits. An outcome the ledger could not record (it was busy) is
//      recorded on a later pass, every 30 s, without running the tool again. A request the owner approved
//      while its recipient was unchecked (payments.js unchecked; a ledger of an earlier release can hold one) is
//      never run: it fails;
//   4. reads each sent operation with `<connector> --json pay status <id>` every 5 s for its first 10 minutes, then
//      every 60 s, until the command calls it final; final and not ok fails the request;
//   5. reconciles each uncertain request with an operation id (its own, or the one the withdrawal validation
//      approved) with `pay status` every 60 s: found, it becomes sent, or failed when final and not ok;
//   6. updates each request message whose state changed: the buttons go once it is not pending;
//   7. tells the requesting conversation each outcome once per state (refused by the owner or by Ignite's
//      check, failed, uncertain, sent and final or sent 10 minutes ago): a wake with the outcome as its note,
//      or, when its work takes no wake, a system message posted in its thread; a wake whose work stops taking
//      wakes before a turn takes it (the turn running then completes the work or waits for the owner) becomes
//      that post. The conversation is found under its newest key (store.js followConversation). The agent store
//      records the notice with its wake or post (store.js notify), so a retry never tells it twice; a try that
//      fails is retried every 30 s, and after 20 in one service run the outcome is marked told and logged as
//      notify-lost.
//   A Slack call that fails is retried after 30 s.
//   stop() → Promise settled when the pass in flight ends; no pass starts after it.
// outcomeText(gate, row) → the note an outcome wakes the conversation with.

const { execFile } = require('node:child_process');
const { publicRow, unchecked } = require('./payments.js');
const { promptBlocks, promptText } = require('./payment-panel.js');

const RUN_MS = 60_000;
const RETRY_MS = 30_000;
const RESOLVE_TRIES = 3;
// A request still unchecked this long after it was made fails at its next failed lookup, even after a restart.
const RESOLVE_FOR_MS = 10 * 60_000;
// An outcome the agent store keeps refusing is given up after this many tries, RETRY_MS apart (about 10 minutes).
const NOTIFY_TRIES = 20;

// A spawn error means the program never ran, so it cannot have made an operation.
function spawnError(error) {
  return Boolean(error && typeof error.syscall === 'string' && error.syscall.startsWith('spawn'));
}

function defaultRun({ env, cwd }) {
  return (command, args, input) => new Promise((resolve) => {
    let child;
    try {
      child = execFile(command, args, { env: env(), cwd, timeout: RUN_MS, maxBuffer: 1024 * 1024, windowsHide: true },
        (error, stdout, stderr) => {
          const code = error ? (typeof error.code === 'number' ? error.code : 1) : 0;
          resolve({ code, stdout: String(stdout || ''), stderr: String(stderr || error?.message || ''), notStarted: spawnError(error) });
        });
    } catch (error) {
      // Node throws, instead of calling back, the spawn errors it does not count as run-time ones (ENAMETOOLONG, E2BIG).
      resolve({ code: 1, stdout: '', stderr: String(error?.message || error), notStarted: spawnError(error) });
      return;
    }
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
    return `Payment ${row.id} sent: ${to}. ${row.connector} id ${row.connector_id}, status ${row.connector_status || 'unknown'}, ${receipt}.`;
  }
  if (row.state === 'refused') {
    if (row.decided_by === 'owner') return `Payment ${row.id} was refused by the owner: ${to}. Nothing was sent.`;
    return `Payment ${row.id} was refused: ${to}. ${row.reason}. Nothing was sent.`;
  }
  if (row.state === 'uncertain') {
    return `Payment ${row.id} may have been paid: ${to}. ${row.reason}. It counts toward the limits until Ignite reads it at ${row.connector}; this conversation hears the outcome. Do not ask again before checking the statement.`;
  }
  return `Payment ${row.id} failed: ${to}. ${row.reason}`;
}

function createPaymentRunner({ gate, slack, store, connectors, run = null, env = () => process.env, cwd, log = () => {}, kick = () => {}, now = Date.now } = {}) {
  const allowed = new Set(connectors || []);
  const launch = run || defaultRun({ env, cwd });
  const nextTry = new Map();
  const resolveTries = new Map();
  const notifyTries = new Map();
  const unrecorded = new Map();
  const unrecordedPrompts = new Map();
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
    try { return store(row.agent)?.followConversation(row.conversation_key) || null; } catch { return null; }
  }

  async function tool(row, verb, input = publicRow(row)) {
    try {
      return await launch(row.connector, ['--json', 'pay', verb, row.id], JSON.stringify(input));
    } catch (error) {
      return { code: 1, stdout: '', stderr: error.message };
    }
  }

  async function resolve(row) {
    if (!due(`resolve:${row.id}`)) return;
    if (!allowed.has(row.connector)) {
      gate.resolveFailed(row.id, `Ignite does not send through ${row.connector}: it has no withdrawal validation for it`);
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
    if (tries >= RESOLVE_TRIES || now() - row.created_at >= RESOLVE_FOR_MS) {
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
      if (halted || !due(`prompt:${row.id}`) || unrecordedPrompts.has(row.id)) continue;
      const conv = conversationOf(row);
      if (!conv?.channel) {
        gate.promptPosted(row.id, { channel: null, ts: '-' });
        note({ action: 'prompt-skipped', id: row.id, reason: 'conversation not found; the request is in /payments' });
        continue;
      }
      let posted;
      try {
        posted = await client.postBlocks({
          channel: conv.channel, threadTs: conv.root_ts || undefined, text: promptText(gate, row), blocks: promptBlocks(gate, row),
        });
      } catch (error) {
        later(`prompt:${row.id}`, error, { action: 'prompt-failed', id: row.id });
        continue;
      }
      recordPrompt(row.id, { channel: posted.channel, ts: posted.ts });
    }
  }

  // Records a message Slack took. A ledger that refuses the write (busy) keeps the message here, recorded again on a
  // later pass; it is never posted again, so the message that shows the buttons is the one later updated.
  function recordPrompt(id, message) {
    try {
      gate.promptPosted(id, message);
      unrecordedPrompts.delete(id);
      note({ action: 'prompt', id });
    } catch (error) {
      unrecordedPrompts.set(id, message);
      later(`prompt-record:${id}`, error, { action: 'prompt-record-retry', id });
    }
  }

  async function send(row) {
    if (!allowed.has(row.connector)) {
      gate.failed(row.id, `Ignite does not send through ${row.connector}: it has no withdrawal validation for it`);
      return;
    }
    const why = unchecked(row);
    if (why) {
      gate.failed(row.id, `Not sent, because it was approved before Ignite had checked it: ${why}`);
      note({ action: 'send-refused', id: row.id, reason: why });
      return;
    }
    if (!gate.claim(row.id)) return;
    note({ action: 'send', id: row.id, connector: row.connector });
    const result = await tool(row, 'execute', publicRow(gate.get(row.id)));
    settle(row.id, sendOutcome(row, result));
  }

  // What a send's run means for its request: sent, failed (nothing can have been paid) or uncertain.
  function sendOutcome(row, result) {
    const body = lastJson(result.stdout);
    const operation = body?.connector_id ?? body?.provider_id; // provider_id: the older spelling a connector may still print
    if (result.code === 0 && operation) {
      return {
        state: 'sent', fields: { connectorId: operation, connectorStatus: body.status || null, receiptUrl: body.receipt_url || null },
        log: { action: 'sent', id: row.id, connectorId: String(operation) },
      };
    }
    if (result.notStarted) {
      const reason = `Not sent: Ignite could not start ${row.connector}: ${reasonOf(result)}`.slice(0, 300);
      return { state: 'failed', reason, log: { action: 'send-not-started', id: row.id, reason } };
    }
    if (body?.created === false) {
      const reason = body.reason ? String(body.reason).slice(0, 300) : reasonOf(result);
      return { state: 'failed', reason, log: { action: 'send-failed', id: row.id, reason } };
    }
    const why = result.code === 0 ? `${row.connector} returned no operation id` : reasonOf(result);
    return { state: 'uncertain', reason: `Ignite does not know whether ${row.connector} made it: ${why}`, log: { action: 'send-uncertain', id: row.id, reason: why } };
  }

  // Records a send's outcome. A ledger that refuses the write (busy) keeps the outcome here, recorded again on a
  // later pass; the request stays claimed, so it is never sent again.
  function settle(id, outcome) {
    try {
      const { row: after } = outcome.state === 'sent' ? gate.sent(id, outcome.fields)
        : outcome.state === 'failed' ? gate.failed(id, outcome.reason) : gate.uncertain(id, outcome.reason);
      unrecorded.delete(id);
      note({ ...outcome.log, state: after?.state || null });
    } catch (error) {
      unrecorded.set(id, outcome);
      later(`record:${id}`, error, { action: 'record-retry', id, outcome: outcome.state });
    }
  }

  async function check(row) {
    if (!allowed.has(row.connector)) return;
    const result = await tool(row, 'status');
    const body = result.code === 0 ? lastJson(result.stdout) : null;
    if (!body) {
      gate.checked(row.id, {});
      note({ action: 'check-failed', id: row.id, reason: reasonOf(result) });
      return;
    }
    gate.checked(row.id, {
      connectorStatus: body.status || null, receiptUrl: body.receipt_url || null,
      final: Boolean(body.final), ok: body.ok !== false, reason: body.reason || null,
    });
  }

  async function reconcile(row) {
    if (!allowed.has(row.connector)) return;
    const operation = row.connector_id || row.answered_operation;
    const result = await tool(row, 'status', { ...publicRow(row), connector_id: operation });
    const body = result.code === 0 ? lastJson(result.stdout) : null;
    if (!body?.status) {
      gate.reconciled(row.id, { found: false });
      note({ action: 'reconcile-failed', id: row.id, reason: reasonOf(result) });
      return;
    }
    const { row: after } = gate.reconciled(row.id, {
      found: true, connectorId: operation, connectorStatus: body.status, receiptUrl: body.receipt_url || null,
      final: Boolean(body.final), ok: body.ok !== false, reason: body.reason || null,
    });
    note({ action: 'reconciled', id: row.id, state: after?.state || null, connectorStatus: body.status });
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

  // The agent store records the notice under payment:<id>:<state> with its wake or post, so a retry after either
  // write tells it no second time. A failed try is retried RETRY_MS later; after NOTIFY_TRIES in one service run the
  // outcome is marked notified and logged as lost.
  function tell(row) {
    const key = `notify:${row.id}:${row.state}`;
    if (!due(key)) return;
    const lost = (reason) => {
      gate.notified(row.id, row.state);
      note({ action: 'notify-lost', id: row.id, state: row.state, reason });
    };
    let told = null;
    try {
      const agentStore = store(row.agent);
      if (!agentStore) {
        lost(`agent ${row.agent} has no store`);
      } else {
        // A conversation rekeyed after the request (its first root post) is found under its new key.
        const conv = agentStore.followConversation(row.conversation_key);
        if (!conv) {
          lost(`conversation ${row.conversation_key} not found`);
        } else {
          const text = outcomeText(gate, row);
          told = agentStore.notify({
            id: `payment:${row.id}:${row.state}`, conversationKey: conv.key, note: text,
            payload: { text: `System message: ${text}`, audio: false, files: [] },
          });
          gate.notified(row.id, row.state);
          note({ action: 'notify', id: row.id, state: row.state, woke: told.woke, ...(told.inserted ? {} : { already: true }) });
        }
      }
    } catch (error) {
      const tries = (notifyTries.get(key) || 0) + 1;
      notifyTries.set(key, tries);
      if (tries < NOTIFY_TRIES) {
        later(key, error, { action: 'notify-retry', id: row.id, state: row.state, tries });
        return;
      }
      try {
        lost(`not told after ${tries} tries: ${error.message}`);
      } catch (markError) {
        later(key, markError, { action: 'notify-retry', id: row.id, state: row.state, tries });
        return;
      }
    }
    notifyTries.delete(key);
    nextTry.delete(key);
    // The notice is in the agent store, put there now or by a try whose mark the ledger refused.
    if (told) kick(row.agent);
  }

  async function pass() {
    try {
      for (const [id, outcome] of unrecorded) {
        if (halted) return;
        if (due(`record:${id}`)) settle(id, outcome);
      }
      for (const [id, message] of unrecordedPrompts) {
        if (halted) return;
        if (due(`prompt-record:${id}`)) recordPrompt(id, message);
      }
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
