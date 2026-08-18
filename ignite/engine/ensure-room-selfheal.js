'use strict';

const { HeartStoreError, E_JOB_EXISTS, E_UNKNOWN_TOOL } = require('../server/heart/heart-store');

const GENERIC_TOOL = 'selfheal-room-goal';
const ARGS_SCHEMA = JSON.stringify({
  required: { tool: 'string' },
  optional: { workdir: 'string' },
});
const EVERY_S = 300;

function jobIdFor(goal) {
  return `selfheal-room-${goal}`;
}

function pickTool(tools, goal) {
  const perRoom = jobIdFor(goal);
  if (tools && Object.hasOwn(tools, perRoom)) return perRoom;
  if (tools && Object.hasOwn(tools, GENERIC_TOOL)) return GENERIC_TOOL;
  return null;
}

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

function ensureRoomSelfheal({ heartStore, goal, goalFolder, logger = null }) {
  const result = {
    jobId: jobIdFor(goal),
    tool: null,
    registered: false,
    scheduled: false,
    skipped: null,
  };
  if (!goal || typeof goal !== 'string') {
    result.skipped = 'no-goal';
    return result;
  }
  if (goal.startsWith('_')) {
    result.skipped = 'reserved-name';
    return result;
  }

  const tool = pickTool(heartStore.config && heartStore.config.tools, goal);
  if (!tool) {
    result.skipped = 'no-tool-entry';
    return result;
  }
  result.tool = tool;

  if (!heartStore.getJob(result.jobId)) {
    try {
      heartStore.registerJob({
        jobId: result.jobId,
        actionType: 'fire-tool',
        function: 'fire-tool',
        argsSchema: ARGS_SCHEMA,
        description: `dead-room detection + recovery, room ${goal}`,
      });
      result.registered = true;
    } catch (err) {
      if (!(err instanceof HeartStoreError && err.code === E_JOB_EXISTS)) throw err;
    }
  }

  const queued = heartStore.listQueue().some((q) => q.job_id === result.jobId);
  if (queued) {
    result.skipped = result.skipped || 'queue-row-exists';
    return result;
  }

  const args = { tool };
  if (tool === GENERIC_TOOL && goalFolder) args.workdir = goalFolder;

  try {
    heartStore.enqueue({
      jobId: result.jobId,
      args: JSON.stringify(args),
      sessionMode: 'headless',
      triggerKind: 'periodic',
      intervalSeconds: EVERY_S,
      runAt: isoNow(),
      enqueuedBy: 'ensure-room-selfheal',
    });
    result.scheduled = true;
  } catch (err) {
    if (err instanceof HeartStoreError && err.code === E_UNKNOWN_TOOL) {
      result.skipped = 'tool-not-in-boot-config';
      if (logger) {
        logger({
          level: 'warn',
          message: 'room selfheal not scheduled — tool missing from boot-read config',
          goal,
          tool,
        });
      }
      return result;
    }
    throw err;
  }
  return result;
}

module.exports = { ensureRoomSelfheal, jobIdFor, GENERIC_TOOL, ARGS_SCHEMA, EVERY_S };
