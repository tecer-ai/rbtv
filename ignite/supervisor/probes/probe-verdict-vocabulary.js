#!/usr/bin/env node
'use strict';

// probe-verdict-vocabulary — the verdict enum is deleted. Engine product files must not
// compute or store the killed §1.7 words. Coord may still emit them until kit lands.

const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const ENGINE = path.join(HERE, '..');
const IGNITE = path.join(HERE, '..', '..');
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
check('seeding exports ONE verdict door table', seeding.VERDICT_DOOR && typeof seeding.VERDICT_DOOR === 'object');

const readyPy = fs.readFileSync(path.join(ENGINE, 'ready.py'), 'utf8');
const liveVerdicts = new Set();
for (const m of readyPy.matchAll(/rec\["verdict"\]\s*=\s*(.+)/g)) {
  for (const w of m[1].matchAll(/"([A-Z][A-Z-]*)"/g)) liveVerdicts.add(w[1]);
}
const door = seeding.VERDICT_DOOR || {};
for (const word of liveVerdicts) {
  check(`VERDICT_DOOR names live kit verdict ${word}`, Object.prototype.hasOwnProperty.call(door, word), word);
}
for (const word of Object.keys(door)) {
  check(`VERDICT_DOOR key ${word} is assigned by ready.py`, liveVerdicts.has(word), [...liveVerdicts].join(','));
}
const launchable = Object.entries(door).filter(([, v]) => v && v.launchable).map(([k]) => k);
check('only READY is launchable', launchable.length === 1 && launchable[0] === 'READY', JSON.stringify(launchable));
check('BLOCKED is waitable and not launchable', door.BLOCKED && door.BLOCKED.waitable === true && door.BLOCKED.launchable === false);
check('IDLE is neither launchable nor waitable', door.IDLE && door.IDLE.launchable === false && door.IDLE.waitable === false);

// The seven product files the killed enum could hide in. Component-relative since the
// component-first move: six stayed in `supervisor/` (this probe's own ENGINE root) and
// `attached-execution.js` left for `operator/`, so the home travels with the name.
const product = [
  'seeding.js', 'reconcile.js', 'execution-record.js', 'lane-watch.js',
  'ending-reads.js', 'owed-from-endings.js',
].map((n) => path.join(ENGINE, n))
  .concat([path.join(IGNITE, 'operator', 'attached-execution.js')]);

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
  //
  // ⚠ THE BORROW IS RESOLVED, NOT SUBSTRING-MATCHED. This row used to accept any line containing
  // the literal `supervisor/owed`, which held only while every borrower sat OUTSIDE `supervisor/`
  // and spelled it `require('../supervisor/owed')`. The component-first move made `seeding.js` and
  // `reconcile.js` siblings of `owed.js`, so the same borrow now reads `require('./owed')` and the
  // literal stopped matching — the row went red on correct code, and would have gone SILENT the
  // other way round had a borrower moved instead. Resolving the specifier against the borrowing
  // file's own directory asks the question the rule actually means, from any depth.
  const OWED = path.join(ENGINE, 'owed.js');
  const borrowsOwed = (line, file) => {
    const m = line.match(/require\(\s*['"]([^'"]+)['"]\s*\)/);
    if (!m) return false;
    const spec = m[1];
    if (!spec.startsWith('.')) return false;
    const resolved = path.resolve(path.dirname(file), spec);
    return resolved === OWED || `${resolved}.js` === OWED;
  };
  const owedLines = code.split('\n')
    .map((l, i) => [l, i + 1])
    .filter(([l]) => l.includes('deriveOwed'));
  const borrowed = owedLines.every(([l]) => borrowsOwed(l, file) || /deriveOwed\s*\(/.test(l));
  check(`${path.basename(file)} does not DEFINE deriveOwed — it may only borrow the supervisor's`,
    borrowed,
    `${file}: ${owedLines.filter(([l]) => !(borrowsOwed(l, file) || /deriveOwed\s*\(/.test(l))).map(([l, n]) => `${n}: ${l.trim()}`).join(' | ')}`);
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
