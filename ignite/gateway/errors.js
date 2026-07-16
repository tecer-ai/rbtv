'use strict';

// Sender-facing typed errors. EVERY refusal — auth, shape, server re-validation,
// not-found — reaches the sender as a typed code + message in the envelope, and
// the CLI maps the class onto its exit code (gateway-cli-spec.md § Exit codes):
//
//   0 success · 2 local usage/parse · 3 refused by gateway auth
//   4 validation refused (gateway shape-check OR server re-validation)
//   5 gateway unreachable/transport · 1 anything else
//
// Exit 4 covers BOTH validation layers on purpose, and the payload's typed error
// is what distinguishes which one refused: SHAPE_INVALID is the gateway's own
// deterministic shape-check; VALIDATION_FAILED comes back from the server core's
// semantic re-validation.

class GatewayError extends Error {
  constructor(code, message, details = null) {
    super(message);
    this.name = 'GatewayError';
    this.code = code;
    this.details = details;
  }
}

// Uniform refusal for a missing, malformed, unmatched, or disabled sender token.
// ⚑ Carries NO detail, by design (spawn-profiles-spec.md Design 4): no token echo,
// no "which field failed", no distinction between "unknown sender" and "disabled
// sender" — the refusal must not become an oracle. Even from localhost: localhost
// is not trust (DEC-3).
const AUTH_REFUSED = 'AUTH_REFUSED';

// The gateway's half of the dry-run: known intent, required fields present,
// well-formed trigger, well-formed args. Deterministic shape only — the gateway
// holds no server config, so it can never check "does this profile exist"; that
// is the server core's semantic re-validation (defense-in-depth).
const SHAPE_INVALID = 'SHAPE_INVALID';

// The sender named a subcommand/intent the gateway does not route.
const UNKNOWN_INTENT = 'UNKNOWN_INTENT';

module.exports = { GatewayError, AUTH_REFUSED, SHAPE_INVALID, UNKNOWN_INTENT };
