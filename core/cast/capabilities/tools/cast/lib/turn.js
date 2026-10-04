'use strict';

// cast turn — one foreground harness turn whose session id is exact, never "newest in the folder".

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const { CODEX_DOC_LIMIT, lookupModel, shortName, resolveEffortValue } = require('./core');
const { agentBody } = require('./agent');
const { procStart, emitHandle } = require('./handles');
const { launchEnv, opencodeTagged, SYSTEM_WRAPPER } = require('./launch');
const { loadOptional } = require('./optional');
const { spawnable } = require('./win-exec');

const { module: monitorMod } = loadOptional('monitor');
const DEADLINE_MS = monitorMod ? monitorMod.DEADLINE_MS : 4 * 60 * 60 * 1000;

const USAGE = 'cast turn --request FILE --result FILE';

function requestPaths(args) {
  if (args.length !== 4 || args[0] !== '--request' || args[2] !== '--result') {
    throw new Error(`usage: ${USAGE}`);
  }
  return { requestFile: path.resolve(args[1]), resultFile: path.resolve(args[3]) };
}

function existingDir(cwd) {
  if (typeof cwd !== 'string' || !path.isAbsolute(cwd)) {
    throw new Error('cwd must be an existing absolute directory');
  }
  let st;
  try { st = fs.statSync(cwd); } catch {
    throw new Error('cwd must be an existing absolute directory');
  }
  if (!st.isDirectory()) throw new Error('cwd must be an existing absolute directory');
}

function readPrompt(request) {
  const hasPrompt = Object.prototype.hasOwnProperty.call(request, 'prompt');
  const hasFile = Object.prototype.hasOwnProperty.call(request, 'promptFile');
  if (hasPrompt === hasFile) throw new Error('request needs exactly one of prompt or promptFile');
  if (hasFile) {
    if (typeof request.promptFile !== 'string' || !request.promptFile) throw new Error('promptFile must be a path');
    let text;
    try { text = fs.readFileSync(request.promptFile, 'utf8'); } catch (e) {
      throw new Error(`cannot read promptFile: ${e.message}`);
    }
    if (!text.trim()) throw new Error('prompt must be nonempty text');
    return text;
  }
  if (typeof request.prompt !== 'string' || !request.prompt.trim()) throw new Error('prompt must be nonempty text');
  return request.prompt;
}

// The agent's standing prompt (`agent.md`) as the model receives it: its body, without the
// frontmatter. Every harness gets the text, so the file's frontmatter never reaches the model.
function readSystemPrompt(request) {
  if (!Object.prototype.hasOwnProperty.call(request, 'systemPromptFile')) return null;
  const file = request.systemPromptFile;
  if (typeof file !== 'string' || !path.isAbsolute(file)) throw new Error('systemPromptFile must be an absolute path');
  let text;
  try { text = fs.readFileSync(file, 'utf8'); } catch (e) {
    throw new Error(`cannot read systemPromptFile: ${e.message}`);
  }
  const body = agentBody(text);
  if (!body.trim()) throw new Error('systemPromptFile must hold nonempty text');
  return { text: body };
}

// How each harness receives the standing prompt, by its strongest channel:
//   claude   a real system prompt (`--append-system-prompt`), on a NEW session only —
//            the harness keeps it across resume and compaction;
//   codex    developer instructions (`-c developer_instructions=…`), on every turn — a run
//            rebuilds its context, so the prompt is re-passed (on Windows cast starts Codex's
//            script with node directly, so no cmd.exe re-parses the text);
//   opencode the first message of a NEW session (no system-prompt flag exists).
function systemPromptRoute(v) {
  if (!v.systemPrompt) return 'none';
  if (v.harness === 'claude') return v.mode === 'new' ? 'flag' : 'none';
  if (v.harness === 'codex') return 'developer';
  return v.mode === 'new' ? 'message' : 'none';
}

function stdinFor(v) {
  return systemPromptRoute(v) === 'message'
    ? `${v.systemPrompt.text}\n\n---\n\n${SYSTEM_WRAPPER}\n\n${v.prompt}`
    : v.prompt;
}

function readSession(session) {
  if (!session || typeof session !== 'object' || Array.isArray(session)) throw new Error('session must be an object');
  if (session.mode !== 'new' && session.mode !== 'resume') throw new Error('session.mode must be new or resume');
  if (session.mode === 'new') {
    if (session.id !== undefined) throw new Error('session.id is not accepted when mode is new');
    return { mode: 'new', sessionId: null };
  }
  if (typeof session.id !== 'string' || !session.id.trim() || session.id === 'last') {
    throw new Error('session.id must be an exact nonempty id');
  }
  return { mode: 'resume', sessionId: session.id };
}

function readEnv(env) {
  if (env === undefined) return null;
  if (!env || typeof env !== 'object' || Array.isArray(env)) throw new Error('env must be an object of strings');
  const out = {};
  for (const [k, v] of Object.entries(env)) {
    if (typeof v !== 'string') throw new Error(`env.${k} must be a string`);
    out[k] = v;
  }
  return out;
}

function validate(request) {
  if (!request || typeof request !== 'object' || Array.isArray(request)) throw new Error('request must be an object');
  const { modelId, spec } = lookupModel(request.harness, request.model);
  existingDir(request.cwd);
  const prompt = readPrompt(request);
  const systemPrompt = readSystemPrompt(request);
  const { mode, sessionId } = readSession(request.session);
  const env = readEnv(request.env);
  const resolved = resolveEffortValue(spec, request.effort, request.harness, request.model);
  return {
    harness: request.harness,
    modelId,
    model: shortName(request.harness, modelId),
    effort: resolved.word,
    effortArgv: resolved.argv,
    cwd: request.cwd,
    prompt,
    systemPrompt,
    mode,
    sessionId,
    env,
  };
}

function argvFor(v, freshId, tag) {
  const effort = v.effortArgv;
  const route = systemPromptRoute(v);
  switch (v.harness) {
    case 'claude':
      return ['claude', '-p', '--model', v.modelId, '--permission-mode', 'bypassPermissions', ...effort,
        '--output-format', 'json',
        ...(route === 'flag' ? ['--append-system-prompt', v.systemPrompt.text] : []),
        ...(v.mode === 'resume' ? ['--resume', v.sessionId] : ['--session-id', freshId])];
    case 'codex': {
      const developer = route === 'developer'
        ? ['-c', `developer_instructions=${JSON.stringify(v.systemPrompt.text)}`] : [];
      return v.mode === 'resume'
        ? ['codex', 'exec', 'resume', v.sessionId, '-m', v.modelId, ...effort, ...developer,
          '-c', 'sandbox_mode=danger-full-access', '-c', 'approval_policy=never', '--skip-git-repo-check', ...CODEX_DOC_LIMIT, '--json', '-']
        : ['codex', 'exec', '--cd', v.cwd, '-m', v.modelId, '--sandbox', 'danger-full-access',
          '-c', 'approval_policy=never', '--skip-git-repo-check', ...CODEX_DOC_LIMIT, ...effort, ...developer, '--json', '-'];
    }
    case 'opencode':
      return ['opencode', 'run', '-m', v.modelId, '--auto', ...effort,
        ...(v.mode === 'resume' ? ['-s', v.sessionId] : ['--title', tag]), '--format', 'json'];
    default:
      throw new Error(`unknown harness: ${v.harness}`);
  }
}

function noteLine(line, acc) {
  let row;
  try { row = JSON.parse(line); } catch { return acc; }
  if (row && row.type === 'thread.started' && typeof row.thread_id === 'string' && row.thread_id) {
    acc.codexId = row.thread_id;
  }
  if (row && typeof row.session_id === 'string' && row.session_id) acc.claudeId = row.session_id;
  return acc;
}

function parseSessionEvents(stdout) {
  const acc = { codexId: null, claudeId: null };
  for (const line of String(stdout).split('\n')) noteLine(line, acc);
  return acc;
}

function capturePaths(resultFile) {
  return { stdoutPath: `${resultFile}.stdout`, stderrPath: `${resultFile}.stderr` };
}

function blankResult(error) {
  return {
    ok: false, harness: null, model: null, effort: null, sessionId: null,
    exitCode: 1, startedAt: null, endedAt: null, pid: null, pidStart: null,
    stdoutPath: null, stderrPath: null, error,
  };
}

function buildResult(v, o) {
  let sessionId = null;
  let error = o.spawnError || null;
  if (v.harness === 'claude') {
    sessionId = v.mode === 'new' ? o.minted : v.sessionId;
    if (o.claudeId && o.claudeId !== sessionId) {
      error = error || 'session_identity_mismatch';
      sessionId = null;
    }
  } else if (v.harness === 'codex') {
    sessionId = o.codexId;
    if (!sessionId) error = error || 'session_identity_missing';
    else if (v.mode === 'resume' && sessionId !== v.sessionId) error = error || 'session_identity_mismatch';
  } else {
    sessionId = v.mode === 'resume' ? v.sessionId : o.boundId;
    if (!sessionId) error = error || 'session_identity_missing';
  }
  if (v.mode === 'new' && o.pid == null) {
    sessionId = null;
    error = error || o.spawnError || 'spawn_failed';
  }
  if (o.exitCode !== 0) error = error || `harness_exit_${o.exitCode}`;
  const ok = !error && o.exitCode === 0 && !!sessionId;
  const body = {
    ok,
    harness: v.harness,
    model: v.model,
    effort: v.effort,
    sessionId: sessionId || null,
    exitCode: o.exitCode,
    startedAt: o.startedAt,
    endedAt: o.endedAt,
    pid: o.pid,
    pidStart: o.pidStart,
    stdoutPath: o.stdoutPath,
    stderrPath: o.stderrPath,
  };
  if (!ok) body.error = error || 'turn_failed';
  return body;
}

function writeResult(file, result) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${process.pid}.${crypto.randomBytes(4).toString('hex')}.tmp`;
  try {
    fs.writeFileSync(temp, `${JSON.stringify(result)}\n`, { mode: 0o600 });
    fs.renameSync(temp, file);
  } catch (e) {
    try { fs.unlinkSync(temp); } catch { /* already gone */ }
    throw e;
  }
}

function spawnTurn(v, resultFile) {
  const { stdoutPath, stderrPath } = capturePaths(resultFile);
  const minted = v.harness === 'claude' && v.mode === 'new' ? crypto.randomUUID() : null;
  const tag = v.harness === 'opencode' && v.mode === 'new' ? `cast-turn:${crypto.randomUUID()}` : null;
  const argv = argvFor(v, minted, tag);
  const [cmd, ...childArgs] = argv;
  const win = spawnable(cmd, childArgs);
  const out = fs.createWriteStream(stdoutPath);
  const err = fs.createWriteStream(stderrPath);
  const childEnv = launchEnv(v.cwd, v.env);
  const startedAt = new Date().toISOString();
  const acc = { codexId: null, claudeId: null };
  let carry = '';

  return new Promise((resolve) => {
    let settled = false;
    const child = spawn(win.cmd, win.args, {
      cwd: v.cwd,
      env: childEnv,
      stdio: ['pipe', 'pipe', 'pipe'],
      ...win.opts,
    });
    const pid = child.pid ?? null;
    const pidStart = pid == null ? null : procStart(pid);
    if (pid != null) {
      emitHandle({
        pid, start: pidStart, harness: v.harness, model: v.model,
        session: minted || v.sessionId, tag, folder: v.cwd, t0: Date.now(),
      });
    }
    const finish = (exitCode, spawnError) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      if (carry) noteLine(carry, acc);
      const closeStreams = () => {
        resolve({
          exitCode, spawnError, minted, tag, pid, pidStart, startedAt,
          endedAt: new Date().toISOString(),
          stdoutPath, stderrPath,
          codexId: acc.codexId,
          claudeId: acc.claudeId,
          boundId: tag ? opencodeTagged(v.cwd, tag) : null,
        });
      };
      const ended = { out: false, err: false };
      const done = (which) => {
        if (ended[which]) return;
        ended[which] = true;
        if (ended.out && ended.err) closeStreams();
      };
      out.on('finish', () => done('out'));
      out.on('error', () => done('out'));
      err.on('finish', () => done('err'));
      err.on('error', () => done('err'));
      out.end();
      err.end();
    };
    const timer = setTimeout(() => {
      child.kill('SIGTERM');
      finish(1, 'deadline');
    }, DEADLINE_MS);
    child.on('error', (e) => finish(1, e.message));
    child.stdout.on('data', (d) => {
      out.write(d);
      carry += d.toString('utf8');
      const lines = carry.split('\n');
      carry = lines.pop();
      for (const line of lines) noteLine(line, acc);
    });
    child.stderr.on('data', (d) => { err.write(d); });
    child.on('close', (status) => finish(status === null ? 1 : status, null));
    child.stdin.on('error', () => {});
    child.stdin.end(stdinFor(v));
  });
}

async function runTurnAsync(args) {
  let resultFile;
  try {
    const paths = requestPaths(args);
    resultFile = paths.resultFile;
    const request = JSON.parse(fs.readFileSync(paths.requestFile, 'utf8'));
    const v = validate(request);
    const outcome = await spawnTurn(v, resultFile);
    const result = buildResult(v, outcome);
    writeResult(resultFile, result);
    process.exitCode = result.ok ? 0 : 1;
  } catch (e) {
    if (!resultFile) {
      process.stderr.write(`cast turn: ${e.message}\n`);
      process.exitCode = 2;
      return;
    }
    try {
      writeResult(resultFile, blankResult(e.message));
    } catch (w) {
      process.stderr.write(`cast turn: ${e.message}\ncast turn: cannot write result: ${w.message}\n`);
      process.exitCode = 2;
      return;
    }
    process.exitCode = 1;
  }
}

function runTurn(args) {
  runTurnAsync(args).catch((e) => {
    process.stderr.write(`cast turn: ${e.message}\n`);
    process.exitCode = 1;
  });
}

module.exports = {
  USAGE, requestPaths, validate, argvFor, stdinFor, noteLine, parseSessionEvents,
  capturePaths, blankResult, buildResult, writeResult, runTurn,
};
