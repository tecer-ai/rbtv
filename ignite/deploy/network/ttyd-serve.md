# ttyd render layer — Tailscale Serve publication (tailnet-only, never Funnel)

Wired at task p6-3 under `specs/session-surface-spec.md` (Design 4, OQ-C ruling D83) +
`specs/network-posture-spec.md` (Design 3; HARD gate D81). The runnable artifact is
`ttyd-serve.sh` in this folder — **a conductor/owner action at deploy, never a build-worker action.**

## The two layers

| Layer | Binds | Published by | Gate |
|-------|-------|--------------|------|
| ttyd render listener (`server/pty/ttyd/serve-ttyd.sh`) | `127.0.0.1:<ttyd_port>` (LOOPBACK only) | — | the terminal credential (ttyd `--credential USER:PASS`) |
| Tailscale Serve (`ttyd-serve.sh`) | tailnet, HTTPS:443 (tailscaled terminates TLS) | `tailscale serve --bg --https=443 http://127.0.0.1:<ttyd_port>` | tailnet membership |

The daemon's JSON API is **not** served through Serve — it is reached directly over the tailnet
(plaintext HTTP, WireGuard-encrypted). Serve publishes the **web/live surface** only
(`spawn-profiles-spec.md:224`; network-posture Design 3).

## Defense-in-depth — THREE independent gates

A browser reaching JOIN/TAKE-OVER must pass all three (D83):

1. **tailnet membership** — enforced by Serve; an off-tailnet host cannot reach the node at all
   (no public listener, no Funnel, Hetzner firewall drops it).
2. **the terminal credential** — the ttyd `--credential` gate. Tailnet reachability ALONE must not
   grant JOIN/TAKE-OVER, so this closes the surface even before a non-owner device is ever enrolled.
3. **the device/sender token** — the attach client's Bearer token; the daemon's D89 authz
   (`kind: owner` OR `enqueued_by == authenticated sender-id`) gates every keystroke and screen read.

## HARD gates (build defects if violated)

- **Loopback upstream only.** Serve proxies `http://127.0.0.1:<ttyd_port>`; ttyd binds loopback and
  nothing else. A public/tailnet ttyd bind is a build defect.
- **Funnel is NEVER used.** `tailscale funnel` would expose the surface to the public internet —
  forbidden by DEC-3. `ttyd-serve.sh` uses `tailscale serve` only; there is no Funnel path.
- **No public listener.** After apply, `tailscale funnel status` shows no funnel and `ss -tlnp`
  shows ttyd on `127.0.0.1:<ttyd_port>` only — the conductor re-proves `probe-no-public-listener`.

## Preconditions (owner/conductor, out of band)

- **ttyd installed** (D87/PA — ttyd 1.7.7 at `/usr/bin/ttyd`, met).
- **Tailnet HTTPS certificates enabled** for `tailf44c73.ts.net` (D87/PC — `CertDomains:
  ['ignite-alfa.tailf44c73.ts.net']`, met). Serve's `--https` cannot issue a cert without it.
- **A second enrolled tailnet device** for the live JOIN/TAKE-OVER grade (PD — met; graded at
  p6-checkpoint, not by the build worker).

## Deploy order (conductor)

1. Restart the live daemon onto the committed pty code (owner action — separate from Serve).
2. Start the ttyd render listener: `IGNITE_GATEWAY_ADDR=… IGNITE_TERMINAL_TOKEN=… IGNITE_TTYD_CRED=user:pass server/pty/ttyd/serve-ttyd.sh`.
3. Apply Serve: `IGNITE_TTYD_PORT=<port> deploy/network/ttyd-serve.sh`.
4. Re-prove `probe-no-public-listener` (funnel status + `ss -tlnp`), then grade criterion 4 from an
   enrolled device (credential-refused without, JOIN+TAKE-OVER with, plus the live takeover screenshot).
