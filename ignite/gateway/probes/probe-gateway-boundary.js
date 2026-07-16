'use strict';

// probe-gateway-boundary — gateway-cli-spec.md test 4 / internal-api-contract-spec.md test 3:
// "The gateway holds no queue/spawn handle. Zero direct store/spawn/profile-config
// references (internal-API client only)."
//
// WHY A STATIC SCAN IS THE RIGHT INSTRUMENT HERE: the property under test is an
// ABSENCE — that no code path in the gateway can reach the store or a spawn. A
// runtime test can only show that the paths it happened to drive did not do so;
// it cannot prove the eleventh path does not. The module graph can.
//
// ⚑ COMMENTS ARE STRIPPED BEFORE SCANNING, and that is load-bearing, not a
// convenience: the gateway's own comments discuss the store and spawn by name
// (explaining precisely why it must not touch them). A scanner that matched raw
// text would fail on prose while a real `require('../server/heart/heart-store')`
// hidden inside a string would still slip past. The check is about CODE.
//
// MUTATION (the run's standing bar — only mutation proves a guard): a clean scan
// proves the code is clean today; it does NOT prove the scanner would notice if it
// were not. So this probe WRITES a violating module into the gateway directory,
// requires the scanner to FAIL on it, then removes it and confirms the scan is
// green again. The revert is verified, not assumed.
//
// The capture is truncated at module load, BEFORE any work — a probe that dies at
// start leaves an EMPTY capture rather than the previous run's stale `EXIT: 0`
// (the D51 evidence-husk hazard). The process exit code remains the truth.

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-gateway-boundary.out');
fs.writeFileSync(outPath, '');

const GATEWAY_DIR = path.join(__dirname, '..');

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Strip comments while PRESERVING string literals. A naive regex would eat the
// `//` inside a URL or a quoted path; this walks the source in one pass.
//
// ⚑ String contents are KEPT, deliberately. An earlier cut of this scanner blanked
// them, which silently made every `require('<path>')` rule below UNFIREABLE — the
// probe still passed, and its mutation still "caught" a violation, but only via an
// identifier rule. Four of seven rules were dead while the capture read green. A
// guard that cannot fire is theatre; the module PATH is exactly what these rules
// exist to read.
function stripComments(src) {
  let outStr = '';
  let i = 0;
  let quote = null;
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (quote) {
      if (c === '\\') { outStr += src.slice(i, i + 2); i += 2; continue; }
      if (c === quote) quote = null;
      outStr += c;
      i++;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { quote = c; outStr += c; i++; continue; }
    if (c === '/' && next === '/') {
      while (i < src.length && src[i] !== '\n') { outStr += ' '; i++; }
      continue;
    }
    if (c === '/' && next === '*') {
      while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) { outStr += src[i] === '\n' ? '\n' : ' '; i++; }
      outStr += '  '; i += 2;
      continue;
    }
    outStr += c;
    i++;
  }
  return outStr;
}

// The forbidden reach. Each entry is what the gateway must NOT be able to name.
const FORBIDDEN = [
  { what: 'heart store module', re: /require\s*\(\s*['"][^'"]*heart[^'"]*['"]\s*\)/ },
  { what: 'spawn module', re: /require\s*\(\s*['"][^'"]*spawn[^'"]*['"]\s*\)/ },
  { what: 'server-core internals', re: /require\s*\(\s*['"][^'"]*\/server\/[^'"]*['"]\s*\)/ },
  { what: 'a raw SQLite driver', re: /require\s*\(\s*['"](node:)?sqlite['"]\s*\)|\bDatabaseSync\b/ },
  { what: 'child-process spawn', re: /require\s*\(\s*['"](node:)?child_process['"]\s*\)|\bchildSpawn\b|\bspawnSync\b/ },
  { what: 'the store/spawn factory functions', re: /\bopenHeartStore\b|\bcreateSpawnManager\b|\bloadConfig\b/ },
  { what: 'launch-profile config', re: /\bspawn-profiles\b|\bprofiles\s*\[/ },
];

// Scans the gateway's own modules. probes/ is excluded: this file necessarily
// NAMES the forbidden things in order to look for them, and a test fixture is not
// the shipped module.
function scanGateway() {
  const violations = [];
  const files = fs.readdirSync(GATEWAY_DIR)
    .filter((f) => f.endsWith('.js'))
    .map((f) => path.join(GATEWAY_DIR, f));
  for (const file of files) {
    const code = stripComments(fs.readFileSync(file, 'utf8'));
    for (const rule of FORBIDDEN) {
      const m = code.match(rule.re);
      if (m) violations.push({ file: path.basename(file), what: rule.what, match: m[0].trim() });
    }
  }
  return { files: files.map((f) => path.basename(f)), violations };
}

const MUTANT = path.join(GATEWAY_DIR, '_boundary-mutant.js');

function removeMutant() {
  try { fs.unlinkSync(MUTANT); } catch {}
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));

  // --- 1. The shipped gateway holds no store/spawn/profile-config reference.
  const clean = scanGateway();
  out(`SCANNED: ${clean.files.join(', ')}`);
  check('the gateway module has ZERO store/spawn/profile-config references',
    clean.violations.length === 0,
    clean.violations.length ? JSON.stringify(clean.violations) : `${clean.files.length} files scanned, 0 violations`);

  // The positive half: it DOES hold the internal-API client, injected — proving the
  // absence above is a real boundary and not simply an empty module.
  const gatewaySrc = stripComments(fs.readFileSync(path.join(GATEWAY_DIR, 'gateway.js'), 'utf8'));
  check('the gateway reaches the core ONLY through an INJECTED dispatch endpoint',
    /createGateway\s*\(\s*\{[^}]*dispatch/.test(gatewaySrc) && /await\s+dispatch\s*\(/.test(gatewaySrc),
    'dispatch is a constructor argument, never a require');

  // --- 2. MUTATION: reintroduce the defect; the scan MUST fail.
  //
  // EVERY rule is mutated, not just one. A single mutation only proves that SOME
  // rule fires — it cannot distinguish seven live rules from one live rule and six
  // dead ones. (That is not hypothetical: an earlier cut of this probe passed its
  // mutation while four rules were structurally unfireable. See stripComments.)
  const MUTATIONS = [
    { what: 'heart store module', code: "const s = require('../server/heart/heart-store');\nmodule.exports = s;" },
    { what: 'spawn module', code: "const s = require('../server/spawn/spawn');\nmodule.exports = s;" },
    { what: 'server-core internals', code: "const t = require('../server/ticker/ticker');\nmodule.exports = t;" },
    { what: 'a raw SQLite driver', code: "const { DatabaseSync } = require('node:sqlite');\nmodule.exports = { DatabaseSync };" },
    { what: 'child-process spawn', code: "const cp = require('node:child_process');\nmodule.exports = cp;" },
    { what: 'the store/spawn factory functions', code: "function f(o) { return openHeartStore(o); }\nmodule.exports = { f };" },
    { what: 'launch-profile config', code: "function g(c, n) { return c.profiles[n]; }\nmodule.exports = { g };" },
  ];

  for (const m of MUTATIONS) {
    fs.writeFileSync(MUTANT, [
      "'use strict';",
      '// Deliberate boundary violation, written by probe-gateway-boundary to prove the',
      '// scanner detects one. Removed before this probe exits.',
      m.code,
      '',
    ].join('\n'));
    const mutated = scanGateway();
    const caught = mutated.violations.filter((v) => v.file === '_boundary-mutant.js' && v.what === m.what);
    check(`MUTATION: a gateway file reaching "${m.what}" is DETECTED`,
      caught.length > 0,
      caught.length ? `caught: ${caught[0].match}` : 'THE RULE DID NOT FIRE — this guard is theatre');
    removeMutant();
  }

  // --- 3. REVERT, and prove the revert landed on disk.
  removeMutant();
  check('REVERT: the mutant file is gone from disk',
    !fs.existsSync(MUTANT),
    `${path.basename(MUTANT)} absent`);

  const reverted = scanGateway();
  check('REVERT: the scan is green again (identity, not a count)',
    reverted.violations.length === 0 && !reverted.files.includes('_boundary-mutant.js'),
    `${reverted.files.length} files scanned, 0 violations`);

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`CHECKS: ${checks.length - failed.length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SKIPPED_COUNT: 0`);
  out(`BOUNDARY_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
} catch (err) {
  out('ERROR:', err.message, err.stack);
  out(`SKIPPED_COUNT: 0`);
  out(`EXIT: 1`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
} finally {
  // The mutation is an INSTRUMENT, never a residue: remove it on every path,
  // including a throw between write and revert.
  removeMutant();
}
