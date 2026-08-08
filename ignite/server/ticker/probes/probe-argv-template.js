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
// ⚠ TWO RED ARMS, because the two gates are two separate claims. R1 cuts the value rule out of a
// SCRATCH copy of `argv-template.js` and shows a `;`-bearing value expand — proving the value gate
// is what refuses. R2 cuts the `checkTemplateArgs` call out of a SCRATCH copy of `heart-store.js`
// and shows the same row ENQUEUE — proving the store actually calls the gate rather than merely
// having a green sibling. Neither mutation touches the live tree, and each is asserted to have
// actually altered the source before its result is trusted.

const fs = require('node:fs');
const path = require('node:path');
const { setup, teardown, capture } = require('./lib');
const { expandArgv, checkTemplateArgs, MAX_NAME, MAX_PATH } = require('../../heart/argv-template');

const TEMPLATE_SRC = path.join(__dirname, '..', '..', 'heart', 'argv-template.js');
const HEART_STORE_SRC = path.join(__dirname, '..', '..', 'heart', 'heart-store.js');
// Scratch copies MUST live beside their originals: both resolve siblings (`./errors`,
// `./argv-template`, `schema.sql`) off their own __dirname. Removed in `finally`.
const templateScratch = path.join(__dirname, '..', '..', 'heart', `argv-template.__c5scratch-${process.pid}.js`);
const storeScratch = path.join(__dirname, '..', '..', 'heart', `heart-store.__c5scratch-${process.pid}.js`);

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
    const R1_ANCHOR = 'function checkTemplateArgs(args) {';
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

    // ── The pure gate answers `null` on the legal row — the module-level control for every H arm ─
    check(lines, checkTemplateArgs(goodArgs) === null,
      'C the value gate passes the legal row', String(checkTemplateArgs(goodArgs)));

    lines.push(`CHECKS: ${passed}/${passed + failed} passed`);
    lines.push(`ARGV_TEMPLATE_OK: ${failed === 0}`);
    if (failed > 0) throw new Error(`${failed} check(s) failed`);
  } finally {
    for (const p of [templateScratch, storeScratch]) {
      try { fs.unlinkSync(p); } catch {}
    }
    teardown(ctx);
  }
}

capture('probe-argv-template', run);
