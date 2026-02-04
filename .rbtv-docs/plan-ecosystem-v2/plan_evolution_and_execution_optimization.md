# Plan Evolution and Execution Optimization

**Type:** Product  
**Date:** 2026-02-03  
**Conversation:** Analysis of Hugo RE Evaluator plan execution that revealed architectural gaps in initial planning and led to mid-execution plan revision, capturing generic patterns for revolving plans and execution optimization.

---

## 1. Overview

**Purpose:** Document learnings about plan evolution during execution and execution optimization principles derived from real-world plan adjustments.

**Scope:** 
- **Included:** Generic patterns for when plans need revision, how to document revisions, execution ordering principles
- **Excluded:** Hugo-specific implementation details (used only as example case)

**Success Metrics:** 
- Plans catch architectural pattern violations before execution starts
- When plans evolve during execution, changes are documented systematically
- Execution order follows dependency logic (build dependencies before dependents)

---

## 2. Context: What Happened

### The Scenario

A plan was created with Phase 1 (create orchestrator) followed by Phase 2 (add workflows). During Phase 1 execution, a fundamental architectural issue emerged:

**Initial Plan Structure:**
- Phase 1: Create orchestrator file with persona, rules, routing
- Phase 2: Add workflow logic to orchestrator file

**Issue Discovered:**
The plan violated BMAD micro-file architecture principle. Workflow logic should live in separate files, not embedded in the orchestrator.

**Result:**
Plan was revised mid-execution to:
- Phase 1: Create orchestrator with routing only (no workflow logic)
- Phase 2: Create separate workflow files
- Phase 2.5 (new): Update orchestrator with workflow input requirements

An execution decisions document was created to capture what changed and why.

---

## 3. Design Decisions

### Decision: Create "Revolving Plan" Pattern

**Status:** Approved  
**Context:** Plans are executed by AI agents over multiple sessions. During execution, architectural insights emerge that require plan adjustment. We need a systematic way to handle plan evolution without losing execution continuity.

**Decision:** Support "revolving plans" — plans that can be adjusted during execution with documented decision trails.

**Rationale:**
- Plans are created before deep implementation understanding exists
- Architectural patterns may be violated in initial planning
- Stopping execution to create an entirely new plan wastes work
- Better to adjust the plan and document what changed

**Alternatives Considered:**
- **Option A: Immutable plans** - Never change plans once execution starts. Rejected because it's too rigid and wastes completed work when minor adjustments are needed.
- **Option B: Silent plan updates** - Update plans without documentation. Rejected because context is lost and future executors don't understand why changes were made.

**Consequences:**
- ✅ Positive: Plans can adapt to discovered architectural requirements
- ✅ Positive: Execution context is preserved through decision documents
- ⚠️ Negative: Requires discipline to document changes rather than just edit

**Implementation Notes:** 
- Plan revisions trigger creation/update of `execution_decisions.md`
- Execution decisions must document: what changed, why it changed, impact on remaining tasks
- YAML todos in plan frontmatter must be updated to match revised task descriptions

---

### Decision: Document Plan Changes in execution_decisions.md

**Status:** Approved  
**Context:** When plans change mid-execution, future executors (or resuming sessions) need to understand what changed and why.

**Decision:** All plan revisions during execution must be documented in `execution_decisions.md` with a section on "Plan Updates."

**Rationale:**
- Execution decisions are already used to document implementation choices
- Adding plan changes to the same document keeps all execution context in one place
- Section structure ("Plan Updates") makes changes easy to find

**Alternatives Considered:**
- **Option A: Separate plan_changes.md** - Rejected because it fragments execution context
- **Option B: Git commit messages only** - Rejected because plan files are tracked but execution rationale is lost

**Consequences:**
- ✅ Positive: Single source of truth for execution context
- ✅ Positive: Easy to review what changed during a phase
- ⚠️ Negative: execution_decisions.md files can get longer when major plan revisions occur

**Implementation Notes:**
Include in execution_decisions.md:
- **Plan Updates** section listing all changes (YAML todos, phase goals, task descriptions)
- **Issues Encountered** section explaining why the plan needed revision
- **Key Decisions** section capturing the architectural principle that was violated or discovered

---

### Decision: Execution Order Follows Dependency Graph

**Status:** Approved  
**Context:** The Hugo plan initially had orchestrator creation (Phase 1) before workflow creation (Phase 2), but the orchestrator needed to reference workflow files. This created a logical dependency gap.

**Decision:** Plan task ordering must follow dependency logic: build dependencies before dependents.

**Rationale:**
- Components that reference other components can't be fully implemented until those dependencies exist
- Placeholders and TODOs in dependent components create unnecessary complexity
- Executing in dependency order eliminates forward references

**Alternatives Considered:**
- **Option A: Use placeholders** - Create dependent first with placeholder references, fill in later. Rejected because it requires a "backfill" step and makes testing harder.
- **Option B: Build everything in parallel** - Rejected because it doesn't work when one component needs to know the interface/structure of another.

**Consequences:**
- ✅ Positive: Each completed component is immediately usable
- ✅ Positive: No backfill or "update references" steps needed
- ✅ Positive: Testing can happen incrementally
- ⚠️ Negative: Requires deeper architectural analysis during planning

**Implementation Notes:**
For orchestrator + workflow patterns:
1. Create workflow files FIRST (Phase 1)
2. Create orchestrator that references workflows SECOND (Phase 2)

For systems with multiple layers:
1. Data layer / knowledge bases
2. Workflow logic that uses data
3. Orchestrator that routes to workflows

---

### Decision: Task Descriptions Must Specify File Operations

**Status:** Approved  
**Context:** The Hugo plan had task descriptions like "Add /avaliar workflow" without specifying whether this meant "add to hugo.md" or "create workflows/avaliar.md". This ambiguity led to the architectural violation.

**Decision:** Task descriptions must explicitly state file operations: CREATE, UPDATE, DELETE, MOVE.

**Rationale:**
- "Add" is ambiguous (add where? to what file?)
- Explicit file operations make architectural intent clear
- Reviewers can spot violations by seeing "UPDATE hugo.md with workflow logic" vs "CREATE workflows/avaliar.md"

**Alternatives Considered:**
- **Option A: Use context to infer** - Rejected because it relies on executor understanding the architecture, which may not be documented
- **Option B: Use verb conventions (add=update, create=new file)** - Rejected because conventions are easily forgotten

**Consequences:**
- ✅ Positive: Task intent is unambiguous
- ✅ Positive: Architectural patterns are visible in task descriptions
- ⚠️ Negative: Task descriptions become more verbose

**Implementation Notes:**
Good task descriptions:
- "CREATE hugo/project/workflows/avaliar.md with calculation logic..."
- "UPDATE hugo/project/hugo.md workflow sections with required inputs..."

Bad task descriptions:
- "Add /avaliar workflow" (where? to what file?)
- "Implement benchmark mode" (what file? create or update?)

---

### Decision: Plans Must Declare Architectural Constraints Explicitly

**Status:** Approved  
**Context:** The Hugo plan stated "All files MUST follow BMAD standards" but didn't explicitly state "workflows in separate files" as a constraint. This led to the violation.

**Decision:** Plans must have an explicit "Architectural Constraints" or "BMAD Standards" section listing specific patterns that MUST be followed.

**Rationale:**
- Generic statements like "follow BMAD" are too abstract
- Executors may not know which BMAD patterns apply to this specific project
- Listing specific constraints makes violations detectable during task creation

**Alternatives Considered:**
- **Option A: Reference external docs only** - Rejected because executors may not read or understand which parts apply
- **Option B: Include constraints in each task description** - Rejected because it's repetitive and can be missed

**Consequences:**
- ✅ Positive: Architectural patterns are explicit and reviewable
- ✅ Positive: Violations are caught earlier (during task description writing)
- ⚠️ Negative: Requires architectural analysis up front

**Implementation Notes:**
Include in plan:
- **BMAD Standards (Mandatory)** section with table of principles and implementations
- **Key Decisions** section explaining why specific architectural patterns were chosen
- Cross-reference to detailed architecture docs (e.g., bmad-creator-persona.md)

Example constraint statements:
- "Micro-file architecture: workflows in separate files (80-200 lines each)"
- "Orchestrator validates inputs only; workflow logic lives in workflow files"
- "Knowledge bases accessed strategically (targeted lookups, not full file loads)"

---

## 4. Implementation Details

### Revolving Plan Workflow

**When a plan needs revision during execution:**

1. **Pause execution** - Stop working on current task
2. **Identify the issue** - What architectural pattern was violated? What needs to change?
3. **Assess impact** - Which tasks are affected? Which are already complete?
4. **Revise the plan:**
   - Update YAML todos (task descriptions, new tasks)
   - Update phase goals if scope changed
   - Update task lists in phase sections
   - Update diagrams if task flow changed
5. **Document in execution_decisions.md:**
   - **Issues Encountered** section: Describe what was discovered
   - **Key Decisions** section: Document the architectural principle
   - **Plan Updates** section: List all changes made to the plan
6. **Resume execution** - Continue with revised task list

### Execution Decisions File Structure

```markdown
# [Project Name] - Execution Decisions

**Phase:** Phase X - [Phase Name]
**Tasks Completed:** [task-ids]
**Completed:** YYYY-MM-DD
**Attempts:** N
**Outcome:** Approved | In Progress | Blocked

---

## Outcome
[Summary of what was accomplished]

## Key Decisions
[Architecture and implementation decisions made during execution]

## Issues Encountered
**Issue:** [What went wrong or what was discovered]
**Resolution:** [How it was addressed]

## Plan Updates
[When plan was revised mid-execution]

**YAML todos updated:**
- [Change 1]

**Plan sections updated:**
- [Change 2]

## Files Created
[List of deliverables]

## Next Steps
[What comes next]
```

### Task Description Template

**Format:** `[ACTION] [file-path] [with/containing] [content description]`

**Examples:**
- `CREATE hugo/project/workflows/avaliar.md with calculation logic, workflow steps, and output template in Portuguese`
- `UPDATE hugo/project/hugo.md workflow sections with required inputs for each workflow`
- `DELETE hugo/project/old-orchestrator.md (deprecated after refactor)`
- `MOVE hugo/docs/old-location.md to hugo/docs/new-location.md`

**Actions:**
- **CREATE** - New file that doesn't exist yet
- **UPDATE** - Modify existing file (add section, change content)
- **DELETE** - Remove file
- **MOVE** - Change file location

---

## 5. How It Works

### Scenario: Mid-Execution Plan Revision

**1. Execution begins**
- Agent starts Phase 1, Task 1
- Reads task description: "Add /avaliar workflow"

**2. Agent implements task**
- Ambiguous description leads to adding workflow TO orchestrator file
- Begins writing workflow logic in orchestrator

**3. Issue discovery**
- User or agent realizes this violates micro-file architecture
- Stops execution before completing the task

**4. Plan revision**
- Analyze: Workflows should be in separate files
- Impact: Phase 2 tasks need rewriting
- Changes needed:
  - Phase 1 creates orchestrator with routing only
  - Phase 2 creates separate workflow files
  - New task (Phase 2.5) updates orchestrator with workflow inputs

**5. Update plan**
- Revise YAML todos
- Revise phase descriptions
- Add new task (p2-5)
- Update diagram

**6. Document changes**
- Create/update execution_decisions.md
- Add "Issues Encountered" section explaining the problem
- Add "Plan Updates" section listing all changes
- Add decision about dependency ordering

**7. Resume execution**
- Complete Phase 1 with revised understanding
- Phase 2 now creates workflow files (not adds to orchestrator)
- Phase 2.5 updates orchestrator references

---

## 6. Constraints & Assumptions

**Technical Constraints:**
- Plans are markdown files with YAML frontmatter
- Plans must be readable by both humans and AI agents

**Assumptions:**
- Executors have access to architecture reference docs (e.g., bmad-creator-persona.md)
- Plans will be executed over multiple sessions with different AI agents
- Not all architectural implications are knowable at planning time

---

## 7. Execution Optimization Principles

### Principle 1: Dependencies Before Dependents

**What:** Components that are referenced by other components should be built first.

**Why:** Eliminates placeholder references, enables incremental testing, reduces backfill work.

**Example:**
- ❌ Bad: Create orchestrator (Phase 1) → Create workflows (Phase 2) → Update orchestrator with workflow references (Phase 3)
- ✅ Good: Create workflows (Phase 1) → Create orchestrator that references workflows (Phase 2)

### Principle 2: Architectural Constraints Up Front

**What:** Plans must explicitly list architectural patterns that must be followed.

**Why:** Generic references to "follow BMAD" are too abstract. Specific constraints catch violations early.

**Example:**
Include in plan:
```markdown
### BMAD Standards (Mandatory)
| Principle | Implementation |
|-----------|----------------|
| Micro-file architecture | Workflows in separate files (80-200 lines) |
| Orchestrator role | Input validation and routing only, no workflow logic |
```

### Principle 3: File Operations Explicit

**What:** Task descriptions must state the file operation (CREATE, UPDATE, DELETE, MOVE) and the file path.

**Why:** Eliminates ambiguity about where logic should live.

**Example:**
- ❌ Bad: "Add /avaliar workflow"
- ✅ Good: "CREATE hugo/project/workflows/avaliar.md with workflow logic"

### Principle 4: Document Plan Evolution

**What:** When plans are revised during execution, document what changed and why in execution_decisions.md.

**Why:** Preserves context for future executors and creates learning artifacts.

**Example:**
```markdown
## Issues Encountered
**Issue:** Original plan had workflows being added directly to orchestrator file
**Resolution:** Revised plan to create separate workflow files per BMAD micro-file architecture

## Plan Updates
**YAML todos updated:**
- p2-1 through p2-4: Changed from "Add workflow to hugo.md" to "CREATE workflows/[name].md"
```

### Principle 5: Test Points at Dependency Boundaries

**What:** After completing a layer of dependencies, verify they work before building dependents.

**Why:** Catches interface issues early, before dependents are built on top of broken dependencies.

**Example:**
After creating workflow files (Phase 1):
- Verify workflow files load correctly
- Test workflow logic independently
- THEN create orchestrator that references workflows (Phase 2)

---

## 8. Open Questions & Future Work

**Unresolved Questions:**
- [ ] Should plans include a "Dependency Graph" diagram showing task dependencies?
- [ ] At what point does a plan revision warrant creating a new plan vs updating the existing one?
- [ ] Should there be a "pre-execution architectural review" step to catch patterns before starting?

**Future Enhancements:**
- [ ] Develop a plan validation tool that checks for dependency ordering violations
- [ ] Create a template for "Architectural Constraints" section with common BMAD patterns
- [ ] Build a library of execution optimization patterns

**Known Limitations:**
- Not all architectural implications are knowable at planning time (some discovery is inevitable)
- Dependency graphs can be complex for large systems (may be hard to visualize in plans)

---

## 9. Case Study: Hugo RE Evaluator Plan

**Background:** A plan to create a Claude Projects-based agentic system with an orchestrator and four workflow modes.

**Initial Plan Structure:**
- Phase 0: Foundation
- Phase 1: Create hugo.md orchestrator (persona, rules, routing, workflow logic)
- Phase 2: Add four modes to hugo.md
- Phase 3: Create knowledge bases
- Phase 4: Create entry point

**Issue Discovered in Phase 1:**
Task p1-1 was "Create hugo.md with persona and rules." During execution, it became clear the plan intended to add workflow logic directly to hugo.md in Phase 2. This violated BMAD micro-file architecture (workflows should be in separate files).

**Plan Revision:**
- Phase 1: Create hugo.md with persona, rules, routing (NO workflow logic)
- Phase 2 (renamed to "Workflow Files"): 
  - p2-1 through p2-4: CREATE separate workflow files (workflows/avaliar.md, etc.)
  - p2-5 (NEW): UPDATE hugo.md with workflow input requirements
- Phase 3: Knowledge bases (unchanged)
- Phase 4: Entry point (unchanged)

**Documented in execution_decisions.md:**
- Key decision: Separate workflow files following BMAD micro-file architecture
- Issue: Original plan violated micro-file architecture
- Resolution: Created workflows/ directory, updated task descriptions
- Plan updates: 12 changes to YAML todos, phase descriptions, goals, and diagrams

**Learning:** Workflow files should be created FIRST (Phase 1), then orchestrator that references them (Phase 2). The revised plan still had dependency ordering backwards (orchestrator in Phase 1, workflows in Phase 2), but at least they were separated into different files. Future plans should reverse this entirely.

**Optimal Structure Would Be:**
- Phase 0: Foundation
- Phase 1: Create workflow files (workflows/avaliar.md, etc.)
- Phase 2: Create hugo.md orchestrator that references workflow files
- Phase 3: Knowledge bases
- Phase 4: Entry point

---

## 10. References

**Files Referenced:**
- `.cursor/plans/hugo-re-evaluator_b144ed6f.plan.md` - Example revolving plan
- `.cursor/plans/hugo-re-evaluator/execution_decisions.md` - Example execution decisions with plan updates
- `hugo/docs/bmad-creator-persona.md` - BMAD architectural thinking patterns
- `robotville/docs/to_dos/bmad_benchmark/agentic-system-study/03-component-patterns-and-templates.md` - BMAD micro-file architecture patterns

**Key Patterns:**
- **Revolving Plan Pattern:** Plan + Execution Decisions documenting changes mid-execution
- **Dependency-First Ordering:** Build dependencies before components that reference them
- **Explicit File Operations:** Task descriptions state CREATE/UPDATE/DELETE/MOVE + file path
- **Architectural Constraints Section:** Plans list specific patterns that must be followed

---

## Summary

Plans evolve during execution as architectural insights emerge. Support this with:
1. **Revolving plan pattern** - Update plans mid-execution when needed
2. **execution_decisions.md** - Document what changed and why
3. **Dependency ordering** - Build dependencies before dependents
4. **Explicit task descriptions** - State file operations (CREATE/UPDATE) and paths
5. **Architectural constraints** - List specific patterns to follow, not generic "follow BMAD"

The Hugo plan example demonstrates all five patterns in action: a plan was revised when architectural violations were discovered, changes were documented, and learnings about execution ordering were captured for future planning.
