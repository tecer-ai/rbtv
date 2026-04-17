---
name: 'step-04-map'
description: 'Create perceptual map with competitor positions and white space analysis'
nextStepFile: './step-05-test.md'
outputFile: '{outputFolder}/brand-positioning.md'
---

# Step 4: Create Perceptual Map

**Progress: Step 4 of 6** — Next: Validation Tests

---

## STEP GOAL

Build a two-dimensional visualization of competitive positioning that reveals white space and validates the brand's intended position is distinct.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Demand evidence for competitor positions — no guessing. Challenge whether white space represents real opportunity or dead zone.

### Step-Specific Rules
- At least 5 competitors/alternatives must be plotted
- MUST include "do nothing" option
- MUST include at least one indirect competitor
- White space must be analyzed for desirability, not just emptiness

---

## CONTEXT TO LOAD

1. Read `{outputFolder}/brand-positioning.md` with Inputs Brief and Draft Statement
2. Read `{outputFolder}/tam-sam-som.md` for competitive landscape
3. Access competitor websites, pricing pages, reviews if needed

---

## MANDATORY SEQUENCE

### 1. Select Map Dimensions

Present dimension options:

| Dimension Pair | Best For | Example |
|----------------|----------|---------|
| Simple ↔ Powerful | Productivity tools | Notion vs Excel |
| Self-serve ↔ Full-service | Service businesses | Stripe vs Traditional banking |
| Affordable ↔ Premium | Consumer products | IKEA vs Herman Miller |
| Generalist ↔ Specialist | Professional services | Fiverr vs Toptal |
| Automated ↔ Manual | Process tools | Zapier vs Custom dev |
| Individual ↔ Team | Collaboration software | Dropbox vs Slack |

Ask user to select or propose dimensions that:
1. **Customers actually use** to evaluate alternatives
2. **Spread competitors out** rather than clustering
3. **Connect to your differentiation** (Golden Circle How or Unfair Advantage)

### 2. Document Dimension Rationale

For each chosen dimension:

```markdown
### Axis Definitions

**X-Axis: [Dimension 1]**
- Left pole: [Definition]
- Right pole: [Definition]
- Why meaningful: [How customers use this to evaluate]
- How strategic: [Connects to our How/Advantage]

**Y-Axis: [Dimension 2]**
- Bottom pole: [Definition]
- Top pole: [Definition]
- Why meaningful: [How customers use this to evaluate]
- How strategic: [Connects to our How/Advantage]
```

### 3. List Competitors to Plot

From competitive landscape and Inputs Brief, list 5-8 entities:

| Entity | Type | Evidence Source |
|--------|------|-----------------|
| [Direct Competitor 1] | Direct | [Website, reviews, pricing] |
| [Direct Competitor 2] | Direct | [Website, reviews, pricing] |
| [Indirect Competitor] | Indirect (same job, different category) | [Analysis] |
| [Do Nothing] | Manual workaround | [Current customer process] |
| [Adjacent Solution] | Partial overlap | [Analysis] |

Require: At least 1 indirect competitor + "do nothing" option.

### 4. Plot Competitor Positions

For each competitor, determine position:

```markdown
### Competitor Positions

| Competitor | X Position (1-5) | Y Position (1-5) | Evidence |
|------------|------------------|------------------|----------|
| [Name] | [1-5] | [1-5] | [Source: website, reviews, etc.] |
| ... | | | |
```

**Scoring:**
- 1 = Extreme left/bottom pole
- 3 = Neutral center
- 5 = Extreme right/top pole

For each: Cite evidence. If lacking data, note uncertainty.

### 5. Plot Brand's Intended Position

Determine where your brand INTENDS to be (not necessarily where it is today):

```markdown
### Brand Position

**Intended Position:** X=[N], Y=[N]

**Rationale:**
- On [Dimension 1]: [Why this position connects to How/Advantage]
- On [Dimension 2]: [Why this position connects to How/Advantage]

**Current State vs Intended:**
- Are we already there? [Yes/No]
- Gap to close: [If no, what's needed]
```

### 6. Visualize the Map

Create text-based map:

```
                    [Dimension 2 High]
                          ^
                          |
           [Comp A]       |        [Comp B]
                          |
    [Dimension 1 Low] <---+---> [Dimension 1 High]
                          |
           [OUR BRAND]    |        [Comp C]
                          |
                          v
                    [Dimension 2 Low]
```

Or as coordinate table if visualization is complex.

### 7. Identify and Analyze White Space

Mark empty quadrants or positions:

```markdown
### White Space Analysis

**Identified White Space:**
1. [Location on map] — [Description of this position]

**Desirability Test:**
For each white space, ask:
- Is there a real customer need in this space?
- Or is it empty because nobody wants to be there?

| White Space | Customer Need? | Opportunity or Trap? | Evidence |
|-------------|----------------|----------------------|----------|
| [Location 1] | [Yes/No] | [Opportunity/Trap] | [Why] |
| ... | | | |
```

### 8. Verify Brand Position is Distinct

Check:
> "Is our intended position DISTINCT from every plotted competitor?"

If overlapping with any competitor:
- Identify which and why
- Consider adjusting positioning or highlighting differentiation dimension
- If can't distinguish, return to Step 3 to revise statement

### 9. Update Output Document

Add Perceptual Map section:

```markdown
## Perceptual Map

### Axis Definitions
[From Sequence 2]

### Competitor Positions
[From Sequence 4]

### Brand Position
[From Sequence 5]

### Visual Map
[From Sequence 6]

### White Space Analysis
[From Sequence 7]

### Distinctness Verification
[From Sequence 8]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-inputs', 'step-03-draft', 'step-04-map']
```

### 10. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Validation Tests

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify 5+ competitors plotted with evidence
2. Verify both dimensions have rationale
3. Verify brand position is distinct from all competitors
4. Load `./step-05-test.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** 5+ competitors plotted with evidence, dimensions are strategic and customer-relevant, brand position is distinct, white space analyzed for desirability

❌ **FAILURE:** Fewer than 5 competitors, guessed positions without evidence, overlapping with competitor, skipping white space analysis
