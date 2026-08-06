---
name: step-05-synthesize
description: Reconcile — draft delta + open questions; Study — draft study notes + reflection prompts; HALT for user resolutions
nextStepFile: ./step-06-write.md
workflowFile: ./workflow.md
---

# Step 5: Synthesize

**Progress: Step 5 of 6** — Next: Write

---

## STEP GOAL

Mode-branched synthesis. Reconcile produces a delta + open questions list (HALT for answers). Study produces a draft study note + reflection prompts (HALT for user shaping).

---

## MANDATORY EXECUTION RULES

- 🛑 NEVER write final outputs in this step — drafts only, in `<runtime_root>/synthesis/`
- 📖 You (parent agent) MAY read: target docs (reconcile), context references, grouping.yaml, user comments
- 🛑 You MUST NOT read source files
- ⏸️ ALWAYS HALT for user input on open questions / shaping before proceeding to step-06
- 🤖 HEADLESS DISPOSITION (orthogonal to yolo — see § Headless Hand-Back Procedure below): if
  `RBTV_SUBAGENT_DEPTH` is set in the environment, there is no interactive user, and 2A.5/2B.3 hand
  back instead of halting. If unset, HALT for user input exactly as written below — unchanged.

---

## HEADLESS HAND-BACK PROCEDURE (dispatched runs only — interactive behavior is never touched)

> ⚠ SUPERSEDED IN PART — `r-seats-only-architecture` (2026-08-06): the `rbtv-subagent` CLI-lane
> dispatcher (`ignite/capabilities/sub-agent-dispatch/`) is RETIRED; headless dispatch now arrives
> seat-side via the orchestration skill's CLI-worker lane. The hand-back PROPERTY below survives,
> but the `RBTV_SUBAGENT_DEPTH` detection has no live stamper until that lane stamps an equivalent.

Fires at 2A.5 / 2B.3 only. Orthogonal to `yolo` (`workflow.md` § YOLO MODE): a headless run without
`yolo` never reaches this step at all (the menus/approvals in earlier steps still halt); a `yolo` run
with an interactive user still uses the HALT below, unchanged. Headless means "no interactive user is
present," not "don't ask me to confirm."

**Detect once:** run `printenv RBTV_SUBAGENT_DEPTH` (Bash). A value present means this process was
launched by the `rbtv-subagent` CLI-lane dispatcher (`ignite/capabilities/sub-agent-dispatch/env.js`
stamps it into every dispatch's environment and nothing else does) — there is no interactive user to
answer. Absent/empty means proceed with the HALT exactly as written; this procedure does not apply.

**If headless, at 2A.5 or 2B.3, instead of the HALT:**

1. Write `<runtime_root>/synthesis/handback.json`:
   ```json
   {
     "handback": true,
     "workflow": "source-mining",
     "run_id": "<manifest.json run_id>",
     "mode": "reconcile | study",
     "halted_at": "2A.5 | 2B.3",
     "reason": "headless dispatch, no interactive user available to answer open questions / reflection prompts",
     "runtime_root": "<absolute path to <runtime_root>>",
     "questions_file": "<absolute path to open-questions.md (reconcile) or reflection-prompts.md (study)>",
     "question_count": "<int>",
     "detected_via": "RBTV_SUBAGENT_DEPTH env var present",
     "timestamp": "<ISO-8601>"
   }
   ```
2. Update `manifest.json` — ADD (never remove or replace existing keys) a top-level `handback` object:
   `{"at": "2A.5 | 2B.3", "record": "<absolute path to handback.json>", "timestamp": "<ISO-8601>"}`.
   Do NOT touch `current_step` or `completed_steps` — step-05 has not completed, it has handed back.
3. Print, as your FINAL output line, exactly this and nothing else on that line:
   `##RBTV-SOURCE-MINING-HANDBACK## <absolute path to handback.json>`
   This is the one documented, machine-parseable signal a caller's tooling greps for — see
   `scripts/detect-handback.py`, which reads it back out of the dispatcher's persisted stdout log.
4. STOP. Do not print `### 3. Step Menu`, do not wait, do not proceed to step-06.

### Resuming a Hand-Back

A hand-back record (`handback.json`) names `runtime_root` and `questions_file` as absolute paths.
Resuming means (1) merge answers into the questions file, then (2) re-enter the workflow directly
at `step-06-write.md` against that SAME `runtime_root` — never a fresh `/source-mining` dispatch:
a fresh run mints a new `run_id`/`runtime_root` (`step-01-init.md` § 4-5) and derives its own
reflection prompts from its own `extractions/grouping.yaml` at 2B.2, so a fresh run's questions
share no join key with the recorded ones (task 7.92 measured this; a fresh re-dispatch would re-pay
steps 01-04 to reach questions it must then discard).

**1. Merge answers.** Write a JSON file mapping `Q<N>` (matching the `### Q<N>:` headers in
`questions_file`) to the answer text, then run:

```
python3 {rbtv_path}/orchestration/workflows/source-mining/scripts/merge-answers.py \
  --questions <questions_file> --answers <your-answers.json> --in-place
```

Exit 0: every question in the file is now answered — each appended as `- Answer: <text>`, the same
form 2A.5/2B.3 use for a live answer — and the file was written. Exit 2: the merge was refused
(coverage gap, an answer key matching no question, or an attempt to re-answer an
already-answered question) and NOTHING was written; the JSON on stdout says which. The script
never partially writes.

**2. Re-enter at step-06.** Dispatch (or, if interactive, instruct) an agent with a task that
explicitly overrides this workflow's own entry point. `workflow.md` stays the cataloged dispatch
target (`orchestration/exposure.csv:45`) — no new catalog row, no new entry point, zero bytes of
`ignite/` change:

```
RESUME (not a fresh run). A prior source-mining dispatch handed back at <halted_at>. Do NOT follow
workflow.md's own "load step-01-init.md" instruction (see workflow.md § RESUMING A HAND-BACK).
Instead:
1. Read `{rbtv_path}/orchestration/workflows/source-mining/step-06-write.md` directly and follow
   its MANDATORY SEQUENCE exactly, starting at "1. Read State".
2. Treat every `<runtime_root>` reference in that file as: <absolute runtime_root path>
3. `<questions_file>` at that runtime_root already carries every `- Answer:` block from step 1
   above — they are resolved; do not re-halt for input.
```

`step-06-write.md` asserts nothing about `current_step` and carries no precondition guard — its
MANDATORY SEQUENCE opens straight at "1. Read State" — so a resumed run and an in-flight run reach
it identically. If the hand-back's `manifest.json` carries `"yolo": true`, step-06's own YOLO
bypass (§5) skips the `[D] Done` halt and the dispatch exits cleanly on its own.

**If `runtime_root` no longer exists on disk** (the auto-delete below already ran, or the caller
never preserved it), reconstruct it before step 1: recreate `<runtime_root>/manifest.json` and
`<runtime_root>/synthesis/` from any preserved copies of those files, at the SAME absolute paths
`handback.json` names. Step-06's Read State needs exactly `manifest.json` plus the two synthesis
files for the run's mode (`study-draft.md` + `questions_file` for study; `delta-draft.md` +
`questions_file` for reconcile) — it does not read `grouping.yaml`. A reconstruction built this way
cannot exercise `scripts/detect-handback.py`: that script's only input is a dispatch workdir's
persisted `stdout.log` (a different, unrelated path tree — see the script's own docstring), which a
reconstruction from preserved synthesis artifacts alone does not carry.

**⚠ A successful resume deletes what it just consumed.** `workflow.md` § Critical Rules and
`step-06-write.md` § 4 auto-delete `<runtime_root>/` once the final write succeeds (and the parent
`.rbtv-runtime/source-mining/` too, if it becomes empty). Copy anything you need from
`runtime_root` BEFORE dispatching the resume in step 2 — not after.

---

## MANDATORY SEQUENCE

### 1. Read Manifest and Inputs

Read:
- `<runtime_root>/manifest.json`
- `<runtime_root>/extractions/grouping.yaml`
- For reconcile: each `inputs.targets[]` document
- Each `inputs.contexts[]` reference (file or URL — invoke `rbtv-web-searching` skill for URLs)
- `inputs.comments` (user line-comments — verbatim)

### 2A. Reconcile Mode — Draft Delta and Open Questions

#### 2A.1 Apply user comments to target

For each target document, locate every line referenced in `inputs.comments` and produce a proposed change. Record in `<runtime_root>/synthesis/delta-draft.md`:

```
### Change: <one-line summary>
- Source: user-comment line N
- Before: <quote>
- After: <quote>
- Rationale: <one sentence>
```

#### 2A.2 Apply context alignment

For each context reference, identify schema/concept/naming divergences between the target doc and the context. Record additional change blocks tagged `Source: context alignment (<ref-name>)`.

#### 2A.3 Apply grouping findings

For each `final_decision` in `grouping.yaml` that ADDS to the target (additions only — overrides require resolved open questions): record a change block tagged `Source: extraction (<source> line N)`.

#### 2A.4 Generate open questions

Triggers (any of these):

| Trigger | Question |
|---------|----------|
| User comment is itself a question | Verbatim |
| `grouping.yaml` contradiction | "<earlier> vs <later> — pick one or both?" |
| Extraction directly contradicts a user comment | "User comment says X; extraction line N says Y — which?" |
| Context divergence not justified by extraction | "Target says X; context says Y — keep, switch, or revise both?" |
| Extraction adds new concept the user has not opined on | "Add this? <text>" |

##### Recommendation policy

For each question, decide whether to recommend an option. Apply this evidence priority — higher rows override lower:

| Priority | Signal | Action |
|----------|--------|--------|
| 1 | User comment states an explicit preference (verbatim phrasing) | Recommend the matching option; rationale cites comment line |
| 2 | User comment states a partial preference or directional hint | Recommend the option ALIGNED with the user's direction — even if another option is better-engineered; rationale cites comment line |
| 3 | Prior decision in `grouping.yaml` constrains the answer | Recommend the option consistent with prior decision; rationale cites extraction line |
| 4 | No user signal AND no prior-decision signal | Do NOT recommend — write `Recommendation: no user signal — your call`; list one-line tradeoffs per option |

Anti-patterns — STOP and re-evaluate if you catch yourself:

| Anti-pattern | Fix |
|--------------|-----|
| Recommending based on general best practice when user comment was ambiguous | Demote to "no user signal — your call" |
| Recommending the more-structured / more-engineered option without user signal | User leans simpler; when in doubt, lean simpler OR abstain |
| Recommending a different SHAPE than the user's comment (e.g., comment says "keep it simple", rec says "drop the section entirely") | Match the comment's shape — "keep simple" ≠ "delete" |
| Treating a user question as a request for the "right answer" | Questions surface design space; recommend only when one option matches user-comment direction |

Write to `<runtime_root>/synthesis/open-questions.md`:

```
### Q{N}: <one-line summary>
- Source: <user-comment line N / contradiction / divergence>
- Context: <relevant lines or quotes>
- Options:
  - A) <option text>
  - B) <option text>
  - C) <option text>
- Recommendation: <A | B | C | "no user signal — your call">
- Rationale: <one of>
    - user-comment line N: "<verbatim phrase anchoring the choice>"
    - prior decision at extraction line N: "<verbatim phrase>"
    - no user signal — tradeoffs: A=<one line>, B=<one line>, C=<one line>
```

#### 2A.5 Present and HALT — or hand back if headless

Headless? (§ Headless Hand-Back Procedure above) → follow it now with mode=reconcile,
halted_at=2A.5, questions_file=open-questions.md, then STOP.

Otherwise (interactive — unchanged), per `rbtv-chat-discipline` (chunked presentation):

- Print `Open questions: <count>. Top 2:` followed by Q1 and Q2 inline.
- Print `Full list at: <runtime_root>/synthesis/open-questions.md`
- HALT for user answers. Accept answers in any order. Continue presenting batches of 2 until exhausted.
- Append answers to `open-questions.md` as `Answer: <user response>` blocks.
- Do NOT proceed to step-06 until every Q has a recorded answer.

### 2B. Study Mode — Draft Study Notes

#### 2B.1 Build outline

From `grouping.yaml`, build:

```
# <study-doc-title — derived from primary source basename>

## Through-lines
- <each through_line>

## Themes
### <theme name>
- Key concepts: <list with line refs>
- Key claims: <list with line refs>
- Open questions: <list with line refs>
- Tensions: <list>
```

Save to `<runtime_root>/synthesis/study-draft.md`.

#### 2B.2 Generate reflection prompts

| Trigger | Prompt |
|---------|--------|
| Multiple competing through-lines | "Which through-line is most central to your study? <list>" |
| Tension worth deepening | "Tension between line N and line M — which side resonates with your existing understanding?" |
| Theme has many open questions | "Theme '<X>' has <N> open questions — which 1-2 do you want to pursue?" |
| Context reference adds a frame | "Context '<ref>' frames this as <Y>. Adopt, reject, or note as alternative?" |

Write to `<runtime_root>/synthesis/reflection-prompts.md` in the same Q-block format as 2A.4.

#### 2B.3 Present and HALT — or hand back if headless

Headless? (§ Headless Hand-Back Procedure above) → follow it now with mode=study,
halted_at=2B.3, questions_file=reflection-prompts.md, then STOP.

Otherwise (interactive — unchanged): same chunked presentation pattern as 2A.5. Append user responses to `reflection-prompts.md` as `Answer: ...` blocks.

### 3. Step Menu

**YOLO bypass:** if `manifest["yolo"] == true`, skip this menu and auto-continue to Step 06 once every open question / reflection prompt has a recorded answer. The question / reflection HALTs in 2A.5 and 2B.3 are NEVER bypassed by yolo. Otherwise:

| Option | Action |
|--------|--------|
| **[C] Continue** | All open questions / reflection prompts answered — proceed to Step 06 |
| **[B] Back** | Return to grouping; user wants to re-cluster |
| **[X] Exit** | Abort; offer cleanup |

HALT and WAIT.

---

## CRITICAL STEP COMPLETION NOTE

ONLY when **[C] Continue** is selected AND all questions/prompts have answers:

1. Update `manifest.json`: append `step-05-synthesize` to `completed_steps`; set `current_step = "step-06-write"`.
2. Load `./step-06-write.md`.

---

## SUCCESS / FAILURE METRICS

✅ **SUCCESS:** Delta draft (reconcile) or study draft (study) exists; all open questions / reflection prompts answered.

❌ **FAILURE:** Source file read by parent agent; questions left unanswered; draft missing required sections.
