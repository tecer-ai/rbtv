# Full checks

The three checks of the full tier of [Compound](../compound.md), step 3. They find what the sweep cannot: a deviation nobody corrected and no tool signalled. Each is a wave of checkers under the `coordinate` skill, routed `cast route --access bounded --type text --class bounded --optimize price`, launched on a different model from the session's own when the catalog offers one. Every finding is a candidate for step 4, never an entry.

## The record

The checks read the session's record as a transcript, not the raw file: `session-sweep transcript RECORD --out <run>/transcript [RECORD ...]` writes `chunks/chunk-NNN.md`, each holding the visible events of a span of the session in order (the user's messages, the agent's text, each tool call with its input and its result cut to its first lines), and prints `events N` and `chunks N`. Pass the records of the session's sub-agents as further `RECORD` arguments when you have them; their reports alone are already in the sweep. The transcript stays in the run folder; this tier collects no manifest and runs no fidelity pass, which belong to [Work history](../work-history.md) when the user asks for the archival record.

## Check 1: the instructions in force

What the agent was bound to, against what it did.

Inputs per checker: one transcript chunk; the instruction set in force, as paths: the installation's instruction files and rules the agent received, the list of installed skills with their descriptions (`rbtv list --installed`), and the agent's prompt when it has one. A change the session itself made to one of those files holds from the turn that made it.

The checker reports, per turn of its chunk, every per-turn instruction not run (the instruction says "before each turn" or "on every X" and the turn shows no such step), every skill whose ALWAYS LOAD WHEN matched a step the agent took with no load of that skill before the step (a skill load is a visible tool call), and every rule whose action condition arose with no action. One row each:

`turn | instruction (file and the sentence) | what the agent did instead | evidence (chunk line)`

## Check 2: decisions and requests

What was decided or asked, against what was done.

Inputs per checker: one transcript chunk; the project's decisions file when the work has one; the requests table the final-act entry step produced for this session; the user's decisions as the transcript records them in earlier chunks, which the caller lists by chunk line when they fall outside this checker's chunk.

The checker reports every edit, answer or action in its chunk that contradicts a decision or a request, and every request or decision the agent accepted in words ("understood", "will do") and then did not act on. One row each:

`turn | the decision or request (where it is stated) | what contradicts it (chunk line) | agreed first: yes or no`

The "agreed first" column matters: an instruction the agent accepted and then dropped points to a mechanism gap (nothing held the instruction), not to its wording.

## Check 3: the disk

What was claimed, against what exists.

Inputs for one checker: the session's claims of completion, which the caller lists from the transcript with their chunk lines ("done", "committed", "fixed", "sent", "installed"); the working folders the session touched; read access to `git status`, `git log` and `git diff` there.

The checker reports every claim the disk does not show (a file said written that is absent or unchanged, a commit said made that the log lacks, an install said run that left the generated file old), every change on disk the record never mentions (an untracked or modified file no turn accounts for), and every leftover the session created and did not remove (a scratch file in the tree, a worktree, a lock). One row each:

`claim or change | where claimed (chunk line) or where found | what the disk shows | verdict: confirmed, wrong, unaccounted`

## Returns

Each checker writes one page in `<run>/checks/<check>-chunk-NNN.md` holding its rows and a last line `UNVERIFIED:` naming what it could not observe. Read the pages; when they exceed one page in total, send them to one summarizer that merges equal findings across chunks into one row with the count, and read its page. Every row is a candidate in step 4 of Compound; a row that two checks report is one candidate.
