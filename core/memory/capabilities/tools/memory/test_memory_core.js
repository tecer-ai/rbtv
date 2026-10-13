'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const lib = require('./lib/index.js');

const passed = [];
const failed = [];

function test(name, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'memory-core-'));
  const prev = { HOME: process.env.HOME, RBTV_AGENT_HOME: process.env.RBTV_AGENT_HOME };
  process.env.HOME = dir;
  process.env.RBTV_AGENT_HOME = path.join(dir, 'agent');
  try {
    fn(dir);
    passed.push(name);
    process.stdout.write(`PASS ${name}\n`);
  } catch (error) {
    failed.push(name);
    process.stderr.write(`FAIL ${name}\n${error.stack}\n`);
  } finally {
    process.env.HOME = prev.HOME;
    if (prev.RBTV_AGENT_HOME == null) delete process.env.RBTV_AGENT_HOME;
    else process.env.RBTV_AGENT_HOME = prev.RBTV_AGENT_HOME;
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

function board(watchOuts = [], extra = '') {
  return `## What matters now\n\n### Review\nReady.\n- Threads: none\n- Detail: none\n- Flags: none\n${extra}## Watch-outs\n\n${watchOuts.join('\n')}\n\n## Timers\n\n## Recently closed\n\n`;
}

function install(dir, home) {
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory', '_artifacts'), { recursive: true });
  fs.mkdirSync(path.join(home, 'memory'), { recursive: true });
  fs.mkdirSync(path.join(home, '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'profile.md'), '# Profile — Sam\n\n## Who\n\n- One (2026-10-01 · note)\n\n## Working with Sam\n\n- Two (2026-10-01 · note)\n\n## Now\n\n- Three (2026-10-01 · note)\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), '# Inbox\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', '_artifacts', 'index.md'), '# Memory\n\n| Open | When |\n|---|---|\n| [facts](../knowledge/facts.md) | when reviewing facts |\n', 'utf8');
  fs.writeFileSync(path.join(home, 'memory', 'learned.md'), '# Learned rules — sample\n', 'utf8');
  fs.writeFileSync(lib.boardPath(home), lib.EMPTY_BOARD, 'utf8');
  spawnSync('git', ['init', '-q'], { cwd: dir });
  spawnSync('git', ['add', '.'], { cwd: dir });
  spawnSync('git', ['-c', 'user.email=t@example.com', '-c', 'user.name=t', 'commit', '-qm', 'init'], { cwd: dir });
}

test('seventh watch-out is captured', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const file = lib.boardPath(home);
  const watches = Array.from({ length: 7 }, (_, i) => `- Correction ${i} (2026-10-01 · sample)`);
  const revision = lib.readBoard(file).revision;
  const result = lib.writeBoard(file, board(watches), { revision });
  assert.equal(result.changed, true);
  assert.equal(lib.parseBoard(fs.readFileSync(file, 'utf8')).watchOuts.length, 7);
});

test('oversized correction is captured and omitted from the view with the mandatory-read notice', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const file = lib.boardPath(home);
  const huge = `- ${'é'.repeat(lib.VIEW_LIMIT)} (2026-10-01 · sample)`;
  const kept = '- Keep this correction (2026-10-02 · sample)';
  const text = board([huge, kept]);
  lib.writeBoard(file, text, { revision: lib.readBoard(file).revision });
  const stored = fs.readFileSync(file, 'utf8');
  assert.ok(stored.includes('é'.repeat(lib.VIEW_LIMIT)));
  const view = lib.renderBoardView(stored, file);
  assert.equal(view.includes('é'.repeat(80)), false);
  assert.match(view, /Omitted watch-outs \(1\): read .+ before acting\. Mandatory\./);
  assert.match(view, /Command: memory board read --file .+ --section Watch-outs/);
});

test('view is at most 6000 code points counted with Array.from(text).length on text containing astral characters', () => {
  const astral = `- ${'😀'.repeat(20)} (2026-10-01 · sample)`;
  const text = board([astral, `- ${'é'.repeat(lib.VIEW_LIMIT)} (2026-10-01 · sample)`]);
  const view = lib.renderBoardView(text, 'board.md');
  assert.ok(Array.from(view).length <= 6000, Array.from(view).length);
  assert.ok(view.includes('😀'));
});

test('selection order (watch-outs, subjects, timers, closures)', () => {
  const watches = ['- Newest (2026-10-03 · sample)', '- Older (2026-10-01 · sample)'];
  const timers = ['| Fires | Timer | For | Subject |', '|---|---|---|---|', '| 2026-10-04 09:00 UTC | later | Note | none |', '| 2026-10-02 09:00 UTC | sooner | Note | none |'];
  const closed = ['- Old — done (2026-10-01 · sample)', '- New — done (2026-10-03 · sample)'];
  const text = `## What matters now\n\n### First subject\nState.\n- Threads: none\n- Detail: none\n- Flags: none\n### Second subject\nState.\n- Threads: none\n- Detail: none\n- Flags: none\n## Watch-outs\n\n${watches.join('\n')}\n\n## Timers\n\n${timers.join('\n')}\n\n## Recently closed\n\n${closed.join('\n')}\n`;
  const view = lib.renderBoardView(text, 'board.md');
  assert.ok(view.indexOf('Newest') < view.indexOf('Older'));
  assert.ok(view.indexOf('First subject') < view.indexOf('Second subject'));
  assert.ok(view.indexOf('sooner') < view.indexOf('later'));
  assert.ok(view.indexOf('New — done') < view.indexOf('Old — done'));
});

test('a view-form text is refused by the checked write and by parseBoard', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const file = lib.boardPath(home);
  const view = lib.renderBoardView(fs.readFileSync(file, 'utf8'), file);
  assert.throws(() => lib.parseBoard(view), /start|headings|Board view|refused/);
  const before = fs.readFileSync(file);
  assert.throws(() => lib.writeBoard(file, view, { revision: lib.readBoard(file).revision }), /refused|start|headings/);
  assert.deepEqual(fs.readFileSync(file), before);
});

test('stale revision is rejected and a fresh one accepted', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const file = lib.boardPath(home);
  const stale = lib.readBoard(file).revision;
  const next = board(['- One (2026-10-01 · sample)']);
  lib.writeBoard(file, next, { revision: stale });
  const fresh = lib.readBoard(file).revision;
  assert.throws(() => lib.writeBoard(file, board(['- One (2026-10-01 · sample)', '- Two (2026-10-02 · sample)']), { revision: stale }), /stale revision/);
  assert.equal(lib.writeBoard(file, board(['- One (2026-10-01 · sample)', '- Two (2026-10-02 · sample)']), { revision: fresh }).changed, true);
});

test('a simultaneous owner correction survives a fold', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const file = lib.boardPath(home);
  const read = lib.readBoard(file);
  const owner = board(['- Owner correction (2026-10-13 · owner)']);
  lib.writeBoard(file, owner, { revision: read.revision });
  assert.throws(() => lib.foldBoard(file, lib.EMPTY_BOARD, { revision: read.revision }), /stale revision/);
  assert.ok(fs.readFileSync(file, 'utf8').includes('Owner correction'));
});

test('preparation of an agent outside .rbtv/agents/', (dir) => {
  const home = path.join(dir, 'outside-agent');
  install(dir, home);
  const prepared = lib.prepareMemory({ installation: dir, agentHome: home, cwd: dir });
  assert.equal(prepared.identity.agentHome, home);
  assert.ok(prepared.bundle.some((row) => row.path.endsWith('profile.md')));
  assert.ok(prepared.bundle.some((row) => row.path.endsWith('learned.md')));
});

test('no foreign board for a workspace match', (dir) => {
  const home = path.join(dir, 'agent');
  const other = path.join(dir, '.rbtv', 'agents', 'other');
  install(dir, home);
  fs.mkdirSync(path.join(other, '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(other, '_artifacts', 'board.md'), board(['- Foreign (2026-10-01 · other)']), 'utf8');
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory', 'workspaces'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'workspaces', 'work.md'), '---\ntype: workspace\npaths: [work]\n---\n# Work\n\n- Note (2026-10-01 · note)\n', 'utf8');
  fs.mkdirSync(path.join(dir, 'work'), { recursive: true });
  const prepared = lib.prepareMemory({ installation: dir, agentHome: home, cwd: path.join(dir, 'work') });
  assert.equal(prepared.bundle.some((row) => row.text.includes('Foreign')), false);
  assert.ok(prepared.bundle.some((row) => row.path.endsWith('work.md')));
});

test('a new project agent without personal records is not master', (dir) => {
  const home = path.join(dir, 'project-agent');
  fs.mkdirSync(home, { recursive: true });
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory', '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'profile.md'), '# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), '# Inbox\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', '_artifacts', 'index.md'), '# Memory\n\n| Open | When |\n|---|---|\n', 'utf8');
  const prepared = lib.prepareMemory({ installation: dir, agentHome: home });
  assert.equal(prepared.identity.master, false);
  assert.ok(prepared.warnings.some((line) => line.includes('not master')));
  assert.equal(prepared.bundle.some((row) => row.path.includes(`${path.sep}master${path.sep}`)), false);
});

test('missing expected record recovers last good with a warning', (dir) => {
  const home = path.join(dir, 'agent');
  install(dir, home);
  const learned = path.join(home, 'memory', 'learned.md');
  fs.writeFileSync(learned, 'broken', 'utf8');
  const prepared = lib.prepareMemory({ installation: dir, agentHome: home });
  const row = prepared.bundle.find((item) => item.path === learned);
  assert.equal(row.source, 'HEAD');
  assert.match(row.text, /# Learned rules/);
  assert.ok(prepared.warnings.some((line) => line.includes('Loaded checked HEAD copy')));
});

test('commitment creation, evidence-based completion, agent self-report stored as annotation, missed due date unchanged', (dir) => {
  const created = lib.createCommitment(dir, { debtor: 'ada', creditor: 'owner', action: 'send the note', sources: 'owner said so', due_at: '2020-01-01' });
  assert.equal(created.status, 'open');
  const noted = lib.annotateCommitment(dir, created.id, 'agent says it is done');
  assert.equal(noted.status, 'open');
  assert.equal(noted.annotated, true);
  const missed = lib.missDueDate(dir, created.id);
  assert.equal(missed.changed, false);
  assert.equal(missed.status, 'open');
  const done = lib.setCommitmentStatus(dir, created.id, 'done', { artifact: 'note.md' });
  assert.equal(done.status, 'done');
  assert.equal(done.prior, 'open');
  const text = fs.readFileSync(lib.collectionPath(dir), 'utf8');
  assert.match(text, /open -> done/);
  assert.match(text, /agent says it is done/);
});

test('evidence intake with missing verification stays pending', (dir) => {
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory'), { recursive: true });
  const result = lib.intakeEvidence(dir, 'Owner likes tea', {
    agent: 'sample',
    evidence: { sourceKind: 'transcript', sourceRef: 'meet-1', author: 'owner', quote: 'I like tea', connector: { accessible: false }, observed: true },
  });
  assert.equal(result.pending, true);
  assert.equal(result.claim, false);
  assert.equal(fs.existsSync(path.join(dir, '.rbtv', 'memory', 'inbox.md')), false);
  const saved = JSON.parse(fs.readFileSync(result.path, 'utf8'));
  assert.equal(saved.status, 'pending');
  assert.equal(saved.quote, 'I like tea');
});

test('global rule refused without approval reference and accepted with one', (dir) => {
  const text = '# Learned rules — installation\n- [correction] Ask first. Why: owner said so. (2026-10-13 · owner/[thread](https://example.com/1))\n';
  assert.throws(() => lib.publishGlobalRule(dir, text, {}), /approval reference/);
  assert.throws(() => lib.publishGlobalRule(dir, text, { approval: 'owner-2026-10-13', migrated: true }), /migrated feedback is not global approval/);
  const published = lib.publishGlobalRule(dir, text, { approval: 'owner-2026-10-13' });
  assert.equal(published.published, true);
  assert.equal(fs.readFileSync(published.path, 'utf8').includes('Ask first'), true);
});

test('4000 and 30 limits', () => {
  const profile = `# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n${'x'.repeat(4001)}`;
  assert.equal(lib.checkLimits('profile', profile).hard.cap, 4000);
  const learned = `# Learned rules — sample\n${Array.from({ length: 31 }, (_, i) => `- [correction] Rule ${i}. Why: owner. (2026-10-01 · sample/[t](https://example.com/${i}))\n`).join('')}`;
  assert.equal(lib.checkLimits('learned', learned).hard.cap, 30);
  assert.equal(lib.checkLimits('profile', '# Profile — Sam\n\n## Who\n\n## Working with Sam\n\n## Now\n').hard, null);
});

test('warn at 100 and split at 300 nonempty lines at record boundaries with originals kept', (dir) => {
  const rows = Array.from({ length: 300 }, (_, i) => `- Fact ${i} (2026-10-01 · note)`);
  const text = `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# Facts\n\n${rows.join('\n')}\n`;
  const checked = lib.checkLimits('knowledge', text);
  assert.ok(checked.warnings.length);
  assert.equal(checked.split, true);
  const split = lib.splitOnDemand(text);
  assert.equal(split.flagged, null);
  assert.ok(lib.nonemptyLines(split.parts.source).length < 300);
  const combined = `${split.parts.source}\n${split.parts.moved.join('\n')}`;
  for (const row of rows) assert.ok(combined.includes(row));
  const file = path.join(dir, 'original.md');
  fs.writeFileSync(file, text);
  assert.equal(fs.readFileSync(file, 'utf8'), text);
});

test('indivisible record retained and flagged', () => {
  const block = `- Fact\n${Array.from({ length: 299 }, () => '  continued').join('\n')}`;
  const text = `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# Facts\n\n${block}\n`;
  const split = lib.splitOnDemand(text);
  assert.equal(split.parts, null);
  assert.ok(split.flagged);
  assert.ok(split.flagged.includes('continued'));
});

function judgedProposal() {
  const token = 'shape-token-not-for-alert';
  const snapshotToken = 'snapshot-token-not-for-alert';
  const alpha = '.rbtv/agents/master/memory/alpha.md';
  const beta = '.rbtv/agents/master/memory/beta.md';
  const outside = 'notes/outside.md';
  const raw = {
    operations: [
      { op: 'add', path: outside, text: `outside ${token}`, sources: [], reason: 'owner', explanation: 'because' },
      {
        op: 'add', path: alpha, sources: [], reason: 'owner', explanation: 'because',
        text: `---\ndescription: when reviewing alpha\ntype: subject\n---\n# Alpha\n\nThreads: none\n- undated ${token}\n`,
      },
      {
        op: 'add', path: beta, sources: [], reason: 'owner', explanation: 'because',
        text: `---\ndescription: when reviewing beta\ntype: subject\naliases: [beta]\n---\n# Beta\n\n- a fact (2026-10-13 · master)\n`,
      },
    ],
    conflicts: [{ path: token, text: token, sources: [], explanation: token }],
  };
  const input = {
    agent: 'master', date: '2026-10-13', messages: [],
    files: { '.rbtv/memory/inbox.md': `# Inbox\n\n- ${snapshotToken} (2026-10-01 · master)\n`, '.rbtv/memory/profile.md': '# Profile\n' },
  };
  return { raw, input, token, snapshotToken, alpha, beta, outside };
}

test('conflict object, outside add, missing aliases, undated record and missing Threads are all named with paths', (dir) => {
  install(dir, path.join(dir, 'agent'));
  const judged = judgedProposal();
  const before = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: dir, encoding: 'utf8' }).stdout.trim();
  const result = lib.publishProposal(judged.input, judged.raw, dir);
  assert.equal(result.ok, false);
  assert.equal(result.published, false);
  assert.equal(spawnSync('git', ['rev-parse', 'HEAD'], { cwd: dir, encoding: 'utf8' }).stdout.trim(), before);
  const body = JSON.stringify(result.failures);
  assert.equal(body.includes(judged.token), false);
  assert.equal(body.includes(judged.snapshotToken), false);
  const by = (reason) => result.failures.filter((row) => row.reason === reason);
  const conflict = by('invalid conflict');
  assert.equal(conflict.length, 1);
  assert.equal(conflict[0].path, null);
  assert.equal(conflict[0].operation, null);
  assert.notEqual(conflict[0].expected, conflict[0].reason);
  const outside = by('path outside agent memory or repeated operation');
  assert.equal(outside.length, 1);
  assert.equal(outside[0].path, judged.outside);
  assert.equal(outside[0].operation, '0 add');
  assert.notEqual(outside[0].expected, outside[0].reason);
  const aliases = by('topic aliases required');
  assert.equal(aliases.length, 1);
  assert.equal(aliases[0].path, judged.alpha);
  assert.equal(aliases[0].operation, '1 add');
  assert.notEqual(aliases[0].expected, aliases[0].reason);
  const dated = by('records require dated provenance');
  assert.equal(dated.length, 1);
  assert.equal(dated[0].path, judged.alpha);
  assert.equal(dated[0].operation, '1 add');
  const threads = by('subject topics require Threads');
  assert.equal(threads.length, 1);
  assert.equal(threads[0].path, judged.beta);
  assert.equal(threads[0].operation, '2 add');
  assert.notEqual(threads[0].expected, threads[0].reason);
});

test('shape fault in conflicts does not hide later operation failures', (dir) => {
  const judged = judgedProposal();
  const result = lib.validateProposalResult(judged.input, judged.raw, dir);
  assert.equal(result.ok, false);
  assert.equal(result.failures.some((row) => row.reason === 'invalid conflict'), true);
  assert.equal(result.failures.some((row) => row.path === judged.outside), true);
});

test('one file reports every independent form error', (dir) => {
  const judged = judgedProposal();
  const result = lib.validateProposalResult(judged.input, judged.raw, dir);
  const alpha = result.failures.filter((row) => row.path === judged.alpha).map((row) => row.reason);
  assert.equal(alpha.includes('topic aliases required'), true);
  assert.equal(alpha.includes('records require dated provenance'), true);
});

test('each operation failure names path, operation and expected form', (dir) => {
  const judged = judgedProposal();
  const result = lib.validateProposalResult(judged.input, judged.raw, dir);
  for (const row of result.failures) {
    if (row.reason === 'invalid conflict') {
      assert.equal(row.path, null);
      assert.equal(row.operation, null);
    } else {
      assert.equal(typeof row.path, 'string');
      assert.match(row.operation, /^\d+ add$/);
    }
    assert.notEqual(row.expected, row.reason);
    assert.equal(typeof row.expected, 'string');
  }
});

test('malformed proposal bytes retained and nothing published', (dir) => {
  install(dir, path.join(dir, 'agent'));
  const before = spawnSync('git', ['rev-parse', 'HEAD'], { cwd: dir, encoding: 'utf8' }).stdout.trim();
  const result = lib.publishProposal({ agent: 'master', date: '2026-10-13', messages: [], files: {} }, 'not json', dir);
  assert.equal(result.ok, false);
  assert.ok(result.failures.length);
  assert.ok(result.failures.some((row) => row.reason.includes('JSON') || row.reason.includes('operations')));
  const retained = fs.readFileSync(result.retained);
  assert.equal(retained.equals(Buffer.from('not json')), true);
  assert.equal(spawnSync('git', ['rev-parse', 'HEAD'], { cwd: dir, encoding: 'utf8' }).stdout.trim(), before);
});

test('validator returns every failed requirement with its own reason', (dir) => {
  install(dir, path.join(dir, 'agent'));
  const raw = {
    operations: [
      { op: 'nope', path: '.rbtv/memory/profile.md', text: 'x', sources: [], reason: 'owner', explanation: 'because' },
      { op: 'add', path: '.rbtv/memory/topics/missing.md', text: 'x', sources: [], reason: 'owner', explanation: 'because' },
    ],
    conflicts: ['one'],
  };
  const result = lib.validateProposalResult({
    agent: 'master', date: '2026-10-13', messages: [], files: { '.rbtv/memory/inbox.md': '# Inbox\n', '.rbtv/memory/profile.md': '# Profile\n' },
  }, raw, dir);
  assert.equal(result.ok, false);
  assert.ok(result.failures.length >= 2, result.failures.map((row) => row.reason).join(' | '));
  assert.equal(new Set(result.failures.map((row) => row.reason)).size, result.failures.length);
  assert.equal(result.failures.some((row) => row.reason === 'invalid operation'), true);
  assert.equal(result.failures.some((row) => /outside agent memory|unsafe|path/.test(row.reason)), true);
});

test('two concurrent writers both survive', (dir) => {
  install(dir, path.join(dir, 'agent'));
  const script = `
    const lib = require(${JSON.stringify(path.join(__dirname, 'lib/index.js'))});
    lib.remember(${JSON.stringify(dir)}, process.argv[2], { agent: 'sample' });
  `;
  const file = path.join(dir, 'append.js');
  fs.writeFileSync(file, script);
  const kids = [0, 1].map((i) => spawnSync(process.execPath, [file, `fact ${i}`], { encoding: 'utf8' }));
  for (const kid of kids) assert.equal(kid.status, 0, kid.stderr);
  const inbox = fs.readFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), 'utf8');
  assert.match(inbox, /fact 0/);
  assert.match(inbox, /fact 1/);
});

function generalMemory(dir) {
  fs.mkdirSync(path.join(dir, '.rbtv', 'memory', '_artifacts'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'profile.md'), '# Profile — Sam\n\n## Who\n\n- One (2026-10-01 · note)\n\n## Working with Sam\n\n- Two (2026-10-01 · note)\n\n## Now\n\n- Three (2026-10-01 · note)\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', 'inbox.md'), '# Inbox\n', 'utf8');
  fs.writeFileSync(path.join(dir, '.rbtv', 'memory', '_artifacts', 'index.md'), '# Memory\n\n| Open | When |\n|---|---|\n| [facts](../knowledge/facts.md) | when reviewing facts |\n', 'utf8');
}

test('agent baseline lets prepare and snapshot succeed without a hand-written memory folder', (dir) => {
  const home = path.join(dir, '.rbtv', 'agents', 'sample');
  fs.mkdirSync(path.join(home, '_artifacts'), { recursive: true });
  fs.writeFileSync(lib.boardPath(home), lib.EMPTY_BOARD, 'utf8');
  generalMemory(dir);
  assert.equal(fs.existsSync(path.join(home, 'memory')), false);
  const created = lib.ensureAgentBaseline(home);
  assert.equal(created.created.length, 1);
  const text = fs.readFileSync(created.created[0], 'utf8');
  lib.checkMemory('learned', text);
  assert.equal(text, `${lib.LEARNED_HEADING}sample\n`);
  const prepared = lib.prepareMemory({ installation: dir, agentHome: home });
  const learned = prepared.bundle.find((row) => row.path === created.created[0]);
  assert.equal(learned.source, 'working');
  assert.equal(prepared.warnings.some((row) => row.includes(created.created[0])), false);
  const files = lib.snapshot(dir, [{ slug: 'sample' }]);
  assert.equal(files.has(`.rbtv/agents/sample/memory/${lib.LEARNED_FILE}`), true);
  assert.equal(fs.existsSync(path.join(home, 'memory', '_artifacts')), false);
  spawnSync('git', ['init', '-q'], { cwd: dir });
  const tracked = spawnSync('git', ['ls-files', '.rbtv/agents/sample/memory'], { cwd: dir, encoding: 'utf8' });
  assert.equal(tracked.stdout.trim(), '');
});

test('existing memory bytes stay identical when the baseline is already present', (dir) => {
  const home = path.join(dir, '.rbtv', 'agents', 'sample');
  const learned = path.join(home, 'memory', 'learned.md');
  const topic = path.join(home, 'memory', 'topic.md');
  fs.mkdirSync(path.dirname(learned), { recursive: true });
  const learnedBytes = Buffer.from('# Learned rules — sample\n- [correction] Keep. Why: owner. (2026-10-01 · sample/[t](https://example.com/1))\n');
  const topicBytes = Buffer.from('topic bytes\n');
  fs.writeFileSync(learned, learnedBytes);
  fs.writeFileSync(topic, topicBytes);
  const result = lib.ensureAgentBaseline(home);
  assert.deepEqual(result.created, []);
  assert.deepEqual(fs.readFileSync(learned), learnedBytes);
  assert.deepEqual(fs.readFileSync(topic), topicBytes);
});

test('memory baseline verb creates the record and refuses a missing agent home', (dir) => {
  const home = path.join(dir, '.rbtv', 'agents', 'sample');
  fs.mkdirSync(home, { recursive: true });
  const program = path.join(__dirname, 'memory.js');
  const missing = spawnSync(process.execPath, [program, 'baseline'], { encoding: 'utf8', cwd: dir });
  assert.equal(missing.status, 1);
  assert.match(missing.stderr, /--agent-home is required/);
  assert.equal(missing.stdout, '');
  const created = spawnSync(process.execPath, [program, 'baseline', '--agent-home', home], { encoding: 'utf8', cwd: dir });
  assert.equal(created.status, 0, created.stderr);
  assert.equal(created.stdout, `created ${lib.agentBaselinePath(home)}\n`);
  const again = spawnSync(process.execPath, [program, 'baseline', '--agent-home', home], { encoding: 'utf8', cwd: dir });
  assert.equal(again.status, 0, again.stderr);
  assert.equal(again.stdout, `present ${lib.agentBaselinePath(home)}\n`);
});

const THREAD = 'https://app.slack.com/archives/C0TEST00001/p1791000000000001';
const OTHER_THREAD = 'https://app.slack.com/archives/C0TEST00002/p1791000000000002';
const FORGET = '- Owner asks to forget: handheld-1001. Owner said: drop it (2026-10-13 · master)';
const BOARD = '.rbtv/agents/master/_artifacts/board.md';

function archiveFile(original, reason, source) {
  return `---\ndescription: when reviewing an archived record\ntype: reference\naliases: [archived]\n---\n# Archived\n\n- Reason: ${reason}. Source: ${source} (2026-10-13 · master)\n\n\`\`\`verbatim\n${original}\`\`\`\n`;
}

function removalCase(shape) {
  const entity = shape === 'live'
    ? `---\ndescription: when identifying the handheld by its name\ntype: device\naliases: [handheld-1001]\n---\n# Handheld-1001\n\n- The handheld is named Handheld-1001. (2026-10-13 · master/${THREAD})\n`
    : `---\ndescription: when reviewing a decision\ntype: decisions\naliases: [handheld-1001]\n---\n# Handheld note\n\n- The note says Handheld-1001. (2026-10-13 · master/${THREAD})\n`;
  const record = entity.trim().split('\n').at(-1);
  const entityPath = shape === 'live'
    ? '.rbtv/memory/entities/devices/handheld-1001.md'
    : '.rbtv/memory/knowledge/decisions/handheld-1001.md';
  const otherPath = shape === 'live'
    ? '.rbtv/memory/entities/devices/other-2002.md'
    : '.rbtv/memory/knowledge/decisions/other-2002.md';
  const other = shape === 'live'
    ? `---\ndescription: when reviewing the other device\ntype: device\naliases: [other-2002]\n---\n# Other-2002\n\n- Other stays. (2026-10-01 · master)\n`
    : `---\ndescription: when reviewing the other decision\ntype: decisions\naliases: [other-2002]\n---\n# Other\n\n- Other stays. (2026-10-01 · master)\n`;
  const indexPath = shape === 'live'
    ? '.rbtv/memory/entities/_artifacts/index.md'
    : '.rbtv/memory/knowledge/_artifacts/index.md';
  const link = shape === 'live' ? '../devices/handheld-1001.md' : '../decisions/handheld-1001.md';
  const otherLink = shape === 'live' ? '../devices/other-2002.md' : '../decisions/other-2002.md';
  const indexRow = `| [Handheld-1001](${link}) | when identifying the handheld |`;
  const otherRow = `| [Other](${otherLink}) | when reviewing the other record |`;
  const index = `# Index\n\n| Open | When |\n|---|---|\n${otherRow}\n${indexRow}\n`;
  const dayPath = '.rbtv/memory/timeline/daily/2026-10-13.md';
  const episode = `- Named the handheld. — master/[thread](${THREAD})`;
  const kept = `- Kept episode. — master/[thread](${OTHER_THREAD})`;
  const day = `---\ndescription: when asked what happened on 2026-10-13\n---\n# 2026-10-13\n\n${kept}\n${episode}\n`;
  const sibling = '.rbtv/memory/knowledge/facts.md';
  const siblingText = `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# Facts\n\n- Unrelated fact. (2026-10-01 · master)\n`;
  const archivePath = '.rbtv/memory/_artifacts/archive/handheld-1001.md';
  const files = {
    [entityPath]: entity,
    [otherPath]: other,
    [indexPath]: index,
    [dayPath]: day,
    [sibling]: siblingText,
    [BOARD]: lib.EMPTY_BOARD,
    '.rbtv/memory/inbox.md': `# Inbox\n\n${FORGET}\n`,
  };
  return { entity, record, entityPath, otherPath, other, indexPath, index, indexRow, otherRow, dayPath, day, episode, kept, sibling, siblingText, archivePath, files };
}

function proposal(parts, extra = {}) {
  return { operations: parts, conflicts: extra.conflicts || [] };
}

function op(fields) {
  return { sources: [FORGET], reason: 'owner', explanation: 'owner asked to forget', removals: [], ...fields };
}

function removalProposal(box, { item, reason = 'owner asked to forget', source = FORGET, sources = [FORGET], dropIndex = true, dropDay = true, archive = true } = {}) {
  const archiveText = archiveFile(box.entity, reason, source);
  const parts = [
    op({
      op: 'archive', path: box.entityPath, leave: true, text: box.entity, sources, item,
      removals: [{ text: box.record, to: box.archivePath }],
    }),
  ];
  if (archive) parts.push(op({ op: 'add', path: box.archivePath, text: archiveText, sources }));
  if (dropIndex) {
    parts.push(op({
      op: 'supersede', path: box.indexPath, reason: 'index', text: box.index.replace(`${box.indexRow}\n`, ''),
      sources, removals: [{ text: box.indexRow }],
    }));
  }
  if (dropDay) {
    parts.push(op({
      op: 'supersede', path: box.dayPath, text: box.day.replace(`${box.episode}\n`, ''),
      sources, removals: [{ text: box.episode }],
    }));
  }
  return proposal(parts);
}

function inputFor(box) {
  return { agent: 'master', date: '2026-10-13', messages: [], files: box.files };
}

function reasons(result) {
  return (result.failures || []).map((row) => row.reason);
}

test('archive-removal of a whole-file record drops its index row and timeline line', (dir) => {
  const box = removalCase('knowledge');
  for (const [file, text] of Object.entries(box.files)) {
    const abs = path.join(dir, file);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    fs.writeFileSync(abs, text);
  }
  const before = new Map(Object.entries(box.files).map(([file, text]) => [file, fs.readFileSync(path.join(dir, file))]));
  const raw = removalProposal(box);
  const result = lib.publishProposal(inputFor(box), raw, dir, { gitCommit: () => ({ stdout: 'abc\n' }) });
  assert.equal(result.ok, true, reasons(result).join(' | '));
  assert.equal(result.published, true);
  assert.equal(fs.existsSync(path.join(dir, box.entityPath)), false);
  const archived = fs.readFileSync(path.join(dir, box.archivePath), 'utf8');
  assert.ok(archived.includes(box.entity));
  assert.ok(archived.includes('Reason: owner asked to forget'));
  assert.ok(archived.includes(`Source: ${FORGET}`));
  const index = fs.readFileSync(path.join(dir, box.indexPath), 'utf8');
  assert.equal(index.includes(box.indexRow), false);
  assert.ok(index.includes(box.otherRow));
  const day = fs.readFileSync(path.join(dir, box.dayPath), 'utf8');
  assert.equal(day.includes(box.episode), false);
  assert.ok(day.includes(box.kept));
  assert.deepEqual(fs.readFileSync(path.join(dir, box.otherPath)), before.get(box.otherPath));
  assert.deepEqual(fs.readFileSync(path.join(dir, box.sibling)), before.get(box.sibling));
  assert.deepEqual(fs.readFileSync(path.join(dir, '.rbtv/memory/inbox.md')), before.get('.rbtv/memory/inbox.md'));
});

test('real-shaped archive-removal matches the live publication shape', (dir) => {
  const box = removalCase('live');
  const result = lib.validateProposalResult(inputFor(box), removalProposal(box), dir);
  assert.equal(result.ok, true, reasons(result).join(' | '));
  assert.equal(result.files.has(box.entityPath), false);
  assert.ok(result.files.get(box.archivePath).includes('```verbatim\n' + box.entity));
  assert.equal(result.files.get(box.indexPath).includes('](../devices/handheld-1001.md)'), false);
  assert.equal(result.files.get(box.dayPath).includes(box.episode), false);
  assert.ok(result.files.get(box.dayPath).includes(box.kept));
});

test('reversed item reference archives a whole file without owner evidence', (dir) => {
  const box = removalCase('live');
  const raw = removalProposal(box, { item: 'run-1#1', reason: 'reversed', source: 'run-1#1', sources: [] });
  const result = lib.validateProposalResult(inputFor(box), raw, dir);
  assert.equal(result.ok, true, reasons(result).join(' | '));
  assert.ok(result.files.get(box.archivePath).includes('Reason: reversed'));
  assert.ok(result.files.get(box.archivePath).includes('Source: run-1#1'));
});

test('removal without an archive entry is refused', (dir) => {
  const box = removalCase('live');
  const result = lib.validateProposalResult(inputFor(box), removalProposal(box, { archive: false }), dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('removal without an archive entry'), reasons(result).join(' | '));
});

test('index or timeline line dropped while the record it points at stays is refused', (dir) => {
  const box = removalCase('live');
  const raw = proposal([op({
    op: 'supersede', path: box.indexPath, reason: 'index', text: box.index.replace(`${box.indexRow}\n`, ''),
    removals: [{ text: box.indexRow }],
  })]);
  const result = lib.validateProposalResult(inputFor(box), raw, dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('index or timeline line dropped while the record it points at stays'), reasons(result).join(' | '));
});

test('dropped line that does not point at the archived record is refused', (dir) => {
  const box = removalCase('live');
  const raw = removalProposal(box, { dropDay: false });
  raw.operations.push(op({
    op: 'supersede', path: box.dayPath, text: box.day.replace(`${box.kept}\n`, ''),
    removals: [{ text: box.kept }],
  }));
  const result = lib.validateProposalResult(inputFor(box), raw, dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('dropped line does not point at the archived record'), reasons(result).join(' | '));
});

test('removal needs a stated reason and a source', (dir) => {
  const box = removalCase('live');
  const raw = removalProposal(box, { reason: 'unspecified', source: 'none', sources: [] });
  const result = lib.validateProposalResult(inputFor(box), raw, dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('removal needs a stated reason and a source'), reasons(result).join(' | '));
});

test('index link left pointing at a record this proposal removes is refused', (dir) => {
  const box = removalCase('live');
  const raw = removalProposal(box, { dropIndex: false });
  const result = lib.validateProposalResult(inputFor(box), raw, dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('index link points at a missing memory file'), reasons(result).join(' | '));
});

test('replacement needs owner evidence and a replacement record still refuses a knowledge bullet drop', (dir) => {
  const file = '.rbtv/memory/knowledge/facts.md';
  const text = `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# Facts\n\n- Keep. (2026-10-01 · master)\n- Drop. (2026-10-01 · master)\n`;
  const next = text.replace('- Drop. (2026-10-01 · master)\n', '');
  const raw = proposal([op({
    op: 'supersede', path: file, text: next, sources: [1],
    removals: [{ text: '- Drop. (2026-10-01 · master)' }],
  })]);
  const result = lib.validateProposalResult({
    agent: 'master', date: '2026-10-13', messages: [{ rowid: 1, text: 'drop', thread: THREAD, conversation_key: 'c' }],
    files: { ...removalCase('live').files, [file]: text },
  }, raw, dir);
  assert.equal(result.ok, false);
  assert.ok(reasons(result).includes('replacement needs owner evidence and a replacement record'), reasons(result).join(' | '));
});

test('restore returns the tree apart from the archive record of the round trip', (dir) => {
  const box = removalCase('live');
  for (const [file, text] of Object.entries(box.files)) {
    const abs = path.join(dir, file);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    fs.writeFileSync(abs, text);
  }
  const gitCommit = () => ({ stdout: 'abc\n' });
  const removed = lib.publishProposal(inputFor(box), removalProposal(box), dir, { gitCommit });
  assert.equal(removed.ok, true, reasons(removed).join(' | '));
  const after = {};
  for (const file of [box.otherPath, box.indexPath, box.dayPath, box.archivePath, box.sibling, BOARD, '.rbtv/memory/inbox.md']) {
    after[file] = fs.readFileSync(path.join(dir, file), 'utf8');
  }
  const restoredArchive = `${after[box.archivePath]}# Restored\n`;
  const raw = proposal([
    op({ op: 'add', path: box.entityPath, text: box.entity, sources: [], explanation: 'restore the archived record' }),
    op({ op: 'supersede', path: box.indexPath, reason: 'index', text: box.index, sources: [], explanation: 'restore the index row' }),
    op({ op: 'supersede', path: box.dayPath, text: box.day, sources: [], explanation: 'restore the timeline line' }),
    op({ op: 'supersede', path: box.archivePath, text: restoredArchive, sources: [], explanation: 'mark the archive entry restored' }),
  ]);
  const again = lib.publishProposal({
    agent: 'master', date: '2026-10-13', messages: [], files: after,
  }, raw, dir, { gitCommit });
  assert.equal(again.ok, true, reasons(again).join(' | '));
  assert.equal(fs.readFileSync(path.join(dir, box.entityPath), 'utf8'), box.entity);
  assert.equal(fs.readFileSync(path.join(dir, box.indexPath), 'utf8'), box.index);
  assert.equal(fs.readFileSync(path.join(dir, box.dayPath), 'utf8'), box.day);
  const round = fs.readFileSync(path.join(dir, box.archivePath), 'utf8');
  assert.ok(round.includes(box.entity));
  assert.ok(round.includes('# Restored'));
  assert.deepEqual(fs.readFileSync(path.join(dir, box.sibling)), Buffer.from(box.siblingText));
});

if (failed.length) process.exit(1);
