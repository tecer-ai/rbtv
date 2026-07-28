'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn, spawnSync } = require('node:child_process');

// ── THE TWO SHARED MODULES, AND NO PRIVATE COPY OF WHAT THEY HOLD ────────────────────────────
// This capability is the second live consumer of both, and both index headers named it as an
// unbuilt one. It holds NO per-harness launch-method table of its own — that absence is task
// 7.45's criterion 3, which this build exists to discharge.
const profilesModule = require('../../launch-profiles');
const ladder = require('../../injection-ladder');
// `scanPath` is exported by launch-profiles/host.js but NOT re-exported by that module's
// index.js. It is used here to resolve the harness binary to an absolute path (see env.js on why
// the child's PATH cannot be the dispatcher's). Reaching into the file rather than duplicating an
// eight-line PATH scan is the lesser of two PRIN-11 evils, and the missing re-export is FILED to
// the leader rather than fixed here — `ignite/launch-profiles/` is read-only to task 7.43.
const { scanPath } = require('../../launch-profiles/host');

const {
  DispatchError,
  E_SEAT_IMPERSONATION,
  E_NESTING_REFUSED,
  E_RUNG_NOT_DRIVABLE,
  E_NO_HARNESS,
  E_HARNESS_BINARY_ABSENT,
  E_BAD_REQUEST,
  E_WORKSPACE_AMBIGUOUS,
} = require('./errors');
const { resolveTarget } = require('./catalog');
const { buildChildEnv, DEPTH_VAR } = require('./env');
const fanout = require('./fanout');

const SUPERVISOR = path.join(__dirname, 'supervisor.js');

// ⚠ MEASURED, AND IT IS A FINDING ABOUT 7.42 RATHER THAN A CHOICE OF MINE. The shared resolver
// REFUSES the committed `config/spawn-profiles.yaml` outright unless the caller injects a
// SeatBinds template validator: profile `claude-seat` declares `sandbox.SeatBinds` (task 7.11) and
// `profiles.js` refuses an unvalidated bind template rather than waving it through — correctly,
// "absence of a checker must never become absence of a check". But the validator lives in
// `server/spawn/cage.js`, which the shared module may not import ("ONE module with no daemon
// import"), so the daemon adapter injects it.
//
// ⇒ THE CONSEQUENCE FOR EVERY NON-DAEMON CONSUMER, WHICH IS WHAT THIS LANE IS: it must either
// import daemon code, or lose access to EVERY profile in the file because ONE profile declares a
// key it cannot validate. Refusing to inject would not be safer — the config would not load at
// all and this lane would be dead, so there is no fail-closed reading in which the absence helps.
// This is a READ-ONLY require of a pure validator (`ignite/server/**` is the live daemon's code
// and is never edited from here). Reported to the leader; not fixed here — `launch-profiles/` and
// `server/` are both outside this task's write surface.
function seatBindValidator(template, profileName, filePath) {
  const { validateSeatBindTemplate } = require('../../server/spawn/cage');
  return validateSeatBindTemplate(template, profileName, filePath);
}

// ── boundary 9 — NO NESTING ──────────────────────────────────────────────────────────────────
// The dispatcher stamps DEPTH_VAR into the scrubbed environment it hands the sub-agent. This is
// the FIRST thing every dispatch does: a sub-agent that reaches for this CLI finds the marker in
// its own environment and is refused before any other work happens. Depth stops one level below
// the dispatcher (`decisions.md#d-sub-agent-population-bounds`).
//
// It is enforceable precisely BECAUSE boundary 11 built the child's environment constructively:
// the marker is one of the few names that survive the scrub, so a sub-agent cannot arrive without
// it and cannot be handed one by accident.
function assertNotNested(env = process.env) {
  if (env[DEPTH_VAR] !== undefined) {
    throw new DispatchError(
      E_NESTING_REFUSED,
      `this process is itself a sub-agent (${DEPTH_VAR}=${env[DEPTH_VAR]}) — a sub-agent NEVER ` +
      `dispatches sub-agents of its own. REFUSING, nothing spawned (CMP-10 boundary 9, ` +
      `decisions.md#d-sub-agent-population-bounds).`,
      { depth: env[DEPTH_VAR] },
    );
  }
}

// ── boundary 6 — NO SEAT IMPERSONATION ───────────────────────────────────────────────────────
// A sub-agent holds no slot in any taskforce. If its workdir sat inside a seat folder, every
// artifact it wrote would be indistinguishable on disk from that seat's — which is what the
// boundary names. Checked BEFORE the spawn so nothing is ever written there and noticed after.
const SEAT_IDENTITY_RE = /(^|\/)runs\/run-[^/]+\/seats\/[^/]+/;
function assertNotSeatIdentity(dir, what) {
  if (SEAT_IDENTITY_RE.test(dir)) {
    throw new DispatchError(
      E_SEAT_IMPERSONATION,
      `${what} '${dir}' carries a taskforce seat's identity ({goal}/runs/run-N/seats/…) — a ` +
      `sub-agent holds no slot in any taskforce and its artifacts may never land under a seat's ` +
      `folder. REFUSING, nothing spawned (CMP-10 boundary 6).`,
      { path: dir },
    );
  }
}

// ⚠ WHICH `.rbtv/` — AND THE FIRST BUILD OF THIS FILE GOT IT WRONG, caught by RUNNING the
// dispatch rather than by reading it. A bare cwd walk-up is NOT the daemon's resolution: the
// daemon takes `RBTV_IGNITE_WORKSPACE_ROOT` from its unit, a walk-up takes whatever `.rbtv/` is
// NEAREST — and the rbtv repo has its OWN `.rbtv/`. Running the CLI from inside the repo therefore
// put a live sub-agent's session dir at `…/tools/rbtv/.rbtv/sessions/`, which is UNTRACKED AND NOT
// GITIGNORED in that repo (measured: `git status --porcelain .rbtv` → `?? .rbtv/`), on a tree the
// run has an explicit standing hazard about `git add -A` on.
//
// The resolution below is `ticker-settings`' own, adopted rather than re-derived: that surface hit
// this exact defect first and its reasoning is the authority (`ticker-settings.md` § Which
// workspace). A walk-up that DISAGREES with a live unit REFUSES rather than picking one.
//
// ⚠ PRIN-11 residual, DISCLOSED rather than hidden: this is now the THIRD home for "which
// workspace roots `.rbtv/`" — `launch-profiles/profiles.js:resolveWorkspaceRoot` (derives it from
// the heart store's db path), `ticker-settings`' CLI-local copy, and this one. Neither of the
// other two is importable from here as a function with this contract. Filed to the leader as a
// convergence candidate; not fixed here, because both other homes are outside this task's write
// surface.
function unitWorkspaceRoot(unit) {
  const r = spawnSync('systemctl', ['--user', 'show', unit, '--property=Environment'], { encoding: 'utf8' });
  if (r.status !== 0 || !r.stdout) return null;
  const m = /RBTV_IGNITE_WORKSPACE_ROOT=(\S+)/.exec(r.stdout);
  return m ? path.resolve(m[1]) : null;
}

function walkUpWorkspaceRoot(startDir) {
  let dir = path.resolve(startDir);
  for (;;) {
    if (fs.existsSync(path.join(dir, '.rbtv'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function resolveWorkspaceRoot(startDir = process.cwd()) {
  const explicit = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  if (explicit) return path.resolve(explicit);

  const unit = process.env.RBTV_IGNITE_UNIT || 'rbtv-ignite.service';
  const fromUnit = unitWorkspaceRoot(unit);
  const fromCwd = walkUpWorkspaceRoot(startDir);

  if (fromUnit && fromCwd && fromUnit !== fromCwd) {
    throw new DispatchError(
      E_WORKSPACE_AMBIGUOUS,
      `REFUSING — two different workspaces answer here, and launching a sub-agent into the wrong ` +
      `one puts its session dir and every artifact it writes somewhere nobody is looking:\n` +
      `  the daemon (${unit}) uses:  ${fromUnit}\n` +
      `  walking up from your cwd:   ${fromCwd}\n` +
      `Set RBTV_IGNITE_WORKSPACE_ROOT to the one you mean, or dispatch from inside it.`,
      { unit, fromUnit, fromCwd },
    );
  }
  return fromUnit || fromCwd || null;
}

function defaultConfigPath() {
  return path.resolve(__dirname, '..', '..', 'config', 'spawn-profiles.yaml');
}

// ═════════════════════════════════════════════════════════════════════════════════════════════
// dispatch() — the cage, in order, every check fail-closed and none of them softenable.
//
// The ORDER is deliberate: every refusal that can be decided without touching the disk is decided
// first, so a refused launch leaves no trace at all. Nothing is created before the last check
// passes; `spawnedNothing` is a property of the sequence, not a claim about it.
// ═════════════════════════════════════════════════════════════════════════════════════════════
async function dispatch(opts) {
  const {
    target,
    profile: profileName,
    task,
    effort = null,
    needResumable = false,
    configPath = defaultConfigPath(),
    rbtvRoot,
    dispatcherEnv = process.env,
    onStdout = null,
    onStderr = null,
  } = opts;

  // 0. boundary 9 first — a nested dispatcher must be refused before it does anything else.
  assertNotNested(dispatcherEnv);

  if (!target) throw new DispatchError(E_BAD_REQUEST, 'no --target: the cataloged part to dispatch', {});
  if (!profileName) throw new DispatchError(E_BAD_REQUEST, 'no --profile: the launch profile to run it under', {});
  if (!task || !String(task).trim()) throw new DispatchError(E_BAD_REQUEST, 'no task text (--task or stdin)', {});

  // 1. boundary 1 — catalog-bound. Reads the component's exposure manifest; refuses anything it
  //    does not find there, and there is no free-form path past it.
  const row = resolveTarget(target, rbtvRoot ? { rbtvRoot } : {});

  // 2. boundary 2 — profile-bound. The profile comes from the SAME shared config the daemon
  //    spawns from, resolved by the SAME module. No raw flags: `resolveProfile` refuses any slot
  //    the profile does not declare, and asserts the resolved argv arity so a caller value can
  //    never become an argv element.
  const config = profilesModule.loadConfig(configPath, { seatBindValidator });
  const resolved = profilesModule.resolveProfile(config, profileName, { effort });

  // 3. WHICH HARNESS. D23: identified from the profile's own argv[0] — never a parallel registry.
  //    `harnessOf()` reads `profile.exec.argv[0]`, which a caged/portable HALVES profile does not
  //    have; the resolved argv is the half-agnostic answer, so `harnessFromBinary` is the right
  //    call for a consumer that has already resolved. Disclosed rather than worked around.
  const harness = ladder.harnessFromBinary(resolved.argv[0]);
  if (!harness) {
    throw new DispatchError(
      E_NO_HARNESS,
      `profile '${profileName}' runs '${resolved.argv[0]}', which the injection ladder has no ` +
      `measured harness entry for (known: ${ladder.KNOWN_HARNESSES.join('|')}). A sub-agent IS an ` +
      `agent: a profile with no harness is not a sub-agent target, and guessing one would put ` +
      `unverified launch knowledge back into the system CMP-9 holds in one place. REFUSING.`,
      { profile: profileName, binary: resolved.argv[0], known: ladder.KNOWN_HARNESSES },
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════════════════════
  // 4. THE WALK. Task 7.45 criterion 3 lives on exactly this call.
  //
  // ⚠ THE RUNG IS NEVER PASSED IN. This caller hands `resolveRung()` the SITUATION and takes
  // whatever it computes:
  //   harness        — derived above from the profile's own argv[0], not chosen here
  //   phase          — 'launch': this lane starts a new session; it never reaches into a live one
  //   needResumable  — the CALLER's requirement, verbatim (`--resumable`), not a rung name
  //   hostSupports   — { keystroke: false }, a true property of this lane and not a preference:
  //                    a headless sub-agent attached to the caller's terminal has no tmux pane to
  //                    type into, so the keystroke rung's surface does not exist here.
  //
  // The walk is DISCRIMINATING at this call site, which is what makes a check over it able to
  // fail: with `--resumable`, an opencode profile resolves to NO rung at all (its headless rung is
  // one-shot, G-13; hooks does not make a session reachable again; keystroke is inject-only) and
  // the dispatch is refused — while a claude profile at the same call resolves to `headless`.
  // Neither answer is written anywhere in this file.
  // ═══════════════════════════════════════════════════════════════════════════════════════════
  const walk = ladder.resolveRung(harness, {
    phase: 'launch',
    needResumable,
    hostSupports: { keystroke: false },
  });

  // 5. Can this lane DRIVE the rung the ladder walked to? `headless` is the harness's own one-shot
  //    invocation, which is exactly what this lane spawns. `hooks` writes a config the harness
  //    reads at start — it configures a launch, it does not perform one — and `keystroke` needs a
  //    live TUI. A walk that lands anywhere but `headless` is a typed refusal carrying the walk's
  //    own reasons, never a silent downgrade to something this lane happens to be able to do.
  if (walk.rung !== 'headless') {
    throw new DispatchError(
      E_RUNG_NOT_DRIVABLE,
      `the injection ladder walked to rung '${walk.rung}' for harness '${harness}' at phase ` +
      `'launch', which this lane cannot drive (it spawns a headless one-shot attached to the ` +
      `caller's terminal; it has no pane and writes no live session). Walk skipped: ` +
      `${walk.skipped.map((s) => `${s.rung} — ${s.why}`).join('; ') || 'nothing'}. REFUSING.`,
      { harness, rung: walk.rung, skipped: walk.skipped },
    );
  }

  // 6. The harness binary, absolute. The child's PATH is a system base with no bus CLI on it
  //    (env.js), so argv[0] must not depend on the dispatcher's PATH being inherited.
  const binaryAbs = scanPath(resolved.argv[0]);
  if (!binaryAbs) {
    throw new DispatchError(
      E_HARNESS_BINARY_ABSENT,
      `harness binary '${resolved.argv[0]}' is not on this box's PATH — REFUSING before spawning ` +
      `so the failure names the binary rather than surfacing as an ENOENT from a child`,
      { binary: resolved.argv[0] },
    );
  }

  // 7. The workdir, through the SAME resolver the daemon uses — including its fail-closed
  //    containment check (E_WORKDIR_ESCAPE if the session dir falls outside the profile's
  //    workdir_root).
  const workspaceRoot = resolveWorkspaceRoot();
  const sessionsRoot = profilesModule.sessionsRootFor(workspaceRoot);
  const execId = `subagent-${crypto.randomUUID()}`;
  const workdir = profilesModule.resolveWorkdir(resolved, null, config.default_workdir_root, configPath, {
    execId, sessionsRoot, workspaceRoot,
  });

  // 8. boundary 6, on the resolved path rather than on the template.
  assertNotSeatIdentity(workdir, 'resolved workdir');

  // 9. boundary 11 — the scrubbed environment, built from an empty object.
  const { env, declared, base } = buildChildEnv({
    resolvedProfile: resolved,
    dispatcherEnv,
    extra: { [DEPTH_VAR]: '1' },
  });

  // 10. The hooks rung's per-harness surface, from the shared module — the daemon's own pattern
  //     (`server/spawn/harness-config.js` is likewise a thin executor over this descriptor). The
  //     ladder WRITES nothing; the caller does. Scoped to the session dir, so the sub-agent's
  //     declared editable root is its own workdir and nothing else.
  const hooks = ladder.hooksConfigFor(harness, { sessionDir: workdir, editablePaths: [workdir] });
  for (const dir of hooks.dirs) fs.mkdirSync(dir.path, { recursive: true, mode: dir.mode || 0o700 });
  for (const file of hooks.files) fs.writeFileSync(file.path, file.content, { mode: file.mode || 0o600 });

  // 11. The prompt. The caller supplies TASK TEXT; it never supplies the target. The dispatch is
  //     anchored to the cataloged part's own entry point, which is what "cataloged capabilities
  //     via their entry capability — never free-form agents" means in practice.
  const promptFile = path.join(workdir, 'prompt.txt');
  const prompt =
    `Cataloged target: ${row.partId} (${row.partKind || 'part'}), exposed by ${row.manifest}\n` +
    `Entry point: ${row.entryPointAbs}\n` +
    `Read that entry point and follow it.\n\n` +
    `Working directory: ${workdir}\n\n` +
    `Task from the dispatcher:\n${String(task).trim()}\n`;
  fs.writeFileSync(promptFile, prompt, { mode: 0o600 });

  // 12. boundary 10 — reserve a fan-out slot. LAST check before the spawn and the only one that
  //     mutates shared state, so a refusal above never leaves a reservation behind.
  const runtimeRoot = workspaceRoot ? path.join(workspaceRoot, '.rbtv', 'runtime') : path.join(os.tmpdir(), 'rbtv-runtime');
  const slot = fanout.reserve({ runtimeRoot, meta: { target: row.partId, profile: profileName, workdir } });

  const spec = { argv: [binaryAbs, ...resolved.argv.slice(1)], workdir, promptFile, sessionDir: workdir };
  const specFile = path.join(workdir, 'spec.json');
  fs.writeFileSync(specFile, JSON.stringify(spec, null, 2), { mode: 0o600 });

  // 13. THE SPAWN. Detached (boundary 8: its own process group, one kill cleans the tree) with a
  //     fourth stdio pipe — the death pipe (boundary 4: it dies with this dispatching step,
  //     including when this process is SIGKILLed and runs no handler).
  const child = spawn(process.execPath, [SUPERVISOR, specFile], {
    detached: true,
    env,
    stdio: ['ignore', 'pipe', 'pipe', 'pipe'],
  });
  slot.bind(child.pid);

  let stdout = '';
  let stderr = '';
  child.stdout.on('data', (b) => { stdout += b; if (onStdout) onStdout(b); });
  child.stderr.on('data', (b) => { stderr += b; if (onStderr) onStderr(b); });

  const exit = await new Promise((resolve) => {
    child.on('exit', (code, signal) => resolve({ code, signal }));
    child.on('error', (err) => resolve({ code: 71, signal: null, error: err.message }));
  });
  slot.release();

  return {
    target: row.partId,
    entryPoint: row.entryPointAbs,
    manifest: row.manifest,
    profile: profileName,
    harness,
    // The walk's answer and its reasons, reported rather than summarized: a caller can see WHICH
    // rung was selected and which were passed and why.
    rung: walk.rung,
    walkSkipped: walk.skipped,
    hostCapability: resolved.hostCapability,
    half: resolved.half,
    argv: spec.argv,
    workdir,
    execId,
    supervisorPid: child.pid,
    envAllowlist: { base, declared, path: env.PATH },
    hooksWritten: hooks.result,
    exitCode: exit.code,
    signal: exit.signal,
    stdout,
    stderr,
  };
}

module.exports = {
  dispatch,
  assertNotNested,
  assertNotSeatIdentity,
  resolveWorkspaceRoot,
  defaultConfigPath,
  SEAT_IDENTITY_RE,
  SUPERVISOR,
};
