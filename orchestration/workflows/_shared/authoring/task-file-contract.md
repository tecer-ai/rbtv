# Task-File Contract

The contract every executable task file MUST satisfy, regardless of which worker executes it. A task file that violates this contract is malformed — the dispatcher halts and reports it rather than inferring missing parts.

Evidence base: 22/22 Kimi tasks landed first-try when the task file was fully self-contained (`learnings-kimi-worker.md` §3); ambiguity became a silent bug every time a field was left to inference.

---

## 1. Self-Containedness — zero context

A task file MUST be interpretable by a worker that has NONE of this conversation, plan history, or "as discussed" knowledge. Inline everything the worker needs; reference another file ONLY when the worker must open it to execute.

| Rule | Why |
|------|-----|
| Inline every interface, edge case, and decision the work depends on | The cheapest capable worker is treated as non-reasoning; what is not stated is guessed |
| Inline EXACT current-code excerpts being modified | The worker anchors edits on the quoted text; a stale/wrong excerpt corrupts the edit |
| **Content anchors, never line numbers** | Line numbers go stale the moment a prior task touches the file — locate by "the block reading `<exact code>`" |
| No "as discussed", "per our earlier" | Another agent was not in the conversation |
| Forbidden-paths / out-of-scope reads stated explicitly | The worker must know what NOT to touch, not only what to touch |

## 2. Granularity

| Rule | Description |
|------|-------------|
| WHAT, not HOW | State the outcome; include HOW only where the user decided it |
| Single action per task | One discrete, independently completable action — never combine actions with "and" |
| Room for judgment | Leave implementation choices to the worker unless the user specified them |
| One bounded dispatch | One module or one coherent slice per task — sized so the worker needs no re-dispatch |
| Self-verifiable acceptance | Give checks the worker can run itself (a syntax check, a one-line probe, a DOM/output assertion) — these correlate with genuinely-done work |

## 3. File-operation verbs

Every file action uses an explicit verb. Format: `[VERB] [path] [with/to/containing] [content description]`.

| Verb | When |
|------|------|
| CREATE | New file that does not exist |
| UPDATE | Modify an existing file |
| DELETE | Remove a file |
| MOVE | Relocate or rename a file |

## 4. File allowlist

Every task carries an explicit allowlist of the files it may create / modify / delete (`✚ create` · `✎ modify` · `✗ delete`). This is the dispatcher's post-run enforcement contract: it diffs the worker's actual changes against the allowlist. Out-of-allowlist ≠ wrong, but it ≠ silent — it means orchestrator review required (`learnings-kimi-worker.md` §4). Repeat the allowlist in human-readable body form even when machine-readable frontmatter also carries it.

## 5. Context budgets

Size the context a task loads; split when it will not fit.

| Context to load | Action |
|-----------------|--------|
| < 50k tokens | Single task, proceed |
| 50–100k tokens | Consider splitting; state the reasoning |
| > 100k tokens | MUST split — a research task produces a ~10–20k summary, downstream tasks consume the summary, not the raw sources |

## 6. Checkpoint / acceptance criteria

Acceptance criteria are ALWAYS owner-observable or worker-runnable outcomes — never an internal assertion the worker cannot exercise. Each criterion states the gesture and the visible result: "when done, running `X` produces `Y`" or "the owner opens `Z` and sees `W`". A task whose only "criterion" is "works" or "looks right" is malformed.

## 7. Return contract

Every task names the fields the worker returns: status, files changed (+ commit hash if committed), validation run (commands + exit + skips with reasons), concerns, blockers/open questions. The return MESSAGE is a hint; disk state is the truth — the dispatcher reconciles the message against the repo before trusting it (`learnings-kimi-worker.md` §S3.2).

## 8. Per-model contract plug-in seam

This file is the GENERIC contract — model-independent. Each model package (`orchestration/models/{model}/`) extends it with a model delta that adds ONLY what that worker needs on top of §1–§7: required frontmatter fields, invocation-specific constraints (workdir, commit policy, swarm policy), and binding dispatch addenda (e.g., the Kimi root-files ban + evidence-file mandate, `learnings-kimi-worker.md` §5). The delta NEVER restates the generic contract — it plugs in. The dispatch-wrapper composes generic contract + model delta at dispatch time. A task authored for a specific model satisfies §1–§7 AND its model delta; a model-agnostic task satisfies §1–§7 and is bound to a model at routing time.

---

## Malformed-task rule

If any required element above is missing, the dispatcher MUST halt and report the malformed task. It MUST NOT infer the missing element into shape — authoring is the author's job, not the dispatcher's.
