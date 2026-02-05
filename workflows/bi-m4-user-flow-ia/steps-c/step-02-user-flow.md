---
name: 'step-02-user-flow'
description: 'Map primary user journey from entry to conversion'
nextStepFile: './step-03-information-architecture.md'
outputFile: '{outputFolder}/user-flow-ia.md'
---

# Step 2: User Flow Mapping

**Progress: Step 2 of 4** — Next: Information Architecture

---

## STEP GOAL

Map the complete user journey from entry point to conversion goal, identifying screens, decision points, and drop-off risks.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor focused on conversion. Challenge flows that bury the CTA, demand clarity at every decision point. If a user can't understand what to do next in 3 seconds, the flow is broken.

### Step-Specific Rules
- Every flow MUST have exactly ONE primary conversion goal
- CTA MUST be reachable in 3 clicks or fewer
- No navigation menus on landing pages — they are escape routes
- Document ALL exit points and drop-off risks

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/user-flow-ia.md` for artifact type from Step 1
2. Review M1 outputs for customer journey understanding (Working Backwards, JTBD)
3. Review M3 outputs for messaging hierarchy (if available)

---

## MANDATORY SEQUENCE

### 1. Define Conversion Goal

Ask user to specify the single conversion goal:

> "What specific action should visitors take?
>
> Common conversion goals:
> - **Email signup** — Capture lead for nurturing
> - **Content download** — Exchange value for contact info
> - **Demo request** — Qualify interested prospects
> - **Purchase** — Direct transaction
> - **Quote request** — Start sales conversation
>
> What is YOUR primary conversion goal for this prototype?"

**Capture:**
- Conversion action (what user does)
- Success metric (how we measure)
- Business value (why this matters)

### 2. Map Entry Points

Ask about how users will arrive:

> "How will visitors reach this prototype?
>
> | Entry Type | User Mindset | Design Implication |
> |------------|--------------|-------------------|
> | Paid ad | Problem-aware, seeking solution | Hero must match ad promise |
> | Organic search | Researching, comparing | Establish credibility fast |
> | Social media | Curious, easily distracted | Hook attention in 3 seconds |
> | Email campaign | Already engaged | Can skip awareness, go to action |
> | Direct/referral | Pre-sold by referrer | Validation focus, easy conversion |
>
> What are the PRIMARY entry points for your prototype?"

Document each entry point with user mindset and design implications.

### 3. Map User Flow Screens

Based on artifact type, guide screen mapping:

**For Landing Page:**
```
Entry Point
    ↓
Hero Section (headline, subheadline, primary CTA)
    ↓
Benefits Section (3-5 key benefits)
    ↓
Social Proof Section (testimonials, logos, metrics)
    ↓
Final CTA Section (repeat conversion opportunity)
    ↓
Conversion (form submit / button click)
```

**For Website:**
```
Entry Point
    ↓
Homepage (overview, navigation)
    ↓
Category/Feature Pages (details)
    ↓
Detail/Product Page (specifics)
    ↓
Conversion Page (checkout, signup)
    ↓
Confirmation
```

**For Infographic:**
```
Entry Point
    ↓
Hero Section (title, key stat)
    ↓
Section 1-N (content blocks)
    ↓
CTA/Footer
```

Ask user to confirm or customize the flow:

> "Based on your [artifact type], here's the standard flow:
>
> [Show appropriate flow]
>
> Does this match your needs, or do you need to customize?"

### 4. Identify Decision Points

For each screen, identify where users make choices:

> "At each screen, what decisions can users make?
>
> **Good decisions:** Move toward conversion
> **Risky decisions:** Navigate away, compare, delay
>
> Let's map decision points..."

Document each decision point:
- Location (which screen)
- Options available
- Desired path
- Risk of abandonment

### 5. Document Exit Points & Drop-off Risks

For each screen, identify where users might leave:

> "Where might users abandon the journey?
>
> Common drop-off causes:
> - Unclear value proposition (bounce from hero)
> - Too much friction (long forms, complex steps)
> - Missing information (unanswered questions)
> - Trust concerns (no social proof)
> - Distractions (competing links, navigation)
>
> For each screen, what could cause a user to leave?"

### 6. Validate Flow Against Rules

Check flow against conversion principles:

| Rule | Check |
|------|-------|
| Single conversion goal | Only one primary CTA action |
| 3-click rule | Conversion reachable in ≤3 clicks |
| CTA above fold | Primary CTA visible without scrolling (mobile) |
| No escape routes | No navigation menu (landing page) |
| Clear next action | Every screen has obvious next step |

Present validation:

> "**Flow Validation:**
>
> ✅/❌ Single conversion goal: [status]
> ✅/❌ 3-click rule: [status]
> ✅/❌ CTA above fold: [status]
> ✅/❌ No escape routes: [status]
> ✅/❌ Clear next action: [status]
>
> [Fix any issues before proceeding]"

### 7. Update Output Document

Update user-flow-ia.md with User Flow section:

```markdown
## User Flow Map

### Conversion Goal
**Action:** [what user does]
**Metric:** [how we measure]
**Value:** [why this matters]

### Entry Points
| Entry Type | User Mindset | Design Implication |
|------------|--------------|-------------------|
| [type] | [mindset] | [implication] |

### Flow Diagram
```
[ASCII diagram of flow]
```

### Screen Details
| Screen | Purpose | Primary Element | CTA |
|--------|---------|-----------------|-----|
| [name] | [purpose] | [element] | [cta] |

### Decision Points
| Location | Options | Desired Path | Risk |
|----------|---------|--------------|------|
| [screen] | [options] | [path] | [risk] |

### Exit Points & Drop-off Risks
| Screen | Exit Risk | Mitigation |
|--------|-----------|------------|
| [screen] | [risk] | [mitigation] |

### Validation
- [x] Single conversion goal
- [x] 3-click rule
- [x] CTA above fold (mobile)
- [x] No escape routes (landing page)
- [x] Clear next action per screen
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-user-flow']
```

### 8. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Information Architecture
- **[R] Revise** — modify user flow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Ensure user-flow-ia.md has User Flow Map section complete
2. Verify `step-02-user-flow` is in `stepsCompleted`
3. Load `./step-03-information-architecture.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Conversion goal defined, flow mapped, decision points documented, exit risks identified, validation passed

❌ **FAILURE:** Multiple competing goals, CTA not above fold, >3 clicks to conversion, escape routes on landing page, unclear next actions
