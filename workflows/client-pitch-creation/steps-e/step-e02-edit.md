---
stepNumber: 'E02'
stepName: 'edit'
---

# Step E02: Apply Edits

**Progress: Edit Step 2 of 2** — Final step

---

## STEP GOAL

Apply the requested modifications to the existing client pitch deck HTML file.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer refining an existing deck. Every edit should make the deck more convincing to a procurement committee, never less. Challenge any change that reduces clarity or weakens buyer conviction.

### Step-Specific Rules

- Preserve the existing design system unless design change was requested
- Maintain print CSS integrity — page breaks must still work
- Update image prompts if image references change
- Keep slide count in the 10-12 range unless user explicitly overrides

---

## MANDATORY SEQUENCE

### 1. Plan Edits

Based on the user's edit intent from Step E01, plan the specific changes:

- Which slides are affected
- What HTML changes are needed
- Whether new slides need to follow existing visual patterns
- Whether image prompts need updating

Present the edit plan to the user for confirmation:
```
Edit Plan:
- [list specific changes with slide numbers]
- Design system: {preserved / modified}
- Image prompts: {will update / no change needed}

Proceed with these edits?
```

Wait for confirmation.

### 2. Apply Changes

Execute the edits on `{output_folder}/pitch-deck.html`:

**Content updates:** Modify text within existing slide structure.

**New slides:** Follow existing design patterns. Insert in correct position and update all slide numbers.

**Removed slides:** Delete the `<section>` element. Update all slide numbers.

**Reorder:** Move `<section>` elements. Update all slide numbers.

**Design:** Modify CSS custom properties for global changes. Never break print CSS.

**Proof updates:** When incorporating research findings, update evidence and citations. Ensure data presentation passes the glance test.

**Client tailoring:** When customizing for a specific client, update relevant slides with client-specific data, industry references, or pain points.

### 3. Update Image Prompts (if needed)

If any image references changed:
- Read `{output_folder}/pitch-image-prompts.md` (if it exists)
- Add prompts for new images
- Remove prompts for deleted images
- Update filenames if references changed
- Save the updated file

### 4. Verify Changes

After applying edits:
- Confirm total slide count
- Verify slide numbers are sequential
- Check page breaks are correct
- Verify no orphaned image references
- Ensure design consistency

### 5. Present Summary

```
✅ Edits applied: {output_folder}/pitch-deck.html

Changes:
- {list of specific changes made}

Slides: {count} (was: {previous_count})
Image prompts: {updated / not affected}
```

### 6. Present Menu

**Select an Option:**
- **[E] More Edits** — describe additional changes
- **[DA] Done** — exit the workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[E] More Edits** is selected:
1. Return to Step E01: reload and re-analyze the updated deck

ONLY when **[DA] Done** is selected:
1. Thank the user. Exit gracefully.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- All requested edits applied correctly
- Design consistency preserved
- Print layout still works
- Slide numbers updated after any add/remove/reorder
- Image prompts updated if needed

❌ **FAILURE:**
- Breaking existing slide design
- Breaking print CSS / page breaks
- Not updating slide numbers
- Introducing inconsistent styles
