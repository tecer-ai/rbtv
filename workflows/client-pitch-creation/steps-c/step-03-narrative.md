---
stepNumber: 3
stepName: 'narrative'
nextStepFile: ./step-04-data-layer.md
outputFile: pitch-narrative.md
---

# Step 03: Narrative Draft with Buyer Stress-Testing

**Progress: Step 3 of 9** — Next: Data Layer

---

## STEP GOAL

Draft a slide-by-slide narrative document (.md) with the main message for each slide. Stress-test every narrative choice inline from a buyer's perspective. Iterate with the user until the story would survive a procurement committee review.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Buyer. You are NOT here to help sell. You are here to pressure-test whether this pitch would make you sign a contract. For every slide you propose, ask yourself: "Would I put this vendor on my shortlist based on this?" If the answer is no, challenge it and propose an alternative.

### Step-Specific Rules

- Draft narrative as a .md document — NO HTML at this stage
- Each slide gets: a title (the POINT, not a label), the main message (1-2 sentences), and key supporting elements
- CHALLENGE every slide inline — ask the hard buyer questions
- ALWAYS propose a concrete alternative when you challenge something
- Iterate with the user — the narrative is not done until both sides agree
- The narrative document is a living artifact updated in the next step (data layer)
- Frame EVERYTHING from the client's perspective, never from the vendor's

---

## MANDATORY SEQUENCE

### 1. Propose Initial Narrative Arc

Using the pitch brief from Step 02 (or standalone discovery), propose a slide-by-slide narrative:

**Client Pitch Narrative (10-12 slides):**

For each slide, write:
```
### Slide {n}: {Title that states the POINT from the client's perspective}

**Main message:** {1-2 sentences — what the buyer should take away}

**Supporting elements:** {bullets, numbers, visuals that reinforce the message}

**🔍 Buyer challenge:** {The hard question a procurement VP would ask about this slide. Then your assessment: does the current narrative answer it convincingly? If not, what's missing or weak?}
```

Standard client slide arc (adapt based on content strength):
1. Title / Who You Are (one line — the client doesn't care about your origin story)
2. Their Problem (data-backed, in their language)
3. Current Reality (how they solve it today, what it costs them)
4. Your Solution (what changes for THEM, not your feature list)
5. How It Works (process, workflow, integration — make it tangible)
6. Before / After (concrete transformation with metrics)
7. Proof Points (case studies, testimonials, pilot results)
8. Why Us vs. Alternatives (honest competitive positioning)
9. Pricing & ROI (plans, payback period, total cost of ownership)
10. Implementation & Timeline (what it takes to switch)
11. Next Steps (clear CTA — pilot, demo, trial, contract)

### 2. Present Narrative and Stress-Test

Present the complete narrative to the user. For each slide, your buyer challenge should be visible.

After presenting all slides, add a **Narrative Assessment** section:

```
## Narrative Assessment

**Buyer conviction:** {Would sign / Needs work / Would pass} — {why}

**Slides that would make the shortlist:** {list the slides that are genuinely compelling}

**Slides that need work:** {list slides with specific problems}

**Missing from the story:** {anything a buyer would expect to see}

**Kill objection:** {The single hardest objection a buyer would raise about this entire pitch. Does the deck pre-empt it?}
```

### 3. Iterate with User

Ask the user to review:
- "Here's the pitch as a buyer would experience it. I've marked where it's strong and where I'd push back. Let's iterate."
- Discuss each challenged slide
- Accept user's input, but push back if the change weakens buyer conviction
- Propose alternatives for weak areas
- Ensure the narrative stays in the CLIENT'S language, not the vendor's

Continue iterating until both agree the narrative would survive a procurement review.

### 4. Save Narrative Document

Save to: `{output_folder}/pitch-narrative.md`

Format:
```markdown
---
project: {project_name}
type: client
target: {target_client}
status: narrative-draft
date: {date}
slides: {count}
---

# Client Pitch Narrative: {project_name}

## Target: {target_client}

## Narrative Arc Summary
{2-3 sentence summary of the pitch story from the buyer's perspective}

---

### Slide 1: {Title}
**Main message:** {message}
**Supporting elements:**
- {element}
- {element}

---

### Slide 2: {Title}
...

---

## Data Needs
{List of proof points, ROI data, case studies that would strengthen the narrative}

## Open Questions
{Any unresolved narrative decisions}
```

### 5. Present Menu

**Select an Option:**
- **[C] Continue** — proceed to data layer discussion
- **[X] Exit** — exit workflow (narrative is saved)

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Load `{nextStepFile}` and carry the narrative document forward

ONLY when **[X] Exit** is selected:
1. Confirm exit and end workflow

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:**
- Every slide framed from the buyer's perspective (not vendor-centric)
- Every slide was challenged from buyer's perspective
- User and agent iterated until narrative is solid
- Narrative document saved as .md
- Data needs identified for next step
- Kill objection addressed

❌ **FAILURE:**
- Vendor-centric framing ("We're the best at X" instead of "You'll gain X")
- Feature dumps instead of outcome-focused messaging
- Rubber-stamping slides without challenging them
- Generating HTML at this stage
- Skipping the buyer challenge on any slide
