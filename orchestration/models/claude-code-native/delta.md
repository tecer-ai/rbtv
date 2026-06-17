# `claude` (Agent-tool) package delta

Per-model delta for the **claude** Agent-tool worker — **Claude as an in-session sub-agent** dispatched via the Agent tool (the Task tool), NOT as a process. This is the DEFAULT carrier for a Claude tier (routing card §4): when the boundedness tree picks a mid- or top-tier Claude, the default carrier is an Agent-tool sub-agent. Use `claude -p` (the sibling `../claude-code-cli/` package) instead ONLY when a process-boundary sub-conductor is needed (the worker must itself drive CLI workers — the nesting wall forces a process) or when native workspace-rule loading is required.

This package is a **SIBLING to `../claude-code-cli/`, not a replacement.** The two Claude carriers are deliberately distinct manifest rows so the conductor evaluates each as its own agent. This package's ABSENCE was the "Claude collapses to one entity" gap: `claude-code-cli` modeled `opus`/`sonnet` variants while the Agent-tool tiers had no manifest at all, so a deterministic selector could not enumerate them. (Decision: `1-projects/rbtv-evolution/orchestration/api-workers/api-workers-build/decisions.md` — "Claude-tier modeling", 2026-06-09.)

**Carrier differences from claude-code-cli (this delta mirrors claude-code-cli's SHAPE but differs on every one of these):**

| Carrier point | Agent-tool `claude` (this package) | `claude-code-cli` (sibling) |
|---------------|------------------------------------|------------------------|
| Transport | An **Agent/Task tool CALL** — no command, no flags, no stdin | A `claude -p` **CLI subprocess** with flags + redirected stdin |
| Workspace rules | **NOT inherited** — the sub-agent loads NO `CLAUDE.md`/rules/skills; the parent inlines what it needs | **Natively auto-loaded** — `claude -p` loads the cwd workspace `CLAUDE.md` and obeys it |
| Auth | **`method: none`** — the conductor IS Claude; no login/key pre-flight | `cli-login` — a one-time interactive `claude` login on a fresh machine |
| Nesting | **Hard wall** — a sub-agent CANNOT spawn sub-agents (depth cap ≤ 2) | A process CAN sub-conduct via further CLI subprocesses (one-level) |
| Resume | **`none`** — re-dispatch a fresh sub-agent with the resolution inlined | `session-id` — `--resume <session_id>` continues the same session |
| Return channel | **The five return fields ARE the sub-agent's final reply** — no file channel required | The JSON envelope's `result`; a durable copy needs `--output-format json > file` |
| Web | **`web_access: false`** native — web ONLY via the `rbtv-web-searching` skill named in the prompt | `web_access: true` — native WebSearch/WebFetch + the skill |

**Cost note:** an Agent-tool Claude sub-agent runs on the SAME Claude account/budget as the conductor. Selecting it buys **in-session orchestration** (no process boundary, no auth, no guidance-file dependency) — NOT a cheaper provider. There is **no cost arbitrage** here (contrast kimi/codex, which move work to a cheaper provider). Route to the Agent-tool carrier for the capability, not to save money.

The render script (`../render-manuals.py`) composes the generic wrapper (`{rbtv_path}/orchestration/skills/orchestrating/cards/dispatch-wrapper.md`) with the sections below into `./manual.md`. Edit Agent-tool Claude behavior HERE; never in the rendered manual.

<!-- RENDER:DELTA model-binding-delta -->
**Agent-tool-Claude-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What the Agent-tool Claude sub-agent is bound to |
|------------|---------------------------------------------------|
| **Rules are NOT inherited — the parent INLINES every needed rule and skill directive** | An Agent-tool sub-agent does NOT load the workspace `CLAUDE.md` / rules / skills (the carrier difference from `claude-code-cli`). The dispatching conductor MUST inline into the prompt: every task-specific fact AND every rule/skill the task triggers, each named in imperative form ("invoke `<skill>` before any web work and follow it exactly" — the `rbtv-sub-agents` mandate). A sub-agent given no skill directive silently skips skills it would otherwise invoke. |
| **Confinement is the conductor's job — the allowlist is passed IN THE PROMPT, not a flag** | There is NO `--work-dir` / `--add-dir` / `--allowedTools` for an in-session sub-agent. Bound the sub-agent by (a) stating the file allowlist (✚ create / ✎ modify / ✗ delete) in the prompt as the complete write surface, and (b) the mandatory post-run `git diff --name-only HEAD` of every changed path vs the task allowlist — the only reliable write enforcement. Out-of-allowlist edit = halt + surface; never auto-revert silently. |
| **Workspace-root-absolute write paths — verify each landed on return** | A sub-agent resolves relative paths from its OWN working directory, which is NOT guaranteed to match the parent's; a bare `subdir/file.md` silently lands in the wrong tree. Give EVERY create/move path as workspace-root-absolute (or fully absolute) in the prompt, and after the dispatch returns VERIFY each claimed file exists at its intended absolute path — the sub-agent's success report is not proof the file landed (`rbtv-sub-agents` file-path hygiene). |
| **Nesting wall — a sub-agent does NOT dispatch its own sub-agents** | An Agent-tool sub-agent CANNOT spawn sub-agents (documented 4×; depth cap ≤ 2 from the root conductor). NEVER write a dispatch that asks the sub-agent to fan out its own Agent-tool sub-agents — it cannot. A second conductor level needs a PROCESS boundary (the `claude-code-cli` package), not deeper Agent nesting. |
| **No self-commit unless the task grants it (default OFF)** | An Agent-tool Claude sub-agent does NOT commit by default — the conductor commits via a separate commit worker invoking `rbtv-commit` (routing §3 commit pin). A sub-agent MAY commit locally — and ONLY locally — after its declared validation passes, ONLY when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the stated allowlist, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one. |
| **Return BEGINS with `status:` on line 1 — zero preamble** | The final reply's VERY FIRST line is the `status` field — the reply opens literally like `status: DONE` (or `status: BLOCKED`, etc.), then the remaining four fields. No greeting, no summary, no "I've completed the task…" prose before it: anything ahead of `status:` is a return-schema violation the conductor re-exercises rather than accepts. Example-anchored because prose pins alone do not hold (token-efficiency-refactor, 2026-06-10: 8 of 9 Agent-tool returns opened with preamble despite escalating pins) — a correct return's first characters are exactly `status: `. |
| **Stay alive for long commands — never background-and-end-turn** | A command longer than a single tool-call timeout is launched DETACHED with output redirected to capture files, and the sub-agent STAYS ALIVE polling synchronously (short foreground checks of PID / capture-file growth) until the command exits — the turn ends ONLY with the final five-field return ready. NEVER background-and-end-turn to "await a monitor notification": an Agent-tool worker has NO post-turn existence, so ending the turn KILLS its children (a detached ~17-min gather died at turn-end with 0-byte captures, the dispatch returning mid-work prose instead of the schema). Background-and-await-notification is a CONDUCTOR / CLI-session pattern only. |
<!-- RENDER:DELTA-END model-binding-delta -->

<!-- RENDER:DELTA model-transport-note -->
**Agent-tool Claude return surface — the five return fields ARE the sub-agent's final reply (no separate file channel required).** Unlike `claude-code-cli` (which returns a JSON envelope whose `result` carries the fields, optionally captured to a file with `--output-format json > path`) and unlike the API workers (which write a `return.json` into `--output-folder`), an Agent-tool sub-agent has **no process and no file channel** — it ENDS its run by emitting the five return fields (`status`, `landed`, `validation`, `concerns`, `open_questions`) as its **final assistant message**, which the Agent tool hands straight back to the conductor. There is no envelope to parse and no output-folder to read: the parent agent reads the sub-agent's text output directly.

Consequence for confinement and durability:
- **No envelope ⇒ no machine-parseable status field** — the conductor reads the five fields from the returned prose. Treat the return as a HINT, never the truth: a final-turn drop is possible (the generic worker lossy-return class — CLI and API workers share it). On any garbled/absent return, **reconcile from disk**: `git status` / `git log` of the work-dir + the cited evidence files. **Disk wins on any disagreement.**
- **Durable-return option (when a known-path artifact is needed):** instruct the sub-agent to ALSO write its five fields to an evidence file INSIDE the allowlist (e.g. a done-gate evidence sheet) — but this is the sub-agent doing a normal in-allowlist file write, NOT a transport requirement. The default return needs no file at all.
- **Ground truth is the on-disk result + the conductor's own diff check, not the sub-agent's prose claim of success** — the conductor reconciles every return against `git status` / `git log` and runs the post-run `git diff --name-only HEAD` vs the allowlist before treating the dispatch as done.
<!-- RENDER:DELTA-END model-transport-note -->

<!-- RENDER:DELTA invocation -->
The Agent-tool Claude dispatch manual — how the conductor dispatches an in-session sub-agent. **There is NO CLI invocation: no command, no flags, no stdin, no `--output-format`.** A dispatch is an **Agent/Task tool call** whose `prompt` parameter carries the entire self-contained task (header + payload + inlined rules/skill directives). The five return fields come back as the sub-agent's final reply.

### Canonical dispatch shape (NO command line)

A dispatch is a single Agent tool call:

| Tool parameter | What the conductor supplies |
|----------------|------------------------------|
| `description` | A short (3–5 word) label for the dispatch |
| `prompt` | The COMPLETE self-contained task: the generic binding header + the task payload + every task-specific fact inlined + every triggered rule/skill named in imperative form + the file allowlist + the five-field return schema. The sub-agent reads NOTHING from conversation history and loads NO workspace rules — everything it needs is in this parameter. |
| `subagent_type` | The sub-agent type the harness exposes (e.g. a general-purpose type); the routed VARIANT (`opus` / `sonnet`) is the model tier the conductor selects for the dispatch, per the routing table below |

There is **no `$null |` stdin redirect, no `-p`, no `--model` flag, no `--permission-mode`, no `--add-dir`** — those are `claude-code-cli` surfaces. The Agent tool call is always in-session and non-interactive; the tool parameter IS the prompt; the conductor's own session permissions govern the sub-agent's tool access.

### Pre-flight (before any dispatch)

| Check | How | Gate |
|-------|-----|------|
| **Skill/rule directives inlined** | Scan the installed skill list for every skill the task triggers — any source, matched on each skill's description — and confirm each match is NAMED in imperative form in the prompt, with its workspace-root-absolute path (`rbtv-sub-agents` Pre-Dispatch Gate) | Any matching skill not named → STOP and rewrite the prompt before dispatching. A sub-agent does not auto-discover reliably and inherits no rules. |
| **Write paths are workspace-root-absolute** | Every ✚ create / ✎ modify / ✗ delete path in the prompt is workspace-root-absolute (or fully absolute), with the workspace root stated explicitly | A bare relative write path → rewrite it absolute before dispatch (a sub-agent resolves relatives from its own cwd). |
| **Allowlist stated as the complete write surface** | The prompt declares the disjoint file allowlist as the ONLY paths the sub-agent may touch | Missing/ambiguous allowlist → tighten it before dispatch; confinement is the conductor's job. |
| Auth | (none — the conductor IS Claude) | NO auth pre-flight — an in-session Agent-tool dispatch needs no login or key (contrast `claude-code-cli`'s `cli-login` and the API workers' `api-key`). |
| Guidance file | (none — NO mirror, NO native load) | NO-OP for this package: an Agent-tool sub-agent loads NO workspace guidance file and there is no mirror to verify. The obligation moves to "inline the needed rules/skills into the prompt" — covered by the first row. |

### The dispatch — an in-session Agent-tool sub-agent

The Agent tool runs the sub-agent to completion in-session and returns its final reply. The sub-agent:
- operates with the **conductor's tool set** (Read/Edit/Write/Bash/Grep/Glob/Skill) — there is no independently configured tool surface and no per-dispatch tool-family flag;
- has **NO native web** (`web_access: false`) — web is reachable ONLY if the prompt names the `rbtv-web-searching` skill (the in-session web path);
- inherits **NO workspace rules** — it is bound ONLY by what the prompt inlines;
- **cannot spawn its own sub-agents** (the nesting wall) — it is a leaf.

**Prompt packaging (Shape — single inline parameter):** the composed header + payload + inlined rules/skill directives + allowlist + return schema are passed inline in the `prompt` parameter. A large task is still a single inline parameter (there is no prompt-file arg for the Agent tool — that is a `claude-code-cli` mechanism). The same composed prompt is the reuse surface if a fresh re-dispatch is needed after a halt.

### Model selection → variants

The claude manifest declares two routable variants — route on `(claude, variant)`:

| Variant | Tier | When |
|---------|------|------|
| `opus` | `reasoning: 7`, `coding: 6`, `cost: 6` | Judgment-dense work and cross-artifact coherence; the unbounded leaf of the boundedness tree; the external-CLI **code-review reviewer floor** (reviewer for kimi/codex code is Opus — route it here). Max-reasoning Claude. |
| `sonnet` | `reasoning: 6`, `coding: 5`, `cost: 5` | Partially-bounded work with `doubt_policy: halt`, and zero-context verification personas (recon, research, cold-verify, commits). The default routable Agent-tool Claude variant; the carrier for the commit worker (an Agent-tool sonnet invoking `rbtv-commit`). |

**haiku is NOT a routable variant** (vault routing floors at sonnet absent a user-approved delegation map naming haiku — routing card §7 Haiku-clause). The cheapest NON-HAIKU Claude tier this package ships is `sonnet`; route a mechanical Agent-tool batch there unless an approved delegation map names haiku.

### Confinement — the conductor's job (no process scoping)

An Agent-tool sub-agent has NO process-level directory scoping; there is no native per-path write allowlist. Bound a sub-agent by combining:

| Control | Mechanism |
|---------|-----------|
| Write scope | State the disjoint file **allowlist** in the prompt as the complete write surface (✚ create / ✎ modify / ✗ delete). There is no `--work-dir` / `--add-dir` flag. |
| Tool surface | The sub-agent operates with the conductor's tool set; restrict by inlining "touch ONLY these paths / do ONLY this" in the prompt. There is no `--allowedTools` / `--disallowedTools`. |
| Read confinement | Inline the required context into the prompt; the sub-agent reads nothing from history and loads no workspace rules. |
| **Write confinement** | **Post-run `git diff --name-only HEAD` of every changed path against the task `allowlist`** — the ONLY reliable enforcement. Out-of-allowlist = halt + surface; NEVER auto-revert silently. |
| Path hygiene | Workspace-root-absolute write paths in the prompt; verify each file landed at its intended absolute path on return. |
| Commit / push | Local-only by policy (`commit_policy: local-only`) or none; verify git state shows no push since dispatch. |

### Return handling

| Situation | Conductor action |
|-----------|------------------|
| Sub-agent returns the five fields, `status: DONE` | Reconcile against disk (`git status` / `git log` + cited evidence files), run the post-run `git diff --name-only HEAD` vs allowlist, then proceed to the verification card. The prose is a HINT; the on-disk result + the diff check are ground truth. |
| `status: DOUBT_ESCALATED` / `NEEDS_CONTEXT` | The sub-agent halted with a precise question. Resolve it, then **RE-DISPATCH a fresh sub-agent** with the resolution inlined into the prompt — there is NO session-resume path (`resume_support: none`). The composed prompt is the reuse surface. |
| `status: BLOCKED` | Read the blocker, fix the precondition, re-dispatch fresh. |
| Garbled / absent return (final-turn drop) | Reconcile from disk: verify on-disk state against the task's Implementation Requirements, run the declared validation/smoke checks, verify allowlist + forbidden-ops compliance. If work landed cleanly inside the allowlist but the return was lost, treat it like the disk-recovery class — verify, then either accept the landed work (re-running validation independently) or re-dispatch; never blind-retry over already-landed changes. |

### Disk-state recovery (work landed, return lost) — judgment-only

A final-turn drop on a long dispatch is possible (the generic worker lossy-return class — `claude-code-cli` / codex / kimi share it). Valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: the sub-agent returned with NO structured five-field reply (or a garbled one); `git status --porcelain` shows uncommitted changes inside the allowlist; `git log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared validation / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: files verified + smoke result, the recovery commit hash, why not re-dispatching, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Prefer a fresh re-dispatch** (the composed prompt is the reuse surface) over recovery when on-disk state is partial or ambiguous — there is no session to resume, so a clean re-dispatch is often simpler than disk surgery.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Sub-agent skips a skill it should have invoked | It inherits NO workspace rules — NAME every triggered skill in the prompt in imperative form (`rbtv-sub-agents` Pre-Dispatch Gate); a mention is insufficient. |
| Bare relative write path lands in the wrong tree | Give workspace-root-absolute write paths in the prompt; verify each file landed at its intended absolute path on return. |
| Designed to nest its own sub-agents | The nesting wall blocks it (depth cap ≤ 2). For a second conductor level use the `claude-code-cli` process boundary, not deeper Agent nesting. |
| Research leaf routed here with no web directive | `web_access: false` natively — name `rbtv-web-searching` in the prompt for the in-session web path, or route the leaf to a web-capable worker. |
| Treating the returned prose as truth | The five fields are a HINT; reconcile against `git status` / `git log` + disk and run the post-run diff-vs-allowlist; disk wins. |
| Attempting to resume a halted sub-agent | `resume_support: none` — there is no session handle; re-dispatch a fresh sub-agent with the resolution inlined. |

### The Agent-tool Claude task contract (plugs into the shared authoring core)

An Agent-tool-Claude-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with Agent-tool-specific frontmatter and body sections. The conductor validates an `executor: claude` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis/review for a read-only or verification leaf
executor: claude-code-native                # the Agent-tool carrier (contrast executor: claude-code-cli for the process carrier)
variant: opus | sonnet          # the routed variant — opus for judgment/code-review, sonnet for mid-tier/verification/commits
allowlist:
  - <workspace-root-absolute file-or-folder path>   # the complete write surface; there is no --work-dir flag
commit_policy: local-only | none       # none = conductor commits via a separate rbtv-commit worker
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - spawning sub-agents          # the nesting wall — an Agent-tool sub-agent cannot nest
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for external-CLI code is Opus — non-overridable
```

(There is NO `permission_mode`, `allowed_workdir`, or `--add-dir` field — those are `claude-code-cli` surfaces. Confinement is the prompt's allowlist + the conductor's post-run diff.)

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (ALL task-specific context inlined — the sub-agent reads nothing from history AND loads no workspace rules, so inline both the task facts AND every triggered rule/skill directive) · Allowed Paths (the workspace-root-absolute allowlist) · Forbidden Paths · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact checks the sub-agent runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema — emitted as the final reply; optionally ALSO written to an in-allowlist evidence file for a durable copy).

**Review gates** every Agent-tool Claude coding task passes (verification card owns the gate): sub-agent self-report → conductor diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until the owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". When an Agent-tool Claude sub-agent is itself the cold verifier or reviewer, it floors at the `opus` variant and receives ONLY the contract criteria + the running artifact, never the builder's claims (the verification card's adversarial pattern).

### Recipes (Agent-tool dispatch shapes — NOT command lines)

```text
# Bounded write dispatch, sonnet, allowlist-confined:
Agent tool call:
  description: "build module X"
  subagent_type: <general-purpose type>
  prompt: |
    <generic binding header>
    <task payload: Goal, Context Snapshot (all facts inlined), Implementation Requirements>
    Allowed paths (workspace-root-absolute, the COMPLETE write surface):
      - C:/.../<repo>/<file-or-folder>
    Forbidden: git push, writes outside allowlist, spawning sub-agents.
    <every triggered skill named imperatively, e.g.:>
    Invoke `rbtv-commit` before committing and follow it exactly.   # only if commit_policy grants it
    Return EXACTLY the five fields (status, landed, validation, concerns, open_questions) as your final reply.
  # routed variant: sonnet (mid-tier)
```

```text
# Judgment-dense / cold-verify dispatch, opus:
Agent tool call:
  description: "cold-verify feature Y"
  subagent_type: <general-purpose type>
  prompt: |
    <ONLY the contract criteria + the running artifact location — never the builder's tests/claims/sheet>
    Re-exercise each criterion at the fidelity floor on the running artifact; capture evidence files on disk.
    Return EXACTLY the five fields as your final reply; cite each evidence file by absolute path.
  # routed variant: opus (reviewer/verifier floor)
```

```text
# Research leaf — web via the rbtv-web-searching skill (no native web):
Agent tool call:
  description: "research topic Z"
  subagent_type: <general-purpose type>
  prompt: |
    Invoke the `rbtv-web-searching` skill before any web work and follow it exactly.
    <self-contained research brief: question, scope, integration target>
    Return EXACTLY the five fields as your final reply.
  # routed variant: sonnet (research leaf)
```
<!-- RENDER:DELTA-END invocation -->
