'use strict';

// cast — `cast monitor` — the freeze tripwire, its witness channel, roster and watch.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const fs = require('fs');
const path = require('path');

const { fail } = require('./core');
const { HANDLES_FILE, procStart } = require('./handles');
const { detectProviderLimit, formatReason } = require('./provider-limit');
const { codexSessions, opencodeCandidates, opencodeStore } = require('./sessions');

// Reports jobs that are ALIVE BUT FROZEN. The one-shot roster never reports completion (that
// rides the caller's own tracked background launch). --watch also notices a departure: a job
// it has seen alive that left liveJobs() is ENDED — not finished-vs-died; cast does not record
// wrapper exit codes. Terminal freeze states: STALLED (no life for --stall) and NO-SIGNAL (no
// signal and no work ever, --grace past launch). SUSPECT is the non-terminal middle: the
// harness signal is silent but a second channel still shows life.
//
// Two channels per job. S1, the harness progress signal (transcript/rollout/session mtime), goes
// silent whenever the agent blocks on one long tool call — a probe suite writing to a --summary
// file looked dead for 10 minutes on 2026-08-19 and a healthy seat was killed on the monitor's
// word (2 of 2 firings that day were false). S2, the witness channel, reads the process TREE under
// the handle PID (/proc CPU-tick + io-byte deltas, new descendants) plus the job's stdout capture
// file. S2 is a witness of LIFE, never of death: a quiet or unreadable tree only withholds a
// terminal verdict, it never causes one. A terminal verdict requires BOTH channels silent.
//
// --stall defaults to 600s — measured 0 false positives at 600 across 12,371 healthy gaps /
// 94 runs. Do not lower it.

// Owner ruling 2026-08-22: this monitor carries NO kill authority, and that must live in the CODE,
// not only in orchestrator prose — documents drift, the line an agent actually reads does not. The
// advisory rides every event burst. It trails the events rather than heading them so the machine-
// parseable line prefixes stay first (callers match on `STALL `/`ENDED `).
const ADVISORY = 'cast monitor: ADVISORY, not authority.'
  + ' STALL/NO-SIGNAL = frozen ONLY if you confirm it yourself — before killing, check for live'
  + ' descendants under the pid AND for files the job named still being written. Two firings on'
  + ' 2026-08-19 were false and a healthy seat was killed on this alarm.'
  + ' ENDED = the job is ALREADY GONE — never kill on it; read its output and exit code.\n';

const MONITOR_USAGE = 'cast monitor [--watch] [--stall SECONDS] [--grace SECONDS] [--poll SECONDS] [--deadline SECONDS] [--folder PREFIX] [--json]';

// Registry rows whose wrapper process is still the one that wrote them — the /proc starttime pin
// makes this comm-free and PID-reuse-proof. Re-read every poll, so launches mid-watch are picked up.
function liveJobs(prefix) {
  let text;
  try { text = fs.readFileSync(HANDLES_FILE, 'utf8'); } catch { return []; }
  const out = [];
  for (const line of text.split('\n')) {
    if (!line.trim()) continue;
    let h;
    try { h = JSON.parse(line); } catch { continue; }
    if (h.start == null || procStart(h.pid) !== h.start) continue;
    if (prefix && !String(h.folder).startsWith(prefix)) continue;
    out.push(h);
  }
  return out;
}

const mtimeOf = (f) => { try { return fs.statSync(f).mtimeMs; } catch { return null; } };

// --- the witness channel (S2): harness-agnostic life under the handle PID ----------------------
// Floors matter: a wedged node harness still wakes event-loop timers and burns a few ticks
// per poll — zero-threshold deltas would make a real hang undetectable. Shared floor 10 was
// below every harness's idle (2026-08-22 GLM lanes hung 9h while monitor said healthy).
// Measured 2026-08-31 treeSample() 30s polls — do not ship the 2026-08-22 numbers:
//   claude   idle 31–39 ticks, busy 85–207
//   opencode idle 103–114 ticks, busy 276–659
//   codex    idle 0–2 ticks, busy 204 ticks in ~5s generation
// IO dropped: idle TUI 120B–80KB, busy 0.7–245MB, retry-hang 108MB — a byte bar cannot
// separate hang from work. Capture growth + descendants + CPU remain. Scale by poll/30s.
const CPU_FLOOR_TICKS = { claude: 50, codex: 20, opencode: 150 };
const FLOOR_POLL_MS = 30_000;
const DEFAULT_DEADLINE_S = 4 * 60 * 60;
const DEADLINE_MS = Number(process.env.CAST_DEADLINE_MS) > 0
  ? Number(process.env.CAST_DEADLINE_MS)
  : DEFAULT_DEADLINE_S * 1000;
const OUT_BANNER_BYTES = 2048; // below this, stdout is a launch banner, not work

function readProcStat(pid) {
  try {
    const txt = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    const rest = txt.slice(txt.lastIndexOf(') ') + 2).split(' ');
    return { state: rest[0], cpu: Number(rest[11]) + Number(rest[12]), start: Number(rest[19]) };
  } catch { return null; }
}

// rchar+wchar, not read_bytes/write_bytes: the files seats write live on tmpfs, which never
// reaches the block layer — syscall counters do.
function readProcIo(pid) {
  try {
    let sum = 0;
    for (const line of fs.readFileSync(`/proc/${pid}/io`, 'utf8').split('\n')) {
      if (line.startsWith('rchar:') || line.startsWith('wchar:')) sum += Number(line.split(' ')[1]);
    }
    return sum;
  } catch { return null; }
}

function descendantPids(pid) {
  const out = [];
  const queue = [pid];
  while (queue.length) {
    const p = queue.shift();
    let tasks;
    try { tasks = fs.readdirSync(`/proc/${p}/task`); } catch { continue; }
    for (const t of tasks) {
      let kids;
      try { kids = fs.readFileSync(`/proc/${p}/task/${t}/children`, 'utf8').trim(); } catch { continue; }
      if (!kids) continue;
      for (const k of kids.split(/\s+/)) { out.push(Number(k)); queue.push(Number(k)); }
    }
  }
  return out;
}

// The job's stdout capture, found via fd 1 — no handle-schema change. Both 2026-08-19 false
// positives had their decisive evidence (11KB / 26KB of real output) sitting on fd 1.
function captureFile(pid) {
  try {
    const target = fs.readlinkSync(`/proc/${pid}/fd/1`);
    if (!target.startsWith('/')) return null; // pipe:[…], socket:[…]
    const st = fs.statSync(target);
    return st.isFile() ? target : null;
  } catch { return null; }
}

function captureSize(pid) {
  const f = captureFile(pid);
  if (!f) return null;
  try { return fs.statSync(f).size; } catch { return null; }
}

function cpuFloor(h, pollMs) {
  const per30 = CPU_FLOOR_TICKS[h.harness] ?? CPU_FLOOR_TICKS.opencode;
  return Math.max(1, Math.round(per30 * pollMs / FLOOR_POLL_MS));
}

function treeSample(h) {
  const pids = [h.pid, ...descendantPids(h.pid)];
  const members = new Set();
  let cpu = 0;
  let io = 0;
  let running = false;
  for (const p of pids) {
    const st = readProcStat(p);
    if (!st) continue; // unreadable = no sample, never "idle"
    members.add(`${p}:${st.start}`);
    cpu += st.cpu;
    if (st.state === 'R') running = true;
    const i = readProcIo(p);
    if (i !== null) io += i;
  }
  return { cpu, io, members, running, desc: pids.length - 1, capSize: captureSize(h.pid) };
}

function jobMemo(cache, h) {
  const key = `memo:${h.pid}:${h.start}`;
  // lastEvidenceAt seeds at t0: a job whose tree NEVER witnessed life has already spent the
  // confirm window when the stall threshold crosses — a genuine deadlock still fires at ~--stall.
  if (!cache.has(key)) cache.set(key, { prev: null, lastEvidenceAt: h.t0, hadWork: false });
  return cache.get(key);
}

// Evidence of life this poll. First sample has no deltas: live descendants or a running root
// count once; every later poll needs a floored delta, so a busy-spin can't ride a stale snapshot.
function witness(h, now, memo, pollMs = FLOOR_POLL_MS) {
  const s = treeSample(h);
  const prev = memo.prev;
  let dCpu = 0;
  let dIo = 0;
  let evidence;
  if (!prev) {
    evidence = s.desc > 0 || s.running;
  } else {
    dCpu = s.cpu - prev.cpu;
    dIo = s.io - prev.io;
    evidence = dCpu >= cpuFloor(h, pollMs)
      || [...s.members].some((m) => !prev.members.has(m))
      || (s.capSize !== null && prev.capSize !== null && s.capSize > prev.capSize);
  }
  memo.prev = s;
  if (evidence) { memo.lastEvidenceAt = now; memo.hadWork = true; }
  if (s.capSize !== null && s.capSize >= OUT_BANNER_BYTES) memo.hadWork = true;
  return { evidence, sample: s, dCpu: Math.max(0, dCpu), dIo: Math.max(0, dIo) };
}

// claude: the parent transcript goes FLAT while subagents work, so the subagent subtree is a
// mandatory second arm — a leader with busy children would otherwise read as stalled.
function claudeProgress(h) {
  const own = h.transcript ? mtimeOf(h.transcript) : null;
  if (own === null) return null; // transcript absent = the signal never appeared
  let newest = own;
  const dir = path.join(path.dirname(h.transcript), h.session, 'subagents');
  try {
    for (const f of fs.readdirSync(dir)) {
      const m = mtimeOf(path.join(dir, f));
      if (m > newest) newest = m;
    }
  } catch { /* no subagent subtree yet */ }
  return newest;
}

// Session ids/files already bound to another live job in this watch. Same-folder same-minute
// launches (how batches run on this box) are otherwise ambiguous — 2026-08-19 §3b flavor.
function claimedBinds(cache) {
  const out = new Set();
  for (const [k, v] of cache) if (k.startsWith('bind:')) out.add(v);
  return out;
}

// codex names no session at launch, so its rollout is resolved post-hoc — reusing the same reader
// `cast sessions` uses (cwd match + thread_source=user), narrowed to rollouts born at/after t0.
// Resolved once per job and cached: only the mtime is re-read each poll.
function codexRollout(h, claimed) {
  const row = codexSessions(h.folder, 5).find((r) => r.started >= h.t0 - 2000 && !claimed.has(r.file));
  return row ? row.file : null;
}

// opencode: `time_updated` on the job's own top-level session row — measured to advance once per
// tool-call round trip. parent_id is null keeps subagent child sessions out. Bind once by t0
// window (closest time_created, never newest-across-the-plan) and cache id like codexRollout.
// The window is 30s (was 2s): a real session missed the 2s window on 2026-08-19 and the job read
// NO-SIGNAL with 26KB of output; the claimed-set keeps the wider window off siblings' rows.
function opencodeBind(h, claimed) {
  const rows = opencodeCandidates(h.folder)
    .filter((r) => r.time_created >= h.t0 - 30_000 && !claimed.has(r.id));
  if (!rows.length) return null;
  let best = rows[0];
  let bestDist = Math.abs(best.time_created - h.t0);
  for (const r of rows) {
    const d = Math.abs(r.time_created - h.t0);
    if (d < bestDist) { best = r; bestDist = d; }
  }
  return best.id;
}

function opencodeUpdated(id) {
  const store = opencodeStore();
  if (!fs.existsSync(store)) return null;
  try {
    const { DatabaseSync } = require('node:sqlite');
    const row = new DatabaseSync(store, { readOnly: true }).prepare(
      'select time_updated from session where id = ?',
    ).get(id);
    return row ? row.time_updated : null;
  } catch (e) {
    process.stderr.write(`cast: opencode session store unreadable (${e.message})\n`);
    return null;
  }
}

function opencodeProgress(h, cache) {
  const key = `bind:${h.pid}:${h.start}`;
  if (!cache.has(key)) {
    const id = opencodeBind(h, claimedBinds(cache));
    if (!id) return null;
    cache.set(key, id);
  }
  return opencodeUpdated(cache.get(key));
}

// null = the progress signal has never appeared for this job.
function progressAt(h, cache) {
  if (h.harness === 'claude') return claudeProgress(h);
  if (h.harness === 'opencode') return opencodeProgress(h, cache);
  if (h.harness === 'codex') {
    const key = `bind:${h.pid}:${h.start}`;
    if (!cache.has(key)) {
      const file = codexRollout(h, claimedBinds(cache));
      if (!file) return null; // not resolved yet — retry next poll
      cache.set(key, file);
    }
    return mtimeOf(cache.get(key));
  }
  return null;
}

// A terminal verdict needs BOTH channels silent, held across a confirm window of two polls.
// One-shot roster calls have no delta history, so their first sample leans on instant life
// (descendants / running root) — honest but coarser than a watch.
function classify(h, now, stallMs, graceMs, pollMs, cache, deadlineMs = DEADLINE_MS) {
  const memo = jobMemo(cache, h);
  const w = witness(h, now, memo, pollMs);
  const confirmMs = 2 * pollMs;
  const evAge = now - memo.lastEvidenceAt;
  const at = progressAt(h, cache);
  const limit = detectProviderLimit({
    harness: h.harness, model: h.model, t0: h.t0, capturePath: captureFile(h.pid),
  });
  const base = { witness: w, evAge, limit };
  if (limit) return { state: 'provider-limit', age: at === null ? evAge : now - at, ...base };
  if (now - h.t0 >= deadlineMs) return { state: 'DEADLINE', age: at === null ? evAge : now - at, ...base };
  if (at !== null) {
    const age = now - at;
    if (age < stallMs) return { state: 'ok', age, ...base };
    if (w.evidence || evAge < confirmMs) return { state: 'SUSPECT', age, ...base };
    return { state: 'STALLED', age, ...base };
  }
  if (memo.hadWork) {
    // unbound but demonstrably worked (§3b 2026-08-19): rides the stall clock from its last
    // evidence, never the grace clock — NO-SIGNAL is reserved for never-any-work.
    return { state: evAge >= stallMs ? 'STALLED' : 'ok', age: evAge, ...base };
  }
  if (now - h.t0 <= graceMs) return { state: 'ok', age: null, ...base };
  if (w.evidence || evAge < confirmMs) return { state: 'SUSPECT', age: null, ...base };
  return { state: 'NO-SIGNAL', age: null, ...base };
}

const secs = (ms) => Math.round(ms / 1000);
const tailShort = (s, cap = 44) => (s.length <= cap ? s : `…${s.slice(-(cap - 1))}`);

// Evidence suffix on rows and event lines: the orchestrator's verify-then-kill starts informed,
// and a wrong kill is reconstructable from the line that prompted it.
const evidenceSuffix = (w) => `desc=${w.sample.desc} cpu+${w.dCpu} io+${w.dIo}`
  + ` out=${w.sample.capSize === null ? '-' : w.sample.capSize}`;

function monitorRows(jobs, now, stallMs, graceMs, pollMs, cache, deadlineMs = DEADLINE_MS) {
  return jobs.map((h) => {
    const { state, age, witness: w, limit } = classify(h, now, stallMs, graceMs, pollMs, cache, deadlineMs);
    const row = {
      folder: h.folder,
      harness: h.harness,
      model: h.model,
      pid: h.pid,
      session: h.session,
      elapsed_s: secs(now - h.t0),
      progress_age_s: age === null ? null : secs(age),
      tree_desc: w.sample.desc,
      out_bytes: w.sample.capSize,
      state,
    };
    if (limit) {
      row.provider = limit.provider;
      row.resets = limit.reset;
    }
    return row;
  });
}

// Default form: a glance at what is running right now. Always exit 0 — a roster is not a verdict.
function runRoster(rows, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(rows)}\n`);
    process.exit(0);
  }
  if (rows.length === 0) {
    // Scope the absence claim: the roster sees only registry-recorded launches, so "empty"
    // must never read as "the box is quiet" — jobs launched before the registry existed
    // (or outside cast) are invisible here.
    let since = null;
    try {
      const first = fs.readFileSync(HANDLES_FILE, 'utf8').split('\n').find((l) => l.trim());
      since = first ? new Date(JSON.parse(first).t0).toISOString() : null;
    } catch { /* no registry yet */ }
    process.stdout.write(since
      ? `no live cast jobs (registry covers launches since ${since}; earlier or non-cast jobs are not visible here)\n`
      : 'no live cast jobs (registry empty — no launch has ever been recorded; this is not proof the box is quiet)\n');
    process.exit(0);
  }
  const cols = ['FOLDER', 'HARNESS', 'MODEL', 'PID', 'ELAPSED', 'PROGRESS', 'STATE'];
  const cells = rows.map((r) => [
    tailShort(r.folder), r.harness, r.model, String(r.pid),
    `${r.elapsed_s}s`, r.progress_age_s === null ? '-' : `${r.progress_age_s}s`, r.state,
  ]);
  const width = cols.map((c, i) => Math.max(c.length, ...cells.map((row) => row[i].length)));
  const line = (vals) => vals.map((v, i) => v.padEnd(width[i])).join('  ').trimEnd();
  process.stdout.write(`${line(cols)}\n`);
  for (const row of cells) process.stdout.write(`${line(row)}\n`);
  process.exit(0);
}

// --watch: silent while healthy. Freeze events (STALL/NO-SIGNAL) terminate at once with
// exit 3. ENDED is a departure this watch itself observed: a job it has seen alive is no
// longer in liveJobs(). Reported once, then suppressed. Exit 4 means "a job ended — go
// read its output"; it is NEVER 3, because 3 is KILL-OR-VERIFY authority and would tell
// an orchestrator to kill a process that is already gone (false-kill, 2026-08-19). If one
// poll lands both, freeze keeps precedence (exit 3). Exit 0 only when the watch was armed
// against an empty roster. SUSPECT is non-terminal and prints nothing here.
async function runWatch(prefix, stallMs, graceMs, pollMs, deadlineMs = DEADLINE_MS) {
  const cache = new Map();
  const seen = new Map();
  for (;;) {
    const jobs = liveJobs(prefix);
    const now = Date.now();
    const live = new Set();
    const events = [];
    let freeze = false;
    for (const h of jobs) {
      const key = `${h.pid}:${h.start}`;
      live.add(key);
      const { state, age, witness: w, limit } = classify(h, now, stallMs, graceMs, pollMs, cache, deadlineMs);
      const rec = seen.get(key) || { h, state, ended: false };
      rec.h = h;
      rec.state = state;
      seen.set(key, rec);
      if (state === 'STALLED') {
        freeze = true;
        events.push(`STALL ${h.pid} ${h.harness} ${h.session || '-'} ${h.folder}`
          + ` alive=${secs(now - h.t0)}s progress-age=${secs(age)}s ${evidenceSuffix(w)}`);
      } else if (state === 'NO-SIGNAL') {
        freeze = true;
        events.push(`NO-SIGNAL ${h.pid} ${h.harness} ${h.folder} alive=${secs(now - h.t0)}s`
          + ` ${evidenceSuffix(w)}`);
      } else if (state === 'provider-limit') {
        freeze = true;
        events.push(`PROVIDER-LIMIT ${h.pid} ${h.harness} ${h.folder} ${formatReason(limit)}`
          + ` ${evidenceSuffix(w)}`);
      } else if (state === 'DEADLINE') {
        freeze = true;
        events.push(`DEADLINE ${h.pid} ${h.harness} ${h.folder} alive=${secs(now - h.t0)}s`
          + ` ${evidenceSuffix(w)}`);
      }
    }
    for (const [key, rec] of seen) {
      if (live.has(key) || rec.ended) continue;
      const { h, state } = rec;
      // A row can leave the registry without the job dying: emitHandle prunes every row older than
      // HANDLE_TTL_MS on each launch, and liveJobs returns [] on ANY read failure. Absence of a row
      // is NOT death. Confirm at /proc with the same starttime pin liveJobs uses; if the process is
      // still there, say nothing and do NOT latch — a false ENDED tells an orchestrator to stop
      // watching a job that is still burning tokens, which is the 2026-08-22 failure inverted.
      if (procStart(h.pid) === h.start) continue;
      rec.ended = true;
      events.push(`ENDED ${h.pid} ${h.harness} ${h.folder} alive=${secs(now - h.t0)}s last-state=${state}`);
    }
    if (events.length) {
      process.stdout.write(`${events.join('\n')}\n`);
      process.stdout.write(ADVISORY);
      if (freeze) process.exit(3);
      if (jobs.length === 0) process.exit(4);
    } else if (jobs.length === 0) {
      process.exit(0);
    }
    await new Promise((r) => { setTimeout(r, pollMs); });
  }
}

function runMonitor(rawArgv) {
  const opts = { stall: 600, grace: 60, poll: 30, deadline: Math.round(DEADLINE_MS / 1000) };
  let watch = false;
  let json = false;
  let prefix = null;
  for (let i = 0; i < rawArgv.length; i++) {
    const a = rawArgv[i];
    if (a === '--watch') {
      watch = true;
    } else if (a === '--json') {
      json = true;
    } else if (a === '--folder') {
      prefix = rawArgv[++i];
      if (prefix === undefined) fail('refused: --folder requires a PREFIX argument');
      prefix = path.resolve(process.cwd(), prefix);
    } else if (a === '--stall' || a === '--grace' || a === '--poll' || a === '--deadline') {
      const val = rawArgv[++i];
      const n = Number(val);
      if (!Number.isFinite(n) || n <= 0) fail(`refused: ${a} needs a positive number of seconds, got: ${val}`);
      opts[a.slice(2)] = n;
    } else {
      fail(`refused: unknown flag '${a}'\nusage: ${MONITOR_USAGE}`);
    }
  }
  if (watch && json) fail(`refused: --json is the roster form; --watch prints event lines\nusage: ${MONITOR_USAGE}`);
  const [stallMs, graceMs, pollMs, deadlineMs] = [opts.stall, opts.grace, opts.poll, opts.deadline].map((s) => s * 1000);
  if (watch) return runWatch(prefix, stallMs, graceMs, pollMs, deadlineMs);
  const jobs = liveJobs(prefix);
  return runRoster(monitorRows(jobs, Date.now(), stallMs, graceMs, pollMs, new Map(), deadlineMs), json);
}

module.exports = {
  MONITOR_USAGE, liveJobs, mtimeOf, CPU_FLOOR_TICKS, FLOOR_POLL_MS,
  DEFAULT_DEADLINE_S, DEADLINE_MS, OUT_BANNER_BYTES, readProcStat, readProcIo,
  descendantPids, captureFile, captureSize, cpuFloor, treeSample, jobMemo,
  witness, claudeProgress, claimedBinds, codexRollout,
  opencodeBind, opencodeUpdated, opencodeProgress, progressAt,
  classify, secs, tailShort, evidenceSuffix,
  monitorRows, runRoster, runWatch, runMonitor,
};
