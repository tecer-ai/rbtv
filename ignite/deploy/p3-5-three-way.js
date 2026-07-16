'use strict';

// p3-5-three-way.js — the owner-specified LIVE 3-way write test (D58(5)): each of the three
// production harnesses (claude, codex, opencode), launched through its production profile via the
// REAL spawn path, is asked to create a file (a) in its own session dir -> MUST succeed, (b) in the
// declared test folder -> MUST succeed, (c) at the vault root -> MUST FAIL at the kernel.
//
// SAFETY PRE-FLIGHT (mandatory): the kernel sandbox is the LOAD-BEARING layer (D58; opencode has NO
// native sandbox — POC finding 3, "it touched the live vault unprompted"). Before launching ANY real
// LLM worker, this script PROVES the systemd carrier actually ENFORCES the filesystem sandbox, by
// spawning a benign `systemd-run --user` unit with PrivateTmp and checking /tmp isolation on disk.
// If the sandbox is a NO-OP (as it is under the --user manager on this box — see p3-5-kernel-write.out
// and the p3-5 findings), the script REFUSES to launch real LLM workers — doing so would run them
// UNCONFINED against the live vault, the exact hazard D46/D56/D58 exist to prevent — and records the
// finding instead. It NEVER fabricates a pass and NEVER weakens the profile to force one (task rule).
//
// Writes deploy/p3-5-three-way.out. Exit 0 = ran-and-passed OR safely-skipped-with-finding;
// exit 1 = a launched leg produced a wrong on-disk result.

const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const { execFileSync } = require('node:child_process');

const IGNITE_SRC = path.resolve(__dirname, '..');
const VAULT_ROOT = process.env.RBTV_IGNITE_WORKSPACE_ROOT || path.resolve(IGNITE_SRC, '..', '..', '..', '..');
const OUT_PATH = path.join(__dirname, 'p3-5-three-way.out');
const lines = [];
const log = (s) => lines.push(s);
const now = () => new Date().toISOString();
function portable(p) { if (p == null) return p; const s = String(p); const h = os.homedir(); if (s.startsWith(VAULT_ROOT)) return '{VAULT}' + s.slice(VAULT_ROOT.length); if (h && s.startsWith(h)) return '{HOME}' + s.slice(h.length); return s; }

const HARNESSES = [
  { name: 'claude', bin: 'claude', profile: 'claude-sonnet-tools' },
  { name: 'codex', bin: 'codex', profile: 'codex-git-write' },
  { name: 'opencode', bin: 'opencode', profile: 'opencode-sakana' },
];

function which(bin) { try { return execFileSync('which', [bin], { encoding: 'utf8' }).trim(); } catch { return null; } }

// Prove the carrier ENFORCES filesystem sandboxing before trusting it with a real LLM worker.
function sandboxEnforced() {
  const tag = `__p35_3wpf_${process.pid}`;
  const canary = path.join('/tmp', tag);
  const unit = `p35-3w-preflight-${process.pid}`;
  try {
    execFileSync('systemd-run', [
      '--user', '--unit', unit, '--collect', '--wait',
      '--property', 'PrivateTmp=true',
      '--', 'bash', '-c', `touch /tmp/${tag}; sleep 0.1`,
    ], { encoding: 'utf8', stdio: ['ignore', 'ignore', 'ignore'], timeout: 15000 });
  } catch { /* --wait returns child status; ignore */ }
  const leaked = fs.existsSync(canary);
  try { if (leaked) fs.rmSync(canary); } catch {}
  // Enforced == the canary did NOT leak to the real /tmp.
  return !leaked;
}

async function main() {
  log('p3-5 live 3-way write test (D58(5)) — with mandatory sandbox-enforcement pre-flight');
  log(`started: ${now()}`);
  log('command: node deploy/p3-5-three-way.js');
  log(`vault root: ${portable(VAULT_ROOT)}`);

  log('');
  log('--- harness availability ---');
  const avail = {};
  for (const h of HARNESSES) { const p = which(h.bin); avail[h.name] = p; log(`  ${h.name} (${h.profile}): ${p ? p : 'ABSENT — cannot launch'}`); }

  log('');
  log('--- SAFETY PRE-FLIGHT: does `systemd-run --user` ENFORCE the filesystem sandbox? ---');
  const enforced = sandboxEnforced();
  log(`  PrivateTmp isolation under --user: ${enforced ? 'ENFORCED' : 'NOT ENFORCED (kernel FS sandbox is a NO-OP for --user units)'}`);

  if (!enforced) {
    log('');
    log('  DECISION: SKIP all live LLM launches. The kernel sandbox — the LOAD-BEARING containment');
    log('  layer (D58) — is not enforced under the --user carrier on this box, so a real worker would');
    log('  run UNCONFINED against the live vault (opencode has no native sandbox; POC finding 3). The');
    log('  deterministic kernel-write test (p3-5-kernel-write.out) already proves the kernel behavior');
    log('  for ANY worker — the sandbox is worker-agnostic — so launching paid LLM workers would add');
    log('  no evidence while creating the exact hazard this task exists to prevent.');
    log('');
    log('  FINDING (escalated): worker filesystem containment is NOT enforced by `systemd-run --user`.');
    log('  Confirmed enforced under `systemd-run --system` (root). This re-opens the D46 user-vs-system');
    log('  manager choice and must be ruled BEFORE Batch 4 relies on worker confinement.');
    log('');
    for (const h of HARNESSES) {
      const reason = avail[h.name] ? 'sandbox not enforced under --user (launch unsafe + non-evidential)' : 'binary ABSENT + sandbox not enforced';
      log(`  ${h.name}: SKIPPED — ${reason}`);
    }
    log('');
    log('result: SKIPPED (safe) — see FINDING; no leg launched, nothing fabricated');
    return 0;
  }

  // (Reached only when a future carrier fix makes --user enforce FS sandboxing.) The live launch
  // path is intentionally left as a guarded stub: enabling it is a follow-up once containment is
  // real, and requires per-harness prompt + disk-verification wiring. It must NEVER run while the
  // pre-flight above reports NOT ENFORCED.
  log('');
  log('  Pre-flight ENFORCED — live launches would proceed here. Left as a guarded follow-up stub');
  log('  (the acceptance blocker on this box is the carrier, not the harness prompts).');
  log('result: PENDING — carrier now enforces; wire the live launches in a follow-up round');
  return 0;
}

main()
  .then((code) => { log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(code); })
  .catch((err) => { log(`error: ${err.code || err.name}: ${err.message}`); log('result: FAIL'); log(`ended: ${now()}`); fs.writeFileSync(OUT_PATH, lines.join('\n') + '\n'); process.exit(1); });
