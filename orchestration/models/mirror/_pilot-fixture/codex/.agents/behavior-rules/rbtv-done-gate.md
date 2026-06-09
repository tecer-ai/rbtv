# Done Gate

An agent MUST NOT declare a coding task done until it has exercised every contracted outcome criterion the way the owner will use the feature and exhibited the evidence. Done is purchased with user-fidelity evidence — nothing else buys it.

## Trigger and Scope

**Activates when:** a coding task starts (Contract) and a done-claim is about to be made (Exercise + Exhibit). Default-ON for every coding task — feature, bug fix, behavior change — in any workspace where this rule is installed.

**Does NOT apply to:**

- Non-code work (documents, plans, vault content) — out of scope entirely.
- The exempt list — the ONLY exit for coding tasks: typo and comment fixes, formatting-only changes, internal cleanups with zero behavior change (renames, dead-code removal), config changes invisible at runtime. Fails safe: not on the list → gated.

**Boundary:** internal correctness (unit tests, type checks, builds) remains the agent's normal testing job. This rule governs ONLY the done boundary — tests green, builds passing, and code review do NOT buy done.

## The Gate — Contract, Exercise, Exhibit

Sequencing gate plus structured output gate. The build itself is unchanged; the gate wraps it.

| Phase | Requirement |
|-------|-------------|
| 1. Contract — at intake | DRAFT outcome criteria in plain language — "when done, the owner can {gesture} and {visible result} happens" — and confirm with the owner in ONE pass. The owner edits conversationally; NEVER ask the owner to write criteria or learn a format. Pushback is MANDATORY on vague criteria ("works", "looks right") — force user-visible outcomes. Criteria count scales with stakes: a small fix may carry a single criterion. Criteria are ALWAYS owner-observable outcomes, never internal/technical assertions. |
| 2. Build | Existing workflows untouched. |
| 3. Exercise — before any done-claim | Perform EACH contracted criterion under real input at the Fidelity Floor, capturing evidence files as you go. |
| 4. Exhibit | Fill the evidence sheet. No sheet → done is UNDECLARABLE. Any `failed` row → back to Build, then re-exercise. `unexercisable` rows → done is declarable ONLY with those rows surfaced explicitly in the done message; the owner decides acceptance. Same for `held-surprising` rows — see Surprising Holds. |

## Fidelity Floor

Exercising below the floor is theater, not evidence.

| Floor requirement |
|-------------------|
| The real application running whole — never an isolated fragment or mock harness |
| The owner's actual file/data when one exists — synthetic fixtures alone do not qualify |
| UI criteria: visible (headed) browser + real mouse/keyboard gestures — NEVER synthetic in-page `dispatchEvent` |
| Visual/layout criteria: assert the MEASURED geometry of the real rendered element (size, position, overflow, aspect ratio) in a headed browser — DOM presence and headless e2e do NOT count; a layout can render "present" while visibly broken |
| CLI/process criteria: read the exit code and errors off the UN-PIPED process — a pipe (e.g. `… \| tee log`) reports the pipe's status, not the program's, masking real failures |
| Content-validation / heuristic criteria: exercise against REAL-corpus input, not only builder-chosen fixtures — fixtures cannot anticipate which real content trips a heuristic |
| Each criterion end-to-end, the way the owner will perform it |
| Evidence captured as files on disk DURING the exercise (screenshots, output files, logs) — prose claims alone NEVER count |
| Genuine blockers: verdict `unexercisable` + the concrete blocker — never silently skip a criterion |

## Required Output — the Evidence Sheet

One sheet per task at `{evidence_root}/{project}/{YYYY-MM-DD}-{feature}.md` — `{project}` is the app or repo being modified; capture files go in a sibling folder `{YYYY-MM-DD}-{feature}/`. Resolve `{evidence_root}` from the workspace CLAUDE.md routing table; absent a routing entry, default to `docs/done-gate-evidence/` at the modified repo's root. Create the sheet at Contract time with the confirmed criteria; fill verdicts at Exhibit.

| Column | Content |
|--------|---------|
| Criterion | The contracted outcome, verbatim |
| Gesture performed | What was actually done to exercise it |
| Observed result | What actually happened |
| Evidence file | Relative path to the capture created during this exercise |
| Verdict | `held` / `held-surprising` / `failed` / `unexercisable` + concrete reason |

The done message to the owner = sheet path + one-line verdict summary + every `failed`, `unexercisable`, and `held-surprising` row surfaced explicitly.

## Surprising Holds

A criterion is `held-surprising` — not plain `held` — when it holds technically but the observed behavior depends on a non-obvious mechanism the criterion never named: a pre-existing quirk, an undocumented convention, an inherited heuristic.

**Operable trigger (apply at Exhibit, to every `held` row before filing it):** Read the observed result as the owner would — zero build context, first time seeing it. Would they say "that's not quite what I meant"? If yes → `held-surprising`.

`held-surprising` rows surface in the done message exactly like `unexercisable` rows. The owner decides acceptance — not the agent.

| Pattern | Verdict |
|---------|---------|
| Observed result matches the criterion's plain words; no hidden mechanism | `held` |
| Criterion holds; behavior depends on a pre-existing quirk or undocumented convention | `held-surprising` |
| Criterion holds; an inherited heuristic produced the "right" result for the wrong reason | `held-surprising` |

## Orchestrated Dispatches

For development dispatches inside an orchestration, builder-graded sheets are INSUFFICIENT from day one: an independent cold verifier — given ONLY the contract criteria and the running artifact, never the builder's tests, claims, or sheet — re-exercises the criteria at the floor and returns its own sheet. Builder/verifier mismatch = the dispatch FAILS return-verification.

## Integrity Tripwire

Evidence rows MUST cite captures created during this task's exercise. The first sheet caught dishonest — a claimed gesture not performed, a fabricated result, a recycled capture — permanently escalates the workspace to independent verification: from then on, a separate verifier re-exercises every contract before done.

## Anti-Patterns

| Type | Thought | Action |
|------|---------|--------|
| Skip | "Tests are green — that's my evidence" | Tests are build-phase work. Exercise the contracted criteria under real input; the sheet cites captures, not test output. |
| Skip | "Task too small for the gate" | Check the exempt list. Not on it → gated. A one-criterion contract costs minutes. |
| Skip | "No contract was made at intake — I'll just describe what I did" | STOP. Draft criteria now, confirm with the owner, then exercise them. Done stays locked until then. |
| Game | "Headless run is equivalent and faster" | Floor violation. UI criteria require a visible browser and real gestures. |
| Game | "DOM says the element is there / headless e2e is green — the layout's fine" | Presence ≠ geometry. Measure the rendered box (size/position/aspect) in a headed browser; a collapsed or oversized layout passes presence checks. |
| Game | "I'll fill the sheet from test results / memory" | Sheet rows cite files captured during the exercise. No capture → the row does not exist → done locked. |
| Game | "Can't drive this — mark it `held`, it probably works" | Mark `unexercisable` + the concrete blocker, and surface it in the done message. |
| Game | "I'll rephrase the criteria into technical assertions I can pass" | Criteria stay owner-observable. Internal assertions live in your tests, not in the contract. |
| Game | "The behavior holds technically — the surprise is a pre-existing quirk, not my code" | Mark `held-surprising`. Pre-existing quirks are exactly the surprises the owner must judge. |
| Game | "I noticed the non-obvious mechanism but the criterion still passes — it's fine" | Apply the owner-lens: read the observed result with zero build context. If surprising → `held-surprising`. |
