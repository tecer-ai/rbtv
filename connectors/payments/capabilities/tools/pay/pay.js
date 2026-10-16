#!/usr/bin/env node
'use strict';

// pay — the port command of the payments port (connectors/payments): an agent pays by Pix key, QR code,
// bill or mobile top-up from a named account through Ignite's payment gate, reads, withdraws and fetches
// the receipt of its own requests, and lists the accounts it may pay from. Every paying verb names the
// account money leaves (--from) and the destination; nothing is defaulted. pay resolves the recipient
// through the account's connector command (`<connector> --json pay resolve draft`, the draft on stdin),
// records the request with `ignite --json payment request --connector NAME --request -` and prints the
// gate's answer; it never calls a paying endpoint (Ignite's waking service does, through the connector).
// Specification: the connector architecture's spec-pay.md (phase 2, 2026-10-16); `pay -h` is the reference.
//
// API
// main(argv, deps?) → Promise<exit code>. deps: cwd, env, stdout(text), stderr(text), run(command, args,
//   input) → { code, stdout, stderr } (the connector's command and ignite, run with execFile by default),
//   which(name) → the command's path or null, root (the repository, for Ignite's adapter loader). Exit 0
//   success, including a payment that waits for the owner (pending); 1 refused or failed (three stderr lines
//   `pay: WHAT`, `  why:`, `  fix:`), and for a request the gate refused, failed or that was cancelled; 2
//   invalid words (same form). --json: one object on stdout for a success; a refusal changes nothing.
// The accounts are read through Ignite's own config reader (core/ignite/.../config.js loadConfig and
// paymentsConfig, found from root), so a file Ignite refuses is refused here with Ignite's message and both
// spellings of the list are read as Ignite reads them; pay keeps no reading of its own.

const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');

const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const VERBS = ['pix', 'qr', 'bill', 'recharge', 'list', 'show', 'cancel', 'receipt', 'accounts'];
const PAYING = ['pix', 'qr', 'bill', 'recharge'];
const STATES = ['pending', 'approved', 'sent', 'uncertain', 'refused', 'cancelled', 'failed'];
const KEY_TYPES = ['CPF', 'CNPJ', 'EMAIL', 'PHONE', 'EVP'];
const OPTIONS = {
  pix: { from: 'value', to: 'value', amount: 'value', note: 'value', type: 'value' },
  qr: { from: 'value', code: 'value', amount: 'value', note: 'value' },
  bill: { from: 'value', line: 'value', note: 'value' },
  recharge: { from: 'value', number: 'value', amount: 'value', note: 'value' },
  list: { state: 'value' },
  show: {},
  cancel: {},
  receipt: { out: 'value' },
  accounts: {},
};
const NOTE_MAX = 140;
const QR_MAX = 2000;
const WAIT_ENV = 'PAY_GATE_WAIT';
const RUN_MS = 60_000;

class Refusal extends Error {
  constructor(what, why, fix, code = 1) {
    super(what);
    this.what = what; this.why = why; this.fix = fix; this.exitCode = code;
  }
}
const refuse = (what, why, fix) => new Refusal(what, why, fix, 1);
const invalid = (what, why, fix) => new Refusal(what, why, fix, 2);

// ───────────────────────────────────────────────────────────── money and words

function brl(cents) {
  if (cents == null) return '-';
  const sign = cents < 0 ? '-' : '';
  const abs = Math.abs(cents);
  const whole = String(Math.floor(abs / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `${sign}R$ ${whole},${String(abs % 100).padStart(2, '0')}`;
}

// The first lines of the value refusals are the specification's literal words (S11): an amount, note or
// key-form refusal names the option alone; qr, bill and recharge name the verb with a colon.
function amountCents(text, verb) {
  const match = String(text).trim().match(/^(\d{1,9})(?:[.,](\d{1,2}))?$/);
  if (!match) throw invalid(`--amount "${text}" is not an amount in reais (like 99 or 99,90)`, 'the amount is reais with up to two decimals', `pay ${verb} -h`);
  const cents = Number(match[1]) * 100 + Number((match[2] || '0').padEnd(2, '0'));
  if (cents === 0) throw invalid(`--amount ${text} is below R$ 0,01`, 'a payment moves at least one cent', `pay ${verb} -h`);
  return cents;
}

function noteText(text, verb) {
  const value = String(text).trim();
  if (!value) throw invalid('--note is empty', 'the recipient and the owner read the note', `pay ${verb} -h`);
  if ([...value].length > NOTE_MAX) throw invalid(`--note is longer than ${NOTE_MAX} characters`, `the recipient sees the note; the bank takes ${NOTE_MAX} characters`, `pay ${verb} -h`);
  if (/[\r\n]/.test(value)) throw invalid('--note must be one line', 'the recipient sees the note on one line', `pay ${verb} -h`);
  return value;
}

function parse(argv) {
  const words = [...argv];
  let json = false;
  let help = false;
  let verb = null;
  const opts = {};
  const positionals = [];
  const unknownVerb = (word) => invalid(`unknown command "${word}"; the commands are ${VERBS.join(', ')}`, 'the first word is the command', 'pay -h');
  for (let i = 0; i < words.length; i++) {
    let word = words[i];
    if (word === '-h' || word === '--help') { help = true; continue; }
    if (word === '--json') { json = true; continue; }
    if (word.startsWith('--') && word.length > 2) {
      let value = null;
      const eq = word.indexOf('=');
      if (eq > 0) { value = word.slice(eq + 1); word = word.slice(0, eq); }
      const name = word.slice(2);
      if (!verb) throw unknownVerb(word);
      if (!(name in OPTIONS[verb])) throw invalid(`${verb} has no option --${name}`, `the options of ${verb} are: ${Object.keys(OPTIONS[verb]).map((o) => `--${o}`).join(', ') || 'none beside --json'}`, `pay ${verb} -h`);
      if (value == null) {
        if (i + 1 >= words.length) throw invalid(`--${name} needs a value`, `${verb} takes --${name} with a value`, `pay ${verb} -h`);
        value = words[++i];
      }
      if (name in opts) throw invalid(`--${name} is given twice`, 'each option is given once', `pay ${verb} -h`);
      opts[name] = value;
      continue;
    }
    if (!verb) {
      if (!VERBS.includes(word)) throw unknownVerb(word);
      verb = word;
      continue;
    }
    positionals.push(word);
  }
  return { json, help, verb, opts, positionals };
}

function parseOrHelp(argv) {
  try { return parse(argv); } catch (error) {
    if (argv.includes('-h') || argv.includes('--help')) return { json: false, help: true, verb: argv.find((w) => VERBS.includes(w)) || null, opts: {}, positionals: [] };
    throw error;
  }
}

// ───────────────────────────────────────────────────────────── help

const ROOT_HELP = `usage: pay [-h] [--json] COMMAND ...

Pays from a named account through Ignite's payment gate: the owner's limits or
the owner's approval decide, never the agent. Every paying verb names the
account money leaves (--from) and the destination; nothing is defaulted or
guessed. The port command of the payments port: it resolves the recipient
through the account's connector (asaas today), records the request with
ignite payment request, and prints the gate's answer. Run inside an Ignite
turn: the outcome wakes this conversation.

positional arguments:
  COMMAND
    pix       Pix to a key: looks up its owner, then asks the gate
    qr        a Pix QR code (copy and paste text): decodes it, then asks
    bill      a boleto or utility bill: simulates it (amount and fee), then asks
    recharge  a mobile top-up: asks the gate to credit a phone
    list      this agent's payment requests, newest first
    show      one request: state, connector id, receipt link
    cancel    withdraw a pending request, or cancel a sent Pix or bill at the
              bank while it can be
    receipt   save a payment's receipt as PDF
    accounts  the accounts --from may name, and their connectors

options:
  -h, --help  show this help message and exit
  --json      one JSON object on stdout instead of text

Exit codes: 0 success, including a payment that waits for the owner (pending);
1 refused or failed (stderr says why and the fix); 2 invalid arguments.
Start: pay accounts, then pay pix -h
`;

const FROM = `  --from ACCOUNT   the account money leaves (pay accounts lists them); required`;
const HELP = {
  pix: `usage: pay pix [-h] [--json] --from ACCOUNT --to KEY --amount VALUE --note TEXT
               [--type {CPF,CNPJ,EMAIL,PHONE,EVP}]

Looks up the key's owner through the account's connector, records the request
with Ignite's payment gate and prints its answer: sent (approved by the
owner's limits and sent by Ignite), pending (waits for the owner: end the turn
waiting_workers, Ignite wakes this conversation with the outcome) or refused.

options:
  -h, --help       show this help message and exit
${FROM}
  --to KEY         the Pix key: email, +55 phone, CPF, CNPJ or random key;
                   required
  --amount VALUE   reais, like 99 or 99,90; required
  --note TEXT      what it is for, up to 140 characters; the recipient sees it
  --type TYPE      needed only when 11 digits could be a CPF or a phone

Example: pay pix --from asaas --to pia@example.com --amount 18,00 --note "Aula"
Next: pay show P-0007
`,
  qr: `usage: pay qr [-h] [--json] --from ACCOUNT --code PAYLOAD --note TEXT [--amount VALUE]

Decodes the QR code through the account's connector (receiver, amount),
records the request with Ignite's payment gate and prints its answer: sent,
pending (end the turn waiting_workers; Ignite wakes this conversation) or
refused.

options:
  -h, --help       show this help message and exit
${FROM}
  --code PAYLOAD   the copy-and-paste text, starts 000201, up to 2,000
                   characters; required
  --note TEXT      what it is for, up to 140 characters; required
  --amount VALUE   reais: needed when the QR code carries no amount; refused
                   when the code fixes another amount

Example: pay qr --from asaas --code 000201... --note "Pão"
Next: pay show P-0008
`,
  bill: `usage: pay bill [-h] [--json] --from ACCOUNT --line DIGITS --note TEXT

Simulates the bill through the account's connector, records the request with
Ignite's payment gate and prints its answer: sent, pending (end the turn
waiting_workers; Ignite wakes this conversation) or refused.
Prints the simulation (amount, fee, due date) before the gate's answer; amount
plus fee counts toward the limits.

options:
  -h, --help       show this help message and exit
${FROM}
  --line DIGITS    the digitable line, 47 or 48 digits, spaces and dots
                   allowed; required
  --note TEXT      what it is for, up to 140 characters; required

Example: pay bill --from asaas --line "23793.38128 60000.000003 ..." --note "Luz"
Next: pay show P-0007
`,
  recharge: `usage: pay recharge [-h] [--json] --from ACCOUNT --number PHONE --amount VALUE --note TEXT

Asks Ignite's payment gate to credit a mobile phone through the account's
connector and prints its answer: sent, pending (end the turn waiting_workers;
Ignite wakes this conversation) or refused.

options:
  -h, --help       show this help message and exit
${FROM}
  --number PHONE   11 digits with the area code, +55 optional, quoted when it
                   has spaces; required
  --amount VALUE   reais; the operator's top-up values apply (the service
                   refuses others); required
  --note TEXT      what it is for, up to 140 characters; required

Example: pay recharge --from asaas --number 11912345678 --amount 20,00 --note "Celular"
Next: pay show P-0009
`,
  list: `usage: pay list [-h] [--json] [--state {pending,approved,sent,uncertain,refused,cancelled,failed}]

The 20 newest requests of this agent, one line each; --state keeps one.

options:
  -h, --help     show this help message and exit
  --state STATE  one of pending, approved, sent, uncertain, refused, cancelled,
                 failed

--json: {"payments": [request, ...]} as ignite payment request -h describes.
`,
  show: `usage: pay show [-h] [--json] ID

One request of this agent: recipient, amount, state, connector id and status,
receipt link.

positional arguments:
  ID          a request id such as P-0007, of this agent

options:
  -h, --help  show this help message and exit

--json: the request, as ignite payment request -h describes.
`,
  cancel: `usage: pay cancel [-h] [--json] ID

Withdraws a pending request; cancels a sent Pix or bill at the bank through its
connector while it can be.

positional arguments:
  ID          a request id such as P-0007, of this agent

options:
  -h, --help  show this help message and exit

--json: the request, or {"id", "connector_id", "status"} for a bank cancel.
`,
  receipt: `usage: pay receipt [-h] [--json] [--out PATH] REF

Saves the receipt PDF of a sent request (REF: its id, or a receipt link);
default <ID>.pdf here, never overwritten.

positional arguments:
  REF         a request id such as P-0007, or the receipt link pay show gives

options:
  -h, --help  show this help message and exit
  --out PATH  the PDF file to write; never overwritten

--json: {"path", "bytes", "receipt_url"}.
`,
  accounts: `usage: pay accounts [-h] [--json]

The accounts --from may name: name, connector, whether its command and
withdrawal validation adapter are found. No network.

options:
  -h, --help  show this help message and exit

--json: {"accounts": [{"name", "connector", "command", "adapter"}]}.
`,
};

// ───────────────────────────────────────────────────────────── the installation and its accounts

function findInstallation(start) {
  let dir = path.resolve(start);
  for (;;) {
    if (fs.existsSync(path.join(dir, '.rbtv', 'config', 'install.json'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

// The payments section of Ignite's config, read and validated by Ignite's own reader: null when the file or
// the section is absent; { connectors } with Ignite's defaults and spellings otherwise; a file Ignite refuses
// is refused here with Ignite's message, so pay and the gate never disagree about the same file.
function paymentsSection(ctx) {
  const file = ctx.installation ? path.join(ctx.installation, '.rbtv', 'config', 'ignite', 'config.json') : null;
  if (!file || !fs.existsSync(file)) return null;
  const { loadConfig, paymentsConfig } = require(path.join(ctx.root, 'core', 'ignite', 'capabilities', 'tools', 'ignite', 'config.js'));
  let config;
  try { config = loadConfig(ctx.installation); } catch (error) {
    throw refuse(`Ignite refuses its config: ${error.message}`, `pay reads the accounts through Ignite's own config reader (${file}), so both refuse the same file`, "the owner fixes the file; until then Ignite's gate refuses too");
  }
  const section = paymentsConfig(config);
  return section ? { connectors: section.connectors } : null;
}

function defaultWhich(name) {
  const exts = process.platform === 'win32' ? (process.env.PATHEXT || '.COM;.EXE;.BAT;.CMD').split(';') : [''];
  for (const dir of (process.env.PATH || '').split(path.delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const candidate = path.join(dir, name + ext.toLowerCase());
      try { if (fs.statSync(candidate).isFile()) return candidate; } catch { /* next */ }
      const upper = path.join(dir, name + ext);
      try { if (ext && fs.statSync(upper).isFile()) return upper; } catch { /* next */ }
    }
  }
  return null;
}

function defaultRun(command, args, input) {
  try {
    const stdout = execFileSync(command, args, { input: input ?? '', encoding: 'utf8', timeout: RUN_MS, maxBuffer: 4 * 1024 * 1024, windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
    return { code: 0, stdout, stderr: '' };
  } catch (error) {
    return { code: typeof error.status === 'number' ? error.status : 1, stdout: String(error.stdout || ''), stderr: String(error.stderr || error.message || '') };
  }
}

function adapterLoads(ctx, connector) {
  try {
    const { loadConnector } = require(path.join(ctx.root, 'core', 'ignite', 'capabilities', 'tools', 'ignite', 'payment-webhook.js'));
    loadConnector(connector, { root: ctx.root });
    return true;
  } catch { return false; }
}

// ───────────────────────────────────────────────────────────── the gate and the connector

async function ignite(ctx, args, input, { fix } = {}) {
  const found = ctx.which('ignite');
  if (!found) throw refuse('the ignite command is not on PATH', "pay pays only through Ignite's payment gate", "run pay inside an Ignite agent's turn");
  let result;
  try { result = await ctx.run(found, ['--json', 'payment', ...args], input); } catch (error) {
    throw refuse("could not run Ignite's payment gate", error.message, 'run the same command again; tell the owner if it persists');
  }
  if (result.code !== 0) {
    const lines = String(result.stderr || result.stdout || '').split(/\r?\n/).filter((l) => l.trim());
    const first = lines[0] || `exit ${result.code}`;
    if (/no payments section/.test(first)) {
      throw refuse("Ignite's payment gate: config has no payments section", 'nothing was recorded or changed', 'the owner sets up payments (runbook); pay accounts shows the state');
    }
    if (/^unknown payment request: /.test(first)) {
      throw refuse(first, "pay list lists this agent's request ids; an id it does not list is another agent's or does not exist", 'pay list');
    }
    throw refuse(`Ignite's payment gate: ${first}`, 'nothing was recorded or changed', fix || "pay list lists this agent's requests");
  }
  try { return JSON.parse(result.stdout); } catch {
    throw refuse("Ignite's payment gate answered something that is not JSON", String(result.stdout).slice(0, 200), 'tell the owner');
  }
}

async function connectorCommand(ctx, account, args, input, verb) {
  const found = ctx.which(account.connector);
  if (!found) {
    throw refuse(`${verb} refused: the account ${account.name} has no command on PATH`, `the ${account.connector} connector is not installed here (rbtv list --installed)`, `rbtv add connectors/${account.connector}`);
  }
  let result;
  try { result = await ctx.run(found, args, input); } catch (error) {
    throw refuse(`${account.connector} could not run`, error.message, 'run the same command again');
  }
  return result;
}

// A connector's refusal passes through: its three lines with `pay:` in front of the first.
function passThrough(result, connector) {
  const lines = String(result.stderr || result.stdout || '').split(/\r?\n/).filter((l) => l.trim());
  const what = (lines[0] || `${connector}: exit ${result.code}`).replace(/^\s+/, '');
  const why = (lines.find((l) => /^\s*why:/.test(l)) || '  why: the connector gave no reason').replace(/^\s*why:\s*/, '');
  const fix = (lines.find((l) => /^\s*fix:/.test(l)) || '  fix: run the same command again').replace(/^\s*fix:\s*/, '');
  return refuse(what, why, fix);
}

function accountOf(ctx, section, name, verb) {
  if (!section.connectors.includes(name)) {
    throw refuse(`${verb} refused: no account named "${name}"`, `the accounts are the entries of Ignite's payments configuration: ${section.connectors.join(', ')}`, `pay ${verb} --from ${section.connectors[0]} …   (pay accounts)`);
  }
  return { name, connector: name };
}

async function resolveDraft(ctx, account, draft) {
  const result = await connectorCommand(ctx, account, ['--json', 'pay', 'resolve', 'draft'], JSON.stringify({ connector: account.connector, ...draft }), draft.method);
  if (result.code !== 0) throw passThrough(result, account.connector);
  let body;
  try { body = JSON.parse(String(result.stdout).trim().split('\n').pop()); } catch {
    throw refuse(`${account.connector} answered something that is not JSON`, String(result.stdout).slice(0, 200), 'tell the owner');
  }
  if (!body?.recipient?.key) throw refuse(`${account.connector} resolved no recipient`, JSON.stringify(body).slice(0, 200), 'tell the owner');
  return body;
}

// ───────────────────────────────────────────────────────────── the gate's answer

function stateLine(row) {
  const { state, reason } = row;
  if (state === 'sent') return row.decided_by === 'owner' ? 'sent: approved by the owner' : `sent: approved by rule (${reason || 'within the limits'})`;
  if (state === 'approved') return 'approved: Ignite is sending it';
  return reason ? `${state}: ${reason}` : state;
}

function requestLine(row) {
  const { id, state } = row;
  if (state === 'pending') return `${id}, sent to the owner for approval`;
  if (state === 'approved' || state === 'uncertain') return `${id}, the outcome arrives in this conversation`;
  if (state === 'sent') return `${id}, ${row.connector} id ${row.connector_id}${row.receipt_url ? `, receipt ${row.receipt_url}` : ''}`;
  return id;
}

const who = (r) => [r.name, r.document, r.bank].filter(Boolean).join(' · ') || r.key || '-';

function report(io, json, row) {
  if (json) io.stdout(`${JSON.stringify(row)}\n`);
  else {
    const r = row.recipient || {};
    const amount = brl(row.amount_cents) + (row.fee_cents ? ` + fee ${brl(row.fee_cents)}` : '');
    const lines = [`Recipient   ${who(r)}`, `Amount      ${amount}`, `State       ${stateLine(row)}`, `Request     ${requestLine(row)}`];
    if (row.state === 'pending') lines.push(`Next        end this turn waiting_workers: Ignite wakes this conversation with the owner's decision; pay show ${row.id} shows it meanwhile`);
    else if (row.state === 'approved') lines.push(`Next        pay show ${row.id} shows when it is sent`);
    else if (row.state === 'uncertain') lines.push(`Next        do not ask again: Ignite reads it at the bank and wakes this conversation with the outcome; pay show ${row.id} shows it`);
    io.stdout(`${lines.join('\n')}\n`);
  }
  return ['refused', 'failed', 'cancelled'].includes(row.state) ? 1 : 0;
}

async function askGate(ctx, account, request) {
  let row = await ignite(ctx, ['request', '--connector', account.connector, '--request', '-'], JSON.stringify(request));
  const wait = Number(ctx.env[WAIT_ENV] ?? 30) || 0;
  const deadline = Date.now() + wait * 1000;
  while (row.state === 'approved' && Date.now() < deadline) {
    await ctx.sleep(Math.min(1000, Math.max(0, deadline - Date.now())));
    row = await ignite(ctx, ['show', row.id]);
  }
  return row;
}

// ───────────────────────────────────────────────────────────── the paying verbs

function requireFrom(opts, verb, example) {
  if (opts.from === undefined) throw invalid(`${verb} refused: --from ACCOUNT is required`, 'pay never picks the account money leaves; name it, even when one is configured', `${example}   (pay accounts lists the accounts)`);
  if (!String(opts.from).trim()) throw invalid(`${verb} refused: --from is empty`, 'pay never picks the account money leaves', `pay ${verb} -h`);
}

function requireNote(opts, verb) {
  if (opts.note === undefined) throw invalid(`${verb} refused: --note TEXT is required`, 'every payment says what it is for; the recipient and the owner read it', `pay ${verb} -h`);
  return noteText(opts.note, verb);
}

function inTurn(ctx, verb) {
  if (!ctx.env.IGNITE_CONVERSATION) {
    throw refuse(`pay ${verb} runs inside an Ignite turn`, 'IGNITE_CONVERSATION is not set, so no conversation can be woken with the outcome', "pay from an agent's turn; a person pays in the bank's app");
  }
}

async function payingContext(ctx, opts, verb) {
  inTurn(ctx, verb);
  if (!ctx.which('ignite')) throw refuse('the ignite command is not on PATH', "pay pays only through Ignite's payment gate", "run pay inside an Ignite agent's turn");
  const section = paymentsSection(ctx);
  if (!section) throw refuse("Ignite's payment gate: config has no payments section", 'nothing was recorded or changed', 'the owner sets up payments (runbook); pay accounts shows the state');
  return accountOf(ctx, section, String(opts.from).trim(), verb);
}

async function doPix(io, parsed, ctx) {
  const { opts, json } = parsed;
  const example = `pay pix --from ${opts.from || 'asaas'} --to ${opts.to || 'KEY'} --amount ${opts.amount || 'VALUE'} --note "${opts.note || 'TEXT'}"`;
  requireFrom(opts, 'pix', example);
  if (opts.to === undefined) throw invalid('pix refused: --to KEY is required', 'the destination is never guessed', example);
  const key = String(opts.to).trim();
  if (!key) throw invalid('pix refused: --to is empty', 'the destination is never guessed', example);
  if (key.startsWith('000201')) throw invalid(`--to ${key.slice(0, 12)}… is a Pix QR code (copy and paste), not a Pix key`, 'a QR code is paid as a QR code', `pay qr --from ${opts.from} --code PAYLOAD --note TEXT`);
  if (opts.amount === undefined) throw invalid('pix refused: --amount VALUE is required', 'the amount is never guessed', example);
  const amount = amountCents(opts.amount, 'pix');
  const note = requireNote(opts, 'pix');
  let type = null;
  if (opts.type !== undefined) {
    type = String(opts.type).toUpperCase();
    if (!KEY_TYPES.includes(type)) throw invalid(`pix refused: --type ${opts.type} is not one of ${KEY_TYPES.join(', ')}`, 'the key type decides whom the bank looks up', 'pay pix -h');
  }
  const digits = key.replace(/\D/g, '');
  if (!type && !/[a-z@]/i.test(key) && !key.startsWith('+') && digits.length === 11 && !/-/.test(key)) {
    throw invalid(`pix refused: ${key} may be a CPF or a phone`, 'both are 11 digits; the key type decides whom the bank looks up', 'add --type CPF or --type PHONE');
  }
  const account = await payingContext(ctx, opts, 'pix');
  const resolved = await resolveDraft(ctx, account, { method: 'pix', recipient: { key, key_type: type }, amount_cents: amount, note });
  const row = await askGate(ctx, account, { method: 'pix', recipient: resolved.recipient, amount_cents: amount, fee_cents: resolved.fee_cents || 0, note, details: resolved.details || {} });
  return report(io, json, row);
}

async function doQr(io, parsed, ctx) {
  const { opts, json } = parsed;
  const example = `pay qr --from ${opts.from || 'asaas'} --code PAYLOAD --note TEXT`;
  requireFrom(opts, 'qr', example);
  if (opts.code === undefined) throw invalid('qr refused: --code PAYLOAD is required', 'the destination is never guessed', example);
  const code = String(opts.code).trim();
  if (!code.startsWith('000201')) throw invalid('qr: --code must start with 000201', "a Pix QR code's copy-and-paste text is one line that starts with 000201", example);
  if ([...code].length > QR_MAX || /[\r\n]/.test(code)) throw invalid(`qr refused: --code is longer than ${QR_MAX} characters or has line breaks`, 'the copy-and-paste text is one line', example);
  const note = requireNote(opts, 'qr');
  const amount = opts.amount === undefined ? null : amountCents(opts.amount, 'qr');
  const account = await payingContext(ctx, opts, 'qr');
  const resolved = await resolveDraft(ctx, account, { method: 'qr', recipient: { key: code, key_type: 'QR' }, amount_cents: amount, note });
  const fixed = resolved.amount_cents ?? null;
  if (fixed == null && amount == null) throw refuse('this QR code carries no amount', 'the payer chooses it', `pay qr --from ${account.name} --code PAYLOAD --amount 35,00 --note TEXT`);
  if (fixed != null && amount != null && amount !== fixed && !resolved.changeable) {
    throw refuse(`this QR code charges ${brl(fixed)}, not ${brl(amount)}`, 'its amount cannot be changed', `pay qr --from ${account.name} --code PAYLOAD --note TEXT   (without --amount)`);
  }
  const row = await askGate(ctx, account, { method: 'qr', recipient: resolved.recipient, amount_cents: amount ?? fixed, fee_cents: resolved.fee_cents || 0, note, details: resolved.details || {} });
  return report(io, json, row);
}

async function doBill(io, parsed, ctx) {
  const { opts, json } = parsed;
  const example = `pay bill --from ${opts.from || 'asaas'} --line DIGITS --note TEXT`;
  requireFrom(opts, 'bill', example);
  if (opts.line === undefined) throw invalid('bill refused: --line DIGITS is required', 'the destination is never guessed', example);
  const digits = String(opts.line).replace(/\D/g, '');
  if (digits.length !== 47 && digits.length !== 48) throw invalid(`bill: --line has ${digits.length} digits; a digitable line has 47 or 48`, 'a 44-digit barcode number is not accepted: copy the digitable line printed above it', example);
  const note = requireNote(opts, 'bill');
  const account = await payingContext(ctx, opts, 'bill');
  const resolved = await resolveDraft(ctx, account, { method: 'bill', recipient: { key: digits, key_type: null }, amount_cents: null, note });
  const amount = resolved.amount_cents;
  if (!Number.isInteger(amount) || amount <= 0) throw refuse('this bill has no amount to pay', `${account.connector}'s simulation returned no value for it`, 'pay a bill that carries its amount; a bill with an open amount is not supported');
  const fee = resolved.fee_cents || 0;
  const details = resolved.details || {};
  if (!json) io.stdout(`Simulated   bill ${brl(amount)}, fee ${brl(fee)}${details.due_date ? `, due ${details.due_date}` : ''}: ${brl(amount + fee)} counts toward the limits\n`);
  const row = await askGate(ctx, account, { method: 'bill', recipient: resolved.recipient, amount_cents: amount, fee_cents: fee, note, details });
  return report(io, json, row);
}

async function doRecharge(io, parsed, ctx) {
  const { opts, json } = parsed;
  const example = `pay recharge --from ${opts.from || 'asaas'} --number PHONE --amount VALUE --note TEXT`;
  requireFrom(opts, 'recharge', example);
  if (opts.number === undefined) throw invalid('recharge refused: --number PHONE is required', 'the destination is never guessed', example);
  let digits = String(opts.number).replace(/\D/g, '');
  if (digits.length === 13 && digits.startsWith('55')) digits = digits.slice(2);
  if (digits.length !== 11) throw invalid('recharge: a mobile number has 11 digits with its area code', 'like 11912345678 or "11 91234-5678" (quoted when it has spaces; +55 optional)', example);
  if (opts.amount === undefined) throw invalid('recharge refused: --amount VALUE is required', 'the amount is never guessed', example);
  const amount = amountCents(opts.amount, 'recharge');
  const note = requireNote(opts, 'recharge');
  const account = await payingContext(ctx, opts, 'recharge');
  const resolved = await resolveDraft(ctx, account, { method: 'recharge', recipient: { key: digits, key_type: 'PHONE' }, amount_cents: amount, note });
  const row = await askGate(ctx, account, { method: 'recharge', recipient: resolved.recipient, amount_cents: amount, fee_cents: resolved.fee_cents || 0, note, details: resolved.details || {} });
  return report(io, json, row);
}

// ───────────────────────────────────────────────────────────── the reads

async function doList(io, parsed, ctx) {
  const { opts, json } = parsed;
  if (parsed.positionals.length) throw invalid(`list takes no positional word: ${parsed.positionals.join(' ')}`, 'a state is chosen with --state', 'pay list -h');
  if (opts.state !== undefined && !STATES.includes(opts.state)) throw invalid(`list refused: --state ${opts.state} is not one of ${STATES.join(', ')}`, 'a state filters the list', 'pay list -h');
  const body = await ignite(ctx, ['list', ...(opts.state ? ['--state', opts.state] : [])]);
  const rows = body.payments || [];
  if (json) { io.stdout(`${JSON.stringify({ payments: rows })}\n`); return 0; }
  if (!rows.length) { io.stdout(`No ${opts.state ? `${opts.state} ` : ''}payment requests.\n`); return 0; }
  for (const r of rows) {
    io.stdout(`${r.id}  ${r.state.padEnd(9)} ${brl(r.amount_cents + (r.fee_cents || 0)).padStart(12)}  ${r.recipient?.name || r.recipient?.key}${r.reason ? `  (${r.reason})` : ''}\n`);
  }
  return 0;
}

function needId(parsed, verb, word = 'ID') {
  const id = parsed.positionals[0];
  if (!id) throw invalid(`${verb} refused: ${word} is required`, `${verb} takes one request id such as P-0007${word === 'REF' ? ', or a receipt link' : ''}`, `pay ${verb} -h`);
  if (parsed.positionals.length > 1) throw invalid(`${verb} takes one ${word}`, `${parsed.positionals.length} were given`, `pay ${verb} -h`);
  return id;
}

async function doShow(io, parsed, ctx) {
  const id = needId(parsed, 'show');
  const row = await ignite(ctx, ['show', id]);
  if (parsed.json) { io.stdout(`${JSON.stringify(row)}\n`); return 0; }
  const r = row.recipient || {};
  io.stdout([
    `Request     ${row.id}  ${row.method}`,
    `Recipient   ${who(r)}`,
    `Key         ${r.key}`,
    `Amount      ${brl(row.amount_cents)}${row.fee_cents ? ` + fee ${brl(row.fee_cents)}` : ''}`,
    `Note        ${row.note || '-'}`,
    `State       ${stateLine(row)}`,
    `Connector   ${row.connector}, id ${row.connector_id || '-'}${row.connector_status ? ` (${row.connector_status})` : ''}`,
    `Receipt     ${row.receipt_url || '-'}`,
  ].join('\n') + '\n');
  return 0;
}

async function doCancel(io, parsed, ctx) {
  const id = needId(parsed, 'cancel');
  const row = await ignite(ctx, ['show', id]);
  if (row.state === 'pending') {
    const cancelled = await ignite(ctx, ['cancel', id]);
    if (parsed.json) io.stdout(`${JSON.stringify(cancelled)}\n`);
    else io.stdout(`Cancelled   ${cancelled.id}: withdrawn before the owner decided\n`);
    return 0;
  }
  if (row.state === 'sent' && row.connector_id && ['pix', 'bill'].includes(row.method)) {
    const section = paymentsSection(ctx);
    const account = { name: row.connector, connector: row.connector };
    if (!section || !section.connectors.includes(row.connector)) throw refuse(`cancel refused: no account named "${row.connector}"`, `the accounts are the entries of Ignite's payments configuration: ${section ? section.connectors.join(', ') : 'none'}`, 'pay accounts');
    const result = await connectorCommand(ctx, account, ['--json', 'cancel', id], '', 'cancel');
    if (result.code !== 0) throw passThrough(result, row.connector);
    let body;
    try { body = JSON.parse(String(result.stdout).trim().split('\n').pop()); } catch { body = {}; }
    const operation = body.connector_id || body.provider_id || row.connector_id;
    if (parsed.json) io.stdout(`${JSON.stringify({ id, connector_id: operation, status: body.status ?? null })}\n`);
    else io.stdout(`Cancelled   ${id} at ${row.connector} (${operation}): ${body.status}\nThe gate counts it until Ignite reads the operation as cancelled.\n`);
    return 0;
  }
  if (row.state === 'sent') {
    throw refuse(`${id} is a ${row.method} payment ${row.connector} already has`, `${row.connector} cancels Pix key transfers and bills only`, "ask the owner to cancel it in the bank's app while it allows it");
  }
  throw refuse(`${id} is ${row.state}: nothing to cancel`, 'a pending request is withdrawn, a sent one is cancelled at the bank while it can be', `pay show ${id}`);
}

async function doReceipt(io, parsed, ctx) {
  const ref = needId(parsed, 'receipt', 'REF');
  const out = parsed.opts.out;
  let account;
  let args;
  if (/^P-\d+$/.test(ref)) {
    const row = await ignite(ctx, ['show', ref]);
    if (!row.receipt_url) throw refuse(`${ref} has no receipt yet`, `it is ${row.state}; the bank gives a receipt once the payment is done`, `pay show ${ref} shows when it has one`);
    account = { name: row.connector, connector: row.connector };
    args = ['receipt', ref];
  } else if (/^https?:\/\//.test(ref)) {
    const section = paymentsSection(ctx);
    if (!section) throw refuse('no accounts', "Ignite's config.json has no payments section, so the gate is not set up", 'the owner adds "payments": {} and restarts the service (runbook)');
    account = { name: section.connectors[0], connector: section.connectors[0] };
    args = ['receipt', ref];
  } else {
    throw refuse(`${ref} is neither a request id nor a receipt link`, 'a receipt is fetched by the request id (P-0007) or by the link pay show gives', 'pay receipt P-0007, or pay receipt https://…');
  }
  const target = path.resolve(ctx.cwd, out || `${ref.startsWith('P-') ? ref : 'receipt'}.pdf`);
  if (fs.existsSync(target)) throw refuse(`${target} already exists`, 'the receipt is never written over a file', 'pass --out with another path');
  const result = await connectorCommand(ctx, account, [...(parsed.json ? ['--json'] : []), ...args, '--out', target], '', 'receipt');
  if (result.code !== 0) throw passThrough(result, account.connector);
  io.stdout(result.stdout);
  return 0;
}

async function doAccounts(io, parsed, ctx) {
  if (parsed.positionals.length) throw invalid('accounts takes no argument', 'it lists the accounts of this installation', 'pay accounts');
  const section = paymentsSection(ctx);
  if (!section) throw refuse('no accounts', "Ignite's config.json has no payments section, so the gate is not set up", 'the owner adds "payments": {} and restarts the service (runbook); until then pay refuses every payment');
  const accounts = section.connectors.map((name) => ({ name, connector: name, command: Boolean(ctx.which(name)), adapter: adapterLoads(ctx, name) }));
  if (parsed.json) { io.stdout(`${JSON.stringify({ accounts })}\n`); return 0; }
  const w = Math.max(7, ...accounts.map((a) => a.name.length));
  io.stdout(`${'Account'.padEnd(w + 3)}${'Connector'.padEnd(12)}${'Command'.padEnd(10)}Adapter\n`);
  for (const a of accounts) {
    io.stdout(`${a.name.padEnd(w + 3)}${a.connector.padEnd(12)}${(a.command ? 'found' : 'missing').padEnd(10)}${a.adapter ? 'found (lib/withdrawal-validation.js)' : 'missing'}\n`);
  }
  return 0;
}

const DO = { pix: doPix, qr: doQr, bill: doBill, recharge: doRecharge, list: doList, show: doShow, cancel: doCancel, receipt: doReceipt, accounts: doAccounts };

async function main(argv, deps = {}) {
  const io = { stdout: deps.stdout || ((t) => process.stdout.write(t)), stderr: deps.stderr || ((t) => process.stderr.write(t)) };
  const env = deps.env || process.env;
  const cwd = deps.cwd || process.cwd();
  const home = env.RBTV_AGENT_HOME && fs.existsSync(env.RBTV_AGENT_HOME) ? path.resolve(env.RBTV_AGENT_HOME) : null;
  const ctx = {
    env, cwd, root: deps.root || REPO,
    installation: findInstallation(home || cwd) || findInstallation(cwd),
    which: deps.which || defaultWhich,
    run: deps.run || ((command, args, input) => defaultRun(command, args, input)),
    sleep: deps.sleep || ((ms) => new Promise((resolve) => setTimeout(resolve, ms))),
  };
  try {
    const parsed = parseOrHelp(argv);
    if (parsed.help || !parsed.verb) {
      io.stdout(parsed.verb ? HELP[parsed.verb] : ROOT_HELP);
      return parsed.help ? 0 : 2;
    }
    if (PAYING.includes(parsed.verb) && parsed.positionals.length) {
      throw invalid(`${parsed.verb} takes no positional word: ${parsed.positionals.join(' ')}`, 'the destination and the amount are options, so a missing part is named', `pay ${parsed.verb} -h`);
    }
    return await DO[parsed.verb](io, parsed, ctx);
  } catch (error) {
    if (error instanceof Refusal) {
      io.stderr(`pay: ${error.what}\n  why: ${error.why}\n  fix: ${error.fix}\n`);
      return error.exitCode;
    }
    io.stderr(`pay: failed: ${error.message}\n  why: an error no refusal covers\n  fix: run the same command again; report it if it persists\n`);
    return 1;
  }
}

module.exports = { main };

if (require.main === module) {
  main(process.argv.slice(2)).then((code) => process.exit(code));
}
