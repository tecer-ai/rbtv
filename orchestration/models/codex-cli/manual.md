<!-- AUTO-GENERATED — DO NOT EDIT. Rendered by orchestration/models/render-manuals.py from orchestration/skills/orchestrating/cards/dispatch-wrapper.md + orchestration/models/codex-cli/delta.md. -->

> [!danger] GENERATED FILE — DO NOT EDIT
> This dispatch manual is composed by `orchestration/models/render-manuals.py` from:
> - the generic dispatch contract `orchestration/skills/orchestrating/cards/dispatch-wrapper.md`, and
> - the `codex-cli` package delta `orchestration/models/codex-cli/delta.md`.
>
> Hand-edits are overwritten on the next render and are forbidden. To change
> packaging/addendum/return behavior, edit the wrapper template; to change
> codex-cli-specific behavior, edit the delta. Then re-render:
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
| **Commit discipline** | Commits go through `rbtv-commit` (routing pins this to a commit-capable worker — CLI workers are kept OFF commits by default). Local commits only; NEVER push. A CLI worker is authorized to self-commit ONLY when its task file / model delta explicitly grants it (the default is no self-commit; the kimi package's delta is where a code-executing worker's local-commit authorization is declared). When the worker IS authorized: validation passes first, the commit message follows the run's mandated convention, and the returned commit hash must match what is actually in `git log` (the conductor checks the message string and the hash, not just the file list). |
| **Forbidden operations** | Honor the task's forbidden-ops list (no pushes, no writes outside the allowed work-dir, no destructive git resets, no external production API calls unless the task explicitly allows a mocked/local one). |
| **Rule-loading (mirror-equipped workspace)** | Before ANY other action — before reading any task-referenced file, writing, running a tool, or responding — inspect your work-dir for a `.agents/behavior-rules/` directory. If it exists (a mirror-equipped workspace), you MUST FIRST read your own guidance file at the work-dir root (`AGENTS.md` for a Codex/Kimi worker, `QWEN.md` for a qwen worker) AND every file under `.agents/behavior-rules/`, and treat their entire contents as binding, non-negotiable rules governing this whole session — exactly as if they were part of this dispatch. Reading them is mandatory even when this task body never mentions rules; the absence of a rule-read instruction in the task is NOT permission to skip them. If the work-dir has no `.agents/behavior-rules/` directory, this obligation is a silent no-op — proceed normally. |

**Conductor obligation — instruct the rule-read for harnesses that do NOT auto-read (CLI workers).** A CLI worker whose governance depends on the behavior-rule fan-out only obeys the Rule-loading obligation above if its harness actually reads its rules directory. Harnesses differ: **codex auto-reads** its rules directory (no explicit instruction needed); **kimi and qwen do NOT** — kimi needs an enumerated Step-0 naming the read, and qwen ignores even imperative directory-read prose unless the dispatch invokes its `QWEN.md` preamble by name OR names the specific rule files (qwen delta `model-binding-delta`). So when composing a dispatch for a non-auto-reading CLI worker in a mirror-equipped work-dir, the conductor MUST add an EXPLICIT rule-read instruction to the dispatch prompt (the per-model proven form, from that model's delta); do NOT rely on the generic obligation alone. That instruction MUST tell the worker to read the rule files ONE FILE PER CALL (or in small batches) — NEVER a single recursive bulk read: a bulk `Get-Content -Recurse`-style read of a multi-file rule library truncates silently mid-corpus, so an alphabetically-later rule's body never reaches the model and the obligation it carries goes unread despite the read "firing" (the 2026-06-09 kimi `<counter>` incident). (The mirror-driver `guidance.py` half of this guarantee is deferred to the mirror-install follow-up — not authored here.)

The addendum is GENERIC. A model package's delta MAY add model-specific obligations on top (e.g., a worker that must be told not to write stray files in the repo root, or a swarm-policy constraint) — it plugs in at the insertion point below and NEVER restates the generic obligations.

**Codex-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What codex is bound to |
|------------|------------------------|
| **Sandbox + approval are the confinement, and they are the conductor's to set (UNPILOTED enforcement)** | Codex has a real native sandbox (`-s/--sandbox`: `read-only` · `workspace-write` · `danger-full-access`) and an approval policy. On Codex CLI **0.137.0** `codex exec` has NO `-a/--ask-for-approval` flag (it was removed from the `exec` subcommand — verified absent in `codex exec --help`, p5-2 smoke probe); the approval policy is set via the config override `-c approval_policy="never"` (a `-c` dotted-path TOML override — `approval_policy` is a recognized key, confirmed under `--strict-config`). A non-interactive dispatch MUST set `-c approval_policy="never"` (so the model never pauses for a human) paired with the TIGHTEST sandbox the task needs — `read-only` for analysis/research leaves, `workspace-write` for code that edits the work-dir, NEVER `danger-full-access` and NEVER `--dangerously-bypass-approvals-and-sandbox` unless the task explicitly sanctions it. The pairing `-c approval_policy="never"` + `--sandbox workspace-write` is the bounded-write default. The sandbox is real but its reliability as a confinement boundary for THIS orchestrator is UNPILOTED — back it with the same post-run `git diff --name-only` vs the allowlist that every CLI worker gets. |
| **Workspace scope is `-C`/`--cd` + `--add-dir`; writes outside the work-dir are a guardrail breach** | Set `-C <repo-root>` (or run from that cwd) and add only the minimal extra writable dirs via `--add-dir`. Files created/modified outside the scoped workspace are an out-of-allowlist write the conductor catches on the post-run diff — surface, never auto-revert. `--skip-git-repo-check` is required ONLY when the work-dir is not a git repo (codex refuses to run outside a repo otherwise). |
| **No self-commit unless the task grants it (default OFF)** | Codex MAY commit locally — and ONLY locally — after its declared validation passes, when the task file grants `commit_policy: local-only`. NEVER push, NEVER force-reset, NEVER amend. The commit subject MUST carry the run's mandated `[<task-id>]` convention; the returned hash MUST match `git log`. Absent an explicit grant, codex does NOT commit (the conductor commits via `rbtv-commit`). This authorization, and the commit message convention's survival across a codex run, are UNPILOTED — verify the hash and the subject string on return. |
| **Project trust is a pre-flight, not a runtime grant** | Codex records per-project `trust_level` in `~/.codex/config.toml` (`[projects.'<path>']`). An untrusted target project triggers a first-run interactive trust prompt — a USER-EXECUTED-ONLY pre-flight (run codex once interactively in the workspace, or pre-set trust) before any headless dispatch. Do NOT attempt to clear a trust prompt programmatically. |
| **Stray-file ban** | Create files ONLY where the allowlist directs. NEVER write scratch notes, logs, or summary files into the repo root or anywhere outside the allowlist — the post-run diff treats any such file as an out-of-allowlist write. Use `-o/--output-last-message <file>` to land the structured return at a known path INSIDE the allowlist rather than scraping stdout. |
| **Forbidden-ops are exhaustive** | The task's `forbidden_ops` list is the complete prohibition set; absence of mention is NOT permission. No writes outside the scoped work-dir, no `git push`, no destructive git reset, no external production API calls unless the task explicitly sanctions a mocked/local one, no `--dangerously-bypass-*` flags unless the task names them. |
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

**Codex return surface:** run headless with `codex exec` (alias `codex e`). The final assistant message goes to stdout; pass `-o/--output-last-message <file>` to ALSO write that final message to a file on disk (the durable copy — prefer it over stdout scraping). `--json` streams events as JSONL (one JSON object per line) for machine parsing — the final result is the last `agent_message`/assistant event. The worker carries the five return fields in that final message; treat the message as a HINT, never the truth. Codex runs autonomously to completion under `-c approval_policy="never"`, so a dropped or garbled final turn is possible (UNPILOTED failure surface — codex's exact behavior on a mid-return connection drop is not corpus-validated; treat it like the kimi exit-75 class and reconcile from disk). The conductor reconciles every codex return against `git status` / `git log` of the work-dir and the cited evidence files on disk — disk wins on any disagreement. For a strictly-shaped final response, `--output-schema <file>` constrains the model's final JSON to a supplied JSON Schema.
<!-- The model package delta names this worker's exact return surface (e.g., the CLI's final-message flag, the evidence-file convention) here. The fields above never change. -->

---

## Invocation — the exact command shape

The codex CLI dispatch manual — the exact command shapes, flags, sandbox/approval grammar, exit handling, resume, and the codex task contract. Verified against **Codex CLI 0.137.0** (`codex --version` → `codex-cli 0.137.0`) on this machine. Re-verify with `codex --help` / `codex exec --help` / `codex --version` before relying on any flag — the CLI evolves fast; `--help` is ground truth for the installed build. Evidence boundary: the separate-process isolation property is live-proven (B4D); the p5-2 smoke probe then ran one real `codex exec` dispatch through this manual on 0.137.0 — it caught that `--ask-for-approval` was removed from the `exec` subcommand (now `-c approval_policy="never"`), and exercised Shape B stdin transport, `--sandbox workspace-write`, `--output-last-message`, and the five-field return (exit 0, file landed byte-correct). Facets NOT yet exercised — the non-zero exit taxonomy, resume inside a dispatch loop, self-commit — remain **UNPILOTED** and are marked where it matters.

### Pre-flight (before any dispatch)

| Check | Command | Gate |
|-------|---------|------|
| CLI present + version | `codex --version` (`codex-cli 0.137.0`) | Absent/older → re-verify flags against `codex exec --help`. |
| **Pinned-flag existence** (routing §4 gate) | `codex exec --help` grepped for every non-trivial flag this dispatch pins (`--sandbox`, `-C`/`--cd`, `--output-last-message`, `--add-dir`); the `-c approval_policy` override key confirmed via `codex exec --strict-config` | Runs EVERY dispatch (NOT only on a version mismatch — a flag can vanish at the SAME version family the manual pinned). Subcommand-aware: verify `codex exec --help`, never `codex --help`. Any pinned flag absent → STOP, do not dispatch; re-resolve at THIS delta, re-render (`../render-manuals.py`), re-run the gate — NEVER hand-edit the rendered manual or pass an ad-hoc flag. A removed/renamed flag is a hard `unexpected argument` exit-2 pre-spend if dispatched (p5-2: `--ask-for-approval` was removed from `exec` at 0.137.0 → `-c approval_policy="never"`). |
| Auth | `codex login status` (this machine → `Logged in using ChatGPT`) | Login is interactive (`codex login`, ChatGPT sign-in) OR `printenv OPENAI_API_KEY \| codex login --with-api-key`. First-time interactive login → USER-EXECUTED-ONLY; if unauthenticated, halt and ask the owner to run it; never automate the browser sign-in. |
| Project trust | target project has `trust_level = "trusted"` in `~/.codex/config.toml` `[projects.'<path>']`? | Untrusted → first-run interactive trust prompt (USER-EXECUTED-ONLY). Pre-trust the workspace or run codex once interactively there before headless dispatch. |
| Guidance file | target workspace has `AGENTS.md`? | Absent → offer to generate it via the mirror (`mirror_entry: codex-mirror`, see the codex `mirror-config.yaml`). Codex natively reads `AGENTS.md`. |

### The invocation shape — `codex exec` (non-interactive)

`codex exec` (alias `codex e`) runs Codex non-interactively. The prompt reaches the worker as a CLI argument OR via stdin (use `-` as the prompt, or pipe; if stdin is piped AND a prompt arg is given, stdin is appended as a `<stdin>` block).

**Shape A — prompt as CLI argument (small prompts):**

```powershell
codex exec --cd "<repo>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" "<task_prompt>"
```

Use when the prompt fits comfortably under the host shell's single-argument limit (Windows PowerShell ~32 KB). Default for short dispatches.

**Shape B — prompt via stdin (large prompts; default in autonomous mode):**

```bash
cat prompt.md | codex exec --cd "<repo>" --sandbox workspace-write -c approval_policy="never" \
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" -
```

Use when the prompt is large OR when running autonomously and you cannot afford a per-prompt size halt. The trailing `-` tells codex to read the prompt from stdin. **Both shapes** apply the same `--cd` scope, the same sandbox + approval policy, and pass the same allowlist + forbidden-ops checks on return. The composed **header + payload** (generic packaging §1) is written to `prompt.md` on disk and dispatched FROM that file — the same prompt file is the reuse surface on resume. (Windows note: PowerShell ~32 KB single-arg ceiling — prefer Shape B for any non-trivial prompt. Stdin piping via Shape B is the validated transport for codex on this machine — the p5-2 smoke probe ran Shape B from Git Bash, exit 0, the prompt reached the worker and the file landed.)

### Sandbox + approval grammar — the confinement axis

| Flag | Values | Use |
|------|--------|-----|
| `-s` / `--sandbox` | `read-only` · `workspace-write` · `danger-full-access` | The blast-radius control. `read-only` = analysis/research leaf (no file writes). `workspace-write` = code that edits the scoped work-dir (the bounded default for code). `danger-full-access` = NEVER unless the task explicitly sanctions it. |
| `-c approval_policy="<policy>"` | `untrusted` · `on-request` · `never` (config override; `codex exec` has NO `--ask-for-approval` flag on 0.137.0) | Headless MUST set `-c approval_policy="never"` (the model never pauses for human approval; failures return to the model). `untrusted`/`on-request` stall a headless run waiting for input. Set it as a `-c` dotted-path TOML override — the `--ask-for-approval` flag was removed from the `exec` subcommand (p5-2 smoke probe: `error: unexpected argument '--ask-for-approval'`). |
| `--dangerously-bypass-approvals-and-sandbox` | (flag) | Skips ALL approvals AND sandboxing. EXTREMELY DANGEROUS — only for an externally-sandboxed environment the task names. Forbidden by default. |
| `-C` / `--cd <dir>` | path | The agent's working root. Scope codex to the repo. |
| `--add-dir <dir>` | path (repeatable) | Extra writable dirs alongside the primary workspace. Keep minimal. |
| `--skip-git-repo-check` | (flag) | Required only when the work-dir is NOT a git repo (codex refuses outside a repo otherwise). |
| `--ignore-rules` | (flag) | Do NOT load user/project execpolicy `.rules` files. Use only when a workspace `.rules` file would wrongly block a sanctioned dispatch. |
| `--ignore-user-config` | (flag) | Do NOT load `~/.codex/config.toml` (auth still uses `CODEX_HOME`). Use for a clean, reproducible dispatch independent of the machine's personal codex config. |

**Confinement is the orchestrator's job (UNPILOTED reliability):** the sandbox is real, but its reliability as the sole confinement boundary for this orchestrator is not corpus-validated. ALWAYS back it with the post-run `git diff --name-only HEAD` of every changed path against the task's `allowlist` — the same reliable enforcement every CLI worker gets. Out-of-allowlist edit = halt + surface; NEVER auto-revert silently.

### Model + reasoning-effort settings → variants

The codex manifest declares routable variants — route on `(codex, variant)`:

| Variant | Flags / config | When |
|---------|----------------|------|
| `default` | (machine config: `model = "gpt-5.5"`, `model_reasoning_effort = "medium"`) | The mid-tier profile; partially-bounded code/analysis with `doubt_policy: halt`. |
| `high-reasoning` | `-c model_reasoning_effort="high"` (or the workspace's configured high-effort model) | Judgment-denser work that still routes to codex. Higher latency + spend. |

`-m/--model <id>` overrides the configured model per dispatch; `-c model_reasoning_effort="<low|medium|high>"` overrides reasoning effort (a `-c` dotted-path config override, TOML-parsed). `-p/--profile <name>` layers a `$CODEX_HOME/<name>.config.toml` profile on top of the base config. The configured model on this machine is `gpt-5.5` at `medium` effort (`~/.codex/config.toml`); a re-pointed model/profile changes the reasoning tier — re-confirm against the live config before routing. The exact reasoning-tier-to-boundedness mapping for codex is UNPILOTED; the manifest marks the package `probe-pending`.

### Exit handling

Codex `exec` returns a process exit code; `0` = success. A non-zero exit means the run did not complete cleanly — halt and surface; do NOT blind-retry. The precise non-zero exit-code taxonomy (which codes are retryable rate-limit/throttle vs non-retryable config/auth) is **UNPILOTED** on this machine — unlike kimi's documented exit-75, codex's retry semantics are not corpus-validated. Until a probe establishes them: on any non-zero exit, reconcile disk state, and if uncommitted in-allowlist work landed without the structured return, apply the disk-state recovery pattern below rather than re-running.

```powershell
codex exec --cd "<repo>" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message "<repo>/.codex-runs/<task-id>.txt" "<task>"; $code = $LASTEXITCODE
if ($code -ne 0) { <reconcile disk; recover-or-surface — do NOT blind-retry> }
```

### Disk-state recovery (work landed, return/commit lost) — UNPILOTED, judgment-only

Mirrors the kimi exit-75 recovery in shape; codex's exact drop behavior is unvalidated, so treat this as a candidate protocol, valid only under a high-reasoning conductor (a lower-reasoning conductor halts + surfaces). Trigger only when ALL hold: codex exited non-zero with NO structured return (no `status`, no commit hash) in the `--output-last-message` file/stdout; `git -C "<repo>" status --porcelain` shows uncommitted changes inside the allowlist; `git -C "<repo>" log -1 --pretty=%s` does NOT show the expected `[<task-id>]` prefix. Steps: (1) verify on-disk state against the task's Implementation Requirements; (2) run the declared `test_command` / smoke checks; (3) verify allowlist compliance (`git diff --name-only HEAD` — every changed path in the allowlist, else halt + surface); (4) verify forbidden-ops compliance; (5) commit manually with the mandatory `(orchestrator-recovered)` subject suffix:

```bash
git -C "<repo>" add <files-in-allowlist>
git -C "<repo>" commit -m "[<task-id>] <description> (orchestrator-recovered)" \
  -m "Co-Authored-By: Claude <noreply@anthropic.com>"
```

(6) log to the run-log: exit code, files verified + smoke result, the recovery commit hash, why not retrying, and that the reviewer MUST FULLY re-validate. The recovery commit is reversible (`git revert <hash>`). **Hung dispatch (codex never exits):** orchestrator kills it, evaluates disk state, then recover-commits (same steps) OR re-dispatches fresh.

### Resume mechanics

| Mechanism | Command | Use |
|-----------|---------|-----|
| Resume a specific session | `codex exec resume <SESSION_ID> "<follow-up>"` | After a `DOUBT_ESCALATED` / `NEEDS_CONTEXT` halt: supply the resolution into the SAME session by id (UUID or thread name). Add `-` as the prompt to read the follow-up from stdin. |
| Resume the most recent | `codex exec resume --last "<follow-up>"` | Pick up the newest recorded session for the cwd without tracking an id. `--all` disables cwd filtering. |
| Run without persisting | `codex exec --ephemeral …` | A dispatch that should leave NO session files on disk (no resume possible afterward). |

Resume is session-id based (`codex exec resume`). Resume reliability inside an autonomous dispatch loop is UNPILOTED — verify the session id round-trips before depending on resume for recovery; fall back to a fresh re-dispatch (the prompt file is the reuse surface) if resume does not engage.

### Known failure modes to pre-empt

| Failure | Pre-emption |
|---------|-------------|
| Headless stalls waiting for approval | ALWAYS set `-c approval_policy="never"` for a non-interactive dispatch; any other policy blocks. (`codex exec` has NO `--ask-for-approval` flag on 0.137.0 — passing it errors `unexpected argument`, p5-2.) |
| Refuses to run outside a git repo | Pass `--skip-git-repo-check` when the work-dir is not a repo. |
| First-run project trust prompt | Pre-trust the workspace (`[projects.'<path>'] trust_level`) or run codex once interactively there — USER-EXECUTED-ONLY; never clear it programmatically. |
| Interactive login required | `codex login` (ChatGPT) or `--with-api-key` via stdin is USER-EXECUTED-ONLY; halt + ask the owner. |
| Sandbox reliability as sole confinement (UNPILOTED) | Always back the sandbox with the post-run `git diff` vs allowlist; the sandbox is not corpus-validated as the only boundary for this orchestrator. |
| `cd` does not persist between shell calls | Each shell command is an independent subprocess — set `--cd`; never rely on `cd` chaining in the prompt. |
| Non-zero exit retry semantics (UNPILOTED) | Codex's exit-code taxonomy is not validated on this machine — on any non-zero exit reconcile disk + recover-or-surface, never blind-retry. |
| Final-message drop on a dropped turn (UNPILOTED) | Prefer `--output-last-message <file>` for a durable return; reconcile from disk on any garbled/absent return. |
| Machine config leaks into a reproducible dispatch | Use `--ignore-user-config` (and `--ignore-rules` if a workspace `.rules` wrongly blocks) for a clean, deterministic run. |

### The codex task contract (plugs into the shared authoring core)

A codex-executable task file extends the generic task-file contract (`{rbtv_path}/orchestration/workflows/_shared/authoring/`) with codex-specific frontmatter and body sections. The orchestrator validates a `executor: codex` task against this contract BEFORE dispatch; a missing required field = halt + report the malformed task — NEVER infer or mutate a field into shape (task shaping belongs to planning).

**Required frontmatter:**

```yaml
execution_kind: code            # or research/analysis for a read-only leaf
executor: codex
allowed_workdir: <absolute-or-project-root-relative repo path>   # → --cd
allowlist:
  - <file-or-folder-glob>
sandbox: read-only | workspace-write   # the tightest the task needs (never danger-full-access by default)
commit_policy: local-only | none       # none = conductor commits via rbtv-commit
test_command: <command-or-NONE>
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - --dangerously-bypass-approvals-and-sandbox
doubt_policy: halt
reviewer: claude-opus           # reviewer floor for codex-produced code is Opus (external-CLI code) — non-overridable
```

**Required body sections:** Goal (one bounded deliverable) · Context Snapshot (all task-specific context inlined — never make codex infer from broad PRDs) · Allowed Paths (the allowlist in human-readable form) · Forbidden Paths · Sandbox + Approval (the `--sandbox` value and the mandatory `-c approval_policy="never"`) · Implementation Requirements (exact behavior — interfaces, data shapes, error semantics, every edge case enumerated) · Validation (the exact commands codex runs before returning) · Commit Rule (local-only after validation, or none) · Return Format (the five-field return schema; land it via `--output-last-message`).

**Review gates** every codex coding task passes (verification card owns the gate): codex self-report → orchestrator diff-vs-allowlist check → declared validation passing (or explicit blocker) → Claude/Opus spec-compliance review → Claude/Opus code-quality review → no push until owner/final-workflow publishes. Any gate fails → halt or route a fix task; never proceed on "close enough". Codex is a SEPARATE-PROCESS worker (its one validated property, B4D) — the cold verifier and review pins apply exactly as for any external-CLI code worker.

### Recipes

```powershell
# Bounded code edit, durable return file (Shape A):
codex exec --cd "5-workbench/inni-cte-recon" --sandbox workspace-write -c approval_policy="never" `
  --output-last-message ".codex-runs/t1.txt" "<inlined task file content>"
```
```bash
# Large prompt via stdin (Shape B — default autonomous/Windows):
cat prompt.md | codex exec --cd "<repo>" --sandbox workspace-write -c approval_policy="never" \
  --output-last-message "<repo>/.codex-runs/t1.txt" -
```
```powershell
# Read-only analysis/research leaf (no writes), JSONL events for parsing:
codex exec --cd "<repo>" --sandbox read-only -c approval_policy="never" --json "<analysis task>"
```
```powershell
# High reasoning effort, clean of machine config:
codex exec --cd "<repo>" --sandbox workspace-write -c approval_policy="never" `
  -c model_reasoning_effort="high" --ignore-user-config "<task>"
```
```powershell
# Resume a halted session with the resolution:
codex exec resume <SESSION_ID> "<resolution to the open question>"
```
