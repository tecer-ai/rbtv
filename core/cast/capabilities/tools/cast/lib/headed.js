'use strict';

// cast — the sessions a person opened and can open again. Every headed launch gets a two-letter
// code in its row of the handle registry (lib/handles.js), and is on record for as long as the
// registry keeps that row (HANDLE_TTL_MS). `spark resume` shows the list and opens one by its code.
//   newCode()           a code that no row on record holds
//   openedSessions()    the rows that carry a code, newest first
//   sessionOf(row)      the harness session a row opened: {id}, or {problem}
//   sessionRow(row)     a row as the list shows it
//   sessionLines(list)  the list as text: a table, or one labeled block per session when the
//                       terminal is too narrow for the table

const crypto = require('crypto');
const path = require('path');

const { terminalWidth } = require('./agent-list');
const { readHandles } = require('./handles');
const { codexSessions, fmtTime, opencodeCandidates } = require('./sessions');

const LETTERS = 'abcdefghijklmnopqrstuvwxyz';
// The most sessions one list shows.
const MAX_SHOWN = 50;

function openedSessions() {
  const newest = new Map();
  for (const h of readHandles()) if (h.code) newest.set(h.code, h);
  return [...newest.values()].sort((a, b) => b.t0 - a.t0);
}

// Random, so that a code a person noted keeps naming the same session when later ones are opened.
// With every code held, the oldest session on record gives up its own.
function newCode() {
  const opened = openedSessions();
  const held = new Set(opened.map((h) => h.code));
  const free = [];
  for (const a of LETTERS) for (const b of LETTERS) if (!held.has(a + b)) free.push(a + b);
  return free.length ? free[crypto.randomInt(free.length)] : opened[opened.length - 1].code;
}

// claude is started on an id cast chose, so the row holds it. codex and opencode name their
// session themselves, after the start: it is the first one they recorded for the folder from the
// moment of the launch.
// ponytail: two sessions of one of those harnesses started in one folder in the same moment are
// told apart by nothing; binding opencode by a title of its own needs a TUI option it lacks.
function sessionOf(h) {
  if (h.harness === 'claude') return { id: h.session };
  const since = h.t0 - 2000;
  const born = h.harness === 'codex'
    ? codexSessions(h.folder, Infinity, since).map((r) => ({ id: r.id, at: r.started }))
    : opencodeCandidates(h.folder).map((r) => ({ id: r.id, at: r.time_created }));
  const first = born.filter((r) => r.at >= since).sort((a, b) => a.at - b.at)[0];
  return first ? { id: first.id }
    : { problem: `${h.harness} recorded no session in ${h.folder} since ${fmtTime(h.t0)}` };
}

const LABELS = ['Code', 'Agent', 'Harness', 'Model', 'Opened', 'Folder'];

function sessionRow(h) {
  return {
    code: h.code,
    agent: h.agent ? path.basename(h.agent) : null,
    harness: h.harness,
    model: h.model,
    opened: new Date(h.t0).toISOString(),
    folder: h.folder,
  };
}

function sessionLines({ sessions, on_record: onRecord }, width = terminalWidth()) {
  if (!onRecord) return ['Sessions opened: 0', '', 'No session is on record. spark AGENT opens one.'];
  const lines = [`Sessions opened: ${sessions.length} of ${onRecord}, newest first`, ''];
  const table = sessions.map((s) => [s.code, s.agent ?? '-', s.harness, s.model,
    fmtTime(Date.parse(s.opened)), s.folder]);
  const widths = LABELS.map((label, i) => Math.max(label.length, ...table.map((row) => row[i].length)));
  if (widths.reduce((sum, w) => sum + w + 2, -2) > width) {
    table.forEach((row, i) => lines.push(...(i ? [''] : []), ...row.map((cell, j) => `${LABELS[j]}: ${cell}`)));
  } else {
    const line = (row) => row.map((cell, i) => cell.padEnd(widths[i])).join('  ').trimEnd();
    lines.push(line(LABELS), ...table.map(line));
  }
  lines.push('', 'Open one again: spark resume CODE');
  if (sessions.length < onRecord) lines.push(`Show more: spark resume -n N, up to ${MAX_SHOWN}.`);
  return lines;
}

module.exports = { MAX_SHOWN, newCode, openedSessions, sessionOf, sessionRow, sessionLines };
