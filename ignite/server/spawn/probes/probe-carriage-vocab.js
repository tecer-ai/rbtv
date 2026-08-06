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
//   (6) POSITIVE: the SHIPPED config/spawn-profiles.yaml still loads cleanly — the 14-profile
//       exec-only roster (r-seats-only-architecture: one profile per harness+model), every one
//       `prompt: stdin`, none declaring a headed prompt carriage.

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
    // ── r-seats-only-architecture (2) — ONE PROFILE PER HARNESS+MODEL, EXEC LANE ONLY. The
    // 7.86 command lane (`command: { caged, portable }`) RETIRED with the daemon's sub-agent
    // dispatch lane; the shipped roster is the owner-ruled 14 (2026-08-06): claude fable/opus/
    // sonnet/haiku, codex-gpt-5-5, kimi, opencode glm-5-2/deepseek-flash/deepseek-pro/fugu/
    // fugu-ultra/gemini-flash/gemini-pro, plus test-sleep (D52). The lane filter is kept so a
    // command-lane profile REAPPEARING is caught by the equality below, never TypeError'd.
    const execLane = names.filter((n) => cfg.profiles[n].exec);
    const commandLane = names.filter((n) => !cfg.profiles[n].exec);
    const carriages = execLane.map((n) => `${n}=${cfg.profiles[n].exec.prompt}`);
    lines.push(`(6) shipped config loads cleanly: ${names.length} profiles = ${execLane.length} exec-lane [${carriages.join(', ')}] + ${commandLane.length} command-lane [${commandLane.join(', ')}]`);
    // ⚠⚠ DO NOT RELAX EITHER COUNT TO A `>=`. This leg exists to notice a profile appearing in
    // (or vanishing from) the shipped config; a floor would stop noticing exactly that.
    if (execLane.length !== 14) throw new Error(`(6) expected the 14 exec-lane shipped profiles, found ${execLane.length}: ${execLane.join(', ')}`);
    // Zero command-lane profiles is a POSITIVE assertion, not an omission: the command lane
    // retired with the daemon's sub-agent lane, and one reappearing must fire this leg.
    if (commandLane.length !== 0) throw new Error(`(6) expected 0 command-lane shipped profiles (lane retired, r-seats-only-architecture (4)), found ${commandLane.length}: ${commandLane.join(', ')}`);
    // UNWEAKENED, and applied to the exec lane exactly as before: `stdin` is the only headless
    // carriage, and a shipped profile declares no headed carriage.
    for (const n of execLane) {
      if (cfg.profiles[n].exec.prompt !== 'stdin') throw new Error(`(6) shipped profile ${n} does not declare prompt: stdin`);
      const headedCarriage = cfg.profiles[n].headed?.tui?.prompt;
      if (headedCarriage !== undefined && headedCarriage !== null) throw new Error(`(6) shipped profile ${n} declares a headed carriage: ${headedCarriage}`);
    }
    lines.push(`RESULT: file/argv-last/argv (and the {prompt} slot) all fail config load LOUDLY; the ${execLane.length} shipped exec-lane stdin profiles load cleanly, and the command lane is asserted EMPTY (retired with the sub-agent lane).`);
  } finally {
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch { /* fine */ }
  }
});
