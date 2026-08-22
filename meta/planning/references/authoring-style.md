---
description: Read at the moment of writing or amending any authored surface — prompt, task, reference, capability body, or seat definition — for the prose law all of them obey.
tags: [planning]
---

# Authoring style — the prose law

Every file authored here is carried by an occupant on every step of its work, and read by a teammate with zero memory of the session that wrote it. These rules are what make that carriage affordable and that reading unambiguous.

## Every sentence MUST be necessary

A sentence whose deletion loses no requirement and no judgment call MUST be deleted. Preamble, a restatement of the line above it, and a summary of what follows all fail that test.

## Mandatory language

Every requirement MUST read **MUST**, **NEVER**, or **ALWAYS**.

"should", "consider", "check", "may want to", "try to", and "it is recommended" are NEVER used for a requirement — each reads as optional to a literal-minded occupant, and an optional requirement is not a requirement.

A genuine judgment call or hint MUST be marked as one ("judgment call:", "hint:", "prefer X where Y"). Unmarked hints are what drain the mandatory words of force: an occupant that finds one MUST it may safely ignore stops trusting the rest.

## References are micro

Every reference carries exactly ONE subject, and the number of references is unlimited. The full law — the one-subject rule, the split test, the merge test — is `kind-reference.md` (sibling). Apply it there; none of it is repeated here.

## No hardcoded owner value

A channel id, path, account, host, or credential is RUN-TIME CONFIGURATION, living under `.rbtv/config/modules/<module>/<component>/` and read at run time. NEVER type one into a prompt, a task, a manifest, a reference, or a seat definition. `workflow-authoring-checklist.md` §5 states this as a wall a produced seat meets; here it binds every authored file, produced or not.

## Write for a zero-memory, literal-minded reader

The reader holds this file and nothing else — no memory, and no willingness to infer. Every instruction MUST be executable from its own text. NEVER write a citation the reader has to chase before it can act: write the rule itself, never "per <record-id>".

## The self-check

Re-read the finished file as its occupant, holding only this file, and name every sentence deletable without losing a requirement or a judgment call. Each one you name is deleted before the file ships.
