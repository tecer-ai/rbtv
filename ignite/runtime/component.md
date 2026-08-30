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
| engine composition root | `engine.js` | `createEngine` - ONE workflow-advancement implementation, TWO attachments (daemon here, `rbtv run` in `operator/`). Was `runtime/engine.js`; renamed only to free `index.js` for the daemon entry, no symbol changed. It also OPENS the one ending store (`openEndingStoreFor(heartStore.config.workspaceRoot)`) and hands it out as `engine.endingStore` - the handle `supervisor/reconcile.js` stamps the exhaustion exit, drains the leader's answers and spends the recovery budget through; an unopenable home is `null` plus one error line, never a boot that dies. Probe: `probes/probe-engine-ending-store.js` |
| tick driver | `ticker/` | The tick algorithm and its per-cadence passes |
| frozen pass driver | `frozen-pass.js` | Calls `observation/frozen.js` once a cadence with the facts `supervisor/lane-watch.js` already computed. Driver only - the frozen DECISION is observation's |
| gateway | `gateway/` | The typed-message seam: sender auth, parse, dispatch boundary. Reaches nothing in the core by construction (`gateway/probes/probe-gateway-boundary.js`) |
| internal API | `internal-api/` | The daemon-local dispatch surface the CLI and bridges talk to. FIFTEEN intents as of the owner direction of 2026-08-28 (`pause-resume`, the mechanical `pause {goal}` / `resume {goal}`, bridge-only like the twelfth/thirteenth/fourteenth). The closed set exists in THREE copies by design (DEC-4: no gateway↔core import) — `gateway/parse.js` INTENTS, `internal-api/dispatch.js` INTENTS, and the `switch` cases — and every new intent extends all three together; `internal-api/probes/probe-intent-drift.js` is the lockstep guard. `inspect asks` answers from BOTH ask records - the `open_asks` table and the recovery exit's signature-grouped files under `<workspace>/.rbtv/runtime/ignite/asks/` - merged oldest-first, so spec-owner-io §5's digest reads one waiting set through one port. A `pause-resume` refused for an unknown goal journals its own info line before the `NOT_FOUND`, so a mistyped slug is visible daemon-side and not only in the bridge's journal. `pause-resume`'s payload carries an OPTIONAL `chat_user` (owner re-ruling D-4(a), 2026-08-30) — the Slack sender the bridge reports, shape-checked at both `parse.js` and `dispatch.js` independently (DEC-3), never read by `authz.canPauseResume`, and named only in the state-store's evidence text |
| lease | `lease/` | The one-live-run lease the daemon derives and consumers read |
| seat identity | `seat-identity/` | `rbtv-seat-identity` and the peer/seat-folder resolution behind it |
| cockpit / retention / settings / fingerprint | `cockpit.js`, `retention.js`, `settings.js`, `code-fingerprint.js` | Host-level boot and housekeeping passes |
| code-deploy re-arm | `code-deploy-rearm.js` | spec-recovery §5's `code-deploy` event, at boot: if this boot's WIDE `ignite/` code digest differs from the one the last boot recorded on `.rbtv/runtime/daemon-code.json`, every attempt counter is re-armed and each cleared row is journalled. A restart hashes the same bytes and re-arms nothing; an UNKNOWN digest re-arms nothing. Runs BEFORE `writeCodeMarker`, which is what records the new digest - there is no second ledger. Probe: `probes/probe-code-deploy-rearm.js` |
| job scripts | `jobs/` | The `fire-tool` payloads the queue invokes (`jobcontain.py`, `restart-daemon.py`, `recover-room.py`, `agent-tmp-clean.py`) |
| run board / substrate / python-cmd | `run-board.js`, `substrate.js`, `python-cmd.js` | The attached-run board, the platform substrate reads, and the one python interpreter resolver |

## `inspect daemon` answers standing conditions from TWO sources, never one

`inspect daemon` (what `ignite status` is the alias for) is the read every role reaches for to
answer "is anything standing". It publishes **both** of these, and a reader states both:

| Field | Source | Empty means |
|---|---|---|
| `standing_warnings` | the daemon's OWN warning table (`heartStore.listWarnings({standingOnly:true})`) | no daemon warning is standing |
| `open_conditions` | the ONE alarm registry (`observation/emitter.js#readOpenConditions`, over `<workspace>/.rbtv/runtime/ignite/alarm-registry.json`) — every alarm ANY component raised through the one emitter: the watchdog's row alarms and its N-fail alarm, the frozen-goal invariant | no alarm condition is open |

⚠ **`null` on `open_conditions` is NOT `[]`.** `[]` says nothing is open; `null` says this daemon
holds no workspace root and therefore CANNOT READ the registry at all. Collapsing them would
publish "no alarm is standing" from exactly the configuration that cannot know.

⚠ The emitter instance behind `open_conditions` is handed a `post` that **throws**, as
`chat/glance.js` does: the daemon's status read never EMITS an alarm [T4-R10]. It `reload()`s
before every read, because the WRITERS are other processes — a constructor-time snapshot would
report the alarm set as it stood at boot, indistinguishable from "nothing is wrong", for the whole
life of the daemon.

WHY THIS EXISTS. Until 2026-08-28 only `standing_warnings` was published, and the master material
told every role that field IS the alarm surface. It is the daemon's own warnings and nothing else:
spec-owner-io §5 puts open conditions in the alarm-signature registry, written from OUTSIDE this
process. On 2026-08-26 a master seat read this answer and told the owner "No standing warnings"
while the watchdog had held an hours-old `probe-suite` alarm. Guard:
`internal-api/probes/probe-inspect-open-conditions.js` (18 checks, with a red control that removes
the field and asserts `undefined`).

## Where its parts came from

`engine/{index,substrate,run-board,frozen-pass}.js`, `server/` minus `heart/` and
`spawn/`, `gateway/`, `jobs/` and `lib/python-cmd.js` - moved with history by
impl-structure-moves-js per `spec-component-map` §2. `server/ticker/goal-stall-alarm.js`
was already D19-archived before the move.
