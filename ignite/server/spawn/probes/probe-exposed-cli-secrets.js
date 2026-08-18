'use strict';

// D4 (2026-08-18) — an exposedCliCode opening that CONTAINS an enumerated private
// entry pierces it. Pattern-floor entries stay masked. A generic ro-bind does not pierce.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { capture } = require('./lib');
const { composeSeatCage } = require('../cage');
const { composePrivateScope } = require('../private-scope');

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

    lines.push('');
    lines.push(fails.length === 0 ? 'ALL LEGS PASS' : `FAILED LEGS: ${fails.join(', ')}`);
    if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.ws, { recursive: true, force: true }); } catch { /* best effort */ }
  }
});
