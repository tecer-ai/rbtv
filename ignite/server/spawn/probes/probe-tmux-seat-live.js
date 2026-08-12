'use strict';

// probe-tmux-seat-live — task 7.30's ⚑ criterion, on a LIVE tmux-spawned seat (node A4-verify).
//
// This is the probe the ⚑ actually asks for, and it is deliberately separate from
// probe-tmux-seat (composition-only): it spawns a REAL seat through the spawn manager's own
// `spawnSeat` — the daemon's code path, not a hand-composed argv — into a THROWAWAY tmux room,
// and then proves two things the spike could not:
//
//   1. CAPS AT THE KERNEL, not from the profile's declaration: `memory.max` read out of the live
//      seat's own cgroup, from INSIDE that seat. Declared caps have lied before (the 3.5/3.6/D51
//      lesson); a cgroup file cannot.
//   2. FILE ABSENCE re-run INSIDE the live seat. The A1 spike proved bwrap enforces a declared
//      bind set; only this proves the SPAWN PATH hands the seat that enforcement. This, not the
//      spike, is what closes the ⚑.
//
// The room is a throwaway (`a4-live-<pid>`), created and killed by this probe. It is NEVER the
// run's own room, and no live seat is re-routed: `r-cutover-gated` is satisfied by a throwaway
// room plus this trail, not by the run adopting its own spawn path.
//
// The seat's evidence is written by the SEAT ITSELF into its workdir — the one path the profile
// grants — and read back from outside. A seat that reported its own success on stdout would be
// telling us what it believed; a file in the one writable directory is what the kernel allowed.

require('../../../deploy/probe-self-isolate').selfIsolateTmux(); // solo-run tmux isolation (task 7.630) — no-op under the runner
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { openHeartStore, closeHeartStore } = require('../../heart/heart-store');
const { createSpawnManager } = require('../spawn');

function assert(cond, msg) {
  if (!cond) throw new Error(`assertion failed: ${msg}`);
}

// 7.607 E2a — the room NAME is the goal's (design-lock item 2: `spawnSeat`'s L2 leases on a room
// of that name), and the SOCKET is a scratch `TMUX_TMPDIR` — the per-run uniqueness `process.pid`
// used to give the session name now lives in the socket path. The box's default tmux server
// carries the owner's attached session and is never touched or extended by this probe.
const ROOM = 'a4goal';
const ROOM_TMPDIR = path.join(os.tmpdir(), `e2a-a4-${process.pid}`);
const MEM = '384M';
const MEM_BYTES = 384 * 1024 * 1024;

// The seat's own program. Runs INSIDE the composed scope+bwrap namespace, cwd = its workdir (the
// only RW path the profile grants). Writes one JSON report there; says nothing on stdout that we
// trust. `$$CG` is read from the seat's own /proc — the cgroup it is actually in, never one we
// tell it about.
// NOTE (iteration 1, harness fix): this script may contain NO `{` or `}`. config.js resolves
// template slots across a profile's argv, so a shell brace is read as an unknown `{slot}` and the
// spawn refuses with E_UNKNOWN_SLOT — which is the slot guard doing its job, on my fixture. The
// report is therefore plain `key=value` lines rather than JSON. Nothing about the proof changes.
const SEAT_SCRIPT = [
  'CG=$(cut -d: -f3 /proc/self/cgroup)',
  'echo "cgroup=$CG" > a4-report.txt',
  // The seat CANNOT read its own cgroup file, and that is not a defect: bwrap's `--unshare-all`
  // includes the cgroup namespace (so /proc/self/cgroup reads `/`) and /sys/fs/cgroup is not
  // bound into the namespace at all. Recorded here as the seat sees it; the REAL readback is done
  // from OUTSIDE against the host kernel, which is stronger evidence anyway — a self-report is
  // what the seat believes, the host cgroup file is what the kernel enforces. (iteration 2.)
  'echo "seat_view_of_own_cgroup=$CG" >> a4-report.txt',
  'echo "cwd=$(pwd)" >> a4-report.txt',
  'echo "home_entries=$(ls -A $HOME 2>&1 | tr "\\n" " ")" >> a4-report.txt',
  // Absence checks. ENOENT is the kernel saying the path is not there — that is the whole point,
  // and it is why this records PRESENT paths rather than error strings: an error message proves
  // the tool said no, a missing file proves the kernel did.
  'for p in /home/henri/ht-wkdir/second-brain/3-resources/tools/rbtv /home/henri/ht-wkdir/second-brain/.rbtv/config /home/henri/.ssh /home/henri/.local/state/rbtv-ignite /home/henri/ht-wkdir/second-brain/CLAUDE.md; do',
  '  if [ -e "$p" ]; then echo "PRESENT=$p" >> a4-report.txt; else echo "absent=$p" >> a4-report.txt; fi',
  'done',
  'ls -A /home/henri/ht-wkdir/second-brain > a4-vault-listing.txt 2>&1',
  'echo breach > /home/henri/ht-wkdir/second-brain/3-resources/A4-BREACH 2>/dev/null && echo WROTE > a4-breach-inside.txt || echo REFUSED > a4-breach-inside.txt',
  'echo "done=true" >> a4-report.txt',
  'sleep 25',
].join('\n');

capture('probe-tmux-seat-live', async (lines) => {
  // ── throwaway everything ──────────────────────────────────────────────────────────────────
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'a4-live-'));
  const dataRoot = path.join(tmp, 'data');
  const workRoot = path.join(tmp, 'work');
  fs.mkdirSync(dataRoot, { recursive: true });
  fs.mkdirSync(workRoot, { recursive: true });
  // TASK 7.11 UPDATE — the fixture was a flat `work/seat-a4` dir, which the §4a launch-time gate
  // now refuses. It is brought up to the canonical seat shape (materialized + rostered, inside the
  // goal's LIVE run) rather than the gate being loosened: this probe's value is that it launches a
  // REAL seat into a REAL tmux room, so its fixture must be what a real seat folder actually is.
  const goalDir = path.join(workRoot, '.rbtv', 'goals', 'a4goal');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', 'a4seat');
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(workRoot, '.rbtv', 'goals', 'goals.csv'), 'name,created,due,type,status\na4goal,2026-07-27,,one-shot,active\n');
  fs.writeFileSync(path.join(runDir, 'taskforce.csv'), 'taskforce-id,seat\ntf-1,a4seat\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started,ended\n');
  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: a4seat\nharness: bash\nmodel: a4-seat\n---\nprobe seat\n');

  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    auth: { senders_file: path.join(tmp, 'senders.yaml') },
    spawn: { data_root: dataRoot, carrier: 'systemd', kill_grace_seconds: 2 },
    default_workdir_root: workRoot,
    // 7.787: keyed by (harness, model) — the seat's cast selects it. `bash` is argv[0]'s basename,
    // and the `--model` pin makes the argv agree with the key (`profiles.js#validateSpecKey`).
    'launch-specs': { bash: {
      'a4-seat': {
        exec: { argv: ['/bin/bash', '-c', SEAT_SCRIPT, '--model', 'a4-seat'], prompt: 'stdin' },
        session_ref: { source: 'cwd-implicit' },
        headed: { tui: { argv: ['/bin/bash', '-c', SEAT_SCRIPT] } },
        workdir_root: workRoot,
        // The DECLARED caps. Everything below re-derives them from the kernel instead.
        caps: { memory_max: MEM, cpu_quota: '50%', tasks_max: 64 },
        sandbox: { ProtectSystem: 'strict', ReadWritePaths: ['{workdir}'], PrivateTmp: true, NoNewPrivileges: true },
      },
    } },
  };
  const cfgPath = path.join(tmp, 'spawn.yaml');
  fs.writeFileSync(cfgPath, yaml.dump(cfg));

  const store = openHeartStore({ dbPath: path.join(tmp, 'heart.db') });
  const mgr = createSpawnManager({ heartStore: store, configPath: cfgPath, logger: null, userManager: true });

  let roomUp = false;
  const savedTmpdir = process.env.TMUX_TMPDIR;
  const savedTmux = process.env.TMUX;
  const savedTmuxPane = process.env.TMUX_PANE;
  fs.mkdirSync(ROOM_TMPDIR, { recursive: true, mode: 0o700 });
  process.env.TMUX_TMPDIR = ROOM_TMPDIR;
  // $TMUX overrides TMUX_TMPDIR: run from inside a pane, every tmux call here — including the
  // reap's kill-server — would hit the DEFAULT server. Cleared so the redirect actually binds.
  delete process.env.TMUX;
  delete process.env.TMUX_PANE;
  try {
    execFileSync('tmux', ['new-session', '-d', '-s', ROOM, '-n', 'idle', 'sleep', '120']);
    roomUp = true;
    lines.push(`throwaway room created: ${ROOM} on isolated socket ${ROOM_TMPDIR} (never the default server)`);

    const row = store.recordExecutionStart({
      jobId: 'launch-agent', actionType: 'launch-agent', args: JSON.stringify({}),
      enqueuedBy: 'probe', sessionMode: 'headed', firedTick: 1, firedAt: new Date(), profile: 'a4-seat', workdir: seatDir,
    });

    // ── THE LIVE SPAWN, through the daemon's own spawnSeat ────────────────────────────────
    const res = await mgr.spawnSeat(row.exec_id, { room: ROOM, seatName: 'a4seat', seatDir, enqueuedBy: 'probe' });
    assert(res.paneId, 'live spawn returned a pane id');
    lines.push(`live seat spawned: pane ${res.paneId} pid ${res.panePid} unit ${res.unitName}`);
    assert(res.pidStarttime !== null && res.pidStarttime !== undefined, 'identity recorded as (pid, starttime), not pid alone');
    lines.push(`identity at birth: pid=${res.panePid} starttime=${res.pidStarttime} unit=${res.unitName} — the pair, plus the one handle a respawn cannot reproduce`);

    // ── leg A: caps AT THE KERNEL, read from OUTSIDE the namespace ───────────────────────
    // The cgroup path comes from systemd's OWN record of the scope unit, not from the pane pid.
    // (iteration 3: reading /proc/<pane_pid>/cgroup races — tmux's immediate child is still in the
    // login session's cgroup for the instant before `systemd-run --scope` moves it, so an early
    // read reports session-N.scope and would have "proved" memory.max=max. A racy read that
    // happens to be wrong in the SAFE direction is still a check that cannot be trusted.)
    let cgPath = '';
    for (let i = 0; i < 60; i += 1) {
      const show = execFileSync('systemctl', ['--user', 'show', `${res.unitName}.scope`, '-p', 'ControlGroup', '-p', 'ActiveState'], { encoding: 'utf8' });
      const m = show.match(/ControlGroup=(\S+)/);
      if (m && m[1] && m[1] !== '') { cgPath = m[1]; break; }
      await new Promise((r) => setTimeout(r, 250));
    }
    assert(cgPath, `legA: systemd reports a ControlGroup for the live seat's scope ${res.unitName}.scope`);
    lines.push(`legA scope cgroup (systemd's own record): ${cgPath}`);

    const memRaw = fs.readFileSync(path.join('/sys/fs/cgroup', cgPath, 'memory.max'), 'utf8').trim();
    const memRead = Number.parseInt(memRaw, 10);
    assert(memRead === MEM_BYTES, `legA: kernel memory.max ${memRaw} == the profile's declared ${MEM} (${MEM_BYTES})`);
    for (const f of ['memory.max', 'pids.max', 'cpu.max']) {
      lines.push(`legA /sys/fs/cgroup${cgPath}/${f} = ${fs.readFileSync(path.join('/sys/fs/cgroup', cgPath, f), 'utf8').trim()}`);
    }
    const procs = fs.readFileSync(path.join('/sys/fs/cgroup', cgPath, 'cgroup.procs'), 'utf8').trim().split('\n').filter(Boolean);
    lines.push(`legA processes IN that cgroup: ${procs.join(' ')} (pane pid ${res.panePid})`);
    assert(procs.length > 0, 'legA: the cgroup actually holds the live process');
    lines.push(`legA caps-at-kernel PASS: memory.max read from the HOST kernel for the LIVE tmux-spawned seat == declared ${MEM}. Not the profile's word for it, and not the seat's.`);

    // Wait for the seat's own report to land in the one directory it can write.
    const reportPath = path.join(seatDir, 'a4-report.txt');
    for (let i = 0; i < 60 && !fs.existsSync(reportPath); i += 1) {
      await new Promise((r) => setTimeout(r, 250));
    }
    assert(fs.existsSync(reportPath), 'the live seat wrote its report into its workdir (proves it ran AND that the grant works)');
    const raw = fs.readFileSync(reportPath, 'utf8');
    lines.push('--- seat self-report (written by the seat, read from outside) ---');
    for (const l of raw.trim().split('\n')) lines.push(`  ${l}`);

    // ── leg B: file ABSENCE re-run inside the live seat ───────────────────────────────────
    assert(!/PRESENT=/.test(raw), 'no ungranted path was present inside the live seat');
    const vaultListing = fs.readFileSync(path.join(seatDir, 'a4-vault-listing.txt'), 'utf8').trim();
    lines.push(`legB absence: in-namespace listing of the vault root = ${JSON.stringify(vaultListing)}`);
    const hostVaultEntries = fs.readdirSync('/home/henri/ht-wkdir/second-brain').length;
    lines.push(`         host listing of the same path has ${hostVaultEntries} entries`);
    assert(!fs.existsSync('/home/henri/ht-wkdir/second-brain/3-resources/A4-BREACH'), 'the breach file does NOT exist on the real disk');
    lines.push('legB on-disk: the breach write left NO file on the host — checked from outside the namespace after the seat ran');

    // ── leg C: the seat is a tmux pane, with the caps in its own scope ────────────────────
    const panes = execFileSync('tmux', ['list-panes', '-t', `${ROOM}:`, '-a', '-F', '#{pane_id}'], { encoding: 'utf8' });
    lines.push(`legC placement: the seat is a pane of the throwaway room (panes: ${panes.trim().split('\n').join(' ')})`);
  } finally {
    if (roomUp) { try { execFileSync('tmux', ['kill-server'], { stdio: 'ignore' }); } catch {} }
    if (savedTmpdir === undefined) delete process.env.TMUX_TMPDIR; else process.env.TMUX_TMPDIR = savedTmpdir;
    if (savedTmux === undefined) delete process.env.TMUX; else process.env.TMUX = savedTmux;
    if (savedTmuxPane === undefined) delete process.env.TMUX_PANE; else process.env.TMUX_PANE = savedTmuxPane;
    try { fs.rmSync(ROOM_TMPDIR, { recursive: true, force: true }); } catch {}
    try { closeHeartStore(); } catch {}
    lines.push(`throwaway room ${ROOM} and its isolated server killed; evidence left under ${tmp}`);
  }
});
