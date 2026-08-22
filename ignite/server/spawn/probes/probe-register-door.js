'use strict';

// THE REGISTER DOOR — a caged filer's declared `cli-write-roots` entry that IS a goal subfolder
// composes into a real read-write opening, while every walled surface of the goals tree stays
// unwritable (ignite-engine m1 task T1 `open-register-door`; engine-goal E1: "the CLI writes ONE
// FILE PER FILING into this goal's `register/` folder, declared as the CLI's write root so a
// filer's cage opens exactly that folder", 2026-08-22).
//
// THE CAUSE THIS PROBE PINS: `seat-grants.js#rwPathRefusal` rule 3 — before 2026-08-22 a blanket
// "overlaps `<ws>/.rbtv/goals` in either direction" — applied by `spawn.js#resolveCliWriteRootGrants`
// to the materializer-baked root `<ws>/.rbtv/goals/ignite-engine/register`; the daemon journal
// carried the refusal on every leader spawn (18 lines in 3 days). The rule is now a WALLED-SET
// test (`goalsTreeRefusal`): goals root · goal roots · `seats/` · `coordination/` · the record
// files, lexically AND through symlinks; a proper goal subfolder is admitted. ONE predicate for
// `rw-paths`, `permission-edits.csv` and `cli-write-roots`, and for `engine/cage-admission.js`.
//
// Driven through `composeCageFor` — the ONE composer both spawn doors use — against a real goal
// tree on disk and the SHIPPED template (`config/spawn-profiles.yaml`'s `cage.SeatBinds`, read
// from the file, never retyped: retyping would test a copy). Evidence rule is probe-seat-cage's
// (design §6, D51): a write claim is proven ON DISK from OUTSIDE the cage; the in-cage exit status
// is information only.
//
// LEGS. Compose legs run in any process: L1 the register is bound rw AFTER the read-root floor;
// L2 zero refusal log lines for the register entry; L6 the four refused shapes (goals root, a goal
// root, `<goal>/coordination`, `<goal>/seats/x`) still compose nothing, each with its logged
// reason. Exec legs need `bwrap`: L3 the REAL filing CLI files in-cage → exit 0 AND exactly ONE
// new file in the fixture's `register/open/`; L4 an in-cage write to the engine goal's
// `sessions.csv` fails, bytes unchanged; L5 an in-cage write one level ABOVE the register fails.
// Where `bwrap` cannot start in this process (a caged sitting: the kernel refuses a nested
// namespace, measured 2026-08-22) L3–L5 print INOPERATIVE and the probe's status IS INOPERATIVE —
// never PASS for a leg it did not run. The scheduled suite's uncaged run is the PASS.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const yaml = require('js-yaml');
const { execFileSync } = require('node:child_process');
const { capture } = require('./lib');
const { composeCageFor } = require('../spawn');
const { buildBwrapArgv } = require('../bwrap');
const { parseSeatPath } = require('../../seat-identity/seat-folder');

const IGNITE = path.join(__dirname, '..', '..', '..');
// The REAL filing CLI, from the live tree. In-cage it is reachable through the `rbtvRoot`
// fence-read grant (D3 item 4), the same path every seat runs it from.
const FILE_ISSUE = path.join(IGNITE, 'team-kit', 'file-issue.py');

function shippedSeatBinds() {
  const cfg = yaml.load(fs.readFileSync(path.join(IGNITE, 'config', 'spawn-profiles.yaml'), 'utf8'));
  return cfg.cage.SeatBinds;
}

function fixture() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'register-door-'));
  const ws = path.join(root, 'ws');
  // `file-issue.py` derives the workspace root from the first ancestor holding `.rbtv/config/`,
  // and reads `rbtv.json#rbtv_path` for an rbtv tree holding `ignite/` and `meta/`.
  fs.mkdirSync(path.join(ws, '.rbtv', 'config'), { recursive: true });
  const rbtvTree = path.join(ws, 'rbtv-tree');
  fs.mkdirSync(path.join(rbtvTree, 'ignite'), { recursive: true });
  fs.mkdirSync(path.join(rbtvTree, 'meta'), { recursive: true });
  fs.writeFileSync(path.join(ws, 'rbtv.json'), JSON.stringify({ rbtv_path: rbtvTree }) + '\n');

  const goalsDir = path.join(ws, '.rbtv', 'goals');
  // The ENGINE goal: the register (empty `open/`) and a record file beside it.
  const engineGoal = path.join(goalsDir, 'ignite-engine');
  const register = path.join(engineGoal, 'register');
  const openDir = path.join(register, 'open');
  fs.mkdirSync(openDir, { recursive: true });
  fs.writeFileSync(path.join(engineGoal, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\nleader,s1,1,1\n');

  // The FILER'S goal `alpha`: `leader` carries exactly what the materializer bakes into a real
  // leader; `refuser` carries the four shapes that must stay refused (each EXISTS, so the refusal
  // is rule 3's and not the nonexistent-path skip); `plain` is the fail-closed control.
  const alpha = path.join(goalsDir, 'alpha');
  const leaderDir = path.join(alpha, 'seats', 'leader');
  const refuserDir = path.join(alpha, 'seats', 'refuser');
  const plainDir = path.join(alpha, 'seats', 'plain');
  fs.mkdirSync(path.join(alpha, 'coordination'), { recursive: true });
  fs.mkdirSync(path.join(alpha, 'seats', 'x'), { recursive: true });
  for (const d of [leaderDir, refuserDir, plainDir]) fs.mkdirSync(d, { recursive: true });
  fs.writeFileSync(path.join(alpha, 'sessions.csv'), 'seat,session-id,pid,pid-starttime\n');

  const refused = [
    goalsDir,                                // the goals root
    alpha,                                   // a goal root
    path.join(alpha, 'coordination'),        // under <goal>/coordination/
    path.join(alpha, 'seats', 'x'),          // under <goal>/seats/
  ];
  fs.writeFileSync(path.join(leaderDir, 'seat.md'),
    ['---', 'seat: leader', 'cli-write-roots:', `- ${register}`, '---', 'briefing'].join('\n') + '\n');
  fs.writeFileSync(path.join(refuserDir, 'seat.md'),
    ['---', 'seat: refuser', 'cli-write-roots:', ...refused.map((r) => `- ${r}`), '---', 'briefing'].join('\n') + '\n');
  fs.writeFileSync(path.join(plainDir, 'seat.md'), '---\nseat: plain\n---\nbriefing\n');

  return { root, ws, goalsDir, engineGoal, register, openDir, leaderDir, refuserDir, plainDir, refused,
           engineSessions: path.join(engineGoal, 'sessions.csv') };
}

// `logs` collects {level, message, entry} — the refusal reason AND the entry it was about, so a
// leg can ask "was THIS entry refused" without parsing the reason text.
function cageFor(seatDir, logs) {
  const log = (level, message, extra) => logs.push({ level, message, entry: extra && extra.entry });
  return composeCageFor({ SeatBinds: shippedSeatBinds() }, parseSeatPath(seatDir), seatDir, '127.0.0.1:7431', log);
}

function hasFlag(flags, verb, p) {
  for (let i = 0; i < flags.length; i++) {
    if (flags[i] === verb && flags[i + 1] === p) return true;
  }
  return false;
}

function bindCount(flags, p) {
  let n = 0;
  for (let i = 0; i < flags.length; i++) if (flags[i] === '--bind' && flags[i + 1] === p) n++;
  return n;
}

function inCage(seatDir, flags, script) {
  const argv = buildBwrapArgv({ argv: ['bash', '-c', script], workdir: seatDir, harness: null, seatBinds: flags });
  try {
    const stdout = execFileSync(argv[0], argv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'], timeout: 60000, encoding: 'utf8' });
    return { exit: 0, stdout: stdout.trim(), stderr: '' };
  } catch (err) {
    return {
      exit: err.status === undefined ? -1 : err.status,
      stdout: (err.stdout || '').toString().trim(),
      stderr: (err.stderr || '').toString().trim(),
    };
  }
}

function bytes(p) {
  try { return fs.readFileSync(p, 'utf8'); } catch (err) { return `<<ABSENT:${err.code}>>`; }
}

const refusals = (logs) => logs.filter((l) => l.message.includes('cli-write-roots entry REFUSED'));

capture('probe-register-door', async (lines) => {
  const f = fixture();
  const fails = [];
  const inoperative = [];
  const leg = (id, desc, ok, detail) => {
    lines.push(`${ok ? 'PASS' : 'FAIL'} ${id} — ${desc}`);
    lines.push(`       ${detail}`);
    if (!ok) fails.push(id);
  };
  const legInoperative = (id, desc) => {
    lines.push(`INOPERATIVE ${id} — ${desc}`);
    lines.push('       INOPERATIVE — bwrap unavailable in this process');
    inoperative.push(id);
  };

  try {
    const leaderLogs = [];
    const leader = cageFor(f.leaderDir, leaderLogs);
    const refuserLogs = [];
    const refuser = cageFor(f.refuserDir, refuserLogs);
    const plainLogs = [];
    const plain = cageFor(f.plainDir, plainLogs);

    // ── COMPOSE LEGS — run in any process ──────────────────────────────────────────────────────
    leg('L1', 'the register (a goal SUBFOLDER) is bound READ-WRITE, AFTER the read-root ro floor',
      hasFlag(leader, '--bind', f.register) && leader.lastIndexOf(f.ws) < leader.lastIndexOf(f.register),
      `--bind ${f.register}: ${hasFlag(leader, '--bind', f.register)}; read-root flag index ${leader.lastIndexOf(f.ws)} < register index ${leader.lastIndexOf(f.register)}`);

    leg('L2', 'ZERO refusal log lines for the register entry (the cause: rule 3 used to refuse it every spawn)',
      refusals(leaderLogs).length === 0,
      `cli-write-roots refusals logged for the filer: ${JSON.stringify(refusals(leaderLogs).map((l) => l.message))}`);

    // L6 — each refused shape composes no opening of ITS OWN (the goal root `alpha` is bound by
    // the template's literal `bind:{goalDir}` line for EVERY seat of the goal, so the control is
    // the plain seat's count of the same flag, not zero) and carries a logged reason.
    const l6 = f.refused.map((r) => ({
      entry: r,
      logged: refusals(refuserLogs).some((l) => l.entry === r),
      extraBinds: bindCount(refuser, r) - bindCount(plain, r),
    }));
    leg('L6', 'the four refused shapes (goals root · a goal root · <goal>/coordination · <goal>/seats/x) still compose NOTHING, each refusal logged',
      l6.every((x) => x.logged && x.extraBinds === 0) && refusals(refuserLogs).length === 4,
      l6.map((x) => `${path.relative(f.ws, x.entry)}: logged=${x.logged} extra-binds=${x.extraBinds}`).join(' · ')
        + `; refusal lines: ${refusals(refuserLogs).length}; reasons: ${JSON.stringify(refusals(refuserLogs).map((l) => l.message.replace(f.ws, '<ws>')))}`);

    // ── EXEC LEGS — need bwrap to START in this process ────────────────────────────────────────
    const canary = inCage(f.leaderDir, leader, 'true');
    if (canary.exit !== 0) {
      lines.push(`bwrap canary: exit ${canary.exit} — ${(canary.stderr || '(no stderr)').split('\n')[0]}`);
      legInoperative('L3', 'the REAL filing CLI files from inside the cage → exit 0 AND exactly ONE new file in register/open/ (on disk, from outside)');
      legInoperative('L4', "an in-cage write to the engine goal's sessions.csv FAILS — bytes unchanged");
      legInoperative('L5', 'an in-cage write ONE LEVEL ABOVE the register FAILS — the opening is the register, not the goal folder');
    } else {
      const before = fs.readdirSync(f.openDir);
      const filing = inCage(f.leaderDir, leader,
        `cd ${f.leaderDir} && python3 ${FILE_ISSUE} file --surface ignite/x --class other --symptom x --evidence e `
        + '--suggested-action s --risk r --as alpha/leader --json');
      const after = fs.readdirSync(f.openDir);
      const fresh = after.filter((n) => !before.includes(n));
      leg('L3', 'the REAL filing CLI files from inside the cage → exit 0 AND exactly ONE new file in register/open/ (on disk, from outside)',
        filing.exit === 0 && before.length === 0 && after.length === 1 && fresh.length === 1 && fresh[0].endsWith('.md'),
        `in-cage exit ${filing.exit}; open/ before ${before.length} → after ${after.length}; new: ${JSON.stringify(fresh)}; `
          + `stdout ${JSON.stringify(filing.stdout.slice(0, 160))}${filing.stderr ? ` stderr ${JSON.stringify(filing.stderr.slice(0, 160))}` : ''}`);

      const beforeSessions = bytes(f.engineSessions);
      const w4 = inCage(f.leaderDir, leader, `echo "imposter,999,999,999" >> ${f.engineSessions}`);
      leg('L4', "an in-cage write to the engine goal's sessions.csv FAILS — bytes unchanged",
        bytes(f.engineSessions) === beforeSessions,
        `${bytes(f.engineSessions) === beforeSessions ? 'UNCHANGED' : 'CHANGED — WALL BREACHED'} (in-cage exit ${w4.exit}, not the evidence)`);

      const oneUp = path.join(f.engineGoal, 'escaped.txt');
      const w5 = inCage(f.leaderDir, leader, `echo reached > ${oneUp}`);
      leg('L5', 'an in-cage write ONE LEVEL ABOVE the register FAILS — the opening is the register, not the goal folder',
        !fs.existsSync(oneUp),
        `file created one level up: ${fs.existsSync(oneUp)} (in-cage exit ${w5.exit}, not the evidence)`);
    }

    lines.push('');
    if (fails.length > 0) {
      lines.push(`legs: FAILED -> ${fails.join(', ')}${inoperative.length ? ` (INOPERATIVE -> ${inoperative.join(', ')})` : ''}`);
      throw new Error(`register-door probe failed: ${fails.join(', ')}`);
    }
    if (inoperative.length > 0) {
      lines.push(`legs: compose legs PASS; INOPERATIVE -> ${inoperative.join(', ')} (bwrap unavailable in this process — the scheduled suite's uncaged run is the evidence)`);
      throw Object.assign(new Error(`exec legs not run: ${inoperative.join(', ')} — bwrap unavailable in this process`), { code: 'E_INOPERATIVE' });
    }
    lines.push('legs: ALL PASS');
  } finally {
    try { fs.rmSync(f.root, { recursive: true, force: true }); } catch {}
  }
});
