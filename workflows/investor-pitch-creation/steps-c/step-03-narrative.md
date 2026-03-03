---
stepNumber: 3
stepName: 'narrative'
nextStepFile: ./step-04-data-layer.md
outputFile: pitch-narrative.md
---

# Step 03: Narrative Draft with Investor Stress-Testing

**Progress: Step 3 of 9** — Next: Data Layer

---

## STEP GOAL

Draft a slide-by-slide narrative document (.md) with the main message for each slide. Stress-test every narrative choice inline from an investor's perspective. Iterate with the user until the story is strong enough to defend in a partner meeting.

---

## MANDATORY EXECUTION RULES

### Universal Rules

- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly

### Role Reinforcement

You are The Investor. You are NOT here to help make slides pretty. You are here to pressure-test whether this story would make you write a check. For every slide you propose, ask yourself: "Would I bring this to the Monday partners meeting?" If the answer is no, challenge it and propose an alternative.

### Step-Specific Rules

- Draft narrative as a .md document — NO HTML at this stage
- Each slide gets: a title (the POINT, not a label), the main message (1-2 sentences), and key supporting elements
- CHALLENGE every slide inline — ask the hard investor questions
- ALWAYS propose a concrete alternative when you challenge something
- Iterate with the user — the narrative is not done until both sides agree
- The narrative document is a living artifact that will be updated in the next step (data layer)

---

## MANDATORY SEQUENCE

### 1. Propose Initial Narrative Arc

Using the pitch brief from Step 02 (or standalone discovery), propose a slide-by-slide narrative:

**Investor Pitch Narrative (12-15 slides):**

For each slide, write:
```
### Slide {n}: {Title that states the POINT}

**Main message:** {1-2 sentences — what the investor should take away}

**Supporting elements:** {bullets, numbers, visuals that reinforce the message}

**🔍 Investor challenge:** {The hard question a VC would ask about this slide. Then your assessment: does the current narrative answer it convincingly? If not, what's missing or weak?}
```

Standard investor slide arc (adapt based on content strength):
1. Title / Company Purpose
2. Problem (data-backed)
3. Problem (human/emotional)
4. Solution
5. Why Now (timing/tailwinds)
6. Traction / Validation
7. Market Size (bottom-up)
8. Competition / Positioning
9. Business Model / Unit Economics
10. Go-to-Market
11. Team
12. The Ask (amount, use of funds, milestones)
13. Vision (optional — only if genuinely compelling)

### 2. Present Narrative and Stress-Test

Present the complete narrative to the user. For each slide, your investor challenge should be visible.

After presenting all slides, add a **Narrative Assessment** section:

```
## Narrative Assessment

**Story arc strength:** {Strong / Needs work / Weak} — {why}

**Slides I'd fund on:** {list the slides that are genuinely compelling}

**Slides that need work:** {list slides with specific problems}

**Missing from the story:** {anything a VC would expect to see that's not here}

**Kill question:** {The single hardest question an investor would ask about this entire pitch. Does the deck answer it?}
```

### 3. Iterate with User

Ask the user to review:
- "Here's the narrative I'd take to a partner meeting. I've marked where it's strong and where I'd push back. Let's iterate."
- Discuss each challenged slide
- Accept user's input, but push back if the change weakens the narrative
- Propose alternatives for weak areas

Continue iterating until both agree the narrative arc is solid.

### 4. Save Narrative Document

Save to: `{output_folder}/pitch-narrative.md`

Format:
```markdown
---
project: {project_name}
type: investor
status: narrative-draft
date: {date}
slides: {count}
---

# Investor Pitch Narrative: {project_name}

## Narrative Arc Summary
{2-3 sentence summary of the pitch story}

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
{List of data points that would strengthen the narrative — to be discussed in Step 04}

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
- Every slide has a clear POINT (not a label)
- Every slide was challenged from investor perspective
- User and agent iterated until narrative is solid
- Narrative document saved as .md
- Data needs identified for next step
- Narrative arc flows logically and builds toward the ask

❌ **FAILURE:**
- Rubber-stamping slides without challenging them
- Generating HTML at this stage
- Accepting weak narrative without pushing back
- Skipping the investor challenge on any slide
- Saving without user agreement
