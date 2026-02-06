---
title: RBTV System Audit & Refinement - 10 Task Sequential Workflow
type: execution-prompt
status: ready
created: 2026-02-06
---

# CLAUDE CODE EXECUTION PROMPT: RBTV SYSTEM AUDIT & REFINEMENT

## ROLE & CONTEXT

You are Claude Code, a systematic codebase analyst and refactoring agent. You will execute a **10-task sequential audit and improvement workflow** for the RBTV (Robotville) module within the BMAD system architecture.

**Critical Constraints:**
- Execute tasks in **strict numerical order** (1→10)
- Create **one commit per task** with conventional commit message
- Do NOT skip tasks or optimize the sequence
- For analysis tasks (2-4, 8-9), document reasoning explicitly before conclusions
- For decision tasks (8-9), apply defined evaluation criteria

**Context Window Strategy:**
- Use targeted file reads; avoid loading entire directories
- Reference documentation paths; read only when analysis requires
- For large file sets, use search/grep to locate patterns before reading

---

## TASK DEFINITIONS

### TASK 1: Review Broken Links
**Objective:** Identify and fix broken internal links in `rbtv/` that reference non-existent files

**Steps:**
1. Search for markdown link patterns: `[.*]\((.*\.md.*)\)` and `[.*]\((.*\.yaml.*)\)`
2. For links to `BMAD/`, check against the mirrored documentation in `_docs/system-documentation/BMAD/`
3. Categorize: (a) Dead links (target doesn't exist), (b) Incorrect paths (target exists elsewhere)
4. Fix all broken links; update paths to correct locations
5. Document findings in commit message body

**Success Criteria:**
- [ ] All markdown files in `rbtv/` scanned
- [ ] Zero broken internal links remain
- [ ] Links to BMAD components resolve to mirror or are documented as external

**Commit Format:**
```
fix(links): repair broken internal links in rbtv documentation

- Fixed [N] dead links
- Updated [N] incorrect paths
- Verified BMAD references against mirror
```

---

### TASK 2: Mentor Workflow Operational Continuity
**Objective:** Verify mentor workflow milestones (M1-M4) are operationally linked

**Analysis Framework:**
1. Load `workflows/bi-m*/` structure
2. For each milestone (M1, M2, M3, M4):
   - Identify framework sequence
   - Check linkage mechanism (nextStepFile, workflow references, etc.)
3. Document linkage topology: M1→M2→M3→M4 connection paths

**Success Criteria:**
- [ ] All 4 milestones documented with framework lists
- [ ] Linkage mechanism identified and verified functional
- [ ] Any broken connections fixed

**Output:** Document analysis in commit message or create `_docs/analysis/mentor-continuity-review.md` if findings are extensive

**Commit Format:**
```
docs(mentor): verify and document operational continuity across M1-M4

- Verified framework linkage: [mechanism]
- Fixed [N] broken connections (if any)
- Documented topology in [location]
```

---

### TASK 3: Mentor Workflow Strategic Continuity
**Objective:** Verify mentor milestones form a logical business progression

**Analysis Framework (Chain of Thought):**
1. **Load Context:** Read milestone/framework descriptions for M1→M4
2. **Evaluate Linear Flow:**
   - Does M1 output inform M2 input?
   - Does M2 build on M1 decisions?
   - Does M3 require M2 completion?
   - Does M4 synthesize prior milestones?
3. **Identify Gaps:** Where does logical flow break or require user assumptions?
4. **Assess Dependencies:** Are framework results actually used in subsequent frameworks?

**Success Criteria:**
- [ ] Strategic flow documented with reasoning
- [ ] Identified any logical gaps or weak dependencies
- [ ] Recommended fixes implemented OR documented as backlog if complex

**Commit Format:**
```
refactor(mentor): improve strategic continuity between milestones

- Analysis: [brief summary of flow assessment]
- Fixed: [specific improvements]
- Backlog: [complex items deferred to PRD]
```

---

### TASK 4: Mentor Knowledge Persistence Verification
**Objective:** Verify mentor uses previous framework results when executing new frameworks

**Investigation:**
1. Verify that `project_memo` is updated **per framework completion** (NOT per milestone)
2. Confirm mentor workflow loads `project_memo` before framework execution
3. Check synthesis step in framework workflows references `project_memo`
4. Trace data flow: Framework A results → `project_memo` → Framework B reads memo

**Note:** Based on preliminary analysis, this appears to already be correctly implemented (framework workflows update memo in final synthesis step). This task is VERIFICATION only.

**Success Criteria:**
- [ ] Confirmed `project_memo` updates per framework (not per milestone)
- [ ] Verified mentor loads `project_memo` during framework execution
- [ ] Documented update mechanism and data flow

**Commit Format:**
```
docs(mentor): verify project_memo knowledge persistence mechanism

- Update frequency: per-framework (VERIFIED CORRECT)
- Memo loading: [when/where verified]
- Data flow documented: [location if created]
```

---

### TASK 5: Improve Component Creator (God Workflow)
**Objective:** Enhance `god` agent/workflow to generate components matching BMAD patterns with correct config/header

**Steps:**
1. Read `agents/god.md` and `workflows/build/`
2. Identify where components are generated (templates, instructions)
3. Document BMAD component patterns (headers, frontmatter, config requirements)
4. Update templates/instructions to:
   - Match BMAD document structure
   - Apply correct config based on component type
   - Include proper header/frontmatter metadata
5. Test by having god generate a sample component; verify against BMAD patterns

**Success Criteria:**
- [ ] God workflow updated with BMAD pattern knowledge
- [ ] Templates enforce correct headers/config
- [ ] Sample generation test passes pattern validation

**Commit Format:**
```
feat(build): update component creator to match BMAD patterns

- Documented BMAD component structure requirements
- Updated templates: [list]
- Added config application logic for [types]
```

---

### TASK 6: Review Plan Workflow Microtask Creation
**Objective:** Ensure plan workflow only creates microtask files for complex tasks

**Steps:**
1. Read `workflows/plan-lifecycle/` (or relevant plan workflow)
2. Locate microtask creation logic
3. Identify decision criteria: When does plan create a separate microtask file vs inline task content?
4. Refine logic:
   - **Complex tasks** (multi-step, detailed instructions needed) → create microtask file
   - **Simple tasks** (single action, clear from title) → inline in YAML `content`
5. Update plan creation rules/templates

**Success Criteria:**
- [ ] Decision criteria documented
- [ ] Microtask creation logic updated to match criteria
- [ ] Examples added to plan creation documentation

**Commit Format:**
```
refactor(plan): optimize microtask file creation for complexity

- Criteria: create files only for [definition of complex]
- Simple tasks now use inline YAML content
- Updated: [files modified]
```

---

### TASK 7: Execute PRDs in `_docs/todos/`
**Objective:** Implement the 2 PRDs located in `_docs/todos/`

**Steps:**
1. Read `_docs/todos/cp-bmad-domain-and-manifests.md`
2. Read `_docs/todos/cp-shape_discovery_propagation.md`
3. For each PRD:
   - Implement specified changes
   - Follow acceptance criteria
   - Verify implementation
   - Commit changes

**Note:** This task will result in **2 commits** (one per PRD, both tagged as Task 7)

**Success Criteria:**
- [ ] Both PRDs implemented per specifications
- [ ] Acceptance criteria validated
- [ ] Two commits created

**Commit Format (per PRD):**
```
feat|fix(scope): [PRD title implementation]

[Implementation details from PRD]

Refs: _docs/todos/[prd-filename]
Task 7: Execute PRDs
```

---

### TASK 8: Evaluate BMAD Analyst vs RBTV M2 Duplication
**Objective:** Decide if BMAD's analyst/market research workflow can substitute or enhance RBTV's Mentor M2 (Business Innovation)

**Evaluation Criteria (Chain of Thought):**
1. **Functional Overlap:**
   - Compare BMAD analyst outputs vs RBTV M2 framework outputs
   - Identify: identical, overlapping, complementary, or distinct
2. **Quality Assessment:**
   - Which produces more valuable market research?
   - Does BMAD analyst add capabilities M2 lacks?
3. **Integration Feasibility:**
   - Can M2 invoke BMAD analyst as a sub-workflow?
   - Would integration reduce RBTV code or just add dependency?
4. **Maintenance Burden:**
   - Is maintaining both worthwhile?
   - Would unification reduce long-term maintenance?

**Decision Framework:**
- **IF** significant overlap (>70%) AND BMAD is superior → Substitute
- **IF** moderate overlap (40-70%) AND complementary → Link/integrate
- **IF** low overlap (<40%) OR distinct purposes → Keep Separate

**Success Criteria:**
- [ ] Analysis documented with reasoning
- [ ] Decision made: Substitute | Integrate | Keep Separate
- [ ] If Substitute/Integrate: implement changes OR create detailed PRD

**Commit Format:**
```
analysis(mentor): evaluate BMAD analyst vs M2 duplication

Decision: [Substitute | Integrate | Keep Separate]
Reasoning: [summary of evaluation]
Action: [changes made OR PRD created at _docs/todos/]

Task 8: BMAD Analyst Evaluation
```

---

### TASK 9: Analyze RBTV Components for BMAD Substitution Opportunities
**Objective:** Identify other RBTV components that could be replaced/linked to BMAD equivalents

**Analysis Process:**
1. List all RBTV components (agents, workflows, tasks)
2. For each, check if BMAD has equivalent functionality
3. Apply evaluation criteria from Task 8:
   - Functional overlap %
   - Quality comparison
   - Integration feasibility
   - Maintenance benefit
4. For components meeting substitution threshold:
   - Create individual PRD in `_docs/todos/`
   - Title: `prd-substitute-[component]-with-bmad-[equivalent].md`

**Success Criteria:**
- [ ] All RBTV components analyzed
- [ ] Candidates identified with reasoning
- [ ] PRDs created for recommended substitutions (if any)
- [ ] Analysis summary documented

**Commit Format:**
```
analysis(rbtv): identify BMAD substitution opportunities

Analyzed: [N] components
Candidates: [N] components recommended for substitution
PRDs created: [list]
No duplication found: [list]

Task 9: BMAD Substitution Analysis
```

---

### TASK 10: RBTV Pattern Compliance Review
**Objective:** Review RBTV codebase against BMAD component patterns using knowledge from Task 5

**Steps:**
1. Reference BMAD pattern documentation created in Task 5
2. Scan RBTV components (agents, workflows, steps, tasks, commands)
3. Check compliance:
   - Correct frontmatter structure
   - Proper config/header metadata
   - Consistent naming conventions
   - Required fields present
4. Fix non-compliant components
5. Document patterns in `.cursor/rules/` if not already present

**Success Criteria:**
- [ ] All RBTV components reviewed
- [ ] Non-compliant components fixed
- [ ] Pattern compliance rules documented

**Commit Format:**
```
refactor(rbtv): align components with BMAD patterns

Reviewed: [N] components
Fixed: [N] non-compliant components
Pattern violations: [brief summary]
Rules updated: [if applicable]

Task 10: Pattern Compliance Review
```

---

## EXECUTION PROTOCOL

### Commit Discipline
1. Complete each task fully before moving to next
2. Create commit immediately after task completion
3. Use conventional commit format: `type(scope): description`
4. Include task number in commit body: `Task N: [Task Name]`

### Quality Gates
Before marking any task complete:
- [ ] All success criteria checked
- [ ] Changes tested/verified
- [ ] Commit message written
- [ ] Ready to execute commit

### Decision Task Protocol (Tasks 8-9)
1. Document reasoning explicitly using "Chain of Thought" format
2. Apply defined evaluation criteria
3. State decision clearly before implementation
4. If decision is "defer to PRD", create PRD immediately

### Failure Recovery
If a task cannot be completed:
1. Document blocker clearly
2. Commit partial progress with `wip(scope):` prefix
3. Create issue in `_docs/todos/` for manual resolution
4. Proceed to next task

---

## START EXECUTION

Begin with **Task 1: Review Broken Links**. After completing Task 1, proceed immediately to Task 2, and continue sequentially through Task 10.

For each task:
1. Announce task start: "Starting Task [N]: [Name]"
2. Execute steps
3. Verify success criteria
4. Create commit
5. Announce completion: "Task [N] complete. Commit: [hash]"

**Do not ask for permission between tasks. Execute the full sequence.**
