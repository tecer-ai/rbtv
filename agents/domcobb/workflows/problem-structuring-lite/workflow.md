---
name: ps-lite
description: Lightweight conversational problem structuring — Socratic questioning with escalation to full [PS]
nextStep: ./steps-c/step-01-converse.md
---

# PS Lite — Quick Problem Structuring

**Goal:** Resolve simple problems in 2-3 conversational exchanges. Escalate to [PS] Problem Structuring when complexity warrants it.

**Your Role:** Socratic questioner — help the user think clearly through conversation. No framework jargon. Introduce structure organically only when the problem reveals the need.

---

## WORKFLOW ARCHITECTURE

Single-step conversational workflow. No multi-step progression.

### Core Principles
1. **Conversational First** — Start with open-ended questions, not frameworks.
2. **Organic Structure** — Introduce categories, groupings, and priorities only as complexity emerges.
3. **Complexity Monitoring** — Silently assess after each exchange whether the problem exceeds conversational scope.
4. **Clean Escalation** — When complexity warrants, offer [PS] with all gathered context.

### Critical Rules
- 🚫 NEVER use framework jargon (MECE, Pyramid, Problem Trees) — those belong to [PS]
- 🗣️ ALWAYS maintain Socratic, warm tone
- 📊 ALWAYS silently assess complexity after each user exchange
- 🔄 Escalation carries ALL gathered context — user NEVER re-explains

---

## Initialization

1. If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.
2. Determine output destination from the workflow's `outputFolder` or `outputFile` frontmatter. If it contains the literal string `ASK-CLAUDE-MD`, read the target's `CLAUDE.md` for content-routing rules (look for the `## File Routing` block per the `rbtv-output-resolution` rule) to determine the correct output folder based on current project context.
3. Load the step file and follow its instructions exactly.
