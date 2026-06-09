# Decisions - builder-open-deck

> **Purpose:** This document captures shaping decisions, discoveries, constraints, and references that future agents need. The Original Shaping section is immutable. Other sections are append-only during routine execution.

---

## Original Shaping

### Scope Definition

**What this accomplishes:**
- Open an existing presentation deck in the builder and see its slides as a reorderable thumbnail tray.
- Reorder, remove, and duplicate the deck's existing slides; add blank placeholder slides; add slides from any slide library (inserted raw, unstyled).
- Save the restructured deck through a NEW server-side recompose path (never the library assembler), choosing new-file or overwrite.
- Bridge builder↔editor in both directions via save-and-switch (a Save-As crossing writes a NEW file, then opens it in the target view).

**What this does NOT include:**
- Saving slides back into a library (round-trip) — deferred.
- Marker/hash provenance system — deferred; saved decks stay clean.
- Theme reconciliation / auto-restyle when adding cross-library slides — user restyles later in the editor.
- Merging builder and editor into one page or live shared state — two-page architecture stands.
- Non-conforming decks: v1 targets decks with top-level `<section>` slides (the slide-library system's own output); arbitrary HTML is best-effort.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Home for restructuring | Builder (not editor) | Library augmentation is core; the editor has no library concept |
| Recompose location | **Server-side** (`server/recompose.py`) | Simpler to unit-test than a hidden-iframe client path; no browser tricks |
| Recompose technique | Byte-range section splicing — locate top-level `<section>` spans and reorder/remove/duplicate/splice them as raw text; NEVER parse-and-re-serialize the whole document | Whole-document re-serialization risks mangling inlined styles, scripts, SVG; raw spans preserve the deck byte-for-byte outside the spliced edits |
| Existing slides identity | Anonymous raw sections (positional index), no injected IDs or markers | Saved deck stays clean; provenance system is out of scope |
| Builder↔editor bridge | Save-and-switch: every crossing runs Save-As (new file), then opens it via the existing `?file=` handoff | No shared live state; never silently overwrites; user stepped back from "live flip" once the page-merge cost was visible |
| Explicit save semantics | Ask new-file vs overwrite on every explicit deck save | User chose "ask each time" over a sticky default |
| Blank slide markup | A plain `<section>` with minimal placeholder content; no `hyp-`/`data-hyp-*` markers | The editor's serializer strips `hyp-`-prefixed content; markers violate clean output |
| Orchestration | `orchestrated: true`, DEEP pre-resolution | User chose DEEP; executor kimi / reviewer claude-opus mirror the validated shortcuts-copypaste pairing |

### Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| ADX-2 — builder never duplicates engine assembly | `docs/decision-log.md` | Recompose is a NEW path manipulating a finished deck's own sections; it must not re-implement `assemble.py` |
| Clean standalone output | Editor strip-only serializer contract (`runtime/js/serializer.js`) | No provenance markers, no `hyp-` classes, no injected attributes in saved decks |
| Two-page architecture (D20) | `docs/decision-log.md` | builder.html and index.html stay separate pages |
| Per-deck inlined theme; library fragments carry no inline style | Library architecture | Cross-library adds render largely unstyled — accepted, restyle later |
| Windows-only native dialogs, same-origin server | Existing platform decisions | New path-picking dialogs follow the `_launch_dialog` PowerShell idiom with injectable launchers for tests |
| Added library fragments carry their own `assets/` | MECE gap caught in structuring | The recompose save MUST copy referenced assets into the deck's folder (the assembler does this today) |
| Owner's real decks at repo root (`tecer-gsmm-introduction*.html`) are READ-ONLY fixtures | Owner data safety | Tests copy them to temp locations before any save exercise; never write to the originals |

### User Inputs

| # | Input Topic | User's Input | Developed Into |
|---|-------------|--------------|----------------|
| 1 | Plan request | "plan structured-problem-2026-06-09.md" | This plan, built from the completed problem structuring |
| 2 | Orchestration mode | "Q1 A" (orchestrated — DEEP) | Full pre-resolution: per-task executor/reviewer, allowlists, validation commands, serialization order, hard-halt registry |
| 3 | Recompose fork | "Q2 A" (server-side) | `server/recompose.py` + `server/deck_api.py`; byte-range splicing constraint added to guard HTML fidelity |

### Collaborative Decisions

| # | Decision | User's Position | AI Contribution | Final Resolution |
|---|----------|-----------------|-----------------|------------------|
| 1 | Server-side recompose risk | Server-side (option A) | Counter: Python re-serialization can mangle complex HTML; proposed byte-range splicing, never whole-document re-serialization | Server-side WITH the byte-range splicing constraint as an architectural rule |
| 2 | Phase order | (from structured problem) risk order C→A→B→D | Mapped to buildable order: Save core first (de-risk), then Ingest, Compose, Bridge | Phases 1-4 = Save core, Ingest, Compose, Bridge |

---

## Standards Applied

### RBTV Standards

| Standard | Application in This Plan |
|----------|-------------------------|
| Task-file contract (`orchestration/workflows/_shared/authoring/task-file-contract.md`) | Every `.task.md` is zero-context: inlined excerpts with content anchors, explicit allowlists, return contract fields |
| Spec authoring (`orchestration/workflows/_shared/authoring/spec-template.md`) | Four specs in `./specs/`; tasks reference specs, never restate them |
| Done-gate fidelity floor (`rbtv-done-gate`) | Checkpoint criteria exercise the real app headed with real decks; evidence files captured during exercise |
| Decisions discipline (`orchestration/workflows/_shared/authoring/decisions-discipline.md`) | Entries below: decision + rationale + scope only; append-only |

### Plan-Specific Rules

| Rule | Enforcement |
|------|-------------|
| Byte-range splicing only — never re-serialize the whole deck through an HTML parser | Reviewer checks `recompose.py` for parse-and-rewrite patterns; unit test asserts untouched sections survive byte-identical |
| No `hyp-`/`data-hyp-*` markers in saved deck output | Checkpoint reviews saved files for marker leakage |
| Root decks are read-only fixtures | Allowlists never include root `*.html` decks; tests copy before saving |
| Dialog endpoints keep injectable launchers | New dialog code mirrors `set_dialog_launcher` so e2e tests can drive them |

---

## Decisions and Discoveries

> **APPEND-ONLY RULES:**
> 1. Only capture decisions, discoveries, and unexpected constraints — NOT routine task completions
> 2. NEVER modify previous entries
> 3. NEVER delete entries
> 4. Ask yourself: "Will this matter in one month?" If no, don't log it
>
> **What belongs here:** Decisions made during execution (with rationale), discoveries that change prior decisions, unexpected constraints
> **What does NOT belong:** Routine task completions ("created file X", "updated config Y")
>
> `decisions.md` entries: decision + rationale + scope ONLY — never file-lists or N→M narratives; supersede by appending, never rewrite.

<!-- Decisions and discovery entries will be appended below this line -->

### ADX-2 — Recompose preserves inter-slide separators (2026-06-09)

- **Decision:** `recompose` carries each existing section's trailing separator with it (deck-default separator for fragments/blanks/last-source-section); an identity recompose reproduces the source byte-for-byte. The spec's Context-Snapshot sketch ("prefix + items + suffix") is superseded (erratum appended to `./specs/deck-save-spec.md`).
- **Rationale:** The immutable shaping decision ("raw spans preserve the deck byte-for-byte outside the spliced edits") and Behavior row 1 ("inter-slide markup byte-identical") both require preservation; the function sketch was the authoring defect. Surfaced by the p1-1 Opus review: an identity save dropped 2,195 bytes of comment dividers on the owner's real deck.
- **Scope:** p1-1 (fix direction issued), and all consumers of `recompose` (p1-2, p3-3, checkpoints exercising saves).

### ADX-1 — Status-flip bookkeeping moved to the orchestrator (2026-06-09)

- **Decision:** Plan/task/deliverables status flips are performed by the orchestrator at verified return; executor allowlists remain deliverable-files-only.
- **Rationale:** Task allowlists exclude the plan folder, so executor-side flips would trip the post-run diff-vs-allowlist gate; run bookkeeping is registrar work and stays with the conductor (validated slide-expand precedent).
- **Scope:** All build tasks p1-1 → p4-1 (ADX-1 erratum appended to each); checkpoint tasks unaffected.

---

## References

> **Path format:** External files (outside this plan folder) use project-root-relative paths. Internal files (within this plan folder) use file-relative paths (`./`, `../`).

### Source Documents Analyzed

| Document | Key Insights Extracted |
|----------|----------------------|
| `./structured-problem-2026-06-09.md` | Problem tree (Ingest/Compose/Save/Bridge), MECE gaps (asset copy, non-conforming decks), priority order, v1 exclusions |
| `docs/spec/02-html-convention.md` | Decks are hint-optional; slides are top-level `<section>`s; serializer strips `hyp-` namespace |
| `docs/decision-log.md` | ADX-2 (no engine duplication), D20 (two pages) |

### Files to Load During Execution

| File | Purpose | When |
|------|---------|------|
| `server/api.py` | Editor save/open handlers + `_launch_dialog` PowerShell idiom + injectable launchers | p1-1, p1-2, p3-3 |
| `server/builder_api.py` | Library endpoints (`handle_library_asset` serves fragments), engine subprocess pattern | p1-2, p3-2 |
| `server/server.py` | Route table (`do_POST` dispatch) for new `/api/deck-*` routes | p1-2 |
| `app/js/builder/builder-main.js` | Builder entry: state, tray wiring, library load, assemble handoff | p2-1 → p4-1 |
| `app/js/builder/tray.js` | Tray model + render (id-keyed, dedup on add) | p2-2, p3-1 |
| `app/js/builder/previews.js` | srcdoc preview composition + caching | p2-2 |
| `app/js/main.js` | Editor `?file=` handoff block | p4-1 |
| `tests/e2e/` (`test_pb*.py`, `builder_helpers.py`) | Playwright e2e idiom for builder tests | every UI task |
