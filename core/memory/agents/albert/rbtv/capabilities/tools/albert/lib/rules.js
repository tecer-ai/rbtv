'use strict';

const fs = require('node:fs');
const path = require('node:path');

function keep(text) {
  return typeof text === 'string' && text.length >= 12 && /[a-z]/i.test(text) && !text.includes('${') && !/^[./]/.test(text);
}

function extractFile(text) {
  const out = [];
  const re = /\b(?:requireThat|refuse)\s*\(/g;
  let match;
  while ((match = re.exec(text))) {
    let index = match.index + match[0].length;
    let depth = 1;
    while (index < text.length && depth) {
      if (text[index] === '(') depth += 1;
      else if (text[index] === ')') depth -= 1;
      index += 1;
    }
    const body = text.slice(match.index, index);
    const quotes = [...body.matchAll(/'((?:\\'|[^'])*)'/g)].map((item) => item[1].replace(/\\'/g, "'"));
    if (quotes.length && keep(quotes[quotes.length - 1])) out.push(quotes[quotes.length - 1]);
    for (const template of body.matchAll(/`([^`]*)`/g)) {
      for (const part of template[1].split(/\$\{[^}]*\}/)) if (keep(part.trim())) out.push(part.trim());
    }
  }
  return out;
}

function validatorRules(libraryFile) {
  const dir = path.dirname(libraryFile);
  const names = ['publish.js', 'records.js', 'board.js'];
  const rules = [];
  for (const name of names) {
    const file = path.join(dir, name);
    if (!fs.existsSync(file)) continue;
    rules.push(...extractFile(fs.readFileSync(file, 'utf8')));
  }
  return [...new Set(rules)].sort();
}

const chatHost = ['app.', 'sl', 'ack.com'].join('');

function structureText() {
  return `Proposal structure (this help is the only copy; a prompt routes here and does not restate it)

A proposal is one JSON object, or a file of that JSON. A fence of json around the object is accepted. No other keys are required. Unknown keys are ignored by the validator.

Top-level fields:
  operations  required array. Each item is one file change. Empty means no change.
  conflicts   required array. Each item is one non-empty string. A number, object, empty string or null is invalid conflict.

Operation fields, every operation:
  op           required. One of: add, supersede, archive.
  path         required string. Installation-relative, forward slashes, no empty, dot or dot-dot part, no backslash, no control character, no : * ? " < > |, no trailing dot or space, no Windows device name, not 4-archives, not agent.md, and not a symlink. One operation per path. The path must be a memory kind for the prepare input's agent.
  text         required string. The complete next file, not a patch. No NUL. No CR except a CRLF pair copied from the snapshot file. No [[. add requires a path absent from the snapshot. supersede and archive require a path present in the snapshot.
  sources      required array. Each item is a safe integer rowid of an unread owner message in the prepare input, or the exact inbox line string for this agent. No other source counts.
  reason       required. One of: owner, merge, file, fold, detail, closed, expired, index.
  explanation  required non-empty string.
  removals     array, required when any record disappears. Each item is { text, to, replacement, duplicate }. text is the removed record verbatim. to is the destination path when the record is preserved elsewhere. replacement is the exact record written at to. duplicate is true only when the record is already in the snapshot destination; omit it otherwise.

Allowed path kinds for the agent slug:
  .rbtv/agents/<slug>/_artifacts/board.md
  .rbtv/agents/<slug>/memory/learned.md
  .rbtv/agents/<slug>/memory/_artifacts/index.md
  .rbtv/agents/<slug>/memory/<slug>.md and memory/archive/<slug>.md (topic)
  .rbtv/memory/profile.md, inbox.md, workstreams.md
  .rbtv/memory/_artifacts/index.md and the index files under entities, knowledge, workspaces, timeline/daily, timeline/weekly
  .rbtv/memory/_artifacts/archive/<slug>.md
  .rbtv/memory/entities/{people,orgs,places,devices}/<slug>.md
  .rbtv/memory/knowledge/{facts,preferences,decisions,self,health}.md and knowledge/<name>/<slug>.md
  .rbtv/memory/workspaces/<slug>.md
  .rbtv/memory/timeline/daily/YYYY-MM-DD.md
  .rbtv/memory/timeline/weekly/YYYY-Www.md
  A slug is lowercase letters, digits and hyphens, starting with a letter or digit.

Reason use:
  file     inbox line into profile, knowledge or an entity. removals.to and replacement required. Keep provenance.
  fold     watch-out into this agent's learned.md as a correction rule. Keep provenance when it has a link; otherwise keep the date and cite this agent's conversation links.
  detail   move board subject state into a subject topic. The topic keeps Threads equal to the subject and every state line. The board Detail becomes ../memory/<rest>.
  expired  only a record whose body ends until YYYY-MM-DD, and that date is before the prepare input date. Learned rules never expire.
  closed   only a Recently closed board record.
  owner    owner evidence in sources. Archive and replacement both require it when they are not a relocation of an existing record.
  merge    replacement of an existing record, with owner evidence and a replacement record.
  index    index maintenance.

Record forms the validator checks:
  Dated bullet: - text (YYYY-MM-DD · agent) or - text (YYYY-MM-DD · agent/[label](URL)).
  Conversation URL the publication function accepts: https://${chatHost}/archives/CHANNEL/pDIGITS with an optional ?thread_ts= query. CHANNEL is uppercase letters and digits. Other hosts are not owner-conversation evidence.
  Inferred learned rule: - [inferred] Rule. Why: reason. (date · agent/[label](URL) · agent/[label](URL)) with two conversations.
  Correction rule: - [correction] Rule. Why: reason. (date · agent/[label](URL)).
  Topic, entity, knowledge, workspace and archive files start with frontmatter description: when ..., type, aliases: [...], then a # heading.
  Entity type is person, org, place or device, matching the folder. Knowledge type is the collection name. Topic type is subject, procedure or reference. A subject topic has exactly one Threads: none or Threads: [label](URL) line.
  Profile is # Profile — Name, then ## Who, ## Working with Name, ## Now. At most 4000 Unicode code points. No frontmatter.
  Learned file is # Learned rules — Name and at most 30 rule bullets. No frontmatter.
  Inbox is # Inbox and one dated bullet per line.
  Index is a heading and an | Open | When | table.
  Daily file name is YYYY-MM-DD, at most 40 lines, episodes and links only. Weekly file name is YYYY-Www, at most 25 lines, and each event links a daily file backed by owner messages.
  Board headings, in order: ## What matters now, ## Watch-outs, ## Timers, ## Recently closed. A subject is a ### title, 1-3 state lines, then Threads, Detail, Flags. Do not create or close subjects, and do not edit Timers, Flags or Recently closed. Every foldable watch-out is folded or removed as a duplicate in this proposal.
  Caps the validator enforces: profile 4000 characters; learned 30 rules; daily 40 lines; weekly 25 lines. On-demand files warn at 100 nonempty lines and split at 300 in the library, not by rewriting inside a proposal.
  A refusal names every failure found. Each names its path, its operation, the requirement and the expected form. The operation is "<index> <op>", for example 0 add. A failure that is not one operation has path (proposal) and operation (proposal). One file returns every independent form error. A conflict that is not a non-empty string does not stop the operation checks. Correct that file and run apply again on the same prepared run.

Prepare input fields the proposal is checked against:
  agent, date, files, messages, cursor, ceiling. messages rows have rowid, text, thread, conversation_key. Cite rowid, not a native id, unless the native id is that rowid.
`;
}

module.exports = { keep, extractFile, validatorRules, structureText };
