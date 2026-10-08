#!/usr/bin/env node
'use strict';

// cast — one headless sub-agent launch behind a single interface.
//
// This file is the CLI front door: argv dispatch and the bare launch path. Every verb lives
// in its own module under lib/, split out 2026-08-20 along the section banners this file used
// to carry. Read lib/<verb>.js for a verb; read here only for how argv reaches it.

const { agentFilePrompt, agentTask, rbtvAgent, takeAgentFlags } = require('./lib/agent');
const { runAgentList } = require('./lib/agent-list');
const { runApi } = require('./lib/api');
const { USAGE, USAGE_IG, fail, listArgs, parseArgs, resolveEffort, resolveEffortValue, resolveFolder, resolveModel, taskText } = require('./lib/core');
const { runDoctor } = require('./lib/doctor');
const { fallbackPlan } = require('./lib/fallback');
const { modelsVerbPages, printHelp, verbHelpPages } = require('./lib/help');
const { SYSTEM_WRAPPER, launch, runResume } = require('./lib/launch');
const { runModels } = require('./lib/models');
const { loadOptional } = require('./lib/optional');
const { runRoute } = require('./lib/route');
const { runSessions } = require('./lib/sessions');

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
  if (rawArgv[0] === 'doctor') {
    const rest = rawArgv.slice(1);
    if (rest.includes('-h') || rest.includes('--help')) {
      process.stdout.write(`${PAGES.doctor.join('\n')}\n`);
      process.exit(0);
    }
    return runDoctor(rest);
  }
  if (rawArgv[0] === 'list') {
    const rest = rawArgv.slice(1);
    if (rest.includes('-h') || rest.includes('--help')) {
      process.stdout.write(`${PAGES.list.join('\n')}\n`);
      process.exit(0);
    }
    const { json, full, agent, target } = listArgs(rest);
    return runAgentList(agent, { json, full, target }, fail);
  }
  if (rawArgv[0] === 'models') {
    const rest = rawArgv.slice(1);
    if (rest.includes('-h') || rest.includes('--help')) {
      // The page of the verb named, wherever -h stands; the group page when none is named.
      const verb = rest.find((a) => !a.startsWith('-'));
      const pages = modelsVerbPages();
      const page = Object.hasOwn(pages, verb) ? pages[verb] : PAGES.models;
      process.stdout.write(`${page.join('\n')}\n`);
      process.exit(0);
    }
    return runModels(rest);
  }
  if (rawArgv[0] === 'resume') return runResume(rawArgv.slice(1));
  if (rawArgv[0] === 'sessions') return runSessions(rawArgv.slice(1));
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
  if (rawArgv[0] === 'turn') {
    fail("refused: unknown verb 'turn'\nchoose from resume, sessions, monitor, route, api, doctor, list, models\nNothing changed.\ncast -h");
  }

  const agentFlags = takeAgentFlags(rawArgv, fail);
  // An rbtv agent may be launched with neither -p nor -f: its folder's task.md is then the task.
  const parsed = parseArgs(agentFlags.argv, USAGE, !agentFlags.rbtv);
  const { dryRun, headed, detached, positional } = parsed;
  let { promptText, system } = parsed;
  if (agentFlags.rbtv && positional.length) {
    fail('refused: --agent does not take a harness, model or effort\n'
      + "with --agent, those values come from the agent's agent.json\n"
      + 'Nothing changed.\n'
      + `cast --agent ${agentFlags.rbtv} -p "reply with exactly: ok"\n`
      + `to change them: rbtv agent configure ${agentFlags.rbtv}`);
  }
  if ((agentFlags.rbtv || agentFlags.file) && system) {
    fail('refused: -s/-S cannot be combined with --agent or --rogue — the agent file is the system prompt');
  }
  if (agentFlags.file) system = agentFilePrompt(agentFlags.file, fail);
  const agent = agentFlags.rbtv ? rbtvAgent(agentFlags.rbtv, fail) : null;
  if (agent) system = { text: agent.prompt };
  if (agent && promptText === null) promptText = taskText(agentTask(agent, fail), `task.md in ${agent.home}`);
  if (system) system.wrapper = SYSTEM_WRAPPER;
  if (!agent && (positional.length < 3 || positional.length > 4)) {
    fail(`usage: ${USAGE}\n       ${USAGE_IG}\nrun cast -h for full help`);
  }
  const [harness, model, effortArg, folderArg = '.'] = agent ? [agent.harness, agent.model] : positional;

  const { modelId, spec } = resolveModel(harness, model, agent ? agent.home : process.cwd());

  // The effort the launch asks for: the agent's own rung word, or the dial number.
  const asked = agent ? agent.effort : Number(effortArg);
  let effort;
  if (agent) {
    try { effort = resolveEffortValue(spec, asked, harness, model); } catch (e) { fail(e.message); }
  } else {
    if (!Number.isInteger(asked) || asked < 1 || asked > 5) fail(`effort must be an integer 1-5, got: ${effortArg}`);
    effort = resolveEffort(spec, asked);
  }

  const folder = agent ? agent.home : resolveFolder(folderArg);

  launch({ harness, modelId, folder, effortWord: effort.word, effortArgv: effort.argv, system, promptText, headed, dryRun, detached,
    agentHome: agent ? agent.home : null,
    fallback: () => fallbackPlan(harness, modelId, asked, agent ? agent.home : process.cwd()) });
}

main(process.argv.slice(2));
