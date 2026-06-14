# Spec — Exemplar-Screenshot Capture Capability

> Behavior source of truth for the screenshot-capture capability. The capability's usage doc and the capability registry reference this spec for the behavioral floor — they never restate it. The capability lives at `{rbtv_path}/studio/capabilities/screenshot-capture/` and is registered in the capability registry. It is the visual layer of the reference library.

## Goal

The owner (or a worker on the owner's behalf) can run the capture capability with one or more URLs and have exemplar screenshots land in the project's reference set (`exemplars/`) with a manifest row each — ready for taste-file annotation.

## Context Snapshot

- **Destination:** the workspace-owned reference set — the project's `<reference_set>/exemplars/` path, resolved at runtime (per `{rbtv_path}/studio/standards/reference-set-contract.md`). Output goes to the reference set, NOT the playwright skill's internal screenshots folder (that folder's discipline — delete after use — applies to throwaway QA shots, not curated exemplars).
- **Manifest row contract:** filename · source URL · capture date · viewport · full-page vs section.
- **Infra:** the module's browser-automation workflow (the playwright-CLI skill); real rendering, real viewports.

## Behavior Specification

| # | When (input / gesture) | Then (observable result) |
|---|------------------------|--------------------------|
| 1 | Invocation with URL(s) + a target reference-set path | Full-page screenshots land in `exemplars/`; one manifest row appended per capture |
| 2 | A viewport is specified (e.g. 1440×900) | The capture is rendered and bounded at that viewport; the manifest records it |
| 3 | A capture targets a section (selector/region) | Only that region is captured; manifest marks it `section` |
| 4 | Re-capturing an already-captured URL | The new file gets a versioned name — NEVER a silent overwrite of a curated exemplar |

## Edge Cases & Error Behavior

- **URL unreachable** → non-zero exit + reason; no manifest row written.
- **Consent/cookie overlays** → best-effort dismissal; if the overlay survives, the capture proceeds and the manifest row flags `overlay-present` so the owner knows to re-curate manually.
- **Extremely long pages** → full-page capture capped at a sane height; cap noted in the manifest row.

## Out of Scope

Curation and taste judgment (the owner annotates the taste file) · token extraction · motion extraction (`subtle-refs`) · editing or retouching captures.

## Test Plan

| # | Criterion (owner-observable) | Gesture to exercise it | Expected observable result | Evidence captured |
|---|------------------------------|------------------------|----------------------------|-------------------|
| 1 | Real capture lands in the reference set | Run un-piped against 2 real public URLs targeting the real reference-set path | Exit 0; image files exist in `exemplars/`; MEASURED dimensions match the requested viewport | The captured files + a dimension-check output |
| 2 | Manifest is complete and true | Open the manifest after the run | One row per capture with filename, URL, date, viewport, mode — matching the files on disk | Manifest diff |
| 3 | No silent overwrite | Re-run against the same URL | A second, versioned file appears; the first is untouched (hash-identical) | Directory listing + hashes |
| 4 | Dead URL fails loud | Run against a dead URL | Non-zero exit; no file, no manifest row | Terminal capture |

> Every criterion obeys the **Fidelity floor** + **Evidence plausibility** rules.

**Fidelity floor for every criterion:** the real application running whole against real pages and the real reference-set path; CLI exit codes read un-piped; evidence files written during the exercise. A genuinely undriveable criterion is marked `unexercisable` with the concrete blocker, never silently skipped.

**Evidence plausibility:** metrics must be physically plausible; impossible timings are auto-reject + rerun.

## Return Expectations

Executor reports: files changed · validation commands + un-piped exit codes + skips with reasons · local commit hash if committed · concerns · blockers. Report is a hint; repo state is the truth.
