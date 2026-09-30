'use strict';

// Launching an agent by its agent file.
//   -ig AGENT   an INSTALLED agent: its folder `<installation>/.rbtv/agents/<AGENT>/` is the
//               working folder and its `agent.md` is the system prompt.
//   -rg FILE    a one-off agent that is not installed: the body of FILE (frontmatter ignored) is
//               the system prompt, and the launch folder is the usual one.
// Both ride the ordinary launch: harness, model and effort are given on the command line.

const fs = require('fs');
const path = require('path');

// The installed agent's folder: under `target` when given, else the nearest installation above `from`.
function findHome(name, from, target) {
  // Installed means launch.json exists (the installer writes it; remove takes it back).
  const has = (home) => fs.existsSync(path.join(home, 'launch.json')) && fs.existsSync(path.join(home, 'agent.md'));
  if (target) {
    const home = path.join(path.resolve(target), '.rbtv', 'agents', name);
    return has(home) ? home : null;
  }
  for (let dir = path.resolve(from); ; dir = path.dirname(dir)) {
    const home = path.join(dir, '.rbtv', 'agents', name);
    if (has(home)) return home;
    if (path.dirname(dir) === dir) return null;
  }
}

// An agent file's body: what follows its leading `---` block.
function agentBody(text) {
  const m = text.match(/^---\r?\n[\s\S]*?\r?\n---[ \t]*(?:\r?\n|$)/);
  return (m ? text.slice(m[0].length) : text).replace(/^(?:\r?\n)+/, '');
}

// Pull -ig / -rg / --target out of argv, leaving the ordinary launch arguments.
function takeAgentFlags(argv, fail) {
  const rest = [];
  const out = { installed: null, file: null, target: null };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '-ig' || a === '-rg' || a === '--target') {
      const val = argv[i + 1];
      if (val === undefined) fail(`refused: ${a} requires an argument`);
      i += 1;
      if (a === '-ig') out.installed = val;
      else if (a === '-rg') out.file = val;
      else out.target = val;
    } else rest.push(a);
  }
  if (out.installed && out.file) fail('refused: -ig and -rg are mutually exclusive — pass exactly one');
  if (out.target && !out.installed) fail('refused: --target only goes with -ig');
  return { argv: rest, ...out };
}

// The folder and system prompt an agent flag stands for.
function agentLaunch(flags, fail) {
  if (flags.installed) {
    const home = findHome(flags.installed, process.cwd(), flags.target);
    if (!home) {
      fail(`refused: no installed agent '${flags.installed}' was found\n`
        + `looked for .rbtv/agents/${flags.installed}/launch.json ${flags.target ? `under ${path.resolve(flags.target)}` : 'from the current folder upward'}\n`
        + 'install one: rbtv install agent add <agent file> --harness … --model … --effort …');
    }
    return { folder: home, system: { file: path.join(home, 'agent.md') } };
  }
  const file = path.resolve(process.cwd(), flags.file);
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) { fail(`refused: cannot read the agent file ${file}: ${e.message}`); }
  return { folder: null, system: { text: agentBody(text) } };
}

module.exports = { findHome, agentBody, takeAgentFlags, agentLaunch };
