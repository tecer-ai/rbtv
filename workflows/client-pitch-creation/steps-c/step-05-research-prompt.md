---
stepNumber: 5
stepName: 'research-prompt'
nextStepFile: ./step-06-structure.md
outputFile: pitch-research-prompt.md
promptingKnowledgeIndex: '{project-root}/_bmad/rbtv/workflows/prompting-assistance/data/knowledge-index.csv'
webResearchStandards: '{project-root}/_bmad/rbtv/tasks/data/web-research-standards.md'
---

# Step 05: Research Prompt Generation

**Progress: Step 5 of 9** — Next: Slide Structure

---

## STEP GOAL

Generate two research prompts for an external AI: one to find proof points supporting the pitch, one to research buyer objections and competitive positioning. Adapt the prompts to the target AI model. Collaboratively select which context documents to provide alongside the prompt.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer crafting a research brief. The research prompt must be broad enough that the researching AI can actually find relevant proof (the exact case studies and benchmarks discussed in Step 04 may not exist — the prompt must give the AI room to find adjacent, proxy, or alternative evidence). Think of it as briefing an analyst: give them the direction and the standards, not a shopping list.

### Step-Specific Rules

- Research queries must be BROADER than the specific proof discussed in Step 04
- The researching AI doesn't know the pitch narrative — the prompt must provide enough context without bloating the context window
- The prompt must embed the web-research-standards so the researching AI follows them
- Objection research must be genuinely adversarial — surface real competitive threats and buyer concerns
- Context documents are provided AS FILES alongside the prompt, not pasted into it

---

## MANDATORY SEQUENCE

### 1. Ask Target AI Model

Ask the user:
"Which AI will run this research? This matters because I'll adapt the prompt to that model's strengths."

Present available models from the prompting knowledge index. Common options:
- Claude (Projects, extended thinking)
- GPT-5 (ChatGPT Projects)
- Gemini (Deep Research)
- Manus (autonomous agent)
- Other (user specifies)

Wait for selection. Set {target_model}.

### 2. Load Model-Specific Guidance

Load `{promptingKnowledgeIndex}` (knowledge-index.csv).

Find the entry for {target_model} and load the corresponding model-specific prompting guide. Extract:
- Model's strengths and weaknesses for research tasks
- Preferred prompt structure for this model
- Any model-specific techniques
- Context window considerations
- Platform-specific guidance if applicable

### 3. Load Web Research Standards

Load `{webResearchStandards}`. These standards must be embedded in the research prompt so the researching AI follows them.

### 4. Select Context Documents

Discuss with the user which founder documents to provide to the researching AI alongside the prompt:

"The researching AI needs context to understand what it's researching — but too much context bloats its window and dilutes focus. Let's pick the minimum set."

**Recommend including:**
- The pitch-narrative.md (so it understands the pitch structure and proof needs)
- Project memo (for company overview)

**Discuss whether to include:**
- Competitive landscape document (if it exists — highly relevant for client pitches)
- Specific customer feedback or testimonial documents
- Pricing/unit economics documents

**Recommend EXCLUDING:**
- Brand/visual documents (irrelevant to proof research)
- Internal strategy documents (the buyer doesn't see these)
- Any document whose content is already captured in the pitch narrative

Present the recommended document list. Let the user add or remove. Final list becomes the context package.

### 5. Generate Proof-Support Research Prompt

Create the research prompt adapted to {target_model}:

Structure the prompt with:
1. **Role/Context** — Brief description: research proof points for a client/sales pitch
2. **Company Context** — Short paragraph about the company and what it sells (extracted from pitch brief — NOT the full narrative inline)
3. **Target Client Profile** — Who the pitch is for, their industry, their role
4. **Research Objectives** — Broad research areas derived from the data layer, written as open-ended questions:
   - Industry benchmarks and cost-of-status-quo data
   - Case studies or success stories from similar solutions (even competitors')
   - ROI frameworks and payback period evidence
   - Implementation success rates and timelines in this space
   - Client satisfaction and retention metrics for this category
   - Industry analyst opinions on this solution category
5. **Research Standards** — Embed the full web-research-standards
6. **Output Format** — Organized by pitch slide, with citations
7. **Context Documents** — List which files will be provided alongside this prompt

**Critical: Breadth over precision.** For each proof need from Step 04, broaden it:
- Instead of "Find a case study from company X" → "Find case studies or success stories from companies using solutions similar to {product} in {industry}, including implementation details and measurable outcomes"
- Instead of "Find the average ROI for X" → "Research ROI benchmarks and cost-benefit analyses for {solution category}, including total cost of ownership comparisons with manual/legacy approaches"
- Instead of "Find G2 reviews for X" → "Research buyer sentiment and adoption trends for {solution category}, including analyst reports, review platforms, and industry surveys"

### 6. Generate Objection Research Prompt

Create a separate adversarial research prompt:

"This prompt is for surfacing the objections and competitive threats a buyer's procurement team will raise. The vendor should have answers ready before the meeting."

Structure:
1. **Role** — "You are a procurement analyst conducting vendor evaluation. Your job is to find reasons to choose a competitor or delay the purchase."
2. **Company Context** — Same brief context as proof prompt
3. **Research Objectives** — Derived from the buyer-objections table in Step 04, but broadened:
   - Competitive alternatives and their strengths (specific competitors if known)
   - Hidden costs and total cost of ownership concerns
   - Implementation risks and failure stories in this category
   - Vendor lock-in risks and switching costs
   - Market maturity — is this a proven category or emerging/risky?
   - Security, compliance, and regulatory concerns for this solution type
   - Common reasons companies abandon or switch away from solutions like this
4. **Research Standards** — Same web-research-standards
5. **Output Format** — Organized by objection category, with severity assessment
6. **Context Documents** — Same context package as proof prompt

### 7. Save Research Prompts

Save to: `{output_folder}/pitch-research-prompt.md`

Format:
```markdown
---
project: {project_name}
type: client
target: {target_client}
target_model: {target_model}
date: {date}
context_documents:
  - {doc1 path}
  - {doc2 path}
---

# Client Pitch Research Prompts: {project_name}

## Instructions

1. Open {target_model} ({platform if applicable})
2. Upload/attach the context documents listed above
3. Run the Proof-Support prompt first
4. Run the Objection Research prompt second
5. Save both outputs and bring them back to the pitch deck workflow

---

## Prompt 1: Proof-Support Research

{complete prompt text}

---

## Prompt 2: Buyer Objection Research

{complete prompt text}
```

### 8. Remind User About Narrative Impact

"When the research comes back, review it before we continue building the deck. The proof might confirm your narrative — or it might reveal gaps. Maybe a competitor has stronger case studies in this vertical. Maybe the ROI benchmarks are lower than you'd like. That's why we're doing this now, not after the deck is designed."

### 9. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to slide structure (user will run research separately and may revisit narrative later)
- **[X] Exit** — exit workflow (research prompts are saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}`

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Target AI model identified and model-specific guidance applied
- Research queries are BROADER than the specific proof points (room for the AI to find what's available)
- Web research standards embedded in prompts
- Objection research is genuinely adversarial (competitive threats, implementation risks)
- Context documents selected collaboratively (minimal but sufficient)
- Prompts adapted to target model's strengths

❌ **FAILURE:**
- Prompts are a shopping list of exact case studies (too narrow)
- Missing web research standards
- Objection research is soft or perfunctory
- Using investor-focused research framing (TAM/SAM) instead of buyer-focused (ROI, TCO, case studies)
- Not adapting to the target AI model
