'use strict';

// cast — the ONE lazy-load seam for lib/ modules that are allowed to fail without taking `cast`
// itself down. Everything else in lib/ (core.js, handles.js, api.js, route.js, sessions.js,
// help.js, launch.js) is required eagerly and its failure IS the outage — it implements argv
// parsing/dispatch itself, so there is no fallback to degrade to.
//
// Each name below serves one narrow slice: monitor.js -> the `monitor` verb only; provider-limit
// -> usage-limit detection inside a launch/monitor sweep, never the launch itself. A module that
// throws at require-time (a broken top-level, e.g. an undefined name) previously killed every
// `cast` invocation, because Node evicts a module that throws mid-load from its cache and every
// eager caller re-threw the same error (measured 2026-08-31, twice: lib/monitor.js then
// lib/provider-limit.js). Route a module through loadOptional() instead of a bare require to
// close that class for it.
const OPTIONAL_MODULES = ['monitor', 'provider-limit'];

const path = require('path');
const LIB_DIR = __dirname;
const cache = {};

function loadOptional(name) {
  if (name in cache) return cache[name];
  let mod = null;
  let error = null;
  try {
    mod = require(path.join(LIB_DIR, name + '.js'));
  } catch (err) {
    error = err;
    process.stderr.write(`cast: degraded — lib/${name}.js failed to load (${err.message})\n`);
  }
  return (cache[name] = { module: mod, error });
}

module.exports = { OPTIONAL_MODULES, loadOptional };
