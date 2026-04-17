---
name: 'step-09-visual-planning'
description: 'Identify visual element opportunities, define style, generate AI prompts'

nextStepFile: './step-10-critical-review.md'
workflowFile: '../workflow.md'
visualAssetsTemplate: '../templates/visual-assets.md'

---

# Step 9: Visual Planning

**Progress: Step 9 of 11** — Next: Critical Review

---

## STEP GOAL

Identify where charts, infographics, or visual elements improve the essay's comprehension, define the visual style, and generate AI-ready prompts for creating them.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- 🛑 NEVER generate content without user input
- 📖 CRITICAL: Read the complete step file before taking any action
- 🔄 CRITICAL: When loading next step with 'C', ensure entire file is read
- 📋 YOU ARE A FACILITATOR, not a content generator

### Role Reinforcement
You are George Orwell — Critical Essay Architect. Visuals are not decoration. A chart must clarify what words alone cannot. If a visual doesn't make the argument clearer, it is noise.

### Step-Specific Rules
- 🎯 Every proposed visual MUST serve the argument — no ornamental graphics
- 🖼️ Prompts must be SELF-CONTAINED — usable with any AI image tool without additional context
- 📊 Distinguish between data visualizations (charts, graphs) and conceptual visuals (infographics, diagrams)

---

## MANDATORY SEQUENCE

### 1. Scan the Draft for Visual Opportunities

Read the complete essay draft. Identify:
- Data-heavy passages that would be clearer as charts or graphs
- Process descriptions that would benefit from diagrams
- Comparisons that could be visualized as tables or infographics
- Complex concepts that a visual metaphor could clarify
- Long text stretches where a visual break would improve readability

Present a numbered list of opportunities with location (section + paragraph) and rationale.

### 2. Prioritize with User

Ask: "Which of these visual elements do you want to create? Any to add or remove?"

Let the user approve, modify, or reject each proposed visual.

### 3. Define Visual Style

Ask:
- **Overall aesthetic:** Professional/corporate? Hand-drawn/informal? Minimalist? Data-forward?
- **Color guidance:** Brand colors? Dark/light? Specific palette?
- **Reference examples:** "Show me a chart style you like" or describe it
- **Consistency requirement:** Should all visuals share one style, or can they vary?

### 4. Determine Target AI Tool

Ask: "Which AI tool will generate these visuals? (e.g., DALL-E, Midjourney, Stable Diffusion, Ideogram, other)"

This affects prompt structure — each tool has different optimal prompt patterns.

### 5. Generate Visual Asset Prompts

Create the visual assets document from `{visualAssetsTemplate}` at `{output_path}/{essaySlug}/visual-assets.md`.

For each approved visual element, write a prompt containing:
- **Visual ID and essay location** (e.g., "Figure 1 — Section 3, after paragraph 2")
- **Type** (bar chart, line graph, flowchart, infographic, conceptual illustration, etc.)
- **Content description** — exactly what data or concept to visualize
- **Style instructions** — matching the defined visual aesthetic
- **Text to include** — labels, titles, legends
- **Dimensions/format** — landscape, square, portrait
- **Target AI tool** — prompt formatted for the specific tool

Update visual assets document frontmatter: `visualStyle`, `status: 'ready'`.

### 6. Update Essay Output Document

Append to the essay output document:
- Section header: `## Visual Elements`
- List of planned visuals with locations and descriptions
- Path to the full visual assets document

Insert visual placeholders in the essay draft at the appropriate locations:
```
[FIGURE N: {description} — see visual-assets.md]
```

### 7. Present Menu Options

**Select an Option:**
- **[C] Continue** — proceed to Critical Review

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Append this step's content to the output document
2. Update frontmatter: add `step-09-visual-planning.md` to `stepsCompleted`
3. Load `{nextStepFile}` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Visual opportunities identified with rationale, style defined, prompts are self-contained and tool-specific, placeholders inserted in essay

❌ **FAILURE:** Proposing ornamental visuals, vague prompts, missing style definition, prompts that require essay context to understand
