<!-- TEST FIXTURE — NOT A REAL MODEL PACKAGE. -->
<!-- Exists solely to exercise render-manuals.py until the first real delta (kimi) lands at p3-4. -->
<!-- The leading-underscore folder name `_fixture` cannot collide with a real model id. -->
<!-- Kept (not deleted) so the done-gate cold verifier can re-exercise the render contract. -->
<!-- Safe to delete once two or more real model deltas exist. -->

# `_fixture` package delta (TEST FIXTURE)

This file fills the dispatch-wrapper template's INSERT points with minimal,
clearly-marked fixture content, plus the mandatory invocation section.

<!-- RENDER:DELTA model-binding-delta -->
**[FIXTURE] `_fixture` worker binding obligations**

- [FIXTURE] Do not write stray scratch files in the repo root.
- [FIXTURE] EDITED-FOR-CRITERION-B: this sentinel line was changed to prove the edit propagates to only this model's manual.
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**[FIXTURE] `_fixture` return surface:** the worker prints the five fields as its
final message; cited evidence files land on disk under the run's evidence folder.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
**[FIXTURE] Invocation shape** (placeholder — a real package documents the exact
command, flags, work-dir, prompt transport, exit codes, and resume support here):

```
fixture-cli --print --work-dir <repo-root> --prompt-file <prompt.md>
```

- [FIXTURE] Exit 0 = success; non-zero = inspect and recover.
- [FIXTURE] Prompt transport: arg or stdin.
<!-- RENDER:DELTA-END invocation -->
