'use strict';

// Minimal, dependency-free argv helpers. Every command builds its request by
// pulling flags/positionals out of its own argv slice with these — no argv
// parsing framework, matching the rest of this module's zero-npm-dependency
// convention (no package.json exists here; see ignite/dependencies.txt).

const { CliUsageError } = require('./errors');

// Pulls `--flag value` out of argv (mutates argv), returns the value or
// `fallback` when the flag is absent.
function takeValue(argv, flag, fallback = undefined) {
  const i = argv.indexOf(flag);
  if (i === -1) return fallback;
  const value = argv[i + 1];
  if (value === undefined || value.startsWith('--')) {
    throw new CliUsageError(`${flag} requires a value`);
  }
  argv.splice(i, 2);
  return value;
}

// Pulls a boolean `--flag` out of argv (mutates argv).
function takeFlag(argv, flag) {
  const i = argv.indexOf(flag);
  if (i === -1) return false;
  argv.splice(i, 1);
  return true;
}

// Pulls every occurrence of a repeatable `--flag value` out of argv, in order.
function takeRepeated(argv, flag) {
  const out = [];
  let i;
  while ((i = argv.indexOf(flag)) !== -1) {
    const value = argv[i + 1];
    if (value === undefined || value.startsWith('--')) {
      throw new CliUsageError(`${flag} requires a value`);
    }
    out.push(value);
    argv.splice(i, 2);
  }
  return out;
}

// Pulls the first remaining non-flag token out of argv as a required
// positional (mutates argv). `label` names it in the error.
function requirePositional(argv, label) {
  const idx = argv.findIndex((a) => !a.startsWith('--'));
  if (idx === -1) throw new CliUsageError(`missing required argument: ${label}`);
  const [value] = argv.splice(idx, 1);
  return value;
}

module.exports = { takeValue, takeFlag, takeRepeated, requirePositional };
