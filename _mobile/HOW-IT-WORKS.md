# How `_mobile/` Works

`_mobile/` is the RBTV-side integration harness that makes Robotville's business innovation workflows accessible through messaging apps (Slack, with WhatsApp planned) instead of the Cursor IDE.

It does **not** implement a messaging platform. It adapts existing RBTV workflows to the [Nanobot](https://github.com/HKUDS/nanobot) runtime, which owns Slack transport, the AI provider layer, and process lifecycle. `_mobile/` owns only the translation, routing, policy, and state logic that connects RBTV to that runtime.

---

## Architecture at a Glance

```
User (Slack)
  │
  ▼
Nanobot Gateway (Slack Socket Mode, outbound-only)
  │  Owns: transport, AI provider, process lifecycle
  │
  ▼
_mobile/ Harness
  │  Owns: bootstrap, routing, security gate, state adapter
  │
  ▼
Existing RBTV Workflows
  │  Owns: business logic, frameworks, agent personas
  │
  ▼
project-memo.md (canonical workflow state)
```

**Responsibility boundary:** Nanobot handles everything below the wire (Slack sockets, message delivery, AI model calls, process supervision). `_mobile/` handles everything above the wire (what commands mean, who is allowed, where state lives, which agent to activate). Existing RBTV workflows remain untouched — the same agents and frameworks that run in Cursor run here.

---

## Bootstrap System

Nanobot loads four markdown files from its working directory on **every call**. These files are the system prompt — they define how the AI behaves before any user message arrives.

| File | Purpose |
|------|---------|
| `AGENTS.md` | Agent dispatch table. Maps `mentor`, `domcobb`, `doc` commands to agent files and defines the activation protocol. |
| `SOUL.md` | Inviolable behavioral contract. The project-memo read/write cycle, workflow execution rules, communication rules, and context window resilience strategy. |
| `TOOLS.md` | Command-to-workflow routing table. Every menu item, every workflow file path, every skill, and every Nanobot tool — all mapped here. |
| `USER.md` | User profile and interaction preferences. Language, directness, output orientation, session behavior, and project context resolution. |

These files live in `_mobile/` as the source of truth. During VPS deployment, the `vps-sync-install.sh` script copies them into the Nanobot workspace root where the runtime expects them.

### What the Bootstrap Achieves

Without these files, Nanobot uses its own generic defaults. With them, every Nanobot call arrives pre-loaded with:

- Which agents exist and how to activate them
- The project-memo contract (read before every response, update after every framework completion)
- The full command routing table (agent menus, workflow file paths, skill references)
- User preferences and session continuity rules

---

## Inbound Pipeline

When a user sends a message in Slack, the harness processes it through four sequential stages. Each stage can reject the request with a typed error; only a fully passing pipeline reaches workflow execution.

### Stage 1: Bridge (Payload Normalization)

**Module:** `integration/nanobot-gateway-bridge.ts`

The bridge receives the raw Nanobot gateway payload and normalizes it into a structured `NormalizedGatewayPayload`:

- Extracts `userId`, `channelId`, `chatId`, and `text` from the raw object
- Generates a `sessionKey` as `channelId:chatId` — this is the session identity
- Extracts the first token from the message text as the `commandToken`
- Attempts to resolve the command token to a canonical command (`mentor`, `domcobb`, or `doc`)
- Commands are case-insensitive; leading `/` is stripped

**Rejects if:** payload is not an object, missing user identity, missing channel identity, or missing text.

### Stage 2: Allowlist Gate (Security)

**Module:** `security/allowlist-gate.ts`

Before any routing or workflow execution, the gate checks whether the user is authorized:

- Normalizes the allowlist (deduplicates, trims whitespace)
- Checks the normalized `userId` against the allowlist
- **Deny-by-default:** empty or invalid allowlist rejects all users
- **Silent rejection:** unauthorized users receive no response (per PRD FR21)

**Rejects if:** allowlist is empty/invalid, user identity is missing, or user is not allowlisted.

### Stage 3: Router (Command Dispatch)

**Module:** `routing/command-router.ts`

Routes the canonical command to its agent target:

| Command | Agent ID | Nanobot Command | Entrypoint |
|---------|----------|-----------------|------------|
| `mentor` | `mentor` | `/bmad-rbtv-mentor` | `_bmad/rbtv/agents/mentor.md` |
| `domcobb` | `domcobb` | `/bmad-rbtv-domcobb` | `_bmad/rbtv/agents/domcobb.md` |
| `doc` | `ana` | `/bmad-rbtv-doc` | `_bmad/rbtv/agents/ana.md` |

**Rejects if:** the command token does not match any supported command.

### Stage 4: State (Project Memo)

**Module:** `state/project-memo-adapter.ts`

Reads the canonical workflow state from `project-memo.md` before downstream execution begins:

- Parses YAML frontmatter from the memo file
- Validates required fields: `projectName`, `currentMilestone`, `currentFramework`, `stepsCompleted`
- Returns a typed `ProjectMemoState` object
- Supports atomic writes (write to temp file, then rename) to reduce corruption risk during updates

**Rejects if:** memo file not found, missing frontmatter delimiters, missing required fields, or invalid field types.

### Full Pipeline Orchestration

The `bootstrapGatewayHarness()` function in the bridge module chains all four stages:

```
raw payload → normalize → allowlist gate → route command → read memo → ready
```

Each stage returns a discriminated union (`{ ok: true, data } | { ok: false, error }`). The orchestrator short-circuits on the first failure, tagging the error with the failing `stage` for diagnostics.

---

## The Project-Memo Contract

`project-memo.md` is the single canonical source of workflow state. This is the most important architectural decision in the system.

### Why It Exists

Nanobot consolidates (summarizes and trims) conversation history when the context window fills up. This means earlier messages can disappear mid-workflow. The project-memo survives consolidation because it lives on disk and is re-read before every response.

### How It Works

**Before every response:**
1. Agent reads `project-memo.md` frontmatter via `read_file`
2. Extracts: `projectName`, `currentMilestone`, `currentFramework`, `stepsCompleted`, `lastUpdated`
3. Uses these fields — not conversation memory — to determine what to do next

**After every framework completion:**
1. Agent updates the frontmatter via `edit_file`
2. Appends completed step ID to `stepsCompleted`
3. Advances `currentFramework` and/or `currentMilestone` as appropriate
4. Sets `lastUpdated` to today's date
5. Confirms the update to the user

### State Integrity Rules

- Project state lives **only** in project-memo. Never duplicated into `MEMORY.md`.
- Only YAML frontmatter is updated programmatically. Body content changes only through framework workflows.
- The read step is **never skipped**, even if the agent "remembers" the state from earlier in conversation.
- All memo writes go through the shared adapter (`project-memo-adapter.ts`) using atomic write operations.

---

## Agent System

Three agents are available, each with a distinct persona and workflow set:

### Mentor (YC Mentor)
- **Command:** `mentor`
- **Role:** Startup lifecycle guide. Blunt, zero-sycophancy, challenges assumptions.
- **Workflows:** New project setup, continue existing project, milestone/framework progression (6 milestones, 22+ frameworks covering M1 Conception through M6 MVP), party mode (multi-agent discussion).
- **State dependency:** Reads project-memo to detect current position in the milestone/framework pipeline.

### DomCobb (Problem Architect)
- **Command:** `domcobb`
- **Role:** Problem structuring and prompting expert. Socratic, makes users feel smarter.
- **Workflows:** Problem structuring (MECE/Pyramid/Problem Trees), PS Lite (quick mode), problem solving, prompting assistance, add AI knowledge.

### Doc / Ana (Documentation Orchestrator)
- **Command:** `doc`
- **Role:** Knowledge curator and documentation guide. Warm, methodical.
- **Workflows:** Compound documentation, context handoff, product briefs, PRDs, UX design specs.
- **Direct mode shortcuts:** `doc compound`, `doc handoff`, `doc product:brief`, `doc product:prd`, `doc product:ux`.

### Agent Switching

Users switch agents by typing a different command. The harness:
1. Checkpoints the current workflow state in project-memo
2. Drops the previous persona completely (no blending)
3. Loads and activates the new agent file
4. When the user returns to the previous agent, state is intact because project-memo persists

---

## VPS Deployment

### Runtime Model

Single Nanobot instance on a single VPS. All users share the same server and process. Sessions are isolated by `channel:chat_id` — each Slack DM or channel gets its own conversation history and project state.

### Service Management

**Module:** `ops/systemd/nanobot-gateway.service`

A systemd unit that:
- Runs `nanobot gateway` as a dedicated `nanobot` user
- Loads secrets from `/etc/robotville/nanobot-gateway.env` (chmod 600, not in git)
- Auto-restarts on failure (`Restart=always`, `RestartSec=15`) — this is FR25
- Rate-limits restarts (5 within 300 seconds) to avoid crash loops
- Applies security hardening: `NoNewPrivileges`, `PrivateTmp`, `ProtectHome`, `ProtectKernelTunables`
- Logs to journal under `nanobot-gateway` identifier

### Deployment Script

**Module:** `ops/scripts/vps-sync-install.sh`

The main deployment automation. Runs idempotently on every `git pull`:

1. **Restore mirror if needed** — re-enables full checkout if sparse-checkout hid the BMAD mirror
2. **Sync BMAD mirror** — `rsync` copies `_admin/docs/BMAD-mirror/_bmad/` into the workspace `_bmad/` (excluding `rbtv/` which is already present as the repo itself)
3. **Run RBTV installer** — executes `_config/install-rbtv.py` to set up RBTV configuration
4. **Deploy bootstrap files** — copies `AGENTS.md`, `SOUL.md`, `TOOLS.md`, `USER.md` from `_mobile/` to the workspace root where Nanobot reads them
5. **Deploy skills** — `rsync --delete` syncs `_mobile/skills/` into `workspace/skills/` (Nanobot auto-discovers skills from `skills/{name}/SKILL.md`)
6. **Hide mirror** — re-applies sparse-checkout to keep the large BMAD mirror out of the working tree

### Git Hooks

**Module:** `ops/scripts/vps-install-git-hooks.sh`

Installs a `post-merge` hook that auto-triggers `vps-sync-install.sh` after every `git pull`, so pulling new code automatically redeploys bootstrap files and skills.

### Ops Patches

**Module:** `ops/patches/`

Small Python scripts for VPS administration:
- `add-allowlist-user.py` — adds Slack user IDs to the Nanobot allowlist config
- `fix-nanobot-workspace.py` — sets the Nanobot workspace path
- `update-nanobot-model.py` — updates the configured AI model

---

## Security Model

- **Access control:** Slack user ID allowlist, checked before routing. Deny-by-default.
- **Silent rejection:** Unauthorized users get no response — the system pretends not to exist.
- **Secrets:** Environment variables only, restricted file permissions (`chmod 600`), no secrets in git.
- **Network posture:** Slack Socket Mode is outbound-only WebSocket. No inbound ports except SSH (IP-restricted). Port scanners find nothing.
- **VPS hardening:** Systemd service runs with restricted privileges, private temp, protected home.

---

## Skills (Nanobot-Compatible)

Three skills are deployed to the Nanobot workspace for on-demand loading:

| Skill | Path | Purpose |
|-------|------|---------|
| Web Research | `skills/web-research/SKILL.md` | Rigorous research with source evaluation and citation standards |
| Quality Review | `skills/quality-review/SKILL.md` | Evaluates deliverables against quality criteria |
| Doc | `skills/doc/SKILL.md` | Documentation generation workflows |

Skills are loaded by Nanobot when relevant to the current task. Each `SKILL.md` points to its activation file (an RBTV task or agent).

---

## Response Envelope Convention

All internal results use a discriminated union pattern:

```typescript
// Success
{ ok: true, data: T, meta?: { ... } }

// Failure
{ ok: false, error: { code: string, message: string, retryable: boolean }, meta?: { ... } }
```

Success and error payloads are never mixed. Error codes are typed per module (`BridgeErrorCode`, `AllowlistErrorCode`, `RouterErrorCode`, `MemoErrorCode`) and composed into a union at the orchestration level.

---

## File Organization Summary

```
_mobile/
├── README.md                       # Harness boundary definition and scope rules
├── HOW-IT-WORKS.md                 # This document
├── AGENTS.md                       # Bootstrap: agent dispatch table
├── SOUL.md                         # Bootstrap: behavioral contract
├── TOOLS.md                        # Bootstrap: command routing table
├── USER.md                         # Bootstrap: user preferences and context
├── integration/
│   └── nanobot-gateway-bridge.ts   # Payload normalization + pipeline orchestration
├── security/
│   └── allowlist-gate.ts           # Pre-routing access control
├── routing/
│   └── command-router.ts           # Command → agent target mapping
├── state/
│   └── project-memo-adapter.ts     # Read/write/validate canonical workflow state
├── skills/
│   ├── web-research/SKILL.md       # Nanobot skill: web research
│   ├── quality-review/SKILL.md     # Nanobot skill: quality review
│   └── doc/SKILL.md                # Nanobot skill: documentation
└── ops/
    ├── systemd/
    │   └── nanobot-gateway.service  # FR25: auto-restart service unit
    ├── scripts/
    │   ├── vps-sync-install.sh     # Main deployment automation
    │   ├── vps-install-git-hooks.sh # Post-merge hook installer
    │   └── vps-pull-rbtv.sh        # Pull + sync trigger
    └── patches/
        ├── add-allowlist-user.py   # Add user to allowlist
        ├── fix-nanobot-workspace.py # Set workspace path
        └── update-nanobot-model.py # Update AI model config
```

---

## Key Design Decisions

1. **Brownfield extension, not greenfield scaffold.** `_mobile/` adapts existing RBTV workflows to Nanobot. It does not re-implement them or fork them.

2. **Non-duplication rule.** If Nanobot already handles a capability (transport, sockets, AI providers, process lifecycle), `_mobile/` must not implement it again.

3. **project-memo as single state authority.** No parallel state stores. No duplication into conversational memory. All workflow position is in one file per project.

4. **File-based persistence.** No database for the prototype. Project memos, framework outputs, and Nanobot memory files are all filesystem artifacts.

5. **Messaging is a feature of RBTV, not a fork.** One codebase, two delivery channels. The `_mobile/` adapter layer makes the same workflows accessible through Slack that already work in Cursor.
