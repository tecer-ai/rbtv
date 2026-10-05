# Building a workflow

A [workflow](../../../core/rbtv/capabilities/glossary/workflow.md) is a set of tasks arranged as a DAG and run by sub-agents.

## Purpose

It lets independent work run at the same time and dependent work wait for exactly what it needs. Without it, the coordinating agent reorders the work in its head each time, and tasks that could run together run one after another. Which kind of unit to build is in [Choosing what to build](<../../../core/rbtv/capabilities/_under-evaluation/guides/procedure documents/choosing-what-to-build.md>).

## What good looks like

- Each task has one purpose whose result can be judged on its own ([Micro agency](../../../core/rbtv/capabilities/principles/micro-agency.md)).
- Each row names every agent whose result its task uses, and no chain of needs loops back.
- Two tasks that change the same file or record never run at the same time: one needs the other ([Micro agency](../../../core/rbtv/capabilities/principles/micro-agency.md)).
- Every agent whose needs are done is launched; none waits for a reason the file does not state.
- Each task's result is a file or record the next task reads without the agent that produced it ([Micro agency](../../../core/rbtv/capabilities/principles/micro-agency.md)).

## Making it good

Split the work into tasks with one purpose each. For each task, list the tasks whose results it reads, then add an order between any two tasks that change the same file. Launch every task whose needs are done, and update its status when it starts and when it finishes.
