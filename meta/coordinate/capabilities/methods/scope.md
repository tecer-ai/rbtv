# Building a scope

A [scope](../../../../core/rbtv/capabilities/glossary/task.md) is the boundary of one [task](../../../../core/rbtv/capabilities/glossary/task.md): what to examine, and what may change.

## Purpose

It keeps this task's boundary closed, so a reviewer can classify any action as in or out, and it gives the agent exactly the material its question needs. Without it, related work is treated as in, no action can be classified, and the agent either drowns in material or judges without it.

## The right size

A scope is one agent's when both hold:

1. **Enough to judge.** The agent holds the surrounding material its question needs: the file where the value is born and the caller that consumes it, the rule and the page that applies it, the record and the code that reads it. An agent handed one file and asked a question whose answer lives in the file next to it returns a confident wrong answer, and nothing in its report shows that.
2. **One page out.** The answer fits the task's output format in one page. A report that needs a section per sub-finding was several scopes.

Both sides fail. Too wide: the agent's context fills with material its question does not need, its answer loses precision, and its report runs past a page. Too narrow: the task withheld the context the judgment needed, and the coordinator pays twice, once for the wrong answer and once for the agent that finds it wrong. Narrow is the more common mistake on a strong model and the more costly one on a weak model, where a wide scope also degrades fast; model levels are `cast route -h`'s (SOTA, L1, L2, L3).

To find the size, split a problem into questions and merge until each question carries its own evidence:

- A PROBLEM (an issue entry, a bug, a feature, "why does X happen") is never one agent's scope. It decomposes into questions, and that decomposition is a wave ([Swarm](swarm.md)). "Why does the session list miss a turn" is a problem; its questions are where the session id is recorded, what the writer stores there, and how the reader filters it. Three agents, each with the files that question needs.
- A question whose answer waits on another question's answer is the next wave, pointed at what the first found. "Find where X happens, then check it" is two scopes.
- A question that one file read or one command answers is one agent, or the coordinator's own read. Never a wave.
- The task can list what to read. When you cannot name the files, the first wave's job is to name them.

## What good looks like

- A reviewer who has not seen the conversation classifies any candidate action as in or out. "Related files" fails.
- Examine and may-change are separate closed lists of named files, folders, or records.
- The examine list carries the material the question needs to be judged, and nothing the question does not need.
- No sentence is true of every task of this agent. Standing remit stays in the [role](../../../../core/rbtv/capabilities/glossary/prompt.md#role); standing limits stay in [constraints](../../../../core/rbtv/capabilities/glossary/prompt.md#constraints). ([Single source of truth](../../../../core/rbtv/capabilities/principles/single-source-of-truth.md))
- It bounds one purpose. Two results that can be judged apart are two tasks. ([Keep it stupidly simple](../../../../core/rbtv/capabilities/principles/keep-it-stupidly-simple.md))
- It states no completion check. That check is the [done contract](done-contract.md). ([Single source of truth](../../../../core/rbtv/capabilities/principles/single-source-of-truth.md))
- A sentence whose removal still leaves every action classifiable is absent. ([Keep it stupidly simple](../../../../core/rbtv/capabilities/principles/keep-it-stupidly-simple.md))

## Making it good

Name what to examine. Name what may change. Keep the two lists separate, and close both: only those names are in, and only the may-change names may change. Then read the examine list as the agent will: can the question be judged from these files alone? If not, add the file that is missing, or move the question to a later wave.

## Traps

- "Investigate this", with no names.
- "Add tests for foo.py" — a file name with no closed examine list and no closed may-change list.
- "Check whether the writer stores the id", with the writer named and the reader that defines what the id must be left out.
