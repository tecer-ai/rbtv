'use strict';

// The owner's side of the payment gate in Slack: the /payments panel, the PIN, and the Approve and
// Refuse buttons, on the waking service's Socket Mode connection. Only the owner acts: every action
// is checked against slack.ownerUserId and slack.team, and anyone else is refused with nothing changed.
//
// API
// createPaymentPanel({ gate, slack, config, log?, kick? }) → { handle(type, payload) }
//   gate() → the Gate, or null when the config has no payments section; slack() → the Slack client;
//   config() → Ignite's config; kick() asks the payment runner for a pass (an approval is sent at once).
//   handle is slack.js connect's onInteraction: → { response?, after? } or null for an envelope that
//   is not the panel's. response is the ACK's payload (a slash command's reply, a modal's errors or
//   its next view); after() makes the Slack calls once the ACK is sent.
//   /payments opens the panel, or the PIN form on first use. Approve opens a PIN form for that
//   request (on top of the panel, or alone from a thread message); Refuse refuses at once. Change
//   settings opens the settings form, saved only with the PIN. A wrong PIN is a form error; five in
//   a row lock every PIN form for 15 minutes (payments.js checkPin).
// promptBlocks(row) → the blocks of a request's message in its agent's thread: its details, then
//   Approve and Refuse while it is pending, else its outcome.
// ACTION, VIEW — the action ids and the view callback ids.

const { brl, parseAmount, PERIODS, ZONE } = require('./payments.js');

const ACTION = Object.freeze({ approve: 'payments_approve', refuse: 'payments_refuse', settings: 'payments_settings' });
const VIEW = Object.freeze({
  panel: 'payments_panel', setPin: 'payments_set_pin', approve: 'payments_approve',
  settings: 'payments_settings', done: 'payments_done',
});
const PIN_BLOCK = 'payments_pin';
const PIN_RE = /^\d{4,12}$/;
const PENDING_SHOWN = 15;
const MODE_TEXT = {
  off: 'Off: every payment is refused',
  automatic: 'Automatic within the limits',
  case_by_case: 'Case by case: every payment waits for you',
};
const PERIOD_TEXT = { day: 'Today', week: 'This week', month: 'This month' };
const LIMIT_LABEL = { day: 'Daily limit', week: 'Weekly limit (weeks start Monday)', month: 'Monthly limit' };
const TIME = new Intl.DateTimeFormat('en-GB', { timeZone: ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const DAY_TIME = new Intl.DateTimeFormat('en-GB', {
  timeZone: ZONE, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

const plain = (text) => ({ type: 'plain_text', text: String(text).slice(0, 150) });
const section = (text) => ({ type: 'section', text: { type: 'mrkdwn', text: String(text).slice(0, 3000) } });
const context = (text) => ({ type: 'context', elements: [{ type: 'mrkdwn', text: String(text).slice(0, 3000) }] });

// Text an agent or a bank supplied, shown as mrkdwn: no link, mention or markup of its own.
function esc(value) {
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function receiptLink(url) {
  return typeof url === 'string' && /^https:\/\/[^\s<>|]+$/.test(url) ? `<${url}|receipt>` : 'receipt pending';
}

function keyLabel(method) {
  if (method === 'pix') return 'Pix key';
  if (method === 'bill') return 'Bill line';
  return 'Recipient key';
}

function details(row) {
  const who = [row.recipient_name, row.recipient_document, row.recipient_bank].filter(Boolean).map(esc).join(' · ');
  const lines = [
    `*Recipient* ${who || 'not named'}`,
    `*${keyLabel(row.method)}* ${esc(row.recipient_key)}`,
    `*Amount* ${brl(row.amount_cents)}${row.fee_cents ? ` + fee ${brl(row.fee_cents)}` : ''}`,
  ];
  if (row.note) lines.push(`*Note* ${esc(row.note)}`);
  return lines.join('\n');
}

function outcome(row) {
  if (row.state === 'pending') return `Waits for you: ${esc(row.reason)}`;
  if (row.state === 'approved') return row.decided_by === 'owner' ? 'Approved by you; Ignite is sending it.' : 'Approved by rule; Ignite is sending it.';
  if (row.state === 'sent') return `Sent: ${esc(row.provider)} id ${esc(row.provider_id)}${row.provider_status ? `, ${esc(row.provider_status)}` : ''} · ${receiptLink(row.receipt_url)}`;
  if (row.state === 'refused') return row.decided_by === 'owner' ? 'Refused by you.' : `Refused: ${esc(row.reason)}`;
  if (row.state === 'cancelled') return 'Withdrawn by the agent.';
  return `Failed: ${esc(row.reason)}`;
}

function buttons(id) {
  return {
    type: 'actions',
    block_id: `payment:${id}`,
    elements: [
      { type: 'button', action_id: ACTION.approve, text: plain('Approve'), style: 'primary', value: id },
      { type: 'button', action_id: ACTION.refuse, text: plain('Refuse'), style: 'danger', value: id },
    ],
  };
}

function promptBlocks(row) {
  const blocks = [section(`*Payment request ${row.id}* from ${esc(row.agent)}\n${details(row)}`)];
  if (row.state === 'pending') {
    blocks.push(context(`Waits for you: ${esc(row.reason)}`));
    blocks.push(buttons(row.id));
  } else {
    blocks.push(context(outcome(row)));
  }
  return blocks;
}

function promptText(row) {
  return `Payment request ${row.id} from ${row.agent}: ${brl(row.amount_cents)} to ${row.recipient_name || row.recipient_key} (${row.state})`;
}

function modal(callbackId, title, blocks, { submit = null, close = 'Close', metadata = '' } = {}) {
  return {
    type: 'modal',
    callback_id: callbackId,
    title: plain(title),
    close: plain(close),
    ...(submit ? { submit: plain(submit) } : {}),
    ...(metadata ? { private_metadata: metadata } : {}),
    blocks,
  };
}

function textInput(blockId, label, { optional = false, initial = null, hint = null, max = 12 } = {}) {
  return {
    type: 'input',
    block_id: blockId,
    optional,
    label: plain(label),
    ...(hint ? { hint: plain(hint) } : {}),
    element: {
      type: 'plain_text_input',
      action_id: 'value',
      max_length: max,
      ...(initial ? { initial_value: initial } : {}),
    },
  };
}

function pinInput(label = 'PIN') {
  return textInput(PIN_BLOCK, label, { hint: 'Slack shows what you type: enter it where no one can see.' });
}

function plainAmount(cents) {
  return cents == null ? null : brl(cents).replace('R$ ', '');
}

function panelView(gate) {
  const { mode, limits } = gate.settings();
  const used = gate.usage();
  const usage = PERIODS.map((p) => `*${PERIOD_TEXT[p]}*\n${brl(used[p])} ${limits[p] == null ? '(no limit)' : `of ${brl(limits[p])}`}`);
  const blocks = [
    section(`*Mode* ${MODE_TEXT[mode]}`),
    { type: 'section', fields: usage.map((text) => ({ type: 'mrkdwn', text })) },
    { type: 'actions', elements: [{ type: 'button', action_id: ACTION.settings, text: plain('Change settings'), value: 'settings' }] },
    { type: 'divider' },
  ];
  const pending = gate.pending();
  blocks.push(section(`*Pending* (${pending.length})`));
  if (!pending.length) blocks.push(context('No request waits for you.'));
  for (const row of pending.slice(0, PENDING_SHOWN)) {
    blocks.push(section(`*${row.id}* from ${esc(row.agent)}: ${brl(row.amount_cents + row.fee_cents)}\n${details(row)}\nWaits: ${esc(row.reason)}`));
    blocks.push(buttons(row.id));
  }
  if (pending.length > PENDING_SHOWN) blocks.push(context(`${pending.length - PENDING_SHOWN} more wait; act on these first.`));
  blocks.push({ type: 'divider' });
  const sent = gate.lastSent(10);
  blocks.push(section('*Last ten sent*'));
  if (!sent.length) blocks.push(context('Nothing sent yet.'));
  for (const row of sent) {
    blocks.push(context(`${row.id} · ${DAY_TIME.format(new Date(row.sent_at))} · ${brl(row.amount_cents + row.fee_cents)} to ${esc(row.recipient_name || row.recipient_key)} · ${receiptLink(row.receipt_url)}`));
  }
  return modal(VIEW.panel, 'Payments', blocks);
}

function setPinView(next) {
  return modal(VIEW.setPin, 'Set payments PIN', [
    section('Choose a PIN of 4 to 12 digits. Ignite asks for it on every approval you make and when you save settings. It keeps only a salted hash.'),
    pinInput('New PIN'),
    textInput('payments_pin_again', 'The same PIN again'),
  ], { submit: 'Save PIN', close: 'Cancel', metadata: JSON.stringify(next) });
}

function approveView(row) {
  return modal(VIEW.approve, 'Approve payment', [
    section(`*${row.id}* from ${esc(row.agent)}: ${brl(row.amount_cents + row.fee_cents)}\n${details(row)}\nWaits: ${esc(row.reason)}`),
    pinInput(),
  ], { submit: 'Approve', close: 'Cancel', metadata: row.id });
}

function settingsView(gate) {
  const { mode, limits } = gate.settings();
  const options = Object.keys(MODE_TEXT).map((value) => ({ text: plain(MODE_TEXT[value]), value }));
  return modal(VIEW.settings, 'Payment settings', [
    {
      type: 'input',
      block_id: 'payments_mode',
      label: plain('Mode'),
      element: { type: 'radio_buttons', action_id: 'value', options, initial_option: options.find((o) => o.value === mode) },
    },
    ...PERIODS.map((p) => textInput(`payments_${p}`, `${LIMIT_LABEL[p]}, R$`, {
      optional: true, initial: plainAmount(limits[p]), hint: 'Blank for no limit. Automatic needs at least one.',
    })),
    pinInput(),
  ], { submit: 'Save', close: 'Cancel' });
}

function doneView(text) {
  return modal(VIEW.done, 'Payments', [section(text)]);
}

function valueOf(view, blockId) {
  const entry = view?.state?.values?.[blockId]?.value;
  if (!entry) return null;
  if (entry.selected_option) return entry.selected_option.value;
  return typeof entry.value === 'string' ? entry.value.trim() : null;
}

function pinError(check) {
  if (check.unset) return 'Set a PIN first: open /payments.';
  if (check.locked) return `Locked after five wrong PINs until ${TIME.format(new Date(check.until))}. Nothing changed.`;
  return `Wrong PIN: ${check.left} ${check.left === 1 ? 'try' : 'tries'} left before PIN forms lock for 15 minutes. Nothing changed.`;
}

const errors = (fields) => ({ response: { response_action: 'errors', errors: fields } });
const update = (view, after) => ({ response: { response_action: 'update', view }, ...(after ? { after } : {}) });

function createPaymentPanel({ gate, slack, config, log = () => {}, kick = () => {} } = {}) {
  function isOwner(payload) {
    const cfg = config();
    const user = payload.user_id || payload.user?.id;
    const team = payload.team_id || payload.team?.id || payload.user?.team_id;
    return Boolean(user && user === cfg.slack.ownerUserId && team && team === cfg.slack.team);
  }

  function note(fields) {
    try { log({ event: 'payments', ...fields }); } catch { /* the panel never fails on a log */ }
  }

  function slash(payload) {
    if (payload.command !== '/payments') return null;
    if (!isOwner(payload)) {
      note({ action: 'refused', who: payload.user_id || null, what: '/payments' });
      return { response: { text: 'Only the owner can open /payments. Nothing changed.' } };
    }
    const g = gate();
    if (!g) return { response: { text: "Payments are not set up here: Ignite's config has no payments section." } };
    const view = g.pinSet() ? panelView(g) : setPinView({ next: 'panel' });
    return { after: () => slack().openView(payload.trigger_id, view) };
  }

  function action(payload) {
    const act = payload.actions?.[0];
    if (!act || !Object.values(ACTION).includes(act.action_id)) return null;
    const inModal = Boolean(payload.view?.id);
    const show = (view) => () => (inModal ? slack().pushView(payload.trigger_id, view) : slack().openView(payload.trigger_id, view));
    const tell = (text) => async () => {
      if (payload.channel?.id) await slack().postEphemeral({ channel: payload.channel.id, user: payload.user?.id, text });
    };
    if (!isOwner(payload)) {
      note({ action: 'refused', who: payload.user?.id || null, what: act.action_id, id: act.value || null });
      return { after: tell('Only the owner can approve or refuse payments. Nothing changed.') };
    }
    const g = gate();
    if (!g) return { after: tell("Payments are not set up here: Ignite's config has no payments section.") };
    if (act.action_id === ACTION.settings) {
      return { after: show(g.pinSet() ? settingsView(g) : setPinView({ next: 'settings' })) };
    }
    const row = g.get(act.value);
    if (!row) return { after: show(doneView(`Unknown request ${esc(act.value)}. Nothing changed.`)) };
    if (act.action_id === ACTION.approve) {
      if (row.state !== 'pending') return { after: show(doneView(`${row.id} is ${row.state}: nothing to approve.`)) };
      return { after: show(g.pinSet() ? approveView(row) : setPinView({ next: 'approve', id: row.id })) };
    }
    const result = g.refuse(row.id);
    if (result.changed) note({ action: 'refuse', id: row.id });
    return {
      after: async () => {
        kick();
        if (inModal) await slack().updateView(payload.view.id, panelView(g));
        else if (!result.changed) await tell(`${row.id} is ${result.row.state}: nothing changed.`)();
      },
    };
  }

  function refreshRoot(g, view) {
    const root = view?.root_view_id;
    return root && root !== view.id ? () => slack().updateView(root, panelView(g)) : null;
  }

  function submit(payload) {
    const view = payload.view || {};
    if (![VIEW.setPin, VIEW.approve, VIEW.settings].includes(view.callback_id)) return null;
    if (!isOwner(payload)) {
      note({ action: 'refused', who: payload.user?.id || null, what: view.callback_id });
      return errors({ [PIN_BLOCK]: 'Only the owner can do this. Nothing changed.' });
    }
    const g = gate();
    if (!g) return errors({ [PIN_BLOCK]: "Payments are not set up here: Ignite's config has no payments section." });
    const pin = valueOf(view, PIN_BLOCK) || '';

    if (view.callback_id === VIEW.setPin) {
      if (g.pinSet()) return errors({ [PIN_BLOCK]: 'The PIN is already set. Nothing changed.' });
      if (!PIN_RE.test(pin)) return errors({ [PIN_BLOCK]: 'Use 4 to 12 digits.' });
      if (pin !== valueOf(view, 'payments_pin_again')) return errors({ payments_pin_again: 'The two PINs differ.' });
      g.setPin(pin);
      note({ action: 'pin-set' });
      let next = {};
      try { next = JSON.parse(view.private_metadata || '{}'); } catch { /* the panel */ }
      const row = next.id ? g.get(next.id) : null;
      if (next.next === 'approve' && row?.state === 'pending') return update(approveView(row));
      if (next.next === 'settings') return update(settingsView(g));
      return update(panelView(g));
    }

    if (view.callback_id === VIEW.approve) {
      const row = g.get(view.private_metadata);
      if (!row || row.state !== 'pending') {
        return update(doneView(row ? `${row.id} is ${row.state}: nothing to approve.` : 'Unknown request. Nothing changed.'), refreshRoot(g, view));
      }
      const check = g.checkPin(pin);
      if (!check.ok) {
        note({ action: 'pin-refused', id: row.id, locked: Boolean(check.locked) });
        return errors({ [PIN_BLOCK]: pinError(check) });
      }
      const result = g.approve(row.id);
      if (!result.changed) return update(doneView(`${row.id} is ${result.row.state}: nothing to approve.`), refreshRoot(g, view));
      note({ action: 'approve', id: row.id });
      const root = refreshRoot(g, view);
      return update(
        doneView(`Approved ${row.id}: ${brl(row.amount_cents + row.fee_cents)} to ${esc(row.recipient_name || row.recipient_key)}. Ignite is sending it now; the result arrives in ${esc(row.agent)}'s thread.`),
        async () => { kick(); if (root) await root(); },
      );
    }

    const mode = valueOf(view, 'payments_mode');
    const limits = {};
    const bad = {};
    for (const period of PERIODS) {
      const raw = valueOf(view, `payments_${period}`);
      if (!raw) { limits[period] = null; continue; }
      const cents = parseAmount(raw);
      if (cents == null || cents < 1) bad[`payments_${period}`] = 'Write an amount in reais, like 150 or 150,00.';
      else limits[period] = cents;
    }
    if (Object.keys(bad).length) return errors(bad);
    if (!['off', 'automatic', 'case_by_case'].includes(mode)) return errors({ payments_mode: 'Choose a mode.' });
    if (mode === 'automatic' && PERIODS.every((p) => limits[p] == null)) {
      return errors({ payments_mode: 'Automatic needs at least one limit: set a daily, weekly or monthly limit.' });
    }
    const check = g.checkPin(pin);
    if (!check.ok) {
      note({ action: 'pin-refused', what: 'settings', locked: Boolean(check.locked) });
      return errors({ [PIN_BLOCK]: pinError(check) });
    }
    const saved = g.saveSettings({ mode, limits });
    note({ action: 'settings', mode: saved.mode, limits: saved.limits });
    const set = PERIODS.filter((p) => saved.limits[p] != null).map((p) => `${PERIOD_TEXT[p].toLowerCase()} ${brl(saved.limits[p])}`);
    return update(doneView(`Saved: ${MODE_TEXT[saved.mode]}${set.length ? `; limits ${set.join(', ')}` : '; no limit'}.`), refreshRoot(g, view));
  }

  async function handle(type, payload = {}) {
    if (type === 'slash_commands') return slash(payload);
    if (type === 'interactive' && payload.type === 'block_actions') return action(payload);
    if (type === 'interactive' && payload.type === 'view_submission') return submit(payload);
    return null;
  }

  return { handle };
}

module.exports = { createPaymentPanel, promptBlocks, promptText, ACTION, VIEW, PIN_BLOCK };
