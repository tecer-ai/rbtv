'use strict';

// Carriage-vocabulary collapse guard (batch-08 item 4 half A, owner ruling 2026-07-20; NARROWS
// D83/OQ-F). The vocabulary is ONE way in per session mode — headless `stdin`, headed
// `file`|`keystroke` — so caller free text NEVER becomes argv, with no exception clause.
// This probe proves the removal is LOAD-BEARING at config load:
//   (1) headless `prompt: file`        -> config-LOAD failure (E_CONFIG_LOAD)
//   (2) headless `prompt: argv-last`   -> config-LOAD failure (E_CONFIG_LOAD)
//   (3) headed  `tui.prompt: argv`     -> config-LOAD failure (E_CONFIG_LOAD)
//   (4) headed  `tui.prompt: stdin`    -> config-LOAD failure (structurally absent, unchanged)
//   (5) a {prompt} slot in headed.tui.argv -> config-LOAD failure (E_UNKNOWN_SLOT — the slot
//       itself is retired)
//   (6) POSITIVE: the SHIPPED config/spawn-profiles.yaml still loads cleanly — five profiles,
//       every one `prompt: stdin`, none declaring a headed carriage.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const yaml = require('js-yaml');
const { capture } = require('./lib');
const { loadConfig } = require('../config');

function writeCfg(tmp, name, profiles) {
  const cfg = {
    bind: { host: '127.0.0.1', port: 7431 },
    spawn: { data_root: path.join(tmp, 'data') },
    default_workdir_root: path.join(tmp, 'default'),
    profiles,
  };
  const p = path.join(tmp, `${name}.yaml`);
  fs.writeFileSync(p, yaml.dump(cfg));
  return p;
}

function baseProfile(extra = {}) {
  return {
    exec: { argv: ['sleep', '60'], prompt: 'stdin' },
    session_ref: { source: 'cwd-implicit' },
    workdir_root: '/tmp',
    caps: { memory_max: '64M' },
    ...extra,
  };
}

capture('probe-carriage-vocab', async (lines) => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'carriage-vocab-probe-'));
  try {
    const cases = [
      {
        name: '(1) headless prompt: file',
        expect: 'E_CONFIG_LOAD',
        profiles: { bad: baseProfile({ exec: { argv: ['sleep', '60'], prompt: 'file' } }) },
      },
      {
        name: '(2) headless prompt: argv-last',
        expect: 'E_CONFIG_LOAD',
        profiles: { bad: baseProfile({ exec: { argv: ['sleep', '60'], prompt: 'argv-last' } }) },
      },
      {
        name: '(3) headed tui.prompt: argv',
        expect: 'E_CONFIG_LOAD',
        profiles: { bad: baseProfile({ headed: { tui: { argv: ['tui', '--prompt', '{prompt}'], prompt: 'argv' } } }) },
      },
      {
        name: '(4) headed tui.prompt: stdin (structurally absent)',
        expect: 'E_CONFIG_LOAD',
        profiles: { bad: baseProfile({ headed: { tui: { argv: ['tui'], prompt: 'stdin' } } }) },
      },
      {
        name: '(5) {prompt} slot in headed.tui.argv (slot retired)',
        expect: 'E_UNKNOWN_SLOT',
        profiles: { bad: baseProfile({ headed: { tui: { argv: ['tui', '{prompt}'] } } }) },
      },
    ];

    for (const c of cases) {
      const cfgPath = writeCfg(tmp, c.name.replace(/[^a-z0-9]+/gi, '-'), c.profiles);
      let refused = false;
      try {
        loadConfig(cfgPath);
      } catch (err) {
        refused = true;
        if (err.code !== c.expect) {
          throw new Error(`${c.name}: refused with WRONG code ${err.code} (expected ${c.expect}): ${err.message}`);
        }
        lines.push(`${c.name} -> LOUD config-LOAD failure ${err.code}: ${err.message}`);
      }
      if (!refused) throw new Error(`${c.name}: UNEXPECTED PASS — the removed carriage loaded cleanly`);
    }

    // (6) POSITIVE — the shipped profiles config still loads. Mirror the daemon's composition
    // root (index.js DAEMON_ONLY_ROOT_KEYS): the daemon-only namespaces are stripped before
    // spawn/config.js sees the file, so the probe strips them the same way.
    const shipped = path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml');
    const raw = yaml.load(fs.readFileSync(shipped, 'utf8'));
    for (const k of ['ticker', 'tools', 'workflows', 'network']) delete raw[k];
    const shippedStripped = path.join(tmp, 'shipped-stripped.yaml');
    fs.writeFileSync(shippedStripped, yaml.dump(raw));
    const cfg = loadConfig(shippedStripped);
    const names = Object.keys(cfg.profiles);
    // ── TASK 7.86 — LANE SPLIT. The shipped config now carries TWO lanes, and this leg's
    // population is the FIRST one only.
    //
    //   exec lane     — `exec:`-shaped. The DAEMON's spawn profiles. This leg's subject: the
    //                   headless carriage vocabulary is a daemon-spawn property.
    //   command lane  — `command: { caged, portable }`-shaped. The orchestration conductor's CLI
    //                   dispatch profiles (7.86), resolved by launch-profiles/resolveProfile.
    //                   The daemon does not spawn these — it typed-refuses them
    //                   (E_PROFILE_HALVES_UNSUPPORTED, probe-profile-halves-refusal.js).
    //
    // The unguarded `cfg.profiles[n].exec.prompt` below USED to be safe because every shipped
    // profile was exec-shaped; the first command-lane profile turned it into a TypeError. That is
    // G-144's shape one layer up, and the filter — not a `?.` — is the fix: a command-lane profile
    // is not a profile this leg has an opinion about, so it is EXCLUDED, never leniently skipped.
    const execLane = names.filter((n) => cfg.profiles[n].exec);
    const commandLane = names.filter((n) => !cfg.profiles[n].exec);
    const carriages = execLane.map((n) => `${n}=${cfg.profiles[n].exec.prompt}`);
    lines.push(`(6) shipped config loads cleanly: ${names.length} profiles = ${execLane.length} exec-lane [${carriages.join(', ')}] + ${commandLane.length} command-lane [${commandLane.join(', ')}]`);
    // Task 7.11 added `claude-seat` (the seat launch profile) — ADDITIVELY, leaving every
    // pre-existing profile untouched. The count moved 5 -> 6. It is still asserted rather than
    // relaxed to a `>=`: this leg exists to notice a profile appearing in the shipped config, and
    // a floor would stop noticing exactly what it was written to catch.
    // ⚠ 7.86 DID NOT MOVE THIS NUMBER, and that is the point of the lane split rather than a
    // count bump: 7.86 added 11 profiles and ALL ELEVEN are command-lane, so the exec lane is
    // still exactly the same six. The day it is not, this fires — which is what it is for.
    // ⚠⚠ DO NOT RELAX EITHER COUNT TO A `>=`. That is the one edit that looks like a fix and
    // silently destroys what these legs exist to catch (the comment above says so; heed it).
    if (execLane.length !== 6) throw new Error(`(6) expected 6 exec-lane shipped profiles, found ${execLane.length}: ${execLane.join(', ')}`);
    // The command lane gets its OWN equality for the same reason the exec lane has one — without
    // it, 11 of the 17 shipped profiles could change in number unnoticed, and "notice a profile
    // appearing in the shipped config" would hold for a third of the file. 11 = the elected CLI
    // (model, variant) pairs task 7.86 authored one profile each for.
    if (commandLane.length !== 11) throw new Error(`(6) expected 11 command-lane shipped profiles, found ${commandLane.length}: ${commandLane.join(', ')}`);
    if (!names.includes('claude-seat')) throw new Error('(6) the 7.11 seat profile claude-seat is missing from the shipped config');
    // UNWEAKENED, and applied to the exec lane exactly as before: `stdin` is the only headless
    // carriage, and a shipped profile declares no headed carriage.
    for (const n of execLane) {
      if (cfg.profiles[n].exec.prompt !== 'stdin') throw new Error(`(6) shipped profile ${n} does not declare prompt: stdin`);
      const headedCarriage = cfg.profiles[n].headed?.tui?.prompt;
      if (headedCarriage !== undefined && headedCarriage !== null) throw new Error(`(6) shipped profile ${n} declares a headed carriage: ${headedCarriage}`);
    }
    // The command lane's halves carry their own `prompt`, validated at config LOAD by the same
    // closed vocabulary (profiles.js validateExec, called per half) — so it is already covered by
    // legs (1)/(2) above, which is why this leg asserts the exec lane and not both.
    lines.push(`RESULT: file/argv-last/argv (and the {prompt} slot) all fail config load LOUDLY; the six shipped exec-lane stdin profiles load cleanly, and the ${commandLane.length} command-lane profiles are excluded by lane, not skipped by leniency.`);
  } finally {
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch { /* fine */ }
  }
});
