'use strict';

// The rbtv agents a folder can launch by name: the one list of agents. `cast list --agents` shows it
// to an agent, `spark list` to a person, and `rbtv agent list` runs `cast list --agents`. The three
// print the same text, so a line that names a command names all three.
//   agentList(from)        the nearest `.rbtv/agents/` folder from `from` upward, and its agents
//   agentRow(agent)        an agent read by lib/agent.js as one row of the list
//   agentInFull(agent)     that row, with the packs and units the installer records in the agent
//   listLines(list)        the list as text: a table, or one labeled block per agent when the
//                          terminal is too narrow for the table
//   agentLines(row)        one agent as a labeled block with its whole description
//   runAgentList(agent, json)  what `cast list --agents | --agent NAME` prints
// A refusal is worded by the caller: cast, spark and rbtv each have their own form.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const { findAgentsFolder, holdsAgentFile, rbtvAgent, readAgent } = require('./agent');
const { spawnable } = require('./win-exec');

const LABELS = ['Name', 'Harness', 'Model', 'Effort', 'Ignite', 'Description'];
const LAST = LABELS.length - 1;
const GAP = 2;
// Below this many columns for the description, each agent is a labeled block instead.
const MIN_DESCRIPTION = 20;

// The kinds of unit the installer records in an agent, under the installer's own type names, and
// the label each is shown with. A pack is a named list of such units.
const KINDS = [['skill', 'Skills'], ['rule', 'Rules'], ['command', 'Commands'], ['mcp-server', 'MCP servers'],
  ['hook', 'Hooks']];
// The most rows one `rbtv list` call returns.
const PAGE = 100;

function agentRow(agent) {
  const { home, description, harness, model, effort, ignite } = agent;
  return { name: path.basename(home), description, harness, model, effort, ignite, home };
}

// The names in `units`, by kind: `{skill: [...], rule: [...], ...}`.
function byKind(units) {
  return Object.fromEntries(KINDS.map(([type]) => [type, units.filter((unit) => unit.type === type).map((unit) => unit.id)]));
}

// What is installed in the agent at `home`, under the names `rbtv show` takes: each pack that is on
// with the units it installs, then, by kind, the units installed outside a pack. Only the installer
// knows it, since it reads the catalog and what each pack lists, so this asks it:
// `rbtv list --installed --target HOME`. `problem` says why there is no answer.
function installedIn(home) {
  const rows = [];
  for (let offset = 0; ;) {
    const win = spawnable('rbtv', ['list', '--installed', '--target', home, '--type',
      ['pack', ...KINDS.map(([type]) => type)].join(','), '--limit', String(PAGE), '--offset', String(offset), '--json']);
    const res = spawnSync(win.cmd, win.args, { ...win.opts, encoding: 'utf8' });
    if (res.error) return { problem: 'rbtv is not on PATH.' };
    let page;
    try { page = JSON.parse(res.stdout); } catch { return { problem: '`rbtv list --installed` did not answer in JSON.' }; }
    if (!page.ok) return { problem: `rbtv refused: ${page.error?.message ?? 'no reason given'}` };
    rows.push(...page.units);
    offset += page.returned;
    if (!page.returned || offset >= page.total) break;
  }
  const units = rows.filter((row) => row.type !== 'pack');
  const listedBy = (pack) => new Set(pack.units ?? []);
  const packs = rows.filter((row) => row.type === 'pack');
  const inAPack = new Set(packs.flatMap((pack) => pack.units ?? []));
  return {
    installed: {
      pack: packs.map((pack) => ({ name: pack.id, ...byKind(units.filter((unit) => listedBy(pack).has(unit.id))) })),
      ...byKind(units.filter((unit) => !inAPack.has(unit.id))),
    },
  };
}

function agentInFull(agent) {
  const { installed = null, problem } = installedIn(agent.home);
  return { ...agentRow(agent), installed, ...(problem ? { installed_problem: problem } : {}) };
}

// Alphabetical by name. An agent that cannot be launched is a row with its problem.
function agentList(from) {
  const folder = findAgentsFolder(from);
  if (!folder) return { folder: null, agents: [] };
  const agents = fs.readdirSync(folder).sort()
    .map((name) => path.join(folder, name))
    .filter(holdsAgentFile)
    .map((home) => {
      const read = readAgent(home);
      return read.problem ? { name: path.basename(home), home, problem: read.why } : agentRow(read.agent);
    });
  return { folder, agents };
}

function cells(row) {
  return [row.name, row.harness, row.model, row.effort || 'none', row.ignite ? 'yes' : 'no', row.description];
}

// COLUMNS first, which a caller sets to choose a width; then the real terminal; then 100.
function terminalWidth() {
  const asked = Number.parseInt(process.env.COLUMNS, 10);
  if (asked > 0) return Math.max(10, asked);
  return process.stdout.columns || 100;
}

// `text` cut at a word boundary to fit `budget`, ending in an ellipsis.
function shorten(text, budget) {
  if (text.length <= budget) return text;
  const head = text.slice(0, budget - 1);
  const cut = head.lastIndexOf(' ');
  return `${(cut > 0 ? head.slice(0, cut) : head).replace(/[.,;:]+$/, '')}…`;
}

// `text` wrapped at spaces to `width`, after `indent`; every line after the first is indented two
// spaces more.
function wrap(text, width, indent = '') {
  const lines = [];
  let line = '';
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (line && line.length + 1 + word.length > width) {
      lines.push(line);
      line = `${indent}  ${word}`;
    } else line = line ? `${line} ${word}` : `${indent}${word}`;
  }
  return line ? [...lines, line] : lines;
}

// `Label: name, name` for each kind in `names`; with `all`, a kind with no name says `none`.
function kindTexts(names, all) {
  return KINDS.filter(([type]) => all || names[type].length)
    .map(([type, label]) => `${label}: ${names[type].join(', ') || 'none'}`);
}

// One agent as a labeled block. A row from agentInFull also gets its folder, what is installed in
// it, and how to read more about each name.
function agentLines(row, width = terminalWidth()) {
  const values = cells(row);
  const lines = LABELS.slice(0, LAST).map((label, i) => `${label}: ${values[i]}`);
  if (row.installed !== undefined) lines.push(`Folder: ${row.home}`);
  lines.push(...wrap(`${LABELS[LAST]}: ${values[LAST]}`, width));
  if (row.installed) {
    const packs = row.installed.pack;
    lines.push('', 'Installed in this agent, under the names rbtv show takes:');
    lines.push(packs.length ? 'Packs, each with what it installs:' : 'Packs: none');
    for (const pack of packs) {
      const texts = kindTexts(pack, false);
      lines.push(`  ${pack.name}`);
      for (const text of texts.length ? texts : ['nothing installed']) lines.push(...wrap(text, width, '    '));
    }
    lines.push('Outside a pack:');
    for (const text of kindTexts(row.installed, true)) lines.push(...wrap(text, width, '  '));
    // With the agent's folder as target, `rbtv show` answers for this agent; without it, for the
    // installation, where the same unit may not be installed.
    const target = /\s/.test(row.home) ? `"${row.home}"` : row.home;
    lines.push('', `More about a pack: rbtv show --pack NAME --target ${target}`,
      `More about any other name: rbtv show NAME --target ${target}`);
  } else if (row.installed_problem) {
    lines.push('', ...wrap(`Installed packs and units: not shown. ${row.installed_problem}`, width));
  }
  return lines;
}

function listLines({ folder, agents }, width = terminalWidth()) {
  if (!folder) return ['rbtv agents: 0', '', 'No .rbtv/agents/ folder was found from the current folder upward.'];
  const lines = [`rbtv agents: ${agents.length}`, `Folder: ${folder}`, ''];
  if (!agents.length) return [...lines, 'No agent found. An agent folder holds agent.md and agent.json.'];
  const ready = agents.filter((row) => !row.problem);
  for (const row of agents) if (row.problem) lines.push(`${row.name}: cannot be launched: ${row.problem}`);
  if (!ready.length) return lines;
  if (ready.length < agents.length) lines.push('');

  const table = ready.map(cells);
  const widths = LABELS.map((label, i) => Math.max(label.length, ...table.map((row) => row[i].length)));
  const budget = width - widths.slice(0, LAST).reduce((sum, w) => sum + w + GAP, 0);
  if (budget < MIN_DESCRIPTION) {
    ready.forEach((row, i) => lines.push(...(i ? [''] : []), ...agentLines(row, width)));
    return lines;
  }
  const line = (row) => row.map((cell, i) => (i === LAST ? shorten(cell, budget) : cell.padEnd(widths[i])))
    .join(' '.repeat(GAP)).trimEnd();
  lines.push(line(LABELS), ...table.map(line));
  if (table.some((row) => row[LAST].length > budget)) {
    lines.push('', 'One agent in full: cast list --agent NAME, spark list NAME or rbtv agent list NAME.');
  }
  return lines;
}

// `cast list --agents | --agent NAME`, once cast has read the arguments. `fail` comes from cast, as
// for the other functions of lib/agent.js.
function runAgentList(agent, json, fail) {
  const print = (value, lines) => process.stdout.write(json ? `${JSON.stringify(value)}\n` : `${lines.join('\n')}\n`);
  if (agent) {
    const row = agentInFull(rbtvAgent(agent, fail));
    print(row, agentLines(row));
  } else {
    const list = agentList(process.cwd());
    print(list, listLines(list));
  }
  process.exit(0);
}

module.exports = { agentList, agentInFull, listLines, agentLines, runAgentList };
