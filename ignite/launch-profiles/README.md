# `launch-profiles/` — the ONE shared launch-profile resolver

The single policy point through which every launch resolves a **launch profile** (the KG term:
a named, config-pinned command-template set; the only unit a caller may select, by NAME).

Built by task 7.42. Governing records: registry `decisions.md#d-profile-source-unification`,
DEC-1 § Shared profile source, CMP-6 § Interface (1), CMP-9.

## Why it exists

`#d-sub-agent-standing-lane` (3) made the launch profiles ONE shared config file. That was not
enough: **"a second interpreter of the one file is the same drift as a second file."** So
resolution, slot validation, the carriage vocabulary, the workdir guard and the pinned-flag
pre-flight live in ONE module that requires **nothing under `server/`** — usable from a CLI, a
skill, or a test with no daemon in the picture.

## The three consumers

| # | Consumer | State |
|---|----------|-------|
| 1 | the daemon's spawn path (`server/spawn/config.js`, a thin adapter over this) | **LIVE** |
| 2 | the attached dispatch capability | task **7.43** — NOT BUILT |
| 3 | the orchestration conductor's CLI-worker dispatch | task **7.54** — NOT BUILT |

**Shipping with one live consumer is 7.42's correct outcome, not an unfinished one.** Stated
plainly so no reader infers more completeness than exists.

⚠ **The live consumer uses the EXTRACTED parts, not the whole surface.** The daemon calls
`loadConfig`, `resolveTemplateSlots`, `resolveWorkdir`, `resolveWorkspaceRoot`, `sessionsRootFor`
— the functions that moved out of `config.js`. It does **not** call `resolveProfile()`: the daemon
does its own profile lookup in `spawn.js`, and rerouting it would change live spawn behaviour,
which 7.42's own criterion forbids. So half selection, the effort slot and the raw-flag bound have
**zero live consumers today** and are exercised only by this module's probe. That is the honest
state, not a gap being hidden.

## What a caller may supply — and may not

A caller supplies exactly three things: the profile **NAME**, an **effort level** in the abstract
vocabulary, and values for **DECLARED SLOTS**. It supplies no argv, no flags, and no half.

| Bound | How it is enforced |
|-------|--------------------|
| Undeclared slot keys | `E_RAW_FLAG` — a caller cannot invent a key to smuggle a flag |
| A value becoming its own argv element | **arity is ASSERTED** after resolution, not documented |
| Choosing the half | impossible — `detectHostCapability()` takes no argument |
| An unknown effort level | `E_UNKNOWN_EFFORT` (closed vocabulary `low\|medium\|high\|max`) |

"Rejects raw flags" is **structural**, not a blocklist. Rejecting strings starting with `-` would
be a losing game over caller text. The real guarantee is that no code path pushes a caller-supplied
string onto argv as its own element — values only fill positions the profile already wrote.

## Profile shape (ruled)

- **Identity bakes harness + model** (+ permission posture where one pair needs two shapes).
  Picking the variant IS picking the profile.
- **Effort is NOT baked** — a per-dispatch slot in the abstract vocabulary, translated by the
  profile's own table (claude `effort`, codex `thinking`). A no-dial harness declares
  `effort: { inert: true }`; a caller's level is then accepted and reported back as
  `effortInert: true` — **stated, never silently dropped**.
- **Caged / portable halves** over one shared core. The resolver picks the half from the HOST's
  detected containment capability. A profile with **no portable half fails closed**
  (`E_NO_PORTABLE_HALF`) on a cage-less host.

  The hazard that shape encodes, from the ruling: `codex-git-write` disables codex's OWN sandbox
  because bwrap covers it. Reused on a cage-less desktop, a "fall back to the caged half" resolver
  would run it with no walls at all — and it would look like a normal run.

## Pinned-flag pre-flight

`preflightPinnedFlags()` verifies every flag a profile pins against the installed CLI's **live
`--help`** before dispatch — orchestration's validated practice, which the daemon lacked.
`E_PINNED_FLAG_ABSENT` (the flag is gone) is deliberately distinct from `E_PREFLIGHT_UNAVAILABLE`
(could not look): collapsing them would let an unrunnable binary read as a clean bill of health.

⚠ **It is exported but NOT wired into the daemon's spawn path** — adding a fork-and-parse to every
spawn would change live daemon behaviour in the same change that moved the module. Wiring is the
consumers' act (7.43 / 7.54) or a follow-on.

**Measured against the really-installed CLIs (2026-07-27), which found two defects in the
pre-flight itself before any consumer wired it:**

| profile | result |
|---------|--------|
| `claude-sonnet-tools` | VERIFIED — `-p --model --output-format --verbose --allowedTools --effort` all present |
| `codex-git-write` | VERIFIED — `--cd --sandbox -c --json` (needed the subcommand fix) |
| `opencode-sakana` | `E_PREFLIGHT_UNAVAILABLE(empty-help)` — see below |

1. **Help is per-SUBCOMMAND.** `--json` is on `codex exec --help` and absent from `codex --help`.
   Asking the top-level binary refused 2 of the 3 real profiles — a bar that fires on valid input
   is worse than no bar, because the refusal looks authoritative.
2. **An empty help is "could not look", never "the flag is gone."** `opencode run --help` writes
   ZERO BYTES to a pipe (it renders only to a TTY). The first cut accepted that empty string as
   help, found no flags in it, and raised `E_PINNED_FLAG_ABSENT` — the exact confusion these two
   codes exist to prevent, inside the function that defines them. The guard was on the throw path
   only; a command that *succeeded* with no output walked past it.

   **Consequence a consumer must know:** the pre-flight cannot verify `opencode` profiles on this
   host at all. It says so with a typed `E_PREFLIGHT_UNAVAILABLE` rather than passing them — an
   unverifiable profile is reported unverifiable, never waved through.

Both defects are covered by probe legs 14b/14c, each mutation-tested to go red when its fix is
reverted.

## Known residuals — disclosed, not hidden

1. **`DAEMON_ONLY_ROOT_KEYS` is duplicated** with `server/index.js:42`. The profile surface ignores
   those namespaces so an outside consumer can load the committed file; index.js strips them.
   Convergence is a one-line edit to live daemon **boot** code and was not smuggled into this task.
2. **`scanPath` is duplicated** with `server/spawn/bwrap.js`. The shared module may not import from
   `server/`; the fix is bwrap.js consuming this one when the seat cage is adopted (built, not
   applied — `G-124`).
3. **⚠ PRESENCE IS NOT CAPABILITY — the highest-severity residual, and it fails UNSAFE.**
   `detectHostCapability()` decides the half from the mere PRESENCE of a `bwrap` binary, never
   from whether it WORKS. A host where bwrap is installed but user namespaces are disabled detects
   `caged`, resolves the caged half, and **fails at exec** — walking straight past the
   `E_NO_PORTABLE_HALF` refusal that exists precisely so a profile whose walls are missing never
   runs. 7.42 exercised present+working (this VPS) and absent+absent (the probe's child process);
   **present-but-broken is modelled by neither.** Reproduced with a stub `bwrap` that is executable
   and always fails: the detector still reports `caged`. Fix shape is a FUNCTIONAL probe (attempt a
   trivial namespace once, cache it), which costs a fork at resolution time and belongs with
   whoever wires `resolveProfile()` into a live consumer. Filed `G-148`.
4. **`spawn.js` reads `profile.exec` unguarded** (`:160`, `:487`), so a half-shaped profile in the
   shipped config would crash the daemon with a `TypeError` instead of a typed refusal. This is why
   no half-shaped profile ships in `config/spawn-profiles.yaml` — the probe uses a runtime temp
   fixture instead, which also keeps criterion 6 (no second profile file in the repo) true.

## Probe

```
node launch-profiles/probes/probe-launch-profiles.js
```

20 checks. Self-contained — requires only this module and node builtins. Its bars were
**mutation-tested**: breaking half selection, the raw-flag bound, the effort translation, and the
fail-closed branch each turns the intended leg red.
