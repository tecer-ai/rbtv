# Skill First

**MANDATORY. NO EXCEPTIONS.** When a skill exists whose description matches the task you are about to perform, you MUST invoke it. NEVER trust that you can do it yourself. NEVER skip a matching skill because the task "seems simple" or because you "already know how."

## Pre-Action Gate

Your FIRST tool call on any new task MUST be a skill-description scan. No Read, no Grep, no Glob, no Bash, no Agent, no Write, no Edit before the scan.

| Step | Requirement |
|------|-------------|
| 1. Scan | Read every skill description in your system reminders. Project skills first, then plugin skills. |
| 2. Match | If ANY skill's description fits the task — even partially — select it. Multiple matches = invoke each in priority order. |
| 3. Announce | Before any other tool call, output: `Using [skill-name] to [purpose].` This announcement is MANDATORY and must appear in your response text. |
| 4. Invoke | Call the `Skill` tool with the matched skill. Follow the skill's instructions exactly. |

If no skill matches, you MAY proceed with other tools. State briefly: `No matching skill — proceeding directly.`

## Red Flags — STOP and Invoke the Skill

If you catch ANY of these thoughts, you are rationalizing. Delete the thought and invoke the skill.

| Thought | Action |
|---------|--------|
| "I can just do this directly" | STOP. Scan skills. |
| "This is straightforward, no skill needed" | STOP. Scan skills. |
| "I know how to do this" | STOP. Scan skills. |
| "The skill would just slow me down" | STOP. Invoke the skill. |
| "Let me explore/research first, then use the skill" | STOP. The skill handles discovery. Invoke it now. |
| "I need context before I can use this skill" | STOP. The skill IS the context-gathering step. |
| "Let me just Read one file to check, then invoke the skill" | STOP. The Read is already a tool call. Invoke the skill first. |
| "This is a follow-up to what I just did, no need to re-scan" | STOP. Each new task = new scan. |

A matching skill is ALWAYS step zero — never step two. No pre-work before invoking it. The skill's own workflow defines what pre-work is needed.

Skills encode decisions, constraints, and workflows that you will miss by improvising. Your confidence in the task is irrelevant — the skill exists for a reason.

## Project-Native Skill Priority

Project skills (listed under "Project" in your skill context) are custom workflows built specifically for this workspace. Scan project skills FIRST and with extra attention. They encode the user's exact decisions and conventions — a partial match on a project skill MUST be invoked. Do not let project skills get buried under the volume of plugin skills.

## Scope

This gate fires on EVERY new task, including follow-ups that change direction. It does NOT fire for mechanical continuations of an already-invoked skill's workflow.
