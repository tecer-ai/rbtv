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
