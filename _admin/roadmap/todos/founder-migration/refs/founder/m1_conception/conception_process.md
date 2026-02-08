---
---

# Conception Process

**Purpose:** Detailed process guide for Milestone 1 (Conception) of the founder module. Transforms an initial idea into a comprehensive business concept through structured frameworks and documentation.

**Goal:** Structure an idea into a comprehensive business concept with clear problem definition, solution articulation, target customer understanding, and initial business model.

---

## Inputs

| Input | Source |
|-------|--------|
| Initial idea or problem statement | User/Founder |
| Market observations | User/Founder |
| Personal experience or pain points | User/Founder |
| Target customer hypotheses | User/Founder |

---

## Outputs

| Output | Format |
|--------|--------|
| Project memo (initialized) | Markdown document (`[project]/docs/founder/[project]_memo.md`) |
| Working Backwards document | Markdown document (applied framework in `[project]/docs/founder/conception/`) |
| Jobs-to-be-Done analysis | Markdown document (applied framework) |
| Competitive Landscape analysis | Markdown document (applied framework) — requires web research |
| Problem-Solution Fit Canvas | Markdown document (applied framework) |
| Lean Canvas | Markdown document (applied framework) |
| 5 Whys analysis | Markdown document (applied framework) |
| M1 Founder Diary | Markdown table (`[project]/docs/founder/conception/m1_founder_diary.md`) |

---

## Steps Summary

| Step | Action | Framework | Output |
|------|--------|-----------|--------|
| 1 | Initialize project structure and memo | — | Project memo with Status section populated |
| 2 | Define customer and their problem | Working Backwards | Press Release + FAQ |
| 3 | Understand customer's desired progress | Jobs-to-be-Done | JTBD analysis document |
| 4 | Map competitive landscape | Competitive Landscape | Competitive analysis with benchmarks |
| 5 | Validate problem-solution alignment | Problem-Solution Fit Canvas | Problem-Solution Fit document |
| 6 | Map business model hypothesis | Lean Canvas | Lean Canvas document |
| 7 | Identify root causes | 5 Whys | Root cause analysis document |
| 8 | Synthesize findings into project memo | — | Updated project memo (Introduction, Problem, Solution, Tenets sections) |
| 9 | Document key decisions and assumptions | — | Updated M1 founder log |

---

## Step 1: Initialize Project Structure

**Inputs:** Project name

**Action:**
1. Create project folder structure: `[project]/docs/founder/`
2. Create milestone folder: `[project]/docs/founder/conception/`
3. Initialize project memo from the template: [project_memo.md](../templates/project_memo.md)
4. Initialize founder diary from the template: [founder_diary.md](../templates/founder_diary.md)
5. Populate Status section with initial milestone state

**Output:** Basic project structure with empty documents

**Framework Reference:** None (structural setup)

---

## Step 2: Define Customer and Problem

**Inputs:** Initial idea, target customer hypotheses

**Action:**
1. Read Working Backwards framework: [working_backwards.md](conception_frameworks/working_backwards.md)
2. Follow Tasks 1–4 of the framework to:
   - Clarify primary customer and problem
   - Draft a customer-facing Press Release describing the product as if launched
   - Draft an External FAQ covering realistic customer and partner questions
   - Draft an Internal FAQ that answers feasibility, economics, and “Is it worth doing?”
3. Focus on customer outcomes and adoption, not internal features or implementation details

**Output:** Working Backwards document (Press Release + External FAQ + Internal FAQ)

**Framework Reference:** Working Backwards (Amazon methodology)

---

## Step 3: Understand Customer's Progress Goal

**Inputs:** Working Backwards document, customer insights

**Action:**
1. Read Jobs-To-Be-Done framework: [jobs_to_be_done.md](conception_frameworks/jobs_to_be_done.md)
2. Follow the framework tasks to:
   - Turn the Working Backwards PR/FAQ from Step 2 into explicit job hypotheses.
   - Design and, where applicable, run JTBD interviews to understand real episodes and forces.
   - Synthesise primary job stories, forces, and a job map for the chosen segment.
   - Prioritise jobs and select a primary job for M1 focus.

**Output:** Jobs-To-Be-Done analysis document

**Framework Reference:** [jobs_to_be_done.md](conception_frameworks/jobs_to_be_done.md)

---

## Step 4: Map Competitive Landscape

**Inputs:** Working Backwards document, JTBD analysis

**Action:**
1. Read Competitive Landscape framework: [competitive_landscape.md](conception_frameworks/competitive_landscape.md)
2. **Web search is MANDATORY for this step.** If unavailable, defer until web access is restored.
3. Follow the framework tasks to:
   - Identify direct and indirect competitors with verified current data
   - Benchmark US and China markets to understand mature market solutions and trajectory
   - Identify cross-industry analogues solving similar problems in adjacent industries
   - Analyze competitor strengths, weaknesses, and positioning
   - Map competitive positioning and identify white space
   - Extract threats and differentiation opportunities
   - Tag competitive assumptions for M2 validation
4. All factual claims about competitors, markets, or capabilities MUST include source URLs

**Output:** Competitive Landscape analysis document with geographic benchmarks, analogues, positioning map, and assumption inventory

**Framework Reference:** [competitive_landscape.md](conception_frameworks/competitive_landscape.md)

---

## Step 5: Validate Problem-Solution Alignment

**Inputs:** Working Backwards document, JTBD analysis, Competitive Landscape analysis

**Action:**
1. Read Problem-Solution Fit Canvas framework: [problem_solution_fit.md](conception_frameworks/problem_solution_fit.md)
2. Follow the framework tasks to:
   - Consolidate inputs from Working Backwards (Step 2) and JTBD (Step 3) into a precise problem-space brief.
   - Map problem, triggers, emotions, current behaviours, and alternatives.
   - Articulate the proposed solution in context of those behaviours and constraints.
   - Extract and tag critical assumptions that must hold for problem-solution fit.

**Output:** Problem-Solution Fit Canvas document

**Framework Reference:** [problem_solution_fit.md](conception_frameworks/problem_solution_fit.md)

---

## Step 6: Map Business Model Hypothesis

**Inputs:** Working Backwards document, JTBD analysis, Problem-Solution Fit Canvas

**Action:**
1. Choose framework depth:
   - Quick snapshot: Read [lean_canvas_quick.md](conception_frameworks/lean_canvas_quick.md) for time-boxed draft
   - Milestone-grade canvas (required for M1 completion): Read [lean_canvas.md](conception_frameworks/lean_canvas.md) for full integration
2. Complete all 9 Lean Canvas blocks as hypotheses:
   - Problem (top 3)
   - Customer Segments (including early adopters)
   - Unique Value Proposition
   - Solution (top 3 features or capabilities)
   - Channels
   - Revenue Streams
   - Cost Structure
   - Key Metrics
   - Unfair Advantage
3. Save document to `[project]/docs/founder/conception/` with version tag (e.g., `lean_canvas_v0.1.md`)
4. Tag key assumptions for M2/M5 validation

**Output:** Lean Canvas document

**Framework Reference:** [lean_canvas_quick.md](conception_frameworks/lean_canvas_quick.md) or [lean_canvas.md](conception_frameworks/lean_canvas.md)

---

## Step 7: Identify Root Causes

**Inputs:** Problem statement from previous steps

**Action:**
1. Read Five Whys framework: [five_whys.md](conception_frameworks/five_whys.md)
2. Follow the framework tasks to:
   - Select and frame a concrete problem scenario grounded in Problem-Solution Fit and Lean Canvas.
   - Run disciplined 5 Whys chains that separate facts from hypotheses.
   - Synthesise root causes and select which structural levers your concept will target.
   - Wire those root causes back into the project memo, Lean Canvas, and validation backlog.

**Output:** 5 Whys analysis document

**Framework Reference:** [five_whys.md](conception_frameworks/five_whys.md)

---

## Step 8: Synthesize into Project Memo

**Inputs:** All framework documents from steps 2-6

**Action:**
1. Update project memo Introduction with project vision and context
2. Update Problem section with synthesized problem understanding
3. Update Solution section with solution approach
4. Update Tenets section with core principles guiding the project
5. Update Progress > Conception subsection with completed frameworks

**Output:** Updated project memo with core sections populated

**Framework Reference:** Project Memo template ([project_memo.md](../templates/project_memo.md))

---

## Step 9: Document Key Decisions and Assumptions

**Inputs:** Insights from all previous steps

**Action:**
1. Review all framework documents for key decisions made
2. Identify critical assumptions that emerged
3. Note any pivots from initial idea
4. Document these in M1 founder log with appropriate Type (Decision, Assumption Invalidated, Pivot, Learning)

**Output:** Updated M1 founder log

**Framework Reference:** Founder Diary template ([founder_diary.md](../templates/founder_diary.md))

---

## Success Criteria

Conception milestone is complete when:

- [ ] Project memo exists with Introduction, Problem, Solution, and Tenets sections populated
- [ ] Working Backwards document exists with Press Release and FAQ
- [ ] Jobs-to-be-Done analysis exists
- [ ] Competitive Landscape analysis exists with geographic benchmarks (US, China), cross-industry analogues, and assumption inventory
- [ ] Problem-Solution Fit Canvas exists
- [ ] Lean Canvas exists with informed Unfair Advantage from competitive analysis
- [ ] 5 Whys analysis exists
- [ ] M1 founder diary exists with at least 2 entries documenting key decisions or assumptions
- [ ] Project memo Progress > Conception section lists all completed frameworks
- [ ] Founder can articulate: Who is the customer? What problem are we solving? Why our solution? What are the alternatives? What must be true?

---

## Next Milestone

Once Conception is complete, proceed to M2: Validation milestone (validation_process.md) to stress-test assumptions and validate feasibility.

---