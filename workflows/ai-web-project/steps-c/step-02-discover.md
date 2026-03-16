---
stepNumber: 2
stepId: discover
nextStepFile: './step-03-generate.md'
outputFile: '{output_folder}/ai-web-projects/{projectName}/project-brief.md'
knowledgeFile: '../data/platform-decision-framework.md'
---

# Step 2: Discover

**Goal:** Elicit the assistant's purpose, behavior, and constraints — then recommend the best platform.

---

## MANDATORY SEQUENCE

### 1. Load Knowledge

Read `{knowledgeFile}` — this is your decision framework for platform recommendation.

### 2. Elicit Use Case

Ask these questions conversationally (not as a rigid checklist — adapt based on answers):

**Core questions:**
- What problem does this assistant solve? What does it DO?
- Who is the primary user? (just you, a team, public?)
- How often will you use it? (daily, weekly, ad-hoc)
- What tone/personality should it have? (formal, casual, Socratic, blunt, etc.)

**Interaction model questions:**
- Is this conversational (back-and-forth dialogue) or task-based (give a goal, get a deliverable)?
- Do you want to guide each step, or delegate the whole task and review the result?
- Does it need to run autonomously while you're away?

**Data & capability questions:**
- Does it need to reference documents or files? If so, what kind and how many?
- Does it need live web search or real-time information?
- Does it need to generate images, code, or structured data?
- Does it need to produce finished deliverables (slides, reports, websites, apps)?
- Does it need access to Google services (Drive, Docs, Gmail)?
- Does it need access to a code repository?

**Constraint questions:**
- Are there things it must NEVER do? (hallucinate facts, give medical advice, etc.)
- Are there specific output formats required? (tables, JSON, bullet points, etc.)
- Any character/token limits you're aware of on the target platform?

### 3. Platform Recommendation

Using the decision signals from `{knowledgeFile}`:

1. **First, determine the category:** Based on the interaction model and autonomy answers, decide if this is a conversational assistant or an agent runtime use case. This is the most important fork — it separates Manus from the other three platforms.
2. If conversational: match signals to ChatGPT / Claude / Gemini
3. If agent runtime: recommend Manus
4. If signals point to multiple platforms, present the tradeoffs
5. Present your recommendation with clear reasoning:

> "Based on what you've described, I recommend **{platform}** because: {reasons}. The tradeoff is: {what you lose}."

Let the user confirm or override.

### 4. Companion Files Assessment

Based on the use case, determine if the project needs companion files beyond `instructions.md`:

| Signal | Companion File |
|--------|---------------|
| References specific documents/data | Knowledge file(s) — upload to platform |
| Needs user-specific context (preferences, profile) | `user-profile.md` or `user-profile.json` |
| Has multi-phase workflows | Phase files (e.g., `phase-1-discovery.md`) |
| Needs structured reference data | Data file (CSV, markdown table) |
| Gemini with large ingests | `ingests/` folder with source files |

Present your recommendation: "I think this project needs: {list of files with purpose}."

### 5. Update Project Brief

Update `{outputFile}`:
- Set `platform: {selected platform}`
- Fill in the **Project Summary** table
- Write the **Discovery Notes** section with a structured summary of everything learned
- Update `stepsCompleted` — add `"step-02-discover"`

---

## STEP MENU

Present these options and HALT:

| Option | Action |
|--------|--------|
| **[C] Continue** | Proceed to Step 3: Generate |
| **[R] Revise** | Revisit any discovery question or change platform |
| **[X] Exit** | Save state, exit workflow |

## ON REVISE

Ask which aspect to revise. Update the project brief accordingly. Redisplay this menu.
