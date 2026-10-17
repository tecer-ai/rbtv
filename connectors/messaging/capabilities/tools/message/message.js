#!/usr/bin/env node
'use strict';

// message — the port command of the messaging port (connectors/messaging): an agent sends a message to one
// address as itself, replies inside a thread it has, reads a thread. It picks the connector --via names among
// the installation's messaging connectors (the repository's connectors/ and the installation's .rbtv/mirror/,
// the mirror's record replacing the repository's whole), checks permission before loading its adapter,
// confirms the connector's account identity, and only then
// hands the delivery to the adapter (connectors/<name>/capabilities/tools/<name>/lib/messaging.js) through the
// one send function it shares with Ignite's outbox (lib/send.js). Specification: projects' spec-message.md,
// phase 2 of the connector architecture; `message -h` is the interface reference.
//
// Both outbound verbs authorize from Ignite's configured team, owner and routes before loading any
// adapter. A DM reply checks Slack's conversation metadata in the port, never a reference or message
// sender. Reference consumers also bind the configured and actual accounts before reading or writing.
// A non-Slack connector's reply resolves its real recipient through the authenticated connector first
// (google: the mail thread the reference's conversation names, verified to contain the referenced
// message) and authorizes that exact service-specific address; a configured account alone grants
// nothing, and mail addresses are compared whole, never by digit stripping.
//
// API
// main(argv, deps?) → Promise<exit code>. deps: root (the folder holding connectors/, this repository),
//   cwd, env, stdout(text), stderr(text). Exit 0 sent or read; 1 refused or failed (three stderr lines:
//   `message: WHAT`, `  why:`, `  fix:`); 2 invalid words (same form). --json prints one object on stdout
//   for a success and changes nothing on a refusal.
// sendModule — lib/send.js, exported so Ignite's test_outbox.js can check both callers share it.

const fs = require('node:fs');
const path = require('node:path');
const { randomUUID } = require('node:crypto');
const sendModule = require('./lib/send.js');
const { sameAddress } = require('./lib/same-address.js');
const { envValue } = require('../../../../../core/ignite/capabilities/tools/ignite/config.js');

const REPO = path.resolve(__dirname, '..', '..', '..', '..', '..');
const VERBS = ['send', 'reply', 'history'];
const OPTIONS = {
  send: { to: 'value', via: 'value', 'text-file': 'value', file: 'list' },
  reply: { thread: 'value', 'text-file': 'value', file: 'list' },
  history: { thread: 'value', full: 'flag' },
};
const WIDTH = 80;

class Refusal extends Error {
  constructor(what, why, fix, code = 1) {
    super(what);
    this.what = what;
    this.why = why;
    this.fix = fix;
    this.exitCode = code;
  }
}
const refuse = (what, why, fix) => new Refusal(what, why, fix, 1);
const invalid = (what, why, fix) => new Refusal(what, why, fix, 2);

// ───────────────────────────────────────────────────────────── the installation

function findInstallation(start) {
  let dir = path.resolve(start);
  for (;;) {
    if (fs.existsSync(path.join(dir, '.rbtv', 'config', 'install.json'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
}

function readJson(file) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); } catch { return null; }
}

// The messaging connectors: every component under connectors/ of the installation's merged catalog (the
// repository, then the installation's .rbtv/mirror/, whose record of the same name replaces the repository's
// whole, as the installer merges them) whose record is of the messaging port and provides message.send, with
// whether it is installed here and whether it has a messaging adapter beside its record.
function connectors(root, installation) {
  const book = installation ? readJson(path.join(installation, '.rbtv', 'config', 'install.json')) : null;
  const installed = new Set(Object.keys(book?.components || {}));
  const trees = [path.join(root, 'connectors')];
  if (installation) trees.push(path.join(installation, '.rbtv', 'mirror', 'connectors'));
  const found = new Map();
  for (const folder of trees) {
    let names = [];
    try { names = fs.readdirSync(folder, { withFileTypes: true }).filter((e) => e.isDirectory()).map((e) => e.name).sort(); } catch { names = []; }
    for (const name of names) {
      const record = readJson(path.join(folder, name, `${name}.json`));
      if (!record) continue;
      found.delete(name);
      const ports = [record.type, ...(Array.isArray(record.serves) ? record.serves : [])];
      if (!ports.includes('messaging') || !(record.provides || []).includes('message.send')) continue;
      const adapter = path.join(folder, name, 'capabilities', 'tools', name, 'lib', 'messaging.js');
      found.set(name, { name, installed: installed.has(`connectors/${name}`), adapter, hasAdapter: fs.existsSync(adapter) });
    }
  }
  return [...found.values()].sort((a, b) => a.name.localeCompare(b.name));
}

const candidates = (all) => all.filter((c) => c.installed && c.hasAdapter);

function selectConnector(all, name, verb, to) {
  const ready = candidates(all);
  const list = ready.map((c) => c.name);
  if (!ready.length) {
    throw refuse('no messaging connector is installed',
      'message delivers through a connector that provides message.send and has a messaging adapter; none is installed here',
      'rbtv add connectors/slack, then message send again');
  }
  const example = (via) => `message send --to ${to || 'ADDRESS'} --via ${via} TEXT`;
  if (name == null) {
    const others = list.slice(1).map((n) => `--via ${n}`).join(', ');
    throw refuse(`${verb} refused: --via is required`,
      `every send names the connector that delivers; the messaging connectors installed here are: ${list.join(', ')}`,
      `${example(list[0])}${others ? `   (or ${others})` : ''}`);
  }
  const chosen = all.find((c) => c.name === name);
  if (!chosen || !chosen.installed) {
    throw refuse(`${verb} refused: no connector named "${name}"`,
      `the messaging connectors installed here are: ${list.join(', ')}`,
      `message send --via ${list[0]} …`);
  }
  if (!chosen.hasAdapter) {
    throw refuse(`${verb} refused: ${name} cannot deliver yet`,
      `connectors/${name} is installed but has no messaging adapter (capabilities/tools/${name}/lib/messaging.js); only ${list.join(', ')} can send`,
      `message send --to ADDRESS --via ${list[0]} TEXT, or ${name} send text (service command) when your prompt allows it`);
  }
  return chosen;
}

// The connector a reference names, for reply and history: installed with an adapter, or the refusal.
function connectorOf(all, name, verb) {
  const ready = candidates(all);
  if (!ready.length) return selectConnector(all, null, verb);
  const chosen = all.find((c) => c.name === name);
  if (!chosen || !chosen.installed) {
    throw refuse(`${verb} refused: connector "${name}" is not installed`,
      `the messaging connectors installed here are: ${ready.map((c) => c.name).join(', ')}`,
      'copy the Ref line of message send or message history');
  }
  if (!chosen.hasAdapter) {
    throw refuse(`${verb} refused: ${name} cannot deliver yet`,
      `connectors/${name} is installed but has no messaging adapter (capabilities/tools/${name}/lib/messaging.js)`,
      'rbtv add connectors/' + name + ' with its adapter, or a reference of an installed connector');
  }
  return chosen;
}

function loadAdapter(connector) {
  const adapter = require(connector.adapter);
  if (!adapter?.operations || typeof adapter.operations !== 'object') {
    throw refuse(`${connector.name} has no usable messaging adapter`, `${connector.adapter} does not export operations`, 'adapter-check ' + connector.name);
  }
  return adapter;
}

// ───────────────────────────────────────────────────────────── the words

function parse(argv) {
  const words = [...argv];
  let json = false;
  let help = false;
  let verb = null;
  const opts = {};
  const positionals = [];
  let text = null;
  let endOfOptions = false;
  const unknownVerb = (word) => invalid(`unknown command "${word}"; the commands are ${VERBS.join(', ')}`, 'the first word is the command', 'message -h');
  for (let i = 0; i < words.length; i++) {
    let word = words[i];
    if (!endOfOptions && word === '--') { endOfOptions = true; continue; }
    if (!endOfOptions && (word === '-h' || word === '--help')) { help = true; continue; }
    if (!endOfOptions && word === '--json') { json = true; continue; }
    if (!endOfOptions && word.startsWith('--') && word.length > 2) {
      let value = null;
      const eq = word.indexOf('=');
      if (eq > 0) { value = word.slice(eq + 1); word = word.slice(0, eq); }
      const name = word.slice(2);
      if (!verb) throw unknownVerb(word);
      const kind = OPTIONS[verb][name];
      if (!kind) {
        if (verb === 'send' && name === 'thread') throw invalid('send has no option --thread; a reply is message reply --thread REF', 'a message that starts a thread takes an address, a reply takes the thread', 'message reply --thread REF TEXT   (message send -h)');
        throw invalid(`${verb} has no option --${name}`, `the options of ${verb} are: ${Object.keys(OPTIONS[verb]).map((o) => `--${o}`).join(', ')}`, `message ${verb} -h`);
      }
      if (kind === 'flag') { opts[name] = true; continue; }
      if (value == null) {
        if (i + 1 >= words.length) throw invalid(`--${name} needs a value`, `${verb} takes --${name} ${name === 'file' || name === 'text-file' ? 'PATH' : name.toUpperCase()}`, `message ${verb} -h`);
        value = words[++i];
      }
      if (kind === 'list') (opts[name] = opts[name] || []).push(value);
      else if (name in opts) throw invalid(`--${name} is given twice`, 'each option is given once', `message ${verb} -h`);
      else opts[name] = value;
      continue;
    }
    if (!verb) {
      if (!VERBS.includes(word)) throw unknownVerb(word);
      verb = word;
      continue;
    }
    positionals.push(word);
  }
  if (verb === 'history' && positionals.length) {
    throw invalid(`history takes no TEXT; ${positionals.length === 1 ? `"${positionals[0]}" was` : `${positionals.length} words were`} given`, 'a thread is read by its reference', 'message history --thread REF   (message history -h)');
  }
  if (positionals.length > 1) throw invalid(`${verb} takes one TEXT; ${positionals.length} were given`, 'quote the text as one argument', `message ${verb} -h`);
  if (positionals.length === 1) text = positionals[0];
  return { json, help, verb, opts, text };
}

// Every word is checked before anything runs; a parse error with -h anywhere is help instead.
function parseOrHelp(argv) {
  try {
    return parse(argv);
  } catch (error) {
    if (argv.includes('-h') || argv.includes('--help')) {
      const verb = argv.find((w) => VERBS.includes(w)) || null;
      return { json: false, help: true, verb, opts: {}, text: null };
    }
    throw error;
  }
}

// ───────────────────────────────────────────────────────────── help

function wrap(text, width = WIDTH) {
  const lines = [];
  let line = '';
  for (const word of text.split(/\s+/)) {
    if (line && `${line} ${word}`.length > width) { lines.push(line); line = word; } else line = line ? `${line} ${word}` : word;
  }
  if (line) lines.push(line);
  return lines.join('\n');
}

function rootHelp(all) {
  const ready = candidates(all).map((c) => c.name);
  const line = wrap(`${ready.length ? `Connectors: ${ready.map((n) => `${n} (installed)`).join(', ')}.` : 'Connectors: none installed (rbtv add connectors/slack).'} A service's own feature (a Slack canvas or reaction, a WhatsApp voice note or poll, a mail label) stays in that service's command (slack, whatsapp, google); use it only when your prompt says so.`);
  return `usage: message [-h] [--json] COMMAND ...

Sends a message to a contact or a group as this agent, through the installed
messaging connector, replies inside a thread and reads a thread. The port
command: it checks who may be messaged, picks the connector and hands it the
delivery. A message to a contact never goes through slack send or ignite post.

positional arguments:
  COMMAND
    send      a message to an address, as this agent
    reply     a message into a thread, where the thread lives
    history   a thread's messages, oldest first

options:
  -h, --help  show this help message and exit
  --json      one JSON object on stdout instead of text

${line}
Who may be messaged: until the permission ladder exists, the owner and this
agent's own channel.
Exit codes: 0 sent or read; 1 refused or failed (stderr says why and the
fix); 2 invalid arguments.
`;
}

const HELP = {
  send: `usage: message send [-h] [--json] --to ADDRESS --via CONNECTOR
                    [--text-file PATH] [--file PATH]... [--] [TEXT]

Delivers TEXT to ADDRESS as this agent and prints the message's reference.

positional arguments:
  TEXT              the message, standard Markdown, up to 12,000 characters
                    (longer is sent as a file); --text-file for text with $

options:
  -h, --help        show this help message and exit
  --to ADDRESS      the recipient in the connector's own form: Slack user id
                    (U...) or channel id (C...); WhatsApp number with country
                    code (5511912345678) or group (...@g.us); a mail address.
                    Names are not resolved until the contact book exists
  --via CONNECTOR   the connector that delivers: slack | whatsapp | google.
                    Required on every send; a missing --via is refused with
                    the installed connectors listed
  --text-file PATH  read TEXT from a file instead of the argument
  --file PATH       attach a file after the text; repeat for several

Prints "Sent", "Ref" and "Reply": copy Ref into message reply --thread REF.
Until the permission ladder exists, only the owner and this agent's own
channel can be messaged; anyone else is refused before any connector runs.
Example: message send --to U0OWNER001 --via slack "Receipt saved: P-0003.pdf"
Next: message reply --thread REF TEXT
`,
  reply: `usage: message reply [-h] [--json] --thread REF [--text-file PATH]
                     [--file PATH]... [--] [TEXT]

Delivers TEXT inside the thread REF names, where that thread lives. A reply
takes no address and no connector: REF carries both.

positional arguments:
  TEXT              as in message send

options:
  -h, --help        show this help message and exit
  --thread REF      the reference message send or message history printed
                    (connector:account:conversation:id)
  --text-file PATH  read TEXT from a file
  --file PATH       attach a file; repeat for several

Example: message reply --thread slack:T0BJAM8PACU:D0OWNERDM1:1792160000.000100 "Done."
`,
  history: `usage: message history [-h] [--json] --thread REF [--full]

Lists the thread's messages oldest first, each with its time, sender and
text, in the one shape every connector delivers.

options:
  -h, --help    show this help message and exit
  --thread REF  the thread's reference (message send prints it)
  --full        every text whole, as labelled blocks

--json: {"ref": REF, "events": [inbound event, ...]} as the messaging
contract's inbound event table defines them.
`,
};

// ───────────────────────────────────────────────────────────── the reference

function parseRef(ref, verb) {
  const parts = String(ref || '').split(':');
  if (parts.length !== 4 || parts.some((p) => !p)) {
    throw refuse(`${verb} refused: not a message reference: ${ref}`,
      'a reference reads connector:account:conversation:id, as message send prints it',
      'copy the Ref line of message send or message history');
  }
  const [connector, account, conversation, id] = parts;
  return { connector, account, conversation, id, ref };
}

const refOf = (connector, account, conversation, id) => `${connector}:${account}:${conversation}:${id}`;

// ───────────────────────────────────────────────────────────── the text and files

function readText(opts, text, verb) {
  if (text != null && opts['text-file']) throw invalid('TEXT and --text-file are two texts: give one', 'a message has one text', `message ${verb} -h`);
  if (opts['text-file']) {
    try { return fs.readFileSync(opts['text-file'], 'utf8'); } catch (error) {
      throw refuse(`${verb} refused: cannot read --text-file ${opts['text-file']}`, error.message, 'give a readable file, or TEXT');
    }
  }
  return text;
}

function checkFiles(opts, verb) {
  const files = opts.file || [];
  for (const file of files) {
    if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {
      throw refuse(`${verb} refused: no file at ${file}`, 'every --file is read before anything is sent', `give the path of an existing file; nothing was sent`);
    }
  }
  return files.map((f) => path.resolve(f));
}

// ───────────────────────────────────────────────────────────── the permission (phase 2 rule 3.4)

function policyConfig(ctx) {
  return ctx.installation ? readJson(path.join(ctx.installation, '.rbtv', 'config', 'ignite', 'config.json')) : null;
}

function listenerSection(ctx, name) {
  return policyConfig(ctx)?.listeners?.[name] || null;
}

function referenceAccount(ctx, ref, verb) {
  const config = policyConfig(ctx);
  const expected = ref.connector === 'slack' ? config?.slack?.team : null;
  const section = listenerSection(ctx, ref.connector);
  const names = [expected, section?.account, section?.mailbox].filter(Boolean);
  if (names.length && !names.includes(ref.account)) {
    throw refuse(`${verb} refused: reference account does not match the configured account`,
      `the reference names ${ref.account}; Ignite config names ${names.join(' or ')}`,
      'copy the Ref line from this account; nothing was sent');
  }
}

// An authoritative contact binding is conversation metadata from Slack, not the author of a message.
// This is a read-only policy lookup in the port, before adapter loading. Config/store do not keep the
// bot-to-owner DM id: routes name groups; stored messages record senders, not a DM's contact. Use the
// same token and endpoint as the adapter, and refuse unknown/malformed metadata without delivery.
async function ownerConversation(ctx, conversation, owner) {
  const token = envValue(ctx.installation, 'SLACK_BOT_TOKEN');
  if (!token) throw new Error('SLACK_BOT_TOKEN is not set; cannot verify the direct conversation');
  const response = await fetch(`${process.env.SLACK_API_URL || 'https://slack.com/api'}/conversations.info`, {
    method: 'POST', signal: AbortSignal.timeout(10_000),
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ channel: conversation }).toString(),
  });
  if (!response.ok) throw new Error(`Slack conversation verification: HTTP ${response.status}`);
  const data = await response.json();
  if (!data.ok) throw new Error(`Slack conversation verification: ${data.error || 'unknown_error'}`);
  return data.channel?.id === conversation && data.channel.is_im === true && data.channel.user === owner;
}

async function permission(ctx, connector, to, verb) {
  const config = policyConfig(ctx);
  // Phase 2 has grants for the configured Slack account only. A mirror/other connector cannot
  // borrow Slack ids as its own permissions; its grants arrive with that port's contact book.
  const isSlack = connector.name === 'slack';
  const owner = isSlack ? config?.slack?.ownerUserId || null : (config?.listeners?.[connector.name]?.owner || null);
  const slug = ctx.home ? path.basename(ctx.home) : null;
  const channels = isSlack && slug && config?.routes
    ? Object.entries(config.routes).filter(([id, agent]) => agent === slug && /^[CG][A-Z0-9]+$/.test(id)).map(([id]) => id) : [];
  if (config?.slack?.team && (channels.includes(to) || (isSlack && verb === 'send' && owner && to === owner))) return;
  // A non-Slack owner grant is the exact service-specific address (a mail address whole, a phone's
  // digits), the resolved reply recipient included: a configured account alone grants no reply.
  if (!isSlack && owner && sameAddress(to, owner)) return;
  let verification = '';
  if (verb === 'reply' && owner && config?.slack?.team && /^D[A-Z0-9]+$/.test(to)) {
    try { if (await ownerConversation(ctx, to, owner)) return; }
    catch (error) { verification = `; ${error.message}`; }
  }
  const where = config ? '' : `; Ignite's config.json names neither here (${ctx.installation ? path.join(ctx.installation, '.rbtv', 'config', 'ignite', 'config.json') : 'no installation found'})`;
  throw refuse(`${verb} refused: no permission to message ${to}`,
    `until the permission ladder exists, this agent may message the owner${owner ? ` (${owner})` : ''} and its own channel${channels.length ? ` (${channels.join(', ')})` : ''} only${where}${verification}`,
    "ask the owner; a contact's permission is set in /messages once it exists");
}

async function accountOf(adapter, ctx, connector, verb, ref = null) {
  const section = listenerSection(ctx, connector.name);
  let account;
  try {
    account = typeof adapter.account === 'function' ? await adapter.account({
      section, account: section?.account, mailbox: section?.mailbox, owner: section?.owner, installation: ctx.installation,
    }) : null;
    if (typeof account !== 'string' || !account.trim() || account.includes(':')) throw new Error('the connector did not confirm its account identity');
  } catch (error) {
    throw refuse(`${verb} failed: ${connector.name} did not answer`, error.message, 'run the same command again; nothing was sent');
  }
  const configured = connector.name === 'slack' ? policyConfig(ctx)?.slack?.team : (section?.mailbox || section?.account || null);
  const accepted = [ref?.account, configured, section?.account, section?.mailbox].filter(Boolean);
  if (accepted.length && !accepted.includes(account)) {
    throw refuse(`${verb} refused: connector account does not match`,
      `the connector answered ${account}; expected ${accepted.join(' or ')}`,
      'use the configured account and a reference from it; nothing was sent');
  }
  return account;
}

// Preserve S8 locally without loading connector code to classify an unauthorized address.
function checkAddress(all, connector, to) {
  if (connector.name !== 'slack' || /^[UWCGD][A-Z0-9]+$/.test(to)) return;
  const other = candidates(all).find((c) => c.name !== connector.name);
  throw refuse(`send refused: slack does not take the address ${to}`,
    `slack addresses are a user id (U...) or a channel id (C...); ${to.includes('@') ? "a mail address is google's" : `${to} is neither`}`,
    `message send --to ${to} --via ${other ? other.name : 'CONNECTOR'} TEXT, or an address in slack's form`);
}

// ───────────────────────────────────────────────────────────── output

function adapterContext(ctx, connector) {
  const section = listenerSection(ctx, connector.name);
  return { section, account: section?.account, mailbox: section?.mailbox, owner: section?.owner, installation: ctx.installation };
}

function boundOperations(adapter, ctx, connector) {
  const extra = adapterContext(ctx, connector);
  const bound = {};
  if (typeof adapter.operations['message.send'] === 'function') {
    bound['message.send'] = (input) => adapter.operations['message.send'](input, extra);
  }
  if (typeof adapter.operations['message.file'] === 'function') {
    bound['message.file'] = (input) => adapter.operations['message.file'](input, extra);
  }
  return bound;
}

function rememberThread(ctx, row) {
  if (!ctx.installation || !row.agent || !row.thread) return;
  const file = path.join(ctx.installation, '.rbtv', 'runtime', 'ignite', 'message-threads.json');
  const lock = `${file}.lock`;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  for (let attempt = 0; attempt < 20; attempt += 1) {
    let fd;
    try { fd = fs.openSync(lock, 'wx'); } catch (error) {
      if (error.code !== 'EEXIST') throw error;
      continue;
    }
    try {
      const current = fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')) : [];
      const rows = Array.isArray(current) ? current : [];
      rows.push({ ...row, via: 'message-send' });
      const tmp = `${file}.${process.pid}.tmp`;
      fs.writeFileSync(tmp, JSON.stringify(rows));
      fs.renameSync(tmp, file);
      return;
    } finally {
      fs.closeSync(fd);
      try { fs.unlinkSync(lock); } catch { /* released */ }
    }
  }
  throw new Error('message thread file is busy');
}

function emitSent(io, json, verb, result) {
  if (json) { io.stdout(`${JSON.stringify(result.body)}\n`); return; }
  const failed = result.body.files.filter((f) => f.error).length;
  const parts = [];
  if (result.body.files.length && failed) parts.push(`${result.body.files.length - failed} of ${result.body.files.length} files`);
  if (result.textAsFile) parts.push(`as a file (text of ${result.textAsFile.chars.toLocaleString('en-US')} characters, limit ${sendModule.MAX_TEXT.toLocaleString('en-US')})`);
  const tail = parts.length ? `, ${parts.join(', ')}` : '';
  const as = result.body.as ? `, as ${result.body.as}` : '';
  if (verb === 'send') {
    io.stdout(`Sent     to ${result.body.to} (${result.where}) via ${result.body.connector}${as}${tail}\n`);
    io.stdout(`Ref      ${result.body.ref}\n`);
    if (!failed) io.stdout(`Reply    message reply --thread ${result.body.ref} TEXT\n`);
  } else {
    io.stdout(`Sent     in thread ${result.threadRef} via ${result.body.connector}${as}${tail}\n`);
    io.stdout(`Ref      ${result.body.ref}\n`);
  }
}

// A delivered message beside refused files: stdout kept what happened, stderr says what did not, exit 1.
function reportRefusedFiles(io, body, ref, result) {
  const failed = result.files.filter((f) => f.error);
  if (!failed.length) return 0;
  const textDelivered = body && (!result.textAsFile || result.files[0]?.id);
  const delivered = textDelivered ? 'the text is delivered' : `${result.files.length - failed.length} of ${result.files.length} files are delivered`;
  io.stderr(`message: ${failed.length} file${failed.length === 1 ? ' was' : 's were'} not sent: ${failed.map((f) => f.path).join(', ')}\n`);
  io.stderr(`  why: ${failed[0].detail || failed[0].error}\n`);
  io.stderr(`  fix: ${delivered}; send the file again with message reply --thread ${ref} --file PATH\n`);
  return 1;
}

function whenOf(at) {
  const d = new Date(at);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}Z`;
}

function emitHistory(io, json, ref, connector, events, full) {
  if (json) { io.stdout(`${JSON.stringify({ ref: ref.ref, events })}\n`); return; }
  const count = events.length;
  io.stdout(`Thread ${ref.ref} (${count} message${count === 1 ? '' : 's'}, via ${connector})\n`);
  if (!count) { io.stdout('No messages: this service keeps no thread for it.\n'); return; }
  if (full) {
    for (const event of events) {
      io.stdout(`\nid     ${event.id}\nwhen   ${whenOf(event.at)}\nfrom   ${event.from}\ntext   ${String(event.text || '').replace(/\r?\n/g, '\n       ')}\n`);
    }
    return;
  }
  io.stdout('\n');
  const fromWidth = Math.max(4, ...events.map((e) => String(e.from || '').length));
  const head = `${'when'.padEnd(23)}${'from'.padEnd(fromWidth + 3)}text`;
  io.stdout(`${head}\n`);
  let shortened = false;
  const room = WIDTH - 23 - (fromWidth + 3);
  for (const event of events) {
    let text = String(event.text || '').replace(/\s*\r?\n\s*/g, ' ');
    if (text.length > room) { text = `${text.slice(0, Math.max(0, room - 3)).trimEnd()}...`; shortened = true; }
    io.stdout(`${whenOf(event.at).padEnd(23)}${String(event.from || '').padEnd(fromWidth + 3)}${text}\n`);
  }
  if (shortened) io.stdout('Some texts are shortened: message history --thread REF --full shows them whole.\n');
}

// ───────────────────────────────────────────────────────────── the verbs

async function doSend(io, parsed, ctx) {
  const { opts, text } = parsed;
  const to = opts.to;
  if (to === undefined) throw invalid('send needs --to ADDRESS', 'the recipient is never guessed', `message send --to ADDRESS --via ${candidates(ctx.all)[0]?.name || 'CONNECTOR'} TEXT   (message send -h)`);
  if (!String(to).trim()) throw invalid('--to is empty', 'the recipient is never guessed', 'message send --to ADDRESS --via CONNECTOR TEXT');
  const body = readText(opts, text, 'send');
  if (body == null && !(opts.file || []).length) {
    throw invalid('send needs TEXT, --text-file PATH or --file PATH', 'nothing to send', `message send --to ${to}${opts.via ? ` --via ${opts.via}` : ''} "text"   (message send -h)`);
  }
  const files = checkFiles(opts, 'send');
  const connector = selectConnector(ctx.all, opts.via, 'send', to);
  checkAddress(ctx.all, connector, to);
  await permission(ctx, connector, to, 'send');
  const adapter = loadAdapter(connector);

  let where;
  try {
    where = typeof adapter.address === 'function' ? adapter.address(to) : { group: to };
  } catch (error) {
    if (error.code === 'address') {
      const other = candidates(ctx.all).find((c) => c.name !== connector.name);
      throw refuse(`send refused: ${connector.name} does not take the address ${to}`, error.message,
        `message send --to ${to} --via ${other ? other.name : 'CONNECTOR'} TEXT, or an address in ${connector.name}'s form`);
    }
    throw error;
  }
  // The account identity before the post: a reference needs it, so a post is never followed by a failure
  // that would hide the reference of a message that exists.
  const account = await accountOf(adapter, ctx, connector, 'send');
  const as = sendModule.senderOf(ctx.home);
  let result;
  try {
    result = await sendModule.send(boundOperations(adapter, ctx, connector), { ...where, thread: null, text: body || '', files, as, clientId: `message:${randomUUID()}` });
  } catch (error) {
    throw refuse(`send failed: ${connector.name} did not deliver`, error.message, 'run the same command again; nothing was sent');
  }
  const ref = refOf(connector.name, account, result.conversation, result.id);
  const out = {
    connector: connector.name, account, to, conversation: result.conversation, thread: null, id: result.id, ref,
    as: as?.name || null, files: result.files.map((f) => (f.error ? { path: f.path, id: null, error: f.error } : { path: f.path, id: f.id })),
  };
  emitSent(io, parsed.json, 'send', { body: out, where: where.contact ? 'direct' : `group ${where.group}`, textAsFile: result.textAsFile });
  rememberThread(ctx, { connector: connector.name, account, conversation: result.conversation, thread: result.id, agent: ctx.home ? path.basename(ctx.home) : null });
  return reportRefusedFiles(io, body, ref, result);
}

// A connector failure on a thread reference: a message id that belongs to another conversation is
// the mismatch refusal; a thread the service does not know is not-found; anything else a failure.
function refusalOf(connector, verb, error) {
  if (error.code === 'thread' && /thread_mismatch/.test(String(error.message || ''))) {
    return refuse(`${verb} refused: reference conversation does not match`, error.message, 'copy the Ref line of message send or message history; nothing was sent');
  }
  if (error.code === 'thread') {
    const fix = verb === 'history' ? 'message history --thread REF of a reference message send printed' : 'message history --thread REF of a reference message send printed; nothing was sent';
    return refuse(`${verb} failed: thread not found`, error.message, fix);
  }
  return refuse(`${verb} failed: ${connector.name} did not answer`, error.message, 'run the same command again; nothing was sent');
}

// A google reference is connector:mailbox:thread:message: its conversation names the mail thread
// and its id a message in that thread. The reply's recipient is resolved through the connector's
// own authenticated resolution (its resolveReply export: the address Gmail authenticated, with the
// message/thread binding validated), and that exact address is what the owner check authorizes —
// never the reference or a configured account alone. A WhatsApp reference's conversation is the
// chat itself: the chat's address is the recipient, the phone identifier it is.
async function resolveNonSlackReply(adapter, ctx, connector, ref) {
  if (connector.name !== 'google') return { group: ref.conversation, thread: ref.id, recipient: ref.conversation };
  if (typeof adapter.resolveReply !== 'function') {
    throw refuse("reply refused: the reply's recipient cannot be verified",
      `connectors/${connector.name} exposes no reply resolution for a mail reference`,
      `update connectors/${connector.name} with its adapter; nothing was sent`);
  }
  let target;
  try {
    target = await adapter.resolveReply({ id: ref.id, conversation: ref.conversation }, adapterContext(ctx, connector));
  } catch (error) {
    throw refusalOf(connector, 'reply', error);
  }
  const recipient = String(target?.to || '').trim();
  if (!recipient || recipient.includes(':')) {
    throw refuse("reply refused: the reply's recipient cannot be verified",
      `${connector.name} resolved no address for message ${ref.id} in ${ref.conversation}`,
      'reply to a message the owner sent; nothing was sent');
  }
  return { group: ref.conversation, thread: ref.id, recipient };
}

async function doReply(io, parsed, ctx) {
  const { opts, text } = parsed;
  if (opts.thread === undefined) throw invalid('reply needs --thread REF', 'a reply goes where the thread lives', 'message reply --thread REF TEXT   (message reply -h)');
  const body = readText(opts, text, 'reply');
  if (body == null && !(opts.file || []).length) throw invalid('reply needs TEXT, --text-file PATH or --file PATH', 'nothing to send', `message reply --thread ${opts.thread} "text"   (message reply -h)`);
  const files = checkFiles(opts, 'reply');
  if (!candidates(ctx.all).length) selectConnector(ctx.all, null, 'reply');
  const ref = parseRef(opts.thread, 'reply');
  const connector = connectorOf(ctx.all, ref.connector, 'reply');
  referenceAccount(ctx, ref, 'reply');
  if (connector.name === 'slack') await permission(ctx, connector, ref.conversation, 'reply');
  const adapter = loadAdapter(connector);
  const account = await accountOf(adapter, ctx, connector, 'reply', ref);
  // A non-Slack reply resolves its real recipient through the authenticated connector first; the
  // owner check authorizes that resolved address, never the reference or a configured account alone.
  let group = ref.conversation;
  let thread = ref.id;
  if (connector.name !== 'slack') {
    const resolved = await resolveNonSlackReply(adapter, ctx, connector, ref);
    group = resolved.group;
    thread = resolved.thread;
    await permission(ctx, connector, resolved.recipient, 'reply');
  }
  const as = sendModule.senderOf(ctx.home);
  let result;
  try {
    result = await sendModule.send(boundOperations(adapter, ctx, connector), { group, thread, text: body || '', files, as, clientId: `message:${randomUUID()}` });
  } catch (error) {
    if (error.code === 'thread') throw refuse('reply failed: thread not found', error.message, 'message history --thread REF of a reference message send printed; nothing was sent');
    throw refuse(`reply failed: ${connector.name} did not deliver`, error.message, 'run the same command again; nothing was sent');
  }
  // thread is the thread's root as the connector resolved it: a reply's reference names its thread's root.
  const out = {
    connector: connector.name, account, to: null, conversation: result.conversation, thread: result.thread ?? ref.id, id: result.id,
    ref: refOf(connector.name, account, result.conversation, result.id),
    as: as?.name || null, files: result.files.map((f) => (f.error ? { path: f.path, id: null, error: f.error } : { path: f.path, id: f.id })),
  };
  emitSent(io, parsed.json, 'reply', { body: out, threadRef: ref.ref, textAsFile: result.textAsFile });
  return reportRefusedFiles(io, body, ref.ref, result);
}

async function doHistory(io, parsed, ctx) {
  const { opts } = parsed;
  if (opts.thread === undefined) throw invalid('history needs --thread REF', 'a thread is read by its reference', 'message history --thread REF   (message history -h)');
  if (!candidates(ctx.all).length) selectConnector(ctx.all, null, 'history');
  const ref = parseRef(opts.thread, 'history');
  const connector = connectorOf(ctx.all, ref.connector, 'history');
  referenceAccount(ctx, ref, 'history');
  const adapter = loadAdapter(connector);
  await accountOf(adapter, ctx, connector, 'history', ref);
  if (typeof adapter.operations['message.history'] !== 'function') {
    throw refuse(`history refused: ${connector.name} does not provide message.history`, `the ${connector.name} record lists no message.history under provides`, 'read the thread in the service itself');
  }
  // A google reference's conversation is the mail thread and its id a message in it: the adapter
  // resolves that binding and refuses a message outside its conversation; the membership check
  // below keeps the invariant true whatever the adapter answered.
  const googleShape = connector.name === 'google';
  let result;
  try {
    result = await adapter.operations['message.history']({ conversation: ref.conversation, thread: ref.id }, adapterContext(ctx, connector));
  } catch (error) {
    throw refusalOf(connector, 'history', error);
  }
  const events = Array.isArray(result?.events) ? result.events : [];
  if (googleShape && ref.id !== ref.conversation && !events.some((event) => event.id === ref.id)) {
    throw refuse('history refused: reference conversation does not match',
      `message ${ref.id} is not in conversation ${ref.conversation} as ${connector.name} reads it`,
      'copy the Ref line of message send or message history');
  }
  const shown = parsed.json ? events : events.map(({ raw, ...rest }) => rest);
  emitHistory(io, parsed.json, ref, connector.name, shown, Boolean(opts.full));
  return 0;
}

async function main(argv, deps = {}) {
  const io = { stdout: deps.stdout || ((t) => process.stdout.write(t)), stderr: deps.stderr || ((t) => process.stderr.write(t)) };
  const env = deps.env || process.env;
  const cwd = deps.cwd || process.cwd();
  const root = deps.root || REPO;
  const home = env.RBTV_AGENT_HOME && fs.existsSync(env.RBTV_AGENT_HOME) ? path.resolve(env.RBTV_AGENT_HOME) : null;
  const installation = findInstallation(home || cwd) || findInstallation(cwd);
  let all = [];
  try { all = connectors(root, installation); } catch { all = []; }
  try {
    const parsed = parseOrHelp(argv);
    if (parsed.help || !parsed.verb) {
      io.stdout(parsed.verb ? HELP[parsed.verb] : rootHelp(all));
      return parsed.help ? 0 : 2;
    }
    const ctx = { all, installation, home };
    if (parsed.verb === 'send') return await doSend(io, parsed, ctx);
    if (parsed.verb === 'reply') return await doReply(io, parsed, ctx);
    return await doHistory(io, parsed, ctx);
  } catch (error) {
    if (error instanceof Refusal) {
      io.stderr(`message: ${error.what}\n  why: ${error.why}\n  fix: ${error.fix}\n`);
      return error.exitCode;
    }
    io.stderr(`message: failed: ${error.message}\n  why: an error no refusal covers\n  fix: run the same command again; report it if it persists\n`);
    return 1;
  }
}

module.exports = { main, sendModule };

if (require.main === module) {
  main(process.argv.slice(2)).then((code) => process.exit(code));
}
