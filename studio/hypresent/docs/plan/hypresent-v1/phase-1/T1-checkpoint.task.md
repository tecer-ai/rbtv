---
task_id: T1-checkpoint
status: pending
phase: close
complexity_score: 8
human_review: required
---

# Checkpoint T1-checkpoint: Foundation Review (CP1)

## Goal

Evaluate Phase-1 foundation deliverables against review criteria and present findings for human approval.

---

## Context Files

| File | Purpose |
|------|---------|
| ../shape.md | Prior decisions and execution context. |
| ../../../spec/01-architecture.md | Isolation, protocol, serialization, namespacing — the constraints to verify. |
| ../../../spec/04-implementation-plan.md | T1–T9 contracts + acceptance + STATUS. |
| ../../../spec/05-verification-plan.md | V-OPEN/SEL/HIST/SAVE foundation cases + §3 regression checklist. |
| server/server.py, server/api.py, app/js/*, runtime/js/element-registry.js, selection.js, commands.js, history.js, serializer.js | Work to evaluate. |

---

## Work to Evaluate

Phase-1 produced: stdlib server + open/save API (T1); app shell + vendored libs (T2); iframe load + runtime boot (T3); parent↔iframe bridge (T4); element registry (T5); selection (T6); command factory (T7); unified history (T8); serializer (T9).

## Review Criteria

1. Server serves both fixtures; `/doc/` rooted at the file's dir; open/save round-trips on disk (V-OPEN server side).
2. Both fixtures load in the iframe; REPORT's own JS runs; `ready` fires (V-OPEN-1/2).
3. Bridge round-trips commands + events, origin-filtered (T4 acceptance).
4. Registry tags editable elements with `data-hyp-id` WITHOUT touching native ids/`data-*`/classes (V-BOOT-3) — namespacing constraint.
5. Selection draws a `hyp-` ring with no document-class mutation; SVG path not text-editable (V-SEL-1/2/3).
6. History undo/redo restores a mixed synthetic-command sequence; redo tail truncates (V-HIST-1/2 partial).
7. Serializer emits chrome-free HTML; document's own scripts retained (namespace-strip only, no doc-body sanitizer); node-count guard non-destructive (T9-scoped acceptance: chrome-free + doc JS retained + valid standalone HTML — reflow/round-trip/re-edit gates are T18).

## Execution Flow

### Phase: Evaluate
1. Read all Context Files.
2. Review shape.md Decisions/Discoveries from Phase 1.
3. Evaluate each criterion PASS/FAIL with evidence (MCP runs / `git diff`).
4. Prepare a per-criterion findings summary.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. MUST append the Human Review Presentation block (format + flag criteria per `3-resources/tools/rbtv/orchestration/workflows/planning/templates/plan-task-microstep-template.md` § Human Review Presentation and `3-resources/tools/rbtv/orchestration/workflows/_shared/authoring/human-review-criteria.md`), pointing at the registry namespacing result and the serializer chrome-free output; if no flags fire, write "None identified" + one-line rationale.
3. HALT for human approval — do not advance regardless of findings.
4. If rejected: document feedback in shape.md, do not advance.
5. If approved: mark CP1 complete in the plan task list.
