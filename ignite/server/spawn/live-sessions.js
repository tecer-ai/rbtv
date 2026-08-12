'use strict';

// ── THE LIVE SESSION MANAGER (live-session-design.md §1, ruled 2026-08-10) ──────────────────────
//
// A warm harness process per active chat thread, fed over stdin, answering in ~1/5 of the cold
// path's wall time. It exists to remove the three costs a one-shot turn pays that have nothing to
// do with thinking: the queue+tick decision (~1s), process creation (systemd-run + bwrap + CLI
// boot, 2.75s) and the reply-leg poll (1.5s).
//
// ⚑ IT LIVES DAEMON-SIDE, AND THAT IS MEASURED, NOT PREFERRED. The design sketch offered the chat
// bridge as an alternative home. The bridge CANNOT be it: `probe-chat-boundary` scans every
// runtime `.js` under `bridges/chat/` for `child_process|\bspawn\s*\(` and fails the suite on a
// hit — the bridge's "no spawn path" invariant (chat-bridge-spec.md Behavior #5) is enforced
// structurally, not by discipline. A bridge-side manager would also have to re-implement the seat
// cage, the carrier, the profile resolution and the at-dispatch record, which is the second
// implementation PRIN-11 exists to prevent. So the manager sits here, beside the spawn path whose
// composition it reuses, and the bridge reaches it through ONE loopback gateway call.
//
// ⚑ EVERY LIVE SESSION IS A `--resume`, NEVER A FRESH `exec`. This is what makes the fallback in
// the design's §1 true rather than hopeful. The FIRST message of a conversation always takes
// today's cold path unchanged; warmth is started afterwards by resuming THAT turn's `session_ref`.
// Because `session_ref: { source: assigned }` and a resumed claude session keeps its own id, the
// chain's ref is ONE value for the chain's whole life — so a reaped live session and the cold
// `--resume` spawn that replaces it are the same conversation, and continuity survives the reaper
// by construction instead of by a hand-off nobody would maintain.
//
// ⚑ WHAT IT DOES NOT DO: it writes no queue row and no `jobs_log` execution row. A live session
// bypasses the queue BY RULING (§4 direct feed), so minting an execution row for it would be
// inventing a queue row that never existed — a false record, not a whole one. The records it does
// keep are exactly the two the design names: ONE `sessions.csv` sitting row per live PROCESS
// (spawn→exit), written by the same writer the dispatch door uses, and the per-turn events in the
// session's own stream-json transcript, teed to the same `logs/<session-id>.log` every other
// session writes. See README/`live-session-design.md` § Accounting for why §4's separate
// fire-and-forget event collapsed to zero code once the manager moved daemon-side.

const fs = require('node:fs');
const path = require('node:path');
const { spawn: childSpawn } = require('node:child_process');

const { loadConfig, resolveWorkdir, resolveWorkspaceRoot } = require('./config');
const { harnessOf, materializeHarnessConfig, planCagedSettings, materializeCagedSettings } = require('./harness-config');
const { buildBwrapArgv } = require('./bwrap');
// `resolveSandbox`/`ensureLogPath` are IMPORTED (7.637). Copies of both stood here only because
// `spawn.js` was another session's dirty file at build time. A live session's cage and its
// transcript mode ARE the dispatch door's — now inexpressibly so, rather than by discipline.
const { composeArgv, composeCageFor, exitFilePath, resolveSandbox, ensureLogPath, launchSpecForSeat } = require('./spawn');
const { generateSessionId, selectCarrier, buildSystemdRunArgs, ensureDir } = require('./carrier');
const { parseSeatPath, parseServiceSeatPath } = require('../seat-identity/seat-folder');
const { appendRow } = require('../seat-identity/csv');
const { SpawnError, E_UNKNOWN_LAUNCH_SPEC, E_BAD_REQUEST, E_CARRIER_FAILED } = require('./errors');

// The design's defaults (owner-confirmed 2026-08-10, live-session-design.md § Deploy policy).
const DEFAULT_IDLE_MS = 600000; // 10 minutes after the LAST OWNER MESSAGE, not the last reply
const DEFAULT_MAX = 4;          // LRU cap — 240-600MB per warm process on an 8GB box
const DEFAULT_TURN_TIMEOUT_MS = 300000;

// ⚑ THE ONE HARNESS THIS IS BUILT FOR, AND THE REFUSAL IS THE POINT. `--input-format stream-json`
// is claude's flag. codex, kimi and opencode each have their own answer or none, and GUESSING one
// would put unverified launch knowledge in this file — the same reason `composeArgv` gates
// `--append-system-prompt-file` on the harness rather than emitting it hopefully. A non-claude
// profile is not broken here: it is INELIGIBLE, and its traffic takes the cold path untouched.
const LIVE_HARNESSES = new Set(['claude']);
const LIVE_INPUT_FLAGS = ['--input-format', 'stream-json'];

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// ── Gate 1 of eligibility: the seat DECLARES it talks to a human ────────────────────────────────
//
// `human-interactive: yes|true` in the seat's OWN `seat.md` frontmatter — and the READER is the
// ferry's, IMPORTED, not a second copy (owner ruling `#d-d3-dedupe-rescope`). The copy that stood
// here was the PRE-a6bb05d regex: it had already resurrected the blind spot F3 closed in the ferry
// — `human-interactive: "yes"` and `human-interactive: yes # ratified …` are both TRUE to the
// `yaml.safe_load` that `component-lint` validates the seat with, and were FALSE to the copy. Two
// readers of one file free to disagree is a defect with no reporting surface, which is why there is
// now one implementation of the predicate and this is not it.
//
// ⚑ THE REQUIRE IS LAZY, AT THE CALL, and that is the same shape `engine/attached-execution.js`
// uses for the same two gates: the bridge is a relocatable subtree, so the daemon holds no LOAD-time
// dependency on it (ignite/CLAUDE.md's relocatable-subtree convention runs in both directions).
//
// ⚑ THE IMPORT IS THE SEAT-DIR CORE, NOT THE `(goalDir, seat)` WRAPPER, and the difference is the
// whole warm path. A `workdir` here is the seat's OWN folder; splitting it back into a goal dir and
// a name to feed the wrapper assumes a `seats/<seat>/` layer, which a STANDING-SEAT HOME does not
// have (`materialize-seats.py#standing_seat`, `r-master-seat-homes`) — `_channel-master` IS the
// seat folder. That split read `.rbtv/seats/_channel-master/seat.md`, which does not exist, so the
// one seat the warm path was built for went ineligible SILENTLY (every ineligibility falls through
// to the cold path by design). Task 7.642.
function seatIsHumanInteractive(seatDir) {
  const { seatDirIsHumanInteractive } = require('../../bridges/chat/bus-ferry');
  return seatDirIsHumanInteractive(path.resolve(seatDir));
}

function createLiveSessions({
  configPath,
  workspaceRoot = null,
  logger = null,
  idleMs = DEFAULT_IDLE_MS,
  maxSessions = DEFAULT_MAX,
  turnTimeoutMs = DEFAULT_TURN_TIMEOUT_MS,
  userManager = true,
  reapPollMs = 30000,
} = {}) {
  const config = loadConfig(configPath);
  const dataRoot = config.spawn && config.spawn.data_root;
  if (!dataRoot) throw new SpawnError(E_BAD_REQUEST, 'spawn.data_root is required for live sessions', { key: 'spawn.data_root' });

  const gatewayAddr = `${process.env.RBTV_IGNITE_BIND_HOST || config.bind?.host || '127.0.0.1'}:`
    + `${Number(process.env.RBTV_IGNITE_BIND_PORT || config.bind?.port) || 7431}`;

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, component: 'live-sessions', ...extra });
  }

  // conversation-id → live session. A plain Map, and its INSERTION ORDER is the LRU: `touch()`
  // deletes and re-sets, so the first key is always the least recently fed. No heap, no clock
  // comparison — the data structure already answers the question the cap asks.
  const sessions = new Map();

  function touch(id, s) {
    sessions.delete(id);
    sessions.set(id, s);
  }

  // ── Eligibility — asked BEFORE anything is spawned, and answerable from config + disk alone ────
  //
  // ⚑ IT ASKS ABOUT THE PROFILE THE SEAT IS CAST AS, not the one the caller named — the same
  // resolution `launch()` performs a few lines below, and it MUST be the same or this gate answers
  // about a different profile than the one that will run. Concretely: the caller names a profile
  // that declares a `resume:` template, the seat is cast as one that does not, and a gate reading
  // the caller's value says "warm, go" straight into a `launch()` that then throws
  // E_UNKNOWN_MODE. Resolving here makes the refusal `profile-has-no-resume-template` — routine,
  // and the caller falls through to the cold path exactly as it does for every other ineligible
  // reason. (No profile is NAMED here on purpose: `probe-caged-settings` holds a standing "no
  // per-profile special case anywhere in server/spawn/" invariant, and a literal in a comment
  // reads to it exactly like a literal in a branch — correctly, since both are profile knowledge
  // on the spawn path. The names live in `launch-profiles/`, which is where they belong.)
  //
  // An UNCAST seat throws E_UNCAST_SEAT out of the resolver (ruling D2). Caught and reported as an
  // ineligible reason rather than propagated: this gate's whole contract is that it answers, and
  // the cold path the caller falls through to raises the same refusal where it can be acted on.
  function eligible({ workdir }) {
    if (!workdir) return { ok: false, reason: 'no-workdir' };
    let profile;
    try {
      ({ spec: profile } = launchSpecForSeat(config.launchSpecs || {}, workdir, log));
    } catch (err) {
      return { ok: false, reason: `uncastable-seat:${err.code || 'unknown'}` };
    }
    if (!profile.resume) return { ok: false, reason: 'profile-has-no-resume-template' };
    const harness = harnessOf(profile);
    if (!LIVE_HARNESSES.has(harness)) return { ok: false, reason: `harness-not-live-capable:${harness || 'unknown'}` };
    if (!seatIsHumanInteractive(workdir)) return { ok: false, reason: 'seat-not-human-interactive' };
    return { ok: true, harness };
  }

  // ── The launch ────────────────────────────────────────────────────────────────────────────────
  //
  // Composition is the DISPATCH DOOR'S, reused wholesale: `composeArgv` (which resolves the
  // profile's resume template and appends the seat descriptor), `composeCageFor` (the seat cage)
  // and `buildBwrapArgv` (the FS walls). The ONLY additions are `--input-format stream-json` and
  // live-pipe carriage. Nothing about the cage, the caps or the writable set is relaxed for a live
  // session — a warm process is the same session, held open.
  function launch({ conversationId, workdir, sessionRef }) {
    // ── THE SEAT'S CAST WINS HERE TOO (launch-cast unification, owner-ruled 2026-08-11) ────────
    //
    // This door did not apply it, and `catalog.js`'s own header claimed it did — "`spawn()` is
    // downstream of the ticker, the chat bridge, the daemon lane, the attached lane and THE WARM-
    // SESSION LEG alike". That sentence was false for this file: `launch()` never calls `spawn()`,
    // it reuses only its composers. So the first message of a Slack thread ran the seat's cast and
    // every message after it ran whatever the transport named, on the same seat, in the same
    // thread — the exact "two different agents wearing one thread" that `forward-path.js` exports
    // `profileFor` to prevent. Measured on `plan-interviewer` 2026-08-11: it ran a different model
    // than its descriptor cast it as, on every Slack turn. (Neither model is NAMED here — see the
    // eligibility gate's note on `probe-caged-settings`'s no-profile-knowledge invariant.)
    //
    // Read off the RAW `workdir`, before `resolveWorkdir` normalizes it — the same ordering and
    // the same stated ceiling as `spawn()`: a relative workdir resolves no descriptor, so it
    // cannot be cast, and under ruling D2 it now REFUSES rather than running the caller's profile.
    const { key: profileName, spec: profile } = launchSpecForSeat(config.launchSpecs || {}, workdir, log);
    if (!sessionRef) throw new SpawnError(E_BAD_REQUEST, 'a live session RESUMES a chain and therefore requires its session_ref', { profile: profileName });

    // The workspace root resolves a profile's WORKSPACE-RELATIVE `workdir_root` (e.g. `.rbtv/
    // goals`). Injected rather than derived: `spawn.js` derives it from the heart store's own
    // path, and this module deliberately holds no store handle.
    const resolvedWorkdir = resolveWorkdir(profile, workdir, config.default_workdir_root, configPath, { execId: conversationId, workspaceRoot });
    const seat = parseSeatPath(resolvedWorkdir) || parseServiceSeatPath(resolvedWorkdir);
    if (!seat) {
      throw new SpawnError(E_BAD_REQUEST, `REFUSING SEATLESS LIVE SESSION: ${resolvedWorkdir} is not a canonical seat folder`, { workdir: resolvedWorkdir, profile: profileName });
    }

    // The session id a live process OWNS is the chain's ref: resuming keeps the id, so the warm
    // process and every cold turn before and after it are ONE claude session on disk. `sessionId`
    // below is this PROCESS's identity (log file, unit name, sessions.csv row) and is deliberately
    // a different value — one conversation can burn several live processes over its life.
    const sessionId = generateSessionId();
    const logPath = ensureLogPath(dataRoot, sessionId);

    // `prompt` is '' and the returned `stdinFile` is DISCARDED: a live session's prompt does not
    // ride a file, it rides the pipe. composeArgv still writes the (empty) prompt file because the
    // profile declares `prompt: stdin` carriage; that is a harmless 0-byte artifact and NOT worth
    // a branch in the shared composer, which the dispatch door depends on.
    const composed = composeArgv(profile, 'headless', sessionId, resolvedWorkdir, '', dataRoot, sessionRef, null, profileName);
    const argv = [...composed.argv, ...LIVE_INPUT_FLAGS];

    const resolvedSandbox = resolveSandbox(profile.sandbox, resolvedWorkdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== resolvedWorkdir);
    })();
    try {
      materializeHarnessConfig({ sessionDir: resolvedWorkdir, profile, editablePaths });
    } catch (err) {
      log('warn', 'harness config materialization failed (advisory layer; the kernel cage is authoritative)', { error: err.message });
    }
    const settings = planCagedSettings(argv, resolvedWorkdir);
    materializeCagedSettings(settings.copies);

    const maskPaths = config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [];
    const seatCage = composeCageFor(resolvedSandbox, seat, resolvedWorkdir, gatewayAddr, (l, m, e) => log(l, m, e));
    const wrappedArgv = buildBwrapArgv({
      argv: settings.argv,
      workdir: resolvedWorkdir,
      editablePaths,
      harness: harnessOf(profile),
      maskPaths,
      seatBinds: seatCage,
    });

    const carrier = selectCarrier(config.spawn.carrier, userManager);
    if (carrier !== 'systemd') {
      throw new SpawnError(E_CARRIER_FAILED, `live sessions require the systemd carrier (containment is non-negotiable, D48); this host selected ${carrier}`, { carrier });
    }
    const { args, unitName } = buildSystemdRunArgs({
      sessionId,
      argv: wrappedArgv,
      workdir: resolvedWorkdir,
      logPath,
      stdinFile: null,
      exitFile: exitFilePath(dataRoot, sessionId),
      caps: profile.caps,
      sandbox: resolvedSandbox,
      envFile: profile.env?.file,
      userManager,
      live: true,
    });
    ensureDir(path.dirname(exitFilePath(dataRoot, sessionId)));

    log('info', 'live session launching', { conversationId, profile: profileName, unitName, sessionId, sessionRef, workdir: resolvedWorkdir });
    const child = childSpawn('systemd-run', args, { stdio: ['pipe', 'pipe', 'pipe'] });

    const s = {
      conversationId,
      child,
      unitName,
      sessionId,
      sessionRef,
      profileName,
      workdir: resolvedWorkdir,
      seat,
      harness: harnessOf(profile),
      startedAt: Date.now(),
      lastOwnerMsgAt: Date.now(),
      state: 'idle',
      // The FIFO of un-answered fed turns. The CLI QUEUES a mid-turn message (spike, 2026-08-10:
      // a message written 3.0s into a 15.8s turn was answered 3.3s after that turn ended, in
      // order, with no error), so this is a RESPONDER queue, never a send queue: everything is
      // written to stdin immediately and `result` events are matched to waiters in arrival order.
      waiting: [],
      buf: '',
      turns: 0,
      logStream: fs.createWriteStream(logPath, { flags: 'a', mode: 0o600 }),
      logPath,
      dead: false,
    };

    child.stdout.on('data', (d) => onStdout(s, d));
    child.stderr.on('data', (d) => { try { s.logStream.write(d); } catch {} });
    child.on('error', (err) => finish(s, `carrier-error:${err.message}`));
    child.on('exit', (code, signal) => finish(s, `exited:${code == null ? signal : code}`));

    recordSitting(s);
    return s;
  }

  // ONE sessions.csv row per live PROCESS (design §1 Accounting), by the SAME writer the dispatch
  // door uses — never a second spelling of the schema. Failure is loud and never fatal: a process
  // is already running by the time this is reached.
  function recordSitting(s) {
    try {
      const written = appendRow(s.seat.sessionsCsv, {
        seat: s.seat.seat,
        'session-id': s.sessionId,
        harness: s.harness || '',
        workdir: s.workdir,
        pid: '',
        'pid-starttime': '',
        tty: '',
        'worktree-path': '',
        started: isoNow(),
      });
      if (!written.appended) {
        log('warn', 'live session sitting row NOT recorded — this session will be UNATTRIBUTABLE', { sessionsCsv: s.seat.sessionsCsv, sessionId: s.sessionId, reason: written.reason });
      }
    } catch (err) {
      log('warn', 'live session sitting row append failed — this session will be UNATTRIBUTABLE', { sessionsCsv: s.seat.sessionsCsv, sessionId: s.sessionId, error: err.message });
    }
  }

  // ── The stdout leg: tee to the transcript, parse for `result` events ───────────────────────────
  //
  // One `result` event ends one turn (spike-measured: N feeds → N results, strictly in order).
  // Everything else — `system/init` (re-emitted per turn), `assistant`, `rate_limit_event` — is
  // transcript only. The tee is byte-exact and happens FIRST, so a parse failure can never cost
  // the transcript `inspect logs` reads.
  function onStdout(s, chunk) {
    try { s.logStream.write(chunk); } catch {}
    s.buf += chunk.toString('utf8');
    let i;
    while ((i = s.buf.indexOf('\n')) >= 0) {
      const line = s.buf.slice(0, i);
      s.buf = s.buf.slice(i + 1);
      if (!line.trim()) continue;
      let ev;
      try { ev = JSON.parse(line); } catch { continue; }
      if (!ev || ev.type !== 'result') continue;
      s.turns += 1;
      const waiter = s.waiting.shift();
      s.state = s.waiting.length ? 'in-turn' : 'idle';
      if (!waiter) {
        log('warn', 'live session produced a result with nobody waiting for it', { conversationId: s.conversationId, sessionId: s.sessionId });
        continue;
      }
      clearTimeout(waiter.timer);
      // ⚑ A HARNESS ERROR IS NOT AN ANSWER. `is_error` results carry an empty (or diagnostic)
      // `result`, and posting that into the owner's thread would be the bare-fallback defect the
      // reply contract exists to remove — dressed up as a fast reply. The measured case that
      // produced this branch: resuming a session id that does not exist prints `No conversation
      // found with session ID: …` and ends the turn `is_error: true` with an empty result. So it
      // is reported as NOT answered, the caller takes the cold path, and the owner gets a real
      // reply one slow turn later instead of a fast blank one.
      const reply = typeof ev.result === 'string' ? ev.result : '';
      if (ev.is_error || !reply) {
        log('warn', 'live turn ended without a usable reply — the caller falls back to the cold path', { conversationId: s.conversationId, sessionId: s.sessionId, isError: Boolean(ev.is_error), replyBytes: reply.length });
        waiter.resolve({ ok: false, reason: ev.is_error ? 'harness-error' : 'empty-reply', sessionId: s.sessionId, sessionRef: s.sessionRef });
        continue;
      }
      waiter.resolve({
        ok: true,
        reply,
        isError: false,
        sessionId: s.sessionId,
        sessionRef: s.sessionRef,
        ms: Date.now() - waiter.at,
      });
    }
  }

  // Death, from any cause: the entry is cleared and EVERY un-answered waiter is failed loudly.
  // A waiter that is never settled is the owner's message disappearing — the exact failure the
  // fallback exists to prevent, so it is settled with a reason the caller can re-route on.
  function finish(s, reason) {
    if (s.dead) return;
    s.dead = true;
    if (sessions.get(s.conversationId) === s) sessions.delete(s.conversationId);
    const orphaned = s.waiting.splice(0, s.waiting.length);
    for (const w of orphaned) {
      clearTimeout(w.timer);
      w.resolve({ ok: false, reason: `live-session-died:${reason}`, unanswered: true, sessionId: s.sessionId, sessionRef: s.sessionRef });
    }
    try { s.logStream.end(); } catch {}
    log('info', 'live session ended', { conversationId: s.conversationId, sessionId: s.sessionId, reason, turns: s.turns, orphanedTurns: orphaned.length, ageMs: Date.now() - s.startedAt });
  }

  function close(s, reason) {
    if (s.dead) return;
    log('info', 'live session closing', { conversationId: s.conversationId, sessionId: s.sessionId, reason, turns: s.turns });
    try { s.child.stdin.end(); } catch {}
    // The exit handler does the bookkeeping. A process that ignores EOF is killed by the reaper's
    // own grace below rather than left holding a slot forever.
    setTimeout(() => {
      if (!s.dead) {
        log('warn', 'live session did not exit on EOF — killing the unit', { conversationId: s.conversationId, unitName: s.unitName });
        try { s.child.kill('SIGKILL'); } catch {}
      }
    }, 15000).unref();
  }

  // ── THE FEED — the whole point of the module ───────────────────────────────────────────────────
  //
  // Returns `{ ok: true, reply }` when the turn was answered by a warm process, and
  // `{ ok: false, reason }` for EVERY other outcome. The caller's contract is simple and total:
  // anything that is not `ok` means "take the cold path" — an ineligible seat, no warm session
  // yet, a death mid-turn, a timeout. `unanswered: true` marks the one case the caller must treat
  // as urgent rather than routine: the owner's words were written into a process that then died
  // without answering, so they MUST be re-routed cold or they are lost.
  async function feed({ conversationId, workdir, prompt, sessionRef = null, start = false }) {
    if (!conversationId) return { ok: false, reason: 'no-conversation' };
    if (typeof prompt !== 'string' || !prompt) return { ok: false, reason: 'empty-prompt' };

    // ⚑ RESOLVE THE CAST BEFORE ANYTHING COMPARES A PROFILE NAME (launch-cast unification,
    // 2026-08-11). `launch()` stores the RESOLVED name on the session, so the switch check below
    // MUST compare against the resolved name too — comparing it with the caller's would report a
    // switch on every single turn of a cast seat and reap the warm process each time, turning the
    // whole warm path into two cold spawns per message. That is exactly what
    // `probe-chat-live-session` arms 2 and 3 measured when this line was missing: "ONE process
    // served BOTH turns" went red with `reason: profile-switched` between them.
    //
    // Resolution is idempotent — it reads the seat's descriptor and ignores the name it is handed —
    // so `eligible()` and `launch()` re-resolving below is harmless and keeps each entry point
    // correct on its own. An UNCAST seat throws here; swallowed, because `eligible()` a few lines
    // down turns it into an ordinary ineligible reason and the caller falls through to the cold
    // path, which is where that refusal belongs.
    let profileName = null;
    try {
      ({ key: profileName } = launchSpecForSeat(config.launchSpecs || {}, workdir, log));
    } catch { /* eligible() reports it below */ }

    let s = sessions.get(conversationId);
    if (s && s.dead) { sessions.delete(conversationId); s = null; }

    // ── REAP ON A PROFILE SWITCH, measured at the only moment that matters ─────────────────────
    // The design asks that a master-profile apply guarantee "a switch takes effect at the very
    // next message". A signal file or a poll would both be later and weaker than this: the caller
    // resolves the profile from its OWN freshly-read config on every message, so a warm session
    // running a profile the caller no longer names is stale BY DEFINITION, and the next message
    // is exactly when that is knowable. `capabilities/master-profile` restarts the chat bridge on
    // apply, which re-reads the config — so the new name arrives here on the owner's first word
    // after the switch, with nothing hooked into the python and no daemon restart involved.
    if (s && profileName && s.profileName !== profileName) {
      log('info', 'live session reaped — its conversation now names a different profile', { conversationId, was: s.profileName, now: profileName });
      sessions.delete(conversationId);
      close(s, 'profile-switched');
      s = null;
    }

    if (!s) {
      if (!start) return { ok: false, reason: 'no-warm-session' };
      const el = eligible({ workdir });
      if (!el.ok) return { ok: false, reason: `ineligible:${el.reason}` };
      if (!sessionRef) return { ok: false, reason: 'no-session-ref-to-resume' };
      evictIfFull();
      try {
        s = launch({ conversationId, workdir, sessionRef });
      } catch (err) {
        log('warn', 'live session launch failed — the cold path is unaffected', { conversationId, error: err.message, code: err.code || null });
        return { ok: false, reason: `launch-failed:${err.message}` };
      }
      sessions.set(conversationId, s);
    }

    s.lastOwnerMsgAt = Date.now();
    touch(conversationId, s);

    // The stream-json user-turn shape, confirmed against claude 2.1.226 by spike (2026-08-10).
    const line = JSON.stringify({ type: 'user', message: { role: 'user', content: [{ type: 'text', text: prompt }] } }) + '\n';
    return new Promise((resolve) => {
      const waiter = { resolve, at: Date.now(), timer: null };
      waiter.timer = setTimeout(() => {
        const ix = s.waiting.indexOf(waiter);
        if (ix >= 0) s.waiting.splice(ix, 1);
        log('warn', 'live session turn timed out — reaping and falling back to the cold path', { conversationId, sessionId: s.sessionId, turnTimeoutMs });
        close(s, 'turn-timeout');
        resolve({ ok: false, reason: 'turn-timeout', unanswered: true });
      }, turnTimeoutMs);
      if (waiter.timer.unref) waiter.timer.unref();
      s.waiting.push(waiter);
      s.state = 'in-turn';
      try {
        s.child.stdin.write(line);
      } catch (err) {
        clearTimeout(waiter.timer);
        s.waiting.pop();
        resolve({ ok: false, reason: `write-failed:${err.message}`, unanswered: true });
        finish(s, `write-failed:${err.message}`);
      }
    });
  }

  function evictIfFull() {
    while (sessions.size >= maxSessions) {
      const [oldestId, oldest] = sessions.entries().next().value;
      log('info', 'live session cap reached — evicting the least recently fed', { evicted: oldestId, cap: maxSessions });
      sessions.delete(oldestId);
      close(oldest, 'lru-evicted');
    }
  }

  // ── The reaper ────────────────────────────────────────────────────────────────────────────────
  // Idle is measured from the LAST OWNER MESSAGE, never from the last reply: a long turn the owner
  // is waiting on must not age out from under him.
  function reapIdle(now = Date.now()) {
    let reaped = 0;
    for (const [id, s] of [...sessions.entries()]) {
      if (s.state === 'in-turn' || s.waiting.length) continue;
      if (now - s.lastOwnerMsgAt < idleMs) continue;
      sessions.delete(id);
      close(s, 'idle');
      reaped += 1;
    }
    return reaped;
  }

  // Reaped on a master-profile apply, so a profile switch takes effect at the very NEXT message
  // (live-session-design.md §1: this is what closes the switch-scope ambiguity). Also the
  // shutdown path — `stopAll` leaves NO orphan behind.
  function reapAll(reason = 'reap-all') {
    const n = sessions.size;
    for (const [id, s] of [...sessions.entries()]) {
      sessions.delete(id);
      close(s, reason);
    }
    if (n) log('info', 'all live sessions reaped', { count: n, reason });
    return n;
  }

  const reaperTimer = setInterval(() => { try { reapIdle(); } catch (err) { log('warn', 'reaper pass threw', { error: err.message }); } }, reapPollMs);
  if (reaperTimer.unref) reaperTimer.unref();

  function stop() {
    clearInterval(reaperTimer);
    return reapAll('shutdown');
  }

  function list() {
    return [...sessions.values()].map((s) => ({
      conversation: s.conversationId,
      session_id: s.sessionId,
      session_ref: s.sessionRef,
      profile: s.profileName,
      seat: s.seat && s.seat.seat,
      workdir: s.workdir,
      state: s.state,
      turns: s.turns,
      idle_ms: Date.now() - s.lastOwnerMsgAt,
      age_ms: Date.now() - s.startedAt,
    }));
  }

  return { feed, eligible, list, reapIdle, reapAll, stop, size: () => sessions.size, config: { idleMs, maxSessions, turnTimeoutMs } };
}

module.exports = { createLiveSessions, seatIsHumanInteractive, DEFAULT_IDLE_MS, DEFAULT_MAX, LIVE_INPUT_FLAGS };
