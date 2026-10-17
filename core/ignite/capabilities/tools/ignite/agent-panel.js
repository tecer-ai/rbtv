'use strict';

// The /agent panel: the owner types /agent in an agent's channel, or in the app's direct messages for
// config.dmAgent, and a modal shows that agent. Tab buttons redraw it in place: Configuration (Overview,
// Installed, Prompt) and State (Board, Timers). It reads the agent's agent.json, prompt.md, board file and
// schedule rows, and changes nothing.
//
// API
// createAgentPanel({ slack, config, store, log? }) → { ack(type, payload), handle(type, payload) }
//   slack() → the Slack client; config() → Ignite's config; store(slug) → that agent's Store, or null.
//   ack answers a /agent slash command at once: a refusal for anyone but the owner, or where no agent answers;
//   null otherwise, and for anything else. handle then opens the panel with the command's trigger_id, or, for a
//   tab button pressed inside the panel, redraws it with views.update. Both re-check the owner; anyone else's
//   button changes nothing. handle never rejects: a failed Slack call is logged as { event: 'agent-panel' }.
// agentView({ slug, home, store, tab }) → the panel's modal on one tab; an unknown tab shows the first.
// agentOf(config, payload) → the slug a slash command's channel answers to, or null.
// TABS — the tab ids, in order, each with its group and label.

const fs = require('fs');
const path = require('path');

const { readAgent } = require('../../../../cast/capabilities/tools/cast/lib/agent');
const { agentHome } = require('./config.js');
const { boardPath } = require('./board.js');
const { plain, section, context, esc, modal } = require('./blocks.js');
const { isOwner } = require('./payment-panel.js');

const COMMAND = '/agent';
const VIEW = 'agent_panel';
const ACTION = 'agent_tab';
const TABS = Object.freeze([
  { id: 'overview', group: 'Configuration', label: 'Overview' },
  { id: 'installed', group: 'Configuration', label: 'Installed' },
  { id: 'prompt', group: 'Configuration', label: 'Prompt' },
  { id: 'board', group: 'State', label: 'Board' },
  { id: 'timers', group: 'State', label: 'Timers' },
]);
const GROUPS = [...new Set(TABS.map((tab) => tab.group))];
// Slack's limits: a modal's title, the characters of a section, the blocks of a view.
const TITLE_CHARS = 24;
const SECTION_CHARS = 3000;
const MAX_BLOCKS = 100;
// The kinds of file the installer records in agent.json, by its method name, and the label each is shown with.
const KINDS = [['skill', 'Skills'], ['rule', 'Rules'], ['tool', 'Tools'], ['command', 'Commands']];

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

function agentView({ slug, home, store, tab }) {
  const current = TABS.find((t) => t.id === tab) || TABS[0];
  const read = readAgent(home);
  const groups = GROUPS.map((group) => ({ id: TABS.find((t) => t.group === group).id, label: group, selected: group === current.group }));
  const subTabs = TABS.filter((t) => t.group === current.group).map((t) => ({ ...t, selected: t === current }));
  const nav = [tabButtons('group', groups), tabButtons('tab', subTabs), { type: 'divider' }];
  const body = read.agent ? BODY[current.id](read.agent, store) : [section(`This agent cannot be read: ${esc(read.why)}`)];
  const room = MAX_BLOCKS - nav.length;
  const blocks = body.length > room ? [...body.slice(0, room - 1), context('Cut here: Slack shows at most 100 blocks.')] : body;
  const name = read.agent?.externalName || slug;
  return modal(VIEW, name.slice(0, TITLE_CHARS), [...nav, ...blocks], { metadata: slug });
}

function createAgentPanel({ slack, config, store, log = () => {} } = {}) {
  function note(fields) {
    try { log({ event: 'agent-panel', ...fields }); } catch { /* the panel never fails on a log */ }
  }

  function view(slug, tab) {
    return agentView({ slug, home: agentHome(config(), slug), store: store(slug), tab });
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
      if (!act?.action_id?.startsWith(ACTION)) return;
      if (!isOwner(config(), payload)) {
        note({ action: 'refused', who: payload.user?.id || null });
        return;
      }
      await slack().updateView(payload.view.id, view(payload.view.private_metadata, act.value));
    } catch (error) {
      note({ action: 'failed', message: error.message });
    }
  }

  return { ack, handle };
}

module.exports = { createAgentPanel, agentView, agentOf, TABS };
