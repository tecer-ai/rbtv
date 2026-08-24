'use strict';

// ── W5 — THE PRIVATE READ SCOPE (owner ruling D-1, 2026-08-13) ────────────────────────────────
//
// A `read-root: true` seat binds the WHOLE workspace read-only. Ruling D-1 replaces that flat
// "everything" with **workspace-wide READ minus a default-deny seed**: enumerated private entries,
// a pattern floor beneath them (so a NEW secret file is denied the day it appears rather than the
// day someone remembers to list it), and `.git` — which without a mask hands every one of those
// files back through `git cat-file` / `git log -p` no matter what the deny list says.
//
// THREE TIERS, AND THE ORDER IS THE MECHANISM (adv C51). Grants compose FIRST (the seat cage's
// own spec), masks land SECOND (later wins in bwrap), and the PIERCES — the openings a seat was
// legitimately granted that happen to sit inside a private entry — are re-emitted THIRD. A pierce
// written into the grant tier could not work at all: the mask would simply re-cover it.
//
// MASK SEMANTICS (adv C50). `--tmpfs` is writable-and-evaporates and a `/dev/null` ro-bind reads
// empty — NEITHER denies a write, and a seat writing into a masked directory would get a success
// whose output does not exist (the D6 false-complete shape). So a directory is masked by
// RO-BINDING AN EMPTY SOURCE over it: reads list nothing AND writes refuse (EROFS). The guarantee
// this module makes is therefore content-absence + write-refusal, asserted as such by the probes.
//
// SCOPE, stated so the KG record cannot overclaim: this is a PATH control, not a content control.
// Hardlinks, copies made before the mask existed, and content already quoted into a transcript are
// out of scope.
//
// GENERALITY (repo rule "RBTV Content Must Be General"): the defaults below name NO instance. The
// per-workspace enumerated entries live in that workspace's `.rbtv/config/private.json`; this file
// ships the pattern floor and the two hardcodes, which are the fail-closed floor when that file is
// absent or unparseable.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const PRIVATE_JSON_REL = path.join('.rbtv', 'config', 'private.json');

// HARDCODED — never overrulable by private.json OR by any seat grant (adv C53).
//   `.rbtv/config/.env`      the provider credentials (the 2026-08-11 mask, absorbed here)
//   `.rbtv/config/private.json` the list ITSELF — its contents enumerate where the secrets are
const HARDCODED_REL = [path.join('.rbtv', 'config', '.env'), PRIVATE_JSON_REL];

// The pattern floor. Matched against each entry's BASENAME during the walk, so `**/x` and `x` mean
// the same thing here; the `**/` prefix is kept in the written file because that is how a user
// reads it. Fails CLOSED for files nobody has enumerated yet.
const DEFAULT_PATTERNS = ['**/*.env', '**/credentials/', '**/*token*', '**/*.key', '**/.git'];

// THE ONE NON-ENTRY, AND IT IS LOAD-BEARING (adv C55). `cli/lib/config.js#readEnvFileToken` walks
// up from the seat's cwd for `.rbtv/config/sender-token.env` and reads IGNITE_SENDER_TOKEN out of
// it — VERIFIED 2026-08-13 at `cli/lib/config.js:178-207`; it is the ONLY file `resolveToken`
// reads. It matches the floor three times over (`*.env`, `*token*`), so without this exclusion the
// floor would silently break EVERY seat's send. The 2026-08-11 split that made the `.env` mask
// survivable is exactly this file; do not seed it, and do not delete this note.
const DEFAULT_ALLOW = [path.join('.rbtv', 'config', 'sender-token.env')];

// A directory mask needs an EMPTY SOURCE to ro-bind (see MASK SEMANTICS above). One shared,
// mode-0500 directory on the host — it is never written to, and every masked directory in every
// cage points at it.
// ponytail: one shared empty dir; give each cage its own only if something ever needs to tell two
// masked directories apart from inside.
function emptyMaskSource() {
  const p = path.join(os.tmpdir(), 'rbtv-cage-empty');
  try { fs.mkdirSync(p, { recursive: true, mode: 0o500 }); } catch { /* already there */ }
  return p;
}

// Interpreter code files are EXEMPT from the pattern FLOOR (owner ruling 2026-08-18, amending
// `#d-cage-seed-ratified`): `**/*token*` was masking PyYAML's `tokens.py` in every tool venv —
// `import yaml` fatal in every cage (`G-plan-interviewer-0818-0213`), same for oauthlib's token
// modules and google.oauth2.id_token. The floor hunts secret FILES; a `.py`/`.pyc`/`.so` is code.
// The exemption binds ONLY the pattern floor: explicit `deny` entries mask regardless of
// extension, and a floor-matching DIRECTORY (`credentials/`, `.git`) still masks whole — code
// under it included. Both floor matchers (the walk and `refusesPath`) MUST consult this same
// predicate, or the wall and the refusal disagree.
const CODE_FILE_RE = /\.(py|pyc|so)$/;
function isInterpreterCodeFile(name) { return CODE_FILE_RE.test(name); }

function globToRe(g) {
  const base = g.replace(/^\*\*\//, '').replace(/\/$/, '');
  return new RegExp('^' + base.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$');
}

function privateJsonPath(workspaceRoot) {
  return path.join(path.normalize(workspaceRoot), PRIVATE_JSON_REL);
}

// Read the workspace's private list. Absent / unreadable / unparseable -> the built-in floor, and
// LOUDLY: an operator who broke the JSON must not silently get a wider cage than yesterday's.
//
//   { deny: ["<workspace-relative path>", ...], patterns: ["**/glob", ...], allow: ["<rel>", ...] }
//
// `deny` entries are workspace-relative; a trailing `/`, a leading `./` and a trailing `.` are all
// tolerated and normalized away (adv C52), and an entry that escapes the workspace root is dropped
// with a reason. Case is the filesystem's — these are real paths, compared after normalization, not
// lowercased. A nested entry (an entry inside another entry) is harmless: both mask, the inner one
// is simply redundant.
function readPrivateScope(workspaceRoot, log = () => {}) {
  const root = path.normalize(workspaceRoot);
  const hardcoded = HARDCODED_REL.map((r) => path.join(root, r));
  let raw = null;
  try {
    raw = JSON.parse(fs.readFileSync(privateJsonPath(root), 'utf8'));
  } catch (err) {
    if (err.code !== 'ENOENT') {
      log('warn', `private.json unreadable — falling back to the built-in floor: ${err.message}`, { file: privateJsonPath(root) });
    }
  }
  const deny = Array.isArray(raw && raw.deny) ? raw.deny : [];
  const patterns = Array.isArray(raw && raw.patterns) ? raw.patterns : DEFAULT_PATTERNS;
  const allowRel = [...DEFAULT_ALLOW, ...(Array.isArray(raw && raw.allow) ? raw.allow : [])];

  const entries = [...hardcoded];
  for (const e of deny) {
    if (typeof e !== 'string' || e.trim() === '') { log('warn', 'private.json deny entry REFUSED: empty', { entry: e }); continue; }
    const trimmed = e.trim().replace(/^\.\//, '').replace(/\/+$/, '');
    if (path.isAbsolute(trimmed)) { log('warn', 'private.json deny entry REFUSED: absolute — entries are workspace-relative', { entry: e }); continue; }
    const abs = path.resolve(root, trimmed);
    if (abs === root || !inside(root, abs)) { log('warn', 'private.json deny entry REFUSED: outside the workspace root', { entry: e, resolved: abs }); continue; }
    entries.push(abs);
  }
  return {
    entries: [...new Set(entries)],
    hardcoded: new Set(hardcoded),
    patterns: patterns.map(globToRe),
    allow: new Set(allowRel.map((r) => path.resolve(root, r))),
  };
}

// Lexical containment — the ONE spelling, shared with cage.js (PRIN-11). Required lazily to keep
// the cage.js <-> private-scope.js pair out of a top-level require cycle.
function inside(dir, file) {
  return require('./cage').contains(dir, file);
}

function realInside(dir, file) {
  const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
  const d = real(dir);
  const f = real(file);
  return !!d && !!f && inside(d, f);
}

// ── The mask + pierce composition ─────────────────────────────────────────────────────────────
//
//   composePrivateScope(spec, { workspaceRoot, log })
//     -> { flags, masked, entries, pierced, refused }
//
// `flags` is masks-then-pierces, in that order, and MUST be appended to the seat's flag list after
// the cage spec (its caller, `cage.js#composeAncestorMasks`, is itself appended last — the single
// append-last call site stays, adv C49).
function composePrivateScope(spec, { workspaceRoot, log = () => {} } = {}) {
  const { lastCovering, specToBwrapFlags } = require('./cage');
  const { SpawnError, E_CAGE_PRIVATE_ALIAS } = require('./errors');
  const root = path.normalize(workspaceRoot);
  const scope = readPrivateScope(root, log);
  const flags = [];

  // A path is worth masking only where something actually BOUND it: nothing covering it, or a
  // tmpfs/ro-mask cover, means it is already absent in-namespace, and masking would only make
  // bwrap mkdir a mountpoint over nothing — worse, when that cover is itself read-only (`ro-mask`,
  // D48), the mkdir for the deeper mount fails against a read-only parent and the whole spawn dies
  // (D53/#576: a peer seat's `ro-mask`-covered folder collides with a pattern-floor match nested
  // under it). Same discipline as the ancestor walk this composes beside.
  const visible = (p) => {
    const cover = lastCovering(spec, p);
    return !!cover && cover.verb !== 'tmpfs' && cover.verb !== 'ro-mask';
  };

  // ── TIER 2a — the ENTRY SET: the enumerated list, then the pattern floor beneath it ──────────
  // THE FLOOR is only walked when the cage can actually SEE the workspace root (a `read-root:
  // true` seat); an ordinary seat has no opening there, so there is nothing to hide and no walk
  // to pay for.
  // A full recursive readdir of the workspace per read-root spawn. MEASURED, twice:
  //   2026-08-13  "111 ms" — that figure was WRONG for the universal read root W5 shipped, and it
  //               stood in this comment while every spawn paid 60x it.
  //   2026-08-15  6417-6822 ms over 75054 entries / 9349 dirs on the ignite VPS (live workspace,
  //               111 masked paths). The readdir itself is 148 ms of that. The other ~5.7 s was
  //               `entries.some((m) => inside(m, p))` — an O(tree x entries) containment scan, run
  //               75054 x up to 111 times, each call re-`require`ing cage.js.
  // The scan was also unnecessary: a path is only skipped when it IS a seed entry or lies under
  // one, and the loop never RECURSES into anything it skips or pushes — so nothing under a seed
  // entry is ever visited, and self-match against the seed set answers the same question. Set
  // membership instead: 174 ms, byte-identical 111-entry result. No cache, therefore no mask list
  // that can go stale — the walk is fresh on every composition, which `probe-private-scope-fresh`
  // holds.
  const entries = scope.entries.filter((e) => fs.existsSync(e));
  const seeded = new Set(entries);
  const rootCover = lastCovering(spec, root);
  if (rootCover && rootCover.verb !== 'tmpfs' && scope.patterns.length > 0) {
    (function walk(dir) {
      let listing;
      try { listing = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
      for (const ent of listing) {
        const p = path.join(dir, ent.name);
        if (scope.allow.has(p)) continue;
        if (seeded.has(p)) continue;                          // already denied by a seed entry
        if (scope.patterns.some((re) => re.test(ent.name))
            && (ent.isDirectory() || !isInterpreterCodeFile(ent.name))) { entries.push(p); continue; }
        if (ent.isDirectory() && !ent.isSymbolicLink()) walk(p);
      }
    })(root);
  }

  // ── TIER 3 — THE PIERCES, resolved here and re-emitted AFTER the masks (adv C51/C52) ────────
  //
  // A grant that NAMES a path inside a private entry is a deliberate, authored exception (the
  // therapy-summarizer's health path is the motivating case) and is punched back through. Three
  // things refuse instead:
  //   * the entry is one of the two HARDCODES (adv C53) — refused SILENTLY-BUT-LOGGED, the mask
  //     stands, and the opening under it reads empty. Unoverrulable by construction.
  //   * the opening NAMES an entry but RESOLVES out of it — a symlink swapped under the name.
  //   * the opening names NOTHING private but RESOLVES INTO a private entry — the alias attack
  //     spawn.js's own `rw-paths` comments document. This one THROWS: the mask cannot close it
  //     (the alias is a different mountpoint carrying the real content), and a cage that cannot
  //     be composed safely must not be composed at all. `resolveRwPathGrants` already refuses
  //     this per entry; this is the backstop for every grant class that does not.
  // A merely-BROADER opening (the read-root floor, a parent directory grant) is not a pierce: it
  // CONTAINS the entry rather than sitting inside it, so it never matches and the entry stays
  // masked.
  //
  // REMOVED (T2-R11, redesign D19): the `exposedCliCode` grant-class pierce (D4, 2026-08-18) that
  // used to live in TIER 2b below — an opening of that class CONTAINING an enumerated deny entry
  // (a declared CLI's own `config.yaml` / `credentials/`) used to re-open it whole. Owner ruling:
  // credentials are env-injected, never caged — no mechanism in this compiler re-opens
  // `credentials/`, `*.env`, `*.key`, or `*token*` for ANY caller/role, declared or not. This
  // TIER-3 named-grant pierce is unaffected (it serves unrelated authored exceptions, e.g. the
  // therapy-summarizer's health path) and still refuses the two HARDCODES unconditionally below.
  const pierced = [];
  const refused = [];
  const pierceOpenings = [];
  for (const opening of spec) {
    const host = entries.find((e) => inside(e, opening.path));
    if (host) {
      if (scope.hardcoded.has(host)) {
        refused.push({ opening: opening.path, reason: `names the unoverrulable private path ${host}` });
        continue;
      }
      if (!realInside(host, opening.path)) {
        refused.push({ opening: opening.path, reason: `names private ${host} but RESOLVES out of it — a segment is a symlink` });
        continue;
      }
      pierceOpenings.push({ opening, host });
      pierced.push(`${opening.verb}:${opening.path}`);
      continue;
    }
    const alias = entries.find((e) => realInside(e, opening.path));
    if (alias) {
      throw new SpawnError(
        E_CAGE_PRIVATE_ALIAS,
        `cage opening ${opening.verb}:${opening.path} RESOLVES inside the private path ${alias} without naming it — ` +
        'a grant reaches a private entry only by spelling it (the symlink-alias attack; ruling D-1)',
        { opening: opening.path, privateEntry: alias },
      );
    }
  }

  // ── TIER 2b — THE MASKS ─────────────────────────────────────────────────────────────────────
  // A directory is masked by ro-binding an EMPTY SOURCE (adv C50): reads list nothing AND writes
  // refuse. ⚠ A directory hosting a pierce needs that pierce's MOUNTPOINT to exist inside the
  // empty source — bwrap cannot mkdir one on a read-only mount, and without it the whole spawn
  // dies with "Can't mkdir … Read-only file system" (measured 2026-08-13). So the source is a
  // SKELETON: empty directories (and empty files) at exactly the pierced sub-paths, nothing else.
  const maskedPaths = [];
  for (const e of entries) {
    if (!visible(e)) continue;
    // REMOVED (T2-R11, redesign D19): the `exposedCliCode` grant-class pierce (D4, 2026-08-18)
    // that used to skip the mask here for a CLI's own `config.yaml` / `credentials/` when that
    // CLI was `exposed-clis:`-declared. Credentials are env-injected, never caged — every private
    // entry masks unconditionally now, declared CLI or not.
    let st;
    try { st = fs.statSync(e); } catch { continue; }
    if (st.isDirectory()) {
      flags.push('--ro-bind', maskSource(e, pierceOpenings.filter((p) => inside(e, p.opening.path)).map((p) => p.opening.path)), e);
    } else {
      flags.push('--ro-bind', '/dev/null', e);
    }
    maskedPaths.push(e);
  }

  for (const { opening } of pierceOpenings) flags.push(...specToBwrapFlags([opening]));

  return { flags, masked: maskedPaths.length, entries, pierced, refused };
}

// The empty (or pierce-skeletal) bind source for a masked directory. Keyed by the entry AND its
// pierce set, so two seats piercing different sub-paths never see each other's mountpoint names —
// an empty directory is still a name, and a name is still a disclosure.
function maskSource(entry, pierceTargets) {
  const sorted = [...pierceTargets].sort();
  if (sorted.length === 0) return emptyMaskSource();
  const key = require('node:crypto').createHash('sha1').update([entry, ...sorted].join('\0')).digest('hex').slice(0, 16);
  const dir = path.join(os.tmpdir(), 'rbtv-cage-mask', key);
  fs.mkdirSync(dir, { recursive: true });
  for (const t of sorted) {
    const dest = path.join(dir, path.relative(entry, t));
    let isDir = true;
    try { isDir = fs.statSync(t).isDirectory(); } catch { /* treat as dir */ }
    if (isDir) fs.mkdirSync(dest, { recursive: true });
    else { fs.mkdirSync(path.dirname(dest), { recursive: true }); if (!fs.existsSync(dest)) fs.writeFileSync(dest, ''); }
  }
  return dir;
}

// ── The edit-time disclosure (adv C54, second half) ────────────────────────────────────────────
//
// The daemon reads private.json AT DISPATCH: a cage already running keeps the list it was composed
// with, and nothing respawns it. So an operator who tightens the list must be told what is still
// running on the old one — and told the verb that closes it. Run after editing:
//
//   node server/spawn/private-scope.js <workspace-root>
//
// Liveness is the sessions ledger plus a real `kill(pid, 0)`: a row with no `ended` whose pid is
// gone is a crashed session, not a running cage.
function runningCages(workspaceRoot) {
  const goalsDir = path.join(path.normalize(workspaceRoot), '.rbtv', 'goals');
  const live = [];
  let goals;
  try { goals = fs.readdirSync(goalsDir, { withFileTypes: true }); } catch { return live; }
  for (const g of goals.sort((a, b) => a.name.localeCompare(b.name))) {
    if (!g.isDirectory()) continue;
    let rows;
    try { rows = fs.readFileSync(path.join(goalsDir, g.name, 'sessions.csv'), 'utf8').split('\n'); } catch { continue; }
    const header = (rows.shift() || '').split(',');
    const col = (name) => header.indexOf(name);
    for (const line of rows) {
      if (!line.trim()) continue;
      const cells = line.split(',');
      if ((cells[col('ended')] || '').trim()) continue;
      const pid = Number.parseInt(cells[col('pid')], 10);
      if (!Number.isInteger(pid) || pid <= 1) continue;
      try { process.kill(pid, 0); } catch { continue; }
      live.push({ goal: g.name, seat: cells[col('seat')], pid });
    }
  }
  return live;
}

// ── W3 — THE PRIVATE-PATH REFUSAL ────────────────────────────────────────────────────────────
//
// Any path that is, or lies inside, a private entry is refused UNCONDITIONALLY — the PIERCE rule
// is a materialize-time authoring affordance and never a runtime one. That question is THIS
// module's (the deny list, the hardcodes, the pattern floor and the realpath matching all live
// here). Historically this was also asked from OUTSIDE the process, by coord.py's `widen-cage`
// verb (ruling D-2) over a `--refuses` CLI answer — deleted with that verb ([T2-R6, C-6],
// 2026-08-24). The design reason it asked rather than re-decided still holds for any future
// caller: a second Python reader of `private.json` is exactly the two-interpreters drift PRIN-11
// forbids, and it would drift in the permissive direction — the one that matters.
//
// Returns the REASON string when the path is refused, `null` when it is not. Realpath-matched in
// both directions, so a symlink planted in a writable directory cannot smuggle a private target in.
function refusesPath(workspaceRoot, target) {
  const root = path.normalize(workspaceRoot);
  const scope = readPrivateScope(root);
  const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
  const abs = path.resolve(root, target);
  const rt = real(abs) || abs;
  // The ONE non-entry (`sender-token.env`) is never masked, so refusing it here would refuse a path
  // every seat already reads — a refusal with no wall behind it.
  if (scope.allow.has(abs) || scope.allow.has(rt)) return null;
  for (const e of scope.entries) {
    const re = real(e) || e;
    if (rt === re || inside(re, rt)) {
      return `it is, or lies inside, the private entry \`${e}\` — a runtime grant never pierces the private scope`;
    }
  }
  // The pattern FLOOR, matched against the target's own basename and every ancestor basename up to
  // the workspace root — the same basename matching `composePrivateScope`'s walk applies, so a NEW
  // secret file is refused the day it appears rather than the day someone enumerates it.
  let rtIsDir = false;
  try { rtIsDir = fs.statSync(rt).isDirectory(); } catch { /* absent -> treat as file */ }
  for (let p = rt; p && p !== root && inside(root, p); p = path.dirname(p)) {
    const b = path.basename(p);
    // The target's OWN basename gets the interpreter-code exemption the walk applies (a code
    // file is never floor-masked, so refusing it here would refuse a path with no wall behind
    // it); ancestor basenames are directories and keep matching.
    if (p === rt && !rtIsDir && isInterpreterCodeFile(b)) continue;
    if (scope.patterns.some((re) => re.test(b))) {
      return `\`${p}\` matches the private-scope pattern FLOOR (basename \`${b}\`) — fail-closed for secrets nobody has enumerated yet`;
    }
  }
  return null;
}

// ── THE DECLARABILITY QUESTION, asked from spawn.js's PATH shim (D56/D74, 2026-08-22) ──────────
//
// `local-bin: true` puts every name in the real `~/.local/bin` on a seat's PATH, undifferentiated.
// Some of those names are the coordination CLIs the grant was BUILT for (`coordinate`, `teamview`,
// `scaffold-seats`, …, spawn.js's own PATH-builder comment) — their own directories hold nothing
// this file would ever mask. Others (`stools`, `gtools`, …) read their own `config.yaml`/
// `credentials/` at argument-parser build time — undeclared, that reachability is the D56 defect:
// an undeclared seat reaching the name hits the raw masked-path `PermissionError` instead of a
// named refusal. (Historical: before T2-R11/redesign D19 removed the `exposedCliCode` pierce, a
// DECLARED seat's opening used to re-open the tool's own secrets; declaring no longer changes
// whether the mask lifts — every private entry masks unconditionally, declared or not — so this
// question now decides ONLY named-refusal-vs-raw-traceback, never reach.)
//
// The two classes are NOT named here (D74: the mechanism hardcodes no tool name). They are DERIVED
// from the SAME deny-list/pattern-floor data every other tier of this file reads: a candidate
// directory that holds, lies inside, or itself IS a private entry — by the enumerated list or the
// pattern floor — NEEDS a pierce to actually work; one that holds nothing private never needed one
// and is unaffected by this question. Scoped to the WORKSPACE only (mirrors `deny`'s own
// workspace-relative contract): a path outside `workspaceRoot` cannot be named in `private.json`
// and cannot be resolved by the `exposed-clis:` materializer either, so it is never a candidate for
// declaration and this returns `false` for it unconditionally — a host utility (`claude`, `codex`,
// `uv`, …) living outside the workspace is never affected.
function needsDeclaration(workspaceRoot, dir, log = () => {}) {
  const root = path.normalize(workspaceRoot);
  const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
  const rd = real(dir) || path.normalize(dir);
  if (rd !== root && !inside(root, rd)) return false;
  const scope = readPrivateScope(root, log);
  for (const e of scope.entries) {
    const re = real(e) || e;
    if (re === rd || inside(rd, re) || inside(re, rd)) return true;
  }
  if (scope.patterns.length === 0) return false;
  let hit = false;
  (function walk(p) {
    if (hit) return;
    let listing;
    try { listing = fs.readdirSync(p, { withFileTypes: true }); } catch { return; }
    for (const ent of listing) {
      if (hit) return;
      const full = path.join(p, ent.name);
      if (scope.allow.has(full)) continue;
      if (scope.patterns.some((re) => re.test(ent.name)) && (ent.isDirectory() || !isInterpreterCodeFile(ent.name))) { hit = true; return; }
      if (ent.isDirectory() && !ent.isSymbolicLink()) walk(full);
    }
  })(rd);
  return hit;
}

if (require.main === module) {
  // The `--refuses <workspace-root> <path>` CLI answer (asked by coord.py's now-deleted
  // `widen-cage` verb) was removed here when `widen-cage` was deleted (ruling [T2-R6, C-6],
  // 2026-08-24) — it had no other caller. `refusesPath` itself stays: it is still called
  // in-process by `probe-private-scope.js` and exported below.
  const ws = process.argv[2] || process.cwd();
  const live = runningCages(ws);
  if (live.length === 0) {
    console.log('private.json: no cage is running — the new list applies to every next dispatch.');
  } else {
    console.log(`private.json: ${live.length} cage(s) running with the PREVIOUS list: ` +
      live.map((s) => `${s.goal}/${s.seat}(pid ${s.pid})`).join(', '));
    console.log('A running cage keeps the list it was composed with. To close them on the new list, ' +
      'end each session (coordinate close-seat, or `ignite kill-session <session-id>`); the next ' +
      'dispatch composes against the edited file.');
  }
}

module.exports = {
  composePrivateScope,
  readPrivateScope,
  refusesPath,
  needsDeclaration,
  privateJsonPath,
  runningCages,
  emptyMaskSource,
  PRIVATE_JSON_REL,
  HARDCODED_REL,
  DEFAULT_PATTERNS,
  DEFAULT_ALLOW,
};
