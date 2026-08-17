'use strict';

// ── live-session-design.md §1/§4 — the warm path, proven against a REAL harness ──────────────────
//
// The manager is daemon-side (`server/spawn/live-sessions.js`); this probe lives here because the
// warm path is a CHAT feature and its consumer is the bridge. It drives the real module: a real
// `claude-haiku` profile, a real seat folder under a real `.rbtv/goals/` tree, the real seat cage,
// the real `systemd-run --pipe` carriage. Nothing about the launch is stubbed — a stubbed launch
// would prove the FIFO and prove nothing about whether a live session can exist at all, which was
// the open question the design flagged as its first risk.
//
// ARMS
//   1  eligibility           — the four refusals and the one admission, from config + disk alone
//   2  warm turns, in order  — two feeds, the SECOND written MID-TURN, both answered, in order
//   3  accounting            — one sessions.csv row per live PROCESS; the transcript is teed
//   4  reaper                — an idle session is closed and its child exits
//   5  crash mid-turn        — the unit is killed under a live turn; the feed resolves
//                              `unanswered: true` so the caller can re-route rather than lose it
//   6  the wire              — `live-feed` through the REAL gateway + dispatch: an unknown
//                              conversation is a soft `{fed:false}`, an unknown field is refused
//   7  MUTATION              — the feed's stdin write is cut out of a COPY; arm 2 must go RED
//
// ⚠ The mutation arm is what makes the rest of this file evidence. A probe that cannot fail
// proves nothing, so arm 7 asserts the mutation ALTERED THE SOURCE first, then requires the
// mutated copy to fail the exact claim arm 2 makes.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { makeCapture, nowMs, sleep, startThrowawayDaemon } = require('./lib');

const OUT = path.join(__dirname, 'probe-chat-live-session.out');
const IGNITE = path.resolve(__dirname, '../../..');
const REAL_PROFILES = path.join(IGNITE, 'config', 'spawn-profiles.yaml');
const LIVE_MODULE = path.join(IGNITE, 'server', 'spawn', 'live-sessions.js');

const checks = [];
function check(name, pass, detail = {}) {
  checks.push({ name, pass: Boolean(pass), ...detail });
  return Boolean(pass);
}

// ── A scratch workspace: a canonical goal/seat tree + a config the manager can load ─────────────
//
// The profiles file is the REAL one with two keys overridden (`spawn.data_root`,
// `default_workdir_root`). Copying it rather than authoring a minimal one is deliberate: the cage
// template, the caps and the claude profiles under test are exactly what the live daemon runs, so
// this probe cannot pass against a cage the deployment does not use.
// The casts the fixtures declare. Since owner ruling D2 (2026-08-11) a seat's descriptor decides
// which profile runs it, so a probe drives `eligible()`'s gates by RE-CASTING the seat rather than
// by naming a different profile at the call — the caller's name no longer decides anything on a
// cast seat. `probe-nonclaude-with-resume` gained a `-m` pin for exactly this: a profile with no
// model pin cannot be cast TO, so without one the harness gate is unreachable through a cast.
const DEFAULT_CAST = 'harness: claude\nmodel: claude-sonnet-5\n';
const NONCLAUDE_CAST = 'harness: kimi\nmodel: probe-kimi-model\n';

function scratchWorkspace({ humanInteractive = true, cast = DEFAULT_CAST } = {}) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'p7-live-'));
  const ws = path.join(root, 'ws');
  const seatDir = path.join(ws, '.rbtv', 'goals', 'livegoal', 'seats', 'liveseat');
  fs.mkdirSync(seatDir, { recursive: true });
  // The seat cage ro-binds the goal package's `coordination/` dir; bwrap refuses a bind whose
  // source does not exist, so the package has to be shaped like a real one.
  fs.mkdirSync(path.join(ws, '.rbtv', 'goals', 'livegoal', 'coordination'), { recursive: true });
  fs.writeFileSync(path.join(ws, '.rbtv', 'goals', 'livegoal', 'seats', 'liveseat', 'seat.md'),
    // ⚑ CAST since owner ruling D2 (2026-08-11): `eligible()` resolves the seat's cast FIRST, because
  // the gates below it must reason about the profile that will actually run, not the one the caller
  // named. An uncast fixture therefore refuses with `uncastable-seat` and MASKS every gate this
  // file is about (harness, resume template, human-interactive). Casting it puts those gates back
  // in reach — the refusals asserted below are then the real ones.
  `---\nseat: liveseat\n${cast}${humanInteractive ? 'human-interactive: yes\n' : ''}fallback: park\n---\n\n`
    + 'Answer with the single word asked for and nothing else.\n');
  // sessions.csv with its header — the manager APPENDS by column name and refuses a headerless
  // file (seat-identity/csv.js), exactly as the dispatch door does.
  // ⚑ sessions.csv is the RUN PACKAGE's, at the goal root — not the seat's. That is where
  // `parseSeatPath` points the at-dispatch record, and the live manager writes to the same file.
  const sessionsCsv = path.join(ws, '.rbtv', 'goals', 'livegoal', 'sessions.csv');
  fs.writeFileSync(sessionsCsv, 'seat,session-id,harness,workdir,pid,pid-starttime,tty,worktree-path,started\n');

  const dataRoot = path.join(root, 'state');
  fs.mkdirSync(dataRoot, { recursive: true });

  let yamlText = fs.readFileSync(REAL_PROFILES, 'utf8');
  yamlText = yamlText.replace(/^(\s*)data_root:.*$/m, `$1data_root: ${dataRoot}`);
  yamlText = yamlText.replace(/^default_workdir_root:.*$/m, `default_workdir_root: ${path.join(ws, '.rbtv', 'goals')}`);
  // A SYNTHETIC non-claude profile that DOES carry a resume template. Without it the harness gate
  // is untestable from this config: every shipped non-claude profile is refused one gate earlier
  // (no `resume:`), so a `kimi` refusal would pass whether the harness gate existed or not — the
  // check would be vacuous. This profile makes the harness the ONLY thing left to refuse it.
  // ⚠ INJECTED INTO `launch-specs:` UNDER ITS OWN HARNESS KEY (7.787). It used to be appended
  // just before `tools:`, which was the end of the flat `profiles:` map; that slot is the
  // name-keyed `jobs:` block now, and a `jobs:` entry can never be CAST to — the arm would go
  // vacuous in the one direction it exists to measure. The key is the pair, and it agrees with the
  // `-m` pin in the argv (`profiles.js#validateSpecKey`).
  // Appended INSIDE the existing `kimi:` harness block rather than as a second one — a duplicate
  // mapping key is a YAML parse error, and the shipped config already declares that harness.
  yamlText = yamlText.replace(/^(  kimi:\n)/m,
    '$1    probe-kimi-model:\n'
    + '      exec:\n'
    + '        argv: ["kimi", "--quiet", "-m", "probe-kimi-model", "--work-dir", "{workdir}"]\n'
    + '        prompt: stdin\n'
    + '      resume:\n'
    + '        argv: ["kimi", "--quiet", "-m", "probe-kimi-model", "--resume", "{session_ref}"]\n'
    + '        prompt: stdin\n'
    + '      session_ref: { source: assigned }\n'
    + '      toolset_ceiling: full\n'
    + '      workdir_root: .rbtv/goals\n');
  const configPath = path.join(root, 'spawn-profiles.yaml');
  fs.writeFileSync(configPath, yamlText);

  return { root, ws, seatDir, dataRoot, configPath, sessionsCsv, cleanup: () => { try { fs.rmSync(root, { recursive: true, force: true }); } catch {} } };
}

// ⚑ A LIVE SESSION IS A `--resume`, so a chain must EXIST before one can be warmed. This seeds
// what a cold first turn leaves behind: one real claude session, at the seat's own workdir, under
// the id the chain's `session_ref` will carry. Measured, not assumed — resuming an id that does
// not exist ends the turn `is_error` with `No conversation found with session ID: …`, which is
// exactly the case the manager now reports as NOT answered.
function seedChain(seatDir, sessionRef) {
  execFileSync('claude', [
    '-p', '--session-id', sessionRef, '--model', 'claude-haiku-4-5',
    '--permission-mode', 'bypassPermissions',
    'I am working on a module named delta-parser. Reply with just: OK',
  ], { cwd: seatDir, encoding: 'utf8', timeout: 180000 });
}

function unitAlive(unitName) {
  try {
    execFileSync('systemctl', ['--user', 'is-active', unitName], { stdio: 'ignore', timeout: 10000 });
    return true;
  } catch { return false;
  }
}

async function main() {
  const cap = makeCapture(OUT);
  const t0 = nowMs();
  const skipped = [];
  let daemon = null;
  const cleanups = [];

  try {
    // ── ARM 1 — eligibility, with each refusal PAIRED against the admission ────────────────────
    {
      const w = scratchWorkspace({ humanInteractive: true });
      cleanups.push(w.cleanup);
      const { createLiveSessions } = require(LIVE_MODULE);
      const mgr = createLiveSessions({ configPath: w.configPath, workspaceRoot: w.ws, reapPollMs: 3600000 });
      cleanups.push(() => mgr.stop());

      const admitted = mgr.eligible({ workdir: w.seatDir });
      check('arm1: a claude profile at a human-interactive seat is ELIGIBLE', admitted.ok === true, { got: admitted });

      // The discriminating pair for the HARNESS gate: same seat, same resume template, only the
      // harness differs. `--input-format stream-json` is claude's flag and no other harness's
      // equivalent has been MEASURED, so a non-claude profile is ineligible rather than guessed at.
      // ⚑ EVERY GATE BELOW IS DRIVEN THROUGH THE SEAT'S CAST, not the caller's profile name
      // (owner ruling D2, 2026-08-11). `eligible()` resolves the cast FIRST — it must, or it would
      // answer about a profile that is not the one going to run — so on a CAST seat the caller's
      // profile decides nothing and passing a kimi or a nonexistent name here would prove nothing.
      // These arms therefore RE-CAST the seat and keep passing the same caller profile, which is
      // also what makes them discriminating: the only thing that changes is the descriptor.
      const nonClaudeSeat = scratchWorkspace({ humanInteractive: true, cast: NONCLAUDE_CAST });
      cleanups.push(nonClaudeSeat.cleanup);
      const mgrNc = createLiveSessions({ configPath: nonClaudeSeat.configPath, workspaceRoot: nonClaudeSeat.ws, reapPollMs: 3600000 });
      cleanups.push(() => mgrNc.stop());
      const nonClaude = mgrNc.eligible({ workdir: nonClaudeSeat.seatDir });
      check('arm1: a seat CAST to a non-claude harness whose profile HAS a resume template is refused, ON THE HARNESS',
        nonClaude.ok === false && /harness-not-live-capable/.test(nonClaude.reason), { got: nonClaude });

      // …and a seat cast to a pair NO profile carries is refused earlier still, by the cast itself.
      const badCast = scratchWorkspace({ humanInteractive: true, cast: 'harness: claude\nmodel: no-such-model-5\n' });
      cleanups.push(badCast.cleanup);
      const mgrBad = createLiveSessions({ configPath: badCast.configPath, workspaceRoot: badCast.ws, reapPollMs: 3600000 });
      cleanups.push(() => mgrBad.stop());
      const unmapped = mgrBad.eligible({ workdir: badCast.seatDir });
      check('arm1: a seat cast to a pair no profile carries is refused AT THE CAST',
        unmapped.ok === false && /uncastable-seat/.test(unmapped.reason), { got: unmapped });

      // ⚠ AN UNCAST SEAT IS REFUSED OUTRIGHT (7.787), and the arm inverted with the ruling. It
      // used to assert that an uncast seat fell through to the CALLER'S profile name and was
      // refused there when the name was unknown — the `unknown-profile` reason, which was the last
      // place a transport's value decided anything. `#d-abolish-profile-names` deleted the caller's
      // name from this door entirely, so an uncast seat has nothing to fall back to and the
      // refusal is the cast's own. It still pairs with the two above: cast seat → the descriptor
      // decides; uncast seat → nothing decides, so nothing runs.
      const uncast = scratchWorkspace({ humanInteractive: true, cast: '' });
      cleanups.push(uncast.cleanup);
      const mgrUncast = createLiveSessions({ configPath: uncast.configPath, workspaceRoot: uncast.ws, reapPollMs: 3600000 });
      cleanups.push(() => mgrUncast.stop());
      const unknown = mgrUncast.eligible({ workdir: uncast.seatDir });
      check('arm1: an UNCAST seat is refused AT THE CAST — there is no caller name left to fall back to',
        unknown.ok === false && unknown.reason === 'uncastable-seat:E_UNCAST_SEAT', { got: unknown });

      // The SAME profile at a seat that does not declare the flag — the discriminator is the
      // seat, not the profile, so the pair is what proves gate 1 is read at all.
      const w2 = scratchWorkspace({ humanInteractive: false });
      cleanups.push(w2.cleanup);
      const mgr2 = createLiveSessions({ configPath: w2.configPath, workspaceRoot: w2.ws, reapPollMs: 3600000 });
      cleanups.push(() => mgr2.stop());
      const notDeclared = mgr2.eligible({ workdir: w2.seatDir });
      check('arm1: the SAME profile at a seat with no `human-interactive:` is refused (gate 1 is the seat\'s declaration)',
        notDeclared.ok === false && notDeclared.reason === 'seat-not-human-interactive', { got: notDeclared });

      // Gate 1 is scoped to the FRONTMATTER: a body line quoting the flag must not open it.
      const { seatIsHumanInteractive } = require(LIVE_MODULE);
      const bodyOnly = path.join(w2.root, 'bodyseat');
      fs.mkdirSync(bodyOnly, { recursive: true });
      fs.writeFileSync(path.join(bodyOnly, 'seat.md'), '---\nseat: x\nharness: claude\nmodel: claude-sonnet-5\n---\n\nhuman-interactive: yes\n');
      check('arm1: `human-interactive: yes` in the BODY does NOT open gate 1', seatIsHumanInteractive(bodyOnly) === false);
      check('arm1: control — the same line in the FRONTMATTER does', seatIsHumanInteractive(w.seatDir) === true);
    }

    // ── ARMS 2/3/4/5 — a REAL live session ────────────────────────────────────────────────────
    const w = scratchWorkspace({ humanInteractive: true });
    cleanups.push(w.cleanup);
    const { createLiveSessions } = require(LIVE_MODULE);
    const mgr = createLiveSessions({
      configPath: w.configPath,
      workspaceRoot: w.ws,
      logger: (m) => cap.log({ mgr: m.message, level: m.level, ...m }),
      idleMs: 3600000,
      turnTimeoutMs: 120000,
      reapPollMs: 3600000,
    });
    cleanups.push(() => mgr.stop());

    // `sessionRef` is a fresh uuid: a live session RESUMES a chain, and claude treats a `--resume`
    // of an unknown id as a new session with that id — which is exactly the shape of a chain whose
    // first cold turn has run. The probe does not need a real cold turn to prove the feed.
    const sessionRef = require('node:crypto').randomUUID();
    const conv = 'C-PROBE:1';
    seedChain(w.seatDir, sessionRef);

    const t1 = nowMs();
    // Turn 1 asks for the word the SEEDED cold turn was told — so a pass proves the warm session
    // is a CONTINUATION of the chain, not a fresh process wearing its id. Continuity across the
    // cold→warm boundary is the design's whole claim; asserting only that a reply arrived would
    // pass on a session that had forgotten everything.
    const p1 = mgr.feed({ conversationId: conv, workdir: w.seatDir, prompt: 'What is the name of the module I mentioned? Reply with only the module name.', sessionRef, start: true });

    // ⚑ THE MID-TURN FEED — written while turn 1 is still running, which is the case the design
    // flagged as unverified. The spike measured the CLI QUEUEING it (2026-08-10, claude 2.1.226);
    // this arm is that measurement held as a standing assertion against the real module.
    await sleep(2500);
    const midTurnState = mgr.list()[0];
    const t2 = nowMs();
    const p2 = mgr.feed({ conversationId: conv, workdir: w.seatDir, prompt: 'What is 12 minus 5? Reply with only the number.', sessionRef, start: true });

    const r1 = await p1;
    const r2 = await p2;

    check('arm2: turn 1 was answered by the warm session', r1.ok === true, { reply: r1.reply, ms: r1.ms, reason: r1.reason });
    check('arm2: turn 2 — WRITTEN MID-TURN — was also answered', r2.ok === true, { reply: r2.reply, ms: r2.ms, reason: r2.reason });
    check('arm2: the warm session CONTINUED the seeded cold chain (it knows the word from the turn before it existed)',
      r1.ok && /delta-parser/i.test(r1.reply || ''), { reply: r1.reply });
    check('arm2: the answers arrived IN ORDER (the chain answer first, the mid-turn arithmetic second)',
      r1.ok && r2.ok && /delta-parser/i.test(r1.reply || '') && /\b7\b/.test(r2.reply || ''),
      { first: r1.reply, second: r2.reply });
    check('arm2: the mid-turn feed found the session already in-turn (so it really was mid-turn, not after)',
      midTurnState && midTurnState.state === 'in-turn', { midTurnState });
    check('arm2: ONE process served BOTH turns (the warm path, not two cold spawns)',
      r1.sessionId && r1.sessionId === r2.sessionId, { first: r1.sessionId, second: r2.sessionId });
    // ⚠ turn2Ms IS NOT A WARM FIGURE. `ms` is stamped inside feed()'s executor, but turn 2 is fed
    // mid-turn, so its result cannot arrive until turn 1's has: turn2Ms = (remaining turn 1) +
    // (turn 2's own work). Measured once: turn1 3449, feedGap 2555, turn2 2584 — of which 894 was
    // spent waiting out turn 1. Reading turn2Ms as warm-path latency reads ~35% queue wait.
    cap.log({ step: 'warm turn latency', turn1Ms: r1.ms, turn2Ms: r2.ms, feedGapMs: t2 - t1, note: 'turn1 includes the live launch; turn2 CARRIES THE QUEUE WAIT for turn1 — not a warm figure' });

    // ── ARM 3 — accounting ────────────────────────────────────────────────────────────────────
    {
      const csv = fs.readFileSync(w.sessionsCsv, 'utf8').trim().split('\n');
      const rows = csv.slice(1).filter(Boolean);
      check('arm3: exactly ONE sessions.csv row per live PROCESS — not one per turn', rows.length === 1, { rows });
      check('arm3: the row carries this live session\'s id and its seat', rows[0] && rows[0].includes(r1.sessionId) && rows[0].startsWith('liveseat,'), { row: rows[0] });
      const logPath = path.join(w.dataRoot, 'logs', `${r1.sessionId}.log`);
      const transcript = fs.existsSync(logPath) ? fs.readFileSync(logPath, 'utf8') : '';
      check('arm3: the stream-json transcript is TEED to logs/<session-id>.log (so `inspect logs` still reads it)',
        transcript.includes('"type":"result"') && /delta-parser/i.test(transcript), { bytes: transcript.length, path: logPath });
      check('arm3: the transcript holds BOTH turns\' results', (transcript.match(/"type":"result"/g) || []).length >= 2,
        { results: (transcript.match(/"type":"result"/g) || []).length });
    }

    // ── ARM 4 — the reaper ────────────────────────────────────────────────────────────────────
    {
      const before = mgr.list()[0];
      const mgrIdle = mgr;
      // ⚑ THE UNIT NAME IS ASSERTED BEFORE IT IS USED, because getting it wrong INVERTS the
      // orphan check below into a green. `list()` is a hand-written snake_case projection: rename
      // or drop `session_id` there (or change the unit-name shape in `carrier.js`) and the derived
      // name points at a unit that never existed — `is-active` fails on the first iteration,
      // `gone` is true, and the probe reports "no orphan left behind" while a real worker unit is
      // orphaned after every reap. The session answered two turns moments ago, so its unit is
      // alive right here by construction; a name that resolves to no live unit is a broken name,
      // and this fails loudly on it instead of manufacturing the pass below.
      const unit = `rbtv-worker-${before && before.session_id}.service`;
      check('arm4: the live session\'s unit name is derivable from `list()` AND names a LIVE unit before the reap (a wrong name would manufacture the pass below)',
        Boolean(before && before.session_id) && unitAlive(unit), { unit, before });
      // Reaping is asked of the manager directly rather than waited out: the window is 10 minutes
      // by design and a probe that slept it would be a probe nobody runs.
      const reaped = mgrIdle.reapAll('probe-reap');
      check('arm4: the reaper closed the live session', reaped === 1 && mgr.size() === 0, { reaped, size: mgr.size() });
      // The child gets EOF and exits; the unit goes with it (`--collect`).
      let gone = false;
      for (let i = 0; i < 40 && !gone; i += 1) { await sleep(250); gone = !unitAlive(unit); }
      check('arm4: the child process actually EXITED on stdin close — no orphan unit left behind',
        gone, { unit });
    }

    // ── ARM 5 — a crash mid-turn must not swallow the owner's message ──────────────────────────
    {
      const conv2 = 'C-PROBE:crash';
      const ref2 = require('node:crypto').randomUUID();
      seedChain(w.seatDir, ref2);
      const pending = mgr.feed({ conversationId: conv2, workdir: w.seatDir, prompt: 'Write 500 words about the colour blue.', sessionRef: ref2, start: true });
      await sleep(4000);
      const live = mgr.list()[0];
      if (!live) {
        skipped.push('arm5: the session was not up in time to be killed mid-turn');
      } else {
        try { execFileSync('systemctl', ['--user', 'kill', '--signal=SIGKILL', `rbtv-worker-${live.session_id}.service`], { stdio: 'ignore', timeout: 10000 }); } catch {}
        const res = await pending;
        check('arm5: a session killed MID-TURN resolves the fed turn rather than hanging', res && res.ok === false, { got: res });
        check('arm5: it is marked `unanswered` — the caller MUST re-route it, never drop it',
          res && res.unanswered === true, { got: res });
        check('arm5: the dead session is cleared from the registry, so the next message takes the cold path',
          mgr.size() === 0, { size: mgr.size() });
      }
    }

    // ── ARM 6 — the wire: `live-feed` through the REAL gateway + internal API ──────────────────
    {
      daemon = await startThrowawayDaemon({ liveSessions: mgr });
      const call = async (payload) => {
        const res = await fetch(`http://${daemon.gatewayAddr}/`, {
          method: 'POST',
          headers: { 'content-type': 'application/json', authorization: `Bearer ${daemon.bridgeToken}` },
          body: JSON.stringify({ intent: 'live-feed', payload }),
        });
        return { status: res.status, body: await res.json() };
      };

      const cold = await call({ conversation: 'C-NOT-WARM:1', prompt: 'hello', start: false });
      check('arm6: a BRIDGE token reaches `live-feed` (the same door `enqueue-job` is open on)',
        cold.body && cold.body.ok === true, { got: cold });
      check('arm6: a conversation with no warm session is a SOFT refusal, never an error — the caller takes the cold path',
        cold.body && cold.body.ok === true && cold.body.result && cold.body.result.fed === false && cold.body.result.reason === 'no-warm-session',
        { got: cold.body && cold.body.result });

      const bogus = await call({ conversation: 'C:1', prompt: 'x', profile: 'claude-haiku', session_ref: 'FORGED' });
      check('arm6: `session_ref` is NOT a wire field — a sender cannot name the session to resume',
        bogus.body && bogus.body.ok === false, { got: bogus.body && bogus.body.error });

      const empty = await call({ conversation: 'C:1', prompt: '', profile: 'claude-haiku' });
      check('arm6: an empty prompt is refused at the door', empty.body && empty.body.ok === false, { got: empty.body && empty.body.error });
    }

    // ── ARM 7 — MUTATION: cut the feed, arm 2 must go RED ──────────────────────────────────────
    {
      const src = fs.readFileSync(LIVE_MODULE, 'utf8');
      const target = 's.child.stdin.write(line);';
      if (!src.includes(target)) {
        check('arm7: the mutation target still exists in the source', false, { target });
      } else {
        const mutated = src.replace(target, 'void line;');
        check('arm7: the mutation ALTERED the source (a no-op mutation proves nothing)', mutated !== src);
        const mutPath = path.join(w.root, 'live-sessions.MUTANT.js');
        fs.writeFileSync(mutPath, mutated);
        // Required from its ORIGINAL directory so its relative requires resolve — a copy beside
        // the original, deleted with the scratch tree.
        const beside = path.join(IGNITE, 'server', 'spawn', `live-sessions.MUTANT-${process.pid}.js`);
        fs.writeFileSync(beside, mutated);
        cleanups.push(() => { try { fs.unlinkSync(beside); } catch {} });
        const { createLiveSessions: mutantFactory } = require(beside);
        const mut = mutantFactory({ configPath: w.configPath, workspaceRoot: w.ws, idleMs: 3600000, turnTimeoutMs: 20000, reapPollMs: 3600000 });
        cleanups.push(() => mut.stop());
        const mutRef = require('node:crypto').randomUUID();
        seedChain(w.seatDir, mutRef);
        const res = await mut.feed({ conversationId: 'C-MUT:1', workdir: w.seatDir, prompt: 'What is the name of the module I mentioned? Reply with only the module name.', sessionRef: mutRef, start: true });
        check('arm7: with the stdin write cut out, the SAME feed that arm 2 answers is NOT answered — the probe can fail',
          res && res.ok === false, { got: res });
      }
    }
  } catch (err) {
    check('probe ran to completion without throwing', false, { error: err.message, stack: (err.stack || '').split('\n').slice(0, 6) });
  } finally {
    if (daemon) { try { await daemon.close(); } catch {} }
    for (const c of cleanups.reverse()) { try { c(); } catch {} }
  }

  const failed = checks.filter((c) => !c.pass);
  cap.log({ step: 'checks', total: checks.length, failed: failed.length, checks });
  if (skipped.length) cap.log({ step: 'skipped', skipped });
  const pass = failed.length === 0 && checks.length > 0;
  const wallMs = nowMs() - t0;
  const exit = pass ? 0 : 1;
  cap.flush({ probe: 'probe-chat-live-session', pass, EXIT: exit, WALL_MS: wallMs, CHECK_COUNT: checks.length, SKIPPED_COUNT: skipped.length });
  process.stdout.write(`PROBE probe-chat-live-session EXIT=${exit} WALL_MS=${wallMs} PASS=${pass} CHECKS=${checks.length} FAILED=${failed.length}\n`);
  process.exit(exit);
}

main();
