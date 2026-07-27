'use strict';

const { execFileSync } = require('node:child_process');
const {
  SpawnError,
  E_PINNED_FLAG_ABSENT,
  E_PREFLIGHT_UNAVAILABLE,
} = require('./errors');

// The pinned-flag pre-flight (task 7.42; #d-profile-source-unification (2) — "the resolver
// absorbs orchestration's pinned-flag pre-flight ... so the daemon gains a protection it lacked").
//
// WHY IT EXISTS: a profile pins flags against an installed CLI that upgrades underneath it. When
// `claude` renames `--effort`, the profile keeps emitting the old flag and the harness either
// errors late, inside a spawned session nobody is watching, or — worse — ignores it and runs at a
// different effort than the run believes. Verifying each pinned flag against the binary's LIVE
// `--help` turns that into a refusal before dispatch.
//
// ⚠ IT IS NOT WIRED INTO THE DAEMON'S SPAWN PATH, and that is deliberate, not an omission.
// Task 7.42's criterion is that the daemon's existing spawn behaviour is BYTE-UNCHANGED; adding a
// fork-and-parse to every spawn would change it, on the live daemon, in the same change that
// moves the module. It is built, exported, and probed here; wiring it is the consumers' act
// (7.43 / 7.54) or a follow-on for the daemon. Stated rather than left to be discovered.

const DEFAULT_TIMEOUT_MS = 10_000;

// A PINNED FLAG is an argv element the PROFILE wrote that looks like an option. Caller values can
// never be flags by construction (resolveProfile fills declared positions and never appends), so
// scanning the resolved argv is safe — but the scan is over the TEMPLATE-derived elements, and a
// filled slot value is skipped: a workdir that happens to start with `-` is a path, not a flag.
function pinnedFlagsOf(templateArgv) {
  const flags = [];
  for (const element of templateArgv) {
    if (typeof element !== 'string') continue;
    if (!element.startsWith('-')) continue;
    // `{slot}`-bearing elements are caller-filled positions, not pinned flags.
    if (element.includes('{')) continue;
    // `--flag=value` pins the flag, not the value.
    flags.push(element.split('=')[0]);
  }
  return flags;
}

// Read the installed CLI's live `--help`. Failure to READ is its own typed error: "the flag is
// gone" and "I could not look" are different facts, and collapsing them would let an unrunnable
// binary read as a clean bill of health (this run has filed that shape five times tonight).
function readHelp(binary, opts = {}) {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, helpArgs = ['--help'] } = opts;
  try {
    return execFileSync(binary, helpArgs, {
      encoding: 'utf8',
      timeout: timeoutMs,
      stdio: ['ignore', 'pipe', 'pipe'],
      // Many CLIs print help to stderr and exit non-zero; both streams are captured and a
      // non-zero exit is NOT by itself a failure to read.
    });
  } catch (err) {
    const captured = `${err.stdout || ''}${err.stderr || ''}`;
    if (captured.trim().length > 0) return captured;
    throw new SpawnError(
      E_PREFLIGHT_UNAVAILABLE,
      `pre-flight could not read \`${binary} ${helpArgs.join(' ')}\`: ${err.message}`,
      { binary, reason: err.code || err.message },
    );
  }
}

// Verify every pinned flag of a resolved profile against the installed binary's live help.
// Returns the checked set on success; throws E_PINNED_FLAG_ABSENT naming the first missing flag.
function preflightPinnedFlags(resolved, opts = {}) {
  const templateArgv = opts.templateArgv || resolved.argv;
  if (!Array.isArray(templateArgv) || templateArgv.length === 0) {
    throw new SpawnError(E_PREFLIGHT_UNAVAILABLE, 'pre-flight needs a non-empty argv', { profile: resolved && resolved.name });
  }
  const binary = templateArgv[0];
  const flags = pinnedFlagsOf(templateArgv);
  if (flags.length === 0) return { binary, checked: [], missing: [] };

  const help = readHelp(binary, opts);
  const missing = flags.filter((flag) => !help.includes(flag));
  if (missing.length > 0) {
    throw new SpawnError(
      E_PINNED_FLAG_ABSENT,
      `profile ${resolved.name} pins ${missing.join(', ')}, absent from the installed ` +
      `\`${binary} --help\` — the CLI changed under the profile; refusing before dispatch`,
      { profile: resolved.name, binary, missing, checked: flags },
    );
  }
  return { binary, checked: flags, missing: [] };
}

module.exports = { preflightPinnedFlags, pinnedFlagsOf, readHelp };
