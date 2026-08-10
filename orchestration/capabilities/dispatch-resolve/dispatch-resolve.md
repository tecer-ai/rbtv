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

## The work-target resolves THROUGH the profile (task 7.87 criterion 4)

`{extra_dir}` **is** an authorable slot — `CLOSED_SLOTS` is
`{workdir} {prompt_file} {session_ref} {extra_dir}` (7.87 widened it; the set is still CLOSED, and
an unknown slot is still `E_UNKNOWN_SLOT` at config LOAD). A profile therefore writes its own
add-dir flag:

```yaml
argv: ["claude", "-p", "--cd", "{workdir}", "--add-dir", "{extra_dir}"]
```

and `preflightDispatch` substitutes the caller's `addDir` into **the position the profile wrote** —
the conductor no longer hand-composes that flag. Two consequences worth naming:

- **The add-dir flag is now pre-flighted.** `pinnedFlagsOf` scans profile-written argv elements, so
  `--add-dir` is checked against the live `--help` like any other pinned flag. A hand-composed flag
  never was.
- **`addDir` stays the ONE door.** A caller-supplied `slots.extra_dir` is overwritten by the value
  `assertWorkTarget` validated, so `E_ADD_DIR_ABSENT` / `E_ADD_DIR_RELATIVE` cannot be routed
  around through the slot map.

**Strictly opt-in, and that is the safety bound.** A profile declaring no `{extra_dir}` is
UNCHANGED: the slot is not injected (it would be `E_RAW_FLAG`), the resolved argv is byte-identical
to before the widening, and the add-dir remains the caller's to compose — the refusals above still
make its absence loud. The result carries **`addDirResolved`** (`true` = the profile wrote the
flag; `false` = the caller still owes one) so no consumer has to guess. A profile with two command
halves must declare the slot in **every** half — the half is picked by host detection, and a
one-sided declaration would resolve differently per machine, so it falls back to the hand-composed
path instead.

⚠ **NO SHIPPED PROFILE DECLARES IT YET, so today this is a capability rather than a deployment.**
`ignite/config/spawn-profiles.yaml` is the live daemon's armed config; declaring the slot on a
shipped profile changes that profile's resolved argv for every daemon spawn, which task 7.42's
byte-unchanged criterion (re-asserted at 7.87) puts outside this row's authority. The two pairs
that record a `launch_profile` point at `cli-claude-sonnet` / `cli-opencode-sakana`, which **task
7.86 has not authored** — those are the conductor-lane profiles the flag belongs on. Both facts are
tripwired in `probe-extra-dir-slot.js` (checks `4` and `4-GAP`) and fail the day they change.

⚠ **opencode is the documented exception, not an omission.** Its launch root **is** the
work-target (`opencode run` resolves against the launch directory; the profiles pin no `--dir`), so
there is no add-dir split to express and `{extra_dir}` is **inapplicable** to that harness. Its
confinement is the launch root itself.

## ⚠ What this does NOT do — read before assuming coverage

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

## Probes

```
node orchestration/capabilities/dispatch-resolve/probes/probe-dispatch-resolve.js
node orchestration/capabilities/dispatch-resolve/probes/probe-extra-dir-slot.js
```

Both are run DIRECTLY: `ignite/deploy/probe-suite.js` enumerates `ignite/` only, so an
orchestration-module probe is outside the runner's reach.

`probe-dispatch-resolve` — 19 checks, exit 0/1. Output committed beside it as
`probe-dispatch-resolve.out`.

⚠ **`probe-dispatch-resolve` is RED against the current config and the cause is DRIFT, not this
lane** (measured 2026-08-10, Windows box: 8 pass / 11 fail). It pins profile names the shipped
config no longer carries — `claude-seat`, `claude-sonnet-tools`, `codex-git-write`,
`opencode-sakana` are gone, `r-seats-only-architecture` renamed the roster to 14 profiles — so its
own preconditions (`P4` "all 6 profiles", the `claude-seat` deny-list control) fail before any bound
is exercised. Repointing it is its own row; treat its verdict as stale until then.

`probe-extra-dir-slot` — task **7.87 criterion 4**: 10 checks, exit 0/1, GREEN 2026-08-10. It runs
against a **fixture** config (the live daemon's armed config must not gain an argv-changing row on
this row's authority) and asserts the shipped config is untouched in the same run. Every leg is
two-directional, and the injection itself is **mutation-verified**: neutering `resolveExtraDirSlot`
to return the caller's slots unchanged turns checks `2` and `2-DOOR` FAIL (`E_MISSING_KEY`, and the
smuggled relative value reaching argv). Source restored and re-verified green in the same sitting.

**Every refusal is exercised in BOTH directions**, because *"it passed everywhere"* and *"it cannot
fail anywhere"* print the same thing (`bars.md` 11). The probe also asserts its own preconditions
(the bare load really refuses; `claude-seat` really declares `SeatBinds`) — a deny-list tested
against a profile that declares nothing proves nothing.

**Mutation-verified 2026-07-28**, because a green probe is not evidence that it discriminates:
neutering the deny-list turned checks `1-RED` and `1-RED-via-entry` FAIL; neutering the add-dir
guard turned `2a-RED` and `2b-RED` FAIL. Source restored and re-verified green in the same sitting.
