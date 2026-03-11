# Shape - Claude Native Config Source

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Inverts IDE config source of truth: `.claude/` becomes canonical, `.cursor/` becomes derived
- Migrates all source files from `_config/.cursor/` and `_admin/.cursor/` to `.claude/` equivalents
- Rewrites installer conversion functions to convert `.claude/` → `.cursor/` (reversing current direction)
- Updates all documentation to reflect the new source-of-truth direction

**What this plan does NOT include:**
- Behavioral changes to any rules, agents, or commands
- Leveraging Claude-only skill features (`context: fork`, `agent:`, `hooks:`) — follow-up enhancement
- Full context rot mitigation implementation — awareness only in v1
- CLAUDE.md restructuring beyond updating the Installation section
- MCP config relocation — stays at `_config/.cursor/mcp.json`

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Source format | Claude Code `.md` as canonical | Strict superset — superset→subset conversion is safe; reverse is lossy |
| MCP location | Stay at `_config/.cursor/mcp.json` | Both IDEs use identical format; no migration needed |
| Skills migration | Move to `.claude/`, strip Claude-only fields when deriving `.cursor/` | Enables future Claude-native features without blocking current Cursor use |
| Admin rules source | `_admin/.claude/rules/*.md` | Same inversion logic applies to admin-specific rules |
| Context rot | Awareness only (v1) | Full implementation is a separate follow-up effort |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Zero behavioral changes | PRD acceptance criteria | All installed output must remain functionally identical |
| MCP stays in `_config/.cursor/` | PRD scope decision | Installer MCP merge logic unchanged |
| Claude-only skill features out of scope | PRD explicit exclusion | Skills move as-is; Claude-only frontmatter fields are future work |
| Installer must remain idempotent | Existing contract | All modes (ide, admin, sync) must work correctly after changes |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Plan scope | "Create a plan for this PRD" (referencing prd-claude-native-config-source.md) | Full 4-phase plan covering migration, installer rewrite, documentation, and validation |
| 2 | Plan location | "Create the plan folder in claude code workspaces and move the prd to the plan folder" | Plan folder at `_admin/roadmap/todos/_claude-code-workspace/claude-native-config-source/` with PRD moved inside |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Phase structure | Accepted 4-phase breakdown | Proposed migration→installer→docs→validate sequence based on dependency analysis | 4 sequential phases with checkpoints at each transition |
| 2 | Task granularity | Accepted proposed tasks | Assessed complexity to determine micro-step file needs | 6 tasks get micro-step files; remaining use inline YAML content |

---

## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Atomic files | All plan artifacts are self-contained; no cross-file content repetition |
| Explicit file operations | Tasks use CREATE/UPDATE/DELETE verbs for file operations |
| Zero-context plans | Plan + shape + microsteps contain everything needed for execution |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| No behavioral changes | Validate installed output is functionally identical before and after |
| Preserve `{project-root}` placeholders | Never resolve placeholders in source files — they are runtime-resolved |
| Installer idempotency | Run installer multiple times; output must be identical each time |

### Tool Mode Selection

| Scenario | Mode | Rationale |
|----------|------|-----------|
| Need prior context | Skill | Preserves conversation history |
| Context saturated | Subagent | Fresh context window |
| Complex validation | Subagent | quality-review needs focused evaluation |
| Quick lookup | Skill | Minimal overhead |
| Already in subagent | Skill only | Subagents cannot nest |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")

<!-- Decisions and discovery entries will be appended below this line -->

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_admin/roadmap/todos/_claude-code-workspace/claude-native-config-source/prd-claude-native-config-source.md` | Full PRD with proposed changes, migration steps, acceptance criteria |
| `_config/install-rbtv.py` | Current installer implementation — 1011 lines, 7 conversion/replication functions |
| `CLAUDE.md` | Repository identity, path resolution, installation documentation |
| `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc` | Admin mode config overrides, installer documentation |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `_config/install-rbtv.py` | Understand and rewrite conversion functions | p2-1 through p2-5 |
| `_config/.cursor/rules/*.mdc` | Source rules to convert to `.md` format | p1-2 |
| `_config/.cursor/agents/*.md` | Source agents to convert frontmatter | p1-3 |
| `.claude/rules/*.md` (installed copies) | Reference for target Claude format | p1-2, p1-3 |
| `CLAUDE.md` | Update installation documentation | p3-1 |
| `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc` | Update installer documentation | p3-2 |
