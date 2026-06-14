# Spec — Image Generation Capability

> Behavior source of truth for the image-gen capability. The capability's usage doc and the capability registry reference this spec for the behavioral floor — they never restate it. The capability lives at `{rbtv_path}/studio/capabilities/image-gen/` and is registered in the capability registry.

## Goal

A worker (or the owner) can run the image-gen capability with a prompt and a target path and get an image file at that path — with the provider swappable by flag and new providers addable without touching the interface or its callers. Gemini is the first concrete provider.

## Context Snapshot

- **Interface shape:** deterministic CLI invocation (per the workspace deterministic-first policy), e.g. `python generate.py --prompt "..." --out path/img.png [--provider gemini] [--aspect 16:9]`. Exact flag names are the executor's call; the BEHAVIOR below is the contract.
- **Pluggability:** source-pluggable, multi-provider — one adapter module per provider behind a common interface; adding a provider = new adapter + registry row, ZERO changes to the interface or existing callers.
- **Credentials:** API key read from the OS environment first (e.g. `GEMINI_API_KEY`), falling back to the workspace env file convention. NEVER hardcoded, NEVER printed.
- **Registry:** the capability self-describes in `{rbtv_path}/studio/capabilities/registry.md` per the capability registry's invocation convention.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Invocation with `--prompt` and `--out`, no provider flag | Gemini generates; a valid image file lands at `--out`; exit 0 |
| 2 | `--provider {name}` given | The named adapter handles generation through the SAME interface |
| 3 | A new provider adapter file is added + registered | It is invocable by name with no edits to the interface or callers |
| 4 | `--out` extension implies format (png/jpg) | Output matches the requested format |
| 5 | Aspect/size flags given | Output dimensions honor them (within provider constraints, reported if coerced) |

## Edge Cases & Error Behavior

- **Missing API key** → non-zero exit + actionable message naming the missing env var; NO partial/empty file left at `--out`.
- **Provider error / rate limit** → non-zero exit; provider's reason surfaced on stderr; no fabricated fallback image.
- **Unknown provider name** → non-zero exit listing registered providers.
- **Unwritable `--out`** → fails BEFORE any API call is spent.

## Out of Scope

Prompt craft (the Designer's job) · image editing/refinement pipelines · cost tracking · provider quota management · authoring brand imagery rules.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | A real image generates via Gemini | Run the CLI un-piped with a real prompt + real `GEMINI_API_KEY` | Exit 0 (read off the un-piped process); file exists, >0 bytes, opens as a valid image with plausible dimensions (verified deterministically, e.g. via PIL) | Generated image + terminal capture |
| 2 | Missing-key failure is clean | Unset the key env var, run the same command | Non-zero exit; message names the env var; no file at `--out` | Terminal capture |
| 3 | Provider pluggability is real | Invoke with a second registered adapter (a deterministic fixture/echo adapter qualifies — it proves the seam; the real gesture stays the same CLI) | Same interface produces that adapter's output; zero interface/caller edits needed | Terminal capture + adapter diff |
| 4 | Format honored | Request `.png` and `.jpg` outputs | Files carry the correct format headers | The two files |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules: real application whole, un-piped exit codes for CLI, evidence files written during the exercise, physically-plausible metrics; undriveable criteria marked `unexercisable` with the blocker.

**Fidelity floor for every criterion:** the real application running whole, on real input; CLI criteria read exit codes off the UN-PIPED process. Evidence is a file on disk written DURING the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker, never silently skipped.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · local commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
