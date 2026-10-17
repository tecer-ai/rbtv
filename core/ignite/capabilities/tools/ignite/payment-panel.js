'use strict';

// The owner's side of the payment gate in Slack: the /payments panel, the PIN, and the Approve and
// Refuse buttons, on the waking service's Socket Mode connection. Only the owner acts: every action
// is checked against slack.ownerUserId and slack.team, and anyone else is refused with nothing changed.
//
// API
// createPaymentPanel({ gate, slack, config, log?, kick?, redraw? }) → { ack(type, payload), handle(type, payload) }
//   gate() → the Gate, or null when the config has no payments section; slack() → the Slack client;
//   config() → Ignite's config; kick() asks the payment runner for a pass (an approval is sent at once); redraw(view)
//   → the view of another panel whose request buttons were pressed (the agent panel), or null for the payments panel.
//   ack and handle are slack.js connect's interactions. ack answers at once and touches neither the ledger nor
//   Slack: a slash command's refusal, a form's field errors (not the owner, the PIN's form, an amount, the mode
//   rules of payments.js), or, for a form that passes them, a "Checking" view in its place. handle then does the
//   work and shows it with Slack calls: /payments opens the panel, or the PIN form on first use; Approve opens a
//   PIN form for that request (on top of the panel, or alone from a thread message); Refuse refuses at once;
//   Change settings opens the settings form, which carries the settings revision it shows. Approve is offered,
//   and accepted, only for a request whose recipient Ignite has checked (payments.js unchecked); an unchecked one
//   shows Refuse alone and why. A submitted form's checking view becomes its outcome, or the form again with the
//   reason: a wrong PIN, or settings changed since the form opened. The ledger changes first; a Slack call that
//   fails after it shows the outcome as text, saying the panel could not refresh, never that nothing changed.
//   Each approve, refuse and settings interaction is recorded by its key, so a replay changes nothing. Five wrong
//   PINs in a row lock every PIN form for 15 minutes (payments.js checkPin).
// promptBlocks(gate, row) → the blocks of a request's message in its agent's thread: the recipient as Ignite
//   resolved it through the connector, then Approve and Refuse while it is pending (Refuse alone while it is
//   unchecked), else its outcome.
//   promptText(gate, row) → that message's text. The agent's own description shows only as a labelled note.
// isOwner(config, payload) → whether an interaction comes from config.slack.ownerUserId within config.slack.team; the
//   agent panel checks the owner with it too.
// interactionKey(payload) → the key an interaction is recorded by: a form's view id and hash, a button's action
//   time; null when the payload has neither.
// ACTION, VIEW — the action ids and the view callback ids.

const { parseAmount, canonicalAmount, settingsProblem, unchecked, PIN_RE, PERIODS, MAX_LIMIT_CENTS } = require('./payments.js');
const { plain, section, context, esc, modal } = require('./blocks.js');

const ACTION = Object.freeze({ approve: 'payments_approve', refuse: 'payments_refuse', settings: 'payments_settings' });
const VIEW = Object.freeze({
  panel: 'payments_panel', setPin: 'payments_set_pin', approve: 'payments_approve',
  settings: 'payments_settings', done: 'payments_done',
});
const FORMS = Object.freeze([VIEW.setPin, VIEW.approve, VIEW.settings]);
const PIN_BLOCK = 'payments_pin';
const PENDING_SHOWN = 15;
const LIMIT_CHARS = canonicalAmount(MAX_LIMIT_CENTS).length;
const NOT_SET_UP = "Payments are not set up here: Ignite's config has no payments section.";
const MODE_TEXT = {
  off: 'Off: every payment is refused',
  automatic: 'Automatic within the limits',
  case_by_case: 'Case by case: every payment waits for you',
};
const PERIOD_TEXT = { day: 'Today', week: 'This week', month: 'This month' };
const LIMIT_LABEL = { day: 'Daily limit', week: 'Weekly limit (weeks start Monday)', month: 'Monthly limit' };

const FORMATS = new Map();
function clock(zone, withDay) {
  const key = `${zone}|${withDay}`;
  if (!FORMATS.has(key)) {
    FORMATS.set(key, new Intl.DateTimeFormat('en-GB', {
      timeZone: zone, hour: '2-digit', minute: '2-digit', hourCycle: 'h23', ...(withDay ? { day: 'numeric', month: 'short' } : {}),
    }));
  }
  return FORMATS.get(key);
}

function receiptLink(url) {
  return typeof url === 'string' && /^https:\/\/[^\s<>|]+$/.test(url) ? `<${url}|receipt>` : 'receipt pending';
}

function keyLabel(method) {
  if (method === 'pix') return 'Pix key';
  if (method === 'bill') return 'Bill line';
  if (method === 'qr') return 'QR code';
  if (method === 'recharge') return 'Phone';
  return 'Recipient key';
}

function who(name, document, bank) {
  return [name, document, bank].filter(Boolean).map(esc).join(' · ');
}

// What a request is paid to, as the owner may read it: Ignite's resolution, else the key the money goes to.
function label(row) {
  return row.resolved_name || row.recipient_key;
}

function details(gate, row) {
  const lines = [];
  const checked = row.resolved_at != null;
  if (checked) {
    lines.push(`*Recipient* ${who(row.resolved_name, row.resolved_document, row.resolved_bank) || 'not named by the bank'} (checked by Ignite through ${esc(row.connector)})`);
    lines.push(`*${keyLabel(row.method)}* ${esc(row.resolved_key || row.recipient_key)}`);
  } else {
    lines.push(row.resolve_error
      ? `*Recipient* not checked: Ignite could not read it through ${esc(row.connector)} (${esc(row.resolve_error)})`
      : '*Recipient* not checked by Ignite yet');
    lines.push(`*${keyLabel(row.method)}* ${esc(row.recipient_key)}`);
  }
  lines.push(`*Amount* ${gate.money(row.amount_cents)}${row.fee_cents ? ` + fee ${gate.money(row.fee_cents)}` : ''}`);
  const told = who(row.recipient_name, row.recipient_document, row.recipient_bank);
  if (told && (!checked || told !== who(row.resolved_name, row.resolved_document, row.resolved_bank))) {
    lines.push(`_The agent's own description, not checked:_ ${told}`);
  }
  if (row.note) lines.push(`*Agent's note* ${esc(row.note)}`);
  return lines.join('\n');
}

function outcome(gate, row) {
  if (row.state === 'pending') return `Waits for you: ${esc(row.reason)}`;
  if (row.state === 'approved') return row.decided_by === 'owner' ? 'Approved by you; Ignite is sending it.' : 'Approved by rule; Ignite is sending it.';
  if (row.state === 'sent') return `Sent: ${esc(row.connector)} id ${esc(row.connector_id)}${row.connector_status ? `, ${esc(row.connector_status)}` : ''} · ${receiptLink(row.receipt_url)}`;
  if (row.state === 'uncertain') return `Uncertain: ${esc(row.reason)}`;
  if (row.state === 'refused') return row.decided_by === 'owner' ? 'Refused by you.' : `Refused: ${esc(row.reason)}`;
  if (row.state === 'cancelled') return 'Withdrawn by the agent.';
  return `Failed: ${esc(row.reason)}`;
}

// A pending request's buttons: Approve only once Ignite has checked its recipient.
function buttons(row) {
  return {
    type: 'actions',
    block_id: `payment:${row.id}`,
    elements: [
      ...(unchecked(row) ? [] : [{ type: 'button', action_id: ACTION.approve, text: plain('Approve'), style: 'primary', value: row.id }]),
      { type: 'button', action_id: ACTION.refuse, text: plain('Refuse'), style: 'danger', value: row.id },
    ],
  };
}

// What a pending request says in place of Approve while its recipient is unchecked; null once it is checked.
function uncheckedLine(row) {
  if (!unchecked(row)) return null;
  return row.resolve_error != null
    ? 'It cannot be approved: Ignite could not check its recipient. Refuse it; the agent can ask again.'
    : 'Approve appears once Ignite has checked the recipient.';
}

function promptBlocks(gate, row) {
  const blocks = [section(`*Payment request ${row.id}* from ${esc(row.agent)}\n${details(gate, row)}`)];
  if (row.state === 'pending') {
    blocks.push(context(`Waits for you: ${esc(row.reason)}`));
    if (uncheckedLine(row)) blocks.push(context(uncheckedLine(row)));
    blocks.push(buttons(row));
  } else {
    blocks.push(context(outcome(gate, row)));
  }
  return blocks;
}

function promptText(gate, row) {
  return `Payment request ${row.id} from ${row.agent}: ${gate.money(row.amount_cents)} to ${label(row)} (${row.state})`;
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

function panelView(gate) {
  const { mode, limits } = gate.settings();
  const used = gate.usage();
  const usage = PERIODS.map((p) => `*${PERIOD_TEXT[p]}*\n${gate.money(used[p])} ${limits[p] == null ? '(no limit)' : `of ${gate.money(limits[p])}`}`);
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
    blocks.push(section(`*${row.id}* from ${esc(row.agent)}: ${gate.money(row.amount_cents + row.fee_cents)}\n${details(gate, row)}\nWaits: ${esc(row.reason)}`));
    if (uncheckedLine(row)) blocks.push(context(uncheckedLine(row)));
    blocks.push(buttons(row));
  }
  if (pending.length > PENDING_SHOWN) blocks.push(context(`${pending.length - PENDING_SHOWN} more wait; act on these first.`));
  const uncertain = gate.listUncertain();
  if (uncertain.length) {
    blocks.push({ type: 'divider' });
    blocks.push(section(`*Uncertain* (${uncertain.length}): counted in the usage above until Ignite reads them at the bank`));
    for (const row of uncertain) {
      blocks.push(context(`${row.id} from ${esc(row.agent)} · ${gate.money(row.amount_cents + row.fee_cents)} to ${esc(label(row))} · ${esc(row.reason)}`));
    }
  }
  blocks.push({ type: 'divider' });
  const sent = gate.lastSent(10);
  blocks.push(section('*Last ten sent*'));
  if (!sent.length) blocks.push(context('Nothing sent yet.'));
  for (const row of sent) {
    blocks.push(context(`${row.id} · ${clock(gate.timeZone, true).format(new Date(row.sent_at))} · ${gate.money(row.amount_cents + row.fee_cents)} to ${esc(label(row))} · ${receiptLink(row.receipt_url)}`));
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

function approveView(gate, row, error = null) {
  return modal(VIEW.approve, 'Approve payment', [
    section(`*${row.id}* from ${esc(row.agent)}: ${gate.money(row.amount_cents + row.fee_cents)}\n${details(gate, row)}\nWaits: ${esc(row.reason)}`),
    ...(error ? [context(error)] : []),
    pinInput(),
  ], { submit: 'Approve', close: 'Cancel', metadata: row.id });
}

// The settings form: the saved settings, or the values a refused submission carried, with the revision it shows.
function settingsView(gate, { mode = null, limits = null, revision = null, error = null } = {}) {
  const saved = gate.settings();
  const shown = { mode: mode ?? saved.mode, limits: limits ?? saved.limits, revision: revision ?? saved.revision };
  const options = Object.keys(MODE_TEXT).map((value) => ({ text: plain(MODE_TEXT[value]), value }));
  return modal(VIEW.settings, 'Payment settings', [
    ...(error ? [context(error)] : []),
    {
      type: 'input',
      block_id: 'payments_mode',
      label: plain('Mode'),
      element: { type: 'radio_buttons', action_id: 'value', options, initial_option: options.find((o) => o.value === shown.mode) },
    },
    ...PERIODS.map((p) => textInput(`payments_${p}`, `${LIMIT_LABEL[p]}, ${gate.currency}`, {
      optional: true, initial: canonicalAmount(shown.limits[p]), max: LIMIT_CHARS, hint: 'Like 1500.00. Blank for no limit; automatic needs at least one.',
    })),
    pinInput(),
  ], { submit: 'Save', close: 'Cancel', metadata: JSON.stringify({ revision: shown.revision }) });
}

function doneView(text) {
  return modal(VIEW.done, 'Payments', [section(text)]);
}

function checkingView() {
  return modal(VIEW.done, 'Payments', [section('Checking…')]);
}

function valueOf(view, blockId) {
  const entry = view?.state?.values?.[blockId]?.value;
  if (!entry) return null;
  if (entry.selected_option) return entry.selected_option.value;
  return typeof entry.value === 'string' ? entry.value.trim() : null;
}

function sentence(text) {
  return `${text[0].toUpperCase()}${text.slice(1)}.`;
}

function readLimits(view) {
  const limits = {};
  const bad = {};
  for (const period of PERIODS) {
    const raw = valueOf(view, `payments_${period}`);
    if (!raw) { limits[period] = null; continue; }
    const cents = parseAmount(raw);
    if (cents == null || cents < 1) bad[`payments_${period}`] = 'Write an amount like 1500.00.';
    else limits[period] = cents;
  }
  return { limits, bad: Object.keys(bad).length ? bad : null };
}

// A submitted form's problems that need neither the ledger nor the PIN's hash; null when there are none.
function formProblems(view) {
  if (view.callback_id === VIEW.setPin) {
    const pin = valueOf(view, PIN_BLOCK) || '';
    if (!PIN_RE.test(pin)) return { [PIN_BLOCK]: 'Use 4 to 12 digits.' };
    if (pin !== valueOf(view, 'payments_pin_again')) return { payments_pin_again: 'The two PINs differ.' };
    return null;
  }
  if (view.callback_id === VIEW.settings) {
    const { limits, bad } = readLimits(view);
    if (bad) return bad;
    const problem = settingsProblem(valueOf(view, 'payments_mode'), limits);
    return problem ? { [`payments_${problem.field}`]: sentence(problem.message) } : null;
  }
  return null;
}

function revisionOf(view) {
  try {
    const revision = JSON.parse(view.private_metadata || '{}').revision;
    return Number.isSafeInteger(revision) ? revision : -1;
  } catch {
    return -1;
  }
}

function interactionKey(payload) {
  if (payload?.type === 'view_submission') {
    const view = payload.view || {};
    return view.id && view.hash ? `view:${view.id}:${view.hash}` : null;
  }
  const act = payload?.actions?.[0];
  if (act?.action_ts) return `action:${act.action_ts}:${act.action_id}:${act.value ?? ''}`;
  return payload?.trigger_id ? `trigger:${payload.trigger_id}` : null;
}

function pinError(gate, check) {
  if (check.unset) return 'Set a PIN first: open /payments.';
  if (check.locked) return `Locked after five wrong PINs until ${clock(gate.timeZone, false).format(new Date(check.until))}. Nothing changed.`;
  return `Wrong PIN: ${check.left} ${check.left === 1 ? 'try' : 'tries'} left before PIN forms lock for 15 minutes. Nothing changed.`;
}

const errors = (fields) => ({ response_action: 'errors', errors: fields });

// Whether an interaction comes from the owner: the payload's user is config.slack.ownerUserId within config.slack.team.
// A slash command carries user_id and team_id; a button or a form carries user.id and user.team_id or team.id.
function isOwner(config, payload) {
  const user = payload.user_id || payload.user?.id;
  const team = payload.team_id || payload.team?.id || payload.user?.team_id;
  return Boolean(user && user === config.slack.ownerUserId && team && team === config.slack.team);
}

function createPaymentPanel({ gate, slack, config, log = () => {}, kick = () => {}, redraw = () => null } = {}) {
  // A panel other than this one that shows request buttons (the agent panel) is redrawn as itself after an action:
  // roots keeps, by view id, what such a panel was when a form was pushed on it.
  const roots = new Map();
  const rootView = (g, view) => (view && view.callback_id !== VIEW.panel && redraw(view)) || panelView(g);
  const ownerSent = (payload) => isOwner(config(), payload);

  function note(fields) {
    try { log({ event: 'payments', ...fields }); } catch { /* the panel never fails on a log */ }
  }

  function ack(type, payload = {}) {
    if (type === 'slash_commands') {
      if (payload.command !== '/payments') return null;
      if (!ownerSent(payload)) return { text: 'Only the owner can open /payments. Nothing changed.' };
      return gate() ? null : { text: NOT_SET_UP };
    }
    if (type !== 'interactive' || payload.type !== 'view_submission') return null;
    const view = payload.view || {};
    if (!FORMS.includes(view.callback_id)) return null;
    if (!ownerSent(payload)) return errors({ [PIN_BLOCK]: 'Only the owner can do this. Nothing changed.' });
    if (!gate()) return errors({ [PIN_BLOCK]: NOT_SET_UP });
    const problems = formProblems(view);
    return problems ? errors(problems) : { response_action: 'update', view: checkingView() };
  }

  async function slash(payload) {
    if (payload.command !== '/payments') return;
    if (!ownerSent(payload)) {
      note({ action: 'refused', who: payload.user_id || null, what: '/payments' });
      return;
    }
    const g = gate();
    if (!g) return;
    await slack().openView(payload.trigger_id, g.pinSet() ? panelView(g) : setPinView({ next: 'panel' }));
  }

  async function action(payload) {
    const act = payload.actions?.[0];
    if (!act || !Object.values(ACTION).includes(act.action_id)) return;
    const inModal = Boolean(payload.view?.id);
    if (inModal && payload.view.callback_id !== VIEW.panel) {
      roots.set(payload.view.id, { callback_id: payload.view.callback_id, private_metadata: payload.view.private_metadata });
    }
    const show = (view) => (inModal ? slack().pushView(payload.trigger_id, view) : slack().openView(payload.trigger_id, view));
    const tell = async (text) => {
      if (payload.channel?.id) await slack().postEphemeral({ channel: payload.channel.id, user: payload.user?.id, text });
    };
    if (!ownerSent(payload)) {
      note({ action: 'refused', who: payload.user?.id || null, what: act.action_id, id: act.value || null });
      await tell('Only the owner can approve or refuse payments. Nothing changed.');
      return;
    }
    const g = gate();
    if (!g) {
      await tell(NOT_SET_UP);
      return;
    }
    if (act.action_id === ACTION.settings) {
      await show(g.pinSet() ? settingsView(g) : setPinView({ next: 'settings' }));
      return;
    }
    const row = g.get(act.value);
    if (!row) {
      await show(doneView(`Unknown request ${esc(act.value)}. Nothing changed.`));
      return;
    }
    if (act.action_id === ACTION.approve) {
      const why = row.state === 'pending' ? unchecked(row) : null;
      if (row.state !== 'pending') await show(doneView(`${row.id} is ${row.state}: nothing to approve.`));
      else if (why) await show(doneView(`${row.id} cannot be approved: ${esc(why)}. Nothing changed.`));
      else await show(g.pinSet() ? approveView(g, row) : setPinView({ next: 'approve', id: row.id }));
      return;
    }
    const result = g.refuse(row.id, { interaction: interactionKey(payload) });
    if (result.changed) note({ action: 'refuse', id: row.id });
    kick();
    const told = result.replay ? `${row.id}: this click was already handled. Nothing changed.` : `${row.id} is ${result.row.state}: nothing changed.`;
    if (inModal) await showOutcome(payload.view.id, { text: result.changed ? `Refused ${row.id}.` : told, view: () => rootView(g, payload.view) });
    else if (!result.changed) await tell(told);
  }

  // The panel under a form, refreshed after the form's outcome is shown; a failure is logged and the outcome stays.
  async function refreshRoot(g, view) {
    const root = view?.root_view_id;
    if (!root || root === view.id) return;
    try { await slack().updateView(root, rootView(g, roots.get(root))); } catch (error) { note({ action: 'refresh-failed', message: error.message }); }
  }

  // Shows an outcome the ledger already holds, in place of viewId: its view, or its text alone when the view cannot
  // be built or shown, saying that the panel could not refresh.
  async function showOutcome(viewId, { text, view = null }) {
    try {
      await slack().updateView(viewId, view ? view() : doneView(text));
      return;
    } catch (error) {
      note({ action: 'show-failed', message: error.message });
    }
    try {
      await slack().updateView(viewId, doneView(`${text} The panel could not refresh; reopen /payments to see it.`));
    } catch (error) {
      note({ action: 'show-failed', message: error.message });
    }
  }

  // A form that passed ack: the ledger decides at once, and its checking view becomes the outcome. Only a failure
  // of the ledger itself, which changed nothing, says so.
  async function submit(payload) {
    const view = payload.view || {};
    if (!FORMS.includes(view.callback_id)) return;
    if (!ownerSent(payload)) {
      note({ action: 'refused', who: payload.user?.id || null, what: view.callback_id });
      return;
    }
    const g = gate();
    if (!g || formProblems(view)) return;
    const pin = valueOf(view, PIN_BLOCK) || '';
    const interaction = interactionKey(payload);
    let outcome;
    try {
      if (view.callback_id === VIEW.setPin) outcome = submitPin(g, view, pin);
      else if (view.callback_id === VIEW.approve) outcome = submitApprove(g, view, pin, interaction);
      else outcome = submitSettings(g, view, pin, interaction);
    } catch (error) {
      note({ action: 'failed', what: view.callback_id, message: error.message });
      await slack().updateView(view.id, doneView(`Ignite could not do this: ${esc(error.message)}. Nothing changed; try again.`));
      return;
    }
    if (outcome.kick) kick();
    await showOutcome(view.id, outcome);
    if (outcome.refresh) await refreshRoot(g, view);
  }

  // Each form's decision → { text, view?, kick?, refresh? }: the outcome as a sentence, the view that shows it
  // (built only when shown), whether the payment runner should pass now, and whether the panel under it refreshes.
  function submitPin(g, view, pin) {
    if (g.pinSet()) return { text: 'The PIN is already set. Nothing changed.' };
    g.setPin(pin);
    note({ action: 'pin-set' });
    return {
      text: 'PIN saved.',
      view: () => {
        let next = {};
        try { next = JSON.parse(view.private_metadata || '{}'); } catch { /* the panel */ }
        const row = next.id ? g.get(next.id) : null;
        if (next.next === 'approve' && row?.state === 'pending' && !unchecked(row)) return approveView(g, row);
        if (next.next === 'settings') return settingsView(g);
        return panelView(g);
      },
    };
  }

  function submitApprove(g, view, pin, interaction) {
    const result = g.approveWithPin(view.private_metadata, pin, { interaction });
    const row = result.row;
    if (result.replay) return { text: `${row ? `${row.id} is ${row.state}. ` : ''}This form was already submitted: nothing changed.` };
    if (result.unchecked) return { text: `${row.id} cannot be approved: ${esc(result.unchecked)}. Nothing changed.`, refresh: true };
    if (result.pin) {
      note({ action: 'pin-refused', id: row.id, locked: Boolean(result.pin.locked) });
      const error = pinError(g, result.pin);
      return { text: error, view: () => approveView(g, row, error) };
    }
    if (!result.changed) {
      return { text: row ? `${row.id} is ${row.state}: nothing to approve.` : 'Unknown request. Nothing changed.', refresh: true };
    }
    note({ action: 'approve', id: row.id });
    return {
      text: `Approved ${row.id}: ${g.money(row.amount_cents + row.fee_cents)} to ${esc(label(row))}. Ignite is sending it now; the result arrives in ${esc(row.agent)}'s thread.`,
      kick: true,
      refresh: true,
    };
  }

  function submitSettings(g, view, pin, interaction) {
    const mode = valueOf(view, 'payments_mode');
    const { limits } = readLimits(view);
    const revision = revisionOf(view);
    const result = g.saveSettingsWithPin({ mode, limits, revision }, pin, { interaction });
    if (result.replay) return { text: 'This form was already submitted: nothing changed.' };
    if (result.stale) {
      note({ action: 'settings-stale', revision });
      return { text: 'The settings changed after this form was opened. Nothing changed: open Change settings again to see them.', refresh: true };
    }
    if (result.pin) {
      note({ action: 'pin-refused', what: 'settings', locked: Boolean(result.pin.locked) });
      const error = pinError(g, result.pin);
      return { text: error, view: () => settingsView(g, { mode, limits, revision, error }) };
    }
    const saved = result.saved;
    note({ action: 'settings', mode: saved.mode, limits: saved.limits, revision: saved.revision });
    const set = PERIODS.filter((p) => saved.limits[p] != null).map((p) => `${PERIOD_TEXT[p].toLowerCase()} ${g.money(saved.limits[p])}`);
    return { text: `Saved: ${MODE_TEXT[saved.mode]}${set.length ? `; limits ${set.join(', ')}` : '; no limit'}.`, refresh: true };
  }

  async function handle(type, payload = {}) {
    if (type === 'slash_commands') return slash(payload);
    if (type === 'interactive' && payload.type === 'block_actions') return action(payload);
    if (type === 'interactive' && payload.type === 'view_submission') return submit(payload);
    return undefined;
  }

  return { ack, handle };
}

module.exports = { createPaymentPanel, isOwner, promptBlocks, promptText, interactionKey, ACTION, VIEW, PIN_BLOCK };
