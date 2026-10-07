'use strict';

// cast — the defaults of an installation: how `cast route` ranks when a call gives no --optimize,
// and how a launch picks the fallback of a model that fails to start.
//
//   <installation>/.rbtv/config/cast/defaults.json   {"route": "price", "fallback": "quality"}
//
// Both keys are optional. An installation without the file, a key the file does not hold, and a
// folder inside no installation all read cast's own values: route by price, fallback off.
// `cast models defaults` (lib/models.js) shows and changes the file.

const fs = require('fs');
const path = require('path');

const DEFAULTS_REL = path.join('.rbtv', 'config', 'cast', 'defaults.json');
// What each key accepts; the first value is cast's own.
const VALUES = {
  route: ['price', 'quality'],
  fallback: ['off', 'price', 'quality'],
};

class DefaultsError extends Error {}

// The defaults in force for an installation root (null = no installation): `route` and
// `fallback`, `file` (the installation's file, whether or not it exists yet) and `own`, the keys
// that file holds. Throws a DefaultsError naming the file when it cannot be used.
function loadDefaults(root) {
  const file = root ? path.join(root, DEFAULTS_REL) : null;
  let own = {};
  if (file && fs.existsSync(file)) {
    const bad = (why) => new DefaultsError(`cannot read cast's defaults ${file}: ${why}`);
    try { own = JSON.parse(fs.readFileSync(file, 'utf8')); } catch (e) { throw bad(e.message); }
    if (!own || typeof own !== 'object' || Array.isArray(own)) throw bad('it holds no object');
    for (const [key, value] of Object.entries(own)) {
      if (!VALUES[key]) throw bad(`unknown key '${key}' (the keys are ${Object.keys(VALUES).join(', ')})`);
      if (!VALUES[key].includes(value)) throw bad(`${key} is ${JSON.stringify(value)} (one of ${VALUES[key].join(', ')})`);
    }
  }
  return { file, own, route: own.route ?? VALUES.route[0], fallback: own.fallback ?? VALUES.fallback[0] };
}

// Replaces the installation's defaults file in one step, with the keys `own` holds.
function saveDefaults(root, own) {
  const file = path.join(root, DEFAULTS_REL);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, `${JSON.stringify(own, null, 2)}\n`, 'utf8');
    fs.renameSync(temporary, file);
  } catch (e) {
    fs.rmSync(temporary, { force: true });
    throw e;
  }
  return file;
}

module.exports = { DEFAULTS_REL, VALUES, DefaultsError, loadDefaults, saveDefaults };
