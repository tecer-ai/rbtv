'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { spawn: childSpawn, execFileSync } = require('node:child_process');
const { requirePythonCmd } = require('../../lib/python-cmd');
const { loadConfig, resolveTemplateSlots, resolveWorkdir, resolveWorkspaceRoot, resolveEffort } = require('./config');
// The (harness, model) -> profile-name catalog, from the ONE shared resolver (task 7.54). Reached
// through `server/spawn/config.js`'s own upstream — this module already depends on that adapter,
// so nothing new crosses the daemon boundary.
const { castProfileFor, bindingOf } = require('../../launch-profiles/catalog');
const { materializeHarnessConfig, harnessOf, planCagedSettings, materializeCagedSettings } = require('./harness-config');
const { buildBwrapArgv } = require('./bwrap');
const { composeSeatSpawn } = require('./tmux');
// Task 7.11 — the seat cage and the launch-time half of the identity gate.
const { composeSeatCage, assertGroundTruthUnwritable, specToBwrapFlags, contains, composeAncestorMasks } = require('./cage');
const { parseServiceSeatPath, parseSeatPath, checkGoalExecuting, checkMaterializedSeat } = require('../seat-identity/seat-folder');
const { deriveLease } = require('../lease/lease');  // 7.607 E1 — the bus/goals authz predicate
const { appendRow, readCsv } = require('../seat-identity/csv');
// The ONE symlink-aware containment rule (fA-4 D-1), parameterized by root and shared with the
// fire-tool workdir guard rather than respelled here — `path.resolve` + a lexical prefix test
// answers where a path POINTS, never where it LANDS.
const { resolvesInsideGoalsRoot } = require('../heart/argv-template');
const {
  generateSessionId,
  selectCarrier,
  spawnSystemd,
  spawnSetsid,
  systemdStatus,
  setsidStatus,
  killSystemd,
  killSetsid,
  listSystemdUnits,
} = require('./carrier');
const {
  SpawnError,
  E_UNKNOWN_PROFILE,
  E_UNKNOWN_MODE,
  E_HEADED_NOT_CAPABLE,
  E_PROFILE_HALVES_UNSUPPORTED,
  E_FLAG_INJECTION,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_UNKNOWN_REQUEST_KEY,
  E_SESSION_NOT_FOUND,
  E_CARRIER_FAILED,
  E_ORPHAN_RESCAN_FAILED,
  E_MISSING_KEY,
  E_BAD_REQUEST,
  E_GOAL_NOT_LIVE,
  E_NOT_A_SEAT_FOLDER,
  E_SEATLESS_GOAL_DISPATCH,
} = require('./errors');

const SESSION_MODES = new Set(['headless', 'headed']);

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function captureSessionRef(profile, launchResult, workdir, sessionRefSlot) {
  const rule = profile.session_ref;
  if (!rule) return null;
  // `assigned` (r-chat-chain-resumes-session): the ref is what this spawn PUT on the command line
  // — this session's id on a fresh launch, the predecessor's ref on a resume (the resumed session
  // keeps its id, so the chain's ref stays one value). Nothing is read back out of the worker, so
  // the ref is on record before the process emits anything and survives a turn that never does.
  if (rule.source === 'assigned') return sessionRefSlot;
  if (rule.source === 'cwd-implicit') return workdir;
  // stdout-json / stdout-json-event require reading the worker's stdout, which is
  // redirected to the log file. For long-running agents the ref arrives later;
  // p2-2 stores null here and the ticker completion path (p3-1) can patch it.
  return null;
}

async function resolvePidStarttime(carrier, pid, unitName) {
  if (carrier === 'systemd' && unitName) {
    // systemctl show ExecMainStartTimestamp is absolute; pid_starttime uses /proc stat field 22.
    // We need a PID to read /proc; systemctl show gives us ExecMainPID.
    const { systemdStatus } = require('./carrier');
    const info = systemdStatus(unitName);
    if (info.pid) {
      const { setsidStatus } = require('./carrier');
      const st = setsidStatus(info.pid);
      return st.pidStarttime || null;
    }
    return null;
  }
  if (carrier === 'setsid' && pid) {
    const { setsidStatus } = require('./carrier');
    const st = setsidStatus(pid);
    return st.pidStarttime || null;
  }
  return null;
}

// Execute a composed tmux argv. The argv is passed as a VECTOR to childSpawn with no shell — the
// same property tmux.js composes for, carried through to the actual exec. `shell: true` here would
// undo the entire reason that module builds a vector (run issue G-11's class); do not add it.
// tmux's `-P -F '#{pane_id} #{pane_pid}'` prints the two handles on stdout.
function runTmux(tmuxArgv) {
  return new Promise((resolve, reject) => {
    const proc = childSpawn(tmuxArgv[0], tmuxArgv.slice(1), { stdio: ['ignore', 'pipe', 'pipe'] });
    let out = '';
    let err = '';
    proc.stdout.on('data', (d) => { out += d.toString(); });
    proc.stderr.on('data', (d) => { err += d.toString(); });
    proc.on('error', (e) => reject(new SpawnError(E_CARRIER_FAILED, `tmux spawn error: ${e.message}`, { carrier: 'tmux-scope' })));
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new SpawnError(E_CARRIER_FAILED, `tmux new-window failed (exit ${code}): ${err || out}`, { carrier: 'tmux-scope', exitCode: code }));
        return;
      }
      const [paneId, panePidRaw] = out.trim().split(/\s+/);
      const panePid = Number.parseInt(panePidRaw, 10);
      resolve({ paneId: paneId || null, panePid: Number.isFinite(panePid) ? panePid : null });
    });
  });
}

function validateRequestKeys(req) {
  const known = new Set(['profile', 'session_mode', 'prompt', 'workdir']);
  for (const key of Object.keys(req)) {
    if (!known.has(key)) {
      throw new SpawnError(E_UNKNOWN_REQUEST_KEY, `unknown request key: ${key}`, { key });
    }
  }
}

function rejectFlagInjection(value, field) {
  if (typeof value !== 'string') return;
  // Reject strings that look like flag injection attempts: leading dash, or embedded shell metacharacters.
  if (value.startsWith('-')) {
    throw new SpawnError(E_FLAG_INJECTION, `${field} starts with a flag marker`, { field, value });
  }
  if (/[;&|`$()\n\r]/.test(value)) {
    throw new SpawnError(E_FLAG_INJECTION, `${field} contains shell metacharacters`, { field, value });
  }
}

function ensurePromptFile(dataRoot, sessionId, prompt) {
  const promptDir = path.join(dataRoot, 'prompts');
  fs.mkdirSync(promptDir, { recursive: true, mode: 0o700 });
  const promptPath = path.join(promptDir, `${sessionId}.txt`);
  fs.writeFileSync(promptPath, prompt ?? '', { mode: 0o600 });
  return promptPath;
}

// Resolve template slots across the WHOLE sandbox block rather than one named directive.
// systemd's sandbox vocabulary is path-heavy (ReadWritePaths=, ReadOnlyPaths=, BindPaths=,
// InaccessiblePaths=, ...); resolving only the directive today's profiles happen to use would
// leave the next one added silently carrying a literal `{workdir}` into the unit — the same
// defect, one directive over. Values are resolved by SHAPE, not by name: strings and
// string-arrays go through slot resolution, everything else (booleans like PrivateTmp,
// numbers) passes through untouched. A slot with no value throws E_MISSING_KEY from
// resolveTemplateSlots — the spawn fails loudly rather than emitting a literal `{slot}`.
function resolveSandbox(sandbox, workdir) {
  if (!sandbox) return sandbox;
  const values = { workdir };
  const resolved = { ...sandbox };
  for (const [key, value] of Object.entries(sandbox)) {
    // 7.11: `SeatBinds` is resolved by cage.js against the SEAT'S OWN records (goal/run/seat dirs
    // and worktree grants), not against a workdir. Sending it through the workdir resolver here
    // would give one template two resolvers — and the one that runs first would silently win.
    if (key === 'SeatBinds') continue;
    if (typeof value === 'string') {
      resolved[key] = resolveTemplateSlots([value], values)[0];
    } else if (Array.isArray(value) && value.every((v) => typeof v === 'string')) {
      resolved[key] = resolveTemplateSlots(value, values);
    }
  }
  return resolved;
}

// ── G-144: this spawn path resolves `exec:` ONLY — refuse a half-shaped profile BY NAME ──────
//
// Task 7.42 ruled the caged/portable half shape (`command: { caged:, portable: }`,
// #d-profile-source-unification (4)) and shipped the shared resolver
// (launch-profiles/resolveProfile) with ONE live consumer — which is not this module. So a
// profile declaring `command:` instead of `exec:` PASSES config load (profiles.js accepts either
// shape) and then reads `.prompt` / `.argv` off `undefined`, taking the spawn path down with a
// bare `TypeError: Cannot read properties of undefined` on a config the daemon booted with.
// **Config validation is not a backstop here** — it was never asked to be: the shape is legal,
// it is this CONSUMER that cannot resolve it.
//
// THIS IS A TYPED REFUSAL, NOT HALF SUPPORT. Routing this module through resolveProfile() is the
// root-cause shape and belongs with its ruled consumers (7.43 / 7.54, both unbuilt); doing it
// here would be reimplementing half selection in the one place 7.42 exists to remove it from.
//
// ⚑ AMENDED 2026-08-11, owner ruling `d-0811lp-effort-lane-build-now` (run exec-0811-live-proofs).
// HALF SELECTION is still refused here and 7.43/7.54 still own it — nothing below changed. What
// the ruling lifted is narrower and separable: the profile's `effort:` LADDER is now read by this
// module too, through the shared `resolveEffort()` that `resolveProfile` itself calls
// (launch-profiles/profiles.js). That is the opposite of reimplementation — ONE interpreter of the
// table, two callers — and it is what let the channel master's DM sittings carry a reasoning rung
// without waiting for the whole 7.43 refactor. The ruling explicitly overrode the reservation this
// comment's sibling at `internal-api/dispatch.js` recorded ("NO daemon caller today … Re-rule at
// 7.43/7.54"): that reservation now holds for E_NO_PORTABLE_HALF and E_RAW_FLAG, and NOT for
// E_UNKNOWN_EFFORT, which this path raises live.
// What this removes is the crash and the silence — the daemon now says WHICH profile and WHICH
// halves, so the operator reads a refusal instead of a stack.
//
// ⚠ CALLED AT BOTH DOORS IMMEDIATELY AFTER THE PROFILE LOOKUP, ahead of every request-, workdir-
// and identity-level gate. Placement is the load-bearing part, not the throw: further down, a
// half-shaped profile launched at a bad workdir would refuse with E_WORKDIR_ESCAPE and the
// operator would fix the workdir, retry, and hit the real refusal one round trip later — a
// correct-but-masking refusal is its own defect. It is deliberately NOT reused as a config-load
// check: a half-shaped profile is legal to LOAD and this daemon must keep booting with one.
function requireExecShape(profile, profileName) {
  if (profile.exec) return;
  const halves = profile.command ? Object.keys(profile.command) : [];
  throw new SpawnError(
    E_PROFILE_HALVES_UNSUPPORTED,
    `profile ${profileName} declares command halves (${halves.join(', ') || 'none'}) and no exec block — ` +
    `the daemon spawn path resolves \`exec:\` only and does not select a half (that is the shared ` +
    `launch-profile resolver's job, wired at tasks 7.43/7.54). REFUSING rather than spawning a ` +
    `half-resolved session.`,
    { profile: profileName, halves },
  );
}

// `resumeRef` (r-chat-chain-resumes-session): non-null selects the profile's RESUME template
// instead of `exec` — same block shape, same carriage, one extra slot value. The caller has
// already established the profile carries one; this function does not decide policy.
// `effort` (owner ruling `d-0811lp-effort-lane-build-now`, 2026-08-11): a NUMERIC RUNG, 1..N, in
// the ladder THIS profile declares — null means the harness default, which is every pre-ruling
// caller's behaviour unchanged. `profileName` rides with it only so a refusal can name the profile.
function composeArgv(profile, mode, sessionId, workdir, prompt, dataRoot, resumeRef = null, effort = null, profileName = null) {
  const isHeaded = mode === 'headed';
  const block = isHeaded ? profile.headed.tui : (resumeRef ? profile.resume : profile.exec);
  const promptCarriage = block.prompt;

  let stdinFile = null;
  if (promptCarriage === 'stdin') {
    // stdin carriage: the prompt rides a file the CARRIER connects as the worker's stdin
    // (StandardInput=file: on systemd; the file's fd on setsid) — bytes then EOF at end-of-file,
    // the "server writes the prompt, then closes stdin" contract. The path never appears in argv
    // (no {prompt_file} slot), and bwrap needs no bind: fd 0 is opened before the wrap execs.
    // Headed blocks can never reach here — config.js rejects `headed.tui.prompt: stdin` at load.
    stdinFile = ensurePromptFile(dataRoot, sessionId, prompt);
  }
  // The former `file` and `argv-last` branches are DELETED (task 7.23): task 7.14 (batch-08
  // item 4 half A) narrowed the loadable headless vocabulary to `stdin` only
  // (KNOWN_PROMPT_VALUES, config.js), making both branches unreachable from any loadable
  // config. Headed `file` carriage was owned end-to-end by the pty host (composeHeadedArgv,
  // pty/carriage.js) and never routed through here; task 7.29 deleted that module, so no headed
  // prompt carriage is composed anywhere today — a seat is driven by its DESCRIPTOR, not by argv.

  // `{session_ref}` resolves to the ref this launch OWNS: the predecessor's on a resume, this
  // session's own id on a fresh launch (which is what pins them equal for the next turn).
  const argv = resolveTemplateSlots(block.argv, { workdir, session_ref: resumeRef || sessionId });

  // ⚑ THE DESCRIPTOR NOW ACTUALLY ARRIVES (owner ruling 2026-08-07). The comment above says a
  // seat is driven by its DESCRIPTOR — and nothing delivered one. The auto-injected CLAUDE.md
  // chain DOES reach a seat session (measured 2026-08-07 on the channel master: its own
  // CLAUDE.md was in context and the model quoted the "read seat.md and FOLLOW it" sentence
  // back on demand), but `seat.md` sat behind that sentence as a POINTER — one voluntary tool
  // call the seat had to make BEFORE its first word. A one-turn headless sitting against a
  // six-word question does not make it: the channel master answered as a generic assistant and
  // listed the harness's tools instead of the seat's instruments. Not a delivery failure — a
  // compliance failure, cured by removing the voluntary step: the descriptor rides the SYSTEM
  // PROMPT, which needs no compliance to arrive, and it costs nothing on later turns of the
  // same chain (a system prompt is re-sent, not re-read into the conversation).
  //
  // ⚠ CONDITIONAL ON THE FILE EXISTING, and that is not politeness: `claude
  // --append-system-prompt-file <missing>` prints "Append system prompt file not found" and
  // RUNS NOTHING (measured, 2.1.224). Unconditional, this flag would kill every spawn at a seat
  // that has no descriptor yet — which includes every seat between scaffold and materialize.
  //
  // Claude-only because the flag is claude's. Another harness gains this when someone MEASURES
  // its equivalent; guessing one would put unverified launch knowledge back in this file, which
  // is what `injection-ladder/` exists to prevent.
  const descriptor = workdir ? path.join(workdir, 'seat.md') : null;
  if (descriptor && harnessOf(profile) === 'claude' && fs.existsSync(descriptor)) {
    argv.push('--append-system-prompt-file', descriptor);
  }

  // ── the effort rung, composed by the profile's OWN ladder ─────────────────────────────────
  // ⚠ ONE INTERPRETER, IMPORTED — never a second reading of the `effort:` table here. `resolveEffort`
  // is the same function `launch-profiles/resolveProfile` calls; this module owns argv composition
  // (G-144) but not the ladder's meaning. An out-of-range rung throws E_UNKNOWN_EFFORT naming the
  // profile's range; a profile whose dial is declared INERT accepts the rung and emits nothing
  // (G-270), so an effort set while the master runs on such a profile visibly does nothing.
  // ⚠ NO PROFILE IS NAMED HERE, and that is a rule this module is probed against
  // (probe-caged-settings, 'no per-profile special case anywhere in server/spawn/'): which
  // profiles have a dial is the CONFIG's statement, never this file's.
  const { argv: effortArgv } = resolveEffort(profile, effort, profileName || '(unnamed profile)');
  argv.push(...effortArgv);

  return { argv, stdinFile, promptCarriage };
}

function ensureLogPath(dataRoot, sessionId) {
  const logDir = path.join(dataRoot, 'logs');
  fs.mkdirSync(logDir, { recursive: true, mode: 0o700 });
  const logPath = path.join(logDir, `${sessionId}.log`);
  // Task 7.13 piece 4 (settles D97): pre-create the transcript 0600 BEFORE the carrier opens
  // it — systemd's `StandardOutput=append:` creates a missing file at the manager's default
  // mode (664 observed live), leaving a secret-bearing transcript world-readable while its
  // audit neighbour sits at 0600. An existing file keeps its mode, so this pre-create wins.
  // appendFileSync (not writeFileSync): never truncate an existing transcript.
  fs.appendFileSync(logPath, '', { mode: 0o600 });
  return logPath;
}

// THE one derivation of a session's exit-marker path (the file the carrier's post-exit hook
// writes the real exit status to, and the ticker's sweep reads back). The ticker imports this
// rather than re-deriving the path (D44 discipline applied to a filesystem contract).
function exitFilePath(dataRoot, sessionId) {
  return path.join(dataRoot, 'exits', `${sessionId}.exit`);
}

function ensureExitFile(dataRoot, sessionId) {
  const exitDir = path.join(dataRoot, 'exits');
  fs.mkdirSync(exitDir, { recursive: true, mode: 0o700 });
  return exitFilePath(dataRoot, sessionId);
}

// ── Task 7.449 (MC7) — THE TRACE PRECONDITION, for both doors below ─────────────────────────────
//
// The daemon already reaches a trace-creating act twice — the at-dispatch door in `spawn` and the
// seat door in `spawnSeat`, both through `appendRow`. What it lacks is the PRECONDITION that act
// needs: `appendRow` refuses an absent-or-headerless file ("refusing to invent a schema") and
// NOTHING creates that file. Package creation deliberately does not — `materialize-seats.py` plans
// `taskforce.csv` and `state.csv`, and the capability's own doc says "sessions.csv is born at
// LAUNCH, not at create". So on a package the kit never launched into, both doors no-op into a warn
// line, the run has no trace at all, and the edge-runner's gate 3 refuses the whole package.
//
// SO THE FIX IS THE PRECONDITION, NOT A SECOND WRITER, and that distinction is the whole design.
// Calling coord.py's `session-open` on top of a door that already appends yields TWO ROWS PER
// LAUNCH, and the extra row carries a FOREIGN session-id — breaking the at-dispatch identity task
// 7.73's join reads, and losing the real pid/pid-starttime pair the seat-identity gate decides on.
// Guaranteeing the header instead lets the door's OWN row land, unchanged, with both intact.
//
// THE HEADER IS NOT SPELLED HERE, DELIBERATELY. `coord.py` owns this schema (`SESSIONS_COLS`, task
// 7.37). A second spelling on the write side is exactly how the run-1 and run-2 headers came to
// disagree — the argument `seat-identity/csv.js` is built on — so the owner is ASKED, at run time,
// and only on the path where the append has ALREADY refused. A normal launch into a live package
// pays nothing: no subprocess, no python, no change in behaviour at all.
//
// AND IT IS WRITTEN IN PLACE. `writeFileSync` truncates an existing file; it does not replace the
// inode. That matters because `composeCageFor` pre-creates this file for a SERVICE seat and then
// RO-BINDS it into the cage: a header written by replacing the inode would be correct outside the
// cage and invisible inside it, which no row-level check could see.
const SESSIONS_HEADER_ARGV = ['-c',
  'import sys; sys.path.insert(0, sys.argv[1]); import coord; print(",".join(coord.SESSIONS_COLS))'];

function appendRowEnsuringHeader(csvPath, values, log) {
  const written = appendRow(csvPath, values);
  if (written.appended) return written;
  // Answer ONLY the missing-header refusal, and decide that STRUCTURALLY rather than by matching
  // the refusal's text: if the file already carries a header, this refusal is not ours and the
  // file is not ours to touch. It also bounds what can be lost — `appendRow` refuses here exactly
  // when the file has no non-empty line, so there is no content to overwrite.
  const before = readCsv(csvPath);
  if (before.exists && before.header.length > 0) return written;
  try {
    const kit = path.join(process.env.RBTV_IGNITE_SRC || path.resolve(__dirname, '../..'), 'team-kit');
    const header = execFileSync(requirePythonCmd(), [...SESSIONS_HEADER_ARGV, kit],
      { encoding: 'utf8', timeout: 30000 }).trim();
    if (!header.includes(',')) throw new Error(`the schema owner returned no header: ${JSON.stringify(header)}`);
    fs.writeFileSync(csvPath, `${header}\n`, 'utf8');
    log('info', 'session trace had no header; created it from coord.py SESSIONS_COLS so this launch could record itself', { sessionsCsv: csvPath, header });
  } catch (err) {
    // Never fatal, for the same reason the callers' own catch is not: a process is already running
    // at this point. The caller's existing warn arm then reports the unrecorded row as it always
    // did — this path can leave the launch no worse off than it was before this function existed.
    log('warn', 'session trace has no header and one could not be created — this launch will be UNATTRIBUTABLE', { sessionsCsv: csvPath, error: err.message });
    return written;
  }
  return appendRow(csvPath, values);
}

// Task 7.11 §2 W2/W3 — the seat's worktree grants, DERIVED from the seat's own identity.
//
// A worktree belonging to this seat is `<ws>/.rbtv/worktrees/{repo}--{goal}--{seat}` (7.38's
// ruled naming). Deriving the grant from that naming rather than from a caller argument means a
// seat can never be handed someone else's worktree at request time — the same posture CMP-17
// takes on the workdir, applied to the openings that were added around it.
//
// The repo's git dir comes from the worktree's own `.git` FILE (a linked worktree's `.git` is a
// file reading `gitdir: <repo>/.git/worktrees/<name>`), so the plumbing paths W3 opens are read
// out of git's own record instead of guessed from a repo list this module would have to be told.
//
// ZERO GRANTS IS THE CORRECT ANSWER FOR A SEAT WITH NO WORKTREE, and it is not a stub. Task 7.38
// (the worktree flow) landed 2026-08-05: `team-kit/worktree-flow.py` creates the
// `{repo}--{goal}--{seat}` directories this resolver reads, so a seat that has one resolves its
// grants here and a seat that does not carries no W2/W3 openings. Nothing in this function changed
// when 7.38 landed — the directories simply appeared.
// READ-ROOT grant (owner-directed, 2026-08-06): a seat whose seat.md frontmatter declares
// `read-root: true` gets the workspace root mounted READ-ONLY (the cage template's
// `ro-bind:{grant:readRoot}` line). The declaration surface is seat.md — ro-bound inside the
// cage, written by the materializer/master — so an occupant cannot grant itself the vault.
//
// THE ONE DECLARATION READER for every seat-declared grant class (read-root, and the three the
// owner's "1a" ruling adds below). One reader because one surface: a second parse of seat.md
// would be a second definition of what "declared" means, and the two would disagree the first
// time either gained a case. `key` is always a literal from THIS module — never caller input.
function seatDeclares(seatDir, key) {
  try {
    const md = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8');
    const fm = /^---\n([\s\S]*?)\n---/.exec(md);
    return !!fm && new RegExp(`^${key}:\\s*true\\s*$`, 'm').test(fm[1]);
  } catch {
    // no seat.md yet (pre-materialization probe paths): not declared, fail closed
    return false;
  }
}

// The LIST half of the one declaration reader. Same surface (seat.md frontmatter, ro-bound inside
// the cage), same lightweight parse — a YAML-style block list, read without pulling a parser into
// the spawn path. The block ends at the first line that is not a `- item`, so a malformed or
// mis-indented entry ends the list rather than swallowing the keys after it. `key` is always a
// literal from THIS module — never caller input.
function seatDeclaresList(seatDir, key) {
  let fm;
  try {
    const md = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8');
    const m = /^---\n([\s\S]*?)\n---/.exec(md);
    if (!m) return [];
    fm = m[1];
  } catch {
    return []; // no seat.md yet: not declared, fail closed
  }
  const items = [];
  let inBlock = false;
  for (const line of fm.split('\n')) {
    if (!inBlock) {
      if (new RegExp(`^${key}:\\s*$`).test(line)) inBlock = true;
      continue;
    }
    const item = /^\s*-\s*(.*)$/.exec(line);
    if (!item) break;
    items.push(item[1].trim().replace(/^["']|["']$/g, ''));
  }
  return items;
}

// The SCALAR half of the one declaration reader — same surface (seat.md frontmatter, ro-bound
// inside the cage), same lightweight parse, same fail-closed absence as its two siblings above.
// It exists because the seat's CAST is a scalar: `materialize-seats.py#_descriptor_frontmatter`
// emits `harness:` / `model:` / `effort:` as plain values, and emits ALL THREE OR NONE (the
// `open_binding` rule — the channel master declares none by design, so its harness and model stay
// the chat bridge's to name).
//
// `key` is always a literal from THIS module — never caller input.
function seatDeclaresValue(seatDir, key) {
  try {
    const md = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8');
    const fm = /^---\n([\s\S]*?)\n---/.exec(md);
    if (!fm) return '';
    const m = new RegExp(`^${key}:[ \\t]*(.*)$`, 'm').exec(fm[1]);
    return m ? m[1].trim().replace(/^["']|["']$/g, '') : '';
  } catch {
    // no seat.md yet (pre-materialization, or a first-fire job-born seat): not declared, and an
    // undeclared cast is the FALLBACK case, never a refusal.
    return '';
  }
}

// ── THE SEAT'S CAST → THE PROFILE THAT RUNS IT — the READ half only (task 7.54 · D19 · D27) ─────
//
// Reads what the seat declares and hands it to the ONE shared resolver. The resolution law, the
// refusals and the reasoning all live in `launch-profiles/catalog.js#castProfileFor`; this side
// owns only the seat.md read, because that reader (`seatDeclaresValue`) is a spawn concern and
// lives here.
//
// ⚠ NOTHING PROFILE-SPECIFIC MAY LAND IN THIS FILE. `probe-caged-settings` asserts "no per-profile
// special case anywhere in `server/spawn/`" and greps this tree for profile-name literals — the
// standing DEC-1 rule that profile knowledge has exactly one home. The resolution logic lived here
// until owner ruling D27 (2026-08-11) moved it out; keep it out, comments included.
function profileForSeatCast(profiles, seatDir, profileName, log) {
  const binding = {
    harness: seatDeclaresValue(seatDir, 'harness'),
    model: seatDeclaresValue(seatDir, 'model'),
  };
  return castProfileFor(profiles, binding, profileName, log, seatDir ? path.basename(seatDir) : null);
}

// ── `rw-paths:` — the seat-declared READ-WRITE workspace paths (owner ruling "a", 2026-08-06) ──
//
// Motivating case: the channel-master holds the whole workspace under `read-root: true`, so an
// in-workspace CLI that must rewrite its own state (gtools refreshing an OAuth token) meets EROFS
// and its reads die when the token expires. The generic answer is a declared, validated list of
// workspace-relative paths punched back through the read-only floor.
//
// FAIL-CLOSED, PER ENTRY. A bad entry is SKIPPED and LOGGED — never guessed at, never repaired,
// and never fatal to the spawn: one typo in a seat descriptor must not take a seat offline. The
// four refusals, in the order they are cheapest to answer:
//
//   1. empty / absolute            — the key's vocabulary is workspace-RELATIVE, only
//   2. escapes the workspace root  — checked AFTER `..` normalization, so `a/../../etc` is caught
//   3. overlaps `<ws>/.rbtv/goals` — in EITHER direction. Every `sessions.csv` and every `seat.md`
//      lives under that subtree, so one containment test covers rule 3 without walking the tree:
//      an entry INSIDE it could be, or contain, one of those files; an entry that CONTAINS it
//      contains all of them. This is also what keeps the seat.md ro-carve winning — an entry
//      covering the seat's own folder is inside `.rbtv/goals` and is refused here, so it never
//      reaches the ordering question at all (refused under rule 3's spirit, as ruled).
//   4. does not exist              — skipped; this resolver NEVER creates a path.
function resolveRwPathGrants(seatPath, log) {
  const root = seatPath.workspaceRoot;
  const goals = path.join(root, '.rbtv', 'goals');
  const grants = [];
  for (const entry of seatDeclaresList(seatPath.seatDir, 'rw-paths')) {
    const refuse = (reason) => log('warn', `rw-paths entry REFUSED: ${reason}`, { seat: seatPath.seat, seatDir: seatPath.seatDir, entry });
    if (!entry) { refuse('empty entry'); continue; }
    if (path.isAbsolute(entry)) { refuse('absolute path — rw-paths entries are workspace-relative'); continue; }
    const target = path.resolve(root, entry);
    if (!contains(root, target) || target === root) { refuse(`resolves outside the workspace root: ${target}`); continue; }
    if (contains(goals, target) || contains(target, goals)) {
      refuse(`overlaps ${goals} — the identity/ground-truth surfaces (sessions.csv, seat.md) stay unwritable: ${target}`);
      continue;
    }
    if (!fs.existsSync(target)) { refuse(`does not exist (never created from here): ${target}`); continue; }
    // fA-4 D-1 — THE LEXICAL TESTS ABOVE ANSWER WHERE THE PATH POINTS, NOT WHERE IT LANDS. A seat
    // with a writable directory anywhere in the workspace can plant a symlink and declare it; the
    // rules above see a tidy relative path and admit it. Resolve for real, against BOTH bounds:
    // inside the workspace root, and — separately — NOT inside the goals tree, because rule 3's
    // whole point is that a symlink is the way an entry gets there without spelling it.
    const realRoot = (() => { try { return fs.realpathSync(root); } catch { return null; } })();
    const realGoals = (() => { try { return fs.realpathSync(goals); } catch { return null; } })();
    if (!realRoot || !resolvesInsideGoalsRoot(target, realRoot)) {
      refuse(`RESOLVES outside the workspace root — a segment on this path is a symlink out of it: ${target}`);
      continue;
    }
    if (realGoals && resolvesInsideGoalsRoot(target, realGoals)) {
      refuse(`RESOLVES inside ${goals} through a symlink — the identity/ground-truth surfaces stay unwritable: ${target}`);
      continue;
    }
    grants.push({ rwPath: target });
  }
  return grants;
}

// ── `goal-writes:` — the seat's ONE declared role output (owner ruling D9, 2026-08-10) ─────────
//
// `rw-paths` above cannot express this, and must not be widened to: it REFUSES every entry under
// `.rbtv/goals` precisely because that subtree holds every `sessions.csv` and every `seat.md`. So
// the thing a seat's role actually PRODUCES — the interviewer's `goal.md`, the structurer's
// `milestones.csv` — had no expressible grant at all, and the interviewer found that out by meeting
// EROFS on the one file it existed to write, after a full night of interviewing (2026-08-09).
//
// GOAL-RELATIVE, not workspace-relative. That is the single vocabulary difference from `rw-paths`
// and it is what makes an entry inside `.rbtv/goals` safe to admit here: the path can only ever
// resolve inside THIS seat's own goal folder, so no entry can name another goal, another seat, or
// anything outside the tree. The cage template's `bind-try:{grant:goalWrite}` line consumes it.
//
// GROUND TRUTH IS NOT DEFENDED BY A LIST HERE, deliberately — it is defended by bind ORDER in
// `config/spawn-profiles.yaml`: the two `ro-bind-try` carves (`sessions.csv`, `state.csv`) sit
// immediately AFTER this grant's line, peer seat folders are absent under the `seats` tmpfs, and
// `seat.md` keeps its own read-only carve. A second list here would be a second place the wall is
// reasoned about. `materialize-seats.py` refuses such a declaration at AUTHORING time as well,
// where the author is still holding the file.
//
// FAIL-CLOSED PER ENTRY, same posture and same reason as `rw-paths`: a bad entry is skipped and
// LOGGED, never fatal — one typo in a descriptor must not take a seat offline.
//
// ⚠ IT CREATES THE DECLARED OUTPUT WHEN ABSENT, and that is the ONE place it departs from its
// `rw-paths` sibling (owner ruling D21, 2026-08-11). The departure is forced by bwrap, not chosen:
// a bind needs an existing source and the goal root is read-only, so a seat whose product does not
// exist YET — the structurer's `milestones.csv`, every checker's findings file — could never create
// it, and "declare your output" would work only for the one file the scaffolder happens to seed.
// Skipping instead would have made the grant useless for most of the roles it exists to serve.
// The precedent is IN THIS FILE: `composeCageFor` already touches an absent `sessions.csv` for the
// service seat, for the same reason and with the same guard. Bounded exactly: only the ONE
// already-validated goal-relative path (absolute, escaping and outside-goal declarations were
// refused above, and `materialize-seats.py` refused ground truth at authoring time), at most its
// parent directory, and always EMPTY — never content, never a template.
function resolveGoalWriteGrants(seatPath, log) {
  const goalDir = seatPath.goalDir;
  const grants = [];
  for (const entry of seatDeclaresList(seatPath.seatDir, 'goal-writes')) {
    const refuse = (reason) => log('warn', `goal-writes entry REFUSED: ${reason}`, { seat: seatPath.seat, seatDir: seatPath.seatDir, entry });
    if (!entry) { refuse('empty entry'); continue; }
    if (path.isAbsolute(entry)) { refuse('absolute path — goal-writes entries are goal-relative'); continue; }
    const target = path.resolve(goalDir, entry);
    if (!contains(goalDir, target) || target === goalDir) { refuse(`resolves outside the seat's own goal folder: ${target}`); continue; }
    // fA-4 D-1 — SAME RULE AS ITS SIBLING, AND IT MUST RUN BEFORE THE D21 CREATION BELOW. The seat
    // holds RW on `{goalDir}/coordination`, so it can plant a symlink there, declare it, and be
    // handed an RW bind of the link's REAL target; and `mkdirSync`/`writeFileSync` follow symlinked
    // segments too, so a check placed after creation would already have written through the link.
    const realGoalDir = (() => { try { return fs.realpathSync(goalDir); } catch { return null; } })();
    if (!realGoalDir || !resolvesInsideGoalsRoot(target, realGoalDir)) {
      refuse(`RESOLVES outside the seat's own goal folder — a segment on this path is a symlink out of it: ${target}`);
      continue;
    }
    if (!fs.existsSync(target)) {
      // D21: create it EMPTY so the bind has a source. A failure here is the same logged skip as
      // any other bad entry — a goal folder that cannot take the file must not take the seat down.
      try {
        fs.mkdirSync(path.dirname(target), { recursive: true });
        fs.writeFileSync(target, '');
      } catch (err) {
        refuse(`does not exist and could not be created: ${target} — ${err.message}`);
        continue;
      }
    }
    grants.push({ goalWrite: target });
  }
  return grants;
}

function resolveReadRootGrant(seatPath) {
  return seatDeclares(seatPath.seatDir, 'read-root') ? [{ readRoot: seatPath.workspaceRoot }] : [];
}

// ── Owner ruling "1a" (2026-08-06) — the three CROSS-GOAL INSTRUMENT grants ──────────────────
//
// A service seat (the channel-master is the first) is promised instruments the cage blocks: the
// coordination CLI writing into ANOTHER goal's run (read-only under the read-root grant -> EROFS,
// measured), the user-local CLIs (HOME is a tmpfs), and the gateway address (no env reaches the
// session). Each is a grant class declared in seat.md — ro-bound inside the cage, written by the
// materializer/master, never the occupant — so no seat can widen its own walls, exactly as
// `read-root` above. Absent key -> empty grant list -> the template line composes to nothing.

// ── 7.607 E1 — THE BUS AUTHZ PREDICATE IS THE DERIVED LEASE (design lock item 4, SECURITY) ─────
//
// `bus-write: true` — RW on the coordination dir of every goal that is EXECUTING RIGHT NOW.
//
// WHAT THIS REPLACED AND WHY IT IS SECURITY, NOT PLUMBING. The predicate was "seats of an OPEN run
// of the goal", read from the (now deleted) run register. With the layer extinguished, seat folders become
// GOAL-DURABLE (`decisions.md#d-runs-extinguished`, owner clarification): every seat a goal ever
// had persists on disk forever. A register-shaped predicate carried straight over would therefore
// have WIDENED — a stale `state=open` row, or the mere existence of the goal's accumulated seat
// tree, would grant the bus to historical seats of an execution that ended months ago. The ruling
// (item 4) is explicit that today's narrowness is preserved EXACTLY: "a seat reads/writes the
// coordination bus only while it has a live, ancestry-verified process in the goal's current
// execution — historical seat folders on disk grant nothing."
//
// So the grant is founded on `lease.js deriveLease()`:
//
//   the goal contributes a bus  ⟺  its room exists NOW  AND  at least one seat of that room has a
//                                  live process whose (pid, pid-starttime) matches its registered
//                                  pair and whose /proc ancestry reaches a pane of that room
//
// THE SEAT CONJUNCT IS LOAD-BEARING HERE AND NOWHERE ELSE. The ticker gate treats a bare room as a
// live lease (a room mid-relaunch is still an execution). AUTHZ may not: a room with no verified
// occupant is a room nobody is in, and handing the bus to a folder tree on that evidence is the
// widening the ruling forbids. The two callers legitimately read the same lease with different
// thresholds, which is why `deriveLease` reports the room and the seat set separately and decides
// neither.
//
// UNREADABLE FAILS CLOSED: `deriveLease` returning `{ok:false}` (tmux gone) contributes NO grant.
// An authz surface may not be opened on ignorance.
//
// This never creates a directory. Goal order is readdirSync's, sorted, so the composed spec is
// deterministic across spawns.
function resolveBusWriteGrants(seatPath) {
  if (!seatDeclares(seatPath.seatDir, 'bus-write')) return [];
  const grants = [];
  for (const { goal, lease } of leasedGoals(seatPath.workspaceRoot)) {
    for (const room of lease.rooms) {
      if (room.seats.length === 0) continue;   // no live occupant ⇒ no bus (the authz narrowing)
      const coordination = path.join(room.packageDir, 'coordination');
      if (fs.existsSync(coordination)) grants.push({ busWrite: coordination, busGoal: goal, busRun: room.room });
    }
  }
  return grants;
}

// The two grant resolvers' shared walk: every goal folder, its lease derived once. Spelled here so
// the authz predicate has ONE home (PRIN-11) — two copies of "which goals are executing" is the
// same drift as two copies of "is this run open" was.
function leasedGoals(workspaceRoot) {
  const goalsDir = path.join(workspaceRoot, '.rbtv', 'goals');
  let goals;
  try {
    goals = fs.readdirSync(goalsDir, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name).sort();
  } catch {
    return [];
  }
  const out = [];
  for (const goal of goals) {
    const lease = deriveLease({ workspaceRoot, goal });
    if (!lease.ok || !lease.live) continue;  // unreadable or not executing — both grant nothing
    out.push({ goal, lease });
  }
  return out;
}

// `goals-write: true` — RW on the GOAL FOLDER of every goal that is EXECUTING, so a seat holding
// the materializer (`team-kit/materialize-seats.py`) can seat a cataloged seat into a live
// execution: it writes `seats/<seat>/seat.md` and appends `taskforce.csv`, and that append is an
// atomic tmp-file-plus-rename IN THE GOAL DIR — which is why the grant is the goal dir and not
// `seats/` alone. Same lease scoping as `bus-write` above, through the same one lease reader.
//
// TWO NARROWINGS, both load-bearing:
//
//   1. THE SEAT'S OWN GOAL FOLDER IS NEVER GRANTED. A seat would otherwise re-open its own
//      goal dir read-write ON TOP of `tmpfs:{goalDir}/seats` and the `ro-bind:{seatDir}/seat.md`
//      carve — un-erasing peer seat folders and handing the occupant its own permission record.
//      (The ground-truth assertion would then refuse the whole spawn; failing closed is correct
//      but useless. Excluding the own goal keeps the grant usable AND the carves intact.)
//   2. EVERY GRANTED GOAL'S `sessions.csv` IS CARVED BACK READ-ONLY, by the second grant field
//      below and the template line that consumes it. The identity gate reads that file to decide
//      who is sitting in a goal; a cross-goal writer of it could spoof any seat's identity.
//      `assertGroundTruthUnwritable` only guards THIS seat's own sessions.csv — it cannot see the
//      other goals this grant opens, so the carve is what keeps them shut.
// 7.607 E1: same lease predicate as `resolveBusWriteGrants` above, same seat conjunct, same
// fail-closed posture — read that block for the security argument; it is not restated here. The
// TWO NARROWINGS below are untouched by the re-founding and remain load-bearing.
function resolveGoalsWriteGrants(seatPath) {
  if (!seatDeclares(seatPath.seatDir, 'goals-write')) return [];
  const grants = [];
  for (const { lease } of leasedGoals(seatPath.workspaceRoot)) {
    for (const room of lease.rooms) {
      if (room.seats.length === 0) continue;             // no live occupant ⇒ nothing to seat into
      const pkgDir = room.packageDir;
      if (!fs.existsSync(pkgDir)) continue;              // never created from here
      if (contains(pkgDir, seatPath.seatDir)) continue;  // narrowing 1 — never the seat's own home
      grants.push({ goalsWrite: pkgDir });
      const sessions = path.join(pkgDir, 'sessions.csv');
      // narrowing 2 — a SEPARATE grant so the carve line composes only where the file exists;
      // a package with no sessions.csv yet has no ground truth to carve back.
      if (fs.existsSync(sessions)) grants.push({ goalsWriteGroundTruth: sessions });
    }
  }
  return grants;
}

// `local-bin: true` — the invoking user's ~/.local/bin, READ-ONLY (D26: os.homedir(), never a
// literal). It is under the HOME tmpfs bwrap.js lays down, so this bind punches it back through.
function resolveLocalBinGrant(seatPath) {
  if (!seatDeclares(seatPath.seatDir, 'local-bin')) return [];
  const localBin = path.join(require('node:os').homedir(), '.local', 'bin');
  return fs.existsSync(localBin) ? [{ localBin }] : [];
}

// `tmux-socket: true` — the tmux server's socket DIRECTORY, READ-ONLY (owner-directed 2026-08-07).
//
// bwrap lays a `--tmpfs /tmp` on EVERY spawn, which masks that directory. So a caged seat holding
// the coordination CLI can log a message but its WAKE leg dies on
// `error connecting to /tmp/tmux-<uid>/default (No such file or directory)`: the recipient is never
// nudged, and the sender reports the socket as "not wired to this seat" — which reads as a missing
// per-seat wiring rather than the one tmpfs that hides the socket from every seat alike. Measured
// in a live channel-master sitting on 2026-08-07, and reproduced against the shipped cage.
//
// READ-ONLY IS THE WHOLE GRANT, and it is not a half-measure. `connect(2)` on a unix socket is NOT
// refused by a read-only mount — the kernel's `sb_permission` returns EROFS only for regular files,
// directories and symlinks — so `send-keys`, `capture-pane`, `display-message` and `list-panes` all
// work through it, while CREATING or DELETING a socket does not. The seat drives the rooms that
// already exist; it can neither mint nor destroy one. Both halves measured on this box, 2026-08-07.
//
// The path is tmux's OWN default — `$TMUX_TMPDIR/tmux-<uid>`, else `/tmp/tmux-<uid>` — derived from
// the daemon's environment and uid rather than named in config, for the reason D26 gives for
// `local-bin` above: a literal would write an instance path into the code tree.
function resolveTmuxSocketGrant(seatPath) {
  if (!seatDeclares(seatPath.seatDir, 'tmux-socket')) return [];
  const dir = path.join(process.env.TMUX_TMPDIR || '/tmp', `tmux-${process.getuid()}`);
  return fs.existsSync(dir) ? [{ tmuxSocketDir: dir }] : [];
}

// `exposed-clis:` — the SANDBOX realization of a prompt card's `exposes: path:` declaration
// (registry `decisions.md#d-path-exposes-authorable`, owner 2026-08-10). `path` keeps no CMP-12
// harness cell: nothing is materialized beside seat.md, so the cage IS the realization.
//
// The materializer resolves each declared part against its component's exposure.csv and writes
// `<part-id> <absolute entry point>` into the descriptor's `exposed-clis:` block list — read here
// by the SAME one declaration reader every other grant class uses. The seat never names a path:
// resolving a part-id to a manifest row is materialize's job and is not written twice (PRIN-11).
//
// BOTH ENDS, because one without the other is not a grant (7.607 E4/E4b measured a seat instructed
// to check in whose `coordinate` was on no PATH and whose team-kit target was unbound):
//   1. the CODE TREE at its real path, READ-ONLY — the entry point's own directory. A CLI reads its
//      siblings through `Path(__file__).resolve().parent`, so the script must live where it really
//      lives; a bwrap `--ro-bind` of the host's `~/.local/bin/<name>` symlink DEREFERENCES it
//      (measured on this box), landing a lone script whose siblings are gone.
//   2. the installed NAME, as a sandbox `--symlink` into a dedicated `~/.rbtv-bin` on PATH. A
//      mount the occupant cannot NAME is not a grant (the `local-bin` precedent). Its OWN dir
//      rather than `~/.local/bin` for one mechanical reason: under `local-bin: true` that
//      directory is a read-only mount, and a symlink cannot be created inside one.
// FAIL-CLOSED PER ENTRY, like `rw-paths`: a bad entry is skipped and logged, never guessed at and
// never fatal to the spawn.
const RBTV_BIN_DIRNAME = '.rbtv-bin';

function resolveExposedCliGrants(seatPath, log) {
  const grants = [];
  for (const entry of seatDeclaresList(seatPath.seatDir, 'exposed-clis')) {
    const refuse = (reason) => log('warn', `exposed-clis entry REFUSED: ${reason}`, { seat: seatPath.seat, seatDir: seatPath.seatDir, entry });
    const cut = entry.indexOf(' ');
    if (cut <= 0) { refuse('entry is `<part-id> <absolute entry point>` — no name/path separator'); continue; }
    const name = entry.slice(0, cut);
    const target = entry.slice(cut + 1).trim();
    // The name becomes a filename on PATH inside the cage: keep it to the part-id grammar so no
    // entry can escape the bin dir or shadow a shell construct.
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(name)) { refuse(`invalid part-id '${name}'`); continue; }
    if (!path.isAbsolute(target)) { refuse('entry point is not absolute — the materializer resolves it'); continue; }
    if (!fs.existsSync(target)) { refuse(`entry point does not exist: ${target}`); continue; }
    grants.push({ exposedCliName: name, exposedCliEntry: target, exposedCliCode: path.dirname(target) });
  }
  return grants;
}

function resolveSeatGrants(seatPath) {
  const worktreesDir = path.join(seatPath.workspaceRoot, '.rbtv', 'worktrees');
  let entries;
  try {
    entries = fs.readdirSync(worktreesDir, { withFileTypes: true });
  } catch {
    return [];
  }
  const suffix = `--${seatPath.goal}--${seatPath.seat}`;
  const grants = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || !entry.name.endsWith(suffix)) continue;
    const worktree = path.join(worktreesDir, entry.name);
    // repoGit/worktreeGitDir start EXPLICITLY null: since r-seats-only-architecture (5) the grant
    // list is heterogeneous and cage.js skips a grant that does not DECLARE an entry's field — so
    // a worktree grant must declare these keys even when degraded, to keep the loud path below.
    const grant = { worktree, worktreeName: entry.name, repoGit: null, worktreeGitDir: null };
    try {
      const dotGit = fs.readFileSync(path.join(worktree, '.git'), 'utf8').trim();
      const m = /^gitdir:\s*(.+)$/.exec(dotGit);
      if (m) {
        // <repo>/.git/worktrees/<name>  ->  <repo>/.git
        const gitdir = m[1].trim();
        const marker = `${path.sep}worktrees${path.sep}`;
        const idx = gitdir.lastIndexOf(marker);
        if (idx > 0) {
          grant.repoGit = gitdir.slice(0, idx);
          grant.worktreeGitDir = gitdir;
        }
      }
    } catch {
      // A worktree whose `.git` is unreadable keeps repoGit null, so every `{grant:repoGit}` entry
      // for it fails loudly at compose time rather than opening a path derived from a guess.
    }
    grants.push(grant);
  }
  return grants;
}

// ── r-seats-only-architecture (5) — HARNESS-CREDENTIAL grants ────────────────────────────────
//
// Read-only mounts for the harness credentials/config a seat is entitled to DISPATCH WITH — its
// delegation children (the orchestration skill's headless CLI workers, which run INSIDE the
// seat's cage and would otherwise find every other harness's credentials simply absent under the
// HOME tmpfs). Grant-gated exactly like the worktree grants above: no grant, no mount. The seat's
// OWN harness needs no grant here — bwrap.js binds its state back over the HOME tmpfs on every
// spawn (harnessStateBinds), read-WRITE, because a harness must write its own session state.
//
// The path table MIRRORS bwrap.js's harnessStateBinds (not exported from that module; converging
// the two is a one-line export in a file outside this change's set) — a PRIN-11 residual,
// DISCLOSED rather than hidden.
//
// ZERO GRANTS IS THE CORRECT ANSWER TODAY, and it is not a stub — the same posture the worktree
// resolver held before task 7.38 landed. No entitlement record names which harnesses a seat may
// dispatch with yet: that producer is the delegation lane's (r-seats-only-architecture (4), the
// orchestration skill's routing). When it lands, it hands harness NAMES here and the mounts
// simply appear; until then a template's `ro-bind:{grant:harnessCreds}` line composes to nothing.
const HARNESS_CRED_PATHS = {
  claude: (home) => [path.join(home, '.claude'), path.join(home, '.claude.json')],
  codex: (home) => [path.join(home, '.codex')],
  opencode: (home) => [
    path.join(home, '.config', 'opencode'),
    path.join(home, '.local', 'share', 'opencode'),
    path.join(home, '.cache', 'opencode'),
  ],
};

function resolveHarnessCredGrants(entitledHarnesses = []) {
  const home = require('node:os').homedir();
  const grants = [];
  for (const harness of entitledHarnesses) {
    const paths = HARNESS_CRED_PATHS[harness];
    if (!paths) continue; // an unknown harness has no known credential paths — nothing to mount
    for (const p of paths(home)) {
      if (fs.existsSync(p)) grants.push({ harness, harnessCreds: p });
    }
  }
  return grants;
}

// ── r-seats-only-architecture (1) — ONE cage composer for BOTH spawn doors ───────────────────
//
// The seat cage (task 7.11's SeatBinds stack) is now the ONE sandbox shape for every daemon
// spawn — the flat worker cage (workdir-only RW, nothing mounted) retires with the flat launch
// branch. Both `spawn` (headless/job) and `spawnSeat` (headed/room) compose through this single
// point, from the SEAT'S OWN records: the folder gives goal/run/seat, the grants come from the
// seat's records (worktrees + harness-credential entitlements), never from caller input (CMP-17).
//
// `assertGroundTruthUnwritable` REFUSES any composition in which the run-level sessions.csv —
// the file the identity gate reads to decide who is sitting here — would be writable from
// inside. Checked on EVERY spawn rather than once in a probe: a probe proves one composition
// sound, an assertion proves all of them (design §1).
//
// `gatewayAddr` (owner ruling "1a", `gateway-env: true`) is NOT a mount: it is emitted as a bwrap
// `--setenv` on the same flag list, because bwrap is the only layer both doors share — the headed
// door never touches the carrier's EnvironmentFile. NO TOKEN rides it; token distribution stays
// owner-out-of-band (the workspace `.env` is already readable under the read-root grant).
//
// `log` is threaded in for ONE reason: the `rw-paths` grant class refuses per entry rather than
// per spawn, and a refusal nobody can hear is a silent narrowing of a seat's declared walls. It
// defaults to a no-op so a caller with no logger still composes.
function composeCageFor(resolvedSandbox, seatPath, resolvedWorkdir, gatewayAddr = null, log = () => {}) {
  let template = resolvedSandbox && resolvedSandbox.SeatBinds;
  if (!template || template.length === 0) return null;

  // ⚠ 7.607 E2b — THE E2a `runs` MOUNTPOINT mkdir IS DELETED, on the condition E2a itself stated.
  // E2a had to `mkdirSync(<goalDir>/runs)` for every caged seat because the shipped SeatBinds
  // template still carried `tmpfs:{goalDir}/runs` and bwrap refuses a tmpfs whose mountpoint is
  // missing under a ro-bound parent. E2b deleted that template line (and `ro-bind:{runDir}`, and
  // the `{runDir}` slot) in `config/spawn-profiles.yaml`, so the mountpoint has no consumer and
  // this mkdir has no reason — and keeping it would re-create, empty, the one directory this epic
  // exists to delete. `probe-seat-rw-paths` R5a is the arm that proves a caged spawn still
  // composes against the SHIPPED template with both gone.

  if (seatPath.service) {
    // Service-seat home (r-master-seat-homes): goalDir==seatDir. Pre-create the bind
    // sources the template expects of a run folder, and carve the IN-FOLDER ground truth
    // read-only — an ordinary seat's sessions.csv lives outside its rw seatDir; here it is
    // inside, and without this carve assertGroundTruthUnwritable below correctly refuses.
    // Appended LAST so it shadows the rw {seatDir} bind (order is the mechanism, as in the
    // template's own seat.md carve).
    fs.mkdirSync(path.join(seatPath.goalDir, 'coordination'), { recursive: true });
    // …and the tmpfs MOUNTPOINTS: bwrap cannot mkdir them once the read-root grant has made
    // the folder ro (measured: exec 19427). tmpfs over an existing empty dir is the same
    // absence the template intends.
    //
    fs.mkdirSync(path.join(seatPath.goalDir, 'seats'), { recursive: true });
    if (!fs.existsSync(seatPath.sessionsCsv)) fs.writeFileSync(seatPath.sessionsCsv, '');
    template = [...template, 'ro-bind:{seatDir}/sessions.csv'];
  }
  // Resolved ONCE: the same grant decides the mount below and the PATH entry after it. Two
  // resolutions would be two answers the first time either gained a case.
  const localBin = resolveLocalBinGrant(seatPath);
  // Same rule, same reason: the ONE resolution decides the mount, the symlink AND the PATH entry.
  const exposedClis = resolveExposedCliGrants(seatPath, log);
  if (exposedClis.length > 0) {
    // Appended in code rather than added to `config/spawn-profiles.yaml`'s SeatBinds, exactly as
    // the service seat's `ro-bind:{seatDir}/sessions.csv` line above is: the line has no meaning
    // for a seat with no grant, and cage.js skips a `{grant:…}` line whose grant list is empty.
    // LAST, and that ORDER IS THE SAFE ONE — but not for the reason a first reading suggests:
    // in bwrap the LATER argument WINS (measured: `--bind sub` then `--ro-bind tree` leaves
    // `tree/sub` read-only; the reverse order leaves it writable). So appending last means this
    // read-only code tree SHADOWS any writable opening the stack made above it under the same
    // path — which is the posture we want for a code tree, and is why it is not moved earlier.
    // ⚠ The consequence, stated so it is not discovered by surprise: an `rw-paths` grant pointing
    // INSIDE a granted CLI's directory is silently downgraded to read-only — no refusal, no log.
    // That is ONE CSV CELL away, not hypothetical: `rw-paths` is a live seats.csv column that
    // materialize emits into this same frontmatter, and a seat already populates it (channel-master).
    // No seat points one at a granted CLI's directory TODAY (verified 2026-08-10); if one ever
    // does, it must be REFUSED at compose time here, not silently ignored by mount order.
    template = [...template, 'ro-bind:{grant:exposedCliCode}'];
  }
  const spec = composeSeatCage({
    seatBinds: template,
    values: {
      workdir: resolvedWorkdir,
      seatDir: seatPath.seatDir,
      goalDir: seatPath.goalDir,
    },
    grants: [
      ...resolveSeatGrants(seatPath),
      ...resolveHarnessCredGrants(),
      ...resolveReadRootGrant(seatPath),
      ...resolveBusWriteGrants(seatPath),
      ...resolveGoalsWriteGrants(seatPath),
      ...localBin,
      ...exposedClis,
      ...resolveTmuxSocketGrant(seatPath),
      ...resolveGoalWriteGrants(seatPath, log),
      ...resolveRwPathGrants(seatPath, log),
    ],
  });
  assertGroundTruthUnwritable(spec, seatPath.sessionsCsv);
  const flags = specToBwrapFlags(spec);
  // ── r-seat-context-cut-at-launch-folder — the ANCESTOR MASK, appended LAST ────────────────
  // Last is the mechanism, exactly as it is for every other line of this stack: the mask must
  // shadow the read-root ro floor and the goal/run ro-binds that made those ancestors visible in
  // the first place. Composed for BOTH doors here because both compose through this function.
  // `keep-instruction-files: true` is the channel policy (ruling bound (ii)) — a seat.md
  // declaration read by the same one declaration reader every other grant class uses.
  const mask = composeAncestorMasks(spec, {
    workspaceRoot: seatPath.workspaceRoot,
    launchFolder: resolvedWorkdir,
    keepInstructionFiles: seatDeclares(seatPath.seatDir, 'keep-instruction-files'),
  });
  flags.push(...mask.flags);
  log('info', 'ancestor harness artifacts masked', { policy: mask.policy, ...mask.masked });
  if (gatewayAddr && seatDeclares(seatPath.seatDir, 'gateway-env')) {
    flags.push('--setenv', 'IGNITE_GATEWAY_ADDR', gatewayAddr);
  }
  // …and PATH, for the same reason the bind exists. A caged session inherits the systemd --user
  // manager's PATH, which does NOT contain ~/.local/bin (the same fact the restart-daemon job
  // notes in spawn-profiles.yaml). So `local-bin: true` mounted the user CLIs at a path nothing
  // would ever look in: the seat is PROMISED `coordinate`, `teamview`, `gtools`, `sb-task`,
  // `ignite`, `scaffold-seats` by name, and every one of them resolved to "command not found" —
  // measured in a live channel-master sitting, 2026-08-06. A mount the occupant cannot NAME is
  // not a grant. Emitted only WITH the grant, so a seat without it sees no PATH change at all.
  //
  // The `exposed-clis:` grants take the same shape and the same reason — a declared CLI is
  // PROMISED BY NAME, so the sandbox symlink carrying that name goes on PATH FIRST (ahead of
  // ~/.local/bin, whose same-named symlink dereferences to a code tree an ordinary seat has no
  // grant for). The symlinks are raw flags rather than spec entries because cage.js's verb set is
  // bind/ro-bind/tmpfs and a symlink is not a mount — the same reason the ancestor mask above
  // pushes `--ro-bind /dev/null <file>` directly. They land AFTER bwrap.js's `--tmpfs <home>`
  // (which is emitted before this whole stack), so bwrap creates the bin dir on that tmpfs.
  const pathDirs = [];
  if (exposedClis.length > 0) {
    const rbtvBin = path.join(require('node:os').homedir(), RBTV_BIN_DIRNAME);
    for (const g of exposedClis) {
      flags.push('--symlink', g.exposedCliEntry, path.join(rbtvBin, g.exposedCliName));
    }
    pathDirs.push(rbtvBin);
    log('info', 'exposed CLIs enabled in the seat sandbox', { seat: seatPath.seat, clis: exposedClis.map((g) => g.exposedCliName) });
  }
  if (localBin.length > 0) pathDirs.push(localBin[0].localBin);
  if (pathDirs.length > 0) {
    const base = process.env.PATH || '/usr/local/bin:/usr/bin:/bin';
    // Prepend, then DEDUPE preserving first-seen order: the daemon's own PATH may already carry
    // ~/.local/bin (or repeat entries from a shell that sourced a profile twice), and a caged
    // session should not inherit that noise in a variable this module is now the author of.
    const dirs = [...new Set([...pathDirs, ...base.split(':').filter(Boolean)])];
    flags.push('--setenv', 'PATH', dirs.join(':'));
  }
  return flags;
}

function createSpawnManager({ heartStore, configPath, logger = null, userManager = true }) {
  const config = loadConfig(configPath);
  const dataRoot = config.spawn.data_root;
  if (!dataRoot) {
    throw new SpawnError(E_MISSING_KEY, 'spawn.data_root is required', { key: 'spawn.data_root' });
  }

  // The workspace root is derived once, from the heart store's own `.rbtv/` location. It resolves
  // machine-agnostic (workspace-relative) profile workdir_roots. The D58(1) sessions root that was
  // also derived here is GONE: the flat `.rbtv/sessions/<exec-id>/` launch branch is retired
  // (r-seats-only-architecture (3) — a dispatch with no home is a refusal, not a flat dir), so
  // nothing on this module materializes a per-execution dir outside a seat folder any more.
  const workspaceRoot = resolveWorkspaceRoot(heartStore && heartStore.dbPath);

  // The daemon's OWN gateway address, derived exactly as server/index.js derives its bind (same
  // env overrides, same config keys, same defaults) — a seat declaring `gateway-env: true` gets it
  // as IGNITE_GATEWAY_ADDR. Loopback is reachable inside the cage: bwrap keeps `--share-net`.
  const gatewayAddr = `${process.env.RBTV_IGNITE_BIND_HOST || config.bind?.host || '127.0.0.1'}:`
    + `${Number(process.env.RBTV_IGNITE_BIND_PORT || config.bind?.port) || 7431}`;

  function log(level, message, extra = {}) {
    if (logger) logger({ level, message, ...extra });
  }

  // `resumeRef` is DAEMON-INTERNAL (r-chat-chain-resumes-session): it is never a request key —
  // no gateway caller supplies it — so it stays out of validateRequestKeys below. The ticker
  // passes the predecessor turn's `jobs_log.session_ref`; every other caller passes nothing.
  // `effort` is DAEMON-INTERNAL in the same sense `resumeRef` is: the ticker reads it off the queue
  // row's args (the catalogue job whose schema admits it) and passes it here; no gateway caller
  // supplies it directly, so it stays out of validateRequestKeys below.
  async function spawn(execId, profileName, sessionMode = 'headless', prompt = null, workdir = null, enqueuedBy = 'unknown', resumeRef = null, effort = null) {
    // Strict request-key validation for object-style callers (gateway path).
    validateRequestKeys({ profile: profileName, session_mode: sessionMode, prompt, workdir });

    rejectFlagInjection(workdir, 'workdir');

    // ── THE SEAT'S CAST WINS (task 7.54 · D19) ───────────────────────────────────────────────
    // Resolved FIRST, so every gate below — unknown-profile, exec shape, resume template, headed
    // capability, workdir root — runs against the profile that will ACTUALLY launch rather than
    // the one the caller asked for. Doing it after those gates would validate one profile and
    // spawn another, which is the same class of lie in a new place.
    //
    // ponytail: reads the cast off the RAW `workdir`, before `resolveWorkdir` normalizes it. Every
    // daemon caller passes an absolute seat folder already (the ticker composes it, the chat
    // bridge passes `resolveGoalSeat().seatDir`), and `composeArgv` reads `seat.md` off this same
    // value a few lines later. Ceiling: a RELATIVE workdir resolves no descriptor, so its cast is
    // not honoured — it falls back to the caller's profile exactly as before. Upgrade path if a
    // relative-workdir caller ever appears: resolve the workdir first and re-run the gates.
    profileName = profileForSeatCast(config.profiles || {}, workdir, profileName, log);

    // An OWN-property test, never a bare lookup: `config.profiles` is a plain object parsed from
    // YAML, so a request naming an INHERITED key (`constructor`, `toString`, `valueOf`) passes a
    // truthiness guard and hands the next line a FUNCTION where a profile object belongs. Same
    // shape the C5 sweep applied to ticker.js and heart-store.js's catalogue lookups (task 7.542).
    if (!Object.hasOwn(config.profiles || {}, profileName)) {
      throw new SpawnError(E_UNKNOWN_PROFILE, `unknown launch profile: ${profileName}`, { profile: profileName });
    }
    const profile = config.profiles[profileName];
    requireExecShape(profile, profileName); // G-144 — door 1 (composeArgv's `profile.exec`)

    // A resume asked of a profile that declares no resume template is REFUSED, not silently
    // downgraded to a fresh spawn: the caller composed a new-messages-only prompt for it, and
    // launching that prompt against an empty session would drop the conversation. The ticker
    // checks the template before it composes; this is the door saying so on its own authority.
    if (resumeRef && !profile.resume) {
      throw new SpawnError(E_UNKNOWN_MODE, `profile ${profileName} declares no resume template`, { profile: profileName });
    }

    if (!SESSION_MODES.has(sessionMode)) {
      throw new SpawnError(E_UNKNOWN_MODE, `invalid session_mode: ${sessionMode}`, { sessionMode });
    }
    if (sessionMode === 'headed' && !profile.headed) {
      throw new SpawnError(E_HEADED_NOT_CAPABLE, `profile ${profileName} is not headed-capable`, { profile: profileName, sessionMode });
    }

    // NO prompt flag-injection guard: the carriage collapse (batch-08 item 4 half A — headless
    // `stdin` only, headed `file`|`keystroke` only) means NO carriage puts caller text on a
    // command line, so there is nothing for a prompt guard to protect. The prompt is 0600-file
    // DATA everywhere (a composed multi-turn transcript legitimately carries newlines and
    // parentheses). The workdir guard above stays UNCONDITIONAL: a workdir always rides
    // argv/unit properties.

    // ── r-seats-only-architecture (3) · NO HOME, NO SPAWN ────────────────────────────────────
    //
    // A launch with NO workdir used to fall through to resolveWorkdir's default branch, which
    // MATERIALIZED the flat `.rbtv/sessions/<exec-id>/` launch dir. That branch is RETIRED for
    // every daemon spawn: "a dispatch with no home is a refusal, not a flat dir". Refused HERE,
    // before resolveWorkdir, because the default branch's side effect is the very dir this
    // ruling removes — a refusal after it would leave the flat dir on disk anyway.
    if (workdir === undefined || workdir === null) {
      throw new SpawnError(
        E_SEATLESS_GOAL_DISPATCH,
        `REFUSING SEATLESS DISPATCH: launch of profile ${profileName} names no home — ` +
        'MISSING FIELD: workdir (a canonical seat folder ' +
        '<ws>/.rbtv/goals/<goal>/seats/<seat>/, resolved from the job row\'s ' +
        'goal_name/seat_name or the dispatch args). The flat .rbtv/sessions/<exec-id>/ launch ' +
        'branch is RETIRED (r-seats-only-architecture: every daemon-spawned agent is a seat).',
        { profile: profileName, missingField: 'workdir', sessionMode },
      );
    }

    const resolvedWorkdir = resolveWorkdir(profile, workdir, config.default_workdir_root, configPath, { execId, workspaceRoot });

    // ── THE DISPATCH DOOR (task 7.75, WIDENED by r-seats-only-architecture (3)) ──────────────
    //
    // The owner's rider on `r-headless-visibility` — "every headless session attributed to a SEAT,
    // no seat-less rows in the snapshot" — enforced BY CONSTRUCTION rather than by filtering: a
    // headless session that names no seat is not hidden downstream, it never comes into
    // existence. This is the ONE door it would pass. `server/index.js` routes session_mode
    // `headed` to spawnSeat (which has carried its own §4a gate since 7.11) and EVERYTHING ELSE
    // here, and the ticker's dispatch phase is the only caller of either — so the two halves of
    // the daemon's launch surface are gated, not one.
    //
    // 7.75's gate fired only INSIDE `.rbtv/goals/`; the exemptions it carried — the sub-agent
    // lane and the machine-lane flat dispatches — RETIRE with the lane and the flat branch
    // (r-seats-only-architecture (3)/(4)): delegation is seat-side now, and every daemon spawn
    // resolves a seat folder or is refused. What still never reaches this function:
    // `fire-tool` / `start-workflow` / `send-message` execs (ticker.js runToolLikeExec goes
    // straight to the carrier). THE RECOVERY PATH IS ONE OF THEM — `selfheal-room`,
    // `selfheal-watch`, `restart-daemon` are all `fire-tool` — which is why arming this gate
    // cannot disarm the repair (the leader's G-52 mirror-trap rider, #465).
    //
    // A refusal here is a REAL refusal: it is raised before any harness config, session dir, unit,
    // pane or store row past `launching` exists — the same absence-proven standard §4a set.
    const dispatchSeat = parseSeatPath(resolvedWorkdir) || parseServiceSeatPath(resolvedWorkdir);
    if (!dispatchSeat) {
      throw new SpawnError(
        E_SEATLESS_GOAL_DISPATCH,
        `REFUSING SEATLESS DISPATCH: ${resolvedWorkdir} is not a canonical seat folder ` +
        `(<ws>/.rbtv/goals/<goal>/seats/<seat>/). MISSING FIELD: seat — the ` +
        'dispatch-time record is the ONLY authority for session->seat attribution (G-31), so a ' +
        'session with no seat to record could never be attributed at all. Supply a seat-folder ' +
        'workdir, or home the job at a (goal, seat) pair (r-seats-only-architecture: a dispatch ' +
        'with no home is a refusal, not a flat dir).',
        { workdir: resolvedWorkdir, missingField: 'seat', profile: profileName, sessionMode },
      );
    }

    // D58(4): materialize the advisory harness-local write-restraint config into the launch dir.
    // The kernel sandbox (resolveSandbox below) is the LOAD-BEARING layer; this is the second belt.
    const resolvedSandbox = resolveSandbox(profile.sandbox, resolvedWorkdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== resolvedWorkdir);
    })();
    try {
      const hc = materializeHarnessConfig({ sessionDir: resolvedWorkdir, profile, editablePaths });
      if (hc && hc.written) log('info', 'harness config materialized', { harness: hc.harness, path: hc.written, enforceable: hc.enforceable });
    } catch (err) {
      log('warn', 'harness config materialization failed (advisory layer; kernel sandbox is authoritative)', { error: err.message });
    }

    const sessionId = generateSessionId();
    const logPath = ensureLogPath(dataRoot, sessionId);
    const { argv: composedArgv, stdinFile } = composeArgv(profile, sessionMode, sessionId, resolvedWorkdir, prompt, dataRoot, resumeRef, effort, profileName);

    // Task 7.444 (MC2) — carry the profile's `--settings` file INTO the cage. See harness-config.js
    // for why this is a materialization rather than a widened SeatBinds template. Done here, after
    // composition and before the argv is wrapped, so the bwrap wall below sees the final paths.
    const settings = planCagedSettings(composedArgv, resolvedWorkdir);
    const argv = settings.argv;
    materializeCagedSettings(settings.copies);
    for (const c of settings.copies) log('info', 'settings materialized into the launch dir', { from: c.src, to: c.dest });

    // D59: bwrap FS walls nested inside the systemd-run --user unit. The wrapped argv rides the
    // carrier opaquely (both systemd and setsid branches); the walls live in argv, not config.
    // No promptFile bind: the sole headless carriage is stdin (fd 0 opens before the wrap execs);
    // headed prompt files were bound by the pty host's own buildBwrapArgv call (module deleted at 7.29).
    //
    // r-seats-only-architecture (1): the SEAT CAGE is the one sandbox for this door too. When the
    // profile's (config-shared) SeatBinds template is present it REPLACES the flat workdir opening
    // inside buildBwrapArgv, composed around THIS dispatch's seat by the same single composer
    // spawnSeat uses. A profile with no template still gets the v1 workdir-only wall — a config
    // state, not a code branch kept on purpose.
    const maskPaths = config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [];
    const seatCage = composeCageFor(resolvedSandbox, dispatchSeat, resolvedWorkdir, gatewayAddr, log);
    const wrappedArgv = buildBwrapArgv({ argv, workdir: resolvedWorkdir, editablePaths, harness: harnessOf(profile), maskPaths, seatBinds: seatCage });

    const carrier = selectCarrier(config.spawn.carrier, userManager);

    // Write the session_id and log_path immediately so the row is identifiable
    // even if the carrier launch fails part-way.
    heartStore.updateExecutionStatus(execId, {
      status: 'launching',
      sessionId,
      logPath,
    });

    const common = { sessionId, argv: wrappedArgv, workdir: resolvedWorkdir, logPath, stdinFile, exitFile: ensureExitFile(dataRoot, sessionId), caps: profile.caps, sandbox: resolvedSandbox, envFile: profile.env?.file, userManager };
    let launchResult;
    try {
      if (carrier === 'systemd') {
        launchResult = await spawnSystemd(common, log);
      } else {
        launchResult = await spawnSetsid(common, log);
      }
    } catch (err) {
      heartStore.updateExecutionStatus(execId, {
        status: 'failed',
        endedAt: new Date(),
      });
      throw new SpawnError(E_CARRIER_FAILED, `spawn failed for profile ${profileName}: ${err.message}`, { profile: profileName, execId, cause: err.code });
    }

    const sessionRef = captureSessionRef(profile, launchResult, resolvedWorkdir, resumeRef || sessionId);
    let pid = launchResult.pid || null;
    const unitName = launchResult.unitName || null;
    if (carrier === 'systemd' && unitName && !pid) {
      const info = systemdStatus(unitName, userManager);
      pid = info.pid || null;
    }
    const pidStarttime = await resolvePidStarttime(carrier, pid, unitName);
    const startedAt = new Date();

    // ── Task 7.75 · THE AT-DISPATCH RECORD ───────────────────────────────────────────────────
    //
    // The other half of the clause, and the half that makes the refusal above worth having: an
    // admitted goal-scoped dispatch writes its `sessions.csv` row HERE, in the dispatching act,
    // keyed by the same `session_id` the `jobs_log` row carries — which is exactly what task
    // 7.73's join reads. NEVER post-hoc, never inferred: no pane matching, no workdir heuristic,
    // no reconciliation pass afterwards (G-31, design-760 §3). A row written later, by anyone
    // else, from anything other than the dispatch itself, is not this record.
    //
    // Written by the SAME writer spawnSeat uses (seat-identity/csv.js appendRow, by column name
    // against the file's own header) — deliberately not a second spelling of the row: two writers
    // of one schema is how the run-1 and run-2 headers came to disagree. `dropped` columns are
    // REPORTED, never invented from this side; task 7.37 owns the schema.
    //
    // Failure is LOUD and never fatal: a process is already running at this point, so refusing the
    // launch here would leave a live session with a failed launch record. The warning says the
    // session will be unattributable, which is precisely the incident 7.73's
    // `headless_unattributed` field surfaces rather than guesses at.
    if (dispatchSeat) {
      try {
        const written = appendRowEnsuringHeader(dispatchSeat.sessionsCsv, {
          seat: dispatchSeat.seat,
          'session-id': sessionId,
          harness: harnessOf(profile) || '',
          // THE PREVENTION GUARANTEE for the wrong-model defect (design proposal §2 defect 9):
          // the model that ACTUALLY launched, read off the resolved profile's own pin — never off
          // the seat's declaration, which is the claim being checked, and never off the caller's
          // request. With it, a divergence between what a seat is cast as and what it ran is
          // visible in the seat's OWN trace instead of only in the system journal.
          //
          // ⚑ OFFERED, NOT IMPOSED. `appendRow` writes BY COLUMN NAME against the file's own
          // header and REPORTS unknown keys as `dropped` rather than inventing a column — and
          // `coord.py#SESSIONS_COLS` owns this schema (task 7.37), not this writer. So on a
          // deployment whose header has no `model` column this is a no-op with a warn, and it
          // starts recording the moment the schema owner adds one. A second spelling of the
          // header here is exactly how the run-1 and run-2 headers came to disagree.
          model: (bindingOf(profile) || {}).model || '',
          workdir: resolvedWorkdir,
          pid,
          'pid-starttime': pidStarttime,
          tty: '',
          'worktree-path': (resolveSeatGrants(dispatchSeat)[0] || {}).worktree || '',
          started: isoNow(),
        }, log);
        if (!written.appended) {
          log('warn', 'at-dispatch session row NOT recorded — this headless session will be UNATTRIBUTABLE', {
            seat: dispatchSeat.seat, sessionsCsv: dispatchSeat.sessionsCsv, sessionId, reason: written.reason,
          });
        } else if (written.dropped.length > 0) {
          log('warn', 'session log lacks columns; they were dropped, not invented (task 7.37 owns the schema)', {
            seat: dispatchSeat.seat, sessionsCsv: dispatchSeat.sessionsCsv, dropped: written.dropped,
          });
        }
      } catch (err) {
        log('warn', 'at-dispatch session row append failed — this headless session will be UNATTRIBUTABLE', {
          seat: dispatchSeat.seat, sessionsCsv: dispatchSeat.sessionsCsv, sessionId, error: err.message,
        });
      }
    }

    const updated = heartStore.updateExecutionStatus(execId, {
      status: 'running',
      carrier,
      unitName,
      pid,
      pidStarttime,
      sessionRef,
      startedAt,
      logPath,
      sessionId,
      profile: profileName,
      workdir: resolvedWorkdir,
    });

    // Return the fresh row with workdir filled from the original recordExecutionStart value.
    const fresh = heartStore.getExecution(execId);
    if (fresh) fresh.workdir = resolvedWorkdir;
    return fresh;
  }

  // ── Task 7.30 — the SEAT spawn: a headed session landing in a tmux pane (R7/R8/R15/R28) ────
  //
  // The gate does not move: this is still the daemon's own door, reached by profile NAME, and no
  // caller free text reaches argv. What moves is the TARGET — a pane in the goal's run-scoped room
  // instead of the server-owned pty unit task 7.29 deleted. Composition (and the reasons for each layer) lives in
  // ./tmux.js; this function is the daemon-side half: resolve, compose, launch, record identity.
  //
  // R7's division of labour, which is the whole point of "profiles stay pure mechanism":
  //   the PROFILE gives  exec/argv, caps, sandbox binds, session_ref     — mechanism only
  //   the SEAT DESCRIPTOR gives  role, briefing, workdir                 — everything cognitive
  // So the briefing never rides argv. It is a FILE the harness reads from its own launch dir, which
  // is why `seatDir` here becomes the workdir and nothing else.
  //
  // `dryRun: true` composes and returns WITHOUT creating a pane or writing a store row. It exists
  // because composition is the half that is checkable off a live room — the probe uses it, and so
  // does any caller that wants to see the exact argv before it runs.
  async function spawnSeat(execId, profileName, { room, seatName, seatDir, dryRun = false, enqueuedBy = 'unknown', readLease = undefined, effort = null } = {}) {
    // The seat's cast wins here too (D19), and for the same reason it does on the headless door:
    // the two doors are the daemon's whole launch surface, and a seat that ran its cast headless
    // but the caller's profile in a pane would be one seat wearing two models. Resolved BEFORE the
    // gates below so they validate what actually launches. `seatDir` is this door's explicit
    // argument, so there is no relative-path ceiling here.
    profileName = profileForSeatCast(config.profiles || {}, seatDir, profileName, log);

    // An own-property test, for the reason given at the request-validation door above (task
    // 7.542): a bare lookup admits every inherited key of `Object.prototype` as a profile name.
    if (!Object.hasOwn(config.profiles || {}, profileName)) {
      throw new SpawnError(E_UNKNOWN_PROFILE, `unknown profile: ${profileName}`, { profile: profileName });
    }
    const profile = config.profiles[profileName];
    requireExecShape(profile, profileName); // G-144 — door 2 (the `profile.exec.argv` read below)
    if (!seatDir) {
      throw new SpawnError(E_BAD_REQUEST, 'seat spawn requires seatDir — the seat descriptor folder supplies role/briefing/workdir (R7)', { profile: profileName });
    }

    // The workdir gate is REUSED, not relaxed. A seat folder outside the profile's `workdir_root`
    // is refused with E_WORKDIR_ESCAPE — the same containment boundary every other spawn crosses.
    // DISCLOSED, not silently worked around: until task 7.11 redesigns the writable set (owner
    // ruling `r-711-write-bounds` pre-binds it to own seat folder + own worktree + git plumbing),
    // a seat folder living outside that root cannot be spawned into. That is a need to SURFACE,
    // which is exactly what the ruling's rider asks for — never a boundary to widen here.
    const resolvedWorkdir = resolveWorkdir(profile, seatDir, config.default_workdir_root, configPath, { execId, workspaceRoot });

    // ── Task 7.11 §4a — THE LAUNCH-TIME IDENTITY GATE ───────────────────────────────────────
    //
    // Three checks, ALL of which must hold or the launch is REFUSED with a typed error before any
    // pane, unit, session dir or store row past `launching` exists. That absence is the proof the
    // acceptance bars ask for (P1/P2/P3): a refusal MESSAGE only shows the tool said no, never
    // that nothing happened.
    //
    // These run on the SEAT path only — but the divergence they once marked is closed: the
    // ticker/job branch (`spawn`, above) left `.rbtv/sessions/` too (r-seats-only-architecture
    // completed 7.11 §5's staged retirement). What stays seat-door-only is L2/L3's rostered-seat
    // strictness; the job door materializes job-born seats instead (resolveSeatHome, ticker.js).
    //
    // L1 — canonical seat-folder shape. `resolveWorkdir` above already refused anything outside
    // the profile's workdir_root (E_WORKDIR_ESCAPE, the mechanism REUSED not relaxed); this adds
    // that the resolved path is a seat folder AT ALL. A profile whose workdir_root still points
    // at `.rbtv/sessions` makes every flat interim dir fail here — which is exactly how the
    // interim path is retired for seats: not by deleting anything, but by ceasing to be a shape a
    // seat can launch into.
    const seatPath = parseSeatPath(resolvedWorkdir);
    if (!seatPath) {
      throw new SpawnError(
        E_WORKDIR_ESCAPE,
        `seat spawn requires a canonical seat folder ` +
        `(<ws>/.rbtv/goals/<goal>/seats/<seat>/); ${resolvedWorkdir} is not one. ` +
        'The flat .rbtv/sessions/<exec-id>/ interim path is retired for seat spawns (task 7.11 §5).',
        { workdir: resolvedWorkdir, profile: profileName, seat: seatName },
      );
    }
    if (seatName && seatName !== seatPath.seat) {
      // The folder decides. A caller-supplied name that disagrees with it is refused rather than
      // preferred — an asserted name outranking a derived one is precisely G-111, where two agents
      // spoke under a single roster row for an hour because the assertion won.
      throw new SpawnError(
        E_NOT_A_SEAT_FOLDER,
        `seat name "${seatName}" contradicts the seat folder "${seatPath.seat}" (${resolvedWorkdir}) — ` +
        'the folder is the identity; a supplied name never overrides it',
        { seatName, folderSeat: seatPath.seat, workdir: resolvedWorkdir },
      );
    }

    // L2 — the goal is known and it is EXECUTING RIGHT NOW.
    //
    // 7.607 E2a: this was `checkRunLive` reading `<goal>/runs.csv`. The register is extinguished,
    // so the same adapter every other L2 caller uses now routes the question to the derived lease
    // (`server/lease/lease.js`) — same shape, same fail-closed posture, live evidence instead of a
    // stored status. `readLease` is injectable so a probe supplies a fixture tmux server rather
    // than this path growing an assertion channel.
    const live = checkGoalExecuting(seatPath, readLease ? { readLease } : undefined);
    if (!live.ok) {
      throw new SpawnError(
        E_GOAL_NOT_LIVE,
        `refusing to spawn into ${resolvedWorkdir}: ${live.reason}`,
        { workdir: resolvedWorkdir, goal: seatPath.goal, reason: live.reason },
      );
    }

    // L3 — a MATERIALIZED, ROSTERED seat: `seat.md` naming this folder, plus a taskforce row.
    const materialized = checkMaterializedSeat(seatPath);
    if (!materialized.ok) {
      throw new SpawnError(
        E_NOT_A_SEAT_FOLDER,
        `refusing to spawn into ${resolvedWorkdir}: ${materialized.reason}`,
        { workdir: resolvedWorkdir, seat: seatPath.seat, reason: materialized.reason },
      );
    }

    const resolvedSandbox = resolveSandbox(profile.sandbox, resolvedWorkdir);
    const editablePaths = (() => {
      const rwp = resolvedSandbox && resolvedSandbox.ReadWritePaths;
      if (!rwp) return [];
      return (Array.isArray(rwp) ? rwp : [rwp]).filter((p) => p && p !== resolvedWorkdir);
    })();

    // Headed argv when the profile is headed-capable, else its plain exec argv (R8: one door, the
    // existing mode flag). No prompt carriage: a seat is driven by its descriptor and by the room.
    // Task 7.444 (MC2) — the SAME carry-into-the-cage step as the headless door above, swept here
    // in the same change: this door's fallback composes `profile.exec.argv`, so any profile with
    // no `headed:` block that names a `--settings` file meets the identical wall. No claude
    // profile reaches the fallback today (all four declare a TUI, and the TUI argv names no
    // settings file) — which is exactly why leaving this door out would have been a latent defect
    // rather than an observable one. PLANNED here and COPIED past the dryRun return below: the
    // probe must see the real argv without this composition leaving a file behind.
    // The EFFORT RUNG rides this door too, through the SAME one interpreter `composeArgv` uses
    // (`resolveEffort` — never a second reading of the `effort:` table). A seat door that composed
    // its own argv and skipped the ladder ran the harness default while the tick log reported the
    // rung, which is precisely the silent drop G-270 forbids. Null composes nothing, so every
    // caller that passes no rung is byte-unchanged; an out-of-range rung refuses here exactly as
    // it does headless, and an inert dial accepts and emits nothing.
    const harnessArgvRaw = [
      ...((profile.headed && profile.headed.tui && profile.headed.tui.argv) || profile.exec.argv),
      ...resolveEffort(profile, effort, profileName).argv,
    ];
    const settings = planCagedSettings(harnessArgvRaw, resolvedWorkdir);
    const harnessArgv = settings.argv;
    const sessionId = generateSessionId();
    const maskPaths = config.auth?.senders_file ? [path.dirname(config.auth.senders_file)] : [];

    // ── Task 7.11 §2 — the SEAT CAGE, via the ONE composer both doors share ─────────────────
    // (composeCageFor above — r-seats-only-architecture (1)). Slots resolve from the SEAT'S OWN
    // RECORDS; nothing here reads caller input (CMP-17), and the ground-truth assertion runs on
    // every spawn.
    const seatCage = composeCageFor(resolvedSandbox, seatPath, resolvedWorkdir, gatewayAddr, log);

    // Composition FIRST — and this ordering is the fail-closed guarantee, not a style choice.
    // composeSeatSpawn runs buildBwrapArgv before it builds any tmux argv, so on a box without
    // bwrap this throws E_FS_SANDBOX_UNAVAILABLE and NO PANE IS EVER CREATED: the seat is not
    // spawned unconfined, it is not spawned at all (D59, and 7.30's own criterion).
    // The window name falls back to the FOLDER'S OWN seat name, never the profile name (task 7.11
    // — G9). Two reasons, both measured: a caller that wants a safe window name should not have to
    // supply `seatName`, because supplying it also asserts an identity (`:487` above refuses a
    // disagreement) — that conflation made the only production call site unable to spawn any real
    // seat. And `profileName` is the WRONG fallback regardless: every seat sharing a profile would
    // collide on one window name. `seatPath.seat` is derived from the resolved workdir, which has
    // already passed the workdir_root containment gate and parseSeatPath's shape check, and
    // assertTmuxName still refuses `:`/`.`/whitespace — so this is a derived-and-validated name,
    // which is the same standard that makes the `:487` refusal correct.
    const composed = composeSeatSpawn({
      room,
      windowName: seatName || seatPath.seat,
      sessionId,
      workdir: resolvedWorkdir,
      harnessArgv,
      caps: profile.caps,
      editablePaths,
      harness: harnessOf(profile),
      maskPaths,
      seatBinds: seatCage,
      userManager,
    });

    // dryRun returns BEFORE anything is written — no session dir, no session row, no store row.
    // That is what makes it safe to point a probe at a live package: composition is the half that
    // is checkable off a live room, and it must leave no trace to be worth checking.
    if (dryRun) return { dryRun: true, sessionId, ...composed, workdir: resolvedWorkdir, seatCage, seat: seatPath.seat };

    // Past the dryRun return: NOW the planned settings copies may touch disk (task 7.444).
    materializeCagedSettings(settings.copies);
    for (const c of settings.copies) log('info', 'settings materialized into the launch dir', { from: c.src, to: c.dest });

    // §4a on pass — the session artifact scratchpad, under the seat folder (task 7.11 criteria:
    // "session artifacts land in sessions/{session-id}/ under it").
    const sessionDir = path.join(seatPath.seatDir, 'sessions', sessionId);
    fs.mkdirSync(sessionDir, { recursive: true, mode: 0o700 });

    heartStore.updateExecutionStatus(execId, { status: 'launching', sessionId });
    log('info', 'seat spawn', { room, seat: seatName, unit: composed.unitName, argv: composed.tmuxArgv });

    const { paneId, panePid } = await runTmux(composed.tmuxArgv);

    // Identity is recorded as the PAIR the daemon already trusts everywhere else — pid plus
    // /proc stat field 22 starttime — because a pid alone is reusable, and because the pane alone
    // is NOT identity either: an in-place respawn reuses the pane id (run issue G-12). The scope
    // unit name is the third handle, and the only one a respawn cannot reproduce.
    const pidStarttime = panePid ? (setsidStatus(panePid).pidStarttime || null) : null;

    // ── Task 7.11 §4a — register the occupant in the run-level session log ───────────────────
    //
    // This is the row the COMMAND-TIME gate later matches live /proc against, so it is written
    // from OUTSIDE every cage (the daemon), to a file §2 leaves unwritable from INSIDE every cage.
    // That asymmetry is the whole design: whoever can rewrite this file decides who anyone is.
    //
    // Written BY COLUMN NAME against the file's own header (see seat-identity/csv.js). Task 7.37
    // owns the settled schema; measured 2026-07-27 it carries none of the identity columns, so
    // `appendRow` reports what it had to DROP rather than inventing columns from this side.
    // Widening a schema from the writer is how the run-1 and run-2 headers came to disagree, and
    // the gate's own answer to a log that cannot name an occupant is a typed refusal — a loud
    // failure later, never a silent pass.
    try {
      const written = appendRowEnsuringHeader(seatPath.sessionsCsv, {
        seat: seatPath.seat,
        'session-id': sessionId,
        harness: harnessOf(profile) || '',
        workdir: resolvedWorkdir,
        pid: panePid,
        'pid-starttime': pidStarttime,
        tty: '',
        'worktree-path': (resolveSeatGrants(seatPath)[0] || {}).worktree || '',
        started: isoNow(),
      }, log);
      if (!written.appended) {
        log('warn', 'session row NOT recorded — the identity gate will refuse commands from this seat', {
          seat: seatPath.seat, sessionsCsv: seatPath.sessionsCsv, reason: written.reason,
        });
      } else if (written.dropped.length > 0) {
        log('warn', 'session log lacks identity columns; they were dropped, not invented (task 7.37 owns the schema)', {
          seat: seatPath.seat, sessionsCsv: seatPath.sessionsCsv, dropped: written.dropped,
        });
      }
    } catch (err) {
      // A pane already exists at this point, so failing the launch here would leave a live seat
      // with a failed launch record. Loud warning + a gate that refuses that seat's commands is
      // the honest outcome; a silent success is the one thing that must not happen.
      log('warn', 'session row append failed — identity gate will refuse this seat', {
        seat: seatPath.seat, sessionsCsv: seatPath.sessionsCsv, error: err.message,
      });
    }
    // carrier stays `systemd`, and this is modelling rather than a workaround: the CARRIER — the
    // thing that holds the process and applies the caps — is still systemd, a --scope unit instead
    // of a transient service. What changed is the TARGET (a tmux pane), which is exactly how the
    // settle ledger frames it: "DEC-1 is amended in TARGET, never in gate" (R28). Writing a new
    // carrier value would also fail the heart store's CHECK constraint
    // (carrier IN ('systemd','setsid')) — a CERTIFIED schema whose reopen is owner-gated tonight
    // (`r-746-schema-pregrant`), and not something to widen from here.
    // SURFACED, not buried: the row therefore cannot distinguish a scope-in-a-pane from a
    // transient service, which matters to any liveness/kill path that switches on carrier. Filed
    // as a run issue for task 7.46's schema pass; the unit name + pane id below carry the truth in
    // the meantime.
    heartStore.updateExecutionStatus(execId, {
      status: 'running',
      carrier: 'systemd',
      unitName: composed.unitName,
      pid: panePid,
      pidStarttime,
      startedAt: new Date(),
      sessionId,
      profile: profileName,
      workdir: resolvedWorkdir,
    });

    // `seat` is the FOLDER-DERIVED name, matching the dryRun return above (task 7.11 — G9). It
    // used to be `seatName`, the CALLER'S string — which is exactly the value the launch gate at
    // `:487` exists to refuse to trust ("the folder is the identity; a supplied name never
    // overrides it"). The two returns therefore disagreed: dryRun reported the folder, live
    // reported the assertion. It was MASKED while the only caller always supplied a name; dropping
    // that supply (index.js) turned it into a literal `undefined` and surfaced it.
    return { sessionId, paneId, panePid, pidStarttime, unitName: composed.unitName, workdir: resolvedWorkdir, room, seat: seatPath.seat };
  }

  async function status(execId) {
    const row = heartStore.getExecution(execId);
    if (!row) throw new SpawnError(E_SESSION_NOT_FOUND, `session not found: ${execId}`, { execId });

    let carrierInfo;
    if (row.carrier === 'systemd' && row.unit_name) {
      carrierInfo = systemdStatus(row.unit_name, userManager);
    } else if (row.carrier === 'setsid' && row.pid) {
      carrierInfo = setsidStatus(row.pid, row.pid_starttime);
    } else {
      carrierInfo = { carrier: row.carrier || null, active: false };
    }

    return {
      execId,
      sessionId: row.session_id,
      profile: row.profile,
      sessionMode: row.session_mode,
      status: row.status,
      workdir: row.workdir,
      carrier: row.carrier,
      unitName: row.unit_name,
      pid: row.pid,
      exitCode: row.exit_code,
      logPath: row.log_path,
      sessionRef: row.session_ref,
      live: carrierInfo.active,
      carrierInfo,
    };
  }

  function logs(execId, { tailBytes = 0, follow = false } = {}) {
    const row = heartStore.getExecution(execId);
    if (!row || !row.log_path) throw new SpawnError(E_SESSION_NOT_FOUND, `no log for session: ${execId}`, { execId });
    if (!fs.existsSync(row.log_path)) return { exists: false, logPath: row.log_path };

    if (follow) {
      const proc = childSpawn('tail', tailBytes > 0 ? ['-c', String(tailBytes), '-f', row.log_path] : ['-f', row.log_path], { stdio: 'inherit' });
      return { exists: true, logPath: row.log_path, following: true, proc };
    }

    const stats = fs.statSync(row.log_path);
    const start = tailBytes > 0 && stats.size > tailBytes ? stats.size - tailBytes : 0;
    const data = fs.readFileSync(row.log_path, { start, encoding: 'utf8' });
    return { exists: true, logPath: row.log_path, data };
  }

  async function kill(execId) {
    const row = heartStore.getExecution(execId);
    if (!row) throw new SpawnError(E_SESSION_NOT_FOUND, `session not found: ${execId}`, { execId });

    let result;
    if (row.carrier === 'systemd' && row.unit_name) {
      result = await killSystemd(row.unit_name, config.spawn.kill_grace_seconds, userManager, log);
    } else if (row.carrier === 'setsid' && row.pid) {
      result = await killSetsid(row.pid, config.spawn.kill_grace_seconds, log);
    } else {
      throw new SpawnError(E_CARRIER_FAILED, `cannot kill session with unknown carrier`, { execId, carrier: row.carrier });
    }

    // 7.46: killing a session ends BOTH levels, and this is where the legacy conflation is still
    // visible. `killed` is a SESSION word, but it stays on the turn row because dispatch.js reads
    // it back and the inspect surface exposes it — retiring it is a runtime change, not the
    // bookkeeping this task is. What is new is that the session-level kill is now recorded where
    // it belongs instead of only being spelled on a turn.
    //
    // ⚠ G-225 — ONE STORE CALL, NOT TWO STATEMENTS. This used to be `updateExecutionStatus()` then
    // `closeSession()` with nothing around them, so a failure between the two left a `killed` turn
    // under an `alive` session: a slot the agent cap keeps counting, holding a session nothing will
    // ever close except a sweep that happens to visit. Both levels land together or neither does.
    const killedAt = new Date();
    heartStore.endTurnAndCloseSession(execId, {
      turnStatus: 'killed',
      sessionStatus: 'killed',
      endedAt: killedAt,
      reason: `kill-session on turn ${execId}`,
    });
    return { execId, killed: result.killed, signal: result.signal };
  }

  function list() {
    const rows = heartStore.dump().jobs_log;
    const anomalies = [];
    try {
      const units = listSystemdUnits('rbtv-worker-', userManager);
      for (const unit of units) {
        const sessionId = unit.unitName.replace(/^rbtv-worker-/, '').replace(/\.service$/, '');
        const match = rows.find((r) => r.session_id === sessionId || r.unit_name === unit.unitName);
        if (!match) {
          anomalies.push({ type: 'row-less-unit', unitName: unit.unitName, sessionId, active: unit.active });
        }
      }
    } catch (err) {
      anomalies.push({ type: 'list-error', error: err.message });
    }
    return { sessions: rows, anomalies };
  }

  async function orphanRescan() {
    const launching = heartStore.listExecutionsByStatus('launching');
    const running = heartStore.listExecutionsByStatus('running');
    const results = { reattached: [], markedFailed: [], rowLessUnits: [], errors: [] };

    for (const row of [...launching, ...running]) {
      try {
        let live = false;
        if (row.carrier === 'systemd' && row.unit_name) {
          live = systemdStatus(row.unit_name, userManager).active;
          if (!live) {
            const info = systemdStatus(row.unit_name, userManager);
            heartStore.updateExecutionStatus(row.exec_id, {
              status: 'failed',
              exitCode: info.exitCode,
              endedAt: new Date(),
            });
            results.markedFailed.push({ execId: row.exec_id, reason: 'unit inactive at boot rescan', carrierInfo: info });
          } else {
            results.reattached.push({ execId: row.exec_id, carrier: 'systemd', unitName: row.unit_name });
          }
        } else if (row.carrier === 'setsid' && row.pid && row.pid_starttime) {
          const info = setsidStatus(row.pid, row.pid_starttime);
          live = info.active && info.pidStarttime === row.pid_starttime;
          if (!live) {
            heartStore.updateExecutionStatus(row.exec_id, {
              status: 'failed',
              endedAt: new Date(),
            });
            results.markedFailed.push({ execId: row.exec_id, reason: 'PID dead or reused at boot rescan' });
          } else {
            results.reattached.push({ execId: row.exec_id, carrier: 'setsid', pid: row.pid });
          }
        } else {
          heartStore.updateExecutionStatus(row.exec_id, { status: 'failed', endedAt: new Date() });
          results.markedFailed.push({ execId: row.exec_id, reason: 'missing carrier metadata' });
        }
      } catch (err) {
        results.errors.push({ execId: row.exec_id, error: err.message });
      }
    }

    try {
      const units = listSystemdUnits('rbtv-worker-', userManager);
      const rows = heartStore.dump().jobs_log;
      for (const unit of units) {
        // list-units reports names WITH the `.service` suffix; stored unit_name has none.
        // Match on the bare unit name and the session_id-derived name to avoid false orphans.
        const bare = unit.unitName.replace(/\.service$/, '');
        const sid = bare.replace(/^rbtv-worker-/, '');
        const match = rows.find((r) => r.unit_name === unit.unitName || r.unit_name === bare || r.session_id === sid);
        if (!match) {
          results.rowLessUnits.push({ unitName: unit.unitName, active: unit.active });
          log('warn', 'row-less rbtv-worker unit found; NOT auto-killed', { unitName: unit.unitName });
        }
      }
    } catch (err) {
      results.errors.push({ error: `unit enumeration failed: ${err.message}` });
      throw new SpawnError(E_ORPHAN_RESCAN_FAILED, `orphan rescan unit enumeration failed: ${err.message}`, { results });
    }

    return results;
  }

  return {
    config,
    spawn,
    spawnSeat,
    status,
    logs,
    kill,
    list,
    orphanRescan,
  };
}

// composeCageFor is exported for the cage probes ONLY — they drive the real resolvers off a real
// seat folder on disk, which is the only way a grant-class check tests the integration rather
// than a hand-typed grant list. Nothing in the daemon calls it from outside this module.
// The last three are exported to DELETE copies, not to grow an API: `resolveSandbox`/`ensureLogPath`
// were duplicated in `live-sessions.js` and `appendRowEnsuringHeader` in `engine/attached-execution.js`,
// each only because this file was another session's dirty file at that build's moment (7.637, 7.628).
// The schema still has one owner (`coord.py SESSIONS_COLS`); what unifies here is the mechanism.
module.exports = {
  createSpawnManager,
  validateSpawnRequest,
  exitFilePath,
  ensureExitFile,
  composeCageFor,
  composeArgv,
  resolveSandbox,
  ensureLogPath,
  appendRowEnsuringHeader,
  // Exported for `launch-profiles/probes/probe-binding-catalog.js`: the seat-cast resolution is
  // the half of the D19 fix that reads a REAL descriptor, and a probe that stubs the descriptor
  // read would prove the catalog and not the fix.
  seatDeclaresValue,
  profileForSeatCast,
};

function validateSpawnRequest(req) {
  if (req === null || typeof req !== 'object' || Array.isArray(req)) {
    throw new SpawnError(E_BAD_REQUEST, 'spawn request must be an object', {});
  }
  validateRequestKeys(req);
}
