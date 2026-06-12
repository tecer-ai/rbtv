# Card: Dispatch-Wrapper

Opened when routing has produced an assignment — a chosen (model, variant, agent-type) under its role pins — and a task is about to be sent to a worker. This card packages that assignment into an actual dispatch: how the task is composed for the worker, the binding addendum the worker is held to, and the one named-field schema every worker returns. It is the single source for dispatch packaging — used DIRECTLY as the card for Agent-tool dispatches, and rendered INTO each model's CLI manual at build time (the render script composes this template + the model's delta into a full per-model dispatch manual).

Iron rules it serves (from the core protocol): **no dispatch without a self-contained task artifact** (this card packages an artifact that already satisfies the task-file contract — it never authors one), and **disk = truth: every return is reconciled against repo state** (the return schema and the post-return rule below exist because the message is a hint, not the truth — five resumed-Kimi sessions drifted to prose while the work had landed correctly on disk; the orchestrator caught all five only by verifying `git` state, never the message).

This card is GENERATED-SOURCE. Sections marked with render markers below are consumed verbatim by the manual render script (`{rbtv_path}/orchestration/models/render-manuals.py`); per-model insertion points are named where a model's delta plugs in. Edit packaging behavior HERE — never in a rendered manual.

---

## What this card is NOT

| Not | Where it lives instead |
|-----|------------------------|
| The task-file contract (what a task file must contain) | `{rbtv_path}/orchestration/workflows/_shared/authoring/task-file-contract.md` — authored at intake/planning, BEFORE routing |
| Model-specific invocation shape (the exact CLI command, flags, workdir, exit codes) | The model package delta at `{rbtv_path}/orchestration/models/{model}/` — plugs in at the named insertion points below |
| The routing decision (which worker) | The routing card — produces the assignment this card packages |
| The return GATE (what the conductor does with a return) | The verification card — owns reconciliation, review gates, and the cold verifier |

This card composes the GENERIC dispatch around an already-authored task and an already-chosen worker. It restates neither the task-file contract nor the model deltas — it references them and binds them together.

---

<!-- RENDER:BEGIN generic-packaging -->
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
<!-- RENDER:END generic-packaging -->

---

<!-- RENDER:BEGIN binding-addendum -->
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

<!-- RENDER:INSERT model-binding-delta -->
<!-- The model package delta inserts its model-specific binding obligations here. -->
<!-- RENDER:END binding-addendum -->

---

<!-- RENDER:BEGIN return-schema -->
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

<!-- RENDER:INSERT model-transport-note -->
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->
<!-- RENDER:END return-schema -->

---

## 4. Tripwires as field checks (D8)

Because the return is named-field, evidence-integrity tripwires are mechanical checks against the schema — not prose judgement. Run these on every return before trusting `status`:

| Tripwire | Field check |
|----------|-------------|
| **Phantom commit** | `landed` claims a commit hash → that hash MUST appear in `git log` of the work-dir. Absent → the commit was never made; treat as not-done. |
| **Implausible speed** | `validation` `WALL_MS` is implausibly small for the work claimed (e.g., a full suite reporting near-zero ms) → the check did not really run; re-exercise it. |
| **EXIT codes** | Every `validation` entry's `EXIT` MUST be present and `0` (or an explicitly-explained non-zero the task sanctions). A missing or unexplained non-zero `EXIT` → the gate did not pass; do not accept `DONE`. |
| **Silent skip** | Any `validation` entry skipped without a stated reason, OR `SKIPPED_COUNT` > 0 unexplained → the gate did not pass; do not accept `DONE`. (`SKIPPED_COUNT` is the `validation` sub-field §3 defines for the count of skipped checks.) |
| **Commit-message drift** | A committed task whose commit message dropped the mandated convention string → flag it (the convention is load-bearing for audits), even when the file list is correct. |

The five field checks above are the parseable-return tripwires; the verification card runs them in its §1b table verbatim (same five). One further tripwire — **Message ≠ state** (`landed` / `validation` disagree with `git status` / `git log` → **state wins**, discrepancy logged in `run-log.md` as a drift instance) — is NOT a §1b field check but the repo-state RECONCILIATION verification performs in its §1c (it compares the parsed fields against the live disk, not within the return). It is named here so the worker knows its message is reconciled against disk; verification owns where it runs.

These checks are the field-level form of "disk = truth." The verification card owns when and how the conductor acts on a tripwire; this card's job is to make the return PARSEABLE so the checks are mechanical.

---

## 5. Post-return rule — reconciliation always follows

EVERY return — `DONE` included, resumes especially — is followed by repo-state reconciliation before the return is trusted or logged. The conductor reads the actual disk state (`git status` / `git log` of the work-dir, plus the cited evidence files) and reconciles it against `landed` / `validation`. Message and state disagree → state wins, logged.

This card carries the WORKER-side obligations that make reconciliation possible (the schema, the evidence-file requirement, the allowlist and commit bindings). The CONDUCTOR-side gate — the actual reconciliation step, the review gates, and the cold verifier for development dispatches — is owned by the **verification card**. Packaging a dispatch from this card is incomplete until the return runs through that gate; do not mark a task done on the strength of the return message alone.

---

## 5a. Generating the dispatch — run the scaffold (pre-flight + execution path)

The composition this card defines (§1 packaging, §2 addendum, §3 schema, + the per-model invocation note for a CLI worker) is GENERATED by the dispatch-scaffold, not hand-authored. The scaffold derives every byte of the boilerplate at run time from THIS card + the chosen model's delta on disk — so a dispatch can never drift from the card. This card's text remains the SOURCE the scaffold derives from: **card text wins; a scaffold output that disagrees with the card is a defect to file, never a reason to hand-patch the dispatch.**

### Pre-flight — scripted, runs before any dispatch (pre-spend)

The scaffold runs four scripted pre-flight gates before it writes anything; ANY failure ⇒ EXIT≠0 + a machine-readable error naming the gap, with NO file written (a broken dispatch is caught before spend):

| # | Scripted check | Passes when |
|---|----------------|-------------|
| 1 | **Package installed** | `{rbtv_path}/orchestration/models/{model}/` exists with a `delta.md` |
| 2 | **Manual fresh** | `render-manuals.py --check --model {model}` reports zero drift — the rendered manual is current with the card + delta (a stale manual signals a re-render is owed first; the scaffold reports it, never papers over it) |
| 3 | **Guidance file present** | the model's guidance-file convention resolves for the LAUNCH ROOT — the orchestrator root the worker's guidance keys to, never the work-target (present, or its absence is reported so the conductor mirrors it). This is the guidance-FILE check, NOT the rules-library reach (that is Review-5's hook, no-op by default) |
| 4 | **Output folder exists** | `--output-folder` is an existing directory — the scaffold never creates it |

**Conductor pre-flight hygiene (ADX-1) — these run ALONGSIDE the scripted gates, conductor-side:** any auth/config pre-flight (e.g. confirming an API key resolves, reading a manifest field) queries SPECIFIC non-secret fields ONLY — NEVER dump a whole settings/config file into a command or a transcript (a live key reached a transcript once — a real incident). Secret PRESENCE is checked as a boolean (resolves / does not resolve); a secret VALUE is never echoed, logged, or pasted.

**Capture-bound Manus dispatches (ADX-4):** when the dispatch is a capture-bound Manus task, add the pre-flight line that the prompt MUST demand the complete deliverable in the reply MESSAGE TEXT — an attachment-only return failed live (see the manus delta obligations).

### The execution path — the exact CLI

Run the scaffold from the rbtv repo root (CWD = `{rbtv_path}`):

```
python orchestration/skills/orchestrating/scripts/scaffold.py \
  --model <model> --output-folder <dir> --filename <name> \
  [--instructions <file-or-inline>] [--explain]
```

| Mode | Trigger | What it writes | Conductor then |
|------|---------|----------------|----------------|
| **Skeleton** | NO `--instructions` | the composed header (addendum §2 + schema §3 + decisions pointer + — for a CLI model — the invocation/transport note) + the per-model frontmatter SKELETON + empty body-section HEADERS | fills ONLY task-specific content (Goal / Context / Implementation / allowlist values), then dispatches |
| **Complete** | `--instructions <file-or-inline>` | a COMPLETE dispatchable prompt — the composed header + frontmatter + body with the instructions merged into the task-specific sections | points the worker straight at the file without re-reading the boilerplate |

`--explain` prints the composed source paths + each pre-flight outcome (provenance preview; still writes the file). The scaffold is carrier-aware: an Agent-tool carrier (the `models/claude-code-native/` package) gets the no-CLI composition (no invocation note, zero scraped flags); a CLI carrier derives its flags from its delta's `invocation` section.

### Hand-authoring is the FALLBACK only

Compose a dispatch by hand ONLY when the scaffold pre-flight fails and cannot be cleared in-run (e.g. a model delta is unparseable). Hand-authoring is a named fallback, not a default: when used, log a run-log event recording WHY the scaffold could not generate the dispatch. The card's §1–§3 below remain the authoritative content the hand-authored dispatch must reproduce verbatim.

---

## 6. What the scaffold composes for an Agent-tool dispatch

For an Agent-tool sub-agent (no per-model manual involved), this card is self-sufficient and the scaffold (skeleton or complete mode, §5a) composes the dispatch as:

1. **Payload** — the self-contained task file, verbatim (§1).
2. **Header** — the binding addendum (§2), the return schema (§3), the `decisions.md` pointer (or inlined entries), and the `[INLINED]`/`[FULL READ]` reference marks with their excerpts.
3. **Skill directives** — run the `rbtv-sub-agents` Pre-Dispatch Gate: name every skill the task triggers, imperatively and with its workspace-root-absolute path — the sub-agent does NOT reliably auto-discover them.
4. **Transport** — instruct the sub-agent to return the five fields as its final reply (§3 Agent-tool row).

No per-model knowledge is needed for the Agent-tool path: the model delta and the CLI invocation shape exist only for CLI workers. A routing-card assignment plus this card (run through the scaffold) fully specify an Agent-tool dispatch.

---

## 7. What the scaffold composes for a CLI dispatch — generic template + model delta

For a CLI worker, the dispatch manual is GENERATED at build time: the render script (`{rbtv_path}/orchestration/models/render-manuals.py`) composes the generic sections of this card (the `RENDER:BEGIN/END` blocks above) with the model package's delta at the named `RENDER:INSERT` points, producing the model's full dispatch manual under `{rbtv_path}/orchestration/models/{model}/`. At run time the conductor opens that rendered manual (JIT, at first dispatch to the model), not this card; the scaffold (§5a) composes the per-dispatch task file/prompt against that same card + delta.

What the model delta supplies at the insertion points:

| Insertion point | Delta supplies |
|-----------------|----------------|
| `model-binding-delta` (§2) | Model-specific worker obligations beyond the generic addendum (e.g., a stray-file ban, a swarm-policy constraint). |
| `model-transport-note` (§3) | This worker's exact return surface — the CLI's final-message flag, the evidence-file convention — without changing the five fields. |
| (model manual, outside this card) | The invocation shape itself: the exact command, flags, work-dir constraint, prompt-transport (CLI arg vs stdin pipe per host limits), exit-code handling, resume support. This is the model delta's territory, NEVER this generic card's. |

The generic↔delta seam is the same one the task-file contract declares (§8 there): generic contract + model delta, composed at dispatch time. This card is the dispatch-side half of that seam. A protocol change to packaging, the addendum, or the schema is made HERE and re-rendered into every manual — manuals are never hand-edited (the render script carries a DO-NOT-EDIT banner; re-render is zero-diff when nothing changed).

---

## Hand off to verification

The dispatch is sent; the worker runs; a return arrives. Do NOT trust it here. The **verification card** owns what happens next: reconcile the return against disk (§4/§5), run the return gate, fire the review gates and — for development dispatches — the cold verifier at feature boundaries. Follow the situation table in the core protocol to the verification card; this card's responsibility ends when the dispatch is packaged and sent, and resumes only to re-package a re-dispatch.
