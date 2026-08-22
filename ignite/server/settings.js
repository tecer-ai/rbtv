'use strict';

// settings — the ONE home in code of the `.rbtv/modules/ignite/settings.json` schema and of the
// `settings-history.jsonl` line format (task 7.66; schema record: `architecture/CMP-1-rbtv-runtime-root.md`
// § Ticker settings schema).
//
// D27 created both files with no reader and no writer. This module is the read half and the write
// half, shared by the two consumers so the schema has one home rather than two copies (`PRIN-11`):
//
//   * the DAEMON, at boot — `server/index.js` overlays this machine's block onto the merged config
//     and refuses to start on an out-of-bound value.
//   * the OPERATOR SURFACE — `ignite/capabilities/ticker-settings/tool/rbtv-ignite-ticker`, which
//     writes the value and appends the history line. It runs with NO daemon, by design.
//
// ── The history-line format is ADOPTED, not invented ──────────────────────────────────────────
// The task brief said nothing writes these files. That was true when it was written and FALSE by
// the time this was built: the installer capability (`core/capabilities/installer/tool/rbtv-install`
// — DELETED 2026-08-22, content in git history; the lines it already wrote are still on disk and
// this reasoning stands, VPS-local install 2026-07-27 19:58) already appends history lines and seeds
// `settings.json` as `{"machines": {}}`. This module is therefore the SECOND writer into one
// append-only stream, so it takes the live writer's six keys verbatim — {ts, machine, key, from,
// to, by} — which are exactly CMP-1's named field set. Coining different names would put two
// formats in one file and break every reader of it.
//
// ⚠ THE FIELD SET IS ADOPTED; THE WRITE SEMANTICS ARE DELIBERATELY NOT (leader ruling, #522).
// All three existing lines read `from: null -> to: 1` for the SAME key: the installer hardcodes
// `"from": None` (`rbtv-install:161`) and never reads prior state, so it records a transition that
// did not happen. A `from` that is always null cannot reconstruct a single transition, which is the
// whole purpose of carrying it — and the two files disagree, since `settings.json` contains none of
// what those lines claim was set. This module computes `from` by READING the stored value. So:
// EVERY LINE IN THIS FILE WRITTEN BEFORE 7.66 HAS AN UNRELIABLE `from`; lines written by this
// module do not. Filed against the installer as an issue, NOT fixed here — it is 7.64's code.
//
// ── Two seeds exist in the wild, and both must read ───────────────────────────────────────────
// The daemon seeds `{}` (`server/index.js`); the installer seeds `{"machines": {}}`. Whichever ran
// first on a box is what is there. `readSettings` tolerates both, an absent `machines` key, and an
// absent file — measured on the live VPS, where the daemon won and the file is `{}`.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// ── Schema ────────────────────────────────────────────────────────────────────────────────────
//
// Shape: `machines.<hostname>.<block>.<key>` (CMP-1, following DEC-7 sub-ruling 3's reasoning for
// `server.json`: `.rbtv/modules/ignite/` is git-COMMITTED and travels to every machine, so one flat
// value would be right on the VPS and wrong on the PC).
//
// Every value below is a DEFAULT carried by a NAMED CONFIG VARIABLE, never a constant — the owner
// approved the three numbers on 2026-07-26 explicitly as adjustable defaults
// (`system-definition/decisions.md#d-operator-surface-apply`). The floor and the ceiling are
// themselves settable in the same block, which is what makes them defaults rather than limits.

const DEFAULTS = {
  ticker: {
    tick_interval_ms: 10000,          // the ratified cadence (ticker.js DEFAULT_CONFIG)
    tick_interval_floor_ms: 5000,     // owner-approved default, 2026-07-26
    tick_interval_ceiling_ms: 60000,  // owner-approved default, 2026-07-26
  },
  jobs: {
    // WALL-CLOCK and deliberately independent of the cadence, so a tick edit can never move it
    // (design § 2.5). Not consumed by this task's surface; declared here because the block is part
    // of the schema this task settles and a reader must know the key exists.
    periodic_min_interval_seconds: 60,
  },
};

// A block this daemon does not know is IGNORED — other consumers will add blocks, and a file
// travelling by git must not refuse to boot a machine that predates them. A key this daemon does
// not know INSIDE a known block is REFUSED at boot: a typo'd `tick_interval` that silently leaves
// the box at the default, while the operator believes they changed it, is the silent-no-op failure
// this runtime keeps paying for. Refusing names it at the one moment someone is watching.
const KNOWN_BLOCKS = Object.keys(DEFAULTS);

function settingsPaths(workspaceRoot) {
  const moduleDir = path.join(workspaceRoot, '.rbtv', 'modules', 'ignite');
  return {
    moduleDir,
    settingsPath: path.join(moduleDir, 'settings.json'),
    historyPath: path.join(moduleDir, 'settings-history.jsonl'),
  };
}

function thisMachine() {
  return os.hostname();
}

// ── Read ──────────────────────────────────────────────────────────────────────────────────────

// The whole file. A missing file is `{machines:{}}`, never an error: the daemon creates it at
// first run and the operator surface must work before that has ever happened.
function readSettings(workspaceRoot) {
  const { settingsPath } = settingsPaths(workspaceRoot);
  let raw;
  try {
    raw = fs.readFileSync(settingsPath, 'utf8');
  } catch (err) {
    if (err.code === 'ENOENT') return { machines: {} };
    throw new Error(`cannot read ${settingsPath}: ${err.message}`);
  }
  if (raw.trim() === '') return { machines: {} };
  let data;
  try {
    data = JSON.parse(raw);
  } catch (err) {
    // Fail LOUD. A corrupt settings file silently treated as empty would run the box at defaults
    // while the file on disk says otherwise — the same class as the typo above, one layer up.
    throw new Error(`${settingsPath} is not valid JSON: ${err.message}`);
  }
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error(`${settingsPath} must be a JSON object, got ${Array.isArray(data) ? 'array' : typeof data}`);
  }
  if (!data.machines || typeof data.machines !== 'object' || Array.isArray(data.machines)) {
    // Both live seeds land here: the daemon's `{}` and any file whose `machines` was never written.
    return { ...data, machines: {} };
  }
  return data;
}

// This machine's block for one namespace, defaults folded in. Another machine's entry is never
// consulted and never validated here — it is validated on its own box, which bounds the blast
// radius of a value that is wrong somewhere else.
function effectiveBlock(workspaceRoot, block, machine = thisMachine()) {
  const settings = readSettings(workspaceRoot);
  const stored = (settings.machines[machine] || {})[block] || {};
  return { ...DEFAULTS[block], ...stored };
}

// ── Validation ────────────────────────────────────────────────────────────────────────────────
//
// Enforced TWICE, fail-closed both times (CMP-1; design § 2.4): here, called by the operator
// surface BEFORE anything is written, and again by the daemon at boot so a value hand-edited into
// the file past the surface cannot run. A surface-only bound is not a bound.
//
// Returns an array of human-readable problems; empty means valid. Never throws on bad DATA — the
// caller decides whether a problem is a refusal or a boot failure, and both need the full list.
function validateTicker(effective) {
  const problems = [];
  const num = (k) => {
    const v = effective[k];
    if (typeof v !== 'number' || !Number.isFinite(v) || !Number.isInteger(v)) {
      problems.push(`ticker.${k} must be an integer number of milliseconds, got ${JSON.stringify(v)}`);
      return null;
    }
    if (v <= 0) { problems.push(`ticker.${k} must be > 0, got ${v}`); return null; }
    return v;
  };
  const floor = num('tick_interval_floor_ms');
  const ceiling = num('tick_interval_ceiling_ms');
  const tick = num('tick_interval_ms');
  // The bounds are configurable, so they can themselves be set incoherently. A floor above its
  // ceiling admits no value at all, and would otherwise surface as a confusing refusal of every
  // cadence rather than as the real error.
  if (floor !== null && ceiling !== null && floor > ceiling) {
    problems.push(`ticker.tick_interval_floor_ms (${floor}) is above ticker.tick_interval_ceiling_ms (${ceiling}) — no cadence could satisfy both`);
  }
  if (tick !== null && floor !== null && tick < floor) {
    problems.push(`ticker.tick_interval_ms (${tick}) is below the floor ticker.tick_interval_floor_ms (${floor})`);
  }
  if (tick !== null && ceiling !== null && tick > ceiling) {
    problems.push(`ticker.tick_interval_ms (${tick}) is above the ceiling ticker.tick_interval_ceiling_ms (${ceiling})`);
  }
  return problems;
}

function validateJobs(effective) {
  const v = effective.periodic_min_interval_seconds;
  if (typeof v !== 'number' || !Number.isInteger(v) || v <= 0) {
    return [`jobs.periodic_min_interval_seconds must be an integer number of seconds > 0, got ${JSON.stringify(v)}`];
  }
  return [];
}

const VALIDATORS = { ticker: validateTicker, jobs: validateJobs };

// Validate THIS machine's whole stored block set. Called at daemon boot; the daemon refuses to
// start on any problem, naming it (the `RBTV_IGNITE_LOG_RETENTION_DAYS` idiom — retention.js).
function validateMachine(workspaceRoot, machine = thisMachine()) {
  const settings = readSettings(workspaceRoot);
  const stored = settings.machines[machine] || {};
  const problems = [];
  for (const block of Object.keys(stored)) {
    if (!KNOWN_BLOCKS.includes(block)) continue; // unknown BLOCK: ignored, see KNOWN_BLOCKS
    const blockData = stored[block];
    if (!blockData || typeof blockData !== 'object' || Array.isArray(blockData)) {
      problems.push(`machines.${machine}.${block} must be a JSON object`);
      continue;
    }
    for (const key of Object.keys(blockData)) {
      if (!(key in DEFAULTS[block])) {
        problems.push(
          `machines.${machine}.${block}.${key} is not a known setting — known keys in \`${block}\`: ` +
          `${Object.keys(DEFAULTS[block]).join(', ')}. A misspelled key would silently leave this ` +
          `machine at the default while the file says otherwise, so it is refused here instead.`
        );
      }
    }
    problems.push(...VALIDATORS[block]({ ...DEFAULTS[block], ...blockData }));
  }
  return problems;
}

// ── Write ─────────────────────────────────────────────────────────────────────────────────────

// Append-only, NEVER rewritten (CMP-1). Six keys, taken from the live writer — see the header.
// `key` is the path WITHIN the machine block (`ticker.tick_interval_ms`), because `machine` is
// already its own field: repeating the hostname inside the key would be the duplication `PRIN-11`
// forbids, and it keeps one grep comparable across machines.
function appendHistory(workspaceRoot, { key, from, to, by, machine = thisMachine(), ts = new Date().toISOString() }) {
  const { historyPath, moduleDir } = settingsPaths(workspaceRoot);
  fs.mkdirSync(moduleDir, { recursive: true });
  const line = JSON.stringify({ ts, machine, key, from, to, by });
  fs.appendFileSync(historyPath, `${line}\n`, 'utf8');
  return line;
}

// Set one key in this machine's block and record it. The history append and the settings write are
// ONE act as far as the caller is concerned: a change that skips the append is a defect even when
// the write is correct (CMP-1), so the history line goes down FIRST — if the process dies between
// the two, the audit trail over-reports rather than losing a change that happened.
//
// The settings write is atomic (temp + rename) so a crash mid-write cannot leave the file
// unparseable, which `readSettings` would then refuse to boot on.
function setValue(workspaceRoot, { block, key, value, by, machine = thisMachine() }) {
  if (!KNOWN_BLOCKS.includes(block)) throw new Error(`unknown settings block: ${block}`);
  if (!(key in DEFAULTS[block])) throw new Error(`unknown setting: ${block}.${key}`);

  const settings = readSettings(workspaceRoot);
  const machines = { ...settings.machines };
  const machineData = { ...(machines[machine] || {}) };
  const blockData = { ...(machineData[block] || {}) };

  // `from` is the STORED value, `null` when nothing was stored — never the effective default.
  // The distinction is the point of the audit trail: "was at the default, now explicitly 15s" and
  // "was explicitly 10s, now 15s" are different events.
  const from = key in blockData ? blockData[key] : null;
  if (from === value) return { changed: false, from, to: value };

  blockData[key] = value;
  machineData[block] = blockData;
  machines[machine] = machineData;
  const next = { ...settings, machines };

  appendHistory(workspaceRoot, { key: `${block}.${key}`, from, to: value, by, machine });

  const { settingsPath, moduleDir } = settingsPaths(workspaceRoot);
  fs.mkdirSync(moduleDir, { recursive: true });
  const tmp = `${settingsPath}.tmp-${process.pid}`;
  fs.writeFileSync(tmp, `${JSON.stringify(next, null, 2)}\n`, 'utf8');
  fs.renameSync(tmp, settingsPath);

  return { changed: true, from, to: value };
}

// ── Duration parsing ──────────────────────────────────────────────────────────────────────────
//
// A UNIT IS REQUIRED. A bare `15` could mean 15 ms or 15 s — a 1000x difference in what the box
// does — and the design's own syntax is `set-interval 15s`. Guessing either way would produce a
// cadence the operator did not ask for, silently, which is the whole failure class the wall-clock
// ruling (design § 2.6) exists to close.
function parseDurationMs(text) {
  const m = /^(\d+)(ms|s)$/.exec(String(text).trim());
  if (!m) {
    throw new Error(
      `cannot read "${text}" as a duration: write an integer with a unit — e.g. 15s or 15000ms. ` +
      `A bare number is refused because 15 could mean 15ms or 15s.`
    );
  }
  const n = Number(m[1]);
  return m[2] === 's' ? n * 1000 : n;
}

function formatMs(ms) {
  return ms % 1000 === 0 ? `${ms / 1000}s` : `${ms}ms`;
}

module.exports = {
  DEFAULTS,
  KNOWN_BLOCKS,
  settingsPaths,
  thisMachine,
  readSettings,
  effectiveBlock,
  validateTicker,
  validateJobs,
  validateMachine,
  appendHistory,
  setValue,
  parseDurationMs,
  formatMs,
};
