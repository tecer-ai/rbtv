'use strict';

const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { extractFile, keep } = require('./lib/rules.js');
const store = require('./lib/store.js');

const tool = path.join(__dirname, 'albert.js');
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, detail) {
  failed += 1;
  process.stdout.write(`FAIL ${name} ${detail}\n`);
}
function assert(name, ok, detail) { if (ok) pass(name); else fail(name, detail || ''); }

function git(cwd, args) {
  const result = spawnSync('git', ['-C', cwd, ...args], { encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || result.stdout);
  return result.stdout.trim();
}

function write(file, text) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, text);
}

function run(home, args, env = {}) {
  return spawnSync(process.execPath, [tool, ...args], {
    cwd: home,
    encoding: 'utf8',
    env: { ...process.env, RBTV_AGENT_HOME: home, ...env },
  });
}

const board = '## What matters now\n\n## Watch-outs\n\n## Timers\n\n## Recently closed\n';
const { candidates } = require('./lib/library.js');

function withPath(dir, fn) {
  const prevPath = process.env.PATH;
  const prevLib = process.env.ALBERT_MEMORY_LIB;
  process.env.PATH = dir;
  delete process.env.ALBERT_MEMORY_LIB;
  try { return fn(); } finally {
    process.env.PATH = prevPath;
    if (prevLib === undefined) delete process.env.ALBERT_MEMORY_LIB;
    else process.env.ALBERT_MEMORY_LIB = prevLib;
  }
}

const shimRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'albert-shim-'));
const shimRepo = path.join(shimRoot, 'repo');
const shimTool = path.join(shimRepo, 'core', 'memory', 'capabilities', 'tools', 'memory');
const shimLib = path.join(shimTool, 'lib', 'index.js');
write(shimLib, 'module.exports = {};\n');
const shimEntry = path.join(shimTool, 'memory.js');
write(shimEntry, '#!/usr/bin/env node\n');
const shimBin = path.join(shimRoot, 'bin');
write(path.join(shimBin, 'memory.cmd'), `@rem rbtv-shim -> ${shimEntry}\r\n@"node" "${shimEntry}" %*\r\n`);
write(path.join(shimBin, 'memory'), `#!/bin/sh\n# rbtv-shim -> ${shimEntry}\nexec node "${shimEntry}" "$@"\n`);
assert('windows shim target is the memory program', withPath(shimBin, () => candidates().includes(shimLib)), '');
const cmdOnly = path.join(shimRoot, 'cmd-only');
fs.mkdirSync(cmdOnly);
write(path.join(cmdOnly, 'memory'), fs.readFileSync(path.join(shimBin, 'memory.cmd')));
assert('cmd shim first line is the memory program', withPath(cmdOnly, () => candidates().includes(shimLib)), '');
const linkBin = path.join(shimRoot, 'link');
fs.mkdirSync(linkBin);
fs.symlinkSync(shimEntry, path.join(linkBin, 'memory'));
assert('memory symlink resolves beside the program', withPath(linkBin, () => candidates().includes(shimLib)), '');
const installer = path.join(shimRepo, 'core', 'rbtv', 'capabilities', 'tools', 'rbtv', 'install.py');
write(installer, '#!/usr/bin/env python3\n');
const rbtvBin = path.join(shimRoot, 'rbtv-bin');
fs.mkdirSync(rbtvBin);
fs.symlinkSync(installer, path.join(rbtvBin, 'rbtv'));
assert('rbtv command resolves the repository library', withPath(rbtvBin, () => candidates().includes(shimLib)), '');
const rootHelp = spawnSync(process.execPath, [tool, '-h'], { encoding: 'utf8' }).stdout;
assert('root help names the library path', rootHelp.includes('lib/index.js beside the memory command') && rootHelp.includes('~/.rbtv/bin must be on PATH') && rootHelp.includes('ALBERT_MEMORY_LIB'), rootHelp);
const profile = '# Profile — Owner\n\n## Who\n\n- Owner (2026-01-01 · albert)\n\n## Working with owner\n\n- prefers short notes (2026-01-01 · albert)\n\n## Now\n\n- none pending (2026-01-01 · albert)\n';
const learned = '# Learned rules — albert\n';
const index = '# Memory\n\n| Open | When |\n| --- | --- |\n';
const line = '- note (2026-10-01 · albert)';

function memory(root, home, inbox) {
  write(path.join(root, '.rbtv/memory/profile.md'), profile);
  write(path.join(root, '.rbtv/memory/inbox.md'), inbox);
  write(path.join(root, '.rbtv/memory/_artifacts/index.md'), index);
  write(path.join(home, 'memory/learned.md'), learned);
  write(path.join(home, '_artifacts/board.md'), board);
}

function fixture(inbox = '# Inbox\n') {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'albert-'));
  git(root, ['init', '-q']);
  git(root, ['config', 'user.email', 't@example.com']);
  git(root, ['config', 'user.name', 'Test']);
  const home = path.join(root, '.rbtv', 'agents', 'albert');
  memory(root, home, inbox);
  git(root, ['add', '.']);
  git(root, ['commit', '-q', '-m', 'init']);
  return { root, home };
}

function emptyHome() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'albert-empty-'));
  const home = path.join(root, '.rbtv', 'agents', 'albert');
  fs.mkdirSync(home, { recursive: true });
  return { root, home };
}

function json(result) {
  return JSON.parse(result.stdout);
}

const quiet = emptyHome();
const checked = run(quiet.home, ['check']);
assert('quiet check prints {"new":false}', checked.status === 0 && checked.stdout.trim() === '{"new":false}', checked.stdout + checked.stderr);
assert('quiet check records liveness', fs.existsSync(store.livenessFile(quiet.home)), '');
const castDir = fs.mkdtempSync(path.join(os.tmpdir(), 'albert-cast-'));
const marker = path.join(castDir, 'started');
write(path.join(castDir, 'cast'), `#!/bin/sh\ntouch ${marker}\n`);
fs.chmodSync(path.join(castDir, 'cast'), 0o755);
const castRun = run(quiet.home, ['check'], { PATH: `${castDir}${path.delimiter}${process.env.PATH}` });
assert('quiet check starts no model', castRun.status === 0 && !fs.existsSync(marker), castRun.stderr);

function reason(setup, name, expect) {
  const box = fixture();
  setup(box);
  const result = run(box.home, ['check']);
  const body = result.status === 0 ? json(result) : null;
  assert(name, body && body.new === true && body.details && body.details.reasons.includes(expect), result.stdout + result.stderr);
}

reason((box) => write(path.join(box.root, '.rbtv/memory/inbox.md'), `# Inbox\n${line}\n`), 'check reports inbox candidate', 'inbox');
reason((box) => {
  const text = board.replace('## Watch-outs\n', '## Watch-outs\n- do not repeat that (2026-01-01 · albert)\n');
  write(path.join(box.home, '_artifacts/board.md'), text);
}, 'check reports pending watch-out', 'watch-out');
reason((box) => {
  write(path.join(box.root, '.rbtv/memory/knowledge/facts.md'), '---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# facts\n\n- temporary note until 2020-01-01 (2026-01-01 · albert)\n');
}, 'check reports expiry', 'expiry');
reason((box) => store.writeJson(store.maintenanceFile(box.home), { dueAt: 1 }), 'check reports due maintenance', 'maintenance');
reason((box) => {
  const rows = [{ id: 'n1', author: 'owner', text: 'seen' }];
  const contentHash = crypto.createHash('sha256').update(JSON.stringify(rows)).digest('hex');
  write(path.join(store.evidenceDir(box.home), 'batch.json'), JSON.stringify({
    sourceKind: 'conversation', sourceAgent: 'other', sourceCursor: 'messages', ceiling: 3, contentHash, rows,
  }));
}, 'check reports evidence batch', 'evidence');

const shaped = fixture();
const shape = run(shaped.home, ['check']);
assert('check from agent home matches timer shapes', shape.status === 0 && shape.stdout.trim() === '{"new":false}', shape.stdout);

const early = run(fixture().home, ['watchdog']);
const earlyBody = json(early);
assert('watchdog fires when no success is recorded', early.status === 0 && earlyBody.new === true && earlyBody.details, early.stdout);
const seeded = fixture();
run(seeded.home, ['liveness', '--at', String(Date.now())]);
const held = run(seeded.home, ['watchdog']);
assert('watchdog does not fire before 48 hours', held.status === 0 && held.stdout.trim() === '{"new":false}', held.stdout);
const old = fixture();
run(old.home, ['liveness', '--at', String(Date.now() - (48 * 60 * 60 * 1000) - 1000)]);
const late = run(old.home, ['watchdog']);
assert('watchdog fires after 48 hours', late.status === 0 && json(late).new === true, late.stdout);
assert('watchdog works with the consolidation turn absent', late.stderr.includes('prepare') === false, late.stderr);

const prepared = fixture(`# Inbox\n${line}\n`);
const prep = run(prepared.home, ['prepare']);
const prepBody = prep.status === 0 ? json(prep) : null;
const lock = path.join(prepared.root, '.rbtv/runtime/ignite/memory.lock');
assert('prepare persists snapshot and holds no lock', prep.status === 0 && prepBody.run && fs.existsSync(store.runFile(prepared.home, prepBody.run)) && !fs.existsSync(lock), prep.stderr);

function proposalFile(home, body) {
  const file = path.join(home, 'proposal.json');
  write(file, JSON.stringify(body));
  return file;
}

const facts = `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# facts\n\n${line}\n`;
const filing = {
  operations: [
    {
      op: 'supersede', path: '.rbtv/memory/inbox.md', reason: 'file', explanation: 'file the owner line',
      sources: [line], text: '# Inbox\n',
      removals: [{ text: line, to: '.rbtv/memory/knowledge/facts.md', replacement: line }],
    },
    {
      op: 'add', path: '.rbtv/memory/knowledge/facts.md', reason: 'file', explanation: 'file the owner line',
      sources: [line], text: facts, removals: [],
    },
  ],
  conflicts: [],
};

function publishBox() {
  const box = fixture(`# Inbox\n${line}\n`);
  const made = run(box.home, ['prepare']);
  if (made.status !== 0) return { box, made, applied: made };
  const file = proposalFile(box.home, filing);
  const applied = run(box.home, ['apply', '--run', json(made).run, '--proposal', file]);
  return { box, made, applied, runId: json(made).run };
}

const published = publishBox();
const head = published.applied.status === 0 ? git(published.box.root, ['log', '-1', '--format=%B']) : '';
const cursor = published.applied.status === 0 ? store.readCursors(published.box.home) : {};
assert('apply publishes and the commit names the run and covered positions', published.applied.status === 0 && head.includes(published.runId) && head.includes('covered') && cursor['inbox:albert'], `${published.applied.stderr}\n${head}`);

const beforeCursor = fixture(`# Inbox\n${line}\n`);
const beforePrep = run(beforeCursor.home, ['prepare']);
const crash = run(beforeCursor.home, ['apply', '--run', json(beforePrep).run, '--proposal', proposalFile(beforeCursor.home, filing)], { ALBERT_FAULT: 'after-commit' });
const crashedCursor = store.readCursors(beforeCursor.home);
const crashedHead = git(beforeCursor.box ? beforeCursor.root : beforeCursor.root, ['log', '-1', '--format=%B']);
assert('cursor advances only after the commit', crash.status !== 0 && !crashedCursor['inbox:albert'] && crashedHead.includes(json(beforePrep).run), crash.stderr + crashedHead);
const retried = run(beforeCursor.home, ['apply', '--run', json(beforePrep).run, '--proposal', proposalFile(beforeCursor.home, filing)]);
const retriedCursor = store.readCursors(beforeCursor.home);
const retriedFacts = fs.readFileSync(path.join(beforeCursor.root, '.rbtv/memory/knowledge/facts.md'), 'utf8');
assert('recovery after commit completes bookkeeping without restoring old bytes', retried.status === 0 && retriedCursor['inbox:albert'] && retriedFacts.includes(line), retried.stderr);

const bad = fixture(`# Inbox\n${line}\n`);
const badPrep = run(bad.home, ['prepare']);
const badFile = proposalFile(bad.home, { operations: [{ op: 'nope' }], conflicts: [] });
const refused = run(bad.home, ['apply', '--run', json(badPrep).run, '--proposal', badFile]);
assert('invalid proposal advances nothing and retains bytes', refused.status !== 0 && refused.stderr.includes('requirement:') && !store.readCursors(bad.home)['inbox:albert'] && fs.readdirSync(store.diagnosticsDir(bad.home)).length > 0, refused.stderr);
const malformed = run(bad.home, ['apply', '--run', json(badPrep).run, '--proposal', proposalFile(bad.home, 'not-json')]);
assert('malformed response advances nothing and retains bytes', malformed.status !== 0 && !store.readCursors(bad.home)['inbox:albert'], malformed.stderr);

const stale = fixture(`# Inbox\n${line}\n`);
const stalePrep = run(stale.home, ['prepare']);
write(path.join(stale.root, '.rbtv/memory/inbox.md'), `# Inbox\n${line}\n- later (2026-10-02 · albert)\n`);
write(path.join(stale.home, '_artifacts/board.md'), board.replace('## What matters now\n', '## What matters now\n- concurrent board note\n'));
const staleApply = run(stale.home, ['apply', '--run', json(stalePrep).run, '--proposal', proposalFile(stale.home, filing)]);
const inboxNow = fs.readFileSync(path.join(stale.root, '.rbtv/memory/inbox.md'), 'utf8');
const boardNow = fs.readFileSync(path.join(stale.home, '_artifacts/board.md'), 'utf8');
assert('stale source refuses with fresh-prepare and overwrites nothing', staleApply.status !== 0 && /fresh prepare/.test(staleApply.stderr) && inboxNow.includes('later') && boardNow.includes('concurrent'), staleApply.stderr);
assert('concurrent remember and board write survive', inboxNow.includes('later') && boardNow.includes('concurrent'), '');

const quietRun = fixture();
const rows = [{ id: 7, author: 'owner', text: 'seen' }];
const contentHash = crypto.createHash('sha256').update(JSON.stringify(rows)).digest('hex');
write(path.join(store.evidenceDir(quietRun.home), 'batch.json'), JSON.stringify({
  sourceKind: 'conversation', sourceAgent: 'other', sourceCursor: 'messages', ceiling: 7, contentHash, rows,
}));
const quietPrep = run(quietRun.home, ['prepare']);
const headBefore = git(quietRun.root, ['rev-parse', 'HEAD']);
const noChange = run(quietRun.home, ['apply', '--run', json(quietPrep).run, '--proposal', proposalFile(quietRun.home, { operations: [], conflicts: [] })]);
const receipts = store.readReceipts(quietRun.home);
assert('no-change acknowledgement is durable before the cursor moves', noChange.status === 0 && receipts[0] && receipts[0].outcome === 'no-change' && git(quietRun.root, ['rev-parse', 'HEAD']) === headBefore && store.readCursors(quietRun.home)['conversation:other:messages'], noChange.stderr);
assert('repeated external reconciliation reads the same receipt', JSON.stringify(store.readReceipts(quietRun.home)) === JSON.stringify(receipts), '');

const crashAck = fixture();
write(path.join(store.evidenceDir(crashAck.home), 'batch.json'), JSON.stringify({
  sourceKind: 'conversation', sourceAgent: 'other', sourceCursor: 'messages', ceiling: 7, contentHash, rows,
}));
const crashPrep = run(crashAck.home, ['prepare']);
const mid = run(crashAck.home, ['apply', '--run', json(crashPrep).run, '--proposal', proposalFile(crashAck.home, { operations: [], conflicts: [] })], { ALBERT_FAULT: 'after-receipt' });
assert('receipt exists before cursor on a crash', mid.status !== 0 && store.readReceipts(crashAck.home).length === 1 && !store.readCursors(crashAck.home)['conversation:other:messages'], mid.stderr);
run(crashAck.home, ['apply', '--run', json(crashPrep).run, '--proposal', proposalFile(crashAck.home, { operations: [], conflicts: [] })]);
assert('retry after receipt advances the cursor once', store.readCursors(crashAck.home)['conversation:other:messages'] && store.readReceipts(crashAck.home).length === 1, '');

const interrupted = fixture(`# Inbox\n${line}\n`);
const intPrep = run(interrupted.home, ['prepare']);
const intCrash = run(interrupted.home, ['apply', '--run', json(intPrep).run, '--proposal', proposalFile(interrupted.home, filing)], { ALBERT_FAULT: 'during-write' });
const factsPath = path.join(interrupted.root, '.rbtv/memory/knowledge/facts.md');
write(factsPath, 'foreign bytes\n');
const recovered = run(interrupted.home, ['apply', '--run', json(intPrep).run, '--proposal', proposalFile(interrupted.home, filing)]);
const inboxAfter = fs.readFileSync(path.join(interrupted.root, '.rbtv/memory/inbox.md'), 'utf8');
assert('recovery restores matching files and reports later bytes', intCrash.status !== 0 && recovered.status !== 0 && /later bytes preserved/.test(recovered.stderr) && inboxAfter.startsWith('# Inbox') && fs.readFileSync(factsPath, 'utf8').includes('foreign'), `${intCrash.stderr}\n${recovered.stderr}`);

function helpText() {
  return spawnSync(process.execPath, [tool, 'apply', '-h'], { encoding: 'utf8' }).stdout;
}
const helpOut = helpText();
const libDir = path.resolve(__dirname, '../../../../../../capabilities/tools/memory/lib');
if (fs.existsSync(path.join(libDir, 'publish.js'))) {
  const missing = [];
  for (const name of ['publish.js', 'records.js', 'board.js']) {
    for (const rule of extractFile(fs.readFileSync(path.join(libDir, name), 'utf8'))) {
      if (keep(rule) && !helpOut.includes(rule)) missing.push(rule);
    }
  }
  assert('apply -h contains every extracted validator rule', missing.length === 0, missing.slice(0, 8).join(' | '));
}
assert('apply -h names every failure and does not stop at the first form error', helpOut.includes('every independent form error') && helpOut.includes('does not stop the operation checks') && helpOut.includes('<index> <op>') && !helpOut.includes('stops at the first form error'), helpOut);
assert('root help names every failure and does not stop at the first form error', rootHelp.includes('every independent form error') && rootHelp.includes('<index> <op>') && !rootHelp.includes('stops at the first form error'), rootHelp);
const promptPath = path.resolve(__dirname, '../../../../prompt.md');
if (fs.existsSync(promptPath)) {
  const prompt = fs.readFileSync(promptPath, 'utf8');
  assert('prompt routes to apply -h and does not restate op values', prompt.includes('apply -h') && !prompt.includes('supersede'), '');
}

const host = ['https://app.', 'sl', 'ack.com'].join('');
const thread = `${host}/archives/C0123ABCDEF/p1700000000000000`;
const oldFact = `- old fact (2026-01-01 · albert/[t](${thread}))`;
const newFact = `- new fact (2026-10-01 · albert/[t](${thread}))`;
const factFile = (bullet) => `---\ndescription: when reviewing facts\ntype: facts\naliases: [facts]\n---\n# facts\n\n${bullet}\n`;
function citedBox() {
  const box = fixture();
  write(path.join(box.root, '.rbtv/memory/knowledge/facts.md'), factFile(oldFact));
  git(box.root, ['add', '.']);
  git(box.root, ['commit', '-q', '-m', 'facts']);
  const evidence = [{ id: 1, author: 'owner', text: 'update the fact', thread, conversationKey: 'c1' }];
  const digest = crypto.createHash('sha256').update(JSON.stringify(evidence)).digest('hex');
  write(path.join(store.evidenceDir(box.home), 'batch.json'), JSON.stringify({
    sourceKind: 'conversation', sourceAgent: 'other', sourceCursor: 'messages', ceiling: 1, contentHash: digest, rows: evidence,
  }));
  const made = run(box.home, ['prepare']);
  const body = {
    operations: [{
      op: 'supersede', path: '.rbtv/memory/knowledge/facts.md', reason: 'owner', explanation: 'replace the fact',
      sources: [1], text: factFile(newFact), removals: [{ text: oldFact }],
    }],
    conflicts: [],
  };
  const applied = run(box.home, ['apply', '--run', json(made).run, '--proposal', proposalFile(box.home, body)]);
  return { box, applied, runId: json(made).run };
}
const first = citedBox();
const prefs = '---\ndescription: when reviewing preferences\ntype: preferences\naliases: [preferences]\n---\n# preferences\n\n- tea (2026-01-02 · albert)\n';
write(path.join(first.box.root, '.rbtv/memory/knowledge/preferences.md'), prefs);
git(first.box.root, ['add', '.']);
git(first.box.root, ['commit', '-q', '-m', 'unrelated later edit']);
store.appendReceipt(first.box.home, {
  id: 'later-edit', createdAt: Date.now() + 10, outcome: 'published', runId: 'later', commit: null, sources: [],
  items: [{ n: 1, ref: 'later#1', agent: 'albert', path: '.rbtv/memory/knowledge/preferences.md', before: null, after: prefs, sources: [], explanation: 'later' }],
});
const reversed = run(first.box.home, ['reverse', '--item', `${first.runId}#1`]);
let prefsAfter = '';
try { prefsAfter = fs.readFileSync(path.join(first.box.root, '.rbtv/memory/knowledge/preferences.md'), 'utf8'); } catch (error) { prefsAfter = error.code; }
let factsAfter = '';
try { factsAfter = fs.readFileSync(path.join(first.box.root, '.rbtv/memory/knowledge/facts.md'), 'utf8'); } catch (error) { factsAfter = error.code; }
assert('reverse of one item keeps an unrelated later edit', first.applied.status === 0 && reversed.status === 0 && prefsAfter === prefs && factsAfter.includes('old fact'), `${reversed.stderr}\n${prefsAfter}`);

const second = citedBox();
const laterFacts = factFile('- changed (2026-10-03 · albert)');
write(path.join(second.box.root, '.rbtv/memory/knowledge/facts.md'), laterFacts);
store.appendReceipt(second.box.home, {
  id: 'dependent-edit', createdAt: Date.now() + 20, outcome: 'published', runId: 'dep', commit: null, sources: [],
  items: [{ n: 1, ref: 'dep#1', agent: 'albert', path: '.rbtv/memory/knowledge/facts.md', before: factFile(newFact), after: laterFacts, sources: [], explanation: 'depends' }],
});
const blocked = run(second.box.home, ['reverse', '--item', `${second.runId}#1`]);
assert('reverse with a dependent later operation reports the dependency and changes nothing', second.applied.status === 0 && blocked.status !== 0 && /dependency/.test(blocked.stderr) && fs.readFileSync(path.join(second.box.root, '.rbtv/memory/knowledge/facts.md'), 'utf8') === laterFacts, `${second.applied.stderr}\n${blocked.stderr}`);

const reportBox = publishBox();
const listed = run(reportBox.box.home, ['report', '--occasion', 'week-a']);
const listedBody = listed.status === 0 ? json(listed) : null;
assert('report lists items and separates sections', listed.status === 0 && listedBody.items.length === 2 && listedBody.text.includes('Applied') && listedBody.text.includes('Pending global-rule approvals') && listedBody.text.includes('Unresolved conflicts') && listedBody.text.includes(`${reportBox.runId}#1`), listed.stderr);
const again = run(reportBox.box.home, ['report', '--occasion', 'week-a']);
assert('report retry reuses the frozen payload', again.stdout === listed.stdout, '');
run(reportBox.box.home, ['report-ack', '--occasion', 'week-a']);
const afterAck = run(reportBox.box.home, ['report', '--occasion', 'week-a']);
const ackBody = json(afterAck);
assert('report-ack prevents omission and repetition', ackBody.text === listedBody.text && ackBody.items.join() === listedBody.items.join() && fs.readdirSync(store.reportsDir(reportBox.box.home)).length === 1, afterAck.stdout);

const pending = fixture();
const pendingPrep = run(pending.home, ['prepare']);
const pendingProposal = { operations: [], conflicts: ['Pending global rule: always ask', 'name clash'] };
const pendingApply = run(pending.home, ['apply', '--run', json(pendingPrep).run, '--proposal', proposalFile(pending.home, pendingProposal)]);
const pendingReport = run(pending.home, ['report', '--occasion', 'week-c']);
const pendingBody = pendingApply.status === 0 ? json(pendingReport) : null;
assert('report separates approvals and conflicts', pendingBody && pendingBody.text.includes('Pending global rule: always ask') && pendingBody.text.includes('name clash'), pendingReport.stdout + pendingApply.stderr);

const occasion = fixture(`# Inbox\n${line}\n`);
const occPrep = run(occasion.home, ['prepare']);
run(occasion.home, ['apply', '--run', json(occPrep).run, '--proposal', proposalFile(occasion.home, filing)]);
const frozen = json(run(occasion.home, ['report', '--occasion', 'week-a']));
const migrated = {
  id: 'migrated-1', createdAt: Date.now(), outcome: 'migrated', runId: 'migrated', commit: null, sources: [],
  items: [{ n: 1, ref: 'migrated#1', agent: 'albert', path: '.rbtv/memory/profile.md', before: profile, after: profile, sources: ['migration'], explanation: 'migrated item' }],
};
store.appendReceipt(occasion.home, migrated);
const retryA = json(run(occasion.home, ['report', '--occasion', 'week-a']));
run(occasion.home, ['report-ack', '--occasion', 'week-a']);
const retryAck = json(run(occasion.home, ['report', '--occasion', 'week-a']));
const next = json(run(occasion.home, ['report', '--occasion', 'week-b']));
assert('frozen report A is stable before and after ack', frozen.text === retryA.text && retryA.text === retryAck.text && frozen.items.join() === retryAck.items.join(), '');
assert('later publication is covered once by the next occasion', next.items.filter((ref) => ref === 'migrated#1').length === 1 && !frozen.items.includes('migrated#1'), next.items.join(','));
assert('migration receipt is in the first owed report that can see it', next.text.includes('migrated#1') && next.text.includes('before:'), next.text.slice(0, 200));

const moved = { box: fixture() };
write(path.join(moved.box.root, '.rbtv/memory/knowledge/facts.md'), factFile(newFact));
git(moved.box.root, ['add', '.']);
git(moved.box.root, ['commit', '-q', '-m', 'current facts']);
write(path.join(moved.box.root, '.rbtv/memory/knowledge/preferences.md'), prefs);
git(moved.box.root, ['add', '.']);
git(moved.box.root, ['commit', '-q', '-m', 'later unrelated']);
store.appendReceipt(moved.box.home, {
  id: 'migrated-reverse', createdAt: 1, outcome: 'migrated', runId: 'migrated', commit: null, sources: [],
  items: [{
    n: 1, ref: 'migrated#1', agent: 'albert', path: '.rbtv/memory/knowledge/facts.md',
    before: factFile(oldFact), after: factFile(newFact), sources: [1],
    messages: [{ rowid: 1, text: 'update the fact', thread, conversation_key: 'c1' }],
    explanation: 'migrated',
  }],
});
store.appendReceipt(moved.box.home, {
  id: 'later-pref', createdAt: Date.now(), outcome: 'published', runId: 'later-pref', commit: null, sources: [],
  items: [{ n: 1, ref: 'later-pref#1', agent: 'albert', path: '.rbtv/memory/knowledge/preferences.md', before: null, after: prefs, sources: [], explanation: 'later' }],
});
const movedReverse = run(moved.box.home, ['reverse', '--item', 'migrated#1']);
  assert('migration reversal preserves a later unrelated edit', movedReverse.status === 0 && fs.readFileSync(path.join(moved.box.root, '.rbtv/memory/knowledge/preferences.md'), 'utf8') === prefs && fs.readFileSync(path.join(moved.box.root, '.rbtv/memory/knowledge/facts.md'), 'utf8').includes('old fact'), movedReverse.stderr);

const inboxBox = fixture('# Inbox\n');
const inboxBefore = `# Inbox\n${line}\n`;
store.appendReceipt(inboxBox.home, {
  id: 'inbox-item', createdAt: 1, outcome: 'published', runId: 'inbox-item', commit: null, sources: [],
  items: [{ n: 1, ref: 'inbox-item#1', agent: 'albert', path: '.rbtv/memory/inbox.md', before: inboxBefore, after: '# Inbox\n', sources: [line], explanation: 'filed' }],
});
const inboxReverse = run(inboxBox.home, ['reverse', '--item', 'inbox-item#1']);
assert('reverse of inbox consumption refuses and leaves the file', inboxReverse.status !== 0 && /consumed line/.test(inboxReverse.stderr) && inboxReverse.stderr.includes(`memory remember --installation ${inboxBox.root} --agent albert TEXT`) && fs.readFileSync(path.join(inboxBox.root, '.rbtv/memory/inbox.md'), 'utf8') === '# Inbox\n', inboxReverse.stderr);

function failureBlock(stderr, reason) {
  return stderr.split(/\n(?=failure )/).find((part) => part.includes(`reason: ${reason}`));
}
const judged = fixture();
const judgedRows = [{ id: 9, author: 'owner', text: 'keep the topic', thread, conversationKey: 'c9' }];
const judgedHash = crypto.createHash('sha256').update(JSON.stringify(judgedRows)).digest('hex');
write(path.join(store.evidenceDir(judged.home), 'batch.json'), JSON.stringify({
  sourceKind: 'conversation', sourceAgent: 'other', sourceCursor: 'messages', ceiling: 9, contentHash: judgedHash, rows: judgedRows,
}));
const judgedPrep = run(judged.home, ['prepare']);
const judgedAlpha = '.rbtv/agents/albert/memory/alpha.md';
const judgedBeta = '.rbtv/agents/albert/memory/beta.md';
const judgedOutside = 'notes/outside.md';
const judgedHead = git(judged.root, ['rev-parse', 'HEAD']);
const judgedCursors = JSON.stringify(store.readCursors(judged.home));
const judgedBad = run(judged.home, ['apply', '--run', json(judgedPrep).run, '--proposal', proposalFile(judged.home, {
  operations: [
    { op: 'add', path: judgedOutside, text: 'outside shape-token-not-for-alert', sources: [], reason: 'owner', explanation: 'because' },
    {
      op: 'add', path: judgedAlpha, sources: [], reason: 'owner', explanation: 'because',
      text: '---\ndescription: when reviewing alpha\ntype: subject\n---\n# Alpha\n\nThreads: none\n- undated shape-token-not-for-alert\n',
    },
    {
      op: 'add', path: judgedBeta, sources: [], reason: 'owner', explanation: 'because',
      text: '---\ndescription: when reviewing beta\ntype: subject\naliases: [beta]\n---\n# Beta\n\n- a fact (2026-10-13 · albert)\n',
    },
  ],
  conflicts: [{ path: 'shape-token-not-for-alert', text: 'shape-token-not-for-alert', sources: [], explanation: 'shape-token-not-for-alert' }],
})]);
const conflictBlock = failureBlock(judgedBad.stderr, 'invalid conflict');
const outsideBlock = failureBlock(judgedBad.stderr, 'path outside agent memory or repeated operation');
const aliasBlock = failureBlock(judgedBad.stderr, 'topic aliases required');
const datedBlock = failureBlock(judgedBad.stderr, 'records require dated provenance');
const threadsBlock = failureBlock(judgedBad.stderr, 'subject topics require Threads');
assert('apply names the conflict, the outside add, both form errors and the missing Threads line', judgedBad.status === 1 && conflictBlock && conflictBlock.includes('path: (proposal)') && conflictBlock.includes('operation: (proposal)') && outsideBlock && outsideBlock.includes(`path: ${judgedOutside}`) && outsideBlock.includes('operation: 0 add') && aliasBlock && aliasBlock.includes(`path: ${judgedAlpha}`) && aliasBlock.includes('operation: 1 add') && datedBlock && datedBlock.includes(`path: ${judgedAlpha}`) && datedBlock.includes('operation: 1 add') && threadsBlock && threadsBlock.includes(`path: ${judgedBeta}`) && threadsBlock.includes('operation: 2 add') && git(judged.root, ['rev-parse', 'HEAD']) === judgedHead && JSON.stringify(store.readCursors(judged.home)) === judgedCursors && !fs.existsSync(path.join(judged.root, judgedAlpha)), judgedBad.stderr);
const cited = `- kept fact (2026-10-13 · albert/[t](${thread}))`;
function subjectFile(name, fact) {
  return `---\ndescription: when reviewing ${name}\ntype: subject\naliases: [${name}]\n---\n# ${name}\n\nThreads: none\n${fact}\n`;
}
const judgedFixed = run(judged.home, ['apply', '--run', json(judgedPrep).run, '--proposal', proposalFile(judged.home, {
  operations: [
    { op: 'add', path: judgedAlpha, sources: [9], reason: 'owner', explanation: 'because', text: subjectFile('alpha', cited) },
    { op: 'add', path: judgedBeta, sources: [9], reason: 'owner', explanation: 'because', text: subjectFile('beta', cited) },
  ],
  conflicts: [],
})]);
assert('corrected proposal applies on the same prepared run', judgedFixed.status === 0 && json(judgedFixed).run === json(judgedPrep).run && fs.readFileSync(path.join(judged.root, judgedAlpha), 'utf8').includes('kept fact') && fs.readFileSync(path.join(judged.root, judgedBeta), 'utf8').includes('Threads: none'), judgedFixed.stderr);

const deviceThread = `${host}/archives/C0TEST00001/p1791000000000001`;
const otherThread = `${host}/archives/C0TEST00002/p1791000000000002`;
const entityPath = '.rbtv/memory/entities/devices/handheld-1001.md';
const entityText = `---\ndescription: when identifying the handheld by its name\ntype: device\naliases: [handheld-1001]\n---\n# Handheld-1001\n\n- The handheld is named Handheld-1001. (2026-10-13 · albert/${deviceThread})\n`;
const otherEntity = '.rbtv/memory/entities/devices/other-2002.md';
const otherEntityText = `---\ndescription: when reviewing the other device\ntype: device\naliases: [other-2002]\n---\n# Other-2002\n\n- Other stays. (2026-10-01 · albert)\n`;
const deviceIndex = '.rbtv/memory/entities/_artifacts/index.md';
const deviceRow = '| [Handheld-1001](../devices/handheld-1001.md) | when identifying the handheld |';
const otherDeviceRow = '| [Other](../devices/other-2002.md) | when reviewing the other record |';
const deviceIndexText = `# Index\n\n| Open | When |\n|---|---|\n${otherDeviceRow}\n${deviceRow}\n`;
const deviceDay = '.rbtv/memory/timeline/daily/2026-10-13.md';
const deviceEpisode = `- Named the handheld. — albert/[thread](${deviceThread})`;
const keptEpisode = `- Kept episode. — albert/[thread](${otherThread})`;
const deviceDayText = `---\ndescription: when asked what happened on 2026-10-13\n---\n# 2026-10-13\n\n${keptEpisode}\n${deviceEpisode}\n`;
const forgetLine = '- Owner asks to forget: handheld-1001. Owner said: drop it (2026-10-13 · albert)';
const archivePath = '.rbtv/memory/_artifacts/archive/handheld-1001.md';

function commitTree(root) {
  git(root, ['add', '.']);
  git(root, ['commit', '-q', '-m', 'records']);
}

function plantDevice(box, inbox) {
  if (inbox != null) write(path.join(box.root, '.rbtv/memory/inbox.md'), inbox);
  write(path.join(box.root, entityPath), entityText);
  write(path.join(box.root, otherEntity), otherEntityText);
  write(path.join(box.root, deviceIndex), deviceIndexText);
  write(path.join(box.root, deviceDay), deviceDayText);
  commitTree(box.root);
  return box;
}

function createdReceipt(home) {
  store.appendReceipt(home, {
    id: 'add-run', createdAt: 1, outcome: 'published', runId: 'add-run', commit: null, sources: [],
    items: [
      { n: 1, ref: 'add-run#1', agent: 'albert', path: entityPath, before: null, after: entityText, sources: [], explanation: 'created' },
      { n: 4, ref: 'add-run#4', agent: 'albert', path: deviceIndex, before: deviceIndexText.replace(`${deviceRow}\n`, ''), after: deviceIndexText, sources: [], explanation: 'index row' },
      { n: 7, ref: 'add-run#7', agent: 'albert', path: deviceDay, before: deviceDayText.replace(`${deviceEpisode}\n`, ''), after: deviceDayText, sources: [], explanation: 'timeline line' },
    ],
  });
}

const created = plantDevice(fixture());
createdReceipt(created.home);
const createdReverse = run(created.home, ['reverse', '--item', 'add-run#1']);
const createdArchive = createdReverse.status === 0 ? fs.readFileSync(path.join(created.root, archivePath), 'utf8') : '';
const createdIndex = createdReverse.status === 0 ? fs.readFileSync(path.join(created.root, deviceIndex), 'utf8') : '';
const createdDay = createdReverse.status === 0 ? fs.readFileSync(path.join(created.root, deviceDay), 'utf8') : '';
const createdReceipts = store.readReceipts(created.home);
const createdLeave = createdReceipts.flatMap((row) => row.items || []).find((row) => row.leave && row.path === entityPath);
assert('reverse of a created record archives it and drops only its index row and timeline line', createdReverse.status === 0 && !fs.existsSync(path.join(created.root, entityPath)) && createdArchive.includes(entityText) && createdArchive.includes('Reason: reversed') && createdArchive.includes('Source: add-run#1') && createdIndex === deviceIndexText.replace(`${deviceRow}\n`, '') && createdDay === deviceDayText.replace(`${deviceEpisode}\n`, '') && fs.readFileSync(path.join(created.root, otherEntity), 'utf8') === otherEntityText && createdLeave && createdLeave.after == null, createdReverse.stderr);
const createdReport = createdReverse.status === 0 ? json(run(created.home, ['report', '--occasion', 'week-reverse'])) : null;
assert('weekly report lists an archived removal and a reversal', createdReport && createdReport.text.includes(createdLeave.ref) && createdReport.text.includes('archived removal') && createdReport.text.includes('reversal'), createdReport && createdReport.text);

const round = createdLeave ? run(created.home, ['reverse', '--item', createdLeave.ref]) : { status: 1, stderr: 'no leave item' };
const roundArchive = round.status === 0 ? fs.readFileSync(path.join(created.root, archivePath), 'utf8') : '';
assert('reverse of a reversal restores the record, the index row and the timeline line', round.status === 0 && fs.readFileSync(path.join(created.root, entityPath), 'utf8') === entityText && fs.readFileSync(path.join(created.root, deviceIndex), 'utf8') === deviceIndexText && fs.readFileSync(path.join(created.root, deviceDay), 'utf8') === deviceDayText && roundArchive.includes('# Restored') && roundArchive.includes(entityText), round.stderr);

const mismatched = plantDevice(fixture());
createdReceipt(mismatched.home);
write(path.join(mismatched.root, deviceIndex), deviceIndexText.replace(`${deviceRow}\n`, ''));
const mismatchReverse = run(mismatched.home, ['reverse', '--item', 'add-run#1']);
assert('reverse refuses when the same-run index row is gone and changes nothing', mismatchReverse.status !== 0 && /do not match add-run#1 uniquely/.test(mismatchReverse.stderr) && fs.readFileSync(path.join(mismatched.root, entityPath), 'utf8') === entityText, mismatchReverse.stderr);

const dependent = plantDevice(fixture());
createdReceipt(dependent.home);
store.appendReceipt(dependent.home, {
  id: 'later-index', createdAt: Date.now(), outcome: 'published', runId: 'later-index', commit: null, sources: [],
  items: [{ n: 1, ref: 'later-index#1', agent: 'albert', path: deviceIndex, before: deviceIndexText, after: deviceIndexText, sources: [], explanation: 'later index' }],
});
const dependentReverse = run(dependent.home, ['reverse', '--item', 'add-run#1']);
assert('reverse refuses when a later receipt touched the index and changes nothing', dependentReverse.status !== 0 && /dependency: later-index#1/.test(dependentReverse.stderr) && fs.readFileSync(path.join(dependent.root, entityPath), 'utf8') === entityText && fs.readFileSync(path.join(dependent.root, deviceIndex), 'utf8') === deviceIndexText, dependentReverse.stderr);

const indexOnly = plantDevice(fixture());
createdReceipt(indexOnly.home);
const indexReverse = run(indexOnly.home, ['reverse', '--item', 'add-run#4']);
assert('reverse of an index item on its own tells the caller to reverse the record', indexReverse.status !== 0 && /reverse the record item instead/.test(indexReverse.stderr) && fs.readFileSync(path.join(indexOnly.root, deviceIndex), 'utf8') === deviceIndexText, indexReverse.stderr);

const appended = fixture();
const appendedBefore = factFile(oldFact);
const appendedAfter = factFile(`${oldFact}\n${newFact}`);
write(path.join(appended.root, '.rbtv/memory/knowledge/facts.md'), appendedAfter);
commitTree(appended.root);
store.appendReceipt(appended.home, {
  id: 'append-run', createdAt: 1, outcome: 'published', runId: 'append-run', commit: null, sources: [],
  items: [{ n: 1, ref: 'append-run#1', agent: 'albert', path: '.rbtv/memory/knowledge/facts.md', before: appendedBefore, after: appendedAfter, sources: [], explanation: 'appended' }],
});
const appendReverse = run(appended.home, ['reverse', '--item', 'append-run#1']);
assert('reverse of an append-only change names the replacement requirement and changes nothing', appendReverse.status !== 0 && /no mechanical inverse for append-run#1: replacement needs owner evidence and a replacement record/.test(appendReverse.stderr) && fs.readFileSync(path.join(appended.root, '.rbtv/memory/knowledge/facts.md'), 'utf8') === appendedAfter, appendReverse.stderr);

const folded = fixture();
const foldedBefore = '## What matters now\n\n## Watch-outs\n\n- stale claim (2026-10-01 · albert)\n\n## Timers\n\n## Recently closed\n';
const foldedAfter = board;
write(path.join(folded.home, '_artifacts/board.md'), foldedAfter);
store.appendReceipt(folded.home, {
  id: 'fold-run', createdAt: 1, outcome: 'published', runId: 'fold-run', commit: null, sources: [],
  items: [{ n: 1, ref: 'fold-run#1', agent: 'albert', path: '.rbtv/agents/albert/_artifacts/board.md', before: foldedBefore, after: foldedAfter, sources: [], explanation: 'folded' }],
});
const foldReverse = run(folded.home, ['reverse', '--item', 'fold-run#1']);
assert('reverse of a board fold names the board requirement and changes nothing', foldReverse.status !== 0 && /no mechanical inverse for fold-run#1: dreamer cannot create or close subjects or edit runtime board fields/.test(foldReverse.stderr) && fs.readFileSync(path.join(folded.home, '_artifacts/board.md'), 'utf8') === foldedAfter, foldReverse.stderr);

const topicPath = '.rbtv/agents/albert/memory/alpha.md';
const topicText = `---\ndescription: when reviewing alpha\ntype: subject\naliases: [alpha]\n---\n# alpha\n\nThreads: none\n- a kept fact (2026-10-13 · albert/[t](${thread}))\n`;
const topicBox = fixture();
write(path.join(topicBox.root, topicPath), topicText);
commitTree(topicBox.root);
store.appendReceipt(topicBox.home, {
  id: 'topic-run', createdAt: 1, outcome: 'published', runId: 'topic-run', commit: null, sources: [],
  items: [{ n: 1, ref: 'topic-run#1', agent: 'albert', path: topicPath, before: null, after: topicText, sources: [], explanation: 'created topic' }],
});
const topicReverse = run(topicBox.home, ['reverse', '--item', 'topic-run#1']);
assert('reverse of a created topic file archives it', topicReverse.status === 0 && !fs.existsSync(path.join(topicBox.root, topicPath)) && fs.readFileSync(path.join(topicBox.root, '.rbtv/memory/_artifacts/archive/alpha.md'), 'utf8').includes(topicText), topicReverse.stderr);

function forgetProposal(fault) {
  const reasonBullet = `- Reason: owner asked to forget. Source: ${forgetLine} (2026-10-13 · albert)`;
  const archiveText = `---\ndescription: when reviewing an archived record\ntype: reference\naliases: [archived]\n---\n# Archived\n\n${reasonBullet}\n\n\`\`\`verbatim\n${entityText}\`\`\`\n`;
  const record = entityText.trim().split('\n').at(-1);
  const operations = [
    { op: 'archive', path: entityPath, leave: true, text: fault === 'text' ? entityText.replace('identifying', 'naming') : entityText, sources: fault === 'source' ? [] : [forgetLine], reason: 'owner', explanation: 'owner asked to forget', item: fault === 'source' ? '' : undefined, removals: [{ text: record, to: archivePath }] },
    { op: 'add', path: archivePath, text: fault === 'source' ? archiveText.replace('owner asked to forget', 'unspecified') : archiveText, sources: fault === 'source' ? [] : [forgetLine], reason: 'owner', explanation: 'owner asked to forget', removals: [] },
    { op: 'supersede', path: deviceIndex, reason: 'index', text: deviceIndexText.replace(`${deviceRow}\n`, ''), sources: fault === 'source' ? [] : [forgetLine], explanation: 'drop the index row', removals: [{ text: deviceRow }] },
    { op: 'supersede', path: deviceDay, text: fault === 'pointer' ? deviceDayText.replace(`${keptEpisode}\n`, '') : deviceDayText.replace(`${deviceEpisode}\n`, ''), sources: fault === 'source' ? [] : [forgetLine], reason: 'owner', explanation: 'drop the episode', removals: [{ text: fault === 'pointer' ? keptEpisode : deviceEpisode }] },
  ];
  if (fault === 'archive') operations.splice(1, 1);
  if (fault === 'index') operations.splice(2, 1);
  if (fault === 'stays') return { operations: [operations[2]], conflicts: [] };
  return { operations, conflicts: [] };
}

const forgetBox = plantDevice(fixture(`# Inbox\n\n${forgetLine}\n`));
const forgetPrep = run(forgetBox.home, ['prepare']);
const forgetRun = forgetPrep.status === 0 ? json(forgetPrep).run : '';
const faultNames = {
  archive: 'removal without an archive entry',
  stays: 'index or timeline line dropped while the record it points at stays',
  pointer: 'dropped line does not point at the archived record',
  source: 'removal needs a stated reason and a source',
  index: 'index link points at a missing memory file',
  text: 'leave keeps the verbatim file text',
};
for (const [fault, reason] of Object.entries(faultNames)) {
  const refused = run(forgetBox.home, ['apply', '--run', forgetRun, '--proposal', proposalFile(forgetBox.home, forgetProposal(fault))]);
  assert(`forget proposal fault ${fault} is refused by name`, refused.status !== 0 && refused.stderr.includes(`reason: ${reason}`) && fs.existsSync(path.join(forgetBox.root, entityPath)), `${reason}\n${refused.stderr}`);
}
const forgetApply = run(forgetBox.home, ['apply', '--run', forgetRun, '--proposal', proposalFile(forgetBox.home, forgetProposal())]);
const forgetReceipt = store.readReceipts(forgetBox.home).find((row) => row.outcome === 'published');
const forgetLeave = forgetReceipt && forgetReceipt.items.find((row) => row.leave && row.path === entityPath);
const forgetCheck = run(forgetBox.home, ['check']);
assert('forget proposal archives the record, drops its lines and consumes the inbox line', forgetApply.status === 0 && forgetReceipt && !fs.existsSync(path.join(forgetBox.root, entityPath)) && fs.readFileSync(path.join(forgetBox.root, archivePath), 'utf8').includes(entityText) && fs.readFileSync(path.join(forgetBox.root, deviceIndex), 'utf8') === deviceIndexText.replace(`${deviceRow}\n`, '') && fs.readFileSync(path.join(forgetBox.root, deviceDay), 'utf8') === deviceDayText.replace(`${deviceEpisode}\n`, '') && forgetReceipt.sources.some((row) => (row.positions || []).includes(forgetLine)) && forgetCheck.status === 0 && forgetCheck.stdout.trim() === '{"new":false}', `${forgetApply.stderr}\n${forgetCheck.stdout}${forgetCheck.stderr}`);
const forgetRound = forgetLeave ? run(forgetBox.home, ['reverse', '--item', forgetLeave.ref]) : { status: 1, stderr: 'no leave item' };
assert('reverse of a forget restores the record', forgetRound.status === 0 && fs.readFileSync(path.join(forgetBox.root, entityPath), 'utf8') === entityText && fs.readFileSync(path.join(forgetBox.root, archivePath), 'utf8').includes('# Restored'), forgetRound.stderr);
const forgetReport = json(run(forgetBox.home, ['report', '--occasion', 'week-forget']));
assert('weekly report lists the forget and its reversal', Boolean(forgetLeave) && forgetReport.text.includes(forgetLeave.ref) && forgetReport.text.includes('archived removal') && forgetReport.text.includes('reversal'), forgetReport.text.slice(0, 400));

const promptForget = fs.readFileSync(promptPath, 'utf8');
assert('prompt says an owner forget is an archived removal and does not restate the proposal', promptForget.includes('archived removal') && promptForget.includes('unresolved conflict') && promptForget.includes('consumed by the same proposal') && !promptForget.includes('leave: true') && !promptForget.includes('Reason: owner asked to forget'), '');
const reverseHelp = spawnSync(process.execPath, [tool, 'reverse', '-h'], { encoding: 'utf8' }).stdout;
assert('reverse -h states the dangling-index rule', reverseHelp.includes('only the index rows whose link target is that record') && reverseHelp.includes('reverse the record item instead') && helpOut.includes('leave: true') && helpOut.includes('Reason: owner asked to forget') && helpOut.includes('# Restored'), reverseHelp);
assert('apply -h states any inbox line, the fifth operation and the timeline rule', helpOut.includes('Any agent\'s line counts') && helpOut.includes('5. supersede .rbtv/memory/inbox.md') && helpOut.includes('The publisher deletes those lines.') && helpOut.includes('A line this same proposal removes from inbox.md does not stay. The archive does not count.') && !helpOut.includes('does not delete the inbox line') && !helpOut.includes('this agent\'s exact inbox line'), helpOut);
assert('reverse -h states capture consumption and does not restore inbox lines', reverseHelp.includes('If the capture line is still in the inbox') && reverseHelp.includes('does not put consumed inbox lines back') && reverseHelp.includes('The archive does not count.'), reverseHelp);

const pebble = 'Pebble-441';
const pebbleUrl = `${host}/archives/C0123ABCDEF/p1700000000000001`;
const pebbleKept = `${host}/archives/C0123ABCDEF/p1700000000000002`;
const pebblePath = '.rbtv/memory/entities/devices/pebble-441.md';
const pebbleText = `---\ndescription: when identifying the device ${pebble}\ntype: device\naliases: [${pebble}]\n---\n# ${pebble}\n\n- The device is named ${pebble}. (2026-10-13 · albert/[owner thread](${pebbleUrl}))\n`;
const pebbleIndexPath = '.rbtv/memory/entities/_artifacts/index.md';
const pebbleRow = `| [${pebble}](../devices/pebble-441.md) | when identifying the device |`;
const pebbleKeptRow = '| [Kept](../devices/kept-device.md) | when reviewing the kept device |';
const pebbleIndexText = `# Entities\n\n| Open | When |\n|---|---|\n${pebbleKeptRow}\n${pebbleRow}\n`;
const pebbleDayPath = '.rbtv/memory/timeline/daily/2026-10-13.md';
const pebbleEpisode = `- Named the device ${pebble}. — albert/[owner thread](${pebbleUrl})`;
const pebbleKeptEpisode = `- Kept episode. — albert/[owner thread](${pebbleKept})`;
const pebbleDayText = `---\ndescription: when recalling owner requests on this day\ntype: reference\naliases: [day]\n---\n# 2026-10-13\n\n${pebbleKeptEpisode}\n${pebbleEpisode}\n`;
const pebbleCapture = `- Owner asks to remember the device name ${pebble}. (2026-10-13 · pal/[owner thread](${pebbleUrl}))`;
const pebbleRequest = `- Owner asks to forget: device ${pebble}. Owner said: forget it (2026-10-13 · pal)`;
const pebbleArchive = '.rbtv/memory/_artifacts/archive/pebble-441.md';
const pebbleInbox = `# Inbox\n${pebbleCapture}\n${pebbleRequest}\n`;
const pebbleKeptEntity = '.rbtv/memory/entities/devices/kept-device.md';
const pebbleKeptText = `---\ndescription: when reviewing the kept device\ntype: device\naliases: [kept]\n---\n# Kept\n\n- Stays. (2026-10-01 · albert)\n`;

function plantPebble(box) {
  write(path.join(box.root, '.rbtv/memory/inbox.md'), pebbleInbox);
  write(path.join(box.root, pebblePath), pebbleText);
  write(path.join(box.root, pebbleKeptEntity), pebbleKeptText);
  write(path.join(box.root, pebbleIndexPath), pebbleIndexText);
  write(path.join(box.root, pebbleDayPath), pebbleDayText);
  commitTree(box.root);
  return box;
}

function pebbleReceipt(home) {
  store.appendReceipt(home, {
    id: 'pebble-add', createdAt: 1, outcome: 'published', runId: 'pebble-add', commit: null, sources: [],
    items: [
      { n: 1, ref: 'pebble-add#1', agent: 'albert', path: pebblePath, before: null, after: pebbleText, sources: [], explanation: 'created' },
      { n: 4, ref: 'pebble-add#4', agent: 'albert', path: pebbleIndexPath, before: pebbleIndexText.replace(`${pebbleRow}\n`, ''), after: pebbleIndexText, sources: [], explanation: 'index row' },
      { n: 7, ref: 'pebble-add#7', agent: 'albert', path: pebbleDayPath, before: pebbleDayText.replace(`${pebbleEpisode}\n`, ''), after: pebbleDayText, sources: [], explanation: 'timeline line' },
    ],
  });
}

const sharedReverse = plantPebble(fixture());
pebbleReceipt(sharedReverse.home);
const keptBefore = {
  profile: fs.readFileSync(path.join(sharedReverse.root, '.rbtv/memory/profile.md'), 'utf8'),
  board: fs.readFileSync(path.join(sharedReverse.home, '_artifacts/board.md'), 'utf8'),
  kept: fs.readFileSync(path.join(sharedReverse.root, pebbleKeptEntity), 'utf8'),
};
const sharedResult = run(sharedReverse.home, ['reverse', '--item', 'pebble-add#1']);
const sharedArchive = sharedResult.status === 0 ? fs.readFileSync(path.join(sharedReverse.root, pebbleArchive), 'utf8') : '';
const sharedInbox = sharedResult.status === 0 ? fs.readFileSync(path.join(sharedReverse.root, '.rbtv/memory/inbox.md'), 'utf8') : '';
assert('reverse of a created record drops the timeline line and consumes a capture still in the inbox', sharedResult.status === 0 && !fs.existsSync(path.join(sharedReverse.root, pebblePath)) && sharedArchive.includes(pebbleText) && sharedArchive.includes('Reason: reversed. Source: pebble-add#1') && sharedArchive.includes(pebbleCapture) && fs.readFileSync(path.join(sharedReverse.root, pebbleIndexPath), 'utf8') === pebbleIndexText.replace(`${pebbleRow}\n`, '') && fs.readFileSync(path.join(sharedReverse.root, pebbleDayPath), 'utf8') === pebbleDayText.replace(`${pebbleEpisode}\n`, '') && !sharedInbox.includes(pebbleCapture) && sharedInbox.includes(pebbleRequest) && fs.readFileSync(path.join(sharedReverse.root, '.rbtv/memory/profile.md'), 'utf8') === keptBefore.profile && fs.readFileSync(path.join(sharedReverse.home, '_artifacts/board.md'), 'utf8') === keptBefore.board && fs.readFileSync(path.join(sharedReverse.root, pebbleKeptEntity), 'utf8') === keptBefore.kept, sharedResult.stderr);
const sharedReport = sharedResult.status === 0 ? json(run(sharedReverse.home, ['report', '--occasion', 'week-shared-reverse'])) : null;
const sharedLeave = store.readReceipts(sharedReverse.home).flatMap((row) => row.items || []).find((row) => row.leave && row.path === pebblePath);

function pebbleForgetProposal() {
  const record = pebbleText.trim().split('\n').at(-1);
  const bullets = [pebbleRequest, pebbleCapture].map((line) => `- Reason: owner asked to forget. Source: ${line} (2026-10-13 · albert)`).join('\n');
  const archiveText = `---\ndescription: when reviewing an archived record\ntype: reference\naliases: [archived]\n---\n# Archived\n\n${bullets}\n\n\`\`\`verbatim\n${pebbleText}\`\`\`\n`;
  return {
    operations: [
      { op: 'archive', path: pebblePath, leave: true, text: pebbleText, sources: [pebbleRequest, pebbleCapture], reason: 'owner', explanation: 'owner asked to forget', removals: [{ text: record, to: pebbleArchive }] },
      { op: 'add', path: pebbleArchive, text: archiveText, sources: [pebbleRequest, pebbleCapture], reason: 'owner', explanation: 'owner asked to forget', removals: [] },
      { op: 'supersede', path: pebbleIndexPath, reason: 'index', text: pebbleIndexText.replace(`${pebbleRow}\n`, ''), sources: [pebbleRequest], explanation: 'drop the index row', removals: [{ text: pebbleRow }] },
      { op: 'supersede', path: pebbleDayPath, text: pebbleDayText.replace(`${pebbleEpisode}\n`, ''), sources: [pebbleRequest], reason: 'owner', explanation: 'drop the episode', removals: [{ text: pebbleEpisode }] },
      { op: 'supersede', path: '.rbtv/memory/inbox.md', reason: 'owner', text: '# Inbox\n', sources: [pebbleRequest, pebbleCapture], explanation: 'consume the inbox lines', removals: [{ text: pebbleCapture, to: pebbleArchive }, { text: pebbleRequest, to: pebbleArchive }] },
    ],
    conflicts: [],
  };
}

const sharedForget = plantPebble(fixture());
const palHome = path.join(sharedForget.root, '.rbtv', 'agents', 'pal');
write(path.join(palHome, 'memory/learned.md'), '# Learned rules — pal\n');
write(path.join(palHome, '_artifacts/board.md'), board);
const sharedPrep = run(sharedForget.home, ['prepare']);
const sharedRun = sharedPrep.status === 0 ? json(sharedPrep).run : '';
const sharedApply = run(sharedForget.home, ['apply', '--run', sharedRun, '--proposal', proposalFile(sharedForget.home, pebbleForgetProposal())]);
const sharedForgetReceipt = store.readReceipts(sharedForget.home).find((row) => row.outcome === 'published');
const sharedForgetLeave = sharedForgetReceipt && sharedForgetReceipt.items.find((row) => row.leave && row.path === pebblePath);
const sharedCheck = run(sharedForget.home, ['check']);
const deliveredLib = require('./lib/library.js').loadLibrary();
const delivered = sharedApply.status === 0 ? deliveredLib.prepareMemory({ installation: sharedForget.root, agentHome: palHome }) : { bundle: [] };
const deliveredText = delivered.bundle.map((row) => row.text).join('\n');
assert('forget proposal of the help shape leaves nothing in delivered memory', sharedApply.status === 0 && sharedForgetReceipt && !fs.existsSync(path.join(sharedForget.root, pebblePath)) && !deliveredText.includes(pebble) && !deliveredText.includes('Owner asks to forget') && sharedCheck.status === 0 && !sharedCheck.stdout.includes('inbox'), `${sharedApply.stderr}\n${sharedCheck.stdout}${deliveredText.slice(0, 400)}`);
const sharedForgetRound = sharedForgetLeave ? run(sharedForget.home, ['reverse', '--item', sharedForgetLeave.ref]) : { status: 1, stderr: 'no leave item' };
const sharedForgetInbox = sharedForgetRound.status === 0 ? fs.readFileSync(path.join(sharedForget.root, '.rbtv/memory/inbox.md'), 'utf8') : '';
const sharedForgetArchive = sharedForgetRound.status === 0 ? fs.readFileSync(path.join(sharedForget.root, pebbleArchive), 'utf8') : '';
assert('reverse of a forget restores the record and does not put inbox lines back', sharedForgetRound.status === 0 && fs.readFileSync(path.join(sharedForget.root, pebblePath), 'utf8') === pebbleText && fs.readFileSync(path.join(sharedForget.root, pebbleIndexPath), 'utf8') === pebbleIndexText && fs.readFileSync(path.join(sharedForget.root, pebbleDayPath), 'utf8') === pebbleDayText && sharedForgetArchive.includes('# Restored') && !sharedForgetInbox.includes(pebbleCapture) && !sharedForgetInbox.includes(pebbleRequest), sharedForgetRound.stderr);
const sharedForgetReport = json(run(sharedForget.home, ['report', '--occasion', 'week-shared-forget']));
assert('weekly report lists the created-record reverse, the forget and the forget reversal', Boolean(sharedLeave) && sharedReport && sharedReport.text.includes(sharedLeave.ref) && sharedReport.text.includes('archived removal') && Boolean(sharedForgetLeave) && sharedForgetReport.text.includes(sharedForgetLeave.ref) && sharedForgetReport.text.includes('archived removal') && sharedForgetReport.text.includes('reversal'), `${sharedReport && sharedReport.text}\n${sharedForgetReport.text}`.slice(0, 500));

const pair = fixture();
const { spawn } = require('node:child_process');
const env = { ...process.env, RBTV_AGENT_HOME: pair.home };
let waiting = 2;
const outs = [];
function finishPair() {
  assert('concurrent requests for one occasion keep one payload', outs.length === 2 && outs[0] === outs[1] && fs.readdirSync(store.reportsDir(pair.home)).length === 1, outs.join('\n'));
  if (failed) process.exit(1);
  process.stdout.write('PASS suite\n');
}
for (let n = 0; n < 2; n += 1) {
  const child = spawn(process.execPath, [tool, 'report', '--occasion', 'week-z'], { cwd: pair.home, env });
  let out = '';
  child.stdout.on('data', (chunk) => { out += chunk; });
  child.on('close', () => {
    outs.push(out);
    waiting -= 1;
    if (!waiting) finishPair();
  });
}
