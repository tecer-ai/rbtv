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

## Deploy-time port precondition (batch-08 item 9 part 4, owner ruling 2026-07-20)

**⚑ MANDATORY, enforced in code — not a manual checklist item.** Before `ttyd-serve.sh` applies
`tailscale serve`, it runs `verify_target_listener` against `127.0.0.1:<ttyd_port>` and refuses to
publish, loudly, on anything short of a positive match. This exists because the target port can be
occupied by a listener that is NOT ignite's ttyd — the concrete incident: a root-owned, distro-packaged
`ttyd.service` held port 7681 for three days, serving a writable system `login` shell with no
credential. Publishing that instead of the daemon-mediated attach client would have collapsed the
surface's three independent gates (tailnet membership · terminal credential · device token) down to
one, and exposed a raw root login prompt.

**What the check verifies** ("ignite's own ttyd", not merely "something" or "nothing" on the port):

1. the process bound to the port has `/proc/<pid>/comm` exactly `ttyd`;
2. it does **not** run as root (ignite's ttyd always runs as the ignite service user; the incident
   listener was root-owned — this alone would have caught it);
3. its `/proc/<pid>/cmdline` wraps this checkout's exact `server/pty/ttyd/attach-client.js` path —
   the argv shape only `serve-ttyd.sh` produces.

**Fail-closed on every non-match, including the inconclusive ones:** nothing listening, or a listener
whose owning process we cannot read (typically a different-UID process — the kernel hides
`/proc/<pid>/{comm,cmdline}` across UIDs, which is itself how a root-owned foreign listener gets
caught even before check 2 runs), all refuse exactly like a positively-wrong listener. None of those
states establishes "this is ignite's own ttyd", which is the only thing that licenses a publish.

**Keys off the configured port**, not a hardcoded `7681` — reads `IGNITE_TTYD_PORT` (default `7681`)
the same way `serve-ttyd.sh` does, so a future port move cannot silently bypass the guard.

**Scope — a precondition check, not an authentication system:** it verifies process identity as seen
from `/proc`, not a cryptographic identity. A process with root on the box (or the ability to run as
the ignite service user) could construct a matching `comm` + non-root uid + argv wrapping the real
`attach-client.js` and pass the check while not actually being ignite's supervised ttyd. This does not
weaken the deploy surface's real security boundary — the terminal credential (gate 2) and the device
token (gate 3) still gate JOIN/TAKE-OVER regardless of what this check does. It only narrows the
publish-time failure mode described above; it is deliberately not built heavier than that.

`server/pty/ttyd/serve-ttyd.sh` also refuses to *start* if something already holds the target port,
naming the pid/process it found (or reporting it as unidentifiable) — a diagnostic preflight, not a
duplicate of the identity check above.

## Deploy order (conductor)

1. Restart the live daemon onto the committed pty code (owner action — separate from Serve).
2. Start the ttyd render listener: `IGNITE_GATEWAY_ADDR=… IGNITE_TERMINAL_TOKEN=… IGNITE_TTYD_CRED=user:pass server/pty/ttyd/serve-ttyd.sh`.
3. Apply Serve: `IGNITE_TTYD_PORT=<port> deploy/network/ttyd-serve.sh`.
4. Re-prove `probe-no-public-listener` (funnel status + `ss -tlnp`), then grade criterion 4 from an
   enrolled device (credential-refused without, JOIN+TAKE-OVER with, plus the live takeover screenshot).
