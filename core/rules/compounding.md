# Compounding

## On User Correction

When the user corrects agent behavior, fix the immediate problem AND produce a **Recurrence Check**:

| Check | Question |
|-------|----------|
| Pattern | Has this type of error occurred before in this session or in prior sessions? |
| Structural fix | Would a rule update, CLAUDE.md change, routing rule, memory entry, or workflow adjustment prevent recurrence? |
| Scope | Does the fix apply to this vault only, or to all RBTV instances? |

If a structural fix exists, state what it is and where it would go. Ask if the user wants to implement it. Never silently skip the check.

## On Self-Detection

When you notice a pattern in your own behavior — repeating the same type of mistake, consistently missing the same class of edge case, or working around a gap in the rules — trigger the Recurrence Check above without waiting for the user to correct you.
