---
stepNumber: 'E01'
stepName: 'load'
nextStepFile: ./step-e02-edit.md
---

# Step E01: Load Existing Pitch Deck

**Progress: Edit Step 1 of 2** — Next: Apply Edits

---

## STEP GOAL

Load an existing HTML pitch deck, analyze its structure, and prepare for editing.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are a Pitch Deck Architect reviewing an existing deck with fresh eyes. Identify what works, what doesn't, and what's missing.

### Step-Specific Rules

- Read the complete HTML before proposing any changes
- Preserve the existing design system unless design change was requested
- Apply context-first-discovery — leverage what you already know about the project

---

## MANDATORY SEQUENCE

### 1. Locate the Deck

**If project-memo was @-mentioned:**
- Set {output_folder}=`{project-root}/_bmad-output/{project_name}/_fundraising/pitch-deck`
- Check for `{output_folder}/pitch-deck.html`

**If a specific HTML file was @-mentioned:**
- Use that file directly

**If neither:**
- Ask: "Which pitch deck should I edit? You can @-mention the HTML file or provide the project name."

If file not found, report error and exit.

### 2. Read and Analyze

Read the HTML file completely. Extract:

- Total slide count
- Slide titles and content summary (one line each)
- Visual direction (color palette, fonts, dark/light scheme)
- Icon libraries currently loaded
- Image references and which ones have actual files present
- Any design patterns used (grid layouts, stat blocks, feature cards)

### 3. Present Analysis

```
📊 Deck Analysis: {filename}

Slides ({count}):
  1. {title} — {brief content description}
  2. {title} — {brief content description}
  ...

Visual: {color scheme description}
Fonts: {font families}
Icons: {libraries loaded}
Images: {count referenced} ({count present} / {count missing})
```

### 4. Ask Edit Intent

"What would you like to change? Options:"

- **Content** — Update text, data, or messaging on specific slides
- **Add** — Insert new slides
- **Remove** — Delete slides
- **Reorder** — Change slide sequence
- **Design** — Modify colors, fonts, layout
- **Images** — Update image references or regenerate prompts
- **Multiple** — Combine any of the above

"Describe what you'd like to do."

Wait for response. Capture edit intent clearly.

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — proceed with the described edits
- **[X] Exit** — exit without changes

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the edit intent forward

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Existing deck loaded and analyzed correctly
- User's edit intent clearly captured
- Slide structure accurately described

❌ **FAILURE:**
- Modifying the deck before confirming edit intent
- Misidentifying slide content or structure
- Proceeding without the user specifying what to change
