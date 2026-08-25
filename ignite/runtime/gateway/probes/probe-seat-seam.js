'use strict';

// probe-seat-seam — task 7.10 / CMP-13: does a PROVEN SEAT actually cross the ingress?
//
// WHY THIS EXISTS, and it is not a hypothetical: 7.10 first shipped with this seam BROKEN, and
// every other check was green while it was. The peer resolver's own probe passed (it resolves a
// seat, caged and uncaged). The authz policy's check passed (it grants `leader` when given a
// sender carrying `seat: 'leader'`). Both halves green — and the envelope builder in gateway.js
// listed `{id, kind, via}` explicitly, so the seat was DROPPED in between and never reached the
// core. The authz wiring was unreachable in production and nothing said so.
//
// That is `p-green-harness-over-a-broken-mechanism` exactly: the policy check HANDED the code the
// value the ingress was supposed to produce, so it exercised everything except the production of
// it. The seam is where the feature lives, and only a request driven end-to-end can see it.
//
// So this probe drives the REAL gateway over a REAL socket and asserts on what the DISPATCH
// endpoint received — never on what the resolver returned.
//
// The capture is truncated at module load, before any work, so a probe that dies at start leaves
// an EMPTY capture rather than the previous run's stale `EXIT: 0` (D51 evidence-husk hazard).

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const start = Date.now();
const outPath = path.join(__dirname, 'probe-seat-seam.out');
fs.writeFileSync(outPath, '');

const { createGateway } = require('../gateway');
const { hashToken } = require('../sender-auth');
// The composition root's own wiring: server/index.js injects exactly this function. Requiring it
// HERE (in a probe) does not breach the gateway boundary — probe-gateway-boundary scans the
// gateway directory's own modules, and the boundary rule is about what the SHIPPED gateway
// reaches, not about what a test harness may assemble.
const { resolvePeerSeat } = require('../../seat-identity/peer-identity');
const { deriveLease } = require('../../lease/lease');

function out(...lines) { fs.appendFileSync(outPath, lines.join('\n') + '\n'); }

const checks = [];
function check(name, pass, detail) {
  checks.push({ name, pass });
  out(`${pass ? 'PASS' : 'FAIL'}  ${name}${detail ? ' — ' + detail : ''}`);
}

out('COMMAND: node runtime/gateway/probes/probe-seat-seam.js');

// A real token, minted per run; only its HASH reaches the registry file, and the token itself is
// never written into this capture — a token in evidence is a leaked token.
const TOKEN = crypto.randomBytes(16).toString('hex');
const sendersFile = path.join(os.tmpdir(), `ignite-seam-senders-${Date.now()}-${process.pid}.yaml`);
fs.writeFileSync(sendersFile,
  `senders:\n  - sender-id: seam-sender\n    kind: agent\n    token-hash: ${hashToken(TOKEN)}\n    enabled: true\n`);
fs.chmodSync(sendersFile, 0o600);

function starttimeOf(pid) {
  const raw = fs.readFileSync(`/proc/${pid}/stat`, 'utf8');
  return raw.slice(raw.lastIndexOf(')') + 2).trim().split(/\s+/)[22 - 3];
}

// A LIVE, MATERIALIZED, ROSTERED seat registered to this process — which is a genuine ancestor of
// the client below, so the identity match is honest rather than relaxed. The fixture supplies
// measurables only; it never supplies the seat NAME to the resolver.
//
// ── 7.607 E3b — RE-KEYED TO THE GOAL-DIRECT GRAMMAR (E2a's cutover; this probe was its fallout) ──
//
// The shape is now `<ws>/.rbtv/goals/<goal>/seats/<seat>/` and every apparatus file sits at GOAL
// level: `taskforce.csv` and `sessions.csv` beside `seats/`, no `runs/run-N/` segment and no
// `runs.csv` at all (`decisions.md#d-extinguishment-design-lock` items 6/9; `seat-folder.js`
// parses ONLY this shape and deliberately does not accept the old one). Under the old fixture
// `parseSeatPath` still matched — `seats` is found by `lastIndexOf` — but it named the RUN dir as
// the goal, so `goals.csv` membership failed and every seat was refused: the probe reported
// `sender.seat=undefined` and read as a broken SEAM while the seam was fine and the FIXTURE was
// stale. NOT ONE ASSERTION BELOW IS WEAKENED BY THE RE-KEY; only the shape on disk moved.
// Every fixture root is remembered so the teardown can remove it. It was NOT removed before, and
// this probe runs hourly under the probe-suite timer: 308 `ignite-seam-*` trees had accumulated in
// /tmp by 2026-08-09, two per run since 2026-08-08. Fixed here rather than filed because the leak
// is in the function this change was already rewriting.
const fixtureRoots = [];
function fixture(seat) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'ignite-seam-'));
  fixtureRoots.push(root);
  const goalDir = path.join(root, '.rbtv', 'goals', 'seam-goal');
  const seatDir = path.join(goalDir, 'seats', seat);
  fs.mkdirSync(seatDir, { recursive: true });
  fs.writeFileSync(path.join(root, '.rbtv', 'goals', 'goals.csv'), 'name,created,due,type,status\nseam-goal,2026-07-27,,one-shot,active\n');
  fs.writeFileSync(path.join(goalDir, 'taskforce.csv'), `seat,role\n${seat},executor\n`);
  fs.writeFileSync(path.join(seatDir, 'seat.md'), `---\nseat: ${seat}\n---\n`);
  fs.writeFileSync(path.join(goalDir, 'sessions.csv'),
    `seat,session-id,pid,pid-starttime,started,ended\n${seat},s1,${process.pid},${starttimeOf(process.pid)},t,\n`);
  return seatDir;
}

// ⚠ THE LEASE, SUPPLIED AS A MEASURABLE — never as a verdict (7.607 E3b). E2a re-founded the
// identity gate's L2 on `runtime/lease/lease.js`, so a seat is only admitted while its goal's tmux
// ROOM exists. This probe must not start a tmux server to satisfy that: it runs under the hourly
// probe-suite timer, and a suite probe that creates rooms would land them on the DEFAULT socket the
// moment `TMUX_TMPDIR` were unset or wrong — on this box that server carries the owner's live
// sessions. So the ONE tmux read is injected instead, exactly as `lease.js`'s own header sanctions
// ("injectable so a probe supplies a real fixture server's output"): the real `deriveLease` runs,
// over a real `sessions.csv`, and only the `tmux list-sessions` line is stood in for. The verdict
// is still computed by the module under test.
const seamLease = (o) => deriveLease({
  ...o,
  tmuxProbe: () => ({ sessions: 'seam-goal\n', panes: '' }),
});

const clientFile = path.join(os.tmpdir(), `ignite-seam-client-${process.pid}.js`);
fs.writeFileSync(clientFile, `
const http=require('http');
const body=JSON.stringify({intent:'inspect',payload:{target:'queue'}});
const req=http.request({host:'127.0.0.1',port:Number(process.env.PORT),path:'/',method:'POST',
  headers:{'content-type':'application/json','content-length':Buffer.byteLength(body),
           'authorization':'Bearer '+process.env.TOK,
           // A DELIBERATELY FALSE claim. Nothing the caller says may influence the verdict.
           'x-seat':'a-seat-i-am-not'}},r=>{r.resume();r.on('end',()=>process.exit(0));});
req.on('error',()=>process.exit(3));
req.end(body);
`);

const seen = [];
const gateway = createGateway({
  // A spy dispatch: what arrives HERE is the measurement. The far side of the seam.
  dispatch: async (envelope) => { seen.push(envelope); return { ok: true, data: {} }; },
  internalSecret: 'seam-probe-internal-secret',
  sendersFilePath: sendersFile,
  // The composition root injects `resolvePeerSeat` itself (`runtime/index.js`); the only difference
  // here is the lease reader it resolves L2 through — a probe's injection point, never the wire's.
  checkPeerSeat: (conn) => resolvePeerSeat(conn, { readLease: seamLease }),
});

async function main() {
  const [addr] = await gateway.listen({ hosts: ['127.0.0.1'], port: 0 });
  const port = addr.port;

  const call = (cwd) => new Promise((resolve) => {
    const c = spawn(process.execPath, [clientFile],
      { cwd, env: { ...process.env, PORT: String(port), TOK: TOKEN }, stdio: 'ignore' });
    c.on('exit', (code) => setTimeout(() => resolve(code), 150));
    c.on('error', () => resolve(-1));
  });

  // ── S1 — the seam itself ────────────────────────────────────────────────────
  seen.length = 0;
  const code = await call(fixture('leader'));
  const env1 = seen[0];
  check('the request completed through the real gateway', code === 0, `client exit=${code}`);
  check('dispatch was reached', !!env1, `dispatch calls=${seen.length}`);
  check('THE SEAM: the proven seat is ATTACHED and carried into dispatch',
    !!(env1 && env1.sender && env1.sender.seat === 'leader'),
    `sender.seat=${env1 && env1.sender && env1.sender.seat}`);
  check('the envelope records HOW the seat was proven',
    !!(env1 && env1.sender && typeof env1.sender.seatProvenBy === 'string'));

  // ── S2 — ADDITIVE: a non-seat caller is unaffected ─────────────────────────
  // If this ever fails, the resolver has stopped being additive and has become a second gate.
  seen.length = 0;
  const code2 = await call(os.tmpdir());
  const env2 = seen[0];
  check('a caller outside any seat folder still authenticates (additive, not a new gate)',
    code2 === 0 && !!env2, `exit=${code2}`);
  check('...and its envelope carries NO seat — byte-identical to the pre-7.10 shape',
    !!(env2 && env2.sender && env2.sender.seat === undefined));

  // ── S3 — the seat is MEASURED, not carried by the token or claimed ─────────
  // ONE token, TWO folders, TWO different seats. This is the discriminating leg: if identity
  // came from the credential (or from the caller's `x-seat` header), it could not differ here.
  seen.length = 0;
  await call(fixture('some-other-seat'));
  const env3 = seen[0];
  check('one token, two folders, two DIFFERENT proven seats (identity is measured)',
    !!(env3 && env3.sender && env3.sender.seat === 'some-other-seat'),
    `sender.seat=${env3 && env3.sender && env3.sender.seat}`);
  check('the caller\'s own x-seat claim is ignored',
    !!(env3 && env3.sender && env3.sender.seat !== 'a-seat-i-am-not'));

  await gateway.close();
}

main().then(() => {
  const failed = checks.filter((c) => !c.pass);
  // Completeness asserted, not counted: a run that ended early prints fewer lines and would
  // otherwise read as a clean pass (G-121).
  const EXPECTED = 8;
  if (checks.length !== EXPECTED) {
    out(`FAIL  completeness — ran ${checks.length} of ${EXPECTED} checks`);
    failed.push({ name: `completeness(${checks.length}/${EXPECTED})` });
  }
  out('');
  out(`CHECKS: ${checks.length - checks.filter((c) => !c.pass).length}/${checks.length} passed`);
  if (failed.length) out('FAILED: ' + failed.map((c) => c.name).join(' | '));
  out(`SEAM_OK: ${failed.length === 0}`);
  out(`EXIT: ${failed.length === 0 ? 0 : 1}`);
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = failed.length === 0 ? 0 : 1;
}).catch((err) => {
  out('ERROR:', err.message, err.stack);
  out('EXIT: 1');
  out(`WALL_MS: ${Date.now() - start}`);
  process.exitCode = 1;
}).finally(() => {
  try { fs.unlinkSync(sendersFile); } catch {}
  try { fs.unlinkSync(clientFile); } catch {}
  for (const root of fixtureRoots) { try { fs.rmSync(root, { recursive: true, force: true }); } catch {} }
});
