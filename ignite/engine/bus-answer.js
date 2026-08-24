'use strict';

// ── THE OWNER'S ANSWER, ON THE BUS (task 7.771; owner ruling 2026-08-11, design
// `one-readiness-predicate.md` § D8) ──────────────────────────────────────────────────────────
//
// THE GAP THIS CLOSES. When the owner answers a seat's question in Slack, the reply is delivered
// as a `session-create` at that seat's own home — and until this module NOTHING recorded anywhere
// that the ask had been answered. The coordination bus kept every question and no reply, so
// `execution-record.js#openOwnerAsks` (which walks that bus pairing each `from: <seat>
// to: owner` ask against a later `type: answer` addressed back) could never see the pairing close
// and fell through to a heart-store term that is unreachable from inside a seat cage.
//
// ⚑ ONE LINE ON THE BUS, PER DELIVERED REPLY, AND COORD WRITES IT. `coordination/messages.md` is
// `coord.py`'s file. A second writer of it from JavaScript is the defect class the whole D8 design
// deletes — two readers of one question that disagree — so this module holds no format, no lock
// and no append: it shells to `coord.py send --type answer` and lets the one writer write.
//
// ⚑ WHY THE DAEMON SHELLS AND THE BRIDGE DOES NOT. The chat bridge is structurally forbidden from
// spawning (`chat-bridge-spec.md` line 14 "the bridge holds NO spawn/queue capability" and line 26
// "no queue handle, no spawn path"; enforced by `bridges/chat/probes/probe-chat-boundary.js`, which
// scans EVERY runtime `.js` in that directory for `child_process` and derives its file list from
// the directory so a new file is scanned automatically). So the bridge makes ONE gateway call
// (`record-bus-answer`) and the child process is held HERE. That is the shape
// `bridges/chat/live-sessions.js:10-15` already describes: the warm-session manager hit this exact
// wall, was moved server-side, and the bridge kept only a caller. Routing the spawn through a
// helper in `bridges/chat/lib/` would pass the probe's regex while handing the bridge process a
// spawn handle — a guard blind to the thing it guards, and correctly refused.
//
// ⚑ `--force` IS NECESSARY, AND ITS COST IS NAMED. `cmd_send` carries four gates this call must
// not be able to lose the owner's answer to, all of them written for SEAT-TO-SEAT traffic:
//   · length      — `MESSAGE_MAX = 2000`; an owner's Slack reply is arbitrary text and routinely
//                   longer. This one alone makes `--force` non-optional.
//   · closing seat — a seat mid-close refuses a peer's message; the owner answering the question
//                   that seat asked is not a peer interrupting it.
//   · bounded inbox — a `senders:` bound is a ruling about which SEATS may spend a seat's context.
//   · unknown recipient — a seat with no roster row and no briefing `agent:` name.
// A refusal at any of them writes NOTHING, which is precisely the durability gap being closed.
// What `--force` does NOT lift: `--re`'s own validation (no override exists), the `ask`-from-an-
// unaddressable-sender gate, and the never-initiate-to-`master` gate — none of which this call can
// trip (it sends `--type answer` to a seat BY NAME).
//
// ⚑ `--re` IS RESOLVED, NOT GUESSED, and that is what keeps `--force` from also making coord's own
// `pending` view lie. The ask id is NOT reachable from the bridge — `agentThreads` is keyed
// `<goalId>#<agent>` and stores only `threadTs` (`chat-bridge.js`) — but it IS reachable HERE, from
// the goal's own bus, through `execution-record.js#openOwnerAsks`: the SAME pairing the hold makes,
// so `pending` and the hold can never disagree about which question is still open. An answer with
// no `--re` leaves the ask open for every reader forever. Coord already accepts `--re` on an `ask`
// OR an `escalation`; if the oldest open row is an escalation (no ask), that is what we settle.
// `--supersedes` of one escalation by another is not a close. C78's pending-view settle stays the
// belt for console answers that never pass through this module.

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFile } = require('node:child_process');
// The ONE interpreter resolver this repo has (`python3` is a Microsoft-Store LIE on Windows) and
// the address of the one writer — both exactly as `engine/seeding.js` names them, and for its
// stated reason: a daemon-fired exec inherits the systemd --user manager's PATH, which does not
// carry `~/.local/bin`, so the `coordinate` symlink resolves interactively and NOT here.
const { requirePythonCmd } = require('../lib/python-cmd');
const { openOwnerAsks } = require('./execution-record');
// The ferry's own name guard: `^[A-Za-z0-9][A-Za-z0-9._-]*$` minus the reserved `owner`. It refuses
// path separators, `..`, control characters and the empty string — a goal or seat token carrying
// any of them would resolve a directory OUTSIDE `.rbtv/goals/`, and both tokens reach this daemon
// from an internet-facing component.
const { isSafeName } = require('../bridges/chat/bus-ferry');

// The ON-DEMAND chair, mirrored from `coord.py#STAFF_SEATS` — the same one-line mirror the
// ferry keeps of that file's name guard. The `consultant` chair this list used to also carry is
// deleted [T2-R17, D-7-ruling]; `leader` is the only member now. A require across the Python
// boundary does not exist to be had, so this mirror stays hand-kept.
const STAFF_SEATS = ['leader'];

const COORD_PY = path.join(__dirname, '..', 'team-kit', 'coord.py');
const BUS_RELPATH = ['coordination', 'messages.md'];
// coord's send path does a roster read, an append under its own lock, and a best-effort wake pass.
// Milliseconds on a room with no panes; the bound is here so a wedged wake can never hold a
// gateway request open.
const DEFAULT_TIMEOUT_MS = 30000;
// `sent message #14 (owner -> plan-interviewer, type: answer, re #9)` — coord's own success line.
const SENT_RE = /^sent message #(\d+)\b/m;

function refuse(reason, extra = {}) {
  return { recorded: false, reason, ...extra };
}

// The oldest still-open `ask` this seat put to the owner, or — if none — the oldest still-open
// `escalation`. Coord accepts `--re` on either type. A note (or anything else) is left unlinked.
function askToSettle(goalDir, seat) {
  let text;
  try { text = fs.readFileSync(path.join(goalDir, ...BUS_RELPATH), 'utf8'); } catch { return null; }
  const open = openOwnerAsks(text, seat);
  const ask = open.find((r) => r.type === 'ask');
  if (ask) return ask.id;
  const esc = open.find((r) => r.type === 'escalation');
  return esc ? esc.id : null;
}

// Record ONE `type: answer` row addressed to `seat` on `goal`'s coordination bus, as the owner.
// Resolves `{ recorded, ... }` — a DECISION as data, never a throw: the caller's delivery already
// happened and must not be undone by a bookkeeping failure.
//
// ⚑ THE BODY NEVER TOUCHES A SHELL. It rides `--file` (which is also what coord requires of
// arbitrary text — a shell eats backticks and `$(…)`), written into a private temp dir, and
// `execFile` passes argv directly with no shell in the path.
function recordBusAnswer({ workspaceRoot, goal, seat, corpus, timeoutMs = DEFAULT_TIMEOUT_MS }) {
  if (!workspaceRoot) return Promise.resolve(refuse('no-workspace-root'));
  if (!isSafeName(goal)) return Promise.resolve(refuse('goal-not-a-name'));
  if (!isSafeName(seat)) return Promise.resolve(refuse('seat-not-a-name'));
  if (typeof corpus !== 'string' || corpus.trim().length === 0) return Promise.resolve(refuse('empty-corpus'));

  const goalDir = path.join(workspaceRoot, '.rbtv', 'goals', String(goal));
  try {
    if (!fs.statSync(goalDir).isDirectory()) return Promise.resolve(refuse('no-such-goal'));
  } catch { return Promise.resolve(refuse('no-such-goal')); }
  // The seat must EXIST IN THIS GOAL. Since W3 coord's unknown-recipient gate is `--force`-PROOF,
  // so this is no longer the only thing standing between a typo'd seat name and a permanent row
  // addressed to nobody — but it stays, because it refuses HERE with a named reason
  // (`no-such-seat`) the bridge can report, instead of surfacing as a generic `coord-refused`.
  // A seat with a folder but no roster row and no briefing would now be refused by coord itself.
  // ⚑ W8 (adv, C78) — THE STAFF CHAIR IS EXEMPT FROM THE DIRECTORY TEST. `leader` (the only
  // member of `STAFF_SEATS` — the `consultant` chair this comment used to also name is deleted
  // [T2-R17, D-7-ruling]) is ON-DEMAND: coord admits it as a recipient unconditionally
  // (`known_recipients` unions `STAFF_SEATS` in), precisely so mail always reaches the chair
  // whether or not it is sitting. Its seat FOLDER, by contrast, appears when the chair is
  // materialized or first spawned — measured 2026-08-14: of six live goals only one had a
  // `seats/leader/` on disk. A directory test would therefore refuse the owner's REPLY TO AN
  // ESCALATION on five of them, and
  // an escalation the owner answered into a `no-such-seat` is the silent stall this program is
  // about, arriving from the one direction nobody watches. The typo protection this test exists
  // for is unaffected: coord's own unknown-recipient gate is `--force`-proof and still refuses
  // every name no roster, briefing, group or staff chair carries.
  if (!STAFF_SEATS.includes(String(seat))) {
    try {
      if (!fs.statSync(path.join(goalDir, 'seats', String(seat))).isDirectory()) return Promise.resolve(refuse('no-such-seat'));
    } catch { return Promise.resolve(refuse('no-such-seat')); }
  }

  let python;
  try { python = requirePythonCmd(); } catch (err) { return Promise.resolve(refuse('no-python', { error: err.message })); }

  const re = askToSettle(goalDir, seat);
  let dir;
  let bodyFile;
  try {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-bus-answer-'));
    bodyFile = path.join(dir, 'body.md');
    fs.writeFileSync(bodyFile, corpus, 'utf8');
  } catch (err) {
    return Promise.resolve(refuse('body-file-failed', { error: err.message }));
  }

  const argv = [COORD_PY, '--package', goalDir, 'send', String(seat),
    '--type', 'answer', '--file', bodyFile, '--as', 'owner', '--force'];
  if (re !== null) argv.push('--re', String(re));

  return new Promise((resolve) => {
    execFile(python, argv, { timeout: timeoutMs, encoding: 'utf8', maxBuffer: 1024 * 1024 }, (err, stdout, stderr) => {
      try { fs.rmSync(dir, { recursive: true, force: true }); } catch { /* temp dir; nothing rides on it */ }
      const out = String(stdout || '');
      if (err) {
        return resolve(refuse('coord-refused', {
          re,
          exit: err.code === undefined ? null : err.code,
          detail: (String(stderr || '').trim() || out.trim()).slice(0, 600),
        }));
      }
      const m = out.match(SENT_RE);
      // coord exited 0 without its own success line: treat it as a refusal rather than claim a row
      // that may not be there. A verdict comes from what the writer SAID it wrote, never from the
      // exit code alone.
      if (!m) return resolve(refuse('coord-said-nothing', { re, detail: out.trim().slice(0, 600) }));
      resolve({ recorded: true, msgId: Number(m[1]), re });
    });
  });
}

module.exports = { recordBusAnswer, askToSettle, DEFAULT_TIMEOUT_MS };
