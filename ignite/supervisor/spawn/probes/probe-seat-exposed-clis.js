'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { capture } = require('./lib');

const CODE_TREE = path.resolve(__dirname, '..', '..', '..', 'coord');
const ENTRY = path.join(CODE_TREE, 'coord.py');

capture('probe-seat-exposed-clis', async (lines) => {
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  if (!fs.existsSync(ENTRY)) throw new Error(`fixture precondition: ${ENTRY} is absent`);
  const spawnSrc = fs.readFileSync(path.join(__dirname, '..', 'spawn.js'), 'utf8');
  leg('X1', 'spawn.js still wires declared exposed-clis as sandbox symlinks on PATH',
    /exposedClis\.length > 0/.test(spawnSrc) && /flags\.push\('--symlink', g\.exposedCliEntry/.test(spawnSrc),
    'symlink+PATH wiring present');
  leg('X2', 'undeclared names still lose to the refusal shim, declared names skip it',
    /declaredNames\.has\(name\)/.test(spawnSrc) && /needsDeclaration\(/.test(spawnSrc),
    'declaredNames skip + needsDeclaration still on the spawn path');
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  lines.push('ALL LEGS PASS');
});
