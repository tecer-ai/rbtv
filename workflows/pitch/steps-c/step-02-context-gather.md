---
stepNumber: 2
stepName: 'context-gather'
nextStepFile: ./step-03-narrative.md
---

# Step 02: Context Gathering from Founder Documents

**Progress: Step 2 of 10** — Next: Narrative Draft

---

## STEP GOAL

**If pitch_type = investor:**
Extract pitch-relevant content from founder documents by running context-distill separately for each milestone. Accumulate a pitch brief that feeds the narrative drafting step.

**If pitch_type = client:**
Extract pitch-relevant content from founder documents by running context-distill separately for each milestone. Focus on what a CLIENT buyer cares about: their problem, your solution, proof it works, and why you vs. alternatives.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

**If pitch_type = investor:**
You are The Investor mining founder documents for the strongest possible pitch material. Think like a partner reviewing a deal memo — what would make you champion this in the Monday meeting?

**If pitch_type = client:**
You are The Buyer mining founder documents for the content that would convince a procurement committee. Think like a VP evaluating a vendor — what would make you put this on the shortlist?

### Step-Specific Rules

- Run context-distill SEPARATELY for each milestone — each milestone contains different frameworks
- Do NOT ask the founder questions already answered in their documents
- Accumulate findings into a structured pitch brief

**If pitch_type = investor:**
- Use investor-focused search queries

**If pitch_type = client:**
- Use CLIENT-FOCUSED search queries (not investor-focused)

---

## MANDATORY SEQUENCE

### 1. Identify Available Milestones

Read the project-memo.md `stepsCompleted` array to identify which milestones have completed frameworks.

Check which milestone folders contain documents:
```
{output_path}/{project_name}/business-innovation/m1-conception/
{output_path}/{project_name}/business-innovation/m2-validation/
{output_path}/{project_name}/business-innovation/m3-brand/
{output_path}/{project_name}/business-innovation/m4-prototypation/
{output_path}/{project_name}/business-innovation/m5-market-validation/
{output_path}/{project_name}/business-innovation/m6-mvp/
```

Also check for a context folder:
```
{output_path}/{project_name}/context/
```

List which folders have .md files. Only search folders that contain documents.

### 2. Run Context-Distill Per Milestone

For EACH milestone folder that has documents, invoke the **context-distill** subagent. Provide these three inputs per call:

**If pitch_type = investor:**

**M1 — Conception:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract: (1) the core problem statement and who experiences it, with any quantified data; (2) the solution's key differentiators (max 3); (3) target customer profile and their current workarounds; (4) competitive positioning — named competitors and differentiation claims; (5) primary value proposition; (6) any contrarian market insights"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m1-conception/`

**M2 — Validation:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract: (1) TAM, SAM, SOM numbers with methodology; (2) unit economics — pricing, CAC, LTV, payback period, margins; (3) technology readiness level; (4) key assumptions tested and their results; (5) leap-of-faith assumptions with evidence status; (6) traction metrics with dates"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m2-validation/`

**M3 — Brand:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract: (1) brand archetype name and core personality traits; (2) primary positioning statement; (3) color palette hex values and typography choices; (4) primary tagline or brand statement; (5) communication tone descriptors"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m3-brand/`

**M4+ — Later Milestones (if they have documents):**
- Adapt the specific request to the milestone's focus (prototypation → product screenshots/demo; market validation → traction data; MVP → product metrics)

**Context folder (if exists):**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract: (1) market research data points with sources; (2) named competitors and their positioning; (3) industry trends supporting 'why now' timing; (4) customer quotes or feedback verbatim; (5) traction proof points with numbers and dates"
- Referenced Files: All .md files in `{output_path}/{project_name}/context/`

**Project Memo:**
- Conversation Context: "Building an investor pitch deck for {project_name}"
- Specific Request: "Extract: (1) one-line project description; (2) problem statement; (3) solution summary; (4) tenets list; (5) current milestone status"
- Referenced Files: `{output_path}/{project_name}/business-innovation/project-memo.md`

**If pitch_type = client:**

**M1 — Conception:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract: (1) the specific problem the TARGET CLIENT experiences and their current workarounds; (2) solution benefits stated from the client's perspective (max 5); (3) how the solution works — workflow, process, integration points; (4) named competitive alternatives the client might evaluate; (5) primary value proposition from the buyer's POV; (6) jobs-to-be-done the client hires this product for"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m1-conception/`

**M2 — Validation:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract: (1) pricing structure and plan tiers; (2) ROI metrics or calculation framework; (3) implementation timeline and effort estimate; (4) pilot results or validation data with numbers; (5) technology readiness and reliability evidence"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m2-validation/`

**M3 — Brand:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract: (1) brand positioning relative to named competitors; (2) key messaging statements for B2B buyers; (3) trust signals and credibility markers; (4) communication tone descriptors; (5) primary tagline or brand statement"
- Referenced Files: All .md files in `{output_path}/{project_name}/business-innovation/m3-brand/`

**M4+ — Later Milestones (if they have documents):**
- Adapt the specific request (prototypation → product demo/screenshots; market validation → client testimonials/case studies; MVP → product metrics/uptime)

**Context folder (if exists):**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract: (1) customer feedback or testimonials verbatim; (2) case study material — client name, problem, result; (3) named competitors and their positioning from the buyer's view; (4) industry benchmarks the client would recognize; (5) proof points with numbers and dates"
- Referenced Files: All .md files in `{output_path}/{project_name}/context/`

**Project Memo:**
- Conversation Context: "Building a client pitch deck for {project_name} targeting {target_client}"
- Specific Request: "Extract: (1) one-line project description; (2) problem statement; (3) solution summary; (4) tenets list; (5) current milestone status relevant to client readiness"
- Referenced Files: `{output_path}/{project_name}/business-innovation/project-memo.md`

### 3. Compile Pitch Brief

After ALL context-distill calls complete, compile findings into a structured pitch brief:

**If pitch_type = investor:**
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

**If pitch_type = client:**
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

**If pitch_type = investor:**
Present the pitch brief to the user:
- "Here's what I extracted from your founder documents:"
- Show the compiled brief
- Highlight the **Gaps** section: "I still need the following to build a strong narrative:"
- Ask ONLY for the missing information

**If pitch_type = client:**
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
- Context-distill invoked separately for each milestone with documents
- Pitch brief compiled with findings organized appropriately
- Gaps identified and filled through targeted questions only
- User confirms brief accuracy

**If pitch_type = investor:**
- Findings organized by deck section

**If pitch_type = client:**
- CLIENT-focused framing (their problem, not your features)

❌ **FAILURE:**
- Running a single context-distill for all documents (must be per milestone)
- Asking questions already answered in founder documents
- Missing available milestone folders
- Fabricating content not found in documents

**If pitch_type = client:** Additionally:
- Framing content from the vendor's perspective instead of the buyer's
