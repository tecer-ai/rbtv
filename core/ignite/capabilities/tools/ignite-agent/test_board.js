'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { CAPS, EMPTY_BOARD, parseBoard, writeBoard, closeSubject, boardPath, migrateBoard, refreshBoard, renderBoard } = require('./board.js');
const { Store } = require('./store.js');

const failures = [];
let passed = 0;

function test(name, fn) {
  try {
    fn();
    passed++;
    console.log(`PASS ${name}`);
  } catch (error) {
    failures.push(name);
    console.log(`FAIL ${name}: ${error.stack || error.message}`);
  }
}

// The ruled template's filled example, including its fictional agent and links.
const FILLED_EXAMPLE = `## What matters now

### Conference talk draft
Outline approved by the owner; slides 1–8 drafted, 9–14 pending.
Next: send the full draft for review by 2026-10-02.
- Threads: [outline review](https://example.slack.com/archives/C0000/p1001) · [slide cut](https://example.slack.com/archives/C0000/p1009)
- Detail: ../memory/conference-talk.md
- Flags: answered 2026-10-01

### Printer toner reorder
Supplier quoted two options; waiting for the owner to pick one.
- Threads: none
- Detail: none
- Flags: none

## Watch-outs

- Send drafts as one PDF, never as separate slide images. (2026-10-02 · janice/[outline review](https://example.slack.com/archives/C0000/p1001))

## Timers

| Fires | Timer | For | Subject |
|---|---|---|---|
| 2026-10-02 09:00 Europe/Lisbon | talk-draft-review | Check the full draft is sent; remind the owner if not | Conference talk draft |

## Recently closed

- Team lunch booking — booked for 2026-10-09, confirmation in the thread. (2026-10-01 · janice/[lunch thread](https://example.slack.com/archives/C0000/p0990))
`;

function subject(title, state = 'Waiting for review.') {
  return `### ${title}\n${state}\n- Threads: none\n- Detail: none\n- Flags: none\n`;
}

function board({ subjects = [], watchOuts = [], timers = [], closed = [] } = {}) {
  return `## What matters now\n\n${subjects.join('\n')}\n## Watch-outs\n\n${watchOuts.join('\n')}\n\n## Timers\n\n${timers.join('\n')}\n\n## Recently closed\n\n${closed.join('\n')}\n`;
}

function withBoard(text, fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite board-'));
  const file = path.join(dir, 'board.md');
  if (text !== null) fs.writeFileSync(file, text, 'utf8');
  try { fn(file); } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}

const closedRows = (count) => Array.from({ length: count }, (_, i) => `- Old subject ${i} — done (2026-10-01 · sample)`);
const NOW = Date.parse('2026-10-03T12:00:00Z');

test('filled template example passes in LF and CRLF', () => {
  for (const text of [FILLED_EXAMPLE, FILLED_EXAMPLE.replace(/\n/g, '\r\n')]) {
    const parsed = parseBoard(text);
    assert.equal(parsed.subjects.length, 2);
    assert.equal(parsed.subjects[0].state.length, 2);
    assert.equal(parsed.subjects[0].flags, 'answered 2026-10-01');
    assert.equal(parsed.watchOuts.length, 1);
    assert.equal(parsed.timers.length, 3);
    assert.equal(parsed.closed.length, 1);
  }
});

test('all four sections may be empty', () => {
  const parsed = parseBoard(EMPTY_BOARD);
  assert.equal(parsed.subjects.length, 0);
  assert.equal(parsed.nonEmpty, 4);
});

test('exact shape caps pass together', () => {
  const parsed = parseBoard(board({
    subjects: Array.from({ length: CAPS.subjects }, (_, i) => subject(`Subject ${i}`, 'First fact.\nSecond fact.\nThird fact.')),
    watchOuts: Array.from({ length: CAPS.watchOuts }, (_, i) => `- Rule ${i} (2026-10-01 · sample)`),
    closed: closedRows(CAPS.closed),
  }));
  assert.equal(parsed.subjects.length, 8);
  assert.equal(parsed.nonEmpty, 72);
});

test('Timers table is outside the line cap, with no schedule count cap', () => {
  const timers = ['| Fires | Timer | For | Subject |', '|---|---|---|---|',
    ...Array.from({ length: 100 }, (_, i) => `| 2026-10-02 09:00 Europe/Lisbon | timer-${i} | Check | none |`)];
  const parsed = parseBoard(board({ subjects: [subject('Review')], timers }));
  assert.equal(parsed.nonEmpty, 9);
  assert.equal(parsed.timers.length, 102);
});

test('blank lines are uncounted', () => {
  assert.equal(parseBoard(EMPTY_BOARD.replace(/\n/g, '\n\n\n')).nonEmpty, 4);
});

for (const [name, text, error] of [
  ['missing section', EMPTY_BOARD.replace('## Watch-outs\n', ''), /headings|four/],
  ['duplicate section', EMPTY_BOARD + '\n## Recently closed\n', /headings/],
  ['unknown section', EMPTY_BOARD.replace('## Timers', '## Notes'), /headings/],
  ['preamble', '# Board\n' + EMPTY_BOARD, /start/],
  ['no state', board({ subjects: [subject('Review', '')] }), /1–3 state/],
  ['too many state lines', board({ subjects: [subject('Review', 'a\nb\nc\nd')] }), /1–3 state/],
  ['duplicate title', board({ subjects: [subject('Review'), subject('Review')] }), /unique/],
  ['extra subject field', board({ subjects: [subject('Review').replace('- Threads:', '- Timers: timer\n- Threads:')] }), /1–3 state/],
  ['bare thread URL', board({ subjects: [subject('Review').replace('Threads: none', 'Threads: https://example.com/t')] }), /Threads/],
  ['broken link URL', board({ subjects: [subject('Review').replace('Threads: none', 'Threads: [review](https://))')] }), /Threads/],
  ['unbalanced link', board({ subjects: [subject('Review').replace('Threads: none', 'Threads: [review](https://example.com/a)[b](https://example.com/b)')] }), /Threads/],
  ['wrong thread separator', FILLED_EXAMPLE.replace(') · [slide cut]', '), [slide cut]'), /Threads/],
  ['empty detail', board({ subjects: [subject('Review').replace('Detail: none', 'Detail:')] }), /Detail/],
  ['bad flag', FILLED_EXAMPLE.replace('answered 2026-10-01', 'pending'), /Flags/],
  ['impossible date', FILLED_EXAMPLE.replace('answered 2026-10-01', 'answered 2026-02-30'), /Flags/],
  ['missing provenance', board({ watchOuts: ['- Send a PDF.'] }), /provenance/],
  ['bad provenance date', board({ watchOuts: ['- Send a PDF. (2026-13-01 · sample)'] }), /provenance/],
  ['missing closed outcome', board({ closed: ['- Review (2026-10-01 · sample)'] }), /outcome/],
  ['timer prose', board({ timers: ['Do a thing.'] }), /table/],
  ['bad timer header', FILLED_EXAMPLE.replace('| Fires | Timer', '| Cron | Timer'), /Fires/],
  ['cron fire', FILLED_EXAMPLE.replace('2026-10-02 09:00 Europe/Lisbon', '0 9 * * *'), /next fire/],
  ['bad timer clock', FILLED_EXAMPLE.replace('09:00 Europe/Lisbon', '25:00 Europe/Lisbon'), /next fire/],
  ['bad timer timezone', FILLED_EXAMPLE.replace('Europe/Lisbon', 'Mars/Olympus'), /IANA/],
  ['subject overflow', board({ subjects: Array.from({ length: 9 }, (_, i) => subject(`Subject ${i}`)) }), /at most 8/],
  ['watch-out overflow', board({ watchOuts: Array.from({ length: 7 }, () => '- Rule (2026-10-01 · sample)') }), /at most 6 watch/],
  ['closed overflow', board({ closed: closedRows(7) }), /at most 6 Recently/],
  ['line overflow', EMPTY_BOARD + 'extra\n'.repeat(91), /at most 90/],
  ['expiry not last', board({ subjects: [subject('Review', 'Hold until 2026-10-03 then resume.')] }), /temporary facts/],
  ['bare carriage return', board({ subjects: [subject('Review', 'First\rSecond')] }), /LF or CRLF/],
  ['NUL byte', board({ subjects: [subject('Review', 'First\0Second')] }), /NUL/],
]) {
  test(`refuses ${name}`, () => assert.throws(() => parseBoard(text), error));
}

test('expiry, idle flag, vault detail and provenance without a thread pass', () => {
  const text = board({ subjects: [subject('Review', 'Hold until 2026-10-03')
    .replace('Flags: none', 'Flags: idle since 2026-09-01')
    .replace('Detail: none', 'Detail: projects/review.md')],
  watchOuts: ['- Send one PDF until 2026-10-03 (2026-10-01 · sample)'] });
  assert.equal(parseBoard(text).subjects[0].detail, 'projects/review.md');
});

test('thread URLs may contain balanced parentheses', () => {
  const text = board({ subjects: [subject('Review').replace('Threads: none', 'Threads: [review](https://example.com/Review_(talk))')] });
  assert.equal(parseBoard(text).subjects.length, 1);
});

test('write creates a missing board and repeated identical bytes are unchanged', () => {
  withBoard(null, (file) => {
    const text = board({ subjects: [subject('Résumé review')] });
    assert.deepEqual(writeBoard(file, text), { path: file, changed: true });
    assert.equal(fs.readFileSync(file, 'utf8'), text);
    assert.deepEqual(writeBoard(file, text), { path: file, changed: false });
    assert.equal(writeBoard(file, text.replace(/\n/g, '\r\n')).changed, true);
    assert.equal(fs.readFileSync(file, 'utf8'), text.replace(/\n/g, '\r\n'));
  });
});

test('write updates subjects and watch-outs without changing runtime data', () => {
  withBoard(FILLED_EXAMPLE, (file) => {
    const next = FILLED_EXAMPLE.replace('Supplier quoted two options; waiting for the owner to pick one.', 'Owner chose toner café.')
      .replace('Send drafts as one PDF, never as separate slide images.', 'Send one PDF.');
    assert.equal(writeBoard(file, next).changed, true);
    assert.equal(fs.readFileSync(file, 'utf8'), next);
  });
});

test('write refuses runtime edits and subject removal without touching any bytes', () => {
  withBoard(FILLED_EXAMPLE, (file) => {
    const before = fs.readFileSync(file);
    for (const [next, error] of [
      [FILLED_EXAMPLE.replace('answered 2026-10-01', 'answered 2026-10-02'), /Flags/],
      [FILLED_EXAMPLE.replace('09:00 Europe/Lisbon', '10:00 Europe/Lisbon'), /Timers/],
      [FILLED_EXAMPLE.replace('booked for 2026-10-09', 'booked for 2026-10-10'), /Recently closed/],
      [FILLED_EXAMPLE.replace('### Printer toner reorder', '### Replacement subject'), /board close/],
      [FILLED_EXAMPLE.replace('## Watch-outs', '## Wrong'), /headings/],
    ]) {
      assert.throws(() => writeBoard(file, next), error);
      assert.deepEqual(fs.readFileSync(file), before);
    }
  });
});

test('new subjects cannot set runtime flags and invalid writes create no file', () => {
  withBoard(null, (file) => {
    assert.throws(() => writeBoard(file, board({ subjects: [subject('Review').replace('Flags: none', 'Flags: answered 2026-10-01')] })), /Flags/);
    assert.equal(fs.existsSync(file), false);
    assert.throws(() => writeBoard(file, 'invalid'), /board refused/);
    assert.equal(fs.existsSync(file), false);
  });
});

test('a malformed existing board is preserved rather than silently replaced', () => {
  withBoard('# Board\r\nlegacy content\r\n', (file) => {
    const before = fs.readFileSync(file);
    assert.throws(() => writeBoard(file, EMPTY_BOARD), /board refused/);
    assert.throws(() => closeSubject(file, 'Review', 'Done', { agent: 'sample' }), /board refused/);
    assert.deepEqual(fs.readFileSync(file), before);
  });
});

test('close removes only the named subject and appends a dated outcome with thread', () => {
  withBoard(FILLED_EXAMPLE.replace(/\n/g, '\r\n'), (file) => {
    const result = closeSubject(file, 'Conference talk draft', 'Draft sent — café slides included.', {
      agent: 'sample', now: NOW, thread: '[review](https://example.com/review)',
    });
    assert.equal(result.subject, 'Conference talk draft');
    const text = fs.readFileSync(file, 'utf8');
    const parsed = parseBoard(text);
    assert.deepEqual(parsed.subjects.map((row) => row.title), ['Printer toner reorder']);
    assert.deepEqual(parsed.watchOuts, parseBoard(FILLED_EXAMPLE).watchOuts);
    assert.deepEqual(parsed.timers, parseBoard(FILLED_EXAMPLE).timers);
    assert.equal(parsed.closed[0], parseBoard(FILLED_EXAMPLE).closed[0]);
    assert.equal(parsed.closed[1], '- Conference talk draft — Draft sent — café slides included. (2026-10-03 · sample/[review](https://example.com/review))');
    assert.doesNotMatch(text, /(?<!\r)\n/);
  });
});

test('close without a thread fills the sixth slot and leaves all section headings', () => {
  withBoard(board({ subjects: [subject('Review')], closed: closedRows(5) }), (file) => {
    closeSubject(file, 'Review', 'Accepted', { agent: 'sample', now: NOW });
    const parsed = parseBoard(fs.readFileSync(file, 'utf8'));
    assert.equal(parsed.subjects.length, 0);
    assert.equal(parsed.closed.length, 6);
    assert.equal(parsed.closed[5], '- Review — Accepted (2026-10-03 · sample)');
  });
});

test('full Recently closed refuses the whole close without dropping any entry', () => {
  withBoard(board({ subjects: [subject('Review')], closed: closedRows(6) }), (file) => {
    const before = fs.readFileSync(file);
    assert.throws(() => closeSubject(file, 'Review', 'Done', { agent: 'sample', now: NOW }), /at most 6 Recently/);
    assert.deepEqual(fs.readFileSync(file), before);
  });
});

test('invalid close arguments and repeat closures leave the board unchanged', () => {
  withBoard(board({ subjects: [subject('Review')] }), (file) => {
    const before = fs.readFileSync(file);
    for (const [title, outcome, options] of [
      ['Missing', 'Done', { agent: 'sample' }],
      ['Review', '', { agent: 'sample' }],
      ['Review', 'Done\nMore', { agent: 'sample' }],
      ['Review', 'Done', { agent: 'bad\nagent' }],
      ['Review', 'Done', { agent: 'sample', thread: 'https://example.com' }],
    ]) {
      assert.throws(() => closeSubject(file, title, outcome, options), /board refused/);
      assert.deepEqual(fs.readFileSync(file), before);
    }
    closeSubject(file, 'Review', 'Done', { agent: 'sample', now: NOW });
    const closed = fs.readFileSync(file);
    assert.throws(() => closeSubject(file, 'Review', 'Done', { agent: 'sample', now: NOW }), /not found/);
    assert.deepEqual(fs.readFileSync(file), closed);
  });
});

test('legacy copy preserves UTF-8 and CRLF bytes and never replaces the canonical board', () => {
  withBoard('legacy café\r\n', (legacy) => {
    const home = path.dirname(legacy);
    const file = migrateBoard(home);
    assert.equal(file, boardPath(home));
    assert.deepEqual(fs.readFileSync(file), fs.readFileSync(legacy));
    fs.writeFileSync(legacy, 'old path changed\n', 'utf8');
    assert.equal(migrateBoard(home), file);
    assert.equal(fs.readFileSync(file, 'utf8'), 'legacy café\r\n');
    assert.equal(fs.readFileSync(legacy, 'utf8'), 'old path changed\n');
  });
});

function runtimeBoard(text, fn) {
  withBoard(null, (legacy) => {
    const home = path.dirname(legacy);
    const file = boardPath(home);
    fs.mkdirSync(path.dirname(file));
    fs.writeFileSync(file, text, 'utf8');
    const store = new Store(path.join(home, 'state.sqlite'));
    try { fn({ home, file, store }); } finally { store.close(); }
  });
}

test('Timers reflect enabled schedules, IANA local time, UTC offsets, escaped notes and subject', () => {
  runtimeBoard(FILLED_EXAMPLE.replace(/\n/g, '\r\n'), ({ home, file, store }) => {
    const key = 'T1:C1:1.000000';
    store.upsertConversation({ key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs: '1.000000' });
    const put = (id, extra) => store.upsertSchedule({ id, conversationKey: key,
      cadence: 'every:1h', timezone: 'fixed', nextAt: NOW, note: 'Review', ...extra });
    put('cron', { cadence: 'cron:0 8 * * *', timezone: 'America/New_York', subject: 'Conference talk draft' });
    put('once', { cadence: 'at:2026-10-03T09:00:00-03:00', timezone: '-03:00', note: 'café | résumé\r\nnext' });
    put('interval', {});
    put('disabled', { enabled: false });
    put('no-next', { nextAt: null });
    refreshBoard(home, store, NOW);
    const text = fs.readFileSync(file, 'utf8');
    const parsed = parseBoard(text);
    assert.deepEqual(parsed.timers, ['| Fires | Timer | For | Subject |', '|---|---|---|---|',
      '| 2026-10-03 08:00 America/New_York | cron | Review | Conference talk draft |',
      '| 2026-10-03 12:00 UTC | interval | Review | none |',
      '| 2026-10-03 12:00 UTC | once | café &#124; résumé<br>next | none |']);
    assert.deepEqual(parsed.subjects, parseBoard(FILLED_EXAMPLE).subjects);
    assert.deepEqual(parsed.watchOuts, parseBoard(FILLED_EXAMPLE).watchOuts);
    assert.deepEqual(parsed.closed, parseBoard(FILLED_EXAMPLE).closed);
    assert.doesNotMatch(text, /(?<!\r)\n/);
    assert.equal(refreshBoard(home, store, NOW).changed, false);
    store.deleteSchedule('cron');
    refreshBoard(home, store, NOW);
    assert.doesNotMatch(fs.readFileSync(file, 'utf8'), /\| cron \|/);
  });
});

test('runtime timers remain outside the cap and invalid refresh leaves every byte intact', () => {
  runtimeBoard(EMPTY_BOARD, ({ home, file, store }) => {
    store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
    for (let i = 0; i < 100; i++) store.upsertSchedule({ id: `timer-${i}`, conversationKey: 'k',
      cadence: 'every:1h', timezone: 'fixed', nextAt: NOW });
    refreshBoard(home, store, NOW);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).timers.length, 102);
    fs.writeFileSync(file, 'malformed café\r\n', 'utf8');
    const before = fs.readFileSync(file);
    assert.throws(() => refreshBoard(home, store, NOW), /board refused/);
    assert.deepEqual(fs.readFileSync(file), before);
  });
});

test('spent one-shot stays on the board while its wake is pending or running', () => {
  runtimeBoard(EMPTY_BOARD, ({ home, file, store }) => {
    store.upsertConversation({ key: 'k', agent: 'sample', workspace: 'T1', channel: 'C1' });
    store.upsertSchedule({ id: 'reminder', conversationKey: 'k', cadence: 'at:2026-10-03T12:00:00Z',
      timezone: 'Z', nextAt: NOW, enabled: false, note: 'Send the draft' });
    store.enqueueScheduleWake({ id: 'wake', conversationKey: 'k', scheduleId: 'reminder' });
    refreshBoard(home, store, NOW);
    assert.match(fs.readFileSync(file, 'utf8'), /reminder \| Send the draft/);
    const claim = store.claimNext();
    refreshBoard(home, store, NOW);
    assert.match(fs.readFileSync(file, 'utf8'), /reminder \| Send the draft/);
    store.finishRun(claim.runId, claim.nonce, { invocationNonce: claim.nonce, output: '{}', disposition: 'completed' });
    refreshBoard(home, store, NOW);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).timers.length, 2);
  });
});

test('linked owner reply becomes answered then idle at seven days, and a new reply clears idle', () => {
  const root = NOW - 10 * 86_400_000;
  const rootTs = `${root / 1000}.000000`;
  const link = `[review](https://example.slack.com/archives/C1/p${rootTs.replace('.', '')})`;
  const initial = board({ subjects: [subject('Review').replace('Threads: none', `Threads: ${link}`), subject('Threadless')],
    watchOuts: ['- Keep this. (2026-10-01 · sample)'], closed: closedRows(1) });
  runtimeBoard(initial, ({ home, file, store }) => {
    const key = `T1:C1:${rootTs}`;
    store.upsertConversation({ key, agent: 'sample', workspace: 'T1', channel: 'C1', rootTs });
    const reply = NOW - 86_400_000;
    store.recordMessage(key, { id: 'reply', role: 'owner', ts: `${reply / 1000}.000000`, createdAt: reply });
    const flags = () => parseBoard(fs.readFileSync(file, 'utf8')).subjects.map((row) => row.flags);
    refreshBoard(home, store, NOW);
    assert.deepEqual(flags(), ['answered 2026-10-02', 'none']);
    refreshBoard(home, store, reply + 7 * 86_400_000 - 1);
    assert.equal(flags()[0], 'answered 2026-10-02');
    refreshBoard(home, store, reply + 7 * 86_400_000);
    assert.equal(flags()[0], 'idle since 2026-10-02');
    const later = reply + 8 * 86_400_000;
    store.recordMessage(key, { id: 'reply2', role: 'owner', ts: `${later / 1000}.000000`, createdAt: later });
    refreshBoard(home, store, later);
    assert.equal(flags()[0], 'answered 2026-10-10');
    const parsed = parseBoard(fs.readFileSync(file, 'utf8'));
    assert.equal(parsed.subjects.length, 2);
    assert.deepEqual(parsed.watchOuts, parseBoard(initial).watchOuts);
    assert.deepEqual(parsed.closed, parseBoard(initial).closed);
    assert.throws(() => writeBoard(file, fs.readFileSync(file, 'utf8').replace('answered 2026-10-10', 'none')), /Flags/);
  });
});

test('without replies idle starts at the linked root; query links and multiple threads use the latest reply', () => {
  const root = NOW - 8 * 86_400_000;
  const rootTs = `${root / 1000}.000000`;
  const recentRoot = `${(NOW - 86_400_000) / 1000}.000000`;
  const initial = board({ subjects: [subject('Review').replace('Threads: none',
    `Threads: [old](https://example.slack.com/archives/C1/p${rootTs.replace('.', '')}) · [reply](https://example.slack.com/archives/C2/p${recentRoot.replace('.', '')}?thread_ts=${rootTs})`)] });
  runtimeBoard(initial, ({ home, file, store }) => {
    for (const channel of ['C1', 'C2']) store.upsertConversation({ key: channel, agent: 'sample', workspace: 'T1', channel, rootTs });
    store.recordMessage('C1', { id: 'root', role: 'owner', ts: rootTs, createdAt: root });
    store.recordMessage('C1', { id: 'bot', role: 'assistant', ts: recentRoot, createdAt: NOW });
    store.recordMessage('C1', { id: 'synthetic', role: 'owner', createdAt: NOW });
    refreshBoard(home, store, NOW);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).subjects[0].flags, 'idle since 2026-09-25');
    store.recordMessage('C1', { id: 'old-reply', role: 'owner', ts: '2.000000', createdAt: NOW - 86_400_000 });
    store.recordMessage('C2', { id: 'latest-reply', role: 'owner', ts: recentRoot, createdAt: NOW });
    refreshBoard(home, store, NOW);
    assert.equal(parseBoard(fs.readFileSync(file, 'utf8')).subjects[0].flags, 'answered 2026-10-03');
  });
});

test('renderBoard refreshes checked recovered text without any filesystem write', () => {
  runtimeBoard('broken working copy\r\n', ({ file, store }) => {
    const before = fs.readFileSync(file);
    const result = renderBoard(FILLED_EXAMPLE.replace(/\n/g, '\r\n'), store, NOW);
    assert.equal(parseBoard(result).subjects.length, 2);
    assert.equal(parseBoard(result).timers.length, 2);
    assert.ok(result.includes('\r\n'));
    assert.deepEqual(fs.readFileSync(file), before);
    assert.throws(() => renderBoard('broken', store, NOW), /board refused/);
  });
});

test('a runtime refresh leaves a missing board absent for turn-start HEAD recovery', () => {
  runtimeBoard(EMPTY_BOARD, ({ home, file, store }) => {
    fs.unlinkSync(file);
    assert.deepEqual(refreshBoard(home, store, NOW), { path: file, changed: false });
    assert.equal(fs.existsSync(file), false);
  });
});

console.log(`${passed} passed, ${failures.length} failed`);
if (failures.length) process.exit(1);
