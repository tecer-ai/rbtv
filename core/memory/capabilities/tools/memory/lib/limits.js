'use strict';

const PROFILE_POINTS = 4000;
const LEARNED_MAX = 30;
const DAILY_LINES = 40;
const WEEKLY_LINES = 25;
const WARN_LINES = 100;
const SPLIT_LINES = 300;
const INBOX_WARN = 20;

const normalize = (text) => String(text).replace(/\r\n/g, '\n');
const nonemptyLines = (text) => normalize(text).split('\n').filter((line) => line.trim());

function onDemand(kind) {
  return ['topic', 'entity', 'knowledge', 'workspace', 'archive'].includes(kind);
}

function checkLimits(kind, text) {
  const textPoints = [...String(text)].length;
  const lines = nonemptyLines(text);
  const warnings = [];
  let hard = null;
  if (kind === 'profile' && textPoints > PROFILE_POINTS) {
    hard = { count: textPoints, cap: PROFILE_POINTS, unit: 'characters' };
  } else if (kind === 'learned' && lines.filter((line) => line.startsWith('- ')).length > LEARNED_MAX) {
    hard = { count: lines.filter((line) => line.startsWith('- ')).length, cap: LEARNED_MAX, unit: 'rules' };
  } else if (kind === 'daily' && normalize(text).trimEnd().split('\n').length > DAILY_LINES) {
    hard = { count: normalize(text).trimEnd().split('\n').length, cap: DAILY_LINES, unit: 'lines' };
  } else if (kind === 'weekly' && normalize(text).trimEnd().split('\n').length > WEEKLY_LINES) {
    hard = { count: normalize(text).trimEnd().split('\n').length, cap: WEEKLY_LINES, unit: 'lines' };
  } else if (kind === 'inbox' && lines.filter((line) => line.startsWith('- ')).length > INBOX_WARN) {
    warnings.push(`Memory inbox has ${lines.filter((line) => line.startsWith('- ')).length} bullet lines (over ${INBOX_WARN}); the dreamer needs to file them.`);
  } else if (onDemand(kind) && lines.length >= WARN_LINES) {
    warnings.push(`${kind} has ${lines.length} nonempty lines; warn at ${WARN_LINES}, split at ${SPLIT_LINES}.`);
  }
  return {
    warnings,
    hard,
    split: Boolean(onDemand(kind) && lines.length >= SPLIT_LINES),
    lines: lines.length,
    points: textPoints,
  };
}

function recordLines(text) {
  const records = [];
  let current = null;
  for (const line of normalize(text).split('\n')) {
    if (!line.trim() || line.startsWith('#') || line.startsWith('---') || /^\|/.test(line) || /^(?:description|type|aliases|paths):/.test(line)) {
      if (current) { records.push(current); current = null; }
      continue;
    }
    if (line.startsWith('- ') || line.startsWith('### ') || !current) {
      if (current) records.push(current);
      current = line;
    } else current = `${current}\n${line}`;
  }
  if (current) records.push(current);
  return records;
}

function splitOnDemand(text) {
  const ending = text.includes('\r\n') ? '\r\n' : '\n';
  const rows = recordLines(text);
  if (nonemptyLines(text).length < SPLIT_LINES) return null;
  const huge = rows.find((row) => nonemptyLines(row).length >= SPLIT_LINES);
  if (huge || rows.length < 2) return { flagged: huge || rows[0], parts: null };
  const without = (drop) => {
    let next = text.split(/\r?\n/).filter((line) => !drop.includes(line)).join(ending);
    if (text.endsWith(ending) && !next.endsWith(ending)) next += ending;
    return next;
  };
  const moved = [];
  for (let i = rows.length - 1; i > 0; i--) {
    const trial = [...moved, rows[i]];
    if (nonemptyLines(without(trial)).length >= SPLIT_LINES) {
      moved.push(rows[i]);
      continue;
    }
    moved.push(rows[i]);
    if (nonemptyLines(without(moved)).length < SPLIT_LINES) break;
  }
  if (!moved.length || nonemptyLines(without(moved)).length >= SPLIT_LINES) return { flagged: rows[0], parts: null };
  return { flagged: null, parts: { source: without(moved), moved: moved.slice().reverse(), ending } };
}

module.exports = {
  PROFILE_POINTS, LEARNED_MAX, DAILY_LINES, WEEKLY_LINES, WARN_LINES, SPLIT_LINES, INBOX_WARN,
  nonemptyLines, onDemand, checkLimits, recordLines, splitOnDemand,
};
