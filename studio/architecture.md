# Studio Module — Architecture

> The blueprint every Phase-2 builder builds against. Maps the five subsystems (Process · Roles · Tools · Standards · Memory) to concrete studio components with landing paths, names every entry surface with its user-invocable-vs-internal verdict, fixes the file layout under `studio/`, and defines the exact Strategist→Designer content-spec contract. Behavior specs in `./` (deck path: the deck-loop-spec in the plan folder) own the *what*; this doc owns the *where* and the *shape*. Authored at `p1-4`; site/app sections are deliberately lean (D8) and get adapted at `p3-checkpoint`.

**Scope frame (binding):** the plan `decisions.md` is the authority on scope, dispositions, and constraints — this doc never restates it, it lands the architecture those decisions imply. The deck path is concrete; site + app are sketched. The v1.1 critic, 5 deferred capabilities, and improve-existing mode are named as roadmap anchors only, never built here.

---

## 0. Module Identity & Substrate

| Fact | Value |
|------|-------|
| Module folder | `studio/` (rename of `html/` — `p1-1`/`p1-2`; hypresent + slide-library rode along content-untouched) |
| What it is | One resumable, phase-first HTML **design + communication** pipeline; artifact (deck / site / app-UI) is a PARAMETER each phase adapts to, never a top-level branch |
| Output substrate | HTML-native for every artifact — full-screen browser + print-to-PDF (D7). No PPTX, ever |
| Two worker classes | **Strategist** (discover → narrative → content-spec: *what to say, what each datum must communicate*) hands a spec to the **Designer** (art-direction → layout → visual: *making it awesome and distinct*) |
| Quality model | Reference-anchored + **HUMAN final gate** (D1); input-side anti-slop mechanics are the load-bearing novelty; automated critic is v1.1 (D2), never gates aesthetics |
| Resident, untouched | `studio/hypresent/**` and `studio/slide-library/**` — parent-path rename ONLY; this build writes nothing inside them (see §6) |

---

## 1. Component Map — the Five Subsystems

Each subsystem → its concrete studio components + landing path + disposition (CREATE-new / REWORK-existing / MINE-from / REUSE-as-is / ROADMAP). Paths are repo-relative to `studio/` unless marked otherwise. Path-shapes for components built in P2+ are the **prescribed layout** this architecture fixes; the building task creates them.

### 1.1 PROCESS — the artifact-general phase spine

The deck path is the proven instance of the spine; site/app are forks adapted at `p3-checkpoint`.

| Component | Landing path | Disposition | Notes |
|-----------|--------------|-------------|-------|
| **Studio loop workflow** (the phase spine entry) | `studio/workflows/studio-loop/workflow.md` | CREATE (`p2-3`+) | The 4-beat deck loop: message-lock → references+art-direction → HTML generation (trio → slices → fresh-eyes) → human gate. Behavior governed by `deck-loop-spec.md`. Replaces `deck-design` |
| Beat 1 — message-lock (Strategist) | `studio/workflows/studio-loop/beats/beat-01-message-lock.md` | CREATE (`p2-3`) | Produces the content spec (§5). Zero design decisions. Strategist craft mined from office `pitch/` steps 01–06 |
| Beat 2 — references + art-direction | `studio/workflows/studio-loop/beats/beat-02-art-direction.md` | CREATE (`p2-4`/`p2-6`) | ≥2–3 distinct direction mini-briefs on the loaded reference set; owner-picked. Obeys ban-list |
| Beat 3 — HTML generation | `studio/workflows/studio-loop/beats/beat-03-generate.md` | CREATE (`p2-7`+) | Template trio (pairwise) → slice-by-slice via fresh contexts → fresh-eyes pass. Chart mechanism resolved at the `p2-2` spike |
| Beat 4 — human gate | `studio/workflows/studio-loop/beats/beat-04-human-gate.md` | CREATE (`p2-10`) | Headed-browser accept/bounce; surgical patch; bounce-cap ≈3/slide → message rethink (H8) |
| Artifact/mode fork rules | folded into `workflow.md` frontmatter + beat conditionals | CREATE | `artifact` (deck/site/app) + `mode` (blank-slate; audit deferred) as parameters, keyed like the office pitch `{pitch_type}` conditional pattern |
| **Site path** | `studio/workflows/studio-loop/forks/site.md` | BUILT (`p5-5`) | Same spine; multi-page; leans on images/animation. Runs in `site-marketing` Strategist mode |
| **App path** | `studio/workflows/studio-loop/forks/app.md` | BUILT (`p5-8`) | Discovery forks to goal→user-flow; output = plain HTML UI + UX companion docs for a coding agent to wire. Runs in `app-product` Strategist mode |
| `deck-design/` workflow + `steps-c/`,`steps-e/`,`data/` | `studio/workflows/deck-design/` | REPLACED → mined (`p1-6`) → DELETED (`p4-2`) after the GSMM proof passes | Until deletion it stays callable (no broken window) |

### 1.2 ROLES — workers & personas

One Strategist (audience modes), one Designer. Art-direction is the Designer's opening sub-phase, not a separate role.

| Component | Landing path | Disposition | Notes |
|-----------|--------------|-------------|-------|
| **Strategist persona** | `studio/personas/strategist.md` | CREATE NEW (`p2-3`/`p2-4`) | ONE persona, audience MODES: investor (Roelof-mined), client (Leo-mined), site-marketing (P5), app-product (P5). Drives beat 1; authors the content spec |
| **Designer persona** | `studio/personas/vivian.md` | REWORK (existing → studio Designer) | Vivian retargeted: art-direction → layout → visual. Menu points at the studio loop, not `deck-design`. `[BV]` brand-visual item keeps pointing at the innovation module (cross-module — manifest `cross_module_agents.vivian`) |
| `roelof.md` (Investor) | `office/personas/roelof.md` | MINED into Strategist investor mode → DELETED at `p4-3` | Stress-test craft + investor vocabulary mined; not moved |
| `leo.md` (Buyer) | `office/personas/leo.md` | MINED into Strategist client mode → DELETED at `p4-3` | Procurement-defense craft mined |
| `rbtv-designing` skill (loader) | `studio/skills/designing/SKILL.md` | REWORK | Designer entry loader → points at reworked `vivian.md` (see §3 entry surfaces) |

### 1.3 TOOLS — one shared capability layer (workers invoke on demand)

v1 ships reference-LOADING only; the other capabilities are roadmap. The module ENFORCES references, never ships them (D4).

| Component | Landing path | Disposition | Notes |
|-----------|--------------|-------------|-------|
| **Capability registry** | `studio/capabilities/registry.md` | CREATE (`p1-7` fills it) | How a worker discovers + invokes a capability. The single index P2 capability work registers into (§7) |
| Reference-loading (v1's only shipped capability) | `studio/capabilities/load-references.md` | CREATE (`p2-1` scaffolds the ref-set contract) | Loads THIS project's reference set from the workspace path (§4); HALTS on missing layer. NOT an authoring tool |
| extract-tokens (from live site) | `studio/workflows/design-extraction/` + `studio/commands/design-extractor.md` | REUSE → re-registered (`p1-7`), aligned (`p5-4`) | Existing token output shape: `design-extraction/templates/design-tokens.json` |
| image→JSON | `studio/workflows/vision-to-json/` + `studio/commands/vision-to-json.md` | REUSE → re-registered (`p1-7`), aligned (`p5-4`) | Forensic image→strict-JSON + regeneration prompts |
| browser-automation (render/screenshot/QA infra) | `studio/workflows/browser-automation/` + `studio/skills/playwright-cli/SKILL.md` | REUSE AS-IS | Powers fresh-eyes rendering, headed-review screenshots, done-gate evidence. Local HTTP server pattern — `file://` is blocked |
| extract-subtle-refs (motion/interaction) · image-gen (multi-provider, Gemini-first) | `studio/capabilities/` (roadmap stubs) | ROADMAP (D10) | Source-pluggable image-gen interface; named, not built in v1 |

### 1.4 STANDARDS — make "world-class AND distinct" a testable gate

The module enforces the standard; the reference set + taste file are workspace-owned (D4). v1 = input-side mechanics + human gate; critic = v1.1.

| Component | Landing path | Disposition | Notes |
|-----------|--------------|-------------|-------|
| **Standards bundle** (ban-list, flaw checklist, craft rules) | `studio/standards/` | CREATE (`p2-5`) — MINED from `deck-design/data/*` | `ban-list.md` (default attractors, H4) · `flaw-checklist.md` (~10-item fresh-eyes checklist, H6) · `craft-rules.md` (design/data-integrity/print rules) |
| Mining sources | `studio/workflows/deck-design/data/{html-patterns,html-components,pitch-deck-rules}.md` | MINED into the Standards bundle; retire with `deck-design` | Living corrections → ban-list + flaw checklist + craft rules |
| Reference-set CONTRACT (what the workspace must supply) | documented in `studio/capabilities/load-references.md` + `studio/standards/reference-set-contract.md` | CREATE (`p2-1`) | tokens file (color/type/spacing/motion) + `exemplars/` screenshots + **taste file** (3–5 admirable-principle bullets per exemplar, H3) + a chart exemplar. Workspace path: `5-workbench/tecer-biz/brand/studio-references/` |
| Distinctiveness/anti-slop rule(s) | `studio/standards/anti-slop.md` (module-internal standard, not a `.claude/` rule) | CREATE (`p2-5`) | Encodes: explicit art-direction beat · divergent reference use (principles, not copy) · ≥2–3 forced-distinct mini-briefs · pairwise trio · fresh-eyes pass |
| Design done-gate (deck) | governed by `deck-loop-spec.md` Test Plan + the always-on `rbtv-done-gate` rule | (no new file) | Evidence root `1-projects/rbtv-evolution/coding/done-gate-evidence/studio-gsmm-deck/` |
| **Critic** (comparative · taxonomy-driven · structural-auto/aesthetic-HUMAN · per-project) | `studio/critic/` + `critic-spec.md` | ROADMAP — built P6 (`v1.1`); evaluator pinned `claude:fable` at `p6-checkpoint` | NEVER gates aesthetics. Named here as the v1.1 anchor only |

### 1.5 MEMORY / COORD — persist, resume, switch

The module does NOT build a state engine. It defines a **payload** that rides the orchestration three-file state spine (the spine is the convention; the payload is module-specific).

| Component | Landing path | Disposition | Notes |
|-----------|--------------|-------------|-------|
| **Design-state schema** | `studio/state/design-state-schema.md` | CREATE (`p1-5` fills it; this doc fixes the slot) | The module-level artifact (§8). Rides the spine, never replaces it |
| Resume / worker-switch protocol | documented in the schema file + `studio-loop/workflow.md` | CREATE | Any fresh agent (or Strategist↔Designer switch) resumes from design-state + the reference set ALONE — zero conversation history (deck-loop-spec behavior ⑨) |
| State spine it rides on | `orchestration/skills/orchestrating/cards/state.md` (the three files: `run-log.md` append-only audit · `state-capsule.md` mutable resume · `decisions.md` worker-facing) | REUSE (pointer only) | The design-state file is a run artifact a worker reads alongside its task file + the run's `decisions.md`; it is NOT a fourth spine file. See §8 |

---

## 2. Entry Surfaces — with the install verdict (DECISION-BEARING)

> **This section resolves the `p1-3` discovery and binds `p1-7`, `p4-1`, `p6-3`.** It states, for each named entry surface, whether it is **user-invocable** (requires studio to enter the install set + a `.claude/` loader) or **module-internal** (reached only via an already-installed entry point).

### 2.1 The discovery (verified on disk, as of p1-3 — SUPERSEDED by the p6-checkpoint flip; see §2.2)

The studio module **was NOT in this vault's install set at p1-3**. `rbtv.json` then declared `modules: [core, office, orchestration, builder, coding]`. The studio manifest's user-facing components — `rbtv-designing`, `rbtv-playwright-cli` skills; `rbtv-design-extractor`, `rbtv-vision-to-json` commands — are **absent from `.claude/`** (verified: no such loaders present; only office's `rbtv-pitcher` reaches studio). `install.py` installs only the five declared modules. Studio's own manifest entries (§ `studio` block) describe loaders that would land **if and only if** studio joins the install set.

### 2.2 The decision

**Decision (original, p1-4): keep studio MODULE-INTERNAL for v1; the deck loop is entered through the already-installed `/rbtv-pitcher` (office) retargeted at P4.** The rationale was to minimise install-set churn and ride on the proof before adding standalone front doors (D8).

**Decision superseded at p6-checkpoint (2026-06-10): studio added to the install set.** The owner approved the flip at p6-checkpoint; the install executed that day. Four surfaces are now live: `rbtv-designing` + `rbtv-playwright-cli` skills; `/rbtv-design-extractor` + `/rbtv-vision-to-json` commands. The Strategist and the studio loop beats remain loop-internal BY DESIGN — reached via `/rbtv-pitcher`, not as standalone commands. The proof-gating clause no longer applies; the install decision was executed without requiring the GSMM deck proof (D7 struck the deck proof from the plan).

**Decision superseded again (2026-06-10): the loop entry moved into studio and was renamed.** The owner moved the entry command out of office and renamed it `/rbtv-pitcher` → `/rbtv-strategist`; the command (`studio/commands/strategist.md`, manifest `studio` module) now opens the Strategist directly. This executes the "optional standalone loader" noted as a post-v1 decision in §2.3 — the Strategist is no longer office-entered or loop-internal-only; it has its own studio command. The dated p1-3/p1-4 prose below records the prior `/rbtv-pitcher` (office) state as historical fact and is left unchanged.

### 2.3 Per-surface verdict

| Entry surface | Name (loader / command) | Verdict | Reached how | Wiring task |
|---------------|-------------------------|---------|-------------|-------------|
| **Deck loop — owner entry (v1)** | `/rbtv-pitcher` (office, **already installed**) retargeted to the studio loop | **module-internal** (today) | Owner runs the installed `/rbtv-pitcher`; its handoff dispatches into `studio/workflows/studio-loop/` (Strategist beat 1) | **`p4-1`** retargets the handoff destination (manifest-allowlisted slot) |
| **Designer** | `rbtv-designing` skill → reworked `vivian.md` | **user-invocable** (installed 2026-06-10) | Reached via the loop (via `/rbtv-pitcher`) OR invoked directly via the `rbtv-designing` skill to resume from a design-state path | **executed** at p6-checkpoint flip |
| **Strategist** | (no standalone loader in v1) — runs as the loop's beat-1 persona | **module-internal** | The loop invokes `studio/personas/strategist.md`; no separate user command in v1 | Optional standalone loader is a `p6-3`/post-v1 decision, not required |
| **playwright-cli** | `rbtv-playwright-cli` skill | **installed** (2026-06-10) | REUSE-as-is rendering/QA infra — invoked by the loop and done-gate evidence; also available standalone via the `rbtv-playwright-cli` skill | executed at p6-checkpoint flip |
| **extract-tokens** | `/rbtv-design-extractor` command | **user-invocable** (installed 2026-06-10) | Invoked on demand via the capability registry during the loop OR directly as `/rbtv-design-extractor` | executed at p6-checkpoint flip |
| **image→JSON** | `/rbtv-vision-to-json` command | **user-invocable** (installed 2026-06-10) | Same | executed at p6-checkpoint flip |

### 2.4 Downstream implications (carried to `concerns`)

- **`p1-7`** registers capabilities into `studio/capabilities/registry.md` — a module-internal index, NOT a `.claude/` install. No install wiring required at `p1-7`.
- **`p4-1`** retargets the EXISTING `/rbtv-pitcher` handoff (the one installed surface) to the studio loop. This is the v1 user entry; it is a manifest description edit at the serialized P4 slot, not a new studio install.
- **`p6-3` (executed at p6-checkpoint, 2026-06-10):** studio added to the install set. The four surfaces listed in §2.3 are live. The Strategist and the loop beats remain loop-internal by design — the install added the reuse capabilities' commands and the Designer/playwright-cli skills; the Strategist has no standalone command (as noted in §2.3).

---

## 3. File Layout Under `studio/`

The prescribed tree (✚ = built in this plan; existing kept; resident = untouched). Builders create files at exactly these paths.

```
studio/
├── architecture.md                      ← THIS doc (p1-4)
├── personas/
│   ├── strategist.md                    ✚ CREATE (p2-3/p2-4) — one persona, audience modes
│   └── vivian.md                          REWORK → studio Designer (menu retargeted)
├── workflows/
│   ├── studio-loop/                     ✚ CREATE — the phase spine (replaces deck-design)
│   │   ├── workflow.md                  ✚   spine entry + artifact/mode fork rules
│   │   ├── beats/
│   │   │   ├── beat-01-message-lock.md  ✚   Strategist → content spec
│   │   │   ├── beat-02-art-direction.md ✚   references + ≥2–3 mini-briefs
│   │   │   ├── beat-03-generate.md      ✚   trio → slices → fresh-eyes
│   │   │   └── beat-04-human-gate.md    ✚   headed accept/bounce + bounce-cap
│   │   └── forks/
│   │       ├── site.md                  ✚ BUILT (p5-5) — artifact: site fork
│   │       └── app.md                   ✚ BUILT (p5-8) — artifact: app fork
│   ├── deck-design/                       REPLACED → mined (p1-6) → DELETED (p4-2)
│   ├── browser-automation/                REUSE AS-IS (render/screenshot/QA infra)
│   ├── design-extraction/                 REUSE → re-registered (p1-7)
│   └── vision-to-json/                    REUSE → re-registered (p1-7)
├── capabilities/                        ✚ CREATE — the shared capability layer
│   ├── registry.md                      ✚   capability discovery/invocation index (p1-7)
│   ├── load-references.md               ✚   v1's only shipped capability (p2-1 contract)
│   └── (roadmap stubs: extract-subtle-refs, image-gen)   ROADMAP (named, not built)
├── standards/                           ✚ CREATE (p2-5) — mined from deck-design/data/*
│   ├── ban-list.md                      ✚   default-attractor ban-list (H4)
│   ├── flaw-checklist.md                ✚   ~10-item fresh-eyes checklist (H6)
│   ├── craft-rules.md                   ✚   design/data-integrity/print rules
│   ├── anti-slop.md                     ✚   distinctiveness mechanics standard
│   └── reference-set-contract.md        ✚   what the workspace must supply (D4)
├── state/                               ✚ CREATE
│   └── design-state-schema.md           ✚   design-state payload schema (p1-5)
├── critic/                                ROADMAP — built P6 (v1.1); critic-spec.md anchor
├── commands/
│   ├── design-extractor.md                REUSE (loader → design-extraction workflow)
│   └── vision-to-json.md                  REUSE (loader → vision-to-json workflow)
├── skills/
│   ├── designing/SKILL.md                 REWORK (loader → reworked vivian.md)
│   └── playwright-cli/SKILL.md            REUSE AS-IS (browser-automation loader)
├── hypresent/                             RESIDENT — UNTOUCHED (parent-rename only)
└── slide-library/                         RESIDENT — UNTOUCHED (wired to hypresent)
```

**Layout conventions (binding on builders):**
- Persona files follow the existing `vivian.md`/`roelof.md` XML-agent shape (activation → menu-handlers → rules → persona → menu).
- Workflow step/beat files follow the office/deck micro-file convention: self-contained, read-fully-before-acting, sequential, halt-at-menu.
- `studio/standards/` holds **module-internal** standards (mined data + checklists), NOT `.claude/` rules. The always-on `.claude/` rules (`rbtv-done-gate`, etc.) are not duplicated here.
- `hypresent/` and `slide-library/` are residents — no file under either is created, modified, or deleted by any studio-build task. A `✎`/`✗` under either tree in any worker diff = defect.

---

## 4. The Reference Set (workspace-owned, module-enforced)

The module LOADS and ENFORCES; it never authors or ships references (D4). Located at the workspace path `5-workbench/tecer-biz/brand/studio-references/` (scaffolded by `p2-1`). The reference-set contract (`studio/standards/reference-set-contract.md`) prescribes the four required layers:

| Layer | Content | On absence |
|-------|---------|-----------|
| Tokens file | color / type / spacing / motion (shape: `design-extraction/templates/design-tokens.json`) | HALT with named missing layer — never proceed on training-mean defaults |
| `exemplars/` | world-class exemplar screenshots | HALT |
| **Taste file** | 3–5 admirable-principle bullets per exemplar (H3 format) | Art-direction beat HALTS to owner; never substitutes model taste silently (`p3-gate` clears this for the GSMM run) |
| Chart exemplar | one reference chart slide | HALT (chart beat blocked) |

---

## 5. Strategist→Designer Content-Spec Contract (THE handoff)

> The exact document the Strategist (beat 1) produces and the Designer (beat 3) consumes. Meets the `deck-loop-spec.md` behavioral floor: **deck thesis · one point per slide · narrative arc · per-datum communication intent · owner-supplied verified numbers with sources.** Zero design language in it (design decisions live in the art-direction pick + trio, recorded in design-state). The Designer reads this from disk + design-state alone — no conversation context.

**File:** `{output_folder}/artifacts/content-spec.md` (the `{output_folder}` resolved per `rbtv-output-resolution`, same folder the loop's design-state references). This supersedes the v0 split (`pitch-narrative.md` + `pitch-structure.md`) the office pitch workflow produced — it folds both into ONE owner-observable content spec; the mined Strategist beats write this shape.

### 5.1 Document shape

```markdown
---
type: content-spec
artifact: deck                    # deck | site | app — the PROCESS parameter
mode: blank-slate                 # blank-slate (audit deferred)
audience_mode: investor           # investor | client | site-marketing | app-product
project: '{project_name}'
artifact_language: '{lang}'
date: {YYYY-MM-DD}
design_state: ./design-state.md   # back-pointer; design lives THERE, never here
---

# Content Spec — {project_name}

## Thesis
{The deck's SINGLE controlling thesis — one sentence. What the whole deck must make the audience believe/do.}

## Narrative Arc
{The ordered logical spine: how the argument moves slide-to-slide to land the thesis.
 Prose or a short ordered list — NOT a slide table. This is the "why this order" the Designer must preserve.}

## Slides
### Slide {n} — {working title}
- **Point:** {the ONE thing this slide must communicate — exactly one point per slide}
- **Role in arc:** {how this slide advances the narrative arc above}
- **Data on this slide:**
  | Datum | Value | Communication intent | Source |
  |-------|-------|----------------------|--------|
  | {metric/claim} | {owner-supplied verified value} | {what THIS datum must make the audience feel/conclude — never "show the number"} | {owner-supplied source; REQUIRED for any external-facing claim} |
- **Blocking note:** {if any datum lacks an owner-supplied source → this slide is BLOCKED; flag, never fabricate (deck-loop-spec ②)}

## Open Data Gaps
{Every claim still missing an owner-supplied source — the loop halts these slides until filled (D5).}
```

### 5.2 Floor-completeness checklist (a content spec is INCOMPLETE if any fails)

| # | Floor element | Where it lives | Rule |
|---|---------------|----------------|------|
| 1 | Deck thesis | `## Thesis` | Exactly one controlling sentence |
| 2 | One point per slide | each `### Slide n` → **Point** | Exactly one; a slide with two points splits or is rethought |
| 3 | Narrative arc | `## Narrative Arc` | Present; each slide's **Role in arc** ties back to it |
| 4 | Per-datum communication intent | the per-slide data table **Communication intent** column | Every datum carries intent — never a bare value dump |
| 5 | Owner-sourced numbers | the data table **Source** column + `## Open Data Gaps` | Every external-facing claim has an owner-supplied source; unsourced → BLOCKED, never fabricated |
| 6 | Zero design language | whole doc | No layout / color / type / visual decisions — those belong to the Designer + design-state |

---

## 6. Residents — `hypresent/` and `slide-library/` (untouched)

| Resident | What it is | This build's relation |
|----------|-----------|----------------------|
| `studio/hypresent/` | The slide-presentation/builder app (its own server, app, tests, multi-version plans) | UNTOUCHED — rode along on the `html/`→`studio/` parent rename. No studio-build task writes inside it. A parallel session is active under `hypresent/docs/plan/builder-open-deck/` — stay out |
| `studio/slide-library/` | Library + engine that organizes slides so hypresent works (wired to hypresent) | UNTOUCHED — parent-rename only; `p1-1`/`p1-3` proved untouchability (rename-only git status + slide-library pytest baseline) |

The studio loop does NOT depend on hypresent or slide-library for v1; the deck path renders via the `browser-automation` infra (local HTTP server + headed browser), independent of the hypresent app.

---

## 7. Pointer — Capability Registry (`p1-7`)

The capability registry at `studio/capabilities/registry.md` is the single index a worker consults to discover and invoke a capability. **`p1-7` fills it**: registers v1's reference-loading capability and re-registers the two REUSE capabilities (extract-tokens, image→JSON) plus the browser-automation infra, each with: capability name, invoke path (workflow/command/skill), input contract, output shape, and the on-absence behavior. It is a **module-internal index, not a `.claude/` install** (see §2.4). Roadmap capabilities (extract-subtle-refs, image-gen) are listed as named-not-built rows so a future builder finds the slot.

---

## 8. Pointer — Design-State Schema (`p1-5`)

The design-state schema at `studio/state/design-state-schema.md` is **filled by `p1-5`**; this architecture fixes its slot and its relationship to the spine. Required payload (from `deck-loop-spec.md` Context Snapshot): project meta · artifact+mode · active phase · content-spec ref · chosen art direction · per-slide HTML status · accept/bounce notes · fresh-eyes punch-lists.

**Spine relationship (binding):** design-state is a **module-level run artifact that RIDES the orchestration three-file state spine — it never replaces or adds to it.** Per `orchestration/.../cards/state.md`:

| Spine file | Design-state's relation |
|------------|------------------------|
| `decisions.md` (worker-facing, append-only) | A slice/Designer worker reads design-state ALONGSIDE its task file + the run's `decisions.md` (the dispatch header carries the `decisions.md` pointer; it may also carry the design-state pointer). Design-state is the loop's working memory, not the run's decision log |
| `state-capsule.md` (mutable resume) | The conductor's resume state points at the active design-state file; design-state itself is the loop-internal mutable working file (per-slide status, bounce notes) |
| `run-log.md` (append-only audit) | A worker NEVER reads it; design-state carries none of its audit role |

The design-state file lives with the run's output (`{output_folder}/.../design-state.md`), referenced by the content spec's `design_state:` frontmatter (§5.1). `p1-5` defines the exact fields/format; it must state explicitly that design-state is a fourth *artifact*, not a fourth *spine file*, so a fresh agent resumes the loop from design-state + the reference set alone (deck-loop-spec ⑨).

---

## 9. What This Architecture Does NOT Decide (deferred to checkpoints)

| Open decision | Owner | Resolved at |
|---------------|-------|-------------|
| Chart mechanism (hand-authored vs library) | the `p2-2` spike against a concrete exemplar | `p2-2` |
| Site/app fork concretization (or drop) | GSMM evidence in hand | `p3-checkpoint` |
| Whether studio enters the install set | **RESOLVED** — studio added to install set at p6-checkpoint (2026-06-10); 4 surfaces installed | closed |
| Exact design-state fields/format | `p1-5` | `p1-5` |
| Capability registry row schema | `p1-7` | `p1-7` |
| Critic taxonomy + structural/aesthetic split | v1.1 build | P6 |
