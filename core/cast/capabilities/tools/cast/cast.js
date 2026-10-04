#!/usr/bin/env node
'use strict';

// cast — one headless sub-agent launch behind a single interface.
//
// This file is the CLI front door: argv dispatch and the bare launch path. Every verb lives
// in its own module under lib/, split out 2026-08-20 along the section banners this file used
// to carry. Read lib/<verb>.js for a verb; read here only for how argv reaches it.

const { agentFilePrompt, installedAgent, takeAgentFlags } = require('./lib/agent');
const { runApi } = require('./lib/api');
const { USAGE, USAGE_IG, fail, parseArgs, resolveEffort, resolveEffortValue, resolveFolder, resolveModel, runDoctor, runList } = require('./lib/core');
const { printHelp, verbHelpPages } = require('./lib/help');
const { SYSTEM_WRAPPER, launch, runResume } = require('./lib/launch');
const { loadOptional } = require('./lib/optional');
const { runRoute } = require('./lib/route');
const { runSessions } = require('./lib/sessions');
const { runTurn } = require('./lib/turn');

function main(rawArgv) {
  if (rawArgv.length === 0) fail(`usage: ${USAGE}\nrun cast -h for full help`);
  if (rawArgv[0] === '-h' || rawArgv[0] === '--help') {
    printHelp();
    process.exit(0);
  }
  // Per-verb help: only when -h/--help is the verb's sole argument, so a prompt whose
  // text happens to be "-h" is never mistaken for a help request.
  const PAGES = verbHelpPages();
  if (PAGES[rawArgv[0]] && rawArgv.length === 2 &&
      (rawArgv[1] === '-h' || rawArgv[1] === '--help')) {
    process.stdout.write(`${PAGES[rawArgv[0]].join('\n')}\n`);
    process.exit(0);
  }
  if (rawArgv[0] === 'doctor') return runDoctor(rawArgv.slice(1));
  if (rawArgv[0] === 'list') return runList(rawArgv.slice(1));
  if (rawArgv[0] === 'resume') return runResume(rawArgv.slice(1));
  if (rawArgv[0] === 'sessions') return runSessions(rawArgv.slice(1));
  if (rawArgv[0] === 'turn') return runTurn(rawArgv.slice(1));
  if (rawArgv[0] === 'monitor') {
    const { module: monitor, error } = loadOptional('monitor');
    if (error) {
      process.stderr.write(`cast monitor: lib/monitor.js failed to load — ${error.message}\n`);
      process.exit(1);
    }
    return monitor.runMonitor(rawArgv.slice(1));
  }
  if (rawArgv[0] === 'route') return runRoute(rawArgv.slice(1));
  // `cast api` takes -p TEXT as of 2026-08-20 (route redesign §7), so the verb owns every `api`
  // invocation — there is no longer a launch-shaped `cast api …` form to fall through to.
  if (rawArgv[0] === 'api') return runApi(rawArgv.slice(1));

  const agentFlags = takeAgentFlags(rawArgv, fail);
  const parsed = parseArgs(agentFlags.argv, USAGE, true);
  const { dryRun, headed, detached, promptText, positional } = parsed;
  let { system } = parsed;
  if (agentFlags.installed && positional.length) {
    fail('refused: -ig does not take a harness, model or effort\n'
      + "with -ig, those values come from the agent's agent.json\n"
      + 'Nothing changed.\n'
      + `cast -ig ${agentFlags.installed} (-p TEXT | -f FILE)\n`
      + `to change them: rbtv agent configure ${agentFlags.installed}`);
  }
  if ((agentFlags.installed || agentFlags.file) && system) {
    fail('refused: -s/-S cannot be combined with -ig or -rg — the agent file is the system prompt');
  }
  if (agentFlags.file) system = agentFilePrompt(agentFlags.file, fail);
  const agent = agentFlags.installed ? installedAgent(agentFlags.installed, fail) : null;
  if (agent) system = { text: agent.prompt };
  if (system) system.wrapper = SYSTEM_WRAPPER;
  if (!agent && (positional.length < 3 || positional.length > 4)) {
    fail(`usage: ${USAGE}\n       ${USAGE_IG}\nrun cast -h for full help`);
  }
  const [harness, model, effortArg, folderArg = '.'] = agent ? [agent.harness, agent.model] : positional;

  const { modelId, spec } = resolveModel(harness, model);

  let effort;
  if (agent) {
    try { effort = resolveEffortValue(spec, agent.effort, harness, model); } catch (e) { fail(e.message); }
  } else {
    const n = Number(effortArg);
    if (!Number.isInteger(n) || n < 1 || n > 5) fail(`effort must be an integer 1-5, got: ${effortArg}`);
    effort = resolveEffort(spec, n);
  }

  const folder = agent ? agent.home : resolveFolder(folderArg);

  launch({ harness, modelId, folder, effortWord: effort.word, effortArgv: effort.argv, system, promptText, headed, dryRun, detached,
    agentHome: agent ? agent.home : null });
}

main(process.argv.slice(2));
