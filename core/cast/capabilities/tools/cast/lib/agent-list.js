'use strict';

// The rbtv agents a folder can launch by name: the one list of agents. `cast list -rbtv` shows it
// to an agent, `spark list` to a person, and `rbtv agent list` runs `cast list -rbtv`. The three
// print the same text, so no line of it names the command that printed it.
//   agentList(from)        the nearest `.rbtv/agents/` folder from `from` upward, and its agents
//   agentRow(agent)        an agent read by lib/agent.js as one row of the list
//   listLines(list)        the list as text: a table, or one labeled block per agent when the
//                          terminal is too narrow for the table
//   agentLines(row)        one agent as a labeled block with its whole description
//   runAgentList(args)     the `cast list -rbtv [AGENT] [--json]` verb
// A refusal is worded by the caller: cast, spark and rbtv each have their own form.

const fs = require('fs');
const path = require('path');

const { findAgentsFolder, holdsAgentFile, rbtvAgent, readAgent } = require('./agent');

const LABELS = ['Name', 'Harness', 'Model', 'Effort', 'Ignite', 'Description'];
const LAST = LABELS.length - 1;
const GAP = 2;
// Below this many columns for the description, each agent is a labeled block instead.
const MIN_DESCRIPTION = 20;

function agentRow(agent) {
  const { home, description, harness, model, effort, ignite } = agent;
  return { name: path.basename(home), description, harness, model, effort, ignite, home };
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

// `text` wrapped at spaces to `width`; every line after the first is indented two spaces.
function wrap(text, width) {
  const lines = [];
  let line = '';
  for (const word of text.split(/\s+/).filter(Boolean)) {
    if (line && line.length + 1 + word.length > width) {
      lines.push(line);
      line = `  ${word}`;
    } else line = line ? `${line} ${word}` : word;
  }
  return line ? [...lines, line] : lines;
}

function agentLines(row, { folder = false, width = terminalWidth() } = {}) {
  const values = cells(row);
  const lines = LABELS.slice(0, LAST).map((label, i) => `${label}: ${values[i]}`);
  if (folder) lines.push(`Folder: ${row.home}`);
  return [...lines, ...wrap(`${LABELS[LAST]}: ${values[LAST]}`, width)];
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
    ready.forEach((row, i) => lines.push(...(i ? [''] : []), ...agentLines(row, { width })));
    return lines;
  }
  const line = (row) => row.map((cell, i) => (i === LAST ? shorten(cell, budget) : cell.padEnd(widths[i])))
    .join(' '.repeat(GAP)).trimEnd();
  lines.push(line(LABELS), ...table.map(line));
  if (table.some((row) => row[LAST].length > budget)) {
    lines.push('', 'Full description of one agent: add its name to this command.');
  }
  return lines;
}

// `cast list -rbtv [AGENT] [--json]`. `fail` and the help page come from cast, as for the other
// functions of lib/agent.js.
function runAgentList(args, fail, help) {
  let json = false;
  const named = [];
  for (const a of args) {
    if (a === '-h' || a === '--help') {
      process.stdout.write(`${help.join('\n')}\n`);
      process.exit(0);
    } else if (a === '--json') json = true;
    else if (a === '-models') {
      fail('refused: -models and -rbtv are two different lists\npass one of them\nNothing was listed.\ncast list -h');
    } else if (a.startsWith('-') && a !== '-rbtv') {
      fail(`refused: '${a}' is not a cast list option\ncast list takes -models or -rbtv [AGENT], and --json\nNothing was listed.\ncast list -h`);
    } else if (a !== '-rbtv') named.push(a);
  }
  if (named.length > 1) {
    fail(`refused: cast list -rbtv takes at most one agent, got ${named.length}\nNothing was listed.\ncast list -h`);
  }
  const print = (value, lines) => process.stdout.write(json ? `${JSON.stringify(value)}\n` : `${lines.join('\n')}\n`);
  if (named.length) {
    const row = agentRow(rbtvAgent(named[0], fail));
    print(row, agentLines(row, { folder: true }));
  } else {
    const list = agentList(process.cwd());
    print(list, listLines(list));
  }
  process.exit(0);
}

module.exports = { agentList, agentRow, listLines, agentLines, runAgentList };
