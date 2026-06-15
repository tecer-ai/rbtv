# Done Gate — Protocol

Loaded by the always-on `rbtv-done-gate` rule the moment a non-exempt coding task fires. The rule owns the trigger, the exempt list, the drivability-only exemption, and the done-lock; THIS protocol owns the mechanics. By the time you are reading this the task is gated — run Contract now, and Exercise + Exhibit before any done-claim.

When a contracted outcome runs through a surface the agent cannot drive or observe, the agent MUST build a test seam for that surface as part of the feature — so the outcome is exercisable at the Fidelity Floor without faking the owner's gesture.

## The Gate — Contract, Exercise, Exhibit

Sequencing gate plus structured output gate. The build itself is unchanged; the gate wraps it.

| Phase | Requirement |
|-------|-------------|
| 1. Contract — at intake | DRAFT outcome criteria in plain language — "when done, the owner can {gesture} and {visible result} happens" — and confirm with the owner in ONE pass. The owner edits conversationally; NEVER ask the owner to write criteria or learn a format. Pushback is MANDATORY on vague criteria ("works", "looks right") — force user-visible outcomes. Criteria count scales with stakes: a small fix may carry a single criterion. Criteria are ALWAYS owner-observable outcomes, never internal/technical assertions. Then, for EACH drafted criterion, run the Drivability Check (below) BEFORE Build. |
| 2. Build | Existing workflows untouched. Any `needs-seam` verdict from the Drivability Check is built here, AS PART OF the feature. |
| 3. Exercise — before any done-claim | Perform EACH contracted criterion under real input at the Fidelity Floor, capturing evidence as you go (see Evidence Tier for the form — files for Full, the concrete observed value for Light). |
| 4. Exhibit | Record the evidence at the task's tier (Full: fill the Evidence Sheet on disk; Light: write the same Exercise rows inline in the done message — see Evidence Tier). No exercised evidence → done is UNDECLARABLE. Any `failed` row → back to Build, then re-exercise. `unexercisable` rows → done is declarable ONLY with those rows surfaced explicitly in the done message; the owner decides acceptance. Same for `held-surprising` rows — see Surprising Holds. |

### Drivability Check + Seam Plan (Contract phase)

Structured-output gate, run at Contract time and recorded with the rest of the evidence (on the sheet for Full tier, inline for Light) — never a separate artifact. For EACH criterion, classify its outcome surface and act before Build:

| Verdict | Meaning | Required action before Build |
|---------|---------|------------------------------|
| `drivable` | The agent can perform the real gesture and observe the result as-is | None — proceed |
| `needs-seam: {pattern}` | The outcome runs through a surface the agent cannot drive or observe | Build the seam named from Seam Patterns AS PART OF the feature |
| `un-seamable: {reason}` | The surface is genuinely outside the software's control (third-party OS chrome you cannot wrap, a remote service) | Record it; it becomes an `unexercisable` row + owner-UAT |
| `un-seamable: interactive-agent-session → owner-UAT` | The surface is a LIVE multi-turn interactive workflow-agent / persona session (`/sb-investor`, `/sb-tutor`, mode-routing via a fresh skill invocation) — an agent cold-verifier cannot author BOTH the human and the agent turns at the floor | Pre-classify it HERE at Contract — NEVER mark it `drivable`. It becomes an `unexercisable` owner-UAT row (or a record/replay seam if one is built); the owner exercises it on the next real session |

**Required output:** the Drivability rows in § Required Output. A `needs-seam` row still seamless at Exhibit = the feature is NOT built; done stays locked.

## Fidelity Floor

Exercising below the floor is theater, not evidence.

| Floor requirement |
|-------------------|
| The real application running whole — never an isolated fragment or mock harness |
| The owner's actual file/data when one exists — synthetic fixtures alone do not qualify |
| UI criteria: visible (headed) browser + real mouse/keyboard gestures — NEVER synthetic in-page `dispatchEvent` |
| Visual/layout criteria: assert the MEASURED geometry of the real rendered element (size, position, overflow, aspect ratio) in a headed browser — DOM presence and headless e2e do NOT count; a layout can render "present" while visibly broken |
| Hidden / closed / dismissed / removed-from-view criteria: assert USER-PERCEIVED visibility — computed `opacity` / `visibility` / `pointer-events`, or an on-screen pixel (screenshot) check — NEVER DOM presence (`offsetParent`, `getBoundingClientRect`, `display`, node-in-document). A modern hide (opacity, `pointer-events:none`, `max-height:0`, off-screen transform) leaves the node present with a non-zero rect that a presence check reads as "visible" forever |
| CLI/process criteria: read the exit code and errors off the UN-PIPED process — a pipe (e.g. `… \| tee log`) reports the pipe's status, not the program's, masking real failures |
| Content-validation / heuristic criteria: exercise against REAL-corpus input, not only builder-chosen fixtures — fixtures cannot anticipate which real content trips a heuristic |
| Content / order / identity criteria: prove the property directly in the artifact — per-item content, the order mapping, identity hashes — a matching COUNT is necessary but never sufficient; a count-only check passes scrambled, content-stripped, or silently-substituted output |
| Destructive criteria (delete / unlink / `rmdir` / prune), especially when target paths resolve from a user-editable state file: exercise against a HOSTILE or corrupt row (a `../`-bearing / out-of-root path) and confirm the operation REFUSES + loudly logs it and touches nothing outside the workspace root — not only against a well-formed row (a well-formed-row-only exercise never reveals an unbounded blast radius) |
| Each criterion end-to-end, the way the owner will perform it |
| Evidence captured DURING the exercise: a file on disk (screenshot, output file, log) when the criterion's evidence is inherently a file — that criterion forces Full tier — else the concrete observed value recorded inline (exit code, returned value, diff). A bare "it works" / prose claim alone NEVER counts, in either tier. |
| Production-untouched / no-rerun criteria: scope the assertion to the artifact's REACHABLE path set (its target files + their parent dirs), never whole-tree emptiness or a clean whole-corpus diff — in a live multi-session vault a concurrent session mutates unrelated files during the exercise window, so a whole-tree clean-diff form is undrivable; filter the diff to the reachable set and disclose any concurrent-session intermediate state |
| Genuine blockers: verdict `unexercisable` + the concrete blocker — never silently skip a criterion |

## Evidence Tier — Light vs Full

The gate ALWAYS runs — Contract, the Drivability Check, Exercise at the Fidelity Floor, and the Lock. Only the STORAGE of the exercise evidence is weight-graded. Classify the task at Contract, right after the criteria are confirmed.

| Tier | Applies when | Evidence form |
|------|--------------|---------------|
| **Full** — disk sheet | ANY of: a criterion's Fidelity-Floor evidence is inherently a FILE (UI screenshot, measured geometry, output artifact, real-corpus log); OR the task changes persistent behavior across multiple steps; OR it touches a risk surface (data mutation, auth, migration, external API); OR it is an orchestrated development dispatch or an integrity-escalated workspace (the cold verifier needs the sheet — see Orchestrated Dispatches + Integrity Tripwire); OR the owner asks for a sheet | The Evidence Sheet below, on disk + capture folder |
| **Light** — inline | NONE of the Full triggers fire — a bounded change the agent drives directly whose every criterion's evidence is inline-expressible text (an exit code off the un-piped process, a returned value, a small reachable-set diff) | The same two row families (Drivability + Exercise), written INLINE in the done message — no disk sheet, no capture folder |

**The tier is not a fresh judgment call — it falls out of the Fidelity Floor the criteria already demand.** Any criterion whose floor evidence is a captured file makes the task Full automatically; Light exists only when every criterion's floor evidence is inline text. When in doubt, Full.

**The Lock binds both tiers:** no exercised evidence (sheet OR inline rows) → done UNDECLARABLE; every `failed` / `unexercisable` / `held-surprising` row surfaces in the done message regardless of tier. Light changes only WHERE the rows live — never WHETHER each criterion was exercised at the floor.

## Required Output — the Evidence Sheet (Full tier)

**Full-tier tasks** write the sheet described here. **Light-tier tasks** carry the SAME two row families inline in the done message — identical structure, no disk file.

One sheet per task at `{evidence_root}/{project}/{YYYY-MM-DD}-{feature}.md` — `{project}` is the app or repo being modified; capture files go in a sibling folder `{YYYY-MM-DD}-{feature}/`. Resolve `{evidence_root}` from the workspace CLAUDE.md routing table; absent a routing entry, default to `docs/done-gate-evidence/` at the modified repo's root. Create the sheet at Contract time with the confirmed criteria; fill verdicts at Exhibit. (Light tier skips the file — it records the same rows inline at Exhibit.)

The sheet carries TWO row families, both created at Contract time. Every row's first column is **Criterion** — the contracted outcome, verbatim.

**Drivability rows** (one per criterion — from the Drivability Check above):

| Column | Content |
|--------|---------|
| Surface | The surface the outcome runs through |
| Verdict | `drivable` / `needs-seam: {pattern}` / `un-seamable: {reason}` |
| Seam built | Path/flag of the seam built (when `needs-seam`); empty otherwise |

**Exercise rows** (one per criterion — filled at Exhibit):

| Column | Content |
|--------|---------|
| Gesture performed | What was actually done to exercise it |
| Observed result | What actually happened |
| Evidence file | Relative path to the capture created during this exercise |
| Verdict | `held` / `held-surprising` / `failed` / `unexercisable` + concrete reason |

The done message to the owner = (Full) the sheet path + one-line verdict summary, or (Light) the inline Exercise rows + one-line verdict summary — and, in BOTH tiers, every `failed`, `unexercisable`, and `held-surprising` row surfaced explicitly.

## Seam Patterns

A seam adds an agent-drivable path WITHOUT faking the owner's gesture — the human-facing action stays real; the seam supplies or exposes ONLY the part the agent otherwise cannot reach.

| Surface the agent can't drive / observe | Build this seam |
|-----------------------------------------|-----------------|
| **Native OS dialog or widget** — file picker, folder picker, color picker, native print/save | An env-gated injection path (e.g. a guarded `HYP_TEST_DIALOG` env + a `/api/_test/set-dialog` endpoint) that supplies the chosen value while the triggering click stays a real gesture. NEVER stub the whole flow. |
| **Isolated-run data/config isolation** — an exercise on a scratch config silently reaches production data | Honor an explicit config-root / override variable (e.g. `BOOKKEEPER_CONFIG_DIR`) in EVERY resolution path. No code path may resolve config, corrections, logs, or output location independently of the override. |
| **Fused or composed output** — RRF-fused search, a multi-arm pipeline where you cannot tell which arm produced a result | A per-arm isolation surface (e.g. `--vector-only` / `--fts-only`) so each arm is independently exercisable and verifiable. |

A new un-drivable surface no pattern covers → build the smallest seam that keeps the real gesture real, and name the new surface in the done message so the pattern set can grow.

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
| Skip | "Task too small for the gate" | Check the exempt list. Not on it → gated. Small-but-gated → Light tier: the gate still runs (Contract, exercise, Lock); the evidence goes inline in the done message, not to a disk sheet. A one-criterion contract costs minutes. |
| Skip | "No contract was made at intake — I'll just describe what I did" | STOP. Draft criteria now, confirm with the owner, then exercise them. Done stays locked until then. |
| Skip | "I'll figure out how to drive it at done-time" | The drivability check runs at Contract, before Build. Hitting the wall at Exhibit and re-inventing the seam every project is the exact waste this rule removes. |
| Skip | "This criterion is obviously drivable, no need to state it" | Mark the row `drivable`. An unstated check is a skipped check. |
| Game | "Headless run is equivalent and faster" | Floor violation. UI criteria require a visible browser and real gestures. |
| Game | "DOM says the element is there / headless e2e is green — the layout's fine" | Presence ≠ geometry. Measure the rendered box (size/position/aspect) in a headed browser; a collapsed or oversized layout passes presence checks. |
| Game | "I'll fill the sheet from test results / memory" | Sheet rows cite files captured during the exercise. No capture → the row does not exist → done locked. |
| Game | "Can't drive this — mark it `held`, it probably works" | Mark `unexercisable` + the concrete blocker, and surface it in the done message. |
| Game | "I'll stub the whole flow so the test passes" | A stub that replaces the owner's gesture is not a seam — it proves nothing at the fidelity floor. The seam supplies only the unreachable part; the real gesture stays real. |
| Game | "I'll mark it `un-seamable` so I needn't build the seam" | `un-seamable` is ONLY for surfaces outside the software's control. A surface you own and could wrap is `needs-seam`. If `un-seamable` fires more often than seams get built, the rule is being dodged. |
| Game | "I'll rephrase the criteria into technical assertions I can pass" | Criteria stay owner-observable. Internal assertions live in your tests, not in the contract. |
| Game | "I'll rename the criterion into something I can already drive" | The criterion stays the owner's observable outcome. Build the seam to the real outcome; never retarget the outcome to dodge the seam. |
| Game | "The behavior holds technically — the surprise is a pre-existing quirk, not my code" | Mark `held-surprising`. Pre-existing quirks are exactly the surprises the owner must judge. |
| Game | "I noticed the non-obvious mechanism but the criterion still passes — it's fine" | Apply the owner-lens: read the observed result with zero build context. If surprising → `held-surprising`. |
