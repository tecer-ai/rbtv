---
name: step-05-synthesize
description: Reconcile — draft delta + open questions; Study — draft study notes + reflection prompts; HALT for user resolutions
nextStepFile: ./step-06-write.md
workflowFile: ./workflow.md
---

# Step 5: Synthesize

**Progress: Step 5 of 6** — Next: Write

---

## STEP GOAL

Mode-branched synthesis. Reconcile produces a delta + open questions list (HALT for answers). Study produces a draft study note + reflection prompts (HALT for user shaping).

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER write final outputs in this step — drafts only, in `<runtime_root>/synthesis/`
- 📖 You (parent agent) MAY read: target docs (reconcile), context references, grouping.yaml, user comments
- 🛑 You MUST NOT read source files
- ⏸️ ALWAYS HALT for user input on open questions / shaping before proceeding to step-06

---

## MANDATORY SEQUENCE

### 1. Read Manifest and Inputs

Read:
- `<runtime_root>/manifest.json`
- `<runtime_root>/extractions/grouping.yaml`
- For reconcile: each `inputs.targets[]` document
- Each `inputs.contexts[]` reference (file or URL — invoke `rbtv-web-searching` skill for URLs)
- `inputs.comments` (user line-comments — verbatim)

### 2A. Reconcile Mode — Draft Delta and Open Questions

#### 2A.1 Apply user comments to target

For each target document, locate every line referenced in `inputs.comments` and produce a proposed change. Record in `<runtime_root>/synthesis/delta-draft.md`:

```
### Change: <one-line summary>
- Source: user-comment line N
- Before: <quote>
- After: <quote>
- Rationale: <one sentence>
```

#### 2A.2 Apply context alignment

For each context reference, identify schema/concept/naming divergences between the target doc and the context. Record additional change blocks tagged `Source: context alignment (<ref-name>)`.

#### 2A.3 Apply grouping findings

For each `final_decision` in `grouping.yaml` that ADDS to the target (additions only — overrides require resolved open questions): record a change block tagged `Source: extraction (<source> line N)`.

#### 2A.4 Generate open questions

Triggers (any of these):

| Trigger | Question |
|---------|----------|
| User comment is itself a question | Verbatim |
| `grouping.yaml` contradiction | "<earlier> vs <later> — pick one or both?" |
| Extraction directly contradicts a user comment | "User comment says X; extraction line N says Y — which?" |
| Context divergence not justified by extraction | "Target says X; context says Y — keep, switch, or revise both?" |
| Extraction adds new concept the user has not opined on | "Add this? <text>" |

##### Recommendation policy

For each question, decide whether to recommend an option. Apply this evidence priority — higher rows override lower:

| Priority | Signal | Action |
|----------|--------|--------|
| 1 | User comment states an explicit preference (verbatim phrasing) | Recommend the matching option; rationale cites comment line |
| 2 | User comment states a partial preference or directional hint | Recommend the option ALIGNED with the user's direction — even if another option is better-engineered; rationale cites comment line |
| 3 | Prior decision in `grouping.yaml` constrains the answer | Recommend the option consistent with prior decision; rationale cites extraction line |
| 4 | No user signal AND no prior-decision signal | Do NOT recommend — write `Recommendation: no user signal — your call`; list one-line tradeoffs per option |

Anti-patterns — STOP and re-evaluate if you catch yourself:

| Anti-pattern | Fix |
|--------------|-----|
| Recommending based on general best practice when user comment was ambiguous | Demote to "no user signal — your call" |
| Recommending the more-structured / more-engineered option without user signal | User leans simpler; when in doubt, lean simpler OR abstain |
| Recommending a different SHAPE than the user's comment (e.g., comment says "keep it simple", rec says "drop the section entirely") | Match the comment's shape — "keep simple" ≠ "delete" |
| Treating a user question as a request for the "right answer" | Questions surface design space; recommend only when one option matches user-comment direction |

Write to `<runtime_root>/synthesis/open-questions.md`:

```
### Q{N}: <one-line summary>
- Source: <user-comment line N / contradiction / divergence>
- Context: <relevant lines or quotes>
- Options:
  - A) <option text>
  - B) <option text>
  - C) <option text>
- Recommendation: <A | B | C | "no user signal — your call">
- Rationale: <one of>
    - user-comment line N: "<verbatim phrase anchoring the choice>"
    - prior decision at extraction line N: "<verbatim phrase>"
    - no user signal — tradeoffs: A=<one line>, B=<one line>, C=<one line>
```

#### 2A.5 Present and HALT

Per `rbtv-chat-discipline` (chunked presentation):

- Print `Open questions: <count>. Top 2:` followed by Q1 and Q2 inline.
- Print `Full list at: <runtime_root>/synthesis/open-questions.md`
- HALT for user answers. Accept answers in any order. Continue presenting batches of 2 until exhausted.
- Append answers to `open-questions.md` as `Answer: <user response>` blocks.
- Do NOT proceed to step-06 until every Q has a recorded answer.

### 2B. Study Mode — Draft Study Notes

#### 2B.1 Build outline

From `grouping.yaml`, build:

```
# <study-doc-title — derived from primary source basename>

## Through-lines
- <each through_line>

## Themes
### <theme name>
- Key concepts: <list with line refs>
- Key claims: <list with line refs>
- Open questions: <list with line refs>
- Tensions: <list>
```

Save to `<runtime_root>/synthesis/study-draft.md`.

#### 2B.2 Generate reflection prompts

| Trigger | Prompt |
|---------|--------|
| Multiple competing through-lines | "Which through-line is most central to your study? <list>" |
| Tension worth deepening | "Tension between line N and line M — which side resonates with your existing understanding?" |
| Theme has many open questions | "Theme '<X>' has <N> open questions — which 1-2 do you want to pursue?" |
| Context reference adds a frame | "Context '<ref>' frames this as <Y>. Adopt, reject, or note as alternative?" |

Write to `<runtime_root>/synthesis/reflection-prompts.md` in the same Q-block format as 2A.4.

#### 2B.3 Present and HALT

Same chunked presentation pattern as 2A.5. Append user responses to `reflection-prompts.md` as `Answer: ...` blocks.

### 3. Step Menu

**YOLO bypass:** if `manifest["yolo"] == true`, skip this menu and auto-continue to Step 06 once every open question / reflection prompt has a recorded answer. The question / reflection HALTs in 2A.5 and 2B.3 are NEVER bypassed by yolo. Otherwise:

| Option | Action |
|--------|--------|
| **[C] Continue** | All open questions / reflection prompts answered — proceed to Step 06 |
| **[B] Back** | Return to grouping; user wants to re-cluster |
| **[X] Exit** | Abort; offer cleanup |

HALT and WAIT.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected AND all questions/prompts have answers:

1. Update `manifest.json`: append `step-05-synthesize` to `completed_steps`; set `current_step = "step-06-write"`.
2. Load `./step-06-write.md`.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Delta draft (reconcile) or study draft (study) exists; all open questions / reflection prompts answered.

❌ **FAILURE:** Source file read by parent agent; questions left unanswered; draft missing required sections.
