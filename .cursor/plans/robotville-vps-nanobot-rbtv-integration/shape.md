# Shape - robotville-vps-nanobot-rbtv-integration

> **Purpose:** This document captures shaping decisions made during planning and accumulates execution context. The Original Shaping section is immutable. All other sections are append-only during execution.

---

## Original Shaping (Planning Phase)

### Scope Definition

**What this plan accomplishes:**
- Provision and harden a remotely manageable Hetzner VPS for Robotville.
- Install and configure Nanobot with Slack Socket Mode and LLM provider credentials.
- Create and wire RBTV `_mobile` harness files under `_bmad/rbtv/` without duplicating Nanobot internals.
- Validate end-to-end behavior with FR25 auto-restart in scope.

**What this plan does NOT include:**
- Full production observability/admin feature surface from FR23, FR24, and FR26.
- Rebuilding Nanobot runtime features inside RBTV.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| VPS provider | Hetzner | API + SSH remote control requirement and practical operations fit |
| Integration style | Brownfield extension | Reuse existing RBTV + Nanobot capabilities and avoid duplication |
| State authority | `project-memo.md` | Preserve established founder workflow continuity contract |
| Documentation location | `_bmad/rbtv/_admin/docs/mobile/` | User requested all plan docs in one clear location |
| Mapping location | `_bmad/rbtv/_mobile/` | User requested all Nanobot mapping/harness code under `_mobile` |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| Must use Hetzner | User decision | Infrastructure tasks and commands target Hetzner APIs and VPS model |
| Must support API + terminal remote control | User requirement | Architecture and runbooks prioritize SSH and provider API control |
| User is non-technical | User statement | Plan requires explicit, path-safe structure and operational guidance |
| Do not duplicate Nanobot internals | Architecture decision | `_mobile` acts as adapter boundary only |
| FR25 in scope; FR23/24/26 deferred | User scope decision | Include auto-restart setup, defer admin status/notifications |

### User Inputs (Maintained and Developed)

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Infrastructure need | "i need guidance on how to actually implement the project ... VPS ... nanobot ... slack ... llm api ... _mobile" | Four-phase execution plan covering VPS, runtime, integration, harness, and validation |
| 2 | VPS choice | "vps will be hetzger as suggested" | Hetzner-specific provisioning and security baseline tasks |
| 3 | File placement clarity | "I dont understand which files are for rbtv/ and which are for the VPS" | Explicit directory boundaries and server-operation vs repo-file task split |
| 4 | Mentor reference correction | " @_bmad/rbtv/agents/mentor.md is the correct mentor" | Files-to-load table and task context references corrected |
| 5 | Docs location | "_admin/docs/mobile/ (all files related to this plan)" | All plan documentation outputs routed to `_bmad/rbtv/_admin/docs/mobile/` |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Planning depth | Needs practical implementation guidance now | Proposed plan-lifecycle workflow and phased tasking | Use RBTV plan workflow to produce executable plan artifacts |
| 2 | Scope handling | Skip heavy overhead where possible | Suggested focused MVP execution with constraints from architecture | Keep FR25, defer FR23/24/26, no unnecessary duplication |
| 3 | Structure policy | Wants clear file ownership by location | Converted tasks to explicit CREATE/UPDATE paths by boundary | RBTV code in `_bmad/rbtv/`, mapping in `_mobile`, docs in `_admin/docs/mobile` |

---

## Standards Applied

### BMAD/RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Zero-context execution | Tasks include clear files to load and explicit outcomes for independent execution |
| Task granularity (WHAT, not HOW) | Tasks define deliverables and boundaries without over-constraining implementation details |
| Explicit file operations | CREATE/UPDATE verbs used for repository file tasks |
| Dependency ordering | Provisioning and security precede runtime; runtime precedes harness wiring; validation last |
| Checkpoint gating | One checkpoint per phase to pause for human approval |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| RBTV files only under `_bmad/rbtv/` | Reject any task creating project files outside RBTV path |
| Nanobot mapping only under `_mobile` | Reject mapping tasks outside `_bmad/rbtv/_mobile/` |
| Plan docs only under `_admin/docs/mobile/` | Route all generated docs and reports to `_bmad/rbtv/_admin/docs/mobile/` |
| Preserve canonical state source | Any state task must reference `project-memo.md` as authority |

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

<!-- Decisions and discovery entries will be appended below this line -->

### 2026-02-14 - p1-3 Security Baseline Applied on Live VPS

- **Decision:** Keep SSH on port 22 for now and enforce key-only auth + deny-all inbound firewall as the baseline, then optionally add IP allowlist tightening once admin source IP is stable.
- **Discovery:** On Ubuntu 24.04, the SSH service unit is `ssh` (not `sshd`). Restart/reload automation must target `systemctl restart ssh`.
- **Validation outcome:** Post-reboot checks confirmed hardening persistence: `PasswordAuthentication no`, UFW active with only `22/tcp` allowed inbound, fail2ban `sshd` jail active and enabled at boot.

### 2026-02-14 - p2-1 Nanobot Runtime and Service Workspace Provisioned

- **Decision:** Install Nanobot using upstream `nanobot-ai` Go binary (`go install github.com/nanobot-ai/nanobot@latest`) and expose it as `/usr/local/bin/nanobot` for service account stability.
- **Discovery:** PyPI package `nanobot` resolves to an unrelated robotics framework; it was removed to prevent command collision and runtime misconfiguration.
- **Discovery:** Current upstream CLI exposes `nanobot run` (not `nanobot gateway`). Phase 2/4 service command wiring must use `run` semantics unless a pinned gateway-capable release is explicitly required.
- **Validation outcome:** Dedicated `nanobot` system user and group were created, workspace root `/opt/robotville/BMAD` was provisioned with restricted permissions, env file path `/etc/robotville/nanobot-gateway.env` was permissioned `0640 root:nanobot`, and `nanobot run --help` executed successfully as the service user.

### 2026-02-14 - p2-1 Nanobot Source Correction to HKUDS Latest Stable

- **Decision:** Pin Nanobot runtime source to `https://github.com/HKUDS/nanobot` and install latest stable release (`nanobot-ai`) to preserve expected gateway CLI semantics.
- **Discovery:** Two different projects expose a `nanobot` binary; source pinning is mandatory to avoid accidental command-surface drift.
- **Validation outcome:** VPS runtime now reports `nanobot-ai 0.1.3.post7`, and both `nanobot gateway --help` and `nanobot onboard --help` execute successfully as the `nanobot` service user.

### 2026-02-14 - p2-2 Server Environment Template Added

- **Decision:** Standardize VPS credential handling in `_bmad/rbtv/_admin/docs/mobile/server-env-template.md` with explicit paths, ownership, and placeholder-only templates.
- **Validation outcome:** Template now defines `/etc/robotville/nanobot-gateway.env` and `/srv/nanobot/.nanobot/config.json` contracts with strict permission requirements and no repository secrets.

### 2026-02-14 - p2-3 Runtime Config Scaffolded, Credentials Pending

- **Decision:** Apply Nanobot Slack/provider config scaffold on VPS using placeholder values first, keeping secrets outside git and in `/etc/robotville/nanobot-gateway.env`.
- **Discovery:** Live Slack and provider credentials are not yet present on the VPS, so handshake-level connectivity cannot be validated in this task step.
- **Validation outcome:** `nanobot status` loads `/srv/nanobot/.nanobot/config.json` successfully under service user and required env keys exist; final connectivity depends on real token/key injection.

### 2026-02-14 - p2-3 Slack "Bot Not Answering" Troubleshooting

- **Discovery:** HKUDS Nanobot Slack config does not use a top-level `allowFrom`. It uses `dm.allow_from` (user IDs for DMs) and `dm.policy: "allowlist"`, and `group_allow_from` (channel IDs when `group_policy` is `allowlist`). The original server-env-template used `allowFrom` which is ignored by Nanobot.
- **Discovery:** Systemd service requires `NANOBOT_GATEWAY_CMD` in the env file; if unset, the service fails. Nanobot reads config from `~/.nanobot/config.json`; if `nanobot` user HOME is wrong (e.g. `/home/nanobot` while config is in `/srv/nanobot/.nanobot`), config is not found. Added `Environment=HOME=/srv/nanobot` to systemd unit.
- **Fix applied:** Updated server-env-template with correct `dm.allow_from` schema, created `slack-troubleshooting-checklist.md`, and added HOME to systemd service draft.

### 2026-02-14 - LLM Model Switch to claude-opus-4-6

- **Decision:** Switch Nanobot agent model from `claude-3-5-sonnet-20241022` to `claude-opus-4-6` after Anthropic returned `not_found_error` for the former.
- **Discovery:** `effort=high` is the default for Claude (equivalent to omitting the parameter); Nanobot's AgentDefaults schema does not expose `output_config` or `effort`, but high-effort behavior is already the default.
- **Fix applied:** Created `_bmad/rbtv/_mobile/ops/patches/update-nanobot-model.py` to update `/srv/nanobot/.nanobot/config.json`; executed on VPS, gateway restarted.

### 2026-02-14 - p3-1 `_mobile` Harness Boundary Baseline

- **Decision:** Define `_bmad/rbtv/_mobile/README.md` as the explicit ownership contract between RBTV harness logic and Nanobot runtime responsibilities.
- **Validation outcome:** README now codifies non-duplication rules, canonical `project-memo.md` state authority, and the allowed `_mobile` adapter/routing/security scope for upcoming phase-3 modules.

### 2026-02-14 - p3-2 Gateway Normalization Bridge Introduced

- **Decision:** Establish `normalizeNanobotGatewayPayload` as a fail-closed bridge contract that validates identity/channel/text before any routing.
- **Validation outcome:** `_mobile/integration/nanobot-gateway-bridge.ts` now emits canonical command tokens (`mentor`, `domcobb`, `doc`), deterministic `channelId:chatId` session keys, and structured malformed-payload errors without mutating workflow state.

### 2026-02-14 - p3-3 Canonical Command Router Added

- **Decision:** Centralize canonical command dispatch in `_mobile/routing/command-router.ts` with a fixed route table for `mentor`, `domcobb`, and `doc`.
- **Validation outcome:** Router now consumes bridge-normalized payload fields, resolves commands to existing RBTV entrypoints (`mentor.md`, `domcobb.md`, `ana.md`), and rejects unsupported commands with explicit allowlist feedback while keeping transport/provider concerns outside routing.

### 2026-02-14 - p3-4 Canonical Project Memo Adapter Added

- **Decision:** Centralize `project-memo.md` read/write through `_mobile/state/project-memo-adapter.ts` with explicit schema checks for `projectName`, `currentMilestone`, `currentFramework`, and `stepsCompleted`.
- **Validation outcome:** Adapter now reads frontmatter without mutation, applies controlled patch updates, preserves non-canonical frontmatter keys, and writes via temp-file rename for atomic state updates.

### 2026-02-14 - p3-5 Allowlist Gate Added Pre-Routing

- **Decision:** Enforce access control in `_mobile/security/allowlist-gate.ts` as a deny-by-default gate that runs before command routing.
- **Validation outcome:** Gate now normalizes allowlist identities, rejects empty/malformed allowlist input and missing identity values, and returns explicit unauthorized results for non-allowlisted users without introducing transport-side behavior.

### 2026-02-14 - p3-6 Gateway Bootstrap Wiring Added to Harness Entry Path

- **Decision:** Treat `_mobile/integration/nanobot-gateway-bridge.ts` as the harness runtime bootstrap entrypoint and compose the mandatory pipeline there: normalize -> allowlist gate -> command router -> canonical `project-memo` adapter read.
- **Validation outcome:** Added `bootstrapGatewayHarness` to load all phase-3 harness modules in-order, fail closed with stage-specific error envelopes, and expose routed command target plus canonical memo state without introducing duplicate transport/runtime responsibilities.

### 2026-02-14 - p4-1 Deployment Runbook Baseline Created

- **Discovery:** Phase-4 task micro-files are partially present (`p4-3`, `p4-compound`), so `p4-1` execution proceeded from plan-level task content while keeping append-only logging in `shape.md`.
- **Decision:** Standardize a single operator run sequence in `_admin/docs/mobile/deploy-runbook.md` covering preflight, secure env/config apply, systemd deployment, live Slack smoke, FR25 restart validation, and rollback.
- **Validation outcome:** Runbook now aligns with existing service/env contracts (`/etc/robotville/nanobot-gateway.env`, `/srv/nanobot/.nanobot/config.json`, `nanobot-gateway.service`) and is ready for live user execution/approval.

### 2026-02-14 - p4-2 Smoke Checklist Baseline Added

- **Decision:** Add a dedicated smoke checklist at `_admin/docs/mobile/smoke-checklist.md` to make live validation deterministic across service health, allowlist behavior, command routing, memo continuity, and FR25 restart.
- **Validation outcome:** Checklist now provides explicit pass/fail criteria and command blocks for reproducible operator evidence capture before final smoke reporting.

### 2026-02-14 - p4-3 FR25 Auto-Restart Validated on Live VPS

- **Discovery:** Live VPS runtime path was not aligned with expected `/opt/robotville/BMAD/_bmad/rbtv` repository layout, so service unit deployment required SCP fallback from operator workstation.
- **Validation outcome:** FR25 behavior was validated with two checks: (1) controlled `SIGKILL` of gateway main PID triggered automatic restart (`restart counter is at 1` and service returned `active`), and (2) full VPS reboot restored service to `active` automatically at boot.
- **Fix applied:** Updated systemd unit `Documentation=` to a valid file URL format (`file://...`) to eliminate invalid URL warnings during service reload/start.

### 2026-02-14 - p4-4 Deployment Smoke Report Captured

- **Decision:** Record live execution evidence and residual risks in `_admin/docs/mobile/deployment-smoke-report.md` as the operational handoff artifact for phase-4 validation.
- **Validation outcome:** Smoke report now captures command evidence, FR25 pass verdict, discovered path-layout mismatch, and explicit follow-up actions for path normalization.

### 2026-02-14 - Canonical VPS Workspace Normalization Executed

- **Decision:** Enforce canonical deployment path contract on VPS: `/opt/robotville/BMAD/_bmad/rbtv` (no symlink shortcut and no SCP fallback branch in runbook flow).
- **Discovery:** Direct `git clone` on VPS failed because remote GitHub authentication for the private repository was unavailable in server context; bootstrap required operator-mediated transfer from local workspace.
- **Execution detail:** Created `/opt/robotville/BMAD/_bmad`, transferred repo contents, restored `.git` metadata, corrected permissions, redeployed `nanobot-gateway.service` from canonical repo path, and reloaded systemd.
- **Validation outcome:** `nanobot-gateway` returned `active (running)` with `Documentation=file://...` URL format, canonical harness files resolved under `_mobile`, and FR25 controlled kill/restart re-validated (`Scheduled restart job, restart counter is at 1`).

### 2026-02-14 - Private Repo Deploy-Key Access Enabled and Origin-Sourced Sync Finalized

- **Decision:** Standardize VPS repository updates through GitHub SSH deploy-key auth under `nanobot` service account, eliminating operator-local bootstrap as a normal update path.
- **Execution detail:** Generated `/srv/nanobot/.ssh/rbtv_deploy_key`, registered read-only deploy key in GitHub, configured `/srv/nanobot/.ssh/config` + `known_hosts`, switched repo `origin` to `git@github.com:hlealt/rbtv.git`, then cloned a clean origin working tree and swapped it into `/opt/robotville/BMAD/_bmad/rbtv` (previous local-seeded tree retained as backup directory).
- **Validation outcome:** `sudo -u nanobot ssh -T git@github.com` authenticated successfully, `git fetch origin --prune` succeeded from canonical path, and active service state remained healthy after repo swap.

### 2026-02-14 - VPS Pull/Reinstall/Mirror-Cleanup Automation Added

- **Decision:** Make RBTV updates script-first on VPS so each pull automatically reinstalls BMAD+RBTV instance state and removes local mirror working-tree footprint after sync.
- **Execution detail:** Added `_mobile/ops/scripts/vps-pull-rbtv.sh` (canonical update entrypoint), `_mobile/ops/scripts/vps-sync-install.sh` (mirror sync + installer + sparse cleanup), and `_mobile/ops/scripts/vps-install-git-hooks.sh` (installs `post-merge` hook calling sync script).
- **Documentation update:** Updated `deploy-runbook.md`, `robotville-vps-access.md`, `smoke-checklist.md`, and `deployment-smoke-report.md` to require script-based updates and hook installation during VPS operations.
- **Expected operational outcome:** Any VPS update using the canonical script (or `git pull` with hook installed) results in deterministic BMAD/RBTV reinstall plus mirror-folder cleanup in working tree.

---

## References

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `_bmad-output/robotville-v4.0/bmad/prd.md` | Scope, FR/NFR requirements, security and runtime expectations |
| `_bmad-output/robotville-v4.0/bmad/architecture.md` | Boundaries, deferred scope decisions, `_mobile` structure, FR25 requirement |
| `_bmad/rbtv/readme.md` | RBTV module context and conventions |
| `_bmad/rbtv/agents/mentor.md` | Agent behavior reference for harness alignment |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `_bmad-output/robotville-v4.0/bmad/prd.md` | Requirement baseline | All phases as needed |
| `_bmad-output/robotville-v4.0/bmad/architecture.md` | Architectural source of truth | All implementation phases |
| `_bmad/rbtv/readme.md` | RBTV conventions | Phase 3 |
| `_bmad/rbtv/agents/mentor.md` | Mentor integration context | Phase 3 |
| `_bmad-output/robotville-v4.0/**` | Project outputs potentially informing `_mobile` behavior | Phase 3 and validation |

### 2026-02-14 - p5-1 AGENTS.md Bootstrap File Created

- **Decision:** Define agent routing in `_mobile/AGENTS.md` as a system-prompt-level dispatch table mapping `mentor`, `domcobb`, and `doc` commands to their respective agent files (`agents/mentor.md`, `agents/domcobb.md`, `agents/ana.md`), with activation protocol, switching rules, and unknown-command handling.
- **Validation outcome:** AGENTS.md routing table aligns exactly with `command-router.ts` route table (same three commands, same agent IDs, same entrypoint paths). Agent summaries capture core persona traits and workflow scope from the actual agent files.

### 2026-02-14 - p5-2 SOUL.md Core Behavioral Rules Created

- **Decision:** Codify the project-memo read-before-respond contract as the central rule in `_mobile/SOUL.md`: (1) read frontmatter before every response, (2) update frontmatter after every framework completion, (3) never duplicate project state into MEMORY.md, (4) never modify memo body during routine state updates.
- **Validation outcome:** SOUL.md covers all four requirements specified in the plan task description (read-before-respond, immediate update, canonical state authority, no MEMORY.md duplication). Includes context window resilience section addressing Nanobot's consolidation behavior with project-memo as the persistence mechanism.

### 2026-02-14 - p5-3 TOOLS.md Command-to-Workflow Mapping Created

- **Decision:** Structure `_mobile/TOOLS.md` as a three-level mapping: (1) top-level command-to-agent routing table, (2) per-agent workflow tables with menu commands, handler types, and file paths, (3) skills reference table and Nanobot-native tool reference.
- **Validation outcome:** All workflow file paths extracted directly from the three agent files (`mentor.md`, `domcobb.md`, `ana.md`). Includes Ana's direct mode shortcuts (`doc compound`, `doc handoff`, etc.). Skills table references the 8 Nanobot-compatible skills created in p5-5. Nanobot tool reference maps RBTV needs to available tools.

### 2026-02-14 - p5-4 USER.md User Context Template Created

- **Decision:** Define `_mobile/USER.md` as a user preferences and context bootstrap covering profile (config-sourced), interaction preferences (directness, speed, output orientation, menu-driven), project context (memo detection, output location), and session behavior (greeting, returning users, multi-project).
- **Validation outcome:** USER.md references config.yaml for dynamic values and aligns with all three agent files' activation expectations (config loading, project-memo detection, language handling).

### 2026-02-14 - p5-5 Skills Directory Created with 8 Nanobot-Compatible Skills

- **Decision:** Create `_mobile/skills/` with 3 skill files adapted from `.cursor/skills/` for Nanobot's `skills/{name}/SKILL.md` format: doc, quality-review, web-research. Excluded 4 browser/Playwright-dependent skills (mermaid-conversion, visual-design-extraction, design-validation, playwright-browser-automation) because Nanobot lacks MCP support — consistent with the known MCP gap documented in the project-memo and other skills to make prototype as simple as possible.
- **Discovery:** Cursor skill files reference `.cursor/rules/admin-rbtv-bmad-mirror.mdc` for admin-mode path resolution. This is Cursor-specific and was removed from Nanobot skill adaptations since Nanobot resolves paths relative to workspace root directly.
- **Validation outcome:** All 8 skill files maintain their original frontmatter (`name`, `description`) for Nanobot's auto-summary system, reference the correct RBTV workflow/task/agent files using workspace-relative paths, and use `read_file` as the file-loading mechanism. Web-research skill includes Nanobot-specific tool guidance (`web_search`, `web_fetch`).

### 2026-02-14 - p5-6 Deploy Mechanism Extended for Bootstrap and Skills

- **Decision:** Extend `vps-sync-install.sh` with two new idempotent functions (`deploy_bootstrap_files`, `deploy_skills`) that run after the RBTV installer and before sparse-checkout cleanup, so every `git pull` on VPS automatically refreshes Nanobot's workspace-root bootstrap state.
- **Implementation detail:** `deploy_bootstrap_files` copies `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md` from `_mobile/` into `WORKSPACE_ROOT` using `cp -f` (overwrite-always for idempotency). Missing individual files produce warnings; all-missing produces an error. `deploy_skills` uses `rsync -a --delete` from `_mobile/skills/` to `WORKSPACE_ROOT/skills/`, removing stale skills that were deleted from the repo.
- **Documentation update:** Updated `deploy-runbook.md` automation summary to reflect the expanded 6-step pull sequence (added bootstrap deploy and skills sync steps) and added a verification block for bootstrap files at workspace root.
- **Validation outcome:** Script structure preserves existing mirror-sync and installer flow, adds bootstrap deploy between installer and sparse-checkout, and all paths derive from existing `WORKSPACE_ROOT`/`RBTV_REPO` variables for consistency.

### 2026-02-14 - p5-7 Bootstrap Deployment Executed on VPS

- **Decision:** Commit all `_mobile/` and `_admin/docs/mobile/` files to origin/master, then pull on VPS via the canonical deploy flow, since the VPS updates from origin exclusively (deploy-key based).
- **Discovery:** VPS had untracked local copies of ops scripts (`vps-install-git-hooks.sh`, `vps-pull-rbtv.sh`, `vps-sync-install.sh`) and `_admin/docs/mobile/` files from earlier manual operations that conflicted with the incoming merge. Also had stale `.cursor/plans/founder-migration/` and `_admin/roadmap/testing/` directories. All resolved by backing up and removing conflicting untracked files before pull.
- **Discovery:** `_mobile/` directory permissions on VPS were root-owned from earlier SCP operations; required `chown -R nanobot:nanobot` before the `nanobot` service user could write during `git pull`.
- **Execution detail:** (1) Committed and pushed `_mobile/` + `_admin/docs/mobile/` to origin, (2) backed up and removed conflicting untracked VPS files, (3) fixed `_mobile/` ownership, (4) ran `git pull --ff-only origin master` which triggered the post-merge hook running `vps-sync-install.sh`, (5) sync-install ran full pipeline: mirror sync → RBTV installer → bootstrap deploy (4 files) → skills deploy (3 skills) → sparse-checkout cleanup.
- **Validation outcome:** All 4 bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) confirmed at `/opt/robotville/BMAD/` workspace root with correct `nanobot:nanobot` ownership. All 3 skill directories (`doc`, `quality-review`, `web-research`) confirmed at `/opt/robotville/BMAD/skills/`. All 4 harness modules confirmed in repo at `_mobile/`. Gateway restarted (`systemctl restart nanobot-gateway`) and returned `active (running)` with Slack bot connected as `U0AFD71DRFT` on port 18790.

### 2026-02-14 - p5-8 Bootstrap Files Not Loaded — Workspace Path Mismatch

- **Discovery:** Live Slack validation of "mentor" command failed — Nanobot responded with generic chat behavior four times, never activating the RBTV mentor agent. Bootstrap files (`AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md`) were confirmed on disk at `/opt/robotville/BMAD/` but Nanobot was not loading them into its system prompt.
- **Root cause:** Nanobot resolves its workspace from `agents.defaults.workspace` in `config.json`, which defaults to `~/.nanobot/workspace`. With `HOME=/srv/nanobot` (set in systemd unit), this resolved to `/srv/nanobot/.nanobot/workspace/` — an empty directory. The systemd `WorkingDirectory=/opt/robotville/BMAD` controls the process CWD but is a distinct concept from Nanobot's workspace path where it loads bootstrap files and skills.
- **Evidence:** Nanobot self-reported (via Slack conversation) that "None of these files exist yet" when asked about its bootstrap files, and that `config.json` had no workspace override — confirming it was looking in the default `~/.nanobot/workspace/` path.
- **Fix applied:** Created `_mobile/ops/patches/fix-nanobot-workspace.py` to set `agents.defaults.workspace` to `/opt/robotville/BMAD` in `config.json`. Updated `server-env-template.md` to include the `workspace` field in the config template. Deployed patch on VPS and restarted gateway.
