---
stepNumber: 3
stepName: 'extract'
nextStepFile: ./step-04-document.md
knowledgeFile: ./data/token-categories.md
---

# Step 03: Token Extraction

**Progress: Step 3 of 4** — Next: Documentation

---

## STEP GOAL

Systematically extract design tokens across all five categories from the screenshot.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Methodical, precise, context-aware.

### Step-Specific Rules

- Extract only visible tokens (no guessing)
- Document usage context for each token
- Identify patterns, not just individual values
- Capture creative interpretation alongside concrete values

---

## MANDATORY SEQUENCE

### 1. Visual Scan

Perform systematic visual scan of the screenshot:

1. Overall impression (3-5 seconds)
2. Color distribution
3. Typography hierarchy
4. Spacing rhythm
5. Layout structure

Report initial observations to user.

### 2. Extract Colors

Identify colors across categories:

| Category | What to Find |
|----------|--------------|
| Primary | Brand identity colors (1-3) |
| Secondary | Supporting palette |
| Neutral | Grays, blacks, whites |
| Accent | CTAs, highlights, states |
| Background | Section and card backgrounds |

For each color, document:
- Hex value: `#RRGGBB`
- Usage context: Where/how used
- Color relationships: Pairings, contrasts

### 3. Extract Typography

Identify typography patterns:

| Element | What to Capture |
|---------|-----------------|
| Font families | Primary, secondary, monospace |
| Heading sizes | H1-H6 sizes in px |
| Body text | Size, weight, line-height |
| Font weights | Which weights are used |

Document the type scale and hierarchy.

### 4. Extract Spacing

Identify spacing system:

| Element | What to Capture |
|---------|-----------------|
| Base unit | 4px or 8px typically |
| Scale | Multipliers (1x, 2x, 3x...) |
| Section gaps | Vertical space between sections |
| Component padding | Internal padding values |

Document spacing scale with usage.

### 5. Extract Layout

Identify structural patterns:

| Element | What to Capture |
|---------|-----------------|
| Grid columns | Count, gaps |
| Max-width | Content container width |
| Section patterns | Hero, features, CTA structures |
| Alignment | Left, center, right patterns |

### 6. Extract Visual Identity

Capture subjective qualities:

| Element | What to Capture |
|---------|-----------------|
| Brand tone | Professional, friendly, bold |
| Aesthetic style | Minimalist, maximalist, etc. |
| Border radius | 0px, 4px, 8px, pill |
| Shadows | None, subtle, pronounced |
| Density | Compact, comfortable, spacious |

### 7. Present Extraction Summary

Display extracted tokens organized by category.

Ask user: "Review the extracted tokens. Any adjustments needed?"

### 8. Update State

Add `step-03-extract.md` to `stepsCompleted` in output document frontmatter.

### 9. Present Menu Options

**Select an Option:**

- **[C] Continue** — Proceed to documentation (step-04)
- **[R] Refine** — Adjust specific token values
- **[X] Exit Workflow** — Save current state, exit

ALWAYS halt and wait for user selection.

---

## EXTRACTION TECHNIQUES

### Color Identification
- Dominant colors: Most prominent in layout
- Frequency: How often each appears
- Context: Where used (buttons, backgrounds, text)

### Typography Analysis
- Compare heading sizes to establish scale
- Note weight distribution across content types
- Identify type scale ratio if consistent

### Spacing Analysis
- Find smallest consistent unit (base)
- Map multipliers across the page
- Note section vs. component spacing

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:

1. Ensure frontmatter is updated with `step-03-extract.md` in `stepsCompleted`
2. Load `./step-04-document.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All five categories extracted
- Usage context documented for each token
- Patterns identified (not just individual values)
- User reviewed and confirmed tokens

❌ **FAILURE:**
- Guessing values not visible in screenshot
- Missing usage context
- Proceeding without user review
