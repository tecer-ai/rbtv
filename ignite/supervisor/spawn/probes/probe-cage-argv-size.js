'use strict';

// probe-cage-argv-size — THE COMPOSED SEAT COMMAND MUST NOT SCALE WITH THE HOST.
//
// The defect this probe exists to keep dead: `cage.js`'s auto-memory mask (bound (iii)) emitted
// one `--tmpfs` per existing `{home}/.claude/projects/*/memory`. That is argv proportional to how
// much OTHER work has happened on the box — 696 stores / 68,503 bytes measured here on
// 2026-08-24 — and `tmux new-window` refuses a command over roughly 16 KB (measured on this box:
// 16000 accepted, 20000 refused). Under universal caging EVERY seat-door launch died
// `E_CARRIER_FAILED: command too long`, and a clean `HOME` made the error vanish. The tell was
// that the cage was fine and the COUNT was the defect.
//
// So the assertion here is not "the current box happens to fit". It is that the composed tmux
// command is CONSTANT in the number of memory stores — measured against a synthetic home holding
// 1000 of them, which is more than the box has ever had. A regression that re-introduces
// per-store argv fails leg 2 by arithmetic long before any real host grows big enough to fail a
// launch, which is the whole point: the previous shape only went red once the box got busy.
//
// Leg 3 is the other half. An O(1) mask that achieved its constancy by masking LESS would pass
// legs 1 and 2 and silently open the store, so the isolation contract is measured the way
// probe-ancestor-mask measures everything else: by what a real bwrap process actually sees.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture, fixtureRoot } = require('./lib');
const { composeSeatCage, composeAncestorMasks, specToBwrapFlags, composeMemoryMask, projectStoreSlug } = require('../cage');
const { composeSeatSpawn } = require('../tmux');

// Well under the ~16 KB tmux ceiling AND under it by enough that the margin is not the thing
// being tested — a mask that is O(1) lands in the low hundreds of bytes, so 8 KB is a wall the
// fixed cost can drift a long way toward before anyone has to look at it again.
const CEILING = 8 * 1024;

const TEMPLATE = [
  'ro-bind:{grant:readRoot}',
  'ro-bind:{goalDir}',
  'tmpfs:{goalDir}/seats',
  'bind:{seatDir}',
];

function assert(cond, msg) {
  if (!cond) throw new Error(`assertion failed: ${msg}`);
}

// A synthetic HOME carrying `count` project stores, every one of them with a `memory/` dir — the
// exact shape the old mask emitted one flag apiece for. Names are long and path-like because the
// real slugs are (`-home-henri-ht-wkdir-second-brain-…`): a fixture of short names would
// understate the argv the defect actually produced.
function synthHome(root, count) {
  const home = path.join(root, 'home');
  const projects = path.join(home, '.claude', 'projects');
  for (let i = 0; i < count; i++) {
    fs.mkdirSync(path.join(projects, `-home-agent-ht-wkdir-second-brain-goals-synthetic-store-${i}`, 'memory'), { recursive: true });
  }
  return home;
}

function fixture(root) {
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'testgoal');
  const seatDir = path.join(goalDir, 'seats', 'mine');
  fs.mkdirSync(path.join(goalDir, 'seats'), { recursive: true });
  fs.mkdirSync(seatDir, { recursive: true });
  return { ws, goalDir, seatDir };
}

// The FULL composition a seat-door launch hands tmux: seat cage -> ancestor masks -> bwrap ->
// systemd-run scope -> tmux new-window. Measured as one string because that is what tmux's
// command-length limit is applied to.
function tmuxCommandFor(f, home) {
  const spec = composeSeatCage({
    seatBinds: TEMPLATE,
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
    grants: [{ readRoot: f.ws }],
  });
  const mask = composeAncestorMasks(spec, {
    workspaceRoot: f.ws,
    launchFolder: f.seatDir,
    home,
  });
  const { tmuxArgv } = composeSeatSpawn({
    room: 'probe-room',
    windowName: 'probe-seat',
    sessionId: '0123abcd-0000-0000-0000-000000000000',
    workdir: f.seatDir,
    harnessArgv: ['/usr/bin/env', 'true'],
    caps: { memory_max: '512M', cpu_quota: '100%', tasks_max: 64 },
    seatBinds: [...specToBwrapFlags(spec), ...mask.flags],
  });
  return { command: tmuxArgv.join(' '), mask };
}

capture('probe-cage-argv-size', async (lines) => {
  const root = fixtureRoot('probe-argv-size-');
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const f = fixture(root);

    // ── leg 1: 1000 synthetic memory stores, and the tmux command still fits ──────────────────
    const big = synthHome(root, 1000);
    const bigCmd = tmuxCommandFor(f, big);
    leg('1', `the composed tmux command stays under ${CEILING} bytes with 1000 memory stores`,
      bigCmd.command.length < CEILING,
      `stores=1000 command_bytes=${bigCmd.command.length} ceiling=${CEILING} memory_masks=${bigCmd.mask.masked.memory}`);

    // ── leg 2: and it is the SAME size at 10 stores — constant, not merely small ──────────────
    // Seven argv entries, pinned: `--tmpfs {projects}` + `--bind {own} {own}` + `--tmpfs
    // {own}/memory`. Pinning the number, not just its constancy, is what catches a "fix" that
    // trades per-store flags for per-something-else flags.
    // The arithmetic that makes this a regression alarm rather than a headroom check: the old
    // shape grew by ~90 bytes per store, so 10 -> 1000 moved the command by ~89 KB.
    const small = synthHome(root, 10);
    const smallCmd = tmuxCommandFor(f, small);
    // The two homes differ in path only by their own fixture prefix; compare the memory-mask
    // flag COUNT (exactly what scaled) and the per-store delta.
    const bigMask = composeMemoryMask(big, f.seatDir);
    const smallMask = composeMemoryMask(small, f.seatDir);
    const delta = Math.abs(bigCmd.command.length - smallCmd.command.length);
    leg('2', 'the mask is O(1) in the store count — same flag count at 10 stores and at 1000',
      bigMask.flags.length === smallMask.flags.length && bigMask.flags.length === 7 && delta === 0,
      `flags@10=${smallMask.flags.length} flags@1000=${bigMask.flags.length} `
      + `bytes@10=${smallCmd.command.length} bytes@1000=${bigCmd.command.length} delta=${delta}`);

    // ── leg 3: constancy did not buy itself by opening the store ──────────────────────────────
    // Real bwrap, read back from outside, exactly as probe-ancestor-mask leg (e) does it: the
    // seat's OWN store keeps its session transcript (the ruling's scope line — `--resume` must
    // survive the memory mask), its own `memory/` is empty, and a FOREIGN store is not there at
    // all. Foreign absence is stronger than the per-store mask this replaced, which left every
    // other project's transcripts readable in-cage.
    const projects = path.join(big, '.claude', 'projects');
    const own = path.join(projects, projectStoreSlug(f.seatDir));
    fs.mkdirSync(path.join(own, 'memory'), { recursive: true });
    fs.writeFileSync(path.join(own, 'sess.jsonl'), 'OWN-TRANSCRIPT\n');
    fs.writeFileSync(path.join(own, 'memory', 'm.md'), 'OWN-MEMORY\n');
    const foreign = path.join(projects, '-home-agent-ht-wkdir-second-brain-goals-synthetic-store-0');
    fs.writeFileSync(path.join(foreign, 'sess.jsonl'), 'FOREIGN-TRANSCRIPT\n');
    fs.writeFileSync(path.join(foreign, 'memory', 'm.md'), 'FOREIGN-MEMORY\n');

    const flags = composeMemoryMask(big, f.seatDir).flags;
    const argv = ['--dev-bind', '/', '/', ...flags, '--', 'bash', '-c',
      `echo "own-tx=[$(cat ${own}/sess.jsonl 2>/dev/null)]"; `
      + `echo "own-mem=[$(ls ${own}/memory 2>/dev/null | tr '\\n' ' ')]"; `
      + `echo "foreign=[$(ls ${foreign} 2>/dev/null | tr '\\n' ' ')]"; `
      + `echo "root=[$(ls ${projects} 2>/dev/null | tr '\\n' ' ')]"`];
    let seen;
    try {
      seen = execFileSync('bwrap', argv, { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] });
    } catch (err) {
      seen = ((err.stdout || '') + (err.stderr || '')).toString();
    }
    leg('3', "the own store's transcript survives while its memory and every foreign store do not",
      /own-tx=\[OWN-TRANSCRIPT\]/.test(seen) && /own-mem=\[\]/.test(seen)
      && /foreign=\[\]/.test(seen) && !/FOREIGN/.test(seen),
      `in-cage: ${JSON.stringify(seen.trim())}`);

    // ── leg 4: no projects store on the box at all -> no flags, not a crash ───────────────────
    // The absent-path discipline this file states for every other mask: masking a path nothing
    // bound would only make bwrap mkdir a mountpoint over nothing.
    const bare = path.join(root, 'bare-home');
    fs.mkdirSync(bare, { recursive: true });
    const bareMask = composeMemoryMask(bare, f.seatDir);
    leg('4', 'a home with no project store composes no memory flags at all',
      bareMask.flags.length === 0 && bareMask.masks === 0 && bareMask.ownStore === null,
      `flags=${bareMask.flags.length} masks=${bareMask.masks} ownStore=${bareMask.ownStore}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`cage-argv-size probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch {}
  }
});
