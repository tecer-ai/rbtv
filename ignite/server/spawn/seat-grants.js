'use strict';

// server/spawn/seat-grants.js — THE SEAT-DECLARED GRANT RESOLVERS, shared between the two doors
// that must agree about them (task 7 · ruling D2, 2026-08-19).
//
// Extracted VERBATIM from spawn.js so `engine/cage-admission.js` — the pre-enqueue admission
// gate — composes admissibility from the SAME grant classes the spawner composes walls from.
// Before this file the gate read `goal-writes` only, so a widen recorded in
// `coordination/permission-edits.csv` (or a frontmatter `rw-paths:` entry) changed the real cage
// while the gate kept refusing off a composition that could not see it — the measured
// `audio-component-smith` permanent refusal loop (G-owner-console-0818-2030). One resolver,
// imported by both, is what makes that disagreement structurally impossible; a copy would be a
// second definition and the same drift with extra steps.

const fs = require('node:fs');
const path = require('node:path');
const { contains } = require('./cage');
const { resolvesInsideGoalsRoot } = require('../heart/argv-template');

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
// The FOUR REFUSAL RULES, in ONE function: the reason string when `entry` may not be granted
// read-write to this seat, `null` when it may. Split out at W3 so `permission-edits.csv` — the
// leader's audited second grant source — is judged by the SAME predicate, and so `widen-cage`
// can validate at WRITE time against the identical rules (a silently-dropped grant at launch reads
// as a successful widen in the leader's evidence, adv C--).
function rwPathRefusal(seatPath, entry) {
  const root = seatPath.workspaceRoot;
  const goals = path.join(root, '.rbtv', 'goals');
  if (!entry) return 'empty entry';
  if (path.isAbsolute(entry)) return 'absolute path — entries are workspace-relative';
  const target = path.resolve(root, entry);
  if (!contains(root, target) || target === root) return `resolves outside the workspace root: ${target}`;
  if (contains(goals, target) || contains(target, goals)) {
    return `overlaps ${goals} — the identity/ground-truth surfaces (sessions.csv, seat.md) stay unwritable: ${target}`;
  }
  if (!fs.existsSync(target)) return `does not exist (never created from here): ${target}`;
  const realRoot = (() => { try { return fs.realpathSync(root); } catch { return null; } })();
  const realGoals = (() => { try { return fs.realpathSync(goals); } catch { return null; } })();
  if (!realRoot || !resolvesInsideGoalsRoot(target, realRoot)) {
    return `RESOLVES outside the workspace root — a segment on this path is a symlink out of it: ${target}`;
  }
  if (realGoals && resolvesInsideGoalsRoot(target, realGoals)) {
    return `RESOLVES inside ${goals} through a symlink — the identity/ground-truth surfaces stay unwritable: ${target}`;
  }
  return null;
}

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

// ── W3 · `coordination/permission-edits.csv` — THE LEADER'S AUDITED WIDENINGS ─────────────────
//
// The SECOND rw-grant source, read additively beside `rw-paths` at every launch (ruling D-2).
//
// ⚠ WHY IT IS NOT THE `rw-paths` CELL. That cell lives in `seat.md` frontmatter, which is
// ro-bound in-cage and MATERIALIZER-OWNED: a `materialize-seats.py --repass` or an `add-seat`
// splice re-emits the file and silently reverts whatever the leader wrote. So the widening is
// recorded where it survives — an append-only CSV under the goal's `coordination/` — and THAT FILE
// IS THE MECHANISM as well as the audit log. One artifact, so a wall that was widened and a
// widening that was recorded can never be two different sets.
//
// FAIL-CLOSED PER ROW, same posture as its `rw-paths` sibling and enforced by the SAME function:
// every row goes through `rwPathRefusal` below, so the four refusal rules have one home and the
// verb that writes the file validates against the identical predicate at write time. A malformed
// row is skipped and logged; it never takes a seat offline.
//
// ⚠ IT CANNOT PIERCE THE PRIVATE SCOPE and needs no check here to say so: `composePrivateScope`
// masks every private entry AFTER this whole grant stack, and an opening that RESOLVES inside a
// private entry without naming it throws `E_CAGE_PRIVATE_ALIAS`. The verb refuses such a path at
// write time (`private-scope.js#refusesPath`) so the leader reads the refusal instead of meeting a
// silently masked grant hours later.
const PERMISSION_EDITS_REL = path.join('coordination', 'permission-edits.csv');

function resolvePermissionEditGrants(seatPath, log) {
  const file = path.join(seatPath.goalDir, PERMISSION_EDITS_REL);
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch { return []; }
  const lines = text.split('\n').filter((l) => l.trim().length);
  if (lines.length < 2) return [];
  const { splitRow } = require('../seat-identity/csv');
  const cols = splitRow(lines[0]).map((c) => c.trim());
  const iSeat = cols.indexOf('seat');
  const iPath = cols.indexOf('path');
  if (iSeat < 0 || iPath < 0) {
    log('warn', 'permission-edits.csv REFUSED WHOLE: no `seat`/`path` columns', { file });
    return [];
  }
  const grants = [];
  for (const line of lines.slice(1)) {
    const cells = splitRow(line);
    if ((cells[iSeat] || '').trim() !== seatPath.seat) continue;
    const entry = (cells[iPath] || '').trim();
    const reason = rwPathRefusal(seatPath, entry);
    if (reason) {
      log('warn', `permission-edits row REFUSED: ${reason}`, { seat: seatPath.seat, file, entry });
      continue;
    }
    grants.push({ rwPath: path.resolve(seatPath.workspaceRoot, entry) });
    log('info', 'permission-edits GRANT applied', { seat: seatPath.seat, entry });
  }
  return grants;
}

module.exports = {
  seatDeclaresList,
  rwPathRefusal,
  resolveRwPathGrants,
  resolvePermissionEditGrants,
  PERMISSION_EDITS_REL,
};
