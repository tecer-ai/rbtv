---
name: 'step-03-key-messages'
description: 'Create 3-5 audience-specific key messages with traceability'
nextStepFile: './step-04-proof-points.md'
outputFile: '{outputFolder}/messaging-architecture.md'
---

# Step 3: Create Key Messages

**Progress: Step 3 of 6** — Next: Build Proof Points

---

## STEP GOAL

For each major audience, define 3-5 key messages that support the brand promise. Each message must trace to a validated assumption or framework output.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Features are NOT messages. "We have real-time analytics" is a feature. "Your team ships decisions in hours, not weeks" is a message. Reject feature lists disguised as messaging.

### Step-Specific Rules
- Each message MUST trace to a framework output or validated assumption
- Messages MUST use customer language from JTBD, not internal vocabulary
- Each audience gets 3-5 DISTINCT messages — no overlap within audience
- Messages are outcomes/beliefs/emotional shifts — NOT capabilities

---

## CONTEXT TO LOAD

1. Read complete `{outputFolder}/messaging-architecture.md` from Steps 1-2
2. Load upstream framework outputs:
   - Brand Promise (from Step 2)
   - JTBD analysis (job stories, forces, customer language)
   - Brand Prism (all facets for consistency check)
   - Lean Canvas (Customer Segments, UVP, Problem)
   - M2 Validation findings (validated assumptions)
   - Brand Archetypes (themes, narrative patterns — optional)

---

## MANDATORY SEQUENCE

### 1. Define Audiences

Establish the primary audiences. For most startups:

```markdown
## Audience Definitions

| Audience | Description | What They Care About | Primary Source |
|----------|-------------|---------------------|----------------|
| Early Adopters | [Who] | [Pain severity, tolerance] | JTBD primary job, push forces |
| Mainstream Customers | [Who] | [Job completion, anxieties] | JTBD related jobs, pull forces |
| Partners | [Who] | [Reach, integration] | Lean Canvas Channels |
| Investors | [Who] | [Market, metrics] | Lean Canvas Problem, M2 TAM |
```

Present to user for confirmation. Add or remove audiences as needed.

### 2. Extract Audience Concerns

For each audience, pull relevant content from upstream frameworks:

**Early Adopters:**
- JTBD primary job: [job]
- Push forces (pain with status quo): [forces]
- Emotional job: [emotional need]

**Mainstream Customers:**
- JTBD related jobs: [jobs]
- Pull forces (attraction to new solution): [forces]
- Anxieties: [concerns]

**Partners:**
- Lean Canvas Channels: [channels]
- Unfair Advantage: [advantage]
- Integration opportunities: [opportunities]

**Investors:**
- Lean Canvas Problem: [problem]
- Customer Segments: [segments]
- M2 TAM/SAM/SOM: [market size]

Present extracted concerns for each audience.

### 3. Draft Key Messages Per Audience

For each audience, draft 3-5 messages that:
1. Support the brand promise (trace upward)
2. Address what that audience cares about
3. Use language the audience uses (from JTBD)

**Message format:**
```markdown
### [Audience Name] Messages

**Brand Promise:** [reference]

| # | Key Message | Traceability | Addresses |
|---|-------------|--------------|-----------|
| 1 | "[Message]" | [Source: JTBD primary job] | [Which concern] |
| 2 | "[Message]" | [Source: M2 validated assumption #X] | [Which concern] |
| 3 | "[Message]" | [Source: Lean Canvas UVP] | [Which concern] |
| 4 | "[Message]" | [Source: JTBD push force] | [Which concern] |
| 5 | "[Message]" | [Source: Working Backwards] | [Which concern] |
```

Draft for each audience before proceeding.

### 4. Apply Quality Filters

For each message, verify:

**Filter 1: Not a feature**
- Does it describe an outcome, belief, or emotional shift?
- NOT a capability or specification

**Filter 2: Has traceability**
- Can you cite the specific framework output?
- If no source, mark as hypothetical

**Filter 3: No overlap**
- Is it distinct from other messages for this audience?
- If substantial overlap, merge or cut

**Filter 4: Customer language**
- For early adopter messages: uses verbatim JTBD language?
- Not internal jargon?

Present filter results for each audience.

### 5. Brand Prism Consistency Check

For each message, verify alignment with:
- Culture facet: Does message align with brand values?
- Personality facet: Does message match brand character?
- Relationship facet: Does message fit brand-customer dynamic?

If any message contradicts Brand Prism:
> "⚠️ Message [N] contradicts Prism [facet]: [explanation]
> Revise message to align (do NOT revise Prism)."

### 6. Build Audience-Message Matrix

Compile final messages into matrix:

```markdown
## Key Messages

### Audience-Message Matrix

| Audience | Message 1 | Message 2 | Message 3 | Message 4 | Message 5 |
|----------|-----------|-----------|-----------|-----------|-----------|
| Early Adopters | [M1] | [M2] | [M3] | [M4] | — |
| Mainstream | [M1] | [M2] | [M3] | [M4] | [M5] |
| Partners | [M1] | [M2] | [M3] | — | — |
| Investors | [M1] | [M2] | [M3] | [M4] | — |

### Detailed Messages

#### Early Adopters

1. **"[Message]"**
   - Traceability: [Source]
   - Addresses: [Concern]

[Continue for all audiences...]
```

Update messaging-architecture.md with this section.

### 7. Update Output Document

Update messaging-architecture.md frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise', 'step-03-key-messages']
```

### 8. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine messages further
- **[C] Continue** — proceed to Build Proof Points

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify Key Messages section is complete
2. Verify all messages have traceability annotations
3. Load `./step-04-proof-points.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 3-5 distinct messages per audience, all traced to sources, customer language used, no features, Prism-consistent

❌ **FAILURE:** Features disguised as messages, missing traceability, internal jargon, overlapping messages, Prism contradictions
