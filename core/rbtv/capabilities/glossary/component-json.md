# `<component>.json`

`<component>.json` is a component’s record at `<module>/<component>/<component>.json`. It tells rbtv what the component is for and which outside software it requires.

Use [component-json.schema.json](../templates/component-json.schema.json) for the fields. Before writing or changing the description, follow [Component](component.md) for the subject boundary and naming. The record does not choose exposure methods; the source folders do.

In `dependencies`, write one entry for each program or package the component requires but does not include. Use an empty list when none is required. This record is the one home of a dependency's install command: a page that tells a reader to install the dependency uses the record's exact command.

- `name` is the name its publisher gives it: the package name in its registry, or the program's name.
- `install` is the command that installs it, the same on Linux and Windows. Write `npm install --global <package>` for an npm package and `python -m pip install <package>` for a Python package; the reader runs it with the Python of their own environment. When no package manager installs it, write the address of its install page.
- `command` is the name the program has on PATH, when it has one. It can differ from `name`: the npm package `defuddle-cli` installs the command `defuddle`.
- `python_package` is the name pip installs a Python package under. An entry has `command` or `python_package`, never both. Write neither when no lookup on both systems finds the dependency, as for the Python interpreter, whose command name differs between systems.

`rbtv show` prints each entry's install command. `rbtv doctor` looks up `command` on PATH and `python_package` in the Python that runs rbtv, reports the entry present, absent or not checked, and prints the install command of each one it did not find present. rbtv never runs an install command.

`repository`, when present, names a git checkout rbtv keeps at `repository/` inside this component folder. `url` and `branch` are required. Neither may start with `-`. `requirements` is an optional relative path inside that checkout. Reading the record does not require the checkout to exist. [rbtv CLI](rbtv-cli.md) owns clone, check and fast-forward.

Validate the record and inspect the component’s displayed description and dependencies through [rbtv CLI](rbtv-cli.md). Verify each `install` value against the publisher's own instructions, and each `command` by running the installed program by that name. Check required software through the component’s actual operation; accepting the record does not prove that software is available.
