---
name: 'step-03-interview'
description: 'Design and run JTBD interviews'
nextStepFile: './step-04-job-stories.md'
outputFile: '{outputFolder}/jobs-to-be-done.md'
---

# Step 3: Interview Design

**Progress: Step 3 of 5** — Next: Job Stories & Forces

---

## STEP GOAL

Design a JTBD research plan and interview guide. Optionally run interviews and capture timeline-based narratives.

---

## MANDATORY EXECUTION RULES

### Universal Rules
- NEVER generate content without user input or confirmation
- READ this complete file before taking any action
- Follow the MANDATORY SEQUENCE below exactly — do not deviate, skip, or optimize

### Role Reinforcement
You are a YC mentor. Real interviews reveal truth. Push for timeline-based questions about past behavior, not hypotheticals.

### Step-Specific Rules
- All interview questions must be answerable with stories about real past events
- Guide can be used WITHOUT showing product or features
- Screener must confirm participants have experienced the job situation
- If no interviews possible, proceed with founder/team knowledge (note limitation)

---

## CONTEXT BOUNDARIES

**Available context:**
- Job hypotheses from Step 2
- Working Backwards customer profile
- JTBD interview methodology

**Out of scope:**
- Synthesizing job stories (that's Step 4)
- Final job prioritization (that's Step 5)

---

## MANDATORY SEQUENCE

### 1. Define Target Groups

Help founder define interview targets:

| Group | Definition | Why |
|-------|------------|-----|
| Recent adopters | Started using solution in last 3-6 months | Fresh memory of switch |
| Switchers | Moved from one solution to another | Can articulate forces |
| Strugglers | Still using workarounds | Experience the pain daily |

For each group, specify:
- Role/title
- Company size/type
- Industry/context
- How to find them (network, communities, tools)

### 2. Create Screener

Draft 3-5 screener questions that confirm:
- Participant has recently experienced the situation from job hypotheses
- They have tried something to make progress
- They're willing to discuss a specific recent episode

**Example screener format:**
> 1. Have you [experienced situation] in the past 6 months?
> 2. What did you use to address it? (Any solution counts)
> 3. Would you walk me through a specific recent instance (30-45 min call)?

### 3. Design Interview Guide

Create timeline-based interview guide:

**Opening (anchor on specific episode):**
> "Tell me about the last time you [job situation]. When was that? Walk me through that day from the beginning."

**Timeline exploration:**
1. **Trigger:** "What first happened that made you think you needed to deal with this?"
2. **Passive looking:** "What did you try casually at first, before making it a project?"
3. **Active looking:** "When did you decide 'I need to fix this now'? What did you search for? Who did you ask?"
4. **Deciding:** "What did you compare? What tipped the decision toward the option you chose?"
5. **Consuming:** "Walk me through what you did the first few times you used that option."

**Force probes:**
- "How did you feel at that moment?" (emotional)
- "Who else cared whether this worked or failed?" (social)
- "What would have happened if you had done nothing?" (stakes)
- "What almost stopped you from making a change?" (anxieties)
- "What were you used to doing before?" (habits)

### 4. Plan Logistics

Confirm interview logistics:
- Target count: 5-10 interviews (minimum 5 for patterns)
- Duration: 45-60 minutes per interview
- Recording approach (if allowed)
- Note-taking template with sections for timeline and forces

### 5. Interview Execution (Optional)

If founder can run interviews:
- Immediately after each interview, clean up notes
- Tag recurring patterns (same trigger, same workaround, same anxiety)
- Note verbatim quotes for key moments

If interviews not possible:
- Document founder/team knowledge as proxy data
- Note this limitation explicitly
- Identify 2-3 priority interviews to do in future

### 6. Update Output Document

Update jobs-to-be-done.md Interview Guide section:

```markdown
## Interview Guide

### Target Groups

| Group | Criteria | How to Find |
|-------|----------|-------------|
| [Group 1] | [Criteria] | [Source] |
| [Group 2] | [Criteria] | [Source] |

### Screener Questions

1. [Question 1]
2. [Question 2]
3. [Question 3]

### Interview Flow

**Opening:** [Anchor question]

**Timeline:**
1. Trigger: [Question]
2. Passive looking: [Question]
3. Active looking: [Question]
4. Deciding: [Question]
5. Consuming: [Question]

**Force Probes:**
- [Emotional probe]
- [Social probe]
- [Stakes probe]
- [Anxiety probe]
- [Habit probe]

### Interview Status

- [ ] Interview 1: [Status/Notes]
- [ ] Interview 2: [Status/Notes]
...

### Data Notes

[Summary of interview findings OR note that interviews pending]
```

Update frontmatter:
```yaml
stepsCompleted: ['step-01-init', 'step-02-job-hypotheses', 'step-03-interview']
```

### 7. Present Menu Options

**Select an Option:**
- **[A] Advanced Elicitation** — refine interview guide or add interview notes
- **[C] Continue** — proceed to Job Stories & Forces

ALWAYS halt and wait for user selection.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected:
1. Verify interview guide documented
2. Verify interview status noted (completed or pending)
3. Verify `step-03-interview` is in `stepsCompleted`
4. Load `./step-04-job-stories.md` and follow its instructions

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Interview guide with timeline-based questions, target groups defined, screener created, status documented

❌ **FAILURE:** Hypothetical questions, leading questions, no target group definition, no interview plan
