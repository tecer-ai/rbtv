# RBTV Standalone — Intermediary Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform RBTV from a BMAD-integrated module into a standalone git repo that can be bootstrapped into any workspace via `install.py`. Install works by generating thin loaders in the target's `.claude/` directory that point back to RBTV's source — no bulk content copy. Henri's Second Brain vault becomes the first instance.

**Architecture:** RBTV source lives as a self-contained repo with flat top-level directories for `skills/`, `commands/`, `rules/`, `agents/`, `workflows/`, and `tasks/`. Bootstrap generates `.claude/skills/rbtv-*/SKILL.md` thin loaders in the target (with RBTV path and output paths baked in) plus copies `rules/*` content (rules load passively, can't use indirection reliably). Agents, workflows, and tasks stay in the RBTV repo and are referenced by loaders via absolute paths. Overwrite scope on re-install is limited to `rbtv-`-prefixed files plus the user's config file `rbtv.yaml`.

**Tech Stack:** Python 3.11+ (install logic, CLI), PyYAML (manifest + config parsing), Markdown + YAML frontmatter (skills/commands/rules/workflows), XML (tasks), Git (source control).

---

## ✅ Pre-Execution Decisions — Resolved 2026-04-17

**Plan is ready to execute.** An adversarial review (2026-04-16) raised blockers — most were fixed in-place; the remainder were deferred to the open-items table below. All items were resolved on 2026-04-17 (O4 superseded by the D7 rewrite; O1–O3, O5–O9 decided by Henri).

**For the executing agent:** Each row's Decision column specifies the chosen option. Apply them where the relevant task is implemented. If a decision looks ambiguous, ask Henri — do not guess.

### Open Items

| # | Issue | Severity | Proposed options | Decision |
|---|---|---|---|---|
| O1 | **Windows path case-sensitivity in `relative_to()`** — `InstallContext.resolve_from_cli` in Task 28 uses `Path.resolve()` which preserves input case on Windows. If user types `H:/bmad/...` vs `H:/BMAD/...`, `relative_to()` raises with an opaque error. Symlinks also trigger this. D19 (relative paths) sidesteps most of the risk by removing absolute-path baking, but the one-time resolution during install still hits it. | HIGH | **(a)** Add case-insensitive comparison on Windows via `os.path.normcase(os.path.normpath(...))` before `relative_to()`. **(b)** Leave as-is — Henri uses consistent casing. **(c)** Add a diagnostic that prints both resolved paths when the check fails. | **(a)** (2026-04-17) — Normalize via `os.path.normcase(os.path.normpath(...))` before `relative_to()` on Windows. Small fix; prevents opaque errors on case-drift. |
| O2 | **Task 12 rule count mismatch** — Task 12 Step 1 says "Expected: [9 specific files]". Adversarial audit saw only 8 in the repo — one expected file isn't present, OR the reviewer miscounted. Executor will discover on first `git mv` attempt: the command fails silently if a source doesn't exist. | HIGH | **(a)** Before executing Task 12, actually `ls rules/` and replace the hardcoded list in Step 2 with a loop that renames only files that exist. **(b)** Manually verify the list at execution time and fix Step 2 before running. **(c)** Accept a mid-phase hiccup and rely on rollback tag. | **(a)** (2026-04-17) — In Task 12 Step 2, replace the hardcoded 9-file list with `ls rules/` + a loop that renames only files actually present. |
| O3 | **Prefix-based overwrite could delete user-created locals** — If Henri (or future fernando-dispatched component creation) creates a LOCAL-only skill named `.claude/skills/rbtv-my-thing/`, next `install.py` run deletes it. Convention says local-only skills must NOT use `rbtv-` prefix (per D10 + fernando's hybrid scope), but this relies on convention compliance. | HIGH | **(a)** Track installed files in `rbtv.yaml` (`installed_files: [...]`) and delete only that set on re-install, instead of prefix-wildcard. **(b)** Rely on convention; document prominently; accept the risk. **(c)** Add install-time warning if a `rbtv-*` named file exists that's not in the current manifest — ask user to confirm deletion. | **(a)** (2026-04-17) — Track installed files in `rbtv.yaml` as `installed_files: [...]` (list of target-relative paths). `clear_module_installed_files` deletes only that set on re-install, ignoring prefix. Protects Fernando-authored local `rbtv-*` components. |
| O4 | ~~**Fresh install requires 9+ interactive prompts; no `--non-interactive` escape**~~ — Superseded by the 2026-04-17 D7 rewrite. Install now prompts only for modules (scriptable via `--modules`). Output path configuration moved to post-install `/rbtv-output-routing` command (see new Task 26A and the `rbtv-output-resolution` rule). No remaining blocker. | RESOLVED | — | **Resolved by D7 rewrite.** |
| O5 | **Fernando's RBTV-publish-vs-local branching is in SKILL.md (entry), not in workflow** — Task 25 Step 3 puts the "ask user where to publish" instruction in the SKILL.md loader. Once fernando's workflow loads, the SKILL.md body is no longer live context; the workflow itself must implement the branching for it to actually work at component-creation time. | MEDIUM | **(a)** Add a dedicated step to `create-component/workflow.md` that asks "publish to RBTV or local-only?" and branches destination path. The workflow reads `rbtv.yaml` (found via walking up from cwd) to know the RBTV source path for RBTV-publish. **(b)** Drop the local-only escape hatch in this plan — all new components go to RBTV source; defer local-only to a future plan. **(c)** Accept as-is — the SKILL.md imperative may influence fernando's early decisions. | **(a)** (2026-04-17) — Add a dedicated step in `agents/fernando/workflows/create-component/workflow.md` that asks "publish to RBTV source or local-only?" and branches the destination path. Workflow locates `rbtv.yaml` by walking up from cwd to find the RBTV source path for RBTV-publish case. |
| O6 | **Git tag rollback doesn't cover Phase 8 vault commits** — Tag strategy is RBTV-repo-scoped. Phase 8 Tasks 36-37 commit to the VAULT repo. If Phase 8 fails mid-way, vault carries broken state. | MEDIUM | **(a)** Phase 8 runs on a vault-side feature branch (e.g., `feat/rbtv-install`) that can be squash-reverted as a unit if needed. **(b)** Accept — vault commits are small, can be manually reverted. **(c)** Add explicit "rollback procedure for vault" notes to each Phase 8 task. | **(a)** (2026-04-17) — Phase 8 runs on a vault-side feature branch `feat/rbtv-install`. Merge to `main` only after all Phase 8 tasks + Step 6/7 routing setup verify clean. Squash-revertable if anything goes wrong. |
| O7 | **Hard-coded 4-parent traversal in `_find_rbtv_root`** — Task 31 `cli.py` uses `Path(__file__).resolve().parent.parent.parent.parent`. If the installer package structure changes later (e.g., flattening `admin/install/installer/` → `admin/installer/`), this breaks silently. | MEDIUM | **(a)** Walk upward from `__file__` until finding `install.py` or `.git/`. **(b)** Accept — brittle but simple; installer structure is stable. **(c)** Use a sentinel file like `admin/install/.rbtv-root` whose presence marks RBTV root. | **(a)** (2026-04-17) — `_find_rbtv_root` walks upward from `Path(__file__).resolve()` until it finds a parent containing `install.py` AND `admin/install/defaults.yaml`. Self-documenting, adds no new files, survives future structure changes. |
| O8 | **BMAD plugin prereqs not checked at install** — Ana's menu + DomCobb's menu rewrite to invoke `bmad-method-lifecycle:*` and `bmad-pro-skills:*` skills. If Henri's Claude Code doesn't have those plugins, the menu items silently fail. | LOW | **(a)** `install.py` checks `~/.claude/plugins/` for these plugin names and warns if missing. **(b)** Accept — Henri already has them per `~/.claude/plugins/cache/`. Document in README. **(c)** Make these plugin references optional in menus (agent asks user whether plugin is installed). | **(a)** (2026-04-17) — `install.py` checks `~/.claude/plugins/` (or `~/.claude/plugins/cache/`) for `bmad-method-lifecycle` and `bmad-pro-skills`. Print a WARNING at end of install if missing, listing which RBTV menu items will silently fail until installed. Non-blocking. |
| O9 | **`admin/roadmap/` archive files cause false-positive in Task 18 Step 6 grep** — The archive contains historical task files with `{bmad_output}` and `rbtv` references. Task 18 Step 6 greps the entire `H:/BMAD/rbtv` expecting zero matches. Archive files make it fail. | LOW | **(a)** Add `--exclude-dir=admin/roadmap` to the verification grep in Task 18 Step 6. **(b)** Also rewrite archive files (not necessary, they don't execute). | **(a)** (2026-04-17) — Add `--exclude-dir=admin/roadmap` to Task 18 Step 6's verification grep. |

### Rule-collision caveat (finding #7, not an open item)

Finding #7 from the adversarial review — RBTV-installed rules semantically duplicate existing vault rules — was **intentionally excluded from this plan** per Henri's instruction ("totally ignore that second brain exists for this plan"). Henri is handling this via a separate review pass on the RBTV plan. The plan installs `rbtv-audio-aware`, `rbtv-chat-discipline`, `rbtv-reasoning` alongside the existing vault rules, knowing Henri will reconcile after.

### Status

All items resolved 2026-04-17. Proceed to Phase 0.

---

## Why This Plan Exists

This plan is the third in a series on how to organize RBTV + Second Brain:

| Plan | Date | Direction | Status |
|---|---|---|---|
| Migration | 2026-04-14 | Vault absorbs RBTV, archive RBTV | Superseded |
| Standalone (full product) | 2026-04-15 | RBTV absorbs SB, multi-user, onboarding, modular summarizer | Deferred |
| **Intermediary (this plan)** | **2026-04-16** | **RBTV standalone, SB untouched** | **Active** |

**Value of the intermediary:** unblocks Henri's "stop using BMAD as working directory" goal by doing only the mechanical BMAD-decoupling and bootstrap work. Defers all product-design complexity (multi-user onboarding, SB component absorption, modular summarizer, personal-data stripping) to a future full-product plan.

**Post-plan state:**
- RBTV is a standalone git repo that lives inside the vault at `3. Resources/rbtv/`
- Vault has `.claude/skills/rbtv-*/`, `.claude/commands/rbtv-*.md`, `.claude/rules/rbtv-*.md` as thin loaders pointing back to RBTV
- Vault's existing SB components (weekly-review, accountant, vault-ops, etc.) are unchanged
- BMAD root elimination and Tecer repo moves happen in a separate workstream (not this plan)

---

## Decisions Log — Fresh-Context Briefing

This plan was designed through iterative clarification. The rationale below must be preserved during execution, because many tasks are only correct in the context of these decisions.

| # | Decision | Rationale |
|---|---|---|
| D1 | Keep "rbtv" as the product name; strip only `bmad-` prefix from files | User wants the name retained; `bmad-rbtv-*` prefixed files become unprefixed in source but gain `rbtv-` prefix when installed into target `.claude/` for namespace isolation |
| D2 | Flat repo layout — no `_config/`, `claude/`, `system/` wrappers | Nobody runs RBTV directly; bootstrap is the only entry point, so semantic wrapper dirs add noise |
| D3 | Install creates thin loaders, not bulk copies | Single source of truth; `git pull` in RBTV is reflected live; less disk usage; simpler install logic |
| D4 | Rules copied (full content), NOT thin-loaded | Rules load passively into Claude's context; indirection like "see `<path>/rule.md`" is unreliable for rule enforcement |
| D5 | `rbtv-` prefix on installed skills/commands/rules; `_system/rbtv/` NOT used | Prefix identifies RBTV-owned files for overwrite scoping; no `_system/` bloat in target |
| D6 | Re-install overwrites only `.claude/*/rbtv-*` files; preserves `rbtv.yaml`; never touches `_system/` | Protects user customizations and existing SB content |
| D7 | **Output paths resolved at runtime from CLAUDE.md routing blocks; no install-time baking.** (Rewritten 2026-04-17 — supersedes the original bake-or-undefined choice.) Components follow the new `rbtv-output-resolution` rule (Module A): read `## Component Output Routing` block from workspace root CLAUDE.md → descend into sub-project CLAUDE.mds as needed → infer runtime variables (e.g. `{client}`) from conversation context → propose the full path with reasoning → confirm before writing. Setup is handled post-install by the `/rbtv-output-routing` command (Module A) which scans the workspace, reads existing CLAUDE.md files, and interactively writes `## Component Output Routing` blocks (between `<!-- component-routing-start -->` / `<!-- component-routing-end -->` markers) across the workspace hierarchy. `rbtv.yaml` no longer contains an `output_paths` section. | Bake-at-install forces 8 prompts for paths that are often per-project (pitches by client, plans by project, meeting summaries by context) and wrong to freeze at install time. Runtime resolution via CLAUDE.md (1) keeps routing human-readable and version-controlled alongside each project, (2) allows sub-project CLAUDE.mds to override parent routing, (3) makes the routing reusable by non-RBTV agents (vault-ops, weekly-review, future plugins) via a generic `## Component Output Routing` marker, (4) encodes the smart-component behavior (infer → propose → confirm, not blind prompt) once as a rule rather than duplicating in every skill template. Install becomes scriptable (solves O4). |
| D8 | Agent-exclusive workflows and tasks nest under their agent directory | `agents/paul/workflows/business-innovation/` makes ownership clear; shared workflows stay at `workflows/` root |
| D9 | Vivian listed in both modules B and C | She's primary designer (C) but also runs the brandbook visual step (B); listed twice in manifest so either module installs her |
| D10 | Fernando hybrid scope — edit existing RBTV component writes to source; new component asks user (RBTV-publish vs. local-only) | Source-of-truth model preferred; local-only escape hatch for personal skills |
| D11 | `_admin/` renamed to `admin/` (no underscore) | Python-importable without `__init__.py` gymnastics |
| D12 | `bootstrap.py` renamed to `install.py` | User-facing name; entrypoint clarity |
| D13 | `config.yaml` renamed to `defaults.yaml` and moved to `admin/install/` | Disambiguates from target-root `rbtv.yaml` (user choices); install-time only |
| D14 | 4 modules: A (Core, always installed), B (Innovation), C (Work Productivity), D (Writing) | User-assigned; Core holds generic productivity skills, B is paul + business-innovation, C is pitch/design, D is writing |
| D15 | SB components untouched in this plan | Scope boundary; full SB absorption deferred |
| D16 | Henri's Tecer repo moves + BMAD root elimination handled by a separate agent/workstream | Not in this plan |
| D17 | Claude Code subagents in `_config/claude/agents/` kept (not silently deleted). `designer` and `web-research` subagents preserved; `context-distill` and `quality-review` dropped (matching skill drops). Source moves to `rbtv/subagents/`. Installed into target as `.claude/agents/rbtv-<name>.md` (copied like rules, since subagents spawn in fresh context and need self-contained bodies). | Adversarial review flagged: original plan deleted these as part of `admin/claude/` wipe, silently losing designer/web-research dispatch capability via Task tool. Keeping them preserves that capability. |
| D18 | `meeting-summarizer` current state is self-contained in its SKILL.md body. Plan transforms it to BMAD architecture: extract the step logic into `workflows/meeting-summarizer/workflow.md`, make the skill a thin loader that points to the workflow. Remove BMAD-specific project-detection logic; the workflow asks the user (or reads CLAUDE.md) for the transcript's project context instead of assuming `{project-root}/projects/{project}/meetings/`. | Adversarial review flagged: the original plan's templates pointed to a `workflows/meeting-summarizer/workflow.md` that does not exist. First invocation of `/rbtv-meeting-summarizer` would FileNotFound. This decision forces the transformation. |
| D19 | Installer bakes RBTV path as **vault-relative**, not absolute. Source templates use `{rbtv_path}` which the installer substitutes with the relative path from target-root to rbtv-root (e.g., `3. Resources/rbtv`). Claude's Read tool resolves relative paths against its cwd (the workspace root), so loaders work whether the vault stays at `H:/BMAD/projects/second-brain/` or later moves. | Adversarial review flagged (Medium 13): absolute-path baking breaks when the vault moves. The separate plan `2026-04-16-vault-move-preparedness-plan.md` handles broader vault-relocation concerns; this decision handles RBTV's own exposure. |
| D20 | Skill and command loader templates use strong imperative voice: **"CRITICAL — Execute these steps in order"** before numbered instructions. This matches the existing BMAD-RBTV skill style and maximizes model compliance with body instructions. Research confirms Claude Code's docs state: *"the rendered SKILL.md content enters the conversation as a single message and stays there for the rest of the session"* — body is reliably loaded and obeyed, but stronger imperative language reduces the chance of the model responding conversationally instead of loading the referenced persona/workflow. | Adversarial review flagged: the original Task 25 templates weakened the imperative language compared to current RBTV skills. |

---

## Module Architecture

### A — Core (always installed)

| Category | Items |
|---|---|
| Agents | `ana`, `domcobb`, `fernando` |
| Ana-nested workflows | `compound-learning`, `context-handoff`, `add-prompting-knowledge` |
| Domcobb-nested workflows | `problem-structuring`, `problem-structuring-lite` (renamed from `ps-lite`), `prompting-assistance`, `ai-web-project` |
| Fernando-nested workflows | `create-component` (renamed from `build-rbtv-component`) — has `data/component-patterns.md` (repurposed from `_admin/claude/rules/admin-rbtv-component-patterns.md`) |
| Shared workflows | `planning` (renamed from `plan-lifecycle`), `meeting-summarizer` (transformed — see D18), `output-routing` (NEW — post-install CLAUDE.md setup, see D7 and Task 26A), `_shared` |
| Skills → commands | `planning`, `web-research`, `create-component`, `doc`, `domcobb`, `meeting-summarizer`, `output-routing` (NEW — see Task 26A), `playwright-cli` (no command for `playwright-cli` — skill-only) |
| Subagents | `designer`, `web-research` (Claude Code dispatchable subagents, distinct from skill SKILL.md and from BMAD persona files) |
| Rules | `atomic-files`, `audio-aware`, `background-agents`, `bash-patterns`, `chat-discipline`, `context-preservation`, `git-file-ops`, `output-resolution` (NEW — smart-component behavior standard, see D7 and Task 26A), `reasoning`, `source-of-truth` (NEW — repurposed from `admin-rbtv-config-source`) |
| Shared tasks | `web-research.xml` |

### B — Innovation (optional)

| Category | Items |
|---|---|
| Agents | `paul`, `vivian` (also in C) |
| Paul-nested workflows | `business-innovation` (renamed from `bi-business-innovation`) — includes all `bi-m1/`, `bi-m2/`, `bi-m3/`, `bi-m4/` subtrees |
| Paul-nested tasks | `mentor-help.xml` |
| Shared workflows | `product-discovery` (renamed from `pre-product-discovery`) |
| Skills → commands | `mentor`, `product-discovery` |

### C — Work Productivity (optional)

| Category | Items |
|---|---|
| Agents | `leo`, `roelof`, `vivian` (also in B) |
| Shared workflows | `pitch`, `design-extraction` (renamed from `design-token-extraction`) |
| Skills → commands | `client-pitch`, `investor-pitch`, `designer`, `design-extraction` (renamed from `visual-design-extraction`) |

### D — Writing (optional)

| Category | Items |
|---|---|
| Agents | `george-orwell` |
| George-Orwell-nested workflows | `writing` (renamed from `essay`) |
| George-Orwell-nested tasks | `critical-essay-review.xml` |
| Skills → commands | `writing` (renamed from `essay`), `tone-extraction` |
| Shared tasks | `tone-extraction.xml` (at root — C's pitch workflow may reference it) |

### Drops

Removed from RBTV entirely:

| Type | Item | Why |
|---|---|---|
| Skills | `help`, `quality-review`, `reorganize-memory` | Low usage or Claude Code native |
| Rules | `memory-system` | Replaced by Claude Code auto-memory |
| Tasks | `help.xml`, `quality-review.xml`, `context-distill.xml`, `check-bmad-compat.xml`, `restore-bmad-config.xml`, `update-bmad-config.xml` | BMAD-only or tied to dropped skills |
| Subagents | `context-distill`, `quality-review` (the dispatchable versions in `_config/claude/agents/`) | Match the corresponding skill drops |
| `_admin/` contents | `_admin/claude/` — component-patterns and config-source files repurposed; rest deleted | Contents repurposed (see D17a below) or deleted |

**Admin file repurposing (not drops):**
- `_admin/claude/rules/admin-rbtv-component-patterns.md` → becomes `agents/fernando/workflows/create-component/data/component-patterns.md` (workflow data file)
- `_admin/claude/rules/admin-rbtv-config-source.md` → becomes `rules/source-of-truth.md` (Module A rule)
- `_config/claude/agents/bmad-rbtv-designer.md` → becomes `subagents/designer.md` (Module A, installed as `.claude/agents/rbtv-designer.md`)
- `_config/claude/agents/bmad-rbtv-web-research.md` → becomes `subagents/web-research.md` (Module A, installed as `.claude/agents/rbtv-web-research.md`)

---

## Rename Reference

Apply these renames consistently across the plan. **Before renaming, grep the codebase for references and update them.**

### Directory + file renames

| Old path | New path |
|---|---|
| `_config/claude/skills/bmad-rbtv-<name>/` | `rbtv/skills/<name>/` |
| `_config/claude/commands/` | `rbtv/commands/` (NEW — no existing commands) |
| `_config/claude/rules/bmad-rbtv-<name>.md` | `rbtv/rules/<name>.md` |
| `_config/claude/agents/bmad-rbtv-<name>.md` | `rbtv/subagents/<name>.md` (designer, web-research; others dropped) |
| `_config/bootstrap.py` | `rbtv/install.py` (rewritten) |
| `_config/bootstrap/` | `rbtv/admin/install/installer/` |
| `_config/config.yaml` | `rbtv/admin/install/defaults.yaml` (rewritten) |
| `_admin/` | `rbtv/admin/` (no underscore, contents reorganized) |
| `agents/<name>.md` | `rbtv/agents/<name>/<name>.md` |
| `workflows/<wf>/` (single-agent-owned) | `rbtv/agents/<agent>/workflows/<wf>/` |
| `workflows/<wf>/` (shared) | `rbtv/workflows/<wf>/` |
| `tasks/<name>.xml` (single-agent-owned) | `rbtv/agents/<agent>/tasks/<name>.xml` |
| `tasks/<name>.xml` (shared) | `rbtv/tasks/<name>.xml` |

### Workflow renames

| Old | New |
|---|---|
| `plan-lifecycle` | `planning` |
| `essay` | `writing` |
| `build-rbtv-component` | `create-component` |
| `bi-business-innovation` | `business-innovation` |
| `pre-product-discovery` | `product-discovery` |
| `ps-lite` | `problem-structuring-lite` |
| `design-token-extraction` | `design-extraction` |

### Skill renames (beyond prefix strip)

| Old | New |
|---|---|
| `bmad-rbtv-plan` | `planning` |
| `bmad-rbtv-essay` | `writing` |
| `bmad-rbtv-visual-design-extraction` | `design-extraction` |

All other `bmad-rbtv-<name>` skills drop the `bmad-rbtv-` prefix only.

### Path variable substitutions

These appear throughout agent/workflow files. Replace with placeholders that the installer will bake at install time.

| Old | New (in RBTV source) | Baked by installer to |
|---|---|---|
| `{project-root}/` | `{rbtv_path}/` | Absolute path to RBTV repo in target |
| `{bmad_rbtv}/` | `{rbtv_path}/` | Same |
| `{bmad_output}` | *(delete the reference entirely from source — output resolution is runtime, per the `rbtv-output-resolution` rule; see D7)* | — |
| `{bmad_core}/...` | *(delete line, possibly replace with plugin invocation)* | — |
| `{bmad_bmm}/...` | *(delete line, possibly replace with plugin invocation)* | — |
| `{bmad_cis}/...` | *(delete line, possibly replace with plugin invocation)* | — |

### BMAD-specific frontmatter fields to delete

- `advancedElicitationTask:`
- `partyModeWorkflow:`
- `main_config:`
- `parentWorkflow:`
- `validateWorkflow:`

Keep `name:`, `description:`, `nextStep:`, `nextStepFile:`, `outputFile:`, `outputFolder:`, `knowledgeFile:`.

### BMAD menu items to delete or replace

| Pattern | Action |
|---|---|
| `[AE]` or `Advanced Elicitation` rows in step menus | Delete the row |
| `[PM]`, `[P]`, or `Party Mode` rows | Delete the row |
| `[B]` Brief in Ana's menu | Replace with: *"Invoke `bmad-method-lifecycle:bmad-product-brief` skill"* |
| `[PRD]` in Ana's menu | Replace with: *"Invoke `bmad-method-lifecycle:bmad-create-prd` skill"* |
| `[UX]` in Ana's menu | Replace with: *"Invoke `bmad-method-lifecycle:bmad-create-ux-design` skill"* |
| `[PV]` Problem Solving in DomCobb's menu | Replace with: *"Invoke `bmad-pro-skills:bmad-problem-solving` skill"* |

---

## Target RBTV Repo Structure (post-plan)

```
rbtv/
├── README.md                            # NEW — product overview
├── install.py                           # NEW entrypoint (thin; imports from admin/install/)
├── admin/                               # RENAMED from _admin, scope expanded
│   ├── install/
│   │   ├── installer/                   # Python package
│   │   │   ├── __init__.py
│   │   │   ├── cli.py                   # CLI arg parsing + module prompt (output paths NOT configured here; see D7)
│   │   │   ├── context.py               # Resolves paths: rbtv_path, target_path
│   │   │   ├── manifest.py              # Reads module-manifest.yaml
│   │   │   ├── generator.py             # Writes thin loaders, copies rules
│   │   │   └── state.py                 # Reads/writes rbtv.yaml in target
│   │   ├── defaults.yaml                # Install defaults (NEW — renamed from config.yaml)
│   │   └── module-manifest.yaml         # NEW — source→target mapping + module assignment
│   ├── roadmap.md                       # Existing or rewrite
│   └── vision.md                        # Existing or rewrite
├── skills/                              # Skill source templates (used by installer to generate loaders)
│   ├── planning/SKILL.md                # Renamed from bmad-rbtv-plan
│   ├── web-research/SKILL.md
│   ├── create-component/SKILL.md
│   ├── doc/SKILL.md
│   ├── domcobb/SKILL.md
│   ├── meeting-summarizer/SKILL.md
│   ├── output-routing/SKILL.md          # NEW — post-install CLAUDE.md routing setup (see Task 26A)
│   ├── playwright-cli/                  # Kept as-is
│   │   └── SKILL.md
│   ├── mentor/SKILL.md
│   ├── product-discovery/SKILL.md
│   ├── client-pitch/SKILL.md
│   ├── investor-pitch/SKILL.md
│   ├── designer/SKILL.md
│   ├── design-extraction/SKILL.md       # Renamed from bmad-rbtv-visual-design-extraction
│   ├── writing/SKILL.md                 # Renamed from bmad-rbtv-essay
│   └── tone-extraction/SKILL.md
├── commands/                            # NEW — one file per skill (1:1), thin
│   ├── planning.md
│   ├── web-research.md
│   ├── create-component.md
│   ├── doc.md
│   ├── domcobb.md
│   ├── meeting-summarizer.md
│   ├── output-routing.md                # NEW — user-facing /rbtv-output-routing entry (see Task 26A)
│   ├── mentor.md
│   ├── product-discovery.md
│   ├── client-pitch.md
│   ├── investor-pitch.md
│   ├── designer.md
│   ├── design-extraction.md
│   ├── writing.md
│   └── tone-extraction.md
├── rules/
│   ├── atomic-files.md                  # Was bmad-rbtv-atomic-files
│   ├── audio-aware.md
│   ├── background-agents.md
│   ├── bash-patterns.md
│   ├── chat-discipline.md
│   ├── context-preservation.md
│   ├── git-file-ops.md
│   ├── output-resolution.md             # NEW — smart-component behavior standard (see Task 26A)
│   ├── reasoning.md
│   └── source-of-truth.md               # NEW — from admin-rbtv-config-source
├── subagents/                           # NEW — Claude Code dispatchable subagents (separate from agent personas)
│   ├── designer.md                      # Was _config/claude/agents/bmad-rbtv-designer
│   └── web-research.md                  # Was _config/claude/agents/bmad-rbtv-web-research
├── agents/
│   ├── ana/
│   │   ├── ana.md
│   │   └── workflows/
│   │       ├── compound-learning/
│   │       ├── context-handoff/
│   │       └── add-prompting-knowledge/
│   ├── domcobb/
│   │   ├── domcobb.md
│   │   └── workflows/
│   │       ├── problem-structuring/
│   │       ├── problem-structuring-lite/
│   │       ├── prompting-assistance/
│   │       └── ai-web-project/
│   ├── fernando/
│   │   ├── fernando.md
│   │   └── workflows/
│   │       └── create-component/
│   │           ├── workflow.md
│   │           └── data/
│   │               └── component-patterns.md
│   ├── george-orwell/
│   │   ├── george-orwell.md
│   │   ├── workflows/
│   │   │   └── writing/
│   │   └── tasks/
│   │       └── critical-essay-review.xml
│   ├── paul/
│   │   ├── paul.md
│   │   ├── workflows/
│   │   │   └── business-innovation/   # Full bi-m1/, bi-m2/, bi-m3/, bi-m4/ tree
│   │   └── tasks/
│   │       └── mentor-help.xml
│   ├── leo/
│   │   └── leo.md
│   ├── roelof/
│   │   └── roelof.md
│   └── vivian/
│       └── vivian.md
├── workflows/                           # Shared-only workflows
│   ├── _shared/
│   ├── pitch/
│   ├── planning/
│   ├── product-discovery/
│   ├── design-extraction/
│   ├── output-routing/                  # NEW — interactive CLAUDE.md routing setup (see Task 26A)
│   │   └── workflow.md
│   └── meeting-summarizer/              # Transformed in Task 18a
│       ├── workflow.md                  # NEW — content extracted from old SKILL.md body
│       └── universal-prompt.md          # Existing fallback summarization prompt
└── tasks/                               # Shared-only tasks
    ├── tone-extraction.xml
    └── web-research.xml
```

## Target Instance Structure (post-install, in Henri's vault)

```
<vault-root>/
├── rbtv.yaml                            # NEW — user's install config (RBTV path, modules). NO output paths — those live in workspace CLAUDE.md files; see D7.
├── CLAUDE.md                            # Existing — augmented (post-install) with `## Component Output Routing` block via /rbtv-output-routing
├── .claude/
│   ├── skills/
│   │   ├── rbtv-planning/SKILL.md       # THIN LOADER
│   │   ├── rbtv-web-research/SKILL.md
│   │   ├── rbtv-create-component/SKILL.md
│   │   ├── rbtv-doc/SKILL.md
│   │   ├── rbtv-domcobb/SKILL.md
│   │   ├── rbtv-meeting-summarizer/SKILL.md
│   │   ├── rbtv-output-routing/SKILL.md # NEW — thin loader for post-install routing setup
│   │   ├── rbtv-playwright-cli/SKILL.md
│   │   ├── rbtv-mentor/SKILL.md
│   │   ├── rbtv-product-discovery/SKILL.md
│   │   ├── rbtv-client-pitch/SKILL.md
│   │   ├── rbtv-investor-pitch/SKILL.md
│   │   ├── rbtv-designer/SKILL.md
│   │   ├── rbtv-design-extraction/SKILL.md
│   │   ├── rbtv-writing/SKILL.md
│   │   └── rbtv-tone-extraction/SKILL.md
│   ├── commands/
│   │   ├── rbtv-output-routing.md       # NEW — /rbtv-output-routing slash command
│   │   └── rbtv-<name>.md               # one per skill (except playwright-cli)
│   ├── rules/
│   │   ├── rbtv-atomic-files.md         # COPIED CONTENT (not a loader)
│   │   ├── rbtv-audio-aware.md
│   │   ├── rbtv-background-agents.md
│   │   ├── rbtv-bash-patterns.md
│   │   ├── rbtv-chat-discipline.md
│   │   ├── rbtv-context-preservation.md
│   │   ├── rbtv-git-file-ops.md
│   │   ├── rbtv-output-resolution.md    # NEW — smart-component behavior standard (COPIED CONTENT)
│   │   ├── rbtv-reasoning.md
│   │   └── rbtv-source-of-truth.md
│   └── agents/                           # NEW — Claude Code dispatchable subagents
│       ├── rbtv-designer.md             # COPIED CONTENT (not a loader)
│       └── rbtv-web-research.md
├── 3. Resources/
│   └── rbtv/                            # The RBTV repo itself (moved here in Phase 7)
│       └── ...
└── _system/                             # NOT touched by RBTV install
    └── ...                              # SB content stays as-is
```

---

## Rollback Strategy

Each phase starts with a git tag checkpoint. All work happens on feature branch `feat/rbtv-standalone` in the RBTV repo.

```bash
git -C "H:/BMAD/rbtv" checkout -b feat/rbtv-standalone
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-0-start
```

Before each phase: `git -C "<rbtv>" tag rbtv-standalone-phase-N-start`.
To roll back: `git -C "<rbtv>" reset --hard rbtv-standalone-phase-N-start`.

Only merge to main after Phase 5 verification passes. Phases 6-7 happen post-merge.

---

## Phase 0: Branch + Backup

### Task 0: Create feature branch and initial tag

**Files:** none modified.

- [ ] **Step 1: Verify RBTV repo is clean**

```bash
git -C "H:/BMAD/rbtv" status
```

Expected: "nothing to commit, working tree clean". If dirty, commit or stash before proceeding.

- [ ] **Step 2: Create feature branch**

```bash
git -C "H:/BMAD/rbtv" checkout -b feat/rbtv-standalone
```

- [ ] **Step 3: Tag starting state**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-0-start
```

- [ ] **Step 4: Push branch and tag to remote (if one exists)**

```bash
git -C "H:/BMAD/rbtv" push -u origin feat/rbtv-standalone
git -C "H:/BMAD/rbtv" push origin rbtv-standalone-phase-0-start
```

Skip if no remote is configured.

---

## Phase 1: Flatten Repo Structure

**Goal:** Remove the `_config/` wrapper, move `_admin/` → `admin/`, hoist skills/commands/rules/agents/workflows/tasks to repo root.

### Task 1: Move _config contents to root

**Files:**
- Move: `_config/claude/skills/` → `skills/`
- Move: `_config/claude/rules/` → `rules/`
- Move: `_config/config.yaml` → `admin/install/defaults.yaml` (deferred rewrite to Task 15)
- Move: `_config/bootstrap/` → `admin/install/installer/` (deferred rewrite to Task 18)
- Move: `_config/bootstrap.py` → `install.py` (deferred rewrite to Task 19)

- [ ] **Step 1: Create destination directories**

```bash
mkdir -p "H:/BMAD/admin/install"
```

- [ ] **Step 2: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-1-start
```

- [ ] **Step 3: Move skills directory**

```bash
git -C "H:/BMAD/rbtv" mv _config/claude/skills skills
```

- [ ] **Step 4: Move rules directory**

```bash
git -C "H:/BMAD/rbtv" mv _config/claude/rules rules
```

- [ ] **Step 5: Create commands directory (empty, files added in later tasks)**

```bash
mkdir -p "H:/BMAD/commands"
```

- [ ] **Step 6: Move config.yaml to admin/install/defaults.yaml**

```bash
git -C "H:/BMAD/rbtv" mv _config/config.yaml admin/install/defaults.yaml
```

- [ ] **Step 7: Move bootstrap package**

```bash
git -C "H:/BMAD/rbtv" mv _config/bootstrap admin/install/installer
```

- [ ] **Step 8: Move bootstrap.py to root as install.py**

```bash
git -C "H:/BMAD/rbtv" mv _config/bootstrap.py install.py
```

- [ ] **Step 9: Remove now-empty _config directory**

```bash
rm -rf "H:/BMAD/_config"
```

- [ ] **Step 10: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor: flatten _config wrapper — skills/rules/commands at root, install in admin/install/"
```

---

### Task 2: Rename _admin to admin

**Files:**
- Move: `_admin/` → `admin/` (merging with existing `admin/install/` created in Task 1)

- [ ] **Step 1: Move _admin contents into admin/**

The `admin/install/` subdirectory already exists from Task 1. The `_admin/` directory contains roadmap/vision docs plus the `claude/` subdirectory to be processed in Task 3. Move the non-install-conflicting contents:

```bash
git -C "H:/BMAD/rbtv" mv _admin/roadmap.md admin/roadmap.md 2>/dev/null || echo "roadmap.md not present, skipping"
```

Use this pattern for any top-level files in `_admin/` (roadmap.md, vision.md, or similar). Check with:

```bash
ls "H:/BMAD/_admin"
```

For each top-level `.md` file, move it:

```bash
git -C "H:/BMAD/rbtv" mv _admin/<filename> admin/<filename>
```

- [ ] **Step 2: Move _admin/claude to admin/claude (temporary — processed in Task 3)**

```bash
git -C "H:/BMAD/rbtv" mv _admin/claude admin/claude
```

- [ ] **Step 3: Move any remaining _admin/ subdirs (e.g., _admin/docs/)**

```bash
ls "H:/BMAD/_admin"
```

For each remaining subdir:

```bash
git -C "H:/BMAD/rbtv" mv _admin/<subdir> admin/<subdir>
```

- [ ] **Step 4: Remove now-empty _admin/**

```bash
rmdir "H:/BMAD/_admin"
```

- [ ] **Step 5: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor: rename _admin to admin (Python-importable)"
```

---

### Task 3: Repurpose admin/claude files, delete admin/claude/

**Files:**
- Move: `admin/claude/rules/admin-rbtv-component-patterns.md` → `agents/fernando/workflows/create-component/data/component-patterns.md` (executed in Task 6 after fernando nesting)
- Move: `admin/claude/rules/admin-rbtv-config-source.md` → `rules/source-of-truth.md`
- Delete: `admin/claude/` (remaining contents)

- [ ] **Step 1: Stage the source-of-truth rule move**

```bash
git -C "H:/BMAD/rbtv" mv admin/claude/rules/admin-rbtv-config-source.md rules/source-of-truth.md
```

- [ ] **Step 2: Update frontmatter of the new rule**

Read the file. Update the frontmatter to reflect the new name and scope. Expected final frontmatter:

```markdown
---
description: "RBTV source files are overwritten on re-install. Edit in RBTV source repo (location in rbtv.yaml), then re-run install.py to propagate."
---
```

Body should retain the original content but with path references updated: `{rbtv_path}/` replaces any `{bmad_rbtv}/` or `{project-root}/` patterns.

- [ ] **Step 3: Temporarily stash the component-patterns file**

We cannot move it to its final destination yet (fernando nesting happens in Task 6). Keep it in place for now:

```bash
ls "H:/BMAD/admin/claude/rules/admin-rbtv-component-patterns.md"
```

Expected: file exists. Leave it — Task 6 will move it.

- [ ] **Step 4: Commit the source-of-truth rule**

```bash
git -C "H:/BMAD/rbtv" add rules/source-of-truth.md
git -C "H:/BMAD/rbtv" commit -m "refactor(rules): extract source-of-truth rule from _admin/claude/"
```

Do NOT add `admin/claude/rules/` in this commit — the component-patterns file will be moved in Task 7 (Fernando nesting). Adding the directory here would stage that move prematurely.

---

### Task 3a: Migrate Claude Code subagents from _config/claude/agents/

**Context:** `_config/claude/agents/` (now `admin/claude/agents/` after Task 2) contains 4 Claude Code subagent files — `bmad-rbtv-designer.md`, `bmad-rbtv-web-research.md`, `bmad-rbtv-quality-review.md`, `bmad-rbtv-context-distill.md`. These are **dispatchable subagents** (invoked via the Task tool in a fresh context), NOT BMAD persona files at `agents/*.md`. They survive Task 3 and must be classified, migrated, or dropped BEFORE Task 22 deletes `admin/claude/`.

**Files:**
- Move: `admin/claude/agents/bmad-rbtv-designer.md` → `subagents/designer.md`
- Move: `admin/claude/agents/bmad-rbtv-web-research.md` → `subagents/web-research.md`
- Delete: `admin/claude/agents/bmad-rbtv-quality-review.md` (matches skill drop)
- Delete: `admin/claude/agents/bmad-rbtv-context-distill.md` (matches skill drop — Claude Code does context distillation natively)

- [ ] **Step 1: Create `rbtv/subagents/` directory**

```bash
mkdir -p "H:/BMAD/subagents"
```

- [ ] **Step 2: Move and rename the two kept subagents**

```bash
git -C "H:/BMAD/rbtv" mv admin/claude/agents/bmad-rbtv-designer.md subagents/designer.md
git -C "H:/BMAD/rbtv" mv admin/claude/agents/bmad-rbtv-web-research.md subagents/web-research.md
```

- [ ] **Step 3: Delete the two dropped subagents**

```bash
git -C "H:/BMAD/rbtv" rm admin/claude/agents/bmad-rbtv-quality-review.md
git -C "H:/BMAD/rbtv" rm admin/claude/agents/bmad-rbtv-context-distill.md
```

- [ ] **Step 4: Update the frontmatter `name:` field in each moved subagent**

Open `subagents/designer.md`. Change the `name:` field from `bmad-rbtv-designer` to `rbtv-designer`. Do the same for `subagents/web-research.md` → `rbtv-web-research`.

Note: subagents install directly as `.claude/agents/rbtv-<name>.md` with no renaming, so the `name:` field in the source must already be `rbtv-<name>`.

- [ ] **Step 5: Verify directory is cleared of subagents**

```bash
ls "H:/BMAD/admin/claude/agents"
```

Expected: empty (or directory does not exist). If other files unexpectedly remain, inspect and decide.

- [ ] **Step 6: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(subagents): migrate dispatchable subagents to rbtv/subagents/, drop context-distill and quality-review"
```

---

## Phase 2: Nest Agents, Workflows, Tasks

**Goal:** Move each agent into its own directory (`agents/<name>/<name>.md`). Nest single-agent-owned workflows and tasks under their agent's directory. Keep shared workflows/tasks at top-level.

### Task 4: Create agent subdirectories and move agent files

**Files:**
- Move: `agents/ana.md` → `agents/ana/ana.md`
- Move: `agents/domcobb.md` → `agents/domcobb/domcobb.md`
- Move: `agents/fernando.md` → `agents/fernando/fernando.md`
- Move: `agents/george-orwell.md` → `agents/george-orwell/george-orwell.md`
- Move: `agents/paul.md` → `agents/paul/paul.md`
- Move: `agents/leo.md` → `agents/leo/leo.md`
- Move: `agents/roelof.md` → `agents/roelof/roelof.md`
- Move: `agents/vivian.md` → `agents/vivian/vivian.md`

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-2-start
```

- [ ] **Step 2: Create subdirectories**

```bash
mkdir -p "H:/BMAD/agents/ana" "H:/BMAD/agents/domcobb" "H:/BMAD/agents/fernando" "H:/BMAD/agents/george-orwell" "H:/BMAD/agents/paul" "H:/BMAD/agents/leo" "H:/BMAD/agents/roelof" "H:/BMAD/agents/vivian"
```

- [ ] **Step 3: Move each agent file**

```bash
git -C "H:/BMAD/rbtv" mv agents/ana.md agents/ana/ana.md
git -C "H:/BMAD/rbtv" mv agents/domcobb.md agents/domcobb/domcobb.md
git -C "H:/BMAD/rbtv" mv agents/fernando.md agents/fernando/fernando.md
git -C "H:/BMAD/rbtv" mv agents/george-orwell.md agents/george-orwell/george-orwell.md
git -C "H:/BMAD/rbtv" mv agents/paul.md agents/paul/paul.md
git -C "H:/BMAD/rbtv" mv agents/leo.md agents/leo/leo.md
git -C "H:/BMAD/rbtv" mv agents/roelof.md agents/roelof/roelof.md
git -C "H:/BMAD/rbtv" mv agents/vivian.md agents/vivian/vivian.md
```

- [ ] **Step 4: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents): nest each agent into its own directory"
```

---

### Task 5: Nest Ana's workflows

**Files:**
- Move: `workflows/compound-learning/` → `agents/ana/workflows/compound-learning/`
- Move: `workflows/context-handoff/` → `agents/ana/workflows/context-handoff/`
- Move: `workflows/add-prompting-knowledge/` → `agents/ana/workflows/add-prompting-knowledge/`

- [ ] **Step 1: Create ana's workflows subdirectory**

```bash
mkdir -p "H:/BMAD/agents/ana/workflows"
```

- [ ] **Step 2: Move workflows**

```bash
git -C "H:/BMAD/rbtv" mv workflows/compound-learning agents/ana/workflows/compound-learning
git -C "H:/BMAD/rbtv" mv workflows/context-handoff agents/ana/workflows/context-handoff
git -C "H:/BMAD/rbtv" mv workflows/add-prompting-knowledge agents/ana/workflows/add-prompting-knowledge
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/ana): nest doc workflows under ana"
```

---

### Task 6: Nest DomCobb's workflows + rename ps-lite

**Files:**
- Move: `workflows/problem-structuring/` → `agents/domcobb/workflows/problem-structuring/`
- Move: `workflows/ps-lite/` → `agents/domcobb/workflows/problem-structuring-lite/` (rename)
- Move: `workflows/prompting-assistance/` → `agents/domcobb/workflows/prompting-assistance/`
- Move: `workflows/ai-web-project/` → `agents/domcobb/workflows/ai-web-project/`

- [ ] **Step 1: Create subdirectory**

```bash
mkdir -p "H:/BMAD/agents/domcobb/workflows"
```

- [ ] **Step 2: Move + rename**

```bash
git -C "H:/BMAD/rbtv" mv workflows/problem-structuring agents/domcobb/workflows/problem-structuring
git -C "H:/BMAD/rbtv" mv workflows/ps-lite agents/domcobb/workflows/problem-structuring-lite
git -C "H:/BMAD/rbtv" mv workflows/prompting-assistance agents/domcobb/workflows/prompting-assistance
git -C "H:/BMAD/rbtv" mv workflows/ai-web-project agents/domcobb/workflows/ai-web-project
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/domcobb): nest problem-structuring workflows, rename ps-lite → problem-structuring-lite"
```

---

### Task 7: Nest Fernando's workflow + component-patterns data file

**Files:**
- Move: `workflows/build-rbtv-component/` → `agents/fernando/workflows/create-component/` (rename)
- Move: `admin/claude/rules/admin-rbtv-component-patterns.md` → `agents/fernando/workflows/create-component/data/component-patterns.md`

- [ ] **Step 1: Create fernando's workflows subdirectory**

```bash
mkdir -p "H:/BMAD/agents/fernando/workflows"
```

- [ ] **Step 2: Move + rename the workflow**

```bash
git -C "H:/BMAD/rbtv" mv workflows/build-rbtv-component agents/fernando/workflows/create-component
```

- [ ] **Step 3: Move the component-patterns file into workflow's data/**

```bash
mkdir -p "H:/BMAD/agents/fernando/workflows/create-component/data"
git -C "H:/BMAD/rbtv" mv admin/claude/rules/admin-rbtv-component-patterns.md agents/fernando/workflows/create-component/data/component-patterns.md
```

- [ ] **Step 4: Update the component-patterns.md header**

Open `agents/fernando/workflows/create-component/data/component-patterns.md`. The previous file was a rule (loaded passively). It is now a data file read by the workflow. Remove the rule frontmatter (if any) and add a one-line intro at the top:

```markdown
# Component Patterns

Reference data for the create-component workflow. Defines size limits, required sections, and structural requirements for each component type (agent, skill, workflow, step, task, rule).

[... existing content unchanged below this line ...]
```

- [ ] **Step 5: Update the workflow to reference the data file**

Open `agents/fernando/workflows/create-component/workflow.md`. Add or verify a `knowledgeFile` frontmatter entry:

```markdown
---
name: create-component
description: ...
knowledgeFile: "{rbtv_path}/agents/fernando/workflows/create-component/data/component-patterns.md"
---
```

If the workflow references component patterns in its body, update paths accordingly.

- [ ] **Step 6: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/fernando): nest create-component workflow, promote component-patterns to workflow data"
```

---

### Task 8: Nest George Orwell's workflow + task

**Files:**
- Move: `workflows/essay/` → `agents/george-orwell/workflows/writing/` (rename)
- Move: `tasks/critical-essay-review.xml` → `agents/george-orwell/tasks/critical-essay-review.xml`

- [ ] **Step 1: Create subdirectories**

```bash
mkdir -p "H:/BMAD/agents/george-orwell/workflows"
mkdir -p "H:/BMAD/agents/george-orwell/tasks"
```

- [ ] **Step 2: Move + rename workflow**

```bash
git -C "H:/BMAD/rbtv" mv workflows/essay agents/george-orwell/workflows/writing
```

- [ ] **Step 3: Move task**

```bash
git -C "H:/BMAD/rbtv" mv tasks/critical-essay-review.xml agents/george-orwell/tasks/critical-essay-review.xml
```

- [ ] **Step 4: Update workflow frontmatter name**

Open `agents/george-orwell/workflows/writing/workflow.md`. Change:

```markdown
---
name: essay
```

To:

```markdown
---
name: writing
```

- [ ] **Step 5: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/george-orwell): nest writing workflow (renamed from essay) and critical-essay-review task"
```

---

### Task 9: Nest Paul's workflow + task

**Files:**
- Move: `workflows/bi-business-innovation/` → `agents/paul/workflows/business-innovation/` (rename)
- Move: `tasks/mentor-help.xml` → `agents/paul/tasks/mentor-help.xml`

- [ ] **Step 1: Create subdirectories**

```bash
mkdir -p "H:/BMAD/agents/paul/workflows"
mkdir -p "H:/BMAD/agents/paul/tasks"
```

- [ ] **Step 2: Move + rename workflow**

```bash
git -C "H:/BMAD/rbtv" mv workflows/bi-business-innovation agents/paul/workflows/business-innovation
```

- [ ] **Step 3: Move task**

```bash
git -C "H:/BMAD/rbtv" mv tasks/mentor-help.xml agents/paul/tasks/mentor-help.xml
```

- [ ] **Step 4: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/paul): nest business-innovation workflow (renamed from bi-business-innovation) and mentor-help task"
```

---

### Task 10: Rename shared workflows + drop dead ones

**Files:**
- Rename: `workflows/plan-lifecycle/` → `workflows/planning/`
- Rename: `workflows/pre-product-discovery/` → `workflows/product-discovery/`
- Rename: `workflows/design-token-extraction/` → `workflows/design-extraction/`
- `workflows/pitch/` → no rename
- `workflows/meeting-summarizer/` → no rename
- `workflows/_shared/` → no rename

- [ ] **Step 1: Rename shared workflows**

```bash
git -C "H:/BMAD/rbtv" mv workflows/plan-lifecycle workflows/planning
git -C "H:/BMAD/rbtv" mv workflows/pre-product-discovery workflows/product-discovery
git -C "H:/BMAD/rbtv" mv workflows/design-token-extraction workflows/design-extraction
```

- [ ] **Step 2: Update workflow.md frontmatter names**

For each renamed workflow, open its `workflow.md` and update the `name:` frontmatter to match the new directory name.

- `workflows/planning/workflow.md`: `name: planning`
- `workflows/product-discovery/workflow.md`: `name: product-discovery`
- `workflows/design-extraction/workflow.md`: `name: design-extraction`

- [ ] **Step 3: Verify no unmoved workflows remain at `workflows/`**

```bash
ls "H:/BMAD/workflows"
```

Expected contents: `_shared`, `meeting-summarizer`, `pitch`, `planning`, `product-discovery`, `design-extraction`. If any others appear, they should either be moved to an agent subdirectory (Task 5-9) or explicitly decided as shared.

- [ ] **Step 4: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(workflows): rename shared workflows — planning, product-discovery, design-extraction"
```

---

## Phase 3: Strip bmad-rbtv Prefixes

**Goal:** Rename all `bmad-rbtv-*` skill directories and `bmad-rbtv-*.md` rule files to unprefixed names. Fix internal references.

### Task 11: Rename skill directories

**Files:** all directories under `skills/` matching `bmad-rbtv-*`.

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-3-start
```

- [ ] **Step 2: List current bmad-rbtv-* skill directories**

```bash
ls "H:/BMAD/skills"
```

Expected matches: `bmad-rbtv-plan`, `bmad-rbtv-help`, `bmad-rbtv-quality-review`, `bmad-rbtv-tone-extraction`, `bmad-rbtv-visual-design-extraction`, `bmad-rbtv-web-research`, `bmad-rbtv-reorganize-memory`, `bmad-rbtv-client-pitch`, `bmad-rbtv-create-component`, `bmad-rbtv-designer`, `bmad-rbtv-doc`, `bmad-rbtv-domcobb`, `bmad-rbtv-essay`, `bmad-rbtv-investor-pitch`, `bmad-rbtv-meeting-summarizer`, `bmad-rbtv-mentor`, `bmad-rbtv-product-discovery`.

- [ ] **Step 3: Rename each to unprefixed (including renames plan→planning, essay→writing, visual-design-extraction→design-extraction)**

```bash
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-plan skills/planning
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-help skills/help
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-quality-review skills/quality-review
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-tone-extraction skills/tone-extraction
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-visual-design-extraction skills/design-extraction
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-web-research skills/web-research
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-reorganize-memory skills/reorganize-memory
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-client-pitch skills/client-pitch
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-create-component skills/create-component
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-designer skills/designer
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-doc skills/doc
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-domcobb skills/domcobb
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-essay skills/writing
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-investor-pitch skills/investor-pitch
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-meeting-summarizer skills/meeting-summarizer
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-mentor skills/mentor
git -C "H:/BMAD/rbtv" mv skills/bmad-rbtv-product-discovery skills/product-discovery
```

- [ ] **Step 4: Update skill frontmatter `name:` field**

For each renamed skill, open `skills/<name>/SKILL.md` and update the `name:` frontmatter to match the new directory name.

Example — `skills/planning/SKILL.md`:

```markdown
---
name: planning
description: ...
---
```

Verify for all 17 renamed skills.

- [ ] **Step 5: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(skills): strip bmad-rbtv prefix, rename plan→planning, essay→writing, visual-design-extraction→design-extraction"
```

---

### Task 12: Rename rule files

**Files:** all files under `rules/` matching `bmad-rbtv-*.md`.

- [ ] **Step 1: List current rule files**

```bash
ls "H:/BMAD/rules"
```

Expected: `bmad-rbtv-atomic-files.md`, `bmad-rbtv-audio-aware.md`, `bmad-rbtv-background-agents.md`, `bmad-rbtv-bash-patterns.md`, `bmad-rbtv-chat-discipline.md`, `bmad-rbtv-context-preservation.md`, `bmad-rbtv-git-file-ops.md`, `bmad-rbtv-memory-system.md`, `bmad-rbtv-reasoning.md`, `source-of-truth.md` (already renamed in Task 3).

- [ ] **Step 2: Rename each**

```bash
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-atomic-files.md rules/atomic-files.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-audio-aware.md rules/audio-aware.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-background-agents.md rules/background-agents.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-bash-patterns.md rules/bash-patterns.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-chat-discipline.md rules/chat-discipline.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-context-preservation.md rules/context-preservation.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-git-file-ops.md rules/git-file-ops.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-memory-system.md rules/memory-system.md
git -C "H:/BMAD/rbtv" mv rules/bmad-rbtv-reasoning.md rules/reasoning.md
```

(`source-of-truth.md` already renamed in Task 3.)

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(rules): strip bmad-rbtv prefix from all rule files"
```

---

### Task 13: Fix internal references to renamed paths

**Files:** any file in `rbtv/` that references an old path.

- [ ] **Step 1: Scan for legacy references**

Use Grep across the entire RBTV repo:

```bash
grep -rn "bmad-rbtv-" "H:/BMAD/rbtv"
```

Every result is a reference that must be updated. Common patterns:

- `bmad-rbtv-designer` → `designer` (or `rbtv-designer` if referring to installed target — see note below)
- `bmad-rbtv-plan` → `planning` (note: rename, not just prefix strip)
- `bmad-rbtv-essay` → `writing` (rename)
- `bmad-rbtv-visual-design-extraction` → `design-extraction` (rename)

**Note on dual-naming:** within RBTV source, refer to skills by unprefixed name (`designer`). When referring to the INSTALLED skill in a target vault, use `rbtv-designer`. Thin loaders in target reference the source by unprefixed name via `{rbtv_path}/skills/designer/SKILL.md`.

- [ ] **Step 2: Fix workflow path references**

Search for old workflow paths now moved under agents:

```bash
grep -rn "workflows/plan-lifecycle\|workflows/essay\|workflows/build-rbtv-component\|workflows/bi-business-innovation\|workflows/pre-product-discovery\|workflows/design-token-extraction\|workflows/problem-structuring\|workflows/ps-lite\|workflows/prompting-assistance\|workflows/ai-web-project\|workflows/compound-learning\|workflows/context-handoff\|workflows/add-prompting-knowledge" "H:/BMAD/rbtv"
```

For each result, update to the new path:

| Old | New |
|---|---|
| `workflows/plan-lifecycle/` | `workflows/planning/` |
| `workflows/essay/` | `agents/george-orwell/workflows/writing/` |
| `workflows/build-rbtv-component/` | `agents/fernando/workflows/create-component/` |
| `workflows/bi-business-innovation/` | `agents/paul/workflows/business-innovation/` |
| `workflows/pre-product-discovery/` | `workflows/product-discovery/` |
| `workflows/design-token-extraction/` | `workflows/design-extraction/` |
| `workflows/problem-structuring/` | `agents/domcobb/workflows/problem-structuring/` |
| `workflows/ps-lite/` | `agents/domcobb/workflows/problem-structuring-lite/` |
| `workflows/prompting-assistance/` | `agents/domcobb/workflows/prompting-assistance/` |
| `workflows/ai-web-project/` | `agents/domcobb/workflows/ai-web-project/` |
| `workflows/compound-learning/` | `agents/ana/workflows/compound-learning/` |
| `workflows/context-handoff/` | `agents/ana/workflows/context-handoff/` |
| `workflows/add-prompting-knowledge/` | `agents/ana/workflows/add-prompting-knowledge/` |

- [ ] **Step 3: Fix agent path references**

```bash
grep -rn "agents/ana\.md\|agents/domcobb\.md\|agents/fernando\.md\|agents/george-orwell\.md\|agents/paul\.md\|agents/leo\.md\|agents/roelof\.md\|agents/vivian\.md" "H:/BMAD/rbtv"
```

For each `agents/<name>.md` result, update to `agents/<name>/<name>.md`.

- [ ] **Step 4: Fix task path references (for moved tasks)**

```bash
grep -rn "tasks/critical-essay-review\.xml\|tasks/mentor-help\.xml" "H:/BMAD/rbtv"
```

For each:

| Old | New |
|---|---|
| `tasks/critical-essay-review.xml` | `agents/george-orwell/tasks/critical-essay-review.xml` |
| `tasks/mentor-help.xml` | `agents/paul/tasks/mentor-help.xml` |

- [ ] **Step 5: Verify zero legacy references remain**

```bash
grep -rn "bmad-rbtv-\|workflows/plan-lifecycle\|workflows/essay\|workflows/build-rbtv-component\|workflows/bi-business-innovation\|workflows/pre-product-discovery\|workflows/design-token-extraction\|workflows/problem-structuring[^-]\|workflows/ps-lite\|workflows/prompting-assistance\|workflows/ai-web-project\|workflows/compound-learning\|workflows/context-handoff\|workflows/add-prompting-knowledge" "H:/BMAD/rbtv"
```

Expected: zero matches. If any remain, fix.

- [ ] **Step 6: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor: fix internal path references after rename and nesting"
```

---

## Phase 4: Strip BMAD External Dependencies

**Goal:** Remove all references to `bmad_core`, `bmad_bmm`, `bmad_cis`, and related frontmatter. Replace BMAD menu items with plugin invocations where appropriate.

### Task 14: Inventory BMAD external references

**Files:** all files under `rbtv/` (agents/, workflows/, tasks/, skills/).

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-4-start
```

- [ ] **Step 2: Search for BMAD module references**

```bash
grep -rn "bmad_core\|bmad_bmm\|bmad_cis\|core\|bmm\|cis" "H:/BMAD/rbtv"
```

Record each match: file path, line number, reference type (menu item, frontmatter, workflow step, etc.).

- [ ] **Step 3: Search for BMAD output path references**

```bash
grep -rn "bmad_output" "H:/BMAD/rbtv"
```

Record these — they will be DELETED (not replaced) in Task 18 Step 2. Per D7, no placeholder substitutes `{bmad_output}`; output resolution is runtime via the `rbtv-output-resolution` rule.

- [ ] **Step 4: Search for project-root-style references**

```bash
grep -rn "{project-root}/rbtv" "H:/BMAD/rbtv"
```

Record these — they will be replaced with `{rbtv_path}` in Task 18.

No commit at the end of this task — this is inventory only.

---

### Task 15: Remove Advanced Elicitation and Party Mode menu items

**Files:** all step and agent files across `rbtv/` that have AE or PM menu rows.

- [ ] **Step 1: Find all AE menu rows**

```bash
grep -rn "\[AE\]\|Advanced Elicitation" "H:/BMAD/rbtv"
```

- [ ] **Step 2: For each match, delete the entire row or list item**

Example before:

```markdown
| [AE] | Advanced Elicitation | Load `{bmad_core}/workflows/advanced-elicitation/workflow.xml` |
| [DC] | DomCobb handler | ... |
```

Example after:

```markdown
| [DC] | DomCobb handler | ... |
```

Delete only the AE row, not the whole table. Preserve table headers and other rows.

- [ ] **Step 3: Find all PM menu rows**

```bash
grep -rn "\[PM\]\|\[P\] Party\|Party Mode" "H:/BMAD/rbtv"
```

- [ ] **Step 4: For each match, delete the entire row or list item**

- [ ] **Step 5: Verify zero AE or PM references remain**

```bash
grep -rn "Advanced Elicitation\|Party Mode" "H:/BMAD/rbtv"
```

Expected: zero matches.

- [ ] **Step 6: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor: remove Advanced Elicitation and Party Mode menu items (BMAD dependencies)"
```

---

### Task 16: Replace BMM references in Ana's menu with plugin invocations

**Files:** `agents/ana/ana.md` (and any nested menu step files).

- [ ] **Step 1: Read Ana's agent file**

```bash
cat "H:/BMAD/agents/ana/ana.md"
```

Identify menu items referencing `{bmad_bmm}` or BMM workflows — typically `[B] Brief`, `[PRD]`, `[UX]` in a Product submenu.

- [ ] **Step 2: Replace each BMM menu item**

For each BMM menu row, replace with a plugin invocation instruction. Example before:

```markdown
| [B] | Brief | Load `{bmad_bmm}/workflows/product-brief/workflow.xml` |
| [PRD] | PRD | Load `{bmad_bmm}/workflows/create-prd/workflow.xml` |
| [UX] | UX Design | Load `{bmad_bmm}/workflows/create-ux-design/workflow.xml` |
```

Example after:

```markdown
| [B] | Brief | Invoke the `bmad-method-lifecycle:bmad-product-brief` skill |
| [PRD] | PRD | Invoke the `bmad-method-lifecycle:bmad-create-prd` skill |
| [UX] | UX Design | Invoke the `bmad-method-lifecycle:bmad-create-ux-design` skill |
```

- [ ] **Step 3: Remove any `{bmad_bmm}` references in Ana's body**

```bash
grep -n "bmad_bmm\|bmm" "H:/BMAD/agents/ana/ana.md"
```

Expected: zero matches after Step 2. Fix any remaining.

- [ ] **Step 4: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/ana): replace BMM references with plugin invocations"
```

---

### Task 17: Replace CIS reference in DomCobb's menu

**Files:** `agents/domcobb/domcobb.md`.

- [ ] **Step 1: Find the CIS reference**

```bash
grep -n "bmad_cis\|cis" "H:/BMAD/agents/domcobb/domcobb.md"
```

Typical location: `[PV] Problem Solving` menu item.

- [ ] **Step 2: Replace with plugin invocation**

Example before:

```markdown
| [PV] | Problem Solving | Load `{project-root}/cis/workflows/problem-solving/workflow.yaml` |
```

Example after:

```markdown
| [PV] | Problem Solving | Invoke the `bmad-pro-skills:bmad-problem-solving` skill |
```

- [ ] **Step 3: Verify zero CIS references remain**

```bash
grep -rn "bmad_cis\|cis" "H:/BMAD/rbtv"
```

Expected: zero matches.

- [ ] **Step 4: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor(agents/domcobb): replace CIS reference with plugin invocation"
```

---

### Task 18: Replace path variables with placeholders

**Files:** all agent, workflow, and step files.

This is the bulk substitution that makes RBTV's source files parameterized for install-time baking.

- [ ] **Step 1: Replace project-root RBTV paths**

Find-and-replace across all files in `rbtv/`:

| Find | Replace |
|---|---|
| `{project-root}/workflows/` | `{rbtv_path}/workflows/` |
| `{project-root}/agents/` | `{rbtv_path}/agents/` |
| `{project-root}/tasks/` | `{rbtv_path}/tasks/` |
| `{project-root}/` | `{rbtv_path}/` |
| `{bmad_rbtv}/workflows/` | `{rbtv_path}/workflows/` |
| `{bmad_rbtv}/agents/` | `{rbtv_path}/agents/` |
| `{bmad_rbtv}/tasks/` | `{rbtv_path}/tasks/` |
| `{bmad_rbtv}/` | `{rbtv_path}/` |

Use your editor's "Find in Files" feature or sed (verify paths before running sed to avoid unintended replacements in docs).

- [ ] **Step 2: Delete BMAD output-path variable references**

| Find | Action |
|---|---|
| `{bmad_output}` | DELETE. Per D7 (rewritten 2026-04-17), no placeholder replaces it — output paths are resolved at runtime by the `rbtv-output-resolution` rule reading CLAUDE.md routing. |

For each occurrence of `{bmad_output}` in RBTV source, rewrite the surrounding context so the workflow no longer claims to know its output path from a baked value. Typical fixes: replace "Output to `{bmad_output}/something`" with "Output location resolved per the `rbtv-output-resolution` rule" OR drop the sentence entirely if destination selection is handled elsewhere in the workflow.

- [ ] **Step 3: Remove BMAD core-specific frontmatter fields**

For each workflow and step file, delete lines matching these frontmatter fields:

- `main_config:`
- `advancedElicitationTask:`
- `partyModeWorkflow:`
- `parentWorkflow:`
- `validateWorkflow:`

```bash
grep -rln "^main_config:\|^advancedElicitationTask:\|^partyModeWorkflow:\|^parentWorkflow:\|^validateWorkflow:" "H:/BMAD/rbtv"
```

For each file listed, edit and remove the matching line. Preserve valid YAML structure — if the last frontmatter field is removed, ensure `---` delimiters are preserved.

- [ ] **Step 4: Remove config-loading instructions from workflow entry points**

Each top-level workflow.md has an initialization section like:

```markdown
## Initialization

1. Load module config: `{project-root}/_config/config.yaml`
2. Load core config: `{project-root}/core/config.yaml`
3. Store variables: ...
```

Replace with:

```markdown
## Initialization

1. If `_system/user/profile/preferences.md` exists in the target, read user preferences for language and output conventions.
2. Determine output destination from the workflow's `outputFile` / `outputFolder` frontmatter. If it contains the literal string `ASK-CLAUDE-MD`, read the target's `CLAUDE.md` for content-routing rules to determine the correct output folder based on current project context.
```

- [ ] **Step 5: Remove remaining BMAD core and BMM references**

```bash
grep -rn "bmad_core\|bmad_bmm\|core\|bmm" "H:/BMAD/rbtv"
```

For each match, either delete the line entirely or replace it with a plugin invocation (same pattern as Tasks 16-17).

- [ ] **Step 6: Verify cleanup**

```bash
grep -rn "bmad_core\|bmad_bmm\|bmad_cis\|bmad_rbtv\|bmad_output\|{project-root}/_bmad\|main_config:\|advancedElicitationTask:\|partyModeWorkflow:" "H:/BMAD/rbtv"
```

Expected: zero matches.

- [ ] **Step 7: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "refactor: replace path variables with standalone placeholders, remove BMAD config loading"
```

---

### Task 18a: Transform meeting-summarizer into BMAD architecture (workflow + thin-loader)

**Context:** The existing `_config/claude/skills/bmad-rbtv-meeting-summarizer/SKILL.md` is self-contained — its body has the entire 6-step summarization procedure. `workflows/meeting-summarizer/` currently has only `universal-prompt.md`. To align with the rest of RBTV (where skills are thin loaders that reference workflows), extract the procedure into `workflow.md` and rewrite it to remove BMAD-specific assumptions (`{project-root}/projects/{project}/meetings/`).

**Files:**
- Read: `skills/meeting-summarizer/SKILL.md` (has the current 6-step body)
- Create: `workflows/meeting-summarizer/workflow.md` (extracted + rewritten)
- Modify: `skills/meeting-summarizer/SKILL.md` (thin-loader rewrite happens in Task 25 Step 6)

- [ ] **Step 1: Read the current SKILL.md to capture the 6-step procedure**

```bash
cat "H:/BMAD/skills/meeting-summarizer/SKILL.md"
```

Record the 6 steps (Read Transcript, Detect Project, Classify & Confirm, Fix Filename & Location, Summarize, Confirm) — this becomes the new workflow body.

- [ ] **Step 2: Create `workflows/meeting-summarizer/workflow.md`**

Write the new workflow with these contents. The key difference from the old SKILL.md body: project-detection logic is removed (no BMAD `projects/{project}/` assumption); instead, the workflow asks the user or reads CLAUDE.md routing.

```markdown
---
name: meeting-summarizer
description: Summarize a meeting transcript, fix filename + location, and output a structured summary
---

# Meeting Summarizer Workflow

**CRITICAL — Execute these steps in order. Do not respond conversationally until Step 6 completes.**

## Step 1 — Read Transcript

Read the referenced transcript file completely. If no transcript was provided, STOP and ask the user for the transcript path.

## Step 2 — Determine context

Determine the meeting's context (participants, topic, project). Look at:

1. **The transcript's path** — if the file lives in a project-specific folder (e.g., `<some_path>/meetings/<type>/`), use that as the project context.
2. **The transcript content** — participants, company names, topics.
3. **CLAUDE.md routing** — if the workspace has a CLAUDE.md with content-routing rules, read it to determine which area/project the meeting belongs to.
4. **Ask the user** — if ambiguous, ask directly. Do NOT assume.

Once project context is determined, look for local memory files (e.g., `memory-<project>.md`, a project index, or an area CLAUDE.md) and read them for participant names and conventions.

## Step 3 — Classify and confirm

Analyze the transcript content to classify the meeting type. Typical categories: client, investor, internal, discovery, therapy, other.

If the project's folder has a `meetings/` subdirectory with type-named sub-folders, use those as the type vocabulary. Otherwise use the generic categories above.

Present to user:

> **Project context:** {what you determined}
> **Meeting type detected:** {type}
> **Confidence:** {high/medium/low}
> **Key cues:** {2-3 signals that led to this classification}
>
> Correct? (or specify the right type)

HALT. Wait for user confirmation.

## Step 4 — Fix filename and location

After user confirms, determine the correct filename and output folder.

**Naming convention:** `YYYY-MM-DD-{slug}.{ext}`
- `{ext}` — preserve original extension
- `{slug}` — kebab-case, content-derived (who was in it, what was it about)
  - Pattern: `{participants}-{topic}` — e.g., `yuri-kenu-budget-review`
  - Bad slugs (too generic): `weekly`, `team-sync`, `meeting-notes`
  - Good slugs: `yuri-kenu-runway-planning`, `machado-corporate-restructuring`
- Extract the meeting date from the transcript CONTENT (not file creation date). If ambiguous, ask.

**Determine output folder:**
Follow the `rbtv-output-resolution` rule (installed as `.claude/rules/rbtv-output-resolution.md`). In short: read the workspace CLAUDE.md's `## Component Output Routing` block, match output type `meeting-summary`, descend into sub-project CLAUDE.mds if needed, infer the `{project}` variable from conversation context (which client / which meeting this is), and propose the full path to the user before writing. If no routing exists yet, inform the user that `/rbtv-output-routing` has not been run and ask once for this meeting's folder.

If the file needs renaming or moving, present the proposed change:

> **Current:** `{current_path}/{current_filename}`
> **Proposed:** `{output_folder}/YYYY-MM-DD-{slug}.{ext}`
>
> Proceed? (y/n)

HALT. Wait for user confirmation.

**Execute file ops:**
- If inside a git repo, use `git mv` to preserve history.
- If outside, copy to the correct location and leave the original (inform the user).

## Step 5 — Summarize

1. Look for a type-specific prompt at `{output_folder}/_summary-prompt.md` (if the meeting's folder has a nested `_summary-prompt.md`, use it).
2. If none, use the universal fallback at `{rbtv_path}/workflows/meeting-summarizer/universal-prompt.md`.
3. Process the transcript following every instruction in the chosen prompt — all analytical layers, the anti-bias protocol, and every section the prompt defines.
4. Save the output as `{output_folder}/YYYY-MM-DD-{slug}-summary.md`.

## Step 6 — Confirm

Report to user:
- Transcript final location (after any rename/move)
- Summary location
- Any ambiguity flags from the summary that need human review
```

- [ ] **Step 3: Verify `workflows/meeting-summarizer/universal-prompt.md` still exists**

```bash
ls "H:/BMAD/workflows/meeting-summarizer/"
```

Expected: `universal-prompt.md`, `workflow.md`. The universal prompt is legacy content — verify it doesn't contain BMAD-specific path references that break standalone:

```bash
grep -n "bmad\|project-root\|_bmad" "H:/BMAD/workflows/meeting-summarizer/universal-prompt.md"
```

If any match appears, edit the file to use generic language or `{rbtv_path}`.

- [ ] **Step 4: The SKILL.md rewrite happens in Task 25 Step 6 (unchanged)**

The template written in Task 25 Step 6 now correctly points to `{rbtv_path}/workflows/meeting-summarizer/workflow.md` — which now actually exists.

- [ ] **Step 5: Commit**

```bash
git -C "H:/BMAD/rbtv" add workflows/meeting-summarizer/workflow.md
git -C "H:/BMAD/rbtv" commit -m "feat(workflows): transform meeting-summarizer into BMAD architecture (workflow + thin-loader skill)"
```

---

## Phase 5: Drop Unused Components

**Goal:** Delete the skills, rules, and tasks marked as drops in the decisions log. No other changes in this phase — isolate deletions so they're easy to revert.

### Task 19: Drop unused skills

**Files:** entire directories under `skills/`.

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-5-start
```

- [ ] **Step 2: Delete dropped skill directories**

```bash
git -C "H:/BMAD/rbtv" rm -r skills/help
git -C "H:/BMAD/rbtv" rm -r skills/quality-review
git -C "H:/BMAD/rbtv" rm -r skills/reorganize-memory
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" commit -m "feat: drop skills help, quality-review, reorganize-memory (low usage or Claude Code native)"
```

---

### Task 20: Drop memory-system rule

**Files:** `rules/memory-system.md`.

- [ ] **Step 1: Delete**

```bash
git -C "H:/BMAD/rbtv" rm rules/memory-system.md
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" commit -m "feat: drop memory-system rule (replaced by Claude Code auto-memory)"
```

---

### Task 21: Drop BMAD-only and obsolete task XML files

**Files:**
- Delete: `tasks/help.xml`
- Delete: `tasks/quality-review.xml`
- Delete: `tasks/context-distill.xml`
- Delete: `tasks/check-bmad-compat.xml`
- Delete: `tasks/restore-bmad-config.xml`
- Delete: `tasks/update-bmad-config.xml`

Note: `tasks/mentor-help.xml` and `tasks/critical-essay-review.xml` were MOVED in Tasks 8 and 9 (not dropped). `tasks/tone-extraction.xml` and `tasks/web-research.xml` are kept at root.

- [ ] **Step 1: Delete dropped task files**

```bash
git -C "H:/BMAD/rbtv" rm tasks/help.xml
git -C "H:/BMAD/rbtv" rm tasks/quality-review.xml
git -C "H:/BMAD/rbtv" rm tasks/context-distill.xml
git -C "H:/BMAD/rbtv" rm tasks/check-bmad-compat.xml
git -C "H:/BMAD/rbtv" rm tasks/restore-bmad-config.xml
git -C "H:/BMAD/rbtv" rm tasks/update-bmad-config.xml
```

- [ ] **Step 2: Verify remaining task files**

```bash
ls "H:/BMAD/tasks"
```

Expected: `tone-extraction.xml`, `web-research.xml`.

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" commit -m "feat: drop BMAD-only and obsolete task XML files"
```

---

### Task 22: Delete emptied admin/claude directory

**Files:** `admin/claude/` (and any subdirs).

- [ ] **Step 1: Verify admin/claude is empty of meaningful content**

```bash
find "H:/BMAD/admin/claude" -type f
```

Expected output: empty (Task 3 moved source-of-truth.md; Task 7 moved component-patterns.md). If any files remain, inspect — they may be unconsumed legacy content that should be moved or explicitly dropped.

- [ ] **Step 2: Delete**

```bash
git -C "H:/BMAD/rbtv" rm -r admin/claude 2>/dev/null || rmdir "H:/BMAD/admin/claude"
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add -A
git -C "H:/BMAD/rbtv" commit -m "chore: remove now-empty admin/claude directory"
```

---

## Phase 6: Build Install Infrastructure

**Goal:** Rewrite `defaults.yaml`, create `module-manifest.yaml`, rebuild the `install.py` + `installer/` package for standalone operation with thin-loader generation.

### Task 23: Rewrite defaults.yaml

**Files:** `admin/install/defaults.yaml`.

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-6-start
```

- [ ] **Step 2: Replace defaults.yaml content**

Overwrite `admin/install/defaults.yaml` with:

```yaml
# RBTV Install Defaults
# Read by install.py at install time. Baked values are written to rbtv.yaml in the target.

rbtv:
  version: "7.0.0"  # Bumped for standalone release
  name: "rbtv"

# NOTE (D7, 2026-04-17): output paths are NOT configured here or in rbtv.yaml.
# They are resolved at runtime by components following the `rbtv-output-resolution` rule,
# which reads `## Component Output Routing` blocks from workspace CLAUDE.md files.
# Users configure routing post-install via `/rbtv-output-routing`.

# Modules available. Core is always installed.
modules:
  available:
    - core
    - innovation
    - work-productivity
    - writing
  always_installed:
    - core

# Language default
defaults:
  language: "en"
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/defaults.yaml
git -C "H:/BMAD/rbtv" commit -m "feat(install): rewrite defaults.yaml for standalone operation"
```

---

### Task 24: Create module-manifest.yaml

**Files:** `admin/install/module-manifest.yaml`.

- [ ] **Step 1: Write the manifest**

Create `admin/install/module-manifest.yaml` with the complete module mapping. Format: each module lists the thin-loader-generation entries (skills, commands) and rule-copy entries. Rules and loaders install to `.claude/<type>/rbtv-<name>`. Agents, workflows, tasks are NOT installed (referenced by path from loaders).

```yaml
# Module Manifest — source of truth for what install.py creates in the target.
# Install generates thin loaders under .claude/skills/, .claude/commands/, and
# copies rule content under .claude/rules/. Agents, workflows, and tasks stay
# in the RBTV repo source and are referenced by path from loaders.

core:
  always_installed: true
  description: "Core productivity utilities, always installed."
  skills:
    - source_template: skills/planning/SKILL.md
      target: .claude/skills/rbtv-planning/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/web-research/SKILL.md
      target: .claude/skills/rbtv-web-research/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/create-component/SKILL.md
      target: .claude/skills/rbtv-create-component/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/doc/SKILL.md
      target: .claude/skills/rbtv-doc/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/domcobb/SKILL.md
      target: .claude/skills/rbtv-domcobb/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/meeting-summarizer/SKILL.md
      target: .claude/skills/rbtv-meeting-summarizer/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/output-routing/SKILL.md
      target: .claude/skills/rbtv-output-routing/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/playwright-cli/SKILL.md
      target: .claude/skills/rbtv-playwright-cli/SKILL.md
      bake: [rbtv_path]
  commands:
    - source_template: commands/planning.md
      target: .claude/commands/rbtv-planning.md
      bake: [rbtv_path]
    - source_template: commands/web-research.md
      target: .claude/commands/rbtv-web-research.md
      bake: [rbtv_path]
    - source_template: commands/create-component.md
      target: .claude/commands/rbtv-create-component.md
      bake: [rbtv_path]
    - source_template: commands/doc.md
      target: .claude/commands/rbtv-doc.md
      bake: [rbtv_path]
    - source_template: commands/domcobb.md
      target: .claude/commands/rbtv-domcobb.md
      bake: [rbtv_path]
    - source_template: commands/meeting-summarizer.md
      target: .claude/commands/rbtv-meeting-summarizer.md
      bake: [rbtv_path]
    - source_template: commands/output-routing.md
      target: .claude/commands/rbtv-output-routing.md
      bake: [rbtv_path]
  rules:
    - source: rules/atomic-files.md
      target: .claude/rules/rbtv-atomic-files.md
      mode: copy
    - source: rules/audio-aware.md
      target: .claude/rules/rbtv-audio-aware.md
      mode: copy
    - source: rules/background-agents.md
      target: .claude/rules/rbtv-background-agents.md
      mode: copy
    - source: rules/bash-patterns.md
      target: .claude/rules/rbtv-bash-patterns.md
      mode: copy
    - source: rules/chat-discipline.md
      target: .claude/rules/rbtv-chat-discipline.md
      mode: copy
    - source: rules/context-preservation.md
      target: .claude/rules/rbtv-context-preservation.md
      mode: copy
    - source: rules/git-file-ops.md
      target: .claude/rules/rbtv-git-file-ops.md
      mode: copy
    - source: rules/output-resolution.md
      target: .claude/rules/rbtv-output-resolution.md
      mode: copy
    - source: rules/reasoning.md
      target: .claude/rules/rbtv-reasoning.md
      mode: copy
    - source: rules/source-of-truth.md
      target: .claude/rules/rbtv-source-of-truth.md
      mode: copy
  subagents:
    - source: subagents/designer.md
      target: .claude/agents/rbtv-designer.md
      mode: copy
    - source: subagents/web-research.md
      target: .claude/agents/rbtv-web-research.md
      mode: copy

innovation:
  description: "Business innovation frameworks, mentorship, and product discovery."
  skills:
    - source_template: skills/mentor/SKILL.md
      target: .claude/skills/rbtv-mentor/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/product-discovery/SKILL.md
      target: .claude/skills/rbtv-product-discovery/SKILL.md
      bake: [rbtv_path]
  commands:
    - source_template: commands/mentor.md
      target: .claude/commands/rbtv-mentor.md
      bake: [rbtv_path]
    - source_template: commands/product-discovery.md
      target: .claude/commands/rbtv-product-discovery.md
      bake: [rbtv_path]

work-productivity:
  description: "Pitch generation, design extraction, client engagement."
  skills:
    - source_template: skills/client-pitch/SKILL.md
      target: .claude/skills/rbtv-client-pitch/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/investor-pitch/SKILL.md
      target: .claude/skills/rbtv-investor-pitch/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/designer/SKILL.md
      target: .claude/skills/rbtv-designer/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/design-extraction/SKILL.md
      target: .claude/skills/rbtv-design-extraction/SKILL.md
      bake: [rbtv_path]
  commands:
    - source_template: commands/client-pitch.md
      target: .claude/commands/rbtv-client-pitch.md
      bake: [rbtv_path]
    - source_template: commands/investor-pitch.md
      target: .claude/commands/rbtv-investor-pitch.md
      bake: [rbtv_path]
    - source_template: commands/designer.md
      target: .claude/commands/rbtv-designer.md
      bake: [rbtv_path]
    - source_template: commands/design-extraction.md
      target: .claude/commands/rbtv-design-extraction.md
      bake: [rbtv_path]

writing:
  description: "Long-form writing and tone analysis."
  skills:
    - source_template: skills/writing/SKILL.md
      target: .claude/skills/rbtv-writing/SKILL.md
      bake: [rbtv_path]
    - source_template: skills/tone-extraction/SKILL.md
      target: .claude/skills/rbtv-tone-extraction/SKILL.md
      bake: [rbtv_path]
  commands:
    - source_template: commands/writing.md
      target: .claude/commands/rbtv-writing.md
      bake: [rbtv_path]
    - source_template: commands/tone-extraction.md
      target: .claude/commands/rbtv-tone-extraction.md
      bake: [rbtv_path]

# Cross-module agent note — documentation only. Vivian agent file lives in rbtv/agents/vivian/
# and is referenced by path from both work-productivity skills (designer) and innovation workflows
# (paul's business-innovation/bi-m3-brandbook). No copy; loaders reference by absolute path.
cross_module_agents:
  vivian:
    primary_module: work-productivity
    also_used_by: [innovation]
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/module-manifest.yaml
git -C "H:/BMAD/rbtv" commit -m "feat(install): create module-manifest.yaml"
```

---

### Task 25: Write skill source templates

**Files:** each `skills/<name>/SKILL.md` in RBTV source must be a template that the installer can bake into a thin loader for the target.

Templates use `{rbtv_path}` as the only placeholder. The installer substitutes it with a vault-relative path at install time, producing the installed `.claude/skills/rbtv-<name>/SKILL.md`. Per D7 (rewritten 2026-04-17), output location is NOT baked — it is resolved at runtime by the `rbtv-output-resolution` rule (see Task 26A). Templates have no `{output_path_*}` placeholders.

**STYLE REQUIREMENT — applies to EVERY template in this task:** Each template's body MUST begin its numbered instruction list with the line:

```
**CRITICAL — Execute these steps in order. Load persona/workflow files FULLY before acting.**
```

This line goes after the `# <Title>` heading and before the `1.` step. Research into Claude Code skill behavior (https://code.claude.com/docs/en/skills.md) confirms the SKILL.md body is reliably loaded into context, but strong imperative voice materially improves compliance — it prevents Claude from responding conversationally without first loading the referenced persona/workflow. Current (pre-standalone) RBTV skills use the same imperative style; we match it.

**PATH REQUIREMENT:** `{rbtv_path}` resolves to a vault-relative path (e.g., `3. Resources/rbtv`) after install-time baking, NOT an absolute path. Loaders are portable across vault relocations. See Decision D19.

- [ ] **Step 1: Write template for `skills/planning/SKILL.md`**

```markdown
---
name: rbtv-planning
description: "Structured plan creation with quality gates. Use when a plan document needs to be produced for a multi-step task."
---

# Planning

**CRITICAL — Execute these steps in order. Load persona/workflow files FULLY before acting.**

1. Read and execute the planning workflow at `{rbtv_path}/workflows/planning/workflow.md`.
```

**This template is the canonical style for every other template in this task. Each subsequent step below shows only the content-unique portion; when you write the file, prepend the same `**CRITICAL — Execute these steps in order...**` line between the heading and the numbered list.**

(Per D7: templates do NOT specify an output location. At runtime, components invoke the `rbtv-output-resolution` rule — which reads workspace CLAUDE.md routing, proposes a path, and confirms with the user before writing. The rule is installed as `.claude/rules/rbtv-output-resolution.md` and is always loaded in-context.)

- [ ] **Step 2: Write template for `skills/web-research/SKILL.md`**

```markdown
---
name: rbtv-web-research
description: "Conduct structured web research with source evaluation. Use when the user asks to research a topic or gather web sources."
---

# Web Research

1. Load the task specification from `{rbtv_path}/tasks/web-research.xml`.
2. Execute the task's flow.
```

- [ ] **Step 3: Write template for `skills/create-component/SKILL.md`**

```markdown
---
name: rbtv-create-component
description: "Create a new RBTV component (agent, skill, workflow, rule, task). Use when adding to or extending the RBTV system."
---

# Create Component

1. Load persona from `{rbtv_path}/agents/fernando/fernando.md`.
2. Execute the workflow at `{rbtv_path}/agents/fernando/workflows/create-component/workflow.md`.
3. **Fernando's scope:**
   - If the user is modifying an existing RBTV component, write the changes to the RBTV source repo at `{rbtv_path}`.
   - If the user is creating a new component, ASK: "Should this be an RBTV component (bootstrapped to all instances via re-install), or a local component (only in this instance)?"
     - RBTV: write to `{rbtv_path}/<type>/<name>/`. User must re-run `install.py` to generate the loader.
     - Local: write directly to `.claude/<type>/<name>/` in the instance (no `rbtv-` prefix). Not touched by re-install.
```

- [ ] **Step 4: Write template for `skills/doc/SKILL.md`**

```markdown
---
name: rbtv-doc
description: "Documentation generation — compound learning or context handoff. Use when the user asks for documentation output or knowledge capture."
---

# Documentation

1. Load persona from `{rbtv_path}/agents/ana/ana.md`.
2. Follow Ana's menu handlers — options include compound learning, context handoff, and prompting knowledge curation.
```

- [ ] **Step 5: Write template for `skills/domcobb/SKILL.md`**

```markdown
---
name: rbtv-domcobb
description: "Problem structuring, prompting assistance, and AI project mentorship. Use when the user needs to decompose a problem or plan an AI project."
---

# DomCobb

1. Load persona from `{rbtv_path}/agents/domcobb/domcobb.md`.
2. Follow DomCobb's menu handlers — options include problem structuring (full or lite), prompting assistance, and AI web project mentorship.
```

- [ ] **Step 6: Write template for `skills/meeting-summarizer/SKILL.md`**

```markdown
---
name: rbtv-meeting-summarizer
description: "Summarize a meeting transcript following RBTV's summarization standards. Use when the user provides a meeting transcript and asks for a summary."
---

# Meeting Summarizer

1. Read and execute the workflow at `{rbtv_path}/workflows/meeting-summarizer/workflow.md`.
```

- [ ] **Step 7: Handle `skills/playwright-cli/SKILL.md` + references/ subdirectory**

The playwright-cli skill has a `references/` subdirectory (9 files) with advanced-capability docs (tracing, video recording, storage-state, test generation, etc.). The SKILL.md body has RELATIVE links like `[Playwright Tests](references/playwright-tests.md)`. If the installer copies only SKILL.md, those links resolve to an empty `references/` in the target → 9 capabilities unreachable.

Rewrite the SKILL.md so its references-table links use `{rbtv_path}` absolute-after-baking paths:

| Before | After |
|---|---|
| `[references/playwright-tests.md](references/playwright-tests.md)` | `[playwright-tests.md]({rbtv_path}/skills/playwright-cli/references/playwright-tests.md)` |

Apply the same rewrite to every link in the SKILL.md that points into `references/`. Leave the description + frontmatter unchanged.

Also check for BMAD path references:

```bash
grep -n "bmad\|_bmad\|project-root" "H:/BMAD/skills/playwright-cli/SKILL.md"
```

Expected: zero matches. Fix if any found.

Note: the installer (Task 29) only copies SKILL.md, not the references subdirectory. The `{rbtv_path}/skills/playwright-cli/references/` links work because they point back into the RBTV source repo, not into the target's `.claude/` copy.

- [ ] **Step 8: Write template for `skills/mentor/SKILL.md`**

```markdown
---
name: rbtv-mentor
description: "Business mentorship via Paul — covers business innovation frameworks: competitive landscape, JTBD, lean canvas, TAM/SAM/SOM, brandbook, and more."
---

# Mentor

1. Load persona from `{rbtv_path}/agents/paul/paul.md`.
2. Follow Paul's menu handlers, which orchestrate the business-innovation workflow tree at `{rbtv_path}/agents/paul/workflows/business-innovation/`.
```

- [ ] **Step 9: Write template for `skills/product-discovery/SKILL.md`**

```markdown
---
name: rbtv-product-discovery
description: "Product discovery — structure benchmarks into a taxonomy and define V1 scope. Use when planning a new product's initial scope."
---

# Product Discovery

1. Read and execute the workflow at `{rbtv_path}/workflows/product-discovery/workflow.md`.
```

- [ ] **Step 10: Write template for `skills/client-pitch/SKILL.md`**

```markdown
---
name: rbtv-client-pitch
description: "Build a client-facing pitch deck via Leo's persona. Use when the user wants to produce a pitch deck for a specific client or prospect."
---

# Client Pitch

1. Load persona from `{rbtv_path}/agents/leo/leo.md`.
2. Execute the workflow at `{rbtv_path}/workflows/pitch/workflow.md` with `pitch_type: client`.
```

- [ ] **Step 11: Write template for `skills/investor-pitch/SKILL.md`**

```markdown
---
name: rbtv-investor-pitch
description: "Build an investor-facing pitch deck via Roelof's persona. Use when the user wants to produce a pitch deck for investors or fundraising."
---

# Investor Pitch

1. Load persona from `{rbtv_path}/agents/roelof/roelof.md`.
2. Execute the workflow at `{rbtv_path}/workflows/pitch/workflow.md` with `pitch_type: investor`.
```

- [ ] **Step 12: Write template for `skills/designer/SKILL.md`**

```markdown
---
name: rbtv-designer
description: "Visual design for pitch decks and brand identity via Vivian. Use when designing pitch deck visuals, brand visual identity, or AI image prompts."
---

# Designer

1. Load persona from `{rbtv_path}/agents/vivian/vivian.md`.
2. Process the user's request using Vivian's menu handlers.
3. Available capabilities:
   - Pitch deck design (HTML/CSS) via `{rbtv_path}/workflows/pitch/steps-c/step-07-generate.md`
   - AI image prompts via `{rbtv_path}/workflows/pitch/steps-c/step-08-images.md`
   - PDF export validation via `{rbtv_path}/workflows/pitch/steps-c/step-10-pdf-validation.md`
   - Brand visual identity via `{rbtv_path}/agents/paul/workflows/business-innovation/bi-m3/bi-m3-brandbook/steps-c/step-03-visual.md`
```

- [ ] **Step 13: Write template for `skills/design-extraction/SKILL.md`**

```markdown
---
name: rbtv-design-extraction
description: "Extract design tokens from website screenshots or URLs. Use when the user provides a reference site and asks for color/typography/spacing tokens."
---

# Design Extraction

1. Read and execute the workflow at `{rbtv_path}/workflows/design-extraction/workflow.md`.
```

- [ ] **Step 14: Write template for `skills/writing/SKILL.md`**

```markdown
---
name: rbtv-writing
description: "Long-form writing (essays, articles) via George Orwell's persona. Use when the user asks for an essay or structured long-form piece."
---

# Writing

1. Load persona from `{rbtv_path}/agents/george-orwell/george-orwell.md`.
2. Execute the workflow at `{rbtv_path}/agents/george-orwell/workflows/writing/workflow.md`.
```

- [ ] **Step 15: Write template for `skills/tone-extraction/SKILL.md`**

```markdown
---
name: rbtv-tone-extraction
description: "Extract a tone-of-voice profile from sample writing. Use when the user provides writing samples and wants a tone-extraction summary."
---

# Tone Extraction

1. Load the task specification from `{rbtv_path}/tasks/tone-extraction.xml`.
2. Execute the task's flow.
```

- [ ] **Step 16: Commit**

```bash
git -C "H:/BMAD/rbtv" add skills/
git -C "H:/BMAD/rbtv" commit -m "feat(skills): write standalone skill templates with path placeholders"
```

---

### Task 26: Write command source templates

**Files:** each `commands/<name>.md` (new file).

Commands are thin wrappers over skills. Each installs 1:1 with a skill (except playwright-cli, which is skill-only). On invocation via `/rbtv-<name>`, the command re-invokes the corresponding skill logic.

- [ ] **Step 1: Write `commands/planning.md`**

```markdown
Read and execute the planning workflow at `{rbtv_path}/workflows/planning/workflow.md`.
```

- [ ] **Step 2: Write `commands/web-research.md`**

```markdown
Load the task specification from `{rbtv_path}/tasks/web-research.xml` and execute its flow.
```

- [ ] **Step 3: Write `commands/create-component.md`**

```markdown
Load persona from `{rbtv_path}/agents/fernando/fernando.md` and execute the workflow at `{rbtv_path}/agents/fernando/workflows/create-component/workflow.md`. For new components, ask the user whether to publish to the RBTV source (re-install needed) or write locally to this instance.
```

- [ ] **Step 4: Write `commands/doc.md`**

```markdown
Load persona from `{rbtv_path}/agents/ana/ana.md` and follow the agent's menu handlers.
```

- [ ] **Step 5: Write `commands/domcobb.md`**

```markdown
Load persona from `{rbtv_path}/agents/domcobb/domcobb.md` and follow the agent's menu handlers.
```

- [ ] **Step 6: Write `commands/meeting-summarizer.md`**

```markdown
Read and execute the workflow at `{rbtv_path}/workflows/meeting-summarizer/workflow.md`.
```

- [ ] **Step 7: Write `commands/mentor.md`**

```markdown
Load persona from `{rbtv_path}/agents/paul/paul.md` and follow the agent's menu handlers for business-innovation workflows.
```

- [ ] **Step 8: Write `commands/product-discovery.md`**

```markdown
Read and execute the workflow at `{rbtv_path}/workflows/product-discovery/workflow.md`.
```

- [ ] **Step 9: Write `commands/client-pitch.md`**

```markdown
Load persona from `{rbtv_path}/agents/leo/leo.md` and execute the workflow at `{rbtv_path}/workflows/pitch/workflow.md` with pitch_type set to "client".
```

- [ ] **Step 10: Write `commands/investor-pitch.md`**

```markdown
Load persona from `{rbtv_path}/agents/roelof/roelof.md` and execute the workflow at `{rbtv_path}/workflows/pitch/workflow.md` with pitch_type set to "investor".
```

- [ ] **Step 11: Write `commands/designer.md`**

```markdown
Load persona from `{rbtv_path}/agents/vivian/vivian.md` and follow Vivian's menu handlers for pitch visuals, AI image prompts, PDF validation, or brand visual identity.
```

- [ ] **Step 12: Write `commands/design-extraction.md`**

```markdown
Read and execute the workflow at `{rbtv_path}/workflows/design-extraction/workflow.md`.
```

- [ ] **Step 13: Write `commands/writing.md`**

```markdown
Load persona from `{rbtv_path}/agents/george-orwell/george-orwell.md` and execute the workflow at `{rbtv_path}/agents/george-orwell/workflows/writing/workflow.md`.
```

- [ ] **Step 14: Write `commands/tone-extraction.md`**

```markdown
Load the task specification from `{rbtv_path}/tasks/tone-extraction.xml` and execute its flow.
```

- [ ] **Step 15: Commit**

```bash
git -C "H:/BMAD/rbtv" add commands/
git -C "H:/BMAD/rbtv" commit -m "feat(commands): write command source templates for all skills"
```

---

### Task 26A: Write output-routing system source files (rule + skill + command + workflow)

**Files (all NEW, per D7 rewrite 2026-04-17):**
- `rules/output-resolution.md` — smart-component behavior standard (installed as `rbtv-output-resolution` rule, copied into every target's `.claude/rules/`)
- `skills/output-routing/SKILL.md` — thin loader for the setup workflow
- `commands/output-routing.md` — `/rbtv-output-routing` entry point
- `workflows/output-routing/workflow.md` — interactive CLAUDE.md routing setup

**Why this task exists:** Per D7, RBTV components do not receive output paths baked at install time. Instead, components read a `## Component Output Routing` section from workspace CLAUDE.md files at runtime (governed by the `rbtv-output-resolution` rule), and the user populates those sections post-install via `/rbtv-output-routing`. This task creates the four new source files that implement both sides of that system.

- [ ] **Step 1: Write `rules/output-resolution.md`**

```markdown
---
name: rbtv-output-resolution
description: "Smart-component behavior standard — RBTV components must read workspace CLAUDE.md routing, propose an output path with reasoning, and confirm with the user before writing. Never blind-prompt for a path."
---

# Output Resolution

When an RBTV component (skill, command, workflow) produces an output file, resolve the destination by this procedure.

## Resolution steps

1. Read the workspace root CLAUDE.md. Look for a `## Component Output Routing` heading. Inside, read the routing table — specifically the content between the `<!-- component-routing-start -->` and `<!-- component-routing-end -->` HTML comment markers.
2. Match the component's output type (e.g. `pitch`, `planning`, `meeting-summary`, `writing`, `doc`, `create-component`, `product-discovery`, `business-innovation`, `design-extraction`, `tone-extraction`) to an entry in the routing table.
3. If the matched route points to a subdirectory that has its own CLAUDE.md with a `## Component Output Routing` block, read it for further refinement. Stop at a leaf path or at a path containing an unresolved variable (e.g. `{client}`, `{project}`, `{prospect}`).
4. Infer runtime variables from conversation context. Variables like `{client}` or `{project}` are resolved from what the user has already said in the current session. Do NOT ask about them blindly — only ask if the conversation truly does not specify.
5. Propose the full resolved path to the user with reasoning. Example: "I'll write this pitch to `tecer-biz/clients/SPSP/pitch-2026-04.md` because the routing says `pitch` → `clients/{client}/` and you mentioned SPSP."
6. Wait for confirmation or redirect. The user may approve, edit the path, or redirect entirely. Do not write until confirmed.

## Degraded modes

- If no `## Component Output Routing` block exists anywhere in the workspace hierarchy, inform the user that `/rbtv-output-routing` has not been run, then ask ONCE for this write's output path. Do not block the workflow.
- If routing is ambiguous (multiple candidate routes, or a variable the conversation does not resolve), ask a SPECIFIC question ("The routing sends pitches to either `clients/` or `prospects/`. Is this for a current client or a prospect?"). Never fall back to a generic "where should this go?" prompt.
- If the user redirects to a path outside the routing table, write where the user said, then note the divergence and suggest running `/rbtv-output-routing` so the routing catches this case next time.

## Routing block format

A `## Component Output Routing` section in a CLAUDE.md contains a markdown table with columns "Output type" and "Route". The table MUST be wrapped between `<!-- component-routing-start -->` and `<!-- component-routing-end -->` HTML comment markers so `/rbtv-output-routing` can edit the block idempotently without touching surrounding CLAUDE.md content. Output-type names must match the list in Resolution step 2 above.

## Scope

This rule governs output path resolution ONLY. It does not govern:
- What content to write (each component's own workflow owns that).
- Whether to write at all (component decides based on task completion).
- File-naming conventions within the resolved directory (component decides, or a more specific rule governs).
```

- [ ] **Step 2: Write `skills/output-routing/SKILL.md`**

```markdown
---
name: rbtv-output-routing
description: "Post-install setup — interactively write `## Component Output Routing` blocks into workspace CLAUDE.md files so the `rbtv-output-resolution` rule has routing to read at runtime. Use when setting up a new RBTV install or when routing needs to change."
---

# Output Routing Setup

**CRITICAL — Execute these steps in order. Load persona/workflow files FULLY before acting.**

1. Read and execute the workflow at `{rbtv_path}/workflows/output-routing/workflow.md`.
```

- [ ] **Step 3: Write `commands/output-routing.md`**

```markdown
Read and execute the output-routing setup workflow at `{rbtv_path}/workflows/output-routing/workflow.md`. This command is the post-install setup for RBTV output path configuration — it scans the workspace, reads existing CLAUDE.md files, and interactively proposes `## Component Output Routing` blocks for user confirmation.
```

- [ ] **Step 4: Write `workflows/output-routing/workflow.md`**

```markdown
---
name: output-routing
description: "Interactive workflow — scan workspace, read existing CLAUDE.md files, propose Component Output Routing blocks per level, confirm with user, write/edit."
---

# Output Routing Setup

Purpose: encode RBTV component output paths into the workspace's CLAUDE.md files so that the `rbtv-output-resolution` rule can resolve paths at runtime without prompting.

## Step 1 — Discover workspace structure

Ask the user, sequentially:

1. "Is this a single-project workspace (one repo/product) or a multi-project workspace (several projects under one root)?"
2. If multi-project: "Please list the top-level project directories you want routing for. I'll skip any you don't mention."
3. Read the installed `rbtv.yaml` to determine which RBTV modules (and therefore which output types) are active. Output types by module:
   - `core`: planning, doc, meeting-summary, create-component
   - `innovation`: business-innovation, product-discovery
   - `work-productivity`: pitch, design-extraction
   - `writing`: writing, tone-extraction

## Step 2 — Read existing CLAUDE.md files

Walk the identified projects plus workspace root:

- Read each `CLAUDE.md` that exists.
- For each, check whether a `## Component Output Routing` section is already present (between `<!-- component-routing-start -->` / `<!-- component-routing-end -->` markers). If present, read its current routing table.
- Record: file path, whether a block exists, existing entries if any.

## Step 3 — Propose routing per file

For each level (workspace root, then each project), present to the user:

- The file path.
- The CURRENT state (no block / block with entries X, Y).
- The PROPOSED block, with entries that fit this level. Rules of thumb:
  - Workspace root CLAUDE.md: handles output types that apply to the entire workspace, or DELEGATES to sub-projects (e.g. "pitch" → route into `tecer-biz/` so that tecer-biz's own CLAUDE.md can refine).
  - Sub-project CLAUDE.md: handles output types specific to that project, using project-relative paths.
  - Use placeholders like `{client}`, `{project}`, `{prospect}` for segments the user will specify at runtime. Do NOT try to enumerate specific clients or projects in the routing block — that is runtime data.

Present proposals as a diff. Ask the user to approve, edit, or skip per file.

## Step 4 — Write the routing blocks

For each approved proposal:

- If the CLAUDE.md does not contain a `## Component Output Routing` section, append one at the end of the file (after existing content). Wrap the table in the markers.
- If the section exists WITH markers, replace ONLY the content between `<!-- component-routing-start -->` and `<!-- component-routing-end -->`. Never touch content outside the markers.
- If the section exists WITHOUT markers, ASK the user whether to add markers (replacing the existing section content) or preserve it as-is (skip this file).

Confirm each write with the user before executing.

## Step 5 — Summary

Report:

- Which CLAUDE.md files were created or updated.
- Which output types now have routing.
- Which output types remain unrouted — these will trigger the degraded-mode behavior in `rbtv-output-resolution` (user prompted per-write). Suggest re-running this command when the right paths are known.
- If the workspace is a git repo, suggest committing the CLAUDE.md changes.
```

- [ ] **Step 5: Commit**

```bash
git -C "H:/BMAD/rbtv" add rules/output-resolution.md skills/output-routing commands/output-routing.md workflows/output-routing
git -C "H:/BMAD/rbtv" commit -m "feat(output-routing): add rule + skill + command + workflow for CLAUDE.md-based runtime output resolution"
```

---

### Task 27: Write installer package — manifest parser

**Files:** `admin/install/installer/manifest.py`.

- [ ] **Step 1: Write `admin/install/installer/manifest.py`**

```python
"""Module manifest parser for RBTV install."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SkillEntry:
    source_template: Path
    target_relative: Path
    bake_keys: tuple[str, ...]


@dataclass(frozen=True)
class CommandEntry:
    source_template: Path
    target_relative: Path
    bake_keys: tuple[str, ...]


@dataclass(frozen=True)
class RuleEntry:
    source: Path
    target_relative: Path
    mode: str  # "copy"


@dataclass(frozen=True)
class SubagentEntry:
    source: Path
    target_relative: Path
    mode: str  # "copy"


@dataclass(frozen=True)
class Module:
    name: str
    description: str
    always_installed: bool
    skills: tuple[SkillEntry, ...]
    commands: tuple[CommandEntry, ...]
    rules: tuple[RuleEntry, ...]
    subagents: tuple[SubagentEntry, ...]


def load_manifest(manifest_path: Path) -> dict[str, Module]:
    """Parse the manifest YAML and return a dict of {module_name: Module}."""
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    modules: dict[str, Module] = {}
    for name, data in raw.items():
        if name == "cross_module_agents":
            continue
        skills = tuple(
            SkillEntry(
                source_template=Path(s["source_template"]),
                target_relative=Path(s["target"]),
                bake_keys=tuple(s.get("bake", [])),
            )
            for s in data.get("skills", [])
        )
        commands = tuple(
            CommandEntry(
                source_template=Path(c["source_template"]),
                target_relative=Path(c["target"]),
                bake_keys=tuple(c.get("bake", [])),
            )
            for c in data.get("commands", [])
        )
        rules = tuple(
            RuleEntry(
                source=Path(r["source"]),
                target_relative=Path(r["target"]),
                mode=r.get("mode", "copy"),
            )
            for r in data.get("rules", [])
        )
        subagents = tuple(
            SubagentEntry(
                source=Path(s["source"]),
                target_relative=Path(s["target"]),
                mode=s.get("mode", "copy"),
            )
            for s in data.get("subagents", [])
        )
        modules[name] = Module(
            name=name,
            description=data.get("description", ""),
            always_installed=bool(data.get("always_installed", False)),
            skills=skills,
            commands=commands,
            rules=rules,
            subagents=subagents,
        )
    return modules
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/installer/manifest.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): manifest parser"
```

---

### Task 28: Write installer package — context resolver

**Files:** `admin/install/installer/context.py`.

- [ ] **Step 1: Write `admin/install/installer/context.py`**

```python
"""Path context for RBTV install."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class InstallContext:
    """Resolved paths and choices for a single install run.

    Per D7 (rewritten 2026-04-17): output paths are NOT part of install context.
    They are resolved at runtime by components following the rbtv-output-resolution
    rule, which reads `## Component Output Routing` blocks from workspace CLAUDE.md
    files. Install only needs to know rbtv/target paths and selected modules.
    """
    rbtv_root: Path          # Absolute path to the RBTV repo (source of truth)
    target_root: Path        # Absolute path to the workspace where loaders will be installed
    rbtv_relative: Path      # RBTV location expressed relative to target_root (e.g., "3. Resources/rbtv")
    modules_selected: tuple[str, ...]


def resolve_from_cli(
    target: Path,
    rbtv_path: Path,
    modules: tuple[str, ...],
) -> InstallContext:
    """Build the context from CLI arguments."""
    target_abs = target.resolve()
    rbtv_abs = rbtv_path.resolve()
    try:
        rbtv_rel = rbtv_abs.relative_to(target_abs)
    except ValueError as exc:
        raise ValueError(
            f"RBTV repo ({rbtv_abs}) must live inside the target workspace ({target_abs})."
        ) from exc
    return InstallContext(
        rbtv_root=rbtv_abs,
        target_root=target_abs,
        rbtv_relative=rbtv_rel,
        modules_selected=modules,
    )
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/installer/context.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): install context resolver"
```

---

### Task 29: Write installer package — loader generator

**Files:** `admin/install/installer/generator.py`.

- [ ] **Step 1: Write `admin/install/installer/generator.py`**

```python
"""Generate thin loaders and copy rules/subagents into the target."""
from __future__ import annotations

import shutil
from pathlib import Path

from .context import InstallContext
from .manifest import CommandEntry, Module, RuleEntry, SkillEntry, SubagentEntry


def _resolve_bake_value(key: str, ctx: InstallContext) -> str:
    """Resolve a template placeholder to a literal string.

    Per D7 (rewritten 2026-04-17): only `rbtv_path` is baked. Output paths
    are resolved at runtime by the rbtv-output-resolution rule reading
    `## Component Output Routing` blocks in CLAUDE.md files. Any template
    referencing an `output_path_*` placeholder is a bug — fail loudly.
    """
    if key == "rbtv_path":
        # Use the VAULT-RELATIVE path, not absolute. Claude's Read tool resolves
        # relative paths against cwd (the workspace root), so loaders remain valid
        # even if the workspace is later moved to a different filesystem location.
        return str(ctx.rbtv_relative).replace("\\", "/")
    raise KeyError(f"Unknown bake key: {key} (output_path_* keys were removed per D7)")


def _bake(template_text: str, keys: tuple[str, ...], ctx: InstallContext) -> str:
    baked = template_text
    for key in keys:
        placeholder = "{" + key + "}"
        baked = baked.replace(placeholder, _resolve_bake_value(key, ctx))
    return baked


def _write_file(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def install_skill(entry: SkillEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source_template
    target = ctx.target_root / entry.target_relative
    template_text = source.read_text(encoding="utf-8")
    baked = _bake(template_text, entry.bake_keys, ctx)
    _write_file(target, baked)
    return target


def install_command(entry: CommandEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source_template
    target = ctx.target_root / entry.target_relative
    template_text = source.read_text(encoding="utf-8")
    baked = _bake(template_text, entry.bake_keys, ctx)
    _write_file(target, baked)
    return target


def install_rule(entry: RuleEntry, module: Module, ctx: InstallContext) -> Path:
    source = ctx.rbtv_root / entry.source
    target = ctx.target_root / entry.target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def install_subagent(entry: SubagentEntry, module: Module, ctx: InstallContext) -> Path:
    """Copy subagent files as-is (self-contained content, no templating).
    Subagents are dispatched in a fresh context via the Task tool, so they
    cannot rely on the parent conversation having loaded anything else."""
    source = ctx.rbtv_root / entry.source
    target = ctx.target_root / entry.target_relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    return target


def clear_module_installed_files(target_root: Path) -> list[Path]:
    """Delete all rbtv-prefixed files/dirs under .claude/skills, .claude/commands,
    .claude/rules, and .claude/agents. Called before a re-install to guarantee
    a clean state. rbtv.yaml at the target root is NOT touched (preserved).
    Returns the list of paths removed (for logging)."""
    removed: list[Path] = []
    skills_dir = target_root / ".claude" / "skills"
    if skills_dir.is_dir():
        for child in skills_dir.iterdir():
            if child.is_dir() and child.name.startswith("rbtv-"):
                shutil.rmtree(child)
                removed.append(child)
    commands_dir = target_root / ".claude" / "commands"
    if commands_dir.is_dir():
        for child in commands_dir.iterdir():
            if child.is_file() and child.name.startswith("rbtv-") and child.suffix == ".md":
                child.unlink()
                removed.append(child)
    rules_dir = target_root / ".claude" / "rules"
    if rules_dir.is_dir():
        for child in rules_dir.iterdir():
            if child.is_file() and child.name.startswith("rbtv-") and child.suffix == ".md":
                child.unlink()
                removed.append(child)
    agents_dir = target_root / ".claude" / "agents"
    if agents_dir.is_dir():
        for child in agents_dir.iterdir():
            if child.is_file() and child.name.startswith("rbtv-") and child.suffix == ".md":
                child.unlink()
                removed.append(child)
    return removed
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/installer/generator.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): loader generator with overwrite-scoped cleanup"
```

---

### Task 30: Write installer package — state (rbtv.yaml) handler

**Files:** `admin/install/installer/state.py`.

- [ ] **Step 1: Write `admin/install/installer/state.py`**

```python
"""Read and write rbtv.yaml (user choices preserved across installs)."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

import yaml


STATE_FILENAME = "rbtv.yaml"


def state_path(target_root: Path) -> Path:
    return target_root / STATE_FILENAME


def read_state(target_root: Path) -> dict[str, Any] | None:
    path = state_path(target_root)
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_state(
    target_root: Path,
    *,
    rbtv_version: str,
    rbtv_relative: str,
    modules: tuple[str, ...],
) -> Path:
    """Write rbtv.yaml. Per D7, no output_paths section exists — output routing
    is resolved at runtime from CLAUDE.md `## Component Output Routing` blocks.
    """
    path = state_path(target_root)
    payload = {
        "rbtv_version": rbtv_version,
        "installed_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "rbtv_path": rbtv_relative,
        "modules": list(modules),
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/installer/state.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): rbtv.yaml state reader/writer"
```

---

### Task 31: Write installer package — CLI

**Files:** `admin/install/installer/cli.py`, `admin/install/installer/__init__.py`.

- [ ] **Step 1: Write `admin/install/installer/__init__.py`**

```python
"""RBTV installer package."""

from .cli import main

__all__ = ["main"]
```

- [ ] **Step 2: Write `admin/install/installer/cli.py`**

```python
"""CLI entry point for install.py."""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from .context import resolve_from_cli
from .generator import (
    clear_module_installed_files,
    install_command,
    install_rule,
    install_skill,
    install_subagent,
)
from .manifest import Module, load_manifest
from .state import read_state, write_state


def _find_rbtv_root() -> Path:
    """install.py lives at RBTV_ROOT/install.py. Return RBTV_ROOT."""
    return Path(__file__).resolve().parent.parent.parent.parent


def _load_defaults(rbtv_root: Path) -> dict[str, Any]:
    defaults_path = rbtv_root / "admin" / "install" / "defaults.yaml"
    return yaml.safe_load(defaults_path.read_text(encoding="utf-8"))


def _prompt_modules(available: list[str], always: list[str], existing: tuple[str, ...] | None) -> tuple[str, ...]:
    print("\nAvailable modules:")
    for m in available:
        marker = " (always installed)" if m in always else ""
        pre_selected = " [currently installed]" if existing and m in existing else ""
        print(f"  - {m}{marker}{pre_selected}")
    if existing is not None:
        print("\nPress Enter to keep current modules, or enter comma-separated module names to change.")
        raw = input("Modules: ").strip()
        if not raw:
            return existing
    else:
        raw = input("\nComma-separated modules to install (core is always included): ").strip()
    if not raw:
        return tuple(always)
    chosen = [m.strip() for m in raw.split(",") if m.strip()]
    for m in always:
        if m not in chosen:
            chosen.insert(0, m)
    for m in chosen:
        if m not in available:
            raise SystemExit(f"Unknown module: {m}")
    return tuple(chosen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Install RBTV into a target workspace.")
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help="Absolute path to the workspace where loaders will be installed.",
    )
    parser.add_argument(
        "--modules",
        type=str,
        default="",
        help="Comma-separated module names (skips interactive prompt if provided).",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip all prompts; use existing rbtv.yaml + --modules only.",
    )
    args = parser.parse_args(argv)

    rbtv_root = _find_rbtv_root()
    defaults = _load_defaults(rbtv_root)
    target_root = args.target.resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    existing_state = read_state(target_root)

    manifest = load_manifest(rbtv_root / "admin" / "install" / "module-manifest.yaml")
    always = [name for name, mod in manifest.items() if mod.always_installed]
    available = list(manifest.keys())

    if args.modules:
        chosen_modules = tuple(m.strip() for m in args.modules.split(",") if m.strip())
        for m in always:
            if m not in chosen_modules:
                chosen_modules = (m,) + chosen_modules
    elif args.non_interactive and existing_state:
        chosen_modules = tuple(existing_state.get("modules", always))
    else:
        existing_modules = tuple(existing_state["modules"]) if existing_state else None
        chosen_modules = _prompt_modules(available, always, existing_modules)

    # Per D7 (2026-04-17): no output_paths prompting or baking. Output routing
    # is resolved at runtime by components reading CLAUDE.md `## Component
    # Output Routing` blocks (rbtv-output-resolution rule). User runs
    # `/rbtv-output-routing` post-install to populate those blocks.
    ctx = resolve_from_cli(
        target=target_root,
        rbtv_path=rbtv_root,
        modules=chosen_modules,
    )

    removed = clear_module_installed_files(ctx.target_root)
    print(f"\nRemoved {len(removed)} previously-installed rbtv- files.")

    for module_name in chosen_modules:
        module = manifest[module_name]
        print(f"\nInstalling module: {module_name}")
        for skill in module.skills:
            written = install_skill(skill, module, ctx)
            print(f"  skill    → {written.relative_to(ctx.target_root)}")
        for command in module.commands:
            written = install_command(command, module, ctx)
            print(f"  cmd      → {written.relative_to(ctx.target_root)}")
        for rule in module.rules:
            written = install_rule(rule, module, ctx)
            print(f"  rule     → {written.relative_to(ctx.target_root)}")
        for subagent in module.subagents:
            written = install_subagent(subagent, module, ctx)
            print(f"  subagent → {written.relative_to(ctx.target_root)}")

    state_file = write_state(
        ctx.target_root,
        rbtv_version=str(defaults["rbtv"]["version"]),
        rbtv_relative=str(ctx.rbtv_relative).replace("\\", "/"),
        modules=chosen_modules,
    )
    print(f"\nState written to {state_file.relative_to(ctx.target_root)}")
    print("\nInstall complete.")
    print("")
    print("Next step: configure output path routing.")
    print("  Open a Claude Code session in the target workspace and run:")
    print("      /rbtv-output-routing")
    print("  This scans your CLAUDE.md files and interactively writes")
    print("  `## Component Output Routing` blocks so RBTV components know")
    print("  where to place outputs. See the rbtv-output-resolution rule")
    print("  for how components consume these blocks.")
    print("")
    print("  Skipping this step is OK — components fall back to degraded mode")
    print("  (ask-per-write) until routing is populated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/install/installer/__init__.py admin/install/installer/cli.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): CLI with module selection (output paths resolved at runtime per D7)"
```

---

### Task 32: Write install.py entrypoint

**Files:** `install.py` at RBTV root.

- [ ] **Step 1: Overwrite `install.py`**

Replace the old (BMAD-flavored) `install.py` with this minimal entrypoint:

```python
#!/usr/bin/env python3
"""install.py — RBTV standalone installer.

Installs thin loaders into a target workspace that point back to this RBTV source.
Modules are declared in admin/install/module-manifest.yaml.

Usage:
    python install.py --target /path/to/workspace
    python install.py --target /path/to/workspace --modules core,innovation
    python install.py --target /path/to/workspace --non-interactive
"""
from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    repo_root = Path(__file__).resolve().parent
    installer_parent = repo_root / "admin" / "install"
    if str(installer_parent) not in sys.path:
        sys.path.insert(0, str(installer_parent))


def main() -> int:
    _bootstrap_import_path()
    from installer.cli import main as cli_main
    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/rbtv" add install.py
git -C "H:/BMAD/rbtv" commit -m "feat(install): rewrite install.py as thin entrypoint to admin/install/installer"
```

---

### Task 33: Test install on a clean directory

**Files:** none modified in RBTV (test only).

- [ ] **Step 1: Create a clean test target**

```bash
mkdir "H:/BMAD/rbtv-install-test"
```

- [ ] **Step 2: Copy RBTV repo into the test target**

```bash
cp -r "H:/BMAD/rbtv" "H:/BMAD/rbtv-install-test/rbtv"
```

- [ ] **Step 3: Run the installer**

```bash
python "H:/BMAD/rbtv-install-test/rbtv/install.py" --target "H:/BMAD/rbtv-install-test" --modules core,innovation,work-productivity,writing --non-interactive
```

Per D7 (2026-04-17), install no longer prompts for output paths — `--non-interactive` succeeds from a fresh start as long as `--modules` is provided (or the default Core-only is acceptable).

- [ ] **Step 4: Verify the target structure**

```bash
ls "H:/BMAD/rbtv-install-test/.claude/skills"
```

Expected contents: `rbtv-planning/`, `rbtv-web-research/`, `rbtv-create-component/`, `rbtv-doc/`, `rbtv-domcobb/`, `rbtv-meeting-summarizer/`, `rbtv-playwright-cli/`, `rbtv-mentor/`, `rbtv-product-discovery/`, `rbtv-client-pitch/`, `rbtv-investor-pitch/`, `rbtv-designer/`, `rbtv-design-extraction/`, `rbtv-writing/`, `rbtv-tone-extraction/`.

```bash
ls "H:/BMAD/rbtv-install-test/.claude/commands"
```

Expected: 14 `rbtv-*.md` files.

```bash
ls "H:/BMAD/rbtv-install-test/.claude/rules"
```

Expected: 10 `rbtv-*.md` files (9 original + `rbtv-output-resolution.md` added per D7/Task 26A).

```bash
ls "H:/BMAD/rbtv-install-test/.claude/agents"
```

Expected: 2 `rbtv-*.md` files — `rbtv-designer.md`, `rbtv-web-research.md`.

```bash
cat "H:/BMAD/rbtv-install-test/rbtv.yaml"
```

Expected: valid YAML with `rbtv_version`, `installed_at`, `rbtv_path` (vault-relative — e.g., `rbtv`), `modules`. Per D7 (rewritten 2026-04-17), there is NO `output_paths` section.

- [ ] **Step 5: Inspect one baked loader — verify RELATIVE path**

```bash
cat "H:/BMAD/rbtv-install-test/.claude/skills/rbtv-planning/SKILL.md"
```

Verify:
- `{rbtv_path}` is replaced with a **vault-relative** path like `rbtv` (NOT `H:/BMAD/rbtv-install-test/rbtv`). If it shows an absolute path, the generator is not using `ctx.rbtv_relative` — bug in `generator.py:_resolve_bake_value`.
- No `{output_path_*}` placeholders appear anywhere in the baked loader — per D7, only `{rbtv_path}` is substituted. If any `{output_path_*}` or `{bmad_output}` remains, Task 18 Step 2 or Task 25 was not fully applied.
- The body begins with `**CRITICAL — Execute these steps in order...**` — if missing, the template was written without the imperative prefix (see Task 25 STYLE REQUIREMENT).

- [ ] **Step 5b: Verify meeting-summarizer loader points to a real workflow file**

```bash
cat "H:/BMAD/rbtv-install-test/.claude/skills/rbtv-meeting-summarizer/SKILL.md"
```

Confirm the baked path ends with `workflows/meeting-summarizer/workflow.md`. Then verify the target exists:

```bash
ls "H:/BMAD/rbtv-install-test/rbtv/workflows/meeting-summarizer/workflow.md"
```

Expected: the file exists (created in Task 18a). If it doesn't, meeting-summarizer will FileNotFound on first invocation.

- [ ] **Step 5c: Verify playwright-cli references resolve**

```bash
cat "H:/BMAD/rbtv-install-test/.claude/skills/rbtv-playwright-cli/SKILL.md" | grep -i "references/"
```

Confirm all `references/*` links are absolute-after-baking (e.g., `rbtv/skills/playwright-cli/references/playwright-tests.md`), not relative. If relative, Task 25 Step 7 wasn't applied.

Then verify the referenced files exist in RBTV source:

```bash
ls "H:/BMAD/rbtv-install-test/rbtv/skills/playwright-cli/references/"
```

Expected: all 9 reference files present.

- [ ] **Step 5d: Verify subagents installed correctly**

```bash
cat "H:/BMAD/rbtv-install-test/.claude/agents/rbtv-designer.md" | head -20
```

Confirm:
- Frontmatter `name:` is `rbtv-designer` (renamed, not `bmad-rbtv-designer`)
- Full subagent content present (copied, not a thin-loader stub)

- [ ] **Step 6: Test re-install (idempotent)**

```bash
python "H:/BMAD/rbtv-install-test/rbtv/install.py" --target "H:/BMAD/rbtv-install-test" --modules core --non-interactive
```

Expected:
- All prior `rbtv-*` files removed.
- Only core module loaders + rules reinstalled.
- `rbtv.yaml` updated with `modules: [core]`.

- [ ] **Step 7: Clean up the test**

```bash
rm -rf "H:/BMAD/rbtv-install-test"
```

- [ ] **Step 8: Commit any installer bug fixes discovered**

If the test revealed bugs (unlikely if the code in Tasks 27-32 was followed exactly, but possible), fix them and commit under a `fix(install): ...` message.

If no bugs, no commit needed for this task (tests don't modify RBTV).

---

## Phase 7: Documentation

**Goal:** Write the README and preserve or update the roadmap/vision.

### Task 34: Write README.md

**Files:** `README.md` at RBTV root.

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-7-start
```

- [ ] **Step 2: Write `README.md`**

```markdown
# RBTV

A standalone Claude Code toolkit for business innovation, pitch generation, documentation, and structured thinking.

## What is RBTV?

RBTV is a self-contained set of agents, workflows, skills, and rules designed to be bootstrapped into any Claude Code workspace. After install, RBTV appears as `/rbtv-<command>` slash commands (e.g., `/rbtv-client-pitch`, `/rbtv-doc`, `/rbtv-planning`) and auto-triggered skills in your workspace.

## Requirements

- Claude Code (CLI, desktop, or IDE extension)
- Python 3.11+ (for `install.py`)
- `pyyaml` Python package
- BMAD plugins for full functionality:
  - `bmad-method-lifecycle` (Ana references this for PRD, Brief, UX)
  - `bmad-pro-skills` (DomCobb references this for Problem Solving)

## Install

1. Clone RBTV as a subfolder of your workspace:

   ```bash
   cd /path/to/your/workspace
   git clone <rbtv-repo-url> rbtv
   ```

   RBTV must live INSIDE the workspace that will use it.

2. Run the installer:

   ```bash
   python rbtv/install.py --target /path/to/your/workspace
   ```

   The installer prompts for:
   - Modules to install (core is always included)

   Output paths are NOT configured at install time. They are resolved at runtime from `## Component Output Routing` blocks in your workspace's CLAUDE.md files (governed by the `rbtv-output-resolution` rule). See step 4 below to populate these blocks after install.

3. After install, your workspace has:
   - `.claude/skills/rbtv-*/` — thin loaders for skills (including `rbtv-output-routing` for the post-install setup in step 4)
   - `.claude/commands/rbtv-*.md` — slash commands (including `/rbtv-output-routing`)
   - `.claude/rules/rbtv-*.md` — rule content (copied — includes `rbtv-output-resolution` which governs how components resolve output paths at runtime)
   - `rbtv.yaml` — your install config

4. Configure output routing (one-time post-install):

   Open Claude Code in the workspace and run:

   ```
   /rbtv-output-routing
   ```

   The workflow scans your CLAUDE.md files and interactively writes `## Component Output Routing` blocks so RBTV components know where to place outputs. Routing is human-readable in CLAUDE.md and can be edited by hand or re-run via the same command whenever structure changes.

## Modules

| Module | What it does |
|---|---|
| **core** (always installed) | Generic productivity skills — planning, documentation, domcobb (problem structuring), meeting summarization, web research, component creation |
| **innovation** | Business innovation frameworks (lean canvas, JTBD, TAM/SAM/SOM, brandbook) via Paul, plus product discovery |
| **work-productivity** | Pitch generation (client, investor), design extraction, visual design via Vivian |
| **writing** | Long-form writing via George Orwell, tone extraction |

## Updating RBTV

RBTV content (agents, workflows, tasks) stays in this repo — thin loaders in your workspace reference it by path. To get new content:

```bash
cd /path/to/your/workspace/rbtv
git pull
```

Content changes appear live. You only need to re-run `install.py` when:
- Adding or removing modules
- RBTV's own module manifest or loader templates change

To change output routing, edit the `## Component Output Routing` blocks in your workspace CLAUDE.md files directly, or re-run `/rbtv-output-routing`. No install re-run needed.

## Source of truth

Installed files in `.claude/skills/rbtv-*`, `.claude/commands/rbtv-*.md`, `.claude/rules/rbtv-*.md` are regenerated on every `install.py` run. **Do not edit them in your workspace** — edit the source in this repo and re-install. See `.claude/rules/rbtv-source-of-truth.md` in your workspace for more.

## Architecture notes

- **Thin loaders:** installed loaders are short files that point back to this repo via absolute path. No content is duplicated into your workspace.
- **Rule exception:** rule files are copied as content (not loaders), because rules load passively into Claude's context and indirection is unreliable.
- **Overwrite scope:** re-install only affects `.claude/*/rbtv-*` files. Your workspace content (notes, projects, other skills) is never touched.

## Extending RBTV

Use `/rbtv-create-component` with Fernando. When you create a new component, Fernando asks whether to publish it to the RBTV source (requires re-install to propagate) or write it locally to your workspace only.

## License and contact

TBD.
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add README.md
git -C "H:/BMAD/rbtv" commit -m "docs: add README for standalone RBTV"
```

---

### Task 35: Update admin/roadmap.md with the intermediary-plan note

**Files:** `admin/roadmap.md`.

- [ ] **Step 1: Read existing roadmap**

```bash
cat "H:/BMAD/admin/roadmap.md" 2>/dev/null || echo "File does not exist — will create."
```

- [ ] **Step 2: If roadmap.md exists, prepend a new section; if not, create it**

Either prepend the section below to the existing content or create the file with this content:

```markdown
# RBTV Roadmap

## Current state (2026-04-16)

RBTV is standalone — decoupled from BMAD, bootstrappable via `install.py`. Henri's Second Brain vault is the first instance. See the intermediary plan at `<vault>/1. Projects/second-brain-evolution/2026-04-16-rbtv-intermediary-plan.md` for the decoupling decisions.

## Next (deferred — full product plan)

- Import Second Brain personal-productivity components into RBTV as a new module (`personal-productivity`) with graceful degradation and personal-data stripping.
- Build a modular summarizer framework (replaces the current meeting-summarizer workflow).
- Build an onboarding workflow for new users (multi-user support).
- Split the financial sub-module from personal-productivity.

See the earlier standalone plan at `<vault>/1. Projects/second-brain-evolution/2026-04-15-rbtv-standalone-plan.md` for the design sketch of the full product plan.
```

- [ ] **Step 3: Commit**

```bash
git -C "H:/BMAD/rbtv" add admin/roadmap.md
git -C "H:/BMAD/rbtv" commit -m "docs: update roadmap with standalone milestone and deferred work"
```

---

## Phase 8: Henri's Instance

**Goal:** Move RBTV into Henri's vault, run the installer, verify installation. Tecer repo moves and BMAD root elimination are handled separately.

### Task 36: Move RBTV repo into the vault

**Files:**
- Move: `H:/BMAD/` → `H:/BMAD/projects/second-brain/3. Resources/rbtv/`
- Modify: `H:/BMAD/projects/second-brain/.gitignore`

- [ ] **Step 1: Tag phase start**

```bash
git -C "H:/BMAD/rbtv" tag rbtv-standalone-phase-8-start
```

- [ ] **Step 2: Verify RBTV working tree is clean**

```bash
git -C "H:/BMAD/rbtv" status
```

Expected: "nothing to commit, working tree clean". If dirty, commit or stash first.

- [ ] **Step 3: Push RBTV to remote (safety backup)**

```bash
git -C "H:/BMAD/rbtv" push origin feat/rbtv-standalone
```

Skip if no remote is configured.

- [ ] **Step 4: Move the repo**

```bash
mv "H:/BMAD/rbtv" "H:/BMAD/projects/second-brain/3. Resources/rbtv"
```

- [ ] **Step 5: Verify git works from the new location**

```bash
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" status
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" log --oneline -3
```

Expected: clean status, recent commits visible. The `.git/` folder moved with the repo.

- [ ] **Step 6: Add rbtv to vault .gitignore**

Read `H:/BMAD/projects/second-brain/.gitignore`. Append:

```
3. Resources/rbtv/
```

Save the file.

- [ ] **Step 7: Commit vault .gitignore**

```bash
git -C "H:/BMAD/projects/second-brain" add .gitignore
git -C "H:/BMAD/projects/second-brain" commit -m "chore: add 3. Resources/rbtv/ as nested git repo (ignored by vault)"
```

---

### Task 37: Run install.py targeting the vault

**Files:**
- Create: `H:/BMAD/projects/second-brain/rbtv.yaml`
- Create: `H:/BMAD/projects/second-brain/.claude/skills/rbtv-*/` (15 directories)
- Create: `H:/BMAD/projects/second-brain/.claude/commands/rbtv-*.md` (14 files)
- Create: `H:/BMAD/projects/second-brain/.claude/rules/rbtv-*.md` (9 files)
- Create: `H:/BMAD/projects/second-brain/.claude/agents/rbtv-*.md` (2 files — designer, web-research)

- [ ] **Step 1: Ensure PyYAML is installed**

```bash
pip install pyyaml
```

- [ ] **Step 2: Run the installer interactively**

```bash
python "H:/BMAD/projects/second-brain/3. Resources/rbtv/install.py" --target "H:/BMAD/projects/second-brain"
```

At the prompts:
- **Modules**: `core,innovation,work-productivity,writing` (all four)

Per D7 (rewritten 2026-04-17), the installer does NOT prompt for output paths. Routing is configured post-install via `/rbtv-output-routing` in step 6.

- [ ] **Step 3: Verify installation**

```bash
ls "H:/BMAD/projects/second-brain/.claude/skills" | grep rbtv-
```

Expected: 16 directories starting with `rbtv-` (15 original + `rbtv-output-routing` added per D7/Task 26A).

```bash
ls "H:/BMAD/projects/second-brain/.claude/commands" | grep rbtv-
```

Expected: 15 files starting with `rbtv-` (14 original + `rbtv-output-routing.md`).

```bash
ls "H:/BMAD/projects/second-brain/.claude/rules" | grep rbtv-
```

Expected: 10 files starting with `rbtv-` (9 original + `rbtv-output-resolution.md`).

```bash
ls "H:/BMAD/projects/second-brain/.claude/agents" | grep rbtv-
```

Expected: 2 files — `rbtv-designer.md`, `rbtv-web-research.md`.

```bash
cat "H:/BMAD/projects/second-brain/rbtv.yaml"
```

Expected: valid YAML with `modules: [core, innovation, work-productivity, writing]`, `rbtv_path: "3. Resources/rbtv"` (vault-relative). Per D7, NO `output_paths` section.

- [ ] **Step 4: Verify existing SB content is untouched**

```bash
ls "H:/BMAD/projects/second-brain/.claude/skills" | grep -v rbtv-
```

Expected: SB's original skills (e.g., `vault-ops`, `vault-integrity`, `google-tools`, `commit`, `web-search`, `karpathy-code`, `md-to-pdf`, `summarize`) — all present and unchanged.

```bash
ls "H:/BMAD/projects/second-brain/_system"
```

Expected: unchanged — workflows, templates, user, etc. No `_system/rbtv/` created.

- [ ] **Step 5: Commit the newly-installed files**

```bash
git -C "H:/BMAD/projects/second-brain" add rbtv.yaml ".claude/skills" ".claude/commands" ".claude/rules" ".claude/agents"
git -C "H:/BMAD/projects/second-brain" commit -m "feat: install RBTV standalone loaders into vault"
```

- [ ] **Step 6: Configure output routing (interactive, via Claude Code)**

Open Claude Code at the vault root and run:

```
/rbtv-output-routing
```

The setup workflow (Task 26A) will scan the vault, read existing CLAUDE.md files (vault root, `2. Areas/tecer/tecer-biz/`, any other sub-projects already using the `## Component Output Routing` convention), and interactively propose routing blocks.

Reference routing for Henri's vault (use this as a guide when the workflow asks):

| Output type | Vault root routing |
|---|---|
| `pitch` | delegate to `2. Areas/tecer/tecer-biz/` (tecer-biz's CLAUDE.md further routes by client / prospect / investor) |
| `planning` | `1. Projects/{project}/` |
| `meeting-summary` | ask per project at runtime (Tecer, Tennis Arte, personal contexts differ) |
| `writing` | ask at runtime (writing outputs vary by piece) |
| `doc` | ask at runtime (documentation targets vary) |
| `product-discovery` / `business-innovation` / `design-extraction` / `tone-extraction` / `create-component` | leave unrouted for now — degraded mode (ask-per-write) is fine until a pattern emerges |

If the tecer-biz plan has already populated `2. Areas/tecer/tecer-biz/CLAUDE.md` with its own `## Component Output Routing` block, the workflow should detect and preserve it.

- [ ] **Step 7: Commit CLAUDE.md routing changes**

```bash
git -C "H:/BMAD/projects/second-brain" add CLAUDE.md
```

Also add any sub-project CLAUDE.mds touched by the routing workflow (confirm with the workflow's summary in step 6):

```bash
git -C "H:/BMAD/projects/second-brain" add "2. Areas/tecer/tecer-biz/CLAUDE.md"
```

(Only add files that actually changed.)

```bash
git -C "H:/BMAD/projects/second-brain" commit -m "chore: add Component Output Routing blocks via /rbtv-output-routing"
```

---

### Task 38: Smoke-test a loader

**Files:** none modified (test only).

- [ ] **Step 1: Open a fresh Claude Code session at the vault root**

```bash
cd "H:/BMAD/projects/second-brain"
claude
```

- [ ] **Step 2: Invoke `/rbtv-domcobb`**

Type `/rbtv-domcobb` in the Claude Code prompt. Expected behavior:
- Command file at `.claude/commands/rbtv-domcobb.md` loads
- Claude reads `3. Resources/rbtv/agents/domcobb/domcobb.md` (baked vault-relative path)
- DomCobb's persona activates and presents its menu

- [ ] **Step 2b: Invoke `/rbtv-client-pitch` (verify workflow chain)**

Type `/rbtv-client-pitch` and observe Claude's response. Expected:
- Leo's persona activates from the command's baked path
- The pitch workflow loads (either as menu or first step depending on the workflow design)
- If Claude responds conversationally instead of loading Leo, the imperative language is too weak — revisit Task 25 STYLE REQUIREMENT

- [ ] **Step 2c: Invoke `/rbtv-meeting-summarizer` (verify Task 18a transformation worked)**

Type `/rbtv-meeting-summarizer`. Expected:
- The workflow at `3. Resources/rbtv/workflows/meeting-summarizer/workflow.md` loads
- Claude asks for the transcript path (Step 1 of the workflow)
- No FileNotFound error (which would mean Task 18a created the workflow.md correctly)

- [ ] **Step 2d: Verify a subagent can be dispatched**

Type: "dispatch the rbtv-web-research subagent to research <some topic>". Expected:
- Claude invokes the Task tool with the `rbtv-web-research` subagent_type
- If Claude reports "no such subagent type," either the subagent file was not installed at `.claude/agents/rbtv-web-research.md` or Claude Code hasn't picked it up (restart session and retry)

- [ ] **Step 3: Exit the session without taking further actions**

If all four invocations succeed, the install works. Any path-resolution errors indicate baked paths are wrong — investigate (likely `generator.py:_resolve_bake_value` or templates).

- [ ] **Step 4: Document the test result in the vault's changelog**

Read `H:/BMAD/projects/second-brain/_system/user/changelog.md`. Under today's date heading (create if missing), append:

```markdown
- ✅ [system] RBTV standalone installed into vault. 15 skills, 14 commands, 9 rules installed as thin loaders/copies. `rbtv.yaml` created in vault root. Existing SB content unchanged. Smoke test passed (/rbtv-domcobb loads DomCobb's persona). Updated: `rbtv.yaml`, `.claude/skills/rbtv-*`, `.claude/commands/rbtv-*`, `.claude/rules/rbtv-*`
```

- [ ] **Step 5: Commit the changelog**

```bash
git -C "H:/BMAD/projects/second-brain" add _system/user/changelog.md
git -C "H:/BMAD/projects/second-brain" commit -m "chore(changelog): record RBTV standalone install"
```

---

### Task 39: Merge the RBTV feature branch

**Files:** none modified in vault.

- [ ] **Step 1: Verify RBTV feature branch passes tests**

From Phase 6 Task 33 — the test install succeeded. If it did, proceed. If not, return to the failing task before merging.

- [ ] **Step 2: Merge feat/rbtv-standalone into main**

```bash
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" checkout main
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" merge --no-ff feat/rbtv-standalone -m "Merge feat/rbtv-standalone: standalone install, thin loaders, module manifest"
```

- [ ] **Step 3: Push main to remote**

```bash
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" push origin main
```

Skip if no remote.

- [ ] **Step 4: Delete the feature branch locally and remotely**

```bash
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" branch -d feat/rbtv-standalone
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" push origin --delete feat/rbtv-standalone
```

Skip the remote deletion if no remote.

- [ ] **Step 5: Tag the merged state**

```bash
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" tag rbtv-v7.0.0
git -C "H:/BMAD/projects/second-brain/3. Resources/rbtv" push origin rbtv-v7.0.0
```

---

## Phase 9: Handoff Note for Separate Agent

### Task 40: Write handoff note

**Files:** `1. Projects/second-brain-evolution/2026-04-16-rbtv-handoff-to-next-agent.md`

- [ ] **Step 1: Write the handoff file**

```markdown
# Handoff: Tecer Migration + BMAD Root Elimination

After the RBTV intermediary plan (`2026-04-16-rbtv-intermediary-plan.md`) is complete, the following workstreams are ready to execute. These are NOT part of this plan — the user instructed they be handled by another agent.

## State at handoff

- RBTV lives at `H:/BMAD/projects/second-brain/3. Resources/rbtv/` as a nested git repo (ignored by vault)
- Vault has RBTV standalone installed (`.claude/skills/rbtv-*`, etc.)
- Existing SB content is unchanged
- `H:/BMAD/` no longer exists (moved to vault)

## Remaining under `H:/BMAD/`

- `H:/BMAD/projects/tecer-biz/` — Tecer business repo, needs to move into vault
- `H:/BMAD/projects/tecer-website/` — Tecer website repo, needs to move into vault
- `H:/BMAD/projects/personal/` — Personal project, needs to move to vault archives
- `H:/BMAD/` — BMAD module parent — may have `bmm/`, `cis/`, `core/` siblings to RBTV (RBTV already removed)
- `H:/BMAD/.claude/`, `H:/BMAD/CLAUDE.md` — BMAD root config that becomes obsolete once nothing is worked on from BMAD root

## Tasks

The previous full-product plan (`2026-04-15-rbtv-standalone-plan.md`) describes equivalent work in its Phase 2 and Phase 7:

1. **Move tecer-biz into vault at `2. Areas/tecer/tecer-biz/`** (Phase 2 Task 3 of Plan 2; Task 3 of Plan 1 — Plan 1's steps are directly reusable)
2. **Move tecer-website into vault at `2. Areas/tecer/tecer-website/`** (Plan 1 Task 4)
3. **Move personal to vault archives at `4. Archives/personal/`** (Plan 1 Task 5)
4. **Update vault's Git Repositories table in CLAUDE.md** (Plan 1 Task 6)
5. **Update Tecer project CLAUDE.md files** (Plan 1 Task 16)
6. **Verify nothing references H:/BMAD/ paths anywhere in vault** (Plan 1 Task 19 Step 1)
7. **Move the vault to a top-level path (optional)** — e.g., `H:/second-brain/` (Plan 1 Task 19 Step 3)
8. **Delete `H:/BMAD/`** — only after verifying nothing above is pending (Plan 1 Task 19 Step 4)
9. **Configure Obsidian to exclude heavy folders** — `3. Resources/rbtv/`, `2. Areas/tecer/tecer-biz/product-specs/`, etc. (Plan 1 Task 17)
10. **Final verification** — fresh Claude Code session, all commands work (Plan 1 Task 20)

## Execution suggestion

Read Plan 1 (migration plan) Phase 2 onwards and Plan 2 (standalone plan) Phase 7 onwards. Most steps are identical and can be copied verbatim.
```

- [ ] **Step 2: Commit**

```bash
git -C "H:/BMAD/projects/second-brain" add "1. Projects/second-brain-evolution/2026-04-16-rbtv-handoff-to-next-agent.md"
git -C "H:/BMAD/projects/second-brain" commit -m "docs: handoff note for Tecer migration + BMAD root elimination"
```

---

## Execution Notes

**Phase order:** Phases 0-8 are sequential (each builds on the previous). Phase 9 is a documentation handoff only.

**Companion plan:** See `1. Projects/second-brain-evolution/2026-04-16-vault-move-preparedness-plan.md` for fixing absolute-path references throughout the vault (separate workstream from RBTV). Execute that plan BEFORE the Tecer + BMAD-root-removal handoff agent moves the vault.

**Hardest phases:**
- **Phase 4** (Task 18 + Task 18a) — bulk path substitution + meeting-summarizer transformation. Use editor's "Find in Files" carefully.
- **Phase 6** (Tasks 27-32) — Python installer implementation. Test thoroughly (Task 33).

**Total estimated work:**
- Phase 1-2 (flatten + nest): ~10 commits, mechanical
- Phase 3 (prefix strip): ~3 commits, mechanical
- Phase 4 (BMAD dep strip): ~5 commits, requires judgment on plugin replacements
- Phase 5 (drops): ~4 commits, trivial
- Phase 6 (install infra): ~10 commits, real engineering
- Phase 7 (docs): ~2 commits
- Phase 8 (Henri's instance): ~4 commits
- Phase 9 (handoff): 1 commit

**File touch estimate:** ~100 renames + moves, ~50 internal-reference edits, ~20 new files (installer package, README, manifest, templates, commands), ~8 deletions.

**Rollback:** Each phase tagged. `git reset --hard rbtv-standalone-phase-N-start` reverts to the start of that phase. Feature branch `feat/rbtv-standalone` contains all work until merged in Task 39.

**Post-plan:**
- Henri can `git pull` in `3. Resources/rbtv/` anytime to get updated content. Content changes are live.
- Adding/removing modules requires re-running `install.py`. Changing output routing is done inside the workspace via `/rbtv-output-routing` (edits `## Component Output Routing` blocks in CLAUDE.md files) — no install re-run needed.
- Fernando-created new components either live in RBTV source (needs re-install) or directly in the target `.claude/` without prefix (not touched by re-install).
- Tecer moves and BMAD root elimination are handed off (Phase 9).

---

## Self-Review Checklist

Before execution, verify:

- [ ] All `bmad-rbtv-*` file renames listed are covered in Phase 3 tasks.
- [ ] All workflow and task relocations (agent-nested) have corresponding path-reference fixes in Task 13.
- [ ] All BMAD external references (`bmad_core`, `bmad_bmm`, `bmad_cis`) have deletion/replacement tasks in Phase 4.
- [ ] The manifest in Task 24 lists every kept skill, command, rule, AND subagent, with correct `bake` keys for skills/commands.
- [ ] Each `SKILL.md` template in Task 25 matches its manifest entry's `bake` keys (no mismatch between what the template uses and what the manifest says to substitute).
- [ ] Each `SKILL.md` template begins with `**CRITICAL — Execute these steps in order...**` (Task 25 STYLE REQUIREMENT).
- [ ] Each `commands/<name>.md` template in Task 26 matches its manifest entry.
- [ ] Rules are in the manifest as `mode: copy` (not as loaders) — 9 rules total in Module A.
- [ ] Subagents (Module A) are in the manifest as `mode: copy` — 2 subagents total (`designer`, `web-research`).
- [ ] Task 18a (meeting-summarizer transformation) executes BEFORE Task 25 (so the workflow.md exists before the template references it).
- [ ] Task 3a (subagent migration) executes BEFORE Task 22 (admin/claude deletion), otherwise the subagent files are lost.
- [ ] Task 25 Step 7 rewrites playwright-cli references links to use `{rbtv_path}/skills/playwright-cli/references/...` (absolute-after-baking), otherwise 9 reference files become unreachable in the target.
- [ ] Generator's `_resolve_bake_value` uses `ctx.rbtv_relative` (not `ctx.rbtv_root`) — verify at Task 29 Step 1 and again at Task 33 Step 5.
- [ ] The installer code in Tasks 27-32 writes to the correct target paths (with `rbtv-` prefix) and only cleans `rbtv-`-prefixed files on re-install.
- [ ] `clear_module_installed_files` extends to `.claude/agents/rbtv-*.md` (subagent overwrite scope).
- [ ] `rbtv.yaml` is preserved across re-installs (not overwritten by `clear_module_installed_files`).
- [ ] Task 33's smoke test runs on a scratch directory, not the real vault.
- [ ] Task 33 Steps 5b-5d verify meeting-summarizer workflow existence, playwright-cli reference links, and subagent install.
- [ ] Phase 8's vault install happens AFTER the feature branch merges (Task 39 after Task 37 — note order inversion below).

**Order clarification:** Task 37 installs into the vault from the feature branch (before merge) because the merge in Task 39 happens in the RBTV repo AFTER it has moved into the vault. If you prefer merge-before-install, swap Tasks 37 and 39 — but then the vault install runs from `main` instead of the feature branch, which is fine but means any bugs found in Task 38 require a new feature-branch commit.

---

## Out of Scope (Do Not Execute Here)

- Second Brain workflows (weekly-review, accountant, vault-ops, etc.) — left unchanged in this plan.
- SB component absorption into RBTV — deferred to a future full-product plan.
- Multi-user onboarding — deferred.
- Modular summarizer framework — deferred.
- Personal-data stripping from SB components — deferred.
- Tecer repo moves — handed off (Phase 9).
- BMAD root elimination — handed off (Phase 9).
- Obsidian configuration for heavy folders — handed off (Phase 9).
