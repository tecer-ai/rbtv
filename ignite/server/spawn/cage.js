'use strict';

// Task 7.11 — the SEAT FENCE: an ORDERED, TYPED bind stack for the seat-folder launch split.
//
// D3 (2026-08-19) is the allow-list. The threat model is agents writing in repos that are not
// `goals/`. Rogue writes on another seat's folder or on the wrong file inside the goal folder
// are not a concern for now. Record forgery is a NON-goal — the fence does not enforce it.
//
//   bind     <goalDir>          the goal folder RW (ledgers, planning, coordination, sessions.csv)
//   ro-mask  <goalDir>/seats    PEER SEAT FOLDERS ABSENT + writes refuse (D48)
//   bind     <seatDir>          the seat's own folder RW
//   ro-bind  <seatDir>/seat.md  the masked file inside the RW folder (wall-control surface)
//   ro-bind  <rbtvRoot>         rbtv repo + <ws>/.rbtv/mirror, READ
//   bind     <worktree>         (per grant) + the repo git plumbing trio
//
// A file-level ro-bind of a RECORD is gone (denying them was the EROFS class). A file-level
// ro-bind of a WALL-CONTROL SURFACE stays: seat.md and coordination/permission-edits.csv.
// Those are not forgery-prevention; they are the fence holding its own posts.
//
// Absence IS the mechanism here exactly as it is in bwrap.js: nothing is denied, things are simply
// never bound. ORDER of the bindings is load-bearing — later wins — so the composition is a
// first-class artifact. The superseded anti-forgery assertion (`assertGroundTruthUnwritable`)
// is deleted: D3 rules coordination ledgers writable.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { SpawnError, E_CAGE_TEMPLATE } = require('./errors');
const { composePrivateScope, emptyMaskSource } = require('./private-scope');

// The bind verbs a template may declare. Deliberately NOT the whole bwrap vocabulary: these three
// compose every opening `r-711-write-bounds` allows, and an unknown verb is a template error
// rather than a silently-dropped line.
// `bind-try` is `bind` that TOLERATES A MISSING SOURCE (bwrap's own `--bind-try`). It counts as
// an RW verb: when the source IS there the opening is read-write. Used by grant lines whose
// source may be absent (a worktree, a bus, a permission-edits carve).
// `ro-mask` is SRC≠DEST: ro-bind an EMPTY source over DEST so the path lists nothing AND writes
// refuse (EROFS). Replaces `--tmpfs` over peer seat folders (D48: fake-success tmpfs is the
// false-complete shape). `tmpfs` stays in the vocabulary for fixture templates that still spell it.
const BIND_VERBS = new Set(['ro-bind', 'ro-bind-try', 'bind', 'bind-try', 'tmpfs', 'ro-mask']);
const RW_VERBS = new Set(['bind', 'bind-try']);

// `{grant:FIELD}` — the one PARAMETERIZED slot form. An entry carrying any `{grant:...}` slot is
// expanded ONCE PER GRANT rather than once, which is how a per-worktree / per-repo opening is
// expressed without the template having to know how many grants a seat holds. One uniform rule;
// the alternative (a distinct `{worktree:*}` / `{repoGit:*}` fan-out per kind) is the same rule
// written three times.
const GRANT_SLOT_RE = /\{grant:([a-zA-Z][a-zA-Z0-9_]*)\}/g;

// The scalar slots. `{workdir}` is admitted so a seat template can be written in the vocabulary
// the rest of the config already speaks; it resolves to the seat folder on this path.
// `runDir` is RETIRED (7.607 E2b, design-lock item 8: the package IS the goal folder). A template
// still spelling it now refuses at compose time with `E_CAGE_TEMPLATE`, which is the loud outcome —
// an unknown slot silently resolving to nothing is how a cage opens a hole nobody sees.
const SCALAR_SLOTS = new Set(['workdir', 'seatDir', 'goalDir']);

function parseEntry(entry, index) {
  if (typeof entry !== 'string' || entry.length === 0) {
    throw new SpawnError(E_CAGE_TEMPLATE, `sandbox.SeatBinds[${index}] must be a non-empty string`, { index });
  }
  const sep = entry.indexOf(':');
  if (sep < 0) {
    throw new SpawnError(
      E_CAGE_TEMPLATE,
      `sandbox.SeatBinds[${index}] must be "<verb>:<path>" (verbs: ${[...BIND_VERBS].join('|')}) — got ${entry}`,
      { index, entry },
    );
  }
  const verb = entry.slice(0, sep);
  const template = entry.slice(sep + 1);
  if (!BIND_VERBS.has(verb)) {
    throw new SpawnError(
      E_CAGE_TEMPLATE,
      `sandbox.SeatBinds[${index}] unknown bind verb "${verb}" (known: ${[...BIND_VERBS].join('|')})`,
      { index, entry, verb },
    );
  }
  if (template.length === 0) {
    throw new SpawnError(E_CAGE_TEMPLATE, `sandbox.SeatBinds[${index}] has an empty path`, { index, entry });
  }
  return { verb, template };
}

// Substitute the scalar slots. A slot with no value is a LOUD failure, never a literal `{slot}`
// carried into an argv — the same posture resolveTemplateSlots takes in config.js, and for the
// same reason: a literal `{seatDir}` reaching bwrap would be a bind of a directory named
// `{seatDir}`, which either fails obscurely or, worse, succeeds.
function substituteScalars(template, values, index) {
  return template.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (match, key) => {
    if (!SCALAR_SLOTS.has(key)) {
      throw new SpawnError(
        E_CAGE_TEMPLATE,
        `sandbox.SeatBinds[${index}] unknown slot ${match} (known: ${[...SCALAR_SLOTS].map((s) => `{${s}}`).join(' ')} and {grant:FIELD})`,
        { index, slot: match },
      );
    }
    const value = values[key];
    if (typeof value !== 'string' || value.length === 0) {
      throw new SpawnError(E_CAGE_TEMPLATE, `sandbox.SeatBinds[${index}] slot ${match} has no value`, { index, slot: match });
    }
    return value;
  });
}

function substituteGrant(template, grant, index) {
  return template.replace(GRANT_SLOT_RE, (match, field) => {
    const value = grant[field];
    if (typeof value !== 'string' || value.length === 0) {
      throw new SpawnError(
        E_CAGE_TEMPLATE,
        `sandbox.SeatBinds[${index}] slot ${match} has no usable value on this grant — declared-but-null ` +
        `is a degraded grant refusing loudly, never a silent skip (grant fields: ${Object.keys(grant).join(', ') || 'none'})`,
        { index, slot: match, field },
      );
    }
    return value;
  });
}

// Compose the ORDERED bind spec. Input order is output order — the template is the sequence.
//
//   composeSeatCage({ seatBinds, values, grants })
//     -> [{ verb, path }, ...]
//
// `grants` is the seat's OWN records (worktree + repo plumbing, and — under
// `r-seats-only-architecture` (5) — harness-credential entitlements), resolved by the daemon from
// the seat's records and never from caller input (CMP-17: callers can never inject paths at
// request time). A template entry with no `{grant:…}` slot appears exactly once regardless of how
// many grants exist; an entry WITH one appears once per grant, in grant order. Zero grants
// therefore yields zero worktree openings — the correct answer, and reached without a special case.
//
// GRANTS ARE HETEROGENEOUS since `r-seats-only-architecture` (5): one grant list carries worktree
// grants AND harness-credential grants, and the shared template carries a line class for each. A
// grant that DECLARES none of an entry's fields is simply not that entry's kind — skipped, never
// an error. A grant that declares the field as a KEY with a null/empty value still fails loudly in
// substituteGrant: that is the unreadable-`.git` case (resolveSeatGrants writes `repoGit: null`),
// where the degraded worktree must refuse at compose time rather than silently lose its plumbing.
function composeSeatCage({ seatBinds = [], values = {}, grants = [] } = {}) {
  if (!Array.isArray(seatBinds)) {
    throw new SpawnError(E_CAGE_TEMPLATE, 'sandbox.SeatBinds must be an array of strings', {});
  }
  const spec = [];
  for (let i = 0; i < seatBinds.length; i++) {
    const { verb, template } = parseEntry(seatBinds[i], i);
    const scalarResolved = substituteScalars(template, values, i);
    GRANT_SLOT_RE.lastIndex = 0;
    const grantFields = [...scalarResolved.matchAll(GRANT_SLOT_RE)].map((m) => m[1]);
    if (grantFields.length === 0) {
      const opening = { verb, path: normalize(scalarResolved, i) };
      if (verb === 'ro-mask' && values.seatDir && contains(opening.path, path.normalize(values.seatDir))) {
        opening.punchThrough = path.normalize(values.seatDir);
      }
      spec.push(opening);
      continue;
    }
    for (const grant of grants) {
      if (!grantFields.some((f) => f in grant)) continue; // not this entry's grant kind
      const opening = { verb, path: normalize(substituteGrant(scalarResolved, grant, i), i) };
      if (typeof grant.grantClass === 'string' && grant.grantClass) {
        opening.grantClass = grant.grantClass;
        if (typeof grant.exposedCliName === 'string' && grant.exposedCliName) {
          opening.exposedCliName = grant.exposedCliName;
        }
      }
      spec.push(opening);
    }
  }
  return spec;
}

// Every path in a composed spec is absolute and lexically normal. A relative path would be
// resolved by bwrap against whatever cwd the daemon happens to hold.
function normalize(p, index) {
  if (!path.isAbsolute(p)) {
    throw new SpawnError(E_CAGE_TEMPLATE, `sandbox.SeatBinds[${index}] resolved to a relative path: ${p}`, { index, path: p });
  }
  return path.normalize(p);
}

// Ancestor-or-self containment, exported because the ground-truth assertion below and the
// `rw-paths` grant resolver (spawn.js) must answer the SAME question the same way — a second
// spelling of "is this path inside that one" is a second place the wall can drift.
function contains(dir, file) {
  const d = path.normalize(dir);
  const f = path.normalize(file);
  return f === d || f.startsWith(d.endsWith(path.sep) ? d : d + path.sep);
}

// Flatten to bwrap flags. SRC == DEST throughout, the same property bwrap.js composes for: the
// caged process sees real paths, so a path the daemon recorded (a workdir, a worktree, an argv
// element) still means the same thing inside the namespace.
function punchMaskSource(entry, punchThrough) {
  const key = require('node:crypto').createHash('sha1').update([entry, punchThrough].join('\0')).digest('hex').slice(0, 16);
  const dir = path.join(os.tmpdir(), 'rbtv-cage-romask', key);
  fs.mkdirSync(path.join(dir, path.relative(entry, punchThrough)), { recursive: true });
  return dir;
}

function specToBwrapFlags(spec) {
  const flags = [];
  for (const { verb, path: p, punchThrough } of spec) {
    if (verb === 'tmpfs') flags.push('--tmpfs', p);
    else if (verb === 'ro-mask') {
      const src = punchThrough ? punchMaskSource(p, punchThrough) : emptyMaskSource();
      flags.push('--ro-bind', src, p);
    } else flags.push(`--${verb}`, p, p);
  }
  return flags;
}

// LOAD-TIME validation of a bind template, with no values to substitute yet — the shape half of
// what `composeSeatCage` does at spawn time. It lives here, beside the parser it shares, so the
// vocabulary has exactly ONE definition: a config.js that re-listed the verbs and slots would be
// a second definition, and the two would drift the first time one of them gained an entry. A
// profile with a typo'd verb or slot must fail at config LOAD (loudly, at the daemon's own door),
// never at the moment a seat is being launched.
function validateSeatBindTemplate(seatBinds, profileName, filePath) {
  if (!Array.isArray(seatBinds) || seatBinds.some((e) => typeof e !== 'string')) {
    throw new SpawnError(
      E_CAGE_TEMPLATE,
      `profiles.${profileName}.sandbox.SeatBinds must be an array of "<verb>:<path>" strings`,
      { file: filePath, key: `profiles.${profileName}.sandbox.SeatBinds` },
    );
  }
  for (let i = 0; i < seatBinds.length; i++) {
    const { template } = parseEntry(seatBinds[i], i);
    // Slot names only — a value-less pass. Unknown names throw; known ones are left alone.
    const withoutGrants = template.replace(GRANT_SLOT_RE, 'x');
    withoutGrants.replace(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g, (match, key) => {
      if (!SCALAR_SLOTS.has(key)) {
        throw new SpawnError(
          E_CAGE_TEMPLATE,
          `profiles.${profileName}.sandbox.SeatBinds[${i}] unknown slot ${match} ` +
          `(known: ${[...SCALAR_SLOTS].map((s) => `{${s}}`).join(' ')} and {grant:FIELD})`,
          { file: filePath, key: `profiles.${profileName}.sandbox.SeatBinds`, index: i, slot: match },
        );
      }
      return match;
    });
  }
  return true;
}

// ── r-seat-context-cut-at-launch-folder (owner, 2026-08-07) ─────────────────────────────────
//
// A seat inherits NO harness artifacts from the path ABOVE its launch folder. Enforced in the
// cage rather than requested of the agent: a directory artifact gets a `--tmpfs` over it, a file
// artifact gets `/dev/null` ro-bound over it. Both are bwrap-native — nothing on the vault is
// edited, and the mask exists only inside this one namespace.
//
// THE SET, declared ONCE, by NAME. Every harness in the roster discovers instruction files and
// project config by walking up from its cwd, so masking a name masks it for whichever harness
// reads it; masking a name a given harness ignores costs nothing. The union is therefore the
// right shape and a per-harness table (which would need a verified up-tree behaviour measured
// for each of the four) is not.
const MASK_INSTRUCTION_FILES = ['CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', 'AGENT.md'];
const MASK_CONFIG_DIRS = ['.claude', '.codex', '.opencode', '.agents', '.kimi'];

// The ruling's bound (i): CLAUDE.md/AGENTS.md INSIDE the goals tree stay inherited — the run
// folder's roster, run rules and THIS-RUN-IS-CLOSED banner are the seat's actual conduct.
const GOALS_SUBTREE = path.join('.rbtv', 'goals');

// What the caged process ACTUALLY sees at a path is decided by the LAST spec entry covering it —
// later wins, the same reading bwrap takes. Nothing covering it means the path is already absent
// (no read-root grant, no vault), so masking it would only make bwrap mkdir a mountpoint into a
// namespace where nothing was there to hide.
function lastCovering(spec, target) {
  let hit = null;
  for (const entry of spec) if (contains(entry.path, target)) hit = entry;
  return hit;
}

// The auto-memory store. The harness keys it on a project slug derived from the workdir, and the
// slug the harness picks is not knowable from here without reimplementing its derivation — so
// every existing `memory` dir under the project store is masked and the derivation question never
// arises. The SIBLING session `.jsonl` transcripts are deliberately untouched: `--resume` reads
// them, and the ruling's scope line requires resume to survive the memory mask.
// ponytail: one readdir of the project store per spawn (601 entries today, sub-ms). Derive the
// slug instead only if this ever shows up on a spawn-latency measurement.
function memoryMaskPaths(home) {
  const projects = path.join(home, '.claude', 'projects');
  let entries;
  try {
    entries = fs.readdirSync(projects);
  } catch {
    return [];
  }
  return entries.map((e) => path.join(projects, e, 'memory')).filter((p) => fs.existsSync(p));
}

// Compose the mask FLAGS to append after a seat cage's own openings (last = wins).
//
//   composeAncestorMasks(spec, { workspaceRoot, launchFolder, keepInstructionFiles })
//     -> { flags, masked: { instructionFiles, configDirs, memory, secrets }, policy }
//
// Returns flags rather than spec entries because a file mask is `--ro-bind /dev/null <file>` —
// SRC != DEST, which the spec vocabulary (SRC == DEST throughout) cannot express.
//
// `keepInstructionFiles` is the CHANNEL policy (ruling bound (ii)): that seat additionally keeps
// the path-up `CLAUDE.md`/`AGENTS.md` but NOT `.claude/`. It is a per-seat declaration, not a
// path special-case — a second seat needing the same posture declares it and gets it.
function composeAncestorMasks(spec, { workspaceRoot, launchFolder, keepInstructionFiles = false, home = os.homedir(), log = () => {} } = {}) {
  const flags = [];
  const masked = { instructionFiles: 0, configDirs: 0, memory: 0, secrets: 0 };
  const policy = keepInstructionFiles ? 'keep-instruction-files' : 'cut-all';

  const maskDir = (p) => { flags.push('--tmpfs', p); };
  const maskFile = (p) => { flags.push('--ro-bind', '/dev/null', p); };

  if (workspaceRoot && launchFolder && contains(workspaceRoot, launchFolder)) {
    const goals = path.join(workspaceRoot, GOALS_SUBTREE);
    // The walk starts at the launch folder's PARENT: the launch folder's own artifacts are never
    // masked (a seat may carry its own `.claude/` with skills — the capability is kept).
    let dir = path.dirname(path.normalize(launchFolder));
    for (; contains(workspaceRoot, dir); dir = path.dirname(dir)) {
      const inGoals = contains(goals, dir);
      const names = [
        ...(keepInstructionFiles || inGoals ? [] : MASK_INSTRUCTION_FILES),
        ...MASK_CONFIG_DIRS,
      ];
      for (const name of names) {
        const p = path.join(dir, name);
        let st;
        try { st = fs.statSync(p); } catch { continue; }
        const cover = lastCovering(spec, p);
        if (!cover || cover.verb === 'tmpfs') continue; // already absent in-namespace
        if (st.isDirectory()) { maskDir(p); masked.configDirs++; }
        else { maskFile(p); masked.instructionFiles++; }
      }
      if (dir === path.normalize(workspaceRoot)) break;
    }
  }

  // Bound (iii): auto-memory is dropped for ALL seat spawns, channel seat included.
  for (const p of memoryMaskPaths(home)) { maskDir(p); masked.memory++; }

  // ── W5 (owner ruling D-1, 2026-08-13) — THE PRIVATE READ SCOPE ──────────────────────────────
  // The third-party secrets file (`.rbtv/config/.env`, task 7.566) is now the FIRST of two
  // hardcodes inside a general default-deny seed; its former standalone block lived here and is
  // absorbed by `private-scope.js`, which composes masks AND the pierce re-binds that must follow
  // them. Appended last inside the last-appended mask block: order is the mechanism (adv C51).
  // ⚠ ORDER IS LOAD-BEARING — masks then pierces, and this whole list after the cage spec.
  let privateScope = { flags: [], masked: 0, pierced: [], refused: [] };
  if (workspaceRoot) {
    privateScope = composePrivateScope(spec, { workspaceRoot, log });
    flags.push(...privateScope.flags);
    masked.secrets += privateScope.masked;
  }

  return { flags, masked, policy, pierced: privateScope.pierced, refusedPierces: privateScope.refused };
}

module.exports = {
  contains,
  lastCovering,
  composeAncestorMasks,
  MASK_INSTRUCTION_FILES,
  MASK_CONFIG_DIRS,
  composeSeatCage,
  specToBwrapFlags,
  validateSeatBindTemplate,
  BIND_VERBS,
  RW_VERBS,
};
