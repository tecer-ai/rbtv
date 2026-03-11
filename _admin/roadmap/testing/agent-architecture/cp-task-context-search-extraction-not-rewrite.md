---
title: 'Compound: Context Search Extracts Instead of Rewrites'
docType: 'compound'
mode: 'create'
priority: 'High'
tracker: ''
stepsCompleted: ['step-01-init', 'step-02-self-assessment', 'step-03-discussion', 'step-04-document']
inputDocuments: ['_bmad/rbtv/tasks/context-search.xml', '.cursor/agents/bmad-rbtv-context-search.md', '.cursor/skills/bmad-rbtv-context-search/SKILL.md']
outputPath: '_bmad-output/planning-artifacts'
date: '2026-03-01'
yoloMode: false
---

# Context Search Extracts Instead of Rewrites

**Type:** System File  
**Priority:** High  
**Tracker:**  
**Status:** Backlog

---

## Overview

### Problem

The context-search agent (`_bmad/rbtv/tasks/context-search.xml`) reproduces entire file contents verbatim instead of extracting only the meaningful context relevant to the invoking agent's request. When invoked via Task tool with `subagent_type="context-search"`, the agent acts as a file copying service — returning hundreds of lines of raw content — instead of distilling targeted, actionable knowledge. This wastes context window space in the invoking agent's session and partially negates the benefit of using background agents (which exist to preserve main conversation context).

### Goals

1. Context-search agent returns distilled, relevant findings — not verbatim file reproduction
2. Output is filtered by relevance to the specific request before being returned
3. Invoking agents receive actionable knowledge they can use immediately without re-reading or re-filtering
4. Output size is proportional to relevance, not to input file size

### Constraints

- Context-search must still return enough detail for the invoking agent to act without reading the source files
- Critical definitions, positioning statements, and data points may need verbatim inclusion — the fix is about filtering, not about aggressive summarization
- The agent file (`.cursor/agents/`), skill file (`.cursor/skills/`), and task file (`_bmad/rbtv/tasks/`) all need aligned language

---

## Self-Assessment

### Error Analysis

**Error Type:** Execution failure (system file design flaw)

**Expectation vs. Actual:**
- **Expected:** Context-search agent reads referenced files and returns only meaningful context relevant to conversation — distilled, filtered, actionable
- **Actual:** Agent reproduced entire file contents verbatim, acting as file copying service

**Impact:** Wasted context window in invoking agent's session. Defeated purpose of background agent (preserve main context via summarized results). In triggering case, mentor session needed brand framework key decisions for Messaging Architecture — got 500+ lines of raw document content instead.

**Root Cause (dual):**
1. Task definition actively encourages copying — `context-search.xml` uses "complete" 6 times, says "not just summaries," has zero filtering/distillation instructions
2. Invoking agent prompt was also at fault — asked for "full contents" instead of specifying what context was needed

### Context Source Evaluation

| File | Role | Issue |
|------|------|-------|
| `_bmad/rbtv/tasks/context-search.xml` | Primary task definition | **Root cause.** Multiple instructions push verbatim reproduction: "Extract COMPLETE relevant content," "Capture complete code blocks, templates, procedures — not just summaries," "Include complete content — do not summarize." Zero filtering or distillation guidance. |
| `.cursor/agents/bmad-rbtv-context-search.md` | Agent definition | Reinforces problem: "Returns complete, deep findings so you don't need to read the files." Word "complete" sets copy-everything expectation. |
| `.cursor/skills/bmad-rbtv-context-search/SKILL.md` | Skill file | Neutral — references task file only. |
| `CLAUDE.md` + `bmad-rbtv-background-agents.mdc` | Workspace rules | Correctly prescribe background agents for research to preserve context. But context-search fills return with full file contents, partially negating benefit. |

**Gaps:**
- No instruction to filter output by relevance to specific request
- No instruction to distill or synthesize rather than copy
- No output size constraint or token budget
- No distinction between "extract relevant parts" vs "copy entire file"
- "Not just summaries" actively discourages summarization — often exactly what's needed
- No guidance for invoking agents on how to write targeted context-search prompts

### Improvement Options

1. **New Rule**: Invoker prompt template — require agents invoking context-search to specify: (a) what decision is being made, (b) what specific data points are needed, (c) what return format is expected. Prevent lazy "give me everything" prompts.
   - **Rationale:** Half the problem was the invoking prompt. Rule prevents "full contents" requests and forces targeted invocation.
   - **Location:** `.cursor/rules/bmad-rbtv-background-agents.mdc` — add "Context Search Invocation" section

2. **Modify Existing Rule**: Rewrite agent description — change "Returns complete, deep findings" → "Returns distilled, relevant findings." Replace "exhaustive knowledge extractor" → "targeted knowledge extractor." Update "What You Get Back" section for filtered output expectations.
   - **Rationale:** Agent description frames agent self-concept. "Complete" and "exhaustive" train copying. "Distilled" and "relevant" train filtering.
   - **Location:** `.cursor/agents/bmad-rbtv-context-search.md`

3. **Update System File**: Rewrite `context-search.xml` — replace all 6 "complete" instances with "relevant"/"targeted." Change "not just summaries" → "summarize where appropriate, include verbatim only for critical definitions, statements, or data." Add substep 2d "Relevance Filter" requiring evaluation of each extraction against specific request.
   - **Rationale:** Root cause file. Language directly instructs behavior. Change language → change behavior.
   - **Location:** `_bmad/rbtv/tasks/context-search.xml`

4. **Add Constraint**: Explicit output size limit — "Output MUST NOT exceed 30% of total input file size." Add relevance threshold: "Only include content that directly answers specific request or is required to understand the direct answer."
   - **Rationale:** Hard size constraint mechanically prevents file copying. Agent must filter when it can't return everything.
   - **Location:** `_bmad/rbtv/tasks/context-search.xml` — new LLM rules

5. **Alternative Approach**: Two-pass architecture (scan → extract) — Pass 1: Read all files, output relevance manifest (table: file, section, why relevant). Pass 2: Extract only manifest-identified sections. Forces relevance judgment before extraction.
   - **Rationale:** Single-pass reads and extracts simultaneously, defaulting to "include everything just in case." Two-pass forces relevance judgment first.
   - **Location:** `_bmad/rbtv/tasks/context-search.xml` — restructure flow steps

---

## Proposed Solution

**Deferred.** Five improvement options documented above. Implementation decision to be made in a future session. Recommended starting point: Options 2+3 combined (modify agent description + rewrite task file) as highest-leverage, lowest-effort combination.

### Implementation Details

| Aspect | Details |
|--------|---------|
| File(s) to modify/create | `_bmad/rbtv/tasks/context-search.xml`, `.cursor/agents/bmad-rbtv-context-search.md`, `.cursor/skills/bmad-rbtv-context-search/SKILL.md` |
| Scope of change | Moderate — language rewrites across 3 files + add filtering step to task flow |
| Related files | `.cursor/rules/bmad-rbtv-background-agents.mdc` (if Option 1 included), `CLAUDE.md` (background agent section) |

---

## Rationale

The task definition is the root cause. Every instruction in `context-search.xml` that says "complete" trains the agent to copy files rather than extract relevant knowledge. The word appears 6 times. The phrase "not just summaries" actively discourages the filtering behavior that is needed. Fixing the language in the task file directly changes agent behavior. Aligning the agent description reinforces the correction.

---

## Acceptance Criteria

- [ ] Context-search agent, when given a specific request and 3+ files totaling 500+ lines, returns fewer than 150 lines of targeted output
- [ ] Output contains only content directly relevant to the specific request, with source attribution
- [ ] Agent description in `.cursor/agents/bmad-rbtv-context-search.md` uses "distilled"/"relevant" language, not "complete"/"exhaustive"
- [ ] Task file `context-search.xml` contains zero instances of unqualified "complete" (qualified usage like "complete definition" for specific items is acceptable)
- [ ] Task flow includes an explicit relevance filtering step before output generation

---

## Related Files

| File | Relationship |
|------|--------------|
| `_bmad/rbtv/tasks/context-search.xml` | Root cause — primary task definition with copy-encouraging language |
| `.cursor/agents/bmad-rbtv-context-search.md` | Reinforces problem — agent self-concept uses "complete" framing |
| `.cursor/skills/bmad-rbtv-context-search/SKILL.md` | References task file — neutral but needs alignment |
| `.cursor/rules/bmad-rbtv-background-agents.mdc` | Prescribes background agent usage — may need invoker prompt guidance |
| `CLAUDE.md` | Workspace rules — background agent section |

---

## References

- Triggering incident: Mentor session for Tecer M3 Messaging Architecture — context-search invoked to load M3 brand files, returned full file contents instead of extracting key decisions and statements
- Related pattern: Any workflow that uses context-search for multi-file context loading will hit this same behavior

---

## Discussion Notes

### Selected Improvement Option

**Deferred.** User requested compound be documented for later implementation. Recommended combination: Options 2+3 (agent description rewrite + task file rewrite) as starting point.

### Open Questions for Implementation Session

- **Minimal or comprehensive?** Options 2+3 (language fix) vs Option 5 (two-pass architecture)
- **Invoker side constraint?** Option 1 (prompt template rule) — include or defer?
- **Hard size cap?** Option 4 (30% output limit) — include as supplementary guardrail or skip?
- **Rename?** See naming observation below — implement during same change or separate?

### Additional Context

- The context-search agent is used across multiple workflows (mentor, coach, any agent persona session)
- Fix must preserve the agent's ability to return enough detail for standalone actionability
- Critical definitions and data points (e.g., positioning statements, Why statements) should still be returned verbatim — the issue is returning *everything* verbatim

---

### Addendum: Invoker-Side Misuse (2026-03-03)

**Triggering incident:** Mentor session (Tecer M3 Brandbook, Step 01 Init). Agent needed key elements from 6 M3 brand framework files. Instead of reading the files directly, the agent invoked context-search with the prompt: "Read ALL of these files completely and return their FULL contents. Do not summarize — return everything."

**Token waste analysis:** The round-trip cost is 3x vs. direct read:
1. Context-search subagent reads files (1x tokens consumed)
2. Context-search outputs full contents back to parent (1x tokens generated by subagent)
3. Parent agent reads the subagent's output (1x tokens consumed by parent)

Direct read = 1x tokens consumed. Context-search-as-file-reader = 3x tokens for identical information. Zero added value.

**Root cause (invoker side):** The invoking agent treated context-search as a file reader — the prompt explicitly asked for "full contents" with "do not summarize." This is a decision error by the invoking agent, not a context-search behavior error. Even if context-search were fixed per this PRD, an invoking agent can still misuse it by asking for everything.

**Implication for Option 1:** The invoker-side rule (Option 1) is more important than initially assessed. The background-agents rule (`.cursor/rules/bmad-rbtv-background-agents.mdc`) must include explicit guidance:
- **NEVER** use context-search to read and return full file contents — use Read tool directly
- **ONLY** use context-search when you need targeted extraction or summarization from multiple files
- **ALWAYS** specify in the prompt: what decision you're making, what specific data points you need, and what format to return
- If you need the full content of a file, read it yourself — that's what the Read tool is for

**Recommendation update:** Option 1 (invoker prompt rule) should be elevated from "optional add-on" to "must-have" alongside Options 2+3. The fix requires both sides: context-search must filter (Options 2+3), AND invoking agents must not ask for everything (Option 1).

---

### Addendum: Naming Observation (2026-03-03)

**Current name:** `context-search` (subagent_type, agent file, skill file, task file)

**Problem:** "Search" implies finding — like grep or semantic search. The agent doesn't search; it reads known files and distills them. The name sets the wrong mental model for invoking agents, making it feel like a general-purpose file access tool rather than a targeted extraction/summarization service.

**Proposed rename:** `context-distill`

Rationale: "Distill" captures exactly what the agent should do — take raw content from multiple files and reduce it to its essential, relevant components. The word implies filtering, concentrating, and extracting the essence. It naturally discourages "give me everything" prompts because you don't ask a distiller to return the raw input.

**Scope of rename:**
- Subagent type: `context-search` → `context-distill`
- Agent file: `.cursor/agents/bmad-rbtv-context-search.md` → `.cursor/agents/bmad-rbtv-context-distill.md`
- Skill file: `.cursor/skills/bmad-rbtv-context-search/SKILL.md` → `.cursor/skills/bmad-rbtv-context-distill/SKILL.md`
- Task file: `_bmad/rbtv/tasks/context-search.xml` → `_bmad/rbtv/tasks/context-distill.xml`
- References in rules, CLAUDE.md, and any workflow files that mention context-search
