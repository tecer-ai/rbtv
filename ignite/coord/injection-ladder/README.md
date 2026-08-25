# `injection-ladder/` — THE one per-harness injection ladder

The single place that answers **which METHOD drives each harness**: an ordered preference of
injection rungs, tried best-first — **headless one-shot → hooks → keystroke**.

Built by task 7.45. Governing records: `CMP-9` (`sd-graph show CMP-9`), registry
`decisions.md#d-injection-ladder-shared`, `decisions.md#d-profile-source-unification`.

## What it answers, and what it deliberately does not

`CMP-9` § Interface (2) draws the line and this module holds it:

> It answers ONE question — **the METHOD**. Given a harness, which injection rung is available and
> preferred. **It never answers what the command line is**; that is the ONE shared launch-profile
> resolver's answer (`ignite/launch-profiles/`, task 7.42, DEC-1 § Shared profile source), and the
> two are consumed together — the caller names a profile and walks this ladder for that profile's
> harness.

It **exposes no command, holds no state, spawns nothing, and writes nothing.** That last clause is
why `hooksConfigFor()` returns a *descriptor* of files and performs no I/O: the daemon adapter does
the writing (`server/spawn/harness-config.js`).

The rungs' concrete surfaces are **owned elsewhere and cited, never restated** (§ Interface (3)):
keystroke is `tmux send-keys` into the seat's pane (`CMP-19` § Interface (2)); headless is the
harness's own one-shot invocation; hooks reaches the harness through its harness config.

## The three consumers

| # | Consumer | State |
|---|----------|-------|
| 1 | the daemon's spawn path (`server/spawn/harness-config.js`, a thin adapter over this) | **LIVE** |
| 2 | the attached dispatch surface — the rbtv CLI run verb | task **7.44** — NOT BUILT. Its former other half, the sub-agent dispatch capability (7.43), is **RETIRED** per `r-seats-only-architecture` (2026-08-06): the daemon's sub-agent lane is gone; delegation is seat-side |
| 3 | the orchestration conductor's CLI-worker dispatch | task **7.54** — NOT BUILT |

⚠ **The unbuilt consumers carry `_Depends:_ 7.42, 7.45` in their own task rows.** So this
module ships with one live consumer not because the work stopped short, but because **the other two
cannot be built before it**. The same disclosure 7.42 made for `resolveProfile()`, for the same
structural reason. Stated plainly so no reader infers more completeness than exists.

## The walk — and the one thing a caller must never do

```js
const { resolveRung, harnessOf } = require('../injection-ladder');

resolveRung(harnessOf(profile), { phase: 'launch', needResumable: true });
//  -> { harness, rung, phase, entry, skipped[] }   or a typed LadderError
```

**Never pass the rung in.** `resolveRung()` takes the *situation* — harness, phase, whether the
session must be reachable again, host capability — and walks. A caller that hands the ladder the
rung it wanted has exercised everything except the selection; that is
`p-green-harness-over-a-broken-mechanism`, and a check written over such a call cannot fail.

| Input | Meaning |
|-------|---------|
| `phase` | `launch` (start a session) or `inject` (reach an already-live one). `headless`/`hooks` are launch-only by construction; `keystroke` is inject-only — you cannot type into a session that does not exist yet. |
| `needResumable` | the caller must reach this session **again** after the first turn. A rung satisfies it only by **declaring** it. |
| `hostSupports` | per-rung host capability, e.g. `{ keystroke: false }` with no tmux. Absent keys mean supported. |

Exhausting the ladder is `E_NO_RUNG_AVAILABLE` carrying **every rung it passed and why** — never a
silent fallback. An unknown harness is `E_UNKNOWN_HARNESS`: the ladder does not guess the shape of a
harness it has not seen driven, because guessing would put unverified launch knowledge back into the
system this module exists to hold in one place.

## The per-harness table

Every entry carries a `basis` citing where the fact was **measured**, never prose asserting it.

| harness | headless | hooks | keystroke |
|---------|----------|-------|-----------|
| `claude` | `claude -p`, resumable by session id | **enforceable** — `.claude/settings.json` `permissions.additionalDirectories` | yes |
| `codex` | `codex exec`, resumable | advisory only — `.codex/config.toml`; the profile runs `--sandbox danger-full-access`, so codex's own sandbox is off | yes |
| `opencode` | `opencode run` — ⚠ **ONE-SHOT, not resumable** | advisory only, and **strict-validating**: an unrecognized key in `opencode.json` kills the session at startup, so the advisory rides a sidecar file | yes |
| `kimi` | `kimi -p`, resumable — the run prints its own `kimi -r <id>` line | **UNAVAILABLE — not measured.** `--config`/`--config-file` exist (`~/.kimi/config.toml`), so a rung may well exist; no key there has been verified to restrain anything, and this table declares rather than guesses | yes |

⚠ **An unavailable hooks rung is a REAL branch, not a gap to fall through.** `hooksConfigFor`
returns an empty descriptor for any harness whose `hooks` rung is unavailable. Before 2026-08-07 the
tail of that function was a bare fallthrough that ASSUMED opencode, so the first harness added to
the table would have had `opencode.json` planned into its seat dir — and opencode strict-validates
that file, so the contamination would have been a startup kill. Guarded by the probe's leg **8b**,
which asserts the hooks-less harness plans zero files *and* that opencode still plans both of its
own (a discrimination, not a function that stopped planning for everyone).

⚠ **Naming a harness also gives it its credential bind.** `harnessOf` returning `null` meant a kimi
seat got the `default: return []` arm of `server/spawn/bwrap.js` `harnessStateBinds` — no state bound
back over the throwaway HOME tmpfs, so a caged kimi seat had no credentials at all. `~/.kimi/` (the
one dir: `config.toml`, `credentials`, `device_id`, `kimi.json`, `logs` — measured; no
`~/.config/kimi`, `~/.local/share/kimi` or `~/.cache/kimi` exists) lands in that table WITH the row
here, never after it.

⚠ **opencode's one-shot rung is the difference that makes this a walk and not a lookup.** The seat
executes its prompt and **exits**, so it can never be woken; a wake aimed at its pane afterwards
types into a bare shell. Live-verified (`G-13`), and the failure it originally caused was silent —
the pre-`G-13` command form exited 0 having run nothing, so any check that only asserted the flag
was present read green.

## Verified against the REALLY installed CLIs (2026-07-28, ignite VPS)

The table's rung claims are transcribed from measured sources; they were then re-checked here
against the binaries actually on this box, because `G-145`'s lesson is that a per-harness claim
read off prose — or off the WRONG help — refuses valid input while looking authoritative.

| harness | installed | headless rung claim | result |
|---------|-----------|---------------------|--------|
| `claude` | 2.1.220 | `claude -p`, resumable by session id | **VERIFIED** — `-p, --print`, `--resume`, `--session-id`, `--model` all present |
| `codex` | codex-cli 0.144.5 | `codex exec`, resumable | **VERIFIED** — `exec` subcommand present; `resume`, `--model`, `--sandbox`, `--cd` present on `codex exec --help` |
| `opencode` | 1.17.18 | `opencode run`, **one-shot** | **UNKNOWN by help — and that is reported, not waved through** |
| `kimi` | 1.48.0 | *(not in this table)* | installed on this box but carries no measured rung set here — `E_UNKNOWN_HARNESS`, see residual 3 |

⚠ **`opencode run --help` writes ZERO BYTES into a pipe on this host, and so does `opencode --help`**
(measured: `help_bytes=0` for both) — it renders only to a TTY. That is `E_PREFLIGHT_UNAVAILABLE`'s
whole reason for existing, and it is reproduced here independently of 7.42's finding. **An empty help
is "could not look", never "the flag is gone."** opencode's rung basis therefore rests on LIVE
verification (`G-13`, a real dispatch on deepseek and glm-5.2) rather than on a help scrape, which is
the correct evidence class for a harness whose help cannot be read.

⚠ **Version drift, found in passing and NOT this task's to fix:** the box runs **codex-cli 0.144.5**
while a now-retired models-tree delta (Historical: `orchestration/models/codex-cli/delta.md`) pinned
its flag verification to **0.137.0**. The flags this ladder relies on are present at 0.144.5
(checked above), so nothing here is broken — live invocation source is the cast catalog / `cast.md`.
Recorded so it is not re-discovered.

## Probe

```
node injection-ladder/probes/probe-injection-ladder.js
```

12 legs. **Self-contained** — requires only this module and node builtins, with no daemon, no heart
store and no config file. That is the assertion, not a convenience: `CMP-9` dropped the
`uses → server` edge, and a probe that needed the daemon to exercise the ladder would disprove the
property the module exists to have. Leg 9 asserts it mechanically (no module file requires anything
under `server/`).

**Every leg was mutation-tested — 10 mutations, 10 red.** The sweep found one real hole in the probe
itself, which is recorded here because the hole is the more useful artifact than the fix:

> Making `keystroke` launch-eligible left **all legs green**. Every launch case already resolves at
> a higher rung, so nothing ever observed the change — the launch-only/inject-only property was
> load-bearing and asserted nowhere. Leg **6b** now asserts the phase table directly *and*
> behaviourally (with both launch rungs barred, the walk must REFUSE rather than reach keystroke).

A second near-miss is recorded in the code at the walk: writing the resumability test as
`resumable === false` instead of `!== true` falls through opencode's one-shot rung onto `hooks` and
returns it confidently — and hooks cannot reach a live session at all. Leg 5b asserts the refusal
rather than merely "not headless", which is what makes that mutation visible.

## The daemon seam, and how it was proved

`server/spawn/harness-config.js` is now a **thin adapter**: the per-harness knowledge moved here; the
filesystem writes and the daemon's log line stayed there. `harnessOf` is re-exported rather than
redefined, so its other call sites in `spawn.js` are untouched. (A fourth site in `pty-host.js` was
cited here until task 7.29 deleted that module; the line numbers are the original citation's and
are not re-derived — see the file itself, which is the source of truth for where they are now.)

- **Byte-equivalence** old-vs-new over 10 cases (all three harnesses × editable-path shapes, plus
  four null-harness cases), comparing the returned object *and* the full on-disk tree — paths, bytes
  and modes. `RESULT: EQUIVALENT`. The comparison was itself mutation-tested: 6 mutations, 6 red.
- **15 of 15 daemon spawn probes green** after the change, each with an `ended:` stamp.
- **10 of those 15 go RED when the shared ladder is mutated** — so the daemon genuinely spawns
  through this module and the probes cover the seam. The 5 that stay green
  (`carriage-vocab`, `profile-halves-refusal`, `seat-cage`, `seat-identity`, `peer-identity`) are
  config-load and identity probes that never reach the spawn path; that is expected, and it is
  stated rather than left for a reader to assume coverage that does not exist.

## Known residuals — disclosed, not hidden

1. **⚠ This is an INTERIM home against a ruled destination that does not exist.** `CMP-9` §
   Interface (5) rules the ladder's preset **data** into the model-and-harness catalog at the
   runtime root's `config/` (`models.json` + `harnesses.json`, `CMP-1` § Model-and-harness catalog;
   owner-ruled `decisions.md#d-elist-model-catalog-relocation`, pinned by
   `#d-cmp9-preset-data-home`). **That relocation is unbuilt and carries no task** — measured
   2026-07-28: grepping the whole Phase-7 core-build tasks file for those anchors and for
   `harnesses.json` returns **zero hits**. This module therefore sits beside 7.42's
   `ignite/launch-profiles/` precedent and **says so**, rather than quietly becoming the
   destination. Inventing the runtime-root catalog inside 7.45 would mint a structural convention
   by accident; the orphaned ruling is filed for routing instead.
2. **The repo still holds more than one per-harness method table, BY DESIGN at this task.**
    `orchestration/`'s cards remain and CALL `cast`. Model manifests/deltas retired with the models
    tree (2026-08-18). Historical: those files lived under `orchestration/models/`. Live roster is
    the cast catalog. `ignite/team-kit/coord.py`'s `harness_command()` is
    **`G-146`**, explicitly carved out of 7.45's scope. Neither was retired here — a grep made clean
    by deleting another task's work is a falsified criterion, not a met one. See § One copy below.
3. ~~**`kimi` is in the orchestration model catalog but NOT in this table.**~~ **CLOSED 2026-08-07**
   — kimi was driven through a consumer and added with a measured basis per rung (see the table
   above): headless verified live on kimi 1.48.0, hooks declared UNAVAILABLE-because-unmeasured
   rather than guessed, keystroke on the same CMP-19 citation the other three carry. Its credential
   bind landed in `harnessStateBinds` in the same change. What closing this residual exposed is
   recorded above and is the more useful artifact: naming a fourth harness was a latent
   cross-harness write, because the hooks descriptor's tail assumed the third one.
4. **The `hooks` rung is modelled as launch-only.** A harness that re-reads its config mid-session
   would be a fourth case this table does not carry. None of the three does today; if one gains it,
   `RUNG_PHASES.hooks` is where it changes, not a consumer.

## One copy — what this module holds, and what it deliberately left standing

Task 7.45's criterion 1 asks that exactly one copy of the per-harness method table exist in the
repo. **At the end of 7.45 that is not yet true, and the reason is in the task graph, not in the
work.** The carve-outs, each named with why:

| Copy | Why it stands |
|------|---------------|
| `ignite/injection-ladder/` | this module — the one home |
| `orchestration/skills/orchestrating/cards/` (call `cast`) | Cards remain and CALL `cast` / `cast route`. Historical: `orchestration/models/*/{manifest.yaml,delta.md}` retired with the tree 2026-08-18. |
| `ignite/team-kit/coord.py` `harness_command()` | **`G-146`**, explicitly out of 7.45's scope by the run leader's directive. Custody of that file is held elsewhere; it was neither read into this module nor edited. |
