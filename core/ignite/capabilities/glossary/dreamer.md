# Dreamer

The dreamer is Ignite’s shared process for turning conversation evidence into long-term [memory](memory.md). It processes agents in sequence. It is not an agent prompt or a second writer to build for each agent.

Use the [Dreamer runbook](../runbook.md#dreamer) to enable, run or diagnose consolidation. Nightly runs and the watchdog depend on configuration; an explicit operator `ignite dreamer run` can run while the nightly setting is disabled. An ordinary agent turn does not invoke it or edit the files it owns.

## Evidence and publication

The model proposes additions, replacements and archives from eligible owner conversation evidence and explicit [inbox](inbox.md) requests. Injected or recalled text and the dreamer’s own writing are not new evidence. Follow [watch-out and inbox handling](../runbook.md#dreamer-watch-outs-and-unread-messages) for required provenance, duplicate filing and cursor advancement; a board correction without the necessary evidence stays pending.

Deterministic code validates each proposal before publication. It refuses over-cap content rather than truncating it, checks that files have not changed since reading, and retains removed material or a verified filing destination with a reason. It never edits `prompt.md` or rbtv source. A conflict with those instructions goes to the owner’s digest.

A successful publication commits changed general memory, each affected agent’s memory and its board. Applied writes already matching the committed version need no new commit. The cursor advances only under the publication conditions in the runbook; an unrelated agent’s writes must not consume unprocessed evidence. Use that commit to undo a bad publication.

## Observe the result

A quiet run makes no model call or digest. Consolidation reports changed files or new conflicts; a failure alerts the owner. The enabled watchdog reports a missing successful run after its documented 48-hour interval. Queueing a notice is not delivery confirmation; use the runbook’s result fields to distinguish them.

Verify with disposable memory and conversation fixtures through the shared consolidation operation. Check a successful write, refusal without truncation, unchanged input, and preserved cursor on failure. Do not use a live consolidation merely to test documentation.
