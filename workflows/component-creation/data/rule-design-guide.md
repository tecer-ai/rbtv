# Rule Design Guide

Reference data for creating effective agent rules.

## Core Principle

**Aspirational rules produce aspirational compliance.** A rule that describes desired behavior ("be critical", "be concise") is a suggestion. A rule that gates a specific action at a specific moment with a required output is enforceable.

Rules must tell agents what to DO, not what to BE.

| Weak (identity) | Strong (procedural) |
|-----------------|---------------------|
| "Be a critical partner" | "Before agreeing, produce a Counter block with three elements" |
| "Be concise" | "If output exceeds 6 lines of prose, cut it" |
| "Don't be sycophantic" | "If you detect praise in your opener, rewrite without it" |

## Required Design Elements

Every rule MUST resolve these during design:

| Element | Question to resolve |
|---------|-------------------|
| Behavior | What specific agent behavior does this rule enforce or prevent? |
| Trigger | When does this rule activate? What input pattern, task type, or moment triggers it? |
| Scope boundary | When does this rule NOT apply? Unbounded rules get ignored. |
| Enforcement mechanism | How does the rule prevent violation? (see Enforcement Types below) |
| Required output | What visible artifact must the agent produce to prove compliance? |
| Anti-pattern table | What rationalizations will agents use to skip OR game this rule? |
| Gaming resistance | How do you prevent token compliance — output that satisfies the rule's shape without genuine engagement? |

## Enforcement Types

Four mechanisms, ranked by effectiveness:

| Type | How it works | Example | Strength |
|------|-------------|---------|----------|
| **Structured output gate** | Agent must produce a specific artifact before proceeding | Table with three required elements before agreement | Strongest — creates visible, evaluable output |
| **Sequencing gate** | Action X must happen before action Y | "Scan skills before any tool call" | Strong — binary pass/fail |
| **Tripwire** | Pattern in agent's own output triggers immediate rewrite | "If output opens with praise, rewrite without it" | Medium — depends on self-detection |
| **Pre-flight check** | Verify condition before proceeding | "Count output lines; if > 6, cut" | Medium — quantifiable but skippable |

Prefer structured output gates for behavioral rules. Sequencing gates for procedural rules. Tripwires for pattern-based rules. Pre-flight checks for quantitative rules.

Not every rule needs every mechanism. Choose the one that fits the behavior being enforced.

## Agent-User Interaction Rules

Rules that govern how agents interact with users are vulnerable to sycophancy — the agent satisfying the rule's shape while accommodating the user. When building a rule that governs agent-user interaction, apply these checks:

| Check | Action | When to apply |
|-------|--------|---------------|
| Does the rule tell users what the agent should BE? | Rewrite as what the agent must DO — a specific output or procedure | Every agent-user rule |
| Can the user's input trigger accommodation? | Add a question-reframing mechanism: agent internally converts user statements to questions before evaluating | Rules where agents evaluate user proposals, decisions, or premises |
| Can the user override the rule by pushing back? | Add position stability: agent maintains position unless user provides NEW evidence | Rules where agents make assessments the user might disagree with |
| Does the agent load user context (profiles, preferences)? | Add explicit compensation: "loaded context increases accommodation — apply stranger-level scrutiny" | Rules in systems that load user profiles or preferences |
| Can the agent satisfy the rule with formulaic praise + compliance? | Add banned opener patterns: no "Great idea", no "You're right", no positive adjectives before analysis | Rules where agents evaluate or respond to user input |

## Anti-Gaming Design

Anti-pattern tables traditionally list rationalizations for SKIPPING a rule. Agents also GAME rules — producing output that satisfies the rule's structure without genuine engagement. Design against both:

| Failure mode | How to detect | Prevention |
|-------------|---------------|------------|
| Skipping | Agent proceeds without triggering the rule | Explicit scope boundary with mandatory language |
| Token compliance | Required output is generic, not specific to the situation | Require outputs to reference specific details from the current context |
| Escape hatch abuse | Valid exit ("no issues found") used on every turn | Track frequency — if the exit fires more than the enforcement, the rule is being gamed |
| Formulaic output | Same table entries or phrases appear across unrelated tasks | Required outputs must name the specific proposal, decision, or artifact being evaluated |

## Rule Sizing

| Guideline | Detail |
|-----------|--------|
| Lines | 40-80 recommended, 120 max |
| Sections | 3-5 focused sections |
| Single concern | One rule, one behavioral change. Exception: foundational rules (e.g., reasoning discipline) may bundle related concerns under a unified framing when the concerns reinforce each other and splitting would weaken the signal. |
| Tables over prose | Every instruction that can be a table row MUST be a table row |
