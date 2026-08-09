'use strict';

// engine/substrate.js — THE SEAM. One host detection, and a NAMED branch point at every site the
// Windows-degraded attached lane must traverse.
//
// Owner ruling decisions.md#d-windows-degraded-attached-lane: the attached-execution engine "carries two
// code paths, POSIX and Windows-degraded". Leader ruling 2026-07-28
// (`runs/run-2/seats/leader/ruling-744-forks.md`) SPLIT that build: task 7.44 owns THE SEAMS —
// this file — and **task 7.84 owns the degraded BRANCH BODIES** (Windows job-object tree-kill, the
// ABSENT filesystem walls, the absent tmux room). The split's stated reason is the reason this
// file refuses instead of falling through: a green obtained where the degradation cannot fire is
// not evidence, and this box is CAGED — it can prove a seam EXISTS and can prove nothing about how
// a degraded body behaves.
//
// ⚠ WHAT THIS FILE EXISTS TO PREVENT, measured at HEAD 4276b51 before it was written:
//
//     grep -rn "process.platform" server/ launch-profiles/   →   ZERO matches
//
// The engine had NO host branch anywhere. So on a cage-less host `selectCarrier('auto')` execs
// `systemctl`, finds nothing, and resolves `setsid` — a POSIX carrier — with no branch point ever
// consulted. Worse, `carrier.js` `killSetsid()` signals the process GROUP (`process.kill(-pid, …)`)
// inside `try {} catch {}`, and its liveness re-check `process.kill(-pid, 0)` reads a throw as
// "the process is gone". A negative pid is not a Windows process group, so both calls throw, both
// are swallowed, and the function resolves `{ killed: true }` HAVING KILLED NOTHING.
//
// ⚠⚠ THAT LAST PARAGRAPH IS A CODE READING, NOT A WINDOWS MEASUREMENT, and it is written that way
// deliberately. Nothing here has been run on Windows and nothing here claims to have been. It is
// stated because it is the failure this seam is shaped against: a SILENT false green. The remedy
// is therefore a REFUSAL, never a fallback — an unbuilt branch that quietly does the POSIX thing
// is indistinguishable from a built one until something does not die.

const E_SUBSTRATE_UNSUPPORTED = 'E_SUBSTRATE_UNSUPPORTED';

// The four sites, named. This list is the seam's inventory: it is what the 7.44 row means by
// "every such site carries an explicit NAMED branch point", and it is what task 7.84 builds
// bodies for. Adding a POSIX construct to the lane without adding its row here is the defect.
const DEGRADED_BRANCHES = Object.freeze([
  Object.freeze({
    site: 'carrier',
    posix: 'systemd-run --user (or setsid), selected by server/spawn/carrier.js selectCarrier()',
    windows: 'a Windows JOB OBJECT holding the worker tree',
    owner: 'task 7.84 · CMP-17 § Carve-out',
  }),
  Object.freeze({
    site: 'tree-kill',
    posix: 'process.kill(-pid, …) — signalling the POSIX process GROUP (carrier.js killSetsid)',
    windows: 'terminating the job object (approximates the tree-kill; NO kernel-enforced per-profile caps)',
    owner: 'task 7.84 · CMP-17 § Carve-out',
  }),
  Object.freeze({
    site: 'filesystem-wall',
    posix: 'bwrap bind-mount cage (server/spawn/bwrap.js, server/spawn/cage.js)',
    windows: 'NONE — the ruling\'s own "load-bearing degradation": an attached worker runs with the caller\'s full filesystem reach',
    owner: 'task 7.84 · DEC-1 § Windows-degraded attached lane',
  }),
  Object.freeze({
    site: 'seat-room',
    posix: 'a tmux room + one pane per seat (server/spawn/tmux.js)',
    windows: 'NONE — no tmux room and no pane',
    owner: 'task 7.84 · DEC-1 § Windows-degraded attached lane',
  }),
]);

class SubstrateError extends Error {
  constructor(code, message, detail = {}) {
    super(message);
    this.name = 'SubstrateError';
    this.code = code;
    this.detail = detail;
  }
}

// `RBTV_IGNITE_SUBSTRATE` is what makes this seam TESTABLE WITHOUT WINDOWS — which is the reason
// the seam half is in 7.44's scope at all. It is a PROBE KNOB and never a portability switch:
// forcing `windows` on this box does not give you a Windows lane, it gives you the refusal, which
// is exactly the thing under test. Forcing `posix` on a real Windows host would defeat the whole
// file, so the override is validated against the known set rather than trusted.
function detectSubstrate(env = process.env, platform = process.platform) {
  const override = env.RBTV_IGNITE_SUBSTRATE;
  if (override) {
    if (override !== 'posix' && override !== 'windows') {
      throw new SubstrateError(
        E_SUBSTRATE_UNSUPPORTED,
        `RBTV_IGNITE_SUBSTRATE=${override} is not a substrate this engine knows; expected 'posix' or 'windows'`,
        { override },
      );
    }
    return override;
  }
  return platform === 'win32' ? 'windows' : 'posix';
}

function describeDegradation() {
  return DEGRADED_BRANCHES.map(
    (b) => `  · ${b.site}: POSIX uses ${b.posix}; the degraded branch would be ${b.windows} — ${b.owner}`,
  ).join('\n');
}

// THE BRANCH POINT. Every lane that composes this engine calls it BEFORE any POSIX construct is
// reached, so a non-POSIX host is refused rather than silently carried down the POSIX path.
//
// It answers the ruling's requirement in the only way this box can honestly discharge: the branch
// EXISTS, it is explicit, it names its four sites and the row that owns their bodies. It does not
// pretend a Windows lane runs.
function assertSubstrateSupported(env = process.env, platform = process.platform) {
  const resolved = detectSubstrate(env, platform);
  if (resolved === 'posix') return resolved;

  throw new SubstrateError(
    E_SUBSTRATE_UNSUPPORTED,
    `the attached-execution engine has no ${resolved} branch bodies yet, and REFUSES rather than running ` +
    `the POSIX ones on a host that cannot honour them.\n` +
    `This is a DELIBERATE DEFERRAL, not an oversight: owner ruling ` +
    `decisions.md#d-windows-degraded-attached-lane rules Windows a supported, DEGRADED substrate; ` +
    `core-build task 7.44 built these seams and core-build TASK 7.84 carries the branch bodies.\n` +
    `The ${DEGRADED_BRANCHES.length} sites this lane would traverse:\n${describeDegradation()}\n` +
    `Until 7.84 lands, the attached lane runs on a POSIX host. There is no override flag: falling ` +
    `through would signal a POSIX process group that does not exist on this host and report the ` +
    `kill as successful.`,
    { substrate: resolved, sites: DEGRADED_BRANCHES.map((b) => b.site) },
  );
}

module.exports = {
  E_SUBSTRATE_UNSUPPORTED,
  SubstrateError,
  DEGRADED_BRANCHES,
  detectSubstrate,
  assertSubstrateSupported,
  describeDegradation,
};
