'use strict';

// Fixture SQLite stores and disposable Git vaults; no live model or Slack calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');
const { Store } = require('./store.js');
const { EMPTY_BOARD, parseBoard } = require('./board.js');
const { runDreamer, castProposal, getState, saveState } = require('./dreamer.js');
const { remember } = require('./memory.js');

const tests = [];
function test(name, fn, slugs) { tests.push([name, fn, slugs]); }
const DATE = '2026-10-01';
const NOW = Date.parse(`${DATE}T12:00:00Z`);
const ROOT = '.rbtv/memory/';
const own = (slug = 'master') => `.rbtv/agents/${slug}/`;
const boardPath = (slug = 'master') => `${own(slug)}_artifacts/board.md`;
const learnedPath = (slug = 'master') => `${own(slug)}memory/learned.md`;
const link = (root = '1000.000001', channel = 'C1') => `https://app.slack.com/archives/${channel}/p${root.replace('.', '')}`;
const tail = (slug = 'master', root = '1000.000001') => `(${DATE} · ${slug}/[thread](${link(root)}))`;
const fact = (body, slug = 'master', root = '1000.000001') => `- ${body} ${tail(slug, root)}`;
const topic = (body = '', type = 'reference') => `---\ndescription: when reviewing this topic\ntype: ${type}\naliases: [topic]\n---\n# Topic\n\n${type === 'subject' ? `Threads: [thread](${link()})\n\n` : ''}${body}${body ? '\n' : ''}`;
const knowledge = (body = '') => topic(body, 'facts');
const profile = '# Profile — Owner\n\n## Who\n\n## Working with Owner\n\n## Now\n';
const subject = (state = 'Draft is ready.', detail = 'none') => `### Report\n${state}\n- Threads: [thread](${link()})\n- Detail: ${detail}\n- Flags: none`;
const board = ({ state, watch = [], closed = [], timers = [], detail } = {}) =>
  `## What matters now\n\n${state ? `${subject(state, detail)}\n\n` : ''}## Watch-outs\n\n${watch.join('\n')}${watch.length ? '\n\n' : ''}## Timers\n\n${timers.join('\n')}${timers.length ? '\n\n' : ''}## Recently closed\n\n${closed.join('\n')}${closed.length ? '\n' : ''}`;

function operation(input, name, text, extra = {}) {
  return { op: Object.hasOwn(input.files, name) ? 'supersede' : 'add', path: name, text,
    sources: input.messages.map((row) => row.rowid), reason: 'owner', explanation: 'Owner supplied this fact.', ...extra };
}
function proposal(...operations) { return { operations, conflicts: [] }; }

function fixture(slugs = ['master']) {
  const workspace = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-dreamer-test space-'));
  const stores = new Map();
  const config = { workspace, tools: { cast: 'cast' }, dmAgent: 'master', routes: Object.fromEntries(slugs.map((slug, i) => [`C${i + 1}`, slug])) };
  function write(name, text) { const file = path.join(workspace, name); fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, text, 'utf8'); }
  function read(name) { return fs.readFileSync(path.join(workspace, name), 'utf8'); }
  function git(...args) {
    const result = spawnSync('git', ['-C', workspace, ...args], { encoding: 'utf8', windowsHide: true });
    assert.equal(result.status, 0, `fixture git ${args[0]} failed: ${result.stderr}`);
    return result.stdout.trim();
  }
  git('init', '-q');
  git('config', 'user.name', 'Memory test');
  git('config', 'user.email', 'memory-test@example.invalid');
  git('config', 'commit.gpgsign', 'false');
  git('config', 'core.autocrlf', 'false');
  write('.gitignore', '*.sqlite*\n');
  write(`${ROOT}profile.md`, profile);
  write(`${ROOT}inbox.md`, '# Inbox — waiting to be filed\n');
  write(`${ROOT}_artifacts/index.md`, '# Memory\n\n| Open | When |\n|---|---|\n');
  for (const slug of slugs) {
    write(boardPath(slug), EMPTY_BOARD);
    write(learnedPath(slug), `# Learned rules — ${slug}\n`);
    write(`${own(slug)}agent.md`, `Owner instructions — ${slug}\r\n`);
    stores.set(slug, new Store(path.join(workspace, own(slug), 'state.sqlite')));
  }
  git('add', '--', '.gitignore', '.rbtv/memory', ...slugs.map(own));
  git('commit', '-qm', 'Fixture');
  function message({ slug = 'master', root = '1000.000001', role = 'owner', text = 'Owner fact.', createdAt = NOW,
    metadata = {}, agent = slug } = {}) {
    const store = stores.get(slug);
    const key = `T1:C1:${root}`;
    store.upsertConversation({ key, agent, workspace: 'T1', channel: 'C1', rootTs: root });
    store.recordMessage(key, { id: `message-${store.db.prepare('SELECT COUNT(*) AS n FROM messages').get().n}`,
      role, text, metadata, createdAt });
    return store.db.prepare('SELECT MAX(rowid) AS id FROM messages').get().id;
  }
  const run = (model, extra = {}) => runDreamer({ config, openStore: (slug) => stores.get(slug), model, now: NOW, ...extra });
  return { workspace, config, stores, write, read, git, message, run,
    cleanup() { for (const store of stores.values()) store.close(); fs.rmSync(workspace, { recursive: true, force: true }); } };
}

test('owner-only input, one scoped commit, persisted rowid cursor and untouched instructions', async (f) => {
  f.message({ role: 'assistant', text: 'Do not learn assistant text.' });
  f.message({ role: 'user', text: 'Do not learn another person.' });
  f.message({ metadata: { source: 'injected' }, text: 'Do not learn injected text.' });
  f.message({ metadata: { source: 'recalled' } });
  f.message({ metadata: { source: 'dreamer' } });
  const owner = f.message({ text: 'I speak português — café.' });
  f.write('unrelated.md', 'staged elsewhere\n'); f.git('add', '--', 'unrelated.md');
  const instructions = f.read(`${own()}agent.md`);
  const head = f.git('rev-parse', 'HEAD');
  const result = await f.run((input) => {
    assert.deepEqual(input.messages.map((row) => row.rowid), [owner]);
    assert.equal(input.cursor, 0);
    assert.equal(getState(f.stores.get('master')).cursor, 0);
    return JSON.stringify(proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Speaks português — café.')))));
  });
  assert.equal(result.ok, true, result.alert);
  assert.equal(result.changed, true);
  assert.equal(f.git('rev-list', '--count', `${head}..HEAD`), '1');
  assert.equal(f.git('show', '--pretty=format:', '--name-only', 'HEAD'), `${ROOT}knowledge/facts.md`);
  assert.equal(f.git('diff', '--cached', '--name-only'), 'unrelated.md');
  assert.equal(f.read(`${own()}agent.md`), instructions);
  assert.equal(getState(f.stores.get('master')).cursor, owner);
  assert.equal(getState(f.stores.get('master')).commit, result.commit);
  assert.equal(result.digest.agent, 'master');
  assert.match(f.read(`${ROOT}knowledge/facts.md`), /português — café/);
  const reopened = new Store(path.join(f.workspace, own(), 'state.sqlite'));
  try { assert.equal(getState(reopened).cursor, owner); } finally { reopened.close(); }
});

test('no-op is silent, makes no commit and records success without advancing its cursor', async (f) => {
  f.message(); const head = f.git('rev-parse', 'HEAD');
  const result = await f.run(() => proposal());
  assert.equal(result.ok, true, result.alert);
  assert.equal(result.changed, false); assert.equal(result.digest, null); assert.equal(result.alert, null);
  assert.equal(f.git('rev-parse', 'HEAD'), head);
  assert.deepEqual(getState(f.stores.get('master')), { cursor: 0, lastSuccessAt: NOW, commit: null, reportedConflicts: [] });
});

test('dreamer state accepts legacy records and validates reported-conflict lists', (f) => {
  const store = f.stores.get('master'); const legacy = { cursor: 0, lastSuccessAt: NOW, commit: null };
  const save = (state) => store.db.prepare("INSERT OR REPLACE INTO settings VALUES ('dreamer',?,?)").run(JSON.stringify(state), NOW);
  save(legacy); assert.deepEqual(getState(store), legacy);
  for (const reportedConflicts of ['conflict', {}, [1]]) {
    save({ ...legacy, reportedConflicts }); assert.throws(() => getState(store), /invalid reported conflicts/);
  }
  save({ ...legacy, reportedConflicts: ['Prior conflict.'] });
  assert.deepEqual(getState(store).reportedConflicts, ['Prior conflict.']);
});

test('late backfill with old created_at waits beyond the fixed rowid ceiling', async (f) => {
  const first = f.message(); let late;
  const result = await f.run((input) => {
    late = f.message({ root: '2000.000001', createdAt: 1 });
    assert.deepEqual(input.messages.map((row) => row.rowid), [first]);
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('First fact.'))));
  });
  assert.equal(result.ok, true, result.alert); assert.equal(getState(f.stores.get('master')).cursor, first);
  const second = await f.run((input) => {
    assert.deepEqual(input.messages.map((row) => row.rowid), [late]);
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, `${input.files[`${ROOT}knowledge/facts.md`]}${fact('Late fact.', 'master', '2000.000001')}\n`));
  });
  assert.equal(second.ok, true, second.alert); assert.equal(getState(f.stores.get('master')).cursor, late);
});

test('all agents run sequentially under ceilings captured before the first model call', async (f) => {
  f.message({ slug: 'alpha' }); f.message({ slug: 'master' });
  let active = 0; const seen = []; const head = f.git('rev-parse', 'HEAD');
  const result = await f.run(async (input) => {
    assert.equal(active++, 0); seen.push(input.agent);
    if (input.agent === 'alpha') f.message({ slug: 'master', root: '2000.000001' });
    await new Promise((resolve) => setImmediate(resolve));
    active--;
    assert.equal(input.messages.length, 1);
    if (input.agent === 'master') assert.ok(input.files[`${ROOT}knowledge/facts.md`]);
    const text = input.files[`${ROOT}knowledge/facts.md`] || knowledge();
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, `${text}${fact(`Fact from ${input.agent}.`, input.agent)}\n`),
      operation(input, learnedPath(input.agent), `${input.files[learnedPath(input.agent)]}${fact('[correction] Check the result. Why: owner correction.', input.agent)}\n`));
  });
  assert.equal(result.ok, true, result.alert); assert.deepEqual(seen, ['alpha', 'master']);
  assert.equal(f.git('rev-list', '--count', `${head}..HEAD`), '1');
  for (const store of f.stores.values()) assert.equal(getState(store).cursor, 1);
}, ['alpha', 'master']);

for (const changed of ['alpha', 'master']) test(`a commit by ${changed} preserves another agent's unread rows without operations`, async (f) => {
  const unchanged = changed === 'alpha' ? 'master' : 'alpha';
  const prior = f.message({ slug: unchanged });
  f.stores.get(unchanged).db.prepare("INSERT INTO settings VALUES ('dreamer',?,?)")
    .run(JSON.stringify({ cursor: prior, lastSuccessAt: 1, commit: f.git('rev-parse', 'HEAD') }), 1);
  const pending = f.message({ slug: unchanged, root: '2000.000001' });
  const consumed = f.message({ slug: changed });
  f.message({ slug: 'idle', role: 'assistant' });
  const idleCeiling = f.message({ slug: 'idle', metadata: { source: 'dreamer' } });
  const result = await f.run((input) => input.agent === changed ?
    proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Confirmed fact.', changed)))) : proposal());
  assert.equal(result.ok, true, result.alert); assert.ok(result.commit);
  assert.equal(getState(f.stores.get(changed)).cursor, consumed);
  assert.equal(getState(f.stores.get(unchanged)).cursor, prior);
  assert.equal(getState(f.stores.get('idle')).cursor, idleCeiling);
  const replay = await f.run((input) => {
    assert.deepEqual(input.messages.map((row) => row.rowid), input.agent === unchanged ? [pending] : []);
    return proposal();
  });
  assert.equal(replay.ok, true, replay.alert); assert.equal(replay.commit, null);
  assert.equal(getState(f.stores.get(unchanged)).cursor, prior);
}, ['alpha', 'idle', 'master']);

test('SQLite owner transcriptions remain valid evidence; unrelated conversations are excluded', async (f) => {
  const used = f.message({ metadata: { source: 'used-text', queueId: 'queue' } });
  f.message({ root: '2000.000001', agent: 'other' });
  const result = await f.run((input) => { assert.deepEqual(input.messages.map((row) => row.rowid), [used]); return proposal(); });
  assert.equal(result.ok, true, result.alert);
});

for (const bad of ['../outside.md', '/tmp/outside.md', 'C:/outside.md', '.rbtv/memory/../agent.md',
  '.rbtv/memory/knowledge\\facts.md', '.rbtv/memory/knowledge/NUL.md', '.rbtv/memory/knowledge/facts.md ',
  'core/ignite/agent.md', `${own()}agent.md`, learnedPath('other'), '4-archives/private.md']) {
  test(`refuses out-of-scope or nonportable path ${bad}`, async (f) => {
    f.message(); const instructions = f.read(`${own()}agent.md`);
    const result = await f.run((input) => proposal(operation(input, bad, knowledge(fact('Unsafe.')))));
    assert.equal(result.ok, false); assert.ok(result.alert); assert.equal(result.commit, null);
    assert.equal(getState(f.stores.get('master')).cursor, 0); assert.equal(f.read(`${own()}agent.md`), instructions);
  });
}

test('refuses symlink traversal into another folder', async (f, ctx) => {
  const target = path.join(f.workspace, 'external'); fs.mkdirSync(target);
  try { fs.symlinkSync(target, path.join(f.workspace, ROOT, 'knowledge'), process.platform === 'win32' ? 'junction' : 'dir'); }
  catch (error) { if (process.platform === 'win32' && error.code === 'EPERM') return ctx.skip('Windows host disallows symlink/junction creation'); throw error; }
  f.message();
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Cannot escape.')))));
  assert.equal(result.ok, false); assert.match(result.alert, /symlink/); assert.deepEqual(fs.readdirSync(target), []);
});

test('archive directories outside memory are never read', async (f) => {
  f.write('4-archives/private.md', 'not input');
  const result = await f.run((input) => { assert.ok(!JSON.stringify(input).includes('not input')); return proposal(); });
  assert.equal(result.ok, true, result.alert);
});

test('legacy migration pointers are left untouched and excluded from evidence', async (f) => {
  f.write(`${ROOT}user/background.md`, 'legacy pointer content');
  const result = await f.run((input) => { assert.ok(!JSON.stringify(input).includes('legacy pointer content')); return proposal(); });
  assert.equal(result.ok, true, result.alert); assert.equal(f.read(`${ROOT}user/background.md`), 'legacy pointer content');
});

test('invalid JSON and model failures alert without exposing model output', async (f) => {
  f.message();
  for (const model of [() => 'sensitive malformed response', () => { throw new Error('sensitive provider response'); }]) {
    const result = await f.run(model);
    assert.equal(result.ok, false); assert.ok(result.alert); assert.ok(!result.alert.includes('sensitive'));
    assert.equal(getState(f.stores.get('master')).cursor, 0);
  }
});

for (const source of ['missing', 'assistant', 'forged-link', 'consumed']) {
  test(`refuses ${source} evidence`, async (f) => {
    const owner = f.message(); const assistant = f.message({ role: 'assistant' });
    if (source === 'consumed') f.stores.get('master').db.prepare("INSERT INTO settings VALUES ('dreamer',?,?)").run(JSON.stringify({ cursor: owner, lastSuccessAt: 1, commit: 'before' }), 1);
    const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`,
      knowledge(fact('Unproven.', 'master', source === 'forged-link' ? '9999.000001' : undefined)),
      { sources: source === 'missing' ? [] : [source === 'assistant' ? assistant : owner] })));
    assert.equal(result.ok, false); assert.match(result.alert, /evidence|provenance|source/);
    assert.equal(fs.existsSync(path.join(f.workspace, ROOT, 'knowledge/facts.md')), false);
  });
}

test('a correction needs one conversation; an inference needs two distinct conversations', async (f) => {
  f.message(); f.message();
  const same = `- [inferred] Ask before booking. Why: repeated refusals. (${DATE} · master/[one](${link()}) · master/[two](${link()}?thread_ts=1000.000001))`;
  const rejected = await f.run((input) => proposal(operation(input, learnedPath(), `${input.files[learnedPath()]}${same}\n`)));
  assert.equal(rejected.ok, false); assert.match(rejected.alert, /two separate/);
  f.message({ root: '2000.000001' });
  const different = same.replace(`${link()}?thread_ts=1000.000001`, link('2000.000001'));
  const accepted = await f.run((input) => proposal(operation(input, learnedPath(), `${input.files[learnedPath()]}${different}\n${fact('[correction] Confirm dates. Why: owner correction.')}\n`)));
  assert.equal(accepted.ok, true, accepted.alert);
});

for (const [name, text, expected] of [
  [`${ROOT}profile.md`, `${profile}${fact('x'.repeat(4000))}\n`, /profile.*cap/],
  [learnedPath(), '# Learned rules — master\n' + Array.from({ length: 31 }, (_, i) => `${fact(`[correction] Rule ${i}. Why: owner correction.`)}\n`).join(''), /learned.*cap/],
  [`${own()}memory/topic.md`, topic(fact('x'.repeat(3000))), /3000/],
  [`${ROOT}workspaces/work.md`, topic(fact('x'.repeat(3000)), 'workspace').replace('aliases: [topic]', 'aliases: [topic]\npaths: [work]'), /workspace.*cap/],
  [boardPath(), board({ watch: Array.from({ length: 7 }, (_, i) => fact(`Watch ${i}.`)) }), /board.*cap/],
  [`${ROOT}timeline/daily/${DATE}.md`, `---\ndescription: when asked about this date\n---\n# ${DATE}\n\n` + Array.from({ length: 40 }, (_, i) => `- Event ${i} — master/[thread](${link()})\n`).join(''), /40 lines/],
  [`${ROOT}timeline/weekly/2026-W39.md`, '---\ndescription: when asked about this week\n---\n# 2026-W39\n\n' + Array.from({ length: 25 }, (_, i) => `- Event ${i} — [${DATE}](../daily/${DATE}.md)\n`).join(''), /25 lines/],
]) test(`refuses the cap for ${name}`, async (f) => {
  f.message(); const head = f.git('rev-parse', 'HEAD');
  const result = await f.run((input) => proposal(operation(input, name, text)));
  assert.equal(result.ok, false); assert.match(result.alert, expected); assert.equal(f.git('rev-parse', 'HEAD'), head);
});

test('inbox lines are filed before removal and watch-outs become correction rules in the same commit', async (f) => {
  f.message();
  const inbox = fact('Owner speaks French.'); const watch = fact('Send one PDF.');
  const rule = fact('[correction] Send one PDF. Why: owner correction.');
  f.write(`${ROOT}inbox.md`, `# Inbox — waiting to be filed\r\n\r\n${inbox}\r\n`);
  f.write(boardPath(), board({ watch: [watch] }).replaceAll('\n', '\r\n'));
  const result = await f.run((input) => proposal(
    operation(input, `${ROOT}knowledge/facts.md`, knowledge(inbox)),
    operation(input, `${ROOT}inbox.md`, '# Inbox — waiting to be filed\n', { reason: 'file', removals: [{ text: inbox, to: `${ROOT}knowledge/facts.md`, replacement: inbox }] }),
    operation(input, learnedPath(), `${input.files[learnedPath()]}${rule}\n`),
    operation(input, boardPath(), EMPTY_BOARD, { reason: 'fold', removals: [{ text: watch, to: learnedPath(), replacement: rule }] }),
  ));
  assert.equal(result.ok, true, result.alert);
  assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(inbox)); assert.ok(f.read(learnedPath()).includes(rule));
  assert.equal(parseBoard(f.read(boardPath())).watchOuts.length, 0);
  assert.equal(f.read(`${ROOT}inbox.md`), '# Inbox — waiting to be filed\r\n');
  assert.equal(f.git('show', '--pretty=format:', '--name-only', 'HEAD').split('\n').length, 4);
  const audit = f.git('log', '-1', '--pretty=%B');
  for (const record of [inbox, watch, rule]) assert.ok(audit.includes(record), 'commit explains even previously uncommitted records');
});

for (const ending of ['\n', '\r\n']) for (const thread of [null, `[thread](${link()})`]) {
  test(`remember alone can be filed using its own provenance (${JSON.stringify(ending)}, thread=${Boolean(thread)})`, async (f) => {
    remember(f.workspace, 'Owner likes café (2026-01-01 · verbal).', { agent: 'master', thread, now: NOW });
    const inbox = f.read(`${ROOT}inbox.md`).replaceAll('\n', ending);
    f.write(`${ROOT}inbox.md`, inbox);
    const line = inbox.split(/\r?\n/).find((row) => row.startsWith('- '));
    const replacement = line.replace('Owner likes café', 'Prefers café');
    const head = f.git('rev-parse', 'HEAD');
    const result = await f.run((input) => {
      assert.deepEqual(input.messages, []);
      return proposal(
        operation(input, `${ROOT}knowledge/facts.md`, knowledge(replacement), { sources: [line], reason: 'file' }),
        operation(input, `${ROOT}inbox.md`, '# Inbox\n', { sources: [line], reason: 'file',
          removals: [{ text: line, to: `${ROOT}knowledge/facts.md`, replacement }] }),
      );
    });
    assert.equal(result.ok, true, result.alert); assert.ok(result.commit); assert.ok(result.digest);
    assert.equal(f.read(`${ROOT}inbox.md`), `# Inbox${ending}`);
    assert.equal(f.read(`${ROOT}knowledge/facts.md`), knowledge(replacement));
    assert.equal(f.git('rev-list', '--count', `${head}..HEAD`), '1');
    assert.ok(f.git('log', '-1', '--pretty=%B').includes(line));
    assert.equal(getState(f.stores.get('master')).lastSuccessAt, NOW);
    assert.equal(getState(f.stores.get('master')).cursor, 0);
  });
}

test('each agent files its own inbox sources even after its owner rows were consumed', async (f) => {
  const lines = ['alpha', 'master'].map((slug) => fact(`Fact from ${slug}.`, slug));
  for (const slug of ['alpha', 'master']) {
    const cursor = f.message({ slug });
    f.stores.get(slug).db.prepare("INSERT INTO settings VALUES ('dreamer',?,?)")
      .run(JSON.stringify({ cursor, lastSuccessAt: 1, commit: 'prior' }), 1);
  }
  f.write(`${ROOT}inbox.md`, `# Inbox\n${lines.join('\n')}\n`);
  const result = await f.run((input) => {
    assert.deepEqual(input.messages, []);
    const line = lines[input.agent === 'alpha' ? 0 : 1];
    return proposal(
      operation(input, `${ROOT}knowledge/facts.md`, `${input.files[`${ROOT}knowledge/facts.md`] || knowledge()}${line}\n`, { sources: [line] }),
      operation(input, `${ROOT}inbox.md`, input.files[`${ROOT}inbox.md`].replace(`${line}\n`, ''), { sources: [line], reason: 'file',
        removals: [{ text: line, to: `${ROOT}knowledge/facts.md`, replacement: line }] }),
    );
  });
  assert.equal(result.ok, true, result.alert); assert.ok(result.commit);
  assert.equal(f.read(`${ROOT}inbox.md`), '# Inbox\n');
  for (const line of lines) assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(line));
}, ['alpha', 'master']);

for (const mode of ['forged-line', 'other-agent', 'changed-provenance', 'unfiled-source', 'learned-rule']) {
  test(`inbox provenance cannot authorize ${mode}`, async (f) => {
    const line = fact('Owner likes café.', mode === 'other-agent' ? 'alpha' : 'master');
    f.write(`${ROOT}inbox.md`, `# Inbox\n${line}\n`);
    const head = f.git('rev-parse', 'HEAD');
    const result = await f.run((input) => {
      const target = mode === 'learned-rule' ? learnedPath() : `${ROOT}knowledge/facts.md`;
      const replacement = mode === 'changed-provenance' ? fact('Owner likes café.', 'master', '2000.000001') :
        mode === 'learned-rule' ? fact('[inferred] Offer café. Why: remembered preference.') : line.replace('Owner likes café.', 'Prefers café.');
      const sources = [mode === 'forged-line' ? line.replace('café', 'tea') : line];
      return proposal(operation(input, target, mode === 'learned-rule' ? `# Learned rules — master\n${replacement}\n` : knowledge(replacement), { sources }),
        ...(mode === 'unfiled-source' ? [] : [operation(input, `${ROOT}inbox.md`, '# Inbox\n', { sources, reason: 'file',
          removals: [{ text: line, to: target, replacement }] })]));
    });
    assert.equal(result.ok, false); assert.equal(result.digest, null);
    assert.equal(f.read(`${ROOT}inbox.md`), `# Inbox\n${line}\n`);
    assert.equal(f.git('rev-parse', 'HEAD'), head);
    assert.equal(getState(f.stores.get('master')).lastSuccessAt, null);
  });
}

for (const ending of ['\n', '\r\n']) test(`a no-link watch-out folds with owner thread evidence and its original date (${JSON.stringify(ending)})`, async (f) => {
  f.message(); const ceiling = f.message({ root: '2000.000001' });
  const watch = '- Send one PDF. (2026-09-30 · master)';
  const rule = `- [correction] Send one PDF. Why: owner correction. (2026-09-30 · master/[one](${link()}) · master/[two](${link('2000.000001')}))`;
  f.write(boardPath(), board({ watch: [watch] }).replaceAll('\n', ending));
  f.write(learnedPath(), `# Learned rules — master${ending}`);
  const result = await f.run((input) => proposal(
    operation(input, learnedPath(), `${input.files[learnedPath()]}${rule}\n`),
    operation(input, boardPath(), EMPTY_BOARD, { reason: 'fold', removals: [{ text: watch, to: learnedPath(), replacement: rule }] }),
  ));
  assert.equal(result.ok, true, result.alert); assert.ok(result.commit);
  assert.equal(f.read(learnedPath()), `# Learned rules — master${ending}${rule}${ending}`);
  assert.equal(f.read(boardPath()), EMPTY_BOARD.replaceAll('\n', ending));
  assert.equal(getState(f.stores.get('master')).cursor, ceiling);
  assert.ok(f.git('log', '-1', '--pretty=%B').includes(watch));
});

for (const mode of ['changed-date', 'wrong-agent', 'inferred', 'no-why', 'no-link', 'no-sources', 'uncited-second-thread', 'malformed-tail']) {
  test(`a no-link watch-out refuses ${mode} replacement evidence`, async (f) => {
    const first = f.message(); f.message({ root: '2000.000001' });
    const watch = `- Send one PDF. (${DATE} · master)`;
    let rule = fact('[correction] Send one PDF. Why: owner correction.');
    if (mode === 'changed-date') rule = rule.replace(DATE, '2026-09-30');
    if (mode === 'wrong-agent') rule = rule.replace('master/', 'other/');
    if (mode === 'inferred') rule = rule.replace('[correction]', '[inferred]').replace(/\)$/, ` · master/[two](${link('2000.000001')}))`);
    if (mode === 'no-why') rule = rule.replace(' Why: owner correction.', '');
    if (mode === 'no-link') rule = rule.replace(`master/[thread](${link()})`, 'master');
    if (mode === 'uncited-second-thread') rule = rule.replace(/\)$/, ` · master/[two](${link('2000.000001')}))`);
    if (mode === 'malformed-tail') rule = rule.replace(/\)$/, ' · master/no-thread)');
    f.write(boardPath(), board({ watch: [watch] }));
    const before = f.read(learnedPath()); const head = f.git('rev-parse', 'HEAD');
    const result = await f.run((input) => proposal(
      operation(input, learnedPath(), `${before}${rule}\n`),
      operation(input, boardPath(), EMPTY_BOARD, { reason: 'fold', sources: mode === 'no-sources' ? [] : [first],
        removals: [{ text: watch, to: learnedPath(), replacement: rule }] }),
    ));
    assert.equal(result.ok, false); assert.equal(result.commit, null);
    assert.equal(f.read(learnedPath()), before); assert.ok(f.read(boardPath()).includes(watch));
    assert.equal(f.git('rev-parse', 'HEAD'), head); assert.equal(getState(f.stores.get('master')).cursor, 0);
  });
}

for (const provenance of ['master', 'master/[note](https://example.com/note)']) {
  for (const unread of [false, true]) test(`watch-out with ${provenance} and unread=${unread} waits in the digest while another agent commits`, async (f) => {
    f.message({ slug: 'alpha' });
    if (unread) f.message({ root: 'board' });
    const ceiling = f.message({ metadata: { source: 'injected' } });
    const watch = `- Send one PDF. (${DATE} · ${provenance})`;
    const original = board({ watch: [watch] }).replaceAll('\n', '\r\n');
    f.write(boardPath(), original);
    const result = await f.run((input) => input.agent === 'alpha' ?
      proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Confirmed fact.', 'alpha')))) : proposal());
    assert.equal(result.ok, true, result.alert); assert.ok(result.commit);
    assert.equal(result.digest.agent, 'master'); assert.equal(result.digest.conflicts.length, 1);
    assert.ok(result.digest.conflicts[0].includes(watch));
    assert.equal(f.read(boardPath()), original); assert.equal(f.read(learnedPath()), '# Learned rules — master\n');
    assert.equal(getState(f.stores.get('alpha')).cursor, 1);
    assert.equal(getState(f.stores.get('master')).cursor, unread ? 0 : ceiling);
    for (const store of f.stores.values()) {
      assert.deepEqual(getState(store).reportedConflicts, []);
      // Simulate the daemon acknowledging a delivered digest.
      saveState(store, { ...getState(store), reportedConflicts: result.digest.conflicts }, NOW);
    }
    const retried = await f.run(() => proposal());
    assert.equal(retried.ok, true, retried.alert); assert.equal(retried.commit, null);
    assert.equal(retried.digest, null); assert.equal(f.read(boardPath()), original);
    assert.ok(getState(f.stores.get('master')).reportedConflicts.some((line) => line.includes(watch)));
  }, ['alpha', 'master']);
}

for (const mode of ['no-link-with-owner-thread', 'slack-link-with-owner-thread']) {
  test(`remaining watch-outs still refuse ${mode}`, async (f) => {
    f.message();
    const watch = mode === 'no-link-with-owner-thread' ? `- Send one PDF. (${DATE} · master)` : fact('Send one PDF.');
    f.write(boardPath(), board({ watch: [watch] }));
    const result = await f.run(() => proposal());
    assert.equal(result.ok, false); assert.match(result.alert, /all watch-outs must be folded/);
    assert.equal(result.commit, null); assert.ok(f.read(boardPath()).includes(watch));
    assert.equal(getState(f.stores.get('master')).cursor, 0);
  });
}

for (const unread of [false, true]) test(`a linked watch-out defers without matching unread evidence (unread=${unread})`, async (f) => {
  if (unread) f.message({ root: '2000.000001' });
  const watch = fact('Send one PDF.');
  const text = board({ watch: [watch] }); f.write(boardPath(), text);
  const result = await f.run(() => proposal());
  assert.equal(result.ok, true, result.alert); assert.equal(result.commit, null);
  assert.ok(result.digest.conflicts[0].includes(watch));
  assert.deepEqual((await f.run(() => proposal())).digest, result.digest);
  assert.deepEqual(getState(f.stores.get('master')).reportedConflicts, []);
  assert.equal(f.read(boardPath()), text); assert.equal(getState(f.stores.get('master')).lastSuccessAt, NOW);
});

for (const mode of ['unexplained', 'unfiled', 'missing-destination', 'wrong-destination', 'changed-provenance', 'unfolded', 'inferred-watch']) {
  test(`refuses ${mode} inbox/watch-out processing`, async (f) => {
    f.message(); const line = fact('Retain this correction.');
    const watch = ['unfolded', 'inferred-watch'].includes(mode);
    f.write(watch ? boardPath() : `${ROOT}inbox.md`, watch ? board({ watch: [line] }) : `# Inbox\n${line}\n`);
    const result = await f.run((input) => {
      if (mode === 'unfiled' || mode === 'unfolded') return proposal();
      const target = mode === 'wrong-destination' ? `${own()}memory/topic.md` : watch ? learnedPath() : `${ROOT}knowledge/facts.md`;
      const replacement = mode === 'changed-provenance' ? fact('Retain this correction.', 'master', '2000.000001') : watch ? fact('[inferred] Retain this correction. Why: repeated.') : line;
      const destination = operation(input, target, watch ? `# Learned rules — master\n${replacement}\n` : target.includes('/knowledge/') ? knowledge(replacement) : topic(replacement));
      return proposal(...(mode === 'missing-destination' ? [] : [destination]),
        operation(input, watch ? boardPath() : `${ROOT}inbox.md`, watch ? EMPTY_BOARD : '# Inbox\n', {
          reason: watch ? 'fold' : 'file', removals: mode === 'unexplained' ? [] : [{ text: line, to: target, replacement }],
        }));
    });
    assert.equal(result.ok, false); assert.equal(getState(f.stores.get('master')).cursor, 0);
    assert.ok(f.read(watch ? boardPath() : `${ROOT}inbox.md`).includes(line));
  });
}

test('explained supersession keeps history and puts learned-rule conflicts in the digest', async (f) => {
  f.message(); const old = fact('[correction] Send plain text. Why: owner preference.');
  const next = fact('[correction] Send one PDF. Why: owner corrected the format.');
  f.write(learnedPath(), `# Learned rules — master\n${old}\n`); f.git('add', '--', learnedPath()); f.git('commit', '-qm', 'Old rule');
  const result = await f.run((input) => ({ operations: [operation(input, learnedPath(), `# Learned rules — master\n${next}\n`, { removals: [{ text: old }] })], conflicts: ['Owner changed the desired format.'] }));
  assert.equal(result.ok, true, result.alert); assert.match(result.digest.text, /Conflict:.*format/);
  assert.ok(f.git('show', `HEAD^:${learnedPath()}`).includes(old)); assert.ok(!f.read(learnedPath()).includes(old));
});

test('a model cannot remove a second record behind an explained supersession', async (f) => {
  f.message(); const old = fact('Old fact.'); const keep = fact('Rare truth.');
  f.write(`${ROOT}knowledge/facts.md`, knowledge(`${old}\n${keep}`));
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('New fact.')), { removals: [{ text: old }] })));
  assert.equal(result.ok, false); assert.match(result.alert, /vanish unexplained/); assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(keep));
});

for (const ending of ['until 2026-09-30', 'until 2026-10-01', 'until 2026-10-02', 'since 2020-01-01', 'rarely used', 'until 2026-02-30']) {
  test(`expiry considers only explicit past end dates: ${ending}`, async (f) => {
    const line = fact(`Temporary situation ${ending}`); const name = `${ROOT}knowledge/facts.md`;
    f.write(name, knowledge(line));
    const result = await f.run((input) => proposal(
      operation(input, `${ROOT}_artifacts/archive/expired.md`, topic(line), { sources: [] }),
      operation(input, name, knowledge(), { op: 'archive', reason: 'expired', sources: [], removals: [{ text: line, to: `${ROOT}_artifacts/archive/expired.md` }] }),
    ));
    if (ending === 'until 2026-09-30') {
      assert.equal(result.ok, true, result.alert); assert.ok(fs.existsSync(path.join(f.workspace, name)));
      assert.ok(f.read(`${ROOT}_artifacts/archive/expired.md`).includes(line));
    } else { assert.equal(result.ok, false); assert.ok(f.read(name).includes(line)); }
  });
}

for (const ending of ['\n', '\r\n']) test(`expiry preserves an earlier provenance lookalike (${JSON.stringify(ending)})`, async (f) => {
  const line = fact('See (2026-01-01 · verbal) until 2026-09-30.');
  const name = `${ROOT}knowledge/facts.md`; const target = `${ROOT}_artifacts/archive/expired.md`;
  f.write(name, knowledge(line).replaceAll('\n', ending));
  const result = await f.run((input) => proposal(
    operation(input, target, topic(line), { sources: [] }),
    operation(input, name, knowledge(), { op: 'archive', reason: 'expired', sources: [], removals: [{ text: line, to: target }] }),
  ));
  assert.equal(result.ok, true, result.alert); assert.ok(result.commit);
  assert.equal(f.read(name), knowledge().replaceAll('\n', ending)); assert.ok(f.read(target).includes(line));
});

test('archive refuses deletion without a verbatim destination', async (f) => {
  f.message(); const old = fact('Old record.'); f.write(`${ROOT}knowledge/facts.md`, knowledge(old));
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(), { op: 'archive', removals: [{ text: old }] })));
  assert.equal(result.ok, false); assert.match(result.alert, /preserved verbatim/);
});

test('closed records are archived into agent topics and board subjects retain moved detail', async (f) => {
  const closed = fact('Lunch — booked.'); const old = subject('Draft is ready.\nReview is pending.');
  f.write(boardPath(), board({ state: 'Draft is ready.\nReview is pending.', closed: [closed] }));
  f.message();
  const topicPath = `${own()}memory/report.md`;
  const detail = `${fact('Draft is ready.')}\n${fact('Review is pending.')}`;
  const result = await f.run((input) => proposal(
    operation(input, topicPath, topic(detail, 'subject')),
    operation(input, boardPath(), board({ state: 'Review is pending.', detail: '../memory/report.md', closed: [closed] }), {
      reason: 'detail', removals: [{ text: old, to: topicPath }],
    }),
  ));
  assert.equal(result.ok, true, result.alert);
  const archivePath = `${own()}memory/lunch.md`;
  const second = await f.run((input) => proposal(
    operation(input, archivePath, topic(closed, 'subject'), { sources: [] }),
    operation(input, boardPath(), input.files[boardPath()].replace(`${closed}\n`, ''), { op: 'archive', reason: 'closed', sources: [], removals: [{ text: closed, to: archivePath }] }),
  ));
  assert.equal(second.ok, true, second.alert); assert.ok(f.read(archivePath).includes(closed));
  assert.equal(parseBoard(f.read(boardPath())).subjects[0].detail, '../memory/report.md');
});

test('moving board detail preserves exact state with a relative source without inventing owner evidence', async (f) => {
  f.write(boardPath(), board({ state: 'Draft is ready.\nReview is pending.' }));
  const target = `${own()}memory/report.md`;
  const copied = ['Draft is ready.', 'Review is pending.'].map((line) => `- ${line} (${DATE} · ../_artifacts/board.md)`).join('\n');
  const result = await f.run((input) => proposal(operation(input, target, topic(copied, 'subject'), { sources: [] }),
    operation(input, boardPath(), board({ state: 'Review is pending.', detail: '../memory/report.md' }), {
      reason: 'detail', sources: [], removals: [{ text: subject('Draft is ready.\nReview is pending.'), to: target }],
    })));
  assert.equal(result.ok, true, result.alert); assert.ok(f.read(target).includes(copied));
});

test('new learned rules cannot use existing memory relocation as owner evidence', async (f) => {
  const old = fact('[correction] Confirm dates. Why: temporary need until 2026-09-30');
  f.write(`${ROOT}knowledge/facts.md`, knowledge(old));
  const result = await f.run((input) => proposal(operation(input, learnedPath(), `# Learned rules — master\n${old}\n`, { sources: [] }),
    operation(input, `${ROOT}knowledge/facts.md`, knowledge(), { op: 'archive', reason: 'expired', sources: [], removals: [{ text: old, to: learnedPath() }] })));
  assert.equal(result.ok, false); assert.match(result.alert, /owner evidence/);
});

for (const field of ['subject', 'timers', 'flags', 'threads']) test(`dreamer cannot rewrite board ${field}`, async (f) => {
  f.message(); f.write(boardPath(), board({ state: 'Draft is ready.' }));
  const result = await f.run((input) => {
    let text = input.files[boardPath()];
    if (field === 'subject') text = text.replace(`${subject()}\n\n`, '');
    if (field === 'timers') text = text.replace('## Timers\n', '## Timers\n\n| Fires | Timer | For | Subject |\n|---|---|---|---|\n| 2026-10-02 09:00 UTC | test | check | none |\n');
    if (field === 'flags') text = text.replace('- Flags: none', '- Flags: answered 2026-10-01');
    if (field === 'threads') text = text.replace(`- Threads: [thread](${link()})`, '- Threads: none');
    return proposal(operation(input, boardPath(), text, { removals: field === 'timers' ? [] : [{ text: subject() }] }));
  });
  assert.equal(result.ok, false); assert.match(result.alert, /runtime board/);
});

for (const racing of ['board', 'inbox']) test(`unchanged-since-read retries ${racing} once using fresh bytes`, async (f) => {
  f.message(); const name = racing === 'board' ? boardPath() : `${ROOT}inbox.md`;
  let calls = 0;
  const result = await f.run((input) => {
    calls++;
    if (calls === 1) f.write(name, `${f.read(name)}\n`);
    else assert.equal(input.files[name], f.read(name));
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Remember this.'))));
  });
  assert.equal(result.ok, true, result.alert); assert.equal(calls, 2);
});

test('a racing inbox append is filed from the re-read, without dropping either line', async (f) => {
  f.message(); const first = fact('First fact.'); const second = fact('Second fact.');
  f.write(`${ROOT}inbox.md`, `# Inbox\n${first}\n`); let calls = 0;
  const result = await f.run((input) => {
    if (++calls === 1) f.write(`${ROOT}inbox.md`, `# Inbox\n${first}\n${second}\n`);
    const lines = input.files[`${ROOT}inbox.md`].split(/\r?\n/).filter((row) => row.startsWith('- '));
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(lines.join('\n'))),
      operation(input, `${ROOT}inbox.md`, '# Inbox\n', { reason: 'file', removals: lines.map((text) => ({ text, to: `${ROOT}knowledge/facts.md`, replacement: text })) }));
  });
  assert.equal(result.ok, true, result.alert); assert.equal(calls, 2);
  assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(first)); assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(second));
});

for (const racing of ['inbox', 'board']) test(`a process writing ${racing} after comparison waits for publication and survives`, async (f) => {
  f.message();
  const first = fact('First fact.');
  const nextBoard = board({ state: 'Review is pending.', detail: '../memory/report.md' });
  if (racing === 'inbox') f.write(`${ROOT}inbox.md`, `# Inbox\n${first}\n`);
  else f.write(boardPath(), board({ state: 'Draft is ready.\nReview is pending.' }));
  const waiting = path.join(f.workspace, 'writer-waiting');
  const finished = path.join(f.workspace, 'writer-finished');
  const lock = path.join(f.workspace, '.rbtv', 'runtime', 'ignite-memory.lock');
  const program = `
    const fs = require('node:fs');
    const [base, workspace, mode, lock, waiting, finished] = process.argv.slice(1);
    const open = fs.openSync;
    fs.openSync = (file, ...args) => {
      try { return open(file, ...args); }
      catch (error) {
        if (file === lock && error.code === 'EEXIST') fs.writeFileSync(waiting, 'waiting', 'utf8');
        throw error;
      }
    };
    if (mode === 'inbox') require(base + '/memory.js').remember(workspace, 'Concurrent café fact', { agent: 'another' });
    else require(base + '/board.js').closeSubject(workspace + '/.rbtv/agents/master/_artifacts/board.md', 'Report', 'Concurrent closure', { agent: 'master' });
    fs.writeFileSync(finished, 'done', 'utf8');
  `;
  const write = fs.writeFileSync;
  let child; let done; let injected = false;
  fs.writeFileSync = (file, body, ...args) => {
    if (!injected && typeof file === 'number' && body === (racing === 'inbox' ? '# Inbox\n' : nextBoard)) {
      injected = true;
      assert.ok(fs.existsSync(lock));
      child = spawn(process.execPath, ['-e', program, __dirname, f.workspace, racing, lock, waiting, finished], { stdio: 'ignore' });
      done = new Promise((resolve, reject) => {
        child.once('error', reject);
        child.once('exit', (code) => code === 0 ? resolve() : reject(new Error(`racing writer exit ${code}`)));
      });
      const deadline = Date.now() + 3000;
      while (!fs.existsSync(waiting) && Date.now() < deadline) Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 10);
      assert.ok(fs.existsSync(waiting), 'writer attempted the held lock before Dreamer wrote');
      assert.equal(fs.existsSync(finished), false);
    }
    return write(file, body, ...args);
  };
  let result;
  try {
    result = await f.run((input) => {
      assert.equal(fs.existsSync(lock), false, 'model calls never hold the publication lock');
      if (racing === 'inbox') return proposal(
        operation(input, `${ROOT}knowledge/facts.md`, knowledge(first)),
        operation(input, `${ROOT}inbox.md`, '# Inbox\n', { reason: 'file', removals: [{ text: first, to: `${ROOT}knowledge/facts.md`, replacement: first }] }));
      const target = `${own()}memory/report.md`;
      return proposal(operation(input, target, topic(`${fact('Draft is ready.')}
${fact('Review is pending.')}`, 'subject')),
        operation(input, boardPath(), nextBoard, { reason: 'detail', removals: [{ text: subject('Draft is ready.\nReview is pending.'), to: target }] }));
    });
  } finally { fs.writeFileSync = write; }
  if (done) await done;
  assert.ok(injected); assert.equal(result.ok, true, result.alert);
  assert.equal(fs.existsSync(lock), false);
  if (racing === 'inbox') {
    assert.ok(f.read(`${ROOT}knowledge/facts.md`).includes(first));
    assert.match(f.read(`${ROOT}inbox.md`), /Concurrent café fact/);
  } else {
    const current = parseBoard(f.read(boardPath()));
    assert.equal(current.subjects.length, 0);
    assert.match(current.closed[0], /Concurrent closure/);
    assert.ok(f.read(`${own()}memory/report.md`).includes('Draft is ready.'));
  }
});

test('second race alerts, leaves concurrent bytes and cursors untouched', async (f) => {
  f.message(); let calls = 0; const head = f.git('rev-parse', 'HEAD');
  const result = await f.run((input) => {
    calls++; f.write(boardPath(), `${f.read(boardPath())}\n`);
    return proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Remember this.'))));
  });
  assert.equal(result.ok, false); assert.match(result.alert, /changed again/); assert.equal(calls, 2);
  assert.equal(f.read(boardPath()), `${EMPTY_BOARD}\n\n`); assert.equal(f.git('rev-parse', 'HEAD'), head);
  assert.equal(getState(f.stores.get('master')).cursor, 0);
});

test('validation failure in a later agent writes nothing for any agent', async (f) => {
  f.message({ slug: 'alpha' }); f.message();
  const result = await f.run((input) => input.agent === 'master' ? 'invalid' : proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Alpha fact.', 'alpha')))));
  assert.equal(result.ok, false); assert.equal(fs.existsSync(path.join(f.workspace, ROOT, 'knowledge/facts.md')), false);
  for (const store of f.stores.values()) assert.equal(getState(store).cursor, 0);
}, ['alpha', 'master']);

test('commit failure returns an alert, restores working bytes and never advances a cursor', async (f) => {
  f.message(); const original = f.read(`${ROOT}profile.md`); const head = f.git('rev-parse', 'HEAD');
  fs.writeFileSync(path.join(f.workspace, '.git', 'index.lock'), 'held by fixture\n', 'utf8');
  const result = await f.run((input) => proposal(operation(input, `${ROOT}profile.md`, `${original}${fact('Owner fact.')}\n`)));
  fs.unlinkSync(path.join(f.workspace, '.git', 'index.lock'));
  assert.equal(result.ok, false); assert.match(result.alert, /git/); assert.equal(f.read(`${ROOT}profile.md`), original);
  assert.equal(f.git('rev-parse', 'HEAD'), head); assert.equal(getState(f.stores.get('master')).cursor, 0);
});

for (const existing of [true, false]) for (const failure of ['write', 'truncate', 'close']) {
  test(`${failure} failure after changing bytes rolls back ${existing ? 'an existing' : 'a new'} file and earlier writes`, async (f) => {
    f.message();
    const name = existing ? learnedPath() : `${ROOT}knowledge/facts.md`;
    const original = `# Learned rules — café ${'original '.repeat(40)}\r\n`;
    if (existing) f.write(name, original);
    const profileBefore = profile.replaceAll('\n', '\r\n');
    f.write(`${ROOT}profile.md`, profileBefore);
    const text = existing ? `# Learned rules — café\r\n${fact('[correction] Check dates. Why: owner correction.')}\r\n` : knowledge(fact('Likes café.'));
    const head = f.git('rev-parse', 'HEAD');
    const state = getState(f.stores.get('master'));
    const write = fs.writeFileSync; const truncate = fs.ftruncateSync; const close = fs.closeSync;
    let targetFd; let injected = false; let result;
    fs.writeFileSync = (file, body, ...args) => {
      if (typeof file === 'number' && body === text && !injected) {
        targetFd = file;
        if (failure === 'write') {
          const bytes = Buffer.from(body, 'utf8');
          write(file, bytes.subarray(0, bytes.indexOf(Buffer.from('é', 'utf8')) + 1));
          injected = true;
          throw new Error('fixture partial write');
        }
      }
      return write(file, body, ...args);
    };
    fs.ftruncateSync = (fd, length) => {
      if (fd === targetFd && failure === 'truncate' && !injected) {
        injected = true;
        throw new Error('fixture truncate failure');
      }
      return truncate(fd, length);
    };
    fs.closeSync = (fd) => {
      const value = close(fd);
      if (fd === targetFd && failure === 'close' && !injected) {
        injected = true;
        throw new Error('fixture close failure');
      }
      return value;
    };
    try {
      result = await f.run((input) => proposal(
        operation(input, `${ROOT}profile.md`, `${profileBefore}${fact('Owner fact.')}\r\n`),
        operation(input, name, text),
      ));
    } finally { fs.writeFileSync = write; fs.ftruncateSync = truncate; fs.closeSync = close; }
    assert.ok(injected);
    assert.equal(result.ok, false); assert.match(result.alert, /write failed/);
    assert.equal(result.changed, false); assert.equal(result.commit, null); assert.equal(result.digest, null);
    assert.deepEqual(fs.readFileSync(path.join(f.workspace, ROOT, 'profile.md')), Buffer.from(profileBefore, 'utf8'));
    if (existing) assert.deepEqual(fs.readFileSync(path.join(f.workspace, name)), Buffer.from(original, 'utf8'));
    else assert.equal(fs.existsSync(path.join(f.workspace, name)), false);
    assert.equal(f.git('rev-parse', 'HEAD'), head);
    assert.deepEqual(getState(f.stores.get('master')), state);
  });
}

test('rollback after a partial write preserves a concurrent edit to an earlier written file', async (f) => {
  f.message();
  const name = `${ROOT}knowledge/facts.md`; const text = knowledge(fact('Likes café.'));
  const concurrent = `${profile}${fact('Concurrent owner fact.')}\n`;
  const write = fs.writeFileSync; let injected = false; let result;
  fs.writeFileSync = (file, body, ...args) => {
    if (typeof file === 'number' && body === text && !injected) {
      injected = true;
      write(file, Buffer.from(body, 'utf8').subarray(0, 8));
      f.write(`${ROOT}profile.md`, concurrent);
      throw new Error('fixture partial write');
    }
    return write(file, body, ...args);
  };
  try {
    result = await f.run((input) => proposal(
      operation(input, `${ROOT}profile.md`, `${profile}${fact('Proposed owner fact.')}\n`),
      operation(input, name, text),
    ));
  } finally { fs.writeFileSync = write; }
  assert.ok(injected); assert.equal(result.ok, false); assert.match(result.alert, /write failed/);
  assert.equal(f.read(`${ROOT}profile.md`), concurrent);
  assert.equal(fs.existsSync(path.join(f.workspace, name)), false);
  assert.equal(getState(f.stores.get('master')).cursor, 0);
});

test('rejected commit restores new files and index entries while retaining unrelated staging', async (f) => {
  f.message();
  f.write('unrelated.md', 'unrelated staged work\n'); f.git('add', '--', 'unrelated.md');
  f.git('config', 'user.name', '');
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('New fact.')))));
  assert.equal(result.ok, false); assert.match(result.alert, /git commit failed/);
  assert.equal(fs.existsSync(path.join(f.workspace, ROOT, 'knowledge/facts.md')), false);
  assert.equal(f.git('diff', '--cached', '--name-only'), 'unrelated.md');
  assert.equal(getState(f.stores.get('master')).cursor, 0);
  f.git('config', 'user.name', 'Memory test');
  const retried = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('New fact.')))));
  assert.equal(retried.ok, true, retried.alert);
});

test('SQLite state is written only after Git confirms the commit', async (f) => {
  f.message(); const observed = [];
  const store = f.stores.get('master'); const prepare = store.db.prepare.bind(store.db);
  store.db.prepare = (sql) => {
    if (sql.startsWith('INSERT INTO settings(key,value')) observed.push(f.git('log', '-1', '--pretty=%s'));
    return prepare(sql);
  };
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('Committed fact.')))));
  assert.equal(result.ok, true, result.alert);
  assert.deepEqual(observed, ['Consolidate memory']);
});

test('duplicate inbox appends may be filed once with an explicit removal mapping', async (f) => {
  f.message(); const line = fact('Remember the same fact.');
  f.write(`${ROOT}inbox.md`, `# Inbox\n${line}\n${line}\n`);
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(line)),
    operation(input, `${ROOT}inbox.md`, '# Inbox\n', { reason: 'file', removals: [{ text: line, to: `${ROOT}knowledge/facts.md`, replacement: line }] })));
  assert.equal(result.ok, true, result.alert);
  assert.equal(f.read(`${ROOT}knowledge/facts.md`).split(line).length, 2);
});

test('inbox and watch-outs cannot bypass filing through archive operations', async (f) => {
  f.message(); const line = fact('Retain this.'); f.write(`${ROOT}inbox.md`, `# Inbox\n${line}\n`);
  const result = await f.run((input) => proposal(operation(input, `${ROOT}_artifacts/archive/notes.md`, topic(line)),
    operation(input, `${ROOT}inbox.md`, '# Inbox\n', { op: 'archive', removals: [{ text: line, to: `${ROOT}_artifacts/archive/notes.md` }] })));
  assert.equal(result.ok, false); assert.match(result.alert, /filed or folded/);
});

test('an unchanged run can return an owner conflict without advancing the cursor', async (f) => {
  f.message(); const result = await f.run(() => ({ operations: [], conflicts: ['Owner preference needs clarification.'] }));
  assert.equal(result.ok, true, result.alert); assert.equal(result.changed, false);
  assert.equal(result.digest.agent, 'master'); assert.match(result.digest.text, /needs clarification/);
  assert.equal(getState(f.stores.get('master')).cursor, 0);
});

test('reported conflicts persist across reopened stores and only new conflicts appear in later digests', async (f) => {
  f.message(); const old = 'Owner preference needs clarification.'; const fresh = 'Owner location needs clarification.';
  const first = await f.run(() => ({ operations: [], conflicts: [old, old] }));
  assert.equal(first.ok, true, first.alert); assert.deepEqual(first.digest.conflicts, [old]);
  const store = f.stores.get('master');
  assert.deepEqual(getState(store).reportedConflicts, []);
  // Simulate the daemon acknowledging a delivered digest.
  saveState(store, { ...getState(store), reportedConflicts: first.digest.conflicts }, NOW);
  f.stores.get('master').close();
  f.stores.set('master', new Store(path.join(f.workspace, own(), 'state.sqlite')));
  const second = await f.run((input) => {
    assert.deepEqual(input.reportedConflicts, [old]);
    return { operations: [], conflicts: [old] };
  }, { now: NOW + 1 });
  assert.equal(second.ok, true, second.alert); assert.equal(second.digest, null);
  const third = await f.run(() => ({ operations: [], conflicts: [old, fresh] }));
  assert.deepEqual(third.digest.conflicts, [fresh]); assert.ok(!third.digest.text.includes(old));
  const reopened = f.stores.get('master');
  assert.deepEqual(getState(reopened).reportedConflicts, [old]);
  saveState(reopened, { ...getState(reopened), reportedConflicts: [old, ...third.digest.conflicts] }, NOW);
  const changed = await f.run((input) => ({ operations: [operation(input, `${ROOT}knowledge/facts.md`, knowledge(fact('New fact.')))], conflicts: [old, fresh] }));
  assert.equal(changed.ok, true, changed.alert); assert.ok(changed.changed); assert.ok(changed.digest);
  assert.deepEqual(changed.digest.conflicts, []);
  assert.deepEqual(getState(f.stores.get('master')).reportedConflicts, [old, fresh]);
});

test('failed consolidation does not mark a conflict as reported', async (f) => {
  f.message(); const conflict = 'Owner preference needs clarification.';
  const result = await f.run((input) => ({ operations: [operation(input, `${ROOT}knowledge/facts.md`, 'invalid')], conflicts: [conflict] }));
  assert.equal(result.ok, false); assert.equal(result.digest, null);
  assert.deepEqual(getState(f.stores.get('master')).reportedConflicts || [], []);
  const retry = await f.run(() => ({ operations: [], conflicts: [conflict] }));
  assert.equal(retry.ok, true, retry.alert); assert.deepEqual(retry.digest.conflicts, [conflict]);
});

test('CRLF-equivalent proposals preserve bytes and remain a no-op', async (f) => {
  f.message(); const text = profile.replaceAll('\n', '\r\n'); f.write(`${ROOT}profile.md`, text);
  const result = await f.run((input) => proposal(operation(input, `${ROOT}profile.md`, profile)));
  assert.equal(result.ok, true, result.alert); assert.equal(result.changed, false); assert.equal(result.digest, null);
  assert.equal(f.read(`${ROOT}profile.md`), text);
});

test('a valid temporary board state stays active until explicitly archived', async (f) => {
  const text = board({ state: 'Office closed until 2026-10-02' }); f.write(boardPath(), text);
  const result = await f.run(() => proposal());
  assert.equal(result.ok, true, result.alert); assert.equal(f.read(boardPath()), text);
});

test('overfull inbox is accepted and all lines can be filed; workstreams alerts but never refuses', async (f) => {
  f.message(); const lines = Array.from({ length: 21 }, (_, i) => fact(`Fact ${i}.`));
  f.write(`${ROOT}inbox.md`, `# Inbox\n${lines.join('\n')}\n`);
  const map = '---\ndescription: when planning work\n---\n# Workstreams\n' + Array.from({ length: 61 }, (_, i) => `- [Project ${i}](../../projects/p${i}/) · board: none\n`).join('');
  const result = await f.run((input) => proposal(operation(input, `${ROOT}knowledge/facts.md`, knowledge(lines.join('\n'))),
    operation(input, `${ROOT}inbox.md`, '# Inbox\n', { reason: 'file', removals: lines.map((text) => ({ text, to: `${ROOT}knowledge/facts.md`, replacement: text })) }),
    operation(input, `${ROOT}workstreams.md`, map)));
  assert.equal(result.ok, true, result.alert); assert.match(result.digest.text, /60 lines/); assert.equal(f.read(`${ROOT}workstreams.md`), map);
});

test('daily and weekly timeline files link to periodic notes and source episodes', async (f) => {
  f.message();
  const daily = `---\ndescription: when asked what happened today\n---\n# ${DATE}\n\nPeriodic note: [Daily](../../../../periodic/${DATE}.md)\nWeek: [2026-W40](../weekly/2026-W40.md)\n\n- Owner confirmed the trip. — master/[thread](${link()})\n`;
  const weekly = `---\ndescription: when asked about the week\n---\n# 2026-W40\n\nPeriodic note: [Weekly](../../../../periodic/2026-W40.md)\n\n- Trip confirmed. — [${DATE}](../daily/${DATE}.md)\n`;
  const result = await f.run((input) => proposal(operation(input, `${ROOT}timeline/daily/${DATE}.md`, daily), operation(input, `${ROOT}timeline/weekly/2026-W40.md`, weekly)));
  assert.equal(result.ok, true, result.alert); assert.equal(f.read(`${ROOT}timeline/daily/${DATE}.md`), daily);
});

test('generated indexes are exempt from the ordinary index row cap', async (f) => {
  const text = '# Topics\n\n| Open | When |\n|---|---|\n' + Array.from({ length: 45 }, (_, i) => `| [Topic ${i}](../topic-${i}.md) | when reviewing topic ${i} |\n`).join('');
  const result = await f.run((input) => proposal(operation(input, `${own()}memory/_artifacts/index.md`, text, { reason: 'index', sources: [] })));
  assert.equal(result.ok, true, result.alert); assert.equal(f.read(`${own()}memory/_artifacts/index.md`), text);
});

test('a subject topic without mirrored thread metadata is refused', async (f) => {
  f.message();
  const text = topic(fact('Some state.'), 'subject').replace(`Threads: [thread](${link()})\n\n`, '');
  const result = await f.run((input) => proposal(operation(input, `${own()}memory/report.md`, text)));
  assert.equal(result.ok, false); assert.match(result.alert, /require Threads/);
});

test('cast adapter defaults to codex gpt-6-sol effort 3 in a disposable folder and parses JSON', async (f) => {
  let temp;
  const result = await castProposal({ agent: 'master', messages: [], files: {} }, { command: 'cast-test.js', run: async (command, args, opts) => {
    assert.equal(command, process.execPath); assert.deepEqual(args.slice(0, 4), [path.resolve('cast-test.js'), 'codex', 'gpt-6-sol', '3']);
    temp = args[4]; assert.equal(opts.cwd, temp); assert.equal(args[5], '-f'); assert.equal(opts.encoding, 'utf8');
    const prompt = fs.readFileSync(args[6], 'utf8'); assert.match(prompt, /Only owner messages and explicit remember lines in inbox.md are evidence/); assert.match(prompt, /never use tools or edit files/);
    assert.match(prompt, /cite its exact line in sources on both filing operations/);
    assert.match(prompt, /keep its date and attach this agent's Slack thread links backed by this operation's owner sources/);
    assert.match(prompt, /leave it unchanged and report a conflict/);
    assert.ok(!temp.startsWith(f.workspace)); return { stdout: '```json\n{"operations":[],"conflicts":[]}\n```' };
  } });
  assert.deepEqual(result, proposal()); assert.equal(fs.existsSync(temp), false);
});

test('cast adapter cleans its temporary prompt after failure', async () => {
  let temp;
  await assert.rejects(castProposal({}, { run: async (_command, _args, opts) => { temp = opts.cwd; throw new Error('provider failure'); } }));
  assert.equal(fs.existsSync(temp), false);
});

test('cast adapter accepts the OpenCode banner and recovered final JSON, but refuses trailing trace text', async () => {
  for (const stdout of ['OpenCode model banner\n\n{"operations":[],"conflicts":[]}',
    'OpenCode model banner\n\n```json\n{"operations":[],"conflicts":[]}\n```',
    'OpenCode model banner\ncast: recovered final message from the opencode session store (absent from stdout):\n{"operations":[],"conflicts":[]}']) {
    assert.deepEqual(await castProposal({}, { run: async () => ({ stdout }) }), proposal());
  }
  await assert.rejects(castProposal({}, { run: async () => ({ stdout: '{"operations":[],"conflicts":[]}\nnot a final report' }) }), /model did not return JSON/);
});

test('Windows cast shim resolves to Node without shell parsing or losing path arguments', async (f) => {
  const entry = path.join(f.workspace, 'cast entry.js'); f.write('cast entry.js', '// fixture\n');
  f.write('cast.cmd', `@rem rbtv-shim -> ${entry}\r\n@"node" "${entry}" %*\r\n`);
  let launched = false;
  const result = await castProposal({}, { command: 'cast', platform: 'win32', env: { PATH: f.workspace }, run: async (command, args, opts) => {
    launched = true; assert.equal(command, process.execPath); assert.equal(args[0], entry);
    assert.deepEqual(args.slice(1, 4), ['codex', 'gpt-6-sol', '3']); assert.equal(opts.shell, undefined);
    return { stdout: JSON.stringify(proposal()) };
  } });
  assert.ok(launched); assert.deepEqual(result, proposal());
});

test('runner can open and close its own SQLite stores', async (f) => {
  f.message(); const result = await runDreamer({ config: f.config, model: () => proposal(), now: NOW });
  assert.equal(result.ok, true, result.alert); assert.equal(getState(f.stores.get('master')).lastSuccessAt, NOW);
});

for (const model of [undefined, { harness: 'opencode', model: 'example/model-v1', effort: 2 }]) test(`runner executes configured cast and model (${model ? 'override' : 'default'}) through the real adapter`, async (f) => {
  f.message(); const name = `${ROOT}knowledge/facts.md`;
  const output = proposal({ op: 'add', path: name, text: knowledge(fact('Confirmed by owner.')),
    sources: [1], reason: 'owner', explanation: 'Owner confirmed this fact.' });
  const args = model ? [model.harness, model.model, String(model.effort)] : ['codex', 'gpt-6-sol', '3'];
  f.write('fake cast.js', `const assert = require('node:assert/strict');\nassert.deepEqual(process.argv.slice(2,5), ${JSON.stringify(args)});\nprocess.stdout.write(${JSON.stringify(JSON.stringify(output))});\n`);
  f.config.tools.cast = path.join(f.workspace, 'fake cast.js');
  f.config.dreamer = { model };
  const result = await f.run(undefined);
  assert.equal(result.ok, true, result.alert); assert.equal(f.read(name), output.operations[0].text);
  assert.equal(f.git('show', '--pretty=format:', '--name-only', 'HEAD'), name);
});

test('failed cast reports only a category and keeps cursor, success and memory unchanged', async (f) => {
  f.message(); const before = getState(f.stores.get('master')); const head = f.git('rev-parse', 'HEAD');
  const stderr = 'old diagnostic\r\n'.repeat(20) + '\x1b[31mInsufficient credits — café\x1b[0m\r\n' + 'details '.repeat(60);
  f.write('failed cast.js', `process.stderr.write(${JSON.stringify(stderr)}); process.exitCode = 1;\n`);
  f.config.tools.cast = path.join(f.workspace, 'failed cast.js');
  const result = await f.run();
  assert.equal(result.ok, false);
  assert.equal(result.alert, 'Dreamer failed: model out of credits or spending limit.');
  assert.doesNotMatch(result.alert, /\x1b|\r|\n/);
  assert.equal(result.digest, null); assert.equal(result.changed, false);
  assert.deepEqual(getState(f.stores.get('master')), before);
  assert.equal(f.git('rev-parse', 'HEAD'), head); assert.equal(f.git('diff', '--name-only'), '');
});

test('cast failure maps stderr to one fixed category without copying any credential shape', async (f) => {
  const credentials = 'api_key synthetic-space-value; api_key=synthetic-equals-value; ' +
    '"api_key": "synthetic-json-value"; Bearer synthetic-bearer-value; Basic synthetic-basic-value; ' +
    'sk-synthetic-provider-value; xoxb-synthetic-slack-value; unlabelled-synthetic-value';
  for (const [diagnostics, cause] of [
    [['spending-limit', 'CREDITS', 'Insufficient balance', 'quota', 'quota 429 unauthorized'], 'model out of credits or spending limit'],
    [['Rate limit', '429', '429 timed out 401'], 'model rate limited'],
    [['Timed out', 'timeout', 'timed out unauthorized'], 'model timed out'],
    [['401', '403', 'Unauthorized', 'Unauthorised', 'Invalid API key'], 'model authentication failed'],
    [['Access denied', 'unrecognized failure'], 'model failed (exit 7)'],
  ]) {
    for (const diagnostic of diagnostics) {
      const stderr = `\x1b[31m${diagnostic} — café\x1b[0m\r\n${credentials}\r\n`;
      const result = await f.run(() => { throw Object.assign(new Error(`unsafe command ${credentials}`), { stderr, code: 7 }); });
      assert.equal(result.ok, false);
      assert.equal(result.alert, `Dreamer failed: ${cause}.`);
      assert.equal(JSON.stringify(result).includes('synthetic'), false);
    }
  }
});

test('cast failure without stderr reports a safe exit or timeout cause', async (f) => {
  for (const [error, cause] of [
    [{ code: 'ENOENT' }, 'model failed (exit ENOENT)'], [{ code: 7 }, 'model failed (exit 7)'],
    [{ killed: true, signal: 'SIGTERM' }, 'model timed out'],
    [{ code: 'ETIMEDOUT' }, 'model timed out'],
    [{}, 'model failed (exit unknown)'], [{ code: 'unsafe command' }, 'model failed (exit unknown)'],
  ]) {
    const result = await f.run(() => { throw Object.assign(new Error('unsafe command'), error); });
    assert.equal(result.alert, `Dreamer failed: ${cause}.`);
  }
});

(async () => {
  let passed = 0; let skipped = 0; const failures = [];
  for (const [name, fn, slugs] of tests) {
    const f = fixture(slugs); let skip = false;
    try {
      await fn(f, { skip(reason) { skip = true; skipped++; process.stdout.write(`SKIP ${name}: ${reason}\n`); } });
      if (!skip) { passed++; process.stdout.write(`PASS ${name}\n`); }
    } catch (error) { failures.push(name); process.stderr.write(`FAIL ${name}\n${error.stack}\n`); }
    finally { f.cleanup(); }
  }
  process.stdout.write(`\n${passed} passed, ${failures.length} failed, ${skipped} skipped\n`);
  if (failures.length) process.exitCode = 1;
})();
