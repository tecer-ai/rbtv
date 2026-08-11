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
| 2 | the sub-agent dispatch capability | task **7.43** — built, then **RETIRED** per `r-seats-only-architecture` (2026-08-06): the daemon's sub-agent lane is gone; delegation is seat-side |
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

  The hazard that shape encodes, from the ruling: the codex profile (`codex-gpt-5-5`) disables codex's OWN sandbox
  because bwrap covers it. Reused on a cage-less desktop, a "fall back to the caged half" resolver
  would run it with no walls at all — and it would look like a normal run.

## `resume:` — the second command template (r-chat-chain-resumes-session, owner 2026-08-07)

A launch profile has always been *defined* as carrying exec **and resume** templates; nothing
declared one until this ruling. `resume:` is OPTIONAL and has the SAME shape and the SAME
validator as `exec:` (argv + `prompt: stdin`), plus one bound: its argv MUST carry the
`{session_ref}` slot, or it would resume no particular session (`E_MISSING_KEY`). A profile
without a `resume:` block simply never resumes — that is the ruling's declared fallback, not a gap.

Paired with it, a fourth `session_ref.source`: **`assigned`**. The three older sources READ the ref
back out of the worker; `assigned` means the launcher MINTS it and pins it into the command line
through the same `{session_ref}` slot (claude: `--session-id {session_ref}`), so the ref is on
record before the worker emits a byte and survives a turn that never emits one. Measured on claude
2.1.224 (2026-08-07): `-p --session-id <uuid>` reports that exact uuid as its own `session_id`, and
`-p --resume <uuid>` keeps both the id and the context (second-turn cache_creation 8843 → 92
tokens).

⚠ **A caller of `resolveProfile()` must now supply a `session_ref` slot value for the shipped
claude profiles** — a declared slot with no value is `E_MISSING_KEY` by construction, because this
module never emits a literal `{slot}` onto a command line. The daemon's own path
(`server/spawn/spawn.js` `composeArgv`) supplies it: the predecessor's ref on a resume, this
session's id on a fresh launch.

## The declared slot vocabulary — `{extra_dir}` (task 7.87)

`CLOSED_SLOTS` is `{workdir} {prompt_file} {session_ref} {extra_dir}`, enforced at config **LOAD**
with `E_UNKNOWN_SLOT`. A profile may write only these; a caller may fill only the ones the profile
it names actually wrote (`E_RAW_FLAG` otherwise).

`{extra_dir}` was added because the **G1 confinement split** needs TWO path values and the
vocabulary expressed ONE. G1 (orchestration `cards/dispatch-wrapper.md` row G1): launch a CLI worker
with its guidance-root = the orchestrator root, and pass the actual **work target** separately via
the harness's add-dir flag. `{workdir}` is the guidance root; `{extra_dir}` is the work target — so
a profile can now write `--add-dir {extra_dir}` itself instead of a conductor hand-composing that
flag. The rule was earned by the `a3e217d` incident: a bare kimi self-commit swept 5 foreign files
because its guidance-root was the unmirrored nested repo.

| Slot | Is | Guarded by |
|------|----|------------|
| `{workdir}` | the launch / guidance root | `resolveWorkdir` — must sit inside the profile's `workdir_root` (`E_WORKDIR_ESCAPE`) |
| `{extra_dir}` | the work target, deliberately OUTSIDE that root | **nothing in this module** — see below |

⚠ **`{extra_dir}` is NOT workdir-guarded, by definition.** A path whose whole purpose is to name a
target outside the guidance root cannot be contained by that root. The structural bound still holds
— the value fills a position the PROFILE wrote and can never become its own argv element (the arity
assertion in `resolveProfile`) — but **which** directory is handed in is the caller's decision and
the caller's confinement to make.

**Additive, and the daemon is byte-unchanged.** No shipped profile declares `{extra_dir}`, so every
profile in `config/spawn-profiles.yaml` resolves the identical argv before and after the widening
(measured over all 14, task 7.42's criterion re-asserted). Probe legs 16 / 17 / 17b cover it, and
17 is the discriminating one: it **plants an unknown slot** and asserts the `E_UNKNOWN_SLOT` refusal
still fires — proving the new slot being accepted means *the vocabulary grew by one*, not *the
vocabulary stopped being closed*.

🔧 **Not yet consumed.** `orchestration/capabilities/dispatch-resolve/` still hand-composes the
add-dir flag (its `assertWorkTarget` makes an absent work-target loud but does not resolve it
through a slot), and no shipped profile declares `{extra_dir}` yet. Making the split resolve
end-to-end is the consumer's edit plus a profile edit, both outside this module.

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

(Profile names below are the live r-seats-only-architecture roster, 2026-08-06 — the measurement
was made against the retired same-harness predecessors and the pinned flags are unchanged.)

| profile | result |
|---------|--------|
| `claude-fable` / `claude-opus` / `claude-sonnet` / `claude-haiku` | VERIFIED — `-p --model --output-format --verbose --effort` all present |
| `codex-gpt-5-5` | VERIFIED — `--cd --sandbox -c --json` (needed the subcommand fix) |
| `opencode-*` (glm-5-2, deepseek-flash, deepseek-pro, fugu, fugu-ultra, gemini-flash, gemini-pro) | `E_PREFLIGHT_UNAVAILABLE(empty-help)` — see below |

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

23 checks. Self-contained — requires only this module and node builtins. Its bars were
**mutation-tested**: breaking half selection, the raw-flag bound, the effort translation, and the
fail-closed branch each turns the intended leg red.

## ⚠ ONE argv element this module does not author (owner ruling 2026-08-07)

`server/spawn/spawn.js` `composeArgv` appends `--append-system-prompt-file <workdir>/seat.md`
after slot resolution — `claude` profiles only, and **only when that file exists**. It is
disclosed here because it is the single exception to "the profile writes the command line", and
the reason it cannot live in a profile argv is measured, not stylistic: `claude
--append-system-prompt-file <missing>` prints *"Append system prompt file not found"* and runs
NOTHING (2.1.224), so an unconditional flag would kill every spawn at a seat sitting between
scaffold and materialize. The condition needs the filesystem; this resolver is deliberately
filesystem-free apart from its workdir guard.

WHY the flag exists at all: the auto-injected CLAUDE.md chain does reach a seat session, but
`seat.md` sat behind it as a POINTER — a voluntary tool call the seat had to make before its
first word, which a one-turn headless sitting does not make (measured on the channel master,
2026-08-07: the "read seat.md and FOLLOW it" sentence was in context and was skipped; the seat
answered as a generic assistant). The descriptor now rides the system prompt, which needs no
compliance to arrive.

Guarded by `server/spawn/probes/probe-flag-injection.js` — present / absent / non-claude, each
mutation-tested (3 mutations, 3 red). Folding it in properly means a profile-level opt-in key
with its own validation; worth doing when a second harness gains a MEASURED equivalent, never
on a guessed one.

## Effort is a numeric rung, 1..N, per profile (2026-08-11)

Owner rulings `d-0811lp-effort-numeric-per-profile` and `d-0811lp-effort-lane-build-now`
(run `exec-0811-live-proofs`). **This replaced the four-level abstract vocabulary**
(`low|medium|high|max` + a per-profile `values:` map) that task 7.42 shipped.

| | Before (7.42) | Now |
|---|---|---|
| what a caller names | one of four abstract levels, closed and cross-harness | an **integer rung**, 1 = lowest reasoning, N = highest |
| what a profile declares | `effort: { dialect, values: {low:…, medium:…, high:…, max:…}, argv }` | `effort: { dialect, rungs: [ … ordered … ], argv }` |
| how wide the ladder is | the same four for everyone | **each profile's own N** |
| an unknown request | a level outside the closed set | a rung outside **that profile's** 1..N, refused naming the range |
| a harness with no dial | `effort: { inert: true }` — accept and report | unchanged (G-270) |
| no effort at all | harness default | unchanged |

**Why.** A closed cross-harness vocabulary can only be as wide as its narrowest member, or it
mistranslates — and it did both: claude's real dial is five rungs, so `xhigh` was unspellable
through the four-level table, and codex's is three, so `max` was silently collapsed onto `high`.
Per-profile ladders are neither. The rung number is the ONLY thing shared across harnesses; every
spelling is the profile's own.

**The ladders in the shipped config:** claude (fable/opus/sonnet) 1..5
`low·medium·high·xhigh·max`; codex 1..3 `low·medium·high` (carried as
`-c model_reasoning_effort=`); kimi 1..2 `--no-thinking·--thinking` (the rung IS the flag);
claude-haiku and the whole `opencode-*` set inert, measured.

**`resolveEffort` is exported, and that is the point.** `server/spawn/spawn.js#composeArgv` calls
it — the daemon composes its own argv (G-144 still stands, half selection is still 7.43/7.54) but
does NOT own a second reading of the `effort:` table. One interpreter, two callers.
