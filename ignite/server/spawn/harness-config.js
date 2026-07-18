'use strict';

// D58(4) — the ADVISORY second belt. At spawn, materialize into the worker's launch (session)
// dir a SIMPLE harness-local write-restraint config for whichever of the three harnesses
// (claude, codex, opencode) the profile launches. Layer honesty (D58, POC finding 3): the KERNEL
// sandbox is the LOAD-BEARING layer and the acceptance test grades IT; this config only expresses
// intent to a harness that honors a local config and NEVER substitutes for the kernel confinement.
// It restrains writes to the launch dir + the editable paths the launch's kernel sandbox already
// grants (the designated test folder, when a launch declares it). Minimal: one file per harness,
// no wrappers, no new subsystems.

const fs = require('node:fs');
const path = require('node:path');

// The harness is identified from the profile's own exec argv[0] (D23: reuse the profile's words,
// never mint a parallel registry). sleep/test profiles carry no harness and get no config.
function harnessOf(profile) {
  const argv0 = profile && profile.exec && profile.exec.argv && profile.exec.argv[0];
  if (argv0 === 'claude') return 'claude';
  if (argv0 === 'codex') return 'codex';
  if (argv0 === 'opencode') return 'opencode';
  return null;
}

function materializeHarnessConfig({ sessionDir, profile, editablePaths = [] }) {
  const kind = harnessOf(profile);
  if (!kind) return { harness: null, written: null, enforceable: false };

  const roots = Array.from(new Set([sessionDir, ...editablePaths].filter(Boolean)));

  if (kind === 'claude') {
    // Claude Code reads `.claude/settings.json` from its working directory. By default it writes
    // only within the working dir; `permissions.additionalDirectories` extends that to the
    // declared editable paths. Advisory — the kernel sandbox is authoritative.
    const dot = path.join(sessionDir, '.claude');
    fs.mkdirSync(dot, { recursive: true, mode: 0o700 });
    const settings = { permissions: { additionalDirectories: editablePaths } };
    const p = path.join(dot, 'settings.json');
    fs.writeFileSync(p, JSON.stringify(settings, null, 2));
    return { harness: 'claude', written: p, enforceable: true, note: 'Claude Code honours it (advisory); kernel authoritative' };
  }

  if (kind === 'codex') {
    // Codex runs `--sandbox danger-full-access` in its profile (the .git-write erratum), so
    // codex's OWN sandbox is OFF and NO local config can restrain its writes. Written for
    // transparency only: the kernel systemd sandbox is the SOLE enforcement.
    const dot = path.join(sessionDir, '.codex');
    fs.mkdirSync(dot, { recursive: true, mode: 0o700 });
    const toml = [
      '# ADVISORY ONLY. This profile runs --sandbox danger-full-access (.git-write erratum);',
      "# codex's own sandbox is OFF. Kernel systemd confinement is the SOLE enforcement.",
      'approval_policy = "never"',
      `# kernel-enforced editable roots: ${roots.join(', ')}`,
      '',
    ].join('\n');
    const p = path.join(dot, 'config.toml');
    fs.writeFileSync(p, toml);
    return { harness: 'codex', written: p, enforceable: false, note: 'danger-full-access — kernel is sole enforcement' };
  }

  // opencode: POC finding 3 — it has NO native path-scoped write sandbox (it touched the live
  // vault unprompted). A local `opencode.json` cannot confine writes to a path set. The kernel
  // systemd/bwrap sandbox is the SOLE enforcement.
  //
  // opencode STRICT-VALIDATES opencode.json and REFUSES any unrecognized key, so the advisory
  // MUST NOT ride in the config it parses (a `_note` key killed every opencode session at startup
  // with "Configuration is invalid ↳ Unrecognized key: _note"). The materialized config carries
  // ONLY opencode-schema-valid keys; the no-native-sandbox advisory (POC finding 3) is preserved
  // in a sidecar file beside it and never seen by opencode's parser.
  const cfg = {
    $schema: 'https://opencode.ai/config.json',
  };
  const p = path.join(sessionDir, 'opencode.json');
  fs.writeFileSync(p, JSON.stringify(cfg, null, 2));
  const notePath = path.join(sessionDir, '.ignite-sandbox-note.txt');
  fs.writeFileSync(
    notePath,
    `ADVISORY ONLY: opencode has no path-scoped write sandbox (POC finding 3). ` +
    `Kernel-enforced editable roots: ${roots.join(', ')}\n`,
    { mode: 0o600 }
  );
  return { harness: 'opencode', written: p, advisoryNote: notePath, enforceable: false, note: 'no native sandbox — kernel is sole enforcement' };
}

module.exports = { materializeHarnessConfig, harnessOf };
