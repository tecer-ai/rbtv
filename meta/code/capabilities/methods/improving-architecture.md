# Improving architecture

The result: the user holds a ranked, visual set of deepening candidates for one codebase (refactors that turn shallow modules into deep ones) and has worked one of them through to a decided shape. On request, the user has also compared alternative interfaces for it. Each new term and each load-bearing rejection is recorded in the codebase's own design sources, on the user's confirmation.

Inputs: the codebase to review, as a path or a name the conversation resolves (a nested repository, a tool, a component's code); optionally a direction (a module, a subsystem, a pain point); the user's picks during the grill. When the codebase is not named, ask the user which one and do not scan until it is named. When no user can answer the questions of steps 5 and 6, follow [When no user can answer](#when-no-user-can-answer).

This method reports and grills. It never edits code in the codebase under review.

## The vocabulary

Use these words exactly, in every sentence of the report and the grill.

| Word | Meaning |
|---|---|
| Module | Anything with an interface and an implementation, at any scale: a function, a class, a package, a slice across tiers. |
| Interface | Everything a caller must know to use the module correctly: signature, invariants, ordering, error modes, required configuration, performance shape. |
| Implementation | What is inside the module. Say "adapter" when the seam is the topic and "implementation" otherwise. |
| Depth | Leverage at the interface: how much behaviour a caller or a test exercises per unit of interface learned. A deep module has much behaviour behind a small interface; a shallow module has an interface nearly as complex as its implementation. Depth is a property of the interface: a deep module may be composed inside of small swappable parts that are not part of its interface. Never measure depth as implementation lines over interface lines; that measure rewards padding. |
| Seam | The place where behaviour can be altered without editing in that place; the location of a module's interface. Where the seam goes is a decision separate from what sits behind it. |
| Adapter | A concrete thing that satisfies an interface at a seam. The word names the role, not the size: a Postgres repository is a small adapter with a large implementation; an in-memory fake is a large adapter with a small implementation. |
| Leverage | What callers get from depth: one implementation pays back across N call sites and M tests. |
| Locality | What maintainers get from depth: change, bugs, knowledge and verification concentrate in one place. |

Never substitute another word for one of these: not "component", "service" or "unit" for module; not "API" or "signature" for interface; not "boundary" for seam; not "layer" or "wrapper" for module.

The principles:

- **The deletion test.** Delete the module in your head. When the complexity vanishes, the module only passed calls through. When the complexity reappears across N callers, the module is needed.
- **The interface is the test surface.** Callers and tests cross the same seam. Wanting to test past the interface means the module has the wrong shape.
- **One adapter is a hypothetical seam; two adapters are a real one.** Never introduce a seam nothing varies across.
- **Accept dependencies, never create them. Return results, never produce side effects.** Fewer methods and parameters mean fewer tests.

## 1. Scope

When the user named a direction, take it and infer nothing. Otherwise read a long stretch of the commit history (`git log --oneline`) for the hot spots, the files and areas that recur, and scan those first: deepening pays where change is frequent. When the changes are scattered and show no hot spot, widen the scan.

## 2. Read the codebase's design sources

Read these before exploring:

- For an rbtv component: its capability pages, any `decisions.md` on its path, and the root `CLAUDE.md`.
- For any other repository: its root agent guidance file (`CLAUDE.md` or `AGENTS.md`), its readme, and its decision-record folder (`docs/adr/` or the equivalent) when one exists.

Take domain names from these sources: write "the intake module" as the sources name it, never a class name. Never re-litigate a decision these sources record.

## 3. Explore through one sub-agent

Run `cast route` for an exploration task and launch one sub-agent through `cast` with the model its verdict names first. Give the sub-agent the scope of step 1 and the friction list below. It returns a list of friction points with file paths, and never a design.

The friction to hunt:

- one concept understood only by moving between many small modules;
- shallow modules;
- pure functions extracted for testability while the real bugs are in how they are called, which leaves no locality;
- tightly coupled modules that leak across their seams;
- parts untested, or hard to test through their current interface.

Apply the deletion test to every suspected shallow module. "Deleting it concentrates complexity" is the signal of a candidate.

## 4. Classify each candidate's dependencies

The class decides how the deepened module is tested across its seam.

| Class | Dependency | How the deepened module is tested |
|---|---|---|
| in-process | Pure computation, in-memory state | Merge, and test through the new interface; no adapter |
| local-substitutable | A local stand-in exists, such as an embedded database or an in-memory filesystem | Test with the stand-in; the seam stays internal |
| remote but owned | Your own service across a network | A port at the seam, an in-memory adapter for tests, a transport adapter for production |
| true external | A third-party service | An injected port, a mock adapter in tests |

The tests replace, they do not add a level: tests at the deepened interface replace the old tests on the shallow parts, assert observable outcomes and survive internal refactors.

## 5. Render the report and ask

Write the candidates as one self-contained HTML file named `architecture-review-<timestamp>.html` in the OS temp folder: `$TMPDIR`, else `/tmp`; `%TEMP%` on Windows. Never write the report inside the repository. Follow [Architecture report format](improving-architecture/report-format.md) for the scaffold, the card, the diagrams, the style and the tone.

The report holds one card per candidate: the files, the problem, the solution, the wins in terms of leverage, locality and tests, a before-and-after diagram, the recommendation strength (`Strong`, `Worth exploring` or `Speculative`), the dependency class, and a decision-conflict callout only where the friction is real enough to reopen a recorded decision. It closes with one top recommendation and the reason for it.

Open the file for the user with the platform's open command (`xdg-open`, `open` or `start`) and state its absolute path. Then ask: "Which of these would you like to explore?" Propose no interface before the answer.

## 6. Grill the picked candidate

Follow [Interview](../../../reason/capabilities/methods/interview.md) for the questioning: its rounds, its question count and its standard of challenge. Walk these decisions with the user, in order: the constraints; the dependencies and their class; the shape of the deepened module; what sits behind the seam; which tests survive.

Two side effects happen as decisions settle, each only on the user's confirmation in the same turn:

- When the deepened module is named after a concept the design sources lack, record the term in the codebase's own design source: the component's capability pages, or the repository's glossary.
- When a candidate is rejected for a load-bearing reason a later reviewer would need, offer to record it as a decision: in `decisions.md` for an rbtv component, in the repository's decision-record folder otherwise. Never offer this for an ephemeral reason ("not now") or a self-evident one.

Never write to a design source without that confirmation.

## When no user can answer

When the question of step 5 stays unanswered because no user is available, do not wait. Leave the question open for the user, and proceed with the report's top recommendation as the picked candidate. Walk the decisions of step 6 against the codebase's design sources and the sub-agent's evidence in place of the user's answers. Write nothing into any design source. Mark the result as derived and unratified: record in the report the derivation, what each part of it rests on, and each unresolved question. The open question and the derivation both wait for the user.

## Design it twice, on request only

When the user asks for alternative interfaces for the picked candidate:

1. Write the problem space for the user: the constraints, the dependencies and their class, and an illustrative sketch that is not a proposal.
2. Convene a panel as [Panel](../../../coordinate/capabilities/methods/panel.md) states, of three or more sub-agents in parallel, each launched through `cast` with the model `cast route` names, each under a radically different brief:
   - minimize the interface: one to three entry points, maximum leverage each;
   - maximize flexibility;
   - optimize the most common caller;
   - ports and adapters, where dependencies cross the seam.
3. Each sub-agent returns: the interface (signature, invariants, ordering, error modes); a usage example; what the implementation hides; the dependency strategy and the adapters; the trade-offs.
4. Present the designs one at a time. Compare them by depth, locality and seam placement. Recommend one, or a hybrid, with the reason; never present the designs as a list for the user to choose from unaided.

## Origin

This page is a fork of an outside skill (`mattpocock/skills`, `improve-codebase-architecture` with the vocabulary of `codebase-design`), adapted to rbtv. Never re-sync it from that origin.
