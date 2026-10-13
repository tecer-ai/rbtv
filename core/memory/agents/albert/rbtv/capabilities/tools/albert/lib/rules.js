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
  sources      required array. Each item is a safe integer rowid of an unread owner message in the prepare input, or an exact inbox line from the snapshot file .rbtv/memory/inbox.md. Any agent's line counts, including one ending · SLUG for another agent. No other source counts.
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

Archived removal (forget, or the reverse of an item that created a record). Correct a refused proposal from this section. Do not invent a field that is not named here.

leave: true on an archive operation whose path is an entity, knowledge, topic or workspace file. text is the snapshot file, not a stub and not a patch. The publisher unlinks that path. It does not write text.
item: a non-empty string on that operation, only for a reversal. It is not a sources entry. Example: RUN#N.
Forget uses reason owner, sources containing an exact inbox line (any agent) or an unread owner rowid, and no item. Reversal uses reason owner, sources empty, and item set to the item reference.

One proposal, five operations, in this order:
1. archive the whole file, leave true, text equal to the snapshot. removals is one item per body record: { "text": "<record line>", "to": ".rbtv/memory/_artifacts/archive/<slug>.md" }.
2. add that archive path, or supersede it when the file already exists. text is an archive file the checker already accepts (description: when ..., type: reference, aliases: [...], a # heading), plus a reason bullet for each consumed line and a verbatim fence. The fence body is the snapshot file, byte for byte, including its frontmatter. records() skips the fence. The reason bullet is the record.
   Forget bullet, one per consumed line: - Reason: owner asked to forget. Source: <exact line> (YYYY-MM-DD · agent)
   Reversal bullet: - Reason: reversed. Source: <item reference> (YYYY-MM-DD · agent)
   A reversal that consumes a capture still in the inbox also carries that line verbatim in the archive text.
3. supersede each index that links the file. reason index. text is the current index with only the rows whose markdown link resolves to the archived path removed. removals names each dropped row. Do not restore an earlier index item. Other rows stay byte for byte.
4. supersede each day or week file that mentions it. A timeline line is dropped when its URL occurs in the archived file and in no file that stays after the proposal. A line this same proposal removes from inbox.md does not stay. The archive does not count. text is the current file with only those episodes removed. removals names each dropped episode. Other episodes stay.
5. supersede .rbtv/memory/inbox.md. reason owner. sources includes each consumed line (beside or instead of an unread owner rowid). text is the inbox without those lines. removals is { "text": "<line>", "to": ".rbtv/memory/_artifacts/archive/<slug>.md" } for the request line (Owner asks to forget: ..., any slug) and, if it is still in the inbox, the original capture of the fact (a line whose URL occurs in the archived file, or that contains the file's # heading). The archive entry's reason bullet is Reason: owner asked to forget. Source: <the line> for each. The publisher deletes those lines. Do not invent a new inbox line.

An index row points at the record when its markdown link, resolved from the index file, is that path. A timeline line points at the record when an https URL in the line occurs in the archived file. The archive path is .rbtv/memory/_artifacts/archive/<slug>.md. Not 4-archives. Not an agent memory/archive/ path.

The subject of Owner asks to forget: <subject>. must occur in the file this proposal archives with leave: true. Citing a line in sources without operation 5 quiets check and leaves the line in the bundle a turn start reads. Do not do that.

Expected forms for a refusal of this shape:
  removals.to is an archive file whose verbatim fence equals this file
  an archive file in this proposal holds the verbatim record
  keep the line, or archive the record it points at in this proposal
  a line whose link or source URL is the archived record
  Reason: owner asked to forget with owner evidence, or Reason: reversed with Source: the item reference
  a relative link to a memory file this proposal leaves in place
  text equals the snapshot file being archived
  entity, knowledge, topic or workspace
  file the line as a record, or carry it verbatim in an archive entry of the same proposal
  the record the request line names is archived with leave: true in this proposal
  a timeline line may be dropped when its URL occurs in the archived file and in no file that stays in active memory after the proposal; an inbox line this proposal consumes does not count as staying; the archive is not active memory
  sources are unread owner message rowids or exact inbox lines

Restore of an archived removal (reversing a reversal or a forget). One proposal against the post-removal snapshot. No new owner evidence. Do not put the consumed inbox lines back. They were a capture and a request, not the record. Restoring them re-raises the request. There is no mechanical inverse that writes an inbox line back.
1. add the original path, text equal to the fence body, sources empty, reason owner.
2. supersede the index back to the text that contains the row, reason index, sources empty.
3. supersede the day file back to the text that contains the episode, sources empty. The episode's URL must occur in the restored file.
4. supersede the archive file. Keep the fence and the reason bullet. Add a line # Restored. sources empty.

Prepare input fields the proposal is checked against:
  agent, date, files, messages, cursor, ceiling. messages rows have rowid, text, thread, conversation_key. Cite rowid, not a native id, unless the native id is that rowid.
`;
}

module.exports = { keep, extractFile, validatorRules, structureText };
