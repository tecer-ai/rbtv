'use strict';

// API
// runOnce(slug, deps) → one claimed turn, or a refusal / empty claim.
//   deps: { home, store, slack?, audio?, turnCommand?, castEnv?, historyWindow?, now?, log? }
//   Refuses when liveRun() matches a live pid. A running row that is not live is failRun'd
//   (recovery) before the next claim. ignite turn cwd is realpath(home). Same harness + stored
//   session id resumes that id; a harness change or no id starts a new session and the prompt
//   carries stored history and work state. The run's session is saved under the harness that
//   ran; what a turn does when the agent's model fails to start is in fallback.js. Every cast
//   request includes systemPromptFile <home>/prompt.md (absolute). This file does not read or
//   require CLAUDE.md.
//   failRun enqueues the one blocker — this file does not.
//   The live status of the conversation of the owner message a turn answers (live-status.js): running
//   and working at launch, fallback once `ignite turn` starts a fallback (the file turn.js's
//   fellBackFile names appears, checked every deps.fallbackCheckMs, else FALLBACK_CHECK_MS, and again
//   at the end), retrying or failed on a failure, and at the end what the result's disposition gives,
//   written in the transaction that ends the run. The replies carry that message, the run and its task
//   state in payload.mark { channel, ts, runId, task? }, for outbox.js to show at delivery.
//   The result's caveats: absent, false or null mean none; true is valid only with completed; any
//   other value fails the turn.
// DEFAULT_HISTORY_WINDOW — re-exported for callers

const fs = require('node:fs');
const path = require('node:path');
const { spawn } = require('node:child_process');
const { procStart } = require('../../../../cast/capabilities/tools/cast/lib/handles');
const castAgent = require('../../../../cast/capabilities/tools/cast/lib/agent');
const { composeTurn, readTurnMemory } = require('./prompt.js');
const { DEFAULT_HISTORY_WINDOW, historyPath, listAll, writeHistory } = require('./history.js');
const { ignitePaths, resolveIgniteRuntime } = require('./config.js');
const fallback = require('./fallback.js');
const live = require('./live-status.js');
const { fellBackFile } = require('./turn.js');

const AUDIO_EXT = new Set(['mp3', 'm4a', 'wav', 'ogg', 'webm', 'flac', 'aac', 'mpeg', 'mp4', 'mpga']);
const DISPOSITIONS = new Set(['completed', 'continue', 'waiting_owner', 'waiting_workers', 'stopped']);
const TRANSCRIPTION_FAILURE_REPLY = 'I could not transcribe that voice note; please send it as text.';
const FALLBACK_CHECK_MS = 1_000;

function clock(deps) {
  return deps.now ? deps.now() : Date.now();
}

function fail(message, scope) {
  const error = new Error(message);
  error.scope = scope;
  return error;
}

function isAudio(file) {
  const mime = String(file?.mimetype || '');
  if (mime.startsWith('audio/')) return true;
  const ext = String(file?.filetype || path.extname(file?.name || '').slice(1)).toLowerCase();
  return AUDIO_EXT.has(ext);
}

// The agent's launch values and voice, as cast reads its record; a record cast would not launch
// stops the turn here.
function readAgent(home) {
  const read = castAgent.readAgent(home);
  if (read.problem) throw fail(read.problem === 'launch' ? `agent.json: ${read.why}` : read.why, 'agent');
  const { harness, model, effort, voice } = read.agent;
  return { harness, model, effort, voice };
}

function inputText(claim) {
  const payload = claim.payload || {};
  if (claim.kind === 'continue') return payload.nextStep || payload.summary || '';
  if (claim.kind === 'wake') return payload.note || 'worker completion';
  if (claim.kind === 'schedule') return payload.scheduleId || '';
  return typeof payload.text === 'string' ? payload.text : '';
}

function tail(file) {
  if (!file) return '';
  try {
    const text = fs.readFileSync(file, 'utf8').trim();
    return text.length > 500 ? text.slice(0, 500) : text;
  } catch {
    return '';
  }
}

function childStarted(launcher) {
  return Boolean(launcher && (launcher.pid != null || launcher.stdoutPath));
}

function launchScope(exitCode, launcher) {
  if (!launcher) return 'agent';
  if (launcher.ok) return null;
  if (!childStarted(launcher)) return 'agent';
  if (exitCode === 2 && launcher.exitCode == null) return 'agent';
  return 'work';
}

// `lead` holds the parts that come before the launcher's own.
function concrete(exitCode, launcher, lead) {
  const parts = [...lead];
  if (launcher?.error) parts.push(String(launcher.error));
  if (launcher?.exitCode != null) parts.push(`exitCode ${launcher.exitCode}`);
  else if (exitCode != null) parts.push(`cast exit ${exitCode}`);
  const stderr = tail(launcher?.stderrPath);
  if (stderr) parts.push(stderr);
  return parts.filter(Boolean).join('; ') || 'launch failed';
}

function readJson(file) {
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function validateAgent(raw, nonce) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw fail('agent result is not an object', 'work');
  if (raw.nonce !== nonce) throw fail('agent result nonce mismatch', 'work');
  if (!DISPOSITIONS.has(raw.disposition)) throw fail(`invalid disposition: ${raw.disposition}`, 'work');
  if (typeof raw.summary !== 'string') throw fail('summary must be a string', 'work');
  if (raw.nextStep != null && typeof raw.nextStep !== 'string') throw fail('nextStep must be a string', 'work');
  if (raw.disposition === 'continue' && !String(raw.nextStep || '').trim()) {
    throw fail('continue requires nextStep', 'work');
  }
  if (raw.caveats != null && typeof raw.caveats !== 'boolean') throw fail('caveats must be true, false or null', 'work');
  if (raw.caveats === true && raw.disposition !== 'completed') {
    throw fail('caveats true is valid only with disposition completed', 'work');
  }
  if (!Array.isArray(raw.workers)) throw fail('workers must be an array', 'work');
  for (const worker of raw.workers) {
    if (!worker || typeof worker.ref !== 'string' || typeof worker.kind !== 'string') {
      throw fail('worker requires ref and kind', 'work');
    }
  }
  if (!Array.isArray(raw.outputs) || raw.outputs.some((item) => typeof item !== 'string')) {
    throw fail('outputs must be an array of paths', 'work');
  }
  if (!Array.isArray(raw.replies)) throw fail('replies must be an array', 'work');
  for (const reply of raw.replies) {
    if (!reply || typeof reply.text !== 'string') throw fail('reply text must be a string', 'work');
    if (reply.audio != null && typeof reply.audio !== 'boolean') throw fail('reply audio must be boolean', 'work');
    if (reply.files != null && (!Array.isArray(reply.files) || reply.files.some((item) => typeof item !== 'string'))) {
      throw fail('reply files must be an array of paths', 'work');
    }
  }
  return raw;
}

async function preprocess(claim, deps, dir) {
  const payload = claim.payload || {};
  if (claim.kind !== 'owner') return { text: inputText(claim), files: [], transcriptError: null, audioAttempted: false };
  const listed = Array.isArray(payload.files) ? payload.files : [];
  const audioMeta = listed.filter(isAudio);
  let downloaded = [];
  if (listed.length) {
    if (typeof deps.slack?.downloadFile !== 'function') throw fail('slack.downloadFile required', 'work');
    const conv = deps.store.getConversation(claim.conversation_key);
    downloaded = await deps.slack.downloadFile({
      channel: conv.channel,
      ts: payload.ts,
      threadTs: payload.threadTs || conv.root_ts,
      dir,
    }) || [];
  }
  const transcripts = [];
  const failures = [];
  for (const meta of audioMeta) {
    const match = (meta.id && downloaded.find((item) => item.id === meta.id))
      || downloaded.find((item) => item.name === meta.name)
      || (downloaded.length === 1 ? downloaded[0] : null);
    if (!match?.path) {
      failures.push(`${meta.name || 'audio'}: file was not downloaded`);
      continue;
    }
    if (typeof deps.audio?.transcribe !== 'function') throw fail('audio.transcribe required', 'work');
    try {
      transcripts.push((await deps.audio.transcribe(match.path)).text);
    } catch (error) {
      failures.push(`${meta.name || match.path}: ${error.message}`);
    }
  }
  const parts = [];
  if (payload.text) parts.push(payload.text);
  if (transcripts.length) parts.push(transcripts.join('\n'));
  const transcriptError = failures.length ? `Transcription failed: ${failures.join('; ')}` : null;
  return {
    text: parts.join('\n').trim(),
    files: downloaded.map((item) => item.path).filter(Boolean),
    missingFiles: Math.max(0, listed.length - downloaded.length),
    transcriptError,
    audioAttempted: audioMeta.length > 0,
    transcripts,
  };
}

function logTranscriptionFailure(deps, message) {
  if (typeof deps.log === 'function') deps.log({ event: 'transcription-failed', message });
}

function waitClose(child) {
  if (child.exitCode != null) return Promise.resolve(child.exitCode);
  return new Promise((resolve, reject) => {
    child.once('error', reject);
    child.once('close', (code) => resolve(code ?? 1));
  });
}

// Fails the run; its message shows retrying while it will retry, and failed once it is held.
function failWithStatus(deps, run, reason, scope) {
  const store = deps.store;
  return store.transaction(() => {
    const failure = store.failRun(run.runId || run.id, reason, { scope, now: clock(deps) });
    live.failed(store, live.messageOf(store, run, deps.log), failure.held, deps.log);
    return failure;
  });
}

async function recover(store, deps) {
  if (store.liveRun()) return null;
  const active = store.getActiveRun();
  if (!active) return null;
  const failure = failWithStatus(deps, active, 'previous invocation is no longer running', 'work');
  return { runId: active.id, failure };
}

function commit(store, claim, fields) {
  return store.finishRun(claim.runId, claim.nonce, {
    invocationNonce: claim.nonce,
    workers: [],
    outputs: [],
    nextStep: null,
    ...fields,
  });
}

async function runOnce(slug, deps) {
  if (!slug) throw new Error('runOnce requires slug');
  if (!deps?.store) throw new Error('runOnce requires deps.store');
  if (!deps.home) throw new Error('runOnce requires deps.home');
  const store = deps.store;
  if (store.liveRun()) return { slug, refused: 'live', claimed: false };

  const recovered = await recover(store, deps);
  const now = clock(deps);
  const claim = store.claimNext(now);
  if (!claim) return { slug, refused: false, claimed: false, recovered };

  try {
    return await execute(slug, claim, deps);
  } catch (error) {
    if (store.getActiveRun()?.id !== claim.runId) throw error;
    const scope = error.scope === 'agent' ? 'agent' : 'work';
    const failure = failWithStatus(deps, claim, error.message, scope);
    return { slug, claimed: true, failed: true, runId: claim.runId, failure: { ...failure, scope }, recovered };
  }
}

async function execute(slug, claim, deps) {
  const store = deps.store;
  const home = fs.realpathSync(deps.home);
  resolveIgniteRuntime(home);
  const dir = path.join(ignitePaths(home).turns, claim.runId);
  fs.mkdirSync(dir, { recursive: true });
  const prepared = await preprocess(claim, deps, path.join(dir, 'files'));
  const message = live.messageOf(store, claim, deps.log);
  if (prepared.transcripts?.length) {
    store.recordMessage(claim.conversation_key, {
      id: `used:${claim.runId}`,
      role: 'owner',
      text: prepared.text,
      metadata: { source: 'used-text', queueId: claim.id },
    });
  }
  const noLaunch = prepared.audioAttempted && !prepared.transcripts?.length && !claim.payload?.text && prepared.transcriptError;
  if (noLaunch) {
    logTranscriptionFailure(deps, prepared.transcriptError);
    const work = store.transaction(() => {
      const done = commit(store, claim, {
        output: TRANSCRIPTION_FAILURE_REPLY,
        disposition: 'completed',
        summary: 'transcription failed',
        outbox: [{ id: `transcript:${claim.id}`, text: TRANSCRIPTION_FAILURE_REPLY, audio: false, files: [] }],
      });
      live.failed(store, message, true, deps.log);
      return done;
    });
    writeHistory(home, store, claim.conversation_key);
    return { slug, claimed: true, launched: false, disposition: 'completed', work, runId: claim.runId };
  }
  if (prepared.transcriptError) {
    logTranscriptionFailure(deps, prepared.transcriptError);
    store.enqueueOutbox({
      id: `transcript:${claim.id}`,
      conversationKey: claim.conversation_key,
      payload: { text: TRANSCRIPTION_FAILURE_REPLY, audio: false, files: [] },
    });
  }

  const setting = readAgent(home);
  const known = store.getSession(claim.conversation_key, setting.harness);
  const session = known ? { mode: 'resume', id: known } : { mode: 'new' };
  const window = deps.historyWindow ?? DEFAULT_HISTORY_WINDOW;
  const stored = listAll(store, claim.conversation_key);
  const recent = store.listHistory(claim.conversation_key, window);
  const resultPath = path.join(dir, 'agent-result.json');
  const requestPath = path.join(dir, 'request.json');
  const launcherPath = path.join(dir, 'launcher.json');
  writeHistory(home, store, claim.conversation_key);
  const memory = readTurnMemory(home, home, store, clock(deps));
  try {
    const installation = require('./memory.js').workspaceFromHome(home);
    if (installation) {
      const prepared = require('../../../../memory/capabilities/tools/memory/lib/index.js').prepareMemory({
        installation, agentHome: home, cwd: home,
      });
      if (prepared.identity?.view) memory.board = prepared.identity.view;
      const bundle = (prepared.bundle || []).filter((row) => row.path !== prepared.identity?.board);
      if (bundle.length) memory.memory = bundle.map((row) => ({ path: row.path, text: row.text }));
    }
  } catch (error) {
    if (error.code !== 'MODULE_NOT_FOUND') memory.alerts.push(`Memory alert: prepareMemory failed: ${error.message}`);
  }
  if (memory.alerts.length) {
    const text = memory.alerts.join('\n');
    try {
      store.enqueueOutbox({ id: `memory:${claim.runId}`, conversationKey: claim.conversation_key,
        payload: { text, audio: false, files: [] } });
    } catch {
      // Alert delivery must not turn a recoverable memory failure into a hold.
      memory.memory.push({ path: 'Memory alerts', text: `${text}\nOwner alert could not be queued; tell the owner.` });
      if (typeof deps.log === 'function') {
        try { deps.log({ event: 'memory-alert-failed', message: text }); } catch { /* Keep the turn runnable. */ }
      }
    }
  }
  // The turn's prompt for a harness session: a new session also gets the stored thread context.
  const promptFor = (target) => composeTurn({
    board: memory.board,
    memory: memory.memory,
    work: claim.work_id ? store.getWork(claim.work_id) : null,
    inputs: [{
      role: claim.kind, text: prepared.text, files: prepared.files, missingFiles: prepared.missingFiles,
      ts: claim.kind === 'owner' ? claim.payload?.ts : undefined,
      check: claim.kind === 'schedule' ? claim.payload?.details : undefined,
    }],
    recent,
    stored,
    historyPath: historyPath(home, claim.conversation_key),
    resultPath,
    nonce: claim.nonce,
    rehydrate: target.mode === 'new',
  });
  const prompt = promptFor(session);
  const plan = fallback.planFor(setting, home, deps.log);
  const request = {
    harness: setting.harness,
    model: setting.model,
    effort: setting.effort,
    cwd: home,
    agentHome: home,
    prompt,
    systemPromptFile: path.join(home, castAgent.PROMPT_MD),
    session,
    env: {
      RBTV_AGENT_HOME: home,
      IGNITE_CONVERSATION: claim.conversation_key,
    },
    fallbacks: fallback.requestList(plan, (harness) => store.getSession(claim.conversation_key, harness), promptFor),
  };
  fs.writeFileSync(requestPath, JSON.stringify(request));

  live.started(store, message, claim.runId, deps.log);
  // Production always starts this tool's local `turn`; a test may replace that
  // program without changing the production command lookup contract.
  const turnCommand = deps.turnCommand || [process.execPath, path.join(__dirname, 'cli.js'), 'turn'];
  const child = spawn(turnCommand[0], [...turnCommand.slice(1), '--request', requestPath, '--result', launcherPath], {
    cwd: home,
    env: { ...process.env, ...deps.castEnv },
    stdio: ['ignore', 'ignore', 'ignore'],
  });
  const exited = waitClose(child);
  const pidStart = child.pid ? procStart(child.pid) : null;
  if (child.pid && pidStart) store.attachProcess(claim.runId, { pid: child.pid, pidStart, setting });
  // The file `ignite turn` writes when it starts the first fallback in place of the agent's model.
  const fellBack = fellBackFile(launcherPath);
  const watch = message && request.fallbacks ? setInterval(() => {
    if (!fs.existsSync(fellBack)) return;
    clearInterval(watch);
    live.fellBack(store, message, deps.log);
  }, deps.fallbackCheckMs ?? FALLBACK_CHECK_MS) : null;

  let exitCode;
  try {
    exitCode = await exited;
  } catch (error) {
    throw fail(error.message, 'agent');
  } finally {
    if (watch) clearInterval(watch);
  }
  const launcher = readJson(launcherPath);
  if (message && launcher?.failed?.length) live.fellBack(store, message, deps.log);
  fallback.report(launcher, plan, { store, claim, log: deps.log });
  const scope = launchScope(exitCode, launcher);
  if (scope) throw fail(concrete(exitCode, launcher, fallback.failureWords(launcher, plan)), scope);

  let agent;
  try {
    agent = validateAgent(readJson(resultPath), claim.nonce);
  } catch (error) {
    if (error.scope) throw error;
    throw fail(error.message, 'work');
  }
  const output = fs.readFileSync(resultPath, 'utf8');
  // The owner message the replies answer, their run, and the task state outbox.js shows once every
  // reply is delivered.
  const task = live.taskOf(agent.disposition, agent.caveats === true);
  const mark = message ? { channel: message.channel, ts: message.ts, runId: claim.runId, ...(task && { task }) } : null;
  const work = store.transaction(() => {
    const done = commit(store, claim, {
      output,
      disposition: agent.disposition,
      summary: agent.summary,
      nextStep: agent.nextStep || null,
      workers: agent.workers,
      outputs: agent.outputs,
      harness: launcher.sessionId ? launcher.harness : null,
      sessionId: launcher.sessionId || null,
      outbox: agent.replies.map((reply) => ({
        payload: { text: reply.text, audio: reply.audio === true, files: reply.files || [], ...(mark && { mark }) },
      })),
    });
    live.ended(store, message, agent.disposition, task, agent.replies.length, deps.log);
    return done;
  });
  writeHistory(home, store, claim.conversation_key);
  const snapshot = store.db.prepare('SELECT launch_snapshot FROM runs WHERE id=?').get(claim.runId);
  return {
    slug,
    claimed: true,
    launched: true,
    runId: claim.runId,
    queueId: claim.id,
    kind: claim.kind,
    disposition: agent.disposition,
    work,
    requestPath,
    prompt,
    session,
    snapshot: snapshot?.launch_snapshot ? JSON.parse(snapshot.launch_snapshot) : setting,
  };
}

module.exports = { runOnce, DEFAULT_HISTORY_WINDOW };
