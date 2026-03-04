---
stepNumber: 2
stepName: 'context-gather'
nextStepFile: ./step-03-narrative.md
---

# Step 02: Context Gathering from Founder Documents

**Progress: Step 2 of 9** — Next: Narrative Draft

---

## STEP GOAL

Extract pitch-relevant content from founder documents by running context-distill separately for each milestone. Accumulate a pitch brief that feeds the narrative drafting step.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Investor mining founder documents for the strongest possible pitch material. Think like a partner reviewing a deal memo — what would make you champion this in the Monday meeting?

### Step-Specific Rules

- Run context-distill SEPARATELY for each milestone — each milestone contains different frameworks
- Use investor-focused search queries
- Do NOT ask the founder questions already answered in their documents
- Accumulate findings into a structured pitch brief

---

## MANDATORY SEQUENCE

### 1. Identify Available Milestones

Read the project-memo.md `stepsCompleted` array to identify which milestones have completed frameworks.

Check which milestone folders contain documents:
```
{project-root}/_bmad-output/{project_name}/founder/m1-conception/
{project-root}/_bmad-output/{project_name}/founder/m2-validation/
{project-root}/_bmad-output/{project_name}/founder/m3-brand/
{project-root}/_bmad-output/{project_name}/founder/m4-prototypation/
{project-root}/_bmad-output/{project_name}/founder/m5-market-validation/
{project-root}/_bmad-output/{project_name}/founder/m6-mvp/
```

Also check for a context folder:
```
{project-root}/_bmad-output/{project_name}/context/
```

List which folders have .md files. Only search folders that contain documents.

### 2. Run Context-Search Per Milestone

For EACH milestone folder that has documents, invoke the **context-distill** subagent. Provide these three inputs per call:

**M1 — Conception:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract all content relevant to an investor pitch: the core problem being solved and who experiences it (with data/numbers); the solution and what makes it different; target customer profile and their current workarounds; competitive landscape and positioning; value proposition and jobs-to-be-done; any key insights or contrarian views about the market"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m1-conception/`

**M2 — Validation:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract all content relevant to an investor pitch: market size (TAM, SAM, SOM with methodology and numbers); unit economics (pricing, CAC, LTV, payback period, margins); technology readiness level and technical differentiators; key assumptions tested and results; leap-of-faith assumptions and evidence; traction metrics or validation signals"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m2-validation/`

**M3 — Brand:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract all content relevant to an investor pitch: brand archetype and personality; brand positioning and messaging; visual identity direction (colors, tone, style); key brand statements or taglines; communication style and voice"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m3-brand/`

**M4+ — Later Milestones (if they have documents):**
- Adapt the specific request to the milestone's focus (prototypation → product screenshots/demo; market validation → traction data; MVP → product metrics)

**Context folder (if exists):**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract all content relevant to an investor pitch: market research findings and data points; competitive intelligence; industry trends and 'why now' evidence; customer quotes or feedback; any traction or proof points; positioning insights"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/context/`

**Project Memo:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract the project introduction, problem statement, solution description, tenets, and progress summary"
- Referenced Files: `{project-root}/_bmad-output/{project_name}/founder/project-memo.md`

### 3. Compile Pitch Brief

After ALL context-distill calls complete, compile findings into a structured pitch brief:

```
## Pitch Brief: {project_name}
### Type: Investor

#### Problem
[Compiled problem data, customer pain, numbers — from M1 + Context]

#### Solution
[Solution description, key differentiators — from M1]

#### Market Size
[TAM/SAM/SOM, market data — from M2]

#### Traction
[Any validation, metrics, proof points — from M2 + Project Memo]

#### Unit Economics
[Pricing, CAC, LTV, margins — from M2]

#### Competitive Position
[Competitors, positioning, differentiation — from M1 + Context]

#### Brand & Messaging
[Brand identity, key messages, visual direction — from M3]

#### Why Now
[Market trends, timing evidence — from Context + M1]

#### Team
[Founder info if available — from Project Memo]

#### Gaps
[What's missing that we need to ask the founder about]
```

### 4. Present Findings and Fill Gaps

Present the pitch brief to the user:
- "Here's what I extracted from your founder documents:"
- Show the compiled brief
- Highlight the **Gaps** section: "I still need the following to build a strong narrative:"
- Ask ONLY for the missing information

Wait for user response. Update the pitch brief with their answers.

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to narrative drafting
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the pitch brief forward as context

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Context-search invoked separately for each milestone with documents
- Pitch brief compiled with findings organized by deck section
- Gaps identified and filled through targeted questions only
- User confirms brief accuracy

❌ **FAILURE:**
- Running a single context-distill for all documents (must be per milestone)
- Asking questions already answered in founder documents
- Missing available milestone folders
- Fabricating content not found in documents
