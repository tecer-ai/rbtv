#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const TOOL = path.join(__dirname, 'spark.js');
const SCRATCH_ROOT = '/tmp/claude-1000/-home-henri-ht-wkdir-second-brain/204266c9-ba58-4854-b838-016c8b55cc42/scratchpad';
const BASE = fs.existsSync(SCRATCH_ROOT) ? SCRATCH_ROOT : os.tmpdir();

const OPENING = 'You have just been started by your owner in an interactive terminal. '
  + 'Greet them in one line and wait for what they need.';

function mkFolder(name) {
  const dir = path.join(BASE, `spark-test-${name}-${process.pid}`);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

// A workspace with two agents: a name-found one and a path-found one, plus one with no agent.json.
const SCOUT_SAYS = 'Scouts the repository for the files a task needs and reports them with one line each. '
  + 'Triggered by a question about where something lives. Not for editing files.';
const root = mkFolder('root');
function writeAgent(folder, values) {
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(folder, 'agent.md'), '---\nname: scout\n---\nYou are Scout.\n');
  if (values) fs.writeFileSync(path.join(folder, 'agent.json'), JSON.stringify(values));
}
const scout = path.join(root, '.rbtv', 'agents', 'scout');
const drafter = path.join(root, 'plans', 'x', 'agents', 'drafter');
const half = path.join(root, '.rbtv', 'agents', 'half');
writeAgent(scout, { name: 'scout', description: SCOUT_SAYS, harness: 'codex', model: 'gpt-6.1-sol', effort: 'high', packs: ['ignite'] });
writeAgent(drafter, { name: 'drafter', harness: 'claude', model: 'sonnet-5-5', effort: 'medium' });
writeAgent(half, null);

// A `cast` on PATH that records its own argv. Launches go through it; nothing reaches a harness.
const shimDir = mkFolder('shim');
const shimOut = path.join(shimDir, 'argv.json');
fs.writeFileSync(path.join(shimDir, 'cast.js'),
  "require('fs').writeFileSync(process.env.SHIM_OUT, JSON.stringify(process.argv.slice(2)));\n");
fs.writeFileSync(path.join(shimDir, 'cast'), `#!/bin/sh\nexec "${process.execPath}" "$(dirname "$0")/cast.js" "$@"\n`, { mode: 0o755 });
fs.writeFileSync(path.join(shimDir, 'cast.cmd'), `@"${process.execPath}" "%~dp0cast.js" %*\r\n`);
const fullPath = `${shimDir}${path.delimiter}${process.env.PATH}`;

function spark(args, { env = {}, cwd = root } = {}) {
  return spawnSync(process.execPath, [TOOL, ...args], {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PATH: fullPath, SHIM_OUT: shimOut, COLUMNS: '100', ...env },
  });
}

// -h: exit 0, the help names the cast form it uses and the list form; after `list` it is the same page
{
  const res = spark(['-h']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.ok(res.stdout.startsWith('spark — help'), res.stdout);
  assert.ok(res.stdout.includes('cast --agent'), 'help names cast --agent');
  assert.ok(res.stdout.includes('       spark list [AGENT] [--json] [-h]\n'), 'help names the list form');

  const afterList = spark(['list', '--help']);
  assert.strictEqual(afterList.status, 0, afterList.stderr);
  assert.strictEqual(afterList.stdout, res.stdout);
}

// --dry-run: one line, the cast command, nothing launched
{
  const res = spark(['scout', '--dry-run']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout, `cast --agent scout --headed -p "${OPENING}"\n`);
  assert.strictEqual(res.stderr, '');
  assert.ok(!fs.existsSync(shimOut), 'a dry run launches nothing');
}

// --dry-run --json: agent, home, cast, with the same argv
{
  const res = spark(['scout', '--dry-run', '--json']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout.trim(), JSON.stringify({
    agent: 'scout', home: scout, cast: ['cast', '--agent', 'scout', '--headed', '-p', OPENING],
  }));
}

// a path names the agent folder; the agent is shown by its folder name
{
  const res = spark(['plans/x/agents/drafter', '--dry-run', '--json']);
  assert.strictEqual(res.status, 0, res.stderr);
  const out = JSON.parse(res.stdout);
  assert.strictEqual(out.agent, 'drafter');
  assert.strictEqual(out.home, drafter);
  assert.deepStrictEqual(out.cast.slice(0, 3), ['cast', '--agent', 'plans/x/agents/drafter']);
}

// list: the agents under .rbtv/agents/, the list cast prints; an agent that cannot be launched is
// named with the reason; nothing is launched and cast is not needed
{
  const res = spark(['list'], { env: { PATH: os.tmpdir() } });
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stderr, '');
  const lines = res.stdout.split('\n');
  assert.deepStrictEqual(lines.slice(0, 3), ['rbtv agents: 2', `Folder: ${path.join(root, '.rbtv', 'agents')}`, '']);
  assert.ok(lines.includes(`half: cannot be launched: ${path.join(half, 'agent.json')} is missing`), res.stdout);
  assert.ok(lines.includes('Name   Harness  Model        Effort  Ignite  Description'), res.stdout);
  const row = lines.find((line) => line.startsWith('scout '));
  assert.match(row, /^scout  codex    gpt-6\.1-sol  high    yes     Scouts the repository .*…$/, 'the description is shortened');
  assert.ok(row.length <= 100, `a row fits the terminal: ${row.length}`);
  assert.ok(!res.stdout.includes('drafter'), 'an agent outside .rbtv/agents/ is not in the list');
  assert.strictEqual(lines[lines.length - 2], 'One agent in full: cast list --agent NAME, spark list NAME or rbtv agent list NAME.');
  assert.ok(!fs.existsSync(shimOut), 'list launches nothing');

  // a narrow terminal: one labeled block per agent, the description whole, no line cut
  const narrow = spark(['list'], { env: { COLUMNS: '60' } });
  assert.strictEqual(narrow.status, 0, narrow.stderr);
  assert.ok(narrow.stdout.includes('Name: scout\nHarness: codex\nModel: gpt-6.1-sol\nEffort: high\nIgnite: yes\nDescription: Scouts'), narrow.stdout);
  assert.ok(narrow.stdout.replace(/\n {2}/g, ' ').includes(`Description: ${SCOUT_SAYS}`), 'the whole description is shown');
  assert.ok(!narrow.stdout.includes('Full description of one agent'), 'nothing was shortened, so no pointer');

  // one agent in full, by name and by path
  const one = spark(['list', 'scout']);
  assert.strictEqual(one.status, 0, one.stderr);
  assert.ok(one.stdout.startsWith(`Name: scout\nHarness: codex\nModel: gpt-6.1-sol\nEffort: high\nIgnite: yes\nFolder: ${scout}\nDescription: `), one.stdout);
  assert.ok(one.stdout.replace(/\n {2}/g, ' ').includes(SCOUT_SAYS), 'the whole description is shown');
  // what is installed in the agent is asked of rbtv, as cast does; without rbtv the view says so
  const alone = spark(['list', 'scout'], { env: { PATH: os.tmpdir() } });
  assert.strictEqual(alone.status, 0, alone.stderr);
  assert.ok(alone.stdout.endsWith('\n\nInstalled packs and units: not shown. rbtv is not on PATH.\n'), alone.stdout);

  const all = JSON.parse(spark(['--json', 'list']).stdout);
  assert.strictEqual(all.folder, path.join(root, '.rbtv', 'agents'));
  assert.deepStrictEqual(all.agents, [
    { name: 'half', home: half, problem: `${path.join(half, 'agent.json')} is missing` },
    { name: 'scout', description: SCOUT_SAYS, harness: 'codex', model: 'gpt-6.1-sol', effort: 'high', ignite: true, home: scout },
  ]);
  assert.deepStrictEqual(JSON.parse(spark(['list', 'plans/x/agents/drafter', '--json'], { env: { PATH: os.tmpdir() } }).stdout), {
    name: 'drafter', description: '', harness: 'claude', model: 'sonnet-5-5', effort: 'medium', ignite: false, home: drafter,
    installed: null, installed_problem: 'rbtv is not on PATH.',
  });
}

// list refusals: --dry-run, a second agent, an unknown option, an agent that is not there or cannot be launched
{
  const dryList = spark(['list', '--dry-run']);
  assert.strictEqual(dryList.status, 1);
  assert.ok(dryList.stderr.includes('`--dry-run` is not a spark list option'), dryList.stderr);

  const two = spark(['list', 'scout', 'half']);
  assert.strictEqual(two.status, 1);
  assert.ok(two.stderr.includes('spark list takes at most one agent'), two.stderr);

  const listFlag = spark(['list', '--target', root]);
  assert.strictEqual(listFlag.status, 1);
  assert.ok(listFlag.stderr.includes('`--target` is not a spark list option'), listFlag.stderr);

  const noOne = spark(['list', 'nosuch', '--json']);
  assert.strictEqual(noOne.status, 1);
  assert.ok(noOne.stderr.includes('no rbtv agent `nosuch` was found'), noOne.stderr);
  assert.strictEqual(noOne.stdout, '', '--json does not change a refusal: stdout stays empty');

  const broken = spark(['list', 'half']);
  assert.strictEqual(broken.status, 1);
  assert.ok(broken.stderr.includes('are unreadable'), broken.stderr);
}

// refusals: no agent by name or path, unreadable agent.json, an unknown option, no agent, no cast
{
  const nosuch = spark(['nosuch', '--dry-run']);
  assert.strictEqual(nosuch.status, 1);
  assert.ok(nosuch.stderr.includes('no rbtv agent `nosuch` was found'), nosuch.stderr);
  assert.ok(nosuch.stderr.includes('`spark list`, or pass the folder.'), nosuch.stderr);

  const nosuchJson = spark(['nosuch', '--json']);
  assert.strictEqual(nosuchJson.status, 1);
  assert.strictEqual(nosuchJson.stdout, '', '--json does not change a refusal: stdout stays empty');

  const missingPath = spark(['plans/launch/agents/missing', '--dry-run']);
  assert.strictEqual(missingPath.status, 1);
  assert.ok(missingPath.stderr.includes('no rbtv agent `plans/launch/agents/missing` was found'), missingPath.stderr);

  const unreadable = spark(['half', '--dry-run']);
  assert.strictEqual(unreadable.status, 1);
  assert.ok(unreadable.stderr.includes('are unreadable'), unreadable.stderr);
  assert.ok(unreadable.stderr.includes('agent.json is missing'), unreadable.stderr);

  const flag = spark(['scout', '--target', root]);
  assert.strictEqual(flag.status, 1);
  assert.ok(flag.stderr.includes("`--target` is not a spark option"), flag.stderr);

  const none = spark([]);
  assert.strictEqual(none.status, 1);
  assert.ok(none.stderr.includes('needs exactly one agent'), none.stderr);

  const noCast = spark(['scout', '--dry-run'], { env: { PATH: os.tmpdir() } });
  assert.strictEqual(noCast.status, 1);
  assert.ok(noCast.stderr.includes('cast is not on PATH'), noCast.stderr);
}

// a real launch: the handoff block, then cast with --agent and no harness, model or effort
if (process.platform !== 'win32') {
  const res = spark(['scout']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout, [
    `agent    scout`,
    `folder   ${scout}`,
    'harness  codex',
    'model    gpt-6.1-sol',
    'effort   high',
    '',
  ].join('\n'));
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(shimOut, 'utf8')), ['--agent', 'scout', '--headed', '-p', OPENING]);

  const withJson = spark(['plans/x/agents/drafter', '--json']);
  assert.strictEqual(withJson.status, 0, withJson.stderr);
  assert.ok(withJson.stdout.startsWith('agent    drafter\n'), 'a real launch ignores --json');
}

console.log('test_spark: ok');
