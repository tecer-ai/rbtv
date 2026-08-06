'use strict';

// Task 7.11 — the SEAT CAGE: the redesigned writable set for the seat-folder launch split.
//
// v1's wall had ONE RW opening (the flat session dir) and one input shape: a flat list of paths,
// every one of them `--bind` (RW). The seat split needs something the flat list cannot express —
// an ORDERED, TYPED stack, where a read-only bind of a parent, a tmpfs that erases a subtree, and
// a read-write bind of a leaf all land in a specific sequence and each one deliberately shadows
// what came before it:
//
//   ro-bind  <goalDir>          decisions.md / issues.md / doubts.md READABLE
//   tmpfs    <goalDir>/runs     every OTHER run ABSENT
//   ro-bind  <runDir>           sessions.csv / state.csv / run CLAUDE.md / conduct READABLE
//   tmpfs    <runDir>/seats     PEER SEAT FOLDERS ABSENT  <- kernel-enforces "never read another
//   bind     <seatDir>                                       seat's folder"; the seat's own folder
//   ro-bind  <seatDir>/seat.md                                is then punched back through it
//   bind     <worktree>        (per grant)
//   ro-bind  <repo>/.git       + bind objects/refs/logs/worktrees/<name>  (per grant)
//
// Absence IS the mechanism here exactly as it is in bwrap.js: nothing is denied, things are simply
// never bound. What this module adds is that the ORDER of the bindings is itself load-bearing, so
// the composition is a first-class artifact that can be asserted about before any process exists.
//
// THE STRUCTURAL INVARIANT (design §1). The identity gate's ground truth is the run-level
// `sessions.csv`, which sits ABOVE `seats/`. A gate whose ground truth the caged process can
// rewrite is decoration — and under `r-launch-automode-all-harnesses` (the harness permission
// layer is off; the kernel sandbox IS the safety boundary) decoration is all that would be left.
// So `assertGroundTruthUnwritable` below REFUSES to compose a spec in which any RW opening
// contains that file. It is an ASSERTION over the composed spec, deliberately, not an inference
// from an observed outcome: G-107's lesson is that checking an outcome and concluding a property
// is how a guard comes to be enforced by nothing but the operator's habits.

const path = require('node:path');
const { SpawnError, E_CAGE_TEMPLATE, E_CAGE_GROUND_TRUTH } = require('./errors');

// The bind verbs a template may declare. Deliberately NOT the whole bwrap vocabulary: these three
// compose every opening `r-711-write-bounds` allows, and an unknown verb is a template error
// rather than a silently-dropped line.
const BIND_VERBS = new Set(['ro-bind', 'bind', 'tmpfs']);
const RW_VERBS = new Set(['bind']);

// `{grant:FIELD}` — the one PARAMETERIZED slot form. An entry carrying any `{grant:...}` slot is
// expanded ONCE PER GRANT rather than once, which is how a per-worktree / per-repo opening is
// expressed without the template having to know how many grants a seat holds. One uniform rule;
// the alternative (a distinct `{worktree:*}` / `{repoGit:*}` fan-out per kind) is the same rule
// written three times.
const GRANT_SLOT_RE = /\{grant:([a-zA-Z][a-zA-Z0-9_]*)\}/g;

// The scalar slots. `{workdir}` is admitted so a seat template can be written in the vocabulary
// the rest of the config already speaks; it resolves to the seat folder on this path.
const SCALAR_SLOTS = new Set(['workdir', 'seatDir', 'goalDir', 'runDir']);

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
      spec.push({ verb, path: normalize(scalarResolved, i) });
      continue;
    }
    for (const grant of grants) {
      if (!grantFields.some((f) => f in grant)) continue; // not this entry's grant kind
      spec.push({ verb, path: normalize(substituteGrant(scalarResolved, grant, i), i) });
    }
  }
  return spec;
}

// Every path in a composed spec is absolute and lexically normal. A relative path would be
// resolved by bwrap against whatever cwd the daemon happens to hold; a `..` segment would make
// the ground-truth assertion below answerable only by accident.
function normalize(p, index) {
  if (!path.isAbsolute(p)) {
    throw new SpawnError(E_CAGE_TEMPLATE, `sandbox.SeatBinds[${index}] resolved to a relative path: ${p}`, { index, path: p });
  }
  return path.normalize(p);
}

function contains(dir, file) {
  const d = path.normalize(dir);
  const f = path.normalize(file);
  return f === d || f.startsWith(d.endsWith(path.sep) ? d : d + path.sep);
}

// THE STRUCTURAL INVARIANT, asserted over the composed spec (design §1; G5 bar P8c).
//
// A later RW opening shadows an earlier read-only one, so the question is not "does some entry
// mention this path" but "does the LAST entry covering it make it writable". That is what the
// caged process actually sees, and it is the only reading that stays correct when someone appends
// a line to the template a year from now.
//
// Refusing here rather than at probe time is the point: a probe proves this composition is sound,
// an assertion proves EVERY composition is. G-115 is tonight's demonstration of the difference —
// a guard that held only because operators typed relative names.
function assertGroundTruthUnwritable(spec, groundTruthPath) {
  if (!groundTruthPath) {
    throw new SpawnError(E_CAGE_GROUND_TRUTH, 'seat cage requires the identity ground-truth path to assert against', {});
  }
  const target = path.normalize(groundTruthPath);
  let writable = null;
  for (const entry of spec) {
    if (!contains(entry.path, target)) continue;
    // A tmpfs over an ancestor makes the target ABSENT, which is not writable ground truth —
    // it is no ground truth at all, and the gate fails closed on a missing file (§4b step 2).
    writable = RW_VERBS.has(entry.verb) ? entry : null;
  }
  if (writable) {
    throw new SpawnError(
      E_CAGE_GROUND_TRUTH,
      `seat cage would leave the identity ground truth ${target} WRITABLE via "${writable.verb}:${writable.path}" — ` +
      'the gate reads that file to decide who is sitting here; a seat that can rewrite it can name itself (design §1)',
      { groundTruth: target, opening: writable },
    );
  }
  return spec;
}

// Flatten to bwrap flags. SRC == DEST throughout, the same property bwrap.js composes for: the
// caged process sees real paths, so a path the daemon recorded (a workdir, a worktree, an argv
// element) still means the same thing inside the namespace.
function specToBwrapFlags(spec) {
  const flags = [];
  for (const { verb, path: p } of spec) {
    if (verb === 'tmpfs') flags.push('--tmpfs', p);
    else flags.push(`--${verb}`, p, p);
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

module.exports = {
  composeSeatCage,
  assertGroundTruthUnwritable,
  specToBwrapFlags,
  validateSeatBindTemplate,
  BIND_VERBS,
  RW_VERBS,
};
