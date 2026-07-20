#!/usr/bin/env bash
#
# Tailscale Serve wiring for the ttyd render layer (network-posture-spec.md Design 3; HARD gate D81).
#
# ⚑ CONDUCTOR/OWNER ACTION AT DEPLOY — a dispatched build worker NEVER runs this (ADX-32). It is
# delivered as a config artifact; the conductor applies it after the daemon restart, then re-proves
# `probe-no-public-listener`. Running `tailscale serve` is owner/conductor-gated.
#
# WHAT IT DOES: publishes the LOOPBACK ttyd listener (server/pty/ttyd/serve-ttyd.sh) into the
# tailnet over HTTPS, tailnet-only. tailscaled terminates HTTPS on the node's MagicDNS cert
# (D87: CertDomains ['ignite-alfa.tailf44c73.ts.net']). The daemon's JSON API is NOT served here —
# it is reached directly over the tailnet (plaintext, WireGuard-encrypted); Serve is for web surfaces.
#
# ⚑ FUNNEL IS NEVER USED. `tailscale funnel` would expose this to the PUBLIC internet — the exact
# thing DEC-3 forbids. This script uses `tailscale serve` (tailnet-only) ONLY. There is no Funnel
# path here and there must never be one.
#
# ⚑ DEPLOY-TIME PORT PRECONDITION (batch-08 item 9 part 4, owner ruling 2026-07-20): a foreign
# listener can occupy the target port (the concrete case: a root-owned system service holding it).
# Publishing THAT to the tailnet instead of ignite's mediated attach client collapses the surface's
# three independent gates (tailnet membership · terminal credential · device token) down to one.
# `verify_target_listener` below MUST run and PASS before `tailscale serve` is ever invoked.
# Fail-closed: an empty port or an unidentifiable listener refuses exactly like a wrong one — none of
# those states positively confirm "this is ignite's own ttyd", which is the only thing that licenses
# a publish.
set -euo pipefail

TTYD_PORT="${IGNITE_TTYD_PORT:-7681}"   # must match serve-ttyd.sh's loopback listener port

# HARD GATE: proxy ONLY 127.0.0.1 (loopback). The upstream MUST be loopback so ttyd never binds a
# public/tailnet interface itself — Serve is the only path into the tailnet.
UPSTREAM="http://127.0.0.1:${TTYD_PORT}"

# verify_target_listener PORT
#
# Refuses (exit 1, message on stderr) unless the process bound to 127.0.0.1:PORT is positively
# identifiable as ignite's own ttyd. "Positively identifiable" here means all three:
#   1. its /proc/<pid>/comm is exactly "ttyd" (not just "something on the port")
#   2. it is NOT owned by root (ignite's ttyd always runs as the ignite service user; the concrete
#      incident this guards against was root-owned)
#   3. its /proc/<pid>/cmdline wraps the exact attach-client.js this checkout ships (the argv shape
#      only serve-ttyd.sh produces — a bare ttyd, even one started by the same user, does not match)
#
# Any state that does not clear all three — nothing listening, a listener whose process is not
# visible to us (e.g. root-owned and we are not root: the kernel hides /proc/<pid>/{comm,cmdline}
# cross-UID), or a listener that fails any single check — is treated as UNCONFIRMED and refused.
# This is deliberately a precondition check, not an authentication system: see the guard's
# spoofability discussion in the item's dispatch return.
verify_target_listener() {
  local port="$1"
  local attach_js
  attach_js="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../server/pty/ttyd" && pwd)/attach-client.js"

  local ss_line
  ss_line="$(ss -H -tlnp "sport = :${port}" 2>/dev/null | grep LISTEN || true)"

  if [[ -z "$ss_line" ]]; then
    echo "REFUSING to publish: nothing is listening on 127.0.0.1:${port}." >&2
    echo "Expected ignite's own ttyd (wrapping ${attach_js})." >&2
    echo "Start server/pty/ttyd/serve-ttyd.sh first, then re-run this script." >&2
    return 1
  fi

  local pid
  pid="$(grep -oP 'pid=\K[0-9]+' <<<"$ss_line" | head -1 || true)"

  if [[ -z "$pid" ]]; then
    echo "REFUSING to publish: something is listening on 127.0.0.1:${port}, but its process is not" >&2
    echo "visible to this check (permission denied reading its socket owner — typically means it" >&2
    echo "belongs to a different user, e.g. root). ignite's own ttyd always runs as the ignite" >&2
    echo "service user, never root. Cannot confirm identity -> fail closed." >&2
    echo "raw: $ss_line" >&2
    return 1
  fi

  if [[ ! -r "/proc/${pid}/cmdline" ]]; then
    echo "REFUSING to publish: pid ${pid} is listening on 127.0.0.1:${port} but /proc/${pid}/cmdline" >&2
    echo "is unreadable. Cannot confirm identity -> fail closed." >&2
    return 1
  fi

  local comm owner_uid cmdline
  comm="$(cat "/proc/${pid}/comm" 2>/dev/null || echo "?")"
  owner_uid="$(stat -c '%u' "/proc/${pid}" 2>/dev/null || echo "?")"
  cmdline="$(tr '\0' '\n' < "/proc/${pid}/cmdline" 2>/dev/null || true)"

  local reasons=()
  [[ "$comm" == "ttyd" ]] || reasons+=("process name is '${comm}', expected 'ttyd'")
  [[ "$owner_uid" != "0" ]] || reasons+=("process runs as root (uid 0) — ignite's ttyd never runs as root")
  grep -qxF "$attach_js" <<<"$cmdline" || reasons+=("argv does not wrap ${attach_js}")

  if (( ${#reasons[@]} > 0 )); then
    echo "REFUSING to publish: pid ${pid} on 127.0.0.1:${port} is NOT ignite's own ttyd." >&2
    printf '  - %s\n' "${reasons[@]}" >&2
    echo "  found: comm=${comm} uid=${owner_uid} argv=$(tr '\n' ' ' <<<"$cmdline")" >&2
    return 1
  fi

  echo "Verified: pid ${pid} on 127.0.0.1:${port} is ignite's own ttyd (comm=ttyd, uid=${owner_uid}, wraps ${attach_js})."
  return 0
}

apply_serve() {
  echo "Applying Tailscale Serve (tailnet-only, HTTPS:443 -> ${UPSTREAM}); Funnel is NOT used."
  # --bg        : run in the background (persist the serve config)
  # --https=443 : tailscaled terminates HTTPS on 443 for this node (needs tailnet HTTPS certs — D87/PC)
  tailscale serve --bg --https=443 "${UPSTREAM}"

  echo
  echo "Serve config now:"
  tailscale serve status

  echo
  echo "POST-APPLY GATES (the conductor re-proves these at deploy):"
  echo "  1. tailscale funnel status   -> MUST show NO funnel config (tailnet-only, never public)."
  echo "  2. ss -tlnp                   -> ttyd on 127.0.0.1:${TTYD_PORT} ONLY; no public listener but 22."
  echo "  3. Open https://<node>.<tailnet>.ts.net/ from an enrolled device -> terminal-credential prompt,"
  echo "     then the ignite session picker. An off-tailnet host cannot reach it at all."
}

main() {
  verify_target_listener "${TTYD_PORT}" || exit 1
  apply_serve
}

# Sourceable for the guard probe (probe-ttyd-port-guard.sh calls verify_target_listener directly
# without ever reaching apply_serve / tailscale serve). Direct execution still runs the full flow.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main
fi
