'use strict';

const { DispatchError, E_ENV_VAR_MISSING, E_ENV_LEAK } = require('./errors');

// ═════════════════════════════════════════════════════════════════════════════════════════════
// Boundary 11 — THE SCRUBBED ENVIRONMENT. THIS IS THE SECRETS WALL.
//
// Owner-ruled 2026-07-26, `decisions.md#d-sub-agent-env-allowlist`, CMP-10 boundary 11 verbatim:
// "every CLI-lane spawn is launched with a SCRUBBED environment — ONLY the variables its launch
// profile explicitly names pass through, plus a minimal base (PATH/HOME-class) … a missing
// variable is a VISIBLE failure, never a silent leak."
//
// THE MECHANISM IS CONSTRUCTIVE, NOT SUBTRACTIVE, and the difference is the whole wall. A denylist
// over the dispatcher's environment is a losing game — it protects against the names someone
// thought of. This builds the child's environment from an EMPTY OBJECT and adds only what is
// named. A variable nobody anticipated is absent by construction rather than by foresight.
//
// ⚠⚠ MEASURED FINDING, REPORTED RATHER THAN QUIETLY SUPPLIED (task 7.43's row instructs exactly
// this for boundary 10's twin, and the same discipline applies here): THE PROFILE'S DECLARING HOME
// FOR AN ENV ALLOWLIST DOES NOT EXIST TODAY. `ignite/launch-profiles/profiles.js` closes the
// profile `env` block to a single key — `KNOWN_ENV_KEYS = new Set(['file'])`, an EnvironmentFile
// path consumed by the daemon's systemd carrier (`server/spawn/carrier.js:158`) — and any other
// key is a loud `E_CONFIG_LOAD` at config load. So a profile CANNOT name a variable today, and
// `declaredEnvNames()` below is always empty on the committed schema. The consequence is
// fail-closed and therefore safe (the allowlist is the minimal base and nothing else), but the
// ruled declaration point is missing and 7.42's module is READ-ONLY to this task — so this is a
// finding routed to the leader, not an edit made here.
//
// PATH IS FIXED, NOT INHERITED, and that carries boundary 3 (no coordination access) as well as
// this one. The dispatcher's own PATH leads with `~/.local/bin`, where `coordinate` — the
// coordination bus CLI — lives. Inheriting it would put the bus one word away from a sub-agent
// that is forbidden to touch it. The harness binary is therefore resolved to an ABSOLUTE path by
// the dispatcher (see dispatch.js) and the child's PATH is a system base that contains no bus CLI.
// ═════════════════════════════════════════════════════════════════════════════════════════════

// The minimal base, PATH/HOME-class, and nothing beyond it. Each name is here for a stated reason;
// a name with no reason does not belong in a secrets wall.
//   PATH     — fixed value below, never the dispatcher's
//   HOME     — the harness reads its own credentials and config from it; without it no harness runs
//   USER     — POSIX identity; several CLIs read it for cache/temp paths
//   LOGNAME  — same, the older spelling; both are cheap and neither carries a secret
//   LANG     — text decoding; its absence produces mojibake, not a wall
//   TZ       — timestamps in the sub-agent's own output
const BASE_PASSTHROUGH = Object.freeze(['HOME', 'USER', 'LOGNAME', 'LANG', 'TZ']);

// A system PATH with no user bin dir. `coordinate`, `sd-graph`, `sb-task` and every other
// workspace CLI live under ~/.local/bin and are unreachable BY NAME from here.
const MINIMAL_PATH = '/usr/local/bin:/usr/bin:/bin';

// The nesting marker (boundary 9). It is the ONE variable this capability adds rather than
// forwards, and it is deliberately inside the allowlist rather than smuggled past it.
const DEPTH_VAR = 'RBTV_SUBAGENT_DEPTH';

// A second belt over the composed result. It cannot replace the constructive allowlist and is not
// asked to: it exists so that if a future edit ever widens the base, the widening fails HERE
// rather than in a spawned process holding the dispatcher's secrets. It can fire — adding
// `ANTHROPIC_API_KEY` or `TMUX` to BASE_PASSTHROUGH turns this red immediately.
const FORBIDDEN_NAME_RE = /(TMUX|COORD|GATEWAY|TOKEN|SECRET|PASSWORD|CREDENTIAL|_KEY$|^ANTHROPIC|^OPENAI|^AWS_|^RBTV_IGNITE)/i;

// What the profile declares. See the finding above: on the committed 7.42 schema this is ALWAYS
// empty, because the profile `env` block admits only `file`. Written to read the key the ruling
// names (`env.allow`) so that the day 7.42's schema carries it, this lane honours it with no edit
// — and written to return [] rather than to guess, because absence of a declaration must never
// become absence of a check.
function declaredEnvNames(resolvedProfile) {
  const env = resolvedProfile && resolvedProfile.env;
  if (!env || !Array.isArray(env.allow)) return [];
  return env.allow.filter((n) => typeof n === 'string' && n.length > 0);
}

// Builds the child's environment from an EMPTY object.
function buildChildEnv({ resolvedProfile, dispatcherEnv = process.env, extra = {} } = {}) {
  const declared = declaredEnvNames(resolvedProfile);
  const out = Object.create(null);

  out.PATH = MINIMAL_PATH;

  for (const name of BASE_PASSTHROUGH) {
    if (dispatcherEnv[name] !== undefined) out[name] = dispatcherEnv[name];
  }

  for (const name of declared) {
    if (dispatcherEnv[name] === undefined) {
      // CMP-10: "a missing variable is a VISIBLE failure, never a silent leak". A profile that
      // names a variable its target needs, on a box where it is unset, refuses the launch — it
      // does not run the target half-configured and let it fail somewhere downstream.
      throw new DispatchError(
        E_ENV_VAR_MISSING,
        `profile '${resolvedProfile.name}' declares environment variable ${name} but it is unset ` +
        `in the dispatcher's environment — REFUSING the launch (CMP-10 boundary 11: a missing ` +
        `variable is a visible failure, never a silent leak)`,
        { profile: resolvedProfile.name, variable: name },
      );
    }
    out[name] = dispatcherEnv[name];
  }

  for (const [name, value] of Object.entries(extra)) out[name] = String(value);

  // ── post-condition, ASSERTED rather than assumed ────────────────────────────────────────────
  const allowed = new Set(['PATH', ...BASE_PASSTHROUGH, ...declared, ...Object.keys(extra)]);
  for (const name of Object.keys(out)) {
    if (!allowed.has(name)) {
      throw new DispatchError(
        E_ENV_LEAK,
        `composed child environment carries ${name}, which is outside the allowlist — refusing to spawn`,
        { variable: name, allowed: [...allowed] },
      );
    }
    if (FORBIDDEN_NAME_RE.test(name) && name !== DEPTH_VAR) {
      throw new DispatchError(
        E_ENV_LEAK,
        `composed child environment carries ${name}, which matches the coordination/credential ` +
        `name guard — refusing to spawn`,
        { variable: name },
      );
    }
  }

  return { env: out, declared, base: [...BASE_PASSTHROUGH] };
}

module.exports = {
  BASE_PASSTHROUGH,
  MINIMAL_PATH,
  DEPTH_VAR,
  FORBIDDEN_NAME_RE,
  declaredEnvNames,
  buildChildEnv,
};
