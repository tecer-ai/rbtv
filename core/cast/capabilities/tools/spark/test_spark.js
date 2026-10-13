#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const os = require('os');
const { spawnSync } = require('child_process');

const TOOL = path.join(__dirname, 'spark.js');
const BASE = os.tmpdir();

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
  fs.writeFileSync(path.join(folder, 'prompt.md'), '---\nname: scout\n---\nYou are Scout.\n');
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
  assert.ok(res.stdout.includes('       spark list [AGENT] [--target FOLDER] [--full] [--json] [-h]\n'), 'help names the list form');

  const afterList = spark(['list', '--help']);
  assert.strictEqual(afterList.status, 0, afterList.stderr);
  assert.strictEqual(afterList.stdout, res.stdout);
}

// --dry-run: one line, the cast command, nothing launched
{
  const res = spark(['scout', '--dry-run']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout, 'cast --agent scout --headed\n', 'spark passes no task: the opening message is cast\'s, read from agent.json');
  assert.strictEqual(res.stderr, '');
  assert.ok(!fs.existsSync(shimOut), 'a dry run launches nothing');
}

// --dry-run --json: agent, home, cast, with the same argv
{
  const res = spark(['scout', '--dry-run', '--json']);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(res.stdout.trim(), JSON.stringify({
    agent: 'scout', home: scout, cast: ['cast', '--agent', 'scout', '--headed'],
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
  assert.deepStrictEqual(lines.slice(-3, -1), ['Whole descriptions: add --full.',
    'One agent in full: cast list --agent NAME, spark list NAME or rbtv agent list NAME.']);
  // --full: every description whole, at any width
  const whole = spark(['list', '--full'], { env: { PATH: os.tmpdir(), COLUMNS: '200' } });
  assert.strictEqual(whole.status, 0, whole.stderr);
  assert.ok(whole.stdout.includes(`Ignite: yes\nDescription: ${SCOUT_SAYS}\n`), whole.stdout);
  assert.ok(!whole.stdout.includes('…'), 'nothing is shortened');
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
  assert.ok(alone.stdout.endsWith('\n\nInstalled packs and files: not shown. rbtv is not on PATH.\n'), alone.stdout);

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

  const fullOpen = spark(['scout', '--full', '--dry-run']);
  assert.strictEqual(fullOpen.status, 1);
  assert.ok(fullOpen.stderr.includes('`--full` is not a spark option'), fullOpen.stderr);

  const listFlag = spark(['list', '--bogus', root]);
  assert.strictEqual(listFlag.status, 1);
  assert.ok(listFlag.stderr.includes('`--bogus` is not a spark list option'), listFlag.stderr);

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

  const oldHome = path.join(root, 'plans', 'old', 'agents', 'oldname');
  writeAgent(oldHome, { name: 'oldname', harness: 'codex', model: 'gpt-6.1-sol', effort: 'high' });
  fs.renameSync(path.join(oldHome, 'prompt.md'), path.join(oldHome, 'agent.md'));
  const oldNamed = spark([oldHome, '--dry-run']);
  assert.strictEqual(oldNamed.status, 1);
  assert.ok(oldNamed.stderr.includes(`${path.join(oldHome, 'prompt.md')} is missing. This folder still has agent.md, the old name of the prompt file. If another machine already renamed it, pull first; otherwise rename it with: git mv agent.md prompt.md (inside ${oldHome}), and change any .gitignore line that names agent.md.`), oldNamed.stderr);

  const flag = spark(['scout', '--bogus', root]);
  assert.strictEqual(flag.status, 1);
  assert.ok(flag.stderr.includes("`--bogus` is not a spark option"), flag.stderr);

  const none = spark([]);
  assert.strictEqual(none.status, 1);
  assert.ok(none.stderr.includes('needs exactly one agent'), none.stderr);

  const noCast = spark(['scout', '--dry-run'], { env: { PATH: os.tmpdir() } });
  assert.strictEqual(noCast.status, 1);
  assert.ok(noCast.stderr.includes('cast is not on PATH'), noCast.stderr);
}

// --target FOLDER: the agents of an installation, of a folder that holds agent folders, or one
// agent folder; cast is handed the agent's folder; a folder that is none of the three is refused
{
  const plans = path.join(root, 'plans', 'x', 'agents');
  const elsewhere = mkFolder('elsewhere');
  const from = { cwd: elsewhere };
  const names = (args) => {
    const res = spark(['list', '--json', ...args], from);
    assert.strictEqual(res.status, 0, res.stderr);
    const out = JSON.parse(res.stdout);
    return [out.folder, out.agents.map((agent) => agent.name)];
  };
  assert.deepStrictEqual(names([]), [null, []], 'outside an installation, no --target lists nothing');
  assert.deepStrictEqual(names(['--target', plans]), [plans, ['drafter']], 'a folder that holds agent folders');
  assert.deepStrictEqual(names(['--target', root]), [path.join(root, '.rbtv', 'agents'), ['half', 'scout']], 'an installation');
  assert.deepStrictEqual(names(['--target', drafter]), [drafter, ['drafter']], 'one agent folder');
  // From inside the installation, the folder of agents wins over the nearest .rbtv/agents/.
  assert.ok(spark(['list', '--target', 'plans/x/agents']).stdout.startsWith(`rbtv agents: 1\nFolder: ${plans}\n`));

  const one = spark(['list', 'drafter', '--target', plans, '--json'], { ...from, env: { PATH: os.tmpdir() } });
  assert.strictEqual(one.status, 0, one.stderr);
  assert.strictEqual(JSON.parse(one.stdout).home, drafter);

  const open = spark(['drafter', '--target', plans, '--dry-run', '--json'], from);
  assert.strictEqual(open.status, 0, open.stderr);
  assert.deepStrictEqual(JSON.parse(open.stdout), {
    agent: 'drafter', home: drafter, cast: ['cast', '--agent', drafter, '--headed'],
  });
  assert.deepStrictEqual(JSON.parse(spark(['--target', root, 'scout', '--dry-run', '--json'], from).stdout).cast.slice(0, 3),
    ['cast', '--agent', scout], 'the option may come before the agent');

  for (const [args, text] of [
    [['list', '--target', elsewhere], 'names no rbtv agents'],
    [['drafter', '--target', elsewhere, '--dry-run'], 'names no rbtv agents'],
    [['list', '--target', path.join(elsewhere, 'absent')], 'is not a folder'],
    [['list', '--target'], '`--target` takes one folder'],
    [['list', '--target', plans, '--target', root], '`--target` takes one folder'],
    [['scout', '--target', plans, '--dry-run'], 'looked for an agent folder named scout in --target'],
    [['plans/x/agents/drafter', '--target', root, '--dry-run'], '`--target` goes with a name'],
  ]) {
    const res = spark(args, from);
    assert.strictEqual(res.status, 1, `expected a refusal for: spark ${args.join(' ')}`);
    assert.strictEqual(res.stdout, '');
    assert.ok(res.stderr.includes(text), `spark ${args.join(' ')}: ${res.stderr}`);
  }
  assert.ok(!fs.existsSync(shimOut), 'nothing was launched');
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
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(shimOut, 'utf8')), ['--agent', 'scout', '--headed']);

  const withJson = spark(['plans/x/agents/drafter', '--json']);
  assert.strictEqual(withJson.status, 0, withJson.stderr);
  assert.ok(withJson.stdout.startsWith('agent    drafter\n'), 'a real launch ignores --json');
}

// spark resume: the sessions on record, read from cast's handle registry under the home folder
{
  const home = mkFolder('resume-home');
  const homeEnv = { HOME: home, USERPROFILE: home };
  const t0 = Date.UTC(2026, 9, 13, 10, 0, 0);
  const plain = mkFolder('resume-plain');
  const rows = [
    { harness: 'claude', model: 'opus-5-5', session: 'old-id', folder: scout, t0: t0 - 5000, code: 'kj', agent: scout },
    { harness: 'claude', model: 'haiku-5-5', session: null, folder: plain, t0: t0 + 500 },
    { harness: 'codex', model: 'gpt-6.1-sol', session: null, folder: scout, t0, code: 'ab', agent: scout },
    { harness: 'opencode', model: 'glm-5.3', session: null, folder: plain, t0: t0 + 1000, code: 'zz', agent: null },
    { harness: 'claude', model: 'sonnet-5-5', session: 'new-id', folder: drafter, t0: t0 + 2000, code: 'kj', agent: drafter },
  ];
  fs.mkdirSync(path.join(home, '.cast'), { recursive: true });
  fs.writeFileSync(path.join(home, '.cast', 'handles.jsonl'), rows.map((r) => `${JSON.stringify(r)}\n`).join(''));
  // codex names its session itself: two rollouts of the folder, one born before the launch
  const day = path.join(home, '.codex', 'sessions', '2026', '10', '13');
  fs.mkdirSync(day, { recursive: true });
  const rollout = (id, at) => fs.writeFileSync(path.join(day, `rollout-${id}.jsonl`),
    `${JSON.stringify({ type: 'session_meta', timestamp: new Date(at).toISOString(), payload: { id, cwd: scout } })}\n`);
  rollout('before', t0 - 60000);
  rollout('opened', t0 + 3000);
  rollout('later', t0 + 90000);
  const resume = (args, env = {}) => spark(['resume', ...args], { env: { ...homeEnv, COLUMNS: '200', ...env } });

  // the list: newest first, one row per code (the newest), a launch with no code left out
  const list = resume([]);
  assert.strictEqual(list.status, 0, list.stderr);
  assert.strictEqual(list.stderr, '');
  const when = (ms) => {
    const d = new Date(ms);
    const p = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  };
  const cols = (...cells) => cells.join('|');
  const got = list.stdout.split('\n').map((line) => line.split(/ {2,}/).join('|'));
  assert.deepStrictEqual(got, [
    'Sessions opened: 3 of 3, newest first',
    '',
    cols('Code', 'Agent', 'Harness', 'Model', 'Opened', 'Folder'),
    cols('kj', 'drafter', 'claude', 'sonnet-5-5', when(t0 + 2000), drafter),
    cols('zz', '-', 'opencode', 'glm-5.3', when(t0 + 1000), plain),
    cols('ab', 'scout', 'codex', 'gpt-6.1-sol', when(t0), scout),
    '',
    'Open one again: spark resume CODE',
    '',
  ], list.stdout);
  const header = list.stdout.split('\n')[2];
  assert.strictEqual(header.indexOf('Folder'), list.stdout.split('\n')[3].indexOf(drafter), 'the columns line up');

  // -n: that many, and where the rest are; --json: the same sessions as one value
  const one = resume(['-n', '1']);
  assert.ok(one.stdout.startsWith('Sessions opened: 1 of 3, newest first\n'), one.stdout);
  assert.ok(one.stdout.endsWith('Open one again: spark resume CODE\nShow more: spark resume -n N, up to 50.\n'), one.stdout);
  assert.deepStrictEqual(JSON.parse(resume(['--json', '-n', '2']).stdout), { on_record: 3, sessions: [
    { code: 'kj', agent: 'drafter', harness: 'claude', model: 'sonnet-5-5', opened: new Date(t0 + 2000).toISOString(), folder: drafter },
    { code: 'zz', agent: null, harness: 'opencode', model: 'glm-5.3', opened: new Date(t0 + 1000).toISOString(), folder: plain },
  ] });

  // a narrow terminal: one labeled block per session, no line cut
  const narrow = resume(['-n', '1'], { COLUMNS: '40' });
  assert.ok(narrow.stdout.includes(`Code: kj\nAgent: drafter\nHarness: claude\nModel: sonnet-5-5\nOpened: ${when(t0 + 2000)}\nFolder: ${drafter}\n`), narrow.stdout);

  // no session on record is success
  const none = resume([], { HOME: plain, USERPROFILE: plain });
  assert.strictEqual(none.status, 0, none.stderr);
  assert.strictEqual(none.stdout, 'Sessions opened: 0\n\nNo session is on record. spark AGENT opens one.\n');
  assert.strictEqual(resume(['--json'], { HOME: plain, USERPROFILE: plain }).stdout, '{"on_record":0,"sessions":[]}\n');

  // refusals: exit 1, nothing on standard output, nothing launched
  fs.rmSync(shimOut, { force: true });
  for (const [args, text, env] of [
    [['qq'], 'no session `qq` is on record'],
    [['kj', 'ab'], 'spark resume takes at most one code'],
    [['-n', '0'], '`-n` takes a number from 1 to 50'],
    [['-n', '51'], '`-n` takes a number from 1 to 50'],
    [['-n'], '`-n` takes a number from 1 to 50'],
    [['-n', '3', 'kj'], '`-n` goes with the list, not with a code'],
    [['--full'], '`--full` is not a spark resume option'],
    [['zz'], `the session \`zz\` cannot be opened again\n  why: opencode recorded no session in ${plain} since`],
    [['kj'], 'cast is not on PATH', { PATH: os.tmpdir() }],
  ]) {
    const res = resume(args, env);
    assert.strictEqual(res.status, 1, `spark resume ${args.join(' ')}`);
    assert.strictEqual(res.stdout, '');
    assert.ok(res.stderr.includes(text), `spark resume ${args.join(' ')}: ${res.stderr}`);
  }
  assert.ok(!fs.existsSync(shimOut), 'nothing was launched');

  if (process.platform !== 'win32') {
    // a code opens its session through cast: claude by the id on record, codex by the first
    // session it recorded for the folder from the launch on
    const claude = resume(['kj']);
    assert.strictEqual(claude.status, 0, claude.stderr);
    assert.strictEqual(claude.stdout, ['session  kj', 'agent    drafter', `folder   ${drafter}`, 'harness  claude',
      'model    sonnet-5-5', ''].join('\n'));
    assert.deepStrictEqual(JSON.parse(fs.readFileSync(shimOut, 'utf8')), ['resume', 'claude', 'new-id', drafter, '--headed']);
    assert.strictEqual(resume(['ab']).status, 0);
    assert.deepStrictEqual(JSON.parse(fs.readFileSync(shimOut, 'utf8')), ['resume', 'codex', 'opened', scout, '--headed']);
  }

  // help after the verb is the one help page, and it names both resume forms
  const help = resume(['-h']);
  assert.strictEqual(help.status, 0);
  assert.ok(help.stdout.includes('       spark resume [-n N] [--json] [-h]\n       spark resume CODE [-h]\n'), help.stdout);
}

console.log('test_spark: ok');
