---
name: 'step-04-proof-points'
description: 'Attach evidence to each message'
nextStepFile: './step-05-ctas-journey.md'
outputFile: '{outputFolder}/messaging-architecture.md'
advancedElicitationTask: '{bmad_core}/workflows/advanced-elicitation/workflow.xml'
partyModeWorkflow: '{bmad_core}/workflows/party-mode/workflow.md'
---

# Step 4: Build Proof Points

**Progress: Step 4 of 6** — Next: CTAs & Journey

---

## STEP GOAL

For each key message, define 2-3 proof points that make the message credible. Proof points are evidence: data, customer quotes, features framed as benefits, or third-party validation. Flag messages with insufficient proof for M5 validation.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Unattributed proof points are opinions, not evidence. Claiming "customers love our product" without a specific quote, metric, or data point trains the audience to distrust your claims. Demand sources for everything.

### Step-Specific Rules
- Each message MUST have 2-3 proof points
- Each proof point MUST document: point, source, type, status (validated/hypothetical)
- Work through audiences ONE AT A TIME
- Flag messages with <2 validated proof points for M5 validation
- Proof points must not contradict Brand Prism

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/messaging-architecture.md` for key messages
2. Read `{outputFolder}/jobs-to-be-done.md` for customer quotes, workarounds, forces
3. Read `{outputFolder}/project-memo.md` M2 section for validation data (experiment results, survey data, interview findings)
4. Read `{outputFolder}/working-backwards.md` for claims, features, customer quote
5. Read `{outputFolder}/lean-canvas.md` for Solution block (top features/capabilities)
6. Optional: Read `{outputFolder}/problem-solution-fit.md` for before/after emotions, constraints

---

## MANDATORY SEQUENCE

### 1. Explain Proof Point Types

Present the four types of evidence:

> "For each message, we'll attach 2-3 proof points. Proof points are evidence that makes the message credible. Four types:
>
> 1. **Data points:** M2 validation results, survey percentages, experiment outcomes, market sizing numbers
>    - Example: '73% of early adopters in M2 survey reported reducing reporting time by 50%'
>
> 2. **Customer language:** Direct quotes from JTBD interviews (verbatim, not paraphrased)
>    - Example: '[Customer name]: "I was spending 4 hours every Friday on reports. Now it's 20 minutes."'
>
> 3. **Feature-as-benefit:** Product capability framed as what it enables for the customer
>    - Example: 'Automated report generation reduces reporting time from 4 hours to 20 minutes'
>    - NOT: 'We have automated reports' (that's just a feature)
>
> 4. **Third-party validation:** Industry analyst citations, press coverage, advisor endorsements, pilot results
>    - Example: 'Featured in TechCrunch as "Top 10 Productivity Tools for 2026"'
>
> Each proof point needs a documented source and status (validated vs. hypothetical)."

### 2. Build Proof Points for Early Adopter Messages

For each Early Adopter message, ask:

> "Message: '[message text]'
>
> Why should early adopters believe this? List every piece of evidence you currently have:
> - Data from M2 validation?
> - Customer quotes from JTBD interviews?
> - Features framed as benefits?
> - Third-party validation?"

For each proof point proposed:

**Document the proof point:**
- The proof point itself (one sentence)
- The source (which framework, interview, or data set)
- The type (data, customer quote, feature-benefit, third-party)
- The status (validated if from M2 validation or JTBD interviews, hypothetical if not yet tested)

**Example format:**
```
Proof Point: "73% of early adopters in M2 survey reported reducing reporting time by 50%"
Source: M2 Assumption Mapping validation experiment #3
Type: Data
Status: Validated
```

**Select strongest 2-3 proof points per message:**
- Most specific
- Most verifiable
- Most emotionally compelling to early adopters

If message has fewer than 2 credible proof points:

> "⚠️ **Insufficient Proof**
>
> This message has only [N] proof point(s). This is aspirational, not proven.
>
> Options:
> 1. Demote to 'future message' requiring M5 validation
> 2. Design M5 experiment to generate missing proof
>
> Which approach?"

Flag the message and record the gap.

Repeat for all Early Adopter messages.

### 3. Build Proof Points for Mainstream Customer Messages

Apply same process as Early Adopters:
- For each message, ask: "Why should mainstream customers believe this?"
- Document proof point, source, type, status
- Select strongest 2-3 per message
- Flag messages with insufficient proof

### 4. Build Proof Points for Partner Messages

Apply same process:
- For each message, ask: "Why should partners believe this?"
- Document proof point, source, type, status
- Select strongest 2-3 per message
- Flag messages with insufficient proof

### 5. Build Proof Points for Investor Messages

Apply same process:
- For each message, ask: "Why should investors believe this?"
- Document proof point, source, type, status
- Select strongest 2-3 per message
- Flag messages with insufficient proof

### 6. Cross-Check Against Brand Prism

For all proof points, verify:

> "Do any of these proof points contradict your Brand Prism Culture ([culture facets]) or Relationship ([relationship type])?"

Example contradiction: Citing aggressive competitive benchmarks if brand personality is collaborative.

If contradiction found, revise or remove the proof point.

### 7. Create Proof Point Library

Compile all proof points into a flat table:

```markdown
## Proof Point Library

| Audience | Message | Proof Point | Source | Type | Status |
|----------|---------|-------------|--------|------|--------|
| Early Adopters | [Message 1] | [Proof 1] | [Source] | [Type] | [Status] |
| Early Adopters | [Message 1] | [Proof 2] | [Source] | [Type] | [Status] |
| Early Adopters | [Message 2] | [Proof 1] | [Source] | [Type] | [Status] |
| ... | ... | ... | ... | ... | ... |

### Flagged Gaps

Messages lacking sufficient validated proof (require M5 validation):

1. [Audience] - [Message] - Current proof: [N] points, [N] validated
   - **Gap:** [What evidence is missing]
   - **M5 Experiment Needed:** [Suggested experiment to generate proof]

2. [Next flagged message if any]
```

### 8. Update Output Document

Update messaging-architecture.md Proof Point Library section with the table and flagged gaps.

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-brand-promise', 'step-03-key-messages', 'step-04-proof-points']
```

### 9. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to CTAs & Journey mapping
- **[R] Refine** — revise proof points for specific message
- **[A] Advanced Elicitation** — deeper exploration of available evidence

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure Proof Point Library is complete with all messages having 2-3 proof points
2. Ensure flagged gaps are documented with M5 experiment suggestions
3. Verify `step-04-proof-points` is in `stepsCompleted`
4. Load `./step-05-ctas-journey.md` and follow its instructions

When **[R] Refine** is selected:
- Ask which message to refine
- Return to that message's proof point section and re-elicit evidence
- Redisplay menu

When **[A] Advanced Elicitation** is selected:
- Ask deeper questions about available evidence sources, M2 validation data, or JTBD customer quotes
- After elicitation, redisplay menu

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Every message has 2-3 proof points with documented source/type/status, at least one proof point per message uses customer language from JTBD, at least one proof point per message references M2 validation data or concrete metric, messages with insufficient proof flagged with M5 experiment suggestions, no proof points contradict Brand Prism

❌ **FAILURE:** Proof points without documented sources, messages with fewer than 2 proof points not flagged, no customer language proof points, no M2 validation data proof points, proof points contradict Brand Prism, status (validated/hypothetical) not documented
