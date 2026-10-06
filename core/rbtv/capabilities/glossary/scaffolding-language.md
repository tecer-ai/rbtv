# Scaffolding language

Scaffolding language is the writing standard for instructions and reference material an agent reads. Use literal, natural language so the reader understands what to do on the first reading.

This includes prompts, skills, rules, commands, folder instructions, folder artifacts and capabilities. Preserve the facts, requirements and reasoning needed for the work. Length alone does not establish quality.

## Write the action directly

Name the actor, action and object. State a condition before the action it controls. Use a list for independent items and prose when one sentence explains the next.

For example: “Use a skill when an agent needs instructions for a particular kind of task but does not need them on every task.” State the instruction directly. Do not describe what an author would want or soften a requirement with “should ideally”; the reader can treat either as optional.

Use ordinary words in their ordinary senses. Use glossary terms for the concepts they define, without inventing synonyms or shortening the terms. A pronoun is suitable when its referent is unambiguous. Do not repeat the full subject just to make every sentence stand alone.

Replace a metaphor with the literal action. Established expressions such as “a link points to a page” need no rewriting. Split a sentence when a reader must resolve several nested clauses to find its action; do not replace connected prose with fragments.

## State requirements that can be applied

Write the action or result instead of an appeal for care. For example, “Name every changed file” states a requirement; “make the report thorough” leaves the requirement undefined.

Do not turn a subjective preference into an invented numerical threshold. For decisions, use the defaults and conditions required by [Keep it stupidly simple](../principles/keep-it-stupidly-simple.md). State the evidence that determines a choice and what happens when the evidence is missing.

Verify statements about software in its source, help or an observed run. Qualify platform-specific behavior and retain explicit uncertainty where it has not been verified.

## Keep explanations and examples for specific needs

Start with the instruction and its conditions. Do not append a reason that repeats them. Retain an explanation when it supplies a fact needed to apply the instruction outside the named example, or addresses an identified mistake in existing work or tests. Put the explanation beside the instruction that uses it, once.

Do not add examples by default. Show one minimal correct example when an exact output format must be learned. Use a contrasting pair to demonstrate a specific mistake identified in existing work or tests. Explain a consequence only when the contrast does not show it. Do not add a pair merely because a section exists, and do not shorten a correct example until it loses a requirement.

For example:

> List a decision only when the note records it as settled. Record an unresolved choice as an open question.

This states the criterion and both actions. It needs no additional sentence saying that unsettled choices are not settled decisions.

## Remove repetition without removing requirements

Keep a fact or instruction in one place. Follow [Single source of truth](../principles/single-source-of-truth.md) when another page owns it. An entry may rely on the framework's required prior reading; it must still route to any additional guidance needed for its task.

Delete repeated restatements, commentary about how the document is organized, and explanations that add no condition, fact or consequence. Preserve the purpose, required inputs, limits, exceptions and actions on missing information. Moving an instruction to its owner is not deleting the requirement: the reader must still reach it before acting.

Use direct Markdown links for references. A reference used in an instruction says when to read the target and what to take from it. Use a table when several conditional readings must be compared. Do not repeat a routing instruction in prose and in a table.

Words such as “clear” or “appropriate” are not banned. They cannot substitute for an action or criterion. Review their meaning in context rather than passing a document because a word search found nothing.

## Review

Read the instructions in the order their user encounters them, including required prior pages. Check for an unclear actor, ambiguous condition, missing action, duplicated requirement or unsupported claim. Ask a reader unfamiliar with the draft what it would do; correct any difference from the intended action. A shorter draft fails if it makes that reader reconstruct a requirement that was explicit before.
