---
type: structured-problem
status: complete
stepsCompleted: [step-01-init, step-02-discover, step-03-structure, step-04-deliver]
created: 2026-02-22
completed: 2026-02-22
problemType: solution
---

# Problem Structuring: Nanobot Standard Architecture + RBTV Batch Changes

## Refined Problem Statement

Henri needs to simplify the nanobot/RBTV integration from a custom adapter architecture to standard nanobot workspace patterns, while simultaneously executing 5 independent RBTV improvements that share touchpoints with the restructuring, in order to reduce maintenance overhead, enable GitHub-based workspace review, and eliminate upgrade friction — constrained by the requirement to never alter nanobot's native architecture, preserve the robotville.ai deploy capability, and produce a document comprehensive enough to build an execution plan without revisiting decisions.

---

## Problem Tree

```
How can we simplify nanobot/RBTV integration to standard architecture
while executing 5 interconnected RBTV improvements?
│
├── 1. Can we establish a standard nanobot workspace? [ARCHITECTURE]
│   ├── 1.1 What is the workspace GitHub repo structure?
│   │   ├── Whitelist .gitignore tracking only bootstrap files
│   │   ├── entry_points.md maintained manually (no manifest/generation)
│   │   └── skills/ tracked when ready (content deferred)
│   ├── 1.2 What is the VPS bootstrap sequence?
│   │   ├── Clone repo → install nanobot → install BMAD → clone RBTV → sync
│   │   └── One-time setup; updates via git pull
│   └── 1.3 How do update flows work?
│       ├── Bootstrap changes: push GitHub → pull VPS → restart nanobot
│       ├── RBTV changes: git pull _bmad/rbtv/ → re-run sync
│       └── BMAD updates: reinstall CLI → re-run sync
│
├── 2. Can we unify the installer scripts? [TOOLING]
│   ├── 2.1 What are the 3 modes?
│   │   ├── IDE mode: full .cursor/.claude setup (current install-rbtv.py)
│   │   ├── Admin mode: standalone dev setup (current install-admin-rbtv.py)
│   │   └── Sync mode: BMAD config patching only (no IDE artifacts)
│   ├── 2.2 What shared functions exist across modes?
│   │   ├── BMAD config updates (output paths, help catalog)
│   │   ├── Version/compatibility checking (from PRDs 3 & 4)
│   │   └── Path variable resolution (from PRD 5)
│   └── 2.3 What mode-specific functions exist?
│       ├── IDE: copy .cursor config, merge MCP, replicate commands, .vscode, .cursorignore
│       ├── Admin: path substitution, reinforcement append, .gitignore, config prompts
│       └── Sync: nothing beyond shared functions
│
├── 3. Can we clean up _mobile/ and dead code? [CLEANUP]
│   ├── 3.1 What gets deleted?
│   │   ├── TypeScript harness (4 files, ~1,024 lines — dead code)
│   │   ├── Obsolete source patches (2 files — nanobot native now)
│   │   ├── Shell deploy scripts (3 files — replaced by sync mode + git pull)
│   │   └── HOW-IT-WORKS.md (documents the old architecture)
│   ├── 3.2 What gets relocated?
│   │   ├── Bootstrap files (AGENTS/SOUL/TOOLS/USER.md) → workspace GitHub repo
│   │   ├── Website HTML files (4 files) → surviving RBTV path
│   │   ├── Config helper scripts (4 files) → surviving RBTV path
│   │   └── Systemd service definition → surviving RBTV path
│   └── 3.3 What gets rewritten?
│       ├── _mobile/README.md → install instructions, server access info, IP
│       └── Operational docs → evaluate: merge into README or keep separately
│
└── 4. Can we execute the 5 RBTV improvements? [STANDARDS & GOVERNANCE]
    ├── 4.1 PRD: BMAD version declaration (foundation — do first)
    │   ├── Add bmad_target_version/bmad_min_version to config.yaml
    │   ├── Create MIRROR-VERSION.md in BMAD mirror folder
    │   └── Create CHANGELOG.md at RBTV root
    ├── 4.2 PRD: BMAD compatibility check (depends on 4.1)
    │   ├── Create bmad-compat.yaml manifest
    │   ├── Create tasks/check-bmad-compat.xml
    │   └── Add installer pre-flight version check (warn, not block)
    ├── 4.3 CP: Output folder standardization
    │   ├── All installer modes apply same output-path normalization
    │   └── Compound workflow output routing correction
    ├── 4.4 PRD: Reduce path resolution hops
    │   ├── Add paths section to config.yaml ({bmad_core}, {bmad_bmm}, etc.)
    │   ├── Migrate ~60 cross-module references to new variables
    │   └── Simplify/remove resolution table from CLAUDE.md and admin rule
    └── 4.5 PRD: Standardize config frontmatter
        ├── Mandate frontmatter config declaration pattern
        ├── Audit and migrate ~10 workflows
        └── Update component patterns documentation
```

## MECE Validation

| Level | ME Test | CE Test | Status |
|-------|---------|---------|--------|
| Layer 2 (4 categories) | Architecture / Tooling / Cleanup / Standards — no overlaps | All 6 changes covered; deploy preservation across 1+3 | Pass |
| Layer 3 under Architecture | Repo structure / Bootstrap sequence / Update flows — distinct lifecycle phases | Initial setup + updates + structure definition | Pass |
| Layer 3 under Tooling | Modes / Shared functions / Mode-specific — no overlap | All installer concerns covered | Pass |
| Layer 3 under Cleanup | Deleted / Relocated / Rewritten — mutually exclusive dispositions | Every `_mobile/` file accounted for | Pass |
| Layer 3 under Standards | 5 PRDs with explicit dependencies (4.1→4.2) | All 5 batch PRDs listed | Pass |

## Priority Branches

1. **Architecture (Branch 1):** Enabling decision — workspace structure determines what the installer does, what gets cleaned up, and where things go.
2. **Tooling (Branch 2):** Highest-complexity implementation — absorbs 3 scripts, adds PRD functionality, handles 3 modes.
3. **Standards (Branch 4):** Contains the dependency chain (4.1→4.2) and migration-heavy work (4.4: ~60 files).

---

## Architectural Decisions

Every decision made during problem structuring, captured for plan creation without rework.

### Workspace Architecture

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Workspace repo | Private GitHub repo = nanobot workspace folder | Enables GitHub review, version-controlled bootstrap files |
| `.gitignore` strategy | Whitelist (ignore everything, un-ignore bootstrap files only) | BMAD, RBTV, outputs, memory all installed/generated — only bootstrap files are authored |
| Bootstrap flow | Create GitHub repo with bootstrap files → clone to VPS workspace → install nanobot → install BMAD → clone RBTV → run sync | Nanobot is born with correct bootstrap files already present |
| Entry points | Manually maintained `entry_points.md` in workspace repo | Simpler than manifest-driven generation; Henri edits locally, pushes to GitHub |
| Nanobot architecture | NEVER altered — bootstrap files live where nanobot expects them | RBTV adapts TO nanobot, never the reverse |

### Tooling

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Installer unification | One script (or micro-service scripts) with 3 modes: IDE, admin, nanobot-sync | Reduces maintenance surface; shared functions, mode-specific behavior |
| Sync script scope | Patches BMAD configs for RBTV only. Does NOT generate entry_points. Does NOT create IDE config. | Minimal scope — bootstrap files and entry_points are in the workspace repo |
| Shared functions | BMAD config updates + version checking + path resolution | These apply to all 3 modes |

### Cleanup

| Decision | Choice | Rationale |
|----------|--------|-----------|
| `_mobile/` survival | Simplify aggressively, keep as minimal folder | README with server info; relocated files go elsewhere |
| TypeScript harness | Delete entirely | Dead code — never wired into runtime |
| Source patches | Delete both | Prompt caching native since Feb 18, 2026; retries via env var |
| Shell scripts | Delete all 3 | Replaced by unified installer sync mode + git pull |
| Config helpers | Keep, relocate | Still useful for VPS admin |
| Website files | Relocate within RBTV | 4 HTML files needed for deploy; update path in TOOLS.md |
| Bootstrap files | Move to workspace GitHub repo | Already standard nanobot files |
| Operational docs | Evaluate; merge useful info into README | Server access info critical; others may be redundant |

### Security & State

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Allowlist | Native nanobot `config.json` (`channels.slack.dm.allow_from`) | Replaces dead TypeScript `allowlist-gate.ts` |
| Project-memo contract | `SOUL.md` behavioral instruction | Simple enough for prompt-based enforcement; no code needed |
| Output paths | `projects/{project-name}/` via SOUL.md + BMAD config | Enforced by SOUL.md instruction and config patching by sync |

### PRD Interactions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PRD execution scope | All 5 are independently valuable for RBTV, batched because they share touchpoints | Not nanobot-specific changes — they impact Cursor IDE and all RBTV contexts equally |
| PRD 4 → PRD 3 dependency | Version declaration must be implemented before compatibility check | Compatibility check consumes version fields |
| Skills exposure | Deferred to implementation | Decide what gets exposed when editing entry_points.md |

---

## Nanobot Technical Reference

Facts established during problem structuring that plan execution will need.

### Nanobot Bootstrap Files (from `context.py`)

```python
BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
```

All loaded into system prompt on every call. Empty by default — user fills them.

Additional workspace files (auto-managed by nanobot):
- `memory/MEMORY.md` — Long-term facts, always in system prompt
- `memory/HISTORY.md` — Append-only event log, grep-searchable
- `memory/YYYY-MM-DD.md` — Daily notes

### Nanobot Native Capabilities (v0.1.4+, Feb 2026)

| Capability | Status | Notes |
|------------|--------|-------|
| Anthropic prompt caching | Native since Feb 18, 2026 | Source patch `add-litellm-prompt-caching.py` is obsolete |
| Slack Socket Mode | Native | Outbound-only WebSocket, no inbound ports |
| Allowlist | Native via `config.json` | `channels.slack.dm.allow_from` |
| MCP support | Native since Feb 14, 2026 | Config compatible with Cursor format |
| Workspace sandboxing | Native | `tools.restrictToWorkspace: true` |
| Memory consolidation | Native | Auto-trims when context window fills |

### Current VPS Infrastructure

| Component | Location | Status after restructuring |
|-----------|----------|---------------------------|
| Nanobot binary | `/usr/local/bin/nanobot` | Unchanged |
| Nanobot config | `/srv/nanobot/.nanobot/config.json` | Unchanged (workspace path already configured) |
| Systemd service | `/etc/systemd/system/nanobot-gateway.service` | Source definition relocates within RBTV |
| Secrets (env file) | `/etc/robotville/nanobot-gateway.env` | Unchanged |
| Netlify CLI | Installed for `nanobot` user | Unchanged |
| Netlify site | `86ed1ff3-dd59-4428-a426-219518589906` (robotville.ai) | Unchanged |

### Workspace Layout After Restructuring

```
workspace/ (= private GitHub repo = BMAD project root)
├── .gitignore              ← Whitelist: track only bootstrap files
├── AGENTS.md               ← RBTV agent routing (from current _mobile/)
├── SOUL.md                 ← RBTV behavioral rules (from current _mobile/)
├── TOOLS.md                ← RBTV command routing + deploy commands (from current _mobile/)
├── USER.md                 ← User preferences (from current _mobile/)
├── IDENTITY.md             ← Optional custom identity
├── entry_points.md         ← Manually maintained RBTV entry points
├── skills/                 ← Nanobot skills (content deferred)
│   └── {name}/SKILL.md
│
│   ── Below this line: .gitignored ──
│
├── memory/                 ← Nanobot auto-managed
│   ├── MEMORY.md
│   └── HISTORY.md
├── .cursor/                ← Created by BMAD installer (irrelevant on VPS)
├── .claude/                ← Created by BMAD installer (irrelevant on VPS)
├── _bmad/                  ← BMAD modules (installed via CLI)
│   ├── _config/
│   ├── core/
│   ├── bmm/
│   ├── bmb/
│   ├── cis/
│   ├── tea/
│   └── rbtv/               ← RBTV repo (git clone)
│       ├── agents/
│       ├── workflows/
│       ├── tasks/
│       ├── _config/
│       │   └── install-rbtv.py  ← Unified installer (3 modes)
│       ├── _mobile/             ← Simplified: README + relocated files
│       └── _admin/
└── projects/            ← Project outputs
    └── {project-name}/
```

### Workspace Repo `.gitignore`

```gitignore
# Ignore everything by default
*

# Track nanobot bootstrap files
!.gitignore
!AGENTS.md
!SOUL.md
!TOOLS.md
!USER.md
!IDENTITY.md
!entry_points.md
!skills/
!skills/**
```

---

## File Disposition Map

Every file in `_mobile/` with its disposition.

### DELETE

| File | Lines | Reason |
|------|-------|--------|
| `integration/nanobot-gateway-bridge.ts` | 324 | Dead code — never wired into runtime |
| `routing/command-router.ts` | 104 | Dead code |
| `security/allowlist-gate.ts` | 123 | Dead code; allowlist is native nanobot config |
| `state/project-memo-adapter.ts` | 473 | Dead code; replaced by SOUL.md instruction |
| `ops/patches/add-litellm-prompt-caching.py` | 84 | Obsolete — nanobot native since Feb 18, 2026 |
| `ops/patches/add-litellm-retries.py` | 85 | Replaceable via env var `LITELLM_NUM_RETRIES=3` |
| `ops/scripts/vps-sync-install.sh` | 152 | Replaced by unified installer sync mode |
| `ops/scripts/vps-install-git-hooks.sh` | 36 | Replaced by simpler git pull workflow |
| `ops/scripts/vps-pull-rbtv.sh` | 40 | Replaced by direct git pull + sync |
| `HOW-IT-WORKS.md` | 376 | Documents the old architecture being replaced |

**Total deleted: ~1,797 lines across 10 files**

### MOVE TO WORKSPACE GITHUB REPO

| File | Lines | Notes |
|------|-------|-------|
| `AGENTS.md` | 30 | Standard nanobot bootstrap file |
| `SOUL.md` | 117 | Standard nanobot bootstrap file; may need minor updates for new paths |
| `TOOLS.md` | 82 | Standard nanobot bootstrap file; update website source path |
| `USER.md` | 40 | Standard nanobot bootstrap file |
| `skills/web-research/SKILL.md` | 42 | Nanobot skill (exposure decision deferred) |
| `skills/quality-review/SKILL.md` | 33 | Nanobot skill (exposure decision deferred) |
| `skills/doc/SKILL.md` | 24 | Nanobot skill (exposure decision deferred) |

### RELOCATE WITHIN RBTV

| File | Lines | Destination TBD |
|------|-------|-----------------|
| `ops/patches/add-allowlist-user.py` | 34 | Config helper — keep under `_mobile/` or new path |
| `ops/patches/fix-nanobot-workspace.py` | 31 | Config helper |
| `ops/patches/update-nanobot-model.py` | 21 | Config helper |
| `ops/patches/update-nanobot-memory-window.py` | 21 | Config helper |
| `ops/systemd/nanobot-gateway.service` | — | Infrastructure definition |
| `_docs/netlify-placeholder/` (4 HTML files) | — | Website source for robotville.ai deploy |

### REWRITE

| File | Action |
|------|--------|
| `README.md` | Rewrite: VPS bootstrap instructions, server access (IP, SSH), update flows, nanobot config reference |

### EVALUATE (merge into README or keep)

| File | Content |
|------|---------|
| `_docs/robotville-vps-access.md` | Server IP, SSH endpoint, access policy |
| `_docs/deploy-runbook.md` | End-to-end setup and recovery |
| `_docs/smoke-checklist.md` | Routing, allowlist, restart tests |
| `_docs/server-env-template.md` | Slack/LLM credential handling |
| `_docs/deployment-smoke-report.md` | Validation evidence |
| `_docs/netlify-site-info.md` | Netlify site ID and link commands |
| `_docs/robotville-netlify-walkthrough.md` | Hosting setup walkthrough |
| `_docs/robotville-hosting-decision.md` | Netlify vs GitHub Pages decision |
| `_docs/robotville-ai-provisioning.md` | Domain provisioning |
| `_docs/hetzner-p1-1-provisioning-guide.md` | VPS provisioning |
| `_docs/slack-troubleshooting-checklist.md` | Slack connection issues |

---

## PRD Reference Summaries

Key details from each PRD needed during plan creation.

### PRD 4: BMAD Version Declaration (`prd-config-bmad-version-declaration.md`)

- **Priority:** Medium | **Dependency:** None (foundation for PRD 3)
- **Creates:** `bmad_target_version` + `bmad_min_version` in `_config/config.yaml`, `MIRROR-VERSION.md`, `CHANGELOG.md`
- **Prerequisite action:** Update BMAD mirror from Beta.4 to Beta.8
- **Risk:** Beta.7 workflow splitting may have broken RBTV's product submenu references in `agents/ana.md`

### PRD 3: BMAD Compatibility Check (`prd-config-bmad-compatibility-check.md`)

- **Priority:** Medium | **Dependency:** PRD 4 must be done first
- **Creates:** `bmad-compat.yaml` (touchpoints manifest), `tasks/check-bmad-compat.xml`, installer pre-flight check
- **Key constraint:** Installer check warns, does not hard-fail (beta software)
- **Scope:** 3 new files, 1 modified file

### CP 2: Output Folder Standardization (`cp-install-scripts-standardize-bmad-output-folder.md`)

- **Priority:** High | **Dependency:** None
- **Modifies:** Both installer scripts (now unified), compound workflow output config
- **Target:** `projects/{project-name}/` as canonical base pattern
- **Key file:** `workflows/doc-compound-learning/workflow.md` (output folder correction)

### PRD 5: Reduce Path Resolution Hops (`prd-reduce-path-resolution-hops.md`)

- **Priority:** Medium | **Dependency:** None
- **Creates:** `paths:` section in `config.yaml` with `{bmad_core}`, `{bmad_bmm}`, `{bmad_rbtv}`, `{bmad_output}`
- **Migration scope:** ~60 files referencing cross-module paths
- **Risk:** Labor-intensive migration; backwards compatibility needed during transition

### PRD 6: Standardize Config Frontmatter (`prd-standardize-main-config-frontmatter.md`)

- **Priority:** Medium | **Dependency:** None
- **Scope:** Audit 38 workflows, migrate ~10 to frontmatter pattern
- **Key file:** `_config/.cursor/rules/bmad-rbtv-component-patterns.mdc` (mandate frontmatter approach)

---

## Dependency Graph

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

---

## Update Flows (Post-Implementation)

| What changed | Action | Frequency |
|-------------|--------|-----------|
| Bootstrap files or entry_points.md | Edit locally → push GitHub → `git pull` on VPS → `systemctl --user restart nanobot-gateway` | As needed |
| RBTV code (agents, workflows) | `git pull` in `_bmad/rbtv/` → re-run sync mode | On RBTV releases |
| BMAD version | Reinstall BMAD via CLI → re-run sync mode | On BMAD releases (after compatibility check) |
| Website content | Edit in RBTV repo or staging → `deploy site` via Slack | User-commanded only |
| Nanobot version | `pip install --upgrade nanobot-ai` → restart gateway | On nanobot releases (no more patches to reapply) |

---

## Recommended Next Steps

| # | Action | Purpose | Priority |
|---|--------|---------|----------|
| 1 | Create execution plan using this document | Sequence the 4 branches into phased, committable work | High |
| 2 | Update BMAD mirror from Beta.4 to Beta.8 | Prerequisite for PRD 4 (version declaration) and risk discovery for Beta.7 workflow splitting | High |
| 3 | Verify nanobot v0.1.4+ is installed on VPS | Confirms prompt caching is native, validates source patch deletion | Medium |
