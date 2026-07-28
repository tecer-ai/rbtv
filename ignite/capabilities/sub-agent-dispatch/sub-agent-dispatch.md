# sub-agent-dispatch — the CLI-lane instrument of the standing sub-agent lane

Core-build task **7.43**. Registry: `CMP-10 § Standing sub-agent lane`,
`system-definition/decisions.md#d-sub-agent-standing-lane` (the lane),
`#d-sub-agent-exposure-enforcement` (its enforcement class),
`#d-catalog-bound-exposure-manifest` (what the catalog IS),
`#d-sub-agent-population-bounds` (boundaries 9–10), `#d-sub-agent-env-allowlist` (boundary 11).

The tool is `tool/rbtv-subagent`. It launches a **headless sub-agent attached to the caller's
terminal**: the sub-agent runs in the foreground of one invocation, its output returns there and
nowhere else, and it dies when that invocation does — by any means, including `SIGKILL`.

**Two instruments, one cage, typed by LANE.** The harness's own sub-agent tool is the preferred
instrument and its counterpart bounds are `constraints`-class — judgment-honored, carried to the
dispatching agent by the rule task 7.49 ships. **This lane's bounds are `restrictions`-class:
fail-closed in this capability's own code, nothing left to the model's judgment.** Neither lane's
bounds are restated in the other's home, and native-tool DETECTION is deliberately absent here —
native-first is guidance for the agent, not a thing a CLI discovers.

## The cage

Every row is a typed error and a non-spawn. **There is no `--force`, no `--allow`, and no
environment override on any of them**: an escape hatch on a fail-closed bound is the bound's repeal.

| # | Boundary | Where it is enforced | Refusal |
|---|---|---|---|
| 1 | catalog-bound | `catalog.js` — the target must be exposed for `sub-agent` dispatch by a component's exposure manifest | `E_TARGET_NOT_CATALOGED` · `E_NO_CATALOG` · `E_CATALOG_ROW_INVALID` |
| 2 | profile-bound | `dispatch.js` via `launch-profiles.resolveProfile` — the SAME shared config the daemon spawns from; slots only, never appended argv | `E_UNKNOWN_PROFILE` · `E_RAW_FLAG` |
| 3 | no coordination access | `env.js` — constructed environment + a system PATH carrying no coordination CLI | (structural: nothing to call) |
| 4 | dies with the dispatching step | `supervisor.js` — a **death pipe** the kernel closes when the dispatcher dies | (structural) |
| 6 | no seat impersonation | `dispatch.js:assertNotSeatIdentity`, on the RESOLVED workdir before any spawn | `E_SEAT_IMPERSONATION` |
| 8 | own process group | `dispatch.js` spawns the supervisor `detached`, so `kill(-pgid)` cleans the tree | (structural) |
| 9 | no nesting | `dispatch.js:assertNotNested` — the depth marker the dispatcher stamps | `E_NESTING_REFUSED` |
| 10 | per-dispatcher fan-out cap (5) | `fanout.js` — a locked registry keyed on the caller's POSIX session | `E_FANOUT_EXCEEDED` |
| 11 | scrubbed environment | `env.js` — built from an EMPTY object | `E_ENV_VAR_MISSING` · `E_ENV_LEAK` |

Boundary 5 is a granted exemption, not a bound. Boundary 7 (native-first) is the other lane's.

**Why the death pipe rather than an exit handler.** Boundary 4 says the sub-agent dies with the
dispatching step. A handler honours that on a clean exit and **not** on `SIGKILL` — and 7.43's
criterion is precisely *"killing the dispatcher mid-run and observing the whole tree die"*, so a
handler would satisfy the sentence and fail the test. The dispatcher holds the write end of a pipe
whose read end is the supervisor's fd 3. Nothing is ever sent through it; when the dispatcher dies
the kernel closes the write end, the supervisor reads EOF and kills its own process group. It is
delivered by the kernel rather than by anyone's cooperation, and it cannot be forgotten.

## The two shared modules, and no private copy of what they hold

This capability is the **second live consumer** of `ignite/launch-profiles` (task 7.42) and of
`ignite/injection-ladder` (task 7.45); both index headers named it as an unbuilt one. It holds
**no per-harness launch-method table of its own** — that absence is 7.45's criterion 3.

**The rung is never passed in.** `resolveRung()` receives the SITUATION — the harness (derived from
the profile's own `argv[0]`), `phase: 'launch'`, the caller's `--resumable` requirement verbatim,
and `hostSupports: { keystroke: false }` (a true property of a lane with no pane, not a preference)
— and WALKS. The walk is discriminating at that call site, which is what lets a check over it fail:
under the same `--resumable`, an opencode profile resolves to **no rung at all** (its headless rung
is one-shot, `G-13`; hooks cannot make a session reachable again; keystroke is inject-only) while a
claude profile resolves to `headless`. Neither answer is written anywhere in this capability.

## The interim exposure manifest — which columns, and why

`ignite/exposure.csv`, ONE row, one target, marked INTERIM on its own face. Authored under the
leader's fork-3 ruling (option (d)) and its four binding bounds. **Task 7.48 is free to re-shape it
without treating it as precedent**, which is what this section exists to make possible.

- **The columns are the six of `concepts/exposure-manifest.md` § file schema, in its order** —
  `part-id, part-kind, method, rbtv-cli, entry-point, description`. They are ROUTED, not invented:
  the registry record already specifies them. Choosing anything else would have been the minting
  act the ruling was careful to avoid.
- **Dispatchability is read from the `method` column's `sub-agent` value.** The ruling left exactly
  this open ("the `method` column's `sub-agent` value, the `rbtv-cli` column, or a dedicated
  marker are Phase-3/4 design output"). `sub-agent` is **already a member of the canonical
  exposure-method vocabulary** (`#d-exposure-method-canon`), so reading it from `method` mints
  nothing. The two alternatives both cost more: the `rbtv-cli` column answers a different question
  (what the CLI exhibits at drill level 2), and overloading it would make a DISPLAY decision change
  a SECURITY one; a dedicated marker column would be a second way to say what the vocabulary
  already says (`PRIN-11`).
- **The cost of this choice, stated:** `method` is single-valued, so a part exposed BOTH as a skill
  and for sub-agent dispatch cannot be expressed in one row today. CMP-10's own multi-exposure
  note (`concepts/component.md`: "one component MAY be surfaced by several exposure methods at
  once") says that case is real. **7.48 will have to solve it** — with multiple rows per part, a
  multi-valued method cell, or the dedicated marker after all. This build did not need to, because
  its one target has one exposure.
- **It sits at the MODULE root, not at `<module>/<component>/exposure.csv`.** Measured 2026-07-28:
  no component folders exist anywhere in this repo (CMP-5's component-first layout is Phase-6
  migration work, unbuilt). `catalog.js` scans BOTH depths, so when that tree materializes and 7.48
  moves the file one level down, nothing needs editing.

## Placement

`ignite/capabilities/sub-agent-dispatch/` — matching the shape of the three capabilities already on
disk (`daemon-operator`, `goals-tree`, `ticker-settings`), which sit at
`<module>/capabilities/<name>/` with `tool/` and `probes/` beside a `<name>.md`. The documented
convention (`rbtv/CLAUDE.md` § CLI Tool Placement, owner-ruled 2026-07-26) is
`<module>/<component>/capabilities/<name>/tool*/` — one level deeper. **Matched the observed
sibling shape rather than the documented one**, because the intermediate `<component>` folder does
not exist for any capability in this repo and inventing one here would create a fourth layout.
Disclosed rather than papered over.

The task is tagged `#mod/orchestration`, and the naive reading — *"so it is Python, like the rest of
orchestration"* — would have put a fourth copy of the launch knowledge in the repo, which is the
exact defect 7.42 and 7.45 exist to prevent. Measured: `orchestration/` has 0 `.js` files, 32 `.py`,
and no file there requires anything under `ignite/`. The two modules this consumes are Node
CommonJS and live under `ignite/`. Language is not homogeneous per module —
`ignite/capabilities/` already ships bash, python and node tools side by side.

## Findings routed to the leader, not fixed here

Each is outside this task's write surface, and each is a real consequence a later task must settle.

1. **Boundary 10's `default 5` has NO home, and the ruled home is structurally CLOSED.** CMP-10
   says the cap is "a config value (default 5) in the same shared config the lane's launch profiles
   live in". Measured: no such key exists, and `launch-profiles/profiles.js` `KNOWN_TOP_KEYS` is a
   closed allowlist, so adding a root key to `spawn-profiles.yaml` is a loud `E_CONFIG_LOAD`. The
   value therefore lives in `fanout.js` and the absence is reported, never quietly supplied.
2. **Boundary 11's declaring home does not exist either.** CMP-10 says only the variables the
   profile "explicitly names" pass through. The profile `env` block admits exactly one key —
   `file`, an EnvironmentFile path for the daemon's systemd carrier. A profile cannot name a
   variable today. The consequence here is fail-closed and therefore safe (the allowlist is the
   minimal base and nothing else), and `env.js:declaredEnvNames()` already reads the `env.allow`
   key the ruling implies, so the day 7.42's schema carries it this lane honours it with no edit.
3. **The shared resolver is unusable by a non-daemon consumer without importing daemon code.**
   `loadConfig` refuses the committed config outright unless the caller injects a SeatBinds
   template validator (profile `claude-seat` declares `sandbox.SeatBinds`), and that validator
   lives in `server/spawn/cage.js` — which the shared module may not import. So every non-daemon
   consumer must either import daemon code or lose access to EVERY profile because ONE declares a
   key it cannot validate. This capability injects it (a read-only require of a pure validator).
4. **`scanPath` is exported by `launch-profiles/host.js` but not re-exported by its `index.js`.**
   Reached into the file rather than duplicating an eight-line PATH scan.
5. **A third home for "which workspace roots `.rbtv/`".** `launch-profiles/profiles.js` derives it
   from the heart store's db path; `ticker-settings`' CLI carries its own unit-first resolver; this
   capability now carries a third, adopted from ticker-settings because **the first build of this
   file hit that surface's exact defect** — a cwd walk-up from inside the rbtv repo put a live
   sub-agent's session dir in the repo's own `.rbtv/`, which is untracked and **not gitignored**
   there. Convergence candidate.

## Probes

`probes/probe-sub-agent-dispatch.js` — 29 checks, run with `node probes/probe-sub-agent-dispatch.js`.
It runs against the committed config, the committed manifest, the real workspace `.rbtv/sessions/`
and a REAL claude harness; it supplies no paths of its own to the dispatch path.

**⚠ It costs real money and real time, and `deploy/probe-suite.js` discovers it by structure** — so
every suite run now makes TWO real claude invocations (~60–90 s, a few tens of cents) and SIGKILLs
a process tree. Deliberate, and not free: 7.43's positive criteria say *"a real run"* and *"proven
by path inspection **after a real run** rather than by a claim"*, so a probe that mocked the harness
would satisfy the suite and fail the row.

**Every check is paired where pairing is possible.** A refusal check is worthless unless the same
call succeeds when the bound is not violated, and a wall check is worthless unless the same
instrument finds the thing on the unwalled side. The two that matter most:

| Control | Proves |
|---|---|
| the SAME supervisor spawned WITHOUT the built environment | the leak canary IS present there — so the environment checks fail on the pre-fix code **by construction**, and are not green either way |
| a detached child WITHOUT the death pipe, parent `SIGKILL`ed | it SURVIVES — so "the whole tree died" is the death pipe's doing and not the OS's |

The probe asserts its own completeness: a short tally is a FAILURE however many checks passed
(`G-121`). That assertion earned its keep on the first run — an all-green 29 was correctly graded a
failure against a hand-counted literal of 27 until the count was reconciled.

**What the probe does NOT prove**, stated rather than left to be noticed: the positive half runs
against an exposure manifest this task's own seat authored (`bars.md` 10); the fan-out cap is
exercised with real live processes but not with five concurrent real harnesses; and the
`E_ENV_VAR_MISSING` branch is unreachable on the committed profile schema (finding 2), so it is
built and unexercised.
