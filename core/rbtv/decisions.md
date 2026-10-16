# rbtv decisions

Standing decisions about the rbtv component. Each states the decision and its reason; the framework skill, the glossary, the principles and the pages of `capabilities/methods/` describe the resulting design.

## A description quotes the phrases a task carries and may name one first action

ALWAYS LOAD WHEN quotes literal phrases a request for the work carries, beside the situations, and may hold one sentence naming the first action the reader takes in place of its habitual first action. Reason: owner decision, 2026-10-09, on measured selection. Three descriptions of the `coding` skill written as situations only made a headless seat on the weakest model open the skill about one time in two on "crashes with ValueError … Fix it" and "Add a function by_id …"; the description that quotes the phrases ("add a function", "fix it", "it crashes") and says "open it as the first step, before reading the file to edit" was opened by 24 of 24 seats and by 0 of 10 on the explain-only neighbour. The `thinking-partner` and `final-act` descriptions had been written that way under the same pressure before the standard said so.

## Selection is verified as a rate over ten seats per task

A skill's description is tested with ten headless seats of the weakest selected model on a task that should select it and ten on the nearest task that should not, and passes on all and none. Reason: owner decision, 2026-10-09. One seat per task cannot show the rate: on the `coding` build one seat per wording read a one-in-two rate as pass, then fail, then pass, and the miss was called the model's variance until ten seats per prompt showed the wording was the cause.

## The seats are run from a method page, not a tool

Running blind seats is a method page, and each build writes its runner from it. Reason: owner decision, 2026-10-09. The runner is about forty lines an agent writes from the recipe; a shipped tool would need the command-line method, selftests on both systems and a row in every agent's tools rule to save that. The part that recurs is the knowledge (the launch form, the stop by the handle's process id, the shape of a Claude Code transcript), and the page holds it. Should the runner keep being rewritten, a `cast` verb is the home for a program, since launching and reading sessions is cast's subject.

## An agent folder holds an empty `.git` folder

The installer creates an empty folder named `.git` in every agent folder, on add and on update, with no flag, never writes into it and never removes it. Reason: owner decision, 2026-10-11. An rbtv agent must receive from its harness only what its own folder holds, and a harness that looks for a project root stops at this folder. It is an empty folder, not a file and not a repository, because git then still reads the agent folder as part of the repository around it. git cannot carry it, so each machine creates it by running add or update for each agent. [Agent](capabilities/glossary/agent.md) states what the folder is, and [rbtv CLI](capabilities/glossary/rbtv-cli.md) the operations that create it.

## A tool owned by one agent lives in that agent's folder, off PATH

An agent may own tools. Such a tool sits in `capabilities/tools/<tool>/` of the agent's folder, laid out as in a component; it is not installed, not on PATH and not in the `rbtv-tools` rule, and the agent's prompt names its invocation. What it keeps between runs, such as a check's record of the items it already reported, stays in the agent's folder. PATH holds the tools of rbtv's components. An agent-owned tool goes into rbtv only when the owner says so. Reason: owner decision, 2026-10-11. Each agent is free to have and build its own tools, and rbtv keeps only what is generic. [Tool](capabilities/glossary/tool.md) states the convention, and [rbtv CLI](capabilities/glossary/rbtv-cli.md) what the installer does with such a tool.

## A dependency entry states its install command and what is looked up

Each entry of a component record's `dependencies` is an object with `name` and `install`, and `command` or `python_package` when a lookup can find it. rbtv prints the install command and never runs it. A Python package's command is `python -m pip install <package>`. Reason: owner decision, 2026-10-13. A bare name did not say which package to install, and `rbtv doctor` looked up that one name both as a command and as a Python package: it reported `defuddle-cli` absent on a machine where its command `defuddle` was installed, and gave one answer for `playwright`, which is an npm program in one component and a Python package in another. [Component record](capabilities/glossary/component-json.md) states the fields.

## Review and conversion are one procedure

A review of existing source and a conversion of outside material both follow the Reviewing method: read the unit, decide its kind and place from its work through Choosing what to build and Choosing where to build, ask the owner, then build. Reason: owner decision, 2026-10-13, after a module that passed the installer was reviewed end to end and became one component of another module: every choice made in that review is the choice a conversion makes, and both apply the same entries.

## A run of seats is optional, recommended and announced

Before a run of blind seats the user is told the harness and model, the count of tasks and seats, and that the seats run at the same time; the run starts on the user's yes. A declined run waives the seat test of a changed description, and the report says the selection was not tested. Reason: owner decision, 2026-10-13: the user decides the spend knowing its size, and an untested change is never read as a verified one.

## A review proposes, and the owner rules

A review lists each removal and rewrite with its evidence and changes only what the owner rules; putting a capability in a tool that agents reach without its entry point, and checking a fixed format with a program, are options it raises. Reason: owner decision, 2026-10-13: each of the two was ruled for one case, and a page that measurably works is not rewritten on a reviewer's judgment.

## Names of shipped components and tools

A component shipped in the repository is named with a short verb, or with the name of the one product it wraps; a shipped tool is named for what it acts on and what it does, with no suffix that only says it is a program. Mirror components and agent-owned tools are named as their owner chooses. Reason: owner decisions, 2026-10-13 (`browse`, not `browsing`; `page-capture`, not `capture-cli`): these are rbtv's conventions for what it ships, kept in this component, while the general method for building a command-line interface stays in `meta/code`.

## A component's records for a reader live in `output/`

What a component produces for people to read and rule on is written in `.rbtv/output/<component>/` for the installation and in `output/<component>/` inside an agent folder for records about that agent alone; both are tracked, and an installation's instruction file may name another place for one method's output. Reason: owner decision, 2026-10-15, while placing the compound backlog of the `final-act` component. Config holds what the user chose, runtime holds what a component needs to run and is never tracked, memory has one writer and agents are agent folders; none of the five held a record awaiting the owner's ruling, so such records were landing in project folders that close. Per component, like config and runtime, because the component is what writes it; tracked because the owner reads it on more than one machine. The move of `runtime/` under the same root, as `_runtime/`, was deferred to its own change.

## An agent's name people see can differ from its internal name

`agent.json` may hold `external_name`, the name people see, such as the Slack sender name; the internal name stays the folder name everywhere else. Reason: owner decision, 2026-10-15. The main agent keeps the internal name `master` on every channel it is reached through, and is shown as the persona the owner gave it. Other agents take their persona's name as their name at creation.

## A component record names its port and operations

A component record may carry `type` (the port it is listed under), `serves` (other ports it covers), `provides` and `needs` (operations, written `<noun>.<verb>`); `type` is required only under `connectors/`, and the installer refuses a `needs` entry no component `provides`. A need is matched by operation, never by connector name, and `dependencies` keeps outside software only. Reason: owner decision, 2026-10-16, in the connector architecture design. The owner wants install-with-dependencies (installing Ignite brings Cast) and named Cast as the model abstraction: Cast is the port command for running an agent, so it provides `agent.run` and Ignite needs it. Types alone cannot say what a connector can do, so a need names an operation (`approval.secure`, which WhatsApp cannot deliver), and a connector lives in one place with `serves` for its other ports because a subtype would read as a specialization (calendar is not a kind of communication). The fields are optional because a required field is a flag day across every component record; `type` is required under `connectors/` because a connector is listed by its port. [Component record](capabilities/glossary/component-json.md) states the fields and [Port](capabilities/glossary/port.md) the vocabulary.

## The shape check of a connector is a tool

The third line of the shape check in [Building a connector](capabilities/methods/building-a-connector.md) is the tool `adapter-check`, which checks a connector's adapters from its record. Reason: review of the connector architecture's first phase, 2026-10-16. The check had been one line of `node -e` in the method, and that line tested only that the exported names existed, so an adapter Ignite's loader refuses passed it and an operation of another port passed too; the check must validate as the loader does and know which operations belong to which port, which is a program, and a method page carries no code. It is a tool and not a script written from the page, unlike the blind seats, because a connector's author runs it unchanged at a fixed step and a blind agent must pass it without writing anything. For a payments adapter it calls Ignite's own loader, so the check and Ignite can never disagree.
