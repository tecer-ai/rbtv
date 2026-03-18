---
name: claude-native-config-source
overview: "Invert IDE config source of truth: .claude/ becomes canonical, .cursor/ becomes derived, with reversed installer conversion direction"
todos:
  # Phase 1: Migrate Source Files
  - id: p1-1
    content: "p1-1: CREATE _config/.claude/commands/ by copying all 14 command files from _config/.cursor/commands/ (identical format, no conversion needed)"
    # inline — no micro-step file
    status: completed
  - id: p1-2
    content: "p1-2: CREATE _config/.claude/rules/ by converting all 7 rule files from _config/.cursor/rules/*.mdc to Claude .md format"
    taskFile: "phase-1/p1-2.task.md"
    status: completed
  - id: p1-3
    content: "p1-3: CREATE _config/.claude/agents/ by converting all agent files from _config/.cursor/agents/ to Claude-native frontmatter"
    taskFile: "phase-1/p1-3.task.md"
    status: completed
  - id: p1-4
    content: "p1-4: CREATE _config/.claude/skills/ by copying all 8 skill directories from _config/.cursor/skills/ (identical format)"
    # inline — no micro-step file
    status: completed
  - id: p1-5
    content: "p1-5: CREATE _admin/.claude/rules/ by converting 2 admin rule files from _admin/.cursor/rules/*.mdc to Claude .md format"
    # inline — no micro-step file (same conversion as p1-2, only 2 files)
    status: completed
  - id: p1-checkpoint
    content: "P1 CHECKPOINT - Verify all source files migrated with correct format conversions"
    status: completed
  # Phase 2: Rewrite Installer
  - id: p2-1
    content: "p2-1: UPDATE _config/install-rbtv.py — replace old conversion helpers with new _convert_claude_rule_to_mdc and _convert_claude_agent_to_cursor functions"
    taskFile: "phase-2/p2-1.task.md"
    status: completed
  - id: p2-2
    content: "p2-2: UPDATE _config/install-rbtv.py — reverse all ide_replicate_*_to_claude functions to ide_replicate_*_to_cursor equivalents"
    taskFile: "phase-2/p2-2.task.md"
    status: completed
  - id: p2-3
    content: "p2-3: UPDATE _config/install-rbtv.py — rewrite IDE mode flow to copy from _config/.claude/ and derive .cursor/"
    taskFile: "phase-2/p2-3.task.md"
    status: completed
  - id: p2-4
    content: "p2-4: UPDATE _config/install-rbtv.py — rewrite admin mode flow to use _admin/.claude/ and _config/.claude/ as source"
    taskFile: "phase-2/p2-4.task.md"
    status: completed
  - id: p2-5
    content: "p2-5: UPDATE _config/install-rbtv.py — update source directory constants, cleanup constants, and path references throughout"
    # inline — no micro-step file
    status: completed
  - id: p2-checkpoint
    content: "P2 CHECKPOINT - Verify installer conversion functions and flow are correct"
    status: completed
  # Phase 3: Update Documentation
  - id: p3-1
    content: "p3-1: UPDATE CLAUDE.md — reflect new source-of-truth direction in Installation section"
    # inline — no micro-step file
    status: completed
  - id: p3-2
    content: "p3-2: UPDATE _admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc — reflect new source-of-truth direction in installer documentation"
    # inline — no micro-step file
    status: completed
  - id: p3-3
    content: "p3-3: UPDATE other files referencing _config/.cursor/ as canonical source (agents/fernando.md, component patterns rule, etc.)"
    # inline — no micro-step file
    status: completed
  - id: p3-checkpoint
    content: "P3 CHECKPOINT - Verify documentation consistency across all files"
    status: completed
  # Phase 4: Validate & Finalize
  - id: p4-1
    content: "p4-1: Run installer in admin mode and verify installed output at rbtv root matches expected structure"
    # inline — no micro-step file
    status: completed
  - id: p4-2
    content: "p4-2: DELETE emptied source directories (_config/.cursor/commands/, _config/.cursor/rules/, _config/.cursor/agents/, _config/.cursor/skills/) — retain only _config/.cursor/mcp.json"
    # inline — no micro-step file
    status: completed
  - id: p4-3
    content: "p4-3: DELETE _admin/.cursor/ directory (fully migrated to _admin/.claude/)"
    # inline — no micro-step file
    status: completed
  - id: p4-refs
    content: "p4-refs: File reference review - verify all internal markdown links resolve correctly"
    # inline — no micro-step file
    status: completed
  - id: p4-compound
    content: "p4-compound: Review learnings.md and compound into system improvements"
    # inline — no micro-step file
    status: completed
  - id: p4-checkpoint
    content: "P4 FINAL CHECKPOINT - User approval to complete plan"
    status: completed
isProject: false
---

# Claude Native Config Source

> Read `shape.md` for full context, decisions, and constraints.
> Read individual `.task.md` files (referenced via `taskFile`) for per-task execution instructions.

## Architectural Constraints

Patterns and principles that MUST be followed during execution.

| Principle | Enforcement |
|-----------|-------------|
| Zero behavioral changes | Installed output must be functionally identical before and after migration |
| Preserve `{project-root}` placeholders | Never resolve runtime placeholders in source files — they are resolved by the installer at install time |
| Installer idempotency | Run installer multiple times in succession — output must be identical each time |
| MCP config unchanged | `_config/.cursor/mcp.json` stays in place — do not move or restructure |
| Claude-only features deferred | Do NOT add new Claude-only frontmatter fields (tools, hooks, memory, etc.) — this is a format migration only |

**Inviolable Rules:**
1. Read shape.md execution log before starting any task
2. Only one task `in_progress` at a time
3. Dependencies are sacred — never skip prerequisite tasks
4. Checkpoints require quality-review subagent execution before user-facing gate decision — never skip the review
5. Checkpoints require human approval — never auto-continue, even after `APPROVED` verdict
6. `REJECTED` checkpoints cannot advance — address feedback before re-evaluation
7. Append to shape.md after each task — never modify previous entries

## Checkpoint Execution Protocol

Every checkpoint has a **"Checkpoint Review Prompt"** subsection in its phase body (marked with `####` heading and a blockquote containing the full prompt). At each checkpoint:

1. Locate the checkpoint's review prompt in the phase body section (e.g. "P1 Checkpoint Review Prompt")
2. Fire Task tool with `subagent_type='quality-review'`, passing the blockquoted prompt content
3. Present the `APPROVED` / `REJECTED` verdict to user
4. **HALT for human approval regardless of verdict**
5. If `REJECTED`, do not advance to the next phase — address feedback first

**Why body, not YAML:** Cursor's plan YAML serializer only preserves `id`, `content`, and `status` on todo items. Custom fields are silently stripped when the executor updates task status.

## Revolving Plan Rules

- Simple discovery (<5 min): resolve immediately, document in shape.md
- Complex discovery: add new task to plan, document in shape.md, notify user

## Phase 1: Migrate Source Files

**Goal:** Move and convert all source files from `_config/.cursor/` and `_admin/.cursor/` to their `.claude/` equivalents, establishing the new canonical source directories.

#### P1 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Migration of IDE config source files from `.cursor/` format to `.claude/` format:
> - `_config/.claude/commands/` — 14 command files (direct copy from `_config/.cursor/commands/`)
> - `_config/.claude/rules/` — 7 rule files converted from `.mdc` to `.md` format
> - `_config/.claude/agents/` — agent files converted to Claude-native frontmatter
> - `_config/.claude/skills/` — 8 skill directories (direct copy from `_config/.cursor/skills/`)
> - `_admin/.claude/rules/` — 2 admin rule files converted from `.mdc` to `.md` format
>
> ## Quality Criteria
> 1. All source files from `_config/.cursor/` have corresponding files in `_config/.claude/` (correct count per artifact type)
> 2. Rule files: `.mdc` frontmatter (`globs:` comma string, `alwaysApply:`) correctly converted to Claude `.md` frontmatter (`paths:` YAML array, no `alwaysApply`)
> 3. Agent files: Cursor frontmatter (`readonly: true`) correctly converted to Claude frontmatter (`permissionMode: plan`)
> 4. Command and skill files: body content is identical between source and copy (no unintended modifications)
> 5. All converted files have valid YAML frontmatter (parseable, no syntax errors)
> 6. No `.mdc`-specific fields remain in any `.claude/` file

## Phase 2: Rewrite Installer

**Goal:** Reverse all conversion functions and installation flows in `_config/install-rbtv.py` so the installer reads from `.claude/` source and derives `.cursor/` output.

#### P2 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Installer rewrite in `_config/install-rbtv.py`:
> - Old conversion functions (`_convert_mdc_frontmatter_to_claude`, `_convert_agent_frontmatter_to_claude`) removed
> - New conversion functions (`_convert_claude_rule_to_mdc`, `_convert_claude_agent_to_cursor`) created
> - All `ide_replicate_*_to_claude` functions reversed to `ide_replicate_*_to_cursor`
> - IDE mode flow updated: copies from `_config/.claude/`, derives `.cursor/`
> - Admin mode flow updated: uses `_admin/.claude/` and `_config/.claude/` as source
> - Source directory constants updated throughout
>
> ## Quality Criteria
> 1. No references to old function names remain anywhere in the installer
> 2. `_convert_claude_rule_to_mdc` correctly converts `paths:` YAML array → `globs:` comma string and adds `alwaysApply: true`
> 3. `_convert_claude_agent_to_cursor` correctly converts `permissionMode: plan` → `readonly: true` and strips unsupported fields
> 4. IDE mode copies from `_config/.claude/` (not `_config/.cursor/`) as primary source
> 5. Admin mode copies from `_config/.claude/` and `_admin/.claude/` as sources
> 6. MCP merge logic is unchanged (still reads from `_config/.cursor/mcp.json`)
> 7. Path substitution and reinforcement reminder injection in admin mode are preserved

## Phase 3: Update Documentation

**Goal:** Update all documentation files that reference the old `.cursor/`-as-source direction to reflect the new `.claude/`-as-canonical architecture.

#### P3 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Documentation updates across the repository:
> - `CLAUDE.md` — Installation section updated
> - `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc` — installer documentation updated
> - Other files referencing `_config/.cursor/` as canonical source
>
> ## Quality Criteria
> 1. `CLAUDE.md` Installation section accurately describes the new flow (`.claude/` as source, `.cursor/` as derived)
> 2. `admin-rbtv-bmad-mirror.mdc` installer documentation matches the actual installer behavior
> 3. No remaining references to `_config/.cursor/` as "source of truth" or "canonical" in any documentation file
> 4. All file path references are accurate (point to files that exist or will exist after migration)
> 5. Documentation changes are informational only — no behavioral impact

## Phase 4: Validate & Finalize

**Goal:** Verify the complete migration works end-to-end, clean up old source directories, compound learnings, and get final approval.

#### P4 Checkpoint Review Prompt

> **Use Task tool with `subagent_type='quality-review'` and the following prompt:**
>
> ## Work to Evaluate
> Full migration validation and cleanup:
> - Installer admin mode run produced correct output at rbtv root
> - Old source directories deleted: `_config/.cursor/commands/`, `_config/.cursor/rules/`, `_config/.cursor/agents/`, `_config/.cursor/skills/`, `_admin/.cursor/`
> - Only `_config/.cursor/mcp.json` remains in `_config/.cursor/`
> - All internal markdown links resolve
> - Learnings compounded (if any)
>
> ## Quality Criteria
> 1. Installer runs successfully in admin mode without errors
> 2. Installed output (`.cursor/` and `.claude/` at rbtv root) contains all expected artifacts
> 3. Old source directories are removed — `_config/.cursor/` contains only `mcp.json`
> 4. `_admin/.cursor/` directory is fully removed
> 5. All internal markdown links in plan artifacts resolve correctly
> 6. Zero behavioral changes — installed rules, agents, commands, and skills function identically
