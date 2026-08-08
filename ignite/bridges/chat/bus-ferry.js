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
// ⚑ ONE EXCEPTION, AND ONLY ONE (7.546): a run this process watched BE BORN — enumerated
// open while its messages.md did not exist yet — has no history, so its cursor seeds at 0
// and its first rows DO travel. That first row is a fresh goal's first escalation, and a
// newly scaffolded goal rosters no authority seat to read it.
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

// The ROLE TOKEN this ferry carries. `master` is an ADDRESS, not a seat name: the bus
// resolves it through `relays:` on the seat descriptors (coord.py `relay_seats`), so the
// seat holding the role may be called anything — `goal-master`, or a name a future run
// picks. Nothing here may key on a seat's NAME; that is the defect `relay_seats`'s own
// docstring exists to prevent.
const ROLE_TOKEN = 'master';

// Does `to:` address the master ROLE? Comma/space tolerant — `master`, `master, leader`,
// `leader master` all match.
//
// ⚑ THE SEAT'S OWN NAME COUNTS TOO, and that is not tidiness — it is a measured defect.
// A sender is supposed to write the role address `master` and stay ignorant of which seat
// holds it (owner ruling). Within TWO HOURS of the seat being renamed `master` →
// `goal-master`, the leader was writing `to: goal-master` instead (rows #5585, #5606,
// #5616 on 2026-08-07). coord.py delivers those fine — it is a real roster name — so
// nothing looks wrong WHILE the seat is checked in. But a role-addressed row is the only
// thing this ferry matches, so those rows were invisible to it: the moment that seat
// checks out they reach NOBODY — no seat reading them, no fallback, nothing in the owner's
// DM. That is exactly the 2026-08-06 failure this module was built for, returning through
// the new name. Matching the holder seats' own names closes it MECHANICALLY, instead of
// asking every sender to remember a convention that had already drifted.
//
// `isRoleSeat` is a PREDICATE, not a set, and is consulted only for tokens the role address
// did not already match — resolved LAZILY for that reason. A run holds hundreds of seat
// folders; reading every descriptor each pass to pre-build a set would trade a real defect
// for a real cost, when the only names that can matter are the few actually written in a
// `to:` field. Check-in state is deliberately NOT part of this question: a row addressed to
// a checked-OUT holder is precisely the row that must travel.
function addressesMaster(to, isRoleSeat = null) {
  const parts = String(to).split(/[,\s]+/);
  if (parts.some((t) => t === ROLE_TOKEN)) return true;
  return typeof isRoleSeat === 'function' && parts.some((t) => t && isRoleSeat(t));
}

// Does this seat's descriptor declare the role token? One file read, memoized by the caller.
function seatDeclaresRole(runDir, seat) {
  let fm;
  try { fm = fs.readFileSync(path.join(runDir, 'seats', seat, 'seat.md'), 'utf8'); } catch { return false; }
  const m = fm.match(/^relays:[ \t]*(.+?)[ \t]*$/m);
  return Boolean(m) && m[1].split(/[,\s]+/).some((t) => t.toLowerCase() === ROLE_TOKEN);
}

// ── IS ANYBODY HOLDING THE ROLE RIGHT NOW? (owner ruling 2026-08-07) ──────────────────
//
// A row addressed to `master` is addressed to the ROLE, and the role has three seats. When
// a seat inside this run holds it and is CHECKED IN, that seat's own inbox and wake already
// deliver the row — ferrying it as well would push a message at the owner that an agent is
// about to answer. When nobody holds it, the row must reach the standing `channel master`
// instead of the owner's triage queue.
//
// ⚑ THE LIVENESS SIGNAL IS THE RUN'S OWN ROSTER, NOT A PROBE. `coordination/workers.md` is
// written by `coordinate checkin`/`checkout`; the roster's `active` column IS the check-in
// state, and LAST ROW PER AGENT WINS (coord.py `latest_rows`). Asking the process table
// instead would be a second answer to a question the run already answers — and a seat's own
// status line freezes at its last good value when it dies, which the roster does not.
//
// ⚑ FAIL TOWARD DELIVERY. An empty return means ROUTE, and an unreadable roster, a missing
// one, and a roster where nobody holds the role all return it — cannot-tell is never
// distinguished from nobody-home, because both take the same branch. The failure this whole
// module exists to fix was a row nobody read.
//
// Roster grammar: `| agent | active | pane | working on | in | out | last-read |`, LAST ROW
// PER AGENT WINS. Only the live seats' descriptors are read — a run holds hundreds of seat
// folders and all but a handful are checked out, so this is a few reads per pass, never a
// directory sweep.
function roleHeldLive(workspaceRoot, goalId, runId) {
  const runDir = path.join(workspaceRoot, '.rbtv', 'goals', goalId, 'runs', runId);
  let text;
  try { text = fs.readFileSync(path.join(runDir, 'coordination', 'workers.md'), 'utf8'); } catch { return []; }
  const live = new Map();
  for (const line of text.split('\n')) {
    if (!line.startsWith('| ')) continue;
    const cells = line.split('|').map((s) => s.trim()); // leading + trailing empty cell
    const [, agent, active] = cells;
    if (cells.length < 8 || !agent || agent === 'agent' || agent.startsWith('---')) continue;
    live.set(agent, active === 'yes');
  }
  const holders = [];
  for (const [agent, isLive] of live) {
    if (isLive && seatDeclaresRole(runDir, agent)) holders.push(agent);
  }
  return holders;
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

// ── THE RETURN LEG: A ROW THAT NAMES ITS OWN CHAT THREAD ─────────────────────────────
//
// Everything above answers "a bus row is addressed to the master role and nobody live
// holds it". This answers the OPPOSITE direction, which had no leg at all: the master
// seat ANSWERING the channel-master. Owner-ruled 2026-08-07 after both gates above were
// measured refusing it — `to: channel-master` matches neither the role token nor any run
// seat (none can be named that), and a row addressed `to: master` stands down because the
// live holder of the role IS the sender.
//
// ⚑ THE TOKEN IS THE ADDRESS, NOT A SEAT NAME — deliberately. This module's own rule is
// that nothing here may key on a seat's NAME (see `ROLE_TOKEN`), and a `channel-master`
// literal would have broken it. A row carrying `[chat-thread: <channel>:<ts>]` states
// WHERE it belongs, so the ferry routes on a declaration the sender made, not on a name
// this file had to know. It also needs no `holders` check: the destination is a Slack
// thread, which no run seat can ever be holding.
//
// ⚑ THE BRACKETS ARE THE LOOP GUARD. `forward-path.js` tells every sitting its own thread
// in the PLAIN form (`chat-thread: <id>`), so a sitting relaying a QUESTION onto the bus can
// name where the answer belongs. Only the BRACKETED form routes. Without that split the
// ferry would read the outbound question as an inbound answer and mint a sitting from it —
// the question arriving back in its own thread. So: plain = "this is which thread I am",
// bracketed = "deliver this INTO that thread", and only a seat answering toward chat writes
// brackets.
//
// ⚑ THE ROUTING SHAPE IS NARROWER THAN THE PROMPT PREFIX, DELIBERATELY. `forward-path.js`
// stamps every sitting with whatever conversation id it has, and a GOAL conversation's id is
// the bare channel (`C0001`) — a goal channel maps 1:1 onto its channel and is never sharded
// by `thread_ts`. This regex requires `<channel>:<ts>`, so a goal sitting's id can never
// route here. That is not an oversight: routing into a goal channel is a different leg (a
// different route kind and a different seat home), and admitting the bare form would mint a
// `kind: 'master'` sitting on a goal's channel. When that leg is wanted, build it — do not
// widen this.
//
// ⚑ FAILS CLOSED. No token, or a malformed one, and this returns null — the row takes the
// unchanged path above. The strict shape is the point: an accidental match would divert a
// row meant for the owner's DM.
const CHAT_THREAD_RE = /\[chat-thread:\s*([A-Z][A-Z0-9_]{2,}:\d+\.\d+)\s*\]/;

function chatThreadToken(body) {
  const m = String(body || '').match(CHAT_THREAD_RE);
  return m ? m[1] : null;
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
  // WHERE a row goes when no live seat holds the role. Injected by the bridge, which owns
  // the thread map and the forward path this ferry deliberately does not hold: it posts the
  // row to the owner DM and MINTS that post's thread as a channel-master sitting, so the
  // agent answers in-thread and the owner's reply continues the SAME sitting with the row
  // in its history. Default (probes, any embedder that wires nothing) is the plain DM post
  // this module shipped with — same signature, same `{ delivered, ts }` contract.
  routeToMaster = null,
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
  // Runs this PROCESS watched be born: enumerated as open with no messages.md on disk yet.
  // Deliberately NOT persisted — see the born-watched block in `_runOnce` for why.
  const bornWatched = new Set();

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
        // NO LOG YET = WE WATCHED THIS RUN BE BORN. The run is registered open and its
        // coordination folder is created EMPTY (`materialize-seats.py`); the log appears only
        // when somebody first writes to it (`coord.py append_message`). Seeing that state is the
        // one moment the ferry can know a run has NO history — which is what the first-sight
        // rule below is protecting against. Recorded here, consumed there.
        try { st = fs.statSync(file); } catch { bornWatched.add(key); continue; }
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
        //
        // ⚑ UNLESS WE WATCHED IT BE BORN (7.546). A run whose log did not exist on an earlier
        // pass of THIS process has no history to protect — the flood rule then costs everything
        // and protects nothing, and what it swallows is a fresh goal's FIRST escalation. A newly
        // scaffolded goal rosters only the planning DAG, so that first message is exactly the one
        // with nobody in the room to read it. Seed at ZERO and FALL THROUGH, so the row travels on
        // the pass that sees it: `continue`-ing here would set the cursor and then skip this run
        // on every later pass via the unchanged-size short-circuit above, until some SECOND
        // message happened to arrive.
        //
        // ⚑ THIS DOES NOT COVER A GOAL BORN WHILE THE BRIDGE IS DOWN, and the marker is not
        // persisted precisely because persisting it would imply that it does. In that case the log
        // already exists when the bridge returns, no pass ever observed the empty state, and the
        // backlog is (correctly, by this rule) treated as history. The durable record for that
        // case is the goal's own `doubts.md` park — tier 1 of the escalation ladder, kept for
        // exactly this reason.
        if (!cursors.has(key)) {
          if (bornWatched.has(key)) {
            bornWatched.delete(key);
            cursors.set(key, 0);
            persist();
            log('info', 'bus ferry watched this run be born — cursor seeded at 0, its first rows ARE the owner\'s business', { key, rows: rows.length });
          } else {
            const tail = rows.length ? rows[rows.length - 1].id : 0;
            cursors.set(key, tail);
            persist();
            log('info', 'bus ferry saw a run for the first time — cursor set at tail, backlog NOT ferried', { key, cursor: tail, rows: rows.length });
            continue;
          }
        }

        // WHO HOLDS THE ROLE, resolved ONCE per pass per run — not per row. The roster does
        // not change between two rows of the same read.
        const holders = roleHeldLive(workspaceRoot, goalId, runId);
        // Memoized per pass: at most one descriptor read per distinct name written in a
        // `to:` field, and zero when every row uses the role address as it should.
        const runDir = path.join(workspaceRoot, '.rbtv', 'goals', goalId, 'runs', runId);
        const roleSeatMemo = new Map();
        const isRoleSeat = (name) => {
          if (!roleSeatMemo.has(name)) roleSeatMemo.set(name, seatDeclaresRole(runDir, name));
          return roleSeatMemo.get(name);
        };

        // In id order, so one undeliverable row does not let a later one jump it.
        for (const row of rows) {
          if (row.id <= cursors.get(key)) continue;
          // THE RETURN LEG. A row naming its own chat thread is routed there and skips BOTH
          // gates below — neither is about it. Read `chatThreadToken`'s header for why this
          // is a token and not a seat name.
          const chatThread = chatThreadToken(row.body);
          if (!chatThread && !addressesMaster(row.to, isRoleSeat)) { cursors.set(key, row.id); persist(); continue; }
          // A LIVE SEAT HOLDS THE ROLE — that seat's own inbox and wake carry this row, so
          // the ferry stands down. The cursor still advances: the row was DISPOSED OF, by a
          // reader better placed than the ferry, and re-offering it when that seat later
          // checks out would deliver the same row twice.
          if (holders.length && !chatThread) {
            cursors.set(key, row.id);
            persist();
            log('info', 'bus ferry stood down — a live seat holds the role and receives this row directly', { key, msgId: row.id, from: row.from, holders });
            continue;
          }
          const text = formatMessage(row, { goalId, runId, relPath, maxBodyChars });
          let delivered = false;
          let error = null;
          try {
            const send = routeToMaster || ((a) => transport.sendToOwner(a));
            const res = await send({ channel: dmChannel, threadTs: null, text, chatThread });
            delivered = Boolean(res && res.delivered);
            error = res && res.error;
          } catch (err) {
            error = err.message;
          }
          if (delivered) {
            attempts.delete(`${key}#${row.id}`);
            cursors.set(key, row.id);
            persist();
            log('info', chatThread ? 'bus ferry routed a bus row to its named chat thread' : 'bus ferry delivered a bus row to the owner DM',
                { key, msgId: row.id, from: row.from, chars: text.length, ...(chatThread ? { chatThread } : {}) });
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

module.exports = {
  createBusFerry, parseMessages, formatMessage, addressesMaster, openRuns,
  roleHeldLive, seatDeclaresRole, ROLE_TOKEN, DEFAULT_MAX_BODY_CHARS,
};
