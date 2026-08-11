'use strict';

// engine/cage-admission.js — CAN THIS SEAT WRITE WHAT IT SAYS IT WILL WRITE, ONCE CAGED?
//
// Owner-ruled 2026-08-11, `build/one-readiness-predicate.md` § D5. Ported out of
// `jobs/edge-runner-job.py` STEP 4a as the Python edge-runner retires — and the port is an
// IMPROVEMENT, not a copy (see § THE LIVE DERIVATION below).
//
// WHAT IT REFUSES, AND WHY AT THE DOOR. A seat that launches CAGED writes inside bwrap walls
// composed from `cage.SeatBinds`; everything outside them is read-only or simply absent. A row
// whose `<io-spec> ## Outputs` declares a token in such a place WILL fail on its own first write —
// today at the FAR end, after a launch, as a missing artifact marked against the seat's WORK, when
// the truth is that its DECLARATION named a place it was never able to write. Refused before the
// enqueue it costs one refusal instead of one wasted seat and one misattributed mark. This is what
// refused `elicitator` in the edge-runner's one live fire.
//
// THE RULE, and it is one sentence:
//
//   A declared-output token is ADMISSIBLE iff its subtree is WRITABLE in the producing seat's
//   composed cage AND — where any successor reads it — READABLE in that successor's composed cage.
//   The discriminator is per ROW ("does a successor read it"), never per subtree.
//
// WHERE AN ADMISSIBLE TOKEN LIVES: no successor reads it -> `seats/<self>/…`; a successor reads it
// -> `coordination/<producer>-<artifact>`; `outputs/` is INADMISSIBLE for a caged producer.
//
// ── THE LIVE DERIVATION — the whole reason this is not a transcription ────────────────────────
//
// The Python read `cage-subtree-map.csv`, a snapshot whose own header warned it was stale the
// moment `cage.SeatBinds` changed — and it was: `d-s31-planning-workspace-shared-rw` added the
// `planning/` opening on 2026-08-11 and the table did not know, so the one artifact surface a
// multi-seat phase hands work across read `undecided` and refused. It then grew a Python MIRROR of
// the composer (`team-kit/cagespec.py`) held against the real thing by a cross-language check.
//
// ⚠ NEITHER IS NEEDED IN JAVASCRIPT, AND THAT IS THE POINT: `server/spawn/cage.js` IS the composer.
// This module drives `composeSeatCage` — the same function `spawn.js#composeCageFor` drives on
// every real launch — over the LIVE profile-resolved template, with the seat's real absolute paths.
// No re-rooting, no mirror, no snapshot, and nothing to hold against anything.
//
// ⚠ THE READING IS THE CAGE'S OWN: input order is output order, and the LAST entry covering a path
// decides what that path IS (`cage.js#assertGroundTruthUnwritable`'s reading, and bwrap's own — a
// later argument wins). That is why ground truth needs no list here: `sessions.csv` and `state.csv`
// are carved back read-only immediately after the `goal-writes` line, peer seat folders sit under
// the `seats` tmpfs, and `seat.md` under its own carve. Each answers "not writable" BY POSITION.
//
// ⚠ EVERYTHING UNDERIVABLE REFUSES. An unknown verb, an unknown slot, a grant with no usable value,
// a token that is absolute or climbs out of the goal folder — every one of them throws or resolves
// nowhere, and every one is a REFUSAL rather than an admission. A token that reads admissible on
// paper but is unwritable in fact turns a gap into a green; fail-closed here is load-bearing, and
// it is what makes template GROWTH safe.
//
// ⚠ SCOPED TO CAGED LAUNCHES, deliberately. An UNCAGED profile (no `SeatBinds`) is NOT refused —
// refusing it would silently convert a ruled token-migration deferral into a forced one.

const fs = require('node:fs');
const path = require('node:path');
const { composeSeatCage, specToBwrapFlags, contains, RW_VERBS } = require('../server/spawn/cage');
// The ONE declaration reader for every seat-declared grant class — the spawner's own
// (`spawn.js#seatDeclaresList`). A second parse of seat.md frontmatter would be a second definition
// of what "declared" means, and this gate must reason about the grant the spawner will compose.
const { seatDeclaresList } = require('../server/spawn/spawn');

// A backticked token that looks like a path: contains a `/` and carries an extension. Verbatim
// from `edge-runner-job.py#_PATHISH`, the reader of the `<io-spec> ## Outputs` grammar that dies
// with that file — a MOVE, not a second reader.
const PATHISH = /`([^`\s]*\/[^`\s]*\.[A-Za-z0-9]{1,6})`/g;

// THE DISTINCT-SUCCESSOR OCCUPANT. "Readable by a successor" is the SAME composition asked with a
// different occupant, not a second table. The space is deliberate: a seat name can never contain
// one, so this can never collide with a real seat (`cagespec.PEER`'s own sentinel).
const PEER_SEAT = ' peer';

// `[tokens]` declared by this seat, or `[]` when it declares none. Three absences, none of them a
// pass and none of them a refusal: no seat.md, no `<io-spec>` block, no `## Outputs` section.
function declaredOutputs(goalFolder, seat) {
  let text;
  try { text = fs.readFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'), 'utf8'); } catch { return []; }
  const block = /<io-spec\b[\s\S]*?<\/io-spec>/.exec(text);
  if (!block) return [];
  const section = /##[ \t]*Outputs[ \t]*([\s\S]*?)(?=\n##[ \t]|$)/.exec(block[0]);
  if (!section) return [];
  return [...section[1].matchAll(PATHISH)].map((m) => m[1]);
}

// The cage this occupant composes for this goal — the REAL composer, over the LIVE template.
// `grants` carries the seat's own `goal-writes` items and nothing else: every other grant class
// composes OUTSIDE the goal folder by construction (worktrees, git plumbing, harness credentials,
// `~/.local/bin`, the tmux socket dir), or re-covers it identically read-only (`read-root`), or is
// excluded from the seat's own goal (`goals-write`), or is refused any overlap with `.rbtv/goals`
// (`rw-paths`) — so none of them can change a verdict about a path inside this goal folder. A
// `{grant:…}` entry with no matching grant composes to nothing, which is the composer's own rule.
function cageFor({ seatBinds, goalDir, seatDir, goalWrites = [] }) {
  return composeSeatCage({
    seatBinds,
    values: { workdir: seatDir, seatDir, goalDir },
    grants: goalWrites.map((item) => ({ goalWrite: path.resolve(goalDir, item) })),
  });
}

// `writable` | `readonly` | `absent` — what the caged occupant actually sees at `target`, decided
// by the LAST spec entry covering it. Nothing covering it means nothing bound it (`absent`), and a
// `tmpfs` over an ancestor makes it absent too — which is not writable and not readable.
function coverVerdict(spec, target) {
  let hit = null;
  for (const entry of spec) if (contains(entry.path, target)) hit = entry;
  if (!hit || hit.verb === 'tmpfs') return { verdict: 'absent', entry: hit };
  return { verdict: RW_VERBS.has(hit.verb) ? 'writable' : 'readonly', entry: hit };
}

// The deciding entry as the FLAGS bwrap is actually handed — `specToBwrapFlags`, the same emitter
// the spawn path uses. A refusal that quotes the wall in the wall's own vocabulary needs no second
// document to be read against.
function flagsOf(entry) {
  return entry ? specToBwrapFlags([entry]).join(' ') : 'nothing covers it — the path is ABSENT in this cage';
}

// `null` to admit, else the refusal text. `successorReads` is `yes` | `no` (anything else is
// treated as undecided, which refuses wherever it decides).
function admitDeclaredOutputs({ seatBinds, goalFolder, seat, successorReads = 'no' }) {
  if (!Array.isArray(seatBinds) || seatBinds.length === 0) return null;   // uncaged: not refused
  const goalDir = path.resolve(goalFolder);
  const seatDir = path.join(goalDir, 'seats', seat);
  const tokens = declaredOutputs(goalDir, seat);
  if (!tokens.length) return null;

  let produced;
  let peer;
  try {
    produced = cageFor({ seatBinds, goalDir, seatDir, goalWrites: seatDeclaresList(seatDir, 'goal-writes') });
    peer = cageFor({ seatBinds, goalDir, seatDir: path.join(goalDir, 'seats', PEER_SEAT) });
  } catch (err) {
    return `undecided: the live cage template does not compose for this seat (${err.message}). An underivable `
      + 'wall NEVER defaults to admissible — teach `server/spawn/cage.js` the shape, never admit past it.';
  }

  const bad = [];
  for (const token of tokens) {
    if (path.isAbsolute(token)) {
      bad.push(`\`${token}\` — undecided: a declared output is GOAL-RELATIVE; an absolute token names a place this gate cannot place in the cage`);
      continue;
    }
    const target = path.resolve(goalDir, token);
    if (!contains(goalDir, target) || target === goalDir) {
      bad.push(`\`${token}\` — undecided: it resolves OUTSIDE the seat's own goal folder (${target})`);
      continue;
    }
    const w = coverVerdict(produced, target);
    if (w.verdict !== 'writable') {
      bad.push(`\`${token}\` — producer-cannot-write: ${w.verdict} in ${seat}'s composed cage (deciding entry: ${flagsOf(w.entry)})`);
      continue;
    }
    const r = coverVerdict(peer, target);
    // Readable from a DISTINCT successor's cage settles it for every value of the discriminator,
    // unknown included — so the discriminator is consulted only where it DECIDES.
    if (r.verdict !== 'absent') continue;
    const sr = String(successorReads).trim().toLowerCase();
    if (sr === 'no') continue;
    bad.push(sr === 'yes'
      ? `\`${token}\` — successor-cannot-read: ${seat} may write it, but it is ABSENT from a successor's composed cage `
        + `(peer seat folders sit under the \`seats\` tmpfs), and a successor DOES read this row`
      : `\`${token}\` — undecided: ${seat} may write it but a successor could not read it, so the verdict turns on `
        + `whether a successor reads it — and that discriminator is \`${successorReads}\`, not yes/no`);
  }
  if (!bad.length) return null;
  return 'DECLARED-OUTPUT TOKEN NOT ADMISSIBLE FOR A CAGED LAUNCH: ' + bad.join('; ')
    + '. THE RULE: a declared-output token is admissible iff its subtree is WRITABLE in the producing seat\'s composed '
    + 'cage AND — where any successor reads it — READABLE in that successor\'s. WHERE AN ADMISSIBLE TOKEN LIVES: no '
    + 'successor reads it -> `seats/<self>/…`; a successor reads it -> `coordination/<producer>-<artifact>`; `outputs/` '
    + 'is INADMISSIBLE for a caged producer. PROVENANCE: derived on THIS pass by composing the seat\'s cage through '
    + '`server/spawn/cage.js#composeSeatCage` over the profile-resolved `cage.SeatBinds` the daemon itself launches '
    + 'with — not a transcribed snapshot. This launch was refused BEFORE it was queued, because the seat could not have '
    + 'written the token once caged; the failure would otherwise have surfaced at the far end as an absent artifact and '
    + 'been marked against the seat\'s work rather than against its declaration.';
}

module.exports = { admitDeclaredOutputs, declaredOutputs, cageFor, coverVerdict, PEER_SEAT };
