'use strict';

// teambuild's own mechanics. Every green here travels with the RED that proves the
// instrument could have failed: the malformed-catalog and absent-mirror checks
// build their defect on a SCRATCH tree under the OS temp dir and assert the refusal
// fires, then assert the same reader stays green on the repaired copy. Nothing in
// the real corpus is touched — the corpus is read-only to this tool by contract.

const fs = require('fs');
const os = require('os');
const path = require('path');
const corpus = require('./corpus');

function scratch() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'teambuild-selftest-'));
}

// A minimal but SHAPE-REAL component: both mirror layouts on this box put catalogs
// at <root>/<module>/<component>/.
function plantComponent(root, { promptsHeader, promptsRow, unitDir, unitBody }) {
  const comp = path.join(root, 'mod', 'comp');
  fs.mkdirSync(comp, { recursive: true });
  fs.writeFileSync(path.join(comp, 'prompts.csv'), `${promptsHeader}\n${promptsRow}\n`);
  if (unitDir) {
    const d = path.join(comp, 'prompts', 'cognitive-units', unitDir);
    fs.mkdirSync(d, { recursive: true });
    fs.writeFileSync(path.join(d, 'u.md'), unitBody);
  }
  return comp;
}

const GOOD_HEADER = 'prompt-id,role,description,staffing-recommendations';
const GOOD_ROW = 'p1,r1,"A prompt that does one thing.","opus; high effort"';

const CHECKS = [
  ['an absent mirror root REFUSES (red arm), a present one resolves (green)', () => {
    const dir = scratch();
    try {
      let refused = null;
      try { corpus.resolveRoot(path.join(dir, 'nope'), dir); } catch (e) { refused = e; }
      if (!refused || refused.rbtvCode !== 'NO_MIRROR') throw new Error('an absent root did NOT refuse');

      // The walk-up arm: no `.rbtv/mirror` anywhere above the scratch dir either.
      let walked = null;
      try { corpus.resolveRoot(null, dir); } catch (e) { walked = e; }
      if (!walked || walked.rbtvCode !== 'NO_MIRROR') throw new Error('the walk-up did NOT refuse with no mirror above it');
      if (!/looked in:/.test(walked.message)) throw new Error('the refusal does not name where it looked');

      const real = path.join(dir, '.rbtv', 'mirror');
      fs.mkdirSync(real, { recursive: true });
      if (corpus.resolveRoot(null, dir) !== real) throw new Error('the walk-up did not find a mirror that IS there');
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['a MALFORMED catalog refuses loudly; the repaired copy goes green', () => {
    const dir = scratch();
    try {
      // Defect 1: no `description` column — the blurb source is gone.
      plantComponent(dir, { promptsHeader: 'prompt-id,role', promptsRow: 'p1,r1' });
      let e1 = null;
      try { corpus.entries(dir, 'agents'); } catch (e) { e1 = e; }
      if (!e1 || e1.rbtvCode !== 'BAD_CATALOG') throw new Error('a catalog with no `description` column did NOT refuse');
      if (!/description/.test(e1.message) || !/prompts\.csv/.test(e1.message)) {
        throw new Error(`the refusal names neither the column nor the file: ${e1.message}`);
      }

      // Defect 2: no id column — rows would be nameless.
      plantComponent(dir, { promptsHeader: 'role,description', promptsRow: 'r1,"a blurb"' });
      let e2 = null;
      try { corpus.entries(dir, 'agents'); } catch (e) { e2 = e; }
      if (!e2 || e2.rbtvCode !== 'BAD_CATALOG') throw new Error('a catalog with no id column did NOT refuse');

      // Defect 3: empty file — a header-less catalog declares no schema.
      plantComponent(dir, { promptsHeader: '', promptsRow: '' });
      let e3 = null;
      try { corpus.entries(dir, 'agents'); } catch (e) { e3 = e; }
      if (!e3 || e3.rbtvCode !== 'BAD_CATALOG') throw new Error('an empty catalog did NOT refuse');

      // GREEN on the repair — the same reader, the same path, one header fixed.
      plantComponent(dir, { promptsHeader: GOOD_HEADER, promptsRow: GOOD_ROW });
      const rows = corpus.entries(dir, 'agents');
      if (rows.length !== 1) throw new Error(`repaired catalog yielded ${rows.length} rows, expected 1`);
      if (rows[0].id !== 'p1') throw new Error(`id read as ${rows[0].id}`);
      if (rows[0].blurb !== 'A prompt that does one thing.') throw new Error(`blurb read as ${rows[0].blurb}`);
      if (rows[0].staffing !== 'opus; high effort') throw new Error('the agent card lost its staffing recommendations');
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['an ABSENT catalog is skipped, never refused — a component need not carry every database', () => {
    const dir = scratch();
    try {
      plantComponent(dir, { promptsHeader: GOOD_HEADER, promptsRow: GOOD_ROW });
      if (corpus.entries(dir, 'seats').length !== 0) throw new Error('a component with no seats.csv produced seat rows');
      if (corpus.entries(dir, 'agents').length !== 1) throw new Error('the present catalog stopped being read');
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['the blurb is the EXISTING description field, folded continuations included', () => {
    const dir = scratch();
    try {
      plantComponent(dir, {
        promptsHeader: GOOD_HEADER,
        promptsRow: GOOD_ROW,
        unitDir: 'roles',
        unitBody: '---\nid: u-one\ndescription: a description that folds\n  across two lines\n---\n\n<role>x</role>\n',
      });
      const [u] = corpus.entries(dir, 'units');
      if (!u) throw new Error('no unit enumerated');
      if (u.id !== 'u-one') throw new Error(`id read as ${u.id}`);
      if (u.blurb !== 'a description that folds across two lines') {
        throw new Error(`folded description read as: ${u.blurb}`);
      }
      // No blurb where none is authored — the reader reports the gap, never fills it.
      fs.writeFileSync(path.join(dir, 'mod', 'comp', 'prompts', 'cognitive-units', 'roles', 'u.md'), '---\nid: u-one\n---\nbody\n');
      if (corpus.entries(dir, 'units')[0].blurb !== corpus.NO_BLURB) throw new Error('a missing description was not reported as missing');
    } finally { fs.rmSync(dir, { recursive: true, force: true }); }
  }],

  ['the unit-kind filter matches both authored shapes (singular and plural)', () => {
    if (!corpus.kindMatches('role', 'roles')) throw new Error('`--kind role` misses a `roles/` directory');
    if (!corpus.kindMatches('personas', 'persona')) throw new Error('`--kind personas` misses a `persona/` directory');
    if (corpus.kindMatches('role', 'scopes')) throw new Error('`--kind role` matched an unrelated kind');
  }],

  ['ONE code path — this capability holds exactly one corpus enumerator', () => {
    // The parity constraint, asserted rather than asserted-in-prose: a second
    // reader landing beside this one is what the constraint forbids, and only a
    // check catches it the day it lands.
    //
    // The instrument is the PROPERTY, not a file count. It counted files until
    // 7.434, when provider.js (the vendor boundary) and search.js (the index
    // lifecycle) landed in this directory: the count went red while the
    // constraint they were accused of breaking still held — neither walks the
    // corpus, and search.js takes every entry from require('./corpus'). A check
    // that cannot pass a correct change stops being read, and being read is the
    // suite's whole value. Repaired under the leader's grant
    // `p-w11-selftest-check6-repair-granted`; same name, same intent.
    //
    // ⚠ WHAT THIS CHECK CANNOT SEE, stated here because a guard that hides its
    // blind spot is how the next silent blindness ships with a green tick beside
    // it: it greps four literal idioms. `fs.promises.readdir`, `fs.opendir`, a
    // dynamic `fs[name]()` call, a third-party glob, and a directory listing
    // shelled out to a child process ALL pass it. Every module in this directory
    // already requires `fs`, so that surface is open today, not hypothetically.
    // Reviewing a new lib module still means reading it.
    const lib = path.join(__dirname);
    if (!fs.existsSync(path.join(lib, 'corpus.js'))) throw new Error('corpus.js — the one enumerator — is missing');
    const ENUMERATES = /\breaddirSync\s*\(|\breaddir\s*\(|\bglobSync\s*\(|\bglob\s*\(/;
    for (const f of fs.readdirSync(lib).filter((n) => n.endsWith('.js') && n !== 'selftest.js' && n !== 'corpus.js')) {
      if (ENUMERATES.test(fs.readFileSync(path.join(lib, f), 'utf8'))) {
        throw new Error(`${f} walks a directory itself — that is a SECOND enumerator; it must take its entries from require('./corpus')`);
      }
    }
    // The positive half: the search must TAKE its entries from the enumerator.
    // Both spellings of the require pass — a check that reds on `./corpus.js`
    // vs `./corpus` would be the same kind of proxy defect this repair removed.
    const search = path.join(lib, 'search.js');
    if (fs.existsSync(search) && !/require\(['"]\.\/corpus(\.js)?['"]\)/.test(fs.readFileSync(search, 'utf8'))) {
      throw new Error('search.js does not require the corpus module — the search must ride the one enumerator, not its own');
    }
  }],
];

module.exports = function runSelftest(opts) {
  const results = CHECKS.map(([name, fn]) => {
    try { fn(); return { name, ok: true }; } catch (err) { return { name, ok: false, error: err.message }; }
  });
  const ok = results.every((r) => r.ok);
  if (opts && opts.json) {
    process.stdout.write(`${JSON.stringify({ ok, checks: results })}\n`);
    return ok ? 0 : 1;
  }
  for (const r of results) console.log(`${r.ok ? 'ok  ' : 'FAIL'}  ${r.name}${r.ok ? '' : `\n      ${r.error}`}`);
  console.log(`\n${ok ? 'ok' : 'FAIL'} — ${results.filter((r) => r.ok).length}/${results.length} checks`);
  return ok ? 0 : 1;
};
