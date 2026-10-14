'use strict';

const board = require('./board.js');
const records = require('./records.js');
const lock = require('./lock.js');
const limits = require('./limits.js');
const publish = require('./publish.js');
const prepare = require('./prepare.js');
const commitments = require('./commitments.js');
const evidence = require('./evidence.js');
const rules = require('./rules.js');

module.exports = {
  ...lock,
  ...board,
  ...records,
  ...limits,
  ...publish,
  ...prepare,
  ...commitments,
  ...evidence,
  ...rules,
  readBoard: board.readCanonical,
  writeBoard: board.writeBoard,
  closeBoard: board.closeSubject,
  renderBoardView: board.renderBoardView,
  prepareMemory: prepare.prepareMemory,
  renderBundle: prepare.renderBundle,
  checkMemory: records.checkMemory,
  validateProposal: publish.validateProposal,
  validateProposalResult: publish.validateProposalResult,
  publishProposal: publish.publishProposal,
  createCommitment: commitments.createCommitment,
  intakeEvidence: evidence.intakeEvidence,
  publishGlobalRule: rules.publishGlobalRule,
  checkLimits: limits.checkLimits,
  ensureAgentBaseline: records.ensureAgentBaseline,
  agentBaselinePath: records.agentBaselinePath,
};
