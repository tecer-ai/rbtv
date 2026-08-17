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
| `ignite register-job <job-id> --action-type <t>` | `register-job` | Registers a job DEFINITION in the catalogue — what the daemon is ABLE to run (task 7.12). CREATE-ONLY: an id already registered is refused typed (`E_JOB_EXISTS`) and nothing is ever overwritten. There is no UPDATE subcommand; the supported way to change a live definition is the two-step retirement below — `deregister-job` then `deregister-job --purge` — then register the id again. `--dry-run` validates without writing. Authorized for the owner AND — under the master APPROXIMATION — any enrolled `agent` sender; `bridge` senders are refused. |
| `ignite deregister-job <job-id> [--purge]` | `deregister-job` | Retires a catalogue DEFINITION, in two steps that are deliberately not one act. Bare = DISABLE (`enabled = 0`): the row and its audit trail stay, the ticker defers every due queue row of a disabled job, and `add-job` refuses it (`E_JOB_DISABLED`). Idempotent; an unknown id is refused typed (`E_UNKNOWN_JOB`), never a success over nothing. `--purge` = DELETE, which FREES THE ID for re-registration — the reclaim path for the machine-minted goal-scoped ids (`<goal>-workflow-start`, `seat-<goal>-<seat>`) a torn-down goal leaves behind. Purge is refused (`E_JOB_PURGE_REFUSED`, `details.reason`) unless the job is ALREADY disabled (`enabled`), has no pending queue rows (`pending-queue-rows` — clear them with `remove-job <queue-id>`; they are never cascaded, since removing a repeating row cancels the whole schedule) and has no non-terminal execution (`live-executions`). Past runs survive a purge: `jobs_log` carries no foreign key to the catalogue and keeps its own copy of every execution. Same authorization as `register-job`. Takes a CATALOGUE id — `remove-job` takes a QUEUE id. |
| `ignite add-job` | `enqueue-job` | Enqueues a job (server-side dry-run-validated before writing). `--dry-run` validates without enqueueing: prints `dry-run: VALID — validated, nothing enqueued` on success, nothing else. |
| `ignite remove-job <queue-id>` | `remove-job` | Removes a pending queue row; removing a repeating row cancels the WHOLE schedule (D68) and the CLI says so. |
| `ignite inspect jobs\|queue\|status <id>\|logs <id> [--tail n]\|daemon\|ticker\|messages <id> [--tail n]` | `inspect` | Read-only. On `logs`, `--tail` walks the offset/limit pages client-side (the contract has no reverse read) and keeps only the last N lines. `messages <id>` (cli-expansion D3): `<id>` is an execution id; the server resolves the execution's chain-stable thread and returns that thread's message rows, paged OLDEST-FIRST (msg_id ASC). Every message page carries `total` (the size of the whole thread), which is what makes the LAST page addressable — `eof` only says whether the page you asked for was the last one. `messages --tail n` gives the NEWEST n in ONE command (the oldest-first order otherwise costs blind offset probes): it reads `total`, then jumps to `total - n` — TWO round trips at any thread size — and reports the total as `tailOf`. Against a daemon predating `total` it falls back to walking the pages. It changes no default: the unflagged listing is still oldest-first. |
| `ignite snooze <kind> <subject> --minutes <n>` | `snooze` | OWNER-ONLY. No standing warning is a clean no-op, never an error. There is no dismiss/clear subcommand — snooze never clears a warning (D45). |
| `ignite inspect executions --status <s> [--offset n] [--limit n] [--tail n]` | `inspect` (`target: executions`) | Read-only. Every execution in ONE `jobs_log` status, paged OLDEST-FIRST — `launching\|running\|done\|blocked\|failed\|stalled\|killed`. The only target that is neither a fixed view nor execution-scoped: it takes no id and answers "every failed run", "every stalled worker". `--status` is REQUIRED (no unfiltered dump) and an unknown status is REFUSED naming the valid set, never answered with an empty list — empty and invalid are different answers. Paging is server-bounded; walk `nextOffset` until `eof`. Every page carries `total` (the size of the whole filtered set), which is what makes the LAST page addressable — `eof` only says whether the page you asked for was the last one. `--tail n` gives the NEWEST n in ONE command (the oldest-first order otherwise costs blind offset probes): it reads `total`, then jumps to `total - n` — TWO round trips at any size, and it reports the total as `tailOf`. Against a daemon predating `total` it falls back to walking the pages like `inspect logs --tail`. It is mutually exclusive with `--offset`/`--limit`, and it changes no default — the unflagged listing is still oldest-first. |
| `ignite status` | `inspect` (`target: daemon`) | Alias for `ignite inspect daemon`. On transport failure (daemon unreachable) prints `daemon: DOWN` instead of a raw connect error. |
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
# Register a job definition (must exist before anything can be queued against it)
IGNITE_GATEWAY_ADDR=127.0.0.1:7431 IGNITE_SENDER_TOKEN=$TOKEN \
  ignite register-job my-job --action-type launch-agent \
    --args-schema '{"required":{"profile":"string"},"optional":{"prompt":"string"}}'

# Validate a definition without writing it
ignite register-job my-job --action-type launch-agent --dry-run

# Enqueue a scheduled job
IGNITE_GATEWAY_ADDR=127.0.0.1:7431 IGNITE_SENDER_TOKEN=$TOKEN \
  ignite add-job --fn my-job \
    --trigger scheduled --at 2026-08-01T00:00:00Z

# Enqueue a periodic job (first fire defaults to now) and read it back as JSON
ignite --json add-job --fn my-job --trigger periodic --every 3600 | jq .

# Tail the last 50 lines of an execution's log
ignite inspect logs 42 --tail 50

# Snooze a standing warning for 30 minutes (owner token required)
ignite snooze seat-blocked-budget-exhausted my-seat --minutes 30

# Read the message rows of execution 42's chain-stable thread
ignite inspect messages 42

# Triage the fleet by state: every failed run, then every stalled worker
ignite inspect executions --status failed
ignite inspect executions --status stalled

# Page through a large result (walk nextOffset until eof)
ignite --json inspect executions --status done --offset 0 --limit 50 | jq '.result | {rows: (.rows|length), nextOffset, eof}'

# Kill session 42 (TERM -> grace -> KILL; status becomes "killed")
ignite kill 42
```

## Probes (`probes/`)

`probe-cli-register.js`, `probe-cli-deregister.js` (covers `--purge` end to end — its three
guards are proved at the store layer by `../server/heart/probes/probe-deregister-purge.js`,
where a pending queue row and a live execution can be seeded without spawning real work),
`probe-cli-add.js`, `probe-cli-inspect.js` (covers `inspect messages`),
`probe-cli-remove.js`, `probe-cli-snooze.js`, `probe-cli-dryrun.js`,
`probe-cli-status.js`, `probe-cli-ticker.js`,
`probe-cli-kill.js` each boot their OWN throwaway daemon (mirrors
`../gateway/probes/probe-gateway-live.js`) and drive this CLI as a real child
process against it — never the live `rbtv-ignite` daemon. `probes/lib/fixtures.js`
holds the shared boot/seed/run helpers.

`probe-cli-executions.js` (task 7.62) joins them, covering `inspect executions` at this layer;
the same feature is ALSO covered below the transport by
`../server/internal-api/probes/probe-inspect-executions.js`, which additionally guards the closed
target and status sets. The two are deliberately not redundant — the in-process probe cannot see
the transport or argv, and the child-process probe cannot import a constant to compare it.

⚑ A fixture fact worth knowing before writing any probe here that seeds executions: **a booted
daemon REWRITES non-terminal statuses within its first tick.** `stalled` is swept by the stall
ladder, `blocked` is re-dispatched, and `launching`/`running` meet the crash sweep — so a probe
seeding one of those against a live daemon races the ticker and reads as a broken feature.
`probe-cli-executions.js` hit exactly that on its first run (all three seeded rows read `failed`
~1.5 s after boot) and now seeds only terminal statuses, asserting the seeded state is still on
disk before it tests anything.
