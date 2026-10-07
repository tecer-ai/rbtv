#!/usr/bin/env node
'use strict';

// Suite for deploy.js via cli.js. The real deploy.sh runs against scratch folders: a scratch git
// repository and its clones stand for the source and the deploy folders, a scratch HOME receives
// the unit file, and stand-in systemctl and journalctl programs on a scratch PATH record their calls.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { main } = require('./cli.js');

const UNIT = 'rbtv-ignite-agents.service';
const UNIT_FOLDER = path.join('core', 'ignite', 'capabilities', 'tools', 'ignite', 'units');
const pending = [];
const failures = [];

function test(name, fn) { pending.push([name, fn]); }

// A test that runs the deploy itself: the verb refuses on Windows, so it is skipped there by name.
function linuxOnly(name, fn) {
  pending.push([name, process.platform === 'win32' ? null : fn, 'the verb deploys a systemd user service and refuses on any other system']);
}

function git(dir, ...args) {
  const result = spawnSync('git', ['-C', dir, '-c', 'user.name=test', '-c', 'user.email=test@example.com', ...args], { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
  return result.stdout.trim();
}

function standIn(file, body) {
  fs.writeFileSync(file, `#!/bin/sh\n${body}\n`);
  fs.chmodSync(file, 0o755);
}

// first and second are the two commits of the source repository; every clone starts at first.
function scratch() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-deploy-'));
  const at = (...parts) => path.join(root, ...parts);
  const source = at('source');
  fs.mkdirSync(path.join(source, UNIT_FOLDER), { recursive: true });
  fs.copyFileSync(path.join(__dirname, 'units', UNIT), path.join(source, UNIT_FOLDER, UNIT));
  git(source, 'init', '-q');
  git(source, 'add', '.');
  git(source, 'commit', '-q', '-m', 'first');
  const first = git(source, 'rev-parse', 'HEAD');
  fs.writeFileSync(path.join(source, 'second.txt'), 'second\n');
  git(source, 'add', '.');
  git(source, 'commit', '-q', '-m', 'second');
  const second = git(source, 'rev-parse', 'HEAD');
  const clone = (name) => {
    git(root, 'clone', '-q', source, name);
    git(at(name), 'checkout', '-q', '--detach', first);
    return at(name);
  };
  const installation = (name) => {
    fs.mkdirSync(at(name, '.rbtv', 'config', 'ignite'), { recursive: true });
    fs.mkdirSync(at(name, '.rbtv', 'config', 'env'), { recursive: true });
    fs.writeFileSync(at(name, '.rbtv', 'config', 'ignite', 'config.json'), '{}');
    fs.writeFileSync(at(name, '.rbtv', 'config', 'env', '.env'), '');
    return at(name);
  };
  fs.mkdirSync(at('home'));
  fs.mkdirSync(at('bin'));
  fs.writeFileSync(at('state'), 'active\n');
  standIn(at('bin', 'systemctl'), `echo "systemctl $*" >> "${at('calls')}"\nif [ "$2" = is-active ]; then cat "${at('state')}"; fi`);
  standIn(at('bin', 'journalctl'), `echo "journalctl $*" >> "${at('calls')}"\necho "journal line one"\necho "journal line two"`);
  return {
    root, source, first, second, clone, installation, at,
    env: { PATH: `${at('bin')}${path.delimiter}${process.env.PATH}`, HOME: at('home') },
    head: (folder) => git(folder, 'rev-parse', 'HEAD'),
    calls: () => (fs.existsSync(at('calls')) ? fs.readFileSync(at('calls'), 'utf8') : ''),
    unitFile: at('home', '.config', 'systemd', 'user', UNIT),
    log: (installation) => path.join(installation, '.rbtv', 'runtime', 'ignite', 'deploys.jsonl'),
    remove: () => fs.rmSync(root, { recursive: true, force: true }),
  };
}

async function deploy(argv, deps = {}) {
  let stdout = '';
  let stderr = '';
  let code;
  try {
    code = await main(['deploy', ...argv], {
      pollMs: 5, limitMs: 200, ...deps, stdout: (text) => { stdout += text; }, stderr: (text) => { stderr += text; },
    });
  } catch (error) {
    code = error.exitCode;
    stderr += error.message;
  }
  return { code, stdout, stderr };
}

function undoLines(text) {
  return text.split('\n').filter((line) => line.startsWith('to undo'));
}

function logEntries(file) {
  const text = fs.readFileSync(file, 'utf8');
  assert.ok(text.endsWith('\n'), 'the log ends with a line end');
  return text.slice(0, -1).split('\n').map((line) => JSON.parse(line));
}

async function withScratch(fn) {
  const s = scratch();
  try { await fn(s); } finally { s.remove(); }
}

test('help-needs-nothing', async () => {
  const help = await deploy(['-h'], { platform: 'win32', env: {} });
  assert.equal(help.code, 0);
  assert.match(help.stdout, /^ignite deploy — /);
  assert.match(help.stdout, /usage: ignite deploy \[COMMIT\] \[--deploy-folder PATH\] \[--installation PATH\]/);
  let root = '';
  assert.equal(main(['-h'], { stdout: (text) => { root += text; } }), 0);
  assert.match(root, /^ {2}deploy {9}Check the service's folder out at a commit/m);
  assert.match(root, /^ {2}ignite deploy \[COMMIT\] \[--deploy-folder PATH\]$/m);
});

test('refuses-off-linux', async () => {
  for (const platform of ['win32', 'darwin']) {
    const refused = await deploy(['--dry-run'], { platform, env: {} });
    assert.equal(refused.code, 1);
    assert.equal(refused.stdout, '');
    assert.equal(refused.stderr, `ignite deploy runs on Linux only: the waking service is a systemd user service, and this system is ${platform}.\nNothing changed.\nignite deploy -h`);
  }
});

test('unknown-words-refused', async () => {
  const option = await deploy(['--force'], { platform: 'linux', env: {} });
  assert.equal(option.code, 1);
  assert.equal(option.stderr, "'--force' is not a deploy option\nNothing changed.\nignite deploy -h");
  const second = await deploy(['one', 'two'], { platform: 'linux', env: {} });
  assert.equal(second.stderr, 'unexpected argument: two\ndeploy takes one COMMIT\nNothing changed.\nignite deploy -h');
  const noValue = await deploy(['--deploy-folder'], { platform: 'linux', env: {} });
  assert.equal(noValue.stderr, '--deploy-folder requires a value\nNothing changed.\nignite deploy -h');
  const agent = await deploy(['--agent', 'scout'], { platform: 'linux', env: {} });
  assert.match(agent.stderr, /^--agent is not a deploy option/);
});

linuxOnly('default-commit', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  const started = Date.now();
  const done = await deploy(['--deploy-folder', folder, '--installation', installation], { env: s.env, sourceDir: s.source });
  const finished = Date.now();
  assert.equal(done.code, 0, done.stderr);
  assert.equal(s.head(folder), s.second, 'the deploy folder is at the HEAD of the source repository');
  assert.deepEqual(undoLines(done.stdout), [`to undo: ignite deploy ${s.first} --deploy-folder ${folder} --installation ${installation}`]);
  assert.equal(done.stdout.split(s.log(installation)).length, 2, 'the output names the log file once');
  assert.match(done.stdout, new RegExp(`^Deploy log {5}${s.log(installation)}$`, 'm'));
  const entries = logEntries(s.log(installation));
  assert.equal(entries.length, 1, 'one deploy, one line');
  const [entry] = entries;
  assert.deepEqual(Object.keys(entry), ['time', 'commitBefore', 'commitAsked', 'commitAfter', 'deployFolder', 'outcome']);
  assert.match(entry.time, /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/);
  assert.ok(Date.parse(entry.time) >= started && Date.parse(entry.time) <= finished, 'the time is the time of the deploy');
  assert.equal(entry.commitBefore, s.first);
  assert.equal(entry.commitAsked, s.second);
  assert.equal(entry.commitAfter, s.second);
  assert.equal(entry.deployFolder, folder);
  assert.equal(entry.outcome, 'ok');
  assert.match(done.stdout, new RegExp(`^Commit {9}${s.second} \\(HEAD of the repository holding `, 'm'));
  assert.match(done.stdout, new RegExp(`^Commit before {2}${s.first}$`, 'm'));
  assert.match(done.stdout, new RegExp(`^Commit now {5}${s.second}$`, 'm'));
  assert.match(done.stdout, new RegExp(`^Service {8}${UNIT} active$`, 'm'));
  assert.match(done.stdout, /A turn that was in progress was left running/);
  assert.match(done.stdout, /\(from --deploy-folder\)/);
  const calls = s.calls().split('\n');
  assert.deepEqual(calls.slice(0, 3), ['systemctl --user daemon-reload', `systemctl --user enable ${UNIT}`, `systemctl --user restart ${UNIT}`]);
  assert.equal(calls.filter((line) => line === `systemctl --user is-active ${UNIT}`).length, 3, 'active is read three times in a row');
  assert.match(fs.readFileSync(s.unitFile, 'utf8'), new RegExp(`^ExecStart=node ${folder}/core/.*/daemon\\.js --installation ${installation}$`, 'm'));
}));

linuxOnly('default-source-is-this-repository', () => withScratch(async (s) => {
  const here = spawnSync('git', ['-C', __dirname, 'rev-parse', '--show-toplevel', 'HEAD'], { encoding: 'utf8' }).stdout.trim().split('\n');
  const plan = await deploy(['--dry-run', '--json', '--deploy-folder', here[0], '--installation', s.installation('installation')], { env: s.env });
  assert.equal(plan.code, 0, plan.stderr);
  assert.equal(JSON.parse(plan.stdout).commit, here[1]);
}));

linuxOnly('explicit-commit', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  git(folder, 'checkout', '-q', '--detach', s.second);
  const done = await deploy([s.first.slice(0, 8), '--json', '--deploy-folder', folder, '--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(done.code, 0, done.stderr);
  assert.equal(s.head(folder), s.first);
  assert.deepEqual(JSON.parse(done.stdout), {
    dryRun: false,
    commit: s.first,
    installation,
    deployFolder: folder,
    deployFolderSource: '--deploy-folder',
    command: `RBTV_DEPLOY=${folder} RBTV_INSTALLATION=${installation} bash ${path.join(__dirname, 'deploy.sh')} ${s.first}`,
    log: s.log(installation),
    before: s.second,
    now: s.first,
    service: 'active',
    undo: `ignite deploy ${s.second} --deploy-folder ${folder} --installation ${installation}`,
  });
  const unknown = await deploy(['no-such-commit', '--deploy-folder', folder, '--installation', installation], { env: s.env });
  assert.equal(unknown.code, 1);
  assert.match(unknown.stderr, new RegExp(`^commit no-such-commit is not known in the deploy folder ${folder}\\.\\n.*\\nNothing changed\\.\\nignite deploy -h$`));
  assert.equal(s.head(folder), s.first);
  // A log folder that cannot be made: .rbtv/runtime is a file in this installation.
  const blocked = s.installation('blocked');
  fs.writeFileSync(path.join(blocked, '.rbtv', 'runtime'), '');
  const unlogged = await deploy([s.second, '--json', '--deploy-folder', folder, '--installation', blocked], { env: s.env });
  assert.equal(unlogged.code, 0, unlogged.stderr);
  assert.equal(s.head(folder), s.second);
  assert.match(unlogged.stderr, new RegExp(`^warning: this deploy was not written to the deploy log ${s.log(blocked)} \\(E[A-Z]+\\)\\.$`, 'm'));
  assert.equal(JSON.parse(unlogged.stdout).log, null);
  assert.equal(JSON.parse(unlogged.stdout).now, s.second);
}));

// The three sources of the deploy folder, each against a second folder a lower source names.
linuxOnly('folder-from-option', () => withScratch(async (s) => {
  const chosen = s.clone('chosen');
  const other = s.clone('other');
  const done = await deploy(['--deploy-folder', chosen, '--installation', s.installation('installation')], {
    env: { ...s.env, RBTV_DEPLOY: other }, sourceDir: s.source,
  });
  assert.equal(done.code, 0, done.stderr);
  assert.equal(s.head(chosen), s.second, '--deploy-folder is deployed');
  assert.equal(s.head(other), s.first, 'RBTV_DEPLOY is left alone when the option is given');
}));

linuxOnly('folder-from-environment', () => withScratch(async (s) => {
  const chosen = s.clone('chosen');
  const other = s.clone('other');
  const installation = s.installation('installation');
  // A real first deploy installs a unit that runs from `other`.
  assert.equal((await deploy([s.first, '--deploy-folder', other, '--installation', installation], { env: s.env })).code, 0);
  const done = await deploy(['--installation', installation], { env: { ...s.env, RBTV_DEPLOY: chosen }, sourceDir: s.source });
  assert.equal(done.code, 0, done.stderr);
  assert.match(done.stdout, /\(from RBTV_DEPLOY\)/);
  assert.equal(s.head(chosen), s.second, 'RBTV_DEPLOY is deployed');
  assert.equal(s.head(other), s.first, 'the installed unit is not read when RBTV_DEPLOY is set');
}));

linuxOnly('folder-from-installed-unit', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  // The unit file is the one the real deploy.sh wrote on a first deploy, not a hand-typed one.
  const same = await deploy([s.first, '--deploy-folder', folder, '--installation', installation], { env: s.env });
  assert.equal(same.code, 0, same.stderr);
  assert.deepEqual(undoLines(same.stdout), [], 'no undo line when the commit did not change');
  const firstLine = fs.readFileSync(s.log(installation), 'utf8');
  assert.equal(logEntries(s.log(installation)).length, 1);
  const done = await deploy(['--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(done.code, 0, done.stderr);
  assert.match(done.stdout, new RegExp(`^Deploy folder {2}${folder} \\(from the installed unit ${s.unitFile}\\)$`, 'm'));
  assert.equal(s.head(folder), s.second);
  const both = fs.readFileSync(s.log(installation), 'utf8');
  assert.equal(both.slice(0, firstLine.length), firstLine, 'the first line is byte-identical after the second deploy');
  const entries = logEntries(s.log(installation));
  assert.equal(entries.length, 2, 'the second deploy appended one line');
  assert.deepEqual([entries[0].commitBefore, entries[0].commitAfter], [s.first, s.first]);
  assert.deepEqual([entries[1].commitBefore, entries[1].commitAfter], [s.first, s.second]);
}));

linuxOnly('no-folder-refused', () => withScratch(async (s) => {
  const installation = s.installation('installation');
  const refused = await deploy(['--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(refused.code, 1);
  assert.equal(refused.stdout, '');
  assert.equal(refused.stderr, `no deploy folder: --deploy-folder was not given, RBTV_DEPLOY is not set, and no unit is installed at ${s.unitFile}.\nFor a first deploy, pass the git worktree the service will run from: ignite deploy --deploy-folder PATH\nNothing changed.\nignite deploy -h`);
  fs.mkdirSync(path.dirname(s.unitFile), { recursive: true });
  fs.writeFileSync(s.unitFile, '[Service]\nExecStart=/usr/bin/other-program\n');
  const unreadable = await deploy(['--installation', installation], { env: s.env, sourceDir: s.source });
  assert.match(unreadable.stderr, new RegExp(`and ${s.unitFile} has no ExecStart line this program can read\\.`));
  const notGit = await deploy(['--deploy-folder', s.at('home'), '--installation', installation], { env: s.env, sourceDir: s.source });
  assert.match(notGit.stderr, /is not a git worktree with a commit checked out\.\nNothing changed\./);
  assert.equal(s.calls(), '');
  assert.equal(fs.existsSync(path.join(installation, '.rbtv', 'runtime')), false, 'a refusal writes no log');
}));

linuxOnly('dry-run-runs-nothing', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  const plan = await deploy(['--dry-run', '--deploy-folder', folder, '--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(plan.code, 0, plan.stderr);
  assert.equal(plan.stderr, '');
  assert.match(plan.stdout, /^ignite deploy — dry run, nothing ran$/m);
  assert.match(plan.stdout, new RegExp(`^Commit {9}${s.second} `, 'm'));
  assert.match(plan.stdout, new RegExp(`^Installation {3}${installation}$`, 'm'));
  assert.match(plan.stdout, new RegExp(`^Deploy folder {2}${folder} \\(from --deploy-folder\\)$`, 'm'));
  assert.match(plan.stdout, new RegExp(`^Would run {6}RBTV_DEPLOY=${folder} RBTV_INSTALLATION=${installation} bash ${path.join(__dirname, 'deploy.sh')} ${s.second}$`, 'm'));
  assert.equal(s.head(folder), s.first, 'the deploy folder did not move');
  assert.equal(s.calls(), '', 'neither systemctl nor journalctl ran');
  assert.equal(fs.existsSync(s.unitFile), false, 'no unit file was written');
  assert.match(plan.stdout, new RegExp(`^Would log to {3}${s.log(installation)}$`, 'm'));
  assert.deepEqual(undoLines(plan.stdout), []);
  assert.equal(fs.existsSync(path.join(installation, '.rbtv', 'runtime')), false, 'a dry run writes no log');
}));

linuxOnly('installation-from-walk', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = fs.realpathSync(s.installation('installation'));
  const other = fs.realpathSync(s.installation('other-installation'));
  const cwd = process.cwd();
  try {
    process.chdir(path.join(installation, '.rbtv', 'config'));
    const done = await deploy([s.first, '--deploy-folder', folder], { env: s.env });
    assert.equal(done.code, 0, done.stderr);
    assert.match(done.stdout, new RegExp(`^Installation {3}${installation}$`, 'm'));
    // The installed unit now serves `installation`; a walk that finds another one is refused.
    process.chdir(other);
    const refused = await deploy(['--dry-run'], { env: s.env, sourceDir: s.source });
    assert.equal(refused.code, 1);
    assert.match(refused.stderr, new RegExp(`^the installed service serves installation ${installation}, and this command resolved ${other}\\.\\n`));
    assert.match(refused.stderr, /\nNothing changed\.\nignite deploy -h$/);
    const named = await deploy(['--dry-run', '--installation', other], { env: s.env, sourceDir: s.source });
    assert.equal(named.code, 0, named.stderr);
    process.chdir(s.root);
    const none = await deploy(['--dry-run', '--deploy-folder', folder], { env: s.env });
    const sought = path.join(process.cwd(), '.rbtv', 'config', 'ignite', 'config.json');
    assert.equal(none.stderr, `no installation found: ${sought} is not in this folder or above.\nRun from inside an installation, or pass --installation PATH.\nNothing changed.\nignite deploy -h`);
  } finally {
    process.chdir(cwd);
  }
}));

linuxOnly('service-not-active-fails', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  fs.writeFileSync(s.at('state'), 'failed\n');
  const failed = await deploy(['--deploy-folder', folder, '--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(failed.code, 1);
  assert.equal(failed.stdout, '');
  assert.match(failed.stderr, new RegExp(`^ignite deploy failed: the service did not stay active at ${s.second} within 0\\.2 seconds\\.$`, 'm'));
  assert.match(failed.stderr, new RegExp(`^Commit before {2}${s.first}\\nCommit now {5}${s.second}\\nService {8}${UNIT} failed\\nLast 20 journal lines:\\njournal line one\\njournal line two$`, 'm'));
  assert.deepEqual(undoLines(failed.stderr), [`to undo: ignite deploy ${s.first} --deploy-folder ${folder} --installation ${installation}`]);
  assert.match(failed.stderr, new RegExp(`^Deploy log {5}${s.log(installation)}$`, 'm'));
  const entries = logEntries(s.log(installation));
  assert.equal(entries.length, 1);
  assert.deepEqual({ ...entries[0], time: null }, {
    time: null,
    commitBefore: s.first,
    commitAsked: s.second,
    commitAfter: s.second,
    deployFolder: folder,
    outcome: 'failed',
    reason: `the service did not stay active at ${s.second} within 0.2 seconds.`,
  });
  assert.match(s.calls(), new RegExp(`^journalctl --user -u ${UNIT} -n 20 --no-pager$`, 'm'));
}));

linuxOnly('script-failure-fails', () => withScratch(async (s) => {
  const folder = s.clone('deploy');
  const installation = s.installation('installation');
  fs.rmSync(path.join(installation, '.rbtv', 'config', 'env', '.env'));
  const failed = await deploy(['--deploy-folder', folder, '--installation', installation], { env: s.env, sourceDir: s.source });
  assert.equal(failed.code, 1);
  assert.match(failed.stderr, /^env file missing: /);
  assert.match(failed.stderr, /^ignite deploy failed: deploy\.sh exited 1\.$/m);
  assert.equal(s.head(folder), s.first);
  assert.doesNotMatch(s.calls(), /restart/);
  assert.deepEqual(undoLines(failed.stderr), [], 'no undo line when the commit did not change');
  const [entry] = logEntries(s.log(installation));
  assert.deepEqual([entry.commitBefore, entry.commitAfter, entry.outcome, entry.reason], [s.first, s.first, 'failed', 'deploy.sh exited 1.']);
}));

(async () => {
  for (const [name, fn, why] of pending) {
    if (!fn) { console.log(`skip: ${name} is Linux-only: ${why}`); continue; }
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failures.push(name);
      console.log(`FAIL ${name}: ${error.stack || error.message}`);
    }
  }
  if (failures.length) {
    console.log(`${failures.length} failed`);
    process.exit(1);
  }
  console.log('ok');
})();
