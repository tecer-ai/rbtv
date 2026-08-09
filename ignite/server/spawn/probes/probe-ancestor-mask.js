'use strict';

// r-seat-context-cut-at-launch-folder — WALL PROBES for the ANCESTOR MASK.
//
// Same evidence rule as probe-seat-cage: every claim is proven by what the CAGED PROCESS ACTUALLY
// SEES, read back from outside. A composed flag list is not evidence that a mount happened — each
// leg here runs a real `bwrap` and reads the bytes it printed.
//
// The five bars are the ruling's five bounds:
//   a  ancestor CLAUDE.md / AGENTS.md / .claude are ABSENT for a plain seat
//   b  CLAUDE.md INSIDE .rbtv/goals (goal + run) is STILL READABLE            (bound i)
//   c  the channel policy keeps path-up CLAUDE.md while .claude stays masked  (bound ii)
//   d  the LAUNCH FOLDER's own artifacts are untouched
//   e  the auto-memory dir is masked while a SIBLING transcript stays readable (bound iii — the
//      one bound whose failure mode is silent: it breaks `--resume`, not the mask)

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeSeatCage, composeAncestorMasks, specToBwrapFlags } = require('../cage');
const { buildBwrapArgv } = require('../bwrap');

// The shipped stack's shape, cut to the lines this probe's claims depend on: the read-root floor
// (which is what makes ancestors visible at all), the goal/run ro-binds, and the seat's RW folder.
const TEMPLATE = [
  'ro-bind:{grant:readRoot}',
  'ro-bind:{goalDir}',
  'tmpfs:{goalDir}/seats',
  'bind:{seatDir}',
];

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'anc-mask-'));
  const ws = path.join(root, 'ws');
  const goalDir = path.join(ws, '.rbtv', 'goals', 'testgoal');
  const runDir = goalDir;   // 7.607 E2a — goal-direct: the goal folder IS the package
  const seatDir = path.join(runDir, 'seats', 'mine');
  fs.mkdirSync(path.join(runDir, 'seats'), { recursive: true });
  // 7.607 E2b — the `tmpfs:{goalDir}/runs` template line and its mountpoint mkdir are BOTH gone
  // (design-lock item 8); this fixture no longer creates a `runs/` and the template no longer
  // names one.
  // spawn.js#composeCageFor creates it for every real seat; this fixture mirrors that. Both
  // go away with the profile's template line (see the E2a note in spawn.js).
  fs.mkdirSync(path.join(ws, '.claude', 'rules'), { recursive: true });
  fs.mkdirSync(path.join(seatDir, '.claude', 'skills'), { recursive: true });

  fs.writeFileSync(path.join(ws, 'CLAUDE.md'), 'VAULT-ROOT-RULES\n');
  fs.writeFileSync(path.join(ws, 'AGENTS.md'), 'VAULT-ROOT-AGENTS\n');
  fs.writeFileSync(path.join(ws, '.claude', 'rules', 'r.md'), 'WORKSPACE-RULE\n');
  // 7.607 E2a — there is ONE level inside the goals tree now. The old fixture wrote a goal
  // CLAUDE.md and a RUN CLAUDE.md at two depths; goal-direct collapses them into this one file,
  // so writing both would only have the second overwrite the first.
  fs.writeFileSync(path.join(goalDir, 'CLAUDE.md'), 'GOAL-RULES\n');
  fs.writeFileSync(path.join(seatDir, 'CLAUDE.md'), 'SEAT-OWN-RULES\n');
  fs.writeFileSync(path.join(seatDir, '.claude', 'skills', 's.md'), 'SEAT-OWN-SKILL\n');
  fs.writeFileSync(path.join(runDir, 'sessions.csv'), 'seat,pid,pid-starttime\nmine,1,1\n');
  return { root, ws, goalDir, runDir, seatDir };
}

function cageFor(f, keepInstructionFiles) {
  const spec = composeSeatCage({
    seatBinds: TEMPLATE,
    values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
    grants: [{ readRoot: f.ws }],
  });
  const mask = composeAncestorMasks(spec, {
    workspaceRoot: f.ws,
    launchFolder: f.seatDir,
    keepInstructionFiles,
  });
  return { flags: [...specToBwrapFlags(spec), ...mask.flags], mask };
}

// Run a shell line inside the real cage and return its combined output.
function inCage(f, keepInstructionFiles, script) {
  const argv = buildBwrapArgv({
    argv: ['bash', '-c', script],
    workdir: f.seatDir,
    harness: 'claude',           // so ~/.claude is bound back — leg (e) needs the real store present
    seatBinds: cageFor(f, keepInstructionFiles).flags,
  });
  try {
    return execFileSync(argv[0], argv.slice(1), { encoding: 'utf8', timeout: 30000, stdio: ['ignore', 'pipe', 'pipe'] });
  } catch (err) {
    return ((err.stdout || '') + (err.stderr || '')).toString();
  }
}

capture('probe-ancestor-mask', async (lines) => {
  const f = fixture();
  const fails = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };

  try {
    // ── (a) ancestor harness artifacts are ABSENT for a plain seat ────────────────────────────
    const a = inCage(f, false,
      `echo "root-claude=[$(cat ${f.ws}/CLAUDE.md 2>/dev/null)]"; ` +
      `echo "root-agents=[$(cat ${f.ws}/AGENTS.md 2>/dev/null)]"; ` +
      `echo "root-dotclaude=[$(ls ${f.ws}/.claude 2>/dev/null | tr '\\n' ' ')]"`);
    leg('A', 'ancestor CLAUDE.md / AGENTS.md / .claude are empty for a plain seat',
      /root-claude=\[\]/.test(a) && /root-agents=\[\]/.test(a) && /root-dotclaude=\[\]/.test(a),
      `in-cage: ${JSON.stringify(a.trim())}`);

    // ── (b) bound (i): the goals tree keeps injecting ─────────────────────────────────────────
    // The SEAT's own CLAUDE.md is read in the same command as the goal's: with one level left in
    // the goals tree, a leg reading only the goal file would pass on a cage that masked everything
    // below it too. Two depths still exist — goal and seat — and both must survive.
    const b = inCage(f, false,
      `echo "goal=[$(cat ${f.goalDir}/CLAUDE.md 2>/dev/null)]"; echo "seat=[$(cat ${f.seatDir}/CLAUDE.md 2>/dev/null)]"`);
    leg('B', 'CLAUDE.md inside .rbtv/goals (the goal folder and the seat folder) is NOT masked',
      /goal=\[GOAL-RULES\]/.test(b) && /seat=\[SEAT-OWN-RULES\]/.test(b),
      `in-cage: ${JSON.stringify(b.trim())}`);

    // ── (c) bound (ii): the channel policy ────────────────────────────────────────────────────
    const c = inCage(f, true,
      `echo "root-claude=[$(cat ${f.ws}/CLAUDE.md 2>/dev/null)]"; ` +
      `echo "root-agents=[$(cat ${f.ws}/AGENTS.md 2>/dev/null)]"; ` +
      `echo "root-dotclaude=[$(ls ${f.ws}/.claude 2>/dev/null | tr '\\n' ' ')]"`);
    leg('C', 'keep-instruction-files keeps path-up CLAUDE.md/AGENTS.md while .claude stays masked',
      /root-claude=\[VAULT-ROOT-RULES\]/.test(c) && /root-agents=\[VAULT-ROOT-AGENTS\]/.test(c) && /root-dotclaude=\[\]/.test(c),
      `in-cage: ${JSON.stringify(c.trim())}`);

    // ── (d) the launch folder's OWN artifacts are never masked ────────────────────────────────
    const d = inCage(f, false,
      `echo "own-claude=[$(cat ${f.seatDir}/CLAUDE.md 2>/dev/null)]"; ` +
      `echo "own-skill=[$(cat ${f.seatDir}/.claude/skills/s.md 2>/dev/null)]"`);
    leg('D', "the launch folder's own CLAUDE.md and .claude/ are untouched",
      /own-claude=\[SEAT-OWN-RULES\]/.test(d) && /own-skill=\[SEAT-OWN-SKILL\]/.test(d),
      `in-cage: ${JSON.stringify(d.trim())}`);

    // ── (e) bound (iii): auto-memory masked, sibling transcript READABLE ──────────────────────
    // Deliberately measured against the REAL project store: the split this leg proves is between
    // two paths the harness itself creates, and a fixture would prove the mask against a shape
    // nothing on the box actually has.
    const projects = path.join(os.homedir(), '.claude', 'projects');
    const slug = (fs.readdirSync(projects, { withFileTypes: true }) || [])
      .filter((e) => e.isDirectory() && fs.existsSync(path.join(projects, e.name, 'memory')))
      .map((e) => path.join(projects, e.name))[0];
    if (!slug) {
      leg('E', 'auto-memory masked while a sibling transcript stays readable',
        false, `no memory dir under ${projects} — the mask target does not exist, so this bound cannot be proven here`);
    } else {
      const transcript = fs.readdirSync(slug).find((n) => n.endsWith('.jsonl'));
      const memDir = path.join(slug, 'memory');
      const e = inCage(f, false,
        `echo "mem=[$(ls ${memDir} 2>/dev/null | tr '\\n' ' ')]"; ` +
        (transcript ? `echo "tx=[$(head -c 12 ${path.join(slug, transcript)} 2>/dev/null)]"` : 'echo "tx=[NO-TRANSCRIPT]"'));
      leg('E', 'auto-memory dir is masked while a sibling session transcript stays readable',
        /mem=\[\]/.test(e) && !/tx=\[\]/.test(e) && !/tx=\[NO-TRANSCRIPT\]/.test(e),
        `store ${slug} — in-cage: ${JSON.stringify(e.trim())}`);
    }

    // ── The composition itself: masks must be emitted AFTER the openings they shadow. ─────────
    const { flags, mask } = cageFor(f, false);
    const joined = flags.join(' ');
    leg('F', 'every mask flag is emitted after the read-root floor it must shadow',
      joined.indexOf(`--ro-bind ${f.ws} ${f.ws}`) < joined.indexOf(`--tmpfs ${f.ws}/.claude`) &&
      mask.masked.configDirs >= 1 && mask.masked.instructionFiles >= 2 && mask.policy === 'cut-all',
      `policy=${mask.policy} masked=${JSON.stringify(mask.masked)}`);

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`ancestor-mask probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
