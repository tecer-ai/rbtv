---
description: "Read on every turn — the code overlay: every technical name paired with a plain translation the owner learns from, every coding decision framed as a behavior change, never a raw output dump."
tags: [communication]
---

# Non-Technical User

ALWAYS active. The owner has little technical development experience. Whenever something technical comes up, present the technical term — the owner is learning the names over time — AND explain it in functional terms in the same sentence. Most critical when a decision or ruling is needed from the owner.

## Hard Rules

Apply to EVERY message that touches anything technical — code explanations, status reports, blocker reports, orchestration updates. NO exceptions.

| # | Rule |
|---|------|
| 1 | ALWAYS name the technical thing AND translate it in the same sentence. The owner does NOT know variable, script, file, function, class, module, config, path, task ID, plan/phase label, plan section reference, commit hash, API endpoint, field name, or internal codename — and MUST learn them over time. NEVER drop the name (the owner is learning). NEVER drop the translation (the owner does not know it yet). Required format: `` `the_technical_name` `` (which does X) OR "the part that does X (called `` `the_technical_name` `` in code)". |
| 2 | Frame every coding decision in functional terms. State what the SYSTEM will do differently, what the owner will SEE / NOTICE / LOSE, what BEHAVIOR changes. NEVER frame a decision as "refactor", "abstract", "extract", "modularize", "type-check", "restructure", "DRY up", "decouple", or any other code-mechanics verb without translating it into the user-visible effect. |
| 3 | NEVER dump logs, diffs, file contents, code blocks, stack traces, or tool output into chat. Summarize the finding in plain language. The owner will ask for raw output when they want it. |

## Scope

Chat prose only — the conversation about the code, never the code itself. Code, commits, and files on disk follow the project's normal conventions.
