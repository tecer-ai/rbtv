'use strict';

// THE BUS FERRY — coordination bus → the owner's Slack DM. One way, outbound only.
//
// The problem it solves (owner-hit 2026-08-06): run agents answer the master over the
// team-kit coordination bus (`<goal>/runs/<run>/coordination/messages.md`). The
// channel-master's Slack sittings are ONE-TURN HEADLESS sessions, so a bus row
// addressed to `master` — a leader's ack, a question, a blocked report — sits unread
// until somebody happens to open the file. Nothing pushed it anywhere. This module is
// that push, and ONLY that push: Slack → bus stays the sittings' job.
//
// ⚑ NO NEW CAPABILITY. The ferry reads workspace FILES and posts OUTBOUND through the
// bridge's existing transport. No gateway intent, no store handle, no listener, no
// write to the bus.
//
// ⚑ CURSOR AT TAIL ON FIRST SIGHT — the rule the whole module exists around. A live
// run's messages.md holds THOUSANDS of rows (5.9 MB / 4817 rows on the run this was
// built against). Ferrying "every row addressed to master" on first sight would dump a
// run's entire history into the owner's phone. So: the FIRST time the ferry sees a run,
// it records the cursor at the CURRENT TAIL and ferries NOTHING. Only rows appended
// after that are the owner's business. The cursor is persisted through the bridge's
// state file, so a restart does not re-arm a flood either.
//
// ⚑ A ROW IS FERRIED ONLY AFTER A CONFIRMED DELIVERY. The cursor advances on
// `delivered: true` — a failed post is retried next pass, bounded, then skipped loudly.
// One undeliverable row must never wedge the ferry behind it forever.

const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_POLL_MS = 15000;
const DEFAULT_MAX_ATTEMPTS = 20;      // per-row post retries before skipping it (never unbounded)
const DEFAULT_MAX_BODY_CHARS = 3000;  // phone-first: a bus row can be an essay

// `## 4774 | from: master | to: leader | type: note | 2026-08-06 14:23`
//
// Read the fields BY KEY, never by position. The bus header grammar is deliberately
// ADDITIVE (coord.py `MSG_HEADER`): a new optional field may be inserted BETWEEN two
// existing ones, and `from-pkg:` already sits between `from:` and `to:`. A positional
// regex reads such a row as MALFORMED and drops it — silently, and precisely for the
// cross-package sends this ferry exists to surface. Observed live on
// build-core-daemon-mvp/run-3 #2366, 2026-08-06.
const HEADER_ID_RE = /^## (\d+) \| (.+)$/;

// The header, or null if the line is not one. Only `from` / `to` / `type` are required;
// every other field (`from-pkg`, `re`, `why`, `supersedes`, the trailing timestamp) is
// carried by the grammar and ignored here.
function parseHeader(line) {
  const m = line.match(HEADER_ID_RE);
  if (!m) return null;
  const f = {};
  for (const part of m[2].split(' | ')) {
    const i = part.indexOf(': ');
    if (i > 0) f[part.slice(0, i)] = part.slice(i + 2).trim();
  }
  if (!f.from || !f.to || !f.type) return null;
  return { id: Number(m[1]), from: f.from, to: f.to, type: f.type, body: [] };
}

// `to:` is comma/space tolerant — `master`, `master, leader`, `leader master` all match
// the TOKEN `master`, while `goal-master` / `master-goal` do not.
function addressesMaster(to) {
  return String(to).split(/[,\s]+/).some((t) => t === 'master');
}

// Parse a messages.md body into rows. DEFENSIVE by construction: the file is appended
// by live agents, so the tail may be a half-written row.
//
// The torn-write rule: the LAST row is only complete when the file ends with a newline.
// A row that is not complete is left for the next pass — never posted half-read.
// ponytail: newline-terminated is a heuristic, not a lock. A writer that flushes a
// partial line ending in "\n" mid-row would defeat it; the fix then is a real
// end-of-record marker in the bus format, not more parsing here.
function parseMessages(text, onMalformed) {
  const rows = [];
  const complete = text.endsWith('\n');
  const lines = text.split('\n');
  let cur = null;
  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (cur) rows.push(cur);
      // `line.match(re)`, never `re.exec(line)` — probe-chat-boundary's spawn guard
      // matches the literal `.exec(`, and a regex call must not read as a process spawn.
      cur = parseHeader(line);
      if (!cur && onMalformed) onMalformed(line);
      continue;
    }
    if (cur) cur.body.push(line);
  }
  if (cur && complete) rows.push(cur);
  for (const r of rows) r.body = r.body.join('\n').trim();
  return rows;
}

// The Slack message: one mrkdwn header line, then the body. Truncation cuts at a LINE
// boundary so a wrapped table or list never ends mid-token, and names where the full
// text lives.
function formatMessage(row, { goalId, runId, relPath, maxBodyChars = DEFAULT_MAX_BODY_CHARS }) {
  const header = `*bus → you* — ${goalId}/${runId} · from ${row.from} · ${row.type} · #${row.id}`;
  let body = row.body;
  if (body.length > maxBodyChars) {
    const cut = body.slice(0, maxBodyChars);
    const nl = cut.lastIndexOf('\n');
    body = (nl > 0 ? cut.slice(0, nl) : cut) + `\n… (truncated — full text: ${relPath} #${row.id})`;
  }
  return body ? `${header}\n${body}` : header;
}

// Enumerate the open runs of every goal under `<workspaceRoot>/.rbtv/goals/`.
// runs.csv: `run-id,type,state,taskforce-ids,opened,closed`.
function openRuns(workspaceRoot) {
  const goalsDir = path.join(workspaceRoot, '.rbtv', 'goals');
  let goals;
  try { goals = fs.readdirSync(goalsDir, { withFileTypes: true }); } catch { return []; }
  const out = [];
  for (const g of goals) {
    if (!g.isDirectory()) continue;
    let csv;
    try { csv = fs.readFileSync(path.join(goalsDir, g.name, 'runs.csv'), 'utf8'); } catch { continue; }
    for (const line of csv.split('\n').slice(1)) {
      const cols = line.split(',');
      if (cols.length < 3 || cols[2].trim() !== 'open') continue;
      out.push({ goalId: g.name, runId: cols[0].trim() });
    }
  }
  return out;
}

function createBusFerry({
  workspaceRoot,
  transport,
  dmUserId = null,
  logger = null,
  pollMs = DEFAULT_POLL_MS,
  maxAttempts = DEFAULT_MAX_ATTEMPTS,
  maxBodyChars = DEFAULT_MAX_BODY_CHARS,
  onMutate = null,
} = {}) {
  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // `<goalId>/<runId>` -> last-ferried msg id. PERSISTED (state file `busFerry` block).
  const cursors = new Map();
  // Volatile per-pass bookkeeping — deliberately NOT persisted: attempt counts and the
  // "already warned about this run's malformed headers" flag are both per-process.
  const attempts = new Map();   // `<key>#<msgId>` -> failed post count
  const warned = new Set();
  const sizes = new Map();      // `<key>` -> last seen byte size (skip an unchanged file)

  let dmChannel = null;
  let enabled = false;
  let timer = null;
  let ticking = false;

  function persist() { if (onMutate) onMutate(); }

  async function _runOnce() {
    if (!enabled || ticking) return;
    ticking = true;
    try {
      for (const { goalId, runId } of openRuns(workspaceRoot)) {
        const key = `${goalId}/${runId}`;
        const relPath = path.join('.rbtv', 'goals', goalId, 'runs', runId, 'coordination', 'messages.md');
        const file = path.join(workspaceRoot, relPath);
        let st;
        try { st = fs.statSync(file); } catch { continue; }
        if (cursors.has(key) && sizes.get(key) === st.size) continue; // nothing appended
        let text;
        // ponytail: whole-file read on every size change. 6 MB / few ms on a local
        // disk; if bus volume ever makes that hurt, remember a byte offset per run and
        // read the tail instead.
        try { text = fs.readFileSync(file, 'utf8'); } catch (err) {
          log('warn', 'bus ferry could not read messages.md', { key, error: err.message });
          continue;
        }
        const rows = parseMessages(text, (line) => {
          if (warned.has(key)) return log('debug', 'bus ferry skipped a malformed header', { key, line: line.slice(0, 120) });
          warned.add(key);
          log('warn', 'bus ferry skipping malformed message header(s) in this run (logged once)', { key, line: line.slice(0, 120) });
        });
        sizes.set(key, st.size);

        // FIRST SIGHT — cursor at the tail, ferry NOTHING. The run's backlog is history.
        if (!cursors.has(key)) {
          const tail = rows.length ? rows[rows.length - 1].id : 0;
          cursors.set(key, tail);
          persist();
          log('info', 'bus ferry saw a run for the first time — cursor set at tail, backlog NOT ferried', { key, cursor: tail, rows: rows.length });
          continue;
        }

        // In id order, so one undeliverable row does not let a later one jump it.
        for (const row of rows) {
          if (row.id <= cursors.get(key)) continue;
          if (!addressesMaster(row.to)) { cursors.set(key, row.id); persist(); continue; }
          const text = formatMessage(row, { goalId, runId, relPath, maxBodyChars });
          let delivered = false;
          let error = null;
          try {
            const res = await transport.sendToOwner({ channel: dmChannel, threadTs: null, text });
            delivered = Boolean(res && res.delivered);
            error = res && res.error;
          } catch (err) {
            error = err.message;
          }
          if (delivered) {
            attempts.delete(`${key}#${row.id}`);
            cursors.set(key, row.id);
            persist();
            log('info', 'bus ferry delivered a bus row to the owner DM', { key, msgId: row.id, from: row.from, chars: text.length });
            continue;
          }
          const akey = `${key}#${row.id}`;
          const n = (attempts.get(akey) || 0) + 1;
          attempts.set(akey, n);
          if (n >= maxAttempts) {
            attempts.delete(akey);
            cursors.set(key, row.id); // advance — never wedge the ferry on one row
            persist();
            log('warn', 'bus ferry giving up on a row after persistent post failures — NOT delivered, cursor advanced', { key, msgId: row.id, attempts: n, error });
            continue;
          }
          log('warn', 'bus ferry post failed — will retry next pass', { key, msgId: row.id, attempts: n, error });
          // Forget the size so the next pass RE-READS this run. Without this the
          // unchanged-size short-circuit at the top would skip the run entirely and the
          // retry would never happen — the bound would be unreachable and the row lost.
          sizes.delete(key);
          break; // stop this run's pass here; order is the point
        }
      }
    } finally {
      ticking = false;
    }
  }

  // Resolve the owner's DM channel ONCE, then arm the poll loop. FAIL CLOSED: no DM
  // channel → the ferry stays disabled and says so; the rest of the bridge is
  // unaffected, which is the whole reason this is a sibling module and not a branch.
  async function start() {
    if (!workspaceRoot) {
      log('error', 'bus_ferry is enabled but workspace_root is NOT configured — BUS FERRY DISABLED (nothing to enumerate)');
      return { enabled: false, reason: 'no-workspace-root' };
    }
    if (!dmUserId) {
      log('error', 'bus_ferry is enabled but no DM user could be determined (set bus_ferry_dm_user, or an allowlist) — BUS FERRY DISABLED');
      return { enabled: false, reason: 'no-dm-user' };
    }
    if (typeof transport.openDm !== 'function') {
      log('error', 'transport exposes no openDm — BUS FERRY DISABLED');
      return { enabled: false, reason: 'no-open-dm' };
    }
    let opened;
    try { opened = await transport.openDm(dmUserId); } catch (err) { opened = { ok: false, error: err.message }; }
    if (!opened || !opened.ok || !opened.channel) {
      log('error', 'bus ferry could not open the owner DM — BUS FERRY DISABLED (the rest of the bridge is unaffected)', { dmUserId, error: opened && opened.error });
      return { enabled: false, reason: 'open-dm-failed', error: opened && opened.error };
    }
    dmChannel = opened.channel;
    enabled = true;
    timer = setInterval(() => {
      _runOnce().catch((err) => log('warn', 'bus ferry tick error', { error: err.message }));
    }, pollMs);
    if (timer.unref) timer.unref();
    log('info', 'bus ferry started', { workspaceRoot, dmUserId, dmChannel, pollMs, knownRuns: cursors.size });
    return { enabled: true, dmChannel };
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
    enabled = false;
    log('info', 'bus ferry stopped');
  }

  // Serialization — this module owns its own shape inside the bridge's state file.
  function toJSON() { return { cursors: Object.fromEntries(cursors) }; }
  function load(obj) {
    cursors.clear();
    for (const [k, v] of Object.entries((obj && obj.cursors) || {})) {
      if (Number.isInteger(v)) cursors.set(String(k), v);
    }
    return cursors.size;
  }

  return { start, stop, tick: _runOnce, toJSON, load, _cursors: cursors, get enabled() { return enabled; }, get dmChannel() { return dmChannel; } };
}

module.exports = { createBusFerry, parseMessages, formatMessage, addressesMaster, openRuns, DEFAULT_MAX_BODY_CHARS };
