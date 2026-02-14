---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/robotville-v4.0/bmad/prd.md'
workflowType: 'architecture'
project_name: 'BMAD'
user_name: 'Henri'
date: '2026-02-13'
lastStep: 8
status: 'complete'
completedAt: '2026-02-13T20:32:38.9167320-03:00'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
The PRD defines 32 functional requirements across eight capability groups. Architecturally, these imply:
- A command and agent orchestration layer for `mentor`, `domcobb`, and `doc` invocation, active-agent routing, and seamless agent switching.
- A workflow execution layer that supports milestone progression (M1-M6), framework completion tracking, markdown output generation, and browser-dependent operations via Playwright shell execution.
- Preservation and enforcement of the established founder workflow state contract (`project-memo` protocol) across Slack/Nanobot/mobile adapter boundaries.
- Session handling keyed by `channel:chat_id`, with continuity across restarts and multi-user shared-channel interaction behavior.
- Administrative operations for allowlist management, runtime health status, startup/restart notifications, and update workflow support.
- File/output behavior preserving existing RBTV structure, with deferred user-facing file listing/content delivery capabilities.

**Non-Functional Requirements:**
The NFR set (15 requirements) drives several hard architectural constraints:
- Performance: fast acknowledgment and bounded response completion under provider-latency variability.
- Security: secrets only via environment variables, restricted host exposure (SSH only, IP-scoped), allowlist enforcement, and outbound-only Slack socket communication.
- Reliability: automatic crash recovery, restart-safe workflow continuity, and admin notification on lifecycle events.
- Integration resilience: Slack reconnection behavior, explicit provider failure surfacing, and graceful degradation with preserved session state.
- Capacity target: up to 5 concurrent sessions on a single VPS for prototype operation.

**Scale & Complexity:**
This project combines conversational orchestration, deterministic workflow state, external provider integration, and operational reliability controls. Complexity is moderate because scope is intentionally constrained (single VPS, prototype limits), but cross-cutting consistency requirements are strict.

- Primary domain: Messaging-delivered AI workflow platform (backend/integration oriented)
- Complexity level: Medium
- Estimated architectural components: 10-14

### Technical Constraints & Dependencies

- Runtime constrained to one Nanobot instance on one VPS.
- Nanobot distribution is pinned to `https://github.com/HKUDS/nanobot` (latest stable release), to preserve expected gateway/channel command behavior.
- Persistence constrained to filesystem artifacts (`project-memo`, framework outputs, memory/history files), with no database.
- Session model constrained to `channel:chat_id`; known shared-channel contamination risk is accepted for prototype context.
- Integration dependencies: Slack Socket Mode, AI provider abstraction, Playwright shell execution wrapper.
- Operational model depends on watchdog cron for auto-restart and admin-channel observability.
- Update path is manual (`git pull` + config reapply), with install automation deferred.
- Existing RBTV output structure must be preserved.
- Existing founder workflow state behavior defined in `mentor.md` must be treated as a compatibility contract, not reimplemented in parallel.

### Cross-Cutting Concerns Identified

- Workflow-state integrity and idempotent updates to `project-memo`.
- Workflow contract preservation between founder agent rules and mobile adapter/runtime orchestration.
- No duplicate state sources or competing state authorities outside the established `project-memo` protocol.
- Access-control enforcement and unauthorized-user silent handling.
- Reliability and recovery semantics across crashes/restarts.
- Consistent command/agent routing and context continuity across agent switches.
- Error handling and graceful degradation for provider/network failures.
- Operational observability for admin confidence during demo/testing.
- Data/output consistency across generated markdown artifacts.

## Starter Template Evaluation

### Primary Technology Domain

Backend/integration-focused messaging platform with brownfield extension constraints (existing RBTV + founder workflows + Nanobot runtime).

### Starter Options Considered

1) **Greenfield Slack starter (Bolt JS / Socket Mode templates)**
- Pros: modern scaffold, TypeScript DX, clear Slack app bootstrap
- Cons: duplicates existing Nanobot gateway and routing model; risks parallel architecture

2) **Greenfield Slack starter (Bolt Python)**
- Pros: mature ecosystem, straightforward event handling
- Cons: introduces second implementation path and language split vs current runtime direction

3) **Brownfield extension of existing RBTV + Nanobot workspace (recommended)**
- Pros: preserves existing workflow/state contracts, avoids duplicate orchestration/state logic, fastest path to PRD goals
- Cons: less template automation; requires disciplined adapter boundaries and contract tests

### Selected Starter: Brownfield Extension (No New External Starter)

**Rationale for Selection:**
This project is not a net-new app scaffold problem. It is an integration/adapter problem with strict compatibility requirements. Introducing a new starter would duplicate behavior already implemented in founder workflows and Nanobot runtime, increasing divergence risk.

**Initialization Command:**

```bash
# No external starter initialization.
# Continue from existing repository/workspace and implement mobile adapter and gateway wiring in-place.
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
No forced re-selection. Reuse current repository/runtime choices and preserve existing command/agent behavior.

**Styling Solution:**
Not applicable for this phase (messaging-first delivery, no primary web UI surface).

**Build Tooling:**
Use existing project tooling; avoid introducing competing build conventions from a new starter.

**Testing Framework:**
Focus on integration/contract tests around:
- `project-memo` read/write behavior
- agent switching continuity
- Slack channel/session isolation semantics

**Code Organization:**
Keep `_mobile/` as adapter boundary layer under existing RBTV structure; do not fork workflow logic.

**Development Experience:**
Prioritize reproducible bootstrap scripts and runtime health checks over scaffold generation.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Platform boundary: use Nanobot channel/gateway capabilities as the transport/orchestration baseline; build only RBTV-specific adapter logic on top.
- State authority: `project-memo` remains the canonical workflow state; no parallel state authority introduced.
- Session boundary: preserve `channel:chat_id` session semantics and prevent cross-session contamination.
- Access gate: enforce allowlist check before command routing and agent execution.
- Process supervision: single VPS runtime with restart policy and admin observability.

**Important Decisions (Shape Architecture):**
- Introduce a file-state adapter with schema-validated frontmatter operations and atomic writes.
- Standardize command normalization and routing contract (`mentor`, `domcobb`, `doc`, `status`, future `files`).
- Define failure envelopes for user-visible errors and admin-visible diagnostics.
- Add lightweight per-channel throttling to protect provider capacity.
- Keep channel formatting abstraction for Slack-now/WhatsApp-later portability.

**Deferred Decisions (Post-MVP):**
- Database introduction and tenant-isolated persistence model.
- Formal public API surface (REST/GraphQL) for external clients.
- Advanced observability stack (centralized tracing/metrics platform).
- Automated rollout pipeline beyond current update workflow.

### Data Architecture

- **Persistence model:** File-based canonical state for MVP (no database).
- **State authority:** `project-memo.md` is canonical for milestone/framework/progress state.
- **Conversation memory boundary:** `MEMORY.md` and `HISTORY.md` store conversational context only; no project workflow duplication.
- **Output model:** Framework documents remain primary generated artifacts in existing RBTV output layout.
- **Validation strategy:** Frontmatter schema guardrails with required keys (`currentMilestone`, `currentFramework`, `stepsCompleted`, plus optional metadata).
- **Write strategy:** Atomic write/update utility (write temp + replace) to reduce corruption risk.
- **Evolution strategy:** Introduce `schemaVersion` in project memo frontmatter for controlled upgrades.

### Authentication & Security

- **Authentication method:** Slack identity + allowlist only (MVP).
- **Authorization pattern:** deny-by-default pre-routing check; unauthorized users receive no response per PRD behavior.
- **Secret management:** environment variables only, restricted file permissions, no committed secrets.
- **Network posture:** outbound-only Socket Mode for messaging; no inbound public app ports.
- **Security middleware boundary:** centralize request validation and identity checks before any agent/tool invocation.

### API & Communication Patterns

- **Primary interaction pattern:** internal command/event contract, not external public API.
- **Pipeline contract:** inbound Slack event -> normalize -> resolve `channel:chat_id` session -> route command -> execute agent workflow -> persist state/artifacts -> respond.
- **Error handling standard:** user-facing concise failures + admin-channel operational details.
- **Rate limiting:** lightweight per-user/per-channel throttling and duplicate-message suppression.
- **Inter-module communication:** in-process module boundaries for MVP; avoid premature service split.
- **Command compatibility:** preserve existing RBTV command semantics and founder workflow expectations.

### Frontend Architecture

- **Scope decision:** no primary frontend/web dashboard architecture in MVP (messaging-first product).
- **Channel portability rule:** response formatting and channel-specific behaviors isolated in adapter layer so new channels do not alter core workflow logic.

### Infrastructure & Deployment

- **Hosting strategy:** single VPS, single runtime process family.
- **Runtime baseline:** use HKUDS Nanobot latest stable release from `https://github.com/HKUDS/nanobot` (or equivalent `nanobot-ai` package release) and align with its channel implementations; do not fork platform concerns already provided.
- **Process supervision:** system service restart policy plus periodic watchdog checks/notifications.
- **Environment strategy:** minimal environment tiers; production-focused configuration for prototype.
- **Monitoring/logging:** structured operational logs + startup/restart/status notifications to admin channel.
- **Update path:** `git pull` + controlled reapply/restart flow until installer automation is introduced.

### Decision Impact Analysis

**Implementation Sequence:**
1. Establish adapter boundaries and command routing contract.
2. Implement centralized auth/allowlist gate and session resolution.
3. Add file-state adapter with schema validation + atomic writes for `project-memo`.
4. Implement agent routing and switch continuity with persistence checkpoints.
5. Add error envelopes, logging, status command, and admin notifications.
6. Add throttling/guardrails and finalize channel formatting abstraction.

**Cross-Component Dependencies:**
- Routing depends on auth and session resolution.
- State writes depend on schema/atomic utilities.
- Recovery/monitoring depends on consistent process/service model.
- Channel portability depends on strict separation between adapter and core workflow execution.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
11 areas where AI agents could make different choices and create integration conflicts in the RBTV harness and channel adapter.

### Naming Patterns

**Project State & Files:**
- Canonical state file name remains `project-memo.md` (exact naming preserved).
- Workflow artifact files use existing RBTV naming and paths; no parallel naming scheme introduced.
- Adapter files under `_mobile/` use kebab-case filenames and camelCase function names.

**Command & Routing Naming:**
- Canonical command tokens are lowercase: `mentor`, `domcobb`, `doc`.
- Deferred commands per scoped cut: `status` and extended admin command surface (FR23, FR24, FR26 deferred for now).
- Internal events use dotted lowercase (e.g., `command.routed`, `memo.updated`, `agent.switched`).

**Code Naming Conventions:**
- TypeScript/JavaScript identifiers: camelCase variables/functions, PascalCase types/classes, UPPER_SNAKE_CASE constants.
- JSON/internal payload fields use camelCase.
- Existing frontmatter keys keep established names exactly (no aliases).

### Structure Patterns

**Project Organization:**
- Nanobot handles channel transport and gateway responsibilities.
- RBTV harness (`_mobile/`) handles normalization, routing to existing workflows, and response formatting.
- Founder workflow logic stays in existing founder/RBTV locations and is never duplicated under `_mobile/`.
- All `project-memo` access uses a shared memo adapter utility; avoid ad-hoc direct writes from multiple modules.

**Verification Organization (No Unit Test Mandate):**
- No unit-test requirement for Nanobot internals.
- Minimal smoke verification for our glue code only:
  - command route works (`mentor`, `domcobb`, `doc`)
  - allowlist enforcement works
  - `project-memo` read/write continuity works
  - session continuity works across agent switching

### Format Patterns

**Internal Response Envelope:**
- Success: `{ ok: true, data, meta? }`
- Failure: `{ ok: false, error: { code, message, retryable }, meta? }`
- Do not mix success and error payloads.

**Date/Time Format:**
- ISO-8601 UTC timestamps for logs/state metadata.
- No locale-formatted timestamps in state artifacts.

**Frontmatter Format:**
- Maintain stable key ordering and stable key names for compatibility with existing workflows.

### Communication Patterns

**Inbound Pipeline (Mandatory):**
1. Receive Slack event via Nanobot gateway.
2. Normalize payload in adapter.
3. Resolve `channel:chat_id` session key.
4. Enforce allowlist gate before workflow routing.
5. Route canonical command to agent/workflow.
6. Execute workflow using existing RBTV/founder contracts.
7. Persist state/artifacts via memo adapter.
8. Return formatted channel response.

**Agent Switching Pattern:**
- Checkpoint state before handoff.
- Resume from persisted `project-memo`, not transient conversational assumptions.

### Process Patterns

**Error Handling Patterns:**
- User-facing errors are concise and actionable.
- Operational logs include correlation id, command, session key, and error code.
- Retryable vs non-retryable failures are explicit.

**Execution Safety Patterns:**
- One active workflow execution per `channel:chat_id` at a time (session lock).
- Duplicate message suppression for quick repeats.
- Fail closed on malformed auth/context input.
- FR25 remains in scope: runtime auto-restart is required (process supervision policy enabled on VPS).

### Enforcement Guidelines

**All AI Agents MUST:**
- Preserve `project-memo` as single workflow state authority.
- Use shared memo update utility for state writes (atomic updates only).
- Keep transport/channel concerns in Nanobot layer and workflow concerns in RBTV harness.
- Enforce allowlist before routing.
- Avoid implementing deferred FR23, FR24, and FR26 capabilities in this phase.

**Pattern Enforcement:**
- Use a lightweight preflight checklist for each release candidate.
- Track violations via `doc` compound logs and remediation notes.
- Revisit deferred FR23-FR26 in a dedicated follow-up phase.

### Pattern Examples

**Good Examples:**
- Event accepted only after allowlist check, then command routed and memo checkpointed.
- Agent switch writes checkpoint to `project-memo` before control transfers.
- Adapter handles channel formatting while workflow logic remains unchanged.

**Anti-Patterns:**
- Re-implementing Slack transport logic outside Nanobot.
- Creating alternative state files that duplicate `project-memo` truth.
- Writing memo from multiple modules with different serializers.
- Adding FR23/FR24/FR26 admin features in this scoped phase; only FR25 auto-restart remains in scope.

## Project Structure & Boundaries

### Complete Project Directory Structure
```text
BMAD/
├── _bmad/
│   └── rbtv/
│       ├── _mobile/
│       │   ├── README.md
│       │   ├── config/
│       │   │   ├── mobile.config.example.yaml
│       │   │   └── allowlist.example.yaml
│       │   ├── adapter/
│       │   │   ├── event-normalizer.ts
│       │   │   ├── session-key.ts
│       │   │   ├── command-parser.ts
│       │   │   └── response-formatter.ts
│       │   ├── routing/
│       │   │   ├── command-router.ts
│       │   │   ├── agent-dispatch.ts
│       │   │   └── route-contract.ts
│       │   ├── state/
│       │   │   ├── project-memo-adapter.ts
│       │   │   ├── frontmatter-schema.ts
│       │   │   └── atomic-write.ts
│       │   ├── security/
│       │   │   ├── allowlist-gate.ts
│       │   │   ├── env-guard.ts
│       │   │   └── input-sanitizer.ts
│       │   ├── runtime/
│       │   │   ├── session-lock.ts
│       │   │   ├── dedupe.ts
│       │   │   └── error-envelope.ts
│       │   ├── integration/
│       │   │   ├── nanobot-gateway-bridge.ts
│       │   │   └── founder-workflow-bridge.ts
│       │   ├── ops/
│       │   │   ├── vps-hardening-checklist.md
│       │   │   ├── deploy-runbook.md
│       │   │   ├── smoke-checklist.md
│       │   │   └── systemd/
│       │   │       └── nanobot-gateway.service
│       │   └── scripts/
│       │       ├── validate-env.ts
│       │       ├── preflight.ts
│       │       └── start-gateway.sh
│       └── ... (existing RBTV/founder workflows preserved)
├── _bmad-output/
│   └── robotville-v4.0/
│       ├── bmad/
│       │   ├── prd.md
│       │   └── architecture.md
│       └── founder/
│           ├── project-memo.md
│           └── ... (existing framework output files)
├── .env.example
├── .gitignore
└── README.md
```

### Architectural Boundaries

**API Boundaries:**
- No public API introduced in this phase.
- Primary boundary is internal command/event contract:
  - Nanobot inbound message -> `_mobile` normalization/routing -> existing RBTV/founder workflows.

**Component Boundaries:**
- Nanobot layer owns channel transport, socket lifecycle, and gateway process.
- `_mobile/adapter` + `_mobile/routing` own normalization, command mapping, and dispatch.
- Existing founder/RBTV workflow definitions own business process logic and state semantics.

**Service Boundaries:**
- In-process module boundaries only for this phase.
- No microservice split.
- State access centralized via `project-memo-adapter`.

**Data Boundaries:**
- Canonical workflow state: `project-memo.md`.
- Conversational memory remains Nanobot memory subsystem.
- No duplicate workflow-state stores.

### Requirements to Structure Mapping

**Feature Mapping:**
- FR1-FR3 (agent invocation): `_mobile/routing/command-router.ts`, `_mobile/integration/founder-workflow-bridge.ts`
- FR6-FR10 (workflow execution + browser-dependent pathways): existing RBTV workflows + `_mobile/integration/*`
- FR11-FR19 (state continuity + switching): `_mobile/state/*`, `_mobile/runtime/session-lock.ts`
- FR20-FR22 (allowlist security): `_mobile/security/allowlist-gate.ts`
- FR25 (auto-restart): `_mobile/ops/systemd/nanobot-gateway.service`
- FR30 (output structure preservation): `_mobile/state/project-memo-adapter.ts` + existing output paths

**Deferred Mapping:**
- FR23, FR24, FR26 intentionally deferred in this phase.

### Integration Points

**Internal Communication:**
- `nanobot-gateway-bridge` -> `event-normalizer` -> `command-router` -> `agent-dispatch` -> `project-memo-adapter`.

**External Integrations:**
- Slack via Nanobot Socket Mode.
- AI provider routing via Nanobot provider system.

**Data Flow:**
- Message input -> auth gate -> session resolution -> workflow execution -> memo/artifact update -> channel response.

### File Organization Patterns

**Configuration Files:**
- Runtime and security examples live in `_mobile/config/`.
- Secrets are environment-only.

**Source Organization:**
- `_mobile` is adapter/harness only.
- Existing workflow logic remains in current RBTV/founder files.

**Verification Organization:**
- No unit test mandate in this phase.
- Use smoke checklist in `_mobile/ops/smoke-checklist.md` for release readiness.

**Asset Organization:**
- No dedicated asset pipeline for this messaging-first phase.

### Development Workflow Integration

**Development Runtime Structure:**
- Nanobot gateway is the runtime entrypoint; `_mobile` modules provide harness behavior.

**Build Process Structure:**
- Minimal compile and environment preflight for harness modules.

**Deployment Structure:**
- VPS runbook and hardening checklist drive deployment.
- `systemd` service enforces FR25 auto-restart behavior.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All core decisions are compatible with the selected brownfield strategy:
- Nanobot remains platform/runtime baseline.
- RBTV `_mobile` remains harness/adapter layer.
- `project-memo` remains canonical workflow state.
- Security model (allowlist + env secrets + outbound socket mode) is consistent with VPS constraints.
- Scoped requirement decision is coherent: FR25 active, FR23/FR24/FR26 deferred.

**Pattern Consistency:**
Implementation patterns support architectural decisions:
- Naming and routing conventions are aligned with existing command contracts.
- State-write rules prevent conflicting agent behavior.
- Adapter boundaries prevent duplicate implementations of Nanobot responsibilities.

**Structure Alignment:**
Project structure supports the chosen architecture:
- `_mobile` modules map directly to required integration concerns.
- Existing founder/RBTV workflow files remain untouched as source of process truth.
- Auto-restart capability has a concrete structure location (`ops/systemd`).

### Requirements Coverage Validation ✅

**Feature Coverage:**
All in-scope FRs have architectural support and mapped locations.

**Functional Requirements Coverage:**
- Covered now: FR1-FR3, FR6-FR22, FR25, FR30
- Deferred intentionally: FR23, FR24, FR26 (captured explicitly as scope decisions)

**Non-Functional Requirements Coverage:**
- Security coverage is strong for prototype scope (secrets, allowlist, network posture).
- Reliability coverage is sufficient for current scope with FR25 auto-restart; NFR11 startup/restart admin notifications are explicitly deferred to align with deferred FR24/FR26.
- Performance and integration constraints are architecturally addressed at the adapter/runtime boundary.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Critical decisions are documented with clear ownership boundaries and compatibility constraints.

**Structure Completeness:**
Directory structure and component boundaries are specific enough for AI-agent implementation.

**Pattern Completeness:**
Conflict-prone areas (naming, state, routing, errors, safety) are defined with enforceable rules.

### Gap Analysis Results

**Critical Gaps:** None.

**Important Gaps:**
- Manual smoke verification is defined, but no automated acceptance harness yet (acceptable for this scope).
- Deferred FR23/24/26 and aligned NFR11 notification behavior need a tracked follow-up milestone to avoid ambiguity later.

**Nice-to-Have Gaps:**
- Optional runbook automation for provisioning and rollout.
- Expanded channel portability checklist for WhatsApp phase.

### Validation Issues Addressed

- Resolved scope contradiction by explicitly retaining FR25 while deferring FR23/24/26.
- Aligned NFR11 with prototype scope by deferring startup/restart admin notifications to the FR24/FR26 follow-up phase.
- Confirmed no duplicate implementation of Nanobot channel/runtime responsibilities.
- Confirmed architecture focuses on infra + harness + connection + safety, not re-building platform internals.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context analyzed
- [x] Scale and constraints assessed
- [x] Technical dependencies identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Core decisions documented
- [x] Platform boundaries defined
- [x] Integration patterns defined
- [x] Scope/defer decisions captured

**✅ Implementation Patterns**
- [x] Naming and routing conventions set
- [x] State consistency rules defined
- [x] Communication/error patterns specified
- [x] Safety/process rules documented

**✅ Project Structure**
- [x] Complete structure defined
- [x] Boundaries established
- [x] Requirement mapping completed
- [x] Integration points documented

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Clear non-duplication boundary with Nanobot
- Canonical state authority (`project-memo`) preserved
- Strong security-first MVP posture
- Concrete structure for harness implementation

**Areas for Future Enhancement:**
- FR23/24/26 phase with admin status and notification capabilities
- Automated acceptance/regression checks for harness flows
- Optional deployment automation improvements

### Implementation Handoff

**AI Agent Guidelines:**
- Follow architecture boundaries strictly (Nanobot platform vs RBTV harness).
- Preserve `project-memo` as single workflow-state source.
- Implement FR25 restart behavior in VPS service setup.
- Do not introduce deferred FR23/24/26 in this phase.

**First Implementation Priority:**
Build and wire `_mobile` adapter/routing/state modules, then deploy on VPS with secure config and FR25 auto-restart enabled.
