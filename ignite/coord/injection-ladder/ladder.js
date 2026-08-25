'use strict';

// THE per-harness injection ladder — the ONE copy of "which method drives each harness".
//
// Task 7.45. Registry: CMP-9 (`sd-graph show CMP-9`), decisions.md#d-injection-ladder-shared,
// decisions.md#d-profile-source-unification.
//
// CMP-9 § Interface fixes this module's whole contract, and every line below is bounded by it:
//   (2) it answers ONE question — the METHOD. Given a harness, which injection rung is available
//       and preferred. It NEVER answers what the command line is; that is the shared launch-profile
//       resolver's answer (`ignite/launch-profiles/`, task 7.42, DEC-1 § Shared profile source).
//       The two are consumed together: the caller names a profile and walks this ladder for that
//       profile's harness.
//   (3) the rungs' concrete surfaces are OWNED ELSEWHERE and cited, never restated: keystroke is
//       `tmux send-keys` into the seat's pane (CMP-19 § Interface (2)); headless is the harness's
//       own one-shot invocation; hooks reaches the harness through its `harness config`.
//   ( ) "it exposes no command, holds no state, spawns nothing, and WRITES nothing." That last
//       clause is why `hooksConfigFor()` below returns a DESCRIPTOR of files and performs no I/O —
//       the daemon adapter does the writing (see server/spawn/harness-config.js).
//
// This module requires NOTHING under `server/` and nothing outside node builtins, which is what
// makes the no-daemon lanes able to read it without keeping a private second copy — the PRIN-11
// drift the 2026-07-25 re-scope removed by dropping CMP-9's `uses → server` edge.

const path = require('node:path');
const { LadderError, E_UNKNOWN_HARNESS, E_NO_RUNG_AVAILABLE, E_UNKNOWN_RUNG } = require('./errors');

// ── The rung vocabulary, in ladder order (CMP-9 § layout) ────────────────────────────────────
// Ordered BEST-FIRST. The order is the ladder; a consumer never picks a rung, it walks.
const RUNGS = Object.freeze(['headless', 'hooks', 'keystroke']);

// A rung's APPLICABILITY is a property of the rung, not of the harness — stated once here so no
// per-harness entry below has to repeat it.
//   launch — starting a new session. `headless` and `hooks` are launch-only by construction: a
//            one-shot invocation IS a process start, and a harness reads its config at start.
//   inject — delivering text into an ALREADY-LIVE session. Only `keystroke` can (there must be a
//            live TUI to type into), which is exactly why it is the last resort and not a choice.
const RUNG_PHASES = Object.freeze({
  headless: Object.freeze(['launch']),
  hooks: Object.freeze(['launch']),
  keystroke: Object.freeze(['inject']),
});

// ── The per-harness table ────────────────────────────────────────────────────────────────────
// Every `basis` is a citation to where the fact was MEASURED, never to prose that asserts it.
// A harness absent from this table has no known rungs and raises E_UNKNOWN_HARNESS — the ladder
// does not guess a shape it has not seen driven.
const HARNESSES = Object.freeze({
  claude: Object.freeze({
    binary: 'claude',
    rungs: Object.freeze({
      headless: Object.freeze({
        available: true,
        // Re-launchable: the JSON envelope emits a session id and `--resume <id>` continues it.
        resumable: true,
        basis: 'Historical (dated probe citation, 2026-06 p3-6 HELD): orchestration/models/claude-code-cli/delta.md § invocation — tree retired 2026-08-18; live invocation source is the cast catalog / cast.md',
      }),
      hooks: Object.freeze({
        available: true,
        // The ONLY harness of the three whose local config actually restrains anything.
        enforceable: true,
        basis: 'supervisor/spawn/harness-config.js (D58(4)) — .claude/settings.json permissions.additionalDirectories',
      }),
      keystroke: Object.freeze({
        available: true,
        basis: 'CMP-19 § Interface (2) — tmux send-keys into the seat pane (the daemon pty rung was retired at task 7.29)',
      }),
    }),
  }),

  codex: Object.freeze({
    binary: 'codex',
    rungs: Object.freeze({
      headless: Object.freeze({
        available: true,
        resumable: true,
        // ⚠ The one-shot form is the `exec` SUBCOMMAND, and its help is per-subcommand. G-145's
        // exact shape: `codex exec --help` carries flags `codex --help` does not, so reading the
        // top-level help refuses valid profiles while looking authoritative.
        basis: 'Historical (dated probe citation, CLI 0.137.0 p5-2 smoke): orchestration/models/codex-cli/delta.md § invocation — tree retired 2026-08-18; live invocation source is the cast catalog / cast.md',
      }),
      hooks: Object.freeze({
        available: true,
        // Written for TRANSPARENCY only: the profile runs --sandbox danger-full-access, so codex's
        // own sandbox is off and no local config can restrain its writes.
        enforceable: false,
        basis: 'supervisor/spawn/harness-config.js (D58(4)) — .codex/config.toml, advisory only',
      }),
      keystroke: Object.freeze({
        available: true,
        basis: 'CMP-19 § Interface (2) — tmux send-keys into the seat pane',
      }),
    }),
  }),

  opencode: Object.freeze({
    binary: 'opencode',
    rungs: Object.freeze({
      headless: Object.freeze({
        available: true,
        // ⚠ THE ONE PER-HARNESS DIFFERENCE THAT MAKES THIS A WALK AND NOT A LOOKUP.
        // `opencode run` is ONE-SHOT: the seat executes its prompt and EXITS, so it can never be
        // woken later. A wake aimed at its pane afterwards types into a bare shell. Live-verified
        // (G-13), and the failure it caused was silent: the pre-G-13 form exited 0 having run
        // nothing, so any check that only asserted the flag was present read green.
        resumable: false,
        basis: 'ignite/coord/coord.py harness_command() G-13 note (live-verified on deepseek + glm-5.2)',
      }),
      hooks: Object.freeze({
        available: true,
        enforceable: false,
        // ⚠ opencode STRICT-VALIDATES opencode.json and refuses any unrecognized key — a `_note`
        // key killed every opencode session at startup. So the hooks rung here carries LESS than
        // the other two: the advisory cannot ride in the file the harness parses.
        strictValidates: true,
        basis: 'supervisor/spawn/harness-config.js (POC finding 3) — opencode.json + sidecar advisory',
      }),
      keystroke: Object.freeze({
        available: true,
        basis: 'CMP-19 § Interface (2) — tmux send-keys into the seat pane',
      }),
    }),
  }),

  // kimi — added 2026-08-07, closing this module's README residual 3 ("adding it is the job of
  // whoever first drives kimi through a consumer, WITH A MEASURED BASIS PER RUNG"). It was in the
  // owner-ruled spawn-profile roster while absent here, so `harnessOf` returned null for it and the
  // harness the daemon was actually spawning had no name in the one place that holds harness facts.
  kimi: Object.freeze({
    binary: 'kimi',
    rungs: Object.freeze({
      headless: Object.freeze({
        available: true,
        // Resumable, and NOT by inference: the run prints its own resume line,
        // `To resume this session: kimi -r <uuid>`.
        resumable: true,
        basis: 'measured 2026-08-07, ignite VPS, kimi 1.48.0: `kimi -p "<prompt>"` ran headless and emitted `kimi -r <session-id>`',
      }),
      // ⚑ DECLARED UNAVAILABLE BECAUSE IT WAS NOT MEASURED — not because it was ruled out. kimi
      // takes `--config`/`--config-file` (TOML/JSON, default `~/.kimi/config.toml`), so a hooks
      // rung MAY exist; whether any key there RESTRAINS anything is unknown, and this table's
      // contract is that a rung claim cites where the fact was measured. An unavailable rung is
      // honest and costs nothing here: the walk satisfies every launch case at `headless` above.
      // Whoever measures it fills this in — and `hooksConfigFor` gains a real branch then.
      hooks: Object.freeze({
        available: false,
        basis: 'NOT MEASURED — `kimi --help` shows --config/--config-file, but no restraining key has been verified; the ladder declares rather than guesses',
      }),
      keystroke: Object.freeze({
        available: true,
        // Same citation as the other three: send-keys is a property of tmux and the pane, not of
        // the harness, so this rung is not a per-harness measurement for any of them.
        basis: 'CMP-19 § Interface (2) — tmux send-keys into the seat pane',
      }),
    }),
  }),
});

const KNOWN_HARNESSES = Object.freeze(Object.keys(HARNESSES));

// ── Harness identification ───────────────────────────────────────────────────────────────────
// D23: the harness is identified from the profile's OWN exec argv[0] — reuse the profile's words,
// never mint a parallel registry. sleep/test/bash profiles carry no harness and get no rungs.
// Returns null (never throws) so a null-harness profile stays a normal case, not an error.
function harnessFromBinary(argv0) {
  for (const name of KNOWN_HARNESSES) {
    if (argv0 === HARNESSES[name].binary) return name;
  }
  return null;
}

function harnessOf(profile) {
  const argv0 = profile && profile.exec && profile.exec.argv && profile.exec.argv[0];
  return harnessFromBinary(argv0);
}

function requireKnownHarness(harness) {
  if (!Object.prototype.hasOwnProperty.call(HARNESSES, harness)) {
    throw new LadderError(
      E_UNKNOWN_HARNESS,
      `unknown harness '${harness}' — the ladder holds measured rungs for ${KNOWN_HARNESSES.join('|')} only; ` +
      `it does not guess the shape of a harness it has not seen driven`,
      { harness, known: KNOWN_HARNESSES },
    );
  }
  return HARNESSES[harness];
}

// ── Reading the table ────────────────────────────────────────────────────────────────────────
function rungsFor(harness) {
  return requireKnownHarness(harness).rungs;
}

function rungFor(harness, rung) {
  if (!RUNGS.includes(rung)) {
    throw new LadderError(E_UNKNOWN_RUNG, `unknown rung '${rung}' (known: ${RUNGS.join('|')})`, { rung, known: RUNGS });
  }
  return requireKnownHarness(harness).rungs[rung] || null;
}

// ── THE WALK ─────────────────────────────────────────────────────────────────────────────────
// Best-first over RUNGS. The caller supplies the SITUATION and never the rung — handing this
// function the answer it exists to compute is the `p-green-harness-over-a-broken-mechanism` shape,
// and it would make every check over it vacuous.
//
//   harness           the harness name (from harnessOf / harnessFromBinary)
//   phase             'launch' (start a session) | 'inject' (reach an already-live session)
//   needResumable     the caller must be able to reach this session AGAIN after the first turn.
//                     Refuses opencode's headless rung (one-shot, G-13) — the only place today
//                     where two harnesses at the same phase resolve to different rungs.
//   hostSupports      per-rung host capability, e.g. { keystroke: false } on a host with no
//                     no tmux. Absent keys mean "supported"; a FALSE key removes that rung.
//
// Returns { harness, rung, phase, entry, skipped[] } — `skipped` names every rung the walk passed
// and WHY, so a caller can report the reason rather than only the verdict.
function resolveRung(harness, opts = {}) {
  const entryTable = requireKnownHarness(harness).rungs;
  const phase = opts.phase === undefined ? 'launch' : opts.phase;
  const needResumable = opts.needResumable === true;
  const hostSupports = opts.hostSupports || {};
  const skipped = [];

  for (const rung of RUNGS) {
    const entry = entryTable[rung];
    if (!entry || entry.available !== true) {
      skipped.push({ rung, why: 'harness does not offer this rung' });
      continue;
    }
    if (!RUNG_PHASES[rung].includes(phase)) {
      skipped.push({ rung, why: `rung is ${RUNG_PHASES[rung].join('|')}-only; caller asked for '${phase}'` });
      continue;
    }
    if (hostSupports[rung] === false) {
      skipped.push({ rung, why: 'host does not support this rung' });
      continue;
    }
    // ⚠ `!== true`, NOT `=== false`, and the difference is the whole point. A rung satisfies
    // `needResumable` only by DECLARING that it does. Written as `=== false` it would have fallen
    // through opencode's one-shot headless rung onto `hooks` — and hooks does not make a session
    // reachable again, it only writes a config the harness reads at start. The walk would have
    // returned a confident rung that cannot do the thing the caller asked for.
    if (needResumable && entry.resumable !== true) {
      skipped.push({ rung, why: 'rung does not declare that the session can be reached again' });
      continue;
    }
    return { harness, rung, phase, entry, skipped };
  }

  throw new LadderError(
    E_NO_RUNG_AVAILABLE,
    `no injection rung is available for harness '${harness}' at phase '${phase}': ` +
    skipped.map((s) => `${s.rung} — ${s.why}`).join('; '),
    { harness, phase, skipped },
  );
}

// ── The hooks rung's per-harness surface ─────────────────────────────────────────────────────
// Returns a DESCRIPTOR and performs NO I/O — CMP-9 § Interface: the ladder "WRITES nothing".
// The daemon adapter (server/spawn/harness-config.js) executes the descriptor; the KNOWLEDGE of
// what each harness's config is lives here, which is the whole re-home.
//
// `result` is the exact object the daemon's two call sites already consume ({harness, written,
// enforceable} + the log's `note`); its shape is byte-preserved deliberately, so this re-home
// changes where the knowledge lives and nothing a consumer observes.
function hooksConfigFor(harness, { sessionDir, editablePaths = [] } = {}) {
  if (harness === null || harness === undefined) {
    return { harness: null, dirs: [], files: [], result: { harness: null, written: null, enforceable: false } };
  }
  requireKnownHarness(harness);

  const roots = Array.from(new Set([sessionDir, ...editablePaths].filter(Boolean)));

  if (harness === 'claude') {
    const dot = path.join(sessionDir, '.claude');
    const p = path.join(dot, 'settings.json');
    return {
      harness,
      dirs: [{ path: dot, mode: 0o700 }],
      files: [{ path: p, content: JSON.stringify({ permissions: { additionalDirectories: editablePaths } }, null, 2) }],
      result: {
        harness: 'claude',
        written: p,
        enforceable: true,
        note: 'Claude Code honours it (advisory); kernel authoritative',
      },
    };
  }

  if (harness === 'codex') {
    const dot = path.join(sessionDir, '.codex');
    const p = path.join(dot, 'config.toml');
    const toml = [
      '# ADVISORY ONLY. This profile runs --sandbox danger-full-access (.git-write erratum);',
      "# codex's own sandbox is OFF. Kernel systemd confinement is the SOLE enforcement.",
      'approval_policy = "never"',
      `# kernel-enforced editable roots: ${roots.join(', ')}`,
      '',
    ].join('\n');
    return {
      harness,
      dirs: [{ path: dot, mode: 0o700 }],
      files: [{ path: p, content: toml }],
      result: {
        harness: 'codex',
        written: p,
        enforceable: false,
        note: 'danger-full-access — kernel is sole enforcement',
      },
    };
  }

  // ⚑ A HARNESS WITH NO MEASURED HOOKS RUNG GETS AN EMPTY DESCRIPTOR — the same no-I/O shape as a
  // null harness, and it must be an EXPLICIT branch. Until 2026-08-07 the tail of this function was
  // a bare fallthrough that ASSUMED opencode, so naming any fourth harness in the table above would
  // have written an `opencode.json` into that harness's seat dir — and opencode STRICT-VALIDATES
  // that file, so the contamination would have been a startup kill in whichever direction it landed.
  // The guard is the declared rung, not the harness name: anything whose `hooks` rung is
  // unavailable writes nothing.
  if (!HARNESSES[harness].rungs.hooks.available) {
    return { harness, dirs: [], files: [], result: { harness, written: null, enforceable: false, note: 'no measured hooks rung — nothing written' } };
  }

  // opencode. The advisory MUST NOT ride in the config opencode parses (strictValidates above).
  const p = path.join(sessionDir, 'opencode.json');
  const notePath = path.join(sessionDir, '.ignite-sandbox-note.txt');
  return {
    harness,
    dirs: [],
    files: [
      { path: p, content: JSON.stringify({ $schema: 'https://opencode.ai/config.json' }, null, 2) },
      {
        path: notePath,
        mode: 0o600,
        content:
          'ADVISORY ONLY: opencode has no path-scoped write sandbox (POC finding 3). ' +
          `Kernel-enforced editable roots: ${roots.join(', ')}\n`,
      },
    ],
    result: {
      harness: 'opencode',
      written: p,
      advisoryNote: notePath,
      enforceable: false,
      note: 'no native sandbox — kernel is sole enforcement',
    },
  };
}

module.exports = {
  RUNGS,
  RUNG_PHASES,
  HARNESSES,
  KNOWN_HARNESSES,
  harnessOf,
  harnessFromBinary,
  rungsFor,
  rungFor,
  resolveRung,
  hooksConfigFor,
};
