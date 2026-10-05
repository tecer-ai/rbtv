"""The `-h` pages, one per command path: the approved help text of
the review screens (`1-projects/rbtv-agent-cli-unification/build/screens/review/`),
kept verbatim. Each page is named by its command path; `root` is the bare command.

The selftest checks that every option a command takes is named on its page.
"""
from __future__ import annotations

PAGES = {
    "root": """\
rbtv — help

Discover
  status        Show target, saved settings, and recorded selections.
  list [NAME]   Browse exact module, component, or unit scope.
  search WORDS  Search catalog names and descriptions broadly.
  show NAME     Show description, included units, and installation details.

Change this installation
  configure         Initialize or change receiving tools and guidance settings.
  add [NAME...]     Add named or filtered units, or turn a pack on.
  remove [NAME...]  Remove installed units, or turn a pack off.
  update SCOPE      Make the folder match the file. The scope is required.

Agents
  agent VERB    Act on one agent instead of this installation: create it, change its
                units, harness, model or effort, or list the agents. See: rbtv agent -h

Check and guided use
  doctor       Check generated files and selected command shortcuts.
  interactive  Choose units through a guided menu (asks questions).
  selftest     Run checks in isolated temporary installations.

Shared options: --target PATH  --json  -h, --help  --version
Non-interactive changes also accept --dry-run and --details.
Only interactive asks questions.
Target order: --target, then RBTV_AGENT_HOME, then discovery from the current folder.
Aliases: ls=list; li=list --installed; rm=remove.
A unit id is module/component#name. A pack is named only with --pack.
A bare name never resolves to a pack.
With no command, this page is printed.

Start: rbtv status
More:  rbtv COMMAND -h
Exit codes: 0 success; 1 refused or check failed; 2 invalid arguments.
""",
    "status": """\
rbtv — status help

usage: rbtv status [-h] [--target TARGET] [--json]

Show the selected installation or agent and its saved settings. The target is --target, then
  RBTV_AGENT_HOME, then discovery from the current folder. The result names the target and why it
  was selected. An agent result shows harness, model, effort, voice, packs and installed units.
  It does not show a Slack connection. A root result shows none of name, description, harness,
  model or effort. Both results name each agent installed as a harness-native sub-agent, with the
  model and the effort of every harness it is written for.

options:
  -h, --help            show this help message and exit
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "list": """\
rbtv — list help

usage: rbtv list [-h] [--module MODULE] [--component COMPONENT]
                  [--type TYPE] [--installed] [--limit LIMIT]
                  [--offset OFFSET] [--target TARGET] [--json]
                 
                  [NAME]

Browse the local source catalog. No NAME shows modules; a module shows its components; a component
  shows its units and any pack it declares; an exact unit name shows only that unit. A pack is
  named only with --pack. NAME never searches descriptions. Use search for broad discovery.
  Installed means recorded for this installation; use doctor to check the files. --installed shows
  installed units, and packs that are on. Under the table, an installed agent is named with the
  harnesses it is written for as a harness-native sub-agent, and the model and effort of each.

A unit id is module/component#name. A pack is a name. The listing names the component that declares
  it. Turn a pack on or off with add --pack and remove --pack. --type pack lists packs; it does not
  turn one on.

Types (--type; comma-separated or repeatable):
  skill                Ability an agent can invoke for a task.
  rule                 Standing instruction applied to an agent.
  command              Explicit command an operator or agent can invoke.
  agent                Agent a component ships; an rbtv agent or a harness-native sub-agent.
  hook                 Action triggered by a tool event.
  mcp-server           Server an agent tool connects to for extra tools.
  tool                 Runnable program exposed through a command shortcut.
  folder-instructions  Text added to a folder's instructions file.
  pack                 A named list of units a component declares.

Examples:
  rbtv list core
  rbtv list core/ignite
  rbtv list --type agent
  rbtv list --type pack
  rbtv list --installed
  rbtv list --limit 20 --offset 20

Results show the next-page command when more entries match.

positional arguments:
  NAME                  exact module, component, unit, or pack name

options:
  -h, --help            show this help message and exit
  --module, -m MODULE   filter to a module (a bundle of components)
  --component, -c COMPONENT
                        filter to a component (related units)
  --type, -x TYPE       filter to a type, such as skill, agent, or pack
  --installed           show only installed units, and packs that are on
  --limit LIMIT         maximum rows (default: 20)
  --offset OFFSET       rows to skip (default: 0)
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "search": """\
rbtv — search help

usage: rbtv search [-h] [--module MODULE] [--component COMPONENT]
                    [--type TYPE] [--installed] [--limit LIMIT]
                    [--offset OFFSET] [--target TARGET] [--json]
                   
                    WORDS

Search names and descriptions in the local source catalog. Results are units and packs with full
  ids. A word matches any part of the id or the description, so a component name matches every entry
  in that component. Search does not choose anything. Use list NAME when you know an exact module,
  component, unit, or pack name. WORDS is required; an empty search is refused.

Types (--type; comma-separated or repeatable):
  skill                Ability an agent can invoke for a task.
  rule                 Standing instruction applied to an agent.
  command              Explicit command an operator or agent can invoke.
  agent                Agent a component ships; an rbtv agent or a harness-native sub-agent.
  hook                 Action triggered by a tool event.
  mcp-server           Server an agent tool connects to for extra tools.
  tool                 Runnable program exposed through a command shortcut.
  folder-instructions  Text added to a folder's instructions file.
  pack                 A named list of units a component declares.

Example: rbtv search research

positional arguments:
  WORDS                 words matched against names and descriptions

options:
  -h, --help            show this help message and exit
  --module, -m MODULE   filter to a module (a bundle of components)
  --component, -c COMPONENT
                        filter to a component (related units)
  --type, -x TYPE       filter to a type, such as skill, agent, or pack
  --installed           show only installed units, and packs that are on
  --limit LIMIT         maximum rows (default: 20)
  --offset OFFSET       rows to skip (default: 0)
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "show": """\
rbtv — show help

usage: rbtv show [-h] [--type TYPE] [--pack PACK]
                  [--target TARGET] [--json]
                  [NAME]

Show the catalog description, included units or component summaries, and the saved selection for one
  unit, pack, component, or module. It does not print source-file contents. A short name must be
  unique. A bare name never resolves to a pack. show --pack NAME shows that pack and prints the
  declaration file, <component>/packs/<pack>.json in the rbtv source. For an agent a component
  ships, it shows the harnesses it is written for as a harness-native sub-agent, whether it is
  placed as an rbtv agent, and the command that adds it in each form.

Types (--type; comma-separated or repeatable):
  skill                Ability an agent can invoke for a task.
  rule                 Standing instruction applied to an agent.
  command              Explicit command an operator or agent can invoke.
  agent                Agent a component ships; an rbtv agent or a harness-native sub-agent.
  hook                 Action triggered by a tool event.
  mcp-server           Server an agent tool connects to for extra tools.
  tool                 Runnable program exposed through a command shortcut.
  folder-instructions  Text added to a folder's instructions file.
  pack                 A named list of units a component declares.

Examples:
  rbtv show kiss
  rbtv show meta/behaviour#kiss
  rbtv show --pack ignite
  rbtv show research
  rbtv show web/research

positional arguments:
  NAME                  unique short name, full id, or module/component;
                        omit it when --pack is given

options:
  -h, --help            show this help message and exit
  --type, -x TYPE       require this type, such as skill or tool
  --pack PACK           show this pack; use it when the name is also a unit
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "doctor": """\
rbtv — doctor help

usage: rbtv doctor [-h] [--cleanup-audit] [--target TARGET]
                    [--json] [--pretty]

Check generated files and selected shared command shortcuts for the selected installation or agent.
  Reports problems and a recovery command. Changes no files. Names where each check ran: the
  installation or agent, the local rbtv source, shared commands, or the current PATH (the shell's
  command lookup list).

options:
  -h, --help            show this help message and exit
  --cleanup-audit       also inspect shortcut claims from other
                        installations
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
  --pretty              use colour in doctor output
""",
    "interactive": """\
rbtv — interactive help

usage: rbtv interactive [-h] [--target TARGET]

Start the guided menu. This is the only command that asks questions. For scripts or agents, use
  list, show, add and remove. --json is refused: a script cannot answer the menu. The menu installs
  whole components and never guesses a model or an effort: an agent a component ships gets no
  harness-native sub-agent file, and the result names the command that adds it,
  rbtv add NAME --on HARNESS:MODEL:EFFORT.

options:
  -h, --help            show this help message and exit
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
""",
    "selftest": """\
rbtv — selftest help

usage: rbtv selftest [-h]

Run automated checks using temporary files and isolated command shortcuts. Leaves live installations
  unchanged. Takes no target: the checks do not read the selected installation. --json is refused;
  run without it.

options:
  -h, --help            show this help message and exit
""",
    "configure": """\
rbtv — configure help

usage: rbtv configure [-h] [--harness HARNESS]
                      [--guidance {AGENTS.md,CLAUDE.md,none}]
                      [--target TARGET] [--json] [--dry-run] [--details]

Initialize a fresh target or change saved receiving tools and guidance.
This command selects no catalog units. Changing settings regenerates
generated files for units already selected; it does not add new units.
On first setup, give both --harness and --guidance. A named guidance file
must already exist at the installation root; choose none when you maintain
no such file. Later, each supplied option replaces its saved setting; an
option you omit stays as it is.

--harness replaces the complete list of receiving AI tools: claude, codex,
opencode.
--guidance names the instruction file you maintain. none turns copies off.

An agent installed as a harness-native sub-agent has a model and an effort
for each harness. A harness you add gets no sub-agent file: rbtv cannot
choose its model and effort. The result names each such agent and the
command that adds it, rbtv add NAME --on HARNESS:MODEL:EFFORT. A harness
you drop loses its sub-agent files and their model and effort.

Examples:
  rbtv configure --harness claude,codex --guidance none
  rbtv configure --harness claude,opencode
  rbtv configure --guidance CLAUDE.md

options:
  -h, --help            show this help message and exit
  --harness HARNESS     replace the list of AI tools: claude,codex,opencode
  --guidance {AGENTS.md,CLAUDE.md,none}
                        instruction file you maintain, or none
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                one JSON value on standard output, for success
                        and for failure
  --dry-run             show what would change; write and delete nothing
  --details             list every unit and file instead of counting

Also accepted:
  rbtv add harness opencode          (add one harness)
  rbtv remove harness codex          (drop one harness)
  rbtv add guidance exclude vendor
  rbtv remove guidance exclude vendor
The last two exclude or include a folder when copying guidance.

Exit codes: 0 success; 1 refused; 2 invalid arguments.
Next: rbtv status
""",
    "add": """\
rbtv — add help

usage: rbtv add [-h] [--all] [--module MODULE] [--component COMPONENT]
                [--type TYPE] [--exclude-type TYPE]
                [--exclude-module MODULE] [--exclude-component COMPONENT]
                [--pack PACK] [--on HARNESS:MODEL:EFFORT]
                [--harness HARNESS]
                [--guidance {AGENTS.md,CLAUDE.md,none}] [--target TARGET]
                [--json] [--dry-run] [--details]
                [NAME ...]

Add named units, whole components, a pack, or a filtered selection from
local source, and write their generated files. A bare name never resolves
to a pack: rbtv add ignite is the tool core/ignite#ignite. Name a pack
with --pack. A short name must match one unit. --pack adds that pack's
units and combines with named units. Filters narrow together, including a
pack; values inside one filter are alternatives. An empty result is
refused and nothing is written. Nothing fetches a newer source.

An agent a component ships, named here, is written as a harness-native
sub-agent: the harness's own sub-agent file, for the harnesses given with
--on HARNESS:MODEL:EFFORT. --on repeats, once per harness, and is required
when an agent is among the names. Each harness must be one this target
receives. Model and effort are checked with cast list, so cast must be on
PATH. Running it again for a harness replaces that harness's model and
effort. The agent's own units and packs are not applied: a harness-native
sub-agent sees what its target has. A component given as a NAME names
its agents too. A selection by --all, --module, --component or --type
skips agents and says so. To place the agent as an rbtv agent in its own
folder instead, use rbtv agent add.

Types (--type; comma-separated or repeatable):
  skill                 Ability an agent can invoke for a task.
  rule                  Standing instruction applied to an agent.
  command               Explicit command an operator or agent can invoke.
  agent                 An agent a component ships. Named here with --on, it
                        is written as a harness-native sub-agent.
  hook                  Action triggered by a tool event.
  mcp-server            Server an agent tool connects to for extra tools.
  tool                  Runnable program exposed through a command shortcut.
  folder-instructions   Text added to a folder's instructions file.

First add in an installation needs both --harness and --guidance:
  rbtv add brainstorm --harness claude,codex --guidance none

--harness chooses which AI tools receive files.
--guidance chooses the instruction file you maintain. none turns copies
off. Later adds can omit both.

positional arguments:
  NAME                  unit name (brainstorm), full unit id
                        (meta/functions#brainstorm), or whole component
                        (meta/functions)

options:
  -h, --help            show this help message and exit
  --all, -A             choose every unit in the catalog
  --module, -m MODULE   choose a module; comma-separated or repeatable
  --component, -c COMPONENT
                        choose a component; full unit ids are accepted too
  --type, -x TYPE       choose unit types; comma-separated or repeatable
  --exclude-type TYPE
                        leave these unit types out
  --exclude-module MODULE
                        leave these modules out
  --exclude-component COMPONENT
                        leave these components out
  --pack PACK           turn this pack on; its units are added like names
  --on HARNESS:MODEL:EFFORT
                        for an agent among the names: write it as a
                        harness-native sub-agent for this harness, with
                        this model and effort; repeatable, one harness
                        each; see cast list
  --harness HARNESS     AI tools receiving files; required on first add:
                        claude,codex,opencode (comma-separated)
  --guidance {AGENTS.md,CLAUDE.md,none}
                        instruction file you maintain, or none; required
                        on first add
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                one JSON value on standard output, for success
                        and for failure
  --dry-run             show what would change; write and delete nothing
  --details             list every unit and file instead of counting

Examples:
  rbtv add brainstorm
  rbtv add --pack research-kit
  rbtv add meta/functions#brainstorm --dry-run --details
  rbtv add fact-checker --on claude:sonnet-5:high --on codex:gpt-6-sol:medium

Different filters narrow together. --module web --type skill chooses only
skills in web. --pack research-kit --type rule matches nothing in that
pack and is refused.

Exit codes: 0 success; 1 refused; 2 invalid arguments.
Next: rbtv status
""",
    "remove": """\
rbtv — remove help

usage: rbtv remove [-h] [--all] [--module MODULE] [--component COMPONENT]
                   [--type TYPE] [--exclude-type TYPE]
                   [--exclude-module MODULE]
                   [--exclude-component COMPONENT] [--pack PACK] [--yes]
                   [--target TARGET] [--json] [--dry-run] [--details]
                   [NAME ...]

Remove installed units from this installation, and delete the generated
files that go with them. A named unit, component or pack needs no --yes.
--pack turns that pack off and removes units it added, unless the same
unit is also installed on its own. Counts never count one unit twice.
Broad filters (--all, --module, --type, or any exclusion) need --yes when
they match installed units. An empty result needs no confirmation.
Removal never asks a question. A command shortcut stays while another
installation still uses it.

Alias: rm

Types (--type; comma-separated or repeatable):
  skill                 Ability an agent can invoke for a task.
  rule                  Standing instruction applied to an agent.
  command               Explicit command an operator or agent can invoke.
  agent                 An agent a component ships, installed here as a
                        harness-native sub-agent.
  hook                  Action triggered by a tool event.
  mcp-server            Server an agent tool connects to for extra tools.
  tool                  Runnable program exposed through a command shortcut.
  folder-instructions   Text added to a folder's instructions file.

Remove a named unit:
  rbtv remove root-cause

Turn a pack off:
  rbtv remove --pack research-kit

Preview a broad removal, then confirm it:
  rbtv remove --all --dry-run
  rbtv remove --all --yes

positional arguments:
  NAME                  unit name, full unit id, or whole component

options:
  -h, --help            show this help message and exit
  --all, -A             select every installed unit
  --module, -m MODULE   choose a module; comma-separated or repeatable
  --component, -c COMPONENT
                        choose a component
  --type, -x TYPE       choose unit types; comma-separated or repeatable
  --exclude-type TYPE
                        leave these unit types out
  --exclude-module MODULE
                        leave these modules out
  --exclude-component COMPONENT
                        leave these components out
  --pack PACK           turn this pack off
  --yes                 confirm a removal selected by module, type, all, or
                        an exclusion
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                one JSON value on standard output, for success
                        and for failure
  --dry-run             show what would change; write and delete nothing
  --details             list every unit and file instead of counting

Exit codes: 0 success; 1 refused; 2 invalid arguments.
Next: rbtv status
""",
    "update": """\
rbtv — update help

usage: rbtv update [-h] {guidance,scaffolding,all} ...

Make the folder match install.json, from the RBTV source already on this
machine. Does not download a newer source, and does not select a unit
the file does not list. The scope is required. The root file is edited
by hand; it is not shared between machines.

  guidance      Copy the instruction file you maintain into each other
                harness's file. Leaves each file's generated section as
                it is. Adds and removes no units. If guidance is none,
                there is nothing to copy.
  scaffolding   Regenerate generated files for the installed units. Add a
                unit the file lists whose generated files are missing.
                Remove generated files for a unit the file no longer
                lists. Does not copy the text you maintain.
  all           Run scaffolding, then guidance.

The result names every unit added and every unit removed, including
when both lists are empty.

positional arguments:
  {guidance,scaffolding,all}
    guidance            copy maintained text; add and remove no units
    scaffolding         make generated files match the installed units
    all                 scaffolding, then guidance

options:
  -h, --help            show this help message and exit

Example: rbtv update all --dry-run
Next: rbtv update all
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "update guidance": """\
rbtv — update guidance help

usage: rbtv update guidance [-h] [--target TARGET] [--json] [--dry-run]
                            [--details]

Copy the human text of the instruction file you maintain (CLAUDE.md or
AGENTS.md) into each other harness's file. Strips generated text from
what it copies. Leaves each destination's own generated section as it
is — it does not rebuild that section (that is update scaffolding).
Adds and removes no units. Saved guidance exclusions apply. If guidance
is none, there is nothing to copy and nothing is written. If the folder
still does not match the file, the result says so and names
`rbtv update scaffolding`. If the maintained file is missing, the command
refuses and changes nothing.

options:
  -h, --help       show this help message and exit
  --target TARGET  installation or agent folder; overrides
                   RBTV_AGENT_HOME and discovery from the current folder
  --json           one JSON value on standard output, for success and
                   for failure
  --dry-run        show what would change; write and delete nothing
  --details        list every file instead of counting

Example: rbtv update guidance
Next: rbtv doctor
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "update scaffolding": """\
rbtv — update scaffolding help

usage: rbtv update scaffolding [-h] [--target TARGET] [--json]
                               [--dry-run] [--details]

Make generated files match install.json. Regenerates generated files
for units the file lists, writes a listed unit whose files are missing,
and removes generated files for a unit the file no longer lists. The
result names what was added and what was removed. Leaves human-authored
text alone; it does not copy that text (that is update guidance). Use
update all when both parts of every file must be current.

options:
  -h, --help       show this help message and exit
  --target TARGET  installation or agent folder; overrides
                   RBTV_AGENT_HOME and discovery from the current folder
  --json           one JSON value on standard output, for success and
                   for failure
  --dry-run        show what would change; write and delete nothing
  --details        list every unit and file instead of counting

Example: rbtv update scaffolding
Next: rbtv doctor
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "update all": """\
rbtv — update all help

usage: rbtv update all [-h] [--target TARGET] [--json] [--dry-run]
                       [--details]

Run scaffolding, then guidance. Generated files are made to match
install.json (units added whose files are missing, generated files
removed for units the file no longer lists), then maintained text is
copied. The result names what was added and what was removed. If the
maintained guidance file is missing, refuses before any write.

options:
  -h, --help       show this help message and exit
  --target TARGET  installation or agent folder; overrides
                   RBTV_AGENT_HOME and discovery from the current folder
  --json           one JSON value on standard output, for success and
                   for failure
  --dry-run        show what would change; write and delete nothing
  --details        list every unit and file instead of counting

Example: rbtv update all
Next: rbtv doctor
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "agent": """\
rbtv — agent help

Manage one agent: which units it is exposed to, and its harness, model and
effort. AGENT is a name under the installation's .rbtv/agents/, found by
walking up from the current folder, or a path to a folder that holds
agent.md and agent.json.

To write a new agent, create a folder with agent.md (its prompt) and
agent.json (its description, units and packs), then run rbtv agent add
AGENT --harness HARNESS --model MODEL --effort EFFORT to apply it. Guide:
core/build/capabilities/guides/agent.md in the rbtv source.

  add AGENT [NAME...]   Apply agent.json, then add named units or a pack.
  remove AGENT NAME...  Remove units or a pack. The agent folder stays.
  configure AGENT       Change harness, model, effort or voice.
  update AGENT SCOPE    Make the folder match agent.json. Scope is required.
  list [AGENT]          List the installation's agents, or AGENT in full.

Shared options: --json  -h, --help
Changes also accept --dry-run and --details.
These verbs take no --target. A name is looked up in the installation
found from the current folder. A path is the agent folder, used in place.
RBTV_AGENT_HOME does not stand in for AGENT.
Aliases ls, li and rm are root commands. They are not verbs of agent.
This command never asks a question.

Start: rbtv agent list
More:  rbtv agent COMMAND -h
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent add": """\
rbtv — agent add help

usage: rbtv agent add [-h] [--pack PACK]
                      [--harness {claude,codex,opencode}] [--model MODEL]
                      [--effort EFFORT] [--on HARNESS:MODEL:EFFORT]
                      [--json] [--dry-run] [--details]
                      AGENT [NAME ...]

Apply what AGENT's agent.json declares, the first time or again, then add
any NAME units and record them in agent.json. --pack turns a pack on and
records it. Declared units are applied first; a unit already on disk is
left as it is. A second run that finds nothing missing changes nothing.
To write a new agent first, see the new-agent passage in rbtv agent -h.

A name is looked up in <installation>/.rbtv/agents/, then among agents a
component ships. A shipped agent with no folder there is placed in
.rbtv/agents/<name>/, then applied. A path is used in place: nothing is
copied. The folder name, the name in agent.md, and the name in agent.json
must agree.

--harness, --model and --effort are required, all three, when agent.json
has none: always the case for an agent a component ships. They are checked
with cast list, so cast must be on PATH, and written into the agent's
agent.json. When agent.json already has them, giving one is refused:
change them with rbtv agent configure.

A short unit name must be unique; otherwise pass the full id,
<module>/<component>#<unit>. A pack is named only with --pack, for example
--pack research-kit. A bare name is always a unit, never a pack. A NAME
that is an agent a component ships is written for AGENT as a
harness-native sub-agent and needs --on with AGENT's own harness.
This verb takes no --target. See rbtv list and rbtv show.

positional arguments:
  AGENT                 name or path of the agent
  NAME                  unit to add; repeatable. Short name or full id

options:
  -h, --help            show this help message and exit
  --pack PACK           turn this pack on and record it in agent.json.
                        A pack is never a bare NAME
  --harness {claude,codex,opencode}
                        the harness that runs AGENT; with --model and
                        --effort, only for an agent whose agent.json has
                        none
  --model MODEL         a model cast list shows for that harness
  --effort EFFORT       1 to 5, or the model's own effort word
  --on HARNESS:MODEL:EFFORT
                        for an agent among the NAME units: the model and
                        effort of its harness-native sub-agent; HARNESS
                        is AGENT's own harness
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every unit and file instead of counting

Examples:
  rbtv agent add plans/launch/agents/drafter
  rbtv agent add research --harness opencode --model glm-5.3 --effort high
  rbtv agent add plans/launch/agents/drafter investignosis
  rbtv agent add plans/launch/agents/drafter --pack research-kit --dry-run

Next: rbtv agent list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent remove": """\
rbtv — agent remove help

usage: rbtv agent remove [-h] [--pack PACK] [--all] [--yes]
                         [--json] [--dry-run] [--details]
                         AGENT [NAME ...]

Remove units from the agent and from its agent.json. --pack turns that
pack off. A pack is named only with --pack; a bare NAME is always a unit.
--all removes every unit and turns every pack off; it requires --yes.
A named unit or a named pack needs no --yes. Give one of NAME, --pack or
--all. This verb takes no --target. It never asks a question and never
deletes the agent folder, agent.md or agent.json.

positional arguments:
  AGENT                 name or path of the agent
  NAME                  unit to remove; repeatable. Short name or full id

options:
  -h, --help            show this help message and exit
  --pack PACK           turn this pack off and drop it from agent.json
  --all                 remove every unit; requires --yes
  --yes                 confirm --all
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every unit and file instead of counting

Examples:
  rbtv agent remove scout interview
  rbtv agent remove scout --pack ignite --dry-run
  rbtv agent remove scout --all --yes

Next: rbtv agent list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent configure": """\
rbtv — agent configure help

usage: rbtv agent configure [-h] [--harness {claude,codex,opencode}]
                            [--model MODEL] [--effort EFFORT]
                            [--voice VOICE] [--json] [--dry-run]
                            [--details]
                            AGENT

Change harness, model, effort or voice. At least one option is required.
Each supplied option replaces that value; an omitted value stays as it
is. The result shows before and after.

--model must be a name from cast list. --effort is a word that model
accepts, or a number 1-5 stored as that model's word. Both are checked
with cast list, so cast must be on PATH. --voice is the voice the agent
speaks with; cast list does not check it.

Changing --harness regenerates generated files for the new harness.
A harness-native sub-agent written for the old harness is deleted with its
model and effort; the result names the command that adds it for the new one.
Changing model, effort or voice updates agent.json only.
This verb takes no --target. It never changes units or packs.

Harness values:
  claude (Claude Code)
  codex (Codex)
  opencode (OpenCode)

positional arguments:
  AGENT                 name or path of the agent

options:
  -h, --help            show this help message and exit
  --harness HARNESS     claude, codex or opencode
  --model MODEL         a model name from cast list
  --effort EFFORT       an effort word that model accepts, or 1-5
  --voice VOICE         voice the agent speaks with; any text
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every unit and file instead of counting

Examples:
  rbtv agent configure scout --model gpt-6-astra --effort medium
  rbtv agent configure plans/launch/agents/drafter --harness codex --model gpt-6.1-sol --effort high

Next: rbtv agent list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent update": """\
rbtv — agent update help

usage: rbtv agent update [-h] [--json] [--dry-run] [--details]
                         AGENT {guidance,scaffolding,all}

Make the agent folder match agent.json. This is what a second machine
runs after git pull. It does not change harness, model, effort or voice,
and it does not download a newer source.

AGENT comes first. SCOPE is required. Without a scope the command is
wrong usage and changes nothing. A scope word is not an agent name.
This verb takes no --target.

  guidance      Copy a maintained instruction file, if one is set. Does
                not add or remove units. With no guidance file set,
                reports nothing to copy. If the folder still does not
                match agent.json, the result says so and names the
                command that would finish the match.
  scaffolding   Generated files only: add what agent.json lists and is
                missing, and remove generated files it no longer lists.
                "scaffolding" is the scope name; the files are generated
                files.
  all           scaffolding, then guidance.

positional arguments:
  AGENT                 name or path of the agent
  {guidance,scaffolding,all}
    guidance            copy maintained text; add and remove no units
    scaffolding         make generated files match agent.json
    all                 scaffolding, then guidance

options:
  -h, --help            show this help message and exit
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every unit and file instead of counting

Examples:
  rbtv agent update scout all
  rbtv agent update plans/launch/agents/drafter scaffolding --dry-run

Next: rbtv agent list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent list": """\
rbtv — agent list help

usage: rbtv agent list [-h] [--json] [AGENT]

List the agents of this installation, or show one of them in full. The
list is the one cast prints: this verb runs cast list --agents, so cast
must be on PATH. It only reads. This verb takes no --target.

With no AGENT: the agents in the installation's .rbtv/agents/, the
installation found by walking up from the current folder. Columns:
name, harness, model, effort, Ignite (yes when the agent's ignite pack
is on, which ignite connect does), and description. The description is
shortened to fit the line. At a narrow width, each agent is a labeled
block with its whole description; a name is never cut. Alphabetical by
name. No row limit. An agent that cannot be launched is named with the
reason. No agent found is success.

With AGENT: that agent in full: its folder, its whole description, and
the packs, skills, rules, commands, MCP servers and hooks installed in
it, under the names rbtv show takes. AGENT is a name or a folder path,
as for the other agent verbs. An agent that is not found is refused.

positional arguments:
  AGENT                 the agent to show in full: a name under
                        .rbtv/agents/, or a path to an agent folder

options:
  -h, --help            show this help message and exit
  --json                one JSON value on standard output, success or
                        failure

Examples:
  rbtv agent list
  rbtv agent list scout
  rbtv agent list plans/launch/agents/drafter

Next: rbtv agent configure scout -h
Exit codes: 0 success, including no agent found; 1 refused or failed; 2 invalid arguments.
""",
}
