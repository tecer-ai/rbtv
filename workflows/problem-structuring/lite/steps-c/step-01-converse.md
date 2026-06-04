---
name: ps-lite-converse
description: Conversational problem structuring with Socratic questioning and complexity-based escalation
nextStepFile: null
---

# Step 1: Conversational Problem Structuring

## MANDATORY SEQUENCE

### 1. OPEN

Ask: **"What are you trying to figure out?"**

No preamble. No framework introduction. One warm, direct question.

### 2. CONVERSATION LOOP (2-3 exchanges)

Ask ONE question per exchange — never batch questions.

After each user response:

1. **Clarify** — Ask Socratic questions:
   - "What specifically about X?"
   - "Who is affected?"
   - "What happens if you do nothing?"
2. **Traction** — Ask at least one traction question during the loop. Traction questions target the user's relationship to the problem, not its content — articulation is the value, not the information:
   - "What's hard about this for you?"
   - "What are you avoiding?"
   - "What feels uncomfortable?"
   - "What's clear vs. fuzzy?"
3. **Surface structure** — Organically group related points, identify categories, highlight tensions
4. **Assess complexity** — Silently evaluate escalation triggers (see below)

### 3. ESCALATION CHECK

If ANY trigger appears:

- 3+ distinct problem dimensions identified
- Competing priorities or stakeholders
- Dependencies requiring decomposition
- User explicitly asks for more structure

→ Say: **"This is getting interesting — enough moving parts that the full structuring toolkit would help. Want me to switch to [PS] with what we've gathered?"**

→ On yes: Load `{rbtv_path}/workflows/problem-structuring/workflow.md`, carry all gathered context as initial input.

→ On no: Continue conversational loop.

### 4. SIMPLE RESOLUTION (no escalation triggered)

When the problem is clear:

1. Deliver a **clean problem statement** (1-2 sentences)
2. List **2-3 actionable next steps**
3. Ask: **"Does this capture it, or is there more?"**

---

## MENU

| Option | Action |
|--------|--------|
| **[C] Continue** | Return to conversation loop |
| **[PS] Escalate** | Switch to full Problem Structuring workflow |
| **[DA] Done** | End session |

**HALT and WAIT for user input.**
