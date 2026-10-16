#!/usr/bin/env node
'use strict';

// Suite for the messaging contract (connectors/messaging/capabilities/methods/messaging-contract.md):
// every Slack class method Ignite's production files call is listed there with a tag, every use of
// the word `slack` in those files is one this program understands, the contract names every field
// the panel reads from a slash-command or interactive payload, and the inbound fixtures beside the
// contract fit its inbound event shape.
//
// A production file is a .js file anywhere under core/ignite/ other than the client (slack.js)
// and the test programs. A call site is a (file, method) at which such a file reaches a method
// of the Slack class through a name that holds the client. In each file the holders are `slack`
// (bare, `deps.slack`, `slack()`, `this.slack` and the like), every name assigned from a holder,
// from `new Slack(` or from a function of the same file that returns a holder, and a method taken
// out of a holder by destructuring, under its own name or renamed (`const { canvasCreate: create }
// = deps.slack` makes `create(` a call of canvasCreate); a holder's method is reached by property
// with any spacing or line break between the holder and the method (`slack.postMessage(`,
// `s.postMessage ({`, `deps.slack?.openIm`, `deps.slack` at the end of one line and
// `.canvasCreate(` on the next), by index in a file that calls the client that way
// (status-ticker.js calls `client[method](...)`, so a method named as a string there is a call
// site) or bare after destructuring. Matching runs on each file's code, its comments blanked,
// never line by line. The contract's call-site table has one row per file and method:
// | `file.js` | `method` | tag | ... | with tag message, panel or ignite-internal, the file written
// relative to this folder. An untagged production call site fails, and so does a row whose call
// site no longer exists.
//
// The program fails closed on the word `slack`: every occurrence of the identifier in a production
// file's code, as a property, a variable, a key, a parameter or inside a string, must be one of the
// forms `classify` names (a call site, a config read, a holder binding, a parameter, a key, a test,
// a return, a string that is a path, an address, a config key or a required-method message) or one
// of the non-client uses NON_CLIENT_USES lists by exact text. Any other occurrence fails with
// `unsupported client use <file>:<line>: <the text>`. The contract's Checks section lists the forms
// for an author; a form this program does not understand is written in a listed form, or a use
// that is not the client is added to NON_CLIENT_USES with its reason.
//
// The slash-command and interactive payloads are the contract's sections "Slash command" and
// "Buttons and forms". Every path the panel's files read from a payload is named in one of those
// sections' Field column, as written: `payload.trigger_id` is `trigger_id`, `payload.actions?.[0]`
// then `act.action_id` is `actions[0].action_id`, `const view = payload.view` then
// `view.state.values[blockId]` is `view.state.values` (a computed index ends the path). A name
// assigned from a payload path (`const view = payload.view || {}`) reads that path wherever the
// file uses it, in any function.
//
// The inbound event shape is the contract's table under "## Inbound event": | `field` | type |
// required or optional | ... |. Each fixture in messaging-contract/inbound-*.json must hold every
// required field with its type, only fields of the table, and nothing of another type.

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const HERE = __dirname;
const IGNITE = path.resolve(HERE, '..', '..', '..');
const REPO = path.resolve(IGNITE, '..', '..');
const CLIENT = path.join(HERE, 'slack.js');
const CONFIG = path.join(HERE, 'config.js');
const CONTRACT = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract.md');
const FIXTURES = path.join(REPO, 'connectors', 'messaging', 'capabilities', 'methods', 'messaging-contract');
const TAGS = new Set(['message', 'panel', 'ignite-internal']);
const INTERACTION_SECTIONS = ['Slash command', 'Buttons and forms'];
const SKIPPED_DIRS = new Set(['node_modules', '.git']);

// The uses of the word `slack` in a production file that are not the client and that no generic
// form of `classify` explains: the file, the exact text around the word (the word once), and why
// it is not a client call. An occurrence that matches none of these and no generic form fails.
const NON_CLIENT_USES = [
  { file: 'config.js', text: "['slack', 'tools'", why: "the config section's name in the list of top-level config keys" },
  { file: 'config.js', text: "SLACK_KEYS, 'slack')", why: "the config section's name as the label of a refusal" },
  { file: 'config.js', text: 'rejectUnknown(raw.slack,', why: "the raw config's slack section handed to its validator" },
  { file: 'config.js', text: 'reqString(raw.slack,', why: "the raw config's slack section handed to its validator" },
  { file: 'config.js', text: 'reqEnvName(raw.slack,', why: "the raw config's slack section handed to its validator" },
  { file: 'config.js', text: 'config.slack[`${key}TokenEnv`]', why: 'the name of a token variable, read under a computed config key' },
  { file: 'daemon.js', text: 'config.slack[name]', why: 'the name of each token variable, read under a computed config key to scrub the env' },
  { file: 'daemon.js', text: "event: 'slack'", why: "the log event name of the client's own log lines" },
  { file: 'albert-evidence.js', text: "['slack', 'used-text']", why: 'a source label of a memory row' },
];

const tests = [];
function test(name, fn) { tests.push({ name, fn }); }

function lines(file) {
  return fs.readFileSync(file, 'utf8').split(/\r?\n/);
}

function escapeReg(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// The methods of the Slack class, read from slack.js: each `  name(` or `  async name(` line of the
// class body, constructor excluded.
function slackMethods() {
  const text = fs.readFileSync(CLIENT, 'utf8');
  const start = text.indexOf('class Slack {');
  assert.ok(start >= 0, 'slack.js declares class Slack');
  const body = text.slice(start);
  const names = new Set();
  for (const line of body.split(/\r?\n/)) {
    const match = line.match(/^ {2}(?:async )?([A-Za-z_$][\w$]*)\s*\(/);
    if (match && match[1] !== 'constructor') names.add(match[1]);
  }
  return [...names].sort();
}

// The keys of the `slack` section of Ignite's config, read from config.js's SLACK_KEYS: a read of
// `config.slack.<key>` is a config read, never a client call.
function slackConfigKeys() {
  const match = fs.readFileSync(CONFIG, 'utf8').match(/const SLACK_KEYS = \[([^\]]*)\]/);
  assert.ok(match, 'config.js declares SLACK_KEYS');
  const keys = match[1].split(',').map((key) => key.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean);
  assert.ok(keys.length > 0, 'SLACK_KEYS names at least one key');
  return keys;
}

// Every production file under core/ignite/, each named relative to this folder.
function productionFiles() {
  const found = [];
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (!SKIPPED_DIRS.has(entry.name)) walk(abs);
        continue;
      }
      if (!entry.name.endsWith('.js') || entry.name.startsWith('test_') || abs === CLIENT) continue;
      found.push({ file: path.relative(HERE, abs).split(path.sep).join('/'), abs });
    }
  };
  walk(IGNITE);
  return found.sort((a, b) => a.file.localeCompare(b.file));
}

// The code of a file: a whole-line comment is blanked, and so is a trailing ` // ...`; line breaks
// are kept, so an index into the code names a line.
function codeOf(text) {
  return text.split(/\r?\n/).map((line) => line.replace(/^\s*\/\/.*$/, '').replace(/\s\/\/.*$/, '')).join('\n');
}

// The 1-based line that holds the character at `index` of `code`.
function lineAt(code, index) {
  return code.slice(0, index).split('\n').length;
}

const NAME = /^[A-Za-z_$][\w$]*$/;

// A receiver that holds the client: an optional property chain ending in a holder name, optionally
// called (`slack()`), as a regular-expression source.
function holderExpr(names) {
  return `(?:[\\w$]+\\??\\.)*(?:${[...names].map(escapeReg).join('|')})(?:\\(\\))?`;
}

// Every string literal of a file's code, so that a `slack` inside a string is judged as text and
// one in code as code: single- and double-quoted strings, ended at the line's end when unterminated
// (a quote inside a regular-expression literal, which this scanner does not read, then swallows
// nothing beyond its line), and template literals, whose `${ }` holes are code. Returns the spans,
// each with its text (a template's holes kept as written), and a mask with 1 at each index that is
// inside a literal.
function stringSpans(code) {
  const n = code.length;
  const mask = new Uint8Array(n);
  const spans = [];
  let i = 0;
  const quoted = () => {
    const quote = code[i];
    const start = i;
    i += 1;
    while (i < n && code[i] !== quote && code[i] !== '\n') i += code[i] === '\\' ? 2 : 1;
    const end = i < n && code[i] === quote ? i + 1 : Math.min(i, n);
    mask.fill(1, start, end);
    spans.push({ start, end, text: code.slice(start + 1, Math.min(i, n)) });
    i = end;
  };
  const template = () => {
    const start = i;
    let text = '';
    mask[i] = 1;
    i += 1;
    while (i < n && code[i] !== '`') {
      if (code[i] === '\\') {
        mask.fill(1, i, Math.min(i + 2, n));
        text += code.slice(i, i + 2);
        i += 2;
        continue;
      }
      if (code.startsWith('${', i)) {
        const hole = i;
        i += 2;
        for (let depth = 1; i < n && depth > 0;) {
          const c = code[i];
          if (c === "'" || c === '"') quoted();
          else if (c === '`') template();
          else {
            if (c === '{') depth += 1;
            else if (c === '}') depth -= 1;
            i += 1;
          }
        }
        text += code.slice(hole, i);
        continue;
      }
      mask[i] = 1;
      text += code[i];
      i += 1;
    }
    const end = Math.min(i + 1, n);
    if (i < n) mask[i] = 1;
    spans.push({ start, end, text });
    i = end;
  };
  while (i < n) {
    const c = code[i];
    if (c === "'" || c === '"') quoted();
    else if (c === '`') template();
    else i += 1;
  }
  return { spans, mask };
}

// The innermost string span whose text holds the character at `at`, or null when `at` is code.
function spanAt(spans, mask, at) {
  if (!mask[at]) return null;
  let found = null;
  for (const span of spans) {
    if (span.start <= at && at < span.end && (!found || span.start > found.start)) found = span;
  }
  return found;
}

// The index of the bracket that closes the one opened at `open`, strings skipped; -1 when none.
function closingOf(code, mask, open) {
  const pairs = { '(': ')', '{': '}', '[': ']' };
  const close = pairs[code[open]];
  let depth = 0;
  for (let i = open; i < code.length; i += 1) {
    if (mask[i]) continue;
    if (code[i] === code[open]) depth += 1;
    else if (code[i] === close) {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return -1;
}

// The innermost bracket group open at `at`: its opening character and index, and how many
// top-level commas lie between its opening and `at` (the position of the element holding `at`).
function groupAt(code, mask, at) {
  let depth = 0;
  let commas = 0;
  for (let i = at - 1; i >= 0; i -= 1) {
    if (mask[i]) continue;
    const c = code[i];
    if (c === ')' || c === '}' || c === ']') depth += 1;
    else if (c === '(' || c === '{' || c === '[') {
      if (depth === 0) return { open: c, at: i, position: commas };
      depth -= 1;
    } else if (c === ',' && depth === 0) commas += 1;
  }
  return null;
}

// The parameter names of the function `name` declared in the code (`function name(`, `async
// function name(`, `const name = (`, `const name = async (`), defaults stripped; null when the
// code declares none.
function paramsOf(code, mask, name) {
  const declared = new RegExp(`(?:function\\s+${escapeReg(name)}|(?:const|let|var)\\s+${escapeReg(name)}\\s*=\\s*(?:async\\s*)?)\\s*\\(`, 'g');
  for (const match of code.matchAll(declared)) {
    const open = match.index + match[0].length - 1;
    if (mask[open]) continue;
    const close = closingOf(code, mask, open);
    if (close < 0) return null;
    const names = [];
    let depth = 0;
    let part = '';
    for (let i = open + 1; i <= close; i += 1) {
      const c = code[i];
      if (i === close || (c === ',' && depth === 0 && !mask[i])) {
        names.push(part.trim().replace(/\s*=[\s\S]*$/, ''));
        part = '';
        continue;
      }
      if (!mask[i] && '({['.includes(c)) depth += 1;
      else if (!mask[i] && ')}]'.includes(c)) depth -= 1;
      part += c;
    }
    return names;
  }
  return null;
}

// The start of the receiver chain ending at `at` (`deps.`, `ctx.config?.`, `this.`), `at` itself
// when the word is bare, and -1 when a dot precedes it with no name before the dot (`f().slack`).
function chainStart(code, at) {
  let i = at;
  for (;;) {
    let j = i;
    while (j > 0 && /\s/.test(code[j - 1])) j -= 1;
    if (code[j - 1] !== '.') return i;
    j -= 1;
    if (code[j - 1] === '?') j -= 1;
    while (j > 0 && /\s/.test(code[j - 1])) j -= 1;
    const end = j;
    while (j > 0 && /[\w$]/.test(code[j - 1])) j -= 1;
    if (j === end) return -1;
    i = j;
  }
}

// The function names of a file that return a holder (`return deps.slack;`, `return new Slack(`),
// each found as the nearest `function name(` above the return.
function factoriesOf(code, names) {
  const found = new Set();
  const returns = new RegExp(`\\breturn\\s+(?:await\\s+)?(?:new Slack\\s*\\(|${holderExpr(names)}\\s*;)`, 'g');
  for (const match of code.matchAll(returns)) {
    const above = [...code.slice(0, match.index).matchAll(/\bfunction\s+([A-Za-z_$][\w$]*)\s*\(/g)].pop();
    if (above) found.add(above[1]);
  }
  return found;
}

// The names that hold the Slack client in one file, the methods taken out of one by destructuring,
// each local name mapped to the Slack method it names, and the functions that return one. Grows
// until no assignment adds a name. Matches on the file's code with ^ and $ at line ends.
function holders(code) {
  const names = new Set(['slack']);
  const bare = new Map();
  let factories = new Set();
  const lhs = '(?:^|[^\\w$.])(?:(?:const|let|var)\\s+)?([A-Za-z_$][\\w$]*)\\s*=\\s*';
  for (;;) {
    const before = names.size + bare.size + factories.size;
    const holder = holderExpr(names);
    factories = new Set([...factories, ...factoriesOf(code, names)]);
    const forms = [
      new RegExp(`${lhs}(?:await\\s+)?${holder}(?:\\s*\\|\\|\\s*null)?\\s*(?:;|$)`, 'gm'),
      new RegExp(`${lhs}[^;\\n]*\\?\\s*${holder}\\s*:`, 'gm'),
      new RegExp(`${lhs}new Slack\\s*\\(`, 'gm'),
    ];
    if (factories.size) forms.push(new RegExp(`${lhs}(?:await\\s+)?(?:${[...factories].map(escapeReg).join('|')})\\s*\\(`, 'gm'));
    for (const form of forms) {
      for (const match of code.matchAll(form)) names.add(match[1]);
    }
    const taken = new RegExp(`(?:const|let|var)\\s*\\{([^}]*)\\}\\s*=\\s*(?:await\\s+)?${holder}\\s*(?:;|$)`, 'gm');
    for (const match of code.matchAll(taken)) {
      for (const part of match[1].split(',')) {
        const [method, local = method] = part.split(':').map((s) => s.trim().replace(/\s*=.*$/, ''));
        if (NAME.test(method) && NAME.test(local)) bare.set(local, method);
      }
    }
    if (names.size + bare.size + factories.size === before) return { names, bare, factories };
  }
}

// Every (file, method) at which Ignite reaches the Slack client, with the lines it was seen on.
function callSites(methods) {
  const found = new Map();
  const note = (file, method, line) => {
    const key = `${file}:${method}`;
    if (!found.has(key)) found.set(key, { file, method, lines: new Set() });
    found.get(key).lines.add(line);
  };
  for (const { file, abs } of productionFiles()) {
    const code = codeOf(fs.readFileSync(abs, 'utf8'));
    const { names, bare } = holders(code);
    const holder = holderExpr(names);
    const indexed = new RegExp(`(?:^|[^\\w$])${holder}\\s*\\[\\s*[^\\]]+\\s*\\]\\s*\\(`).test(code);
    for (const method of methods) {
      const forms = [new RegExp(`(?:^|[^\\w$])${holder}\\s*\\??\\.\\s*${method}\\b`, 'g')];
      if (indexed) forms.push(new RegExp(`['"\`]${method}['"\`]`, 'g'));
      for (const [local, original] of bare) {
        if (original === method) forms.push(new RegExp(`(?:^|[^\\w$.])${escapeReg(local)}\\s*\\(`, 'g'));
      }
      for (const form of forms) {
        for (const match of code.matchAll(form)) note(file, method, lineAt(code, match.index));
      }
    }
  }
  for (const site of found.values()) site.lines = [...site.lines].sort((a, b) => a - b);
  return found;
}

// The form of one occurrence of the word `slack` at `at` in a file's code, or null when no form
// explains it. `used` receives the index range a form explains beyond the word itself (the value
// of a `slack:` key), so the words inside it are not judged again. The forms, in the order tried:
//   string: a module path (`./slack.js`, `connectors/slack/`), a web address (`slack.com`), a
//     config key or key path (`slack.team`, `config.slack.ownerUserId`, `slack.${key}`), the
//     message thrown when the client lacks a method (`slack.openIm required`), or a listed use;
//   call: the holder, bare, as a property or as a getter call, then `.method` or `?.method`
//     (`slack.auth()`, `deps.slack?.openIm`, `slack().openView(`), any spacing or line break
//     between;
//   config: `<name>.slack.<key>` or `<name>?.slack?.<key>` with a key of config.js's SLACK_KEYS;
//   binding: the holder as the value assigned to a name (`const s = deps.slack;`, `let slack =
//     opts.slack || null;`, `socket = slack;`, `const client = slack();`) or as a branch of a
//     ternary assigned to one (`? slack() : null`);
//   target: `slack` or `<name>.slack` declared or assigned a holder value (`let slack = opts.slack
//     || null;`, `slack = new Slack({`, `ctx.slack = slack;`, `const slack = slackClient(…)`
//     where slackClient returns a holder);
//   test: `typeof slack`, `!slack`, `if (deps.slack)`, `&& slack`, `|| slack`;
//   return: `return deps.slack;`, which makes the enclosing function a holder factory;
//   parameter: bare `slack` in a function's parameter list, plain or destructured
//     (`function f(store, slack)`, `(slack) =>`, `createLegend({ slack, log })`);
//   key: bare `slack` as a shorthand key of an object (`{ config, slack, log }`), or as a key
//     whose value is a holder or a getter of one (`slack: () => slack`, `slack: deps.slack`);
//   argument: the holder passed to a function of the same file whose parameter at that position
//     is named `slack` (`activateThread(store, ctx.slack, route)`);
//   listed: an exact text of NON_CLIENT_USES in that file.
// Not explained, so refused: destructuring the client itself (`const { slack: client } = deps`),
// a computed key (`deps['slack']`), a holder passed to a parameter of another name, a `slack`
// property followed by a name that is neither a Slack method nor a config key, and any text not
// named above.
function classify(file, code, spans, mask, at, context) {
  const { methods, keys, names, factories, used } = context;
  const base = path.posix.basename(file);
  const listed = () => NON_CLIENT_USES.find((use) => use.file === base && code.startsWith(use.text, at - use.text.indexOf('slack')));
  const span = spanAt(spans, mask, at);
  if (span) {
    const text = span.text;
    if (/(^|\/)slack(\/|\.js$)/.test(text)) return { form: 'string: a module path' };
    if (/\bslack\.com\b/.test(text)) return { form: 'string: a web address' };
    if (new RegExp(`^(?:config\\.)?slack\\.(?:${keys.join('|')}|\\$\\{key\\})(?![\\w$])`).test(text)) return { form: 'string: a config key' };
    if (new RegExp(`^slack\\.(?:${methods.join('|')}) required$`).test(text)) return { form: 'string: a required-method message' };
    const use = listed();
    return use ? { form: `listed: ${use.why}` } : null;
  }
  const start = chainStart(code, at);
  if (start < 0) return listed() ? { form: 'listed' } : null;
  const isProp = start < at;
  const getter = code.slice(at + 5).match(/^\s*\(\s*\)/);
  const end = at + 5 + (getter ? getter[0].length : 0);
  const head = code.slice(0, start).trimEnd();
  const tail = code.slice(end).trimStart();
  const holder = holderExpr(names);
  const factory = factories.size ? `(?:${[...factories].map(escapeReg).join('|')})\\s*\\(` : '(?!)';
  const holderValue = new RegExp(`^(?:await\\s+)?(?:new Slack\\s*\\(|${holder}(?:\\s*\\|\\|\\s*null)?\\s*(?:[;,)}]|$)|${factory})`);
  const valueEnd = /^(?:\|\|\s*null\s*)?(?:[;,)}\]]|\|\||&&|===|!==|\?|:|$)/.test(tail);
  const property = tail.match(/^\??\.\s*([A-Za-z_$][\w$]*)/);
  if (property) {
    if (methods.includes(property[1])) return { form: 'call', method: property[1] };
    if (isProp && !getter && keys.includes(property[1])) return { form: 'config' };
    return null;
  }
  if (tail.startsWith('[') || tail.startsWith('(')) {
    const use = listed();
    return use ? { form: `listed: ${use.why}` } : null;
  }
  const assigned = /(?:^|[^\w$.])(?:(?:const|let|var)\s+)?[\w$]+(?:\s*\??\.\s*[\w$]+)*\s*(?<![=!<>])=(?:\s*await)?$/.test(head);
  if (assigned && valueEnd) return { form: 'binding' };
  if (/\?$/.test(head) && /^:/.test(tail)) return { form: 'binding' };
  if (/^=(?![=>])/.test(tail) && (/(?:const|let|var)$/.test(head) || /(?:^|[;{}])$/.test(head))) {
    return holderValue.test(tail.slice(1).trimStart()) ? { form: 'target' } : null;
  }
  if (/(?:typeof|!|&&|\|\||\b(?:if|while)\s*\()$/.test(head) && valueEnd) return { form: 'test' };
  if (/\breturn$/.test(head) && valueEnd) return { form: 'return' };
  if (!isProp && !getter && /^:(?!:)/.test(tail) && /[{,]$/.test(head)) {
    const value = tail.slice(1).trimStart().match(new RegExp(`^(?:\\(\\)\\s*=>\\s*)?${holder}\\s*(?=[,}])`));
    if (!value) return null;
    const from = code.length - tail.length + 1;
    used.push([from, from + (tail.length - 1 - tail.slice(1).trimStart().length) + value[0].length]);
    return { form: 'key' };
  }
  const grouped = () => {
    if (!/[({,]$/.test(head) || !/^[,)}]/.test(tail)) return null;
    const group = groupAt(code, mask, start);
    if (!group) return null;
    if (group.open === '{') return isProp || getter ? null : { form: 'key' };
    if (group.open !== '(') return null;
    const opener = code.slice(0, group.at).trimEnd();
    const close = closingOf(code, mask, group.at);
    if (!isProp && !getter && (/\bfunction(?:\s+[\w$]+)?$/.test(opener) || (close >= 0 && /^\s*=>/.test(code.slice(close + 1))))) return { form: 'parameter' };
    const callee = opener.match(/([A-Za-z_$][\w$]*)$/);
    const params = callee && paramsOf(code, mask, callee[1]);
    return params && params[group.position] === 'slack' ? { form: 'argument' } : null;
  };
  const found = grouped();
  if (found) return found;
  const use = listed();
  return use ? { form: `listed: ${use.why}` } : null;
}

// Every use of the word `slack` in the production files: the ones a form explains, counted by form,
// and the ones none does, each with its file, line and the line's text.
function slackUses(methods, keys) {
  const explained = new Map();
  const unsupported = [];
  for (const { file, abs } of productionFiles()) {
    const code = codeOf(fs.readFileSync(abs, 'utf8'));
    const { spans, mask } = stringSpans(code);
    const { names, factories } = holders(code);
    const used = [];
    for (const match of code.matchAll(/(?<![\w$])slack(?![\w$])/g)) {
      const at = match.index;
      if (used.some(([from, to]) => from <= at && at < to)) continue;
      const found = classify(file, code, spans, mask, at, { methods, keys, names, factories, used });
      if (found) {
        explained.set(found.form, (explained.get(found.form) || 0) + 1);
        continue;
      }
      const line = lineAt(code, at);
      unsupported.push({ file, line, text: code.split('\n')[line - 1].trim() });
    }
  }
  return { explained, unsupported };
}

function contractRows() {
  const rows = new Map();
  const shape = [];
  const sections = new Map();
  let section = null;
  for (const line of lines(CONTRACT)) {
    if (line.startsWith('## ')) {
      section = line.slice(3).trim();
      sections.set(section, []);
      continue;
    }
    if (section) sections.get(section).push(line);
    const call = line.match(/^\| `([\w./-]+\.js)` \| `([A-Za-z_$][\w$]*)` \| ([a-z-]+) \|/);
    if (call) {
      rows.set(`${call[1]}:${call[2]}`, { file: call[1], method: call[2], tag: call[3] });
      continue;
    }
    if (section === 'Inbound event') {
      const field = line.match(/^\| `(\w+)` \| ([^|]+?) \| (required|optional) \|/);
      if (field) shape.push({ field: field[1], type: field[2].trim(), presence: field[3] });
    }
  }
  return { rows, shape, sections };
}

// Every path a section's table names in its Field column, as written: `user.id`,
// `actions[0].action_id`, `view.state.values`; a cell may name several, joined by `,` or ` or `.
const PATH = /^[A-Za-z_$][\w$]*(?:\[\d+\]|\.[A-Za-z_$][\w$]*)*$/;
function sectionFields(sectionLines) {
  const fields = new Set();
  let column = -1;
  for (const line of sectionLines) {
    if (!line.startsWith('|')) continue;
    const cells = line.split('|').slice(1, -1).map((cell) => cell.trim());
    if (column < 0) {
      column = cells.indexOf('Field');
      continue;
    }
    if (column >= cells.length || /^-+$/.test(cells[column])) continue;
    for (const span of cells[column].match(/`[^`]+`/g) || []) {
      for (const part of span.slice(1, -1).split(/,|\s+or\s+/)) {
        const field = part.trim();
        if (PATH.test(field)) fields.add(field);
      }
    }
  }
  return fields;
}

// The path read right after `index` in `code`: `.name`, `?.name`, `[0]` and `?.[0]` segments, ended
// by anything else, a computed index (`[blockId]`) included. Returns the path as the contract
// writes it (`actions[0].action_id`, empty when nothing is read) and where it ends.
function pathAfter(code, index) {
  let path = '';
  let at = index;
  for (;;) {
    const rest = code.slice(at, at + 120);
    let match;
    if ((match = rest.match(/^\s*\??\.\s*([A-Za-z_$][\w$]*)/))) path += `${path ? '.' : ''}${match[1]}`;
    else if ((match = rest.match(/^\s*(?:\?\.)?\s*\[\s*(\d+)\s*\]/))) path += `[${match[1]}]`;
    else return { path, end: at };
    at += match[0].length;
  }
}

// Every path the given files read from a payload, with where. A root is `payload` or a name assigned
// from a payload path (`const view = payload.view || {};`, `const act = payload?.actions?.[0];`),
// found to a fixed point; a read through such a name is the payload path it stands for, and a name
// nothing reads through (`const root = view?.root_view_id;`) is a read of the path it was given.
function payloadFields(files) {
  const read = new Map();
  const defines = /(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*$/;
  const ends = /^\s*(?:(?:\|\||\?\?)\s*\{\}\s*)?;/;
  for (const { file, abs } of files) {
    const code = codeOf(fs.readFileSync(abs, 'utf8'));
    const roots = new Map([['payload', '']]);
    const occurrences = () => {
      const seen = [];
      const root = new RegExp(`(?:^|[^\\w$.])(${[...roots.keys()].map(escapeReg).join('|')})\\b`, 'g');
      for (const match of code.matchAll(root)) {
        const start = match.index + match[0].length - match[1].length;
        const { path, end } = pathAfter(code, match.index + match[0].length);
        if (!path) continue;
        const prefix = roots.get(match[1]);
        const full = prefix ? `${prefix}.${path}` : path;
        const alias = code.slice(Math.max(0, start - 40), start).match(defines);
        seen.push({ root: match[1], full, line: lineAt(code, start), alias: alias && ends.test(code.slice(end, end + 20)) ? alias[1] : null });
      }
      return seen;
    };
    let seen = occurrences();
    for (;;) {
      const before = roots.size;
      for (const { full, alias } of seen) if (alias && !roots.has(alias)) roots.set(alias, full);
      if (roots.size === before) break;
      seen = occurrences();
    }
    const through = new Set(seen.map(({ root }) => root));
    for (const { full, line, alias } of seen) {
      if (alias && through.has(alias)) continue;
      if (!read.has(full)) read.set(full, []);
      const at = `${file}:${line}`;
      if (!read.get(full).includes(at)) read.get(full).push(at);
    }
  }
  return read;
}

// A type cell: `string`, `number`, `boolean`, `array`, `object`, or those joined by ` or ` with `null`.
function fits(value, typeCell) {
  return typeCell.split(/\s+or\s+/).some((type) => {
    switch (type.trim()) {
      case 'null': return value === null;
      case 'string': return typeof value === 'string';
      case 'number': return typeof value === 'number' && Number.isFinite(value);
      case 'boolean': return typeof value === 'boolean';
      case 'array': return Array.isArray(value);
      case 'object': return value !== null && typeof value === 'object' && !Array.isArray(value);
      default: return false;
    }
  });
}

test('the contract exists beside its fixtures', () => {
  assert.ok(fs.existsSync(CONTRACT), `${CONTRACT} exists`);
  assert.ok(fs.existsSync(FIXTURES), `${FIXTURES} exists`);
});

test('every production call site of a Slack method is tagged in the contract', () => {
  const methods = slackMethods();
  assert.ok(methods.includes('postMessage') && methods.includes('connect'), `Slack methods read: ${methods.join(', ')}`);
  const sites = callSites(methods);
  assert.ok(sites.size > 0, 'Ignite calls the Slack client somewhere');
  const { rows } = contractRows();
  const untagged = [...sites.values()].filter((site) => !rows.has(`${site.file}:${site.method}`));
  const badTag = [...rows.values()].filter((row) => !TAGS.has(row.tag));
  assert.deepEqual(untagged.map((s) => `${s.file}:${s.method} (lines ${s.lines.join(', ')})`), [], 'untagged call sites');
  assert.deepEqual(badTag.map((r) => `${r.file}:${r.method}: ${r.tag}`), [], 'rows with a tag other than message, panel or ignite-internal');
  console.log(`  call sites: ${[...sites.values()].map((s) => `${s.file}:${s.method}`).join(', ')}`);
});

test('every use of the word slack in a production file is a form this program understands', () => {
  const methods = slackMethods();
  const keys = slackConfigKeys();
  assert.deepEqual(keys.filter((key) => methods.includes(key)), [], 'a config key that is also a Slack method would make a config read and a call site one form');
  const { explained, unsupported } = slackUses(methods, keys);
  assert.ok(explained.has('call') && explained.has('config') && explained.has('parameter') && explained.has('key'), `forms seen: ${[...explained.keys()].join('; ')}`);
  const hint = 'write each in a form the messaging contract\'s Checks section lists, or, for a use that is not the client, add its exact text to NON_CLIENT_USES in this program with the reason';
  assert.ok(unsupported.length === 0, [...unsupported.map((use) => `unsupported client use ${use.file}:${use.line}: ${use.text}`), hint].join('\n'));
  console.log(`  slack uses: ${[...explained.entries()].map(([form, count]) => `${form} ${count}`).join(', ')}`);
});

test('every call-site row of the contract still names a call site', () => {
  const sites = callSites(slackMethods());
  const { rows } = contractRows();
  const stale = [...rows.values()].filter((row) => !sites.has(`${row.file}:${row.method}`));
  assert.deepEqual(stale.map((r) => `${r.file}:${r.method}`), [], 'rows with no call site');
});

test('the inbound event shape names who, group, thread and text', () => {
  const { shape } = contractRows();
  const fields = shape.map((f) => f.field);
  for (const required of ['from', 'group', 'thread', 'text']) {
    assert.ok(fields.includes(required), `inbound shape has ${required}: ${fields.join(', ')}`);
  }
  assert.ok(shape.some((f) => f.presence === 'optional'), 'optional parts are marked');
});

test('the contract names every payload field path the panel reads from a slash command, a button or a form', () => {
  const { rows, sections } = contractRows();
  const named = new Set();
  for (const name of INTERACTION_SECTIONS) {
    assert.ok(sections.has(name), `the contract has a section "${name}"`);
    for (const field of sectionFields(sections.get(name))) named.add(field);
  }
  const forms = sections.get('Buttons and forms').join('\n');
  assert.ok(forms.includes('`block_actions`') && forms.includes('`view_submission`'), 'Buttons and forms covers block_actions and view_submission');
  const panelFiles = new Set([...rows.values()].filter((row) => row.tag === 'panel').map((row) => row.file));
  assert.ok(panelFiles.size > 0, 'the contract tags a panel call site');
  const read = payloadFields(productionFiles().filter((entry) => panelFiles.has(entry.file)));
  for (const path of ['trigger_id', 'actions[0].action_id', 'view.callback_id', 'view.state.values']) {
    assert.ok(read.has(path), `the panel reads ${path}; paths read: ${[...read.keys()].join(', ')}`);
  }
  const uncovered = [...read.entries()].filter(([field]) => !named.has(field));
  assert.deepEqual(uncovered.map(([field, at]) => `${field} (${at.join(', ')})`), [], 'payload field paths the contract does not name');
});

test('the email and WhatsApp fixtures fit the inbound event shape', () => {
  const { shape } = contractRows();
  assert.ok(shape.length > 0, 'the contract has an inbound event table');
  const byField = new Map(shape.map((f) => [f.field, f]));
  const files = fs.readdirSync(FIXTURES).filter((name) => /^inbound-.*\.json$/.test(name)).sort();
  assert.ok(files.some((f) => f.includes('email')) && files.some((f) => f.includes('whatsapp')), `fixtures: ${files.join(', ')}`);
  for (const name of files) {
    const fixture = JSON.parse(fs.readFileSync(path.join(FIXTURES, name), 'utf8'));
    const problems = [];
    for (const { field, type, presence } of shape) {
      if (!(field in fixture)) {
        if (presence === 'required') problems.push(`${field} missing`);
        continue;
      }
      if (!fits(fixture[field], type)) problems.push(`${field} is not ${type}`);
    }
    for (const key of Object.keys(fixture)) {
      if (!byField.has(key)) problems.push(`${key} is not a field of the inbound event`);
    }
    assert.deepEqual(problems, [], `${name}`);
  }
});

(async () => {
  let failed = 0;
  for (const { name, fn } of tests) {
    try {
      await fn();
      console.log(`PASS ${name}`);
    } catch (error) {
      failed += 1;
      console.log(`FAIL ${name}: ${error.message}`);
    }
  }
  process.exit(failed ? 1 : 0);
})();
