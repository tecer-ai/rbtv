# Writing a glossary entry

Write one page that defines a term and teaches an agent how to build or use what it names. The entry belongs in the glossary of the component that owns the term. It must work with the framework's required reading and the additional pages it names.

An entry is successful when an agent can use it to produce the intended result. Headings and installer acceptance alone do not establish that. Follow [Scaffolding language](glossary/scaffolding-language.md) for wording, reasons and examples; follow the framework's principles without repeating them in every entry.

## Establish the requirements

Read the existing entry, related guidance, relevant software and the user's decisions. Resolve disagreement about the intended behavior with the user before writing. Verify software claims in source, help or observed runs; name any unverified claim instead of presenting it as settled. If that uncertainty determines what the builder must write, stop the dependent work and report it. Keep the unresolved claim in the work record, not as a qualified instruction in the entry.

Find the mistakes the entry must prevent in existing instances, earlier warnings and public primary guidance. For an installable kind, also give a fresh agent a short task without the entry and inspect what it builds. Supply everything needed for the task without revealing the expected answer.

Keep a work record of each relevant mistake, the decision that caused it, its consequence and the evidence. Group mistakes with the same cause. Identify at least one distinction from the nearest kinds; if there is none, investigate whether the term needs a separate entry. Do not copy this research sequence into the instructions for the builder.

For each authoring decision, record the fact that requires it and the result that fails when it is made incorrectly. Preserve this record for review. It is not another section of the entry.

## Give shared instructions one owner

Compare the entry with its containing concept, its parts and the nearest related entries.

- A part never built, edited or reviewed independently belongs in its containing entry. Teach that part where the builder writes it; do not create a separate term for each heading.
- A part built independently has its own entry. Its containing entry says where it belongs, what must agree between them, and when to read its instructions. It does not reteach them.
- Instructions shared by skills, rules, commands and prompts belong in [Cognitive unit](glossary/cognitive-unit.md). An entry of one kind adds only the requirements that differ for that kind.
- Description and routing-table structure belongs in [Routing table](glossary/routing-table.md). Each kind explains only what the fields mean for its particular use.
- Each entry defines its own term. Follow [Single source of truth](principles/single-source-of-truth.md) for a fact owned elsewhere.

The owning entry is the one that must change when the fact changes. If an entry has almost nothing of its own after shared material is removed, report the overlap to the user before merging or removing the term.

## Write the entry

Present the definition and purpose first, then the decisions in the order the author makes them, and the observations used to verify the result. The table names the information to cover, not mandatory heading text. Combine related material and omit a separate section when its information already appears beside the instruction that needs it:

| Section | Content | Include when |
|---|---|---|
| Title and introduction | Definition, purpose and when to use it | Always |
| How it fails | Distinct mistakes and consequences | A distinct failure needs explanation beyond the instructions beside it |
| What it is composed of | Parts the author decides about and their locations | Such parts exist |
| How to build it | Decisions and actions in the builder's order | An author creates or changes it |
| How to work with it / How to apply it | Operations on software-written content / use of a standard | These fit the subject instead of building it |
| Checks | How to inspect and test the result | The term names something built or used |
| Template | Minimal layout of the output, with decision placeholders | The author writes one file with a fixed layout |
| References | Additional readings and their conditions | The entry needs them |

These sections organize distinct information; they are not prompts to say the same thing repeatedly. Put a condition, explanation or example beside the decision it informs. Checks name the observation that demonstrates success rather than copying the writing instructions. A vocabulary-only entry needs a definition and enough contrast to distinguish it from the nearest terms, not a build procedure. Use examples only under the language page’s conditions.

Define the term in a first sentence understandable on its own. Explain differences from outside usage only where importing that usage would produce an incorrect result. State the purpose directly. Do not finish the introduction with another sentence restating that purpose as an order.

Begin the method with the decision the builder actually faces. Establish the required result and the failure it prevents, but do not require every entry to repeat an abstract “failure, cause, situation, purpose” exercise. If a shared page already settles that decision, start with what this kind adds.

Write steps from the facts that distinguish this kind. A skill's description is read before its body; a command's inputs arrive with a human invocation. Those facts produce different authoring instructions even though both files contain instructions. Keep inputs, missing-input behavior, limits, exceptions and necessary reasoning explicit.

Do not teach the builder how you researched the entry. Do not repeat general writing advice with the term substituted. When an instruction is identical for related kinds, put it in their shared page and ensure the reader reaches it.

Use examples as Scaffolding language specifies. Do not add whole instances as templates to copy. A template describes the layout and each required decision; a schema used by software remains a separate file and is the authority for checked fields.

Keep facts about what software exposes to an agent when they determine an authoring choice. Put invocation syntax, flags, enforced naming rules and refusal messages in [rbtv CLI](glossary/rbtv-cli.md) or the relevant record's entry. Link those instructions instead of duplicating them.

Give editing, conversion or review a separate instruction only for requirements specific to that mode. For conversion, record whether each source requirement was kept, moved or dropped and why. Preserve actions, conditions, inputs, outputs, limits and exceptions. A source heading, repeated reason or illustrative story is not by itself a requirement. Retain an explanation or example only under Scaffolding language’s conditions; record removed text without pretending its removal deletes the behavior it illustrated. Use [Choosing what to build](choosing-what-to-build.md) for content that belongs to a different kind.

Use direct links at the point of reading or a conditional references table, not both for the same instruction. Resolve links from the entry's final location. Required readings come before the work that needs them; optional readings have a condition the agent can recognize before opening them.

## Review and test

Review the entry with the related pages the same task reads. Check that every recorded requirement has a home and is reachable, that no two pages give different answers, and that shared instructions are not repeated. Shared terms and short phrases are not duplication; duplicated guidance is.

Follow every link and verify software facts against their sources. Report an inconsistency outside the authorized change. Correct in-scope contradictions together rather than leaving two designs active.

Use fresh test agents with the entry, its required prior reading, conditional pages available through their routes, and a realistic task. Keep the answer and authoring work record out of their inputs. Follow [Delegating work](../../../meta/sub-agents/capabilities/methods/delegating-work.md) to launch them and verify their reports.

| Kind | Test tasks |
|---|---|
| An author-written kind that rbtv installs | Create, convert and review, twice each; the conversion includes a part that needs a different home; the review includes two known defects accepted by the installer |
| A record or a cognitive unit with sections | One create task |
| A folder | Place three files |
| A file maintained by software | Change what it shows through the supported operation |
| A shared concept such as cognitive unit | Build with the entry of one concrete kind |
| A standard | Correct a text that violates it |
| A principle | Correct a design that violates it in two ways |
| A capability | Follow two routes to complete its work |
| A vocabulary-only term | Sort ten sentences: five correct uses and five nearest-term confusions |

A run counts only when its inputs were complete and the expected answer was inaccessible. Check both software acceptance, where applicable, and the actual result against the recorded failures. A review must find the seeded defects. A copied example is not evidence that the agent learned to apply the guidance to a new task.

Investigate a failed valid run before changing the entry: identify the missing, incorrect or unread instruction. Repair an evidenced defect and rerun that task with a fresh agent. Stop and report the results if the same task fails twice after repairs. Preserve the test evidence.

For an edit, repeat link checks and the tests affected by the changed requirements. Describe current behavior in the entry; keep decisions and change history in their designated records.
