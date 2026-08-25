'use strict';

// file_share pass-through (2026-08-08): a message with an attachment must reach the
// bridge as a normal chat message whose text carries a pointer line per file (channel +
// message ts — what stools download needs). The bridge never ferries the bytes. Every
// other subtype stays dropped.

const path = require('node:path');
const fs = require('node:fs');
const { createSlackSocketMode } = require('../slack-socket-mode');

const OUT = path.join(__dirname, 'probe-chat-file-share.out');
const results = [];
function check(name, ok, detail) {
  results.push(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` — ${detail}` : ''}`);
  if (!ok) process.exitCode = 1;
}

const t = createSlackSocketMode({ botToken: 'x', appToken: 'x', onMessage: async () => {}, log: () => {} });

const base = { type: 'message', user: 'U1', channel: 'D123', ts: '1718031600.123456', channel_type: 'im' };

// 1. file_share with files → passes, text carries the pointer line
const m1 = t.toChatMessage({ ...base, subtype: 'file_share', text: 'here is the report',
  files: [{ id: 'F1', name: 'report.txt', mimetype: 'text/plain' }] });
check('file_share passes through', m1 !== null);
check('original text kept', Boolean(m1 && m1.text.startsWith('here is the report')));
check('pointer names the file', Boolean(m1 && m1.text.includes('report.txt')));
check('pointer carries channel + ts', Boolean(m1 && m1.text.includes('--channel D123') && m1.text.includes('--ts 1718031600.123456')));

// 2. file-only message (empty text) → still passes, text is just the pointer
const m2 = t.toChatMessage({ ...base, subtype: 'file_share', text: '',
  files: [{ id: 'F2', name: 'data.csv', mimetype: 'text/csv' }] });
check('empty-text file_share passes', Boolean(m2 && m2.text.includes('data.csv')));

// 3. other subtypes still dropped
check('message_changed still dropped', t.toChatMessage({ ...base, subtype: 'message_changed', text: 'x' }) === null);
check('file_share with no files dropped', t.toChatMessage({ ...base, subtype: 'file_share', text: 'x' }) === null);

// 4. plain message unchanged
const m4 = t.toChatMessage({ ...base, text: 'hello' });
check('plain message text untouched', Boolean(m4 && m4.text === 'hello'));

fs.writeFileSync(OUT, results.join('\n') + '\n');
console.log(results.join('\n'));
