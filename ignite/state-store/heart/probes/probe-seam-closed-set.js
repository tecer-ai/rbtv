'use strict';

// probe-seam-closed-set — every crossing of the SESSION/TURN boundary is CLASSIFIED.
//
// WHAT IT ASSERTS: the set of production call sites that read a live-ness question out of the heart
// store is a CLOSED SET. Each one carries a human judgment of the question it ASKS (SESSION: is the
// process there? / TURN: is the work in flight?) beside the level it actually READS. A new,
// unclassified crossing turns this probe RED.
//
// ⚠⚠ WHAT IT MUST NEVER ASSERT: "these four seams are mis-levelled." That would encode the defect as
// expected behaviour, so fixing G-226/227/228/229 would turn the probe RED and the tired repair is
// to revert the fix (bars.md 11's `hostile` shape — and exactly the trap probe-session-turn-split
// fell into on 2026-07-28, when an owner ratification turned a correct check red). This probe
// asserts CLASSIFICATION COVERAGE. Rule 4 below is what makes it go GREEN when a row is fixed.
//
// WHY A MANIFEST AND NOT A SWEEP: `asks` is a human judgment and the probe must never infer it. The
// site says what it READS; only a person can say what question it is ANSWERING. A probe deriving
// both would be comparing a thing to itself.
//
// ── WHAT THIS PROBE CANNOT SEE. Read this before treating its green as completeness. ──
//
//  1. AN OMISSION HAS NO TOKEN. A path that SHOULD cross the levels and does not is invisible to any
//     enumeration. `G-225` was found by a failure measurement, never by a grep. This probe covers
//     crossings that EXIST; it will never find a missing one.
//  2. TRANSITIVE CROSSINGS ARE ATTRIBUTED TO THE WRAPPER, NOT THE CONSUMER. `isSlotLiveOrRearmed`
//     asks its question through `findLiveExecutionForThread` -> `openTurnRows()`; the enumerator
//     sees the crossing at `openTurnRows` and the consumer's own question is TWO hops away.
//     ⚠⚠ THIS BLIND SPOT WAS NOT HYPOTHETICAL AND IS NO LONGER FULLY OPEN. The consumer ladder was
//     swept to a fixpoint (`FINDING-wrapper-sweep.md`): 11 crossings + 6 at depth 1 + 2 at depth 2,
//     closing at depth 3 — complete FOR CALLS, which does not make every ROUTE enumerated. All 19
//     were classified, and the sweep found `G-237` at depth 2: the guard against double-dispatching
//     a blocked slot, which SPAWNS a second process once a session outlives its turn.
//     ⇒ THE ENUMERATOR BELOW STILL SEES ONLY DIRECT CROSSINGS. A consumer reached through a wrapper
//     is invisible to it, so a NEW one appearing at depth 1+ does NOT turn this probe red. That
//     ladder was swept by hand and is not held closed by any check.
//  3. ROW EXISTENCE IS NOT ASSERTED, DELIBERATELY. Rule 3 checks a row's FORMAT (`G-<n>`), not that
//     it exists in a ledger: `issues.md` lives in a run package, not in this repo, so a ledger check
//     would silently skip in every workspace this probe ships to — and a check that skips where it
//     runs is worse than an absent one (it retires the attention that would cover the site).
//
// ── HOW THE POPULATION IS DERIVED ──
//
// By an enumerator over the production trees, never a hand-list (`G-179`). This probe exists because
// the hand-list it was specced from was SHORT: it named 7 crossings and 1 call site in dispatch.js;
// the enumerator finds 11 and 3. Two crossings (ticker.js's blocked re-dispatch and the crash
// sweep's `stalled` concat) had never been classified at all. AN AUDIT IS NOT THE DERIVATION.
//
// Comments and string literals are STRIPPED before matching, offsets preserved. That is not
// tidiness: `dispatch.js:95` names `listExecutionsByStatus()` inside a comment, and a grep counts it
// as a twelfth crossing that does not exist.

const fs = require('node:fs');
const path = require('node:path');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-seam-closed-set.out');
const igniteRoot = path.resolve(__dirname, '..', '..', '..');

// The two readers that ARE the boundary. `listExecutionsByStatus` reads jobs_log.status (TURN);
// `listTurnsOfLiveSessions` reads sessions.status = 'alive' (SESSION). Verified 2026-07-28: no
// production code outside heart-store.js queries session liveness by any other route.
const SEAM_READERS = ['listExecutionsByStatus', 'listTurnsOfLiveSessions'];
const PROD_DIRS = ['runtime', 'state-store', 'supervisor', 'operator', 'observation', 'ignite-cli'];

// ── THE MANIFEST — one entry per crossing, keyed file:symbol ───────────────────────────────────
//
// Keyed by SYMBOL, never by line: `teamview.py:1001` cites `coord.py:338-345` by line and is a decay
// hazard by construction. `asks` is the question, decided by a human. `row` is required iff they
// differ, and forbidden when they agree.
const MANIFEST = [
  // REMOVED at task 7.29 — `runtime/index.js:main`, the headed-reconnect crossing (asks SESSION,
  // reads TURN, row G-228). The pass it described re-attached headed sessions that survived a
  // restart to the server-owned pty; that module was deleted, so the call site is gone and with
  // it this crossing. THE PROBE CAUGHT IT: it failed `stale manifest entry ... the site was
  // deleted or renamed and the manifest was not`, which is exactly the decay this manifest's
  // symbol-keying exists to make loud. G-228 named a defect at a site that no longer exists —
  // whether that CLOSES the row is the leader's call, not this deletion's; nothing here rules it.

  { site: 'runtime/index.js:runRetentionSweep',
    asks: 'SESSION', reads: 'TURN', row: 'G-227',
    note: 'a live session\'s artifacts are never swept — the predicate is a TURN read' },

  { site: 'runtime/internal-api/dispatch.js:handleInspectDaemon',
    asks: 'SESSION', reads: 'TURN', row: 'G-226',
    note: 'live_agent_sessions count' },

  { site: 'runtime/internal-api/dispatch.js:handleInspectTicker',
    asks: 'SESSION', reads: 'TURN', row: 'G-234',
    note: 'the `liveSessions` list rendered by `inspect ticker` — same shape as G-226, one function '
        + 'away, and the hand-list that seeded this manifest missed it. MEASURED A=2 B=0 C=0 D=0 '
        + '-> follows TURN (seam-sweep S6), not read off the code' },

  { site: 'runtime/internal-api/dispatch.js:handleInspect',
    asks: 'TURN', reads: 'TURN',
    note: '`inspect executions --status <s>` — the operator asked for turns in a status; a '
        + 'read-through of the turn level, correctly levelled' },

  { site: 'supervisor/spawn/spawn.js:orphanRescan',
    asks: 'SESSION', reads: 'TURN', row: 'G-229' },

  { site: 'runtime/ticker/ticker.js:openTurnRows',
    asks: 'TURN', reads: 'TURN',
    note: '7.46 half one — WHICH TURN ROWS ARE STILL RECORDED OPEN? Renamed from `liveTurns` when '
        + '`jobs_log.status` was demoted to history [T4-R8]: the old name asserted liveness, which '
        + 'is the one thing this column may not be read for. It still asks a TURN question of a '
        + 'TURN column — correctly levelled — and every consumer re-asks liveness of the process.' },

  { site: 'runtime/ticker/ticker.js:liveSessionTurns',
    asks: 'SESSION', reads: 'SESSION',
    note: '7.46 half two — is the PROCESS there?' },

  { site: 'runtime/ticker/ticker.js:advance',
    asks: 'TURN', reads: 'TURN',
    note: 'blocked-slot re-dispatch. `blocked` is a turn state and the gate asks a turn question. '
        + 'Correctly levelled — but its sibling gate `isSlotLiveOrRearmed` reaches the boundary '
        + 'THROUGH `findLiveExecutionForThread`, and blind spot 2 above owns that.' },

  // ⚠ This entry said `:tick` when it was written from a reading of the code, and the enumerator
  // said `:enforce` — verified at ticker.js:1004. The manifest's first act was to correct its own
  // author, which is the whole reason the key is derived and not declared.
  { site: 'runtime/ticker/ticker.js:enforce',
    asks: 'SESSION', reads: 'SESSION',
    note: 'the crash sweep. ⚠ THIS ENTRY WAS DRAFTED AS reads=TURN WITH A LEDGER ROW, off the '
        + '`.concat(listExecutionsByStatus(\'stalled\'))` and the comment justifying it. MEASURED '
        + '(seam-sweep S6/S7 run) the SET follows SESSION: A=3 B=3 C=0 D=0 — correctly levelled, '
        + 'and the row was never filed. The `stalled` arm alone measures INCONCLUSIVE (that fixture '
        + 'creates no stalled turn), so what is asserted here is the SET\'s level, not the arm\'s.' },

  { site: 'runtime/ticker/warnings-check.js:findBlockedBudgetExhaustedSubjects',
    asks: 'TURN', reads: 'TURN',
    note: 'blocked-and-out-of-budget — a turn question, read at the turn level' },
];

// ── the stripper: comments and string literals out, byte offsets preserved ────────────────────
function stripNonCode(src) {
  const out = Buffer.from(src, 'utf8').toString('utf8').split('');
  let i = 0;
  const n = src.length;
  const blank = (from, to) => { for (let k = from; k < to && k < n; k++) if (out[k] !== '\n') out[k] = ' '; };
  // A `/` opens a regex literal only after one of these; otherwise it is division. Standard
  // heuristic — and the fixtures below prove it on a regex containing a quote, which is the one
  // case that would corrupt every later string boundary if it were mis-scanned.
  const REGEX_OK_BEFORE = new Set(['(', ',', '=', ':', '[', '!', '&', '|', '?', '{', '}', ';', '+', '-', '*', '%', '~', '^', '\n']);
  let prev = '\n';
  while (i < n) {
    const c = src[i];
    if (c === '/' && src[i + 1] === '/') {
      let j = i; while (j < n && src[j] !== '\n') j++;
      blank(i, j); i = j; continue;
    }
    if (c === '/' && src[i + 1] === '*') {
      let j = i + 2; while (j < n && !(src[j] === '*' && src[j + 1] === '/')) j++;
      blank(i, Math.min(j + 2, n)); i = j + 2; continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      let j = i + 1;
      while (j < n) {
        if (src[j] === '\\') { j += 2; continue; }
        if (src[j] === c) break;
        j++;
      }
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
    if (!/\s/.test(c)) prev = c;
    else if (c === '\n') prev = '\n';
    i++;
  }
  return out.join('');
}

// ── attribution: the innermost NAMED function frame containing an offset ──────────────────────
const FN_HEADER = [
  /(?:async\s+)?function\s*\*?\s*([A-Za-z0-9_$]+)\s*\([^()]*\)\s*$/,
  /(?:const|let|var)\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s+)?(?:function\s*\*?\s*[A-Za-z0-9_$]*\s*)?\([^()]*\)\s*(?:=>\s*)?$/,
  /(?:^|[\s,{;])(?:async\s+)?([A-Za-z0-9_$]+)\s*\([^()]*\)\s*$/,
];
const NOT_A_FUNCTION = new Set(['if', 'for', 'while', 'switch', 'catch', 'with', 'return', 'do', 'else', 'try', 'finally']);

function frameNameBefore(code, bracePos) {
  const tail = code.slice(Math.max(0, bracePos - 400), bracePos).replace(/\s+$/, '');
  for (const re of FN_HEADER) {
    const m = tail.match(re);
    if (m && m[1] && !NOT_A_FUNCTION.has(m[1])) return m[1];
  }
  return null;
}

// Returns [{ offset, line, reader, symbol }] for one file's source.
function crossingsIn(relFile, src) {
  const code = stripNonCode(src);
  const found = [];
  for (const reader of SEAM_READERS) {
    const re = new RegExp('\\.' + reader + '\\s*\\(', 'g');
    let m;
    while ((m = re.exec(code)) !== null) found.push({ offset: m.index, reader });
  }
  if (!found.length) return [];

  // One pass over the braces; each frame remembers the name of the function that opened it.
  const stack = [];
  const frameAt = new Map();
  const sorted = found.slice().sort((a, b) => a.offset - b.offset);
  let next = 0;
  for (let i = 0; i < code.length && next < sorted.length; i++) {
    if (code[i] === '{') stack.push(frameNameBefore(code, i));
    else if (code[i] === '}') stack.pop();
    while (next < sorted.length && sorted[next].offset === i) {
      for (let d = stack.length - 1; d >= 0; d--) if (stack[d]) { frameAt.set(i, stack[d]); break; }
      next++;
    }
  }
  return sorted.map((f) => ({
    reader: f.reader,
    line: src.slice(0, f.offset).split('\n').length,
    symbol: frameAt.get(f.offset) || '(module)',
    site: relFile + ':' + (frameAt.get(f.offset) || '(module)'),
  }));
}

function walkJs(dir, acc) {
  let entries;
  try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name === 'node_modules' || e.name === 'probes') continue;
      walkJs(p, acc);
    } else if (e.isFile() && e.name.endsWith('.js')) {
      acc.push(p);
    }
  }
  return acc;
}

function enumerate() {
  const files = [];
  for (const d of PROD_DIRS) walkJs(path.join(igniteRoot, d), files);
  const sites = new Map(); // site -> { site, readers:Set, lines:[] }
  for (const abs of files) {
    const rel = path.relative(igniteRoot, abs).split(path.sep).join('/');
    for (const c of crossingsIn(rel, fs.readFileSync(abs, 'utf8'))) {
      const cur = sites.get(c.site) || { site: c.site, readers: new Set(), lines: [] };
      cur.readers.add(c.reader);
      cur.lines.push(c.line);
      sites.set(c.site, cur);
    }
  }
  return { fileCount: files.length, sites };
}

// ── the four rules ────────────────────────────────────────────────────────────────────────────
function applyRules(sites) {
  const failures = [];
  const byKey = new Map(MANIFEST.map((e) => [e.site, e]));

  for (const site of [...sites.keys()].sort()) {
    if (!byKey.has(site)) failures.push(`unclassified crossing: ${site} (rule 1) — a person must decide what question it asks`);
  }
  for (const e of MANIFEST) {
    if (!sites.has(e.site)) failures.push(`stale manifest entry: ${e.site} (rule 2) — the site was deleted or renamed and the manifest was not`);
  }
  for (const e of MANIFEST) {
    const mismatched = e.asks !== e.reads;
    if (mismatched && !/^G-\d+$/.test(e.row || '')) failures.push(`undocumented mismatch: ${e.site} asks ${e.asks} reads ${e.reads} with no ledger row (rule 3)`);
    if (!mismatched && e.row) failures.push(`${e.site} claims row ${e.row} but asks and reads now agree (rule 4) — the row was fixed and the manifest still says it is open`);
    if (!['SESSION', 'TURN'].includes(e.asks) || !['SESSION', 'TURN'].includes(e.reads)) failures.push(`${e.site}: asks/reads must each be SESSION or TURN`);
  }
  return failures;
}

// ── CONTROLS. bars.md 11: a clean sweep is a result only once something in the same run went red
// on purpose — and the control needs its own proof that it fires. Each fixture drives the REAL
// functions, and each asserts a DISTINCT failure mode, so a control passing by accident is visible.
function controls() {
  const errs = [];
  const eq = (got, want, what) => { if (got !== want) errs.push(`control ${what}: got ${JSON.stringify(got)}, want ${JSON.stringify(want)}`); };

  // C1 the stripper blanks a call inside a line comment and inside a block comment, and KEEPS the
  // real one. This is the dispatch.js:95 hazard: a grep counts a comment as a crossing.
  const c1 = crossingsIn('f.js', [
    'function real() {',
    '  // heartStore.listExecutionsByStatus("running") <- a comment',
    '  /* heartStore.listTurnsOfLiveSessions() <- a block comment */',
    '  return heartStore.listExecutionsByStatus("running");',
    '}',
  ].join('\n'));
  eq(c1.length, 1, 'C1 count');
  eq(c1[0] && c1[0].symbol, 'real', 'C1 symbol');

  // C2 a call named inside a STRING is not a crossing.
  eq(crossingsIn('f.js', 'function s() { log("heartStore.listExecutionsByStatus(x)"); }').length, 0, 'C2 string');

  // C3 THE STRIPPER ITSELF CAN BE THE DEFECT: a regex literal containing a quote, mis-scanned,
  // swallows every following string boundary and the file silently reads as one long literal.
  const c3 = crossingsIn('f.js', [
    'function r() {',
    '  const re = /["\']/g;',
    '  return heartStore.listTurnsOfLiveSessions();',
    '}',
  ].join('\n'));
  eq(c3.length, 1, 'C3 count after a quote-bearing regex');
  eq(c3[0] && c3[0].symbol, 'r', 'C3 symbol');

  // C4 attribution: module-level code is NOT attributed to the function above it.
  const c4 = crossingsIn('f.js', [
    'function earlier() { return 1; }',
    'const rows = heartStore.listExecutionsByStatus("running");',
  ].join('\n'));
  eq(c4.length, 1, 'C4 count');
  eq(c4[0] && c4[0].symbol, '(module)', 'C4 module scope');

  // C5 attribution: the INNERMOST named frame wins, not the outermost.
  const c5 = crossingsIn('f.js', [
    'function outer() {',
    '  const inner = () => {',
    '    return heartStore.listExecutionsByStatus("running");',
    '  };',
    '  return inner;',
    '}',
  ].join('\n'));
  eq(c5[0] && c5[0].symbol, 'inner', 'C5 innermost frame');

  // ── the four rules each go RED on their own fixture ──
  const sitesOf = (arr) => new Map(arr.map((s) => [s, { site: s, readers: new Set(['x']), lines: [1] }]));
  const real = new Set(MANIFEST.map((e) => e.site));

  const r1 = applyRules(sitesOf([...real, 'server/new-file.js:brandNewCaller']));
  if (!r1.some((f) => f.includes('rule 1'))) errs.push('control R1: a NEW unclassified crossing did not go red');

  const r2 = applyRules(sitesOf([...real].slice(1)));
  if (!r2.some((f) => f.includes('rule 2'))) errs.push('control R2: a manifest entry whose site vanished did not go red');

  // R3/R4 mutate a COPY of the manifest through the same rule function.
  const saved = MANIFEST.map((e) => ({ ...e }));
  try {
    const mismatch = MANIFEST.find((e) => e.asks !== e.reads);
    delete mismatch.row;
    if (!applyRules(sitesOf([...real])).some((f) => f.includes('rule 3'))) errs.push('control R3: a mismatch with no row did not go red');
    Object.assign(mismatch, saved.find((e) => e.site === mismatch.site));

    const agree = MANIFEST.find((e) => e.asks === e.reads);
    agree.row = 'G-999';
    if (!applyRules(sitesOf([...real])).some((f) => f.includes('rule 4'))) errs.push('control R4: a stale row on an agreeing site did not go red');
    Object.assign(agree, saved.find((e) => e.site === agree.site));
  } finally {
    MANIFEST.length = 0;
    for (const e of saved) MANIFEST.push(e);
  }

  // R5 the real manifest, against the real manifest's own key set, is clean — so R1..R4 above
  // failed for their mutation and not because the baseline was already red.
  const r5 = applyRules(sitesOf([...real]));
  if (r5.length) errs.push('control R5: the baseline manifest is not self-consistent: ' + r5.join(' | '));

  return errs;
}

// ── run ───────────────────────────────────────────────────────────────────────────────────────
const lines = [];
const say = (...s) => lines.push(s.join(' '));

let exit = 0;
try {
  say('COMMAND: node ' + path.relative(process.cwd(), __filename));
  say('IGNITE_ROOT: ' + igniteRoot);

  const controlErrs = controls();
  say(`CONTROLS: ${controlErrs.length === 0 ? 'all fired' : controlErrs.length + ' broken'}`);
  for (const e of controlErrs) say('  FAILED control — ' + e);
  if (controlErrs.length) throw new Error('controls did not fire; no verdict may be read from this run');

  const { fileCount, sites } = enumerate();
  say(`SCANNED_FILES: ${fileCount}`);
  say(`CROSSINGS_FOUND: ${sites.size}`);
  if (sites.size === 0) throw new Error('zero crossings enumerated — a refusal, never a vacuous green');

  for (const site of [...sites.keys()].sort()) {
    const e = MANIFEST.find((x) => x.site === site);
    const s = sites.get(site);
    say(`  SITE ${site}  lines=[${s.lines.join(',')}]  ${e ? `asks=${e.asks} reads=${e.reads}${e.row ? ' row=' + e.row : ''}` : 'UNCLASSIFIED'}`);
  }

  const failures = applyRules(sites);
  for (const f of failures) say('FAILED ' + f);
  say(`RESULT: ${failures.length === 0 ? 'every crossing is classified' : failures.length + ' rule violation(s)'}`);
  exit = failures.length === 0 ? 0 : 1;
} catch (err) {
  say('ERROR: ' + err.message);
  exit = 1;
}

say('EXIT: ' + exit);
say('WALL_MS: ' + (Date.now() - start));
fs.writeFileSync(outPath, lines.join('\n') + '\n');
process.stdout.write(lines.join('\n') + '\n');
process.exitCode = exit;
