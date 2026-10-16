'use strict';

const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const MIGRATE = path.join(__dirname, 'migrate.js');
const ALBERT_LIB = path.join(__dirname, '..', '..', '..', 'agents', 'albert', 'rbtv', 'capabilities', 'tools', 'albert', 'lib');
const store = require(path.join(ALBERT_LIB, 'store.js'));
const report = require(path.join(ALBERT_LIB, 'report.js'));

const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const failed = [];
const ok = (result) => assert.equal(result.status, 0, String(result));

function test(name, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'migrate-'));
  try { fn(world(dir)); process.stdout.write(`PASS ${name}\n`); }
  catch (error) { failed.push(name); process.stderr.write(`FAIL ${name}\n${error.stack}\n`); }
  finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

const FACTS = '---\ndescription: when reviewing preferences\ntype: preferences\naliases: [preferences]\n---\n# Preferences\n\n- tea over coffee (2026-09-01 · owner)\n';
const LEARNED = '# Learned rules — gaming\n';
const THREAD = 'https://chat.example/archives/C1/p100';
const DAILY_HEADER = '---\ndescription: when reviewing 2026-10-13\n---\n# 2026-10-13\n';

function write(file, text) { fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, text, 'utf8'); }
function git(cwd, args) { return spawnSync('git', ['-c', 'user.email=t@example.com', '-c', 'user.name=t', ...args], { cwd, encoding: 'utf8' }); }

function snapshot(dir) {
  const out = {};
  const walk = (current) => {
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const file = path.join(current, entry.name);
      if (entry.name === '.git') continue;
      if (entry.isDirectory()) walk(file); else out[path.relative(dir, file)] = sha(fs.readFileSync(file));
    }
  };
  walk(dir);
  return out;
}

function world(dir) {
  const inst = path.join(dir, 'inst');
  const harness = path.join(dir, 'harness');
  const albert = path.join(inst, '.rbtv', 'agents', 'albert');
  write(path.join(inst, '.rbtv/memory/knowledge/preferences.md'), FACTS);
  write(path.join(inst, '.rbtv/agents/gaming/memory/learned.md'), LEARNED);
  write(path.join(albert, 'runtime/albert/cursors.json'), '{"conversation:gaming:messages":"42"}\n');
  write(path.join(albert, 'runtime/albert/evidence/batch-1.json'), '{"sourceAgent":"gaming","rows":[]}\n');
  git(inst, ['init', '-q']);
  git(inst, ['config', 'user.email', 't@example.com']);
  git(inst, ['config', 'user.name', 't']);
  git(inst, ['add', '.']);
  git(inst, ['commit', '-qm', 'init']);
  const source = (name, text) => { write(path.join(harness, name), text); return path.join(harness, name); };
  const fixture = {
    dir, inst, harness, albert,
    mixed: source('feedback_mixed.md', '---\nname: mixed\n---\nOwner likes oat milk.\nPlease book the dentist for Friday.\n'),
    lesson: source('feedback_lesson.md', 'Always confirm before deleting.\n'),
    global: source('feedback_global.md', 'Never auto-merge.\n'),
    other: source('reference_x.md', 'unmapped note\n'),
    manifest: path.join(dir, 'manifest.json'),
    destHash: (rel) => { try { return sha(fs.readFileSync(path.join(inst, rel))); } catch { return null; } },
  };
  const keep = { futureAnswerEffect: true, usefulAfterThirtyDays: true, owner: 'owner' };
  const oneOff = { futureAnswerEffect: false, usefulAfterThirtyDays: false, owner: 'task' };
  fixture.keep = keep;
  fixture.oneOff = oneOff;
  fixture.rows = () => [
    {
      id: 'r-mixed', source: fixture.mixed, origin: { harness: 'claude-code', agent: 'gaming' }, hash: sha(fs.readFileSync(fixture.mixed)),
      mtime: fs.statSync(fixture.mixed).mtimeMs, disposition: 'migrated', original: 'keep',
      records: [
        { span: [4, 4], kind: 'fact', scope: 'workspace', verdict: keep, destination: '.rbtv/memory/knowledge/preferences.md', text: '- oat milk (2026-10-13 · owner · migrated feedback_mixed.md)' },
        { span: [5, 5], kind: 'operational request', scope: 'personal', verdict: oneOff, destination: '.rbtv/memory/timeline/daily/2026-10-13.md', header: DAILY_HEADER, text: `- book the dentist for Friday — gaming/[request](${THREAD})` },
      ],
    },
    {
      id: 'r-lesson', source: fixture.lesson, origin: { harness: 'claude-code', agent: 'gaming' }, hash: sha(fs.readFileSync(fixture.lesson)),
      mtime: 1, disposition: 'migrated', original: 'keep',
      records: [{ span: [1, 1], kind: 'agent lesson', scope: 'personal', verdict: keep, destination: '.rbtv/agents/gaming/memory/learned.md', text: `- [correction] Confirm before deleting. Why: lost a file (2026-10-13 · gaming/[thread](${THREAD}))` }],
    },
    {
      id: 'r-global', source: fixture.global, origin: { harness: 'claude-code', agent: 'gaming' }, hash: sha(fs.readFileSync(fixture.global)),
      mtime: 1, disposition: 'pending-global-approval', original: 'keep',
      records: [{ span: [1, 1], kind: 'agent lesson', scope: 'global', verdict: keep, text: 'Never auto-merge.' }],
    },
  ];
  fixture.cutover = () => ({ destinations: Object.fromEntries(['.rbtv/memory/knowledge/preferences.md', '.rbtv/agents/gaming/memory/learned.md', '.rbtv/memory/timeline/daily/2026-10-13.md', '.rbtv/memory/learned.md'].map((rel) => [rel, fixture.destHash(rel)])) });
  fixture.save = (rows = fixture.rows(), extra = {}) => write(fixture.manifest, JSON.stringify({ version: 1, cutover: fixture.cutover(), rows, ...extra }));
  fixture.run = (verb, ...more) => {
    const result = spawnSync(process.execPath, [MIGRATE, verb, '--installation', inst, '--manifest', fixture.manifest, ...more], { encoding: 'utf8', env: { ...process.env, HOME: dir, RBTV_AGENT_HOME: '' } });
    result.toString = () => `exit ${result.status}\n${result.stderr}\n${result.stdout}`;
    return result;
  };
  fixture.ledger = () => JSON.parse(fs.readFileSync(path.join(inst, '.rbtv/runtime/migration/ledger.json'), 'utf8'));
  fixture.read = (rel) => fs.readFileSync(path.join(inst, rel), 'utf8');
  fixture.commits = () => git(inst, ['rev-list', '--count', 'HEAD']).stdout.trim();
  fixture.receipts = () => store.readReceipts(albert);
  return fixture;
}

test('dry-run writes nothing', (w) => {
  w.save();
  const before = snapshot(w.dir);
  const result = w.run('dry-run');
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(snapshot(w.dir), before);
  assert.equal(w.commits(), '1');
  assert.equal(JSON.parse(result.stdout).rows.length, 3);
});

test('apply keeps verbatim originals and origins', (w) => {
  w.save();
  const result = w.run('apply');
  assert.equal(result.status, 0, result.stderr);
  for (const entry of w.ledger().entries.filter((e) => e.original)) {
    assert.deepEqual(fs.readFileSync(entry.original), fs.readFileSync(entry.source));
  }
  assert.equal(w.ledger().entries[0].source, w.mixed);
});

test('one source with a durable fact and a one-off request splits per record', (w) => {
  w.save();
  ok(w.run('apply'));
  assert.match(w.read('.rbtv/memory/knowledge/preferences.md'), /oat milk/);
  assert.doesNotMatch(w.read('.rbtv/memory/knowledge/preferences.md'), /dentist/);
  assert.match(w.read('.rbtv/memory/timeline/daily/2026-10-13.md'), /dentist/);
  assert.doesNotMatch(w.read('.rbtv/memory/timeline/daily/2026-10-13.md'), /oat milk/);
});

test('manifest per-record keeping verdicts decide the route', (w) => {
  const rows = w.rows();
  rows[0].records[0].verdict = w.oneOff;
  w.save(rows);
  const toDurable = w.run('apply');
  assert.equal(toDurable.status, 1);
  assert.match(toDurable.stderr, /failing the keeping test goes to the timeline only/);
  const second = w.rows();
  second[0].records[1].verdict = w.keep;
  w.save(second);
  const toTimeline = w.run('apply');
  assert.equal(toTimeline.status, 1);
  assert.match(toTimeline.stderr, /passing the keeping test cannot go to the timeline/);
  assert.match(toTimeline.stderr, /only a fact or an agent lesson is kept/);
});

test('personal, workspace and global scope assignment', (w) => {
  const wrong = w.rows();
  wrong[1].records[0].destination = '.rbtv/agents/sara/memory/learned.md';
  wrong[2].records[0].destination = '.rbtv/memory/learned.md';
  wrong[0].records[0].scope = 'personal';
  wrong[0].records[0].destination = '.rbtv/agents/sara/memory/notes.md';
  w.save(wrong);
  const refused = w.run('apply');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /not a memory file this agent or workspace owns/);
  assert.match(refused.stderr, /global rule is never written by migration/);
  w.save();
  ok(w.run('apply'));
  assert.match(w.read('.rbtv/agents/gaming/memory/learned.md'), /Confirm before deleting/);
  assert.match(w.read('.rbtv/memory/knowledge/preferences.md'), /oat milk/);
  assert.equal(w.destHash('.rbtv/memory/learned.md'), null);
});

test('fact versus agent lesson versus task', (w) => {
  const rows = w.rows();
  rows[0].records[0].destination = '.rbtv/agents/gaming/memory/learned.md';
  rows[0].records[0].scope = 'personal';
  rows[1].records[0].kind = 'task';
  rows[1].records[0].destination = '.rbtv/memory/knowledge/preferences.md';
  rows[1].records[0].scope = 'workspace';
  w.save(rows);
  const refused = w.run('dry-run');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /a fact is not a learned rule/);
  assert.match(refused.stderr, /only a fact or an agent lesson is kept as memory/);
  w.save();
  ok(w.run('apply'));
});

test('unchanged source not imported twice and its retry emits no second receipt', (w) => {
  w.save();
  ok(w.run('apply'));
  const commits = w.commits();
  const receipts = w.receipts().map((r) => r.id);
  const facts = w.read('.rbtv/memory/knowledge/preferences.md');
  const retry = w.run('apply');
  assert.equal(retry.status, 0, retry.stderr);
  assert.equal(w.commits(), commits);
  assert.deepEqual(w.receipts().map((r) => r.id), receipts);
  assert.equal(w.read('.rbtv/memory/knowledge/preferences.md'), facts);
  assert.ok(JSON.parse(retry.stdout).rows.every((row) => row.state === 'already-imported'));
  assert.match(receipts[0], /^migrated-[0-9a-f]{16}$/);
});

test('changed source reconsidered and linked to its earlier row', (w) => {
  w.save();
  ok(w.run('apply'));
  fs.appendFileSync(w.lesson, 'Also confirm before archiving.\n');
  const rows = w.rows().slice(1, 2);
  rows[0].id = 'r-lesson-2';
  rows[0].records = [{ span: [2, 2], kind: 'agent lesson', scope: 'personal', verdict: w.keep, destination: '.rbtv/agents/gaming/memory/learned.md', text: `- [correction] Confirm before archiving. Why: lost a folder (2026-10-13 · gaming/[thread](${THREAD}))` }];
  w.save(rows);
  const unlinked = w.run('apply');
  assert.equal(unlinked.status, 1);
  assert.match(unlinked.stderr, /changed source needs a row linked to its earlier row/);
  rows[0].earlier = 'r-lesson';
  w.save(rows);
  ok(w.run('apply'));
  const entry = w.ledger().entries.find((e) => e.rowId === 'r-lesson-2');
  assert.equal(entry.earlier, 'r-lesson');
  assert.match(w.read('.rbtv/agents/gaming/memory/learned.md'), /archiving/);
  assert.match(w.read('.rbtv/agents/gaming/memory/learned.md'), /deleting/);
});

test('stale source refused', (w) => {
  w.save();
  fs.appendFileSync(w.mixed, 'edited after inspection\n');
  const before = snapshot(w.inst);
  const refused = w.run('apply');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /stale source: hash differs from the manifest/);
  assert.deepEqual(snapshot(w.inst), before);
});

test('every failure is printed with its requirement and expectation', (w) => {
  const rows = w.rows();
  rows[0].original = 'drop';
  rows[1].records[0].span = [9, 9];
  w.save(rows);
  const refused = w.run('apply', '--json');
  assert.equal(refused.status, 1);
  const failures = JSON.parse(refused.stdout);
  assert.ok(failures.length >= 2 && failures.every((f) => ['path', 'operation', 'requirement', 'expected', 'reason'].every((k) => k in f)));
  assert.match(refused.stderr, /expected: original: "keep"/);
});

test('pending global approval stays pending', (w) => {
  w.save();
  ok(w.run('apply'));
  assert.equal(w.destHash('.rbtv/memory/learned.md'), null);
  const approvals = JSON.parse(fs.readFileSync(path.join(w.albert, 'runtime/albert/conflicts.json'), 'utf8')).items;
  assert.equal(approvals.length, 1);
  assert.equal(approvals[0].kind, 'approval');
  assert.equal(approvals[0].text, 'Pending global rule: Never auto-merge.');
});

test('source-agent cursor identity and pending evidence preserved', (w) => {
  const cursors = path.join(w.albert, 'runtime/albert/cursors.json');
  const evidence = path.join(w.albert, 'runtime/albert/evidence/batch-1.json');
  const before = [fs.readFileSync(cursors), fs.readFileSync(evidence)];
  w.save();
  ok(w.run('apply'));
  assert.deepEqual([fs.readFileSync(cursors), fs.readFileSync(evidence)], before);
  ok(w.run('rollback'));
  assert.deepEqual([fs.readFileSync(cursors), fs.readFileSync(evidence)], before);
});

test('fixture harness files byte-identical after apply and rollback (no loader disabled)', (w) => {
  const before = snapshot(w.harness);
  w.save();
  ok(w.run('apply'));
  ok(w.run('rollback'));
  assert.deepEqual(snapshot(w.harness), before);
});

test('unmapped source reported', (w) => {
  w.save(w.rows(), { inventory: [w.mixed, w.other] });
  const result = JSON.parse(w.run('dry-run').stdout);
  assert.deepEqual(result.unmapped, [w.other]);
  assert.equal(result.complete, false);
});

test('off-machine source marked pending and never complete', (w) => {
  const rows = [{ id: 'r-win', source: 'windows:%USERPROFILE%\\.claude\\memory\\x.md', origin: { harness: 'claude-code', workspace: 'vault' }, hash: null, mtime: null, disposition: 'off-machine-pending', original: 'keep' }];
  w.save(rows);
  const applied = w.run('apply');
  assert.equal(applied.status, 0, applied.stderr);
  const result = JSON.parse(applied.stdout);
  assert.deepEqual(result.offMachinePending, [rows[0].source]);
  assert.equal(result.complete, false);
  assert.equal(w.ledger().entries[0].disposition, 'off-machine-pending');
  assert.equal(JSON.parse(w.run('apply').stdout).complete, false);
});

test('stable migration receipt carries before, after and sources, and the first Albert report includes it', (w) => {
  w.save();
  ok(w.run('apply'));
  const receipt = w.receipts().find((r) => r.runId.startsWith('migrated-') && r.items.some((i) => i.path.endsWith('preferences.md')));
  assert.equal(receipt.outcome, 'migrated');
  const item = receipt.items.find((i) => i.path.endsWith('preferences.md'));
  assert.equal(item.before, FACTS);
  assert.match(item.after, /oat milk/);
  assert.ok(item.sources[0].startsWith(`${w.mixed}#L4-4`));
  assert.equal(item.ref, `${receipt.id}#1`);
  const first = report.report(w.albert, 'week-1');
  assert.ok(first.items.includes(item.ref));
  assert.match(first.text, /oat milk/);
  assert.match(first.text, /Pending global rule: Never auto-merge\./);
  assert.ok(w.ledger().entries.every((e) => e.reporting === 'owed'));
});

test('rollback restores written destinations only', (w) => {
  w.save();
  ok(w.run('apply'));
  write(path.join(w.inst, '.rbtv/memory/knowledge/facts.md'), '---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# Facts\n\n- bystander (2026-09-01 · owner)\n');
  const bystander = w.read('.rbtv/memory/knowledge/facts.md');
  const rolled = w.run('rollback');
  assert.equal(rolled.status, 0, rolled.stderr);
  assert.equal(w.read('.rbtv/memory/knowledge/preferences.md'), FACTS);
  assert.equal(w.read('.rbtv/agents/gaming/memory/learned.md'), LEARNED);
  assert.equal(fs.existsSync(path.join(w.inst, '.rbtv/memory/timeline/daily/2026-10-13.md')), false);
  assert.equal(w.read('.rbtv/memory/knowledge/facts.md'), bystander);
  const stopped = w.run('apply');
  assert.equal(stopped.status, 1);
  assert.match(stopped.stderr, /stopped by a rollback/);
});

test('checked reversal preserves a later unrelated destination edit', (w) => {
  w.save();
  ok(w.run('apply'));
  fs.appendFileSync(path.join(w.inst, '.rbtv/memory/knowledge/preferences.md'), '- jazz at night (2026-10-14 · owner)\n');
  const rolled = w.run('rollback');
  assert.equal(rolled.status, 0, rolled.stderr);
  const text = w.read('.rbtv/memory/knowledge/preferences.md');
  assert.match(text, /jazz at night/);
  assert.doesNotMatch(text, /oat milk/);
  assert.ok(w.receipts().some((r) => r.runId.startsWith('migration-rollback-')));
});

test('rollback preserves a post-cutover edit and reports the conflict', (w) => {
  w.save();
  ok(w.run('apply'));
  const file = path.join(w.inst, '.rbtv/agents/gaming/memory/learned.md');
  const edited = fs.readFileSync(file, 'utf8').replace('Confirm before deleting', 'Confirm twice before deleting');
  fs.writeFileSync(file, edited);
  const rolled = w.run('rollback');
  assert.equal(rolled.status, 1);
  const result = JSON.parse(rolled.stdout);
  assert.equal(result.conflicts[0].path, '.rbtv/agents/gaming/memory/learned.md');
  assert.equal(fs.readFileSync(file, 'utf8'), edited);
  assert.equal(w.read('.rbtv/memory/knowledge/preferences.md'), FACTS);
});

test('apply refuses to overwrite a post-cutover change', (w) => {
  w.save();
  fs.appendFileSync(path.join(w.inst, '.rbtv/memory/knowledge/preferences.md'), '- changed since cutover (2026-10-12 · owner)\n');
  const before = snapshot(w.inst);
  const refused = w.run('apply');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /destination changed after cutover/);
  assert.deepEqual(snapshot(w.inst), before);
});

test('memory migrate dry-run gives the same result as node migrate.js dry-run', (w) => {
  w.save();
  const direct = w.run('dry-run');
  const viaMemory = spawnSync(process.execPath, [path.join(__dirname, 'memory.js'), 'migrate', 'dry-run', '--installation', w.inst, '--manifest', w.manifest], { encoding: 'utf8', env: { ...process.env, HOME: w.dir, RBTV_AGENT_HOME: '' } });
  assert.equal(direct.status, 0, direct.toString());
  assert.equal(viaMemory.status, direct.status);
  assert.equal(viaMemory.stdout, direct.stdout);
  assert.equal(spawnSync(process.execPath, [path.join(__dirname, 'memory.js'), 'migrate', '-h'], { encoding: 'utf8' }).stdout.includes('Manifest:'), true);
});

test('a workspace document imports without a harness; an agent note still needs one', (w) => {
  const doc = path.join(w.dir, 'docs', 'session.md');
  write(doc, '# Session\nOwner said he prefers green tea.\n');
  const row = (origin) => ({
    id: 'r-doc', source: doc, origin, hash: sha(fs.readFileSync(doc)), mtime: 1, disposition: 'migrated', original: 'keep',
    records: [{ span: [2, 2], kind: 'fact', scope: 'workspace', verdict: w.keep, destination: '.rbtv/memory/knowledge/preferences.md', text: '- green tea (2026-09-15 · docs/session.md)' }],
  });
  w.save([row({ workspace: 'vault' })]);
  ok(w.run('apply'));
  assert.match(w.read('.rbtv/memory/knowledge/preferences.md'), /green tea/);
  w.save([{ ...row({ agent: 'gaming' }), id: 'r-note' }]);
  const refused = w.run('dry-run');
  assert.equal(refused.status, 1);
  assert.match(refused.stderr, /origin missing/);
});

if (failed.length) { process.stderr.write(`${failed.length} failed\n`); process.exit(1); }
