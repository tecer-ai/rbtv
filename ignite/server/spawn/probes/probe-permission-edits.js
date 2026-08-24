#!/usr/bin/env node
'use strict';

// ── THE THREE SPELLINGS OF "WHO MAY EDIT PERMISSIONS" AGREE (closeout task 07, 2026-08-15) ────
//
// ⚠ THIS PROBE WAS CLAIMED BY NAME FOR A DAY AND DID NOT EXIST. `coord.py#is_permission_editor`
// and `spawn.js#PERMISSION_EDITOR_SEAT` both carried comments saying it asserted they agree; the
// enumerator (`deploy/probe-suite.js --list`) listed nothing of the sort, so the two independent
// spellings — one Python, one JS — had NOTHING holding them together while the code said they did.
// A comment naming an absent probe is worse than silence: it stops the next agent writing the check.
//
// There are in fact THREE spellings, not two:
//   * `team-kit/coord.py#is_permission_editor`  — THE AUTHORITY. Who may run the audited
//     `widen-cage` verb (ruling D-2). ⚠ `widen-cage` and `is_permission_editor` were DELETED from
//     coord.py ([T2-R6, C-6], 2026-08-24) — this leg now calls a symbol that no longer exists;
//     see the same-dated team-kit memory entry for the disposition. Deliberately not
//     `is_authorized_launcher`.
//   * `server/spawn/spawn.js#PERMISSION_EDITOR_SEAT` — what the CAGE has in hand: the ONE seat
//     whose `permission-edits.csv` stays read-WRITE, driven here through the real
//     `resolvePermissionEditsRoGrant` rather than read as a constant.
//   * `team-kit/cagespec.py#PERMISSION_EDITOR_SEAT` — the Python mirror the materialization
//     preflight reads, which decides the same carve BEFORE any process exists.
// A widening of any one of them must not outrun the other two, in EITHER direction: the authority
// admitting a seat the cage still carves is a verb that cannot write its own audit; the cage
// opening a seat the authority refuses is an unaudited writer of the audit file.
//
// The legs drive the REAL predicates over a name roster and compare the ADMITTED SETS. Leg 0 pins
// non-vacuity: a roster nobody admits (or everybody admits) would make every comparison below
// trivially true.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const spawnMod = require('../spawn');

const TEAM_KIT = path.resolve(__dirname, '..', '..', '..', 'team-kit');

// A roster wide enough that a one-sided widening lands in it: every role name the kit's own
// predicates single out, plus the two sides' declared editors so a RENAME on either side shows up
// here rather than nowhere.
const ROSTER = [
  'leader', 'consultant', 'builder', 'reviewer', 'watcher', 'closer-1', 'daemon',
  'interviewer', 'structurer', 'assembler', 'engineer', '',
];

function pythonAdmits(module, fn) {
  const out = execFileSync('python3', ['-c',
    `import json, ${module}\n` +
    `print(json.dumps([n for n in json.loads(input()) if ${fn}]))`,
  ], { cwd: TEAM_KIT, input: JSON.stringify(ROSTER), encoding: 'utf8', timeout: 60000 });
  return new Set(JSON.parse(out));
}

capture('probe-permission-edits', async (lines) => {
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  const show = (s) => `{${[...s].map((n) => JSON.stringify(n)).sort().join(', ')}}`;
  const eq = (a, b) => a.size === b.size && [...a].every((n) => b.has(n));

  // A real goal folder with a real `permission-edits.csv`: `resolvePermissionEditsRoGrant` emits
  // nothing when the file is absent, so without it EVERY seat would look like the editor.
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'permission-edits-'));
  const goalDir = path.join(root, 'goal');
  fs.mkdirSync(path.join(goalDir, 'coordination'), { recursive: true });
  const auditFile = path.join(goalDir, spawnMod.PERMISSION_EDITS_REL);
  fs.writeFileSync(auditFile, 'seat,path,at\n');

  try {
    // THE CAGE's spelling, driven: a seat gets the read-only carve iff it is NOT the editor.
    const cageAdmits = new Set(ROSTER.filter((seat) =>
      spawnMod.resolvePermissionEditsRoGrant({ seat, goalDir }).length === 0));

    // ── 0 — NON-VACUITY ──────────────────────────────────────────────────────────────────────
    leg('0', 'the roster splits — some names are admitted, some refused (else every leg below is trivial)',
      cageAdmits.size > 0 && cageAdmits.size < ROSTER.length,
      `roster=${ROSTER.length}; cage admits ${show(cageAdmits)}`);

    // ── 1 — THE AUTHORITY vs THE CAGE ────────────────────────────────────────────────────────
    const coordAdmits = pythonAdmits('coord', 'coord.is_permission_editor(n)');
    leg('1', '`coord.py#is_permission_editor` and the cage admit EXACTLY the same seats',
      eq(coordAdmits, cageAdmits),
      `coord=${show(coordAdmits)} cage=${show(cageAdmits)}`);

    // ── 2 — THE PYTHON MIRROR ────────────────────────────────────────────────────────────────
    const specAdmits = pythonAdmits('cagespec', 'n == cagespec.PERMISSION_EDITOR_SEAT');
    leg('2', '`cagespec.py#PERMISSION_EDITOR_SEAT` agrees with both — the mirror the preflight reads',
      eq(specAdmits, cageAdmits) && eq(specAdmits, coordAdmits),
      `cagespec=${show(specAdmits)}`);

    // ── 3 — AND THE VERDICTS AGREE, NOT JUST THE NAMES ───────────────────────────────────────
    // The whole point of the spelling is the carve. Ask the mirror for the actual verdict on the
    // audit file for one admitted and one refused seat, and require them to differ the right way.
    const editor = [...cageAdmits][0];
    const other = ROSTER.find((n) => !cageAdmits.has(n));
    const verdicts = JSON.parse(execFileSync('python3', ['-c',
      'import json, cagespec\n' +
      'PE = ["ro-bind:{goalDir}", "bind:{goalDir}/coordination",\n' +
      '      "ro-bind-try:{grant:permissionEditsRo}", "bind-try:{grant:goalWrite}"]\n' +
      'print(json.dumps({n: cagespec.evaluate(PE, cagespec.PERMISSION_EDITS_REL, seat=n)[0]\n' +
      '                  for n in json.loads(input())}))',
    ], { cwd: TEAM_KIT, input: JSON.stringify([editor, other]), encoding: 'utf8', timeout: 60000 }));
    leg('3', 'the admitted seat is WRITABLE on `permission-edits.csv` and a refused one is READONLY',
      verdicts[editor] === 'writable' && verdicts[other] === 'readonly',
      `${JSON.stringify(editor)}=${verdicts[editor]} ${JSON.stringify(other)}=${verdicts[other]}`);

    lines.push('');
    lines.push(fails.length === 0 ? 'ALL LEGS PASS' : `FAILED LEGS: ${fails.join(', ')}`);
    if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
});
