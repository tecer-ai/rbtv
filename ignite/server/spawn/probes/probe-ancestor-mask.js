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
//
// Legs g/h carry a LATER ruling on the same mask surface (owner, 2026-08-11, task 7.566): the
// third-party secrets file `.rbtv/config/.env` is masked for every seat, while the one-key
// `.rbtv/config/sender-token.env` beside it stays readable so a caged seat keeps gateway auth.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeSeatCage, composeAncestorMasks, specToBwrapFlags, projectStoreSlug, lastCovering } = require('../cage');
const { admitLaunch, bindsToSpec } = require('../../../envelope/launch');
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
  // 7.566 — the two config files leg (g) is about: the third-party secrets file that must be
  // MASKED, and the one-key sender-token file beside it that must NOT be.
  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', '.env'), 'SLACK_BOT_TOKEN=xoxb-THIRD-PARTY-SECRET\n');
  fs.writeFileSync(path.join(ws, '.rbtv', 'config', 'sender-token.env'), 'IGNITE_SENDER_TOKEN=SENDER-TOKEN-VALUE\n');
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

    // ── (e) bound (iii): auto-memory masked, the OWN store's transcript READABLE ──────────────
    // Deliberately measured against the REAL project store: the split this leg proves is between
    // two paths the harness itself creates, and a fixture would prove the mask against a shape
    // nothing on the box actually has.
    //
    // ⚠ THIS LEG CHANGED SHAPE 2026-08-24, AND THE CONTRACT GOT STRONGER, NOT WEAKER. It used to
    // pick an ARBITRARY store — a FOREIGN one — and require its transcript readable in-cage,
    // because the mask was per-store (`--tmpfs` over every `*/memory`) and left everything else
    // on the box open. That mask emitted one flag per store, 68,503 bytes of argv against a
    // ~16 KB `tmux new-window` ceiling, and killed every seat-door launch. Masking the projects
    // ROOT and binding back only the seat's own store is O(1) — and the foreign store is now
    // ABSENT rather than merely memory-less, which is what a seat should always have seen. The
    // ruling's scope line is `--resume` must survive, and a seat only ever resumes its OWN
    // session, so the own store is the whole of what the bind-back owes.
    const projects = path.join(os.homedir(), '.claude', 'projects');
    const own = path.join(projects, projectStoreSlug(f.seatDir));
    const foreign = (fs.readdirSync(projects, { withFileTypes: true }) || [])
      .filter((d) => d.isDirectory() && path.join(projects, d.name) !== own)
      .map((d) => path.join(projects, d.name))[0];
    // The own store is what `composeMemoryMask` creates and binds back; seeding it here is what
    // gives the leg something to READ, exactly as a real seat's prior session would have left it.
    fs.mkdirSync(path.join(own, 'memory'), { recursive: true });
    fs.writeFileSync(path.join(own, 'probe-sess.jsonl'), 'OWN-TRANSCRIPT\n');
    fs.writeFileSync(path.join(own, 'memory', 'probe-m.md'), 'OWN-MEMORY\n');
    try {
      if (!foreign) {
        leg('E', "auto-memory masked, own transcript readable, foreign stores absent",
          false, `no second store under ${projects} — the foreign-absence half cannot be proven here`);
      } else {
        const e = inCage(f, false,
          `echo "own-mem=[$(ls ${path.join(own, 'memory')} 2>/dev/null | tr '\\n' ' ')]"; ` +
          `echo "own-tx=[$(head -c 14 ${path.join(own, 'probe-sess.jsonl')} 2>/dev/null)]"; ` +
          `echo "foreign=[$(ls ${foreign} 2>/dev/null | tr '\\n' ' ')]"`);
        leg('E', "the own store's transcript stays readable while its memory dir and every foreign store are absent",
          /own-tx=\[OWN-TRANSCRIPT\]/.test(e) && /own-mem=\[\]/.test(e) && /foreign=\[\]/.test(e),
          `own ${own} — foreign ${foreign} — in-cage: ${JSON.stringify(e.trim())}`);
      }
    } finally {
      try { fs.rmSync(own, { recursive: true, force: true }); } catch {}
    }

    // ── The composition itself: masks must be emitted AFTER the openings they shadow. ─────────
    const { flags, mask } = cageFor(f, false);
    const joined = flags.join(' ');
    leg('F', 'every mask flag is emitted after the read-root floor it must shadow',
      joined.indexOf(`--ro-bind ${f.ws} ${f.ws}`) < joined.indexOf(`--tmpfs ${f.ws}/.claude`) &&
      mask.masked.configDirs >= 1 && mask.masked.instructionFiles >= 2 && mask.policy === 'cut-all',
      `policy=${mask.policy} masked=${JSON.stringify(mask.masked)}`);

    // ── (g) 7.566: the third-party secrets file is MASKED, the sender token stays readable ────
    // The whole exposure is `read-root: true` — the entire workspace bound read-only, secrets
    // file included. This is the leg that says the seat still reaches the gateway afterwards:
    // masking without the split would take the channel master's auth with it, and that failure
    // is invisible until the master goes silent.
    const g = inCage(f, true,   // the channel policy — the ONE live read-root seat runs it
      `echo "secrets=[$(cat ${f.ws}/.rbtv/config/.env 2>/dev/null)]"; ` +
      `echo "token=[$(cat ${f.ws}/.rbtv/config/sender-token.env 2>/dev/null)]"`);
    leg('G', '.rbtv/config/.env is masked in-cage while .rbtv/config/sender-token.env stays readable',
      /secrets=\[\]/.test(g) && /token=\[IGNITE_SENDER_TOKEN=SENDER-TOKEN-VALUE\]/.test(g),
      `in-cage: ${JSON.stringify(g.trim())}`);

    // ── (h) the absent-path discipline, composition-only ──────────────────────────────────────
    // Masking a path nothing bound would make bwrap mkdir a mountpoint over nothing (cage.js's
    // own note). No `.env` on disk -> no flag, and the counter says so.
    const bare = fs.mkdtempSync(path.join(os.tmpdir(), 'anc-mask-bare-'));
    try {
      const spec = composeSeatCage({
        seatBinds: TEMPLATE,
        values: { workdir: f.seatDir, seatDir: f.seatDir, goalDir: f.goalDir },
        grants: [{ readRoot: bare }],
      });
      const m = composeAncestorMasks(spec, { workspaceRoot: bare, launchFolder: f.seatDir });
      const withEnv = cageFor(f, true).mask;
      leg('H', 'the .env mask fires only when the file exists (masked.secrets 1 with it, 0 without)',
        withEnv.masked.secrets === 1 && m.masked.secrets === 0
        && !m.flags.join(' ').includes(path.join(bare, '.rbtv', 'config', '.env')),
        `with-file=${JSON.stringify(withEnv.masked)} without-file=${JSON.stringify(m.masked)}`);
    } finally {
      try { fs.rmSync(bare, { recursive: true, force: true }); } catch {}
    }

    // ── (i) lastCovering agrees with the COMPILER about what a conflict is ────────────────────
    // The mask composer's visibility query used to re-derive "covering pair at different access"
    // with none of the compiler's authorized carves, so a workspace the compiler compiled happily
    // was illegal the moment it sat under a baked temp family: `/tmp` is family 4/7 RW and family
    // 5 `vault-wide-read` RO at once, and `lastCovering` threw `E_LAUNCH_REFUSED conflict` on a
    // launch that held no conflict. `probes/lib.js` routes every fixture to `/var/tmp` to dodge
    // exactly this; that workaround is the evidence, and this leg is the assertion under it.
    //
    // Deliberately rooted in `/tmp` — the shape the workaround avoids — and driven through the
    // REAL compiler, so the leg fails if either side's rules move away from the other.
    const tmpWs = fs.mkdtempSync(path.join('/tmp', 'anc-mask-carve-'));
    try {
      const g = path.join(tmpWs, 'work', '.rbtv', 'goals', 'g');
      fs.mkdirSync(path.join(g, 'seats', 's'), { recursive: true });
      fs.mkdirSync(path.join(tmpWs, 'work', '.rbtv', 'mirror', 'x'), { recursive: true });
      fs.writeFileSync(path.join(g, 'seats', 's', 'seat.md'), '---\nseat: s\n---\n');
      const wsRoot = path.join(tmpWs, 'work');
      const admitted = admitLaunch({ workspaceRoot: wsRoot, goalId: 'g', goalDir: g });
      if (!admitted.spawn) {
        leg('I', 'a workspace the compiler ADMITS is not refused by lastCovering',
          false, `the compiler itself refused the fixture: ${JSON.stringify(admitted.refuse)}`);
      } else {
        const compiled = bindsToSpec(admitted.binds);
        const covering = compiled.filter((e) => wsRoot === e.path || wsRoot.startsWith(`${e.path}/`));
        let outcome;
        try { outcome = `OK (${(lastCovering(compiled, wsRoot) || {}).verb})`; }
        catch (err) { outcome = `${err.code}: ${err.message}`; }
        leg('I', 'a workspace the compiler ADMITS is not refused by lastCovering (temp-floor carve)',
          outcome.startsWith('OK')
          && covering.some((e) => e.verb === 'bind') && covering.some((e) => e.verb === 'ro-bind'),
          `binds=${admitted.binds.length} covering=${JSON.stringify(covering.map((e) => `${e.verb}:${e.family}`))} lastCovering -> ${outcome}`);
      }
    } finally {
      try { fs.rmSync(tmpWs, { recursive: true, force: true }); } catch {}
    }

    lines.push('');
    lines.push(`legs: ${fails.length === 0 ? 'ALL PASS' : `FAILED -> ${fails.join(', ')}`}`);
    if (fails.length > 0) throw new Error(`ancestor-mask probes failed: ${fails.join(', ')}`);
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
