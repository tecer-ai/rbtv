'use strict';

// cast — the Windows process table. Linux code reads /proc per pid; Windows has no /proc, so
// every pin and witness sample here comes from ONE `Get-CimInstance Win32_Process` read (~1.5s,
// measured 2026-09-09) that is memoised for a second, so a poll that pins the registry and then
// samples every job's tree pays for one read, not N+1.
//
// Units match the Linux side so monitor.js floors apply unchanged: `start` is whole seconds since
// 1601 (FILETIME / 1e7 — stays under 2^53), `cpu` is in 10ms ticks (100ns / 1e5), `io` is bytes.

const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// By absolute path: a caller may hand cast a PATH that carries only node (the self-check suite
// does), and the pin must not depend on where powershell happens to be findable from.
const SYSTEM_PS = path.join(process.env.SystemRoot || 'C:\\Windows',
  'System32', 'WindowsPowerShell', 'v1.0', 'powershell.exe');
const POWERSHELL = fs.existsSync(SYSTEM_PS) ? SYSTEM_PS : 'powershell';

const TABLE_TTL_MS = 1000;
// -Property narrows the CIM fetch: 0.7s against 0.9s for the full object (measured 2026-09-09).
const QUERY = 'Get-CimInstance -ClassName Win32_Process -Property ProcessId,ParentProcessId,'
  + 'CreationDate,KernelModeTime,UserModeTime,ReadTransferCount,WriteTransferCount'
  + ' | ForEach-Object { try {'
  + ' "$($_.ProcessId) $($_.ParentProcessId) $($_.CreationDate.ToFileTimeUtc())'
  + ' $($_.KernelModeTime+$_.UserModeTime) $($_.ReadTransferCount+$_.WriteTransferCount)"'
  + ' } catch {} }';

let cached = { at: 0, table: new Map() };

// Map pid → { ppid, start, born, cpu, io }. `born` keeps FILETIME resolution for the parent check.
function procTable() {
  if (Date.now() - cached.at < TABLE_TTL_MS) return cached.table;
  const table = new Map();
  const r = spawnSync(POWERSHELL, ['-NoProfile', '-NonInteractive', '-Command', QUERY],
    { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], windowsHide: true });
  for (const line of String(r.stdout || '').split('\n')) {
    const m = /^(\d+) (\d+) (\d+) (\d+) (\d+)\s*$/.exec(line);
    if (!m) continue;
    const born = Number(m[3]);
    table.set(Number(m[1]), {
      ppid: Number(m[2]), born, start: Math.floor(born / 1e7),
      cpu: Math.floor(Number(m[4]) / 1e5), io: Number(m[5]),
    });
  }
  cached = { at: Date.now(), table };
  return table;
}

function winProcStarts(pids) {
  const table = procTable();
  const out = new Map();
  for (const p of pids) {
    const row = table.get(Number(p));
    if (row) out.set(Number(p), row.start);
  }
  return out;
}

// Same shape treeSample() builds from /proc. A parent pid can be REUSED after the parent dies, so
// a child is only a descendant when it was born after the process now holding that pid.
function winTreeSample(pid) {
  const table = procTable();
  const kids = new Map();
  for (const [p, row] of table) {
    const parent = table.get(row.ppid);
    if (!parent || parent.born > row.born) continue;
    if (!kids.has(row.ppid)) kids.set(row.ppid, []);
    kids.get(row.ppid).push(p);
  }
  const members = new Set();
  let cpu = 0;
  let io = 0;
  const queue = [Number(pid)];
  while (queue.length) {
    const p = queue.shift();
    const row = table.get(p);
    if (!row) continue;
    members.add(`${p}:${row.start}`);
    cpu += row.cpu;
    io += row.io;
    queue.push(...(kids.get(p) || []));
  }
  // running: Windows exposes no per-process run state. capSize is filled by the caller from the
  // handle's recorded `out` path (monitor.js captureSize) — fd 1 of another process is not
  // resolvable here.
  return { cpu, io, members, running: false, desc: Math.max(0, members.size - 1), capSize: null };
}

// Where THIS process's stdout goes, as a file path — or null for a console, pipe or socket. The
// caller's redirect is the job's stdout capture the witness channel reads; Windows has no
// /proc/self/fd/1, so a child powershell resolves the handle it inherits as ITS stderr (fd 2 of
// the child = fd 1 of this process) through GetFinalPathNameByHandle. ~0.5s, paid once per launch.
const STDOUT_CS = 'using System;using System.Runtime.InteropServices;using System.Text;'
  + 'public static class H{[DllImport("kernel32.dll")]public static extern IntPtr GetStdHandle(int n);'
  + '[DllImport("kernel32.dll",CharSet=CharSet.Unicode)]public static extern uint GetFinalPathNameByHandleW'
  + '(IntPtr h,StringBuilder p,uint c,uint f);public static string P(){var sb=new StringBuilder(2048);'
  + 'var n=GetFinalPathNameByHandleW(GetStdHandle(-12),sb,2048,0);return n==0?"":sb.ToString();}}';

function winStdoutPath() {
  const r = spawnSync(POWERSHELL, ['-NoProfile', '-NonInteractive', '-Command',
    `Add-Type -TypeDefinition '${STDOUT_CS}'; [H]::P()`],
  { encoding: 'utf8', stdio: ['ignore', 'pipe', 1], windowsHide: true });
  const p = String(r.stdout || '').trim().replace(/^\\\\\?\\/, '');
  return p ? p : null;
}

module.exports = { winProcStarts, winTreeSample, winStdoutPath, procTable };
