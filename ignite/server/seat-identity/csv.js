'use strict';

// Task 7.11 — the minimal header-driven CSV reader the identity gate reads its ground truth with.
//
// WHY HEADER-DRIVEN, AND WHY THIS IS NOT AN ABSTRACTION FOR ITS OWN SAKE. Measured on this box,
// 2026-07-27, on the two runs of the goal this code was written inside:
//
//   run-1  session-id,seat,harness,native-session-id,workdir,recorded,started,ended
//   run-2  seat,session-id,harness,native-session-id,model,workdir,started,ended
//
// The two disagree on column ORDER *and* on the column SET. A positional parse is therefore not
// merely fragile here, it is WRONG TODAY: read run-2 with run-1's offsets and every seat name
// comes back as a session id. The gate that decides who is sitting in a seat cannot be built on
// that, so every access in this module is BY NAME, and a name that is absent is absent — never
// silently the value of whatever sits at that index.
//
// No CSV library: the files are script-written, comma-separated, and this reader handles the one
// piece of real CSV they can contain — a double-quoted field with embedded commas/quotes. Adding
// a dependency to the daemon's startup path to parse eight columns is not a trade worth making.

const fs = require('node:fs');

function splitRow(line) {
  const out = [];
  let field = '';
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"') {
        if (line[i + 1] === '"') { field += '"'; i++; }
        else quoted = false;
      } else field += ch;
    } else if (ch === '"') {
      quoted = true;
    } else if (ch === ',') {
      out.push(field);
      field = '';
    } else {
      field += ch;
    }
  }
  out.push(field);
  return out;
}

function quoteField(value) {
  const s = value === undefined || value === null ? '' : String(value);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

// Read a CSV into { header: [...], rows: [{col: value}] }.
//
// A row with FEWER fields than the header yields empty strings for the tail rather than throwing:
// a truncated final line is what a file being appended to while it is read looks like, and the
// gate's job is to fail closed on a bad row, not to crash the caller reading it. A row with MORE
// fields keeps the overflow out of the named map entirely — it can never masquerade as a column.
function readCsv(filePath) {
  let raw;
  try {
    raw = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    return { exists: false, header: [], rows: [], error: err.code || err.message };
  }
  const lines = raw.split(/\r?\n/).filter((l) => l.length > 0);
  if (lines.length === 0) return { exists: true, header: [], rows: [] };
  const header = splitRow(lines[0]).map((h) => h.trim());
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const fields = splitRow(lines[i]);
    const row = {};
    for (let c = 0; c < header.length; c++) row[header[c]] = fields[c] === undefined ? '' : fields[c];
    row.__line = i + 1;
    rows.push(row);
  }
  return { exists: true, header, rows };
}

// Append a row BY NAME against the file's own header — so a file whose columns are reordered or
// extended later keeps receiving correct rows without this code being edited. A key the header
// does not carry is DROPPED and reported, never appended positionally: silently widening a
// schema from the write side is how the two divergent headers above came to exist.
function appendRow(filePath, values) {
  const { exists, header } = readCsv(filePath);
  if (!exists || header.length === 0) {
    return { appended: false, reason: 'no header — refusing to invent a schema', dropped: Object.keys(values) };
  }
  const dropped = Object.keys(values).filter((k) => !header.includes(k));
  const line = header.map((col) => quoteField(values[col])).join(',');
  fs.appendFileSync(filePath, line + '\n', 'utf8');
  return { appended: true, header, dropped, line };
}

module.exports = { readCsv, appendRow, splitRow, quoteField };
