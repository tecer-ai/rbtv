#!/usr/bin/env node
'use strict';

// cast — one headless sub-agent launch behind a single interface.
//
// This file is the CLI front door: argv dispatch and the bare launch path. Every verb lives
// in its own module under lib/, split out 2026-08-20 along the section banners this file used
// to carry. Read lib/<verb>.js for a verb; read here only for how argv reaches it.

const { runApi } = require('./lib/api');
const { USAGE, fail, parseArgs, resolveEffort, resolveFolder, resolveModel, runDoctor, runList } = require('./lib/core');
const { printHelp, verbHelpPages } = require('./lib/help');
const { SYSTEM_WRAPPER, launch, runResume, runSeat } = require('./lib/launch');
const { monitor, monitorLoadError } = require('./lib/monitor-load');
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
  if (rawArgv[0] === 'doctor') return runDoctor(rawArgv.slice(1));
  if (rawArgv[0] === 'list') return runList(rawArgv.slice(1));
  if (rawArgv[0] === 'seat') return runSeat(rawArgv.slice(1));
  if (rawArgv[0] === 'resume') return runResume(rawArgv.slice(1));
  if (rawArgv[0] === 'sessions') return runSessions(rawArgv.slice(1));
  if (rawArgv[0] === 'monitor') {
    if (monitorLoadError) {
      process.stderr.write(`cast monitor: lib/monitor.js failed to load — ${monitorLoadError.message}\n`);
      process.exit(1);
    }
    return monitor.runMonitor(rawArgv.slice(1));
  }
  if (rawArgv[0] === 'route') return runRoute(rawArgv.slice(1));
  // `cast api` takes -p TEXT as of 2026-08-20 (route redesign §7), so the verb owns every `api`
  // invocation — there is no longer a launch-shaped `cast api …` form to fall through to.
  if (rawArgv[0] === 'api') return runApi(rawArgv.slice(1));

  const { dryRun, headed, detached, promptText, system, positional } = parseArgs(rawArgv, USAGE, true);
  if (system) system.wrapper = SYSTEM_WRAPPER;
  if (positional.length < 3 || positional.length > 4) {
    fail(`usage: ${USAGE}\nrun cast -h for full help`);
  }
  const [harness, model, effortStr, folderArg = '.'] = positional;

  const { modelId, spec } = resolveModel(harness, model);

  const n = Number(effortStr);
  if (!Number.isInteger(n) || n < 1 || n > 5) fail(`effort must be an integer 1-5, got: ${effortStr}`);

  const folder = resolveFolder(folderArg);
  const { word: effortWord, argv: effortArgv } = resolveEffort(spec, n);

  launch({ harness, modelId, folder, effortWord, effortArgv, system, promptText, headed, dryRun, detached });
}

main(process.argv.slice(2));

