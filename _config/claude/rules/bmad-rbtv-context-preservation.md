---
description: Context preservation — detects rich session context and captures it to the right destination before it is lost
---
# Context Preservation

Detects when a session contains context worth preserving and guides the agent through a structured capture process.

## Detection Signals

| # | Signal | What to look for |
|---|--------|-----------------|
| 1 | Reasoned choices | User explains WHY they chose something, corrects the agent with background context, or overrides a default with rationale. The key indicator is reasoning — not just a preference stated, but a preference *justified*. |
| 2 | Unwritten knowledge | User provides facts, constraints, rules, conventions, or limitations that are not present in any loaded file. If you couldn't have known it without the user telling you, it's unwritten knowledge. |
| 3 | Structured information | User provides relational or organized data: lists, hierarchies, mappings, schedules, entity relationships, org charts, system dependencies. The structure itself carries meaning that would be lost in plain prose. |
| 4 | Process or workflow | User describes how something is done — sequences, routines, operational procedures, decision trees, approval chains. Distinguished from a one-off instruction by being *repeatable*. |
| 5 | Historical context | User provides past events, prior decisions, or circumstances that inform the current session. The context predates this conversation and wouldn't exist in any current document. |

**Trigger threshold:** 2+ signals across one or more turns.

## Non-Triggers

This rule does NOT activate for:

- Single-turn tasks (one prompt, one output, no rich context)
- Simple file edits or quick questions
- Sessions where the user provides only task instructions without surrounding context

## Detect → Discover → Confirm → Capture

When the trigger threshold is met, execute these four steps in exact order.

### 1. Detect

Recognize that 2+ signals are present. Do not announce detection to the user yet — proceed to Discover first.

### 2. Discover

Identify where this context belongs:

| Check | How |
|-------|-----|
| Active plan with shape.md? | Check if the session is executing a plan — shape.md is the target |
| Target system has its own conventions? | Read CLAUDE.md, memory system, or docs folder conventions for the target project/module |
| No conventions found? | shape.md fallback using universal template |

Map each piece of context to its destination. A single session may write to multiple targets (e.g., a decision to shape.md AND a tool workaround to memory).

### 3. Confirm

Present the capture proposal to the user:

- What context was detected (brief summary — not a restatement of what they said)
- Where it will be written
- Format (append to existing file, create new file, etc.)

Wait for user approval, redirection, or decline. NEVER write without confirmation.

### 4. Capture

Write to the confirmed destination(s). Follow destination-specific conventions:

| Destination | Convention |
|-------------|-----------|
| Plan shape.md | Append to Decisions and Discoveries section; follow append-only rules |
| Memory system | Follow memory system entry format (`date \| what \| why`) |
| Project docs | Follow project documentation conventions |
| New shape.md (fallback) | Use universal template at `_bmad/rbtv/workflows/_shared/templates/shape-template.md` |

## Living Document Principle

Context preservation is continuous, not a one-time action.

| Behavior | Required |
|----------|----------|
| First write | Same turn as user confirms |
| New context provided in later turn | Write IMMEDIATELY — same turn, not deferred |
| Decision made | Write IMMEDIATELY |
| Correction or nuance added | Write IMMEDIATELY |
| Direction change | Write IMMEDIATELY |
| Defer writes to session end | NEVER |
| Write once and stop monitoring | NEVER |

After the initial capture, continue monitoring for new signals. Every turn that adds context triggers an immediate write to the confirmed destination — no re-confirmation needed unless the destination changes.

## Freeform Session Fallback

When no plan or target-system conventions exist, create a shape.md using the universal template:

| Element | Convention |
|---------|-----------|
| Filename | `{YYYY-MM-DD}-{topic}-shape.md` |
| Location | Output folder for the session context, or project root if no output folder applies |
| Template | `_bmad/rbtv/workflows/_shared/templates/shape-template.md` |
| Plan-specific sections | Omit (Standards Applied, Tool Mode Selection) |

## Relationship to Memory System

Context preservation and the memory system are complementary:

| Content type | Destination |
|-------------|-------------|
| Session-specific decisions, scope, constraints, user inputs | Context preservation (shape.md or target docs) |
| Reusable cross-session knowledge, tool workarounds, self-corrections | Memory system (`.claude/memory/`) |
| Content that fits both | Write to both — one entry each, not duplicated content |
