#!/usr/bin/env node
'use strict';

// probe-verdict-vocabulary — D25's recurrence-proof. seeding.js classifies every coord
// verdict as waitable or not; an unknown class falls OUT of the frozen-at-seeding alarm.
// This probe extracts coord's LIVE vocabulary (CLASS_TO_VERDICT values + every
// rec["verdict"] = "…" assignment — never a hardcoded copy on this side alone) and
// asserts seeding.CLASSIFIED_VERDICTS names every value. A new coord verdict is a
// commit-time failure, never a silent 10-second alarm loop.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { requirePythonCmd } = require('../../lib/python-cmd');

const HERE = __dirname;
const IGNITE = path.join(HERE, '..', '..');
const COORD_PY = path.join(IGNITE, 'team-kit', 'coord.py');
const SEEDING = path.join(HERE, '..', 'seeding.js');
const OUT_PATH = path.join(HERE, 'probe-verdict-vocabulary.out');

const { CLASSIFIED_VERDICTS } = require('../seeding.js');

const lines = [];
const failures = [];
function say(s) { lines.push(s); }
function check(claim, ok, detail) {
  say(`${ok ? 'ok  ' : 'FAIL'}  ${claim}${ok ? '' : ` — ${detail}`}`);
  if (!ok) failures.push(claim);
}

// THE PRODUCT IS SEVERAL FILES NOW. The move-only split [D23, T4-R12] carried
// `CLASS_TO_VERDICT` and the `rec["verdict"]` assignments out of coord.py into the sibling files
// coord.py loads, so an extract over coord.py alone yields an EMPTY vocabulary — which this probe
// already refuses as green-by-absence. The file list is derived from coord.py's own SPLIT_MODULES
// tuple, so the next split file arrives here for free. Scan target only: the extractor is unchanged.
const SPLIT_MODULES = ((fs.readFileSync(COORD_PY, 'utf8')
  .match(/SPLIT_MODULES = \(([\s\S]*?)\)/) || [, ''])[1].match(/"([a-z_]+)"/g) || [])
  .map((q) => q.replace(/"/g, ''));
const PRODUCT_PY = [COORD_PY].concat(
  SPLIT_MODULES.map((n) => path.join(IGNITE, 'team-kit', `${n}.py`)));

const EXTRACT = `
import ast, sys
tree = ast.parse("\\n".join(open(p, encoding="utf-8").read() for p in sys.argv[1:]))
verdicts = set()
class V(ast.NodeVisitor):
    def visit_Assign(self, node):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "CLASS_TO_VERDICT" and isinstance(node.value, ast.Dict):
                for v in node.value.values:
                    if isinstance(v, ast.Constant) and isinstance(v.value, str):
                        verdicts.add(v.value)
        if node.targets and isinstance(node.targets[0], ast.Subscript):
            sl = node.targets[0]
            key = sl.slice if not isinstance(sl.slice, ast.Index) else sl.slice.value
            if isinstance(key, ast.Constant) and key.value == "verdict":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    verdicts.add(node.value.value)
        self.generic_visit(node)
V().visit(tree)
print("\\n".join(sorted(verdicts)))
`;

const raw = execFileSync(requirePythonCmd(), ['-c', EXTRACT, ...PRODUCT_PY], { encoding: 'utf8' });
const coordVerdicts = raw.split(/\n/).map((s) => s.trim()).filter(Boolean);

say('── coord live verdict vocabulary (AST of CLASS_TO_VERDICT + rec["verdict"] assignments) ──');
say(`  coord: ${coordVerdicts.join(', ')}`);
say(`  seeding CLASSIFIED_VERDICTS: ${Object.keys(CLASSIFIED_VERDICTS).join(', ')}`);

check('coord yielded a NON-EMPTY vocabulary — an empty extract would green-by-absence',
  coordVerdicts.length > 0, `n=${coordVerdicts.length}`);
check('seeding CLASSIFIED_VERDICTS is a non-empty object',
  CLASSIFIED_VERDICTS && Object.keys(CLASSIFIED_VERDICTS).length > 0);

const missing = coordVerdicts.filter((v) => !Object.prototype.hasOwnProperty.call(CLASSIFIED_VERDICTS, v));
check('every coord verdict is a key of seeding.CLASSIFIED_VERDICTS',
  missing.length === 0, `unclassified: ${missing.join(', ')}`);

const extra = Object.keys(CLASSIFIED_VERDICTS).filter((v) => !coordVerdicts.includes(v));
check('seeding names no verdict coord does not produce (drift the other way is also a defect)',
  extra.length === 0, `extra: ${extra.join(', ')}`);

say('');
say('── red arm — drop IDLE from a COPY of the classified table ──────────────────────────────');
const mutated = { ...CLASSIFIED_VERDICTS };
delete mutated.IDLE;
const missingAfter = coordVerdicts.filter((v) => !Object.prototype.hasOwnProperty.call(mutated, v));
check('WITHOUT IDLE in the classified table, coverage FAILS — the probe can go red',
  missingAfter.includes('IDLE'), `missingAfter=${missingAfter.join(',')}`);

const srcHasIdle = fs.readFileSync(SEEDING, 'utf8').includes("IDLE: 'not-waitable'");
check('the live seeding.js still names IDLE — the red arm mutated a copy, not the source',
  srcHasIdle);

const verdict = failures.length ? 'FAIL' : 'PASS';
say('');
say(`SUMMARY: ${lines.filter((l) => l.startsWith('ok')).length}/${lines.filter((l) => /^(ok|FAIL)/.test(l)).length} passed`);
say(`VERDICT: ${verdict}`);
const out = lines.join('\n') + '\n';
fs.writeFileSync(OUT_PATH, out);
process.stdout.write(out);
process.exit(failures.length ? 1 : 0);
