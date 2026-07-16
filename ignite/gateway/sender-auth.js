'use strict';

// Sender auth (L1: sender -> gateway) — spawn-profiles-spec.md Design 4 +
// gateway-cli-spec.md § Sender auth, ruled at p1-6 (D15).
//
// This is the ONLY place in the daemon that holds sender credentials. L2
// (gateway -> server core) is the internal-api contract's per-boot secret; L3 is
// the server core re-validating every request regardless of origin.

const fs = require('node:fs');
const crypto = require('node:crypto');
const yaml = require('js-yaml');

const { GatewayError, AUTH_REFUSED } = require('./errors');

const SENDER_KINDS = new Set(['owner', 'agent', 'bridge']);

// ── The startup gate (spawn-profiles-spec.md Design 4 § Startup gate) ─────────
//
// A missing, empty, or group/world-readable senders_file makes the daemon REFUSE
// TO START, loudly. Fail at boot, never at auth time: a daemon that starts with
// no sender registry is a daemon whose door is either shut (every sender refused)
// or, on the wrong code path, open — and neither is discoverable from the outside.
//
// ⚑ OPERATOR NOTE (this is the live-daemon landmine): the LIVE file is deployed
// OUTSIDE the repo, root-owned and 0600. Seed copies ship under config/ and are
// EXAMPLES — never real tokens or real hashes (D27: credentials never in git).
// Until the live file is deployed, this gate stops the daemon at boot BY DESIGN.
function loadSendersFile(filePath) {
  if (typeof filePath !== 'string' || filePath.length === 0) {
    throw new Error('senders_file path is required (config auth.senders_file)');
  }

  let stat;
  try {
    stat = fs.statSync(filePath);
  } catch (err) {
    throw new Error(
      `REFUSING TO START: senders_file is missing at ${filePath} (${err.code}). ` +
      `The named-sender registry is the gateway's only sender-auth source; without it the ingress ` +
      `cannot authenticate anyone. Deploy it root-owned with mode 0600 (a seed copy ships at ` +
      `config/senders.example.yaml — copy it, fill real sender rows, NEVER commit real tokens), ` +
      `or point auth.senders_file / RBTV_IGNITE_SENDERS_FILE at the deployed file.`
    );
  }

  if (!stat.isFile()) {
    throw new Error(`REFUSING TO START: senders_file at ${filePath} is not a regular file.`);
  }

  // Group/world-readable = readable by someone who is not the daemon user. The
  // file carries token HASHES, not plaintext, but a hash file is still an offline
  // attack surface and a disclosed sender roster.
  const mode = stat.mode & 0o777;
  if (mode & 0o077) {
    throw new Error(
      `REFUSING TO START: senders_file at ${filePath} is group/world-accessible (mode ${mode.toString(8)}). ` +
      `It must be 0600 and owned by the daemon user. Fix with: chmod 600 ${filePath}`
    );
  }

  const raw = fs.readFileSync(filePath, 'utf8');
  if (raw.trim().length === 0) {
    throw new Error(
      `REFUSING TO START: senders_file at ${filePath} is empty. ` +
      `An empty registry means no sender can ever authenticate — that is a misconfiguration, not a posture.`
    );
  }

  let doc;
  try {
    doc = yaml.load(raw);
  } catch (err) {
    throw new Error(`REFUSING TO START: senders_file at ${filePath} is not valid YAML: ${err.message}`);
  }

  const list = doc && doc.senders;
  if (!Array.isArray(list) || list.length === 0) {
    throw new Error(
      `REFUSING TO START: senders_file at ${filePath} declares no senders. ` +
      `Expected a top-level "senders:" list of { sender-id, kind, token-hash, enabled }.`
    );
  }

  // The ratified row shape (spawn-profiles-spec.md:70). A malformed row is a
  // boot failure naming the offending row — never a silently skipped sender, which
  // would present as "my token stopped working" with nothing in any log.
  const senders = [];
  const seen = new Set();
  list.forEach((row, i) => {
    const at = `senders[${i}]`;
    if (row === null || typeof row !== 'object' || Array.isArray(row)) {
      throw new Error(`REFUSING TO START: ${at} in ${filePath} is not a mapping.`);
    }
    const id = row['sender-id'];
    const kind = row.kind;
    const tokenHash = row['token-hash'];
    const enabled = row.enabled;
    if (typeof id !== 'string' || id.length === 0) {
      throw new Error(`REFUSING TO START: ${at} in ${filePath} has no "sender-id".`);
    }
    if (seen.has(id)) {
      throw new Error(`REFUSING TO START: duplicate sender-id "${id}" in ${filePath}.`);
    }
    seen.add(id);
    if (!SENDER_KINDS.has(kind)) {
      throw new Error(`REFUSING TO START: ${at} ("${id}") in ${filePath} has kind "${kind}"; expected owner|agent|bridge.`);
    }
    if (typeof tokenHash !== 'string' || !/^[0-9a-f]{64}$/i.test(tokenHash)) {
      throw new Error(
        `REFUSING TO START: ${at} ("${id}") in ${filePath} has no valid "token-hash" ` +
        `(expected a 64-char hex SHA-256 of the sender's token; plaintext tokens NEVER rest on disk).`
      );
    }
    if (typeof enabled !== 'boolean') {
      throw new Error(`REFUSING TO START: ${at} ("${id}") in ${filePath} has no boolean "enabled".`);
    }
    senders.push({ id, kind, tokenHash: tokenHash.toLowerCase(), enabled });
  });

  return senders;
}

function hashToken(token) {
  return crypto.createHash('sha256').update(String(token), 'utf8').digest('hex');
}

// ── The resolver seam (D15) ──────────────────────────────────────────────────
//
// A sender-identity resolver has ONE contract: credential material -> sender-id,
// or a refusal. v1 ships the token resolver below. The CMP-13 seat-folder checker
// (matching the live process/terminal id against the seat folder's sessions.csv)
// lands LATER as an ADDITIVE resolver implementation — the pipeline order, the
// forwarded envelope (which already carries `sender`), and the CLI surface do not
// change when it does. That is the whole point of the seam: it is the landing
// slot, reserved now so the later gate costs no rewrite.
function createTokenResolver(senders) {
  // Pre-hash comparison operates over the registry as a whole so that a miss costs
  // the same walk as a hit — no early return on the first non-match.
  const rows = senders.slice();

  return function resolveToken(credential) {
    if (typeof credential !== 'string' || credential.length === 0) return null;
    const presented = hashToken(credential);
    const presentedBuf = Buffer.from(presented, 'hex');

    let matched = null;
    for (const row of rows) {
      const stored = Buffer.from(row.tokenHash, 'hex');
      // Constant-time compare against the STORED HASH — plaintext never rests on
      // disk, and a timing-distinguishable compare would leak the hash byte by byte.
      const same = stored.length === presentedBuf.length && crypto.timingSafeEqual(stored, presentedBuf);
      if (same && matched === null) matched = row;
    }
    if (matched === null) return null;
    // A disabled sender is refused exactly like an unknown one — revocation must
    // not be distinguishable from never-existed.
    if (!matched.enabled) return null;
    return { id: matched.id, kind: matched.kind };
  };
}

// The authenticate step. Returns the resolved sender, or throws the UNIFORM
// refusal. Every failure mode — no token, unknown token, disabled sender — yields
// the SAME error with the same message, so the refusal cannot be used as an oracle
// to enumerate senders or probe token validity.
function createSenderAuthenticator({ senders, resolvers = null, logger = null }) {
  const chain = resolvers || [createTokenResolver(senders)];

  return function authenticate(credential, context = {}) {
    let sender = null;
    for (const resolve of chain) {
      const r = resolve(credential);
      if (r && sender === null) sender = r;
    }
    if (sender === null) {
      // The ATTEMPT is logged (source address, timestamp) — the refusal tells the
      // caller nothing; the daemon log tells the owner everything.
      if (logger) {
        logger({ level: 'warn', message: 'gateway refused an unauthenticated sender', source: context.source || null });
      }
      throw new GatewayError(AUTH_REFUSED, 'authentication required');
    }
    return sender;
  };
}

module.exports = { loadSendersFile, createTokenResolver, createSenderAuthenticator, hashToken };
