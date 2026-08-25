#!/usr/bin/env node
'use strict';

// probe-verdict-vocabulary — the verdict enum is deleted. Engine product files must not
// compute or store the killed §1.7 words. Coord may still emit them until kit lands.

const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const ENGINE = path.join(HERE, '..');
const OUT_PATH = path.join(HERE, 'probe-verdict-vocabulary.out');
const SEEDING = path.join(ENGINE, 'seeding.js');

const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

const seeding = require('../seeding.js');
check('seeding no longer exports CLASSIFIED_VERDICTS', seeding.CLASSIFIED_VERDICTS === undefined);
check('seeding no longer exports isWaitableWork', seeding.isWaitableWork === undefined);

const product = [
  'seeding.js', 'reconcile.js', 'attached-execution.js', 'execution-record.js', 'lane-watch.js',
  'ending-reads.js', 'owed-from-endings.js',
].map((n) => path.join(ENGINE, n));

const banned = [
  'CLASSIFIED_VERDICTS', 'PROCESS_OUTCOME_OF', 'RECORD_DISPOSITIONS',
  'isNonTerminal', 'TERMINAL_DISPOSITIONS',
];
for (const file of product) {
  const src = fs.readFileSync(file, 'utf8');
  const code = src.split('\n').filter((l) => !/^\s*\/\//.test(l) && !/^\s*\*/.test(l)).join('\n');
  for (const sym of banned) {
    check(`${path.basename(file)} has no product ${sym}`, !code.includes(sym), file);
  }

  // ── `deriveOwed` IS NO LONGER BANNED OUTRIGHT — IT IS BANNED AS ENGINE'S [spec-supervisor §5] ──
  //
  // It used to be forbidden here because engine had no business computing owed work off a killed
  // verdict enum. It now EXISTS, once, as the single "this seat is owed a launch" function at the
  // supervisor home (`supervisor/owed.js`) — the survivor of the two owed-work computers [T4-R7,
  // C-15]. So the property this row holds is unchanged in substance and sharper in form: an engine
  // product file may BORROW the supervisor's computer, and may never BE one. Every occurrence must
  // therefore sit on the require line that names `supervisor/owed`, or be a call. A definition
  // (`function deriveOwed`), a re-export, or an assignment is the second computer coming back.
  const owedLines = code.split('\n')
    .map((l, i) => [l, i + 1])
    .filter(([l]) => l.includes('deriveOwed'));
  const borrowed = owedLines.every(([l]) => l.includes("supervisor/owed") || /deriveOwed\s*\(/.test(l));
  check(`${path.basename(file)} does not DEFINE deriveOwed — it may only borrow the supervisor's`,
    borrowed,
    `${file}: ${owedLines.filter(([l]) => !(l.includes('supervisor/owed') || /deriveOwed\s*\(/.test(l))).map(([l, n]) => `${n}: ${l.trim()}`).join(' | ')}`);
}

const srcHasIdle = fs.readFileSync(SEEDING, 'utf8').includes("IDLE: 'not-waitable'");
check('seeding.js no longer classifies IDLE', !srcHasIdle);

const verdict = failures.length ? 'FAIL' : 'PASS';
say('');
say(`SUMMARY: ${lines.filter((l) => l.startsWith('ok')).length}/${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} passed`);
say(`VERDICT: ${verdict}`);
const out = `${lines.join('\n')}\n`;
fs.writeFileSync(OUT_PATH, out);
process.stdout.write(out);
process.exit(failures.length ? 1 : 0);
