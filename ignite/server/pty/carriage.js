'use strict';

// Headed prompt carriage — session-surface-spec.md Design 3 (OQ-F RULED, D83).
//
// ★ SCOPE NOTE (surfaced in the dispatch return): the matching STRICT config-load validation for
// `headed.tui.prompt` and the `{prompt}` slot lives in server/spawn/config.js
// (KNOWN_TUI_KEYS = {'argv'}; CLOSED_SLOTS excludes {prompt}) — which is OUTSIDE this task's
// allowlist and runs at daemon boot. So the carriage cannot be DECLARED on a profile in the
// shared config until config.js is extended (a conductor-owed change, per Amendment #6's
// "server-side validation" that collides with the allowlist forbidding config.js). This module
// therefore owns the headed path's OWN carriage validation + composition, independent of
// config.js, so the machinery is complete and reject-by-default is enforced at spawn time now.
//
// Vocabulary (closed): a profile's `headed.tui.prompt` ∈ { 'argv' | 'file' | 'keystroke' }.
//   argv      — the prompt fills a single {prompt} slot in headed.tui.argv (closed substitution;
//               never split, never shell-expanded; position declared by the profile). Covers both
//               the review's argv-last (["claude","{prompt}"]) AND OpenCode's MEASURED flag form
//               (["opencode","--prompt","{prompt}"], M6).
//   file      — the prompt is written to a {prompt_file} slot (reuses the 0600 prompt-file path).
//   keystroke — LAST RESORT: inject as keystrokes after a rendered-screen readiness marker, with a
//               timeout (typed `prompt-injection-timeout` failure on expiry), text + Enter as
//               SEPARATE injections.
//   stdin     — STRUCTURALLY ABSENT: unrepresentable (stdin IS the pty slave; write-then-close =
//               type-then-hang-up). A profile declaring it is a config-LOAD failure, not runtime.

const {
  SpawnError,
  E_HEADED_PROMPT_REJECTED,
  E_HEADED_PROMPT_CARRIAGE,
  E_HEADED_STDIN_CARRIAGE,
} = require('./errors');

const KNOWN_CARRIAGES = new Set(['argv', 'file', 'keystroke']);
const PROMPT_SLOT_RE = /\{prompt\}/g;

function hasPromptSlot(argv) {
  return argv.some((el) => typeof el === 'string' && el.includes('{prompt}'));
}

// Substitute a SINGLE {prompt} slot occurrence with the prompt value. Closed substitution: the
// whole prompt goes into exactly the one element carrying the slot; it is never split into
// multiple argv elements and never shell-expanded (the marked per-profile exception to
// "caller free text never becomes argv", Design 3).
function substitutePromptSlot(argv, prompt) {
  let replaced = 0;
  const out = argv.map((el) => {
    if (typeof el !== 'string' || !el.includes('{prompt}')) return el;
    replaced += 1;
    return el.replace(PROMPT_SLOT_RE, prompt);
  });
  return { out, replaced };
}

// Validate a profile's headed block carriage declaration (independent of config.js). Throws on
// `stdin` (structurally absent) or an unknown carriage value. Returns the carriage value or null.
function validateHeadedCarriage(headedBlock, profileName) {
  const tui = headedBlock && headedBlock.tui;
  const carriage = tui && tui.prompt;
  if (carriage === undefined || carriage === null) return null; // no carriage declared → reject-by-default
  if (carriage === 'stdin') {
    throw new SpawnError(
      E_HEADED_STDIN_CARRIAGE,
      `profile ${profileName}: headed.tui.prompt: stdin is structurally absent (stdin is the pty slave; ` +
      `write-then-close would type-then-hang-up the session) — a config-load failure, not a runtime value`,
      { profile: profileName, carriage },
    );
  }
  if (!KNOWN_CARRIAGES.has(carriage)) {
    throw new SpawnError(
      E_HEADED_PROMPT_CARRIAGE,
      `profile ${profileName}: unknown headed.tui.prompt carriage '${carriage}' (known: argv|file|keystroke)`,
      { profile: profileName, carriage },
    );
  }
  if (carriage === 'argv' && !hasPromptSlot(tui.argv)) {
    throw new SpawnError(
      E_HEADED_PROMPT_CARRIAGE,
      `profile ${profileName}: headed.tui.prompt: argv declared but headed.tui.argv carries no {prompt} slot`,
      { profile: profileName, carriage },
    );
  }
  if (carriage === 'keystroke') {
    const ks = tui.keystroke || {};
    if (typeof ks.readiness !== 'string' || ks.readiness.length === 0 || !Number.isInteger(ks.timeout_ms)) {
      throw new SpawnError(
        E_HEADED_PROMPT_CARRIAGE,
        `profile ${profileName}: keystroke carriage MUST declare a readiness marker (string, matched vs the ` +
        `RENDERED screen) and an integer timeout_ms (expiry → prompt-injection-timeout failure)`,
        { profile: profileName, carriage },
      );
    }
  }
  return carriage;
}

// Compose the headed launch argv + carriage plan for a spawn.
//   headedBlock : profile.headed  (the { tui: { argv, prompt?, keystroke? } } block)
//   prompt      : the caller's free-text prompt (may be null/undefined = none supplied)
//   opts.ensurePromptFile(prompt) -> absolute 0600 file path  (for the `file` carriage)
// Returns { argv, promptFile, carriage, keystrokePlan }.
//   - No prompt supplied → argv is the tui.argv verbatim (no carriage needed), any {prompt} slot
//     left in argv is a config error surfaced here.
//   - Prompt supplied + NO carriage declared → typed REJECTION (Design 3 default, Behavior #9).
function composeHeadedArgv(headedBlock, prompt, profileName, opts = {}) {
  const tui = headedBlock.tui;
  const carriage = validateHeadedCarriage(headedBlock, profileName);
  const promptSupplied = prompt !== undefined && prompt !== null && prompt !== '';

  if (!promptSupplied) {
    // A profile whose argv still carries a {prompt} slot but got no prompt is a mis-declared
    // profile: refuse rather than exec a literal "{prompt}" token.
    if (hasPromptSlot(tui.argv)) {
      throw new SpawnError(
        E_HEADED_PROMPT_CARRIAGE,
        `profile ${profileName}: headed.tui.argv carries a {prompt} slot but no prompt was supplied`,
        { profile: profileName },
      );
    }
    return { argv: tui.argv.slice(), promptFile: null, carriage: null, keystrokePlan: null };
  }

  // Prompt supplied.
  if (!carriage) {
    throw new SpawnError(
      E_HEADED_PROMPT_REJECTED,
      `profile ${profileName}: a prompt was supplied for a headed session but the profile declares NO ` +
      `headed.tui.prompt carriage — rejected by default (spec Design 3, Behavior #9)`,
      { profile: profileName },
    );
  }

  if (carriage === 'argv') {
    const { out, replaced } = substitutePromptSlot(tui.argv, prompt);
    if (replaced !== 1) {
      throw new SpawnError(
        E_HEADED_PROMPT_CARRIAGE,
        `profile ${profileName}: argv carriage expects exactly one {prompt} slot, found ${replaced}`,
        { profile: profileName },
      );
    }
    return { argv: out, promptFile: null, carriage, keystrokePlan: null };
  }

  if (carriage === 'file') {
    if (typeof opts.ensurePromptFile !== 'function') {
      throw new SpawnError(E_HEADED_PROMPT_CARRIAGE, `profile ${profileName}: file carriage needs a prompt-file writer`, { profile: profileName });
    }
    const promptFile = opts.ensurePromptFile(prompt);
    const values = { prompt_file: promptFile };
    const out = tui.argv.map((el) =>
      typeof el === 'string' ? el.replace(/\{prompt_file\}/g, promptFile) : el);
    if (!out.some((el) => el === promptFile || (typeof el === 'string' && el.includes(promptFile)))) {
      throw new SpawnError(
        E_HEADED_PROMPT_CARRIAGE,
        `profile ${profileName}: file carriage declared but headed.tui.argv carries no {prompt_file} slot`,
        { profile: profileName },
      );
    }
    return { argv: out, promptFile, carriage, keystrokePlan: null };
  }

  // keystroke: argv is left untouched; the daemon injects after readiness (post-spawn).
  return {
    argv: tui.argv.slice(),
    promptFile: null,
    carriage,
    keystrokePlan: {
      prompt,
      readiness: tui.keystroke.readiness,
      timeoutMs: tui.keystroke.timeout_ms,
    },
  };
}

module.exports = { composeHeadedArgv, validateHeadedCarriage, KNOWN_CARRIAGES };
