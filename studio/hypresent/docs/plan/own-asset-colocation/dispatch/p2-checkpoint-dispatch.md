---
execution_kind: research
executor: claude-code-native
variant: opus
allowlist:
  - "READ-ONLY review dispatch — you create/modify NOTHING except (optionally) running pytest, which writes only pytest/playwright temp artifacts"
commit_policy: none
test_command: python -m pytest tests/test_deck_api.py tests/test_recompose.py tests/e2e/test_pb11_deck_save.py -q  # from the hypresent app dir
forbidden_ops:
  - git push
  - ANY file create/modify/delete (read-only review; pytest temp output excepted)
  - any git write (add/commit/reset)
  - running stamp.py
  - destructive git reset
  - external production API calls
doubt_policy: halt
reviewer: OWNER (the conductor halts to the human after your return)
---

## Goal

---
task_id: p2-checkpoint
status: pending
complexity_score: 6
human_review: required
---

# Checkpoint p2-checkpoint: Final Review
Evaluate the whole feature against the spec — done-gate evidence sufficiency, full test suite green, plan links valid, decisions audit — and obtain user approval to complete the plan.

## Context Files

| File | Purpose |
|------|---------|
| `../decisions.md` | All decisions + discoveries; the audit target |
| `../deliverables.md` | Artifact index — confirm every row delivered at its Path |
| `../specs/own-asset-colocation-spec.md` | The full Behavior + Test Plan to evaluate against |
| `./done-gate-evidence/` | The p2-1 headed evidence to judge for sufficiency |

**Path anchor:** `server/…`/`tests/…` relative to `3-resources/tools/rbtv/studio/hypresent/`.

## Work to Evaluate

The complete feature: own-asset copy + collision rename/rewrite (`server/deck_api.py`, maybe `server/recompose.py`), unit tests, the headed done-gate evidence, and the e2e regression assertion.

## Review Criteria

Evaluate each; note PASS / FAIL / needs-attention:

1. Done-gate evidence proves spec Test Plan row 7: a real deck copy's own images render in the builder reopen AND the editor, and the collision case shows the correct image — each backed by an evidence file on disk (not prose); timings plausible.
2. Full suite green, re-run now (not a stale log): `pytest tests/test_deck_api.py tests/test_recompose.py tests/e2e/test_pb11_deck_save.py -q` EXIT 0.
3. Spec invariants intact: library behavior unchanged; non-colliding sections + separators byte-identical (existing faithfulness tests green); collisions never render the wrong image.
4. `p2-refs` validated: all internal plan links resolve; intra-plan refs are file-relative; `server/…`,`tests/…` are app-relative; no absolute/root-relative self-reference to the plan folder.
5. Scope held — no library-ref rewriting, no full-asset-tree copy, no speculative options ("don't overengineer" honored); diff is proportionate.
6. `decisions.md` audit: entries are decision + rationale + scope only — no file-lists, no N→M narratives, append-only; any rewrite carried explicit sanction + the ≥50% size floor. Checkpoint entries record the ruling only.

## Execution Flow

### Phase: Evaluate
1. Read all Context Files; read `decisions.md` end-to-end and `deliverables.md`.
2. Re-run the full suite yourself; inspect the done-gate evidence files; run the `p2-refs` link checks.
3. Prepare a findings summary with per-criterion PASS/FAIL.

### Phase: Gate
1. Present findings with clear PASS/FAIL per criterion.
2. Append the Human Review Presentation block — point the user at the done-gate evidence and the `deck_api.py` collision logic; surface red/yellow flags from evidence (criterion FAILs, implausible timings, any `unexercisable` claim). If none, write "None identified" + a one-line rationale.
3. **HALT for human approval** — do not advance regardless of findings.
4. If rejected: document feedback in `decisions.md`; do not complete.
5. If approved: stamp complete (run from the vault root; `<plan-dir>` = this plan's folder, holding the plan file + `deliverables.md`):
   `python 3-resources/tools/rbtv/orchestration/skills/orchestrating/scripts/stamp.py --plan-dir <plan-dir> --task p2-checkpoint --status completed --scope worker`
   Then remove `#wip` from this task's line in `2-areas/rbtv/rbtv-tasks.md` and mark the source task done.

> `decisions.md` entries: decision + rationale + scope ONLY (+ optional one-word `compoundable` marker for harvest-worthy findings) — never file-lists or N→M narratives; supersede by appending, never rewrite.

## Context Snapshot

- Workspace root: `C:\Users\henri\Documents\second-brain`. Hypresent app dir: `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\`. Plan folder: `…\studio\hypresent\docs\plan\own-asset-colocation\`. ALL Context-File relative paths in the task body anchor there.
- This dispatch BATCHES `p2-refs` + the `p2-checkpoint` EVALUATE phase. You also perform p2-refs: verify every internal link in `own-asset-colocation-plan.md`, `decisions.md`, `deliverables.md`, the spec, and the phase task files resolves on disk; intra-plan refs file-relative (`./`, `../`); `server/…`/`tests/…` app-relative; report any broken/non-conforming link.
- Run state you must weigh (read `../decisions.md` + `../run-log.md` is NOT yours to read — decisions.md only): phase 1 committed `3ce0400`; p2-1 done-gate proved disk-colocation + EDITOR render; the "render in BUILDER" criterion was ruled structurally unexercisable (pre-existing srcdoc `<base>` gap — decisions.md 2026-06-12 entry); p2-3 root-caused the owner's failed save to an assets-less source deck (handler + live path CORRECT — evidence `./done-gate-evidence/2026-06-12-p2-3-live-save-bug.md` + `p2-3-live-payloads.jsonl` + `p2-3-repro-results.json`); p2-2 added the e2e regression test (`test_pb11_deck_save.py`, 9/9 green).
- Known pre-existing flakes you must NOT count against criterion 2 (they are outside the named three-file suite anyway): `test_f5_comments.py::test_tagging_does_not_move_marker`, `test_r2_resize_real.py::test_control_box_aligns_with_target`.
- Criterion 1 nuance: judge "render in the builder reopen" against the decisions.md `unexercisable` ruling — evaluate whether that ruling is sound, do not blindly FAIL the criterion.

## Allowed Paths

NONE — read-only review. You run pytest (which writes its own temp artifacts) and read files. You do NOT edit the plan, decisions.md, deliverables.md, code, or tests. If you find a defect, REPORT it in your return; do not fix.

## Forbidden Paths

All writes. Also: do not read `run-log.md` or `state-capsule.md` (conductor surfaces).

## Implementation Requirements

- Execute the task body's Evaluate phase + p2-refs only. Phase Gate steps 2-5 (human presentation, halt, stamp, vault-task close) are the CONDUCTOR's — your job ends at returning the findings.
- Re-run the suite YOURSELF from the hypresent app dir: `python -m pytest tests/test_deck_api.py tests/test_recompose.py tests/e2e/test_pb11_deck_save.py -q` — record EXIT + WALL_MS. No server should be left running afterward (kill any process you start).
- Inspect the done-gate evidence FILES on disk (p2-1 sheet + screenshots + the p2-3 sheet/payloads) — judge sufficiency from the files, not from prose summaries.
- Produce per-criterion PASS / FAIL / needs-attention for criteria 1-6, plus the p2-refs link-check result, plus a Human Review Presentation block (red/yellow flags from evidence, or "None identified" + one-line rationale) the conductor can hand to the owner verbatim.

## Validation

`validation` field carries: the pytest command + EXIT + WALL_MS; the count of links checked and failures; the list of evidence files inspected.

## Commit Rule

`commit_policy: none` — no git writes of any kind.

## Return Format

<conductor fills this section>

### Invocation note (Agent-tool dispatch)

Agent-tool dispatch — no CLI invocation; the prompt is the Agent tool's prompt parameter.

> This is an in-session sub-agent carrier. There is no process, no flags, no stdin/stdout surface.


## Pre-Dispatch Hook

A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — default no-op, always passes. Review 5 supplies the verify-or-supply body.


---

## Run-Binding Header (derived from dispatch-wrapper card + model delta)

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
