'use strict';

// cast — the launch path: spawn, `cast seat`, `cast resume`.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { SPECS } = require('../catalog');

const { HARNESSES, RESUME_USAGE, SEAT_USAGE, baseArgv, fail, parseArgs, promptArgv, refuseIfDetached, resolveFolder, resolveModel, shortName } = require('./core');
const { claudeSlug, emitHandle, procStart } = require('./handles');
const { opencodeBind } = require('./monitor');
const { opencodeCandidates, opencodeStore } = require('./sessions');

function launch({ harness, modelId, folder, effortWord, effortArgv, system, promptText, headed, dryRun, detached }) {
  if (headed && harness === 'opencode' && effortArgv.length) {
    // measured 2026-08-14: --variant exists only on `opencode run`, not the TUI
    process.stderr.write('cast: note: opencode TUI has no --variant flag — effort ignored in headed mode\n');
    effortWord = null;
    effortArgv = [];
  }

  let argv = baseArgv(harness, modelId, folder, headed);
  let stdinText = promptText;

  // Mint claude's session id instead of resolving it post-hoc: the id names the transcript file
  // exactly, so no folder->session guessing (measured: 373/900 slug dirs hold >1 transcript).
  // codex/opencode have no such flag — their handle carries session: null.
  let session = null;
  if (harness === 'claude' && !headed) {
    session = crypto.randomUUID();
    argv = [...argv, '--session-id', session];
  }

  // ⚑ Uniform descriptor carriage (ignite's `d-uniform-descriptor-carriage`): claude gets a true
  // system-prompt flag; every other harness rides the system text on the first message,
  // ahead of the wake prompt, with the same wrapper text spawn.js composes.
  if (system && harness === 'claude') {
    argv = [...argv, ...(system.file
      ? ['--append-system-prompt-file', system.file]
      : ['--append-system-prompt', system.text])];
  } else if (system) {
    const sysText = system.text ?? fs.readFileSync(system.file, 'utf8');
    stdinText = `${sysText}\n\n---\n\n${system.wrapper}\n\n${promptText ?? ''}`;
  }

  argv = [...argv, ...effortArgv];

  if (headed) {
    // the TUI needs the real terminal on stdin, so the prompt rides argv
    argv = [...argv, ...promptArgv(harness, stdinText)];
    stdinText = null;
  }

  if (dryRun) {
    process.stdout.write(`${JSON.stringify({
      argv,
      cwd: folder,
      stdin_preview: stdinText === null ? null : stdinText.slice(0, 200),
      effort_word: effortWord,
      headed,
    })}\n`);
    process.exit(0);
  }

  refuseIfDetached(detached);

  const t0 = Date.now();
  emitHandle({
    pid: process.pid,
    start: procStart(process.pid),
    harness,
    model: shortName(harness, modelId),
    session,
    folder,
    transcript: session
      ? path.join(os.homedir(), '.claude', 'projects', claudeSlug(folder), `${session}.jsonl`)
      : null,
    t0,
  });

  if (harness === 'opencode' && !headed) {
    return runOpencodeChecked(argv, { cwd: folder, stdinText, t0,
      bind: () => opencodeBind({ folder, t0 }, new Set()) });
  }

  const [cmd, ...args] = argv;
  const res = spawnSync(cmd, args, stdinText === null
    ? { cwd: folder, stdio: 'inherit' }
    : { cwd: folder, input: stdinText, stdio: ['pipe', 'inherit', 'inherit'] });
  if (res.error) fail(`launch failed: ${res.error.message}`);
  process.exit(res.status === null ? 1 : res.status);
}

// opencode/grok sometimes swallows the run's final message: the child exits 0 with stdout ending
// mid-tool-trace, indistinguishable from a run that did nothing (issue G-owner-console-0819-0010).
// The session store still holds the final assistant message when stdout lost it, so every opencode
// headless run gets stdout tee'd through a capture and reconciled against the store after exit:
// a final message absent from stdout is appended from the store; a run whose store holds NO final
// message exits non-zero with an explicit no-report marker.
function runOpencodeChecked(argv, { cwd, stdinText, t0, bind }) {
  const { spawn } = require('child_process');
  const [cmd, ...args] = argv;
  const child = spawn(cmd, args, {
    cwd,
    stdio: [stdinText === null ? 'inherit' : 'pipe', 'pipe', 'inherit'],
  });
  child.on('error', (e) => fail(`launch failed: ${e.message}`));
  if (stdinText !== null) child.stdin.end(stdinText);
  let captured = '';
  child.stdout.on('data', (d) => { captured += d; process.stdout.write(d); });
  child.on('close', (status) => {
    const code = status === null ? 1 : status;
    const sessionId = bind();
    const final = sessionId ? opencodeFinalMessage(sessionId, t0) : null;
    if (final === null) {
      process.stdout.write('cast: no-report — the opencode session store holds no final assistant'
        + ` message for this run${sessionId ? ` (session ${sessionId})` : ''}\n`);
      process.exit(code || 1);
    }
    if (!captured.includes(final)) {
      process.stdout.write('\ncast: recovered final message from the opencode session store'
        + ` (absent from stdout):\n${final}\n`);
    }
    process.exit(code);
  });
}

// The final report of one run: the newest assistant message born at/after t0 that carries text.
// null = the store holds no final report for this run (an absent/unreadable store included —
// a report cast cannot see is a report the caller does not have).
function opencodeFinalMessage(sessionId, t0) {
  const store = opencodeStore();
  if (!fs.existsSync(store)) return null;
  try {
    const { DatabaseSync } = require('node:sqlite');
    const db = new DatabaseSync(store, { readOnly: true });
    const messages = db.prepare(
      'select id, data from message where session_id = ? and time_created >= ? order by time_created desc',
    ).all(sessionId, t0 - 2000);
    const parts = db.prepare('select data from part where message_id = ? order by time_created');
    for (const m of messages) {
      let d;
      try { d = JSON.parse(m.data); } catch { continue; }
      if (d.role !== 'assistant') continue;
      // stdout prints each text part trimmed, so trim-per-part keeps includes() comparable
      const text = parts.all(m.id).map((p) => {
        try { const pd = JSON.parse(p.data); return pd.type === 'text' ? pd.text.trim() : ''; } catch { return ''; }
      }).filter(Boolean).join('\n');
      if (text) return text;
    }
    return null;
  } catch (e) {
    process.stderr.write(`cast: opencode session store unreadable (${e.message})\n`);
    return null;
  }
}

// resume `last` binds post-hoc: the folder session this turn actually touched (newest
// time_updated at/after t0) — opencode's own -c picks "the newest", so cast cannot know
// the id up front the way an explicit -s resume does.
function opencodeTouched(folder, t0) {
  const rows = opencodeCandidates(folder).filter((r) => r.time_updated >= t0 - 2000);
  rows.sort((a, b) => b.time_updated - a.time_updated);
  return rows.length ? rows[0].id : null;
}

// Minimal frontmatter scan — the three scalar keys seat.md carries that cast needs.
// ponytail: line-regex parser, swap in a YAML lib if seat frontmatter ever nests these keys.
function seatFrontmatter(text) {
  const out = {};
  const lines = text.split('\n');
  if (lines[0].trim() !== '---') return out;
  for (let i = 1; i < lines.length && lines[i].trim() !== '---'; i++) {
    const m = lines[i].match(/^(harness|model|effort):\s*(\S+)\s*$/);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

const SEAT_WRAPPER = "The descriptor above is this seat's binding instruction set for this whole "
  + 'sitting — it rides this first message because your harness carries no system prompt. '
  + 'Do not re-read seat.md; you have just read it. The message that fired this sitting follows:';
const SYSTEM_WRAPPER = 'The text above is your system-prompt directive for this run — it rides this '
  + "first message because your harness carries no system prompt. The user's message follows:";

// cast seat: the seat.md frontmatter says which harness/model/effort to launch with, and its
// body is the system prompt; -p/-f is an optional wake message on top of it.
function runSeat(rawArgv) {
  const { dryRun, headed, detached, promptText, system, positional } = parseArgs(rawArgv, SEAT_USAGE, false);
  if (system) fail('refused: seat mode reads its system prompt from seat.md — drop -s/-S');
  if (positional.length > 1) fail(`usage: ${SEAT_USAGE}\nrun cast -h for full help`);
  const folder = resolveFolder(positional[0] ?? '.');

  const descriptor = path.join(folder, 'seat.md');
  if (!fs.existsSync(descriptor)) fail(`no seat.md in ${folder}`);
  const fm = seatFrontmatter(fs.readFileSync(descriptor, 'utf8'));
  for (const key of ['harness', 'model']) {
    if (!fm[key]) fail(`seat.md frontmatter is missing '${key}': ${descriptor}`);
  }

  const { modelId, spec } = resolveModel(fm.harness, fm.model);

  let effortWord = null;
  let effortArgv = [];
  const eff = spec.effort;
  if (fm.effort && fm.effort !== 'inert' && eff && !eff.inert) {
    if (!eff.rungs.includes(fm.effort)) {
      fail(`refused: effort '${fm.effort}' is not a rung of ${fm.model}\nknown rungs: ${eff.rungs.join(', ')}`);
    }
    effortWord = fm.effort;
    effortArgv = eff.flag(fm.effort);
  }

  launch({
    harness: fm.harness, modelId, folder, effortWord, effortArgv,
    system: { file: descriptor, wrapper: SEAT_WRAPPER },
    promptText: promptText ?? 'No separate wake message — act per your seat descriptor.',
    headed, dryRun, detached,
  });
}

// cast resume: send one more turn into an existing headless session. `last` = the harness's own
// "most recent session in this folder" affordance, so no id bookkeeping is needed for the common
// case. Permission/sandbox flags are per-invocation, not per-session, so they ride again here.
// codex has no --cd/--sandbox on `exec resume`; cwd comes from spawnSync and sandbox via -c.
function resumeArgv(harness, id) {
  switch (harness) {
    case 'claude': return ['claude', '-p', ...(id === 'last' ? ['--continue'] : ['--resume', id]),
      '--permission-mode', 'bypassPermissions'];
    case 'codex': return ['codex', 'exec', 'resume', ...(id === 'last' ? ['--last'] : [id]),
      '-c', 'sandbox_mode=danger-full-access', '-c', 'approval_policy=never'];
    case 'opencode': return ['opencode', 'run', ...(id === 'last' ? ['-c'] : ['-s', id]), '--auto'];
  }
}

function runResume(rawArgv) {
  const { dryRun, headed, detached, promptText, system, positional } = parseArgs(rawArgv, RESUME_USAGE, true);
  if (headed) fail('refused: resume is headless-only — drop --headed');
  if (system) fail('refused: the resumed session already has its system prompt — drop -s/-S');
  if (positional.length < 2 || positional.length > 3) {
    fail(`usage: ${RESUME_USAGE}\nrun cast -h for full help`);
  }
  const [harness, id, folderArg = '.'] = positional;
  if (!SPECS[harness]) {
    fail(`refused: '${harness}' is not a known harness\nknown: ${HARNESSES.join(', ')}`);
  }
  const argv = resumeArgv(harness, id);
  const folder = resolveFolder(folderArg);

  if (dryRun) {
    process.stdout.write(`${JSON.stringify({
      argv, cwd: folder, stdin_preview: promptText.slice(0, 200),
    })}\n`);
    process.exit(0);
  }
  refuseIfDetached(detached);
  const t0 = Date.now();
  emitHandle({
    pid: process.pid,
    start: procStart(process.pid),
    harness,
    model: 'resume',
    session: id === 'last' ? null : id,
    folder,
    // claude mints its session id at launch, so a bare/seat handle's transcript filename is known
    // up front; a resume reuses an EXISTING session, so the filename is only knowable when the
    // caller named it explicitly — `last` has no id until the harness resolves it itself, the same
    // ceiling `cast sessions` already documents for same-minute launches.
    transcript: harness === 'claude' && id !== 'last'
      ? path.join(os.homedir(), '.claude', 'projects', claudeSlug(folder), `${id}.jsonl`)
      : null,
    t0,
  });
  if (harness === 'opencode') {
    return runOpencodeChecked(argv, { cwd: folder, stdinText: promptText, t0,
      bind: () => (id === 'last' ? opencodeTouched(folder, t0) : id) });
  }
  const [cmd, ...args] = argv;
  const res = spawnSync(cmd, args, { cwd: folder, input: promptText, stdio: ['pipe', 'inherit', 'inherit'] });
  if (res.error) fail(`resume failed: ${res.error.message}`);
  process.exit(res.status === null ? 1 : res.status);
}

module.exports = {
  launch, runOpencodeChecked, opencodeFinalMessage, opencodeTouched,
  seatFrontmatter, SEAT_WRAPPER, SYSTEM_WRAPPER, runSeat,
  resumeArgv, runResume,
};
