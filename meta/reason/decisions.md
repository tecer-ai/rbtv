# reason decisions

Standing decisions about the reason component. Each states the decision and its reason; the rule, the skill and the pages of `capabilities/methods/` describe the resulting design.

## One skill for thinking a subject through: thinking-partner

Interview and the six brainstorm modes are method pages under the `thinking-partner` skill, not skills of their own. Reason: they serve one purpose, thinking a subject through with the user, and the user often cannot say whether their subject is already clear; the clear/unclear test is a mode pick inside the skill, where the agent can switch when the subject turns out otherwise, and nested exposure forbids a skill inside a skill.

## One component for the rule and the skill

The `critical-partner` rule and the `thinking-partner` skill form the `meta/reason` component. Reason: owner decision, 2026-10-08; the always-on stance and the invoked session are the two faces of one subject, how an agent reasons with the user, and `behaviour` keeps only the state-hygiene rule.

## One always-on rule for the critical stance: critical-partner

Challenging a proposal, framing a vague request, stating the simplest solution and stating the root cause are four tripwires of one rule, `critical-partner`, not four rules. Reason: they are one stance applied at four moments, and four files on every task repeated their motivations; the state-hygiene rule stays separate because it guards a file left for a later agent, not a moment of judgment.

## Every tripwire produces a named block in the response

Each tripwire writes a block with a fixed tag (`<counter>`, `<frame>`, `<simplest>`, `<cause>`) in the response text, before the tool call or sentence it governs, in a headless seat too, and the sentence after it says what it changed. Reason: an audit of 188 saved transcripts (2026-10-08) found the one rule with a named block fired in every harness, while the rules that asked for a sentence "before the first edit" fired in Codex seats and left no trace in Claude Code seats; a block the following plan never cites was also common, hence the closing sentence.

## No block for a factual answer or a delegated mechanical edit

Reason: a rename or a lookup carries no decision to counter, frame or simplify, and a block there is noise that trains the reader to skip the blocks that matter.
