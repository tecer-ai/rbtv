---
id: review-plan
description: "Trial the draft plan once, tag findings blocking/non-blocking, revise only blocking, and ship the approval package"
---

<task-goal>
Trial the seeded draft plan once against its frozen milestone list and the six seat declarations, emit findings tagged blocking or non-blocking, revise only the blocking findings, and produce the review package a verifier can check.
</task-goal>

<scope>
- **Read:** the design and the facts brief; the draft plan; `planning/execution-contract.md` and, for a one-off plan, `planning/current/` (`manifest.csv`, the `seats/<seat>/` pairs, `bindings.json`); every artifact those name; on a verify FAIL relaunch, the FAIL body as the closed findings list.
- **Write:** `planning/review-package.md`.
</scope>

<done-contract>
Done criteria — all must hold:

- `planning/review-package.md` exists and its first line is exactly `REVIEW-PACKAGE`.
- The body carries a findings list, each entry tagged `blocking` or `non-blocking`, emitted exactly once — a second findings pass on the same run is a fail.
- Only findings tagged `blocking` were revised; every `non-blocking` finding remains, untouched, as accepted residue.
- The revised plan still carries every milestone id the design froze, unbroken.
- The approval package section names what the owner is being asked to bind: the plan artifacts, and that approval binds at a recorded git commit — never at a canvas. It names WHO records it and WHERE the verify stage reads it: the goal's `leader` commits `planning/` to the vault when it accepts this seat's row and writes the hash to `planning/bound-commit`. No planning seat records it: they run caged with `.git` masked.
- The draft's EXECUTION DECLARATION was trialed and is present and valid, or the finding is `blocking`. Valid means: an `execution-goal` matching `^[a-z0-9]+(-[a-z0-9]+)*$` (lowercase kebab-case, what the scaffold takes) and not `owner`; a `lane`; a `roster` of the plan's own seat ids with no duplicate; `workflow`+`sheet` present or explicitly declared one-off; a `contract-file` naming `planning/execution-contract.md`. An absent declaration, a name that is a path or a title, a roster naming a seat the plan does not detail, or a plan that says it "executes in place" are each `blocking` — approval BIRTHS a new goal and mints its roster, so a plan with no truthful declaration cannot be approved at all.
- The two artifacts the BIRTH consumes exist and are well-formed, or the finding is `blocking` — they are the draft's own parts, and the approving act writes nothing:
  - `planning/execution-contract.md` exists, carries NO frontmatter (`scaffold` writes the goal's own above it), and reads as the born goal's contract for a stranger — the owner's request restated plus a pointer to the plan artifacts at the bound commit. A contract that is a copy of the draft, or that assumes the reader has read the plan, is `blocking`. Do NOT assign this file to "the approving act", to the `leader`, or to any seat downstream of the draft: no such step exists, and a plan that assigns it there is `blocking`.
  - Where the declaration omits `workflow`, `planning/current/` carries `manifest.csv` (header `Seat/workflow,after,i/o,Modality`), one `seats/<seat>/` folder per manifest row holding a PROMPT (frontmatter `id:` + `<role>` + a `<permissions>` block) and a TASK (frontmatter `id:` + `<task-goal>`), and `bindings.json` casting every manifest seat with a `harness` and a `model`. A missing pair, a missing `<permissions>` block, an `after` member naming nothing in the manifest, a duplicate or catalog-shadowing `id:`, an `on-fail-relaunch` that is a boolean rather than a seat name, or an uncast seat is each `blocking` — every one of them is a refusal at the birth, i.e. after the owner has already approved.
- No milestone mechanism assigns the casting, materializing or launching of an execution seat to any seat — this goal's `leader` included. That act is the daemon's at birth. A mechanism that names a performer for it is `blocking`, and it is fixed by naming the roster seat rather than by naming a different performer.
- An `input-gaps` list is present (may be empty).
- Completeness: every one of the six workflow-authoring-checklist declarations was trialed against every produced execution seat in the draft; a failed declaration is `blocking`; two findings naming the same defect are collapsed to one; a finding with no plan location is not a finding.

Outcome map:

- **Complete** → the review package seeds verify.
- **Markerless or thin draft** → repair forward, log the gap, complete. Never reject. Never re-enter draft or design.
- **Verify FAIL relaunch** (this task's seat is on verify's `on-fail-relaunch`) → treat the FAIL body as the closed findings list; do not emit a new findings list; apply a targeted fix for those items only; rewrite the review package (same first-line marker); complete. Feedback schema: each closed finding paired with the fix applied.
</done-contract>
