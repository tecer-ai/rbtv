'use strict';

// cast — the launch-handle registry — the one observable a watcher needs to find a run again.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const fs = require('fs');
const os = require('os');
const path = require('path');

const { winProcStarts, winStdoutPath } = require('./win-proc');


const HANDLES_FILE = path.join(os.homedir(), '.cast', 'handles.jsonl');
const HANDLE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

// claude encodes the launch folder into its transcript directory name.
const claudeSlug = (folder) => folder.replace(/[^a-zA-Z0-9]/g, '-');

// Field 22 of /proc/<pid>/stat (starttime, in clock ticks) — pins the pid against reuse. Fields
// 1 and 2 are pid and the parenthesized comm, so the tail after ') ' starts at field 3.
function procStart(pid) {
  if (process.platform === 'win32') return winProcStarts([pid]).get(Number(pid)) ?? null;
  try {
    const stat = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
    return Number(stat.slice(stat.lastIndexOf(')') + 2).split(' ')[19]);
  } catch { return null; }
}

// Same pin for many pids at once — Map pid → start (absent = not alive). The registry reader
// calls this once per poll. Windows has no /proc: the pin there is the process creation time
// read off one process-table query (lib/win-proc.js). Without that branch every registry row
// was written with start:null and liveJobs() dropped all of them, so `cast monitor` reported an
// empty roster while five seats were alive (observed 2026-09-09).
function procStarts(pids) {
  if (process.platform === 'win32') return winProcStarts(pids);
  return new Map(pids.map((p) => [p, procStart(p)]).filter(([, s]) => s !== null));
}

// The file this process's stdout is redirected to, or null (console, pipe, socket). Recorded on
// the handle as `out` so the monitor's witness channel and the provider-limit detector can read
// the job's stdout capture on any platform; rows without it fall back to /proc/<pid>/fd/1.
function stdoutPath() {
  let p = null;
  if (process.platform === 'win32') {
    p = winStdoutPath();
  } else {
    try { p = fs.readlinkSync('/proc/self/fd/1'); } catch { return null; }
    if (!p.startsWith('/')) return null; // pipe:[…], socket:[…]
  }
  try { return p && fs.statSync(p).isFile() ? p : null; } catch { return null; }
}

// One stderr line the caller can parse, plus a registry row for post-hoc lookup. Emitted BEFORE
// the spawn, so a child that hangs at launch is still findable.
// ponytail: append-then-prune, no lock — a concurrent launch can only lose a line during the rare
// prune rewrite; add a lockfile if the registry ever becomes load-bearing for scheduling.
function emitHandle(handle) {
  process.stderr.write(`cast: handle ${JSON.stringify(handle)}\n`);
  try {
    fs.mkdirSync(path.dirname(HANDLES_FILE), { recursive: true });
    fs.appendFileSync(HANDLES_FILE, `${JSON.stringify(handle)}\n`);
    const lines = fs.readFileSync(HANDLES_FILE, 'utf8').split('\n').filter((l) => l.trim());
    const fresh = lines.filter((l) => {
      try { return JSON.parse(l).t0 > handle.t0 - HANDLE_TTL_MS; } catch { return false; }
    });
    if (fresh.length !== lines.length) fs.writeFileSync(HANDLES_FILE, `${fresh.join('\n')}\n`);
  } catch (e) {
    process.stderr.write(`cast: handle registry write failed: ${e.message}\n`);
  }
}

// Compose argv and spawn (or dry-run). `system` is {text}|{file} plus a `wrapper` line used by
// the harnesses that carry no system prompt, or null for a bare launch.

module.exports = {
  HANDLES_FILE, HANDLE_TTL_MS, claudeSlug, procStart, procStarts, stdoutPath,
  emitHandle,
};
