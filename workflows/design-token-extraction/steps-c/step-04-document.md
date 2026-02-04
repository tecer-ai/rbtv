---
stepNumber: 4
stepName: 'document'
templateFiles:
  design-brief: ../templates/design-brief.md
  design-tokens: ../templates/design-tokens.json
outputFile: '{output_folder}/design-{slug}.md'
---

# Step 04: Document

**Progress: Step 4 of 4** — Final Step

---

## STEP GOAL

Generate the final output document(s) in the user's selected format(s).

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Complete your work with professional documentation.

### Step-Specific Rules

- Generate format(s) selected in step-01
- Include creative interpretation in brief format
- Use concrete values in tokens format
- Save to output folder

---

## MANDATORY SEQUENCE

### 1. Confirm Output Format

Check `outputFormat` from output document frontmatter:
- `brief` → Generate design brief only
- `tokens` → Generate design tokens JSON only
- `both` → Generate both documents

### 2. Generate Design Brief (if applicable)

Create narrative prose capturing creative interpretation:

**Structure:**
```markdown
# Design Extraction: {Website Name}

## Color Strategy
{Narrative describing color palette, relationships, and intent}

## Typography Direction
{Narrative describing type choices, hierarchy, and voice}

## Spacing Philosophy
{Narrative describing rhythm, density, breathing room}

## Layout Patterns
{Narrative describing grid, structure, section patterns}

## Visual Identity
{Narrative capturing brand tone, aesthetic, personality}
```

### 3. Generate Design Tokens (if applicable)

Create structured JSON with concrete values:

```json
{
  "colors": {
    "primary": "#XXXXXX",
    "secondary": "#XXXXXX",
    "neutral": { "100": "#XXXXXX", "500": "#XXXXXX", "900": "#XXXXXX" },
    "accent": "#XXXXXX"
  },
  "typography": {
    "fontFamily": { "primary": "Font Name" },
    "fontSize": { "h1": "48px", "h2": "36px", "body": "16px" },
    "fontWeight": { "regular": "400", "semibold": "600", "bold": "700" }
  },
  "spacing": {
    "xs": "8px", "sm": "16px", "md": "24px", "lg": "32px", "xl": "48px"
  },
  "layout": {
    "maxWidth": "1200px",
    "columns": 12,
    "gap": "16px"
  },
  "visual": {
    "borderRadius": { "sm": "4px", "md": "8px", "lg": "16px" },
    "shadow": "0px 2px 8px rgba(0,0,0,0.08)"
  }
}
```

### 4. Present Output for Review

Display generated document(s) to user.

Ask: "Review the output. Ready to save?"

### 5. Save Output Document(s)

Write to output folder:
- Brief: `{output_folder}/design-brief-{slug}.md`
- Tokens: `{output_folder}/design-tokens-{slug}.json`

### 6. Update State

Add `step-04-document.md` to `stepsCompleted` in output document frontmatter.

### 7. Present Completion Summary

```
Design extraction complete.

Files created:
- {list of created files with paths}

Tokens extracted:
- {count} colors
- {count} typography values
- {count} spacing values
- {count} layout properties
- {count} visual identity elements
```

### 8. Present Menu Options

**Select an Option:**

- **[D] Done** — Exit workflow successfully
- **[R] Revise** — Make changes to output
- **[S] Start New** — Begin extraction for another website

ALWAYS halt and wait for user selection.

---

## OUTPUT FORMAT EXAMPLES

### Design Brief (Narrative)

```markdown
## Color Strategy

The palette establishes trust through deep navy (#002B5C) as primary,
balanced with energetic coral (#FF6B6B) for calls-to-action. Neutral
grays provide breathing room without feeling sterile. The palette
communicates professionalism with a human touch.
```

### Design Tokens (Structured)

```json
{
  "colors": {
    "primary": "#002B5C",
    "accent": "#FF6B6B"
  }
}
```

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[D] Done** is selected:

1. Confirm all files saved successfully
2. Present final summary
3. Exit workflow gracefully

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Output document(s) match selected format
- All extracted tokens included
- Files saved to correct location
- User confirmed output quality

❌ **FAILURE:**
- Missing tokens in output
- Wrong output format generated
- Files not saved
- Proceeding without user confirmation
