'use strict';

// Launching an agent by its agent folder.
//   -ig AGENT   an agent folder. AGENT is a name, looked up as `.rbtv/agents/<name>/` from the
//               current folder upward, or a path to the folder (a value with `/`, or `.` or `..`).
//               agent.json gives harness, model and effort; agent.md, without its frontmatter, is
//               the system prompt; the folder is the working folder.
//   -rg FILE    a one-off agent that is not installed: the body of FILE (frontmatter ignored) is
//               the system prompt, and the launch folder is the usual one.
// Both ride the ordinary launch. spark reads the same files through the readers below.

const fs = require('fs');
const path = require('path');

const AGENT_MD = 'agent.md';
const AGENT_JSON = 'agent.json';

// An agent file's body: what follows its leading `---` block.
function agentBody(text) {
  const m = text.match(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/);
  return (m ? text.slice(m[0].length) : text).replace(/^(?:\r?\n)+/, '');
}

// A value is a path when it has a slash or is `.` or `..`; any other value is a name.
function isPath(value) {
  return value.includes('/') || value === '.' || value === '..';
}

// The agent folder a value names, or null when neither agent file is there. A path is taken as
// given; a name is looked up under `.rbtv/agents/` from `from` upward. A folder holding either file
// counts, so a folder with one file missing is named as broken rather than skipped.
function findAgentHome(value, from) {
  const holds = (home) => fs.existsSync(path.join(home, AGENT_MD)) || fs.existsSync(path.join(home, AGENT_JSON));
  if (isPath(value)) {
    const home = path.resolve(from, value);
    return holds(home) ? home : null;
  }
  for (let dir = path.resolve(from); ; dir = path.dirname(dir)) {
    const home = path.join(dir, '.rbtv', 'agents', value);
    if (holds(home)) return home;
    if (path.dirname(dir) === dir) return null;
  }
}

// The agent in `home`: its launch values and standing prompt, or the problem that stops a launch.
// problem 'launch' = agent.json is missing, unreadable or names no harness or model;
// problem 'prompt' = agent.md is missing.
function readAgent(home) {
  const mdPath = path.join(home, AGENT_MD);
  const jsonPath = path.join(home, AGENT_JSON);
  if (!fs.existsSync(jsonPath)) return { problem: 'launch', why: `${jsonPath} is missing` };
  let values;
  try { values = JSON.parse(fs.readFileSync(jsonPath, 'utf8')); } catch (e) {
    return { problem: 'launch', why: `${jsonPath} cannot be read: ${e.message}` };
  }
  if (!values || typeof values.harness !== 'string' || typeof values.model !== 'string') {
    return { problem: 'launch', why: `${jsonPath} names no harness or model` };
  }
  if (!fs.existsSync(mdPath)) return { problem: 'prompt', why: `${mdPath} is missing` };
  const agent = {
    home,
    harness: values.harness,
    model: values.model,
    effort: values.effort ?? null,
    prompt: agentBody(fs.readFileSync(mdPath, 'utf8')),
  };
  return { agent };
}

// The installed agent -ig names, read for launch. A refusal stops here.
function installedAgent(value, fail) {
  const home = findAgentHome(value, process.cwd());
  if (!home) {
    const looked = isPath(value)
      ? `looked for ${path.join(path.resolve(value), AGENT_JSON)}\nNothing changed.\ncheck the path, or look up a name: rbtv agent list`
      : `looked for .rbtv/agents/${value}/agent.json from the current folder upward\nNothing changed.\nlook up a name: rbtv agent list`;
    fail(`refused: no installed agent '${value}' was found\n${looked}`);
  }
  const read = readAgent(home);
  if (read.problem === 'launch') {
    fail(`refused: the launch values of '${value}' are unreadable\n${read.why}\nNothing changed.\nrestore that file, then run the same command again`);
  }
  if (read.problem === 'prompt') {
    fail(`refused: the agent '${value}' has no agent.md\n${read.why}\nNothing changed.\nrestore that file, then run the same command again`);
  }
  return read.agent;
}

// Pull -ig / -rg out of argv, leaving the ordinary launch arguments.
function takeAgentFlags(argv, fail) {
  const rest = [];
  const out = { installed: null, file: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '-ig' || a === '-rg') {
      const val = argv[i + 1];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      i += 1;
      if (a === '-ig') out.installed = val;
      else out.file = val;
    } else rest.push(a);
  }
  if (out.installed && out.file) fail('refused: -ig and -rg are mutually exclusive — pass exactly one');
  return { argv: rest, ...out };
}

// The system prompt a one-off agent file stands for.
function agentFilePrompt(flag, fail) {
  const file = path.resolve(process.cwd(), flag);
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) { fail(`refused: cannot read the agent file ${file}: ${e.message}`); }
  return { text: agentBody(text) };
}

module.exports = { agentBody, isPath, findAgentHome, readAgent, installedAgent, takeAgentFlags, agentFilePrompt };
