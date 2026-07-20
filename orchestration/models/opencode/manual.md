<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/opencode/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `opencode` package delta `orchestration/models/opencode/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> opencode-specific behavior, edit the delta. Then re-render:
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
| **Absolute paths in every launch command** | Every path in a CLI/server launch command — the prompt-file pointer, any stdout/stderr redirect, the work-target/add-dir argument — MUST be absolute. A relative path resolves against the spawning shell's CWD, which drifts after any prior `cd`: a relative launch path once resolved against the wrong directory and no worker ran while a redirect error masqueraded as the worker's exit code. This is the workspace `rbtv-sub-agents` rule's write-path hygiene (Pre-Dispatch Gate, workspace-root-absolute paths) applied at launch time — follow it, do not restate it. |
| **Launch-root = orchestrator root; work-target via add-dir (G1)** | ALWAYS launch a CLI worker with its guidance-root = the **orchestrator root** (the workspace the conductor runs from, where the full rules/skills mirror lives) and pass the actual **work-target** separately via the model's add-dir flag. The per-model launch-root flag comes from the model's delta (claude-cli/codex key guidance to CWD/`-C`; kimi to `--work-dir`; opencode to `--dir` — the DOCUMENTED exception: its launch root IS the work-target worktree, no add-dir split exists). NEVER root the worker at the work-target when the work-target is a nested repo: the mirror skips nested git repos BY DESIGN, so a worker rooted there loads ZERO behavior-rules and operates blind (the a3e217d incident — a bare kimi self-commit swept 5 foreign files because its guidance-root was the unmirrored nested repo). State the split explicitly to the worker in the dispatch: "your rules load from your launch root; create/modify files ONLY inside `<work-target>` per the allowlist". Two caveats the conductor owns: (a) the post-run confinement diff MUST run in the **work-target's git** — `git -C <work-target> diff --name-only HEAD` — never in the launch-root's git (a nested-repo work-target has its own git; a launch-root diff passes vacuously); (b) the work-target's OWN local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from an add-dir — inline the load-bearing ones into the dispatch or mark the file `[FULL READ]`. |
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
| **Invariant-conflict divergence** | When a ruling's or brief's LITERAL wording conflicts with a load-bearing documented invariant, protect the invariant and state the divergence PLAINLY in the return (`concerns`) — rather than halting, and rather than complying literally and silently. This is NOT licence to redesign a ruling the worker merely disagrees with: absent a broken documented invariant, the Halt/doubt row above (or plain compliance) governs — and the disclosure is MANDATORY, never optional. Owner-endorsed as standing precedent 2026-07-20: in one run, four of eight briefs carried a premise that was wrong against the actual code, and workers protecting invariants while disclosing caught all four; a worker complying literally with an aged or over-generalized ruling ships something that looks right and is not. |
| **Evidence-file requirement** | Capture validation evidence as FILES on disk during the work (command output, logs, screenshots for UI), not as prose claims in the reply. For CLI workers the return message is lossy at session end (documented: a completed dispatch returned a garbage final message while the commit had landed) — evidence on disk is what survives. The `validation` field cites what was run; the captures are the proof. |
| **Evidence integrity & byte-exact paths** | Before returning, VERIFY every evidence capture cited in `validation` is NON-EMPTY; a cited capture that is empty or absent is reported as such, NEVER quoted as if it held content (a husk citation is the fabricated-evidence class — a CLI worker cited two empty captures while quoting their supposed content). Any file path consumed OR produced from an existing filename is COPIED BYTE-EXACT from a machine-written source (a list file, a directory listing), NEVER retyped — curly quotes and non-ASCII characters survive a copy but not a transcription. A read that fails is reported as READ-FAIL with the EXACT path used, NEVER classified as a missing/absent file (a transcription typo read-fails on a file that exists, and "file does not exist" then silently drops real work). |
| **Content/order/identity proof** | Any assertion or grading of a content, order, or identity criterion MUST prove that property DIRECTLY; a count (rows, slides, length) is necessary but NEVER sufficient and MUST NOT stand alone as the proof. A count-preserving silent slide-drop passed every count check while dropping real data; the count-only weakening recurred 3× in one run across two models AND the cold-verifier role. The verification card §2b standing pre-flag references this dispatch-side obligation; the `rbtv-done-gate` protocol carries the criterion-exercise twin of the same rule. |
| **Computed claims — authored briefs & checkpoint verdicts** | Every factual claim you WRITE for another agent to act on — a fact stated in a task brief you author, a checkpoint or "done" verdict, a resume/status claim — is COMPUTED from a command AT THE MOMENT OF WRITING, never recalled from memory or derived by reasoning. `rbtv-deterministic-first`'s Compute gate binds these surfaces; follow it, do not restate it. A brief's factual claims are consumed by the receiving agent as ground truth, so an unverified one is not a wrong ANSWER but a wrong INSTRUCTION, executed (2026-07-15: five brief-borne assertions in one run were each wrong and each computable in one command; every one was caught only because the receiving worker recomputed instead of complying — one catch stopped a "fix" that would otherwise have silently REMOVED an existing safeguard while being described as strengthening it). This binds you whenever you author or grade, not only when you answer: under the depth cap a worker may itself drive a sub-conductor and author briefs. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). An authorized self-commit MUST be **pathspec-scoped to the allowlist**: stage with `git add <allowlist-paths>` and commit with `git commit -- <allowlist-paths>`; `git add -A`, `git add .`, and a bare `git commit -a` are FORBIDDEN regardless of authorization — an unscoped self-commit sweeps foreign uncommitted files into the commit (the a3e217d defect class: 5 foreign files swept by one bare kimi self-commit). The dispatch INLINES the exact pathspec-scoped commit command when self-commit is granted. |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). The git prohibition is MUTATING-ONLY: read-only git (`status`, `log`, `diff`, `show`) is permitted to every worker and briefs MUST NOT widen it to a blanket "never run git" — reconciling one's own claims against disk state is an obligation, not a violation (narrowed 2026-07-18, sysdef-archive closeout: repeated harmless read-only-git "drift" against blanket-banned briefs). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your **launch root** (the directory your guidance keys to: your CWD/`-C` root, or kimi's `--work-dir`; under orchestration this is the orchestrator root, NOT the work-target) for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at that root (`AGENTS.md` for a Codex/Kimi/OpenCode worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the launch root has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **opencode auto-reads `AGENTS.md`** at its `--dir` root when present (worktree dispatches must mirror it in first — opencode delta pre-flight) but its `.agents/behavior-rules/` read is UNPILOTED — instruct it explicitly; **kimi does NOT** auto-read — it needs an enumerated Step-0 naming the read (kimi delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker with a mirror-equipped launch root, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**OpenCode-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What opencode is bound to |
|------------|---------------------------|
| **NO native sandbox — confinement is ENTIRELY the conductor's, and it is worktree-mandatory** | opencode has no sandbox, no approval gate in headless runs, and no work-dir/add-dir scoping flags (POC 2026-07-06: it ran `git status` on the LIVE vault unprompted). Every dispatch MUST run inside a dedicated **git worktree** passed via `--dir "<worktree>"` — never against a live repo or the vault root. The post-run `git -C "<worktree>" diff --name-only HEAD` of every changed path vs the task allowlist is the ONLY reliable enforcement; out-of-allowlist = halt + surface, never auto-revert. The `opencode.json` `permission` block and per-agent tool specs exist but are UNPILOTED — never rely on them as the boundary. A container per profile is the flagged FUTURE escalation for untrusted tasks (aligns with merge-refactor DEC-1 R3); worktree isolation is the shipped default for trusted build/read tasks. |
| **The worktree IS the launch root (deviation from the G1 launch-root split)** | opencode has NO `--add-dir` — `--dir` is both the working root and the work target, so the generic "launch at the orchestrator root, add the work-target" split does not apply. Consequence: guidance loads from the WORKTREE. A fresh vault worktree carries NO `AGENTS.md` (the vault gitignores mirror-generated guidance) — the pre-flight MUST generate it into the worktree via the mirror (`mirror_entry: opencode-mirror`, target = the worktree; the worktree DOES carry the tracked `CLAUDE.md` source) or the conductor inlines the load-bearing behavior rules in the prompt. Never dispatch assuming the worker read rules it could not see. |
| **API keys live in the PROCESS env — export before dispatch** | opencode resolves provider keys from the process environment (registry lookup for `zai`; `{env:SAKANA_API_KEY}` in the sakana provider block). rbtv's `env_file` is NOT auto-read by opencode. The dispatch wrapper resolves the variant's key per rbtv availability semantics (OS env → `env_file`) and exports it into the dispatch process env — never inlines it in the prompt, the task file, or any artifact. |
| **No self-commit unless the task grants it (default OFF)** | opencode MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only` (the POC task committed on a branch inside its worktree — capability proven). NEVER push, NEVER force-reset, NEVER amend. The commit subject carries the run's `[<task-id>]` convention; verify the returned hash against `git log`. Absent an explicit grant, opencode does NOT commit (the conductor commits via `rbtv-commit`). |
| **Stray-file ban** | Create files ONLY where the allowlist directs, inside the worktree. NEVER write scratch notes, logs, or summaries outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the worktree, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions one, no `--dangerously-skip-permissions` unless the task names it. |
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

**OpenCode return surface:** run headless with `opencode run` — the assistant's output prints to stdout (formatted text by default). The worker carries the five return fields in its FINAL message; capture stdout to a durable file via shell redirection (`> "<worktree>/.opencode-runs/<task-id>.txt"`) rather than scraping the console. For machine parsing, `--format json` streams raw JSON events (JSONL — the final result is the last assistant-text event); this is the escalation path if plain-text capture proves brittle (decision 2026-07-09: start with stdout text capture — option (a) of the worker plan; note the earlier "no --json" POC claim is STALE, `--format json` exists on 1.17.11). opencode also has a first-class server (`opencode serve` → `POST /session/{id}/message` returning JSON) — NOT used for dispatch (per-dispatch serve was evaluated and deferred). Treat any returned message as a HINT, never the truth: reconcile every return against `git -C "<worktree>" status` / `git log` and the cited evidence files on disk — disk wins on any disagreement.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The opencode CLI dispatch manual — exact command shapes, flags, provider config, confinement, exit handling, resume, and the opencode task contract. Flags below were verified against **opencode 1.17.11** on 2026-07-09; the ignite VPS now runs **1.17.18** (`opencode --version`, 2026-07-15) — the flags have not been re-verified against that build. Re-verify with `opencode run --help` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build (the POC's "no --json" note was already stale by authoring time: 1.17.11 has `--format json`).

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `opencode --version` (ignite VPS, 2026-07-15: `1.17.18`; flags in this manual were verified against `1.17.11`) | Absent/different → re-verify flags against `opencode run --help`. |
| **Pinned-flag existence** (routing §4 gate) | `opencode run --help` grepped for every non-trivial flag this dispatch pins (`--dir`, `-m`, `--format`, `-s`/`--session`, `-c`/`--continue`, `--title`) | Runs EVERY dispatch. Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. |
| Credential resolves (EITHER path) | **Path A — env var (the piloted one):** resolve the variant's key per rbtv availability semantics (OS env → `rbtv.json` `env_file`): z1 → `ZHIPU_API_KEY`, sakana → `SAKANA_API_KEY`, deepseek-flash/pro → `DEEPSEEK_API_KEY`; then EXPORT it into the dispatch process env. **Path B — stored opencode login (z1, deepseek-flash, deepseek-pro):** `opencode auth list` shows a stored credential (`Z.AI Coding Plan` for z1; `deepseek` for deepseek-flash/pro) → the variant dispatches with NO env var exported; nothing to export. | EITHER path is sufficient for z1, deepseek-flash, and deepseek-pro (route.py gates on env-var **OR** the stored credential — manifest `auth.credential_store`; task adhoc-1, 2026-07-15, live-probed both deepseek variants on the ignite VPS with no env var and no env_file, each returning exit 0). Both absent → variant unavailable; route elsewhere or halt (api-key semantics — never a USER-EXECUTED login at dispatch time). For a key supplied via Path A, opencode reads ONLY the process env — exporting it is mandatory on that path. sakana declares no credential store — adhoc-1 live-probed it with no env var / no env_file and it FAILED (`Forbidden: request was blocked by a gateway or proxy`; the capture does not distinguish a stored-credential gap from an account/gateway block), so it was NOT opted in and stays Path A only. |
| Provider config | z1 + deepseek backends: none needed (the `zai-coding-plan` and `deepseek` providers are models.dev-built-in — key-only). sakana: the custom provider block MUST exist in the machine-global `~/.config/opencode/opencode.jsonc` (template below) | `opencode models` lists the variant's `-m` id (`zai-coding-plan/glm-5.2` / `sakana/fugu-ultra` / `deepseek/deepseek-v4-flash` / `deepseek/deepseek-v4-pro`)? Absent → fix the provider config / key FIRST (a wrong `-m` id fails the dispatch). z1 uses the coding-plan endpoint — pay-per-token `zai/glm-5.2` 429s without an account balance. |
| Worktree exists | `git worktree add <path> -b <branch>` (or reuse the task's assigned worktree) | Worktree-mandatory — NEVER `--dir` a live repo root. One worktree per dispatch (sessions are per-cwd). |
| Guidance file in the WORKTREE | worktree root has `AGENTS.md`? | It will NOT by default (the vault gitignores mirror-generated guidance and a fresh worktree checks out only tracked files) → generate it: `python {rbtv_path}/orchestration/models/mirror/mirror.py --config {rbtv_path}/orchestration/models/opencode/mirror-config.yaml --target "<worktree>"` (the worktree carries the tracked `CLAUDE.md` source), or inline the load-bearing rules in the prompt. |

**Sakana provider block** (machine-global `~/.config/opencode/opencode.jsonc` — already present on this machine, 2026-07-09; reproduce on a new machine):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "sakana": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "Sakana AI",
      "options": { "baseURL": "https://api.sakana.ai/v1", "apiKey": "{env:SAKANA_API_KEY}" },
      "models": { "fugu-ultra": { "name": "Sakana Fugu Ultra" } }
    }
  }
}
```

### The invocation shape — `opencode run` (non-interactive)

`opencode run` executes one headless turn (or resumes a session). The prompt is a positional argument. There is no separate print/quiet flag — `run` IS the headless mode.

**Stdin-EOF guard — MANDATORY on EVERY headless dispatch.** opencode reads stdin whenever it is non-TTY and HANGS forever on "Reading additional input from stdin..." without an EOF (the POC's first stuck launches, 2026-07-06). Force the EOF: **Bash dispatch → suffix `< /dev/null`** (PREFERRED — the line still BEGINS with `opencode`, preserving the §1 D17 binary-first allowlist match). **PowerShell dispatch → prefix `$null |`** (POC-verified) — but the line then begins with `$null`, breaking the `PowerShell(opencode:*)` prefix match: auto-mode/`!`-dispatch only. An owner's interactive terminal has a TTY stdin → no guard needed.

**Shape A — prompt as CLI argument (small prompts; PowerShell-fenced, apply the matching guard):**

```powershell
# Path A (env var). On Path B — a stored `opencode auth login` → "Z.AI Coding Plan"
# credential — SKIP this line entirely: opencode reads the credential from its own store.
$env:ZHIPU_API_KEY = "<resolved from env_file — never inline in artifacts>"
$null | opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 --title "<task-id>" "<task_prompt>" `
  > "<worktree>/.opencode-runs/<task-id>.txt"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Windows ~32 KB). Swap `-m sakana/fugu-ultra` + `SAKANA_API_KEY` for the sakana variant.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; Bash-fenced — the in-session binary-first-safe form):**

```bash
opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 --title "<task-id>" \
  "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists." \
  > "<worktree>/.opencode-runs/<task-id>.txt" < /dev/null
```

The composed **header + payload** (generic packaging §1) is written to `prompt.md` INSIDE the worktree allowlist and dispatched FROM that file — the same prompt file is the reuse surface on resume. opencode loads the brief via its own file tool, so the command stays short and BEGINS with `opencode`. The file-pointer read is VALIDATED for opencode (2026-07-09 smoke, sakana backend: the worker's log shows the `Read oc-task.md` tool call and its return executed the brief's exact contract — exit 0, five-field return conformant).

**Structured events (escalation path):** add `--format json` to stream raw JSON events (JSONL); the final assistant-text event carries the return. Use only if plain-text capture proves brittle.

### Model selection → variants

Route on `(opencode, variant)`; `-m <provider>/<model>` selects the backend per dispatch:

| Variant | `-m` id | reasoning · coding · cost · evidence | Key env var | When |
|---------|---------|--------------------------------------|-------------|------|
| `z1` | `zai-coding-plan/glm-5.2` | 5 · 4 · 3 · validated (piloted 2026-07-09) | `ZHIPU_API_KEY` (a GLM Coding Plan key → the `zai-coding-plan` endpoint. Pay-per-token `zai/glm-5.2` 429s "insufficient balance") **OR** a stored `opencode auth login` → "Z.AI Coding Plan" credential (either satisfies availability — ruling 2026-07-15; the ignite VPS runs on the stored credential alone, no env var) | Open-weights/provider-diversity code executor at mid cost; 1M context. |
| `sakana` | `sakana/fugu-ultra` | 6 · 6 · 7 · validated (piloted 2026-07-09; grades remain vendor-reported, confidence low) | `SAKANA_API_KEY` (provisioned) | Model-diversity premium option; cost 7 ranks LAST — reached via pinned roles, never auto-picked. |
| `deepseek-flash` | `deepseek/deepseek-v4-flash` | 4 · 3 · 1 · validated (piloted 2026-07-09; deepseek-api twin grades) | `DEEPSEEK_API_KEY` (provisioned) **OR** a stored `opencode auth login` → `deepseek` credential (either satisfies availability — task adhoc-1, 2026-07-15; live-probed on the ignite VPS with no env var and no env_file, exit 0) | The cost-floor bounded-code executor (ex-qwen role). CODE roles only (`routable_for`) — text stays on `deepseek-api`. |
| `deepseek-pro` | `deepseek/deepseek-v4-pro` | 5 · 4 · 1 · validated (piloted 2026-07-09; deepseek-api twin grades) | `DEEPSEEK_API_KEY` (provisioned) **OR** a stored `opencode auth login` → `deepseek` credential (either satisfies availability — task adhoc-1, 2026-07-15; live-probed on the ignite VPS with no env var and no env_file, exit 0) | Heavier-reasoning cost-1 code executor. CODE roles only. |

**Effort dial — PROBED, single-mode.** opencode 1.17.11 exposes `--variant <level>` ("provider-specific reasoning effort, e.g., high, max, minimal" — note the flag-name collision with this table's variant ids: opencode's `--variant` is its EFFORT flag, not our routing variant). PROBED 2026-07-09 on all four backends: opencode does NOT validate `--variant` — a bogus level (`--variant bogus-xyz`) returns identically to high/max/minimal (exit 0, same output), so no backend honors an effort ladder through it. Treat every backend as single-mode; do NOT pin an effort level.

### Exit handling

`opencode run` returns a process exit code; `0` = success. The non-zero taxonomy is **UNPILOTED** — no known retryable-throttle code (unlike kimi's 75). On any non-zero exit: reconcile disk state (`git -C "<worktree>" status --porcelain`, the `.opencode-runs/` return file), then recover-or-surface — do NOT blind-retry.

```powershell
$null | opencode run --dir "<worktree>" -m zai-coding-plan/glm-5.2 "<task>" > "<worktree>/.opencode-runs/<task-id>.txt"; $code = $LASTEXITCODE
if ($code -ne 0) { <reconcile disk; recover-or-surface — do NOT blind-retry> }
```

**Disk-state recovery (work landed, return lost):** mirrors the codex candidate protocol — trigger only when the exit is non-zero with NO structured return, `git status` shows uncommitted in-allowlist changes, and no `[<task-id>]` commit exists. Verify the on-disk state against the task's requirements, run the declared validation, check allowlist + forbidden-ops compliance, then commit manually with the `(orchestrator-recovered)` subject suffix and log it. Valid only under a high-reasoning conductor; otherwise halt + surface. **Hung dispatch** (never exits — suspect a missed stdin guard first): kill it, evaluate disk, recover-commit or re-dispatch fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `opencode run -s <SESSION_ID> --dir "<worktree>" "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id. |
| Resume the cwd's last session | `opencode run -c --dir "<worktree>" "<follow-up>"` | POC-proven (two-turn memory, 2026-07-06). Per-cwd — safe ONLY because each dispatch owns its worktree; never share a cwd across dispatches. |
| Fork before continuing | `opencode run -c --fork --dir "<worktree>" "<follow-up>"` | Branch a session to explore a resolution without mutating the original. UNPILOTED. |

Session-id capture is UNPILOTED on the text path (the id is not printed in default format) — capture it from `--format json` events when resume-by-id matters; `-c` inside the dispatch's own worktree is the validated fallback.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless HANGS reading non-TTY stdin | Stdin-EOF guard on EVERY dispatch: Bash `< /dev/null` suffix (binary-first-safe) / PowerShell `$null \|` prefix (auto-mode only). The POC's multi-minute "stalls" were exactly this. |
| No native sandbox — writes anywhere | Worktree-mandatory `--dir` + post-run `git -C "<worktree>" diff --name-only HEAD` vs the allowlist. Never rely on the UNPILOTED `permission` block. |
| `-m` id does not resolve | Pre-flight `opencode models` lists the id? sakana needs its provider block (machine-global config); zai-coding-plan + deepseek need only the key. |
| z.ai key on the WRONG endpoint | z.ai exposes two providers: `zai` (pay-per-token, needs an account balance) and `zai-coding-plan` (GLM Coding Plan subscription, base `https://api.z.ai/api/coding/paas/v4`). A coding-plan key 429s ("insufficient balance") on `zai/*` and works on `zai-coding-plan/*`. `opencode auth login` → "Z.AI" stores the pay-per-token cred (does NOT cover coding-plan) — pick "Z.AI Coding Plan", or export `ZHIPU_API_KEY` and use `zai-coding-plan/glm-5.2` (the piloted path). |
| opencode HANGS on an upstream 429 (balance/quota) | It silently retries with backoff and never surfaces the error — the dispatch times out with only `> build · <model>` on stderr. Not a stdin-guard hang. Diagnostic: raw-curl the provider's `chat/completions` endpoint for the real HTTP status. (live-diagnosed 2026-07-09) |
| Key not visible to the worker | Export the variant's key into the PROCESS env at dispatch (opencode never reads rbtv's `env_file`). |
| Worker saw no behavior rules | A fresh worktree has NO `AGENTS.md` (gitignored) — run the mirror against the worktree, or inline the load-bearing rules in the prompt. |
| Cross-session `-c` contamination | One worktree per dispatch; never launch two dispatches with the same `--dir`. |
| Non-zero exit semantics unknown (UNPILOTED) | Reconcile disk + recover-or-surface; never blind-retry. |
| **Timeout-killed dispatch orphans the worker (live-diagnosed 2026-07-09)** | Killing the dispatch shell does NOT kill the opencode child on Windows — the orphan keeps executing and mutating the workspace (observed: it completed its task minutes after the kill, while a naive re-dispatch raced it in the same cwd). Before ANY re-dispatch after a timeout/kill: liveness-check (`Get-Process opencode`; a busy snapshot `index.lock` delete is also an orphan signal) and `taskkill /PID <pid> /T /F` survivors, then reconcile disk — the orphan may have finished the work. |
| Stale snapshot `index.lock` after a killed run | Benign WARN spam under `~/.local/share/opencode/snapshot/` on later runs; delete once no orphan holds it. |
| Runaway spend on sakana | cost 7 ($5/$30 per 1M) — bound the task tightly; sakana is pin-only, never an auto-pick. Fugu-ultra's multi-agent loop is SLOW on trivial tasks too — budget ≥10 min wall-clock per dispatch before suspecting a hang (a 5-min timeout killed a healthy run, 2026-07-09). |

### The opencode task contract (plugs into the shared authoring core)

An opencode-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with opencode-specific frontmatter.

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: opencode
model_backend: zai-coding-plan/glm-5.2   # or sakana/fugu-ultra — the -m id, pinned at planning
allowed_workdir: <the dedicated worktree path — the --dir value; worktree-mandatory>
allowlist:
  - <file-or-folder-glob, worktree-relative>
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside the worktree allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-skip-permissions
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for external-CLI code is Opus — non-overridable
```

**Required body sections:** Goal · Context Snapshot (all task-specific context inlined — the worker cannot see the conversation) · Allowed Paths · Forbidden Paths · Confinement (the worktree path; the post-run diff the conductor will run) · Implementation Requirements · Validation (the exact commands opencode runs before returning) · Commit Rule · Return Format (the five-field return schema as the FINAL message; stdout is captured to `.opencode-runs/<task-id>.txt`).

**Review gates** every opencode coding task passes (verification card owns the gate): worker self-report → conductor diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. opencode is a separate-process worker with NO sandbox — the cold verifier and review pins apply exactly as for any external-CLI code worker, and the confinement diff is NEVER skippable.
