'use strict';

// Task C5 — PER-ROW ARGV TEMPLATING and its hostile-input suite (owner ruling
// `d-owner-q10-launcher-0808` (2); the ruling attaches a MANDATORY hostile-input criterion because
// row text becomes an exec'd command line).
//
// THE GREEN THAT MATTERS IS G2, and it is green only through a REAL FIRE. A registered workflow
// argv carrying `{{workflow}}` / `{{entry-seat}}` / `{{workdir}}` is fired by a real `ticker.tick()`
// through the real carrier, and the composed argv is read back from the CHILD's own `process.argv`
// (`_argv-echo.js`) rather than from the tick log — the tick log is the ticker's account of what it
// composed, and the criterion is what the exec RECEIVED.
//
// ⚠ G2 CANNOT PASS ON AN UNEXPANDED FIRE, and check G3 states that rather than leaving it implied:
// the expected argv is asserted to DIFFER from the registered template, so a ticker that handed the
// template straight to exec would fail G2 on the placeholder tokens themselves. That is the
// discrimination a mutant would otherwise have to supply for this arm.
//
// ⚠ THE HOSTILE ARMS ARE REFUSALS EXCEPT ONE, and the exception is the interesting one. Placeholder
// smuggling (H2) is not refused — it is INERT: a row value that itself reads `{{workdir}}` is
// emitted verbatim, because the expansion is one pass over the template and never re-enters its own
// output. Asserting a refusal there would have been asserting the wrong property.
//
// ⚠ THIS PROBE ALSO CARRIES TASK 7.559's FIRE-TOOL ARMS (§ "TASK 7.559" below) — deliberately in
// ONE file rather than a second probe, because both rows govern the SAME expander and a split would
// let one side's mutant answer the other side's question. C5 admits a `workflows:` value by GRAMMAR;
// 7.559 admits a `tools:` value by IDENTITY against a config-authored list. The F arms fire through
// a real `ticker.tick()` on the fire-tool path and include their own guard-removal mutant (F10).
//
// ⚠ TWO RED ARMS, because the two gates are two separate claims. R1 cuts the value rule out of a
// SCRATCH copy of `argv-template.js` and shows a `;`-bearing value expand — proving the value gate
// is what refuses. R2 cuts the `checkTemplateArgs` call out of a SCRATCH copy of `heart-store.js`
// and shows the same row ENQUEUE — proving the store actually calls the gate rather than merely
// having a green sibling. Neither mutation touches the live tree, and each is asserted to have
// actually altered the source before its result is trusted.

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const { setup, teardown, capture } = require('./lib');
const { expandArgv, checkTemplateArgs, MAX_NAME, MAX_PATH } = require('../../heart/argv-template');

const TEMPLATE_SRC = path.join(__dirname, '..', '..', 'heart', 'argv-template.js');
// The REAL catalogue, not a fixture — task 7.577 criterion (9) asks whether the entries that fire
// on this box still compose, and a hand-built map would answer a different question.
const SHIPPED_CONFIG = path.join(__dirname, '..', '..', '..', 'config', 'spawn-profiles.yaml');
const HEART_STORE_SRC = path.join(__dirname, '..', '..', 'heart', 'heart-store.js');
// Scratch copies MUST live beside their originals: both resolve siblings (`./errors`,
// `./argv-template`, `schema.sql`) off their own __dirname. Removed in `finally`.
const templateScratch = path.join(__dirname, '..', '..', 'heart', `argv-template.__c5scratch-${process.pid}.js`);
const storeScratch = path.join(__dirname, '..', '..', 'heart', `heart-store.__c5scratch-${process.pid}.js`);
// 7.559's own mutant: a SECOND scratch copy, because R1 above already holds the first one and a
// shared path would have one arm's mutation silently answering the other's question.
const allowScratch = path.join(__dirname, '..', '..', 'heart', `argv-template.__c7559scratch-${process.pid}.js`);

const GOAL = 'test-c5-fixture';
const WORKFLOW = 'planning';
const ENTRY_SEAT = 'elicitator';

let passed = 0;
let failed = 0;
function check(lines, ok, label, detail = '') {
  lines.push(`${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? ` — ${detail}` : ''}`);
  if (ok) passed += 1; else failed += 1;
}

function attempt(fn) {
  try { return { ok: true, value: fn() }; } catch (err) { return { ok: false, code: err.code, message: err.message }; }
}

async function waitFor(predicate, budgetMs = 20000) {
  const deadline = Date.now() + budgetMs;
  while (Date.now() < deadline) {
    if (predicate()) return true;
    await new Promise((r) => setTimeout(r, 200));
  }
  return false;
}

async function run(lines) {
  const ctx = setup();
  try {
    // A real fixture goal folder, inside the probe's throwaway workspace — the containment rule
    // the store enforces is satisfied by a real path, not by a string shaped like one.
    const goalDir = path.join(ctx.workRoot, '.rbtv', 'goals', GOAL);
    fs.mkdirSync(goalDir, { recursive: true });

    // The registered launcher: ONE generic entry whose per-goal values are placeholders. This is
    // the shape the shipped `workflows:` entry will take once its argv is ruled.
    const TEMPLATE = [
      process.execPath,
      path.join(__dirname, '_argv-echo.js'),
      '--workflow', '{{workflow}}',
      '--entry-seat', '{{entry-seat}}',
      '--package', '{{workdir}}',
    ];
    ctx.store.config.workflows = { [WORKFLOW]: { argv: TEMPLATE } };

    ctx.store.registerJob({
      jobId: 'c5-workflow-start',
      actionType: 'start-workflow',
      function: 'start-workflow',
      argsSchema: JSON.stringify({
        required: { workflow: 'string', 'entry-seat': 'string' },
        optional: { workdir: 'string' },
      }),
    });

    const goodArgs = { workflow: WORKFLOW, 'entry-seat': ENTRY_SEAT, workdir: goalDir };

    // ── G1 · the enqueue gate ACCEPTS the legal row (the control every refusal below needs) ─────
    const enq = attempt(() => ctx.store.enqueue({
      jobId: 'c5-workflow-start',
      args: JSON.stringify(goodArgs),
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() - 60000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    }));
    check(lines, enq.ok, 'G1 a legal templated row ENQUEUES — without this every refusal below is satisfied by "refuse everything"',
      enq.ok ? `queue_id=${enq.value.queue_id}` : `${enq.code} ${enq.message}`);

    // ── G3 · the expectation is written FIRST and differs from the template ─────────────────────
    const EXPECTED = [
      path.join(__dirname, '_argv-echo.js'),
      '--workflow', WORKFLOW,
      '--entry-seat', ENTRY_SEAT,
      '--package', goalDir,
    ];
    check(lines, JSON.stringify(EXPECTED) !== JSON.stringify(TEMPLATE.slice(1)),
      'G3 the expected argv DIFFERS from the registered template — so G2 cannot pass on a fire that skipped expansion',
      `${TEMPLATE.filter((t) => t.includes('{{')).length} placeholder tokens must have been replaced`);

    // ── G2 · a REAL fire composes the argv, read back from the child's own process.argv ─────────
    await ctx.ticker.tick(new Date());
    const echoPath = path.join(goalDir, 'argv-echo.json');
    const arrived = await waitFor(() => fs.existsSync(echoPath));
    if (!arrived) {
      // An honest refusal is a result, not a skip — the C3 setsid precedent. It is reported as a
      // FAIL here because this box's carrier is the one the daemon uses.
      check(lines, false, 'G2 the fired child wrote its own argv', `no ${echoPath} within budget — the exec did not run`);
    } else {
      const seen = JSON.parse(fs.readFileSync(echoPath, 'utf8'));
      check(lines, JSON.stringify(seen) === JSON.stringify(EXPECTED),
        'G2 the EXEC RECEIVED the composed argv, byte-compared against the written expectation',
        `seen=${JSON.stringify(seen)}`);
    }

    // ── H · the hostile-arm suite. Each attempt MUST be refused at the ENQUEUE gate ─────────────
    const HOSTILE = [
      ['H1a shell metacharacter `;` in a seat value', { ...goodArgs, 'entry-seat': 'elicitator; rm -rf /' }],
      ['H1b command substitution `$(` in a workflow value', { ...goodArgs, workflow: 'planning$(id)' }],
      ['H1c backtick in a workflow value', { ...goodArgs, workflow: 'planning`id`' }],
      ['H1d pipe in a seat value', { ...goodArgs, 'entry-seat': 'elicitator|nc' }],
      ['H3a path traversal in a seat value', { ...goodArgs, 'entry-seat': '../../etc/passwd' }],
      ['H3b path traversal in a workdir value', { ...goodArgs, workdir: `${goalDir}/../../../etc` }],
      ['H3c workdir OUTSIDE the .rbtv/goals containment', { ...goodArgs, workdir: '/etc' }],
      ['H3d relative workdir', { ...goodArgs, workdir: 'goals/x' }],
      ['H5 an oversized value', { ...goodArgs, 'entry-seat': 'a'.repeat(MAX_NAME + 1) }],
      ['H6 a control character in a value', { ...goodArgs, workflow: 'plan\nning' }],
      ['H7 a non-string value where a name is required', { ...goodArgs, 'entry-seat': 7 }],
    ];
    for (const [label, args] of HOSTILE) {
      const r = attempt(() => ctx.store.enqueue({
        jobId: 'c5-workflow-start',
        args: JSON.stringify(args),
        triggerKind: 'scheduled',
        runAt: new Date(Date.now() + 600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
        enqueuedBy: 'probe',
      }));
      check(lines, !r.ok && r.code === 'E_BAD_ARGS', `${label} is REFUSED at enqueue, typed`,
        r.ok ? `ACCEPTED queue_id=${r.value.queue_id} — the gate did not fire` : `${r.code}: ${r.message}`);
    }

    // ── H4 · an unknown WORKFLOW name is refused by the store's own catalogue check ─────────────
    const unknownWf = attempt(() => ctx.store.enqueue({
      jobId: 'c5-workflow-start',
      args: JSON.stringify({ ...goodArgs, workflow: 'no-such-workflow' }),
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() + 600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    }));
    check(lines, !unknownWf.ok && unknownWf.code === 'E_UNKNOWN_WORKFLOW',
      'H4 an unknown workflow name is REFUSED at enqueue', `${unknownWf.code || 'ACCEPTED'}`);

    // ── H2 · placeholder smuggling is INERT, not refused — the expansion never re-reads output ──
    const smuggled = `${goalDir}/{{workdir}}`;
    const smuggle = expandArgv(['--package', '{{workdir}}'], { ...goodArgs, workdir: smuggled });
    check(lines, !smuggle.refused && smuggle.argv[1] === smuggled && smuggle.argv.length === 2,
      'H2 a `{{workdir}}` smuggled INSIDE a row value is emitted verbatim — one pass, output never re-scanned',
      JSON.stringify(smuggle));

    // ── H8 · an unknown placeholder in the CONFIG argv is a typed refusal, never an empty token ─
    const unknownPh = expandArgv(['--x', '{{secret}}'], goodArgs);
    check(lines, !!unknownPh.refused && unknownPh.refused.includes('unknown placeholder'),
      'H8 an unknown placeholder is REFUSED at fire — never silently dropped into a missing operand',
      unknownPh.refused || JSON.stringify(unknownPh));

    // ── H9 · a partial placeholder token is refused rather than passed through as a literal ─────
    const partial = expandArgv(['--package={{workdir}}'], goodArgs);
    check(lines, !!partial.refused && partial.refused.includes('malformed placeholder'),
      'H9 `--flag={{key}}` is REFUSED — whole-token only, so a value can never be welded onto a flag',
      partial.refused || JSON.stringify(partial));

    // ── H10 · a placeholder with no value in the row is refused ─────────────────────────────────
    // argv[0] is a LITERAL here on purpose: a placeholder at argv[0] is refused by its own rule
    // (V5, added by the C5 review), which would satisfy this arm for the wrong reason.
    const noValue = expandArgv(['/bin/true', '{{goal}}'], goodArgs);
    check(lines, !!noValue.refused && noValue.refused.includes('no value'),
      'H10 a placeholder the row carries no value for is REFUSED', noValue.refused || JSON.stringify(noValue));

    // ── R1 · RED ARM · the VALUE RULE cut out of a scratch copy — the hostile value must expand ──
    const tplOriginal = fs.readFileSync(TEMPLATE_SRC, 'utf8');
    // ⚠ THE ANCHOR CARRIES THE SIGNATURE, so it goes stale the moment the signature changes — as it
    // did when 7.559 added the `allow` parameter, and this arm went red and said exactly why. That
    // is the anchor working, not the anchor being brittle: a mutation arm whose anchor silently
    // missed would report a guard as proven while mutating nothing.
    const R1_ANCHOR = 'function checkTemplateArgs(args, allow = null) {';
    const tplMutated = tplOriginal.includes(R1_ANCHOR)
      ? tplOriginal.replace(R1_ANCHOR, `${R1_ANCHOR}\n  if (args) return null; // MUTANT: value rule removed`)
      : null;
    check(lines, tplMutated !== null && tplMutated !== tplOriginal && tplMutated.includes('MUTANT'),
      'R1 the mutation was actually applied to the scratch copy — an unmutated mutant passes for the wrong reason',
      tplMutated === null ? 'ANCHOR NOT FOUND' : `+${tplMutated.length - tplOriginal.length} bytes`);
    if (tplMutated) {
      fs.writeFileSync(templateScratch, tplMutated);
      const unguarded = require(templateScratch);
      const attack = unguarded.expandArgv(['--entry-seat', '{{entry-seat}}'], { ...goodArgs, 'entry-seat': 'elicitator; rm -rf /' });
      check(lines, !attack.refused && attack.argv[1] === 'elicitator; rm -rf /',
        'R1 UNGUARDED the `;`-bearing value expands into the argv — the value rule is what H1a measures',
        JSON.stringify(attack));
    } else {
      check(lines, false, 'R1 UNGUARDED the `;`-bearing value expands', 'SKIPPED — mutation could not be built');
    }

    // ── R2 · RED ARM · the STORE's call to the gate cut out — the hostile row must ENQUEUE ───────
    const storeOriginal = fs.readFileSync(HEART_STORE_SRC, 'utf8');
    const R2_START = '    const templateRefusal = checkTemplateArgs(parsed);';
    const R2_END = '  } else if (actionType === \'send-message\') {';
    const s0 = storeOriginal.indexOf(R2_START);
    const s1 = storeOriginal.indexOf(R2_END, s0);
    const storeMutated = (s0 !== -1 && s1 !== -1)
      ? storeOriginal.slice(0, s0) + storeOriginal.slice(s1)
      : null;
    check(lines, storeMutated !== null && !storeMutated.includes(R2_START) && storeMutated.length < storeOriginal.length,
      'R2 the store mutation was actually applied — the gate call is gone from the scratch copy',
      storeMutated === null ? 'ANCHORS NOT FOUND' : `cut ${storeOriginal.length - storeMutated.length} bytes`);
    if (storeMutated) {
      fs.writeFileSync(storeScratch, storeMutated);
      const scratch = require(storeScratch);
      // The scratch copy is a SEPARATE module instance, so its `singleton` is its own — the live
      // store stays open and the second-writer guard is not tripped. Its db is a separate file.
      const unguardedDb = path.join(ctx.tmp, 'unguarded.db');
      const us = scratch.openHeartStore({ dbPath: unguardedDb, workflows: { [WORKFLOW]: { argv: TEMPLATE } } });
      us.registerJob({
        jobId: 'c5-workflow-start', actionType: 'start-workflow', function: 'start-workflow',
        argsSchema: JSON.stringify({ required: { workflow: 'string', 'entry-seat': 'string' }, optional: { workdir: 'string' } }),
      });
      const r = attempt(() => us.enqueue({
        jobId: 'c5-workflow-start',
        args: JSON.stringify({ ...goodArgs, 'entry-seat': 'elicitator; rm -rf /' }),
        triggerKind: 'scheduled',
        runAt: new Date(Date.now() + 600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
        enqueuedBy: 'probe',
      }));
      check(lines, r.ok, 'R2 UNGUARDED the store ENQUEUES the `;`-bearing row — the store really does call the gate',
        r.ok ? `queue_id=${r.value.queue_id}` : `still refused: ${r.code} ${r.message}`);
      scratch.closeHeartStore();
    } else {
      check(lines, false, 'R2 UNGUARDED the store enqueues the hostile row', 'SKIPPED — mutation could not be built');
    }

    // ══ §2 REVIEW ARMS (C5 review 2026-08-08) — attack shapes the build's own suite did not carry.
    // The ruling attaches a MANDATORY hostile-input criterion, and a suite written by the author of
    // the defence tests the shapes the author thought of. These are the ones it did not.

    // ── V1 · ENCODING. A homoglyph is not a filter problem here: the name grammar is ASCII, so a
    // Cyrillic `а` is refused by the same rule that refuses `;`. `%2e%2e` is ACCEPTED and that is
    // correct — the kernel does not decode percent escapes, so it names a literal directory that is
    // still inside containment. Asserting a refusal there would assert a wrong property.
    // Composed from a COMPUTED pad, never a hand-counted literal: the first draft of this arm
    // was 512 chars and passed the length rule, so it measured nothing.
    const OVERLONG_PREFIX = '/tmp/x/.rbtv/goals/';
    const OVERLONG_WORKDIR = OVERLONG_PREFIX + 'a'.repeat(MAX_PATH + 1 - OVERLONG_PREFIX.length);
    const REVIEW_REFUSED = [
      ['V1a a Cyrillic homoglyph in a seat value', { ...goodArgs, 'entry-seat': 'elicаtator' }],
      ['V1b a fullwidth latin letter in a workflow value', { ...goodArgs, workflow: 'ｐlanning' }],
      ['V1c a literal backslash escape in a seat value', { ...goodArgs, 'entry-seat': 'a\\x2e\\x2eb' }],
      ['V1d a backslash path separator in a seat value', { ...goodArgs, 'entry-seat': 'a\\b' }],
      ['V2a an EMPTY seat value', { ...goodArgs, 'entry-seat': '' }],
      ['V2b a WHITESPACE-ONLY seat value', { ...goodArgs, 'entry-seat': ' ' }],
      ['V2c an EMPTY workdir', { ...goodArgs, workdir: '' }],
      ['V2d a workdir naming the goals root with NO goal segment', { ...goodArgs, workdir: '/tmp/x/.rbtv/goals' }],
      ['V3 an over-long single token (workdir, MAX_PATH+1)', { ...goodArgs, workdir: OVERLONG_WORKDIR }],
    ];
    for (const [label, args] of REVIEW_REFUSED) {
      const r = attempt(() => ctx.store.enqueue({
        jobId: 'c5-workflow-start',
        args: JSON.stringify(args),
        triggerKind: 'scheduled',
        runAt: new Date(Date.now() + 600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
        enqueuedBy: 'probe',
      }));
      check(lines, !r.ok && r.code === 'E_BAD_ARGS', `${label} is REFUSED at enqueue, typed`,
        r.ok ? `ACCEPTED queue_id=${r.value.queue_id} — the gate did not fire` : `${r.code}: ${r.message}`);
    }
    const pctEscape = checkTemplateArgs({ ...goodArgs, workdir: `${goalDir}/%2e%2e/etc` });
    check(lines, pctEscape === null,
      'V1e a `%2e%2e` workdir is ACCEPTED — and that is the correct property: the kernel decodes no percent escape, so it names a literal directory still inside containment',
      String(pctEscape));

    // ── V4 · NESTED / RECURSIVE PLACEHOLDERS in the TEMPLATE. Whole-token-only makes each of these
    // a malformed token rather than a partial expansion.
    for (const [label, tok] of [
      ['V4a a doubled-brace token `{{{{workflow}}}}`', '{{{{workflow}}}}'],
      ['V4b a nested inner key `{{work{{flow}}}}`', '{{work{{flow}}}}'],
      ['V4c a placeholder with a trailing space', '{{workflow}} '],
      ['V4d an uppercase placeholder key', '{{Workflow}}'],
    ]) {
      const r = expandArgv(['/bin/true', tok], goodArgs);
      check(lines, !!r.refused && r.refused.includes('malformed placeholder'),
        `${label} is REFUSED as malformed, never partially expanded`, r.refused || JSON.stringify(r));
    }

    // ── V5 · THE ROW MAY FILL AN OPERAND, NEVER CHOOSE THE PROGRAM. argv[0] is the executable and
    // `spawn` resolves a bare name through PATH, so a placeholder there hands the row that choice —
    // and `entry-seat`/`goal` are bounded only by kebab-case, which `python3` and `curl` satisfy.
    // The other four shape properties all still hold while this is true, which is why it needed its
    // own guard rather than an argument. Found and fixed by this review.
    for (const [label, tpl] of [
      ['V5a a placeholder at argv[0] ({{workdir}})', ['{{workdir}}', '--x']],
      ['V5b a placeholder at argv[0] ({{entry-seat}} — a PATH-resolved bare name)', ['{{entry-seat}}', '--x']],
    ]) {
      const r = expandArgv(tpl, goodArgs);
      check(lines, !!r.refused && r.refused.includes('never choose the program'),
        `${label} is REFUSED`, r.refused || JSON.stringify(r));
    }
    const legalHead = expandArgv(['/bin/true', '--workflow', '{{workflow}}'], goodArgs);
    check(lines, !legalHead.refused && legalHead.argv[0] === '/bin/true' && legalHead.argv[2] === WORKFLOW,
      'V5c CONTROL a LITERAL argv[0] with a placeholder operand still expands — V5a/V5b are not "refuse everything"',
      JSON.stringify(legalHead));

    // ── V6 · PROTOTYPE-CHAIN CATALOGUE LOOKUP. `constructor` is legal kebab-case, so a truthiness
    // test on `config.workflows[name]` resolved it to Object and let the row past the very guard
    // that refuses `no-such-workflow`. Found by this review; fixed with `Object.hasOwn`.
    const proto = attempt(() => ctx.store.enqueue({
      jobId: 'c5-workflow-start',
      args: JSON.stringify({ ...goodArgs, workflow: 'constructor' }),
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() + 600000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    }));
    check(lines, !proto.ok && proto.code === 'E_UNKNOWN_WORKFLOW',
      'V6 a workflow named `constructor` is REFUSED like any other unregistered name — the existence check does not walk the prototype chain',
      proto.ok ? `ACCEPTED queue_id=${proto.value.queue_id} — the lookup is truthiness, not hasOwn` : `${proto.code}`);
    check(lines, checkTemplateArgs(['not', 'an', 'object']) === 'args must be a JSON object',
      'V6b an ARRAY is refused by the gate that says "must be a JSON object" — an array is `typeof object` and passed before this review',
      String(checkTemplateArgs(['not', 'an', 'object'])));

    // ── V7 · THE FIRE-TIME RE-VALIDATION, MEASURED RATHER THAN READ. The brief requires defence in
    // depth against a row that is legal at enqueue and hostile at fire. Nothing in the enqueue path
    // can produce such a row, so the only honest exercise is to WRITE one into the store behind the
    // gate's back and then fire it through a real tick. A pass here means the fire path treats a
    // stored row as data, not as something a past validation vouched for.
    const mutDir = path.join(ctx.workRoot, '.rbtv', 'goals', 'test-c5-mutated');
    fs.mkdirSync(mutDir, { recursive: true });
    const mutEnq = attempt(() => ctx.store.enqueue({
      jobId: 'c5-workflow-start',
      args: JSON.stringify({ ...goodArgs, workdir: mutDir }),
      triggerKind: 'scheduled',
      runAt: new Date(Date.now() - 60000).toISOString().replace(/\.\d{3}Z$/, 'Z'),
      enqueuedBy: 'probe',
    }));
    check(lines, mutEnq.ok, 'V7a the row is LEGAL at enqueue — the control the mutation below needs',
      mutEnq.ok ? `queue_id=${mutEnq.value.queue_id}` : `${mutEnq.code}: ${mutEnq.message}`);
    if (mutEnq.ok) {
      const hostileArgs = JSON.stringify({ workflow: WORKFLOW, 'entry-seat': 'elicitator; rm -rf /', workdir: mutDir });
      ctx.store._prepare('UPDATE queue SET args = ? WHERE queue_id = ?').run(hostileArgs, mutEnq.value.queue_id);
      const readBack = ctx.store._prepare('SELECT args FROM queue WHERE queue_id = ?').get(mutEnq.value.queue_id).args;
      check(lines, readBack === hostileArgs,
        'V7b the stored row really was mutated behind the gate — an unmutated row would pass V7c for the wrong reason',
        `stored=${readBack}`);
      const mutTick = await ctx.ticker.tick(new Date());
      const acts = JSON.stringify((mutTick && mutTick.actions) || mutTick || []);
      check(lines, acts.includes('start-workflow-failed') && acts.includes('argv-template:'),
        'V7c FIRE-TIME RE-VALIDATION refuses the row the enqueue gate never saw, typed and RECORDED', acts.slice(0, 300));
      const ranAnyway = await waitFor(() => fs.existsSync(path.join(mutDir, 'argv-echo.json')), 3000);
      check(lines, !ranAnyway,
        'V7d and NO child was exec\'d for the refused row — the refusal is the outcome, not just a log line',
        ranAnyway ? 'argv-echo.json EXISTS — the exec ran despite the refusal' : 'no argv-echo.json');
    }

    // ══ TASK 7.559 · THE FIRE-TOOL PATH — ADMISSION BY IDENTITY ═════════════════════════════════
    // (owner ruling `d-owner-7559-design-rulings-0808`; design `dossiers/7559-argv-allowlist-design.md`.)
    //
    // C5 above admits a value by GRAMMAR, which is right for a workflow name. On the `tools:` path
    // it is not an admission mechanism at all: a fired tool runs with NO sandbox and its operands
    // are absolute paths, which no name grammar bounds. So a value is admitted by MEMBERSHIP of a
    // list the config author wrote, or not at all.
    //
    // ⚠ EVERY ARM BELOW GOES THROUGH A REAL `ticker.tick()` FIRE — the row criterion says "against
    // the real fire path and not a unit stub", and 7.559 adds NO enqueue gate (the enqueue-door
    // half is deliberately deferred), so the fire path is the ONLY place the guard exists. The
    // hostile args are written into the store BEHIND the enqueue gate, which is also the honest way
    // to exercise a fire path that must treat any stored row as data.
    //
    // ⚠ NO ARM SKIPS ON "THE TARGET WAS NOT FOUND". A missing refusal, a missing action, an absent
    // echo file — each is a FAIL. The only thing reported as a fixture problem is a control row
    // that could not be ENQUEUED AT ALL, and that is reported as a FAIL too, never as a skip: an
    // absent target IS the failure, and a skip predicate that swallows it makes the arm vacuous.
    const TOOL = 'c7559-edge';
    const goalA = path.join(ctx.workRoot, '.rbtv', 'goals', 'test-7559-approved');
    const goalB = path.join(ctx.workRoot, '.rbtv', 'goals', 'test-7559-unapproved');
    const fireDir = path.join(ctx.workRoot, 'fire-7559');
    const frozenDir = path.join(ctx.workRoot, 'frozen-7559');
    const refusedDir = path.join(ctx.workRoot, 'refused-7559');
    for (const d of [goalA, goalB, fireDir, frozenDir, refusedDir]) fs.mkdirSync(d, { recursive: true });

    const ECHO = path.join(__dirname, '_argv-echo.js');
    const FIRE_TEMPLATE = [process.execPath, ECHO, '--goal', '{{goal}}'];
    const FROZEN_ARGV = [process.execPath, ECHO, '--frozen', 'literal-operand'];
    ctx.store.config.tools = {
      [TOOL]: { argv: FIRE_TEMPLATE, args_allowlist: { goal: [goalA] } },
      'c7559-frozen': { argv: FROZEN_ARGV },
      'c7559-templated-no-list': { argv: FIRE_TEMPLATE },
      'c7559-empty-list': { argv: FIRE_TEMPLATE, args_allowlist: { goal: [] } },
      // Templates `{{goal}}` but lists a DIFFERENT key. `entry-seat` and not `workdir`: every row
      // carries a workdir, so a workdir-keyed list would refuse on MEMBERSHIP first and F7 would
      // pass on the wrong reason — the arm must reach the by-name branch to mean anything.
      'c7559-other-key': { argv: FIRE_TEMPLATE, args_allowlist: { 'entry-seat': ['elicitator'] } },
    };
    ctx.store.registerJob({
      jobId: 'c7559-fire',
      actionType: 'fire-tool',
      function: 'fire-tool',
      argsSchema: JSON.stringify({ required: { tool: 'string' }, optional: { goal: 'string', workdir: 'string' } }),
    });

    const dueNow = () => new Date(Date.now() - 60000).toISOString().replace(/\.\d{3}Z$/, 'Z');
    async function fireRow(rowArgs) {
      const enq = attempt(() => ctx.store.enqueue({
        jobId: 'c7559-fire',
        args: JSON.stringify({ tool: TOOL, goal: goalA, workdir: refusedDir }),
        triggerKind: 'scheduled',
        runAt: dueNow(),
        enqueuedBy: 'probe',
      }));
      if (!enq.ok) return { built: false, detail: `control row could not be ENQUEUED: ${enq.code} ${enq.message}` };
      const wanted = JSON.stringify(rowArgs);
      ctx.store._prepare('UPDATE queue SET args = ? WHERE queue_id = ?').run(wanted, enq.value.queue_id);
      const stored = ctx.store._prepare('SELECT args FROM queue WHERE queue_id = ?').get(enq.value.queue_id).args;
      if (stored !== wanted) return { built: false, detail: 'the args write behind the gate did not take' };
      const t = await ctx.ticker.tick(new Date());
      return { built: true, acts: JSON.stringify((t && t.actions) || t || []) };
    }

    // ── F0/F1 · the GREEN control: a LISTED member composes, read back from the child's argv ─────
    const EXPECT_FIRED = [ECHO, '--goal', goalA];
    check(lines, JSON.stringify(EXPECT_FIRED) !== JSON.stringify(FIRE_TEMPLATE.slice(1)),
      'F0 the expected fire-tool argv DIFFERS from the registered template — so F1 cannot pass on a fire that skipped expansion',
      `${FIRE_TEMPLATE.filter((t) => t.includes('{{')).length} placeholder token(s) must have been replaced`);
    const greenFire = await fireRow({ tool: TOOL, goal: goalA, workdir: fireDir });
    check(lines, greenFire.built, 'F1a the green fire-tool fixture was built', greenFire.detail || 'enqueued + fired');
    const fireEcho = path.join(fireDir, 'argv-echo.json');
    const fireArrived = greenFire.built && await waitFor(() => fs.existsSync(fireEcho));
    if (!fireArrived) {
      check(lines, false, 'F1b the fired child wrote its own argv', `no ${fireEcho} within budget — the exec did not run`);
    } else {
      const seen = JSON.parse(fs.readFileSync(fireEcho, 'utf8'));
      check(lines, JSON.stringify(seen) === JSON.stringify(EXPECT_FIRED),
        'F1b a LISTED member REACHES THE EXEC, byte-compared against the written expectation — refusal-by-default is not "refuse everything"',
        `seen=${JSON.stringify(seen)}`);
    }

    // ── F2/F3 · REFUSAL BY DEFAULT and the hostile-argv suite, each at the REAL fire ─────────────
    // The expected reason is asserted per arm, not just "some refusal": a membership refusal and a
    // control-character refusal are different claims, and an arm that accepted either would not
    // notice the membership test disappearing.
    const NOT_LISTED = "not on this entry's allowlist";
    const OVERLONG_VALUE = 'a'.repeat(10000);
    const FIRE_HOSTILE = [
      ['F2  an UNLISTED but REAL goal folder is REFUSED — the criterion-(2) arm: admission is identity, not plausibility', goalB, NOT_LISTED],
      ['F3a shell metacharacters appended to a listed value', `${goalA}; rm -rf /`, NOT_LISTED],
      ['F3b command substitution', '$(cat /etc/passwd)', NOT_LISTED],
      ['F3c backtick substitution', '`id`', NOT_LISTED],
      ['F3d path traversal out of the listed folder', `${goalA}/../../../../etc`, NOT_LISTED],
      ['F3e an absolute path nobody listed', '/etc/passwd', NOT_LISTED],
      ['F3f flag injection (long flag)', '--dry-run', NOT_LISTED],
      ['F3g flag injection (short flag)', '-rf', NOT_LISTED],
      ['F3h an over-long value (10 000 bytes)', OVERLONG_VALUE, NOT_LISTED],
      ['F3i a CASE near-miss of a listed value', goalA.toUpperCase(), NOT_LISTED],
      ['F3j a TRAILING-SLASH near-miss of a listed value', `${goalA}/`, NOT_LISTED],
      ['F3k a CYRILLIC HOMOGLYPH inside a listed value', goalA.replace('o', 'о'), NOT_LISTED],
      ['F3l placeholder smuggling as a value', '{{workdir}}', NOT_LISTED],
      ['F3m the EMPTY STRING', '', NOT_LISTED],
      ['F3n an embedded NEWLINE — refused as a control character, which fires BEFORE membership', `${goalA}\nExecStart=/bin/sh`, 'must carry no control character'],
      ['F3o a NUL byte', `${goalA}\u0000/etc`, 'must carry no control character'],
    ];
    let membershipArms = 0;
    for (const [label, value, expect] of FIRE_HOSTILE) {
      if (expect === NOT_LISTED) membershipArms += 1;
      const r = await fireRow({ tool: TOOL, goal: value, workdir: refusedDir });
      if (!r.built) { check(lines, false, `${label} is REFUSED at fire`, r.detail); continue; }
      check(lines, r.acts.includes('fire-tool-failed') && r.acts.includes('argv-template:') && r.acts.includes(expect),
        `${label} is REFUSED at fire, typed and RECORDED`, r.acts.slice(0, 240));
    }
    for (const [label, value] of [['F3p an ARRAY', [goalA]], ['F3q NULL', null], ['F3r a NUMBER', 7]]) {
      const r = await fireRow({ tool: TOOL, goal: value, workdir: refusedDir });
      if (!r.built) { check(lines, false, `${label} where a listed value is required is REFUSED at fire`, r.detail); continue; }
      check(lines, r.acts.includes('fire-tool-failed') && r.acts.includes('must be a string, got'),
        `${label} where a listed value is required is REFUSED at fire — type confusion never reaches membership`, r.acts.slice(0, 240));
    }

    // ── F4 · CRITERION (4): FROZEN BY DEFAULT SURVIVES, proven by a REAL fire, not by inspection ─
    const frozenFire = await fireRow({ tool: 'c7559-frozen', workdir: frozenDir });
    check(lines, frozenFire.built, 'F4a the frozen-entry fixture was built', frozenFire.detail || 'enqueued + fired');
    const frozenEcho = path.join(frozenDir, 'argv-echo.json');
    const frozenArrived = frozenFire.built && await waitFor(() => fs.existsSync(frozenEcho));
    if (!frozenArrived) {
      check(lines, false, 'F4b an entry declaring NO args_allowlist still fires', `no ${frozenEcho} within budget — the exec did not run`);
    } else {
      const seen = JSON.parse(fs.readFileSync(frozenEcho, 'utf8'));
      check(lines, JSON.stringify(seen) === JSON.stringify(FROZEN_ARGV.slice(1)),
        'F4b an entry declaring NO args_allowlist composes a BYTE-IDENTICAL argv and fires exactly as before 7.559',
        `seen=${JSON.stringify(seen)}`);
    }

    // ── F5 · FAIL CLOSED: an entry that templates a value but declares no list never execs ───────
    const failClosed = await fireRow({ tool: 'c7559-templated-no-list', goal: goalA, workdir: refusedDir });
    check(lines, failClosed.built && failClosed.acts.includes('no args_allowlist on a templated entry'),
      'F5 an entry that TEMPLATES a value while declaring NO allowlist is REFUSED — never exec\'d with a literal `{{goal}}` operand',
      failClosed.built ? failClosed.acts.slice(0, 240) : failClosed.detail);

    // ── F6 · an EMPTY positive list admits NOTHING (failing open here would be the whole defect) ─
    const emptyList = await fireRow({ tool: 'c7559-empty-list', goal: goalA, workdir: refusedDir });
    check(lines, emptyList.built && emptyList.acts.includes('an empty positive list admits nothing'),
      'F6 an EMPTY allowlist admits nothing — a value that would be listed is still refused',
      emptyList.built ? emptyList.acts.slice(0, 240) : emptyList.detail);

    // ── F7 · a placeholder whose KEY has no list on that entry is refused BY NAME ────────────────
    const otherKey = await fireRow({ tool: 'c7559-other-key', goal: goalA, workdir: refusedDir });
    check(lines, otherKey.built && otherKey.acts.includes('has no allowlist on this entry'),
      'F7 a placeholder whose key carries no allowlist on THAT entry is refused BY NAME — not by a grammar complaint that misdescribes the reason',
      otherKey.built ? otherKey.acts.slice(0, 240) : otherKey.detail);

    // ── F8 · THE SECURITY CONDITION (owner ruling B1): the list comes from the BOOT-READ CONFIG ──
    // A row that carries its OWN `args_allowlist` permitting the hostile value must still be
    // refused. This is the arm that would catch the one change that moves the boundary: reading
    // the list from anywhere an enrolled agent token can write (a row, a job registration).
    const selfGranted = await fireRow({ tool: TOOL, goal: goalB, workdir: refusedDir, args_allowlist: { goal: [goalB] } });
    check(lines, selfGranted.built && selfGranted.acts.includes(NOT_LISTED),
      'F8 a ROW that carries its OWN args_allowlist permitting the value is STILL REFUSED — a row can never extend its own boundary',
      selfGranted.built ? selfGranted.acts.slice(0, 240) : selfGranted.detail);
    for (const rel of ['internal-api/dispatch.js', 'internal-api/authz.js']) {
      const src = fs.readFileSync(path.join(__dirname, '..', '..', rel), 'utf8');
      check(lines, !src.includes('args_allowlist'),
        `F8b \`${rel}\` never reads args_allowlist — the registration/authz surfaces are exactly the ones an enrolled AGENT token can write`,
        `${src.length} bytes scanned`);
    }

    // ── F9 · NO CHILD WAS EXEC'D FOR ANY REFUSED ARM. Every refusal above shares one workdir, so
    // a single echo file here would mean SOME refusal leaked an exec. The refusal is the outcome,
    // not just a log line.
    const leaked = await waitFor(() => fs.existsSync(path.join(refusedDir, 'argv-echo.json')), 3000);
    check(lines, !leaked,
      'F9 NOT ONE of the refused arms exec\'d a child — the shared refusal workdir is empty',
      leaked ? 'argv-echo.json EXISTS — a refusal still reached the exec' : 'no argv-echo.json');

    // ── F10 · RED ARM · the MEMBERSHIP TEST cut out of a scratch copy — the hostile values compose ─
    // The guard must be SEEN to fire. Cutting the three-line membership test and nothing else, the
    // arms above must flip from refused to composed; the ones that still refuse are C5's structural
    // and type rules, which is itself the proof that C5 does not already satisfy criterion (2).
    const tpl2Original = fs.readFileSync(TEMPLATE_SRC, 'utf8');
    const F10_START = '  if (!permitted.includes(value)) {';
    const F10_END = '  return null;\n}\n\n// The CLOSED set of keys';
    const c0 = tpl2Original.indexOf(F10_START);
    const c1 = tpl2Original.indexOf(F10_END, c0);
    const tpl2Mutated = (c0 !== -1 && c1 !== -1)
      ? `${tpl2Original.slice(0, c0)}  // MUTANT: membership test removed\n${tpl2Original.slice(c1)}`
      : null;
    check(lines, tpl2Mutated !== null && !tpl2Mutated.includes(F10_START) && tpl2Mutated.includes('MUTANT'),
      'F10 the membership mutation was actually applied to the scratch copy — an unmutated mutant passes for the wrong reason',
      tpl2Mutated === null ? 'ANCHOR NOT FOUND' : `cut ${tpl2Original.length - tpl2Mutated.length} bytes`);
    if (tpl2Mutated) {
      fs.writeFileSync(allowScratch, tpl2Mutated);
      const unguarded = require(allowScratch);
      const allow = { goal: [goalA] };
      let flipped = 0;
      const stillRefused = [];
      for (const [label, value, expect] of FIRE_HOSTILE) {
        if (expect !== NOT_LISTED) { stillRefused.push(label.slice(0, 4)); continue; }
        const r = unguarded.expandArgv(FIRE_TEMPLATE, { goal: value }, allow);
        if (!r.refused && r.argv[3] === value) flipped += 1; else stillRefused.push(label.slice(0, 4));
      }
      check(lines, flipped >= 12 && flipped === membershipArms,
        `F10 UNGUARDED ${flipped} of ${membershipArms} membership arms FLIP from refused to composed — the membership test is what refuses them, and a grammar would not`,
        `flipped=${flipped} still-refused=[${stillRefused.join(' ')}] (the survivors are control-character and type rules, which C5 already owned)`);
      const guardedAgain = expandArgv(FIRE_TEMPLATE, { goal: goalB }, allow);
      check(lines, !!guardedAgain.refused,
        'F10 CONTROL the LIVE module still refuses the same value — the mutation touched only the scratch copy',
        guardedAgain.refused || JSON.stringify(guardedAgain));
    }

    // ══ TASK 7.577 · A MALFORMED `args_allowlist` IS A REFUSAL, NEVER AN ABANDONED TICK ════════
    // Measured by the §2 review of 7.559 (`evidence/w7559-review/r04`): a SCALAR `args_allowlist`
    // — `goal`, `5`, `true`, the YAML typo where a mapping of key → list is meant — made
    // `key in allow` raise a TypeError out of `expandArgv`, against the never-throws contract that
    // function's own header states. `tick()` is `try/finally` with NO `catch`, so the throw took
    // enforce, broadcast and `recordTick` with it for the WHOLE tick, and repeated every cadence
    // until the config was fixed.
    //
    // ⚠ NO MUTATION ARM HERE, and the absence is reasoned rather than forgotten. R1/F10 need one
    // because deleting a membership test leaves a REFUSAL behind, and only a mutant can say WHICH
    // check refused. Deleting THIS guard leaves a THROW — a different observable — so S1 below goes
    // red by itself the moment the guard goes, which is the whole thing a mutation arm buys.
    const SHAPE_REASON = 'args_allowlist must be a mapping of key to a list of permitted values';
    for (const [label, badAllow] of [
      ['S1a a YAML STRING', 'goal'],
      ['S1b a YAML NUMBER', 5],
      ['S1c a YAML BOOLEAN', true],
      ['S1d a YAML LIST — an array is `typeof object` and still not a mapping of key → list', [goalA]],
    ]) {
      const e = attempt(() => expandArgv(FIRE_TEMPLATE, { goal: goalA }, badAllow));
      check(lines, e.ok && !!e.value.refused && e.value.refused.includes(SHAPE_REASON),
        `${label} \`args_allowlist\` is REFUSED as a shape error and expandArgv does NOT throw`,
        e.ok ? JSON.stringify(e.value) : `THREW ${e.message}`);
      const g = attempt(() => checkTemplateArgs({ goal: goalA }, badAllow));
      check(lines, g.ok && typeof g.value === 'string' && g.value.includes(SHAPE_REASON),
        `${label} \`args_allowlist\` is REFUSED by checkTemplateArgs too — the gate the store shares`,
        g.ok ? String(g.value) : `THREW ${g.message}`);
    }

    // ── S2 · CRITERION (3): THE TICK SURVIVES, ASSERTED AT ITS COMPLETION ────────────────────────
    // ⚠ "no exception was seen" is NOT the assertion here, and that is the whole point: a
    // `try/catch` swallowing the TypeError would pass a no-throw arm while still eating the rest of
    // the tick. So each phase AFTER `dispatch` is observed DIRECTLY — enforce by the unconditional
    // `state` action it ends with, broadcast by a note stamped with THIS tick's number, recordTick
    // by the `ticks` row. Each of the three is a positive observation of work done, not of harm
    // absent.
    ctx.store.config.tools['c7577-bad-shape'] = { argv: FIRE_TEMPLATE, args_allowlist: 'goal' };
    const shapeDir = path.join(ctx.workRoot, 'shape-7577');
    fs.mkdirSync(shapeDir, { recursive: true });
    const marker = attempt(() => ctx.store.recordMessage({
      type: 'note', sender: 'probe-7577', thread: 'probe-7577', corpus: 'broadcast marker for S2e',
    }));
    // A fixture that could not be BUILT is a FAIL, never a skip — an absent target IS the failure.
    check(lines, marker.ok && marker.value && marker.value.broadcast_at_tick === null,
      'S2a the broadcast marker note exists and is UNBROADCAST before the tick — without this S2e would pass vacuously',
      marker.ok ? `msg_id=${marker.value.msg_id} broadcast_at_tick=${marker.value.broadcast_at_tick}` : `THREW ${marker.message}`);
    const shapeEnq = attempt(() => ctx.store.enqueue({
      jobId: 'c7559-fire',
      args: JSON.stringify({ tool: 'c7577-bad-shape', goal: goalA, workdir: shapeDir }),
      triggerKind: 'scheduled',
      runAt: dueNow(),
      enqueuedBy: 'probe',
    }));
    check(lines, shapeEnq.ok, 'S2b the malformed-entry row was ENQUEUED — the fixture every arm below needs',
      shapeEnq.ok ? `queue_id=${shapeEnq.value.queue_id}` : `${shapeEnq.code}: ${shapeEnq.message}`);
    // The catch is the PROBE's, so a throwing tick reports as failed arms instead of aborting the
    // suite mid-file. It is not the shape the fix may take: the guard refuses, it does not rescue.
    let shapeTick = null;
    let shapeThrew = null;
    try { shapeTick = await ctx.ticker.tick(new Date()); } catch (err) { shapeThrew = `${err.name}: ${err.message}`; }
    check(lines, shapeThrew === null,
      'S2c the tick did NOT throw on the malformed entry — necessary, and on its own NOT sufficient (S2e-S2g are what a swallowing catch could not fake)',
      shapeThrew || 'no exception');
    const shapeActs = JSON.stringify((shapeTick && shapeTick.actions) || []);
    check(lines, shapeActs.includes('fire-tool-failed') && shapeActs.includes('argv-template:') && shapeActs.includes(SHAPE_REASON),
      'S2d CRITERION (2) the malformed shape is RECORDED on the fire path as a typed refusal, exactly like every other refusal',
      shapeActs.slice(0, 260) || 'no actions — the tick never returned');
    check(lines, shapeActs.includes('"phase":"enforce","action":"state"'),
      'S2e ENFORCE still ran for that tick — its unconditional closing action is present',
      shapeActs.includes('"phase":"enforce"') ? 'enforce state action present' : 'NO enforce action — the tick was abandoned');
    const markerAfter = marker.ok ? ctx.store.getMessage(marker.value.msg_id) : null;
    check(lines, !!shapeTick && !!markerAfter && markerAfter.broadcast_at_tick === shapeTick.tick,
      'S2f BROADCAST still ran for that tick — the marker note is stamped with THIS tick number, not merely left alone',
      markerAfter ? `broadcast_at_tick=${markerAfter.broadcast_at_tick} tick=${shapeTick && shapeTick.tick}` : 'marker unreadable');
    const tickRow = shapeTick ? ctx.store._prepare('SELECT tick FROM ticks WHERE tick = ?').get(shapeTick.tick) : null;
    check(lines, !!tickRow,
      'S2g RECORDTICK still ran for that tick — the `ticks` row is on disk',
      tickRow ? `ticks row tick=${tickRow.tick}` : 'NO ticks row — recordTick never ran');
    const shapeLeaked = await waitFor(() => fs.existsSync(path.join(shapeDir, 'argv-echo.json')), 3000);
    check(lines, !shapeLeaked,
      'S2h and NO child was exec\'d for the malformed entry — the refusal is the outcome, not just a log line',
      shapeLeaked ? 'argv-echo.json EXISTS — a shape refusal still reached the exec' : 'no argv-echo.json');

    // ── S3 · CRITERION (9): THE SHIPPED CATALOGUE STILL COMPOSES, ENTRY BY ENTRY, BY EXECUTION ───
    // Not by inspection: every `tools:` entry of the REAL `config/spawn-profiles.yaml` goes through
    // ticker.js's own resolver expression and the REAL expander. A FROZEN entry must resolve `allow`
    // to null, carry no placeholder, and compose BYTE-IDENTICALLY to its registered argv; the
    // allowlisted entry must still admit every listed member. The count is deliberately not a
    // literal here — it is computed and printed, because a figure written into an assertion is the
    // very defect item 2 of this row corrects.
    const shippedTools = (yaml.load(fs.readFileSync(SHIPPED_CONFIG, 'utf8')) || {}).tools || {};
    const shippedNames = Object.keys(shippedTools);
    check(lines, shippedNames.length > 0,
      'S3a the SHIPPED tools catalogue was read and is NON-EMPTY — an empty read would make every arm below vacuous',
      `${shippedNames.length} entries: ${shippedNames.join(' ')}`);
    let frozenEntries = 0;
    let listedEntries = 0;
    const drift = [];
    for (const name of shippedNames) {
      const entry = shippedTools[name] || {};
      const argv = Array.isArray(entry.argv) ? entry.argv : [];
      const allow = (entry && entry.args_allowlist) || null;  // ticker.js's own resolver expression
      if (!allow && !argv.some((t) => typeof t === 'string' && t.includes('{{'))) {
        frozenEntries += 1;
        const composed = expandArgv(argv, {}, null);
        if (composed.refused || JSON.stringify(composed.argv) !== JSON.stringify(argv)) {
          drift.push(`${name}: ${composed.refused || JSON.stringify(composed.argv)}`);
        }
        continue;
      }
      listedEntries += 1;
      const shapeBad = checkTemplateArgs({}, allow);
      if (shapeBad) { drift.push(`${name}: SHAPE ${shapeBad}`); continue; }
      for (const [key, permitted] of Object.entries(allow || {})) {
        for (const value of (Array.isArray(permitted) ? permitted : [])) {
          const c = expandArgv(argv, { [key]: value }, allow);
          if (c.refused || !c.argv.includes(value)) drift.push(`${name}.${key}: ${c.refused || 'listed value absent from the composed argv'}`);
        }
      }
    }
    check(lines, drift.length === 0 && frozenEntries > 0 && listedEntries > 0,
      `S3b every SHIPPED tools entry still composes unchanged — ${frozenEntries} frozen byte-identical, ${listedEntries} allowlisted admitting every listed member`,
      drift.length ? `DRIFT: ${drift.join(' | ')}` : `frozen=${frozenEntries} allowlisted=${listedEntries} of ${shippedNames.length}`);
    const liveRowTool = shippedTools['goal-creation-request'] || null;
    check(lines, !!liveRowTool && !liveRowTool.args_allowlist
      && !(liveRowTool.argv || []).some((t) => typeof t === 'string' && t.includes('{{')),
      'S3c `goal-creation-request` — the tool the LIVE 300 s queue row fires — is still FROZEN: no allowlist, no placeholder, so the new guard is not even on its path',
      liveRowTool ? JSON.stringify(liveRowTool.argv) : 'ENTRY ABSENT from the shipped catalogue');

    // ── The pure gate answers `null` on the legal row — the module-level control for every H arm ─
    check(lines, checkTemplateArgs(goodArgs) === null,
      'C the value gate passes the legal row', String(checkTemplateArgs(goodArgs)));
    check(lines, checkTemplateArgs({ goal: goalA }, { goal: [goalA] }) === null,
      'C7559 the identity gate passes a LISTED value — every F refusal above is measured against this control',
      String(checkTemplateArgs({ goal: goalA }, { goal: [goalA] })));

    lines.push(`CHECKS: ${passed}/${passed + failed} passed`);
    lines.push(`ARGV_TEMPLATE_OK: ${failed === 0}`);
    if (failed > 0) throw new Error(`${failed} check(s) failed`);
  } finally {
    for (const p of [templateScratch, storeScratch, allowScratch]) {
      try { fs.unlinkSync(p); } catch {}
    }
    teardown(ctx);
  }
}

capture('probe-argv-template', run);
