# `dispatch-resolve` — the conductor's seam onto the shared launch-profile resolver

Task **7.54**. The orchestration conductor is the THIRD consumer of the ONE shared resolver
`ignite/launch-profiles/` (task 7.42). Consumer 1 is the daemon's spawn path
(`ignite/server/spawn/config.js`), consumer 2 the sub-agent dispatch capability (task 7.43).

Governing records: registry `decisions.md#d-profile-source-unification`, DEC-1 § Shared profile
source, CMP-9. Leader rulings `#1465` (the three forks) and `#1486` (criterion-1 scope + the
add-dir homing).

## What it does

One entry point. Resolution and pre-flight in a single call, so a caller cannot obtain a resolved
argv without the refusals having run:

```js
const lane = require('orchestration/capabilities/dispatch-resolve');
const config = lane.loadProfiles('<rbtv>/ignite/config/spawn-profiles.yaml');
const { argv, preflight } = lane.preflightDispatch(config, 'claude-sonnet-tools', {
  addDir: '/abs/path/to/work-target',
  effort: 'high',
});
```

The caller supplies a profile **NAME**, an abstract **effort** level, and values for **DECLARED
SLOTS** — never argv, never flags. Effort reaches the harness in that harness's own dialect via the
profile's translation table (`high` → `--effort high` for claude, `-c model_reasoning_effort=high`
for codex), never as a hand-written flag.

## The three refusals this module adds

The shared resolver raises its own (`E_UNKNOWN_PROFILE`, `E_RAW_FLAG`, `E_UNKNOWN_EFFORT`,
`E_PINNED_FLAG_ABSENT`, `E_PREFLIGHT_UNAVAILABLE`). These three are the conductor's:

| Code | Fires when | Why it exists |
|------|-----------|---------------|
| `E_SEATBINDS_PROFILE` | the named profile declares `sandbox.SeatBinds` | This consumer loads the config through a **non-interpreting validator stub**, because the real validator lives in `server/spawn/cage.js` and the conductor may not import daemon code. The stub DEFEATS that guard; this deny-list is what converts *"the conductor will never resolve `claude-seat`"* from discipline back into enforcement. **The stub and the deny-list are one mechanism — neither ships without the other.** |
| `E_ADD_DIR_ABSENT` | no work-target was supplied | The confinement split (`dispatch-wrapper.md:36`, row G1) needs TWO path values; a profile expresses ONE. Earned by the `a3e217d` incident — a bare kimi self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo. |
| `E_ADD_DIR_RELATIVE` | the work-target is not absolute | A relative path resolves against the spawning shell's CWD, which drifts after any prior `cd` (`dispatch-wrapper.md:35`). |

## ⚠ What this does NOT do — read before assuming coverage

**The confinement split is ENFORCED, not SOLVED.** `{extra_dir}` is not an authorable slot —
`CLOSED_SLOTS` is `{workdir} {prompt_file} {session_ref}`, closed at config LOAD with
`E_UNKNOWN_SLOT`, and widening it is task **7.87**. So the add-dir flag is **still hand-composed**.
This module does not make that correct; it makes its ABSENCE LOUD.

**Coverage is 2 of 11 elected CLI `(model, variant)` pairs**, and that is deliberate:
`claude-code-cli:sonnet` and `opencode:sakana`. Authoring the missing profiles is task **7.86**.
A pair with no `launch_profile` dispatches from its package manual as before — those manuals are
intact and must stay so until 7.86 lands.

**And 1 of 11, not 2, completes a fully resolver-backed pre-flight today.** Two live gaps, both
FILED rather than worked around, both tripwired in the probe so they fail the day they are fixed:

- **`G-270`** — `opencode-sakana` declares no effort dial and does not declare `effort: { inert: true }`,
  so the resolver refuses every effort-bearing dispatch. Routing sets an effort for *every*
  dispatch. The fix is one line in the LIVE DAEMON'S ARMED CONFIG — the leader's call, not this
  row's.
- **`G-271`** — `opencode run --help` writes to stderr and exits 0; the shared `readHelp` merges
  stderr only in its catch branch (non-zero exit), so a clean-exit stderr help reads as empty.

## Probe

```
node orchestration/capabilities/dispatch-resolve/probes/probe-dispatch-resolve.js
```

19 checks, exit 0/1. Output committed beside it as `probe-dispatch-resolve.out`.

**Every refusal is exercised in BOTH directions**, because *"it passed everywhere"* and *"it cannot
fail anywhere"* print the same thing (`bars.md` 11). The probe also asserts its own preconditions
(the bare load really refuses; `claude-seat` really declares `SeatBinds`) — a deny-list tested
against a profile that declares nothing proves nothing.

**Mutation-verified 2026-07-28**, because a green probe is not evidence that it discriminates:
neutering the deny-list turned checks `1-RED` and `1-RED-via-entry` FAIL; neutering the add-dir
guard turned `2a-RED` and `2b-RED` FAIL. Source restored and re-verified green in the same sitting.
