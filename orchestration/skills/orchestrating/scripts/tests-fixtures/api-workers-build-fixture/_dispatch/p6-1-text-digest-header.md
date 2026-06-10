You are drafting the close-out digest for a completed multi-phase orchestration build run ("api-workers-build"). The digest will be presented to the build's owner at the final approval checkpoint, so it must be accurate, compact, and fully derived from the two source documents inlined below — NEVER invent, never embellish; if something is not in the sources, write "not in sources".

Emit EXACTLY ONE file at path `exit-report-digest.md` with this structure:

# api-workers-build — Exit Report Digest

## 1. Run at a glance
One table: phase | what shipped (one line) | commits | checkpoint outcome. Phases 1–5 (Phase 6 is in progress — mark it "in progress (this pilot)"). Derive strictly from SOURCE 2 (deliverables map) and SOURCE 1's shaping.

## 2. Decision register digest
One table row per decision entry in SOURCE 1: id (D1/D2/D3 from Collaborative Decisions; D-exec-1 … D-exec-14) | one-sentence decision | current standing (applied / confirmed / superseded-by-X / deferred follow-on). Status must reflect later entries (e.g. an entry superseded by a later one is marked superseded).

## 3. Pilots and evidence
One table from SOURCE 2's checkpoint rows: pilot | what it proved | outcome (incl. any held-surprising / unexercisable notes).

## 4. Open follow-ons
Bullet list of every item the sources defer or leave owner-pending (follow-on decisions, the user-executed install run, deferred providers). One line each, with its source id.

## 5. Dropped / deferred scope
What was deliberately not built, with the deciding entry id.

Style: terse, factual, tables over prose. Every claim must trace to a source line. Do not add recommendations or commentary — this is a record digest, not advice.

The two sources follow, each verbatim and clearly delimited.
