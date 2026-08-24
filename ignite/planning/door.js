'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { requirePythonCmd } = require('../lib/python-cmd');
const { readLane, laneIsPaused, consoleRunIsLive, DAEMON } = require('../engine/lane-watch');

const PLANNING_DIR = __dirname;
const ARGV_PY = path.join(PLANNING_DIR, 'argv.py');
const PATH_A_PY = path.join(PLANNING_DIR, 'path_a.py');
// `pipeline-seats.json` is NOT the source of truth for these names — it is a cached
// mirror of the workflow manifest `meta/planning/workflows/plan-console/plan-console.csv`
// (`Seat/workflow` column), which is what `materialize-seats.py --workflow plan-console`
// actually writes onto `taskforce.csv`. The two vocabularies MUST be one string set: this
// file compares the json against that column, so any divergence makes `pipelineMinted()`
// permanently false and the door re-mints every cadence, forever. The json is a bare array
// and carries no comment field; `engine/queue-request.js` `planningManifestSeats()` reads
// the manifest, and `engine/probes/probe-queue-request-pass.js` leg M fails on divergence.
const SEATS_FILE = path.join(PLANNING_DIR, 'pipeline-seats.json');
const PLANNING_SEATS = Object.freeze(JSON.parse(fs.readFileSync(SEATS_FILE, 'utf8')));
const ROLE_RE = /^role:[ \t]*planning(?:[ \t].*)?$/m;

function isPlanningGoal(goalFolder) {
  const file = path.join(goalFolder, 'goal.md');
  let raw;
  try { raw = fs.readFileSync(file, 'utf8'); } catch { return false; }
  const fm = raw.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (!fm) return false;
  return ROLE_RE.test(fm[1]);
}

function pipelineMinted(rows) {
  const seats = new Set((rows || []).map((r) => String((r && r.seat) || '').trim()));
  return PLANNING_SEATS.every((s) => seats.has(s));
}

function taskforceRows(goalFolder) {
  const file = path.join(goalFolder, 'taskforce.csv');
  if (!fs.existsSync(file)) return [];
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return null; }
  const lines = text.split(/\r?\n/).filter((l) => l.trim());
  if (!lines.length) return [];
  const header = lines[0].split(',');
  const si = header.indexOf('seat');
  if (si < 0) return null;
  return lines.slice(1).map((line) => {
    const cells = line.split(',');
    return { seat: (cells[si] || '').trim() };
  });
}

function planningMintArgv({ goalFolder, catalogRoot, sheet }) {
  const raw = execFileSync(requirePythonCmd(),
    [ARGV_PY, '--package', goalFolder, '--catalog-root', catalogRoot, '--sheet', sheet],
    { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] });
  return JSON.parse(raw);
}

function runPathA({ goalFolder, catalogRoot, sheet, subject }) {
  const raw = execFileSync(requirePythonCmd(),
    [PATH_A_PY, '--package', goalFolder, '--catalog-root', catalogRoot, '--sheet', sheet,
      '--subject', subject],
    { encoding: 'utf8', timeout: 120000, stdio: ['ignore', 'pipe', 'pipe'] });
  return JSON.parse(raw);
}

function runPlanningMintPass({ goalsRoot, resolveCatalog, logger = null, mint = null }) {
  const say = (level, message, extra = {}) => { if (logger) logger({ level, message, ...extra }); };
  const seeded = [];
  const skipped = [];

  let entries;
  try {
    entries = fs.readdirSync(goalsRoot, { withFileTypes: true });
  } catch {
    return { seeded, skipped };
  }

  let catalog;
  try {
    catalog = resolveCatalog(goalsRoot);
  } catch (err) {
    skipped.push({ reason: err.code || 'catalog-unresolvable', error: err.message });
    say('debug', 'planning-mint pass: no component catalog on this workspace — nothing minted',
      { code: err.code, error: err.message });
    return { seeded, skipped };
  }

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const goal = entry.name;
    const goalFolder = path.join(goalsRoot, goal);

    if (laneIsPaused(goalFolder)) { skipped.push({ goal, reason: 'goal-paused' }); continue; }
    if (readLane(goalFolder).lane !== DAEMON) {
      skipped.push({ goal, reason: 'not-assigned-to-the-daemon' });
      continue;
    }
    if (consoleRunIsLive(goalFolder)) {
      skipped.push({ goal, reason: 'console-run-live' });
      say('info', 'planning-mint pass: a console run is LIVE on this goal — not minting', { goal });
      continue;
    }
    if (!isPlanningGoal(goalFolder)) {
      skipped.push({ goal, reason: 'not-planning-goal' });
      continue;
    }

    const rows = taskforceRows(goalFolder);
    if (rows === null) {
      skipped.push({ goal, reason: 'taskforce-unreadable' });
      say('warn', 'planning-mint pass: taskforce.csv is unreadable — nothing minted', { goal });
      continue;
    }
    if (pipelineMinted(rows)) {
      skipped.push({ goal, reason: 'already-minted' });
      say('debug', 'planning-mint pass: pipeline seats already minted — quiet no-op', { goal });
      continue;
    }

    try {
      if (mint) {
        mint({ goalFolder, catalogRoot: catalog.catalogRoot, sheet: catalog.sheet, seats: PLANNING_SEATS });
      } else {
        const out = runPathA({
          goalFolder, catalogRoot: catalog.catalogRoot, sheet: catalog.sheet, subject: goal,
        });
        if (!out.ok) {
          skipped.push({ goal, reason: 'materialize-refused', record: out.record });
          say('warn', 'planning-mint pass: supervised mint refused — nothing written', {
            goal, record: out.record,
          });
          continue;
        }
      }
    } catch (err) {
      skipped.push({ goal, reason: 'materialize-refused', error: err.message });
      say('warn', 'planning-mint pass: supervised mint refused — nothing written', {
        goal, error: err.message,
      });
      continue;
    }

    seeded.push({ goal, seats: PLANNING_SEATS.slice() });
    say('info', 'planning-mint pass: minted the planning-seat chain on this goal', { goal });
  }

  return { seeded, skipped };
}

module.exports = {
  PLANNING_SEATS, ARGV_PY, PATH_A_PY,
  isPlanningGoal, pipelineMinted, planningMintArgv, runPlanningMintPass,
};
