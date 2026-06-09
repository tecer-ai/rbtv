# Build for Agent Testability

When a feature's owner-observable outcome runs through a surface the agent cannot drive or observe, the agent MUST build a test seam for that surface as part of the feature — so the outcome is exercisable at the done-gate fidelity floor without faking the owner's gesture.

## Trigger and Scope

**Activates when:** at `rbtv-done-gate`'s Contract moment — for EACH drafted outcome criterion, run a **drivability check** BEFORE Build. Same default-ON coding-task scope as the done gate. Read `rbtv-done-gate` for the Contract phase and the evidence sheet this rule writes onto.

**Does NOT apply to:**

- Anything `rbtv-done-gate` exempts (typos, formatting, comments, zero-behavior cleanups, runtime-invisible config). Fails safe: not exempt there → checked here.
- A criterion whose surface the agent can ALREADY drive and observe with a real gesture — a normal in-page control, a CLI flag, a file it reads/writes. Mark it and move on; no seam needed.

**Boundary:** this rule governs what you BUILD so the outcome is drivable. HOW you then exercise and prove it is `rbtv-done-gate`'s job. Internal correctness (unit tests, type checks, builds) stays your normal testing job.

## The Gate — Drivability Check + Seam Plan

Structured-output gate, run at Contract time and recorded on the existing done-gate evidence sheet (no separate artifact). For EACH criterion, classify its outcome surface and act before Build:

| Verdict | Meaning | Required action before Build |
|---------|---------|------------------------------|
| `drivable` | The agent can perform the real gesture and observe the result as-is | None — proceed |
| `needs-seam: {pattern}` | The outcome runs through a surface the agent cannot drive or observe | Build the seam named from Seam Patterns AS PART OF the feature |
| `un-seamable: {reason}` | The surface is genuinely outside the software's control (third-party OS chrome you cannot wrap, a remote service) | Record it; it becomes a done-gate `unexercisable` row + owner-UAT |

**Required output:** one drivability row per criterion on the evidence sheet at Contract time — `criterion | surface | verdict | seam built (path/flag)`. A `needs-seam` row still seamless at Exhibit = the feature is NOT built; done stays locked.

## Seam Patterns

A seam adds an agent-drivable path WITHOUT faking the owner's gesture — the human-facing action stays real; the seam supplies or exposes ONLY the part the agent otherwise cannot reach.

| Surface the agent can't drive / observe | Build this seam |
|-----------------------------------------|-----------------|
| **Native OS dialog or widget** — file picker, folder picker, color picker, native print/save | An env-gated injection path (e.g. a guarded `HYP_TEST_DIALOG` env + a `/api/_test/set-dialog` endpoint) that supplies the chosen value while the triggering click stays a real gesture. NEVER stub the whole flow. |
| **Isolated-run data/config isolation** — an exercise on a scratch config silently reaches production data | Honor an explicit config-root / override variable (e.g. `BOOKKEEPER_CONFIG_DIR`) in EVERY resolution path. No code path may resolve config, corrections, logs, or output location independently of the override. |
| **Fused or composed output** — RRF-fused search, a multi-arm pipeline where you cannot tell which arm produced a result | A per-arm isolation surface (e.g. `--vector-only` / `--fts-only`) so each arm is independently exercisable and verifiable. |

A new un-drivable surface no pattern covers → build the smallest seam that keeps the real gesture real, and name the new surface in the done message so the pattern set can grow.

## Anti-Patterns

| Type | Thought | Action |
|------|---------|--------|
| Skip | "I'll figure out how to drive it at done-time" | The drivability check runs at Contract, before Build. Hitting the wall at Exhibit and re-inventing the seam every project is the exact waste this rule removes. |
| Skip | "This criterion is obviously drivable, no need to state it" | Mark the row `drivable`. An unstated check is a skipped check. |
| Game | "I'll stub the whole flow so the test passes" | A stub that replaces the owner's gesture is not a seam — it proves nothing at the fidelity floor. The seam supplies only the unreachable part; the real gesture stays real. |
| Game | "I'll mark it `un-seamable` so I needn't build the seam" | `un-seamable` is ONLY for surfaces outside the software's control. A surface you own and could wrap is `needs-seam`. If `un-seamable` fires more often than seams get built, the rule is being dodged. |
| Game | "I'll rename the criterion into something I can already drive" | The criterion stays the owner's observable outcome (`rbtv-done-gate`). Build the seam to the real outcome; never retarget the outcome to dodge the seam. |
