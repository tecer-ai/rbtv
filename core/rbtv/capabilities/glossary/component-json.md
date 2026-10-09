# `<component>.json`

`<component>.json` is a component’s record at `<module>/<component>/<component>.json`. It tells rbtv what the component is for and which outside software it requires.

Use [component-json.schema.json](../templates/component-json.schema.json) for the fields. Before writing or changing the description, follow [Component](component.md) for the subject boundary and naming. The record does not choose exposure methods; the source folders do.

In `dependencies`, name the software the component requires but does not include. Use an empty list when none is required. rbtv displays these names; it does not install or verify those dependencies.

`repository`, when present, names a git checkout rbtv keeps at `repository/` inside this component folder. `url` and `branch` are required. Neither may start with `-`. `requirements` is an optional relative path inside that checkout. Reading the record does not require the checkout to exist. [rbtv CLI](rbtv-cli.md) owns clone, check and fast-forward.

Validate the record and inspect the component’s displayed description and dependencies through [rbtv CLI](rbtv-cli.md). Check required software through the component’s actual operation; accepting the record does not prove that software is available.
