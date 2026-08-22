'use strict';

// D4 (2026-08-18) — an exposedCliCode opening that CONTAINS an enumerated private
// entry pierces it. Pattern-floor entries stay masked. A generic ro-bind does not pierce.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeSeatCage } = require('../cage');
const { composePrivateScope, needsDeclaration } = require('../private-scope');
const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath } = require('../../seat-identity/seat-folder');

function fixture() {
  const ws = fs.mkdtempSync(path.join(os.tmpdir(), 'exposed-cli-secrets-'));
  const stools = path.join(ws, '3-resources', 'tools', 'stools');
  fs.mkdirSync(path.join(stools, 'credentials', 'workspace'), { recursive: true });
  fs.mkdirSync(path.join(stools, '.git', 'objects'), { recursive: true });
  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(stools, 'config.yaml'), 'token: secret\n');
  fs.writeFileSync(path.join(stools, 'credentials', 'workspace', 'token.json'), 'xoxp-secret\n');
  fs.writeFileSync(path.join(stools, '.git', 'HEAD'), 'ref: refs/heads/main\n');
  fs.writeFileSync(path.join(stools, 'stools'), '#!/usr/bin/env python3\n');
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'private.json'), JSON.stringify({
    deny: [
      '3-resources/tools/stools/config.yaml',
      '3-resources/tools/stools/credentials/',
    ],
    patterns: ['**/*.env', '**/credentials/', '**/*token*', '**/*.key', '**/.git'],
  }));
  return {
    ws,
    stools,
    configYaml: path.join(stools, 'config.yaml'),
    creds: path.join(stools, 'credentials'),
    gitDir: path.join(stools, '.git'),
  };
}

// ── D56/D74 fixture — a `local-bin: true` seat, HOME faked so `resolveLocalBinGrant`'s hardcoded
// `os.homedir()` sees a fixture `.local/bin` rather than this machine's real one. Two names: one
// whose real target's directory holds a private entry (needs a pierce, per `needsDeclaration`), one
// whose directory holds nothing (the `coordinate`/`teamview` shape `local-bin` was built for).
function fixtureLocalBin() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'local-bin-refusal-'));
  const home = path.join(root, 'home');
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'alpha');
  const seatDir = path.join(goalDir, 'seats', 'worker');
  fs.mkdirSync(path.join(home, '.local', 'bin'), { recursive: true });
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\n');

  const privateTool = path.join(ws, '3-resources', 'tools', 'privtool');
  fs.mkdirSync(path.join(privateTool, 'credentials'), { recursive: true });
  fs.writeFileSync(path.join(privateTool, 'config.yaml'), 'token: secret\n');
  fs.writeFileSync(path.join(privateTool, 'privtool.py'), '#!/usr/bin/env python3\nimport sys\nprint("real privtool", sys.argv[1:])\n', { mode: 0o755 });
  fs.symlinkSync(path.join(privateTool, 'privtool.py'), path.join(home, '.local', 'bin', 'privtool'));

  const cleanTool = path.join(ws, 'coordkit');
  fs.mkdirSync(cleanTool, { recursive: true });
  fs.writeFileSync(path.join(cleanTool, 'coordish.py'), '#!/usr/bin/env python3\nimport sys\nprint("real coordish", sys.argv[1:])\n', { mode: 0o755 });
  fs.symlinkSync(path.join(cleanTool, 'coordish.py'), path.join(home, '.local', 'bin', 'coordish'));

  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'private.json'), JSON.stringify({
    deny: ['3-resources/tools/privtool/config.yaml', '3-resources/tools/privtool/credentials/'],
    patterns: ['**/*.env', '**/credentials/', '**/*token*', '**/*.key', '**/.git'],
  }));

  fs.writeFileSync(path.join(seatDir, 'seat.md'), '---\nseat: worker\nlocal-bin: true\n---\nbriefing\n');
  const declaredDir = path.join(goalDir, 'seats', 'declared');
  fs.mkdirSync(declaredDir, { recursive: true });
  fs.writeFileSync(path.join(declaredDir, 'seat.md'), [
    '---', 'seat: declared', 'local-bin: true', 'exposed-clis:',
    `  - privtool ${path.join(privateTool, 'privtool.py')}`, '---', 'briefing',
  ].join('\n') + '\n');

  return { root, home, ws, seatDir, declaredDir, privateTool, cleanTool };
}

function shippedSeatBindsLocal() {
  const cfg = yaml.load(fs.readFileSync(path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

function isMasked(result, p) {
  for (let i = 0; i < result.flags.length; i++) {
    if (result.flags[i] === '--ro-bind' && result.flags[i + 2] === p) return true;
  }
  return false;
}

function compose(ws, grants) {
  const spec = composeSeatCage({
    seatBinds: ['ro-bind:{grant:readRoot}', 'ro-bind:{grant:exposedCliCode}'],
    values: {},
    grants,
  });
  const logs = [];
  const result = composePrivateScope(spec, {
    workspaceRoot: ws,
    log: (level, msg, extra) => logs.push({ level, msg, extra }),
  });
  return { spec, result, logs };
}

capture('probe-exposed-cli-secrets', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    const tagged = compose(f.ws, [
      { readRoot: f.ws },
      { exposedCliCode: f.stools, exposedCliName: 'stools', grantClass: 'exposedCliCode' },
    ]);
    const taggedOpening = tagged.spec.find((o) => o.path === f.stools);
    const configPierced = tagged.result.pierced.some((p) => p.includes(f.configYaml) && p.includes('stools'));
    const credsPierced = tagged.result.pierced.some((p) => p.includes(f.creds) && p.includes('stools'));
    const logsNameBoth = tagged.logs.filter((l) =>
      l.msg === 'private-scope PIERCE' && l.extra && l.extra.grantingCli === 'stools'
      && (l.extra.entry === f.configYaml || l.extra.entry === f.creds)).length === 2;

    leg('1', 'exposedCliCode-tagged ro-bind of the CLI dir pierces enumerated config.yaml AND credentials/',
      taggedOpening && taggedOpening.grantClass === 'exposedCliCode' && taggedOpening.exposedCliName === 'stools'
      && !isMasked(tagged.result, f.configYaml) && !isMasked(tagged.result, f.creds)
      && configPierced && credsPierced,
      `opening=${JSON.stringify(taggedOpening)}; configMasked=${isMasked(tagged.result, f.configYaml)}; `
      + `credsMasked=${isMasked(tagged.result, f.creds)}; pierced=${JSON.stringify(tagged.result.pierced)}`);

    const plain = compose(f.ws, [
      { readRoot: f.ws },
      { exposedCliCode: f.stools },
    ]);
    const plainOpening = plain.spec.find((o) => o.path === f.stools);
    leg('2', 'the same ro-bind WITHOUT the exposedCliCode class tag leaves config.yaml masked',
      plainOpening && plainOpening.grantClass === undefined
      && isMasked(plain.result, f.configYaml) && isMasked(plain.result, f.creds)
      && !plain.result.pierced.some((p) => p.includes(f.configYaml)),
      `opening=${JSON.stringify(plainOpening)}; configMasked=${isMasked(plain.result, f.configYaml)}; `
      + `pierced=${JSON.stringify(plain.result.pierced)}`);

    const gitCreatedByWalk = tagged.result.entries.includes(f.gitDir);
    leg('3', 'the .git pattern floor still masks a .git under the exposed tree (root cover makes the walk run)',
      gitCreatedByWalk && isMasked(tagged.result, f.gitDir)
      && !tagged.result.pierced.some((p) => p.includes(f.gitDir)),
      `gitInEntries=${gitCreatedByWalk}; gitMasked=${isMasked(tagged.result, f.gitDir)}; `
      + `entries.git=${f.gitDir}`);

    const disclosure = tagged.logs
      .filter((l) => l.msg === 'private-scope PIERCE')
      .map((l) => `${l.msg} entry=${l.extra.entry} grantingCli=${l.extra.grantingCli}`);
    leg('4', 'spawn disclosure names each pierced entry and its granting CLI',
      logsNameBoth && disclosure.length === 2,
      disclosure.join(' | '));

    const spawnSrc = fs.readFileSync(path.join(__dirname, '..', 'spawn.js'), 'utf8');
    const tagsGrant = /grantClass:\s*'exposedCliCode'/.test(spawnSrc)
      && /function resolveExposedCliGrants/.test(spawnSrc);
    leg('5', 'resolveExposedCliGrants threads grantClass: exposedCliCode onto the grant',
      tagsGrant, `spawn.js tags grantClass=${tagsGrant}`);

    // ── D56/D74 — NEW LEG: undeclared + `local-bin: true` gets the NAMED REFUSAL, not the real
    // tool; a name whose directory holds nothing private is untouched. `needsDeclaration` first
    // (the classification the shim decision rests on), then the full `composeCageFor` composition
    // with HOME faked so `local-bin`'s hardcoded `os.homedir()` sees the fixture, not this machine.
    leg('6', 'needsDeclaration: a tool directory holding an enumerated private entry needs declaration',
      needsDeclaration(f.ws, f.stools) === true, `needsDeclaration(ws, stools)=${needsDeclaration(f.ws, f.stools)}`);
    leg('7', 'needsDeclaration: a directory outside the workspace root never needs declaration',
      needsDeclaration(f.ws, os.tmpdir()) === false, `needsDeclaration(ws, tmpdir)=${needsDeclaration(f.ws, os.tmpdir())}`);

    const lb = fixtureLocalBin();
    const savedHome = process.env.HOME;
    let undeclaredFlags; let declaredFlags; let undeclaredLogs = []; let declaredLogs = [];
    try {
      process.env.HOME = lb.home;
      undeclaredFlags = composeCageFor({ SeatBinds: shippedSeatBindsLocal() }, parseSeatPath(lb.seatDir), lb.seatDir, null,
        (level, msg) => undeclaredLogs.push(`${level}: ${msg}`));
      declaredFlags = composeCageFor({ SeatBinds: shippedSeatBindsLocal() }, parseSeatPath(lb.declaredDir), lb.declaredDir, null,
        (level, msg) => declaredLogs.push(`${level}: ${msg}`));
    } finally {
      process.env.HOME = savedHome;
    }
    const rbtvBinLocal = path.join(lb.home, '.rbtv-bin');
    const symlinkTarget = (flags, dest) => {
      for (let i = 0; i < flags.length; i++) if (flags[i] === '--symlink' && flags[i + 2] === dest) return flags[i + 1];
      return undefined;
    };
    const privtoolShim = symlinkTarget(undeclaredFlags, path.join(rbtvBinLocal, 'privtool'));
    leg('8', 'UNDECLARED privtool (private dir) gets a shim symlink, not the real entry point',
      privtoolShim !== undefined && privtoolShim !== path.join(lb.privateTool, 'privtool.py'),
      `symlink target for privtool: ${privtoolShim}`);
    leg('9', 'UNDECLARED coordish (clean dir — the coordinate/teamview shape) gets NO shim at all',
      symlinkTarget(undeclaredFlags, path.join(rbtvBinLocal, 'coordish')) === undefined,
      `symlink target for coordish: ${symlinkTarget(undeclaredFlags, path.join(rbtvBinLocal, 'coordish'))}`);
    leg('10', 'DECLARED privtool (exposed-clis) gets the REAL entry point symlinked, not the shim',
      symlinkTarget(declaredFlags, path.join(rbtvBinLocal, 'privtool')) === path.join(lb.privateTool, 'privtool.py'),
      `symlink target for declared privtool: ${symlinkTarget(declaredFlags, path.join(rbtvBinLocal, 'privtool'))}`);

    const runUndeclared = () => {
      const argv = buildBwrapArgv({ argv: ['bash', '-c', 'privtool x 2>&1; echo rc=$?; coordish y 2>&1; echo rc2=$?'], workdir: lb.seatDir, harness: null, seatBinds: undeclaredFlags });
      try {
        const out = execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000, encoding: 'utf8', env: { ...process.env, HOME: lb.home } });
        return out;
      } catch (err) { return ((err.stdout || '') + (err.stderr || '')).toString(); }
    };
    const inCageOut = runUndeclared();
    try { fs.rmSync(lb.root, { recursive: true, force: true }); } catch { /* best effort */ }
    leg('11', 'RED (in-cage): undeclared privtool prints the named refusal and exits nonzero; coordish still runs',
      /privtool is not exposed to this seat/.test(inCageOut) && /rc=1/.test(inCageOut)
      && /real coordish/.test(inCageOut) && /rc2=0/.test(inCageOut),
      `in-cage output: ${JSON.stringify(inCageOut.slice(0, 300))}`);

    // ── mutation proof (D62): mutate a COPY of private-scope.js so `needsDeclaration` always
    // returns false, confirm leg 6 goes RED against the mutated copy, then discard the copy.
    const psPath = path.join(__dirname, '..', 'private-scope.js');
    const psSrc = fs.readFileSync(psPath, 'utf8');
    const mutCopy = path.join(os.tmpdir(), `private-scope-mutant-${process.pid}.js`);
    const mutated = psSrc.replace('function needsDeclaration(workspaceRoot, dir, log = () => {}) {',
      'function needsDeclaration(workspaceRoot, dir, log = () => {}) { return false;');
    let mutantIsRed = false; let mutantDetail = 'mutation did not apply — source pattern not found';
    if (mutated !== psSrc) {
      fs.writeFileSync(mutCopy, mutated);
      try {
        delete require.cache[require.resolve(mutCopy)];
        const mutantMod = require(mutCopy);
        mutantIsRed = mutantMod.needsDeclaration(f.ws, f.stools) === false;
        mutantDetail = `mutant needsDeclaration(ws, stools) = ${mutantMod.needsDeclaration(f.ws, f.stools)} (real code says true — leg 6 above)`;
      } finally {
        try { fs.unlinkSync(mutCopy); } catch { /* best effort */ }
        delete require.cache[require.resolve(mutCopy)];
      }
    }
    leg('12', 'MUTATION PROOF: forcing needsDeclaration to always return false makes leg 6 go RED (copy discarded)',
      mutantIsRed, mutantDetail);

    lines.push('');
    lines.push(fails.length === 0 ? 'ALL LEGS PASS' : `FAILED LEGS: ${fails.join(', ')}`);
    if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.ws, { recursive: true, force: true }); } catch { /* best effort */ }
  }
});
