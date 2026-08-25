'use strict';

// -- SELFTESTS FOR THE ONE ALARM EMITTER --------------------------------------------------------
//
// Two clauses carry this file, and both are regressions of a real failure:
//
//   (a) THE SCHEMA GATE. Every one of the required fields, dropped one at a time, must THROW at the
//       emitting call site and post NOTHING. The alarm that read `frozen: undefined` for 13 hours is
//       what a missing field looks like when the emitter is permissive.
//   (b) DEDUP ACROSS A RESTART. Two emissions of the same signature leave ONE registry row and ONE
//       post. The deleted `goal-stall-alarm.js` held this in a process-lifetime Map; the assertion
//       here re-reads the row set FROM DISK through a second emitter instance, because surviving a
//       daemon restart is the whole reason the registry is persisted.
//
// The outbox is a recording stub: what this file must prove is what the emitter HANDS the outbox and
// when, not that the real outbox delivers (that is `chat/`'s own selftest).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert');

const {
  REQUIRED_FIELDS, createAlarmEmitter, validateAlarm, signatureOf,
} = require('./emitter');

const tmpRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'observation-emitter-'));
let failed = 0;

function pass(name) { process.stdout.write(`PASS ${name}\n`); }
function fail(name, err) {
  failed += 1;
  process.stdout.write(`FAIL ${name}: ${err && err.message ? err.message : err}\n`);
  if (err && err.stack) process.stdout.write(`${err.stack}\n`);
}

function stubOutbox() {
  const posts = [];
  return {
    posts,
    post: async (input) => {
      posts.push(input);
      return { delivered: true, ts: `ts-${posts.length}`, outbox_id: `ob-${posts.length}`, error: null };
    },
  };
}

const GOOD = Object.freeze({
  condition: 'the daemon has not answered its own health probe',
  subject: { type: 'goal', id: 'ignite-engine' },
  evidence_pointer: '.rbtv/runtime/ignite/watchdog.log',
  what_would_clear_it: 'the daemon answering one probe',
  signature_class: 'daemon-down',
  immediate: true,
  channel_id: 'C-system',
});

// (a) THE SCHEMA GATE — one arm per required field, plus the explicit-`immediate` arm.
async function caseMissingFieldThrows() {
  const name = 'schema: each missing required field throws and posts nothing';
  const box = stubOutbox();
  const emitter = createAlarmEmitter({ storePath: path.join(tmpRoot, 'schema.json'), post: box.post });
  for (const field of REQUIRED_FIELDS) {
    const broken = { ...GOOD };
    delete broken[field];
    let threw = null;
    try { await emitter.emit(broken); } catch (err) { threw = err; }
    assert.ok(threw, `dropping \`${field}\` must throw`);
    assert.match(threw.message, new RegExp(field), `the throw must name \`${field}\``);
    process.stdout.write(`  missing field \`${field}\` → throws: ${threw.message}\n`);
  }
  const noImmediate = { ...GOOD };
  delete noImmediate.immediate;
  await assert.rejects(() => emitter.emit(noImmediate), /immediate/);
  process.stdout.write('  missing field `immediate` → throws [CF-9]\n');
  assert.strictEqual(box.posts.length, 0, 'a schema failure must post NOTHING');
  assert.strictEqual(emitter.readOpenConditions().length, 0, 'a schema failure must register NOTHING');
  pass(name);
}

async function caseEmptyAndTokenFieldsRefused() {
  const name = 'schema: empty condition, bare subject and empty clear-it are refused';
  assert.throws(() => validateAlarm({ ...GOOD, condition: '   ' }), /plain words/);
  assert.throws(() => validateAlarm({ ...GOOD, subject: 'goal-1' }), /concrete/);
  assert.throws(() => validateAlarm({ ...GOOD, subject: { type: 'goal' } }), /concrete/);
  assert.throws(() => validateAlarm({ ...GOOD, what_would_clear_it: '' }), /required field/);
  // `unknown` is a legal ANSWER, and this is the arm that keeps it legal.
  assert.ok(validateAlarm({ ...GOOD, what_would_clear_it: 'unknown' }));
  pass(name);
}

// (b) DEDUP — two emits of one signature before the condition changes → ONE row, ONE post.
async function caseDedupOneRowOnePost() {
  const name = 'dedup: two emits of the same signature → one registry row, one post';
  const storePath = path.join(tmpRoot, 'dedup.json');
  const box = stubOutbox();
  const emitter = createAlarmEmitter({ storePath, post: box.post });
  const first = await emitter.emit(GOOD);
  const second = await emitter.emit(GOOD);
  assert.strictEqual(first.posted, true);
  assert.strictEqual(first.reason, 'first');
  assert.strictEqual(second.posted, false);
  assert.strictEqual(second.reason, 'deduped');
  assert.strictEqual(box.posts.length, 1, 'the second emit must not reach the outbox');
  const onDisk = JSON.parse(fs.readFileSync(storePath, 'utf8')).rows;
  assert.strictEqual(onDisk.length, 1, 'the registry must carry exactly one row');
  assert.strictEqual(onDisk[0].signature, signatureOf(GOOD));
  assert.strictEqual(onDisk[0].emission_count, 1);
  process.stdout.write(`  registry rows after two emits: ${onDisk.length} (signature ${onDisk[0].signature})\n`);
  pass(name);
}

async function caseDedupSurvivesRestart() {
  const name = 'dedup: a second emitter instance reads the open signature from DISK';
  const storePath = path.join(tmpRoot, 'restart.json');
  const boxA = stubOutbox();
  await createAlarmEmitter({ storePath, post: boxA.post }).emit(GOOD);
  const boxB = stubOutbox();
  const rebooted = createAlarmEmitter({ storePath, post: boxB.post });
  const again = await rebooted.emit(GOOD);
  assert.strictEqual(again.posted, false, 'a restart must not re-page an already-open condition');
  assert.strictEqual(boxB.posts.length, 0);
  assert.strictEqual(JSON.parse(fs.readFileSync(storePath, 'utf8')).rows.length, 1);
  pass(name);
}

async function caseConditionChangeRePosts() {
  const name = 'a changed condition on the same signature re-posts, still one row';
  const storePath = path.join(tmpRoot, 'changed.json');
  const box = stubOutbox();
  const emitter = createAlarmEmitter({ storePath, post: box.post });
  await emitter.emit(GOOD);
  const changed = await emitter.emit({ ...GOOD, condition: 'the daemon answered, then stopped again' });
  assert.strictEqual(changed.posted, true);
  assert.strictEqual(changed.reason, 'condition-changed');
  assert.strictEqual(box.posts.length, 2);
  assert.strictEqual(JSON.parse(fs.readFileSync(storePath, 'utf8')).rows.length, 1);
  pass(name);
}

async function caseRepeatWindow() {
  const name = 'repeat_every_ms re-posts after the window, never before, on one row';
  const storePath = path.join(tmpRoot, 'repeat.json');
  const box = stubOutbox();
  let ms = Date.parse('2026-08-24T10:00:00.000Z');
  const emitter = createAlarmEmitter({ storePath, post: box.post, now: () => new Date(ms).toISOString() });
  const hourly = { ...GOOD, repeat_every_ms: 3600000 };
  await emitter.emit(hourly);
  ms += 59 * 60 * 1000;
  assert.strictEqual((await emitter.emit(hourly)).posted, false, '59 minutes in: silent');
  ms += 2 * 60 * 1000;
  const repeated = await emitter.emit(hourly);
  assert.strictEqual(repeated.posted, true, '61 minutes in: repeats');
  assert.strictEqual(repeated.reason, 'repeat');
  assert.strictEqual(box.posts.length, 2);
  const rows = JSON.parse(fs.readFileSync(storePath, 'utf8')).rows;
  assert.strictEqual(rows.length, 1, 'the hourly repeat must not mint a second row');
  assert.strictEqual(rows[0].emission_count, 2);
  pass(name);
}

async function caseReadInterfaceMatchesDigest() {
  const name = 'readOpenConditions publishes the digest\'s documented shape; clear drops the row';
  const storePath = path.join(tmpRoot, 'read.json');
  const box = stubOutbox();
  const emitter = createAlarmEmitter({ storePath, post: box.post });
  await emitter.emit(GOOD);
  const [cond] = emitter.readOpenConditions();
  // `chat/system-digest.js` documents exactly these keys on its `readOpenConditions`.
  for (const key of ['signature', 'condition', 'subject', 'first_emitted_at', 'evidence_pointer']) {
    assert.ok(cond[key] !== undefined, `the digest reads \`${key}\``);
  }
  assert.strictEqual(cond.subject, 'ignite-engine', 'the digest renders the bare subject id');
  emitter.clear(cond.signature);
  assert.strictEqual(emitter.readOpenConditions().length, 0, 'a cleared condition leaves the digest');
  assert.strictEqual(box.posts.length, 1, 'clearing is silent — no owner-facing post');
  // A cleared signature is emittable again: the condition genuinely recurred.
  const reopened = await emitter.emit(GOOD);
  assert.strictEqual(reopened.posted, true);
  pass(name);
}

async function caseImmediateMarkAndChannel() {
  const name = 'the immediate mark is recorded; system-health falls back to the system channel';
  const storePath = path.join(tmpRoot, 'immediate.json');
  const box = stubOutbox();
  const emitter = createAlarmEmitter({ storePath, post: box.post, systemChannelId: 'C-system-default' });
  const noChannel = { ...GOOD };
  delete noChannel.channel_id;
  await emitter.emit(noChannel);
  const rows = JSON.parse(fs.readFileSync(storePath, 'utf8')).rows;
  assert.strictEqual(rows[0].immediate, true, 'a system-health alarm carries the digest-exempt mark');
  assert.strictEqual(rows[0].channel_id, 'C-system-default');
  assert.strictEqual(box.posts[0].kind, 'alarm', 'the emitter stamps the outbox kind, never the caller');
  // The four required fields all reach the owner-facing body.
  const body = box.posts[0].payload;
  for (const fragment of [GOOD.condition, GOOD.subject.id, GOOD.evidence_pointer, GOOD.what_would_clear_it]) {
    assert.ok(body.includes(fragment), `the posted body carries: ${fragment}`);
  }
  pass(name);
}

const cases = [
  caseMissingFieldThrows,
  caseEmptyAndTokenFieldsRefused,
  caseDedupOneRowOnePost,
  caseDedupSurvivesRestart,
  caseConditionChangeRePosts,
  caseRepeatWindow,
  caseReadInterfaceMatchesDigest,
  caseImmediateMarkAndChannel,
];

(async () => {
  for (const fn of cases) {
    try { await fn(); } catch (err) { fail(fn.name, err); }
  }
  try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* tmp */ }
  if (failed) {
    process.stdout.write(`${failed} FAIL\n`);
    process.exit(1);
  }
  process.stdout.write('ALL PASS\n');
})();
