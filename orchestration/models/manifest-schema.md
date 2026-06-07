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

A manifest is one YAML document with three top-level keys:

| Key | Type | Purpose |
|-----|------|---------|
| `model` | string | The package id — matches the folder name `models/{model}/` (e.g. `kimi`, `codex`, `claude-cli`, `qwen`). |
| `evidence_status` | string | Package-level validation status: `validated` (piloted live) or `probe-pending` (authored from docs/probe, not yet pilot-validated). Per-variant overrides allowed (see `variants[].evidence_status`). |
| `variants` | list | One entry per routable `(model, variant)` pair. Routing routes on these — never on a bare model name. A model with a single operating profile still declares one variant. |

Every routing input below the model level lives **inside a variant** — because routing routes on `(model, variant)`, and two variants of the same model can differ in reasoning tier, cost class, or context window (e.g. a `--thinking` vs `--no-thinking` profile, or two configured models).

---

## 2. Variant fields — the finalized D5 field list

Each entry in `variants` carries the fields below. Required fields MUST be present (a manifest missing a required field is malformed — the routing card treats the package as un-routable and logs it, never infers the value). Optional fields are omitted when not applicable.

| Field | Required | Type | Meaning |
|-------|----------|------|---------|
| `variant` | yes | string | The variant id, unique within the model (e.g. `default`, `thinking`, `fast`). The `(model, variant)` pair is the routing key. |
| `reasoning_tier` | yes | enum | `non-reasoning` · `mid` · `top`. The boundedness-tree input: which boundedness band this variant can serve. `non-reasoning` = bounded code/mechanical only; `mid` = partially-bounded with `doubt_policy: halt`; `top` = judgment-dense. |
| `context_window` | yes | int (tokens) | Usable input budget. Sizes how much inlined task context fits before a task must be split. |
| `max_output` | yes | int (tokens) | Max tokens the worker can emit in one turn. Flags work whose single-turn output would exceed it. |
| `cost_class` | yes | enum | `cheapest` · `low` · `mid` · `high`. The budget-filter input and the "cheapest capable" tiebreaker in the boundedness tree. |
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
| `invocation_pointer` | yes | string | Relative pointer to the rendered dispatch manual for the exact command shape (`./manual.md` once the render step ships). The manifest does NOT carry the full invocation — it points to the manual so routing recall stays light. |
| `failure_modes` | yes | list | Known failure modes the conductor pre-empts (each a short string, e.g. `headless auto-approves all tools — no native allowlist`, `cd does not persist between shell calls`, `runaway autonomous loop if iteration cap unset`). Sourced from validated evidence; un-validated packages may carry `[]` plus a `probe-pending` status. |
| `guidance_file` | no | map | The per-workspace guidance file this worker natively loads, if any. Sub-fields: `convention` (the filename, e.g. `AGENTS.md`, or `CLAUDE.md` for claude-cli), `mirror_entry` (the mirror-machinery entry point that generates/syncs it). Drives routing's pre-dispatch guidance-file check. Omitted when the worker loads no workspace guidance file (e.g. a pure Agent-tool-equivalent). |
| `swarm_support` | yes | map | Whether the worker can itself spawn sub-workers. Sub-fields: `subagents` (bool — can it launch its own subagents), `nesting` (`none` · `one-level` — depth it allows), `default` (`enabled` · `disabled` — the safe default posture). Informs topology and the depth cap. |
| `os_quirks` | no | map | OS-specific invocation notes, keyed by OS (e.g. `windows:`). Carries the Windows-specific corpus notes (stdin-pipe handling, exit-code semantics, first-run delays). Omitted when none. |
| `evidence_status` | no | enum | Per-variant override of the package-level `evidence_status` (`validated` · `probe-pending`). Omitted = inherits the package-level value. Lets a model ship one validated variant and one probe-pending variant. |

**Field-count discipline:** every field above is consumed by a routing-card question in §3. If a future edit adds a field, it MUST add the matching consumer row in §3 or it does not belong in the schema (validated-evidence-only applies to schema bloat).

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
| `auth` | "Does this need a USER-EXECUTED-ONLY auth pre-flight before dispatch?" | §1 (availability) → halt-recovery USER-EXECUTED-ONLY |
| `rate_budget_notes` | "What throttle/quota behavior must the conductor handle on this worker?" | §2 (BUDGET), §8 (wave pacing) |
| `tool_surface` | "Does the worker have the tools this task needs (shell/web/MCP)?" | §2 (capability gate), §6 (web via tools) |
| `confinement` | "How do I bound this worker's writes — and is that my job, not the CLI's?" | §4 (guidance-file check), §8 (allowlist enforcement) |
| `invocation_pointer` | "Where is the exact command shape when I package the dispatch?" | §4 → hands to dispatch-wrapper / model manual |
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

The manifest is **recall + routing inputs**; the rendered manual (`./manual.md`, pointed to by `invocation_pointer`) is the exact invocation shape, read JIT at first dispatch. The manifest never duplicates the manual's command text — it points to it.

---

## 5. Authoring a manifest

A model package author fills `./manifest-template.yaml` for the package and saves it as `models/{model}/manifest.yaml`. Every required field in §2 must be present with an evidence-traceable value; unvalidated values carry `evidence_status: probe-pending` (package-level or per-variant). Do NOT invent values speculatively — an unknown required value means the package is not ready to ship, not that a placeholder is acceptable.
