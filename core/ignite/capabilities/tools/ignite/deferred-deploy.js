'use strict';

// API — the deploy an agent asks for inside its own turn (ignite deploy --after-turn), run by the
// daemon once no turn is running, and reported back to the conversation that asked for it.
// request({ installation, commit, deployFolder, agent, conversation, now }) → the stored request;
//   refuses while another request waits.
// step({ installation, busy, start, report, now, log }) → what one daemon tick did:
//   'none' | 'waiting' | 'started' | 'reported'. busy() is true while a turn runs; start(request)
//   launches the deploy outside the service and returns { ok, error }; report(request, text) queues
//   the outcome in the requesting conversation.
// startCommand(request, installation, env, ignite) → [program, args] for start: a systemd-run job,
//   so the deploy outlives the service it restarts and runs with the service's own PATH. ignite is
//   the program's absolute path: systemd does not search the PATH it is given.

const fs = require('node:fs');
const path = require('node:path');
const { runtimeFolder } = require('./memory-write.js');

const REQUEST = 'deploy-request.json';
const LOG = 'deploys.jsonl';
const UNIT = 'rbtv-ignite-agents.service';
// A started deploy writes its log line within about a minute (the script, then up to 30 seconds of
// checks). With no line after this long, the job died before logging, and the request is closed.
const REPORT_LIMIT_MS = 10 * 60_000;

function requestFile(installation) {
  return path.join(runtimeFolder(installation), REQUEST);
}

function read(installation) {
  try { return JSON.parse(fs.readFileSync(requestFile(installation), 'utf8')); } catch { return null; }
}

function write(installation, body) {
  const file = requestFile(installation);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(temp, `${JSON.stringify(body)}\n`);
  fs.renameSync(temp, file);
}

function request({ installation, commit, deployFolder, agent, conversation, now = Date.now() }) {
  const waiting = read(installation);
  if (waiting) {
    const error = new Error(`a deploy of ${waiting.commit} asked by ${waiting.agent} is already waiting (${requestFile(installation)}).\nNothing changed.\nignite deploy -h`);
    error.exitCode = 1;
    throw error;
  }
  const body = { commit, deployFolder, agent, conversation, requestedAt: now, startedAt: null };
  write(installation, body);
  return body;
}

// The last deploy log line for the request's commit written since it started.
function logLine(installation, req) {
  let text;
  try { text = fs.readFileSync(path.join(runtimeFolder(installation), LOG), 'utf8'); } catch { return null; }
  const rows = text.split('\n').filter(Boolean).map((line) => { try { return JSON.parse(line); } catch { return null; } });
  return rows.reverse().find((row) => row?.commitAsked === req.commit && Date.parse(row.time) >= req.startedAt) || null;
}

function describe(req, row) {
  if (row.outcome === 'ok') return `Deploy of ${req.commit} (asked with ignite deploy --after-turn) finished: ok. Deploy log line: ${JSON.stringify(row)}`;
  return `Deploy of ${req.commit} (asked with ignite deploy --after-turn) FAILED: ${row.reason}. Deploy log line: ${JSON.stringify(row)}. Read journalctl --user -u ${UNIT} and tell the owner.`;
}

function finish(installation, req, text, report, log) {
  try { report(req, text); } catch (error) { log?.({ event: 'deploy-after-turn', message: `report failed: ${error.message}`, text }); }
  try { fs.unlinkSync(requestFile(installation)); } catch { /* already gone */ }
  log?.({ event: 'deploy-after-turn', commit: req.commit, reported: text });
  return 'reported';
}

function step({ installation, busy, start, report, now = Date.now(), log }) {
  const req = read(installation);
  if (!req) return 'none';
  if (req.startedAt == null) {
    if (busy()) return 'waiting';
    const started = { ...req, startedAt: now };
    // Recorded before the launch, so a restart the deploy causes never launches it a second time.
    write(installation, started);
    const launched = start(started);
    if (!launched.ok) {
      return finish(installation, started, `Deploy of ${req.commit} (asked with ignite deploy --after-turn) did not start: ${launched.error}. Nothing was deployed.`, report, log);
    }
    log?.({ event: 'deploy-after-turn', commit: req.commit, started: true });
    return 'started';
  }
  const row = logLine(installation, req);
  if (row) return finish(installation, req, describe(req, row), report, log);
  if (now - req.startedAt > REPORT_LIMIT_MS) {
    return finish(installation, req, `Deploy of ${req.commit} (asked with ignite deploy --after-turn) started but wrote no deploy log line in ${REPORT_LIMIT_MS / 60_000} minutes. Read journalctl --user -u 'ignite-deploy-*' and journalctl --user -u ${UNIT}, then tell the owner.`, report, log);
  }
  return 'started';
}

function startCommand(req, installation, env, ignite) {
  return ['systemd-run', [
    '--user', '--collect', `--unit=ignite-deploy-${req.commit.slice(0, 12)}-${req.startedAt}`,
    `--setenv=PATH=${env.PATH || ''}`, `--setenv=HOME=${env.HOME || ''}`,
    ignite, 'deploy', req.commit, '--installation', installation, '--deploy-folder', req.deployFolder,
  ]];
}

module.exports = { request, step, startCommand, requestFile, REPORT_LIMIT_MS };
