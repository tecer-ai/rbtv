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
// The ONE declaration reader for every seat-declared grant class, AND the spawner's own two
// workspace rw-grant resolver (`rw-paths` frontmatter) — shared via `seat-grants.js` under ruling
// D2 (2026-08-19). A second parse of seat.md frontmatter would be a second definition of what
// "granted" means, and this gate must reason about exactly the grant the spawner will compose.
// Its former sibling, `coordination/permission-edits.csv` (W3), is GONE ([T2-R12, T1-R9],
// 2026-08-24): the grant store is deleted, owner auth is an answer to a live ask.
const {
  seatDeclaresList, resolveRwPathGrants,
} = require('../server/spawn/seat-grants');

// A backticked token that looks like a path: contains a `/` and carries an extension. Verbatim
// from `edge-runner-job.py#_PATHISH`, the reader of the `<io-spec> ## Outputs` grammar that dies
// with that file — a MOVE, not a second reader.
const PATHISH = /`([^`\s]*\/[^`\s]*\.[A-Za-z0-9]{1,6})`/g;

// D3 (outputs-unify, 2026-08-18): THE SHARED DECLARED-OUTPUTS RESOLVER — the io-spec
// `## Outputs` block is the ONE declared-outputs surface, and this parse is its JS half.
// `team-kit/coord.py#iospec_outputs` is the Python half (seed computation + done-contract
// grading read it); the two are TWO PARSERS OF ONE GRAMMAR — a cross-language subprocess call
// was refused because coord.py's runtime path (probes, caged runs) carries no node — held
// equivalent by `team-kit/outputs-resolver-fixtures.json`, exercised by BOTH sides' scheduled
// checks (`engine/probes/probe-outputs-resolver.js`; coord.py selftest). Change the grammar in
// both files and the fixtures in the same commit, or one side's check goes red.
//
// `declared` is whether an `## Outputs` section EXISTS inside an `<io-spec>` block — carried
// separately from the tokens because a PROSE section yielding zero tokens is its own loud
// condition on the grading side (`outputs-undeclarable`), and a resolver that collapsed the two
// would rebuild the silent `none-declared` this ruling retires. This gate itself needs only the
// tokens: zero tokens is zero admission questions either way.
// D36 (2026-08-20): the typed NON-FILE output. A bullet whose SCHEMA opens `chat` declares a
// product that is CONVERSATION and therefore has no path to check — a DECLARATION, not an
// absence. THIS gate is unchanged by it (zero path tokens is zero admission questions either
// way); it is reported so the shared fixture set can hold both halves to one grammar, because
// coord.py's checkout gate and materialize's zero-token check DO branch on it.
// ⚠ SCHEMA POSITION ONLY — the word `chat` appears in ordinary Outputs prose ("...posted to the
// chat bridge") and matching it loose would exempt real file producers. Mirror of
// `team-kit/coord.py#_IOSPEC_CHAT`.
const CHAT_SCHEMA = /^[ \t]*[-*][ \t]*\**Schema:?\**:?[ \t]*`?chat`?\b/m;

function parseDeclaredOutputs(text) {
  const block = /<io-spec\b[\s\S]*?<\/io-spec>/.exec(text || '');
  if (!block) return { declared: false, tokens: [], chat: false };
  const section = /##[ \t]*Outputs[ \t]*([\s\S]*?)(?=\n##[ \t]|$)/.exec(block[0]);
  if (!section) return { declared: false, tokens: [], chat: false };
  return {
    declared: true,
    tokens: [...section[1].matchAll(PATHISH)].map((m) => m[1]),
    chat: CHAT_SCHEMA.test(section[1]),
  };
}

// THE DISTINCT-SUCCESSOR OCCUPANT. "Readable by a successor" is the SAME composition asked with a
// different occupant, not a second table. The space is deliberate: a seat name can never contain
// one, so this can never collide with a real seat (`cagespec.PEER`'s own sentinel).
const PEER_SEAT = ' peer';

// `[tokens]` declared by this seat, or `[]` when it declares none. Three absences, none of them a
// pass and none of them a refusal: no seat.md, no `<io-spec>` block, no `## Outputs` section.
function declaredOutputs(goalFolder, seat) {
  let text;
  try { text = fs.readFileSync(path.join(goalFolder, 'seats', seat, 'seat.md'), 'utf8'); } catch { return []; }
  return parseDeclaredOutputs(text).tokens;
}

// The cage this occupant composes for this goal — the REAL composer, over the LIVE template.
// `grants` carries the seat's own `goal-writes` items plus (D2, 2026-08-19) the resolved
// WORKSPACE rw grants in `extraGrants` — `rw-paths` frontmatter entries, resolved by the
// spawner's own resolver. The workspace grants can never change a verdict about a path INSIDE
// the goal folder (the resolver refuses any entry overlapping `.rbtv/goals`); they exist to decide the
// workspace-grammar tokens below. Every remaining grant class still composes outside the goal
// folder by construction (worktrees, git plumbing, harness credentials, `~/.local/bin`, the tmux
// socket dir), or re-covers it identically read-only (`read-root`). A `{grant:…}` entry with no
// matching grant composes to nothing, which is the composer's own rule.
function cageFor({ seatBinds, goalDir, seatDir, goalWrites = [], extraGrants = [] }) {
  return composeSeatCage({
    seatBinds,
    values: { workdir: seatDir, seatDir, goalDir },
    grants: [...goalWrites.map((item) => ({ goalWrite: path.resolve(goalDir, item) })), ...extraGrants],
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

// D2 (2026-08-19): THE WORKSPACE GRAMMAR. Planning legitimately mints seats whose deliverable IS
// a workspace mirror component (`.rbtv/mirror/…`), declared workspace-relative in `## Outputs`.
// Resolved goal-relative such a token dodged the containment refusal (no leading `..`), landed
// under `<goalDir>/.rbtv/…` and was refused `producer-cannot-write` quoting the goal ro-bind — a
// permanent, misdiagnosed refusal loop no grant could flip (G-owner-console-0818-2030,
// `audio-component-smith`). A token SPEAKS THE WORKSPACE GRAMMAR when its FIRST segment names
// something that exists at the workspace root and not inside the goal folder — cheap, and exactly
// the shape that separates `.rbtv/mirror/…` from `coordination/…`/`seats/…`. Undecidable shapes
// (`.`/`..`, a first segment existing in neither place or in both) keep the goal-relative
// reading, whose refusals already fail closed.
function speaksWorkspaceGrammar(token, goalDir, workspaceRoot) {
  const first = String(token).split('/')[0];
  if (!first || first === '.' || first === '..') return false;
  return fs.existsSync(path.join(workspaceRoot, first)) && !fs.existsSync(path.join(goalDir, first));
}

// `null` to admit, else the refusal text. `successorReads` is `yes` | `no` (anything else is
// treated as undecided, which refuses wherever it decides). `workspaceRoot` is THREADED from the
// caller chain (seeding reads the composition root's resolution off `heartStore.config`) — this
// module never resolves it itself; absent, workspace-grammar tokens keep the goal-relative
// reading, which is the pre-D2 behaviour.
function admitDeclaredOutputs({ seatBinds, goalFolder, seat, successorReads = 'no', workspaceRoot = null }) {
  if (!Array.isArray(seatBinds) || seatBinds.length === 0) return null;   // uncaged: not refused
  const goalDir = path.resolve(goalFolder);
  const seatDir = path.join(goalDir, 'seats', seat);
  const tokens = declaredOutputs(goalDir, seat);
  if (!tokens.length) return null;

  let produced;
  let peer;
  try {
    // The workspace rw grant — the SAME source, resolved by the SAME function, the spawner
    // composes at launch (`spawn.js#composeCageFor`). Refusals of individual entries are the
    // spawner's launch-time business to log; here a refused entry is simply not a grant.
    const noLog = () => {};
    const grantSeatPath = { workspaceRoot, goalDir, seatDir, seat };
    const wsGrants = workspaceRoot
      ? [...resolveRwPathGrants(grantSeatPath, noLog)]
      : [];
    produced = cageFor({
      seatBinds, goalDir, seatDir,
      goalWrites: seatDeclaresList(seatDir, 'goal-writes'), extraGrants: wsGrants,
    });
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
    if (workspaceRoot && speaksWorkspaceGrammar(token, goalDir, workspaceRoot)) {
      const wsTarget = path.resolve(workspaceRoot, token);
      if (!contains(workspaceRoot, wsTarget) || wsTarget === workspaceRoot) {
        bad.push(`\`${token}\` — undecided: it resolves OUTSIDE the workspace root (${wsTarget})`);
        continue;
      }
      const w = coverVerdict(produced, wsTarget);
      if (w.verdict !== 'writable') {
        bad.push(`\`${token}\` — no-workspace-grant: it names the WORKSPACE path ${wsTarget}, and no workspace `
          + `write grant composes a writable bind over it — no \`rw-paths:\` entry in ${seat}'s seat.md `
          + `frontmatter covers it. Grant one `
          + `and the next seed pass admits it`);
        continue;
      }
      // Admitted, with NO successor-read test on this lane: a workspace path sits OUTSIDE the
      // goal's `seats` tmpfs, persists on disk after the producer exits, and a successor reads it
      // through its own cage's read-root floor or workspace grants — never through the peer
      // composition the goal lane asks about.
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

// ── D5 (seed-gates, 2026-08-19): THE LANE-REACH GATE ──────────────────────────────────────────
//
// The measured failure (G-plan-3-plan-dod-judge-0818-2130, G-canvas-live-prober-0818-1955,
// G-leader-0818-1936): a goal burned two waves and three seats because its DoD judge kept landing
// in a cage where its probe lane could not run (`stools workspaces` → exit 127; `.git` masked).
// The lane requirement was written into a plan, a handoff, a completion message and a seed — and
// NOTHING that admits a launch read any of them. This gate is that reader: the requirement lives
// MACHINE-READABLE in the seat's own io-spec (`## Requires-reach`, the same D3 single-surface
// idiom `## Outputs` uses), and a seat whose composed cage cannot satisfy it is refused at the
// door instead of after a wasted seat.
//
// The grammar, one entry per line, backticked argument (the materializer derives `cli` entries
// from the done-contract's named probe lane; `path` entries are authorable):
//   - cli `<name>`               satisfied when the seat's `exposed-clis:` declares <name>
//   - path `<workspace-relative>` satisfied when the composed cage (goal-writes + the two
//                                 workspace rw-grant classes, the SAME extension D2 taught
//                                 `admitDeclaredOutputs`) covers it readable-or-writable
//
// ⚠ LIMIT, stated honestly: this gate checks REACH — the declaration/bind is PRESENT — never
// BEHAVIOR (`exit 0`). A file masked to /dev/null that is technically readable passes; the D4
// tool-secrets pierce is what fixes that class. And an UNCAGED launch is not refused, exactly as
// `admitDeclaredOutputs` above: D5 ruled the caged gate only.
const REACH_ENTRY = /^\s*[-*]?\s*(cli|path)[ \t]+`([^`]+)`\s*$/;

function parseRequiresReach(text) {
  const block = /<io-spec\b[\s\S]*?<\/io-spec>/.exec(text || '');
  if (!block) return { declared: false, entries: [], malformed: [] };
  const section = /##[ \t]*Requires-reach[ \t]*([\s\S]*?)(?=\n##[ \t]|$)/.exec(block[0]);
  if (!section) return { declared: false, entries: [], malformed: [] };
  const entries = [];
  const malformed = [];
  for (const line of section[1].split('\n')) {
    if (!line.trim() || line.includes('</io-spec>')) continue;
    const m = REACH_ENTRY.exec(line);
    if (m) entries.push({ verb: m[1], arg: m[2] });
    else malformed.push(line.trim());
  }
  return { declared: true, entries, malformed };
}

// `null` to admit, else the refusal text. Fail-closed like everything in this module: a malformed
// entry refuses (a requirement that cannot be read is not a requirement that was met), and a
// `path` entry with no threaded workspace root refuses (an unjudgeable reach never defaults to
// reachable).
function admitLaneReach({ seatBinds, goalFolder, seat, workspaceRoot = null }) {
  if (!Array.isArray(seatBinds) || seatBinds.length === 0) return null;   // uncaged: not refused
  const goalDir = path.resolve(goalFolder);
  const seatDir = path.join(goalDir, 'seats', seat);
  let text;
  try { text = fs.readFileSync(path.join(seatDir, 'seat.md'), 'utf8'); } catch { return null; }
  const { entries, malformed } = parseRequiresReach(text);
  if (!entries.length && !malformed.length) return null;

  const bad = malformed.map((line) => `\`${line}\` — undecided: not a requires-reach entry (the grammar is `
    + '`cli <name>` | `path <workspace-relative>`, argument backticked); an unreadable requirement is never a met one');
  const cliNames = new Set(seatDeclaresList(seatDir, 'exposed-clis')
    .map((e) => (e.indexOf(' ') > 0 ? e.slice(0, e.indexOf(' ')) : e)));
  let produced = null;
  for (const { verb, arg } of entries) {
    if (verb === 'cli') {
      if (!cliNames.has(arg)) {
        bad.push(`\`cli ${arg}\` — no-cli-grant: the lane needs the \`${arg}\` CLI on PATH inside the cage, and `
          + `${seat}'s \`exposed-clis:\` declares ${cliNames.size ? `only [${[...cliNames].join(', ')}]` : 'nothing'}. `
          + 'The materializer writes that block from the seat\'s `exposes: path:` parts — declare the part and re-materialize');
      }
      continue;
    }
    if (!workspaceRoot) {
      bad.push(`\`path ${arg}\` — undecided: no workspace root threaded, so a workspace-relative reach cannot be judged`);
      continue;
    }
    if (path.isAbsolute(arg)) {
      bad.push(`\`path ${arg}\` — undecided: a reach path is WORKSPACE-RELATIVE; an absolute one names a place this gate cannot place`);
      continue;
    }
    const target = path.resolve(workspaceRoot, arg);
    if (!contains(workspaceRoot, target) || target === workspaceRoot) {
      bad.push(`\`path ${arg}\` — undecided: it resolves OUTSIDE the workspace root (${target})`);
      continue;
    }
    if (produced === null) {
      try {
        const noLog = () => {};
        const grantSeatPath = { workspaceRoot, goalDir, seatDir, seat };
        const wsGrants = [...resolveRwPathGrants(grantSeatPath, noLog)];
        produced = cageFor({
          seatBinds, goalDir, seatDir,
          goalWrites: seatDeclaresList(seatDir, 'goal-writes'), extraGrants: wsGrants,
        });
      } catch (err) {
        return `undecided: the live cage template does not compose for this seat (${err.message}). An underivable `
          + 'wall NEVER defaults to reachable — teach `server/spawn/cage.js` the shape, never admit past it.';
      }
    }
    const v = coverVerdict(produced, target);
    if (v.verdict === 'absent') {
      bad.push(`\`path ${arg}\` — lane-cannot-reach: ${target} is ABSENT in ${seat}'s composed cage — no bind covers it. `
        + `Grant it through an \`rw-paths:\` entry in ${seat}'s seat.md frontmatter `
        + 'and the next seed pass admits it');
    }
  }
  if (!bad.length) return null;
  return 'LANE REACH REQUIREMENT NOT SATISFIED BY THE COMPOSED CAGE: ' + bad.join('; ')
    + '. THE RULE: a `## Requires-reach` entry is satisfied iff `cli <name>` is declared in the seat\'s `exposed-clis:` '
    + 'block, and `path <p>` is covered readable-or-writable by the seat\'s composed cage (goal-writes + `rw-paths:`). '
    + 'LIMIT: this gate checks REACH (the bind is present), never BEHAVIOR (`exit 0`) — a '
    + 'masked-but-readable file passes; the D4 tool-secrets pierce is the fix for that class. This launch was refused '
    + 'BEFORE it was queued, because the seat\'s probe lane could not have run once caged; the failure would otherwise '
    + 'have surfaced mid-milestone as a blocked seat and burned the wave.';
}

module.exports = {
  admitDeclaredOutputs, admitLaneReach, declaredOutputs, parseDeclaredOutputs, parseRequiresReach,
  CHAT_SCHEMA,
  cageFor, coverVerdict, PEER_SEAT,
};
