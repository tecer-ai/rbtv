---
name: 'step-02-identity'
description: 'Compile Brand Identity section from all M3 framework outputs'
nextStepFile: './step-03-visual.md'
outputFile: '{outputFolder}/brandbook.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 2: Brand Identity

**Progress: Step 2 of 5** — Next: Visual Guidelines

---

## STEP GOAL

Compile the Brand Identity section of the brandbook by synthesizing mission, vision, brand persona, target audience, brand values, and brand story from existing M3 and M1 framework outputs.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Every element in Brand Identity must trace directly to a framework output. Do NOT invent new brand elements — compile, distill, and present what already exists. Challenge the founder if they want to deviate from established framework decisions.

### Step-Specific Rules
- Every statement must cite its source framework
- Do NOT create visual elements — that is Step 3
- The founder reviews and approves each subsection before moving on
- If a framework output is ambiguous, present options and let the founder choose

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brandbook.md` (current state)
2. Read `{outputFolder}/golden-circle.md` for Why/How/What
3. Read `{outputFolder}/brand-archetypes.md` for persona and IS/NOT
4. Read `{outputFolder}/brand-prism.md` for all 6 facets
5. Read `{outputFolder}/brand-positioning.md` for positioning statement
6. Read `{outputFolder}/project-memo.md` for M1 context (JTBD, Lean Canvas, Working Backwards)

---

## MANDATORY SEQUENCE

### 1. Mission Statement

Distill from Golden Circle Why:

```markdown
### Mission Statement

{Company name} exists to {Golden Circle Why — reframed as present-tense mission}.

*Source: Golden Circle — Why*
```

Present to founder for approval. The mission must be:
- One sentence, present tense
- Action-oriented (what the company does, not what it aspires to)
- Grounded in the Golden Circle Why

### 2. Vision Statement

Distill from Golden Circle What (aspirational) and Brand Positioning:

```markdown
### Vision Statement

{Aspirational future state the brand aims to create — derived from Golden Circle What and Positioning}.

*Source: Golden Circle — What, Brand Positioning*
```

Present to founder for approval. The vision must be:
- One sentence, future-oriented
- Aspirational but achievable
- Distinct from the mission (mission = present purpose, vision = future state)

### 3. Brand Persona

Compile from Brand Archetypes and Brand Prism:

```markdown
### Brand Persona

**Archetype:** {Primary archetype name}

{2-3 sentence description of the brand as a character, drawn from archetype analysis}

**Personality Traits:**

| Trait | Expression |
|-------|------------|
| {Prism personality trait 1} | {How it manifests in brand behavior} |
| {Prism personality trait 2} | {How it manifests} |
| {Prism personality trait 3} | {How it manifests} |

**Brand Character IS / IS NOT:**

| IS | IS NOT |
|----|--------|
| {Word from archetype} | {Counter-word} |
| {Word} | {Counter-word} |
| {Word} | {Counter-word} |
| {Word} | {Counter-word} |

*Source: Brand Archetypes, Brand Prism — Personality Facet*
```

Present to founder for approval.

### 4. Target Audience

Compile from M1 JTBD and Lean Canvas:

```markdown
### Target Audience

**Primary Audience:** {From Lean Canvas — Customer Segments}

**Buyer Persona:**

| Attribute | Description |
|-----------|-------------|
| Demographics | {Age, location, profession — from JTBD and Lean Canvas} |
| Goals | {Functional and emotional jobs — from JTBD} |
| Challenges | {Pain points and anxieties — from JTBD forces} |
| Motivations | {Push/pull forces — from JTBD} |

**What They Care About:** {1-2 sentences from JTBD primary job}

*Source: M1 Jobs-to-be-Done, M1 Lean Canvas — Customer Segments*
```

Present to founder. Ask if additional audience segments should be added (reference Messaging Architecture audiences if different from primary).

### 5. Brand Values

Compile from Brand Prism Culture and Golden Circle How:

```markdown
### Brand Values

| Value | Meaning | Source |
|-------|---------|--------|
| {Value 1} | {What this means in practice} | Brand Prism — Culture |
| {Value 2} | {What this means in practice} | Golden Circle — How |
| {Value 3} | {What this means in practice} | {Source} |

*Source: Brand Prism — Culture Facet, Golden Circle — How*
```

Present to founder for approval.

### 6. Brand Story

Compile from Working Backwards and Golden Circle:

```markdown
### Brand Story

{2-3 paragraph narrative arc:
- Paragraph 1: The problem (from Working Backwards — customer pain, JTBD)
- Paragraph 2: The belief (from Golden Circle Why — why this matters)
- Paragraph 3: The solution (from Golden Circle How/What — how the brand addresses it)}

*Source: M1 Working Backwards, Golden Circle*
```

Present to founder for approval. The story must feel authentic and emotionally resonant, not like marketing copy.

### 7. Compile Brand Identity Section

After founder approves all subsections, update brandbook.md:

Replace the `## Brand Identity` placeholder with the compiled section containing all 6 subsections.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-identity']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — hand off to the design agent for Visual Guidelines
- **[A] Advanced Elicitation** — refine any subsection

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Brand Identity section is written to brandbook.md
2. Verify `step-02-identity` is in `stepsCompleted`

> **AGENT HANDOFF — Design Agent Required**
>
> Step 03 (Visual Guidelines) is owned by the **design agent (Vivian)**, not the current mentor agent. You cannot execute this step yourself.
>
> Instruct the user:
>
> *"Brand Identity is locked. Visual Guidelines — color palette, typography, logo, imagery, and iconography — require the design agent. To continue, invoke Vivian using the command `@bmad-rbtv-designer` and select **[BV] Brand Visual Identity**. She'll build the visual identity grounded in the brand frameworks we just compiled."*
>
> Do NOT load `{nextStepFile}` yourself. The design agent will load it.

When **[A] Advanced Elicitation** is selected:
- Ask which subsection to refine
- After refinement, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Mission, vision, persona, audience, values, and brand story compiled with source citations, founder approved each subsection, brandbook.md updated

❌ **FAILURE:** Inventing brand elements not in frameworks, skipping founder approval, missing source citations, creating visual elements in this step
