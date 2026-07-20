'use strict';

// Headed prompt carriage — session-surface-spec.md Design 3 (OQ-F RULED, D83; NARROWED by the
// batch-08 item 4 half A owner ruling, 2026-07-20). This module owns the headed path's OWN
// carriage validation + composition (the SPAWN gate); the matching config-LOAD gate lives in
// server/spawn/config.js (KNOWN_HEADED_CARRIAGES) and the QUEUE gate in heart-store.js — the
// three MUST agree on the vocabulary.
//
// Vocabulary (closed): a profile's `headed.tui.prompt` ∈ { 'file' | 'keystroke' }.
//   file      — the prompt is written to a {prompt_file} slot (reuses the 0600 prompt-file path).
//   keystroke — LAST RESORT: inject as keystrokes after a rendered-screen readiness marker, with a
//               timeout (typed `prompt-injection-timeout` failure on expiry), text + Enter as
//               SEPARATE injections.
//   argv      — REMOVED (batch-08 item 4 half A): the {prompt}-slot substitution path is retired
//               so caller free text NEVER becomes argv, with no exception. The capability an
//               initial prompt needs is carried by `keystroke` instead (not yet exercised).
//   stdin     — STRUCTURALLY ABSENT: unrepresentable (stdin IS the pty slave; write-then-close =
//               type-then-hang-up). A profile declaring it is a config-LOAD failure, not runtime.

const {
  SpawnError,
  E_HEADED_PROMPT_REJECTED,
  E_HEADED_PROMPT_CARRIAGE,
  E_HEADED_STDIN_CARRIAGE,
} = require('./errors');

const KNOWN_CARRIAGES = new Set(['file', 'keystroke']);

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
      `profile ${profileName}: unknown headed.tui.prompt carriage '${carriage}' (known: file|keystroke; ` +
      `argv REMOVED, batch-08 item 4 — caller free text never becomes argv)`,
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
//   - No prompt supplied → argv is the tui.argv verbatim (no carriage needed).
//   - Prompt supplied + NO carriage declared → typed REJECTION (Design 3 default, Behavior #9).
function composeHeadedArgv(headedBlock, prompt, profileName, opts = {}) {
  const tui = headedBlock.tui;
  const carriage = validateHeadedCarriage(headedBlock, profileName);
  const promptSupplied = prompt !== undefined && prompt !== null && prompt !== '';

  if (!promptSupplied) {
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
