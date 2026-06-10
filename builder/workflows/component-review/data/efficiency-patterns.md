# Efficiency Patterns

Token-waste pattern taxonomy for component diagnosis and design-time prevention. Two consumers: the component-review workflow (diagnostic lens, steps 01–04) and component-creation step-05 (the Create-Time Gate section at the end). Patterns are classified by COST LOCUS — where in the agent loop the waste is paid.

---

## The Four Cost Loci

| Locus | The question it asks |
|-------|---------------------|
| **LOAD** | Is material loaded that the session or task doesn't need, or loaded in a more expensive form than needed? |
| **DECIDE** | Is judgment spent where a deterministic structure could decide? |
| **RECORD** | Is more written than is ever consumed, or written more expensively than needed? |
| **COORDINATE** | Do component seams force re-derivation or mismatch repair? |

A waste item is filed under the locus where its FIX lives, not where its symptom appears.

---

## LOAD Patterns

| Pattern | Detection heuristic | Fix direction |
|---------|--------------------|---------------|
| Always-on for event-gated behavior | Text loaded every session whose own trigger fires in a minority of sessions (judge firing rate from the trigger text itself) | Event-scope it: a 1–2 line always-on trigger pointing to a JIT detail file; or scope installation to the contexts where it fires |
| Multi-source clause | The same constraint stated verbatim or near-verbatim in 2+ files — the duplication detector in `../scripts/measure-component.py` surfaces shared blocks | Single authority: one canonical statement; every other site carries a functional reference only |
| Render/copy artifact | Generated copies multiplying a shared core (N rendered files × the same boilerplate) | Verify runtime reads are JIT against the source; exclude generated mass from cost claims — but confirm nothing reads the copies wholesale |
| Monolithic loading | A consumer must load a large file to use a small part — no index, no section anchors, no per-mode split | Split by consumption unit; index plus selective load |
| Self-duplicated section | The cross-file duplication detector misses it; detect by intra-file section-heading repetition (same `##` heading twice) | Delete the second occurrence |

## DECIDE Patterns

| Pattern | Detection heuristic | Fix direction |
|---------|--------------------|---------------|
| Prose arbitration | One sentence or table cell carrying 3+ precedence operators (EXCEPT, UNLESS, WINS, OVERRIDES) that the executor must resolve on every occurrence | An N-input decision table: enumerated inputs → one output action, no prose resolution |
| Algorithm-in-prose | A procedure with exact inputs and outputs specified as prose the agent re-interprets per run (tokenizers, scoring formulas, selection orders) | Extract to a script or lookup table; the file cites the invocation, never restates the algorithm |
| Dual authority | A workflow or step restating behavior an always-on rule already mandates — or two files each claiming to own the same decision | Delete the restatement; exactly one file owns the behavior, all others reference it |
| Judgment-fired trigger | A trigger relying on agent self-assessment at an unmeasurable moment ("when context fills", "when appropriate") — these under-fire precisely when the agent is busiest | Anchor to a discrete observable moment: a mandatory checklist row inside an existing procedure, or a measurable threshold |
| Cross-trigger single-source over-merge | A clause appears in 2 files BUT the two sites fire on different triggers; naive dedup would silence one trigger | Single-source the *statement*, keep a one-line trigger stub at each site that cross-references the canonical home — do NOT collapse to one site if a trigger would lose coverage |

## RECORD Patterns

| Pattern | Detection heuristic | Fix direction |
|---------|--------------------|---------------|
| Uniform ceremony floor | The same artifact set required regardless of task size; no light path for trivial cases INSIDE the flow (entry-level exemptions don't count once the flow is running) | A qualifying light path with explicit criteria; escapes owner-approvable, never silent |
| Fragmented bookkeeping | One semantic state transition requires N separate file edits | One scripted transition updating all N surfaces in a single call |
| Write-only artifact | An artifact maintained during a run that no later step, agent, or file reads — check consumption by grepping for inbound references | Fold into a close-time synthesis step or delete; keep only artifacts with a NAMED consumer |
| Narrated logging | Log entries mixing a forward-affecting ruling with completion narration ("all N criteria held, approved, and...") | Strict entry template: ruling + scope only; completion belongs in the run log alone |

## COORDINATE Patterns

| Pattern | Detection heuristic | Fix direction |
|---------|--------------------|---------------|
| Blind contract seam | A producer emits a format without reading its consumer's contract (e.g., task files authored blind to the executor's required frontmatter) | The producer derives output from the consumer's contract — or both consume one shared schema |
| Re-derived constant | A path, name, or value the agent computes each run instead of reading from one stated place (wrong-path stumbles in transcripts are the symptom) | A canonical constant in the owning manifest or data file |
| Duplicated lifecycle logic | The same decision made independently at two lifecycle moments (e.g., plan-time executor choice and run-time routing) | One shared function or file called at both moments |

---

## Diagnostic Method Requirements

These bind every component-review run:

| # | Requirement |
|---|-------------|
| 1 | **Measure, never estimate** — every figure comes from `../scripts/measure-component.py` or an explicit `wc`/`grep` invocation visible in the transcript. A reasoned number is a defect. |
| 2 | **Quality floor** — protections keep their value; only the delivery format is on trial. Every cut proposal names the protection and the format that preserves it. |
| 3 | **Test felt waste** — the owner's inefficiency hypotheses are recorded verbatim at intake and TESTED against evidence. Felt waste and measured waste routinely diverge — in both directions. |
| 4 | **Hunt counter-evidence** — content that earns its cost is marked KEEP with the failure it guards. A diagnosis with zero KEEP rows is suspect: it means the earned-content hunt did not run. |
| 5 | **Read-only investigators** — file reading happens in dispatched read-only sub-agents (default model: sonnet). The conductor's context holds conclusions, not file dumps. |

---

## Create-Time Gate

Consumed by `component-creation/step-05-efficiency-gate.md`. Run against every file created or structurally modified in the build session. For each row: pass, or fail with evidence. A fail is fixed or explicitly accepted by the owner — never silently passed.

| # | Gate check | Pass condition |
|---|-----------|----------------|
| 1 | Single authority | No clause in the new files restates a constraint owned by another file (rule, card, step, or data file) — functional references only |
| 2 | Determinism | Every exact procedure (count, sort, parse, select, render) cites a script, table, or schema — none is specified as prose for the executor to re-interpret |
| 3 | Discrete triggers | Every trigger names an observable moment — no self-assessed firing conditions |
| 4 | Named consumers | Every artifact the component instructs agents to write has a named consumer that reads it |
| 5 | Event-scoped load | Detail loads JIT at the moment of use; always-on text is no larger than the trigger needed to find it |
| 6 | Size limits | Every file is within the limits in `../../component-creation/data/component-patterns.md` |
| 7 | Light path | If the component prescribes per-task ceremony, a trivial-case light path exists with explicit qualifying criteria |

---

## Quick Reference

- File waste by FIX locus: LOAD / DECIDE / RECORD / COORDINATE.
- Measured figures only; hypotheses tested; KEEP rows mandatory; read-only sonnet investigators.
- Create-Time Gate: 7 checks, fail = fix or owner-accepted, never silent.
