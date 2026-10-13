# Reviewing

The result: a module, component or file that has the kind and place its work calls for and agrees with the framework's principles, with each claim about an agent's behaviour either measured or reported as not tested. The unit is existing rbtv source under review, or outside material being converted to rbtv: the two are one procedure, because both decide every kind and place from the work and then apply the same entries. Inputs: the unit the request names, the owner's reason, and any failure the owner reports. This page gives the order of the work; each step's method is on the page it links.

When no owner can answer, do steps 1 and 2, write the findings and the decisions step 3 would ask, and change nothing.

## 1. Read the unit as it is

Read every file of the unit and each of its records. Search the repository for the unit's identifiers, paths, skill names and tool names: a pack, the readme, help text and a test are callers too. List where the unit is installed with the commands [rbtv CLI](../glossary/rbtv-cli.md) gives, for the installation and for each agent: a file no installation selects reaches nobody. Outside material has no caller and no installation in rbtv: read all of it. Change nothing in this step.

## 2. Decide what the unit should be

Take the work the unit does, not the folders it has, through [Choosing what to build](choosing-what-to-build.md) and then [Choosing where to build](choosing-where-to-build.md). The answer may be the kind and place it already has; state that and continue. It may also be another: a module whose work is one subject is one component, several entry points for one purpose are one under [Nested exposure](nested-exposure.md), a page that computes an exact answer is a tool. A kind or place the request names is used as Choosing where to build states. In a conversion, classify each distinct part before choosing: the outside folder layout, record and names are not requirements.

Then compare each file with the entry of the kind chosen for it and with the framework's principles. Write one row per finding, in the form [Cognitive unit](../glossary/cognitive-unit.md) gives for a review: the location, what is wrong there and its consequence for the agent that reads it, the rule broken, the correction.

## 3. Ask the owner

Ask in one round, each decision with its options, their consequences and a recommendation:

- the kind and place chosen in step 2, with the alternatives considered;
- each removal and each rewrite the findings propose, with its evidence;
- the names of what will exist, as [Component](../glossary/component.md) and [Tool](../glossary/tool.md) state;
- which installations and agents get the result;
- whether to measure, as step 4 states.

Change only what the owner rules. A page that the measurement shows working is a finding to raise, not a page to rewrite. Ask again only when a measurement produces a decision that did not exist in this round.

Raise these two as options when the review observes their situation; do not apply them unasked:

- Agents reach a tool through its listing without opening the entry point that explains it: the tool can carry what the agent needs at that moment, as an option of the tool or in its result.
- A result's form must hold on every run: a program can check it, with the page's last step running that program, as [Deterministic first](../principles/deterministic-first.md) states.

## 4. Measure, when the owner accepts

Measuring is optional and recommended. [Running blind seats](running-blind-seats.md) states what the user is told before a run and how the seats are run and read.

Measure the unit as it is before changing an entry point or a page whose effect on an agent is in question, with requests in the owner's words; step 6 runs the same requests again. When the owner reports a failure and the seats do not open the page that should prevent it, run a second set that is told to open the page: the two sets separate a page that is never read from a page that is read and not followed, and the correction goes where they point.

When the owner declines, continue, and state in the report for each changed entry point that its selection was not tested.

## 5. Build what was ruled

Build each part as its kind's entry states; for converted material, that entry says what is retained and what is dropped. Update every caller found in step 1 in the same change, and move standing rulings to the component's decisions file, as [Documenting a change](documenting-a-change.md) states.

## 6. Verify and deliver

Run the checks that rbtv CLI and the changed files oblige. When step 4 measured, run the same requests again, and again after any later change to an entry point's name or description: both are in the listing the agent chooses from. Install the result for each installation and agent the owner named, with the commands rbtv CLI gives, and confirm on each that the old names are gone and the new ones answer.

## 7. Report

State the kind and place chosen and why; what changed; each measurement, or that it was not run; what was not verified; and what the review found and did not do, for the owner's ruling.
