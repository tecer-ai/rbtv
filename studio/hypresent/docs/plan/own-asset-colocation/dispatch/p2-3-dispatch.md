---
execution_kind: code
executor: claude-code-native
variant: opus
allowlist:
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/server/deck_api.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/server/server.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/server/api.py
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/app/js/builder/deck-save.js
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/app/js/builder/tray.js
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/tests/**
  - C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent/docs/plan/own-asset-colocation/phase-2/done-gate-evidence/**
  - "%TEMP% scratch dirs (deck copies + save-as targets) — create freely, never under the repo or tecer-biz"
commit_policy: none
test_command: python -m pytest  # from C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv/studio/hypresent
forbidden_ops:
  - git push
  - writes outside allowlist
  - destructive git reset
  - external production API calls
  - any write/delete on C:/Users/henri/Desktop/** (read-only surface)
  - any write under 5-workbench/tecer-biz/** (copy decks OUT to temp instead)
doubt_policy: halt
reviewer: OWNER (human halt gate — human_review: required)
---

## Goal

---
task_id: p2-3
status: in_progress
complexity_score: 13
human_review: required
---

# Task p2-3: BUG — real builder save-to-new-dir does NOT copy own-assets (live path diverges from the unit-tested handler)

## Severity

**Blocks the feature.** The phase-1 code is committed (`3ce0400`) and passes 52/52 unit+e2e tests, AND a direct `handle_deck_save` call copies assets correctly — but the OWNER's real builder save (open a real deck → restructure → Save-As to the Desktop) copies NOTHING. The feature does not work end-to-end. This must be root-caused before the plan can be called done.

## What happened (2026-06-12, during p2-1)

The owner saved a real gsmm/tecer pitch deck from the builder to `C:\Users\henri\Desktop\teste.html`. The saved HTML references its own slide images (`assets/founder-guilherme.png`, `assets/founder-henrique.jpeg`, `assets/founder-luiz.jpeg`, `assets/gsmm-logo.png`, `assets/tecer-wordmark-white.png` — all inside `<section>` bodies, verified), but **no `assets/` folder was created at the Desktop and no images copied**. Re-tested on a freshly started server — **same failure**.

## Path anchor

`server/…`, `tests/…` relative to the hypresent app dir `3-resources/tools/rbtv/studio/hypresent/`. Run `python -m pytest` from there (global Python 3.12 has pytest 9.0.3 + playwright chromium 1223). The hypresent server runs `python server/server.py` on `127.0.0.1:8765` (stdlib `http.server`, **NO auto-reload** — must be restarted to load code changes).

## What is already DONE / VERIFIED (do not redo)

- **Phase-1 code committed `3ce0400`** (rbtv repo, branch `master`): `server/deck_api.py` (+121: own-asset copy + collision rename via `_unique_asset_path`/`_rewrite_referenced_assets` + `existing.html` override path + 1:1 fragment-span guard + `assets_renamed` response), `server/recompose.py` (+12: optional `existing.html` override, `index` still drives separators), `tests/test_deck_api.py` + `tests/test_recompose.py` (own-asset + collision + boundary-safe + 1:1-refusal tests). Suite **52/52 green**.
- **The handler logic is CORRECT in isolation** — direct repro PROVED it:
  ```bash
  # from hypresent app dir; copies 5 assets, STATUS 200, creates out_dir/assets/
  python -c "
  import sys, pathlib, tempfile, os; sys.path.insert(0,'server')
  from recompose import split_sections
  import deck_api
  src = r'C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\investors\_decks\pitch-deck\small-deck-v3\tecer-pitch-deck.html'
  n = len(split_sections(pathlib.Path(src).read_text(encoding='utf-8')))
  out = tempfile.mkdtemp(); outp = os.path.join(out,'t.html')
  items = [{'kind':'existing','index':i} for i in range(n)]
  print(deck_api.handle_deck_save({'source_path':src,'out_path':outp,'items':items,'libraries':{}}))
  print(os.listdir(os.path.join(out,'assets')))
  "
  ```
- **The open-deck flow preserves the real path:** `api.py` `handle_open` → `set_open_path(str(p.resolve()))` (L153) and `set_doc_root(parent)` (L151); `deck-load.js` `loadDeckByPath(path)` returns `{path}`. So `deck.path` (= `source_path` the builder POSTs, per `deck-save.js`) is the real resolved deck location, whose dir has `assets/` beside it for a normal deck.
- **DISPROVEN root causes:** (a) stale/pre-patch server — owner re-tested on a fresh server, same failure; (b) assets referenced outside `<section>` — verified the founder/logo refs are INSIDE section bodies (`teste.html` L3371/3373/3465/3481/4376/4378); (c) open-flow re-points to a copy without assets — `api.py` resolves the real path.

## The divergence to root-cause (THE lead)

The unit-tested handler + a direct call both COPY assets, but the live builder save does NOT — for the same feature, same deck family. The bug is in the REAL builder→server save path, in something the direct repro did not replicate. Prime suspects, in order:

1. **The actual `source_path` the builder POSTs may not be the assets-bearing dir.** The owner's deck may have been opened from / re-pointed to a location WITHOUT `assets/` beside it (e.g. a prior Desktop save `teste.html` became `deck.path`, then re-saving from there has no `assets/` at `source_root`; or the deck was loaded from a standalone copy). The handler then hits `if not src_asset.exists(): continue` and silently copies nothing (spec Behavior row 5 — correct behavior, wrong input).
2. **The running server may not actually be executing `3ce0400`'s `deck_api.py`** — a stale `__pycache__/deck_api.*.pyc`, a DIFFERENT hypresent instance/checkout, or the server started from a different cwd. Confirm the live server imports THIS file.
3. **`items` from `tray.getItems()` after a restructure** may not be the `{kind:'existing','index':i}` shape the loop scans (or the indices don't cover the asset-bearing sections). `teste.html` IS restructured (slide order s01,s1b,s02,s1c,s05,s03,… non-sequential).

## Investigation plan (next session)

1. **Instrument the live path.** Add temporary logging to `handle_deck_save` (or a request log in `server/server.py`) that prints the received `source_path`, `out_path`, `len(items)` + item kinds, `source_root`, whether `source_root/'assets'` exists, and the final `assets_copied`/`assets_skipped`/`assets_renamed`. Have the owner reproduce the EXACT save (same deck, same Desktop target). Capture the real payload — this is the decisive evidence. (Remove the logging after.)
2. From the captured `source_path`: check `Path(source_path).resolve().parent / 'assets'` exists and holds the referenced files. If NOT → the bug is upstream (the deck was opened from / re-pointed to an assets-less location); decide whether the feature should also handle that (e.g. resolve assets relative to the deck's ORIGINAL source, or the doc-root). If it DOES exist → the bug is inside the handler's live execution → suspect #2 (stale bytecode / wrong instance) or #3 (items shape).
3. Confirm the live server runs `3ce0400` code: check `import deck_api; deck_api.__file__` from the server's interpreter, clear `__pycache__`, restart, retest.
4. Reproduce the FULL flow headed if needed (the e2e harness works: `tests/e2e/test_pb11_deck_save.py`, `builder_helpers.py`, `conftest_helpers.py`), driving an actual open→restructure→save-new and asserting `out_dir/assets/` on disk — extend p2-2's intent to the REAL open path, not a synthetic injected deck.
5. Fix at the root cause (prevent recurrence, per `rbtv-reasoning` root-cause discipline). Re-validate: the OWNER's real save creates `out_dir/assets/` with the images, AND the editor/builder render them.

## Context files

| File | Purpose |
|------|---------|
| `server/deck_api.py` `handle_deck_save` (L169-371) | The handler; the own-asset loop is L297-358 (scans `section_html = html[spans[idx]]` per `existing` item) |
| `app/js/builder/deck-save.js` | The builder POST: body `{source_path: deck.path, out_path, items, libraries}` — NO `html` field (server reads source from `source_path`) |
| `server/api.py` `handle_open` (L131-153) | Sets `open_path` = resolved deck path; `deck.path` derives from here |
| `app/js/builder/tray.js` `getItems()` | What `items` actually contains after a restructure |
| `../specs/own-asset-colocation-spec.md` | Behavior rows + invariants (row 5: missing source asset tolerated — the silent-skip path this bug likely hits) |
| `../decisions.md` | All decisions + the discoveries logged during this run |
| `./done-gate-evidence/2026-06-12-own-asset-colocation.md` | p2-1 done-gate sheet (editor render PROVEN; builder srcdoc gap noted) |

## Also note (separate, lower priority — do not conflate with this bug)

- **Builder thumbnail render gap (pre-existing, orthogonal):** builder slide thumbnails/stage render via `srcdoc` iframes (`app/js/builder/previews.js`, `tray.js`, `slide-stage.js`) with NO `<base>` tag → ALL relative `assets/…` refs 404 in the builder (own, library, pre-existing alike). The editor (`/doc/` route, `server.py` `set_doc_root`) serves from the real dir and renders correctly. The spec's "render in the builder" criterion is unachievable until a `<base>`-tag fix lands in the srcdoc machinery. This is NOT this bug and NOT a colocation defect — it is a candidate separate follow-up (a `<base>`-tag injection in `buildDeckSrcdoc`/preview srcdoc).
- **`assets_renamed` not surfaced in builder UI:** `deck-save.js` reads only `assets_copied`/`assets_skipped` from the response — `assets_renamed` is dropped from the status bar (display only, not a correctness bug).

## Criteria

Root cause identified (with the captured live payload as evidence); the OWNER's real builder save of a deck with its own `assets/*` to a NEW directory creates `out_dir/assets/` with the images, and they render in the editor (and builder once the srcdoc gap is separately addressed) — proven headed on the real deck, done-gate floor.

## Return contract

`status` · `landed` · `validation` (commands + EXIT + WALL_MS + the captured live payload) · `concerns` · `open_questions`.

## ADX-1 erratum (2026-06-12, conductor — appended, task body above unchanged)

Investigation plan step 1 says "Have the owner reproduce the EXACT save." The owner is AFK this session — do NOT wait on the owner mid-task. Amendment:

1. YOU reproduce the live save yourself, HEADED, driving the REAL builder UI (server `python server/server.py` on 127.0.0.1:8765, then Playwright or the existing e2e harness in `tests/e2e/` against the live page): open a deck → restructure (reorder/drop a slide) → Save-As to a NEW empty directory. Capture the instrumented payload on every save.
2. Reproduce BOTH scenarios: (a) a fresh COPY of `C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\investors\_decks\pitch-deck\small-deck-v3\` (deck + its `assets/`) placed in a temp dir — NEVER open or write the tecer-biz original; (b) the suspected owner scenario for suspect #1 — open a deck file whose directory has NO `assets/` beside it (e.g. a prior save-output) and save-as again.
3. Conductor-verified disk facts (2026-06-12): `C:\Users\henri\Desktop\teste.html` EXISTS and `C:\Users\henri\Desktop\assets` does NOT — you may READ `teste.html` (e.g. match its slide ids/content to candidate source decks to infer what the owner opened) but NEVER modify or delete anything on the Desktop. `small-deck-v3\assets\` exists. No server is currently running.
4. The owner's real-save confirmation remains the FINAL human-review step after your fix — it is the conductor's halt gate, not yours.

## Context Snapshot

- **Workspace root:** `C:\Users\henri\Documents\second-brain`. Hypresent app dir (your work-target): `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\` — a NESTED git repo (`3-resources/tools/rbtv/`, branch `master`, HEAD includes `3ce0400`). ALL `server/…`, `tests/…`, `app/…` paths in the task body are relative to the hypresent app dir.
- **Run decisions file `[FULL READ]`:** `C:\Users\henri\Documents\second-brain\3-resources\tools\rbtv\studio\hypresent\docs\plan\own-asset-colocation\decisions.md` — read it BEFORE starting; it carries the shaping decisions, invariants (byte-for-byte spans except colliding own-asset refs), and the blocker discovery.
- **Spec `[FULL READ]`:** `…\docs\plan\own-asset-colocation\specs\own-asset-colocation-spec.md` (Behavior rows + invariants).
- **Environment:** global Python 3.12 has pytest 9.0.3 + playwright with chromium 1223. Server: `python server/server.py` → 127.0.0.1:8765, stdlib http.server, NO auto-reload — restart after every server-code change; kill it when done. No server is running now (conductor-verified).
- **The rbtv repo may carry foreign uncommitted files from parallel sessions — do not touch anything outside your allowlist and do not run any git write operation.**

## Allowed Paths

The frontmatter `allowlist` is your COMPLETE write surface (✚ create / ✎ modify / ✗ delete). Notes:

- `server/*.py` + `app/js/builder/{deck-save,tray}.js`: instrumentation (temporary — remove or convert to a permanent, justified log line before returning) and the root-cause fix.
- `tests/**`: a regression test that captures the root cause at the REAL flow level (extend `tests/e2e/test_pb11_deck_save.py` or siblings).
- `docs/plan/own-asset-colocation/phase-2/done-gate-evidence/**`: ALL evidence files land here — captured payload logs, repro transcripts, screenshots, and an evidence sheet `2026-06-12-p2-3-live-save-bug.md` summarizing root cause + proof.
- `%TEMP%` scratch: deck copies and save-as target dirs.

## Forbidden Paths

- `C:\Users\henri\Desktop\**` — READ-ONLY (read `teste.html` for forensics; never write/delete there).
- `C:\Users\henri\Documents\second-brain\5-workbench\tecer-biz\**` — READ-ONLY (copy the small-deck-v3 deck + assets OUT to temp; never open-and-save the original in the builder in a way that writes there).
- Everything else outside the frontmatter allowlist.

## Implementation Requirements

- **Invoke `superpowers:systematic-debugging` via the Skill tool FIRST and follow it exactly** — this is a root-cause investigation; no fix before the root cause is named with the captured payload as evidence.
- If you drive the browser ad hoc (outside the pytest e2e harness), **invoke `rbtv-playwright-cli` (skill file: `C:\Users\henri\Documents\second-brain\.claude\skills\rbtv-playwright-cli\SKILL.md`) and follow it exactly**; the existing harness (`tests/e2e/builder_helpers.py`, `conftest_helpers.py`) is also at your disposal and already proven.
- Follow the task's Investigation plan §1-5 as amended by ADX-1 (you reproduce headed yourself; both scenarios a + b).
- Discipline (binding): root-cause over symptom; minimal surgical diff; reuse existing helpers; no speculative features; read callers before editing; an empty search result is NOT absence — verify with a second method. Remove every piece of temporary instrumentation before returning (or keep it only as a minimal permanent log line with a one-line justification in `concerns`).
- If the root cause turns out to be suspect #1 (assets-less `source_path` is the INPUT, handler correct): do NOT silently re-spec the feature — implement nothing beyond what the captured evidence justifies, document the finding + the candidate design options in the evidence sheet, and return `DONE_WITH_NOTES` with the design question in `open_questions` for the conductor/owner to rule on.
- Full unit+e2e suite (`python -m pytest` from the hypresent app dir) must be green before you return `DONE`/`DONE_WITH_NOTES` with a fix landed. Baseline is 52/52 + whatever you add. The flaky `test_tagging_does_not_move_marker` (F5 comments) is a known pre-existing flake — if it alone fails, re-run it standalone and report, do not chase it.

## Validation

Report in the `validation` field, each with command + EXIT + WALL_MS:

1. The captured live `/api/deck-save` payload(s) — cite the evidence file path holding them.
2. Headed repro BEFORE the fix (bug reproduced) and AFTER the fix (assets copied + render in the editor) — scenario (a) at minimum; scenario (b) result reported either way.
3. `python -m pytest` full suite from the hypresent app dir — EXIT 0.
4. Disk proof: listing of the save-target `assets/` dir after the fixed save.

## Commit Rule

`commit_policy: none` — you do NOT commit. NEVER run `git add`/`git commit`/`git push`/`git reset`. Leave all changes uncommitted in the working tree; the conductor reconciles and commits via `rbtv-commit`.

## Return Format

Your final reply's VERY FIRST line is `status: <DONE|DONE_WITH_NOTES|BLOCKED|DOUBT_ESCALATED|NEEDS_CONTEXT>` — zero preamble — followed by `landed`, `validation`, `concerns`, `open_questions` exactly as defined in §3 below. Also write the same five fields at the END of your evidence sheet in `done-gate-evidence/` (durable copy).

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
