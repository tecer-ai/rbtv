'use strict';

// D59 — the filesystem containment layer. On this box `systemd-run --user` enforces cgroup
// caps but its filesystem sandbox is a SILENT no-op (workers can write anywhere). The fix is
// bubblewrap (`bwrap`) nested INSIDE the systemd-run --user transient unit: systemd keeps the
// cgroup caps + unit lifecycle; bwrap adds a mount namespace in which ONLY the session dir and
// the launch's declared editable paths exist writable, and the vault, `.rbtv/heart/`, the rbtv
// source tree, and the daemon data_root are UNREACHABLE — not merely read-only, simply never
// bound. Absence IS the mechanism; there is no deny list to drift.
//
// This module is a pure argv composer — it builds `[bwrapPath, ...flags, '--', ...argv]`. It
// never spawns anything itself; spawn.js hands the wrapped argv to the carrier, which sees an
// opaque argv. The flag ORDER is load-bearing: a tmpfs must be mounted before anything is bound
// back under it (HOME tmpfs shadows the real home; harness state + binaries + the session dir +
// editable paths are then punched back through it), and /usr is ro-bound before the /bin,/lib,…
// symlinks whose targets live under it. Do not reorder.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { SpawnError, E_FS_SANDBOX_UNAVAILABLE } = require('./errors');

// D61 — the systemd `sandbox:` properties that survive onto the transient unit WHEN bwrap wraps.
// bwrap wraps EVERY spawn (spawn.js, unconditional), so it is the SOLE filesystem layer; the
// systemd filesystem-sandbox properties are dropped from the unit for TWO independent reasons:
//   1. They are a proven no-op under the `--user` manager on this box (D59) — they confine nothing.
//   2. They ACTIVELY BREAK bwrap: any FS-mount sandbox directive (ProtectSystem, ReadWritePaths,
//      ProtectHome, PrivateTmp, …) makes systemd set up a mount namespace for the unit, which
//      denies bwrap the nested user namespace it needs — the worker dies on
//      `bwrap: No permissions to create a new namespace`.
// Empirically verified on the box (2026-07-16): ProtectSystem=strict, ReadWritePaths (even alone),
// PrivateTmp=yes, and ProtectHome=yes each break the wrap; NoNewPrivileges=yes and the cgroup
// resource caps (MemoryMax/CPUQuota/TasksMax — emitted from the `caps:` block, not `sandbox:`)
// run and still confine. This is a KEEP allowlist by design: a future FS-mount directive not
// named here is dropped (bwrap already confines — no loss), never emitted-and-breaking. The
// cgroup caps live in the separate `caps:` block and are unaffected by this set.
const BWRAP_COMPATIBLE_SANDBOX_KEYS = new Set(['NoNewPrivileges']);

// In-process PATH scan — deterministic and testable; never forks `which` (the spawn path must
// stay free of child processes just to resolve a binary). Returns the first dir on PATH holding
// an executable `name`, or null.
function scanPath(name) {
  const dirs = (process.env.PATH || '').split(':');
  for (const dir of dirs) {
    if (!dir) continue;
    const candidate = path.join(dir, name);
    try {
      fs.accessSync(candidate, fs.constants.X_OK);
      return candidate;
    } catch {}
  }
  return null;
}

// The bwrap binary itself. Not on PATH => the box cannot contain a worker; the launch REFUSES
// (D59 fail-closed). No opt-out knob: the ONLY behavior on a bwrap-less box is this typed error.
function resolveBwrapBinary() {
  const found = scanPath('bwrap');
  if (!found) {
    throw new SpawnError(
      E_FS_SANDBOX_UNAVAILABLE,
      'bwrap not found on PATH — filesystem containment unavailable; refusing to spawn (D59 fail-closed)',
      {},
    );
  }
  return found;
}

// Resolve argv[0] the same way execvp would: an absolute path is used as-is; a bare name is a
// PATH scan. Unresolvable => fail-closed (a binary that cannot be bound into the namespace
// cannot be exec'd by the worker, so the launch refuses rather than spawn a worker that would
// die on exec).
function resolveBinary(name) {
  if (path.isAbsolute(name)) return name;
  return scanPath(name);
}

// §2 harness OWN-state bind table. These are bound back over the throwaway HOME tmpfs so a real
// harness keeps its credentials/session state. `null` harness (test-sleep, bash probes) binds
// none. D26: HOME is os.homedir() at call time — never a literal.
function harnessStateBinds(harness, home) {
  if (!harness || !home) return [];
  switch (harness) {
    case 'claude':
      return [path.join(home, '.claude'), path.join(home, '.claude.json')];
    case 'codex':
      return [path.join(home, '.codex')];
    case 'opencode':
      return [
        path.join(home, '.config', 'opencode'),
        path.join(home, '.local', 'share', 'opencode'),
        path.join(home, '.cache', 'opencode'),
      ];
    // kimi keeps everything in ONE dir — measured 2026-08-07 on the ignite VPS: `~/.kimi/`
    // holds config.toml, credentials, device_id, kimi.json and logs, and no `~/.config/kimi`,
    // `~/.local/share/kimi` or `~/.cache/kimi` exists. Without this bind a caged kimi seat sees
    // the throwaway HOME tmpfs and has no credentials at all — which is what it saw while the
    // ladder returned a null harness for kimi, so this lands WITH the table row, not after it.
    case 'kimi':
      return [path.join(home, '.kimi')];
    default:
      return [];
  }
}

function isUnderUsr(p) {
  return p === '/usr' || p.startsWith('/usr/');
}

// §2 generic binary rule (EVERY spawn): ro-bind argv[0]'s resolved path so the worker can exec
// it. /usr is already ro-bound wholesale above, so anything already under it is skipped. A
// symlinked binary (e.g. `claude` -> H/.local/share/claude/versions/<v>/claude) additionally
// binds its realpath's directory so the real ELF is reachable at its resolved location.
function binaryBindFlags(binPath) {
  const flags = [];
  if (isUnderUsr(binPath)) return flags;
  flags.push('--ro-bind', binPath, binPath);
  let real;
  try {
    real = fs.realpathSync(binPath);
  } catch {
    return flags;
  }
  if (real !== binPath) {
    const dir = path.dirname(real);
    if (!isUnderUsr(dir)) flags.push('--ro-bind', dir, dir);
  }
  return flags;
}

// Compose the bwrap argv. Every bind mounts the path AT ITS OWN PATH (SRC == DEST) so the
// worker sees real paths: resolveWorkdir()'s boundary, the harness config paths, and the
// profile's own argv stay valid inside the namespace.
//
//   { argv, workdir, editablePaths = [], promptFile = null, harness = null, maskPaths = [],
//     seatBinds = null }
// -> [bwrapPath, ...flags (in load-bearing order), '--', ...argv]
//
// TASK 7.11 — `seatBinds`. v1 had ONE RW opening (the session dir) and one input shape: a flat
// list of paths, every one of them `--bind`. A seat's writable set cannot be expressed that way —
// it is an ORDERED, TYPED stack in which a ro-bind of a parent, a tmpfs that erases a subtree,
// and a bind of a leaf each deliberately shadow what came before. cage.js composes that stack and
// asserts the invariant over it; this function only emits it.
//
// When `seatBinds` is supplied it REPLACES the workdir + editablePaths block rather than adding
// to it, and that is load-bearing rather than tidy: the seat stack ro-binds the GOAL directory,
// which sits ABOVE the workdir. Emitting `--bind workdir` first and the stack after would mount
// the read-only goal tree straight over the seat's own RW opening, and the seat would launch into
// a read-only home. There is no ordering in which both blocks can be emitted — hence a
// replacement, not an addition.
function buildBwrapArgv({ argv, workdir, editablePaths = [], promptFile = null, harness = null, maskPaths = [], seatBinds = null }) {
  const bwrapPath = resolveBwrapBinary();
  const home = os.homedir();

  const out = [
    '--die-with-parent',
    '--unshare-all',
    '--share-net',                       // workers need the LLM APIs; only mount/pid/ipc/uts/cgroup ns are private
    '--proc', '/proc',
    '--dev', '/dev',
    '--tmpfs', '/tmp',
    '--tmpfs', '/run',                   // masks /run/user/<uid>/bus — the user systemd bus MUST be unreachable (leg f)
    '--ro-bind-try', '/run/systemd/resolve', '/run/systemd/resolve', // /etc/resolv.conf symlinks here on Ubuntu
    '--ro-bind', '/usr', '/usr',
    '--symlink', 'usr/bin', '/bin',
    '--symlink', 'usr/lib', '/lib',
    '--symlink', 'usr/lib64', '/lib64',
    '--symlink', 'usr/sbin', '/sbin',
    '--ro-bind', '/etc', '/etc',
  ];

  // Mask senders-registry dirs that live under the ro /etc (the ro-bind already hides their
  // contents; a tmpfs over them also keeps a future relocated registry empty in-namespace).
  for (const p of maskPaths) {
    if (fs.existsSync(p)) out.push('--tmpfs', p);
  }

  // Writable throwaway HOME: everything real under it is unreachable unless bound back below.
  out.push('--tmpfs', home);

  // Harness OWN state — bound back over the HOME tmpfs.
  for (const p of harnessStateBinds(harness, home)) {
    out.push('--bind-try', p, p);
  }

  // Harness/worker binary — bound back over the HOME tmpfs when it lives there.
  const binPath = resolveBinary(argv[0]);
  if (!binPath) {
    throw new SpawnError(
      E_FS_SANDBOX_UNAVAILABLE,
      `worker binary ${argv[0]} not resolvable on PATH — cannot bind it into the sandbox; refusing to spawn (D59 fail-closed)`,
      { binary: argv[0] },
    );
  }
  out.push(...binaryBindFlags(binPath));

  if (seatBinds && seatBinds.length > 0) {
    // 7.11 SEAT PATH — the composed stack, in the order cage.js produced it. Emitted verbatim:
    // this function does not sort, dedupe or "fix" the sequence, because every reordering here is
    // a silent change to what the seat can write, and the sequence has already been asserted
    // against the ground-truth invariant by the composer.
    out.push(...seatBinds);
  } else {
    // v1 / ticker path, unchanged. The ONE unconditional RW wall opening — the per-execution
    // session dir — plus the launch's declared editable paths (the test folder, when a launch
    // declares one).
    out.push('--bind', workdir, workdir);
    for (const p of editablePaths) {
      out.push('--bind', p, p);
    }
  }

  // The prompt file (when the carriage is file) — ro.
  if (promptFile) {
    out.push('--ro-bind', promptFile, promptFile);
  }

  out.push('--chdir', workdir);
  out.push('--');
  // Exec the RESOLVED, sandbox-bound binary path (not the bare argv[0]): bwrap's in-namespace
  // execvp searches the sandbox PATH, which need not contain argv[0]'s dir. binPath is ro-bound
  // at SRC==DEST above, so it is valid inside the sandbox.
  out.push(binPath, ...argv.slice(1));

  return [bwrapPath, ...out];
}

module.exports = { resolveBwrapBinary, buildBwrapArgv, BWRAP_COMPATIBLE_SANDBOX_KEYS };
