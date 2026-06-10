# p5-refs (B13) — Plan Link Check — Evidence Report

- **Executed by:** conductor (per the approved delegation map — no dispatch)
- **Date:** 2026-06-10
- **Method:** deterministic scan, `./p5-refs-link-check.py` (sibling file = the computation artifact). Extracts markdown links + backtick path tokens from the plan's deliverable docs; resolves each against four roots (containing file → plan root → project root `studio/hypresent` → rbtv repo root); classifies per the Plan Linking Standard (internal = file-relative, external = project-root-relative).
- **Scope:** 29 files — plan, decisions, deliverables, learnings, structured-problem, `specs/*.md`, `phase-*/*.task.md`, `phase-*/evidence/*.md`. Excluded by design: `run-log.md` + `state-capsule.md` (append-only state spine; historical pre-rename paths are correct as records) and `_dispatch-*.md` (work-dir-relative path maps by design).

## Raw result

- Refs checked: **345**
- Scanner-clean (OK / OK*): **326**
- Scanner-flagged: **19** after 1 fix (raw run: 20) — every flagged row adjudicated below.

## Adjudication of all flagged rows

| Row(s) | Class | Ruling |
|--------|-------|--------|
| plan `../`, decisions `../` | Prose, not a link | Both are the standard's own wording: "file-relative paths (`./`, `../`)". No target intended. |
| decisions `assets/`, structured-problem `assets/` | Prose, not a link | "library fragments carry their own `assets/`" — generic folder name in a constraint description. |
| deck-ingest-spec `/doc/`, findings-p2 `/app/builder.html`, findings.md (p1) `/doc/` mention | Server routes, not file links | URL paths of the running app (`handle_open` re-points `/doc/`; headed exercise navigated to `/app/builder.html`). |
| deck-save-spec `assets/logo.png`, `assets/x.png` | Deck-content examples, not plan links | Examples of asset refs INSIDE a saved deck's HTML — the spec describes deck content. |
| decisions ×3 `orchestration/workflows/_shared/authoring/*.md` | Tolerated variant — resolves | rbtv-repo-root-relative refs to shared RBTV standards; all 3 exist at the repo root. The standard's "project root" is `studio/hypresent`; repo-shared standards have no hypresent-relative form. |
| deliverables + p5-checkpoint.task `1-projects/rbtv-evolution/coding/done-gate-evidence/hypresent/` | Tolerated variant — resolves | VAULT-root-relative `{evidence_root}` per the vault CLAUDE.md routing table. Directory confirmed to exist (conductor `ls`). Outside all repo roots by design. |
| 5× completed-phase task files `phase-N/evidence/` (p1-checkpoint, p2-2, p2-checkpoint, p3-checkpoint, p4-checkpoint) | Historical deviation — left unchanged | Plan-root-relative instead of strict file-relative. Consumed correctly the whole run (dispatch prompts inlined absolute paths; evidence landed correctly in phases 1–4). Rewriting certified, already-consumed task files would muddy the run record for zero forward value. |
| findings.md (p1) `3-resources/tools/rbtv/html/hypresent/` | Historical record — left unchanged | Pre-rename path correctly recording where Phase-1 ran. The html→studio rename handover explicitly preserved historical records. |
| p5-checkpoint.task.md `phase-5/evidence/` | **FIXED** | The one deviation in a still-pending (future-consumed) file → corrected to file-relative `./evidence/`. Confirmed cleared on re-run (violations 8→7). |

## Verdict

**PASS.** Zero broken plan links — every true reference resolves on disk at its intended root. Plan Linking Standard compliance holds across all live and forward-consumed documents after one surgical fix to the pending `p5-checkpoint.task.md`; all remaining scanner flags are adjudicated prose/route/content noise, tolerated root-variants that resolve, or deliberately preserved historical records.
