# 20260831-i-vault-root-git-diff-of-nested — vault-root git diff of nested rbtv repo grades empty-green

kind: issue
component: meta-leader
date: 2026-08-31
commit: 899694e7
deployed: no
pin: NONE
components: meta-planning

## Observed
Task 170 (redesign-continue-1 seed): on `stools-canvas-audio-elevenlabs-close` M6, Observable D
("zero canvas instructions added") was to be graded off `git diff -- 3-resources/tools/rbtv/…`
run from the vault root. That tree is a nested git repo the vault ignores (vault `.gitignore:6`),
so the command exits 0 with 0 bytes REGARDLESS of whether the nested tree is dirty — a grading
check that can never fail. Manual patch at the time: the leader refused the ask as written and ran
`git -C 3-resources/tools/rbtv diff -- meta/master/references/slack-message-format.md` instead
(`p-m6-diff-evidence`). Re-verified 2026-08-31 on the current tree: `git -C <vault> diff -- 3-resources/tools/rbtv/meta/master/references/slack-message-format.md`
against a planted append still prints 0 bytes / exit 0, while `git -C 3-resources/tools/rbtv diff --
meta/master/references/slack-message-format.md` against the same planted append prints 543 bytes.
Grepped `meta/` for the literal vault-root form (`git diff -- 3-resources/tools/rbtv`) — zero hits;
the bad form lived only in that one goal's own evidence text, never in a reusable brief, so nothing
else was minting it. But no brief that DOES gather rbtv-repo evidence stated the nested-repo rule
either, so the trap was one edit away from recurring the next time a leader or judge composes a
diff command from scratch.

## Mechanism
`3-resources/tools/rbtv` is a separate git repository checked out inside the vault tree and listed
in the vault's own `.gitignore`. `git -C <vault> diff -- <path under that tree>` walks the VAULT's
index, which has no entry for anything under that path (`git ls-files --error-unmatch` there
answers "did not match any file(s) known to git") — so the diff is empty regardless of the nested
repo's own working-tree state. Nothing about that command's output distinguishes "clean" from
"wrong target"; both print zero bytes and exit 0.

## Attempts
First attempt held on this exact defect — checked: `rbtv embed-search` + the grep floor over every
`_issues.md`/`_creations.md` surfaced `meta-master/20260828-c-audio-flow-section-in-slack-me`,
whose own ATTENTION #1 already states the hazard from the M6 incident, but that record lives in
the CLOSED build-memory (read-before-editing, not a brief an executing seat consults mid-trial) and
carries no fix to a brief. No prior entry had added the rule to a brief that composes or checks
rbtv-repo evidence.

## Fix
Added one sentence to `meta/leader/prompts/leader.md` §2 ("Triage on evidence you observe, never on
the report" — the leader's own act of checking a seat's claim against disk) and one clause to
`meta/planning/prompts/dod-judge.md` step 1 (gathering the evidence a done-contract clause names):
both now state, inline at the point evidence is gathered, that the rbtv repo is a nested repo
requiring `git -C 3-resources/tools/rbtv …`, never a vault-root form. Landed at the two seats that
actually gather/check evidence against the rbtv repo, rather than at `meta/master/references/slack-message-format.md`
(Slack formatting, not an evidence-gathering brief — grepped, carries no diff-command guidance,
would have been noise) or at `meta/planning/prompts/drafter.md` (authors milestone clauses but not
found to compose diff commands itself). Rejected: editing the goal's own historical
`relay-ask.md` under `.rbtv/goals/` — that folder is out of scope per this plan's read-first and
the defect is generic, not specific to one goal's evidence text.

## Consequences
Pure addition — 2 sentences across 2 files, no deletions, nothing reordered. Nothing else in either
prompt reads or depends on the wording touched, so no other section of `leader.md` or `dod-judge.md`
needed a matching edit. No follow-up fix elsewhere in the tree was required by this change, and no
regression surface was introduced — both files remain valid prompt sources with the same structure
as before, just carrying one more sentence of evidence-gathering guidance each.

## Verification
Red-first (before + after, same repro): planted an append to `meta/master/references/slack-message-format.md`
in the rbtv repo, confirmed `git -C <vault> diff -- 3-resources/tools/rbtv/meta/master/references/slack-message-format.md`
prints 0 bytes / exit 0 on the dirty tree (the trap), and `git -C 3-resources/tools/rbtv diff --
meta/master/references/slack-message-format.md` prints 543 bytes on the same dirty tree (the fix
form correctly reds it); reverted with `git -C 3-resources/tools/rbtv checkout -- <path>` and
re-confirmed 0 bytes clean. Grepped `meta/` after the edit for the bad literal form — the only two
hits are inside the new warning sentences themselves (quoting the form to name it as wrong), not a
minted grading command. Committed at `899694e7`, uncommitted daemon leg: none — these are prompt
sources read at sitting-start, not boot-time config; no restart needed.

## ATTENTION
1. `git diff` (and `status`/`log`/`show`) against anything under `3-resources/tools/rbtv/` MUST be
   run `git -C 3-resources/tools/rbtv …`. A vault-root form exits 0 with 0 bytes on a dirty nested
   tree — read that as "wrong target", never "clean".
2. This fix is textual guidance at two evidence-gathering seats (leader, dod-judge), not a
   mechanical guard — a THIRD brief that composes a diff command over the rbtv repo from scratch
   (a new judge/relay prompt, a goal's own drafted done-contract clause) can still reintroduce the
   vault-root form; grep `meta/` for the literal bad form before trusting a new one is clean.
- git diff/status/log against 3-resources/tools/rbtv MUST use git -C — a vault-root form exits 0/0-bytes on a dirty nested tree
