#!/usr/bin/env node
'use strict';

// Migrates existing memory notes into an installation from an explicit manifest.
// dry-run prints the plan; apply publishes it after the whole manifest is checked;
// rollback undoes only what apply wrote. It never writes to a source or a loader.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib/index.js');
const { failure, refusalError } = require('./lib/failures.js');

const ALBERT = path.join(__dirname, '..', '..', '..', 'agents', 'albert', 'rbtv', 'capabilities', 'tools', 'albert', 'lib');
const DISPOSITIONS = ['migrated', 'merged-duplicate', 'timeline', 'pending-global-approval', 'retained-unmapped', 'off-machine-pending', 'rejected-with-reason'];
const KINDS = ['fact', 'agent lesson', 'task', 'operational request'];
const SCOPES = ['personal', 'workspace', 'global'];
const TIMELINE = /^\.rbtv\/memory\/timeline\/daily\/[^/]+\.md$/;
const sha = (data) => crypto.createHash('sha256').update(data).digest('hex');
const lines = (text) => text.split('\n');
const keeps = (verdict) => verdict?.futureAnswerEffect === true && verdict.usefulAfterThirtyDays === true && verdict.owner === 'owner';
const durable = (record) => keeps(record.verdict);

function migrationDir(installation) { return path.join(installation, '.rbtv', 'runtime', 'migration'); }
function ledgerFile(installation) { return path.join(migrationDir(installation), 'ledger.json'); }
function readLedger(installation) {
  try { return JSON.parse(fs.readFileSync(ledgerFile(installation), 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return { stopped: false, entries: [], destinations: {} }; throw error; }
}
function writeLedger(installation, ledger) {
  fs.mkdirSync(migrationDir(installation), { recursive: true });
  fs.writeFileSync(ledgerFile(installation), `${JSON.stringify(ledger, null, 2)}\n`, 'utf8');
}
function readText(installation, relative) {
  try { return fs.readFileSync(lib.safePath(installation, relative), 'utf8'); }
  catch (error) { if (error.code === 'ENOENT') return null; throw error; }
}

// One plan: every failure the manifest has, plus the destination texts it would write.
function plan(installation, manifest, { resume = false } = {}) {
  const failures = [];
  const bad = (row, requirement, expected, extra = {}) => failures.push(failure({
    path: extra.path ?? row?.source ?? null, operation: extra.operation ?? row?.disposition ?? 'manifest',
    requirement, expected, reason: `${row ? `row ${row.id}: ` : ''}${requirement}`,
  }));
  const ledger = readLedger(installation);
  const rows = Array.isArray(manifest?.rows) ? manifest.rows : [];
  if (!Array.isArray(manifest?.rows)) bad(null, 'manifest has no rows array', 'a JSON object with a rows array', { path: null });
  if (ledger.stopped && !resume) bad(null, 'migration was stopped by a rollback', 'apply --resume after the rollback is understood', { path: null, operation: 'apply' });
  const texts = new Map();
  const warnings = [];
  const steps = [];
  const mapped = new Set(rows.map((row) => row.source));
  const unmapped = (manifest?.inventory || []).filter((source) => !mapped.has(source));
  const ids = new Set();
  for (const row of rows) {
    if (typeof row.id !== 'string' || !row.id || ids.has(row.id)) bad(row, 'row id missing or repeated', 'a unique string id');
    ids.add(row.id);
    if (!DISPOSITIONS.includes(row.disposition)) { bad(row, 'unknown disposition', DISPOSITIONS.join(', ')); continue; }
    if (row.original !== 'keep') bad(row, 'verbatim original not kept', 'original: "keep"');
    // A harness wrote an agent's notes; a workspace file (a document or transcript) has none.
    if (!(row.origin?.agent ? row.origin.harness : row.origin?.workspace)) bad(row, 'origin missing', 'origin with harness and agent, or workspace');
    if (['rejected-with-reason', 'retained-unmapped'].includes(row.disposition) && !String(row.reason || '').trim()) bad(row, 'reason missing', 'a reason');
    const offMachine = row.disposition === 'off-machine-pending';
    let source = null;
    if (!offMachine) {
      try { source = fs.readFileSync(row.source); } catch { bad(row, 'source unreadable', 'a readable source file'); continue; }
      if (sha(source) !== row.hash) { bad(row, 'stale source: hash differs from the manifest', `hash ${row.hash}; the source now hashes ${sha(source)}; re-inspect it`); continue; }
    }
    const prior = ledger.entries.filter((entry) => entry.source === row.source && !entry.rolledBack);
    const same = prior.find((entry) => entry.hash === (row.hash ?? null) && entry.rowId === row.id);
    const changed = prior.filter((entry) => entry.hash !== (row.hash ?? null));
    if (!same && changed.length && !changed.some((entry) => entry.rowId === row.earlier)) {
      bad(row, 'changed source needs a row linked to its earlier row', `earlier: ${changed.at(-1).rowId}`);
      continue;
    }
    if (same) { steps.push({ row, state: 'already-imported' }); continue; }
    const step = { row, state: 'new', writes: [], pending: [] };
    steps.push(step);
    if (row.disposition === 'merged-duplicate') {
      const present = readText(installation, row.duplicateOf?.path || '') ?? '';
      if (!row.duplicateOf || !lines(present).includes(row.duplicateOf.text)) bad(row, 'duplicate not found at its destination', 'duplicateOf.path containing duplicateOf.text as a line');
    }
    const records = row.records || [];
    if (['migrated', 'timeline', 'pending-global-approval'].includes(row.disposition) && !records.length) bad(row, 'no record subrows', 'at least one record');
    const sourceLines = source ? lines(source.toString('utf8')) : [];
    for (const [index, record] of records.entries()) {
      const where = `${row.source}#record${index + 1}`;
      const rbad = (requirement, expected, operation = record.kind) => bad(row, `record ${index + 1}: ${requirement}`, expected, { path: where, operation });
      const [from, to] = record.span || [];
      if (!KINDS.includes(record.kind) || !SCOPES.includes(record.scope)) { rbad('kind or scope unknown', `kind ${KINDS.join('|')}; scope ${SCOPES.join('|')}`); continue; }
      if (!Number.isInteger(from) || !Number.isInteger(to) || from < 1 || to < from || to > sourceLines.length) rbad('source span outside the source', 'span [first, last] inside the source lines');
      if (typeof record.text !== 'string' || !record.text.trim() || record.text.includes('\n')) { rbad('record text must be one line', 'one line of destination text'); continue; }
      if (record.scope === 'global' || row.disposition === 'pending-global-approval') {
        if (record.scope !== 'global' || row.disposition !== 'pending-global-approval') rbad('global scope and pending-global-approval go together', 'scope global with disposition pending-global-approval');
        else if (record.destination) rbad('a global rule is never written by migration', 'no destination until the owner approves');
        else step.pending.push(`Pending global rule: ${record.text}`);
        continue;
      }
      const route = durable(record);
      const dest = record.destination;
      const kind = typeof dest === 'string' ? lib.kindOf(dest, row.origin?.agent || '') : null;
      try { lib.safePath(installation, dest); } catch (error) { rbad(error.message, 'a path inside the installation memory'); continue; }
      if (!kind || dest === '.rbtv/memory/learned.md') { rbad('destination is not a memory file this agent or workspace owns', 'an agent memory, workspace, knowledge or timeline path'); continue; }
      if (route && TIMELINE.test(dest)) rbad('a record passing the keeping test cannot go to the timeline', 'a durable destination');
      if (!route && !TIMELINE.test(dest)) rbad('a record failing the keeping test goes to the timeline only', 'a timeline/daily destination');
      if (route && !['fact', 'agent lesson'].includes(record.kind)) rbad('only a fact or an agent lesson is kept as memory', 'kind fact or agent lesson');
      if (record.scope === 'personal' && !dest.startsWith(`.rbtv/agents/${row.origin?.agent}/`) && route) rbad('personal scope belongs in the source agent\'s memory', `.rbtv/agents/${row.origin?.agent}/memory/`);
      if (record.scope === 'workspace' && dest.startsWith('.rbtv/agents/')) rbad('workspace scope belongs in installation memory', '.rbtv/memory/');
      if (record.kind === 'agent lesson' && route && !['learned', 'workspace'].includes(kind)) rbad('a lesson goes to learned rules or its workspace', 'learned.md of the source agent, or a workspace file');
      if (record.kind === 'fact' && kind === 'learned') rbad('a fact is not a learned rule', 'a knowledge, topic, entity or workspace file');
      const current = texts.has(dest) ? texts.get(dest) : readText(installation, dest);
      // The manifest's cutover hash is the reference: the job computed it when it read the destination.
      // The ledger's hash is older (a previous job), and the consolidation edits destinations between jobs.
      const expected = manifest.cutover?.destinations?.[dest];
      if (!texts.has(dest) && expected !== undefined && (current == null ? null : sha(current)) !== expected) {
        rbad('destination changed after cutover', `destination hash ${expected}; it now is ${current == null ? 'absent' : sha(current)}`);
        continue;
      }
      if (expected === undefined && !texts.has(dest)) rbad('destination hash missing from cutover.destinations', 'cutover.destinations[path] = hash or null');
      if (current == null && !String(record.header || '').trim()) { rbad('destination is new and has no header', 'header: the file\'s frontmatter and heading'); continue; }
      const base = current ?? `${record.header.replace(/\n*$/, '\n')}`;
      if (lines(base).includes(record.text)) { rbad('destination already holds this record', 'merged-duplicate disposition'); continue; }
      const next = `${base.replace(/\n*$/, '\n')}${record.text}\n`;
      texts.set(dest, next);
      let write = step.writes.find((w) => w.path === dest);
      if (!write) step.writes.push(write = { path: dest, kind, created: current == null, header: current == null ? record.header : null, before: current, lines: [], spans: [] });
      write.lines.push(record.text);
      write.spans.push(`${row.source}#L${from}-${to}`);
      write.after = next;
    }
  }
  for (const [dest, text] of texts) {
    const kind = lib.kindOf(dest, steps.find((s) => s.writes?.some((w) => w.path === dest))?.row.origin?.agent || '');
    try { lib.checkFile(dest, kind, text); } catch (error) {
      failures.push(...(error.failures?.length ? error.failures : [failure({ path: dest, operation: kind, requirement: error.message, expected: `a valid ${kind} file`, reason: error.message })]));
      continue;
    }
    const limits = lib.checkLimits(kind, text);
    warnings.push(...limits.warnings);
    if (limits.hard) failures.push(failure({ path: dest, operation: kind, requirement: `${kind} cap exceeded`, expected: `at most ${limits.hard.cap} ${limits.hard.unit}`, reason: `${dest}: ${limits.hard.count}/${limits.hard.cap} ${limits.hard.unit}` }));
    if (limits.split) {
      const split = lib.splitOnDemand(text);
      failures.push(failure({ path: dest, operation: kind, requirement: 'on-demand file would reach the split limit', expected: 'a manifest destination that keeps it under 300 lines', reason: `${dest}: ${split?.parts ? `${split.parts.moved.length} records would move to a second file` : 'one record is too large to split'}` }));
    }
  }
  return { failures, steps, texts, unmapped, warnings, ledger };
}

function describe(result) {
  return {
    ok: !result.failures.length,
    rows: result.steps.map(({ row, state, writes = [], pending = [] }) => ({
      id: row.id, source: row.source, disposition: row.disposition, state,
      destinations: writes.map((w) => w.path), pendingGlobal: pending,
    })),
    unmapped: result.unmapped,
    offMachinePending: result.steps.filter((s) => s.row.disposition === 'off-machine-pending').map((s) => s.row.source),
    warnings: result.warnings,
    complete: !result.failures.length && !result.unmapped.length && !result.steps.some((s) => s.row.disposition === 'off-machine-pending'),
  };
}

function commit(installation, paths, message) {
  lib.git(installation, ['add', '--', ...paths]);
  lib.git(installation, ['commit', '-F', '-', '--', ...paths], `${message}\n\n${paths.join('\n')}\n`);
  return lib.git(installation, ['rev-parse', 'HEAD']).stdout.trim();
}

function albertHome(installation, options) { return options.albertHome || path.join(installation, '.rbtv', 'agents', 'albert'); }

function apply(installation, manifest, options) {
  const release = lib.acquireMemoryLock(installation);
  try {
    const result = plan(installation, manifest, options);
    if (result.failures.length) throw refusalError(result.failures);
    const store = require(path.join(ALBERT, 'store.js'));
    const { noteConflicts } = require(path.join(ALBERT, 'report.js'));
    const home = albertHome(installation, options);
    const ledger = result.ledger;
    ledger.stopped = false;
    const fresh = result.steps.filter((s) => s.state === 'new');
    const written = [];
    for (const dest of result.texts.keys()) {
      lib.writeText(lib.safePath(installation, dest), result.texts.get(dest));
      written.push(dest);
    }
    const hash = written.length ? commit(installation, written, 'Migrate memory notes') : null;
    for (const { row, writes, pending } of fresh) {
      const runId = `migrated-${sha(`${row.source}|${row.hash}|${row.id}`).slice(0, 16)}`;
      let original = null;
      if (row.disposition !== 'off-machine-pending') {
        original = path.join(migrationDir(installation), 'originals', row.hash, path.basename(row.source));
        fs.mkdirSync(path.dirname(original), { recursive: true });
        fs.copyFileSync(row.source, original);
      }
      if (pending.length) noteConflicts(home, pending);
      const entry = { rowId: row.id, source: row.source, hash: row.hash || null, earlier: row.earlier || null, disposition: row.disposition, original, runId, commit: hash, writes, pending, reporting: 'owed' };
      ledger.entries.push(entry);
      for (const w of writes) ledger.destinations[w.path] = sha(w.after);
      if (writes.length) {
        store.appendReceipt(home, {
          id: runId, createdAt: Date.now(), outcome: 'migrated', runId, commit: hash,
          sources: [{ source: row.source, sourceKind: 'migration', sourceAgent: row.origin.agent || null, sourceCursor: `${row.source}@${row.hash}`, ceiling: null, positions: writes.flatMap((w) => w.spans) }],
          items: writes.map((w, n) => ({
            n: n + 1, ref: `${runId}#${n + 1}`, agent: row.origin.agent || 'migration', path: w.path,
            before: w.before, after: w.after, sources: w.spans, explanation: `migrated from ${path.basename(row.source)}`,
          })),
        });
      }
    }
    writeLedger(installation, ledger);
    return { ...describe(result), commit: hash };
  } finally { release(); }
}

function rollback(installation, manifest, options) {
  const release = lib.acquireMemoryLock(installation);
  try {
    const ledger = readLedger(installation);
    ledger.stopped = true;
    writeLedger(installation, ledger);
    const ids = new Set((manifest.rows || []).map((row) => row.id));
    const store = require(path.join(ALBERT, 'store.js'));
    const conflicts = [];
    const restored = [];
    const touched = [];
    const items = [];
    for (const entry of ledger.entries.filter((e) => ids.has(e.rowId) && !e.rolledBack).reverse()) {
      let clean = true;
      for (const w of entry.writes) {
        const current = readText(installation, w.path);
        const present = current == null ? [] : lines(current);
        const missing = w.lines.filter((line) => present.filter((have) => have === line).length !== 1);
        if (missing.length) {
          clean = false;
          conflicts.push({ path: w.path, rowId: entry.rowId, reason: 'a record this migration wrote was changed or removed after cutover; nothing was overwritten', records: missing });
          continue;
        }
        const next = lines(current).filter((line) => !w.lines.includes(line)).join('\n');
        const empty = w.created && next.trim() === w.header.trim();
        if (!empty) {
          try { lib.checkFile(w.path, lib.kindOf(w.path, agentOf(manifest, entry.rowId)), next); }
          catch (error) { clean = false; conflicts.push({ path: w.path, rowId: entry.rowId, reason: `restored text would be refused: ${error.message}`, records: [] }); continue; }
          lib.writeText(lib.safePath(installation, w.path), next);
        } else fs.unlinkSync(lib.safePath(installation, w.path));
        if (empty) delete ledger.destinations[w.path];
        else ledger.destinations[w.path] = sha(next);
        touched.push(w.path);
        restored.push({ path: w.path, rowId: entry.rowId, removed: w.lines.length, deleted: empty });
        items.push({ entry, w, after: empty ? null : next });
      }
      if (clean) entry.rolledBack = true;
    }
    const unique = [...new Set(touched)];
    const hash = unique.length ? commit(installation, unique, 'Roll back memory migration') : null;
    if (hash) {
      const runId = `migration-rollback-${hash.slice(0, 12)}`;
      store.appendReceipt(albertHome(installation, options), {
        id: runId, createdAt: Date.now(), outcome: 'published', runId, commit: hash, sources: [],
        items: items.map(({ entry, w, after }, n) => ({ n: n + 1, ref: `${runId}#${n + 1}`, agent: 'migration', path: w.path, before: w.after, after, sources: [entry.runId], explanation: `rollback of ${entry.rowId}` })),
      });
    }
    writeLedger(installation, ledger);
    return { ok: !conflicts.length, restored, conflicts, commit: hash, pendingGlobalLeft: ledger.entries.filter((e) => ids.has(e.rowId) && e.pending?.length).flatMap((e) => e.pending) };
  } finally { release(); }
}

function agentOf(manifest, rowId) { return (manifest.rows || []).find((row) => row.id === rowId)?.origin?.agent || ''; }

const HELP = `Imports memory from existing files (documents, transcripts, old agent notes) through a manifest:
each record cites its source file, hash and line span, and is checked before anything is written.

usage: memory migrate dry-run|apply|rollback --installation PATH --manifest FILE [--albert-home PATH] [--resume] [--json]
(node migrate.js takes the same arguments)

dry-run   check the whole manifest and print the plan; writes nothing.
apply     publish the checked plan; an unchanged source is imported once; a changed source needs a row whose "earlier" names its earlier row.
rollback  stop, then remove only the records apply wrote; a record changed since is reported as a conflict and left.
--resume  apply again after a rollback stopped migration.

Manifest: {"version":1,"cutover":{"destinations":{"<path>":"<sha256 or null>"}},"inventory":["<source>"],"rows":[{
  "id","source","origin":{"harness","agent"}|{"workspace"},"hash","mtime","disposition","reason","earlier","original":"keep","duplicateOf":{"path","text"},
  "records":[{"span":[first,last],"kind":"fact|agent lesson|task|operational request","scope":"personal|workspace|global",
  "verdict":{"futureAnswerEffect","usefulAfterThirtyDays","owner":"owner|task"},"destination","header","text"}]}]}
Dispositions: ${DISPOSITIONS.join(', ')}.
Exit 0 success; 1 refusal (every failure is printed); 2 usage.`;

function main(argv) {
  const [verb, ...rest] = argv;
  if (!verb || verb === '-h' || verb === '--help' || rest.includes('-h') || rest.includes('--help')) { process.stdout.write(`${HELP}\n`); return verb ? 0 : 2; }
  const options = {};
  const flags = { '--installation': 'installation', '--manifest': 'manifest', '--albert-home': 'albertHome' };
  for (let i = 0; i < rest.length; i++) {
    if (flags[rest[i]]) options[flags[rest[i]]] = rest[++i];
    else if (rest[i] === '--resume') options.resume = true;
    else if (rest[i] === '--json') options.json = true;
    else { process.stderr.write(`unknown argument ${rest[i]}\n`); return 2; }
  }
  if (!['dry-run', 'apply', 'rollback'].includes(verb) || !options.installation || !options.manifest) {
    process.stderr.write('usage: memory migrate dry-run|apply|rollback --installation PATH --manifest FILE\nmemory migrate -h\n');
    return 2;
  }
  const installation = path.resolve(options.installation);
  try {
    const manifest = JSON.parse(fs.readFileSync(options.manifest, 'utf8'));
    let result;
    if (verb === 'dry-run') {
      const planned = plan(installation, manifest);
      if (planned.failures.length) throw refusalError(planned.failures);
      result = describe(planned);
    } else result = (verb === 'apply' ? apply : rollback)(installation, manifest, options);
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return result.ok === false ? 1 : 0;
  } catch (error) {
    if (!error.failures?.length) { process.stderr.write(`${error.message}\n`); return 1; }
    if (options.json) process.stdout.write(`${JSON.stringify(error.failures, null, 2)}\n`);
    for (const f of error.failures) process.stderr.write(`${f.reason} [${f.path ?? '-'} | ${f.operation ?? '-'}] expected: ${f.expected}\n`);
    return 1;
  }
}

if (require.main === module) process.exitCode = main(process.argv.slice(2));

module.exports = { main, plan, apply, rollback, describe };
