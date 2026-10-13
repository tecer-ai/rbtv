#!/usr/bin/env node
'use strict';

const fs = require('node:fs');
const path = require('node:path');
const lib = require('./lib/index.js');

const SECTIONS = ['What matters now', 'Watch-outs', 'Timers', 'Recently closed'];

function fail(message) {
  process.stderr.write(`${message}\n`);
  process.exit(1);
}

function wantHelp(argv) {
  return argv.includes('-h') || argv.includes('--help');
}

function option(argv, name) {
  const index = argv.indexOf(name);
  if (index === -1) return null;
  const value = argv[index + 1];
  if (!value || value.startsWith('-')) fail(`${name} requires a value\nmemory -h`);
  return value;
}

function emit(payload, text) {
  if (process.argv.includes('--json')) process.stdout.write(`${JSON.stringify(payload)}\n`);
  else if (text) process.stdout.write(text);
}

const HELP = {
  root: `memory — shared board, capture and publication

  board        Read, write, close, fold or view a board.
  prepare      Prepare one agent's memory bundle.
  validate     Check a whole proposal and list every failed requirement.
  publish      Validate, then publish when every requirement passes.
  remember     Append one owner fact, or store unverified evidence as pending.
  commitment   Create or update a shared commitment.
  evidence     Store attributable evidence as pending or as a remember line.
  rule         Publish one approved global learned rule.
  limit        Check always-loaded and on-demand limits.
  migrate      Dry-run, apply or roll back a memory migration manifest.

Proposal field names are taught by the consolidation tool's -h, not here.
A refusal lists every failed requirement this command could check.
Each item has path, operation, requirement, expected and reason.
No memory text you did not submit is printed.

memory <verb> -h
`,
  board: `memory board — canonical board operations

  read         Print the canonical board and its revision.
  write        Replace editable sections when the revision still matches.
  close        Close one subject.
  fold         Drop watch-outs only when the revision still matches.
  view         Print the derived view. It is not saved.

memory board <verb> -h
`,
  'board read': `memory board read — print the canonical board

usage: memory board read --file PATH [--section SECTION]

SECTION is one of: ${SECTIONS.join(', ')}
Success: revision, then the text, on stdout. Exit 0.
Refusal: the reason on stderr. Exit 1. Nothing is written.
`,
  'board write': `memory board write — checked board write

usage: memory board write --file PATH --revision REV --from FILE

The revision comes from memory board read. A stale revision is refused.
Success: path and changed on stdout. Exit 0.
`,
  'board close': `memory board close — close one subject

usage: memory board close --file PATH --subject TITLE --outcome TEXT --agent SLUG [--thread LINK]
`,
  'board fold': `memory board fold — fold watch-outs

usage: memory board fold --file PATH --revision REV --from FILE

A simultaneous correction changes the revision. This command then refuses and leaves that correction in the file.
`,
  'board view': `memory board view — derived excerpt

usage: memory board view --file PATH

The view starts with "Board view" and is not the board. It is not saved.
`,
  prepare: `memory prepare — identity-safe bundle

usage: memory prepare --installation ROOT [--agent-home PATH] [--cwd PATH]

Returns the bundle, the resolved identity and warnings. It does not infer another agent from the working directory.
`,
  validate: `memory validate — whole-proposal check

usage: memory validate --installation ROOT --proposal FILE

Does not publish. Exit 0 when every checked requirement passes.
Exit 1 and a JSON list of failures otherwise. Each failure names path, operation, requirement, expected and reason.
Proposal structure is taught by the consolidation tool's -h.
`,
  publish: `memory publish — validate and publish

usage: memory publish --installation ROOT --proposal FILE --input FILE

--input is the snapshot JSON the proposal was written against: {agent, date, messages, files}.
The lock is held only for the publish step. A refusal publishes nothing and keeps the proposal bytes.
`,
  remember: `memory remember — append an owner fact

usage: memory remember --installation ROOT --agent SLUG [--thread LINK] TEXT

With --evidence FILE, missing verification stores a pending candidate and does not append a durable claim.
`,
  commitment: `memory commitment — shared commitments

  add          Create one open commitment.
  complete     Mark done from an explicit statement or an artifact.
  cancel       Mark cancelled from an explicit statement or an artifact.
  annotate     Store an agent self-report on the open item.

memory commitment <verb> -h
`,
  'commitment add': `usage: memory commitment add --installation ROOT --debtor NAME --creditor NAME --action TEXT --sources TEXT [--due-at WHEN]
`,
  'commitment complete': `usage: memory commitment complete --installation ROOT --id ID (--statement TEXT | --artifact PATH)
`,
  'commitment cancel': `usage: memory commitment cancel --installation ROOT --id ID (--statement TEXT | --artifact PATH)
`,
  'commitment annotate': `usage: memory commitment annotate --installation ROOT --id ID --note TEXT
`,
  evidence: `memory evidence — attributable intake

usage: memory evidence --installation ROOT --agent SLUG --file JSON

JSON fields: sourceKind, sourceRef, author, quote, connector.accessible or artifact, observed.
Missing verification stays pending. Observed text is not stored as a remember request.
`,
  rule: `memory rule — approved global learned rules

usage: memory rule publish --installation ROOT --file PATH --approval REF

Refuses when --approval is missing, and when --migrated is set.
`,
  limit: `memory limit — record limits

usage: memory limit --kind KIND --file PATH

Always-loaded profile and learned rules stay hard limits. On-demand collections warn at 100 nonempty lines and split at 300.
`,
};

function helpFor(key) {
  process.stdout.write(HELP[key] || HELP.root);
  process.exit(0);
}

function readFile(flag, argv) {
  const file = option(argv, flag);
  if (!file) fail(`${flag} is required\nmemory -h`);
  return fs.readFileSync(file, 'utf8');
}

function boardFile(argv) {
  const file = option(argv, '--file');
  if (!file) fail('--file is required\nmemory board -h');
  return file;
}

function run(argv) {
  if (!argv.length || wantHelp(argv) && argv.length === 1) helpFor('root');
  const [verb, ...rest] = argv;
  if (wantHelp([verb, ...rest]) && rest.length === 0 && verb !== 'board' && verb !== 'commitment') helpFor(verb);
  if (verb === 'board') {
    if (!rest.length || wantHelp(rest) && rest.length === 1 && rest[0].startsWith('-')) helpFor('board');
    const action = rest[0];
    const tail = rest.slice(1);
    if (wantHelp(tail) || wantHelp([action])) helpFor(`board ${action}`);
    const file = boardFile(tail);
    if (action === 'read') {
      const loaded = lib.readBoard(file);
      const section = option(tail, '--section');
      let text = loaded.text;
      if (section) {
        if (!SECTIONS.includes(section)) fail(`unknown section: ${section}\nmemory board read -h`);
        const parsed = lib.parseBoard(text);
        const index = SECTIONS.indexOf(section);
        const block = parsed.lines.slice(parsed.sections[index].start, parsed.sections[index].end).join('\n');
        text = `${block}\n`;
      }
      emit({ path: file, revision: loaded.revision, section: section || null, text }, `${loaded.revision}\n${text}`);
      return;
    }
    if (action === 'view') {
      const text = lib.renderBoardView(fs.readFileSync(file, 'utf8'), file);
      emit({ path: file, saved: false, text }, text);
      return;
    }
    if (action === 'write' || action === 'fold') {
      const revision = option(tail, '--revision');
      const from = option(tail, '--from');
      if (!revision || !from) fail('--revision and --from are required\nmemory board -h');
      const fn = action === 'fold' ? lib.foldBoard : lib.writeBoard;
      const result = fn(file, fs.readFileSync(from, 'utf8'), { revision });
      emit(result, `${result.changed ? 'written' : 'unchanged'} ${result.path}\n`);
      return;
    }
    if (action === 'close') {
      const result = lib.closeSubject(file, option(tail, '--subject'), option(tail, '--outcome'), {
        agent: option(tail, '--agent'), thread: option(tail, '--thread'),
      });
      emit(result, `closed ${result.subject} in ${result.path}\n`);
      return;
    }
    fail(`unknown board verb: ${action}\nmemory board -h`);
  }
  if (verb === 'prepare') {
    if (wantHelp(rest)) helpFor('prepare');
    const result = lib.prepareMemory({
      installation: option(rest, '--installation'),
      agentHome: option(rest, '--agent-home'),
      cwd: option(rest, '--cwd'),
    });
    emit(result, `identity ${result.identity.agentHome || 'shared'}\nwarnings ${result.warnings.length}\n`);
    return;
  }
  if (verb === 'validate' || verb === 'publish') {
    if (wantHelp(rest)) helpFor(verb);
    const installation = option(rest, '--installation');
    const proposal = readFile('--proposal', rest);
    if (verb === 'validate') {
      let raw = proposal;
      try { raw = JSON.parse(proposal); } catch { /* validateProposal reports the JSON failure */ }
      const input = option(rest, '--input') ? JSON.parse(readFile('--input', rest)) : { agent: 'master', date: '2026-10-13', messages: [], files: {} };
      const result = lib.validateProposalResult(input, raw, installation);
      if (!result.ok) {
        emit({ ok: false, failures: result.failures }, '');
        if (!process.argv.includes('--json')) process.stderr.write(`${result.failures.map((row) => row.reason).join('\n')}\n`);
        process.exit(1);
      }
      emit({ ok: true, failures: [] }, 'proposal passed\n');
      return;
    }
    const input = JSON.parse(readFile('--input', rest));
    let raw = proposal;
    try { raw = JSON.parse(proposal); } catch { raw = proposal; }
    const result = lib.publishProposal(input, raw, installation);
    if (!result.ok) {
      emit({ ok: false, failures: result.failures, retained: result.retained }, '');
      if (!process.argv.includes('--json')) process.stderr.write(`${result.failures.map((row) => row.reason).join('\n')}\n`);
      process.exit(1);
    }
    emit(result, `published ${result.commit || 'unchanged'}\n`);
    return;
  }
  if (verb === 'remember') {
    if (wantHelp(rest)) helpFor('remember');
    const installation = option(rest, '--installation');
    const agent = option(rest, '--agent');
    const evidenceFile = option(rest, '--evidence');
    const text = rest.filter((word, index) => rest[index - 1] !== '--installation' && rest[index - 1] !== '--agent' && rest[index - 1] !== '--thread' && rest[index - 1] !== '--evidence' && !word.startsWith('--')).join(' ');
    const evidence = evidenceFile ? JSON.parse(fs.readFileSync(evidenceFile, 'utf8')) : null;
    const result = lib.remember(installation, text, { agent, thread: option(rest, '--thread'), evidence });
    emit(result, result.pending ? `pending ${result.path}\n` : `remembered in ${result.path}\n`);
    return;
  }
  if (verb === 'commitment') {
    const action = rest[0];
    const tail = rest.slice(1);
    if (!action || wantHelp(tail)) helpFor(action ? `commitment ${action}` : 'commitment');
    const installation = option(tail, '--installation');
    if (action === 'add') {
      const result = lib.createCommitment(installation, {
        debtor: option(tail, '--debtor'), creditor: option(tail, '--creditor'),
        action: option(tail, '--action'), sources: option(tail, '--sources'), due_at: option(tail, '--due-at') || '',
      });
      emit(result, `commitment ${result.id} open\n`);
      return;
    }
    if (action === 'annotate') {
      const result = lib.annotateCommitment(installation, option(tail, '--id'), option(tail, '--note'));
      emit(result, `annotated ${result.id}\n`);
      return;
    }
    if (action === 'complete' || action === 'cancel') {
      const result = lib.setCommitmentStatus(installation, option(tail, '--id'), action === 'complete' ? 'done' : 'cancelled', {
        statement: option(tail, '--statement'), artifact: option(tail, '--artifact'), actor: option(tail, '--actor'),
      });
      emit(result, `${result.status} ${result.id}\n`);
      return;
    }
    fail(`unknown commitment verb: ${action}\nmemory commitment -h`);
  }
  if (verb === 'evidence') {
    if (wantHelp(rest)) helpFor('evidence');
    const evidence = JSON.parse(readFile('--file', rest));
    const result = lib.intakeEvidence(option(rest, '--installation'), evidence.quote, {
      agent: option(rest, '--agent'), evidence,
    });
    emit(result, result.pending ? `pending ${result.path}\n` : `remembered in ${result.path}\n`);
    return;
  }
  if (verb === 'rule') {
    if (rest[0] !== 'publish' || wantHelp(rest)) helpFor('rule');
    const result = lib.publishGlobalRule(option(rest, '--installation'), readFile('--file', rest), {
      approval: option(rest, '--approval'), migrated: rest.includes('--migrated'),
    });
    emit(result, `published ${result.path}\n`);
    return;
  }
  if (verb === 'limit') {
    if (wantHelp(rest)) helpFor('limit');
    const kind = option(rest, '--kind');
    const text = readFile('--file', rest);
    const result = lib.checkLimits(kind, text);
    emit(result, `${result.hard ? 'refused' : 'checked'} ${kind}\n`);
    if (result.hard) process.exit(1);
    return;
  }
  if (verb === 'migrate') {
    process.exitCode = require('./migrate.js').main(rest);
    return;
  }
  fail(`unknown command: ${verb}\nmemory -h`);
}

try { run(process.argv.slice(2)); }
catch (error) {
  const failures = error.failures;
  if (failures) {
    emit({ ok: false, failures }, '');
    if (!process.argv.includes('--json')) process.stderr.write(`${failures.map((row) => row.reason).join('\n')}\n`);
  } else process.stderr.write(`${error.message}\n`);
  process.exit(1);
}
