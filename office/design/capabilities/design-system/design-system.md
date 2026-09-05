---
id: design-system
description: Create and govern a project design system — principles, tokens, component recipes, patterns, per-view files, governance, changelog — through source gathering, a relentless owner interview, an adversarial panel review, and an owner decision batch. Nothing becomes law without an owner ruling.
inputs: project name; source material (existing mockups/HTML, live reference URL(s), reference images, or none); output folder (caller-proposed, owner-confirmed); mode (create | evolve, detected from the output folder when unstated)
outcome: the caller holds a governed design-system folder — every rule an assertion with its WHY, every rule either owner-ruled or marked proposed, every later change routed through the exception/system-change protocol and logged
outputs: a design-system folder scaffolded from `templates.md` beside this file — design-system.md (principles + tokens), components.md (recipe cards), patterns.md (cross-view compositions), views/{view}.md, CLAUDE.md (governance), changelog.md
---

# design-system

Create a project design system, or evolve an existing one. Instruction-only — no CLI. This capability COMPOSES its siblings; it never re-does their jobs:

| Job | Owner — delegate, never duplicate |
|---|---|
| Extract tokens from a live site | `design-tokens` (same component) |
| Read visual identity out of a reference image | `vision-to-json`, `subtle-refs` (same component) |
| Verify produced HTML against the finished system | `visual-check` (same component) — never this capability |
| Multi-lens adversarial review | the environment's `panel` capability |
| The relentless owner interview | the environment's `interview` function |

`design-tokens` extracts what a site HAS; this capability decides, with the owner, what the system SHOULD BE — it consumes extraction output as evidence, never replaces it.

## Standing rules

1. **Nothing becomes law without an owner ruling.** Every rule the agent drafts is `[PROPOSED]` until the owner rules on it in the decision batch (or later via the evolve protocol). An agent-invented rule presented as settled law is a violation.
2. **Every rule is an assertion + WHY.** A testable, falsifiable statement plus the one-line reason it exists. Prose guidance that cannot be checked is not a rule.
3. **Every change is a changelog row.** Creation, ruling, exception, amendment — one dated row each, from the first write onward.
4. **Output location comes from the caller.** Propose `{project-root}/design-system/` with reasoning, confirm ONCE, never invent or hardcode a destination.
5. **One source of truth per fact.** Where a live stylesheet or `:root` block exists, the tables document it; if they disagree, the code wins and the table is the defect.

## Mode detection

Output folder already contains a `changelog.md` → **evolve**. Otherwise → **create**. The caller may name the mode explicitly; explicit wins.

---

## Create pipeline

### 1. Init

Resolve project name, source material, and output folder. Ask ONCE — bundle any missing item into the single init confirmation, then never halt again outside the interview and the decision batch.

### 2. Gather evidence

Branch on what exists (several branches may apply; run all that do):

| Source present | Action |
|---|---|
| Live reference site | Invoke `design-tokens` — its tokens JSON + brief become the evidence base |
| Existing mockups / HTML | Read them; inventory actual colors, sizes, spacings, radii, shadows, and recurring component shapes into a raw-values note |
| Reference images | Invoke `vision-to-json` and/or `subtle-refs` per image |
| Nothing | Research the product's domain conventions (delegate to research seats where available); the interview below carries more weight |

Write the gathered evidence into a working note at the output path. Evidence is INPUT to the system, never the system: extraction reports what is; the owner rules what should be.

### 3. Relentless owner interview

Invoke the environment's `interview` function in **relentless** mode (15–25 questions). This step is MANDATORY — the interview is where the system's semantics come from, and no evidence pile replaces it. Cover at minimum:

- Principles — what the design optimizes for, and what it deliberately refuses.
- Color semantics — what each palette layer MEANS (status, kind/category, interaction), not just which hexes exist.
- Type roles and hierarchy; density and spacing philosophy.
- Shape semantics — what radius, elevation, and borders signal (e.g. clickability), if anything.
- Motion tolerance; empty/error/loading state expectations; copy voice.
- Scope — which views/surfaces the system must govern first.

Feed gathered evidence into the questions ("your mockup uses 4 grays — which are law?"). Record every answer; unanswered areas stay `[PROPOSED]` in the draft.

### 4. Draft

Scaffold the folder from `templates.md` beside this file and fill it from evidence + interview. Mark every rule the interview did not settle `[PROPOSED — pending owner ruling]`.

### 5. Panel review

Run the environment's `panel` capability over the draft with three lenses, then a synthesis:

| Lens | Question |
|---|---|
| Completeness | What will a page-building agent need that the draft does not answer? |
| Fidelity | Where does the draft contradict the gathered evidence or the interview answers? |
| Generality | Which rules are one-view rules masquerading as core law? |

Fold synthesis findings into the draft; findings that need an owner call join the decision batch.

### 6. Owner decision batch

Assemble EVERY `[PROPOSED]` rule and every panel finding needing a ruling into ONE lettered batch (A, B, C…), each item with options, consequences, and a recommendation. Put it to the owner. Apply the rulings; log each as a changelog row. Only now do rules lose their `[PROPOSED]` mark.

### 7. Close

Report: file set written, rulings applied, anything still `[PROPOSED]`. Point the caller at `visual-check` for verifying pages built against the system. This capability's job ends at the spec.

### Resume

Detect from artifacts at the output path, never from a menu: evidence note only → interview; interview record present → draft; draft present, no panel output → panel; synthesis present, no rulings in changelog → decision batch; rulings logged → close.

---

## Evolve protocol (two-way door)

For ANY change request against an existing system — a deviation a page needs, a new component, a contradiction found:

1. Classify: **exception** (this one spot breaks the rule, rule stands) or **system change** (the rule itself is wrong or incomplete).
2. Either way the owner rules first — an exception is still a ruling, not a favor the agent grants itself.
3. Log in the SAME turn: system change → changelog row + the rule edited in place; exception → changelog exceptions-in-force row naming rule, location, why, since-when.
4. Placement heuristic for new rules: a rule lives in `views/{view}.md` until a SECOND view needs it; only then is it promoted to `patterns.md` or core. Premature promotion is a defect.

## What this never does

- It NEVER extracts tokens from a live site itself — that is `design-tokens`.
- It NEVER verifies rendered HTML — that is `visual-check`.
- It NEVER turns a rule into law without an owner ruling.
- It NEVER skips the relentless interview, however rich the extracted evidence.
- It NEVER decides where the system lives.
