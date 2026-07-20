#!/usr/bin/env bash
#
# The ttyd render layer (session-surface-spec.md Design 4, OQ-C ruling D83).
#
# Starts ONE ttyd listener on LOOPBACK, gated by a SEPARATE terminal credential, wrapping the
# mediated per-session attach client (attach-client.js). ttyd renders the server-owned pty (c-ii);
# it never spawns a harness (c-i is rejected). The browser is a viewer/keyboard only — every
# keystroke and every screen read is mediated + audited by the daemon.
#
# THREE independent gates protect this surface (defense-in-depth, D83):
#   1. tailnet membership        — enforced by `tailscale serve` at deploy (deploy/network/), not here.
#   2. the terminal credential   — THIS script's `--credential` (a shared USER:PASS on the ttyd
#                                  listener). Reachability-by-tailnet alone must NOT grant JOIN/
#                                  TAKE-OVER, so the credential closes that even before a non-owner
#                                  device is ever enrolled.
#   3. the device/sender token   — the attach client's Bearer token; the daemon's D89 authz gates
#                                  every send-to-session / capture-session-screen on it.
#
# BIND POSTURE (network-posture-spec.md Design 3, HARD gate D81): ttyd binds loopback ONLY.
# `tailscale serve --bg --https=443 http://127.0.0.1:<port>` (deploy/network/) proxies it into the
# tailnet; tailscaled terminates HTTPS. FUNNEL IS NEVER USED. Do not point --interface at a public
# or tailnet address here — the loopback bind is what keeps the surface off every public interface.
#
# Applying `tailscale serve` and restarting the live daemon are CONDUCTOR/OWNER actions at deploy —
# NOT this script's job. This script only stands up the loopback ttyd listener.
set -euo pipefail

: "${IGNITE_GATEWAY_ADDR:?set IGNITE_GATEWAY_ADDR=host:port of the ignite gateway (loopback or tailnet)}"
: "${IGNITE_TERMINAL_TOKEN:?set IGNITE_TERMINAL_TOKEN to an owner-kind ignite sender token}"
: "${IGNITE_TTYD_CRED:?set IGNITE_TTYD_CRED to the terminal credential USER:PASS (defense-in-depth gate, D83)}"

TTYD_PORT="${IGNITE_TTYD_PORT:-7681}"
TTYD_IFACE="${IGNITE_TTYD_IFACE:-127.0.0.1}"   # LOOPBACK ONLY — never a public/tailnet address
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ATTACH="$HERE/attach-client.js"

# Guard the bind class in the script too (belt-and-braces): refuse anything but a loopback interface.
case "$TTYD_IFACE" in
  127.*|::1|localhost) : ;;
  *) echo "REFUSING: ttyd --interface must be loopback (got '$TTYD_IFACE'); Serve proxies the tailnet, ttyd never binds it." >&2; exit 2 ;;
esac

# Preflight (batch-08 item 9 part 4, owner ruling 2026-07-20): name what already holds the port
# before attempting to bind, instead of letting ttyd fail with a bare "address already in use".
# This is diagnostic only — the binding fail-closed identity check that actually gates the tailnet
# publish lives in deploy/network/ttyd-serve.sh's verify_target_listener, which this script does not
# duplicate (Simplicity-first — a bare bind conflict here is caught by ttyd's own exec failure).
_preflight_line="$(ss -H -tlnp "sport = :${TTYD_PORT}" 2>/dev/null | grep LISTEN || true)"
if [[ -n "$_preflight_line" ]]; then
  _preflight_pid="$(grep -oP 'pid=\K[0-9]+' <<<"$_preflight_line" | head -1 || true)"
  if [[ -n "$_preflight_pid" ]]; then
    _preflight_comm="$(cat "/proc/${_preflight_pid}/comm" 2>/dev/null || echo '?')"
    echo "REFUSING to start: 127.0.0.1:${TTYD_PORT} is already held by pid ${_preflight_pid} (${_preflight_comm}) — not this script." >&2
  else
    echo "REFUSING to start: 127.0.0.1:${TTYD_PORT} is already held by a process we cannot identify (permission denied — likely a different user)." >&2
  fi
  exit 3
fi

# --writable enables TAKE-OVER (keyboard in); without it ttyd is view-only (JOIN only).
# --credential is the terminal gate (gate 2 above). --check-origin rejects a cross-origin websocket
# (a malicious page abusing the browser's ambient tailnet reach cannot open the terminal ws).
# --max-clients bounds concurrent terminals. IGNITE_GATEWAY_ADDR + IGNITE_TERMINAL_TOKEN are inherited
# by the wrapped node process via the environment — the token NEVER appears in ttyd's argv or the URL
# (process lists / access logs leak both).
exec ttyd \
  --interface "$TTYD_IFACE" \
  --port "$TTYD_PORT" \
  --credential "$IGNITE_TTYD_CRED" \
  --writable \
  --check-origin \
  --max-clients 4 \
  node "$ATTACH"
