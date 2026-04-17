---
stepNumber: 5
stepName: 'document'
templateFiles:
  design-brief: ../templates/design-brief.md
  design-tokens: ../templates/design-tokens.json
outputFile: '{output_folder}/design-{slug}.md'
---

# Step 05: Document

**Progress: Step 5 of 5** — Final Step

---

## STEP GOAL

Generate the final output document(s) in the user's selected format(s) using the synthesized tokens from step-04.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement

You are a Design System Analyst. Complete your work with professional documentation that captures both precise values and design intent.

### Step-Specific Rules

- Generate format(s) selected in step-01 (check `outputFormat` in frontmatter)
- Use DOM-extracted values for all concrete token fields
- Include source attribution in tokens JSON
- Include creative interpretation in brief format (informed by screenshots)
- Save all output files to `{output_folder}/`

---

## MANDATORY SEQUENCE

### 1. Confirm Output Format

Check `outputFormat` from output document frontmatter:
- `brief` → Generate design brief only
- `tokens` → Generate design tokens JSON only
- `both` → Generate both documents

### 2. Generate Design Brief (if applicable)

Load template from `{design-brief}`.

Fill narrative sections using synthesized tokens from step-04. The brief captures design intent and creative interpretation — it is prose, not data:

- **Color Strategy** — palette relationships, intent, emotional impact
- **Typography Direction** — type choices, hierarchy, voice, readability
- **Spacing Philosophy** — rhythm, density, breathing room, vertical flow
- **Layout Patterns** — grid systems, section structures, responsive behavior
- **Visual Identity** — brand tone, aesthetic style, personality, overall impression

### 3. Generate Design Tokens JSON (if applicable)

Load template from `{design-tokens}`.

Populate every field with synthesized values from step-04:
- Use DOM-extracted values for all precise fields (colors, fonts, sizes, spacing)
- Include source attribution (`"dom"` or `"screenshot-sampled"`) per token
- Populate new categories: `fontFace`, `letterSpacing`, `transition`, `breakpoints`, `cssVariables`, `alphaScale`, `zIndex`, `opacity`
- NEVER leave a field as the template placeholder if data was extracted
- Mark genuinely absent tokens with `null` and a comment explaining absence

### 4. Present Output for Review

Display generated document(s) to user.

Ask: "Review the output. Ready to save?"

HALT and wait for confirmation.

### 5. Save Output Document(s)

Write to output folder:
- Brief: `{output_folder}/design-brief-{slug}.md`
- Tokens: `{output_folder}/design-tokens-{slug}.json`

### 6. Update State

Add `step-05-document.md` to `stepsCompleted` in output document frontmatter.

### 7. Present Completion Summary

```
Design extraction complete.

Files created:
- {list of created files with paths}

Sources:
- {N} pages captured and analyzed
- {N} screenshots in {output_folder}/screenshots/
- {N} DOM scan JSONs in {output_folder}/design-tokens/

Token coverage:
- {count} colors
- {count} font families ({count} @font-face declarations)
- {count} font sizes, {count} weights
- {count} spacing values
- {count} breakpoints
- {count} CSS variables
- {count} transitions/animations
```

### 8. Present Menu Options

**Select an Option:**

- **[D] Done** — Exit workflow successfully
- **[R] Revise** — Make changes to output
- **[S] Start New** — Begin extraction for another website

ALWAYS halt and wait for user selection.

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
- All synthesized tokens included — no data loss between step-04 and output
- Tokens JSON has no `null` for values that were extracted
- Source attribution present in tokens JSON
- Files saved to correct location
- User confirmed output quality

❌ **FAILURE:**
- Missing tokens that were synthesized in step-04
- `null` values for extractable tokens
- Wrong output format generated
- Files not saved
- Proceeding without user confirmation
