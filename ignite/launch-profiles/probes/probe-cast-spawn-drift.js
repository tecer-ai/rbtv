'use strict';

// probe-cast-spawn-drift — cast catalog ladders vs spawn-profiles.yaml launch-specs (W5).
//
// For every (harness, model) pair present in BOTH `launch-specs:` and `cast list --json`,
// the effort ladders must agree. Also red if `kimi` reappears as a harness key.
// Join is via catalog.js `id` (yaml / argv pin) ↔ `model` (cast list short name).

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const yaml = require('js-yaml');

const IGNITE_ROOT = path.resolve(__dirname, '..', '..');
const SHIPPED = path.join(IGNITE_ROOT, 'config', 'spawn-profiles.yaml');
const OUT = path.join(__dirname, 'probe-cast-spawn-drift.out');

function resolveCatalog() {
  if (process.env.RBTV_CAST_CATALOG) return require(path.resolve(process.env.RBTV_CAST_CATALOG));
  const fromCast = () => {
    const which = execFileSync('which', ['cast'], { encoding: 'utf8' }).trim();
    const real = fs.realpathSync(which);
    return require(path.join(path.dirname(real), 'catalog.js'));
  };
  try { return fromCast(); } catch {
    return require(path.resolve(
      IGNITE_ROOT, '..', '..', '..', '..',
      '.rbtv', 'mirror', 'core', 'sub-agents', 'tool', 'catalog.js',
    ));
  }
}

const lines = [];
const started = new Date();
let failed = null;

function check(label, fn) {
  try {
    const detail = fn();
    lines.push(`PASS ${label}${detail ? ` -> ${detail}` : ''}`);
  } catch (err) {
    lines.push(`FAIL ${label} -> ${err.message}`);
    if (!failed) failed = err;
  }
}

const catalog = resolveCatalog();
const shipped = yaml.load(fs.readFileSync(SHIPPED, 'utf8'));
const launchSpecs = (shipped && shipped['launch-specs']) || {};

let castList;
check('(1) cast list --json is readable', () => {
  const raw = execFileSync('cast', ['list', '--json'], { encoding: 'utf8' });
  castList = JSON.parse(raw);
  const harnesses = Object.keys(castList).sort().join(',');
  if (!harnesses) throw new Error('empty catalog');
  return harnesses;
});

check('(2) kimi is not a launch-specs harness key', () => {
  if (Object.prototype.hasOwnProperty.call(launchSpecs, 'kimi')) {
    throw new Error('kimi reappeared as a launch-specs: harness key');
  }
  return 'absent';
});

check('(3) overlapping (harness, model) ladders agree', () => {
  const cliRows = (catalog.ROWS || []).filter((r) => r.mode === 'cli');
  const byPair = new Map();
  for (const row of cliRows) {
    byPair.set(`${row.harness}\t${row.id}`, row);
    byPair.set(`${row.harness}\t${row.model}`, row);
  }
  const compared = [];
  const diverged = [];
  for (const harness of Object.keys(launchSpecs)) {
    const models = launchSpecs[harness];
    if (!models || typeof models !== 'object') continue;
    for (const model of Object.keys(models)) {
      const row = byPair.get(`${harness}\t${model}`);
      if (!row) continue;
      const spec = models[model] || {};
      const effort = spec.effort || {};
      const yamlRungs = effort.inert === true ? [] : (effort.rungs || []);
      const catalogRungs = row.rungs || [];
      const castRungs = ((castList[harness] || {})[row.model]);
      const left = JSON.stringify(yamlRungs);
      const fromCatalog = JSON.stringify(catalogRungs);
      compared.push(`${harness}/${model}`);
      if (left !== fromCatalog) {
        diverged.push(`${harness}/${model} yaml=${left} catalog=${fromCatalog}`);
      }
      if (castRungs !== undefined && left !== JSON.stringify(castRungs)) {
        diverged.push(`${harness}/${model} yaml=${left} cast=${JSON.stringify(castRungs)}`);
      }
    }
  }
  if (!compared.length) throw new Error('no overlapping pairs — join failed');
  if (diverged.length) throw new Error(diverged.join(' | '));
  return `${compared.length} pairs`;
});

const ended = new Date();
const exitCode = failed ? 1 : 0;
const body = [
  'probe: probe-cast-spawn-drift',
  `started: ${started.toISOString()}`,
  'command: node launch-profiles/probes/probe-cast-spawn-drift.js',
  ...lines,
  `status: ${failed ? 'FAIL' : 'PASS'}`,
  `checks: ${lines.length} (${lines.filter((l) => l.startsWith('PASS')).length} pass, ${lines.filter((l) => l.startsWith('FAIL')).length} fail)`,
  `exit: ${exitCode}`,
  `wall_ms: ${ended - started}`,
  `ended: ${ended.toISOString()}`,
  '',
].join('\n');
fs.writeFileSync(OUT, body);
process.stdout.write(body);
process.exit(exitCode);
