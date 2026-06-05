# {Rule Name}

{One sentence: what behavior this rule enforces.}

## Trigger and Scope

**Activates when:** {specific input pattern, task type, or moment that triggers this rule.}

**Does NOT apply to:** {explicit scope boundary — when this rule is skipped.}

## {Enforcement Section — name after the mechanism}

{Gate, pre-flight check, or primary enforcement mechanism. This is the core of the rule — the thing the agent MUST do.}

| {Structured output element} | {Requirement} |
|------------------------------|---------------|
| {element 1} | {what the agent must produce} |
| {element 2} | {what the agent must produce} |

**Required output:** {What visible artifact proves compliance. What the user can evaluate.}

## Tripwires (if applicable)

{Self-detection patterns. Include ONLY if the rule targets patterns the agent can detect in its own output. Omit this section entirely for rules that use sequencing gates or pre-flight checks.}

| Pattern | Example | Rewrite to |
|---------|---------|------------|
| {pattern} | {bad example} | {correct behavior} |

## Anti-Patterns

{Rationalizations agents use to skip OR game this rule. Include at least one of each type.}

| Type | Thought | Action |
|------|---------|--------|
| Skip | "{rationalization for not triggering the rule}" | {correct action} |
| Game | "{rationalization for token compliance}" | {correct action} |
