---
execution_kind: code
executor: codex-cli
variant: default
allowed_workdir: C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv
allowlist:
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/server/api.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/server/deck_api.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/tests/test_deck_api.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/tests/test_api_save.py (new file allowed if cleaner)
sandbox: workspace-write
commit_policy: none
test_command: NONE — the CONDUCTOR runs pytest and the headed proof (your sandbox cannot execute repo Python; do NOT attempt, do NOT report as a blocker)
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - any git add/commit (conductor commits)
  - running stamp.py (conductor stamps)
doubt_policy: halt
reviewer: claude-code-native:opus at the re-run p2-checkpoint
---

## Goal

---
task_id: p2-7
status: pending
complexity_score: 9
human_review: required
---

# Task p2-7: own-asset colocation on the EDITOR/bridge save path — `/api/save-as` + `/api/dialog-save-as`
Saving from the EDITOR (or the builder↔editor leave-guard modal's "Save As…") to a NEW directory colocates the document's own `assets/*` files exactly like the builder save does: referenced own assets that exist beside the CURRENTLY-OPEN deck are copied to the destination `assets/`, missing ones are reported in `assets_missing`. Today `api.handle_save_as` (`server/api.py:162`) writes the HTML string and copies NOTHING — a parallel save path the colocation feature never covered (decisions.md, 2026-06-12). The owner's failing flow may use this path ("not sure / varies"), so all save paths must behave consistently.

**Path anchor:** `server/…`, `tests/…` relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`. Run `python -m pytest` from there.

## Context Files

**MUST read every file in the table below before any execution phase.**

| File | Purpose |
|------|---------|
| `server/api.py` (`handle_save_as` L162, `handle_dialog_save_as` L199, `handle_save` L217, `handle_open` L131, `get_open_path`/`set_open_path`) | The handlers to extend; `get_open_path()` identifies the source deck |
| `server/deck_api.py` (own-asset copy + chrome scan + `assets_missing`, all in `handle_deck_save`; helpers `_find_referenced_assets`, `_html_outside_spans`) | The semantics to FACTOR OUT and reuse — do not duplicate |
| `../decisions.md` | The 2026-06-12 two-endpoint discovery + every invariant |
| `tests/test_deck_api.py` | The colocation/missing unit-test conventions to mirror |

## Behavior

1. **Factor a reusable helper** (e.g. `colocate_own_assets(html, source_root, out_dir)` in `server/deck_api.py` or a shared module) from the existing logic: scan `html` for `assets/*` refs via `_find_referenced_assets`; for each — copy from `source_root` when present (skip-if-exists at dest → `assets_skipped`), else record in `assets_missing` (dedup, first-seen order). Returns `(assets_copied, assets_skipped, assets_missing)`. `handle_deck_save`'s chrome pass MAY be refactored onto it ONLY if behavior stays identical (its section pass with collision rename/rewrite stays as-is).
2. **`handle_save_as`:** after a successful write, when `get_open_path()` is set AND `Path(get_open_path()).resolve().parent != target.parent.resolve()` (a genuine save-to-a-DIFFERENT-dir), run the helper over the SAVED `html` with `source_root` = the open deck's parent; merge the three lists into the response (`assets_copied` always present, `assets_skipped`/`assets_missing` per the deck-save response conventions). Same-dir overwrite (including `handle_save`'s silent overwrite) and no-open-file cases: behavior byte-for-byte unchanged (no scan, response unchanged).
3. **`handle_dialog_save_as`:** colocation happens via its delegation to `handle_save_as` — it MUST run BEFORE `set_open_path` re-points to the new file (the source is the PREVIOUSLY open deck). Verify the ordering; today `set_open_path` runs after `handle_save_as` returns, which is correct — do not break it.
4. No rename/rewrite on this path (the editor html is saved verbatim; collisions at dest = skip-if-exists + `assets_skipped`). Builder `/api/deck-save` behavior unchanged.

## Constraints

- Minimal surgical diff; ONE shared implementation of scan+copy+missing — never two copies of the logic.
- `handle_save_as`'s existing error semantics (missing parent dir → 500, write failure → 500) unchanged; a colocation copy failure must NOT fail the save — record the ref in `assets_missing` (the HTML write already succeeded; degrade soft).
- Do not touch `app/**` in this task (the editor UI warning surface is a separate concern; server response fields first).

## Test Plan (unit — `tests/test_deck_api.py` or a new `tests/test_api_save.py` if cleaner)

- (a) open deck with `assets/x.png` beside it (simulate via `set_open_path`) → `handle_save_as` to a NEW dir: `assets/x.png` copied, `assets_copied == ["assets/x.png"]`, written HTML byte-identical to the input string.
- (b) same but asset file absent → `assets_missing == ["assets/x.png"]`, save succeeds.
- (c) same-dir save (target parent == open deck parent) → NO scan, response has no colocation side effects, HTML written.
- (d) no open file (`set_open_path(None)` / unset) → behavior unchanged from today.
- (e) `handle_save` silent overwrite → unchanged (routes to same-dir case).
- (f) existing suites stay green: `python -m pytest tests/test_deck_api.py tests/test_recompose.py -q` + `tests/e2e/test_pb11_deck_save.py`.

## Criteria

Unit tests (a)-(e) green + named suite green; headed proof: open a real deck copy (gsmm intro, WITH assets) in the EDITOR, Save-As to a new empty dir, `assets/` lands beside the saved file with the referenced images and the saved deck renders in the editor — evidence to `./done-gate-evidence/` (conductor runs the headed proof). Owner re-test of HIS flow is the final gate.

## Return contract

`status` · `landed` · `validation` (commands + EXIT + WALL_MS) · `concerns` · `open_questions`.

## Context Snapshot

- Work-target: the rbtv repo `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv` (branch `master`); hypresent app dir = `studio/hypresent/` inside it. ALL task-body paths anchor there.
- The working tree carries UNCOMMITTED prior work you BUILD ON (read CURRENT files, not committed versions): `server/deck_api.py` has the section colocation + collision rename + chrome scan (`_html_outside_spans`) + `assets_missing` collection; `tests/test_deck_api.py` has the colocation/missing test conventions.
- `[FULL READ]` before executing: `studio/hypresent/docs/plan/own-asset-colocation/decisions.md` (the 2026-06-12 two-endpoint discovery entry is your mandate) and `server/api.py` in full (it is small).
- `get_open_path`/`set_open_path` live in `server/api.py` (module-level open-file state set by `handle_open`). The unit tests can drive them directly.
- Do not touch other uncommitted files (tests/e2e/*, app/**, docs/**) or any foreign parallel-session files.

## Allowed Paths

Frontmatter `allowlist` = complete write surface: `studio/hypresent/server/api.py` (✎), `studio/hypresent/server/deck_api.py` (✎ — ONLY to factor the shared helper; no behavior change to `handle_deck_save`), `studio/hypresent/tests/test_deck_api.py` (✎) and/or a NEW `studio/hypresent/tests/test_api_save.py` (✚ if a separate file is cleaner).

## Forbidden Paths

Everything else — `server/server.py`, `server/recompose.py`, `app/**`, `tests/e2e/**`, `docs/**`, `5-workbench/**`.

## Sandbox + Approval

`--sandbox workspace-write` + `-c approval_policy="never"`. Launch root (`--cd`) = the vault root; the rbtv repo rides on `--add-dir`. Your rules load from the launch root; write ONLY inside the work-target per the allowlist.

## Implementation Requirements

- Implement the task's Behavior items 1-4 exactly. ONE shared scan+copy+missing implementation (factored helper), reused by `handle_save_as` — and by `handle_deck_save`'s chrome pass ONLY if its behavior stays byte-for-byte identical (its existing tests prove it).
- `handle_save_as` colocation fires ONLY on: write succeeded AND `get_open_path()` set AND resolved source parent != resolved target parent. Soft-degrade: a copy failure goes to `assets_missing`, never fails the save (the HTML write already succeeded).
- Response shape mirrors `handle_deck_save` conventions: `assets_copied` always present on the colocation-eligible path; `assets_skipped`/`assets_missing` keys per the same presence rules deck-save uses. Existing response fields (`ok`, `path`) unchanged; no-colocation cases return byte-identical responses to today.
- Minimal surgical diff; match each file's existing style.

## Validation

You cannot run pytest (sanctioned skip — report `SKIPPED_COUNT: 1`, reason: sandbox cannot execute repo python; conductor runs it). Make tests (a)-(e) correct by inspection against the existing conventions. The conductor runs the named suite + a headed editor-save proof after your return.

## Commit Rule

`commit_policy: none` — NEVER run git add/commit/push/reset. Leave changes uncommitted.

## Return Format

Final message BEGINS with `status: ` on line 1 (zero preamble), then `landed`, `validation` (with the sanctioned-skip entry), `concerns`, `open_questions`.

### Invocation note (launch flags — DATA only; derived-from: delta invocation section)

Derived flags from delta: `--version`, `--help`, `--ask-for-approval`, `--sandbox`, `--output-last-message`, `--cd`, `--add-dir`, `--strict-config`, `--with-api-key`, `--dangerously-bypass-approvals-and-sandbox`, `--skip-git-repo-check`, `--ignore-rules`, `-c`, `-C`, `-s`, `-m`, `-p`

Confinement diff: `git diff --name-only HEAD` run in the work-target's git, not the launch-root.

> These fields are emitted as data; the conductor supplies orchestrator-root and work-target values at dispatch.


## Pre-Dispatch Hook

A named pre-dispatch hook slot exists (`pre_dispatch_hook` in scaffold.py) — default no-op, always passes. Review 5 supplies the verify-or-supply body.


---

## Run-Binding Header (derived from dispatch-wrapper card + model delta)

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

**Codex-specific worker obligations** (on top of the generic binding addendum — never restating it):

| Obligation | What codex is bound to |
|------------|------------------------|
| **Sandbox + approval are the confinement, and they are the conductor's to set (UNPILOTED enforcement)** | Codex has a real native sandbox (`-s/--sandbox`: `read-only` · `workspace-write` · `danger-full-access`) and an approval policy. On Codex CLI **0.137.0** `codex exec` has NO `-a/--ask-for-approval` flag (it was removed from the `exec` subcommand — verified absent in `codex exec --help`, p5-2 smoke probe); the approval policy is set via the config override `-c approval_policy="never"` (a `-c` dotted-path TOML override — `approval_policy` is a recognized key, confirmed under `--strict-config`). A non-interactive dispatch MUST set `-c approval_policy="never"` (so the model never pauses for a human) paired with the TIGHTEST sandbox the task needs — `read-only` for analysis/research leaves, `workspace-write` for code that edits the work-dir, NEVER `danger-full-access` and NEVER `--dangerously-bypass-approvals-and-sandbox` unless the task explicitly sanctions it. The pairing `-c approval_policy="never"` + `--sandbox workspace-write` is the bounded-write default. The sandbox is real but its reliability as a confinement boundary for THIS orchestrator is UNPILOTED — back it with the same post-run `git diff --name-only` vs the allowlist that every CLI worker gets. |
| **Workspace scope is `-C`/`--cd` + `--add-dir`; the launch root is the ORCHESTRATOR root, never the work-target** | Set `-C <orchestrator-root>` (or run from that cwd) — the launch root codex auto-reads its `AGENTS.md` + rules from — and pass the actual **work-target** via `--add-dir <work-target>` (+ further minimal extra dirs only when needed). NEVER root codex at a nested-repo work-target: the mirror skips nested repos, so a worker rooted there loads zero behavior-rules (the a3e217d defect class). The work-target's own local `CLAUDE.md`/`AGENTS.md` conventions are NOT auto-loaded from `--add-dir` — the conductor inlines the load-bearing ones or marks them `[FULL READ]`. Files created/modified outside the work-target allowlist are an out-of-allowlist write the conductor catches on the post-run diff run in the WORK-TARGET's git (`git -C <work-target> diff --name-only HEAD`) — surface, never auto-revert. `--skip-git-repo-check` is required ONLY when the launch root is not a git repo (codex refuses to run outside a repo otherwise). |
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
