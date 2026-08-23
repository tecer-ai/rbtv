'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const engine = require('./engine');

function scratch() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'embed-search-selftest-'));
}

function plant(dir, rel, body) {
  const full = path.join(dir, rel);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, body);
}

const CHECKS = [
  ['an absent --root REFUSES (red arm), a present one resolves (green)', () => {
    const dir = scratch();
    try {
      let refused = null;
      try { engine.resolveRoot(path.join(dir, 'nope')); } catch (e) { refused = e; }
      if (!refused || refused.rbtvCode !== 'no-root') throw new Error('an absent root did NOT refuse');
      if (!/not readable/.test(refused.message)) throw new Error('the refusal does not name the path');

      fs.mkdirSync(path.join(dir, 'ok'));
      if (engine.resolveRoot(path.join(dir, 'ok')) !== path.join(dir, 'ok')) {
        throw new Error('a present root did not resolve');
      }

      let usage = null;
      try { engine.resolveRoot(null); } catch (e) { usage = e; }
      if (!usage || usage.rbtvCode !== 'usage') throw new Error('a missing --root did NOT refuse as usage');
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['4-archives is skipped and the default index lives OUTSIDE the tree', async () => {
    const dir = scratch();
    try {
      plant(dir, 'keep.md', '# Keep\nfix inventory regression guard lives here\n');
      plant(dir, '4-archives/secret.md', '# Secret\nfix inventory regression guard should never rank\n');
      const idx = engine.defaultIndexPath(dir);
      if (idx.startsWith(dir + path.sep) || idx === dir) {
        throw new Error(`default index is inside the tree: ${idx}`);
      }
      const synced = await engine.sync({ root: dir, indexFile: idx, embed: false, cwd: dir });
      if (synced.docs < 1) throw new Error('keep.md was not indexed');
      if (synced.sections.some((s) => s.path.includes('4-archives'))) {
        throw new Error('4-archives leaked into the index');
      }
      if (fs.existsSync(path.join(dir, 'index.json'))) {
        throw new Error('an index file was written inside the tree');
      }
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['keyword arm ranks a planted section with no key', async () => {
    const dir = scratch();
    const prev = process.env[engine.KEY_VAR];
    process.env[engine.KEY_VAR] = '';
    try {
      plant(dir, 'system-problems.md', '# Fix inventory\ngit log regression guard\n');
      plant(dir, 'other.md', '# Unrelated\nweather and cats\n');
      const out = await engine.query({
        root: dir,
        query: 'fix inventory git log regression guard',
        top: 3,
        arm: 'keyword',
        embed: false,
        cwd: dir,
        indexFile: engine.defaultIndexPath(dir),
      });
      if (out.arm !== 'keyword') throw new Error(`arm was ${out.arm}`);
      if (!out.results.some((r) => r.path === 'system-problems.md')) {
        throw new Error(`keyword miss: ${JSON.stringify(out.results.map((r) => r.path))}`);
      }
    } finally {
      if (prev === undefined) delete process.env[engine.KEY_VAR];
      else process.env[engine.KEY_VAR] = prev;
      fs.rmSync(dir, { recursive: true, force: true });
    }
  }],
];

module.exports = async function runSelftest(opts) {
  const results = [];
  for (const [name, fn] of CHECKS) {
    try {
      await fn();
      results.push({ name, ok: true });
    } catch (err) {
      results.push({ name, ok: false, error: err.message });
    }
  }
  const ok = results.every((r) => r.ok);
  if (opts && opts.json) {
    process.stdout.write(`${JSON.stringify({ ok, checks: results, red_arm: CHECKS[0][0] })}\n`);
    return ok ? 0 : 1;
  }
  for (const r of results) console.log(`${r.ok ? 'ok  ' : 'FAIL'}  ${r.name}${r.ok ? '' : `\n      ${r.error}`}`);
  console.log(`\n${ok ? 'ok' : 'FAIL'} — ${results.filter((r) => r.ok).length}/${results.length} checks`);
  console.log('red arm: an absent --root REFUSES (caught), a present one resolves');
  return ok ? 0 : 1;
};
