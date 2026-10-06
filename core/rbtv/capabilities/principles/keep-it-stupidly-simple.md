# Keep it stupidly simple

Keep it stupidly simple is the principle that a result carries every part a stated need requires, and no part that need does not require. It applies even when another result would be shorter, and even when another result would be ready for a need that nobody has stated. Outside rbtv, a shorter result is often called simple, and YAGNI is a separate practice. Here the two are one principle, and YAGNI is stated outright: build nothing for a need that nobody has stated. Leaving a stated requirement out does not meet this principle.

A need is stated when a person or a task has asked for it. A need that might arrive later is met when someone states it. On this page, a part is a file, a folder, a field, an option or a step.

Giving a task one purpose, and a cognitive unit one purpose, belongs to this principle. Give each a purpose whose result can be judged on its own, even when a second purpose could be added to the same task or the same cognitive unit. An agent and a component each have one stated purpose. A second purpose that can be judged apart is not added to either. Capabilities that share a purpose, or that name the same documents, are exposed through one exposure method, even when each capability could have an exposure method of its own. The page "Nested exposure"² says when one exposure method is the wrong choice. One purpose, and one exposure method for a shared purpose or for the same documents, are this principle. They are not separate principles.

An author applies this principle before creating or keeping a file, a folder, a field, an option, a step, a cognitive unit, a task, an agent, a module or a component, and before splitting that work or exposing each piece. Apply it so that a reviewer can name the stated need each part serves, and can name no part built for a need that nobody has stated.

How a text of the scaffolding is worded is the page "Scaffolding language"¹.

## How it fails

The program can accept the files, and the work can still fail. It does not read whether a part was required.

- A part that a stated need requires is missing, because the result was shortened. The reader cannot do what the need asked.
- A field, an option, a setting, a step or a file exists for a need that nobody has stated. Every reading has to decide whether that part applies.
- One cognitive unit, one task, one agent or one component carries two purposes, and each result can be judged without the other. A check of one result also has to check the other.
- Each capability of one purpose, or of one set of documents, has its own exposure method. The agent or the human chooses among those methods before any work. That choice takes attention from the task.
- An old file, field or page remains beside the new one, so that nothing breaks before the change is finished. A reader can open either, and the two disagree.
- A new module, component or folder exists, and an existing one's stated purpose already covers the need. The only difference was the file type or the exposure method. The reader has two folders for one subject.

## How to apply it

1. **Name the stated need, and what fails without each part.** Before you add a part, write the need a person or the task has asked for, in one line. For each part, write what fails if that part is absent. When nothing fails, do not add the part. When something fails, the part stays, even when the result is longer. Fewer files is not the test. The test is whether a stated requirement or a decision is lost. Delete a file, a field, an option or a step whose removal loses no stated requirement and no decision. Do not apply this test to a sentence. How a sentence is worded is the page "Scaffolding language"¹.

   Weak: "Drop the step that sends the report. The need asked for the report, and without that step the file is shorter."

   Strong: "Keep the step that sends the report. The need asked for the report, and without that step the agent closes the task with the report unsent."

   The author who writes the weak line drops a step that the stated need requires, because the file is shorter.

2. **Build nothing for a need that nobody has stated.** A value that has only one use today is not an option, a setting or a field. Write that use into the part that has it. Do not add a second file, or a part that only a later need would use, because you are already editing. The later need gets its part when someone states it.

   Weak: "Write the one format the task asked for, inside the step that produces the file. Add a format option, because a later task may want a second format."

   Strong: "Write the one format the task asked for, inside the step that produces the file. Add no format option."

   The author who writes the weak line adds an option for a need that nobody has stated. Every later reading has to decide whether the option applies.

3. **Give the task, the cognitive unit, the agent and the component one purpose.** Split only when the pieces are independent and each result can be judged without the other. Do not split in order to reach a number of files, of steps or of tasks. A question answered by one read of a file, or by one run of a tool, stays one task. Do not split limits that serve one purpose into several files in order to have one limit in each file. When another task uses a result, give that result as a file or a record. The other task reads that file. It does not need the agent that produced the result. When you arrange tasks, run them at the same time only when they do not change the same file or record. When one uses the other's result, or both would change the same file or record, order them. A second purpose that can be judged apart is not added here. Which kind carries that purpose is the page "Choosing what to build"³.

   Weak: "The cognitive unit writes the summary. It also renews the certificate."

   Strong: "The cognitive unit writes the summary. It does not renew the certificate."

   The author who writes the weak line puts two results that can be judged apart into one cognitive unit. A check of the summary also has to check the certificate.

4. **Expose capabilities that share a purpose, or that name the same documents, through one exposure method.** Step 3 applies to the exposure method. It does not require one exposure method per capability. When the capabilities share a purpose, that purpose is the one purpose of the exposure method. Read the page "Nested exposure"² before you expose them, before you give each its own, and when they name the same documents without a shared purpose. That page says when a separate exposure method is required. Do not put two purposes that step 3 separates into one cognitive unit in order to have fewer exposure methods.

   Weak: "Expose the sources capability through one exposure method and the checks capability through another. Both name the same brief."

   Strong: "Expose the sources capability and the checks capability through one exposure method. Both name the same brief."

   The author who writes the weak line gives the agent or the human two exposure methods that name the same document.

5. **Do not create a module, a component or a folder when an existing one's stated purpose covers the need.** A different file type, or a different exposure method, is not a reason to create one. The same test bars a new file when an existing file's stated purpose covers the need. The page "Choosing where to build"⁴ is where you find the module, the component or the folder that already covers the need. This page only gives the test.

   Weak: "Create a component for the command. The existing component's stated purpose covers the need, and that component has no command yet."

   Strong: "Add the command to the existing component. That component's stated purpose covers the need, and it has no command yet."

   The author who writes the weak line creates a folder because the file type differs.

6. **When two principles both apply, choose the design with the fewest parts that still carries every stated requirement and every decision.** Do not add a part to satisfy a second principle when the fewer-parts design already satisfies it. Do not drop a stated requirement to reach fewer parts. When the question is which reading receives a text, decide it with the page "Progressive disclosure"⁵. This page does not decide that.

   Weak: "Add a second file. The one file carries the stated requirement, and the second principle does not require a second file."

   Strong: "Keep one file. It carries the stated requirement, and the second principle does not require a second file."

   The author who writes the weak line adds a part that no stated requirement and no second principle requires.

- When you edit: a part you are about to keep has to name its stated need again. A part is not kept because it is already there.
- When you convert an outside document: a part that the source has is not a stated need. It passes step 1 and step 2, or you drop it. Which kind carries a part that is another kind of thing in rbtv is the page "Choosing what to build"³.
- When you review: list each part and the need it serves, then list each exposure method whose capabilities name the same documents. A review that only checks that the program accepts the files misses every failure on this page.

Checks:

- A stated requirement that was present before the change is still present, unless a person withdrew it. No part serves a need that nobody has stated. A value with only one use today is not an option, a setting or a field. A cognitive unit, a task, an agent or a component does not carry two purposes whose results can be judged apart. Capabilities that share a purpose, or that name the same documents, have one exposure method, unless the page "Nested exposure"² requires more than one. The change does not leave the old file, field or page in place.
- Where the program accepts a file, acceptance shows that a record matched its schema. It does not show that each part was required, and it does not show that an unneeded part is absent.
- Take one design that drops a stated requirement and adds an option for a need that nobody has stated. The same design puts two purposes that can be judged apart into one cognitive unit, and it exposes two capabilities that name the same document through two exposure methods. Apply the steps. The requirement is present, and the option is absent. The two purposes are not in one cognitive unit. The two capabilities have one exposure method, unless the page "Nested exposure"² requires two.

## References

| # | Page | File | Read | When | To |
|---|---|---|---|---|---|
| 1 | Scaffolding language | [Scaffolding language](../glossary/scaffolding-language.md) | when | wording a text of the scaffolding | word the text, and do not restate that page |
| 2 | Nested exposure | [Nested exposure](../nested-exposure.md) | when | exposing several capabilities, or about to give each its own exposure method | decide whether one exposure method is right, and take which files an exposure method is |
| 3 | Choosing what to build | [Choosing what to build](../choosing-what-to-build.md) | when | a second purpose has to be carried, or a converted part is another kind of thing in rbtv | decide the kind, and do not choose it on this page |
| 4 | Choosing where to build | [Choosing where to build](../choosing-where-to-build.md) | when | about to create a module, a component or a folder, or about to place a file | find the module, the component or the folder that already covers the need. This page only bars a new one when a stated purpose already covers the need |
| 5 | Progressive disclosure | [Progressive disclosure](progressive-disclosure.md) | when | the question is which reading receives a text | decide the reading. Fewer files is not that decision |
