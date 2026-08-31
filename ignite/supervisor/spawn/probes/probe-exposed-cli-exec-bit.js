'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { resolveExposedCliGrants } = require('../spawn');

// task 161: a granted CLI whose target `.py` is `-rw-rw-r--` (no +x) used to mint a bare
// `--symlink` straight to that target — the OS then refuses `Permission denied` on the granted
// name, unrelated to whether the seat is even declared to run it. Drives resolveExposedCliGrants
// against a REAL 644 shebang fixture, the same shape as capability_cards.py / gtools.py.
capture('probe-exposed-cli-exec-bit', async (lines) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'exec-bit-'));
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  try {
    const seatDir = path.join(root, 'seat');
    fs.mkdirSync(seatDir, { recursive: true });
    const target = path.join(root, 'fixture-cli.py');
    fs.writeFileSync(target, '#!/usr/bin/env python3\nprint("ran")\n');
    fs.chmodSync(target, 0o664);  // -rw-rw-r-- — the measured defect shape
    const mode = fs.statSync(target).mode & 0o777;
    leg('E0 fixture', 'the fixture target is NOT executable to start (control precondition)',
      (mode & 0o111) === 0, `mode=${mode.toString(8)}`);
    fs.writeFileSync(path.join(seatDir, 'seat.md'),
      `---\nexposed-clis:\n  - fixture-cli ${target}\n---\n\nbody\n`);
    const grants = resolveExposedCliGrants({ seat: 'probe', seatDir }, () => {});
    leg('E1', 'a 644 target still resolves ONE grant (not silently dropped)',
      grants.length === 1, `grants=${JSON.stringify(grants)}`);
    const g = grants[0];
    leg('E2', 'the grant carries an execWrapper (the target itself has no +x)',
      !!g.execWrapper, `execWrapper=${g.execWrapper}`);
    let wrapperMode = -1;
    try { wrapperMode = fs.statSync(g.execWrapper).mode & 0o777; } catch { /* leg fails below */ }
    leg('E3', 'the minted wrapper IS +x on disk',
      (wrapperMode & 0o111) !== 0, `wrapperMode=${wrapperMode.toString(8)}`);
    let out = '';
    try { out = execFileSync(g.exposedCliEntry, [], { encoding: 'utf8' }); } catch (err) {
      out = `EXEC FAILED: ${err.message}`;
    }
    leg('E4', 'invoking the granted exposedCliEntry (as the bare-name symlink target would) '
      + 'actually runs the target, no Permission denied',
      out.trim() === 'ran', `out=${JSON.stringify(out)}`);
    // Control: a target that IS already +x gets no wrapper — unchanged behaviour.
    const execTarget = path.join(root, 'fixture-cli-exec.py');
    fs.writeFileSync(execTarget, '#!/usr/bin/env python3\nprint("ran2")\n');
    fs.chmodSync(execTarget, 0o755);
    fs.writeFileSync(path.join(seatDir, 'seat.md'),
      `---\nexposed-clis:\n  - fixture-cli2 ${execTarget}\n---\n\nbody\n`);
    const grants2 = resolveExposedCliGrants({ seat: 'probe', seatDir }, () => {});
    leg('E5 control', 'an ALREADY +x target gets no wrapper — symlinked straight to itself',
      grants2.length === 1 && grants2[0].execWrapper === null
        && grants2[0].exposedCliEntry === execTarget,
      `grants2=${JSON.stringify(grants2)}`);
  } finally {
    try { fs.rmSync(root, { recursive: true, force: true }); } catch { /* best effort */ }
  }
  if (fails.length > 0) throw new Error(`FAILED LEGS: ${fails.join(', ')}`);
  lines.push('ALL LEGS PASS');
});
