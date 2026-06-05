---
name: 'step-02-competitor-id'
description: 'Identify direct and indirect competitors via web research'
nextStepFile: './step-03-benchmarking.md'
outputFile: '{outputFolder}/competitive-landscape.md'
---

# Step 2: Competitor Identification

**Progress: Step 2 of 5** — Next: Geographic & Cross-Industry Benchmarking

---

## STEP GOAL

Map the current competitive landscape in the target market, including direct competitors, indirect alternatives, and reasons for non-consumption — all verified via web research.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Every competitor claim must include a source URL. Challenge any assertion without verification.

### Step-Specific Rules
- MUST use web-research tool for all competitor identification
- All competitor entries MUST include source URLs
- Identify at least 5 direct competitors and 5 indirect alternatives
- Do NOT skip non-consumption analysis

---

## CONTEXT BOUNDARIES

**Available context:**
- Output document from Step 1
- Working Backwards customer definition
- JTBD job definition and current alternatives

**Out of scope:**
- Deep competitor analysis (Step 4)
- Positioning and white space (Step 4)
- Threats and opportunities (Step 5)

---

## MANDATORY SEQUENCE

### 1. Gather Search Context

From JTBD and Working Backwards, identify:
- Primary customer segment
- Core problem being solved
- Industry/category terms
- Known alternatives from JTBD "current hiring"

Ask founder: "What competitors are you already aware of? What search terms would your customers use?"

### 2. Search for Direct Competitors

**WEB SEARCH REQUIRED:**

Execute searches:
- "[problem] software/solution"
- "[industry] [problem] tools"
- "alternatives to [known competitor]"
- "best [category] for [customer segment]"

For each competitor found, capture in a table:

| Competitor | Positioning | Target Customer | Pricing Model | Key Features | Source URL |
|------------|-------------|-----------------|---------------|--------------|------------|
| ... | ... | ... | ... | ... | [URL] |

Target: At least **5 direct competitors** with verified current information.

### 3. Identify Indirect Alternatives

From JTBD analysis and web research, identify what customers currently "hire":

| Alternative Category | How It Addresses the Job | Limitations | Source |
|---------------------|-------------------------|-------------|--------|
| Other product categories | ... | ... | [URL or JTBD] |
| Workarounds (spreadsheets, email) | ... | ... | [URL or JTBD] |
| Professional services | ... | ... | [URL or JTBD] |
| Internal solutions (custom builds) | ... | ... | [URL or JTBD] |

Target: At least **5 indirect alternatives**.

### 4. Analyze Non-Consumption

Identify why some potential customers do nothing:

| Barrier | Explanation |
|---------|-------------|
| Awareness gaps | Don't know solutions exist |
| Cost/complexity barriers | Existing solutions too expensive or hard |
| Regulatory/organizational constraints | Cannot adopt due to rules |
| Inertia and habit strength | Change effort exceeds perceived benefit |

Present to founder: "Based on research, here are the reasons customers might not adopt any solution..."

### 5. Update competitive-landscape.md

Add Section 1 content:

```markdown
## 1. Current Alternatives Inventory

### 1.1 Direct Competitors

| Competitor | Positioning | Target Customer | Pricing Model | Key Features | Source URL |
|------------|-------------|-----------------|---------------|--------------|------------|
| {competitor} | {positioning} | {segment} | {pricing} | {features} | [{source}](URL) |

### 1.2 Indirect Alternatives

| Alternative Category | How It Addresses the Job | Limitations | Source |
|---------------------|-------------------------|-------------|--------|
| {category} | {how} | {limitations} | [{source}](URL) |

### 1.3 Non-Consumption

**Why some customers do nothing:**

- **Awareness:** {explanation}
- **Cost/Complexity:** {explanation}
- **Regulatory/Organizational:** {explanation}
- **Inertia:** {explanation}
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-competitor-id']
```

### 6. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Geographic & Cross-Industry Benchmarking

**Menu handling:** When [P] is selected, execute {partyModeWorkflow} then redisplay this menu. When [C] is selected, proceed per CRITICAL STEP COMPLETION NOTE below.

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append Section 1 content to competitive-landscape.md
2. Update frontmatter: add `step-02-competitor-id` to `stepsCompleted`
3. Load `./step-03-benchmarking.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** At least 5 direct competitors and 5 indirect alternatives identified, all with source URLs, non-consumption analyzed

❌ **FAILURE:** Listing competitors without source URLs, using training data without verification, skipping indirect alternatives
