---
task_id: p3-checkpoint
status: pending
phase: validate
complexity_score: 8
human_review: required
orchestrator_executed: true
---

# Checkpoint p3-checkpoint: determinism + no-collapse

## Goal

Exercise the deterministic selector against the **real installed manifests** (with `models/claude/` present) and confirm the Claude collapse is gone — every `(model, variant)` enumerated, the pick deterministic, summaries name pairs.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions + discoveries |
| `../specs/deterministic-routing-spec.md` | The Test Plan criteria exercised here |
| `orchestration/models/claude/manifest.yaml` | The new package under test |
| `orchestration/skills/orchestrating/cards/{routing,intake}.md` | The edited cards under test |

## Work to Evaluate

Phase 3 produced: the Agent-tool Claude package (p3-1), the routing selector + carrier + API hooks (p3-2), the intake pair-enumeration (p3-3).

## Review Criteria

1. Every installed `(model, variant)` is enumerated for a sample text leaf — Claude `opus`/`sonnet` included (spec Test Plan #1).
2. The pick is **deterministic** — same leaf, same pick twice; no tie reached the judgment fallback (#2).
3. A sample intake budget summary names `(model, variant)` on every row — no bare "Claude" (#3).
4. A web leaf filters to `web_access: true` variants only (#4).
5. Pinned roles still win (reviewer floors at sonnet) (#5).
6. `models/claude/` is sibling to — not a replacement for — `claude-cli`; both enumerate distinctly.
7. Atomic-files + no invariant contradiction in the edited cards.

## Execution Flow

### Phase: Evaluate
1. Read Context Files + `decisions.md`.
2. The conductor exercises criteria 1–6 against the live `models/` folder, writing selection traces + a sample summary as evidence files; a cold verifier re-exercises from the spec alone.
3. Write the evidence sheet at `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-deterministic-routing.md`.

### Phase: Gate
1. Present per-criterion PASS/FAIL + evidence-sheet path.
2. **MUST** emit the Human Review Presentation block.
3. **HALT for human approval.** Do not advance on FAIL.
4. On approve: mark complete + flip `../deliverables.md` rows to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
