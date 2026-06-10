---
name: 'app-fork'
description: 'Studio loop APP fork — the artifact: app branch. Forks EARLIER than the site (at discovery): replaces the deck slide-narrative with the goals → user-flow → UX beats (Strategist-side), producing testable user goals, a reachable flow map, and per-screen UX companion docs, then rides the deck loop''s art-direction / template / slice / fresh-eyes / human-gate beats parameterized for SCREENS. The output is plain-HTML screens with designed states PLUS UX companion docs a coding agent wires into a real app — the UI beat NEVER writes application code.'
nextStepFile: ../beats/beat-02-art-direction.md
outputFile: content-spec.md
---

# App Fork — `artifact: app`

The studio loop is artifact-general: `artifact` is a design-state parameter each beat reads, never a top-level branch (workflow.md fork rules). This file is the `artifact: app` branch. It exists because apps fork from decks EARLIER than sites do — at the **discovery** phase, not the structure phase: a deck locks a linear slide narrative; an app must first establish what the user must ACHIEVE (goals), then HOW they move toward each goal across screens (user-flow), then the per-screen UX detail a coding agent needs (UX). After discovery converges into a content spec, an app rides the deck loop's beats 2–4 with `slide` read as `screen`, producing plain-HTML screens with designed states (NOT a wired app — wiring is a coding agent's job, handed off via the UX companion docs).

Read `1-projects/rbtv-evolution/design-module/design-module-v1-build/specs/app-path-spec.md` (vault-root-relative) for the behavior floor and `{rbtv_path}/studio/architecture.md` §1.1/§3 for the subsystem map and landing paths. This file never restates them.

---

## When This Fork Activates

A beat reads `artifact` from the active design-state frontmatter FIRST (workflow.md fork rules). `artifact: app` routes message-lock through the **three app discovery beats** below (§A goals → §B user-flow → §C UX) instead of the deck slide-narrative path; beats 2–4 then run their existing files with the screen-noun substitution recorded in design-state (schema §4). `artifact: deck` and `artifact: site` are unaffected by this file.

| Loop position | `artifact: deck` (proven) | `artifact: app` (this fork) |
|---------------|---------------------------|-----------------------------|
| Beat 1 — message-lock (Strategist) | slide-by-slide narrative arc → content spec | **§A goals beat → §B user-flow beat → §C UX beat** below: testable user goals → reachable flow map → per-screen UX docs → screen-keyed content spec (one goal-serving job per screen) |
| Beats 2–4 (Designer) | run unchanged on slides | run unchanged on **screens** (§E downstream reuse), honoring the **§D app output contract** (plain-HTML screens, designed states, zero code wiring) |

The Strategist runs the §A–§C discovery beats in the **app-product** `{audience_mode}` (`{rbtv_path}/studio/personas/strategist.md` `<mode id="app-product">`); those three beats are that mode's beat-1 shape. The deck beats are referenced here, NEVER duplicated.

---

## §A — Goals Beat (Strategist; the first fork beat)

The app fork's first NEW beat. Discovery-led: the Strategist turns a product brief into the set of **user goals** — what the user must ACHIEVE or be enabled to do — in testable phrasing, with ZERO design decisions, exactly as the deck message-lock makes zero design decisions. This beat (with §B and §C) REPLACES the deck slide-narrative step (§2 of `beat-01-message-lock.md`) for `artifact: app`; every other part of `beat-01-message-lock.md` (discovery intake, owner-sourced-numbers rule, content-spec emission, design-state init, handoff) applies unchanged. Read `beat-01-message-lock.md` for those shared parts — this file states ONLY the app discovery fork.

### A.1 Discovery — shared with the deck beat

Run `beat-01-message-lock.md` MANDATORY SEQUENCE step 1 (discovery — brief intake) as written: confirm `{project_name}` + `{audience_mode}` (here `app-product`), resolve and HALT on `{output_folder}`, read the product brief / project-memo / entity root-level `.md` files, ingest any prior app as CONTENT INPUT ONLY (H1 — never a restyling base). Build the data wishlist; every gap becomes an Open Data Gap. This file does not restate that step.

### A.2 Goals — what the user must achieve (app-only)

1. State the app's SINGLE controlling product purpose — one sentence: what the whole app must enable the user to do (the app-product analogue of the deck thesis), landing the app-product emphasis (user goals · enablement · flow-to-goal — strategist `<mode id="app-product">`).
2. Enumerate the **user goals**: each one a thing the user must ACHIEVE or be enabled to do, phrased TESTABLY — a goal a coding agent could later verify the wired app delivers (app-path-spec behavior row 1). "Reconcile a bank statement against the ledger in under five minutes" passes; "manage finances" fails. One goal = one achievable end state, not a feature label.
3. For EACH goal, name WHO holds it (the app user role) and WHAT success looks like from that user's seat (the observable end state that means the goal is met). Goals carrying owner-supplied data targets (e.g. a threshold, a count) follow the owner-sourced-numbers rule — never fabricate a target (mining map ML-5; deck-loop-spec ②).
4. Challenge every goal inline from the app user's seat (strategist `<mode id="app-product">` enforced craft): for each, assess whether it is genuinely the user's goal or a disguised feature, and if disguised, propose the real underlying goal — NEVER rubber-stamp (mining map SC-1/SI-3). Close with the mode's goal assessment.
5. Iterate with the owner until the goal set is "solid" per the app-product lock definition (strategist `<mode id="app-product">` `<lock_definition>`). Do NOT proceed to the user-flow beat until the owner and Strategist agree the goals are complete and testable (mining map ML-1).

## §B — User-Flow Beat (Strategist; the second fork beat)

The app fork's second NEW beat. From the locked goal set, the Strategist maps the **flow**: the screens, the transitions between them, and the decision points — such that EVERY goal from §A is reachable through the flow. Still zero design decisions: this is the structure of movement toward goals, not the look of any screen.

1. Propose the **screen set**: the ordered set of screens the app needs to serve the goals (e.g. list → detail → edit → confirm — adapt to the goals, never a reflexive template). Each screen exists to advance one or more goals; a screen serving no goal is cut.
2. Map the **flow**: for each screen, its transitions (which gesture leads to which next screen) and its **decision points** (where the flow branches on user choice or app state). Give each screen a goal-serving working title that states its JOB, not a label (mining map ML-4): "Confirm and post the reconciliation" passes; "Screen 3" fails.
3. **Reachability check (the app-only halt floor):** trace EVERY goal from §A through the flow map and confirm it is reachable — there is a path of screens+transitions from entry to the goal's success end state. A goal with NO reachable path HALTS the user-flow beat (app-path-spec Edge Cases: flows with unreachable goals halt at the user-flow beat) — surface the unreachable goal to the owner; never proceed on a flow that strands a goal.
4. For each screen, identify conceptually WHAT it must let the user do and WHERE any owner-supplied datum it shows lives (conceptual data discussion — never present specific numbers unless owner-supplied, mining map ML-5). Note per-screen what the screen must SHOW; sourcing is the §D output contract's job at generation.
5. Challenge the flow inline from the user's seat: for each transition, assess whether it is the path the user expects toward their goal, and if not, propose a more intuitive route — NEVER rubber-stamp (strategist `<mode id="app-product">`; mining map SC-1/SI-3). Close with the mode's flow assessment (does the flow move intuitively toward every goal?).
6. Iterate with the owner until the flow is "solid": every goal reachable, transitions intuitive, decision points complete. Do NOT proceed to the UX beat until the owner and Strategist agree (mining map ML-1).

## §C — UX Beat (Strategist; the third fork beat)

The app fork's third NEW beat. For each screen in the §B flow, the Strategist authors a **per-screen UX companion doc** in the format the `p5-10` contract defines — the document that travels with the UI beat's HTML so a coding agent can wire the app from the package alone. This is the discovery output that makes the handoff self-sufficient; it is still author-side (what each screen must DO and SHOW and how it must BEHAVE), never a visual-design decision.

1. Read the UX companion-docs contract at `{rbtv_path}/studio/standards/ux-companion-docs-contract.md` (authored at `p5-10`) — the per-screen doc format and the package convention. Follow that contract's format; this file never restates it. (The contract is the handoff floor: screen goal · flow position · states · interactions · acceptance notes.)
2. For EACH screen in the §B flow, author its UX companion doc per the contract: its **screen goal** (which §A goal(s) it serves — the screen's job), its **flow position** (from which screen / to which screen, per §B's transitions and decision points), its **states** (empty · loading · error · success — each named with what the user sees and the condition that triggers it; the actual designed HTML for each state is the UI beat's §D output, this doc names WHICH states must exist), its **interactions** (what every control does and where each leads, traced to §B's transitions), and its **acceptance notes** (what "wired correctly" looks like from the user's seat — owner-observable, per the §A goal it serves).
3. **Designed-states floor (the app-only completeness rule):** a screen whose states the UX doc leaves undesigned — no empty, no error state named — is INCOMPLETE; the beat FLAGS it rather than letting a happy-path-only screen pass (app-path-spec Edge Cases + Quality bar: edge states designed explicitly; a screen with undesigned states is incomplete). Every screen's UX doc must name all four states or justify which genuinely cannot occur on that screen.
4. Challenge each UX doc from both the user's seat (does this screen serve its goal intuitively?) and the coding agent's seat (could a fresh coding agent wire this screen from this doc + its HTML ALONE, asking the designer nothing?). If the doc leaves a wiring question unanswerable from the package, fill it — NEVER rubber-stamp (mining map SC-1/SI-3). This is the self-sufficiency bar the §D output and `p5-10` contract enforce.

## §A–§C output — emit the content spec + UX docs (screen-keyed)

1. Write the content spec to `{output_folder}/artifacts/content-spec.md` in the EXACT architecture §5.1 format, with `artifact: app` and `audience_mode: app-product` in the frontmatter. Read `beat-01-message-lock.md` step 3 + architecture §5 for the format — this file never restates it. The substitutions for an app: `## Thesis` carries the app's controlling product purpose (§A.1); `## Narrative Arc` is the §B flow's linear spine (the path the user walks toward goals, even though screens are reachable per the flow's decision points); each `### Slide {n}` section is a `### Screen {n} — {goal-serving title}` section carrying the screen's **job** (the Point — which goal it serves), its **Role in arc** (flow position), its per-datum data table (Datum / Value / Communication intent / Source), and a pointer to its UX companion doc.
2. Write each screen's UX companion doc to `{output_folder}/artifacts/ux/{screen-slug}.md` in the `p5-10` contract format. The content spec's per-screen section points at the screen's UX doc; the UX docs + the (later) HTML are the coding-agent handoff package.
3. Fill every datum's **Communication intent** (what it must make the user understand) and **Source** (owner-supplied). Any datum lacking an owner source → that screen is BLOCKED in its Blocking note AND listed under `## Open Data Gaps`. Never fabricate to unblock (deck-loop-spec ②).
4. Verify against the §5.2 floor-completeness checklist (thesis/purpose · one job per screen · arc/flow · per-datum intent · owner-sourced numbers · zero design language) AND the app-only floors above (every goal reachable in §B; every screen's states designed in §C). A spec or UX-doc set failing any row is INCOMPLETE — fix before handoff.

## §A–§C output — initialize design-state (shared, with the app parameters)

Run `beat-01-message-lock.md` step 4 as written, with `artifact: app`, `mode: blank-slate`, `audience_mode: app-product` in the frontmatter, and `## Slide Status` seeded one row per SCREEN (the schema noun handling renders the row label as screen — schema §4). Set the Strategist→Designer cursor (`active_beat: beat-02-art-direction`, `who_acts_next: Designer`) exactly as the deck beat does. This file does not restate the schema.

---

## §D — App Output Contract (what the Designer beats produce)

The deck output contract is a full-screen browser deck + print-to-PDF CSS (`beat-03-generate.md` SUB-BEAT 3B). For `artifact: app`, that contract is REPLACED by the plain-HTML-screen contract below; every OTHER `beat-03-generate.md` rule (hand-authored charts, ban-list, fresh contexts, surgical patch, local-server render, no `file://`) applies unchanged.

| # | App output rule | Detail |
|---|------------------|--------|
| 1 | Plain-HTML screens — NO code wiring | One HTML screen per content-spec screen. **The UI beat NEVER writes application code** — no framework, no data fetching, no event-handler business logic, no backend/API calls, no state management (app-path-spec Context Snapshot + Out of Scope: code wiring is a coding agent's job). Plain HTML/CSS, plus MINIMAL demo-state JS ONLY where a state must be SHOWN (e.g. a toggle to preview the empty-vs-populated view) — nothing more. A screen that fetches data, posts a form to a real endpoint, or wires real navigation logic is a DEFECT. |
| 2 | Designed states, not implemented | EVERY state named in the screen's UX doc (empty · loading · error · success — §C) is DESIGNED as a visible HTML rendering — the coding agent wires WHEN each shows; the designer shows WHAT each looks like. A screen shipping happy-path-only when its UX doc named an empty or error state is INCOMPLETE (app-path-spec Edge Cases: a screen with undesigned states is incomplete — the beat flags it rather than shipping happy-path-only). |
| 3 | Responsive breakpoints designed | Each screen is responsive — readable and intact at desktop AND mobile viewports, with the breakpoints designed explicitly (app-path-spec behavior row 4 + Quality bar: responsive breakpoints designed explicitly — the gap every UI generator leaves). A screen that renders only at one width is INCOMPLETE. NO print-to-PDF / `@media print` block is required (that is the deck contract); an app targets the screen at multiple widths. |
| 4 | UX companion doc travels with each screen | Each HTML screen ships WITH its UX companion doc (§C / `p5-10` contract). The package — HTML screens + UX docs + the flow map — is the coding-agent handoff; the contract's self-sufficiency rule binds (a fresh coding agent wires from the package alone, asking the designer nothing). The Designer keeps each screen's HTML and its UX doc in sync: a screen whose designed states diverge from its UX doc's named states is a defect. |
| 5 | Imagery — real provenance only | Imagery comes via the image-gen capability (`{rbtv_path}/studio/capabilities/image-gen/`) OR owner-supplied assets. NEVER fabricate stock-lookalike photos passed as real photos of real things, people, or places (D4 imagery ruling). A screen needing an image whose asset is absent HALTS to the owner naming the missing asset — never an invented "real" photo. (The image-gen capability's FIXTURE provider is the quota-independent path — the contract may invoke the capability without assuming live image-gen quota.) |
| 6 | Charts — unchanged from the deck | Any chart is hand-authored inline SVG/CSS with an action-title — NO charting library (decisions.md p2-2). A library import is a defect, same as the deck. |
| 7 | Render-for-review — unchanged | Render via the local-server pattern (`{rbtv_path}/studio/workflows/browser-automation/`); `file://` is blocked. Review is HEADED at desktop AND mobile viewports (§E / app-path-spec row 2), asserting MEASURED geometry of the real rendered screen incl. one edge state. |

---

## §E — Downstream Reuse (screens ride the deck beats — do NOT duplicate them)

After §A–§C emit the screen-keyed content spec + UX docs and initialize design-state, the run hands off to the Designer and rides the deck loop's beats 2, 3, 4 AS WRITTEN — the app fork builds NO new designer beats. Each beat reads `artifact: app` from design-state and substitutes the screen noun. Read each beat file for its mechanics; the table states ONLY the per-screen parameterization.

| Beat (reused as-is) | Runs for an app by | App-specific note |
|---------------------|--------------------|-------------------|
| `beat-02-art-direction.md` | Loading the reference set + taste file; producing ≥2–3 distinct direction mini-briefs (six axes) on the app's references; owner-influenced pick → design-state. | The six axes apply to screens unchanged. The mini-brief governs the look of the screens; it NEVER adds code wiring. App screens converge with the deck/site at art-direction exactly as the app-path-spec states (apps converge with the other artifacts at art-direction → layout → visual). |
| `beat-03-generate.md` (3A trio → 3B slices → 3C fresh-eyes) | 3A: a screen-template trio (a primary screen type · a content/detail screen · a state-bearing screen — e.g. a form with its error state) pairwise-picked → visual contract. 3B: each SCREEN generated slice-by-slice by a fresh-context worker resuming from design-state ALONE, conforming to the trio contract + the §D output contract — INCLUDING every state its UX doc names, responsive at both viewports, ZERO code wiring. 3C: fresh-eyes pass (non-builder) against the mini-brief + flaw checklist before the owner looks. | "slice" reads as "screen". Surgical patch is per-SCREEN: a bounce changes only the flagged screen; other screens stay byte-identical (deck-loop-spec ④/⑦). The output is §D's plain-HTML-screen contract (designed states + responsive breakpoints + travelling UX docs), NOT the deck's print-to-PDF contract. The fresh-eyes pass ALSO confirms each screen's designed states match its UX doc's named states (§D rule 4). |
| `beat-04-human-gate.md` | Headed owner review at BOTH viewports; accept/bounce-with-notes per screen → design-state; surgical per-screen patch; bounce-cap (≈3/screen) → message-level rethink routed through the Strategist. | **Review at BOTH viewports** (desktop + mobile) — measured geometry sane at each, AND walk at least one edge state per the screen's UX doc (app-path-spec row 2; fidelity floor). On full accept the loop completes; there is NO print-to-PDF step (that is deck-only) — the accepted artifact is the rendered screen package (HTML + UX docs + flow map) ready for coding-agent handoff. A bounce demanding a GOAL or FLOW change (not a visual change) routes back to the Strategist (§A/§B), never edited by the Designer. |

**Binding reuse rules:**

- The app fork adds EXACTLY THREE new beats (§A goals, §B user-flow, §C UX) and ONE replaced contract (§D output). Beats 2–4 are the deck beats, parameterized — never copies. Any divergence a future run discovers (a genuine screen-only beat need) is a DISCOVERY to surface (PLAN MODIFIED), not a license to fork beats 2–4 here.
- Every beat in the chain has a defined input artifact: §A reads the brief + reference set → emits the goal set; §B reads the goals → emits the flow map (every goal reachable or HALT); §C reads the flow → emits per-screen UX docs (every screen's states designed or FLAG) + the screen-keyed content-spec + design-state; beat 2 reads content-spec + design-state + reference set → emits art-direction brief + design-state; beat 3 reads those + the trio contract → emits per-screen HTML (every state designed, responsive, zero wiring) + design-state; beat 4 reads the rendered screens + UX docs + design-state → emits accept/bounce + the accepted screen package. A fresh agent resumes any point from design-state + the reference set alone (deck-loop-spec ⑨; schema §2, §4).
- The coding-agent handoff is the OUTPUT, not a beat: the accepted package (HTML screens + UX companion docs + flow map) satisfies the `p5-10` contract's self-sufficiency bar (a fresh coding agent wires the real app reading ONLY the package — app-path-spec behavior row 5). Production code wiring, backend, data models are OUT OF SCOPE here — the coding agent owns them (app-path-spec Out of Scope).

---

## Resume / Worker-Switch

Identical to the deck path: a fresh agent or a Strategist↔Designer switch resumes from **design-state + the reference set ALONE**, zero conversation history (workflow.md Resume; schema §2–4). The design-state `artifact: app` parameter routes the resuming worker through this fork's discovery beats (§A→§B→§C, if pre-beat-2) or straight into the reused designer beats (beat 2+). A worker NEVER reads `run-log.md` or `state-capsule.md`.

---

## Roadmap Boundary

This fork concretizes the `artifact: app` discovery beats (§A goals · §B user-flow · §C UX) + output contract (§D) + downstream wiring (§E) (`p5-8`). It does NOT build: the site fork (`forks/site.md`, separate); production code wiring, backend, or data models (coding agents own them — app-path-spec Out of Scope); native-platform UI; accessibility certification (designed-for, not certified). The owner entry surface and any standalone app command are install-set decisions deferred to `p6-3`/`p6-checkpoint` (architecture §2), not built here.
