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
set -euo pipefail

TTYD_PORT="${IGNITE_TTYD_PORT:-7681}"   # must match serve-ttyd.sh's loopback listener port

# HARD GATE: proxy ONLY 127.0.0.1 (loopback). The upstream MUST be loopback so ttyd never binds a
# public/tailnet interface itself — Serve is the only path into the tailnet.
UPSTREAM="http://127.0.0.1:${TTYD_PORT}"

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
