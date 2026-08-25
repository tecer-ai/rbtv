---
description: Read before touching the daemon process itself - the HTTP service, the engine composition root, the tick driver, the gateway seam, the job scripts and the host-level passes that are not recovery, not store and not alarm policy.
---

# runtime

The daemon **process host**. Law is
`1-projects/build-ignite/redesign/specs/spec-component-map.md` §1 under [D22],
[T4-R11], [C-15]: no required unit owned "be the process", and folding that into
`supervisor/` or `state-store/` would mix hosting with recovery and with the store.

This component is what runs, listens and drives. It decides nothing about whether a
seat is alive (`supervisor/`), what an ending means (`state-store/`), what an alarm
says (`observation/`), or what a cage admits (`envelope/`).

## What lives here

| Part | File | What it is |
|---|---|---|
| daemon entry | `index.js` | The systemd unit's `ExecStart`: boots the engine, gateway, internal API, cockpit, retention, settings, and runs the cadence loop |
| engine composition root | `engine.js` | `createEngine` - ONE workflow-advancement implementation, TWO attachments (daemon here, `rbtv run` in `operator/`). Was `runtime/engine.js`; renamed only to free `index.js` for the daemon entry, no symbol changed |
| tick driver | `ticker/` | The tick algorithm and its per-cadence passes |
| frozen pass driver | `frozen-pass.js` | Calls `observation/frozen.js` once a cadence with the facts `supervisor/lane-watch.js` already computed. Driver only - the frozen DECISION is observation's |
| gateway | `gateway/` | The typed-message seam: sender auth, parse, dispatch boundary. Reaches nothing in the core by construction (`gateway/probes/probe-gateway-boundary.js`) |
| internal API | `internal-api/` | The daemon-local dispatch surface the CLI and bridges talk to |
| lease | `lease/` | The one-live-run lease the daemon derives and consumers read |
| seat identity | `seat-identity/` | `rbtv-seat-identity` and the peer/seat-folder resolution behind it |
| cockpit / retention / settings / fingerprint | `cockpit.js`, `retention.js`, `settings.js`, `code-fingerprint.js` | Host-level boot and housekeeping passes |
| job scripts | `jobs/` | The `fire-tool` payloads the queue invokes (`jobcontain.py`, `restart-daemon.py`, `recover-room.py`, `agent-tmp-clean.py`) |
| run board / substrate / python-cmd | `run-board.js`, `substrate.js`, `python-cmd.js` | The attached-run board, the platform substrate reads, and the one python interpreter resolver |

## Where its parts came from

`engine/{index,substrate,run-board,frozen-pass}.js`, `server/` minus `heart/` and
`spawn/`, `gateway/`, `jobs/` and `lib/python-cmd.js` - moved with history by
impl-structure-moves-js per `spec-component-map` §2. `server/ticker/goal-stall-alarm.js`
was already D19-archived before the move.
