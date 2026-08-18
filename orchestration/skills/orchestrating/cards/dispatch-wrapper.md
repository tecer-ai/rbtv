# Card: Dispatch-Wrapper

Opened when routing has produced an assignment — a chosen `(harness, model)` plus `effort` plus `carrier` under its role pins — and a task is about to be sent to a worker. This card packages that assignment into an actual dispatch: how the task is composed for the worker, the binding addendum the worker is held to, and the one named-field schema every worker returns. It is the single source for dispatch packaging.

Iron rules it serves (from the core protocol): **no dispatch without a self-contained task artifact** (this card packages an artifact that already satisfies the task-file contract — it never authors one), and **disk = truth: every return is reconciled against repo state** (the return schema and the post-return rule below exist because the message is a hint, not the truth — five resumed-Kimi sessions drifted to prose while the work had landed correctly on disk; the orchestrator caught all five only by verifying `git` state, never the message).

---

## What this card is NOT

| Not | Where it lives instead |
|-----|------------------------|
| The task-file contract (what a task file must contain) | `{rbtv_path}/orchestration/workflows/_shared/authoring/task-file-contract.md` — authored at intake/planning, BEFORE routing |
| The launch argv (the exact `cast` command) | This card §1 — `cast <harness> <model> <effort> <launch-root> -f <task file>`. `cast` owns and tests the argv (`cast --dry-run` is the composition check) |
| The routing decision (which worker) | The routing card — produces the assignment this card packages |
| The return GATE (what the conductor does with a return) | The verification card — owns reconciliation, review gates, and the cold verifier |

This card composes the GENERIC dispatch around an already-authored task and an already-chosen worker. It restates neither the task-file contract nor the catalog — it references them and binds them together.

---

## 1. Task packaging — the dispatchable unit

The unit sent to a worker is a **self-contained task artifact** (it already satisfies §1–§7 of the task-file contract — this card does not re-author it) composed with the run's binding context. Composition is **header + payload**, never a rewrite of the task file.

| Element | Rule |
|---------|------|
| **Payload = the task file, verbatim** | The dispatched prompt carries the task file's content unedited and untruncated. The worker reads NOTHING from conversation history — the artifact IS the brief. Editing the task body at dispatch time is forbidden; if the task is wrong, fix the task file (and log the amendment), then re-dispatch. |
| **Header = run-binding context** | Prepend only what the worker needs that is not already in the task file: the binding addendum (§2), the return schema (§3), the run's worker-facing `decisions.md` pointer (or its inlined relevant entries), and — for a research leaf — the `rbtv-web-searching` directive in imperative form. The header is composed; the payload is verbatim. |
| **Prompt-file reuse** | For workers driven by a prompt file (CLI workers, and Agent-tool dispatches large enough to warrant it), write the composed header+payload to a prompt file on disk and dispatch FROM that file. The same prompt file is the reuse surface on resume — re-dispatch reads the file, it is not re-composed from memory. |
| **CLI dispatch path** | `cast <harness> <model> <effort> <launch-root> -f <task file>`. Absolute paths on every argument. Binary-first (D17): the line BEGINS with `cast`. A leading `cd …`, an inline env assignment, or a stdin pipe breaks the session allowlist match and the spawn falls to the permission classifier, which denies in-session yolo spawns. So: run from the conductor's CWD (pass the work-target via `--add-dir` when the harness supports it, never a leading `cd`), set env vars in a SEPARATE prior statement, and hand a large brief as `-f <abs-path>` — never a stdin pipe. Pipe and env-prefixed forms remain functionally valid ONLY for owner-typed `!` dispatches (those bypass the session classifier). |
| **Composition check** | `cast --dry-run` on the same argv prints the composed command and exits 0 without launching. Run it before spend. A dry-run that refuses → STOP, do not dispatch. This replaces per-dispatch `--help` scraping. |
| **Absolute paths in every launch command** | Every path in a launch command — the `-f` task file, any stdout/stderr redirect, the launch-root, any `--add-dir` argument — MUST be absolute. A relative path resolves against the spawning shell's CWD, which drifts after any prior `cd`. This is the workspace `rbtv-sub-agents` rule's write-path hygiene (Pre-Dispatch Gate, workspace-root-absolute paths) applied at launch time — follow it, do not restate it. |
| **Launch-folder = orchestrator root; work-target via `--add-dir` (G1)** | ALWAYS launch a CLI worker with its launch-folder = the **orchestrator root** (the workspace the conductor runs from, where the full rules/skills mirror lives) and pass the actual **work-target** separately via `--add-dir <abs>` when the harness supports it: claude `--add-dir`; codex `-c` sandbox writable root. **opencode exception:** launch root IS the target — no add-dir split exists; do not invent one. NEVER root a non-opencode worker at the work-target when the work-target is a nested repo: the mirror skips nested git repos BY DESIGN, so a worker rooted there loads ZERO behavior-rules and operates blind (the a3e217d incident — a bare self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo). State the split explicitly to the worker in the dispatch: "your rules load from your launch root; create/modify files ONLY inside `<work-target>` per the allowlist". Two caveats the conductor owns: (a) the post-run confinement diff MUST run in the **work-target's git** — `git -C <work-target> diff --name-only HEAD` — never in the launch-root's git (a nested-repo work-target has its own git; a launch-root diff passes vacuously); (b) the work-target's OWN local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from an add-dir — inline the load-bearing ones into the dispatch or mark the file `[FULL READ]`. |
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
| API-worker dispatch is ALL-`[INLINED]` | An API worker has no file-read tool — it can never do a `[FULL READ]`. EVERY reference in an API-worker dispatch MUST be `[INLINED]`; the runner inlines each `--target-file` into the request. The whole composed prompt is bounded by the row's `context_window` — a dispatch that won't fit must be SPLIT, never handed off as a path for the worker to read. |

---

## 2. The binding addendum — worker obligations

Every dispatch carries this addendum in its header. These are the obligations the worker is held to regardless of model; they are the conductor's enforcement contract on return. State them imperatively in the dispatch ("you MUST…", "return…", "do NOT…") — never permissively.

| Obligation | What the worker is bound to |
|------------|-----------------------------|
| **Return-schema compliance** | Return the named-field schema in §3 exactly — every field, no field renamed, none invented. The conductor parses these fields; a prose-only return is a contract violation that triggers re-exercise of the return, not acceptance. |
| **Allowlist boundary** | Create / modify / delete ONLY the files in the task's allowlist. Out-of-allowlist file ops are not silently wrong but are NOT silent — they force conductor review (the conductor diffs actual changes against the allowlist on return). State the allowlist in the dispatch even though the task file also carries it. |
| **Halt / doubt policy** | On ambiguity the task does not resolve, HALT and return `DOUBT_ESCALATED` (or `NEEDS_CONTEXT`) — never guess, never improvise past a doubt. A fully-bounded task should contain no ambiguity; if the worker hits one, the task was under-specified and the conductor needs to know. |
| **Invariant-conflict divergence** | When a ruling's or brief's LITERAL wording conflicts with a load-bearing documented invariant, protect the invariant and state the divergence PLAINLY in the return (`concerns`) — rather than halting, and rather than complying literally and silently. This is NOT licence to redesign a ruling the worker merely disagrees with: absent a broken documented invariant, the Halt/doubt row above (or plain compliance) governs — and the disclosure is MANDATORY, never optional. Owner-endorsed as standing precedent 2026-07-20: in one run, four of eight briefs carried a premise that was wrong against the actual code, and workers protecting invariants while disclosing caught all four; a worker complying literally with an aged or over-generalized ruling ships something that looks right and is not. |
| **Evidence-file requirement** | Capture validation evidence as FILES on disk during the work (command output, logs, screenshots for UI), not as prose claims in the reply. For CLI workers the return message is lossy at session end (documented: a completed dispatch returned a garbage final message while the commit had landed) — evidence on disk is what survives. The `validation` field cites what was run; the captures are the proof. |
| **Evidence integrity & byte-exact paths** | Before returning, VERIFY every evidence capture cited in `validation` is NON-EMPTY; a cited capture that is empty or absent is reported as such, NEVER quoted as if it held content (a husk citation is the fabricated-evidence class — a CLI worker cited two empty captures while quoting their supposed content). Any file path consumed OR produced from an existing filename is COPIED BYTE-EXACT from a machine-written source (a list file, a directory listing), NEVER retyped — curly quotes and non-ASCII characters survive a copy but not a transcription. A read that fails is reported as READ-FAIL with the EXACT path used, NEVER classified as a missing/absent file (a transcription typo read-fails on a file that exists, and "file does not exist" then silently drops real work). |
| **Content/order/identity proof** | Any assertion or grading of a content, order, or identity criterion MUST prove that property DIRECTLY; a count (rows, slides, length) is necessary but NEVER sufficient and MUST NOT stand alone as the proof. A count-preserving silent slide-drop passed every count check while dropping real data; the count-only weakening recurred 3× in one run across two models AND the cold-verifier role. The verification card §2b standing pre-flag references this dispatch-side obligation; the `rbtv-done-gate` protocol carries the criterion-exercise twin of the same rule. |
| **Computed claims — authored briefs & checkpoint verdicts** | Every factual claim you WRITE for another agent to act on — a fact stated in a task brief you author, a checkpoint or "done" verdict, a resume/status claim — is COMPUTED from a command AT THE MOMENT OF WRITING, never recalled from memory or derived by reasoning. `rbtv-deterministic-first`'s Compute gate binds these surfaces; follow it, do not restate it. A brief's factual claims are consumed by the receiving agent as ground truth, so an unverified one is not a wrong ANSWER but a wrong INSTRUCTION, executed (2026-07-15: five brief-borne assertions in one run were each wrong and each computable in one command; every one was caught only because the receiving worker recomputed instead of complying — one catch stopped a "fix" that would otherwise have silently REMOVED an existing safeguard while being described as strengthening it). This binds you whenever you author or grade, not only when you answer: under the depth cap a worker may itself drive a sub-conductor and author briefs. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file explicitly grants it (the default is no self-commit). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). An authorized self-commit MUST be **pathspec-scoped to the allowlist**: stage with `git add <allowlist-paths>` and commit with `git commit -- <allowlist-paths>`; `git add -A`, `git add .`, and a bare `git commit -a` are FORBIDDEN regardless of authorization — an unscoped self-commit sweeps foreign uncommitted files into the commit (the a3e217d defect class: 5 foreign files swept by one bare self-commit). The dispatch INLINES the exact pathspec-scoped commit command when self-commit is granted. |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). The git prohibition is MUTATING-ONLY: read-only git (`status`, `log`, `diff`, `show`) is permitted to every worker and briefs MUST NOT widen it to a blanket "never run git" — reconciling one's own claims against disk state is an obligation, not a violation (narrowed 2026-07-18, sysdef-archive closeout: repeated harmless read-only-git "drift" against blanket-banned briefs). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your **launch root** (the directory your guidance keys to: under orchestration this is the orchestrator root, NOT the work-target; for opencode it IS the target) for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at that root (`AGENTS.md` for a Codex/OpenCode worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the launch root has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **opencode auto-reads `AGENTS.md`** at its launch root when present (worktree dispatches must place it there first — G1's opencode exception) but its `.agents/behavior-rules/` read is UNPILOTED — instruct it explicitly. So when composing a dispatch for a non-auto-reading CLI worker with a mirror-equipped launch root, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt; do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing".

The addendum is GENERIC. Catalog quirk facts (when present on the row) MAY add worker-specific obligations on top — they NEVER restate the generic obligations.

---

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
| `DOUBT_ESCALATED` | The worker hit an ambiguity and stopped rather than guess; `open_questions` holds the doubt | Resolve the doubt (halt-to-user or a doc-reader), then **resume** per halt-recovery §2 (same CLI session via `cast resume` where supported; a fresh re-dispatch for an Agent-tool worker that has no session) — never accept a guess in its place. Halt-recovery owns the resume-vs-re-dispatch choice. |
| `NEEDS_CONTEXT` | The task lacked something the worker needed to proceed (a missing file, an unstated decision) | Supply the context (amend the task file + log it), then resume / re-dispatch per halt-recovery §2. |

### Transport — same fields, multiple carriers

The schema is identical across workers; only HOW the fields arrive differs by worker type.

| Worker type | Transport |
|-------------|-----------|
| **Agent-tool helper (Claude sub-agent)** | The five fields ARE the final reply — the sub-agent writes them as its return message; there is no separate file channel required. `cast` refuses to launch `carrier: agent-tool` rows; dispatch those via the Agent tool. |
| **CLI worker (`cast <harness> …`)** | The fields appear in the worker's final message AND the evidence they cite is on disk as files. The final message is treated as a HINT; the disk state and the cited evidence files are the truth the conductor reconciles. |
| **sdd composite dispatch (`superpowers:subagent-driven-development`)** | sdd is ONE composite dispatch wrapped by the outer gates (routing §5). Its outer-wrapper return carries the five fields as the in-session final reply — same as the Agent-tool row — over its whole code body; its internal TDD sub-structure is not surfaced as separate returns. |
| **API worker (`cast api`)** | `cast api <model> <effort> -f FILE --output-folder DIR [--target-file] [--timeout] [--grounded] [--extra-params JSON] [--dry-run]`. Short-name model. `--grounded` / `--extra-params` are the `[mode]` surface. The runner writes the deliverable output file(s) AND a `return.json` carrying the five fields into the conductor-supplied `--output-folder`. The conductor reads the output folder + `return.json` — the API model cannot write to the repo, run git, or commit. Same "message is a hint, disk is truth" discipline; here "disk" = the output folder, NOT a git repo (so reconciliation is file-exists + non-empty + envelope-valid, not `git log`). |

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

The five field checks above are the parseable-return tripwires; the verification card runs them in its §1b table verbatim — and ADDS there one content-inspection tripwire (cited-capture content inspection: it opens each capture the return cites to confirm non-empty + consistent with the claim), a disk-content check beyond these five parseable-field checks. One further tripwire — **Message ≠ state** (`landed` / `validation` disagree with `git status` / `git log` → **state wins**, discrepancy logged in `run-log.md` as a drift instance) — is NOT a §1b field check but the repo-state RECONCILIATION verification performs in its §1c (it compares the parsed fields against the live disk, not within the return). It is named here so the worker knows its message is reconciled against disk; verification owns where it runs.

These checks are the field-level form of "disk = truth." The verification card owns when and how the conductor acts on a tripwire; this card's job is to make the return PARSEABLE so the checks are mechanical.

---

## 5. Post-return rule — reconciliation always follows

EVERY return — `DONE` included, resumes especially — is followed by repo-state reconciliation before the return is trusted or logged. The conductor reads the actual disk state (`git status` / `git log` of the work-dir, plus the cited evidence files) and reconciles it against `landed` / `validation`. Message and state disagree → state wins, logged.

This card carries the WORKER-side obligations that make reconciliation possible (the schema, the evidence-file requirement, the allowlist and commit bindings). The CONDUCTOR-side gate — the actual reconciliation step, the review gates, and the cold verifier for development dispatches — is owned by the **verification card**. Packaging a dispatch from this card is incomplete until the return runs through that gate; do not mark a task done on the strength of the return message alone.

---

## 5a. Generating the dispatch — run the scaffold (pre-flight + execution path)

The composition this card defines (§1 packaging, §2 addendum, §3 schema, + the `cast` argv for a CLI worker) is GENERATED by the dispatch-scaffold, not hand-authored. The scaffold derives the boilerplate at run time from THIS card + the `cast` argv — so a dispatch can never drift from the card. This card's text remains the SOURCE the scaffold derives from: **card text wins; a scaffold output that disagrees with the card is a defect to file, never a reason to hand-patch the dispatch.**

### Pre-flight — scripted, runs before any dispatch (pre-spend)

The scaffold runs scripted pre-flight gates before it writes anything; ANY failure ⇒ EXIT≠0 + a machine-readable error naming the gap, with NO file written (a broken dispatch is caught before spend). Catalog-existence is the scaffold's job (`cast route --catalog` succeeds and names the target pair). The remaining gates:

| # | Scripted check | Passes when |
|---|----------------|-------------|
| 1 | **Catalog names the pair** | `cast route --catalog` exits 0 and the catalog names the `(harness, model)` this scaffold is composing for |
| 2 | **Guidance file present** | the worker's guidance-file convention resolves for the LAUNCH ROOT — the orchestrator root the worker's guidance keys to, never the work-target (present, or its absence is reported so the conductor mirrors it). This is the guidance-FILE check, NOT the rules-library reach (that is Review-5's hook, no-op by default) |
| 3 | **Output folder exists** | `--output-folder` is an existing directory — the scaffold never creates it |

**Conductor pre-flight hygiene — these run ALONGSIDE the scripted gates, conductor-side:** `cast --dry-run` on the composed argv (the composition check). Any auth/config pre-flight (e.g. confirming an API key resolves, reading a catalog field) queries SPECIFIC non-secret fields ONLY — NEVER dump a whole settings/config file into a command or a transcript (a live key reached a transcript once — a real incident). Secret PRESENCE is checked as a boolean (resolves / does not resolve); a secret VALUE is never echoed, logged, or pasted.

**Capture-bound Manus dispatches:** when the dispatch is a capture-bound Manus task, add the pre-flight line that the prompt MUST demand the complete deliverable in the reply MESSAGE TEXT — an attachment-only return failed live.

### The execution path — the exact CLI

Run the scaffold from the rbtv repo root (CWD = `{rbtv_path}`):

```
python orchestration/skills/orchestrating/scripts/scaffold.py \
  --model <model> --output-folder <dir> --filename <name> \
  [--harness <harness>] [--instructions <file-or-inline>] [--explain]
```

| Mode | Trigger | What it writes | Conductor then |
|------|---------|----------------|----------------|
| **Skeleton** | NO `--instructions` | the composed header (addendum §2 + schema §3 + decisions pointer + — for a CLI row — the `cast` argv note) + the frontmatter SKELETON + empty body-section HEADERS | fills ONLY task-specific content (Goal / Context / Implementation / allowlist values), then dispatches |
| **Complete** | `--instructions <file-or-inline>` | a COMPLETE dispatchable prompt — the composed header + frontmatter + body with the instructions merged into the task-specific sections | points the worker straight at the file without re-reading the boilerplate |

`--explain` prints the composed source paths + each pre-flight outcome (provenance preview; still writes the file). The scaffold is carrier-aware: an Agent-tool carrier gets the no-CLI composition (no invocation note); a CLI carrier emits the `cast <harness> <model> <effort> <launch-root> -f <task file>` argv; an API carrier emits the `cast api` argv.

### Hand-authoring is the FALLBACK only

Compose a dispatch by hand ONLY when the scaffold pre-flight fails and cannot be cleared in-run (e.g. `cast route --catalog` cannot name the pair). Hand-authoring is a named fallback, not a default: when used, log a run-log event recording WHY the scaffold could not generate the dispatch. The card's §1–§3 below remain the authoritative content the hand-authored dispatch must reproduce verbatim.

---

## 6. What the scaffold composes for an Agent-tool dispatch

For an Agent-tool sub-agent, this card is self-sufficient and the scaffold (skeleton or complete mode, §5a) composes the dispatch as:

1. **Payload** — the self-contained task file, verbatim (§1).
2. **Header** — the binding addendum (§2), the return schema (§3), the `decisions.md` pointer (or inlined entries), and the `[INLINED]`/`[FULL READ]` reference marks with their excerpts.
3. **Skill directives** — run the `rbtv-sub-agents` Pre-Dispatch Gate: name every skill the task triggers, imperatively and with its workspace-root-absolute path — the sub-agent does NOT reliably auto-discover them.
4. **Transport** — instruct the sub-agent to return the five fields as its final reply (§3 Agent-tool row).

No per-model launch knowledge is needed for the Agent-tool path: `cast` refuses to launch `carrier: agent-tool` rows. A routing-card assignment plus this card (run through the scaffold) fully specify an Agent-tool dispatch.

---

## Hand off to verification

The dispatch is sent; the worker runs; a return arrives. Do NOT trust it here. The **verification card** owns what happens next: reconcile the return against disk (§4/§5), run the return gate, fire the review gates and — for development dispatches — the cold verifier at feature boundaries. Follow the situation table in the core protocol to the verification card; this card's responsibility ends when the dispatch is packaged and sent, and resumes only to re-package a re-dispatch.
