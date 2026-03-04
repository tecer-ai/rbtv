---
stepNumber: 2
stepName: 'context-gather'
nextStepFile: ./step-03-narrative.md
---

# Step 02: Context Gathering from Founder Documents

**Progress: Step 2 of 9** — Next: Narrative Draft

---

## STEP GOAL

Extract pitch-relevant content from founder documents by running context-distill separately for each milestone. Focus on what a CLIENT buyer cares about: their problem, your solution, proof it works, and why you vs. alternatives.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer mining founder documents for the content that would convince a procurement committee. Think like a VP evaluating a vendor — what would make you put this on the shortlist?

### Step-Specific Rules

- Run context-distill SEPARATELY for each milestone — each milestone contains different frameworks
- Use CLIENT-FOCUSED search queries (not investor-focused)
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

### 2. Run Context-Distill Per Milestone

For EACH milestone folder that has documents, invoke the **context-distill** subagent:

**M1 — Conception:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract all content relevant to a client/sales pitch: the specific problem the TARGET CLIENT experiences and how they cope today; the solution and its concrete benefits for THIS type of client; how the solution works (workflow, process, integration); competitive alternatives the client might consider; value proposition from the client's perspective; jobs-to-be-done that the client hires this product for"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m1-conception/`

**M2 — Validation:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract all content relevant to a client/sales pitch: pricing structure and plans; ROI metrics or calculations; implementation timeline and effort; any pilot results or validation data; unit economics that affect pricing decisions; technology readiness and reliability evidence"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m2-validation/`

**M3 — Brand:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract all content relevant to a client pitch: brand positioning relative to competitors; messaging that resonates with buyers; trust signals and credibility markers; communication tone appropriate for B2B sales; key brand statements or taglines"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/founder/m3-brand/`

**M4+ — Later Milestones (if they have documents):**
- Adapt the specific request (prototypation → product demo/screenshots; market validation → client testimonials/case studies; MVP → product metrics/uptime)

**Context folder (if exists):**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract all content relevant to a client pitch: customer feedback or testimonials; case study material; competitive intelligence from the client's perspective; industry benchmarks the client would recognize; proof points, metrics, or success stories"
- Referenced Files: All .md files in `{project-root}/_bmad-output/{project_name}/context/`

**Project Memo:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract the project introduction, problem statement, solution description, tenets, and any client-relevant progress"
- Referenced Files: `{project-root}/_bmad-output/{project_name}/founder/project-memo.md`

### 3. Compile Client Pitch Brief

After ALL context-distill calls complete, compile findings:

```
## Client Pitch Brief: {project_name}
### Target: {target_client}

#### Their Problem
[The client's specific pain — in THEIR language, not yours — from M1 + Context]

#### Current Solution / Status Quo
[What they use today and why it's insufficient — from M1]

#### Your Solution
[What you do for them, concrete benefits — from M1]

#### How It Works
[Workflow, process, integration points — from M1 + M4]

#### Proof Points
[Testimonials, case studies, metrics, pilot results — from M2 + M5 + Context]

#### Competitive Alternatives
[What else they could buy and why you're different — from M1 + Context]

#### Pricing & ROI
[Plans, pricing, ROI calculation framework — from M2]

#### Brand & Messaging
[Trust signals, positioning, tone — from M3]

#### Gaps
[What's missing that we need to ask the founder about]
```

### 4. Present Findings and Fill Gaps

Present the pitch brief to the user:
- "Here's what I extracted from your founder documents, viewed through a buyer's lens:"
- Show the compiled brief
- Highlight the **Gaps** section: "I still need the following to build a pitch a buyer would take seriously:"
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
- Context-distill invoked separately for each milestone
- Pitch brief compiled with CLIENT-focused framing (their problem, not your features)
- Gaps identified and filled through targeted questions
- User confirms brief accuracy

❌ **FAILURE:**
- Framing content from the vendor's perspective instead of the buyer's
- Asking questions already answered in founder documents
- Missing available milestone folders
