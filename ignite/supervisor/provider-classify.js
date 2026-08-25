'use strict';

// -- PROVIDER RECOGNITION: transient vs configuration [spec-recovery §3, T1-R13, T1-R17, C-10] --
//
// WHAT WAS BROKEN. Provider errors were not classified at all, so ONE error text drove TWO wrong
// behaviours at once (inventory ST-19 / ST-10). A transient quota outage struck the seat's counter
// and burned it toward a dead end for something no seat did; a plan-declared BAD SLUG rerouted
// silently, so the pin the plan wrote was replaced by a model nobody asked for and the mistake was
// never surfaced. The two need OPPOSITE handling, and nothing here could tell them apart.
//
// THE SPLIT, and it is DATA, not code. Two versioned JSON files beside this one carry the lists
// spec-recovery §3 seeds. They are edited by an owner without touching code; an edit is a
// config-change re-arm [spec-recovery §5], which is why `listsFingerprint()` exists.
//
// THE MATCH RULE, spelled once [spec-recovery §3]:
//   * case-insensitive SUBSTRING against the provider/cast error text (and against the class
//     tokens named on the lists themselves, which is why tokens and strings are one search);
//   * first list that hits wins;
//   * both could hit -> CONFIGURATION. FAIL CLOSED: a strike an owner can see beats a silent
//     reroute that hides a pin;
//   * UNRECOGNISED -> CONFIGURATION, for the same reason. An unknown shape is a strike until the
//     list is edited - never a no-strike dead end. That is the ST-19 class, mechanically closed.
//
// ⚠ THIS FILE DECIDES NOTHING BUT THE WORD. What each class DOES - reroute, backoff, strike -
// is `provider-lanes.js`. A recognition-list edit must never have to reach into behaviour, and
// behaviour must never have to grow a second opinion about what an error text means.

const fs = require('node:fs');
const path = require('node:path');

const TRANSIENT = 'transient';
const CONFIGURATION = 'configuration';
const CLASSES = Object.freeze([TRANSIENT, CONFIGURATION]);

const TRANSIENT_LIST = path.join(__dirname, 'provider-transient.json');
const CONFIGURATION_LIST = path.join(__dirname, 'provider-configuration.json');

class ProviderListError extends Error {
  constructor(message) {
    super(message);
    this.name = 'ProviderListError';
    this.code = 'E_PROVIDER_LIST';
  }
}

// A list is REQUIRED. An absent or malformed recognition list is a configuration-error the same
// way an absent recovery config is: the daemon must not classify off numbers - or words - nobody
// can see. It does NOT silently degrade to "everything is configuration", because that reading
// would strike every lane in a real provider outage.
function readList(file) {
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    throw new ProviderListError(`provider recognition list is unreadable at ${file}: ${err.code || err.message}`);
  }
  const tokens = parsed && parsed.class_tokens;
  const strings = parsed && parsed.common_strings;
  if (!Array.isArray(tokens) || !Array.isArray(strings)) {
    throw new ProviderListError(`provider recognition list at ${file} needs array \`class_tokens\` and \`common_strings\``);
  }
  // Tokens and strings are ONE search set on purpose: spec-recovery §3 matches the error text
  // against both, and a caller that classified a bare class token (`quota`) would otherwise miss.
  const needles = [...tokens, ...strings]
    .map((s) => String(s).trim().toLowerCase())
    .filter(Boolean);
  return { file, class: parsed.class, version: parsed.version, needles };
}

function hitIn(list, haystack) {
  for (const needle of list.needles) {
    if (haystack.includes(needle)) return needle;
  }
  return null;
}

// -- THE ONE CLASSIFIER -------------------------------------------------------------------------
//
// Returns the word plus the EVIDENCE for it: which list, which needle. A classification an
// operator cannot audit is a classification they will not trust the second time it strikes a lane.
function classifyProviderError(errorText, { transientList, configurationList } = {}) {
  const text = String(errorText === null || errorText === undefined ? '' : errorText).toLowerCase();
  const transient = readList(transientList || TRANSIENT_LIST);
  const configuration = readList(configurationList || CONFIGURATION_LIST);

  const cfgHit = hitIn(configuration, text);
  const trHit = hitIn(transient, text);

  if (cfgHit && trHit) {
    return {
      classification: CONFIGURATION,
      matched: cfgHit,
      also_matched: trHit,
      list: configuration.file,
      why: 'both lists hit — CONFIGURATION wins, fail closed [spec-recovery §3]',
    };
  }
  if (cfgHit) {
    return {
      classification: CONFIGURATION, matched: cfgHit, list: configuration.file, why: 'configuration list hit',
    };
  }
  if (trHit) {
    return {
      classification: TRANSIENT, matched: trHit, list: transient.file, why: 'transient list hit',
    };
  }
  return {
    classification: CONFIGURATION,
    matched: null,
    list: null,
    why: 'unrecognised shape — CONFIGURATION = strike until the list is edited [spec-recovery §3]',
  };
}

// -- THE EDIT DETECTOR --------------------------------------------------------------------------
//
// A recognition-list edit IS a named re-arm event (`config-change`) [spec-recovery §5], so the
// boot / config-change path needs a value it can compare across passes. Content-derived rather
// than mtime-derived: a re-checkout that rewrites the file unchanged must not re-arm every driver.
function listsFingerprint({ transientList, configurationList } = {}) {
  const { createHash } = require('node:crypto');
  const h = createHash('sha256');
  for (const file of [transientList || TRANSIENT_LIST, configurationList || CONFIGURATION_LIST]) {
    h.update(fs.readFileSync(file));
  }
  return h.digest('hex');
}

module.exports = {
  TRANSIENT,
  CONFIGURATION,
  CLASSES,
  TRANSIENT_LIST,
  CONFIGURATION_LIST,
  ProviderListError,
  readList,
  classifyProviderError,
  listsFingerprint,
};
