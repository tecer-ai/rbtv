#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { main } = require('./cli.js');

const failures = [];

async function test(name, fn) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

function workspace() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-create-'));
}

function writeConfig(dir, routes = {}) {
  const agents = path.join(dir, '.rbtv', 'agents');
  fs.mkdirSync(agents, { recursive: true });
  const body = {
    workspace: dir,
    slack: {
      team: 'T1',
      botUserId: 'UBOT',
      ownerUserId: 'UOWNER',
      botTokenFile: path.join(dir, 'bot.json'),
      appTokenSource: 'SLACK_APP_TOKEN',
      ownerTokenFile: path.join(dir, 'owner.json'),
    },
    tools: { cast: 'cast', stools: 'stools', audio: 'audio' },
    defaultLaunch: { harness: 'claude', model: 'm', effort: 'high' },
    dmAgent: 'master',
    routes,
  };
  fs.writeFileSync(path.join(agents, 'ignite.json'), `${JSON.stringify(body, null, 2)}\n`);
  return body;
}

function purposeFile(dir) {
  const file = path.join(dir, 'purpose.md');
  fs.writeFileSync(file, 'Answer briefly. Read the files you are given.\n');
  return file;
}

function acceptLaunch(setting) {
  if (/^[1-5]$/.test(String(setting.effort))) {
    return { ...setting, effort: 'high', voice: setting.voice ?? null };
  }
  return { harness: setting.harness, model: setting.model, effort: setting.effort, voice: setting.voice ?? null };
}

function fakeSlack() {
  const calls = [];
  return {
    calls,
    async createChannel(name) {
      calls.push(['create', name]);
      return { id: 'CNEW', name };
    },
    async joinChannel(id) {
      calls.push(['join', id]);
      return { id };
    },
    async inviteUser(id, user) {
      calls.push(['invite', id, user]);
      return { id };
    },
    async archiveChannel(id) {
      calls.push(['archive', id]);
      return { ok: true };
    },
  };
}

function install(id, home) {
  const part = id.split('#')[1];
  for (const rel of [path.join('.claude', 'skills'), path.join('.agents', 'skills')]) {
    const folder = path.join(home, rel, part);
    fs.mkdirSync(folder, { recursive: true });
    fs.writeFileSync(path.join(folder, 'SKILL.md'), `---\nname: ${part}\ndescription: stub\n---\nstub\n`);
  }
}

function tree(dir) {
  const out = [];
  const walk = (current) => {
    for (const name of fs.readdirSync(current)) {
      const abs = path.join(current, name);
      const rel = path.relative(dir, abs);
      out.push(rel);
      if (fs.statSync(abs).isDirectory()) walk(abs);
    }
  };
  walk(dir);
  return out.sort();
}

async function run(argv, extra = {}) {
  const out = [];
  const err = [];
  const code = await main(argv, {
    stdout: (text) => out.push(text),
    stderr: (text) => err.push(text),
    validateLaunch: acceptLaunch,
    install,
    ...extra,
  });
  return { code, out: out.join(''), err: err.join('') };
}

function baseArgs(dir, slug, extra = []) {
  return ['create', '--workspace', dir, '--slug', slug, '--purpose-file', purposeFile(dir), ...extra];
}

(async () => {
  await test('dry-run makes no writes', async () => {
    const dir = workspace();
    writeConfig(dir);
    const args = baseArgs(dir, 'probe', ['--channel-name', 'probe', '--dry-run']);
    const before = tree(dir);
    const slack = fakeSlack();
    const result = await run(args, { slack });
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /writes: none/);
    assert.match(result.out, /slug: probe/);
    assert.deepEqual(tree(dir), before);
    assert.equal(slack.calls.length, 0);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
  });

  await test('full create', async () => {
    const dir = workspace();
    writeConfig(dir);
    const schedule = path.join(dir, 'schedule.json');
    fs.writeFileSync(schedule, JSON.stringify({ cron: '0 9 * * 1', tz: 'UTC', note: 'read the board' }));
    const slack = fakeSlack();
    const result = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe', '--schedule-json', schedule, '--effort', '3', '--harness', 'claude', '--model', 'm']), { slack });
    assert.equal(result.code, 0, result.out + result.err);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    const claude = fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8');
    assert.equal(claude, fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8'));
    assert.match(claude, /Answer briefly/);
    assert.match(claude, /Standing instructions/);
    const launch = JSON.parse(fs.readFileSync(path.join(home, 'launch.json'), 'utf8'));
    assert.equal(launch.effort, 'high');
    assert.equal(/^[1-5]$/.test(launch.effort), false);
    assert.equal(fs.existsSync(path.join(home, 'state.sqlite')), true);
    assert.equal(fs.existsSync(path.join(home, 'conversations')), true);
    const config = JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), 'utf8'));
    assert.equal(config.routes.CNEW, 'probe');
    assert.deepEqual(slack.calls.map((call) => call[0]), ['create', 'join', 'invite']);
    assert.equal(slack.calls[2][2], 'UOWNER');
    assert.match(result.out, /route: CNEW -> probe/);
    assert.match(result.out, /bot=joined owner=invited/);
    assert.match(result.out, /loaders: ok/);
    assert.match(fs.readFileSync(path.join(home, 'board.md'), 'utf8'), /read the board/);
    assert.equal(fs.existsSync(path.join(home, '.claude', 'skills', 'slack-message-format', 'SKILL.md')), true);
    assert.equal(fs.existsSync(path.join(home, '.agents', 'skills', 'investignosis', 'SKILL.md')), true);
  });

  await test('resume after a failure between channel creation and route write', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    let failed = false;
    const first = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), {
      slack,
      afterChannel() {
        failed = true;
        const error = new Error('injected');
        error.exitCode = 1;
        throw error;
      },
    }).catch((error) => error);
    assert.equal(first.message, 'injected');
    assert.equal(failed, true);
    const mid = JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), 'utf8'));
    assert.deepEqual(mid.routes, {});
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    const second = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(second.code, 0, second.out + second.err);
    assert.equal(slack.calls.filter((call) => call[0] === 'create').length, 1);
    const done = JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), 'utf8'));
    assert.equal(done.routes.CNEW, 'probe');
    assert.match(second.out, /route: CNEW -> probe/);
  });

  await test('remove', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    fs.writeFileSync(path.join(home, 'conversations', 'kept.md'), 'history\n');
    const removed = await run(['create', '--remove', '--workspace', dir, '--slug', 'probe', '--archive-channel'], { slack, now: () => Date.parse('2026-09-28T12:00:00Z') });
    assert.equal(removed.code, 0, removed.out + removed.err);
    assert.equal(fs.existsSync(home), false);
    const config = JSON.parse(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'ignite.json'), 'utf8'));
    assert.deepEqual(config.routes, {});
    assert.equal(slack.calls.some((call) => call[0] === 'archive' && call[1] === 'CNEW'), true);
    const trash = path.join(dir, '.rbtv', 'agents', '.removed');
    const moved = fs.readdirSync(trash);
    assert.equal(moved.length, 1);
    assert.match(moved[0], /^probe-/);
    assert.equal(fs.readFileSync(path.join(trash, moved[0], 'conversations', 'kept.md'), 'utf8'), 'history\n');
    assert.match(removed.out, /moved:/);
  });

  function stale(home) {
    for (const name of ['CLAUDE.md', 'AGENTS.md']) {
      const file = path.join(home, name);
      const text = fs.readFileSync(file, 'utf8');
      const at = text.indexOf('\n## Purpose\n');
      assert.ok(at > 0, name);
      fs.writeFileSync(file, `# Standing instructions\n\nSTALE STANDING\n${text.slice(at)}\n`);
    }
  }

  await test('stale pair refreshed', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    stale(home);
    const kept = fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8').split('\n## Purpose\n')[1];
    const again = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(again.code, 0, again.out + again.err);
    const claude = fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8');
    const agents = fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8');
    assert.equal(claude, agents);
    assert.match(claude, /A turn is one shot/);
    assert.equal(claude.includes('STALE STANDING'), false);
    assert.match(claude, /Answer briefly/);
    assert.equal(claude.split('\n## Purpose\n')[1], kept.endsWith('\n') ? kept : `${kept}\n`);
  });

  await test('identical pair untouched', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    const file = path.join(home, 'CLAUDE.md');
    const twin = path.join(home, 'AGENTS.md');
    const before = fs.readFileSync(file, 'utf8');
    const mtime = fs.statSync(file).mtimeMs;
    const twinMtime = fs.statSync(twin).mtimeMs;
    const again = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(again.code, 0, again.out + again.err);
    assert.equal(fs.readFileSync(file, 'utf8'), before);
    assert.equal(fs.readFileSync(twin, 'utf8'), before);
    assert.equal(fs.statSync(file).mtimeMs, mtime);
    assert.equal(fs.statSync(twin).mtimeMs, twinMtime);
  });

  await test('dry-run writes nothing', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const home = path.join(dir, '.rbtv', 'agents', 'probe');
    stale(home);
    const before = {
      claude: fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8'),
      agents: fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8'),
      tree: tree(dir),
    };
    const calls = slack.calls.length;
    const result = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe', '--dry-run']), { slack });
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /writes: none/);
    assert.match(result.out, /STALE STANDING/);
    assert.match(result.out, /A turn is one shot/);
    assert.equal(fs.readFileSync(path.join(home, 'CLAUDE.md'), 'utf8'), before.claude);
    assert.equal(fs.readFileSync(path.join(home, 'AGENTS.md'), 'utf8'), before.agents);
    assert.deepEqual(tree(dir), before.tree);
    assert.equal(slack.calls.length, calls);
  });

  function mirrorSkill(dir, id) {
    const [cid, pid] = id.split('#');
    const folder = path.join(dir, '.rbtv', 'mirror', ...cid.split('/'));
    fs.mkdirSync(folder, { recursive: true });
    fs.writeFileSync(path.join(folder, 'exposure.csv'), [
      'part-id,part-kind,method,rbtv-cli,entry-point,description,write-roots',
      `${pid},capability,skill,,${pid}.md,fixture,`,
      '',
    ].join('\n'));
  }

  await test('repo skill resolves', async () => {
    const dir = workspace();
    writeConfig(dir);
    const result = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe', '--skill', 'core/communication#slack-message-format', '--dry-run']));
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /core\/communication#slack-message-format/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
  });

  await test('workspace-resident skill resolves', async () => {
    const dir = workspace();
    writeConfig(dir);
    mirrorSkill(dir, 'lab/widget#widget-skill');
    const result = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe', '--skill', 'lab/widget#widget-skill', '--dry-run']));
    assert.equal(result.code, 0, result.out + result.err);
    assert.match(result.out, /lab\/widget#widget-skill/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
  });

  await test('unknown skill is refused', async () => {
    const dir = workspace();
    writeConfig(dir);
    const args = baseArgs(dir, 'probe', ['--channel-name', 'probe', '--skill', 'lab/widget#missing', '--dry-run']);
    const before = tree(dir);
    const result = await run(args).catch((error) => ({
      code: error.exitCode || 1,
      out: '',
      err: error.message,
    }));
    assert.notEqual(result.code, 0);
    assert.match(result.err, /unknown skill: lab\/widget#missing/);
    assert.deepEqual(tree(dir), before);
  });

  await test('new home gets empty settings', async () => {
    const dir = workspace();
    writeConfig(dir);
    const args = baseArgs(dir, 'probe', ['--channel-name', 'probe', '--dry-run']);
    const preview = await run(args);
    assert.equal(preview.code, 0, preview.out + preview.err);
    assert.match(preview.out, /settings: \{\}/);
    assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'agents', 'probe')), false);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    assert.equal(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'probe', 'settings.json'), 'utf8'), '{}\n');
  });

  await test('settings-file seeds settings', async () => {
    const dir = workspace();
    writeConfig(dir);
    const file = path.join(dir, 'settings.json');
    fs.writeFileSync(file, '{"voice":"warm"}\n');
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe', '--settings-file', file]), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    assert.equal(fs.readFileSync(path.join(dir, '.rbtv', 'agents', 'probe', 'settings.json'), 'utf8'), '{\n  "voice": "warm"\n}\n');
  });

  await test('invalid settings JSON refused', async () => {
    const dir = workspace();
    writeConfig(dir);
    const file = path.join(dir, 'bad.json');
    fs.writeFileSync(file, '{');
    const args = baseArgs(dir, 'probe', ['--channel-name', 'probe', '--settings-file', file, '--dry-run']);
    const before = tree(dir);
    const result = await run(args).catch((error) => ({ code: error.exitCode || 1, out: '', err: error.message }));
    assert.notEqual(result.code, 0);
    assert.match(result.err, /not JSON/);
    assert.deepEqual(tree(dir), before);
  });

  await test('re-run keeps settings', async () => {
    const dir = workspace();
    writeConfig(dir);
    const slack = fakeSlack();
    const created = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(created.code, 0, created.out + created.err);
    const file = path.join(dir, '.rbtv', 'agents', 'probe', 'settings.json');
    fs.writeFileSync(file, '{"kept":true}\n');
    const mtime = fs.statSync(file).mtimeMs;
    const again = await run(baseArgs(dir, 'probe', ['--channel-name', 'probe']), { slack });
    assert.equal(again.code, 0, again.out + again.err);
    assert.equal(fs.readFileSync(file, 'utf8'), '{"kept":true}\n');
    assert.equal(fs.statSync(file).mtimeMs, mtime);
  });

  if (failures.length) {
    console.log(`FAILED ${failures.length}`);
    process.exit(1);
  }
  console.log('ok');
})().catch((error) => {
  console.log(`FAIL runner: ${error.stack || error.message}`);
  process.exit(1);
});
