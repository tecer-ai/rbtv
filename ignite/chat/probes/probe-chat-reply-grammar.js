'use strict';

const path = require('node:path');
const fs = require('node:fs');
const { parseReply, NACK_ASK, NACK_MECHANICAL } = require('../reply-grammar');

const OUT = path.join(__dirname, 'probe-chat-reply-grammar.out');
const t0 = Date.now();
const checks = [];
const check = (name, pass, evidence) => { checks.push({ name, pass, evidence }); };

const ASK = "couldn't parse that reply. First word must be one of: approve, reject-and-close, reject-and-pause, reject-and-retry, retry with:, close, a letter (a–g), pause {goal}, resume {goal}. Comments go after that word. Reply again.";
const MECH = "couldn't parse pause/resume. Use `pause {goal}` or `resume {goal}` with one live goal slug. In a goal channel, bare pause/resume targets that goal. Reply again.";

function ok(text, extra) {
  const r = parseReply(text, extra);
  return r.ok === true ? r : null;
}

function fail(text, extra) {
  const r = parseReply(text, extra);
  return r.ok === false ? r : null;
}

check('§4.5 ask NACK string is byte-exact on the export and on a failure',
  NACK_ASK === ASK && fail('ok').nack === ASK && fail('ok').nackKind === 'ask',
  { nack: fail('ok').nack });

check('§4.5 mechanical NACK string is byte-exact on the export and on a failure',
  NACK_MECHANICAL === MECH && fail('pause', {}).nack === MECH && fail('pause', {}).nackKind === 'mechanical',
  { nack: fail('pause', {}).nack });

const approvalRows = [
  ['approve', ['approve', 'approved', 'APPROVE', 'Approved'], 'approve'],
  ['reject-and-close', ['reject-and-close', 'reject and close', 'REJECT AND CLOSE', 'Reject-And-Close'], 'reject-and-close'],
  ['reject-and-pause', ['reject-and-pause', 'reject and pause', 'reject-and pause'], 'reject-and-pause'],
  ['reject-and-retry', ['reject-and-retry', 'reject and retry'], 'reject-and-retry'],
  ['retry with:', ['retry with:', 'retry with', 'RETRY WITH:', 'retry-with:', 'retry-with'], 'retry with:'],
  ['close', ['close', 'CLOSE'], 'close'],
];

for (const [canonical, variants, outcome] of approvalRows) {
  for (const v of variants) {
    const r = ok(v);
    check(`§4.2 ${canonical} variant ${JSON.stringify(v)}`,
      !!r && r.outcome === outcome && r.family === 'approval' && r.goal === null,
      { got: r && { outcome: r.outcome, family: r.family } });
  }
}

const letterForms = (L) => {
  const l = L.toLowerCase();
  const u = L.toUpperCase();
  return [
    l, u,
    `${l})`, `${u})`,
    `${u}.`, `${l}.`,
    `${l}:`, `${u}:`,
    `option ${l}`, `option ${u}`, `option ${l})`,
    `option-${l}`, `OPTION ${u})`,
  ];
};

for (const L of 'abcdefg') {
  for (const v of letterForms(L)) {
    const r = ok(v);
    check(`§4.2 letter ${L} variant ${JSON.stringify(v)}`,
      !!r && r.outcome === L && r.family === 'lettered',
      { got: r && { outcome: r.outcome, family: r.family } });
  }
}

const nacked = ['ok', 'okay', 'go', 'lgtm', 'looks good', 'yes', 'yep', 'y', 'reject', 'no', 'nah', 'retry', 'please approve', 'sure', 'apple', 'h', 'approve.', 'rejectandclose'];
for (const w of nacked) {
  const r = fail(w);
  check(`§4.3 ${JSON.stringify(w)} is ask NACK`,
    !!r && r.nack === ASK && r.nackKind === 'ask',
    { got: r });
}

check('§4.1 empty leading lines are ignored',
  ok('\n\n  \napprove later').outcome === 'approve' && ok('\n\n  \napprove later').comments === 'later',
  { r: ok('\n\n  \napprove later') });

check('§4.1 empty / whitespace-only text is ask NACK',
  fail('').nack === ASK && fail('  \n\n').nack === ASK && fail(null).nack === ASK,
  {});

check('§4.1 longest match: reject and close wins over bare reject',
  ok('reject and close the plan').outcome === 'reject-and-close'
    && fail('reject').nackKind === 'ask'
    && ok('reject and close the plan').comments === 'the plan',
  { r: ok('reject and close the plan') });

check('§4.1 hyphen/space equivalence on multi-word tokens',
  ok('reject-and-close').outcome === 'reject-and-close'
    && ok('reject and close').outcome === 'reject-and-close'
    && ok('reject-and close').outcome === 'reject-and-close',
  {});

check('§4.1 case-insensitive',
  ok('APPROVED ship it').outcome === 'approve' && ok('APPROVED ship it').comments === 'ship it',
  {});

check('§4.1 letter trailing punctuation does not leak into comments',
  ok('a) because binder').comments === 'because binder'
    && ok('B. second').outcome === 'b'
    && ok('c: note').comments === 'note',
  {});

check('§4.1 leading filler words are not stripped',
  fail('please approve').nackKind === 'ask' && fail('I approve').nackKind === 'ask',
  {});

check('§4.1 comments capture rest of first line plus following lines',
  ok('approve first line\nsecond\n\nthird').comments === 'first line\nsecond\n\nthird',
  { comments: ok('approve first line\nsecond\n\nthird').comments });

const retry = ok('retry with:\n- missing tests\n- wrong path');
check('§4.2 retry with: comments are the findings list',
  retry && retry.outcome === 'retry with:' && retry.family === 'approval'
    && retry.comments === '- missing tests\n- wrong path'
    && Array.isArray(retry.findings)
    && retry.findings.length === 2
    && retry.findings[0] === '- missing tests'
    && retry.findings[1] === '- wrong path',
  { retry });

const rar = ok('reject-and-retry tighten the envelope');
check('§4.2 reject-and-retry findings are comments split into a list',
  rar && rar.findings && rar.findings.join('|') === 'tighten the envelope',
  { rar });

check('non-findings outcomes carry findings: null',
  ok('approve x').findings === null && ok('a extra').findings === null && ok('close').findings === null,
  {});

const p = ok('pause my-goal leftover', { liveGoals: ['my-goal', 'other'] });
check('§4.2 pause {goal} parses slug and leftover comments',
  p && p.outcome === 'pause' && p.family === 'mechanical' && p.goal === 'my-goal' && p.comments === 'leftover',
  { p });

const rsm = ok('resume my-goal do this next', { liveGoals: ['my-goal'] });
check('§4.2 resume {goal} with comments (resume-with-instructions)',
  rsm && rsm.outcome === 'resume' && rsm.goal === 'my-goal' && rsm.comments === 'do this next',
  { rsm });

check('§4.2 bare pause in a goal channel targets channelGoal',
  ok('pause', { channelGoal: 'chan-goal' }).goal === 'chan-goal'
    && ok('PAUSE', { channelGoal: 'chan-goal' }).outcome === 'pause',
  {});

check('§4.2 bare resume in a goal channel targets channelGoal',
  ok('resume', { channelGoal: 'chan-goal' }).goal === 'chan-goal',
  {});

check('§4.2 bare pause/resume without channelGoal is mechanical NACK',
  fail('pause').nack === MECH && fail('resume').nack === MECH,
  {});

check('§4.2 slug matching zero live goals is mechanical NACK',
  fail('pause ghost', { liveGoals: ['my-goal'] }).nack === MECH,
  {});

check('§4.2 slug matching multiple live goals is mechanical NACK',
  fail('pause Foo', { liveGoals: ['Foo', 'foo'] }).nack === MECH,
  {});

check('§4.2 liveGoals case-insensitive unique hit returns the live spelling',
  ok('pause MY-GOAL', { liveGoals: ['My-Goal'] }).goal === 'My-Goal',
  {});

check('letters past a–c still parse (seat may re-ask)',
  ok('g').outcome === 'g' && fail('h').nackKind === 'ask',
  {});

check('same parser for approval and lettered replies (one function)',
  ok('approve').family === 'approval' && ok('b)').family === 'lettered' && ok('close').family === 'approval',
  {});

check('pure module: result has no ask-record fields and does not mention open',
  !('state' in ok('approve')) && !('open' in ok('approve')) && !('id' in fail('ok')),
  {});

const pass = checks.every((c) => c.pass);
const wallMs = Date.now() - t0;
const exit = pass ? 0 : 1;
fs.writeFileSync(OUT, `${JSON.stringify({
  summary: { probe: 'probe-chat-reply-grammar', pass, checks: checks.length, failed: checks.filter((c) => !c.pass).map((c) => c.name), EXIT: exit, WALL_MS: wallMs, SKIPPED_COUNT: 0 },
  entries: checks,
}, null, 2)}\n`);
process.stdout.write(`PROBE probe-chat-reply-grammar EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length}\n`);
if (!pass) process.stdout.write(`FAILED: ${checks.filter((c) => !c.pass).map((c) => c.name).join(' | ')}\n`);
process.exit(exit);
