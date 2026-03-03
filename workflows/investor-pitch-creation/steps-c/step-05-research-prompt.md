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

Generate two research prompts for an external AI: one to find data supporting the pitch thesis, one to find data that could kill it. Adapt the prompts to the target AI model. Collaboratively select which context documents to provide alongside the prompt.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Investor crafting a research brief. The research prompt must be broad enough that the researching AI can actually find data (the exact data points discussed in Step 04 may not exist — the prompt must give the AI room to find adjacent, proxy, or alternative data). Think of it as briefing a junior analyst: give them the direction and the standards, not a shopping list of exact numbers.

### Step-Specific Rules

- Research queries must be BROADER than the specific data discussed in Step 04
- The researching AI doesn't know the pitch narrative — the prompt must provide enough context without being so large it bloats the context window
- The prompt must embed the web-research-standards so the researching AI follows them
- Counter-thesis prompt must be genuinely adversarial — not a softball
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
- Any model-specific techniques (e.g., Claude's extended thinking, Gemini's search grounding)
- Context window considerations
- Platform-specific guidance if applicable (e.g., Claude Projects, ChatGPT Projects)

### 3. Load Web Research Standards

Load `{webResearchStandards}`. These standards must be embedded in the research prompt so the researching AI follows them.

### 4. Select Context Documents

Discuss with the user which founder documents to provide to the researching AI alongside the prompt:

"The researching AI needs context to understand what it's researching — but too much context bloats its window and dilutes focus. Let's pick the minimum set of documents that give it what it needs."

**Recommend including:**
- The pitch-narrative.md (so it understands the pitch structure and data needs)
- Project memo (for company overview and stage)

**Discuss whether to include:**
- Specific milestone documents (only if they contain unique context the AI needs)
- Context folder documents (market research, competitive intel)

**Recommend EXCLUDING:**
- Brand/visual documents (irrelevant to data research)
- Prototypation documents (unless product-specific data is needed)
- Any document whose content is already captured in the pitch narrative

Present the recommended document list. Let the user add or remove. Final list becomes the context package.

### 5. Generate Thesis-Support Research Prompt

Create the research prompt adapted to {target_model}:

Structure the prompt with:
1. **Role/Context** — Brief description of the research task and why
2. **Company Context** — A short paragraph about the company (extracted from pitch brief — NOT the full narrative pasted inline; the narrative will be a separate context document)
3. **Research Objectives** — Broad research areas derived from the data layer, but written as open-ended research questions, NOT as specific number requests
4. **Research Standards** — Embed the full web-research-standards (or reference them if the model supports file references)
5. **Output Format** — How to structure findings (organized by pitch slide, with citations)
6. **Context Documents** — List which files will be provided alongside this prompt

**Critical: Breadth over precision.** For each data need from Step 04, broaden it:
- Instead of "Find the TAM for X in Brazil" → "Research the market size and growth dynamics for X in Latin America, with Brazil-specific data where available"
- Instead of "Find competitor Y's revenue" → "Map the competitive landscape for X, including key players, their scale, funding, and market positioning"
- Instead of "Find the CAGR for X" → "Identify growth trends and market drivers in the X industry, including historical growth rates and forward projections from credible sources"

### 6. Generate Counter-Thesis Research Prompt

Create a separate adversarial research prompt:

"This prompt is for finding data that could KILL the investment thesis. A smart VC will research these risks before the second meeting. The founder should know the answers first."

Structure:
1. **Role** — "You are a VC analyst conducting due diligence. Your job is to find reasons NOT to invest."
2. **Company Context** — Same brief context as thesis prompt
3. **Research Objectives** — Derived from the counter-thesis table in Step 04, but broadened:
   - Key risks to the business model
   - Market headwinds or declining trends
   - Competitive threats (larger players, well-funded competitors)
   - Regulatory risks
   - Technology risks
   - Historical failures in this space and why they failed
4. **Research Standards** — Same web-research-standards
5. **Output Format** — Organized by risk category, with severity assessment
6. **Context Documents** — Same context package as thesis prompt

### 7. Save Research Prompts

Save to: `{output_folder}/pitch-research-prompt.md`

Format:
```markdown
---
project: {project_name}
target_model: {target_model}
date: {date}
context_documents:
  - {doc1 path}
  - {doc2 path}
---

# Investor Pitch Research Prompts: {project_name}

## Instructions

1. Open {target_model} ({platform if applicable})
2. Upload/attach the context documents listed above
3. Run the Thesis-Support prompt first
4. Run the Counter-Thesis prompt second
5. Save both outputs and bring them back to the pitch deck workflow

---

## Prompt 1: Thesis-Support Research

{complete prompt text}

---

## Prompt 2: Counter-Thesis Research

{complete prompt text}
```

### 8. Remind User About Narrative Impact

"When the research comes back, review it before we continue building the deck. The data may confirm your narrative — or it may require changes. Slides where the data doesn't support the claim will need to be reworked. That's why we're doing this now, not after the deck is designed."

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
- Research queries are BROADER than the specific data points (room for the AI to find what's available)
- Web research standards embedded in prompts
- Counter-thesis prompt is genuinely adversarial
- Context documents selected collaboratively (minimal but sufficient)
- Prompts adapted to target model's strengths
- User warned about narrative impact

❌ **FAILURE:**
- Prompts are a shopping list of exact numbers (too narrow to yield results)
- Missing web research standards (output won't meet quality bar)
- Counter-thesis prompt is soft or perfunctory
- Pasting entire narrative/documents into the prompt body instead of referencing context files
- Not adapting to the target AI model
- Not discussing context document selection with user
