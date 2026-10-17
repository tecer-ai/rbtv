'use strict';

// The /agent panel: the owner types /agent in an agent's channel, or in the app's direct messages for
// config.dmAgent, and a modal shows that agent. Tab buttons redraw it in place: Configuration (Overview,
// Installed, Prompt), State (Board, Timers), Work (Tasks, Sub-agents), Approvals (Payments) and Docs (Recent).
// It reads the agent's agent.json, prompt.md, board file, its store (schedules, open work, the running turn,
// progress notes), cast's handle registry and the payment ledger. It changes nothing itself but the channel
// canvas, when the owner opens a document in it, and the agent's output/ignite/canvas/, when the owner saves
// the canvas there (docs.js). Approve and Refuse on a payment are the payment panel's own buttons, handled
// there with its PIN.
//
// API
// createAgentPanel({ slack, config, store, gate?, log?, launches?, now? }) → { ack(type, payload), handle(type, payload), redraw(view) }
//   slack() → the Slack client; config() → Ignite's config; store(slug) → that agent's Store, or null;
//   launches() → cast's launches, each with alive (default: the handle registry, each process checked); now() → ms;
//   gate() → the payment gate, or null. redraw(view) → the agent panel a payment action was taken in, on Approvals,
//   for the payment panel to show after it; null for any other view.
//   ack answers a /agent slash command at once: a refusal for anyone but the owner, or where no agent answers;
//   null otherwise, and for anything else. handle then opens the panel with the command's trigger_id, or, for a
//   tab button pressed inside the panel, redraws it with views.update. Both re-check the owner; anyone else's
//   button changes nothing. handle never rejects: a failed Slack call is logged as { event: 'agent-panel' }.
// agentView({ slug, home, store, tab, gate?, workspace?, channel?, notice?, launches?, now? }) → the panel's modal on one tab; an unknown tab shows the first.
// castLaunches() → every launch in cast's handle registry, its latest row per process, with alive.
// agentOf(config, payload) → the slug a slash command's channel answers to, or null.
// TABS — the tab ids, in order, each with its group and label.

const fs = require('fs');
const path = require('path');

const { readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');
const { readHandles, procStarts } = require('../../../../cast/capabilities/tools/cast/lib/handles');
const { agentHome } = require('./config.js');
const { boardPath } = require('./board.js');
const { plain, section, context, esc, modal } = require('./blocks.js');
const { isOwner, promptBlocks } = require('./payment-panel.js');
const { recentDocs, openDocument, openDoc, saveDoc, pendingSaves } = require('./docs.js');

const COMMAND = '/agent';
const VIEW = 'agent_panel';
const ACTION = 'agent_tab';
const OPEN_DOC = 'agent_doc_open';
const SAVE_DOC = 'agent_doc_save';
const TABS = Object.freeze([
  { id: 'overview', group: 'Configuration', label: 'Overview' },
  { id: 'installed', group: 'Configuration', label: 'Installed' },
  { id: 'prompt', group: 'Configuration', label: 'Prompt' },
  { id: 'board', group: 'State', label: 'Board' },
  { id: 'timers', group: 'State', label: 'Timers' },
  { id: 'tasks', group: 'Work', label: 'Tasks' },
  { id: 'subagents', group: 'Work', label: 'Sub-agents' },
  { id: 'payments', group: 'Approvals', label: 'Payments' },
  { id: 'docs', group: 'Docs', label: 'Recent' },
]);
const GROUPS = [...new Set(TABS.map((tab) => tab.group))];
// Slack's limits: a modal's title, the characters of a section, the blocks of a view.
const TITLE_CHARS = 24;
const SECTION_CHARS = 3000;
const MAX_BLOCKS = 100;
// The kinds of file the installer records in agent.json, by its method name, and the label each is shown with.
const KINDS = [['skill', 'Skills'], ['rule', 'Rules'], ['tool', 'Tools'], ['command', 'Commands']];
// Work that is not finished, and how each state reads.
const OPEN_WORK = { open: 'In progress', continue: 'Continuing', waiting_owner: 'Waiting for you', waiting_workers: 'Waiting for workers', held: 'Held after failures' };
// How many notes each task shows, and how many ended sub-agents.
const NOTES_SHOWN = 3;
const ENDED_SHOWN = 15;
// How many decided payment requests Approvals shows after the pending ones.
const DECIDED_SHOWN = 10;

function agentOf(config, payload) {
  const routed = config.routes?.[payload.channel_id];
  if (routed) return routed;
  return payload.channel_name === 'directmessage' ? config.dmAgent || null : null;
}

// Markdown a file holds, as Slack mrkdwn: headings and bold become bold, a web link stays a link, any other
// link keeps its text. Everything else is shown as written.
function mrkdwn(markdown) {
  return esc(markdown).split('\n').map((line) => line
    .replace(/^#{1,6}\s+(.*)$/, '*$1*')
    .replace(/\*\*(.+?)\*\*/g, '*$1*')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<$2|$1>')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')).join('\n');
}

// Text as sections of at most SECTION_CHARS each, cut at a line end where one is near.
function sections(text) {
  const blocks = [];
  let rest = text.trim();
  while (rest) {
    let cut = rest.length <= SECTION_CHARS ? rest.length : rest.lastIndexOf('\n', SECTION_CHARS);
    if (cut < SECTION_CHARS / 2) cut = Math.min(rest.length, SECTION_CHARS);
    blocks.push(section(rest.slice(0, cut)));
    rest = rest.slice(cut).trim();
  }
  return blocks;
}

function fileText(file) {
  try { return fs.readFileSync(file, 'utf8'); } catch (error) { return error.code === 'ENOENT' ? null : `Cannot read ${file}: ${error.message}`; }
}

// What the installer recorded in agent.json: each file's name by kind, and the packs.
function installed(home) {
  let record;
  try { record = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8')); } catch { return null; }
  const names = Object.fromEntries(KINDS.map(([kind]) => [kind, []]));
  for (const component of Object.values(record.components || {})) {
    for (const [name, file] of Object.entries(component.selected || {})) names[file.method]?.push(name);
  }
  for (const list of Object.values(names)) list.sort();
  return { packs: Array.isArray(record.packs) ? record.packs : [], names };
}

// How long ago a moment was, in the largest whole unit.
function ago(ms, now) {
  const minutes = Math.max(0, Math.round((now - ms) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  return hours < 48 ? `${hours} h ago` : `${Math.round(hours / 24)} days ago`;
}

function cut(text, chars) {
  const value = String(text ?? '');
  return value.length > chars ? `${value.slice(0, chars - 1)}…` : value;
}

// A conversation's thread in Slack, or words saying it has none yet.
function threadLink(store, key) {
  const row = store.getConversation(key);
  return row?.channel && row.root_ts ? `<https://app.slack.com/archives/${row.channel}/p${row.root_ts.replace('.', '')}|thread>` : 'no thread yet';
}

function castLaunches() {
  const latest = new Map(readHandles().map((row) => [`${row.pid}:${row.start}`, row]));
  const rows = [...latest.values()];
  const starts = procStarts(rows.filter((row) => row.start != null).map((row) => row.pid));
  return rows.map((row) => ({ ...row, alive: row.start != null && starts.get(row.pid) === row.start }));
}

// A timer's next fire in its own zone; a timer kept at a fixed offset (`fixed`, `Z`, `-03:00`) is shown in UTC.
function when(ms, timeZone) {
  if (ms == null) return 'not scheduled';
  const format = (zone) => new Intl.DateTimeFormat('en-GB', {
    timeZone: zone, day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(ms));
  try { return `${format(timeZone)} (${timeZone})`; } catch { return `${format('UTC')} (UTC)`; }
}

const BODY = {
  overview(agent) {
    const head = section(`*${esc(agent.externalName || agent.name)}*  (${esc(agent.name)})\n${esc(agent.description) || '_No description._'}`);
    if (agent.avatar && /^https:\/\//.test(agent.avatar)) head.accessory = { type: 'image', image_url: agent.avatar, alt_text: agent.externalName || agent.name };
    const fields = [['Harness', agent.harness], ['Model', agent.model], ['Effort', agent.effort], ['Voice', agent.voice || 'none']];
    return [head, { type: 'section', fields: fields.map(([label, value]) => ({ type: 'mrkdwn', text: `*${label}*\n${esc(value)}` })) }];
  },
  installed(agent) {
    const record = installed(agent.home);
    if (!record) return [section('agent.json cannot be read.')];
    const lines = [`*Packs:* ${record.packs.map(esc).join(', ') || 'none'}`];
    for (const [kind, label] of KINDS) lines.push(`*${label}:* ${record.names[kind].map(esc).join(', ') || 'none'}`);
    return sections(lines.join('\n\n'));
  },
  prompt(agent) {
    return [...sections(mrkdwn(agent.prompt)), context(`${esc(agent.home)}/prompt.md`)];
  },
  board(agent) {
    const text = fileText(boardPath(agent.home));
    return text == null ? [section('This agent has no board.')] : [...sections(mrkdwn(text)), context(esc(boardPath(agent.home)))];
  },
  timers(agent, store) {
    if (!store) return [section('This agent has no Ignite store, so it has no timers.')];
    // Timers that are on come first, soonest first; timers that are off follow.
    const rows = store.listSchedules().sort((a, b) => (b.enabled - a.enabled) || ((a.next_at ?? Infinity) - (b.next_at ?? Infinity)));
    if (!rows.length) return [section('No timers.')];
    return sections(rows.map((row) => [
      `*${esc(row.subject || row.note || row.id)}*${row.enabled ? '' : '  _(off)_'}`,
      `Next: ${esc(when(row.next_at, row.timezone))} · ${esc(row.cadence)}${row.check_tool ? ` · check: ${esc(row.check_tool)}` : ''}`,
      ...(row.subject && row.note ? [esc(row.note)] : []),
    ].join('\n')).join('\n\n'));
  },
  tasks(agent, store, { now }) {
    if (!store) return [section('This agent has no Ignite store, so it has no tasks.')];
    const run = store.liveRun();
    const head = run
      ? `*Running now* in a ${threadLink(store, run.conversation_key)} · ${esc(run.launch_snapshot?.model || '?')} ${esc(run.launch_snapshot?.effort || '')} · started ${ago(run.started_at, now)}`
      : '*Running now:* nothing';
    const open = store.listWork().filter((work) => OPEN_WORK[work.state])
      .sort((a, b) => (Number(b.conversation_key === run?.conversation_key) - Number(a.conversation_key === run?.conversation_key)) || (b.updated_at - a.updated_at));
    const tasks = open.map((work) => {
      const notes = store.listNotes(work.conversation_key, NOTES_SHOWN);
      return section([
        `*${OPEN_WORK[work.state]}*${work.conversation_key === run?.conversation_key ? ' · running' : ''} · ${threadLink(store, work.conversation_key)} · updated ${ago(work.updated_at, now)}`,
        esc(cut(work.summary || 'No summary yet.', 900)),
        ...(work.next_step ? [`_Next:_ ${esc(cut(work.next_step, 400))}`] : []),
        ...((work.workers || []).length ? [`_Workers:_ ${work.workers.map((w) => `${esc(w.ref)} (${esc(cut(w.kind, 80))})`).join(', ')}`] : []),
        ...notes.map((note) => `• ${esc(note.text)} _(${ago(note.created_at, now)})_`),
      ].join('\n'));
    });
    return [section(head), ...(tasks.length ? tasks : [section('No open tasks.')])];
  },
  subagents(agent, store, { launches, now }) {
    const mine = launches().filter((row) => row.launcher && path.resolve(row.launcher) === path.resolve(agent.home))
      .sort((a, b) => (Number(b.alive) - Number(a.alive)) || (b.t0 - a.t0));
    const alive = mine.filter((row) => row.alive);
    const ended = mine.filter((row) => !row.alive).slice(0, ENDED_SHOWN);
    const line = (row) => [
      `*${esc(row.launched ? path.basename(row.launched) : row.tag || 'worker')}* · ${esc(row.harness)} ${esc(row.model)} · started ${ago(row.t0, now)}`,
      esc(row.task || 'No task recorded.'),
    ].join('\n');
    return [
      section(alive.length ? `*Running* (${alive.length})\n\n${alive.map(line).join('\n\n')}` : '*Running:* none'),
      ...(ended.length ? sections(`*Ended* (last ${ended.length} of the past 7 days)\n\n${ended.map(line).join('\n\n')}`) : []),
      context('Sub-agents launched through cast in this agent\'s turns. Sub-agents a harness starts inside itself are not recorded.'),
    ];
  },
  payments(agent, store, { gate }) {
    if (!gate) return [section('Payments are not set up here: Ignite\'s config has no payments section.')];
    const slug = path.basename(agent.home);
    const pending = gate.pending().filter((row) => row.agent === slug);
    const decided = gate.list({ agent: slug, limit: DECIDED_SHOWN + pending.length }).filter((row) => row.state !== 'pending').slice(0, DECIDED_SHOWN);
    return [
      section(`*Waiting for you* (${pending.length})`),
      ...(pending.length ? pending.flatMap((row) => promptBlocks(gate, row)) : [context('No payment of this agent waits for you.')]),
      { type: 'divider' },
      section(`*Decided* (last ${decided.length})`),
      ...(decided.length ? decided.flatMap((row) => promptBlocks(gate, row)) : [context('None yet.')]),
      context('Settings and every agent\'s payments: /payments. External message approvals will show here once Ignite has a message gate.'),
    ];
  },
  docs(agent, store, { workspace, channel, now }) {
    const name = esc(agent.externalName || agent.name);
    const open = store && openDocument(store);
    const docs = store && workspace ? recentDocs(store, workspace) : [];
    const head = section(open
      ? `*In the canvas:* \`${esc(open.path)}\` (opened ${ago(open.openedAt, now)}). Edit it there, then Save canvas to keep your edits as a file ${name} brings into the document.`
      : '*In the canvas:* nothing yet.');
    if (open && channel) head.accessory = { type: 'button', action_id: SAVE_DOC, value: open.path, text: plain('Save canvas') };
    const saves = pendingSaves(agent.home).map((one) => `• \`${esc(one.file)}\` from \`${esc(one.source || '?')}\`${one.savedAt ? `, saved ${ago(Date.parse(one.savedAt), now)}` : ''}`);
    const rows = docs.map((doc, i) => ({
      ...section(`\`${esc(doc.path)}\`\n_from a turn ${ago(doc.at, now)}_`),
      ...(channel ? { accessory: { type: 'button', action_id: `${OPEN_DOC}_${i}`, value: doc.path, text: plain('Open in canvas') } } : {}),
    }));
    return [
      head,
      ...(saves.length ? [section(`*Saved, not yet brought in* (${saves.length}): ask ${name} to bring them into their documents.\n${saves.join('\n')}`)] : []),
      ...(channel ? [] : [context(`Documents open in the agent's own channel canvas; ${name} answers in direct messages, so opening is not available here.`)]),
      ...(rows.length ? rows : [context('No Markdown document in this agent\'s recent turn outputs.')]),
      context('One canvas per channel: opening a document replaces the one in the canvas, never while it holds edits not yet saved.'),
    ];
  },
};

// One row of tab buttons; each button's value is the tab it opens. `row` keeps action ids unique per row.
function tabButtons(row, tabs) {
  return {
    type: 'actions',
    elements: tabs.map((tab) => ({
      type: 'button',
      action_id: `${ACTION}_${row}_${tab.id}`,
      value: tab.id,
      text: plain(tab.label),
      ...(tab.selected ? { style: 'primary' } : {}),
    })),
  };
}

function agentView({ slug, home, store, tab, gate = null, workspace = null, channel = null, notice = null, launches = castLaunches, now = Date.now() }) {
  const current = TABS.find((t) => t.id === tab) || TABS[0];
  const read = readAgent(home);
  const groups = GROUPS.map((group) => ({ id: TABS.find((t) => t.group === group).id, label: group, selected: group === current.group }));
  const subTabs = TABS.filter((t) => t.group === current.group).map((t) => ({ ...t, selected: t === current }));
  const nav = [tabButtons('group', groups), tabButtons('tab', subTabs), { type: 'divider' }];
  const body = read.agent ? [...(notice ? [context(notice)] : []), ...BODY[current.id](read.agent, store, { gate, workspace, channel, launches, now })] : [section(`This agent cannot be read: ${esc(read.why)}`)];
  const room = MAX_BLOCKS - nav.length;
  const blocks = body.length > room ? [...body.slice(0, room - 1), context('Cut here: Slack shows at most 100 blocks.')] : body;
  const name = read.agent?.externalName || slug;
  return modal(VIEW, name.slice(0, TITLE_CHARS), [...nav, ...blocks], { metadata: slug });
}

function createAgentPanel({ slack, config, store, gate = () => null, log = () => {}, launches = castLaunches, now = Date.now } = {}) {
  function note(fields) {
    try { log({ event: 'agent-panel', ...fields }); } catch { /* the panel never fails on a log */ }
  }

  // The channel the config routes to the agent: where its canvas is. The direct-message agent has none.
  function channelOf(slug) {
    return Object.entries(config().routes || {}).find(([, routed]) => routed === slug)?.[0] || null;
  }

  function view(slug, tab, notice = null) {
    return agentView({
      slug, home: agentHome(config(), slug), store: store(slug), tab, gate: gate(),
      workspace: config().workspace, channel: channelOf(slug), notice, launches, now: now(),
    });
  }

  // The owner's Open in canvas: only a document the Docs tab lists, into the agent's channel canvas.
  async function openFromPanel(slug, wanted) {
    const db = store(slug);
    const channel = channelOf(slug);
    if (!db || !channel || !recentDocs(db, config().workspace).some((doc) => doc.path === wanted)) return 'That document is not in the list any more. Nothing changed.';
    try {
      const result = await openDoc({ slack: slack(), store: db, workspace: config().workspace, channel, path: wanted });
      if (result.opened) return `Opened \`${esc(wanted)}\` in this channel's canvas: <https://app.slack.com/docs/${config().slack.team}/${result.canvasId}|open it>.`;
      if (result.refused === 'edited') return `Not opened: \`${esc(result.path)}\` was edited in the canvas since it was opened or last saved. Save canvas first, then open again.`;
      return 'Not opened: this channel\'s canvas holds something Ignite did not open. Ask the agent to replace it.';
    } catch (error) {
      note({ action: 'open-failed', message: error.message });
      return `Could not open \`${esc(wanted)}\`: ${esc(error.message)}. Nothing in the canvas changed.`;
    }
  }

  // The owner's Save canvas: the edited canvas becomes a file in the agent's output/ignite/canvas/.
  async function saveFromPanel(slug) {
    const db = store(slug);
    if (!db || !channelOf(slug)) return 'Nothing to save here. Nothing changed.';
    try {
      const result = await saveDoc({ slack: slack(), store: db, home: agentHome(config(), slug), now: now() });
      if (!result) return 'No document is open in the canvas. Nothing changed.';
      if (!result.saved) return `Nothing to save: the canvas of \`${esc(result.source)}\` is unchanged since it was opened or last saved.`;
      return `Saved your canvas edits to \`${esc(result.saved)}\` in the agent's folder. Ask the agent to bring them into \`${esc(result.source)}\`.${result.comments ? ` The canvas has ${result.comments} comments; their text stays in the canvas.` : ''}`;
    } catch (error) {
      note({ action: 'save-failed', message: error.message });
      return `Could not save the canvas: ${esc(error.message)}. Nothing changed.`;
    }
  }

  function ack(type, payload = {}) {
    if (type !== 'slash_commands' || payload.command !== COMMAND) return null;
    if (!isOwner(config(), payload)) return { text: 'Only the owner can open /agent. Nothing changed.' };
    return agentOf(config(), payload) ? null : { text: 'No agent answers in this channel. Type /agent in an agent\'s channel, or in the app\'s direct messages.' };
  }

  async function handle(type, payload = {}) {
    try {
      if (type === 'slash_commands' && payload.command === COMMAND) {
        const slug = agentOf(config(), payload);
        if (!isOwner(config(), payload) || !slug) return;
        await slack().openView(payload.trigger_id, view(slug, TABS[0].id));
        return;
      }
      const act = payload.actions?.[0];
      if (type !== 'interactive' || payload.type !== 'block_actions' || payload.view?.callback_id !== VIEW) return;
      if (![ACTION, OPEN_DOC, SAVE_DOC].some((prefix) => act?.action_id?.startsWith(prefix))) return;
      if (!isOwner(config(), payload)) {
        note({ action: 'refused', who: payload.user?.id || null });
        return;
      }
      const slug = payload.view.private_metadata;
      if (act.action_id === SAVE_DOC) {
        await slack().updateView(payload.view.id, view(slug, 'docs', await saveFromPanel(slug)));
        return;
      }
      if (act.action_id.startsWith(OPEN_DOC)) {
        const notice = await openFromPanel(slug, act.value);
        await slack().updateView(payload.view.id, view(slug, 'docs', notice));
        return;
      }
      await slack().updateView(payload.view.id, view(slug, act.value));
    } catch (error) {
      note({ action: 'failed', message: error.message });
    }
  }

  function redraw(panel) {
    return panel?.callback_id === VIEW ? view(panel.private_metadata, 'payments') : null;
  }

  return { ack, handle, redraw };
}

module.exports = { createAgentPanel, agentView, agentOf, castLaunches, TABS };
