---
stepNumber: 9
stepName: 'synthesis'
---

# Step 09: Synthesis

**Progress: Step 9 of 9** — Final step

---

## STEP GOAL

Review the complete client pitch package, provide a quality assessment, and guide next steps.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

---

## MANDATORY SEQUENCE

### 1. Package Summary

Present the complete build summary:

```
🤝 Client Pitch Package Complete: {project_name}

Target: {target_client}

Deliverables:
  1. pitch-narrative.md        — Buyer-tested slide-by-slide narrative with proof needs
  2. pitch-research-prompt.md  — Research prompts (proof + objections) for {target_model}
  3. pitch-deck.html           — Professional HTML deck (landscape PDF via Ctrl+P)
  4. pitch-image-prompts.md    — Image generation prompts for Nano Banana

Output folder: {output_folder}/
Image folder:  {output_folder}/images/
```

### 2. Quality Self-Assessment

Review the deck against key client pitch principles:

| Check | Status | Notes |
|-------|--------|-------|
| Narrative framed from buyer's perspective | ✅/⚠️ | |
| Every slide challenged from buyer's POV | ✅/⚠️ | |
| Proof needs identified and research prompted | ✅/⚠️ | |
| Buyer objections addressed | ✅/⚠️ | |
| Slide count (10-12 range) | ✅/⚠️ | |
| One idea per slide | ✅/⚠️ | |
| Glance test passes (legible, simple, obvious) | ✅/⚠️ | |
| ROI / proof slides early in the deck | ✅/⚠️ | |
| Landscape PDF works (Ctrl+P) | ✅/⚠️ | |
| Professional, trust-first visual design | ✅/⚠️ | |
| Clear CTA / next steps slide | ✅/⚠️ | |
| No feature dumps (outcomes over features) | ✅/⚠️ | |

Be honest. Flag any ⚠️ items with specific improvement suggestions.

### 3. Recommended Next Steps

Present ordered next steps:

1. **Run the research prompts** — Open {target_model}, upload context documents, run both prompts (proof + objections)
2. **Review research results** — Compare findings against the narrative. If proof is weaker than expected or objections reveal gaps, revisit the narrative
3. **Prepare objection responses** — Use the objection research to build a FAQ document for the sales conversation
4. **Update the deck** — Use **[E] Edit** mode to incorporate research data into the HTML slides
5. **Open the HTML file** in a browser to review all slides
6. **Test PDF export** — press Ctrl+P, select "Save as PDF", verify landscape format and page breaks
7. **Generate images** — use the prompts in `pitch-image-prompts.md` with Google Nano Banana
8. **Place images** — save generated images to `{output_folder}/images/` with exact filenames
9. **Tailor for specific client** — if this is a generic deck, customize slides 2-3 with the specific client's data/situation before the meeting
10. **Practice the pitch** — rehearse the narrative arc and objection responses

### 4. Suggest Complementary Tools

"For additional quality checks, you can use these RBTV tools on the HTML file:"
- **design-validation** — evaluates structural integrity, visual hierarchy, brand consistency, and UX quality
- **quality-review** — general quality gate assessment

### 5. Present Menu

**Select an Option:**
- **[E] Edit** — switch to edit mode to refine the deck
- **[DA] Done** — exit the workflow

ALWAYS halt and wait for user selection.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Complete summary presented with all four deliverables
- Quality assessment honest and actionable
- Next steps emphasize running research before finalizing
- Objection preparation called out explicitly
- User has clear path forward

❌ **FAILURE:**
- Rubber-stamping quality without real assessment
- Missing deliverables in summary
- Not emphasizing the research → narrative revision loop
- Forgetting to mention objection preparation
