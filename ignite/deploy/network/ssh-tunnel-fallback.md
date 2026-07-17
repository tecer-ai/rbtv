# SSH-tunnel fallback — the universal path when the tailnet is unavailable

Wired at task p5-2 under `specs/network-posture-spec.md` (Design 1; Behavior row 8; Test Plan criterion 10). Realizes **DEC-3**: the SSH tunnel is the **universal fallback** — the path that works when the tailnet does not.

## Why it exists

The daemon binds `127.0.0.1:<port>` **unconditionally and first**, before any tailnet bind, and keeps it bound even when tailscaled is down (network-posture-spec Design 1, "Why loopback MUST stay bound"). The loopback listener is therefore always present, so an SSH local-forward to the VPS's loopback always reaches the gateway — including during a tailnet outage, exactly when the fallback is needed.

The daemon **never** opens a public port for the fallback. SSH is the only fallback; a tailnet loss never widens the bind (Design 2, rule 5).

## The command

From the operator's own machine (already key-authorized on the VPS — an out-of-band one-time step per the module `CLAUDE.md` § Installation model):

```
ssh -L <port>:127.0.0.1:<port> <ssh_user>@<vps-host>
```

Then, in a second shell on the operator's machine, point the CLI at the local end of the tunnel:

```
IGNITE_GATEWAY_ADDR=127.0.0.1:<port> ignite inspect queue
```

The request rides the SSH tunnel to the VPS's loopback gateway, authenticates by sender token (the token is required on every path — the tunnel is not trust either), and is served by the same gateway/server chain proven at p4-checkpoint.

## Where the fields come from — the endpoint record (D27)

The values are NOT memorized; they live in the committed endpoint record `.rbtv/modules/ignite/server.json`, populated at runtime by the daemon (tailnet fields) and by the owner at install (SSH fields):

| Field | Source | Used for |
|-------|--------|----------|
| `gateway_port` | daemon (runtime) | both `<port>` occurrences above |
| `ssh_host` | owner (install) | `<vps-host>` |
| `ssh_user` | owner (install) | `<ssh_user>` |
| `ssh_port` | owner (install) | pass as `ssh -p <ssh_port>` if the VPS SSH is not on 22 |
| `tailnet_host` / `tailnet_ip` | daemon (runtime) | the PREFERRED path — use this directly when the tailnet is up; the tunnel is only the fallback |

The CLI's `resolveGatewayAddr()` already derives the tunnel command from these fields and prints it when no tailnet address is on record; the CLI deliberately does NOT open the tunnel itself — opening it is an operator action.

## Preconditions (owner-executed, out of band)

- The operator's public key is authorized on the VPS for `<ssh_user>` (one-time). Private keys never live in the repo (D27).
- The Hetzner cloud firewall already allows inbound TCP 22 (the only sanctioned public ingress) + ICMP; no daemon port is ever opened publicly.
