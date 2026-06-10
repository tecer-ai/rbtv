---
stepNumber: 'E01'
stepName: 'narrative-revision'
nextStepFile: null
---

# Step E01: Narrative Revision

**Progress: Revise Step 1 of 1** — Story-level rework; ends in design re-handoff

---

## STEP GOAL

Revise an existing pitch narrative at the story level — argument sequence, claims, the ask, slide set — with full audience stress-testing. Update the narrative and structure artifacts, then hand off to the studio module so the deck is synced.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly
- NEVER edit `pitch-deck.html` or any HTML/PDF file — HTML work is owned by the studio module's deck-design workflow

### Role Reinforcement

**If pitch_type = investor:**
You are The Investor revisiting a narrative with fresh eyes. Every revision must make the story more fundable — challenge proposed changes exactly as you challenged the original draft.

**If pitch_type = client:**
You are The Buyer revisiting a narrative with fresh eyes. Every revision must make the story more convincing to a procurement committee — challenge proposed changes exactly as you challenged the original draft.

### Step-Specific Rules

- Narrative and structure artifacts are a linked unit — when the slide set, order, or titles change, BOTH must be updated in the same operation
- A revised narrative with an existing deck means HTML drift — the step ALWAYS ends by routing the user to the deck sync handoff; never leave drift unflagged
- Small in-deck fixes (a number, a typo, a color) do NOT belong here — route the user to Vivian's deck-edit mode directly

---

## MANDATORY SEQUENCE

### 1. Locate the Artifacts

**If a pitch artifact or its folder was @-mentioned:** use it; set {output_folder} to the pitch folder root.

**If a project-memo was @-mentioned:** resolve the pitch output folder via the `rbtv-output-resolution` rule (File Routing in workspace CLAUDE.md).

**If neither:** Ask: "Which pitch should I revise? You can @-mention the narrative file or provide the project name."

Load:
- `{output_folder}/artifacts/pitch-narrative.md` (required)
- `{output_folder}/artifacts/pitch-structure.md` — set {pitch_type} from its frontmatter (if missing, ask investor or client)
- Check whether `{output_folder}/pitch-deck.html` exists — set {deck_exists}

### 2. Capture Revision Intent

Ask: "What should change in the story?" Capture the intent clearly. Classify each requested change:

| Class | Examples | Handled here? |
|-------|----------|---------------|
| Story-level | Re-sequence the argument, change the ask, add/remove/merge slides, reframe a claim, new evidence reshaping a section | YES |
| Deck-level | Update a number in the HTML, styling, layout, images | NO — route to the `rbtv-designing` skill (Vivian), deck-edit mode |

If everything requested is deck-level: stop, route the user to Vivian, and exit.

### 3. Stress-Test the Proposed Changes

For each story-level change, challenge it from the audience's perspective before applying:

**If pitch_type = investor:** Would this change make a VC partner lean forward — or weaken a claim that was already defensible? Push back with a concrete alternative when a change weakens the narrative.

**If pitch_type = client:** Would this change help the buyer defend the purchase to their CFO — or bury the proof? Push back with a concrete alternative when a change weakens conviction.

Agree the final shape of each change with the user before writing.

### 4. Apply to the Narrative

Update `{output_folder}/artifacts/pitch-narrative.md` with the agreed changes. Preserve the document's existing structure and data annotations.

### 5. Sync the Structure Artifact

If the slide set, order, titles, layout implications, or data/proof points changed: update `{output_folder}/artifacts/pitch-structure.md` (slide spec table + `slideCount` + Structure Notes) in the same operation.

### 6. Present Summary

```
✅ Narrative revised: {output_folder}/artifacts/pitch-narrative.md
{✅ Structure updated: artifacts/pitch-structure.md — only if changed}

Changes:
- {list of story-level changes applied}

Deck status: {no deck generated yet / pitch-deck.html exists — now OUT OF SYNC}
```

### 7. Present Menu

**Select an Option:**
- **[R] More Revisions** — describe additional story-level changes
- **[DA] Done** — proceed to handoff

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[R] More Revisions** is selected:
1. Return to Section 2 with the new intent

ONLY when **[DA] Done** is selected:

> **AGENT HANDOFF — studio module (deck-design)**
>
> **If {deck_exists}:** Instruct the user:
>
> *"The narrative and structure are revised — the existing deck is now out of sync. Invoke the `rbtv-designing` skill (Vivian) and select **[DE] Deck Edit** to sync the deck to the revised artifacts (or **[PD] Pitch Deck Design** to regenerate it)."*
>
> **If no deck exists yet:** Instruct the user:
>
> *"The narrative and structure are revised. When ready to build the deck, invoke the `rbtv-designing` skill (Vivian) and select **[PD] Pitch Deck Design**."*
>
> Do NOT load any deck-design step yourself. The design agent loads them.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Story-level changes stress-tested before applying — not rubber-stamped
- Narrative and structure artifacts updated together
- Deck-level requests routed to Vivian, not executed here
- Handoff presented whenever a deck exists

❌ **FAILURE:**
- Editing pitch-deck.html or any HTML/PDF file
- Updating the narrative but leaving pitch-structure.md stale
- Ending the step without flagging an out-of-sync deck
- Applying changes without audience stress-testing
