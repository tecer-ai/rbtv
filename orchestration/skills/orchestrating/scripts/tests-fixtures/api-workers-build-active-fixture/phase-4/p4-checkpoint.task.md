---
task_id: p4-checkpoint
status: pending
phase: validate
complexity_score: 7
human_review: required
orchestrator_executed: true
hard_halt: true   # running install.py (env_file prompt) is USER-EXECUTED-ONLY
---

# Checkpoint p4-checkpoint: the conductor sees the workers

## Goal

Confirm the conductor can now SEE and route to the API/agentic/Claude-agent workers: availability resolves on key-present, manuals render zero-diff, `install.py` records `env_file`, docs-sync is complete.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | Prior decisions + discoveries |
| `orchestration/skills/orchestrating/cards/{dispatch-wrapper,verification}.md` + `core-protocol.md` | Edited surfaces |
| `install.py` + `admin/install/module-manifest.json` | Install + registration |
| `orchestration/models/render-manuals.py` | The manual renderer |

## Work to Evaluate

Phase 4 produced: dispatch-wrapper transport (p4-1), verification lighter gate (p4-2), core-protocol roster (p4-3), install.py env_file (p4-4), `.env.example` key names (p4-5, inline), the manual render (p4-6, inline), docs-sync (p4-7).

## Review Criteria

1. `python orchestration/models/render-manuals.py` renders the new manuals and is **zero-diff for unchanged** manuals (p4-6); EXIT 0 on the un-piped process.
2. **USER-EXECUTED-ONLY hard halt:** running `install.py` (the interactive `env_file` prompt) is performed by the user; the conductor surfaces it and does not auto-run it. After the user runs it, `rbtv.json` carries `env_file` and the availability block lists the new packages.
3. `.env.example` lists the four key names (`DEEPSEEK_/GEMINI_/OPENAI_/MANUS_API_KEY`) vault-side (p4-5).
4. `module-manifest.json` parses and registers every new installable file (p4-7).
5. dispatch-wrapper transport row + verification lighter gate read correctly against the API return contract.
6. Atomic-files + no invariant contradiction across the edited cards.

## Execution Flow

### Phase: Evaluate
1. Read Context Files + `decisions.md`.
2. Conductor runs the render (un-piped, reads EXIT), checks the manifest parses, and confirms (post user-run) the availability resolution. Evidence files captured.
3. Write the evidence sheet at `1-projects/rbtv-evolution/coding/done-gate-evidence/rbtv/{date}-conductor-integration.md`.

### Phase: Gate
1. Present per-criterion PASS/FAIL + evidence-sheet path; surface the USER-EXECUTED install step.
2. **MUST** emit the Human Review Presentation block.
3. **HALT for human approval.** Do not advance on FAIL.
4. On approve: mark complete + flip `../deliverables.md` rows to ✅.

> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.
