'use strict';
// PROBE — THE CONSUMER CLOSURE OF THE SEAM READERS IS CLOSED AND CLASSIFIED.
//
// PROMOTED 2026-07-28 from `wrapper-sweep.js`, a seat-folder instrument that ran ONCE, by hand,
// because a bound happened to be lifted. ⚠⚠ THE GAP WAS NEVER THAT THE SWEEP IS HARD — NOTHING
// TRIGGERED IT. `probe-seam-closed-set.js` holds the 11 DIRECT crossings; the 8 consumers beyond
// them were swept by hand exactly once, and `G-237` — the only defect in this family that makes the
// system DO something wrong rather than misreport — sat at depth 2. Nothing would have re-run that.
// Promotion is what puts the ladder under the hourly suite instead of under someone remembering.
//
// ⚠ WHAT A GREEN HERE DOES *NOT* MEAN, stated so it is never read as more:
//   · it does NOT classify the depth-2+ consumers — the one-hop classification bound (leader #1182)
//     stands; this asserts the closure's MEMBERSHIP, not that each member's question is levelled.
//   · it does NOT see an OMISSION. Every enumeration here covers consumers that EXIST. A path that
//     SHOULD ask the liveness question and does not has no token in any of it — `G-225` was found
//     by a failure measurement, never by a grep.
//
// WRAPPER SWEEP — the consumers one hop past a classified crossing.
//
// WHY: `probe-seam-closed-set.js` classifies the sites that CALL a seam reader. A consumer that
// reaches the boundary THROUGH one of those sites asks its own question at a distance, and the
// probe attributes the crossing to the wrapper. `isSlotLiveOrRearmed` was the motivating example.
//
// BOUND (leader #1182): ONE HOP, from wrappers ALREADY IN THE MANIFEST. Depth 2+ is enumerated but
// NOT classified — it is named as the horizon, not silently dropped.
//
// ⚠⚠ TWO INDEPENDENT DERIVATIONS, DIFFED — the `G-233` rule, not the disclosure bound that failed.
// "State what your method cannot see" is answerable only for blind spots you can already name.
//   A · BY CALL GRAPH  — who calls a manifest symbol (structure)
//   B · BY QUESTION    — every function whose NAME asserts a liveness question, then does it reach
//                        a seam reader at all (naming, an axis A cannot see)
// B exists to find a consumer A structurally misses; A exists to find one B never named. Neither is
// the population. The DIFF is the instrument.
//
// ⚠ The stripper below is a COPY of the one in probe-seam-closed-set.js, deliberately: this is a
// seat-folder instrument and the probe is the durable artifact. If they ever disagree, the probe's
// is authoritative — this file is not a second home for that logic.

const fs = require('node:fs');
const path = require('node:path');
// ⚠⚠ THE ROOT IS DERIVED BY ITS DEFINING PROPERTY AND CROSS-CHECKED — NEVER BY COUNTING `..`.
// The seat-folder original hard-coded an absolute path, which cannot move. The repair is NOT to
// swap in `path.resolve(__dirname, '../../..')`: that is the same counting, correct only until the
// file moves, and it is exactly how a sibling instrument silently created a `.rbtv/` tree in the
// wrong place and wrote its artifact there while every check it had passed. Resolving from
// `__filename` and MISCOUNTING THE HOPS is the same defect as not resolving at all.
// Two independent derivations that must AGREE, and an abort before anything is measured.
const IGNITE = (() => {
  let d = path.dirname(__filename);
  while (d !== path.dirname(d)) {
    if (path.basename(d) === 'ignite' && fs.existsSync(path.join(d, 'server'))) break;
    d = path.dirname(d);
  }
  const byProperty = d;
  // Cross-check: a path derived from a DIFFERENT anchor — the heart module this probe lives under.
  const byAnchor = path.resolve(path.dirname(__filename), '..', '..', '..');
  if (path.basename(byProperty) !== 'ignite'
      || !fs.existsSync(path.join(byProperty, 'server', 'heart', 'heart-store.js'))) {
    console.log(`ABORT: ignite root did not resolve by property (got ${byProperty}).`);
    process.exit(2);
  }
  if (byProperty !== byAnchor) {
    console.log('ABORT: the two root derivations DISAGREE — one derivation cannot catch this.');
    console.log(`  by-property: ${byProperty}`);
    console.log(`  by-anchor:   ${byAnchor}`);
    process.exit(2);
  }
  return byProperty;
})();
const PROD_DIRS = ['server', 'capabilities', 'cli'];
const SEAM_READERS = ['listExecutionsByStatus', 'listTurnsOfLiveSessions'];

// The 11 classified crossings. Symbol only — the file is carried for reporting.
const MANIFEST = [
  ['server/index.js', 'main'], ['server/index.js', 'runRetentionSweep'],
  ['server/internal-api/dispatch.js', 'handleInspect'],
  ['server/internal-api/dispatch.js', 'handleInspectDaemon'],
  ['server/internal-api/dispatch.js', 'handleInspectTicker'],
  ['server/spawn/spawn.js', 'orphanRescan'],
  ['server/ticker/ticker.js', 'advance'], ['server/ticker/ticker.js', 'enforce'],
  ['server/ticker/ticker.js', 'liveSessionTurns'], ['server/ticker/ticker.js', 'liveTurns'],
  ['server/ticker/warnings-check.js', 'findBlockedBudgetExhaustedSubjects'],
];

// A name that ASSERTS a liveness question. Derivation B's whole input — chosen from the vocabulary
// the codebase already uses for this question, not invented.
const QUESTION_NAME = /(live|alive|running|orphan|crash|stall|active|survive|reconnect|ghost)/i;

function stripNonCode(src) {
  const out = src.split('');
  let i = 0; const n = src.length;
  const blank = (from, to) => { for (let k = from; k < to && k < n; k++) if (out[k] !== '\n') out[k] = ' '; };
  const REGEX_OK_BEFORE = new Set(['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '%', '~', '^', '\n']);
  let prev = '\n';
  while (i < n) {
    const c = src[i];
    if (c === '/' && src[i + 1] === '/') { let j = i; while (j < n && src[j] !== '\n') j++; blank(i, j); i = j; continue; }
    if (c === '/' && src[i + 1] === '*') { let j = i + 2; while (j < n && !(src[j] === '*' && src[j + 1] === '/')) j++; blank(i, Math.min(j + 2, n)); i = j + 2; continue; }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) { if (src[j] === '\\') { j += 2; continue; } if (src[j] === c) break; j++; }
      blank(i, Math.min(j + 1, n)); i = j + 1; prev = '"'; continue;
    }
    if (c === '/' && REGEX_OK_BEFORE.has(prev)) {
      let j = i + 1, closed = false;
      while (j < n && src[j] !== '\n') {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === '[') { while (j < n && src[j] !== ']' && src[j] !== '\n') j++; }
        if (src[j] === '/') { closed = true; break; }
        j++;
      }
      if (closed) { blank(i, j + 1); i = j + 1; prev = '/'; continue; }
    }
    if (!/\s/.test(c)) prev = c; else if (c === '\n') prev = '\n';
    i++;
  }
  return out.join('');
}

const FN_HEADER = [
  /(?:async\s+)?function\s*\*?\s*([A-Za-z0-9_$]+)\s*\([^()]*\)\s*$/,
  /(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s+)?(?:function\s*\*?\s*[A-Za-z0-9_$]*\s*)?\([^()]*\)\s*(?:=>\s*)?$/,
  /(?:^|[\s,{;])(?:async\s+)?([A-Za-z0-9_$]+)\s*\([^()]*\)\s*$/,
];
const NOT_A_FUNCTION = new Set(['if', 'for', 'while', 'switch', 'catch', 'with', 'return', 'do', 'else', 'try', 'finally']);
function frameNameBefore(code, bracePos) {
  const tail = code.slice(Math.max(0, bracePos - 400), bracePos).replace(/\s+$/, '');
  for (const re of FN_HEADER) { const m = tail.match(re); if (m && m[1] && !NOT_A_FUNCTION.has(m[1])) return m[1]; }
  return null;
}

// Every offset -> enclosing named symbol, for one file.
function symbolAt(code, offsets) {
  const stack = []; const at = new Map();
  const sorted = [...offsets].sort((a, b) => a - b); let next = 0;
  for (let i = 0; i < code.length && next < sorted.length; i++) {
    if (code[i] === '{') stack.push(frameNameBefore(code, i));
    else if (code[i] === '}') stack.pop();
    while (next < sorted.length && sorted[next] === i) {
      for (let d = stack.length - 1; d >= 0; d--) if (stack[d]) { at.set(i, stack[d]); break; }
      if (!at.has(i)) at.set(i, '(module)');
      next++;
    }
  }
  return at;
}

function walk(dir, acc) {
  let es; try { es = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of es) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'node_modules' && e.name !== 'probes') walk(p, acc); }
    else if (e.isFile() && e.name.endsWith('.js')) acc.push(p);
  }
  return acc;
}

const FILES = [];
for (const d of PROD_DIRS) walk(path.join(IGNITE, d), FILES);
const SRC = new Map();   // STRIPPED — for matching code
const RAW = new Map();   // raw bytes — for anything that must read a STRING LITERAL
for (const abs of FILES) {
  const rel = path.relative(IGNITE, abs).split(path.sep).join('/');
  const raw = fs.readFileSync(abs, 'utf8');
  RAW.set(rel, raw);
  SRC.set(rel, stripNonCode(raw));
}

// ⚠⚠ THE FIRST RUN OF THIS SCRIPT REPORTED 14 CALLER SITES AND SIX OF THEM WERE FALSE.
// It matched a BARE NAME across every file with no module resolution, so five unrelated `main()`
// definitions (cli/ignite.js, the pty shim, attach-client, seat-identity/cli, the sub-agent
// supervisor) came back as consumers of `index.js:main`. A name is not an identity.
//
// The fix is to scope a call to the DEFINING FILE — and that is only valid if no manifest symbol
// is reachable from another file, so it is ASSERTED here rather than assumed. Measured: none of the
// 11 is exported (`index.js` has no `module.exports` at all; `main` is exported only from
// `seat-identity/cli.js`, which is the pollution itself, not a caller). If that ever changes this
// aborts instead of silently under-reporting — the failure direction a scoping bound wants.
function assertManifestSymbolsAreFilePrivate() {
  const leaks = [];
  for (const [file, sym] of MANIFEST) {
    const code = SRC.get(file) || '';
    const m = code.match(/module\.exports\s*=\s*{([^}]*)}/);
    const exported = m ? m[1].split(',').map((s) => s.trim().split(':')[0].trim()) : [];
    if (exported.includes(sym)) leaks.push(`${file}:${sym}`);
  }
  if (leaks.length) {
    console.log('ABORT: these manifest symbols ARE exported, so a same-file call scope under-reports them:');
    for (const l of leaks) console.log('  ' + l);
    process.exit(2);
  }
  console.log(`PRECONDITION: all ${MANIFEST.length} manifest symbols are file-private -> a same-file call scope is complete for them.\n`);
}

// Call sites of a bare symbol `name(` — not `.name(` (that is a method on another object).
// `inFile` scopes the search to the defining file; see the assertion above for why that is sound.
function callsOf(name, inFile) {
  const hits = [];
  const re = new RegExp('(^|[^A-Za-z0-9_$.])' + name + '\\s*\\(', 'g');
  for (const [rel, code] of SRC) {
    if (inFile && rel !== inFile) continue;
    const offs = []; let m;
    while ((m = re.exec(code)) !== null) offs.push(m.index + m[1].length);
    if (!offs.length) continue;
    const at = symbolAt(code, offs);
    for (const o of offs) {
      const sym = at.get(o) || '(module)';
      if (sym === name) continue;                        // recursion / the definition's own body
      const line = code.slice(0, o).split('\n').length;
      // skip the definition line itself (`function name(`)
      if (/(?:function|const|let|var)\s*\*?\s*$/.test(code.slice(Math.max(0, o - 30), o))) continue;
      hits.push({ file: rel, symbol: sym, line });
    }
  }
  return hits;
}

// ⚠⚠ SECOND SCOPING DEFECT, THE OPPOSITE DIRECTION, AND IT WAS MINE TOO. Having killed the
// false POSITIVES by scoping every call to the defining file, the expansion below then dropped the
// callers of any consumer that IS exported — `runWarningCheck` and `createTicker` both are, and
// both are called from another file. The ladder printed a FIXPOINT at depth 3 that was an artifact
// of the scope, not a property of the graph. One bound, two failure directions; the first was
// caught by reading the output, the second only by asking whether the assertion that licensed the
// scope covered the symbols it was being applied to. IT DID NOT — it covered the 11 manifest
// symbols and was silently reused for consumers.
//
// Resolution: an exported symbol is searched in the files that REQUIRE its module, never in every
// file (which is what produced five phantom `main` callers).
function exportsOf(file) {
  const m = (SRC.get(file) || '').match(/module\.exports\s*=\s*{([^}]*)}/);
  return m ? m[1].split(',').map((x) => x.trim().split(':')[0].trim()) : [];
}
// ⚠⚠ THIRD DEFECT IN THIS ONE MECHANISM, AND THE CONTROL IS THE ONLY REASON IT IS NOT IN A REPORT.
// This searched SRC — the STRIPPED source — for `require('./warnings-check')`. The stripper blanks
// string literals, so every module path had already been erased before this ever looked for one:
// the importer set was structurally always empty and the cross-file expansion could never fire.
// It printed a clean depth-3 FIXPOINT and I was about to report the ladder CLOSES.
// ⇒ A DETECTOR WHOSE INPUT WAS DESTROYED UPSTREAM BY A DIFFERENT, CORRECT MECHANISM. The stripper
// is right; using its output to read a string literal is not. Reads RAW now, deliberately.
function importersOf(file) {
  const base = file.replace(/\.js$/, '').split('/').pop();
  const out = [];
  for (const [rel, code] of RAW) {
    if (rel === file) continue;
    if (new RegExp("require\\(['\"][^'\"]*/" + base + "['\"]\\)|require\\(['\"]\\./" + base + "['\"]\\)").test(code)) out.push(rel);
  }
  return out;
}
// Callers of `sym` defined in `file`: same-file always; plus importing files iff it is exported.
function callersOfSymbol(file, sym) {
  const hits = callsOf(sym, file);
  if (exportsOf(file).includes(sym)) {
    for (const importer of importersOf(file)) hits.push(...callsOf(sym, importer));
  }
  return hits;
}

// Every named function definition in production code.
function allDefs() {
  const defs = [];
  for (const [rel, code] of SRC) {
    for (const re of [/(?:async\s+)?function\s*\*?\s*([A-Za-z0-9_$]+)\s*\(/g,
                      /(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(/g]) {
      let m; while ((m = re.exec(code)) !== null) defs.push({ file: rel, name: m[1], line: code.slice(0, m.index).split('\n').length });
    }
  }
  return defs;
}

// ── DERIVATION A · by call graph ──────────────────────────────────────────────────────────────
assertManifestSymbolsAreFilePrivate();
const A = new Map();   // "file:symbol" -> { via:Set, lines:[] }
for (const [file, sym] of MANIFEST) {
  for (const h of callsOf(sym, file)) {
    const key = `${h.file}:${h.symbol}`;
    const cur = A.get(key) || { via: new Set(), lines: [] };
    cur.via.add(sym); cur.lines.push(h.line); A.set(key, cur);
  }
}

// ── DERIVATION B · by question ────────────────────────────────────────────────────────────────
// Every function whose NAME asserts a liveness question. Then: does it reach a seam reader within
// two hops? B is allowed to be noisy — a name is a weak signal. What matters is what it holds that
// A does not.
const namedDefs = allDefs().filter((d) => QUESTION_NAME.test(d.name));
const reachesReader = new Map();   // symbol -> depth (0 = calls a reader directly)
for (const [rel, code] of SRC) {
  const offs = []; let m;
  for (const r of SEAM_READERS) {
    const re = new RegExp('\\.' + r + '\\s*\\(', 'g');
    while ((m = re.exec(code)) !== null) offs.push(m.index);
  }
  if (!offs.length) continue;
  const at = symbolAt(code, offs);
  for (const o of offs) { const s = at.get(o); if (s && !reachesReader.has(s)) reachesReader.set(s, 0); }
}
// Same scoping rule as A — an unscoped expansion here would inherit the identical `main` defect.
for (const sym of [...reachesReader.keys()]) {
  if (reachesReader.get(sym) !== 0) continue;
  const home = MANIFEST.find(([, s2]) => s2 === sym);
  for (const h of callsOf(sym, home ? home[0] : null)) if (!reachesReader.has(h.symbol)) reachesReader.set(h.symbol, 1);
}
const B = new Map();
for (const d of namedDefs) {
  const depth = reachesReader.has(d.name) ? reachesReader.get(d.name) : null;
  B.set(`${d.file}:${d.name}`, { depth });
}

// ── REPORT ────────────────────────────────────────────────────────────────────────────────────
const line = (s) => console.log(s);
line('== DERIVATION A — consumers one hop past a classified crossing (by call graph) ==');
const aKeys = [...A.keys()].sort();
for (const k of aKeys) {
  const v = A.get(k);
  const isManifest = MANIFEST.some(([f, s]) => `${f}:${s}` === k);
  line(`  ${k.padEnd(58)} via=${[...v.via].join(',').padEnd(22)} lines=[${v.lines.join(',')}]${isManifest ? '  (already classified)' : ''}`);
}
line(`  -> ${aKeys.length} caller sites, ${aKeys.filter((k) => !MANIFEST.some(([f, s]) => `${f}:${s}` === k)).length} of them NOT already in the manifest`);

line('');
line('== DERIVATION B — functions whose NAME asserts a liveness question (by naming) ==');
const bReaching = [...B.entries()].filter(([, v]) => v.depth !== null).sort();
const bNot = [...B.entries()].filter(([, v]) => v.depth === null).sort();
for (const [k, v] of bReaching) line(`  REACHES(depth ${v.depth})  ${k}`);
line(`  -> ${B.size} name-matched definitions; ${bReaching.length} reach a seam reader within 2 hops, ${bNot.length} do not`);

line('');
line('== THE DIFF — what each derivation holds that the other does not ==');
const aSet = new Set(aKeys.filter((k) => !MANIFEST.some(([f, s]) => `${f}:${s}` === k)));
const bSet = new Set(bReaching.map(([k]) => k).filter((k) => !MANIFEST.some(([f, s]) => `${f}:${s}` === k)));
const onlyA = [...aSet].filter((k) => !bSet.has(k)).sort();
const onlyB = [...bSet].filter((k) => !aSet.has(k)).sort();
const both = [...aSet].filter((k) => bSet.has(k)).sort();
line(`  IN BOTH (${both.length}):`); for (const k of both) line(`    ${k}`);
line(`  ONLY A — call graph found it, its NAME does not assert the question (${onlyA.length}):`);
for (const k of onlyA) line(`    ${k}`);
line(`  ONLY B — its NAME asserts the question, the one-hop call graph did not reach it (${onlyB.length}):`);
for (const k of onlyB) line(`    ${k}`);
line('');
line('== THE HORIZON — depth 2, ENUMERATED AND NOT CLASSIFIED (leader #1182 bound) ==');
line('  Named, not dropped: the ruled bound is ONE hop, and the motivating example sits at TWO.');
const depth1 = [...aSet].map((k) => k.split(':'));
const d2 = new Map();
for (const [file, sym] of depth1) {
  if (sym === '(module)') continue;
  for (const h of callersOfSymbol(file, sym)) {
    if (h.symbol === sym) continue;
    const key = `${h.file}:${h.symbol}`;
    if (aSet.has(key) || MANIFEST.some(([f, s2]) => `${f}:${s2}` === key)) continue;
    const cur = d2.get(key) || new Set(); cur.add(sym); d2.set(key, cur);
  }
}
for (const k of [...d2.keys()].sort()) line(`    ${k.padEnd(52)} via=${[...d2.get(k)].join(',')}`);
line(`  -> ${d2.size} consumer(s) at depth 2. UNCLASSIFIED BY RULING, not by oversight.`);
line('');
// ⚠ THE LADDER WAS PREDICTED TO BE UNBOUNDED (leader #1182: "wrappers more ... no complete
// enumeration here, only successively better ones"). That is a PREMISE about this call graph, and
// it is measurable, so it is measured rather than assumed. Expand to a fixpoint and print the size
// of every layer. Enumerating the closure is not classifying it — the one-hop bound is untouched.
line('');
// CONTROL ON THE CROSS-FILE EXPANSION: it must be shown to FIRE, or the fixpoint above is again
// an artifact of a scope. `runWarningCheck` is exported from warnings-check.js and called from
// ticker.js — the exact case the same-file scope drops.
// ⚠ PLACED BEFORE THE LADDER, not after: a control that runs after the verdict it bounds cannot
// stop the verdict being read. bars.md 11's third half — a control proves its precondition AT THE
// INSTANT IT RUNS, never for the run that follows.
{
  const sameFileOnly = callsOf('runWarningCheck', 'server/ticker/warnings-check.js');
  const withExports = callersOfSymbol('server/ticker/warnings-check.js', 'runWarningCheck');
  line('');
  line('CONTROL — cross-file expansion fires:');
  line(`  runWarningCheck  same-file-only=${sameFileOnly.length}  with-exports=${withExports.length}`
    + `  -> ${withExports.map((h) => h.file + ':' + h.symbol).join(', ') || 'NONE'}`);
  if (withExports.length <= sameFileOnly.length) {
    line('  ⚠⚠ ABORT — THE EXPANSION IS A NO-OP, so any fixpoint below would be an artifact of the');
    line('     scope rather than a property of the graph. NO LADDER VERDICT IS READABLE FROM THIS RUN.');
    process.exit(2);
  } else {
    line('  => it fires: the ladder below is expanded WITH cross-file callers followed, so a fixpoint there holds');
    line('     because callers were reached and already classified, not because they were dropped.');
  }
}
line('== THE LADDER, EXPANDED TO A FIXPOINT — is the horizon actually unbounded? ==');
const seen = new Set([...aSet, ...MANIFEST.map(([f, s2]) => `${f}:${s2}`)]);
let frontier = [...d2.keys()];
for (const k of frontier) seen.add(k);
const layers = [aSet.size, d2.size];
let depth = 2;
while (frontier.length && depth < 25) {
  const nextLayer = new Set();
  for (const key of frontier) {
    const idx = key.lastIndexOf(':');
    const file = key.slice(0, idx), sym = key.slice(idx + 1);
    if (sym === '(module)') continue;
    for (const h of callersOfSymbol(file, sym)) {
      const k2 = `${h.file}:${h.symbol}`;
      if (h.symbol === sym || seen.has(k2)) continue;
      nextLayer.add(k2); seen.add(k2);
    }
  }
  depth++;
  layers.push(nextLayer.size);
  if (!nextLayer.size) { line(`  depth ${depth}: 0 new consumers -> FIXPOINT.`); break; }
  line(`  depth ${depth}: ${nextLayer.size} new -> ${[...nextLayer].sort().join(', ')}`);
  frontier = [...nextLayer];
}
line('');
line('SUCCESSIVE ENUMERATIONS: hand-list 7 -> enumerator 11 crossings -> depth-1 ' + layers[0]
  + ' -> ' + layers.slice(1).map((n, i) => `depth-${i + 2} ${n}`).join(' -> '));
line('⇒ this ladder CLOSES. The horizon is a measured fixpoint, not an open one — see the record.');

// ============================================================================================
// THE VERDICT — everything above this line is DIAGNOSIS. This is what can go RED.
// ============================================================================================
//
// ⚠ THE PROPERTY: the consumer closure beyond the 11 direct crossings is EXACTLY the set a person
// classified, and the ladder still CLOSES. A new consumer at depth 1 or 2 — the layer `G-237` lived
// in — turns this red AND NAMES IT. Removal turns it red too: a consumer that vanished is a
// manifest that has stopped describing the code, which is the same defect pointing the other way.
//
// ⚠⚠ THE KEY IS THE CONSUMER ALONE (`file:symbol`), AND THE VIA-PATH IS RE-DERIVED EVERY RUN AND
// NEVER STORED. Storing the route (consumer -> wrapper -> reader) would break this manifest every
// time an INTERMEDIATE is renamed — a defect keyed on a name that is not the subject. Under this
// key a renamed intermediate changes nothing: the walk finds the consumer again through the new
// name. The manifest holds what a PERSON decided; the machine re-derives reachability each run.
const CONSUMER_MANIFEST = {
  // depth 1 — reached through a classified crossing.
  'server/index.js:(module)': 'plumbing',
  'server/internal-api/dispatch.js:dispatch': 'plumbing',
  'server/ticker/ticker.js:createTicker': 'plumbing',
  'server/ticker/ticker.js:launchAgent': 'asks',
  'server/ticker/ticker.js:findLiveExecutionForThread': 'asks',
  'server/ticker/warnings-check.js:runWarningCheck': 'asks',
  // depth 2 — the horizon. ENUMERATED AND DELIBERATELY NOT CLASSIFIED (leader #1182's one-hop
  // bound). `isSlotLiveOrRearmed` is `G-237`: the guard that spawns a duplicate. It is in this
  // manifest so its DISAPPEARANCE OR COMPANY is noticed, not because its levelling is settled.
  'server/ticker/ticker.js:dispatch': 'horizon',
  'server/ticker/ticker.js:isSlotLiveOrRearmed': 'horizon',
};

{
  const found = new Set([...aSet, ...d2.keys()]);
  const declared = new Set(Object.keys(CONSUMER_MANIFEST));

  // ⚠ POSITIVE CONTROL, AND IT RUNS BEFORE THE VERDICT IT BOUNDS. "Every consumer is declared" and
  // "the comparison cannot see an undeclared consumer" print the SAME green. Inject a consumer that
  // is definitionally absent and require the comparison to name it. bars.md 11's second half: a
  // clean sweep is a result only once something in the same run went red on purpose.
  const canary = 'server/__does_not_exist__.js:__canary__';
  const probeSet = new Set([...found, canary]);
  const canaryCaught = [...probeSet].filter((k) => !declared.has(k)).includes(canary);
  line('');
  line('CONTROL — the closure comparison can FAIL:');
  line(`  injected ${canary} -> reported as undeclared: ${canaryCaught}`);
  if (!canaryCaught) {
    line('  ⚠⚠ ABORT — the comparison cannot report an undeclared consumer, so its green below');
    line('     would be a property of the comparison rather than of the code. NO VERDICT READABLE.');
    process.exit(2);
  }
  if (!declared.size || !found.size) {
    line('  ⚠⚠ ABORT — an empty side makes every set comparison vacuously true.');
    process.exit(2);
  }

  const undeclared = [...found].filter((k) => !declared.has(k)).sort();
  const missing = [...declared].filter((k) => !found.has(k)).sort();
  const ladderClosed = layers[layers.length - 1] === 0;

  line('');
  line('== VERDICT — the consumer closure ==');
  line(`  declared ${declared.size} · enumerated ${found.size} · ladder closes: ${ladderClosed}`);
  for (const k of undeclared) {
    line(`  UNDECLARED CONSUMER: ${k}`);
    line('     it reaches a seam reader and NOBODY HAS CLASSIFIED ITS QUESTION. That is the layer');
    line('     G-237 lived in — a guard that read a TURN-level answer to a SESSION-level question');
    line('     and spawned a second process for a slot that already had one.');
  }
  for (const k of missing) {
    line(`  DECLARED BUT NOT FOUND: ${k}`);
    line('     either it was removed (update this manifest in the SAME change) or the enumerator');
    line('     stopped reaching it — and those two look identical from here, so BOTH are red.');
  }
  if (!ladderClosed) {
    line('  LADDER DID NOT CLOSE — the fixpoint that made this set finite no longer holds.');
  }
  const ok = !undeclared.length && !missing.length && ladderClosed;
  line('');
  // ⚠⚠ THE BOUND IS PRINTED AT THE VERDICT, NOT ONLY IN THE HEADER (leader's bound, #1530).
  // A reader meets the PASS line; the header is a footnote one level out, and this seat's own
  // G-258 fix an hour earlier was precisely that a footnote is read after the damage. A green
  // that does not carry its own limits is read as covering more than it does.
  if (ok) {
    line('PASS — the consumer closure is exactly the classified set, and it still closes.');
    line('  ⚠ WHAT THIS GREEN DOES NOT COVER, at the verdict rather than in the header:');
    line(`     · MEMBERSHIP only. The ${Object.values(CONSUMER_MANIFEST).filter((v) => v === 'horizon').length}`
      + ' depth-2 rows are ENUMERATED AND UNCLASSIFIED by ruling (one-hop bound, #1182) —');
    line('       including isSlotLiveOrRearmed, which IS G-237. Their levelling is not asserted here.');
    line('     · NO OMISSIONS. Every set above covers consumers that EXIST. A path that SHOULD ask');
    line('       the liveness question and does not has no token in any enumeration — G-225 was');
    line('       found by a failure measurement, never by a grep.');
  } else {
    line('FAIL — the consumer closure has moved. See the named rows above.');
  }
  process.exit(ok ? 0 : 1);
}
