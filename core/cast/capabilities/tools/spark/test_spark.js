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
const root = mkFolder('root');
function writeAgent(folder, values) {
  fs.mkdirSync(folder, { recursive: true });
  fs.writeFileSync(path.join(folder, 'agent.md'), '---\nname: scout\n---\nYou are Scout.\n');
  if (values) fs.writeFileSync(path.join(folder, 'agent.json'), JSON.stringify(values));
}
const scout = path.join(root, '.rbtv', 'agents', 'scout');
const drafter = path.join(root, 'plans', 'x', 'agents', 'drafter');
const half = path.join(root, '.rbtv', 'agents', 'half');
writeAgent(scout, { name: 'scout', harness: 'codex', model: 'gpt-6.1-sol', effort: 'high' });
writeAgent(drafter, { name: 'drafter', harness: 'claude', model: 'sonnet-5-5', effort: 'medium' });
writeAgent(half, null);

// A program on PATH under `name` that runs `script` with node, on POSIX and on Windows.
const shimDir = mkFolder('shim');
function writeShim(name, script) {
  fs.writeFileSync(path.join(shimDir, `${name}.js`), script);
  fs.writeFileSync(path.join(shimDir, name), `#!/bin/sh\nexec "${process.execPath}" "$(dirname "$0")/${name}.js" "$@"\n`, { mode: 0o755 });
  fs.writeFileSync(path.join(shimDir, `${name}.cmd`), `@"${process.execPath}" "%~dp0${name}.js" %*\r\n`);
}
// A `cast` that records its own argv. Launches go through it; nothing reaches a harness.
const shimOut = path.join(shimDir, 'argv.json');
writeShim('cast', "require('fs').writeFileSync(process.env.SHIM_OUT, JSON.stringify(process.argv.slice(2)));\n");
// An `rbtv` that records its own argv, prints one line and exits with RBTV_EXIT. No list is read.
const rbtvOut = path.join(shimDir, 'rbtv-argv.json');
writeShim('rbtv', "require('fs').writeFileSync(process.env.RBTV_OUT, JSON.stringify(process.argv.slice(2)));\n"
  + "process.stdout.write('the list\\n');\nprocess.exitCode = Number(process.env.RBTV_EXIT || 0);\n");
const fullPath = `${shimDir}${path.delimiter}${process.env.PATH}`;

function spark(args, { env = {}, cwd = root } = {}) {
  return spawnSync(process.execPath, [TOOL, ...args], {
    cwd,
    encoding: 'utf8',
    env: { ...process.env, PATH: fullPath, SHIM_OUT: shimOut, RBTV_OUT: rbtvOut, ...env },
  });
}

// -h: exit 0, the help names the cast form it uses and the list form; after `list` it is the same page
{
  const res = spark(['-h']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.ok(res.stdout.startsWith('spark — help'), res.stdout);
  assert.ok(res.stdout.includes('cast -rbtv'), 'help names cast -rbtv');
  assert.ok(res.stdout.includes('       spark list [FOLDER] [--json] [-h]\n'), 'help names the list form');

  const afterList = spark(['list', '--help']);
  assert.strictEqual(afterList.status, 0, afterList.stderr);
  assert.strictEqual(afterList.stdout, res.stdout);
  assert.ok(!fs.existsSync(rbtvOut), 'help runs nothing');
}

// --dry-run: one line, the cast command, nothing launched
{
  const res = spark(['scout', '--dry-run']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout, `cast -rbtv scout --headed -p "${OPENING}"\n`);
  assert.strictEqual(res.stderr, '');
  assert.ok(!fs.existsSync(shimOut), 'a dry run launches nothing');
}

// --dry-run --json: agent, home, cast, with the same argv
{
  const res = spark(['scout', '--dry-run', '--json']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout.trim(), JSON.stringify({
    agent: 'scout', home: scout, cast: ['cast', '-rbtv', 'scout', '--headed', '-p', OPENING],
  }));
}

// a path names the agent folder; the agent is shown by its folder name
{
  const res = spark(['plans/x/agents/drafter', '--dry-run', '--json']);
  assert.strictEqual(res.status, 0, res.stderr);
  const out = JSON.parse(res.stdout);
  assert.strictEqual(out.agent, 'drafter');
  assert.strictEqual(out.home, drafter);
  assert.deepStrictEqual(out.cast.slice(0, 3), ['cast', '-rbtv', 'plans/x/agents/drafter']);
}

// list: `rbtv agent list` runs with the same folder and --json; its output and exit status pass through
{
  const res = spark(['list']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout, 'the list\n');
  assert.strictEqual(res.stderr, '');
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(rbtvOut, 'utf8')), ['agent', 'list']);

  const folder = spark(['--json', 'list', 'plans/x'], { env: { RBTV_EXIT: '1' } });
  assert.strictEqual(folder.status, 1, 'the exit status of rbtv agent list passes through');
  assert.strictEqual(folder.stdout, 'the list\n');
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(rbtvOut, 'utf8')), ['agent', 'list', 'plans/x', '--json']);
  assert.ok(!fs.existsSync(shimOut), 'list launches nothing');
}

// list refusals: --dry-run, a second folder, an unknown option, no rbtv; none of them runs rbtv
{
  fs.rmSync(rbtvOut);
  const dryList = spark(['list', '--dry-run']);
  assert.strictEqual(dryList.status, 1);
  assert.ok(dryList.stderr.includes('`--dry-run` is not a spark list option'), dryList.stderr);

  const two = spark(['list', 'plans/x', 'plans/y']);
  assert.strictEqual(two.status, 1);
  assert.ok(two.stderr.includes('spark list takes at most one folder'), two.stderr);

  const listFlag = spark(['list', '--target', root]);
  assert.strictEqual(listFlag.status, 1);
  assert.ok(listFlag.stderr.includes('`--target` is not a spark list option'), listFlag.stderr);

  const noRbtv = spark(['list', '--json'], { env: { PATH: os.tmpdir() } });
  assert.strictEqual(noRbtv.status, 1);
  assert.ok(noRbtv.stderr.includes('rbtv is not on PATH'), noRbtv.stderr);
  assert.strictEqual(noRbtv.stdout, '', '--json does not change a refusal by spark: stdout stays empty');
  assert.ok(!fs.existsSync(rbtvOut), 'a refused list runs nothing');
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

// a real launch: the handoff block, then cast with -rbtv and no harness, model or effort
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
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(shimOut, 'utf8')), ['-rbtv', 'scout', '--headed', '-p', OPENING]);

  const withJson = spark(['plans/x/agents/drafter', '--json']);
  assert.strictEqual(withJson.status, 0, withJson.stderr);
  assert.ok(withJson.stdout.startsWith('agent    drafter\n'), 'a real launch ignores --json');
}

console.log('test_spark: ok');
