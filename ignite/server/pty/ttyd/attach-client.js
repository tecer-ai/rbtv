#!/usr/bin/env node
'use strict';

// The mediated (c-ii) per-session attach client + session picker — the command ttyd wraps.
//
// ttyd runs ONE of these per browser connection; its stdio IS the browser terminal
// (session-surface-spec.md Design 4). This process is NOT a harness and NEVER touches a pty:
// it is an authenticated SENDER that drives a live headed session THROUGH the daemon's two
// ratified intents, so the daemon stays the SOLE keystroke mediator and single audit point.
//
//   • picker           — ONE ttyd endpoint + a picker (OQ-C ruling D83, NOT per-session URLs):
//                         lists live HEADED sessions via `inspect` and attaches the chosen id.
//   • capture-session-screen  — POLLED, never streamed. §4 of the internal-api contract FORBIDS
//                         a stream/emitter/handle crossing the boundary, so the screen crosses as
//                         a DETACHED value snapshot and this client POLLS it on an interval — the
//                         `inspect logs {lines,nextOffset,eof}` pagination shape, applied to a
//                         screen. `repainting: true` (D99) marks a first-capture-after-reattach
//                         that is genuinely blank while the TUI repaints — poll again, NEVER render
//                         a silently-blank screen.
//   • send-to-session  — browser keystrokes are forwarded as DATA (≤ the server's PIPE_BUF bound;
//                         chunked here well under it). The daemon audits every accepted burst.
//
// Authorization is the daemon's (D89: `kind: owner` OR `enqueued_by == authenticated sender-id`).
// This client only presents its Bearer token; the terminal credential (a SEPARATE defense-in-depth
// gate, D83) lives on the ttyd listener, not here.
//
// Config (all from the environment ttyd inherits — a token NEVER travels in argv/URL):
//   IGNITE_GATEWAY_ADDR   host:port of the ignite gateway (loopback behind Serve, or tailnet).
//   IGNITE_TERMINAL_TOKEN owner-kind sender token presented as Bearer to the gateway.
//   IGNITE_SESSION_ID     optional — attach straight to this exec id, skipping the picker.
//   IGNITE_POLL_MS        optional capture poll interval (default 250).

const { call } = require('./gateway-call');

const ADDR = process.env.IGNITE_GATEWAY_ADDR || '';
const TOKEN = process.env.IGNITE_TERMINAL_TOKEN || '';
const POLL_MS = Number(process.env.IGNITE_POLL_MS) || 250;
const KEYS_CHUNK = 2048; // well under the server's 4096-byte PIPE_BUF reject bound (send-to-session)
const DETACH_BYTE = 0x1d; // Ctrl-] (GS) — reserved to detach back to the picker; rarely used by TUIs

const out = (s) => process.stdout.write(s);
const clearScreen = () => out('\x1b[2J\x1b[3J\x1b[H');
const nl2crlf = (s) => s.replace(/\r?\n/g, '\r\n');

function fail(msg) {
  clearScreen();
  out(`ignite attach client: ${msg}\r\n`);
}

// A gateway call that fails LOUD on transport error but returns the typed refusal as data.
async function gw(intent, payload) {
  return call(ADDR, TOKEN, intent, payload);
}

// List the LIVE HEADED sessions the picker offers. `inspect ticker` names every live execution;
// `inspect status <id>` carries the `sessionMode`/`live` this filter needs (the ticker snapshot
// does not). Headed-only + live-only — the picker "naturally lists only headed sessions" (D83).
async function listHeadedSessions() {
  const t = await gw('inspect', { target: 'ticker' });
  if (!t.ok) throw new Error(`inspect ticker refused: ${(t.error && t.error.code) || t.status}`);
  const live = (t.result && t.result.live_sessions) || [];
  const headed = [];
  for (const s of live) {
    const st = await gw('inspect', { target: 'status', id: s.exec_id });
    if (!st.ok) continue;
    const r = st.result || {};
    if (r.sessionMode === 'headed' && r.live) {
      headed.push({ execId: s.exec_id, sessionId: r.sessionId || r.session_id || null, profile: r.profile || null });
    }
  }
  return headed;
}

// Read one line from stdin in COOKED mode (the picker prompt). Returns the trimmed line.
function readLine() {
  return new Promise((resolve) => {
    const stdin = process.stdin;
    if (stdin.isTTY) stdin.setRawMode(false);
    stdin.resume();
    stdin.setEncoding('utf8');
    let buf = '';
    const onData = (d) => {
      buf += d;
      const i = buf.indexOf('\n');
      if (i >= 0) {
        stdin.removeListener('data', onData);
        stdin.pause();
        resolve(buf.slice(0, i).replace(/\r$/, '').trim());
      }
    };
    stdin.on('data', onData);
  });
}

async function pickSession() {
  for (let attempt = 0; attempt < 600; attempt += 1) { // up to ~5 min of "waiting for a session"
    let sessions;
    try {
      sessions = await listHeadedSessions();
    } catch (err) {
      fail(`could not list sessions (${err.message}). Retry? [enter] `);
      await readLine();
      continue;
    }
    clearScreen();
    out('\x1b[1mIgnite — headed sessions\x1b[0m  (server-owned pty; the browser only views/types)\r\n\r\n');
    if (sessions.length === 0) {
      out('  no live headed sessions right now.\r\n\r\n');
      out('  [enter] refresh   [q] quit\r\n');
      const line = await readLine();
      if (line.toLowerCase() === 'q') return null;
      continue;
    }
    sessions.forEach((s, i) => {
      out(`  [${i + 1}] exec ${s.execId}` + (s.profile ? `  profile=${s.profile}` : '') +
          (s.sessionId ? `  session=${s.sessionId}` : '') + '\r\n');
    });
    out('\r\n  pick a number, or [r] refresh, [q] quit: ');
    const line = await readLine();
    if (line.toLowerCase() === 'q') return null;
    if (line.toLowerCase() === 'r' || line === '') continue;
    const n = Number(line);
    if (Number.isInteger(n) && n >= 1 && n <= sessions.length) return sessions[n - 1].execId;
    // invalid — loop and re-list
  }
  return null;
}

// Forward keystroke bytes to the live session, chunked under the server's reject bound.
async function sendKeys(execId, buf) {
  // Browser keystrokes arrive UTF-8 (xterm forwards UTF-8 over the ws); send them as the SAME
  // UTF-8 string so the daemon re-encodes to identical bytes. Typed events are tiny, but a PASTE
  // arrives as ONE large data event, so a chunk boundary can land INSIDE a multibyte sequence.
  // send-to-session re-decodes each chunk independently, so a split char would arrive as U+FFFD —
  // so every chunk MUST end on a UTF-8 character boundary, never mid-sequence.
  let i = 0;
  while (i < buf.length) {
    let end = Math.min(i + KEYS_CHUNK, buf.length);
    // If the NEXT chunk would start on a UTF-8 continuation byte (10xxxxxx), this chunk splits a
    // character — back the boundary up to the character's start. A UTF-8 char is ≤4 bytes, so this
    // backs off at most 3 bytes and never underflows KEYS_CHUNK (2048).
    if (end < buf.length) {
      let back = 0;
      while (end > i + 1 && back < 3 && (buf[end] & 0xc0) === 0x80) { end -= 1; back += 1; }
    }
    const slice = buf.slice(i, end);
    const res = await gw('send-to-session', { id: execId, data: slice.toString('utf8') });
    if (!res.ok) {
      const code = (res.error && res.error.code) || res.status;
      if (code === 'NOT_FOUND' || (res.error && res.error.details && res.error.details.check === 'E_SESSION_NOT_LIVE')) {
        throw new Error('session ended');
      }
      // A transient refusal (e.g. audit hiccup) is surfaced but not fatal.
      return;
    }
    i = end;
  }
}

// Attach: raw stdin -> send-to-session; poll capture-session-screen -> render. Resolves on detach
// (Ctrl-]) or when the session ends. Returns 'detach' to go back to the picker, 'ended' otherwise.
function attach(execId) {
  return new Promise((resolve) => {
    const stdin = process.stdin;
    if (stdin.isTTY) stdin.setRawMode(true);
    stdin.resume();
    let lastScreen = null;
    let done = false;
    let timer = null;

    const finish = (why) => {
      if (done) return;
      done = true;
      if (timer) clearInterval(timer);
      stdin.removeListener('data', onKeys);
      if (stdin.isTTY) stdin.setRawMode(false);
      stdin.pause();
      resolve(why);
    };

    const onKeys = (chunk) => {
      const buf = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      if (buf.includes(DETACH_BYTE)) { finish('detach'); return; }
      sendKeys(execId, buf).catch((err) => {
        if (/session ended/.test(err.message)) { fail('session ended.'); finish('ended'); }
      });
    };
    stdin.on('data', onKeys);

    clearScreen();
    out('\x1b[2m(attached — Ctrl-] to return to the picker)\x1b[0m\r\n');

    const poll = async () => {
      let res;
      try {
        res = await gw('capture-session-screen', { id: execId });
      } catch (err) {
        return; // transient transport blip; next tick retries
      }
      if (!res.ok) {
        const code = (res.error && res.error.code) || res.status;
        if (code === 'NOT_FOUND' || (res.error && res.error.details && res.error.details.check === 'E_SESSION_NOT_LIVE')) {
          fail('session ended.'); finish('ended');
        }
        return;
      }
      const r = res.result || {};
      // D99: a repainting capture is genuinely blank while the TUI redraws after a reattach.
      // NEVER render it as final — skip this frame and poll again.
      if (r.repainting) return;
      const screen = typeof r.screen === 'string' ? r.screen : '';
      if (screen === lastScreen) return; // no change — avoid needless flicker
      lastScreen = screen;
      out('\x1b[H\x1b[2J' + nl2crlf(screen));
    };

    timer = setInterval(() => { poll().catch(() => {}); }, POLL_MS);
    poll().catch(() => {});
  });
}

async function main() {
  if (!ADDR || !TOKEN) {
    fail('IGNITE_GATEWAY_ADDR and IGNITE_TERMINAL_TOKEN must be set in the environment.');
    process.exit(2);
  }
  // Fail loud early if the gateway is unreachable or the token is rejected.
  try {
    const probe = await gw('inspect', { target: 'daemon' });
    if (!probe.ok && (probe.error && probe.error.code) === 'AUTH_REFUSED') {
      fail('the gateway refused this terminal token (AUTH_REFUSED).');
      process.exit(3);
    }
  } catch (err) {
    fail(`the ignite gateway is unreachable: ${err.message}`);
    process.exit(4);
  }

  const direct = process.env.IGNITE_SESSION_ID ? Number(process.env.IGNITE_SESSION_ID) : null;
  for (;;) {
    const execId = direct || await pickSession();
    if (!execId) { clearScreen(); out('bye.\r\n'); process.exit(0); }
    const why = await attach(execId);
    if (direct) { clearScreen(); out('bye.\r\n'); process.exit(0); } // direct-attach mode has no picker to return to
    if (why === 'detach') continue; // back to the picker
    // 'ended' — brief pause then re-list
    await new Promise((r) => setTimeout(r, 900));
  }
}

main().catch((err) => { fail(`fatal: ${err.message}`); process.exit(1); });
