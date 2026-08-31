'use strict';

// Proves the owner-correction payload end to end: `writeRetryCorrection` writes it, and
// `launch.py#boot_prompt` (proved separately, in `coord_selftest.py`, since that composer is
// Python) reads it back from the SAME path this file asserts. This suite owns the JS half of the
// contract: the write, the empty-comments no-op, and the exact path the Python reader depends on.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { writeRetryCorrection, CORRECTION_PAYLOAD_DIR } = require('./retry-correction');

function fixtureGoal() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'rbtv-retry-correction-'));
}

function payloadPath(goalFolder, seat) {
  return path.join(goalFolder, 'coordination', CORRECTION_PAYLOAD_DIR, `${seat}.md`);
}

test('owner text is written to the seat-scoped correction payload, marked as an owner correction', () => {
  const goalFolder = fixtureGoal();
  const out = writeRetryCorrection({
    goalFolder, seat: 'terminal-a', comments: 'use the staging bucket, not prod',
  });
  assert.strictEqual(out.ok, true);
  assert.strictEqual(out.written, true);
  const target = payloadPath(goalFolder, 'terminal-a');
  assert.strictEqual(out.path, target);
  const body = fs.readFileSync(target, 'utf8');
  assert.match(body, /OWNER CORRECTION/);
  assert.match(body, /use the staging bucket, not prod/);
});

test('empty comments is a clean no-op - nothing is written', () => {
  const goalFolder = fixtureGoal();
  const out = writeRetryCorrection({ goalFolder, seat: 'terminal-a', comments: '' });
  assert.strictEqual(out.ok, true);
  assert.strictEqual(out.written, false);
  assert.strictEqual(fs.existsSync(path.join(goalFolder, 'coordination')), false);
});

test('absent comments (undefined) is the same clean no-op', () => {
  const goalFolder = fixtureGoal();
  const out = writeRetryCorrection({ goalFolder, seat: 'terminal-a' });
  assert.strictEqual(out.ok, true);
  assert.strictEqual(out.written, false);
});

test('whitespace-only comments is the same clean no-op', () => {
  const goalFolder = fixtureGoal();
  const out = writeRetryCorrection({ goalFolder, seat: 'terminal-a', comments: '   \n  ' });
  assert.strictEqual(out.ok, true);
  assert.strictEqual(out.written, false);
});

test('a second correction overwrites the first - the boot prompt reads only the latest', () => {
  const goalFolder = fixtureGoal();
  writeRetryCorrection({ goalFolder, seat: 'terminal-a', comments: 'first correction' });
  writeRetryCorrection({ goalFolder, seat: 'terminal-a', comments: 'second correction' });
  const body = fs.readFileSync(payloadPath(goalFolder, 'terminal-a'), 'utf8');
  assert.doesNotMatch(body, /first correction/);
  assert.match(body, /second correction/);
});

test('refuses a seat name that is not a safe filename, before touching disk', () => {
  const goalFolder = fixtureGoal();
  const out = writeRetryCorrection({
    goalFolder, seat: '../../etc/passwd', comments: 'malicious',
  });
  assert.strictEqual(out.ok, false);
  assert.strictEqual(out.written, false);
  assert.strictEqual(fs.existsSync(path.join(goalFolder, 'coordination')), false);
});

test('two different seats get two independent payload files', () => {
  const goalFolder = fixtureGoal();
  writeRetryCorrection({ goalFolder, seat: 'terminal-a', comments: 'for a' });
  writeRetryCorrection({ goalFolder, seat: 'terminal-b', comments: 'for b' });
  assert.match(fs.readFileSync(payloadPath(goalFolder, 'terminal-a'), 'utf8'), /for a/);
  assert.match(fs.readFileSync(payloadPath(goalFolder, 'terminal-b'), 'utf8'), /for b/);
});
