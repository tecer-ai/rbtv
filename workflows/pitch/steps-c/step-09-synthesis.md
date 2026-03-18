---
stepNumber: 9
stepName: 'synthesis'
nextStepFile: ./step-10-pdf-validation.md
---

# Step 09: Synthesis

**Progress: Step 9 of 10** — Next: PDF Export & Visual QA

---

## STEP GOAL

**If pitch_type = investor:**
Review the complete investor pitch package, provide a quality assessment, and guide next steps.

**If pitch_type = client:**
Review the complete client pitch package, provide a quality assessment, and guide next steps.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

---

## MANDATORY SEQUENCE

### 1. Package Summary

**If pitch_type = investor:**
Present the complete build summary:

```
💰 Investor Pitch Package Complete: {project_name}

Deliverables:
  1. artifacts/pitch-narrative.md        — Stress-tested slide-by-slide narrative with data layer
  2. artifacts/pitch-research-prompt.md  — Research prompts (thesis + counter-thesis) for {target_model}
  3. pitch-deck.html                     — Professional HTML deck (PDF via step-10)
  4. artifacts/pitch-image-prompts.md    — Image generation prompts for Nano Banana

Output folder: {output_folder}/
  ├── pitch-deck.html / .pdf
  ├── artifacts/    (narrative, research prompt, image prompts)
  ├── assets/       (images)
  └── research/     (research outputs)
```

**If pitch_type = client:**
Present the complete build summary:

```
🤝 Client Pitch Package Complete: {project_name}

Target: {target_client}

Deliverables:
  1. artifacts/pitch-narrative.md        — Buyer-tested slide-by-slide narrative with proof needs
  2. artifacts/pitch-research-prompt.md  — Research prompts (proof + objections) for {target_model}
  3. pitch-deck.html                     — Professional HTML deck (PDF via step-10)
  4. artifacts/pitch-image-prompts.md    — Image generation prompts for Nano Banana

Output folder: {output_folder}/
  ├── pitch-deck.html / .pdf
  ├── artifacts/          (narrative, research prompt, image prompts)
  ├── assets/             (images)
  ├── research/           (research outputs)
  └── meeting-transcript/ (meeting notes)
```

### 2. Quality Self-Assessment

**If pitch_type = investor:**
Review the deck against key investor pitch principles:

| Check | Status | Notes |
|-------|--------|-------|
| Narrative stress-tested (every slide challenged) | ✅/⚠️ | |
| Data needs identified and research prompted | ✅/⚠️ | |
| Counter-thesis risks addressed | ✅/⚠️ | |
| Slide count (12-15 range) | ✅/⚠️ | |
| One idea per slide | ✅/⚠️ | |
| Glance test passes (legible, simple, obvious) | ✅/⚠️ | |
| Landscape layout ready for PDF export (step-10) | ✅/⚠️ | |
| Narrative arc flows logically | ✅/⚠️ | |
| Strongest slides front-loaded | ✅/⚠️ | |
| The Ask is clear and defensible | ✅/⚠️ | |
| Icons render properly | ✅/⚠️ | |
| Image placeholders styled gracefully | ✅/⚠️ | |
| Color consistency throughout | ✅/⚠️ | |

**If pitch_type = client:**
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
| Landscape layout ready for PDF export (step-10) | ✅/⚠️ | |
| Professional, trust-first visual design | ✅/⚠️ | |
| Clear CTA / next steps slide | ✅/⚠️ | |
| No feature dumps (outcomes over features) | ✅/⚠️ | |

Be honest. Flag any ⚠️ items with specific improvement suggestions.

### 3. Recommended Next Steps

**If pitch_type = investor:**
Present ordered next steps:

1. **Run the research prompts** — Open {target_model}, upload context documents, run both prompts (thesis + counter-thesis)
2. **Review research results** — Compare findings against the narrative. If data contradicts key slides, revisit the narrative before proceeding
3. **Update the deck** — Use **[E] Edit** mode to incorporate research data into the HTML slides
4. **Export PDF** — Use **[C] Continue** to run step-10 (Decktape export + visual QA loop)
5. **Generate images** — use the prompts in `artifacts/pitch-image-prompts.md` with Google Nano Banana
6. **Place images** — save generated images to `{output_folder}/assets/` with exact filenames
7. **Practice the pitch** — review the narrative document to rehearse the story arc
8. **Review with audience** — test the deck's clarity with someone unfamiliar with your project

**If pitch_type = client:**
Present ordered next steps:

1. **Run the research prompts** — Open {target_model}, upload context documents, run both prompts (proof + objections)
2. **Review research results** — Compare findings against the narrative. If proof is weaker than expected or objections reveal gaps, revisit the narrative
3. **Prepare objection responses** — Use the objection research to build a FAQ document for the sales conversation
4. **Update the deck** — Use **[E] Edit** mode to incorporate research data into the HTML slides
5. **Export PDF** — Use **[C] Continue** to run step-10 (Decktape export + visual QA loop)
6. **Generate images** — use the prompts in `artifacts/pitch-image-prompts.md` with Google Nano Banana
7. **Place images** — save generated images to `{output_folder}/assets/` with exact filenames
8. **Tailor for specific client** — if this is a generic deck, customize slides 2-3 with the specific client's data/situation before the meeting
9. **Practice the pitch** — rehearse the narrative arc and objection responses

### 4. Suggest Complementary Tools

"For additional quality checks, you can use these RBTV tools on the HTML file:"
- **design-validation** — evaluates structural integrity, visual hierarchy, brand consistency, and UX quality
- **quality-review** — general quality gate assessment

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to PDF export & visual QA (step-10)
- **[E] Edit** — switch to edit mode to refine the deck
- **[S] Skip PDF** — skip PDF export and exit the workflow
- **[X] Exit** — exit workflow

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
- Load `{nextStepFile}` (step-10-pdf-validation)

ONLY when **[E] Edit** is selected:
- Load edit mode entry point (`steps-e/step-e01-load.md`)

ONLY when **[S] Skip PDF** or **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Complete summary presented with all four deliverables listed
- Quality assessment honest and actionable (not rubber-stamped)
- Next steps emphasize running research before finalizing
- User has clear path forward

**If pitch_type = client:** Additionally:
- Objection preparation called out explicitly

❌ **FAILURE:**
- Rubber-stamping quality without real assessment
- Missing deliverables in summary
- Not emphasizing the research → narrative revision loop
- No actionable next steps

**If pitch_type = client:** Additionally:
- Forgetting to mention objection preparation
