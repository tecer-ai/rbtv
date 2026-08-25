'use strict';

// The recognition lists and the match rule [spec-recovery §3]. Run: `node --test`.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const classify = require('./provider-classify');

const SPEC_TRANSIENT_TOKENS = ['quota', 'rate-limit', 'provider-down'];
const SPEC_TRANSIENT_STRINGS = ['429', 'rate_limit', 'overloaded', 'capacity', 'temporarily unavailable'];
const SPEC_CONFIG_TOKENS = ['model-not-found', 'bad slug', 'auth-rejected'];
const SPEC_CONFIG_STRINGS = ['404 model', 'unknown model', 'invalid_api_key', 'unauthorized'];

test('both versioned recognition files exist and carry the spec §3 seed contents VERBATIM', () => {
  const tr = JSON.parse(fs.readFileSync(classify.TRANSIENT_LIST, 'utf8'));
  const cf = JSON.parse(fs.readFileSync(classify.CONFIGURATION_LIST, 'utf8'));
  assert.strictEqual(tr.class, 'transient');
  assert.strictEqual(cf.class, 'configuration');
  assert.deepStrictEqual(tr.class_tokens, SPEC_TRANSIENT_TOKENS);
  assert.deepStrictEqual(tr.common_strings, SPEC_TRANSIENT_STRINGS);
  assert.deepStrictEqual(cf.class_tokens, SPEC_CONFIG_TOKENS);
  assert.deepStrictEqual(cf.common_strings, SPEC_CONFIG_STRINGS);
  // Versioned: a list edit is a config-change re-arm, so the files carry a version to edit.
  assert.strictEqual(typeof tr.version, 'number');
  assert.strictEqual(typeof cf.version, 'number');
});

test('every transient seed classifies TRANSIENT, case-insensitively, as a SUBSTRING', () => {
  for (const seed of [...SPEC_TRANSIENT_TOKENS, ...SPEC_TRANSIENT_STRINGS]) {
    const v = classify.classifyProviderError(`cast: launch refused — ${seed.toUpperCase()} — try later`);
    assert.strictEqual(v.classification, 'transient', `${seed} -> ${v.classification}`);
  }
});

test('every configuration seed classifies CONFIGURATION', () => {
  for (const seed of [...SPEC_CONFIG_TOKENS, ...SPEC_CONFIG_STRINGS]) {
    const v = classify.classifyProviderError(`provider said: ${seed}`);
    assert.strictEqual(v.classification, 'configuration', `${seed} -> ${v.classification}`);
  }
});

test('AMBIGUOUS — text matching BOTH lists classifies CONFIGURATION (fail closed)', () => {
  const v = classify.classifyProviderError('429 rate_limit on an unknown model — quota exceeded');
  assert.strictEqual(v.classification, 'configuration');
  assert.ok(v.also_matched, 'the transient hit is reported as evidence, not swallowed');
  assert.match(v.why, /fail closed/);
});

test('UNRECOGNISED classifies CONFIGURATION — a strike until the list is edited (ST-19 class)', () => {
  const v = classify.classifyProviderError('the harness exited 7 with a message nobody has seen before');
  assert.strictEqual(v.classification, 'configuration');
  assert.strictEqual(v.matched, null);
  assert.match(v.why, /unrecognised/i);
});

test('an empty / absent error text is CONFIGURATION, never a silent no-strike dead end', () => {
  assert.strictEqual(classify.classifyProviderError('').classification, 'configuration');
  assert.strictEqual(classify.classifyProviderError(null).classification, 'configuration');
  assert.strictEqual(classify.classifyProviderError(undefined).classification, 'configuration');
});

test('an unreadable list is a configuration-error, never a silent default', () => {
  assert.throws(
    () => classify.classifyProviderError('quota', { transientList: '/nonexistent/provider-transient.json' }),
    /unreadable/,
  );
});

test('a list EDIT changes the fingerprint (the config-change re-arm detector)', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'prov-lists-'));
  const tr = path.join(dir, 't.json');
  const cf = path.join(dir, 'c.json');
  fs.writeFileSync(tr, JSON.stringify({ class: 'transient', class_tokens: ['quota'], common_strings: [] }));
  fs.writeFileSync(cf, JSON.stringify({ class: 'configuration', class_tokens: ['bad slug'], common_strings: [] }));
  const before = classify.listsFingerprint({ transientList: tr, configurationList: cf });
  fs.writeFileSync(tr, JSON.stringify({ class: 'transient', class_tokens: ['quota', 'throttled'], common_strings: [] }));
  const after = classify.listsFingerprint({ transientList: tr, configurationList: cf });
  assert.notStrictEqual(before, after);
  // And an edit is what makes a previously-unrecognised shape transient.
  assert.strictEqual(
    classify.classifyProviderError('throttled', { transientList: tr, configurationList: cf }).classification,
    'transient',
  );
  fs.rmSync(dir, { recursive: true, force: true });
});
