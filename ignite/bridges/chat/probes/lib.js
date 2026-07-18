'use strict';

// Shared probe harness for the chat bridge (chat-bridge-spec.md Test Plan; ADX-33(2)).
//
// ⚑ VALIDATION IS STAGED (ADX-33(2), D106). The spec's fidelity floor — a REAL
// round-trip on the ruled transport (Slack Socket Mode) — needs an owner-provisioned
// Slack app that does not exist at dispatch time. Build-time validation exercises the
// spec's probes against a LOCAL stand-in:
//   • a MOCK Socket-Mode server (an outbound-WS + HTTP endpoint the bridge drives),
//   • a THROWAWAY in-process daemon (heart store + internal API + gateway) on an
//     EPHEMERAL loopback port — NEVER the live daemon, NEVER port 7431.
// The REAL-transport round-trip (Test Plan rows 1/2/4/6 at the real floor) runs at
// p7-checkpoint with the owner present.
//
// ⚑ Timing uses Node `Date.now()` — `date +%s%3N` is broken on this box (D64).

const http = require('node:http');
const crypto = require('node:crypto');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

// The throwaway daemon is built from the SIBLING server/gateway modules — this is a
// PROBE (test harness), not the relocatable bridge runtime, so reaching into siblings
// here is fine (the existing probes do the same). The BRIDGE source never does.
const { openHeartStore, closeHeartStore } = require('../../../server/heart/heart-store');
const { createInternalApi } = require('../../../server/internal-api/dispatch');
const { createGateway } = require('../../../gateway/gateway');

function nowMs() { return Date.now(); }

function sha256(s) { return crypto.createHash('sha256').update(String(s), 'utf8').digest('hex'); }

function tmpDir(prefix) {
  return fs.mkdtempSync(path.join(os.tmpdir(), `p7-2-${prefix}-`));
}

function isoNow() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

// A capture sink: writes JSON lines to an .out file AND keeps them in memory so the
// probe can assert on them. Every probe writes its evidence to disk (never prose).
function makeCapture(outPath) {
  const lines = [];
  return {
    log(obj) {
      const entry = { ts: isoNow(), ...obj };
      lines.push(entry);
      return entry;
    },
    lines,
    flush(summary) {
      fs.writeFileSync(outPath, JSON.stringify({ summary, entries: lines }, null, 2) + '\n');
    },
  };
}

async function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

// ── The throwaway daemon ─────────────────────────────────────────────────────
//
// Stands up heart store + internal API + gateway on 127.0.0.1:<ephemeral>. Seeds a
// launch-agent catalogue job ('chat-launch') and a send-message catalogue job
// ('send-message'), plus a 'worker' launch profile so launch-agent enqueues
// re-validate. Writes a temp senders.yaml (mode 0600) with a fake kind:bridge row.
async function startThrowawayDaemon({ bridgeSenderId = 'bridge-probe' } = {}) {
  const dir = tmpDir('daemon');
  const workspaceRoot = path.join(dir, 'workspace'); // store lives at <root>/.rbtv/heart/heart.db
  fs.mkdirSync(workspaceRoot, { recursive: true });

  // Fake bridge token — obviously not a real secret (D-secrets hygiene: no real
  // tokens minted into repo/transcripts). Its sha256 is the token-hash on disk.
  const bridgeToken = `fake-bridge-token-${crypto.randomBytes(6).toString('hex')}`;
  const sendersPath = path.join(dir, 'senders.yaml');
  fs.writeFileSync(sendersPath,
    `senders:\n` +
    `  - sender-id: ${bridgeSenderId}\n` +
    `    kind: bridge\n` +
    `    token-hash: ${sha256(bridgeToken)}\n` +
    `    enabled: true\n`,
    { mode: 0o600 });
  fs.chmodSync(sendersPath, 0o600);

  const store = openHeartStore({
    runtimeStateRoot: workspaceRoot,
    profiles: { worker: { exec: ['/bin/true'] } }, // a named launch profile so launch-agent re-validates
    tools: {},
    workflows: {},
  });

  // Seed the two catalogue rows the bridge names.
  store.registerJob({
    jobId: 'chat-launch',
    actionType: 'launch-agent',
    function: 'launch-worker',
    argsSchema: JSON.stringify({ required: { profile: 'string' }, optional: { prompt: 'string', workdir: 'string' } }),
    description: 'session-creating job the chat bridge names for a first message',
    enabled: 1,
  });
  store.registerJob({
    jobId: 'send-message',
    actionType: 'send-message',
    function: 'record-message',
    argsSchema: JSON.stringify({ required: { type: 'string', thread: 'string', corpus: 'string' } }),
    description: 'send-message action-type job the chat bridge names for a follow-up',
    enabled: 1,
  });

  // Minimal spawn stub — enqueue-job + inspect(queue|jobs|ticker|daemon) never call
  // it; only inspect(status|logs) would, which these probes do not use.
  const spawnStub = {
    status: async (id) => ({ live: false, exitCode: null }),
    logs: () => ({ exists: false, data: '' }),
  };

  const secret = crypto.randomBytes(32).toString('hex');
  const internalApi = createInternalApi({ heartStore: store, spawnManager: spawnStub, secret, daemonStartTime: Date.now(), daemonConfig: {} });

  const gateway = createGateway({ dispatch: internalApi.dispatch, internalSecret: secret, sendersFilePath: sendersPath });
  const [addr] = await gateway.listen({ hosts: ['127.0.0.1'], port: 0 });
  const gatewayAddr = `127.0.0.1:${addr.port}`;

  return {
    store, gatewayAddr, bridgeToken, bridgeSenderId, port: addr.port,
    async close() {
      try { await gateway.close(); } catch {}
      try { closeHeartStore(); } catch {}
      try { fs.rmSync(dir, { recursive: true, force: true }); } catch {}
    },
  };
}

// Seed a RUNNING launch-agent execution so a chain thread `exec-<exec_id>` exists
// and inspect ticker exposes it (for the follow-up resolution probe).
function seedRunningExecution(store, { enqueuedBy = 'bridge-probe' } = {}) {
  const exec = store.recordExecutionStart({
    jobId: 'chat-launch',
    actionType: 'launch-agent',
    args: JSON.stringify({ profile: 'worker', prompt: 'hi' }),
    enqueuedBy,
    sessionMode: 'headless',
    firedTick: 1,
    firedAt: new Date(),
    sessionId: 'sess-probe',
    pid: 999999,
    profile: 'worker',
    workdir: null,
  });
  store.updateExecutionStatus(exec.exec_id, { status: 'running' });
  return store.getExecution(exec.exec_id); // carries derived thread = exec-<exec_id>
}

// ── Minimal RFC6455 WebSocket server (server side; zero npm deps) ─────────────
//
// The bridge uses the Node 24 global WebSocket CLIENT for Socket Mode; the mock
// needs a WS SERVER, which Node does not provide built-in. This is a compact
// server-side frame implementation — text + close + ping only. It is TEST harness
// code; the bridge itself opens NO server.
const WS_GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11';

function wsAccept(key) {
  return crypto.createHash('sha1').update(key + WS_GUID).digest('base64');
}

function encodeTextFrame(str) {
  const payload = Buffer.from(str, 'utf8');
  const len = payload.length;
  let header;
  if (len < 126) {
    header = Buffer.from([0x81, len]);
  } else if (len < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x81; header[1] = 126; header.writeUInt16BE(len, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x81; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2);
  }
  return Buffer.concat([header, payload]);
}

// Parse as many complete client frames as `buf` holds. Returns { messages, rest }.
function decodeFrames(buf) {
  const messages = [];
  let offset = 0;
  while (offset + 2 <= buf.length) {
    const b0 = buf[offset];
    const b1 = buf[offset + 1];
    const opcode = b0 & 0x0f;
    const masked = (b1 & 0x80) !== 0;
    let len = b1 & 0x7f;
    let cursor = offset + 2;
    if (len === 126) {
      if (cursor + 2 > buf.length) break;
      len = buf.readUInt16BE(cursor); cursor += 2;
    } else if (len === 127) {
      if (cursor + 8 > buf.length) break;
      len = Number(buf.readBigUInt64BE(cursor)); cursor += 8;
    }
    let maskKey = null;
    if (masked) {
      if (cursor + 4 > buf.length) break;
      maskKey = buf.slice(cursor, cursor + 4); cursor += 4;
    }
    if (cursor + len > buf.length) break;
    let payload = buf.slice(cursor, cursor + len);
    if (masked) {
      const out = Buffer.alloc(len);
      for (let i = 0; i < len; i++) out[i] = payload[i] ^ maskKey[i % 4];
      payload = out;
    }
    cursor += len;
    offset = cursor;
    messages.push({ opcode, text: opcode === 0x1 ? payload.toString('utf8') : null });
  }
  return { messages, rest: buf.slice(offset) };
}

// The mock Slack Socket-Mode server: HTTP (apps.connections.open + chat.postMessage)
// on the SAME port that serves the WS upgrade. Returns handles the probe drives.
async function startMockSlack({ logger = null } = {}) {
  const sentMessages = [];   // captured chat.postMessage bodies (outbound to owner)
  let wsSocket = null;       // the connected bridge client socket
  const acks = new Map();    // envelope_id -> resolver
  let connectedResolve;
  const connected = new Promise((r) => { connectedResolve = r; });

  const server = http.createServer((req, res) => {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      let json = {};
      try { json = body ? JSON.parse(body) : {}; } catch {}
      if (req.url.endsWith('/apps.connections.open')) {
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: true, url: `ws://127.0.0.1:${server.address().port}` }));
      } else if (req.url.endsWith('/chat.postMessage')) {
        sentMessages.push(json);
        res.writeHead(200, { 'content-type': 'application/json' });
        res.end(JSON.stringify({ ok: true, ts: `${Date.now() / 1000}` }));
      } else {
        res.writeHead(404); res.end('{}');
      }
    });
  });

  server.on('upgrade', (req, socket) => {
    const key = req.headers['sec-websocket-key'];
    socket.write(
      'HTTP/1.1 101 Switching Protocols\r\n' +
      'Upgrade: websocket\r\n' +
      'Connection: Upgrade\r\n' +
      `Sec-WebSocket-Accept: ${wsAccept(key)}\r\n\r\n`
    );
    wsSocket = socket;
    let buffer = Buffer.alloc(0);
    socket.on('data', (chunk) => {
      buffer = Buffer.concat([buffer, chunk]);
      const { messages, rest } = decodeFrames(buffer);
      buffer = rest;
      for (const m of messages) {
        if (m.opcode === 0x8) { try { socket.end(); } catch {} continue; }
        if (m.opcode !== 0x1 || m.text === null) continue;
        let msg;
        try { msg = JSON.parse(m.text); } catch { continue; }
        if (msg.envelope_id && acks.has(msg.envelope_id)) {
          acks.get(msg.envelope_id)();
          acks.delete(msg.envelope_id);
        }
      }
    });
    // Slack sends `hello` on connect.
    socket.write(encodeTextFrame(JSON.stringify({ type: 'hello', num_connections: 1 })));
    connectedResolve();
  });

  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const apiBase = `http://127.0.0.1:${server.address().port}`;

  // Push a Slack message event to the connected bridge and RESOLVE when the bridge
  // acks its envelope (Socket Mode requires an ack).
  function pushMessage(event, { timeoutMs = 3000 } = {}) {
    const envelopeId = crypto.randomUUID();
    const frame = { type: 'events_api', envelope_id: envelopeId, payload: { event }, accepts_response_payload: false };
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { acks.delete(envelopeId); reject(new Error('ack timeout')); }, timeoutMs);
      acks.set(envelopeId, () => { clearTimeout(timer); resolve({ envelopeId }); });
      wsSocket.write(encodeTextFrame(JSON.stringify(frame)));
    });
  }

  return {
    apiBase, connected, pushMessage, sentMessages,
    port: server.address().port,
    close() { try { if (wsSocket) wsSocket.destroy(); } catch {} try { server.close(); } catch {} },
  };
}

module.exports = {
  nowMs, sha256, makeCapture, sleep, isoNow,
  startThrowawayDaemon, seedRunningExecution, startMockSlack,
};
