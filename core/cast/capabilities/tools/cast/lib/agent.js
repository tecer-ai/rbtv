'use strict';

// Launching an agent by its agent folder.
//   --agent NAME   an agent folder. AGENT is a name, looked up as `.rbtv/agents/<name>/` from the
//               current folder upward, or a path to the folder (a value with `/`, or `.` or `..`).
//               agent.json gives harness, model and effort; the body of prompt.md is the system
//               prompt, and a leading `---` block, when present, is ignored; the folder is the
//               working folder. With neither -p nor -f, task.md in the folder is the task.
//   --rogue PROMPT-FILE  a rogue agent with no folder: the body of the file (frontmatter ignored) is
//               the system prompt, and the launch folder is the usual one.
// Both ride the ordinary launch. This file is the one place that knows where an agent's folder
// is and how its record is read: spark, lib/agent-list.js and Ignite all use the functions below.

const fs = require('fs');
const path = require('path');

const PROMPT_MD = 'prompt.md';
// The task of an agent launched with neither -p nor -f.
const TASK_MD = 'task.md';
const AGENT_JSON = 'agent.json';
// The prompt file's old name: read by nothing, named only in the refusal for a folder that still holds it.
const OLD_PROMPT_MD = 'agent.md';

// An agent file's body: what follows its leading `---` block.
function agentBody(text) {
  const m = text.match(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/);
  return (m ? text.slice(m[0].length) : text).replace(/^(?:\r?\n)+/, '');
}

// A value is a path when it has a slash or a backslash, or is `.` or `..`; any other value is a
// name. No name holds either character, on any system.
function isPath(value) {
  return value.includes('/') || value.includes('\\') || value === '.' || value === '..';
}

// Where the agents of the installation at `root` live, and the folder of one of them.
function agentsFolder(root) {
  return path.join(root, '.rbtv', 'agents');
}

function agentHomeIn(root, name) {
  return path.join(agentsFolder(root), name);
}

// A folder holding either agent file counts as an agent folder, so a folder with one file missing
// is named as broken rather than skipped.
function holdsAgentFile(home) {
  return fs.existsSync(path.join(home, PROMPT_MD)) || fs.existsSync(path.join(home, AGENT_JSON));
}

// An agent folder holds both files: only such a folder can be run.
function isAgentFolder(home) {
  return fs.existsSync(path.join(home, PROMPT_MD)) && fs.existsSync(path.join(home, AGENT_JSON));
}

// The first value `pick` returns for a folder, from `from` upward, or null.
function upward(from, pick) {
  for (let dir = path.resolve(from); ; dir = path.dirname(dir)) {
    const found = pick(dir);
    if (found) return found;
    if (path.dirname(dir) === dir) return null;
  }
}

function isFolder(folder) {
  return fs.existsSync(folder) && fs.statSync(folder).isDirectory();
}

// The agent folders directly inside `folder`, by name.
function agentHomesIn(folder) {
  if (!isFolder(folder)) return [];
  return fs.readdirSync(folder).sort().map((name) => path.join(folder, name)).filter(holdsAgentFile);
}

// The agents `--target FOLDER` names: the one place that reads that option, for cast, spark and
// rbtv. FOLDER is one of three things, tried in this order:
//   an installation (it holds `.rbtv/`)   the agents under its `.rbtv/agents/`
//   an agent folder                       that one agent
//   a folder that holds agent folders     those agents
// Returns {folder, homes}, `folder` being where the agents were taken from, or {problem} when
// FOLDER is none of the three.
function targetAgents(target, from) {
  const given = path.resolve(from, target);
  if (!isFolder(given)) return { problem: `${given} is not a folder` };
  if (isFolder(path.join(given, '.rbtv'))) {
    const folder = agentsFolder(given);
    return { folder, homes: agentHomesIn(folder) };
  }
  if (holdsAgentFile(given)) return { folder: given, homes: [given] };
  const homes = agentHomesIn(given);
  if (homes.length) return { folder: given, homes };
  return { problem: `${given} is not an installation (it holds no .rbtv/), is not an agent folder (it holds no ${PROMPT_MD} or ${AGENT_JSON}), and holds no agent folder` };
}

// The agent folders a list shows: those `target` names, else those of the nearest `.rbtv/agents/`
// folder from `from` upward ({folder: null, homes: []} when there is none).
function agentHomes(from, target = null) {
  if (target) return targetAgents(target, from);
  const folder = upward(from, (dir) => (isFolder(agentsFolder(dir)) ? agentsFolder(dir) : null));
  return { folder, homes: agentHomesIn(folder ?? '') };
}

// The agent folder a value names, or null when neither agent file is there. A path is taken as
// given; a name is looked up among `homes` (the agents of a --target) when given, else under
// `.rbtv/agents/` from `from` upward.
function findAgentHome(value, from, homes = null) {
  if (isPath(value)) {
    const home = path.resolve(from, value);
    return holdsAgentFile(home) ? home : null;
  }
  if (homes) return homes.find((home) => path.basename(home) === value) ?? null;
  return upward(from, (dir) => {
    const home = agentHomeIn(dir, value);
    return holdsAgentFile(home) ? home : null;
  });
}

// Why an agent folder without its prompt file cannot be launched. A folder that still holds the
// file under its old name gets the rename command.
function promptMissing(home) {
  const missing = `${path.join(home, PROMPT_MD)} is missing.`;
  if (!fs.existsSync(path.join(home, OLD_PROMPT_MD))) return missing;
  return `${missing} This folder still has ${OLD_PROMPT_MD}, the old name of the prompt file. If another machine already renamed it, pull first; otherwise rename it with: git mv ${OLD_PROMPT_MD} ${PROMPT_MD} (inside ${home}), and change any .gitignore line that names ${OLD_PROMPT_MD}.`;
}

// The agent in `home`: its launch values, voice, standing prompt, description and whether it is an
// Ignite agent (its `ignite` pack is on, which `ignite connect` does), or the problem that stops a
// launch.
// problem 'launch' = agent.json is missing, unreadable, names no harness, model or effort, or
//                    gives the effort as a number where the record holds the model's own word;
// problem 'prompt' = prompt.md is missing.
function readAgent(home) {
  const mdPath = path.join(home, PROMPT_MD);
  const jsonPath = path.join(home, AGENT_JSON);
  if (!fs.existsSync(jsonPath)) return { problem: 'launch', why: `${jsonPath} is missing` };
  let values;
  try { values = JSON.parse(fs.readFileSync(jsonPath, 'utf8')); } catch (e) {
    return { problem: 'launch', why: `${jsonPath} cannot be read: ${e.message}` };
  }
  const text = (value) => typeof value === 'string' && value.trim() !== '';
  if (!values || !text(values.harness) || !text(values.model) || !text(values.effort)) {
    return { problem: 'launch', why: `${jsonPath} names no harness, model or effort` };
  }
  if (/^\d+$/.test(values.effort)) {
    return { problem: 'launch', why: `${jsonPath} gives effort as the number ${values.effort}; it holds the model's own effort word` };
  }
  if (!fs.existsSync(mdPath)) return { problem: 'prompt', why: promptMissing(home) };
  const agent = {
    home,
    harness: values.harness,
    model: values.model,
    effort: values.effort,
    voice: values.voice ?? null,
    description: typeof values.description === 'string' ? values.description : '',
    ignite: Array.isArray(values.packs) && values.packs.includes('ignite'),
    prompt: agentBody(fs.readFileSync(mdPath, 'utf8')),
  };
  return { agent };
}

// cast's refusal for a --target that names no agents.
function targetRefusal(target, problem) {
  return `refused: --target ${target} names no rbtv agents\n${problem}\nNothing was listed.\ncast list -h`;
}

// The rbtv agent --agent names, read for launch. A refusal stops here. `target` is the --target
// of `cast list --agent NAME`: the name is then looked up among that folder's agents.
function rbtvAgent(value, fail, target = null) {
  let homes = null;
  if (target) {
    if (isPath(value)) {
      fail(`refused: --target goes with a name, and '${value}' is a path\na path already names the agent folder\nNothing was listed.\ncast list --agent ${value}`);
    }
    const found = targetAgents(target, process.cwd());
    if (found.problem) fail(targetRefusal(target, found.problem));
    homes = found.homes;
  }
  const home = findAgentHome(value, process.cwd(), homes);
  if (!home) {
    let looked;
    if (target) {
      looked = `looked for an agent folder named ${value} in --target ${target}\nNothing was listed.\nlook up a name: cast list --agents --target ${target}`;
    } else if (isPath(value)) {
      looked = `looked for ${path.join(path.resolve(value), AGENT_JSON)}\nNothing changed.\ncheck the path, or look up a name: cast list --agents`;
    } else {
      looked = `looked for .rbtv/agents/${value}/agent.json from the current folder upward\nNothing changed.\nlook up a name: cast list --agents`;
    }
    fail(`refused: no rbtv agent '${value}' was found\n${looked}`);
  }
  const read = readAgent(home);
  if (read.problem === 'launch') {
    fail(`refused: the launch values of '${value}' are unreadable\n${read.why}\nNothing changed.\nrestore that file, then run the same command again`);
  }
  if (read.problem === 'prompt') {
    fail(`refused: the agent '${value}' has no prompt.md\n${read.why}\nNothing changed.\nrestore that file, then run the same command again`);
  }
  return read.agent;
}

// The task of an rbtv agent launched with neither -p nor -f: the text of task.md in its folder,
// read as -f reads a file. A folder without the file is refused.
function agentTask(agent, fail) {
  const file = path.join(agent.home, TASK_MD);
  if (!fs.existsSync(file)) {
    fail(`refused: no task: pass -p TEXT or -f FILE, or write ${TASK_MD} in ${agent.home}\nNothing changed.`);
  }
  return fs.readFileSync(file, 'utf8');
}

// Pull --agent / --rogue out of argv, leaving the ordinary launch arguments.
function takeAgentFlags(argv, fail) {
  const rest = [];
  const out = { rbtv: null, file: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--agent' || a === '--rogue') {
      const val = argv[i + 1];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      i += 1;
      if (a === '--agent') out.rbtv = val;
      else out.file = val;
    } else rest.push(a);
  }
  if (out.rbtv && out.file) fail('refused: --agent and --rogue are mutually exclusive — pass exactly one');
  return { argv: rest, ...out };
}

// The system prompt a rogue agent file stands for.
function agentFilePrompt(flag, fail) {
  const file = path.resolve(process.cwd(), flag);
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) { fail(`refused: cannot read the agent file ${file}: ${e.message}`); }
  return { text: agentBody(text) };
}

module.exports = {
  PROMPT_MD, TASK_MD, AGENT_JSON, agentBody, isPath, agentsFolder, agentHomeIn, holdsAgentFile, isAgentFolder, targetAgents, agentHomes, findAgentHome,
  readAgent, rbtvAgent, agentTask, targetRefusal, takeAgentFlags, agentFilePrompt, promptMissing,
};
