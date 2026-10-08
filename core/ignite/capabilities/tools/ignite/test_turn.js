#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { validate, argvFor, parseSessionEvents, buildResult } = require('./turn.js');

const TOOL = path.join(__dirname, 'cli.js');
const cwd = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-'));

function base(over = {}) {
  return {
    harness: 'claude', model: 'sonnet-5-5', effort: 3, cwd,
    prompt: 'hello', session: { mode: 'new' }, ...over,
  };
}

function rejects(request, needle) {
  assert.throws(() => validate(request), (e) => e.message.includes(needle),
    `expected ${needle} for ${JSON.stringify(request)}`);
}

{
  const v = validate(base());
  assert.strictEqual(v.harness, 'claude');
  assert.strictEqual(v.modelId, 'claude-sonnet-5-5');
  assert.strictEqual(v.model, 'sonnet-5-5');
  assert.strictEqual(v.effort, 'high');
  assert.deepStrictEqual(v.effortArgv, ['--effort', 'high']);
  assert.strictEqual(v.mode, 'new');
  assert.strictEqual(v.sessionId, null);
}

{
  const v = validate(base({ model: 'claude-sonnet-5-5', effort: 'high' }));
  assert.strictEqual(v.modelId, 'claude-sonnet-5-5');
  assert.strictEqual(v.effort, 'high');
}

{
  const file = path.join(cwd, 'prompt.txt');
  fs.writeFileSync(file, 'from file\n');
  const req = base();
  delete req.prompt;
  req.promptFile = file;
  assert.strictEqual(validate(req).prompt, 'from file\n');
}

{
  const codex = validate({ harness: 'codex', model: 'gpt-6-luna', effort: 5, cwd,
    prompt: 'x', session: { mode: 'resume', id: 'tid-1' } });
  assert.strictEqual(codex.effort, 'max');
  assert.strictEqual(codex.sessionId, 'tid-1');
  assert.deepStrictEqual(codex.env, null);
}

rejects(base({ harness: 'nope' }), 'unknown harness');
rejects(base({ model: 'no-such' }), "'claude no-such' is not a model cast supports");
rejects(base({ effort: 'turbo' }), 'unsupported effort');
rejects(base({ effort: 0 }), 'unsupported effort');
rejects(base({ cwd: 'relative' }), 'absolute directory');
rejects(base({ cwd: path.join(cwd, 'missing') }), 'absolute directory');
rejects(base({ prompt: '  ' }), 'nonempty');
rejects(base({ prompt: 'a', promptFile: path.join(cwd, 'prompt.txt') }), 'exactly one');
{
  const req = base();
  delete req.prompt;
  rejects(req, 'exactly one');
}
rejects(base({ session: { mode: 'last' } }), 'new or resume');
rejects(base({ session: { mode: 'new', id: 'abc' } }), 'not accepted');
rejects(base({ session: { mode: 'resume' } }), 'exact nonempty');
rejects(base({ session: { mode: 'resume', id: 'last' } }), 'exact nonempty');
rejects(base({ session: { mode: 'resume', id: '' } }), 'exact nonempty');
rejects(base({ env: ['PATH'] }), 'object of strings');
rejects(base({ env: { A: 1 } }), 'must be a string');

{
  const fresh = '11111111-1111-4111-8111-111111111111';
  const tag = 'cast-turn:22222222-2222-4222-8222-222222222222';
  const claude = validate(base());
  const freshArgv = argvFor(claude, fresh, null);
  assert.ok(freshArgv.includes('--session-id') && freshArgv.includes(fresh));
  assert.ok(!freshArgv.includes('--resume'));
  assert.ok(freshArgv.includes('--model') && freshArgv.includes('claude-sonnet-5-5'));
  assert.ok(freshArgv.includes('--effort') && freshArgv.includes('high'));
  assert.ok(!freshArgv.includes('last'));

  const resumed = validate(base({ session: { mode: 'resume', id: 'ses-9' } }));
  const resumeArgv = argvFor(resumed, null, null);
  assert.ok(resumeArgv.includes('--resume') && resumeArgv.includes('ses-9'));
  assert.ok(resumeArgv.includes('--model') && resumeArgv.includes('--effort'));
  assert.ok(!resumeArgv.includes('--session-id'));
  assert.ok(!resumeArgv.includes('last'));
}

{
  const codex = validate({ harness: 'codex', model: 'gpt-6-luna', effort: 'high', cwd,
    prompt: 'x', session: { mode: 'new' } });
  const argv = argvFor(codex, null, null);
  assert.deepStrictEqual(argv.slice(0, 3), ['codex', 'exec', '--cd']);
  assert.ok(argv.includes('-m') && argv.includes('gpt-6-luna'));
  assert.ok(argv.includes('model_reasoning_effort=high'));
  assert.ok(argv.includes('--skip-git-repo-check'), 'codex turn must run outside git repos');
  assert.ok(argv.includes('project_doc_max_bytes=131072'), 'codex turn must raise the AGENTS.md limit');
  assert.ok(argv.includes('--dangerously-bypass-hook-trust'), `a fresh codex turn must run the generated hooks: ${argv}`);
  assert.ok(argv.includes('--json'));
  assert.ok(!argv.includes('resume'));
  assert.ok(!argv.includes('last'));

  const back = validate({ harness: 'codex', model: 'gpt-6-luna', effort: 2, cwd,
    prompt: 'x', session: { mode: 'resume', id: 'tid-2' } });
  const resume = argvFor(back, null, null);
  assert.ok(resume.includes('resume') && resume.includes('tid-2'));
  assert.ok(resume.includes('-m') && resume.includes('gpt-6-luna'));
  assert.ok(resume.includes('model_reasoning_effort=medium'));
  assert.ok(resume.includes('--dangerously-bypass-hook-trust'), `a resumed codex turn must run the generated hooks: ${resume}`);
  assert.ok(!resume.includes('--last'));
  assert.ok(!resume.includes('last'));

  // One builder makes every Codex command line: an option added to cast's shared list reaches
  // the daemon's fresh and resumed turn. test_cast.js holds the same arm for cast's own lists.
  const { CODEX_ALWAYS } = require('../../../../cast/capabilities/tools/cast/lib/core');
  CODEX_ALWAYS.push('--probe-option');
  try {
    for (const [name, list] of [['fresh', argvFor(codex, null, null)], ['resumed', argvFor(back, null, null)]]) {
      for (const option of CODEX_ALWAYS) {
        assert.ok(list.includes(option), `the daemon's ${name} codex turn lacks the shared option ${option}: ${list}`);
      }
    }
  } finally {
    CODEX_ALWAYS.pop();
  }
}

{
  const oc = validate({ harness: 'opencode', model: 'grok-4.7', effort: 'high', cwd,
    prompt: 'x', session: { mode: 'new' } });
  const tag = 'cast-turn:33333333-3333-4333-8333-333333333333';
  const argv = argvFor(oc, null, tag);
  assert.ok(argv.includes('--title') && argv.includes(tag));
  assert.ok(argv.includes('-m') && argv.includes('xai/grok-4.7'));
  assert.ok(argv.includes('--variant') && argv.includes('high'));
  assert.ok(!argv.includes('-s'));
  assert.ok(!argv.includes('-c'));
  assert.ok(!argv.includes('last'));

  const back = validate({ harness: 'opencode', model: 'xai/grok-4.7', effort: 1, cwd,
    prompt: 'x', session: { mode: 'resume', id: 'ses_keep' } });
  const resume = argvFor(back, null, null);
  assert.ok(resume.includes('-s') && resume.includes('ses_keep'));
  assert.ok(resume.includes('--variant'));
  assert.ok(!resume.includes('--title'));
  assert.ok(!resume.includes('last'));
}

{
  const fixture = [
    '{"type":"thread.started","thread_id":"019fecad-4ff4-7761-a2eb-46d2b4172db3"}',
    'not json',
    '{"type":"item.completed","item":{"type":"agent_message","text":"hi"}}',
  ].join('\n');
  assert.strictEqual(parseSessionEvents(fixture).codexId, '019fecad-4ff4-7761-a2eb-46d2b4172db3');
  assert.strictEqual(parseSessionEvents('{"type":"thread.started"}\n').codexId, null);
  assert.strictEqual(parseSessionEvents('').codexId, null);
  const claudeOut = '{"type":"result","session_id":"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa","result":"ok"}\n';
  assert.strictEqual(parseSessionEvents(claudeOut).claudeId, 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
}

{
  const v = validate(base());
  const ok = buildResult(v, {
    exitCode: 0, spawnError: null, minted: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    claudeId: null, codexId: null, boundId: null, pid: 42, pidStart: 99,
    startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
  });
  assert.strictEqual(ok.ok, true);
  assert.strictEqual(ok.sessionId, 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa');
  assert.strictEqual(ok.pid, 42);
  assert.strictEqual(ok.pidStart, 99);
  assert.ok(!Object.prototype.hasOwnProperty.call(ok, 'error'));

  const mismatch = buildResult(v, {
    ...{
      exitCode: 0, spawnError: null, minted: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
      claudeId: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb', codexId: null, boundId: null,
      pid: 42, pidStart: 99, startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
    },
  });
  assert.strictEqual(mismatch.ok, false);
  assert.strictEqual(mismatch.sessionId, null);
  assert.strictEqual(mismatch.error, 'session_identity_mismatch');

  const codex = validate({ harness: 'codex', model: 'gpt-6-luna', effort: 1, cwd,
    prompt: 'x', session: { mode: 'new' } });
  const missing = buildResult(codex, {
    exitCode: 0, spawnError: null, minted: null, claudeId: null, codexId: null, boundId: null,
    pid: 7, pidStart: 1, startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
  });
  assert.strictEqual(missing.ok, false);
  assert.strictEqual(missing.error, 'session_identity_missing');

  const echoed = buildResult(
    validate({ harness: 'codex', model: 'gpt-6-luna', effort: 1, cwd,
      prompt: 'x', session: { mode: 'resume', id: 'tid-keep' } }),
    {
      exitCode: 0, spawnError: null, minted: null, claudeId: null, codexId: 'tid-other', boundId: null,
      pid: 7, pidStart: 1, startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
    },
  );
  assert.strictEqual(echoed.ok, false);
  assert.strictEqual(echoed.error, 'session_identity_mismatch');
  assert.strictEqual(echoed.sessionId, 'tid-other');

  const oc = buildResult(
    validate({ harness: 'opencode', model: 'grok-4.7', effort: 1, cwd,
      prompt: 'x', session: { mode: 'new' } }),
    {
      exitCode: 0, spawnError: null, minted: null, claudeId: null, codexId: null, boundId: 'ses_mine',
      pid: 7, pidStart: 1, startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
    },
  );
  assert.strictEqual(oc.ok, true);
  assert.strictEqual(oc.sessionId, 'ses_mine');
  const unbound = buildResult(
    validate({ harness: 'opencode', model: 'grok-4.7', effort: 1, cwd,
      prompt: 'x', session: { mode: 'new' } }),
    {
      exitCode: 0, spawnError: null, minted: null, claudeId: null, codexId: null, boundId: null,
      pid: 7, pidStart: 1, startedAt: 't0', endedAt: 't1', stdoutPath: '/o', stderrPath: '/e',
    },
  );
  assert.strictEqual(unbound.ok, false);
  assert.strictEqual(unbound.sessionId, null);
}

// A stand-in harness on PATH. Windows starts a .cmd file, never a sh script.
function installFake(bin, name, js) {
  fs.writeFileSync(path.join(bin, `${name}.js`), js);
  if (process.platform === 'win32') {
    fs.writeFileSync(path.join(bin, `${name}.cmd`), `@node "%~dp0${name}.js" %*\r\n`);
    return;
  }
  fs.writeFileSync(path.join(bin, name), `#!/bin/sh\nexec node "${path.join(bin, `${name}.js`)}" "$@"\n`);
  fs.chmodSync(path.join(bin, name), 0o755);
}

function runTurn(request, env) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-run-'));
  const requestFile = path.join(dir, 'request.json');
  const resultFile = path.join(dir, 'result.json');
  fs.writeFileSync(requestFile, JSON.stringify(request));
  const res = spawnSync('node', [TOOL, 'turn', '--request', requestFile, '--result', resultFile], {
    encoding: 'utf8', env,
  });
  const written = fs.existsSync(resultFile) ? JSON.parse(fs.readFileSync(resultFile, 'utf8')) : null;
  return { res, written, resultFile };
}

{
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-bin-'));
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-home-'));
  const argvFile = path.join(bin, 'argv.json');
  installFake(bin, 'claude', `
    const fs = require('fs');
    try { fs.readFileSync(0); } catch {}
    fs.writeFileSync(process.env.ARGV_FILE, JSON.stringify(process.argv.slice(2)));
    setTimeout(() => process.exit(0), 200);
  `);
  const env = {
    ...process.env, HOME: home, USERPROFILE: home, ARGV_FILE: argvFile,
    PATH: [bin, path.dirname(process.execPath)].join(path.delimiter),
  };
  const { res, written } = runTurn(base(), env);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(written.ok, true);
  assert.match(written.sessionId, /^[0-9a-f-]{36}$/);
  assert.strictEqual(typeof written.pid, 'number');
  if (process.platform !== 'win32') assert.strictEqual(typeof written.pidStart, 'number');
  assert.ok(fs.existsSync(written.stdoutPath));
  assert.ok(fs.existsSync(written.stderrPath));
  const argv = JSON.parse(fs.readFileSync(argvFile, 'utf8'));
  assert.ok(argv.includes('--session-id') && argv.includes(written.sessionId));
  assert.ok(argv.includes('--model') && argv.includes('--effort'));
  assert.ok(!argv.includes('last'));
}

{
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-bin-'));
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-home-'));
  const argvFile = path.join(bin, 'argv.json');
  installFake(bin, 'codex', `
    const fs = require('fs');
    try { fs.readFileSync(0); } catch {}
    fs.writeFileSync(process.env.ARGV_FILE, JSON.stringify(process.argv.slice(2)));
    process.stdout.write('{"type":"thread.started","thread_id":"019fecad-4ff4-7761-a2eb-46d2b4172db3"}\\n');
    process.exit(0);
  `);
  const env = {
    ...process.env, HOME: home, USERPROFILE: home, ARGV_FILE: argvFile,
    PATH: [bin, path.dirname(process.execPath)].join(path.delimiter),
  };
  const { res, written } = runTurn({
    harness: 'codex', model: 'gpt-6-luna', effort: 'medium', cwd,
    prompt: 'ping', session: { mode: 'resume', id: '019fecad-4ff4-7761-a2eb-46d2b4172db3' },
  }, env);
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(written.sessionId, '019fecad-4ff4-7761-a2eb-46d2b4172db3');
  const argv = JSON.parse(fs.readFileSync(argvFile, 'utf8'));
  assert.ok(argv.includes('resume') && argv.includes(written.sessionId));
  assert.ok(argv.includes('-m') && argv.includes('gpt-6-luna'));
  assert.ok(argv.includes('model_reasoning_effort=medium'));
  assert.ok(!argv.includes('--last'));
}

{
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-bin-'));
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-home-'));
  const xdg = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-xdg-'));
  const dbPath = path.join(xdg, 'opencode', 'opencode.db');
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });
  const { DatabaseSync } = require('node:sqlite');
  const db = new DatabaseSync(dbPath);
  db.exec('create table session (id text primary key, directory text not null, parent_id text,'
    + ' title text, time_created integer not null, time_updated integer not null)');
  const now = Date.now();
  db.prepare('insert into session values (?,?,?,?,?,?)').run(
    'ses_sib', cwd, null, 'newer sibling', now + 1000, now + 1000);
  db.close();
  installFake(bin, 'opencode', `
    const fs = require('fs');
    const path = require('path');
    try { fs.readFileSync(0); } catch {}
    const args = process.argv.slice(2);
    const title = args[args.indexOf('--title') + 1];
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(path.join(process.env.XDG_DATA_HOME, 'opencode', 'opencode.db'));
    const now = Date.now();
    db.prepare('insert into session values (?,?,?,?,?,?)').run('ses_mine', ${JSON.stringify(cwd)}, null, title, now, now);
    db.close();
    process.exit(0);
  `);
  const env = {
    ...process.env, HOME: home, USERPROFILE: home, XDG_DATA_HOME: xdg,
    PATH: [bin, path.dirname(process.execPath)].join(path.delimiter),
  };
  const { res, written } = runTurn({
    harness: 'opencode', model: 'grok-4.7', effort: 1, cwd,
    prompt: 'ping', session: { mode: 'new' },
  }, env);
  assert.strictEqual(res.status, 0, `${res.stderr}\n${JSON.stringify(written)}`);
  assert.strictEqual(written.sessionId, 'ses_mine');
}

{
  const { res, written } = runTurn(base({ session: { mode: 'resume', id: 'last' } }), process.env);
  assert.strictEqual(res.status, 1);
  assert.strictEqual(written.ok, false);
  assert.ok(written.error.includes('exact nonempty'));
}

// F1: the child must see PWD = request cwd, not the caller's PWD. OpenCode records
// its project directory from PWD, so a daemon running elsewhere would bind the
// session to the caller's folder and then fail session_identity_missing.
{
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-bin-'));
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-home-'));
  const callerPwd = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-caller-'));
  const pwdFile = path.join(bin, 'pwd.txt');
  const recordPwd = `try { require('fs').readFileSync(0); } catch {}
require('fs').writeFileSync(process.env.PWD_FILE, process.env.PWD || '');
process.exit(0);
`;
  // Direct node shebang, not the sh wrapper: sh resets PWD to the real cwd and would hide the bug.
  // The Windows .cmd stand-in leaves PWD as it was given.
  if (process.platform === 'win32') installFake(bin, 'opencode', recordPwd);
  else {
    fs.writeFileSync(path.join(bin, 'opencode'), `#!/usr/bin/env node\n${recordPwd}`);
    fs.chmodSync(path.join(bin, 'opencode'), 0o755);
  }
  const env = {
    ...process.env, HOME: home, USERPROFILE: home, PWD: callerPwd, PWD_FILE: pwdFile,
    PATH: [bin, path.dirname(process.execPath)].join(path.delimiter),
  };
  runTurn({
    harness: 'opencode', model: 'grok-4.7', effort: 1, cwd,
    prompt: 'ping', session: { mode: 'new' },
    env: { PWD: callerPwd },
  }, env);
  assert.strictEqual(fs.readFileSync(pwdFile, 'utf8'), cwd);
}

// F2: one throwing lookup. validate must not exit the process on an unknown model.
{
  const { lookupModel } = require('../../../../cast/capabilities/tools/cast/lib/core');
  assert.strictEqual(lookupModel('claude', 'sonnet-5-5', cwd).modelId, 'claude-sonnet-5-5');
  assert.throws(() => lookupModel('claude', 'no-such', cwd), /is not a model cast supports/);
  assert.throws(() => lookupModel('nope', 'sonnet-5-5', cwd), /unknown harness/);
  assert.throws(() => lookupModel('claude', 'sonnet-5-5'), /needs the folder that locates the installation/);
}

// A turn launches only a model its installation has selected. The installation is the one that
// holds the request's cwd (the agent's folder): its model catalog is .rbtv/config/cast/models.csv,
// and while it has none every supported model is selected.
{
  const HEAD = 'mode,harness,model,efforts,image,level,reasoning,coding,cost,use,quality-override,price-override';
  const SONNET = 'cli,claude,sonnet-5-5,5,N,L2,3,3,10,route,N,N';
  const agentHome = (lines) => {
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-gate-'));
    const home = path.join(root, '.rbtv', 'agents', 'probe');
    fs.mkdirSync(home, { recursive: true });
    fs.mkdirSync(path.join(root, '.rbtv', 'config', 'cast'), { recursive: true });
    fs.writeFileSync(path.join(root, '.rbtv', 'config', 'install.json'), '{}\n');
    const file = path.join(root, '.rbtv', 'config', 'cast', 'models.csv');
    if (lines) fs.writeFileSync(file, `${lines.join('\n')}\n`);
    return { root, home, file };
  };
  const turn = (home, harness, model) => ({ harness, model, effort: 1, cwd: home, prompt: 'x', session: { mode: 'new' } });

  // no model catalog: everything supported launches
  const fresh = agentHome(null);
  assert.strictEqual(validate(turn(fresh.home, 'claude', 'haiku-4-5')).modelId, 'claude-haiku-4-5');
  assert.strictEqual(validate(turn(fresh.home, 'opencode', 'grok-4.7')).modelId, 'xai/grok-4.7');

  // the model is not in the installation's model catalog: refused with the command that selects it
  const pruned = agentHome([HEAD, SONNET]);
  assert.strictEqual(validate(turn(pruned.home, 'claude', 'sonnet-5-5')).modelId, 'claude-sonnet-5-5');
  for (const model of ['haiku-4-5', 'claude-haiku-4-5']) {
    rejects(turn(pruned.home, 'claude', model),
      `refused: 'claude haiku-4-5' is not selected in ${pruned.root}\nmodel catalog: ${pruned.file}\nNothing changed.\ncast models add claude haiku-4-5`);
  }
  // the turn's own process reports it as an invalid request, never as a launch
  const { res, written } = runTurn(turn(pruned.home, 'claude', 'haiku-4-5'), process.env);
  assert.notStrictEqual(res.status, 0);
  assert.ok(JSON.stringify(written || res.stderr).includes('cast models add claude haiku-4-5'), `${res.stderr}${JSON.stringify(written)}`);

  // a row this copy of cast does not support: the deploy-copy case, named as such
  const orphan = agentHome([HEAD, SONNET, 'cli,opencode,not-a-real-model,3,N,L2,6,6,1,route,N,N']);
  rejects(turn(orphan.home, 'opencode', 'not-a-real-model'),
    `refused: 'opencode not-a-real-model' is selected in ${orphan.file} but this copy of cast does not support it`);
  rejects(turn(orphan.home, 'opencode', 'not-a-real-model'),
    'the daemon runs its own deployed copy of rbtv: deploy a commit that supports it\nNothing changed.\ncast models remove opencode not-a-real-model');

  // a model catalog that cannot be read stops the turn, for a selected model too
  const broken = agentHome([HEAD, 'cli,claude,sonnet-5-5,5,N,L2,3,3,1,0,route,N,N']);
  rejects(turn(broken.home, 'claude', 'sonnet-5-5'),
    `refused: cannot read the model catalog ${broken.file} line 2: 13 cells where the header has 12\nNothing changed.\ncorrect ${broken.file}, then run the same command again`);

  // the cwd is checked before the model: a missing folder is the answer, not a lookup from it
  rejects(turn(path.join(pruned.root, 'missing'), 'claude', 'haiku-4-5'), 'absolute directory');
}

// The agent's standing prompt rides each harness's strongest channel.
{
  const { stdinFor } = require('./turn.js');
  const file = path.join(cwd, 'prompt.md');
  fs.writeFileSync(file, '# Role\nYou are the agent.\n');
  const sys = (over) => validate({ ...base(), systemPromptFile: file, ...over });

  const fresh = argvFor(sys(), '11111111-1111-4111-8111-111111111111', null);
  assert.strictEqual(fresh[fresh.indexOf('--append-system-prompt') + 1], '# Role\nYou are the agent.\n', 'claude gets the prompt text');
  const resumed = argvFor(sys({ session: { mode: 'resume', id: 'ses-1' } }), null, null);
  assert.ok(!resumed.includes('--append-system-prompt'), 'claude keeps its system prompt across resume');
  const withFrontmatter = path.join(cwd, 'agent-frontmatter.md');
  fs.writeFileSync(withFrontmatter, '---\nname: writer\n---\n# Role\nYou are the agent.\n');
  const framed = argvFor(validate({ ...base(), systemPromptFile: withFrontmatter }), '11111111-1111-4111-8111-111111111111', null);
  assert.strictEqual(framed[framed.indexOf('--append-system-prompt') + 1], '# Role\nYou are the agent.\n', 'frontmatter never reaches the model');
  assert.strictEqual(stdinFor(sys()), 'hello');

  const codex = { harness: 'codex', model: 'gpt-6-luna', effort: 2 };
  const cx = argvFor(sys(codex), null, null);
  const cxResumed = argvFor(sys({ ...codex, session: { mode: 'resume', id: 'tid-1' } }), null, null);
  for (const argv of [cx, cxResumed]) {
    const at = argv.findIndex((a) => a.startsWith('developer_instructions='));
    assert.ok(at > 0 && argv[at - 1] === '-c', 'codex gets developer instructions on every turn');
    assert.strictEqual(JSON.parse(argv[at].slice('developer_instructions='.length)), '# Role\nYou are the agent.\n');
  }
  assert.strictEqual(stdinFor(sys(codex)), 'hello');

  const oc = { harness: 'opencode', model: 'grok-4.7', effort: 1 };
  const first = stdinFor(sys(oc));
  assert.ok(first.startsWith('# Role\nYou are the agent.') && first.endsWith('\n\nhello'), 'opencode: first message');
  assert.strictEqual(stdinFor(sys({ ...oc, session: { mode: 'resume', id: 'ses-2' } })), 'hello');
  assert.strictEqual(stdinFor(validate(base())), 'hello', 'no standing prompt, no change');
}
rejects(base({ systemPromptFile: 'relative.md' }), 'absolute path');
rejects(base({ systemPromptFile: path.join(cwd, 'missing.md') }), 'cannot read systemPromptFile');
{
  const empty = path.join(cwd, 'empty.md');
  fs.writeFileSync(empty, ' \n');
  rejects(base({ systemPromptFile: empty }), 'nonempty');
}

{
  // A request that cannot be read is a message on stderr and exit 1; the result file still records why.
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-missing-'));
  const resultFile = path.join(dir, 'result.json');
  const res = spawnSync('node', [TOOL, 'turn', '--request', path.join(dir, 'absent.json'), '--result', resultFile], { encoding: 'utf8' });
  assert.strictEqual(res.status, 1, res.stderr);
  assert.match(res.stderr, /ENOENT/);
  assert.strictEqual(res.stdout, '');
  assert.strictEqual(JSON.parse(fs.readFileSync(resultFile, 'utf8')).ok, false);
}

// The fallbacks of a turn: run in order, each in place of the one before, while a harness fails
// to start. The stand-in codex ends as FAKE_CODEX says for the model it was given.
{
  const bin = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-bin-'));
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'cast-turn-home-'));
  const ranFile = path.join(bin, 'ran.jsonl');
  installFake(bin, 'claude', `
    try { require('fs').readFileSync(0); } catch {}
    process.exit(Number(process.env.FAKE_CLAUDE || 1));
  `);
  installFake(bin, 'codex', `
    const fs = require('fs');
    const prompt = fs.readFileSync(0, 'utf8');
    const argv = process.argv.slice(2);
    const model = argv[argv.indexOf('-m') + 1];
    fs.appendFileSync(process.env.RAN_FILE, JSON.stringify({ model, argv, prompt }) + '\\n');
    process.stdout.write('{"type":"thread.started","thread_id":"019fecad-4ff4-7761-a2eb-46d2b4172db3"}\\n');
    process.exit(JSON.parse(process.env.FAKE_CODEX || '{}')[model] || 0);
  `);
  const env = {
    ...process.env, HOME: home, USERPROFILE: home, RAN_FILE: ranFile,
    PATH: [bin, path.dirname(process.execPath)].join(path.delimiter),
  };
  const fallbacks = [
    { harness: 'codex', model: 'gpt-6-luna', effort: 2, session: { mode: 'new' }, prompt: 'the first fallback prompt' },
    { harness: 'codex', model: 'gpt-5.6-terra', effort: 2, session: { mode: 'new' }, prompt: 'the second fallback prompt' },
  ];
  const ran = () => (fs.existsSync(ranFile) ? fs.readFileSync(ranFile, 'utf8').trim().split('\n').map((l) => JSON.parse(l)) : []);
  const turn = (request, extra = {}) => {
    fs.rmSync(ranFile, { force: true });
    return runTurn(request, { ...env, ...extra });
  };
  const claudeFailed = { harness: 'claude', model: 'sonnet-5-5', error: 'harness_exit_1' };
  // The entries of `failed` without `end`, once each `end` says how that run ended: the exit code
  // in `error`, no signal, and the time the run took.
  const withoutEnd = (failed) => failed.map(({ end, ...entry }) => {
    assert.deepStrictEqual([`harness_exit_${end.code}`, end.signal], [entry.error, null]);
    assert.ok(Number.isInteger(end.elapsedMs) && end.elapsedMs >= 0 && end.elapsedMs < 15_000, JSON.stringify(end));
    return entry;
  });

  // the harness exits with a failure at once: the first fallback runs, and the result is its run
  let { res, written, resultFile } = turn(base({ fallbacks }));
  assert.strictEqual(res.status, 0, res.stderr);
  assert.strictEqual(written.ok, true);
  assert.deepStrictEqual([written.harness, written.model, written.sessionId], ['codex', 'gpt-6-luna', '019fecad-4ff4-7761-a2eb-46d2b4172db3']);
  assert.deepStrictEqual([withoutEnd(written.failed), written.exhausted], [[claudeFailed], false]);
  assert.strictEqual(written.stdoutPath, `${resultFile}.fallback1.stdout`);
  assert.ok(fs.existsSync(`${resultFile}.stderr`), 'the failed run keeps its own capture files');
  assert.deepStrictEqual(ran().map((r) => [r.model, r.prompt]), [['gpt-6-luna', 'the first fallback prompt']]);
  assert.ok(ran()[0].argv.includes('model_reasoning_effort=medium'), JSON.stringify(ran()[0].argv));

  // the first fallback fails to start too: the second runs
  ({ written, resultFile } = turn(base({ fallbacks }), { FAKE_CODEX: '{"gpt-6-luna":1}' }));
  assert.deepStrictEqual([written.ok, written.model, written.exhausted], [true, 'gpt-5.6-terra', false]);
  assert.deepStrictEqual(withoutEnd(written.failed), [claudeFailed, { harness: 'codex', model: 'gpt-6-luna', error: 'harness_exit_1' }]);
  assert.strictEqual(written.stdoutPath, `${resultFile}.fallback2.stdout`);
  assert.deepStrictEqual(ran().map((r) => r.prompt), ['the first fallback prompt', 'the second fallback prompt']);

  // none starts: the result is the last run's failure, and says nothing is left
  ({ res, written } = turn(base({ fallbacks }), { FAKE_CODEX: '{"gpt-6-luna":1,"gpt-5.6-terra":4}' }));
  assert.strictEqual(res.status, 1);
  assert.deepStrictEqual([written.ok, written.model, written.error, written.exhausted], [false, 'gpt-5.6-terra', 'harness_exit_4', true]);
  assert.strictEqual(written.failed.length, 2);

  // an empty list still says the level is used up; a request without the key says nothing
  ({ written } = turn(base({ fallbacks: [] })));
  assert.deepStrictEqual([written.error, written.failed, written.exhausted], ['harness_exit_1', [], true]);
  ({ written } = turn(base()));
  assert.deepStrictEqual([written.error, written.failed, written.exhausted], ['harness_exit_1', undefined, undefined]);
  assert.deepStrictEqual(ran(), []);

  // a turn that succeeds starts one harness
  ({ written } = turn(base({ fallbacks }), { FAKE_CLAUDE: '0' }));
  assert.deepStrictEqual([written.ok, written.harness, written.failed, written.exhausted], [true, 'claude', [], false]);
  assert.deepStrictEqual(ran(), []);

  // the fallbacks are validated with the request
  rejects(base({ fallbacks: 'codex' }), 'fallbacks must be an array');
  rejects(base({ fallbacks: ['codex'] }), 'a fallback must be an object');
  rejects(base({ fallbacks: [{ ...fallbacks[0], model: 'no-such' }] }), "'codex no-such' is not a model cast supports");
  assert.deepStrictEqual(validate(base({ fallbacks })).fallbacks.map((f) => f.modelId), ['gpt-6-luna', 'gpt-5.6-terra']);
  assert.strictEqual(validate(base()).fallbacks, null);
}

{
  // Wrong usage exits 1, the convention of every other ignite verb (not 2).
  const res = spawnSync('node', [TOOL, 'turn', '--request', 'request.json'], { encoding: 'utf8' });
  assert.strictEqual(res.status, 1, res.stderr);
  assert.match(res.stderr, /usage: ignite turn --request FILE --result FILE/);
}

console.log('test_turn: ok');
