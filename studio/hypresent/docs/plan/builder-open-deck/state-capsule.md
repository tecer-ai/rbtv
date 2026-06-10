# State Capsule — builder-open-deck

> **Mutable file — overwriting is the contract.** The orchestrator atomically overwrites this file at each batch close and each reviewer close. Holds in-flight resume state ONLY — never an audit log (that is `run-log.md`, append-only) and never a worker-facing decision (that is `decisions.md`, append-only). A WORKER never reads this file.

> **Audience:** the next conductor session, resuming after interruption or context-refresh. Everything here exists to make resumption clean.

---

## Resume Point

- **Last completed:** B12 (p4-checkpoint) CERTIFIED + AUTO-PASSED 2026-06-10T05:33Z — Phase-4 feature-boundary COLD VERIFICATION, all-7-PASS audit-confirmed. Ran as TWO verifier sessions: session 1 (claude:sonnet) exercised all 7 criteria headed but graded C1 count-only + returned a non-conforming status + skipped `findings-p4.md` → conductor §1 gate caught all three → session-2 fix dispatch re-exercised C1 with content-level proofs (order via disk section-text; marker ` [CV-B12]` in final-tray row-0 srcdoc + crossing-2 bytes). One drift logged (phantom `disk_assertions` block) — conductor re-derived the order proof deterministically (`c1-fix-conductor-order-check.txt`). Opus audit confirmed all 7 (fixed the stale pointer in place), conditioned on surfacing 2 owner items. Statuses flipped (ADX-1). Evidence: `phase-4/evidence/findings-p4.md` + `findings-p4-opus-audit.md` + 27 files. **PHASE 4 COMPLETE (built + cold-verified).** (Earlier: phases 1-3 certified; `D-asset-colocation` + `D-bridge-runtime-ready` in force; HR carry-forward = findings-p2.md + findings-p3.md + **findings-p4.md w/ audit**.)
- **OWNER-JUDGMENT ITEMS (surface at next touchpoint + run close, owner decides acceptance):** (1) **C1 thumbnail legibility** — the round-trip edited text is PROVEN in the final tray thumbnail's content (DOM srcdoc + disk bytes) but is NOT pixel-legible at thumbnail scale (`held-surprising`-class); (2) **C7 enable-on-ready latency** — "Open in builder" disabled→enabled measured 155 ms (dialog open) / 187 ms (`?file=` open) on the owner's machine; acceptance per `D-bridge-runtime-ready` is the owner's call.
- **NEXT:** B13 (p5-refs) — CONDUCTOR-EXECUTED deterministic link check: verify all plan-internal links resolve and comply with the Plan Linking Standard (internal = file-relative, external = project-root-relative). No dispatch — the conductor runs it itself per the map. Then B14 (p5-compound, claude:opus) and B15 (p5-checkpoint, **HARD HALT — user approval required, NEVER auto-passed**).
- **On resume (B13):** reconcile run-log tail vs disk first (HEAD carries `beb85fe`; parallel sessions commit to master — `4a240cd`, `fe1ac3b` are foreign, hypresent untouched). B12 closed at a refresh-candidate=YES boundary — the refresh offer to the owner was made at close; honor whatever the owner chose.
- **⚠ WORKER NOTE:** kimi's usage limit has REFRESHED (owner notice 2026-06-10) — kimi:default is routable again for code. No remaining map batch is kimi-assigned (B12/B15 = claude:sonnet exercise, B13 = conductor, B14 = claude:opus), so no reroute-back is needed; relevant only if a revolving-plan fix/code task arises (re-run the pinned-flag gate before any kimi dispatch).
- **Last update:** 2026-06-10T05:35Z (B12 CERTIFIED + AUTO-PASSED, Phase 4 COMPLETE; statuses flipped; resume at B13 p5-refs; refresh offer + 2 owner-judgment items surfaced to owner)

## Run Configuration

- **Run mode:** end-to-end
- **Context-refresh:** suggest
- **Plan path:** studio/hypresent/docs/plan/builder-open-deck/builder-open-deck-plan.md
- **Decisions file:** studio/hypresent/docs/plan/builder-open-deck/decisions.md

## Approved Delegation Map

| Batch | Phase | Tasks | Worker (model, variant) | Reviewer timing | Refresh candidate |
|-------|-------|-------|-------------------------|-----------------|-------------------|
| B7 | 3 | p3-1 | kimi:default | claude:opus after task | no |
| B8 | 3 | p3-2 | kimi:default | claude:opus after task | no |
| B9 | 3 | p3-3 | qwen:default (RE-ROUTED from kimi 2026-06-10 — kimi 429 quota; owner chose qwen) | claude:opus after task | no |
| B10 | 3 | p3-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B11 | 4 | p4-1 | qwen:default (RE-ROUTED from kimi 2026-06-10 — kimi 429 quota; owner chose qwen, B9 precedent) | claude:opus after task | no |
| B12 | 4 | p4-checkpoint | claude:sonnet (exercise) | claude:opus review — auto-pass only if ALL criteria PASS | yes |
| B13 | 5 | p5-refs | conductor (deterministic link check) | — | no |
| B14 | 5 | p5-compound | claude:opus | claude:opus review | no |
| B15 | 5 | p5-checkpoint | claude:sonnet (exercise) | claude:opus review — **HARD HALT, user approval required** | — |

> Original map (intake 2026-06-09, plan defaults, CLI-fleet code backend) approved by user. Phases 1–2 batches collapsed into Completed Batches.

## Completed Batches

| Batch | Phase | Tasks | Worker | Status | Reviewer |
|-------|-------|-------|--------|--------|----------|
| B1–B3 | 1 | p1-1 · p1-2 · p1-checkpoint | kimi (cff2be0+4756b71, e9ce107) · claude:sonnet | Phase 1 CLOSED — builds CERTIFIED; checkpoint all-7-PASS, owner-approved 21:55Z | claude:opus — all clean |
| B4 | 2 | p2-1 | kimi (session 01b0dba3; commit b9aceef) | CERTIFIED — Open deck + ?file= + tray fill; pb2 regression green; spawned ADX-3 | claude:opus — DONE_WITH_NOTES, zero edits |
| B5 | 2 | p2-2 | kimi (session f44f82f6; 69cd7e2 + fold ea4efb3) | CERTIFIED — deck-themed thumbnails; ADX-3 stopgap removed; 5 e2e passed; headed proven; PB8-2b guard folded | claude:opus — DONE_WITH_NOTES, zero JS defects |
| B6 | 2 | p2-checkpoint | claude:sonnet exercise | CERTIFIED — all-6-PASS at floor, auto-passed (soft halt, end-to-end); HR = findings-p2.md | claude:opus — DONE_WITH_NOTES, all verdicts re-confirmed |
| B7 | 3 | p3-1 | kimi (session d41dcc3e; commit 8f7239c + fold dc990dd) | CERTIFIED — heterogeneous tray (uid identity, 3 kinds, duplicate, getItems); p2-2 tray invariant preserved (pb8 5-passed); full suite 17-passed | claude:opus — DEFECTS_FIXED (1 off-by-one folded), invariant verified |
| B8 | 3 | p3-2 | kimi (session 0e745997; commit 242a1e3 + fold e7f158e) | CERTIFIED — deck-mode library-add + blank-add (static button); regression pb8+pb9 green; suite 12-passed. [post-rename, in studio/hypresent] | claude:opus — DEFECTS_FIXED (latent null-libraryPath on deck-open folded + regression test) |
| B9 | 3 | p3-3 | **qwen** (RE-ROUTED from kimi; commit 4d55455 + fold 00e75d6) | CERTIFIED — Save-deck UI (new-file/overwrite); owner decks provably byte-unchanged; suite 19-passed. qwen's first code dispatch — allowlist-perfect | claude:opus — DEFECTS_FIXED (qwen had weakened test_pb11 reopen assertion to count-only; strengthened to disk-level restructure proof) |
| B10 | 3 | p3-checkpoint | claude:sonnet exercise | CERTIFIED — auto-pass (soft halt, all-6-PASS genuine); headed full restructure loop at floor; criterion-4 conductor-re-run 13-passed; owner decks SHA-256 unchanged. Evidence `phase-3/evidence/findings-p3.md`; forward finding D-asset-colocation. **PHASE 3 COMPLETE.** | claude:opus — ALL-PASS HOLDS (C2/C3 pre-flags resolved to genuine PASS vs spec+source); audit folded to findings-p3-opus-audit.md |
| B11 | 4 | p4-1 | **qwen** (RE-ROUTED from kimi; commit 5b72397 + fold beb85fe) | CERTIFIED — Save-and-switch bridge both directions; full 6-suite 29-passed stable ×3 (conductor re-run); owner decks untouched. Forward finding D-bridge-runtime-ready. **PHASE-4 BUILD COMPLETE.** | claude:opus review (DEFECTS_FIXED — row-4 test-weakening→strengthened) + claude:opus DEBUG §4 (DEFECTS_FIXED — conductor-caught suite-load flake root-caused to a real enable-before-runtime-ready product defect; gated enable on runtime `ready`) |
| B12 | 4 | p4-checkpoint | claude:sonnet exercise ×2 sessions (S1 all-7 headed; S2 C1-completion fix after conductor gate caught count-only grading + missing findings + bad status) | CERTIFIED — AUTO-PASS (soft halt, end-to-end, all-7-PASS audit-confirmed); C1 content-level proven (disk section-order + marker in tray DOM; conductor deterministic re-derivation `c1-fix-conductor-order-check.txt` after phantom-block drift); owner decks SHA-256 unchanged both sessions; 2 owner-judgment items carried (C1 thumbnail legibility; C7 latency 155/187 ms). Evidence `phase-4/evidence/findings-p4.md`. **PHASE 4 COMPLETE.** | claude:opus audit — ALL-PASS HOLDS, no overturn; C1 CONFIRMED-WITH-CAVEAT; fixed stale pointer in place; `findings-p4-opus-audit.md` |

## Active Red Sets

> Test files whose failures are PLANNED (a RED task landed; its GREEN pair has not). Halt-recovery §5 registers and retires these; a failure IN this list does not halt, a failure NOT in it still halts. Self-expiring — a retired green removes its row. Format: ONE test-file path per row, relative to the work-dir root — EXACT paths only, never globs.

| Red set (test file — exact path) | Registered by (RED task) | Retires when (GREEN task) |
|----------------------------------|--------------------------|---------------------------|

## Active Doubts / Blockers

- **Doubt escalated:** none
- **Blocker:** none — B12 CLOSED (certified + auto-passed 05:33Z). Nothing in flight.
- **Awaiting owner:** refresh offer at the B12 refresh-candidate boundary (continue this conductor vs fresh session for Phase 5), plus the 2 owner-judgment items above (informational unless the owner rejects — rejection reopens p4-checkpoint per the task's Gate flow). Next mandatory owner touchpoint after that = B15 (p5-checkpoint, HARD HALT).
- **Rename handover:** COMPLETE. Run continues in `studio/hypresent`; all forward paths rewritten.

## Notes for Resuming Conductor

Plan-backed run, all tasks SERIAL in plan order (no parallel waves). Shared-file serialization (ADX-3-updated): `builder-main.js`: p2-1→p2-2→**p3-1**→p3-2→p3-3→p4-1 · `tray.js`: p2-2→**p3-1** · `test_pb8_deck_open.py`: done. Hard-halt registry: p1-checkpoint (DONE) and p5-checkpoint NEVER auto-passed; p2 (DONE)/p3/p4 checkpoints auto-pass in end-to-end ONLY with all-PASS criteria. Root decks (`tecer-gsmm-introduction*.html`) are READ-ONLY owner data.

**p3-1 BINDING INVARIANT (from B5 review — put in the p3-1 dispatch header):** tray.js exposes `setSrcdocProvider(fn)` where `fn(rec,index)=>Promise<string>`; the provider takes precedence over `libraryPath` in `render()`, and `setLibrary()` clears it. p3-1 adds row-manipulation (uid identity, 3 kinds, duplicate, getItems) and MUST preserve this precedence + the setLibrary-clears-provider invariant — reorder/remove already re-invoke the provider correctly (PB8-2b guards it). Known pre-existing scope gap (NOT a defect): tray renders thumbnails EAGERLY; spec's 30+-slide lazy-render edge unbuilt for both row kinds — flag at p5 if a large-deck target emerges.

Rulings in force: **ADX-1** (conductor does ALL status flips; executors write only within allowlist), **ADX-2 + D2** (recompose preserves inter-slide separators; spec erratum at the bottom of `specs/deck-save-spec.md` — point every deck-save-spec consumer at it: p3-3 + checkpoints), **ADX-3** (p2-2 builder-main.js stopgap removal — DONE), **D1** (kimi guidance-file check satisfied via `.kimi-agent/code-agent.yaml`).

Dispatch mechanics (validated this run): prompt files `_dispatch-{task}.md` = header (binding obligations, ADX-extended allowlist if any, path-mapping table, five-field return schema) + verbatim task payload; dispatch via Bash background with ABSOLUTE paths (shell-cwd-drift lesson): `cat "<ABS>/studio/hypresent/docs/plan/builder-open-deck/_dispatch-{task}.md" | kimi --work-dir "<ABS>/studio/hypresent" --print --input-format text --final-message-only > "<ABS>/…/_kimi-run-{task}.log" 2>&1` + echo KIMI_EXIT (where `<ABS>` = `C:/Users/henri/Documents/second-brain/3-resources/tools/rbtv`). Pinned-flag gate before EVERY kimi dispatch (`kimi --help` grep; `--final-message-only` renders truncated as `--final-message…` — match on `final-message`). On return: §1 gate (commit hash in log, subject `[task-id]`, commit files == allowlist, tree clean, root decks clean, RE-RUN the test commands yourself), then opus review with pre-flagged brief (reviewer may fix in place, never commits — conductor folds reviewer fixes via explicit-path commit), then conductor flips statuses. Checkpoints: claude:sonnet COLD exercise (independent — no builder claims) → claude:opus findings audit → auto-pass on all-PASS (soft halts). e2e suite convention is HEADLESS (pb2–pb8, legitimate); headed fidelity floor lives in checkpoint exercises + task spot-checks.

Kimi sessions: p1-1 35fc3fde · p1-2 3be12714 · p2-1 01b0dba3-ba32-44f4-bc9a-44af4b998aad · p2-2 f44f82f6-69ff-4bd5-862e-19ea4d6416a9. Kimi commits land on rbtv `master` (kimi authed; exits: 0 ok, 1 non-retryable halt, 75 exit-75 recovery protocol in the kimi manual).

The rbtv repo working tree carries unrelated uncommitted changes from OTHER sessions (orchestration docs) — never `git add -A`; stage explicit paths only. The plan folder is TRACKED since commit 3766583; conductor bookkeeping edits show as tracked modifications and evidence + dispatch artifacts are untracked — committing the spine/evidence is a close-time decision via an rbtv-commit worker. Code commits so far: cff2be0, 4756b71, e9ce107, b9aceef, 69cd7e2, ea4efb3, 8f7239c, dc990dd (all on master, all `[task-id]`-prefixed). Non-code: cab4285 (spine checkpoint), 9288ede (html→studio rename). Note `3566150` is the parallel mirror-install session's `[p4-0]` merge — NOT this run's. Run-log timestamps 20:05–20:16Z were ~10 min ahead of true clock; 22:00Z onward accurate.

Core-protocol availability line is stale on `claude` (live `models/claude/` package exists with manifest + manual; also `manus` present) — trust disk; mismatch logged 19:39Z.

**Rename handover (html→studio) — ✅ DONE 2026-06-10 (owner rename committed `9288ede`; spine checkpoint `cab4285` preceded it; path-rewrite executed; relocated code re-verified pb9+pb4+pb8 17-passed).** Record of what was rewritten — `html/hypresent` → `studio/hypresent` in: (1) every remaining task frontmatter `work_dir:` + `allowed_workdir:` (phase-3/4/5 `.task.md`); (2) this capsule's `Plan path` + `Decisions file` + in-flight refs; (3) `run-log.md` `Spine location` + `Decisions file`; (4) the runtime launch commands (kimi `--work-dir`, the `cat` prompt path, the `> _kimi-run-*.log` redirect). UNCHANGED: `workspace: 3-resources/tools/rbtv`; `deliverables.md` + `_dispatch-*.md` path-mapping tables (work-dir-relative, carry no `html/hypresent` prefix). After rewrite, the rbtv repo's tracked paths are `studio/hypresent/...`; future kimi `[p3-x]` commits land there (allowlists are work-dir-relative — unchanged). Then dispatch p3-2 in `studio/hypresent`. Dispatch shell-cwd lesson: a prior diagnostic `cd` drifted the shell cwd and misfired the first p3-1 launch — ALWAYS use absolute paths in the kimi launch command (or `cd` to vault root first), never rely on the inherited cwd.
