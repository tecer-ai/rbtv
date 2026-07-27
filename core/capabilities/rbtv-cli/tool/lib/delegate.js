'use strict';

// Delegation — the whole reason this CLI adds no second implementation.
//
// THE CONTRACT, and it is a contract rather than an implementation choice:
// a delegated call is TRANSPARENT. The delegate's stdout, stderr and EXIT CODE
// are the caller's, unchanged and un-reinterpreted. This CLI never wraps a
// delegate's output in an envelope, never re-derives its verdict, and never
// translates its exit code.
//
// That matters most for `rbtv ignite daemon unit`. Its exit code reports whether
// the READ SUCCEEDED, never whether the daemon is HEALTHY — health is a FIELD
// (`healthy|unstable|starting|inactive|failed`). A wrapper that re-collapsed
// health into its own exit status would undo defect G-121's fix for every caller
// that arrives through this CLI. Branch on `health`; never on the exit status.
//
// Env passes through untouched, which is also how IGNITE_SENDER_TOKEN stays out
// of argv: the gateway client reads it from the environment itself and this
// process never sees, formats, or forwards its value.

const fs = require('fs');
const { spawnSync } = require('child_process');

// exec: 'direct' — the target is its own executable (its shebang runs it).
//       'node'   — the target is a Node script invoked with the running node.
function delegate(route, args) {
  if (!fs.existsSync(route.target)) {
    return {
      status: 1,
      missing: true,
      message:
        `refused: the delegate for \`rbtv ${route.prefix.join(' ')}\` is not on disk\n`
        + `  expected: ${route.target}\n`
        + '  why: this CLI wraps that surface and owns no copy of it, so with the file absent\n'
        + '       there is nothing to run — this is a broken checkout, not a usage error.\n'
        + '  fix: restore it (git checkout -- <path>) or run `rbtv doctor` for the full picture.',
    };
  }

  const [cmd, argv] = route.exec === 'node'
    ? [process.execPath, [route.target, ...args]]
    : [route.target, args];

  const res = spawnSync(cmd, argv, { stdio: 'inherit', env: process.env });

  if (res.error) {
    return {
      status: 1,
      missing: false,
      message:
        `refused: could not execute the delegate for \`rbtv ${route.prefix.join(' ')}\`\n`
        + `  target: ${route.target}\n`
        + `  cause: ${res.error.message}\n`
        + '  fix: check the file is executable (chmod +x) and run `rbtv doctor`.',
    };
  }

  // A delegate killed by a signal produced no exit code of its own. Reporting 0
  // here would be this CLI inventing a success the delegate never claimed.
  if (res.signal) {
    return {
      status: 128,
      missing: false,
      message: `delegate terminated by signal ${res.signal} — no exit status of its own; reporting 128, not success.`,
    };
  }

  return { status: res.status === null ? 1 : res.status, missing: false, message: null };
}

// Re-attach a global `--json` that was consumed before the route was known, so
// `rbtv --json ignite daemon unit` and `rbtv ignite daemon unit --json` reach the
// delegate identically. Exported as a pure function so selftest can assert it
// directly rather than infer it from a delegated call's output.
function buildDelegateArgs(rest, opts) {
  if (!opts || !opts.json) return [...rest];
  if (rest.includes('--json')) return [...rest];
  return [...rest, '--json'];
}

module.exports = { delegate, buildDelegateArgs };
