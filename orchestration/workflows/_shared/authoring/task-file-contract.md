# Task-File Contract

The contract every executable task file MUST satisfy, regardless of which worker executes it. A task file that violates this contract is malformed — the dispatcher halts and reports it rather than inferring missing parts.

Evidence base: 22/22 Kimi tasks landed first-try when the task file was fully self-contained (`learnings-kimi-worker.md` §3); ambiguity became a silent bug every time a field was left to inference.

---

## 1. Self-Containedness — zero context

A task file MUST be interpretable by a worker that has NONE of this conversation, plan history, or "as discussed" knowledge. Inline everything the worker needs; reference another file ONLY when the worker must open it to execute.

| Rule | Why |
|------|-----|
| Inline every interface, edge case, and decision the work depends on | The cheapest capable worker is treated as non-reasoning; what is not stated is guessed |
| Inline EXACT current-code excerpts being modified | The worker anchors edits on the quoted text; a stale/wrong excerpt corrupts the edit |
| **Content anchors, never line numbers** | Line numbers go stale the moment a prior task touches the file — locate by "the block reading `<exact code>`" |
| No "as discussed", "per our earlier" | Another agent was not in the conversation |
| Forbidden-paths / out-of-scope reads stated explicitly | The worker must know what NOT to touch, not only what to touch |

## 2. Granularity

| Rule | Description |
|------|-------------|
| WHAT, not HOW | State the outcome; include HOW only where the user decided it |
| Single action per task | One discrete, independently completable action — never combine actions with "and" |
| Room for judgment | Leave implementation choices to the worker unless the user specified them |
| One bounded dispatch | One module or one coherent slice per task — sized so the worker needs no re-dispatch |
| Self-verifiable acceptance | Give checks the worker can run itself (a syntax check, a one-line probe, a DOM/output assertion) — these correlate with genuinely-done work |

## 3. File-operation verbs

Every file action uses an explicit verb. Format: `[VERB] [path] [with/to/containing] [content description]`.

| Verb | When |
|------|------|
| CREATE | New file that does not exist |
| UPDATE | Modify an existing file |
| DELETE | Remove a file |
| MOVE | Relocate or rename a file |

**MOVE/rename reference completeness.** A MOVE or rename task MUST author its reference-discovery step to find EVERY form a reference to the moved artifact can take in its ecosystem — never only the path form. Enumerate at minimum: **path form** (the old path), **name/symbol form** (the bare identifier in reference contexts — import symbols, `<old>-` prefixes, "the `<old>` X" prose), and **link/import form** (relative links, import statements, config keys). Acceptance MUST confirm every enumerated form returns zero functional hits after the edit. A path-only discovery grep is malformed for a rename task — name-form and broken-link references slip through it. *(Markdown-doc example: a module rename greps `<old>/`, then `the <old> module` / `[<old> module]` / `<old>-module`, then `(./<old>.md)` / `modules/<old>.md`.)*

## 4. File allowlist

Every task carries an explicit allowlist of the files it may create / modify / delete (`✚ create` · `✎ modify` · `✗ delete`). This is the dispatcher's post-run enforcement contract: it diffs the worker's actual changes against the allowlist. Out-of-allowlist ≠ wrong, but it ≠ silent — it means orchestrator review required (`learnings-kimi-worker.md` §4). Repeat the allowlist in human-readable body form even when machine-readable frontmatter also carries it.

## 5. Context budgets

Size the context a task loads; split when it will not fit.

| Context to load | Action |
|-----------------|--------|
| < 50k tokens | Single task, proceed |
| 50–100k tokens | Consider splitting; state the reasoning |
| > 100k tokens | MUST split. A research task splits by producing a ~10–20k summary that downstream tasks consume instead of the raw sources. A non-research over-budget task splits by decomposing into smaller bounded slices (per `dependency-ordering.md`), each under budget — NEVER by truncating inlined context (truncation breaks self-containedness). |

## 6. Acceptance criteria

Acceptance criteria are ALWAYS owner-observable or worker-runnable outcomes — never an internal assertion the worker cannot exercise. Each criterion states the gesture and the visible result: "when done, running `X` produces `Y`" or "the owner opens `Z` and sees `W`". A task whose only "criterion" is "works" or "looks right" is malformed.

### 6a. Runnable-probe authoring discipline

When a task authors machine-runnable probes (verification checklists, acceptance greps, validation commands), the contract REQUIRES all three — a probe authored but never run is presumed broken:

| Requirement | Rule |
|-------------|------|
| **Spot-run every probe before close** | Every authored probe is RUN against the current corpus before the task closes. An un-run suite poisons every downstream checkpoint that consumes it (one run shipped 35 probes; 13 false-failed as written while the corpus was intact). |
| **Alternation carries its engine flag** | A regex-alternation probe (`a|b`) carries the flag that activates alternation (`grep -E`), and the artifact documents its probe-execution conventions in a header the consuming agent reads first. |
| **Patterns copied from the corpus, never recalled** | Every literal pattern is copy-pasted from the actual file text — casing and wording verified against the file, never typed from memory (`Failure modes` vs `Failure Modes`, `dual` vs `deferred capture` each false-failed on recall). |

This moves upstream the discipline the reviewer-side catch-net enforces at review time (verification card §2c, "re-run any count claim"): authoring-time spot-running stops a broken probe before it reaches a single checkpoint.

## 7. Return contract

Every task names the five fields the worker returns — the SAME schema the dispatch-wrapper fixes (`orchestration/skills/orchestrating/cards/dispatch-wrapper.md` §3 is the single source for the exact field names): `status` · `landed` (files changed + commit hash if committed) · `validation` (commands + EXIT + WALL_MS + skips with reasons) · `concerns` · `open_questions` (the precise blocker/doubt when halting). Use those exact field names — do not rename them. The return MESSAGE is a hint; disk state is the truth — the dispatcher reconciles the message against the repo before trusting it (`learnings-kimi-worker.md` §S3.2).

## 8. Per-model contract plug-in seam

This file is the GENERIC contract — model-independent. (This seam is forward-wiring: the model packages it plugs into land in P3 — until a given `orchestration/models/{model}/` package ships, the generic contract §1–§7 stands alone and a task is model-bound at routing time without a delta.) Each model package (`orchestration/models/{model}/`) extends it with a model delta that adds ONLY what that worker needs on top of §1–§7: required frontmatter fields, invocation-specific constraints (workdir, commit policy, swarm policy), and binding dispatch addenda (e.g., the Kimi root-files ban + evidence-file mandate, `learnings-kimi-worker.md` §5). The delta NEVER restates the generic contract — it plugs in. The dispatch-wrapper composes generic contract + model delta at dispatch time. A task authored for a specific model satisfies §1–§7 AND its model delta; a model-agnostic task satisfies §1–§7 and is bound to a model at routing time.

## 9. Execution-level feasibility

A task whose execution flow itself dispatches Agent-tool sub-agents (review fan-outs, parallel-worker waves driven via the Agent tool, any "dispatch N sub-agents" step) MUST be authored as **orchestrator-executed** — it carries `orchestrator_executed: true` in frontmatter and runs at the conductor's (top) level. It is NEVER delegated whole into an executor sub-agent, because Agent-tool sub-agents cannot spawn sub-agents (the nesting wall, `orchestration/skills/orchestrating/cards/routing.md` §4 — "One Agent-tool level"). A sub-agent-dispatching task placed at an executor level is malformed: the dispatcher halts and reports it (Malformed-task rule below) rather than routing it down to fail at the wall.

**Process-boundary exception.** This clause bans Agent-tool nesting, NOT all sub-dispatch. A task that drives CLI workers (`kimi`, `codex exec`, `claude -p`, `qwen`) as separate OS processes is the sanctioned sub-conductor path (depth cap ≤ 2, same routing card §4) — a process is not an Agent-tool sub-agent, so the wall does not apply. Such a task is NOT flagged orchestrator-executed on that basis; the marker keys on Agent-tool sub-agent dispatch specifically.

---

## Malformed-task rule

If any required element above is missing — OR a sub-agent-dispatching task (§9) is authored at an executor level instead of orchestrator-executed — the dispatcher MUST halt and report the malformed task. It MUST NOT infer the missing element into shape or re-level the task itself — authoring is the author's job, not the dispatcher's.
