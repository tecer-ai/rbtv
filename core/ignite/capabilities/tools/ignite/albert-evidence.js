#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const { loadConfig, updateConfig, agentHome, storePath, ignitePaths } = require('./config.js');
const { Store, conversationKey } = require('./store.js');
const { cadenceSpec, nextOccurrence, FIXED_TZ } = require('./schedule.js');
const { workspaceFromHome } = require('./memory.js');

const RULE_ID = 'core/ignite#albert-memory-operations';
const FENCE_NAME = 'albert-fence.json';
const PUBLISHER_NAME = 'publisher.json';
const CURSOR_NAME = 'ignite-cursors.json';
const APPLIED_NAME = 'ignite-applied-receipts.json';
const ZONE = 'America/Sao_Paulo';
const CHECKS = {
  nightly: 'runtime/ignite/checks/albert-evidence.js',
  watchdog: 'runtime/ignite/checks/albert-watchdog.js',
  friday: 'runtime/ignite/checks/albert-friday.js',
};
const SCHEDULES = [
  { id: 'albert-nightly', cron: '0 3 * * *', tz: ZONE, note: 'nightly memory check', check: CHECKS.nightly },
  { id: 'albert-watchdog', every: '1h', note: 'memory watchdog', check: CHECKS.watchdog },
  { id: 'albert-friday', cron: '45 8 * * 5', tz: ZONE, note: 'Friday memory report', check: CHECKS.friday },
];

function adapterFile() {
  return path.resolve(__dirname, 'albert-evidence.js');
}

function legacyCursor(store) {
  const raw = store.db.prepare("SELECT value FROM settings WHERE key='dreamer'").get()?.value;
  const state = raw ? JSON.parse(raw) : { cursor: 0, lastSuccessAt: null, commit: null };
  if (!(Number.isSafeInteger(state.cursor) && state.cursor >= 0)) throw new Error('invalid dreamer cursor');
  if (!(state.reportedConflicts == null || (Array.isArray(state.reportedConflicts) &&
    state.reportedConflicts.every((line) => typeof line === 'string')))) {
    throw new Error('invalid reported conflicts');
  }
  return state;
}

function fenceFile(workspace) {
  return path.join(workspace, '.rbtv', 'runtime', 'ignite', FENCE_NAME);
}

function publisherFile(workspace) {
  return path.join(workspace, '.rbtv', 'runtime', 'ignite', PUBLISHER_NAME);
}

function legacyFenced(workspace) {
  return fs.existsSync(fenceFile(workspace));
}

function readJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch (error) {
    if (error.code === 'ENOENT') return fallback;
    throw error;
  }
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`);
  fs.renameSync(tmp, file);
}

function albertHome(env = process.env) {
  const home = env.RBTV_AGENT_HOME || process.cwd();
  if (!home) throw new Error('RBTV_AGENT_HOME is required');
  return path.resolve(home);
}

function installationOf(home) {
  const root = workspaceFromHome(home);
  if (!root) throw new Error('RBTV_AGENT_HOME is not an installed agent folder');
  return root;
}

function albertScript(home) {
  if (process.env.ALBERT_TOOL) return process.env.ALBERT_TOOL;
  return path.join(home, 'rbtv', 'capabilities', 'tools', 'albert', 'albert.js');
}

function runAlbert(home, args, env = process.env) {
  const script = albertScript(home);
  if (!fs.existsSync(script)) throw new Error(`albert tool not found: ${script}`);
  const result = spawnSync(process.execPath, [script, ...args], {
    cwd: home,
    env: { ...env, RBTV_AGENT_HOME: home },
    encoding: 'utf8',
    maxBuffer: 10 * 1024 * 1024,
  });
  if (result.error) throw new Error(`albert failed to start: ${result.error.message}`);
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || 'albert failed').trim();
    throw new Error(detail);
  }
  return result.stdout;
}

function parseAlbert(stdout) {
  const body = JSON.parse(stdout);
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw new Error('albert returned no JSON object');
  return body;
}

function ownerRows(store, slug, cursor, ceiling) {
  return store.db.prepare(`SELECT m.rowid AS rowid, m.text, m.metadata, m.conversation_key,
    m.created_at, c.channel, c.root_ts FROM messages m JOIN conversations c ON c.key=m.conversation_key
    WHERE m.role='owner' AND c.agent=? AND m.rowid>? AND m.rowid<=? ORDER BY m.rowid`).all(slug, cursor, ceiling)
    .filter((row) => {
      const meta = JSON.parse(row.metadata);
      return !meta.source || ['slack', 'used-text'].includes(meta.source);
    }).map(({ metadata, ...row }) => ({ ...row,
      thread: row.root_ts && /^\d+\.\d+$/.test(row.root_ts) ? `https://app.slack.com/archives/${row.channel}/p${row.root_ts.replace('.', '')}` : null }));
}

function sourceSlugs(config) {
  return [...new Set([config.dmAgent, ...Object.values(config.routes || {})].filter(Boolean))].sort();
}

function openSource(config, slug, opened) {
  const db = storePath(config, slug);
  if (!fs.existsSync(db)) throw new Error(`source store missing for ${slug}: ${db}`);
  const store = new Store(storePath(config, slug));
  opened.push(store);
  return store;
}

function cursorFile(home) {
  return path.join(home, 'runtime', 'albert', CURSOR_NAME);
}

function appliedFile(home) {
  return path.join(home, 'runtime', 'albert', APPLIED_NAME);
}

function readCursors(home) {
  return readJson(cursorFile(home), {});
}

function sourceCursor(cursors, slug) {
  const row = cursors[slug];
  const cursor = row == null ? 0 : Number(row.cursor);
  if (!Number.isSafeInteger(cursor) || cursor < 0) throw new Error(`invalid ignite cursor for ${slug}`);
  return cursor;
}

function evidenceDir(home) {
  return path.join(home, 'runtime', 'albert', 'evidence');
}

function hashRows(rows) {
  return crypto.createHash('sha256').update(JSON.stringify(rows)).digest('hex');
}

function batchRows(rows) {
  return rows.map((row) => ({
    id: row.rowid,
    author: 'owner',
    text: row.text,
    thread: row.thread,
    conversationKey: row.conversation_key,
  }));
}

function writeBatch(home, batch) {
  const dir = evidenceDir(home);
  fs.mkdirSync(dir, { recursive: true });
  const name = `ignite-${batch.sourceAgent}-${batch.sourceCursor}-${batch.ceiling}.json`;
  const file = path.join(dir, name);
  const text = `${JSON.stringify(batch)}\n`;
  if (fs.existsSync(file) && fs.readFileSync(file, 'utf8') === text) return file;
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, text);
  fs.renameSync(tmp, file);
  return file;
}

function readReceipts(home) {
  const dir = path.join(home, 'runtime', 'albert', 'receipts');
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((name) => name.endsWith('.json')).sort()
    .map((name) => readJson(path.join(dir, name), null)).filter(Boolean);
}

function samePositions(rows, positions) {
  const left = rows.map((row) => row.rowid).sort((a, b) => a - b);
  const right = positions.map(Number).sort((a, b) => a - b);
  return left.length === right.length && left.every((id, index) => id === right[index]);
}

function coveredAlready(cursor, source) {
  const ceiling = Number(source.ceiling);
  return Number.isSafeInteger(ceiling) && cursor >= ceiling
    && (source.positions || []).every((id) => Number(id) <= cursor);
}

function reconcile(home, config, deps = {}) {
  const receipts = readReceipts(home);
  const applied = new Set(readJson(appliedFile(home), { ids: [] }).ids);
  const cursors = readCursors(home);
  const opened = [];
  let advanced = false;
  try {
    for (const receipt of receipts) {
      if (applied.has(receipt.id)) continue;
      if (receipt.outcome !== 'published' && receipt.outcome !== 'no-change') continue;
      let ready = true;
      const next = { ...cursors };
      for (const source of receipt.sources || []) {
        if (source.sourceKind !== 'ignite') continue;
        const slug = source.sourceAgent;
        if (!slug) { ready = false; break; }
        const cursor = sourceCursor(next, slug);
        if (coveredAlready(cursor, source)) continue;
        const ceiling = Number(source.ceiling);
        if (!Number.isSafeInteger(ceiling) || ceiling < cursor) { ready = false; break; }
        const store = deps.store || openSource(config, slug, opened);
        const rows = ownerRows(store, slug, cursor, ceiling);
        if (!samePositions(rows, source.positions || [])) { ready = false; break; }
        next[slug] = {
          cursor: ceiling,
          ceiling,
          positions: (source.positions || []).map(Number),
          receipt: receipt.id,
        };
      }
      if (!ready) continue;
      Object.assign(cursors, next);
      applied.add(receipt.id);
      advanced = true;
    }
    if (advanced) {
      writeJson(cursorFile(home), cursors);
      writeJson(appliedFile(home), { ids: [...applied].sort() });
    }
    return { cursors, advanced };
  } finally {
    if (!deps.store) for (const store of opened) store.close();
  }
}

function refreshEvidence(home, config, deps = {}) {
  const cursors = readCursors(home);
  const opened = [];
  const batches = [];
  try {
    for (const slug of sourceSlugs(config)) {
      const store = deps.store || openSource(config, slug, opened);
      const cursor = sourceCursor(cursors, slug);
      const ceiling = store.db.prepare('SELECT COALESCE(MAX(rowid),0) AS ceiling FROM messages').get().ceiling;
      if (!Number.isSafeInteger(ceiling) || ceiling < cursor) throw new Error(`message rowid moved behind cursor for ${slug}`);
      const rows = ownerRows(store, slug, cursor, ceiling);
      if (!rows.length) continue;
      const packed = batchRows(rows);
      const batch = {
        sourceKind: 'ignite',
        sourceAgent: slug,
        sourceCursor: String(cursor),
        ceiling,
        contentHash: hashRows(packed),
        rows: packed,
      };
      batches.push(writeBatch(home, batch));
    }
    return { batches, cursors };
  } finally {
    if (!deps.store) for (const store of opened) store.close();
  }
}

function fault(point) {
  if (process.env.ALBERT_EVIDENCE_FAULT === point) {
    const error = new Error(`fault ${point}`);
    error.code = 'fault';
    throw error;
  }
}

function saoPauloDate(now = Date.now()) {
  return new Intl.DateTimeFormat('en-CA', { timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(now));
}

function albertStore(home) {
  const db = ignitePaths(home).database;
  if (!fs.existsSync(db)) throw new Error(`albert store missing: ${db}`);
  return new Store(ignitePaths(home).database);
}

function scheduleConversation(store, id) {
  const schedule = store.getSchedule(id);
  if (!schedule) throw new Error(`schedule ${id} is not bound`);
  const conv = store.getConversation(schedule.conversation_key);
  if (!conv) throw new Error(`schedule ${id} has no conversation`);
  return { schedule, conv };
}

function queueReport(home, opts = {}) {
  const occasion = opts.occasion || process.env.ALBERT_OCCASION || saoPauloDate(opts.now);
  const body = parseAlbert(runAlbert(home, ['report', '--occasion', occasion], opts.env));
  if (!body.identity || !body.occasion) throw new Error('report returned no identity');
  const store = opts.store || albertStore(home);
  const owned = !opts.store;
  try {
    const { conv } = scheduleConversation(store, 'albert-friday');
    store.transaction(() => {
      const existing = store.db.prepare('SELECT id, client_msg_id FROM outbox WHERE client_msg_id=?').get(body.identity);
      if (!existing) {
        store.enqueueOutbox({
          id: `albert-report:${body.identity}`,
          conversationKey: conv.key,
          payload: { text: body.text, audio: false, files: [] },
          clientMsgId: body.identity,
        });
      }
    });
    fault('after-queue');
    parseAlbert(runAlbert(home, ['report-ack', '--occasion', body.occasion], opts.env));
    fault('after-ack');
    return body;
  } finally {
    if (owned) store.close();
  }
}

function watchdogNotice(home, body, opts = {}) {
  const store = opts.store || albertStore(home);
  const owned = !opts.store;
  try {
    const { conv } = scheduleConversation(store, 'albert-watchdog');
    const since = body.details && body.details.lastSuccessAt != null ? body.details.lastSuccessAt : 'none';
    store.beginProactive({
      id: `watchdog:${since}`,
      agent: conv.agent,
      workspace: conv.workspace,
      channel: conv.channel,
      payload: {
        text: 'Memory watchdog: no successful check or apply within 48 hours.',
        audio: false,
        files: [],
      },
      clientMsgId: `watchdog:${since}`,
    });
  } finally {
    if (owned) store.close();
  }
}

function runCheck(home, opts = {}) {
  const installation = opts.installation || installationOf(home);
  const config = opts.config || loadConfig(installation);
  reconcile(home, config, opts);
  refreshEvidence(home, config, opts);
  const stdout = runAlbert(home, ['check'], opts.env);
  const body = parseAlbert(stdout);
  if (body.new !== false && !(body.new === true && body.details != null)) {
    throw new Error('albert check did not return {"new":false} or {"new":true,"details":…}');
  }
  return body;
}

function runWatchdog(home, opts = {}) {
  const body = parseAlbert(runAlbert(home, ['watchdog'], opts.env));
  if (body.new === true) watchdogNotice(home, body, opts);
  return { new: false };
}

function helpText() {
  return `albert-evidence — Ignite source adapter for Albert.

usage: node albert-evidence.js [check|report|watchdog|migrate|fence|drain|cleanup|probe|verify|recover]
Default operation is check. A timer spawns this file with no arguments.

check reconciles durable published or no-change receipts, reads source stores at the current ceiling, refreshes evidence batches, then runs albert check. A source-read or receipt error exits 1 and does not record liveness.
report asks albert report, queues one outbox row for that identity, then runs albert report-ack.
watchdog runs albert watchdog. When that tool reports new work, one notice is queued in Albert's channel and this process prints {"new":false} so no model turn starts.
The proposal structure is taught by albert apply -h. This adapter does not restate it.
`;
}

function emit(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function main(argv = process.argv.slice(2)) {
  const op = argv[0] || 'check';
  if (op === '-h' || op === '--help') {
    process.stdout.write(helpText());
    return 0;
  }
  const home = albertHome();
  if (op === 'check') {
    emit(runCheck(home));
    return 0;
  }
  if (op === 'report') {
    if (argv.includes('--dry-run')) {
      const occasion = process.env.ALBERT_OCCASION || saoPauloDate();
      const body = parseAlbert(runAlbert(home, ['report', '--occasion', occasion]));
      emit({ dryRun: true, occasion: body.occasion, identity: body.identity, items: body.items });
      return 0;
    }
    queueReport(home);
    emit({ new: false });
    return 0;
  }
  if (op === 'watchdog') {
    emit(runWatchdog(home));
    return 0;
  }
  const installation = installationOf(home);
  if (op === 'migrate') return migrateCommand(installation, home, argv.includes('--dry-run'));
  if (op === 'fence') return fenceCommand(installation);
  if (op === 'drain') return drainCommand(installation);
  if (op === 'cleanup') return cleanupCommand(installation);
  if (op === 'probe') return probeCommand(installation);
  if (op === 'verify') return verifyCommand(home);
  if (op === 'recover') return recoverCommand(installation, home);
  throw new Error(`unknown operation ${op}; run albert-evidence.js -h`);
}

function planOf(installation, home) {
  const config = loadConfig(installation);
  const lines = [];
  let latest = null;
  const conflicts = [];
  for (const slug of sourceSlugs(config)) {
    const db = storePath(config, slug);
    if (!fs.existsSync(db)) {
      lines.push(`missing ${slug}`);
      continue;
    }
    const store = new Store(storePath(config, slug));
    try {
      const state = legacyCursor(store);
      lines.push(`source ${slug} cursor=${state.cursor} lastSuccessAt=${state.lastSuccessAt ?? 'none'} conflicts=${(state.reportedConflicts || []).length}`);
      if (state.lastSuccessAt != null && (latest == null || state.lastSuccessAt > latest)) latest = state.lastSuccessAt;
      for (const line of state.reportedConflicts || []) conflicts.push(line);
      const pending = store.pendingOutbox().filter((row) => String(row.payload?.text || '').startsWith('Memory consolidation') || String(row.payload?.text || '').startsWith('Memory alert:'));
      for (const row of pending) lines.push(`pending ${slug} outbox ${row.id}`);
    } finally { store.close(); }
  }
  lines.push(`liveness ${latest ?? 'none'}`);
  lines.push(`conflicts ${conflicts.length}`);
  return { lines, latest, conflicts, config };
}

function migrateCommand(installation, home, dryRun) {
  const plan = planOf(installation, home);
  for (const line of plan.lines) process.stdout.write(`${line}\n`);
  if (dryRun) {
    process.stdout.write('dry-run writes: none\n');
    return 0;
  }
  const cursors = readCursors(home);
  for (const slug of sourceSlugs(plan.config)) {
    const db = storePath(plan.config, slug);
    if (!fs.existsSync(db)) continue;
    const store = new Store(storePath(plan.config, slug));
    try {
      const state = legacyCursor(store);
      if (cursors[slug] == null) cursors[slug] = { cursor: state.cursor, ceiling: state.cursor, positions: [], migrated: true };
    } finally { store.close(); }
  }
  writeJson(cursorFile(home), cursors);
  if (plan.conflicts.length) {
    const cryptoId = (text) => crypto.createHash('sha256').update(text).digest('hex').slice(0, 12);
    const items = [];
    const seen = new Set();
    for (const text of plan.conflicts) {
      const id = cryptoId(text);
      if (seen.has(id)) continue;
      seen.add(id);
      items.push({ id, text, kind: text.startsWith('Pending global rule:') ? 'approval' : 'conflict' });
    }
    writeJson(path.join(home, 'runtime', 'albert', 'conflicts.json'), { items });
  }
  if (plan.latest != null) parseAlbert(runAlbert(home, ['liveness', '--at', String(plan.latest)]));
  process.stdout.write('migrated\n');
  return 0;
}

function fenceCommand(installation) {
  writeJson(fenceFile(installation), { fencedAt: Date.now(), publisher: 'legacy' });
  writeJson(publisherFile(installation), { publisher: 'fenced' });
  process.stdout.write('fenced\n');
  return 0;
}

function lockHeld(installation) {
  const file = path.join(installation, '.rbtv', 'runtime', 'ignite', 'memory.lock');
  if (!fs.existsSync(file)) return false;
  let owner;
  try { owner = JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return true; }
  if (!owner?.pid) return true;
  try { process.kill(owner.pid, 0); return true; } catch { return false; }
}

function drainCommand(installation) {
  if (!legacyFenced(installation)) throw new Error('drain requires the legacy fence');
  if (lockHeld(installation)) throw new Error('publication lock is held; drain refused');
  process.stdout.write('drained\n');
  return 0;
}

function cleanupCommand(installation) {
  updateConfig(installation, (raw) => {
    delete raw.dreamer;
    return raw;
  });
  process.stdout.write('cleaned\n');
  return 0;
}

function probeCommand(installation) {
  const raw = JSON.parse(fs.readFileSync(path.join(installation, '.rbtv', 'config', 'ignite', 'config.json'), 'utf8'));
  const keys = raw.dreamer ? Object.keys(raw.dreamer) : [];
  if (keys.length) throw new Error(`dreamer keys present: ${keys.join(', ')}`);
  process.stdout.write('dreamer keys absent\n');
  return 0;
}

function verifyCommand(home) {
  const check = runCheck(home);
  process.stdout.write(`nightly ${JSON.stringify(check)}\n`);
  const watch = runWatchdog(home);
  process.stdout.write(`watchdog ${JSON.stringify(watch)}\n`);
  const occasion = process.env.ALBERT_OCCASION || saoPauloDate();
  const report = parseAlbert(runAlbert(home, ['report', '--occasion', occasion]));
  process.stdout.write(`report dry-run ${report.identity}\n`);
  return 0;
}

function recoverCommand(installation, home) {
  const store = fs.existsSync(ignitePaths(home).database) ? albertStore(home) : null;
  try {
    if (store) {
      for (const row of SCHEDULES) {
        const existing = store.getSchedule(row.id);
        if (existing) store.upsertSchedule({ ...existing, id: row.id, conversationKey: existing.conversation_key, cadence: existing.cadence, timezone: existing.timezone, enabled: false, checkTool: existing.check_tool });
      }
    }
  } finally {
    if (store) store.close();
  }
  fs.rmSync(fenceFile(installation), { force: true });
  writeJson(publisherFile(installation), { publisher: 'legacy' });
  process.stdout.write('recovered legacy\n');
  return 0;
}

function installChecks(home) {
  const dir = path.join(home, 'runtime', 'ignite', 'checks');
  fs.mkdirSync(dir, { recursive: true });
  const adapter = adapterFile();
  const nightly = path.join(dir, 'albert-evidence.js');
  try { fs.lstatSync(nightly); fs.unlinkSync(nightly); } catch { /* absent */ }
  try { fs.symlinkSync(adapter, nightly); } catch {
    fs.writeFileSync(nightly, `#!/usr/bin/env node\nrequire(${JSON.stringify(adapter)}).main(['check']);\n`, { mode: 0o755 });
  }
  for (const [name, op] of [['albert-watchdog.js', 'watchdog'], ['albert-friday.js', 'report']]) {
    fs.writeFileSync(path.join(dir, name), `#!/usr/bin/env node\nrequire(${JSON.stringify(adapter)}).main([${JSON.stringify(op)}]);\n`, { mode: 0o755 });
  }
}

function bindAlbertSchedules(home, config, agent, channelId, now) {
  installChecks(home);
  const key = conversationKey(config.slack.team, channelId, 'board');
  const store = new Store(ignitePaths(home).database);
  try {
    store.upsertConversation({
      key, agent, workspace: config.slack.team, channel: channelId, rootTs: 'board', activated: false,
    });
    const ids = [];
    for (const row of SCHEDULES) {
      const spec = cadenceSpec({
        cron: row.cron, every: row.every, tz: row.tz,
      });
      const nextAt = spec.nextAt != null ? spec.nextAt : nextOccurrence(spec.cadence, spec.timezone, now);
      store.upsertSchedule({
        id: row.id,
        conversationKey: key,
        cadence: spec.cadence,
        timezone: spec.timezone,
        nextAt,
        enabled: true,
        note: row.note,
        report: 'when-useful',
        checkTool: row.check,
      });
      ids.push(row.id);
    }
    return ids;
  } finally { store.close(); }
}

function extraSelection(home, verb) {
  let record;
  try { record = JSON.parse(fs.readFileSync(path.join(home, 'agent.json'), 'utf8')); } catch { return []; }
  if (record.name !== 'albert') return [];
  if (verb === 'remove' && !(record.files || []).includes(RULE_ID)) return [];
  return [RULE_ID];
}

if (require.main === module) {
  try { process.exit(main()); }
  catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exit(1);
  }
}

module.exports = {
  RULE_ID, CHECKS, SCHEDULES, ZONE, ownerRows, reconcile, refreshEvidence, queueReport, runCheck, runWatchdog,
  legacyFenced, fenceFile, installChecks, bindAlbertSchedules, extraSelection, main, adapterFile, legacyCursor,
  saoPauloDate, readCursors, FIXED_TZ,
};
