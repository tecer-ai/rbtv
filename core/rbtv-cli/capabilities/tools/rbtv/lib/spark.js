'use strict';

// rbtv spark <agent> — run an installed agent interactively.
//
// The agent is found by its folder, `<installation>/.rbtv/agents/<agent>/`, so a new agent
// needs no PATH change. Its harness, model and effort are read from `launch.json` at this
// moment (never cached), and the agent file goes to the harness as its standing prompt
// through `cast --headed`, the same channels every launch uses.

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const { RBTV_ROOT } = require('./catalog');
const { delegate } = require('./delegate');
const { refusal } = require('./render');

const CAST = path.join(RBTV_ROOT, 'core', 'cast', 'capabilities', 'tools', 'cast', 'cast.js');

// cast needs a first message to open the session; this one starts a conversation and waits.
const OPENING = 'You have just been started by your owner in an interactive terminal. '
  + 'Greet them in one line and wait for what they need.';

// The agent's folder: under `target` when given, else the nearest installation above `from`.
function findHome(name, from, target) {
  const has = (home) => fs.existsSync(path.join(home, 'launch.json'));
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

// `launch.json` holds the model's own effort word; cast takes its step number, 1-5.
function effortStep(launch, known) {
  const ladder = ((known[launch.harness] || {})[launch.model]) || [];
  const at = ladder.indexOf(launch.effort);
  return at >= 0 ? at + 1 : 1;
}

function castList() {
  const res = spawnSync(process.execPath, [CAST, 'list', '--json'], { encoding: 'utf8' });
  try { return JSON.parse(res.stdout); } catch { return {}; }
}

function castArgs(home, launch, known) {
  return [launch.harness, launch.model, String(effortStep(launch, known)), home,
    '--headed', '-S', path.join(home, 'agent.md'), '-p', OPENING];
}

function quote(arg) {
  return /^[\w@%+=:,./\\-]+$/.test(arg) ? arg : `"${arg.replace(/"/g, '\\"')}"`;
}

function spark(args, opts) {
  const flagsWithValue = new Set(['--target']);
  const positional = [];
  let target = null;
  let dry = false;
  let json = Boolean(opts && opts.json);
  for (let i = 0; i < args.length; i += 1) {
    if (flagsWithValue.has(args[i])) { target = args[i + 1]; i += 1; } else if (args[i] === '--dry-run') dry = true;
    else if (args[i] === '--json') json = true;
    else if (args[i] === '-h' || args[i] === '--help') {
      console.log('usage: rbtv spark <agent> [--target <workspace>] [--dry-run] [--json]\n'
        + 'Runs an installed agent interactively in its own folder, with its agent.md as the system prompt\n'
        + 'and its launch.json harness, model and effort.');
      return 0;
    } else if (args[i].startsWith('-')) {
      console.error(refusal({
        what: `\`${args[i]}\` is not a spark option`,
        why: 'spark takes one agent name and the options --target, --dry-run and --json.',
        fix: 'usage: rbtv spark <agent> [--target <workspace>] [--dry-run] [--json]',
      }));
      return 2;
    } else positional.push(args[i]);
  }
  if (positional.length !== 1) {
    console.error(refusal({
      what: 'spark needs exactly one agent name',
      why: `got ${positional.length}.`,
      fix: 'usage: rbtv spark <agent> [--target <workspace>] [--dry-run] [--json]. Install one with `rbtv install agent add`.',
    }));
    return 2;
  }
  const name = positional[0];
  const home = findHome(name, process.cwd(), target);
  if (!home) {
    console.error(refusal({
      what: `no installed agent \`${name}\` was found`,
      why: `looked for .rbtv/agents/${name}/launch.json ${target ? `under ${path.resolve(target)}` : 'from the current folder upward'}.`,
      fix: `install it with \`rbtv install agent add <agent file> --harness … --model … --effort …\`, or pass --target <workspace>.`,
    }));
    return 1;
  }
  let launch;
  try { launch = JSON.parse(fs.readFileSync(path.join(home, 'launch.json'), 'utf8')); } catch (err) {
    console.error(refusal({
      what: `the launch values of \`${name}\` are unreadable`,
      why: err.message,
      fix: `repair ${path.join(home, 'launch.json')} (harness, model, effort).`,
    }));
    return 1;
  }
  const argv = castArgs(home, launch, castList());
  if (dry) {
    if (json) console.log(JSON.stringify({ agent: name, home, cast: ['cast', ...argv] }));
    else console.log(`cast ${argv.map(quote).join(' ')}`);
    return 0;
  }
  const res = delegate({ prefix: ['spark'], target: CAST, exec: 'node' }, argv);
  if (res.message) console.error(res.message);
  return res.status;
}

module.exports = { spark, findHome, effortStep, castArgs };
