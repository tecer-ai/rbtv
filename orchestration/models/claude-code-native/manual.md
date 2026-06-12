<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/claude-code-native/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `claude-code-native` package delta `orchestration/models/claude-code-native/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> claude-code-native-specific behavior, edit the delta. Then re-render:
>
> ```
> python orchestration/models/render-manuals.py
> ```

## 1. Task packaging — the dispatchable unit

The unit sent to a worker is a **self-contained task artifact** (it already satisfies §1–§7 of the task-file contract — this card does not re-author it) composed with the run's binding context. Composition is **header + payload**, never a rewrite of the task file.

| Element | Rule |
|---------|------|
| **Payload = the task file, verbatim** | The dispatched prompt carries the task file's content unedited and untruncated. The worker reads NOTHING from conversation history — the artifact IS the brief. Editing the task body at dispatch time is forbidden; if the task is wrong, fix the task file (and log the amendment), then re-dispatch. |
| **Header = run-binding context** | Prepend only what the worker needs that is not already in the task file: the binding addendum (§2), the return schema (§3), the run's worker-facing `decisions.md` pointer (or its inlined relevant entries), and — for a research leaf — the `rbtv-web-searching` directive in imperative form. The header is composed; the payload is verbatim. |
| **Prompt-file reuse** | For workers driven by a prompt file (CLI workers, and Agent-tool dispatches large enough to warrant it), write the composed header+payload to a prompt file on disk and dispatch FROM that file. The same prompt file is the reuse surface on resume — re-dispatch reads the file, it is not re-composed from memory. |
| **In-session CLI spawns BEGIN with the worker binary (D17)** | A CLI dispatch issued from inside a Claude session is permitted by PREFIX allowlist rules (`Bash(<bin>:*)` / `PowerShell(<bin>:*)`, installer-managed from the package manifest's `permission_rules`) — they match ONLY a command line that BEGINS with the worker binary. A leading `cd …`, an inline env assignment, or a `cat …\|`/`Get-Content …\|` stdin pipe breaks the match and the spawn falls to the permission classifier, which denies in-session yolo spawns. So: run from the conductor's CWD (pass the work-target via the model's add-dir flag, never a leading `cd`), set env vars in a SEPARATE prior statement, and hand a large brief to the worker as a SHORT positional/file-pointer prompt naming the prompt file — never a stdin pipe. Pipe and env-prefixed forms remain functionally valid ONLY for owner-typed `!` dispatches (those bypass the session classifier). Each model's delta carries its binary-first shape. |
| **Launch-root = orchestrator root; work-target via add-dir (G1)** | ALWAYS launch a CLI worker with its guidance-root = the **orchestrator root** (the workspace the conductor runs from, where the full rules/skills mirror lives) and pass the actual **work-target** separately via the model's add-dir flag. The per-model launch-root flag comes from the model's delta (claude-cli/qwen/codex key guidance to CWD/`-C`; kimi to `--work-dir`). NEVER root the worker at the work-target when the work-target is a nested repo: the mirror skips nested git repos BY DESIGN, so a worker rooted there loads ZERO behavior-rules and operates blind (the a3e217d incident — a bare kimi self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo). State the split explicitly to the worker in the dispatch: "your rules load from your launch root; create/modify files ONLY inside `<work-target>` per the allowlist". Two caveats the conductor owns: (a) the post-run confinement diff MUST run in the **work-target's git** — `git -C <work-target> diff --name-only HEAD` — never in the launch-root's git (a nested-repo work-target has its own git; a launch-root diff passes vacuously); (b) the work-target's OWN local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from an add-dir — inline the load-bearing ones into the dispatch or mark the file `[FULL READ]`. |
| **One dispatch = one bounded task (or one disjoint-allowlist batch)** | Routing sized the batch (30–90 min, disjoint allowlists for parallel workers). This card packages exactly that unit — never silently merge two tasks into one dispatch. |

### Reference-doc inlining (D21)

A task references other documents. The conductor decides per referenced doc whether the worker reads the source or receives an inlined excerpt — and MARKS each reference so the worker knows which:

| Reference kind | Mark | Worker behavior |
|----------------|------|-----------------|
| **Inlined** | `[INLINED]` | The relevant excerpt is pasted into the header under a labelled heading (`### {Doc} — {Section}`, with source path). The worker treats the excerpt as authoritative and does NOT re-read the source unless escalating a doubt. |
| **Full read** | `[FULL READ]` | The worker opens the source itself via its file tool when it needs the content. |

Inlining rules:

| Rule | Detail |
|------|--------|
| Inline frozen-doc and credential excerpts — never grant read access | A frozen reference doc or a credentials path is inlined as the needed excerpt; the worker is NEVER given a read path into it. (Mirrors routing's pre-staging rule: judgment over external files → extend read surface; mechanical need of a fixed excerpt → inline/pre-stage it.) |
| Inline what is small and load-bearing; point to what is large | A short contract clause the work hinges on → inline it. A large design doc the worker may need parts of → `[FULL READ]` with the exact section named. Budget per the task-file contract's context budgets — a task whose inlined context will not fit gets split, not truncated. |
| Each inlined excerpt is standalone | Do not assume cross-references between excerpts unless stated; label each with its source so a doubt-escalation can find the full doc. |
| API-worker dispatch is ALL-`[INLINED]` | An API worker has no file-read tool — it can never do a `[FULL READ]`. EVERY reference in an API-worker dispatch MUST be `[INLINED]`; the runner inlines each `--target-file` into the request. The whole composed prompt is bounded by the variant's `context_window` — a dispatch that won't fit must be SPLIT, never handed off as a path for the worker to read. |
## 2. The binding addendum — worker obligations

Every dispatch carries this addendum in its header. These are the obligations the worker is held to regardless of model; they are the conductor's enforcement contract on return. State them imperatively in the dispatch ("you MUST…", "return…", "do NOT…") — never permissively.

| Obligation | What the worker is bound to |
|------------|-----------------------------|
| **Return-schema compliance** | Return the named-field schema in §3 exactly — every field, no field renamed, none invented. The conductor parses these fields; a prose-only return is a contract violation that triggers re-exercise of the return, not acceptance. |
| **Allowlist boundary** | Create / modify / delete ONLY the files in the task's allowlist. Out-of-allowlist file ops are not silently wrong but are NOT silent — they force conductor review (the conductor diffs actual changes against the allowlist on return). State the allowlist in the dispatch even though the task file also carries it. |
| **Halt / doubt policy** | On ambiguity the task does not resolve, HALT and return `DOUBT_ESCALATED` (or `NEEDS_CONTEXT`) — never guess, never improvise past a doubt. A fully-bounded task should contain no ambiguity; if the worker hits one, the task was under-specified and the conductor needs to know. |
| **Evidence-file requirement** | Capture validation evidence as FILES on disk during the work (command output, logs, screenshots for UI), not as prose claims in the reply. For CLI workers the return message is lossy at session end (documented: a completed dispatch returned a garbage final message while the commit had landed) — evidence on disk is what survives. The `validation` field cites what was run; the captures are the proof. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). An authorized self-commit MUST be **pathspec-scoped to the allowlist**: stage with `git add <allowlist-paths>` and commit with `git commit -- <allowlist-paths>`; `git add -A`, `git add .`, and a bare `git commit -a` are FORBIDDEN regardless of authorization — an unscoped self-commit sweeps foreign uncommitted files into the commit (the a3e217d defect class: 5 foreign files swept by one bare kimi self-commit). The dispatch INLINES the exact pathspec-scoped commit command when self-commit is granted. |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your **launch root** (the directory your guidance keys to: your CWD/`-C` root, or kimi's `--work-dir`; under orchestration this is the orchestrator root, NOT the work-target) for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at that root (`AGENTS.md` for a Codex/Kimi worker, `QWEN.md` for a qwen worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the launch root has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **kimi and qwen do NOT** — kimi needs an enumerated Step-0 naming the read, and qwen ignores even imperative directory-read prose unless the dispatch invokes its `QWEN.md` preamble by name OR names the specific rule files (qwen delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker with a mirror-equipped launch root, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

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
<!-- The model package delta inserts its model-specific binding obligations here. -->
## 3. The unified return schema (D8)

ONE schema for EVERY worker — bounded CLI worker, mid-tier Claude, top-tier conductor-grade Claude, research worker. The fields are FIXED: the schema is named-field precisely because prose returns drift (resumed long-context sessions favored conversational summaries over the contract — five instances in one session). Named fields are the conductor's parse surface and the substrate the tripwire field-checks (§4) run against.

The worker returns exactly these five fields:

| Field | Content |
|-------|---------|
| **`status`** | EXACTLY one of: `DONE` · `DONE_WITH_NOTES` · `BLOCKED` · `DOUBT_ESCALATED` · `NEEDS_CONTEXT`. No other value is valid. |
| **`landed`** | What actually changed on disk: files created/modified/deleted, and the commit hash(es) if the worker committed. This is the claim the conductor reconciles against `git status` / `git log`. |
| **`validation`** | Each validation performed: the command run, its `EXIT` code, its `WALL_MS` (wall-clock duration), and any skipped check WITH its reason. The sub-field `SKIPPED_COUNT` carries the number of checks skipped (0 when none); any skip it counts MUST carry a per-skip reason — a skip without a reason, or `SKIPPED_COUNT > 0` with no reasons, is a contract violation. Empty validation on a code task is itself a flag. |
| **`concerns`** | Anything the worker noticed that the conductor should weigh — risks, smells, partial confidence, adjacent issues spotted but not fixed. Distinct from blockers: concerns did not stop the work. |
| **`open_questions`** | Questions the worker could not resolve and that bear on this or downstream work. For `DOUBT_ESCALATED` / `NEEDS_CONTEXT` this carries the precise question that halted the work. |

### Status semantics

| Status | Means | Conductor's next move |
|--------|-------|-----------------------|
| `DONE` | Every contracted outcome met; nothing to surface | Reconcile against disk, then proceed (verification card owns the gate). |
| `DONE_WITH_NOTES` | Work landed, but `concerns` / `open_questions` carry items worth the conductor's attention | Reconcile, then weigh the notes before proceeding. |
| `BLOCKED` | Work could not be completed — an external obstacle, a failed validation that the worker cannot resolve | Route recovery (recovery card); do NOT mark the task done. |
| `DOUBT_ESCALATED` | The worker hit an ambiguity and stopped rather than guess; `open_questions` holds the doubt | Resolve the doubt (halt-to-user or a doc-reader), then **resume** per halt-recovery §2 (same CLI session via `-r` where supported; a fresh re-dispatch for an Agent-tool worker that has no session) — never accept a guess in its place. Halt-recovery owns the resume-vs-re-dispatch choice. |
| `NEEDS_CONTEXT` | The task lacked something the worker needed to proceed (a missing file, an unstated decision) | Supply the context (amend the task file + log it), then resume / re-dispatch per halt-recovery §2. |

### Transport — same fields, multiple carriers

The schema is identical across workers; only HOW the fields arrive differs by worker type. This is the one axis the per-model delta touches for the return.

| Worker type | Transport |
|-------------|-----------|
| **Agent-tool helper (Claude sub-agent)** | The five fields ARE the final reply — the sub-agent writes them as its return message; there is no separate file channel required. |
| **CLI worker (`kimi`, `codex exec`, `claude -p`, `qwen`, …)** | The fields appear in the worker's final message AND the evidence they cite is on disk as files. The final message is treated as a HINT; the disk state and the cited evidence files are the truth the conductor reconciles. |
| **sdd composite dispatch (`superpowers:subagent-driven-development`)** | sdd is ONE composite dispatch wrapped by the outer gates (routing §5). Its outer-wrapper return carries the five fields as the in-session final reply — same as the Agent-tool row — over its whole code body; its internal TDD sub-structure is not surfaced as separate returns. |
| **API worker (shared runner `models/_api/run.py`)** | The conductor invokes `run.py` via Bash; the RUNNER writes the deliverable output file(s) AND a `return.json` carrying the five fields into the conductor-supplied `--output-folder`. The conductor reads the output folder + `return.json` — the API model cannot write to the repo, run git, or commit. Same "message is a hint, disk is truth" discipline; here "disk" = the output folder, NOT a git repo (so reconciliation is file-exists + non-empty + envelope-valid, not `git log`). |

**Agent-tool Claude return surface — the five return fields ARE the sub-agent's final reply (no separate file channel required).** Unlike `claude-code-cli` (which returns a JSON envelope whose `result` carries the fields, optionally captured to a file with `--output-format json > path`) and unlike the API workers (which write a `return.json` into `--output-folder`), an Agent-tool sub-agent has **no process and no file channel** — it ENDS its run by emitting the five return fields (`status`, `landed`, `validation`, `concerns`, `open_questions`) as its **final assistant message**, which the Agent tool hands straight back to the conductor. There is no envelope to parse and no output-folder to read: the parent agent reads the sub-agent's text output directly.

Consequence for confinement and durability:
- **No envelope ⇒ no machine-parseable status field** — the conductor reads the five fields from the returned prose. Treat the return as a HINT, never the truth: a final-turn drop is possible (the generic worker lossy-return class — CLI and API workers share it). On any garbled/absent return, **reconcile from disk**: `git status` / `git log` of the work-dir + the cited evidence files. **Disk wins on any disagreement.**
- **Durable-return option (when a known-path artifact is needed):** instruct the sub-agent to ALSO write its five fields to an evidence file INSIDE the allowlist (e.g. a done-gate evidence sheet) — but this is the sub-agent doing a normal in-allowlist file write, NOT a transport requirement. The default return needs no file at all.
- **Ground truth is the on-disk result + the conductor's own diff check, not the sub-agent's prose claim of success** — the conductor reconciles every return against `git status` / `git log` and runs the post-run `git diff --name-only HEAD` vs the allowlist before treating the dispatch as done.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

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
| `opus` | `reasoning_tier: top`, `cost_class: high` | Judgment-dense work and cross-artifact coherence; the unbounded leaf of the boundedness tree; the external-CLI **code-review reviewer floor** (reviewer for kimi/codex code is Opus — route it here). Max-reasoning Claude. |
| `sonnet` | `reasoning_tier: mid`, `cost_class: mid` | Partially-bounded work with `doubt_policy: halt`, and zero-context verification personas (recon, research, cold-verify, commits). The default routable Agent-tool Claude variant; the carrier for the commit worker (an Agent-tool sonnet invoking `rbtv-commit`). |

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
