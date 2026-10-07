"""The `-h` pages, one per command path: the approved help text of
the review screens (`1-projects/rbtv-agent-cli-unification/build/screens/review/`),
kept verbatim. Each page is named by its command path; `root` is the bare command.
The `--type` values and their meanings are written once, in `present.py`.

The selftest checks that every option a `providers` command takes is named on its page.
"""
from __future__ import annotations

from .present import types_block

_LISTING_TYPES = types_block()

PAGES = {
    "root": """\
rbtv — help

Discover
  status        Show target, saved settings, and recorded selections.
  list [NAME]   Table of many entries, browsed by exact name: modules, a module's
                components, a component's files.
  search WORDS  Find modules, components, files and packs whose name or description
                holds every word.
  show NAME     Everything about one named entry: description, files, dependencies,
                where it is installed.

Change this installation
  configure         Initialize or change receiving tools and guidance settings.
  add [NAME...]     Add named or filtered files, or turn a pack on.
  remove [NAME...]  Remove installed files, or turn a pack off.
  update SCOPE      Make the folder match install.json. The scope is required.

Agents
  agent VERB    Act on one agent instead of this installation: create it, change its
                files, harness, model or effort, or list the agents. See: rbtv agent -h

Provider accounts
  providers VERB  List providers, save and switch account logins, read plan
                  usage. See: rbtv providers -h

Check and guided use
  doctor       Check harness files and selected command shortcuts.
  interactive  Choose files through a guided menu (asks questions).
  selftest     Run checks in isolated temporary installations.

Shared options: --target PATH  --json  -h, --help  --version
Non-interactive changes also accept --dry-run and --details.
Only interactive asks questions.
Target order: --target, then RBTV_AGENT_HOME, then discovery from the current folder.
Aliases: ls=list; li=list --installed; rm=remove.
A file id is module/component#name. A pack is named only with --pack.
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
  was selected. An agent result shows harness, model, effort, voice, packs and installed files.
  It does not show a Slack connection. A root result shows none of name, description, harness,
  model or effort. Both results name each agent installed as a harness-native sub-agent, with the
  model and the effort of every harness it is written for. A root result names each folder of
  .rbtv/ that exists, what it holds and the page of the rbtv source that explains it.

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
                  [--offset OFFSET] [--full] [--target TARGET] [--json]
                 
                  [NAME]

Browse the local source catalog. No NAME shows modules; a module shows its components; a component
  shows its files and any pack it declares; an exact name shows only that file. A pack is
  named only with --pack. NAME never searches descriptions. Use search for broad discovery.
  Installed means recorded for this installation; use doctor to check the files. --installed with
  no NAME lists every installed file across modules in one table, then the packs that are on; with a
  NAME it narrows inside that module or component. Under the table, an installed agent is named with the
  harnesses it is written for as a harness-native sub-agent, and the model and effort of each.

A file id is module/component#name. A pack is a name. The listing names the component that declares
  it. Turn a pack on or off with add --pack and remove --pack. --type pack lists packs; it does not
  turn one on. --type module lists the modules, the table no NAME shows. --type component lists every
  component across modules; with a module as NAME, that module's components. Each of the two is
  named without another type.

Types (--type; comma-separated or repeatable):
""" + _LISTING_TYPES + """

Examples:
  rbtv list core
  rbtv list core/ignite
  rbtv list --type agent
  rbtv list --type pack
  rbtv list --type component
  rbtv list --installed
  rbtv list --limit 20 --offset 20

Results show the next-page command when more entries match.

positional arguments:
  NAME                  exact module, component, file, or pack name

options:
  -h, --help            show this help message and exit
  --module, -m MODULE   filter to a module (a bundle of components)
  --component, -c COMPONENT
                        filter to a component (related files)
  --type, -x TYPE       filter to a type, such as skill, agent, or pack
  --installed           show only installed files, and packs that are on
  --limit LIMIT         maximum rows (default: 20)
  --offset OFFSET       rows to skip (default: 0)
  --full                show every description whole, one labeled block
                        per row; a list shows the first sentence otherwise
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "search": """\
rbtv — search help

usage: rbtv search [-h] [--module MODULE] [--component COMPONENT]
                    [--type TYPE] [--installed] [--limit LIMIT]
                    [--offset OFFSET] [--full] [--target TARGET] [--json]
                   
                    WORDS

Search names and descriptions in the local source catalog. Results are modules, components, files
  and packs, with full ids. A word matches any part of the id or the description, so a component
  name matches every entry in that component. Search does not choose anything. Use list NAME when
  you know an exact module, component, file, or pack name. WORDS is required; an empty search is
  refused. A search with no hit prints no rows and up to five words of the source catalog nearest
  to each word that matched nothing, as "Did you mean: ...?"; with --json they are the list
  did_you_mean.

Types (--type; comma-separated or repeatable):
""" + _LISTING_TYPES + """

Example: rbtv search research

positional arguments:
  WORDS                 words matched against names and descriptions

options:
  -h, --help            show this help message and exit
  --module, -m MODULE   filter to a module (a bundle of components)
  --component, -c COMPONENT
                        filter to a component (related files)
  --type, -x TYPE       filter to a type, such as skill, agent, or pack
  --installed           show only installed files, and packs that are on
  --limit LIMIT         maximum rows (default: 20)
  --offset OFFSET       rows to skip (default: 0)
  --full                show every description whole, one labeled block
                        per row; a list shows the first sentence otherwise
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "show": """\
rbtv — show help

usage: rbtv show [-h] [--type TYPE] [--pack PACK] [--full]
                  [--target TARGET] [--json]
                  [NAME]

Show the source catalog description, included files or component summaries, and the saved
  selection for one file, pack, component, or module. It does not print source-file contents. A
  short name must be unique. A bare name never resolves to a pack. show --pack NAME shows that pack
  and prints the declaration file, <component>/packs/<pack>.json in the rbtv source. For an agent a
  component ships, it shows the harnesses it is written for as a harness-native sub-agent, whether
  it is placed as an rbtv agent, and the command that adds it in each form. A name that is no file
  is read as a component's short name; --type component reads it so when a file has the same name.
  --type module requires a module.

Types (--type; comma-separated or repeatable):
""" + _LISTING_TYPES + """

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
  --pack PACK           show this pack; use it when the name is also a file
  --full                show the whole description of a module or a
                        component, and of the rows under it
  --target TARGET       installation or agent folder; overrides
                        RBTV_AGENT_HOME and discovery from the current
                        folder
  --json                return structured JSON for scripts and agents
""",
    "doctor": """\
rbtv — doctor help

usage: rbtv doctor [-h] [--cleanup-audit] [--target TARGET]
                    [--json] [--pretty]

Check harness files and selected shared command shortcuts for the selected installation or agent.
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
This command selects no source catalog files. Changing settings regenerates
the harness files of files already selected; it does not add new files.
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
  --details             list every file and harness file instead of counting

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

Add named files, whole components, a pack, or a filtered selection from
local source, and write their harness files. A bare name never resolves
to a pack: rbtv add ignite is the tool core/ignite#ignite. Name a pack
with --pack. A short name must match one file. --pack adds that pack's
files and combines with named files. Filters narrow together, including a
pack; values inside one filter are alternatives. An empty result is
refused and nothing is written. Nothing fetches a newer source.

An agent a component ships, named here, is written as a harness-native
sub-agent: the harness's own sub-agent file, for the harnesses given with
--on HARNESS:MODEL:EFFORT. --on repeats, once per harness, and is required
when an agent is among the names. Each harness must be one this target
receives. Model and effort are checked with cast models list: the model
must be one this installation selected (cast models add HARNESS MODEL
selects one), so cast must be on PATH. Running it again for a harness replaces that harness's model and
effort. The agent's own files and packs are not applied: a harness-native
sub-agent sees what its target has. A component given as a NAME names
its agents too. A selection by --all, --module, --component or --type
skips agents and says so. To place the agent as an rbtv agent in its own
folder instead, use rbtv agent add.

Types (--type; comma-separated or repeatable):
""" + types_block(change="add") + """

First add in an installation needs both --harness and --guidance:
  rbtv add brainstorm --harness claude,codex --guidance none

--harness chooses which AI tools receive files.
--guidance chooses the instruction file you maintain. none turns copies
off. Later adds can omit both.

positional arguments:
  NAME                  short name (brainstorm), full id
                        (meta/functions#brainstorm), or whole component
                        (meta/functions)

options:
  -h, --help            show this help message and exit
  --all, -A             choose every file in the source catalog
  --module, -m MODULE   choose a module; comma-separated or repeatable
  --component, -c COMPONENT
                        choose a component; full ids are accepted too
  --type, -x TYPE       choose file types; comma-separated or repeatable
  --exclude-type TYPE
                        leave these file types out
  --exclude-module MODULE
                        leave these modules out
  --exclude-component COMPONENT
                        leave these components out
  --pack PACK           turn this pack on; its files are added like names
  --on HARNESS:MODEL:EFFORT
                        for an agent among the names: write it as a
                        harness-native sub-agent for this harness, with
                        this model and effort; repeatable, one harness
                        each; see cast models list
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
  --details             list every file and harness file instead of counting

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

Remove installed files from this installation, and delete the harness
files that go with them. A named file, component or pack needs no --yes.
--pack turns that pack off and removes files it added, unless the same
file is also installed on its own. Counts never count one file twice.
Broad filters (--all, --module, --type, or any exclusion) need --yes when
they match installed files. An empty result needs no confirmation.
Removal never asks a question. A command shortcut stays while another
installation still uses it.

Alias: rm

Types (--type; comma-separated or repeatable):
""" + types_block(change="remove") + """

Remove a named file:
  rbtv remove root-cause

Turn a pack off:
  rbtv remove --pack research-kit

Preview a broad removal, then confirm it:
  rbtv remove --all --dry-run
  rbtv remove --all --yes

positional arguments:
  NAME                  short name, full id, or whole component

options:
  -h, --help            show this help message and exit
  --all, -A             select every installed file
  --module, -m MODULE   choose a module; comma-separated or repeatable
  --component, -c COMPONENT
                        choose a component
  --type, -x TYPE       choose file types; comma-separated or repeatable
  --exclude-type TYPE
                        leave these file types out
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
  --details             list every file and harness file instead of counting

Exit codes: 0 success; 1 refused; 2 invalid arguments.
Next: rbtv status
""",
    "update": """\
rbtv — update help

usage: rbtv update [-h] {guidance,scaffolding,all} ...

Make the folder match install.json, from the RBTV source already on this
machine. Does not download a newer source, and does not select a file
that install.json does not list. The scope is required. The root file is edited
by hand; it is not shared between machines.

  guidance      Copy the instruction file you maintain into each other
                harness's file. Leaves each file's generated section as
                it is. Adds and removes no files. If guidance is none,
                there is nothing to copy.
  scaffolding   Regenerate the harness files of the installed files. Add a
                file that install.json lists whose harness files are
                missing. Remove the harness files of a file it no longer
                lists. Does not copy the text you maintain.
  all           Run scaffolding, then guidance.

The result names every file added and every file removed, including
when both lists are empty.

positional arguments:
  {guidance,scaffolding,all}
    guidance            copy maintained text; add and remove no files
    scaffolding         make harness files match the installed files
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
Adds and removes no files. Saved guidance exclusions apply. If guidance
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

Make harness files match install.json. Regenerates the harness files
of the files it lists, writes a listed file whose harness files are
missing, and removes the harness files of a file it no longer lists. The
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
  --details        list every file and harness file instead of counting

Example: rbtv update scaffolding
Next: rbtv doctor
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "update all": """\
rbtv — update all help

usage: rbtv update all [-h] [--target TARGET] [--json] [--dry-run]
                       [--details]

Run scaffolding, then guidance. Harness files are made to match
install.json (a listed file added when its harness files are missing,
the harness files of a file it no longer lists removed), then maintained text is
copied. The result names what was added and what was removed. If the
maintained guidance file is missing, refuses before any write.

options:
  -h, --help       show this help message and exit
  --target TARGET  installation or agent folder; overrides
                   RBTV_AGENT_HOME and discovery from the current folder
  --json           one JSON value on standard output, for success and
                   for failure
  --dry-run        show what would change; write and delete nothing
  --details        list every file and harness file instead of counting

Example: rbtv update all
Next: rbtv doctor
Exit codes: 0 success; 1 refused; 2 invalid arguments.
""",
    "agent": """\
rbtv — agent help

Manage one agent: which files it is exposed to, and its harness, model and
effort. AGENT is a name under the installation's .rbtv/agents/, found by
walking up from the current folder, or a path to a folder that holds
agent.md and agent.json.

To write a new agent, create a folder with agent.md (its prompt) and
agent.json (its description, files and packs), then run rbtv agent add
AGENT --harness HARNESS --model MODEL --effort EFFORT to apply it. Guide:
core/rbtv/capabilities/glossary/agent.md in the rbtv source.

  add AGENT [NAME...]   Apply agent.json, then add named files or a pack.
  remove AGENT NAME...  Remove files or a pack. The agent folder stays.
  configure AGENT       Change harness, model, effort or voice.
  update AGENT SCOPE    Make the folder match agent.json. Scope is required.
  list [AGENT]          List the installation's agents, or AGENT in full.

Shared options: --json  -h, --help
Changes also accept --dry-run and --details.
Only list takes --target, to list the agents of another folder. For the
other verbs a name is looked up in the installation
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
any NAME files and record them in agent.json. --pack turns a pack on and
records it. Declared files are applied first; a file already on disk is
left as it is. A second run that finds nothing missing changes nothing.
To write a new agent first, see the new-agent passage in rbtv agent -h.

A name is looked up in <installation>/.rbtv/agents/, then among agents a
component ships. A shipped agent with no folder there is placed in
.rbtv/agents/<name>/, then applied. A path is used in place: nothing is
copied. The folder name, the name in agent.md, and the name in agent.json
must agree.

--harness, --model and --effort are required, all three, when agent.json
has none: always the case for an agent a component ships. They are checked
with cast models list, so cast must be on PATH, and written into the
agent's agent.json. The model must be one the installation selected:
cast models add HARNESS MODEL selects one. When agent.json already has them, giving one is refused:
change them with rbtv agent configure.

A short name must be unique; otherwise pass the full id,
<module>/<component>#<name>. A pack is named only with --pack, for example
--pack research-kit. A bare name is always a file, never a pack. A NAME
that is an agent a component ships is written for AGENT as a
harness-native sub-agent and needs --on with AGENT's own harness.
This verb takes no --target. See rbtv list and rbtv show.

positional arguments:
  AGENT                 name or path of the agent
  NAME                  file to add; repeatable. Short name or full id

options:
  -h, --help            show this help message and exit
  --pack PACK           turn this pack on and record it in agent.json.
                        A pack is never a bare NAME
  --harness {claude,codex,opencode}
                        the harness that runs AGENT; with --model and
                        --effort, only for an agent whose agent.json has
                        none
  --model MODEL         a model cast models list shows for that harness
  --effort EFFORT       1 to 5, or the model's own effort word
  --on HARNESS:MODEL:EFFORT
                        for an agent among the names: the model and
                        effort of its harness-native sub-agent; HARNESS
                        is AGENT's own harness
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every file and harness file instead of counting

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

Remove files from the agent and from its agent.json. --pack turns that
pack off. A pack is named only with --pack; a bare NAME is always a file.
--all removes every file and turns every pack off; it requires --yes.
A named file or a named pack needs no --yes. Give one of NAME, --pack or
--all. This verb takes no --target. It never asks a question and never
deletes the agent folder, agent.md or agent.json.

positional arguments:
  AGENT                 name or path of the agent
  NAME                  file to remove; repeatable. Short name or full id

options:
  -h, --help            show this help message and exit
  --pack PACK           turn this pack off and drop it from agent.json
  --all                 remove every file; requires --yes
  --yes                 confirm --all
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every file and harness file instead of counting

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

--model must be a name from cast models list: a model this installation
selected (cast models add HARNESS MODEL selects one). --effort is a word
that model accepts, or a number 1-5 stored as that model's word. Both are
checked with cast models list, so cast must be on PATH. --voice is the
voice the agent speaks with; cast does not check it.

Changing --harness regenerates the harness files for the new harness.
A harness-native sub-agent written for the old harness is deleted with its
model and effort; the result names the command that adds it for the new one.
Changing model, effort or voice updates agent.json only.
This verb takes no --target. It never changes files or packs.

Harness values:
  claude (Claude Code)
  codex (Codex)
  opencode (OpenCode)

positional arguments:
  AGENT                 name or path of the agent

options:
  -h, --help            show this help message and exit
  --harness HARNESS     claude, codex or opencode
  --model MODEL         a model name from cast models list
  --effort EFFORT       an effort word that model accepts, or 1-5
  --voice VOICE         voice the agent speaks with; any text
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every file and harness file instead of counting

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
                not add or remove files. With no guidance file set,
                reports nothing to copy. If the folder still does not
                match agent.json, the result says so and names the
                command that would finish the match.
  scaffolding   Harness files only: add what agent.json lists and is
                missing, and remove harness files it no longer lists.
                "scaffolding" is the scope name; the files are harness
                files.
  all           scaffolding, then guidance.

positional arguments:
  AGENT                 name or path of the agent
  {guidance,scaffolding,all}
    guidance            copy maintained text; add and remove no files
    scaffolding         make harness files match agent.json
    all                 scaffolding, then guidance

options:
  -h, --help            show this help message and exit
  --json                one JSON value on standard output, success or
                        failure
  --dry-run             preview changes without writing or removing files
  --details             list every file and harness file instead of counting

Examples:
  rbtv agent update scout all
  rbtv agent update plans/launch/agents/drafter scaffolding --dry-run

Next: rbtv agent list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "agent list": """\
rbtv — agent list help

usage: rbtv agent list [-h] [--target FOLDER] [--full] [--json] [AGENT]

List the agents of this installation, or show one of them in full. The
list is the one cast prints: this verb runs cast list --agents, so cast
must be on PATH. It only reads.

With --target FOLDER: the agents of FOLDER instead, as cast reads it.
FOLDER is an installation (it holds .rbtv/): the agents in its
.rbtv/agents/. Or an agent folder: that one agent. Or a folder that
holds agent folders, such as the agents/ folder of a plan: those agents.
A FOLDER that is none of the three is refused. AGENT is then a name
among those agents, never a path.

With no AGENT: the agents in the installation's .rbtv/agents/, the
installation found by walking up from the current folder. Columns:
name, harness, model, effort, Ignite (yes when the agent's ignite pack
is on, which ignite connect does), and description. The description is
shortened to fit the line. With --full, or at a narrow width, each
agent is a labeled block with its whole description; a name is never
cut. Alphabetical by name. No row limit. An agent that cannot be
launched is named with the reason. No agent found is success.

With AGENT: that agent in full: its folder, its whole description, and
the packs, skills, rules, commands, MCP servers and hooks installed in
it, under the names rbtv show takes. AGENT is a name or a folder path,
as for the other agent verbs. An agent that is not found is refused.

positional arguments:
  AGENT                 the agent to show in full: a name under
                        .rbtv/agents/, or a path to an agent folder

options:
  -h, --help            show this help message and exit
  --target FOLDER       list the agents of FOLDER: an installation, a
                        folder that holds agent folders, or one agent
                        folder
  --full                show every description whole; one agent is
                        always shown in full
  --json                one JSON value on standard output, success or
                        failure

Examples:
  rbtv agent list
  rbtv agent list --full
  rbtv agent list scout
  rbtv agent list plans/launch/agents/drafter
  rbtv agent list --target plans/launch/agents

Next: rbtv agent configure scout -h
Exit codes: 0 success, including no agent found; 1 refused or failed; 2 invalid arguments.
""",
    "providers": """\
rbtv — providers help

usage: rbtv providers [-h] COMMAND ...

Manage the AI provider accounts this machine uses. A provider is the lab
whose models a harness runs (claude, codex, zai, google, ...). List the
supported providers, save the current login under a name, switch between
saved logins without logging in again, and read each account's plan usage.

  list [PROVIDER]               Login state and saved names; --supported
                                lists what rbtv supports instead.
  switch PROVIDER ACCOUNT       Make a saved login the live one.
  name PROVIDER ACCOUNT         Save the current login under ACCOUNT.
  remove-name PROVIDER ACCOUNT  Delete a saved login. It cannot be undone.
  usage [PROVIDER] [ACCOUNT]    Plan usage and renewal times.

Only claude and codex logins can be saved and switched; every other
provider holds one login or key, with nothing to switch between. Saved
logins live in <installation>/.rbtv/config/rbtv/providers/, kept out of
git. The installation is found from the current folder; these verbs take
no --target.
Guide: core/rbtv/capabilities/providers.md in the rbtv source.

Shared options: --json  -h, --help
Changes also accept --dry-run. This command never asks a question.

Start: rbtv providers list
More:  rbtv providers COMMAND -h
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "providers list": """\
rbtv — providers list help

usage: rbtv providers list [-h] [--supported] [--json] [PROVIDER]

Every supported provider and whether this machine is logged in to it. For
claude and codex: each saved name, * on the live one, its e-mail and how
long the saved login stays valid. A live login saved under no name is
flagged: save it with name before you switch. Local files only; no network.

--supported lists what rbtv supports instead: each provider's lab, the
harness that runs it, its login method (account or API key), its key
variable, and where its usage figure comes from. Models: cast models list.

positional arguments:
  PROVIDER     only this provider, for example claude

options:
  -h, --help   show this help message and exit
  --supported  supported providers instead of login state
  --json       one JSON value on standard output, success or failure

Examples:
  rbtv providers list
  rbtv providers list claude --json
  rbtv providers list --supported

Next: rbtv providers usage
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "providers switch": """\
rbtv — providers switch help

usage: rbtv providers switch [-h] [--json] [--dry-run] PROVIDER ACCOUNT

Make the login saved as ACCOUNT the live login of PROVIDER (claude or
codex). The live login is first saved back under its own name, because
tokens change as they are used. Refused when the live login is saved under
no name: run rbtv providers name PROVIDER NAME first. Running sessions keep
their account; new sessions use ACCOUNT.

positional arguments:
  PROVIDER    claude or codex
  ACCOUNT     a saved name; rbtv providers list PROVIDER shows them

options:
  -h, --help  show this help message and exit
  --json      one JSON value on standard output, success or failure
  --dry-run   say what would change without writing

Example: rbtv providers switch claude work
Next: rbtv providers usage claude
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "providers name": """\
rbtv — providers name help

usage: rbtv providers name [-h] [--json] [--dry-run] PROVIDER ACCOUNT

Save PROVIDER's current login as ACCOUNT, in
<installation>/.rbtv/config/rbtv/providers/PROVIDER/ACCOUNT.json. Log in
with the harness first (claude, then /login; codex login). ACCOUNT is 1 to
40 lowercase letters, digits and hyphens. A name that already holds a
different account is refused: remove it first. The same account is
refreshed.

positional arguments:
  PROVIDER    claude or codex
  ACCOUNT     the name to save the current login under

options:
  -h, --help  show this help message and exit
  --json      one JSON value on standard output, success or failure
  --dry-run   say what would be written without writing

Example: rbtv providers name claude work
Next: rbtv providers list claude
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "providers remove-name": """\
rbtv — providers remove-name help

usage: rbtv providers remove-name [-h] [--yes] [--json] [--dry-run]
                                  PROVIDER ACCOUNT

Delete the login saved as ACCOUNT. That file is the only copy of the
account's login: to use it again, log in to it again. The live name is
refused; switch first. Without --yes, nothing is deleted: the refusal names
the file and the command that confirms (exit 1).

positional arguments:
  PROVIDER    claude or codex
  ACCOUNT     a saved name; rbtv providers list PROVIDER shows them

options:
  -h, --help  show this help message and exit
  --yes       confirm the deletion
  --json      one JSON value on standard output, success or failure
  --dry-run   name the file that would be deleted without deleting it

Example: rbtv providers remove-name claude work --yes
Next: rbtv providers list claude
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
    "providers usage": """\
rbtv — providers usage help

usage: rbtv providers usage [-h] [--posh] [--interval SECONDS] [--json]
                            [PROVIDER] [ACCOUNT]

Plan usage of each account with a readable source: used percent and renewal
time of each window (claude, codex, zai, kimi), the balance (deepseek), or
the console address where no source exists (google, sakana, xai). claude
reads every saved name through its own stored token; an expired token is
reported as expired, never as 0%. Each key is sent only to its own
provider's usage address and is never printed. codex usage comes from this
machine's session files: whichever account ran last. A row that cannot be
read is reported in its place, and the command still exits 0.

positional arguments:
  PROVIDER            only this provider
  ACCOUNT             only this saved name; needs PROVIDER

options:
  -h, --help          show this help message and exit
  --posh              a full-screen view with bars and countdowns, redrawn
                      every second; ctrl-c exits; needs a terminal; not
                      with --json
  --interval SECONDS  with --posh, seconds between reads, 30 or more
                      (default 120)
  --json              one JSON value on standard output, success or failure

Examples:
  rbtv providers usage
  rbtv providers usage claude work
  rbtv providers usage --posh

Next: rbtv providers list
Exit codes: 0 success; 1 refused or failed; 2 invalid arguments.
""",
}
