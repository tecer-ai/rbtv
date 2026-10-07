'use strict';

// cast — the launch path: spawn, `cast resume`.
// Split out of cast.js 2026-08-20 on the file's own section banners; the code below is
// unchanged from that file. Every composed argv and every stdout surface stayed
// byte-identical across the split (163-invocation corpus, both self-check suites).

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { SPECS } = require('../supported-models');

const { HARNESSES, RESUME_USAGE, baseArgv, codexArgv, fail, parseArgs, promptArgv, refuseIfDetached, resolveFolder, shortName } = require('./core');
const { startFailure } = require('./fallback');
const { claudeSlug, emitHandle, procStart, stdoutPath } = require('./handles');
const { loadOptional } = require('./optional');
const { spawnable } = require('./win-exec');
const { opencodeCandidates, opencodeStore } = require('./sessions');

const { module: monitorMod } = loadOptional('monitor');
const DEADLINE_MS = monitorMod ? monitorMod.DEADLINE_MS : 4 * 60 * 60 * 1000;
const { module: providerLimitMod } = loadOptional('provider-limit');

function exitDeadline() {
  process.stderr.write(`cast: deadline — job exceeded ${Math.round(DEADLINE_MS / 1000)}s wall clock\n`);
  process.exit(1);
}

// Node's spawn `cwd` chdirs the child but leaves the inherited PWD env var alone.
// OpenCode records its project directory from PWD, not from the chdir, so a caller
// running in another folder would bind the session to the caller's directory.
// PWD is set last so a request env cannot put it back.
function launchEnv(folder, extra) {
  return { ...process.env, ...(extra || {}), PWD: folder };
}

// How one harness run ended: `error` when the harness could not be started, else its exit `code`
// and the `signal` that ended it if one did. `note` is text the run owes its caller's stdout.
// `ended` closes cast on it, the way every run without a fallback ends.
function ended(failLabel) {
  return (out) => {
    if (out.note) process.stdout.write(out.note);
    if (out.error) fail(`${failLabel}: ${out.error}`);
    process.exit(out.code);
  };
}

function spawnWithDeadline(cmd, args, opts) {
  const win = spawnable(cmd, args);
  const spawned = { ...opts, ...win.opts, timeout: DEADLINE_MS, killSignal: 'SIGTERM' };
  if (opts.cwd) spawned.env = launchEnv(opts.cwd, opts.env);
  const res = spawnSync(win.cmd, win.args, spawned);
  if (res.error && res.error.code === 'ETIMEDOUT') exitDeadline();
  if (res.error) return { error: res.error.message };
  return { code: res.status === null ? 1 : res.status, signal: res.signal };
}

// One launch. `fallback`, when given, returns the launch values of the model's fallback
// (lib/fallback.js `fallbackOf`); a headless launch that fails to start runs it once, in the same
// folder with the same task.
function launch({ harness, modelId, effortWord, effortArgv, fallback, ...run }) {
  attempt({ harness, modelId, effortWord, effortArgv, ...run }, (out) => {
    const next = fallback && !run.headed && startFailure(out) ? fallback() : null;
    if (!next) return ended('launch failed')(out);
    const how = out.error || `exit ${out.code} after ${Math.round(out.elapsedMs / 1000)}s`;
    const failed = `cast: ${harness} ${shortName(harness, modelId)} did not start (${how})`;
    if (next.problem) {
      process.stderr.write(`${failed}, and its fallback cannot be launched: ${next.problem}\n`);
      return ended('launch failed')(out);
    }
    // The failed run's closing note goes to stderr: stdout is the report of the run that follows.
    if (out.note) process.stderr.write(out.note);
    process.stderr.write(`${failed}; launching its fallback ${next.harness} ${next.model}\n`);
    return attempt({ ...run, ...next }, ended('launch failed'));
  });
}

// Composes one harness run and starts it; `done` receives how it ended, with `elapsedMs`.
function attempt({ harness, modelId, folder, effortWord, effortArgv, system, promptText, headed, dryRun, detached, agentHome }, done) {
  if (headed && harness === 'opencode' && effortArgv.length) {
    // measured 2026-08-14: --variant exists only on `opencode run`, not the TUI
    process.stderr.write('cast: note: opencode TUI has no --variant flag — effort ignored in headed mode\n');
    effortWord = null;
    effortArgv = [];
  }

  let argv = baseArgv(harness, modelId, folder, headed);
  let stdinText = promptText;
  // An rbtv agent's folder is announced to the harness's process as RBTV_AGENT_HOME.
  const agentEnv = agentHome ? { RBTV_AGENT_HOME: agentHome } : null;

  // Mint claude's session id instead of resolving it post-hoc: the id names the transcript file
  // exactly, so no folder->session guessing (measured: 373/900 slug dirs hold >1 transcript).
  // codex/opencode have no such flag — their handle carries session: null.
  let session = null;
  if (harness === 'claude' && !headed) {
    session = crypto.randomUUID();
    argv = [...argv, '--session-id', session];
  }

  // opencode has no session-id flag, but `--title` is recorded verbatim on the session row, so a
  // per-launch unique title is the identity cast otherwise lacks (measured 2026-08-31: two runs
  // 32ms apart under one project root each kept their own title, and a completed run was never
  // retitled). Without it a run was identified by nearest time_created inside its project root —
  // and opencode stores the RESOLVED PROJECT ROOT, not the launch cwd, so every concurrent seat
  // under one repo matched the same window and the "recovered final message" tail could carry a
  // SIBLING seat's report (measured 2026-08-31, ~20 concurrent seats: one seat's whole 76-line
  // report was appended to another's).
  let tag = null;
  if (harness === 'opencode' && !headed) {
    tag = `${path.basename(folder)} [cast:${crypto.randomBytes(4).toString('hex')}]`;
    argv = [...argv, '--title', tag];
  }

  // Claude gets a true system-prompt flag and Codex its developer instructions; OpenCode has no such
  // channel, so its system text rides the first message, ahead of the wake prompt, with the
  // descriptor wrapper text below.
  if (system && harness === 'claude') {
    argv = [...argv, ...(system.file
      ? ['--append-system-prompt-file', system.file]
      : ['--append-system-prompt', system.text])];
  } else if (system && harness === 'codex') {
    const sysText = system.text ?? fs.readFileSync(system.file, 'utf8');
    argv = [...argv, '-c', `developer_instructions=${JSON.stringify(sysText)}`];
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
      ...agentEnv,
    })}\n`);
    process.exit(0);
  }

  refuseIfDetached(detached);

  const t0 = Date.now();
  emitHandle({
    pid: process.pid,
    start: procStart(process.pid),
    out: stdoutPath(),
    harness,
    model: shortName(harness, modelId),
    session,
    tag,
    folder,
    transcript: session
      ? path.join(os.homedir(), '.claude', 'projects', claudeSlug(folder), `${session}.jsonl`)
      : null,
    t0,
  });

  const finish = (out) => done({ ...out, elapsedMs: Date.now() - t0 });
  if (harness === 'opencode' && !headed) {
    return runOpencodeChecked(argv, { cwd: folder, env: agentEnv, stdinText, t0,
      model: shortName(harness, modelId),
      bind: () => opencodeTagged(folder, tag) }, finish);
  }

  const [cmd, ...args] = argv;
  return finish(spawnWithDeadline(cmd, args, stdinText === null
    ? { cwd: folder, env: agentEnv, stdio: 'inherit' }
    : { cwd: folder, env: agentEnv, input: stdinText, stdio: ['pipe', 'inherit', 'inherit'] }));
}

// opencode/grok sometimes swallows the run's final message: the child exits 0 with stdout ending
// mid-tool-trace, indistinguishable from a run that did nothing (issue G-owner-console-0819-0010).
// The session store still holds the final assistant message when stdout lost it, so every opencode
// headless run gets stdout tee'd through a capture and reconciled against the store after exit:
// a final message absent from stdout is appended from the store; a run whose store holds NO final
// message exits non-zero with an explicit no-report marker. `done` receives how the run ended.
function runOpencodeChecked(argv, { cwd, env, stdinText, t0, bind, model }, done) {
  const { spawn } = require('child_process');
  const [cmd, ...args] = argv;
  const win = spawnable(cmd, args);
  const child = spawn(win.cmd, win.args, {
    cwd,
    env: launchEnv(cwd, env),
    stdio: [stdinText === null ? 'inherit' : 'pipe', 'pipe', 'inherit'],
    ...win.opts,
  });
  // A harness that cannot be started emits `error` and then `close`: the first one ends the run.
  let over = false;
  const end = (out) => {
    if (over) return;
    over = true;
    done(out);
  };
  child.on('error', (e) => end({ error: e.message }));
  if (stdinText !== null) child.stdin.end(stdinText);
  let captured = '';
  let timedOut = false;
  const timer = setTimeout(() => { timedOut = true; child.kill('SIGTERM'); }, DEADLINE_MS);
  child.stdout.on('data', (d) => { captured += d; process.stdout.write(d); });
  child.on('close', (status, signal) => {
    clearTimeout(timer);
    if (timedOut) exitDeadline();
    if (over) return;
    const code = status === null ? 1 : status;
    const sessionId = bind();
    const final = sessionId ? opencodeFinalMessage(sessionId, t0) : null;
    if (final === null) {
      const hit = providerLimitMod
        && providerLimitMod.detectProviderLimit({ harness: 'opencode', model, t0, text: captured });
      const note = hit ? `${providerLimitMod.formatReason(hit)}\n`
        : 'cast: no-report — the opencode session store holds no final assistant'
          + ` message for this run${sessionId ? ` (session ${sessionId})` : ''}\n`;
      return end({ code: code || 1, signal, note });
    }
    const note = captured.includes(final) ? null
      : `\ncast: recovered final message from the opencode session store (absent from stdout):\n${final}\n`;
    return end({ code, signal, note });
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

// A launch binds to the session carrying its own title tag — an exact identity, never a guess.
// null = cast cannot see its own session, so the caller reports no-report (or a provider limit)
// rather than recovering whatever else is in the store: a missing report is recoverable, a
// sibling's report read as this seat's is not.
function opencodeTagged(folder, tag) {
  const row = opencodeCandidates(folder).find((r) => r.title === tag);
  return row ? row.id : null;
}

// resume `last` binds post-hoc: the folder session this turn actually touched (newest
// time_updated at/after t0) — opencode's own -c picks "the newest", so cast cannot know
// the id up front the way an explicit -s resume does.
function opencodeTouched(folder, t0) {
  const rows = opencodeCandidates(folder).filter((r) => r.time_updated >= t0 - 2000);
  rows.sort((a, b) => b.time_updated - a.time_updated);
  return rows.length ? rows[0].id : null;
}

const SYSTEM_WRAPPER = 'The text above is your system-prompt directive for this run — it rides this '
  + "first message because your harness carries no system prompt. The user's message follows:";

// cast resume: send one more turn into an existing headless session. `last` = the harness's own
// "most recent session in this folder" affordance, so no id bookkeeping is needed for the common
// case. Permission/sandbox flags are per-invocation, not per-session, so they ride again here.
// codex's cwd comes from spawnSync (see codexArgv).
function resumeArgv(harness, id) {
  switch (harness) {
    case 'claude': return ['claude', '-p', ...(id === 'last' ? ['--continue'] : ['--resume', id]),
      '--permission-mode', 'bypassPermissions'];
    case 'codex': return codexArgv({ resume: id === 'last' ? '--last' : id });
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
    out: stdoutPath(),
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
    return runOpencodeChecked(argv, { cwd: folder, stdinText: promptText, t0, model: 'resume',
      bind: () => (id === 'last' ? opencodeTouched(folder, t0) : id) }, ended('launch failed'));
  }
  const [cmd, ...args] = argv;
  return ended('resume failed')(spawnWithDeadline(cmd, args, { cwd: folder, input: promptText,
    stdio: ['pipe', 'inherit', 'inherit'] }));
}

module.exports = {
  launch, launchEnv, runOpencodeChecked, opencodeFinalMessage, opencodeTagged, opencodeTouched,
  SYSTEM_WRAPPER,
  resumeArgv, runResume,
};
