'use strict';

const fs = require('node:fs');
const path = require('node:path');
const yaml = require('js-yaml');
const {
  SpawnError,
  E_CONFIG_LOAD,
  E_UNKNOWN_SLOT,
  E_MISSING_KEY,
  E_UNKNOWN_LAUNCH_SPEC,
  E_WORKDIR_ESCAPE,
  E_WORKDIR_MISSING,
  E_NO_PORTABLE_HALF,
  E_UNKNOWN_EFFORT,
  E_RAW_FLAG,
} = require('./errors');
const { detectHostCapability, CAGED, PORTABLE } = require('./host');
// The key builder and the key/argv agreement guard's derivation. `catalog.js` requires only
// `./errors`, so this import creates no cycle — and the join between a (harness, model) and its
// key must be spelled in ONE module, which is that one.
const { bindingOf, specKey } = require('./catalog');

// ═════════════════════════════════════════════════════════════════════════════════════════════
// The shared launch-profile resolver (task 7.42; registry decisions.md#d-profile-source-unification).
//
// MOVED HERE from server/spawn/config.js. The ruling is explicit that one shared FILE is not
// enough — "a second interpreter of the one file is the same drift as a second file" — so the
// resolution, slot validation, carriage vocabulary and workdir guard live in ONE module that
// requires nothing under `server/`. server/spawn/config.js is now a thin daemon-side adapter
// over this; the attached dispatch capability (task 7.43) and the orchestration conductor's
// worker dispatch (task 7.54) are the other two consumers and are NOT built here.
//
// Every validator below is moved with its behaviour intact — the daemon's existing spawn
// behaviour is byte-unchanged, which is task 7.42's own criterion. The ADDITIONS are the ruled
// shape: caged/portable halves, the effort parameter slot, and the raw-flag bound.
// ═════════════════════════════════════════════════════════════════════════════════════════════

// r-seats-only-architecture (1)/(2): profiles collapse to harness+model, with the shared blocks
// declared ONCE at the top level and merged into every profile by this resolver — one seat-cage
// template (`cage:`, carrying SeatBinds — the committed config's spelling; `sandbox_default` is
// accepted as a synonym), one global caps block (`caps:` / `caps_default`, rare per-profile
// overrides only by ruling), and the CLOSED `toolsets` enum.
const KNOWN_TOP_KEYS = new Set([
  'bind', 'auth', 'spawn', 'launch-specs', 'jobs', 'default_workdir_root',
  'cage', 'caps', 'sandbox_default', 'caps_default', 'toolsets',
]);

// ⚠ 7.42 — measured, not assumed: the COMMITTED `config/spawn-profiles.yaml` carries root keys
// that are NOT the profile surface's. `server/index.js` (DAEMON_ONLY_ROOT_KEYS) strips them and
// hands spawn a filtered copy, so the daemon never presents them here — which is why the old
// config.js could reject them and nothing broke. Verified with the PRE-CHANGE file: it refuses
// the raw committed config with the same `E_CONFIG_LOAD config root.network`. Not a regression.
//
// But 7.42's goal is a config surface "consumable OUTSIDE the daemon process", and outside there
// is no index.js to strip. Left strict, every non-daemon consumer (7.43, 7.54) would have to
// reimplement the strip — a second interpreter of the one file, which is the drift this task
// exists to remove. So the profile surface IGNORES these namespaces instead of rejecting them.
//
// IGNORED, not accepted-blindly: any root key outside BOTH sets is still a loud E_CONFIG_LOAD, so
// a typo is caught exactly as before. The list is duplicated with server/index.js:42 today and
// that is a PRIN-11 residual I am DISCLOSING rather than hiding — the convergence (index.js
// importing this constant) is a one-line edit to live daemon boot code, which the directive's
// bar 1 flags as the highest-risk file in this task; filed as a follow-on, not smuggled in here.
const DAEMON_ONLY_ROOT_KEYS = new Set(['ticker', 'tools', 'workflows', 'network']);
// `command` (the caged/portable halves) and `effort` (the translation table) are ADDITIVE and
// OPTIONAL at 7.42. Every profile shipped before this task declares neither and is unaffected —
// which is what makes the daemon's behaviour byte-unchanged rather than merely "tested to be".
// `resume` is the OTHER command template a launch profile has always been defined to carry
// (ignite/CLAUDE.md § Terminology: "a named, config-pinned command-template set
// (exec/resume/caps/sandbox)") and that nothing had yet declared. Same shape and same validator as
// `exec` — argv + carriage — and OPTIONAL: a profile without one simply never resumes
// (r-chat-chain-resumes-session's declared fallback).
const KNOWN_SPEC_KEYS = new Set([
  'exec', 'resume', 'session_ref', 'headed', 'workdir_root', 'caps', 'sandbox', 'env', 'command', 'effort',
  'toolset_ceiling',
]);

// ── r-seats-only-architecture (2) — the CLOSED toolset enum, in WIDENING order ───────────────
// Tool rights are named tiers, not per-profile flag soup. The ORDER is the clamp's law: a
// dispatch (or a child) may only ever NARROW its profile's `toolset_ceiling`, never widen it.
const TOOLSET_ORDER = ['read-only', 'git-write', 'full'];
// Local to this module deliberately: this resolver owns the toolset surface, and the shared
// errors module is not widened as a side effect of this change.
const E_UNKNOWN_TOOLSET = 'E_UNKNOWN_TOOLSET';
const E_TOOLSET_WIDENING = 'E_TOOLSET_WIDENING';
const KNOWN_EXEC_KEYS = new Set(['argv', 'prompt']);
const KNOWN_HEADED_KEYS = new Set(['tui']);
const KNOWN_TUI_KEYS = new Set(['argv', 'prompt', 'keystroke']);
// The HEADLESS exec prompt vocabulary — NOT the headed one. `stdin` ONLY: `file` and
// `argv-last` were REMOVED (owner ruling 2026-07-20, batch-08 item 4 half A; NARROWS D83/OQ-F)
// so that caller free text NEVER becomes argv, with no exception clause anywhere. A profile
// declaring a removed carriage is a config-LOAD failure, loudly.
const KNOWN_PROMPT_VALUES = new Set(['stdin']);
// The HEADED carriage vocabulary (session-surface-spec.md Design 3; OQ-F RULED, D83; `argv`
// REMOVED by the same batch-08 item 4 half A ruling — no carriage may put caller text on a
// command line, and the headed argv path was the one UNGUARDED route there). A DIFFERENT
// closed set from KNOWN_PROMPT_VALUES above — the two are deliberately not shared:
// `stdin` is STRUCTURALLY ABSENT here (stdin IS the terminal slave; write-then-close =
// type-then-hang-up), so declaring it is a config-LOAD failure and not a runtime error.
// Matched server/pty/carriage.js's KNOWN_CARRIAGES exactly until task 7.29 deleted that file;
// this is now the SOLE home of the vocabulary. The profile-LOAD gate, the QUEUE
// gate (heart-store.js) and the SPAWN gate (carriage.js) MUST agree on this vocabulary.
const KNOWN_HEADED_CARRIAGES = new Set(['file', 'keystroke']);
// `assigned` — the daemon MINTS the ref and pins it into the launch itself through the
// `{session_ref}` slot (claude: `--session-id <uuid>`), so the ref is known before the worker has
// produced a byte and survives a turn that dies without ever writing a result line. The three
// OBSERVED sources read the ref back out of the worker; `assigned` is the one that does not have
// to. Measured on claude 2.1.224 (2026-08-07): `-p --session-id <uuid>` reports that exact uuid as
// its own `session_id`, and `-p --resume <uuid>` keeps it.
const KNOWN_SESSION_REF_SOURCES = new Set([
  'stdout-json', 'stdout-json-event', 'cwd-implicit', 'assigned',
]);
const KNOWN_CAPS_KEYS = new Set(['memory_max', 'cpu_quota', 'runtime_max', 'tasks_max']);
// `SeatBinds` (task 7.11) is NOT a systemd property — it is the seat cage's ordered bind
// template, read only by bwrap via cage.js. It rides the sandbox block because that block already
// IS "the profile's containment declaration", and a separate top-level key would split one
// concept in two. It can never reach the unit: carrier.js emits only the
// BWRAP_COMPATIBLE_SANDBOX_KEYS allowlist (bwrap.js) — exactly NoNewPrivileges — so this key is
// dropped by the same construction that already drops ProtectSystem and ReadWritePaths.
const KNOWN_SANDBOX_KEYS = new Set([
  'ProtectSystem', 'ReadWritePaths', 'PrivateTmp', 'NoNewPrivileges', 'SeatBinds',
]);
const KNOWN_ENV_KEYS = new Set(['file']);
// `{extra_dir}` — task 7.87. The G1 CONFINEMENT SPLIT needs TWO path values, and the vocabulary
// could express only one. G1 (orchestration `cards/dispatch-wrapper.md`) says: launch a CLI worker
// with its guidance-root = the orchestrator root, and pass the actual WORK TARGET separately via
// the harness's add-dir flag. `{workdir}` is the launch/guidance root; `{extra_dir}` is that second
// path, so a profile can now WRITE the add-dir flag itself (`--add-dir {extra_dir}`) instead of a
// conductor hand-composing it. The rule was earned by the `a3e217d` incident — a bare kimi
// self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo.
//
// ⚠ NOT WORKDIR-GUARDED, deliberately and by definition. `resolveWorkdir`'s containment check
// (E_WORKDIR_ESCAPE) applies to the workdir alone; an add-dir whose whole purpose is to name a
// target OUTSIDE the guidance root cannot be contained by that same root. The structural bound
// still holds — a value fills a position the PROFILE wrote and can never become its own argv
// element (the arity assertion in resolveProfile) — but WHICH directory is handed in is the
// caller's decision and the caller's confinement to make.
//
// Additive and optional: every profile shipped today declares no `{extra_dir}`, so the daemon's
// resolved argv is byte-unchanged by this widening (task 7.42's criterion, re-asserted at 7.87).
const CLOSED_SLOTS = new Set(['{workdir}', '{prompt_file}', '{session_ref}', '{extra_dir}']);
const SLOT_RE = /\{(workdir|prompt_file|session_ref|extra_dir)\}/g;
const UNKNOWN_SLOT_RE = /\{[^}]+\}/g;

// EFFORT IS A NUMERIC RUNG, 1..N — ordered lower→higher reasoning, each profile declaring its
// OWN ladder (owner ruling `d-0811lp-effort-numeric-per-profile`, 2026-08-11: "use N levels (1-N),
// from lower to higher reasoning. this way each harness/model can have as many as they want").
//
// ⚠ THIS REPLACES the four-level ABSTRACT vocabulary (low|medium|high|max) 7.42 shipped, and the
// replacement is the ruling, not a rename. That vocabulary forced every harness onto ONE ladder and
// had to lie about two of the four it served: claude's real dial is FIVE rungs, so `xhigh` was
// unspellable through it, and codex's is THREE, so `max` was collapsed onto `high`. A closed
// cross-harness vocabulary can only be as wide as its narrowest member OR mistranslate; per-profile
// rungs are neither. `values:` (the old level→dialect map) is GONE from the schema — a second live
// scheme is the drift this module exists to remove.
//
// The ladder is 1-BASED and ORDERED: rung 1 = lowest reasoning, rung N = highest. A request outside
// 1..N is REFUSED naming that profile's range. A harness with no dial declares `inert: true` and
// ACCEPTS any rung, reporting `effortInert` (G-270 — stated, never silently dropped).
const KNOWN_EFFORT_KEYS = new Set(['dialect', 'rungs', 'argv', 'inert', 'headed']);
const KNOWN_COMMAND_HALVES = new Set([CAGED, PORTABLE]);

function assertObject(value, name, filePath) {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new SpawnError(E_CONFIG_LOAD, `${name} must be an object`, { file: filePath, key: name });
  }
}

function assertString(value, name, filePath) {
  if (typeof value !== 'string' || value.length === 0) {
    throw new SpawnError(E_MISSING_KEY, `${name} must be a non-empty string`, { file: filePath, key: name });
  }
}

function assertArrayOfStrings(value, name, filePath) {
  if (!Array.isArray(value) || value.some((x) => typeof x !== 'string')) {
    throw new SpawnError(E_CONFIG_LOAD, `${name} must be an array of strings`, { file: filePath, key: name });
  }
}

function checkUnknownKeys(obj, knownSet, prefix, filePath) {
  for (const key of Object.keys(obj)) {
    if (!knownSet.has(key)) {
      throw new SpawnError(E_CONFIG_LOAD, `unknown key in ${prefix}: ${key}`, { file: filePath, key: `${prefix}.${key}` });
    }
  }
}

function detectUnknownSlots(value, prefix, filePath) {
  const str = typeof value === 'string' ? value : JSON.stringify(value);
  const matches = str.match(UNKNOWN_SLOT_RE);
  if (matches) {
    for (const m of matches) {
      if (!CLOSED_SLOTS.has(m)) {
        throw new SpawnError(E_UNKNOWN_SLOT, `unknown template slot ${m} in ${prefix}`, { file: filePath, key: prefix, slot: m });
      }
    }
  }
}

function validateSessionRef(sessionRef, label, filePath) {
  assertObject(sessionRef, `${label}.session_ref`, filePath);
  if (!sessionRef.source || !KNOWN_SESSION_REF_SOURCES.has(sessionRef.source)) {
    throw new SpawnError(E_CONFIG_LOAD, `${label}.session_ref.source must be one of ${Array.from(KNOWN_SESSION_REF_SOURCES).join(', ')}`, { file: filePath, key: `${label}.session_ref.source` });
  }
  if (sessionRef.source === 'stdout-json' && !sessionRef.field) {
    throw new SpawnError(E_MISSING_KEY, `${label}.session_ref.field is required for source stdout-json`, { file: filePath, key: `${label}.session_ref.field` });
  }
  if (sessionRef.source === 'stdout-json-event' && (!sessionRef.event || !sessionRef.field)) {
    throw new SpawnError(E_MISSING_KEY, `${label}.session_ref.event and field are required for source stdout-json-event`, { file: filePath, key: `${label}.session_ref` });
  }
}

function validateExec(block, label, filePath, blockName = 'exec') {
  assertObject(block, `${label}.${blockName}`, filePath);
  checkUnknownKeys(block, KNOWN_EXEC_KEYS, `${label}.${blockName}`, filePath);
  assertArrayOfStrings(block.argv, `${label}.${blockName}.argv`, filePath);
  if (!block.prompt || !KNOWN_PROMPT_VALUES.has(block.prompt)) {
    throw new SpawnError(E_CONFIG_LOAD, `${label}.${blockName}.prompt must be stdin — the ONLY headless carriage (file and argv-last REMOVED, batch-08 item 4: caller free text never becomes argv)`, { file: filePath, key: `${label}.${blockName}.prompt` });
  }
  for (let i = 0; i < block.argv.length; i++) {
    detectUnknownSlots(block.argv[i], `${label}.${blockName}.argv[${i}]`, filePath);
  }
}

function validateCaps(caps, label, filePath) {
  assertObject(caps, `${label}.caps`, filePath);
  checkUnknownKeys(caps, KNOWN_CAPS_KEYS, `${label}.caps`, filePath);
  for (const key of KNOWN_CAPS_KEYS) {
    if (caps[key] !== undefined) {
      const ok = (typeof caps[key] === 'string' && caps[key].length > 0) || Number.isInteger(caps[key]);
      if (!ok) {
        throw new SpawnError(E_CONFIG_LOAD, `${label}.caps.${key} must be a non-empty string or integer`, { file: filePath, key: `${label}.caps.${key}` });
      }
    }
  }
}

// r-seats-only-architecture (2): `toolsets:` declares which of the CLOSED enum's tiers this
// install speaks. Tolerant of shape (a list of names, or a mapping keyed by name whose values a
// consumer may attach tool definitions to) but closed on VOCABULARY: a name outside TOOLSET_ORDER
// is a load failure, never a fourth tier minted in config.
function validateToolsets(toolsets, filePath) {
  const names = Array.isArray(toolsets)
    ? toolsets
    : (toolsets !== null && typeof toolsets === 'object' ? Object.keys(toolsets) : null);
  if (!names || names.some((n) => typeof n !== 'string')) {
    throw new SpawnError(E_CONFIG_LOAD, 'toolsets must be a list of names or a mapping keyed by name', { file: filePath, key: 'toolsets' });
  }
  for (const n of names) {
    if (!TOOLSET_ORDER.includes(n)) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `toolsets declares "${n}", outside the CLOSED enum ${TOOLSET_ORDER.join('|')} ` +
        '(r-seats-only-architecture (2): tool rights are a closed enum of named toolsets)',
        { file: filePath, key: 'toolsets', toolset: n },
      );
    }
  }
  return names;
}

function validateSandbox(sandbox, label, filePath, seatBindValidator) {
  assertObject(sandbox, `${label}.sandbox`, filePath);
  checkUnknownKeys(sandbox, KNOWN_SANDBOX_KEYS, `${label}.sandbox`, filePath);
  if (sandbox.ReadWritePaths !== undefined) {
    const arr = Array.isArray(sandbox.ReadWritePaths) ? sandbox.ReadWritePaths : [sandbox.ReadWritePaths];
    for (let i = 0; i < arr.length; i++) {
      detectUnknownSlots(arr[i], `${label}.sandbox.ReadWritePaths[${i}]`, filePath);
    }
  }
  // 7.11 — SeatBinds carries its OWN slot vocabulary ({seatDir}/{goalDir}/{runDir}/{grant:FIELD}),
  // which the CLOSED_SLOTS set above deliberately does not contain: those slots are resolved by
  // cage.js from the seat's own records, never by resolveTemplateSlots from a workdir. So it is
  // validated by cage.js's own parser rather than by detectUnknownSlots — one vocabulary, one
  // definition, checked at config LOAD like every other profile key.
  //
  // ⚠ 7.42: cage.js lives under server/, and this module may not import it. The validator is
  // INJECTED by the caller (the daemon adapter passes cage.js's). A consumer that supplies none
  // gets the key structurally REFUSED rather than waved through — absence of a checker must never
  // become absence of a check, which is the exact fail-open this run has filed five times tonight.
  if (sandbox.SeatBinds !== undefined) {
    if (typeof seatBindValidator !== 'function') {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.sandbox.SeatBinds is declared but this consumer supplied no ` +
        `SeatBinds validator — refusing rather than accepting an unvalidated bind template`,
        { file: filePath, key: `${label}.sandbox.SeatBinds` },
      );
    }
    seatBindValidator(sandbox.SeatBinds, label, filePath);
  }
}

function validateEnv(env, label, filePath) {
  assertObject(env, `${label}.env`, filePath);
  checkUnknownKeys(env, KNOWN_ENV_KEYS, `${label}.env`, filePath);
  if (env.file !== undefined) assertString(env.file, `${label}.env.file`, filePath);
}

function validateHeaded(headed, label, filePath) {
  assertObject(headed, `${label}.headed`, filePath);
  checkUnknownKeys(headed, KNOWN_HEADED_KEYS, `${label}.headed`, filePath);
  if (!headed.tui || typeof headed.tui !== 'object') {
    throw new SpawnError(E_MISSING_KEY, `${label}.headed.tui must be an object`, { file: filePath, key: `${label}.headed.tui` });
  }
  checkUnknownKeys(headed.tui, KNOWN_TUI_KEYS, `${label}.headed.tui`, filePath);
  assertArrayOfStrings(headed.tui.argv, `${label}.headed.tui.argv`, filePath);

  // ── Headed prompt carriage — the profile-LOAD gate (ADDITIVE; Design 3, OQ-F RULED D83) ──
  // The `headed.tui.prompt` key is OPTIONAL: a profile declaring none is VALID and means
  // "headed spawns of this profile REJECT a prompt" (reject-by-default, Behavior #9) — the
  // headed-CAPABLE seam (D17: presence of the `headed.tui` block = capable) is unchanged.
  const carriage = headed.tui.prompt;
  if (carriage !== undefined && carriage !== null) {
    if (carriage === 'stdin') {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.headed.tui.prompt: stdin is STRUCTURALLY ABSENT from the headed ` +
        `carriage vocabulary (stdin IS the terminal slave; write-then-close would type-then-hang-up the ` +
        `session) — declaring it is a config-LOAD failure, not a runtime value (known: file|keystroke)`,
        { file: filePath, key: `${label}.headed.tui.prompt`, carriage },
      );
    }
    if (!KNOWN_HEADED_CARRIAGES.has(carriage)) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.headed.tui.prompt must be one of file|keystroke (argv REMOVED, ` +
        `batch-08 item 4: caller free text never becomes argv)`,
        { file: filePath, key: `${label}.headed.tui.prompt`, carriage },
      );
    }
  }

  // The slot set is CLOSED_SLOTS, unconditionally. The former `{prompt}` admission (argv
  // carriage only) was retired with that carriage — a `{prompt}` slot in headed.tui.argv is now
  // an E_UNKNOWN_SLOT config-load failure regardless of what the profile declares.
  for (let i = 0; i < headed.tui.argv.length; i++) {
    detectUnknownSlots(headed.tui.argv[i], `${label}.headed.tui.argv[${i}]`, filePath);
  }

  // Consistency, declared-but-absent direction: a carriage whose slot is missing would compose
  // no prompt at spawn time. Refuse the profile at LOAD instead (server/pty/carriage.js refused
  // the same shapes at spawn time — the gates agree).
  if (carriage === 'file' && !headed.tui.argv.some((el) => el.includes('{prompt_file}'))) {
    throw new SpawnError(
      E_CONFIG_LOAD,
      `${label}.headed.tui.prompt: file declared but headed.tui.argv carries no {prompt_file} slot`,
      { file: filePath, key: `${label}.headed.tui.argv`, carriage },
    );
  }

  // keystroke (declared LAST RESORT, Design 3): a profile declaring it MUST also declare a
  // readiness marker — matched against the RENDERED screen state, never raw ANSI bytes — and a
  // timeout whose expiry is the typed `prompt-injection-timeout` failure (Behavior #10), never a
  // hang and never a silent no-prompt session. Shape mirrors carriage.js's own check exactly.
  if (carriage === 'keystroke') {
    const ks = headed.tui.keystroke;
    if (!ks || typeof ks !== 'object' || Array.isArray(ks)
      || typeof ks.readiness !== 'string' || ks.readiness.length === 0
      || !Number.isInteger(ks.timeout_ms)) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.headed.tui.keystroke: keystroke carriage MUST declare a readiness ` +
        `marker (non-empty string, matched vs the RENDERED screen) and an integer timeout_ms ` +
        `(expiry → prompt-injection-timeout failure)`,
        { file: filePath, key: `${label}.headed.tui.keystroke`, carriage },
      );
    }
  }
}

// ── 7.42: the caged/portable halves (#d-profile-source-unification (4)) ──────────────────────
// One shared core (slots, carriage, session_ref, caps) with up to TWO command halves. A profile
// declares `exec:` (single-shape, every host) OR `command: {caged:, portable:}` — never both,
// because two sources for one argv is the drift this whole task exists to remove.
function validateCommandHalves(command, label, filePath) {
  assertObject(command, `${label}.command`, filePath);
  checkUnknownKeys(command, KNOWN_COMMAND_HALVES, `${label}.command`, filePath);
  if (Object.keys(command).length === 0) {
    throw new SpawnError(
      E_CONFIG_LOAD,
      `${label}.command declares no half — declare caged, portable, or both`,
      { file: filePath, key: `${label}.command` },
    );
  }
  for (const half of Object.keys(command)) {
    validateExec(command[half], label, filePath, `command.${half}`);
  }
}

// ── 7.42: the effort translation table (#d-profile-source-unification (3)) ───────────────────
// EFFORT IS NOT BAKED INTO THE PROFILE — it is a per-dispatch parameter slot in the abstract
// vocabulary, translated by the profile's OWN table. A harness with no such dial declares
// `inert: true`, which is STATED rather than silently dropped: an inert profile handed an effort
// level accepts it and emits no argv for it, and says so in the resolution result.
function validateEffort(effort, label, filePath) {
  assertObject(effort, `${label}.effort`, filePath);
  checkUnknownKeys(effort, KNOWN_EFFORT_KEYS, `${label}.effort`, filePath);

  if (effort.inert === true) {
    // An inert table declares nothing else — a dialect or argv beside `inert` would be a
    // contradiction the resolver would have to arbitrate at runtime.
    for (const key of ['dialect', 'values', 'argv', 'headed']) {
      if (effort[key] !== undefined) {
        throw new SpawnError(
          E_CONFIG_LOAD,
          `${label}.effort declares inert: true AND ${key} — an inert dial has no translation`,
          { file: filePath, key: `${label}.effort.${key}` },
        );
      }
    }
    return;
  }
  if (effort.inert !== undefined && effort.inert !== false) {
    throw new SpawnError(E_CONFIG_LOAD, `${label}.effort.inert must be a boolean`, { file: filePath, key: `${label}.effort.inert` });
  }

  assertString(effort.dialect, `${label}.effort.dialect`, filePath);
  assertArrayOfStrings(effort.rungs, `${label}.effort.rungs`, filePath);
  assertArrayOfStrings(effort.argv, `${label}.effort.argv`, filePath);

  // An EMPTY ladder would declare a dial with no reachable setting — which is what `inert: true`
  // means, and the two must not be spellable as the same thing: an empty `rungs:` would refuse
  // every rung while READING as a working dial, while inert accepts and says so.
  if (effort.rungs.length === 0) {
    throw new SpawnError(
      E_CONFIG_LOAD,
      `${label}.effort.rungs is empty — a dial with no rungs is an INERT dial and ` +
      `must declare itself one ('effort: { inert: true }'), never an empty ladder`,
      { file: filePath, key: `${label}.effort.rungs` },
    );
  }
  for (let i = 0; i < effort.rungs.length; i++) {
    if (effort.rungs[i].length === 0) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.effort.rungs[${i}] is empty — rung ${i + 1} would compose the ` +
        `harness's flag with no value`,
        { file: filePath, key: `${label}.effort.rungs` },
      );
    }
  }
  // The argv fragment MUST carry the {effort} slot, else the rung would be validated and then
  // thrown away — a dial that reads as working and changes nothing.
  if (!effort.argv.some((el) => el.includes('{effort}'))) {
    throw new SpawnError(
      E_CONFIG_LOAD,
      `${label}.effort.argv carries no {effort} slot — the level would be dropped silently`,
      { file: filePath, key: `${label}.effort.argv` },
    );
  }

  // Tri-state `headed:` — true (TUI accepts the same argv), false/absent (not expressible),
  // or a string list that must carry {effort}. Absent = false is the safe default.
  if (effort.headed !== undefined && effort.headed !== true && effort.headed !== false) {
    assertArrayOfStrings(effort.headed, `${label}.effort.headed`, filePath);
    if (!effort.headed.some((el) => el.includes('{effort}'))) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.effort.headed carries no {effort} slot — the level would be dropped silently`,
        { file: filePath, key: `${label}.effort.headed` },
      );
    }
  }
}

// ── resolveEffort — THE ONE implementation of rung → argv, shared by BOTH live consumers ─────
//
// `resolveProfile` (below) calls it, and so does the daemon's own `server/spawn/spawn.js#composeArgv`
// (wired 2026-08-11 under owner ruling `d-0811lp-effort-lane-build-now`). It is EXPORTED for exactly
// that: spawn.js composes `exec:` / `resume:` / `headed.tui:` blocks that resolveProfile has no path
// for — routing the whole composition through resolveProfile is tasks 7.43/7.54 and is NOT done here
// — so the choice was between sharing this function or writing the table's second interpreter. "A
// second interpreter of the one file is the same drift as a second file" (#d-profile-source-
// unification), so: one function, two callers, one table.
//
// Returns { argv, applied, inert }. `applied` carries the rung, the harness's dialect name, the
// literal it composed and the ladder's size — a consumer logs what actually happened rather than
// what it asked for.
function resolveEffort(profile, rung, label, mode) {
  if (rung === null || rung === undefined) return { argv: [], applied: null, inert: false };
  if (!Number.isInteger(rung) || rung < 1) {
    throw new SpawnError(
      E_UNKNOWN_EFFORT,
      `effort must be an INTEGER RUNG >= 1 (rung 1 = lowest reasoning, rung N = highest), got: ` +
      `${JSON.stringify(rung)}`,
      { profile: label, effort: rung },
    );
  }
  if (!profile.effort) {
    throw new SpawnError(
      E_UNKNOWN_EFFORT,
      `profile ${label} declares no effort table — it cannot translate a rung. A harness ` +
      `with no such dial must declare 'effort: { inert: true }' so the slot is STATED inert ` +
      `rather than silently dropped.`,
      { profile: label, effort: rung },
    );
  }
  if (profile.effort.inert === true) {
    // STATED, never silently dropped (G-270): the caller's rung is accepted and reported back as
    // inert, so a consumer logs "this harness has no effort dial" instead of believing it applied
    // one. An inert profile declares NO range, so no rung is out of range on it.
    return { argv: [], applied: null, inert: true };
  }
  const rungs = profile.effort.rungs;
  if (rung > rungs.length) {
    throw new SpawnError(
      E_UNKNOWN_EFFORT,
      `effort rung ${rung} is outside profile ${label}'s range 1..${rungs.length} ` +
      `(${rungs.map((r, i) => `${i + 1}=${r}`).join(', ')})`,
      { profile: label, effort: rung, min: 1, max: rungs.length, rungs: rungs.slice() },
    );
  }
  const value = rungs[rung - 1];
  const applied = { rung, of: rungs.length, dialect: profile.effort.dialect, value };
  if (mode === 'headed') {
    const headed = profile.effort.headed;
    if (headed === true) {
      // TUI accepts the same effort.argv — fall through.
    } else if (Array.isArray(headed)) {
      const argv = resolveTemplateSlots(headed, {}).map((el) => el.replace('{effort}', value));
      return { argv, applied, inert: false };
    } else {
      // false or absent — not expressible headed. Distinct from inert (G-270).
      return { argv: [], applied, inert: false, headedNotCarried: true };
    }
  }
  const argv = resolveTemplateSlots(
    profile.effort.argv,
    // The {effort} slot is NOT in CLOSED_SLOTS (that set governs the workdir/prompt/session
    // vocabulary), so it is substituted here against the profile's own rung literal.
    {},
  ).map((el) => el.replace('{effort}', value));
  return { argv, applied, inert: false };
}

// ── THE KEY/ARGV AGREEMENT GUARD (owner ruling `#d-abolish-profile-names`, 2026-08-12) ─────────
//
// Under `profiles:` the pair a row RAN was DERIVED from its argv, so key and reality could not
// disagree — the key was arbitrary and meant nothing. Under `launch-specs:` the KEY is the
// authority every lookup goes through, which opens exactly one new failure: a spec filed under
// `claude/claude-opus-5` whose argv says `--model claude-haiku-4-5`. That is the silent-wrong-model
// launch this whole line of work exists to kill, so the old derivation law survives HERE, as a
// LOAD-TIME GUARD rather than a lookup. Refused at boot, where a human is reading output.
//
// Only `exec:`-shaped specs are checked. A `command: {caged:, portable:}` spec has two argvs and
// no single pin to compare; the daemon spawn path refuses those anyway (G-144,
// `E_SPEC_HALVES_UNSUPPORTED`), so the gap is not reachable from a launch.
function validateSpecKey(spec, harness, model, label, filePath) {
  const ran = bindingOf(spec);
  if (!ran) return;                              // no `exec:` half — nothing to compare against
  if (ran.harness === harness && ran.model === model) return;
  throw new SpawnError(
    E_CONFIG_LOAD,
    `${label} is filed under harness '${harness}' model '${model}' but its exec.argv runs `
    + `harness '${ran.harness}' model '${ran.model || '(no --model/-m pin)'}'. The KEY is what every `
    + 'seat cast resolves through, so a key that disagrees with the command line is a launch that '
    + 'runs a model nobody asked for while every record says otherwise. Fix the key or the argv.',
    { file: filePath, key: label, keyed: { harness, model }, runs: ran },
  );
}

function validateSpec(profile, label, filePath, seatBindValidator, toolsetNames = null) {
  assertObject(profile, `${label}`, filePath);
  checkUnknownKeys(profile, KNOWN_SPEC_KEYS, `${label}`, filePath);

  // r-seats-only-architecture (2): the per-profile toolset CEILING — the widest tier a dispatch
  // of this profile may ask for. Must name a tier of the closed enum, and (when the install
  // declares a `toolsets:` block) one that block actually speaks.
  if (profile.toolset_ceiling !== undefined) {
    if (!TOOLSET_ORDER.includes(profile.toolset_ceiling)) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.toolset_ceiling must be one of ${TOOLSET_ORDER.join('|')}, got: ${profile.toolset_ceiling}`,
        { file: filePath, key: `${label}.toolset_ceiling` },
      );
    }
    if (toolsetNames && !toolsetNames.includes(profile.toolset_ceiling)) {
      throw new SpawnError(
        E_CONFIG_LOAD,
        `${label}.toolset_ceiling names "${profile.toolset_ceiling}", which the toolsets block does not declare ` +
        `(declared: ${toolsetNames.join(', ')})`,
        { file: filePath, key: `${label}.toolset_ceiling` },
      );
    }
  }

  const hasExec = Boolean(profile.exec);
  const hasHalves = Boolean(profile.command);
  if (hasExec && hasHalves) {
    throw new SpawnError(
      E_CONFIG_LOAD,
      `${label} declares BOTH exec and command — one profile, one argv source`,
      { file: filePath, key: `${label}.command` },
    );
  }
  if (!hasExec && !hasHalves) {
    throw new SpawnError(E_MISSING_KEY, `${label}.exec is required`, { file: filePath, key: `${label}.exec` });
  }
  if (hasExec) validateExec(profile.exec, label, filePath);
  else validateCommandHalves(profile.command, label, filePath);

  // The resume template: same block shape as `exec`, validated by the same function (one
  // definition of what a command block is). A resume argv with no `{session_ref}` slot would
  // resume nothing in particular, so it is refused rather than launched.
  if (profile.resume !== undefined) {
    validateExec(profile.resume, label, filePath, 'resume');
    if (!JSON.stringify(profile.resume.argv).includes('{session_ref}')) {
      throw new SpawnError(
        E_MISSING_KEY,
        `${label}.resume.argv carries no {session_ref} slot — it would resume no particular session`,
        { file: filePath, key: `${label}.resume.argv` },
      );
    }
  }

  if (profile.effort !== undefined) validateEffort(profile.effort, label, filePath);

  if (!profile.session_ref) {
    throw new SpawnError(E_MISSING_KEY, `${label}.session_ref is required`, { file: filePath, key: `${label}.session_ref` });
  }
  validateSessionRef(profile.session_ref, label, filePath);

  if (profile.headed) {
    validateHeaded(profile.headed, label, filePath);
  }

  if (!profile.workdir_root) {
    throw new SpawnError(E_MISSING_KEY, `${label}.workdir_root is required`, { file: filePath, key: `${label}.workdir_root` });
  }
  assertString(profile.workdir_root, `${label}.workdir_root`, filePath);

  if (!profile.caps) {
    throw new SpawnError(E_MISSING_KEY, `${label}.caps is required`, { file: filePath, key: `${label}.caps` });
  }
  validateCaps(profile.caps, label, filePath);

  if (profile.sandbox) validateSandbox(profile.sandbox, label, filePath, seatBindValidator);
  if (profile.env) validateEnv(profile.env, label, filePath);
}

function validateSpawnBlock(spawn, filePath) {
  assertObject(spawn, 'spawn', filePath);
  const known = new Set(['data_root', 'carrier', 'kill_grace_seconds']);
  checkUnknownKeys(spawn, known, 'spawn', filePath);
  if (spawn.data_root !== undefined) assertString(spawn.data_root, 'spawn.data_root', filePath);
  if (spawn.carrier !== undefined && !['auto', 'systemd', 'setsid'].includes(spawn.carrier)) {
    throw new SpawnError(E_CONFIG_LOAD, `spawn.carrier must be one of auto|systemd|setsid`, { file: filePath, key: 'spawn.carrier' });
  }
  if (spawn.kill_grace_seconds !== undefined && (!Number.isInteger(spawn.kill_grace_seconds) || spawn.kill_grace_seconds <= 0)) {
    throw new SpawnError(E_CONFIG_LOAD, `spawn.kill_grace_seconds must be a positive integer`, { file: filePath, key: 'spawn.kill_grace_seconds' });
  }
}

function validateBindBlock(bind, filePath) {
  assertObject(bind, 'bind', filePath);
  const known = new Set(['host', 'port']);
  checkUnknownKeys(bind, known, 'bind', filePath);
}

function validateAuthBlock(auth, filePath) {
  assertObject(auth, 'auth', filePath);
  const known = new Set(['senders_file']);
  checkUnknownKeys(auth, known, 'auth', filePath);
}

function loadConfig(filePath, opts = {}) {
  const { seatBindValidator } = opts;
  let raw;
  try {
    raw = fs.readFileSync(filePath, 'utf8');
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `cannot read config file: ${err.message}`, { file: filePath });
  }

  let parsed;
  try {
    parsed = yaml.load(raw);
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `malformed YAML: ${err.message}`, { file: filePath });
  }

  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new SpawnError(E_CONFIG_LOAD, 'config must be a YAML mapping', { file: filePath });
  }

  // The daemon-only namespaces are skipped by the profile surface (see DAEMON_ONLY_ROOT_KEYS);
  // everything else still faces the closed allowlist.
  const rootForCheck = {};
  for (const key of Object.keys(parsed)) {
    if (!DAEMON_ONLY_ROOT_KEYS.has(key)) rootForCheck[key] = parsed[key];
  }
  checkUnknownKeys(rootForCheck, KNOWN_TOP_KEYS, 'config root', filePath);

  if (parsed.bind) validateBindBlock(parsed.bind, filePath);
  if (parsed.auth) validateAuthBlock(parsed.auth, filePath);
  if (parsed.spawn) validateSpawnBlock(parsed.spawn, filePath);

  if (!parsed.default_workdir_root) {
    throw new SpawnError(E_MISSING_KEY, 'default_workdir_root is required at the top level', { file: filePath, key: 'default_workdir_root' });
  }
  assertString(parsed.default_workdir_root, 'default_workdir_root', filePath);

  // ── THE TWO MECHANICS BLOCKS (owner ruling `#d-abolish-profile-names`, 2026-08-12) ─────────
  //
  // `profiles:` — one flat map keyed by an arbitrary NAME — is abolished. What replaces it is two
  // blocks split by ONE test: does this entry have a (harness, model) identity?
  //
  //   `launch-specs:`  YES. Nested `harness: { model: { …mechanics… } }` and keyed by the PAIR, so
  //                    a seat's cast addresses its mechanics directly and no name sits in between.
  //   `jobs:`          NO. Deterministic launches that pin no model (`test-sleep`'s `sleep 60`) —
  //                    sub-ruling 1: "a job's name IS its identity", so these stay name-keyed.
  //
  // Both are flattened into ONE-LEVEL maps here (`launchSpecs` keyed `harness/model` by
  // `catalog.js#specKey`, `jobs` keyed by name) so every daemon-side lookup is a single own-property
  // test rather than a two-level walk.
  //
  // ⚠ BOTH BLOCKS ARE OPTIONAL, AND THAT IS DELIBERATE. Requiring `launch-specs:` was considered
  // and dropped: "this config can cast nothing" is not detectable as a defect at LOAD — a config
  // used to assert a load-shape, or one that carries only job stand-ins, legitimately has none —
  // and the condition it would guard is caught at the right door anyway, far more loudly.
  // `specForSeatCast` refuses every launch with `E_UNMAPPED_BINDING` and prints
  // `castable: (none — the config declares no launch-specs: block)`. A load-time copy of that
  // would only fire earlier on configs that were never going to launch anything.
  for (const key of ['launch-specs', 'jobs']) {
    const block = parsed[key];
    if (block !== undefined && (block === null || typeof block !== 'object' || Array.isArray(block))) {
      throw new SpawnError(E_CONFIG_LOAD, `${key} must be a mapping`, { file: filePath, key });
    }
  }

  // ── r-seats-only-architecture (1)/(2): merge the SHARED blocks into every entry ────────────
  //
  // `cage:` (the one seat-cage template, SeatBinds included — merged as each entry's sandbox)
  // and the top-level `caps:` (the one global caps block) are declared ONCE; each entry
  // receives them here, with the entry's OWN keys winning — the "rare per-entry overrides
  // only by ruling" seam. `sandbox_default`/`caps_default` are accepted synonyms so the resolver
  // does not break on a spelling. Merged BEFORE per-entry validation so the merged shape is
  // what gets validated (caps is a required key, and under the shared block an entry
  // legitimately declares none of its own). A config with the blocks already expanded per
  // entry via YAML anchors needs no merge and passes through this loop unchanged.
  const toolsetNames = parsed.toolsets !== undefined ? validateToolsets(parsed.toolsets, filePath) : null;
  const capsDefault = parsed.caps ?? parsed.caps_default ?? null;
  const sandboxDefault = parsed.cage ?? parsed.sandbox_default ?? null;
  if (capsDefault !== null) assertObject(capsDefault, 'caps_default', filePath);
  if (sandboxDefault !== null) assertObject(sandboxDefault, 'sandbox_default', filePath);

  // Flatten + validate. The label a refusal prints is the entry's FULL config path
  // (`launch-specs.claude.claude-fable-5`, `jobs.test-sleep`) — an operator has to be able to open
  // the file at the line the message names, and under a nested block the leaf key alone is not
  // enough to find it.
  const applyDefaults = (entry) => {
    if (entry === null || typeof entry !== 'object' || Array.isArray(entry)) return entry; // validateSpec refuses it
    if (capsDefault) entry.caps = { ...capsDefault, ...(entry.caps || {}) };
    if (sandboxDefault) entry.sandbox = { ...sandboxDefault, ...(entry.sandbox || {}) };
    return entry;
  };

  const launchSpecs = {};
  for (const harness of Object.keys(parsed['launch-specs'] || {})) {
    const models = parsed['launch-specs'][harness];
    assertObject(models, `launch-specs.${harness}`, filePath);
    for (const model of Object.keys(models)) {
      const label = `launch-specs.${harness}.${model}`;
      const spec = applyDefaults(models[model]);
      validateSpec(spec, label, filePath, seatBindValidator, toolsetNames);
      validateSpecKey(spec, harness, model, label, filePath);
      launchSpecs[specKey(harness, model)] = spec;
    }
  }

  const jobs = {};
  for (const name of Object.keys(parsed.jobs || {})) {
    const label = `jobs.${name}`;
    const spec = applyDefaults(parsed.jobs[name]);
    validateSpec(spec, label, filePath, seatBindValidator, toolsetNames);
    jobs[name] = spec;
  }

  const config = {
    bind: parsed.bind || {},
    auth: parsed.auth || {},
    spawn: {
      data_root: parsed.spawn?.data_root || null,
      carrier: parsed.spawn?.carrier || 'auto',
      kill_grace_seconds: parsed.spawn?.kill_grace_seconds ?? 10,
    },
    default_workdir_root: parsed.default_workdir_root,
    // THE (harness, model) -> mechanics table, flattened. `catalog.js#specKey` builds the key and
    // `catalog.js#catalogOf` reads it back apart — one spelling of the join, in one module.
    launchSpecs,
    // The name-keyed deterministic stand-ins. Deliberately NOT merged into `launchSpecs`: they
    // carry no (harness, model), so a seat can never cast to one, which is exactly the ambiguity
    // the split removes.
    jobs,
    // r-seats-only-architecture (2): the declared toolsets block, RAW (a mapping may attach
    // per-harness tier definitions its consumers read); null when the config predates the
    // block. The vocabulary is validated above; the ORDER is TOOLSET_ORDER's, exported.
    toolsets: parsed.toolsets ?? null,
  };

  return config;
}

function resolveTemplateSlots(template, values) {
  return template.map((element) => {
    let out = element;
    SLOT_RE.lastIndex = 0;
    const matches = [...out.matchAll(SLOT_RE)];
    for (const m of matches) {
      const slot = m[0];
      const key = m[1];
      if (!(key in values)) {
        throw new SpawnError(E_MISSING_KEY, `template slot ${slot} has no value`, { slot });
      }
      out = out.replace(slot, values[key]);
    }
    return out;
  });
}

// A RELATIVE requested workdir is anchored on the WORKSPACE ROOT, never on the daemon's own
// process.cwd() — the SAME constraint resolveWorkdir already applies to a workspace-relative
// `workdir_root` below (D58 repoint, D26(3)). cwd is "a convenience default for dev runs"
// (server/index.js's own comment on its root resolution), so anchoring a workdir on it makes the
// resolution a function of the START DIRECTORY: the identical job row lands in a different folder,
// or fails realpath outright, purely by how the unit was started. An ABSOLUTE workdir is
// UNCHANGED — path.resolve ignores every preceding segment once one is absolute.
function canonicalizeWorkdir(requested, filePath, workspaceRoot = null) {
  if (requested === undefined || requested === null) return null;
  if (typeof requested !== 'string' || requested.length === 0) {
    throw new SpawnError(E_CONFIG_LOAD, 'workdir must be a non-empty string', { file: filePath });
  }
  try {
    const resolved = fs.realpathSync(path.resolve(workspaceRoot || process.cwd(), requested));
    return resolved;
  } catch (err) {
    throw new SpawnError(E_CONFIG_LOAD, `workdir does not exist or is not resolvable: ${requested}`, { workdir: requested });
  }
}

// D58 open-item ruling (smallest shape): the per-execution launch dir lives at
// `<workspaceRoot>/.rbtv/sessions/<exec-id>/`. The sessions root is DERIVED, never a new
// config key. It MUST be a sibling of the heart store's `.rbtv/` (D58(3): `.rbtv/heart/` — the
// control-plane store — stays out of every worker's reach), so it is sourced FROM the store's
// own db path (`<ws>/.rbtv/heart/heart.db`), which guarantees the sibling relationship. index.js
// is frozen for this task and cannot pass the workspace root in, so the fallback chain mirrors
// index.js's own machine-agnostic resolution: the store's `.rbtv/`, then RBTV_IGNITE_WORKSPACE_ROOT,
// else null (a store with no `.rbtv/` shape — a test-only flat db — yields null, and the default
// branch then bases the session dir on the profile's own workdir_root, which is still contained).
function resolveWorkspaceRoot(heartDbPath) {
  if (heartDbPath) {
    const parts = path.resolve(heartDbPath).split(path.sep);
    const idx = parts.lastIndexOf('.rbtv');
    if (idx > 0) return parts.slice(0, idx).join(path.sep) || path.sep;
  }
  const env = process.env.RBTV_IGNITE_WORKSPACE_ROOT;
  if (env) return path.resolve(env);
  return null;
}

function sessionsRootFor(workspaceRoot) {
  return workspaceRoot ? path.join(workspaceRoot, '.rbtv', 'sessions') : null;
}

// D56 fix (D58 contract). BOTH branches now pass the SAME fail-closed containment check —
// the resolved dir must sit inside the profile's workdir_root or the spawn REFUSES
// (E_WORKDIR_ESCAPE). The former default branch returned `default_workdir_root` UNCHECKED
// (the fail-open); it now materializes a per-execution launch dir under the sessions root and
// enforces it exactly as the caller branch enforces a caller-supplied workdir. A worker that
// cannot be contained does not run (the D48 fail-closed direction).
function resolveWorkdir(profile, requestedWorkdir, defaultWorkdirRoot, filePath, opts = {}) {
  const { execId, sessionsRoot = null, workspaceRoot = null } = opts;

  // Resolve the profile's containment boundary to an absolute path. A machine-agnostic
  // committed workdir_root may be workspace-relative (the D58 repoint `.rbtv/sessions`, D26(3)):
  // resolve it against the workspace root the daemon runs under, never a stray process cwd.
  const workdirRootAbs = path.isAbsolute(profile.workdir_root)
    ? profile.workdir_root
    : path.resolve(workspaceRoot || process.cwd(), profile.workdir_root);

  if (requestedWorkdir === undefined || requestedWorkdir === null) {
    if (execId === undefined || execId === null) {
      throw new SpawnError(E_WORKDIR_MISSING, 'default-branch launch requires an exec id to materialize the session dir', { profile });
    }
    // The session dir is sourced from the sessions root (workspace-derived), which is
    // INDEPENDENT of the profile's workdir_root — so this check is not vacuous: a sessions
    // root that falls outside workdir_root (misconfiguration, or a divergence a mutation test
    // injects) is REFUSED. In production the two coincide; the check proves they do.
    const base = sessionsRoot || workdirRootAbs;
    fs.mkdirSync(workdirRootAbs, { recursive: true, mode: 0o700 });
    const sessionDir = path.join(base, String(execId));
    fs.mkdirSync(sessionDir, { recursive: true, mode: 0o700 });
    const resolved = fs.realpathSync(sessionDir);
    const allowedRoot = fs.realpathSync(workdirRootAbs);
    if (resolved !== allowedRoot && !resolved.startsWith(allowedRoot + path.sep)) {
      throw new SpawnError(E_WORKDIR_ESCAPE, `resolved session dir ${resolved} is outside profile workdir_root ${allowedRoot}`, { workdir: resolved, allowedRoot });
    }
    return resolved;
  }

  const resolved = canonicalizeWorkdir(requestedWorkdir, filePath, workspaceRoot);
  const allowedRoot = fs.realpathSync(workdirRootAbs);
  if (resolved !== allowedRoot && !resolved.startsWith(allowedRoot + path.sep)) {
    throw new SpawnError(E_WORKDIR_ESCAPE, `workdir ${resolved} is outside profile workdir_root ${allowedRoot}`, { workdir: resolved, allowedRoot });
  }
  return resolved;
}

// ═════════════════════════════════════════════════════════════════════════════════════════════
// resolveLaunchSpec — THE shared policy point (task 7.42 criterion 3; re-keyed at 7.787)
//
// ⚠ THE SECOND ARGUMENT IS NO LONGER A NAME. It is the (harness, model) a seat is CAST as — the
// only address a launch spec has since `#d-abolish-profile-names`. `{ job: '<name>' }` addresses
// the name-keyed `jobs:` block instead, which is the one place a name still identifies mechanics
// (sub-ruling 1: a job's name IS its identity). Nothing else may select a spec, and no caller
// anywhere in ignite supplies either form for an AGENT launch — the daemon reads the seat.
//
// A caller supplies: that address, an effort rung, and values for DECLARED SLOTS.
// It supplies NO argv, NO flags, and NO half. Three bounds, each enforced rather than documented:
//
//   1. UNDECLARED SLOT KEYS ARE REFUSED (E_RAW_FLAG). A caller cannot smuggle `--dangerously-x`
//      through a slot map by inventing a key.
//   2. VALUES ARE SUBSTITUTED INTO DECLARED POSITIONS, NEVER APPENDED. The post-condition below
//      asserts the resolved argv is exactly the template length plus the profile's OWN declared
//      effort fragment. A caller value can therefore never BECOME an argv element — it can only
//      fill one the profile already wrote.
//   3. THE HALF IS DETECTED, NOT CHOSEN (host.js).
//
// Bound (2) is the one worth stating precisely, because it is what "rejects raw flags" actually
// means. Rejecting strings that start with `-` would be a blocklist, and a blocklist over caller
// text is a losing game. The real guarantee is structural: there is no code path that pushes a
// caller-supplied string onto argv as its own element.
// ═════════════════════════════════════════════════════════════════════════════════════════════
function resolveLaunchSpec(config, address, opts = {}) {
  const { effort = null, slots = {}, hostCapability = null, toolset = null } = opts;

  const isJob = Boolean(address && address.job);
  const table = (isJob ? (config && config.jobs) : (config && config.launchSpecs)) || {};
  const name = isJob ? String(address.job) : specKey(address && address.harness, address && address.model);
  if (!Object.hasOwn(table, name)) {
    throw new SpawnError(E_UNKNOWN_LAUNCH_SPEC, `no launch spec for ${isJob ? `job ${name}` : `harness+model ${name}`}`, {
      spec: name,
      known: Object.keys(table),
    });
  }
  const profile = table[name];

  // ── half selection ────────────────────────────────────────────────────────────────────────
  // `hostCapability` exists ONLY so a single resolution pass can reuse one detection; it is NOT
  // a caller preference and the resolver never lets it widen what the host can do. Passing
  // `caged` on a bwrap-less box is refused below exactly as detection would refuse it.
  const detected = detectHostCapability();
  const capability = hostCapability || detected;
  if (capability === CAGED && detected !== CAGED) {
    throw new SpawnError(
      E_NO_PORTABLE_HALF,
      `caged half requested for profile ${name} but this host has no containment capability ` +
      `(detected: ${detected}) — the half is a property of the HOST, never a caller choice`,
      { profile: name, requested: capability, detected },
    );
  }

  let execBlock;
  let half = null;
  if (profile.exec) {
    // Single-shape profile: one command for every host. Every profile that predates 7.42 is this
    // shape, which is why the daemon's behaviour is unchanged.
    execBlock = profile.exec;
  } else {
    half = capability;
    execBlock = profile.command[half];
    if (!execBlock) {
      if (half === PORTABLE) {
        throw new SpawnError(
          E_NO_PORTABLE_HALF,
          `profile ${name} declares no portable half and this host has no containment capability ` +
          `(bwrap absent) — REFUSING. Running the caged half uncaged would drop every wall the ` +
          `profile presumes (e.g. a harness whose own sandbox is disabled because bwrap covers it).`,
          { profile: name, detected: capability, declared: Object.keys(profile.command) },
        );
      }
      // A caged host with only a portable half: use it. Portable is strictly weaker in what it
      // presumes, so running it on a capable box is safe — the reverse never is.
      half = PORTABLE;
      execBlock = profile.command[PORTABLE];
    }
  }

  // ── slot bound (1): only DECLARED slots may be supplied ───────────────────────────────────
  const declared = new Set();
  for (const element of execBlock.argv) {
    SLOT_RE.lastIndex = 0;
    for (const m of element.matchAll(SLOT_RE)) declared.add(m[1]);
  }
  for (const key of Object.keys(slots)) {
    if (!declared.has(key)) {
      throw new SpawnError(
        E_RAW_FLAG,
        `profile ${name} declares no {${key}} slot — a caller may fill declared slots only, ` +
        `never append argv (declared: ${Array.from(declared).join(', ') || 'none'})`,
        { profile: name, slot: key, declared: Array.from(declared) },
      );
    }
    if (typeof slots[key] !== 'string') {
      throw new SpawnError(E_RAW_FLAG, `slot ${key} must be a string`, { profile: name, slot: key });
    }
  }

  const argv = resolveTemplateSlots(execBlock.argv, slots);

  // ── effort: a numeric rung composed by the profile's OWN ladder (resolveEffort, above) ────
  const { argv: effortArgv, applied: effortApplied, inert: effortInert } =
    resolveEffort(profile, effort, name);

  const finalArgv = argv.concat(effortArgv);

  // ── bound (2), ASSERTED rather than assumed ───────────────────────────────────────────────
  // The resolved argv length must equal the template's plus the profile's own effort fragment.
  // If a future edit ever pushes a caller value on as its own element, this fires here rather
  // than in production. A comment claiming the property would not survive that edit; this does.
  const expected = execBlock.argv.length + effortArgv.length;
  if (finalArgv.length !== expected) {
    throw new SpawnError(
      E_RAW_FLAG,
      `resolution changed argv arity for ${name} (${execBlock.argv.length} template + ` +
      `${effortArgv.length} effort => expected ${expected}, got ${finalArgv.length}) — a caller ` +
      `value became an argv element`,
      { profile: name, expected, got: finalArgv.length },
    );
  }

  // ── toolset: a per-dispatch parameter CLAMPED to the profile's ceiling (narrowing only) ────
  // r-seats-only-architecture (2): tool rights are per-dispatch, drawn from the closed enum, and
  // a dispatch may only NARROW its profile's `toolset_ceiling` — asking for a wider tier is a
  // LOUD refusal, never a silent clamp-down (a silently narrowed dispatch would read as granted).
  // No requested toolset resolves to the ceiling itself; a profile with no ceiling refuses a
  // toolset request outright — the same stated-not-dropped posture the effort table takes.
  const toolsetCeiling = profile.toolset_ceiling ?? null;
  let resolvedToolset = toolsetCeiling;
  if (toolset !== null && toolset !== undefined) {
    if (!TOOLSET_ORDER.includes(toolset)) {
      throw new SpawnError(
        E_UNKNOWN_TOOLSET,
        `toolset must be one of ${TOOLSET_ORDER.join('|')} (closed enum), got: ${toolset}`,
        { profile: name, toolset },
      );
    }
    if (!toolsetCeiling) {
      throw new SpawnError(
        E_UNKNOWN_TOOLSET,
        `profile ${name} declares no toolset_ceiling — it cannot honor a toolset request. ` +
        'Declare a ceiling on the profile so the clamp has a law to apply.',
        { profile: name, toolset },
      );
    }
    if (TOOLSET_ORDER.indexOf(toolset) > TOOLSET_ORDER.indexOf(toolsetCeiling)) {
      throw new SpawnError(
        E_TOOLSET_WIDENING,
        `REFUSING TOOLSET WIDENING: dispatch asks for "${toolset}" but profile ${name}'s ` +
        `toolset_ceiling is "${toolsetCeiling}" — a dispatch may only NARROW its profile's ` +
        'ceiling, never widen it (r-seats-only-architecture (2))',
        { profile: name, toolset, ceiling: toolsetCeiling },
      );
    }
    resolvedToolset = toolset;
  }

  return {
    name,
    half,
    hostCapability: capability,
    argv: finalArgv,
    prompt: execBlock.prompt,
    effort: effortApplied,
    effortInert,
    toolset: resolvedToolset,
    toolset_ceiling: toolsetCeiling,
    session_ref: profile.session_ref,
    // Reported unresolved (the ref belongs to a PREDECESSOR session this call knows nothing
    // about) — but never dropped: a declared template silently missing from the resolver's own
    // output is how a consumer concludes the profile cannot resume.
    resume: profile.resume,
    workdir_root: profile.workdir_root,
    caps: profile.caps,
    sandbox: profile.sandbox,
    env: profile.env,
    headed: profile.headed,
  };
}

module.exports = {
  loadConfig,
  resolveLaunchSpec,
  resolveTemplateSlots,
  resolveWorkdir,
  resolveWorkspaceRoot,
  sessionsRootFor,
  CLOSED_SLOTS,
  DAEMON_ONLY_ROOT_KEYS,
  resolveEffort,
  // r-seats-only-architecture (2) — the toolset surface, owned here.
  TOOLSET_ORDER,
  E_UNKNOWN_TOOLSET,
  E_TOOLSET_WIDENING,
};
