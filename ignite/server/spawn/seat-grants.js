'use strict';

// server/spawn/seat-grants.js — THE SEAT-DECLARED GRANT RESOLVERS, shared between the two doors
// that must agree about them (task 7 · ruling D2, 2026-08-19).
//
// Extracted VERBATIM from spawn.js so `engine/cage-admission.js` — the pre-enqueue admission
// gate — composes admissibility from the SAME grant classes the spawner composes walls from.
// Before this file the gate read `goal-writes` only, so a widen declared in a frontmatter
// `rw-paths:` entry changed the real cage while the gate kept refusing off a composition that
// could not see it — the measured `audio-component-smith` permanent refusal loop
// (G-owner-console-0818-2030). One resolver, imported by both, is what makes that disagreement
// structurally impossible; a copy would be a second definition and the same drift with extra
// steps.
//
// The SECOND grant source this file used to carry, `coordination/permission-edits.csv` (W3, the
// leader's audited widen lane), is GONE ([T2-R12, T1-R9], 2026-08-24): the redesign deletes the
// grant store entirely — owner auth is an answer to a live ask, not a standing widen a leader
// files and a cage reads back. `rw-paths` is now the only workspace rw-grant source.

const fs = require('node:fs');
const path = require('node:path');
const { contains } = require('./cage');

// The LIST half of the one declaration reader. Same surface (seat.md frontmatter, ro-bound inside
// the cage), same lightweight parse — a YAML-style block list, read without pulling a parser into
// the spawn path. The block ends at the first line that is not a `- item`, so a malformed or
// mis-indented entry ends the list rather than swallowing the keys after it. `key` is always a
// literal from a calling module — never caller input.
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

// ── `rw-paths:` — the seat-declared READ-WRITE workspace paths (owner ruling "a", 2026-08-06) ──
//
// Motivating case: the channel-master holds the whole workspace under `read-root: true`, so an
// in-workspace CLI that must rewrite its own state (gtools refreshing an OAuth token) meets EROFS
// and its reads die when the token expires. The generic answer is a declared, validated list of
// workspace-relative paths punched back through the read-only floor.
//
// FAIL-CLOSED, PER LAUNCH. One conflicting or unresolved source refuses the whole spawn
// ([T2-R1] [C-6]): never skip-and-continue, never lastCovering. The four path-shape
// refusals, in the order they are cheapest to answer:
//
//   1. empty / absolute            — the key's vocabulary is workspace-RELATIVE, only
//   2. escapes the workspace root  — checked AFTER `..` normalization, so `a/../../etc` is caught
//   3. lands on a WALLED SURFACE of the goals tree `<ws>/.rbtv/goals` — `goalsTreeRefusal` below,
//      the ONE statement of the rule: the goals dir itself or any path CONTAINING it; a goal
//      folder's ROOT (`goals/<goal>`); anything under `<goal>/seats/` (every seat.md, every seat's
//      identity surface) or `<goal>/coordination/` (the bus); and a RECORD FILE by name —
//      sessions.csv, state.csv, seat.md,
//      taskforce.csv, goal.md, milestones.csv — wherever under the tree it sits. A PROPER
//      SUBFOLDER of a goal folder that is none of those (`<goal>/register`, `<goal>/planning`) is
//      ADMITTED. That carve is the 2026-08-22 change (ignite-engine m1, engine-goal E1): the
//      filing CLI's declared write root IS a goal subfolder, and the blanket "overlaps .rbtv/goals
//      in either direction" rule this replaced refused it on every spawn while protecting nothing
//      the walled set does not. The walled set is also what keeps the seat.md ro-carve winning —
//      an entry covering the seat's own folder is under `seats/` and is refused here, so it never
//      reaches the ordering question at all.
//   4. does not exist              — skipped; this resolver NEVER creates a path.
//   (+) the RESOLVED path is held to rules 2 and 3 AGAIN (fA-4 D-1): the lexical tests answer
//      where the path POINTS, not where it LANDS, and a symlink is how an entry lands on a walled
//      surface — or outside the workspace — without spelling it.
//
// The FOUR REFUSAL RULES, in ONE function: the reason string when `entry` may not be granted
// read-write to this seat, `null` when it may. ONE predicate for both remaining rw-grant sources —
// `rw-paths` (resolveRwPathGrants below) and `cli-write-roots`
// (`spawn.js#resolveCliWriteRootGrants`, W6) — and for `engine/cage-admission.js`, which composes
// admissibility from the same resolver. A second copy of the rule anywhere is the drift this file
// exists to prevent.
const GOALS_WALLED_DIRS = new Set(['seats', 'coordination']);
const GOALS_RECORD_FILES = new Set(['sessions.csv', 'state.csv', 'seat.md', 'taskforce.csv', 'goal.md', 'milestones.csv']);

// Rule 3. `goals` is the `<ws>/.rbtv/goals` dir and `target` an absolute normalized path — BOTH
// lexical, or BOTH resolved (realpath), so the one test serves both passes of rwPathRefusal.
function goalsTreeRefusal(goals, target) {
  const walled = (what) => `${what} — the identity/ground-truth surfaces (sessions.csv, seat.md, seats/, coordination/) stay unwritable: ${target}`;
  if (contains(target, goals)) return walled(`contains ${goals}`);
  if (!contains(goals, target)) return null;
  const rel = path.relative(goals, target).split(path.sep);   // [<goal>, ...inside the goal folder]
  if (rel.length < 2) return walled(`is a direct child of ${goals} (a goal root)`);
  if (GOALS_WALLED_DIRS.has(rel[1])) return walled(`is under <goal>/${rel[1]}/ in ${goals}`);
  const leaf = rel[rel.length - 1];
  if (GOALS_RECORD_FILES.has(leaf)) return walled(`is the record file ${leaf} under ${goals}`);
  return null;
}

function reasonFrom(refuse) {
  if (!refuse) return 'launch-refused';
  if (refuse.kind === 'conflict') {
    const pair = (refuse.pair || []).map((p) => `${p.access}:${p.path}`).join(' vs ');
    return `conflict ${pair || refuse.path || ''}`.trim();
  }
  if (refuse.kind === 'unresolved') return `unresolved ${refuse.path || ''}`.trim();
  return String(refuse.reason || refuse.path || 'launch-refused');
}

function unresolvedBind(p, extra) {
  if (!p) return { kind: 'unresolved', path: p || '', ...extra };
  if (!fs.existsSync(p)) return { kind: 'unresolved', path: p, ...extra };
  try {
    fs.realpathSync(p);
    return null;
  } catch {
    return { kind: 'unresolved', path: p, ...extra };
  }
}

function conflictBind(sources) {
  const list = sources || [];
  for (let i = 0; i < list.length; i++) {
    for (let j = i + 1; j < list.length; j++) {
      const a = list[i];
      const b = list[j];
      if (!a || !b || a.access === b.access) continue;
      if (!contains(a.path, b.path) && !contains(b.path, a.path)) continue;
      return { kind: 'conflict', path: a.path, pair: [a, b] };
    }
  }
  return null;
}

function rwPathRefusal(seatPath, entry) {
  const root = seatPath.workspaceRoot;
  const goals = path.join(root, '.rbtv', 'goals');
  if (!entry) return 'empty entry';
  if (path.isAbsolute(entry)) return 'absolute path — entries are workspace-relative';
  const target = path.resolve(root, entry);
  if (!contains(root, target) || target === root) return `resolves outside the workspace root: ${target}`;
  const walled = goalsTreeRefusal(goals, target);
  if (walled) return walled;
  if (!fs.existsSync(target)) return `does not exist (never created from here): ${target}`;
  // (+) — the same two bounds, asked of where the path LANDS. `target` exists (rule 4 passed), so
  // its realpath resolves; a root that does not resolve is a workspace this seat cannot be in.
  let realRoot = null;
  let realTarget = null;
  try { realRoot = fs.realpathSync(root); realTarget = fs.realpathSync(target); } catch { realRoot = null; }
  if (!realRoot || !contains(realRoot, realTarget) || realTarget === realRoot) {
    return `RESOLVES outside the workspace root — a segment on this path is a symlink out of it: ${target}`;
  }
  const realGoals = (() => { try { return fs.realpathSync(goals); } catch { return null; } })();
  const landed = realGoals ? goalsTreeRefusal(realGoals, realTarget) : null;
  if (landed) return `RESOLVES through a symlink onto a walled surface of ${goals} — ${landed}`;
  return null;
}

function resolveRwPathGrants(seatPath, log) {
  const grants = [];
  for (const entry of seatDeclaresList(seatPath.seatDir, 'rw-paths')) {
    const reason = rwPathRefusal(seatPath, entry);
    if (reason) {
      log('warn', `rw-paths entry REFUSED: ${reason}`, { seat: seatPath.seat, seatDir: seatPath.seatDir, entry });
      const err = new Error(`rw-paths launch-refused: ${reason}`);
      err.code = 'E_LAUNCH_REFUSED';
      err.refuse = unresolvedBind(path.isAbsolute(entry) ? entry : path.resolve(seatPath.workspaceRoot, entry), { reason, source: 'rw-paths' })
        || { kind: 'unresolved', path: entry, reason, source: 'rw-paths' };
      throw err;
    }
    grants.push({ rwPath: path.resolve(seatPath.workspaceRoot, entry) });
  }
  return grants;
}

module.exports = {
  seatDeclaresList,
  rwPathRefusal,
  resolveRwPathGrants,
  conflictBind,
  unresolvedBind,
  reasonFrom,
};
