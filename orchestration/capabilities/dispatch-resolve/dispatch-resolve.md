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

## Who consumes it — MANUAL INVOCATION IS THE CONTRACT

Owner ruling `d-r2-preflight-manual-plus-skill` (2026-08-10). There is **no automated wiring, by
design**: no code path composes a CLI-worker command line (`route.py` emits an
`invocation_pointer`, `scaffold.py` only checks manual drift, the AGENT types the command), so
nothing reads `preflightDispatch` or `addDirResolved` but the conductor's own eyes. The supported
consumption path is the conductor invoking this capability BEFORE packaging a dispatch, and the
front door is the **`rbtv-dispatch-resolve` skill** (`orchestration/skills/dispatch-resolve/`) —
which exists so the conductor reaches for this call instead of hand-composing the add-dir flag.
A future automated consumer is not owed; a zero-consumer grep is the expected reading.

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

`probe-dispatch-resolve` — 22 checks, exit 0/1, GREEN 2026-08-10 (Windows box). The committed
`probe-dispatch-resolve.out` beside it is the pre-repoint VPS capture and is **stale**.

⚠ **REPOINTED 2026-08-10, and the shape changed with it.** It used to pin four profile names the
shipped config no longer carries (`claude-seat`, `claude-sonnet-tools`, `codex-git-write`,
`opencode-sakana` — `r-seats-only-architecture` retired all four and re-rostered the file to 14),
so 11 of 19 checks failed at their PRECONDITIONS before any bound was exercised and the verdict
carried no information. The lane's own bounds now run against a **fixture this probe writes**, the
sibling `probe-extra-dir-slot` pattern, so a roster change cannot strand them again; four `LIVE-*`
checks carry what is genuinely a statement about the shipped tree, asserted as relationships rather
than counts. Two of those are tripwires over live defects this lane does not own:

- `LIVE-2` — **every** shipped profile now inherits the shared `cage:` block's `SeatBinds`, so the
  deny-list refuses all 14: this lane can resolve **zero** live profiles. The deny-list is not
  wrong; its premise (seat profiles are the exception) is. Fixing it is an architecture call.
- `LIVE-3` — all **11** recorded `launch_profile` values name `cli-*` twins task 7.86 was to author
  and `r-seats-only-architecture` retired, so the manifest→profile mapping is **100% dangling**.
  `probe-extra-dir-slot` check `4-GAP` measures the same absence from the config side.

`probe-extra-dir-slot` — task **7.87 criterion 4**: 10 checks, exit 0/1, GREEN 2026-08-10. It runs
against a **fixture** config (the live daemon's armed config must not gain an argv-changing row on
this row's authority) and asserts the shipped config is untouched in the same run. Every leg is
two-directional, and the injection itself is **mutation-verified**: neutering `resolveExtraDirSlot`
to return the caller's slots unchanged turns checks `2` and `2-DOOR` FAIL (`E_MISSING_KEY`, and the
smuggled relative value reaching argv). Source restored and re-verified green in the same sitting.

**Every refusal is exercised in BOTH directions**, because *"it passed everywhere"* and *"it cannot
fail anywhere"* print the same thing (`bars.md` 11). The probe also asserts its own preconditions
(the bare load really refuses; `fx-seat` really declares `SeatBinds`) — a deny-list tested against a
profile that declares nothing proves nothing. `1-GREEN` additionally asserts its subject EXISTS:
`assertNoSeatBinds` returns silently for an unknown name, so the retired `claude-sonnet-tools` kept
"passing" that check for days after it stopped existing.

**Mutation-verified 2026-07-28, re-verified 2026-08-10 after the repoint**, because a green probe is
not evidence that it discriminates: neutering the deny-list turned `1-RED`, `1-RED-via-entry` **and
`LIVE-2`** FAIL (19/3); neutering the add-dir guard turned `2a-RED` and `2b-RED` FAIL (20/2). Source
restored byte-identical and re-verified green (22/0) in the same sitting.
