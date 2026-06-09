# Sub-Agents

**MANDATORY. NO EXCEPTIONS.** Every Agent tool call MUST pass the Pre-Dispatch Gate below before invocation. Skipping the gate is a rule violation, even for "quick" or "simple" dispatches.

## Default Model

When launching sub-agents via the Agent tool, use `sonnet` as the default model. NEVER use `haiku` unless the user explicitly requests it.

### Haiku Reconciliation — Approved Delegation Map

An orchestration delegation map the user has approved IS the "explicit request" this section requires — but ONLY for the mechanical batches that map names, and ONLY for haiku. No separate per-dispatch permission is needed once the map is approved.

| Condition | Haiku eligibility |
|-----------|-------------------|
| User-approved delegation map names haiku for a specific mechanical batch | Routable for THAT batch — the map approval satisfies the "explicit request" clause above |
| No approved delegation map naming haiku for the batch | NEVER routed — default to the cheapest **non-haiku** capable model; every pinned role (reviewer, verifier, debug, commit) floors at **sonnet** regardless |
| Batch carries any judgment call | NOT mechanical — haiku is off the table even under an approved map |

**Mechanical = no judgment:** disjoint-allowlist file ops, format conversions, deterministic batch edits with self-verifiable acceptance. The moment a batch requires a judgment call, it is no longer mechanical. A standalone haiku dispatch outside an approved delegation map still requires the explicit user ask.

## Pre-Dispatch Gate

Before EVERY Agent tool call, you MUST:

1. **Scan the planned prompt** for trigger keywords (see Mandatory Skill Triggers below).
2. **Identify every matching skill** from the available skill list — RBTV skills below, plus any non-RBTV skills (sb-os, user-defined, third-party) that match the planned task.
3. **Name each matching skill explicitly** in the sub-agent prompt using the Required Phrasing format.
4. **Include the mandate** — do not just mention the skill; instruct the sub-agent to invoke and follow it.

You MUST NOT dispatch until the prompt contains every required skill directive. If you catch yourself about to dispatch without the gate, STOP and rewrite the prompt.

## Mandatory Skill Triggers

If the planned sub-agent task or prompt contains ANY trigger in a row below, you MUST name the matching installed RBTV skill in the prompt. Multiple matching trigger families = multiple skills named.

| Trigger family — keywords or task type | Matching RBTV skill |
|----------------------------------------|---------------------|
| research, web search, URL, fetch, extract page content, multi-source, citations, look up online, find on the web | `rbtv-web-searching` |
| Commit, stage, push changes | `rbtv-commit` |

If multiple installed skills match a trigger family, name every match. If no installed skill matches a trigger family for the current dispatch, the family is inactive — do not invent skill names.

**Web research is the hardest-enforced case.** Any dispatch whose prompt mentions research, web searching, URL fetching, page extraction, or source gathering — in ANY phrasing — MUST name the matching installed web-research skill. No exceptions. No "this is just a quick lookup." No "the sub-agent will figure it out."

## Non-RBTV Skills

This rule covers RBTV skills only. Other skills installed in the workspace (sb-os, user-defined, plugins, third-party) have their own scope and triggers. When a non-RBTV skill matches the planned sub-agent task — based on its description in the available skill list — you MUST also name it in the sub-agent prompt using the Required Phrasing below. The Pre-Dispatch Gate fires for ALL applicable skills, regardless of source.

## Required Phrasing

The sub-agent prompt MUST contain a directive in one of these forms. Mere mention of the skill name is INSUFFICIENT. Replace `<skill-name>` with the actual installed skill matched from the trigger families.

| Acceptable | Unacceptable |
|------------|--------------|
| "Invoke the `<skill-name>` skill before any web work and follow it exactly." | "You can use the `<skill-name>` skill." |
| "You MUST invoke `<skill-name>` before any edit and follow it exactly." | "Consider checking `<skill-name>`." |
| "Start by invoking `<skill-name>` and execute its checklist." | "See `<skill-name>` for context." |

Directives MUST be imperative ("invoke", "follow exactly", "execute") — never permissive ("may", "consider", "can").

## File-Path Hygiene — Write / Move Dispatches

When a sub-agent will CREATE, WRITE, or MOVE files, the prompt MUST give every target path as WORKSPACE-ROOT-ABSOLUTE (or fully absolute) — NEVER a bare relative path. A sub-agent resolves relative paths from its OWN working directory, which is NOT guaranteed to match the parent's; a bare `subdir/file.md` silently lands in the wrong tree. State the workspace root explicitly in the prompt AND prefix every write path with it. After the dispatch returns, VERIFY each claimed file exists at its intended absolute path before treating the dispatch as done — a sub-agent's success report is not proof the file landed where you intended.

## Red Flags — STOP and Rewrite

If you notice any of these thoughts, you are about to violate this rule:

| Thought | Action |
|---------|--------|
| "The sub-agent will auto-discover the skill" | STOP. Name it explicitly. Auto-discovery is unreliable. |
| "This dispatch is too small to need a skill directive" | STOP. Size does not waive the gate. |
| "I already named the skill last dispatch" | STOP. Each dispatch is independent. Name it again. |
| "The prompt is already long, adding skill directives will bloat it" | STOP. Brevity does not waive the gate. |
| "Specialized sub-agent types (Explore, Plan, general-purpose) don't need this" | STOP. These types need it MOST — they skip skills by default. |
| "No installed skill matches this exact trigger keyword" | STOP. Re-scan the available skill list for partial matches before declaring the family inactive. |
| "The sub-agent shares my working directory — a bare relative write path is fine" | STOP. Give workspace-root-absolute write paths and verify each file landed on return. |

## Scope

This rule applies to EVERY Agent tool invocation, including parallel dispatches and background agents. It does not apply to the `Skill` tool (direct skill invocation by the parent agent).
