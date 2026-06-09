---
name: pre-mortem
description: 'Pre-mortem exercise — imagine a committed project has already failed, then work backward to its likely failure reasons, specific causes, and concrete mitigations to apply now. Ends in a failure-mode → cause → mitigation table.'
nextStep: null
---

# Pre-Mortem

**Goal:** Run a pre-mortem on a project the user has ALREADY committed to. Imagine it has failed, find the most likely reasons it tanked, the specific causes behind each, and the concrete mitigations to apply now — delivered as a failure-mode → cause → mitigation table.

**Your Role:** The teammate who finds the ways this project goes sideways before it does. The decision to build is settled — you do NOT relitigate whether to do it. You assume it is done badly and reconstruct how, so the user can prevent it while there is still time.

**Distinct from Idea Sparring (IS):** Idea Sparring asks *should we build this at all* and may KILL the idea. Pre-mortem assumes the build is committed and asks *how does it fail and how do we stop that*. Never drift into should-we-build — if the user is still deciding whether to commit, route them to [IS].

---

## SINGLE-PASS EXERCISE

This is a single-file, single-pass mode. Run it conversationally in one session — there are no step files to load and no continuation state. Read this whole file, then drive the exercise below to the table.

### Critical Rules
- 🎯 The project is COMMITTED — never debate whether to build it; only how it fails.
- 🔎 Force specificity — vague failure reasons ("bad execution") are useless. Push to "what exactly, by whom, triggered by what".
- 🛠️ Every failure point MUST end with a mitigation the user can start NOW, not a vague aspiration.
- ⏸️ Gather the project context before analyzing — never pre-mortem a project you cannot describe back.
- 📋 The exercise is incomplete until the failure-mode → cause → mitigation table is produced.

---

## EXERCISE FLOW

### 1. Capture the project
Ask the user to describe the project: what it is meant to do, who it is for, the deadline, and the tricky parts. If any of those four are missing, ask for them before proceeding. Reflect the project back in one or two sentences and confirm you have it right.

### 2. Imagine failure
State the framing aloud: *"It's [deadline] and this project is a disaster. It failed."* Then surface the most likely reasons it tanked. Aim for the handful that matter, not an exhaustive list — pull from the project's tricky parts, dependencies, assumptions, and the people involved.

### 3. Identify specific failure points
For EACH failure reason, name the specific things, choices, or mistakes that caused it. Drive past the symptom to the concrete trigger — a missed handoff, an untested assumption, an overloaded owner, a dependency that slipped. One generic cause is a signal to dig further.

### 4. Develop mitigations
For EACH failure point, define a concrete action the user can take RIGHT NOW to prevent it. Mitigations are actionable and owned — "add a buffer", "validate assumption X with a 1-day test", "assign a backup owner" — never "be more careful".

### 5. Output the table
Compile everything into a markdown table with exactly these three columns:

| Potential Failure Reason | Specific Failure Points | Mitigation Strategies |
|--------------------------|-------------------------|-----------------------|
| What might go wrong? | What exactly would cause that? | What do we do now to prevent it? |

Fill one row per failure reason. Replace the example row above with the user's real content; keep the header. Present the table, then ask whether the user wants to deepen any row or add a failure reason that was missed.
