<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/claude-code-cli/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `claude-code-cli` package delta `orchestration/models/claude-code-cli/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> claude-code-cli-specific behavior, edit the delta. Then re-render:
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
| **Evidence integrity & byte-exact paths** | Before returning, VERIFY every evidence capture cited in `validation` is NON-EMPTY; a cited capture that is empty or absent is reported as such, NEVER quoted as if it held content (a husk citation is the fabricated-evidence class — a CLI worker cited two empty captures while quoting their supposed content). Any file path consumed OR produced from an existing filename is COPIED BYTE-EXACT from a machine-written source (a list file, a directory listing), NEVER retyped — curly quotes and non-ASCII characters survive a copy but not a transcription. A read that fails is reported as READ-FAIL with the EXACT path used, NEVER classified as a missing/absent file (a transcription typo read-fails on a file that exists, and "file does not exist" then silently drops real work). |
| **Content/order/identity proof** | Any assertion or grading of a content, order, or identity criterion MUST prove that property DIRECTLY; a count (rows, slides, length) is necessary but NEVER sufficient and MUST NOT stand alone as the proof. A count-preserving silent slide-drop passed every count check while dropping real data; the count-only weakening recurred 3× in one run across two models AND the cold-verifier role. The verification card §2b standing pre-flag references this dispatch-side obligation; the `rbtv-done-gate` protocol carries the criterion-exercise twin of the same rule. |
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). An authorized self-commit MUST be **pathspec-scoped to the allowlist**: stage with `git add <allowlist-paths>` and commit with `git commit -- <allowlist-paths>`; `git add -A`, `git add .`, and a bare `git commit -a` are FORBIDDEN regardless of authorization — an unscoped self-commit sweeps foreign uncommitted files into the commit (the a3e217d defect class: 5 foreign files swept by one bare kimi self-commit). The dispatch INLINES the exact pathspec-scoped commit command when self-commit is granted. |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your **launch root** (the directory your guidance keys to: your CWD/`-C` root, or kimi's `--work-dir`; under orchestration this is the orchestrator root, NOT the work-target) for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at that root (`AGENTS.md` for a Codex/Kimi worker, `QWEN.md` for a qwen worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the launch root has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **kimi and qwen do NOT** — kimi needs an enumerated Step-0 naming the read, and qwen ignores even imperative directory-read prose unless the dispatch invokes its `QWEN.md` preamble by name OR names the specific rule files (qwen delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker with a mirror-equipped launch root, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Claude-cli-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What claude-code-cli is bound to |
|------------|------------------------------|
| **Unattended writes are EXPLICIT, never assumed-default** | For any dispatch that must write files, pass `--permission-mode acceptEdits` (probe H4-accept: file landed deterministically). Do NOT rely on the default permission mode to be read-only OR write-capable: the probe's no-flag negative control ALSO wrote (H4-default, `helper-04-write-default-*` — the workspace default already permitted writes). The mode is the portable guarantee; the default is workspace-dependent and MUST NOT be trusted for confinement either way. NEVER pass `--dangerously-skip-permissions` / `bypassPermissions` as a confinement shortcut — that removes the guardrail, it does not set one. |
| **Confinement is the orchestrator's job — `--permission-mode` authorizes, it does not BOUND** | `acceptEdits` lets the worker write without a prompt; it does NOT restrict writes to an allowlist. Bound the worker by (a) running from / `--add-dir`-ing only the minimal dirs, (b) `--allowedTools`/`--disallowedTools` to strip tool families the task does not need, and (c) the mandatory post-run `git diff --name-only HEAD` of every changed path vs the task allowlist — the only reliable write enforcement (corroboration: the harness auto-reverts writes outside `case_dir` via a post-run git diff). Out-of-allowlist edit = halt + surface; never auto-revert silently. |
| **Native workspace rules are loaded — root the worker at the LAUNCH ROOT, never `--bare`** | Run `claude -p` FROM the **orchestrator root** (the launch root — its cwd is the `CLAUDE.md` auto-load root, probe H5) and pass the **work-target** via `--add-dir <work-target>`. NEVER root the worker at a nested-repo work-target — its guidance root would be the unmirrored nested repo (the a3e217d defect class). A `--add-dir`'d work-target's OWN `CLAUDE.md` is NOT auto-loaded — inline its load-bearing conventions into the prompt or mark the file `[FULL READ]`. NEVER pass `--bare` (it DISABLES `CLAUDE.md` auto-discovery, per `--help`) when the worker needs the workspace rules. If the launch root has no `CLAUDE.md`, inline the needed rules into the prompt — do not silently run rule-less. |
| **Sub-conductor depth cap ≤ 2 — a claude -p worker does NOT nest Agent-tool sub-agents** | A `claude -p` worker IS a sub-conductor (the D7 process-boundary escape, probe-exercised at one boundary: conductor → `claude -p`). It MAY shell out to further CLI subprocesses, but the depth cap ≤ 2 FORBIDS relying on deeper nesting, and the 4× documented Agent-tool nesting wall blocks a `claude -p` worker's own Agent-tool sub-agents from spawning further ones anyway. Do NOT design a claude -p dispatch that fans out Agent-tool sub-agents beneath itself. |
| **No self-commit unless the task grants it (default OFF)** | claude-code-cli MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, claude-code-cli does NOT commit (the conductor commits via `rbtv-commit`). When committing through Claude Code, honor the workspace's own commit conventions (the natively-loaded `CLAUDE.md` may mandate a trailer) — they bind this worker because it loaded them. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--dangerously-skip-permissions` / `--bare` unless the task names them. |
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

**Claude-cli return surface:** run headless with `claude -p "<prompt>" --output-format json`. The JSON is a single envelope (probe H2/H3/H7, `helper-02/03/07-*`): `result` (the assistant's final text — where the five return fields live), `session_id`, `total_cost_usd`, `is_error`, `num_turns`, `duration_ms`, `permission_denials[]`, and `modelUsage.<model>.{contextWindow,maxOutputTokens,…}`. `--output-format text` gives the bare assistant text instead; `stream-json` streams events (one JSON object per line, not probed). The worker carries the five return fields in `result`; treat the message as a HINT, never the truth. A final-turn drop is possible (the generic CLI-worker lossy-return class — codex/kimi share it); on any garbled/absent return, reconcile from disk. **Ground truth is the exit code + `is_error`, not the prose**: `exit 0` + `is_error: false` = success (probe; corroboration: the harness trusts `git push` exit 0, never Claude's claim of success). The conductor reconciles every claude-code-cli return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a known-path durable return, instruct the worker to ALSO write its five fields to an evidence file inside the allowlist (the JSON envelope can be captured to a file by redirecting stdout: `… --output-format json > <evidence-path>`).
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The claude-code-cli dispatch manual — the exact command shapes, flags, exit handling, resume, the native-workspace-rules property, and the claude-code-cli task contract. Every shape here is probe-HELD (p3-6) or sourced from `claude --help` (capture `helper-help.txt`); the probe environment was Windows 11, Claude Code **2.1.168**. Re-verify with `claude --help` / `claude --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build.

### Canonical unattended dispatch shape (Windows)

```bash
# In-session dispatch (bash carrier) — command BEGINS with `claude`; stdin redirect TRAILS:
claude -p "<PROMPT>" --output-format json --model <opus|sonnet|fullname> [--permission-mode acceptEdits] [--add-dir <DIR>] < /dev/null
```

```powershell
# Owner-typed `!` dispatch (PowerShell) — the leading $null| pipe is fine OUTSIDE the session classifier:
$null | claude -p "<PROMPT>" --output-format json --model <opus|sonnet|fullname> [--permission-mode acceptEdits] [--add-dir <DIR>]
```

The mandatory stdin redirect, the JSON envelope, `--model`, the optional unattended-write flag, and `--add-dir` are all probe-validated. For an IN-SESSION dispatch the command line MUST BEGIN with `claude` (generic packaging §1 D17 row): PowerShell's only stdin-redirect mechanism is a leading `$null |` pipe, which breaks the `claude:*` prefix match — so in-session dispatches go through the bash carrier, where `< /dev/null` trails the command. Run the command FROM the orchestrator root (the launch root — the worker auto-loads THAT workspace's `CLAUDE.md`) and pass the work-target via `--add-dir` (see "Workspace rooting").

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `claude --version` (probe: `2.1.168`) | Absent/older → re-verify flags against `claude --help`. |
| **Pinned-flag existence** (routing §4 gate) | `claude --help` grepped for every non-trivial flag this dispatch pins (`-p`/`--print`, `--output-format`, `--model`, `--permission-mode`, `--add-dir`, `--allowedTools`/`--disallowedTools`, `--resume`/`--session-id`, `--max-budget-usd`) | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned; codex 0.137.0/`--ask-for-approval` is the cautionary case, p5-2). Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard arg-parse error pre-spend if dispatched (probe H6: an unknown flag → exit 1, no spend). |
| Auth | (already authenticated — the conductor IS Claude Code on this machine) | On the SAME machine/user no per-dispatch auth is needed (the probe ran 8 API dispatches in-helper, no login step). A brand-new machine needs a one-time interactive `claude` login — that is the conductor's own setup (USER-EXECUTED-ONLY), not a per-dispatch pre-flight. |
| Guidance file | the LAUNCH ROOT (orchestrator root — the cwd) has `CLAUDE.md`? | **NO mirror** — CLI-Claude loads its cwd workspace's OWN `CLAUDE.md` natively (H5). Checked at the launch root, never the work-target (a `--add-dir`'d work-target's `CLAUDE.md` is NOT auto-loaded — inline/point instead). Launch root lacks one → inline the needed rules into the prompt, or root cwd at a `CLAUDE.md`-bearing dir; NEVER generate a banner-stamped `CLAUDE.md` (it would clobber the user's file). NEVER pass `--bare` when rules are needed. |

### The invocation — `claude -p` (non-interactive print mode)

`-p` / `--print` runs Claude non-interactively: it executes the prompt and exits (probe: every H row). It skips the workspace trust dialog — run it ONLY in trusted directories. The prompt reaches the worker as the `-p` argument; **stdin MUST be redirected** or the CLI waits 3s for piped input (see "Windows stdin" below).

**Shape A — prompt as the `-p` argument (small prompts; command BEGINS with `claude`):**

```bash
claude -p "<task_prompt>" --output-format json --model sonnet --permission-mode acceptEdits < /dev/null
```

Use when the prompt fits comfortably under the host shell's single-argument limit (~32 KB single arg on Windows shells). Default for short dispatches.

**Shape B — large brief via a FILE POINTER (default in autonomous mode; command BEGINS with `claude`):**

```bash
claude -p "Read the file '<prompt-path>' and execute the task it contains exactly; create only the files it allowlists." \
  --output-format json --model opus --permission-mode acceptEdits --add-dir "<repo>" < /dev/null
```

Use when the prompt is large OR when running autonomously. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and the worker loads it via its own file tool — the command stays short AND begins with `claude` (the in-session permission requirement; the prompt file is the reuse surface on resume). Do **not** read the file into a shell variable first (`$prompt = Get-Content -Raw prompt.md; $null | claude -p "$prompt" …`): the leading assignment/pipe breaks the `claude:*` prefix match in-session — that form stays valid for owner-typed `!` dispatches only. (Claude reads the prompt from the `-p` arg, not from stdin in `-p` mode — stdin stays redirected; do not pipe the prompt via stdin.)

### Windows stdin — the mandatory redirect

| Symptom | Cause | Fix |
|---------|-------|-----|
| 3s pause + `no stdin data received in 3s, proceeding without it` on stderr; the warning pollutes `text` stdout | `claude -p` waits for piped stdin when none is redirected (probe C1) | ALWAYS redirect stdin: `< /dev/null` (bash, TRAILING — the in-session form, keeps the command beginning with `claude`) · `< NUL` (cmd) · `$null \|` (PowerShell — leading pipe, breaks the in-session `claude:*` prefix match; owner-typed `!` dispatches only). Probe C2 + every H row ran clean with the redirect. |

### Output format + the JSON envelope

| `--output-format` | Yields | Use |
|-------------------|--------|-----|
| `text` (default) | bare assistant final text | quick dispatches where you only need the answer string |
| `json` | one envelope: `result` · `session_id` · `total_cost_usd` · `is_error` · `num_turns` · `duration_ms` · `permission_denials[]` · `modelUsage.<model>.{contextWindow,maxOutputTokens,…}` · `terminal_reason` | the dispatch default — parseable status + cost + the session id for resume (probe H2/H3/H7) |
| `stream-json` | one JSON object per line (events) | streaming consumers (not probed) |

The five return fields (§3) live inside `result`. Capture the envelope to a file with `> <evidence-path>` for a durable return inside the allowlist.

### Model selection → variants

The claude-code-cli manifest declares three routable variants — route on `(claude-code-cli, variant)`:

| Variant | Flag | When |
|---------|------|------|
| `fable` | `--model fable` | Senior-most Claude; the conductor / final-plan-reviewer pin target; premium cost. |
| `opus` | `--model opus` (or full name `claude-opus-4-8`) | Judgment-dense work and the **sub-conductor** role; the external-CLI **code-review reviewer floor** (reviewer for kimi/codex code is Opus — route it here). Max-reasoning Claude. |
| `sonnet` | `--model sonnet` | Partially-bounded work with `doubt_policy: halt`, and zero-context verification personas (recon, research, cold-verify, commits). Mid-tier; the default routable Claude-cli variant. |

`--model <alias|fullname>` is honored — the JSON `modelUsage` key names the ACTUAL model + its real context window (probe H3: `--model sonnet` → `modelUsage.claude-sonnet-4-6`, ctx 2e5). **The DEFAULT model is user-config-dependent**: on the probe machine the default was `claude-opus-4-8[1m]` (1M ctx, probe H2) — NOT sonnet, and NOT a constant to assume. ALWAYS pass `--model` explicitly for a deterministic dispatch; read the live `modelUsage` to confirm. **haiku is NOT a routable variant** (vault routing floors at sonnet absent a user-approved delegation map naming haiku — routing card §7).

### Effort invocation — the post-pin reasoning dial (fable, opus, and sonnet; haiku is a no-op)

Claude CLI exposes a **5-level effort ladder** (`low | medium | high | xhigh | max`) via the `--effort <level>` flag. This is the post-pin reasoning dial: effort is set AFTER the variant is pinned (`effort = f(boundedness)`), stored in the manifest's `reasoning_modes`, and is a CLI-only surface (`claude -p`) — the Agent-tool carrier (`claude-code-native`) is single-mode (effort not settable in-session). The ladder applies to fable, opus, and sonnet (probe 2026-07-07: `--model fable` accepted both `--effort low` and `--effort max`, evidence below). **Haiku is a no-op single-mode** even on the CLI — pass no `--effort` flag for a haiku dispatch.

| Effort | Flag | When (boundedness) |
|--------|------|-------------------|
| `low` | `--effort low` | Fully-bounded mechanical work (the cheapest thinking budget) |
| `medium` | `--effort medium` | Partially-bounded work with `doubt_policy: halt` |
| `high` | `--effort high` | Unbounded or judgment-dense work |
| `xhigh` | `--effort xhigh` | Extended thinking; higher spend |
| `max` | `--effort max` | Maximum reasoning budget; use for the highest-stakes unbounded leaves |

Example (opus, high effort, unattended write):

```bash
claude -p "<task_prompt>" --model opus --effort high --output-format json --permission-mode acceptEdits < /dev/null
```

### Permission modes — unattended writes

| Mode | Effect | Use |
|------|--------|-----|
| `acceptEdits` | file writes auto-approved, no prompt (probe H4-accept) | the explicit, portable unattended-write guarantee — pass it for any dispatch that must write |
| `default` | workspace-dependent — **the probe's default already wrote** (H4-default) | do NOT assume read-only OR write-capable; never rely on it for confinement |
| `plan` | plan-only, no execution | a read-only analysis leaf that must not act |
| `bypassPermissions` / `--dangerously-skip-permissions` | ALL permission checks off | NEVER as a confinement shortcut; only an externally-sandboxed env the task explicitly names (corroboration: the harness used `bypassPermissions` ONLY because a post-run git-diff boundary check + framing-layer hard rules confined it — the mode alone confines nothing) |

Modes available per `--help`: `acceptEdits`, `auto`, `bypassPermissions`, `default`, `dontAsk`, `plan`. **Confinement is the orchestrator's job** — `acceptEdits` authorizes writes but does NOT bound them; ALWAYS back a dispatch with the post-run `git diff --name-only HEAD` vs the allowlist.

### Workspace rooting — the unique native property (NO mirror)

CLI-Claude **natively auto-loads the cwd workspace `CLAUDE.md`** (and its rules/skills) and obeys it (probe H5-pos returned the planted codeword `XYZZY-ROOT`; H5-neg with no file returned "I don't have a codeword"). This is the property Agent-tool helpers LACK and the reason claude-code-cli is the sub-conductor of choice for in-workspace work.

| Need | Mechanism |
|------|-----------|
| Give the worker the orchestrating workspace's rules | Run `claude -p` FROM the **orchestrator root** (the launch root — cwd is the `CLAUDE.md` auto-load root). The worker inherits that root's `CLAUDE.md` + rules + skills automatically. NEVER root the worker at a nested-repo work-target (G1 — the a3e217d defect class). |
| Grant access to the work-target (and extra dirs) | `--add-dir <work-target>` (repeatable for further extras; confirmed in `--help`). A `--add-dir`'d dir's own `CLAUDE.md` is NOT auto-loaded — inline its load-bearing conventions or mark the file `[FULL READ]`. The post-run confinement diff runs in the work-target's git: `git -C <work-target> diff --name-only HEAD`. |
| Disable rule auto-load (rare) | `--bare` DISABLES `CLAUDE.md` auto-discovery (per `--help`) — the opposite knob; use only when the worker must run rule-less. |
| Launch root has NO `CLAUDE.md` | Inline the needed rules into the prompt, or root cwd at a `CLAUDE.md`-bearing dir. Do NOT generate one — there is no mirror for claude-code-cli (a banner-stamped `CLAUDE.md` would clobber the user's primary project file; the workspace's own `CLAUDE.md` is the source of truth, loaded natively). |

**Why no mirror (ruling):** kimi/codex mirror their guidance file (`AGENTS.md` — a worker-specific, non-conflicting filename that does not exist natively) into a target workspace. claude-code-cli's guidance file IS `CLAUDE.md`, which the worker loads natively and which is the user's own hand-authored file. Mirroring `CLAUDE.md`→`CLAUDE.md` is a self-copy where the file exists (and a destructive banner-overwrite of the user's file) and circular where it is absent. So claude-code-cli ships **no `mirror-config.yaml`**, and its manifest omits `guidance_file.mirror_entry`. The routing card's pre-dispatch guidance-file check, for claude-code-cli, VERIFIES the workspace has a `CLAUDE.md` (and cwd/`--add-dir` points at it) — it never offers a mirror. (Full ruling: `../../../shape.md` mirror Decision, 2026-06-07.)

### Exit handling

| Code | Meaning | Conductor action |
|------|---------|------------------|
| `0` | Success — JSON `is_error: false`, `result` populated | Proceed to the return gate (reconcile against disk, then verification card). `exit 0` + `is_error:false` is ground truth, NOT the prose. |
| `1` | Arg-parse / usage error — fast (0.4s), **BEFORE any API spend** | Halt + surface; fix the command. A malformed dispatch costs nothing (probe H6: `--not-a-real-flag-xyz` → exit 1 + stderr `error: unknown option …`, no spend). |

No richer exit-code taxonomy was probed (no hang was engineered, per the task's "do NOT engineer a hang"; observed durations 0.4–10.1s). On any unexpected non-zero exit, reconcile disk state and recover-or-surface; do NOT blind-retry.

```bash
claude -p "<task>" --output-format json --model sonnet --permission-mode acceptEdits > out.json < /dev/null
code=$?
# non-zero -> halt + surface — H6: arg-parse error, no spend; fix the command
# else: parse out.json; trust is_error:false + exit 0, then reconcile against git status / git log
```

### Disk-state recovery (work landed, return/commit lost) — judgment-only

A final-turn drop on a long dispatch is possible (the generic CLI-worker lossy-return class; not separately probed for claude-code-cli — no hang was engineered). Treat it like the kimi exit-75 / codex disk-recovery class: valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: the worker exited with NO structured return (no five fields / no commit hash) in the JSON `result` or the captured output; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (claude -p never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh (the prompt file is the reuse surface). Prefer resume (below) when a `session_id` was captured before the drop.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `claude -p --resume <session_id> "<follow-up>" --output-format json < /dev/null` (bash; in-session form) | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id (probe H7 recalled the earlier turn; the same `session_id` returns). The `session_id` comes from the prior JSON envelope. |
| Fork instead of continue | `claude -p --fork-session --resume <session_id> "<prompt>"` | Branch a new session from an existing one (per `--help`; not separately exercised). |
| Pin a session id | `claude -p --session-id <uuid> "<prompt>"` | Assign a known id up front (per `--help`). |
| Run without persisting | `claude -p --no-session-persistence "<prompt>"` | A print-only dispatch that should leave no resumable session (per `--help`). |

Resume is `session_id`-based and probe-validated (H7). Corroboration: the harness resumes the same Claude session across machines by UUID lookup — the session id is the durable handle. Capture the `session_id` from the JSON envelope on every dispatch you may need to resume; fall back to a fresh re-dispatch (prompt file = reuse surface) if resume does not engage.

### Confinement grammar — the orchestrator's job

CLI-Claude's `--permission-mode acceptEdits` AUTHORIZES writes but does NOT bound them to an allowlist; there is no native per-path write allowlist. Bound a worker by combining:

| Control | Mechanism |
|---------|-----------|
| Workspace scope | Run from the orchestrator root (cwd = launch root, the `CLAUDE.md` auto-load root) + `--add-dir <work-target>` (+ further `--add-dir <extra>` only when needed; repeatable). Keep the set minimal. |
| Tool surface | `--allowedTools` / `--disallowedTools` to allow/deny tool families (corroboration: the harness ran `--disallowedTools Bash` to prevent git races in read-only pipelines). No agent-file mechanism (unlike kimi). |
| Read confinement | Inline required context into the prompt; the natively-loaded workspace `CLAUDE.md` already scopes behavior. |
| **Write confinement** | **Post-run `git -C <work-target> diff --name-only HEAD` of every changed path against the task's `allowlist`** — run in the WORK-TARGET's git, never the launch-root's; the ONLY reliable enforcement (corroboration: the harness auto-reverts writes outside `case_dir` via post-run git diff). Out-of-allowlist = halt + surface; NEVER auto-revert silently. |
| Permission posture | `--permission-mode acceptEdits` for an intended unattended write; `plan` for a no-act analysis leaf. NEVER `bypassPermissions` / `--dangerously-skip-permissions` as a confinement shortcut. |
| Commit / push | Local-only by policy; verify git state shows no push since dispatch. |
| Budget guard | `--max-budget-usd <amount>` + `--fallback-model <model>` (print-mode, per `--help`) cap an autonomous dispatch's spend. |

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| stdin not redirected → 3s wait + warning polluting `text` stdout | ALWAYS redirect stdin (`$null \|` / `< NUL` / `< /dev/null`) — probe C1 vs C2. |
| Default permission mode is NOT guaranteed read-only | The no-flag write control still wrote (H4-default); pass `--permission-mode acceptEdits` explicitly for an intended write, and never trust the default for confinement. |
| `--permission-mode` authorizes but does not BOUND writes | Always back with the post-run `git diff` vs allowlist — the only reliable write confinement. |
| `--bare` disables `CLAUDE.md` auto-load | Never pass `--bare` when the worker needs the workspace rules; it is the opposite of the native-rooting property. |
| Final-turn drop on a long dispatch | JSON/message is a HINT; reconcile from disk; `exit 0` + `is_error:false` is ground truth. Capture the envelope to a file for a durable return. |
| Treating the message as truth | `git push` / write exit code is ground truth, never Claude's prose claim of success (corroboration: the harness re-checks the wire, never the self-report). |
| Depth-cap violation | A claude -p worker must NOT nest Agent-tool sub-agents beneath itself (depth cap ≤ 2; the nesting wall blocks it anyway) — sub-conduct via further CLI subprocesses only. |

### The claude-code-cli task contract (plugs into the shared authoring core)

A claude-code-cli-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with claude-code-cli-specific frontmatter and body sections. The orchestrator validates a `executor: claude-code-cli` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis/review for a read-only or verification leaf
executor: claude-code-cli
model: opus | sonnet            # the routed variant — opus for judgment/sub-conductor/code-review, sonnet for mid-tier/verification
allowed_workdir: <work-target repo path — passed via --add-dir; the cwd/launch root is the orchestrator root, never this>
allowlist:
  - <file-or-folder-glob>
permission_mode: acceptEdits | plan | default   # acceptEdits for an intended write; plan for a no-act analysis leaf
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-skip-permissions
  - --bare
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for external-CLI code is Opus — non-overridable
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — the worker also inherits the workspace `CLAUDE.md` natively, so do NOT duplicate workspace rules into the prompt; inline only task-specific facts) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Permission + Rooting (the `--permission-mode` value, the cwd/`--add-dir` rooting, and whether `--bare` is forbidden) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands claude-code-cli runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema; capture the JSON envelope to an evidence file inside the allowlist).

**Review gates** every claude-code-cli coding task passes (verification card owns the gate): claude-code-cli self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". When claude-code-cli is itself the cold verifier or reviewer (its strong suit — a separate Claude invocation with no authoring context, exactly the harness's adversarial/red-team pattern), it floors at the `opus` variant and receives ONLY the contract criteria + the running artifact, never the builder's claims.

### Recipes

All in-session recipes are bash-carrier, command BEGINS with `claude`, stdin redirect trailing (the `$null | claude …` PowerShell forms remain valid for owner-typed `!` dispatches only):

```bash
# Bounded write dispatch, JSON envelope captured to a durable file (Shape A), rooted in the workspace:
claude -p "<inlined task file content>" --output-format json --model sonnet \
  --permission-mode acceptEdits --add-dir "5-workbench/inni-cte-recon" > .claude-runs/t1.json < /dev/null
```
```bash
# Large brief via a FILE POINTER (Shape B), opus sub-conductor, rooted at the repo:
claude -p "Read the file '<prompt-path>' and execute the task it contains exactly" \
  --output-format json --model opus --permission-mode acceptEdits --add-dir "<repo>" > .claude-runs/t1.json < /dev/null
```
```bash
# Read-only analysis / cold-verify leaf (no writes), opus, no acceptEdits (plan mode):
claude -p "<verification task: exercise these criteria on the running artifact>" \
  --output-format json --model opus --permission-mode plan --add-dir "<repo>" > .claude-runs/verify.json < /dev/null
```
```bash
# Resume a halted session with the resolution:
claude -p --resume <session_id> "<resolution to the open question>" --output-format json > .claude-runs/t1-resume.json < /dev/null
```
