---
task_id: p2-checkpoint
status: pending
phase: validate
complexity_score: 8
human_review: required
orchestrator_executed: true
hard_halt: true   # first real Gemini call (free-tier-or-metered confirmed before spend)
---

# Checkpoint p2-checkpoint: chat duo pilot — DeepSeek + Gemini

## Goal

Exercise the runner against the **real Gemini API** at the fidelity floor (real call → real files), confirming the runner now resolves **two chat providers** (DeepSeek + Gemini) via dynamic client resolution WITHOUT any `run.py` edit, then gate. (OpenAI dropped — D1 / D-exec-2; the chat trio is now a duo.)

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions + discoveries (D1 / D-exec-2 dropped OpenAI) |
| `../specs/api-text-worker-spec.md` | The Test Plan criteria |
| `orchestration/models/_api/clients/gemini.py` | The new artifact under test (deepseek.py already proven at p1-checkpoint) |
| `orchestration/models/gemini/manifest.yaml` | The Gemini package under test |

## Work to Evaluate

Phase 2 produced: `gemini.py` (p2-1) and the Gemini package (p2-2). (OpenAI's `openai.py`/package dropped — D1; not built.)

## Review Criteria

1. **HARD HALT — surface projected per-call spend before the first real Gemini call (confirm whether the key is on Gemini's free tier or metered); get explicit go-ahead before any spend.**
2. A real Gemini call (default JSON mode) writes files + valid `return.json` (`status: DONE`). (Search-grounding is DEFERRED to Phase 5 per D-exec-6 — `gemini.py` supports it but `run.py` is not wired for it in Phase 2; NOT exercised here.)
3. The chat **duo** ships proven: Gemini validated here (criterion 2); DeepSeek already validated at p1-checkpoint and still dynamically resolvable in the same runner (`clients/deepseek.py` intact, `run.py` unedited). A fresh DeepSeek call is optional — it is already proven.
4. **`run.py` was NOT edited** to add Gemini (`git diff` shows only new `clients/gemini.py` + `models/gemini/` — dynamic resolution holds).
5. Keys never appear in any prompt/return/stdout/log (grep clean).
6. Gemini's manifest variants route distinctly.

## Execution Flow

### Phase: Evaluate
1. Read Context Files + `decisions.md`.
2. Conductor exercises criteria 2–6 (real Gemini call, evidence on disk); a cold verifier re-exercises from the spec alone. Mismatch → FAIL.
3. Write the evidence sheet at `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-api-chat-duo.md`.

### Phase: Gate
1. Present per-criterion PASS/FAIL + evidence-sheet path.
2. **MUST** emit the Human Review Presentation block.
3. **HALT for human approval.** Do not advance on FAIL or without the spend go-ahead.
4. On approve: mark complete + flip `../deliverables.md` rows to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
