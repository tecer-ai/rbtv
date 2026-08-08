'use strict';

// A3 / owner ruling `d-owner-batch1` (2) — `goalKind()`: a goal folder -> the kind a consumer
// treats it as, defaulting to `interactive`.
//
// Isolation: a throwaway goal tree under os.tmpdir(). Nothing here touches a real `.rbtv/`.
//
// ⚠ WHAT THIS PROBE IS FOR. The helper's whole job is the DEFAULT, and a default is the one
// behaviour a broken reader imitates perfectly: a `goalKind` that ignored frontmatter entirely and
// returned `'interactive'` unconditionally would pass every absence check here. So the arms are
// paired — each defaulting arm sits beside a DECLARED arm that must come back different. The
// `non-interactive` reads are the positive control (bars.md 11): they are the only checks that can
// tell "it defaulted correctly" apart from "it cannot read a descriptor at all".

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const outPath = path.join(__dirname, 'probe-goal-kind.out');
fs.writeFileSync(outPath, '');

const { goalKind } = require('../seat-folder');

const root = fs.mkdtempSync(path.join(os.tmpdir(), 'probe-goal-kind-'));

function out(...lines) {
  fs.appendFileSync(outPath, lines.join('\n') + '\n');
}

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

// Write a goal folder whose goal.md carries `frontmatter` verbatim. `null` means no goal.md at all.
function makeGoal(name, frontmatter) {
  const dir = path.join(root, name);
  fs.mkdirSync(dir, { recursive: true });
  if (frontmatter !== null) {
    fs.writeFileSync(path.join(dir, 'goal.md'), `${frontmatter}\n\nthe contract body\n`);
  }
  return dir;
}

try {
  out('COMMAND: node ' + path.relative(process.cwd(), __filename));
  out('');

  // --- the two DECLARED arms. Positive control: without these, every check below passes on a
  // helper that returns the default and never opens a file.
  check(
    'a declared non-interactive kind reads back non-interactive',
    goalKind(makeGoal('declared-non', '---\nname: declared-non\ngoal-kind: non-interactive\nstatus: briefed\n---')) === 'non-interactive',
  );
  check(
    'a declared interactive kind reads back interactive',
    goalKind(makeGoal('declared-int', '---\nname: declared-int\ngoal-kind: interactive\nstatus: briefed\n---')) === 'interactive',
  );

  // --- the ruled default. A pre-existing goal carries NO key: this is the majority case on any
  // real box, and it is the one the ruling is about.
  check(
    'a goal with no goal-kind key defaults to interactive',
    goalKind(makeGoal('legacy', '---\nname: legacy\ncreation-date: 2026-01-01\nstatus: briefed\n---')) === 'interactive',
  );

  // --- the three unreadable shapes, which resolve like absence and for the same stated reason:
  // the caller's question has no answer that is not one of the two kinds.
  check(
    'a goal.md with no frontmatter block defaults to interactive',
    goalKind(makeGoal('bare', '# just a heading, no frontmatter')) === 'interactive',
  );
  check(
    'a goal folder with no goal.md defaults to interactive',
    goalKind(makeGoal('empty', null)) === 'interactive',
  );
  check(
    'a path that does not exist defaults to interactive',
    goalKind(path.join(root, 'no-such-goal')) === 'interactive',
  );
  check(
    'a value outside the enum defaults to interactive (lint is what names it)',
    goalKind(makeGoal('bogus', '---\nname: bogus\ngoal-kind: nonsense\n---')) === 'interactive',
  );

  // --- shapes a YAML author actually produces, which the regex read must not fall over on.
  check(
    'a quoted value is unquoted',
    goalKind(makeGoal('quoted', '---\nname: quoted\ngoal-kind: "non-interactive"\n---')) === 'non-interactive',
  );
  check(
    'a key AFTER goal-kind does not swallow it',
    goalKind(makeGoal('trailing', '---\ngoal-kind: non-interactive\nstatus: briefed\n---')) === 'non-interactive',
  );
  check(
    'CRLF line endings read the same as LF',
    goalKind(makeGoal('crlf', '---\r\nname: crlf\r\ngoal-kind: non-interactive\r\n---')) === 'non-interactive',
  );

  const failed = checks.filter((c) => !c.pass);
  out('');
  out(`SUMMARY: ${checks.length - failed.length}/${checks.length} passed`);
  out(failed.length ? 'VERDICT: FAIL' : 'VERDICT: PASS');
  process.exitCode = failed.length ? 1 : 0;
} catch (err) {
  out(`ERROR: ${err && err.stack ? err.stack : err}`);
  out('VERDICT: FAIL');
  process.exitCode = 1;
} finally {
  fs.rmSync(root, { recursive: true, force: true });
}
