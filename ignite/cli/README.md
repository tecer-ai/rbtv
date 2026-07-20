# `ignite` — the client CLI

The `ignite` CLI is the client for the gateway module (`../gateway/`) — DEC-1
R1's CLI-first client surface, one subcommand per action, each a **thin
wrapper** over the gateway's HTTP API. It is the client for BOTH the owner and
agents (`gateway-cli-spec.md` behavior row 7). It never opens the store,
never spawns anything, and never sends raw SQL — every operation goes through
the gateway, which forwards to the server core's internal-only API
(`internal-api-contract-spec.md`).

Binding contract: `1-projects/rbtv-sb-merge-refactor-core-build/build/phase-7-plan/specs/gateway-cli-spec.md`.

## Install

There is no build step and no npm dependency (`ignite/dependencies.txt` — this
CLI adds none; it uses only Node.js built-ins). Run it directly:

```bash
node /path/to/ignite/cli/ignite.js <command> ...
```

Or symlink it onto `PATH` for a bare `ignite` command:

```bash
ln -s /path/to/ignite/cli/ignite.js ~/.local/bin/ignite
chmod +x ~/.local/bin/ignite   # cli/ignite.js already carries the shebang + exec bit
```

## Auth / config

| Source | Purpose |
|--------|---------|
| `IGNITE_GATEWAY_ADDR` env var | Explicit gateway address override (`host:port` or a full URL). Always wins when set. |
| `.rbtv/modules/ignite/server.json` | The workspace's committed endpoint record (D27 install model), a **machine-keyed map**: each machine's install lives under `machines[<hostname>]` (endpoint fields + that machine's `state_root`). Used when `IGNITE_GATEWAY_ADDR` is unset: this machine's own entry wins when it records a server, else the one entry that does; tailnet address preferred; the SSH-tunnel fallback is printed as a command to run yourself (this CLI never opens a tunnel). The legacy flat shape is still accepted. |
| `IGNITE_SENDER_TOKEN` env var | The sender's auth token. **Never** passed as a flag — argv and process lists leak flags; env does not. |

Run `ignite --help` (or `ignite <command> --help`) for the exact flags of each
subcommand.

## Commands

| Command | Wraps | Notes |
|---------|-------|-------|
| `ignite add-job` | `enqueue-job` | Enqueues a job (server-side dry-run-validated before writing). `--dry-run` is refused (see § Known gap below). |
| `ignite remove-job <queue-id>` | `remove-job` | Removes a pending queue row; removing a repeating row cancels the WHOLE schedule (D68) and the CLI says so. |
| `ignite inspect jobs\|queue\|status <id>\|logs <id> [--tail n]\|daemon\|ticker\|messages <id>` | `inspect` | Read-only. `--tail` walks the offset/limit pages client-side (the contract has no reverse read) and keeps only the last N lines. `messages <id>` (cli-expansion D3): `<id>` is an execution id; the server resolves the execution's chain-stable thread and returns that thread's message rows, paged. |
| `ignite snooze <kind> <subject> --minutes <n>` | `snooze` | OWNER-ONLY. No standing warning is a clean no-op, never an error. There is no dismiss/clear subcommand — snooze never clears a warning (D45). |
| `ignite status` | `inspect` (`target: daemon`) | Alias for `ignite inspect daemon`. On transport failure (daemon unreachable) prints `daemon: DOWN` instead of a raw connect error. |
| `ignite send <session-id> --data <string>` | `send-to-session` | Keystroke bytes into a live HEADED session's pty (D92/D93 — audited server-side before delivery). `<session-id>` is the integer execution id. Headless id → typed refusal, never a hang. The 4096-byte max is server-enforced only (never re-checked locally). |
| `ignite screen <session-id>` | `capture-session-screen` | A live HEADED session's current rendered screen — a detached snapshot with dimensions, never a stream; every read audited server-side first (D94). `repainting: true` means the re-attached pty has not painted yet — capture again. |
| `ignite kill <session-id>` | `kill-session` | TERM → grace → KILL of the whole process tree; status becomes `killed`. Any session mode (headless or headed). Unknown id → typed not-found; an already-terminal session (`done`/`failed`/`killed`) → typed refusal. |

## `--json` policy

Every subcommand accepts a global `--json` flag. With it, stdout is EXACTLY
the gateway's own envelope, unmodified — `{ "ok": true, "result": ... }` or
`{ "ok": false, "error": { "code", "message", "details"? } }` — one line,
`jq`-parseable. Local (never-reached-the-gateway) failures — a bad flag, an
unreachable gateway — get the SAME envelope shape with a CLI-local error code
(`CLI_USAGE_ERROR`, `CLI_TRANSPORT_ERROR`, `CLI_INTERNAL_ERROR`) so a caller
scripting on `--json` never has to special-case "local vs. gateway" failures
in its parsing, only in the `error.code` value.

Without `--json`, each command renders a short human-readable summary on
success and `ERROR [<code>] <message>` on failure.

### Exit codes (`gateway-cli-spec.md` § Exit codes)

| Exit | Meaning |
|------|---------|
| `0` | Success |
| `2` | Local usage/parse error (bad flags, missing args) — never reached the gateway |
| `3` | Refused by gateway auth (`AUTH_REFUSED`) |
| `4` | Validation refused — gateway shape-check or server re-validation (`SHAPE_INVALID`, `VALIDATION_FAILED`) |
| `5` | Gateway unreachable / transport failure (connect error, timeout) |
| `1` | Anything else (`AUTH_FAILED`, `UNKNOWN_INTENT`, `VERSION_MISMATCH`, `BAD_ENVELOPE`, `NOT_FOUND`, `UNAUTHORIZED_SENDER`, `INTERNAL`, ...) |

## Examples

```bash
# Enqueue a scheduled job
IGNITE_GATEWAY_ADDR=127.0.0.1:7431 IGNITE_SENDER_TOKEN=$TOKEN \
  ignite add-job --fn my-job --profile my-profile \
    --trigger scheduled --at 2026-08-01T00:00:00Z

# Enqueue a periodic job (first fire defaults to now) and read it back as JSON
ignite --json add-job --fn my-job --profile my-profile --trigger periodic --every 3600 | jq .

# Tail the last 50 lines of an execution's log
ignite inspect logs 42 --tail 50

# Snooze a standing warning for 30 minutes (owner token required)
ignite snooze seat-blocked-budget-exhausted my-seat --minutes 30

# Send a keystroke burst into a live headed session (execution id 42)
ignite send 42 --data $'ls -la\n'

# Capture the same session's current rendered screen
ignite screen 42

# Read the message rows of execution 42's chain-stable thread
ignite inspect messages 42

# Kill session 42 (TERM -> grace -> KILL; status becomes "killed")
ignite kill 42
```

## Known gap — `add-job --dry-run`

`gateway-cli-spec.md`'s CLI Surface table and behavior row 2 spec a
`--dry-run` mode: full gateway + server validation runs, but nothing is
enqueued. The landed wire contract (`gateway/parse.js` `ENQUEUE_KEYS`,
`internal-api-contract-spec.md` §1 `enqueue-job`) carries no validate-only
field — every successfully re-validated `enqueue-job` call inserts a queue
row. `ignite add-job --dry-run` refuses loudly (`commands/add-job.js`) rather
than either enqueueing anyway or faking a client-side validation this thin
wrapper cannot honestly perform. See task p4-2's `open_questions`.

## Probes (`probes/`)

`probe-cli-add.js`, `probe-cli-inspect.js` (covers `inspect messages`),
`probe-cli-remove.js`, `probe-cli-snooze.js`, `probe-cli-dryrun.js`,
`probe-cli-status.js`, `probe-cli-ticker.js`, `probe-cli-send.js`,
`probe-cli-screen.js`, `probe-cli-kill.js` each boot their OWN throwaway daemon (mirrors
`../gateway/probes/probe-gateway-live.js`) and drive this CLI as a real child
process against it — never the live `rbtv-ignite` daemon. `probes/lib/fixtures.js`
holds the shared boot/seed/run helpers.
