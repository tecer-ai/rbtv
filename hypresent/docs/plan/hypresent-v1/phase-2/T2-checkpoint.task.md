---
task_id: T2-checkpoint
status: pending
phase: close
complexity_score: 9
human_review: required
---

# Checkpoint T2-checkpoint: Features Review (CP2)

## Goal

Evaluate Phase-2 feature deliverables against review criteria on BOTH fixtures and present findings for human approval.

---

## Context Files

| File | Purpose |
|------|---------|
| ../shape.md | Prior decisions and execution context. |
| ../../decision-log.md | Locked decisions D1/D2/D4/D6 to verify against. |
| ../../../spec/04-implementation-plan.md | T10–T15 contracts + acceptance + STATUS. |
| ../../../spec/05-verification-plan.md | V-TXT/FMT/RSZ/MOV/COL/CMT cases + §3 regression checklist. |
| runtime/js/{text-edit,text-format,resize,move,color,comments}.js, app/js/shell/{color-popover,comment-panel}.js | Work to evaluate. |

---

## Work to Evaluate

Phase-2 produced: text edit (T10); text format (T11); flow-aware resize (T12); transform move (T13); recolor token+element+inline (T14); comments + JSON island (T15).

## Review Criteria

1. Text edit + format work on both fixtures; native classes untouched; undoable (V-TXT-1/2, V-FMT-1/2, V-TXT-NEG).
2. Resize is flow-aware; NO `position:absolute` conversion; absolute content handled correctly (V-RSZ-1/2/3, V-RSZ-NEG) — D1.
3. Move writes ONLY `transform`; out-of-flow flag fires; no sibling reflow (V-MOV-1/2/3/4) — D2.
4. Recolor covers tokens AND per-element AND inline-style colors; palette filtered to color tokens (V-COL-1..5) — D6.
5. Comments anchor, thread, resolve; author name once; island portable + invisible + re-anchors (V-CMT-1..5) — D4.
6. §3 regression checklist clean: no `hyp-` leakage, no native class/id/`data-*` mutation, REPORT's own JS still runs, SVG paths intact, undo restores baseline.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files.
2. Review shape.md Decisions/Discoveries from Phase 2.
3. Evaluate each criterion PASS/FAIL with MCP evidence on DECK and REPORT.
4. Prepare a per-criterion findings summary.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. MUST append the Human Review Presentation block (format + flag criteria per `3-resources/tools/rbtv/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation and `.../data/plan-creation-rules.md` § Human Review Flag Criteria), pointing at any D1/D2/D6 deviation evidence and regression-checklist FAILs; if none, write "None identified" + one-line rationale.
3. HALT for human approval — do not advance regardless of findings.
4. If rejected: document feedback in shape.md, do not advance.
5. If approved: mark CP2 complete in the plan task list.
