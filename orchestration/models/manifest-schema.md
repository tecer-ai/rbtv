# Capability-Manifest Schema

The machine-readable capability manifest every model package ships at `{rbtv_path}/orchestration/models/{model}/manifest.yaml`. It is the **routing card's data interface**: the routing card reads the installed packages' manifests and routes on `(model, variant)` pairs from the fields defined here. This document defines the field list, each field's routing-card consumer, and how the routing card consumes a manifest. The fill-in template is `./manifest-template.yaml`.

This schema finalizes the D5 field draft (`debate-decisions.md` D5 — "finalize at build"). It carries ONLY fields a routing-card question reads (the §3 consumer-question table is the proof obligation); a field no routing question consumes is schema bloat and is cut.

---

## Format: YAML

Manifests are **YAML**, not JSON. Rationale:

| Reason | Detail |
|--------|--------|
| The consumer is an LLM agent, not a code parser | The routing card is read and executed by a Claude conductor that reads each installed manifest as context at routing time. YAML lets every field carry an inline `#` comment the router reads alongside the value; JSON forbids comments. |
| Repo-wide consistency | Every other structured data surface in this repo is YAML — frontmatter, persona/agent files, kimi `--agent-file` specs, the `sb-workflow-context` YAMLs. A JSON manifest would force a reader to switch mental models mid-tree. |
| Hand-authored tolerance | Model deltas are written by hand. YAML tolerates comments and trailing content and is forgiving of minor syntax; JSON's strictness (no comments, no trailing commas) makes hand-authored data brittle. |

(`admin/install/module-manifest.json` is JSON because `install.py` parses it programmatically — a different consumer class. These capability manifests are agent-read, so they are YAML.)

---

## 1. Schema structure

A manifest is one YAML document with four top-level keys (plus one optional installer-consumed key):

| Key | Type | Purpose |
|-----|------|---------|
| `model` | string | The package id — matches the folder name `models/{model}/` (e.g. `kimi-code-cli`, `codex-cli`, `claude-code-cli`, `qwen-code-cli`). The id is folder-safe and states carrier + runtime. |
| `display` | string | Human-facing label shown in the installer worker pick-menu and the baked availability line — the parenthesized carrier+runtime form the folder-safe id cannot carry (e.g. `kimi-code (CLI)`, `claude (native, from Claude Code)`, `gemini (API)`). **Installer-consumed, NOT a routing input** — the router parser (`route.py`) ignores it; it is therefore exempt from the §3 routing-consumer obligation and the variant field-count discipline. Falls back to the bare folder name when absent. |
| `evidence_status` | string | Package-level validation status: `validated` (piloted live) or `probe-pending` (authored from docs/probe, not yet pilot-validated). Per-variant overrides allowed (see `variants[].evidence_status`). |
| `permission_rules` | list (optional) | The literal Claude Code permission-allowlist strings a conductor session needs to spawn this CLI worker in-session (e.g. `"Bash(qwen:*)"`, `"PowerShell(qwen:*)"` — PREFIX rules, hence the start-with-binary dispatch shaping in `dispatch-wrapper.md` §1). **Installer-consumed, NOT a routing input** (same §3 exemption as `display`): on install, an ELECTED package's strings are ensured present in the target's `.claude/settings.local.json` `permissions.allow`; a present-but-NOT-elected package's strings are removed. Only these exact strings are ever touched — hand-added entries survive. Omit for packages a session never shell-spawns (API workers, the native Agent-tool carrier). Must be TOP-LEVEL (column 0) — the installer's line-scan reader ignores nested keys. |
| `variants` | list | One entry per routable `(model, variant)` pair. Routing routes on these — never on a bare model name. A model with a single operating profile still declares one variant. |

Every routing input below the model level lives **inside a variant** — because routing routes on `(model, variant)`, and two variants of the same model can differ in reasoning tier, cost class, or context window (e.g. a `--thinking` vs `--no-thinking` profile, or two configured models).

---

## 2. Variant fields — the finalized D5 field list

Each entry in `variants` carries the fields below. Required fields MUST be present (a manifest missing a required field is malformed — the routing card treats the package as un-routable and logs it, never infers the value). Optional fields are omitted when not applicable.

| Field | Required | Type | Meaning |
|-------|----------|------|---------|
| `variant` | yes | string | The variant id, unique within the model (e.g. `default`, `thinking`, `fast`). The `(model, variant)` pair is the routing key. |
| `display` | no | string | Per-variant human-facing label for the installer's backend-election rows — a CONFIGURABLE package (see `configurable_model`) surfaces each variant as a separately-electable row labeled with this. **Installer-consumed, NOT a routing input** — `route.py` ignores it (same §3 exemption as the package-level `display`). Falls back to the variant id when absent. |
| `reasoning_tier` | yes | enum | `non-reasoning` · `mid` · `top`. The boundedness-tree input: which boundedness band this variant can serve. `non-reasoning` = bounded code/mechanical only; `mid` = partially-bounded with `doubt_policy: halt`; `top` = judgment-dense. |
| `context_window` | yes | int (tokens) | Usable input budget. Sizes how much inlined task context fits before a task must be split. |
| `max_output` | yes | int (tokens) | Max tokens the worker can emit in one turn. Flags work whose single-turn output would exceed it. |
| `cost_class` | yes | enum | `cheapest` · `low` · `mid` · `high` · `premium`. The budget-filter input and the "cheapest capable" tiebreaker in the boundedness tree. `premium` ranks ABOVE `high` (reserved for premium-priced top-tier models — e.g. Fable 5 at ~2× opus pricing); cost-ascending selectors rank it LAST, so a `premium` variant is never auto-picked on a cost tie — it is reached via pinned roles. |
| `code_competence` | yes | enum | `none` · `bounded` · `strong`. Whether this variant executes code, and how well — picks kimi-vs-codex and gates code leaves. `none` = not a code executor (route code elsewhere). |
| `web_access` | yes | bool | Whether the variant can reach the web natively. The research-leaf gate (route a research brief only to a `web_access: true` worker). |
| `multimodal` | no | list | Input modalities beyond text the variant accepts (e.g. `[image]`). Omitted = text-only. Gates a task that must feed an image to the worker. |
| `parallel_safe` | yes | bool | Whether multiple instances can run concurrently in the same work-dir under disjoint allowlists. The batching/parallel-wave input. |
| `resume_support` | yes | enum | `none` · `session-id` · `continue`. Whether and how a halted/incomplete dispatch resumes the same session — drives resume-vs-re-dispatch after a `DOUBT_ESCALATED`/`NEEDS_CONTEXT` halt. |
| `headless` | yes | map | How to run the variant non-interactively. Sub-fields: `flags` (the headless/print invocation, e.g. `--quiet`), `auto_approves_tools` (bool — does headless mode auto-approve every tool call, the confinement-burden flag), `prompt_transport` (`arg` · `stdin` · `either` — how the prompt reaches the worker, a host-limit input). |
| `auth` | yes | map | Auth requirement before dispatch. Sub-fields: `required` (bool), `method` (e.g. `cli-login`, `api-key`, `none`), `interactive` (bool — does first-time auth need a human, i.e. a USER-EXECUTED-ONLY pre-flight). |
| `rate_budget_notes` | no | string | Rate limits, quota behavior, or budget gotchas the conductor must respect (e.g. retryable-throttle exit code, per-model spend forecast basis). |
| `tool_surface` | yes | map | What the worker can do. Sub-fields: `native` (list of built-in tool families, e.g. `[shell, file, web]`), `mcp` (bool — accepts MCP servers), `agent_file` (bool — supports a per-dispatch agent/guidance spec that constrains the tool set). |
| `confinement` | yes | map | How the worker's blast radius is bounded. Sub-fields: `workspace_scope` (the flag(s) that scope it, e.g. `--work-dir` + `--add-dir`), `tool_restriction` (how to strip tools, e.g. `agent-file exclude_tools`), `write_enforcement` (the reliable post-run check, e.g. `git-diff-vs-allowlist`). Captures that confinement may be the orchestrator's job, not the CLI's. |
| `invocation_pointer` | yes | string | Relative pointer to the rendered dispatch manual for the exact command shape (`./manual.md`). The manifest does NOT carry the full invocation — it points to the manual so routing recall stays light. The conductor reads this JIT at routing time; it is NOT the planning-emittable constant (see `manual_path`). |
| `manual_path` | yes | string | Canonical relative path to the package's rendered dispatch manual: ALWAYS `./manual.md` (relative to this manifest, i.e. `models/{model}/manual.md`). DISTINCT from `invocation_pointer` by CONSUMER: `manual_path` is the **planning-emittable path constant** the planning→dispatch seam pins into a task's frontmatter so no agent ever RE-DERIVES the manual path (the rename-transcript stumble — a path re-derived wrongly, recovered only by `ls`). A fixed constant, not a routing-time read. |
| `delta_path` | yes | string | Canonical relative path to the package's `delta.md` (the per-model render source): ALWAYS `./delta.md` (relative to this manifest, i.e. `models/{model}/delta.md`). The planning-emittable constant the dispatch-scaffold seam reads to locate the delta to compose, without re-deriving it. No prior field pointed at `delta.md` — `invocation_pointer` names only the manual. |
| `specialty` | no | string | A one-line positive "best at" capability statement for this `(model, variant)` — what it is GREAT at (e.g. "bounded code execution", "cheapest text synthesis", "web research via search grounding"). Consumed ONLY as a **within-tier tiebreaker** — never as the master routing cut (boundedness-first stays the master cut; `specialty` breaks a tie BETWEEN variants the boundedness tree already placed in the same tier). Omitted when the variant has no distinguishing specialty beyond its tier. |
| `configurable_model` | no | map | Declares that the served model is CONFIGURATION, not a fixed package identity — the actual model the harness runs is set by config/env, not baked into the package. Sub-fields: `is_configurable` (bool — true when the CLI runs a configurable model set), `note` (short string naming the configuration surface, e.g. the `--auth-type` / `OPENAI_BASE_URL` / `OPENAI_MODEL` switches), `provider_label` (optional string — the installer's backend-election provider-path label for this package's rows, e.g. `qwen-code (DashScope US)`; **installer-consumed, NOT a routing input**; defaults to the package `display` minus its trailing parenthetical). Omitted for packages whose model identity is fixed. Drives result-attribution (the run-log names "the package running configured-model X", never a fixed model id), the router's provider-model-id resolution (the model id is read at dispatch, not assumed from the package name), and — when `is_configurable: true` — the installer's per-backend election surface (each variant becomes a separately-electable row; see §4 `model_variants`). |
| `failure_modes` | yes | list | Known failure modes the conductor pre-empts (each a short string, e.g. `headless auto-approves all tools — no native allowlist`, `cd does not persist between shell calls`, `runaway autonomous loop if iteration cap unset`). Sourced from validated evidence; un-validated packages may carry `[]` plus a `probe-pending` status. |
| `guidance_file` | no | map | The per-workspace guidance file this worker natively loads, if any. Sub-fields: `convention` (the filename, e.g. `AGENTS.md`, or `CLAUDE.md` for claude-code-cli), `mirror_entry` (the mirror-machinery entry point that generates/syncs it). Drives routing's pre-dispatch guidance-file check. Omitted when the worker loads no workspace guidance file (e.g. a pure Agent-tool-equivalent). |
| `swarm_support` | yes | map | Whether the worker can itself spawn sub-workers. Sub-fields: `subagents` (bool — can it launch its own subagents), `nesting` (`none` · `one-level` — depth it allows), `default` (`enabled` · `disabled` — the safe default posture). Informs topology and the depth cap. |
| `os_quirks` | no | map | OS-specific invocation notes, keyed by OS (e.g. `windows:`). Carries the Windows-specific corpus notes (stdin-pipe handling, exit-code semantics, first-run delays). Omitted when none. |
| `evidence_status` | no | enum | Per-variant override of the package-level `evidence_status` (`validated` · `probe-pending`). Omitted = inherits the package-level value. Lets a model ship one validated variant and one probe-pending variant. |

### 2a. Repurposed field semantics for API/agentic workers

The four required fields `headless`, `tool_surface`, `confinement`, and `swarm_support` are shaped for CLI/Agent-tool workers (run-with-flags, native tool families, filesystem scoping, subagent spawning). API chat workers and Agent-tool in-session workers have none of these in their original CLI sense. **Decision (design §0.4 option a): repurpose — fill with API/agentic-meaningful values** rather than adding a `transport:` discriminator. Rationale: no schema churn; the repurposed values remain routing-informative. `transport:` is the documented escalation path if the repurposed values ever mislead the router.

**Canonical repurposed values for API chat workers** (stateless HTTP-call workers — no filesystem access, no tool execution loop):

| Field | API-worker value | What it means to the router |
|-------|------------------|------------------------------|
| `headless` | `flags: ""` (no invocation flags — the runner script is always non-interactive), `auto_approves_tools: false` (no tool-approval surface), `prompt_transport: arg` (prompt reaches the runner via `--prompt-file` argument) | The runner is always non-interactive; no approval dialog exists. |
| `tool_surface` | `native: []` or `native: [web]` (Gemini only — grounding), `mcp: false`, `agent_file: false` | The worker executes no shell/file tools. Gemini's `native: [web]` is what gates the web-research leaf for API workers. |
| `confinement` | `workspace_scope: "output-folder only — no filesystem access"`, `tool_restriction: "none — worker cannot execute tools"`, `write_enforcement: "runner writes only into --output-folder; path-sanitized against ../ and absolute paths"` | Confinement is the runner's job (path sanitization), not the CLI's. The conductor does NOT need to scope a work-dir. |
| `swarm_support` | `subagents: false`, `nesting: none`, `default: disabled` | API workers cannot spawn sub-workers. |

**Canonical repurposed values for Agent-tool in-session workers** (the `models/claude-code-native/` package — Claude variants dispatched as sub-agents via the Agent tool, not as a process):

| Field | Agent-tool value | What it means to the router |
|-------|------------------|------------------------------|
| `headless` | `flags: ""` (no process flags), `auto_approves_tools: false` (Agent-tool sub-agents run under the conductor's permissions), `prompt_transport: arg` (prompt passed as the Agent tool's `prompt` parameter) | The Agent tool call is always non-interactive; the tool parameter IS the prompt. |
| `tool_surface` | `native: [shell, file]` (inherits the conductor's tool grants; no native web), `mcp: false` (inherits session MCP), `agent_file: false` (no per-dispatch agent/guidance spec) | The sub-agent operates with the conductor's tool set, not an independently configured one. |
| `confinement` | `workspace_scope: "allowlist only — no --work-dir flag"`, `tool_restriction: "conductor's disjoint allowlist"`, `write_enforcement: "git-diff-vs-allowlist"` | Confinement is the conductor's job (allowlist passed in the prompt); no process-level directory scoping. |
| `swarm_support` | `subagents: false`, `nesting: none`, `default: disabled` | Agent-tool sub-agents are the nesting wall — they MUST NOT spawn further sub-agents (depth cap ≤ 2 from the root conductor). |

**Canonical repurposed values for agentic-web workers** (autonomous-agent task-API workers — e.g. Manus: submit a task → poll → retrieve the agent's output; the agent runs its OWN browser/tool loop **server-side**, which we neither drive nor confine):

| Field | Agentic-web value | What it means to the router |
|-------|-------------------|------------------------------|
| `headless` | `flags: ""` (runner non-interactive), `auto_approves_tools: false` (no approval surface — the agent's loop is server-side), `prompt_transport: arg` (prompt → runner via `--prompt-file`, inlined into the task `description`) | The runner is always non-interactive; no approval dialog exists. |
| `tool_surface` | `native: [web, browser]` (the agent's autonomous browser is its defining capability), `mcp: false`, `agent_file: false` | The agent executes its OWN server-side tool loop, NOT ours — `[web, browser]` gates the autonomous-web leaf. |
| `confinement` | `workspace_scope: "output-folder only — no local filesystem access"`, `tool_restriction: "none — the agent runs its own server-side tool loop, not ours"`, `write_enforcement: "runner writes only the agent's returned output into --output-folder; path-sanitized"` | Confinement is the runner's job; the conductor scopes no work-dir. |
| `swarm_support` | `subagents: false`, `nesting: none`, `default: disabled` | The agent cannot spawn OUR sub-workers; its internal autonomy is server-side and invisible to our topology/depth-cap. |

**`transport:` discriminator — escalation-only fallback.** A `transport: api | cli | agent` field is the documented next step if the repurposed values above ever mislead the router in practice (e.g., if a future routing question cannot be answered unambiguously from the repurposed values). Do NOT add it speculatively; add it only when a concrete ambiguity in the routing card demands it.

---

**Field-count discipline:** every field above is consumed by a routing-card question in §3. If a future edit adds a field, it MUST add the matching consumer row in §3 or it does not belong in the schema (validated-evidence-only applies to schema bloat).

**Variant field-count discipline:** a provider mode that changes NO routing-relevant field does NOT get its own variant entry. Author a variant only when at least one field in §2 differs from the existing variant(s) for the same model (e.g., `reasoning_tier`, `context_window`, `cost_class`, `web_access`, `code_competence`). Identical-routing modes collapse into one variant — duplicating a row that routes identically is schema bloat.

---

## 3. Consumer questions — every field answers a routing-card question

The proof that no field is bloat: each maps to a question the routing card (`{rbtv_path}/orchestration/skills/orchestrating/cards/routing.md`) asks. A field with no consumer question is cut.

| Field | Routing-card question it answers | Card location |
|-------|----------------------------------|---------------|
| `model` / `variant` | "Which `(model, variant)` pair receives this task?" | §1, §2 (routes on pairs) |
| `reasoning_tier` | "Does this variant's reasoning match the task's boundedness band?" | §2 (boundedness tree) |
| `context_window` | "Will the task's inlined context fit, or must it be split?" | §8 (batch sizing) + task-file contract §5 |
| `max_output` | "Can the worker emit this task's output in one turn?" | §8 (batch sizing) |
| `cost_class` | "Is this the cheapest capable variant? Does the budget map allow it?" | §2 (BUDGET filter, cheapest-capable) |
| `code_competence` | "Can this variant execute the code work? kimi or codex?" | §2 (code leaves), §4 (kimi-vs-codex) |
| `web_access` | "Can this worker reach the web for the research leaf?" | §6 (research leaf) |
| `multimodal` | "Can the worker accept the image/non-text input this task feeds it?" | §2 (capability gate) |
| `parallel_safe` | "Can I run these in a parallel wave with disjoint allowlists?" | §8 (parallelism, worktree isolation) |
| `resume_support` | "After a halt, do I resume the session or re-dispatch fresh?" | §4 (topology) → hands to halt-recovery resume choice |
| `headless` | "How do I run this non-interactively, and does it auto-approve tools?" | §4 (carrier resolution) → dispatch-wrapper invocation |
| `auth` | "Does this need a USER-EXECUTED-ONLY auth pre-flight before dispatch? Or, for `method: api-key`, does the key resolve?" | §1 (availability) → halt-recovery USER-EXECUTED-ONLY; for `api-key` workers see §4 availability note |
| `rate_budget_notes` | "What throttle/quota behavior must the conductor handle on this worker?" | §2 (BUDGET), §8 (wave pacing) |
| `tool_surface` | "Does the worker have the tools this task needs (shell/web/MCP)?" | §2 (capability gate), §6 (web via tools) |
| `confinement` | "How do I bound this worker's writes — and is that my job, not the CLI's?" | §4 (guidance-file check), §8 (allowlist enforcement) |
| `invocation_pointer` | "Where is the exact command shape when I package the dispatch?" | §4 → hands to dispatch-wrapper / model manual |
| `manual_path` | "What manual-path constant do I PIN into this task's frontmatter so the worker/scaffold never re-derives it?" | §4 → planning→dispatch seam (frontmatter the dispatch-scaffold + planning emit; closes the D10 re-derivation gap) |
| `delta_path` | "Where is this package's render-source delta, as a constant — to compose the dispatch without re-deriving the path?" | §4 → dispatch-scaffold compose-from-source (the delta the scaffold reads) |
| `specialty` | "Two variants tie within the chosen tier — which is BEST at this task's shape?" | §2a (within-tier tiebreaker, AFTER the boundedness master cut) + §4 carrier choice; the positive form is also surfaced in `orchestration/docs/routing-matrix-reference.md` |
| `configurable_model` | "Is this package's served model fixed, or configured at dispatch — and what do I attribute the result to?" | §1 (provider-model-id resolution — read the configured id, don't assume from the package name) + §9 (honest run-log attribution of the configured model) |
| `failure_modes` | "What known failure must I pre-empt for this worker?" | §2 (manifest's known-failure-modes are routing inputs) |
| `guidance_file` | "Does the target workspace carry this worker's guidance file? Mirror it if absent." | §4 (pre-dispatch guidance-file check) |
| `swarm_support` | "Can this worker sub-conduct, and at what depth cap?" | §4 (topology, depth cap ≤ 2) |
| `os_quirks` | "What Windows-specific invocation note applies here?" | §4 → dispatch-wrapper invocation (prompt transport) |
| `evidence_status` | "Is this worker pilot-validated or probe-pending? Flag the unvalidated seam." | §1, §9 (label unvalidated routing honestly in the run-log) |

---

## 4. How the routing card consumes manifests

Consumption is **installed-manifests-only**, and **folder presence = availability**:

| Rule | Detail |
|------|--------|
| Folder presence = availability | A package is routable iff `{rbtv_path}/orchestration/models/{model}/` exists on disk. An absent folder = an absent row; that model is not a choice this run. The routing card lists the live `models/` folder and trusts it over the installer-baked availability line on any mismatch (disk = truth). |
| Read only installed manifests | For each installed package, the router reads `models/{model}/manifest.yaml` at routing time (not front-loaded). It does NOT read manifests for absent packages. |
| Route on `(model, variant)` pairs | The router never routes on a bare model name — it selects a variant from `variants[]` whose fields satisfy the leaf (boundedness, stakes, budget, capability gates). |
| Parse expectations | The router reads the YAML as a structured document: top-level `model` / `evidence_status` / `variants`, then per-variant fields by the names in §2. A required field absent → the package is malformed; the router logs it and treats the package as un-routable rather than guessing the value. An unknown extra field is ignored (forward-compatible), not an error. |
| Degrade gracefully | If the cheapest capable variant for a leaf is not installed, the router routes to the next capable installed `(model, variant)` and logs the substitution. Zero installed packages → only Agent-tool Claude tiers are routable (routing card §1); a task that REQUIRES a CLI worker halts. |
| `auth.method: api-key` availability | **Availability = the key resolves**, not a USER-EXECUTED login. Check order: OS environment variable first (e.g. `DEEPSEEK_API_KEY`), then the `env_file` path recorded in `rbtv.json`. If the key is absent in both → the package is unavailable for this dispatch; the router logs it and degrades (does not halt). This is distinct from `cli-login` workers, whose availability requires a USER-EXECUTED-ONLY login pre-flight (`auth.interactive: true`). For `method: api-key` workers, `auth.interactive: false` — availability is a key-resolution test the runner performs, never a human gesture. |
| Backend-subset election (`model_variants`) | A CONFIGURABLE package (`configurable_model.is_configurable: true`) may be confined to a subset of its backends via `rbtv.json` `model_variants` (`{package_id: [variant_id, ...]}`). `route.py` enumerates ONLY the listed backends of that package and skips the rest at enumerate (reason `not elected (rbtv.json model_variants)`); an ABSENT entry => ALL its variants (back-compat with pre-variant installs). The installer surfaces each backend of a configurable package as a separately-electable, provider-path-labeled row (`install.py --list-model-backends`; interactive picker, or `--model-variants pkg=v1,v2`). A proper-subset election is recorded in `model_variants`; a full election records no entry (so a backend added later is auto-included). This is backend-level refinement OF the package-level `model_packages` election — a configurable package is still elected/deselected as a whole in `model_packages`. |

The manifest is **recall + routing inputs**; the rendered manual (`./manual.md`, pointed to by `invocation_pointer`) is the exact invocation shape, read JIT at first dispatch. The manifest never duplicates the manual's command text — it points to it.

---

## 5. Authoring a manifest

A model package author fills `./manifest-template.yaml` for the package and saves it as `models/{model}/manifest.yaml`. Every required field in §2 must be present with an evidence-traceable value; unvalidated values carry `evidence_status: probe-pending` (package-level or per-variant). Do NOT invent values speculatively — an unknown required value means the package is not ready to ship, not that a placeholder is acceptable.
