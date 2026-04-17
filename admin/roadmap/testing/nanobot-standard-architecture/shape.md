# Shape - Nanobot Standard Architecture + RBTV Batch Changes

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Simplifies nanobot/RBTV integration from custom adapter architecture to standard nanobot workspace patterns
- Unifies three RBTV installer scripts (IDE, admin, nanobot-sync) into a single script with 3 modes
- Cleans up `_mobile/` — deletes dead code, relocates surviving files, rewrites documentation
- Executes 5 independent RBTV improvement PRDs/compounds that share tooling touchpoints with the restructuring
- Establishes a private GitHub repo as the nanobot workspace for version-controlled bootstrap files
- Preserves the `robotville.ai` deployment capability

**What this plan does NOT include:**
- Modifying nanobot's native architecture or source code (RBTV adapts TO nanobot, never the reverse)
- Modifying anything under `_admin/docs/BMAD-mirror/` content (exception: RBTV-owned metadata like MIRROR-VERSION.md)
- Creating CI/CD pipelines or automated deployment beyond what exists
- Exposing specific nanobot skills (deferred to implementation — decided when editing entry_points.md)
- Adding new RBTV features or business innovation workflows

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Workspace repo | Private GitHub repo = nanobot workspace folder | Enables GitHub-based review, version-controlled bootstrap files, eliminates need for FileZilla/terminal access |
| `.gitignore` strategy | Whitelist: ignore everything, un-ignore bootstrap files only | BMAD, RBTV, outputs, memory are all installed/generated — only bootstrap files are authored |
| Bootstrap flow | Create GitHub repo → clone to VPS workspace → install nanobot → install BMAD → clone RBTV → run sync | Nanobot is born with correct bootstrap files already present |
| Entry points | Manually maintained `entry_points.md` in workspace repo | Simpler than manifest-driven generation; Henri edits locally, pushes to GitHub |
| Nanobot architecture | NEVER altered — bootstrap files live where nanobot expects them | RBTV adapts TO nanobot per Admin Restriction #3 |
| Installer unification | One script with 3 modes: IDE, admin, nanobot-sync | Reduces maintenance surface; shared functions handle common operations |
| Sync script scope | Patches BMAD configs for RBTV only; does NOT generate entry_points or create IDE config | Minimal scope — bootstrap files and entry_points are in the workspace repo |
| `_mobile/` survival | Simplify aggressively, keep as minimal folder | README with server access info; relocated files go to surviving paths within RBTV |
| TypeScript harness | Delete entirely (4 files, ~1,024 lines) | Dead code — never wired into nanobot runtime; integration was always via markdown bootstrap files |
| Source patches | Delete both `add-litellm-prompt-caching.py` and `add-litellm-retries.py` | Prompt caching native since Feb 18, 2026; retries replaceable via env var `LITELLM_NUM_RETRIES=3` |
| Shell deploy scripts | Delete all 3 (`vps-sync-install.sh`, `vps-install-git-hooks.sh`, `vps-pull-rbtv.sh`) | Replaced by unified installer sync mode + `git pull` |
| Config helpers | Keep and relocate (4 files) | Still useful for VPS admin tasks |
| Website HTML files | Relocate within RBTV (4 files) | Needed for `robotville.ai` deploy; update path in `TOOLS.md` |
| Bootstrap files | Move to workspace GitHub repo | Already standard nanobot files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) |
| Allowlist | Native nanobot `config.json` (`channels.slack.dm.allow_from`) | Replaces dead TypeScript `allowlist-gate.ts` |
| Project-memo contract | `SOUL.md` behavioral instruction | Simple enough for prompt-based enforcement; no code needed |
| Output paths | `projects/{project-name}/` via SOUL.md instruction + BMAD config patching by sync | Dual enforcement: nanobot sees it in system prompt, config has it as default |
| PRD execution scope | All 5 independently valuable for RBTV, batched because they share installer/config touchpoints | Not nanobot-specific — they impact Cursor IDE and all RBTV contexts equally |
| PRD 4 → PRD 3 dependency | Version declaration must be implemented before compatibility check | Compatibility check consumes version fields from PRD 4 |
| `robotville.ai` deployment | Preserved — relocate static HTML files, update source path in `TOOLS.md` | Netlify CLI + site ID unchanged; only the file location within RBTV changes |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Never modify nanobot native architecture | Admin Restriction #2 adapted for nanobot | All integration via standard bootstrap files; no source patches post-cleanup |
| Never modify `_admin/docs/BMAD-mirror/` content | CLAUDE.md boundary rule | Exception: RBTV-owned metadata files about the mirror (e.g., `MIRROR-VERSION.md`) |
| Preserve `{project-root}` placeholders in RBTV files | CLAUDE.md boundary rule | Placeholders are runtime-resolved; editing must not replace them with literals |
| BMAD is in beta (soft version enforcement) | BMAD project status | Installer version check warns, does not hard-fail |
| No users, no downtime risk | Current deployment state | Total freedom to restructure; no migration concerns |
| ~60 files need path variable migration (PRD 5) | Codebase audit | Labor-intensive but mechanical; backwards compatibility needed during transition |
| BMAD mirror must be updated Beta.4 → Beta.8 before PRD 4 | PRD 4 prerequisite | Stale mirror blocks version declaration; Beta.7 workflow splitting is a known risk |
| Micro-commit discipline | CLAUDE.md admin restrictions | At least one commit per phase; push after every commit; Conventional Commits format |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Core intent | "Revert to standard nanobot implementation, having BMAD and all its folders in nanobot's workspace folder" | Workspace architecture: private GitHub repo = nanobot workspace = BMAD project root |
| 2 | Bootstrap workflow | "Install nanobot → install BMAD → clone RBTV → run sync script" | Refined to: create GitHub repo first with bootstrap files, then clone to VPS, then install nanobot (so it inherits existing bootstrap files) |
| 3 | Entry points exposure | "Create entry_points.md in root with list of all commands/skills/agents" | Changed from sync-script-generated to manually maintained file in workspace GitHub repo — simpler, version-controlled |
| 4 | Workspace as GitHub repo | "I want nanobot's workspace/ folder to be a private repo in GitHub, so I can easily review files without FileZilla or terminal" | Whitelist `.gitignore` strategy tracking only bootstrap files; BMAD/RBTV/memory/outputs all gitignored |
| 5 | Sync script purpose | "rbtv-vps-nanobot-sync.py — does not touch nanobot original files, just creates .md files that expose entry points" | Refined: sync script patches BMAD configs only; entry_points.md is in workspace repo, not generated |
| 6 | Architecture freedom | "Design from scratch — delete all nanobot files if needed, no users, no downtime risk" | Enabled aggressive cleanup of `_mobile/`; all TypeScript/shell scripts identified as dead code |
| 7 | Output path enforcement | "Critical that nanobot understands where to correctly place outputs when user mentions /rbtv" | SOUL.md instruction for output path + BMAD config patching by sync mode |
| 8 | PRD scope clarification | "PRDs are important not only for nanobot but for RBTV as a whole — batched because they share touchpoints" | All 5 PRDs maintained as independently valuable RBTV improvements, executed in same batch for efficiency |
| 9 | Installer unification | "We can merge them all in one script with 3 modes" | Unified installer with IDE, admin, and nanobot-sync modes; shared functions for BMAD config updates |
| 10 | Nanobot bootstrap file handling | "Bootstrap files should be in the GitHub repo first, then nanobot inherits them on install" | Reversed original assumption: create repo with bootstrap files → clone to VPS → install nanobot |
| 11 | Robotville.ai deployment | "Nanobot currently has capability to deploy to robotville.ai — this is important" | Deployment preserved: relocate HTML files, update path in TOOLS.md; Netlify CLI + site ID unchanged |
| 12 | Deliverable format | "Document must cover all decisions so there is no rework when creating the plan" | Comprehensive structured problem document with all architectural decisions, file disposition map, PRD summaries, dependency graph |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | TypeScript harness disposition | User wanted to "revert to standard nanobot" | AI discovered TypeScript files were dead code — never wired into runtime; integration was already via markdown bootstrap files | Delete entirely; the "simplification" is actually cleanup, not rewriting |
| 2 | Source patch obsolescence | User was uncertain about prompt caching patch status | AI identified nanobot added native prompt caching support on Feb 18, 2026 | Delete `add-litellm-prompt-caching.py`; delete `add-litellm-retries.py` (replaceable via env var) |
| 3 | Workspace `.gitignore` strategy | User noted "BMAD must be in the gitignore" | AI proposed whitelist strategy (ignore everything, un-ignore specific files) instead of explicit exclusion list | Whitelist `.gitignore` — cleaner, self-maintaining as new installed components appear |
| 4 | Entry points generation vs manual | User initially envisioned sync script creating entry_points.md | AI suggested: if workspace is a GitHub repo, entry_points.md can be version-controlled and manually maintained | Manual maintenance in workspace repo; sync script has no entry_points responsibility |
| 5 | Config helpers disposition | User was uncertain ("no idea" about allowlist handling) | AI evaluated each script individually: allowlist → native config.json, project-memo → SOUL.md instruction, config helpers → useful utilities to keep | Differentiated: delete dead/obsolete, keep useful utilities, relocate within RBTV |
| 6 | Nanobot `INSTRUCTIONS.md` bootstrap | User mentioned "native INSTRUCTIONS.md file" | AI discovered nanobot has no `INSTRUCTIONS.md` — bootstrap files are `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`, `IDENTITY.md` | Corrected: use actual nanobot bootstrap file names; entry_points.md referenced from SOUL.md or TOOLS.md |
| 7 | Bootstrap sequence order | User proposed: install nanobot → install BMAD → clone RBTV | AI identified: if bootstrap files are created first in GitHub repo, nanobot should be installed AFTER cloning the repo so it inherits them | Revised: create GitHub repo → clone to VPS → install nanobot → install BMAD → clone RBTV → run sync |
| 8 | Robotville.ai deploy preservation | User asked if changes break deployment | AI traced deploy flow: TOOLS.md `deploy site` command → Netlify CLI → static HTML files; only path reference needs updating | Preserved: relocate HTML files within RBTV, update source path in TOOLS.md, Netlify CLI/site ID unchanged |

---

## Standards Applied

### RBTV Admin Restrictions

| Standard | Application in This Plan |
|----------|-------------------------|
| BMAD Component Map Check | Must check `bmad-help.csv` before creating new components — installer adds RBTV entry |
| Never Touch BMAD | All BMAD modifications automated via installer/sync script; no manual BMAD file edits |
| Leverage BMAD | Use BMAD's native config structure, output paths, module system |
| Prefer Native BMAD | Do not duplicate BMAD functionality in RBTV — use BMAD components directly |
| Minimal Internalization | Reference BMAD files rather than copying; only internalize what sync mode needs |

### Micro-Commit Discipline

| Standard | Application in This Plan |
|----------|-------------------------|
| Conventional Commits | `type(scope): P{phase}-{task-id} description` format |
| Push after each commit | Never batch pushes |
| Minimum per phase | At least one commit per plan phase |
| Sequential letters | `a`, `b`, `c` suffixes for multi-commit tasks |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| PRD 4 before PRD 3 | Dependency chain: version declaration fields must exist before compatibility check can consume them |
| BMAD mirror update before PRD 4 | Cannot declare Beta.8 target version with Beta.4 mirror |
| Installer changes centralized | All 3 modes modified in same phase to prevent divergence |
| File disposition tracking | Every `_mobile/` file must be accounted for: deleted, moved, rewritten, or explicitly preserved |

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

### Discovery P1-A: BMAD target version changed from Beta.8 to Beta.4

**Date:** 2026-02-23 | **Task:** p1-1

User confirmed that the installed BMAD version is Beta.4 (not Beta.8). The plan originally specified updating the mirror to Beta.8, but the user instructed to use Beta.4 as the target — the same version already in the mirror. This makes p1-1 a verify task (no mirror update needed) and p1-2 N/A (no Beta.7 workflow splitting risk at Beta.4). All version declarations set to `6.0.0-Beta.4` (both target and min). A separate post-plan PRD will cover what is needed to migrate to the latest BMAD release.

**Impact:** p1-1 (verify only), p1-2 (N/A — Beta.7 risk does not apply), p1-3 (Beta.4 declared, not Beta.8)

### Discovery P1-B: Config helper relocation destination proposed

**Date:** 2026-02-23 | **Task:** p5-4 (pre-decided before phase 5)

Config helper scripts (4 files from `_mobile/ops/patches/`) will be relocated to `_mobile/ops/helpers/` — rename from "patches" to "helpers" since these are admin utility scripts, not source patches. Systemd service stays at `_mobile/ops/systemd/`. Website HTML files (netlify-placeholder) move to `_mobile/web/`. This was a TBD in the plan, resolved by proposing and self-approving per user's "execute autonomously" instruction.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `structured-problem-2026-02-22.md` | Complete problem tree, MECE validation, all architectural decisions, file disposition map, dependency graph, nanobot technical reference |
| `prd-config-bmad-version-declaration.md` | PRD 4: Add `bmad_target_version`/`bmad_min_version` to config.yaml, create `MIRROR-VERSION.md`, create `CHANGELOG.md`; prerequisite action: update mirror Beta.4→Beta.8; risk: Beta.7 workflow splitting |
| `prd-config-bmad-compatibility-check.md` | PRD 3: Create `bmad-compat.yaml`, `tasks/check-bmad-compat.xml`, installer pre-flight check; depends on PRD 4; warn-only enforcement |
| `cp-install-scripts-standardize-bmad-output-folder.md` | CP 2: Both installers apply same output-path normalization to `projects/{project-name}/`; compound workflow output routing correction |
| `prd-reduce-path-resolution-hops.md` | PRD 5: Add `paths:` section to config.yaml; migrate ~60 cross-module references; simplify resolution table in CLAUDE.md |
| `prd-standardize-main-config-frontmatter.md` | PRD 6: Mandate frontmatter config declaration; audit 38 workflows, migrate ~10; update component patterns documentation |
| `_mobile/README.md` | Original harness boundary definition; scope and responsibility split with nanobot |
| `_mobile/HOW-IT-WORKS.md` | Documented architecture of dead TypeScript harness (inbound pipeline, bridge, router, allowlist gate, state adapter) |
| `_mobile/ops/scripts/vps-sync-install.sh` | Current VPS deployment mechanism; confirmed TypeScript files never used at runtime; bootstrap files deployed directly |
| `_config/install-rbtv.py` | Current IDE installer: copies `.cursor/` config, merges MCP, updates BMAD configs, adds to `bmad-help.csv` |
| `_admin/install-admin-rbtv.py` | Current admin installer: path substitution, reinforcement append, `.gitignore`, config prompts |
| `CLAUDE.md` | Repository identity, path resolution rules, installation details, admin restrictions, commit discipline |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `structured-problem-2026-02-22.md` | Primary reference for all architectural decisions, file dispositions, nanobot technical details | Before each phase |
| `_config/config.yaml` | RBTV module configuration — will be modified by PRDs 4 and 5 | PRD 4, PRD 5 tasks |
| `_config/install-rbtv.py` | Current IDE installer — will be refactored into unified installer | Installer unification phase |
| `_admin/install-admin-rbtv.py` | Current admin installer — will be absorbed into unified installer | Installer unification phase |
| `_mobile/AGENTS.md` | Bootstrap file to move to workspace repo | Workspace setup phase |
| `_mobile/SOUL.md` | Bootstrap file to move — may need output path instruction updates | Workspace setup phase |
| `_mobile/TOOLS.md` | Bootstrap file to move — needs website source path update | Workspace setup phase |
| `_mobile/USER.md` | Bootstrap file to move to workspace repo | Workspace setup phase |
| `CLAUDE.md` | Path resolution table to simplify after PRD 5; mirrored sections to update | PRD 5, cleanup phase |
| `.cursor/rules/admin-rbtv-bmad-mirror.mdc` | Path resolution table mirrored from CLAUDE.md — update together | PRD 5, cleanup phase |
| `workflows/build-rbtv-component/data/admin-restrictions.md` | Mirrored admin restrictions — update together with CLAUDE.md | Any admin restriction changes |
| `agents/ana.md` | Product submenu references BMAD workflow paths — verify after mirror update | Post BMAD mirror update |
| `workflows/doc-compound-learning/workflow.md` | Output folder config to correct | CP 2 tasks |
| `_admin/docs/BMAD-mirror/_bmad/_config/manifest.yaml` | Current BMAD version in mirror (Beta.4) | BMAD mirror update phase |

### Dependency Graph

```
PRD 4 (version declaration) ──→ PRD 3 (compatibility check)
                                    │
                                    ▼
                              Unified installer
                              (absorbs version check)
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
  CP 2 (output paths)        PRD 5 (path vars)          PRD 6 (frontmatter)
  [shared function]           [shared function]          [independent]
        │                           │
        └──────────┬────────────────┘
                   ▼
         Sync mode implementation
         (uses shared functions)
                   │
                   ▼
         Workspace repo setup
         (bootstrap files ready)
                   │
                   ▼
         _mobile/ cleanup
         (delete/move/rewrite)
```

**Critical path:** PRD 4 → PRD 3 → Unified installer → Sync mode → Workspace repo → Cleanup

**Parallelizable:** CP 2, PRD 5, PRD 6 can run in parallel once the unified installer structure is defined.

### Nanobot Technical Quick-Reference

**Bootstrap files** (loaded into system prompt on every call):
`AGENTS.md`, `SOUL.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md`

**Native capabilities (v0.1.4+):**
Prompt caching (native Feb 18, 2026), Slack Socket Mode, allowlist via `config.json`, MCP support (Feb 14, 2026), workspace sandboxing, memory consolidation.

**VPS infrastructure:**
- Binary: `/usr/local/bin/nanobot`
- Config: `/srv/nanobot/.nanobot/config.json`
- Service: `/etc/systemd/system/nanobot-gateway.service`
- Secrets: `/etc/robotville/nanobot-gateway.env`
- Netlify site: `86ed1ff3-dd59-4428-a426-219518589906` (robotville.ai)

### File Disposition Summary (`_mobile/`)

**DELETE (10 files, ~1,797 lines):** TypeScript harness (4), obsolete source patches (2), shell deploy scripts (3), `HOW-IT-WORKS.md` (1)

**MOVE TO WORKSPACE REPO (7 files):** Bootstrap files (4: AGENTS/SOUL/TOOLS/USER.md), skills (3: web-research, quality-review, doc)

**RELOCATE WITHIN RBTV (9 files):** Config helpers (4), systemd service definition, netlify-placeholder HTML files (4)

**REWRITE (1 file):** `_mobile/README.md` → VPS bootstrap instructions, server access, update flows

**EVALUATE (11 files):** `_docs/` operational docs — merge useful info into README or keep as separate docs

---

### Execution Log P5 (Phase 5 — completed 2026-02-23)

**p5-1:** Updated `TOOLS.md` deploy path (`_docs/netlify-placeholder` → `web/netlify-placeholder`). Updated `SOUL.md` allowlist rule to remove stale harness gate reference (TypeScript gate deleted; allowlist now native nanobot config.json).

**p5-2:** Created `_mobile/_docs/workspace-repo-setup.md` with whitelist .gitignore template, `entry_points.md` template, full VPS bootstrap sequence (9 steps), and update flows for bootstrap files, RBTV module, and BMAD upgrades.

**p5-3/4/5:** Dead code deleted (10 files), config helpers moved to `ops/helpers/`, netlify-placeholder HTML moved to `web/`. Committed in prior session.

**p5-6:** Disposition decisions:
- `deploy-runbook.md`: KEEP + updated (Step 2 → git pull + sync installer; Step 8 → helpers only; removed TypeScript harness checks; removed source patch steps)
- `netlify-site-info.md`: DELETED (site ID already in server-env-template.md and TOOLS.md)
- `robotville-vps-access.md`: KEEP + updated (Automated Pull/Reinstall section rewritten as Update Contract with new git pull + sync installer flow)
- `smoke-checklist.md`: KEEP + updated (script check → helpers check; source patches F) check updated)
- `server-env-template.md`, `slack-troubleshooting-checklist.md`, `hetzner-p1-1-provisioning-guide.md`: KEPT as-is (valid and current)

**p5-7:** Rewrote `_mobile/README.md` — new architecture description (no harness, bootstrap files only), VPS layout diagram, server access quick reference, update flows, directory index.

---

### Execution Log P6 (Phase 6 — completed 2026-02-23)

**p6-refs:** Found 5 broken references outside exclusion zones. Fixed:
- `readme.md`: Removed reference to deleted `_mobile/HOW-IT-WORKS.md`
- `_admin/README.md`: Updated _mobile documentation links (removed HOW-IT-WORKS.md)
- `get_started.md`: Updated admin installer reference (`_admin/install-admin-rbtv.py` → `_config/install-rbtv.py --mode admin`)
- `_mobile/_docs/server-env-template.md`: Removed reference to deleted `netlify-site-info.md`
- `_admin/.cursor/rules/admin-rbtv-bmad-mirror.mdc`: Updated stale admin installer reference to unified installer admin mode

**p6-compound:** No compound-ready learnings in `learnings.md` (template only, no entries recorded during execution). Skipped.
