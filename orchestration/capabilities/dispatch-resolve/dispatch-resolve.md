# `dispatch-resolve` — the conductor's seam onto the shared launch-profile resolver

Task **7.54**. The orchestration conductor is the THIRD consumer of the ONE shared resolver
`ignite/launch-profiles/` (task 7.42). Consumer 1 is the daemon's spawn path
(`ignite/server/spawn/config.js`), consumer 2 the sub-agent dispatch capability (task 7.43).

Governing records: registry `decisions.md#d-profile-source-unification`, DEC-1 § Shared profile
source, CMP-9. Leader rulings `#1465` (the three forks) and `#1486` (criterion-1 scope + the
add-dir homing). **Owner ruling 2026-08-11** — `launch_profile` retired, manual invocation
permanent (executes `d-r2-preflight-manual-plus-skill`) — retired the seat-binds deny-list and the
manifest field; § *What this lane does NOT give you* states what is left.

## What it does

One entry point. Resolution and pre-flight in a single call, so a caller cannot obtain a resolved
argv without the refusals having run:

```js
const lane = require('orchestration/capabilities/dispatch-resolve');
const config = lane.loadProfiles('<rbtv>/ignite/config/spawn-profiles.yaml');
const { argv, preflight } = lane.preflightDispatch(config, 'claude-opus', {
  addDir: '/abs/path/to/work-target',
  effort: 'high',
});
```

The profile NAME is the conductor's own choice — no manifest records one any more. `claude-opus` is
a real key of the shipped roster; read the roster before naming one, and read the section below
before treating the resolved argv as a command you can simply type.

The caller supplies a profile **NAME**, an abstract **effort** level, and values for **DECLARED
SLOTS** — never argv, never flags. Effort reaches the harness in that harness's own dialect via the
profile's translation table (`high` → `--effort high` for claude, `-c model_reasoning_effort=high`
for codex), never as a hand-written flag.

## Who consumes it — MANUAL INVOCATION IS THE CONTRACT

Owner ruling `d-r2-preflight-manual-plus-skill` (2026-08-10), made permanent by the owner ruling of
2026-08-11. There is **no automated wiring, by design**: no code path composes a CLI-worker command
line (`route.py` emits an `invocation_pointer`, `scaffold.py` only checks manual drift, the AGENT
types the command), so nothing reads `preflightDispatch` or `addDirResolved` but the conductor's own
eyes. The supported consumption path is the conductor invoking this capability BEFORE packaging a
dispatch, and the front door is the **`rbtv-dispatch-resolve` skill**
(`orchestration/skills/dispatch-resolve/`) — which exists so the conductor reaches for this call
instead of hand-composing the add-dir flag. A future automated consumer is not owed; a zero-consumer
grep is the expected reading.

## The two refusals this module adds

The shared resolver raises its own (`E_UNKNOWN_PROFILE`, `E_RAW_FLAG`, `E_UNKNOWN_EFFORT`,
`E_PINNED_FLAG_ABSENT`, `E_PREFLIGHT_UNAVAILABLE`). These two are the conductor's:

| Code | Fires when | Why it exists |
|------|-----------|---------------|
| `E_ADD_DIR_ABSENT` | no work-target was supplied | The confinement split (`dispatch-wrapper.md:36`, row G1) needs TWO path values; a profile expresses ONE. Earned by the `a3e217d` incident — a bare kimi self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo. |
| `E_ADD_DIR_RELATIVE` | the work-target is not absolute | A relative path resolves against the spawning shell's CWD, which drifts after any prior `cd` (`dispatch-wrapper.md:35`). |

**`E_SEATBINDS_PROFILE` was the third, and it is RETIRED** (owner ruling 2026-08-11). It refused any
profile declaring `sandbox.SeatBinds`, on the premise that seat profiles were the exception. That
premise died at `r-seats-only-architecture` (2026-08-06), which made the shared `cage:` block every
profile's sandbox: the deny-list then refused all 14 and the lane could resolve nothing at all.
What makes its removal safe is the fact that always made it redundant — **`resolveProfile` returns
argv / binary / effort / toolset and NOT the sandbox block**, so a bind template this consumer never
validated also never reaches a command line through it. The non-interpreting stub stays (without it
the config does not load here at all); it now has nothing to leak. Probe `1-NO-CAGE-IN-ARGV` asserts
exactly that, with the declaring fixture as its positive control.

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

⚠ **NO SHIPPED PROFILE DECLARES IT, so today this is a capability rather than a deployment.**
`ignite/config/spawn-profiles.yaml` is the live daemon's armed config; declaring the slot on a
shipped profile changes that profile's resolved argv for every daemon spawn, which task 7.42's
byte-unchanged criterion (re-asserted at 7.87) puts outside this row's authority. The conductor-lane
`cli-*` family the flag belonged on was retired by `r-seats-only-architecture` and never re-created.
Both facts are tripwired in `probe-extra-dir-slot.js` (checks `4` and `4-GAP`).

⚠ **opencode is the documented exception, not an omission.** Its launch root **is** the
work-target (`opencode run` resolves against the launch directory; the profiles pin no `--dir`), so
there is no add-dir split to express and `{extra_dir}` is **inapplicable** to that harness. Its
confinement is the launch root itself.

## ⚠ What this lane does NOT give you — read before assuming coverage

**No `(model, variant)` pair maps to a profile any more.** `launch_profile` is RETIRED (owner ruling
2026-08-11) and the 11 recorded values are gone from the manifests. Every elected pair dispatches
from its **package manual**; any profile this lane resolves is one the conductor NAMED itself.

**Every shipped profile is a DAEMON SEAT profile, and its argv is not a manual command line.** The
roster is 14 seat profiles (`r-seats-only-architecture`): the argvs carry `--session-id
{session_ref}` (assigned by the spawn path), a `--settings` path absolute on the daemon host,
`workdir_root: .rbtv/goals`, and a posture (`bypassPermissions`, `danger-full-access`) that is only
bounded **inside the bwrap seat cage** — which this lane does not resolve and a manual dispatch does
not apply. ⇒ Resolving one hands you the DAEMON's command, not yours.

**What is honestly left, then, is the MECHANISM:** name a profile → argv + binary, effort translated
into that harness's dialect, the work-target substituted through `{extra_dir}` where declared, the
pinned flags checked against the live `--help`, and the two add-dir refusals riding along. It is
exercised end-to-end on the probes' fixtures and is the ready seam for a conductor-lane profile
family if one is ever authored. **Until then no shipped profile is an honest subject for a manual
dispatch, and the pinned-flag gate for a real dispatch is run from that worker's delta Pre-flight —
as `routing.md` §4 has always said for a pair without a profile, which is now every pair.**

Two live gaps in the shared resolver remain, both FILED rather than worked around, both tripwired in
the probes so they fail the day they are fixed:

- **`G-270`** — a profile with no effort dial that does not declare `effort: { inert: true }` makes
  the resolver refuse every effort-bearing dispatch, and routing sets an effort for *every*
  dispatch. Proven on the `fx-no-dial` fixture (check `4-NO-DIAL`); a live profile that forgets the
  declaration is a config defect, and the shipped roster now declares one or the other throughout.
- **`G-271`** — `opencode run --help` writes to stderr and exits 0; the shared `readHelp` merges
  stderr only in its catch branch (non-zero exit), so a clean-exit stderr help reads as empty.

## Probes

```
node orchestration/capabilities/dispatch-resolve/probes/probe-dispatch-resolve.js
node orchestration/capabilities/dispatch-resolve/probes/probe-extra-dir-slot.js
```

Both are run DIRECTLY: `ignite/deploy/probe-suite.js` enumerates `ignite/` only, so an
orchestration-module probe is outside the runner's reach.

`probe-dispatch-resolve` — 21 checks, exit 0/1, GREEN 2026-08-11 (Windows box) after the retirement
repoint. The committed `probe-dispatch-resolve.out` beside it is the pre-repoint VPS capture and is
**stale** — regenerating it belongs to the next VPS run, not to a Windows box.

⚠ **REPOINTED 2026-08-10, and the shape changed with it.** It used to pin four profile names the
shipped config no longer carries (`claude-seat`, `claude-sonnet-tools`, `codex-git-write`,
`opencode-sakana` — `r-seats-only-architecture` retired all four and re-rostered the file to 14),
so 11 of 19 checks failed at their PRECONDITIONS before any bound was exercised and the verdict
carried no information. The lane's own bounds now run against a **fixture this probe writes**, the
sibling `probe-extra-dir-slot` pattern, so a roster change cannot strand them again; four `LIVE-*`
checks carry what is genuinely a statement about the shipped tree, asserted as relationships rather
than counts.

⚠ **REPOINTED AGAIN 2026-08-11 by the owner ruling.** `LIVE-2` and `LIVE-3` used to pin the DEFECT
state — "the deny-list refuses all 14" and "all 11 `launch_profile` values dangle". The ruling closed
both by REMOVAL, so each now pins the RETIRED state and fails if it creeps back:

- `LIVE-2` — every shipped profile still carries the shared cage's `SeatBinds` (asserted as the
  precondition), **none is refused**, and neither `assertNoSeatBinds` nor `E_SEATBINDS_PROFILE` is
  on the lane surface.
- `LIVE-3` — **no** manifest records a `launch_profile` (8 manifests scanned; the scan count is
  asserted so a zero-file read cannot print the same green). Mutation-verified 2026-08-11: adding one
  value back turns it FAIL (20/1), removed and re-verified green (21/0) in the same sitting.

§1 changed with them: `1-NO-DENYLIST` and `1-NO-CAGE-IN-ARGV` replace the old deny-list RED/GREEN
pair — the SeatBinds-declaring fixture now RESOLVES, and nothing of its bind template reaches the
argv or the result.

`probe-extra-dir-slot` — task **7.87 criterion 4**: 10 checks, exit 0/1, GREEN 2026-08-10. It runs
against a **fixture** config (the live daemon's armed config must not gain an argv-changing row on
this row's authority) and asserts the shipped config is untouched in the same run. Every leg is
two-directional, and the injection itself is **mutation-verified**: neutering `resolveExtraDirSlot`
to return the caller's slots unchanged turns checks `2` and `2-DOOR` FAIL (`E_MISSING_KEY`, and the
smuggled relative value reaching argv). Source restored and re-verified green in the same sitting.

**Every refusal is exercised in BOTH directions**, because *"it passed everywhere"* and *"it cannot
fail anywhere"* print the same thing (`bars.md` 11). The probe also asserts its own preconditions
(the bare load really refuses; `fx-seat` really declares `SeatBinds`; `LIVE-3` really read some
manifests) — an absence asserted over an empty set proves nothing.

**Mutation-verified 2026-07-28, re-verified 2026-08-10 after the repoint and 2026-08-11 after the
retirement**, because a green probe is not evidence that it discriminates: neutering the add-dir
guard turned `2a-RED` and `2b-RED` FAIL (19/2); re-adding one `launch_profile` value to a manifest
turned `LIVE-3` FAIL (20/1). Both sources restored and re-verified green (21/0) in the same sitting.
