# UX Companion-Docs Contract — the Coding-Agent Handoff

> The per-screen document format that travels with the app path's plain-HTML screens. A studio **module-internal standard** (not a `.claude/` rule), authored at `p5-10`; slot fixed by `architecture.md` §1.4/§3 (`studio/standards/`). It makes the app fork's handoff self-sufficient: a coding agent wires a real app reading ONLY the package (HTML screens + these companion docs + the flow map) — the designer is never needed for a wiring question. The app fork (`{rbtv_path}/studio/workflows/studio-loop/forks/app.md` §C) emits docs in THIS format; the app-path-spec owns the behavior floor, this contract owns the doc SHAPE.

Read `{rbtv_path}/studio/workflows/studio-loop/forks/app-path-spec.md` for the behavior floor (the handoff criterion is its behavior row 5). This contract never restates it.

---

## Who Produces, Who Consumes

| Actor | Role |
|-------|------|
| The Strategist (app fork §C — UX beat) | AUTHORS one companion doc per screen in this format, during discovery — what each screen must DO, SHOW, and let the user ACHIEVE. Zero visual-design and zero application-code decisions. |
| The Designer (beats 2–4) | Renders the screen's plain HTML so every state the doc NAMES is visibly DESIGNED, and keeps the HTML in sync with its companion doc (a designed state diverging from a named state is a defect — app fork §D rule 4). |
| The coding agent (downstream, OUT OF SCOPE here) | CONSUMES the package — reads ONLY the companion docs + the HTML + the flow map and wires the real app: data, events, navigation, backend. Asks the designer NOTHING. This contract's acceptance bar is the test that this is possible. |

---

## The Per-Screen Companion Doc — the five required fields

One companion doc per screen, written to `{output_folder}/artifacts/ux/{screen-slug}.md` (app fork §C). A doc is INCOMPLETE if any of the five fields below is absent or vague. Each field is owner-observable / coding-agent-actionable — never an internal-technical assertion.

| # | Field | What it MUST state | Floor rule |
|---|-------|--------------------|------------|
| 1 | **Screen goal** | Which user goal(s) this screen serves (traced to the goals beat, app fork §A) — the ONE job of the screen, phrased as what the user ACHIEVES here. | Exactly one job per screen (the app analogue of one-point-per-slide). A screen serving two goals splits or is rethought (app fork §A/§C; strategist `<mode id="app-product">`). |
| 2 | **Flow position** | Where the screen sits in the flow (app fork §B): FROM which screen(s) the user arrives, and TO which screen(s) each exit leads — naming the gesture/decision that causes each transition. | Every from/to traces to a transition in the §B flow map; no orphan screen, no dead-end that strands a goal (app-path-spec behavior row 2; app fork §B reachability). |
| 3 | **States** | EVERY state the screen can be in — at minimum **empty · loading · error · success** — each named with: the CONDITION that triggers it, what the USER sees, and a pointer to the designed HTML rendering of that state (the UI beat's §D output). | All four states named or the doc JUSTIFIES which genuinely cannot occur on this screen. A screen with undesigned/unnamed states is INCOMPLETE — flagged, never shipped happy-path-only (app-path-spec Edge Cases + Quality bar; app fork §C designed-states floor). |
| 4 | **Interactions** | What EVERY control on the screen does — for each interactive element: the gesture, the immediate user-visible effect, and where it leads (which state-change or which screen, per field 2). Including what is disabled/unavailable and why. | Every control accounted for; a control whose behavior the coding agent could not infer from the doc + HTML alone is a gap to fill, not to defer (app fork §C self-sufficiency challenge). NO application code is written here — the doc DESCRIBES the wiring, the coding agent IMPLEMENTS it. |
| 5 | **Acceptance notes** | What "wired correctly" looks like — owner-observable: the conditions under which the coding agent (and later the owner) can confirm THIS screen delivers its goal. Phrased as observable outcomes ("when the list is empty, the empty-state with the Add-first-item CTA shows"), never internal assertions. | Tied to the screen's goal (field 1) and its states (field 3); each acceptance note is something a person can SEE is true in the running app. This is the per-screen slice of the package's self-sufficiency bar below. |

### Per-screen doc shape

```markdown
---
type: ux-companion-doc
screen: '{screen-slug}'
artifact: app
project: '{project_name}'
content_spec: ../content-spec.md     # back-pointer; the screen's content-spec section
flow_map: ./flow-map.md              # the package's flow map (or the content-spec Narrative Arc)
date: {YYYY-MM-DD}
---

# UX Companion — {Screen title (states the job, not a label)}

## Screen Goal
{The one user goal this screen serves (from the goals beat) — what the user ACHIEVES here. One job.}

## Flow Position
- **Arrives from:** {screen(s) + the gesture/decision that brings the user here}
- **Leads to:**
  | Exit gesture | Destination | Condition |
  |--------------|-------------|-----------|
  | {control/gesture} | {screen or state} | {when this exit applies} |

## States
| State | Trigger condition | What the user sees | Designed HTML |
|-------|-------------------|--------------------|---------------|
| empty   | {when}            | {description}      | {file / section ref} |
| loading | {when}            | {description}      | {file / section ref} |
| error   | {when}            | {description}      | {file / section ref} |
| success | {when}            | {description}      | {file / section ref} |
{Justify here any of the four omitted as genuinely impossible on this screen.}

## Interactions
| Control | Gesture | Immediate effect | Leads to (state-change / screen) |
|---------|---------|------------------|----------------------------------|
| {element} | {click/type/…} | {user-visible effect} | {per Flow Position} |
{Include disabled/unavailable controls and the condition that disables them.}

## Acceptance Notes
- {Owner-observable condition that proves this screen delivers its goal — what "wired correctly" looks like, visible in the running app.}
- {One per state and per goal-critical interaction.}
```

---

## The Package Convention — what ships together

The handoff is a PACKAGE, not a loose set of files. The app fork's accepted output (beat 4, app fork §E) is exactly this package; nothing else is needed to wire the app.

| Package member | What it is | Source |
|----------------|-----------|--------|
| **HTML screens** | One plain-HTML screen per content-spec screen, every named state visibly designed, responsive at desktop + mobile, ZERO application code (app fork §D rules 1–3). | Designer, beat 3 |
| **UX companion docs** | One doc per screen in the five-field format above. Each travels WITH its screen and stays in sync with it (app fork §D rule 4). | Strategist §C, kept in sync by the Designer |
| **Flow map** | The screen set + transitions + decision points (app fork §B) — the map every companion doc's Flow Position references. May be the content-spec's `## Narrative Arc` (the flow's linear spine) or a standalone `flow-map.md` in the package. | Strategist §B |

**The self-sufficiency rule (the package's acceptance bar — the contract's whole point):** a fresh coding agent, given ONLY this package (HTML screens + companion docs + flow map) and NOTHING else — no designer, no Strategist, no conversation history — can wire the real app: it can answer, from the package alone, every wiring question (what each control does, where it leads, which state shows when, what "done" looks like per screen). **The coding agent asks the PACKAGE, not the designer.** A package that forces a wiring question back to the designer FAILS this bar — the gap is filled in the companion doc, not answered out-of-band.

This is the app-path-spec's handoff criterion (behavior row 5): "the package (HTML + companion docs) answers wiring questions without the designer in the loop." That criterion is THIS contract's acceptance bar — a package is done only when it clears it. Exercising it at the fidelity floor: a fresh-context coding agent reads ONLY the package and answers concrete wiring questions correctly, with no designer input (app-path-spec Test Plan row 3).

---

## What This Contract Does NOT Cover

- The application code itself — data models, event handlers, API calls, navigation logic, state management. The coding agent OWNS all of it; this contract hands off enough for them to build it, never the code (app-path-spec Out of Scope).
- The screen's visual design — type, color, layout, motion. That is the Designer's job (beats 2–4) and the chosen direction's; the companion doc names states and behavior, never look.
- Accessibility certification (designed-for, not certified here) and native-platform UI (app-path-spec Out of Scope).
