#!/usr/bin/env node
'use strict';

// probe-outputs-resolver — DO THE TWO HALVES OF THE SHARED DECLARED-OUTPUTS RESOLVER AGREE?
//
// D3 (outputs-unify, 2026-08-18): the io-spec `## Outputs` block in seat.md is the ONE
// declared-outputs surface, consumed by two readers — `envelope/cage-admission.js` (this side,
// `parseDeclaredOutputs`, the caged-launch admission gate) and `team-kit/coord.py#iospec_outputs`
// (seed computation + done-contract grading). The measured defect this closes: the two readers
// read two DIFFERENT surfaces (block vs the retired `outputs:` frontmatter key), so a seat
// declaring on one was invisible to the other — 23 of 26 meet-transcript-summarizer dispositions
// read "none-declared" while their seats carried `## Outputs` blocks.
//
// The unification mechanism is two parsers of ONE grammar held equivalent by ONE fixture set
// (`team-kit/outputs-resolver-fixtures.json`) exercised by both sides' scheduled checks: this
// probe (hourly suite) and coord.py's selftest. This probe is therefore deliberately dumb — it
// asserts this side's parse against the shared file, case by case, plus the file-level read
// (`declaredOutputs`) on a real fixture tree. A grammar change that lands on one side only
// reddens here or there; it cannot land silently.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const HERE = __dirname;
const OUT_PATH = path.join(HERE, 'probe-outputs-resolver.out');
const FIXTURES = path.join(HERE, '..', '..', 'team-kit', 'outputs-resolver-fixtures.json');
const { parseDeclaredOutputs, declaredOutputs } = require('../cage-admission');

const start = Date.now();
const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function checkEq(claim, got, want) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`}`);
  if (!ok) failures.push(claim);
}

function main() {
  const fixtures = JSON.parse(fs.readFileSync(FIXTURES, 'utf8'));
  checkEq('the shared fixture set is non-trivial (>= 8 cases — a shrunken file is a shrunken contract)',
    fixtures.length >= 8, true);
  // D36 (2026-08-20): the `chat` bit is asserted on EVERY case, not only the ones that carry it
  // — `!!f.chat` reads absent as false, so a resolver that started reporting `chat: true`
  // everywhere reds on the other nine rows, not just on the two that are about it.
  for (const f of fixtures) {
    const got = parseDeclaredOutputs(f.text);
    checkEq(`fixture ${f.name}: ${f.why}`,
      { declared: got.declared, tokens: got.tokens, chat: !!got.chat },
      { declared: f.declared, tokens: f.tokens, chat: !!f.chat });
  }
  // The shared set must still CARRY the D36 pair — a fixture file that lost them would pass
  // every row above vacuously.
  checkEq('the shared set carries the D36 typed-`chat` case AND its prose negative control',
    [fixtures.some((f) => f.chat === true),
      fixtures.some((f) => f.name === 'chat-word-in-prose-is-not-a-declaration')],
    [true, true]);

  // The FILE-LEVEL read, on a real tree: `declaredOutputs` is the admission gate's entry point
  // and must be exactly parseDeclaredOutputs over the seat.md bytes — including the two absences
  // (no seat.md at all; a key-only descriptor, the retired surface, which declares NOTHING here).
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-outputs-resolver-'));
  try {
    const blockCase = fixtures.find((f) => f.name === 'block-with-tokens');
    const keyCase = fixtures.find((f) => f.name === 'key-only-frontmatter');
    for (const [seat, f] of [['blocky', blockCase], ['keyed', keyCase]]) {
      fs.mkdirSync(path.join(tmp, 'seats', seat), { recursive: true });
      fs.writeFileSync(path.join(tmp, 'seats', seat, 'seat.md'), f.text);
    }
    checkEq('declaredOutputs(file) on the block-only seat = the fixture tokens',
      declaredOutputs(tmp, 'blocky'), blockCase.tokens);
    checkEq('declaredOutputs(file) on the key-only seat = [] — the retired frontmatter key is not a declaration surface',
      declaredOutputs(tmp, 'keyed'), []);
    checkEq('declaredOutputs(file) on an absent seat.md = [] — absence is not a crash',
      declaredOutputs(tmp, 'ghost'), []);
  } finally {
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

try {
  main();
} catch (err) {
  say(`FAIL probe threw: ${err.stack || err.message}`);
  failures.push('probe threw');
}
const exitCode = failures.length ? 1 : 0;
say('');
say(exitCode
  ? `RESULT: FAIL — ${failures.length} failing check(s): ${failures.join(' · ')}`
  : 'RESULT: PASS — the JS half of the shared declared-outputs resolver matches every case of '
    + 'the shared fixture set (coord.py selftest holds the Python half to the same file), and '
    + 'the file-level read agrees on block-only, key-only and absent seats.');
say(`WALL_MS ${Date.now() - start}`);
say(`EXIT ${exitCode}`);
fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n');
console.log(lines.join('\n'));
process.exit(exitCode);
